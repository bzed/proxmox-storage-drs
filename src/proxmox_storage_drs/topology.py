# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Build the disk/storage/group model. See IMPLEMENTATION_PLAN.md section 3.5/3.6/3.7/5.1/5.3 (C2).

This module joins ``pve.py``'s API responses with the configured
``groups`` into the per-group `D`/`S` sets the rest of the engine (the load
model, the solver, the scheduler) consumes. It never touches the network
itself and never touches Prometheus -- it takes a already-constructed
:class:`~proxmox_storage_drs.pve.PveClient` and reads through it, once, per
section 3.5's "a per-run topology cache" (this whole module's output *is*
that cache; nothing here fetches twice).

Terminology, matching the plan exactly: ``D`` is *every* disk this module
places into a group, pinned or not (section 5.1's own definition: "movable
disks currently in the group" -- (C2) is what fixes some of their
placement variables, it does not remove them from ``D``). A disk this
module never sees at all (a stopped VM excluded by ``exclude.running_only``,
or a disk whose current storage is not in any configured group) is what
"foreign" (`Uˢᵉˣᵗ`, section 5.1.1) means -- not merely "excluded by name".
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from proxmox_storage_drs.config import Config, GroupConfig, StorageConfig
from proxmox_storage_drs.exceptions import TopologyError
from proxmox_storage_drs.pve import PveClient
from proxmox_storage_drs.state import State, active_disk_cooldowns, empty_state
from proxmox_storage_drs.units import format_duration_seconds

# Section 3.5's disk-key regex, verbatim. Every bus counts (AGENTS.md section
# 6 domain rule 8) -- a regex that only matched scsi* would silently
# mis-account capacity.
_DISK_KEY_RE = re.compile(
    r"^(?:ide[0-3]|sata[0-5]|scsi(?:[0-9]|[12][0-9]|30)|virtio(?:[0-9]|1[0-5])"
    r"|efidisk0|tpmstate0|unused\d+)$"
)

# PVE's own config-file size suffixes (section 3.5's `size=512G`): binary
# units without an explicit "i", unlike this project's own units.py, which
# is for *our* config file, not for parsing PVE's. Kept as a fallback only --
# GET /storage/{s}/content is the authoritative size (section 3.5), used
# whenever it has an entry for the volume.
_PVE_CONFIG_SIZE_RE = re.compile(r"^([0-9]+(?:\.[0-9]+)?)([KMGT])$")

# Section 3.5: "falling back to the storage type's default (raw for LVM,
# qcow2 for directory storages, raw for ZFS zvols)".
_DEFAULT_FORMAT_BY_STORAGE_TYPE = {
    "lvm": "raw",
    "lvmthin": "raw",
    "zfspool": "raw",
    "rbd": "raw",
    "iscsi": "raw",
    "iscsidirect": "raw",
    "dir": "qcow2",
    "nfs": "qcow2",
    "cifs": "qcow2",
    "cephfs": "qcow2",
    "pbs": "raw",  # never holds `images`; content-listed only for completeness
}


def _parse_pve_config_size_bytes(value: str) -> int | None:
    """Parse a `size=` value from a VM config line, e.g. ``"512G"``.

    Returns ``None`` if it does not match -- callers fall back further, or
    treat the disk's size as unknown, rather than raising: this is only a
    fallback for when ``GET /storage/{s}/content`` (authoritative, section
    3.5) has no entry for the volume.
    """
    match = _PVE_CONFIG_SIZE_RE.match(value)
    if not match:
        return None
    number, suffix = match.groups()
    factor = {"K": 1 << 10, "M": 1 << 20, "G": 1 << 30, "T": 1 << 40}[suffix]
    return round(float(number) * factor)


def _parse_disk_spec(value: str) -> tuple[str, str, dict[str, str]]:
    """Split a VM config disk value into ``(storage_id, volume_name, params)``.

    E.g. ``"san-a:vm-101-disk-0,size=512G,iothread=1"`` ->
    ``("san-a", "vm-101-disk-0", {"size": "512G", "iothread": "1"})``.
    """
    head, _, rest = value.partition(",")
    storage_id, _, volume_name = head.partition(":")
    params: dict[str, str] = {}
    for part in rest.split(","):
        if not part:
            continue
        key, sep, val = part.partition("=")
        if sep:
            params[key] = val
    return storage_id, volume_name, params


def _split_tags(raw: str) -> set[str]:
    """PVE tags as returned by `cluster/resources`: semicolon-separated,
    with comma tolerated defensively since older tooling used it."""
    if not raw:
        return set()
    normalized = raw.replace(",", ";")
    return {tag.strip() for tag in normalized.split(";") if tag.strip()}


@dataclass(frozen=True, slots=True)
class Disk:
    """One movable-or-pinned disk in `D` for its group. Section 5.1."""

    key: str  # "vmid:device", e.g. "101:scsi0" -- section 11.2's state.json key shape
    vmid: int
    device: str
    vm_name: str
    node: str
    size_bytes: int
    current_storage: str
    format: str
    pinned_reason: str | None  # None means movable (d in D^mov, section 5.3 (C3))


@dataclass(frozen=True, slots=True)
class Storage:
    """One storage in a group, with the data section 5.3's constraints need."""

    id: str
    capability_weight: float
    reserve_factor: float
    saturation_load: float | None
    capacity_bytes: int
    used_bytes: int
    foreign_used_bytes: int  # U^ext, section 5.1.1
    saferemove: bool
    saferemove_throughput_bytes_per_sec: float | None


@dataclass(frozen=True, slots=True)
class Group:
    """One storage group: section 5's independent optimization unit."""

    name: str
    storages: tuple[Storage, ...]
    disks: tuple[Disk, ...]  # every d in D for this group, pinned or not


@dataclass(frozen=True, slots=True)
class Topology:
    """The whole cluster's worth of groups, as seen by this run."""

    groups: tuple[Group, ...]
    warnings: tuple[str, ...]


def _resolve_reserve_factor(storage_cfg: StorageConfig, config: Config) -> float:
    if storage_cfg.reserve_factor is not None:
        return storage_cfg.reserve_factor
    return config.snapshot_reserve.factor


def _pick_active_node(storage_id: str, storage_resources: list[dict[str, Any]]) -> str:
    """Any node reporting this (shared) storage as available. Section 3.5's
    node-scoped status/content calls need one concrete node even for a
    cluster-wide shared storage; every node reports the same data for it
    (verified against a live cluster). Prefers a node reporting `status:
    "available"` over one that merely lists the storage, so a node that
    happens to have it configured but currently unreachable is not picked
    first when a working one exists.
    """
    candidates = [r for r in storage_resources if r.get("storage") == storage_id]
    candidates.sort(key=lambda r: r.get("status") != "available")
    for resource in candidates:
        node = resource.get("node")
        if isinstance(node, str):
            return node
    raise TopologyError(f"storage {storage_id!r} is not reported active on any node")


def _validate_group_storages(
    groups: tuple[GroupConfig, ...], definitions_by_id: dict[str, dict[str, Any]]
) -> list[str]:
    """Section 11.1: "storage ids exist in the cluster" -- fatal, not a
    warning, per that rule's own rationale (a typo silently excludes a
    storage rather than erroring). Returns non-fatal warnings for storages
    that exist but look questionable (not shared)."""
    warnings: list[str] = []
    for group in groups:
        for storage_cfg in group.storages:
            definition = definitions_by_id.get(storage_cfg.id)
            if definition is None:
                raise TopologyError(
                    f"group {group.name!r} references storage {storage_cfg.id!r}, "
                    "which does not exist in this cluster"
                )
            content_types = {c.strip() for c in definition.get("content", "").split(",")}
            if "images" not in content_types:
                raise TopologyError(
                    f"group {group.name!r} storage {storage_cfg.id!r} does not have "
                    f"'images' in its content list ({sorted(content_types)}); "
                    "it can never hold a VM disk"
                )
            if not definition.get("shared"):
                warnings.append(
                    f"group {group.name!r} storage {storage_cfg.id!r} is not marked "
                    "shared; migrations may only work for VMs already on its node"
                )
    return warnings


def _default_format(storage_type: str) -> str:
    return _DEFAULT_FORMAT_BY_STORAGE_TYPE.get(storage_type, "raw")


def _disk_snapshot_or_orphan_reason(
    vmid: int,
    disk_specs: dict[str, tuple[str, str, dict[str, str]]],
    real_snapshots: list[dict[str, Any]],
    content_by_storage: dict[str, list[dict[str, Any]]],
) -> str | None:
    """Section 3.7: pin every disk of a VM that has a real snapshot, or an
    unreferenced companion volume (a volume-chain member or an orphan) on
    any storage its own disks reference. Returns a human-readable reason,
    or None.
    """
    if real_snapshots:
        return f"snapshots present ({len(real_snapshots)})"

    referenced_volids = {f"{storage}:{name}" for storage, name, _ in disk_specs.values()}
    for storage_id, _name, _params in disk_specs.values():
        for item in content_by_storage.get(storage_id, ()):
            if item.get("vmid") == vmid and item.get("volid") not in referenced_volids:
                return "unreferenced companion volume (snapshot chain or orphan)"
    return None


@dataclass(frozen=True, slots=True)
class _ClusterData:
    """Everything fetched before the per-VM join, gathered in one place so
    the join itself (`_collect_vm_disks`) takes one argument bundle rather
    than seven."""

    storage_group_of: dict[str, str]
    definitions_by_id: dict[str, dict[str, Any]]
    content_by_id: dict[str, list[dict[str, Any]]]
    status_by_id: dict[str, dict[str, Any]]


def _fetch_cluster_data(client: PveClient, config: Config) -> tuple[_ClusterData, list[str]]:
    storage_group_of = {
        storage_cfg.id: group.name for group in config.groups for storage_cfg in group.storages
    }
    definitions_by_id = {d["storage"]: d for d in client.storage_definitions()}
    warnings = _validate_group_storages(config.groups, definitions_by_id)

    # storage_resources() is fetched exactly once here, never per-storage --
    # section 3.5's whole point in specifying a per-run cache.
    storage_resources = client.storage_resources()
    active_node_of = {sid: _pick_active_node(sid, storage_resources) for sid in storage_group_of}
    content_by_id = {
        sid: client.storage_content(active_node_of[sid], sid) for sid in storage_group_of
    }
    status_by_id = {
        sid: client.storage_status(active_node_of[sid], sid) for sid in storage_group_of
    }
    data = _ClusterData(
        storage_group_of=storage_group_of,
        definitions_by_id=definitions_by_id,
        content_by_id=content_by_id,
        status_by_id=status_by_id,
    )
    return data, warnings


def _pin_reason(
    *,
    vm_excluded: bool,
    disk_excluded: bool,
    snapshot_reason: str | None,
    cooldown_remaining_seconds: float,
    lock: str | None,
    device: str,
    include_unused_disks: bool,
) -> str | None:
    """Section 5.3 (C2)'s pin conditions, in the order the plan lists them
    -- the first that applies is reported; a disk can only have one
    reason. ``cooldown_remaining_seconds`` (``> 0`` means still pinned) is
    a precomputed value, not a `state.State` lookup done here -- this
    function stays a pure decision over already-resolved flags, exactly
    like `snapshot_reason` already is, per AGENTS.md section 5 ("one
    implementation" of the cooldown-expiry arithmetic itself lives in
    `state.cooldown_remaining_seconds()`, not duplicated here)."""
    if vm_excluded:
        return "excluded by config"
    if disk_excluded:
        return "excluded by config (exclude.disks)"
    if snapshot_reason is not None:
        return snapshot_reason
    if cooldown_remaining_seconds > 0:
        return (
            f"cooldown: moved recently, {format_duration_seconds(cooldown_remaining_seconds)} "
            "left on gates.cooldown_per_disk"
        )
    if lock:
        return f"locked: {lock}"
    if device.startswith("unused") and not include_unused_disks:
        return "excluded: unused disk (exclude.include_unused_disks=false)"
    return None


def _resolve_disk_size_and_format(
    key: str, volid: str, storage_id: str, params: dict[str, str], data: _ClusterData
) -> tuple[int, str, str | None]:
    """Section 3.5: content listing is authoritative; the config's own
    `size=` is only a fallback, flagged with a warning when used."""
    content_item = next(
        (c for c in data.content_by_id[storage_id] if c.get("volid") == volid), None
    )
    storage_type = data.definitions_by_id[storage_id].get("type", "")
    if content_item is not None:
        return (
            int(content_item["size"]),
            content_item.get("format") or _default_format(storage_type),
            None,
        )
    size_bytes = _parse_pve_config_size_bytes(params.get("size", "")) or 0
    warning = (
        f"{key}: {volid!r} not found in {storage_id!r}'s content listing; "
        "using the VM config's own size= (unauthoritative, section 3.5)"
    )
    return size_bytes, _default_format(storage_type), warning


@dataclass(frozen=True, slots=True)
class _VmFetch:
    """One VM's network-fetched data, before the join. Section 3.5/P-02:
    the fetch itself (this dataclass's construction, `_fetch_vm`) is what
    runs concurrently across `config.proxmox.read_workers` threads; the join
    that follows (`_join_vm_disks`) is pure and stays single-threaded so
    `disks_by_group`/`referenced_volids`/`warnings` never need locking."""

    resource: dict[str, Any]
    raw_config: dict[str, Any]
    real_snapshots: list[dict[str, Any]]


def _fetch_vm(client: PveClient, resource: dict[str, Any]) -> _VmFetch:
    """The two per-VM network calls (section 3.5), with nothing else --
    this is the unit `ThreadPoolExecutor` runs concurrently."""
    vmid = int(resource["vmid"])
    node = resource["node"]
    raw_config = client.vm_config(node, vmid)
    real_snapshots = [s for s in client.vm_snapshots(node, vmid) if s.get("name") != "current"]
    return _VmFetch(resource=resource, raw_config=raw_config, real_snapshots=real_snapshots)


def _join_vm_disks(
    config: Config,
    fetch: _VmFetch,
    data: _ClusterData,
    disks_by_group: dict[str, list[Disk]],
    referenced_volids: dict[str, set[str]],
    warnings: list[str],
    cooldowns_by_group: dict[str, dict[str, float]],
) -> None:
    """Join one already-fetched VM's disks into `disks_by_group`, appending
    any warnings (ungrouped disks, unauthoritative sizes) in place. Pure
    (no network I/O) so `build_topology` can run it single-threaded, in
    cluster-resource order, right after the concurrent fetch phase --
    keeping `disks_by_group`/`warnings` ordering identical to a fully
    sequential run regardless of `config.proxmox.read_workers`.

    ``cooldowns_by_group`` is ``build_topology()``'s one-time-per-group
    ``state.active_disk_cooldowns()`` result (bare ``vmid:device`` ->
    seconds remaining), computed once up front rather than re-read from
    `state.State` per disk here."""
    resource = fetch.resource
    raw_config = fetch.raw_config
    vmid = int(resource["vmid"])
    node = resource["node"]
    vm_name = raw_config.get("name", resource.get("name", str(vmid)))
    lock = raw_config.get("lock")  # section 9.3: config carries it, no extra call needed
    tags = _split_tags(resource.get("tags", ""))
    vm_excluded = vmid in set(config.exclude.vmids) or bool(tags & set(config.exclude.tags))

    disk_specs: dict[str, tuple[str, str, dict[str, str]]] = {}
    for device, value in raw_config.items():
        if not _DISK_KEY_RE.match(device):
            continue
        storage_id, volume_name, params = _parse_disk_spec(value)
        if params.get("media") == "cdrom":
            continue  # section 3.5: ISO/empty/cloudinit media -- never in D
        disk_specs[device] = (storage_id, volume_name, params)

    snapshot_reason = _disk_snapshot_or_orphan_reason(
        vmid, disk_specs, fetch.real_snapshots, data.content_by_id
    )
    excluded_disk_keys = set(config.exclude.disks)

    for device, (storage_id, volume_name, params) in disk_specs.items():
        key = f"{vmid}:{device}"
        group_name = data.storage_group_of.get(storage_id)
        if group_name is None:
            # Section 5.3 (C2): unmanaged, not in any D, reported for
            # visibility so an omission from `groups` is not silent.
            warnings.append(
                f"{key} is on storage {storage_id!r}, which is not in any "
                "configured group -- ungrouped, not managed"
            )
            continue

        volid = f"{storage_id}:{volume_name}"
        referenced_volids[storage_id].add(volid)
        size_bytes, disk_format, size_warning = _resolve_disk_size_and_format(
            key, volid, storage_id, params, data
        )
        if size_warning:
            warnings.append(size_warning)

        pinned_reason = _pin_reason(
            vm_excluded=vm_excluded,
            disk_excluded=key in excluded_disk_keys,
            snapshot_reason=snapshot_reason,
            cooldown_remaining_seconds=cooldowns_by_group.get(group_name, {}).get(key, 0.0),
            lock=lock,
            device=device,
            include_unused_disks=config.exclude.include_unused_disks,
        )

        disks_by_group[group_name].append(
            Disk(
                key=key,
                vmid=vmid,
                device=device,
                vm_name=vm_name,
                node=node,
                size_bytes=size_bytes,
                current_storage=storage_id,
                format=disk_format,
                pinned_reason=pinned_reason,
            )
        )


def _build_storages(
    group_cfg: GroupConfig,
    config: Config,
    data: _ClusterData,
    referenced_volids: dict[str, set[str]],
) -> tuple[Storage, ...]:
    storages: list[Storage] = []
    for storage_cfg in group_cfg.storages:
        sid = storage_cfg.id
        definition = data.definitions_by_id[sid]
        status = data.status_by_id[sid]
        if config.snapshot_reserve.count_foreign_volumes:
            foreign_bytes = sum(
                int(item["size"])
                for item in data.content_by_id[sid]
                if item.get("volid") not in referenced_volids[sid]
            )
        else:
            foreign_bytes = 0
        throughput = definition.get("saferemove_throughput")
        storages.append(
            Storage(
                id=sid,
                capability_weight=storage_cfg.capability_weight,
                reserve_factor=_resolve_reserve_factor(storage_cfg, config),
                saturation_load=storage_cfg.saturation_load,
                capacity_bytes=int(status["total"]),
                used_bytes=int(status["used"]),
                foreign_used_bytes=foreign_bytes,
                saferemove=bool(definition.get("saferemove", False)),
                saferemove_throughput_bytes_per_sec=(
                    float(throughput) if throughput is not None else None
                ),
            )
        )
    return tuple(storages)


def build_topology(
    client: PveClient,
    config: Config,
    state: State | None = None,
    now: datetime | None = None,
) -> Topology:
    """Build the whole cluster's :class:`Topology` for this run.

    One pass: every read call this needs is made exactly once, in the order
    section 3.5 lists them, and the result is handed to every later stage
    (the load model, the solver, the scheduler) rather than re-fetched.

    ``state``/``now`` are section 5.3 (C2)'s "``d`` is within its per-disk
    cooldown -> also pin to current": ``state`` defaults to
    ``state.empty_state()`` (no cooldowns recorded, matching every call
    site until `execute.py` writes any), and ``now`` defaults to the real
    current time -- an explicit parameter, per `.agents/testing.md`'s
    "inject the clock", since this function is already a real I/O boundary
    (like `metrics.py`'s own `time.time()` calls) that a test can override
    without monkeypatching a module-global clock.
    """
    if state is None:
        state = empty_state()
    if now is None:
        now = datetime.now(timezone.utc)
    data, warnings = _fetch_cluster_data(client, config)

    disks_by_group: dict[str, list[Disk]] = {group.name: [] for group in config.groups}
    referenced_volids: dict[str, set[str]] = {sid: set() for sid in data.storage_group_of}
    cooldowns_by_group: dict[str, dict[str, float]] = {
        group.name: active_disk_cooldowns(
            state, group.name, config.gates.cooldown_per_disk_seconds, now
        )
        for group in config.groups
    }

    considered: list[dict[str, Any]] = []
    for resource in client.vm_resources():
        if resource.get("type") != "qemu":
            continue  # section 3.5 scopes this tool to QEMU VMs only, never LXC
        if config.exclude.running_only and resource.get("status") != "running":
            continue  # never fetched: section 3.5's read-path cost note
        considered.append(resource)

    # REVIEW.md P-02: `config.proxmox.read_workers` bounds a thread pool for
    # the per-VM fetch (section 3.5's "no batch config endpoint, so
    # concurrency is the only lever"), not for the join that follows --
    # `Executor.map` returns results in `considered`'s order even though the
    # fetches themselves complete out of order, so the join phase below sees
    # exactly the same per-VM order a sequential run would, keeping
    # `disks_by_group`/`warnings` ordering (and so `show-load`'s output)
    # independent of `read_workers` and of thread scheduling.
    if considered:
        with ThreadPoolExecutor(max_workers=max(1, config.proxmox.read_workers)) as pool:
            fetched = list(pool.map(lambda resource: _fetch_vm(client, resource), considered))
    else:
        fetched = []

    for fetch in fetched:
        _join_vm_disks(
            config, fetch, data, disks_by_group, referenced_volids, warnings, cooldowns_by_group
        )

    groups = tuple(
        Group(
            name=group_cfg.name,
            storages=_build_storages(group_cfg, config, data, referenced_volids),
            disks=tuple(disks_by_group[group_cfg.name]),
        )
        for group_cfg in config.groups
    )
    return Topology(groups=groups, warnings=tuple(warnings))
