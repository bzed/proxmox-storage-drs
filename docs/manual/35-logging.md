# Logging: what lands where, and what an unattended run records

Two rules cover almost everything:

- **The report goes to stdout.** **The log goes to stderr.** Always, in
  every mode. `pve-storage-drs --json plan > plan.json` is safe. Nothing is
  ever interleaved into that file.
- **A run in which nothing went wrong logs nothing.** By default the tool
  logs only warnings and errors. A healthy `plan`, `explain` or
  `show-load` prints its report and not one line beside it.

## Verbosity

| | Level | What you get |
|---|---|---|
| `--quiet` | errors | The run failed, nothing else |
| *(default)* | warnings | Something degraded but the run continued |
| `-v` | info | This run's decision trail (below) |
| `-vv` | debug | Per-query detail, plus `urllib3`/`proxmoxer` library logs |

`--log-level error|warning|info|debug` names a level directly. It wins over
both `-v` and `--quiet`, for automation that would rather name a level than
count `v`s. The tool keeps one exception: the mandatory floor below
("Unattended runs log this without being asked"). On a `confirm`/`auto`
apply run the tool raises `--log-level warning`/`error` back up to `info`,
rather than silently discarding the audit trail. `--quiet` is the only flag
that discards it.

## The decision trail

`-v` logs the reasoning behind what the report shows, per group. It logs
the measured load (`load_digest`). It logs the gate's computed
drift/imbalance, together with the thresholds the gate compared them
against (`gate_decision`). It logs the chosen plan with its solver backend
and the seven objective terms (`plan_selected`). It logs section 7's payback
arithmetic and the ratio it needed (`payback_verdict`). It logs every
migration issued, with its PVE task UPID (`move_started` /
`move_finished`). A run opens with `run_started` and closes with
`run_summary`: moves issued, succeeded, failed, bytes moved, wall time and
exit code.

```
$ pve-storage-drs -v plan
run started: plan (dry-run)
group fc-tier1: load 7.400 across 6 disks
group fc-tier1: ACT -- imbalance 255.0% meets or exceeds gates.imbalance_threshold (20.0%)
group fc-tier1: cbc plan, 2 move(s)
group fc-tier1: payback ratio 151 (need 10) -> accepted
run finished: plan exit=0
```

## Snapshot pins: a warning on every run

A VM with a snapshot, or with an unreferenced volume next to its disks, keeps
its disks in place. The tool cannot move them. The tool warns about this on
every `plan`, `explain` and `apply` run, with no `-v` needed.

The tool logs one `snapshot_pinned` record for each such VM. The record names
the VM, the reason, the disks, the pinned bytes and the pinned load. The tool
then logs one `snapshot_pinned_total` record for the group. It holds the VM
count, the disk count, the pinned bytes and the pinned load. Clear the
snapshots, or check the extra volume, to let the tool balance these disks.
When the tool cannot measure the load, `pinned_load` is `null` and the byte
figures stay.

```
group fc-tier1: VM web1(101) is pinned, snapshots present (2), 2 disks, 3.00 TiB, load 1.000 -- clear the cause to unblock balancing
group fc-tier1: 1 VMs pinned by snapshots or companion volumes, 2 disks, 3.00 TiB, load 1.000
```

## Unattended runs log this without being asked

`apply` in `confirm` or `auto` mode emits the whole decision trail above
**whether or not `-v` was given**. In those modes the log is the only
record of what happened to your cluster. A record you only get if you
remembered a flag is not a record. Read-only commands and
`--mode dry-run apply` changes nothing. They stay at the ordinary default.

`--quiet` still wins, including over this. It is the one option that leaves
you with an `auto` run that migrated data and no account of what it moved
or why. A timer unit should not pass it.

## Text or JSON

`--log-format text` (the default) writes **one human-readable line per
record**, at a terminal and in the journal alike. `journalctl -u
pve-storage-drs` then reads like the terminal output:

```
$ pve-storage-drs -v plan 2>&1 >/dev/null | head -1
run started: plan (dry-run)
```

`--log-format json` writes **one JSON object per line** instead, for a
pipeline that filters on it:

```
$ pve-storage-drs --log-format json -v plan 2>log.json >/dev/null ; head -c 120 log.json
{"command": "plan", "event": "run_started", "level": "INFO", "logger": ...
```

Every JSON record carries an `event`, which is the supported way to filter:

```sh
journalctl -u pve-storage-drs.service -o cat | jq -r 'select(.event=="move_started") | .upid'
```

This is the one stream written *as each move starts and finishes*, UPID
included. The `--json` report on stdout appears only once the run is over.
A run that dies mid-move never prints it. That is the reason to choose JSON
for an unattended timer.

`--log-format auto` was the default through 0.1.9. It chose JSON whenever
stderr was not a terminal, which included the journal. The option is still
accepted and now means `text`. A unit that relied on it for JSON needs
`--log-format json`.

## Under systemd

Point `StandardError=` at the journal. Let the defaults do the rest:
`auto` mode raises its own verbosity to log the audit trail, as text. Add
`--log-format json` if something downstream parses the journal. Do not add
`--quiet`. Do not add `-v`. It is only needed if you also want the trail
from a `dry-run` timer.
