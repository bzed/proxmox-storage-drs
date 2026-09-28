# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Section 5.3 (C8): small disks follow their VM. See
proxmox_storage_drs/topology.py's ``small_disk_placement_ok()`` and its two
solver transcriptions (``optimize.py``, ``heuristic.py``).

The scenario the rule exists for is reduced from a real bundle: a storage
hundreds of GiB short of its free-space requirement, its big disks pinned,
and the only movable disk a 528 KiB efidisk0. Without (C8), moving that EFI
disk alone frees half a MiB -- crossing a whole-MiB boundary of the
shortfall, it even counts as a 1 MiB "repair" -- while splitting it from
its VM.
"""

from __future__ import annotations

import dataclasses

import pytest

from proxmox_storage_drs.config import ObjectiveConfig
from proxmox_storage_drs.heuristic import run_heuristic
from proxmox_storage_drs.optimize import cbc_available, solve
from proxmox_storage_drs.topology import (
    LONE_SMALL_DISK_REASON,
    Disk,
    Group,
    Storage,
    pin_lone_small_disks,
    small_disk_placement_ok,
    small_disks_follow_their_vm,
)

MIB = 1 << 20
GIB = 1 << 30
TIB = 1 << 40
TINY = 64 * MIB
EFI_BYTES = 540_672  # 528 KiB, a real efidisk0


def disk(key: str, size_bytes: int, storage: str, pinned: str | None = None) -> Disk:
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


def storage(id_: str, capacity_bytes: int, soft_bytes: int = 0) -> Storage:
    return Storage(
        id=id_,
        capability_weight=1.0,
        reserve_factor=0.0,
        capacity_bytes=capacity_bytes,
        used_bytes=0,
        foreign_used_bytes=0,
        saferemove=False,
        saferemove_throughput_bytes_per_sec=None,
        free_space_soft_bytes=soft_bytes,
        free_space_hard_bytes=soft_bytes,
        storage_type="dir",
        allowed_formats=frozenset({"raw", "qcow2"}),
    )


def current(d: Disk) -> str:
    return d.current_storage


# ------------------------------------------------------------------ the rule


def split_vm_group() -> Group:
    """VM 201 split across a and c: scsi0 (big) on a, efidisk0 (small) on c."""
    return Group(
        name="g",
        storages=(storage("a", TIB), storage("b", TIB), storage("c", TIB)),
        disks=(disk("201:scsi0", 100 * GIB, "a"), disk("201:efidisk0", EFI_BYTES, "c")),
    )


def test_a_small_disk_may_stay_or_rejoin_a_larger_disk_of_its_vm_but_not_wander() -> None:
    group = split_vm_group()
    efi = group.disks[1]
    assert small_disk_placement_ok(group, efi, "c", current, TINY)  # stays
    assert small_disk_placement_ok(group, efi, "a", current, TINY)  # rejoins scsi0
    assert not small_disk_placement_ok(group, efi, "b", current, TINY)  # alone


def test_a_small_disk_may_follow_its_vms_larger_disk_to_where_it_is_going() -> None:
    group = split_vm_group()
    moved = {"201:scsi0": "b", "201:efidisk0": "b"}
    assert small_disks_follow_their_vm(group, lambda d: moved[d.key], TINY)
    # ... but not be left on b once the big disk goes elsewhere.
    stranded = {"201:scsi0": "a", "201:efidisk0": "b"}
    assert not small_disks_follow_their_vm(group, lambda d: stranded[d.key], TINY)


def test_the_rule_is_off_at_tiny_disk_bytes_zero_and_never_touches_a_larger_disk() -> None:
    group = split_vm_group()
    efi, scsi0 = group.disks[1], group.disks[0]
    assert small_disk_placement_ok(group, efi, "b", current, 0)
    assert small_disks_follow_their_vm(group, lambda d: "b", 0)
    assert small_disk_placement_ok(group, scsi0, "b", current, TINY)


def test_other_vms_larger_disks_are_no_anchor() -> None:
    group = Group(
        name="g",
        storages=(storage("a", TIB), storage("b", TIB)),
        disks=(
            disk("201:scsi0", 100 * GIB, "a"),
            disk("201:efidisk0", EFI_BYTES, "a"),
            disk("202:scsi0", 100 * GIB, "b"),
        ),
    )
    assert not small_disk_placement_ok(group, group.disks[1], "b", current, TINY)


def test_pin_lone_small_disks_pins_only_a_vm_with_nothing_larger_in_the_group() -> None:
    """VM 301's big disks live in another group: its efidisk0 is alone here
    and never moves. VM 302 has a larger disk here, so its efidisk0 stays
    movable. Already-pinned disks keep their own reason."""
    disks = (
        disk("301:efidisk0", EFI_BYTES, "a"),
        disk("302:scsi0", 100 * GIB, "a"),
        disk("302:efidisk0", EFI_BYTES, "a"),
        disk("303:tpmstate0", 4 * MIB, "a", pinned="snapshots present (1)"),
    )
    pinned = pin_lone_small_disks(disks, TINY)
    assert [d.pinned_reason for d in pinned] == [
        LONE_SMALL_DISK_REASON,
        None,
        None,
        "snapshots present (1)",
    ]
    assert pin_lone_small_disks(disks, 0) == disks


# ------------------------------------------- the EFI-disk "repair", both solvers


def efi_repair_group() -> Group:
    """ "slow" is short by 1000.2 MiB, so moving the 528 KiB EFI disk crosses a
    whole-MiB boundary: the shortfall drops by exactly 1 MiB. Its VM's big
    disk is pinned there. "fast" has all the room in the world."""
    used = 650 * GIB
    soft = 5 * TIB - used + 1000 * MIB + MIB // 5
    return Group(
        name="g",
        storages=(storage("slow", 5 * TIB, soft), storage("fast", 20 * TIB)),
        disks=(
            disk("616577:virtio0", used - EFI_BYTES, "slow", pinned="pending config change"),
            disk("616577:efidisk0", EFI_BYTES, "slow"),
            disk("101:scsi0", TIB, "fast"),
        ),
    )


LOADS = {"616577:virtio0": 0.0, "616577:efidisk0": 0.0, "101:scsi0": 1.0}
OBJECTIVE = ObjectiveConfig(delta_capacity_spread=0.0)


@pytest.mark.skipif(not cbc_available(), reason="pulp not installed")
@pytest.mark.parametrize(("tiny", "efi_moves"), [(0, True), (TINY, False)])
def test_cbc_moves_the_efi_disk_alone_only_without_the_rule(tiny: int, efi_moves: bool) -> None:
    """Lexicographic stage 1 takes any shortfall reduction, however small,
    so without (C8) it moves the EFI disk; with it, the disk has no larger
    disk of its VM to follow off "slow" and stays."""
    result = solve(efi_repair_group(), LOADS, OBJECTIVE, "cbc", 10.0, 0.0, tiny_disk_bytes=tiny)
    assert result is not None
    assert (result.assignment["616577:efidisk0"] == "fast") is efi_moves


@pytest.mark.parametrize(("tiny", "repairs"), [(0, 1), (TINY, 0)])
def test_the_heuristics_repair_step_skips_a_lone_small_disk(tiny: int, repairs: int) -> None:
    result = run_heuristic(efi_repair_group(), LOADS, OBJECTIVE, tiny_disk_bytes=tiny)
    assert result.repair_moves == repairs
    if tiny:
        assert result.assignment["616577:efidisk0"] == "slow"


@pytest.mark.skipif(not cbc_available(), reason="pulp not installed")
def test_cbc_moves_a_small_disk_together_with_its_vm() -> None:
    """The rule restricts where a small disk goes, never whether its VM
    moves: VM 201 carries all the load on "a", and the plan moves both of
    its disks to the empty "b" together."""
    group = Group(
        name="g",
        storages=(storage("a", 10 * TIB), storage("b", 10 * TIB)),
        disks=(
            disk("201:scsi0", 100 * GIB, "a"),
            disk("201:efidisk0", EFI_BYTES, "a"),
            disk("202:scsi0", 100 * GIB, "a"),
        ),
    )
    loads = {"201:scsi0": 5.0, "201:efidisk0": 0.0, "202:scsi0": 5.0}
    result = solve(group, loads, OBJECTIVE, "cbc", 10.0, 0.0, tiny_disk_bytes=TINY)
    assert result is not None
    moved_vm = 201 if result.assignment["201:scsi0"] == "b" else 202
    assert result.assignment[f"{moved_vm}:scsi0"] == "b"
    assert result.assignment["201:efidisk0"] == result.assignment["201:scsi0"]


def test_explain_never_offers_a_lone_small_disk_as_the_closest_alternative() -> None:
    from proxmox_storage_drs.heuristic import (
        best_single_disk_alternative,
        evaluate_assignment,
        group_average_fill,
        group_average_utilization,
        seed_assignment,
    )

    group = dataclasses.replace(efi_repair_group(), disks=efi_repair_group().disks[:2])
    loads = {k: v for k, v in LOADS.items() if k != "101:scsi0"}
    u, b = group_average_utilization(group, loads), group_average_fill(group)
    baseline = evaluate_assignment(group, seed_assignment(group), loads, OBJECTIVE, u, b)
    assert best_single_disk_alternative(group, loads, OBJECTIVE, u, b, baseline, TINY) is None
    assert best_single_disk_alternative(group, loads, OBJECTIVE, u, b, baseline, 0) is not None
