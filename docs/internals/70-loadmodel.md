# The load model

**What does this page answer?** How does `loadmodel.py` turn six raw
Prometheus series into the single per-disk `ℓ_d` section 4 defines? What
happens when the data for one disk cannot be trusted? This page describes
`proxmox_storage_drs/loadmodel.py`.

## One function, one group, already-built input

`compute_group_load()` takes an already-built `topology.Group`. That is
one group's `D`/`S` (section 5.1). It also takes a
`metrics.PrometheusClient`. The function returns a `GroupLoad`. The value
holds one `DiskLoad` per disk (`ℓ_d`) and one `StorageLoad` per storage
(`L_s`, `u_s`). It also holds the group's `u*` and whether the whole group
is idle. The function never touches the PVE API. It never builds topology
itself. This matches `reserve.py`'s identical "given the join, evaluate
one formula" framing. The match is no coincidence. `cli.py` calls the
function exactly once per group. The solver consumes that same set of
per-disk `ℓ_d` values against every *candidate* assignment it considers.
The solver is `heuristic.py`'s `run_heuristic()`, via
`GroupLoad.load_by_disk_key()`. It does not recompute load per candidate.

## Six queries, scoped to the group

The module fetches the six raw quantities (section 3.4). It sends **one
instant query each**, scoped to the calling group's own vmids. It uses
`metrics.group_query_selectors()` for the scope. An unscoped
`sum by (vmid, device) (...)` would return every disk Prometheus currently
reports. Picking out one group's keys in Python used to be the whole
story. REVIEW.md Q-02 (below) is why that stopped being true. The module
converts `read_time_ns`/`write_time_ns` from nanoseconds to seconds here,
engine-side (`_combined_raw`). The reason matches the one F-03 used to
move `read_factor`/`write_factor` engine-side. One tested constant beats
the same `/1e9` repeated across deployed PromQL strings.

**REVIEW.md Q-02, revisited.** The original design fetched these six
queries *unfiltered by group*. The theory was that Python-side filtering
was free. Six more Prometheus queries per group was not free. The theory
held. The team accepted it as a "Low, wasteful but correct" limitation.
The project was designed against 1-3-group deployments. The limitation
stopped being merely wasteful. A real cluster hit it. The cluster had
several hundred VMs spread across many groups. Every group's plan
re-issued the *same* unfiltered, cluster-wide aggregation.
Prometheus/gigapipe's own query evaluator timed out on it outright. The
message was "query timed out in expression evaluation". The result was not
wasteful, it was broken. `metrics.group_query_selectors()` now scopes
every such query. The queries are this module's six raw quantities,
`compute_disk_load_series()`'s own forecast history fetch, and
`metrics.compute_disk_coverage()`. The scope is the calling group's own
vmids. When a single group is large enough, the fetch splits into
`metrics.VMID_QUERY_BATCH_SIZE`-sized batches. The function merges the
batches back into one logical result. It splits when even the group's own
aggregation would be too big for one query. A config with `N` groups still
makes `7N` queries. The redundancy is unchanged. Each group's
coverage/rejection decisions are independent. The fetch still cannot be
shared across groups. The redundancy is still just a performance note for
a many-group deployment. Each of those `7N` queries now aggregates only
the disks that group actually has. It does not aggregate the whole
cluster.

## Coverage rejection excludes a disk from the group total, not just from its own `ℓ_d`

Section 3.4 states the rule: "reject a disk whose sample coverage over `W`
is below `window.min_coverage` and fall back to its last known load from
`state.json`... never treat missing data as zero load." Two things deserve
an explicit statement. The plan states the rule, but not this mechanism:

1. **The module excludes the rejected disk's raw contribution from
   `T_g`/`O_g`/`B_g` entirely**. It does not merely cap or zero the value
   in place. One noisy or half-missing series must not bias every *other*
   disk's normalized share. The module computes `ℓ_d` for every accepted
   disk from the accepted-only totals.
2. **The module substitutes the rejected disk's own `ℓ_d` afterward**. It
   takes the value from `last_known_loads` if the caller has one (keyed by
   `topology.Disk.key`). If the caller has no seed, the module flags
   `0.0`. `DiskLoad.flagged_reason` is set either way. A caller can never
   mistake a flagged `0.0` for a genuinely idle disk. `show-load` renders
   it as an explicit `⚠` line, never silently.

`state.py` (section 11.2) now provides the real `last_known_loads`
source. `cli.py`'s `show-load` and `plan` both pass
`state.load_vector_for_group(state, group.name)` through unchanged. The
mapping is exactly what this function already expected (see
`docs/internals/15-state.md`). `compute_group_load()` itself needed no
change at all. The parameter was shaped for this from the start. A group
with no recorded balance yet gets `None`. The group has a fresh
`state.json`, or none on disk. Every coverage-rejected disk with no seed
is flagged `0.0`, exactly as before.

## `tpmstate0`/`unusedN` are never rejected; `efidisk0` is

Section 3.4's own note: `tpmstate0` and `unusedN` are not QEMU block
devices. They legitimately emit no `blockstat` series. `ℓ_d = 0` for them
is correct, not a data-quality problem. `_is_metrics_expected_absent()`
encodes exactly this device-name distinction. These two kinds are never
flagged for low coverage. `efidisk0` is a real QEMU drive. It *should*
appear. The module holds it to the same `min_coverage` bar as
`scsi`/`virtio`/`ide`/`sata`. Getting this backwards either way is a real
bug. Exempting `efidisk0` would hide a genuine metrics gap on it. Not
exempting `tpmstate0`/`unusedN` would print a flag on every run, for every
cluster. The "gap" would not be one.

## `T_g = 0` is "idle", computed only from accepted disks

`GroupLoad.idle` is `True` exactly when every *accepted* disk's `raw_t` is
zero. This is the guard section 4 requires ("if `T_g = 0` the entire group
is idle, skip it"). An all-rejected group also comes out `idle=True` by
this same computation. The group has a total Prometheus outage mid-window,
for example. The result is not quite literally accurate. The truth is
"unknown", not "idle". The result is harmless. Both outcomes mean "do not
act". That is the only decision that follows from either. A caller can
distinguish the two. Every disk's `flagged_reason` is still there to
check.

## `L_s`/`u_s` are the *current* assignment, not a candidate one

`StorageLoad` sums `ℓ_d` over disks whose `Disk.current_storage` already
points at that storage. This is today's state, exactly like `reserve.py`'s
`compute_reserve_status()`. `u_s = L_s / c_s`. `c_s` is
`storage.capability_weight`. This is a per-storage config knob (default
`1.0`, see `config/drs.example.yaml`). An operator lowers it to say "this
storage should carry a smaller *share* of the group's load than an
equal-weighted one would." Example: `0.5` for a storage with half the
spindles of its peers. `u_s` is load-per-unit-of-declared-capability. It
is not a byte-fill percentage. The gate/objective's notion of "imbalanced"
is about I/O share, not free space. Free space is (C4)/(C5)'s job
(`docs/internals/60-topology.md`). `GroupLoad.average_utilization` (`u*`)
is the group-wide counterpart. The value is `(Σ_d ℓ_d) / (Σ_s c_s)`. That
is total load over total declared capability across every storage in the
group (section 5.3 (C6)). The solver re-sums the identical per-disk `ℓ_d`
values against each *candidate* assignment it considers. The solver is
`heuristic.py`'s `evaluate_assignment()` or `optimize.py`'s MILP encoding
(see `90-heuristic.md`/`91-optimize.md`). It uses its own `storage_of()`
lookup in place of `Disk.current_storage`. `loadmodel.py` itself needed no
change for that. `ℓ_d` does not depend on which storage a disk is
currently on.

## `compute_disk_load_series()`: the same blend, as a time series

`compute_group_load()` reduces each raw quantity to one already-quantile'd
scalar per disk. It uses `quantile_over_time` at query time. Section 10's
forecast needs the opposite. It needs the *raw* per-disk `ℓ_d` signal,
unreduced. It needs it over a range and step of its own choosing. The
choice is typically `forecast.required_range_seconds()`, not
`window.lookback`. Section 10.1 is explicit that these are "genuinely
different things". `compute_disk_load_series()` fetches the identical six
`rate(...)` expressions `_fetch_raw_quantity()` builds. It uses
`query_range`, instead of wrapping in `quantile_over_time` and
`instant_query`. The function then runs section 4's exact
normalize-then-weight-then-rescale blend once **per timestamp**, instead of
once. `_combine_raw_values()`/`_blend_loads()` factor that formula out to
plain-number arguments. Both this function and `compute_group_load()` call
the identical implementation (AGENTS.md section 5). The extraction is then
proven behavior-preserving. `test_loadmodel.py`'s full existing suite
passed unchanged, before any series-specific test was added. This is the
same regression-by-refactor discipline `reserve.transient_charge_ok()`'s
own extraction used.

Every disk in the group gets an entry, even an empty one. Unlike
`compute_group_load()`, this function does not apply `window.min_coverage`
at all. The forecast history is a much longer, coarser signal. That rule
was built to validate a shorter signal. A sparse history is exactly what a
fit needs to see to refuse to trust itself. This is section 10's raw
material for a forecast of each disk's load. See
[`20-forecasting.md`](20-forecasting.md) and `apply_forecast()` below.

## `apply_forecast()`: scaling, never replacing

`apply_forecast(group_load, group, factors)` multiplies each disk's `ℓ_d`
by its factor `f_d / h_d`. The factor is the forecast p95 over the
observed p95 of the same series. The per-timestamp series and
`compute_group_load()`'s window-level `ℓ_d` are normalized differently.
Only a ratio is meaningful. The function rebuilds each storage's
`L_s`/`u_s` and the group's `u*` from the scaled loads. A disk without a
factor keeps its observed load exactly. Any disk with a `flagged_reason`
keeps its observed load exactly. `idle` and `no_series_matched` are
untouched. `cli._compute_group_load()` calls the function from both
`show-load` and `plan`/`apply`. A group's gates and its plan always see
the same `ℓ`.

## What `loadmodel.py` is, and is not, responsible for

`loadmodel.py` is the load computation the rest of the engine consumes.
`compute_group_load()`'s `ℓ_d`/`L_s`/`u_s` feed `gates.py`'s
drift/imbalance gates ([`80-gates.md`](80-gates.md)). `reserve.py`'s
reserve override is computed separately, straight from the group's
disks/storages. It does not go through this module.
`compute_disk_load_series()` feeds a section 10 forecast. This module
decides none of those verdicts itself. `pve-storage-drs show-load` reports
`ℓ_d`/`L_s`/`u_s` directly. Deciding whether a group should be
re-balanced at all is `gates.py`'s job, not this module's.
