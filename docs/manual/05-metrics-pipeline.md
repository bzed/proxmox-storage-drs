# Where the numbers come from, and how a transport loses them

`pve-storage-drs` collects nothing itself. It ships no exporter, installs no
agent on your nodes and opens no connection to a VM. Every number in every
plan comes out of a Prometheus-compatible backend you already run, via a
pipeline PVE already has.

Read this page before you write the `metrics` block in
[`10-configuration.md`](10-configuration.md). The pipeline is where this
tool's inputs get quietly damaged, and a damaged input produces a confident
plan rather than an error.

## The six counters

Per VM disk, per push:

```
rd_operations   wr_operations         how many I/Os
rd_bytes        wr_bytes              how much data
rd_total_time_ns  wr_total_time_ns    how long the device was busy
```

They are QEMU's own `query-blockstats` figures. `pvestatd` already gathers
them on every status push — it calls `vmstatus(undef, 1)`, and the `full`
flag is what makes it issue the QMP query — and PVE's **InfluxDB external
metric server** already exports the whole stats hash without filtering.

`PVE/Status/InfluxDB.pm` flattens that nested hash so the first level
becomes the measurement (`blockstat`), the second becomes a **tag**
(`instance=scsi0`), and the leaves become fields. A series therefore arrives
looking roughly like:

```
blockstat_rd_operations{vmid="101", instance="scsi0", nodename="pve01", host="db-01"}
```

The device id being a **label** rather than part of the metric name is the
whole reason this approach works: it is what makes per-disk `rate()` and
aggregation across drives possible at all.

Note the label names in that example. PVE's own tag for the drive id is
`instance`, which **collides with Prometheus's own scrape-target label of
the same name**, and many Telegraf configurations rename or overwrite one of
the two. That is why the tool never hardcodes them: `metrics.labels.vmid`,
`.device` and `.node` are configuration keys naming whatever labels your
deployment actually produces, defaulting to `vmid`, `instance` and
`nodename`. `verify-metrics` warns when `.device` is still `instance` — not
because that is wrong, but because it is the one name where you have to
confirm which of the two survived before anything joins on it.

So the data exists cluster-wide before this tool is installed, and there is
nothing new to deploy. `IMPLEMENTATION_PLAN.md` §3.1 carries the source
excerpts if you want to confirm any of the above against `pve-manager` and
`qemu-server` yourself.

### Two things deliberately not used

- **RRD.** `GET /nodes/{node}/qemu/{vmid}/rrddata` exposes only VM-aggregate
  `diskread`/`diskwrite` in bytes per second — no per-disk breakdown, no
  operation counts, no latency. It cannot answer the question this tool
  asks.
- **The OpenTelemetry metric server** (new in PVE 9.1), despite being the
  more modern-looking option. It appends a nested key to the metric *name*
  rather than carrying it as an attribute, so `blockstat.scsi0.rd_operations`
  becomes `proxmox_vm_blockstat_scsi0_rd_operations_total`. The device is
  baked into the name, which makes aggregation across devices impossible
  without `label_replace` gymnastics and makes metric-name cardinality
  unbounded. The InfluxDB path is strictly better here.

## The failure mode: a transport that cannot carry strings

This is the most common way to get a wrong answer out of `pve-storage-drs`,
and it never announces itself.

PVE's InfluxDB output speaks **InfluxDB line protocol**, which carries
**string** fields alongside numeric ones. Two properties of that protocol
combine badly with a Prometheus-shaped destination:

1. **A field's type is fixed by its first write.** Once a given series'
   field has arrived as a string, it is a string for that series from then
   on — permanently, not until the next push corrects it.
2. **Prometheus and OpenMetrics have no string sample type.** A sink that
   cannot represent a string field does the only thing available to it: it
   drops the field.

Put together: one non-numeric value, once, possibly months ago, for one
disk, is enough to make one of the six counters vanish for that series while
the other five keep working perfectly. Nothing logs an error. Your
dashboards keep drawing, because they rarely plot all six.

What `pve-storage-drs` then sees is a disk that does no writes, or a disk
whose device was never busy. The load model has no way to tell that apart
from a genuinely idle disk — the data does not say "missing", it says
nothing at all — so it plans around a number that is simply false.

### Telegraf with a Prometheus remote-write output

This is the prominent example, and it is prominent because it is what most
people build first:

```
inputs.influxdb_listener  →  (no processors)  →  outputs.prometheus_remote_write
```

`outputs.prometheus_client` and any other OpenMetrics-shaped output behave
the same way, as does any other bridge from PVE's InfluxDB output into a
Prometheus data model. **Unless the pipeline is configured deliberately** — converting
the string fields, or dropping them explicitly with a processor so you know
what you lost — it will silently discard fields, and you will find out from
a plan that does not make sense rather than from a log line.

This is not an argument against Telegraf. It is an argument for configuring
its processors on purpose, and for running
[`verify-metrics`](20-verifying-metrics.md) afterwards rather than assuming.

### What catches it

`verify-metrics` cross-checks the full `(vmid, device)` set that each of the
six metrics reports against the other five, and warns — naming the metric
and the disk — whenever one metric's set is a strict subset of another's.
This costs your Prometheus nothing extra: it reuses the six instant queries
that step of `verify-metrics` was already making in order to print a sample
series.

Treat that warning as a real defect in the pipeline, not as noise. Fixing
the pipeline does not retroactively restore the samples you never received,
and by point 1 above it does not necessarily restore future ones either: as
long as the affected series keeps arriving under the same identity with the
field pinned to a string type, it stays dropped. Re-check with
`verify-metrics` after any change rather than assuming.

## A reference implementation that is well tested

**[gigapipe](https://github.com/metrico/gigapipe) with ClickHouse as the
database**, fed directly from PVE's InfluxDB output.

gigapipe accepts **the InfluxDB protocol exactly as PVE exports it** on the
ingest side, and serves the Prometheus HTTP query API — `/api/v1/query`,
`/api/v1/query_range`, `/api/v1/label/<name>/values`, which is the entire
surface this tool uses — on the read side. So PVE's own metric server writes
to it directly and `pve-storage-drs` reads from it directly: there is no
Telegraf, no output plugin and no format bridge anywhere in the path, and so
nothing that can drop a field on type grounds.

It is the backend this project is dogfooded against. Both bundles in
`tests/corpus/` were captured from a cluster running it and record it as
their `prometheus_backend`, so the regression suite runs against real
gigapipe-shaped data on every `make check`.

To use it, point `prometheus.url` at gigapipe's query endpoint. Nothing else
in this manual changes.

gigapipe also ingests OpenTelemetry, but **that path is untested here** and
is not the way to use it with this tool. Feeding it from PVE's OpenTelemetry
metric server instead of the InfluxDB one would reintroduce the
device-in-the-metric-name problem described above, whatever the backend does
with it afterwards.

## Other backends

Plain **Prometheus** and **VictoriaMetrics** both work. Every query this
tool issues — `rate()`, `quantile_over_time`, subquery ranges, and
`/api/v1/label/__name__/values` — is supported by all three backends, and
`prometheus.url` is the only setting that distinguishes them.

Whatever you use, the pipeline in front of it is still yours to get right,
and `verify-metrics` is still the thing that tells you whether you did.

## What to do next

1. Work out which transport your cluster actually uses today. The PVE side
   is the external metric server — `/etc/pve/status.cfg`, which is what
   Datacenter → Metric Server writes; if there is no InfluxDB entry there,
   nothing described on this page is happening yet and that is the first
   thing to set up.

   Do **not** take an existing "VM disk I/O" dashboard as evidence that it
   is. Such a dashboard may be drawing PVE's RRD data, or series from
   `prometheus-pve-exporter`, neither of which carries per-disk `blockstat`
   at all. Query your backend for `blockstat_rd_operations` directly and
   look at whether the result carries a per-drive label.
2. Set the `metrics` block in `/etc/pve/drs.yaml` to match the names that
   transport produces — they are configuration, not constants, because
   Telegraf's measurement/field join character and tag renaming vary per
   deployment. [`10-configuration.md`](10-configuration.md) documents every
   key with its default.
3. Run [`verify-metrics`](20-verifying-metrics.md) and read every finding.
