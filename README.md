<p align="center">
  <img src="docs/logo.svg" alt="pve-storage-drs logo: a disk moving between two storage pools" width="160">
</p>

# proxmox-storage-drs

[![Proxmox](https://img.shields.io/badge/Proxmox-E57000?style=for-the-badge&logo=proxmox&logoColor=white)](https://proxmox.com/)
[![Ask DeepWiki](docs/deepwiki-badge.svg)](https://deepwiki.com/bzed/proxmox-storage-drs)
[![Tests](https://github.com/bzed/proxmox-storage-drs/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/bzed/proxmox-storage-drs/actions/workflows/tests.yml)
[![Debian Package](https://github.com/bzed/proxmox-storage-drs/actions/workflows/debian-package.yml/badge.svg?branch=main)](https://github.com/bzed/proxmox-storage-drs/actions/workflows/debian-package.yml)
[![codecov](https://codecov.io/gh/bzed/proxmox-storage-drs/branch/main/graph/badge.svg)](https://codecov.io/gh/bzed/proxmox-storage-drs)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

A replacement for VMware's Storage DRS, for Proxmox VE 9.2.

The PVE 9.2 Dynamic Load Balancer moves guests between nodes to even out CPU and memory. It has no
notion of the LUNs behind the guests. This tool is the **storage** counterpart of the balancer.
It never moves a guest. It moves individual disks between storages. The command is
`pve-storage-drs`. The name stops readers from confusing the two tools.

The tool balances **disk I/O load across configurable groups of shared storages**. A group holds
LVM/FC storage, Ceph RBD, or any other shared storage type PVE supports. The tool live-migrates
individual VM disks between storages within a group. It guarantees a snapshot free-space reserve.
It performs as few migrations as possible.

---

## Quickstart

Read this section end to end before running anything.

**Steps 1–6 cannot move a disk**. Work through them on production during business hours.
**Steps 7 and 8 migrate data**. Step 7 asks before each move. Step 8 does not ask. Both steps
carry a warning mark. Earlier steps do not commit you to a move.

### Step 0 — check the prerequisites

| You need | How to tell you have it |
|---|---|
| A **PVE 9.2 cluster** with at least two shared, image-holding storages. A disk could reasonably move between them. Use storages on the same backing tier, so that a move is a balancing decision, not a demotion | `pvesm status` lists them. It lists their content types. `grep shared /etc/pve/storage.cfg` shows which storages are shared. `verify-storages` checks the rest once you are installed |
| A **Prometheus-compatible metrics backend** already receiving PVE's per-disk `blockstat` series | query it for `blockstat_rd_operations`. Check that the result carries a per-drive label. An existing "VM disk I/O" dashboard is *not* evidence. It may be built on PVE's RRD data or on `prometheus-pve-exporter`. Neither source carries these series at all |
| A **host to run it on**. The host is a cluster member, or any Debian trixie box that can reach tcp/8006 and your Prometheus | — |
| A **PVE credential** with the right privileges | Step 2 |

`apply` is the only command that can write to the cluster at all. `show-load`, `verify-metrics`,
`verify-storages`, `plan`, `explain` and `collect-testdata` have no code path that writes to the
cluster. `apply` does nothing beyond what `plan` printed until you move `execution.mode` or
`--mode` off the `dry-run` default.

### Step 1 — install

**Every release is published as a ready-built Debian package** on the
[GitHub releases page](https://github.com/bzed/proxmox-storage-drs/releases). Each release carries
an architecture-independent `pve-storage-drs_<version>_all.deb`. A `SHA256SUMS` file sits next to
it. The project has no apt repository yet. Download the `.deb`. Install it with `apt`. `apt`
pulls the dependencies from the trixie archive. A PVE node already has that archive configured:

```sh
VERSION=0.1.22      # the newest release on the releases page
BASE=https://github.com/bzed/proxmox-storage-drs/releases/download/debian/$VERSION
wget "$BASE/pve-storage-drs_${VERSION}_all.deb" "$BASE/SHA256SUMS"
sha256sum -c SHA256SUMS
apt install ./pve-storage-drs_${VERSION}_all.deb
```

The package is not signed. `SHA256SUMS` comes from the same release page as the `.deb`. It
catches a corrupted download, not a tampered release. CI builds the package in a `debian:trixie`
container. CI runs lintian on it. CI installs it. CI runs its autopkgtests there. A release
publishes only after CI finishes these steps.

To build the package yourself instead:

```sh
make deb                                     # builds ../pve-storage-drs_*_all.deb
apt install ../pve-storage-drs_*_all.deb
```

The Debian package targets **trixie**. Trixie is the base of PVE 9.x. The package pulls a real
MILP solver (`coinor-cbc` via `python3-pulp`) as a hard dependency. A package install therefore plans with the CBC solver by default. The heuristic
runs only when you select it or when a CBC solve fails. See [Packaging](#packaging).

Run from a git checkout instead. The checkout gives you the dependency-free heuristic unless you
also install the `solver` extra:

```sh
make venv
.venv/bin/pve-storage-drs --version
```

### Step 2 — grant a PVE credential

Read this step in full. A too-narrow grant fails *silently* rather than with an error. Here is
the short version:

| Privilege | Where | Why |
|---|---|---|
| `Datastore.Audit` **and** `Datastore.Allocate` | on each managed storage's own path, `/storage/<id>` | Under `Datastore.Audit` alone, `GET /nodes/{node}/storage/{storage}/content` returns an empty list. The response is a clean `200`. It carries no error. The empty list silently under-counts what already occupies a storage. The under-count erodes the snapshot reserve the tool exists to protect. |
| `VM.Audit` | cluster-wide, `/` | VM inventory and config |
| `VM.Config.Disk`, `VM.Migrate` | cluster-wide, `/` | only needed once `apply` actually executes a move |

An **API token** is the recommended credential. Unattended operation requires one. PVE
privilege separation sets the token's effective permission to the *intersection* of the token's
own ACL and its owning user's ACL. Grant the roles to **both** `user@realm` and
`user@realm!tokenid`. Or disable privilege separation on the token.

[`docs/manual/00-installation.md`](docs/manual/00-installation.md) has the full reasoning and a
concrete minimal setup.

### Step 3 — write the configuration

```sh
cp /usr/share/doc/pve-storage-drs/examples/drs.example.yaml /etc/pve/drs.yaml
# or, from a checkout: cp config/drs.example.yaml /etc/pve/drs.yaml
$EDITOR /etc/pve/drs.yaml
```

`/etc/pve` is on the cluster filesystem, so every node holds the same file. The file is
group-readable by `www-data`. Prefer a token secret in the environment to a
plaintext secret in the file.

A minimal configuration is four blocks. Every other key has a documented default. Leave the keys
alone until you have a reason to change one:

```yaml
schema_version: 1

proxmox:
  host: pve01.example.com
  auth:
    token_id: "drs@pve!balancer"
    token_secret: null        # set PVE_TOKEN_SECRET in the environment instead

prometheus:
  url: http://prometheus.example.com:9090

groups:
  - name: fc-tier1
    storages:
      - id: san-a
      - id: san-b
```

`groups[].storages[]` is what a disk may not leave. An entry is a literal PVE storage id or a
`/regex/` pattern. The tool matches the pattern against the cluster's storage inventory on every
run. A LUN added next year joins its group with no config edit.

You may still have to touch one block: `metrics`. Touch it if your Telegraf names things
differently from the defaults. Step 4 tells you whether it does.

### Step 4 — verify the metrics

```sh
pve-storage-drs -c /etc/pve/drs.yaml verify-metrics
```

Do not skip this step. Do not treat a warning here as cosmetic. The tool runs six checks against
the live backend:

1. each of the six configured metric names exists;
2. a live series really carries the labels that `metrics.labels.vmid`/`.device`/`.node` name. The
   config keys and the label names are different words. They default to `vmid`, `instance` and
   `nodename`;
3. `metrics.labels.device` is not still the unconfirmed default `instance`;
4. the six metrics agree with each other about which disks exist;
5. per-disk sample coverage is good enough over your window;
6. the declared `pvestatd` push interval matches the sample spacing actually observed.

Two findings matter more than the rest. Check 4 failing means a transport dropped a field. The finding reads *no series for N disk(s) that other configured metrics report*. That failure mode produces a
confidently wrong plan rather than an error. See [The metrics pipeline](#the-metrics-pipeline).
Check 3 asks you to confirm something the tool cannot check for you. `instance` is the tag PVE
itself emits for the drive id, so `instance` is not wrong. Prometheus uses `instance` for its own
scrape target. Many Telegraf configurations rename or overwrite one of the two tags. Find out
which one survived in your deployment before anything downstream joins on it.

[`docs/manual/20-verifying-metrics.md`](docs/manual/20-verifying-metrics.md) explains every
finding and what to do about it.

### Step 5 — look at the cluster

```sh
pve-storage-drs -c /etc/pve/drs.yaml show-load          # per storage: disks, sizes, load, reserve
pve-storage-drs -c /etc/pve/drs.yaml verify-storages    # saferemove, wipe times, pattern expansion
```

Use `show-load` to check whether the numbers describe the cluster you think you have. The command
also prints a per-group act/no-act verdict with its reasoning. You see what a `plan` would decide
before you ask for one.

### Step 6 — compute a plan

```sh
pve-storage-drs -c /etc/pve/drs.yaml plan
pve-storage-drs -c /etc/pve/drs.yaml explain    # the same plan, narrated
```

`plan` never runs anything, in any mode. `explain` runs the identical pipeline. It then narrates
what `plan` output does not print. The narration covers every disk pinned this run and why. It
covers the VMs a pin leaves spread across storages. It covers the objective's seven terms,
individually. It covers the payback arithmetic. It covers the closest move the solver rejected, when a group's gate
said "act" but the solver still chose to move nothing. It shows
what that move would have cost. That last item answers the most common question this tool gets.

### Step 7 — apply it ⚠️ this one migrates data

```sh
pve-storage-drs -c /etc/pve/drs.yaml --mode confirm apply    # asks before each move
```

The flag `--mode confirm` selects a less safe mode. It is the only thing that makes `apply` do
more than `plan` printed. `confirm` prompts per move. Nothing happens without a second decision
from you. `auto` does not prompt. It also honours `execution.time_windows` and
`execution.max_migrations_per_run`. With `execution.mode` at its `dry-run` default, `apply` with
no `--mode` stays a dry run.

### Step 8 — run it unattended ⚠️ this one migrates data without asking

```sh
pve-storage-drs -c /etc/pve/drs.yaml --mode auto apply
```

The package ships no timer unit — write your own `.service`/`.timer` pair, or use cron. Whichever
you choose, run it on **exactly one host**: `state.json` (cooldowns, the drift baseline, the run
lock) is node-local and does not coordinate across the cluster, so two hosts running this keep two
independent sets of cooldowns and two independent locks. A startup scan for in-flight `move_disk`
tasks keeps them from actively conflicting, but it degrades the overlap to "slow and redundant"
rather than preventing it.

An `auto` run logs its full decision trail — gate, load, plan, objective, payback, and every
migration with its PVE task UPID — without needing `-v`, because under a timer that log
is the only record of what happened to your cluster. `--log-level warning` or `error` on such a
run is raised back up to `info` rather than discarding it; `--quiet` is the one option that does
discard it, and it does not belong in a timer unit. See
[`docs/manual/35-logging.md`](docs/manual/35-logging.md).

To have your monitoring system watch an unattended run, set `monitoring.status_file`: `apply` then
leaves a status report in the format of the `check_statusfile` Nagios plugin
(`monitoring-plugins-contrib`) after **every** run — `OK`, `WARNING` (it gave up after too many outside
changes, or a group is still short of its reserve) or `CRITICAL` (a move failed, or PVE or Prometheus
could not be read) — and its modification time tells the plugin the timer is still firing. See
[`docs/manual/36-monitoring.md`](docs/manual/36-monitoring.md).

### Things worth knowing at this point

- `--group NAME` (repeatable) restricts a `show-load`, `verify-storages`, `plan`, `explain` or
  `apply` run to one storage group. `verify-metrics` and `collect-testdata` are cluster-wide.
  They ignore the flag. Groups are independent, so the flag never changes the answer for the
  groups you selected.
- `--json` emits the machine-readable report on **stdout**. Logs always go to **stderr**. So
  `pve-storage-drs --json plan > plan.json` is safe.
- `--replay BUNDLE` runs the whole engine offline against a captured bundle. See
  [Contributing test data](#contributing-test-data).
- `pve-storage-drs --help`, `pve-storage-drs <command> --help` and `man pve-storage-drs` always
  carry the exact current option list and every default.

---

## The metrics pipeline

📖 **[`docs/manual/05-metrics-pipeline.md`](docs/manual/05-metrics-pipeline.md) is the page on
this.** Read it before writing the `metrics` config block. What follows is the short version. It
sits here, not only in the manual, because it decides whether this tool can work on your cluster
at all.

`pve-storage-drs` collects nothing itself. It ships no exporter. It reads six per-disk counters
out of a Prometheus-compatible backend you already run. The counters are QEMU `query-blockstats`
figures. `pvestatd` already gathers them. PVE's **InfluxDB external metric server** already
exports them. The export carries the drive id as a label. So the data exists cluster-wide before you
install the tool. What varies is **what survives the trip**. Getting that wrong is the most
common way to get a confidently wrong answer out of this tool.

The mechanism, in one paragraph. InfluxDB line protocol carries string fields. It fixes a
field's type at its first write. Prometheus and OpenMetrics have no string sample type. A
transport between the two can therefore drop one of the six counters. It drops the counter for
one disk, permanently, silently. The other five counters keep working. Nothing errors. Your
dashboards keep drawing. This tool reads the gap as "that disk does no writes". **Telegraf with
a Prometheus remote-write or OpenMetrics output is the prominent example**. Most people build it
first. It needs deliberate processor configuration to avoid this. `verify-metrics` cross-checks
the six metrics against each other precisely to catch it.

A backend that ingests **the InfluxDB protocol exactly as PVE exports it** and serves PromQL
itself has no such bridge. There is no Telegraf, no output plugin, nothing in the path that can
drop a field on type grounds. **[gigapipe](https://github.com/metrico/gigapipe) on ClickHouse** is
the well-tested setup here. The project runs the tool against it. Point `prometheus.url` at its query endpoint.
It also ingests OpenTelemetry, but the project has not tested that path. PVE's OTel metric server
is the wrong source for this tool regardless. It bakes the drive id into the metric name instead
of a label. Plain Prometheus and VictoriaMetrics work too. `prometheus.url` is the only setting
that distinguishes them.

---

## Status

The tool is implemented, tested against a production cluster, and released as a Debian
package. See [Step 1](#step-1--install). Phases 1–14 and 16–18 of `IMPLEMENTATION_PLAN.md` §12
are implemented. Phase 16 is not yet tested on a live cluster.
They run from reading the cluster and Prometheus, through the gates, the solver (CBC when
installed, a dependency-free heuristic otherwise), move ordering and execution, to Debian
packaging. They also cover the `collect-testdata` / `--replay` diagnostic-bundle subsystem, the
§2.3 logging policy, the capacity-spread objective, the free-space requirements and
forecast-driven placement. Phase 15 is an internal refactor of how configuration defaults are
stored. It is still open. It changes no behaviour. Every command is implemented and covered
by the test suite. This includes `apply`'s unattended `auto` mode and `explain`'s narration of
the pins, fragmentation and payback arithmetic behind a plan.

[`docs/manual/30-safety-and-status.md`](docs/manual/30-safety-and-status.md) is the authoritative,
per-command status table. Trust it over any impression given elsewhere. `REVIEW.md` holds a
standing external review of both the plan and the implementation. The review tracks findings to
resolution with stable IDs. The code and commit messages refer back to those IDs.

## Configuration

`groups[].storages[]` names the storages a disk may move between. An entry is a literal PVE storage
id or a `/regex/` pattern. The tool matches a pattern against the cluster's storage inventory on
every run. A LUN that you add later thus joins its group with no config edit. Every other key has a
documented default. These keys cover the load model's weights, the gates that decide *whether* a
group needs to act, the snapshot reserve, the objective the solver optimizes, cooldowns, execution
concurrency and time windows. Leave a key alone until you have a reason to change it.

[`config/drs.example.yaml`](config/drs.example.yaml) is the full annotated reference. It shows every
key, its default, and why the key exists, in the order of `10-configuration.md`.
[`docs/manual/10-configuration.md`](docs/manual/10-configuration.md) is the prose version of the
same content, with one section per key. Both files are written by hand. The test suite keeps them
correct (`.agents/documentation.md`). The example must validate against the configuration schema and
carry every top-level key. The manual must document every key of the schema, and no other key.

## Contributing test data

**Pull requests with test data from real clusters are very welcome, arguably more welcome than
code.** The interesting failures of this tool came from clusters that behaved in ways no synthetic
fixture anticipated. A bug report *describes* a failure. A bundle *reproduces* the failure, offline,
forever. A synthetic fixture can prove the solver optimal on six disks. Only a real cluster can
prove that the MILP and the heuristic still agree at three hundred disks. Today, every bundle in
`tests/corpus/` comes from the author's own cluster. A submission from your cluster fixes exactly
that limitation.

`collect-testdata` captures a bundle:

```sh
pve-storage-drs -c /etc/pve/drs.yaml collect-testdata --estimate   # what it would fetch
pve-storage-drs -c /etc/pve/drs.yaml collect-testdata              # capture it
```

The command is read-only by construction and never issues `move_disk`. `--mode confirm`/`--mode
auto` alongside it is a usage error; the command does not silently ignore the flag. `--estimate`
first shows the query count and the sample-point count, and fetches nothing. Above
`support.max_series_points`, the capture refuses to run instead of overloading your Prometheus.
Useful flags:

- `--range`/`--step` limit the series capture.
- `--no-series` captures only the topology and instant queries.
- `-o` writes the bundle somewhere else.

The command writes two forms of the same bundle under `support.bundle_dir`. The **directory** is
the form that you read and that gets committed. The deterministic **`.tar.gz`** of the directory is
the form that you attach to a mail or an issue. Exit status `1` with a written bundle means that
the manifest recorded a failed API call, usually a permission gap. It does not mean that the capture
is unusable.

Replay the bundle yourself before you send it anywhere. The bundle is the whole input, so the replay
is not a sanity check. It is the actual proof that the bundle reproduces the problem:

```sh
pve-storage-drs --replay /var/lib/pve-storage-drs/testdata/<bundle> plan
pve-storage-drs --replay /var/lib/pve-storage-drs/testdata/<bundle> explain
```

`--replay` opens **no network connections at all**, neither to PVE nor to Prometheus. It uses the
bundle's own `config.yaml` unless you override it with `-c`. With `-c`, you can run the cluster of
another person through a different solver backend, spread metric or forecast model.

### What a bundle does and does not hide

The tool replaces every identifier with a pseudonym: node, storage, VM, volume, pool, tag, user
and task id. An HMAC salt keys the pseudonyms. The salt **stays on your host and never enters the
bundle**. The tool copies fields by **allowlist**. It does not capture anything that the engine does
not read. Free text from operators lives in such fields (VM names, descriptions, snapshot names,
comments). No hostname, IP, IQN, fingerprint, key or password survives.

A bundle is **not anonymous to somebody who already knows your cluster.** Node, storage and VM
counts, capacities, disk sizes and load shapes all survive, because they make the bundle a test
case. Together they form a recognizable fingerprint.

So **open the bundle and read it before you send it.** The files are sorted, indented JSON, made for
reading. The size and shape of your cluster alone can be confidential. In that case, send a
`--no-series` bundle, or send only a description. A description is still worth having.

### Submitting one

[`tests/corpus/README.md`](tests/corpus/README.md) is the full submission guide. In short:

- A committed bundle must be under **8 MiB unpacked**. Larger bundles live outside the repository,
  and `DRS_CORPUS_DIR` finds them.
- A bundle must come with a `<bundle>.submission.yaml`. The file records who collected the bundle
  and what it reproduces. It records that you read the bundle. It records that you consent to its
  redistribution under AGPL-3.0-or-later.
- An accepted bundle is public permanently, in the git history. A bundle that its submitter did not
  review does not get committed, however clean the automated scrub audit says it is.

Every committed bundle is then part of `make check`. The checks are:

- a scrub audit that assumes the collector has a bug,
- the domain invariants, asserted again against real data,
- the agreement between the MILP and the heuristic,
- a generated `<bundle>.expected.json` regression baseline.

## Documentation

| What | Where |
|---|---|
| Quick start, this file | you are reading it |
| Operator manual (installation, configuration, every command, logging, safety guarantees and exit codes) | [`docs/manual/`](docs/manual/) (Markdown, one file per topic) or [`docs/pve-storage-drs-manual.pdf`](docs/pve-storage-drs-manual.pdf) (typeset) |
| `pve-storage-drs(1)` manpage | `man pve-storage-drs` once installed, or [`man/pve-storage-drs.1.md`](man/pve-storage-drs.1.md) in source |
| `--help` | always current. The same argument definitions that the manual and manpage describe generate it |
| Full specification (the data model, the optimization problem, every formula and invariant) | [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md), or [`docs/IMPLEMENTATION_PLAN.pdf`](docs/IMPLEMENTATION_PLAN.pdf) typeset with a title page and table of contents |
| Internals guide, for whoever changes the code | [`docs/internals/`](docs/internals/) (Markdown, one file per module) or [`docs/internals.pdf`](docs/internals.pdf) (typeset) |
| Submitting real-cluster test data | [`tests/corpus/README.md`](tests/corpus/README.md) |
| External review of the plan and the implementation | [`REVIEW.md`](REVIEW.md). The plan, code and commits refer back to its stable finding IDs |
| Worked example / test fixtures | [`tests/fixtures/fc-tier1.yaml`](tests/fixtures/fc-tier1.yaml) (the example of §14, machine-readable) and [`tests/fixtures/reserve-tradeoff.yaml`](tests/fixtures/reserve-tradeoff.yaml) (a deliberately adversarial second group). Both have proven-optimal `*.expected.json` results. `python3 tests/fixtures/generate_expected.py` regenerates them (`--check` asserts that they are current) |
| Working agreement for contributors (human or agent) | [`AGENTS.md`](AGENTS.md) and [`.agents/`](.agents/) |

The package installs all of this under `/usr/share/doc/pve-storage-drs/`. That directory holds the
Markdown sources under `manual/` and `internals/`, plus `IMPLEMENTATION_PLAN.md`, and the three
typeset PDFs beside them. A cluster node has no GUI and often no way to get a PDF off the node. For
this reason, the package ships the Markdown uncompressed, and the Markdown is not an afterthought.
On the machine that has the problem, read it like this:
`less /usr/share/doc/pve-storage-drs/manual/20-verifying-metrics.md`.

`make docs` generates all three PDFs from those Markdown sources (`make pdf`/`internals`/`manual`
individually). `make docs-check`, a part of `make check`, keeps the PDFs in step. The title page of
each PDF carries the SHA-256 of its Markdown source.

## Requirements

### To run it

- A Proxmox VE 9.2 cluster with shared storages (LVM/FC, Ceph RBD, or another shared type)
- A Prometheus-compatible backend that already receives PVE's per-disk `blockstat` series via the
  **InfluxDB external metric server**. This can be plain Prometheus, VictoriaMetrics, or
  [gigapipe](https://github.com/metrico/gigapipe) on ClickHouse. The project runs the tool against
  gigapipe. Read [The metrics pipeline](#the-metrics-pipeline) first: the transport between PVE and
  the backend is where metrics get lost.
- A PVE API user or token with these privileges. `Datastore.Audit` **and `Datastore.Allocate`** on
  each managed storage. `VM.Audit` cluster-wide. Also `VM.Config.Disk` and `VM.Migrate`, once
  `apply` executes moves. `Datastore.Audit` alone is not enough and fails silently. To see why, read
  [`docs/manual/00-installation.md`](docs/manual/00-installation.md) and
  [Step 2](#step-2--grant-a-pve-credential) above.

### To work on it

- Python 3.11+ (`make venv` installs the rest into `.venv/`)
- `pandoc`, `lualatex` and `latexmk`. You need them only to rebuild the PDFs. On Debian:
  `pandoc texlive-luatex texlive-latex-extra latexmk fonts-sil-gentiumplus fonts-dejavu-core
  fonts-dejavu-mono fonts-symbola`
- `pulp` (with `coinor-cbc`) is the optional `pip install .[solver]` extra for the CBC solver
  backend. The tool works fully without it and uses a dependency-free heuristic instead
  (`solver.backend: auto`, the default, tries CBC first)

## Packaging

The project ships the tool as the Debian package `pve-storage-drs`. The sources of the package are
in `debian/` in this repository. The package targets **Debian trixie**, the base of Proxmox VE 9.x.
The project chooses dependencies that trixie packages, so the package installs on a management host
with no outbound network. `debian/tests` installs the built package on a system that carries only
its `Depends`, and proves that the command runs.

GitHub Actions builds every `debian/<version>` tag. After the package passes lintian and its
install-and-run test, GitHub Actions publishes it as a
[GitHub release](https://github.com/bzed/proxmox-storage-drs/releases). The release carries the
`.deb` and a `SHA256SUMS` file. [Step 1](#step-1--install) shows how to install it. There is no apt
repository yet. If you want `apt install pve-storage-drs` and `apt upgrade` to work, put the `.deb`
into your own repository.

```sh
make deb                      # local build; CI builds it in a debian:trixie container and with sbuild
```

The project has two pipelines. GitHub Actions runs lint, types, tests and coverage in
`debian:trixie` with the Debian-packaged toolchain. It also builds the package and installs it.
GitLab CI (`debian/.gitlab-ci.yml`) runs Debian's Salsa pipeline: sbuild without network, then
lintian, piuparts, reprotest and autopkgtest. [`.agents/packaging.md`](.agents/packaging.md)
explains both pipelines.

## Contributing

[`AGENTS.md`](AGENTS.md) is the working agreement for this repository, for humans and for agents
alike. It covers the toolchain (black + flake8 + mypy + pytest, all configured not to disagree with
each other). It covers the 85 % coverage floor, the branch-and-merge-on-green workflow, the
documentation the project owes its users, and the domain rules that a refactoring must not remove.
[`.agents/`](.agents/) holds the long form.

```sh
make venv     # bootstrap .venv with the dev tooling
make check    # format, lint, types, tests, coverage, fixture, corpus and PDF freshness
make docs     # re-render the PDFs and the manpage after editing them
```

`make SYSTEM_TOOLS=1 <target>` runs the same targets against tools already on `PATH` instead of
`.venv`. CI and the Debian build run them that way.

Test data is a contribution in its own right. See
[Contributing test data](#contributing-test-data) above.

## Licence

GNU Affero General Public License v3.0 or later. See [`LICENSE`](LICENSE).

Copyright © 2026 Bernd Zeimetz <bernd@bzed.de>

## AI disclaimer

This project was built with AI help at every stage. Anthropic's
[Claude Opus 5](https://www.anthropic.com/claude) did the planning and architecture, including
`IMPLEMENTATION_PLAN.md` itself. Anthropic's [Claude Sonnet 5](https://www.anthropic.com/claude)
wrote most of the code, tests and documentation. Since late September 2026,
[Claude Opus 5.5](https://www.anthropic.com/claude) has done the work: bug fixes found on a
production cluster, new placement rules, reviews of the documentation, and the releases. Each commit
names the model that wrote it in its `Co-Authored-By:` trailer. The result went through two
independent rounds of review. A human maintainer did one round.
[Z.ai](https://z.ai)'s GLM 5.3 model did the other, as a second, automated reviewer. `REVIEW.md` is
the standing record of both.
