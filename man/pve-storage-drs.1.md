% PVE-STORAGE-DRS(1) pve-storage-drs @VERSION@ | Proxmox Storage DRS
%
% @DATE@

# NAME

pve-storage-drs - balance disk I/O across Proxmox VE shared storages

# SYNOPSIS

**pve-storage-drs** \[*global options*\] *command* \[*command options*\]

# DESCRIPTION

**pve-storage-drs** balances disk I/O load across configurable groups of shared storages in a
Proxmox VE cluster. The tool live-migrates individual VM disks between the storages of a group.
It reads the historical per-disk load from an existing Prometheus. It reads the cluster topology
from the Proxmox VE API. It solves for a placement. It then prints the plan, or it runs the plan
with **move_disk**.

The tool guarantees two properties. No setting turns them off. Every storage keeps free space
for snapshots. By default the reserve is twice the most space one VM's snapshot would need on
that storage, which is the sum of all of that VM's disks on the storage. The reserve holds
*during* a migration, not only before and after it. A mirrored disk uses both storages until the
move ends. The tool rejects a plan whose migration cost exceeds the imbalance the plan removes.

The default mode is **dry-run**. In this mode **pve-storage-drs** prints the plan, the
arithmetic behind it and the API calls it would issue. It changes nothing. The tool never
deletes a volume on its own.

Every plan computes from the six per-disk counters. These are QEMU `query-blockstats` figures.
**pvestatd** already exports them through PVE's InfluxDB external metric server. The tool
installs no exporter and no collector.

The InfluxDB protocol that PVE exports carries string fields. It fixes a field's type at its
first write. Prometheus has no string sample type. A transport between the two can drop one
counter for one disk. The drop is silent and permanent. The other five counters keep working.
Telegraf with a Prometheus remote-write or OpenMetrics output is the common case.

A dropped counter produces a wrong plan, not an error. Run **verify-metrics** before you trust
any plan. The command cross-checks all six counters against each other.

A backend that takes PVE's InfluxDB output as-is and serves PromQL itself has no such bridge.
gigapipe on ClickHouse is the tested example. The tool is dogfooded against it. The "Where the
numbers come from" page of the operator manual describes the mechanism in full.

The tool reads its configuration from */etc/pve/drs.yaml*. The file sits on the cluster
filesystem. Every node reads the same file.

# COMMANDS

**plan**
: Computes a migration plan. Prints the plan. Does not execute it.

**apply**
: Runs a plan, subject to *execution.mode*. *dry-run* and *confirm* run the plan/schedule/payback
  pipeline once. They print the plan or execute it. *auto* also honours
  *execution.time_windows* and *execution.max_migrations_per_run*. *auto* re-plans from freshly
  observed cluster state if a move mismatches what a concurrent change to the cluster expected.
  The re-plans are bounded by *execution.max_replans_per_run*. See the operator manual.

**show-load**
: Prints every storage in every group. It shows the disks, sizes, load and reserve status of
  each storage. Under *forecast.model: holt_winters* the tool scales the loads with the
  forecast. A *forecast:* line under the group header says whether the run used the forecast.

**explain**
: Runs the same gate/solve/schedule/payback pipeline as **plan**. It narrates what the **plan**
  output does not print. It shows the measured load every number derives from, which is
  **show-load**'s own per-storage/per-disk picture. It names every disk pinned this run, with
  its exact reason. It names any VM a pin leaves with disks on more than one storage ("cannot
  fully consolidate"). It breaks the solver's objective into its five weighted terms. It shows
  the pinned load as a fraction of the group's total, against *report.warn_pinned_load_fraction*.
  That flags a residual imbalance that is likely too structural (too much load pinned) for
  another run of **plan** to fix by itself. **-v** adds the exact Prometheus query the whole run
  used, with its node-scoping filter, window and rate settings.

**verify-metrics**
: Validates the configured metric and label names against the live Prometheus. Prints a sample
  series. Run this before you rely on any plan. Telegraf and InfluxDB naming varies by
  deployment.

**verify-storages**
: Reports per storage: type, shared flag, content types, **saferemove** and its throughput,
  capacity, the largest VM footprint and the largest disk on it. It warns where the implied
  wipe time exceeds the configured move duration or the storage cooldown.

**collect-testdata**
: Captures an anonymized diagnostic bundle so the author can reproduce a problem offline. The
  bundle holds the topology, the effective configuration with credentials and endpoints
  removed, and the Prometheus metrics. The command is read-only and dry-run-only. Giving
  **--mode confirm**/**auto** alongside it is a usage error. The tool replaces every identifier
  with a pseudonym. It keys the pseudonyms to a salt that stays on the host. The tool keeps
  sizes, capacities and load shapes. A bundle is not anonymous to someone who already knows
  the cluster. Read the bundle before you send it. The command's own options are listed under
  **COLLECT-TESTDATA OPTIONS** below. The exit status is *0* when every capture step succeeds.
  It is *1* when the bundle was written but its manifest records a failed call.

**help**
: Alias for **--manual**.

# OPTIONS

The tool accepts the global options before the command.

**-c**, **--config** *PATH*
: Reads the configuration from *PATH* instead of */etc/pve/drs.yaml*. A file named here that is
  missing, unreadable or invalid is an error. The tool never falls back to the default path.
  The environment variable **PVE_STORAGE_DRS_CONFIG** has the same effect and lower precedence.

**--group** *NAME*
: Restricts the run to one storage group. You may give the flag more than once. The groups are
  independent. The flag does not change the result for the groups it selects. A name that
  matches no group in the configuration is a hard failure (exit code 1). The tool does not
  print an empty report instead. The flag applies to **show-load**, **verify-storages**,
  **plan**, **explain** and **apply**. **verify-metrics** and **collect-testdata** are
  cluster-wide. The flag does not restrict them.

**--mode** *dry-run*|*confirm*|*auto*
: Overrides *execution.mode* for this run. The tool logs every override. An override toward
  less safety logs at warning level. The modes order is **dry-run** < **confirm** < **auto**.
  The log names both values. The override removes a barrier the operator configured.

**--json**
: Prints the machine-readable report instead of the human-readable one.

**-v**, **--verbose**
: **-v** logs the decision trail of this run on stderr. The trail holds the gate decision, the
  thresholds the run compares against, the measured load, the plan and its objective terms, the
  payback arithmetic, and every migration with its PVE task UPID. **-vv** adds per-query
  detail and third-party library logs. For **explain**, **-v** also adds a line to the report
  itself, on stdout. The line names the exact query (node-scoping filter, window and rate
  settings) the run used.

: By default the tool logs nothing below warning level. A run in which nothing went wrong
  prints only its report. An **apply** run in **confirm** or **auto** mode is the exception.
  It logs the decision trail above whether or not you give **-v**. In those modes the log is
  the only record of what was migrated and why.

**--quiet**
: Logs errors only. On an **auto** run the flag also discards the audit trail described under
  **-v**. That trail is the only record of what the run moved. Use the default, not
  **--quiet**, under a timer.

**--log-level** *error|warning|info|debug*
: Sets the log level explicitly. The flag wins over both **-v** and **--quiet**. One exception:
  on an **apply** run in **confirm**/**auto** mode, the tool raises a level below the mandatory
  audit-trail floor (**info**) back up to **info**. **--quiet** is the only way to discard that
  record.

**--log-format** *text|json|auto*
: **text** is the default. It writes one human-readable line per log record, at a terminal and
  in the journal. **json** writes one JSON object per line. Each object carries an **event**
  name to filter on. **auto** was the default through 0.1.9. It meant JSON off a terminal. It
  now means **text**. The report on stdout is unaffected. See **--json** for it.

**--version**
: Prints the version and exits.

**--manual**
: Shows this manual page.

**--replay** *PATH*
: Runs against a **collect-testdata** bundle at *PATH* instead of the live cluster. The tool
  makes no network connection. It uses the *config.yaml* from the bundle, unless you also give
  **--config**. In that case your settings run against the bundle's data. That can be a
  different solver backend, spread metric or forecast model than the one the operator who
  captured the bundle selected. **apply** and any **--mode** above *dry-run* are a usage error
  under **--replay**. So is **collect-testdata** itself, which needs a live cluster.

**-h**, **--help**
: Prints a usage summary with every option and its default, then exits. **pve-storage-drs**
  *command* **--help** does the same for one command.

# COLLECT-TESTDATA OPTIONS

The tool accepts these options only after the **collect-testdata** command. No other
subcommand takes options of its own.

**-o**, **--output** *DIR*
: Writes the bundle directory and its tarball to *DIR* instead of *support.bundle_dir*.

**--estimate**
: Prints the query count and the estimated number of series sample points. Then it exits. It
  fetches nothing. A real capture refuses to start above *support.max_series_points*.

**--range** *DURATION*
: Sets the range of the series capture. The flag overrides *support.capture_range*. The
  default captures what *holt_winters* needs (twice *window.lookback*), not only what the
  configured model needs.

**--step** *DURATION*
: Sets the resolution of the series capture. The flag overrides *metrics.step*. Coarsening the
  step is the other way to bring an oversized capture under the limit.

**--no-series**
: Captures topology, instant queries and findings only. The bundle is much smaller. It cannot
  exercise the *holt_winters* forecast. Send this form if the cluster's load shape is
  confidential.

**--no-archive**
: Writes the bundle directory only. It skips the deterministic *.tar.gz*.

**--salt-file** *PATH*
: Uses the anonymization salt at *PATH* instead of *support.salt_path*.

**--new-salt**
: Generates a fresh salt. It replaces the persisted one. The tool logs this at warning level.
  Bundles made before and after the rotation no longer share a pseudonym mapping. The same
  cluster no longer compares against itself.

# CONFIGURATION

The tool searches for the configuration in this order: **--config**, then
**$PVE_STORAGE_DRS_CONFIG**, then the default path */etc/pve/drs.yaml*. The tool validates the
file in full at startup. It treats every violation as a fatal error. The error message names
the setting. A misconfigured balancer that moves production disks is worse than one that
refuses to start.

Top-level keys: **schema_version**, **proxmox** (API connection and credentials), **prometheus**
(URL and auth), **free_space** (the free space every storage must keep, absolute or as a
percentage of its own capacity), **metrics** (metric and label name mapping), **window** (how
much history to consider), **load_weights** (the weighting of I/O time, operations and bytes),
**groups** (the storage groups, which are what a disk may not leave), **snapshot_reserve**,
**gates** (drift and imbalance thresholds, cooldowns), **migration** (bandwidth, cost and
payback), **objective** (the solver's trade-off weights), **solver** (backend and iteration
budget), **execution** (mode, concurrency, time windows, locking), **exclude**, **report**,
**state**, **forecast**, **support** (the anonymization salt and defaults for
**collect-testdata**) and **monitoring** (the status file **apply** leaves for a Nagios-style
**check_statusfile** check).

The manual listed under **SEE ALSO** documents every option individually. It gives the unit,
the default and what happens at either extreme. That document, not this page, is authoritative
for configuration.

The cluster filesystem replicates */etc/pve*. An edit is live on every node immediately. The
web server can read the files there as a group. Keep the credentials out of the file and in
**PVE_PASSWORD** or **PVE_TOKEN_SECRET**. Prefer an API token over a password.

# ENVIRONMENT

**PVE_STORAGE_DRS_CONFIG**
: Path to the configuration file. **--config** overrides it.

**PVE_PASSWORD**, **PVE_TOKEN_SECRET**
: Proxmox VE credentials. You can keep them out of the configuration file.

# FILES

*/etc/pve/drs.yaml*
: The configuration file. The cluster replicates it.

*/var/lib/pve-storage-drs/state.json*
: Cooldowns, the load vector at the last balance, in-flight task ids and the run lock. The
  file is node-local. It is deliberately not on */etc/pve*, because the tool rewrites it on
  every run. Losing the file is safe. It resets the cooldowns.

*/usr/share/doc/pve-storage-drs/manual/*, */usr/share/doc/pve-storage-drs/internals/*
: The operator manual and the internals guide, as uncompressed Markdown. One file per topic.
  Read them with **less**(1) on a node with no GUI. Typeset PDFs of both, and of the
  specification (*IMPLEMENTATION_PLAN.md*), sit beside them in */usr/share/doc/pve-storage-drs/*.

*monitoring.status_file* (unset by default)
: **apply** rewrites the status report at the end of every run. The report uses the format the
  **check_statusfile** plugin (*monitoring-plugins-contrib*) reads. Line 1 is *OK*, *WARNING* or
  *CRITICAL*. Line 2 is the output. The modification time of the file is its freshness. The
  tool rewrites the file even when the run moved nothing. See *docs/manual/36-monitoring.md*.

*/var/lib/pve-storage-drs/anonymization-salt*
: The pseudonym key for **collect-testdata**. The tool generates it on first use. Its mode is
  0600. The tool never writes it into a bundle. **--new-salt** rotates the key. Bundles made
  before and after the rotation no longer share a mapping.

*/var/lib/pve-storage-drs/testdata/*
: The default output directory of **collect-testdata** (**support.bundle_dir**, **-o**/**--output**).

# EXIT STATUS

0
: Success. A run that stopped at a gate also exits 0. A run that found nothing worth moving
  also exits 0. That is the normal outcome for most unattended invocations. The package ships
  no timer unit. Write your own, or run the tool from cron. Run it on exactly one host.
  */var/lib/pve-storage-drs/state.json* is node-local.

1
: The run failed. The failure can be an invalid configuration. It can be Prometheus or the
  Proxmox VE API unreachable, or failing mid-run. It can be a failed migration. It can be a
  solver that produced nothing usable. The API can fail for any group, in the first plan or in
  a re-plan. **apply** stops at once and visits no later group. A run that stops because
  *execution.max_replans_per_run* was exhausted is not a failure. It exits 0.

2
: Usage error on the command line.

# SEE ALSO

The operator manual, in */usr/share/doc/pve-storage-drs/manual/* (or *pve-storage-drs-manual.pdf*).
It documents every configuration option in detail. Start with *05-metrics-pipeline.md* if
**verify-metrics** reported anything. Start with *35-logging.md* before you write a systemd unit.

The specification, in */usr/share/doc/pve-storage-drs/IMPLEMENTATION_PLAN.md* (or *.pdf*). It
covers the load model, the optimization problem and the migration ordering rules.

<https://github.com/bzed/proxmox-storage-drs> is the home of the project. Send bug reports
there. The project welcomes diagnostic bundles collected with **collect-testdata** as pull
requests. The terms are in *tests/corpus/README.md*.

**pvesm**(1), **qm**(1), **pvecm**(1).

# AUTHOR

Bernd Zeimetz, bernd@bzed.de.

# COPYRIGHT

Copyright (C) 2026 Bernd Zeimetz. Licensed under the GNU Affero General Public License, version 3
or later. There is NO WARRANTY, to the extent permitted by law.
