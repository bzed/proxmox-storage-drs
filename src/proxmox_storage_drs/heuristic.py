# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The dependency-free heuristic solver. See IMPLEMENTATION_PLAN.md section 5.5.

Seed from the current assignment, repair any (C5) reserve violation first
and unconditionally (never traded against balance -- section 13), then
descend the section 5.4 objective with single-disk moves and pairwise
swaps until nothing improves it or ``heuristic_iterations`` is reached.

``evaluate_assignment()`` is the one place the section 5.4 objective is
computed from an arbitrary candidate assignment -- built specifically so
``optimize.py`` (the MILP path, not yet written) can call the identical
function section 5.5 requires ("the heuristic must use the same
feasibility and objective functions as the MILP path so the two backends
are directly comparable"). Everything here is pure: no network I/O, and
no ``state.json`` access of its own -- ``run_heuristic()``'s
``cooldown_storages`` parameter is a plain, already-derived
``frozenset[str]`` its caller (`cli.py`, via
``state.active_storage_cooldowns()``) computes, not a `state.State` this
module reads itself.

**Implements** section 6's "a storage involved in a migration within
`cooldown_per_storage` accepts no new incoming moves": `_descend()`
excludes any storage in ``cooldown_storages`` as a move/swap
*destination* (never as a source -- a disk is always free to move away
from one). `_repair()` deliberately does **not** consult it at all; see
that function's own docstring for why a live (C5) violation is never
deferred for a storage cooldown, mirroring the reserve-override exemption
already established in `gates.py`/`payback.py`.

**Descend's neighbourhood is single-disk moves, pairwise swaps, and
whole-VM co-relocation** (a multi-disk VM's every movable disk moved to
one target storage together, in the same step -- see `_descend()`'s own
docstring for why this had to be added beyond the plan's own step 3
wording: without it, a multi-disk VM entirely on one overloaded storage
can leave descend with *zero* improving moves at all, confirmed live on a
real production cluster).

**Not implemented in this pass:** heuristic step 4, "polish" (reuniting a
fragmented VM when doing so does not worsen imbalance beyond
``imbalance_threshold``) for the *N-way rotation* case whole-VM
co-relocation above does not cover -- e.g. disk A needs S1→S2, disk B
needs S2→S3, and disk C needs S3→S1 in a cycle, no single disk's own move
improving on its own and no two disks belonging to the same VM. The
section 14 acceptance fixture's exact three-move and two-move solutions
are both reachable by repair+descend alone (verified in
``tests/unit/test_heuristic.py``): the objective's own ``kappa`` term
already makes descend prefer co-location whenever it does not cost more
than it is worth, which covers everything the fixture exercises. A real
gap, not forgotten, just not yet needed to pass the one fixture that
exists to prove this module correct. **Also not implemented:** (C2)'s *format-compatibility*
eligibility rule -- a different target-exclusion rule from the storage
cooldown above, not yet subsumed by it -- (a storage that cannot hold a
disk's format is fixed `x_{d,s}=0`) — ``topology.Storage`` does not yet
carry the type/format
information that rule needs (see ``topology.py``'s ``_default_format``,
which resolves it internally but does not expose it on `Storage`), so
every group storage is treated as an eligible target for every movable
disk today. The section 14 fixture is homogeneous (all three storages
accept the same format) and does not exercise this gap.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from proxmox_storage_drs.config import ObjectiveConfig
from proxmox_storage_drs.reserve import ReserveStatus, compute_reserve_status
from proxmox_storage_drs.topology import Disk, Group, Storage

# Every byte-valued objective term (`gamma`, and `r_s` for reporting) is
# expressed in TiB here, matching `objective.gamma_move_bytes_per_tib` and
# the section 14 worked example's own units -- this is the plain,
# floating-point heuristic objective, not CP-SAT's separately-scaled
# integer one (section 5.5), so there is no reason to use anything but the
# unit the config and the worked example already use.
_BYTES_PER_TIB = 1 << 40

Assignment = dict[str, str]  # topology.Disk.key -> storage id


@dataclass(frozen=True, slots=True)
class ObjectiveBreakdown:
    """The section 5.4 objective, evaluated for one candidate assignment,
    broken into its five terms -- kept separate rather than collapsed into
    only ``total`` because ``explain`` (``cli._render_group_explain_human()``'s
    "objective:" line) needs to show the arithmetic, not just the answer,
    and because tests cross-checking this against the section 14 worked
    example need each term individually."""

    imbalance_term: float  # alpha * (sum(e_s) [l1] or max(u_s) [minmax] -- objective.spread_metric)
    move_count_term: float  # beta * number of disks that moved
    bytes_moved_term: float  # gamma * TiB moved
    fragmentation_term: float  # kappa * sum(extra storages per VM)
    reserve_penalty_term: float  # objective.reserve_violation_penalty * TiB short
    spread_e: dict[str, float]  # storage id -> e_s = |u_s - u*|, for reporting (both metrics)
    utilization: dict[str, float]  # storage id -> u_s, for reporting and the minmax metric
    reserve_statuses: dict[str, ReserveStatus]  # storage id -> (C4)/(C5) at this assignment
    moved_disk_keys: frozenset[str]

    @property
    def total(self) -> float:
        return (
            self.imbalance_term
            + self.move_count_term
            + self.bytes_moved_term
            + self.fragmentation_term
            + self.reserve_penalty_term
        )

    @property
    def moves(self) -> int:
        return len(self.moved_disk_keys)


@dataclass(frozen=True, slots=True)
class HeuristicResult:
    """One group's heuristic solve. ``assignment`` is the final target
    placement (every disk, pinned or not -- a pinned disk's entry always
    equals its ``current_storage``, by construction, never by having been
    specially checked); ``initial`` is section 14.2's "before" for the same
    breakdown, so a caller can report the improvement without re-deriving
    it."""

    assignment: Assignment
    breakdown: ObjectiveBreakdown
    initial_breakdown: ObjectiveBreakdown
    repair_moves: int  # how many of `breakdown.moves` were forced by (C5)


def _movable_disks(group: Group) -> tuple[Disk, ...]:
    """`D^mov` (section 5.3): disks (C2) has not fixed in place. A pinned
    disk's assignment entry is never touched by any function in this
    module -- it is seeded to `current_storage` and every search step here
    iterates `_movable_disks()`, never `group.disks`, when proposing a
    change."""
    return tuple(d for d in group.disks if d.pinned_reason is None)


def seed_assignment(group: Group) -> Assignment:
    """Section 5.5 step 1: "seed with the current assignment (not from
    scratch -- we are minimizing *change*)." Every disk, pinned or not."""
    return {d.key: d.current_storage for d in group.disks}


def group_average_utilization(group: Group, load_by_key: Mapping[str, float]) -> float:
    """`u* = (Sum_d l_d) / (Sum_s c_s)` (C6) -- a constant under any
    reassignment of `D`'s own disks (section 5.3): moving a disk changes
    which storage its load counts toward, never the group's total load or
    total capability. Computed once per group, not once per candidate."""
    total_load = sum(load_by_key.get(d.key, 0.0) for d in group.disks)
    total_capability = sum(s.capability_weight for s in group.storages)
    return total_load / total_capability if total_capability else 0.0


def raw_spread(breakdown: ObjectiveBreakdown, spread_metric: str) -> float:
    """Section 7.2's unweighted ``E`` -- ``sum(e_s)`` (``"l1"``) or
    ``max(u_s)`` (``"minmax"``) -- as distinct from
    ``breakdown.imbalance_term``, which is that same quantity multiplied by
    ``objective.alpha_spread`` for section 5.4's *solver* objective.
    ``payback.py``'s ``compute_benefit_load_seconds()`` needs this raw
    quantity: section 7.2 defines ``E_before = Sum_s e_s`` with no alpha
    factor, so passing ``imbalance_term`` instead would make the payback
    ratio depend on a solver tuning knob rather than only on the imbalance
    reduction and migration cost a plan actually produces (REVIEW.md
    R-01)."""
    if spread_metric == "minmax":
        return max(breakdown.utilization.values()) if breakdown.utilization else 0.0
    return sum(breakdown.spread_e.values())


def evaluate_assignment(
    group: Group,
    assignment: Assignment,
    load_by_key: Mapping[str, float],
    objective: ObjectiveConfig,
    min_free_bytes: int,
    average_utilization: float,
) -> ObjectiveBreakdown:
    """Section 5.4's objective for one candidate ``assignment``.

    ``average_utilization`` is ``u*`` (see ``group_average_utilization``)
    -- a parameter, not recomputed here, since every candidate evaluated
    during a single heuristic run shares the same value and recomputing it
    from scratch on every call would be pure waste.

    ``objective.spread_metric`` picks (C6)'s two alternative imbalance
    forms (section 5.4): ``"l1"`` (default) is ``alpha * sum(e_s)``, the
    sum of every storage's absolute deviation from ``u*``; ``"minmax"`` is
    ``alpha * max(u_s)`` -- the plan's own "``t >= u_s`` for all s", the
    *raw* utilization of the single hottest storage, not the largest
    deviation from ``u*`` (those are not the same quantity: minmax is
    "indifferent to everything below" the hottest storage, which a
    deviation-based measure is not, since a storage far *below* u* would
    also produce a large deviation). ``spread_e``/``utilization`` are
    always both populated regardless of which metric is selected, so a
    caller (or a test) can inspect either view either way.
    """

    def storage_of(disk: Disk) -> str:
        return assignment.get(disk.key, disk.current_storage)

    reserve_statuses: dict[str, ReserveStatus] = {}
    spread_e: dict[str, float] = {}
    utilization: dict[str, float] = {}
    for storage in group.storages:
        status = compute_reserve_status(storage, group.disks, min_free_bytes, storage_of=storage_of)
        reserve_statuses[storage.id] = status
        load = sum(load_by_key.get(d.key, 0.0) for d in group.disks if storage_of(d) == storage.id)
        u_s = load / storage.capability_weight if storage.capability_weight else 0.0
        utilization[storage.id] = u_s
        spread_e[storage.id] = abs(u_s - average_utilization)

    if objective.spread_metric == "minmax":
        spread = max(utilization.values()) if utilization else 0.0
    else:
        spread = sum(spread_e.values())

    moved = frozenset(
        d.key for d in group.disks if assignment.get(d.key, d.current_storage) != d.current_storage
    )
    bytes_moved_tib = sum(d.size_bytes for d in group.disks if d.key in moved) / _BYTES_PER_TIB
    reserve_shortfall_tib = (
        sum(s.shortfall_bytes for s in reserve_statuses.values()) / _BYTES_PER_TIB
    )

    fragmentation_disks = (
        group.disks if objective.affinity_counts_pinned_disks else _movable_disks(group)
    )
    storages_per_vm: dict[int, set[str]] = {}
    for disk in fragmentation_disks:
        storages_per_vm.setdefault(disk.vmid, set()).add(storage_of(disk))
    fragmentation = sum(max(0, len(storages) - 1) for storages in storages_per_vm.values())

    return ObjectiveBreakdown(
        imbalance_term=objective.alpha_spread * spread,
        move_count_term=objective.beta_move_count * len(moved),
        bytes_moved_term=objective.gamma_move_bytes_per_tib * bytes_moved_tib,
        fragmentation_term=objective.kappa_vm_affinity * fragmentation,
        reserve_penalty_term=objective.reserve_violation_penalty * reserve_shortfall_tib,
        spread_e=spread_e,
        utilization=utilization,
        reserve_statuses=reserve_statuses,
        moved_disk_keys=moved,
    )


_RepairCandidate = tuple[float, Disk, str, bool, int]  # ratio, disk, target_id, worsens, used


def _best_repair_candidate(
    group: Group,
    assignment: Assignment,
    movable: tuple[Disk, ...],
    worst_id: str,
    current_total_shortfall: int,
    min_free_bytes: int,
) -> _RepairCandidate | None:
    """The inner search of one `_repair` iteration, factored out only to
    keep that function's own branching within the project's complexity
    limit -- picks, among every (disk on `worst_id`, other target) pair,
    the one with the highest group-wide shortfall reduction per byte, then
    not worsening the target, then the target with the least existing
    usage (section 5.5: "the feasible storage with the lowest u_s"; used
    bytes is a monotonic proxy for u_s here since every candidate compared
    is a trial where load itself has not changed)."""
    best: _RepairCandidate | None = None
    for disk in movable:
        if assignment.get(disk.key, disk.current_storage) != worst_id or disk.size_bytes <= 0:
            continue
        for target in group.storages:
            if target.id == worst_id:
                continue
            trial = dict(assignment)
            trial[disk.key] = target.id

            def trial_storage_of(d: Disk, _trial: Assignment = trial) -> str:
                return _trial.get(d.key, d.current_storage)

            trial_total = sum(
                compute_reserve_status(
                    s, group.disks, min_free_bytes, storage_of=trial_storage_of
                ).shortfall_bytes
                for s in group.storages
            )
            reduction = current_total_shortfall - trial_total
            if reduction <= 0:
                continue
            ratio = reduction / disk.size_bytes

            target_status = compute_reserve_status(
                target, group.disks, min_free_bytes, storage_of=trial_storage_of
            )
            candidate: _RepairCandidate = (
                ratio,
                disk,
                target.id,
                target_status.violated,
                target_status.managed_used_bytes,
            )
            if best is None or (ratio, not candidate[3], -candidate[4]) > (
                best[0],
                not best[3],
                -best[4],
            ):
                best = candidate
    return best


def _repair(
    group: Group,
    assignment: Assignment,
    min_free_bytes: int,
) -> tuple[Assignment, int]:
    """Section 5.5 step 2: "while any `s` violates (C5), move the disk from
    `s` that most reduces the violation per byte moved, to the feasible
    storage with the lowest `u_s`."

    Each candidate is judged by the reduction in the **group-wide total**
    shortfall, not the source storage's shortfall alone: moving a disk off
    a violating storage always reduces *that* storage's own shortfall (it
    has fewer bytes and, if anything, a smaller or equal largest-disk
    requirement), but it can just as easily create or worsen a violation
    on whichever storage receives it -- reducing the source's problem
    while making the group's total worse, or merely relocating it rather
    than repairing it. Requiring the *group* total to strictly decrease is
    what makes the loop's termination bound below actually correct, and
    is also what stops it from oscillating a disk back and forth between
    two storages that can never both hold it -- an earlier version of this
    function checked only the source and did exactly that (see
    ``test_repair_does_not_oscillate_when_no_target_can_fully_absorb_the_violation``).
    Bounded generously (movable disks times storages) rather than tightly,
    since "one repair per disk" is not actually how many steps a multi-
    storage violation can need; the strict-decrease requirement is what
    actually guarantees termination, this bound is only a defensive cap.

    **Never consults ``gates.cooldown_per_storage``.** A storage's
    cooldown exists to reduce churn/wear on a target that was just written
    to -- a purely economic, hysteresis-style throttle, exactly the kind
    section 13's "the reserve is never traded against balance" already
    overrides everywhere else in this codebase (`gates.py`'s reserve
    override bypasses drift/imbalance; `payback.py`'s aggregate test is
    exempted for a reserve-fixing plan). A storage actively needed to
    resolve a live (C4)/(C5) violation is not a candidate an operator gets
    to defer because it was recently written to -- see
    ``docs/internals/15-state.md`` for this reasoning applied to
    `_descend()`'s own, non-exempt use of the same cooldown data.
    """
    assignment = dict(assignment)
    movable = _movable_disks(group)
    repairs = 0
    max_iterations = len(movable) * max(1, len(group.storages)) + 1

    def storage_of(disk: Disk) -> str:
        return assignment.get(disk.key, disk.current_storage)

    for _ in range(max_iterations):
        statuses = {
            s.id: compute_reserve_status(s, group.disks, min_free_bytes, storage_of=storage_of)
            for s in group.storages
        }
        violating = [sid for sid, status in statuses.items() if status.violated]
        if not violating:
            break
        worst_id = max(violating, key=lambda sid: statuses[sid].shortfall_bytes)
        current_total = sum(status.shortfall_bytes for status in statuses.values())

        best = _best_repair_candidate(
            group, assignment, movable, worst_id, current_total, min_free_bytes
        )
        if best is None:
            break  # no repair move helps: report the residual as unfixable (caller's job)
        _ratio, disk, target_id, _worsens, _used = best
        assignment[disk.key] = target_id
        repairs += 1

    return assignment, repairs


def _vm_relocation_candidates(movable: tuple[Disk, ...]) -> dict[int, tuple[Disk, ...]]:
    """Movable disks grouped by ``vmid``, for the "co-relocate this whole
    VM" candidate in :func:`_descend` -- restricted to a vmid with **more
    than one** movable disk, since a single-disk VM's co-relocation is
    already exactly the plain single-disk-move candidate. Computed once,
    outside `_descend()`'s own iteration loop: it depends only on `group`,
    never on the current trial assignment."""
    by_vmid: dict[int, list[Disk]] = {}
    for disk in movable:
        by_vmid.setdefault(disk.vmid, []).append(disk)
    return {vmid: tuple(disks) for vmid, disks in by_vmid.items() if len(disks) > 1}


def _best_of(
    trials: Iterable[Assignment],
    group: Group,
    load_by_key: Mapping[str, float],
    objective: ObjectiveConfig,
    min_free_bytes: int,
    average_utilization: float,
    best_value: float,
    best_assignment: Assignment | None,
) -> tuple[float, Assignment | None]:
    """Evaluates every candidate in ``trials`` against the shared
    section 5.4 objective, keeping whichever (including the incumbent
    ``best_value``/``best_assignment`` passed in) scores lowest --
    factored out of `_descend()`'s three candidate-generating helpers
    below purely to stay within this project's flake8 complexity limit,
    and so all three score candidates through the exact same comparison."""
    for trial in trials:
        value = evaluate_assignment(
            group, trial, load_by_key, objective, min_free_bytes, average_utilization
        ).total
        if value < best_value:
            best_value = value
            best_assignment = trial
    return best_value, best_assignment


def _single_move_trials(
    assignment: Assignment,
    movable: tuple[Disk, ...],
    storages: tuple[Storage, ...],
    cooldown_storages: frozenset[str],
) -> Iterable[Assignment]:
    for disk in movable:
        here = assignment[disk.key]
        for target in storages:
            if target.id == here or target.id in cooldown_storages:
                continue
            trial = dict(assignment)
            trial[disk.key] = target.id
            yield trial


def _swap_trials(
    assignment: Assignment, movable: tuple[Disk, ...], cooldown_storages: frozenset[str]
) -> Iterable[Assignment]:
    for i, disk_a in enumerate(movable):
        for disk_b in movable[i + 1 :]:
            here_a = assignment[disk_a.key]
            here_b = assignment[disk_b.key]
            if here_a == here_b:
                continue  # no-op swap
            if here_a in cooldown_storages or here_b in cooldown_storages:
                continue  # the swap would send a disk to each of these
            trial = dict(assignment)
            trial[disk_a.key], trial[disk_b.key] = here_b, here_a
            yield trial


def _vm_relocation_trials(
    assignment: Assignment,
    vm_relocation_candidates: dict[int, tuple[Disk, ...]],
    storages: tuple[Storage, ...],
    cooldown_storages: frozenset[str],
) -> Iterable[Assignment]:
    for disks in vm_relocation_candidates.values():
        here = {assignment[d.key] for d in disks}
        for target in storages:
            if here == {target.id} or target.id in cooldown_storages:
                continue
            trial = dict(assignment)
            for disk in disks:
                trial[disk.key] = target.id
            yield trial


def _descend(
    group: Group,
    assignment: Assignment,
    load_by_key: Mapping[str, float],
    objective: ObjectiveConfig,
    min_free_bytes: int,
    average_utilization: float,
    max_iterations: int,
    cooldown_storages: frozenset[str] = frozenset(),
) -> Assignment:
    """Section 5.5 step 3: repeatedly apply whichever single-disk move,
    pairwise swap, or whole-VM co-relocation (below) most improves the
    full objective; stop when nothing does, or after
    ``heuristic_iterations``. Swaps matter (the plan is explicit): when
    every storage is near its cap, no single move is feasible-and
    -improving, and only an exchange of two disks can help.

    **Whole-VM co-relocation, beyond what the plan's own step 3 names.**
    Moving every one of a multi-disk VM's movable disks to the same target
    storage together is *not* reachable by single-disk moves or pairwise
    swaps alone whenever the objective's own ``kappa`` (VM affinity) term
    is large enough to make every individual disk's move a net loss on its
    own -- moving one disk of an N-disk VM temporarily *fragments* it
    (paying `kappa`) before a second, third, ... move could reunite it
    elsewhere, and `_descend()` only ever accepts a single step that is
    *itself* improving. A swap does not help either: it exchanges two
    disks' positions with *each other*, never relocates a whole group of
    disks to a third storage together. Confirmed live on a real,
    heavily-imbalanced production cluster (two-disk VM entirely on one
    storage, `kappa_vm_affinity` at its default `0.50`): without this
    candidate, `_descend()` found *zero* improving moves at all and left
    the cluster at its full initial imbalance, even though relocating that
    one VM's disks together is a large, unambiguous improvement CP-SAT
    finds immediately -- the "dependency-free ... path for very large
    groups" the plan describes this heuristic as must not be able to get
    stuck this badly. Tried in the same "evaluate every candidate, apply
    the best one" step as single-disk moves and swaps, so it is scored by
    exactly the same objective and cannot itself ever choose a worse
    assignment.

    ``cooldown_storages`` (section 6: "a storage involved in a migration
    within `cooldown_per_storage` accepts no new incoming moves") excludes
    a storage as a *destination* only -- a disk already on one is free to
    move away, a swap involving one is skipped only because a swap always
    sends a disk *to* both storages it touches, and a whole-VM
    co-relocation is skipped as a target the same way for the same
    reason. Deliberately not consulted by ``_repair()`` -- see that
    function's own docstring for why a (C5) repair move ignores this the
    same way it ignores every other form of hysteresis (section 13)."""
    assignment = dict(assignment)
    movable = _movable_disks(group)
    vm_relocation_candidates = _vm_relocation_candidates(movable)
    current = evaluate_assignment(
        group, assignment, load_by_key, objective, min_free_bytes, average_utilization
    ).total

    for _ in range(max_iterations):
        best_value: float = current
        best_assignment: Assignment | None = None

        for trials in (
            _single_move_trials(assignment, movable, group.storages, cooldown_storages),
            _swap_trials(assignment, movable, cooldown_storages),
            _vm_relocation_trials(
                assignment, vm_relocation_candidates, group.storages, cooldown_storages
            ),
        ):
            best_value, best_assignment = _best_of(
                trials,
                group,
                load_by_key,
                objective,
                min_free_bytes,
                average_utilization,
                best_value,
                best_assignment,
            )

        if best_assignment is None:
            break
        assignment = best_assignment
        current = best_value

    return assignment


def run_heuristic(
    group: Group,
    load_by_key: Mapping[str, float],
    objective: ObjectiveConfig,
    min_free_bytes: int,
    heuristic_iterations: int = 5000,
    cooldown_storages: frozenset[str] = frozenset(),
) -> HeuristicResult:
    """Section 5.5's four-step heuristic (minus "polish"; see the module
    docstring), producing a :class:`HeuristicResult` for one group.

    ``load_by_key`` is ``loadmodel.GroupLoad.load_by_disk_key()``;
    ``min_free_bytes`` is ``config.snapshot_reserve.min_free_bytes``.
    ``cooldown_storages`` -- storage ids currently within
    ``gates.cooldown_per_storage`` (``state.active_storage_cooldowns()``,
    bare ids for this group) -- is passed to ``_descend()`` only, never to
    ``_repair()``; see ``_repair()``'s own docstring for why a (C5) repair
    move is never blocked by it.
    """
    average_utilization = group_average_utilization(group, load_by_key)
    initial = seed_assignment(group)
    initial_breakdown = evaluate_assignment(
        group, initial, load_by_key, objective, min_free_bytes, average_utilization
    )

    repaired, repair_moves = _repair(group, initial, min_free_bytes)
    final = _descend(
        group,
        repaired,
        load_by_key,
        objective,
        min_free_bytes,
        average_utilization,
        heuristic_iterations,
        cooldown_storages,
    )
    final_breakdown = evaluate_assignment(
        group, final, load_by_key, objective, min_free_bytes, average_utilization
    )
    return HeuristicResult(
        assignment=final,
        breakdown=final_breakdown,
        initial_breakdown=initial_breakdown,
        repair_moves=repair_moves,
    )
