# The Prometheus client and `verify-metrics`

**What does this page answer?** How does `metrics.py` talk to Prometheus
without ever touching the network in a test? What does each of the six
`verify-metrics` checks query? This page describes
`proxmox_storage_drs/metrics.py`.

## `_SessionLike` / `_ResponseLike`: why not `requests.Session` directly

`PrometheusClient.__init__` accepts `session: _SessionLike | None`. That
type is a `Protocol` defined in this module. It exposes only the one
`get(...)` method the client actually calls. It is not `requests.Session`
itself. `.agents/testing.md` forbids any test that talks to a real
Prometheus. A structural protocol lets a test hand in a small dataclass
with a matching `get()`. The test does not mock or subclass the real
(network-capable) session. `PrometheusClient()` with no `session` argument
still constructs a real `requests.Session()`. That object satisfies the
protocol. The real session fits without any extra code.

## `_get()`: one request path, three endpoint shapes

All three methods `instant_query`, `range_query` and `label_values` go
through the private `_get()`. That function does the HTTP call. It checks
the status code. It parses the JSON. It checks Prometheus's own
`status: "success"` field. Then it returns `payload["data"]`. The *shape*
of that field differs by endpoint. A `query`/`query_range` call returns a
dict with a `result` list. A `label/<name>/values` call returns a bare
list. `_get()` is therefore typed `Any` instead of picking one shape. Each
public method knows which shape it asked for. It narrows the type
accordingly. Every failure mode raises `MetricsError` from this one place.
The failure modes are a transport error, a non-200 status, unparseable JSON
and an unsuccessful Prometheus response. A caller catches `MetricsError`
around any of the three public methods. The caller sees every failure mode
uniformly.

## PromQL construction

`build_rate_promql()` builds `sum by (vmid, device) (rate(<metric>{<selector>}[<rate_window>]))`.
The `sum by` deliberately collapses the node/host labels. A VM that
live-migrated between nodes mid-window still reads as one series. The
`selector` (see "Node-scoping" below) sits *inside* the vector selector of
`rate()`. It sits there before the collapse. `build_quantile_over_time_promql()`
wraps a rate expression in `quantile_over_time(q, (<rate_expr>)[<lookback>:<step>])`.
The six-raw-quantity fetch in `metrics.py` calls the first function to
build each `rate_expr`. It then wraps the result with the second, once per
configured quantile.
Both functions are pure string builders. The code keeps them out of any
query-issuing code. That is why a unit test can call them without a fake
session at all. `IMPLEMENTATION_PLAN.md` section 3.4 has the full per-metric
derivation. `raw_metric_name()` is the one place that maps a
`RAW_METRIC_FIELDS` entry (`"read_ops"`, ...) to the configured metric name
on a `MetricsConfig`, via `getattr`. That lets `verify_metrics()` iterate
"every configured raw metric". It does so without hand-listing the six
field names a second time anywhere in this module.

## Node-scoping: `build_node_selector()` / `resolve_node_selector()`

`build_rate_promql()` takes a `selector` parameter. The parameter makes a
query correct on a Prometheus that serves more than one PVE cluster. It
also makes the query correct on any other source that emits a same-named
metric. Without the selector, `sum by (vmid,
device)` sums across clusters. The `vmid` is unique only *within* one
cluster. `resolve_node_selector(metrics, node_names)` resolves the selector
text once per command invocation. It uses this order:

1. `metrics.extra_selector`, verbatim, when the operator set it. The code
   trusts it completely. It may not even name a node label at all.
2. `build_node_selector(metrics.labels.node, node_names)` otherwise. The
   function escapes every name (`_escape_promql_regex_literal()`; an FQDN's
   `.` is a regex metacharacter otherwise). It then joins the names into one
   `=~` alternation. This is the default tier, built from this cluster's own
   node list.
3. `None` when nothing above resolved anything (an empty `node_names`).

An earlier revision of this function had a middle tier here. That tier
matched a `cluster`-naming label against the live cluster's own name
(`PveClient.cluster_name()`, `GET /cluster/status`). An operator correction
removed the tier. The premise was that this project's deployments carry
such a label "as standard practice". That premise was simply wrong. This
project does not follow such a convention. The tier existed only on a
mistaken assumption. The extra `Sys.Audit`-gated API call it needed added
nothing. Use `metrics.extra_selector` for a cluster-naming (or any other)
label your own Telegraf/InfluxDB tagging scheme actually has.

`node_names` comes from `PveClient.node_names()` (`GET /nodes`). The code
fetches it at most once per run. It threads the value down through
`loadmodel.py`'s functions as a plain `Sequence[str] | None`. This module
and `loadmodel.py` never call the PVE API themselves.

`cli._resolve_node_selector_for_run()` is the one place that decides
*whether* to make that API call at all. It skips the call when
`metrics.extra_selector` is already set. `verify-metrics` never reaches
this function. The command calls `resolve_node_selector(metrics, None)`
directly. It applies only an explicit override. The command is deliberately
independent of the PVE API. It also has no node list of its own to build
the default tier from. Of its six checks, only `_check_coverage()`/
`_check_observed_spacing()` build a `rate()`/range query at all. The other
checks query a raw metric name or sample one series directly. A
cross-cluster mix-up is not a correctness question there. It is a
correctness question for a summed rate.

## `safe_range_step_seconds()` / `decimate_to_configured_step()`: the gigapipe `step >= range` workaround

Two live-confirmed deployments of a recently updated gigapipe backend
return **zero series** from `/api/v1/query_range`. The same holds for the
PromQL `[range:step]` subquery form. The failure happens for any
range-vector function whenever the query's own `step` is `>=` the
function's own range-vector duration. The confirmed functions are `rate()`,
`irate()`, `increase()`, `delta()` and `deriv()`. The identical expression
as a plain instant `/api/v1/query` returns correct data. That form has no
step at all. A binary search found the boundary to the exact second.
`rate(x[300s])` gets a full response at `step=299s`. It gets nothing at all
at `step=300s`. This project's own defaults set
`metrics.step == metrics.rate_window` (`300s` each). The defaults sit
exactly on the failing boundary. A fresh install with untouched defaults
can hit this on an affected backend with no misconfiguration.

`safe_range_step_seconds(step_seconds, rate_window_seconds)` is a no-op
once `step_seconds` is already strictly below `rate_window_seconds`.
Nothing then needs a workaround. Otherwise the function returns the largest
whole-second step strictly below `rate_window_seconds`. That step divides
`step_seconds` as evenly as a whole-second value can. At the 300s/300s
default the result is 150s. Other ratios do not always give an exact
divisor. 3600s/300s divides to 276s. 13·276=3588 ≠ 3600. That is a
documented ~0.33%-per-point grid drift. `compute_disk_coverage()` and
`loadmodel.py`'s raw-series fetch both call the function unconditionally.
The code does not wait to detect the affected backend. The symptom (zero
series) is indistinguishable from genuinely absent data. Both call sites
pass the result as the step on every `query_range` call.
`decimate_to_configured_step()` then recovers the originally-configured
grid. It keeps every Nth point of the denser response, anchored at the same
`start`. For an exact divisor the workaround is a true no-op. The retained
points are the identical instants and values a plain `metrics.step` query
would have returned on an unaffected backend.

The `quantile_over_time` subquery cannot decimate. An instant query returns
one scalar, not a series. The function evaluates its inner expression on
the denser, safe-step grid unconditionally. It does so on *every* backend,
healthy or not. At the 300s/300s default this doubles the inner sample
count the 95th percentile is taken over. The shift in the reduced
statistic is small but real (REVIEW.md Z-04). `collect.py`'s
`estimate_capture()` accounts for this step, not the configured one. The
`--replay` `compute_disk_coverage()` fallback does the same. That fallback
covers a bundle captured before this function existed, at the plain
configured step. Both account for this step for the same reason (REVIEW.md
Z-05).

## `RANGE_QUERY_CHUNK_SECONDS` / `stitch_range_results()`: chunking a wide `query_range`

A `query_range` call issued as a single request can exceed a
VictoriaMetrics/gigapipe backend's own max-points-per-timeseries limit.
This is the case when the range is wide enough. The limit is 11,000 points
by default. The failure is confirmed live with a
500 error: `"exceeded maximum resolution of 11,000 points per timeseries"`.
`IMPLEMENTATION_PLAN.md` section 10.2's backtest-gate floor
(`2 · window.lookback`) alone can double the fetch range. The doubled
range is wide enough for the failure. `collect.py`'s capture path
(`_issue_range_chunks`, section 16.2)
was already immune to this. The day-sized chunking there predates the
live-fetch bug. `loadmodel.py`'s own raw-series fetch had no such
protection. That fetch feeds a forecast. It issued one unchunked
request regardless of range.

`stitch_range_results(captures)` is the shared merge both paths now use. It
takes several `(start, end, result)` captures of the *same* query. Any
combination of chunking and repeat calls works. The function returns one
logical result. It holds one series per `(vmid, device)` pair. Each series
carries every point from every chunk, deduplicated by timestamp and sorted.
The merge is order-independent. A duplicate timestamp across overlapping
captures overwrites with the same value. It does not matter whether the
captures arrived in chunk order. `collect.py`'s own `_stitch_range_captures`
is now a thin wrapper around it. The wrapper adds the `(start, end, step)`
bookkeeping a captured bundle's range file needs.

`loadmodel._issue_chunked_range_query()` is `_fetch_raw_quantity_series()`'s own counterpart to
`collect.py`'s `_issue_range_chunks`. It splits `[start, end]` into
sub-requests of `RANGE_QUERY_CHUNK_SECONDS`. That constant is one day. It
matches `collect.py`'s own chunk size. The boundaries fall on
`start_epoch_seconds`. They never fall on wall-clock "now". The split is
deterministic across repeated calls. That property matters under `--replay`.
There, the code looks up the same promql text per chunk from one stored
bundle file. `replay.py`'s `_trim_range_result()` then trims the result to
each chunk's own window. After the split, the function stitches. It carries
the same `RangeStepMismatch`/`BundleError` fallback the unchunked call
always had. It applies the fallback per chunk. Both exceptions are a
property of the query text, not of which chunk asks for it. One property is
a `--replay` bundle's own recorded step. The other is "no recorded response
for this query at all". Once the step has fallen back once, every later
chunk reuses it directly. It does so without re-entering the fallback
branch.

## `verify_metrics()`: six checks, six functions

Each `_check_*` function is a single, focused verification. It returns
`Finding`s. Where relevant, it also returns the data the report carries
forward:

| Function | What it checks | Returns |
|---|---|---|
| `_check_metric_names_exist` | each of the six configured `metrics.*` names (`read_ops`, ...) exists as a Prometheus series name (`label_values("__name__")`). The check emits one error per name that does not. The error names the likely cause (never configured/emitted, or dropped — see below) | findings only |
| `_check_sample_series` | one instant query per metric returns at least one sample. The sample carries the expected `vmid`/`device` labels. Via its private `_check_cross_metric_disk_consistency()`, the check confirms that all six metrics report the identical set of `(vmid, device)` disks. It flags a metric whose disk set is a strict subset of the others' | findings, `{metric_name: sample_labels}` |
| `_check_device_label_collision` | warns if `metrics.labels.device` is literally `"instance"`. That value collides with Prometheus's own scrape-target `instance` label. The collision is a common Telegraf misconfiguration | one `Finding` or `None` (pure, no I/O) |
| `_check_coverage` | runs `compute_disk_coverage()`. It flags every disk whose sample coverage over the window falls below `window.min_coverage` | findings, `{DiskKey: coverage_fraction}` |
| `_check_observed_spacing` | measures the real sample spacing as the median over series of `window / count_over_time(read_ops[window])`. One instant query is enough. A `query_range` would only echo its own step back. The check compares the result against what `metrics.rate_window >= 4x` (section 11.1) assumes the real scrape interval to be | findings, `observed_spacing_seconds` |

`_check_coverage` and `_check_observed_spacing` both use `metrics.read_ops`.
The metric is the one representative. The code does not probe all six. A
coverage or spacing gap is a property of the underlying Telegraf scrape. It
is not a property of which of the six raw quantities is read. Probing all
six would use six times the Prometheus load. It would add no new
information.

That assumption has one real exception. InfluxDB's line protocol fixes a
field's type from its first write. Telegraf's Prometheus-compatible output
drops a field when it sees a non-numeric value for it. It drops the field
silently. Prometheus/OpenMetrics has no string sample type. The drop
happens independently of the other five fields for the same disk. If the
dropped field is not `read_ops`, `_check_coverage` alone would never notice.
`_check_sample_series` already runs an instant query against all six metrics
(step 2). Its private `_check_cross_metric_disk_consistency()` reuses those
same results. It adds no extra Prometheus load. The function compares each
metric's own `(vmid, device)` set against the union across all six. It warns
whenever one metric's set is a strict subset of another's. The warning names
the metric and the specific disk(s) missing from it.

`VerifyMetricsReport.ok` is `True` iff no `Finding` has `level == "error"`.
The `verify-metrics` handler in `cli.py` uses exactly this property. It uses
the property to decide the process exit code. That gives one definition of
"the verification passed."

## What `cli.py` does with the report

`_handle_verify_metrics` in `cli.py` constructs a `PrometheusClient` from
`resolved.config.prometheus`. It then calls `verify_metrics()`. It renders
the human form (`[level] message` lines). Under `--json`, it renders a
JSON-serializable dict instead. The renderer turns `DiskKey` keys into
`"vmid:device"` strings. JSON object keys must be strings. This module keeps
no opinion about output formatting.
