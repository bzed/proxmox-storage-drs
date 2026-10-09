# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""IMPLEMENTATION_PLAN.md section 14.9's fixture, exercised through the real production code
paths (not just tests/fixtures/generate_expected.py's exhaustive-enumeration oracle). See
tests/fixtures/large-vm-split.yaml and its generated large-vm-split.expected.json for the
proven numbers this file's assertions are transcribed from -- do not hand-edit either file;
regenerate with `python3 tests/fixtures/generate_expected.py`.

A balanced group, every reserve satisfied, one 10 TiB VM whole on one storage: only the split
rule (section 5.3.3), its gate (section 6) and its payback term (section 7.2) can move anything.
"""

from __future__ import annotations

import dataclasses

import pytest

from proxmox_storage_drs.config import MigrationConfig, ObjectiveConfig
from proxmox_storage_drs.gates import split_gate
from proxmox_storage_drs.heuristic import (
    active_split_caps,
    compute_vm_weights,
    evaluate_assignment,
    group_average_fill,
    group_average_utilization,
    raw_affinity_debt,
    raw_capacity_spread,
    raw_split_excess_tib,
    raw_spread,
    run_heuristic,
)
from proxmox_storage_drs.optimize import cbc_available, solve
from proxmox_storage_drs.payback import (
    compute_benefit_load_seconds,
    compute_move_cost,
    evaluate_plan_payback,
)
from proxmox_storage_drs.reserve import compute_reserve_status, vm_footprints_bytes
from proxmox_storage_drs.schedule import order_moves
from proxmox_storage_drs.topology import Disk, Group, Storage

TIB = 1 << 40
MIB = 1 << 20

BACKENDS = [
    pytest.param("cbc", marks=pytest.mark.skipif(not cbc_available(), reason="pulp not installed")),
]

# delta = 0 keeps data spread from doing any of the work (section 14.9).
OBJECTIVE = ObjectiveConfig(
    alpha_spread=1.0,
    beta_move_count=0.25,
    gamma_move_bytes_per_tib=0.05,
    kappa_vm_affinity=0.5,
    delta_capacity_spread=0.0,
    mu_vm_split_per_tib=1.0,
    affinity_counts_pinned_disks=False,
)
MIGRATION = MigrationConfig(
    bwlimit_bytes_per_sec=200 * MIB,
    account_saferemove_wipe=False,
    payback_horizon_seconds=31_536_000.0,
    payback_ratio=10.0,
    tiny_disk_bytes=0,
)


def _storage(id_: str) -> Storage:
    return Storage(
        id=id_,
        capability_weight=1.0,
        reserve_factor=2.0,
        capacity_bytes=40 * TIB,
        used_bytes=0,
        foreign_used_bytes=0,
        saferemove=False,
        saferemove_throughput_bytes_per_sec=None,
        free_space_soft_bytes=0,
        free_space_hard_bytes=0,
        storage_type="dir",
        allowed_formats=frozenset({"raw", "qcow2"}),
    )


def _disk(key: str, size_tib: int, storage: str) -> Disk:
    vmid, device = key.split(":")
    return Disk(
        key=key,
        vmid=int(vmid),
        device=device,
        vm_name=f"vm{vmid}",
        node="pve01",
        size_bytes=size_tib * TIB,
        current_storage=storage,
        format="raw",
        pinned_reason=None,
    )


def _group(
    split_vm_footprint_bytes: int | None = 2 * TIB, placement: dict[str, str] | None = None
) -> Group:
    placement = placement or {}
    disks = tuple(
        _disk(f"701:scsi{i}", 2, placement.get(f"701:scsi{i}", "st-a")) for i in range(5)
    ) + (
        _disk("702:scsi0", 1, "st-a"),
        _disk("703:scsi0", 1, "st-b"),
        _disk("704:scsi0", 1, "st-c"),
    )
    return Group(
        name="large-vm-split",
        storages=(_storage("st-a"), _storage("st-b"), _storage("st-c")),
        disks=disks,
        split_vm_footprint_bytes=split_vm_footprint_bytes,
    )


LOADS = {
    **{f"701:scsi{i}": 0.0 for i in range(5)},
    "702:scsi0": 1.0,
    "703:scsi0": 1.0,
    "704:scsi0": 1.0,
}


def _footprints(group: Group, assignment: dict[str, str]) -> list[int]:
    def storage_of(d: Disk) -> str:
        return assignment.get(d.key, d.current_storage)

    return sorted(
        (
            vm_footprints_bytes(group.disks, s.id, storage_of=storage_of).get(701, 0)
            for s in group.storages
        ),
        reverse=True,
    )


def test_every_reserve_is_satisfied_so_only_the_split_rule_can_act() -> None:
    group = _group()
    for storage in group.storages:
        assert not compute_reserve_status(storage, group.disks).violated
    status = compute_reserve_status(group.storages[0], group.disks)
    assert status.largest_footprint_vmid == 701
    assert status.largest_footprint_bytes == 10 * TIB
    assert status.required_reserve_bytes == 20 * TIB


def test_vm_701_is_in_v_split_with_weight_one() -> None:
    group = _group()
    assert active_split_caps(group, OBJECTIVE) == {701: 2 * TIB}
    weights = compute_vm_weights(group, LOADS, [701, 702], active_split_caps(group, OBJECTIVE))
    assert weights[701] == 1.0


def test_the_split_gate_opens_on_the_initial_state() -> None:
    opened = split_gate(_group(), OBJECTIVE)
    assert opened is not None
    assert opened[0] == 701


def test_the_split_gate_is_off_without_the_rule_or_the_weight() -> None:
    assert split_gate(_group(split_vm_footprint_bytes=None), OBJECTIVE) is None
    assert split_gate(_group(), dataclasses.replace(OBJECTIVE, mu_vm_split_per_tib=0.0)) is None


def test_the_split_gate_skips_a_storage_in_cooldown() -> None:
    assert split_gate(_group(), OBJECTIVE, frozenset({"st-b", "st-c"})) is None
    assert split_gate(_group(), OBJECTIVE, frozenset({"st-b"})) is not None


def test_heuristic_finds_the_four_four_two_split() -> None:
    group = _group()
    result = run_heuristic(group, LOADS, OBJECTIVE)
    assert _footprints(group, result.assignment) == [4 * TIB, 4 * TIB, 2 * TIB]
    assert result.breakdown.moves == 3
    assert result.breakdown.total == pytest.approx(4.05)
    assert sum(result.breakdown.split_excess_bytes.values()) == 2 * TIB


@pytest.mark.parametrize("backend", BACKENDS)
def test_milp_finds_the_proven_optimum(backend: str) -> None:
    group = _group()
    result = solve(group, LOADS, OBJECTIVE, backend=backend, time_limit_seconds=30.0, mip_gap=0.0)
    assert result is not None
    assert _footprints(group, result.assignment) == [4 * TIB, 4 * TIB, 2 * TIB]
    assert result.breakdown.moves == 3
    assert result.breakdown.total == pytest.approx(4.05)


def test_the_gate_shuts_on_the_result() -> None:
    """No single move lowers a peak of 4 on three storages (4, 4, 2 -> 2, 4, 4)."""
    group = _group()
    result = run_heuristic(group, LOADS, OBJECTIVE)
    settled = _group(placement={k: v for k, v in result.assignment.items() if k.startswith("701")})
    assert split_gate(settled, OBJECTIVE) is None


def test_without_the_rule_nothing_moves() -> None:
    """The counterfactual recorded in the expected file."""
    group = _group(split_vm_footprint_bytes=None)
    assert run_heuristic(group, LOADS, OBJECTIVE).breakdown.moves == 0


def test_a_pinned_vm_never_opens_the_gate() -> None:
    group = _group()
    pinned = dataclasses.replace(
        group,
        disks=tuple(
            dataclasses.replace(d, pinned_reason="excluded") if d.vmid == 701 else d
            for d in group.disks
        ),
    )
    assert split_gate(pinned, OBJECTIVE) is None


def test_end_to_end_payback_accepts_on_merit_not_as_a_repair() -> None:
    group = _group()
    solve_outcome = run_heuristic(group, LOADS, OBJECTIVE)
    schedule_result = order_moves(group, solve_outcome.assignment, LOADS, OBJECTIVE)
    assert not schedule_result.deadlocked
    assert len(schedule_result.order) == 3

    storages_by_id = {s.id: s for s in group.storages}
    move_costs = [
        compute_move_cost(m, storages_by_id[m.from_storage], MIGRATION)
        for m in schedule_result.order
    ]
    assert sum(mc.cost_load_seconds for mc in move_costs) == pytest.approx(62_914.56, abs=0.01)

    final = evaluate_assignment(
        group,
        schedule_result.final_assignment,
        LOADS,
        OBJECTIVE,
        group_average_utilization(group, LOADS),
        group_average_fill(group),
    )
    initial = solve_outcome.initial_breakdown
    assert raw_split_excess_tib(initial) == pytest.approx(8.0)
    assert raw_split_excess_tib(final) == pytest.approx(2.0)
    benefit = compute_benefit_load_seconds(
        OBJECTIVE.alpha_spread,
        raw_spread(initial, OBJECTIVE.spread_metric),
        raw_spread(final, OBJECTIVE.spread_metric),
        OBJECTIVE.delta_capacity_spread,
        raw_capacity_spread(initial),
        raw_capacity_spread(final),
        MIGRATION.payback_horizon_seconds,
        OBJECTIVE.kappa_vm_affinity,
        raw_affinity_debt(initial),
        raw_affinity_debt(final),
        OBJECTIVE.mu_vm_split_per_tib,
        raw_split_excess_tib(initial),
        raw_split_excess_tib(final),
    )
    assert benefit == pytest.approx(157_680_000.0, rel=1e-6)
    result = evaluate_plan_payback(
        move_costs,
        benefit,
        MIGRATION.payback_ratio,
        current_shortfall_bytes=0,
        final_shortfall_bytes=0,
    )
    assert result.ratio == pytest.approx(2506.26, abs=0.01)
    assert result.accepted
    assert not result.repair_exempt


def test_payback_without_the_mu_term_would_reject() -> None:
    """The mu*dO term is what pays here: kappa*dA alone is negative."""
    assert (
        compute_benefit_load_seconds(
            1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 31_536_000.0, 0.5, 0.0, 2.0, 1.0, 8.0, 2.0
        )
        > 0
    )
    assert (
        compute_benefit_load_seconds(1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 31_536_000.0, 0.5, 0.0, 2.0) < 0
    )
