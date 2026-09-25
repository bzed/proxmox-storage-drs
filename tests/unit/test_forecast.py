# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Holt-Winters forecasting, its backtest gate, and the required-range rule."""

from __future__ import annotations

import math
import random
import sys
import warnings
from typing import Any

import pytest

from proxmox_storage_drs.config import ForecastConfig, HoltWintersConfig
from proxmox_storage_drs.forecast import (
    Backtest,
    ForecastReport,
    TimeSeries,
    _quantile,
    backtest,
    disk_factors,
    forecast_group,
    group_aggregate_series,
    holt_winters_quantile,
    required_range_seconds,
)

DAY = 86400.0
STEP = 3600.0
HW = HoltWintersConfig(seasonal_periods=24)  # a daily cycle at a 1h step


def series_of(n: int, fn: Any) -> TimeSeries:
    return tuple((i * STEP, float(fn(i))) for i in range(n))


# --------------------------------------------------------------- required range


def test_quantile_required_range_is_the_lookback() -> None:
    fc = ForecastConfig(model="quantile")
    assert required_range_seconds(fc, lookback_seconds=DAY, step_seconds=300) == DAY


def test_holt_winters_required_range_matches_plan_worked_example() -> None:
    # section 10.1: seasonal_periods=288 at a 5m step needs 2*288*300s = 48h,
    # which a 24h lookback can never supply.
    fc = ForecastConfig(model="holt_winters", holt_winters=HoltWintersConfig(seasonal_periods=288))
    required = required_range_seconds(fc, lookback_seconds=DAY, step_seconds=300)
    assert required == 48 * 3600


def test_holt_winters_required_range_is_the_lookback_when_that_is_longer() -> None:
    fc = ForecastConfig(model="holt_winters", holt_winters=HoltWintersConfig(seasonal_periods=24))
    assert required_range_seconds(fc, lookback_seconds=10 * DAY, step_seconds=300) == 10 * DAY


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


# ------------------------------------------------------ holt_winters_quantile


def test_holt_winters_quantile_is_the_p95_of_the_forecast_path_not_its_last_point() -> None:
    """A diurnal series that *ends at its trough*: the last forecast point (one
    day ahead, same phase) is the trough again, but the p95 of the whole next day
    is near the peak -- which is what tomorrow's placement should be based on."""
    pytest.importorskip("statsmodels")
    rng = random.Random(1)
    n = 24 * 8 + 13  # the last sample sits at the cosine's minimum
    series = series_of(
        n, lambda i: 10 + 5 * math.cos(2 * math.pi * i / 24) + rng.uniform(-0.2, 0.2)
    )
    assert series[-1][1] < 6  # ends at the trough
    result = holt_winters_quantile(series, HW, STEP, DAY, 0.95)
    assert result is not None
    assert 13.5 < result < 15.5  # ~ 10 + 5 * cos(pi * 0.05)


def test_holt_winters_fits_the_default_288_periods_on_two_bursty_days() -> None:
    """The shipped default (288 periods at a 5m step) over the two cycles the
    lookback floor guarantees, with bursty noise like real disk I/O. Under
    ``initialization_method="estimated"`` this raised a ConvergenceWarning on
    every seed (so no fit, ever, on the live dev cluster); the heuristic
    initialization fits it."""
    pytest.importorskip("statsmodels")
    rng = random.Random(0)
    step = 300.0
    series = tuple(
        (
            i * step,
            max(
                0.0,
                10
                + 5 * math.sin(2 * math.pi * i / 288)
                + rng.expovariate(1.0) * (8 if rng.random() < 0.05 else 1),
            ),
        )
        for i in range(576)
    )
    hw = HoltWintersConfig(seasonal_periods=288)
    assert holt_winters_quantile(series, hw, step, DAY, 0.95) is not None


def test_holt_winters_quantile_follows_a_rising_trend_above_the_observed_p95() -> None:
    pytest.importorskip("statsmodels")
    rng = random.Random(2)
    series = series_of(
        24 * 6, lambda i: 10 + 0.1 * i + 3 * math.sin(2 * math.pi * i / 24) + rng.uniform(-0.2, 0.2)
    )
    observed = _quantile([v for _, v in series[-24:]], 0.95)
    result = holt_winters_quantile(series, HW, STEP, DAY, 0.95)
    assert result is not None and result > observed


def test_holt_winters_quantile_is_none_with_too_few_samples() -> None:
    assert holt_winters_quantile(series_of(47, lambda i: i % 5), HW, STEP, DAY, 0.95) is None


def test_holt_winters_quantile_is_none_for_a_constant_series() -> None:
    assert holt_winters_quantile(series_of(96, lambda i: 3.0), HW, STEP, DAY, 0.95) is None


def test_holt_winters_quantile_is_none_when_statsmodels_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "statsmodels.tsa.holtwinters", None)
    series = series_of(96, lambda i: i % 7)
    assert holt_winters_quantile(series, HW, STEP, DAY, 0.95) is None


def test_holt_winters_quantile_is_none_when_the_fit_raises() -> None:
    pytest.importorskip("statsmodels")
    # A multiplicative model cannot be fitted to data containing zeros.
    hw = HoltWintersConfig(seasonal_periods=24, trend="mul", seasonal="mul")
    series = series_of(96, lambda i: i % 5)  # contains 0.0
    assert holt_winters_quantile(series, hw, STEP, DAY, 0.95) is None


def test_holt_winters_quantile_is_none_on_a_convergence_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sm = pytest.importorskip("statsmodels.tsa.holtwinters")
    from statsmodels.tools.sm_exceptions import ConvergenceWarning

    class _Warns:
        def __init__(self, *_a: object, **_k: object) -> None:
            pass

        def fit(self) -> object:
            warnings.warn("did not converge", ConvergenceWarning, stacklevel=2)
            raise AssertionError("unreachable: the warning is an error")

    monkeypatch.setattr(sm, "ExponentialSmoothing", _Warns)
    series = series_of(96, lambda i: i % 7)
    assert holt_winters_quantile(series, HW, STEP, DAY, 0.95) is None


def test_holt_winters_quantile_is_none_for_a_non_finite_forecast(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sm = pytest.importorskip("statsmodels.tsa.holtwinters")

    class _Nan:
        def __init__(self, *_a: object, **_k: object) -> None:
            pass

        def fit(self) -> "_Nan":
            return self

        def forecast(self, steps: int) -> list[float]:
            return [float("nan")] * steps

    monkeypatch.setattr(sm, "ExponentialSmoothing", _Nan)
    assert holt_winters_quantile(series_of(96, lambda i: i % 7), HW, STEP, DAY, 0.95) is None


def test_holt_winters_quantile_clamps_at_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    sm = pytest.importorskip("statsmodels.tsa.holtwinters")

    class _Negative:
        def __init__(self, *_a: object, **_k: object) -> None:
            pass

        def fit(self) -> "_Negative":
            return self

        def forecast(self, steps: int) -> list[float]:
            return [-4.0] * steps

    monkeypatch.setattr(sm, "ExponentialSmoothing", _Negative)
    assert holt_winters_quantile(series_of(96, lambda i: i % 7), HW, STEP, DAY, 0.95) == 0.0


def test_holt_winters_quantile_forecasts_ceil_window_over_step_steps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sm = pytest.importorskip("statsmodels.tsa.holtwinters")
    asked: list[int] = []

    class _Recorder:
        def __init__(self, *_a: object, **_k: object) -> None:
            pass

        def fit(self) -> "_Recorder":
            return self

        def forecast(self, steps: int) -> list[float]:
            asked.append(steps)
            return [1.0] * steps

    monkeypatch.setattr(sm, "ExponentialSmoothing", _Recorder)
    holt_winters_quantile(series_of(96, lambda i: i % 7), HW, 300.0, 1000.0, 0.95)
    assert asked == [4]  # ceil(1000 / 300)


# ----------------------------------------------------------------- disk_factors


def _factor_series(window_values: list[float]) -> TimeSeries:
    """96 hourly samples whose last 24 are ``window_values`` (repeated)."""
    older = [1.0 + (i % 3) for i in range(72)]
    return tuple((i * STEP, v) for i, v in enumerate(older + window_values))


class _FixedForecast:
    """Patches ``holt_winters_quantile`` to a constant so the ratio is exact."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, value: float | None) -> None:
        monkeypatch.setattr(
            "proxmox_storage_drs.forecast.holt_winters_quantile", lambda *a, **k: value
        )


def test_disk_factors_is_forecast_over_observed_p95(monkeypatch: pytest.MonkeyPatch) -> None:
    _FixedForecast(monkeypatch, 8.0)
    series = _factor_series([4.0] * 24)  # observed p95 over the last window: 4.0
    now = 95 * STEP
    factors = disk_factors({"101:scsi0": series}, set(), now, DAY, STEP, HW, 0.95)
    assert factors == {"101:scsi0": pytest.approx(2.0)}


def test_disk_factors_leaves_out_a_zero_observed_disk(monkeypatch: pytest.MonkeyPatch) -> None:
    _FixedForecast(monkeypatch, 8.0)
    series = _factor_series([0.0] * 24)
    assert disk_factors({"101:scsi0": series}, set(), 95 * STEP, DAY, STEP, HW, 0.95) == {}


def test_disk_factors_leaves_out_a_skipped_disk(monkeypatch: pytest.MonkeyPatch) -> None:
    _FixedForecast(monkeypatch, 8.0)
    series = _factor_series([4.0] * 24)
    assert disk_factors({"101:scsi0": series}, {"101:scsi0"}, 95 * STEP, DAY, STEP, HW, 0.95) == {}


def test_disk_factors_leaves_out_a_failed_fit(monkeypatch: pytest.MonkeyPatch) -> None:
    _FixedForecast(monkeypatch, None)
    series = _factor_series([4.0] * 24)
    assert disk_factors({"101:scsi0": series}, set(), 95 * STEP, DAY, STEP, HW, 0.95) == {}


def test_disk_factors_leaves_out_a_disk_with_no_samples_in_the_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _FixedForecast(monkeypatch, 8.0)
    assert disk_factors({"101:scsi0": ()}, set(), 95 * STEP, DAY, STEP, HW, 0.95) == {}
    stale = series_of(10, lambda i: 4.0)  # ends long before the window
    assert disk_factors({"101:scsi0": stale}, set(), 95 * STEP, DAY, STEP, HW, 0.95) == {}


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


def _trend_series(seed: int = 2) -> TimeSeries:
    rng = random.Random(seed)
    return series_of(
        97, lambda i: 10 + 0.15 * i + 3 * math.sin(2 * math.pi * i / 24) + rng.uniform(-0.2, 0.2)
    )


def _noise_series(seed: int = 3) -> TimeSeries:
    rng = random.Random(seed)
    return series_of(97, lambda i: 10 + rng.uniform(-3, 3))


W2 = 48 * STEP  # a two-day window: each backtest half holds two seasonal cycles
NOW = 96 * STEP


def test_backtest_passes_on_a_seasonal_series_with_a_trend() -> None:
    pytest.importorskip("statsmodels")
    result = backtest(_trend_series(), NOW, W2, STEP, HW, 0.95)
    assert result is not None and result.passed
    assert result.hw_error is not None and result.hw_error < result.baseline_error


def test_backtest_fails_on_white_noise() -> None:
    pytest.importorskip("statsmodels")
    result = backtest(_noise_series(), NOW, W2, STEP, HW, 0.95)
    assert result is not None and not result.passed


def test_backtest_hw_error_is_none_when_the_fit_half_is_too_short() -> None:
    """Fewer than 2 * seasonal_periods samples before now - W: Holt-Winters cannot
    be fitted, so it cannot pass."""
    result = backtest(_trend_series(), NOW, W2, STEP, HoltWintersConfig(seasonal_periods=48), 0.95)
    assert result is not None
    assert result.hw_error is None and not result.passed


def test_backtest_is_none_without_a_fit_half() -> None:
    series = series_of(10, lambda i: 1.0)  # everything inside the actual half
    assert backtest(series, 9 * STEP, 20 * STEP, STEP, HW, 0.95) is None


def test_backtest_is_none_without_an_actual_half() -> None:
    series = series_of(10, lambda i: 1.0)  # everything inside the fit half
    assert backtest(series, 100 * STEP, 50 * STEP, STEP, HW, 0.95) is None


def test_backtest_is_none_for_an_empty_series() -> None:
    assert backtest((), NOW, W2, STEP, HW, 0.95) is None


def test_backtest_passed_needs_a_holt_winters_error_not_worse_than_the_baseline() -> None:
    assert Backtest(hw_error=0.1, baseline_error=0.1).passed  # a tie passes
    assert Backtest(hw_error=0.0, baseline_error=0.1).passed
    assert not Backtest(hw_error=0.2, baseline_error=0.1).passed
    assert not Backtest(hw_error=None, baseline_error=0.1).passed


# ---------------------------------------------------------------- forecast_group


def _group_series(base: TimeSeries) -> dict[str, TimeSeries]:
    return {
        "101:scsi0": base,
        "102:scsi0": tuple((ts, v / 2) for ts, v in base),
        "103:scsi0": tuple((ts, 0.0) for ts, _v in base),  # idle: nothing to scale
    }


def test_forecast_group_scales_disks_when_the_backtest_passes() -> None:
    pytest.importorskip("statsmodels")
    fc = ForecastConfig(model="holt_winters", holt_winters=HW)
    factors, report = forecast_group(
        _group_series(_trend_series()), {"102:scsi0"}, fc, NOW, W2, STEP, 0.95
    )
    assert set(factors) == {"101:scsi0"}  # 102 is skipped, 103 has h_d = 0
    assert report.used and report.model == "holt_winters"
    assert report.disks_scaled == 1 and report.disks_kept == 2
    assert report.backtest_error is not None and report.baseline_error is not None
    assert report.backtest_error <= report.baseline_error


def test_forecast_group_keeps_every_load_when_the_backtest_fails() -> None:
    pytest.importorskip("statsmodels")
    fc = ForecastConfig(model="holt_winters", holt_winters=HW)
    factors, report = forecast_group(_group_series(_noise_series()), set(), fc, NOW, W2, STEP, 0.95)
    assert factors == {}
    assert not report.used
    assert report.disks_scaled == 0 and report.disks_kept == 3
    assert report.backtest_error is not None and report.baseline_error is not None
    assert report.backtest_error > report.baseline_error


def test_forecast_group_without_enough_history_reports_no_errors() -> None:
    fc = ForecastConfig(model="holt_winters", holt_winters=HW)
    factors, report = forecast_group(
        _group_series(series_of(10, lambda i: 1.0)), set(), fc, NOW, W2, STEP, 0.95
    )
    assert factors == {}
    assert report == ForecastReport(
        model="holt_winters",
        used=False,
        backtest_error=None,
        baseline_error=None,
        disks_scaled=0,
        disks_kept=3,
    )


def test_forecast_report_as_dict_has_the_documented_keys() -> None:
    report = ForecastReport("holt_winters", True, 0.08, 0.14, 37, 5)
    assert report.as_dict() == {
        "model": "holt_winters",
        "used": True,
        "backtest_error": 0.08,
        "baseline_error": 0.14,
        "disks_scaled": 37,
        "disks_kept": 5,
    }
