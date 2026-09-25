# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Holt-Winters load forecasting. See IMPLEMENTATION_PLAN.md sections 10 and 12.1.

The decision statistic behind every placement is ``window.quantile`` (p95) of a
disk's load. The default ``quantile`` model takes it over the *last*
``W = window.lookback``; ``holt_winters`` predicts it over the *next* ``W``: fit
the disk's series, forecast ``ceil(W / step)`` steps, take ``window.quantile`` of
that forecast path, clamp at 0. It is **not** the last forecast point (one sample
at one hour of day says nothing about tomorrow's peak) and there is **no** ``z *
sigma`` band (a forecast p95 is compared with its quantile-model peers' observed
p95, and a residual band would inflate exactly the disks that were forecast).

The forecast never replaces a load, it scales it: ``loadmodel.apply_forecast()``
multiplies a disk's ``l_d`` by ``f_d / h_d`` -- the forecast p95 over the observed
p95 of the same series -- because the per-timestamp series and the window-level
``l_d`` are normalized differently. This module is pure: series in, numbers out.

Holt-Winters is used for a group only if a backtest says it beats the trivial
baseline (persist the last window's p95) on that group's own recent past -- no
threshold, just "not worse than doing nothing clever".

``statsmodels`` is an optional dependency (IMPLEMENTATION_PLAN.md section 2.1) and
is imported only inside :func:`holt_winters_quantile`, never at module level -- the
autopkgtest in ``debian/tests/import-all`` is what catches a regression here.
"""

from __future__ import annotations

import logging
import math
import warnings
from dataclasses import dataclass
from typing import Any, Collection, Mapping, Sequence

from proxmox_storage_drs.config import ForecastConfig, HoltWintersConfig

logger = logging.getLogger(__name__)

# A time series is a list of (unix_timestamp_seconds, value) pairs, sorted
# ascending by timestamp. `value` is the section 4 load ``l_d`` (or a group sum).
TimeSeries = Sequence[tuple[float, float]]


def _quantile(values: Sequence[float], q: float) -> float:
    """Linear-interpolation quantile, matching ``numpy.percentile``'s default.

    Implemented without numpy so the quantile path stays usable with no
    forecast extra installed (section 2.1: "the tool must run, plan and execute
    with only requests + ruamel.yaml + jsonschema installed").
    """
    if not values:
        raise ValueError("cannot take a quantile of an empty sequence")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = q * (len(ordered) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = rank - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def required_range_seconds(
    forecast: ForecastConfig, lookback_seconds: float, step_seconds: float
) -> float:
    """The history ``forecast.model`` needs, in seconds.

    Called by ``config.py``'s startup validation (section 11.1:
    ``window.lookback >= required``) and by ``collect.py``'s capture range, so
    the rule exists exactly once. ``holt_winters`` needs two full seasonal
    cycles; the backtest additionally fits on a window-long half, which is why
    the same figure is also a floor on ``window.lookback`` itself.
    """
    if forecast.model == "quantile":
        return lookback_seconds
    if forecast.model == "holt_winters":
        return max(lookback_seconds, 2 * forecast.holt_winters.seasonal_periods * step_seconds)
    raise ValueError(
        f"unknown forecast.model {forecast.model!r}"
    )  # pragma: no cover - schema-guarded


def holt_winters_quantile(
    series: TimeSeries,
    hw: HoltWintersConfig,
    step_seconds: float,
    horizon_seconds: float,
    quantile: float,
) -> float | None:
    """``window.quantile`` of the Holt-Winters forecast path over the next
    ``horizon_seconds``, clamped at 0 -- or ``None`` when no trustworthy fit is
    possible: fewer than ``2 * seasonal_periods`` samples, a constant series,
    ``statsmodels`` not installed, any exception from the fit, a
    ``ConvergenceWarning``, or a non-finite forecast. ``None`` always means "use
    the observed load unchanged", never "zero".
    """
    values = [v for _, v in series]
    if len(values) < 2 * hw.seasonal_periods or len(set(values)) < 2:
        return None
    try:
        from statsmodels.tools.sm_exceptions import ConvergenceWarning
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
    except ImportError:
        logger.debug(
            "holt_winters: statsmodels is not installed", extra={"event": "forecast_fit_skipped"}
        )
        return None

    steps = max(1, math.ceil(horizon_seconds / step_seconds))
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", ConvergenceWarning)
            model = ExponentialSmoothing(
                values,
                trend=None if hw.trend == "none" else hw.trend,
                seasonal=None if hw.seasonal == "none" else hw.seasonal,
                seasonal_periods=hw.seasonal_periods,
                # Initial level/trend/seasonals from a classical decomposition
                # of the first cycles; only the smoothing parameters are
                # optimized. "estimated" also optimizes every initial seasonal
                # and fails to converge at 288 periods on real data.
                initialization_method="heuristic",
            )
            path = [float(x) for x in model.fit().forecast(steps)]
    except Exception as exc:  # statsmodels raises ValueError, LinAlgError, ... -- all mean "no fit"
        logger.debug("holt_winters fit failed: %s", exc, extra={"event": "forecast_fit_failed"})
        return None
    if not path or not all(math.isfinite(x) for x in path):
        return None
    return max(0.0, _quantile(path, quantile))


@dataclass(frozen=True, slots=True)
class Backtest:
    """One group's backtest: absolute error of each model's predicted p95 of
    ``[now-W, now]``. ``hw_error`` is ``None`` when Holt-Winters could not be
    fitted on ``[now-2W, now-W)``."""

    hw_error: float | None
    baseline_error: float

    @property
    def passed(self) -> bool:
        return self.hw_error is not None and self.hw_error <= self.baseline_error


def group_aggregate_series(disk_series: Mapping[str, TimeSeries]) -> TimeSeries:
    """Sum every disk's own series into one group-aggregate series, at the union
    of every timestamp seen across all of them (a timestamp missing from one
    disk's own series contributes 0 for it, the same "absence means no I/O"
    convention :func:`~proxmox_storage_drs.loadmodel._blend_loads` already uses).
    The backtest is run once per group against this aggregate: ``forecast.model``
    is a single configuration choice, never something that differs disk by disk."""
    per_disk_lookup = {key: dict(series) for key, series in disk_series.items()}
    timestamps: set[float] = set()
    for series in disk_series.values():
        timestamps.update(ts for ts, _v in series)
    return tuple(
        (ts, sum(lookup.get(ts, 0.0) for lookup in per_disk_lookup.values()))
        for ts in sorted(timestamps)
    )


def backtest(
    series: TimeSeries,
    now_epoch_seconds: float,
    window_seconds: float,
    step_seconds: float,
    hw: HoltWintersConfig,
    quantile: float,
) -> Backtest | None:
    """Section 10.2's backtest, comparing against a baseline: fit on
    ``[now-2W, now-W)`` and have both models predict the p95 of ``[now-W, now]``.
    The baseline's prediction is the p95 of the fit half itself (persistence, what
    the ``quantile`` model would have said). Returns ``None`` when ``series`` does
    not have a non-empty half on each side of ``now - W`` -- "not enough history
    yet" is treated by the caller like a failed backtest, never as a free pass."""
    fit_start = now_epoch_seconds - 2 * window_seconds
    split = now_epoch_seconds - window_seconds
    fit = tuple((ts, v) for ts, v in series if fit_start <= ts < split)
    actual = [v for ts, v in series if split <= ts <= now_epoch_seconds]
    if not fit or not actual:
        return None
    observed = _quantile(actual, quantile)
    baseline = _quantile([v for _, v in fit], quantile)
    predicted = holt_winters_quantile(fit, hw, step_seconds, window_seconds, quantile)
    return Backtest(
        hw_error=None if predicted is None else abs(predicted - observed),
        baseline_error=abs(baseline - observed),
    )


def disk_factors(
    disk_series: Mapping[str, TimeSeries],
    skip: Collection[str],
    now_epoch_seconds: float,
    window_seconds: float,
    step_seconds: float,
    hw: HoltWintersConfig,
    quantile: float,
) -> dict[str, float]:
    """``f_d / h_d`` for every disk that has one: ``f_d`` the Holt-Winters
    forecast p95 over the next ``window_seconds`` (fitted on the disk's whole
    series), ``h_d`` the observed p95 over ``[now-W, now]`` of the same series. A
    disk is left out -- its load stays as observed -- when it is in ``skip``
    (flagged for low coverage), has no samples in the window, has ``h_d = 0``, or
    has no trustworthy fit."""
    window_start = now_epoch_seconds - window_seconds
    factors: dict[str, float] = {}
    for key, series in disk_series.items():
        if key in skip:
            continue
        recent = [v for ts, v in series if window_start <= ts <= now_epoch_seconds]
        if not recent:
            continue
        observed = _quantile(recent, quantile)
        if observed <= 0:
            continue
        forecast = holt_winters_quantile(series, hw, step_seconds, window_seconds, quantile)
        if forecast is None:
            continue
        factors[key] = forecast / observed
    return factors


@dataclass(frozen=True, slots=True)
class ForecastReport:
    """What one group's forecast did this run -- the ``forecast`` block of
    ``explain`` and ``plan --json`` (section 12.1 point 6). ``used`` is whether
    Holt-Winters drove the group's loads (the backtest passed); ``disks_scaled``
    and ``disks_kept`` partition the group's disks."""

    model: str
    used: bool
    backtest_error: float | None
    baseline_error: float | None
    disks_scaled: int
    disks_kept: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "used": self.used,
            "backtest_error": self.backtest_error,
            "baseline_error": self.baseline_error,
            "disks_scaled": self.disks_scaled,
            "disks_kept": self.disks_kept,
        }


def forecast_group(
    disk_series: Mapping[str, TimeSeries],
    skip: Collection[str],
    forecast: ForecastConfig,
    now_epoch_seconds: float,
    window_seconds: float,
    step_seconds: float,
    quantile: float,
) -> tuple[dict[str, float], ForecastReport]:
    """One group's forecast: run the backtest on the group aggregate, and only if
    Holt-Winters beats the baseline compute each disk's scaling factor. Returns
    ``({disk_key: f_d / h_d}, report)``; the factors are empty when the backtest
    fails or cannot run, and the caller then keeps every load as observed."""
    hw = forecast.holt_winters
    result = backtest(
        group_aggregate_series(disk_series),
        now_epoch_seconds,
        window_seconds,
        step_seconds,
        hw,
        quantile,
    )
    total = len(disk_series)
    if result is None or not result.passed:
        report = ForecastReport(
            model=forecast.model,
            used=False,
            backtest_error=None if result is None else result.hw_error,
            baseline_error=None if result is None else result.baseline_error,
            disks_scaled=0,
            disks_kept=total,
        )
        return {}, report
    factors = disk_factors(
        disk_series, skip, now_epoch_seconds, window_seconds, step_seconds, hw, quantile
    )
    report = ForecastReport(
        model=forecast.model,
        used=True,
        backtest_error=result.hw_error,
        baseline_error=result.baseline_error,
        disks_scaled=len(factors),
        disks_kept=total - len(factors),
    )
    return factors, report
