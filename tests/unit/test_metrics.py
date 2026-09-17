# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Prometheus client, PromQL builders and verify-metrics.

No test here talks to a real Prometheus (.agents/testing.md): PrometheusClient
is exercised through a fake session with the same get(url, params=...) shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

import pytest

from proxmox_storage_drs.config import MetricLabels, MetricsConfig, PrometheusConfig, WindowConfig
from proxmox_storage_drs.exceptions import BundleError, MetricsError, RangeStepMismatch
from proxmox_storage_drs.metrics import (
    DiskKey,
    PrometheusClient,
    build_node_selector,
    build_quantile_over_time_promql,
    build_rate_promql,
    compute_disk_coverage,
    decimate_to_configured_step,
    parse_disk_range_series,
    parse_disk_series,
    raw_metric_name,
    resolve_node_selector,
    safe_range_step_seconds,
    verify_metrics,
)


@dataclass
class FakeResponse:
    status_code: int = 200
    _payload: dict[str, Any] = field(default_factory=dict)
    text: str = ""

    def json(self) -> dict[str, Any]:
        return self._payload


@dataclass
class FakeSession:
    """Records calls and answers from a queue keyed by path."""

    answers: dict[str, Any]
    calls: list[tuple[str, dict[str, str]]] = field(default_factory=list)

    def get(
        self,
        url: str,
        params: dict[str, str],
        timeout: float,
        auth: object,
        headers: dict[str, str],
    ) -> Any:
        del timeout, auth, headers
        for path, answer in self.answers.items():
            if url.endswith(path):
                self.calls.append((path, params))
                if isinstance(answer, Exception):
                    raise answer
                return answer
        raise AssertionError(f"unexpected request to {url}")


def success(data: Any) -> FakeResponse:
    return FakeResponse(200, {"status": "success", "data": data})


PROM_CONFIG = PrometheusConfig(url="http://prom.example.com:9090")


# --------------------------------------------------------------------- PromQL


def test_build_rate_promql() -> None:
    expr = build_rate_promql("blockstat_rd_operations", "vmid", "instance", 300)
    assert expr == "sum by (vmid, instance) (rate(blockstat_rd_operations[300s]))"


def test_build_rate_promql_with_a_selector_scopes_the_metric_itself() -> None:
    """Section 3.4: the selector goes *inside* `rate()`'s own vector
    selector, before `sum by` ever collapses the labels it names --
    verified by exact string, since a matcher outside the wrong pair of
    parens would silently apply to nothing."""
    expr = build_rate_promql(
        "blockstat_rd_operations", "vmid", "instance", 300, selector='nodename=~"pve01|pve02"'
    )
    assert expr == (
        'sum by (vmid, instance) (rate(blockstat_rd_operations{nodename=~"pve01|pve02"}[300s]))'
    )


def test_build_rate_promql_selector_none_is_unchanged_from_before() -> None:
    assert build_rate_promql(
        "blockstat_rd_operations", "vmid", "instance", 300, selector=None
    ) == build_rate_promql("blockstat_rd_operations", "vmid", "instance", 300)


def test_build_node_selector_escapes_dots_in_an_fqdn() -> None:
    """A node named `pve1.example.com` must match only that exact string
    in RE2 -- an unescaped `.` would match any character there, so
    e.g. `pve1xexample.com` would wrongly match too."""
    selector = build_node_selector("nodename", ["pve1.example.com"])
    assert selector == r'nodename=~"pve1\.example\.com"'


def test_build_node_selector_sorts_and_dedupes() -> None:
    selector = build_node_selector("nodename", ["pve02", "pve01", "pve02"])
    assert selector == 'nodename=~"pve01|pve02"'


def test_build_node_selector_empty_list_is_none() -> None:
    assert build_node_selector("nodename", []) is None


def test_resolve_node_selector_prefers_the_operator_override() -> None:
    """`metrics.extra_selector` wins outright, even over a real node list --
    the operator's own tagging scheme, not necessarily node names at all."""
    metrics = MetricsConfig(extra_selector='cluster="mycluster"')
    assert resolve_node_selector(metrics, ["pve01", "pve02"]) == 'cluster="mycluster"'
    assert resolve_node_selector(metrics, []) == 'cluster="mycluster"'
    assert resolve_node_selector(metrics, None) == 'cluster="mycluster"'


def test_resolve_node_selector_auto_derives_without_an_override() -> None:
    metrics = MetricsConfig()
    assert resolve_node_selector(metrics, ["pve01", "pve02"]) == 'nodename=~"pve01|pve02"'


def test_resolve_node_selector_is_none_with_neither_override_nor_node_names() -> None:
    """The ``verify-metrics`` case: no ``extra_selector`` configured, and
    ``node_names=None`` since that command never talks to the PVE API."""
    assert resolve_node_selector(MetricsConfig(), None) is None
    assert resolve_node_selector(MetricsConfig(), []) is None


def test_build_quantile_over_time_promql() -> None:
    expr = build_quantile_over_time_promql("sum(x)", 0.95, 86400, 300)
    assert expr == "quantile_over_time(0.95, (sum(x))[86400s:300s])"


def test_build_quantile_over_time_promql_large_lookback_is_not_scientific_notation() -> None:
    """A 14-day lookback is 1209600s -- ``f"{1209600:g}s"`` renders as
    ``"1.2096e+06s"``, which Prometheus's duration parser rejects outright
    (``unknown unit "." in duration``). Confirmed live against a real
    backend."""
    expr = build_quantile_over_time_promql("sum(x)", 0.95, 1_209_600, 300)
    assert "e+" not in expr
    assert expr == "quantile_over_time(0.95, (sum(x))[1209600s:300s])"


def test_build_rate_promql_large_window_is_not_scientific_notation() -> None:
    expr = build_rate_promql("blockstat_rd_operations", "vmid", "instance", 1_209_600)
    assert "e+" not in expr
    assert expr == "sum by (vmid, instance) (rate(blockstat_rd_operations[1209600s]))"


# ------------------------------------------------------- gigapipe step/range


def test_safe_range_step_seconds_is_a_no_op_below_the_rate_window() -> None:
    """The common, correctly-behaving-backend case: nothing to work around."""
    assert safe_range_step_seconds(299.0, 300.0) == 299.0
    assert safe_range_step_seconds(60.0, 300.0) == 60.0


def test_safe_range_step_seconds_shrinks_when_equal_to_the_rate_window() -> None:
    """This project's own default (metrics.step == metrics.rate_window ==
    300s) sits exactly on the failing boundary a live gigapipe deployment
    was confirmed to have (query_range/subquery step >= the range-vector
    duration returns zero series) -- the result must be strictly smaller
    than 300, and must evenly divide it (so decimate_to_configured_step()
    can recover the original grid losslessly)."""
    step = safe_range_step_seconds(300.0, 300.0)
    assert step < 300.0
    assert 300.0 % step == pytest.approx(0.0)


def test_safe_range_step_seconds_shrinks_when_step_is_far_above_the_rate_window() -> None:
    """A real observed shape (a 7-day-capture config's metrics.step: 1h
    against the default rate_window: 300s): 3600/13 = 276.923...,
    confirmed live to be rejected outright by gigapipe's own duration
    parser ("cannot parse \"276.923s\" to a valid duration") -- so unlike
    the 300/300 case above, this cannot be an exact divisor and must still
    come out as a whole number of seconds."""
    step = safe_range_step_seconds(3600.0, 300.0)
    assert step < 300.0
    assert step == int(step)
    assert step == 276.0


def test_decimate_to_configured_step_is_a_no_op_when_steps_match() -> None:
    points = [(0.0, 1.0), (300.0, 2.0)]
    assert decimate_to_configured_step(points, 300.0, 300.0) == points


def test_decimate_to_configured_step_keeps_every_nth_point() -> None:
    """safe_range_step_seconds(300, 300) == 150 -- a series captured at
    that finer grid should decimate back to exactly the 300s-spaced one a
    correctly-behaving backend would have returned directly."""
    dense = [(0.0, "a"), (150.0, "b"), (300.0, "c"), (450.0, "d"), (600.0, "e")]
    assert decimate_to_configured_step(dense, 300.0, 150.0) == [
        (0.0, "a"),
        (300.0, "c"),
        (600.0, "e"),
    ]


def test_raw_metric_name() -> None:
    metrics = MetricsConfig(read_ops="custom_read_ops")
    assert raw_metric_name(metrics, "read_ops") == "custom_read_ops"


# --------------------------------------------------------------------- parsing


def test_parse_disk_series_happy_path() -> None:
    result = [
        {"metric": {"vmid": "101", "instance": "scsi0"}, "value": [123.0, "3.5"]},
        {"metric": {"vmid": "102", "instance": "scsi1"}, "value": [123.0, "1.0"]},
    ]
    parsed = parse_disk_series(result, "vmid", "instance")
    assert parsed == {
        DiskKey(101, "scsi0"): 3.5,
        DiskKey(102, "scsi1"): 1.0,
    }


def test_parse_disk_series_skips_series_missing_labels() -> None:
    result = [
        {"metric": {"vmid": "101"}, "value": [1.0, "1"]},  # no device label
        {"metric": {"instance": "scsi0"}, "value": [1.0, "1"]},  # no vmid label
        {"metric": {"vmid": "not-a-number", "instance": "scsi0"}, "value": [1.0, "1"]},
    ]
    assert parse_disk_series(result, "vmid", "instance") == {}


def test_parse_disk_range_series_happy_path() -> None:
    result = [
        {
            "metric": {"vmid": "101", "instance": "scsi0"},
            "values": [[100.0, "1.0"], [200.0, "2.5"]],
        },
        {"metric": {"vmid": "102", "instance": "scsi1"}, "values": [[100.0, "0.0"]]},
    ]
    parsed = parse_disk_range_series(result, "vmid", "instance")
    assert parsed == {
        DiskKey(101, "scsi0"): ((100.0, 1.0), (200.0, 2.5)),
        DiskKey(102, "scsi1"): ((100.0, 0.0),),
    }


def test_parse_disk_range_series_skips_series_missing_labels() -> None:
    result = [
        {"metric": {"vmid": "101"}, "values": [[1.0, "1"]]},  # no device label
        {"metric": {"instance": "scsi0"}, "values": [[1.0, "1"]]},  # no vmid label
        {"metric": {"vmid": "not-a-number", "instance": "scsi0"}, "values": [[1.0, "1"]]},
    ]
    assert parse_disk_range_series(result, "vmid", "instance") == {}


def test_parse_disk_range_series_defaults_missing_values_to_empty() -> None:
    result = [{"metric": {"vmid": "101", "instance": "scsi0"}}]  # no "values" key at all
    assert parse_disk_range_series(result, "vmid", "instance") == {DiskKey(101, "scsi0"): ()}


# --------------------------------------------------------------------- client


def test_instant_query_returns_result_list() -> None:
    session = FakeSession(
        {"/api/v1/query": success({"result": [{"metric": {}, "value": [1, "2"]}]})}
    )
    client = PrometheusClient(PROM_CONFIG, session=session)
    result = client.instant_query("up")
    assert result == [{"metric": {}, "value": [1, "2"]}]
    assert session.calls[0][1]["query"] == "up"


def test_range_query_passes_start_end_step() -> None:
    session = FakeSession({"/api/v1/query_range": success({"result": []})})
    client = PrometheusClient(PROM_CONFIG, session=session)
    client.range_query("up", -3600.0, 0.0, 300.0)
    _, params = session.calls[0]
    assert params["start"] == "-3600.000"
    assert params["end"] == "0.000"
    assert params["step"] == "300s"


def test_label_values_returns_bare_list() -> None:
    session = FakeSession({"/api/v1/label/__name__/values": success(["a", "b"])})
    client = PrometheusClient(PROM_CONFIG, session=session)
    assert client.label_values("__name__") == ["a", "b"]


def test_buildinfo_returns_the_version_string() -> None:
    session = FakeSession(
        {"/api/v1/status/buildinfo": success({"version": "2.45.0", "revision": "abc123"})}
    )
    client = PrometheusClient(PROM_CONFIG, session=session)
    assert client.buildinfo() == "2.45.0"


def test_buildinfo_missing_key_is_none() -> None:
    session = FakeSession({"/api/v1/status/buildinfo": success({"revision": "abc123"})})
    client = PrometheusClient(PROM_CONFIG, session=session)
    assert client.buildinfo() is None


def test_non_200_status_raises_metrics_error() -> None:
    session = FakeSession({"/api/v1/query": FakeResponse(500, {}, "boom")})
    client = PrometheusClient(PROM_CONFIG, session=session)
    with pytest.raises(MetricsError, match="500"):
        client.instant_query("up")


def test_unsuccessful_status_field_raises_metrics_error() -> None:
    session = FakeSession(
        {"/api/v1/query": FakeResponse(200, {"status": "error", "error": "bad query"})}
    )
    client = PrometheusClient(PROM_CONFIG, session=session)
    with pytest.raises(MetricsError, match="bad query"):
        client.instant_query("up")


def test_non_json_response_raises_metrics_error() -> None:
    @dataclass
    class BadJsonResponse:
        status_code: int = 200

        def json(self) -> Any:
            raise ValueError("not json")

    session = FakeSession({"/api/v1/query": BadJsonResponse()})
    client = PrometheusClient(PROM_CONFIG, session=session)
    with pytest.raises(MetricsError, match="not JSON"):
        client.instant_query("up")


def test_request_exception_is_wrapped() -> None:
    import requests

    session = FakeSession({"/api/v1/query": requests.ConnectionError("refused")})
    client = PrometheusClient(PROM_CONFIG, session=session)
    with pytest.raises(MetricsError, match="failed"):
        client.instant_query("up")


def test_auth_uses_username_password_when_both_set() -> None:
    config = PrometheusConfig(url="http://x", username="u", password="p")
    client = PrometheusClient(config, session=FakeSession({}))
    assert client._auth() == ("u", "p")


def test_auth_is_none_without_credentials() -> None:
    client = PrometheusClient(PROM_CONFIG, session=FakeSession({}))
    assert client._auth() is None


def test_bearer_token_header() -> None:
    config = PrometheusConfig(url="http://x", bearer_token="tok")
    client = PrometheusClient(config, session=FakeSession({}))
    assert client._headers() == {"Authorization": "Bearer tok"}


def test_no_headers_without_bearer_token() -> None:
    client = PrometheusClient(PROM_CONFIG, session=FakeSession({}))
    assert client._headers() == {}


# ------------------------------------------------------------ compute_disk_coverage


class _StepAwareFakeClient(PrometheusClient):
    """A minimal, in-process stand-in for a live cluster's Prometheus
    endpoint, for exercising compute_disk_coverage()'s
    safe_range_step_seconds()/RangeStepMismatch-fallback logic directly,
    without a real bundle on disk (unlike test_replay.py's real
    ReplayPrometheusClient round trips). ``range_query`` is overridden
    entirely -- ``_session``/``_get`` are never reached -- so this
    subclasses PrometheusClient (rather than merely duck-typing it) purely
    to satisfy ``compute_disk_coverage``'s own ``client: PrometheusClient``
    annotation.

    ``found=True`` (the default) mirrors the real ``ReplayPrometheusClient``:
    the query text is always in the bundle, so a step other than
    ``working_step`` raises :class:`RangeStepMismatch` carrying it, never a
    plain, unrecoverable :class:`BundleError` -- a bundle's own captured
    step is always discoverable once its query text matches something.
    ``found=False`` simulates the one case that stays genuinely
    unrecoverable: no capture for this query text at all."""

    def __init__(
        self, working_step: float, result: list[dict[str, Any]], *, found: bool = True
    ) -> None:
        super().__init__(PROM_CONFIG)
        self._working_step = working_step
        self._result = result
        self._found = found
        self.requested_steps: list[float] = []

    def range_query(
        self, promql: str, start_epoch_seconds: float, end_epoch_seconds: float, step_seconds: float
    ) -> list[dict[str, Any]]:
        del promql, start_epoch_seconds, end_epoch_seconds
        self.requested_steps.append(step_seconds)
        if step_seconds != self._working_step:
            if not self._found:
                raise BundleError("simulated --replay bundle: no recorded response for this query")
            raise RangeStepMismatch(
                "simulated --replay bundle: recorded at a different step",
                actual_step_seconds=self._working_step,
            )
        return self._result


def test_compute_disk_coverage_applies_the_safe_step_and_decimates_back() -> None:
    """metrics.step == metrics.rate_window == 300s is this project's own
    default, and sits exactly on a live-confirmed gigapipe failing
    boundary (query_range on a rate()-based expression returns zero series
    whenever step >= the range-vector duration). The coverage query must
    go out at the smaller, divisor-of-300 safe step, and the returned
    (denser) series decimated back down to the configured grid before
    counting samples -- 3 raw points at the 150s grid decimate to 2 at the
    300s one, matching expected_samples exactly (not capped at some
    inflated ratio)."""
    metrics = MetricsConfig(rate_window_seconds=300.0, step_seconds=300.0, labels=MetricLabels())
    window = WindowConfig(
        lookback_seconds=300.0, quantile=0.95, upper_quantile=0.99, min_coverage=0.8
    )
    dense_series = [
        {
            "metric": {"vmid": "101", "instance": "scsi0"},
            "values": [[0, "0"], [150, "0"], [300, "0"]],
        }
    ]
    client = _StepAwareFakeClient(working_step=150.0, result=dense_series)

    coverage = compute_disk_coverage(client, metrics, window, now=300.0)

    assert client.requested_steps == [150.0]  # the safe step succeeded on the first try
    assert coverage[DiskKey(vmid=101, device="scsi0")] == 1.0


def test_compute_disk_coverage_decimation_does_not_inflate_a_real_gap() -> None:
    """The correctness property decimation exists for: real coverage is
    only 2/3 of the configured 300s grid over this 600s window (data
    exists for [0,300] only, nothing after), but counting raw points at
    the finer 150s grid *without* decimating back down would read as an
    inflated, wrong fraction relative to expected_samples (computed from
    the configured step, not the safe one)."""
    metrics = MetricsConfig(rate_window_seconds=300.0, step_seconds=300.0, labels=MetricLabels())
    window = WindowConfig(
        lookback_seconds=600.0, quantile=0.95, upper_quantile=0.99, min_coverage=0.8
    )
    partial_series = [
        {
            "metric": {"vmid": "101", "instance": "scsi0"},
            "values": [[0, "0"], [150, "0"], [300, "0"]],
        }
    ]
    client = _StepAwareFakeClient(working_step=150.0, result=partial_series)

    coverage = compute_disk_coverage(client, metrics, window, now=600.0)

    assert coverage[DiskKey(vmid=101, device="scsi0")] == pytest.approx(2 / 3)


def test_compute_disk_coverage_retries_at_the_bundles_actual_captured_step() -> None:
    """``--replay`` backward/override compatibility: a bundle captured
    before ``safe_range_step_seconds()`` existed, or with
    ``collect-testdata --step`` overriding ``config.metrics.step`` for
    that one run, has its range data at some step this run's own guess
    does not match. ``RangeStepMismatch`` names that step, so
    ``compute_disk_coverage()`` retries with exactly it -- one retry,
    never a second guess -- rather than propagate the error."""
    metrics = MetricsConfig(rate_window_seconds=300.0, step_seconds=300.0, labels=MetricLabels())
    window = WindowConfig(
        lookback_seconds=300.0, quantile=0.95, upper_quantile=0.99, min_coverage=0.8
    )
    real_series = [
        {"metric": {"vmid": "101", "instance": "scsi0"}, "values": [[0, "0"], [300, "0"]]}
    ]
    client = _StepAwareFakeClient(working_step=300.0, result=real_series)

    coverage = compute_disk_coverage(client, metrics, window, now=300.0)

    assert client.requested_steps == [150.0, 300.0]  # safe step tried first, then the real one
    assert coverage[DiskKey(vmid=101, device="scsi0")] == 1.0


def test_compute_disk_coverage_reraises_bundle_error_when_the_query_was_never_captured() -> None:
    """A step mismatch is always recoverable (RangeStepMismatch names the
    real step) -- the one case that must still fail loudly is no capture
    for this query at all, the same "no recorded response" a genuinely
    wrong or corrupted bundle raises."""
    metrics = MetricsConfig(rate_window_seconds=600.0, step_seconds=300.0, labels=MetricLabels())
    window = WindowConfig(
        lookback_seconds=300.0, quantile=0.95, upper_quantile=0.99, min_coverage=0.8
    )
    client = _StepAwareFakeClient(working_step=999.0, result=[], found=False)

    with pytest.raises(BundleError):
        compute_disk_coverage(client, metrics, window, now=300.0)


# --------------------------------------------------------------- verify_metrics


def _full_metrics_config() -> MetricsConfig:
    return MetricsConfig(
        labels=MetricLabels(vmid="vmid", device="instance", node="nodename"),
        rate_window_seconds=300,
        step_seconds=300,
        pvestatd_push_interval_seconds=60,
    )


def _all_metric_names(metrics: MetricsConfig) -> list[str]:
    return [
        metrics.read_ops,
        metrics.write_ops,
        metrics.read_bytes,
        metrics.write_bytes,
        metrics.read_time_ns,
        metrics.write_time_ns,
    ]


def test_verify_metrics_all_green() -> None:
    metrics = _full_metrics_config()
    window = WindowConfig(lookback_seconds=600, min_coverage=0.5)
    names = _all_metric_names(metrics)
    sample = {"vmid": "101", "instance": "scsi0", "nodename": "pve01"}

    # instant_query and range_query both hit /api/v1/query(_range); route by
    # query string content instead of path, since all six metrics share a path.
    class RoutingSession(FakeSession):
        def get(self, url, params, timeout, auth, headers):  # type: ignore[no-untyped-def]
            del timeout, auth, headers
            if url.endswith("/api/v1/label/__name__/values"):
                return success(names)
            if url.endswith("/api/v1/query"):
                return success({"result": [{"metric": sample, "value": [0.0, "1.0"]}]})
            if url.endswith("/api/v1/query_range"):
                # The coverage probe uses the configured step (300s); the
                # spacing probe uses pvestatd_push_interval (60s).
                step = 60.0 if params.get("step") == "60s" else 300.0
                timestamps = [i * step for i in range(3)]
                return success(
                    {
                        "result": [
                            {
                                "metric": sample,
                                "values": [[t, "1.0"] for t in timestamps],
                            }
                        ]
                    }
                )
            raise AssertionError(url)

    session = RoutingSession({})
    client = PrometheusClient(PROM_CONFIG, session=session)
    report = verify_metrics(client, metrics, window)
    assert report.ok, [f.message for f in report.findings if f.level == "error"]
    assert report.observed_spacing_seconds == pytest.approx(60.0)
    assert DiskKey(101, "scsi0") in report.coverage_by_disk


def test_verify_metrics_applies_extra_selector_to_coverage_and_spacing_queries() -> None:
    """``metrics.extra_selector``, when set, is what ``verify-metrics``
    applies too (`resolve_node_selector(metrics, None)`'s own contract:
    the operator override, never an auto-derived one this command has no
    PVE client to build) -- verified by inspecting the actual query text
    sent, the same regression class `test_coverage_and_spacing_use_
    absolute_not_relative_start_end` guards against for the timestamps."""
    from proxmox_storage_drs.metrics import _check_coverage, _check_observed_spacing

    metrics = replace(_full_metrics_config(), extra_selector='cluster="mycluster"')
    window = WindowConfig(lookback_seconds=600)
    session = FakeSession(
        {
            "/api/v1/query_range": success(
                {"result": [{"metric": {"vmid": "1", "instance": "scsi0"}, "values": []}]}
            )
        }
    )
    client = PrometheusClient(PROM_CONFIG, session=session)

    _check_coverage(client, metrics, window, selector=metrics.extra_selector)
    _check_observed_spacing(client, metrics, selector=metrics.extra_selector)

    assert len(session.calls) == 2
    for _, params in session.calls:
        assert 'cluster="mycluster"' in params["query"]


def test_verify_metrics_missing_metric_name_is_an_error() -> None:
    metrics = _full_metrics_config()
    window = WindowConfig()

    class RoutingSession(FakeSession):
        def get(self, url, params, timeout, auth, headers):  # type: ignore[no-untyped-def]
            del timeout, auth, headers
            if url.endswith("__name__/values"):
                return success([])  # nothing exists
            if url.endswith("/api/v1/query"):
                return success({"result": []})
            if url.endswith("/api/v1/query_range"):
                return success({"result": []})
            raise AssertionError(url)

    client = PrometheusClient(PROM_CONFIG, session=RoutingSession({}))
    report = verify_metrics(client, metrics, window)
    assert not report.ok
    assert any("does not exist" in f.message for f in report.findings)


def test_verify_metrics_device_label_instance_warns() -> None:
    metrics = MetricsConfig(labels=MetricLabels(device="instance"))
    from proxmox_storage_drs.metrics import _check_device_label_collision

    finding = _check_device_label_collision(metrics)
    assert finding is not None
    assert finding.level == "warning"


def test_verify_metrics_device_label_not_instance_is_fine() -> None:
    metrics = MetricsConfig(labels=MetricLabels(device="disk"))
    from proxmox_storage_drs.metrics import _check_device_label_collision

    assert _check_device_label_collision(metrics) is None


def test_disk_keys_seen_skips_series_missing_either_label() -> None:
    from proxmox_storage_drs.metrics import _disk_keys_seen

    result: list[dict[str, Any]] = [
        {"metric": {"vmid": "101", "instance": "scsi0"}},
        {"metric": {"vmid": "102"}},  # no device label
        {"metric": {"instance": "scsi0"}},  # no vmid label
    ]
    assert _disk_keys_seen(result, "vmid", "instance") == {("101", "scsi0")}


def test_cross_metric_disk_consistency_silent_when_all_metrics_agree() -> None:
    from proxmox_storage_drs.metrics import _check_cross_metric_disk_consistency

    keys = {("101", "scsi0"), ("102", "efidisk0")}
    findings, missing_by_metric = _check_cross_metric_disk_consistency(
        {"rd_operations": keys, "wr_operations": keys}
    )
    assert findings == []
    assert missing_by_metric == {}


def test_cross_metric_disk_consistency_warns_on_a_dropped_field() -> None:
    """REVIEW.md-worthy real-world failure: Telegraf's Prometheus-compatible
    output silently drops a field the moment it sees a non-numeric value for
    it (InfluxDB fixes a field's type from its first write) -- which can
    drop just one of the six metrics for one disk, without touching the
    other five. ``compute_disk_coverage`` alone (only checking ``read_ops``)
    would miss this entirely if the dropped field is one of the other five;
    this cross-check catches it from data ``_check_sample_series`` already
    fetched, at no extra Prometheus cost."""
    from proxmox_storage_drs.metrics import _check_cross_metric_disk_consistency

    findings, missing_by_metric = _check_cross_metric_disk_consistency(
        {
            "rd_operations": {("101", "scsi0"), ("102", "efidisk0")},
            "wr_total_time_ns": {("101", "scsi0")},  # missing 102:efidisk0
        }
    )
    assert len(findings) == 1
    assert findings[0].level == "warning"
    assert "wr_total_time_ns" in findings[0].message
    assert "102:efidisk0" in findings[0].message
    assert "non-numeric" in findings[0].message
    assert missing_by_metric == {"wr_total_time_ns": (("102", "efidisk0"),)}


def test_cross_metric_disk_consistency_truncates_a_long_missing_list() -> None:
    from proxmox_storage_drs.metrics import _check_cross_metric_disk_consistency

    full = {(str(vmid), "scsi0") for vmid in range(100, 108)}  # 8 disks
    findings, missing_by_metric = _check_cross_metric_disk_consistency({"a": full, "b": set()})
    assert len(findings) == 1
    assert "no series for 8 disk(s)" in findings[0].message
    assert "+3 more" in findings[0].message
    assert len(missing_by_metric["b"]) == 8


def test_check_sample_series_reports_a_cross_metric_gap(monkeypatch: pytest.MonkeyPatch) -> None:
    """Integration through the real caller: a field silently missing one
    disk the others all report shows up as a warning naming that field."""
    from proxmox_storage_drs.metrics import _check_sample_series

    metrics = _full_metrics_config()

    def fake_instant_query(name: str) -> list[dict[str, Any]]:
        common = [
            {"metric": {"vmid": "101", "instance": "scsi0", "nodename": "pve01"}},
            {"metric": {"vmid": "102", "instance": "efidisk0", "nodename": "pve01"}},
        ]
        if name == metrics.write_time_ns:
            return common[:1]  # drops 102:efidisk0
        return common

    client = PrometheusClient(PROM_CONFIG, session=FakeSession({}))
    monkeypatch.setattr(client, "instant_query", fake_instant_query)

    findings, _samples, _missing_by_metric = _check_sample_series(client, metrics)
    warnings = [f.message for f in findings if f.level == "warning"]
    assert any(metrics.write_time_ns in m and "102:efidisk0" in m for m in warnings)


def test_verify_metrics_query_failure_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    metrics = _full_metrics_config()
    window = WindowConfig()

    class FailingSession(FakeSession):
        def get(self, url, params, timeout, auth, headers):  # type: ignore[no-untyped-def]
            raise AssertionError(f"should not be called for {url}")

    client = PrometheusClient(PROM_CONFIG, session=FailingSession({}))

    def raise_error(*args: object, **kwargs: object) -> Any:
        raise MetricsError("network down")

    monkeypatch.setattr(client, "label_values", raise_error)
    monkeypatch.setattr(client, "instant_query", raise_error)
    monkeypatch.setattr(client, "range_query", raise_error)

    report = verify_metrics(client, metrics, window)
    assert not report.ok
    assert any("network down" in f.message for f in report.findings)


def test_verify_metrics_no_device_label_collision_when_not_instance() -> None:
    metrics = MetricsConfig(
        labels=MetricLabels(vmid="vmid", device="disk", node="nodename"),
        rate_window_seconds=300,
        step_seconds=300,
        pvestatd_push_interval_seconds=60,
    )
    window = WindowConfig()
    sample = {"vmid": "101", "disk": "scsi0"}

    class RoutingSession(FakeSession):
        def get(self, url, params, timeout, auth, headers):  # type: ignore[no-untyped-def]
            del timeout, auth, headers
            if url.endswith("__name__/values"):
                return success(_all_metric_names(metrics))
            if url.endswith("/api/v1/query_range"):
                return success({"result": [{"metric": sample, "values": []}]})
            if url.endswith("/api/v1/query"):
                return success({"result": [{"metric": sample, "value": [0.0, "1"]}]})
            raise AssertionError(url)

    client = PrometheusClient(PROM_CONFIG, session=RoutingSession({}))
    report = verify_metrics(client, metrics, window)
    assert not any("collides" in f.message for f in report.findings)


def test_coverage_and_spacing_use_absolute_not_relative_start_end() -> None:
    """Regression: start/end must be real epoch timestamps, not `-lookback`.

    Prometheus's (and VictoriaMetrics's) query_range API takes absolute
    start/end -- Unix time or RFC3339 -- never an offset relative to "now".
    Found against a live server: an unanchored `-window.lookback_seconds`
    was rejected with a time-parsing error rather than silently
    misinterpreted, but the bug shipped past every prior mocked test because
    the fakes never checked what value was actually sent.
    """
    from proxmox_storage_drs.metrics import _check_coverage, _check_observed_spacing

    metrics = _full_metrics_config()
    window = WindowConfig(lookback_seconds=600)
    session = FakeSession(
        {
            "/api/v1/query_range": success(
                {"result": [{"metric": {"vmid": "1", "instance": "scsi0"}, "values": []}]}
            )
        }
    )
    client = PrometheusClient(PROM_CONFIG, session=session)

    _check_coverage(client, metrics, window)
    _check_observed_spacing(client, metrics)

    # A timestamp from any time this test could plausibly run, not a small
    # offset like -600 or 0.
    year_2024_epoch = 1_700_000_000.0
    assert len(session.calls) == 2
    for _, params in session.calls:
        start, end = float(params["start"]), float(params["end"])
        assert start > year_2024_epoch, params
        assert end > year_2024_epoch, params
        assert end > start, params


def test_coverage_skips_series_with_bad_labels() -> None:
    from proxmox_storage_drs.metrics import _check_coverage

    metrics = _full_metrics_config()
    window = WindowConfig(lookback_seconds=600)

    class RoutingSession(FakeSession):
        def get(self, url, params, timeout, auth, headers):  # type: ignore[no-untyped-def]
            del timeout, auth, headers, params
            return success(
                {
                    "result": [
                        {"metric": {"instance": "scsi0"}, "values": [[0.0, "1"]]},  # no vmid
                        {"metric": {"vmid": "101"}, "values": [[0.0, "1"]]},  # no device
                        {"metric": {"vmid": "x", "instance": "scsi0"}, "values": []},  # bad vmid
                    ]
                }
            )

    client = PrometheusClient(PROM_CONFIG, session=RoutingSession({}))
    findings, coverage = _check_coverage(client, metrics, window)
    assert coverage == {}
    assert any("no series to measure coverage" in f.message for f in findings)


def test_low_coverage_is_a_warning() -> None:
    from proxmox_storage_drs.metrics import _check_coverage

    metrics = _full_metrics_config()
    window = WindowConfig(lookback_seconds=600, min_coverage=0.9)

    class RoutingSession(FakeSession):
        def get(self, url, params, timeout, auth, headers):  # type: ignore[no-untyped-def]
            del timeout, auth, headers, params
            return success(
                {
                    "result": [
                        {
                            "metric": {"vmid": "101", "instance": "scsi0"},
                            "values": [[0.0, "1"]],  # 1 of 3 expected samples
                        }
                    ]
                }
            )

    client = PrometheusClient(PROM_CONFIG, session=RoutingSession({}))
    findings, coverage = _check_coverage(client, metrics, window)
    assert coverage[DiskKey(101, "scsi0")] < 0.9
    assert any("below window.min_coverage" in f.message for f in findings)


def test_spacing_skips_series_with_fewer_than_two_samples() -> None:
    from proxmox_storage_drs.metrics import _check_observed_spacing

    metrics = _full_metrics_config()

    class RoutingSession(FakeSession):
        def get(self, url, params, timeout, auth, headers):  # type: ignore[no-untyped-def]
            del timeout, auth, headers, params
            return success(
                {
                    "result": [
                        {"metric": {}, "values": [[0.0, "1"]]},  # only one sample
                        {"metric": {}, "values": [[0.0, "1"], [60.0, "1"]]},
                    ]
                }
            )

    client = PrometheusClient(PROM_CONFIG, session=RoutingSession({}))
    findings, spacing = _check_observed_spacing(client, metrics)
    assert spacing == pytest.approx(60.0)
    assert findings == []


def test_verify_metrics_spacing_disagreement_is_error() -> None:
    metrics = _full_metrics_config()
    window = WindowConfig()
    sample = {"vmid": "101", "instance": "scsi0"}

    class RoutingSession(FakeSession):
        def get(self, url, params, timeout, auth, headers):  # type: ignore[no-untyped-def]
            del timeout, auth, headers
            if url.endswith("__name__/values"):
                return success(_all_metric_names(metrics))
            if url.endswith("/api/v1/query_range") and "step" in params and params["step"] == "60s":
                # spacing probe: actual spacing is 600s, wildly off from the
                # configured 60s push interval.
                timestamps = [0.0, 600.0, 1200.0]
                return success(
                    {"result": [{"metric": sample, "values": [[t, "1"] for t in timestamps]}]}
                )
            if url.endswith("/api/v1/query_range"):
                return success({"result": []})
            if url.endswith("/api/v1/query"):
                return success({"result": [{"metric": sample, "value": [0.0, "1"]}]})
            raise AssertionError(url)

    client = PrometheusClient(PROM_CONFIG, session=RoutingSession({}))
    report = verify_metrics(client, metrics, window)
    assert not report.ok
    assert any("disagrees" in f.message for f in report.findings)
