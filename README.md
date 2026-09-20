# proxmox-storage-drs

[![Proxmox](https://img.shields.io/badge/Proxmox-E57000?style=for-the-badge&logo=proxmox&logoColor=white)](https://proxmox.com/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/bzed/proxmox-storage-drs)
[![Tests](https://github.com/bzed/proxmox-storage-drs/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/bzed/proxmox-storage-drs/actions/workflows/tests.yml)
[![Debian Package](https://github.com/bzed/proxmox-storage-drs/actions/workflows/debian-package.yml/badge.svg?branch=main)](https://github.com/bzed/proxmox-storage-drs/actions/workflows/debian-package.yml)
[![codecov](https://codecov.io/gh/bzed/proxmox-storage-drs/branch/main/graph/badge.svg)](https://codecov.io/gh/bzed/proxmox-storage-drs)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

A replacement for VMware's Storage DRS, for Proxmox VE 9.2.

It is the **storage** counterpart to the Dynamic Load Balancer that PVE 9.2 ships: that one moves
guests between nodes to even out CPU and memory, and has no notion of the LUNs behind them. This
one never moves a guest — it moves individual disks between storages. The command is
`pve-storage-drs`, named to keep the two from being confused.

It balances **disk I/O load across configurable groups of shared storages** (LVM/FC, Ceph RBD, or
any other shared storage type PVE supports) by live-migrating individual VM disks between storages
within a group, while guaranteeing a snapshot free-space reserve and performing as few migrations
as possible.

---

## Quickstart

Read this section end to end before running anything.

**Steps 1–6 cannot move a disk**, so you can work through them on production during business
hours. **Steps 7 and 8 migrate data** — step 7 asks before each move, step 8 does not — and are
marked accordingly. Nothing before them commits you to them.

### Step 0 — check the prerequisites

| You need | How to tell you have it |
|---|---|
| A **PVE 9.2 cluster** with at least two shared, image-holding storages a disk could reasonably move between — same backing tier, so that moving a disk between them is a balancing decision and not a demotion | `pvesm status` lists them and their content types; `grep shared /etc/pve/storage.cfg` shows which are shared. `verify-storages` checks the rest once you are installed |
| A **Prometheus-compatible metrics backend** already receiving PVE's per-disk `blockstat` series | query it for `blockstat_rd_operations` and check the result carries a per-drive label. An existing "VM disk I/O" dashboard is *not* evidence — it may well be built on PVE's RRD data or on `prometheus-pve-exporter`, neither of which carries these series at all |
| A **host to run it on** — a cluster member or any Debian trixie box that can reach tcp/8006 and your Prometheus | — |
| A **PVE credential** with the right privileges | Step 2 |

`apply` is the only command that can write to the cluster at all — `show-load`, `verify-metrics`,
`verify-storages`, `plan`, `explain` and `collect-testdata` have no code path that does — and
`apply` itself does nothing beyond what `plan` printed until `execution.mode` or `--mode` moves it
off its `dry-run` default.

### Step 1 — install

There is no public apt repository yet, so `apt install pve-storage-drs` works only once you have
built the package and put it in a repository of your own — or installed the `.deb` directly:

```sh
make deb                                     # builds ../pve-storage-drs_*_all.deb
apt install ../pve-storage-drs_*_all.deb     # or: dpkg -i ... && apt -f install
```

The Debian package targets **trixie**, the base of PVE 9.x, and pulls in a real MILP solver
(`coinor-cbc` via `python3-pulp`) as a hard dependency, so a package install always plans with a
solver rather than the fallback heuristic. See [Packaging](#packaging).

To run from a git checkout instead — note that this gets you the dependency-free heuristic unless
you also install the `solver` extra:

```sh
make venv
.venv/bin/pve-storage-drs --version
```

### Step 2 — grant a PVE credential

This is the one step worth reading in full, because a too-narrow grant fails *silently* rather
than with an error. The short version:

| Privilege | Where | Why |
|---|---|---|
| `Datastore.Audit` **and** `Datastore.Allocate` | on each managed storage's own path, `/storage/<id>` | `GET /nodes/{node}/storage/{storage}/content` returns an empty list — a clean `200`, no error — under `Datastore.Audit` alone. That silently under-counts what already occupies a storage, which erodes the snapshot reserve the tool exists to protect. |
| `VM.Audit` | cluster-wide, `/` | VM inventory and config |
| `VM.Config.Disk`, `VM.Migrate` | cluster-wide, `/` | only needed once `apply` actually executes a move |

If you use an **API token** (recommended, and required for unattended operation), remember that
PVE privilege separation makes the token's effective permission the *intersection* of its own ACL
and its owning user's. Grant the roles to **both** `user@realm` and `user@realm!tokenid`, or
disable privilege separation on the token.

[`docs/manual/00-installation.md`](docs/manual/00-installation.md) has the full reasoning and a
concrete minimal setup.

### Step 3 — write the configuration

```sh
cp /usr/share/doc/pve-storage-drs/examples/drs.example.yaml /etc/pve/drs.yaml
# or, from a checkout: cp config/drs.example.yaml /etc/pve/drs.yaml
$EDITOR /etc/pve/drs.yaml
```

`/etc/pve` is on the cluster filesystem, so this is automatically the same file on every node.
It is also group-readable by `www-data`, so prefer a token secret in the environment over a
plaintext one in the file.

A minimal configuration is four blocks. Everything else has a documented default and can be left
alone until you have a reason to change it:

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

`groups[].storages[]` is what a disk may not leave. Entries are literal PVE storage ids, or a
`/regex/` pattern matched against the cluster's storage inventory on every run — so a LUN added
next year joins its group with no config edit.

The one block you may still have to touch is `metrics`, if your Telegraf names things differently
from the defaults. Step 4 tells you whether it does.

### Step 4 — verify the metrics

```sh
pve-storage-drs -c /etc/pve/drs.yaml verify-metrics
```

Do not skip this, and do not treat a warning here as cosmetic. Six checks run against the live
backend:

1. each of the six configured metric names exists;
2. a live series really carries the labels that `metrics.labels.vmid`/`.device`/`.node` name — the
   config keys and the label names are different words, defaulting to `vmid`, `instance` and
   `nodename`;
3. `metrics.labels.device` is not still the unconfirmed default `instance`;
4. the six metrics agree with each other about which disks exist;
5. per-disk sample coverage is good enough over your window;
6. the declared `pvestatd` push interval matches the sample spacing actually observed.

Two findings matter more than the rest. Check 4 failing — *one metric is missing disks the others
report* — means a transport dropped a field, which is the failure mode that produces a confidently
wrong plan rather than an error; see [The metrics pipeline](#the-metrics-pipeline). Check 3 is
asking you to confirm something the tool cannot check for you: `instance` is the tag PVE itself
emits for the drive id, so it is not wrong, but Prometheus uses `instance` for its own scrape
target, and many Telegraf configurations rename or overwrite one of the two. Find out which one
survived in your deployment before anything downstream joins on it.

[`docs/manual/20-verifying-metrics.md`](docs/manual/20-verifying-metrics.md) explains every
finding and what to do about it.

### Step 5 — look at the cluster

```sh
pve-storage-drs -c /etc/pve/drs.yaml show-load          # per storage: disks, sizes, load, reserve
pve-storage-drs -c /etc/pve/drs.yaml verify-storages    # saferemove, wipe times, pattern expansion
```

`show-load` is where you find out whether the numbers describe the cluster you think you have. It
also prints a per-group act/no-act verdict with its reasoning, so you can see what a `plan` would
decide before you ask for one.

### Step 6 — compute a plan

```sh
pve-storage-drs -c /etc/pve/drs.yaml plan
pve-storage-drs -c /etc/pve/drs.yaml explain    # the same plan, narrated
```

`plan` never executes anything, in any mode. `explain` runs the identical pipeline and then
narrates what `plan`'s output does not print: every disk pinned this run and why, VMs a pin leaves
spread across storages, the objective's five terms individually, the payback arithmetic, and —
when a group's gate said "act" but the solver still chose to move nothing — the closest move it
rejected and what it would have cost. That last one answers the most common question this tool
gets asked.

### Step 7 — apply it ⚠️ this one migrates data

```sh
pve-storage-drs -c /etc/pve/drs.yaml --mode confirm apply    # asks before each move
```

That `--mode confirm` is you selecting a less safe mode, which is the only thing that makes
`apply` do more than `plan` printed. `confirm` prompts per move, so nothing happens without a
second decision from you; `auto` does not prompt, and additionally honours
`execution.time_windows` and `execution.max_migrations_per_run`. With `execution.mode` left at its
`dry-run` default, `apply` with no `--mode` stays a dry run.

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
migration with its PVE task UPID — without needing `-v`, as JSON, because under a timer that log
is the only record of what happened to your cluster. Two options suppress it and neither belongs
in a timer unit: `--quiet` and `--log-level error`. See
[`docs/manual/35-logging.md`](docs/manual/35-logging.md).

To have your monitoring system watch an unattended run, set `monitoring.status_file`: `apply` then
leaves a status report in the format of the `check_statusfile` Nagios plugin
(`monitoring-plugins-contrib`) after **every** run — `OK`, `WARNING` (it gave up after too many outside
changes, or a group is still short of its reserve) or `CRITICAL` (a move failed, or PVE or Prometheus
could not be read) — and its modification time tells the plugin the timer is still firing. See
[`docs/manual/36-monitoring.md`](docs/manual/36-monitoring.md).

### Things worth knowing at this point

- `--group NAME` (repeatable) restricts a `show-load`, `verify-storages`, `plan`, `explain` or
  `apply` run to one storage group; `verify-metrics` and `collect-testdata` are cluster-wide and
  ignore it. Groups are independent, so this never changes the answer for the groups you selected.
- `--json` emits the machine-readable report on **stdout**; logs always go to **stderr**, so
  `pve-storage-drs --json plan > plan.json` is safe.
- `--replay BUNDLE` runs the whole engine offline against a captured bundle — see
  [Contributing test data](#contributing-test-data).
- `pve-storage-drs --help`, `pve-storage-drs <command> --help` and `man pve-storage-drs` always
  carry the exact current option list and every default.

---

## The metrics pipeline

📖 **[`docs/manual/05-metrics-pipeline.md`](docs/manual/05-metrics-pipeline.md) is the page on
this.** Read it before writing the `metrics` config block. What follows is the short version, and
it is here rather than only there because it decides whether this tool can work on your cluster at
all.

`pve-storage-drs` collects nothing itself and ships no exporter. It reads six per-disk counters
out of a Prometheus-compatible backend you already run — QEMU `query-blockstats` figures that
`pvestatd` already gathers and PVE's **InfluxDB external metric server** already exports, with the
drive id carried as a label. So the data exists cluster-wide before this tool is installed. What
varies is **what survives the trip**, and getting that wrong is the most common way to get a
confidently wrong answer out of this tool.

The mechanism, in one paragraph: InfluxDB line protocol carries string fields and fixes a field's
type at its first write, while Prometheus and OpenMetrics have no string sample type. A transport
between the two can therefore drop one of the six counters — for one disk, permanently, silently —
while the other five keep working. Nothing errors, your dashboards keep drawing, and this tool
reads the gap as "that disk does no writes". **Telegraf with a Prometheus remote-write or
OpenMetrics output is the prominent example**, because it is what most people build first and it
needs deliberate processor configuration to avoid this. `verify-metrics` cross-checks the six
metrics against each other precisely to catch it.

A backend that ingests **the InfluxDB protocol exactly as PVE exports it** and serves PromQL itself
has no such bridge to lose a field in — no Telegraf, no output plugin, nothing in the path that can
drop a field on type grounds. **[gigapipe](https://github.com/metrico/gigapipe) on ClickHouse** is
the well-tested setup here, and the one this project is dogfooded against; point `prometheus.url`
at its query endpoint. (It also ingests OpenTelemetry, but that path is untested here, and PVE's
OTel metric server is the wrong source for this tool regardless — it bakes the drive id into the
metric name instead of a label.) Plain Prometheus and VictoriaMetrics work too; `prometheus.url` is
the only setting that distinguishes them.

---

## Status

Implemented and dogfooded against a production cluster. All eleven phases of
`IMPLEMENTATION_PLAN.md` §12 are done — from reading the cluster and Prometheus, through the
gates, the solver (CP-SAT or CBC when installed, a dependency-free heuristic otherwise), move
ordering and execution, to Debian packaging, the `collect-testdata` / `--replay` diagnostic-bundle
subsystem and the §2.3 logging policy. Every command, including `apply`'s unattended `auto` mode
and `explain`'s narration of the pins, fragmentation and payback arithmetic behind a plan, is
implemented and covered by the test suite.

[`docs/manual/30-safety-and-status.md`](docs/manual/30-safety-and-status.md) is the authoritative,
per-command status table — trust that over any impression given elsewhere. `REVIEW.md` is a
standing external review of both the plan and the implementation; findings are tracked to
resolution with stable IDs that the code and commit messages refer back to.

## Configuration

`groups[].storages[]` names the storages a disk may move between — literal PVE storage ids, or a
`/regex/` pattern that is matched against the cluster's storage inventory on every run, so a LUN
added later joins its group with no config edit. Everything else — the load model's weights, the
gates that decide *whether* a group needs to act, the snapshot reserve, the objective the solver
optimizes, cooldowns, execution concurrency and time windows — has a documented default and can be
left alone until you have a reason to change it.

[`config/drs.example.yaml`](config/drs.example.yaml) is the full annotated reference: every key,
its default, and why it exists, in the order `10-configuration.md` documents them.
[`docs/manual/10-configuration.md`](docs/manual/10-configuration.md) is the prose version of the
same thing, one section per key. Both are generated from — and must never drift from — the actual
defaults in `config.py` and what `--help` prints (`.agents/documentation.md`).

## Contributing test data

**Pull requests carrying real-cluster test data are very welcome — arguably more welcome than
code.** The interesting failures this tool has had came from clusters behaving in ways no
synthetic fixture anticipated, and a bug report *describes* a failure while a bundle *reproduces*
it, offline, forever. A synthetic fixture can prove the solver optimal on six disks; only a real
cluster can prove the MILP and the heuristic still agree at three hundred. Every bundle in
`tests/corpus/` today came from the author's own cluster, which is exactly the limitation a
submission from yours would fix.

`collect-testdata` captures one:

```sh
pve-storage-drs -c /etc/pve/drs.yaml collect-testdata --estimate   # what it would fetch
pve-storage-drs -c /etc/pve/drs.yaml collect-testdata              # capture it
```

It is read-only by construction and never issues `move_disk`; passing `--mode confirm`/`--mode
auto` alongside it is a usage error rather than a silently ignored flag. `--estimate` prints the
query and sample-point count first and fetches nothing; the capture itself refuses outright above
`support.max_series_points` rather than hammering your Prometheus. Useful flags: `--range`/`--step`
to bound the series capture, `--no-series` for topology and instant queries only, `-o` for
somewhere else.

It writes two forms of the same bundle under `support.bundle_dir`: a **directory**, which is what
you read and what gets committed, and a deterministic **`.tar.gz`** of it, which is what you
attach to a mail or an issue. Exit status `1` with the bundle still written means the manifest
recorded a failed API call — usually a permission gap — not that the capture is unusable.

Replay it yourself before sending it anywhere — the bundle is the whole input, so this is not a
sanity check but the actual proof that it reproduces:

```sh
pve-storage-drs --replay /var/lib/pve-storage-drs/testdata/<bundle> plan
pve-storage-drs --replay /var/lib/pve-storage-drs/testdata/<bundle> explain
```

`--replay` opens **no network connections at all** — not to PVE, not to Prometheus — and uses the
bundle's own `config.yaml` unless you override it with `-c`, which lets you rerun somebody else's
cluster through a different solver backend, spread metric or forecaster.

### What a bundle does and does not hide

Every identifier — node, storage, VM, volume, pool, tag, user, task id — is replaced by a
pseudonym keyed to an HMAC salt that **stays on your host and never enters the bundle**. Fields are
copied by **allowlist**: anything the engine does not read is not captured, which is where
operator-authored free text (VM names, descriptions, snapshot names, comments) lives. No hostname,
IP, IQN, fingerprint, key or password survives.

It is **not anonymous against somebody who already knows your cluster.** Node, storage and VM
counts, capacities, disk sizes and load shapes all survive — they are what makes it a test case —
and together they are a recognizable fingerprint.

So: **open the bundle and read it before you send it.** It is sorted, indented JSON, written to be
read. If your cluster's mere size and shape is confidential, send a `--no-series` bundle or just a
description instead — a description is still worth having.

### Submitting one

[`tests/corpus/README.md`](tests/corpus/README.md) is the full submission guide. In short: a
bundle must be under **8 MiB unpacked** to be committed (larger ones live outside the repo, found
via `DRS_CORPUS_DIR`), and must come with a `<bundle>.submission.yaml` recording who collected it,
what it reproduces, that you read it, and that you consent to it being redistributed under
AGPL-3.0-or-later. Accepting a bundle makes it public permanently, in git history; a bundle whose
submitter did not review it does not get committed, however clean the automated scrub audit says
it is.

Every committed bundle is then part of `make check`: a scrub audit that assumes the collector has
a bug, the domain invariants re-asserted against real data, MILP-versus-heuristic agreement, and a
generated `<bundle>.expected.json` regression baseline.

## Documentation

| What | Where |
|---|---|
| Quick start, this file | you are reading it |
| Operator manual (installation, configuration, every command, logging, safety guarantees and exit codes) | [`docs/manual/`](docs/manual/) (Markdown, one file per topic) or [`docs/pve-storage-drs-manual.pdf`](docs/pve-storage-drs-manual.pdf) (typeset) |
| `pve-storage-drs(1)` manpage | `man pve-storage-drs` once installed, or [`man/pve-storage-drs.1.md`](man/pve-storage-drs.1.md) in source |
| `--help` | always current, generated from the same argument definitions the manual and manpage describe |
| Full specification (the data model, the optimization problem, every formula and invariant) | [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md), or [`docs/IMPLEMENTATION_PLAN.pdf`](docs/IMPLEMENTATION_PLAN.pdf) typeset with a title page and table of contents |
| Internals guide, for whoever changes the code | [`docs/internals/`](docs/internals/) (Markdown, one file per module) or [`docs/internals.pdf`](docs/internals.pdf) (typeset) |
| Submitting real-cluster test data | [`tests/corpus/README.md`](tests/corpus/README.md) |
| External review of the plan and the implementation | [`REVIEW.md`](REVIEW.md) — stable finding IDs the plan/code/commits refer back to |
| Worked example / test fixtures | [`tests/fixtures/fc-tier1.yaml`](tests/fixtures/fc-tier1.yaml) (§14's example, machine-readable) and [`tests/fixtures/reserve-tradeoff.yaml`](tests/fixtures/reserve-tradeoff.yaml) (a deliberately adversarial second group); both have `*.expected.json` proven-optimal results, regenerated by `python3 tests/fixtures/generate_expected.py` (`--check` to assert they are current) |
| Working agreement for contributors (human or agent) | [`AGENTS.md`](AGENTS.md) and [`.agents/`](.agents/) |

Installed, all of it lands under `/usr/share/doc/pve-storage-drs/`: the Markdown sources under
`manual/` and `internals/`, plus `IMPLEMENTATION_PLAN.md`, and the three typeset PDFs beside them.
A cluster node has no GUI and often no way to get a PDF off it, so the Markdown is shipped
uncompressed and is not an afterthought —
`less /usr/share/doc/pve-storage-drs/manual/20-verifying-metrics.md` is the expected way to read
this on the machine that actually has the problem.

All three PDFs are generated from those Markdown sources by `make docs` (`make pdf`/`internals`/
`manual` individually) and kept in step by `make docs-check`, part of `make check`; each PDF's
title page carries the SHA-256 of the Markdown it was built from.

## Requirements

### To run it

- Proxmox VE 9.2 cluster with shared storages (LVM/FC, Ceph RBD, or another shared type)
- A Prometheus-compatible backend already receiving PVE's per-disk `blockstat` series via the
  **InfluxDB external metric server** — plain Prometheus, VictoriaMetrics, or
  [gigapipe](https://github.com/metrico/gigapipe) on ClickHouse, which is what this project is
  dogfooded against. Read [The metrics pipeline](#the-metrics-pipeline) first: the transport
  between PVE and the backend is where metrics get lost.
- A PVE API user or token with `Datastore.Audit` **and `Datastore.Allocate`** on each managed
  storage, `VM.Audit` cluster-wide, and — once `apply` executes — `VM.Config.Disk` and
  `VM.Migrate`. `Datastore.Audit` alone is not enough and fails silently; see
  [`docs/manual/00-installation.md`](docs/manual/00-installation.md) and
  [Step 2](#step-2--grant-a-pve-credential) above for why

### To work on it

- Python 3.11+ (`make venv` installs the rest into `.venv/`)
- `pandoc`, `lualatex` and `latexmk` — only needed to rebuild the PDFs. On Debian:
  `pandoc texlive-luatex texlive-latex-extra latexmk fonts-sil-gentiumplus fonts-dejavu-core
  fonts-dejavu-mono fonts-symbola`
- `ortools` and/or `pulp` (with `coinor-cbc`) are optional `pip install .[solver]` extras for the
  CP-SAT/CBC solver backends; the tool works fully without them, falling back to a dependency-free
  heuristic (`solver.backend: auto`, the default, tries them in that order)

## Packaging

The tool is delivered as the Debian package `pve-storage-drs`, built from `debian/` in this repository and
targeting **Debian trixie**, the base of Proxmox VE 9.x. Dependencies are chosen for being packaged
in trixie, so the package installs on a management host with no outbound network; `debian/tests`
installs the built package on a system carrying only its `Depends` and proves the command runs.

```sh
apt install pve-storage-drs   # once added to a repository you control
make deb                      # local build; CI builds it in a debian:trixie container and with sbuild
```

Two pipelines: GitHub Actions runs lint, types, tests and coverage in `debian:trixie` with the
Debian-packaged toolchain, builds the package and installs it; GitLab CI (`debian/.gitlab-ci.yml`)
runs Debian's Salsa pipeline — sbuild without network, then lintian, piuparts, reprotest and
autopkgtest. [`.agents/packaging.md`](.agents/packaging.md) explains both.

## Contributing

[`AGENTS.md`](AGENTS.md) is the working agreement for this repository — for humans and for
agents alike. It covers the toolchain (black + flake8 + mypy + pytest, all configured not to
disagree with each other), the 85 % coverage floor, the branch-and-merge-on-green workflow, the
documentation the project owes its users, and the domain rules that must not be refactored away.
[`.agents/`](.agents/) holds the long form.

```sh
make venv     # bootstrap .venv with the dev tooling
make check    # format, lint, types, tests, coverage, fixture, corpus and PDF freshness
make docs     # re-render the PDFs and the manpage after editing them
```

`make SYSTEM_TOOLS=1 <target>` runs the same targets against tools already on `PATH` instead of
`.venv`, which is how CI and the Debian build run them.

Test data is a contribution in its own right — see
[Contributing test data](#contributing-test-data) above.

## Licence

GNU Affero General Public License v3.0 or later — see [`LICENSE`](LICENSE).

Copyright © 2026 Bernd Zeimetz <bernd@bzed.de>

## AI disclaimer

This project was built with AI assistance at every stage. Planning and architecture — including
`IMPLEMENTATION_PLAN.md` itself — were done with Anthropic's
[Claude Opus 5](https://www.anthropic.com/claude), and the code, tests and documentation were
written with Anthropic's [Claude Sonnet 5](https://www.anthropic.com/claude). The result went
through two independent rounds of review: one by a human maintainer, and one by
[Z.ai](https://z.ai)'s GLM 5.3 model acting as a second, automated reviewer. `REVIEW.md` is the
standing record of both.
