# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""``pve-storage-drs collect-testdata``: capture, anonymize and write a
diagnostic bundle. See IMPLEMENTATION_PLAN.md section 16, especially 16.1
(the bundle layout), 16.2 (what gets captured and why it is a superset of
the configured path) and 16.4 (the command itself).

This module is read-only and dry-run-only by construction: it never calls
``PveClient.move_disk()``, and the recording clients below raise rather than
attempt one (defense in depth -- ``cli.py`` also refuses ``--mode
confirm``/``auto`` alongside ``collect-testdata`` before this module is ever
reached).

Two phases, deliberately kept apart: **capture** (this module talks to the
real cluster and Prometheus, through the recording client wrappers below,
which are the *only* things in this module that touch the network) fills an
in-memory, still-real structure; **anonymize** (every value passed through
:mod:`proxmox_storage_drs.anonymize`) produces what actually reaches
:func:`write_bundle_dir`. Nothing unanonymized ever reaches disk.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import logging
import re
import tarfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Any, Callable

from proxmox_storage_drs import __version__
from proxmox_storage_drs.anonymize import (
    CLUSTER_TASK_FIELDS,
    NODE_LIST_FIELDS,
    STORAGE_CONTENT_FIELDS,
    STORAGE_DEFINITION_FIELDS,
    STORAGE_RESOURCE_FIELDS,
    STORAGE_STATUS_FIELDS,
    VM_RESOURCE_FIELDS,
    VM_SNAPSHOT_FIELDS,
    VM_STATUS_CURRENT_FIELDS,
    Mapper,
    filter_allowed_fields,
    filter_disk_value_params,
    filter_vm_config_fields,
    load_or_create_salt,
    salt_fingerprint,
    sanitize_snapshot_name,
)
from proxmox_storage_drs.config import Config, ResolvedConfig
from proxmox_storage_drs.exceptions import BundleError, MetricsError, PveApiError, TopologyError
from proxmox_storage_drs.metrics import (
    RAW_METRIC_FIELDS,
    PrometheusClient,
    VerifyMetricsReport,
    build_quantile_over_time_promql,
    build_rate_promql,
    raw_metric_name,
    resolve_node_selector,
    verify_metrics,
)
from proxmox_storage_drs.pve import PveClient
from proxmox_storage_drs.topology import (
    DISK_KEY_RE,
    Topology,
    _pick_active_node,
    build_topology,
    parse_disk_spec,
)
from proxmox_storage_drs.units import parse_duration_seconds

logger = logging.getLogger(__name__)

# One day, in seconds: section 16.2's chunk size for a range query, chosen
# so a request never runs into a backend's own max_samples limit, and
# "deterministically" -- chunk boundaries fall on the range's own start,
# never on wall-clock "now".
_CHUNK_SECONDS = 86400.0

# Section 16.2's own worked example: 6 raw metrics * every disk.
_METRICS_PER_DISK = len(RAW_METRIC_FIELDS)


def hash_query_text(text: str) -> str:
    """The cache key both this module (writing) and ``replay.py`` (reading)
    derive a bundle filename from -- sha256 of the exact PromQL text. Range
    files are keyed on text alone, not on the literal start/end/step: a
    bundle captures exactly one superset range per (group, metric) pair at
    ``metrics.step`` (the only step this project ever queries at for a
    given config), and a replay request for a *narrower* window of the same
    query (a different forecaster's own, smaller ``required_range()``) is
    served by trimming the one stored series -- see ``replay.py``'s own
    docstring for why an exact match on the literal range would defeat the
    point of capturing a superset at all."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_label_name(label_name: str) -> str:
    return hashlib.sha256(label_name.encode("utf-8")).hexdigest()


# ------------------------------------------------------------------ options


@dataclass(frozen=True, slots=True)
class CaptureOptions:
    output_dir: str
    estimate_only: bool = False
    range_seconds: float | None = None  # None -> support.capture_range
    step_seconds: float | None = None  # None -> metrics.step
    no_series: bool = False
    no_archive: bool = False
    salt_path: str | None = None  # None -> support.salt_path
    new_salt: bool = False


@dataclass(frozen=True, slots=True)
class CaptureEstimate:
    group_count: int
    disk_count: int
    query_count: int
    sample_points: int
    range_seconds: float
    step_seconds: float

    def exceeds(self, max_series_points: int) -> bool:
        return self.sample_points > max_series_points


def capture_range_seconds(config: Config, override: float | None) -> float:
    """Section 16.2's ``capture_range = max(...)`` -- the union of every
    forecaster's ``required_range()``, not just the configured one, unless
    ``--range``/``override`` was given."""
    if override is not None:
        return override
    configured = config.support.capture_range
    if configured != "auto":
        return parse_duration_seconds(configured)
    return max(
        config.window.lookback_seconds,
        config.forecast.seasonal_lookback_days * 86400.0,
        2 * config.forecast.holt_winters.seasonal_periods * config.metrics.step_seconds,
    )


def estimate_capture(
    topology: Topology,
    config: Config,
    *,
    range_seconds: float,
    step_seconds: float,
    no_series: bool,
) -> CaptureEstimate:
    """Section 16.2: print this before fetching anything."""
    disk_count = sum(len(group.disks) for group in topology.groups)
    group_count = len(topology.groups)
    # verify-metrics' own instant query per metric, the two quantile
    # reductions per metric per group, one range query per metric per group.
    query_count = 3 * _METRICS_PER_DISK + group_count * (1 * _METRICS_PER_DISK) * (
        1 if no_series else 2
    )
    query_count += 3  # label_values for vmid/device/node
    points_per_disk = 0 if no_series else int(range_seconds / max(step_seconds, 1.0))
    sample_points = disk_count * _METRICS_PER_DISK * points_per_disk
    return CaptureEstimate(
        group_count=group_count,
        disk_count=disk_count,
        query_count=query_count,
        sample_points=sample_points,
        range_seconds=range_seconds,
        step_seconds=step_seconds,
    )


# -------------------------------------------------------------- call log


@dataclass
class CallRecord:
    description: str
    outcome: str  # ok | http_error | empty | refused | skipped
    detail: str | None = None


@dataclass
class CaptureLog:
    calls: list[CallRecord] = field(default_factory=list)

    def record(self, description: str, outcome: str, detail: str | None = None) -> None:
        self.calls.append(CallRecord(description, outcome, detail))

    @property
    def ok(self) -> bool:
        return all(c.outcome in ("ok", "empty", "skipped") for c in self.calls)


def _guarded(log: CaptureLog, description: str, fn: Callable[[], Any]) -> Any | None:
    """Run ``fn()``, recording its outcome in ``log``. Returns ``None`` (and
    records ``http_error``) rather than raising, for a capture step that
    section 16.2 says must not abort the whole bundle -- 'failures are
    recorded, never rendered as absence'."""
    try:
        result = fn()
    except (PveApiError, MetricsError) as exc:
        log.record(description, "http_error", str(exc))
        return None
    if result == [] or result == {}:
        log.record(description, "empty")
    else:
        log.record(description, "ok")
    return result


# --------------------------------------------------------- recording clients


class RecordingPveClient(PveClient):
    """Wraps a real, already-authenticated :class:`PveClient` and records
    every call's outcome as a side effect -- the single set of PVE calls
    ``build_topology()`` and this module's own extra reads (``cluster_tasks``,
    a fresh ``storage_definitions``/``node_names`` for the bundle's own
    top-level files) both go through, so nothing is fetched twice."""

    def __init__(self, inner: PveClient, log: CaptureLog) -> None:
        super().__init__(api=None)
        self._inner = inner
        self._log = log

    def vm_resources(self) -> list[dict[str, Any]]:
        return _guarded(self._log, "vm_resources", self._inner.vm_resources) or []

    def cluster_tasks(self) -> list[dict[str, Any]]:
        return _guarded(self._log, "cluster_tasks", self._inner.cluster_tasks) or []

    def storage_resources(self) -> list[dict[str, Any]]:
        return _guarded(self._log, "storage_resources", self._inner.storage_resources) or []

    def node_names(self) -> list[str]:
        return _guarded(self._log, "node_names", self._inner.node_names) or []

    def storage_definitions(self) -> list[dict[str, Any]]:
        return _guarded(self._log, "storage_definitions", self._inner.storage_definitions) or []

    def vm_config(self, node: str, vmid: int) -> dict[str, Any]:
        return (
            _guarded(self._log, f"vm_config({vmid})", lambda: self._inner.vm_config(node, vmid))
            or {}
        )

    def storage_status(self, node: str, storage: str) -> dict[str, Any]:
        return (
            _guarded(
                self._log,
                f"storage_status({node},{storage})",
                lambda: self._inner.storage_status(node, storage),
            )
            or {}
        )

    def storage_content(self, node: str, storage: str) -> list[dict[str, Any]]:
        return (
            _guarded(
                self._log,
                f"storage_content({node},{storage})",
                lambda: self._inner.storage_content(node, storage),
            )
            or []
        )

    def vm_snapshots(self, node: str, vmid: int) -> list[dict[str, Any]]:
        return (
            _guarded(
                self._log, f"vm_snapshots({vmid})", lambda: self._inner.vm_snapshots(node, vmid)
            )
            or []
        )

    def vm_status_current(self, node: str, vmid: int) -> dict[str, Any]:
        return (
            _guarded(
                self._log,
                f"vm_status_current({vmid})",
                lambda: self._inner.vm_status_current(node, vmid),
            )
            or {}
        )

    def move_disk(self, *args: Any, **kwargs: Any) -> str:  # pragma: no cover - defense in depth
        raise PveApiError("collect-testdata is read-only: move_disk must never be called")

    def task_status(self, node: str, upid: str) -> dict[str, Any]:
        return (
            _guarded(self._log, f"task_status({upid})", lambda: self._inner.task_status(node, upid))
            or {}
        )


class RecordingPrometheusClient(PrometheusClient):
    """Records every ``(path, params) -> response`` pair as a side effect
    of the real request -- the one place this module's Prometheus reads are
    captured, used both directly (the range/quantile loop below) and
    indirectly (``verify_metrics()`` issues its own instant queries and
    ``label_values`` calls through the same client).

    Wraps the caller-supplied ``inner`` client's own ``config``/``session``
    (reused verbatim, not rebuilt from scratch) rather than composing over
    it: ``verify_metrics()``'s signature is typed ``client: PrometheusClient``
    specifically, so this has to *be* one, not merely behave like one."""

    def __init__(self, inner: PrometheusClient, log: CaptureLog) -> None:
        # inner._session's declared type (_SessionLike | requests.Session) is
        # wider than __init__'s own _SessionLike | None -- both are
        # structurally fine (metrics.py's _SessionLike is a Protocol
        # requests.Session already satisfies), mypy just can't see it
        # through the Union. noqa: SLF001 -- same package.
        super().__init__(inner._config, inner._session)  # type: ignore[arg-type]
        self._log = log
        #: Every ``(path, params, raw response)`` this client has served,
        #: in call order. ``verify_metrics()`` issues several queries this
        #: module's own orchestration never constructs by hand (the bare
        #: per-metric sample-series check, the coverage/spacing queries,
        #: ``label_values("__name__")``) -- capturing here, once, at the
        #: transport boundary, rather than trying to replicate metrics.py's
        #: internal call sequence is what makes ``--replay verify-metrics``
        #: reproduce the exact same checks (section 16.2, bullet 1).
        self.captured: list[tuple[str, dict[str, str], Any]] = []

    def _get(self, path: str, params: dict[str, str]) -> Any:
        description = f"{path} {params.get('query', params)}"
        try:
            result = super()._get(path, params)
        except MetricsError as exc:
            self._log.record(description, "http_error", str(exc))
            raise
        if isinstance(result, (list, dict)) and len(result) == 0:
            self._log.record(description, "empty")
        else:
            self._log.record(description, "ok")
        self.captured.append((path, dict(params), result))
        return result


# ------------------------------------------------------------------ bundle


@dataclass
class Bundle:
    manifest: dict[str, Any]
    config_yaml: dict[str, Any]
    findings: dict[str, Any]
    pve_files: dict[str, Any]  # relative path -> JSON-serializable content
    prometheus_files: dict[str, Any]
    salt_fingerprint: str
    ok: bool


def _rebase_all_timestamps(obj: Any, mapper: Mapper, keys: frozenset[str]) -> Any:
    """Recursively rebase every value at a key in ``keys`` found anywhere in
    ``obj`` (a nested dict/list of already-allowlisted data). Used for the
    handful of timestamp-carrying fields (``ctime`` on a volume, a
    snapshot's ``snaptime``) that survive allowlisting but must still not
    leak the real capture date."""
    if isinstance(obj, dict):
        return {
            k: (mapper.rebase_timestamp(v) if k in keys and isinstance(v, (int, float)) else v)
            for k, v in ((k, _rebase_all_timestamps(v, mapper, keys)) for k, v in obj.items())
        }
    if isinstance(obj, list):
        return [_rebase_all_timestamps(item, mapper, keys) for item in obj]
    return obj


_TIMESTAMP_KEYS = frozenset({"ctime", "snaptime", "starttime", "endtime"})


def _anonymize_storage_definitions(
    raw: list[dict[str, Any]], mapper: Mapper
) -> list[dict[str, Any]]:
    out = []
    for item in raw:
        filtered = filter_allowed_fields(item, STORAGE_DEFINITION_FIELDS)
        storage_id = filtered.get("storage")
        if not isinstance(storage_id, str):
            continue
        filtered["storage"] = mapper.storage(storage_id)
        if isinstance(filtered.get("nodes"), str):
            filtered["nodes"] = ",".join(
                mapper.node(n) for n in filtered["nodes"].split(",") if n in mapper.known_nodes
            )
        out.append(filtered)
    return sorted(out, key=lambda item: str(item["storage"]))


def _anonymize_storage_resources(raw: list[dict[str, Any]], mapper: Mapper) -> list[dict[str, Any]]:
    out = []
    for item in raw:
        filtered = filter_allowed_fields(item, STORAGE_RESOURCE_FIELDS)
        storage_id = filtered.get("storage")
        node = filtered.get("node")
        if not isinstance(storage_id, str) or not isinstance(node, str):
            continue
        if node not in mapper.known_nodes:
            continue
        filtered["storage"] = mapper.storage(storage_id)
        filtered["node"] = mapper.node(node)
        out.append(filtered)
    return sorted(out, key=lambda item: (str(item["storage"]), str(item["node"])))


def _anonymize_node_list(raw: list[dict[str, Any]], mapper: Mapper) -> list[dict[str, Any]]:
    out = []
    for item in raw:
        filtered = filter_allowed_fields(item, NODE_LIST_FIELDS)
        node = filtered.get("node")
        if isinstance(node, str):
            filtered["node"] = mapper.node(node)
            out.append(filtered)
    return sorted(out, key=lambda item: str(item["node"]))


def _anonymize_cluster_tasks(raw: list[dict[str, Any]], mapper: Mapper) -> list[dict[str, Any]]:
    out = []
    for item in raw:
        filtered = filter_allowed_fields(item, CLUSTER_TASK_FIELDS)
        upid = filtered.get("upid")
        node = filtered.get("node")
        if isinstance(upid, str):
            new_upid = mapper.upid(upid)
            if new_upid is None:
                continue
            filtered["upid"] = new_upid
        if isinstance(node, str):
            if node not in mapper.known_nodes:
                continue
            filtered["node"] = mapper.node(node)
        if isinstance(filtered.get("user"), str):
            filtered["user"] = mapper.username(filtered["user"])
        out.append(_rebase_all_timestamps(filtered, mapper, _TIMESTAMP_KEYS))
    return sorted(out, key=lambda item: str(item.get("upid", "")))


def _anonymize_disk_value(value: str, mapper: Mapper) -> str | None:
    storage_id, volume_name, params = parse_disk_spec(value)
    if storage_id not in mapper.known_storages:
        return None
    new_storage = mapper.storage(storage_id)
    if params.get("media") == "cdrom":
        kept = filter_disk_value_params(params)
        rebuilt = ",".join([f"{k}={v}" for k, v in kept.items()])
        head = f"{new_storage}:{volume_name}" if volume_name else new_storage
        return f"{head},{rebuilt}" if rebuilt else head
    new_volid = mapper.volume_id(f"{storage_id}:{volume_name}")
    if new_volid is None:
        return None
    kept = filter_disk_value_params(params)
    rebuilt = ",".join(f"{k}={v}" for k, v in kept.items())
    return f"{new_volid},{rebuilt}" if rebuilt else new_volid


def _anonymize_vm_config(raw: dict[str, Any], mapper: Mapper) -> dict[str, Any] | None:
    filtered = filter_vm_config_fields(raw)
    out: dict[str, Any] = {}
    for key, value in filtered.items():
        if key in ("lock", "template"):
            out[key] = value
        elif key == "name":
            continue  # free text -- section 16.3's per-kind table: dropped
        elif isinstance(value, str) and ":" in value:
            new_value = _anonymize_disk_value(value, mapper)
            if new_value is not None:
                out[key] = new_value
        else:
            out[key] = value
    return out


def _anonymize_storage_content(raw: list[dict[str, Any]], mapper: Mapper) -> list[dict[str, Any]]:
    out = []
    for item in raw:
        filtered = filter_allowed_fields(item, STORAGE_CONTENT_FIELDS)
        volid = filtered.get("volid")
        if not isinstance(volid, str):
            continue
        new_volid = mapper.volume_id(volid)
        if new_volid is None:
            continue
        filtered["volid"] = new_volid
        vmid = filtered.get("vmid")
        if isinstance(vmid, int):
            new_vmid = mapper.vmid(vmid)
            if new_vmid is None:
                continue
            filtered["vmid"] = new_vmid
        out.append(filtered)
    return sorted(out, key=lambda item: str(item["volid"]))


def _anonymize_vm_snapshots(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for item in raw:
        filtered = filter_allowed_fields(item, VM_SNAPSHOT_FIELDS)
        name = filtered.get("name")
        if isinstance(name, str):
            filtered["name"] = sanitize_snapshot_name(name)
        out.append(filtered)
    # "current" first (section 3.7's own pseudo-entry), then every real
    # snapshot -- all now named identically ("snapshot"), so this is a
    # stable sort by the only field left, not an identifying one.
    return sorted(out, key=lambda item: item.get("name") != "current")


def _anonymize_vm_resources(raw: list[dict[str, Any]], mapper: Mapper) -> list[dict[str, Any]]:
    out = []
    for item in raw:
        filtered = filter_allowed_fields(item, VM_RESOURCE_FIELDS)
        vmid = filtered.get("vmid")
        node = filtered.get("node")
        if not isinstance(vmid, int) or not isinstance(node, str):
            continue
        new_vmid = mapper.vmid(vmid)
        if new_vmid is None or node not in mapper.known_nodes:
            continue
        filtered["vmid"] = new_vmid
        filtered["node"] = mapper.node(node)
        filtered.pop("name", None)  # free text -- dropped
        if isinstance(filtered.get("tags"), str):
            tags = [t for t in filtered["tags"].replace(",", ";").split(";") if t.strip()]
            filtered["tags"] = ";".join(mapper.tag(t.strip()) for t in tags)
        out.append(filtered)
    return sorted(out, key=lambda item: int(item["vmid"]))


def _label_value_for(label_kind: str, value: str, mapper: Mapper) -> str | None:
    if label_kind == "vmid":
        try:
            new_vmid = mapper.vmid(int(value))
        except ValueError:
            return None
        return None if new_vmid is None else str(new_vmid)
    if label_kind == "node":
        return mapper.node(value) if value in mapper.known_nodes else None
    if label_kind == "device":
        # Passes through unchanged, but only if it actually looks like one
        # of the enumerated bus keys (section 3.5's regex) -- label_values()
        # is a *global* Prometheus query, not scoped to the blockstat
        # measurement, so when the configured device label is literally
        # "instance" (verify-metrics' own check 4 warning: it collides with
        # Prometheus's unrelated scrape-target label of the same name) it
        # can just as easily return a scrape target ("127.0.0.1:8098") as a
        # real device name -- confirmed on a live cluster. Fail closed
        # rather than pass through anything shaped like a device that is
        # not actually one.
        return value if DISK_KEY_RE.match(value) else None
    # "other" -- e.g. __name__ (metric names, from verify_metrics()'s check
    # 1): not an identifier, not the configured device label, and the
    # disk-bus-key shape has no bearing on it at all -- passes through
    # unchanged.
    return value


def _anonymize_prometheus_series(
    result: list[dict[str, Any]],
    vmid_label: str,
    device_label: str,
    mapper: Mapper,
    node_label: str | None = None,
) -> list[dict[str, Any]]:
    """Anonymizes a Prometheus ``result`` list -- both the instant-query
    shape (one ``"value": [ts, v]`` pair) and the range-query shape (a
    ``"values": [[ts, v], ...]`` matrix). Every sample timestamp is rebased
    through ``mapper.rebase_timestamp()``, the same offset the range file's
    own ``start``/``end`` go through -- a live capture against the dev
    cluster found this the hard way: leaving the *points* on the real
    clock while only the file's start/end were rebased meant a replayed
    request's (rebased) window and the stored (real) sample timestamps
    never overlapped at all, so every trim came back empty and every
    disk's coverage silently read 0%.

    ``node_label``, when given, is carried through (its *value* mapped via
    ``mapper.node()``) -- section 16.3's per-kind table keeps all three
    configured labels (vmid/device/node), not just two. The `sum by
    (vmid, device)` rate expressions this module's own driver issues never
    carry a node label at all (section 3.4's own aggregation collapses
    it), but ``verify_metrics()``'s bare-metric-name sample-series check
    queries the raw series directly and does -- dropping it
    unconditionally made ``verify-metrics --replay`` report a live
    cluster's real node label as "missing", which the live command never
    would. Every *other* label is dropped regardless, live cluster
    findings aside -- the allowlist, section 16.3's whole point."""
    out = []
    for series in result:
        labels = series.get("metric", {})
        vmid_raw = labels.get(vmid_label)
        device = labels.get(device_label)
        if vmid_raw is None or not device:
            continue
        # Same fail-closed guard as _label_value_for(): a device label
        # literally named "instance" can carry Prometheus's own unrelated
        # scrape-target value instead of a real device key (confirmed live
        # -- verify-metrics' own check 4 exists for exactly this).
        if not DISK_KEY_RE.match(device):
            continue
        try:
            new_vmid = mapper.vmid(int(vmid_raw))
        except (TypeError, ValueError):
            continue
        if new_vmid is None:
            continue
        new_series = dict(series)
        new_metric = {vmid_label: str(new_vmid), device_label: device}
        if node_label is not None:
            node_value = labels.get(node_label)
            if node_value and node_value in mapper.known_nodes:
                new_metric[node_label] = mapper.node(node_value)
        new_series["metric"] = new_metric
        if "value" in series:
            ts, value = series["value"]
            new_series["value"] = [mapper.rebase_timestamp(float(ts)), value]
        if "values" in series:
            new_series["values"] = [
                [mapper.rebase_timestamp(float(ts)), value] for ts, value in series["values"]
            ]
        out.append(new_series)
    return sorted(out, key=lambda s: sorted(s["metric"].items()))


# ---------------------------------------------------------------- capture


def _load_salt(options: CaptureOptions, config: Config, log: CaptureLog) -> bytes:
    salt_path = options.salt_path or config.support.salt_path
    if not options.new_salt:
        return load_or_create_salt(salt_path)
    from proxmox_storage_drs.anonymize import generate_new_salt

    logger.warning(
        "generating a new anonymization salt: bundles made before and after no longer "
        "share a pseudonym mapping",
        extra={"event": "salt_rotated", "path": salt_path},
    )
    del log  # rotation itself is not a capture call; kept for a uniform signature
    return generate_new_salt(salt_path)


def _capture_pve_vm_files(
    recording_pve: RecordingPveClient, topology: Topology, mapper: Mapper
) -> dict[str, Any]:
    """``RecordingPveClient``'s own methods already guard and record each
    call (never raising, returning a safe empty default on failure), so
    every capture function in this section calls them directly rather than
    wrapping them in a second, redundant :func:`_guarded`."""
    files: dict[str, Any] = {}
    considered_vmids = sorted({disk.vmid for group in topology.groups for disk in group.disks})
    node_by_vmid = {disk.vmid: disk.node for group in topology.groups for disk in group.disks}
    for vmid in considered_vmids:
        node = node_by_vmid[vmid]
        new_vmid = mapper.vmid(vmid)

        anonymized = _anonymize_vm_config(recording_pve.vm_config(node, vmid), mapper)
        if anonymized is not None and new_vmid is not None:
            files[f"vm-config/{new_vmid}.json"] = anonymized

        if new_vmid is not None:
            snaps_raw = recording_pve.vm_snapshots(node, vmid)
            files[f"vm-snapshots/{new_vmid}.json"] = _anonymize_vm_snapshots(snaps_raw)
            status_raw = recording_pve.vm_status_current(node, vmid)
            files[f"vm-status-current/{new_vmid}.json"] = filter_allowed_fields(
                status_raw, VM_STATUS_CURRENT_FIELDS
            )
    return files


def _capture_pve_storage_files(
    recording_pve: RecordingPveClient,
    topology: Topology,
    storage_resources_raw: list[dict[str, Any]],
    known_nodes: frozenset[str],
    mapper: Mapper,
) -> dict[str, Any]:
    files: dict[str, Any] = {}
    node_storage_pairs: set[tuple[str, str]] = set()
    for group in topology.groups:
        for storage in group.storages:
            # Every managed storage needs its own content/status capture
            # (topology.py's own per-storage read pass, section 3.5) even
            # when no disk of this group currently sits on it -- picked the
            # same way topology.py itself picks a node for that call.
            try:
                node_storage_pairs.add(
                    (_pick_active_node(storage.id, storage_resources_raw), storage.id)
                )
            except TopologyError:
                pass  # already surfaced by build_topology() itself; nothing to capture
            for disk in group.disks:
                if disk.current_storage == storage.id:
                    node_storage_pairs.add((disk.node, storage.id))
    for node, storage_id in sorted(node_storage_pairs):
        if node not in known_nodes:
            continue
        new_storage = mapper.storage(storage_id)
        new_node = mapper.node(node)
        files[f"storage-status/{new_node}/{new_storage}.json"] = filter_allowed_fields(
            recording_pve.storage_status(node, storage_id), STORAGE_STATUS_FIELDS
        )
        files[f"storage-content/{new_node}/{new_storage}.json"] = _anonymize_storage_content(
            recording_pve.storage_content(node, storage_id), mapper
        )
    return files


def _capture_pve_files(
    recording_pve: RecordingPveClient,
    topology: Topology,
    known_nodes: frozenset[str],
    mapper: Mapper,
) -> dict[str, Any]:
    storage_resources_raw = recording_pve.storage_resources()
    files: dict[str, Any] = {
        "cluster-resources-vm.json": _anonymize_vm_resources(recording_pve.vm_resources(), mapper),
        "cluster-resources-storage.json": _anonymize_storage_resources(
            storage_resources_raw, mapper
        ),
        "storage-definitions.json": _anonymize_storage_definitions(
            recording_pve.storage_definitions(), mapper
        ),
        "nodes.json": _anonymize_node_list([{"node": n} for n in known_nodes], mapper),
        "cluster-tasks.json": _anonymize_cluster_tasks(recording_pve.cluster_tasks(), mapper),
    }
    files.update(_capture_pve_vm_files(recording_pve, topology, mapper))
    files.update(
        _capture_pve_storage_files(
            recording_pve, topology, storage_resources_raw, known_nodes, mapper
        )
    )
    return files


def _drive_group_series(
    recording_prom: RecordingPrometheusClient,
    config: Config,
    group_name: str,
    node_selector: str | None,
    range_seconds: float,
    step_seconds: float,
    capture_now: datetime,
    options: CaptureOptions,
    log: CaptureLog,
) -> None:
    """Section 16.2 bullets 2-3, one raw metric at a time: the two
    ``quantile_over_time`` instant reductions ``compute_group_load()``
    itself consumes, plus (unless ``--no-series``) the range series over
    ``range_seconds`` every forecaster's own narrower window is trimmed
    from at replay time. Issues the calls only -- ``recording_prom``'s own
    ``captured`` log is what :func:`_anonymize_captured_prometheus` turns
    into bundle files, once, after every driver (this one, ``verify_metrics``,
    :func:`_drive_label_values`) has run."""
    end_epoch = capture_now.timestamp()
    start_epoch = end_epoch - range_seconds
    for field_name in RAW_METRIC_FIELDS:
        metric_name = raw_metric_name(config.metrics, field_name)
        rate_expr = build_rate_promql(
            metric_name,
            config.metrics.labels.vmid,
            config.metrics.labels.device,
            config.metrics.rate_window_seconds,
            node_selector,
        )
        for quantile in (config.window.quantile, config.window.upper_quantile):
            promql = build_quantile_over_time_promql(
                rate_expr, quantile, config.window.lookback_seconds, config.metrics.step_seconds
            )
            _guarded(
                log,
                f"instant quantile_over_time {field_name} q={quantile} ({group_name})",
                partial(recording_prom.instant_query, promql),
            )

        if options.no_series:
            continue
        _issue_range_chunks(recording_prom, rate_expr, start_epoch, end_epoch, step_seconds, log)


def _drive_label_values(
    recording_prom: RecordingPrometheusClient, config: Config, log: CaptureLog
) -> None:
    for label_name in (
        config.metrics.labels.vmid,
        config.metrics.labels.device,
        config.metrics.labels.node,
    ):
        _guarded(
            log, f"label_values {label_name}", partial(recording_prom.label_values, label_name)
        )


def _label_kind_for(label_name: str, labels: Any) -> str:
    if label_name == labels.vmid:
        return "vmid"
    if label_name == labels.node:
        return "node"
    if label_name == labels.device:
        return "device"
    # __name__ (metric names, from verify_metrics()'s own check 1) or
    # anything else: not an identifier at all, and specifically *not* the
    # configured device label, so the disk-bus-key validation
    # "device" gets below must not apply to it -- section 16.3 only ever
    # anonymizes/validates the three *configured* labels.
    return "other"


def _anonymize_query_text(query: str, mapper: Mapper, rate_expr_map: dict[str, str]) -> str:
    """Rewrites captured PromQL text so it matches what a ``--replay`` run
    reconstructs. Two cases:

    - The text contains one of ``rate_expr_map``'s real-selector rate
      expressions (section 3.4's ``sum by (...) (rate(...))``, built with
      the cluster's real node names -- the only thing the real Prometheus
      server can match) as an exact substring -- a bare range query, or
      embedded inside ``quantile_over_time(...)``. Replaced wholesale with
      the pre-built, independently-sorted anonymized equivalent, never by
      substituting node names one at a time inside the text: sorting the
      real names and sorting their pseudonyms can disagree, and a replay
      run always builds its selector by sorting pseudonyms.
    - No known rate expression appears at all -- ``verify_metrics()``'s
      own checks never carry a node selector in the first place (it never
      talks to the PVE API), so there is nothing node-shaped to rewrite,
      and this is a no-op.
    """
    for real_expr, anon_expr in rate_expr_map.items():
        if real_expr in query:
            return query.replace(real_expr, anon_expr)
    return query


def _anonymize_captured_prometheus(
    recording_prom: RecordingPrometheusClient,
    config: Config,
    mapper: Mapper,
    rate_expr_map: dict[str, str],
) -> dict[str, Any]:
    """Turns every ``(path, params, raw response)`` :class:`RecordingPrometheusClient`
    recorded -- from this module's own driver functions *and* from whatever
    ``verify_metrics()`` issued internally -- into anonymized bundle files.
    One pass, after every query for this run has already been issued,
    rather than each driver writing its own files as it goes: this is what
    makes capture complete by construction instead of by having correctly
    anticipated every query metrics.py's internal checks might make."""
    files: dict[str, Any] = {}
    vmid_label = config.metrics.labels.vmid
    device_label = config.metrics.labels.device
    node_label = config.metrics.labels.node

    range_captures: dict[str, list[tuple[float, float, float, list[dict[str, Any]]]]] = {}
    for path, params, raw_result in recording_prom.captured:
        # Mirrors instant_query()/range_query()'s own unwrapping: `_get()`
        # returns the raw `data` dict for these two endpoints (a bare list
        # only for label_values), and both call `.get("result", [])`.
        if path == "/api/v1/query":
            query = _anonymize_query_text(params["query"], mapper, rate_expr_map)
            series = raw_result.get("result", []) if isinstance(raw_result, dict) else []
            files[f"instant/{hash_query_text(query)}.json"] = {
                "query": query,
                "result": _anonymize_prometheus_series(
                    series, vmid_label, device_label, mapper, node_label
                ),
            }
        elif path == "/api/v1/query_range":
            query = _anonymize_query_text(params["query"], mapper, rate_expr_map)
            series = raw_result.get("result", []) if isinstance(raw_result, dict) else []
            range_captures.setdefault(query, []).append(
                (
                    float(params["start"]),
                    float(params["end"]),
                    _parse_step_param(params["step"]),
                    series,
                )
            )
        elif path.startswith("/api/v1/label/") and path.endswith("/values"):
            label_name = path[len("/api/v1/label/") : -len("/values")]
            kind = _label_kind_for(label_name, config.metrics.labels)
            mapped = [
                v
                for value in (raw_result or [])
                if (v := _label_value_for(kind, value, mapper)) is not None
            ]
            files[f"label-values/{hash_label_name(label_name)}.json"] = {
                "label": label_name,
                "result": sorted(set(mapped)),
            }

    for query, captures in range_captures.items():
        start, end, step, result = _stitch_range_captures(captures)
        files[f"range/{hash_query_text(query)}.json"] = {
            "query": query,
            "start": start - mapper.time_offset_seconds,
            "end": end - mapper.time_offset_seconds,
            "step": step,
            "result": _anonymize_prometheus_series(
                result, vmid_label, device_label, mapper, node_label
            ),
        }
    return files


def _parse_step_param(step_text: str) -> float:
    """The inverse of ``metrics._format_promql_duration()``, which this
    project only ever emits as ``f"{seconds:g}s"``."""
    return float(step_text[:-1]) if step_text.endswith("s") else float(step_text)


def _capture_prometheus_files(
    recording_prom: RecordingPrometheusClient,
    topology: Topology,
    config: Config,
    known_nodes: frozenset[str],
    range_seconds: float,
    step_seconds: float,
    capture_now: datetime,
    mapper: Mapper,
    options: CaptureOptions,
    log: CaptureLog,
) -> tuple[dict[str, Any], VerifyMetricsReport | None]:
    verify_report: VerifyMetricsReport | None
    try:
        verify_report = verify_metrics(
            recording_prom, config.metrics, config.window, now=capture_now.timestamp()
        )
    except MetricsError as exc:
        log.record("verify_metrics", "http_error", str(exc))
        verify_report = None

    # The REAL node names: this selector is sent to the real Prometheus
    # (recording_prom's calls are genuine HTTP requests), and only a
    # selector built from the cluster's actual node names matches any real
    # series at all. The query *text* this module writes into the bundle
    # is anonymized afterwards -- a real name here would leak, and it
    # would also never match what a later --replay run's own (anonymized)
    # selector reconstructs, but neither problem is solved by anonymizing
    # the text *before* issuing it: that just queries the real server for
    # a node name it does not have, and gets nothing back (the first of
    # two bugs a live capture against the dev cluster actually hit,
    # section 16.3's "the actual mechanism").
    node_selector = resolve_node_selector(config.metrics, sorted(known_nodes))
    # The second bug that same capture hit: build_node_selector() sorts
    # its *own* input, so blindly substring-replacing each real node name
    # inside already-built query text preserves the *real*-name sort
    # order, while a --replay run building the selector fresh from
    # ReplayPveClient.node_names() sorts the *pseudonyms* -- a different
    # order, hence different text, whenever a real name's lexical rank
    # differs from its pseudonym's. rate_expr_map is built by calling
    # build_rate_promql() a second time with a selector built from
    # pre-anonymized, independently-sorted names, so both sides are each
    # self-consistent constructions rather than one derived from the
    # other by text surgery -- the one substitution
    # _anonymize_query_text() still does (on a query with no node
    # selector at all, e.g. verify_metrics()'s own unscoped checks) has no
    # ordering to get wrong in the first place.
    anon_node_selector = resolve_node_selector(
        config.metrics, sorted(mapper.node(n) for n in known_nodes)
    )
    rate_expr_map = {
        build_rate_promql(
            raw_metric_name(config.metrics, field),
            config.metrics.labels.vmid,
            config.metrics.labels.device,
            config.metrics.rate_window_seconds,
            node_selector,
        ): build_rate_promql(
            raw_metric_name(config.metrics, field),
            config.metrics.labels.vmid,
            config.metrics.labels.device,
            config.metrics.rate_window_seconds,
            anon_node_selector,
        )
        for field in RAW_METRIC_FIELDS
    }
    for group in topology.groups:
        _drive_group_series(
            recording_prom,
            config,
            group.name,
            node_selector,
            range_seconds,
            step_seconds,
            capture_now,
            options,
            log,
        )
    _drive_label_values(recording_prom, config, log)

    files = _anonymize_captured_prometheus(recording_prom, config, mapper, rate_expr_map)
    return files, verify_report


def capture_bundle(
    pve_client: PveClient,
    prometheus_client: PrometheusClient,
    resolved: ResolvedConfig,
    options: CaptureOptions,
    *,
    now: datetime | None = None,
) -> Bundle:
    """Capture and anonymize a diagnostic bundle. Never writes to disk --
    see :func:`write_bundle_dir`/:func:`write_tarball` for that; this
    function's job stops at producing the in-memory :class:`Bundle`."""
    config = resolved.config
    capture_now = now or datetime.now(timezone.utc)
    log = CaptureLog()
    recording_pve = RecordingPveClient(pve_client, log)

    topology = build_topology(recording_pve, config, now=capture_now)

    range_seconds = capture_range_seconds(config, options.range_seconds)
    step_seconds = options.step_seconds or config.metrics.step_seconds
    estimate = estimate_capture(
        topology,
        config,
        range_seconds=range_seconds,
        step_seconds=step_seconds,
        no_series=options.no_series,
    )
    if not options.no_series and estimate.exceeds(config.support.max_series_points):
        raise BundleError(
            f"capture refused: estimated {estimate.sample_points} series sample points exceeds "
            f"support.max_series_points ({config.support.max_series_points}) -- pass --range, "
            "--step or --no-series to bring it under, or raise the config limit"
        )

    salt = _load_salt(options, config, log)
    known_nodes = frozenset(recording_pve.node_names())
    known_storages = frozenset(s.id for group in topology.groups for s in group.storages)
    mapper = Mapper(
        salt=salt,
        capture_start_epoch=capture_now.timestamp(),
        known_nodes=known_nodes,
        known_storages=known_storages,
    )
    mapper.register_vmids(disk.vmid for group in topology.groups for disk in group.disks)

    pve_files = _capture_pve_files(recording_pve, topology, known_nodes, mapper)

    recording_prom = RecordingPrometheusClient(prometheus_client, log)
    prometheus_files, verify_report = _capture_prometheus_files(
        recording_prom,
        topology,
        config,
        known_nodes,
        range_seconds,
        step_seconds,
        capture_now,
        mapper,
        options,
        log,
    )

    findings = _findings_to_json(verify_report, config, mapper)
    config_yaml = _anonymized_config_dict(config, mapper, topology)
    manifest = _build_manifest(
        resolved, topology, estimate, log, salt_fingerprint(salt), capture_now, mapper, options
    )

    return Bundle(
        manifest=manifest,
        config_yaml=config_yaml,
        findings=findings,
        pve_files=pve_files,
        prometheus_files=prometheus_files,
        salt_fingerprint=salt_fingerprint(salt),
        ok=log.ok,
    )


def _issue_range_chunks(
    client: RecordingPrometheusClient,
    promql: str,
    start_epoch: float,
    end_epoch: float,
    step_seconds: float,
    log: CaptureLog,
) -> None:
    """Section 16.2: chunk a long range into day-sized sub-queries,
    deterministically (boundaries fall on ``start_epoch``, never on
    wall-clock 'now'). Issues the calls only -- every chunk lands in
    ``client.captured`` and :func:`_stitch_range_captures` merges them (and
    any *other* range query for the same text, e.g. ``verify_metrics()``'s
    own observed-spacing probe) back into one logical series per disk."""
    chunk_start = start_epoch
    while chunk_start < end_epoch:
        chunk_end = min(chunk_start + _CHUNK_SECONDS, end_epoch)
        _guarded(
            log,
            f"range_query chunk [{chunk_start:.0f},{chunk_end:.0f}]",
            partial(client.range_query, promql, chunk_start, chunk_end, step_seconds),
        )
        chunk_start = chunk_end


def _stitch_range_captures(
    captures: list[tuple[float, float, float, list[dict[str, Any]]]],
) -> tuple[float, float, float, list[dict[str, Any]]]:
    """Merges every ``(start, end, step, result)`` capture for one query
    text -- whichever combination of chunking and repeat calls produced
    them -- into one ``(start, end, step, result)``: the widest start/end
    span, the (uniform) step, and one series per disk with every point from
    every chunk, deduplicated by timestamp and sorted."""
    overall_start = min(c[0] for c in captures)
    overall_end = max(c[1] for c in captures)
    step = captures[0][2]
    by_disk: dict[tuple[tuple[str, str], ...], dict[float, float]] = {}
    for _start, _end, _step, result in captures:
        for series in result or []:
            key = tuple(sorted(series.get("metric", {}).items()))
            points = by_disk.setdefault(key, {})
            for ts, value in series.get("values", []):
                points[float(ts)] = value
    stitched = [
        {"metric": dict(key), "values": sorted(points.items())} for key, points in by_disk.items()
    ]
    return (
        overall_start,
        overall_end,
        step,
        sorted(stitched, key=lambda s: sorted(s["metric"].items())),
    )


# ---------------------------------------------------------------- findings


def _redact_finding_message(message: str, mapper: Mapper) -> str:
    """``verify_metrics()``'s own finding text is written for a human
    reading it against their live cluster, so a few of its messages embed
    real identifiers verbatim (a sample series' own label values, a
    per-disk coverage gap's ``vmid:device``) -- section 16.3's allowlist
    principle applies to free text too, not just structured fields. Rather
    than special-casing every message shape metrics.py might ever produce,
    this substitutes any *whole* number matching an already-registered real
    vmid, and any occurrence of a real node name, with its pseudonym --
    broader than strictly necessary (a coincidental vmid-shaped number that
    is not actually a vmid would also get rewritten), which is the safe
    direction to be wrong in for a privacy control."""
    text = message
    for real_vmid, new_vmid in sorted(mapper.registered_vmids().items()):
        text = re.sub(rf"\b{real_vmid}\b", str(new_vmid), text)
    for real_node in sorted(mapper.known_nodes, key=len, reverse=True):
        text = text.replace(real_node, mapper.node(real_node))
    return text


def _findings_to_json(
    report: VerifyMetricsReport | None, config: Config, mapper: Mapper
) -> dict[str, Any]:
    if report is None:
        return {"verify_metrics": None}
    findings = [
        {"level": f.level, "message": _redact_finding_message(f.message, mapper)}
        for f in report.findings
    ]
    sample_series = {}
    for field_name, labels in report.sample_series.items():
        keep = {
            config.metrics.labels.vmid,
            config.metrics.labels.device,
            config.metrics.labels.node,
        }
        anonymized_labels: dict[str, str] = {}
        for k, v in labels.items():
            if k not in keep:
                continue
            if k == config.metrics.labels.vmid:
                new_vmid = mapper.vmid(int(v)) if str(v).isdigit() else None
                if new_vmid is None:
                    continue
                anonymized_labels[k] = str(new_vmid)
            elif k == config.metrics.labels.node:
                if v not in mapper.known_nodes:
                    continue
                anonymized_labels[k] = mapper.node(v)
            else:
                anonymized_labels[k] = v  # device: passes through unchanged
        sample_series[field_name] = anonymized_labels
    coverage: dict[str, float] = {}
    for disk_key, value in report.coverage_by_disk.items():
        new_vmid = mapper.vmid(disk_key.vmid)
        if new_vmid is None:
            continue
        coverage[f"{new_vmid}:{disk_key.device}"] = value
    return {
        "verify_metrics": {
            "ok": report.ok,
            "findings": findings,
            "sample_series": sample_series,
            "coverage_by_disk": coverage,
            "observed_spacing_seconds": report.observed_spacing_seconds,
        }
    }


# -------------------------------------------------------------- config.yaml


def _anonymized_config_dict(config: Config, mapper: Mapper, topology: Topology) -> dict[str, Any]:
    """Section 16.3's "the configuration in the bundle": credentials and
    endpoints dropped (not blanked), every identifier mapped, everything
    else carried verbatim.

    Built from ``topology.groups`` -- the already-expanded, already
    -resolved :class:`~proxmox_storage_drs.topology.Storage` objects
    ``build_topology()`` produced -- rather than from ``config.groups``
    directly: a ``/…/`` storage pattern (section 11.4) cannot survive
    anonymization as a pattern (its text names real storages), so the
    bundle carries the literal, anonymized ids it matched instead, with
    each storage's already-resolved (pattern-default-or-literal-override)
    ``capability_weight``/``reserve_factor``/``saturation_load`` -- exactly
    what a replay needs, and none of what would let it re-test the
    expansion itself, a gap named here rather than discovered later."""
    groups = []
    for group in topology.groups:
        groups.append(
            {
                "name": mapper.group(group.name),
                "storages": [
                    {
                        "id": mapper.storage(s.id),
                        "capability_weight": s.capability_weight,
                        "reserve_factor": s.reserve_factor,
                        **(
                            {"saturation_load": s.saturation_load}
                            if s.saturation_load is not None
                            else {}
                        ),
                    }
                    for s in group.storages
                ],
            }
        )

    exclude = config.exclude
    return {
        "schema_version": config.schema_version,
        "proxmox": {"read_workers": config.proxmox.read_workers},
        "prometheus": {},
        "metrics": {
            "read_ops": config.metrics.read_ops,
            "write_ops": config.metrics.write_ops,
            "read_bytes": config.metrics.read_bytes,
            "write_bytes": config.metrics.write_bytes,
            "read_time_ns": config.metrics.read_time_ns,
            "write_time_ns": config.metrics.write_time_ns,
            "labels": {
                "vmid": config.metrics.labels.vmid,
                "device": config.metrics.labels.device,
                "node": config.metrics.labels.node,
            },
            "rate_window": config.metrics.rate_window_seconds,
            "step": config.metrics.step_seconds,
            "pvestatd_push_interval": config.metrics.pvestatd_push_interval_seconds,
            # extra_selector is rewritten to the default tier's own
            # equivalent, never carried verbatim -- section 16.3.
            "extra_selector": None,
        },
        "window": {
            "lookback": config.window.lookback_seconds,
            "quantile": config.window.quantile,
            "upper_quantile": config.window.upper_quantile,
            "min_coverage": config.window.min_coverage,
        },
        "load_weights": {
            "iotime": config.load_weights.iotime,
            "ops": config.load_weights.ops,
            "bytes": config.load_weights.bytes,
            "read_factor": config.load_weights.read_factor,
            "write_factor": config.load_weights.write_factor,
        },
        "groups": groups,
        "snapshot_reserve": {
            "factor": config.snapshot_reserve.factor,
            "min_free_bytes": config.snapshot_reserve.min_free_bytes,
            "count_foreign_volumes": config.snapshot_reserve.count_foreign_volumes,
        },
        "gates": {
            "drift_threshold": config.gates.drift_threshold,
            "imbalance_threshold": config.gates.imbalance_threshold,
            "cooldown_per_disk": config.gates.cooldown_per_disk_seconds,
            "cooldown_per_storage": config.gates.cooldown_per_storage_seconds,
        },
        "migration": {
            "bwlimit_bytes_per_sec": config.migration.bwlimit_bytes_per_sec,
            "source_load_weight": config.migration.source_load_weight,
            "target_load_weight": config.migration.target_load_weight,
            "payback_horizon": config.migration.payback_horizon_seconds,
            "payback_ratio": config.migration.payback_ratio,
            "max_single_move_duration": config.migration.max_single_move_duration_seconds,
            "account_saferemove_wipe": config.migration.account_saferemove_wipe,
            "wipe_load_weight": config.migration.wipe_load_weight,
            "saturation_ceiling": config.migration.saturation_ceiling,
            "assume_thick_provisioning": config.migration.assume_thick_provisioning,
        },
        "objective": {
            "spread_metric": config.objective.spread_metric,
            "alpha_spread": config.objective.alpha_spread,
            "beta_move_count": config.objective.beta_move_count,
            "gamma_move_bytes_per_tib": config.objective.gamma_move_bytes_per_tib,
            "kappa_vm_affinity": config.objective.kappa_vm_affinity,
            "affinity_counts_pinned_disks": config.objective.affinity_counts_pinned_disks,
            "reserve_violation_penalty": config.objective.reserve_violation_penalty,
        },
        "solver": {
            "backend": config.solver.backend,
            "time_limit_seconds": config.solver.time_limit_seconds,
            "mip_gap": config.solver.mip_gap,
            "heuristic_iterations": config.solver.heuristic_iterations,
        },
        "execution": {
            "mode": "dry-run",  # a bundle's config.yaml never authorizes execution
            "max_concurrent_migrations": config.execution.max_concurrent_migrations,
            "max_migrations_per_run": config.execution.max_migrations_per_run,
            "max_concurrent_per_storage": config.execution.max_concurrent_per_storage,
            "max_replans_per_run": config.execution.max_replans_per_run,
            "abort_on_failure": config.execution.abort_on_failure,
            "poll_interval_seconds": config.execution.poll_interval_seconds,
            "locks": {
                "wait_timeout": config.execution.locks.wait_timeout_seconds,
                "poll_interval": config.execution.locks.poll_interval_seconds,
                "on_timeout": config.execution.locks.on_timeout,
            },
            "source_release": {
                "wait": config.execution.source_release.wait,
                "timeout": config.execution.source_release.timeout_seconds,
            },
            "time_windows": [
                {"days": list(tw.days), "start": tw.start, "end": tw.end}
                for tw in config.execution.time_windows
            ],
        },
        "exclude": {
            "vmids": [v for v in (mapper.vmid(v) for v in exclude.vmids) if v is not None],
            "disks": list(exclude.disks),
            "storages": [mapper.storage(s) for s in exclude.storages if s in mapper.known_storages],
            "tags": [mapper.tag(t) for t in exclude.tags],
            "skip_vms_with_snapshots": exclude.skip_vms_with_snapshots,
            "running_only": exclude.running_only,
            "include_unused_disks": exclude.include_unused_disks,
        },
        "report": {"warn_pinned_load_fraction": config.report.warn_pinned_load_fraction},
        "state": {"path": "state.json"},
        "forecast": {
            "model": config.forecast.model,
            "seasonal_lookback_days": config.forecast.seasonal_lookback_days,
            "holt_winters": {
                "seasonal_periods": config.forecast.holt_winters.seasonal_periods,
                "trend": config.forecast.holt_winters.trend,
                "seasonal": config.forecast.holt_winters.seasonal,
                "residual_z": config.forecast.holt_winters.residual_z,
            },
        },
        "support": {
            "salt_path": "anonymization-salt",
            "bundle_dir": "testdata",
            "max_series_points": config.support.max_series_points,
            "capture_range": config.support.capture_range,
        },
    }


# ----------------------------------------------------------------- manifest


def _build_manifest(
    resolved: ResolvedConfig,
    topology: Topology,
    estimate: CaptureEstimate,
    log: CaptureLog,
    fingerprint: str,
    capture_now: datetime,
    mapper: Mapper,
    options: CaptureOptions,
) -> dict[str, Any]:
    del resolved
    # The manifest deliberately never carries the real capture date --
    # section 16.3: "the manifest records the duration and the wall-clock
    # -hour alignment rather than the date". `synthetic_now_epoch` is
    # `capture_now` rebased through the same week-aligned offset every
    # other timestamp in the bundle goes through (`mapper.rebase_timestamp`),
    # so it preserves hour-of-day/day-of-week and nothing else -- this is
    # also exactly the fixed reference instant `replay.bundle_reference_now()`
    # hands back for every replay run against this bundle.
    synthetic_now_epoch = mapper.rebase_timestamp(capture_now.timestamp())
    return {
        "schema_version": 1,
        "generated_by": f"pve-storage-drs {__version__}",
        "capture": {
            "synthetic_now_epoch": synthetic_now_epoch,
            "range_seconds": estimate.range_seconds,
            "step_seconds": estimate.step_seconds,
            "no_series": options.no_series,
        },
        "counts": {
            "groups": len(topology.groups),
            "storages": sum(len(g.storages) for g in topology.groups),
            "vms": len({d.vmid for g in topology.groups for d in g.disks}),
            "disks": sum(len(g.disks) for g in topology.groups),
            "estimated_sample_points": estimate.sample_points,
            "dropped_records": mapper.dropped_records,
        },
        "salt_fingerprint": fingerprint,
        "calls": sorted(
            (
                {"description": c.description, "outcome": c.outcome, "detail": c.detail}
                for c in log.calls
            ),
            key=lambda c: c["description"],
        ),
        "ok": log.ok,
    }


# --------------------------------------------------------------- writer


def _dump_json(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _sorted_dict(obj: Any) -> Any:
    """Recursively sort every mapping's keys -- section 16.1: "every file
    is... written with sorted keys". JSON output gets this from
    ``json.dumps(sort_keys=True)``; ``config.yaml`` goes through
    ``ruamel.yaml`` (this project's one YAML library, section 2.1), whose
    plain dumper preserves whatever order it is handed, so the sort has to
    happen here first."""
    if isinstance(obj, dict):
        return {k: _sorted_dict(obj[k]) for k in sorted(obj, key=str)}
    if isinstance(obj, list):
        return [_sorted_dict(item) for item in obj]
    return obj


def write_bundle_dir(path: str | Path, bundle: Bundle) -> None:
    """Write ``bundle`` as the canonical directory form (section 16.1):
    sorted keys, two-space indent, ``\\n`` endings, plus ``SHA256SUMS``."""
    root = Path(path)
    root.mkdir(parents=True, exist_ok=True)
    files: dict[str, bytes] = {"manifest.json": _dump_json(bundle.manifest)}
    files["findings.json"] = _dump_json(bundle.findings)

    from io import StringIO

    from ruamel.yaml import YAML

    yaml_writer = YAML(typ="safe")
    yaml_writer.default_flow_style = False
    yaml_stream = StringIO()
    yaml_writer.dump(_sorted_dict(bundle.config_yaml), yaml_stream)
    files["config.yaml"] = yaml_stream.getvalue().encode("utf-8")

    for relpath, content in bundle.pve_files.items():
        files[f"pve/{relpath}"] = _dump_json(content)
    for relpath, content in bundle.prometheus_files.items():
        files[f"prometheus/{relpath}"] = _dump_json(content)

    for relpath, data in sorted(files.items()):
        target = root / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    sha_lines = [
        f"{hashlib.sha256(data).hexdigest()}  {relpath}\n"
        for relpath, data in sorted(files.items())
    ]
    (root / "SHA256SUMS").write_text("".join(sha_lines), encoding="utf-8")


def write_tarball(dir_path: str | Path, tar_path: str | Path) -> None:
    """A deterministic ``.tar.gz`` of ``dir_path`` (section 16.1): sorted
    members, ``mtime=0``, ``uid=gid=0``, empty ``uname``/``gname``, fixed
    modes, and a gzip header with ``mtime=0``."""
    root = Path(dir_path)
    members = sorted(p for p in root.rglob("*") if p.is_file())
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.GNU_FORMAT) as tar:
        for member_path in members:
            data = member_path.read_bytes()
            info = tarfile.TarInfo(name=f"{root.name}/{member_path.relative_to(root)}")
            info.size = len(data)
            info.mtime = 0
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(data))
    buffer.seek(0)
    with open(tar_path, "wb") as fh:
        # filename="" (not the default None) suppresses gzip's own FNAME
        # header field -- left at the default, GzipFile falls back to
        # fileobj.name, which would bake the *output path* (an accident of
        # where this particular call happened to write to, e.g. a temp
        # directory) into the compressed bytes, breaking byte-identical
        # repeat captures for no reason connected to the bundle's content.
        with gzip.GzipFile(fileobj=fh, mode="wb", mtime=0, filename="") as gz:
            gz.write(buffer.getvalue())
