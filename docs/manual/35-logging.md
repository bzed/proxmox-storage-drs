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
group fc-tier1: cpsat plan, 2 move(s)
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

`--log-format auto` (the default) writes **human-readable text when stderr
is a terminal** and **one JSON object per line everywhere else** — a pipe, a
redirect, or journald under systemd. So the same command reads well by hand
and parses correctly under a timer, with nothing to configure:

```
$ pve-storage-drs -v plan 2>&1 >/dev/null | head -1
run started: plan (dry-run)

$ pve-storage-drs -v plan 2>log.json >/dev/null ; head -c 120 log.json
{"command": "plan", "event": "run_started", "level": "INFO", "logger": ...
```

`--log-format text` and `--log-format json` force one or the other in either
direction.

Every JSON record carries an `event`, which is the supported way to filter:

```sh
journalctl -u pve-storage-drs.service -o cat | jq -r 'select(.event=="move_started") | .upid'
```

## Under systemd

Point `StandardError=` at the journal and let the defaults do the rest: the
non-TTY stream selects JSON on its own, and `auto` mode raises its own
verbosity to log the audit trail. Do not add `--quiet`; do not add `-v`
(it is only needed if you also want the trail from a `dry-run` timer).
