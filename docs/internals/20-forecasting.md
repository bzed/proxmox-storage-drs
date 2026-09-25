# Forecasting: the protocol and its three implementations

**What does this page answer?** How does `forecast.py` decide how much
history a model needs, and what does each of `quantile`/`seasonal_naive`/
`holt_winters` actually compute? Describes `proxmox_storage_drs/forecast.py`.

## The one rule, in one place

Every model needs at least `window.lookback` seconds of history (the
*decision* window, since a forecaster's point estimate is always over that
window) — `quantile` needs nothing more than that. `seasonal_naive` needs
whichever is larger of `window.lookback` and `forecast.seasonal_lookback_days`
converted to seconds (`* 86400`): enough calendar days that every
hour-of-day bucket (see `SeasonalNaiveForecaster` below) has actually been
sampled at least once, not just the decision window itself. `holt_winters`
needs whichever is larger of `window.lookback` and `2 *
forecast.holt_winters.seasonal_periods * metrics.step` seconds — two full
seasonal cycles' worth of samples at the configured scrape step, matching
`statsmodels`'s own "needs at least two periods to fit a seasonal
component at all" requirement (see its own fallback rule below). That rule
has exactly one implementation: three small pure functions,
`_quantile_required_range_seconds`, `_seasonal_naive_required_range_seconds`
and `_holt_winters_required_range_seconds`, each called from **two** places —
the free function `required_range_seconds()` that `config.py`'s startup
validation uses (before any `Forecaster` is constructed), and the matching
`Forecaster.required_range()` method on the concrete class. Duplicating the
arithmetic between those two call sites, rather than sharing the pure
function, is exactly the kind of "second copy of a rule" AGENTS.md section 5
forbids — a change to the Holt-Winters requirement made in only one of them
would silently desynchronize config validation from what the forecaster
itself believes it needs. (`IMPLEMENTATION_PLAN.md` section 10.1 has the
full per-model table this generalizes from.)

## Nothing consumes the upper bound

Every `Forecaster.predict()` returns a `Forecast(point_estimate,
upper_bound)`. The only consumer of `upper_bound` was section 7.3's
saturation guard, removed by phase 14a (a migration is throttled by
`migration.bwlimit_bytes_per_sec` alone). Phase 14b rewrites this module's
contract around a forecast of each disk's p95 over the next `window.lookback`.

## `QuantileForecaster`

The default. `predict()` takes the `window.quantile`/`window.upper_quantile`
percentiles of the raw series with no fitting at all. `_quantile()`
implements linear-interpolation percentile matching `numpy.percentile`'s
default method, by hand — deliberately not using numpy, since the tool must
stay usable with only `requests` + `ruamel.yaml` + `jsonschema` installed
(`IMPLEMENTATION_PLAN.md` section 2.1). `horizon` is accepted (to satisfy the
`Forecaster` protocol) and immediately discarded: the quantile model has no
notion of a horizon-dependent forecast.

## `SeasonalNaiveForecaster`

Groups historical samples by hour-of-day (`int((ts // 3600) % 24)`) and takes
the median as the point estimate, the configured upper quantile across the
same bucket as the bound. `now_epoch_seconds` selects which hour-of-day
bucket the *current* moment falls into; `predict()` ignores everything
outside that bucket. A bucket with no samples returns `Forecast(0.0, 0.0)`
rather than raising, matching `IMPLEMENTATION_PLAN.md` section 4's rule for
an idle group's raw quantities: no data is zero, not an error, at this layer
(the caller decides whether zero is trustworthy).

## `HoltWintersForecaster`

`statsmodels` is an optional dependency (`Suggests`, not `Depends` — see
`debian/control`), so it is imported **only inside `predict()`**, never at
module level; `debian/tests/import-all` is what would catch a regression
here. Two situations fall back to `QuantileForecaster`, both logged at
warning level rather than failing silently:

1. fewer than `2 * seasonal_periods` samples in the series (section 10.2's
   own rule — a fit on too little data is worse than no fit);
2. `statsmodels` is not importable at all.

The upper bound is `point_estimate + residual_z * stdev(in-sample
residuals)` — not derived from the model's own confidence interval, which
`statsmodels`'s `ExponentialSmoothing.fit()` does not expose directly for
every configuration. `residual_z` (`forecast.holt_winters.residual_z`,
default `2.0`) is what an operator tunes if this bound turns out too tight
or too loose in practice.

## The section 10.2 backtest validation gate (phase 9)

Fitting successfully (`HoltWintersForecaster`'s own two fallback
conditions above) is not the same question as fitting *accurately* —
section 10.2's backtest is what actually answers the second one, once
per group, before `seasonal_naive`/`holt_winters` is trusted to drive the
load model at all. `quantile` is never backtested: it
does no fitting, so there is nothing to validate and nothing more
conservative to fall back to.

`backtest_error()` implements the plan's own recipe literally: fit the
candidate forecaster on `[now-2W, now-W)`, predict `W` ahead (`W` is
`window.lookback_seconds`, the same "decision window" every forecaster is
already tied to for its point estimate), and compare that single point
estimate against the *actual* mean observed over `[now-W, now]`. The
result is a **relative** error — `|predicted - actual| / actual`,
normalizing by `predicted` instead only when `actual` is exactly zero (a
nonzero prediction against true silence then reads as a full, bounded
miss, `1.0`, rather than a division by zero; two zeros, correctly
predicted silence, score a perfect `0.0`) — so it is directly comparable
against `gates.imbalance_threshold` (both plain fractions in `[0, 1]`,
section 10.2's own choice of yardstick). `backtest_error()` returns
`None`, not `0.0` or an exception, when `series` does not cover a full
`2W` to split into two non-empty halves at all; `backtest_validated()`
treats that exactly like a failed backtest — a fresh deployment with no
track record yet does not get a free pass just because it has not been
disproven, matching `HoltWintersForecaster`'s own existing "not enough
samples yet → fall back" precedent rather than contradicting it.

**Validated once per group, against the group's own aggregate series, not
once per disk.** `group_aggregate_series()` sums every disk's own series
at the union of their timestamps (a disk missing a sample at some
timestamp contributes `0`, the identical "absence means no I/O"
convention `loadmodel._blend_loads()` already uses). `forecast.model` is
a single, deployment-wide configuration choice — it cannot differ disk by
disk — so validating it once, cheaply, against one representative series
is the right granularity; backtesting separately per disk per move would
be both more expensive and would raise an unanswerable question (use the
fancier model for the disks it happens to fit and `quantile` for the rest,
*within the same run*?) that the plan itself never poses.

`cli._backtest_gated_forecaster()` is the one caller (nothing calls it
between 14a and 14b). A model that fails validation falls back to a fresh `QuantileForecaster` (routed
through `build_forecaster()` again with `forecast.model` overridden to
`"quantile"`, never hand-constructed — the one factory, see below), logged
at warning with the model name that failed.

## `build_forecaster()`

The one factory function that turns a `ForecastConfig` plus the ambient
`window`/`metrics` values into a live `Forecaster` instance. Nothing else in
the codebase should construct a `QuantileForecaster`/`SeasonalNaiveForecaster`/
`HoltWintersForecaster` directly once a caller exists that needs one from
config — route it through here so the model-name-to-class mapping stays in
one place.
