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

- **`headroom_src`/`headroom_dst`** in section 7.1's
  ``duration_mirror_d = z_d / min(bwlimit, headroom_src, headroom_dst)``.
  These two terms are used in that one formula and never defined anywhere
  else in the plan — no config field or topology data represents a
  per-storage effective throughput ceiling distinct from the configured
  ``migration.bwlimit_bytes_per_sec``. ``compute_move_cost()`` here uses
  ``z_d / bwlimit`` only, which is what the formula reduces to whenever
  neither storage's own throughput is the binding constraint (the common
  case bwlimit exists to enforce) — a documented simplification of the
  plan's own underspecified formula, not a full accounting.
- **The section 7.3 saturation-ceiling defer check**
  (``L_during(s) <= saturation_ceiling * N_s``). Needs the forecaster's
  upper bound over a horizon equal to a specific move's own duration,
  which `forecast.py`'s ``Forecaster`` protocol does not yet expose (it
  answers for ``window.lookback`` only); and no group in this codebase's
  own dogfooding cluster has ``storages[].saturation_load`` set, which the
  plan itself says makes this "fully supported... loses only this one
  advisory check." `max_single_move_duration` (implemented below) and the
  transient reserve invariant (`schedule.py`, already enforced before a
  move ever reaches this module) are the two *hard* bounds section 7.3
  names as "always active"; this deferred one is explicitly the
  best-effort extra.
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
from proxmox_storage_drs.schedule import ScheduledMove
from proxmox_storage_drs.topology import Storage


@dataclass(frozen=True, slots=True)
class MoveCost:
    """Section 7.1's cost for one already-scheduled move."""

    disk_key: str
    duration_mirror_seconds: float
    duration_wipe_seconds: float
    cost_load_seconds: float  # duration_mirror*(w_src+w_dst) + duration_wipe*w_wipe
    exceeds_max_duration: bool  # hard rule: duration_d > migration.max_single_move_duration
    # Copied from `ScheduledMove.resolves_reserve_violation` -- carried here
    # rather than re-derived, so `evaluate_plan_payback()` can implement
    # section 13's "reserve is never traded against balance" for the
    # aggregate test too (see that function's docstring) without needing
    # the `ScheduledMove`s themselves.
    resolves_reserve_violation: bool

    @property
    def duration_seconds(self) -> float:
        return self.duration_mirror_seconds + self.duration_wipe_seconds


@dataclass(frozen=True, slots=True)
class PaybackResult:
    """One plan's section 7.3 acceptance verdict.

    ``aggregate_ok`` (``benefit >= payback_ratio * Sum cost_d``, or
    unconditionally ``True`` when any move resolves a reserve violation --
    see ``evaluate_plan_payback()``) and ``accepted`` (``aggregate_ok``
    **and** no individually-rejected move) are kept separate so a caller
    can report *why* an otherwise-profitable plan was still rejected,
    rather than only a single bit."""

    move_costs: tuple[MoveCost, ...]
    benefit_load_seconds: float  # (E_before - E_after) * migration.payback_horizon
    rejected_moves: tuple[str, ...]  # disk keys failing the hard per-move duration rule
    aggregate_ok: bool

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
    wipe -- one implementation of the formula (AGENTS.md section 5)."""
    if not throughput_bytes_per_sec:
        return None
    return disk_bytes / throughput_bytes_per_sec


def compute_move_cost(
    move: ScheduledMove,
    source: Storage,
    migration: MigrationConfig,
) -> MoveCost:
    """Section 7.1's cost for one scheduled move.

    Only ``source`` is needed (not the target storage): `saferemove` is a
    property of where the volume is *removed from*, and
    ``migration.bwlimit_bytes_per_sec`` is the one global mirror-rate
    config value both ends share (see the module docstring's note on
    ``headroom_src``/``headroom_dst``).
    """
    bwlimit = migration.bwlimit_bytes_per_sec
    duration_mirror = move.size_bytes / bwlimit if bwlimit else 0.0

    duration_wipe = 0.0
    if migration.account_saferemove_wipe and source.saferemove:
        wipe = compute_wipe_duration_seconds(
            move.size_bytes, source.saferemove_throughput_bytes_per_sec
        )
        if wipe is not None:
            duration_wipe = wipe

    cost = (
        duration_mirror * (migration.source_load_weight + migration.target_load_weight)
        + duration_wipe * migration.wipe_load_weight
    )
    exceeds = (duration_mirror + duration_wipe) > migration.max_single_move_duration_seconds

    return MoveCost(
        disk_key=move.disk_key,
        duration_mirror_seconds=duration_mirror,
        duration_wipe_seconds=duration_wipe,
        cost_load_seconds=cost,
        exceeds_max_duration=exceeds,
        resolves_reserve_violation=move.resolves_reserve_violation,
    )


def compute_benefit_load_seconds(
    imbalance_before: float, imbalance_after: float, payback_horizon_seconds: float
) -> float:
    """Section 7.2: ``benefit = (E_before - E_after) * H``. Both
    ``imbalance_before``/``imbalance_after`` are a
    ``heuristic.ObjectiveBreakdown.imbalance_term`` -- the *unweighted*
    (``alpha_spread``-scaled, which defaults to 1.0) section 5.4 imbalance
    term, evaluated at the pre-plan and post-plan assignments
    respectively. A negative result (the plan made imbalance *worse*,
    which a beta/gamma/kappa-dominated objective can in principle choose)
    is returned as computed, not clamped -- ``evaluate_plan_payback()``'s
    acceptance test already rejects it correctly without special-casing
    the sign here.
    """
    return (imbalance_before - imbalance_after) * payback_horizon_seconds


def evaluate_plan_payback(
    move_costs: Iterable[MoveCost],
    benefit_load_seconds: float,
    payback_ratio: float,
) -> PaybackResult:
    """Section 7.3: the aggregate acceptance test over a whole plan, plus
    the hard per-move ``max_single_move_duration`` rule.

    **A plan containing any reserve-violation-resolving move always
    passes the aggregate test.** Section 7's whole premise is weighing a
    move's cost against the *balance* benefit it buys -- but a move that
    resolves an active (C4)/(C5) violation is not optional in the way a
    balance-driven move is; it exists for safety, not for the imbalance
    reduction the benefit formula happens to compute for it (which can
    easily be zero or even net-zero on its own, e.g. a two-storage group
    where the only loaded disk simply changes which side it's on). Section
    13's "the reserve is never traded against balance" applies here just
    as much as it does to the drift/imbalance gates (`gates.py`) -- an
    operator does not get to decline a capacity emergency fix because it
    scores poorly against `migration.payback_ratio`. The hard per-move
    duration rule still applies regardless (it is an operational limit,
    not an economic one, and section 7.3 lists it as one of the rules
    applied "regardless of the aggregate test"), so a reserve-resolving
    move that would take days to wipe is still correctly flagged and
    still blocks `accepted`.

    The transient reserve invariant's own hard rule (section 7.3's third
    bullet) is not re-checked here -- ``schedule.py`` already enforces it
    before a move is ever scheduled, so by the time a ``ScheduledMove``
    reaches this module it has already passed that rule (AGENTS.md
    section 5: one implementation, not a second one here)."""
    move_costs = tuple(move_costs)
    total_cost = sum(mc.cost_load_seconds for mc in move_costs)
    has_reserve_override = any(mc.resolves_reserve_violation for mc in move_costs)
    aggregate_ok = has_reserve_override or benefit_load_seconds >= payback_ratio * total_cost
    rejected = tuple(mc.disk_key for mc in move_costs if mc.exceeds_max_duration)
    return PaybackResult(
        move_costs=move_costs,
        benefit_load_seconds=benefit_load_seconds,
        rejected_moves=rejected,
        aggregate_ok=aggregate_ok,
    )
