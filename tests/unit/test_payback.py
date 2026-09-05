# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Migration cost and the payback test. See proxmox_storage_drs/payback.py.

Cross-checked against IMPLEMENTATION_PLAN.md section 14.5's worked
example exactly: the two-move plan's per-move durations/costs, the
accepted ratio (150.7), and the separate failed-payback example (a 4 TiB
archive disk, ratio 0.72, rejected).
"""

from __future__ import annotations

import pytest

from proxmox_storage_drs.config import MigrationConfig
from proxmox_storage_drs.payback import (
    compute_benefit_load_seconds,
    compute_move_cost,
    compute_wipe_duration_seconds,
    evaluate_plan_payback,
)
from proxmox_storage_drs.schedule import ScheduledMove
from proxmox_storage_drs.topology import Storage

TIB = 1 << 40
MIB = 1 << 20

# Section 14.5: bwlimit=200 MiB/s, w_src=w_dst=1.0, saferemove off
# everywhere so duration_wipe_d=0 -- the fixture states this explicitly
# rather than leaving it to be inferred (the plan's own note on why).
SECTION_14_5_MIGRATION = MigrationConfig(
    bwlimit_bytes_per_sec=200 * MIB,
    source_load_weight=1.0,
    target_load_weight=1.0,
    payback_horizon_seconds=604800.0,  # 7d
    payback_ratio=10.0,
    max_single_move_duration_seconds=21600.0,  # 6h
    account_saferemove_wipe=True,  # the default; irrelevant since saferemove is off below
    wipe_load_weight=1.0,
)


def no_saferemove_storage(id_: str) -> Storage:
    return Storage(
        id=id_,
        capability_weight=1.0,
        reserve_factor=2.0,
        saturation_load=None,
        capacity_bytes=8 * TIB,
        used_bytes=0,
        foreign_used_bytes=0,
        saferemove=False,
        saferemove_throughput_bytes_per_sec=None,
    )


def move(disk_key: str, from_storage: str, to_storage: str, size_tib: float) -> ScheduledMove:
    vmid, device = disk_key.split(":")
    return ScheduledMove(
        disk_key=disk_key,
        vmid=int(vmid),
        device=device,
        from_storage=from_storage,
        to_storage=to_storage,
        size_bytes=round(size_tib * TIB),
        imbalance_reduction=0.0,
        resolves_reserve_violation=False,
    )


# ------------------------------------------------------------------- section 14.5


def test_section_14_5_move_durations_and_costs_match_exactly() -> None:
    san_a = no_saferemove_storage("san-a")

    m1 = move("102:scsi0", "san-a", "san-c", 1.5)
    cost1 = compute_move_cost(m1, san_a, SECTION_14_5_MIGRATION)
    assert cost1.duration_mirror_seconds == pytest.approx(7864.32, abs=0.01)
    assert cost1.duration_wipe_seconds == 0.0
    assert cost1.cost_load_seconds == pytest.approx(15728.64, abs=0.01)

    m2 = move("101:scsi1", "san-a", "san-b", 1.0)
    cost2 = compute_move_cost(m2, san_a, SECTION_14_5_MIGRATION)
    assert cost2.duration_mirror_seconds == pytest.approx(5242.88, abs=0.01)
    assert cost2.cost_load_seconds == pytest.approx(10485.76, abs=0.01)

    total_cost = cost1.cost_load_seconds + cost2.cost_load_seconds
    assert total_cost == pytest.approx(26214.4, abs=0.1)  # plan: "26 214 load*s"


def test_section_14_5_two_move_plan_is_accepted_at_ratio_150_7() -> None:
    san_a = no_saferemove_storage("san-a")
    moves = [
        move("102:scsi0", "san-a", "san-c", 1.5),
        move("101:scsi1", "san-a", "san-b", 1.0),
    ]
    costs = [compute_move_cost(m, san_a, SECTION_14_5_MIGRATION) for m in moves]

    # Section 14.2/14.3's exact E_before/E_after for the two-move plan.
    benefit = compute_benefit_load_seconds(8.066667, 1.533333, 604800.0)
    assert benefit == pytest.approx(3951360.0, abs=1.0)  # plan: "3 951 360"

    result = evaluate_plan_payback(costs, benefit, SECTION_14_5_MIGRATION.payback_ratio)

    assert result.total_cost_load_seconds == pytest.approx(26214.4, abs=0.1)
    assert result.ratio == pytest.approx(150.7, abs=0.05)
    assert result.aggregate_ok
    assert result.accepted
    assert result.rejected_moves == ()


def test_section_14_5_archive_disk_fails_payback_at_ratio_0_72() -> None:
    """The plan's own counter-example: a 4 TiB, low-benefit disk."""
    san_x = no_saferemove_storage("san-x")
    archive_move = move("106:scsi0", "san-x", "san-y", 4.0)
    cost = compute_move_cost(archive_move, san_x, SECTION_14_5_MIGRATION)

    assert cost.duration_mirror_seconds == pytest.approx(20971.52, abs=0.01)
    assert cost.cost_load_seconds == pytest.approx(41943.04, abs=0.01)

    benefit = 0.05 * 604800.0  # plan states the improvement directly: 0.05
    assert benefit == pytest.approx(30240.0)

    result = evaluate_plan_payback([cost], benefit, SECTION_14_5_MIGRATION.payback_ratio)

    assert result.ratio == pytest.approx(0.72, abs=0.005)
    assert not result.aggregate_ok
    assert not result.accepted


# --------------------------------------------------------------------- wipe accounting


def test_saferemove_wipe_is_included_when_enabled() -> None:
    source = Storage(
        id="san-a",
        capability_weight=1.0,
        reserve_factor=2.0,
        saturation_load=None,
        capacity_bytes=8 * TIB,
        used_bytes=0,
        foreign_used_bytes=0,
        saferemove=True,
        saferemove_throughput_bytes_per_sec=10 * MIB,  # PVE's LVM default
    )
    m = move("101:scsi0", "san-a", "san-b", 1.5)
    migration = MigrationConfig(
        bwlimit_bytes_per_sec=200 * MIB,
        source_load_weight=1.0,
        target_load_weight=1.0,
        account_saferemove_wipe=True,
        wipe_load_weight=1.0,
        max_single_move_duration_seconds=999_999_999.0,
    )

    cost = compute_move_cost(m, source, migration)

    # 1.5 TiB / 10 MiB/s -- the plan's own "~44 hours" to *wipe* this disk
    # (the mirror itself is the separate ~2.2h from section 14.5).
    assert cost.duration_wipe_seconds == pytest.approx(1.5 * TIB / (10 * MIB))
    assert cost.duration_wipe_seconds / 3600 == pytest.approx(44.0, abs=0.5)  # plan says "about"
    assert cost.cost_load_seconds == pytest.approx(
        cost.duration_mirror_seconds * 2 + cost.duration_wipe_seconds * 1.0
    )


def test_account_saferemove_wipe_false_disables_the_term_even_if_enabled_on_the_storage() -> None:
    source = Storage(
        id="san-a",
        capability_weight=1.0,
        reserve_factor=2.0,
        saturation_load=None,
        capacity_bytes=8 * TIB,
        used_bytes=0,
        foreign_used_bytes=0,
        saferemove=True,
        saferemove_throughput_bytes_per_sec=10 * MIB,
    )
    m = move("101:scsi0", "san-a", "san-b", 1.5)
    migration = MigrationConfig(
        bwlimit_bytes_per_sec=200 * MIB,
        account_saferemove_wipe=False,
        max_single_move_duration_seconds=999_999_999.0,
    )

    cost = compute_move_cost(m, source, migration)

    assert cost.duration_wipe_seconds == 0.0


def test_saferemove_on_but_throughput_unknown_skips_the_wipe_term() -> None:
    """`saferemove=True` with no known throughput (e.g. never surfaced by
    `GET /storage`) must not crash or invent a duration -- matches
    `verify-storages`'s own "saferemove is off or throughput unknown; no
    wipe-time check" handling of the identical gap."""
    source = Storage(
        id="san-a",
        capability_weight=1.0,
        reserve_factor=2.0,
        saturation_load=None,
        capacity_bytes=8 * TIB,
        used_bytes=0,
        foreign_used_bytes=0,
        saferemove=True,
        saferemove_throughput_bytes_per_sec=None,
    )
    m = move("101:scsi0", "san-a", "san-b", 1.5)
    migration = MigrationConfig(bwlimit_bytes_per_sec=200 * MIB, account_saferemove_wipe=True)

    cost = compute_move_cost(m, source, migration)

    assert cost.duration_wipe_seconds == 0.0


def test_compute_wipe_duration_seconds_returns_none_without_throughput() -> None:
    assert compute_wipe_duration_seconds(1 * TIB, None) is None
    assert compute_wipe_duration_seconds(1 * TIB, 0.0) is None
    assert compute_wipe_duration_seconds(1 * TIB, 10 * MIB) == pytest.approx(1 * TIB / (10 * MIB))


# ------------------------------------------------------------------ hard duration rule


def test_move_exceeding_max_single_move_duration_is_flagged_and_rejects_the_plan() -> None:
    source = no_saferemove_storage("san-a")
    m = move("101:scsi0", "san-a", "san-b", 100.0)  # huge disk
    migration = MigrationConfig(
        bwlimit_bytes_per_sec=200 * MIB,
        max_single_move_duration_seconds=3600.0,  # 1h -- this move takes far longer
    )

    cost = compute_move_cost(m, source, migration)
    assert cost.exceeds_max_duration

    # Even a huge, generously-profitable benefit cannot rescue a plan with
    # a hard-rejected move -- "report, never force" (section 8.3's phrase,
    # applied here to section 7.3's own hard per-move rule).
    result = evaluate_plan_payback([cost], benefit_load_seconds=1e12, payback_ratio=10.0)
    assert result.aggregate_ok  # the aggregate ratio alone would pass
    assert result.rejected_moves == ("101:scsi0",)
    assert not result.accepted


def test_move_cost_duration_seconds_is_mirror_plus_wipe() -> None:
    source = Storage(
        id="san-a",
        capability_weight=1.0,
        reserve_factor=2.0,
        saturation_load=None,
        capacity_bytes=8 * TIB,
        used_bytes=0,
        foreign_used_bytes=0,
        saferemove=True,
        saferemove_throughput_bytes_per_sec=10 * MIB,
    )
    m = move("101:scsi0", "san-a", "san-b", 1.5)
    migration = MigrationConfig(
        bwlimit_bytes_per_sec=200 * MIB,
        account_saferemove_wipe=True,
        max_single_move_duration_seconds=999_999_999.0,
    )
    cost = compute_move_cost(m, source, migration)
    assert cost.duration_seconds == pytest.approx(
        cost.duration_mirror_seconds + cost.duration_wipe_seconds
    )
    assert cost.duration_wipe_seconds > 0  # sanity: the wipe term is actually nonzero here


def test_move_within_max_single_move_duration_is_not_flagged() -> None:
    source = no_saferemove_storage("san-a")
    m = move("101:scsi0", "san-a", "san-b", 0.1)
    migration = MigrationConfig(
        bwlimit_bytes_per_sec=200 * MIB, max_single_move_duration_seconds=21600.0
    )
    cost = compute_move_cost(m, source, migration)
    assert not cost.exceeds_max_duration


# -------------------------------------------------------------------------- edge cases


def test_zero_cost_plan_has_infinite_ratio_and_is_accepted_if_benefit_is_nonnegative() -> None:
    result = evaluate_plan_payback([], benefit_load_seconds=0.0, payback_ratio=10.0)
    assert result.total_cost_load_seconds == 0.0
    assert result.ratio == float("inf")
    assert result.aggregate_ok  # 0 >= 10*0
    assert result.accepted


def test_reserve_resolving_move_always_passes_the_aggregate_test() -> None:
    """Section 13's "reserve is never traded against balance" applied to
    payback too: a move that resolves a (C4)/(C5) violation is not
    optional the way a balance-driven move is, so a plan containing one
    always passes the aggregate ratio test -- even with zero benefit and a
    real cost, which is exactly the common case (moving the only loaded
    disk between two storages relocates the imbalance but does not reduce
    it)."""
    source = no_saferemove_storage("san-a")
    vmid, device = "101:scsi0".split(":")
    reserve_move = ScheduledMove(
        disk_key="101:scsi0",
        vmid=int(vmid),
        device=device,
        from_storage="san-a",
        to_storage="san-b",
        size_bytes=round(3.0 * TIB),
        imbalance_reduction=0.0,
        resolves_reserve_violation=True,
    )
    cost = compute_move_cost(reserve_move, source, SECTION_14_5_MIGRATION)

    result = evaluate_plan_payback([cost], benefit_load_seconds=0.0, payback_ratio=10.0)

    assert result.total_cost_load_seconds > 0  # a real cost, not a free move
    assert result.aggregate_ok
    assert result.accepted


def test_reserve_resolving_move_still_blocked_by_the_hard_duration_rule() -> None:
    """The exemption above is from the *economic* test only -- the hard
    per-move duration rule is operational, not economic, and section 7.3
    lists it as applying "regardless of the aggregate test"."""
    source = Storage(
        id="san-a",
        capability_weight=1.0,
        reserve_factor=2.0,
        saturation_load=None,
        capacity_bytes=8 * TIB,
        used_bytes=0,
        foreign_used_bytes=0,
        saferemove=True,
        saferemove_throughput_bytes_per_sec=10 * MIB,  # slow wipe
    )
    vmid, device = "101:scsi0".split(":")
    reserve_move = ScheduledMove(
        disk_key="101:scsi0",
        vmid=int(vmid),
        device=device,
        from_storage="san-a",
        to_storage="san-b",
        size_bytes=round(3.0 * TIB),
        imbalance_reduction=0.0,
        resolves_reserve_violation=True,
    )
    migration = MigrationConfig(
        bwlimit_bytes_per_sec=200 * MIB,
        account_saferemove_wipe=True,
        max_single_move_duration_seconds=3600.0,  # far shorter than the wipe
    )
    cost = compute_move_cost(reserve_move, source, migration)
    assert cost.exceeds_max_duration

    result = evaluate_plan_payback([cost], benefit_load_seconds=0.0, payback_ratio=10.0)

    assert result.aggregate_ok  # the economic test is exempted
    assert not result.accepted  # but the hard duration rule still blocks it
    assert result.rejected_moves == ("101:scsi0",)


def test_negative_benefit_is_never_accepted() -> None:
    """A plan that makes imbalance worse (possible if beta/gamma/kappa
    dominate) must fail payback outright, not merely score low."""
    benefit = compute_benefit_load_seconds(
        imbalance_before=1.0, imbalance_after=1.5, payback_horizon_seconds=604800.0
    )
    assert benefit < 0
    source = no_saferemove_storage("san-a")
    m = move("101:scsi0", "san-a", "san-b", 0.1)
    migration = MigrationConfig(bwlimit_bytes_per_sec=200 * MIB)
    cost = compute_move_cost(m, source, migration)

    result = evaluate_plan_payback([cost], benefit, migration.payback_ratio)
    assert not result.aggregate_ok
    assert not result.accepted
