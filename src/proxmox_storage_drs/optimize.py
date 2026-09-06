# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The MILP solver backends. See IMPLEMENTATION_PLAN.md section 5.5.

Two backends, CP-SAT (`ortools`) and CBC (via `pulp`), both solving the
section 5.3 constraint set with the **lexicographic** two-stage reserve
solve the plan recommends as the default: stage 1 minimizes
``Σ_s r_s`` (the total reserve shortfall) alone; stage 2 fixes that total
as a hard constraint and minimizes the real section 5.4 objective over
every assignment that does not exceed it. The reserve is then never
traded against balance at *any* weight -- there is no `P` to calibrate,
and `Σ r_s > 0` in the result provably means "physically impossible for
any assignment", never "not worth it". The single-stage big-M alternative
the plan also describes is not implemented here: it exists in the plan to
be *compared against* the lexicographic solve (see
``tests/fixtures/generate_expected.py``, which proves both against
exhaustive enumeration on ``reserve-tradeoff.yaml``), not as a second
runtime mode -- there is no `solver.*` config knob that selects it, and
the plan itself says "use the lexicographic solve by default" without
qualification.

Both backends solve for `x_{d,s}` alone (and, internally, whatever
auxiliary variables each needs to linearize the objective) and then hand
the resulting assignment to `heuristic.evaluate_assignment()` for the
*reported* :class:`~proxmox_storage_drs.heuristic.ObjectiveBreakdown` --
one implementation of the objective, shared by every backend including
this one (AGENTS.md section 5; `heuristic.py`'s own module docstring was
written anticipating exactly this). A MILP modeling mistake in this
module can at worst make the solver choose a *suboptimal* (but always
correctly *reported*) assignment; it can never make the tool *believe*
an assignment is better than it is, because the number that ends up in
`plan`'s output never comes from this module's own objective value.

**Failure is not exceptional here.** Section 13's own failure-mode table
says plainly: "Solver infeasible or timing out -> fall back to the
heuristic; never emit a partial/unvalidated assignment" -- with no
carve-out for a backend the operator explicitly asked for via
`solver.backend`. `solve()` therefore returns `None`, not an exception,
whenever the requested backend's library cannot be imported or the solve
produces no feasible incumbent within `solver.time_limit_seconds`; the
caller (`cli.py`) is what turns that into "try the next backend" or "fall
back to `heuristic.run_heuristic()`". Nothing here raises
:class:`~proxmox_storage_drs.exceptions.SolverError` -- that exception's
own docstring is "neither solver backend **could produce a feasible or
heuristic plan**", and the heuristic never fails, so this module has no
occasion to reach for it.

**Deliberately not implemented in this pass** (see
``docs/internals/91-optimize.md``):

- **The storage cooldown's repair-exemption asymmetry is not replicated
  here** (REVIEW.md S-04 fixed the gap this bullet used to describe: both
  MILP models now hard-fix `x_{d,s}=0` for `s in cooldown_storages` in
  *both* lexicographic stages, whenever `s` is not `d`'s current storage
  -- section 6's "accepts no new incoming moves", identical to
  `heuristic._descend()`'s own `target.id in cooldown_storages` check).
  What is *not* replicated is `heuristic._repair()`'s own exemption from
  that same cooldown when fixing a live (C4)/(C5) violation (section 13's
  reserve-override principle) -- the fix here is a single feasibility
  constraint applied uniformly to both stages, including stage 1's own
  reserve-shortfall minimization, so a cooldown storage stays unavailable
  even when it is the *only* way to resolve a violation, which the
  heuristic would still do. Replicating the exemption exactly needs
  either a second, repair-only relaxation of the same constraint or a
  restructured two-phase solve; this pass takes the simpler, uniform
  fix instead, on the judgment that a group both mid-violation and
  mid-cooldown on the one storage that could fix it is a narrow edge
  case, and reports the fixture's own numbers if it is ever hit (the
  slack is genuinely 0 with the cooldown storage excluded, so `plan`
  reports an accurate, if pessimistic-relative-to-the-heuristic,
  shortfall rather than a wrong one).
- **(C2) format-compatibility eligibility** -- the same gap
  `heuristic.py` already documents (`topology.Storage` does not expose
  storage type/format).
- **The plan's post-solve floating-point/scaled-objective agreement
  assertion** ("assert... recomputed in floating point agrees with the
  solver's value... a cheap guard against a scaling mistake") is not a
  separate check here: `evaluate_assignment()` *is* that recomputation,
  called unconditionally on every solve, and its result is what gets
  reported -- there is no second code path whose silent disagreement
  would go unnoticed. `test_optimize.py`'s cross-checks against the
  exhaustively-enumerated fixtures are the sharper version of the same
  guard: not just "internally consistent" but "agrees with a
  independently proven optimum". Section 5.5's other two assertions from
  the same paragraph -- every coefficient a non-zero integer wherever its
  unscaled weight is non-zero, and the objective's maximum magnitude
  under `2**62` -- *are* implemented, as `_assert_nonzero_when_weighted()`
  and `_assert_objective_magnitude_within_int64()` in
  `_cpsat_objective_terms()` (REVIEW.md S-09; CP-SAT's own integer
  -coefficient discipline is what these two guard, so neither applies to
  CBC's continuous, unscaled model).
"""

from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass
from typing import Any, Mapping

from proxmox_storage_drs.config import ObjectiveConfig
from proxmox_storage_drs.heuristic import (
    Assignment,
    ObjectiveBreakdown,
    evaluate_assignment,
    group_average_utilization,
    seed_assignment,
)
from proxmox_storage_drs.topology import Disk, Group

logger = logging.getLogger(__name__)

# Section 5.5's two scales: K for load-valued variables/constants, W for
# every objective weight. Size-valued quantities (Z_s, R_s, r_s, z_d, C_s,
# Uˢᵉˣᵗ, min_free_bytes) need no scale of their own -- they are rounded to
# whole MiB, already integral. `_RESERVE_FACTOR_SCALE` is this module's
# own addition, not named in the plan: `reserve_factor` (`f_s`) multiplies
# a *variable* (`Z_s`), not a constant, in (C5), so it cannot be folded
# into a single per-(d,s) coefficient the way section 5.5 folds `ℓ_d/c_s`
# -- it needs its own fixed-point scale to stay an integer *coefficient*
# in `SCALE·R_s ≥ round(f_s·SCALE)·Z_s` rather than a non-integer one.
_LOAD_SCALE = 1_000_000  # K
_WEIGHT_SCALE = 10_000  # W
_RESERVE_FACTOR_SCALE = 1_000_000
_BYTES_PER_MIB = 1 << 20
_BYTES_PER_TIB = 1 << 40


def _mib(size_bytes: int) -> int:
    """Round to whole MiB -- section 5.5's size unit for every MILP variable
    and constant (`Z_s`, `R_s`, `r_s`, `z_d`, `C_s`, `Uˢᵉˣᵗ`,
    `min_free_bytes`)."""
    return round(size_bytes / _BYTES_PER_MIB)


def _movable_disks(group: Group) -> tuple[Disk, ...]:
    """`D^mov` (section 5.3) -- identical filter to
    `heuristic._movable_disks()`, duplicated rather than imported since
    that name is private to that module (AGENTS.md section 5 is about one
    *implementation* per rule, not one importable helper for every trivial
    filter; every sibling test/module in this codebase already duplicates
    this exact one-liner rather than reach into another module's private
    names)."""
    return tuple(d for d in group.disks if d.pinned_reason is None)


def _pinned_by_storage(group: Group) -> dict[str, tuple[Disk, ...]]:
    by_storage: dict[str, list[Disk]] = {s.id: [] for s in group.storages}
    for disk in group.disks:
        if disk.pinned_reason is not None and disk.current_storage in by_storage:
            by_storage[disk.current_storage].append(disk)
    return {sid: tuple(disks) for sid, disks in by_storage.items()}


def _relevant_vmids(
    group: Group, movable: tuple[Disk, ...], objective: ObjectiveConfig
) -> list[int]:
    """(C3)'s `V`: vmids of `D^mov`, or of all of `D` when
    `objective.affinity_counts_pinned_disks` ranges the constraint over
    every disk instead (section 5.3's own text on that flag)."""
    disks = group.disks if objective.affinity_counts_pinned_disks else movable
    return sorted({d.vmid for d in disks})


def _pinned_of_vmid(group: Group, vmid: int, objective: ObjectiveConfig) -> tuple[Disk, ...]:
    if not objective.affinity_counts_pinned_disks:
        return ()
    return tuple(d for d in group.disks if d.vmid == vmid and d.pinned_reason is not None)


def cpsat_available() -> bool:
    try:
        import ortools.sat.python.cp_model  # noqa: F401
    except ImportError:
        return False
    return True


def cbc_available() -> bool:
    try:
        import pulp  # noqa: F401
    except ImportError:
        return False
    return True


def _lp_variable(pulp: Any, name: str, **kwargs: Any) -> Any:
    """``pulp.LpVariable(name, ...)`` -- not ``prob.add_variable(...)``,
    PuLP v4's replacement, which does not exist before pulp 3.3.1.
    Debian trixie packages pulp **2.7.0** (`python3-pulp`), and
    section 2.1 designates that as the primary, packaged CBC path, so
    `add_variable` would crash on the platform this project targets
    (REVIEW.md S-01 -- confirmed by wheel inspection across every pulp
    release from 2.7.0 to 3.3.2). Direct construction works unchanged on
    every one of those versions; on 3.3+ it also raises a v4-migration
    `DeprecationWarning` recommending `add_variable` instead, which this
    function suppresses explicitly -- adopting an API the target platform
    cannot provide, just to silence a warning about an alternative that
    does not yet apply there, would fix the wrong thing."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return pulp.LpVariable(name, **kwargs)


def _pulp_solve(pulp: Any, prob: Any, solver_cmd: Any) -> int | None:
    """``prob.solve(solver_cmd)``, returning ``None`` instead of raising
    when the CBC binary itself cannot be executed -- Debian splits it
    into `coinor-cbc`, a `Recommends`, not a `Depends`, of `python3-pulp`,
    so the library can be importable with no working solver behind it
    (REVIEW.md S-01). Matches this module's own contract (see the module
    docstring): a backend that cannot produce a plan returns ``None``,
    never an exception, so `cli.py`'s fallback cascade -- not a
    traceback -- is what an operator sees."""
    try:
        return int(prob.solve(solver_cmd))
    except pulp.PulpSolverError as exc:
        logger.warning(
            "solver.backend=cbc could not run the CBC solver: %s",
            exc,
            extra={"event": "optimize_backend_unavailable", "backend": "cbc"},
        )
        return None


@dataclass(frozen=True, slots=True)
class OptimizeResult:
    """One group's MILP solve. ``breakdown``/``initial_breakdown`` are
    computed by the identical `heuristic.evaluate_assignment()` every
    other backend uses -- see the module docstring. ``status`` is
    ``"optimal"`` (both stages proved optimal within `mip_gap`) or
    ``"feasible"`` (stage 2 hit `time_limit_seconds` with an incumbent in
    hand but did not prove the gap closed) -- `solve()` returns `None`
    instead of constructing this at all when even that much could not be
    achieved."""

    assignment: Assignment
    breakdown: ObjectiveBreakdown
    initial_breakdown: ObjectiveBreakdown
    backend: str  # "cpsat" | "cbc"
    status: str  # "optimal" | "feasible"


def solve(
    group: Group,
    load_by_key: Mapping[str, float],
    objective: ObjectiveConfig,
    min_free_bytes: int,
    backend: str,
    time_limit_seconds: float,
    mip_gap: float,
    cooldown_storages: frozenset[str] = frozenset(),
) -> OptimizeResult | None:
    """Solve one group with ``backend`` (``"cpsat"`` or ``"cbc"``).

    Returns ``None`` -- never raises -- when ``backend``'s library is not
    importable, or when the lexicographic solve cannot produce even one
    feasible incumbent within ``time_limit_seconds`` (section 13: "solver
    infeasible or timing out -> fall back to the heuristic"). The caller
    decides what "fall back" means; this function's only job is one
    group's solve attempt.
    """
    movable = _movable_disks(group)
    average_utilization = group_average_utilization(group, load_by_key)
    initial = seed_assignment(group)
    initial_breakdown = evaluate_assignment(
        group, initial, load_by_key, objective, min_free_bytes, average_utilization
    )

    if not movable:
        # Nothing this solver could change -- both backends would agree
        # trivially, so skip building a degenerate empty model.
        return OptimizeResult(
            assignment=initial,
            breakdown=initial_breakdown,
            initial_breakdown=initial_breakdown,
            backend=backend,
            status="optimal",
        )

    solvers = {"cpsat": _solve_cpsat, "cbc": _solve_cbc}
    if backend not in solvers:  # pragma: no cover - cli.py never passes anything else
        raise ValueError(f"optimize.solve() does not know backend {backend!r}")
    outcome = solvers[backend](
        group,
        movable,
        load_by_key,
        objective,
        min_free_bytes,
        time_limit_seconds,
        mip_gap,
        cooldown_storages,
    )

    if outcome is None:
        return None
    assignment, status = outcome
    breakdown = evaluate_assignment(
        group, assignment, load_by_key, objective, min_free_bytes, average_utilization
    )
    return OptimizeResult(
        assignment=assignment,
        breakdown=breakdown,
        initial_breakdown=initial_breakdown,
        backend=backend,
        status=status,
    )


def _no_feasible_solution(backend: str, group: Group, stage: str) -> None:
    logger.warning(
        "%s stage %s found no feasible solution within the time limit",
        backend,
        stage,
        extra={"event": "optimize_no_feasible_solution", "backend": backend, "group": group.name},
    )


# ------------------------------------------------------------------ CP-SAT


def _cpsat_feasibility_constraints(
    cp_model: Any,
    model: Any,
    group: Group,
    movable: tuple[Disk, ...],
    vmids: list[int],
    pinned_by_storage: dict[str, tuple[Disk, ...]],
    objective: ObjectiveConfig,
    min_free_bytes: int,
    size_bound: int,
    cooldown_storages: frozenset[str] = frozenset(),
) -> tuple[dict[Any, Any], dict[Any, Any], dict[Any, Any], dict[Any, Any]]:
    """(C1)/(C3)/(C4)/(C5) -- identical in both lexicographic stages, so
    built once per stage by both `_solve_cpsat()` calls to `build()`
    rather than duplicated inline (keeping that function's own branching
    within this project's complexity limit)."""
    x = {
        (d.key, s.id): model.NewBoolVar(f"x_{d.key}_{s.id}")
        for d in movable
        for s in group.storages
    }
    y = {(v, s.id): model.NewBoolVar(f"y_{v}_{s.id}") for v in vmids for s in group.storages}
    z = {s.id: model.NewIntVar(0, size_bound, f"Z_{s.id}") for s in group.storages}
    r = {s.id: model.NewIntVar(0, size_bound, f"R_{s.id}") for s in group.storages}
    slack = {s.id: model.NewIntVar(0, size_bound, f"r_{s.id}") for s in group.storages}

    for d in movable:
        model.Add(sum(x[d.key, s.id] for s in group.storages) == 1)
        model.AddHint(x[d.key, d.current_storage], 1)
        for s in group.storages:
            if s.id in cooldown_storages and s.id != d.current_storage:
                # Section 6: "a storage involved in a migration within
                # cooldown_per_storage accepts no new incoming moves" --
                # excludes a cooldown storage as a *destination* only,
                # exactly like `heuristic._descend()`'s own
                # `target.id in cooldown_storages` check. A disk already
                # resident there (`d.current_storage == s.id`) is left
                # free to stay -- the cooldown never blocks that.
                model.Add(x[d.key, s.id] == 0)

    for v in vmids:
        movable_of_v = [d for d in movable if d.vmid == v]
        pinned_of_v = _pinned_of_vmid(group, v, objective)
        for s in group.storages:
            for d in movable_of_v:
                model.Add(x[d.key, s.id] <= y[v, s.id])
            model.Add(
                y[v, s.id]
                <= sum(x[d.key, s.id] for d in movable_of_v)
                + sum(1 for d in pinned_of_v if d.current_storage == s.id)
            )
            if any(d.current_storage == s.id for d in pinned_of_v):
                model.Add(y[v, s.id] == 1)

    for s in group.storages:
        pinned_largest = max((_mib(d.size_bytes) for d in pinned_by_storage[s.id]), default=0)
        if pinned_largest:
            model.Add(z[s.id] >= pinned_largest)
        for d in movable:
            model.Add(z[s.id] >= _mib(d.size_bytes) * x[d.key, s.id])

    for s in group.storages:
        reserve_factor_scaled = round(s.reserve_factor * _RESERVE_FACTOR_SCALE)
        model.Add(_RESERVE_FACTOR_SCALE * r[s.id] >= reserve_factor_scaled * z[s.id])
        model.Add(r[s.id] >= _mib(min_free_bytes))
        pinned_used = sum(_mib(d.size_bytes) for d in pinned_by_storage[s.id])
        foreign_mib = _mib(s.foreign_used_bytes)
        model.Add(
            sum(_mib(d.size_bytes) * x[d.key, s.id] for d in movable)
            + pinned_used
            + foreign_mib
            + r[s.id]
            <= _mib(s.capacity_bytes) + slack[s.id]
        )

    return x, y, z, slack


def _cpsat_storage_lhs(
    s: Any,
    movable: tuple[Disk, ...],
    pinned_by_storage: dict[str, tuple[Disk, ...]],
    load_by_key: Mapping[str, float],
    x: dict[Any, Any],
) -> Any:
    """(C6)'s per-storage scaled load, section 5.5's `a_{d,s} = round(K *
    ell_d / c_s)` folded coefficients plus pinned disks' constant
    contribution -- the LHS both the L1 and minmax forms compare against."""
    pinned_load = sum(load_by_key.get(d.key, 0.0) for d in pinned_by_storage[s.id])
    pinned_scaled = (
        round(_LOAD_SCALE * pinned_load / s.capability_weight) if s.capability_weight else 0
    )
    coeffs = {
        d.key: (
            round(_LOAD_SCALE * load_by_key.get(d.key, 0.0) / s.capability_weight)
            if s.capability_weight
            else 0
        )
        for d in movable
    }
    return sum(coeffs[d.key] * x[d.key, s.id] for d in movable) + pinned_scaled


def _assert_nonzero_when_weighted(unscaled_weight: float, scaled: int, name: str) -> None:
    """Section 5.5: "assert... every coefficient is a non-zero integer
    wherever its unscaled weight is non-zero" -- the regression guard
    for the gamma trap (REVIEW.md S-09): `if gamma_scaled: terms.append(...)`
    a few lines above *silently drops* a coefficient that rounded to
    zero, which is exactly the failure shape this assertion exists to
    catch. Unreachable at the default weights after per-disk folding (a
    coefficient rounds to zero only for a sub-kilobyte disk), but "can't
    happen in practice" is what an assertion is for, not a reason to skip
    writing it."""
    assert not (unscaled_weight and not scaled), (
        f"{name} rounded to 0 despite a non-zero configured weight ({unscaled_weight!r}) -- "
        "section 5.5's coefficient-folding regression guard"
    )


def _assert_objective_magnitude_within_int64(
    beta_scaled: int,
    gamma_scaled_values: list[int],
    kappa_scaled: int,
    alpha_scaled: int,
    num_movable: int,
    num_vmids: int,
    num_storages: int,
    load_bound: int,
) -> None:
    """Section 5.5: "assert... the maximum objective magnitude is below
    2**62" (REVIEW.md S-09). A coarse, deliberately conservative upper
    bound -- every term at its own worst case simultaneously, which no
    real solution reaches -- computed directly from the same scaled
    coefficients and bounds the model already uses, not a second solve or
    a second pass over the built model. CP-SAT's own `IntVar`/objective
    domain is bounded at `2**63 - 1`; staying an order of magnitude under
    that is what makes overflow structurally impossible at any realistic
    cluster size, rather than merely unlikely."""
    worst_case = (
        beta_scaled * num_movable
        + sum(abs(g) for g in gamma_scaled_values)
        + abs(kappa_scaled) * num_vmids * num_storages
        + abs(alpha_scaled) * load_bound * num_storages
    )
    assert worst_case < 2**62, (
        f"objective magnitude bound {worst_case} exceeds 2**62 -- solver.* weights or "
        "disk/group sizes are large enough to risk CP-SAT integer overflow (section 5.5)"
    )


def _cpsat_objective_terms(
    model: Any,
    group: Group,
    movable: tuple[Disk, ...],
    vmids: list[int],
    pinned_by_storage: dict[str, tuple[Disk, ...]],
    load_by_key: Mapping[str, float],
    objective: ObjectiveConfig,
    u_star: float,
    load_bound: int,
    x: dict[Any, Any],
    y: dict[Any, Any],
) -> list[Any]:
    """Section 5.5's stage-2 objective coefficients -- (C6) plus the
    beta/gamma/kappa terms -- factored out of `_solve_cpsat()` to keep
    that function's own branching within this project's complexity limit."""
    terms: list[Any] = []
    beta_scaled = round(objective.beta_move_count * _WEIGHT_SCALE * _LOAD_SCALE)
    kappa_scaled = round(objective.kappa_vm_affinity * _WEIGHT_SCALE * _LOAD_SCALE)
    _assert_nonzero_when_weighted(objective.beta_move_count, beta_scaled, "beta_scaled")
    _assert_nonzero_when_weighted(objective.kappa_vm_affinity, kappa_scaled, "kappa_scaled")
    gamma_scaled_values: list[int] = []
    for d in movable:
        moved = 1 - x[d.key, d.current_storage]
        if beta_scaled:
            terms.append(beta_scaled * moved)
        gamma_scaled = round(
            objective.gamma_move_bytes_per_tib
            * _WEIGHT_SCALE
            * _LOAD_SCALE
            * (d.size_bytes / _BYTES_PER_TIB)
        )
        _assert_nonzero_when_weighted(
            objective.gamma_move_bytes_per_tib, gamma_scaled, f"gamma_scaled[{d.key}]"
        )
        gamma_scaled_values.append(gamma_scaled)
        if gamma_scaled:
            terms.append(gamma_scaled * moved)
    if kappa_scaled:
        for v in vmids:
            terms.append(kappa_scaled * (sum(y[v, s.id] for s in group.storages) - 1))

    alpha_scaled = round(objective.alpha_spread * _WEIGHT_SCALE)
    _assert_nonzero_when_weighted(objective.alpha_spread, alpha_scaled, "alpha_scaled")
    u_star_scaled = round(_LOAD_SCALE * u_star)
    if objective.spread_metric == "minmax":
        t = model.NewIntVar(0, load_bound, "t")
        for s in group.storages:
            model.Add(_cpsat_storage_lhs(s, movable, pinned_by_storage, load_by_key, x) <= t)
        if alpha_scaled:
            terms.append(alpha_scaled * t)
    else:
        e = {s.id: model.NewIntVar(0, load_bound, f"e_{s.id}") for s in group.storages}
        for s in group.storages:
            lhs = _cpsat_storage_lhs(s, movable, pinned_by_storage, load_by_key, x)
            model.Add(lhs - u_star_scaled <= e[s.id])
            model.Add(u_star_scaled - lhs <= e[s.id])
        if alpha_scaled:
            terms.append(alpha_scaled * sum(e.values()))

    _assert_objective_magnitude_within_int64(
        beta_scaled,
        gamma_scaled_values,
        kappa_scaled,
        alpha_scaled,
        len(movable),
        len(vmids),
        len(group.storages),
        load_bound,
    )
    return terms


def _solve_cpsat(
    group: Group,
    movable: tuple[Disk, ...],
    load_by_key: Mapping[str, float],
    objective: ObjectiveConfig,
    min_free_bytes: int,
    time_limit_seconds: float,
    mip_gap: float,
    cooldown_storages: frozenset[str] = frozenset(),
) -> tuple[Assignment, str] | None:
    try:
        from ortools.sat.python import cp_model
    except ImportError:
        logger.warning(
            "solver.backend=cpsat requested but ortools is not importable",
            extra={"event": "optimize_backend_unavailable", "backend": "cpsat"},
        )
        return None

    pinned_by_storage = _pinned_by_storage(group)
    vmids = _relevant_vmids(group, movable, objective)
    u_star = group_average_utilization(group, load_by_key)
    total_load = sum(load_by_key.get(d.key, 0.0) for d in group.disks)
    total_mib = sum(_mib(d.size_bytes) for d in group.disks)
    size_bound = max((_mib(s.capacity_bytes) for s in group.storages), default=0) + total_mib + 1
    load_bound = round(_LOAD_SCALE * (total_load + 1.0)) + 1

    def build() -> tuple[Any, dict[Any, Any], dict[Any, Any], dict[Any, Any]]:
        model = cp_model.CpModel()
        x, y, _z, slack = _cpsat_feasibility_constraints(
            cp_model,
            model,
            group,
            movable,
            vmids,
            pinned_by_storage,
            objective,
            min_free_bytes,
            size_bound,
            cooldown_storages,
        )
        return model, x, y, slack

    model1, _x1, _y1, slack1 = build()
    model1.Minimize(sum(slack1.values()))
    solver1 = cp_model.CpSolver()
    solver1.parameters.max_time_in_seconds = time_limit_seconds
    # Stage 1's whole point is a *proven* minimum -- "Σ r_s > 0 provably
    # means physically impossible", not "impossible within mip_gap"
    # (REVIEW.md S-07). `mip_gap` is stage 2's tolerance on the real
    # objective, not stage 1's on the reserve floor; forced to 0 here
    # regardless of what the operator configured, and only `OPTIMAL`
    # (never `FEASIBLE`, which would mean the gap was merely satisfied,
    # not proven closed) is accepted as this stage's answer. Cheap: this
    # stage is a near-feasibility problem that closes instantly on
    # realistic groups, per this module's own docstring.
    solver1.parameters.relative_gap_limit = 0.0
    status1 = solver1.Solve(model1)
    if status1 != cp_model.OPTIMAL:
        _no_feasible_solution("cpsat", group, "1 (reserve)")
        return None
    min_slack = round(solver1.ObjectiveValue())

    model2, x2, y2, slack2 = build()
    # `<=`, not `==`: stage 1 already proved `min_slack` is the true
    # minimum, so stage 2 can never find less of it -- `<=` is exactly as
    # tight as `==` there, but stays monotone-safe (never worse than the
    # incumbent) rather than brittle against a hypothetical floating
    # -point disagreement between the two solves (REVIEW.md S-07).
    model2.Add(sum(slack2.values()) <= min_slack)
    terms = _cpsat_objective_terms(
        model2,
        group,
        movable,
        vmids,
        pinned_by_storage,
        load_by_key,
        objective,
        u_star,
        load_bound,
        x2,
        y2,
    )
    model2.Minimize(sum(terms))
    solver2 = cp_model.CpSolver()
    solver2.parameters.max_time_in_seconds = time_limit_seconds
    solver2.parameters.relative_gap_limit = mip_gap
    status2 = solver2.Solve(model2)
    if status2 not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        _no_feasible_solution("cpsat", group, "2 (objective)")
        return None

    assignment: Assignment = {
        d.key: next(s.id for s in group.storages if solver2.Value(x2[d.key, s.id])) for d in movable
    }
    for disk in group.disks:
        if disk.pinned_reason is not None:
            assignment[disk.key] = disk.current_storage
    status = "optimal" if status2 == cp_model.OPTIMAL else "feasible"
    return assignment, status


# --------------------------------------------------------------------- CBC


def _cbc_feasibility_constraints(
    pulp: Any,
    prob: Any,
    group: Group,
    movable: tuple[Disk, ...],
    vmids: list[int],
    pinned_by_storage: dict[str, tuple[Disk, ...]],
    objective: ObjectiveConfig,
    min_free_bytes: int,
    cooldown_storages: frozenset[str] = frozenset(),
) -> tuple[dict[Any, Any], dict[Any, Any], dict[Any, Any], dict[Any, Any]]:
    """(C1)/(C3)/(C4)/(C5), continuous -- "direct transcription" per the
    plan's own words for this backend, no scaling needed. Factored out for
    the same reason as `_cpsat_feasibility_constraints()`."""
    x = {
        (d.key, s.id): _lp_variable(pulp, f"x_{d.key}_{s.id}", cat="Binary")
        for d in movable
        for s in group.storages
    }
    y = {
        (v, s.id): _lp_variable(pulp, f"y_{v}_{s.id}", cat="Binary")
        for v in vmids
        for s in group.storages
    }
    z = {s.id: _lp_variable(pulp, f"Z_{s.id}", lowBound=0) for s in group.storages}
    r = {s.id: _lp_variable(pulp, f"R_{s.id}", lowBound=0) for s in group.storages}
    slack = {s.id: _lp_variable(pulp, f"r_{s.id}", lowBound=0) for s in group.storages}

    for d in movable:
        prob += pulp.lpSum(x[d.key, s.id] for s in group.storages) == 1
        for s in group.storages:
            if s.id in cooldown_storages and s.id != d.current_storage:
                # See `_cpsat_feasibility_constraints()`'s identical
                # comment -- a cooldown storage is excluded as a
                # *destination* only, never for a disk already there.
                prob += x[d.key, s.id] == 0

    for v in vmids:
        movable_of_v = [d for d in movable if d.vmid == v]
        pinned_of_v = _pinned_of_vmid(group, v, objective)
        for s in group.storages:
            for d in movable_of_v:
                prob += x[d.key, s.id] <= y[v, s.id]
            prob += y[v, s.id] <= pulp.lpSum(x[d.key, s.id] for d in movable_of_v) + sum(
                1 for d in pinned_of_v if d.current_storage == s.id
            )
            if any(d.current_storage == s.id for d in pinned_of_v):
                prob += y[v, s.id] == 1

    for s in group.storages:
        pinned_largest = max((d.size_bytes for d in pinned_by_storage[s.id]), default=0)
        if pinned_largest:
            prob += z[s.id] >= pinned_largest / _BYTES_PER_MIB
        for d in movable:
            prob += z[s.id] >= (d.size_bytes / _BYTES_PER_MIB) * x[d.key, s.id]

    for s in group.storages:
        prob += r[s.id] >= s.reserve_factor * z[s.id]
        prob += r[s.id] >= min_free_bytes / _BYTES_PER_MIB
        pinned_used = sum(d.size_bytes for d in pinned_by_storage[s.id]) / _BYTES_PER_MIB
        foreign_mib = s.foreign_used_bytes / _BYTES_PER_MIB
        prob += (
            pulp.lpSum((d.size_bytes / _BYTES_PER_MIB) * x[d.key, s.id] for d in movable)
            + pinned_used
            + foreign_mib
            + r[s.id]
            <= s.capacity_bytes / _BYTES_PER_MIB + slack[s.id]
        )

    return x, y, z, slack


def _cbc_storage_load(
    pulp: Any,
    s: Any,
    movable: tuple[Disk, ...],
    pinned_by_storage: dict[str, tuple[Disk, ...]],
    load_by_key: Mapping[str, float],
    x: dict[Any, Any],
) -> Any:
    pinned_load = sum(load_by_key.get(d.key, 0.0) for d in pinned_by_storage[s.id])
    moved_load = pulp.lpSum(load_by_key.get(d.key, 0.0) * x[d.key, s.id] for d in movable)
    return (moved_load + pinned_load) / s.capability_weight if s.capability_weight else moved_load


def _cbc_objective_terms(
    pulp: Any,
    prob: Any,
    group: Group,
    movable: tuple[Disk, ...],
    vmids: list[int],
    pinned_by_storage: dict[str, tuple[Disk, ...]],
    load_by_key: Mapping[str, float],
    objective: ObjectiveConfig,
    u_star: float,
    x: dict[Any, Any],
    y: dict[Any, Any],
) -> list[Any]:
    terms: list[Any] = []
    for d in movable:
        moved = 1 - x[d.key, d.current_storage]
        if objective.beta_move_count:
            terms.append(objective.beta_move_count * moved)
        if objective.gamma_move_bytes_per_tib:
            terms.append(
                objective.gamma_move_bytes_per_tib * (d.size_bytes / _BYTES_PER_TIB) * moved
            )
    if objective.kappa_vm_affinity:
        for v in vmids:
            terms.append(
                objective.kappa_vm_affinity * (pulp.lpSum(y[v, s.id] for s in group.storages) - 1)
            )

    if objective.spread_metric == "minmax":
        t = _lp_variable(pulp, "t", lowBound=0)
        for s in group.storages:
            prob += _cbc_storage_load(pulp, s, movable, pinned_by_storage, load_by_key, x) <= t
        if objective.alpha_spread:
            terms.append(objective.alpha_spread * t)
    else:
        e = {s.id: _lp_variable(pulp, f"e_{s.id}", lowBound=0) for s in group.storages}
        for s in group.storages:
            lhs = _cbc_storage_load(pulp, s, movable, pinned_by_storage, load_by_key, x)
            prob += lhs - u_star <= e[s.id]
            prob += u_star - lhs <= e[s.id]
        if objective.alpha_spread:
            terms.append(objective.alpha_spread * pulp.lpSum(e.values()))
    return terms


def _solve_cbc(
    group: Group,
    movable: tuple[Disk, ...],
    load_by_key: Mapping[str, float],
    objective: ObjectiveConfig,
    min_free_bytes: int,
    time_limit_seconds: float,
    mip_gap: float,
    cooldown_storages: frozenset[str] = frozenset(),
) -> tuple[Assignment, str] | None:
    try:
        import pulp
    except ImportError:
        logger.warning(
            "solver.backend=cbc requested but pulp is not importable",
            extra={"event": "optimize_backend_unavailable", "backend": "cbc"},
        )
        return None

    pinned_by_storage = _pinned_by_storage(group)
    vmids = _relevant_vmids(group, movable, objective)
    u_star = group_average_utilization(group, load_by_key)
    # COIN_CMD, not the older PULP_CBC_CMD alias PuLP now deprecates -- same
    # CBC binary, same keyword arguments.
    solver_cmd = pulp.COIN_CMD(msg=0, timeLimit=time_limit_seconds, gapRel=mip_gap)
    # Stage 1's whole point is a *proven* minimum -- "Σ r_s > 0 provably
    # means physically impossible", not "impossible within mip_gap"
    # (REVIEW.md S-07). PuLP's own `LpStatus` collapses "proved optimal"
    # and "stopped because gapRel was satisfied" into the identical
    # "Optimal" string, so the only way to make that distinction real is
    # to force `gapRel=0` for this stage's own solve, regardless of what
    # the operator configured `solver.mip_gap` to -- that setting is
    # stage 2's tolerance on the real objective, not stage 1's on the
    # reserve floor. Cheap: this stage is a near-feasibility problem that
    # closes instantly on realistic groups, per this module's own
    # docstring.
    stage1_solver_cmd = pulp.COIN_CMD(msg=0, timeLimit=time_limit_seconds, gapRel=0.0)

    prob1 = pulp.LpProblem("stage1_reserve", pulp.LpMinimize)
    _x1, _y1, _z1, slack1 = _cbc_feasibility_constraints(
        pulp,
        prob1,
        group,
        movable,
        vmids,
        pinned_by_storage,
        objective,
        min_free_bytes,
        cooldown_storages,
    )
    prob1 += pulp.lpSum(slack1.values())
    status1 = _pulp_solve(pulp, prob1, stage1_solver_cmd)
    if status1 is None:
        return None
    if pulp.LpStatus[status1] not in ("Optimal",):
        _no_feasible_solution("cbc", group, "1 (reserve)")
        return None
    min_slack = sum(v.value() or 0.0 for v in slack1.values())

    prob2 = pulp.LpProblem("stage2_objective", pulp.LpMinimize)
    x2, y2, _z2, slack2 = _cbc_feasibility_constraints(
        pulp,
        prob2,
        group,
        movable,
        vmids,
        pinned_by_storage,
        objective,
        min_free_bytes,
        cooldown_storages,
    )
    # A small tolerance: CBC's own reported stage-1 slack already carries
    # solver rounding noise, and pinning it exactly can make stage 2
    # spuriously infeasible by a fraction of a MiB.
    prob2 += pulp.lpSum(slack2.values()) <= min_slack + 1e-6
    terms = _cbc_objective_terms(
        pulp,
        prob2,
        group,
        movable,
        vmids,
        pinned_by_storage,
        load_by_key,
        objective,
        u_star,
        x2,
        y2,
    )
    prob2 += pulp.lpSum(terms)
    status2 = _pulp_solve(pulp, prob2, solver_cmd)
    if status2 is None:
        return None
    if pulp.LpStatus[status2] not in ("Optimal",):
        _no_feasible_solution("cbc", group, "2 (objective)")
        return None

    assignment: Assignment = {}
    for d in movable:
        chosen = max(group.storages, key=lambda s: x2[d.key, s.id].value() or 0.0)
        assignment[d.key] = chosen.id
    for disk in group.disks:
        if disk.pinned_reason is not None:
            assignment[disk.key] = disk.current_storage
    return assignment, "optimal"
