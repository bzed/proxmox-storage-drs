# Reading `show-load` and `verify-storages`

Both commands only read. Neither command changes anything, in any
`execution.mode`. Run them whenever you want to see what the tool sees.

## `show-load`

The command prints every storage in every configured group, its disks, and its
snapshot-reserve status. This example uses the group of the worked example in
`IMPLEMENTATION_PLAN.md` section 14. `config/drs.example.yaml` ships the same
group and weights. You can thus trace the numbers to that section. They are not
invented for this page:

```
$ pve-storage-drs -c /etc/pve/drs.yaml show-load
Group fc-tier1 → ACT: reserve violated on san-a; acting now regardless of the normal drift/imbalance thresholds -- a capacity shortfall is never delayed by them
  san-a  provisioned 4.50 TiB/8.00 TiB  L=6.50 u=6.50  ⚠ reserve short by 2.50 TiB  (largest VM footprint 3.00 TiB = web01(101), requires 6.00 TiB free)
    web01(101):scsi0             2.00 TiB  raw     ℓ 3.00
    web01(101):scsi1             1.00 TiB  raw     ℓ 1.00
    db01(102):scsi0              1.50 TiB  raw     ℓ 2.50
  san-b  provisioned 1.50 TiB/8.00 TiB  L=0.70 u=0.70  reserve OK  (largest VM footprint 1.00 TiB = app01(104), requires 2.00 TiB free)
    mail01(103):scsi0          512.00 GiB  raw     ℓ 0.40
    app01(104):scsi0             1.00 TiB  raw     ℓ 0.30
  san-c  provisioned 512.00 GiB/8.00 TiB  L=0.20 u=0.20  reserve OK  (largest VM footprint 512.00 GiB = cache01(105), requires 1.00 TiB free)
    cache01(105):scsi0         512.00 GiB  raw     ℓ 0.20
```

The tool computes the snapshot reserve from the `largest VM footprint`. A
snapshot covers a whole VM. The room that a snapshot needs on a storage is thus
the sum of **all disks of that VM on that storage**. Here, VM 101 holds a 2 TiB
disk and a 1 TiB disk on san-a, a footprint of 3 TiB. san-a must therefore keep
`2.0 × 3.00 = 6.00 TiB` free. A rule that looks only at the largest disk would ask
for 4 TiB. The VM named beside the figure is the VM that drives it.

An older release reserved room only for the largest *disk*. After an upgrade from
such a release, a storage with two or more disks of one VM can show a new
shortfall here. The rule is correct. The cluster did not change. `plan` treats the
shortfall as a repair, like any other. Read this output first.

`provisioned` on the line of a storage is the sum of the *provisioned* sizes of
every disk on it, compared with the capacity of the storage. The disks are the
managed disks and any foreign volumes (templates, ISOs, backups, disks of other
groups). The reserve shortfall beside the figure comes from this figure. The tool
never counts on over-provisioning. It counts a thin-provisioned pool (Ceph RBD,
LVM-thin, ZFS) at the provisioned sizes of its disks, not at the allocated bytes.
On a thick pool, the two numbers are the same. On a thin pool, the command prints
the lower figure of the pool next to it, so that the shortfall does not look like
a mistake. The tool counts a shortfall in whole MiB, rounded up. A storage that is
one byte short shows `⚠ reserve short by 1.00 MiB`, never `reserve OK`:

```
  ceph-a  provisioned 3.36 TiB/9.48 TiB (pool reports 1.45 TiB allocated)  L=2.10 u=2.10  reserve OK  (largest VM footprint 1.00 TiB = app02(204), requires 2.00 TiB free)
```

Only the provisioned figure ever enters a decision. The command shows the
allocated figure for information only. (`--json` carries both:
`provisioned_used_bytes` and `used_bytes`.)

`L=` on the line of a storage is `L_s`, the sum of `ℓ` over every disk on that
storage now. `u=` is `u_s = L_s / capability_weight`, the *utilization*. The tool
balances this utilization across storages. A storage with half the
`capability_weight` of another storage is thus expected to carry half the load,
not the same absolute amount.

`ℓ` after the size and format of a disk is the load of that disk. The unit is
**average in-flight I/O requests**. By default, `ℓ` is
`rate(rd_total_time_ns + wr_total_time_ns) / 1e9` for the disk: the average number
of read and write requests in progress on the device at the same time. This value
weights requests by their cost. An 8 ms write and a 1 ms read correctly count
eight to one. A plain IOPS count would count them as equal operations.
`load_weights.read_factor`/`write_factor` can weight reads and writes differently.
You can also blend `ops` and `bytes` terms in with I/O time. See
`IMPLEMENTATION_PLAN.md` section 4 for the full normalization, and
`docs/internals/70-loadmodel.md` for the code. The worked numbers above are the
example of `IMPLEMENTATION_PLAN.md` section 14 (`config/drs.example.yaml` ships the
same group and weights). They are not invented for this page.

**Under `forecast.model: holt_winters` these are not the measured numbers.** The
default `quantile` model reports the load observed over the last
`window.lookback`. With `holt_winters`, the tool scales the `ℓ` of each disk to a
forecast of its p95 over the *next* `window.lookback`. The tool computes `L=`/`u=`,
the spread and the `ACT`/`NO ACTION` verdict from those scaled values. The balancer
acts on these loads. `show-load` says so on a line directly under the group header.
`explain` prints the same line:

```
Group fc-tier1 → NO ACTION: imbalance 12.2% is below gates.imbalance_threshold (20.0%)
  forecast: holt_winters used (backtest error 0.08 vs baseline 0.14): 37 disks scaled to their forecast p95, 5 kept as observed
```

The forecast can lose its backtest, or the history can be too short to run one.
The group then falls back to the observed loads, and the line reads `forecast:
holt_winters not used -- ...; loads are as observed`. With no `forecast:` line at
all, you have configured the `quantile` model, or the tool could not fetch the
forecast history in this run. In the second case, the tool logs a warning and the
numbers are the observed ones. See [`explain`](29-explain.md) for the fields. See
`forecast.model` in the configuration reference for the rule of the backtest.

## The `Group <name> → ACT`/`NO ACTION` line

The tool evaluates four gates in this order: **reserve override**, then the
**capacity gate**, then **drift**, then **imbalance**. The first gate that decides
wins. The header line above shows the reserve override. The shortfall of 0.5 TiB
on san-a forces `ACT`, however balanced or drifted the group is, because "safety is
not subject to hysteresis" (section 13). On a group with no reserve violation, the
line can take these other shapes:

```
Group fc-tier1 → ACT: imbalance 255.4% meets or exceeds gates.imbalance_threshold (20.0%)
Group fc-tier1 → NO ACTION: imbalance 12.2% is below gates.imbalance_threshold (20.0%)
```

The **capacity gate** is the data-spread counterpart of the imbalance gate. It does
not compare I/O load across the storages of a group. It compares how *full* each
storage is, as a fraction of its own capacity. The gate fires when the spread of the
fill fraction across the storages is at least `gates.capacity_spread_threshold`
(default `0.25`), relative to the mean fill of the group. Like the reserve override,
it then bypasses drift and imbalance. The reason is that a quiet workload is no
reason to leave data lopsided across storages:

```
Group fc-tier1 → ACT: capacity spread 32.0% meets or exceeds gates.capacity_spread_threshold (25.0%) -- acting now regardless of I/O drift/imbalance
```

The other three gates differ in one way: this gate can act on a group whose I/O is
already perfectly balanced. Once the solver runs,
`objective.delta_capacity_spread`, a price per TiB, does the actual spreading.
`gates.capacity_spread_threshold: null` disables the gate. The gate never fires on
a group with no data at all (mean fill `0`).

`show-load` reads the load vector that `state.path` records (section 11.2) and
passes it to the drift gate. Once a group has such a record, the line can also read:

```
Group fc-tier1 → NO ACTION: drift 3.1% is below gates.drift_threshold (10.0%)
```

A group with no `state.json`, or with no record in it yet, evaluates as if this
were the first run. The tool skips the drift gate. It does not treat the drift as
zero (the degenerate-case rule of section 6). The verdict thus comes from the
reserve override, the capacity gate (which never depends on `state.json`) or an
imbalance check. `docs/internals/80-gates.md` and `docs/internals/15-state.md` have
the details. `apply` writes `last_balance` after a run that executes at least one
move (`confirm` or `auto` mode). `dry-run` only simulates, so it never writes the
record. The first-run behaviour is therefore only common for a group before its
first successful migration. After that migration, the drift line of `show-load`
shows real history.

A pinned disk carries `[pinned: <reason>]` after its size and format. The reasons
are:

- `snapshots present (N)`
- `pending config change (unapplied)`
- `pending deletion (unapplied)`
- `locked: <lock>`
- `excluded by config`
- `excluded: unused disk (exclude.include_unused_disks=false)`
- `small disk with no larger disk of its VM in this group
  (migration.tiny_disk_bytes)`: an EFI/TPM disk whose VM has all its other disks
  in a different group. Such a disk only ever moves with a larger disk of its VM.
- `cooldown: moved recently, <time> left on gates.cooldown_per_disk`: `state.json`
  records a move of this disk within `gates.cooldown_per_disk`.

These reasons match `IMPLEMENTATION_PLAN.md` section 5.3 (C2) exactly. The reason
answers the question "why won't it move this disk". The two `pending` reasons
(section 3.8) mean that PVE has queued an edit or a deletion for that disk key. The
change is not yet in effect, usually because it waits for a VM reboot. Apply or
revert the change in the PVE UI. Then run the command again.

A disk whose measured I/O falls below `window.min_coverage` (section 3.4) gets its
own `⚠ <disk> : <reason>` line, right after the disks of its group. Without this
line, `ℓ` would be wrong without any message. The disk shows either the last known
load that `state.json` records (see `docs/internals/70-loadmodel.md`), or `0.0`
when `state.json` has no entry for it. In both cases, the warning says which of the
two applies. The tool never flags `tpmstate0` and `unusedN` disks this way. These
disks emit no I/O metrics, so `ℓ 0.00` is correct for them, not a gap.

A group with no measured I/O at all gets one `(idle: no measured I/O for this group
this window)` line instead of the warnings per disk. One exception exists. If all six
queries return zero series (not just series with a real rate of zero), the line
reads `⚠ the resolved query filter matched no series at all` instead. That is a
scoping problem (`metrics.labels.node`, or `extra_selector`), not an idle cluster.
Look next at the sample-series labels of `verify-metrics`
(`docs/manual/20-verifying-metrics.md`) (REVIEW.md W-06/W-07).

**A Prometheus outage does not fail this command.** Sizes and reserve status never
depend on Prometheus. If the load fetch of a group fails, the storage and disk lines
of that group omit `L=`/`u=`/`ℓ`. A `⚠ per-disk load unavailable: <reason>` line
explains why. If you see this line, check `verify-metrics` first.

A **`Warnings:`** block, when present, lists things that deserve a look but are not
fatal. One example is a disk on a storage that no configured group contains
("ungrouped, not managed"). Check whether that storage belongs in a group. Another
example is a disk whose size came from its own config instead of the authoritative
content listing of the storage. This usually means that the volume no longer exists
on the storage. The most common cause is that someone removed it directly on the
storage backend instead of through Proxmox. That leaves a dangling reference. PVE
neither cleans it up nor notices it (a VM starts fine with such a reference; see
`IMPLEMENTATION_PLAN.md` section 3.6 for a confirmed case). If you see this
warning, check whether the named volume still exists on the storage. If it does not
exist, remove the stale reference (`qm unlink <vmid> <device>` for an `unusedN`
entry).

`--json` shows the same information as one object. It has these parts:

- `groups[].storages[]` includes the exact byte counts behind the reserve check:
  `largest_footprint_bytes`/`largest_footprint_vmid`, the largest VM footprint on
  the storage and the VM it belongs to. When available, it also includes `load` and
  `utilization`.
- `groups[].disks[]` includes, when available, `load` and `load_flagged_reason`.
- Each group carries its own `load_computed`, `idle`, `load_error` and `gate`
  fields. Under `holt_winters` only, when the loads are forecast-scaled, it also
  carries a `forecast` object: `model`, `used`, `backtest_error`, `baseline_error`,
  `disks_scaled`, `disks_kept`. A Prometheus outage on one group never stops another
  group from reporting `load_computed: true` or `gate`.
- `gate` is `null` when `load_computed` is `false`, because there is then no
  `GroupLoad` to evaluate gates against. Otherwise it is an object with `act`
  (bool), `reason` (string, identical to the text of the human line after the arrow)
  and `reserve_override` (bool).
- The `gate` object also has `drift_fraction`/`imbalance_fraction`/
  `capacity_fraction` (float or `null`). `null` means that the tool never reached
  the gate, not that the gate evaluated to zero. `capacity_fraction` is the ratio of
  the capacity gate described above. It is `null` whenever
  `gates.capacity_spread_threshold` is unset or the mean fill of the group is 0, the
  same two cases in which the gate never fires.
- The `gate` object also has `split_vmid`: the id of the large VM that opened the
  group through the split gate (see `snapshot_reserve.split_vm_footprint`), or
  `null`.

**A config with several groups issues Prometheus queries per group.** The load of
one group takes seven queries: six raw metrics plus one coverage check. Each query
covers only the VMs of that group. A config with `N` groups therefore sends `7N`
queries on every `show-load`, not 7, because each group makes its own coverage and
data-quality decisions. The groups thus cannot share a fetch. A typical deployment
with one to three groups sends a handful of fast instant queries, which is no
concern. An operator who runs many groups against an already busy Prometheus must
know about this multiplier. Each query aggregates only the VMs that the group
actually has, split into batches of `metrics.VMID_QUERY_BATCH_SIZE` VMs for a very
large single group. It does not aggregate every VM of the cluster. An earlier
version of this tool aggregated the whole cluster in each of those `7N` queries.
On a cluster with hundreds of VMs, Prometheus itself could then time out the query
instead of just answering slowly.

## `verify-storages`

For a storage that sets `enforce_format`, the command also prints that value and the
entry it came from. It also prints the number of disks on the storage that have a
different format, and their total size. That is not an error. It only shows how far
the storage is from its policy, because the tool applies the format only to moves
and never moves a disk for this reason alone. The `--json` form carries the same
information as `enforce_format`, `enforce_format_source`, `nonconforming_disks` and
`nonconforming_bytes`. It also carries `largest_footprint_bytes` and
`largest_footprint_vmid` beside `largest_disk_bytes`. The first two give the figure
from which the tool computes the snapshot reserve, and the VM it belongs to.
`largest_disk_bytes` is the figure per volume from which the tool estimates the wipe
time.

For each storage, the command reports:

- the resolved `free_space.soft`/`.hard` bytes, each with the level it came from
  (`IMPLEMENTATION_PLAN.md` section 5.3.1). An operator cannot predict this
  derivation otherwise, once inheritance, `/…/` patterns and percentages all play a
  part;
- the largest VM footprint on the storage, with the VM it belongs to (the tool
  computes the snapshot reserve from it);
- `saferemove`, and the wipe time it implies for the largest *disk* on the storage
  (a wipe is per volume).

The command warns when your configured cooldown or move-duration limit is shorter
than that implied wipe time. `IMPLEMENTATION_PLAN.md` section 9.3 describes this
condition as "the next run plans onto a storage that is still draining". The
fixture of section 14 has `saferemove` off on every storage (stated explicitly
there, so that its payback arithmetic is reproducible). To show the warning, this
example instead assumes an LVM `san-b` with `saferemove` on, at PVE's default
throughput of 10 MiB/s:

```
$ pve-storage-drs -c /etc/pve/drs.yaml verify-storages
Group fc-tier1
  san-a  saferemove=off
    largest VM footprint (Z_s): 3.00 TiB = web01(101)
    free_space: soft=0 B (global)  hard=0 B (= soft (no dip))
    saferemove is off or throughput unknown; no wipe-time check
  san-b  saferemove=on
    largest VM footprint (Z_s): 1.00 TiB = app01(104)
    free_space: soft=0 B (global)  hard=0 B (= soft (no dip))
    implied wipe time for the largest disk (1.00 TiB): 1.2d
    ⚠ gates.cooldown_per_storage (1.0h) is shorter than the implied wipe time -- the next run may plan onto a still-draining storage
    ⚠ migration.max_single_move_duration (6.0h) is shorter than the implied wipe time -- a move of the largest disk would be rejected outright
  san-c  saferemove=off
    largest VM footprint (Z_s): 512.00 GiB = cache01(105)
    free_space: soft=0 B (global)  hard=0 B (= soft (no dip))
    saferemove is off or throughput unknown; no wipe-time check
```

`free_space.soft`/`.hard` show `0 B` here because the fixture sets no `free_space`
key at all. That is the default from before section 5.3.1, unchanged. A config with
a non-zero `free_space.soft` shows the resolved byte count here. `plan`, `explain`
and `show-load` all enforce the same value.

The parenthesis after each value shows where the value came from. You cannot read
this from the config file when one line can mean a different number for each LUN:

| Shown | Meaning |
|---|---|
| `global` | inherited from the top-level `free_space` block |
| `storage entry` | written on this storage's own `groups[].storages[]` entry |
| `pattern /re/` | supplied by the `/…/` pattern entry that matched this storage |
| `…, 10% of 30.00 TiB` | appended when the value was a percentage: the capacity it was converted against |
| `= soft (no dip)` | (hard only) `hard` is null, so it equals the resolved soft |

`--json` carries the same strings as `free_space_soft_source` and
`free_space_hard_source` beside the two byte counts.

Storage types without `saferemove` at all (Ceph RBD, ZFS) always report
`saferemove=off`. The tool skips the check, because there is nothing to wipe.

### A negative `saferemove_throughput` is normal

If your `storage.cfg` reads

```
saferemove_throughput -1073741824
```

the value means **1 GiB/s**. It is neither an error nor a negative rate. PVE passes
the value unchanged to `cstream -t`. The sign selects how `cstream` enforces the
limit, and the magnitude is the rate:

- **positive**: a session average. The wipe may exceed the rate for a while to make
  up for earlier underuse, so that the whole run converges on the rate.
- **negative**: an upper limit on each individual read/write, never exceeded.

`verify-storages` reports the implied wipe time from the magnitude. `-1073741824`
and `1073741824` therefore give the same duration. The
`saferemove_throughput_bytes_per_sec` field of the `--json` output still echoes the
value exactly as PVE has it, with its sign, so that you can compare it with
`storage.cfg` without arithmetic. Everything that uses the number reads it the same
way: the migration cost that the payback test charges, the
`migration.max_single_move_duration` check and the source-release wait of `apply`.

Versions up to 0.1.6 divided by the signed value instead. This produced a *negative*
wipe time (`implied wipe time for the largest disk (1.00 TiB): -17.1m`). If you run
one of those versions, the two warnings above can never fire on a storage configured
this way. It is also natural to configure `|saferemove_throughput|` equal to
`migration.bwlimit_bytes_per_sec`. In that case, the total duration of every move was
exactly zero, so the tool did not enforce `migration.max_single_move_duration` at
all. An upgrade is the fix. You need no configuration change.

If any `groups[].storages[].id` is a `/regex/` pattern (`IMPLEMENTATION_PLAN.md`
section 11.4), `verify-storages` also prints what each pattern matched in this run.
It lists every cluster storage that no group matched. This is the same "ungrouped,
not managed" view that `show-load` gives per disk, but at the level of storages,
whether or not a disk is on the storage now:

```
Pattern expansions:
  [fc-tier1] /san-.*/ → san-a, san-b, san-c

Cluster storages matched by no group:
  - local-only
```

A pattern that is too broad, or that matches nothing, is the one new way to
misconfigure a group that this feature adds. The tool therefore never applies an
expansion without a record: every run also logs the expansion at INFO, whichever
command you run.
