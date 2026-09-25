# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Migration cost and the payback acceptance test. See IMPLEMENTATION_PLAN.md section 7.

"Migrating a very large disk may generate more traffic than it saves" is a
**hard acceptance test on the finished plan** (section 7's own framing),
not a soft penalty in the balance objective — a penalty can always be
outweighed by a large enough imbalance term, an acceptance test cannot.
Everything here is pure: given a scheduled move and the storages it
touches, or a whole plan's before/after imbalance, compute the numbers;
nothing fetches anything.

**Deliberately not implemented in this pass** (see
``docs/internals/96-payback.md``):

- **`headroom_src`/`headroom_dst`** in an older draft of section 7.1's
  ``duration_mirror_d`` formula. They were never defined; the mirror
  duration is ``z_d / migration.bwlimit_bytes_per_sec``, full stop.
  ``bwlimit`` is the only throttle a migration needs (section 7.3).
- **The 3-retry re-solve-with-doubled-`beta`/`gamma` loop** on aggregate
  payback failure. A real UX refinement (it converges on the smaller
  subset of high-value moves rather than abandoning the run), not a
  correctness requirement -- the core requirement ("reject a plan whose
  cost outweighs its benefit") is satisfied by reporting accept/reject
  plainly. Automatically re-solving and re-scheduling from here would
  duplicate `cli.py`'s own orchestration of `heuristic.py`/`schedule.py`;
  better done there, later, than half-built in this module now.
- **Automatically dropping an individually-rejected move** (one whose own
  `duration_d` exceeds `max_single_move_duration`) and re-solving without
  it. Reported instead (`MoveCost.exceeds_max_duration`,
  `PaybackResult.rejected_moves`) -- "report, never force" is this
  project's consistent answer to a move that cannot proceed as planned
  (`schedule.py`'s deadlock reporting is the same choice).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from proxmox_storage_drs.config import MigrationConfig
from proxmox_storage_drs.heuristic import Assignment
from proxmox_storage_drs.reserve import total_shortfall_bytes
from proxmox_storage_drs.schedule import ScheduledMove
from proxmox_storage_drs.topology import Disk, Group, Storage


@dataclass(frozen=True, slots=True)
class MoveCost:
    """Section 7.1's cost for one already-scheduled move."""

    disk_key: str
    duration_mirror_seconds: float
    duration_wipe_seconds: float
    cost_load_seconds: float  # duration_mirror*(w_src+w_dst) + duration_wipe*w_wipe
    exceeds_max_duration: bool  # hard rule: duration_d > migration.max_single_move_duration
    # Section 7.3's revert test: would holding this disk back on its
    # current storage strictly raise the plan's final Sum r_s? Computed by
    # `repair_markers()` below, over the *executed* final assignment (this
    # move's source/target still held if it was itself excluded by
    # `exceeds_max_duration`) -- not set by
    # `compute_move_cost()` itself, which runs before that assignment is
    # known; defaults False until the caller (cli.py's plan builder) fills
    # it in via `dataclasses.replace()`.
    repair: bool = False

    @property
    def duration_seconds(self) -> float:
        return self.duration_mirror_seconds + self.duration_wipe_seconds


@dataclass(frozen=True, slots=True)
class PaybackResult:
    """One plan's section 7.3 acceptance verdict.

    ``aggregate_ok`` (``benefit >= payback_ratio * Sum cost_d``, or
    unconditionally ``True`` when ``repair_exempt`` -- see
    ``evaluate_plan_payback()``) and ``accepted`` (``aggregate_ok`` **and**
    no individually-rejected move) are kept separate so a
    caller can report *why* an otherwise-profitable plan was still
    rejected, rather than only a single bit.

    ``repair_exempt``/``reserve_shortfall_bytes_before``/``_after`` are
    section 7.3's outcome trigger, carried on the result so `cli.py` can
    surface them in ``--json`` (section 9.5) -- without them an exempt
    plan and one accepted on merit are the same object to a consumer."""

    move_costs: tuple[MoveCost, ...]
    # (alpha*(E_before-E_after) + delta*(F_before-F_after) + kappa*(A_before-A_after))
    # * migration.payback_horizon
    benefit_load_seconds: float
    rejected_moves: tuple[str, ...]  # disk keys failing the hard per-move duration rule
    aggregate_ok: bool
    repair_exempt: bool = False
    reserve_shortfall_bytes_before: int = 0
    reserve_shortfall_bytes_after: int = 0

    @property
    def total_cost_load_seconds(self) -> float:
        return sum(mc.cost_load_seconds for mc in self.move_costs)

    @property
    def ratio(self) -> float:
        cost = self.total_cost_load_seconds
        return self.benefit_load_seconds / cost if cost > 0 else float("inf")

    @property
    def accepted(self) -> bool:
        return self.aggregate_ok and not self.rejected_moves


def compute_wipe_duration_seconds(
    disk_bytes: int, throughput_bytes_per_sec: float | None
) -> float | None:
    """``duration_wipe_d`` (section 7.1) for one disk on one storage, or
    ``None`` if there is nothing to wipe (no ``saferemove`` throughput
    known -- either the storage type has no such concept, e.g. Ceph RBD
    or ZFS, or ``saferemove`` is off there). Shared by
    ``compute_move_cost()`` below and ``cli.py``'s ``verify-storages``,
    which needs the identical number for its own, unrelated warning about
    cooldowns and move-duration limits being shorter than the implied
    wipe -- one implementation of the formula (AGENTS.md section 5).

    **A negative ``saferemove_throughput`` is normal, and its magnitude
    is the rate.** PVE passes the configured value straight through to
    ``cstream -t`` (section 7.1), whose sign selects *how* the limit is
    enforced, never how fast: a positive number is an average the whole
    session converges on, so a run may exceed the rate for a while to
    make good on earlier underutilization; a negative number is a hard
    ceiling on each individual read/write syscall pair, which is never
    exceeded. Both describe the same |num| bytes/second, so the duration
    is ``disk_bytes / abs(throughput)`` in both cases -- and if anything
    the negative form is the more dependable estimate of the two, since
    the wipe can never finish ahead of it. Dividing by the signed value
    instead yields a *negative duration*, which is not merely a cosmetic
    wrong number: it cancels ``duration_mirror_seconds`` in
    ``compute_move_cost()`` and silently disables section 7.3's
    ``max_single_move_duration`` rejection and ``verify-storages``'
    cooldown warning. Found by replaying a real bundle whose three LVM
    storages all carry ``saferemove_throughput -1073741824``.
    """
    if not throughput_bytes_per_sec:
        return None
    return disk_bytes / abs(throughput_bytes_per_sec)


def compute_move_cost(move: ScheduledMove, source: Storage, migration: MigrationConfig) -> MoveCost:
    """Section 7.1's cost for one scheduled move.

    Only ``source`` is needed (not the target storage): `saferemove` is a
    property of where the volume is *removed from*, and
    ``migration.bwlimit_bytes_per_sec`` is the one global mirror-rate
    config value both ends share, so ``duration_mirror_d = z_d / bwlimit``
    (see the module docstring)."""
    bwlimit = migration.bwlimit_bytes_per_sec
    duration_mirror = move.size_bytes / bwlimit if bwlimit else 0.0

    duration_wipe = 0.0
    if migration.account_saferemove_wipe and source.saferemove:
        wipe = compute_wipe_duration_seconds(
            move.size_bytes, source.saferemove_throughput_bytes_per_sec
        )
        if wipe is not None:
            duration_wipe = wipe

    # Section 7.1: "a disk below migration.tiny_disk_bytes costs nothing" --
    # cost_load_seconds alone is zeroed, not duration_mirror/duration_wipe:
    # the hard per-move duration rule below still applies to a
    # tiny disk exactly like any other move (section 7.3).
    cost = (
        0.0
        if move.size_bytes < migration.tiny_disk_bytes
        else (
            duration_mirror * (migration.source_load_weight + migration.target_load_weight)
            + duration_wipe * migration.wipe_load_weight
        )
    )
    exceeds = (duration_mirror + duration_wipe) > migration.max_single_move_duration_seconds

    return MoveCost(
        disk_key=move.disk_key,
        duration_mirror_seconds=duration_mirror,
        duration_wipe_seconds=duration_wipe,
        cost_load_seconds=cost,
        exceeds_max_duration=exceeds,
    )


def compute_benefit_load_seconds(
    alpha_spread: float,
    imbalance_before: float,
    imbalance_after: float,
    delta_capacity_spread: float,
    capacity_spread_before: float,
    capacity_spread_after: float,
    payback_horizon_seconds: float,
    kappa_vm_affinity: float = 0.0,
    affinity_debt_before: float = 0.0,
    affinity_debt_after: float = 0.0,
) -> float:
    """Section 7.2: ``benefit = (alpha*(E_before - E_after) +
    delta*(F_before - F_after) + kappa*(A_before - A_after)) * H``.
    ``imbalance_before``/``imbalance_after``, ``capacity_spread_before``/
    ``capacity_spread_after`` and ``affinity_debt_before``/
    ``affinity_debt_after`` must be the *raw*, unweighted section 7.2
    quantities -- ``heuristic.raw_spread()``'s ``sum(e_s)`` (``"l1"``) or
    ``max(u_s)`` (``"minmax"``) for ``E``, ``heuristic.raw_capacity_spread()``'s
    ``sum(d_s)`` for ``F``, and ``heuristic.raw_affinity_debt()``'s
    ``sum(w_v * extra storages)`` for ``A`` -- evaluated at the pre-plan
    and post-plan assignments respectively. **Not**
    ``ObjectiveBreakdown.imbalance_term``/``.capacity_spread_term``/
    ``.fragmentation_term``: those are the same quantities already scaled
    by ``objective.alpha_spread``/``objective.delta_capacity_spread``/
    ``objective.kappa_vm_affinity`` for the section 5.4 *solver* objective,
    and passing them here would double-apply the weight (REVIEW.md R-01 --
    earlier code passed ``imbalance_term`` directly; only invisible while
    ``alpha_spread``'s default of ``1.0`` made the two numerically
    identical). ``alpha_spread``/``delta_capacity_spread``/
    ``kappa_vm_affinity`` are explicit parameters here rather than baked
    into the inputs -- section 7.2's formula genuinely weights all three
    terms, and passing the weights in visibly, applied once, in the one
    place that computes ``benefit``, is what keeps R-01's underlying
    principle (no weight smuggled in through an already-scaled quantity)
    intact.

    ``kappa``/``A`` default to ``0.0`` so an existing caller that has not
    been updated to pass affinity data keeps computing the pre-section-12
    two-term formula unchanged.

    A negative result (the plan made imbalance, spread or affinity
    *worse* -- section 7.2: "``dA`` may be negative, and then it *reduces*
    the benefit: a balance move that splits a VM must pay for the
    fragmentation out of its alpha gain") is returned as computed, not
    clamped -- ``evaluate_plan_payback()``'s acceptance test already
    rejects it correctly without special-casing the sign here.
    """
    return (
        alpha_spread * (imbalance_before - imbalance_after)
        + delta_capacity_spread * (capacity_spread_before - capacity_spread_after)
        + kappa_vm_affinity * (affinity_debt_before - affinity_debt_after)
    ) * payback_horizon_seconds


def executed_assignment(
    group: Group, final_assignment: Assignment, excluded_disk_keys: frozenset[str]
) -> Assignment:
    """Section 7.3: "what it will really run" -- ``final_assignment``
    (``schedule_result.final_assignment``, the R-02 scheduled endpoint)
    with every disk in ``excluded_disk_keys`` held back at its *current*
    storage, as if its move had never been scheduled. ``excluded_disk_keys``
    is every disk key the hard per-move duration rule has taken out
    (``MoveCost.exceeds_max_duration``), computed by the caller before this
    is called (a per-move verdict on ``duration_d`` alone, independent of
    the exemption).

    This is the one assignment both section 7.3's outcome trigger and its
    revert test (:func:`repair_markers`) score, so a repair move that is
    itself excluded can never buy the plan-level exemption -- see the
    module-level ``evaluate_plan_payback()`` docstring."""
    return {
        d.key: (
            d.current_storage
            if d.key in excluded_disk_keys
            else final_assignment.get(d.key, d.current_storage)
        )
        for d in group.disks
    }


def repair_markers(
    group: Group, order: Iterable[ScheduledMove], executed_final_assignment: Assignment
) -> dict[str, bool]:
    """Section 7.3's revert test, one verdict per scheduled move in
    ``order``: would holding that one disk back on its *current* storage
    strictly raise the plan's final ``Sum r_s``, evaluated on
    ``executed_final_assignment`` (the same assignment the outcome trigger
    scores, via :func:`executed_assignment`) with that one ``x`` held? No
    re-solve -- the plan is fixed, this asks only what its own slack would
    be without one move.

    A move excluded from ``executed_final_assignment`` (its disk already
    sits at its current storage there) trivially scores ``False``: holding
    it back changes nothing, since it was never really applied. This
    covers the *indirect* repair (section 14.8): a move that empties the
    destination another repair needs is marked even though its own source
    was never in violation, because reverting it is what raises the
    group's final shortfall -- not because its own source was short."""
    disks_by_key = {d.key: d for d in group.disks}

    def storage_of(d: Disk) -> str:
        return executed_final_assignment.get(d.key, d.current_storage)

    base = total_shortfall_bytes(group.storages, group.disks, storage_of=storage_of)

    markers: dict[str, bool] = {}
    for move in order:
        disk = disks_by_key[move.disk_key]

        def reverted_storage_of(d: Disk, _disk: Disk = disk) -> str:
            if d.key == _disk.key:
                return _disk.current_storage
            return executed_final_assignment.get(d.key, d.current_storage)

        reverted = total_shortfall_bytes(
            group.storages, group.disks, storage_of=reverted_storage_of
        )
        markers[move.disk_key] = reverted > base
    return markers


def evaluate_plan_payback(
    move_costs: Iterable[MoveCost],
    benefit_load_seconds: float,
    payback_ratio: float,
    current_shortfall_bytes: int,
    final_shortfall_bytes: int,
) -> PaybackResult:
    """Section 7.3: the aggregate acceptance test over a whole plan, plus
    the hard per-move ``max_single_move_duration`` rule.

    **A plan that repairs is exempt from the aggregate test.** The
    trigger is the plan's *outcome*, not any one move's own flag:
    ``final_shortfall_bytes`` (``Sum r_s`` of the plan's executed
    endpoint -- :func:`executed_assignment`, after the hard per-move
    rules have taken their moves out) strictly below
    ``current_shortfall_bytes`` (``Sum r_s`` today). Section 7's whole
    premise is weighing a move's cost against the *balance* benefit it
    buys -- but a plan that leaves the group with less reserve/free-space
    shortfall than it found is not optional in the way a balance-driven
    plan is; it exists for safety, not for the imbalance reduction the
    benefit formula happens to compute for it (which can easily be zero or
    even net-negative on its own, section 14.8's own worked example).
    Section 13's "the reserve is never traded against balance" applies
    here just as much as it does to the drift/imbalance gates (`gates.py`)
    -- an operator does not get to decline a capacity emergency fix
    because it scores poorly against `migration.payback_ratio`. This is
    deliberately narrower than the built flag it replaced
    (``ScheduledMove.resolves_reserve_violation``, "some move's source was
    violating at scheduling time"): the outcome trigger is a *strict
    subset* of that condition (section 7.3's own proof), never a
    superset, so this change can only remove exemptions, never invent
    one. Both shortfall sums are the *caller's* responsibility --
    ``current_shortfall_bytes``/``final_shortfall_bytes`` are two sums
    over already-computed :class:`~proxmox_storage_drs.heuristic.ObjectiveBreakdown`
    objects (``reserve.total_shortfall_bytes()`` over
    ``solve_outcome.initial_breakdown``'s assignment and the *executed*
    final one respectively) -- this function has no access to a `Group`
    and does not need one.

    The hard per-move duration rule still applies regardless of the
    exemption (it is an operational limit, not an economic one, and
    section 7.3 lists it as one of the rules applied "regardless of the
    aggregate test"), so a repair move that would take days to wipe is
    still correctly flagged and still blocks `accepted`.

    The transient reserve invariant's own hard rule (section 7.3's third
    bullet) is not re-checked here -- ``schedule.py`` already enforces it
    before a move is ever scheduled, so by the time a ``ScheduledMove``
    reaches this module it has already passed that rule (AGENTS.md
    section 5: one implementation, not a second one here).

    **A plan of nothing but tiny disks passes the aggregate test
    unconditionally, by design.** Every move below
    ``migration.tiny_disk_bytes`` has ``cost_load_seconds == 0``
    (section 7.1), so ``total_cost`` is 0, ``aggregate_ok`` reduces to
    ``benefit_load_seconds >= 0``, and :attr:`PaybackResult.ratio`
    reports ``+inf``. Section 7.3's "needs no verdict" is exactly this:
    a 528 KiB ``efidisk0`` rejoining its VM must not have to out-earn a
    rule written for multi-terabyte migrations.

    The consequence is worth stating where the line is, because it is not
    visible from it: for such a plan **nothing downstream of the section
    5.4 objective asks whether the moves are worth making**, and no term
    in that objective has a materiality floor, so any ``+epsilon`` is
    enough. The affinity term's correctness is therefore load-bearing for
    tiny moves in a way it is not for any other kind. When section 5.3
    (C3) still excluded pinned disks by default, two 528 KiB moves on a
    real cluster were emitted on a 3.6e-7 capacity-spread difference with
    a kappa gain of exactly zero -- see section 7.3, which carries the
    full account and the narrowest fix (require
    ``affinity_debt_before > affinity_debt_after`` for a zero-cost plan)
    should a future bundle show the branch actually biting. Deliberately
    not implemented now: the observed failure was a defect in the
    objective, not a missing gate, and any threshold here would be a
    magic number."""
    move_costs = tuple(move_costs)
    total_cost = sum(mc.cost_load_seconds for mc in move_costs)
    repair_exempt = final_shortfall_bytes < current_shortfall_bytes
    aggregate_ok = repair_exempt or benefit_load_seconds >= payback_ratio * total_cost
    rejected = tuple(mc.disk_key for mc in move_costs if mc.exceeds_max_duration)
    return PaybackResult(
        move_costs=move_costs,
        benefit_load_seconds=benefit_load_seconds,
        rejected_moves=rejected,
        aggregate_ok=aggregate_ok,
        repair_exempt=repair_exempt,
        reserve_shortfall_bytes_before=current_shortfall_bytes,
        reserve_shortfall_bytes_after=final_shortfall_bytes,
    )
