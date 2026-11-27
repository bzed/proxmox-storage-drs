# Configuration reference

This page documents every key `pve-storage-drs` reads. For each key it gives
the type, the unit, the default, the keys it interacts with, and what happens
if you set it too high or too low. A key that exists in the schema but not
here, or here but not in the schema, is a bug.
`tests/unit/test_documentation.py` asserts that the two never drift apart.

`config/drs.example.yaml` in the source tree (installed to
`/usr/share/doc/pve-storage-drs/examples/drs.example.yaml`) carries the same
defaults with inline comments. This page is the full explanation each
comment points back to.

### `schema_version`

Integer, required, no default.

The version of the config format. `pve-storage-drs` refuses to start on any `schema_version` other than the one it
understands. The error
names the version the tool does understand. The tool does not guess field
values from a future incompatible format. The current value is `1`.

## `proxmox` — the cluster API connection

### `proxmox.host`

String, required, no default.

The hostname or IP of any cluster member. The tool reaches the API at
`https://<host>:<port>/api2/json`.

### `proxmox.port`

Integer, default `8006`.

The PVE API port. Change this value only if you put a reverse proxy or
another service in front of the API.

### `proxmox.verify_ssl`

Boolean, default `true`.

Sets whether the tool verifies the API's TLS certificate. Set `false` only
for a self-signed certificate you cannot trust by another method. Prefer
`proxmox.ca_file` where possible. Disabling verification also disables the
protection against a compromised network path to every node's API.

### `proxmox.ca_file`

String path or `null`, default `null`.

A CA bundle to verify the API's certificate against. Use it when the API's
certificate is not signed by a certificate the host running
`pve-storage-drs` already trusts.

### `proxmox.auth.username`

String or `null`.

A PVE user, e.g. `drs@pve`. The key is required unless you set both
`proxmox.auth.token_id` and `proxmox.auth.token_secret`. Username/password authentication is what the
original requirement asked for. An API token (below) is the preferred
method for `execution.mode: auto`. A token needs no interactive ticket
refresh, and you can scope it tightly. The tool's actual minimum privilege
is `Datastore.Audit` **and** `Datastore.Allocate` on every storage in the
config's `groups`, plus `VM.Config.Disk` and `VM.Migrate` (or an equivalent
custom role) on the VMs it may move.

`Datastore.Audit` alone is not enough. PVE's per-volume content listing
returns an *empty* result with no error when only `Datastore.Audit` is
granted. The tool would then show every tracked disk as untracked, without
any error you would notice. Grant the role per storage. Do not rely on
propagation from the parent `/storage` path. An API token's effective
permission is the **intersection** of the user's own grants and the
token's own grants. Both need the grant, or neither has it.
(`IMPLEMENTATION_PLAN.md` section 3.5.)

### `proxmox.auth.password`

String or `null`, default `null`, environment: `PVE_PASSWORD`.

Leave this key `null` in the file. Set `PVE_PASSWORD` in the environment
(or a systemd credential) instead. This matters most when the config file
lives on `/etc/pve`, where it is group-readable by `www-data`. A password
given in the file is used as-is. The environment variable does **not**
override it. See [`00-installation.md`](00-installation.md) for why the
file's own permissions matter here.

### `proxmox.auth.token_id`

String or `null`, default `null`.

An API token id, e.g. `drs@pve!balancer`. Set this key instead of
`username`/`password` for unattended operation. A token needs no ticket
refresh loop. You can revoke it independently of the user's password.

### `proxmox.auth.token_secret`

String or `null`, default `null`, environment: `PVE_TOKEN_SECRET`.

The secret half of the API token. It follows the same environment-variable
preference as `proxmox.auth.password`.

### `proxmox.ticket_refresh_seconds`

Duration, default `3000` (50 minutes).

How often the tool refreshes a username/password ticket. PVE tickets last
about two hours. A refresh well before the expiry avoids a mid-run
authentication failure. The tool does not use this key for API-token
authentication, which needs no ticket. The implementation overrides
`proxmoxer`'s own refresh interval after login, because `proxmoxer` has no
constructor option for the value. Without the override, the interval is
fixed at 3600s. If a ticket is still rejected mid-run (a long `confirm`-mode
wait, a suspended process, a clock jump; see `50-pve-api.md`), the client
logs in again from scratch. It then retries the failed call once, then it
gives up.

### `proxmox.read_workers`

Integer, default `12`.

The size of the bounded thread pool that fetches the per-VM configuration.
`GET /nodes/{node}/qemu/{vmid}/config` has no batch form, so this key keeps
the topology read of a several-hundred-VM cluster from being serial. A
higher value increases API server load and reduces wall-clock time. The
plan suggests the range 8 to 16. Too high a value can itself become the
bottleneck on a small PVE API server. Only the per-VM fetch runs in
parallel. The cluster-wide and per-storage calls (`50-pve-api.md`) still run
once each, sequentially, before it starts.

## `prometheus` — the metrics source

### `prometheus.url`

String, required, no default.

The base URL of your Prometheus, e.g. `http://prometheus.example.com:9090`.

### `prometheus.timeout_seconds`

Duration, default `30`.

The per-request timeout for calls to Prometheus. A value that is too low
can make `verify-metrics` and the load model fail on a busy or long-range
query even though Prometheus is healthy. A value that is too high delays
the moment you notice that Prometheus is unreachable.

### `prometheus.username` / `prometheus.password`

String or `null`, default `null`.

The HTTP basic auth credentials for your Prometheus, if it requires them.
Set either these two keys or
`prometheus.bearer_token`, not both (see that key).

### `prometheus.bearer_token`

String or `null`, default `null`.

A bearer token for a Prometheus instance behind an auth proxy that expects
one. Do not set it together with `prometheus.username`
and `prometheus.password`. When all are set, this version sends the basic auth
credentials and does **not** send the token (a known defect, issue #2).

## `metrics` — Telegraf/InfluxDB name mapping

Telegraf's naming is deployment-specific (`IMPLEMENTATION_PLAN.md` section
3.3). Every name below is configuration, never a constant. Run
`pve-storage-drs verify-metrics` after you change any of them. See
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

The Prometheus metric name for the cumulative read I/O time in
nanoseconds. This is the **primary** load signal by default
(`load_weights.iotime`). By Little's law, `rate(rd_total_time_ns +
wr_total_time_ns) / 1e9` is the average number of I/O requests in flight on
that disk. The value is dimensionless. It is additive across disks on the
same storage, and directly comparable between storages of different size
and speed. The term also *self-weights* reads against writes
automatically. An operation that takes eight times as long to service
(a large sequential write versus a small random read, for example) counts
eight times as much. You need no manual read/write tuning. A pure IOPS
model treats every operation as equal, so it under-counts large sequential
load. A pure throughput model does the reverse and under-counts small
random load. `ops` and `bytes` (see `load_weights` below) remain available
as additional weighted terms for a policy the array's own timings do not
capture. (`IMPLEMENTATION_PLAN.md` section 4.)

### `metrics.write_time_ns`

String, default `blockstat_wr_total_time_ns`.

As `metrics.read_time_ns`, for writes.

### `metrics.labels.vmid`

String, default `vmid`.

The Prometheus label that carries the VM id.

### `metrics.labels.device`

String, default `instance`.

The Prometheus label that carries the drive id (`scsi0`, `virtio0`, ...).
**Confirm this key with `verify-metrics`.** PVE's own tag of this name
collides with Prometheus's own scrape-target `instance` label. Many
Telegraf configurations rename or overwrite the tag. `verify-metrics`
prints a warning when this key is still set to the literal string
`instance`.

### `metrics.labels.node`

String, default `nodename`.

The Prometheus label that carries the PVE node name. The tool builds the
automatic filter below from this label: it fetches this cluster's own node
list from the PVE API, then scopes every query to `<this
label>=~"<node1>|<node2>|..."`. When one Prometheus serves more than one
PVE cluster, or any other source emits a metric with the same name, this
filter keeps a same-numbered vmid from another cluster out of the result.
This is the default filter for every run. `verify-metrics` never applies
it. See `metrics.extra_selector` below.

**Confirm what is actually there with `verify-metrics`** before you assume
the default is right for your Prometheus. `verify-metrics` reports each
configured metric's sample series labels, so you can check that this key
names a real one.

### `metrics.extra_selector`

String or `null`, default `null` (auto).

Overrides the automatic node-scoping filter above with a raw PromQL label
matcher. The tool inserts the value verbatim into every query's vector
selector (e.g. `{metrics.extra_selector}` becomes part of
`rate(blockstat_rd_operations{cluster="mycluster"}[5m])`). Set this key
when the node-list filter does not fit your setup: your Telegraf/InfluxDB
tagging scheme does not put the exact PVE node name in
`metrics.labels.node`, you want to scope by something else (a cluster-naming
tag your deployment carries, for example), or you need a different
restriction entirely. Write exactly what your label scheme needs, e.g.
`nodename=~"pve01|pve02|pve03"` or `cluster="mycluster"`. The tool uses the
value as-is, with no further quoting or escaping. `pve-storage-drs
verify-metrics` applies this override too when it is set. It never derives
its own filter automatically, because it is deliberately independent of
the PVE API.

The tool does not add a "cluster label" auto-scoping tier above the
node-list default. An earlier revision of this tool assumed such a label
was standard practice across this project's deployments. That assumption
turned out to be wrong: nothing in the Telegraf/InfluxDB pipeline
guarantees a cluster label. Use `metrics.extra_selector` for that instead,
if your Prometheus actually carries such a label.

### `metrics.rate_window`

Duration, default `5m`.

The inner range the tool passes to `rate()`. The value must be at least
four times `metrics.pvestatd_push_interval`. Below that, `rate()` sees too
few points to be meaningful. `verify-metrics` measures the *observed*
sample spacing of a live series. It returns an error if this rule fails
against the observed spacing, not just against the declared
`pvestatd_push_interval`.

### `metrics.step`

Duration, default `5m`.

The sampling step the tool uses for range queries (forecasting, coverage
checks). The key is independent of `metrics.rate_window`, though you
usually set the two equal. The workaround below silently changes the step that the collector actually
fetches at. It applies when the two keys are equal, the usual case, and when
`metrics.step` is larger.

**Whenever `metrics.step >= metrics.rate_window`** (true at the usual-equal
default), the collector does not send `metrics.step` to Prometheus as-is.
A live-confirmed gigapipe bug returns zero series for any `rate()`-based
range query or `quantile_over_time` subquery once the query's own step
reaches the function's range-vector duration. The tool therefore queries at
half that step (or the largest whole-second step below it that divides
`metrics.step` evenly, at a wider ratio). It then reassembles the configured
grid from the result. Every disk's coverage, load history and forecast
input comes back numerically identical to what a plain `metrics.step` query
would have returned on an unaffected backend. One value differs: the
`quantile_over_time` decision statistic itself. Its inner evaluation runs on
the denser grid unconditionally, on every backend. That causes a small,
real shift in the reduced 95th-percentile value. See
`docs/internals/30-metrics.md`. The *stored* sample count the workaround
produces (what `collect-testdata --estimate` prints and
`support.max_series_points` compares against) doubles (or grows more) at
the same ratio.

### `metrics.pvestatd_push_interval`

Duration, default `10s` (`pvestatd`'s own default).

How often PVE's `pvestatd` pushes metrics. This is a PVE-side setting that
the tool cannot read from the API, so you must declare it here.
`verify-metrics` cross-checks it against the *observed* sample spacing of a
live series. It returns an error if the two disagree by more than 20%.
That check stops a stale declaration from silently invalidating the
`rate_window` rule above.

## `window` — the decision window

This is the period whose load the tool balances. It is **not** the amount
of history a forecast needs to fit. See `forecast.model` below and
`IMPLEMENTATION_PLAN.md` section 10.1.

### `window.lookback`

Duration, default `24h`.

The window over which the tool reduces each disk's load. Under
`forecast.model: quantile`, it is the last `window.lookback`. Under
`forecast.model: holt_winters`, it is the next window (the forecast one).
The value must be at least as long as the configured `forecast.model`
needs. For example, `forecast.model: holt_winters` at its default
`seasonal_periods` needs 48h, and a 24h lookback can never supply that.
The tool rejects the config at startup; it does not degrade silently.

### `window.quantile`

Fraction in (0, 1), default `0.95`.

The quantile the tool uses as the point estimate: each disk's load is the
p95 of its raw signal over `window.lookback`, not the mean. One traffic
spike then neither triggers nor suppresses a migration.

### `window.min_coverage`

Fraction in (0, 1], default `0.80`.

The tool rejects a disk's data for this run when its sample coverage over
`window.lookback` falls below this fraction. It then uses the disk's last
known load from `state.json`, flagged in the report. When `state.json` has no load for the disk, the tool uses 0 and flags the disk.
A load of 0 can invite migrations *onto* a busy but under-sampled storage. Check
flagged disks before you trust a plan.

## `load_weights` — combining read/write and time/ops/bytes

Each disk's load is a single scalar, in **average in-flight I/O
requests**. The tool blends three raw per-disk signals to compute it: I/O
time, operations/second and bytes/second. It applies the read/write
asymmetry factors below before the blend. The three raw signals have
widely different magnitudes: in-flight I/O is about 0 to 10, ops/s can
reach the tens of thousands, and bytes/s the billions. The tool cannot
weight them directly. It first normalizes each signal against its own
group's total. That makes the three comparable, but the normalization
loses the physical meaning of the signals. The tool then blends the
normalized values using the weights below, and rescales the blend back onto
the in-flight-I/O scale using the group's total I/O time. Under the
defaults (`iotime: 1.0`, `ops: 0.0`, `bytes: 0.0`) that rescale is an
exact identity. A disk's load is then simply its own I/O-time term. The
normalize/blend/rescale machinery changes the result only once `ops` or
`bytes` carries a non-zero weight. The absolute scale matters beyond the
blend itself: `migration.source_load_weight` and its siblings below assume
that `1.0` in-flight request at a mirror endpoint is directly comparable to
a disk's own load. That holds only because of this rescale.
(`IMPLEMENTATION_PLAN.md` section 4 derives the formula in full, with the
normalization formula.)

### `load_weights.iotime`

Weight, default `1.0`.

The weight on the I/O-time term (`rate(rd_total_time_ns + wr_total_time_ns) /
1e9`). This is the primary signal by default. It is Little's-law in-flight
I/O. It is additive across disks, and it self-weights between large
sequential and small random access. You need no manual read/write tuning.

### `load_weights.ops`

Weight, default `0.0`.

The weight on the operations/second term. Set it non-zero only if you want
IOPS to influence placement independently of I/O time.

### `load_weights.bytes`

Weight, default `0.0`.

The weight on the bytes/second term, for the same reason as
`load_weights.ops`.

### `load_weights.read_factor`

Weight, default `1.0`.

The factor that the tool applies to the read side of all three raw signals: I/O
time, operations and bytes (see `load_weights.write_factor`). I/O time already
reflects the real cost difference between reads and writes. A factor other than
1.0 therefore counts that difference twice in the I/O-time signal. Change it only
on purpose.

### `load_weights.write_factor`

Weight, default `1.0`.

The same factor as `load_weights.read_factor`, for the write side. A
write-heavy RAID-6 array, for example, might set this key above 1.0 to express a
cost that the `ops` and `bytes` signals cannot show. The factor also scales the
I/O-time signal.

## `groups` — storage groups

### `groups[].name`

String, required.

The name of the group. A disk may only move between storages in its own
group. The tool does not balance across groups
(`IMPLEMENTATION_PLAN.md` section 5). The name must be unique. This version
does not check this: a duplicate name silently replaces the earlier group (a
known defect, issue #3).

### `groups[].storages[].id`

String, required.

A PVE storage id, or a `/regex/` pattern. A pattern is a value that both
begins and ends with `/`. It matches one or more storage ids
(`IMPLEMENTATION_PLAN.md` section 11.4). The tool matches a pattern with
`re.fullmatch` (case-sensitive) against the live cluster's storage
inventory on every run. A LUN added after you wrote the config is picked up
by `/san-.*/` with no edit. The pattern entry's own
`capability_weight`/`reserve_factor` apply to every storage the pattern
matches. A literal entry always overrides a pattern that also matches its
storage. That lets you pin one member of a pattern-matched family to
different options. A storage may belong to **at most one** group (after
pattern expansion). A storage in two groups would make a disk's eligible
destinations ambiguous, so config/cluster validation rejects the config.
The validation also rejects a pattern that matches zero storages, and two
patterns in one group that claim the same storage.

### `groups[].storages[].capability_weight`

Weight, `> 0`, default `1.0`.

The storage's **relative** share of the group's load. `u_s = L_s / c_s` is
what the tool actually equalizes. A storage with half the spindles of its
peers can be given `0.5`, and the tool then assigns it half the load. Only
the *ratios* within a group matter. The absolute value is meaningless, and
it is not a capacity.

### `groups[].storages[].reserve_factor`

Weight or `null`, default `null` (inherits `snapshot_reserve.factor`).

A per-storage override of the group-wide snapshot reserve factor. Use it
for a storage whose snapshot behaviour genuinely differs from its peers.

### `groups[].storages[].enforce_format`

`raw`, `qcow2` or `null`, default `null` (keep the disk's current format).

A disk keeps its format when the tool moves it. A `qcow2` disk lands as
`qcow2`, and a raw disk lands as raw. The tool does not choose as a
destination a storage that cannot hold the disk's format. Setting this key
on a storage changes that rule for **moves onto it**. Every disk the plan
moves there arrives in the named format. The tool converts the disk during
the move if it was in another format. The typical use is shared (non-thin)
LVM on Proxmox VE 9.2, where a `qcow2` volume makes volume-chain snapshots
possible. `enforce_format: qcow2` makes every disk that lands on that LUN
snapshot-capable. `raw` does the opposite, for the speed of a plain block
device. Set this key on a literal entry or on a `/…/` pattern entry. Every
storage the pattern matches gets the key. A literal entry for one of them
overrides the pattern, as for every per-storage option. The tool offers no
global setting, because the formats that exist depend on the storage type.
The tool does not offer `vmdk`.

The tool does *not* do the following:

- The key never causes a move. A disk that already sits on the storage in
  another format stays where it is. `verify-storages` counts such disks so
  you can see how far the storage is from its policy. You convert those
  disks in place yourself, with `qm disk move`. The tool converts a disk
  only as a side effect of a move the balancer wanted for its usual reasons.
- The tool never touches a VM's TPM state disk (`tpmstate0`). That disk
  always keeps its format. The tool never moves a disk with snapshots at
  all.
- The value must fit the storage's type. The tool accepts `qcow2` on
  `lvm`, `dir`, `nfs`, `cifs` and `cephfs` storages, and `raw` everywhere.
  The tool refuses a value the storage's type cannot hold when it reads the
  cluster, and the error names the storage. For a pattern entry, the error
  means: narrow the pattern.

**Space accounting.** The tool counts a converted disk on the target at the
larger of its current size and the `size=` in its VM configuration. For a
`qcow2` volume on an `lvm` storage, the tool adds the image's own metadata
(a small fraction of a percent; the tool uses a safe upper bound). The
snapshot reserve, your `free_space` requirement and the in-flight space
check all use that larger figure. A conversion cannot reduce them. Just
before a converting move starts, the tool re-reads the volume. If the format is no longer the planned one, the tool skips the move
and the next run plans again.

This policy has a cost. `qcow2 → raw` on LVM removes volume-chain snapshots
on that storage for the moved disks. `raw → qcow2` adds a qcow2 layer to
every I/O. Leave this key `null` unless you want one of those outcomes. The
move line of `plan` shows a conversion as `raw→qcow2`.

### `groups[].storages[].free_space.soft` / `groups[].storages[].free_space.hard`

Size, byte-unit string, percentage string (`"N%"`), or `null`. Each value
is independent. `null` here means *inherit the global `free_space.soft`/
`.hard` value below* (§`free_space`). This is the same null-means-inherit
rule that `reserve_factor` above already has. One member of a `/…/`-matched
family can carry a different requirement from its peers, the same way a
literal entry already overrides a pattern's `reserve_factor`.

The tool resolves a percentage against **this storage's own capacity**,
even when the value comes from a pattern entry matching several
differently-sized storages. `"10%"` demands different byte counts on a
20 TiB and a 2 TiB LUN. That is one policy applied per storage, "a tenth
of the LUN free", not one number shared across the family.

## `snapshot_reserve` — the free-space floor

### `snapshot_reserve.factor`

Weight `>= 0`, default `2.0`.

Keep this many times the **largest VM footprint** on a storage free at
all times, including *during* a migration, not merely before and after.
PVE 9 takes a snapshot of a whole VM at once, and its volume-chain
snapshots allocate a new full-size volume per snapshotted disk. A snapshot
of VM *v* therefore needs on storage *s* the sum of all of *v*'s disks
that live on *s* (its *footprint* there), not its largest single disk. A
VM with five 2 TiB disks on one storage needs 10 TiB free for one
snapshot. At the default `2.0` the storage keeps 20 TiB free for it. The
tool counts the footprint per storage. The room a snapshot needs on
*another* storage holding some of the same VM's disks is that storage's
own footprint figure. Pinned disks count, because the tool snapshots them
with their VM. Disks of stopped VMs count toward used space but carry no
footprint, because the tool does not plan snapshots for stopped VMs.
`show-load` and `verify-storages` print the largest footprint on each
storage and the VM it belongs to. This is the constraint the tool never
trades against balance.

**Upgrading from a release that reserved only the largest disk:** a
storage holding two or more disks of one VM now reserves more than before.
A storage that was compliant can report a reserve shortfall it did not
have yesterday. That is the new rule, not a change in the cluster. The
tool treats the result as a repair like any other shortfall. The first run
after the upgrade can plan substantial migrations. Read `show-load` (and a
dry-run `plan`) first.

### `snapshot_reserve.split_vm_footprint`

Size, byte-unit string, or `null`, default `2TiB`.

The most of **one VM** that **one storage** should hold. The tool spreads
a VM over several storages when its disks add up to more than this. It
spreads until no storage holds more than this much of the VM, or as little
as the storages available allow. With fewer storages than disks (the usual
case), the cap is not reachable, and it need not be. Five 2 TiB disks on
three storages end up 2 + 2 + 1 disks (4 + 4 + 2 TiB), the smallest peak
three storages allow. The fullest storage then needs `2.0 × 4 TiB = 8 TiB`
free for a snapshot instead of `20 TiB`. The tool cannot split a single
disk larger than the cap, so its own storage may hold it in full. Only what
is *added* to that disk there counts as excess. The rule is a standing
preference, not a repair. It never displaces a reserve or free-space
repair, and it never creates a shortfall. `objective.mu_vm_split_per_tib`
sets how strongly the tool pursues the rule. The tool plans a group holding
such a VM on one storage even when its I/O and data are in balance. `null`
turns the rule, that weight and the planning trigger off. The value must be
`null` or above `0`. A `0` would spread every multi-disk VM. That is a
typo, not a policy. **Too low** spreads many VMs for little gain and costs
migrations. **Too high** keeps large VMs together and leaves their snapshot
reserve large.

### `snapshot_reserve.count_foreign_volumes`

Boolean, default `true`.

Count volumes DRS does not manage (templates, ISOs, backups, other groups'
disks, orphans) against a storage's used capacity. Keeping it `true` is strongly
recommended. Turning it off understates real usage and erodes the
reserve that the key is meant to guarantee, without warning.

## `free_space` — keep N bytes (or N%) free on top of the snapshot reserve

The Storage-DRS mandate (`IMPLEMENTATION_PLAN.md` section 5.3.1). An admin
places a new VM on a storage. The storage then has less free space than you
require, which the snapshot reserve alone does not cover. The engine migrates
data off that storage until the configured free space is free again. For exactly
this reason, the engine bypasses the drift/imbalance gates and the payback
economics, the same way it already does for a snapshot-reserve violation.
`soft` and `hard` here are the *global* defaults.
`groups[].storages[].free_space.soft`/`.hard` above override them per
storage or per `/…/`-matched pattern. The most specific value wins.

### `free_space.soft`

Size, byte-unit string, or percentage string (`"N%"`, `0 <= N < 100`),
default `0`.

The **plan-endpoint** requirement. It is the number of bytes that must be
free on a storage once the plan has fully run. `R_s = max(factor *
largest_vm_footprint, soft)`. The *larger* of the snapshot term and this
floor wins, on every storage, always. Neither term can erode the other.
The default `0` changes nothing for a config that sets no knob in this
block at all. The resulting model is identical to the pre-`free_space`
snapshot-only floor. A storage that ends the plan below its `soft`
requirement is in violation exactly like a snapshot-reserve breach. The
engine migrates disks off it until the requirement is met. If the engine
cannot meet it, the engine reports the residual shortfall as unfixable.
The report is `plan`'s `⚠ unfixable shortfall` line, with the amount and
the pinned disks in the way. The tool does not guarantee the requirement
is *achievable*. It only guarantees that it is pursued unconditionally.

### `free_space.hard`

Size, byte-unit string, percentage string, or `null`, default `null` (=
`soft`: no dip at all).

The **transient** floor. It sets how far a storage may dip below `soft`
while a disk lands on it mid-migration (section 8.1). A mirror target is
fully allocated before its source releases anything. A plan that lands a
disk on a storage that is *heading toward* `soft` needs room to pass
through it without ever crossing `hard`. The default `null` keeps the
transient invariant exactly as strong as it was before `free_space`
existed. That means no dip below `soft` at all. Set this key strictly
below `soft` only when you have deliberately decided to trade a bounded,
planned dip for it. A transient dip can only ever land on a storage the
*finished* plan leaves compliant. You never use the dip to permanently
weaken the requirement. A `hard` value above `soft` is a config error. A
floor stronger than the requirement it is supposed to relax would make
every plan for an already-compliant storage infeasible.

## `gates` — deciding whether to act at all

### `gates.drift_threshold`

Fraction, default `0.10`.

The tool skips re-planning until the load vector has moved by this much in
L1, relative to the vector recorded at the last executed balance. Lower
values react sooner and migrate more. Below roughly 0.05 the tool reacts
to noise on a busy cluster. The key interacts with
`gates.imbalance_threshold`. Drift decides *whether to look*. Imbalance
decides *whether to act*.

The compared vector is the load the balancer itself acts on, whatever
produced it. With `forecast.model: holt_winters` that is the
forecast-scaled load, and the vector recorded at the last balance is the
forecast-scaled one too. A change in forecast state between two runs
counts as drift even when the workload did not change. Such a change is
switching `forecast.model`, or the backtest starting to pass or fail. The
tool counts such a change on purpose. The picture the balancer places
disks against changed, so the balancer reconsiders the placement. The
change only opens the imbalance gate. A plan still has to clear the
payback test.

### `gates.imbalance_threshold`

Fraction, default `0.20`.

The minimum relative spread across a group's storages before the tool
builds a plan. The tool leaves a group under this threshold alone, even
if it has drifted.

### `gates.capacity_spread_threshold`

Fraction or `null`, default `0.25`.

The data-spread counterpart of `gates.imbalance_threshold`. It is the
minimum relative spread in fill fraction (bytes used / capacity) across a
group's storages before the tool builds a plan. The tool evaluates it even
when the group's I/O is already perfectly balanced. In that case,
`objective.delta_capacity_spread` does the spreading. The value can
legitimately exceed `1`. A group filled to 5% that keeps 60% of its bytes
on one storage deviates as much as a full one does. Unlike the
drift/imbalance gates, this gate **bypasses** them when it fires. A
stable, balanced workload is not a reason to keep data concentrated on
one storage. `null` disables the gate outright. The gate also cannot fire
on a group with no data at all (mean fill `0`).

**Opening a group is not the same as moving data.** When this gate fires,
the tool plans the group. The objective decides whether anything moves. On
a group whose I/O is already balanced, only
`objective.delta_capacity_spread` can pay for a move. That weight is a
price per TiB. A disk pays for its own move once it is larger than a
break-even size (about 270 GiB at the defaults; the entry for that weight
derives it). When the only disks that would help are smaller, `plan`
reports `→ ACT` followed by `no moves made`. The line names
`objective.beta_move_count`,
`objective.gamma_move_bytes_per_tib` and
`objective.delta_capacity_spread`, and it prints the break-even size.
Either raise `objective.delta_capacity_spread` (or lower
`objective.beta_move_count`) until the moves you want pay. Or raise this
threshold (or set it to `null`) if you do not want the tool to plan groups
for data spread at all. The gate stays relative on purpose. It asks
whether the data is skewed enough to plan for. That is a question about
proportions. The objective asks whether a particular move is worth it.
That is a question about bytes.

### `gates.cooldown_per_disk`

Duration, default `24h`.

The tool pins a disk that moved within this duration. The planner does not move
it. This stops a disk from moving back and forth between two storages that are
still noisy.

### `gates.cooldown_per_storage`

Duration, default `1h`.

A storage that took part in a migration within this duration accepts no new
incoming moves. The value **must exceed the implied wipe time of the largest disk
of that storage** (`largest_disk / |saferemove_throughput|`). Use the magnitude of
the throughput. See [`verify-storages`](25-show-load-and-verify-storages.md) for
why the value is often negative. With a shorter cooldown, the next run plans onto
a storage that is still draining, and the run stalls.
`pve-storage-drs verify-storages` computes the wipe time and warns when the
configured cooldown is too short.

## `migration` — cost, bandwidth and the payback rule

### `migration.bwlimit_bytes_per_sec`

Size/s, default `209715200` (200 MiB/s).

The tool passes the value to `move_disk` as `bwlimit`. It converts the value to
KiB/s at the API call site, because KiB/s is the unit of the API, never bytes/s.
The value is also the divisor of the mirror-duration estimate that the payback
test uses. The test assumes that the mirror of a move takes
`disk_bytes / bwlimit_bytes_per_sec` seconds (see `migration.payback_ratio` below
for the full cost/benefit comparison).

This value is the **whole** throttle of a migration. A migration may start at any
time. The tool does not model storage saturation. The other limits are
`migration.max_single_move_duration` and the transient reserve invariant (see
`snapshot_reserve.factor`).

### `migration.source_load_weight`

Weight, default `1.0`.

The extra in-flight I/O that the cost model charges to the **source** storage while
a mirror runs. A mirror is one sequential reader, so `1.0` is the natural value in
the units of the load model.

### `migration.target_load_weight`

Weight, default `1.0`.

As `migration.source_load_weight`, for the target (one sequential writer).

### `migration.payback_horizon`

Duration, default `365d`.

The horizon `H`. The tool assumes that the reduction of imbalance, data spread and
VM affinity that a plan achieves persists over this horizon:
`benefit = (alpha_spread * ΔE + delta_capacity_spread * ΔF + kappa_vm_affinity *
ΔA + mu_vm_split_per_tib * ΔO) * H`. Each `Δ` is the improvement that the plan achieves in that term: the
value before the plan minus the value after it. `ΔE` is for imbalance, `ΔF` for
data spread, `ΔA` for VM-affinity fragmentation and `ΔO` for the split excess of
large VMs in TiB (see `snapshot_reserve.split_vm_footprint`). See `objective` below for what
each term measures. `ΔA` may be negative. A balance move that splits a VM pays for
that fragmentation out of its other gains (`IMPLEMENTATION_PLAN.md` section 7.2).

A value of `0` would disable the payback test entirely. The tool rejects it when it
loads the config: `payback_horizon > 0` is required (`IMPLEMENTATION_PLAN.md`
section 11.1).

This is an explicit assumption about how long a placement lasts, not about the
patience of the operator. A migration pays its cost once and early. Its benefit
accrues as long as the workload keeps running on the new placement.
Infrastructure timescales are months to years, and the default assumes at least one
year. Configuration validation warns (it does not fail) below `30d`. There, the
test starts to reject real benefit that accrues slowly again. Lower the value
toward the actual lifetime of your VMs only for fleets that really are short-lived
(CI runners, render farms, lab clusters).

### `migration.payback_ratio`

Weight `> 0`, default `10.0`.

`λ`: a plan is only accepted when `benefit >= payback_ratio * cost`, summed
over every disk the plan moves. One exception exists: a plan that lowers the
reserve or free-space shortfall of its group passes without this test (see
`free_space`). The per-move limit `migration.max_single_move_duration` still
applies to it. Both sides are in **load-seconds**.
Load-seconds are average in-flight I/O requests multiplied by seconds.
`load_weights` produces that request unit (see `metrics.read_time_ns`
above). That is what makes the comparison meaningful. A disk's cost
(`cost_d`) is the extra in-flight I/O the migration itself imposes. The
mirror takes `disk_bytes / migration.bwlimit_bytes_per_sec` seconds. While
it runs, the tool counts `migration.source_load_weight` on the source and
`migration.target_load_weight` on the target. If
`migration.account_saferemove_wipe` is on and the source storage has
`saferemove` set, the tool also counts `migration.wipe_load_weight` on the
source for as long as the old volume takes to be zeroed. Benefit is the
improvement the plan gets in imbalance, data spread and VM affinity. The
tool weighs each term exactly as in the `objective` section below and holds
the gain for `migration.payback_horizon` (see above for that formula). `λ`
is the numeric form of "migrating a very large disk might generate more
traffic than it saves." (`IMPLEMENTATION_PLAN.md` section 7.2.)

### `migration.max_single_move_duration`

Duration, default `6h`.

A hard ceiling per move on `duration_mirror + duration_wipe`. The tool rejects a
move that it predicts to take longer than this, whatever the aggregate payback
test says.

### `migration.account_saferemove_wipe`

Boolean, default `true`.

Include the post-move `saferemove` zeroing pass in cost and duration
estimates. The PVE LVM `saferemove` throughput defaults to 10 MiB/s. The
cleanup of a 1.5 TiB disk takes about 44 hours at that rate. The mirror of
the same disk takes about 2.2 hours. So the zeroing pass can be much
longer than the mirror. Set this key to `false` only if you have verified
`saferemove` is off on every storage in a group. If that assumption is
wrong, the key understates real migration cost badly.

### `migration.wipe_load_weight`

Weight, default `1.0`.

The in-flight I/O that the cost model charges to the source for the whole duration
of the `saferemove` wipe. The zeroing pass is one sequential writer, so `1.0` is
the natural value.

### `migration.assume_thick_provisioning`

Boolean, only `true` (the default) is accepted. **Kept so a config that
spells it out still loads; `false` is refused at startup.**

This tool never considers over-provisioning. Every disk counts at its
*provisioned* size, in the reserve arithmetic, the free-space requirement,
the transient check and the cost model. A thin-provisioned storage (Ceph
RBD, LVM-thin, ZFS) counts exactly as a thick one. Thin provisioning lets a
pool hold more provisioned bytes than it has. This tool deliberately never
counts on that, because a move that only fits *if the disks stay thin* is
one a growing guest can turn into a full pool.

Plan for this consequence. On a thin pool, the tool's idea of "used" is the
sum of the disks' sizes plus foreign volumes. That sum can be several times
what the pool reports as allocated. So a `free_space.soft` of `"90%"` on a
pool with plenty of *actually* free space can show a large shortfall in
`plan`/`explain`. The engine then migrates disks off that pool. That is the
intended behaviour, not a miscalculation.

The same holds at the moment of the move. Just before each `move_disk`,
the check that `apply` makes re-reads the target's volume listing. It sums
the volumes' provisioned sizes, never the pool's allocated figure. So it
can refuse a move onto a thin pool that still looks half empty in the PVE
UI. `show-load`, `plan` and `explain` print the provisioned figure as the
storage's usage. When the pool's own number differs, they add it in
brackets as `(pool reports X allocated)`.

### `migration.tiny_disk_bytes`

Size, default `67108864` (64 MiB).

A disk smaller than this carries zero `beta_move_count`/`gamma_move_bytes_per_tib`
cost in the objective and zero `cost_d` in the payback model. It still
counts as a scheduled move. Every hard per-move safety rule
(`max_single_move_duration`, the transient reserve invariant) applies to it
exactly like any other move. It needs no payback verdict. It cannot make a
plan fail the aggregate `payback_ratio` test.

Together with `objective.kappa_vm_affinity`, this lets a tiny volume rejoin its
VM at no cost, instead of paying the price of a real migration. A tiny volume is,
for example, an `efidisk0` var store or a `tpmstate0`. Both are normally a few
hundred KiB to a few MiB. Both device types move online on PVE 9.2. Once their
cost is small enough to ignore, there is no reason to price their reunion like a
real migration. (`IMPLEMENTATION_PLAN.md` §§5.4, 7.1, 7.3, 3.6.)

The default sits comfortably above either of those. It also sits far below
any disk the payback rule was written for. So a 528 KiB EFI disk always
qualifies and a 64 GiB data disk never does. Set the key to `0` to restore
the pre-section-7.2 accounting. Under that accounting, every disk is
charged a full migration, however small. Setting the key too high (larger
than disks you actually want cost-accounted) lets real, meaningfully-sized
migrations bypass the payback safety test entirely. No upper bound is
enforced beyond `≥ 0`. The tool leaves this as an operator judgement call,
not a validated range.

**A disk below this size only ever moves together with its VM.** It may end
a plan where it is now. It may also end the plan on a storage where at least
one *larger* disk of the same VM, in the same storage group, ends the plan.
It never ends the plan on a storage of its own. So an EFI or TPM disk
follows its VM's system disk when that disk moves. It rejoins that disk when
the VM is already split. Otherwise it stays put. Moving it alone gains
nothing. The disk carries no load worth balancing. As a free-space
"repair", it frees a fraction of a MiB while splitting the VM from its
firmware state. Larger disks are not bound this way. A VM's big disks can
still be placed on different storages when they do not fit together. They
can also be placed on different storages when only a split balances the
group. `objective.kappa_vm_affinity` is the soft preference against that. A
VM whose disks in this group are *all* below the threshold has nothing to
follow. This is typically because its system disk is in a different group.
The tool pins those disks, with the pin message
`small disk with no larger disk of its VM in this group (migration.tiny_disk_bytes)`.
Nothing ever moves between groups. Setting the threshold to `0` switches
this rule off along with the cost exemption.

## `objective` — the solver's trade-off weights

The solver (and, for the terms it also uses, the heuristic backend)
minimizes one weighted sum, evaluated per group:

```
  alpha_spread            * (imbalance: summed deviation of each storage's utilization from the group's target)
+ beta_move_count         * (number of migrations)
+ gamma_move_bytes_per_tib * (TiB actually migrated)
+ kappa_vm_affinity       * (VM disk fragmentation, I/O-weighted — see below)
+ delta_capacity_spread   * (data spread: TiB by which each storage's data is off its capacity-proportional share, summed)
+ mu_vm_split_per_tib     * (split excess: TiB of each large VM beyond the cap on its fullest storage)
+ reserve_violation_penalty * (reserve violation, heuristic backend only — see below)
```

The first six terms are calibrated to share one scale. The unit is
average in-flight I/O per storage (see `metrics.read_time_ns` above).
That is what makes the weights directly comparable. At the defaults, a
migration must reduce the summed imbalance by at least 0.25 requests just to
cover its own `beta_move_count` cost. Its `gamma_move_bytes_per_tib` and
`kappa_vm_affinity` costs come on top. The separate payback test
(`migration.payback_ratio` above) also comes afterwards.
Each term is explained, with its own default and worked numbers, in its
own entry below. (`IMPLEMENTATION_PLAN.md` section 5.4 has the full
derivation. Section 14.3 computes two competing plans with this exact
formula.)

### `objective.spread_metric`

`l1` or `minmax`, default `l1`.

How the tool measures imbalance. `l1` sums each storage's deviation from
the group's target utilization. `minmax` counts only the single hottest
storage. `l1` is the default because `minmax` is indifferent to a second
nearly-as-bad storage once the worst one is fixed.

### `objective.alpha_spread`

Weight, default `1.0`.

Weight on the imbalance term. The term sums each storage's deviation from
the group's target utilization. See `objective` above for where this term
sits in the full objective. The default `1.0` stands against the default
`beta_move_count: 0.25`. So a migration must reduce that sum by at least
0.25 requests to be worth making at all.

### `objective.beta_move_count`

Weight, default `0.25`.

Penalty per migration. This key is the tunable implementation of
"minimize the number of migrations". A strict minimum would refuse a
second cheap move that halves the remaining imbalance. That outcome is not
desired (see the "Requirement interpretation" note in
`IMPLEMENTATION_PLAN.md`). Raising this weight trades balance quality for
fewer, larger moves.

### `objective.gamma_move_bytes_per_tib`

Weight per TiB, default `0.05`.

Penalty per TiB actually migrated, biasing against moving large disks
specifically (as opposed to `beta_move_count`, which only counts moves).

### `objective.kappa_vm_affinity`

Weight, default `0.50`.

Penalty per extra storage a VM's disks are spread across. The tool counts
this only **within** a group. A VM split across two groups is structural
and cannot be repaired by any migration, so the tool does not count it.
The tool weights the penalty by the VM's own I/O share of the group, as
`w_v = max(1, ℓ_v / ℓ̄)`. `ℓ_v` is the VM's total load: the sum, in
average in-flight I/O, of every one of its disks in the group, including
disks pinned this run. `ℓ̄` is the group's mean load per VM: the group's
total load divided by every VM that owns a disk in the group. The floor of
`1` means a below-average VM's fragmentation is weighted exactly as
configured. A VM running several times the group's average I/O is worth
correspondingly more to keep together. The configured weight alone cannot
show that. A VM doing 2.7x the group's average I/O, for example, is
effectively weighted as if `kappa_vm_affinity` were 2.7 times higher for
that VM alone. This is a soft preference. A strong imbalance or a capacity
constraint can legitimately override it. (`IMPLEMENTATION_PLAN.md`
section 5.4.)

### `objective.mu_vm_split_per_tib`

Weight `>= 0`, default `1.0`.

Weight, per TiB, of the large-VM split rule
(`snapshot_reserve.split_vm_footprint` above). The tool applies it to every
VM above that threshold. For such a VM, the *excess* is how far its
footprint on its **fullest** storage exceeds the VM's cap. This is the peak,
not a sum over storages. The reserve a storage needs is driven by the
largest footprint on it.

Moving a disk off the fullest storage lowers the excess by up to the disk's
size. The move costs `beta_move_count + gamma_move_bytes_per_tib × TiB`. If
the move opens a storage the VM did not use yet, it also costs
`kappa_vm_affinity`. At the defaults, a move pays above about 0.26 TiB onto
a storage the VM already uses. It pays above about 0.79 TiB onto a new one.
A VM made of many small disks splits more reluctantly than one with a few
large disks. Raise the weight to split harder.

A large VM's affinity weight is fixed at 1. The I/O-weighting of
`kappa_vm_affinity` does not apply to a large VM. So a busy VM's I/O cannot
veto the policy. `0` disables the term and the planning trigger.
Configuration validation warns when the weight is above `0` but below
`kappa_vm_affinity`. In that range, a TiB of excess no longer covers the
cost of a new storage, and the rule rarely acts.

### `objective.delta_capacity_spread`

Weight per TiB, default `0.5`.

Price of one TiB of data spread. A storage's data spread is how far the data
on it is from its capacity-proportional share of the group's data. If a
group holds 20 TiB across storages of 30, 10 and 10 TiB, the shares are 12,
4 and 4 TiB. A storage holding 15 TiB is 3 TiB off. The term is the sum of
those deviations over the storages, in TiB, times this weight. It bounds
the share of a group's data any single storage failure costs. It also keeps
peak fill uniform across the group. `0` disables the term entirely.

**It is absolute, so it does not depend on the group's size.** Moving a TiB
of data from a storage that has too much to one that has too little removes
two TiB of deviation (one at each end). The move earns
`2 × delta_capacity_spread`, which is `1.0` at the default. This gain holds
whether the group holds 5 TiB or 500. A disk of `X` TiB pays for its move
when that gain exceeds its cost, `beta_move_count + gamma_move_bytes_per_tib × X`.
This gives a break-even size

```
X* = beta_move_count / (2 × delta_capacity_spread − gamma_move_bytes_per_tib)  TiB
```

At the defaults that is `0.25 / (1.0 − 0.05) ≈ 0.263 TiB`, about 270 GiB.
Larger disks that sit on an over-full storage and have somewhere to go pay
for their own move. Smaller disks move only when something else moves them
anyway, such as their VM's other disks or the I/O balance. When
`2 × delta_capacity_spread` is at most `gamma_move_bytes_per_tib`, no disk of
any size can pay. The term is on but inert in that case, and configuration
validation warns. `plan` prints `X*` in its `no moves made` line.

I/O balance stays the first priority. This term acts as an exchange rate.
At the default, one TiB moved toward its share earns a gain of `1.0`. The
gain is worth one unit of in-flight-load deviation. `alpha_spread` is per
unit of in-flight load. On a group whose I/O is imbalanced, the I/O term
dominates. On a group whose I/O is already balanced, this term is what
decides.

**Choosing a value.** Decide the smallest disk you want moved purely for
data spread, `X_min`. Then set
`delta_capacity_spread = (beta_move_count / X_min + gamma_move_bytes_per_tib) / 2`.
For `X_min = 100 GiB` (about 0.098 TiB) that is about `1.3`. For
`X_min = 1 TiB` it is `0.15`.

Too high moves many small disks for little gain. Every TiB of spread now
outweighs more of the I/O term, so data evenness can override I/O evenness.
Too low (or `0`) leaves data spread to chance. The capacity gate still opens
groups, but nothing moves for data spread.

**Upgrading:** earlier versions priced the deviation relative to the
group's mean fill. A value raised under that formula does not carry over.
Re-derive it from `X*`. A replayed bundle with five equal storages, balanced
I/O and data concentrated on three of them: under the relative form at the
default it planned no capacity move. Under the absolute one it plans 20
data-disk moves. They are 100 GiB disks that follow their VM, up to 1.95 TiB
(observed on the operator's own cluster).

### `objective.affinity_counts_pinned_disks`

Boolean, default `true`.

Whether a disk that cannot move this run still counts toward
`kappa_vm_affinity`. Such a disk is snapshot-blocked, excluded, or on a
locked VM. The default is `true`. A disk that cannot move still *occupies*
a storage, so the VM really is spread. The disk's fixed location is an
anchor the VM's movable disks can be drawn back to. Note that
`efidisk0`/`tpmstate0` are *not* in this pinned set on PVE 9.2. They move
online.

Set it to `false` to count movable disks only. That changes how plans score
a reunion. Take a VM with a snapshot-blocked disk on `san-a`:

- **One movable disk, on `san-b`.** With `false` the VM's counted footprint
  is that one disk, so the VM is never "spread". Moving the disk to `san-a`
  (reuniting the VM) scores exactly the same as leaving it or sending it to
  a third storage. The reunion is invisible, and the solver may pick any of
  the three options. With `true` the VM counts as spread over two storages
  until the disk joins `san-a`. Then `kappa_vm_affinity` pulls the disk
  there.
- **Two movable disks, both on `san-b`.** With `false` the counted
  footprint is `san-b` alone. Moving one of the disks to `san-a` to rejoin
  the pinned disk makes the footprint `{san-a, san-b}`. The move is charged
  `kappa_vm_affinity` as if the VM had just been split. With `true` that
  same move is neutral, and moving both is a gain.

The pinned disk's storage is fixed, so counting it never asks for anything
unreachable: it only prefers targets where the VM already has a disk.

**This default changed after 0.1.6** (it was `false`). If you have not set
it and your cluster has pinned disks, expect plans to prefer targets where
the VM already has a disk. To keep the old behaviour, set it explicitly.

### `objective.reserve_violation_penalty`

Weight, default `1000.0`.

The reserve-violation weight in the **heuristic backend**'s objective
(`solver.backend: heuristic`, or `auto` when it falls back to the heuristic). The tool multiplies the weight straight into
`reserve_penalty_term = objective.reserve_violation_penalty *
reserve_shortfall_tib`. This is one of the seven terms that the
`objective:` line of `explain` prints.

The tool uses the weight exactly as configured. There is no floor, no
automatic raise and no warning.

The MILP backend (`solver.backend: cbc`, and `auto`) solves the reserve
**lexicographically** instead. It fixes the reserve as a hard constraint
and solves for it first. It does so before the rest of the objective above
is considered. So no weight, this one included, can trade the reserve away.

A single-stage alternative exists on paper. It computes a
provably-dominant penalty from the group's own load instead of taking this
key at face value. It uses that penalty as a `max(configured, computed)`
floor. The alternative is not implemented. So the tool never raises this
key automatically, for any backend. The heuristic backend uses exactly what
you set. The MILP backend never consults the key at all.
(`IMPLEMENTATION_PLAN.md` section 5.3.)

## `solver` — which backend plans

### `solver.backend`

One of `auto`, `cbc`, `heuristic`; default `auto`.

`auto` uses CBC. That is the packaged solver path via `python3-pulp` +
`coinor-cbc`, both hard dependencies of the Debian package. `auto` falls
back to the dependency-free heuristic if that library is not importable or
its `cbc` binary cannot run. That happens with a plain `pip install`
without the `solver` extra. It never happens on a Debian install.

`cbc` forces that one backend. The solve for a group falls back to the
heuristic if the library is not importable or if `cbc` cannot solve within
`solver.time_limit_seconds`. Use a specific backend only to reproduce or
compare a result.

`heuristic` skips the solver entirely. See `docs/internals/91-optimize.md`.

A `cpsat` value existed through release 0.1.8. It selected an optional
`ortools`-based backend. The value was removed, because `ortools` has no
Debian package and the backend could therefore never run on a PVE host. A
config that still names the value now fails schema validation, loudly, as
it should.

### `solver.time_limit_seconds`

Duration, default `60`.

Wall-clock budget for a MILP solve attempt. If the solver has a feasible plan when the limit ends, the tool uses that plan
and reports it as `feasible`, which means not proven optimal. The tool falls back
to the heuristic only when the solver finds no feasible plan in time. It never
emits a partial assignment.

### `solver.mip_gap`

Fraction, default `0.02`.

Acceptable optimality gap for the MILP solve. CBC may stop once the best
solution found is within this fraction of a proven lower bound. It then
does not solve to exact optimality. (`IMPLEMENTATION_PLAN.md` section 5.5.)

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

How many moves may be in flight across the whole run at once. The setting
applies in `--mode auto` only. `dry-run` and `confirm` always run strictly
sequentially, regardless of this setting.

A value above `1` requires the *generalized* form of the transient reserve
invariant (see `snapshot_reserve.factor` above for the single-move
definition). Several disks can land on one storage at once. None of their
sources releases space until the disk individually completes. `apply`
re-checks the invariant live before launching each move.

Launch order stays strictly FIFO. `apply` never reorders the scheduler's
own queue to keep every slot busy. A move that cannot launch yet is waited
for, not skipped past. See the "Concurrent execution" section of
`docs/manual/28-apply.md`.

### `execution.max_migrations_per_run`

Integer `>= 1`, default `5`.

A ceiling on how many moves one invocation executes. The ceiling is
independent of how many the plan contains. The remainder waits for the next
run. This applies in `auto` mode only. `dry-run` and `confirm` execute or
report the whole plan regardless. The budget is shared across every group
the run visits. It is not reset per group.

### `execution.max_concurrent_per_storage`

Integer `>= 1`, default `1`.

Caps concurrent moves touching one storage, counting it as either source or
target. The cap applies in `--mode auto` only. At the default of `1`, two
moves targeting the same storage serialize automatically. The generalized
transient invariant collapses to its simple single-move form. Raise the cap
only deliberately, on a storage with real spare headroom. Two moves off the
same source also means two concurrent `saferemove` wipes sharing one
throttle.

### `execution.max_replans_per_run`

Integer `>= 0`, default `3`.

A cap on how many times one run may abandon its current plan and re-plan
from newly observed state. The cap applies in `auto` mode only.

A mismatch between the plan and reality is normal. A VM may be
live-migrated mid-plan, a lock may have appeared, someone else may have
created or moved a disk, or another tool may be filling the target. A
cluster churning faster than the engine can plan is a condition for a
human, not for indefinite retrying. In `confirm` and `dry-run`, the tool
reports a mismatch (`replan_needed`) and stops that group's run. The
operator re-runs the group by hand. The tool does not re-plan
automatically.

When the cap is reached, the run bails out and exits `0`. The next run
starts from freshly observed state. Set too low, and ordinary churn ends
runs early. Moves then wait for the next run. Set too high, and a cluster
that keeps changing under the tool keeps the tool planning instead of
waiting. `0` disables re-planning. The first mismatch ends the run.

Only a *mismatch* re-plans. An error reading PVE or Prometheus fails the
run outright. Such an error never counts against this cap (see
`28-apply.md`, "When something cannot be read").

### `execution.abort_on_failure`

Boolean, default `true`.

On a failed move, the tool stops the run and reports. It does not continue
with the remaining plan. The cluster is left in a valid intermediate state
either way. The next run re-plans from reality.

### `execution.poll_interval_seconds`

Duration, default `10`.

How often an in-flight `move_disk` task's status is polled.

### `execution.api_outage_timeout`

Duration, default `1h`. `0` disables.

While `apply` executes, the tool retries a Proxmox VE API read that fails
because the API cannot be reached. A read fails this way when the
connection is refused or times out. It also fails on a TLS handshake
failure. It fails when the answer is not valid API output, such as a
firewall's error page. It fails on an HTTP 429 or 5xx, as during network
maintenance or a node restart. The tool retries with back-off (5 s
doubling to 60 s) for up to this long. This keeps the run from ending
while a migration may still be going on.

The clock is per call. It restarts after each success. An error the API
actually answers is never retried. This includes 4xx errors, in particular
401/403 "not authorized".

Outside this window, every read still gets a short retry. The retries take
waits of 1 s, 2 s and 4 s, each multiplied by a random factor between 0.5 and
1.5. A single dropped connection
does not fail a dry run or `show-load`. A virtual IP moving to another node
does not fail them either. Each retry after a connection-level failure
starts from a fresh login and connection.

Failover between API hosts is not done here. Point `proxmox.host` at a name
or virtual IP that already fails over.

`move_disk` itself is never retried blindly. A connection that dropped after
the request went out may still have started the task. If the run does give
up, the next run discovers a still-running move (`state.json` and the
cluster task list) and leaves that VM alone.

### `execution.locks.wait_timeout`

Duration, default `4h`.

How long the tool waits for a VM's config `lock` to clear. The tool also
waits for a task still running on the VM to finish, such as the "Erase
data" job of an earlier move. When the wait ends, the tool applies
`execution.locks.on_timeout`.

The lock can hold any non-empty value. The tool treats the set as
open-ended and never whitelists it.

The default is generous. A backup of a large VM can easily run for hours.
That is a normal, not exceptional, condition.

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

The `move_disk` *task itself* can fail immediately. The error is PVE's own
`can't lock file '/var/lock/qemu-server/lock-<vmid>.conf' - got timeout`.

This is a different lock than the config `lock` attribute that
`execution.locks.wait_timeout` waits out. The lock can stay held for a
moment even after that attribute already reads clear. This is typically the
previous move's own `saferemove` wipe/cleanup finishing for the same VM.

The tool makes this many extra attempts before it reports the move
`failed`, like any other task failure. It waits
`execution.locks.task_retry_backoff` before each attempt. `0` disables the
retry.

### `execution.locks.task_retry_backoff`

Duration, default `15s`.

How long to wait between a task-lock-timeout failure and the next
`move_disk` retry attempt.

### `execution.source_release.wait`

Boolean, default `true`.

Wait for the source volume of a completed move to actually disappear (and
the VM to be unlocked) before the tool considers the move done. The tool
does not trust the `move_disk` task's own `OK` status. With `saferemove`
enabled, `OK` does not mean the source space is back yet. Set this to
`false` only on storages verified not to wipe.

### `execution.source_release.timeout`

Duration, default `48h`.

Bound on the wait above. The bound is sized for a multi-TiB disk wiping
at the default 10 MiB/s. Set it to at least `largest_disk / |saferemove_throughput|`
for every storage where `saferemove` is on. `verify-storages` checks this.

### `execution.time_windows[].days`

List of `mon`..`sun`. Required in every window: to run every day, name all
seven days.

Which days a time window applies on. The window applies only to
`execution.mode: auto`. `dry-run` and `confirm` are not time-restricted, because neither mode changes
anything without a human already present.

### `execution.time_windows[].start` / `execution.time_windows[].end`

`HH:MM` strings, required together, must differ.

The window `auto` mode is permitted to execute moves in. The window is in
the **local time of the host running `pve-storage-drs`**, not UTC. That is
the same convention `systemd.timer`'s own `OnCalendar=` uses by default.

A window may cross midnight (`start: "22:00"`, `end: "06:00"`).
`start == end` is rejected as ambiguous. It would silently mean either
"never" or "always".

No `time_windows` configured at all means no restriction. `auto` may
execute at any time. That is the deliberate default, not merely the absence
of a rule.

Before starting a move, `auto` also checks its estimated duration. If the
move would not finish before the window closes, `auto` refuses it. The
group's run stops cleanly. A move already in progress is not aborted.

## `exclude` — what DRS never touches

### `exclude.vmids`

List of integers, default `[]`.

VM ids whose disks are never moved.

### `exclude.disks`

List of `"vmid:device"` strings, default `[]`, e.g. `["101:scsi1"]`.

Individual disks excluded regardless of their VM.

### `exclude.storages`

List of storage ids, default `[]`.

Intended meaning: storages that no disk moves onto or off. **This version does
not apply the key** (a known defect, issue #1): plans still move disks onto and
off the listed storages. To keep a storage out of balancing, remove it from
`groups`.

### `exclude.tags`

List of PVE tags, default `["no-drs"]`.

A VM carrying any of these tags opts out entirely.

### `exclude.skip_vms_with_snapshots`

Boolean, default `true`.

**The key has no effect in this version** (issue #5). The tool pins every disk
with a snapshot or an unreferenced companion volume, whatever the value. PVE
rejects `move_disk delete=1` on a snapshotted volume in any case. Keep this
`true`.

### `exclude.stopped`

Boolean, default `true`, and `true` is the only accepted value.

Stopped VMs are never touched. Whatever violation their disks cause, the
tool does not move a stopped VM's disks. Such a violation may be a storage
below its snapshot reserve. It may be a storage below the free space you
configured. It may be a badly out-of-balance storage.

This is a safety property rather than a tuning knob. Replication and backup
products such as Veeam track a VM's volumes by their location. Moving the
disks of a replicated VM breaks the replica badly.

A VM whose status is not `running` is skipped before its configuration is
even fetched. Its disks still occupy space on their storage. Their bytes
are counted as foreign volumes. That reduces the room the planner has to
work with. The planner then repairs a violation by moving running VMs'
disks instead, or reports that it cannot.

A VM that was running when the plan was made but has stopped by the time
its move is due is refused at apply time. The run then asks for a re-plan.

The key exists only so that a configuration which spells it out keeps
loading. `false` is **refused at load time** with an error naming the
setting, because it would promise a mode that does not exist. There is no
too-high or too-low: the setting has one value.

Renamed from `running_only`, which meant the same as `exclude.stopped:
true`. A configuration still carrying the old key is rejected at load time
as an unknown key; remove it.

### `exclude.include_unused_disks`

Boolean, default `true`.

Whether detached (`unusedN`) volumes are movable. They carry zero load.
The solver only relocates one to repair a capacity violation. It never
relocates one for balance, since there is no benefit to buy. Set this to
`false` to pin them in place entirely. They still count via
`snapshot_reserve.count_foreign_volumes` either way.

## `report`

### `report.warn_pinned_load_fraction`

Fraction in (0, 1], default `0.25`.

Pinned load (snapshots, locks, exclusions) can exceed this fraction of the total
load of a group. The remaining imbalance may then be structural, not a failure of
the planning. `explain` says so, together with the best spread that the pins allow
(see [`29-explain.md`](29-explain.md)).

## `state`

### `state.path`

File path, default `/var/lib/pve-storage-drs/state.json`.

A file on a local disk, one copy per host. It is deliberately never on `/etc/pve`
(see [`00-installation.md`](00-installation.md)). Losing this file is safe but not
free. The cooldowns and the drift baseline reset, so the next run may migrate
sooner than you intend. Treat it as state that you back up, not as a cache.

`show-load` and `plan` both read this file, when it exists, for the history of the
drift gate. Neither command writes it. A missing or unreadable file only means that
every group evaluates as if the tool had never balanced it before (see
[`../internals/15-state.md`](../internals/15-state.md)).

## `forecast` — placing disks for the load they will have

The `forecast` section sets the model that predicts each disk's load for the next placement. The default model, `quantile`, uses the percentile set by `window.quantile` (p95 by default) over the last `window.lookback`. It needs no fitting and no extra history. The model `holt_winters` predicts that same percentile over the next `window.lookback`, so a disk with a rising load or a daily peak is placed for what it will do. `holt_winters` needs `2 × seasonal_periods × metrics.step` of history, which is 48 hours at the defaults. The tool uses it for a group only if a backtest on that group's recent past shows that it beats `quantile`. (Plan sections 10 and 12.1 give the derivation.)

### `forecast.model`

One of `quantile`, `holt_winters`; default `quantile`.

`quantile`: the load of each disk is the p95 (`window.quantile`) of its I/O over
the **last** `window.lookback`. It needs no fitting, no extra history and no
optional package. Every plan used it before `holt_winters` existed. With
`quantile`, nothing below applies, and the tool sends no extra Prometheus query.

`holt_winters`: the tool scales the load of each disk to a Holt-Winters forecast
of that same p95 over the **next** `window.lookback`. It fits the history of the
disk, forecasts `window.lookback` ahead and takes `window.quantile` of the forecast
path. The scaling is a ratio: the forecast p95 divided by the observed p95 of the
same history. The load thus stays on the scale for which the rest of the model is
calibrated. The tool places a disk for what it is about to do. This matters for a
disk whose load rises, or a disk with a daily peak that the last window missed. A
disk keeps its observed load in these cases:

- it is flagged for low sample coverage;
- it has no observed load;
- its model cannot be fitted.

The gates, the solver, the payback test and the ordering all see the same forecast
load.

When `holt_winters` is worth selecting: a load that follows a daily cycle (or a
weekly cycle, see `seasonal_periods`), or a load with a trend. A load with no
structure (noise around a constant) gives it nothing to predict, and the gate
below says so.

**The gate: it must beat doing nothing clever.** Once per group, the tool fits the
model on the older half of the recent history of the group
(`[now − 2·lookback, now − lookback)`). Both this model and the `quantile` model
then predict the p95 of the newer half. The group uses `holt_winters` only if its
error is no larger than the error of the `quantile` model. There is no threshold to
tune. If `holt_winters` loses, or if `2 · window.lookback` of history does not exist
yet, the group uses `quantile` for that run. The tool logs this at warning level.
`explain` and `plan --json` show what happened per group: the model used, both
backtest errors, and the number of disks scaled or kept.

**Requirements.**

- `window.lookback` must span two seasonal cycles
  (`2 · seasonal_periods · metrics.step`; 48h at the defaults). `pve-storage-drs`
  enforces this at startup and does not degrade silently.
- Prometheus must hold `2 · window.lookback` of history, or the gate cannot run at
  all.
- `python3-statsmodels` must be installed. Without it, every disk keeps its
  observed load.

### `forecast.holt_winters.seasonal_periods`

Integer `> 0`, default `288` (24h at a 5-minute step).

The number of samples per seasonal cycle. Together with `metrics.step`, it sets the
history that `holt_winters` requires: `2 * seasonal_periods * metrics.step`. That is
48h at the defaults, which a `window.lookback` of 24h can never satisfy.

To fit **weekly** seasonality instead of daily seasonality (for example, weekends
look different from weekdays), widen this key together with `window.lookback`.
`seasonal_periods: 2016` (7d at the default step of 5m) needs a `window.lookback` of
at least 14 days (`2 * 2016 * 5m`). Both a live `plan`/`apply` and
`collect-testdata` fetch the history in requests of one day each, however wide the
range gets. A large combination of `seasonal_periods` and `window.lookback`
therefore no longer risks the per-series resolution limit of a
Prometheus-compatible backend (11,000 points by default on
VictoriaMetrics/gigapipe), as an unchunked request over the same range once could.
It costs more Prometheus requests per run instead: one per day of range, per raw
metric, per group. This is a real cost that you should size on purpose. It is not a
reason to keep the range small artificially.

### `forecast.holt_winters.trend`

One of `add`, `mul`, `none`; default `none`.

The trend component that the tool passes to the underlying Holt-Winters fit
(`statsmodels`, an optional dependency; see
[`30-safety-and-status.md`](30-safety-and-status.md)). The forecast runs a whole
`window.lookback` ahead, and the model extrapolates a trend over all of it without
damping. On a real cluster, `add` scored no better than `none` in the backtest, but
it forecast one disk at 95% of the load of its whole group. Enable a trend only for
a load that really grows steadily. Then check the scaled disks in the `forecast`
block.

### `forecast.holt_winters.seasonal`

One of `add`, `mul`, `none`; default `add`.

The seasonal component that the tool passes to the same fit.

## `support` — diagnostic bundles

See [`26-collect-testdata-and-replay.md`](26-collect-testdata-and-replay.md) and
`IMPLEMENTATION_PLAN.md` section 16. The normal `plan`/`apply` path reads nothing
here. Only `collect-testdata` and the config loading of `--replay` read these
keys.

### `support.salt_path`

File path, default `/var/lib/pve-storage-drs/anonymization-salt`.

The salt is 32 random bytes. The tool generates it on first use and stores it here,
with mode `0600`. The tool never writes it into a bundle. Every pseudonym that
`collect-testdata` produces is an `HMAC-SHA256` keyed on this salt. The same object
therefore maps to the same pseudonym across runs and across bundles, until
`--new-salt` rotates the salt. This holds per salt file, that is, per node by
default. If every node of the cluster should use one mapping, point this key at a
pmxcfs path (e.g. `/etc/pve/pve-storage-drs-anon-salt`). That also replicates the
salt to every node. This is the trade-off.

### `support.bundle_dir`

Directory path, default `/var/lib/pve-storage-drs/testdata`.

The default of `-o`/`--output` of `collect-testdata`, used when you do not give
the flag.

### `support.max_series_points`

Positive integer, default `5000000`.

`collect-testdata` prints the estimated number of series samples before it fetches
anything. Above this ceiling, it refuses to run. It never truncates the data
silently. The refusal names the `--range`/`--step`/`--no-series` flags that would
bring the estimate under the ceiling.

### `support.capture_range`

The literal string `"auto"`, or a duration, default `"auto"`.

`"auto"` captures what `holt_winters` needs. That is currently
`max(2 * window.lookback, 2 * forecast.holt_winters.seasonal_periods *
metrics.step)` (twice the window, for the backtest). A bundle can thus reproduce a
model that the operator who captured it never configured. An explicit duration (e.g.
`14d`) overrides `"auto"`. `--range` on the command line overrides both.

## `monitoring` — telling your monitoring system what the last run did

### `monitoring.status_file`

String (a file path) or `null`, default `null`.

`apply` writes its status report here. `null` writes nothing. When the key is set,
`apply` rewrites the file at the end of **every** run that produced a result,
including `dry-run` runs and runs that moved nothing. The file has the format that
the `check_statusfile` plugin reads (Debian package `monitoring-plugins-contrib`).
A Nagios-style monitoring system therefore needs only a plain
`check_statusfile <path>` check. See [`36-monitoring.md`](36-monitoring.md) for the
format, for what makes a run `OK`, `WARNING` or `CRITICAL`, and for how to set up
the check.

Choose a path that the user who runs `apply` can write and that the monitoring user
can read. The file has mode `0644`, and the tool creates the parent directory if it
is missing. `/var/lib/pve-storage-drs/status`, beside `state.json`, is the natural
place.

The key interacts with the `--age` option of the plugin. The modification time of
the file shows that the timer still fires. A timer that runs every 15 minutes needs
a check like `check_statusfile -a 1h`. The default of the plugin, 26 hours, suits a
daily timer. If the age is too generous, a stopped timer goes unnoticed for that
long. If it is too tight, one slow run turns the check `WARNING`. The tool logs a
write failure (`status_file_write_failed`). A write failure never changes the run or
its exit code.
