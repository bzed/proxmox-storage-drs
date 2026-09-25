# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Move ordering. See proxmox_storage_drs/schedule.py.

Cross-checked against IMPLEMENTATION_PLAN.md section 14.4's ordering
example: 102:scsi0 first (it alone repairs san-a's reserve violation and
has the largest imbalance reduction), then 101:scsi1, then 105:scsi0 --
reproduced here from the objective/reserve primitives directly, not typed
in as an expected constant, so a change to either would break this test.
"""

from __future__ import annotations

import dataclasses

from proxmox_storage_drs.config import ObjectiveConfig
from proxmox_storage_drs.heuristic import run_heuristic
from proxmox_storage_drs.reserve import compute_reserve_status
from proxmox_storage_drs.schedule import order_moves, transient_invariant_ok
from proxmox_storage_drs.topology import Disk, Group, Storage

TIB = 1 << 40


def make_disk(key: str, size_tib: float, storage: str) -> Disk:
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
        pinned_reason=None,
    )


def make_storage(
    id_: str,
    capacity_tib: float = 8.0,
    reserve_factor: float = 2.0,
    foreign_used_tib: float = 0.0,
    free_space_soft_bytes: int = 0,
    free_space_hard_bytes: int | None = None,
) -> Storage:
    return Storage(
        id=id_,
        capability_weight=1.0,
        reserve_factor=reserve_factor,
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
        allowed_formats=frozenset({"raw", "qcow2"}),
    )


_SECTION_14_DISKS = (
    ("101:scsi0", 2.0, "san-a"),
    ("101:scsi1", 1.0, "san-a"),
    ("102:scsi0", 1.5, "san-a"),
    ("103:scsi0", 0.5, "san-b"),
    ("104:scsi0", 1.0, "san-b"),
    ("105:scsi0", 0.5, "san-c"),
)
_SECTION_14_LOADS = {
    "101:scsi0": 3.0,
    "101:scsi1": 1.0,
    "102:scsi0": 2.5,
    "103:scsi0": 0.4,
    "104:scsi0": 0.3,
    "105:scsi0": 0.2,
}


def section_14_group() -> Group:
    disks = tuple(make_disk(key, size, storage) for key, size, storage in _SECTION_14_DISKS)
    storages = (make_storage("san-a"), make_storage("san-b"), make_storage("san-c"))
    return Group(name="fc-tier1", storages=storages, disks=disks)


# delta_capacity_spread=0.0: this file's section 14.4 ordering fixture is
# the classic beta demonstration, cross-checked at delta=0 -- see
# IMPLEMENTATION_PLAN.md section 14.3's own framing ("the classic beta
# demonstration kept at delta = 0"); at the section 12 default (0.5) the
# two-move plan wins instead, which is a different, already-covered case.
DEFAULT_OBJECTIVE = ObjectiveConfig(
    alpha_spread=1.0,
    beta_move_count=0.25,
    gamma_move_bytes_per_tib=0.05,
    kappa_vm_affinity=0.50,
    delta_capacity_spread=0.0,
)


# -------------------------------------------------------------- section 14.4


def test_section_14_4_ordering_reproduced_exactly() -> None:
    group = section_14_group()
    heuristic_result = run_heuristic(group, _SECTION_14_LOADS, DEFAULT_OBJECTIVE)
    assert heuristic_result.breakdown.moves == 3  # sanity: this is the three-move plan

    result = order_moves(group, heuristic_result.assignment, _SECTION_14_LOADS, DEFAULT_OBJECTIVE)

    assert not result.deadlocked
    # 102:scsi0 first (resolves the reserve violation), same as before.
    # 105:scsi0 now ranks ahead of 101:scsi1 -- section 5.4's fragmentation
    # term joined the persistent-objective ranking (section 8.2), and
    # applying 101:scsi1's own move splits VM 101 (still whole on san-a
    # after move 1), a cost 105:scsi0's move does not pay, so its
    # persistent_reduction is now the larger one.
    assert [m.disk_key for m in result.order] == ["102:scsi0", "105:scsi0", "101:scsi1"]
    assert result.order[0].from_storage == "san-a"
    assert result.order[0].to_storage == "san-c"
    assert result.order[0].resolves_reserve_violation
    assert not result.order[1].resolves_reserve_violation
    assert not result.order[2].resolves_reserve_violation


def test_section_14_4_transient_checks_match_the_plan_exactly() -> None:
    """The plan's own arithmetic: move 1 -> 5.0 <= 8.0, move 2 -> 4.5 <= 8.0,
    move 3 -> 5.0 <= 8.0 (all as `used + f*max(Z,z)`)."""
    group = section_14_group()
    state = {key: storage for key, _size, storage in _SECTION_14_DISKS}
    storages_by_id = {s.id: s for s in group.storages}
    disks_by_key = {d.key: d for d in group.disks}

    # Move 1: 102:scsi0 (1.5 TiB) -> san-c. san-c has 105:scsi0 (0.5 TiB)
    # only: used 0.5+1.5=2.0, f*max(0.5,1.5)=2*1.5=3.0, total 5.0 <= 8.0.
    assert transient_invariant_ok(group, state, disks_by_key["102:scsi0"], storages_by_id["san-c"])
    state["102:scsi0"] = "san-c"

    # Move 2: 101:scsi1 (1.0 TiB) -> san-b. san-b has 103(0.5)+104(1.0)=1.5
    # used: used 1.5+1.0=2.5, f*max(1.0,1.0)=2.0, total 4.5 <= 8.0.
    assert transient_invariant_ok(group, state, disks_by_key["101:scsi1"], storages_by_id["san-b"])
    state["101:scsi1"] = "san-b"

    # Move 3: 105:scsi0 (0.5 TiB) -> san-b. san-b now has 103+104+101:scsi1
    # = 2.5 used: used 2.5+0.5=3.0, f*max(1.0,0.5)=2.0, total 5.0 <= 8.0.
    assert transient_invariant_ok(group, state, disks_by_key["105:scsi0"], storages_by_id["san-b"])


def test_transient_invariant_rejects_a_move_that_would_overflow_the_target() -> None:
    group = Group(
        name="g",
        storages=(make_storage("san-a", capacity_tib=8.0), make_storage("san-b", capacity_tib=2.0)),
        disks=(make_disk("101:scsi0", 3.0, "san-a"),),
    )
    state = {"101:scsi0": "san-a"}
    target = next(s for s in group.storages if s.id == "san-b")
    disk = group.disks[0]
    # 3.0 used + 2*max(0,3.0)=6.0 -> 9.0 > 2.0 capacity.
    assert not transient_invariant_ok(group, state, disk, target)


def test_transient_invariant_applies_the_hard_free_bytes_floor() -> None:
    """A storage with no existing disks and a tiny arriving one must still
    reserve `free_space_hard_bytes`, not just `f_b * z_d`."""
    huge_floor = round(2.0 * TIB)  # bigger than san-b's whole 1.0 TiB capacity
    group = Group(
        name="g",
        storages=(
            make_storage("san-a"),
            make_storage(
                "san-b",
                capacity_tib=1.0,
                free_space_soft_bytes=huge_floor,
                free_space_hard_bytes=huge_floor,
            ),
        ),
        disks=(make_disk("101:scsi0", 0.01, "san-a"),),
    )
    state = {"101:scsi0": "san-a"}
    target = next(s for s in group.storages if s.id == "san-b")
    disk = group.disks[0]
    assert not transient_invariant_ok(group, state, disk, target)

    no_floor_group = Group(
        name="g",
        storages=(make_storage("san-a"), make_storage("san-b", capacity_tib=1.0)),
        disks=(make_disk("101:scsi0", 0.01, "san-a"),),
    )
    no_floor_target = next(s for s in no_floor_group.storages if s.id == "san-b")
    assert transient_invariant_ok(no_floor_group, state, disk, no_floor_target)


# ---------------------------------------------------------------------- deadlock


def test_deadlock_is_reported_not_forced() -> None:
    """Two disks, both storages already full: the target assignment swaps
    them, which is feasible as an endpoint, but neither individual move can
    ever be transient-feasible (this module deliberately does not
    implement staging, section 8.3 option 1 -- see the module docstring),
    so scheduling must report the deadlock rather than force either one."""
    storages = (
        make_storage("san-a", capacity_tib=2.0, reserve_factor=0.0),
        make_storage("san-b", capacity_tib=2.0, reserve_factor=0.0),
    )
    disks = (make_disk("101:scsi0", 2.0, "san-a"), make_disk("102:scsi0", 2.0, "san-b"))
    group = Group(name="g", storages=storages, disks=disks)
    loads = {"101:scsi0": 1.0, "102:scsi0": 5.0}
    target_assignment = {"101:scsi0": "san-b", "102:scsi0": "san-a"}  # a straight swap

    result = order_moves(group, target_assignment, loads, DEFAULT_OBJECTIVE)

    assert result.order == ()
    assert set(result.deadlocked) == {"101:scsi0", "102:scsi0"}
    assert result.deadlocked_msg is not None
    assert "101:scsi0" in result.deadlocked_msg
    assert "no safe order found" in result.deadlocked_msg


def test_no_deadlock_message_when_fully_scheduled() -> None:
    group = section_14_group()
    heuristic_result = run_heuristic(group, _SECTION_14_LOADS, DEFAULT_OBJECTIVE)
    result = order_moves(group, heuristic_result.assignment, _SECTION_14_LOADS, DEFAULT_OBJECTIVE)
    assert result.deadlocked_msg is None


# --------------------------------------------------------------- no moves needed


def test_no_pending_moves_returns_an_empty_order() -> None:
    group = section_14_group()
    identity_assignment = {key: storage for key, _size, storage in _SECTION_14_DISKS}
    result = order_moves(group, identity_assignment, _SECTION_14_LOADS, DEFAULT_OBJECTIVE, 0)
    assert result.order == ()
    assert result.deadlocked == ()


# ------------------------------------------------------------- reserve priority


def test_reserve_resolving_move_is_scheduled_before_a_non_resolving_one() -> None:
    """Section 8.2 priority 1: among the *feasible* moves, one resolving a
    currently-violating storage is scheduled before any move whose source
    is not violating -- the priority filter excludes the non-resolving
    move from consideration entirely, it is not merely outranked."""
    storages = (
        make_storage("san-a", capacity_tib=4.0),  # will violate
        make_storage("san-b", capacity_tib=20.0),
        make_storage("san-c", capacity_tib=20.0),
    )
    disks = (
        make_disk("101:scsi0", 3.0, "san-a"),  # san-a: used 3.0, f*3.0=6.0 -> 9.0 > 4.0: violates
        make_disk("102:scsi0", 0.1, "san-b"),  # san-b is not violating
        make_disk("103:scsi0", 0.1, "san-c"),
    )
    group = Group(name="g", storages=storages, disks=disks)
    # 100.0 makes 102:scsi0 the tempting move on pure ratio if priority
    # filtering did not exclude it outright.
    loads = {"101:scsi0": 1.0, "102:scsi0": 100.0, "103:scsi0": 0.0}
    target_assignment = {
        "101:scsi0": "san-b",  # resolves san-a's violation
        "102:scsi0": "san-c",
        # 103:scsi0 stays on san-c -- moving it to the still-violating
        # san-a is never transient-feasible, so it is not part of this plan.
    }

    result = order_moves(group, target_assignment, loads, DEFAULT_OBJECTIVE)

    assert result.order[0].disk_key == "101:scsi0"
    assert result.order[0].resolves_reserve_violation
    assert [m.disk_key for m in result.order] == ["101:scsi0", "102:scsi0"]


def test_ordering_prefers_the_larger_persistent_reduction_once_delta_matters() -> None:
    """REVIEW.md AA-04: section 8.2 was revised to rank candidates by "the
    alpha and delta terms of section 5.4 -- the parts whose improvement
    persists", not by imbalance (alpha) alone -- but `order_moves()` kept
    ranking by `imbalance_term` only, so a pending move trading I/O
    balance for data spread could be scheduled in the wrong order. Two
    disks, both starting on ``a``, moving to different destinations:
    ``102:scsi0`` has the better imbalance-only ratio (it is picked first
    at ``delta_capacity_spread=0``), but ``101:scsi0`` has the better
    *combined* alpha+delta ratio once delta is large enough to matter --
    the section 8.2 ranking must switch to it, not stay on 102:scsi0."""
    storages = (
        make_storage("a", capacity_tib=27.0, foreign_used_tib=10.0),
        make_storage("b", capacity_tib=23.5),
        make_storage("c", capacity_tib=25.0),
    )
    disks = (
        make_disk("101:scsi0", 4.8, "a"),
        make_disk("102:scsi0", 3.9, "a"),
    )
    group = Group(name="g", storages=storages, disks=disks)
    loads = {"101:scsi0": 0.15, "102:scsi0": 8.2}
    target_assignment = {"101:scsi0": "b", "102:scsi0": "c"}

    imbalance_only = ObjectiveConfig(
        alpha_spread=1.0,
        beta_move_count=0.0,
        gamma_move_bytes_per_tib=0.0,
        kappa_vm_affinity=0.0,
        delta_capacity_spread=0.0,
    )
    result_no_delta = order_moves(group, target_assignment, loads, imbalance_only)
    assert result_no_delta.order[0].disk_key == "102:scsi0"

    delta_matters = dataclasses.replace(imbalance_only, delta_capacity_spread=2.0)
    result_with_delta = order_moves(group, target_assignment, loads, delta_matters)
    assert result_with_delta.order[0].disk_key == "101:scsi0"


def test_tiny_disk_bytes_ranks_a_zero_cost_move_first_regardless_of_its_own_reduction() -> None:
    """Section 8.2: "cost_m = 0 (a tiny disk, section 7.1) ranks first --
    free value, delivered before anything pays". Two VMs each have an
    efidisk0 stranded off their big disk's storage; VM 302 is much busier
    (five near-idle filler VMs push its w_v to ~7, section 5.4), so
    302:efidisk0's reunion is worth far more than 301:efidisk0's -- with no
    exemption, it ranks first purely on that larger persistent_reduction
    per byte. Covering only 301:efidisk0's 1 MiB (not 302:efidisk0's 4 MiB)
    with tiny_disk_bytes must still put it first: a zero-cost move beats
    any nonzero-cost one outright, not merely by comparing magnitudes."""
    storages = (
        make_storage("san-a", capacity_tib=80.0),
        make_storage("san-b", capacity_tib=80.0),
        make_storage("san-c", capacity_tib=80.0),
    )
    disks = [
        make_disk("301:scsi0", 1.0, "san-a"),
        make_disk("301:efidisk0", 1 / (1024 * 1024), "san-b"),
        make_disk("302:scsi0", 1.0, "san-a"),
        make_disk("302:efidisk0", 4 / (1024 * 1024), "san-c"),
    ]
    loads = {"301:scsi0": 1.0, "301:efidisk0": 0.0, "302:scsi0": 1000.0, "302:efidisk0": 0.0}
    for i in range(5):
        key = f"{400 + i}:scsi0"
        disks.append(make_disk(key, 1.0, "san-a"))
        loads[key] = 0.001
    group = Group(name="g", storages=storages, disks=tuple(disks))
    target = {d.key: d.current_storage for d in disks}
    target["301:efidisk0"] = "san-a"
    target["302:efidisk0"] = "san-a"
    objective = ObjectiveConfig(
        alpha_spread=1.0,
        beta_move_count=0.25,
        gamma_move_bytes_per_tib=0.05,
        kappa_vm_affinity=0.5,
        delta_capacity_spread=0.0,
    )

    no_exemption = order_moves(group, target, loads, objective)
    assert no_exemption.order[0].disk_key == "302:efidisk0"  # bigger reduction wins on ratio

    with_exemption = order_moves(group, target, loads, objective, tiny_disk_bytes=2 * 1024 * 1024)
    assert with_exemption.order[0].disk_key == "301:efidisk0"  # zero cost wins outright


# ----------------------------------------------------- the shortfall never rises (AI-01)


def _shortfall_tib_bytes(group: Group, assignment: dict[str, str]) -> int:
    return sum(
        compute_reserve_status(
            storage, group.disks, storage_of=lambda d: assignment.get(d.key, d.current_storage)
        ).shortfall_bytes
        for storage in group.storages
    )


def _one_move_that_would_leave_san_b_slightly_short(
    hard_tib: float,
) -> tuple[Group, dict[str, str]]:
    """san-b is compliant now (10 TiB free against a 9.001 TiB requirement) and
    would be ~1 GiB short once a 1 TiB disk lands on it. The target assignment
    is written by hand -- it is *any* assignment whose endpoint is slightly
    worse than the current one, whichever backend produced it."""
    group = Group(
        name="g",
        storages=(
            make_storage("san-a", capacity_tib=10.0),
            make_storage(
                "san-b",
                capacity_tib=10.0,
                free_space_soft_bytes=round(9.001 * TIB),
                free_space_hard_bytes=round(hard_tib * TIB),
            ),
        ),
        disks=(make_disk("1:scsi0", 1.0, "san-a"), make_disk("2:scsi0", 1.0, "san-a")),
    )
    return group, {"1:scsi0": "san-b", "2:scsi0": "san-a"}


def test_hard_equal_soft_never_lets_the_executed_plan_raise_the_shortfall() -> None:
    """The guarantee the corpus's check 4 actually rests on when ``hard = soft``
    (REVIEW.md AI-01): a move is scheduled only if its *target* clears ``hard``
    on arrival, so a target assignment that would raise ``sum(r_s)`` -- from any
    backend -- is stopped here, and ``final_assignment`` (what really runs)
    keeps the current shortfall."""
    group, target = _one_move_that_would_leave_san_b_slightly_short(hard_tib=9.001)
    result = order_moves(group, target, {"1:scsi0": 4.0, "2:scsi0": 4.0}, DEFAULT_OBJECTIVE)
    assert result.deadlocked == ("1:scsi0",)
    assert result.order == ()
    assert _shortfall_tib_bytes(group, result.final_assignment) == _shortfall_tib_bytes(group, {})


def test_hard_below_soft_permits_a_plan_that_ends_below_soft() -> None:
    """The other side of the same rule, by design (section 5.3.1): ``hard`` is
    the transient floor, so with ``hard < soft`` the scheduler no longer
    protects the endpoint -- that is the solver's job, and it is exactly the
    configuration in which check 4 can fire on a backend whose objective can
    trade reserve for balance."""
    group, target = _one_move_that_would_leave_san_b_slightly_short(hard_tib=0.0)
    result = order_moves(group, target, {"1:scsi0": 4.0, "2:scsi0": 4.0}, DEFAULT_OBJECTIVE)
    assert result.deadlocked == ()
    assert [m.disk_key for m in result.order] == ["1:scsi0"]
    assert _shortfall_tib_bytes(group, result.final_assignment) > _shortfall_tib_bytes(group, {})
