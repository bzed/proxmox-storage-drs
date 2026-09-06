# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Prometheus client, PromQL builders and verify-metrics.

No test here talks to a real Prometheus (.agents/testing.md): PrometheusClient
is exercised through a fake session with the same get(url, params=...) shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from proxmox_storage_drs.config import MetricLabels, MetricsConfig, PrometheusConfig, WindowConfig
from proxmox_storage_drs.exceptions import MetricsError
from proxmox_storage_drs.metrics import (
    DiskKey,
    PrometheusClient,
    build_quantile_over_time_promql,
    build_rate_promql,
    parse_disk_range_series,
    parse_disk_series,
    raw_metric_name,
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


def test_build_quantile_over_time_promql() -> None:
    expr = build_quantile_over_time_promql("sum(x)", 0.95, 86400, 300)
    assert expr == "quantile_over_time(0.95, (sum(x))[86400s:300s])"


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
