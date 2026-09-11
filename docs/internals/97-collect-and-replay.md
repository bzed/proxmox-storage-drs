# `anonymize.py`, `collect.py`, `replay.py` — diagnostic bundles

`IMPLEMENTATION_PLAN.md` section 16 is the specification. This page is
about the shape of the implementation, for whoever changes it next.

## Why three modules, not one

- **`anonymize.py` is pure.** No I/O beyond two small salt-file helpers,
  no dependency on `pve.py`/`metrics.py`. It is the allowlist and the
  pseudonym function, nothing else, and it is imported by both `collect.py`
  (to write a bundle) and `tests/corpus/validate_corpus.py` (to check one)
  — the "single implementation" AGENTS.md section 5 asks for, so the audit
  cannot silently drift from what the collector permits.
- **`collect.py` is the one thing that talks to the real cluster** for this
  feature. It never imports `replay.py`.
- **`replay.py` reads a bundle back.** It imports `collect.py` only for two
  tiny pure functions (`hash_query_text`/`hash_label_name`) — the cache-key
  scheme has to agree exactly between the module that writes a bundle and
  the one that reads it back, so it lives in one place, written first.

## Capture: recording clients, not a second code path

`capture_bundle()` does **not** re-implement what `verify_metrics()` or
`build_topology()` do. It wraps the real `PveClient`/`PrometheusClient` in
`RecordingPveClient`/`RecordingPrometheusClient`, hands those to the exact
same functions a live `plan`/`show-load`/`verify-metrics` run already
calls, and lets every response pass through on its way back to the caller.

- `RecordingPveClient` overrides each of `pve.py`'s ten read methods
  individually: catches `PveApiError`, records the outcome
  (`ok`/`http_error`/`empty`) in the manifest's `calls` list, and returns a
  safe empty default (`{}`/`[]`) on failure rather than raising — section
  16.2's "failures are recorded, never rendered as absence" applied at the
  transport boundary, so `build_topology()` itself never needs to know it
  is running under capture.
- `RecordingPrometheusClient` overrides only `_get()` (the one funnel every
  public method routes through) and, unlike the PVE side, **does not**
  swallow a failure — it records and re-raises, matching what the real
  client does, because `verify_metrics()`'s own error handling already
  covers that case correctly. It additionally accumulates every
  `(path, params, response)` triple it has ever served, in call order.

That accumulator is the reason `collect.py`'s own driver functions
(`_drive_group_series()`, `_drive_label_values()`) look thin: they only
need to *issue* the calls this bundle's own §16.2 requires. Once
`verify_metrics()` and both drivers have run against one
`RecordingPrometheusClient`, `_anonymize_captured_prometheus()` walks the
whole accumulator exactly once and turns it into bundle files — which is
what makes capture complete by construction rather than by having
correctly guessed every internal query `metrics.py` might issue (the bare
per-metric sample check, the coverage probe, the observed-spacing probe,
`label_values("__name__")` — none of which `collect.py`'s own driver
functions construct by hand).

### Range queries: chunk, then stitch by query text

A capture range can span days; a single `query_range` call over it can hit
a backend's own `max_samples` limit. `_issue_range_chunks()` issues one
`range_query()` call per day-sized chunk and does **nothing else** — no
stitching happens at issue time. `_anonymize_captured_prometheus()` groups
every accumulated `query_range` call by its *query text* and merges all of
them — however many chunks, plus `verify_metrics()`'s own single,
differently-windowed spacing probe if its text happens to coincide — into
one `(start, end, step, result)` via `_stitch_range_captures()`: widest
start/end span, one series per disk, every point from every chunk
deduplicated by timestamp. One file, one query text, regardless of how
many separate HTTP calls produced its content.

### `now` has to be controllable, all the way down

Section 16.1's determinism promise ("two captures of an unchanged cluster
produce byte-identical bundles") only holds if every query genuinely
depends on `capture_bundle()`'s own `now` parameter and nothing captures
`time.time()` on its own. Two functions did, originally, independent of
this feature: `metrics.compute_disk_coverage()` and
`metrics._check_observed_spacing()`. Both gained an optional `now: float |
None = None` (default: the real wall clock, so every *live* caller is
unaffected) that `collect.py` — and, since the same problem applies to a
replayed `plan`/`show-load`/`explain`/`verify-metrics` run,
`cli.py`'s `_now_for()` — now pass explicitly.
`loadmodel.compute_group_load()` picked up the same optional `now`,
forwarded to `compute_disk_coverage()`, for the same reason.

### Node selector: anonymized names, captured verbatim

The node-scoping selector (`resolve_node_selector()`, section 3.4) is
built into the query *text* this module captures and writes into a bundle
file's `"query"` field. If it were built from the real node list, two
things would go wrong at once: the real node names would leak into the
bundle, and a later `--replay` run — which reconstructs the identical
selector from `ReplayPveClient.node_names()`, itself pseudonymized — would
build different query text and never match. `_capture_prometheus_files()`
maps `known_nodes` through `mapper.node()` *before* handing them to
`resolve_node_selector()`, so the captured text and the replayed text are
built from the same (anonymized) inputs by construction.

## Anonymization: allowlist, then pseudonym, then timestamp

`anonymize.py`'s `Mapper` is a plain dataclass holding the salt plus one
piece of real state: `_vmid_map`, because vmid pseudonyms need the
section 16.3 linear-probing collision rule, and that rule has to be
*order-independent* — the same original vmid must map to the same
pseudonym regardless of which order a caller happens to visit VMs in.
`register_vmids()` is the only place that matters: it sorts every not-yet
-seen vmid before assigning, once, up front. Every other `Mapper` method
(`node()`, `storage()`, `tag()`, ...) is a pure function of the salt and
its own argument and needs no registration at all.

**Fail closed, everywhere.** A method that cannot resolve its input to
something already known — a storage outside every group, a UPID naming a
node that has left the cluster, a vmid never registered — returns `None`.
Every caller in `collect.py` treats `None` as "drop this record", never as
"pass the original through" and never as "invent a placeholder". This is
what section 16.3 means by "unmapped means dropped": the failure mode of a
smaller bundle is preferred over the failure mode of a leak, unconditionally.

**Free text gets a second look.** A handful of `verify_metrics()` finding
messages embed real values directly in human-readable prose (a sample
series' raw label dict, a coverage gap's `vmid:device`) — the allowlist
alone does not catch this, since it operates on structured keys, not on
substrings of a message string. `collect._redact_finding_message()` is a
deliberately broad regex substitution — any whole number matching an
already-registered real vmid, any occurrence of a real node name — applied
to every finding message, not just the ones known to need it. Over
-redaction (rewriting a coincidentally vmid-shaped number that was not
actually a vmid) is the safe direction to be wrong in here.

## Replay: real subclasses, not lookalikes

`ReplayPveClient(PveClient)` and `ReplayPrometheusClient(PrometheusClient)`
are genuine subclasses — `super().__init__()` with an inert transport
(`api=None`, a session whose `get()` raises) — specifically so that every
existing `client: PveClient`/`client: PrometheusClient` type annotation in
`topology.py`, `metrics.verify_metrics()`, `loadmodel.py` and `cli.py`
accepts one with zero changes anywhere else. `ReplayPveClient` overrides
each of the ten read methods directly, keyed by the bundle's own directory
layout (vmid-only for VM files — the bundle does not key by node, since
`topology.py` always already knows the right node before calling). Neither
`move_disk` nor `task_status` can be reached in practice (`apply` is
refused before any handler gets this far), but both raise `PveApiError`
anyway — defense in depth costs one `raise` each.

`ReplayPrometheusClient` overrides only `_get()`. Its `/api/v1/query`
branch is an exact match on the (anonymized) query text — an instant query
carries no separate time parameter, so there is nothing else to key on.
Its `/api/v1/query_range` branch is *not* an exact match on the literal
requested `start`/`end`: see "Range queries" above for why a bundle stores
one superset span per query text, and
[`replay.py`](../../src/proxmox_storage_drs/replay.py)'s own module
docstring for the trimming logic that serves a narrower request (a
different forecaster's own, smaller `required_range()`) out of it. A
request outside the stored span, or at a different `step`, is a
`BundleError` naming the query and both ranges — never a silent empty
result.

`bundle_reference_now()` returns the bundle's own rebased capture instant
from `manifest.json`'s `capture.synthetic_now_epoch` — the same value
`cli._now_for()` substitutes for `datetime.now(timezone.utc)` everywhere a
handler builds a query time window under `--replay`. The manifest never
carries the real capture date (section 16.3): what is stored is `now`
already shifted by the same whole-week offset every other timestamp in the
bundle goes through, so only hour-of-day and day-of-week survive.
