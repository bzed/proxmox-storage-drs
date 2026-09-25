# The load model

**What does this page answer?** How does `loadmodel.py` turn six raw
Prometheus series into the single per-disk `ℓ_d` section 4 defines, and
what happens when the data for one disk cannot be trusted? Describes
`proxmox_storage_drs/loadmodel.py`.

## One function, one group, already-built input

`compute_group_load()` takes an already-built `topology.Group` (one
group's `D`/`S`, section 5.1) and a `metrics.PrometheusClient` and returns
a `GroupLoad`: one `DiskLoad` per disk (`ℓ_d`) and one `StorageLoad` per
storage (`L_s`, `u_s`), plus the group's `u*` and whether the whole group
is idle. It never touches the PVE API and never builds topology itself —
matching `reserve.py`'s identical "given the join, evaluate one formula"
framing, not a coincidence: `cli.py` calls it exactly once per group, and
the solver (`heuristic.py`'s `run_heuristic()`, via `GroupLoad.load_by_disk_key()`)
consumes that same set of per-disk `ℓ_d` values against every *candidate*
assignment it considers, rather than recomputing load per candidate.

## Six queries, scoped to the group

The six raw quantities (section 3.4) are fetched with **one instant query
each**, scoped to the calling group's own vmids
(`metrics.group_query_selectors()`) — `sum by (vmid, device) (...)` would
already return every disk Prometheus currently reports if left unscoped,
and picking out one group's keys in Python used to be the whole story, but
REVIEW.md Q-02 (below) is why that stopped being true.
`read_time_ns`/`write_time_ns` are converted from nanoseconds to seconds
here, engine-side (`_combined_raw`), for the same reason F-03 moved
`read_factor`/`write_factor` engine-side: one tested constant beats the
same `/1e9` repeated across deployed PromQL strings.

**REVIEW.md Q-02, revisited.** The original design fetched these six
queries *unfiltered by group* on the theory that Python-side filtering was
free and six more Prometheus queries per group was not — correct, and
accepted as a "Low, wasteful but correct" limitation for the 1-3-group
deployments this project was designed against. It stopped being merely
wasteful once a real cluster with several hundred VMs spread across many
groups hit it: every group's plan re-issued the *same* unfiltered,
cluster-wide aggregation, and Prometheus/gigapipe's own query evaluator
timed out on it outright ("query timed out in expression evaluation") —
not wasteful, broken. `metrics.group_query_selectors()` scopes every such
query (this module's six raw quantities, `compute_disk_load_series()`'s
own forecaster history fetch, and `metrics.compute_disk_coverage()`) to
the calling group's own vmids, splitting into
`metrics.VMID_QUERY_BATCH_SIZE`-sized batches (merged back into one
logical result) when a single group itself is large enough that even its
own aggregation would be too big for one query. A config with `N` groups
still makes `7N` queries — that redundancy (each group's coverage/rejection
decisions are independent, so the fetch still cannot be shared across
groups) is unchanged and still just a performance note for a many-group
deployment — but each of those `7N` queries now aggregates only the disks
that group actually has, not the whole cluster.

## Coverage rejection excludes a disk from the group total, not just from its own `ℓ_d`

Section 3.4: "reject a disk whose sample coverage over `W` is below
`window.min_coverage` and fall back to its last known load from
`state.json`... never treat missing data as zero load." Two things worth
being explicit about, since the plan states the rule but not this
mechanism:

1. **The rejected disk's raw contribution is excluded from `T_g`/`O_g`/`B_g`
   entirely**, not merely capped or zeroed in place — one noisy or
   half-missing series must not bias every *other* disk's normalized
   share. `ℓ_d` for every accepted disk is computed from the accepted-only
   totals.
2. **The rejected disk's own `ℓ_d` is substituted afterward**, from
   `last_known_loads` if the caller has one (keyed by `topology.Disk.key`),
   or flagged `0.0` if not. `DiskLoad.flagged_reason` is set either way, so
   a caller can never mistake a flagged `0.0` for a genuinely idle disk —
   `show-load` renders it as an explicit `⚠` line, never silently.

`state.py` (section 11.2) now provides the real `last_known_loads` source:
`cli.py`'s `show-load` and `plan` both pass
`state.load_vector_for_group(state, group.name)` through unchanged, exactly
the mapping this function already expected (see `docs/internals/15-state.md`).
`compute_group_load()` itself needed no change at all — the parameter was
shaped for this from the start. A group with no recorded balance yet (a
fresh `state.json`, or none on disk) still gets `None`, and every
coverage-rejected disk with no seed is flagged `0.0`, exactly as before.

## `tpmstate0`/`unusedN` are never rejected; `efidisk0` is

Section 3.4's own note: `tpmstate0` and `unusedN` are not QEMU block
devices and legitimately emit no `blockstat` series — `ℓ_d = 0` for them is
correct, not a data-quality problem. `_is_metrics_expected_absent()`
encodes exactly this device-name distinction so these two kinds are never
flagged for low coverage, while `efidisk0` — a real QEMU drive that
*should* appear — is held to the same `min_coverage` bar as
`scsi`/`virtio`/`ide`/`sata`. Getting this backwards either way is a real
bug: exempting `efidisk0` would hide a genuine metrics gap on it; not
exempting `tpmstate0`/`unusedN` would spam a flag on every run for every
cluster, for a "gap" that isn't one.

## `T_g = 0` is "idle", computed only from accepted disks

`GroupLoad.idle` is `True` exactly when every *accepted* disk's `raw_t` is
zero — the guard section 4 requires ("if `T_g = 0` the entire group is
idle, skip it"). An all-rejected group (e.g. a total Prometheus outage
mid-window) also comes out `idle=True` by this same computation, which is
not quite literally accurate (the truth is "unknown", not "idle") but is
harmless: both mean "do not act", which is the only decision that follows
from either. A caller that wants to distinguish the two can — every
disk's `flagged_reason` is still there to check.

## `L_s`/`u_s` are the *current* assignment, not a candidate one

`StorageLoad` sums `ℓ_d` over disks whose `Disk.current_storage` already
points at that storage — today's state, exactly like `reserve.py`'s
`compute_reserve_status()`. `u_s = L_s / c_s`, where `c_s` is
`storage.capability_weight` — a per-storage config knob (default `1.0`,
see `config/drs.example.yaml`) an operator lowers to say "this storage
should carry a smaller *share* of the group's load than an equal-weighted
one would," e.g. `0.5` for a storage with half the spindles of its peers.
`u_s` is therefore load-per-unit-of-declared-capability, not a byte-fill
percentage — the gate/objective's notion of "imbalanced" is about I/O
share, not free space (that is (C4)/(C5)'s job, `docs/internals/60-topology.md`).
`GroupLoad.average_utilization` (`u*`) is the group-wide counterpart,
`(Σ_d ℓ_d) / (Σ_s c_s)` — total load over total declared capability across
every storage in the group, section 5.3 (C6). The solver
(`heuristic.py`'s `evaluate_assignment()`, `optimize.py`'s MILP encoding —
see `90-heuristic.md`/`91-optimize.md`) re-sums the identical per-disk
`ℓ_d` values against each *candidate* assignment it considers, using its
own `storage_of()` lookup in place of `Disk.current_storage`; `loadmodel.py`
itself needed no change for that, since `ℓ_d` does not depend on which
storage a disk is currently on.

## `compute_disk_load_series()`: the same blend, as a time series

`compute_group_load()` reduces each raw quantity to one already
-quantile'd scalar per disk via `quantile_over_time` at query time.
Section 10's forecaster needs the opposite: the *raw* per-disk `ℓ_d`
signal, unreduced, over a range and step of its own choosing (typically
`forecast.required_range_seconds()`, not `window.lookback` — section 10.1
is explicit these are "genuinely different things"). `compute_disk_load_series()`
fetches the identical six `rate(...)` expressions
`_fetch_raw_quantity()` builds, `query_range`'d instead of wrapped in
`quantile_over_time` and `instant_query`'d, then runs section 4's exact
normalize-then-weight-then-rescale blend once **per timestamp** instead
of once. `_combine_raw_values()`/`_blend_loads()` are that formula
factored out to plain-number arguments so both this function and
`compute_group_load()` call the identical implementation (AGENTS.md
section 5) — extracted, then proven behavior-preserving by
`test_loadmodel.py`'s full existing suite passing unchanged before any
series-specific test was added, the same regression-by-refactor
discipline `reserve.transient_charge_ok()`'s own extraction used.

Every disk in the group gets an entry, even an empty one — unlike
`compute_group_load()`, this function does not apply `window.min_coverage`
at all: a forecaster's own `required_range()` is a much longer, coarser
signal than that rule was built to validate, and a sparse history is
exactly what the forecaster itself needs to see to distrust its own fit.
This is section 10's raw material for a forecast of each disk's load
(phase 14b wires it into `cli.py`).

## What `loadmodel.py` is, and is not, responsible for

`loadmodel.py` is the load computation the rest of the engine consumes —
`compute_group_load()`'s `ℓ_d`/`L_s`/`u_s` feed `gates.py`'s drift/imbalance
gates ([`80-gates.md`](80-gates.md); `reserve.py`'s reserve override is
computed separately, straight from the group's disks/storages, not through
this module), and `compute_disk_load_series()` feeds a section 10 forecast — but this
module decides none of those verdicts
itself. `pve-storage-drs show-load` reports `ℓ_d`/`L_s`/`u_s` directly;
deciding whether a group should be re-balanced at all is `gates.py`'s job,
not this one's.
