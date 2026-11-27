# Monitoring: the status file

A timer-driven `pve-storage-drs --mode auto apply` that fails quietly is
worse than one that fails loudly. The journal is not a monitoring system.
Set [`monitoring.status_file`](10-configuration.md). Then `apply` leaves a
small report of its last run, in the format of the **`check_statusfile`**
plugin from Debian's `monitoring-plugins-contrib` package
(`/usr/lib/nagios/plugins/check_statusfile`). Nagios, Icinga, or anything
else that runs a Nagios plugin can watch the file. Nothing of ours is
installed on the monitoring side:

```
/usr/lib/nagios/plugins/check_statusfile /var/lib/pve-storage-drs/status
/usr/lib/nagios/plugins/check_statusfile -a 1h /var/lib/pve-storage-drs/status
```

`-a` is the maximum age of the file (`s`, `m`, `h` or `d`; default `26h`).
See "Freshness" below.

## What is in the file

A worked example of a run that gave up after too many outside changes:

```
WARNING
apply completed with 2 warnings: group fc-tier1: execution.max_replans_per_run (3) exceeded (last mismatch: VM 101 is now on 'san-c', not the planned 'san-a') | groups=1 moves_succeeded=2 moves_failed=0 bytes_moved=2199023255552B replans=3 warnings=2 duration=412.6s
warning: group fc-tier1: 9.50 GiB short of its snapshot reserve / free-space requirement after this run's plan
pve-storage-drs 0.1.13, mode auto, finished 2026-09-20T20:30:00Z
```

- **Line 1** is the state: exactly `OK`, `WARNING` or `CRITICAL`. The
  plugin turns the state into its exit status (`0`, `1`, `2`).
- **Line 2** is the summary. It names the first problem if there is one.
  After the `|` come `label=value` performance data your monitoring can
  graph: `groups`, `moves_succeeded`, `moves_failed`, `bytes_moved`
  (bytes), `replans`, `warnings`, `duration` (seconds).
- **The rest** lists any further errors and warnings, one per line. The
  file holds at most 20 of them, then "and N more — see the run log". A
  message longer than 300 characters is cut with `...`, because monitoring
  systems truncate plugin output. The full text is in the run log. The
  file ends with the version, the mode and the finish time. It holds
  counts, group and storage names and volume ids. It never holds
  credentials.

## What makes a run `OK`, `WARNING` or `CRITICAL`

| State | When |
|---|---|
| `CRITICAL` | The run exited non-zero: a move failed; PVE or Prometheus could not be read, for any group, in the first plan or in a re-plan (the run stops at once); or the tool crashed. The file says `CRITICAL` before the crash propagates, so a bug cannot leave the previous run's `OK` in place. |
| `WARNING` | The run exited `0` but left something for a human. It gave up after `execution.max_replans_per_run` re-plans, because outside changes kept invalidating its plans (try again later). A failed move left a volume on the target, which is reported and **never deleted**. A source storage had not released a volume after a move (`draining`, usually a slow `saferemove` wipe). A group is **still short of its snapshot reserve or free-space requirement** once this run's plan has run. The tool never trades the reserve for balance, so it will not fix that by itself. |
| `OK` | None of the above. A run that found nothing worth moving is `OK`; so is a `dry-run`. |

The tool never writes `UNKNOWN`. You will see it from the plugin itself
when the file does not exist yet, or is not in the expected shape.

## Freshness: why every run rewrites the file

`check_statusfile` judges freshness by the file's **modification time**,
not its content. A file older than `-a` is reported `WARNING`. So `apply`
rewrites the file on **every** run that produced a result, including runs
that moved nothing and dry runs. A stale file then means "the timer
stopped", never "it was a quiet day".

Two cases deliberately leave the file alone. Case one: a run that exited
quietly because another instance held the lock. It produced no result, and
the file keeps the last real one. Case two: a run that could not read its
configuration at all. There is no path to write to, so the file simply goes
stale. `plan`, `explain`, `show-load` and `--replay` never write the file.
An operator running them by hand must not overwrite the timer's last
result.

The tool writes the file to a temporary file in the same directory. It then
renames the temporary file into place. The plugin can run at any moment
without reading half a report. If the tool cannot write the file at all,
the run carries on and exits as it would have. A status file that cannot be
written must not change what a run did. The tool logs a
`status_file_write_failed` error. The file turns `WARNING` by age on its
own.

## Wiring it into Nagios/NRPE

The check runs on the node that owns `state.json`. That is the one node the
timer runs on:

```
command[check_pve_storage_drs]=/usr/lib/nagios/plugins/check_statusfile -a 1h /var/lib/pve-storage-drs/status
```

Pick `-a` a little longer than the timer's period. Too generous, and a
stopped timer goes unnoticed for that long. Too tight, and one slow run
turns the check `WARNING`.
