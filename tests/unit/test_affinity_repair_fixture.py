# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""IMPLEMENTATION_PLAN.md section 14.7's fixture, exercised through the real
production code paths (not just tests/fixtures/generate_expected.py's own
exhaustive-enumeration oracle). See tests/fixtures/affinity-repair.yaml and
its generated affinity-repair.expected.json for the proven-optimal numbers
this file's assertions are transcribed from -- do not hand-edit either file;
regenerate with `python3 tests/fixtures/generate_expected.py`.

This is the live dogfooding failure section 5.4/7.2 exist to fix, reproduced
end to end: a group whose I/O is already balanced and whose only improving
moves are a VM's tiny disks reuniting with it, cross-checked against the
heuristic, both MILP backends, the scheduler and the payback rule together --
not just the objective's own reported total, the way test_heuristic.py's/
test_optimize.py's section-14 cross-checks already do for the *other* worked
example.
"""

from __future__ import annotations

import pytest

from proxmox_storage_drs.config import MigrationConfig, ObjectiveConfig
from proxmox_storage_drs.heuristic import (
    evaluate_assignment,
    group_average_fill,
    group_average_utilization,
    raw_affinity_debt,
    raw_capacity_spread,
    raw_spread,
    run_heuristic,
)
from proxmox_storage_drs.optimize import cbc_available, cpsat_available, solve
from proxmox_storage_drs.payback import (
    compute_benefit_load_seconds,
    compute_move_cost,
    evaluate_plan_payback,
)
from proxmox_storage_drs.schedule import order_moves
from proxmox_storage_drs.topology import Disk, Group, Storage

TIB = 1 << 40
MIB = 1 << 20

BACKENDS = [
    pytest.param(
        "cpsat", marks=pytest.mark.skipif(not cpsat_available(), reason="ortools not installed")
    ),
    pytest.param("cbc", marks=pytest.mark.skipif(not cbc_available(), reason="pulp not installed")),
]

TINY_DISK_BYTES = 64 * MIB  # config default, section 5.4/11.1

OBJECTIVE = ObjectiveConfig(
    alpha_spread=1.0,
    beta_move_count=0.25,
    gamma_move_bytes_per_tib=0.05,
    kappa_vm_affinity=0.5,
    delta_capacity_spread=0.5,
    # Pinned explicitly, not inherited: section 14.7's worked numbers are
    # computed with `V` ranging over movable disks only, and
    # `tests/fixtures/generate_expected.py`'s independent oracle computes
    # `fragmentation()` the same way. The engine's own default is True
    # (section 5.3 (C3)); a fixture that carries the plan's arithmetic must
    # state which semantics that arithmetic is in, not track a default.
    affinity_counts_pinned_disks=False,
)

MIGRATION = MigrationConfig(
    bwlimit_bytes_per_sec=200 * MIB,
    source_load_weight=1.0,
    target_load_weight=1.0,
    wipe_load_weight=1.0,
    account_saferemove_wipe=False,
    payback_horizon_seconds=31_536_000.0,  # 365d
    payback_ratio=10.0,
    tiny_disk_bytes=TINY_DISK_BYTES,
)


def _make_storage(id_: str, foreign_used_tib: float = 0.0) -> Storage:
    return Storage(
        id=id_,
        capability_weight=1.0,
        reserve_factor=2.0,
        saturation_load=None,
        capacity_bytes=8 * TIB,
        used_bytes=0,
        foreign_used_bytes=round(foreign_used_tib * TIB),
        saferemove=False,
        saferemove_throughput_bytes_per_sec=None,
    )


def _make_disk(
    key: str, size_bytes: int, load: float, storage: str, pinned: str | None = None
) -> Disk:
    vmid, device = key.split(":")
    return Disk(
        key=key,
        vmid=int(vmid),
        device=device,
        vm_name=f"vm{vmid}",
        node="pve01",
        size_bytes=size_bytes,
        current_storage=storage,
        format="raw",
        pinned_reason=pinned,
    )


def _affinity_repair_group() -> Group:
    """tests/fixtures/affinity-repair.yaml, built as real topology objects."""
    storages = (_make_storage("stor-a"), _make_storage("stor-b"), _make_storage("stor-c", 4.0))
    disks = (
        _make_disk("301:scsi0", 1 * TIB, 2.0, "stor-a"),
        _make_disk("301:efidisk0", 528 * 1024, 0.0, "stor-c"),  # 528 KiB
        _make_disk("301:tpmstate0", 1 * MIB, 0.0, "stor-b"),
        _make_disk("302:scsi0", 1 * TIB, 2.0, "stor-b"),
        _make_disk("309:scsi0", 1 * TIB, 2.0, "stor-c", pinned="excluded: exclude.vmids"),
    )
    return Group(name="affinity-repair", storages=storages, disks=disks)


def _loads() -> dict[str, float]:
    return {
        "301:scsi0": 2.0,
        "301:efidisk0": 0.0,
        "301:tpmstate0": 0.0,
        "302:scsi0": 2.0,
        "309:scsi0": 2.0,
    }


def test_heuristic_reunites_the_tiny_disks_for_free() -> None:
    group = _affinity_repair_group()
    loads = _loads()
    result = run_heuristic(
        group, loads, OBJECTIVE, min_free_bytes=0, tiny_disk_bytes=TINY_DISK_BYTES
    )

    assert result.assignment["301:efidisk0"] == "stor-a"
    assert result.assignment["301:tpmstate0"] == "stor-a"
    assert result.assignment["301:scsi0"] == "stor-a"  # never moved
    assert result.assignment["302:scsi0"] == "stor-b"  # never moved
    assert result.assignment["309:scsi0"] == "stor-c"  # pinned, never moved
    assert result.breakdown.moves == 2
    assert result.breakdown.move_count_term == 0.0  # both moves are D^big-exempt
    assert result.breakdown.bytes_moved_term == 0.0
    assert result.breakdown.fragmentation_term == 0.0  # VM 301 fully reunited


@pytest.mark.parametrize("backend", BACKENDS)
def test_both_milp_backends_agree_with_the_heuristic(backend: str) -> None:
    group = _affinity_repair_group()
    loads = _loads()
    result = solve(
        group,
        loads,
        OBJECTIVE,
        min_free_bytes=0,
        backend=backend,
        time_limit_seconds=10.0,
        mip_gap=0.0,
        tiny_disk_bytes=TINY_DISK_BYTES,
    )
    assert result is not None
    assert result.assignment["301:efidisk0"] == "stor-a"
    assert result.assignment["301:tpmstate0"] == "stor-a"
    assert result.breakdown.moves == 2
    assert result.breakdown.fragmentation_term == 0.0


def test_end_to_end_plan_accepts_payback_at_zero_cost() -> None:
    """The full pipeline -- solve, order, cost, benefit, accept -- exactly
    reproducing section 14.7's proven numbers (affinity-repair.expected.json's
    own `payback_two_move_plan`): benefit ~3.15e7 load*s against cost 0,
    accepted. This fixture pins section 5.4/7.2's *value*, not a verdict
    flip: replayed with the pre-fix formula (no kappa*dA term,
    tiny_disk_bytes=0), this same plan still accepts (ΔE=0 exactly, ΔF
    positive, benefit ~+6.65 load*s against a nonzero cost, ratio ~438) --
    see IMPLEMENTATION_PLAN.md section 14.7 for the live scenario that
    actually did flip reject-to-accept (the pre-section-12 one-term, 7d
    formula)."""
    group = _affinity_repair_group()
    loads = _loads()
    solve_outcome = run_heuristic(
        group, loads, OBJECTIVE, min_free_bytes=0, tiny_disk_bytes=TINY_DISK_BYTES
    )
    schedule_result = order_moves(
        group,
        solve_outcome.assignment,
        loads,
        OBJECTIVE,
        min_free_bytes=0,
        tiny_disk_bytes=TINY_DISK_BYTES,
    )
    assert not schedule_result.deadlocked
    assert len(schedule_result.order) == 2

    storages_by_id = {s.id: s for s in group.storages}
    move_costs = [
        compute_move_cost(move, storages_by_id[move.from_storage], MIGRATION)
        for move in schedule_result.order
    ]
    assert all(mc.cost_load_seconds == 0.0 for mc in move_costs)

    final_breakdown = evaluate_assignment(
        group,
        schedule_result.final_assignment,
        loads,
        OBJECTIVE,
        0,
        group_average_utilization(group, loads),
        group_average_fill(group),
        TINY_DISK_BYTES,
    )

    benefit = compute_benefit_load_seconds(
        OBJECTIVE.alpha_spread,
        raw_spread(solve_outcome.initial_breakdown, OBJECTIVE.spread_metric),
        raw_spread(final_breakdown, OBJECTIVE.spread_metric),
        OBJECTIVE.delta_capacity_spread,
        raw_capacity_spread(solve_outcome.initial_breakdown),
        raw_capacity_spread(final_breakdown),
        MIGRATION.payback_horizon_seconds,
        OBJECTIVE.kappa_vm_affinity,
        raw_affinity_debt(solve_outcome.initial_breakdown),
        raw_affinity_debt(final_breakdown),
    )
    assert benefit == pytest.approx(31_536_006.65, abs=1.0)  # affinity-repair.expected.json

    payback_result = evaluate_plan_payback(move_costs, benefit, MIGRATION.payback_ratio)
    assert payback_result.total_cost_load_seconds == 0.0
    assert payback_result.ratio == float("inf")
    assert payback_result.aggregate_ok
    assert payback_result.accepted
