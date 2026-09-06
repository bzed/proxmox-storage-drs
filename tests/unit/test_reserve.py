# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""(C4)/(C5) reserve evaluation. See proxmox_storage_drs/reserve.py.

Cross-checked against the IMPLEMENTATION_PLAN.md section 14 worked example
(section 14.2's initial state), which is the project's proven-optimal
acceptance fixture -- reserve.py reproducing those exact numbers is a real
correctness check, not just a unit test in isolation.
"""

from __future__ import annotations

import dataclasses

import pytest

from proxmox_storage_drs.reserve import (
    compute_reserve_status,
    largest_disk_bytes,
    managed_used_bytes,
    transient_charge_ok,
)
from proxmox_storage_drs.topology import Disk, Storage

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


def make_storage(id_: str, capacity_tib: float, reserve_factor: float = 2.0) -> Storage:
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


# --------------------------------------------------------------- section 14.2


def test_section_14_2_san_a_violates_by_half_a_tib() -> None:
    """san-a: used 4.5 TiB, Z=2.0 TiB, f=2.0 -> required 8.5 > capacity 8.0."""
    disks = [
        make_disk("101:scsi0", 2.0, "san-a"),
        make_disk("101:scsi1", 1.0, "san-a"),
        make_disk("102:scsi0", 1.5, "san-a"),
    ]
    storage = make_storage("san-a", capacity_tib=8.0)
    status = compute_reserve_status(storage, disks, min_free_bytes=0)
    assert status.largest_disk_bytes == round(2.0 * TIB)
    assert status.required_reserve_bytes == round(4.0 * TIB)
    assert status.managed_used_bytes == round(4.5 * TIB)
    assert status.violated
    assert status.shortfall_bytes == round(0.5 * TIB)


def test_section_14_2_san_b_and_san_c_do_not_violate() -> None:
    san_b_disks = [make_disk("103:scsi0", 0.5, "san-b"), make_disk("104:scsi0", 1.0, "san-b")]
    san_b = make_storage("san-b", capacity_tib=8.0)
    status_b = compute_reserve_status(san_b, san_b_disks, min_free_bytes=0)
    assert status_b.managed_used_bytes == round(1.5 * TIB)
    assert status_b.required_reserve_bytes == round(2.0 * TIB)  # f=2.0 * Z=1.0
    assert not status_b.violated

    san_c_disks = [make_disk("105:scsi0", 0.5, "san-c")]
    san_c = make_storage("san-c", capacity_tib=8.0)
    status_c = compute_reserve_status(san_c, san_c_disks, min_free_bytes=0)
    assert not status_c.violated


def test_section_14_3_post_plan_reserve_is_clean_everywhere() -> None:
    """After the plan's three-move solution (section 14.3): san-a keeps only
    101:scsi0 (Z=2.0), san-b gains 101:scsi1 and 105:scsi0, san-c gains
    102:scsi0. Every storage must clear its reserve afterward."""
    disks = [
        make_disk("101:scsi0", 2.0, "san-a"),
        make_disk("103:scsi0", 0.5, "san-b"),
        make_disk("104:scsi0", 1.0, "san-b"),
        make_disk("101:scsi1", 1.0, "san-b"),
        make_disk("105:scsi0", 0.5, "san-b"),
        make_disk("102:scsi0", 1.5, "san-c"),
    ]
    for storage_id, expected_used_tib in (("san-a", 2.0), ("san-b", 3.0), ("san-c", 1.5)):
        storage = make_storage(storage_id, capacity_tib=8.0)
        status = compute_reserve_status(storage, disks, min_free_bytes=0)
        assert status.managed_used_bytes == round(expected_used_tib * TIB)
        assert not status.violated, f"{storage_id}: unexpected shortfall {status.shortfall_bytes}"


# --------------------------------------------------------------------- edges


def test_min_free_bytes_floor_dominates_a_small_largest_disk() -> None:
    """A 10 GiB largest disk on a 20 TiB LUN: the snapshot term alone (f=2.0)
    would reserve only 20 GiB; min_free_bytes is the floor that matters."""
    disks = [make_disk("1:scsi0", 10 / 1024, "big")]  # 10 GiB in TiB units
    storage = make_storage("big", capacity_tib=20.0)
    status = compute_reserve_status(storage, disks, min_free_bytes=100 * (1 << 30))
    assert status.required_reserve_bytes == 100 * (1 << 30)


def test_empty_storage_has_zero_largest_disk_and_reserve() -> None:
    storage = make_storage("empty", capacity_tib=1.0)
    status = compute_reserve_status(storage, [], min_free_bytes=0)
    assert status.largest_disk_bytes == 0
    assert status.required_reserve_bytes == 0
    assert status.managed_used_bytes == 0
    assert not status.violated


def test_foreign_used_bytes_counts_toward_the_reserve_check() -> None:
    storage = Storage(
        id="s",
        capability_weight=1.0,
        reserve_factor=2.0,
        saturation_load=None,
        capacity_bytes=10 * (1 << 30),
        used_bytes=0,
        foreign_used_bytes=8 * (1 << 30),
        saferemove=False,
        saferemove_throughput_bytes_per_sec=None,
    )
    disk = make_disk("1:scsi0", 1 / 1024, "s")  # negligible size, negligible reserve
    status = compute_reserve_status(storage, [disk], min_free_bytes=0)
    # 8 GiB foreign + ~1 GiB managed + a tiny reserve comfortably exceeds 10 GiB.
    assert status.violated


def test_largest_disk_and_managed_used_ignore_other_storages() -> None:
    disks = [make_disk("1:scsi0", 5.0, "other"), make_disk("2:scsi0", 1.0, "s")]
    assert largest_disk_bytes(disks, "s") == round(1.0 * TIB)
    assert managed_used_bytes(disks, "s") == round(1.0 * TIB)


def test_reserve_status_is_frozen() -> None:
    storage = make_storage("s", capacity_tib=1.0)
    status = compute_reserve_status(storage, [], min_free_bytes=0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        status.shortfall_bytes = 1  # type: ignore[misc]


# ------------------------------------------------------------- transient_charge_ok


def test_transient_charge_ok_single_move_matches_section_8_1() -> None:
    """The single-move form section 8.1 states directly:
    used_b + z_d + f_b * max(Z_b, z_d) <= C_b. 2 TiB used, Z_b=1 TiB
    existing, a 1 TiB incoming disk, f=2.0, C=8 TiB:
    2 + 1 + 2*max(1,1) = 5 <= 8 -> ok."""
    assert transient_charge_ok(
        reserve_factor=2.0,
        capacity_bytes=8 * TIB,
        used_bytes=2 * TIB,
        existing_largest_bytes=1 * TIB,
        charge_sizes_bytes=[1 * TIB],
        min_free_bytes=0,
    )


def test_transient_charge_ok_single_move_over_capacity_rejects() -> None:
    """Same shape, but the incoming disk is now the new largest (3 TiB):
    2 + 3 + 2*max(1,3) = 11 > 8 -> not ok."""
    assert not transient_charge_ok(
        reserve_factor=2.0,
        capacity_bytes=8 * TIB,
        used_bytes=2 * TIB,
        existing_largest_bytes=1 * TIB,
        charge_sizes_bytes=[3 * TIB],
        min_free_bytes=0,
    )


def test_transient_charge_ok_sums_every_concurrent_charge() -> None:
    """Section 8.1's generalized form: N 1 TiB moves landing on the same
    storage at once, on top of 2 TiB already used, f=2.0, C=8 TiB, no
    existing largest disk: total = 2 + N + 2*max(0,1) = 4+N. N=2 -> 6
    (ok); N=4 -> 8, exactly at capacity (still ok); N=5 -> 9 (breaches)."""
    assert transient_charge_ok(
        reserve_factor=2.0,
        capacity_bytes=8 * TIB,
        used_bytes=2 * TIB,
        existing_largest_bytes=0,
        charge_sizes_bytes=[1 * TIB, 1 * TIB],
        min_free_bytes=0,
    )
    assert transient_charge_ok(
        reserve_factor=2.0,
        capacity_bytes=8 * TIB,
        used_bytes=2 * TIB,
        existing_largest_bytes=0,
        charge_sizes_bytes=[1 * TIB] * 4,
        min_free_bytes=0,
    )
    assert not transient_charge_ok(
        reserve_factor=2.0,
        capacity_bytes=8 * TIB,
        used_bytes=2 * TIB,
        existing_largest_bytes=0,
        charge_sizes_bytes=[1 * TIB] * 5,
        min_free_bytes=0,
    )


def test_transient_charge_ok_reserve_term_uses_the_largest_single_charge_not_the_sum() -> None:
    """The f_b * max(...) term takes the *largest individual* incoming
    disk (3 TiB here), never the sum of the charges (which would be 5
    TiB): two 1 TiB disks and one 3 TiB disk land together, used=0, f=2.0.
    Correct (largest-based): total = 0 + sum(1,1,3) + 2*max(0,3) = 5+6=11.
    C=11 TiB makes this exactly borderline-ok; a sum-based reserve
    (2*max(0,5)=10) would instead compute 5+10=15, failing the same C=11
    -- so this assertion only passes if the implementation takes the
    largest-charge branch, not the sum."""
    assert transient_charge_ok(
        reserve_factor=2.0,
        capacity_bytes=11 * TIB,
        used_bytes=0,
        existing_largest_bytes=0,
        charge_sizes_bytes=[1 * TIB, 1 * TIB, 3 * TIB],
        min_free_bytes=0,
    )


def test_transient_charge_ok_existing_largest_still_dominates_when_bigger() -> None:
    """A storage already holding a 5 TiB disk, and two small 1 TiB moves
    land on it: the reserve term is f*max(5, 1) = f*5, not f*1."""
    assert not transient_charge_ok(
        reserve_factor=2.0,
        capacity_bytes=8 * TIB,
        used_bytes=0,
        existing_largest_bytes=5 * TIB,
        charge_sizes_bytes=[1 * TIB, 1 * TIB],
        min_free_bytes=0,
    )  # 0 + 2 + 2*5 = 12 > 8


def test_transient_charge_ok_min_free_bytes_floor_still_applies() -> None:
    assert not transient_charge_ok(
        reserve_factor=0.01,
        capacity_bytes=1 * TIB,
        used_bytes=round(0.9 * TIB),
        existing_largest_bytes=0,
        charge_sizes_bytes=[round(0.05 * TIB)],
        min_free_bytes=round(0.2 * TIB),
    )


def test_transient_charge_ok_with_no_charges_is_vacuously_true() -> None:
    """Nothing landing on this storage -- there is nothing to check."""
    assert transient_charge_ok(
        reserve_factor=2.0,
        capacity_bytes=0,
        used_bytes=10**9,
        existing_largest_bytes=10**9,
        charge_sizes_bytes=[],
        min_free_bytes=0,
    )
