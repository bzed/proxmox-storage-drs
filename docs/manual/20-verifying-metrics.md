# Verifying your setup

Run this before relying on any plan. Telegraf and InfluxDB naming varies by
deployment, so `pve-storage-drs` never assumes the defaults in
[`10-configuration.md`](10-configuration.md) are correct for your cluster —
`verify-metrics` is what checks them against the live Prometheus instead.

## Running it

```sh
pve-storage-drs -c /etc/pve/drs.yaml verify-metrics
```

A successful run looks like this (labels and values are illustrative):

```
[   info] metrics.read_ops = 'blockstat_rd_operations' exists
[   info] metrics.write_ops = 'blockstat_wr_operations' exists
[   info] metrics.read_bytes = 'blockstat_rd_bytes' exists
[   info] metrics.write_bytes = 'blockstat_wr_bytes' exists
[   info] metrics.read_time_ns = 'blockstat_rd_total_time_ns' exists
[   info] metrics.write_time_ns = 'blockstat_wr_total_time_ns' exists
[   info] blockstat_rd_operations: sample series labels {'vmid': '101', 'instance': 'scsi0', 'nodename': 'pve01', 'cluster': 'pvezebe'}
...
[   info] 'cluster' label values seen across these metrics: pvezebe
...

OK: verify-metrics found no blocking problems
```

Exit status is `0` when every check passes, `1` when any check reports an
`error`-level finding (see below). `--json` emits the same information as one
JSON object instead — see [`30-safety-and-status.md`](30-safety-and-status.md)
for exit codes in general.

## What each finding means

`verify-metrics` runs six checks, in this order (`IMPLEMENTATION_PLAN.md`
section 3.3):

1. **Metric names exist.** Each of `metrics.read_ops`, `write_ops`,
   `read_bytes`, `write_bytes`, `read_time_ns` and `write_time_ns` is looked
   up against Prometheus's own `/api/v1/label/__name__/values`. A missing
   name is an **error** — fix the name in `10-configuration.md`'s `metrics.*`
   section to match what your Telegraf actually emits.
2. **Sample series and labels.** One instant query per metric, printing its
   full label set so you can see at a glance whether `metrics.labels.vmid`,
   `.device` and `.node` are really present and non-empty on a live series.
   A metric that exists but currently has no series is a **warning**, not an
   error — it may simply mean nothing has generated that kind of I/O
   recently.
3. **Configured labels present.** If `metrics.labels.vmid`/`.device`/`.node`
   do not appear (or are empty) on the sample series, that is an **error**:
   the load model has nothing to join disks on.
4. **The `instance` collision.** If `metrics.labels.device` is still the
   literal string `instance`, a **warning** — PVE's own per-disk tag has this
   name and it collides with Prometheus's unrelated scrape-target `instance`
   label. Many Telegraf configurations rename or overwrite one of the two;
   confirm which one survived before trusting this.
5. **Per-disk coverage.** For every `(vmid, device)` pair seen on
   `metrics.read_ops`, the fraction of expected samples actually present over
   `window.lookback` is measured. Below `window.min_coverage`, a **warning**
   naming the disk — that disk's own data will be rejected by the load model
   at plan time and its last known load from `state.json` used instead.
6. **Observed sample spacing.** The modal gap between consecutive samples of
   a live series is measured directly, rather than trusted from
   `metrics.pvestatd_push_interval`. Disagreeing by more than 20%, or
   `metrics.rate_window` being below four times what was actually observed,
   is an **error** — this is what stops a stale `pvestatd_push_interval`
   declaration from silently breaking the `rate()` window it is supposed to
   protect.

## If it fails

- **A metric does not exist**: check your Telegraf `influxdb_listener` (or
  equivalent) configuration for the actual measurement/field names it is
  producing, and update `metrics.*` to match.
- **A label is missing or empty**: the sample series printed by check 2 is
  the fastest way to see what labels Prometheus actually has for that
  series — update `metrics.labels.*` to name the real ones.
- **Coverage is low for specific disks**: check that Telegraf is actually
  scraping every node, and that `window.lookback` is not longer than your
  Prometheus retention.
- **Spacing disagrees**: measure `pvestatd`'s real push interval on a node
  (its systemd timer, or the interval visible in `/etc/pve/status.cfg` if
  set there) and correct `metrics.pvestatd_push_interval`.
