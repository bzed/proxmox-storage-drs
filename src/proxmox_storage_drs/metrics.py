# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Prometheus client, PromQL construction and ``pve-storage-drs verify-metrics``.

See IMPLEMENTATION_PLAN.md sections 3.1-3.4. Telegraf/InfluxDB naming is
deployment-specific (section 3.3), so every metric and label name is
configuration (``config.MetricsConfig``), never a constant baked in here.

This module only ever *reads*. All arithmetic on raw series (the section 4
load model) lives in ``loadmodel.py``; this module's job stops at handing
back parsed ``(vmid, device) -> value`` maps, the section 3.3 verification
report, and (:func:`compute_disk_coverage`) the one per-disk coverage
computation both that report and ``loadmodel.py``'s ``min_coverage`` gate
share.
"""

from __future__ import annotations

import re
import statistics
import time
from dataclasses import dataclass
from typing import Any, Protocol, Sequence

import requests

from proxmox_storage_drs.config import MetricsConfig, PrometheusConfig, WindowConfig
from proxmox_storage_drs.exceptions import BundleError, MetricsError, RangeStepMismatch


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
# that names them -- this is what lets verify-metrics and loadmodel.py
# iterate "every configured metric" without hardcoding the list twice.
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

    Deliberately *not* ``f"{duration_seconds:g}s"``: ``%g`` switches to
    scientific notation past 6 significant digits (e.g. a 14-day lookback,
    1209600s, becomes ``"1.2096e+06s"``), which PromQL's duration parser
    rejects outright (``unknown unit "." in duration``) -- confirmed live.
    ``:f`` never uses scientific notation; trimming trailing zeros (and a
    then-bare trailing ``.``) keeps the same exact, no-unit-choice output
    for the whole-second case this project sends almost everywhere.
    """
    return f"{duration_seconds:.6f}".rstrip("0").rstrip(".") + "s"


def build_rate_promql(
    metric_name: str,
    vmid_label: str,
    device_label: str,
    rate_window_seconds: float,
    selector: str | None = None,
) -> str:
    """The section 3.4 per-metric rate expression.

    ``sum by (vmid, device) (rate(<metric>{<selector>}[<rate_window>]))``
    -- the ``sum by`` deliberately collapses the node/host labels, so a VM
    that live-migrated between nodes during the window remains one series.
    ``selector`` (:func:`resolve_node_selector`) is the section 3.4
    node-scoping matcher, applied *inside* ``rate()``'s own vector
    selector, before the labels it names are ever collapsed -- this is
    what keeps a Prometheus shared by more than this one cluster (or
    anything else emitting a same-named metric) from silently summing in
    a same-numbered vmid from somewhere else. ``None`` (the default)
    means "no restriction", identical to the expression before this
    parameter existed.
    """
    window = _format_promql_duration(rate_window_seconds)
    scope = f"{{{selector}}}" if selector else ""
    return f"sum by ({vmid_label}, {device_label}) (rate({metric_name}{scope}[{window}]))"


def safe_range_step_seconds(step_seconds: float, rate_window_seconds: float) -> float:
    """The step to actually send Prometheus for a ``rate()``-based
    ``query_range`` call or ``quantile_over_time`` subquery.

    Confirmed live against a real gigapipe deployment (two independent
    production clusters, both after an update to it): both
    ``/api/v1/query_range`` and the PromQL ``[range:step]`` subquery form
    silently return *zero series* for any range-vector function
    (``rate()``, ``irate()``, ``increase()``, ``delta()``, ``deriv()`` all
    confirmed) whenever the query's own ``step`` is **greater than or
    equal to** the function's own range-vector duration -- even though the
    identical expression evaluated with no step at all (a plain instant
    ``/api/v1/query``) returns correct data, and even though a bare
    (non-function) selector via the same ``query_range``/subquery step is
    unaffected. Binary-searched to the exact second: for
    ``rate(x[300s])``, ``step=299s`` returns full data, ``step=300s``
    returns nothing at all -- independent of window length or absolute
    step size. This project's own defaults set ``metrics.step`` and
    ``metrics.rate_window`` to the *same* value (300s, idiomatic
    back-to-back PromQL tiling with no gaps or overlap between successive
    rate windows) -- exactly the failing boundary -- so a fresh install
    with untouched defaults can hit this on an affected backend with no
    misconfiguration at all.

    A no-op (returns ``step_seconds`` unchanged) once ``step_seconds`` is
    already strictly less than ``rate_window_seconds`` -- nothing to work
    around. Otherwise returns the largest whole-second step that is
    strictly less than ``rate_window_seconds`` and divides ``step_seconds``
    as evenly as a whole-second value can -- :func:`decimate_to_configured_step`
    recovers (approximately, by *rounded* division, not necessarily exact)
    the originally configured grid from it by keeping every Nth point. A
    whole number of seconds is not a style choice: gigapipe's own duration
    parser rejects a fractional-second value outright (``cannot parse
    "276.923s" to a valid duration``, confirmed live against
    ``metrics.step: 1h``/the default ``rate_window: 300s``, whose exact
    quotient is 3600/13 = 276.923...) -- confirmed on the very deployment
    this workaround exists for, so this cannot skip the floor and still
    work. Not Prometheus-backend-specific by name: this workaround is keyed
    purely on the ``step >= range`` symptom, and every *range* query path
    (coverage, the forecaster's raw series) is a true no-op against a
    correctly-behaving backend -- :func:`decimate_to_configured_step`
    recovers the identical instants and values a plain ``step_seconds``
    query would have returned. The one exception is
    :func:`build_quantile_over_time_promql`'s own subquery, which cannot
    decimate (an instant query returns one scalar): its inner expression is
    evaluated on this denser, safe-step grid unconditionally, on *every*
    backend healthy or not -- a small but real shift in the reduced
    statistic, not a no-op there (REVIEW.md Z-04)."""
    if step_seconds < rate_window_seconds:
        return step_seconds
    divisor = int(step_seconds // rate_window_seconds) + 1
    return float(max(1, int(step_seconds // divisor)))


def decimate_to_configured_step(
    points: Sequence[Any], step_seconds: float, safe_step_seconds: float
) -> list[Any]:
    """The inverse of :func:`safe_range_step_seconds`: recover a series at
    (approximately) the originally configured ``step_seconds`` grid from
    one actually sampled at ``safe_step_seconds`` (a whole-second value
    that divides ``step_seconds`` as evenly as a whole second can -- not
    always an *exact* divisor, see that function's own docstring), by
    keeping every ``round(step_seconds / safe_step_seconds)``-th point.
    ``points`` is a plain, untyped sequence -- both a raw
    ``query_range`` response's ``values`` list (``[timestamp, value_str]``
    pairs) and an already-parsed ``TimeSeries`` (``(timestamp, value)``
    tuples) are valid inputs; this never inspects an element, only slices
    the sequence. A no-op (returns ``points`` unchanged, as a plain list)
    when the two steps are equal -- :func:`safe_range_step_seconds` was
    never triggered, so there is nothing to reduce."""
    if safe_step_seconds >= step_seconds:
        return list(points)
    divisor = max(1, round(step_seconds / safe_step_seconds))
    return list(points[::divisor])


#: One day, in seconds -- the default chunk size for a live ``query_range``
#: fetch (:func:`stitch_range_results`, ``loadmodel._fetch_raw_quantity_series``),
#: matching ``collect.py``'s own ``_CHUNK_SECONDS`` (section 16.2): chosen so
#: a request never runs into a backend's own max-points-per-timeseries limit
#: (VictoriaMetrics/gigapipe's default 11,000, confirmed live -- a single
#: unchunked request over a wide range, e.g. the section 10.2 backtest gate's
#: ``2 * window.lookback_seconds`` floor combined with a fine ``metrics.step``,
#: can exceed it with a 500 "exceeded maximum resolution").
RANGE_QUERY_CHUNK_SECONDS = 86400.0


def stitch_range_results(
    captures: Sequence[tuple[float, float, list[dict[str, Any]]]],
) -> list[dict[str, Any]]:
    """Merges several ``(start, end, result)`` ``query_range`` captures of
    the *same* query -- whichever combination of chunking and repeat calls
    produced them -- into one logical result: one series per disk with
    every point from every chunk, deduplicated by timestamp and sorted.
    Order-independent, so it does not matter whether the captures arrived
    in chunk order. The same merge collect.py's own ``_stitch_range_captures``
    (section 16.2) performs for a captured bundle's range files, generalized
    here (result list only, no start/end/step bookkeeping) for a live
    fetch's own chunked retry (``loadmodel._fetch_raw_quantity_series``)."""
    by_disk: dict[tuple[tuple[str, str], ...], dict[float, Any]] = {}
    for _start, _end, result in captures:
        for series in result or []:
            key = tuple(sorted(series.get("metric", {}).items()))
            points = by_disk.setdefault(key, {})
            for ts, value in series.get("values", []):
                points[float(ts)] = value
    stitched = [
        {"metric": dict(key), "values": sorted(points.items())} for key, points in by_disk.items()
    ]
    return sorted(stitched, key=lambda s: sorted(s["metric"].items()))


_PROMQL_REGEX_SPECIAL = re.compile(r"([.^$|()\[\]{}*+?\\])")


def _escape_promql_regex_literal(value: str) -> str:
    """Escape one literal string for safe use inside a PromQL/RE2 ``=~``
    alternation. A node name is very often an FQDN (``pve1.example.com``),
    and ``.`` is a regex metacharacter -- without this, a node selector
    built from node names would match more than the exact node it names."""
    return _PROMQL_REGEX_SPECIAL.sub(r"\\\1", value)


def build_node_selector(node_label: str, node_names: Sequence[str]) -> str | None:
    """Section 3.4's auto-derived node-scoping filter:
    ``<node_label>=~"n1|n2|..."`` from the cluster's own node list
    (``PveClient.node_names()``) -- every name escaped as a literal, not a
    sub-pattern, so a node named ``pve-1`` cannot also match a
    ``pve-10`` that happens to exist too. ``None`` for an empty list: a
    config/API problem is what should surface that loudly elsewhere, not
    a query silently scoped to match nothing everywhere it is used."""
    if not node_names:
        return None
    alternation = "|".join(_escape_promql_regex_literal(n) for n in sorted(set(node_names)))
    return f'{node_label}=~"{alternation}"'


def resolve_node_selector(
    metrics: MetricsConfig,
    node_names: Sequence[str] | None,
) -> str | None:
    """The one selector every query in this module inserts, resolved once
    per run (section 3.4), in this precedence:

    1. ``metrics.extra_selector`` wins outright when the operator set one
       -- trusted completely, since only the operator knows their own
       Telegraf/InfluxDB tagging scheme, and it may name something other
       than a node at all.
    2. The auto-derived :func:`build_node_selector` from ``node_names``
       (``PveClient.node_names()``, this cluster's own node list)
       otherwise -- the default, so a Prometheus shared by more than one
       PVE cluster (or by anything else emitting a same-named metric)
       cannot silently sum in a same-numbered vmid from somewhere else.
    3. ``None`` when neither applies -- an empty ``node_names`` (or
       ``verify-metrics``, which passes ``node_names=None`` here rather
       than fetching them from the PVE API itself, since it is otherwise
       deliberately independent of the PVE API entirely --
       `docs/manual/20-verifying-metrics.md`).

    There used to be a middle tier here matching a ``cluster``-naming
    label against the live cluster's own name (``PveClient.cluster_name()``).
    It was removed: the premise that this project's deployments carry such
    a label "as standard practice" was simply wrong (an operator's own
    correction, not a Prometheus finding) -- there is no such convention,
    and the tier existed only on that mistaken assumption. Use
    ``metrics.extra_selector`` for a cluster-naming (or any other) label
    your own Telegraf/InfluxDB tagging scheme actually has."""
    if metrics.extra_selector:
        return metrics.extra_selector
    if node_names:
        return build_node_selector(metrics.labels.node, node_names)
    return None


def build_quantile_over_time_promql(
    rate_expr: str, quantile: float, lookback_seconds: float, step_seconds: float
) -> str:
    """Wrap a rate expression in the section 3.4 quantile-over-time reduction.

    ``quantile_over_time(q, (<rate_expr>)[<lookback>:<step>])``.

    ``step_seconds`` is embedded verbatim, deliberately -- this stays a
    pure, unconditional text builder. A caller working around the
    ``step >= range`` gigapipe bug (:func:`safe_range_step_seconds`) does so
    by calling this a second time with a *different* ``step_seconds``, not
    by this function silently substituting one in: unlike
    :func:`compute_disk_coverage`'s ``query_range`` call, an
    unconditional substitution here would change every replayed bundle's
    query text (hence its lookup hash) even for a bundle captured
    correctly, before any backend ever had this bug -- see the retry
    wrappers in ``loadmodel.py``/``collect.py`` instead, which only ever
    reach for the alternate step after the plain one has already come back
    empty.
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

    def buildinfo(self) -> str | None:
        """``GET /api/v1/status/buildinfo``: the running Prometheus's own
        version (section 16.1/16.3's manifest "versions" field -- X-08).
        Not an identifier, so it needs no anonymization; ``None`` if the
        response has no ``version`` key."""
        data = self._get("/api/v1/status/buildinfo", {})
        value = data.get("version") if isinstance(data, dict) else None
        return str(value) if value is not None else None


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


def parse_disk_range_series(
    result: list[dict[str, Any]], vmid_label: str, device_label: str
) -> dict[DiskKey, tuple[tuple[float, float], ...]]:
    """The ``query_range`` counterpart to :func:`parse_disk_series`: turns a
    ``query_range`` ``result`` list (each series carrying ``values``, a
    ``[[timestamp, value_str], ...]`` matrix, rather than one ``value``)
    into ``{DiskKey: TimeSeries}`` -- section 10's raw material for a
    :class:`~proxmox_storage_drs.forecast.Forecaster`, and
    ``loadmodel.compute_disk_load_series()``'s own input before its section
    4 blend. Skips a series missing either label, identically to
    :func:`parse_disk_series` and for the same reason."""
    out: dict[DiskKey, tuple[tuple[float, float], ...]] = {}
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
        points = tuple((float(ts), float(value_raw)) for ts, value_raw in series.get("values", []))
        out[DiskKey(vmid=vmid, device=device)] = points
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
    # Z-02: the full (vmid, device) lists `_check_cross_metric_disk_consistency()`
    # truncates to "top 5 (+N more)" for its own finding text -- carried here,
    # untruncated and with real vmids, so `collect.py` can rebuild that
    # finding's message from a registered-vmid-only view instead of leaking
    # a foreign vmid the structured `coverage_by_disk` above already drops.
    missing_disks_by_metric: dict[str, tuple[tuple[str, str], ...]]

    @property
    def ok(self) -> bool:
        return not any(f.level == "error" for f in self.findings)


_NUMERIC_DROP_HINT = (
    "Prometheus/OpenMetrics has no string sample type, and Telegraf silently drops a field "
    "the moment it observes a non-numeric value for it (InfluxDB line protocol fixes a field's "
    "type from its first write) -- check your PVE/Telegraf blockstat collection for a "
    "non-numeric value on this field"
)


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
                Finding(
                    "error",
                    f"metrics.{field} = {name!r} does not exist in Prometheus -- "
                    f"{_NUMERIC_DROP_HINT}, or it genuinely has not been configured/emitted",
                )
            )
        else:
            findings.append(Finding("info", f"metrics.{field} = {name!r} exists"))
    return findings


def _disk_keys_seen(
    result: list[dict[str, Any]], vmid_label: str, device_label: str
) -> set[tuple[str, str]]:
    """Every distinct ``(vmid, device)`` pair carried by an
    :meth:`PrometheusClient.instant_query` result -- pure and side-effect
    free so :func:`_check_cross_metric_disk_consistency` below is
    unit-testable without a fake session at all. A series missing either
    label is skipped, matching every other per-disk join in this module
    (``compute_disk_coverage``, ``loadmodel.py``)."""
    keys: set[tuple[str, str]] = set()
    for series in result:
        series_labels = series.get("metric", {})
        vmid_value = series_labels.get(vmid_label)
        device_value = series_labels.get(device_label)
        if vmid_value and device_value:
            keys.add((vmid_value, device_value))
    return keys


def format_cross_metric_finding(name: str, missing: Sequence[tuple[str, str]]) -> Finding:
    """Builds :func:`_check_cross_metric_disk_consistency`'s one finding
    shape from a ``(vmid, device)`` list -- a "top 5, +N more" note over
    whatever ``missing`` it is handed. Factored out (rather than inlined at
    the one call site below) so ``collect.py`` can rebuild the *identical*
    message from a filtered, registered-vmid-only view of ``missing`` when
    redacting a bundle's findings.json (Z-02), instead of reformatting the
    clause by hand and risking disagreement with this, the live shape."""
    shown = ", ".join(f"{vmid}:{device}" for vmid, device in missing[:5])
    more = f" (+{len(missing) - 5} more)" if len(missing) > 5 else ""
    return Finding(
        "warning",
        f"{name}: no series for {len(missing)} disk(s) that other configured metrics "
        f"do report ({shown}{more}) -- {_NUMERIC_DROP_HINT}",
    )


def _check_cross_metric_disk_consistency(
    keys_by_metric: dict[str, set[tuple[str, str]]],
) -> tuple[list[Finding], dict[str, tuple[tuple[str, str], ...]]]:
    """Flags a disk reported by *some* of the six configured metrics but not
    others -- normally impossible, since all six come from one Telegraf
    ``blockstat`` collection per disk (the same assumption
    :func:`compute_disk_coverage` relies on to check only ``read_ops``).
    The one common way it happens anyway: InfluxDB's line protocol fixes a
    field's type from its first write, and Telegraf's Prometheus-compatible
    output silently drops a field the instant it sees a non-numeric value
    for it -- Prometheus/OpenMetrics has no string sample type. That drop
    can hit one field for one disk without touching the other five, which
    is exactly the asymmetry this catches and ``compute_disk_coverage``
    alone (checking only ``read_ops``) cannot: if the dropped field happens
    not to be ``read_ops``, coverage looks perfect while a real gap sits in
    one of the other five. Costs nothing extra: every input set here is
    already fetched by ``_check_sample_series``'s own instant queries.

    Returns the findings *and* the full (untruncated) missing-disk lists by
    metric name -- :class:`VerifyMetricsReport` carries the latter as
    ``missing_disks_by_metric`` precisely so ``collect.py`` has the real
    ``(vmid, device)`` pairs to filter and re-format (Z-02), the same
    reason ``sample_series`` carries raw labels alongside the free-text
    "sample series labels" finding."""
    all_keys: set[tuple[str, str]] = set()
    for keys in keys_by_metric.values():
        all_keys |= keys
    findings: list[Finding] = []
    missing_by_metric: dict[str, tuple[tuple[str, str], ...]] = {}
    for name, keys in keys_by_metric.items():
        missing = sorted(all_keys - keys)
        if not missing:
            continue
        missing_by_metric[name] = tuple(missing)
        findings.append(format_cross_metric_finding(name, missing))
    return findings, missing_by_metric


def _check_sample_series(
    client: PrometheusClient, metrics: MetricsConfig
) -> tuple[list[Finding], dict[str, dict[str, str]], dict[str, tuple[tuple[str, str], ...]]]:
    """Section 3.3 step 2/3/4: one sample series per metric, with its labels."""
    findings: list[Finding] = []
    samples: dict[str, dict[str, str]] = {}
    labels = metrics.labels
    keys_by_metric: dict[str, set[tuple[str, str]]] = {}
    for field in RAW_METRIC_FIELDS:
        name = raw_metric_name(metrics, field)
        try:
            result = client.instant_query(name)
        except MetricsError as exc:
            findings.append(Finding("error", f"{name}: query failed: {exc}"))
            continue
        if not result:
            findings.append(
                Finding(
                    "warning",
                    f"{name}: no series returned -- no data yet, or {_NUMERIC_DROP_HINT}",
                )
            )
            continue
        sample_labels = result[0].get("metric", {})
        samples[name] = sample_labels
        keys_by_metric[name] = _disk_keys_seen(result, labels.vmid, labels.device)
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
    cross_metric_findings, missing_by_metric = _check_cross_metric_disk_consistency(keys_by_metric)
    findings.extend(cross_metric_findings)
    return findings, samples, missing_by_metric


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


def compute_disk_coverage(
    client: PrometheusClient,
    metrics: MetricsConfig,
    window: WindowConfig,
    selector: str | None = None,
    *,
    now: float | None = None,
) -> dict[DiskKey, float]:
    """Section 3.3 step 5 / section 3.4's ``min_coverage`` rule: per-disk
    sample coverage over the decision window, as a fraction in ``[0, 1]``.

    Uses ``read_ops`` as the representative metric: coverage gaps are a
    property of the underlying scrape, not of which of the six fields is
    read, and running six range queries here would be six times the load for
    no extra information. That assumption can break for one specific
    reason -- a non-numeric value silently dropping just one of the six
    fields for one disk, Telegraf/InfluxDB-side, independently of the other
    five (Prometheus/OpenMetrics has no string sample type) -- which is why
    ``_check_sample_series``'s :func:`_check_cross_metric_disk_consistency`
    cross-checks all six metrics' own disk sets against each other instead
    of trusting this one. Shared by ``verify-metrics``'s own report
    (:func:`_check_coverage` below) and ``loadmodel.py``'s per-disk
    data-quality gate (section 3.4: "reject a disk whose sample coverage...
    is below ``window.min_coverage``") -- one implementation of the
    computation, per AGENTS.md section 5, even though the two callers do
    different things with a low value (one reports it, the other falls back
    to a disk's last known load). Raises :class:`MetricsError` on a failed
    live query -- callers decide for themselves whether that is fatal or
    merely unknown-coverage. Can also raise :class:`~proxmox_storage_drs.exceptions.BundleError`
    under ``--replay``, but only for a bundle captured before
    :func:`safe_range_step_seconds` existed *and* whose own
    ``metrics.step``/``metrics.rate_window`` genuinely needs the
    workaround -- see that function's own try/except below, which also
    handles a bundle captured with ``collect-testdata --step`` overriding
    ``config.metrics.step`` for that one run (a
    :class:`~proxmox_storage_drs.exceptions.RangeStepMismatch`, distinct
    from the plain-``BundleError`` case).
    """
    metric_name = metrics.read_ops
    expr = build_rate_promql(
        metric_name,
        metrics.labels.vmid,
        metrics.labels.device,
        metrics.rate_window_seconds,
        selector=selector,
    )
    # Prometheus's query_range API takes absolute start/end (Unix time or
    # RFC3339), never an offset relative to "now" -- anchoring to a concrete
    # instant here is not optional. An unanchored negative value was
    # rejected outright by a live server during development; see the git
    # history for the fix. That instant defaults to the real wall clock
    # (correct for the live gate/verify-metrics callers) but collect.py
    # passes its own controlled capture instant instead, so a bundle's
    # captured range does not depend on the real time collect-testdata
    # happened to run at (section 16.1's determinism requirement).
    end = now if now is not None else time.time()
    start = end - window.lookback_seconds
    # safe_range_step_seconds(): a no-op against a correctly-behaving
    # backend, but works around a live-confirmed gigapipe bug where
    # query_range on a rate()-based expression returns zero series
    # whenever step >= rate_window -- exactly this project's own default
    # (both 300s). decimate_to_configured_step() below recovers the
    # expected_samples grid from whatever finer resolution this actually
    # queried at, so the coverage fraction stays correct either way.
    #
    # The try/except is `--replay` backward compatibility, not part of the
    # workaround itself: a *live* client never raises BundleError (only
    # ReplayPrometheusClient does, when a requested (query, step) pair was
    # never captured), so this is a no-op against a real cluster either
    # way. A bundle captured *before* this function existed has real data
    # at the plain `metrics.step` only -- collect.py now always captures
    # at the safe step when one is needed, so this fallback exists solely
    # to keep already-committed bundles (tests/corpus/bzed-dev-cluster-*)
    # replaying exactly as they did before this change.
    query_step = safe_range_step_seconds(metrics.step_seconds, metrics.rate_window_seconds)
    try:
        result = client.range_query(expr, start, end, query_step)
    except RangeStepMismatch as exc:
        # A --step override at capture time (recorded only in manifest.json's
        # capture.step_seconds, never in config.yaml) left this bundle's
        # range data at a step neither guess above derives from config
        # alone -- use the one the bundle actually has.
        query_step = exc.actual_step_seconds
        result = client.range_query(expr, start, end, query_step)
    except BundleError:
        if query_step == metrics.step_seconds:
            raise
        query_step = metrics.step_seconds
        result = client.range_query(expr, start, end, query_step)

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
        values = decimate_to_configured_step(
            series.get("values", []), metrics.step_seconds, query_step
        )
        actual_samples = len(values)
        coverage[key] = min(1.0, actual_samples / expected_samples)
    return coverage


def _check_coverage(
    client: PrometheusClient,
    metrics: MetricsConfig,
    window: WindowConfig,
    selector: str | None = None,
    now: float | None = None,
) -> tuple[list[Finding], dict[DiskKey, float]]:
    """Section 3.3 step 5: report which disks fall below ``window.min_coverage``."""
    try:
        coverage = compute_disk_coverage(client, metrics, window, selector=selector, now=now)
    except MetricsError as exc:
        return [Finding("error", f"coverage check failed: {exc}")], {}

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
        findings.append(Finding("warning", f"{metrics.read_ops}: no series to measure coverage on"))
    return findings, coverage


def _check_observed_spacing(
    client: PrometheusClient,
    metrics: MetricsConfig,
    selector: str | None = None,
    now: float | None = None,
) -> tuple[list[Finding], float | None]:
    """Section 3.3 step 6: observed sample spacing vs. ``pvestatd_push_interval``.

    Measures the modal delta between consecutive timestamps of one live
    series over a short recent range, since that is what the ``rate_window
    >= 4x`` rule (section 11.1) is actually protecting.

    ``now`` defaults to the real wall clock (``time.time()``), correct for
    the live ``verify-metrics`` command; ``collect.py`` passes its own
    controlled capture instant instead, so this probe's window -- and thus
    the bundle byte it produces -- does not depend on the real time a
    capture happened to run at (section 16.1's determinism requirement).
    """
    metric_name = metrics.read_ops
    if selector:
        metric_name = f"{metric_name}{{{selector}}}"
    probe_window_seconds = max(metrics.pvestatd_push_interval_seconds * 20, 600.0)
    end = now if now is not None else time.time()
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
    client: PrometheusClient,
    metrics: MetricsConfig,
    window: WindowConfig,
    *,
    now: float | None = None,
) -> VerifyMetricsReport:
    """Run every section 3.3 check and assemble the report.

    Must be run before relying on any plan (section 3.3); ``cli.py``'s
    ``verify-metrics`` command is this function plus formatting. ``now``
    is forwarded to :func:`_check_observed_spacing` -- see its docstring;
    the live command leaves it as the real wall clock.
    """
    # `verify-metrics` never talks to the PVE API (`resolve_node_selector()`'s
    # own docstring), so only an explicit `metrics.extra_selector` narrows
    # these checks -- the auto-derived node filter needs a live node list
    # `plan`/`show-load`/`apply`/`explain` already have from building their
    # own topology, which this command deliberately does not build.
    selector = resolve_node_selector(metrics, None)
    findings: list[Finding] = []
    findings.extend(_check_metric_names_exist(client, metrics))
    sample_findings, samples, missing_disks_by_metric = _check_sample_series(client, metrics)
    findings.extend(sample_findings)
    collision = _check_device_label_collision(metrics)
    if collision is not None:
        findings.append(collision)
    coverage_findings, coverage = _check_coverage(
        client, metrics, window, selector=selector, now=now
    )
    findings.extend(coverage_findings)
    spacing_findings, spacing = _check_observed_spacing(client, metrics, selector=selector, now=now)
    findings.extend(spacing_findings)

    return VerifyMetricsReport(
        findings=tuple(findings),
        sample_series=samples,
        coverage_by_disk=coverage,
        observed_spacing_seconds=spacing,
        missing_disks_by_metric=missing_disks_by_metric,
    )
