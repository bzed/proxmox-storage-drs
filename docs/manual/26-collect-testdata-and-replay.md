# Diagnostic bundles: `collect-testdata` and `--replay`

`IMPLEMENTATION_PLAN.md` section 16 is the specification; this page is the
operational side of it. Two facts motivate the whole feature: one cluster is
not a test corpus (every interesting bug so far was found by an operator
running the tool on a cluster the author has never seen, then *describing*
what they saw), and the data cannot leave the cluster as-is (a PVE inventory
is customer names, hostnames, IQNs, ticket numbers and credentials).

## `collect-testdata`: capturing a bundle

```sh
pve-storage-drs -c /etc/pve/drs.yaml collect-testdata
```

This is **read-only and dry-run-only** by construction: it never issues
`move_disk`, and `--mode confirm`/`--mode auto` alongside it is a usage
error (exit `2`), not a silently ignored flag. It captures the *superset* of
what any supported configuration could need — every raw metric over the
union of every forecaster's own history requirement, not just the one
`forecast.model` you have configured — so a bundle captured today can still
reproduce a Holt-Winters misfit tomorrow.

Before fetching anything, it estimates the size of the capture from the
topology it has already read:

```sh
pve-storage-drs -c /etc/pve/drs.yaml collect-testdata --estimate
```

```
groups: 2   disks: 47
range: 7d  step: 5m
estimated Prometheus queries: 42
estimated series sample points: 573104
```

Above `support.max_series_points` (default 5,000,000) the real capture
refuses outright, naming the flags that bring it under the limit:

| Option | Effect |
|---|---|
| `-o`, `--output DIR` | Where the bundle directory and its `.tar.gz` are written (default `support.bundle_dir`). |
| `--estimate` | Print the estimate above and exit; fetches nothing. |
| `--range DURATION` | Override the series capture range (default `support.capture_range`). |
| `--step DURATION` | Override the series resolution (default `metrics.step`). |
| `--no-series` | Topology, instant queries and findings only — no per-disk time series, so the bundle cannot exercise a seasonal forecaster, but is much smaller. |
| `--no-archive` | Write the directory only, skip the `.tar.gz`. |
| `--salt-file PATH` | Use a different anonymization salt (default `support.salt_path`). |
| `--new-salt` | Generate a fresh salt first. Logged at warning level: bundles made before and after no longer share a pseudonym mapping. |

Exit status is `0` when every capture step succeeded, `1` when the bundle
was still written but the manifest records one or more failed calls (a
`Datastore.Allocate`-shaped permission gap looks exactly like this — see
`00-installation.md`), `2` on a usage error.

### What is in a bundle, and what is not

A bundle is a directory (`manifest.json`, `config.yaml`, `findings.json`,
`pve/`, `prometheus/`, `SHA256SUMS`) plus a deterministic `.tar.gz` of it.
**Read it before sending it anywhere** — it is plain, sorted, indented JSON,
meant to be opened in an editor:

- **No direct identifier and no secret.** `config.yaml` never carries
  `proxmox.host`/`auth`, `prometheus.url`, or any other credential or
  endpoint — they are dropped, not blanked. Every node name, storage id,
  vmid, volume id, tag, pool and UPID is replaced by a pseudonym keyed to a
  salt (`support.salt_path`) that is generated locally, never written into
  the bundle, and never leaves the host. Free text — VM names, descriptions,
  snapshot names, storage comments — is dropped outright. Device keys
  (`scsi0`, `efidisk0`, ...) are not identifiers and are kept as-is, since
  the movability rules read them directly.
- **The mapping is stable per salt**, so a second bundle from the same host
  names the same objects the same way — useful for comparing a before/after
  pair — until `--new-salt` rotates it.
- **Sizes, capacities, load shapes and the whole configuration (minus
  credentials) are preserved.** That is what makes a bundle a test case
  instead of a shape. It also means a bundle is **not anonymous against
  someone who already knows the cluster** — a cluster with three nodes, two
  8 TiB LUNs and 1,214 VMs is recognizable to anyone who has seen it.
  Submitting one to the project (see `tests/corpus/README.md`) is an
  informed decision, not a formality.

## `--replay`: running against a bundle offline

```sh
pve-storage-drs --replay ./drs-testdata-cluster-3f8a91c2 plan --json
```

`--replay PATH` is a **global** option, accepted before any subcommand, and
substitutes both the PVE and Prometheus clients at the one place each is
constructed — so `verify-metrics`, `verify-storages`, `show-load`, `plan`
and `explain` all run **unchanged**, with **no network access at all**.

- The configuration is the bundle's own `config.yaml`, unless `-c` is also
  given — that is how you run the operator's cluster through a solver
  backend, a `spread_metric`, or a forecaster they never selected
  themselves.
- **`apply` is refused**, and so is any `--mode` above `dry-run` — exit `2`
  either way. A replay can never issue a write.
- A query the bundle has no recorded response for is a **loud, specific
  error** naming the query and the range it asked for — never a silent
  empty result standing in for "no data":

  ```
  pve-storage-drs: bundle has no recorded response for the range query
  'sum by (vmid, instance) (rate(blockstat_rd_operations{...}[300s]))'
  over [1700000000,1700086400] -- captured range was [1699400000,1700000000]
  ```

  This is the failure mode to expect if you hand-edit a bundle's
  `config.yaml` to a `window.lookback`/`metrics.step` combination the
  capture never anticipated, or if `--step` was overridden at capture time
  to something a replayed forecaster does not expect.
- `state.json` is read from the bundle if present, and never written —
  a replay never touches the host's real state.

Run `--replay` against your own bundle before sending it anywhere: "does
`plan` against this bundle show the problem I am reporting?" is exactly the
question it answers, and it is also how the author verifies a submitted
bundle reproduces what its `tests/corpus/*.submission.yaml` claims.

## See also

`tests/corpus/README.md` in the source tree: how a bundle becomes part of
the project's own test suite, the scrub audit it goes through, and the
consent terms for submitting one.
