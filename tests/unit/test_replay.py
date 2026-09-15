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
from proxmox_storage_drs.config import load_config as _load_config
from proxmox_storage_drs.exceptions import BundleError, PveApiError, RangeStepMismatch
from proxmox_storage_drs.metrics import (
    build_quantile_over_time_promql,
    build_rate_promql,
    compute_disk_coverage,
    parse_disk_range_series,
    parse_disk_series,
    resolve_node_selector,
    safe_range_step_seconds,
)
from proxmox_storage_drs.topology import build_topology
from tests.unit.test_collect import (
    CAPTURE_NOW,
    capture,
    make_config,
    make_prometheus_client,
    make_pve_client,
)


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


def test_replay_prometheus_client_range_query_step_mismatch_is_a_range_step_mismatch(
    tmp_path: Path,
) -> None:
    """A step mismatch is the one BundleError case that carries its own
    recovery: RangeStepMismatch.actual_step_seconds names the step this
    bundle's range capture actually has (manifest.json's capture.step_seconds,
    a --step override never written to config.yaml), which
    metrics.compute_disk_coverage()/loadmodel._fetch_raw_quantity_series()
    retry with instead of failing outright."""
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
    captured_step = safe_range_step_seconds(step, resolved.config.metrics.rate_window_seconds)
    with pytest.raises(RangeStepMismatch) as excinfo:
        client.range_query(rate_expr, end - range_seconds, end, step * 2)
    assert excinfo.value.actual_step_seconds == captured_step
    assert isinstance(excinfo.value, BundleError)


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


def test_replay_prometheus_client_range_query_survives_a_captured_extra_selector(
    tmp_path: Path,
) -> None:
    """Z-03: a bundle captured with `metrics.extra_selector` set must still
    replay. `config.yaml` nulls the selector (section 16.3), so a real
    `--replay` run resolves it back to `build_node_selector()`'s node
    alternation via the bundle's *own* config -- reproducing that path
    exactly (rather than reusing the capture-time `resolved` with
    `extra_selector` still set, which would rebuild the wrong text) is
    the point of this test."""
    bundle_dir = tmp_path / "bundle"
    bundle = capture(
        tmp_path,
        support={"salt_path": str(tmp_path / "salt")},
        metrics={"extra_selector": 'cluster="prod"'},
    )
    collect.write_bundle_dir(bundle_dir, bundle)

    # What a real `--replay` run loads: the bundle's own config.yaml, whose
    # extra_selector is null (cli.py defaults --config to <replay>/config.yaml).
    replayed = _load_config(str(bundle_dir / "config.yaml"), env={}, require_connection=False)
    assert replayed.config.metrics.extra_selector is None

    manifest = replay.load_manifest(bundle_dir)
    end = manifest["capture"]["synthetic_now_epoch"]
    range_seconds = manifest["capture"]["range_seconds"]
    step = _captured_step(replayed, manifest["capture"]["step_seconds"])

    client = replay.ReplayPrometheusClient(PrometheusConfig(url="unused"), bundle_dir)
    rate_expr = _replay_rate_expr(bundle_dir, replayed)
    result = client.range_query(rate_expr, end - range_seconds, end, step)
    parsed = parse_disk_range_series(result, "vmid", "instance")
    assert parsed  # replay succeeded -- no BundleError, and data survived


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


def test_compute_disk_coverage_replays_a_bundle_captured_with_a_step_override(
    tmp_path: Path,
) -> None:
    """The real bug, end to end: ``collect-testdata --step 180`` on a
    cluster whose ``config.metrics.step`` is the 300s default (found on a
    real 4-node production cluster) records its range data at 180s --
    manifest.json's own ``capture.step_seconds``, never written to
    config.yaml. Replaying with that same config.yaml alone used to fail
    outright (neither the 150s safe-step guess nor the plain 300s fallback
    matches what was actually captured); RangeStepMismatch fixes it by
    naming the real step instead of guessing a third time."""
    resolved = make_config(tmp_path, support={"salt_path": str(tmp_path / "salt")})
    assert resolved.config.metrics.step_seconds == 300.0  # the untouched default

    options = collect.CaptureOptions(output_dir=str(tmp_path / "bundle"), step_seconds=180.0)
    bundle = collect.capture_bundle(
        make_pve_client(), make_prometheus_client(), resolved, options, now=CAPTURE_NOW
    )
    assert bundle.ok
    bundle_dir = tmp_path / "bundle"
    collect.write_bundle_dir(bundle_dir, bundle)

    manifest = replay.load_manifest(bundle_dir)
    assert manifest["capture"]["step_seconds"] == 180.0
    safe_guess = safe_range_step_seconds(
        resolved.config.metrics.step_seconds, resolved.config.metrics.rate_window_seconds
    )
    assert safe_guess != 180.0  # confirms this bundle really does trigger the mismatch

    prom_client = replay.ReplayPrometheusClient(PrometheusConfig(url="unused"), bundle_dir)
    end = manifest["capture"]["synthetic_now_epoch"]
    # loadmodel.py's real call (the one plan/show-load actually make) scopes
    # this to the cluster's own nodes -- the *other*, selector-less capture
    # of this same metric (verify_metrics()'s own findings.json driver) is a
    # separate file at a different step and not what this test is after.
    node_names = replay.ReplayPveClient(bundle_dir).node_names()
    node_selector = resolve_node_selector(resolved.config.metrics, node_names)
    rate_expr = build_rate_promql(
        "blockstat_rd_operations",
        resolved.config.metrics.labels.vmid,
        resolved.config.metrics.labels.device,
        resolved.config.metrics.rate_window_seconds,
        selector=node_selector,
    )
    # Requesting the guessed (wrong) step directly proves the mismatch is
    # real and recoverable, not just that some unrelated path swallowed it.
    with pytest.raises(RangeStepMismatch) as excinfo:
        prom_client.range_query(rate_expr, end - 86400.0, end, safe_guess)
    assert excinfo.value.actual_step_seconds == 180.0

    # No BundleError/RangeStepMismatch propagating is the property under
    # test here -- the test fixture's own canned Prometheus answers (see
    # test_collect.py's _range_answer) have no series for read_ops, the
    # metric compute_disk_coverage() queries, so an empty result is the
    # correct outcome, not a sign the retry silently failed.
    coverage = compute_disk_coverage(
        prom_client,
        resolved.config.metrics,
        resolved.config.window,
        selector=node_selector,
        now=end,
    )
    assert coverage == {}
