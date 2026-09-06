# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pluggable load forecasting. See IMPLEMENTATION_PLAN.md section 10.

The optimizer and the section 7.3 saturation guard consume the **upper
bound**, never the point estimate (section 10.1): being wrong in the
direction of "busier than it looks" costs a slightly suboptimal balance,
being wrong the other way risks migrating a disk onto a storage that is
about to saturate.

Each forecaster owns its own required history (section 10.1's table) because
the *decision* window (``window.lookback``) and the *history a model needs*
are genuinely different things -- conflating them makes Holt-Winters
unreachable, since its 48h requirement can never be satisfied by a 24h
decision window. :func:`required_range_seconds` is the pure function
``config.py`` calls during startup validation (section 11.1); each
forecaster class calls the same function so there is exactly one place that
knows the rule (AGENTS.md section 5).

``statsmodels`` (the Holt-Winters backend) is an optional dependency
(IMPLEMENTATION_PLAN.md section 2.1) and is therefore imported only inside
:meth:`HoltWintersForecaster.predict`, never at module level -- the
autopkgtest in ``debian/tests/import-all`` is what catches a regression here.
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass
from datetime import timedelta
from typing import Iterable, Mapping, Protocol, Sequence

from proxmox_storage_drs.config import ForecastConfig

logger = logging.getLogger(__name__)

# A time series is a list of (unix_timestamp_seconds, value) pairs, sorted
# ascending by timestamp. `value` is whatever the caller is forecasting --
# typically a raw PromQL series or the section 4 load ``ℓ_d``.
TimeSeries = Sequence[tuple[float, float]]


@dataclass(frozen=True, slots=True)
class Forecast:
    """A point estimate and an upper bound over a horizon.

    Both are in the same unit as the input series (section 4: average
    in-flight I/O requests, when forecasting load). The optimizer and section
    7.3's saturation guard must use ``upper_bound``, never ``point_estimate``.
    """

    point_estimate: float
    upper_bound: float


class Forecaster(Protocol):
    """See IMPLEMENTATION_PLAN.md section 10's Forecaster protocol."""

    def required_range(self) -> timedelta:
        """How much history this model needs. ``metrics.py`` serves exactly this."""
        ...  # pragma: no cover - Protocol method body is never executed

    def predict(self, series: TimeSeries, horizon: timedelta) -> Forecast:
        """Return a point estimate and an upper bound for ``horizon``."""
        ...  # pragma: no cover - Protocol method body is never executed


def storage_upper_bound(
    forecaster: Forecaster,
    disk_load_series: Mapping[str, TimeSeries],
    disk_keys: Iterable[str],
    horizon: timedelta,
) -> float:
    """Section 10.1: ``L̂_s(Δ) = Σ_{d : x_{d,s}=1} û_d(Δ)`` -- every given
    disk's own upper bound, forecast independently from its own series,
    summed. Summing upper bounds (rather than forecasting the storage's
    own already-summed series directly) is deliberately conservative: it
    assumes every disk peaks together, the right direction for a guard
    whose failure mode is starting a mirror onto an already-busy array
    (section 10.1's own words). A ``disk_keys`` entry missing from
    ``disk_load_series`` (no data fetched for it at all) forecasts an
    empty series -- every :class:`Forecaster` already returns a zero
    :class:`Forecast` for that, per its own docstring, so this never
    raises a ``KeyError`` for a disk this run simply has no history for
    yet."""
    return sum(
        forecaster.predict(disk_load_series.get(key, ()), horizon).upper_bound for key in disk_keys
    )


def _quantile(values: Sequence[float], q: float) -> float:
    """Linear-interpolation quantile, matching ``numpy.percentile``'s default.

    Implemented without numpy so the heuristic/quantile path stays usable
    with no forecast extra installed (section 2.1: "the tool must run, plan
    and execute with only requests + ruamel.yaml + jsonschema installed").
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


# --------------------------------------------------------- required ranges
#
# One pure function per model, each the single source of truth for that
# model's history requirement; required_range_seconds() and every
# Forecaster.required_range() below call these, never re-derive them.


def _quantile_required_range_seconds(lookback_seconds: float) -> float:
    return lookback_seconds


def _seasonal_naive_required_range_seconds(
    lookback_seconds: float, seasonal_lookback_days: float
) -> float:
    return max(lookback_seconds, seasonal_lookback_days * 86400.0)


def _holt_winters_required_range_seconds(
    lookback_seconds: float, seasonal_periods: int, step_seconds: float
) -> float:
    return max(lookback_seconds, 2 * seasonal_periods * step_seconds)


def required_range_seconds(
    forecast: ForecastConfig, lookback_seconds: float, step_seconds: float
) -> float:
    """The history ``forecast.model`` needs, in seconds.

    Called by ``config.py``'s startup validation (section 11.1:
    ``window.lookback >= forecaster.required_range()``) without needing to
    construct a live series, and by each concrete Forecaster's
    ``required_range()`` below, so the rule exists exactly once.
    """
    if forecast.model == "quantile":
        return _quantile_required_range_seconds(lookback_seconds)
    if forecast.model == "seasonal_naive":
        return _seasonal_naive_required_range_seconds(
            lookback_seconds, forecast.seasonal_lookback_days
        )
    if forecast.model == "holt_winters":
        return _holt_winters_required_range_seconds(
            lookback_seconds, forecast.holt_winters.seasonal_periods, step_seconds
        )
    raise ValueError(
        f"unknown forecast.model {forecast.model!r}"
    )  # pragma: no cover - schema-guarded


@dataclass(frozen=True, slots=True)
class QuantileForecaster:
    """The default: p95 point estimate, p99 upper bound, over the whole series.

    Deliberately conservative and needs no model fitting (section 10). The
    quantiles are ``window.quantile``/``window.upper_quantile``, not hardcoded,
    so the concrete p95/p99 default lives only in ``config.py``.
    """

    lookback_seconds: float
    quantile: float = 0.95
    upper_quantile: float = 0.99

    def required_range(self) -> timedelta:
        return timedelta(seconds=_quantile_required_range_seconds(self.lookback_seconds))

    def predict(self, series: TimeSeries, horizon: timedelta) -> Forecast:
        del horizon  # the quantile model does not depend on the horizon
        values = [v for _, v in series]
        if not values:
            return Forecast(point_estimate=0.0, upper_bound=0.0)
        return Forecast(
            point_estimate=_quantile(values, self.quantile),
            upper_bound=_quantile(values, self.upper_quantile),
        )


@dataclass(frozen=True, slots=True)
class SeasonalNaiveForecaster:
    """Median/p95 across samples at the same hour-of-day, over several days.

    ``required_range`` per section 10.1 is ``seasonal_lookback_days`` (default
    7d), independent of ``window.lookback``.
    """

    lookback_seconds: float
    seasonal_lookback_days: float
    now_epoch_seconds: float
    upper_quantile: float = 0.95

    def required_range(self) -> timedelta:
        return timedelta(
            seconds=_seasonal_naive_required_range_seconds(
                self.lookback_seconds, self.seasonal_lookback_days
            )
        )

    def predict(self, series: TimeSeries, horizon: timedelta) -> Forecast:
        del horizon
        target_hour = int((self.now_epoch_seconds // 3600) % 24)
        same_hour = [v for ts, v in series if int((ts // 3600) % 24) == target_hour]
        if not same_hour:
            return Forecast(point_estimate=0.0, upper_bound=0.0)
        return Forecast(
            point_estimate=statistics.median(same_hour),
            upper_bound=_quantile(same_hour, self.upper_quantile),
        )


@dataclass(frozen=True, slots=True)
class HoltWintersForecaster:
    """Double-exponential smoothing with a seasonal component, via statsmodels.

    Not computed in PromQL (section 10.2): Prometheus's function of a similar
    name is level+trend only, with no seasonal term, and cannot learn a daily
    cycle. Falls back to :class:`QuantileForecaster`, with a logged warning,
    when there are fewer than ``2 * seasonal_periods`` samples (section
    10.2) or when ``statsmodels`` is not installed -- it is an optional
    dependency (section 2.1) and this is the one place the fallback needs to
    handle its absence, since a Debian install without ``python3-statsmodels``
    must still be able to select this model without crashing.
    """

    lookback_seconds: float
    seasonal_periods: int
    step_seconds: float
    trend: str = "add"
    seasonal: str = "add"
    residual_z: float = 2.0
    quantile: float = 0.95
    upper_quantile: float = 0.99

    def required_range(self) -> timedelta:
        return timedelta(
            seconds=_holt_winters_required_range_seconds(
                self.lookback_seconds, self.seasonal_periods, self.step_seconds
            )
        )

    def _fallback(self, series: TimeSeries, horizon: timedelta, reason: str) -> Forecast:
        logger.warning(
            "holt_winters falling back to quantile: %s",
            reason,
            extra={"event": "forecast_fallback", "reason": reason},
        )
        return QuantileForecaster(
            lookback_seconds=self.lookback_seconds,
            quantile=self.quantile,
            upper_quantile=self.upper_quantile,
        ).predict(series, horizon)

    def predict(self, series: TimeSeries, horizon: timedelta) -> Forecast:
        min_samples = 2 * self.seasonal_periods
        if len(series) < min_samples:
            return self._fallback(
                series,
                horizon,
                f"only {len(series)} samples, need >= {min_samples} (2x seasonal_periods)",
            )
        try:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing
        except ImportError:
            return self._fallback(series, horizon, "statsmodels is not installed")

        values = [v for _, v in series]
        model = ExponentialSmoothing(
            values,
            trend=None if self.trend == "none" else self.trend,
            seasonal=None if self.seasonal == "none" else self.seasonal,
            seasonal_periods=self.seasonal_periods,
            initialization_method="estimated",
        )
        fit = model.fit()
        steps = max(1, round(horizon.total_seconds() / self.step_seconds))
        forecast_values = fit.forecast(steps)
        point = float(forecast_values[-1])
        residuals = fit.resid
        sigma = float(statistics.pstdev(residuals)) if len(residuals) > 1 else 0.0
        return Forecast(point_estimate=point, upper_bound=point + self.residual_z * sigma)


def build_forecaster(
    forecast: ForecastConfig,
    lookback_seconds: float,
    step_seconds: float,
    now_epoch_seconds: float,
    quantile: float,
    upper_quantile: float,
) -> Forecaster:
    """Construct the configured forecaster. See section 10.1's table."""
    if forecast.model == "quantile":
        return QuantileForecaster(
            lookback_seconds=lookback_seconds, quantile=quantile, upper_quantile=upper_quantile
        )
    if forecast.model == "seasonal_naive":
        return SeasonalNaiveForecaster(
            lookback_seconds=lookback_seconds,
            seasonal_lookback_days=forecast.seasonal_lookback_days,
            now_epoch_seconds=now_epoch_seconds,
            upper_quantile=upper_quantile,
        )
    if forecast.model == "holt_winters":
        hw = forecast.holt_winters
        return HoltWintersForecaster(
            lookback_seconds=lookback_seconds,
            seasonal_periods=hw.seasonal_periods,
            step_seconds=step_seconds,
            trend=hw.trend,
            seasonal=hw.seasonal,
            residual_z=hw.residual_z,
            quantile=quantile,
            upper_quantile=upper_quantile,
        )
    raise ValueError(
        f"unknown forecast.model {forecast.model!r}"
    )  # pragma: no cover - schema-guarded


# --------------------------------------------------------------- backtest gate
#
# Section 10.2/phase 9: "validate by backtesting: fit on [t-2T, t-T],
# predict [t-T, t], compare against actual. Refuse to let a model whose
# backtest error exceeds the imbalance threshold drive migrations." This
# is a one-time-per-group gate on *which forecaster object to use at
# all* -- distinct from (and composable with) HoltWintersForecaster's own
# per-call "too few samples/statsmodels missing" fallback inside
# predict() itself, which answers a different question (can this model
# even run right now) from the one here (has this model actually been
# accurate). `quantile` is never backtested -- it does no fitting at all,
# so there is nothing to validate and nothing more conservative to fall
# back to.


def group_aggregate_series(disk_series: Mapping[str, TimeSeries]) -> TimeSeries:
    """Sum every disk's own series into one group-aggregate series, at the
    union of every timestamp seen across all of them (a timestamp missing
    from one disk's own series contributes 0 for it, the same "absence
    means no I/O" convention :func:`~proxmox_storage_drs.loadmodel._blend_loads`
    already uses). The backtest gate below validates ``forecast.model``
    itself, once per group, against this aggregate -- not once per disk
    -- because the model is a single, deployment-wide configuration
    choice, never something that could differ disk by disk."""
    per_disk_lookup = {key: dict(series) for key, series in disk_series.items()}
    timestamps: set[float] = set()
    for series in disk_series.values():
        timestamps.update(ts for ts, _v in series)
    return tuple(
        (ts, sum(lookup.get(ts, 0.0) for lookup in per_disk_lookup.values()))
        for ts in sorted(timestamps)
    )


def backtest_error(
    forecaster: Forecaster, series: TimeSeries, now_epoch_seconds: float, window_seconds: float
) -> float | None:
    """Section 10.2's backtest: fit ``forecaster`` on
    ``[now-2*window, now-window)``, predict ``window`` ahead, and compare
    that single point estimate against the *actual* mean observed over
    ``[now-window, now]`` -- a relative error, so it is directly
    comparable against ``gates.imbalance_threshold`` (both fractions).
    ``window_seconds`` is the caller's own choice (``window.lookback_seconds``,
    the same "decision window" section 10.1 already ties every forecaster
    to for its point estimate).

    Returns ``None`` when ``series`` does not cover a full ``2*window``
    of history to split into two non-empty halves at all -- "not yet
    validated" is treated by the caller exactly like "failed validation"
    (fall back), matching :class:`HoltWintersForecaster`'s own existing
    "not enough data yet -> fall back" precedent rather than giving a
    fresh deployment's still-unvalidated model a free pass.

    The relative error's denominator is ``actual`` normally, falling back
    to ``predicted`` only when ``actual`` is exactly zero (an idle
    backtest window) so a nonzero prediction against true silence reads
    as a full, bounded miss (``1.0``) instead of a division by zero; two
    zeros (correctly predicted silence) is a perfect score (``0.0``).
    """
    fit_start = now_epoch_seconds - 2 * window_seconds
    split = now_epoch_seconds - window_seconds
    fit_series = tuple((ts, v) for ts, v in series if fit_start <= ts < split)
    actual_series = tuple((ts, v) for ts, v in series if split <= ts <= now_epoch_seconds)
    if not fit_series or not actual_series:
        return None
    predicted = forecaster.predict(fit_series, timedelta(seconds=window_seconds)).point_estimate
    actual = statistics.mean(v for _, v in actual_series)
    denominator = actual if actual != 0 else predicted
    if denominator == 0:
        return 0.0
    return abs(predicted - actual) / abs(denominator)


def backtest_validated(
    forecaster: Forecaster,
    series: TimeSeries,
    now_epoch_seconds: float,
    window_seconds: float,
    imbalance_threshold: float,
) -> bool:
    """``True`` only when :func:`backtest_error` both ran (enough history
    existed to backtest at all) and came back within
    ``gates.imbalance_threshold`` -- the one boolean gate
    ``cli._saturation_forecast_inputs()`` actually acts on."""
    error = backtest_error(forecaster, series, now_epoch_seconds, window_seconds)
    return error is not None and error <= imbalance_threshold
