# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The heuristic solver. See proxmox_storage_drs/heuristic.py.

Cross-checked against IMPLEMENTATION_PLAN.md section 14's worked example --
not just the moves and per-storage loads (section 14.2/14.3), but the exact
total objective values REVIEW.md Appendix A independently re-derived by
hand (2.533333 / 2.658333 / 3.158333 / 3.283333), which is the strongest
evidence available that this module's objective and this module's search
agree with the plan's own arithmetic, not merely with each other.
"""

from __future__ import annotations

import dataclasses

import pytest

from proxmox_storage_drs.config import ObjectiveConfig
from proxmox_storage_drs.heuristic import (
    _repair,
    evaluate_assignment,
    run_heuristic,
    seed_assignment,
)
from proxmox_storage_drs.reserve import compute_reserve_status
from proxmox_storage_drs.topology import Disk, Group, Storage

TIB = 1 << 40


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


def make_storage(id_: str, capacity_tib: float = 8.0, capability_weight: float = 1.0) -> Storage:
    return Storage(
        id=id_,
        capability_weight=capability_weight,
        reserve_factor=2.0,
        saturation_load=None,
        capacity_bytes=round(capacity_tib * TIB),
        used_bytes=0,
        foreign_used_bytes=0,
        saferemove=False,
        saferemove_throughput_bytes_per_sec=None,
    )


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


DEFAULT_OBJECTIVE = ObjectiveConfig(
    alpha_spread=1.0, beta_move_count=0.25, gamma_move_bytes_per_tib=0.05, kappa_vm_affinity=0.50
)


# ------------------------------------------------------------------------ seeding


def test_seed_assignment_matches_current_storage_for_every_disk() -> None:
    group = section_14_group()
    assignment = seed_assignment(group)
    assert assignment == {key: storage for key, _s, _l, storage in _SECTION_14_DISKS}


def test_initial_imbalance_term_matches_section_14_2_e_before() -> None:
    group = section_14_group()
    loads = section_14_loads()
    assignment = seed_assignment(group)
    breakdown = evaluate_assignment(group, assignment, loads, DEFAULT_OBJECTIVE, 0, 7.4 / 3)
    assert breakdown.imbalance_term == pytest.approx(8.0667, abs=1e-4)
    assert breakdown.reserve_statuses["san-a"].violated
    assert breakdown.reserve_statuses["san-a"].shortfall_bytes == round(0.5 * TIB)
    assert breakdown.utilization["san-a"] == pytest.approx(6.5)  # c_s=1.0 -> u_s == L_s


# ------------------------------------------------------------- REVIEW.md Q-01


def test_spread_metric_l1_is_the_default_and_sums_every_deviation() -> None:
    group = section_14_group()
    loads = section_14_loads()
    assignment = seed_assignment(group)
    assert DEFAULT_OBJECTIVE.spread_metric == "l1"
    breakdown = evaluate_assignment(group, assignment, loads, DEFAULT_OBJECTIVE, 0, 7.4 / 3)
    assert breakdown.imbalance_term == pytest.approx(sum(breakdown.spread_e.values()))


def test_spread_metric_minmax_uses_only_the_hottest_storages_raw_utilization() -> None:
    """Section 5.4: minmax is `t >= u_s` -- the hottest storage's own u_s,
    not its deviation from u* (those disagree whenever a cold storage's
    deviation below u* happens to be the largest one, which this fixture
    is not, so this test also cross-checks the two forms are computed
    independently rather than one derived from the other by accident)."""
    group = section_14_group()
    loads = section_14_loads()
    assignment = seed_assignment(group)
    objective = dataclasses.replace(DEFAULT_OBJECTIVE, spread_metric="minmax")

    breakdown = evaluate_assignment(group, assignment, loads, objective, 0, 7.4 / 3)

    assert breakdown.imbalance_term == pytest.approx(6.5)  # san-a's raw u_s, the hottest
    assert breakdown.imbalance_term != pytest.approx(max(breakdown.spread_e.values()))
    # Both views are always populated, regardless of which metric is active.
    assert breakdown.utilization["san-a"] == pytest.approx(6.5)
    assert breakdown.spread_e["san-a"] == pytest.approx(abs(6.5 - 7.4 / 3))


def test_spread_metric_minmax_is_indifferent_to_a_second_nearly_as_bad_storage() -> None:
    """The manual's own claim, made concrete: with the same hottest storage
    (u_s=5.0) in both scenarios, minmax scores them identically no matter
    how the *other* storages are doing, while l1 correctly tells a group
    with two problem storages apart from one with only a single problem."""
    storages = (make_storage("san-a"), make_storage("san-b"), make_storage("san-c"))
    disks = (
        make_disk("101:scsi0", 1.0, 0.0, "san-a"),
        make_disk("102:scsi0", 1.0, 0.0, "san-b"),
        make_disk("103:scsi0", 1.0, 0.0, "san-c"),
    )
    group = Group(name="g", storages=storages, disks=disks)
    assignment = seed_assignment(group)
    minmax = dataclasses.replace(DEFAULT_OBJECTIVE, spread_metric="minmax")
    l1 = dataclasses.replace(DEFAULT_OBJECTIVE, spread_metric="l1")

    # Only san-a is hot; san-b/san-c already sit at the target.
    one_problem_loads = {"101:scsi0": 5.0, "102:scsi0": 3.0, "103:scsi0": 3.0}
    # san-a is equally hot, but san-b/san-c are now nearly as bad too.
    two_problem_loads = {"101:scsi0": 5.0, "102:scsi0": 2.9, "103:scsi0": 2.9}

    one_minmax = evaluate_assignment(group, assignment, one_problem_loads, minmax, 0, 3.0)
    two_minmax = evaluate_assignment(group, assignment, two_problem_loads, minmax, 0, 3.0)
    one_l1 = evaluate_assignment(group, assignment, one_problem_loads, l1, 0, 3.0)
    two_l1 = evaluate_assignment(group, assignment, two_problem_loads, l1, 0, 3.0)

    assert one_minmax.imbalance_term == pytest.approx(two_minmax.imbalance_term) == 5.0
    assert one_l1.imbalance_term != pytest.approx(two_l1.imbalance_term)
    assert two_l1.imbalance_term > one_l1.imbalance_term  # l1 correctly sees it got worse


# --------------------------------------------------------------- full heuristic runs


def test_beta_025_reproduces_the_three_move_solution() -> None:
    group = section_14_group()
    loads = section_14_loads()
    result = run_heuristic(group, loads, DEFAULT_OBJECTIVE, min_free_bytes=0)

    assert result.assignment == {
        "101:scsi0": "san-a",
        "101:scsi1": "san-b",
        "102:scsi0": "san-c",
        "103:scsi0": "san-b",
        "104:scsi0": "san-b",
        "105:scsi0": "san-b",
    }
    assert result.breakdown.moves == 3
    assert result.breakdown.imbalance_term == pytest.approx(1.1333, abs=1e-4)
    assert result.breakdown.total == pytest.approx(2.533333, abs=1e-5)
    assert not result.breakdown.reserve_statuses["san-a"].violated  # repaired
    assert result.repair_moves == 1  # 102:scsi0 alone repairs san-a


def test_beta_050_reproduces_the_two_move_solution() -> None:
    group = section_14_group()
    loads = section_14_loads()
    objective = dataclasses.replace(DEFAULT_OBJECTIVE, beta_move_count=0.50)
    result = run_heuristic(group, loads, objective, min_free_bytes=0)

    assert result.assignment == {
        "101:scsi0": "san-a",
        "101:scsi1": "san-b",
        "102:scsi0": "san-c",
        "103:scsi0": "san-b",
        "104:scsi0": "san-b",
        "105:scsi0": "san-c",  # stays -- the third move is not worth it at beta=0.50
    }
    assert result.breakdown.moves == 2
    assert result.breakdown.imbalance_term == pytest.approx(1.5333, abs=1e-4)
    assert result.breakdown.total == pytest.approx(3.158333, abs=1e-5)


def test_beta_knob_crossover_matches_section_14_3_exactly() -> None:
    """The plan's own demonstration: at beta=0.25 the three-move plan beats
    the two-move one; at beta=0.50 the reverse. Evaluate both fixed
    assignments directly (bypassing search) so this test is about the
    objective arithmetic itself, independent of whether the heuristic's
    search finds either optimum."""
    group = section_14_group()
    loads = section_14_loads()
    two_move = {
        "101:scsi0": "san-a",
        "101:scsi1": "san-b",
        "102:scsi0": "san-c",
        "103:scsi0": "san-b",
        "104:scsi0": "san-b",
        "105:scsi0": "san-c",
    }
    three_move = {**two_move, "105:scsi0": "san-b"}
    u_star = 7.4 / 3

    for beta, three_move_wins in ((0.25, True), (0.50, False)):
        objective = dataclasses.replace(DEFAULT_OBJECTIVE, beta_move_count=beta)
        two = evaluate_assignment(group, two_move, loads, objective, 0, u_star)
        three = evaluate_assignment(group, three_move, loads, objective, 0, u_star)
        assert (three.total < two.total) is three_move_wins


def test_heuristic_iterations_bounds_the_descend_search() -> None:
    """``heuristic_iterations`` caps descend's own loop: capped at 1, only
    the single best-improving move after repair is applied, not the full
    local optimum -- a real, bounded-computation guarantee worth its own
    test, not just an implementation detail."""
    group = section_14_group()
    loads = section_14_loads()
    result = run_heuristic(
        group, loads, DEFAULT_OBJECTIVE, min_free_bytes=0, heuristic_iterations=1
    )
    assert result.repair_moves == 1
    assert result.breakdown.moves == 2  # repair's move + exactly one descend step


def test_reserve_violation_is_repaired_even_with_beta_high_enough_to_forbid_balance_moves() -> None:
    """Safety first: even a beta so high that no balance-only move is ever
    worth it must still see the repair-phase move that fixes (C5)."""
    group = section_14_group()
    loads = section_14_loads()
    objective = dataclasses.replace(DEFAULT_OBJECTIVE, beta_move_count=100.0)
    result = run_heuristic(group, loads, objective, min_free_bytes=0)
    assert not result.breakdown.reserve_statuses["san-a"].violated
    assert result.repair_moves >= 1


def test_repair_does_not_oscillate_when_no_target_can_fully_absorb_the_violation() -> None:
    """A 3 TiB disk on an 8 TiB, reserve_factor=2.0 storage cannot be fully
    repaired by moving it anywhere: landing alone on either storage still
    needs 2x its own size reserved, which alone exceeds 8 TiB once you add
    the 3 TiB itself. An earlier version of `_repair` judged a candidate
    move only by whether the *source*'s shortfall fell, which it always
    does when bytes leave it -- so it moved the disk to fix the source,
    then on the next iteration moved it right back to fix the (now
    violating) target, forever alternating without ever reducing the
    group's total shortfall. The fix requires the group-wide total to
    strictly decrease, which this fixture cannot fully reach (best
    possible is 3 TiB -> 1 TiB, not 0) but must still not oscillate."""
    disks = (
        make_disk("101:scsi0", 3.0, 3.0, "san-a"),
        make_disk("102:scsi0", 2.0, 0.0, "san-a", pinned="locked: backup"),
    )
    storages = (make_storage("san-a"), make_storage("san-b"))
    group = Group(name="g", storages=storages, disks=disks)

    assignment, repairs = _repair(group, seed_assignment(group), min_free_bytes=0)

    assert repairs == 1  # not 2 -- no back-and-forth
    assert assignment == {"101:scsi0": "san-b", "102:scsi0": "san-a"}

    # Residual shortfall (1 TiB on san-b) is real and expected -- this
    # fixture cannot be fully repaired, only improved from 3 TiB to 1 TiB.
    def storage_of(d: Disk) -> str:
        return assignment[d.key]

    san_b = next(s for s in storages if s.id == "san-b")
    status = compute_reserve_status(san_b, disks, 0, storage_of=storage_of)
    assert status.shortfall_bytes == round(1.0 * TIB)


# ------------------------------------------------------------------- pinned disks


def test_pinned_disk_never_moves_even_when_it_would_improve_the_objective() -> None:
    disks = (
        make_disk("101:scsi0", 2.0, 3.0, "san-a", pinned="locked: backup"),
        make_disk("102:scsi0", 0.5, 0.1, "san-b"),
    )
    storages = (make_storage("san-a"), make_storage("san-b"))
    group = Group(name="g", storages=storages, disks=disks)
    loads = {"101:scsi0": 3.0, "102:scsi0": 0.1}

    result = run_heuristic(group, loads, DEFAULT_OBJECTIVE, min_free_bytes=0)

    assert result.assignment["101:scsi0"] == "san-a"  # never touched despite being all the load
    assert result.repair_moves == 0


def test_pinned_disks_are_excluded_from_fragmentation_by_default() -> None:
    """(C3): affinity_counts_pinned_disks=False (default) ranges over
    D^mov, so a VM whose only "spread" comes from a pinned disk is not
    counted as fragmented."""
    disks = (
        make_disk("101:scsi0", 1.0, 1.0, "san-a", pinned="locked: backup"),
        make_disk("101:scsi1", 1.0, 1.0, "san-b"),
    )
    storages = (make_storage("san-a"), make_storage("san-b"))
    group = Group(name="g", storages=storages, disks=disks)
    assignment = seed_assignment(group)

    default = evaluate_assignment(
        group, assignment, {"101:scsi0": 1.0, "101:scsi1": 1.0}, DEFAULT_OBJECTIVE, 0, 1.0
    )
    assert default.fragmentation_term == 0.0  # 101:scsi1 alone in D^mov -> 1 storage, no spread

    counting_pinned = dataclasses.replace(DEFAULT_OBJECTIVE, affinity_counts_pinned_disks=True)
    counted = evaluate_assignment(
        group, assignment, {"101:scsi0": 1.0, "101:scsi1": 1.0}, counting_pinned, 0, 1.0
    )
    assert counted.fragmentation_term == pytest.approx(0.50)  # now both disks count -> 2 storages


# -------------------------------------------------------------------------- swaps


def test_descend_uses_a_swap_when_no_single_move_is_feasible() -> None:
    """Section 5.5: "when both storages are near their capacity limit, no
    single move is feasible, and only an exchange of two disks can improve
    the balance." Both storages here have exactly 0.5 TiB of headroom --
    too little for any of the four 1.0 TiB disks to move alone -- so the
    only way to reach a better balance is to swap one disk from each."""
    a1 = make_disk("201:scsi0", 1.0, 1.0, "san-a")
    a2 = make_disk("202:scsi0", 1.0, 1.0, "san-a")
    b1 = make_disk("203:scsi0", 1.0, 3.0, "san-b")
    b2 = make_disk("204:scsi0", 1.0, 3.0, "san-b")
    # reserve_factor=0 isolates pure capacity-fit reasoning from (C5)'s
    # snapshot-reserve overhead, which is not what this test is about.
    storages = (
        dataclasses.replace(make_storage("san-a", capacity_tib=2.5), reserve_factor=0.0),
        dataclasses.replace(make_storage("san-b", capacity_tib=2.5), reserve_factor=0.0),
    )
    group = Group(name="g", storages=storages, disks=(a1, a2, b1, b2))
    loads = {"201:scsi0": 1.0, "202:scsi0": 1.0, "203:scsi0": 3.0, "204:scsi0": 3.0}

    initial = seed_assignment(group)
    before = evaluate_assignment(group, initial, loads, DEFAULT_OBJECTIVE, 0, 4.0)
    assert before.imbalance_term == pytest.approx(4.0)  # |2.0-4.0| + |6.0-4.0|

    result = run_heuristic(group, loads, DEFAULT_OBJECTIVE, min_free_bytes=0)

    assert result.breakdown.imbalance_term == pytest.approx(0.0, abs=1e-9)  # perfectly balanced
    assert result.breakdown.moves == 2  # exactly one disk from each side, swapped
    assert result.assignment["201:scsi0"] != result.assignment["202:scsi0"]
    assert result.assignment["203:scsi0"] != result.assignment["204:scsi0"]
