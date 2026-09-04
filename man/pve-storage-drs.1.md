% PVE-STORAGE-DRS(1) pve-storage-drs @VERSION@ | Proxmox Storage DRS
%
% @DATE@

# NAME

pve-storage-drs - balance disk I/O across Proxmox VE shared storages

# SYNOPSIS

**pve-storage-drs** \[*global options*\] *command* \[*command options*\]

# DESCRIPTION

**pve-storage-drs** equalizes disk I/O load across configurable groups of shared storages in a Proxmox VE
cluster by live-migrating individual VM disks between the storages of a group. It reads the
historical per-disk load from an existing Prometheus and the cluster topology from the Proxmox VE
API, solves for a placement, and either prints the resulting plan or executes it with
**move_disk**.

Two properties are guaranteed and are not configurable away. Every storage keeps free space for
snapshots -- by default twice its largest disk -- and that reserve holds *during* a migration, not
merely before and after it, because a mirrored disk occupies both storages until the move
completes. And a plan whose own migration cost exceeds the imbalance it removes is rejected
outright rather than merely penalized.

The default mode is **dry-run**: **pve-storage-drs** prints the plan, the arithmetic behind it and the API
calls it would issue, and changes nothing. Nothing is ever deleted automatically.

The configuration is read from */etc/pve/drs.yaml*, which is on the cluster filesystem and so is
the same file on every node.

# COMMANDS

**plan**
: Compute and print a migration plan. Does not execute it.

**apply**
: Execute a plan, subject to *execution.mode*, the concurrency caps and the time windows.

**show-load**
: Print every storage in every group with its disks, sizes, measured load and reserve status.

**explain**
: Say why the tool did what it did: which gate stopped it, why a disk is pinned, why a move was
  deferred, and the payback arithmetic behind an accepted or rejected plan.

**verify-metrics**
: Validate the configured metric and label names against the live Prometheus and print a sample
  series. Run this before relying on any plan; Telegraf and InfluxDB naming varies by deployment.

**verify-storages**
: Report per storage: type, shared flag, content types, **saferemove** and its throughput, capacity
  and the largest disk on it, and warn where the implied wipe time exceeds the configured move
  duration or storage cooldown.

# OPTIONS

Global options are accepted before the command.

**-c**, **--config** *PATH*
: Read the configuration from *PATH* instead of */etc/pve/drs.yaml*. A file named here that is
  missing, unreadable or invalid is an error; **pve-storage-drs** never falls back to the default.
  The environment variable **PVE_STORAGE_DRS_CONFIG** has the same effect and lower precedence.

**--group** *NAME*
: Restrict the run to one storage group. May be given more than once. Groups are independent, so
  this does not change the result for the groups selected.

**--mode** *dry-run*|*confirm*|*auto*
: Override *execution.mode* for this run. Every override is logged; one that moves toward less
  safety -- the modes order **dry-run** < **confirm** < **auto** -- is logged at warning level,
  naming both values, because it removes a barrier the operator themselves configured.

**--json**
: Emit the machine-readable report instead of the human-readable one.

**-v**, **--verbose**
: More detail on stderr. Repeatable.

**--quiet**
: Warnings and errors only. Intended for the systemd timer.

**--version**
: Print the version and exit.

**--manual**
: Show this manual page.

**-h**, **--help**
: Print a usage summary with every option and its default, and exit. **pve-storage-drs** *command*
  **--help** does the same for one command.

# CONFIGURATION

*/etc/pve/drs.yaml*, searched for in this order: **--config**, then **$PVE_STORAGE_DRS_CONFIG**, then the
default path. It is validated in full at startup; every violation is a fatal error with a message
naming the setting, because a misconfigured balancer that moves production disks is worse than one
that refuses to start.

Top-level keys: **proxmox** (API connection and credentials), **prometheus** (URL and auth),
**metrics** (metric and label name mapping), **window** (how much history to consider),
**groups** (the storage groups, which are what a disk may not leave), **snapshot_reserve**,
**load** (the weighting of I/O time, operations and bytes), **objective** (the solver's trade-off
weights), **gates** (drift and imbalance thresholds, cooldowns), **migration** (bandwidth, cost and
payback), **execution** (mode, concurrency, time windows, locking), **exclude**, **report**,
**state** and **forecast**.

Every option is documented individually, with its unit, its default and what happens at either
extreme, in the manual listed under **SEE ALSO**. That document, not this page, is authoritative
for configuration.

Because */etc/pve* is replicated by the cluster filesystem, an edit is live on every node
immediately. Files there are group-readable by the web server, so keep credentials out of the file
and in **PVE_PASSWORD** or **PVE_TOKEN_SECRET**, and prefer an API token over a password.

# ENVIRONMENT

**PVE_STORAGE_DRS_CONFIG**
: Path to the configuration file. Overridden by **--config**.

**PVE_PASSWORD**, **PVE_TOKEN_SECRET**
: Proxmox VE credentials, so that they need not be written into the configuration file.

# FILES

*/etc/pve/drs.yaml*
: The configuration. Cluster-replicated.

*/var/lib/pve-storage-drs/state.json*
: Cooldowns, the load vector at the last balance, in-flight task ids and the run lock. Node-local
  and deliberately not on */etc/pve*: it is rewritten on every run. Losing it is safe but resets
  the cooldowns.

*/usr/share/doc/pve-storage-drs/*
: The manual and the specification.

# EXIT STATUS

0
: Success. A run that stopped at a gate, or found nothing worth moving, also exits 0 -- that is the
  normal outcome for most invocations of the timer.

1
: The run failed: configuration invalid, Prometheus or the Proxmox VE API unreachable, a migration
  failed, or the solver produced nothing usable.

2
: Usage error on the command line.

# SEE ALSO

*/usr/share/doc/pve-storage-drs/pve-storage-drs-manual.pdf*, the operator manual, which documents every
configuration option in detail.

*/usr/share/doc/pve-storage-drs/IMPLEMENTATION_PLAN.pdf*, the specification, for the load model, the
optimization problem and the migration ordering rules.

**pvesm**(1), **qm**(1), **pvecm**(1).

# AUTHOR

Bernd Zeimetz, bernd@bzed.de.

# COPYRIGHT

Copyright (C) 2026 Bernd Zeimetz. Licensed under the GNU Affero General Public License, version 3
or later. There is NO WARRANTY, to the extent permitted by law.
