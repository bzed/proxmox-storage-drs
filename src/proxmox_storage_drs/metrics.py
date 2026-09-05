# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Prometheus client, PromQL construction and ``pve-storage-drs verify-metrics``.

See IMPLEMENTATION_PLAN.md sections 3.1-3.4. Telegraf/InfluxDB naming is
deployment-specific (section 3.3), so every metric and label name is
configuration (``config.MetricsConfig``), never a constant baked in here.

This module only ever *reads*. All arithmetic on raw series (the section 4
load model) lives in ``loadmodel.py``; this module's job stops at handing
back parsed ``(vmid, device) -> value`` maps and the section 3.3
verification report.
"""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass
from typing import Any, Protocol

import requests

from proxmox_storage_drs.config import MetricsConfig, PrometheusConfig, WindowConfig
from proxmox_storage_drs.exceptions import MetricsError


class _ResponseLike(Protocol):
    """The subset of ``requests.Response`` this module relies on."""

    status_code: int
    text: str

    def json(self) -> Any: ...  # noqa: E704 - black's one-line Protocol body style


class _SessionLike(Protocol):
    """The subset of ``requests.Session`` this module relies on.

    A structural type rather than ``requests.Session`` itself, so tests can
    substitute a plain fake object with a matching ``get()`` instead of
    subclassing or mocking the real (network-capable) session.
    """

    def get(
        self,
        url: str,
        params: dict[str, str],
        timeout: float,
        auth: object,
        headers: dict[str, str],
    ) -> _ResponseLike: ...  # noqa: E704


# The six raw quantities of section 3.4, keyed by the MetricsConfig attribute
# that names them -- this is what lets verify-metrics and the loadmodel (a
# later phase) iterate "every configured metric" without hardcoding the list
# twice.
RAW_METRIC_FIELDS = (
    "read_ops",
    "write_ops",
    "read_bytes",
    "write_bytes",
    "read_time_ns",
    "write_time_ns",
)


@dataclass(frozen=True, slots=True)
class DiskKey:
    """The ``(vmid, device)`` identity both Prometheus and the PVE API expose.

    See IMPLEMENTATION_PLAN.md section 2: "The join between them is the disk
    identity (vmid, device), which both sides expose."
    """

    vmid: int
    device: str


def _format_promql_duration(duration_seconds: float) -> str:
    """Render a duration as a PromQL range-vector selector, e.g. ``"300s"``.

    Always in seconds: PromQL accepts any of ``s``/``m``/``h``/``d`` but
    seconds needs no unit-choice logic and is exact for a non-round value.
    """
    return f"{duration_seconds:g}s"


def build_rate_promql(
    metric_name: str, vmid_label: str, device_label: str, rate_window_seconds: float
) -> str:
    """The section 3.4 per-metric rate expression.

    ``sum by (vmid, device) (rate(<metric>[<rate_window>]))`` -- the ``sum
    by`` deliberately collapses the node/host labels, so a VM that
    live-migrated between nodes during the window remains one series.
    """
    window = _format_promql_duration(rate_window_seconds)
    return f"sum by ({vmid_label}, {device_label}) (rate({metric_name}[{window}]))"


def build_quantile_over_time_promql(
    rate_expr: str, quantile: float, lookback_seconds: float, step_seconds: float
) -> str:
    """Wrap a rate expression in the section 3.4 quantile-over-time reduction.

    ``quantile_over_time(q, (<rate_expr>)[<lookback>:<step>])``.
    """
    lookback = _format_promql_duration(lookback_seconds)
    step = _format_promql_duration(step_seconds)
    return f"quantile_over_time({quantile:g}, ({rate_expr})[{lookback}:{step}])"


def raw_metric_name(metrics: MetricsConfig, field: str) -> str:
    """The configured metric name for one of :data:`RAW_METRIC_FIELDS`."""
    value = getattr(metrics, field)
    assert isinstance(value, str)  # narrows for mypy; field is always a str attribute
    return value


# ------------------------------------------------------------------ client


class PrometheusClient:
    """Thin wrapper over the Prometheus HTTP API. See section 3.4/3.5.

    ``session`` is injectable so tests substitute a fake with the same
    ``get(url, params=..., timeout=...)`` shape -- no test ever talks to a
    real Prometheus (.agents/testing.md).
    """

    def __init__(self, config: PrometheusConfig, session: _SessionLike | None = None) -> None:
        self._config = config
        self._session = session if session is not None else requests.Session()

    def _auth(self) -> tuple[str, str] | None:
        if self._config.username is not None and self._config.password is not None:
            return (self._config.username, self._config.password)
        return None

    def _headers(self) -> dict[str, str]:
        if self._config.bearer_token:
            return {"Authorization": f"Bearer {self._config.bearer_token}"}
        return {}

    def _get(self, path: str, params: dict[str, str]) -> Any:
        """Issue one request and return the decoded ``data`` field.

        Typed ``Any`` rather than a specific shape because that field's
        shape genuinely differs by endpoint: a dict for ``query``/
        ``query_range``, a bare list for ``label/<name>/values``. Each
        caller below knows which shape it asked for.
        """
        url = self._config.url.rstrip("/") + path
        try:
            response = self._session.get(
                url,
                params=params,
                timeout=self._config.timeout_seconds,
                auth=self._auth(),
                headers=self._headers(),
            )
        except requests.RequestException as exc:
            raise MetricsError(f"Prometheus request to {path} failed: {exc}") from exc
        if response.status_code != 200:
            raise MetricsError(
                f"Prometheus request to {path} returned HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise MetricsError(f"Prometheus response to {path} was not JSON: {exc}") from exc
        if payload.get("status") != "success":
            raise MetricsError(
                f"Prometheus request to {path} did not succeed: {payload.get('error', payload)}"
            )
        return payload["data"]

    def instant_query(self, promql: str) -> list[dict[str, Any]]:
        """``GET /api/v1/query``. Returns the raw ``data.result`` list."""
        data = self._get("/api/v1/query", {"query": promql})
        result: list[dict[str, Any]] = data.get("result", [])
        return result

    def range_query(
        self, promql: str, start_epoch_seconds: float, end_epoch_seconds: float, step_seconds: float
    ) -> list[dict[str, Any]]:
        """``GET /api/v1/query_range``. Returns the raw ``data.result`` list."""
        data = self._get(
            "/api/v1/query_range",
            {
                "query": promql,
                "start": f"{start_epoch_seconds:.3f}",
                "end": f"{end_epoch_seconds:.3f}",
                "step": _format_promql_duration(step_seconds),
            },
        )
        result: list[dict[str, Any]] = data.get("result", [])
        return result

    def label_values(self, label_name: str) -> list[str]:
        """``GET /api/v1/label/<name>/values``.

        The one endpoint whose ``data`` is a bare list rather than a dict
        with a ``result`` key.
        """
        data: list[str] = self._get(f"/api/v1/label/{label_name}/values", {})
        return data


# -------------------------------------------------------------- parsing


def parse_disk_series(
    result: list[dict[str, Any]], vmid_label: str, device_label: str
) -> dict[DiskKey, float]:
    """Turn an instant-query ``result`` list into ``{DiskKey: value}``.

    Skips (rather than raising on) a series missing either label: an
    unrelated series matched by an overly broad metric name should not abort
    the whole query, and section 3.3's own label-presence check is what
    reports that as a finding instead.
    """
    out: dict[DiskKey, float] = {}
    for series in result:
        labels = series.get("metric", {})
        vmid_raw = labels.get(vmid_label)
        device = labels.get(device_label)
        if vmid_raw is None or not device:
            continue
        try:
            vmid = int(vmid_raw)
        except (TypeError, ValueError):
            continue
        _timestamp, value_raw = series["value"]
        out[DiskKey(vmid=vmid, device=device)] = float(value_raw)
    return out


# ----------------------------------------------------------- verify-metrics


@dataclass(frozen=True, slots=True)
class Finding:
    """One line of ``verify-metrics`` output. ``level`` is info/warning/error."""

    level: str
    message: str


@dataclass(frozen=True, slots=True)
class VerifyMetricsReport:
    findings: tuple[Finding, ...]
    sample_series: dict[str, dict[str, str]]
    coverage_by_disk: dict[DiskKey, float]
    observed_spacing_seconds: float | None

    @property
    def ok(self) -> bool:
        return not any(f.level == "error" for f in self.findings)


def _check_metric_names_exist(client: PrometheusClient, metrics: MetricsConfig) -> list[Finding]:
    """Section 3.3 step 1: every configured metric name must exist."""
    try:
        known_names = set(client.label_values("__name__"))
    except MetricsError as exc:
        return [Finding("error", f"could not list metric names: {exc}")]
    findings = []
    for field in RAW_METRIC_FIELDS:
        name = raw_metric_name(metrics, field)
        if name not in known_names:
            findings.append(
                Finding("error", f"metrics.{field} = {name!r} does not exist in Prometheus")
            )
        else:
            findings.append(Finding("info", f"metrics.{field} = {name!r} exists"))
    return findings


def _check_sample_series(
    client: PrometheusClient, metrics: MetricsConfig
) -> tuple[list[Finding], dict[str, dict[str, str]]]:
    """Section 3.3 step 2/3/4: one sample series per metric, with its labels."""
    findings: list[Finding] = []
    samples: dict[str, dict[str, str]] = {}
    labels = metrics.labels
    for field in RAW_METRIC_FIELDS:
        name = raw_metric_name(metrics, field)
        try:
            result = client.instant_query(name)
        except MetricsError as exc:
            findings.append(Finding("error", f"{name}: query failed: {exc}"))
            continue
        if not result:
            findings.append(Finding("warning", f"{name}: no series returned (no data yet?)"))
            continue
        sample_labels = result[0].get("metric", {})
        samples[name] = sample_labels
        findings.append(Finding("info", f"{name}: sample series labels {sample_labels}"))
        for role, label_name in (
            ("vmid", labels.vmid),
            ("device", labels.device),
            ("node", labels.node),
        ):
            if not sample_labels.get(label_name):
                findings.append(
                    Finding(
                        "error",
                        f"{name}: configured {role} label {label_name!r} is missing or "
                        "empty on the sample series",
                    )
                )
    return findings, samples


def _check_device_label_collision(metrics: MetricsConfig) -> Finding | None:
    """Section 3.3 step 4: warn if the device label is literally ``instance``.

    PVE's own ``instance`` tag collides with Prometheus's scrape-target
    ``instance`` label; many Telegraf configurations rename or overwrite it.
    """
    if metrics.labels.device == "instance":
        return Finding(
            "warning",
            "metrics.labels.device is 'instance', which collides with Prometheus's "
            "own scrape-target label of the same name -- confirm this is really the "
            "per-disk device tag and not the scrape target",
        )
    return None


def _check_coverage(
    client: PrometheusClient, metrics: MetricsConfig, window: WindowConfig
) -> tuple[list[Finding], dict[DiskKey, float]]:
    """Section 3.3 step 5: per-disk sample coverage over the decision window.

    Uses ``read_ops`` as the representative metric: coverage gaps are a
    property of the underlying scrape, not of which of the six fields is
    read, and running six range queries here would be six times the load for
    no extra information.
    """
    metric_name = metrics.read_ops
    expr = build_rate_promql(
        metric_name, metrics.labels.vmid, metrics.labels.device, metrics.rate_window_seconds
    )
    # Prometheus's query_range API takes absolute start/end (Unix time or
    # RFC3339), never an offset relative to "now" -- anchoring to time.time()
    # here is not optional. An unanchored negative value was rejected outright
    # by a live server during development; see the git history for the fix.
    end = time.time()
    start = end - window.lookback_seconds
    try:
        result = client.range_query(expr, start, end, metrics.step_seconds)
    except MetricsError as exc:
        return [Finding("error", f"coverage check failed: {exc}")], {}

    expected_samples = max(1, round(window.lookback_seconds / metrics.step_seconds) + 1)
    coverage: dict[DiskKey, float] = {}
    for series in result:
        labels = series.get("metric", {})
        vmid_raw = labels.get(metrics.labels.vmid)
        device = labels.get(metrics.labels.device)
        if vmid_raw is None or not device:
            continue
        try:
            key = DiskKey(vmid=int(vmid_raw), device=device)
        except (TypeError, ValueError):
            continue
        actual_samples = len(series.get("values", []))
        coverage[key] = min(1.0, actual_samples / expected_samples)

    findings = []
    for key, fraction in sorted(coverage.items(), key=lambda kv: (kv[0].vmid, kv[0].device)):
        if fraction < window.min_coverage:
            findings.append(
                Finding(
                    "warning",
                    f"{key.vmid}:{key.device}: coverage {fraction:.0%} is below "
                    f"window.min_coverage ({window.min_coverage:.0%})",
                )
            )
    if not coverage:
        findings.append(Finding("warning", f"{metric_name}: no series to measure coverage on"))
    return findings, coverage


def _check_observed_spacing(
    client: PrometheusClient, metrics: MetricsConfig
) -> tuple[list[Finding], float | None]:
    """Section 3.3 step 6: observed sample spacing vs. ``pvestatd_push_interval``.

    Measures the modal delta between consecutive timestamps of one live
    series over a short recent range, since that is what the ``rate_window
    >= 4x`` rule (section 11.1) is actually protecting.
    """
    metric_name = metrics.read_ops
    probe_window_seconds = max(metrics.pvestatd_push_interval_seconds * 20, 600.0)
    end = time.time()
    start = end - probe_window_seconds
    try:
        result = client.range_query(metric_name, start, end, metrics.pvestatd_push_interval_seconds)
    except MetricsError as exc:
        return [Finding("error", f"spacing check failed: {exc}")], None

    for series in result:
        timestamps = [point[0] for point in series.get("values", [])]
        if len(timestamps) < 2:
            continue
        deltas = [b - a for a, b in zip(timestamps, timestamps[1:])]
        spacing = statistics.mode(deltas)
        findings: list[Finding] = []
        configured = metrics.pvestatd_push_interval_seconds
        relative_diff = abs(spacing - configured) / configured if configured else float("inf")
        if relative_diff > 0.20:
            findings.append(
                Finding(
                    "error",
                    f"observed sample spacing {spacing:g}s disagrees with "
                    f"metrics.pvestatd_push_interval ({configured:g}s) by more than 20%",
                )
            )
        if metrics.rate_window_seconds < 4 * spacing:
            findings.append(
                Finding(
                    "error",
                    f"metrics.rate_window ({metrics.rate_window_seconds:g}s) is below 4x "
                    f"the observed sample spacing ({spacing:g}s)",
                )
            )
        return findings, spacing

    return [
        Finding("warning", f"{metric_name}: no series with >=2 samples to measure spacing")
    ], None


def verify_metrics(
    client: PrometheusClient, metrics: MetricsConfig, window: WindowConfig
) -> VerifyMetricsReport:
    """Run every section 3.3 check and assemble the report.

    Must be run before relying on any plan (section 3.3); ``cli.py``'s
    ``verify-metrics`` command is this function plus formatting.
    """
    findings: list[Finding] = []
    findings.extend(_check_metric_names_exist(client, metrics))
    sample_findings, samples = _check_sample_series(client, metrics)
    findings.extend(sample_findings)
    collision = _check_device_label_collision(metrics)
    if collision is not None:
        findings.append(collision)
    coverage_findings, coverage = _check_coverage(client, metrics, window)
    findings.extend(coverage_findings)
    spacing_findings, spacing = _check_observed_spacing(client, metrics)
    findings.extend(spacing_findings)

    return VerifyMetricsReport(
        findings=tuple(findings),
        sample_series=samples,
        coverage_by_disk=coverage,
        observed_spacing_seconds=spacing,
    )
