# `anonymize.py`, `collect.py`, `replay.py` — diagnostic bundles

`IMPLEMENTATION_PLAN.md` section 16 is the specification. This page
shows the shape of the implementation for the next developer who
changes the code.

## Why three modules, not one

- **`anonymize.py` is pure.** The module has no I/O beyond two small
  salt-file helpers. It has no dependency on `pve.py` or `metrics.py`.
  It holds the allowlist and the pseudonym function, nothing else.
  `collect.py` imports it to write a bundle.
  `tests/corpus/validate_corpus.py` imports it to check one. That is
  the "single implementation" AGENTS.md section 5 asks for. The audit
  cannot drift from what the collector permits.
- **`collect.py` is the one thing that talks to the real cluster** for
  this feature. It never imports `replay.py`.
- **`replay.py` reads a bundle back.** It imports `collect.py` only for
  two tiny pure functions (`hash_query_text`/`hash_label_name`). The
  cache-key scheme has to agree exactly between the module that writes
  a bundle and the module that reads it back. The scheme therefore
  lives in one place, written first.

## Capture: recording clients, not a second code path

`capture_bundle()` does **not** re-implement what `verify_metrics()` or
`build_topology()` do. It wraps the real `PveClient`/`PrometheusClient`
in `RecordingPveClient`/`RecordingPrometheusClient`. It hands those to
the exact same functions a live `plan`/`show-load`/`verify-metrics` run
already calls. It lets every response pass through on its way back to
the caller.

- `RecordingPveClient` overrides each of `pve.py`'s twelve read
  methods individually. Each override catches `PveApiError`. It
  records the outcome (`ok`/`http_error`/`empty`) in the manifest's
  `calls` list. On failure it returns a safe empty default (`{}`/`[]`)
  instead of raising. Section 16.2 states "failures are recorded,
  never rendered as absence". The client applies that rule at the
  transport boundary. `build_topology()` itself never needs to know it
  is running under capture.
- `RecordingPrometheusClient` overrides only `_get()`. Every public
  method routes through this one funnel. Unlike the PVE side, the
  client **does not** swallow a failure. It records the failure and
  re-raises it. This matches what the real client does.
  `verify_metrics()`'s own error handling already covers that case
  correctly. The client also accumulates every `(path, params,
  response)` triple it has ever served, in call order.

That accumulator is the reason `collect.py`'s own driver functions
(`_drive_group_series()`, `_drive_label_values()`) stay small. They
only *issue* the calls that section 16.2 requires for this bundle.
Once `verify_metrics()` and both drivers have run against one
`RecordingPrometheusClient`, `_anonymize_captured_prometheus()` walks
the whole accumulator exactly once. It turns the accumulator into
bundle files. Capture is complete because the code records every query
that ran. It does not depend on a correct guess of every internal
query that `metrics.py` might issue. The queries include the bare
per-metric sample check, the coverage probe, the observed-spacing
probe, and `label_values("__name__")`. `collect.py`'s own driver
functions construct no such query by hand.

### Range queries: chunk, then stitch by query text

A capture range can span days. A single `query_range` call over the
range can hit a backend's own `max_samples` limit.
`_issue_range_chunks()` issues one `range_query()` call per day-sized
chunk. It does **nothing else**. No stitching happens at issue time.
`_anonymize_captured_prometheus()` groups every accumulated
`query_range` call by its *query text*. The group holds however many
chunks exist. It also holds `verify_metrics()`'s own single spacing
probe if its text happens to coincide. That probe uses a different
window. `_stitch_range_captures()` merges the group into one
`(start, end, step, result)`. The merge takes the widest start/end
span. It keeps one series per disk. It deduplicates every point from
every chunk by timestamp. The result is one file per query text,
regardless of how many separate HTTP calls produced its content.

### `now` has to be controllable, all the way down

Section 16.1 promises: "two captures of an unchanged cluster produce
byte-identical bundles". The promise only holds if every query
genuinely depends on `capture_bundle()`'s own `now` parameter. It also
holds only if nothing captures `time.time()` on its own. Two functions
did so originally, independent of this feature:
`metrics.compute_disk_coverage()` and `metrics._check_observed_spacing()`.
Both gained an optional `now: float | None = None` parameter. The
default is the real wall clock, so every *live* caller stays
unaffected. `collect.py` passes the parameter explicitly now. The same
problem applies to a replayed `plan`/`show-load`/`explain`/
`verify-metrics` run. `cli.py`'s `_now_for()` also passes the
parameter explicitly. `loadmodel.compute_group_load()` picked up the
same optional `now`. It forwards the value to
`compute_disk_coverage()`, for the same reason.

### Node selector: anonymized names, captured verbatim

The node-scoping selector (`resolve_node_selector()`, section 3.4) is
built into the query *text*. This module captures that text and writes
it into a bundle file's `"query"` field. The *live* query must use the real node names, because Prometheus knows no
other names. The *captured* text must not: real names would leak into the
bundle, and a later `--replay` run would build different query text and never
match. That run builds the selector from `ReplayPveClient.node_names()`, which
returns pseudonyms. `_capture_prometheus_files()` therefore builds the selector
twice. It calls `resolve_node_selector()` with the real names for the live query.
It calls `build_node_selector()` with the names mapped through `mapper.node()` for
the captured text. The captured text and the replayed text thus come from the
same anonymized inputs.

## Anonymization: allowlist, then pseudonym, then timestamp

`anonymize.py`'s `Mapper` is a plain dataclass. It holds the salt plus
one piece of real state: `_vmid_map`. The state exists because a vmid
pseudonym cannot be a pure function of the salt and the vmid alone. A
node or storage pseudonym is such a function. The `Mapper.vmid()` hash
produces a value in the fixed range (`100..999999`). When two
different real vmids hash to the same candidate, the second one steps
to `candidate + 1`. It keeps stepping, wrapping back to the low end of
the range, until it finds a value nothing has claimed yet. Linear
probing resolves the collision. An open-addressing hash table uses the
same technique. The scheme must be *order-independent*. The same
original vmid must map to the same pseudonym regardless of the order a
caller visits the VMs in. `register_vmids()` is the only place that
matters. It sorts every not-yet-seen vmid. It assigns the pseudonyms
once, up front. Every other `Mapper` method (`node()`, `storage()`,
`tag()`, ...) is a pure function of the salt and its own argument.
Those methods need no registration.

**Fail closed, everywhere.** A method returns `None` when it cannot
resolve its input to something already known. The unresolvable inputs
include a storage outside every group, a UPID naming a node that has
left the cluster, and a vmid never registered. Every caller in
`collect.py` treats `None` as "drop this record". It never treats
`None` as "pass the original through". It never treats `None` as
"invent a placeholder". Section 16.3 states the rule as "unmapped
means dropped". The tool prefers the failure mode of a smaller bundle
over the failure mode of a leak, unconditionally.

**An allowlisted key is not a scrubbed value.** `CLUSTER_TASK_FIELDS`
allows a task's `id`. For a VM task, that `id` is the vmid. The UPID
embeds the same vmid. `_anonymize_cluster_tasks()` once mapped the UPID
and copied `id` through untouched. A bundle then carried each real
vmid right next to its pseudonym. A small integer passes every
value-pattern check. The leak was found by reading a real bundle by
hand. `_anonymize_cluster_tasks()` now takes `id` from the mapped
UPID. It drops `id` from an entry with no UPID. The scrub audit
(`validate_corpus._scrub_task_ids()`) checks that every task's `id`
equals the id its UPID carries.

**Free text gets a second look.** A handful of `verify_metrics()`
finding messages embed real values in human-readable prose. The values
include a sample series' raw label dict and a coverage gap's
`vmid:device`. The allowlist alone does not catch this. It operates on
structured keys, not on substrings of a message string.
`collect._redact_finding_message()` is a deliberately broad regex
substitution. It rewrites any whole number that matches an
already-registered real vmid. It rewrites any occurrence of a real
node name. The code applies it to every finding message, not just the
ones known to need it. Over-redaction rewrites a coincidentally
vmid-shaped number that was not actually a vmid. That direction of
error is the safe one here.

## Replay: real subclasses, not lookalikes

`ReplayPveClient(PveClient)` and `ReplayPrometheusClient(PrometheusClient)`
are genuine subclasses. Their `super().__init__()` call takes an inert
transport: `api=None`, and a session whose `get()` raises. This design
keeps every existing `client: PveClient`/`client: PrometheusClient`
type annotation in `topology.py`, `metrics.verify_metrics()`,
`loadmodel.py` and `cli.py` working with zero changes anywhere else.
`ReplayPveClient` overrides each of the eleven read methods directly.
The methods are keyed by the bundle's own directory layout. VM files
use the vmid only. The bundle does not key by node, since
`topology.py` always already knows the right node before calling.
Neither `move_disk` nor `task_status` can be reached in practice.
`apply` is refused before any handler gets this far. Both methods
raise `PveApiError` anyway. Defense in depth costs one `raise` each.

`vm_pending()` is the one method here that does not raise `BundleError`
on a missing file. A bundle captured before section 3.8 added the call
has no `pve/vm-pending/` directory at all. The code reads a missing
file there as "nothing pending", not as a corrupt bundle. A bundle
captured since that change always writes the file for every considered
VM. `collect.py`'s `_capture_pve_vm_files()` writes the file even when
the list is empty. The fallback can only trigger on a bundle that
genuinely predates the feature. It is not a general "missing means
empty" rule for this class.

`ReplayPrometheusClient` overrides only `_get()`. Its `/api/v1/query`
branch is an exact match on the anonymized query text. An instant
query carries no separate time parameter. Nothing else provides a
key. Its `/api/v1/query_range` branch is *not* an exact match on the
literal requested `start`/`end`. See "Range queries" above for why a
bundle stores one superset span per query text. See also
[`replay.py`](../../src/proxmox_storage_drs/replay.py)'s own module
docstring. It describes the trimming logic. The logic serves a
narrower request out of the stored span. That request comes from a
different model with a smaller history requirement. A request outside
the stored span raises a `BundleError`. A request at a different
`step` raises a `BundleError`. The error names the query and both
ranges. The code never returns a silent empty result.

`bundle_reference_now()` returns the bundle's own rebased capture
instant. It reads the value from `manifest.json`'s
`capture.synthetic_now_epoch`. `cli._now_for()` substitutes the same
value for `datetime.now(timezone.utc)`. It does so everywhere a handler
builds a query time window under `--replay`. The manifest never
carries the real capture date (section 16.3). The stored value is
`now`, already shifted by the same whole-week offset every other
timestamp in the bundle goes through. Only hour-of-day and
day-of-week survive.
