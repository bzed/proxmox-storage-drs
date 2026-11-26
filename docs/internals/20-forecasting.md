# Forecasting: a Holt-Winters scaling of each disk's load

**What does this page answer?** How does `forecast.py` turn a disk's history
into a load for the *next* window? When is that value trusted? Where does it
enter the model? This page describes `proxmox_storage_drs/forecast.py` and
its two callers, `cli._compute_group_load()` and `loadmodel.apply_forecast()`.

## What is forecast, and what is not

The decision statistic behind every placement is `window.quantile` (p95) of a
disk's load. `forecast.model: quantile` (the default) takes it over the **last**
`W = window.lookback`. This module is used only for `holt_winters`. That
model predicts the statistic over the **next** `W`. It fits the disk's
series. It forecasts `ceil(W / metrics.step)` steps. It takes
`window.quantile` of that forecast path. It clamps the result at 0
(`holt_winters_quantile()`).

Two things the value deliberately is not:

- **Not the last forecast point.** `fit.forecast(steps)[-1]` is one sample at
  one hour of day. That value says nothing about tomorrow's peak. The unit
  test builds a series that *ends at its daily trough*: the last point is
  the trough, the p95 of the path is near the peak.
- **No `z * sigma` band.** The tool compares a forecast p95 with the
  observed p95 of its `quantile`-model peers. A residual band would inflate
  exactly the disks that were forecast.

There is no forecaster protocol and no model registry any more. `quantile`
needs no code here at all. `seasonal_naive` was removed. Its statistic, the
median of the same hour of day, was not a forecast over `W`. Everything that
used an upper bound (the section 7.3 saturation guard) is gone too.

## A ratio, never a substitution

`loadmodel.compute_disk_load_series()` normalizes **per timestamp**.
`compute_group_load()` normalizes over the whole window. The latter also
owns coverage rejection and the `last_known_loads` fallback. The two
numbers are therefore on different scales. The forecast scales a load; it
does not replace one:

    l_d  <-  l_d * f_d / h_d

Here `h_d` is the `window.quantile` of the disk's own series over
`[now-W, now]`, and `f_d` is the forecast from above (`disk_factors()`).
`loadmodel.apply_forecast()` applies the factors. It rebuilds the
per-storage `L_s`/`u_s` and `u*`. A disk keeps its observed `l_d`
unchanged when

- it is flagged for low coverage (`DiskLoad.flagged_reason`), or
- it has no samples in the window, or `h_d = 0`, or
- there is no trustworthy fit: fewer than `2 * seasonal_periods` samples, a
  constant series, `statsmodels` not installed, any exception from the fit, a
  `ConvergenceWarning` (turned into an error inside the fit), or a non-finite
  forecast. `holt_winters_quantile()` returns `None` and the disk stays out.

`idle` and `no_series_matched` describe the observed window, and the
forecast leaves them untouched. A forecast never wakes an idle group up.

**One call site rule.** `cli._compute_group_load()` is the only place that
`show-load` or `plan`/`apply` gets a group's load from. A group's gates and
its plan always see the same `l`. The re-plans do too. Under `quantile`, the
value is exactly `compute_group_load()`. The code issues no extra Prometheus
query. It produces no report.

**Provenance is printed by every consumer that shows loads.** The call
returns a `ForecastReport`. The code does not discard the report anywhere.
`explain` and `show-load` render it as the same `forecast:` line.
`_render_forecast_line()` produces that line. `show-load` puts the line
directly under the group header. `plan --json`, `explain --json` and
`show-load --json` carry the report as a per-group `forecast` object. The
object is present only when there is a report (REVIEW.md AM-01). Without
the report, a forecast-scaled `ℓ` would be indistinguishable from a
measured one.

**The drift baseline is the effective load.** `last_balance.load_vector`
stores what `_compute_group_load()` returned for the run. Under
`holt_winters`, the stored vector is forecast-scaled. The next run's drift
gate then compares like with like, as long as the forecast state is
unchanged. The state changes when `forecast.model` switches, when the
backtest verdict flips, or when the factors move. Every disk's basis
changes then. The gate reads the change as drift. That is intended. The
balancer's picture changed, so reconsidering the placement is right. The
change only opens the imbalance gate. Payback still gates execution
(REVIEW.md AM-05).

## The gate: beat the baseline, no threshold

The backtest runs once per group, in `forecast_group()`. It uses
`group_aggregate_series()`. That series sums every disk's series at the
union of their timestamps. A disk missing a sample counts as 0,
`loadmodel._blend_loads()`'s own convention. The fit window is
`[now-2W, now-W)`. Both models predict the p95 of `[now-W, now]`. The
`quantile` model's prediction is the p95 of the fit half. That is
persistence. The group uses `holt_winters` if and only if its absolute
error is no larger than the baseline's (`Backtest.passed`). A tie
passes. Otherwise the group runs on `quantile` for this run. The run
logs a `forecast_backtest_failed` warning. A history of less than `2W` is
a failed backtest too. Such a history has no non-empty half on each side
of `now - W`. A fresh deployment does not get an exception. A history
query that fails outright is handled the same way. The failure can be a
`MetricsError`. Under `--replay`, the failure can be a `BundleError` for a
bundle captured over less than `2W`. The run logs a
`forecast_history_unavailable` warning. The group keeps its observed
loads. The group is still planned.

This replaces the earlier comparison against `gates.imbalance_threshold`.
That knob is unrelated. The new comparison also fixes a
point-at-horizon-versus-window-mean mismatch.

The backtest fits on a `W`-long half. For that reason, `window.lookback`
must hold `2 * seasonal_periods * step`. `required_range_seconds()`
returns the same figure for `holt_winters`. `config.py`'s startup
validation uses that figure. The tool fetches `max(required_range_seconds(),
2W)` of history. It fetches the history via the chunked
`compute_disk_load_series()` (`metrics.RANGE_QUERY_CHUNK_SECONDS`). The
fetch only happens for `holt_winters`.

## Reporting

`forecast_group()` returns `({disk_key: f_d / h_d}, ForecastReport)`.
`cli.py` logs one line per group. The log level is INFO for
`forecast_used`. The log level is WARNING for `forecast_backtest_failed`
or `forecast_history_unavailable`. The per-fit failures inside
`holt_winters_quantile()` log at DEBUG. A separate line per disk would
flood the journal. `explain` and `plan --json` carry
`forecast: {model, used, backtest_error, baseline_error, disks_scaled,
disks_kept}` per group. The object is present only under `holt_winters`.
The `quantile` reports stay byte-identical.

## Initialization

The fit uses `initialization_method="heuristic"`. The initial level, trend
and seasonals come from a classical decomposition of the first cycles, up
to five. Only the smoothing parameters are optimized. `"estimated"` also
optimizes every initial seasonal. At the default 288 periods, it did not
converge on real data at all. The heuristic needs two full cycles. The
`window.lookback >= 2 * seasonal_periods * step` rule already guarantees
two full cycles for the backtest's fit half.

## Cost

One `statsmodels` fit per disk with history. One more fit for the
backtest. The tool runs them per group per run. Each fit takes order 0.1 s
at a couple of thousand samples. The tool uses no caching. It uses no
parallelism. That is fine for a timer.

## `statsmodels` is optional

The code imports `statsmodels` only inside `holt_winters_quantile()`. It
never imports the package at module level. `debian/tests/import-all`
catches a regression. Without the package, every fit returns `None`. The
backtest cannot pass. Every group runs on `quantile`.

## `_quantile()`

`_quantile()` computes a linear-interpolation percentile. It matches
`numpy.percentile`'s default. The code is written by hand. The default
path then needs only `requests` + `ruamel.yaml` + `jsonschema`
(`IMPLEMENTATION_PLAN.md` section 2.1).
