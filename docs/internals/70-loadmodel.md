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
framing, not a coincidence: both are meant to be called again, unchanged,
by the solver once it exists.

## Six queries, not six-times-groups queries

The six raw quantities (section 3.4) are fetched with **one instant query
each**, unfiltered by group — `sum by (vmid, device) (...)` already returns
every disk Prometheus currently reports, and picking out one group's keys
in Python is free, whereas six *more* Prometheus queries per group is not.
`read_time_ns`/`write_time_ns` are converted from nanoseconds to seconds
here, engine-side (`_combined_raw`), for the same reason F-03 moved
`read_factor`/`write_factor` engine-side: one tested constant beats the
same `/1e9` repeated across deployed PromQL strings.

**Known limitation, not a bug:** a config with more than one group re-runs
these same six unfiltered queries once per group — correct (each group's
coverage/rejection decisions are independent) but wasteful for a many-group
cluster. Fetching once and slicing per group would be a straightforward
follow-up if a real deployment's group count ever makes this Prometheus
load worth avoiding; nothing about `compute_group_load()`'s per-group
signature forces the current one-fetch-per-call shape, it is just what the
first implementation does.

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

`state.json` persistence (the actual `last_known_loads` source) is not yet
written (section 11.2) — `compute_group_load()` accepts the mapping today
so this module needs no change when it exists; until then every call site
passes nothing, and every coverage-rejected disk with no seed is flagged
`0.0`, honestly.

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
`compute_reserve_status()`. The solver (`optimize.py`/`heuristic.py`, not
yet written) will evaluate the identical per-disk `ℓ_d` values against a
*candidate* assignment instead; nothing in `loadmodel.py` needs to change
for that, since `ℓ_d` itself does not depend on which storage a disk is
currently on.

## What is still missing from phase 3

`IMPLEMENTATION_PLAN.md` section 12 phase 3's own "done when" is "correct
act/no-act decision per group, with the reasoning shown" — that is the
section 6 drift/imbalance gates, cooldowns, and the reserve override, none
of which exist yet. `loadmodel.py` is the load computation those gates
consume, not the gates themselves; `pve-storage-drs show-load` reports
`ℓ_d`/`L_s`/`u_s` today, but no command yet decides whether a group should
be re-balanced.
