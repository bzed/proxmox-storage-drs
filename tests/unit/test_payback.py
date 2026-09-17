# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Migration cost and the payback test. See proxmox_storage_drs/payback.py.

Cross-checked against IMPLEMENTATION_PLAN.md section 14.5's worked
example exactly: the two-move plan's per-move durations/costs, the
accepted ratio (~7344 at the 365d default horizon, with the delta*F and
kappa*A terms folded in per sections 12 and 5.4/7.2's affinity-payback
fix), and the separate failed-payback example (a 4 TiB archive disk,
ratio 7.5, rejected).
"""

from __future__ import annotations

import pytest

from proxmox_storage_drs.config import MigrationConfig
from proxmox_storage_drs.payback import (
    compute_benefit_load_seconds,
    compute_move_cost,
    compute_wipe_duration_seconds,
    evaluate_plan_payback,
    mirror_duration_seconds,
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
    payback_horizon_seconds=31_536_000.0,  # 365d, section 12's default
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


def test_section_14_5_two_move_plan_is_accepted_at_ratio_7344() -> None:
    """Reworked by section 5.4/7.2's affinity-payback fix: the plan splits
    VM 101 (both disks on san-a before, scsi1 moves to san-b), so
    ``kappa*(A_before - A_after)`` -- A_before=0 (together), A_after=w_101
    (one extra storage), w_101=max(1, 4.0/(7.4/5))=2.7027 -- now enters the
    benefit as a negative term the split must pay for out of its alpha
    gain, lowering the pre-section-12 ratio from ~8970 to ~7344."""
    san_a = no_saferemove_storage("san-a")
    moves = [
        move("102:scsi0", "san-a", "san-c", 1.5),
        move("101:scsi1", "san-a", "san-b", 1.0),
    ]
    costs = [compute_move_cost(m, san_a, SECTION_14_5_MIGRATION) for m in moves]

    # Section 14.2/14.3's exact E_before/E_after and F_before/F_after for
    # the two-move plan, at the defaults alpha_spread=1.0,
    # delta_capacity_spread=0.5, and the 365d horizon (section 12/7.2).
    benefit = compute_benefit_load_seconds(
        1.0,
        8.066667,
        1.533333,
        0.5,
        2.153846,
        0.307692,
        31_536_000.0,
        kappa_vm_affinity=0.5,
        affinity_debt_before=0.0,
        affinity_debt_after=20 / 7.4,  # w_101 = 4.0 / (7.4/5), section 14.3
    )
    assert benefit == pytest.approx(192527280.0, rel=1e-4)  # plan: "~1.93e8"

    result = evaluate_plan_payback(costs, benefit, SECTION_14_5_MIGRATION.payback_ratio)

    assert result.total_cost_load_seconds == pytest.approx(26214.4, abs=0.1)
    assert result.ratio == pytest.approx(7344.0, abs=1.0)
    assert result.aggregate_ok
    assert result.accepted
    assert result.rejected_moves == ()


def test_section_14_5_archive_disk_fails_payback_at_ratio_7_5() -> None:
    """The plan's own counter-example: a 4 TiB disk whose relocation
    improves E by only 0.01 and leaves the data spread essentially
    unchanged (delta*F contributes ~0)."""
    san_x = no_saferemove_storage("san-x")
    archive_move = move("106:scsi0", "san-x", "san-y", 4.0)
    cost = compute_move_cost(archive_move, san_x, SECTION_14_5_MIGRATION)

    assert cost.duration_mirror_seconds == pytest.approx(20971.52, abs=0.01)
    assert cost.cost_load_seconds == pytest.approx(41943.04, abs=0.01)

    # plan states the improvement directly: alpha*0.01, delta*0 (unchanged spread).
    benefit = compute_benefit_load_seconds(1.0, 0.01, 0.0, 0.5, 0.0, 0.0, 31_536_000.0)
    assert benefit == pytest.approx(315360.0)

    result = evaluate_plan_payback([cost], benefit, SECTION_14_5_MIGRATION.payback_ratio)

    assert result.ratio == pytest.approx(7.5, abs=0.05)
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


def test_mirror_duration_seconds_matches_compute_move_cost() -> None:
    """The one implementation both `compute_move_cost()` and a saturation
    -guard caller (which needs the duration *before* calling that
    function, to request a forecast at the right horizon) share."""
    m = move("101:scsi0", "san-a", "san-b", 1.5)
    migration = MigrationConfig(bwlimit_bytes_per_sec=200 * MIB)
    cost = compute_move_cost(m, no_saferemove_storage("san-a"), migration)
    assert mirror_duration_seconds(m, migration) == pytest.approx(cost.duration_mirror_seconds)


# --------------------------------------------------------- section 7.3 saturation guard


def saturating_storage(id_: str, saturation_load: float | None) -> Storage:
    return Storage(
        id=id_,
        capability_weight=1.0,
        reserve_factor=2.0,
        saturation_load=saturation_load,
        capacity_bytes=8 * TIB,
        used_bytes=0,
        foreign_used_bytes=0,
        saferemove=False,
        saferemove_throughput_bytes_per_sec=None,
    )


SATURATION_MIGRATION = MigrationConfig(
    bwlimit_bytes_per_sec=200 * MIB,
    source_load_weight=1.0,
    target_load_weight=1.0,
    saturation_ceiling=0.85,
    max_single_move_duration_seconds=999_999_999.0,
)


def test_saturation_check_is_inactive_without_a_target() -> None:
    """The default call shape (every pre-existing call site) never sets
    `saturation_deferred`, regardless of how extreme `l_hat_src`/
    `l_hat_dst` would be if they were ever consulted -- the check is
    opt-in, not opt-out."""
    m = move("101:scsi0", "san-a", "san-b", 1.0)
    source = saturating_storage("san-a", saturation_load=0.001)
    cost = compute_move_cost(
        m, source, SATURATION_MIGRATION, target=None, l_hat_src=1e9, l_hat_dst=1e9
    )
    assert not cost.saturation_deferred


def test_saturation_check_skipped_for_an_endpoint_with_no_saturation_load() -> None:
    m = move("101:scsi0", "san-a", "san-b", 1.0)
    source = saturating_storage("san-a", saturation_load=None)
    target = saturating_storage("san-b", saturation_load=None)
    cost = compute_move_cost(
        m, source, SATURATION_MIGRATION, target=target, l_hat_src=1e9, l_hat_dst=1e9
    )
    assert not cost.saturation_deferred


def test_saturation_check_defers_when_the_source_endpoint_exceeds_the_ceiling() -> None:
    m = move("101:scsi0", "san-a", "san-b", 1.0)
    source = saturating_storage("san-a", saturation_load=10.0)  # ceiling: 0.85*10=8.5
    target = saturating_storage("san-b", saturation_load=None)
    # l_hat_src=8.0 + omega_src(1.0) = 9.0 > 8.5 -> deferred.
    cost = compute_move_cost(
        m, source, SATURATION_MIGRATION, target=target, l_hat_src=8.0, l_hat_dst=0.0
    )
    assert cost.saturation_deferred


def test_saturation_check_defers_when_the_target_endpoint_exceeds_the_ceiling() -> None:
    m = move("101:scsi0", "san-a", "san-b", 1.0)
    source = saturating_storage("san-a", saturation_load=None)
    target = saturating_storage("san-b", saturation_load=10.0)
    cost = compute_move_cost(
        m, source, SATURATION_MIGRATION, target=target, l_hat_src=0.0, l_hat_dst=8.0
    )
    assert cost.saturation_deferred


def test_saturation_check_passes_comfortably_under_the_ceiling() -> None:
    m = move("101:scsi0", "san-a", "san-b", 1.0)
    source = saturating_storage("san-a", saturation_load=10.0)
    target = saturating_storage("san-b", saturation_load=10.0)
    cost = compute_move_cost(
        m, source, SATURATION_MIGRATION, target=target, l_hat_src=1.0, l_hat_dst=1.0
    )
    assert not cost.saturation_deferred


def test_saturation_check_charges_the_role_weight_on_top_of_the_forecast() -> None:
    """L_during(s) = L_hat_s(duration_mirror) + omega_role(s) -- the
    forecast alone sitting exactly at the ceiling still defers once the
    move's own mirroring charge is added on top."""
    m = move("101:scsi0", "san-a", "san-b", 1.0)
    source = saturating_storage("san-a", saturation_load=10.0)  # ceiling 8.5
    target = saturating_storage("san-b", saturation_load=None)
    migration = MigrationConfig(
        bwlimit_bytes_per_sec=200 * MIB,
        source_load_weight=1.0,
        target_load_weight=1.0,
        saturation_ceiling=0.85,
        max_single_move_duration_seconds=999_999_999.0,
    )
    # l_hat_src alone (8.5) is exactly at the ceiling -- not over it -- but
    # + omega_src (1.0) pushes L_during to 9.5, over 8.5.
    cost = compute_move_cost(m, source, migration, target=target, l_hat_src=8.5, l_hat_dst=0.0)
    assert cost.saturation_deferred


def test_evaluate_plan_payback_reports_deferred_moves_separately_from_rejected() -> None:
    m1 = move("101:scsi0", "san-a", "san-b", 1.0)
    m2 = move("102:scsi0", "san-a", "san-c", 1.0)
    source = saturating_storage("san-a", saturation_load=10.0)  # ceiling 8.5
    target_b = saturating_storage("san-b", saturation_load=None)
    target_c = saturating_storage("san-c", saturation_load=None)
    deferred_cost = compute_move_cost(
        m1, source, SATURATION_MIGRATION, target=target_b, l_hat_src=20.0, l_hat_dst=0.0
    )
    normal_cost = compute_move_cost(
        m2, source, SATURATION_MIGRATION, target=target_c, l_hat_src=0.0, l_hat_dst=0.0
    )
    assert deferred_cost.saturation_deferred
    assert not normal_cost.saturation_deferred

    result = evaluate_plan_payback(
        [deferred_cost, normal_cost], benefit_load_seconds=1e9, payback_ratio=10.0
    )
    assert result.deferred_moves == ("101:scsi0",)
    assert result.rejected_moves == ()  # a defer is not a hard-duration rejection
    assert result.aggregate_ok  # the economic test itself is unaffected
    assert not result.accepted  # but a deferred move still blocks a clean accept


def test_negative_benefit_is_never_accepted() -> None:
    """A plan that makes imbalance worse (possible if beta/gamma/kappa
    dominate) must fail payback outright, not merely score low."""
    benefit = compute_benefit_load_seconds(
        alpha_spread=1.0,
        imbalance_before=1.0,
        imbalance_after=1.5,
        delta_capacity_spread=0.0,
        capacity_spread_before=0.0,
        capacity_spread_after=0.0,
        payback_horizon_seconds=604800.0,
    )
    assert benefit < 0
    source = no_saferemove_storage("san-a")
    m = move("101:scsi0", "san-a", "san-b", 0.1)
    migration = MigrationConfig(bwlimit_bytes_per_sec=200 * MIB)
    cost = compute_move_cost(m, source, migration)

    result = evaluate_plan_payback([cost], benefit, migration.payback_ratio)
    assert not result.aggregate_ok
    assert not result.accepted


# ------------------------------------------------------- tiny_disk_bytes (section 7.1/7.3)


def test_compute_move_cost_is_zero_below_tiny_disk_bytes() -> None:
    """Section 7.1: ``cost_d = 0`` when ``z_d < tiny_disk_bytes`` -- but
    duration and the hard per-move rules are still computed normally
    (section 7.3: "every hard rule below applies to it exactly as to any
    other move"), so a tiny disk that happens to exceed
    ``max_single_move_duration`` (an absurdly throttled ``bwlimit``, here)
    is still correctly flagged even though its cost is zero."""
    source = no_saferemove_storage("san-a")
    migration = MigrationConfig(
        bwlimit_bytes_per_sec=1,  # absurdly slow, to make even a tiny move exceed the duration rule
        max_single_move_duration_seconds=1.0,
        tiny_disk_bytes=2 * MIB,
    )
    efidisk = move(
        "301:efidisk0", "san-a", "san-b", 1 / (1024 * 1024)
    )  # 1 MiB, below tiny_disk_bytes
    cost = compute_move_cost(efidisk, source, migration)
    assert cost.cost_load_seconds == 0.0
    assert cost.duration_mirror_seconds > 0.0  # duration itself is still real
    assert cost.exceeds_max_duration  # the hard rule still applies to a tiny disk


def test_compute_move_cost_is_nonzero_at_tiny_disk_bytes_threshold() -> None:
    """The boundary is inclusive on the ``D^big`` side: a disk exactly at
    ``tiny_disk_bytes`` still carries a real cost (section 5.4: ``D^big =
    {d : z_d >= tiny_disk_bytes}``)."""
    source = no_saferemove_storage("san-a")
    migration = MigrationConfig(bwlimit_bytes_per_sec=200 * MIB, tiny_disk_bytes=2 * MIB)
    at_threshold = ScheduledMove(
        disk_key="301:efidisk0",
        vmid=301,
        device="efidisk0",
        from_storage="san-a",
        to_storage="san-b",
        size_bytes=2 * MIB,
        imbalance_reduction=0.0,
        resolves_reserve_violation=False,
    )
    cost = compute_move_cost(at_threshold, source, migration)
    assert cost.cost_load_seconds > 0.0


def test_negative_delta_affinity_reduces_benefit() -> None:
    """Section 7.2: "dA may be negative, and then it reduces the benefit: a
    balance move that splits a VM must pay for the fragmentation out of
    its alpha gain." A plan that improves imbalance but splits a heavy VM
    (A_before=0, together -> A_after=3.0, split) sees its benefit cut by
    kappa*3.0*H."""
    without_split = compute_benefit_load_seconds(
        1.0, 5.0, 2.0, 0.0, 0.0, 0.0, 604800.0, kappa_vm_affinity=0.5
    )
    with_split = compute_benefit_load_seconds(
        1.0,
        5.0,
        2.0,
        0.0,
        0.0,
        0.0,
        604800.0,
        kappa_vm_affinity=0.5,
        affinity_debt_before=0.0,
        affinity_debt_after=3.0,
    )
    assert with_split < without_split
    assert with_split == pytest.approx(without_split - 0.5 * 3.0 * 604800.0)


def test_all_tiny_disk_plan_accepts_on_affinity_benefit_alone() -> None:
    """Section 14.7's affinity-repair fixture in miniature: two tiny disks
    reunite with their VM, each costing 0 (section 7.1), so the aggregate
    test degrades to ``benefit >= payback_ratio * 0`` -- accepted purely on
    the kappa*dA term, exactly the live dogfooding case section 5.4/7.2
    exist to fix."""
    source = no_saferemove_storage("stor-c")
    migration = MigrationConfig(bwlimit_bytes_per_sec=200 * MIB, tiny_disk_bytes=2 * MIB)
    moves = [
        move("301:efidisk0", "stor-c", "stor-a", 1 / (1024 * 1024)),  # 1 MiB
        move("301:tpmstate0", "stor-b", "stor-a", 1 / (1024 * 1024)),  # 1 MiB
    ]
    costs = [compute_move_cost(m, source, migration) for m in moves]
    assert all(c.cost_load_seconds == 0.0 for c in costs)

    benefit = compute_benefit_load_seconds(
        1.0,
        0.0,
        0.0,
        0.5,
        0.0,
        0.0,
        31_536_000.0,
        kappa_vm_affinity=0.5,
        affinity_debt_before=2.0,  # VM spread over 2 extra storages, w_v=1
        affinity_debt_after=0.0,  # reunited
    )
    assert benefit > 0

    result = evaluate_plan_payback(costs, benefit, migration.payback_ratio)
    assert result.total_cost_load_seconds == 0.0
    assert result.ratio == float("inf")
    assert result.aggregate_ok
    assert result.accepted
