# Diagnostic bundles: `collect-testdata` and `--replay`

`IMPLEMENTATION_PLAN.md` section 16 is the specification. This page is the
operational side. Two facts motivate the whole feature.
First, one cluster is not a test corpus. Every interesting bug so far was found
by an operator who ran the tool on a cluster the author has never seen. The
operator then *described* what they saw. Second, the data cannot leave the
cluster as-is. A PVE inventory is customer names, hostnames, IQNs, ticket numbers
and credentials.

## `collect-testdata`: capturing a bundle

```sh
pve-storage-drs -c /etc/pve/drs.yaml collect-testdata
```

The command is **read-only and dry-run-only**. It never issues `move_disk`.
Adding `--mode confirm`/`--mode auto` alongside it is a usage error (exit
`2`). The tool does not silently ignore the flag. The command captures the
*superset* of what any supported configuration could need. That is every
raw metric over the history that `holt_winters` needs, twice
`window.lookback` for its backtest. It is not just what the
`forecast.model` you have configured needs. A bundle captured today can
still reproduce a Holt-Winters misfit tomorrow.

`--estimate` sizes the capture first. It reads the full PVE inventory.
That is the same read pass a real capture or a `plan` run makes: every VM
config, every content listing, every status call. It uses the inventory to
size the series capture. It fetches nothing from Prometheus:

```sh
pve-storage-drs -c /etc/pve/drs.yaml collect-testdata --estimate
```

```
groups: 2   disks: 47
range: 2.0d  step: 5.0m
estimated Prometheus queries: 57
estimated series sample points: 324864
```

The query count includes the day-sized chunking `--estimate` itself
performs at capture time. That is 2 range-query chunks per group per metric
at the 48 h default, not 1. So the count is the real HTTP request count. It
is not a logical-query count that understates it.

The sample-point figure is `47 disks · 6 metrics · 1152 points`. A plain division,
`172800s / 300s`, would suggest `576` instead. At
`metrics.step == metrics.rate_window`, a live capture issues range queries
at *half* the configured step. Both settings are `5m` here, the project's
own default. The capture stores the points at that half step too. The half
step works around a gigapipe backend bug (`docs/internals/30-metrics.md`).
It doubles the points actually captured. `--estimate` accounts for this.
The printed figure matches what a real capture stores, not the configured
step's naive arithmetic. The `support.max_series_points` refusal below
compares against the same number.

Above `support.max_series_points` (default 5,000,000) the real capture
refuses outright. It names the flags that bring the count under the limit:

| Option | Effect |
|---|---|
| `-o`, `--output DIR` | Where the tool writes the bundle directory and its `.tar.gz` (default `support.bundle_dir`). |
| `--estimate` | Reads the full PVE inventory (one planning run's worth of API calls), prints the estimate above, and exits. It fetches nothing from Prometheus. |
| `--range DURATION` | Override the series capture range (default `support.capture_range`). |
| `--step DURATION` | Override the series resolution (default `metrics.step`). |
| `--no-series` | Topology, instant queries and findings only. The bundle has no per-disk time series, so it cannot exercise the `holt_winters` forecast. It is much smaller. |
| `--no-archive` | Write the directory only, skip the `.tar.gz`. |
| `--salt-file PATH` | Use a different anonymization salt (default `support.salt_path`). |
| `--new-salt` | Generate a fresh salt first. The tool logs it at warning level. Bundles made before and after no longer share a pseudonym mapping. |

The exit status is `0` when every capture step succeeded. It is `1` when
the bundle was written but the manifest records one or more failed calls.
A permission gap that
returns an HTTP error appears as such a failed call. A missing
`Datastore.Allocate` does not: PVE returns an empty list, and the tool records
that as success (see `00-installation.md`). The exit status is `2` on a usage error.

### What is in a bundle, and what is not

A bundle is a directory (`manifest.json`, `config.yaml`, `findings.json`,
`pve/`, `prometheus/`, `SHA256SUMS`). It also has a deterministic
`.tar.gz` archive. **Read it before sending it anywhere**. The content is
plain, sorted, indented JSON. Open it in an editor:

- **No direct identifier and no secret.** `config.yaml` never carries
  `proxmox.host`/`auth`, `prometheus.url`, or any other credential or
  endpoint. The tool drops them, it does not blank them. The tool replaces
  every node name, storage id, vmid, volume id, tag, pool and UPID with a
  pseudonym. The pseudonym is keyed to a salt (`support.salt_path`). The
  tool generates the salt locally. It never writes the salt into the
  bundle. The salt never leaves the host. The tool drops free text
  outright. That covers VM names, descriptions, snapshot names and storage
  comments. Device keys (`scsi0`, `efidisk0`, ...) are not identifiers.
  The tool keeps them as-is. The movability rules read them directly.
- `manifest.json` carries the **PVE and Prometheus server versions**
  (`capture.pve_version`/`capture.prometheus_version`, `null` if that one
  call failed). The versions are not identifiers. They need no
  anonymization. They are the one piece of "what was this captured
  against" that the bundle's own files otherwise leave out. The submission
  file that goes with a bundle records them too (see
  [Submission terms](#submission-terms)).
- **The mapping is stable per salt**. A second bundle from the same host
  names the same objects the same way. That helps compare a before/after
  pair. The mapping stays stable until `--new-salt` rotates it.
- **Sizes, capacities, load shapes and the whole configuration (minus
  credentials) are preserved.** That is what makes a bundle a test case
  instead of a shape. A bundle is **not anonymous against someone who
  already knows the cluster**. A cluster with three nodes, two 8 TiB LUNs
  and 1,214 VMs is recognizable to anyone who has seen it. Submitting one
  to the project is an informed decision. It is not a formality. See
  [Submission terms](#submission-terms).

## `--replay`: running against a bundle offline

```sh
pve-storage-drs --replay ./drs-testdata-cluster-3f8a91c2 plan --json
```

`--replay PATH` is a **global** option. The tool accepts it before any
subcommand. It substitutes both the PVE and Prometheus clients at the one
place each is constructed. So `verify-metrics`, `verify-storages`,
`show-load`, `plan` and `explain` all run **unchanged**. They use **no
network access at all**. `PATH` is the **unpacked bundle directory**, not
the `.tar.gz` it was sent as. Run
`tar -xzf drs-testdata-cluster-3f8a91c2.tar.gz` first.

- The configuration is the bundle's own `config.yaml`. That changes when
  `-c` is also given. Then you run the operator's cluster through a solver
  backend, a `spread_metric`, or a forecast model they never selected
  themselves.
- **`apply` is refused**. The tool also refuses any `--mode` above
  `dry-run`. The exit code is `2` either way. A replay can never issue a
  write.
- A query the bundle has no recorded response for produces a **loud,
  specific error**. The error names the query and the range the tool asked
  for. The tool never answers with a silent empty result standing in for
  "no data":

  ```
  pve-storage-drs: bundle has no recorded response for
  'sum by (vmid, instance) (rate(blockstat_rd_operations{...}[300s]))'
  over [1700000000,1700086400] -- captured range was [1699400000,1700000000]
  ```

  This is the failure mode to expect if you hand-edit a bundle's
  `config.yaml` to a `window.lookback`/`metrics.step` combination the
  capture never anticipated. It is also the failure mode if `--step` was
  overridden at capture time to something a replayed forecast does not
  expect.
- The tool reads `state.json` from the bundle if present. It never writes
  the file. A replay never touches the host's real state.

Run `--replay` against your own bundle before sending it anywhere. The
question is: "does `plan` against this bundle show the problem I am
reporting?" The command answers exactly that. It is also how the author
verifies a submitted bundle reproduces what its submission file claims.

## Sending one to the project

**Bundles are wanted, and a pull request carrying one is as valuable as a
pull request carrying code.** A bug report describes a failure. A bundle
reproduces it offline, on a machine that has never seen your cluster. The
reproduction works for as long as the project exists. A bundle is also the
only thing that can prove the MILP solver and the fallback heuristic still
agree at a few hundred disks. The synthetic fixtures in `tests/fixtures/`
top out at eight disks.

Only bundles that meet the terms below are accepted.

## Submission terms

These terms set when the project accepts a bundle. Read all of them before you send one.

### 1. Read the bundle first

Open the bundle directory. Read `manifest.json`, `config.yaml`, `findings.json` and the
files under `pve/` and `prometheus/`. The files are plain, sorted, indented text.

The project runs a scrub audit on every bundle. The audit looks for IP addresses, e-mail
addresses, hostnames, keys and long hex strings. The audit assumes the collector has a bug.
A clean audit does not replace your own reading. Do not send a bundle that you did not read.

### 2. Choose the size and the form

- A bundle under 8 MiB unpacked can be committed to the project repository.
- A larger bundle is not committed. The test suite can run on it from a directory named in
  the `DRS_CORPUS_DIR` environment variable.
- If the size and shape of your cluster are confidential, send a `--no-series` bundle, or
  send only a written description. A description still helps the project.

### 3. Write the submission file

Each committed bundle has a submission file, named `<bundle-name>.submission.yaml`. It
records who collected the bundle, what it shows, and the consent you give. Use this form:

```yaml
submitted_by: Somebody <somebody@example.org>   # or "anonymous", with a contact for questions
submitted_on: 2026-09-11
consent:
  redistribute_under: AGPL-3.0-or-later
  reviewed_bundle_before_sending: true
collected_with: pve-storage-drs 0.1.1           # the collector version, from manifest.json
versions:
  pve: 9.2.11
  prometheus_backend: gigapipe                  # or prometheus, victoriametrics, ...
what_this_reproduces: >
  One of the six blockstat metrics missing for a single disk while the other five
  report it normally.
```

- `submitted_by`: your name and e-mail address. Or write `anonymous`, with a contact for
  questions.
- `submitted_on`: the date you send the bundle, as `YYYY-MM-DD`.
- `consent.redistribute_under`: the licence of the project, `AGPL-3.0-or-later`.
- `consent.reviewed_bundle_before_sending`: `true`. Write `true` only when you read the
  bundle under section 1.
- `collected_with`: the collector version, from `manifest.json`.
- `versions`: the PVE version and the Prometheus backend name.
- `what_this_reproduces`: one short statement of the behaviour the bundle shows.

### 4. Send it

Open a pull request in the project repository, <https://github.com/bzed/proxmox-storage-drs>.
The pull request adds the unpacked bundle directory and its submission file together. Do
not send only the `.tar.gz`. The project commits the unpacked form, because it diffs line by
line in review.

### 5. What you agree to

When you send a bundle with a submission file that gives consent, you agree that:

- you have the right to send the bundle from your cluster;
- the project may commit the bundle to its repository under AGPL-3.0-or-later, the licence of
  the project;
- a committed bundle is public. Git keeps it in the history of the repository, so anyone who
  clones the repository gets it;
- the bundle is **not anonymous against someone who already knows the cluster**. See
  [What is in a bundle, and what is not](#what-is-in-a-bundle-and-what-is-not);
- if a later review shows that a committed bundle leaks data, the project may repair the
  bundle from its own captured data. It records the repair in the submission file.

### 6. What the project checks before it accepts a bundle

- The scrub audit passes on the bundle.
- The submission file exists, and it records your consent.
- The submitter reviewed the bundle. A bundle that the submitter did not review is not
  committed, however clean the audit is.

After acceptance, the test suite runs each bundle in four passes:

1. The scrub audit, on every `make check`.
2. Invariant checks: the reserve, the transient invariant, and the per-move duration rule
   hold at every step.
3. A comparison of the MILP solver and the fallback heuristic. The MILP objective must not be
   worse than the heuristic objective.
4. A regression check against a generated expected-results file. A person does not edit that
   file.
