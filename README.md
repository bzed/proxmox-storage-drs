# proxmox-storage-drs

[![Proxmox](https://img.shields.io/badge/Proxmox-E57000?style=for-the-badge&logo=proxmox&logoColor=white)](https://proxmox.com/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/bzed/proxmox-storage-drs)
[![Tests](https://github.com/bzed/proxmox-storage-drs/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/bzed/proxmox-storage-drs/actions/workflows/tests.yml)
[![Debian Package](https://github.com/bzed/proxmox-storage-drs/actions/workflows/debian-package.yml/badge.svg?branch=main)](https://github.com/bzed/proxmox-storage-drs/actions/workflows/debian-package.yml)
[![codecov](https://codecov.io/gh/bzed/proxmox-storage-drs/branch/main/graph/badge.svg)](https://codecov.io/gh/bzed/proxmox-storage-drs)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

A Storage DRS replacement for Proxmox VE 9.2.

It is the **storage** counterpart to the Dynamic Load Balancer that PVE 9.2 ships: that one moves
guests between nodes to even out CPU and memory, and has no notion of the LUNs behind them. This
one never moves a guest — it moves individual disks between storages. The command is
`pve-storage-drs`, named to keep the two from being confused.

It balances **disk I/O load across configurable groups of shared storages** (LVM/FC, Ceph RBD, or
any other shared storage type PVE supports) by live-migrating individual VM disks between storages
within a group, while guaranteeing a snapshot free-space reserve and performing as few migrations
as possible.

## Status

Implemented and dogfooded against a production cluster. `IMPLEMENTATION_PLAN.md` section 12's nine
phases are all done: reading the cluster and Prometheus, deciding whether a group needs to act,
solving for a placement (CP-SAT or CBC when installed, a dependency-free heuristic otherwise),
ordering and executing the moves, and Debian packaging. The one command not yet implemented is
`explain` (which will narrate the payback arithmetic behind a plan) — every other command,
including `apply`'s unattended `auto` mode, is implemented and covered by the test suite.

[`docs/manual/30-safety-and-status.md`](docs/manual/30-safety-and-status.md) is the authoritative,
per-command status table — trust that over any impression given elsewhere. `REVIEW.md` is a
standing external review of both the plan and the implementation; findings are tracked to
resolution with stable IDs that the code and commit messages refer back to.

## Quickstart

1. **Install** the Debian package on a management host or a cluster member (see
   [Packaging](#packaging) below), or run from a checkout with `make venv`.
2. **Grant a PVE credential** the privileges the tool needs — this is the one step worth reading
   in full before anything else, because a too-narrow grant fails silently rather than with an
   error. See [`docs/manual/00-installation.md`](docs/manual/00-installation.md)'s "Setting up the
   PVE credential" section.
3. **Copy the example config** and edit it for your cluster:

   ```sh
   cp /usr/share/doc/pve-storage-drs/examples/drs.example.yaml /etc/pve/drs.yaml
   # or, from a checkout: cp config/drs.example.yaml /etc/pve/drs.yaml
   $EDITOR /etc/pve/drs.yaml
   ```

   At minimum, set `proxmox.host`/`proxmox.auth`, `prometheus.url`, and one `groups` entry naming
   at least two storages to balance between:

   ```yaml
   schema_version: 1
   proxmox:
     host: pve01.example.com
     auth:
       token_id: "drs@pve!balancer"
       token_secret: null   # set PVE_TOKEN_SECRET in the environment instead
   prometheus:
     url: http://prometheus.example.com:9090
   groups:
     - name: fc-tier1
       storages:
         - id: san-a
         - id: san-b
   ```

   Every key — including the many not shown here (gates, cooldowns, the objective weights, the
   snapshot reserve) — is documented with its default in
   [`config/drs.example.yaml`](config/drs.example.yaml) and in
   [`docs/manual/10-configuration.md`](docs/manual/10-configuration.md).

4. **Verify the metrics** the plan will be computed from actually exist under the names configured:

   ```sh
   pve-storage-drs -c /etc/pve/drs.yaml verify-metrics
   ```

5. **Look at the current state** before changing anything:

   ```sh
   pve-storage-drs -c /etc/pve/drs.yaml show-load
   pve-storage-drs -c /etc/pve/drs.yaml verify-storages
   ```

6. **Compute a plan** (never executes anything — this is always safe to run):

   ```sh
   pve-storage-drs -c /etc/pve/drs.yaml plan
   ```

7. **Apply it**, once the plan looks right. The default `execution.mode` is `dry-run`; `apply`
   only ever does more than `plan` printed once you explicitly configure or pass a less safe mode:

   ```sh
   pve-storage-drs -c /etc/pve/drs.yaml --mode confirm apply   # asks per move
   pve-storage-drs -c /etc/pve/drs.yaml --mode auto apply      # unattended, for a systemd timer
   ```

Every command also takes `--group NAME` (repeatable, restricts the run to one storage group),
`--json` (machine-readable output), `-v`/`--verbose`, and `--quiet`; `pve-storage-drs --help` or
`pve-storage-drs --manual` (equivalently, `man pve-storage-drs`) always carries the exact, current
option list and every default.

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

## Documentation

| What | Where |
|---|---|
| Quick start, this file | you are reading it |
| Operator manual (installation, configuration, every command, safety guarantees and exit codes) | [`docs/manual/`](docs/manual/) (Markdown, one file per topic) or [`docs/pve-storage-drs-manual.pdf`](docs/pve-storage-drs-manual.pdf) (typeset) |
| `pve-storage-drs(1)` manpage | `man pve-storage-drs` once installed, or [`man/pve-storage-drs.1.md`](man/pve-storage-drs.1.md) in source |
| `--help` | always current, generated from the same argument definitions the manual and manpage describe |
| Full specification (the data model, the optimization problem, every formula and invariant) | [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md), or [`docs/IMPLEMENTATION_PLAN.pdf`](docs/IMPLEMENTATION_PLAN.pdf) typeset with a title page and table of contents |
| Internals guide, for whoever changes the code | [`docs/internals/`](docs/internals/) (Markdown, one file per module) or [`docs/internals.pdf`](docs/internals.pdf) (typeset) |
| External review of the plan and the implementation | [`REVIEW.md`](REVIEW.md) — stable finding IDs the plan/code/commits refer back to |
| Worked example / test fixtures | [`tests/fixtures/fc-tier1.yaml`](tests/fixtures/fc-tier1.yaml) (section 14's example, machine-readable) and [`tests/fixtures/reserve-tradeoff.yaml`](tests/fixtures/reserve-tradeoff.yaml) (a deliberately adversarial second group); both have `*.expected.json` proven-optimal results, regenerated by `python3 tests/fixtures/generate_expected.py` (`--check` to assert they are current) |
| Working agreement for contributors (human or agent) | [`AGENTS.md`](AGENTS.md) and [`.agents/`](.agents/) |

All three PDFs are generated from their Markdown sources by `make docs` (`make pdf`/`internals`/
`manual` individually) and kept in step by `make docs-check`, part of `make check`; each PDF's
title page carries the SHA-256 of the Markdown it was built from.

## Requirements

### To run it

- Proxmox VE 9.2 cluster with shared storages (LVM/FC, Ceph RBD, or another shared type)
- A Prometheus (or VictoriaMetrics) instance already receiving PVE metrics via the
  **InfluxDB external metric server → Telegraf → Prometheus** path, carrying per-disk `blockstat`
  series (`rd_operations`, `wr_operations`, `rd_bytes`, `wr_bytes`, `rd_total_time_ns`,
  `wr_total_time_ns`)
- A PVE API user with permission to read cluster/storage/VM config and to run `move_disk` — see
  [`docs/manual/00-installation.md`](docs/manual/00-installation.md) for the exact privileges

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
make check    # format, lint, types, tests, coverage, fixture and PDF freshness
make docs     # re-render the PDFs and the manpage after editing them
```

`make SYSTEM_TOOLS=1 <target>` runs the same targets against tools already on `PATH` instead of
`.venv`, which is how CI and the Debian build run them.

## Licence

GNU Affero General Public License v3.0 or later — see [`LICENSE`](LICENSE).

Copyright © 2026 Bernd Zeimetz <bernd@bzed.de>
