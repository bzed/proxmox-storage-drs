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

It is the **storage** counterpart to the Dynamic Load Balancer that PVE 9.2
ships: that one moves guests between nodes to even out CPU and memory, and
has no notion of the LUNs behind them. This one never moves a guest — it
moves individual disks between storages. The command is `pve-storage-drs`,
named to keep the two from being confused.

It balances **disk I/O load across configurable groups of shared storages**
(LVM/FC, Ceph RBD, or any other shared storage type PVE supports) by
live-migrating individual VM disks between storages within a group, while
guaranteeing a snapshot free-space reserve and performing as few migrations
as possible.

## The safety properties to rely on

- **Dry-run is the default.** `apply` does nothing beyond what `plan` printed
  until `execution.mode` or `--mode` moves it off its dry-run default, and it
  is the only command with a code path that can write to the cluster.
- **The snapshot reserve is never traded for balance.** A migration plan that
  would spend the free-space reserve during a move is rejected outright, not
  weighted against the load it would fix.
- **Nothing is ever auto-deleted.** Volumes left behind by a failed move are
  reported, never cleaned up silently.

The [safety and status page](manual/30-safety-and-status.md) spells out the
full list, the exit codes, and which parts of it this build actually
implements.

## The documents

| Audience | Document |
|---|---|
| Somebody running the tool | [**Operator manual**](manual/00-installation.md) — installation, configuration reference with every knob, the verification commands, how to read `plan` and `apply`, troubleshooting |
| Whoever changes the code | [**Internals**](internals/00-overview.md) — the data path end to end: metrics in, load vector, gates, solver, scheduler, executor, `state.json` out |
| Both, and the curious | [**Implementation plan**](IMPLEMENTATION_PLAN.md) — the specification the tool implements, with the full design derivations |

The same three documents also ship as PDFs inside the Debian package, and the
site is built from the same Markdown as those — in CI, on every push, so it
cannot drift from what the package contains.

## Getting the tool

Every release is published as a ready-built Debian package on the
[GitHub releases page](https://github.com/bzed/proxmox-storage-drs/releases);
the installation walkthrough (and the prerequisites: a PVE 9.2 cluster, a
Prometheus carrying PVE's per-disk `blockstat` series, a credential) is in
the [operator manual](manual/00-installation.md).

The source is AGPL-3.0-or-later, at
[bzed/proxmox-storage-drs](https://github.com/bzed/proxmox-storage-drs).
