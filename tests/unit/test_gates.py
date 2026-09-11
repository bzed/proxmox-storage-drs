# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Section 6 gating. See proxmox_storage_drs/gates.py.

The initial-state imbalance check is cross-checked against
IMPLEMENTATION_PLAN.md section 14.2's worked example (spread 255%, same
u*=2.4667 reserve.py and loadmodel.py's own fixtures already reproduce),
not just self-consistent numbers.
"""

from __future__ import annotations

import pytest

from proxmox_storage_drs.config import GatesConfig
from proxmox_storage_drs.gates import GateDecision, evaluate_group_gates
from proxmox_storage_drs.loadmodel import DiskLoad, GroupLoad, StorageLoad
from proxmox_storage_drs.reserve import ReserveStatus

GATES = GatesConfig(drift_threshold=0.10, imbalance_threshold=0.20)


def ok_reserve() -> ReserveStatus:
    return ReserveStatus(
        largest_disk_bytes=0, required_reserve_bytes=0, managed_used_bytes=0, shortfall_bytes=0
    )


def violated_reserve() -> ReserveStatus:
    return ReserveStatus(
        largest_disk_bytes=0, required_reserve_bytes=0, managed_used_bytes=0, shortfall_bytes=1
    )


def section_14_2_group_load() -> GroupLoad:
    """The exact section 14.2 initial state: L=(6.50, 0.70, 0.20), u*=2.4667."""
    return GroupLoad(
        group_name="fc-tier1",
        idle=False,
        average_utilization=7.4 / 3,
        disks=(
            DiskLoad("101:scsi0", 3.0, None),
            DiskLoad("101:scsi1", 1.0, None),
            DiskLoad("102:scsi0", 2.5, None),
            DiskLoad("103:scsi0", 0.4, None),
            DiskLoad("104:scsi0", 0.3, None),
            DiskLoad("105:scsi0", 0.2, None),
        ),
        storages=(
            StorageLoad("san-a", 6.5, 6.5),
            StorageLoad("san-b", 0.7, 0.7),
            StorageLoad("san-c", 0.2, 0.2),
        ),
    )


def reserves_ok(group_load: GroupLoad) -> dict[str, ReserveStatus]:
    return {s.storage_id: ok_reserve() for s in group_load.storages}


# --------------------------------------------------------------- reserve override


def test_reserve_violation_bypasses_drift_and_imbalance_and_always_acts() -> None:
    """Balanced (spread 0) and no drift history -- would never act on
    imbalance/drift grounds alone, but a reserve violation must still win."""
    group_load = GroupLoad(
        group_name="g",
        idle=False,
        average_utilization=1.0,
        disks=(),
        storages=(StorageLoad("san-a", 1.0, 1.0), StorageLoad("san-b", 1.0, 1.0)),
    )
    statuses = {"san-a": violated_reserve(), "san-b": ok_reserve()}

    decision = evaluate_group_gates(group_load, statuses, GATES, last_load=None)

    assert decision == GateDecision(
        act=True,
        reason=(
            "reserve violated on san-a; acting now regardless of the normal "
            "drift/imbalance thresholds -- a capacity shortfall is never delayed by them"
        ),
        reserve_override=True,
        drift_fraction=None,
        imbalance_fraction=None,
    )


def test_reserve_violation_names_every_violating_storage_sorted() -> None:
    group_load = GroupLoad(
        group_name="g",
        idle=False,
        average_utilization=1.0,
        disks=(),
        storages=(StorageLoad("san-b", 1.0, 1.0), StorageLoad("san-a", 1.0, 1.0)),
    )
    statuses = {"san-b": violated_reserve(), "san-a": violated_reserve()}

    decision = evaluate_group_gates(group_load, statuses, GATES, last_load=None)

    assert "san-a, san-b" in decision.reason


# --------------------------------------------------------------------- imbalance gate


def test_section_14_2_initial_state_acts_at_255_percent_imbalance() -> None:
    group_load = section_14_2_group_load()

    decision = evaluate_group_gates(group_load, reserves_ok(group_load), GATES, last_load=None)

    assert decision.act
    assert decision.reserve_override is False
    assert decision.drift_fraction is None  # first run: drift gate skipped entirely
    assert decision.imbalance_fraction is not None
    assert round(decision.imbalance_fraction, 4) == round((6.5 - 0.2) / (7.4 / 3), 4)
    assert "25" in decision.reason  # 255.4% -- formatted with one decimal place


def test_two_move_solution_still_acts_at_53_percent_imbalance() -> None:
    """section 9.5's own example: after the two-move plan, spread is 53% --
    still above the default 20% threshold, so a subsequent run would act
    again (that next run's actual moves are the solver's job, not gates')."""
    group_load = GroupLoad(
        group_name="g",
        idle=False,
        average_utilization=7.4 / 3,
        disks=(),
        storages=(
            StorageLoad("san-a", 3.00, 3.00),
            StorageLoad("san-b", 1.70, 1.70),
            StorageLoad("san-c", 2.70, 2.70),
        ),
    )

    decision = evaluate_group_gates(group_load, reserves_ok(group_load), GATES, last_load=None)

    assert decision.act
    assert decision.imbalance_fraction is not None
    assert round(decision.imbalance_fraction, 3) == round((3.00 - 1.70) / (7.4 / 3), 3)


def test_balanced_group_does_not_act() -> None:
    group_load = GroupLoad(
        group_name="g",
        idle=False,
        average_utilization=1.0,
        disks=(),
        storages=(StorageLoad("san-a", 1.0, 1.0), StorageLoad("san-b", 1.0, 1.0)),
    )

    decision = evaluate_group_gates(group_load, reserves_ok(group_load), GATES, last_load=None)

    assert not decision.act
    assert decision.imbalance_fraction == 0.0
    assert "below" in decision.reason


def test_imbalance_exactly_at_threshold_acts() -> None:
    """The spec's `>=`, not `>` -- an exact-threshold spread must act."""
    gates = GatesConfig(drift_threshold=0.10, imbalance_threshold=0.20)
    # u* = 1.0; spread = (1.1 - 0.9) / 1.0 = 0.20 exactly.
    group_load = GroupLoad(
        group_name="g",
        idle=False,
        average_utilization=1.0,
        disks=(),
        storages=(StorageLoad("san-a", 1.1, 1.1), StorageLoad("san-b", 0.9, 0.9)),
    )

    decision = evaluate_group_gates(group_load, reserves_ok(group_load), gates, last_load=None)

    assert decision.act
    assert decision.imbalance_fraction == pytest.approx(0.20)


def test_idle_group_never_acts_on_first_run() -> None:
    """average_utilization == 0.0 (idle, section 4) always means no-act,
    checked independently of the drift gate's own zero/zero short-circuit
    (test_zero_last_load_and_zero_now_exits_immediately covers that one)."""
    group_load = GroupLoad(
        group_name="g",
        idle=True,
        average_utilization=0.0,
        disks=(DiskLoad("101:scsi0", 0.0, None),),
        storages=(StorageLoad("san-a", 0.0, 0.0),),
    )

    decision = evaluate_group_gates(group_load, reserves_ok(group_load), GATES, last_load=None)

    assert not decision.act
    assert "idle" in decision.reason


def test_no_series_matched_reports_the_query_filter_not_idle() -> None:
    """REVIEW.md W-06/W-07: the same act=False verdict as the ordinary idle
    case, but the reason must name the actual cause (a scoping mismatch)
    rather than call a possibly-busy group idle."""
    group_load = GroupLoad(
        group_name="g",
        idle=True,
        average_utilization=0.0,
        disks=(DiskLoad("101:scsi0", 0.0, "sample coverage 0% is below window.min_coverage"),),
        storages=(StorageLoad("san-a", 0.0, 0.0),),
        no_series_matched=True,
    )

    decision = evaluate_group_gates(group_load, reserves_ok(group_load), GATES, last_load=None)

    assert not decision.act
    assert "matched no series" in decision.reason
    assert "group is idle" not in decision.reason


def test_no_storages_at_all_does_not_act() -> None:
    group_load = GroupLoad(
        group_name="g", idle=True, average_utilization=0.0, disks=(), storages=()
    )

    decision = evaluate_group_gates(group_load, {}, GATES, last_load=None)

    assert not decision.act


# ------------------------------------------------------------------------ drift gate


def test_first_run_skips_drift_gate_and_proceeds_to_imbalance() -> None:
    group_load = section_14_2_group_load()

    decision = evaluate_group_gates(group_load, reserves_ok(group_load), GATES, last_load=None)

    assert decision.drift_fraction is None
    assert decision.imbalance_fraction is not None  # imbalance gate did run


def test_drift_below_threshold_blocks_even_a_large_imbalance() -> None:
    group_load = section_14_2_group_load()  # 255% imbalance -- would act on its own
    load_now = group_load.load_by_disk_key()
    last_load = dict(load_now)  # identical -- zero drift

    decision = evaluate_group_gates(group_load, reserves_ok(group_load), GATES, last_load=last_load)

    assert not decision.act
    assert decision.drift_fraction == 0.0
    assert decision.imbalance_fraction is None  # never reached
    assert "drift" in decision.reason


def test_drift_at_or_above_threshold_proceeds_to_imbalance() -> None:
    group_load = GroupLoad(
        group_name="g",
        idle=False,
        average_utilization=1.0,
        disks=(DiskLoad("101:scsi0", 1.0, None), DiskLoad("102:scsi0", 1.0, None)),
        storages=(StorageLoad("san-a", 1.0, 1.0), StorageLoad("san-b", 1.0, 1.0)),
    )
    # l1_last = 2.0 (1.0 + 1.0); l1_diff = |1.0-0.5| + |1.0-1.5| = 1.0 -> 50% drift.
    last_load = {"101:scsi0": 0.5, "102:scsi0": 1.5}

    decision = evaluate_group_gates(group_load, reserves_ok(group_load), GATES, last_load=last_load)

    assert decision.drift_fraction == 0.5
    assert decision.imbalance_fraction is not None  # imbalance gate ran (spread=0 -> no act)
    assert not decision.act  # balanced group, so imbalance gate says no despite the drift


def test_drift_alignment_counts_a_new_disk_fully() -> None:
    """A disk with no entry in `last_load` (created since the last balance)
    must contribute its full current load to the drift numerator."""
    group_load = GroupLoad(
        group_name="g",
        idle=False,
        average_utilization=1.0,
        disks=(DiskLoad("101:scsi0", 1.0, None), DiskLoad("102:scsi0", 2.0, None)),
        storages=(StorageLoad("san-a", 3.0, 3.0),),
    )
    last_load = {"101:scsi0": 1.0}  # 102:scsi0 is new since the last balance

    decision = evaluate_group_gates(group_load, reserves_ok(group_load), GATES, last_load=last_load)

    # l1_last = 1.0; l1_diff = |1-1| + |2-0| = 2.0 -> 200% drift.
    assert decision.drift_fraction == 2.0


def test_zero_last_load_with_nonzero_now_is_fully_drifted() -> None:
    group_load = section_14_2_group_load()
    last_load = {key: 0.0 for key in group_load.load_by_disk_key()}

    decision = evaluate_group_gates(group_load, reserves_ok(group_load), GATES, last_load=last_load)

    assert decision.drift_fraction == 1.0
    assert decision.imbalance_fraction is not None  # proceeded to the imbalance gate


def test_zero_last_load_and_zero_now_exits_immediately() -> None:
    group_load = GroupLoad(
        group_name="g",
        idle=True,
        average_utilization=0.0,
        disks=(DiskLoad("101:scsi0", 0.0, None),),
        storages=(StorageLoad("san-a", 0.0, 0.0),),
    )
    last_load = {"101:scsi0": 0.0}

    decision = evaluate_group_gates(group_load, reserves_ok(group_load), GATES, last_load=last_load)

    assert not decision.act
    assert decision.drift_fraction == 0.0
    assert decision.imbalance_fraction is None  # exited before the imbalance gate ran
    assert "nothing to balance" in decision.reason
