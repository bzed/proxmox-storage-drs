# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Order a target assignment's moves. See IMPLEMENTATION_PLAN.md section 8.

``heuristic.py`` (or, later, ``optimize.py``) produces a *target
assignment* — which storage each disk should end up on. It says nothing
about the order those moves happen in, and order matters: section 8.1's
transient invariant is a constraint on every intermediate state during a
migration, not just the before/after endpoints, since the mirror target
holds a full copy of the volume before the source is released.

``order_moves()`` implements section 8.2's scheduling loop: repeatedly
pick the pending move with the best imbalance-reduction-per-byte-moved
that is transient-feasible right now, applying moves that repair a
currently-violating storage first regardless of that ratio (section 13:
safety is not subject to hysteresis, here too). A move whose source or
target the invariant rejects stays pending; if *no* pending move is
feasible, scheduling stops and reports the deadlock rather than forcing
an infeasible one (section 8.3's option 3 -- see the module docstring's
note on what is deliberately not implemented, below).

**Deliberately not implemented in this pass** (all documented, not
forgotten -- see ``docs/internals/95-schedule.md``):

- **Concurrent scheduling** (``execution.max_concurrent_migrations > 1``).
  This module schedules strictly sequentially -- each move is assumed to
  fully complete (including any ``saferemove`` wipe) before the next
  starts -- regardless of the configured concurrency. Reasoning about
  overlapping in-flight windows needs move-duration estimates
  (``payback.py``, not yet written); the plan's own generalized invariant
  is stated so scheduling can be extended to it later without changing
  this module's shape (section 8.1: "implement this as the single
  feasibility predicate and call it with M = {m} for the sequential
  case"), which is exactly what this module does.
- **Ordering priority 2** ("moves that free space a later move needs")
  and **staging** (section 8.3 option 1). Both are optimizations over a
  plan that is already feasible without them (front-loading value, or
  resolving an otherwise-genuine deadlock by temporarily parking a disk);
  omitting them can only make this module report a deadlock where a more
  sophisticated scheduler would have found a way through, never produce
  an unsafe order.
- **Cooldowns and concurrency limits.** ``state.json`` (section 11.2, not
  yet written) is what a real cooldown or an accurate in-flight-move count
  needs; every move here is scheduled as if no cooldown applies and no
  other run's moves are already in flight, the same simplification
  ``gates.py`` already documents for ``last_load=None``.
- **The section 7.3 saturation check.** Belongs with ``payback.py``, which
  also does not exist yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from proxmox_storage_drs.config import ObjectiveConfig
from proxmox_storage_drs.heuristic import Assignment, evaluate_assignment, group_average_utilization
from proxmox_storage_drs.reserve import (
    compute_reserve_status,
    largest_disk_bytes,
    managed_used_bytes,
)
from proxmox_storage_drs.topology import Disk, Group, Storage


@dataclass(frozen=True, slots=True)
class ScheduledMove:
    """One move, in the position :func:`order_moves` assigned it."""

    disk_key: str
    vmid: int
    device: str
    from_storage: str
    to_storage: str
    size_bytes: int
    imbalance_reduction: float  # this move's own effect, at the moment it was scheduled
    resolves_reserve_violation: bool  # section 8.2 priority 1: scheduled first regardless of ratio


@dataclass(frozen=True, slots=True)
class ScheduleResult:
    """One group's ordered plan, or as much of it as could be scheduled."""

    order: tuple[ScheduledMove, ...]
    # Disks the target assignment moves that no feasible order was found
    # for -- section 8.3 option 3, "report the blocking set and stop."
    # Empty unless a real deadlock was hit.
    deadlocked: tuple[str, ...]

    @property
    def deadlocked_msg(self) -> str | None:
        if not self.deadlocked:
            return None
        return (
            "no transient-feasible order found for: "
            + ", ".join(sorted(self.deadlocked))
            + " -- every remaining move would breach the transient reserve invariant "
            "on its target (section 8.1); see section 8.3 for resolution options "
            "this module does not yet implement (staging, splitting the plan)"
        )


def _pending_moves(group: Group, target_assignment: Assignment) -> dict[str, Disk]:
    return {
        d.key: d
        for d in group.disks
        if target_assignment.get(d.key, d.current_storage) != d.current_storage
    }


def transient_invariant_ok(
    group: Group,
    state: Assignment,
    disk: Disk,
    target_storage: Storage,
    min_free_bytes: int,
) -> bool:
    """Section 8.1's single-move transient invariant:
    ``used_b + z_d + f_b * max(Z_b, z_d) <= C_b``.

    ``state`` is the assignment as of *right before* this move starts --
    every previously-scheduled move already fully applied (this module's
    sequential-only simplification; see the module docstring), so
    ``target_storage``'s ``used``/``Z_b`` here do not yet include the
    disk this call is checking. The ``min_free_bytes`` floor is folded in
    the same way (C5) folds it into the steady-state reserve, for the same
    reason: a small-disk storage's absolute floor should not evaporate
    just because a migration is in flight.
    """

    def storage_of(d: Disk) -> str:
        return state.get(d.key, d.current_storage)

    used_b = (
        managed_used_bytes(group.disks, target_storage.id, storage_of=storage_of)
        + target_storage.foreign_used_bytes
    )
    existing_largest = largest_disk_bytes(group.disks, target_storage.id, storage_of=storage_of)
    required = max(
        round(target_storage.reserve_factor * max(existing_largest, disk.size_bytes)),
        min_free_bytes,
    )
    return used_b + disk.size_bytes + required <= target_storage.capacity_bytes


def _resolves_reserve_violation(
    group: Group, state: Assignment, disk: Disk, min_free_bytes: int
) -> bool:
    """Section 8.2 priority 1: is ``disk``'s *current* (in ``state``)
    storage presently violating (C5)? Moving any disk off a violating
    storage always helps or leaves it unchanged (removing bytes cannot
    increase `used`, and cannot increase the largest-disk-driven reserve
    term either) -- see ``heuristic._repair``'s identical reasoning -- so
    "source currently violates" is sufficient to qualify without needing
    to re-check the reduction amount here."""

    def storage_of(d: Disk) -> str:
        return state.get(d.key, d.current_storage)

    source_id = state.get(disk.key, disk.current_storage)
    source = next(s for s in group.storages if s.id == source_id)
    return compute_reserve_status(
        source, group.disks, min_free_bytes, storage_of=storage_of
    ).violated


def order_moves(
    group: Group,
    target_assignment: Assignment,
    load_by_key: Mapping[str, float],
    objective: ObjectiveConfig,
    min_free_bytes: int,
) -> ScheduleResult:
    """Section 8.2's scheduling loop for one group.

    ``target_assignment`` is normally a :class:`heuristic.HeuristicResult`'s
    ``.assignment``; ``load_by_key``/``objective``/``min_free_bytes`` are
    the same inputs :func:`heuristic.evaluate_assignment` takes, reused
    here (not re-derived) to score each candidate move's imbalance
    reduction with whichever ``objective.spread_metric`` is configured.
    """
    storages_by_id = {s.id: s for s in group.storages}
    state: Assignment = {d.key: d.current_storage for d in group.disks}
    pending = _pending_moves(group, target_assignment)
    u_star = group_average_utilization(group, load_by_key)

    order: list[ScheduledMove] = []
    while pending:
        current_imbalance = evaluate_assignment(
            group, state, load_by_key, objective, min_free_bytes, u_star
        ).imbalance_term

        feasible: list[str] = []
        for key, disk in pending.items():
            target_id = target_assignment[key]
            target = storages_by_id[target_id]
            if transient_invariant_ok(group, state, disk, target, min_free_bytes):
                feasible.append(key)

        if not feasible:
            break

        priority = [
            key
            for key in feasible
            if _resolves_reserve_violation(group, state, pending[key], min_free_bytes)
        ]
        candidates = priority or feasible

        best_key = None
        best_ratio = float("-inf")
        best_reduction = 0.0
        for key in candidates:
            disk = pending[key]
            trial = dict(state)
            trial[key] = target_assignment[key]
            trial_imbalance = evaluate_assignment(
                group, trial, load_by_key, objective, min_free_bytes, u_star
            ).imbalance_term
            reduction = current_imbalance - trial_imbalance
            cost = disk.size_bytes
            ratio = reduction / cost if cost > 0 else reduction
            if ratio > best_ratio:
                best_ratio = ratio
                best_key = key
                best_reduction = reduction

        assert best_key is not None  # candidates is non-empty whenever feasible is
        disk = pending.pop(best_key)
        target_id = target_assignment[best_key]
        order.append(
            ScheduledMove(
                disk_key=best_key,
                vmid=disk.vmid,
                device=disk.device,
                from_storage=state[best_key],
                to_storage=target_id,
                size_bytes=disk.size_bytes,
                imbalance_reduction=best_reduction,
                resolves_reserve_violation=best_key in priority,
            )
        )
        state[best_key] = target_id

    return ScheduleResult(order=tuple(order), deadlocked=tuple(sorted(pending)))
