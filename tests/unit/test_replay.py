# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""replay.py: serving a diagnostic bundle through the pve.py/metrics.py
interfaces with no network access at all. See IMPLEMENTATION_PLAN.md
section 16.5.

Builds real bundles on disk via ``collect.capture_bundle()``/
``write_bundle_dir()`` against the same fakes ``test_collect.py`` uses, then
reads them back through ``replay.py`` -- proving the round trip, not just
each half in isolation.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import requests

from proxmox_storage_drs import collect, replay
from proxmox_storage_drs.config import PrometheusConfig
from proxmox_storage_drs.exceptions import BundleError, PveApiError
from proxmox_storage_drs.metrics import (
    build_quantile_over_time_promql,
    build_rate_promql,
    parse_disk_range_series,
    parse_disk_series,
    resolve_node_selector,
    safe_range_step_seconds,
)
from proxmox_storage_drs.topology import build_topology
from tests.unit.test_collect import capture, make_config


def write_bundle(tmp_path: Path, **config_overrides: object) -> Path:
    bundle = capture(tmp_path, **config_overrides)
    out = tmp_path / "bundle"
    collect.write_bundle_dir(out, bundle)
    return out


# ----------------------------------------------------------------- manifest


def test_load_manifest_missing_directory_is_a_bundle_error(tmp_path: Path) -> None:
    with pytest.raises(BundleError):
        replay.load_manifest(tmp_path / "does-not-exist")


def test_load_manifest_names_the_tarball_still_needs_unpacking(tmp_path: Path) -> None:
    """X-10: `.tar.gz` (write_tarball()'s own transport form, section 16.1)
    is not a form `--replay` accepts directly -- the error should say so
    rather than leaving an operator to guess."""
    tarball = tmp_path / "bundle.tar.gz"
    tarball.touch()
    with pytest.raises(BundleError, match="unpack it first"):
        replay.load_manifest(tarball)


def test_bundle_reference_now_matches_manifest(tmp_path: Path) -> None:
    bundle_dir = write_bundle(tmp_path)
    manifest = replay.load_manifest(bundle_dir)
    now = replay.bundle_reference_now(bundle_dir)
    assert now.timestamp() == pytest.approx(manifest["capture"]["synthetic_now_epoch"])


def test_bundle_reference_now_is_stable_across_calls(tmp_path: Path) -> None:
    bundle_dir = write_bundle(tmp_path)
    assert replay.bundle_reference_now(bundle_dir) == replay.bundle_reference_now(bundle_dir)


# --------------------------------------------------------------- ReplayPveClient


def test_replay_pve_client_serves_topology(tmp_path: Path) -> None:
    """The point of --replay: build_topology() runs unchanged against
    ReplayPveClient plus the bundle's own (anonymized) config.yaml."""
    bundle_dir = write_bundle(tmp_path)
    client = replay.ReplayPveClient(bundle_dir)
    bundle_config = _config_from_bundle(bundle_dir)

    topology = build_topology(client, bundle_config)
    assert len(topology.groups) == 1
    assert len(topology.groups[0].disks) == 1
    assert topology.groups[0].disks[0].vmid != 101  # anonymized, not the original


def _config_from_bundle(bundle_dir: Path):  # type: ignore[no-untyped-def]
    from proxmox_storage_drs.config import load_config

    return load_config(str(bundle_dir / "config.yaml"), env={}, require_connection=False).config


def test_replay_pve_client_vm_config_ignores_node_argument(tmp_path: Path) -> None:
    bundle_dir = write_bundle(tmp_path)
    client = replay.ReplayPveClient(bundle_dir)
    vmids = [int(p.stem) for p in (bundle_dir / "pve" / "vm-config").glob("*.json")]
    assert len(vmids) == 1
    vmid = vmids[0]
    assert client.vm_config("any-node-name", vmid) == client.vm_config("node1", vmid)


def test_replay_pve_client_node_names(tmp_path: Path) -> None:
    bundle_dir = write_bundle(tmp_path)
    client = replay.ReplayPveClient(bundle_dir)
    names = client.node_names()
    assert names  # at least the one node in the fixture
    assert all(n.startswith("node-") for n in names)


def test_replay_pve_client_missing_file_is_a_loud_bundle_error(tmp_path: Path) -> None:
    bundle_dir = write_bundle(tmp_path)
    client = replay.ReplayPveClient(bundle_dir)
    with pytest.raises(BundleError, match="config for VM 999999"):
        client.vm_config("node1", 999999)


def test_replay_pve_client_move_disk_and_task_status_refuse(tmp_path: Path) -> None:
    bundle_dir = write_bundle(tmp_path)
    client = replay.ReplayPveClient(bundle_dir)
    with pytest.raises(PveApiError):
        client.move_disk("node1", 101, "scsi0", "san-a")
    with pytest.raises(PveApiError):
        client.task_status("node1", "UPID:...")


def test_replay_pve_client_never_constructs_requests_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle_dir = write_bundle(tmp_path)

    def boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("ReplayPveClient must never touch requests.Session")

    monkeypatch.setattr(requests, "Session", boom)
    client = replay.ReplayPveClient(bundle_dir)
    client.vm_resources()  # exercises the replay path; must not raise


# ----------------------------------------------------------- ReplayPrometheusClient


def test_replay_prometheus_client_never_constructs_requests_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle_dir = write_bundle(tmp_path)

    def boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("ReplayPrometheusClient must never touch requests.Session")

    monkeypatch.setattr(requests, "Session", boom)
    client = replay.ReplayPrometheusClient(PrometheusConfig(url="unused"), bundle_dir)
    client.label_values("__name__")  # exercises the replay path; must not raise


def test_replay_prometheus_client_instant_query_key_miss(tmp_path: Path) -> None:
    bundle_dir = write_bundle(tmp_path)
    client = replay.ReplayPrometheusClient(PrometheusConfig(url="unused"), bundle_dir)
    with pytest.raises(BundleError, match="no recorded response"):
        client.instant_query("this_query_was_never_captured")


def test_replay_prometheus_client_label_values_round_trips(tmp_path: Path) -> None:
    bundle_dir = write_bundle(tmp_path)
    client = replay.ReplayPrometheusClient(PrometheusConfig(url="unused"), bundle_dir)
    values = client.label_values("vmid")
    assert values  # the one captured, anonymized vmid
    assert all(v.isdigit() for v in values)
    assert "101" not in values


def _replay_rate_expr(bundle_dir: Path, resolved) -> str:  # type: ignore[no-untyped-def]
    """Reconstructs section 3.4's rate expression exactly as a real
    ``--replay`` command would: the node selector comes from
    ``ReplayPveClient.node_names()`` (the bundle's own, anonymized node
    list), not from a hardcoded/unscoped selector -- matching what was
    actually captured is the whole point of this helper."""
    node_names = replay.ReplayPveClient(bundle_dir).node_names()
    selector = resolve_node_selector(resolved.config.metrics, node_names)
    return build_rate_promql(
        "blockstat_rd_total_time_ns",
        resolved.config.metrics.labels.vmid,
        resolved.config.metrics.labels.device,
        resolved.config.metrics.rate_window_seconds,
        selector,
    )


def _captured_step(resolved, step_seconds: float) -> float:  # type: ignore[no-untyped-def]
    """The step a range/subquery capture is actually stored at --
    ``make_config()``'s default ``metrics.step``/``metrics.rate_window``
    (300s/300s) sit exactly on ``safe_range_step_seconds()``'s failing
    boundary, so ``collect.py`` now captures (and a live/replay run now
    requests) the *safe*, decimatable step, not ``step_seconds`` verbatim
    -- see that function in metrics.py and its callers' own docstrings."""
    return safe_range_step_seconds(step_seconds, resolved.config.metrics.rate_window_seconds)


def test_replay_prometheus_client_range_query_trims_to_the_requested_window(
    tmp_path: Path,
) -> None:
    resolved = make_config(tmp_path, support={"salt_path": str(tmp_path / "salt")})
    bundle_dir = tmp_path / "bundle"
    bundle = capture(tmp_path, support={"salt_path": str(tmp_path / "salt")})
    collect.write_bundle_dir(bundle_dir, bundle)

    manifest = replay.load_manifest(bundle_dir)
    end = manifest["capture"]["synthetic_now_epoch"]
    range_seconds = manifest["capture"]["range_seconds"]
    step = _captured_step(resolved, manifest["capture"]["step_seconds"])

    # A narrower window than the full capture -- e.g. a forecaster whose
    # required_range() is smaller than the capture superset.
    narrow_start = end - range_seconds / 2

    client = replay.ReplayPrometheusClient(PrometheusConfig(url="unused"), bundle_dir)
    rate_expr = _replay_rate_expr(bundle_dir, resolved)
    result = client.range_query(rate_expr, narrow_start, end, step)
    assert result
    for series in result:
        for ts, _value in series.get("values", []):
            assert narrow_start - 1 <= ts <= end + 1


def test_replay_prometheus_client_range_query_step_mismatch_is_a_bundle_error(
    tmp_path: Path,
) -> None:
    resolved = make_config(tmp_path, support={"salt_path": str(tmp_path / "salt")})
    bundle_dir = tmp_path / "bundle"
    bundle = capture(tmp_path, support={"salt_path": str(tmp_path / "salt")})
    collect.write_bundle_dir(bundle_dir, bundle)
    manifest = replay.load_manifest(bundle_dir)
    end = manifest["capture"]["synthetic_now_epoch"]
    range_seconds = manifest["capture"]["range_seconds"]
    step = manifest["capture"]["step_seconds"]

    client = replay.ReplayPrometheusClient(PrometheusConfig(url="unused"), bundle_dir)
    rate_expr = _replay_rate_expr(bundle_dir, resolved)
    with pytest.raises(BundleError, match="different metrics.step"):
        client.range_query(rate_expr, end - range_seconds, end, step * 2)


def test_replay_prometheus_client_range_query_out_of_bounds_is_a_bundle_error(
    tmp_path: Path,
) -> None:
    resolved = make_config(tmp_path, support={"salt_path": str(tmp_path / "salt")})
    bundle_dir = tmp_path / "bundle"
    bundle = capture(tmp_path, support={"salt_path": str(tmp_path / "salt")})
    collect.write_bundle_dir(bundle_dir, bundle)
    manifest = replay.load_manifest(bundle_dir)
    end = manifest["capture"]["synthetic_now_epoch"]
    range_seconds = manifest["capture"]["range_seconds"]
    step = _captured_step(resolved, manifest["capture"]["step_seconds"])

    client = replay.ReplayPrometheusClient(PrometheusConfig(url="unused"), bundle_dir)
    rate_expr = _replay_rate_expr(bundle_dir, resolved)
    with pytest.raises(BundleError, match="no recorded response"):
        client.range_query(rate_expr, end - 10 * range_seconds, end, step)


def test_replay_prometheus_client_instant_quantile_query_round_trips(tmp_path: Path) -> None:
    resolved = make_config(tmp_path, support={"salt_path": str(tmp_path / "salt")})
    bundle_dir = tmp_path / "bundle"
    bundle = capture(tmp_path, support={"salt_path": str(tmp_path / "salt")})
    collect.write_bundle_dir(bundle_dir, bundle)

    client = replay.ReplayPrometheusClient(PrometheusConfig(url="unused"), bundle_dir)
    rate_expr = _replay_rate_expr(bundle_dir, resolved)
    promql = build_quantile_over_time_promql(
        rate_expr,
        resolved.config.window.quantile,
        resolved.config.window.lookback_seconds,
        _captured_step(resolved, resolved.config.metrics.step_seconds),
    )
    result = client.instant_query(promql)
    parsed = parse_disk_series(result, "vmid", "instance")
    assert parsed  # the one captured disk survived the round trip


def test_parse_disk_range_series_still_works_on_replayed_data(tmp_path: Path) -> None:
    """A light end-to-end sanity check: replayed range data is still valid
    input to the same parsing loadmodel.py itself uses."""
    resolved = make_config(tmp_path, support={"salt_path": str(tmp_path / "salt")})
    bundle_dir = tmp_path / "bundle"
    bundle = capture(tmp_path, support={"salt_path": str(tmp_path / "salt")})
    collect.write_bundle_dir(bundle_dir, bundle)

    manifest = replay.load_manifest(bundle_dir)
    end = manifest["capture"]["synthetic_now_epoch"]
    range_seconds = manifest["capture"]["range_seconds"]
    step = _captured_step(resolved, manifest["capture"]["step_seconds"])

    client = replay.ReplayPrometheusClient(PrometheusConfig(url="unused"), bundle_dir)
    rate_expr = _replay_rate_expr(bundle_dir, resolved)
    result = client.range_query(rate_expr, end - range_seconds, end, step)
    parsed = parse_disk_range_series(result, "vmid", "instance")
    assert parsed
