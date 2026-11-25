<!--
SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
SPDX-License-Identifier: AGPL-3.0-or-later

The landing page of the GitHub Pages site. Unlike the pages it links to,
which are the repository's documentation rendered verbatim, this file exists
only for the site -- but it is held to the same standard (AGENTS.md section
8.0): it explains what the tool is from what is on the page, and links to the
documents that carry the detail.
-->

# proxmox-storage-drs

A replacement for VMware's Storage DRS, for Proxmox VE 9.2.

The Dynamic Load Balancer that PVE 9.2 ships moves guests between nodes to
even out CPU and memory. It has no notion of the LUNs behind them. This
tool is the **storage** counterpart to it. It never moves a guest. It moves
individual disks between storages. The command is `pve-storage-drs`, named
to keep the two from being confused.

It balances **disk I/O load across configurable groups of shared storages**.
The storage types are LVM/FC, Ceph RBD, or any other shared storage type PVE
supports. The tool live-migrates individual VM disks between storages within
a group. It guarantees a snapshot free-space reserve. It performs as few
migrations as possible.

## The safety properties to rely on

- **Dry-run is the default.** `apply` does nothing beyond what `plan`
  printed, until `execution.mode` or `--mode` moves it off the dry-run
  default. It is the only command with a code path that can write to the
  cluster.
- **The tool never trades the snapshot reserve for balance.** A migration
  plan that spends the free-space reserve during a move is rejected
  outright. The tool does not weight it against the load the plan would
  fix.
- **The tool never deletes anything automatically.** It reports volumes
  left behind by a failed move. The tool never removes them.

The [safety and status page](manual/30-safety-and-status.md) spells out the
full list, the exit codes, and which parts of it this build actually
implements.

## The documents

| Audience | Document |
|---|---|
| Somebody running the tool | [**Operator manual**](manual/00-installation.md) — installation, configuration reference with every knob, the verification commands, how to read `plan` and `apply`, troubleshooting |
| Whoever changes the code | [**Internals**](internals/00-overview.md) — the data path end to end: metrics in, load vector, gates, solver, scheduler, executor, `state.json` out |

Both ship as PDFs inside the Debian package too. The site is built from the
same Markdown as those, in CI, on every push. It cannot drift from what the
package contains.

The [implementation plan](https://github.com/bzed/proxmox-storage-drs/blob/main/IMPLEMENTATION_PLAN.md)
is deliberately not on the site. The plan is the full specification the tool
implements, with every design derivation. The plan is addressed to whoever
builds or changes the tool, rather than to whoever runs it. It lives in the
repository and as a PDF in the package.

## Getting the tool

Every release is published as a ready-built Debian package on the
[GitHub releases page](https://github.com/bzed/proxmox-storage-drs/releases).
The [operator manual](manual/00-installation.md) holds the installation
walkthrough and the prerequisites: a PVE 9.2 cluster, a Prometheus carrying
PVE's per-disk `blockstat` series, and a credential.

The source is AGPL-3.0-or-later, at
[bzed/proxmox-storage-drs](https://github.com/bzed/proxmox-storage-drs).
