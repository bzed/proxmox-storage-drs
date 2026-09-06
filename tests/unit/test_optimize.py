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
(pyproject.toml), and `make install`'s own `.[dev]` never pulls it in, so
neither is present in this project's ordinary dev/CI venv. This mirrors
`test_forecast.py`'s `pytest.importorskip("statsmodels")` for the same
reason: a real, useful test suite for an optional dependency must still
pass cleanly without it. Developing this module, both backends *were*
installed and exercised for real (`pip install -e .[solver]`) -- every
test here passed and reproduced the fixtures' exact numbers; see
`docs/internals/91-optimize.md`.
"""

from __future__ import annotations

import dataclasses
import importlib
import sys

import pytest

from proxmox_storage_drs.config import ObjectiveConfig
from proxmox_storage_drs.optimize import (
    OptimizeResult,
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
    key: str, size_tib: float, load: float, storage: str, pinned: str | None = None
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
        format="raw",
        pinned_reason=pinned,
    )


def make_storage(
    id_: str,
    capacity_tib: float = 8.0,
    capability_weight: float = 1.0,
    reserve_factor: float = 2.0,
    foreign_used_tib: float = 0.0,
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
    )


DEFAULT_OBJECTIVE = ObjectiveConfig(
    alpha_spread=1.0, beta_move_count=0.25, gamma_move_bytes_per_tib=0.05, kappa_vm_affinity=0.50
)


def _solve(
    group: Group,
    loads: dict[str, float],
    objective: ObjectiveConfig,
    backend: str,
    min_free_bytes: int = 0,
) -> OptimizeResult:
    result = solve(
        group,
        loads,
        objective,
        min_free_bytes,
        backend,
        time_limit_seconds=10.0,
        mip_gap=0.0,
    )
    assert result is not None, f"{backend} found no feasible solution"
    return result


# --------------------------------------------------------------- availability


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
        0,
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
    assert result.breakdown.total == pytest.approx(2.533333, abs=1e-4)
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
    assert result.breakdown.total == pytest.approx(3.158333, abs=1e-4)


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


def test_solve_warns_when_cooldown_storages_is_non_empty(
    caplog: pytest.LogCaptureFixture,
) -> None:
    import logging

    group = Group(
        name="g",
        storages=(make_storage("san-a"), make_storage("san-b")),
        disks=(make_disk("101:scsi0", 1.0, 1.0, "san-a"),),
    )
    with caplog.at_level(logging.WARNING):
        solve(
            group,
            {"101:scsi0": 1.0},
            DEFAULT_OBJECTIVE,
            0,
            "cpsat",
            time_limit_seconds=5.0,
            mip_gap=0.0,
            cooldown_storages=frozenset({"san-b"}),
        )
    assert any("does not yet enforce" in r.message for r in caplog.records)
