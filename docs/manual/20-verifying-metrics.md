# Verifying your setup

Run this command before you rely on any plan. Telegraf and InfluxDB naming
differs between deployments. `pve-storage-drs` therefore never assumes that the
defaults in [`10-configuration.md`](10-configuration.md) are correct for your
cluster. `verify-metrics` checks them against the live Prometheus.

The command also checks something that the names alone cannot tell you: whether
all six counters survived the transport. See
[`05-metrics-pipeline.md`](05-metrics-pipeline.md) for the reasons a counter can
get lost, and why that produces a wrong plan instead of an error.

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

The exit status is `0` when every check passes. It is `1` when any check reports
a finding of level `error` (see below). `--json` shows the same information as one
JSON object instead. See [`30-safety-and-status.md`](30-safety-and-status.md) for
exit codes in general.

## What each finding means

`verify-metrics` runs six checks, in this order (`IMPLEMENTATION_PLAN.md`
section 3.3):

1. **Metric names exist.** The command looks up each of `metrics.read_ops`,
   `write_ops`, `read_bytes`, `write_bytes`, `read_time_ns` and `write_time_ns`
   in Prometheus's own `/api/v1/label/__name__/values`. A missing name is an
   **error**. Correct the name in the `metrics.*` section of
   `10-configuration.md` so that it matches what your Telegraf actually sends.
2. **Sample series and labels.** The command sends one instant query per metric.
   It prints the full label set of the result. You can then see at a glance whether
   `metrics.labels.vmid`, `.device` and `.node` are present and not empty on a
   live series. A metric that exists but has no series now is a **warning**, not an
   error. It may only mean that nothing produced that kind of I/O recently. This
   step also compares the full `(vmid, device)` set of each of the six metrics with
   the sets of the other five. It costs your Prometheus nothing extra, because it
   reuses these six instant queries. If one metric misses a disk that the other
   five report, the command gives a **warning**. The warning names the metric and
   the disk. The usual cause is that Telegraf's Prometheus-compatible output drops
   a field as soon as it sees a non-numeric value for it. InfluxDB's line protocol
   fixes the type of a field at its first write, and Prometheus/OpenMetrics has no
   string sample type. The drop is independent of the other five fields of the same
   disk. This is exactly why check 5 below cannot catch a drop of a *different*
   field on its own: check 5 looks only at `read_ops`.
3. **Configured labels present.** `metrics.labels.vmid`/`.device`/`.node` may be
   missing or empty on the sample series. That is an **error**, because the load
   model then has nothing to join disks on.
4. **The `instance` collision.** If `metrics.labels.device` is still the literal
   string `instance`, the command gives a **warning**. PVE's own per-disk tag has
   this name. It collides with the unrelated scrape-target `instance` label of
   Prometheus. Many Telegraf configurations rename or overwrite one of the two.
   Confirm which one survived before you trust the label.
5. **Per-disk coverage.** The command takes every `(vmid, device)` pair that
   appears on `metrics.read_ops`. For each pair, it measures the fraction of the
   expected samples that are present over `window.lookback`. A fraction below
   `window.min_coverage` gives a **warning** that names the disk. At plan time, the
   load model rejects the data of that disk and uses its last known load from
   `state.json` instead.
6. **Observed sample spacing.** The command measures the real gap between samples.
   It counts the raw samples over a 10-minute window with `count_over_time()` and
   takes the median across series. It does not trust
   `metrics.pvestatd_push_interval`. A difference of more than 20% is an
   **error**. A `metrics.rate_window` below four times the observed spacing is also
   an **error**. This check stops an outdated `pvestatd_push_interval` from
   breaking the `rate()` window that the setting protects, without any message.

## If it fails

- **A metric does not exist**: check the configuration of your Telegraf
  `influxdb_listener` (or the equivalent) for the actual measurement and field
  names that it produces. Update `metrics.*` to match.
- **A label is missing or empty**: the sample series that check 2 prints is the
  fastest way to see which labels Prometheus actually has for that series. Update
  `metrics.labels.*` to name the real labels.
- **One metric is missing disks the others report**: a transport dropped a field.
  Check your Telegraf configuration, and the PVE-side field that it collects.
  Look for a non-numeric value of that field for that disk at some time. One such
  value is enough: Telegraf then drops the field of that series permanently, while
  every other field of the same disk continues to work. This is a real defect in
  the pipeline, not noise, and it does not repair itself.
  [`05-metrics-pipeline.md`](05-metrics-pipeline.md) explains the mechanism, the
  output plugins that are prone to it, and the setup with gigapipe on ClickHouse
  that avoids the format bridge entirely.
- **Coverage is low for specific disks**: check that Telegraf scrapes every node.
  Check that `window.lookback` is not longer than your Prometheus retention.
- **Spacing disagrees**: measure the real push interval of `pvestatd` on a node.
  Use its systemd timer, or the interval in `/etc/pve/status.cfg` if you set it
  there. Then correct `metrics.pvestatd_push_interval`.
