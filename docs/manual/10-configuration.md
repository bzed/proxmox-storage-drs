# Configuration reference

Every key `pve-storage-drs` reads is documented here: type, unit, default, what it
interacts with, and what happens if you set it too high or too low. A key
that exists in the schema but not here, or here but not in the schema, is a
bug — `tests/unit/test_documentation.py` asserts the two never drift apart.

`config/drs.example.yaml` in the source tree (installed to
`/usr/share/doc/pve-storage-drs/examples/drs.example.yaml`) carries the same defaults
with inline comments; this page is the full explanation each comment points
back to.

### `schema_version`

Integer, required, no default.

The config format's version. `pve-storage-drs` refuses to start on a `schema_version`
whose **major** number it does not understand, naming the version it does
understand in the error, rather than guessing at fields from a future
incompatible format. Currently `1`.

## `proxmox` — the cluster API connection

### `proxmox.host`

String, required, no default.

Any cluster member's hostname or IP. The API is reached at
`https://<host>:<port>/api2/json`.

### `proxmox.port`

Integer, default `8006`.

The PVE API port. Change this only if you have put something unusual (a
reverse proxy) in front of the API.

### `proxmox.verify_ssl`

Boolean, default `true`.

Whether to verify the API's TLS certificate. Set `false` only for a
self-signed certificate you cannot otherwise trust, and prefer
`proxmox.ca_file` instead where possible — disabling verification also
disables protection against a compromised network path to every node's API.

### `proxmox.ca_file`

String path or `null`, default `null`.

A CA bundle to verify the API's certificate against, when it is not signed
by a certificate already trusted by the host running `pve-storage-drs`.

### `proxmox.auth.username`

String or `null`.

A PVE user, e.g. `drs@pve`. Required unless `proxmox.auth.token_id` is set.
Username/password authentication is what the original requirement asked
for; an API token (below) is preferred for `execution.mode: auto` because it
needs no interactive ticket refresh and can be scoped tightly: the tool's
actual minimum privilege is `Datastore.Audit` **and** `Datastore.Allocate` on
every storage in the config's `groups`, plus `VM.Config.Disk` and
`VM.Migrate` (or an equivalent custom role) on the VMs it may move.
`Datastore.Audit` alone is not enough — PVE's per-volume content listing
silently returns an *empty* result with no error when only Audit is
granted, which would make every tracked disk look untracked rather than
raising anything you'd notice. Grant the role per storage rather than
relying on propagation from the parent `/storage` path, and remember that
an API token's effective permission is the **intersection** of the user's
own grants and the token's own: both need the grant, or neither has it.
(`IMPLEMENTATION_PLAN.md` section 3.5.)

### `proxmox.auth.password`

String or `null`, default `null`, environment: `PVE_PASSWORD`.

Leave this `null` in the file and set `PVE_PASSWORD` in the environment (or a
systemd credential) instead, especially when the config lives on `/etc/pve`
and is therefore group-readable by `www-data`. A password given in the file
is used as-is and is **not** overridden by the environment variable — see
[`00-installation.md`](00-installation.md) for why the file's own
permissions matter here.

### `proxmox.auth.token_id`

String or `null`, default `null`.

An API token id, e.g. `drs@pve!balancer`. Set this instead of
`username`/`password` for unattended operation; a token needs no ticket
refresh loop and can be revoked independently of the user's password.

### `proxmox.auth.token_secret`

String or `null`, default `null`, environment: `PVE_TOKEN_SECRET`.

The secret half of the API token, with the same environment-variable
preference as `proxmox.auth.password`.

### `proxmox.ticket_refresh_seconds`

Duration, default `3000` (50 minutes).

How often a username/password ticket is refreshed. PVE tickets last
approximately two hours; refreshing well before that avoids a mid-run
authentication failure. Not used for API-token authentication, which needs
no ticket. Implemented by overriding `proxmoxer`'s own (otherwise
fixed-at-3600s) refresh interval after login, since `proxmoxer` has no
constructor option for it; if a ticket somehow still gets rejected mid-run
regardless (a long `confirm`-mode wait, a suspended process, a clock jump —
see `50-pve-api.md`), the client transparently logs in again from scratch
and retries the one call that failed, once, before giving up.

### `proxmox.read_workers`

Integer, default `12`.

Size of the bounded thread pool used to fetch per-VM configuration —
`GET /nodes/{node}/qemu/{vmid}/config` has no batch form, so this is what
keeps a several-hundred-VM cluster's topology read from being serial.
Raising it trades API server load for wall-clock time; 8–16 is the range the
plan suggests. Too high a value on a small PVE API server can itself become
the bottleneck. Only the per-VM fetch is parallelized; the cluster-wide and
per-storage calls (`50-pve-api.md`) still run once each, sequentially,
before it starts.

## `prometheus` — the metrics source

### `prometheus.url`

String, required, no default.

The base URL of your Prometheus, e.g. `http://prometheus.example.com:9090`.

### `prometheus.timeout_seconds`

Duration, default `30`.

Per-request timeout against Prometheus. Too low a value on a busy or
long-range query makes `verify-metrics` and the load model fail spuriously;
too high a value delays noticing that Prometheus is actually unreachable.

### `prometheus.username` / `prometheus.password`

String or `null`, default `null`.

HTTP basic auth credentials, if your Prometheus requires them. Ignored when
`prometheus.bearer_token` is set.

### `prometheus.bearer_token`

String or `null`, default `null`.

A bearer token for Prometheus instances behind an auth proxy that expects
one. Takes precedence over basic auth when both are set.

## `metrics` — Telegraf/InfluxDB name mapping

Telegraf's naming is deployment-specific (`IMPLEMENTATION_PLAN.md` section
3.3), so every name below is configuration, never a constant. Run
`pve-storage-drs verify-metrics` after changing any of them — see
[`20-verifying-metrics.md`](20-verifying-metrics.md).

### `metrics.read_ops`

String, default `blockstat_rd_operations`.

The Prometheus metric name for per-disk read operations/second (raw
counter, before `rate()`).

### `metrics.write_ops`

String, default `blockstat_wr_operations`.

As `metrics.read_ops`, for writes.

### `metrics.read_bytes`

String, default `blockstat_rd_bytes`.

The Prometheus metric name for per-disk bytes read (raw counter).

### `metrics.write_bytes`

String, default `blockstat_wr_bytes`.

As `metrics.read_bytes`, for writes.

### `metrics.read_time_ns`

String, default `blockstat_rd_total_time_ns`.

The Prometheus metric name for cumulative read I/O time in nanoseconds. This
is the **primary** load signal by default (`load_weights.iotime`): by
Little's law, `rate(rd_total_time_ns + wr_total_time_ns) / 1e9` is the
average number of I/O requests in flight on that disk — dimensionless,
additive across disks on the same storage, and directly comparable between
storages of different size and speed. It also *self-weights* reads against
writes automatically: an operation that takes eight times as long to
service (a large sequential write against a small random read, say) counts
eight times as much, with no manual read/write tuning needed. Pure IOPS
treats every operation as equal and so under-counts large sequential load;
pure throughput does the reverse and under-counts small random load. `ops`
and `bytes` (see `load_weights` below) remain available as additional
weighted terms for a policy the array's own timings do not capture.
(`IMPLEMENTATION_PLAN.md` section 4.)

### `metrics.write_time_ns`

String, default `blockstat_wr_total_time_ns`.

As `metrics.read_time_ns`, for writes.

### `metrics.labels.vmid`

String, default `vmid`.

The Prometheus label carrying the VM id.

### `metrics.labels.device`

String, default `instance`.

The Prometheus label carrying the drive id (`scsi0`, `virtio0`, ...).
**Confirm this with `verify-metrics`.** PVE's own tag of this name collides
with Prometheus's own scrape-target `instance` label, and many Telegraf
configurations rename or overwrite it; `verify-metrics` warns loudly when
this is still set to the literal string `instance`.

### `metrics.labels.node`

String, default `nodename`.

The Prometheus label carrying the PVE node name — what the auto-derived
filter below is built from: the tool fetches this cluster's
own node list from the PVE API and scopes every query to `<this
label>=~"<node1>|<node2>|..."`, so a Prometheus shared by more than one
PVE cluster (or by anything else emitting a same-named metric) cannot
silently sum in a same-numbered vmid from somewhere else. This is the
default filter for every run; `verify-metrics` never applies it — see
`metrics.extra_selector` below.

**Confirm what's actually there with `verify-metrics`** before assuming
the default is right for your Prometheus: it reports each configured
metric's sample series labels so you can check this key names a real one.

### `metrics.extra_selector`

String or `null`, default `null` (auto).

Overrides the automatic node-scoping filter above with a raw PromQL label
matcher, inserted verbatim into every query's vector selector (e.g.
`{metrics.extra_selector}` becomes part of
`rate(blockstat_rd_operations{cluster="mycluster"}[5m])`). Set this when
the node-list filter isn't quite what you need — your own Telegraf/InfluxDB
tagging scheme doesn't put the exact PVE node name in `metrics.labels.node`,
you want to scope by something else (a cluster-naming tag your deployment
happens to carry, say), or the restriction needed is something else
entirely. Write exactly what your label scheme needs, e.g.
`nodename=~"pve01|pve02|pve03"` or `cluster="mycluster"`; the value is
used as-is, with no further quoting or escaping. `pve-storage-drs
verify-metrics` applies this override too when set, but never derives its
own filter automatically — it is deliberately independent of the PVE API
entirely.

There is deliberately no "cluster label" auto-scoping tier above the
node-list default: an earlier revision of this tool assumed such a label
was standard practice across this project's deployments, which turned out
to be wrong — nothing in the Telegraf/InfluxDB pipeline guarantees one.
Use `metrics.extra_selector` for that instead, if your Prometheus actually
carries such a label.

### `metrics.rate_window`

Duration, default `5m`.

The inner range passed to `rate()`. Must be at least four times
`metrics.pvestatd_push_interval`, or `rate()` sees too few points to be
meaningful — `verify-metrics` measures the *observed* sample spacing of a
live series and errors if this rule is violated against reality, not just
against the declared `pvestatd_push_interval`.

### `metrics.step`

Duration, default `5m`.

The sampling step used for range queries (forecasting, coverage checks).
Independent of `metrics.rate_window`, though the two are usually set equal —
which is also the one setting a workaround below silently changes what
actually gets fetched at.

**Whenever `metrics.step >= metrics.rate_window`** (true at the usual-equal
default), the collector does not send `metrics.step` to Prometheus as-is: a
live-confirmed gigapipe bug returns zero series for any `rate()`-based range
query or `quantile_over_time` subquery once the query's own step reaches the
function's range-vector duration, so this tool queries at half that step (or
the largest whole-second step below it that divides `metrics.step` evenly,
at a wider ratio) and reassembles the configured grid from the result. Every
disk's coverage, load history and forecaster input comes back numerically
identical to what a plain `metrics.step` query would have returned on an
unaffected backend — except the `quantile_over_time` decision statistic
itself, whose inner evaluation runs on the denser grid unconditionally, on
every backend (a small, real shift in the reduced 95th-percentile value; see
`docs/internals/30-metrics.md`). The *stored* sample count this produces —
what `collect-testdata --estimate` prints and `support.max_series_points`
compares against — is correspondingly doubled (or more) at the same ratio.

### `metrics.pvestatd_push_interval`

Duration, default `60s`.

How often PVE's `pvestatd` pushes metrics — a PVE-side setting this tool
cannot read from the API, so it must be declared here. `verify-metrics`
cross-checks it against the *observed* sample spacing of a live series and
errors if they disagree by more than 20%, which is what stops a stale
declaration from silently invalidating the `rate_window` rule above.

## `window` — the decision window

This is the period whose load is balanced. It is **not** the amount of
history a forecaster needs to fit — see `forecast.model` below and
`IMPLEMENTATION_PLAN.md` section 10.1.

### `window.lookback`

Duration, default `24h`.

The trailing window each disk's load is reduced over. Must be at least as
long as the configured `forecast.model` needs (`forecast.model: holt_winters`
at its default `seasonal_periods` needs 48h, which a 24h lookback can never
supply — this is rejected at startup, not silently degraded).

### `window.quantile`

Fraction in (0, 1), default `0.95`.

The point-estimate quantile: each disk's load is the p95 of its raw signal
over `window.lookback`, not the mean, so one traffic spike neither triggers
nor suppresses a migration.

### `window.upper_quantile`

Fraction in (0, 1), default `0.99`.

The quantile the **saturation guard** actually consumes — must be
`>= window.quantile`. (The saturation guard is the migration-time safety
check, `migration.saturation_ceiling` below, that defers a move if it would
push a storage's forecasted load past a configured ceiling; it runs only for
a storage that sets `groups[].storages[].saturation_load`.) Being wrong in
the direction of "busier than it looks" costs the guard deferring a move
that was actually safe; the other direction risks the guard missing a
mirror that pushes a storage past saturation. The optimizer itself still
decides placement from `window.quantile`, the point estimate, not this
upper bound; wiring the upper bound into the optimizer's own input remains
future work. (`IMPLEMENTATION_PLAN.md` §10.1's "As built" note.)

### `window.min_coverage`

Fraction in (0, 1], default `0.80`.

A disk whose sample coverage over `window.lookback` falls below this
fraction has its data rejected for this run; its last known load from
`state.json` is used instead, flagged in the report. Never treated as zero —
that would silently invite migrations *onto* a busy but under-sampled
storage.

## `load_weights` — combining read/write and time/ops/bytes

Each disk's load is a single scalar, in **average in-flight I/O
requests**, blended from three raw per-disk signals — I/O time,
operations/second and bytes/second — after applying the read/write
asymmetry factors below. The three raw signals have wildly different
magnitudes (in-flight I/O is roughly 0–10, ops/s can run into the tens of
thousands, bytes/s into the billions), so they cannot be weighted directly:
each is first normalized against its own group's total (which makes the
three comparable, but throws away their physical meaning), the normalized
values are blended using the weights below, and the blend is then rescaled
back onto the in-flight-I/O scale using the group's total I/O time. Under
the defaults (`iotime: 1.0`, `ops: 0.0`, `bytes: 0.0`) that rescale is an
exact identity, so a disk's load is simply its own I/O-time term — the
normalize/blend/rescale machinery only changes the result once `ops` or
`bytes` carries a non-zero weight. The absolute scale this produces matters
beyond the blend itself: `migration.source_load_weight` and its siblings
below assume that `1.0` in-flight request at a mirror endpoint is directly
comparable to a disk's own load, which is only true because of this
rescale. (Derived in full, with the normalization formula, in
`IMPLEMENTATION_PLAN.md` section 4.)

### `load_weights.iotime`

Weight, default `1.0`.

Weight on the I/O-time term (`rate(rd_total_time_ns + wr_total_time_ns) /
1e9`), the primary signal by default: it is Little's-law in-flight I/O,
additive across disks and self-weighting between large sequential and small
random access with no manual read/write tuning needed.

### `load_weights.ops`

Weight, default `0.0`.

Weight on the operations/second term. Non-zero only if you want IOPS to
influence placement independently of I/O time.

### `load_weights.bytes`

Weight, default `0.0`.

Weight on the bytes/second term, for the same reason as `load_weights.ops`.

### `load_weights.read_factor`

Weight, default `1.0`.

Read/write asymmetry applied to the `ops`/`bytes` terms only (see
`load_weights.write_factor`). Applying it to the `iotime` term as well
double-counts, since I/O time already reflects the real read/write cost
difference — do that only deliberately.

### `load_weights.write_factor`

Weight, default `1.0`.

As `load_weights.read_factor`, for the write side. A write-heavy RAID-6
array, for example, might set this above 1.0 on the `ops`/`bytes` terms to
express the real cost asymmetry those terms cannot otherwise see.

## `groups` — storage groups

### `groups[].name`

String, required.

A group's name. A disk may only ever move between storages in its own
group; there is no cross-group balancing (`IMPLEMENTATION_PLAN.md` section
5). Must be unique.

### `groups[].storages[].id`

String, required.

A PVE storage id, or a `/regex/` pattern — a value that both begins and
ends with `/` — matching one or more storage ids (`IMPLEMENTATION_PLAN.md`
section 11.4). A pattern is matched with `re.fullmatch` (case-sensitive)
against the live cluster's storage inventory on every run, so `/san-.*/`
picks up a LUN added after the config was written with no edit needed; its
own entry's `capability_weight`/`reserve_factor`/`saturation_load` apply to
every storage it matches. A literal entry always overrides a pattern that
also matches its storage, so one member of a pattern-matched family can
still be pinned to different options. A storage may belong to **at most
one** group (after pattern expansion) — belonging to two would make a
disk's eligible destinations ambiguous, and config/cluster validation
rejects it, as does a pattern matching zero storages or two patterns in one
group claiming the same storage.

### `groups[].storages[].capability_weight`

Weight, `> 0`, default `1.0`.

The storage's **relative** share of the group's load — `u_s = L_s / c_s` is
what actually gets equalized, so a storage with half the spindles of its
peers can be given `0.5` and will correctly be assigned half the load. Only
the *ratios* within a group matter; the absolute value is meaningless and it
is not a capacity.

### `groups[].storages[].reserve_factor`

Weight or `null`, default `null` (inherits `snapshot_reserve.factor`).

Per-storage override of the group-wide snapshot reserve factor, for a
storage whose snapshot behaviour genuinely differs from its peers.

### `groups[].storages[].free_space.soft` / `groups[].storages[].free_space.hard`

Size, byte-unit string, percentage string (`"N%"`), or `null` — each
independently. `null` here means *inherit the global `free_space.soft`/
`.hard` value below* (§`free_space` — the same per-storage-null-means
-inherit rule `reserve_factor` above already has). One member of a
`/…/`-matched family can still be pinned to a different requirement than
its peers, the same way a literal entry already overrides a pattern's
`reserve_factor`.

A percentage is resolved against **this storage's own capacity**, even
when it comes from a pattern entry matching several differently-sized
storages — `"10%"` demands different byte counts on a 20 TiB and a 2 TiB
LUN, which is the point: "a tenth of the LUN free" is one policy applied
per storage, not one number shared across the family.

### `groups[].storages[].saturation_load`

Positive number or `null`, default `null`.

The storage's approximate queue depth — the number of concurrent I/O
requests it services before latency climbs super-linearly — in the same
units as the load model (average in-flight I/O). Used only by the
saturation guard on a migration's mirror (see `window.upper_quantile`
above). **Has no safe default**: an idle storage's observed load is not its
capacity, so leaving this `null` (the default) simply disables that one
advisory check for the storage; the hard bounds always apply regardless —
`migration.max_single_move_duration`, and the **transient reserve
invariant**: the `snapshot_reserve` floor (below) checked against the
storage's actual state *while a migration is in flight*, when a moving
disk's source and target copies are both briefly fully allocated at once,
not merely before and after. Obtain a real value for `saturation_load` from
the array's documented queue depth, or by observing where latency actually
starts climbing.

## `snapshot_reserve` — the free-space floor

### `snapshot_reserve.factor`

Weight `>= 0`, default `2.0`.

Keep this many times the largest disk on a storage free at all times,
including *during* a migration, not merely before and after — PVE 9's
volume-chain snapshots allocate a new full-size volume per snapshot, which
is what this protects against. This is the constraint the tool never trades
against balance (`IMPLEMENTATION_PLAN.md` section 5.3, (C5)).

### `snapshot_reserve.min_free_bytes`

Size, default `0`. **Deprecated syntax for `free_space.soft` below.**

An absolute floor, applied as `reserve = max(factor * largest_disk,
min_free_bytes)`. Matters when a storage's largest disk is small: with
`factor: 2.0` and a 10 GiB largest disk, the snapshot term alone would
reserve only 20 GiB on a 20 TiB LUN — exactly what `free_space.soft` now
expresses, with per-storage and percentage forms this scalar never had.
Still accepted, and still works: if set alongside `free_space.soft` it is
folded in as a floor on top of the resolved value (the larger of the two
applies on every storage, never a "last one wins" substitution — a config
warning names both keys when this happens), so upgrading is never a silent
weakening. New configs should use `free_space.soft` instead.

### `snapshot_reserve.count_foreign_volumes`

Boolean, default `true`.

Count volumes DRS does not manage (templates, ISOs, backups, other groups'
disks, orphans) against a storage's used capacity. Strongly recommended:
turning this off understates real usage and silently erodes the reserve it
is meant to guarantee.

## `free_space` — keep N bytes (or N%) free on top of the snapshot reserve

The Storage-DRS mandate (`IMPLEMENTATION_PLAN.md` section 5.3.1): an admin
places a new VM on a storage this tool does not manage the free space of by
snapshot behaviour alone, and the engine migrates data off it until the
configured free space is free again — bypassing the drift/imbalance gates
and the payback economics for exactly this reason, the same way a snapshot
-reserve violation already does. `soft` and `hard` here are the *global*
defaults; `groups[].storages[].free_space.soft`/`.hard` above override them
per storage or per `/…/`-matched pattern, most specific wins.

### `free_space.soft`

Size, byte-unit string, or percentage string (`"N%"`, `0 <= N < 100`),
default `0`.

The **plan-endpoint** requirement: the number of bytes that must be free on
a storage once the plan has fully run. `R_s = max(factor * largest_disk,
soft)` — the *larger* of the snapshot term and this floor wins, on every
storage, always; neither term can erode the other. The default `0` changes
nothing for a config that sets no knob in this block at all: the resulting
model is identical to the pre-`free_space` snapshot-only floor. A storage
that ends the plan below its `soft` requirement is in violation exactly
like a snapshot-reserve breach, and the engine migrates disks off it until
the requirement is met or reports the residual shortfall as unfixable
(section 9.5) — it does not guarantee the requirement is *achievable*, only
that it is pursued unconditionally.

### `free_space.hard`

Size, byte-unit string, percentage string, or `null`, default `null` (=
`soft`: no dip at all).

The **transient** floor: how far a storage may dip below `soft` while a
disk is landing on it mid-migration (section 8.1) — a mirror target is
fully allocated before its source releases anything, so a plan that lands
a disk on a storage that is *heading toward* `soft` needs room to pass
through it without ever crossing `hard`. The default `null` keeps the
transient invariant exactly as strong as it was before `free_space`
existed: no dip below `soft` at all. Set it strictly below `soft` only when
you have deliberately decided to trade a bounded, planned dip for it — a
transient dip can only ever land on a storage the *finished* plan leaves
compliant, never used to permanently weaken the requirement. `hard` above
`soft` is a config error: a floor stronger than the requirement it is
supposed to relax would make every plan for an already-compliant storage
infeasible.

## `gates` — deciding whether to act at all

### `gates.drift_threshold`

Fraction, default `0.10`.

Re-planning is skipped until the load vector has moved by this much in L1,
relative to the vector recorded at the last executed balance. Lower reacts
sooner and migrates more; below roughly 0.05 the tool will start chasing
noise on a busy cluster. Interacts with `gates.imbalance_threshold`: drift
decides *whether to look*, imbalance decides *whether to act*.

### `gates.imbalance_threshold`

Fraction, default `0.20`.

The minimum relative spread across a group's storages before a plan is
actually built. A group under this threshold is left alone even if it has
drifted. Also, unrelatedly, this same value doubles as the backtest error
ceiling a non-`quantile` `forecast.model` (`seasonal_naive`/`holt_winters`)
must stay within before its forecast is trusted to drive the saturation
guard for that group's run — see `forecast.model` below for how that
backtest works.

### `gates.capacity_spread_threshold`

Fraction or `null`, default `0.25`.

The data-spread counterpart of `gates.imbalance_threshold`: the minimum
relative spread in fill fraction (bytes used / capacity) across a group's
storages before a plan is built, evaluated even when the group's I/O is
already perfectly balanced -- in that case `objective.delta_capacity_spread`
is what does the spreading. It can legitimately exceed `1` (a group filled to
5% that keeps 60% of its bytes on one storage deviates as much as a full one
does). Unlike the drift/imbalance gates, this one **bypasses** them when it
fires -- a stable, balanced workload is not a reason to keep data
concentrated on one storage. `null` disables the gate outright; the gate
also cannot fire on a group with no data at all (mean fill `0`).

### `gates.cooldown_per_disk`

Duration, default `24h`.

A disk that moved within this long is pinned in place for planning
purposes. Prevents a disk from being shuffled back and forth across two
still-noisy storages.

### `gates.cooldown_per_storage`

Duration, default `1h`.

A storage involved in a migration within this long accepts no new incoming
moves. **Must exceed the implied wipe time of that storage's largest disk**
(`largest_disk / |saferemove_throughput|` — the magnitude, see
[`verify-storages`](25-show-load-and-verify-storages.md) on why that value is
often negative) or the next run will plan onto a
storage that is still draining and stall — `pve-storage-drs verify-storages` computes
this and warns when the configured cooldown is too short.

## `migration` — cost, bandwidth and the payback rule

### `migration.bwlimit_bytes_per_sec`

Size/s, default `209715200` (200 MiB/s).

Passed to `move_disk` as `bwlimit` (converted to KiB/s at the API call site —
the API's own unit, never bytes/s). Also the divisor in the mirror-duration
estimate the payback test uses: a move's mirror is assumed to take
`disk_bytes / bwlimit_bytes_per_sec` seconds (see `migration.payback_ratio`
below for the full cost/benefit comparison).

### `migration.source_load_weight`

Weight, default `1.0`.

Additional in-flight I/O charged to the **source** storage while a mirror is
running — a mirror is one sequential reader, so `1.0` is the natural value
in the same units as the load model.

### `migration.target_load_weight`

Weight, default `1.0`.

As `migration.source_load_weight`, for the target (one sequential writer).

### `migration.payback_horizon`

Duration, default `365d`.

The horizon `H` over which a plan's imbalance, data-spread and VM-affinity
reduction are assumed to persist — `benefit = (alpha_spread * ΔE +
delta_capacity_spread * ΔF + kappa_vm_affinity * ΔA) * H`, where each `Δ`
is the improvement the plan buys in that term (its value before the plan
minus its value after: `ΔE` for imbalance, `ΔF` for data spread, `ΔA` for
VM-affinity fragmentation — see `objective` below for what each term
measures). `ΔA` may be negative (a balance move that splits a VM pays for that fragmentation out
of its other gains — `IMPLEMENTATION_PLAN.md` section 7.2). Setting this to
`0` disables the payback test entirely
(`IMPLEMENTATION_PLAN.md` section 11.1 rejects that at config-load time:
`payback_horizon > 0` is required). This is an explicit assumption about how
long a placement lasts, not about operator patience: a migration's cost is
paid once and early, while its benefit accrues for as long as the workload
keeps running on the new placement — infrastructure timescales are months to
years, and the default assumes at least one year. Configuration validation
warns (does not error) below `30d`, where the test starts rejecting real,
slow-accruing benefit again; lower it toward the actual lifetime of your VMs
only for genuinely short-lived fleets (CI runners, render farms, lab
clusters).

### `migration.payback_ratio`

Weight `> 0`, default `10.0`.

`λ`: a plan is only accepted when `benefit >= payback_ratio * cost`, summed
over every disk the plan moves. Both sides are in **load-seconds** —
average in-flight I/O requests (the unit `load_weights` produces, see
`metrics.read_time_ns` above) multiplied by seconds — which is what makes
the comparison meaningful. A disk's cost (`cost_d`) is the extra in-flight
I/O the migration itself imposes: `migration.source_load_weight` on the
source and `migration.target_load_weight` on the target for the mirror,
which takes `disk_bytes / migration.bwlimit_bytes_per_sec` seconds, plus —
when `migration.account_saferemove_wipe` is on and the source storage has
`saferemove` set — `migration.wipe_load_weight` on the source for as long
as the old volume takes to be zeroed. Benefit is the improvement the plan
buys in imbalance, data spread and VM affinity, each weighted exactly as in
the `objective` section below and held for `migration.payback_horizon`
(see above for that formula). This is the numeric form of "migrating a very
large disk might generate more traffic than it saves." (`IMPLEMENTATION_PLAN.md`
section 7.2.)

### `migration.max_single_move_duration`

Duration, default `6h`.

A hard per-move ceiling on `duration_mirror + duration_wipe`. A move
predicted to take longer than this is rejected outright regardless of the
aggregate payback test.

### `migration.account_saferemove_wipe`

Boolean, default `true`.

Include the post-move `saferemove` zeroing pass in cost and duration
estimates. PVE's LVM `saferemove` defaults to 10 MiB/s, so a 1.5 TiB disk's
cleanup (~44h) can dwarf its ~2.2h mirror; disabling this only if you have
verified `saferemove` is off on every storage in a group understates real
migration cost badly if that assumption is wrong.

### `migration.wipe_load_weight`

Weight, default `1.0`.

In-flight I/O charged to the source for the whole `saferemove` wipe duration
— both in the cost model and in the saturation guard, where a draining move
charges this to its source and nothing to its target. The
zeroing pass is one sequential writer, so `1.0` is the natural value.

### `migration.saturation_ceiling`

Fraction in (0, 1], default `0.85`.

The fraction of a storage's `saturation_load` (not of `capability_weight`) a
move may drive it to. Inactive for any storage whose `saturation_load` is
`null` — the default, since there is no safe way to infer it.

### `migration.assume_thick_provisioning`

Boolean, only `true` (the default) is accepted. **Kept so a config that
spells it out still loads; `false` is refused at startup.**

This tool never considers over-provisioning. Every disk counts at its
*provisioned* size — in the reserve arithmetic, the free-space requirement,
the transient check and the cost model — on a thin-provisioned storage (Ceph
RBD, LVM-thin, ZFS) exactly as on a thick one. Thin provisioning is what lets
a pool hold more provisioned bytes than it has; here it is deliberately never
counted on, because a move that only fits *if the disks stay thin* is one a
growing guest can turn into a full pool.

The consequence to plan for: on a thin pool the tool's idea of "used" is the
sum of the disks' sizes plus foreign volumes, which can be several times what
the pool reports as allocated. A `free_space.soft` of `"90%"` on a pool with
plenty of *actually* free space can therefore show a large shortfall in
`plan`/`explain`, and the engine will migrate disks off it. That is the
intended behaviour, not a miscalculation.

The same holds at the moment of the move: the check `apply` makes just before
each `move_disk` re-reads the target's volume listing and sums the volumes'
provisioned sizes, never the pool's allocated figure, so it can refuse a move
onto a thin pool that still looks half empty in the PVE UI. `show-load`,
`plan` and `explain` print the provisioned figure as the storage's usage and,
when the pool's own number differs, add it in brackets as `(pool reports X
allocated)`.

### `migration.tiny_disk_bytes`

Size, default `67108864` (64 MiB).

A disk smaller than this carries zero `beta_move_count`/`gamma_move_bytes_per_tib`
cost in the objective and zero `cost_d` in the payback model — it still
counts as a scheduled move and every hard per-move safety rule
(`max_single_move_duration`, the saturation guard, the transient reserve
invariant) still applies to it exactly like any other move, but it needs no
payback verdict and cannot make a plan fail the aggregate `payback_ratio`
test. Together with `objective.kappa_vm_affinity`, this is what lets a tiny
volume — an `efidisk0` var store or `tpmstate0`, both normally a few hundred
KiB to a few MiB — rejoin its VM for free instead of being priced like a
real migration: both device types move online on PVE 9.2, so there is no
reason to price their reunion like a real migration once they are cheap
enough to ignore. (`IMPLEMENTATION_PLAN.md` §§5.4, 7.1, 7.3, 3.6.)

The default sits comfortably above either of those and far below any disk the
payback rule was written for, so a 528 KiB EFI disk always qualifies and a
64 GiB data disk never does. Set it to `0` to restore the pre-section-7.2
accounting, where every disk — however small — is charged a full migration.
Setting it too high (larger than disks you actually want cost-accounted) lets
real, meaningfully-sized migrations bypass the payback safety test entirely;
there is no upper bound enforced beyond `≥ 0`, so this is an operator
judgement call, not a validated range.

## `objective` — the solver's trade-off weights

The solver (and, for the terms it also uses, the heuristic backend)
minimizes one weighted sum, evaluated per group:

```
  alpha_spread            * (imbalance: summed deviation of each storage's utilization from the group's target)
+ beta_move_count         * (number of migrations)
+ gamma_move_bytes_per_tib * (TiB actually migrated)
+ kappa_vm_affinity       * (VM disk fragmentation, I/O-weighted — see below)
+ delta_capacity_spread   * (data spread: summed deviation of each storage's fill fraction from the group's mean)
+ reserve_violation_penalty * (reserve violation, heuristic backend only — see below)
```

The first five terms are calibrated to share one scale, in units of average
in-flight I/O per storage (see `metrics.read_time_ns` above) — which is
what makes the weights directly comparable: at the defaults, a migration
must buy at least a 0.25-request reduction in summed imbalance just to
cover its own `beta_move_count` cost, before its `gamma_move_bytes_per_tib`
and `kappa_vm_affinity` costs and the separate payback test
(`migration.payback_ratio` above) are even considered. Each term is
explained, with its own default and worked numbers, in its own entry below.
(`IMPLEMENTATION_PLAN.md` section 5.4 has the full derivation; section 14.3
works two competing plans through this exact formula.)

### `objective.spread_metric`

`l1` or `minmax`, default `l1`.

How imbalance is measured: `l1` (sum of each storage's deviation from the
group's target utilization) or `minmax` (only the single hottest storage).
`l1` is the default because `minmax` is indifferent to a second
nearly-as-bad storage once the worst one is fixed.

### `objective.alpha_spread`

Weight, default `1.0`.

Weight on the imbalance term (the sum of each storage's deviation from the
group's target utilization — see `objective` above for where this sits in
the full objective, and why `1.0` against the default
`beta_move_count: 0.25` means a migration must buy at least a 0.25-request
reduction in that sum to be worth making at all).

### `objective.beta_move_count`

Weight, default `0.25`.

Penalty per migration — the tunable implementation of "minimize the number
of migrations" (`IMPLEMENTATION_PLAN.md`'s "Requirement interpretation"
note: a strict minimum would refuse a second cheap move that halves the
remaining imbalance, which is not desired). Raising it trades balance
quality for fewer, larger moves.

### `objective.gamma_move_bytes_per_tib`

Weight per TiB, default `0.05`.

Penalty per TiB actually migrated, biasing against moving large disks
specifically (as opposed to `beta_move_count`, which only counts moves).

### `objective.kappa_vm_affinity`

Weight, default `0.50`.

Penalty per extra storage a VM's disks are spread across, counted only
**within** a group — a VM split across two groups is structural and cannot
be repaired by any migration, so it is not counted — and weighted by the
VM's own I/O share of the group: `w_v = max(1, ℓ_v / ℓ̄)`, where `ℓ_v` is
the VM's total load (the sum, in average in-flight I/O, of every one of its
disks in the group, including disks pinned this run) and `ℓ̄` is the
group's mean load per VM (the group's total load divided by every VM that
owns a disk in the group). The floor of `1` means a below-average VM's
fragmentation is weighted exactly as configured; a VM running several times
the group's average I/O is worth correspondingly more to keep together than
the configured weight alone suggests — a VM doing 2.7x the group's average
I/O, for example, is effectively weighted as if `kappa_vm_affinity` were
2.7 times higher for that VM alone. A soft preference: a strong imbalance
or a capacity constraint can legitimately override it.
(`IMPLEMENTATION_PLAN.md` section 5.4.)

### `objective.delta_capacity_spread`

Weight, default `0.5`.

Weight on data spread — the deviation of each storage's fill fraction
(bytes used / capacity) from the group's mean fill (`IMPLEMENTATION_PLAN.md`
section 5.3 (C7)). Bounds the share of a group's data any single storage
failure costs, and keeps peak fill uniform across the group. I/O balance
stays the first priority: this defaults to half of `alpha_spread`, and acts
on its own mainly when a group's I/O is already balanced but its data is
concentrated — the case `gates.capacity_spread_threshold` exists to reach.
`0` disables the term entirely; configuration validation warns once it
exceeds `alpha_spread`, the point where data evenness starts outweighing I/O
evenness in every plan comparison.

### `objective.affinity_counts_pinned_disks`

Boolean, default `true`.

Whether a disk that cannot move this run (snapshot-blocked, excluded, or on
a locked VM) still counts toward `kappa_vm_affinity`. Default `true`: such a
disk still *occupies* a storage, so the VM really is spread, and its fixed
location is an anchor the VM's movable disks can be drawn back to. Note
`efidisk0`/`tpmstate0` are *not* in this pinned set on PVE 9.2 — they move
online.

Set it to `false` to count movable disks only. Be aware of what that costs.
Take a VM with a snapshot-blocked disk on `san-a`:

- **One movable disk, on `san-b`.** With `false` the VM's counted footprint
  is that one disk, so it is never "spread", and moving it to `san-a`
  (reuniting the VM) scores exactly the same as leaving it or sending it to
  a third storage — the reunion is invisible, and the solver may pick any
  of them. With `true` the VM counts as spread over two storages until the
  disk joins `san-a`, and `kappa_vm_affinity` pulls it there.
- **Two movable disks, both on `san-b`.** With `false` the counted
  footprint is `san-b` alone; moving one of them to `san-a` to rejoin the
  pinned disk makes it `{san-a, san-b}` and is charged `kappa_vm_affinity`
  as if the VM had just been split. With `true` that same move is neutral,
  and moving both is a gain.

The pinned disk's storage is fixed, so counting it never asks for anything
unreachable: it only prefers targets where the VM already has a disk.

**This default changed after 0.1.6** (it was `false`). If you have not set
it and your cluster has pinned disks, expect plans to prefer targets where
the VM already has a disk. To keep the old behaviour, set it explicitly.

### `objective.reserve_violation_penalty`

Weight, default `1000.0`.

The reserve-violation weight in the **heuristic backend**'s objective
(`solver.backend: heuristic`, or `auto` falling back to it when neither a
MILP backend is installed): multiplied straight into
`reserve_penalty_term = objective.reserve_violation_penalty *
reserve_shortfall_tib`, one of the six terms `explain`'s `objective:`
line prints. It is used exactly as configured — no floor, no automatic
raise, no warning.

The MILP backends (`solver.backend: cpsat`/`cbc`, and `auto` when either is
available) solve the reserve **lexicographically** instead: the reserve is
fixed as a hard constraint and solved for first, before the rest of the
objective above is even considered, so no weight — this one included — can
trade it away. A single-stage alternative exists on paper: computing a
provably-dominant penalty from the group's own load instead of taking this
key at face value, with a `max(configured, computed)` floor. It is not
implemented, so this key never gets raised automatically for any backend —
what you set is exactly what the heuristic backend uses, and the MILP
backends never consult it at all. (`IMPLEMENTATION_PLAN.md` section 5.3.)

## `solver` — which backend plans

### `solver.backend`

One of `auto`, `cpsat`, `cbc`, `heuristic`; default `auto`.

`auto` prefers CP-SAT (`pip install proxmox-storage-drs[solver]` -- not
packaged for Debian), falls back to CBC (the packaged solver path via
`python3-pulp` + `coinor-cbc`), then the dependency-free heuristic. `cpsat`/
`cbc` force one specific backend, failing that group's solve back to the
heuristic (never a silent substitution of the *other* MILP backend) if its
library is not importable or it cannot solve within `solver.time_limit_seconds`
-- force a specific backend only to reproduce or compare a result.
`heuristic` skips the solver entirely. See `docs/internals/91-optimize.md`.

### `solver.time_limit_seconds`

Duration, default `60`.

Wall-clock budget for a MILP solve attempt before falling back to the
heuristic. Never emits a partial/unvalidated assignment on timeout — it
falls back cleanly instead.

### `solver.mip_gap`

Fraction, default `0.02`.

Acceptable optimality gap for the MILP solve: CP-SAT/CBC may stop once the
best solution found is within this fraction of a proven lower bound, rather
than solving to exact optimality. The CP-SAT backend must also convert
every fractional weight and load value into an integer coefficient before
solving, which introduces its own rounding error — worked out to roughly
`5×10⁻⁴` of summed load-deviation units even for a 1,000-disk group, three
orders of magnitude below this default `0.02` gap, so that rounding error
cannot itself change which plan is selected or make CP-SAT and CBC
disagree. (`IMPLEMENTATION_PLAN.md` section 5.5.)

### `solver.heuristic_iterations`

Integer `> 0`, default `5000`.

Iteration budget for the heuristic's local-search descent phase. Higher can
find a better local optimum on a large group at the cost of run time.
(`IMPLEMENTATION_PLAN.md` section 5.5.)

## `execution` — how (and whether) moves actually happen

### `execution.mode`

One of `dry-run`, `confirm`, `auto`; default `dry-run`.

`dry-run` (the default) prints the plan and changes nothing.
`confirm` executes one move at a time with a prompt before each.
`auto` executes unattended, subject to the concurrency and time-window
settings below. `--mode` on the command line overrides this for one run;
moving *toward* less safety is logged at warning level
(`IMPLEMENTATION_PLAN.md` section 11.3).

### `execution.max_concurrent_migrations`

Integer `>= 1`, default `1`.

How many moves may be in flight across the whole run at once, in `--mode
auto` only (`dry-run`/`confirm` always run strictly sequentially
regardless of this setting). Above `1` requires the *generalized* form of the transient reserve
invariant (see `groups[].storages[].saturation_load` above for the
single-move definition): several disks can land on one storage at once, and
none of their sources release space until each individually completes —
`apply` re-checks it live before launching each move. Launch order stays strictly FIFO: `apply` never reorders the
scheduler's own queue to keep every slot busy, so a move that cannot
launch yet is waited for rather than skipped past — see
`docs/manual/28-apply.md`'s own "Concurrent execution" section.

### `execution.max_migrations_per_run`

Integer `>= 1`, default `5`.

A ceiling on how many moves one invocation executes, independent of how many
the plan contains — the remainder waits for the next run. `auto` mode only
(`dry-run`/`confirm` execute or report the whole plan regardless); a shared
budget across every group the run visits, not reset per group.

### `execution.max_concurrent_per_storage`

Integer `>= 1`, default `1`.

Caps concurrent moves touching one storage, counting it as either source or
target, in `--mode auto` only. At the default of `1`, two moves targeting
the same storage serialize automatically and the generalized transient
invariant collapses to its simple single-move form. Raising it should be a
deliberate act on a storage with real spare headroom — two moves off the
same source also means two concurrent `saferemove` wipes sharing one
throttle.

### `execution.max_replans_per_run`

Integer `>= 0`, default `3`.

A cap on how many times one run may abandon its current plan and re-plan
from newly observed state — a mismatch between the plan and reality (a VM
live-migrated mid-plan, a lock appeared, a disk created or moved by someone
else, another tool filling the target) is normal, but a
cluster churning faster than the engine can plan is a condition for a human,
not for indefinite retrying. `auto` mode only — `confirm`/`dry-run` report a
mismatch (`replan_needed`) and stop that group's own run for the operator to
re-run by hand, rather than re-planning automatically.

When the cap is reached the run bails out and exits `0`; the next run starts
from freshly observed state. Set too low, ordinary churn ends runs early
and moves wait for the next one; set too high, a cluster that keeps
changing under the tool keeps it planning instead of waiting. `0` disables
re-planning: the first mismatch ends the run. Only a *mismatch* re-plans —
an error reading PVE or Prometheus fails the run outright and never counts
against this cap (see `28-apply.md`, "When something cannot be read").

### `execution.abort_on_failure`

Boolean, default `true`.

On a failed move, stop the run and report rather than continuing with the
remaining plan. The cluster is left in a valid intermediate state either
way; the next run re-plans from reality.

### `execution.poll_interval_seconds`

Duration, default `10`.

How often an in-flight `move_disk` task's status is polled.

### `execution.locks.wait_timeout`

Duration, default `4h`.

How long to wait for a VM's config `lock` (any non-empty value — the set is
treated as open-ended and never whitelisted) to clear before applying
`execution.locks.on_timeout`. Generous by default: a backup of a large VM
can easily run for hours, and that is a normal, not exceptional, condition.

### `execution.locks.poll_interval`

Duration, default `30s`.

How often the lock is re-checked while waiting.

### `execution.locks.on_timeout`

One of `skip`, `abort`; default `skip`.

What happens when `execution.locks.wait_timeout` elapses: skip this move and
continue with the rest of the plan, or abort the run. Never "force" — that
option does not exist, deliberately.

### `execution.locks.task_retry_limit`

Integer, default `2`.

The `move_disk` *task itself* can fail immediately with PVE's own `can't
lock file '/var/lock/qemu-server/lock-<vmid>.conf' - got timeout` — a
different lock than the config `lock` attribute `execution.locks.wait_timeout`
waits out, momentarily still held (typically by the previous move's own
`saferemove` wipe/cleanup finishing for the same VM) even after that
attribute already reads clear. This many extra attempts are made, each
preceded by `execution.locks.task_retry_backoff`, before the move is
reported `failed` like any other task failure. `0` disables the retry.

### `execution.locks.task_retry_backoff`

Duration, default `15s`.

How long to wait between a task-lock-timeout failure and the next
`move_disk` retry attempt.

### `execution.source_release.wait`

Boolean, default `true`.

Wait for the source volume of a completed move to actually disappear (and
the VM to be unlocked) before considering the move done, rather than
trusting the `move_disk` task's own `OK` status — with `saferemove` enabled,
`OK` does not mean the source space is back yet. Set `false` only on
storages verified not to wipe.

### `execution.source_release.timeout`

Duration, default `48h`.

Bound on the wait above, sized for a multi-TiB disk wiping at the default 10
MiB/s. Must be at least `largest_disk / |saferemove_throughput|` for every
storage where `saferemove` is on — `verify-storages` checks this.

### `execution.time_windows[].days`

List of `mon`..`sun`, default: every day.

Which days a time window applies on. Applies only to `execution.mode: auto`
— `dry-run` and `confirm` are not time-restricted, since neither changes
anything without a human already present.

### `execution.time_windows[].start` / `execution.time_windows[].end`

`HH:MM` strings, required together, must differ.

The window `auto` mode is permitted to execute moves in, in the **local
time of the host running `pve-storage-drs`** — the same convention
`systemd.timer`'s own `OnCalendar=` uses by default — not UTC. A window may
cross midnight (`start: "22:00"`, `end: "06:00"`); `start == end` is
rejected as ambiguous — it would silently mean either "never" or "always".
No `time_windows` configured at all means no restriction: `auto` may
execute at any time — this is the deliberate default, not merely the
absence of a rule. Before starting a move, `auto` also refuses it (and
stops the group's run cleanly, without aborting a move already in
progress) if its estimated duration would not finish before the window
closes.

## `exclude` — what DRS never touches

### `exclude.vmids`

List of integers, default `[]`.

VM ids whose disks are never moved.

### `exclude.disks`

List of `"vmid:device"` strings, default `[]`, e.g. `["101:scsi1"]`.

Individual disks excluded regardless of their VM.

### `exclude.storages`

List of storage ids, default `[]`.

Storages excluded as both source and target — effectively removes them from
their group without editing `groups`.

### `exclude.tags`

List of PVE tags, default `["no-drs"]`.

A VM carrying any of these tags opts out entirely.

### `exclude.skip_vms_with_snapshots`

Boolean, default `true`.

Pre-filter disks with a snapshot or an unreferenced companion volume before
they reach the API. Setting this `false` does **not** make such a move
work — PVE rejects `move_disk delete=1` on a snapshotted volume regardless;
it only removes the early, informative warning. Keep this `true`.

### `exclude.running_only`

Boolean, default `true`.

Only running VMs generate load to balance; a stopped VM's disks are moved
only if a capacity constraint requires it. Setting this `false` widens the
movable set to stopped VMs' disks for capacity purposes but they still
contribute zero load.

### `exclude.include_unused_disks`

Boolean, default `true`.

Whether detached (`unusedN`) volumes are movable. They carry zero load, so
the solver only relocates one to repair a capacity violation — never for
balance, since there is no benefit to buy. Set `false` to pin them in place
entirely; they still count via `snapshot_reserve.count_foreign_volumes`
either way.

## `report`

### `report.warn_pinned_load_fraction`

Fraction in (0, 1], default `0.25`.

If pinned load (snapshots, locks, exclusions) exceeds this fraction of a
group's total, the residual imbalance may be structural rather than a
planning failure, and `explain` says so alongside the best achievable
spread given the pins — see [`29-explain.md`](29-explain.md).

## `state`

### `state.path`

File path, default `/var/lib/pve-storage-drs/state.json`.

Local disk, one copy per host, deliberately never `/etc/pve` — see
[`00-installation.md`](00-installation.md). Losing this file is safe but not
free: cooldowns and the drift baseline reset, so the next run may migrate
sooner than intended. Treat it as state to back up, not as a cache.

`show-load` and `plan` both read this file (if present) for the drift
gate's history; neither writes it, and a missing or unreadable file just
means every group evaluates as if it had never been balanced before — see
[`../internals/15-state.md`](../internals/15-state.md).

## `forecast` — history beyond the plain quantile

See `IMPLEMENTATION_PLAN.md` section 10 and `proxmox_storage_drs/forecast.py`.

### `forecast.model`

One of `quantile`, `seasonal_naive`, `holt_winters`; default `quantile`.

`quantile` needs only `window.lookback` and no model fitting. `seasonal_naive`
and `holt_winters` need more history than the decision window alone — see
below — and `pve-storage-drs` refuses to start if `window.lookback` (or your
Prometheus retention) cannot supply it, rather than silently falling back.

**Backtest-validated before use.** Only when the saturation guard is
actually active (some `groups[].storages[].saturation_load` is set): a
`seasonal_naive`/`holt_winters` model is fit on the older half of its own
recent history and checked against what actually happened in the newer
half, once per group, before it is trusted for that run. A model that
misses by more than `gates.imbalance_threshold` — or that does not yet
have enough history to backtest at all — falls back to `quantile` for that
group's saturation guard this run, logged at warning. `quantile` itself is
never backtested; there is nothing to validate and nothing more
conservative to fall back to. (`IMPLEMENTATION_PLAN.md` section 10.2.)

### `forecast.seasonal_lookback_days`

Days, default `7`.

History `seasonal_naive` needs: same-hour-of-day samples across this many
days. `0` does not disable the model or fall back to anything — it simply
stops requiring history beyond `window.lookback`, which for a lookback
under 24h can leave no same-hour-of-day sample to match at all (predicting
`0.0`, not a fallback).

### `forecast.holt_winters.seasonal_periods`

Integer `> 0`, default `288` (24h at a 5-minute step).

Samples per seasonal cycle. Combined with `metrics.step`, this determines
`holt_winters`'s required history: `2 * seasonal_periods * metrics.step`
— 48h at the defaults, which a 24h `window.lookback` can never satisfy.

To fit **weekly** seasonality instead of daily (e.g. weekends look
different from weekdays), widen this together with `window.lookback`:
`seasonal_periods: 2016` (7d at the default 5m step) needs
`window.lookback` of at least 28 days (`2 * 2016 * 5m`). The fetch behind
this — both the live `plan`/`apply` saturation guard and
`collect-testdata` — is chunked into day-sized requests regardless of how
wide the range gets, so a large `seasonal_periods`/`window.lookback`
combination no longer risks exceeding a Prometheus-compatible backend's
own per-series resolution limit (VictoriaMetrics/gigapipe's default
11,000 points) the way an unchunked request over the same range once
could; it costs more Prometheus requests per run instead (one per day of
range, per raw metric, per group) — a real cost worth sizing
deliberately, not a reason to keep the range artificially small.

### `forecast.holt_winters.trend`

One of `add`, `mul`, `none`; default `add`.

The trend component passed to the underlying Holt-Winters fit
(`statsmodels`, an optional dependency — see
[`30-safety-and-status.md`](30-safety-and-status.md)).

### `forecast.holt_winters.seasonal`

One of `add`, `mul`, `none`; default `add`.

The seasonal component passed to the same fit.

### `forecast.holt_winters.residual_z`

Weight, default `2.0`.

The upper bound is `point_estimate + residual_z * stdev(residuals)` from the
in-sample fit — this is what the saturation guard actually consumes (see
`window.upper_quantile` above for the equivalent under the `quantile`
model; the optimizer itself does not consume this).

## `support` — diagnostic bundles

See [`26-collect-testdata-and-replay.md`](26-collect-testdata-and-replay.md) and
`IMPLEMENTATION_PLAN.md` section 16. Nothing here is read on the normal
`plan`/`apply` path — only by `collect-testdata` and by `--replay`'s config
loading.

### `support.salt_path`

File path, default `/var/lib/pve-storage-drs/anonymization-salt`.

32 random bytes, generated on first use and persisted here, mode `0600`,
never written into a bundle. Every pseudonym `collect-testdata` produces is
`HMAC-SHA256` keyed on this salt, so the same object maps to the same
pseudonym across runs and across bundles until `--new-salt` rotates it.
Reproducibility is per salt file, i.e. per node by default; point this at a
pmxcfs path (e.g. `/etc/pve/pve-storage-drs-anon-salt`) if every node in the
cluster should agree on one mapping — that also replicates the salt to every
node, which is the trade-off being made.

### `support.bundle_dir`

Directory path, default `/var/lib/pve-storage-drs/testdata`.

Default `-o`/`--output` for `collect-testdata` when the flag is not given.

### `support.max_series_points`

Positive integer, default `5000000`.

`collect-testdata` prints the estimated series-sample count before fetching
anything and refuses outright above this ceiling — never a silent
truncation — naming the `--range`/`--step`/`--no-series` flags that would
bring the estimate under it.

### `support.capture_range`

The literal string `"auto"`, or a duration, default `"auto"`.

`"auto"` captures the union of every forecaster's `required_range()` —
currently
`max(window.lookback, forecast.seasonal_lookback_days, 2 * forecast.holt_winters.seasonal_periods * metrics.step)`
— so a bundle can reproduce a forecaster the capturing operator never
configured. An explicit duration (e.g. `14d`) overrides that; `--range` on
the command line overrides both.
