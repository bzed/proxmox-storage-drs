# Logging: what lands where, and what an unattended run records

Two rules cover almost everything:

- **The report goes to stdout, the log goes to stderr.** Always, in every
  mode. `pve-storage-drs --json plan > plan.json` is safe: nothing is ever
  interleaved into that file.
- **A run in which nothing went wrong logs nothing.** By default only
  warnings and errors are logged, so a healthy `plan`, `explain` or
  `show-load` prints its report and not one line beside it.

## Verbosity

| | Level | What you get |
|---|---|---|
| `--quiet` | errors | The run failed, nothing else |
| *(default)* | warnings | Something degraded but the run continued |
| `-v` | info | This run's decision trail (below) |
| `-vv` | debug | Per-query detail, plus `urllib3`/`proxmoxer` library logs |

`--log-level error|warning|info|debug` states a level outright and wins over
both `-v` and `--quiet` — for automation that would rather name a level than
count `v`s. The one exception is the mandatory floor below ("Unattended runs
log this without being asked"): `--log-level warning`/`error` on a
`confirm`/`auto` apply run is raised back up to `info` rather than silently
discarding the audit trail. `--quiet` is the only flag that discards it.

## The decision trail

`-v` logs, per group, the reasoning behind what the report shows: the
measured load (`load_digest`), the gate's computed drift/imbalance together
with the thresholds they were compared against (`gate_decision`), the chosen
plan with its solver backend and the six objective terms (`plan_selected`),
section 7's payback arithmetic and the ratio it needed (`payback_verdict`),
and every migration issued with its PVE task UPID (`move_started` /
`move_finished`). A run opens with `run_started` and closes with
`run_summary` — moves issued, succeeded, failed, bytes moved, wall time and
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

## Unattended runs log this without being asked

`apply` in `confirm` or `auto` mode emits the whole decision trail above
**whether or not `-v` was given**. In those modes the log is the only record
of what happened to your cluster, and a record you only get if you
remembered a flag is not a record. Read-only commands and
`apply --mode dry-run` change nothing, so they stay at the ordinary default.

`--quiet` still wins, including over this. It is the one option that will
leave you with an `auto` run that migrated data and no account of what it
moved or why — which is why a timer unit should not pass it.

## Text or JSON

`--log-format text` (the default) writes **one human-readable line per
record**, at a terminal and in the journal alike, so `journalctl -u
pve-storage-drs` reads like the terminal output:

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
included; the `--json` report on stdout only appears once the run is over,
so a run that dies mid-move never prints it. That is the reason to choose
JSON for an unattended timer.

`--log-format auto` was the default through 0.1.9 and chose JSON whenever
stderr was not a terminal, which included the journal. It is still accepted
and now means `text`; a unit that relied on it for JSON needs
`--log-format json`.

## Under systemd

Point `StandardError=` at the journal and let the defaults do the rest:
`auto` mode raises its own verbosity to log the audit trail, as text. Add
`--log-format json` if something downstream parses the journal. Do not add
`--quiet`; do not add `-v` (it is only needed if you also want the trail
from a `dry-run` timer).
