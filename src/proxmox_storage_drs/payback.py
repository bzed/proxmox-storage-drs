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
- **The mirroring-phase-only reading of the section 7.3 saturation
  check.** ``compute_move_cost()`` evaluates ``L_during(s) <=
  saturation_ceiling * N_s`` once, at ``duration_mirror_seconds`` (the
  section header's own words: "push either endpoint above ... during
  *the mirror*"), charging both ``ω_src``/``ω_dst``. It does **not**
  additionally check the *draining* phase (``ω_wipe`` over
  ``duration_wipe_seconds``) as a second, separate check the way the full
  generalized in-flight-set model implies it could -- doing that exactly
  needs `schedule.py` to reason about which moves are actually
  overlapping at defer-check time, which it does not do (see
  `95-schedule.md`'s own "reasoning about concurrency at scheduling
  time" gap). A best-effort guard checked at its own literal, narrower
  reading is still strictly more than none; a fuller model is a real,
  separately-scoped follow-up. And, as ever: no group in this codebase's
  own dogfooding cluster has ``storages[].saturation_load`` set, which
  the plan itself says makes the check's total absence "fully
  supported... loses only this one advisory check" -- `N_s` is `None`
  skips it per endpoint, never assumed.
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
    # `exceeds_max_duration`/`saturation_deferred`) -- not set by
    # `compute_move_cost()` itself, which runs before that assignment is
    # known; defaults False until the caller (cli.py's plan builder) fills
    # it in via `dataclasses.replace()`.
    repair: bool = False
    # Section 7.3's best-effort defer check: `L_during(s) > saturation_ceiling
    # * N_s` for either endpoint, at the mirroring-phase horizon (see the
    # module docstring's note on why only that phase is checked). Defaults
    # `False` -- inactive unless the caller supplies `target`/`l_hat_src`/
    # `l_hat_dst` to `compute_move_cost()`, which every existing call site
    # predating this field does not.
    saturation_deferred: bool = False

    @property
    def duration_seconds(self) -> float:
        return self.duration_mirror_seconds + self.duration_wipe_seconds


@dataclass(frozen=True, slots=True)
class PaybackResult:
    """One plan's section 7.3 acceptance verdict.

    ``aggregate_ok`` (``benefit >= payback_ratio * Sum cost_d``, or
    unconditionally ``True`` when ``repair_exempt`` -- see
    ``evaluate_plan_payback()``) and ``accepted`` (``aggregate_ok`` **and**
    no individually-rejected or -deferred move) are kept separate so a
    caller can report *why* an otherwise-profitable plan was still
    rejected, rather than only a single bit.

    ``rejected_moves`` (the hard per-move duration rule) and
    ``deferred_moves`` (the best-effort saturation guard) are kept as two
    separate tuples, not merged into one, even though `cli.py` excludes
    both from execution identically -- section 7.3's own words draw the
    same distinction ("reject the move" vs. "defer the move to a later
    run"), and a caller reporting *why* a move did not run should be able
    to say which of the two happened, one hard and always active, the
    other best-effort and skipped entirely when a storage has no
    ``saturation_load`` configured.

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
    deferred_moves: tuple[str, ...] = ()  # disk keys failing the section 7.3 saturation guard
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
        return self.aggregate_ok and not self.rejected_moves and not self.deferred_moves


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


def mirror_duration_seconds(move: ScheduledMove, migration: MigrationConfig) -> float:
    """Section 7.1's ``duration_mirror_d = z_d / bwlimit`` (see the module
    docstring's note on ``headroom_src``/``headroom_dst``), factored out
    of :func:`compute_move_cost` so a caller can learn a move's own
    mirror duration *before* calling that function -- a real ordering
    dependency section 7.3's saturation guard introduces: the guard's own
    forecast horizon is this move's mirror duration, but
    ``compute_move_cost()`` is also what decides whether that guard's
    verdict makes the move deferred, so the caller must compute this
    first, fetch its forecasts, and only then call
    ``compute_move_cost(..., target=..., l_hat_src=..., l_hat_dst=...)``.
    """
    bwlimit = migration.bwlimit_bytes_per_sec
    return move.size_bytes / bwlimit if bwlimit else 0.0


def _saturation_deferred(
    source: Storage,
    target: Storage,
    migration: MigrationConfig,
    l_hat_src: float,
    l_hat_dst: float,
) -> bool:
    """Section 7.3's defer check, mirroring-phase only (see the module
    docstring): ``L_during(s) = L_hat_s(duration_mirror) + omega_role(s)``,
    checked against ``saturation_ceiling * N_s`` for each endpoint that
    has a ``saturation_load`` configured -- skipped entirely for one that
    does not ("fully supported... loses only this one advisory check").
    Factored out of :func:`compute_move_cost` purely to stay within this
    project's flake8 complexity limit."""
    if source.saturation_load is not None:
        l_during_src = l_hat_src + migration.source_load_weight
        if l_during_src > migration.saturation_ceiling * source.saturation_load:
            return True
    if target.saturation_load is not None:
        l_during_dst = l_hat_dst + migration.target_load_weight
        if l_during_dst > migration.saturation_ceiling * target.saturation_load:
            return True
    return False


def compute_move_cost(
    move: ScheduledMove,
    source: Storage,
    migration: MigrationConfig,
    target: Storage | None = None,
    l_hat_src: float = 0.0,
    l_hat_dst: float = 0.0,
) -> MoveCost:
    """Section 7.1's cost for one scheduled move, plus (only when
    ``target`` is given) section 7.3's saturation defer check.

    Only ``source`` is needed for the cost itself (not the target
    storage): `saferemove` is a property of where the volume is *removed
    from*, and ``migration.bwlimit_bytes_per_sec`` is the one global
    mirror-rate config value both ends share (see the module docstring's
    note on ``headroom_src``/``headroom_dst``).

    ``target``/``l_hat_src``/``l_hat_dst`` are the saturation guard's own
    inputs -- ``l_hat_src``/``l_hat_dst`` are the caller's own
    already-computed ``L_hat_s(duration_mirror)`` (section 10.1:
    `forecast.storage_upper_bound()`, summed over each endpoint's
    *currently* resident disks), left at their default of ``0.0`` and
    ``target=None`` (the check inactive) for every caller that has not
    computed a forecast at all -- this function stays pure either way,
    never fetching anything itself (the module docstring's own promise).
    """
    duration_mirror = mirror_duration_seconds(move, migration)

    duration_wipe = 0.0
    if migration.account_saferemove_wipe and source.saferemove:
        wipe = compute_wipe_duration_seconds(
            move.size_bytes, source.saferemove_throughput_bytes_per_sec
        )
        if wipe is not None:
            duration_wipe = wipe

    # Section 7.1: "a disk below migration.tiny_disk_bytes costs nothing" --
    # cost_load_seconds alone is zeroed, not duration_mirror/duration_wipe:
    # every hard per-move rule below (exceeds/deferred) still applies to a
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
    deferred = (
        _saturation_deferred(source, target, migration, l_hat_src, l_hat_dst)
        if target is not None
        else False
    )

    return MoveCost(
        disk_key=move.disk_key,
        duration_mirror_seconds=duration_mirror,
        duration_wipe_seconds=duration_wipe,
        cost_load_seconds=cost,
        exceeds_max_duration=exceeds,
        saturation_deferred=deferred,
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
    is every disk key a hard per-move rule has taken out --
    ``MoveCost.exceeds_max_duration`` or ``.saturation_deferred`` -- computed
    by the caller before this is called (both are per-move verdicts on
    ``cost_d``/``duration_d`` alone, independent of the exemption).

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
    section 5: one implementation, not a second one here)."""
    move_costs = tuple(move_costs)
    total_cost = sum(mc.cost_load_seconds for mc in move_costs)
    repair_exempt = final_shortfall_bytes < current_shortfall_bytes
    aggregate_ok = repair_exempt or benefit_load_seconds >= payback_ratio * total_cost
    rejected = tuple(mc.disk_key for mc in move_costs if mc.exceeds_max_duration)
    deferred = tuple(mc.disk_key for mc in move_costs if mc.saturation_deferred)
    return PaybackResult(
        move_costs=move_costs,
        benefit_load_seconds=benefit_load_seconds,
        rejected_moves=rejected,
        aggregate_ok=aggregate_ok,
        deferred_moves=deferred,
        repair_exempt=repair_exempt,
        reserve_shortfall_bytes_before=current_shortfall_bytes,
        reserve_shortfall_bytes_after=final_shortfall_bytes,
    )
