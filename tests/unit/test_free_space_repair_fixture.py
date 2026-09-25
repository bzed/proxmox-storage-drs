# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""IMPLEMENTATION_PLAN.md section 14.8's fixture, exercised through the real
production code paths (not just tests/fixtures/generate_expected.py's own
exhaustive-enumeration oracle). See tests/fixtures/free-space-repair.yaml
and its generated free-space-repair.expected.json for the proven-optimal
numbers this file's assertions are transcribed from -- do not hand-edit
either file; regenerate with `python3 tests/fixtures/generate_expected.py`.

A group whose I/O is already perfectly balanced (2.05/2.05/2.05) and whose
snapshot reserve is satisfied everywhere -- only the configured
`free_space.soft` is violated, on `packed` alone, by admin-placed foreign
volumes DRS does not manage. Proves, end to end, together:

- section 5.3.1's mandate: the engine repairs the shortfall even though
  doing so actively worsens I/O balance and would fail payback on economics
  alone (``test_end_to_end_repair_is_exempt_from_the_economic_test``);
- section 5.3 (C2)'s format eligibility: ``swapme`` accepts only ``raw``,
  which is what makes the repair a *two*-move plan with an *indirect*
  second move rather than a one-move one
  (``test_heuristic_finds_the_two_move_repair_not_the_one_move_format_violation``);
- section 7.3's revert test, including the indirect-repair case
  (``test_repair_markers_mark_both_moves_including_the_indirect_one``);
- section 8.1's hard-sweep order reversal
  (``test_schedule_order_reverses_between_the_hard_sweep_values``);
- section 5.3.1's own proof that the requirement is what makes the solver
  move at all (``test_counterfactual_free_space_soft_zero_moves_nothing``).
"""

from __future__ import annotations

from typing import Callable

import pytest

from proxmox_storage_drs.config import MigrationConfig, ObjectiveConfig
from proxmox_storage_drs.heuristic import run_heuristic
from proxmox_storage_drs.optimize import cbc_available, solve
from proxmox_storage_drs.payback import (
    compute_benefit_load_seconds,
    compute_move_cost,
    evaluate_plan_payback,
    executed_assignment,
    repair_markers,
)
from proxmox_storage_drs.reserve import total_shortfall_bytes
from proxmox_storage_drs.schedule import order_moves
from proxmox_storage_drs.topology import Disk, Group, Storage

TIB = 1 << 40
MIB = 1 << 20

BACKENDS = [
    pytest.param("cbc", marks=pytest.mark.skipif(not cbc_available(), reason="pulp not installed")),
]

# Section 12's defaults; delta_capacity_spread matters here (the whole
# fixture is a data-spread/free-space story, not an I/O-balance one).
OBJECTIVE = ObjectiveConfig(
    alpha_spread=1.0,
    beta_move_count=0.25,
    gamma_move_bytes_per_tib=0.05,
    kappa_vm_affinity=0.5,
    delta_capacity_spread=0.5,
    # Pinned explicitly, not inherited -- the same reason as
    # test_affinity_repair_fixture.py: `generate_expected.py`'s oracle
    # computes fragmentation() with `V` over movable disks only, and the
    # engine's own default is True (section 5.3 (C3)).
    affinity_counts_pinned_disks=False,
)

# saferemove off everywhere in the fixture -- see free-space-repair.yaml's
# own note on why (reproducible payback arithmetic, matching fc-tier1.yaml's
# convention).
MIGRATION = MigrationConfig(
    bwlimit_bytes_per_sec=200 * MIB,
    source_load_weight=1.0,
    target_load_weight=1.0,
    wipe_load_weight=1.0,
    account_saferemove_wipe=False,
    payback_horizon_seconds=31_536_000.0,  # 365d
    payback_ratio=10.0,
)

SOFT_30_PERCENT = round(3.0 * TIB)  # "30%" of the 10 TiB capacity below


def _make_storage(
    id_: str,
    *,
    foreign_used_tib: float,
    allowed_formats: frozenset[str],
    free_space_soft_bytes: int = SOFT_30_PERCENT,
    free_space_hard_bytes: int | None = None,
) -> Storage:
    return Storage(
        id=id_,
        capability_weight=1.0,
        reserve_factor=2.0,
        capacity_bytes=10 * TIB,
        used_bytes=0,
        foreign_used_bytes=round(foreign_used_tib * TIB),
        saferemove=False,
        saferemove_throughput_bytes_per_sec=None,
        free_space_soft_bytes=free_space_soft_bytes,
        free_space_hard_bytes=(
            free_space_hard_bytes if free_space_hard_bytes is not None else free_space_soft_bytes
        ),
        storage_type=("iscsi" if allowed_formats == frozenset({"raw"}) else "dir"),
        allowed_formats=allowed_formats,
    )


def _make_disk(key: str, size_tib: float, storage: str, format: str) -> Disk:
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
        pinned_reason=None,
    )


def _free_space_repair_group(
    *, free_space_soft_bytes: int = SOFT_30_PERCENT, hard_bytes: int | None = None
) -> Group:
    """tests/fixtures/free-space-repair.yaml, built as real topology
    objects. ``hard_bytes`` (None = "= soft", the default) sweeps section
    5.3.1's transient floor identically across all three storages, matching
    the fixture's own global-only `hard_sweep_tib` override."""
    storages = (
        _make_storage(
            "packed",
            foreign_used_tib=6.0,
            allowed_formats=frozenset({"raw", "qcow2"}),
            free_space_soft_bytes=free_space_soft_bytes,
            free_space_hard_bytes=hard_bytes,
        ),
        _make_storage(
            "roomy",
            foreign_used_tib=5.8,
            allowed_formats=frozenset({"raw", "qcow2"}),
            free_space_soft_bytes=free_space_soft_bytes,
            free_space_hard_bytes=hard_bytes,
        ),
        _make_storage(
            "swapme",
            foreign_used_tib=0.0,
            allowed_formats=frozenset({"raw"}),
            free_space_soft_bytes=free_space_soft_bytes,
            free_space_hard_bytes=hard_bytes,
        ),
    )
    disks = (
        _make_disk("601:scsi0", 0.5, "packed", "qcow2"),
        _make_disk("602:scsi0", 1.0, "packed", "qcow2"),
        _make_disk("603:scsi0", 1.0, "roomy", "raw"),
        _make_disk("604:scsi0", 1.0, "swapme", "raw"),
    )
    return Group(name="free-space-repair", storages=storages, disks=disks)


def _loads() -> dict[str, float]:
    return {"601:scsi0": 0.05, "602:scsi0": 2.00, "603:scsi0": 2.05, "604:scsi0": 2.05}


def _storage_of(assignment: dict[str, str]) -> Callable[[Disk], str]:
    """`total_shortfall_bytes()`'s `storage_of` wants a callable over a
    `Disk`, not a bare `dict.get` -- that would look up the `Disk` object
    itself as a key and silently miss every entry (section 5.1's
    assignment shape is always keyed by `Disk.key`, a string)."""
    return lambda d: assignment.get(d.key, d.current_storage)


# ------------------------------------------------------------------- the repair


def test_initial_state_matches_the_worked_example() -> None:
    """Section 14.8's own initial table: packed violates by 0.5 TiB
    (7.5 used + 3.0 required > 10.0), roomy/swapme are clean."""
    group = _free_space_repair_group()
    assert total_shortfall_bytes(group.storages, group.disks) == round(0.5 * TIB)


def test_heuristic_finds_the_two_move_repair_not_the_one_move_format_violation() -> None:
    """The direct repair (601 -> a storage with room) alone would prefer
    `swapme` (the smaller move, all else equal) if format eligibility did
    not forbid it -- (C2) is what turns this into the two-move plan section
    14.8 proves is optimal, with 603 -> swapme as the *indirect* repair
    that clears room on `roomy` for 601 to land there instead."""
    group = _free_space_repair_group()
    result = run_heuristic(group, _loads(), OBJECTIVE)

    assert result.assignment["601:scsi0"] == "roomy"
    assert result.assignment["603:scsi0"] == "swapme"
    assert result.assignment["602:scsi0"] == "packed"  # never moved
    assert result.assignment["604:scsi0"] == "swapme"  # never moved
    assert result.breakdown.moves == 2
    # Section 14.8: Sigma r_s: 0.5 -> 0.
    assert (
        total_shortfall_bytes(
            group.storages, group.disks, storage_of=_storage_of(result.assignment)
        )
        == 0
    )


@pytest.mark.parametrize("backend", BACKENDS)
def test_both_milp_backends_agree_with_the_heuristic(backend: str) -> None:
    group = _free_space_repair_group()
    result = solve(
        group, _loads(), OBJECTIVE, backend=backend, time_limit_seconds=10.0, mip_gap=0.0
    )
    assert result is not None
    assert result.assignment["601:scsi0"] == "roomy"
    assert result.assignment["603:scsi0"] == "swapme"
    assert result.breakdown.moves == 2


# ------------------------------------------------------------- the hard sweep


def test_schedule_order_reverses_between_the_hard_sweep_values() -> None:
    """Section 14.8's own proof that a transient dip below `soft` is a
    real, schedulable state: with `hard = soft` (the default `null`), the
    direct order (601 first) is transient-infeasible on `roomy` (7.3 used +
    a 3.0 TiB floor = 10.3 > 10), so the scheduler reverses it -- 603 first,
    emptying `roomy`, then 601. With `hard = "10%"` (1.0 TiB), the direct
    order is feasible as preferred (7.3 + 1.0*2 = 9.3 <= 10) and stays.
    Both orders reach the identical, fully compliant endpoint."""
    target_assignment = {
        "601:scsi0": "roomy",
        "602:scsi0": "packed",
        "603:scsi0": "swapme",
        "604:scsi0": "swapme",
    }

    default_hard_group = _free_space_repair_group()  # hard_bytes=None -> hard=soft
    default_hard_result = order_moves(default_hard_group, target_assignment, _loads(), OBJECTIVE)
    assert not default_hard_result.deadlocked
    assert [m.disk_key for m in default_hard_result.order] == ["603:scsi0", "601:scsi0"]

    ten_percent_hard_group = _free_space_repair_group(hard_bytes=round(1.0 * TIB))
    ten_percent_result = order_moves(ten_percent_hard_group, target_assignment, _loads(), OBJECTIVE)
    assert not ten_percent_result.deadlocked
    assert [m.disk_key for m in ten_percent_result.order] == ["601:scsi0", "603:scsi0"]

    # Both orders reach the same compliant endpoint -- the hard floor only
    # ever changes *ordering*, never the target itself (section 5.3.1).
    for result in (default_hard_result, ten_percent_result):
        assert (
            total_shortfall_bytes(
                default_hard_group.storages,
                default_hard_group.disks,
                storage_of=_storage_of(result.final_assignment),
            )
            == 0
        )


# ------------------------------------------------------------------- payback


def test_end_to_end_repair_is_exempt_from_the_economic_test() -> None:
    """Section 14.8's own worked numbers: cost ~15 729 load*s, benefit
    ~-1.23e8 load*s (this repair actively WORSENS I/O balance -- loads
    become 2.00/0.05/4.10), ratio far below `payback_ratio` on economics
    alone, yet the plan is accepted outright because it repairs the
    group's free-space shortfall (Sigma r_s: 0.5 TiB -> 0)."""
    group = _free_space_repair_group()
    loads = _loads()

    heuristic_result = run_heuristic(group, loads, OBJECTIVE)
    schedule_result = order_moves(group, heuristic_result.assignment, loads, OBJECTIVE)
    assert not schedule_result.deadlocked
    assert len(schedule_result.order) == 2

    storages_by_id = {s.id: s for s in group.storages}
    move_costs = [
        compute_move_cost(move, storages_by_id[move.from_storage], MIGRATION)
        for move in schedule_result.order
    ]
    assert not any(mc.exceeds_max_duration for mc in move_costs)
    total_cost = sum(mc.cost_load_seconds for mc in move_costs)
    assert total_cost == pytest.approx(15728.64, abs=0.1)  # 5242.88 + 10485.76

    from proxmox_storage_drs.heuristic import (
        evaluate_assignment,
        group_average_fill,
        group_average_utilization,
        raw_capacity_spread,
        raw_spread,
    )

    final_breakdown = evaluate_assignment(
        group,
        schedule_result.final_assignment,
        loads,
        OBJECTIVE,
        group_average_utilization(group, loads),
        group_average_fill(group),
    )
    benefit = compute_benefit_load_seconds(
        OBJECTIVE.alpha_spread,
        raw_spread(heuristic_result.initial_breakdown, OBJECTIVE.spread_metric),
        raw_spread(final_breakdown, OBJECTIVE.spread_metric),
        OBJECTIVE.delta_capacity_spread,
        raw_capacity_spread(heuristic_result.initial_breakdown),
        raw_capacity_spread(final_breakdown),
        MIGRATION.payback_horizon_seconds,
    )
    assert benefit < 0  # the repair worsens balance -- the point of the fixture
    assert benefit == pytest.approx(-123_114_070.59, rel=1e-3)

    excluded_disk_keys: frozenset[str] = frozenset(
        mc.disk_key for mc in move_costs if mc.exceeds_max_duration
    )
    executed_final = executed_assignment(
        group, schedule_result.final_assignment, excluded_disk_keys
    )
    current_shortfall = total_shortfall_bytes(group.storages, group.disks)
    final_shortfall = total_shortfall_bytes(
        group.storages, group.disks, storage_of=_storage_of(executed_final)
    )
    assert current_shortfall == round(0.5 * TIB)
    assert final_shortfall == 0

    payback_result = evaluate_plan_payback(
        move_costs, benefit, MIGRATION.payback_ratio, current_shortfall, final_shortfall
    )
    assert payback_result.ratio < 0  # would fail on economics alone
    assert not (benefit >= MIGRATION.payback_ratio * total_cost)  # sanity: economics really do fail
    assert payback_result.repair_exempt
    assert payback_result.aggregate_ok  # overridden by the repair mandate
    assert payback_result.accepted


def test_repair_markers_mark_both_moves_including_the_indirect_one() -> None:
    """601's move is a *direct* repair (its own source, `packed`, is what
    violates). 603's move is an *indirect* one -- `roomy` never violates
    anything itself, but holding 603 back leaves no room for 601 to land
    there, raising the plan's own final Sigma r_s from 0 to 0.3 TiB
    (section 14.8's own arithmetic: roomy at 7.3 used, short by 0.3)."""
    group = _free_space_repair_group()
    loads = _loads()
    heuristic_result = run_heuristic(group, loads, OBJECTIVE)
    schedule_result = order_moves(group, heuristic_result.assignment, loads, OBJECTIVE)

    markers = repair_markers(group, schedule_result.order, schedule_result.final_assignment)
    assert markers == {"601:scsi0": True, "603:scsi0": True}


# --------------------------------------------------------------- counterfactual


def test_counterfactual_free_space_soft_zero_moves_nothing() -> None:
    """Section 14.8's own proof that the requirement, and nothing else, is
    what makes the solver move: the identical cluster with
    `free_space.soft: 0` everywhere (the snapshot reserve alone is
    satisfied on every storage in this fixture) has "do nothing" as its
    optimum instead."""
    group = _free_space_repair_group(free_space_soft_bytes=0)
    assert total_shortfall_bytes(group.storages, group.disks) == 0  # no snapshot violation either

    result = run_heuristic(group, _loads(), OBJECTIVE)
    assert result.breakdown.moves == 0
    assert result.assignment == {
        "601:scsi0": "packed",
        "602:scsi0": "packed",
        "603:scsi0": "roomy",
        "604:scsi0": "swapme",
    }
