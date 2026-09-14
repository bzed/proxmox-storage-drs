# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""collect.py: capture, anonymize and write a diagnostic bundle. See
IMPLEMENTATION_PLAN.md section 16.

No test here talks to a real PVE API or Prometheus (.agents/testing.md):
``tests/unit/fakes.py``'s ``fake_api``/``FakePrometheusSession`` stand in for
both, exactly as ``test_topology.py``/``test_metrics.py`` already do.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
import yaml

from proxmox_storage_drs import anonymize, collect
from proxmox_storage_drs import config as config_module
from proxmox_storage_drs.exceptions import BundleError, PveApiError
from proxmox_storage_drs.metrics import PrometheusClient
from proxmox_storage_drs.pve import PveClient
from proxmox_storage_drs.topology import build_topology
from tests.unit.fakes import FakePrometheusSession, fake_api

CAPTURE_NOW = datetime(2026, 9, 8, 12, 0, 0, tzinfo=timezone.utc)  # an arbitrary Tuesday noon

STORAGE_DEFS = [
    {"storage": "san-a", "type": "rbd", "shared": 1, "content": "images,rootdir"},
    {"storage": "san-b", "type": "rbd", "shared": 1, "content": "images,rootdir"},
]
STORAGE_RESOURCES = [
    {"storage": "san-a", "node": "node1", "status": "available"},
    {"storage": "san-b", "node": "node1", "status": "available"},
]
STORAGE_STATUS = {
    "san-a": {"total": 10 * (1 << 40), "used": 3 * (1 << 40)},
    "san-b": {"total": 5 * (1 << 40), "used": 1 * (1 << 40)},
}
VM_RESOURCES = [
    {"vmid": 101, "node": "node1", "status": "running", "type": "qemu", "tags": "", "name": "db-01"}
]
VM_CONFIGS = {101: {"name": "db-01", "scsi0": "san-a:vm-101-disk-0,size=10G"}}
VM_SNAPSHOTS: dict[int, list[dict[str, Any]]] = {101: [{"name": "current"}]}
CONTENT_SAN_A = [
    {"volid": "san-a:vm-101-disk-0", "vmid": 101, "size": 10 * (1 << 30), "format": "raw"}
]
CONTENT_SAN_B: list[dict[str, Any]] = []

METRIC_NAMES = [
    "blockstat_rd_operations",
    "blockstat_wr_operations",
    "blockstat_rd_bytes",
    "blockstat_wr_bytes",
    "blockstat_rd_total_time_ns",
    "blockstat_wr_total_time_ns",
]


def make_config(tmp_path: Path, **overrides: Any) -> config_module.ResolvedConfig:
    tmp_path.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {
        "schema_version": 1,
        "proxmox": {"host": "pve.example.com", "auth": {"username": "drs@pve"}},
        "prometheus": {"url": "http://localhost:9090"},
        "groups": [{"name": "g1", "storages": [{"id": "san-a"}, {"id": "san-b"}]}],
        # Never the real /var/lib/pve-storage-drs default in a test.
        "support": {"salt_path": str(tmp_path / "salt")},
    }
    data.update(overrides)
    path = tmp_path / "drs.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return config_module.load_config(str(path), env={})


def make_pve_client(
    error_on: str | None = None, error_message: str = "simulated failure"
) -> PveClient:
    responses: dict[str, Any] = {
        "cluster/resources": lambda type: (VM_RESOURCES if type == "vm" else STORAGE_RESOURCES),
        "storage": STORAGE_DEFS,
        "nodes": [{"node": "node1"}],
        "cluster/tasks": [],
        "nodes/node1/storage/san-a/status": STORAGE_STATUS["san-a"],
        "nodes/node1/storage/san-b/status": STORAGE_STATUS["san-b"],
        "nodes/node1/storage/san-a/content": CONTENT_SAN_A,
        "nodes/node1/storage/san-b/content": CONTENT_SAN_B,
        "nodes/node1/qemu/101/config": VM_CONFIGS[101],
        "nodes/node1/qemu/101/snapshot": VM_SNAPSHOTS[101],
        "nodes/node1/qemu/101/status/current": {},
        "version": {"version": "8.2.1"},
    }
    error = PveApiError(error_message) if error_on else None
    api = fake_api(responses, error=None)
    client = PveClient(api)
    if error_on:
        # Only the named path fails -- swap that one response for the error
        # by wrapping fake_api with a second, selectively-failing client.
        failing_responses = dict(responses)
        failing_responses[error_on] = _Raise(error)
        client = PveClient(fake_api(failing_responses))
    return client


class _Raise:
    def __init__(self, exc: BaseException | None) -> None:
        self._exc = exc

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        raise self._exc  # type: ignore[misc]


def _instant_answer(params: dict[str, str]) -> dict[str, Any]:
    query = params["query"]
    if "blockstat_rd_total_time_ns" in query and "quantile_over_time" in query:
        # A real, "now"-adjacent timestamp -- not an arbitrary fixed one --
        # since this is exactly what the collector's own timestamp-rebase
        # step has to shift into the bundle's synthetic epoch correctly.
        return {
            "result": [
                {
                    "metric": {"vmid": "101", "instance": "scsi0"},
                    "value": [CAPTURE_NOW.timestamp(), "1.5"],
                }
            ]
        }
    if query == "blockstat_rd_operations":
        # verify_metrics()'s own bare-metric-name sample-series check --
        # not wrapped in sum by(...), so the real "nodename" label a live
        # series carries is still present here, unlike the rate
        # expressions above (section 3.4's sum by (vmid, device) already
        # collapses it).
        return {
            "result": [
                {
                    "metric": {"vmid": "101", "instance": "scsi0", "nodename": "node1"},
                    "value": [CAPTURE_NOW.timestamp(), "1.5"],
                }
            ]
        }
    return {"result": []}


def _range_answer(params: dict[str, str]) -> dict[str, Any]:
    query = params["query"]
    if "blockstat_rd_total_time_ns" in query:
        # Real points inside the requested [start, end] window, like a
        # real Prometheus would answer -- not a fixed, unrelated timestamp.
        start = float(params["start"])
        return {
            "result": [
                {
                    "metric": {"vmid": "101", "instance": "scsi0"},
                    "values": [[start, "1.0"], [start + 300.0, "2.0"]],
                }
            ]
        }
    return {"result": []}


def make_prometheus_client() -> PrometheusClient:
    session = FakePrometheusSession(
        answers={
            "label/__name__/values": METRIC_NAMES,
            "label/vmid/values": ["101"],
            "label/instance/values": ["scsi0"],
            "label/nodename/values": ["node1"],
            "api/v1/query_range": _range_answer,
            "api/v1/query": _instant_answer,
            "api/v1/status/buildinfo": {"version": "2.45.0"},
        }
    )
    return PrometheusClient(config_module.PrometheusConfig(url="http://localhost:9090"), session)


def capture(tmp_path: Path, **config_overrides: Any) -> collect.Bundle:
    resolved = make_config(tmp_path, **config_overrides)
    options = collect.CaptureOptions(output_dir=str(tmp_path / "bundle"))
    return collect.capture_bundle(
        make_pve_client(), make_prometheus_client(), resolved, options, now=CAPTURE_NOW
    )


# --------------------------------------------------------------------- estimate


def test_capture_range_seconds_auto_is_the_union_maximum(tmp_path: Path) -> None:
    resolved = make_config(
        tmp_path,
        window={"lookback": "24h"},
        forecast={
            "model": "quantile",
            "seasonal_lookback_days": 7,
            "holt_winters": {"seasonal_periods": 288},
        },
    )
    seconds = collect.capture_range_seconds(resolved.config, None)
    assert seconds == 7 * 86400.0  # seasonal_lookback_days dominates here


def test_capture_range_seconds_override_wins(tmp_path: Path) -> None:
    resolved = make_config(tmp_path)
    assert collect.capture_range_seconds(resolved.config, 3600.0) == 3600.0


def test_estimate_capture_query_count_accounts_for_day_chunking(tmp_path: Path) -> None:
    """X-09: the printed query count used to treat a multi-day range as one
    range query per (group, metric); the collector actually issues one HTTP
    request per day-sized chunk (`_issue_range_chunks`), so the 7 d default
    was really ~7x more range requests than the estimate said."""
    resolved = make_config(tmp_path)
    topology = build_topology(make_pve_client(), resolved.config)
    one_day = 86400.0
    seven_days = 7 * one_day
    estimate_1d = collect.estimate_capture(
        topology, resolved.config, range_seconds=one_day, step_seconds=300.0, no_series=False
    )
    estimate_7d = collect.estimate_capture(
        topology, resolved.config, range_seconds=seven_days, step_seconds=300.0, no_series=False
    )
    # One group, six raw metrics: each extra day of range adds one more
    # chunked range request per metric.
    assert estimate_7d.query_count - estimate_1d.query_count == 6 * 6
    # --no-series never issues a range query at all, chunked or not -- its
    # query count is unaffected by the range.
    estimate_no_series_1d = collect.estimate_capture(
        topology, resolved.config, range_seconds=one_day, step_seconds=300.0, no_series=True
    )
    estimate_no_series_7d = collect.estimate_capture(
        topology, resolved.config, range_seconds=seven_days, step_seconds=300.0, no_series=True
    )
    assert estimate_no_series_1d.query_count == estimate_no_series_7d.query_count


def test_estimate_capture_sample_points_uses_the_safe_step(tmp_path: Path) -> None:
    """Z-05: a live capture stores every range series at
    `safe_range_step_seconds(step_seconds, rate_window_seconds)`, not the
    configured `step_seconds` verbatim, whenever the gigapipe workaround
    triggers -- true at this project's own defaults
    (metrics.step == metrics.rate_window). `estimate_capture()`'s
    `sample_points` (what `--estimate` prints and what
    `support.max_series_points`'s refusal check compares against) must
    reflect the step actually issued and stored, or both understate by
    the workaround factor."""
    from proxmox_storage_drs.metrics import safe_range_step_seconds

    resolved = make_config(tmp_path)  # default metrics.step == metrics.rate_window == 300s
    topology = build_topology(make_pve_client(), resolved.config)
    range_seconds = 86400.0
    estimate = collect.estimate_capture(
        topology, resolved.config, range_seconds=range_seconds, step_seconds=300.0, no_series=False
    )
    safe_step = safe_range_step_seconds(300.0, resolved.config.metrics.rate_window_seconds)
    assert safe_step == 150.0  # sanity: the workaround is actually triggering here
    disk_count = sum(len(g.disks) for g in topology.groups)
    expected_points_per_disk = int(range_seconds / safe_step)
    assert estimate.sample_points == disk_count * 6 * expected_points_per_disk
    # The configured step itself is unaffected -- only the point math changes.
    assert estimate.step_seconds == 300.0


# ----------------------------------------------------------------------- capture


def test_capture_bundle_produces_anonymized_pve_files(tmp_path: Path) -> None:
    bundle = capture(tmp_path)
    assert bundle.ok

    vm_resources = bundle.pve_files["cluster-resources-vm.json"]
    assert len(vm_resources) == 1
    assert vm_resources[0]["vmid"] != 101
    assert "name" not in vm_resources[0]  # free text dropped

    storage_defs = bundle.pve_files["storage-definitions.json"]
    storage_ids = {d["storage"] for d in storage_defs}
    assert "san-a" not in storage_ids and "san-b" not in storage_ids
    assert all(s.startswith("stor-") for s in storage_ids)

    vm_config_files = [k for k in bundle.pve_files if k.startswith("vm-config/")]
    assert len(vm_config_files) == 1
    vm_config = bundle.pve_files[vm_config_files[0]]
    assert "scsi0" in vm_config
    assert vm_config["scsi0"].startswith("stor-")
    assert "san-a" not in vm_config["scsi0"]


def test_capture_bundle_queries_the_real_prometheus_with_real_node_names(
    tmp_path: Path,
) -> None:
    """A live capture against the dev cluster found this one directly
    (section 16.3's "the actual mechanism"): querying the real Prometheus
    with an *anonymized* node selector matches no real series at all --
    real data only comes back for a selector built from the real node
    names. The text this module *writes into the bundle* must still be
    anonymized; the two are deliberately different strings (see
    collect._anonymize_query_text's own docstring)."""
    session = FakePrometheusSession(
        answers={
            "label/__name__/values": METRIC_NAMES,
            "label/vmid/values": ["101"],
            "label/instance/values": ["scsi0"],
            "label/nodename/values": ["node1"],
            "api/v1/query_range": _range_answer,
            "api/v1/query": _instant_answer,
        }
    )
    prom_client = PrometheusClient(
        config_module.PrometheusConfig(url="http://localhost:9090"), session
    )
    resolved = make_config(tmp_path)
    options = collect.CaptureOptions(output_dir=str(tmp_path / "bundle"))
    bundle = collect.capture_bundle(
        make_pve_client(), prom_client, resolved, options, now=CAPTURE_NOW
    )

    # The real HTTP calls this module issued must use the real node name --
    # otherwise a live capture returns nothing for every query.
    sent_queries = [params.get("query", "") for _path, params in session.calls]
    assert any("node1" in q for q in sent_queries if "nodename" in q)

    # What actually reaches the bundle must not.
    for payload in bundle.prometheus_files.values():
        query_text = payload.get("query", "")
        assert "node1" not in query_text


def test_capture_bundle_manifest_call_log_is_anonymized(tmp_path: Path) -> None:
    """A live capture against the dev cluster found this one directly: the
    recording clients build each call's description/detail from the *real*
    call they wrap (real node name, real storage id, real vmid) since the
    call log exists to describe what happened, not to feed replay.py --
    and, unlike every other file in the bundle, nothing was redacting it
    before it reached manifest.json. Section 16.3's governing rule applies
    to this free text exactly as it does to structured fields."""
    bundle = capture(tmp_path)
    manifest_text = json.dumps(bundle.manifest)
    for real in ("node1", "san-a", "san-b"):
        assert real not in manifest_text
    assert not re.search(r"\b101\b", manifest_text)
    descriptions = [c["description"] for c in bundle.manifest["calls"]]
    assert any("node-" in d for d in descriptions)
    assert any("stor-" in d for d in descriptions)


def test_capture_bundle_manifest_scrubs_a_transport_failures_own_hostname(
    tmp_path: Path,
) -> None:
    """X-02: a transport-level failure's own exception text embeds the
    *configured* endpoint (`requests`' own `HTTPSConnectionPool(host=
    '<endpoint>', ...)` framing) -- exactly the identifier section 16.3
    drops `proxmox.host`/`prometheus.url` from config.yaml to avoid, and
    node/storage substitution alone does not catch it (a `.example`/
    `.internal`/`.corp` domain shares no substring with any known node or
    storage name). Reproduced with the same shape a live DNS/connection
    failure actually produces."""
    resolved = make_config(tmp_path)
    options = collect.CaptureOptions(output_dir=str(tmp_path / "bundle"))
    client = make_pve_client(
        error_on="cluster/tasks",
        error_message=(
            "cluster/tasks: request failed: HTTPSConnectionPool("
            "host='pve01.internal.example.invalid', port=8006): "
            "Max retries exceeded with url: /api2/json/cluster/tasks"
        ),
    )
    bundle = collect.capture_bundle(
        client, make_prometheus_client(), resolved, options, now=CAPTURE_NOW
    )
    manifest_text = json.dumps(bundle.manifest)
    assert "pve01.internal.example.invalid" not in manifest_text
    failed = [c for c in bundle.manifest["calls"] if c["outcome"] == "http_error"]
    assert failed
    assert any("host='<redacted>'" in str(c["detail"]) for c in failed)


def test_capture_bundle_config_yaml_drops_credentials(tmp_path: Path) -> None:
    bundle = capture(tmp_path)
    assert "host" not in bundle.config_yaml["proxmox"]
    assert bundle.config_yaml["prometheus"] == {}
    group_names = [g["name"] for g in bundle.config_yaml["groups"]]
    assert group_names == [g for g in group_names if g.startswith("group-")]
    storage_ids = [s["id"] for group in bundle.config_yaml["groups"] for s in group["storages"]]
    assert all(s.startswith("stor-") for s in storage_ids)


def test_capture_bundle_config_yaml_expands_storage_patterns(tmp_path: Path) -> None:
    """A live capture against a real dev cluster (section 16.3's own
    "the actual mechanism") found this the hard way: a `/…/` pattern
    group entry's own text ('/san-.*/') is not a real storage id, so
    matching it against `mapper.known_storages` (real, expanded ids only)
    always missed and silently produced an empty storages list. The bundle
    must carry the *expanded* literal ids build_topology() actually
    resolved, not the raw config entry."""
    bundle = capture(tmp_path, groups=[{"name": "g1", "storages": [{"id": "/san-.*/"}]}])
    assert bundle.ok
    storages = bundle.config_yaml["groups"][0]["storages"]
    assert len(storages) == 2  # san-a, san-b both matched the pattern
    assert all(s["id"].startswith("stor-") for s in storages)


def test_capture_bundle_config_yaml_maps_exclude_disks_vmid(tmp_path: Path) -> None:
    """X-01: `exclude.disks` entries are `"vmid:device"` (section 16.3's own
    per-kind table lists it among the identifiers that must move with the
    mapping) -- a verbatim carry leaks the real vmid into the one file the
    manual tells an operator to read before sending, and silently stops
    matching anything at replay, since replayed disk keys are built from
    pseudonymized vmids (topology.py's `f"{vmid}:{device}"`)."""
    bundle = capture(tmp_path, exclude={"disks": ["101:scsi0", "999:scsi1", "not-a-vmid:scsi2"]})
    assert bundle.ok
    disks = bundle.config_yaml["exclude"]["disks"]
    # 101 was registered (it is the one VM in the fixture topology); 999 was
    # never seen and is dropped, per the "unmapped means dropped" rule.
    assert len(disks) == 1
    new_vmid, _, device = disks[0].partition(":")
    assert device == "scsi0"
    assert new_vmid != "101"  # the real vmid never reaches the bundle
    assert new_vmid.isdigit()


def test_capture_bundle_prometheus_series_vmid_is_remapped(tmp_path: Path) -> None:
    bundle = capture(tmp_path)
    range_files = [v for k, v in bundle.prometheus_files.items() if k.startswith("range/")]
    populated = [f for f in range_files if f["result"]]
    assert populated, "expected at least one non-empty range capture"
    series = populated[0]["result"][0]
    assert series["metric"]["vmid"] != "101"
    assert series["metric"]["instance"] == "scsi0"  # device passes through unchanged


def test_capture_bundle_rejects_a_device_label_value_that_is_not_a_real_device(
    tmp_path: Path,
) -> None:
    """A live capture against the dev cluster found this directly:
    metrics.labels.device is literally "instance" there (verify-metrics'
    own check 4 warning -- it collides with Prometheus's unrelated
    scrape-target label of the same name), and label_values("instance")
    is a *global* Prometheus query, not scoped to the blockstat
    measurement -- it returned a real scrape target ("127.0.0.1:8098")
    alongside genuine device keys. Both label_values() results and a
    series' own "instance" tag must be checked against the enumerated bus
    -key shape (section 3.5) and dropped, not passed through, when they
    are not."""
    session = FakePrometheusSession(
        answers={
            "label/__name__/values": METRIC_NAMES,
            "label/vmid/values": ["101"],
            "label/instance/values": ["scsi0", "127.0.0.1:8098"],
            "label/nodename/values": ["node1"],
            "api/v1/query_range": _range_answer,
            "api/v1/query": _instant_answer,
        }
    )
    prom_client = PrometheusClient(
        config_module.PrometheusConfig(url="http://localhost:9090"), session
    )
    resolved = make_config(tmp_path)
    options = collect.CaptureOptions(output_dir=str(tmp_path / "bundle"))
    bundle = collect.capture_bundle(
        make_pve_client(), prom_client, resolved, options, now=CAPTURE_NOW
    )

    device_label_files = [
        v for k, v in bundle.prometheus_files.items() if k.startswith("label-values/")
    ]
    matches = [f for f in device_label_files if f["label"] == "instance"]
    assert matches
    assert matches[0]["result"] == ["scsi0"]  # the scrape target dropped, not passed through


def test_capture_bundle_metric_names_are_not_validated_as_device_keys(tmp_path: Path) -> None:
    """A regression on the fix above's own first cut: __name__ (metric
    names, from verify_metrics()'s own check 1) is not the configured
    device label and must not be run through the disk-bus-key filter at
    all -- a metric name like "blockstat_rd_operations" does not match it
    and was silently dropped entirely by an earlier version of this fix,
    which made every metric look like it "does not exist" under replay."""
    bundle = capture(tmp_path)
    name_files = [v for v in bundle.prometheus_files.values() if v.get("label") == "__name__"]
    assert name_files
    assert set(name_files[0]["result"]) == set(METRIC_NAMES)


def test_capture_bundle_prometheus_sample_timestamps_are_rebased(tmp_path: Path) -> None:
    """A live capture against the dev cluster found this the hard way: a
    range file's own start/end were rebased, but the individual sample
    timestamps inside "values" were not, so every --replay request's
    (rebased) window and the stored (still-real) points never overlapped
    -- every trim came back empty and every disk read 0% coverage. The
    fake session's canned timestamps (1700000000-ish, "real" by
    construction) must not survive into the bundle unchanged."""
    bundle = capture(tmp_path)
    range_files = [v for k, v in bundle.prometheus_files.items() if k.startswith("range/")]
    populated = [f for f in range_files if f["result"]]
    assert populated
    for payload in populated:
        for series in payload["result"]:
            for ts, _value in series["values"]:
                assert payload["start"] - 1 <= ts <= payload["end"] + 1

    instant_files = [v for k, v in bundle.prometheus_files.items() if k.startswith("instant/")]
    populated_instant = [f for f in instant_files if f["result"]]
    assert populated_instant
    for payload in populated_instant:
        for series in payload["result"]:
            ts, _value = series["value"]
            assert ts != 1700000000  # the fake's own raw canned timestamp


def test_capture_bundle_preserves_the_node_label_when_present(tmp_path: Path) -> None:
    """A live capture against the dev cluster found this one too:
    verify_metrics()'s own bare-metric-name sample-series check queries
    the raw series directly (not wrapped in sum by (vmid, device), which
    is what collapses the node label elsewhere), so it *does* carry a
    real node label -- dropping it unconditionally made a replayed
    verify-metrics report a live cluster's real label as "missing"."""
    bundle = capture(tmp_path)
    matches = [
        f
        for f in bundle.prometheus_files.values()
        if f.get("result")
        and isinstance(f["result"][0], dict)
        and "nodename" in f["result"][0].get("metric", {})
    ]
    assert matches, "expected at least one sample series to carry the node label"
    for f in matches:
        node_value = f["result"][0]["metric"]["nodename"]
        assert node_value != "node1"
        assert node_value.startswith("node-")


def test_capture_bundle_findings_json_does_not_leak_unconfigured_labels(tmp_path: Path) -> None:
    """A live capture found this the hard way: ``_check_sample_series()``'s
    "info" finding dumps a sample series' *entire* raw label dict into free
    text (``f"{name}: sample series labels {sample_labels}"``) for a human
    reading it against their own live cluster. A real Telegraf ``host`` tag
    is not one of the three labels this project's config assigns any
    meaning to (vmid/device/node), so ``_redact_free_text()`` -- which only
    knows how to rewrite those three -- passed it through unredacted into
    ``findings.json``. The structured ``sample_series`` field next to it was
    already correctly filtered to just vmid/device/node; the finding
    message must be too."""

    def instant_answer_with_extra_label(params: dict[str, str]) -> dict[str, Any]:
        query = params["query"]
        if query == "blockstat_rd_operations":
            return {
                "result": [
                    {
                        "metric": {
                            "vmid": "101",
                            "instance": "scsi0",
                            "nodename": "node1",
                            "host": "real-guest-hostname-01",
                        },
                        "value": [CAPTURE_NOW.timestamp(), "1.5"],
                    }
                ]
            }
        return _instant_answer(params)

    session = FakePrometheusSession(
        answers={
            "label/__name__/values": METRIC_NAMES,
            "label/vmid/values": ["101"],
            "label/instance/values": ["scsi0"],
            "label/nodename/values": ["node1"],
            "api/v1/query_range": _range_answer,
            "api/v1/query": instant_answer_with_extra_label,
            "api/v1/status/buildinfo": {"version": "2.45.0"},
        }
    )
    prom_client = PrometheusClient(
        config_module.PrometheusConfig(url="http://localhost:9090"), session
    )
    resolved = make_config(tmp_path)
    options = collect.CaptureOptions(output_dir=str(tmp_path / "bundle"))
    bundle = collect.capture_bundle(
        make_pve_client(), prom_client, resolved, options, now=CAPTURE_NOW
    )

    findings_text = json.dumps(bundle.findings)
    assert "real-guest-hostname-01" not in findings_text

    messages = [f["message"] for f in bundle.findings["verify_metrics"]["findings"]]
    sample_messages = [
        m for m in messages if m.startswith("blockstat_rd_operations: sample series")
    ]
    assert sample_messages
    # vmid/device/node still make it through, anonymized -- just not the
    # unconfigured "host" label.
    assert "instance" in sample_messages[0]
    assert "vmid" in sample_messages[0]


def test_capture_bundle_findings_json_drops_a_foreign_vmids_coverage_warning(
    tmp_path: Path,
) -> None:
    """Z-02: `_check_coverage()`'s per-disk warning embeds a real vmid taken
    straight from whatever the coverage query returns -- not just vmids in a
    managed disk group. A vmid outside every configured group (a deleted VM,
    one on an ungrouped storage, or a same-numbered vmid from another
    cluster sharing the Prometheus) is never registered with the mapper, so
    it must not reach findings.json even though the structured
    `coverage_by_disk` field beside it already drops it."""

    def range_answer_with_foreign_vmid(params: dict[str, str]) -> dict[str, Any]:
        query = params["query"]
        if "blockstat_rd_operations" in query:
            start = float(params["start"])
            # Two points each -- far below window.min_coverage(80%) of the
            # ~289 samples a 24h/300s window expects, for both disks.
            return {
                "result": [
                    {
                        "metric": {"vmid": "101", "instance": "scsi0"},
                        "values": [[start, "1.0"], [start + 300.0, "2.0"]],
                    },
                    {
                        "metric": {"vmid": "777", "instance": "scsi0"},
                        "values": [[start, "1.0"], [start + 300.0, "2.0"]],
                    },
                ]
            }
        return _range_answer(params)

    session = FakePrometheusSession(
        answers={
            "label/__name__/values": METRIC_NAMES,
            "label/vmid/values": ["101"],
            "label/instance/values": ["scsi0"],
            "label/nodename/values": ["node1"],
            "api/v1/query_range": range_answer_with_foreign_vmid,
            "api/v1/query": _instant_answer,
            "api/v1/status/buildinfo": {"version": "2.45.0"},
        }
    )
    prom_client = PrometheusClient(
        config_module.PrometheusConfig(url="http://localhost:9090"), session
    )
    resolved = make_config(tmp_path)
    options = collect.CaptureOptions(output_dir=str(tmp_path / "bundle"))
    bundle = collect.capture_bundle(
        make_pve_client(), prom_client, resolved, options, now=CAPTURE_NOW
    )

    findings_text = json.dumps(bundle.findings)
    assert "777" not in findings_text

    coverage = bundle.findings["verify_metrics"]["coverage_by_disk"]
    assert "777:scsi0" not in coverage
    assert any(k.endswith(":scsi0") for k in coverage)  # 101's own, pseudonymized

    messages = [f["message"] for f in bundle.findings["verify_metrics"]["findings"]]
    coverage_messages = [m for m in messages if "coverage" in m and "min_coverage" in m]
    assert len(coverage_messages) == 1  # 101's warning survives, 777's is dropped
    (mapped_key,) = coverage.keys()
    assert coverage_messages[0].startswith(mapped_key)


def test_capture_bundle_findings_json_drops_a_foreign_vmid_from_cross_metric_finding(
    tmp_path: Path,
) -> None:
    """Z-02: `_check_cross_metric_disk_consistency()`'s warning embeds every
    disk missing from one metric's series set, drawn from whatever
    Prometheus returns -- including a foreign vmid no managed group
    registers. That vmid must not reach findings.json, and if it was the
    *only* disk the warning would have named, the finding itself must be
    dropped rather than emitted empty."""

    def instant_answer_with_foreign_vmid(params: dict[str, str]) -> dict[str, Any]:
        query = params["query"]
        if query == "blockstat_wr_total_time_ns":
            # This one metric is missing vmid 777 -- the asymmetry
            # _check_cross_metric_disk_consistency() exists to catch.
            return {
                "result": [
                    {
                        "metric": {"vmid": "101", "instance": "scsi0", "nodename": "node1"},
                        "value": [CAPTURE_NOW.timestamp(), "1.5"],
                    }
                ]
            }
        if query in METRIC_NAMES:
            return {
                "result": [
                    {
                        "metric": {"vmid": "101", "instance": "scsi0", "nodename": "node1"},
                        "value": [CAPTURE_NOW.timestamp(), "1.5"],
                    },
                    {
                        "metric": {"vmid": "777", "instance": "scsi0", "nodename": "node1"},
                        "value": [CAPTURE_NOW.timestamp(), "1.5"],
                    },
                ]
            }
        return _instant_answer(params)

    session = FakePrometheusSession(
        answers={
            "label/__name__/values": METRIC_NAMES,
            "label/vmid/values": ["101"],
            "label/instance/values": ["scsi0"],
            "label/nodename/values": ["node1"],
            "api/v1/query_range": _range_answer,
            "api/v1/query": instant_answer_with_foreign_vmid,
            "api/v1/status/buildinfo": {"version": "2.45.0"},
        }
    )
    prom_client = PrometheusClient(
        config_module.PrometheusConfig(url="http://localhost:9090"), session
    )
    resolved = make_config(tmp_path)
    options = collect.CaptureOptions(output_dir=str(tmp_path / "bundle"))
    bundle = collect.capture_bundle(
        make_pve_client(), prom_client, resolved, options, now=CAPTURE_NOW
    )

    findings_text = json.dumps(bundle.findings)
    assert "777" not in findings_text

    messages = [f["message"] for f in bundle.findings["verify_metrics"]["findings"]]
    assert not any("no series for" in m and "wr_total_time_ns" in m for m in messages)


def test_capture_bundle_no_series_skips_the_forecasting_range_series(tmp_path: Path) -> None:
    """--no-series must skip the big, per-group superset range captures --
    it does not (and need not) suppress verify_metrics()'s own two smaller,
    fixed-window range probes (observed-spacing, coverage), neither of
    which is chunked and neither of which relates to support.capture_range."""
    resolved = make_config(tmp_path)
    capture_range = collect.capture_range_seconds(resolved.config, None)
    options = collect.CaptureOptions(output_dir=str(tmp_path / "bundle"), no_series=True)
    bundle = collect.capture_bundle(
        make_pve_client(), make_prometheus_client(), resolved, options, now=CAPTURE_NOW
    )
    range_files = [v for k, v in bundle.prometheus_files.items() if k.startswith("range/")]
    assert range_files  # verify_metrics' own probes are still captured
    for f in range_files:
        assert f["end"] - f["start"] < capture_range
    assert bundle.manifest["capture"]["no_series"] is True


def test_capture_bundle_refuses_over_max_series_points(tmp_path: Path) -> None:
    resolved = make_config(tmp_path, support={"max_series_points": 1}, window={"lookback": "24h"})
    options = collect.CaptureOptions(output_dir=str(tmp_path / "bundle"))
    with pytest.raises(BundleError, match="max_series_points"):
        collect.capture_bundle(
            make_pve_client(), make_prometheus_client(), resolved, options, now=CAPTURE_NOW
        )


def test_capture_bundle_records_pve_failure_without_aborting(tmp_path: Path) -> None:
    resolved = make_config(tmp_path)
    options = collect.CaptureOptions(output_dir=str(tmp_path / "bundle"))
    client = make_pve_client(error_on="cluster/tasks")
    bundle = collect.capture_bundle(
        client, make_prometheus_client(), resolved, options, now=CAPTURE_NOW
    )
    assert not bundle.ok
    failed = [c for c in bundle.manifest["calls"] if c["outcome"] == "http_error"]
    assert failed
    assert any("cluster_tasks" in c["description"] for c in failed)


def test_capture_bundle_manifest_never_carries_real_date(tmp_path: Path) -> None:
    bundle = capture(tmp_path)
    manifest_text = json.dumps(bundle.manifest)
    assert "2026" not in manifest_text
    assert "synthetic_now_epoch" in bundle.manifest["capture"]


def test_capture_bundle_manifest_carries_pve_and_prometheus_versions(tmp_path: Path) -> None:
    """X-08: section 16.1's manifest line ("schema, versions, what was
    captured...") and section 16.3's preserved list both promise PVE and
    Prometheus version strings; neither was ever captured."""
    bundle = capture(tmp_path)
    assert bundle.manifest["capture"]["pve_version"] == "8.2.1"
    assert bundle.manifest["capture"]["prometheus_version"] == "2.45.0"


def test_capture_bundle_manifest_version_is_not_mangled_by_vmid_redaction(tmp_path: Path) -> None:
    """Y-06: the manifest's version fields are machine-generated provenance,
    not free text -- routing them through ``_redact_free_text()`` used to
    rewrite any digit run matching a registered vmid, so with vmid 101
    registered a real ``"pve-manager/8.2.101"`` string came out as
    ``"pve-manager/8.2.<pseudonym>"``, a silently wrong value in a field
    whose whole purpose is honest provenance."""
    api = fake_api(
        {
            "cluster/resources": lambda type: (VM_RESOURCES if type == "vm" else STORAGE_RESOURCES),
            "storage": STORAGE_DEFS,
            "nodes": [{"node": "node1"}],
            "cluster/tasks": [],
            "nodes/node1/storage/san-a/status": STORAGE_STATUS["san-a"],
            "nodes/node1/storage/san-b/status": STORAGE_STATUS["san-b"],
            "nodes/node1/storage/san-a/content": CONTENT_SAN_A,
            "nodes/node1/storage/san-b/content": CONTENT_SAN_B,
            "nodes/node1/qemu/101/config": VM_CONFIGS[101],
            "nodes/node1/qemu/101/snapshot": VM_SNAPSHOTS[101],
            "nodes/node1/qemu/101/status/current": {},
            "version": {"version": "pve-manager/8.2.101"},
        }
    )
    client = PveClient(api)
    resolved = make_config(tmp_path)
    options = collect.CaptureOptions(output_dir=str(tmp_path / "bundle"))
    bundle = collect.capture_bundle(
        client, make_prometheus_client(), resolved, options, now=CAPTURE_NOW
    )
    assert bundle.manifest["capture"]["pve_version"] == "pve-manager/8.2.101"


def test_capture_bundle_manifest_flags_an_extra_selector_rewrite(tmp_path: Path) -> None:
    """X-08: section 16.3 promises the manifest "flags" a non-node-shaped
    `metrics.extra_selector` being rewritten to the default tier's own
    equivalent -- the one honesty signal for a bundle whose live queries
    were scoped differently from what it replays."""
    default_bundle = capture(tmp_path)
    assert default_bundle.manifest["capture"]["extra_selector_rewritten"] is False

    custom_bundle = capture(tmp_path / "custom", metrics={"extra_selector": 'cluster="prod"'})
    assert custom_bundle.manifest["capture"]["extra_selector_rewritten"] is True


def test_capture_bundle_extra_selector_never_reaches_a_query_file(tmp_path: Path) -> None:
    """Z-03: `resolve_node_selector()`'s tier-1 precedence used to win on
    *both* sides of `rate_expr_map` whenever `metrics.extra_selector` was
    set, making the "anonymized" side identical to the real one --
    section 16.3's "rewritten, not carried" promise was a no-op, and the
    operator's raw selector text (a real label value on a shared
    Prometheus) reached the bundle's `prometheus/` query files verbatim.
    The anonymized side must always be `build_node_selector()`'s own node
    alternation, bypassing `resolve_node_selector()` entirely."""
    bundle = capture(tmp_path, metrics={"extra_selector": 'cluster="prod"'})
    query_texts = [f["query"] for f in bundle.prometheus_files.values() if "query" in f]
    assert query_texts  # sanity: something was actually captured
    for query in query_texts:
        assert "prod" not in query
        assert "cluster=" not in query


def test_capture_bundle_manifest_version_is_none_on_a_failed_call(tmp_path: Path) -> None:
    resolved = make_config(tmp_path)
    options = collect.CaptureOptions(output_dir=str(tmp_path / "bundle"))
    client = make_pve_client(error_on="version")
    bundle = collect.capture_bundle(
        client, make_prometheus_client(), resolved, options, now=CAPTURE_NOW
    )
    assert bundle.manifest["capture"]["pve_version"] is None


# --------------------------------------------------------------------- writer


def test_write_bundle_dir_is_deterministic(tmp_path: Path) -> None:
    # Same salt for both captures -- otherwise the pseudonyms themselves
    # would differ and nothing else could possibly match either.
    shared_salt = tmp_path / "shared-salt"
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    bundle_a = capture(tmp_path / "a", support={"salt_path": str(shared_salt)})
    bundle_b = capture(tmp_path / "b", support={"salt_path": str(shared_salt)})

    dir_a = tmp_path / "out-a"
    dir_b = tmp_path / "out-b"
    collect.write_bundle_dir(dir_a, bundle_a)
    collect.write_bundle_dir(dir_b, bundle_b)

    files_a = sorted(p.relative_to(dir_a) for p in dir_a.rglob("*") if p.is_file())
    files_b = sorted(p.relative_to(dir_b) for p in dir_b.rglob("*") if p.is_file())
    assert files_a == files_b
    for rel in files_a:
        assert (dir_a / rel).read_bytes() == (dir_b / rel).read_bytes(), rel


def test_write_bundle_dir_writes_sha256sums(tmp_path: Path) -> None:
    bundle = capture(tmp_path)
    out = tmp_path / "out"
    collect.write_bundle_dir(out, bundle)
    assert (out / "manifest.json").is_file()
    assert (out / "config.yaml").is_file()
    assert (out / "findings.json").is_file()
    shasums = (out / "SHA256SUMS").read_text(encoding="utf-8")
    assert "manifest.json" in shasums
    assert "config.yaml" in shasums


def test_write_tarball_produces_a_gzip_file(tmp_path: Path) -> None:
    bundle = capture(tmp_path)
    out = tmp_path / "out"
    collect.write_bundle_dir(out, bundle)
    tar_path = tmp_path / "out.tar.gz"
    collect.write_tarball(out, tar_path)
    assert tar_path.is_file()
    with open(tar_path, "rb") as fh:
        magic = fh.read(2)
    assert magic == b"\x1f\x8b"  # gzip magic bytes


def test_write_tarball_is_deterministic(tmp_path: Path) -> None:
    bundle = capture(tmp_path)
    out = tmp_path / "out"
    collect.write_bundle_dir(out, bundle)
    tar1 = tmp_path / "one.tar.gz"
    tar2 = tmp_path / "two.tar.gz"
    collect.write_tarball(out, tar1)
    collect.write_tarball(out, tar2)
    assert tar1.read_bytes() == tar2.read_bytes()


# ----------------------------------------------------------------- hashing


def test_hash_query_text_is_deterministic() -> None:
    assert collect.hash_query_text("foo") == collect.hash_query_text("foo")
    assert collect.hash_query_text("foo") != collect.hash_query_text("bar")


def test_hash_label_name_is_deterministic() -> None:
    assert collect.hash_label_name("vmid") == collect.hash_label_name("vmid")
    assert collect.hash_label_name("vmid") != collect.hash_label_name("device")


# ------------------------------------------------------- query anonymization


def test_anonymize_query_text_rewrites_a_known_rate_expression() -> None:
    """A live capture against the dev cluster found the previous
    implementation's bug directly: blindly substring-replacing each real
    node name inside already-built selector text preserves the *real*
    -name sort order (build_node_selector() sorted its own real-name
    input), while a --replay run builds the selector fresh from
    pseudonyms and sorts *those* -- a different string whenever a real
    name's lexical rank differs from its pseudonym's. The fix looks up the
    exact real rate expression in a pre-built map instead of touching
    node-name substrings piecemeal."""
    real_expr = 'sum by (vmid, instance) (rate(rd_operations{nodename=~"real-b|real-a"}[300s]))'
    anon_expr = 'sum by (vmid, instance) (rate(rd_operations{nodename=~"node-x|node-y"}[300s]))'
    rate_expr_map = {real_expr: anon_expr}
    mapper = anonymize.Mapper(salt=b"x" * 32, capture_start_epoch=CAPTURE_NOW.timestamp())

    # A bare range query: the whole text is the rate expression.
    assert collect._anonymize_query_text(real_expr, mapper, rate_expr_map) == anon_expr

    # Embedded inside quantile_over_time(...), as the instant queries are.
    wrapped = f"quantile_over_time(0.95, ({real_expr})[86400s:300s])"
    expected = f"quantile_over_time(0.95, ({anon_expr})[86400s:300s])"
    assert collect._anonymize_query_text(wrapped, mapper, rate_expr_map) == expected


def test_anonymize_query_text_is_a_noop_with_no_known_rate_expression() -> None:
    """verify_metrics() never carries a node selector at all -- nothing to
    rewrite, and _anonymize_query_text() must leave a query it does not
    recognize alone rather than guessing."""
    mapper = anonymize.Mapper(salt=b"x" * 32, capture_start_epoch=CAPTURE_NOW.timestamp())
    query = "blockstat_rd_operations"
    assert collect._anonymize_query_text(query, mapper, {}) == query


# ------------------------------------------------------- dropped_records (X-09)


def _mapper(
    nodes: frozenset[str] = frozenset(), storages: frozenset[str] = frozenset()
) -> anonymize.Mapper:
    return anonymize.Mapper(
        salt=b"x" * 32,
        capture_start_epoch=CAPTURE_NOW.timestamp(),
        known_nodes=nodes,
        known_storages=storages,
    )


def test_anonymize_storage_definitions_counts_a_pruned_unknown_node() -> None:
    """X-09: `manifest.json`'s `counts.dropped_records` is documented as
    counting every dropped identifier (section 16.3); an unknown node
    silently pruned from a storage definition's `nodes` list was not."""
    mapper = _mapper(nodes=frozenset({"pve01"}), storages=frozenset({"san-a"}))
    out = collect._anonymize_storage_definitions(
        [{"storage": "san-a", "type": "rbd", "nodes": "pve01,pve-unknown"}], mapper
    )
    assert out[0]["nodes"] == mapper.node("pve01")
    assert mapper.dropped_records == 1


def test_anonymize_storage_resources_counts_an_unknown_node() -> None:
    mapper = _mapper(nodes=frozenset(), storages=frozenset({"san-a"}))
    out = collect._anonymize_storage_resources(
        [{"storage": "san-a", "status": "available", "node": "pve-unknown"}], mapper
    )
    assert out == []
    assert mapper.dropped_records == 1


def test_anonymize_vm_resources_counts_an_unknown_node() -> None:
    mapper = _mapper(nodes=frozenset(), storages=frozenset())
    out = collect._anonymize_vm_resources(
        [{"vmid": 101, "node": "pve-unknown", "status": "running", "type": "qemu"}], mapper
    )
    assert out == []
    assert mapper.dropped_records == 1


def test_anonymize_disk_value_counts_an_unknown_storage() -> None:
    mapper = _mapper(nodes=frozenset(), storages=frozenset())
    assert collect._anonymize_disk_value("san-unknown:vm-101-disk-0,size=10G", mapper) is None
    assert mapper.dropped_records == 1
