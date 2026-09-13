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

The six per-disk counters every plan is computed from are QEMU `query-blockstats` figures that
**pvestatd** already exports through PVE's InfluxDB external metric server; no exporter or
collector is installed by this tool. Because the InfluxDB protocol PVE exports carries string
fields and fixes a field's type at its first write, while Prometheus has no string sample type, a
transport between the two -- Telegraf with a Prometheus remote-write or OpenMetrics output being
the prominent case -- can silently and permanently drop one counter for one disk while the other
five keep working. That produces a wrong plan rather than an error, which is why **verify-metrics**
cross-checks all six against each other and should be run before any plan is trusted. A backend
that ingests PVE's InfluxDB output as-is and serves PromQL itself has no such bridge; gigapipe on
ClickHouse is the tested example, and is what this tool is dogfooded against. The operator manual's
"Where the numbers come from" page has the mechanism in full.

The configuration is read from */etc/pve/drs.yaml*, which is on the cluster filesystem and so is
the same file on every node.

# COMMANDS

**plan**
: Compute and print a migration plan. Does not execute it.

**apply**
: Execute a plan, subject to *execution.mode*. *dry-run* and *confirm* run the plan/schedule/payback
  pipeline once and either print or execute it. *auto* additionally honours
  *execution.time_windows* and *execution.max_migrations_per_run*, and re-plans from freshly
  observed cluster state (bounded by *execution.max_replans_per_run*) if a move mismatches what a
  concurrent change to the cluster expected -- see the operator manual.

**show-load**
: Print every storage in every group with its disks, sizes, measured load and reserve status.

**explain**
: Run the identical gate/solve/schedule/payback pipeline **plan** does, and narrate what its output
  does not print: the measured load every number derives from (**show-load**'s own per-storage/
  per-disk picture), every disk pinned this run with its exact reason, any VM a pin leaves with disks
  spread across more than one storage ("cannot fully consolidate"), the section 5.4 objective's five
  terms individually, and pinned load as a fraction of the group's total against
  *report.warn_pinned_load_fraction* -- flagging a residual imbalance likely too structural (too
  much load pinned) for another run of **plan** to fix by itself. **-v** additionally names the
  exact Prometheus query (node-scoping filter, window and rate settings) the whole run was
  computed from.

**verify-metrics**
: Validate the configured metric and label names against the live Prometheus and print a sample
  series. Run this before relying on any plan; Telegraf and InfluxDB naming varies by deployment.

**verify-storages**
: Report per storage: type, shared flag, content types, **saferemove** and its throughput, capacity
  and the largest disk on it, and warn where the implied wipe time exceeds the configured move
  duration or storage cooldown.

**collect-testdata**
: Capture an anonymized diagnostic bundle -- topology, the effective configuration with credentials
  and endpoints removed, and Prometheus metrics -- for the author to reproduce a problem offline.
  Read-only and dry-run-only: **--mode confirm**/**auto** alongside it is a usage error. Every
  identifier is replaced by a pseudonym keyed to a salt that stays on the host; sizes, capacities
  and load shapes are preserved, so a bundle is not anonymous against somebody who already knows
  the cluster. Read it before sending it. Its own options are listed under **COLLECT-TESTDATA
  OPTIONS** below. Exit status is *0* when every capture step succeeded and *1* when the bundle was
  written but its manifest records a failed call.

**help**
: Alias for **--manual**.

# OPTIONS

Global options are accepted before the command.

**-c**, **--config** *PATH*
: Read the configuration from *PATH* instead of */etc/pve/drs.yaml*. A file named here that is
  missing, unreadable or invalid is an error; **pve-storage-drs** never falls back to the default.
  The environment variable **PVE_STORAGE_DRS_CONFIG** has the same effect and lower precedence.

**--group** *NAME*
: Restrict the run to one storage group. May be given more than once. Groups are independent, so
  this does not change the result for the groups selected. A name that does not match any group
  in the configuration is a hard failure (exit code 1), not a silently empty report. Applies to
  **show-load**, **verify-storages**, **plan**, **explain** and **apply**; **verify-metrics** and
  **collect-testdata** are cluster-wide and are not restricted by this flag.

**--mode** *dry-run*|*confirm*|*auto*
: Override *execution.mode* for this run. Every override is logged; one that moves toward less
  safety -- the modes order **dry-run** < **confirm** < **auto** -- is logged at warning level,
  naming both values, because it removes a barrier the operator themselves configured.

**--json**
: Emit the machine-readable report instead of the human-readable one.

**-v**, **--verbose**
: **-v** logs this run's decision trail on stderr -- the gate decision and the thresholds it was
  compared against, the measured load, the plan and its objective terms, the payback arithmetic, and
  every migration with its PVE task UPID. **-vv** adds per-query detail and third-party library
  logs. **explain** is the one command where **-v** also adds a line to the report itself, on
  stdout: the exact query (node-scoping filter, window and rate settings) the run was computed from.

: By default nothing is logged below warning level, so a run in which nothing went wrong prints
  only its report. An **apply** run in **confirm** or **auto** mode is the exception: it logs the
  decision trail above whether or not **-v** was given, because in those modes that log is the only
  record of what was migrated and why.

**--quiet**
: Errors only. On an **auto** run this also discards the audit trail described under **-v**, which
  is the only record of what that run moved -- prefer the default over **--quiet** under a timer.

**--log-level** *error|warning|info|debug*
: Set the log level explicitly. Wins over both **-v** and **--quiet** -- except that on an
  **apply** run in **confirm**/**auto** mode, a level below the mandatory audit-trail floor
  (**info**) is raised back up to it. **--quiet** is the only way to discard that record.

**--log-format** *auto|text|json*
: **auto** (the default) writes human-readable text when stderr is a terminal and one JSON object
  per line anywhere else -- a pipe, a redirect, or journald under systemd. **text** and **json**
  force one or the other. The report on stdout is unaffected; see **--json** for that.

**--version**
: Print the version and exit.

**--manual**
: Show this manual page.

**--replay** *PATH*
: Run against a **collect-testdata** bundle at *PATH* instead of the live cluster -- no network
  access at all. The bundle's own *config.yaml* is used unless **--config** is also given, in which
  case its knobs run against the bundle's data (a different solver backend, spread metric or
  forecaster than the operator who captured it selected). **apply** and any **--mode** above
  *dry-run* are a usage error under **--replay**; so is **collect-testdata** itself, which needs a
  live cluster.

**-h**, **--help**
: Print a usage summary with every option and its default, and exit. **pve-storage-drs** *command*
  **--help** does the same for one command.

# COLLECT-TESTDATA OPTIONS

Accepted only after the **collect-testdata** command. No other subcommand takes options of its own.

**-o**, **--output** *DIR*
: Write the bundle directory and its tarball to *DIR* instead of *support.bundle_dir*.

**--estimate**
: Print the query count and the estimated number of series sample points, then exit. Fetches
  nothing. A real capture refuses outright, rather than starting, above *support.max_series_points*.

**--range** *DURATION*
: Range of the series capture, overriding *support.capture_range*. The default captures the
  superset every supported forecaster could need, not only the configured one.

**--step** *DURATION*
: Resolution of the series capture, overriding *metrics.step*. Coarsening this is the other way to
  bring an oversized capture under the limit.

**--no-series**
: Capture topology, instant queries and findings only. Much smaller, but the bundle cannot exercise
  a seasonal forecaster. This is the form to send if the cluster's load shape is confidential.

**--no-archive**
: Write the bundle directory only, skipping the deterministic *.tar.gz*.

**--salt-file** *PATH*
: Use the anonymization salt at *PATH* instead of *support.salt_path*.

**--new-salt**
: Generate a fresh salt, replacing the persisted one. Logged at warning level: bundles made before
  and after no longer share a pseudonym mapping, so the same cluster no longer compares against
  itself.

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
**state**, **forecast** and **support** (the anonymization salt and defaults for
**collect-testdata**).

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

*/usr/share/doc/pve-storage-drs/manual/*, */usr/share/doc/pve-storage-drs/internals/*
: The operator manual and the internals guide, as uncompressed Markdown, one file per topic --
  readable with **less**(1) on a node with no GUI. Typeset PDFs of both, and of the specification
  (*IMPLEMENTATION_PLAN.md*), sit beside them in */usr/share/doc/pve-storage-drs/*.

*/var/lib/pve-storage-drs/anonymization-salt*
: **collect-testdata**'s pseudonym key, generated on first use, mode 0600. Never written into a
  bundle. **--new-salt** rotates it; bundles made before and after no longer share a mapping.

*/var/lib/pve-storage-drs/testdata/*
: Default **collect-testdata** output directory (**support.bundle_dir**, **-o**/**--output**).

# EXIT STATUS

0
: Success. A run that stopped at a gate, or found nothing worth moving, also exits 0 -- that is the
  normal outcome for most unattended invocations. (No timer unit is shipped; write your own, or
  run it from cron, on exactly one host -- */var/lib/pve-storage-drs/state.json* is node-local.)

1
: The run failed: configuration invalid, Prometheus or the Proxmox VE API unreachable, a migration
  failed, or the solver produced nothing usable.

2
: Usage error on the command line.

# SEE ALSO

*/usr/share/doc/pve-storage-drs/manual/* (or *pve-storage-drs-manual.pdf*), the operator manual,
which documents every configuration option in detail. Start with *05-metrics-pipeline.md* if
**verify-metrics** reported anything, and *35-logging.md* before writing a systemd unit.

*/usr/share/doc/pve-storage-drs/IMPLEMENTATION_PLAN.md* (or *.pdf*), the specification, for the load
model, the optimization problem and the migration ordering rules.

<https://github.com/bzed/proxmox-storage-drs> -- bug reports, and diagnostic bundles collected with
**collect-testdata**, which are welcome as pull requests on the terms in *tests/corpus/README.md*.

**pvesm**(1), **qm**(1), **pvecm**(1).

# AUTHOR

Bernd Zeimetz, bernd@bzed.de.

# COPYRIGHT

Copyright (C) 2026 Bernd Zeimetz. Licensed under the GNU Affero General Public License, version 3
or later. There is NO WARRANTY, to the extent permitted by law.
