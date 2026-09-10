# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""build_topology() and its helpers. See proxmox_storage_drs/topology.py.

No test here talks to a real PVE API (.agents/testing.md) -- FakeProxmoxResource
(tests/unit/fakes.py) stands in for proxmoxer.ProxmoxAPI, and PveClient wraps
it exactly as it would wrap the real thing.
"""

from __future__ import annotations

import dataclasses
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
import yaml

from proxmox_storage_drs import config as config_module
from proxmox_storage_drs.exceptions import TopologyError
from proxmox_storage_drs.pve import PveClient
from proxmox_storage_drs.topology import (
    Disk,
    Topology,
    _default_format,
    _parse_pve_config_size_bytes,
    _pin_reason,
    _split_tags,
    build_topology,
    parse_disk_spec,
)
from tests.unit.fakes import fake_api

# --------------------------------------------------------------------- config


def make_config(tmp_path: Path, **overrides: Any) -> config_module.Config:
    data: dict[str, Any] = {
        "schema_version": 1,
        "proxmox": {"host": "pve.example.com", "auth": {"username": "drs@pve"}},
        "prometheus": {"url": "http://localhost:9090"},
        "groups": [
            {
                "name": "g1",
                "storages": [{"id": "san-a"}, {"id": "san-b"}],
            }
        ],
    }
    data.update(overrides)
    path = tmp_path / "drs.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return config_module.load_config(str(path), env={}).config


# --------------------------------------------------------------------- fixture cluster


def _vm(
    vmid: int, node: str, status: str = "running", tags: str = "", name: str | None = None
) -> dict[str, Any]:
    return {
        "vmid": vmid,
        "node": node,
        "status": status,
        "type": "qemu",
        "tags": tags,
        "name": name or f"vm{vmid}",
    }


def _content(storage: str, vmid: int, disk: str, size: int, fmt: str = "raw") -> dict[str, Any]:
    return {
        "volid": f"{storage}:vm-{vmid}-{disk}",
        "vmid": vmid,
        "size": size,
        "format": fmt,
        "content": "images",
    }


STORAGE_DEFS = [
    {"storage": "san-a", "type": "rbd", "shared": 1, "content": "images,rootdir"},
    {
        "storage": "san-b",
        "type": "rbd",
        "shared": 1,
        "content": "images,rootdir",
        "saferemove": 1,
        "saferemove_throughput": 10485760,
    },
]

STORAGE_RESOURCES = [
    {"storage": "san-a", "node": "node1", "status": "available"},
    {"storage": "san-b", "node": "node1", "status": "available"},
]

STORAGE_STATUS = {
    "san-a": {"total": 10 * (1 << 40), "used": 3 * (1 << 40)},
    "san-b": {"total": 5 * (1 << 40), "used": 1 * (1 << 40)},
}


def build_fake_client(
    vm_resources: list[dict[str, Any]],
    vm_configs: dict[int, dict[str, Any]],
    vm_snapshots: dict[int, list[dict[str, Any]]],
    content_by_storage: dict[str, list[dict[str, Any]]],
) -> PveClient:
    responses: dict[str, Any] = {
        "cluster/resources": lambda type: (vm_resources if type == "vm" else STORAGE_RESOURCES),
        "storage": STORAGE_DEFS,
    }
    for storage, status in STORAGE_STATUS.items():
        responses[f"nodes/node1/storage/{storage}/status"] = status
    for storage, items in content_by_storage.items():
        responses[f"nodes/node1/storage/{storage}/content"] = items
    for vmid, cfg in vm_configs.items():
        responses[f"nodes/node1/qemu/{vmid}/config"] = cfg
    for vmid, snaps in vm_snapshots.items():
        responses[f"nodes/node1/qemu/{vmid}/snapshot"] = snaps
    return PveClient(fake_api(responses))


# --------------------------------------------------------------------- the big scenario


def test_build_topology_full_scenario(tmp_path: Path) -> None:
    config = make_config(
        tmp_path,
        exclude={
            "tags": ["no-drs"],
            "vmids": [103],
            "disks": ["104:scsi1"],
            "include_unused_disks": False,
        },
    )

    vm_resources = [
        _vm(101, "node1"),  # plain movable
        _vm(102, "node1", tags="no-drs"),  # excluded by tag
        _vm(103, "node1"),  # excluded by vmid
        _vm(104, "node1"),  # one movable disk, one exclude.disks-pinned disk
        _vm(105, "node1"),  # snapshot-pinned
        _vm(106, "node1"),  # lock-pinned
        _vm(107, "node1"),  # unused0, include_unused_disks=False
        _vm(108, "node1"),  # disk on an ungrouped storage
        _vm(109, "node1", status="stopped"),  # excluded: running_only default True
        _vm(112, "node1"),  # has an orphaned companion volume
    ]
    vm_configs = {
        101: {"name": "vm101", "scsi0": "san-a:vm-101-disk-0,size=10G"},
        102: {"name": "vm102", "scsi0": "san-a:vm-102-disk-0,size=10G"},
        103: {"name": "vm103", "scsi0": "san-b:vm-103-disk-0,size=10G"},
        104: {
            "name": "vm104",
            "scsi0": "san-a:vm-104-disk-0,size=10G",
            "scsi1": "san-a:vm-104-disk-1,size=5G",
        },
        105: {"name": "vm105", "scsi0": "san-a:vm-105-disk-0,size=10G"},
        106: {"name": "vm106", "scsi0": "san-a:vm-106-disk-0,size=10G", "lock": "backup"},
        107: {"name": "vm107", "unused0": "san-a:vm-107-disk-0,size=1G"},
        108: {"name": "vm108", "scsi0": "local-only:vm-108-disk-0,size=10G"},
        112: {"name": "vm112", "scsi0": "san-a:vm-112-disk-0,size=10G"},
    }
    vm_snapshots = {
        101: [{"name": "current"}],
        102: [{"name": "current"}],
        103: [{"name": "current"}],
        104: [{"name": "current"}],
        105: [{"name": "current"}, {"name": "before-upgrade"}],
        106: [{"name": "current"}],
        107: [{"name": "current"}],
        108: [{"name": "current"}],
        112: [{"name": "current"}],
    }
    content_san_a = [
        _content("san-a", 101, "disk-0", 10 * (1 << 30)),
        _content("san-a", 102, "disk-0", 10 * (1 << 30)),
        _content("san-a", 104, "disk-0", 10 * (1 << 30)),
        _content("san-a", 104, "disk-1", 5 * (1 << 30)),
        _content("san-a", 105, "disk-0", 10 * (1 << 30)),
        _content("san-a", 106, "disk-0", 10 * (1 << 30)),
        _content("san-a", 107, "disk-0", 1 * (1 << 30)),
        _content("san-a", 109, "disk-0", 2 * (1 << 30)),  # stopped VM's disk: foreign
        _content("san-a", 112, "disk-0", 10 * (1 << 30)),
        _content("san-a", 112, "disk-1", 20 * (1 << 30)),  # orphan: not in vm112's config
        {  # a template/orphan with no owning VM at all
            "volid": "san-a:base-9999-disk-0",
            "vmid": None,
            "size": 3 * (1 << 30),
            "format": "raw",
            "content": "images",
        },
    ]
    content_san_b = [
        _content("san-b", 103, "disk-0", 10 * (1 << 30)),
    ]

    client = build_fake_client(
        vm_resources,
        vm_configs,
        vm_snapshots,
        {"san-a": content_san_a, "san-b": content_san_b},
    )

    topology = build_topology(client, config)

    assert len(topology.groups) == 1
    group = topology.groups[0]
    disks_by_key = {d.key: d for d in group.disks}

    # Plain movable disk.
    assert disks_by_key["101:scsi0"].pinned_reason is None
    assert disks_by_key["101:scsi0"].size_bytes == 10 * (1 << 30)

    # Tag-excluded VM: pinned, not dropped.
    assert disks_by_key["102:scsi0"].pinned_reason == "excluded by config"

    # vmid-excluded VM.
    assert disks_by_key["103:scsi0"].pinned_reason == "excluded by config"

    # exclude.disks pins only the named disk, not its sibling.
    assert disks_by_key["104:scsi0"].pinned_reason is None
    assert disks_by_key["104:scsi1"].pinned_reason == "excluded by config (exclude.disks)"

    # Snapshot-pinned (1 real snapshot, "current" excluded from the count).
    assert disks_by_key["105:scsi0"].pinned_reason == "snapshots present (1)"

    # Lock-pinned.
    assert disks_by_key["106:scsi0"].pinned_reason == "locked: backup"

    # Unused disk pinned because include_unused_disks is False.
    assert disks_by_key["107:unused0"].pinned_reason == (
        "excluded: unused disk (exclude.include_unused_disks=false)"
    )

    # Orphan companion volume pins the VM's own (otherwise ordinary) disk.
    assert disks_by_key["112:scsi0"].pinned_reason == (
        "unreferenced companion volume (snapshot chain or orphan)"
    )

    # Ungrouped disk (108) never appears in any group, and is warned about.
    assert "108:scsi0" not in disks_by_key
    assert any("108:scsi0" in w and "ungrouped" in w for w in topology.warnings)

    # Stopped VM (109, running_only defaults True) is never fetched or pinned.
    assert not any(k.startswith("109:") for k in disks_by_key)

    # Foreign accounting: san-a's untracked bytes are 109's disk (2 GiB),
    # 112's orphan disk-1 (20 GiB) and the ownerless template (3 GiB).
    storages_by_id = {s.id: s for s in group.storages}
    expected_foreign = (2 + 20 + 3) * (1 << 30)
    assert storages_by_id["san-a"].foreign_used_bytes == expected_foreign

    # saferemove mapping from GET /storage (the list form).
    assert storages_by_id["san-a"].saferemove is False
    assert storages_by_id["san-a"].saferemove_throughput_bytes_per_sec is None
    assert storages_by_id["san-b"].saferemove is True
    assert storages_by_id["san-b"].saferemove_throughput_bytes_per_sec == 10485760.0

    # Capacity/used from the authoritative status call.
    assert storages_by_id["san-a"].capacity_bytes == 10 * (1 << 40)
    assert storages_by_id["san-a"].used_bytes == 3 * (1 << 40)


# --------------------------------------------------------------------- cooldowns


def _one_disk_cluster(vmid: int = 201) -> tuple[PveClient, dict[int, dict[str, Any]]]:
    vm_resources = [_vm(vmid, "node1")]
    vm_configs = {vmid: {"name": f"vm{vmid}", "scsi0": f"san-a:vm-{vmid}-disk-0,size=10G"}}
    client = build_fake_client(
        vm_resources,
        vm_configs,
        {vmid: []},
        {"san-a": [_content("san-a", vmid, "disk-0", 10 * (1 << 30))], "san-b": []},
    )
    return client, vm_configs


def test_build_topology_pins_a_disk_within_its_cooldown(tmp_path: Path) -> None:
    from proxmox_storage_drs.state import Cooldowns, State, disk_state_key

    config = make_config(tmp_path)
    client, _ = _one_disk_cluster()
    now = datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc)
    state = State(
        cooldowns=Cooldowns(
            disk={disk_state_key("g1", 201, "scsi0"): "2026-09-06T11:00:00Z"}  # 1h ago
        )
    )

    topology = build_topology(client, config, state=state, now=now)

    disk = next(d for d in topology.groups[0].disks if d.key == "201:scsi0")
    assert disk.pinned_reason is not None
    assert disk.pinned_reason.startswith("cooldown:")
    assert "gates.cooldown_per_disk" in disk.pinned_reason


def test_build_topology_does_not_pin_once_the_cooldown_has_expired(tmp_path: Path) -> None:
    from proxmox_storage_drs.state import Cooldowns, State, disk_state_key

    config = make_config(tmp_path)  # default cooldown_per_disk: 24h
    client, _ = _one_disk_cluster()
    now = datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc)
    state = State(
        cooldowns=Cooldowns(
            disk={disk_state_key("g1", 201, "scsi0"): "2026-09-01T00:00:00Z"}  # long expired
        )
    )

    topology = build_topology(client, config, state=state, now=now)

    disk = next(d for d in topology.groups[0].disks if d.key == "201:scsi0")
    assert disk.pinned_reason is None


def test_build_topology_ignores_another_groups_cooldown_entry(tmp_path: Path) -> None:
    from proxmox_storage_drs.state import Cooldowns, State, disk_state_key

    config = make_config(tmp_path)
    client, _ = _one_disk_cluster()
    now = datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc)
    state = State(
        cooldowns=Cooldowns(
            disk={disk_state_key("some-other-group", 201, "scsi0"): "2026-09-06T11:00:00Z"}
        )
    )

    topology = build_topology(client, config, state=state, now=now)

    disk = next(d for d in topology.groups[0].disks if d.key == "201:scsi0")
    assert disk.pinned_reason is None


def test_build_topology_with_no_state_behaves_exactly_as_before(tmp_path: Path) -> None:
    """The default (`state=None`) must be indistinguishable from an empty
    state -- every existing caller/test that never passes `state` at all
    keeps behaving exactly as it did before cooldowns existed."""
    config = make_config(tmp_path)
    client, _ = _one_disk_cluster()
    topology = build_topology(client, config)
    disk = next(d for d in topology.groups[0].disks if d.key == "201:scsi0")
    assert disk.pinned_reason is None


def test_build_topology_multiple_buses_and_cdrom_skip(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    vm_resources = [_vm(200, "node1")]
    vm_configs = {
        200: {
            "name": "vm200",
            "ide0": "san-a:vm-200-disk-0,size=1G",
            "sata0": "san-a:vm-200-disk-1,size=1G",
            "virtio0": "san-a:vm-200-disk-2,size=1G",
            "efidisk0": "san-a:vm-200-disk-3,size=4M",
            "tpmstate0": "san-a:vm-200-disk-4,size=4M",
            "ide2": "none,media=cdrom",
        }
    }
    content = [
        _content("san-a", 200, "disk-0", 1 << 30),
        _content("san-a", 200, "disk-1", 1 << 30),
        _content("san-a", 200, "disk-2", 1 << 30),
        _content("san-a", 200, "disk-3", 4 << 20),
        _content("san-a", 200, "disk-4", 4 << 20),
    ]
    client = build_fake_client(
        vm_resources,
        vm_configs,
        {200: [{"name": "current"}]},
        {"san-a": content, "san-b": []},
    )
    topology = build_topology(client, config)
    keys = {d.key for d in topology.groups[0].disks}
    assert keys == {"200:ide0", "200:sata0", "200:virtio0", "200:efidisk0", "200:tpmstate0"}


def test_build_topology_content_missing_falls_back_to_config_size(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    vm_resources = [_vm(201, "node1")]
    vm_configs = {201: {"name": "vm201", "scsi0": "san-a:vm-201-disk-0,size=7G"}}
    client = build_fake_client(
        vm_resources, vm_configs, {201: [{"name": "current"}]}, {"san-a": [], "san-b": []}
    )
    topology = build_topology(client, config)
    disk = topology.groups[0].disks[0]
    assert disk.size_bytes == 7 * (1 << 30)
    assert any("VM config's own size=" in w for w in topology.warnings)


def test_build_topology_content_item_without_size_falls_back_to_config_size(
    tmp_path: Path,
) -> None:
    """A storage plugin can list a volid with no `size` key at all -- seen
    on a live cluster (KeyError crash before this was handled), distinct
    from the volid being absent from the listing entirely. Falls back the
    same way, and still trusts the content item's own `format`."""
    config = make_config(tmp_path)
    vm_resources = [_vm(201, "node1")]
    vm_configs = {201: {"name": "vm201", "scsi0": "san-a:vm-201-disk-0,size=7G"}}
    content = [
        {
            "volid": "san-a:vm-201-disk-0",
            "vmid": 201,
            "format": "qcow2",
            "content": "images",
            # deliberately no "size" key
        }
    ]
    client = build_fake_client(
        vm_resources, vm_configs, {201: [{"name": "current"}]}, {"san-a": content, "san-b": []}
    )
    topology = build_topology(client, config)
    disk = topology.groups[0].disks[0]
    assert disk.size_bytes == 7 * (1 << 30)
    assert disk.format == "qcow2"
    assert any("has no size=" in w and "content listing" in w for w in topology.warnings)


def test_build_topology_foreign_volume_without_size_is_skipped_not_crashed(
    tmp_path: Path,
) -> None:
    """The same content-listing gap, for a foreign (unreferenced) volume
    counted toward the snapshot reserve instead of a managed disk -- no VM
    config to fall back to here, so it is skipped (undercounting the
    reserve) with a warning, rather than crashing."""
    config = make_config(tmp_path)
    vm_resources = [_vm(201, "node1")]
    vm_configs = {201: {"name": "vm201", "scsi0": "san-a:vm-201-disk-0,size=7G"}}
    content = [
        _content("san-a", 201, "disk-0", 7 * (1 << 30)),
        {
            "volid": "san-a:base-9999-disk-0",
            "vmid": None,
            "format": "raw",
            "content": "images",
            # deliberately no "size" key
        },
    ]
    client = build_fake_client(
        vm_resources, vm_configs, {201: [{"name": "current"}]}, {"san-a": content, "san-b": []}
    )
    topology = build_topology(client, config)
    storages_by_id = {s.id: s for s in topology.groups[0].storages}
    assert storages_by_id["san-a"].foreign_used_bytes == 0
    assert any("base-9999-disk-0" in w and "has no size=" in w for w in topology.warnings)


def test_build_topology_stopped_vm_included_when_running_only_false(tmp_path: Path) -> None:
    config = make_config(tmp_path, exclude={"running_only": False})
    vm_resources = [_vm(202, "node1", status="stopped")]
    vm_configs = {202: {"name": "vm202", "scsi0": "san-a:vm-202-disk-0,size=2G"}}
    content = [_content("san-a", 202, "disk-0", 2 * (1 << 30))]
    client = build_fake_client(
        vm_resources, vm_configs, {202: [{"name": "current"}]}, {"san-a": content, "san-b": []}
    )
    topology = build_topology(client, config)
    disk = topology.groups[0].disks[0]
    assert disk.key == "202:scsi0"
    assert disk.pinned_reason is None  # movable, just carries zero load later


def test_build_topology_non_qemu_resources_are_skipped(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    vm_resources = [{"vmid": 300, "node": "node1", "status": "running", "type": "lxc"}]
    client = build_fake_client(vm_resources, {}, {}, {"san-a": [], "san-b": []})
    topology = build_topology(client, config)
    assert topology.groups[0].disks == ()


def test_build_topology_count_foreign_volumes_false(tmp_path: Path) -> None:
    config = make_config(tmp_path, snapshot_reserve={"count_foreign_volumes": False})
    vm_resources: list[dict[str, Any]] = []
    content = [
        {
            "volid": "san-a:base-1-disk-0",
            "vmid": None,
            "size": 5 * (1 << 30),
            "format": "raw",
            "content": "images",
        }
    ]
    client = build_fake_client(vm_resources, {}, {}, {"san-a": content, "san-b": []})
    topology = build_topology(client, config)
    storages_by_id = {s.id: s for s in topology.groups[0].storages}
    assert storages_by_id["san-a"].foreign_used_bytes == 0


def test_build_topology_reserve_factor_override(tmp_path: Path) -> None:
    config = make_config(
        tmp_path,
        groups=[
            {
                "name": "g1",
                "storages": [{"id": "san-a", "reserve_factor": 3.0}, {"id": "san-b"}],
            }
        ],
        snapshot_reserve={"factor": 2.0},
    )
    client = build_fake_client([], {}, {}, {"san-a": [], "san-b": []})
    topology = build_topology(client, config)
    storages_by_id = {s.id: s for s in topology.groups[0].storages}
    assert storages_by_id["san-a"].reserve_factor == 3.0
    assert storages_by_id["san-b"].reserve_factor == 2.0  # inherits the group default


# --------------------------------------------------------------------- validation errors


def test_build_topology_missing_storage_raises(tmp_path: Path) -> None:
    config = make_config(
        tmp_path, groups=[{"name": "g1", "storages": [{"id": "san-a"}, {"id": "ghost"}]}]
    )
    responses = {
        "cluster/resources": lambda type: [],
        "storage": [{"storage": "san-a", "type": "rbd", "shared": 1, "content": "images"}],
    }
    client = PveClient(fake_api(responses))
    with pytest.raises(TopologyError, match="ghost"):
        build_topology(client, config)


def test_build_topology_storage_without_images_content_raises(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    responses = {
        "cluster/resources": lambda type: [],
        "storage": [
            {"storage": "san-a", "type": "pbs", "shared": 1, "content": "backup"},
            {"storage": "san-b", "type": "rbd", "shared": 1, "content": "images"},
        ],
    }
    client = PveClient(fake_api(responses))
    with pytest.raises(TopologyError, match="images"):
        build_topology(client, config)


def test_build_topology_unshared_storage_warns_not_raises(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    responses = {
        "cluster/resources": lambda type: (STORAGE_RESOURCES if type == "storage" else []),
        "storage": [
            {"storage": "san-a", "type": "rbd", "shared": 0, "content": "images"},
            {"storage": "san-b", "type": "rbd", "shared": 1, "content": "images"},
        ],
        "nodes/node1/storage/san-a/status": STORAGE_STATUS["san-a"],
        "nodes/node1/storage/san-a/content": [],
        "nodes/node1/storage/san-b/status": STORAGE_STATUS["san-b"],
        "nodes/node1/storage/san-b/content": [],
    }
    client = PveClient(fake_api(responses))
    topology = build_topology(client, config)
    assert any("not marked shared" in w for w in topology.warnings)


def test_pick_active_node_prefers_available(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    resources = [
        {"storage": "san-a", "node": "node-broken", "status": "unknown"},
        {"storage": "san-a", "node": "node-good", "status": "available"},
        {"storage": "san-b", "node": "node1", "status": "available"},
    ]
    responses = {
        "cluster/resources": lambda type: resources if type == "storage" else [],
        "storage": STORAGE_DEFS,
        "nodes/node-good/storage/san-a/status": STORAGE_STATUS["san-a"],
        "nodes/node-good/storage/san-a/content": [],
        "nodes/node1/storage/san-b/status": STORAGE_STATUS["san-b"],
        "nodes/node1/storage/san-b/content": [],
    }
    client = PveClient(fake_api(responses))
    topology = build_topology(client, config)
    assert topology.groups[0].storages  # did not raise; picked node-good


def test_pick_active_node_raises_when_storage_absent_from_resources(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    responses = {"cluster/resources": lambda type: [], "storage": STORAGE_DEFS}
    client = PveClient(fake_api(responses))
    with pytest.raises(TopologyError, match="not reported active"):
        build_topology(client, config)


# --------------------------------------------------------------------- pure helpers


def test_parse_disk_spec() -> None:
    storage, name, params = parse_disk_spec("san-a:vm-101-disk-0,size=512G,iothread=1")
    assert storage == "san-a"
    assert name == "vm-101-disk-0"
    assert params == {"size": "512G", "iothread": "1"}


def test_parse_disk_spec_no_params() -> None:
    storage, name, params = parse_disk_spec("san-a:vm-101-disk-0")
    assert storage == "san-a"
    assert name == "vm-101-disk-0"
    assert params == {}


@pytest.mark.parametrize(
    "value,expected",
    [
        ("512G", 512 * (1 << 30)),
        ("4M", 4 * (1 << 20)),
        ("1T", 1 << 40),
        ("100K", 100 * (1 << 10)),
        ("1.5G", int(1.5 * (1 << 30))),
    ],
)
def test_parse_pve_config_size_bytes(value: str, expected: int) -> None:
    assert _parse_pve_config_size_bytes(value) == expected


def test_parse_pve_config_size_bytes_invalid() -> None:
    assert _parse_pve_config_size_bytes("not-a-size") is None
    assert _parse_pve_config_size_bytes("") is None


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("", set()),
        ("no-drs", {"no-drs"}),
        ("no-drs;prod", {"no-drs", "prod"}),
        ("no-drs,prod", {"no-drs", "prod"}),
        (" no-drs ; prod ", {"no-drs", "prod"}),
    ],
)
def test_split_tags(raw: str, expected: set[str]) -> None:
    assert _split_tags(raw) == expected


@pytest.mark.parametrize(
    "storage_type,expected",
    [
        ("lvm", "raw"),
        ("zfspool", "raw"),
        ("rbd", "raw"),
        ("dir", "qcow2"),
        ("nfs", "qcow2"),
        ("unknown-type", "raw"),
    ],
)
def test_default_format(storage_type: str, expected: str) -> None:
    assert _default_format(storage_type) == expected


def test_pin_reason_priority_order() -> None:
    # vm_excluded wins over everything else.
    assert (
        _pin_reason(
            vm_excluded=True,
            disk_excluded=True,
            snapshot_reason="snapshots present (1)",
            cooldown_remaining_seconds=3600.0,
            lock="backup",
            device="scsi0",
            include_unused_disks=True,
        )
        == "excluded by config"
    )


def test_pin_reason_movable() -> None:
    assert (
        _pin_reason(
            vm_excluded=False,
            disk_excluded=False,
            snapshot_reason=None,
            cooldown_remaining_seconds=0.0,
            lock=None,
            device="scsi0",
            include_unused_disks=True,
        )
        is None
    )


def test_pin_reason_unused_disk_allowed_by_default() -> None:
    assert (
        _pin_reason(
            vm_excluded=False,
            disk_excluded=False,
            snapshot_reason=None,
            cooldown_remaining_seconds=0.0,
            lock=None,
            device="unused0",
            include_unused_disks=True,
        )
        is None
    )


def test_pin_reason_cooldown_is_reported_with_time_remaining() -> None:
    assert (
        _pin_reason(
            vm_excluded=False,
            disk_excluded=False,
            snapshot_reason=None,
            cooldown_remaining_seconds=3600.0,
            lock=None,
            device="scsi0",
            include_unused_disks=True,
        )
        == "cooldown: moved recently, 1.0h left on gates.cooldown_per_disk"
    )


def test_pin_reason_cooldown_wins_over_lock_per_the_plans_own_order() -> None:
    """Section 5.3 (C2) lists cooldown before the lock check -- both being
    true at once must report the cooldown, not the (transient) lock."""
    assert (
        _pin_reason(
            vm_excluded=False,
            disk_excluded=False,
            snapshot_reason=None,
            cooldown_remaining_seconds=1.0,
            lock="backup",
            device="scsi0",
            include_unused_disks=True,
        )
        != "locked: backup"
    )


def test_pin_reason_snapshot_wins_over_cooldown() -> None:
    assert (
        _pin_reason(
            vm_excluded=False,
            disk_excluded=False,
            snapshot_reason="snapshots present (1)",
            cooldown_remaining_seconds=3600.0,
            lock=None,
            device="scsi0",
            include_unused_disks=True,
        )
        == "snapshots present (1)"
    )


# --------------------------------------------------------------------- dataclass sanity


def test_disk_and_topology_are_frozen() -> None:
    disk = Disk(
        key="1:scsi0",
        vmid=1,
        device="scsi0",
        vm_name="x",
        node="n",
        size_bytes=1,
        current_storage="s",
        format="raw",
        pinned_reason=None,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        disk.size_bytes = 2  # type: ignore[misc]


def test_topology_is_a_plain_container() -> None:
    topology = Topology(groups=(), warnings=("w",))
    assert topology.groups == ()
    assert topology.warnings == ("w",)
    assert topology.pattern_expansions == ()
    assert topology.unmanaged_storage_ids == ()


# ------------------------------------------------------- section 11.4 patterns


def _cluster_client(
    storage_defs: list[dict[str, Any]], inactive: frozenset[str] = frozenset()
) -> PveClient:
    """A fake client wired for exactly the storages in `storage_defs`, one
    node ("node1") reporting each available, empty content everywhere --
    the section 11.4 pattern-expansion tests below only care about
    `GET /storage` and the join, never about actual disk content.

    `inactive` names storages with a definition but no entry in
    `GET /cluster/resources?type=storage` at all -- the shape of a
    disabled storage (REVIEW.md U-01), still validated for content/status
    below since `_pick_active_node`/`_build_storages` are never reached for
    a storage this module's own expansion checks reject first.
    """
    resources = [
        {"storage": d["storage"], "node": "node1", "status": "available"}
        for d in storage_defs
        if d["storage"] not in inactive
    ]
    responses: dict[str, Any] = {
        "cluster/resources": lambda type: ([] if type == "vm" else resources),
        "storage": storage_defs,
    }
    for d in storage_defs:
        sid = d["storage"]
        responses[f"nodes/node1/storage/{sid}/status"] = {
            "total": 10 * (1 << 40),
            "used": 1 * (1 << 40),
        }
        responses[f"nodes/node1/storage/{sid}/content"] = []
    return PveClient(fake_api(responses))


def _rbd_def(storage: str, content: str = "images,rootdir") -> dict[str, Any]:
    return {"storage": storage, "type": "rbd", "shared": 1, "content": content}


def test_pattern_expands_to_every_matching_storage(tmp_path: Path) -> None:
    config = make_config(tmp_path, groups=[{"name": "g1", "storages": [{"id": "/san-.*/"}]}])
    client = _cluster_client([_rbd_def("san-a"), _rbd_def("san-b"), _rbd_def("san-c")])
    topology = build_topology(client, config)
    assert {s.id for s in topology.groups[0].storages} == {"san-a", "san-b", "san-c"}
    assert len(topology.pattern_expansions) == 1
    expansion = topology.pattern_expansions[0]
    assert expansion.group_name == "g1"
    assert expansion.pattern == "/san-.*/"
    assert expansion.matched_ids == ("san-a", "san-b", "san-c")


def test_pattern_matching_is_fullmatch_not_substring(tmp_path: Path) -> None:
    # section 11.4: "/prod/" names exactly the storage `prod`; under
    # substring semantics it would also capture `preprod`.
    config = make_config(
        tmp_path, groups=[{"name": "g1", "storages": [{"id": "/prod/"}, {"id": "preprod"}]}]
    )
    client = _cluster_client([_rbd_def("prod"), _rbd_def("preprod")])
    topology = build_topology(client, config)
    storages_by_id = {s.id: s for s in topology.groups[0].storages}
    assert set(storages_by_id) == {"prod", "preprod"}
    assert topology.pattern_expansions[0].matched_ids == ("prod",)


def test_literal_entry_overrides_a_matching_pattern(tmp_path: Path) -> None:
    config = make_config(
        tmp_path,
        groups=[
            {
                "name": "g1",
                "storages": [
                    {"id": "/san-.*/", "capability_weight": 1.0},
                    {"id": "san-b", "capability_weight": 0.5},
                ],
            }
        ],
    )
    client = _cluster_client([_rbd_def("san-a"), _rbd_def("san-b")])
    topology = build_topology(client, config)
    storages_by_id = {s.id: s for s in topology.groups[0].storages}
    assert storages_by_id["san-a"].capability_weight == 1.0  # from the pattern
    assert storages_by_id["san-b"].capability_weight == 0.5  # literal wins over the pattern


def test_two_patterns_matching_the_same_storage_is_a_hard_error(tmp_path: Path) -> None:
    config = make_config(
        tmp_path,
        groups=[{"name": "g1", "storages": [{"id": "/san-.*/"}, {"id": "/.*-a/"}]}],
    )
    client = _cluster_client([_rbd_def("san-a"), _rbd_def("san-b")])
    with pytest.raises(TopologyError, match="matched by two patterns"):
        build_topology(client, config)


def test_pattern_matching_nothing_raises(tmp_path: Path) -> None:
    config = make_config(
        tmp_path, groups=[{"name": "g1", "storages": [{"id": "/nope-.*/"}, {"id": "san-b"}]}]
    )
    client = _cluster_client([_rbd_def("san-a"), _rbd_def("san-b")])
    with pytest.raises(TopologyError, match="matches no storage"):
        build_topology(client, config)


def test_pattern_matching_a_disabled_storage_raises_naming_the_pattern(tmp_path: Path) -> None:
    # REVIEW.md U-01: a storage with a `GET /storage` definition but no
    # entry in the resource inventory (disabled) must not silently join a
    # group, and the error must name the pattern that pulled it in, not
    # `_pick_active_node`'s generic "not reported active" three steps
    # later.
    config = make_config(tmp_path, groups=[{"name": "g1", "storages": [{"id": "/san-.*/"}]}])
    client = _cluster_client(
        [_rbd_def("san-a"), _rbd_def("san-b"), _rbd_def("san-z")], inactive=frozenset({"san-z"})
    )
    with pytest.raises(TopologyError, match=r"pattern '/san-\.\*/' matched storage 'san-z'"):
        build_topology(client, config)


def test_pattern_matching_an_unshared_storage_still_warns(tmp_path: Path) -> None:
    # REVIEW.md U-03: the not-shared warning is a balance-quality signal,
    # not a typo-safety one, so unlike the `images` content check it
    # applies uniformly whether a literal or a pattern named the storage.
    config = make_config(tmp_path, groups=[{"name": "g1", "storages": [{"id": "/san-.*/"}]}])
    client = _cluster_client(
        [{"storage": "san-a", "type": "rbd", "shared": 0, "content": "images"}, _rbd_def("san-b")]
    )
    topology = build_topology(client, config)
    assert any("san-a" in w and "not marked shared" in w for w in topology.warnings)


def test_group_with_fewer_than_two_storages_after_expansion_raises(tmp_path: Path) -> None:
    config = make_config(tmp_path, groups=[{"name": "g1", "storages": [{"id": "/only-.*/"}]}])
    client = _cluster_client([_rbd_def("only-a"), _rbd_def("san-b")])
    with pytest.raises(TopologyError, match="at least 2"):
        build_topology(client, config)


def test_cross_group_pattern_and_literal_collision_raises(tmp_path: Path) -> None:
    config = make_config(
        tmp_path,
        groups=[
            {"name": "g1", "storages": [{"id": "/san-.*/"}]},
            {"name": "g2", "storages": [{"id": "san-a"}, {"id": "san-c"}]},
        ],
    )
    client = _cluster_client([_rbd_def("san-a"), _rbd_def("san-b"), _rbd_def("san-c")])
    with pytest.raises(TopologyError, match="san-a.*matched by both group"):
        build_topology(client, config)


def test_unmanaged_storage_ids_lists_storages_matched_by_no_group(tmp_path: Path) -> None:
    config = make_config(tmp_path)  # g1: literal san-a, san-b
    client = _cluster_client([_rbd_def("san-a"), _rbd_def("san-b"), _rbd_def("san-c")])
    topology = build_topology(client, config)
    assert topology.unmanaged_storage_ids == ("san-c",)


def test_pattern_matched_storage_skips_the_images_content_check(tmp_path: Path) -> None:
    # section 11.4's closing note: unlike a literal entry, a pattern match
    # is not required to carry "images" -- a balance-quality concern the
    # operator is warned about in the plan, not a hard error here.
    config = make_config(tmp_path, groups=[{"name": "g1", "storages": [{"id": "/san-.*/"}]}])
    client = _cluster_client(
        [_rbd_def("san-a"), _rbd_def("san-b"), _rbd_def("san-iso", content="iso")]
    )
    topology = build_topology(client, config)
    assert {s.id for s in topology.groups[0].storages} == {"san-a", "san-b", "san-iso"}


def test_pattern_expansion_is_logged_at_info(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    config = make_config(tmp_path, groups=[{"name": "g1", "storages": [{"id": "/san-.*/"}]}])
    client = _cluster_client([_rbd_def("san-a"), _rbd_def("san-b")])
    with caplog.at_level(logging.INFO):
        build_topology(client, config)
    assert any(
        r.levelno == logging.INFO and "san-a" in r.message and "san-b" in r.message
        for r in caplog.records
    )
