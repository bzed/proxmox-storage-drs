# Forecasting: a Holt-Winters scaling of each disk's load

**What does this page answer?** How does `forecast.py` turn a disk's history into
a load for the *next* window, when is that trusted, and where does it enter the
model? Describes `proxmox_storage_drs/forecast.py` and its two callers,
`cli._compute_group_load()` and `loadmodel.apply_forecast()`.

## What is forecast, and what is not

The decision statistic behind every placement is `window.quantile` (p95) of a
disk's load. `forecast.model: quantile` (the default) takes it over the **last**
`W = window.lookback`; this module is only used for `holt_winters`, which
predicts it over the **next** `W`: fit the disk's series, forecast
`ceil(W / metrics.step)` steps, take `window.quantile` of that forecast path,
clamp at 0 (`holt_winters_quantile()`).

Two things it deliberately is not:

- **Not the last forecast point.** `fit.forecast(steps)[-1]` is one sample at
  one hour of day; it says nothing about tomorrow's peak. The unit test builds a
  series that *ends at its daily trough*: the last point is the trough, the p95
  of the path is near the peak.
- **No `z * sigma` band.** A forecast p95 is compared with its `quantile`-model
  peers' observed p95; a residual band would inflate exactly the disks that were
  forecast.

There is no forecaster protocol and no model registry any more: `quantile` needs
no code here at all, `seasonal_naive` was removed (its statistic — the median of
the same hour of day — was not a forecast over `W`), and everything that used an
upper bound (the section 7.3 saturation guard) is gone.

## A ratio, never a substitution

`loadmodel.compute_disk_load_series()` normalizes **per timestamp** while
`compute_group_load()` normalizes over the whole window and also owns coverage
rejection and the `last_known_loads` fallback, so the two numbers are on
different scales. The forecast therefore scales, it does not replace:

    l_d  <-  l_d * f_d / h_d

with `h_d` the `window.quantile` of the disk's own series over `[now-W, now]`
and `f_d` the forecast from above (`disk_factors()`). `loadmodel.apply_forecast()`
applies the factors and rebuilds the per-storage `L_s`/`u_s` and `u*`. A disk
keeps its observed `l_d` unchanged when

- it is flagged for low coverage (`DiskLoad.flagged_reason`), or
- it has no samples in the window, or `h_d = 0`, or
- there is no trustworthy fit: fewer than `2 * seasonal_periods` samples, a
  constant series, `statsmodels` not installed, any exception from the fit, a
  `ConvergenceWarning` (turned into an error inside the fit), or a non-finite
  forecast. `holt_winters_quantile()` returns `None` and the disk is left out.

`idle` and `no_series_matched` describe the observed window and are untouched: a
forecast never wakes an idle group up.

**One call site rule.** `cli._compute_group_load()` is the only place either
`show-load` or `plan`/`apply` gets a group's load from, so a group's gates and its
plan (and its re-plans) always see the same `l`. Under `quantile` it is exactly
`compute_group_load()`: no extra Prometheus query, no report.

## The gate: beat the baseline, no threshold

Once per group (`forecast_group()`), on `group_aggregate_series()` (every disk's
series summed at the union of their timestamps; a disk missing a sample counts as
0, `loadmodel._blend_loads()`'s own convention): fit on `[now-2W, now-W)` and have
both models predict the p95 of `[now-W, now]`. The `quantile` model's prediction
is the p95 of the fit half — persistence. `holt_winters` is used for the group iff
its absolute error is no larger than the baseline's (`Backtest.passed`); a tie
passes. Otherwise the group runs on `quantile` for this run, with a
`forecast_backtest_failed` warning. Less than `2W` of history (no non-empty half on
each side of `now - W`) is a failed backtest too: a fresh deployment gets no free
pass. A history query that fails outright (a `MetricsError`, or under `--replay` a
`BundleError` for a bundle captured over less than `2W`) is handled the same way,
with a `forecast_history_unavailable` warning: the group keeps its observed loads
and is still planned.

This replaces the earlier comparison against `gates.imbalance_threshold` — an
unrelated knob — and a point-at-horizon-versus-window-mean mismatch.

Because the backtest fits on a `W`-long half, `window.lookback` must hold
`2 * seasonal_periods * step`; that is the same figure `required_range_seconds()`
returns for `holt_winters`, and `config.py`'s startup validation uses it. The
history actually fetched is `max(required_range_seconds(), 2W)`, via the chunked
`compute_disk_load_series()` (`metrics.RANGE_QUERY_CHUNK_SECONDS`), and only for
`holt_winters`.

## Reporting

`forecast_group()` returns `({disk_key: f_d / h_d}, ForecastReport)`. `cli.py`
logs one line per group (INFO `forecast_used`, WARNING `forecast_backtest_failed`
or `forecast_history_unavailable`;
the per-fit failures inside `holt_winters_quantile()` are DEBUG, one per disk
would flood the journal), and `explain` and `plan --json` carry
`forecast: {model, used, backtest_error, baseline_error, disks_scaled,
disks_kept}` per group — present only under `holt_winters`, so `quantile` reports
stay byte-identical.

## Initialization

The fit uses `initialization_method="heuristic"`: the initial level, trend and
seasonals come from a classical decomposition of the first (up to five) cycles,
and only the smoothing parameters are optimized. `"estimated"` also optimizes
every initial seasonal, and at the default 288 periods it did not converge on
real data at all. The heuristic needs two full cycles, which the
`window.lookback >= 2 * seasonal_periods * step` rule already guarantees for the
backtest's fit half.

## Cost

One `statsmodels` fit per disk with history, plus one for the backtest, per group
per run: order 0.1 s each at a couple of thousand samples. No caching and no
parallelism; fine for a timer.

## `statsmodels` is optional

It is imported only inside `holt_winters_quantile()`, never at module level —
`debian/tests/import-all` is what catches a regression. Without it every fit
returns `None`, the backtest cannot pass, and every group runs on `quantile`.

## `_quantile()`

Linear-interpolation percentile matching `numpy.percentile`'s default, written by
hand so the default path needs only `requests` + `ruamel.yaml` + `jsonschema`
(`IMPLEMENTATION_PLAN.md` section 2.1).
