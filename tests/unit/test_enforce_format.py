# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Per-storage ``enforce_format``. See IMPLEMENTATION_PLAN.md section 5.3.2.

Everything is exercised without a cluster: the PVE API is the fake from
``fakes.py``. The two live-only questions of section 12 phase 16 -- that
``efidisk0`` converts in both directions on a real PVE, and that the target's
listed size matches ``z_{d,s}`` -- are deliberately not asserted anywhere here.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import yaml

from proxmox_storage_drs import cli
from proxmox_storage_drs import config as config_module
from proxmox_storage_drs.config import ObjectiveConfig
from proxmox_storage_drs.exceptions import ConfigError, TopologyError
from proxmox_storage_drs.heuristic import run_heuristic
from proxmox_storage_drs.optimize import cbc_available, solve
from proxmox_storage_drs.reserve import compute_reserve_status
from proxmox_storage_drs.schedule import ScheduledMove, order_moves, transient_invariant_ok
from proxmox_storage_drs.topology import (
    Disk,
    Group,
    Storage,
    Topology,
    build_topology,
    disk_size_on,
    nonconforming_disks,
    qcow2_lvm_allocation_bytes,
    storage_accepts_format,
    target_format,
)
from tests.unit.test_execute import (
    TIB,
    client_with,
    make_move,
)
from tests.unit.test_execute import make_storage as make_exec_storage
from tests.unit.test_execute import run
from tests.unit.test_topology import _cluster_client, make_config

GIB = 1 << 30
OBJECTIVE = ObjectiveConfig(
    alpha_spread=1.0,
    beta_move_count=0.25,
    gamma_move_bytes_per_tib=0.05,
    kappa_vm_affinity=0.50,
    delta_capacity_spread=0.0,
)
needs_cbc = pytest.mark.skipif(not cbc_available(), reason="pulp not installed")


def disk(
    key: str = "101:scsi0",
    size_bytes: int = 100 * GIB,
    storage: str = "src",
    fmt: str = "qcow2",
    config_size_bytes: int = 0,
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
        format=fmt,
        pinned_reason=None,
        config_size_bytes=config_size_bytes,
    )


def storage(
    id_: str,
    *,
    capacity_bytes: int = 2 * TIB,
    storage_type: str = "dir",
    formats: frozenset[str] = frozenset({"raw", "qcow2"}),
    enforce: str | None = None,
    reserve_factor: float = 0.0,
    foreign_bytes: int = 0,
) -> Storage:
    return Storage(
        id=id_,
        capability_weight=1.0,
        reserve_factor=reserve_factor,
        capacity_bytes=capacity_bytes,
        used_bytes=0,
        foreign_used_bytes=foreign_bytes,
        saferemove=False,
        saferemove_throughput_bytes_per_sec=None,
        free_space_soft_bytes=0,
        free_space_hard_bytes=0,
        storage_type=storage_type,
        allowed_formats=formats,
        enforce_format=enforce,
    )


# ------------------------------------------------------------ phi(d, s)


def test_no_enforcement_keeps_the_disks_format_and_size() -> None:
    d = disk(config_size_bytes=200 * GIB)
    s = storage("dst")
    assert target_format(d, s) == "qcow2"
    assert disk_size_on(d, s) == d.size_bytes


def test_enforcement_on_another_storage_changes_the_target_format() -> None:
    assert target_format(disk(fmt="qcow2"), storage("dst", enforce="raw")) == "raw"
    assert target_format(disk(fmt="raw"), storage("dst", enforce="qcow2")) == "qcow2"


def test_a_disk_already_on_the_storage_keeps_its_format() -> None:
    """Enforcement never creates a move: the disk's own storage is not 'a move onto it'."""
    d = disk(storage="src", fmt="raw")
    assert target_format(d, storage("src", enforce="qcow2")) == "raw"
    assert disk_size_on(d, storage("src", enforce="qcow2")) == d.size_bytes


def test_tpmstate0_is_exempt() -> None:
    tpm = disk(key="101:tpmstate0", fmt="raw")
    assert target_format(tpm, storage("dst", enforce="qcow2")) == "raw"


def test_efidisk0_is_not_exempt() -> None:
    efi = disk(key="101:efidisk0", fmt="raw")
    assert target_format(efi, storage("dst", enforce="qcow2")) == "qcow2"


def test_enforcement_widens_eligibility_never_narrows_it() -> None:
    """A qcow2 disk cannot go to a raw-only storage -- unless that storage enforces raw."""
    raw_only = frozenset({"raw"})
    d = disk(fmt="qcow2")
    plain = storage("thin", storage_type="lvmthin", formats=raw_only)
    enforcing = storage("thin", storage_type="lvmthin", formats=raw_only, enforce="raw")
    assert not storage_accepts_format(plain, target_format(d, plain))
    assert storage_accepts_format(enforcing, target_format(d, enforcing))


# ----------------------------------------------------------- z_{d,s}


def test_converting_move_is_charged_at_the_larger_of_listed_and_config_size() -> None:
    d = disk(fmt="qcow2", size_bytes=10 * GIB, config_size_bytes=100 * GIB)
    assert disk_size_on(d, storage("dst", enforce="raw")) == 100 * GIB


def test_converting_move_keeps_a_larger_listed_size() -> None:
    d = disk(fmt="qcow2", size_bytes=120 * GIB, config_size_bytes=100 * GIB)
    assert disk_size_on(d, storage("dst", enforce="raw")) == 120 * GIB


def test_converting_move_without_a_config_size_uses_the_listed_size() -> None:
    d = disk(fmt="qcow2", size_bytes=50 * GIB, config_size_bytes=0)
    assert disk_size_on(d, storage("dst", enforce="raw")) == 50 * GIB


def test_a_move_that_does_not_change_the_format_is_not_charged_extra() -> None:
    d = disk(fmt="raw", size_bytes=10 * GIB, config_size_bytes=100 * GIB)
    assert disk_size_on(d, storage("dst", enforce="raw")) == 10 * GIB


def test_qcow2_on_lvm_adds_the_images_own_metadata() -> None:
    d = disk(fmt="raw", size_bytes=100 * GIB, config_size_bytes=100 * GIB)
    lvm = storage("dst", storage_type="lvm", enforce="qcow2")
    assert disk_size_on(d, lvm) == qcow2_lvm_allocation_bytes(100 * GIB)
    assert disk_size_on(d, lvm) > 100 * GIB


def test_qcow2_metadata_is_not_charged_on_a_file_storage() -> None:
    d = disk(fmt="raw", size_bytes=100 * GIB, config_size_bytes=100 * GIB)
    assert disk_size_on(d, storage("dst", storage_type="dir", enforce="qcow2")) == 100 * GIB


@pytest.mark.parametrize("size", [1 << 20, 100 * GIB, 8 * TIB])
def test_lvm_qcow2_bound_is_never_below_qemus_default_layout(size: int) -> None:
    """With 64 KiB clusters qcow2 needs an 8-byte L2 and a 2-byte refcount entry per cluster
    (plus the tables that index them); the bound must stay above that for every size."""
    clusters = -(-size // (64 << 10))
    l2 = 8 * clusters
    refcount = 2 * (clusters + -(-l2 // (64 << 10)) + 1)
    assert qcow2_lvm_allocation_bytes(size) >= size + l2 + refcount


def test_reserve_counts_a_disk_at_z_ds_on_the_storage_it_is_assigned_to() -> None:
    d = disk(fmt="qcow2", size_bytes=10 * GIB, config_size_bytes=100 * GIB, storage="src")
    dst = storage("dst", enforce="raw", capacity_bytes=1 * TIB)
    status = compute_reserve_status(dst, [d], storage_of=lambda _d: "dst")
    assert status.managed_used_bytes == 100 * GIB
    assert status.largest_disk_bytes == 100 * GIB


def test_reserve_on_the_disks_own_storage_is_unchanged() -> None:
    d = disk(fmt="qcow2", size_bytes=10 * GIB, config_size_bytes=100 * GIB, storage="src")
    src = storage("src", enforce="raw")
    assert compute_reserve_status(src, [d]).managed_used_bytes == 10 * GIB


# --------------------------------------------------- non-conforming disks


def test_nonconforming_disks_are_counted_but_are_not_a_violation() -> None:
    s = storage("san", enforce="qcow2")
    disks = [
        disk("1:scsi0", 10 * GIB, "san", "raw"),
        disk("2:scsi0", 20 * GIB, "san", "qcow2"),
        disk("3:tpmstate0", 4 * GIB, "san", "raw"),  # exempt
        disk("4:scsi0", 40 * GIB, "elsewhere", "raw"),  # not on this storage
    ]
    assert nonconforming_disks(s, disks) == (1, 10 * GIB)
    assert nonconforming_disks(storage("san"), disks) == (0, 0)


# ---------------------------------------------------------- solvers


def _two_storage_group(src_disk: Disk, dst: Storage) -> Group:
    src = storage("src", capacity_bytes=1 * TIB)
    return Group(name="g", storages=(src, dst), disks=(src_disk,))


def _crowded_group(enforce: str | None) -> Group:
    """`src` holds a qcow2 disk and a small raw one and is heavily loaded; `thin` accepts raw
    only. Moving the qcow2 disk balances the group, which is possible only when `thin` enforces
    raw (it widens the eligible targets)."""
    src = storage("src", capacity_bytes=1 * TIB)
    thin = storage(
        "thin",
        capacity_bytes=1 * TIB,
        storage_type="lvmthin",
        formats=frozenset({"raw"}),
        enforce=enforce,
    )
    disks = (
        disk("101:scsi0", 100 * GIB, "src", "qcow2", config_size_bytes=100 * GIB),
        disk("102:scsi0", 100 * GIB, "src", "qcow2", config_size_bytes=100 * GIB),
    )
    return Group(name="g", storages=(src, thin), disks=disks)


LOADS = {"101:scsi0": 5.0, "102:scsi0": 5.0}


def _moved_to_thin(assignment: dict[str, str]) -> list[str]:
    return [key for key, sid in assignment.items() if sid == "thin"]


def test_heuristic_never_moves_a_qcow2_disk_onto_raw_only_storage_without_enforcement() -> None:
    result = run_heuristic(_crowded_group(None), LOADS, OBJECTIVE)
    assert _moved_to_thin(result.assignment) == []


def test_heuristic_moves_it_when_the_target_enforces_raw() -> None:
    result = run_heuristic(_crowded_group("raw"), LOADS, OBJECTIVE)
    assert len(_moved_to_thin(result.assignment)) == 1


@needs_cbc
def test_milp_never_moves_a_qcow2_disk_onto_raw_only_storage_without_enforcement() -> None:
    result = solve(_crowded_group(None), LOADS, OBJECTIVE, "cbc", 10.0, 0.0)
    assert result is not None
    assert _moved_to_thin(result.assignment) == []


@needs_cbc
def test_milp_moves_it_when_the_target_enforces_raw() -> None:
    result = solve(_crowded_group("raw"), LOADS, OBJECTIVE, "cbc", 10.0, 0.0)
    assert result is not None
    assert len(_moved_to_thin(result.assignment)) == 1


def _size_changes_which_disk_fits_group() -> Group:
    """Both disks are 40 GiB listed; `a` has a stale 90 GiB `size=`. `dst` is only 100 GiB big
    and enforces raw, so converting `a` (charged 90 GiB) leaves room for nothing else, while the
    plain-sized `b` (raw already, so charged 40 GiB) fits next to the 90 GiB one only when the
    converted size is NOT what is checked. The converted size must therefore be the one used."""
    src = storage("src", capacity_bytes=1 * TIB)
    dst = storage("dst", capacity_bytes=100 * GIB, enforce="raw")
    a = disk("1:scsi0", 40 * GIB, "src", "qcow2", config_size_bytes=90 * GIB)
    b = disk("2:scsi0", 40 * GIB, "src", "raw")
    return Group(name="g", storages=(src, dst), disks=(a, b))


@needs_cbc
def test_milp_capacity_uses_the_converted_size() -> None:
    group = _size_changes_which_disk_fits_group()
    result = solve(group, {"1:scsi0": 5.0, "2:scsi0": 5.0}, OBJECTIVE, "cbc", 10.0, 0.0)
    assert result is not None
    on_dst = [d for d in group.disks if result.assignment[d.key] == "dst"]
    assert sum(disk_size_on(d, group.storages[1]) for d in on_dst) <= 100 * GIB
    # Counting `a` at its listed 40 GiB would let both disks (80 GiB) in; at 90 GiB they cannot.
    assert len(on_dst) < 2


def test_heuristic_capacity_uses_the_converted_size() -> None:
    group = _size_changes_which_disk_fits_group()
    result = run_heuristic(group, {"1:scsi0": 5.0, "2:scsi0": 5.0}, OBJECTIVE)
    on_dst = [d for d in group.disks if result.assignment[d.key] == "dst"]
    assert sum(disk_size_on(d, group.storages[1]) for d in on_dst) <= 100 * GIB


# --------------------------------------------------------- scheduler


def test_transient_invariant_charges_the_converted_size() -> None:
    d = disk(fmt="qcow2", size_bytes=40 * GIB, config_size_bytes=90 * GIB)
    dst = storage("dst", capacity_bytes=80 * GIB, enforce="raw")
    group = _two_storage_group(d, dst)
    state = {d.key: "src"}
    # 40 GiB would fit in 80 GiB; the 90 GiB conversion charge does not.
    assert not transient_invariant_ok(group, state, d, dst)
    assert transient_invariant_ok(group, state, d, replace(dst, enforce_format=None))


def test_transient_invariant_counts_an_already_converted_disk_on_the_target() -> None:
    converted = disk("1:scsi0", 40 * GIB, "src", "qcow2", config_size_bytes=60 * GIB)
    mover = disk("2:scsi0", 10 * GIB, "src", "raw")
    dst = storage("dst", capacity_bytes=100 * GIB, enforce="raw")
    group = Group(name="g", storages=(storage("src"), dst), disks=(converted, mover))
    state = {"1:scsi0": "dst", "2:scsi0": "src"}  # `converted` already landed, charged 60 GiB
    assert transient_invariant_ok(group, state, mover, dst)  # 60 + 10 <= 100
    big = replace(mover, size_bytes=45 * GIB)
    assert not transient_invariant_ok(group, state, big, dst)  # 60 + 45 > 100


def test_scheduled_moves_record_the_format_change() -> None:
    group = _crowded_group("raw")
    plan = order_moves(group, {"101:scsi0": "thin", "102:scsi0": "src"}, LOADS, OBJECTIVE)
    (move,) = plan.order
    assert (move.format_from, move.format_to) == ("qcow2", "raw")


def test_a_move_without_enforcement_records_equal_formats() -> None:
    src = storage("src")
    dst = storage("dst")
    d = disk("1:scsi0", 10 * GIB, "src", "raw")
    group = Group(name="g", storages=(src, dst), disks=(d,))
    plan = order_moves(group, {"1:scsi0": "dst"}, {"1:scsi0": 1.0}, OBJECTIVE)
    (move,) = plan.order
    assert move.format_from == move.format_to == "raw"


# ---------------------------------------------------------- executor


def _exec_group(enforce: str | None, fmt: str, volume: str, size: str) -> tuple[Group, Any]:
    src = make_exec_storage("san-a")
    dst = replace(make_exec_storage("san-b"), enforce_format=enforce)
    d = replace(_exec_disk(), format=fmt, config_size_bytes=0)
    group = Group(name="fc-tier1", storages=(src, dst), disks=(d,))
    client, api = client_with(
        {"nodes/pve01/qemu/101/config": {"scsi0": f"san-a:{volume},size={size}"}}
    )
    return group, (client, api)


def _exec_disk() -> Disk:
    from tests.unit.test_execute import make_disk

    return make_disk("101:scsi0", 1.0, "san-a")


def _posted_move(api: Any) -> dict[str, Any]:
    return next(c[2] for c in api.calls if c[1] == "nodes/pve01/qemu/101/move_disk")


def test_format_is_sent_only_when_the_move_converts() -> None:
    group, (client, api) = _exec_group("raw", "qcow2", "101/vm-101-disk-0.qcow2", "1024G")
    result = run(client, group, (make_move(),))
    assert result.outcomes[0].status == "moved"
    assert _posted_move(api)["format"] == "raw"


def test_format_is_not_sent_without_enforcement() -> None:
    group, (client, api) = _exec_group(None, "qcow2", "101/vm-101-disk-0.qcow2", "1024G")
    run(client, group, (make_move(),))
    assert "format" not in _posted_move(api)


def test_format_is_not_sent_when_the_disk_already_has_the_enforced_format() -> None:
    group, (client, api) = _exec_group("raw", "raw", "vm-101-disk-0", "1024G")
    run(client, group, (make_move(),))
    assert "format" not in _posted_move(api)


def test_a_live_format_that_differs_from_the_plan_means_replan() -> None:
    # The plan believed qcow2 -> raw; the volume is raw by now (no .qcow2 suffix).
    group, (client, api) = _exec_group("raw", "qcow2", "vm-101-disk-0", "1024G")
    result = run(client, group, (make_move(),))
    assert result.outcomes[0].status == "replan_needed"
    assert "re-plan" in result.outcomes[0].detail
    assert not [c for c in api.calls if c[1] == "nodes/pve01/qemu/101/move_disk"]


def test_live_format_is_not_checked_for_a_move_that_does_not_convert() -> None:
    group, (client, api) = _exec_group(None, "qcow2", "vm-101-disk-0", "1024G")
    result = run(client, group, (make_move(),))
    assert result.outcomes[0].status == "moved"


def test_a_converting_move_is_refused_when_the_live_check_finds_no_room() -> None:
    """The live transient check charges the converted size from the live `size=`."""
    src = make_exec_storage("san-a")
    dst = replace(make_exec_storage("san-b", capacity_tib=0.5), enforce_format="raw")
    d = replace(_exec_disk(), format="qcow2", size_bytes=100 * GIB)
    group = Group(name="fc-tier1", storages=(src, dst), disks=(d,))
    client, api = client_with(
        {
            "nodes/pve01/qemu/101/config": {"scsi0": "san-a:101/vm-101-disk-0.qcow2,size=1024G"},
            "nodes/pve01/storage/san-b/status": {"total": TIB // 2, "used": 0},
        }
    )
    result = run(client, group, (make_move(),))
    assert result.outcomes[0].status != "moved"
    assert not [c for c in api.calls if c[1] == "nodes/pve01/qemu/101/move_disk"]


# ---------------------------------------------------- config & topology


def _write(tmp_path: Path, groups: list[dict[str, Any]]) -> Path:
    data = {
        "schema_version": 1,
        "proxmox": {"host": "pve.example.com", "auth": {"username": "drs@pve"}},
        "prometheus": {"url": "http://localhost:9090"},
        "groups": groups,
    }
    path = tmp_path / "drs.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_config_parses_enforce_format(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            {
                "name": "g",
                "storages": [{"id": "a", "enforce_format": "qcow2"}, {"id": "b"}],
            }
        ],
    )
    cfg = config_module.load_config(str(path), env={}).config
    assert [s.enforce_format for s in cfg.groups[0].storages] == ["qcow2", None]


@pytest.mark.parametrize("bad", ["vmdk", "QCOW2", "", 1])
def test_config_rejects_a_value_other_than_raw_qcow2_or_null(tmp_path: Path, bad: Any) -> None:
    path = _write(
        tmp_path,
        [{"name": "g", "storages": [{"id": "a", "enforce_format": bad}, {"id": "b"}]}],
    )
    with pytest.raises(ConfigError):
        config_module.load_config(str(path), env={})


def test_config_has_no_global_enforce_format(tmp_path: Path) -> None:
    data = yaml.safe_load(
        _write(tmp_path, [{"name": "g", "storages": [{"id": "a"}, {"id": "b"}]}]).read_text()
    )
    data["enforce_format"] = "raw"
    path = tmp_path / "global.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ConfigError):
        config_module.load_config(str(path), env={})


def _lvm_def(storage_id: str) -> dict[str, Any]:
    return {"storage": storage_id, "type": "lvm", "shared": 1, "content": "images"}


def test_pattern_value_applies_to_every_match_and_a_literal_entry_wins(tmp_path: Path) -> None:
    cfg = make_config(
        tmp_path,
        groups=[
            {
                "name": "g1",
                "storages": [
                    {"id": "/san-.*/", "enforce_format": "qcow2"},
                    {"id": "san-b"},  # literal replaces the pattern's options wholesale
                ],
            }
        ],
    )
    client = _cluster_client([_lvm_def("san-a"), _lvm_def("san-b"), _lvm_def("san-c")])
    by_id = {s.id: s for s in build_topology(client, cfg).groups[0].storages}
    assert by_id["san-a"].enforce_format == "qcow2"
    assert by_id["san-b"].enforce_format is None
    assert by_id["san-c"].enforce_format == "qcow2"
    assert by_id["san-a"].enforce_format_source == "pattern /san-.*/"
    assert by_id["san-b"].enforce_format_source == ""


def test_a_literal_entry_can_set_its_own_value(tmp_path: Path) -> None:
    cfg = make_config(
        tmp_path,
        groups=[
            {
                "name": "g1",
                "storages": [
                    {"id": "/san-.*/", "enforce_format": "qcow2"},
                    {"id": "san-b", "enforce_format": "raw"},
                ],
            }
        ],
    )
    client = _cluster_client([_lvm_def("san-a"), _lvm_def("san-b")])
    by_id = {s.id: s for s in build_topology(client, cfg).groups[0].storages}
    assert (by_id["san-a"].enforce_format, by_id["san-b"].enforce_format) == ("qcow2", "raw")
    assert by_id["san-b"].enforce_format_source == "storage entry"


def test_a_format_the_storage_type_cannot_hold_is_refused(tmp_path: Path) -> None:
    cfg = make_config(
        tmp_path,
        groups=[
            {
                "name": "g1",
                "storages": [{"id": "ceph-a", "enforce_format": "qcow2"}, {"id": "ceph-b"}],
            }
        ],
    )
    rbd = [
        {"storage": s, "type": "rbd", "shared": 1, "content": "images"}
        for s in ("ceph-a", "ceph-b")
    ]
    with pytest.raises(TopologyError, match="ceph-a.*enforce_format 'qcow2'"):
        build_topology(_cluster_client(rbd), cfg)


def test_a_pattern_matching_a_storage_that_cannot_hold_it_names_that_storage(
    tmp_path: Path,
) -> None:
    cfg = make_config(
        tmp_path,
        groups=[{"name": "g1", "storages": [{"id": "/s-.*/", "enforce_format": "qcow2"}]}],
    )
    defs = [
        _lvm_def("s-lvm"),
        {"storage": "s-rbd", "type": "rbd", "shared": 1, "content": "images"},
    ]
    with pytest.raises(TopologyError, match="s-rbd"):
        build_topology(_cluster_client(defs), cfg)


def test_raw_is_accepted_on_every_storage_type(tmp_path: Path) -> None:
    cfg = make_config(
        tmp_path,
        groups=[{"name": "g1", "storages": [{"id": "/s-.*/", "enforce_format": "raw"}]}],
    )
    defs = [
        _lvm_def("s-lvm"),
        {"storage": "s-rbd", "type": "rbd", "shared": 1, "content": "images"},
    ]
    topology = build_topology(_cluster_client(defs), cfg)
    assert {s.enforce_format for s in topology.groups[0].storages} == {"raw"}


# --------------------------------------------------------------- CLI


def _enforcing_topology() -> Topology:
    from tests.unit.test_cli import _sample_topology

    base = _sample_topology()
    group = base.groups[0]
    san_a = replace(
        group.storages[0], enforce_format="qcow2", enforce_format_source="pattern /san-.*/"
    )
    disks = (
        tuple(replace(d, format="raw", current_storage=san_a.id) for d in group.disks[:1])
        + group.disks[1:]
    )
    patched = Group(name=group.name, storages=(san_a, group.storages[1]), disks=disks)
    return Topology(groups=(patched,), warnings=())


def test_verify_storages_reports_enforce_format_and_nonconforming_disks(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.unit.test_cli import FAKE_CLIENT, _fake_build_topology, write_config

    monkeypatch.setattr("proxmox_storage_drs.cli.build_pve_client", lambda cfg: FAKE_CLIENT)
    monkeypatch.setattr(
        "proxmox_storage_drs.cli.build_topology", _fake_build_topology(_enforcing_topology())
    )
    group = _enforcing_topology().groups[0]
    expected_count, _bytes = nonconforming_disks(group.storages[0], group.disks)
    assert expected_count >= 1
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "verify-storages"]) == 0
    out = capsys.readouterr().out
    assert "enforce_format: qcow2" in out
    assert "pattern /san-.*/" in out
    assert f"non-conforming disks: {expected_count}" in out

    assert cli.main(["-c", str(path), "--json", "verify-storages"]) == 0
    payload = json.loads(capsys.readouterr().out)
    by_id = {s["id"]: s for s in payload["groups"][0]["storages"]}
    assert by_id["san-a"]["enforce_format"] == "qcow2"
    assert by_id["san-a"]["enforce_format_source"] == "pattern /san-.*/"
    assert by_id["san-a"]["nonconforming_disks"] == expected_count
    assert by_id["san-b"]["enforce_format"] is None
    assert by_id["san-b"]["nonconforming_disks"] == 0


def test_a_storage_without_enforcement_prints_no_enforce_format_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.unit.test_cli import (
        FAKE_CLIENT,
        _fake_build_topology,
        _sample_topology,
        write_config,
    )

    monkeypatch.setattr("proxmox_storage_drs.cli.build_pve_client", lambda cfg: FAKE_CLIENT)
    monkeypatch.setattr(
        "proxmox_storage_drs.cli.build_topology", _fake_build_topology(_sample_topology())
    )
    assert cli.main(["-c", str(write_config(tmp_path)), "verify-storages"]) == 0
    assert "enforce_format" not in capsys.readouterr().out


def _plan_line(move: ScheduledMove) -> str:
    return cli._render_plan_move_line(1, move, None, {}, "vm101")


def _move(format_from: str, format_to: str) -> ScheduledMove:
    return ScheduledMove(
        disk_key="101:scsi0",
        vmid=101,
        device="scsi0",
        from_storage="san-a",
        to_storage="san-b",
        size_bytes=GIB,
        imbalance_reduction=1.0,
        resolves_reserve_violation=False,
        format_from=format_from,
        format_to=format_to,
    )


def test_a_converting_move_shows_the_conversion_on_its_plan_line() -> None:
    assert "san-b (raw→qcow2)" in _plan_line(_move("raw", "qcow2"))


def test_a_move_that_keeps_its_format_shows_nothing_extra() -> None:
    line = _plan_line(_move("raw", "raw"))
    assert "san-b   " in line and "→raw" not in line


def test_a_hand_built_move_without_formats_shows_nothing_extra() -> None:
    assert "san-b   " in _plan_line(_move("", ""))


def test_a_second_converting_move_sees_the_first_ones_converted_size_as_z_b() -> None:
    """REVIEW.md AN-01: the (C4) largest-disk bookkeeping records ``z_{d,s}``, not the listed size,
    so a later move onto the same enforcing storage is checked against the right ``Z_b``."""
    from proxmox_storage_drs.config import ExecutionConfig
    from proxmox_storage_drs.execute import MoveOutcome, _post_move_bookkeeping

    d = disk(fmt="raw", size_bytes=100 * GIB, config_size_bytes=120 * GIB)
    lvm = storage("san-b", storage_type="lvm", enforce="qcow2")
    largest = {"san-b": 0}
    outcome = MoveOutcome(
        disk_key=d.key, from_storage="san-a", to_storage="san-b", status="moved", detail=""
    )
    move = _move("raw", "qcow2")
    stop = _post_move_bookkeeping(outcome, move, d, largest, set(), ExecutionConfig(), lvm)
    assert stop is None
    assert largest["san-b"] == disk_size_on(d, lvm) > 120 * GIB
