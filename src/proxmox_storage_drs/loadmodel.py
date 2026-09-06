# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reduce raw per-disk metrics to the scalar load vector `ℓ`. See
IMPLEMENTATION_PLAN.md section 4.

This module fetches nothing about topology and never talks to the PVE API --
it takes an already-built ``topology.Group`` (one group's `D`/`S`) and a
``metrics.PrometheusClient``, and produces one load value per disk plus the
per-storage `L_s`/`u_s` and group-wide `u*` that ``show-load`` and the
gates/solver (not yet written) need. Every quantity here is in **average
in-flight I/O requests** unless documented otherwise -- section 4 is
explicit that the rescale back onto that absolute scale is not cosmetic:
everything downstream (the saturation guard, the big-M bound, the objective
weights) is calibrated against it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from proxmox_storage_drs.config import LoadWeights, MetricsConfig, WindowConfig
from proxmox_storage_drs.forecast import TimeSeries
from proxmox_storage_drs.metrics import (
    RAW_METRIC_FIELDS,
    DiskKey,
    PrometheusClient,
    build_quantile_over_time_promql,
    build_rate_promql,
    compute_disk_coverage,
    parse_disk_range_series,
    parse_disk_series,
    raw_metric_name,
)
from proxmox_storage_drs.topology import Group

# Section 3.4's own note: "tpmstate0 and unused{N} are not QEMU block
# devices, so no series will exist for them and ℓ_d = 0 under the
# min_coverage rule... that is correct rather than a gap." A disk of one of
# these device kinds is never rejected/flagged for low coverage -- its true
# load is legitimately (not just apparently) zero. efidisk0 *is* a QEMU
# drive and should appear in blockstat, so it is not in this set and is
# held to the same coverage bar as scsi/virtio/ide/sata.
_METRICS_EXPECTED_ABSENT_PREFIXES = ("unused",)
_METRICS_EXPECTED_ABSENT_EXACT = frozenset({"tpmstate0"})


def _is_metrics_expected_absent(device: str) -> bool:
    if device in _METRICS_EXPECTED_ABSENT_EXACT:
        return True
    return device.startswith(_METRICS_EXPECTED_ABSENT_PREFIXES)


@dataclass(frozen=True, slots=True)
class DiskLoad:
    """One disk's `ℓ_d`. Section 4."""

    disk_key: str  # topology.Disk.key ("vmid:device")
    load: float
    # None: a normal, trusted measurement. Otherwise section 3.4's
    # min_coverage rule fired -- `load` is either a state.json-recorded
    # last known value (not yet wired through; see the module docstring
    # note below `compute_group_load`) or 0.0, and this says which so a
    # caller never mistakes a flagged 0.0 for a genuinely idle disk.
    flagged_reason: str | None


@dataclass(frozen=True, slots=True)
class StorageLoad:
    """One storage's current `L_s`/`u_s`, at the assignment `Disk.current_storage`
    already encodes -- not a candidate assignment (that is the solver's job,
    not yet written), matching ``reserve.py``'s identical "current state"
    framing."""

    storage_id: str
    load: float  # L_s = Sum_d l_d over disks currently on this storage
    utilization: float  # u_s = L_s / c_s


@dataclass(frozen=True, slots=True)
class GroupLoad:
    """One group's whole load picture for this run. Section 4/6."""

    group_name: str
    # Section 4: "if T_g = 0 the entire group is idle -- skip it, there is
    # nothing to balance." True only when every *accepted* (not
    # coverage-rejected) disk's raw in-flight I/O is zero -- see
    # `compute_group_load`'s docstring for why an all-rejected group is
    # deliberately reported the same way (safe: "unknown" and "idle" both
    # mean "don't act").
    idle: bool
    average_utilization: float  # u* = (Sum_d l_d) / (Sum_s c_s), section 5.3 (C6)
    disks: tuple[DiskLoad, ...]
    storages: tuple[StorageLoad, ...]

    def load_by_disk_key(self) -> dict[str, float]:
        """Convenience for callers (``show-load``) keying off `Disk.key`."""
        return {d.disk_key: d.load for d in self.disks}


def _fetch_raw_quantity(
    client: PrometheusClient, metrics: MetricsConfig, window: WindowConfig, field: str
) -> dict[DiskKey, float]:
    """One of the six section 3.4 raw quantities, quantile-reduced over the
    decision window, for every disk Prometheus currently reports -- not
    filtered to one group, since a single query covering everything is one
    call instead of one per group and Python-side filtering by `DiskKey` is
    free."""
    metric_name = raw_metric_name(metrics, field)
    rate_expr = build_rate_promql(
        metric_name, metrics.labels.vmid, metrics.labels.device, metrics.rate_window_seconds
    )
    promql = build_quantile_over_time_promql(
        rate_expr, window.quantile, window.lookback_seconds, metrics.step_seconds
    )
    result = client.instant_query(promql)
    return parse_disk_series(result, metrics.labels.vmid, metrics.labels.device)


@dataclass(frozen=True, slots=True)
class _RawQuantities:
    """The six section 3.4 series, fetched once and reused for every disk."""

    read_ops: dict[DiskKey, float]
    write_ops: dict[DiskKey, float]
    read_bytes: dict[DiskKey, float]
    write_bytes: dict[DiskKey, float]
    read_time_ns: dict[DiskKey, float]
    write_time_ns: dict[DiskKey, float]


def _fetch_all_raw_quantities(
    client: PrometheusClient, metrics: MetricsConfig, window: WindowConfig
) -> _RawQuantities:
    fetched = {
        field: _fetch_raw_quantity(client, metrics, window, field) for field in RAW_METRIC_FIELDS
    }
    return _RawQuantities(**fetched)


#: :func:`parse_disk_range_series`'s own concrete value type -- used here
#: instead of :data:`~proxmox_storage_drs.forecast.TimeSeries` (a
#: ``Sequence``) purely because ``dict`` is invariant in its value type;
#: any :class:`_RawTimeSeries` is already a valid ``TimeSeries`` wherever
#: one is expected (:func:`compute_disk_load_series`'s own return type).
_RawTimeSeries = tuple[tuple[float, float], ...]


def _fetch_raw_quantity_series(
    client: PrometheusClient,
    metrics: MetricsConfig,
    field: str,
    start_epoch_seconds: float,
    end_epoch_seconds: float,
    step_seconds: float,
) -> dict[DiskKey, _RawTimeSeries]:
    """One of the six section 3.4 raw quantities as a raw time series over
    ``[start, end]`` at ``step`` -- section 10's own material for a
    :class:`~proxmox_storage_drs.forecast.Forecaster`, as opposed to
    :func:`_fetch_raw_quantity`'s single quantile-reduced scalar for the
    decision statistic. The identical ``rate(...)`` expression
    :func:`_fetch_raw_quantity` builds, `query_range`'d instead of wrapped
    in `quantile_over_time` and `instant_query`'d -- not a second PromQL
    formula, only a different query type against the same expression."""
    metric_name = raw_metric_name(metrics, field)
    rate_expr = build_rate_promql(
        metric_name, metrics.labels.vmid, metrics.labels.device, metrics.rate_window_seconds
    )
    result = client.range_query(rate_expr, start_epoch_seconds, end_epoch_seconds, step_seconds)
    return parse_disk_range_series(result, metrics.labels.vmid, metrics.labels.device)


@dataclass(frozen=True, slots=True)
class _RawSeriesQuantities:
    """The six section 3.4 series, as time series -- :class:`_RawQuantities`'
    own counterpart for :func:`compute_disk_load_series`."""

    read_ops: dict[DiskKey, _RawTimeSeries]
    write_ops: dict[DiskKey, _RawTimeSeries]
    read_bytes: dict[DiskKey, _RawTimeSeries]
    write_bytes: dict[DiskKey, _RawTimeSeries]
    read_time_ns: dict[DiskKey, _RawTimeSeries]
    write_time_ns: dict[DiskKey, _RawTimeSeries]


def _fetch_all_raw_quantity_series(
    client: PrometheusClient,
    metrics: MetricsConfig,
    start_epoch_seconds: float,
    end_epoch_seconds: float,
    step_seconds: float,
) -> _RawSeriesQuantities:
    fetched = {
        field: _fetch_raw_quantity_series(
            client, metrics, field, start_epoch_seconds, end_epoch_seconds, step_seconds
        )
        for field in RAW_METRIC_FIELDS
    }
    return _RawSeriesQuantities(**fetched)


def _combine_raw_values(
    read_time_ns: float,
    write_time_ns: float,
    read_ops: float,
    write_ops: float,
    read_bytes: float,
    write_bytes: float,
    load_weights: LoadWeights,
) -> tuple[float, float, float]:
    """`(raw_t, raw_o, raw_b)` for one disk **at one instant**, section 4:
    ``raw_t/o/b(d) = rho*rd_X(d) + omega*wr_X(d)``, read and write combined
    *before* normalization using the configured asymmetry factors.
    ``raw_time_ns`` is converted to seconds here (section 3.4's PromQL
    divides by 1e9 inline; this project applies that conversion
    engine-side instead, for the same reason F-03 moved
    read_factor/write_factor engine-side: one tested unit conversion beats
    the same constant repeated across deployed query strings).

    Takes plain numbers, not a whole raw-quantities structure, so it is
    the one implementation (AGENTS.md section 5) both `_combined_raw()`
    (one call per disk, from a single scalar snapshot) and
    `compute_disk_load_series()` (one call per disk *per timestamp*, from
    a time series) share -- the same rule, evaluated at a different
    number of instants."""
    rho, omega = load_weights.read_factor, load_weights.write_factor
    raw_t = (rho * read_time_ns + omega * write_time_ns) / 1e9
    raw_o = rho * read_ops + omega * write_ops
    raw_b = rho * read_bytes + omega * write_bytes
    return raw_t, raw_o, raw_b


def _combined_raw(
    key: DiskKey, raw: _RawQuantities, load_weights: LoadWeights
) -> tuple[float, float, float]:
    """`(raw_t, raw_o, raw_b)` for one disk, section 4 -- see
    :func:`_combine_raw_values`. A key absent from a series (no data at
    all, e.g. an idle disk or a tpmstate0/unusedN device -- section 3.4's
    note) contributes 0, not a missing-key error: `.get(key, 0.0)` is
    deliberate here, not a shortcut -- absence is exactly what "no I/O
    this window" looks like for a disk that genuinely has none."""
    return _combine_raw_values(
        raw.read_time_ns.get(key, 0.0),
        raw.write_time_ns.get(key, 0.0),
        raw.read_ops.get(key, 0.0),
        raw.write_ops.get(key, 0.0),
        raw.read_bytes.get(key, 0.0),
        raw.write_bytes.get(key, 0.0),
        load_weights,
    )


def _blend_loads(
    raw_by_key: Mapping[str, tuple[float, float, float]], load_weights: LoadWeights
) -> dict[str, float]:
    """Section 4's normalize-then-weight-then-rescale blend, given every
    key's own already-combined `(raw_t, raw_o, raw_b)` for one instant:
    the group totals, then per-key normalized shares, then the weighted
    blend rescaled back onto the in-flight-I/O scale
    (``T_g * blend``). Shared by `compute_group_load()` (called once,
    over its `accepted_raw` scalar snapshot) and
    `compute_disk_load_series()` (called once per timestamp) -- the one
    implementation of the formula itself (AGENTS.md section 5); only how
    many times it is invoked differs between a scalar snapshot and a time
    series. Guards every division exactly as section 4 requires: a zero
    group total for one term means that term contributes 0 for every key,
    never `NaN`."""
    t_total = sum(t for t, _o, _b in raw_by_key.values())
    o_total = sum(o for _t, o, _b in raw_by_key.values())
    b_total = sum(b for _t, _o, b in raw_by_key.values())
    w_t, w_o, w_b = load_weights.iotime, load_weights.ops, load_weights.bytes
    weight_sum = w_t + w_o + w_b
    result: dict[str, float] = {}
    for key, (raw_t, raw_o, raw_b) in raw_by_key.items():
        i_d = raw_t / t_total if t_total else 0.0
        o_d = raw_o / o_total if o_total else 0.0
        b_d = raw_b / b_total if b_total else 0.0
        blended = (w_t * i_d + w_o * o_d + w_b * b_d) / weight_sum if weight_sum else 0.0
        result[key] = t_total * blended
    return result


def compute_group_load(
    client: PrometheusClient,
    metrics: MetricsConfig,
    window: WindowConfig,
    load_weights: LoadWeights,
    group: Group,
    last_known_loads: Mapping[str, float] | None = None,
) -> GroupLoad:
    """Compute one group's :class:`GroupLoad` for this run. Section 4.

    ``last_known_loads`` is section 3.4's "fall back to its last known load
    from ``state.json``" -- keyed by ``Disk.key``. Pass ``None`` (the
    default) until ``state.json`` persistence exists (not yet written; see
    IMPLEMENTATION_PLAN.md section 11.2): a disk that fails the
    ``min_coverage`` check with no entry here is flagged with load ``0.0``
    rather than silently accepted as zero -- the "never treat missing data
    as zero load" rule (section 3.4) is about not *pretending* an unknown
    load is zero, not about refusing to run before ``state.json`` exists;
    callers must check ``DiskLoad.flagged_reason``, not just filter it out.

    Coverage rejection excludes a disk's raw contribution from its group's
    normalization totals entirely, so one noisy or half-missing series
    cannot bias every other disk's normalized share -- the rejected disk's
    own `ℓ_d` is then substituted from ``last_known_loads`` (or flagged
    0.0), independent of the group blend.
    """
    if not group.disks:
        return GroupLoad(
            group_name=group.name, idle=True, average_utilization=0.0, disks=(), storages=()
        )

    coverage = compute_disk_coverage(client, metrics, window)
    raw = _fetch_all_raw_quantities(client, metrics, window)
    fallback = last_known_loads or {}

    accepted_raw: dict[str, tuple[float, float, float]] = {}
    rejected: dict[str, str] = {}  # disk key -> reason
    for disk in group.disks:
        key = DiskKey(vmid=disk.vmid, device=disk.device)
        fraction = coverage.get(key, 0.0)
        if fraction < window.min_coverage and not _is_metrics_expected_absent(disk.device):
            rejected[disk.key] = (
                f"sample coverage {fraction:.0%} is below window.min_coverage "
                f"({window.min_coverage:.0%})"
            )
            continue
        accepted_raw[disk.key] = _combined_raw(key, raw, load_weights)

    t_total = sum(t for t, _o, _b in accepted_raw.values())
    blended_by_key = _blend_loads(accepted_raw, load_weights)

    disk_loads: list[DiskLoad] = []
    for disk in group.disks:
        if disk.key in rejected:
            if disk.key in fallback:
                disk_loads.append(
                    DiskLoad(
                        disk_key=disk.key,
                        load=fallback[disk.key],
                        flagged_reason=f"{rejected[disk.key]}; using last known load",
                    )
                )
            else:
                disk_loads.append(
                    DiskLoad(
                        disk_key=disk.key,
                        load=0.0,
                        flagged_reason=f"{rejected[disk.key]}; no last known load recorded",
                    )
                )
            continue

        disk_loads.append(
            DiskLoad(disk_key=disk.key, load=blended_by_key[disk.key], flagged_reason=None)
        )

    load_by_key = {d.disk_key: d.load for d in disk_loads}
    storage_loads: list[StorageLoad] = []
    total_load = 0.0
    total_capability = 0.0
    for storage in group.storages:
        storage_load = sum(
            load_by_key[d.key] for d in group.disks if d.current_storage == storage.id
        )
        utilization = storage_load / storage.capability_weight if storage.capability_weight else 0.0
        storage_loads.append(
            StorageLoad(storage_id=storage.id, load=storage_load, utilization=utilization)
        )
        total_load += storage_load
        total_capability += storage.capability_weight

    average_utilization = total_load / total_capability if total_capability else 0.0

    return GroupLoad(
        group_name=group.name,
        idle=t_total == 0.0,
        average_utilization=average_utilization,
        disks=tuple(disk_loads),
        storages=tuple(storage_loads),
    )


def _per_disk_lookup(disk_key: DiskKey, raw: _RawSeriesQuantities) -> dict[str, dict[float, float]]:
    """One disk's six raw series, each turned into a ``{timestamp: value}``
    lookup for :func:`compute_disk_load_series`'s per-timestamp blend --
    factored out purely so that function's own loop stays within this
    project's flake8 complexity limit."""
    return {
        "rt": dict(raw.read_time_ns.get(disk_key, ())),
        "wt": dict(raw.write_time_ns.get(disk_key, ())),
        "ro": dict(raw.read_ops.get(disk_key, ())),
        "wo": dict(raw.write_ops.get(disk_key, ())),
        "rb": dict(raw.read_bytes.get(disk_key, ())),
        "wb": dict(raw.write_bytes.get(disk_key, ())),
    }


def compute_disk_load_series(
    client: PrometheusClient,
    metrics: MetricsConfig,
    load_weights: LoadWeights,
    group: Group,
    range_seconds: float,
    step_seconds: float,
    now_epoch_seconds: float,
) -> dict[str, TimeSeries]:
    """Section 4's `ℓ_d` blend, as a time series per disk over
    ``[now - range_seconds, now]`` at ``step_seconds`` -- the raw material
    a section 10 :class:`~proxmox_storage_drs.forecast.Forecaster` needs,
    as opposed to :func:`compute_group_load`'s single p95-reduced scalar
    per disk for the decision statistic. ``range_seconds``/``step_seconds``
    are the caller's own choice (typically
    ``forecast.required_range_seconds()``/``metrics.step_seconds`` -- see
    ``payback.py``'s section 7.3 saturation guard, the one caller today),
    not fixed to ``window.lookback`` the way :func:`compute_group_load`
    is: section 10.1 is explicit that a forecaster's own history
    requirement and the decision window are "genuinely different things."

    Every disk in ``group`` gets an entry, even one with no samples at all
    (an empty series -- every :class:`~proxmox_storage_drs.forecast.Forecaster`
    already handles that, returning a zero forecast, per its own
    docstring), never a ``KeyError`` for a caller iterating ``group.disks``.
    Deliberately **not** filtered by ``window.min_coverage`` the way
    :func:`compute_group_load`'s decision-window scalar is: a forecaster's
    own ``required_range()`` is typically a much longer, coarser signal
    (up to 7 days for ``seasonal_naive``) than that coverage rule was
    designed to validate over one 24h decision window, and a genuinely
    sparse history is exactly what a forecaster needs to see for itself in
    order to decide it cannot trust its own fit -- silently dropping those
    samples here would hide that from it instead.
    """
    if not group.disks:
        return {}

    end = now_epoch_seconds
    start = end - range_seconds
    raw = _fetch_all_raw_quantity_series(client, metrics, start, end, step_seconds)

    timestamps: set[float] = set()
    for field_series in (
        raw.read_ops,
        raw.write_ops,
        raw.read_bytes,
        raw.write_bytes,
        raw.read_time_ns,
        raw.write_time_ns,
    ):
        for series in field_series.values():
            timestamps.update(ts for ts, _v in series)

    disk_keys = {d.key: DiskKey(vmid=d.vmid, device=d.device) for d in group.disks}
    lookups = {d_key: _per_disk_lookup(prom_key, raw) for d_key, prom_key in disk_keys.items()}

    result: dict[str, list[tuple[float, float]]] = {d_key: [] for d_key in disk_keys}
    for ts in sorted(timestamps):
        raw_by_key: dict[str, tuple[float, float, float]] = {}
        for d_key, lut in lookups.items():
            raw_by_key[d_key] = _combine_raw_values(
                lut["rt"].get(ts, 0.0),
                lut["wt"].get(ts, 0.0),
                lut["ro"].get(ts, 0.0),
                lut["wo"].get(ts, 0.0),
                lut["rb"].get(ts, 0.0),
                lut["wb"].get(ts, 0.0),
                load_weights,
            )
        blended = _blend_loads(raw_by_key, load_weights)
        for d_key, value in blended.items():
            result[d_key].append((ts, value))

    return {d_key: tuple(points) for d_key, points in result.items()}
