# Monitoring: the status file

A timer-driven `pve-storage-drs apply --mode auto` that fails quietly is worse than
one that fails loudly, and the journal is not a monitoring system. Set
[`monitoring.status_file`](10-configuration.md) and `apply` leaves a small report of
its last run in the format of the **`check_statusfile`** plugin from Debian's
`monitoring-plugins-contrib` package (`/usr/lib/nagios/plugins/check_statusfile`).
Nagios, Icinga, or anything else that runs a Nagios plugin can then watch it with
nothing of ours installed on the monitoring side:

```
/usr/lib/nagios/plugins/check_statusfile /var/lib/pve-storage-drs/status
/usr/lib/nagios/plugins/check_statusfile -a 1h /var/lib/pve-storage-drs/status
```

`-a` is the maximum age of the file (`s`, `m`, `h` or `d`; default `26h`) — see
"Freshness" below.

## What is in the file

A worked example of a run that gave up after too many outside changes:

```
WARNING
apply completed with 2 warnings: group fc-tier1: execution.max_replans_per_run (3) exceeded (last mismatch: VM 101 is now on 'san-c', not the planned 'san-a') | groups=1 moves_succeeded=2 moves_failed=0 bytes_moved=2199023255552B replans=3 warnings=2 duration=412.6s
warning: group fc-tier1: 9.50 GiB short of its snapshot reserve / free-space requirement after this run's plan
pve-storage-drs 0.1.7, mode auto, finished 2026-09-20T20:30:00Z
```

- **Line 1** is the state: exactly `OK`, `WARNING` or `CRITICAL`. The plugin turns it
  into its exit status (`0`, `1`, `2`).
- **Line 2** is the summary, naming the first problem if there is one. After the `|`
  come `label=value` performance data your monitoring can graph: `groups`,
  `moves_succeeded`, `moves_failed`, `bytes_moved` (bytes), `replans`, `warnings`,
  `duration` (seconds).
- **The rest** lists any further errors and warnings, one per line (at most 20, then
  "and N more — see the run log"; a message longer than 300 characters is cut with
  `...`, since monitoring systems truncate plugin output — the full text is in the
  run log), and ends with the version, the mode and the finish
  time. The file holds counts, group and storage names and volume ids — never
  credentials.

## What makes a run `OK`, `WARNING` or `CRITICAL`

| State | When |
|---|---|
| `CRITICAL` | The run exited non-zero: a move failed; PVE or Prometheus could not be read (for any group, in the first plan or in a re-plan — the run stops at once); or the tool crashed (the file says `CRITICAL` before the crash propagates, so a bug cannot leave the previous run's `OK` in place). |
| `WARNING` | The run exited `0` but left something for a human: it gave up after `execution.max_replans_per_run` re-plans because outside changes kept invalidating its plans (try again later); a failed move left a volume on the target, which is reported and **never deleted**; a source storage had not released a volume after a move (`draining`, usually a slow `saferemove` wipe); or a group is **still short of its snapshot reserve or free-space requirement** once this run's plan has run — the tool never trades the reserve for balance, so it will not fix that by itself. |
| `OK` | None of the above. A run that found nothing worth moving is `OK`; so is a `dry-run`. |

`UNKNOWN` is never written by the tool. You will see it from the plugin itself when
the file does not exist yet, or is not in the expected shape.

## Freshness: why every run rewrites the file

`check_statusfile` judges freshness by the file's **modification time**, not its
content: older than `-a` is reported `WARNING`. So `apply` rewrites the file on
**every** run that produced a result — including runs that moved nothing and dry runs
— so that a stale file means "the timer stopped", never "it was a quiet day".

Two cases deliberately leave the file alone: a run that exited quietly because
another instance held the lock (it produced no result, and the file keeps the last
real one), and a run that could not read its configuration at all (there is no path
to write to; the file simply goes stale). `plan`, `explain`, `show-load` and
`--replay` never write it: an operator running them by hand must not overwrite the
timer's last result.

The file is written to a temporary file in the same directory and renamed into place,
so the plugin can run at any moment without reading half a report. If it cannot be
written at all, the run carries on and exits as it would have (a status file that
cannot be written must not change what a run did), a `status_file_write_failed`
error is logged, and the file turns `WARNING` by age on its own.

## Wiring it into Nagios/NRPE

The check runs on the node that owns `state.json` — the one node the timer runs on:

```
command[check_pve_storage_drs]=/usr/lib/nagios/plugins/check_statusfile -a 1h /var/lib/pve-storage-drs/status
```

Pick `-a` a little longer than the timer's period. Too generous and a stopped timer
goes unnoticed for that long; too tight and one slow run turns the check `WARNING`.
