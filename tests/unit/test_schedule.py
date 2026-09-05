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

from proxmox_storage_drs.config import ObjectiveConfig
from proxmox_storage_drs.heuristic import run_heuristic
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


def make_storage(id_: str, capacity_tib: float = 8.0, reserve_factor: float = 2.0) -> Storage:
    return Storage(
        id=id_,
        capability_weight=1.0,
        reserve_factor=reserve_factor,
        saturation_load=None,
        capacity_bytes=round(capacity_tib * TIB),
        used_bytes=0,
        foreign_used_bytes=0,
        saferemove=False,
        saferemove_throughput_bytes_per_sec=None,
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


DEFAULT_OBJECTIVE = ObjectiveConfig(
    alpha_spread=1.0, beta_move_count=0.25, gamma_move_bytes_per_tib=0.05, kappa_vm_affinity=0.50
)


# -------------------------------------------------------------- section 14.4


def test_section_14_4_ordering_reproduced_exactly() -> None:
    group = section_14_group()
    heuristic_result = run_heuristic(group, _SECTION_14_LOADS, DEFAULT_OBJECTIVE, min_free_bytes=0)
    assert heuristic_result.breakdown.moves == 3  # sanity: this is the three-move plan

    result = order_moves(
        group, heuristic_result.assignment, _SECTION_14_LOADS, DEFAULT_OBJECTIVE, min_free_bytes=0
    )

    assert not result.deadlocked
    assert [m.disk_key for m in result.order] == ["102:scsi0", "101:scsi1", "105:scsi0"]
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
    assert transient_invariant_ok(
        group, state, disks_by_key["102:scsi0"], storages_by_id["san-c"], 0
    )
    state["102:scsi0"] = "san-c"

    # Move 2: 101:scsi1 (1.0 TiB) -> san-b. san-b has 103(0.5)+104(1.0)=1.5
    # used: used 1.5+1.0=2.5, f*max(1.0,1.0)=2.0, total 4.5 <= 8.0.
    assert transient_invariant_ok(
        group, state, disks_by_key["101:scsi1"], storages_by_id["san-b"], 0
    )
    state["101:scsi1"] = "san-b"

    # Move 3: 105:scsi0 (0.5 TiB) -> san-b. san-b now has 103+104+101:scsi1
    # = 2.5 used: used 2.5+0.5=3.0, f*max(1.0,0.5)=2.0, total 5.0 <= 8.0.
    assert transient_invariant_ok(
        group, state, disks_by_key["105:scsi0"], storages_by_id["san-b"], 0
    )


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
    assert not transient_invariant_ok(group, state, disk, target, 0)


def test_transient_invariant_applies_the_min_free_bytes_floor() -> None:
    """A storage with no existing disks and a tiny arriving one must still
    reserve `min_free_bytes`, not just `f_b * z_d`."""
    group = Group(
        name="g",
        storages=(make_storage("san-a"), make_storage("san-b", capacity_tib=1.0)),
        disks=(make_disk("101:scsi0", 0.01, "san-a"),),
    )
    state = {"101:scsi0": "san-a"}
    target = next(s for s in group.storages if s.id == "san-b")
    disk = group.disks[0]
    assert transient_invariant_ok(group, state, disk, target, min_free_bytes=0)
    huge_floor = round(2.0 * TIB)  # bigger than san-b's whole 1.0 TiB capacity
    assert not transient_invariant_ok(group, state, disk, target, min_free_bytes=huge_floor)


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

    result = order_moves(group, target_assignment, loads, DEFAULT_OBJECTIVE, min_free_bytes=0)

    assert result.order == ()
    assert set(result.deadlocked) == {"101:scsi0", "102:scsi0"}
    assert result.deadlocked_msg is not None
    assert "101:scsi0" in result.deadlocked_msg
    assert "section 8.1" in result.deadlocked_msg


def test_no_deadlock_message_when_fully_scheduled() -> None:
    group = section_14_group()
    heuristic_result = run_heuristic(group, _SECTION_14_LOADS, DEFAULT_OBJECTIVE, min_free_bytes=0)
    result = order_moves(
        group, heuristic_result.assignment, _SECTION_14_LOADS, DEFAULT_OBJECTIVE, min_free_bytes=0
    )
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

    result = order_moves(group, target_assignment, loads, DEFAULT_OBJECTIVE, min_free_bytes=0)

    assert result.order[0].disk_key == "101:scsi0"
    assert result.order[0].resolves_reserve_violation
    assert [m.disk_key for m in result.order] == ["101:scsi0", "102:scsi0"]
