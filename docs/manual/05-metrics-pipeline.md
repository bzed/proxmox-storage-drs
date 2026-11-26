# Where the numbers come from, and how a transport loses them

`pve-storage-drs` collects nothing itself. It ships no exporter. It installs no
agent on your nodes. It opens no connection to a VM. Every number in every plan
comes from a Prometheus-compatible backend that you already run. The data
reaches that backend through a pipeline that PVE already has.

Read this page before you write the `metrics` block in
[`10-configuration.md`](10-configuration.md). The pipeline can damage the inputs
of this tool without any message. A damaged input produces a confident plan, not
an error.

## The six counters

Per VM disk, per push:

```
rd_operations   wr_operations         how many I/Os
rd_bytes        wr_bytes              how much data
rd_total_time_ns  wr_total_time_ns    how long the device was busy
```

The counters are QEMU's own `query-blockstats` figures. `pvestatd` already
gathers them on every status push. It calls `vmstatus(undef, 1)`, and the `full`
flag makes it send the QMP query. PVE's **InfluxDB external metric server**
already exports the whole stats hash without any filter.

`PVE/Status/InfluxDB.pm` flattens that nested hash. The first level becomes the
measurement (`blockstat`). The second level becomes a **tag** (`instance=scsi0`).
The leaves become fields. A series therefore arrives looking roughly like:

```
blockstat_rd_operations{vmid="101", instance="scsi0", nodename="pve01", host="db-01"}
```

The device id is a **label**, not a part of the metric name. This is the whole
reason that the approach works. A label makes a per-disk `rate()` possible. It
also makes aggregation across drives possible.

Note the label names in that example. PVE's own tag for the drive id is
`instance`. That name **collides with Prometheus's own scrape-target label of the
same name**. Many Telegraf configurations rename or overwrite one of the two. For
this reason, the tool never hardcodes the names. `metrics.labels.vmid`,
`.device` and `.node` are configuration keys. Each key names the label that your
deployment actually produces. The defaults are `vmid`, `instance` and
`nodename`. `verify-metrics` warns when `.device` is still `instance`. That value
is not wrong. But with this one name, you have to confirm which of the two labels
survived before anything joins on it.

So the data exists cluster-wide before you install the tool, and you deploy
nothing new. If you want to check any of the statements above against
`pve-manager` and `qemu-server`, `IMPLEMENTATION_PLAN.md` §3.1 carries the source
excerpts.

### Two things deliberately not used

- **RRD.** `GET /nodes/{node}/qemu/{vmid}/rrddata` exposes only the VM aggregate
  of `diskread`/`diskwrite`, in bytes per second. It has no per-disk breakdown,
  no operation counts and no latency. It cannot answer the question that this
  tool asks.
- **The OpenTelemetry metric server** (new in PVE 9.1), although it looks more
  modern. It appends a nested key to the metric *name* instead of an attribute.
  `blockstat.scsi0.rd_operations` thus becomes
  `proxmox_vm_blockstat_scsi0_rd_operations_total`. The device is part of the
  name. Aggregation across devices is then not possible without complex
  `label_replace` rules. The number of metric names also has no bound. The
  InfluxDB path is strictly better here.

## The failure mode: a transport that cannot carry strings

This is the most common way to get a wrong answer from `pve-storage-drs`. No
message announces it.

PVE's InfluxDB output uses **InfluxDB line protocol**. That protocol carries
**string** fields beside numeric fields. Two of its properties combine badly with
a destination that has the shape of Prometheus:

1. **The first write fixes the type of a field.** A field of a given series can
   arrive as a string once. It is then a string for that series from then on. The
   change is permanent. The next push does not correct it.
2. **Prometheus and OpenMetrics have no string sample type.** A sink that cannot
   represent a string field can do only one thing: it drops the field.

Together, this has a serious effect. One non-numeric value for one disk is enough,
even one time, possibly months ago. One of the six counters then disappears for
that series. The other five counters continue to work. No component logs an
error. Your dashboards continue to draw, because they rarely plot all six
counters.

`pve-storage-drs` then sees a disk that does no writes, or a disk whose device is
never busy. The load model cannot tell that apart from an idle disk. The data
does not say "missing". It says nothing at all. The tool therefore plans around a
number that is false.

### Telegraf with a Prometheus remote-write output

This is the prominent example, because most people build it first:

```
inputs.influxdb_listener  →  (no processors)  →  outputs.prometheus_remote_write
```

`outputs.prometheus_client` and any other output with the shape of OpenMetrics
behave the same way. Any other bridge from PVE's InfluxDB output into a
Prometheus data model does too. **You must configure the pipeline on purpose.**
Convert the string fields, or drop them explicitly with a processor, so that you
know what you lose. Without that, the pipeline discards fields without any
message. You then learn of the loss from a plan that does not make sense, not
from a log line.

This is not an argument against Telegraf. It is an argument to configure its
processors on purpose. It is also an argument to run
[`verify-metrics`](20-verifying-metrics.md) afterwards instead of an assumption.

### What catches it

`verify-metrics` compares the full `(vmid, device)` set of each of the six metrics
with the sets of the other five. When the set of one metric is a strict subset of
the set of another, the command warns. The warning names the metric and the disk.
The check costs your Prometheus nothing extra. It reuses the six instant queries
that `verify-metrics` already sends to print a sample series.

Treat that warning as a real defect in the pipeline, not as noise. A repair of the
pipeline does not restore the samples that you never received. Because of point 1
above, it does not necessarily restore future samples either. The affected series
can continue to arrive with the same identity and with the field fixed to a string
type. The field then stays dropped. After any change, run `verify-metrics` again
instead of an assumption.

## A reference implementation that is well tested

**[gigapipe](https://github.com/metrico/gigapipe) with ClickHouse as the
database**, fed directly from PVE's InfluxDB output.

On the ingest side, gigapipe accepts **the InfluxDB protocol exactly as PVE
exports it**. On the read side, it serves the Prometheus HTTP query API:
`/api/v1/query`, `/api/v1/query_range` and `/api/v1/label/<name>/values`. This is
the entire API surface that this tool uses. PVE's own metric server thus writes to
gigapipe directly, and `pve-storage-drs` reads from it directly. The path has no
Telegraf, no output plugin and no format bridge. Nothing in the path can drop a
field because of its type.

The project runs the tool against this backend. Two of the three
bundles in `tests/corpus/` come from a cluster that runs it, and they record it
as their `prometheus_backend`. The third records `unverified`. The regression suite thus runs against real data of the
gigapipe shape on every `make check`.

To use gigapipe, point `prometheus.url` at its query endpoint. Nothing else
in this manual changes, including the defaults of `metrics.step` and
`metrics.rate_window`. A test against a live system found that a recently updated
gigapipe returns zero series for a range query whose step reaches the duration of
its `rate()` window. The default does exactly that. The tool works around the
problem on every backend, always. It does not ask you to change your
configuration for gigapipe. See `metrics.step` in
`docs/manual/10-configuration.md` for the effect of the workaround on the data
that the tool actually fetches.

gigapipe also ingests OpenTelemetry, but **that path is untested here**. Do not
use it with this tool. PVE's OpenTelemetry metric server has the problem described
above: the device is part of the metric name. If you feed gigapipe from that
server instead of the InfluxDB server, you get the problem back. This is true
whatever the backend does with the data afterwards.

## Other backends

Plain **Prometheus** and **VictoriaMetrics** both work. All three backends support
every query that this tool sends: `rate()`, `quantile_over_time`, subquery ranges
and `/api/v1/label/__name__/values`. `prometheus.url` is the only setting that
distinguishes them.

Whatever backend you use, you still have to build the pipeline in front of it
correctly. `verify-metrics` still tells you whether you did.

## What to do next

1. Find out which transport your cluster uses today. The PVE side is the external
   metric server. Its settings are in `/etc/pve/status.cfg`, the file that
   Datacenter → Metric Server writes. If that file has no InfluxDB entry, nothing
   on this page happens yet. Set up the entry first.

   Do **not** take an existing "VM disk I/O" dashboard as proof that the pipeline
   exists. Such a dashboard may draw PVE's RRD data, or series from
   `prometheus-pve-exporter`. Neither source carries per-disk `blockstat` data at
   all. Query your backend for `blockstat_rd_operations` directly. Check that the
   result carries a per-drive label.
2. Set the `metrics` block in `/etc/pve/drs.yaml` to match the names that your
   transport produces. The names are configuration, not constants, because the
   join character between measurement and field in Telegraf, and its tag renames,
   differ between deployments.
   [`10-configuration.md`](10-configuration.md) documents every key with its
   default.
3. Run [`verify-metrics`](20-verifying-metrics.md) and read every finding.
