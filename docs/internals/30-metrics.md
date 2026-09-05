# The Prometheus client and `verify-metrics`

**What does this page answer?** How does `metrics.py` talk to Prometheus
without ever touching the network in a test, and what does each of the six
`verify-metrics` checks actually query? Describes
`proxmox_storage_drs/metrics.py`.

## `_SessionLike` / `_ResponseLike`: why not `requests.Session` directly

`PrometheusClient.__init__` accepts `session: _SessionLike | None`, a
`Protocol` defined in this module with only the one `get(...)` method the
client actually calls — not `requests.Session` itself. `.agents/testing.md`
forbids any test talking to a real Prometheus; a structural protocol lets a
test hand in a small dataclass with a matching `get()` instead of mocking
or subclassing the real (network-capable) session. `PrometheusClient()` with
no `session` argument still constructs a real `requests.Session()`, which
satisfies the protocol structurally — nothing special is needed to make the
real thing fit.

## `_get()`: one request path, three endpoint shapes

Every one of `instant_query`, `range_query` and `label_values` goes through
the private `_get()`, which does the HTTP call, checks the status code,
parses JSON, checks Prometheus's own `status: "success"` field, and returns
`payload["data"]`. That field's *shape* genuinely differs by endpoint — a
dict with a `result` list for `query`/`query_range`, a bare list for
`label/<name>/values` — which is why `_get()` is typed `Any` rather than
picking one shape; each public method knows which shape it asked for and
narrows accordingly. Every failure mode (a transport error, a non-200
status, unparseable JSON, an unsuccessful Prometheus response) raises
`MetricsError` from exactly this one place, so a caller catching
`MetricsError` around any of the three public methods sees every failure
mode uniformly.

## PromQL construction

`build_rate_promql()` and `build_quantile_over_time_promql()` are pure
string-building functions, deliberately factored out of any query-issuing
code so they are unit-testable without a fake session at all — see
`IMPLEMENTATION_PLAN.md` section 3.4 for the exact expressions they
implement. `raw_metric_name()` is the one place that maps a
`RAW_METRIC_FIELDS` entry (`"read_ops"`, ...) to the configured metric name
on a `MetricsConfig`, via `getattr` — this is what lets `verify_metrics()`
iterate "every configured raw metric" without hand-listing the six field
names a second time anywhere in this module.

## `verify_metrics()`: six checks, six functions

Each `_check_*` function implements exactly one `IMPLEMENTATION_PLAN.md`
section 3.3 numbered check and returns `Finding`s (plus, where relevant, the
data the report carries forward):

| Function | Section 3.3 step | Returns |
|---|---|---|
| `_check_metric_names_exist` | 1 | findings only |
| `_check_sample_series` | 2 + 3 (labels present) | findings, `{metric_name: sample_labels}` |
| `_check_device_label_collision` | 4 | one `Finding` or `None` (pure, no I/O) |
| `_check_coverage` | 5 | findings, `{DiskKey: coverage_fraction}` |
| `_check_observed_spacing` | 6 | findings, `observed_spacing_seconds` |

`_check_coverage` and `_check_observed_spacing` both use `metrics.read_ops`
as the one representative metric rather than probing all six: a coverage or
spacing gap is a property of the underlying Telegraf scrape, not of which of
the six raw quantities is read, so probing all six would be six times the
Prometheus load for no additional information.

`VerifyMetricsReport.ok` is `True` iff no `Finding` has `level == "error"` —
`cli.py`'s `verify-metrics` handler uses exactly this property to decide the
process exit code, so there is one definition of "the verification passed."

## What `cli.py` does with the report

`_handle_verify_metrics` in `cli.py` constructs a `PrometheusClient` from
`resolved.config.prometheus`, calls `verify_metrics()`, and renders either
the human form (`[level] message` lines) or, under `--json`, a
JSON-serializable dict — `DiskKey` keys are turned into `"vmid:device"`
strings there, since JSON object keys must be strings and this module keeps
no opinion about output formatting.
