# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The MILP solver backends. See proxmox_storage_drs/optimize.py.

Cross-checked against the same IMPLEMENTATION_PLAN.md section 14 worked
example `test_heuristic.py` reproduces (the exact 3-move/2-move solutions
and their objective totals) -- phase 6's own "done when" is "matches or
beats the heuristic on the section 14 fixture; CP-SAT and CBC agree" --
and against `tests/fixtures/reserve-tradeoff.yaml`'s exhaustively-proven
lexicographic optimum, the one fixture built specifically to catch a
solver that fell for the single-stage big-M trap the plan warns against.

Every test that runs a real solve is parametrized over both backends
(`cpsat`, `cbc`) and skips whichever one's library is not importable --
`solver = ["ortools>=9.8", "pulp>=2.7"]` is an *optional* extra
(pyproject.toml), and `make install`'s own `.[dev]` venv never pulls it
in, so neither is present there. This mirrors `test_forecast.py`'s
`pytest.importorskip("statsmodels")` for the same reason: a real, useful
test suite for an optional dependency must still pass cleanly without it.
Developing this module, both backends *were* installed and exercised for
real (`pip install -e .[solver]`) -- every test here passed and
reproduced the fixtures' exact numbers; see `docs/internals/91-optimize.md`.
CI's own "test" job (`.github/workflows/tests.yml`) installs `ortools`
(there is no Debian package for it) specifically so these cpsat-marked
cases run there too, alongside `python3-pulp`/`coinor-cbc` from apt for
the cbc ones -- both backends are exercised on every push, this project's
own dev venv is just not one of the places that happens.
"""

from __future__ import annotations

import dataclasses
import importlib
import logging
import sys

import pytest

from proxmox_storage_drs.config import ObjectiveConfig
from proxmox_storage_drs.optimize import (
    OptimizeResult,
    _assert_nonzero_when_weighted,
    _assert_objective_magnitude_within_int64,
    _pinned_by_storage,
    _relevant_vmids,
    cbc_available,
    cpsat_available,
    solve,
)
from proxmox_storage_drs.topology import Disk, Group, Storage

TIB = 1 << 40
BACKENDS = [
    pytest.param(
        "cpsat", marks=pytest.mark.skipif(not cpsat_available(), reason="ortools not installed")
    ),
    pytest.param("cbc", marks=pytest.mark.skipif(not cbc_available(), reason="pulp not installed")),
]


def make_disk(
    key: str,
    size_tib: float,
    load: float,
    storage: str,
    pinned: str | None = None,
    format: str = "raw",
) -> Disk:
    vmid, device = key.split(":")
    return Disk(
        key=key,
        vmid=int(vmid),
        device=device,
        vm_name=f"vm{vmid}",
        node="pve01",
        size_bytes=round(size_tib * TIB),
        current_storage=storage,
        format=format,
        pinned_reason=pinned,
    )


def make_storage(
    id_: str,
    capacity_tib: float = 8.0,
    capability_weight: float = 1.0,
    reserve_factor: float = 2.0,
    foreign_used_tib: float = 0.0,
    free_space_soft_bytes: int = 0,
    free_space_hard_bytes: int | None = None,
    allowed_formats: frozenset[str] = frozenset({"raw", "qcow2"}),
) -> Storage:
    return Storage(
        id=id_,
        capability_weight=capability_weight,
        reserve_factor=reserve_factor,
        saturation_load=None,
        capacity_bytes=round(capacity_tib * TIB),
        used_bytes=0,
        foreign_used_bytes=round(foreign_used_tib * TIB),
        saferemove=False,
        saferemove_throughput_bytes_per_sec=None,
        free_space_soft_bytes=free_space_soft_bytes,
        free_space_hard_bytes=(
            free_space_hard_bytes if free_space_hard_bytes is not None else free_space_soft_bytes
        ),
        storage_type="dir",
        allowed_formats=allowed_formats,
    )


# delta_capacity_spread=0.0: this file's fixtures/expected assignments
# predate section 12's capacity-spread term -- see test_capacity_spread
# coverage for the dedicated (C7) MILP tests, which set their own non-zero
# delta explicitly.
DEFAULT_OBJECTIVE = ObjectiveConfig(
    alpha_spread=1.0,
    beta_move_count=0.25,
    gamma_move_bytes_per_tib=0.05,
    kappa_vm_affinity=0.50,
    delta_capacity_spread=0.0,
)


def _solve(
    group: Group,
    loads: dict[str, float],
    objective: ObjectiveConfig,
    backend: str,
    cooldown_storages: frozenset[str] = frozenset(),
) -> OptimizeResult:
    result = solve(
        group,
        loads,
        objective,
        backend,
        time_limit_seconds=10.0,
        mip_gap=0.0,
        cooldown_storages=cooldown_storages,
    )
    assert result is not None, f"{backend} found no feasible solution"
    return result


# --------------------------------------------------------------- availability


def test_cpsat_available_is_false_when_ortools_is_not_importable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`cpsat_available()`'s own ``except ImportError: return False`` --
    distinct from `test_solve_returns_none_when_the_library_is_unavailable`
    below, which exercises `_solve_cpsat()`'s independent import attempt,
    never this function. A plain ``import a.b.c`` statement raises
    ``ImportError`` on its own once ``sys.modules["a.b.c"]`` is the ``None``
    sentinel (no need for the ``delattr`` gymnastics the ``from ... import``
    case below requires), so this is coverable in any environment,
    `ortools` installed or not."""
    monkeypatch.setitem(sys.modules, "ortools.sat.python.cp_model", None)
    assert cpsat_available() is False


def test_cbc_available_is_false_when_pulp_is_not_importable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "pulp", None)
    assert cbc_available() is False


@pytest.mark.parametrize("backend", ["cpsat", "cbc"])
def test_solve_returns_none_when_the_library_is_unavailable(
    backend: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deliberately *not* parametrized over the skip-guarded `BACKENDS`
    list above -- this test's whole point is the "library not importable"
    path, which is exactly as meaningful (and exercised the same way, via
    `sys.modules`) whether or not the real library happens to be installed
    in this environment."""
    if backend == "cpsat" and cpsat_available():
        # `from ortools.sat.python import cp_model` resolves via
        # `getattr(sys.modules["ortools.sat.python"], "cp_model")` first --
        # a plain `sys.modules["...cp_model"] = None` alone is never
        # consulted unless that cached attribute is *also* cleared.
        # `importlib.import_module` (a runtime call, not a literal `import
        # ortools...` statement) guarantees the attribute exists first,
        # and gives mypy no static import of its own to resolve ortools's
        # heavy, optional type stubs for.
        importlib.import_module("ortools.sat.python.cp_model")
        monkeypatch.setitem(sys.modules, "ortools.sat.python.cp_model", None)
        monkeypatch.delattr(sys.modules["ortools.sat.python"], "cp_model", raising=False)
    elif backend == "cbc" and cbc_available():
        monkeypatch.setitem(sys.modules, "pulp", None)
    # else: the library is already not installed in this environment --
    # solve() must still return None, which is exactly what is asserted
    # below either way.
    group = Group(
        name="g",
        storages=(make_storage("san-a"), make_storage("san-b")),
        disks=(make_disk("101:scsi0", 1.0, 1.0, "san-a"),),
    )
    result = solve(
        group,
        {"101:scsi0": 1.0},
        DEFAULT_OBJECTIVE,
        backend,
        time_limit_seconds=1.0,
        mip_gap=0.0,
    )
    assert result is None


# --------------------------------------------------------------- section 14 fixture

_SECTION_14_DISKS = (
    ("101:scsi0", 2.0, 3.0, "san-a"),
    ("101:scsi1", 1.0, 1.0, "san-a"),
    ("102:scsi0", 1.5, 2.5, "san-a"),
    ("103:scsi0", 0.5, 0.4, "san-b"),
    ("104:scsi0", 1.0, 0.3, "san-b"),
    ("105:scsi0", 0.5, 0.2, "san-c"),
)


def section_14_group() -> Group:
    disks = tuple(
        make_disk(key, size, load, storage) for key, size, load, storage in _SECTION_14_DISKS
    )
    storages = (make_storage("san-a"), make_storage("san-b"), make_storage("san-c"))
    return Group(name="fc-tier1", storages=storages, disks=disks)


def section_14_loads() -> dict[str, float]:
    return {key: load for key, _size, load, _storage in _SECTION_14_DISKS}


@pytest.mark.parametrize("backend", BACKENDS)
def test_beta_025_reproduces_the_three_move_solution(backend: str) -> None:
    result = _solve(section_14_group(), section_14_loads(), DEFAULT_OBJECTIVE, backend)

    assert result.assignment == {
        "101:scsi0": "san-a",
        "101:scsi1": "san-b",
        "102:scsi0": "san-c",
        "103:scsi0": "san-b",
        "104:scsi0": "san-b",
        "105:scsi0": "san-b",
    }
    assert result.breakdown.moves == 3
    # Section 5.4's w_v reweights kappa: VM 101 (l_v=4.0, l_bar=7.4/5=1.48)
    # carries w=2.7027, raising the pre-section-12 2.533333 the same way
    # test_heuristic.py's identical fixture does (section 14.3).
    assert result.breakdown.total == pytest.approx(3.384685, abs=1e-4)
    assert not result.breakdown.reserve_statuses["san-a"].violated  # repaired
    assert result.backend == backend
    assert result.status == "optimal"


@pytest.mark.parametrize("backend", BACKENDS)
def test_beta_050_reproduces_the_two_move_solution(backend: str) -> None:
    objective = dataclasses.replace(DEFAULT_OBJECTIVE, beta_move_count=0.50)
    result = _solve(section_14_group(), section_14_loads(), objective, backend)

    assert result.assignment == {
        "101:scsi0": "san-a",
        "101:scsi1": "san-b",
        "102:scsi0": "san-c",
        "103:scsi0": "san-b",
        "104:scsi0": "san-b",
        "105:scsi0": "san-c",  # stays -- the third move is not worth it at beta=0.50
    }
    assert result.breakdown.moves == 2
    # This plan also splits VM 101 (section 14.3), carrying the same
    # w_101=2.7027-weighted fragmentation_term as the three-move plan above.
    assert result.breakdown.total == pytest.approx(4.009685, abs=1e-4)


# --------------------------------------------------------- tiny_disk_bytes (D^big)


@pytest.mark.parametrize("backend", BACKENDS)
def test_tiny_disk_bytes_lets_a_tiny_disk_reunite_with_its_vm_for_free(backend: str) -> None:
    """Section 5.4's D^big: at beta_move_count=1.0, moving `201:efidisk0`
    (1 MiB) to rejoin `201:scsi0` costs a full migration (1.0) against a
    fragmentation benefit of only kappa*w=0.5*1=0.5 -- not worth it, so
    with tiny_disk_bytes=0 (no exemption) the solver leaves it split. Above
    the 1 MiB disk's own size, the same move costs zero beta/gamma, so the
    kappa benefit alone makes it worth taking -- reproducing, in miniature,
    the live dogfooding failure section 5.4/7.2 exist to fix."""
    disks = (
        make_disk("201:scsi0", 1.0, 3.0, "san-a"),
        make_disk("201:efidisk0", 1 / (1024 * 1024), 0.0, "san-b"),  # 1 MiB
        make_disk("202:scsi0", 1.0, 3.0, "san-b"),
    )
    group = Group(name="g", storages=(make_storage("san-a"), make_storage("san-b")), disks=disks)
    loads = {"201:scsi0": 3.0, "201:efidisk0": 0.0, "202:scsi0": 3.0}
    objective = dataclasses.replace(DEFAULT_OBJECTIVE, beta_move_count=1.0)

    without_exemption = solve(
        group, loads, objective, backend, time_limit_seconds=10.0, mip_gap=0.0
    )
    assert without_exemption is not None
    assert without_exemption.assignment["201:efidisk0"] == "san-b"  # not worth a full migration

    with_exemption = solve(
        group,
        loads,
        objective,
        backend,
        time_limit_seconds=10.0,
        mip_gap=0.0,
        tiny_disk_bytes=2 * 1024 * 1024,  # 2 MiB -- above the 1 MiB efidisk0
    )
    assert with_exemption is not None
    assert with_exemption.assignment["201:efidisk0"] == "san-a"  # free to reunite
    assert with_exemption.breakdown.move_count_term == 0.0
    assert with_exemption.breakdown.bytes_moved_term == 0.0


# ---------------------------------------------------- capacity-spread (C7)/delta


@pytest.mark.parametrize("backend", BACKENDS)
def test_delta_050_at_the_default_beta_reproduces_the_two_move_solution(backend: str) -> None:
    """IMPLEMENTATION_PLAN.md section 14.3's "delta knob, demonstrated at
    the defaults": with delta_capacity_spread=0.5 (the section 12
    default) folded into beta=0.25's own three-move optimum, the third
    move (105:scsi0 san-c -> san-b) concentrates data enough that delta's
    penalty outweighs its I/O gain, so the two-move plan wins instead --
    both backends' own (C7) linearization must agree with the heuristic
    here, not just on beta's imbalance-only terms."""
    objective = dataclasses.replace(DEFAULT_OBJECTIVE, delta_capacity_spread=0.5)
    result = _solve(section_14_group(), section_14_loads(), objective, backend)

    assert result.assignment == {
        "101:scsi0": "san-a",
        "101:scsi1": "san-b",
        "102:scsi0": "san-c",
        "103:scsi0": "san-b",
        "104:scsi0": "san-b",
        "105:scsi0": "san-c",
    }
    assert result.breakdown.moves == 2
    # Section 14.2/14.3's exact F_before/F_after for this group.
    assert sum(result.initial_breakdown.fill_deviation.values()) == pytest.approx(
        2.153846, abs=1e-5
    )
    assert sum(result.breakdown.fill_deviation.values()) == pytest.approx(0.307692, abs=1e-5)
    assert result.breakdown.capacity_spread_term == pytest.approx(0.5 * 0.307692, abs=1e-5)


@pytest.mark.parametrize("backend", BACKENDS)
def test_delta_negligible_does_not_swamp_the_objective(backend: str) -> None:
    """REVIEW.md AA-01: CP-SAT's (C7) linearization once built `d_s` on a
    scale six orders of magnitude larger than every other term's, so even
    a negligible `delta_capacity_spread` acted, in effect, like ~100 --
    the exact "obvious formulation" trap section 5.5 warns the gamma term
    away from, reintroduced for (C7). At `delta=0.0001` the term's true
    contribution to the specified objective is ~3e-5, so the optimum is
    the delta=0 optimum (the three-move plan) -- both backends' (C7)
    linearization must agree with that, not silently prefer the two-move
    plan by amplifying delta's weight internally."""
    objective = dataclasses.replace(DEFAULT_OBJECTIVE, delta_capacity_spread=0.0001)
    result = _solve(section_14_group(), section_14_loads(), objective, backend)

    assert result.assignment == {
        "101:scsi0": "san-a",
        "101:scsi1": "san-b",
        "102:scsi0": "san-c",
        "103:scsi0": "san-b",
        "104:scsi0": "san-b",
        "105:scsi0": "san-b",
    }
    assert result.breakdown.moves == 3


@pytest.mark.parametrize("backend", BACKENDS)
def test_delta_zero_reproduces_the_beta_only_three_move_solution(backend: str) -> None:
    """The inverse check: explicitly disabling delta must restore beta's
    own three-move optimum exactly, confirming `delta_capacity_spread: 0`
    "disables the term" (section 5.4) all the way through both MILP
    backends, not just the heuristic."""
    objective = dataclasses.replace(DEFAULT_OBJECTIVE, delta_capacity_spread=0.0)
    result = _solve(section_14_group(), section_14_loads(), objective, backend)

    assert result.assignment == {
        "101:scsi0": "san-a",
        "101:scsi1": "san-b",
        "102:scsi0": "san-c",
        "103:scsi0": "san-b",
        "104:scsi0": "san-b",
        "105:scsi0": "san-b",
    }
    assert result.breakdown.moves == 3
    assert result.breakdown.capacity_spread_term == 0.0


# ------------------------------------------------------- reserve-tradeoff fixture


def reserve_tradeoff_group() -> Group:
    """`tests/fixtures/reserve-tradeoff.yaml`: both hot disks on `roomy`
    (E=10, no violation); moving either to `cramped` balances perfectly
    (E=0) but breaches (C5) there by 1 TiB. The lexicographic solve must
    stay put -- `reserve-tradeoff.expected.json`'s own
    `big_m_undersized_p_demo` shows an under-calibrated big-M (P=5) would
    wrongly move a disk instead."""
    disks = (
        make_disk("201:scsi0", 1.0, 5.0, "roomy"),
        make_disk("202:scsi0", 1.0, 5.0, "roomy"),
    )
    storages = (
        make_storage("roomy", capacity_tib=20.0),
        make_storage("cramped", capacity_tib=5.0, foreign_used_tib=3.0),
    )
    return Group(name="fc-conflict", storages=storages, disks=disks)


@pytest.mark.parametrize("backend", BACKENDS)
def test_reserve_tradeoff_lexicographic_solve_does_not_fall_for_the_big_m_trap(
    backend: str,
) -> None:
    objective = ObjectiveConfig(
        alpha_spread=1.0, beta_move_count=0.25, gamma_move_bytes_per_tib=0.05, kappa_vm_affinity=0.5
    )
    result = _solve(
        reserve_tradeoff_group(), {"201:scsi0": 5.0, "202:scsi0": 5.0}, objective, backend
    )

    # expected_move_count: 0, min_total_slack_tib: 0.0, expected_objective_nonreserve: 10.0
    assert result.breakdown.moves == 0
    assert not result.breakdown.reserve_statuses["roomy"].violated
    assert not result.breakdown.reserve_statuses["cramped"].violated
    total_nonreserve = (
        result.breakdown.imbalance_term
        + result.breakdown.move_count_term
        + result.breakdown.bytes_moved_term
        + result.breakdown.fragmentation_term
    )
    assert total_nonreserve == pytest.approx(10.0, abs=1e-4)


@pytest.mark.parametrize("backend", BACKENDS)
def test_stage_one_reserve_floor_ignores_a_generous_mip_gap(backend: str) -> None:
    """REVIEW.md S-07: stage 1's own proof that the reserve floor is
    achieved must not be relaxed by `solver.mip_gap` -- only stage 2's
    real objective may trade off within that gap. A generous gap here
    must not let either backend "cheat" by moving a disk into a
    cheaper-looking but reserve-violating placement -- `_solve()`'s own
    helper always passes `mip_gap=0.0`, so this calls `solve()` directly
    to exercise a gap the fixed stage-1 solve must ignore."""
    objective = ObjectiveConfig(
        alpha_spread=1.0, beta_move_count=0.25, gamma_move_bytes_per_tib=0.05, kappa_vm_affinity=0.5
    )
    result = solve(
        reserve_tradeoff_group(),
        {"201:scsi0": 5.0, "202:scsi0": 5.0},
        objective,
        backend,
        time_limit_seconds=10.0,
        mip_gap=0.5,
    )
    assert result is not None
    assert result.breakdown.moves == 0
    assert not result.breakdown.reserve_statuses["cramped"].violated


# ---------------------------------------------------------------------- pinning


@pytest.mark.parametrize("backend", BACKENDS)
def test_pinned_disk_never_moves_even_when_it_would_improve_the_objective(backend: str) -> None:
    disks = (
        make_disk("101:scsi0", 2.0, 3.0, "san-a", pinned="locked: backup"),
        make_disk("102:scsi0", 0.5, 0.1, "san-b"),
    )
    group = Group(name="g", storages=(make_storage("san-a"), make_storage("san-b")), disks=disks)
    result = _solve(group, {"101:scsi0": 3.0, "102:scsi0": 0.1}, DEFAULT_OBJECTIVE, backend)

    assert result.assignment["101:scsi0"] == "san-a"  # never touched despite being all the load


@pytest.mark.parametrize("backend", BACKENDS)
def test_pinned_disks_are_excluded_from_fragmentation_by_default(backend: str) -> None:
    """(C3): `affinity_counts_pinned_disks=False` (default) ranges the y
    -linking constraints over `D^mov` only, so a VM whose only "spread"
    comes from a pinned disk is not counted as fragmented -- mirrors
    `test_heuristic.py`'s identical-in-spirit test, proving the MILP's own
    y-variable modeling agrees with `evaluate_assignment()`'s independent
    computation, not just with itself."""
    disks = (
        make_disk("101:scsi0", 1.0, 1.0, "san-a", pinned="locked: backup"),
        make_disk("101:scsi1", 1.0, 1.0, "san-b"),
    )
    group = Group(name="g", storages=(make_storage("san-a"), make_storage("san-b")), disks=disks)
    result = _solve(group, {"101:scsi0": 1.0, "101:scsi1": 1.0}, DEFAULT_OBJECTIVE, backend)
    assert result.breakdown.fragmentation_term == 0.0

    counting_pinned = dataclasses.replace(DEFAULT_OBJECTIVE, affinity_counts_pinned_disks=True)
    counted = _solve(group, {"101:scsi0": 1.0, "101:scsi1": 1.0}, counting_pinned, backend)
    assert counted.breakdown.fragmentation_term == pytest.approx(0.50)


# ------------------------------------------------------------------------ swaps


@pytest.mark.parametrize("backend", BACKENDS)
def test_finds_the_perfectly_balanced_swap_when_no_single_move_is_feasible(backend: str) -> None:
    """The same capacity-locked scenario `test_heuristic.py`'s own swap
    test uses -- unlike the heuristic, the MILP does not need "swap" as a
    distinct search step, it just optimizes every `x_{d,s}` jointly, so
    this mainly proves (C4)/(C5)'s linearization does not itself block the
    only two-move improvement that exists."""
    disks = (
        make_disk("201:scsi0", 1.0, 1.0, "san-a"),
        make_disk("202:scsi0", 1.0, 1.0, "san-a"),
        make_disk("203:scsi0", 1.0, 3.0, "san-b"),
        make_disk("204:scsi0", 1.0, 3.0, "san-b"),
    )
    storages = (
        dataclasses.replace(make_storage("san-a", capacity_tib=2.5), reserve_factor=0.0),
        dataclasses.replace(make_storage("san-b", capacity_tib=2.5), reserve_factor=0.0),
    )
    group = Group(name="g", storages=storages, disks=disks)
    loads = {"201:scsi0": 1.0, "202:scsi0": 1.0, "203:scsi0": 3.0, "204:scsi0": 3.0}

    result = _solve(group, loads, DEFAULT_OBJECTIVE, backend)

    assert result.breakdown.imbalance_term == pytest.approx(0.0, abs=1e-6)
    assert result.assignment["201:scsi0"] != result.assignment["202:scsi0"]
    assert result.assignment["203:scsi0"] != result.assignment["204:scsi0"]


# --------------------------------------------------------------- spread_metric


@pytest.mark.parametrize("backend", BACKENDS)
def test_minmax_spread_metric_matches_the_heuristics_own_result(backend: str) -> None:
    minmax = dataclasses.replace(DEFAULT_OBJECTIVE, spread_metric="minmax")
    result = _solve(section_14_group(), section_14_loads(), minmax, backend)
    # heuristic.py's own minmax run on this fixture (test_heuristic.py does
    # not assert this directly, so this is this module's own cross-check:
    # the hottest storage's raw u_s after the solve must not exceed the
    # pre-solve hottest value of 6.5 -- a sanity bound, not a fragile exact
    # match to a search path unique to the other backend).
    assert max(result.breakdown.utilization.values()) <= 6.5 + 1e-6


# ------------------------------------------------------------- helper functions


def test_pinned_by_storage_groups_only_pinned_disks() -> None:
    disks = (
        make_disk("101:scsi0", 1.0, 1.0, "san-a", pinned="locked: backup"),
        make_disk("102:scsi0", 1.0, 1.0, "san-a"),
    )
    group = Group(name="g", storages=(make_storage("san-a"), make_storage("san-b")), disks=disks)
    result = _pinned_by_storage(group)
    assert [d.key for d in result["san-a"]] == ["101:scsi0"]
    assert result["san-b"] == ()


def test_relevant_vmids_defaults_to_movable_disks_only() -> None:
    disks = (
        make_disk("101:scsi0", 1.0, 1.0, "san-a", pinned="locked: backup"),
        make_disk("102:scsi0", 1.0, 1.0, "san-a"),
    )
    group = Group(name="g", storages=(make_storage("san-a"),), disks=disks)
    movable = tuple(d for d in disks if d.pinned_reason is None)
    assert _relevant_vmids(group, movable, DEFAULT_OBJECTIVE) == [102]
    counting_pinned = dataclasses.replace(DEFAULT_OBJECTIVE, affinity_counts_pinned_disks=True)
    assert _relevant_vmids(group, movable, counting_pinned) == [101, 102]


# --------------------------------------------------------------------- no-op


@pytest.mark.parametrize("backend", BACKENDS)
def test_solve_with_no_movable_disks_skips_the_model_entirely(backend: str) -> None:
    disks = (make_disk("101:scsi0", 1.0, 5.0, "san-a", pinned="locked: backup"),)
    group = Group(name="g", storages=(make_storage("san-a"), make_storage("san-b")), disks=disks)
    result = _solve(group, {"101:scsi0": 5.0}, DEFAULT_OBJECTIVE, backend)
    assert result.assignment == {"101:scsi0": "san-a"}
    assert result.status == "optimal"


# --------------------------------------------------------------------- cooldown


@pytest.mark.parametrize("backend", BACKENDS)
def test_solve_excludes_a_cooldown_storage_as_a_target_for_a_movable_disk(backend: str) -> None:
    """Mirrors `test_heuristic.py`'s
    `test_descend_blocks_new_arrivals_onto_a_cooldown_storage` exactly,
    against both MILP backends (REVIEW.md S-04): section 6's "a storage
    involved in a migration ... accepts no new incoming moves". Structural,
    not an exact-assignment check, so it holds regardless of which
    alternative the solver settles on."""
    group = section_14_group()
    loads = section_14_loads()
    original_storage = {key: storage for key, _s, _l, storage in _SECTION_14_DISKS}

    result = _solve(
        group, loads, DEFAULT_OBJECTIVE, backend, cooldown_storages=frozenset({"san-b"})
    )

    for disk_key, target in result.assignment.items():
        if target == "san-b":
            assert original_storage[disk_key] == "san-b"  # never a *new* arrival
    # The cooldown had a real effect: the baseline's own san-b arrival
    # (see test_beta_025_reproduces_the_three_move_solution) is blocked.
    assert result.assignment["101:scsi1"] != "san-b"


@pytest.mark.parametrize("backend", BACKENDS)
def test_solve_still_allows_a_disk_to_move_away_from_a_cooldown_storage(backend: str) -> None:
    """Mirrors `test_heuristic.py`'s
    `test_descend_still_allows_a_disk_to_move_away_from_a_cooldown_storage`:
    san-a is only ever a *source* in the section 14 three-move optimum, so
    putting it in cooldown must not change the result at all -- the
    cooldown blocks incoming moves, never outgoing ones (REVIEW.md S-04)."""
    result = _solve(
        section_14_group(),
        section_14_loads(),
        DEFAULT_OBJECTIVE,
        backend,
        cooldown_storages=frozenset({"san-a"}),
    )

    assert result.assignment == {
        "101:scsi0": "san-a",
        "101:scsi1": "san-b",
        "102:scsi0": "san-c",
        "103:scsi0": "san-b",
        "104:scsi0": "san-b",
        "105:scsi0": "san-b",
    }


# ------------------------------------------------------- (C2) format eligibility


@pytest.mark.parametrize("backend", BACKENDS)
def test_solve_never_places_a_disk_on_a_storage_that_cannot_hold_its_format(
    backend: str,
) -> None:
    """Section 5.3 (C2): `x_{d,s}=0` for a format-ineligible pair, fixed in
    the model rather than merely scored against -- `block` (raw-only, an
    LVM-shaped storage) would otherwise be the solver's obvious pick for
    `201:scsi0` (qcow2), since it alone would perfectly balance the group's
    heavily skewed load. The solver must never place it there, whatever it
    decides for the rest of the group."""
    block = make_storage("block", allowed_formats=frozenset({"raw"}))
    file_storage = make_storage("file", allowed_formats=frozenset({"raw", "qcow2"}))
    disks = (
        make_disk("201:scsi0", 1.0, 10.0, "file", format="qcow2"),
        make_disk("202:scsi0", 1.0, 0.1, "file", format="raw"),
    )
    group = Group(name="g", storages=(block, file_storage), disks=disks)
    loads = {"201:scsi0": 10.0, "202:scsi0": 0.1}

    result = _solve(group, loads, DEFAULT_OBJECTIVE, backend)

    assert result.assignment["201:scsi0"] == "file"  # never the raw-only storage


# ------------------------------------------------------- section 5.5 assertions


def test_assert_nonzero_when_weighted_passes_for_a_disabled_weight() -> None:
    _assert_nonzero_when_weighted(0.0, 0, "x")  # a deliberately disabled weight: no assertion


def test_assert_nonzero_when_weighted_passes_when_both_are_nonzero() -> None:
    _assert_nonzero_when_weighted(0.05, 500, "x")


def test_assert_nonzero_when_weighted_raises_on_the_gamma_trap() -> None:
    """Section 5.5's regression guard (REVIEW.md S-09): a non-zero
    configured weight whose *scaled, rounded* coefficient collapsed to 0
    is exactly the silent-drop failure `_cpsat_objective_terms()` would
    otherwise ship."""
    with pytest.raises(AssertionError, match="rounded to 0"):
        _assert_nonzero_when_weighted(0.05, 0, "gamma_scaled[101:scsi0]")


def test_assert_objective_magnitude_within_int64_passes_for_realistic_sizes() -> None:
    _assert_objective_magnitude_within_int64(
        beta_scaled=2_500_000,
        gamma_scaled_values=[500_000, 500_000],
        kappa_scaled_values=[5_000_000, 5_000_000],
        alpha_scaled=10_000,
        delta_scaled=5_000,
        num_big_movable=2,
        num_storages=3,
        load_bound=10_000_000,
        fill_bound_total=10_000_000,
    )


def test_assert_objective_magnitude_within_int64_raises_when_over_the_bound() -> None:
    with pytest.raises(AssertionError, match=r"2\*\*62"):
        _assert_objective_magnitude_within_int64(
            beta_scaled=0,
            gamma_scaled_values=[],
            kappa_scaled_values=[],
            alpha_scaled=2**60,
            delta_scaled=0,
            num_big_movable=0,
            num_storages=1000,
            load_bound=2**60,
            fill_bound_total=0,
        )


@pytest.mark.skipif(not cpsat_available(), reason="ortools not installed")
def test_gamma_trap_assertion_fires_end_to_end_for_a_sub_kilobyte_disk() -> None:
    """A disk small enough that `gamma_move_bytes_per_tib`'s own folded
    coefficient rounds to 0 despite a non-zero configured weight --
    exactly the case section 5.5's assertion exists to catch, exercised
    through the real `solve()` entry point rather than only the helper
    directly."""
    group = Group(
        name="g",
        storages=(make_storage("san-a"), make_storage("san-b")),
        disks=(make_disk("101:scsi0", 1e-10, 1.0, "san-a"),),
    )
    with pytest.raises(AssertionError, match="rounded to 0"):
        solve(
            group,
            {"101:scsi0": 1.0},
            DEFAULT_OBJECTIVE,
            "cpsat",
            time_limit_seconds=5.0,
            mip_gap=0.0,
        )


# ------------------------------------------- backend probing (section 2.3)


def test_a_missing_optional_solver_is_not_a_warning_under_auto(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The defect that prompted IMPLEMENTATION_PLAN.md section 2.3, in the
    operator's own words: "solver.backend=cpsat requested but ortools is not
    importable", at warning level, once per group, on every run of a cluster
    whose config says `solver.backend: auto` and never mentioned cpsat.

    Under `auto` this call is the cascade asking which optional dependency
    is installed, and "not this one" is the answer it exists to get.
    """
    from proxmox_storage_drs.optimize import _log_backend_unavailable

    with caplog.at_level(logging.DEBUG, logger="proxmox_storage_drs.optimize"):
        _log_backend_unavailable("cpsat", "ortools is not importable", probing=True)
    record = caplog.records[-1]
    assert record.levelno == logging.DEBUG
    assert record.probing is True  # type: ignore[attr-defined]
    # ... and it no longer claims the operator asked for this backend.
    assert "requested" not in record.getMessage()


def test_an_explicitly_configured_solver_that_is_missing_still_warns(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The other half: an operator who wrote `solver.backend: cpsat` and is
    silently not getting cpsat needs to hear about it."""
    from proxmox_storage_drs.optimize import _log_backend_unavailable

    with caplog.at_level(logging.DEBUG, logger="proxmox_storage_drs.optimize"):
        _log_backend_unavailable("cpsat", "ortools is not importable", probing=False)
    record = caplog.records[-1]
    assert record.levelno == logging.WARNING
    assert "solver.backend=cpsat" in record.getMessage()
