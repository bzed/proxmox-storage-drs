# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Forecasters and the section 10.1 required-range rule."""

from __future__ import annotations

import logging
import math
from datetime import timedelta

import pytest

from proxmox_storage_drs.config import ForecastConfig, HoltWintersConfig
from proxmox_storage_drs.forecast import (
    HoltWintersForecaster,
    QuantileForecaster,
    SeasonalNaiveForecaster,
    _quantile,
    backtest_error,
    backtest_validated,
    build_forecaster,
    group_aggregate_series,
    required_range_seconds,
    storage_upper_bound,
)

DAY = 86400.0


# --------------------------------------------------------------- required range


def test_quantile_required_range_is_the_lookback() -> None:
    fc = ForecastConfig(model="quantile")
    assert required_range_seconds(fc, lookback_seconds=DAY, step_seconds=300) == DAY


def test_seasonal_naive_required_range_is_the_larger_of_the_two() -> None:
    fc = ForecastConfig(model="seasonal_naive", seasonal_lookback_days=7)
    assert required_range_seconds(fc, lookback_seconds=DAY, step_seconds=300) == 7 * DAY
    assert required_range_seconds(fc, lookback_seconds=10 * DAY, step_seconds=300) == 10 * DAY


def test_holt_winters_required_range_matches_plan_worked_example() -> None:
    # section 10.1: seasonal_periods=288 at a 5m step needs 2*288*300s = 48h,
    # which a 24h lookback can never supply.
    fc = ForecastConfig(model="holt_winters", holt_winters=HoltWintersConfig(seasonal_periods=288))
    required = required_range_seconds(fc, lookback_seconds=DAY, step_seconds=300)
    assert required == 48 * 3600


def test_required_range_unknown_model_raises() -> None:
    fc = ForecastConfig(model="quantile")
    object.__setattr__(fc, "model", "bogus")
    with pytest.raises(ValueError):
        required_range_seconds(fc, lookback_seconds=DAY, step_seconds=300)


# ------------------------------------------------------------------- quantile


def test_quantile_matches_numpy_percentile_convention() -> None:
    # median of [1,2,3,4] under linear interpolation is 2.5
    assert _quantile([1, 2, 3, 4], 0.5) == 2.5
    assert _quantile([5], 0.9) == 5


def test_quantile_of_empty_sequence_raises() -> None:
    with pytest.raises(ValueError):
        _quantile([], 0.5)


def test_quantile_forecaster_point_and_upper_bound() -> None:
    forecaster = QuantileForecaster(lookback_seconds=DAY, quantile=0.5, upper_quantile=1.0)
    series = [(float(i), float(i)) for i in range(1, 11)]  # values 1..10
    forecast = forecaster.predict(series, timedelta(hours=1))
    assert forecast.point_estimate == pytest.approx(5.5)
    assert forecast.upper_bound == pytest.approx(10.0)


def test_quantile_forecaster_empty_series_is_zero() -> None:
    forecaster = QuantileForecaster(lookback_seconds=DAY)
    forecast = forecaster.predict([], timedelta(hours=1))
    assert forecast.point_estimate == 0.0
    assert forecast.upper_bound == 0.0


def test_quantile_forecaster_required_range() -> None:
    forecaster = QuantileForecaster(lookback_seconds=DAY)
    assert forecaster.required_range() == timedelta(seconds=DAY)


# ------------------------------------------------------------- seasonal naive


def test_seasonal_naive_groups_by_hour_of_day() -> None:
    # Two samples at hour 3 (values 10, 20) on different days, one at hour 9.
    hour3_day1 = 3 * 3600
    hour3_day2 = hour3_day1 + int(DAY)
    hour9 = 9 * 3600
    series = [(hour3_day1, 10.0), (hour3_day2, 20.0), (hour9, 999.0)]
    forecaster = SeasonalNaiveForecaster(
        lookback_seconds=DAY, seasonal_lookback_days=7, now_epoch_seconds=hour3_day2
    )
    forecast = forecaster.predict(series, timedelta(hours=1))
    assert forecast.point_estimate == pytest.approx(15.0)  # median of [10, 20]
    assert forecast.upper_bound >= 15.0


def test_seasonal_naive_no_matching_hour_is_zero() -> None:
    forecaster = SeasonalNaiveForecaster(
        lookback_seconds=DAY, seasonal_lookback_days=7, now_epoch_seconds=0
    )
    forecast = forecaster.predict([], timedelta(hours=1))
    assert forecast.point_estimate == 0.0
    assert forecast.upper_bound == 0.0


def test_seasonal_naive_required_range() -> None:
    forecaster = SeasonalNaiveForecaster(
        lookback_seconds=DAY, seasonal_lookback_days=7, now_epoch_seconds=0
    )
    assert forecaster.required_range() == timedelta(seconds=7 * DAY)


# ------------------------------------------------------------------ holt-winters


def test_holt_winters_falls_back_when_too_few_samples(caplog: pytest.LogCaptureFixture) -> None:
    forecaster = HoltWintersForecaster(
        lookback_seconds=48 * 3600, seasonal_periods=288, step_seconds=300
    )
    series = [(float(i) * 300, float(i % 5)) for i in range(10)]  # far below 2*288
    with caplog.at_level(logging.WARNING):
        forecast = forecaster.predict(series, timedelta(hours=1))
    assert any("fall" in r.message for r in caplog.records)
    assert forecast.upper_bound >= forecast.point_estimate


def test_holt_winters_required_range() -> None:
    forecaster = HoltWintersForecaster(
        lookback_seconds=48 * 3600, seasonal_periods=288, step_seconds=300
    )
    assert forecaster.required_range() == timedelta(hours=48)


def test_holt_winters_fits_a_seasonal_series() -> None:
    statsmodels = pytest.importorskip("statsmodels")
    del statsmodels
    seasonal_periods = 24
    step_seconds = 3600.0
    n = 4 * seasonal_periods
    series = [
        (i * step_seconds, 10.0 + 5.0 * math.sin(2 * math.pi * i / seasonal_periods))
        for i in range(n)
    ]
    forecaster = HoltWintersForecaster(
        lookback_seconds=n * step_seconds,
        seasonal_periods=seasonal_periods,
        step_seconds=step_seconds,
    )
    forecast = forecaster.predict(series, timedelta(hours=1))
    assert forecast.upper_bound >= forecast.point_estimate
    # A reasonable fit stays in the neighbourhood of the series' own range.
    assert -5.0 <= forecast.point_estimate <= 25.0


# --------------------------------------------------------------- build_forecaster


def test_build_forecaster_selects_the_right_class() -> None:
    quantile_fc = ForecastConfig(model="quantile")
    seasonal_fc = ForecastConfig(model="seasonal_naive")
    hw_fc = ForecastConfig(model="holt_winters")

    assert isinstance(build_forecaster(quantile_fc, DAY, 300, 0, 0.95, 0.99), QuantileForecaster)
    assert isinstance(
        build_forecaster(seasonal_fc, DAY, 300, 0, 0.95, 0.99), SeasonalNaiveForecaster
    )
    assert isinstance(build_forecaster(hw_fc, DAY, 300, 0, 0.95, 0.99), HoltWintersForecaster)


def test_build_forecaster_unknown_model_raises() -> None:
    fc = ForecastConfig(model="quantile")
    object.__setattr__(fc, "model", "bogus")
    with pytest.raises(ValueError):
        build_forecaster(fc, DAY, 300, 0, 0.95, 0.99)


# --------------------------------------------------------- storage_upper_bound


def test_storage_upper_bound_sums_independent_per_disk_forecasts() -> None:
    """Section 10.1: L_hat_s(Delta) = sum of each disk's own upper bound,
    forecast independently -- not the forecast of the storage's own
    summed series (which could differ once the disks' peaks do not
    coincide)."""
    forecaster = QuantileForecaster(lookback_seconds=DAY, quantile=0.5, upper_quantile=1.0)
    series = {
        "101:scsi0": tuple((float(i), v) for i, v in enumerate([1.0, 2.0, 3.0])),
        "102:scsi0": tuple((float(i), v) for i, v in enumerate([4.0, 5.0, 6.0])),
    }
    result = storage_upper_bound(forecaster, series, ["101:scsi0", "102:scsi0"], timedelta(hours=1))
    # upper_bound (quantile=1.0, i.e. max) is 3.0 and 6.0 respectively.
    assert result == pytest.approx(9.0)


def test_storage_upper_bound_missing_disk_key_contributes_zero() -> None:
    """A disk key with no fetched series at all -- e.g. this run has no
    history for it yet -- forecasts an empty series, not a KeyError."""
    forecaster = QuantileForecaster(lookback_seconds=DAY, quantile=0.5, upper_quantile=1.0)
    series = {"101:scsi0": tuple((float(i), v) for i, v in enumerate([1.0, 2.0]))}
    result = storage_upper_bound(forecaster, series, ["101:scsi0", "999:scsi0"], timedelta(hours=1))
    assert result == pytest.approx(2.0)  # 999:scsi0 contributes 0.0


def test_storage_upper_bound_empty_disk_keys_is_zero() -> None:
    forecaster = QuantileForecaster(lookback_seconds=DAY)
    assert storage_upper_bound(forecaster, {}, [], timedelta(hours=1)) == 0.0


# --------------------------------------------------------- group_aggregate_series


def test_group_aggregate_series_sums_across_disks_per_timestamp() -> None:
    series = {
        "101:scsi0": ((0.0, 1.0), (1.0, 2.0)),
        "102:scsi0": ((0.0, 3.0), (1.0, 4.0)),
    }
    assert group_aggregate_series(series) == ((0.0, 4.0), (1.0, 6.0))


def test_group_aggregate_series_missing_disk_at_a_timestamp_contributes_zero() -> None:
    """101:scsi0 has no sample at t=1 at all -- that timestamp still
    appears (from 102:scsi0's own contribution), with 101:scsi0 counted
    as 0, not a KeyError or a dropped timestamp."""
    series = {
        "101:scsi0": ((0.0, 1.0),),
        "102:scsi0": ((0.0, 1.0), (1.0, 5.0)),
    }
    assert group_aggregate_series(series) == ((0.0, 2.0), (1.0, 5.0))


def test_group_aggregate_series_empty_input_is_empty() -> None:
    assert group_aggregate_series({}) == ()


# ------------------------------------------------------------------- backtest gate

# window_seconds=100, now=200: the fit half covers [0, 100), the actual
# half covers [100, 200] -- every test below places its points squarely
# inside one half or the other so there is no ambiguity about which side
# of the split they land on.
BACKTEST_WINDOW = 100.0
BACKTEST_NOW = 200.0


def test_backtest_error_is_zero_for_a_perfect_prediction() -> None:
    """A constant series: the median of the fit half exactly matches the
    mean of the actual half."""
    series = tuple((float(ts), 5.0) for ts in (10, 30, 50, 70, 90, 110, 130, 150, 170, 190))
    forecaster = QuantileForecaster(lookback_seconds=DAY, quantile=0.5, upper_quantile=1.0)
    error = backtest_error(forecaster, series, BACKTEST_NOW, BACKTEST_WINDOW)
    assert error == pytest.approx(0.0)


def test_backtest_error_detects_a_real_miss() -> None:
    fit = tuple((float(ts), 1.0) for ts in (10, 30, 50, 70, 90))
    actual = tuple((float(ts), 10.0) for ts in (110, 130, 150, 170, 190))
    forecaster = QuantileForecaster(lookback_seconds=DAY, quantile=0.5, upper_quantile=1.0)
    error = backtest_error(forecaster, fit + actual, BACKTEST_NOW, BACKTEST_WINDOW)
    assert error == pytest.approx(0.9)  # |1 - 10| / 10


def test_backtest_error_both_halves_idle_is_a_perfect_score() -> None:
    """Zero predicted, zero actual -- correctly forecasting silence is not
    a division-by-zero, it is the best possible score."""
    series = tuple((float(ts), 0.0) for ts in (10, 30, 50, 70, 90, 110, 130, 150, 170, 190))
    forecaster = QuantileForecaster(lookback_seconds=DAY, quantile=0.5, upper_quantile=1.0)
    error = backtest_error(forecaster, series, BACKTEST_NOW, BACKTEST_WINDOW)
    assert error == pytest.approx(0.0)


def test_backtest_error_nonzero_prediction_against_true_silence_is_bounded() -> None:
    """actual == 0 with a nonzero prediction falls back to normalizing by
    the prediction itself, rather than raising -- a full, bounded miss
    (1.0), not an unbounded ratio."""
    fit = tuple((float(ts), 5.0) for ts in (10, 30, 50, 70, 90))
    actual = tuple((float(ts), 0.0) for ts in (110, 130, 150, 170, 190))
    forecaster = QuantileForecaster(lookback_seconds=DAY, quantile=0.5, upper_quantile=1.0)
    error = backtest_error(forecaster, fit + actual, BACKTEST_NOW, BACKTEST_WINDOW)
    assert error == pytest.approx(1.0)


def test_backtest_error_returns_none_without_a_full_fit_half() -> None:
    """Every point falls in the *actual* half only -- there is nothing
    old enough to fit on yet."""
    series = tuple((float(ts), 1.0) for ts in (110, 130, 150))
    forecaster = QuantileForecaster(lookback_seconds=DAY)
    assert backtest_error(forecaster, series, BACKTEST_NOW, BACKTEST_WINDOW) is None


def test_backtest_error_returns_none_without_a_full_actual_half() -> None:
    """Every point falls in the *fit* half only -- nothing recent enough
    to compare a prediction against."""
    series = tuple((float(ts), 1.0) for ts in (10, 30, 50))
    forecaster = QuantileForecaster(lookback_seconds=DAY)
    assert backtest_error(forecaster, series, BACKTEST_NOW, BACKTEST_WINDOW) is None


def test_backtest_error_returns_none_for_a_completely_empty_series() -> None:
    forecaster = QuantileForecaster(lookback_seconds=DAY)
    assert backtest_error(forecaster, (), BACKTEST_NOW, BACKTEST_WINDOW) is None


def test_backtest_validated_true_when_error_is_within_the_threshold() -> None:
    series = tuple((float(ts), 5.0) for ts in (10, 30, 50, 70, 90, 110, 130, 150, 170, 190))
    forecaster = QuantileForecaster(lookback_seconds=DAY, quantile=0.5, upper_quantile=1.0)
    assert backtest_validated(forecaster, series, BACKTEST_NOW, BACKTEST_WINDOW, 0.20)


def test_backtest_validated_false_when_error_exceeds_the_threshold() -> None:
    fit = tuple((float(ts), 1.0) for ts in (10, 30, 50, 70, 90))
    actual = tuple((float(ts), 10.0) for ts in (110, 130, 150, 170, 190))
    forecaster = QuantileForecaster(lookback_seconds=DAY, quantile=0.5, upper_quantile=1.0)
    assert not backtest_validated(forecaster, fit + actual, BACKTEST_NOW, BACKTEST_WINDOW, 0.20)


def test_backtest_validated_false_without_enough_history() -> None:
    """Not yet validated is treated the same as failed validation, not a
    free pass for a fresh deployment."""
    forecaster = QuantileForecaster(lookback_seconds=DAY)
    assert not backtest_validated(forecaster, (), BACKTEST_NOW, BACKTEST_WINDOW, 0.20)
