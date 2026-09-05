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
    build_forecaster,
    required_range_seconds,
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
