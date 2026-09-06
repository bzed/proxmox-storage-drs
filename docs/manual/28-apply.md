# Reading `apply`

`apply` runs the identical per-group pipeline `plan` prints — the same
gate, the same solver, the same scheduler, the same payback test (`plan`'s
own manual page, `docs/manual/27-plan.md`, describes all four in detail)
— and then, unless it is `dry-run`, actually issues the moves.
`execution.mode` (or `--mode`) picks what happens next:

| Mode | What `apply` does |
|---|---|
| `dry-run` *(default)* | Prints the same report `plan` would, plus a `would_move` outcome per move. Issues zero API calls. |
| `confirm` | Executes one move at a time, prompting before each: `[y]es`/`[n]o skip`/`[a]ll remaining`/`[q]uit`. |
| `auto` | **Refused outright in this build.** Its own safety rails (`execution.time_windows`, `max_migrations_per_run`, the concurrency caps) are `IMPLEMENTATION_PLAN.md` section 12 phase 8, a separate, not-yet-implemented piece of work — see `docs/manual/30-safety-and-status.md`. |

A `confirm` run, using the same section 14 fixture `plan`'s own manual
page walks through, with the operator declining the first move and
accepting the rest:

```
$ pve-storage-drs -c /etc/pve/drs.yaml --mode confirm apply
Group fc-tier1 → ACT: reserve violated on san-a; bypassing the drift and imbalance gates (section 13: safety is not subject to hysteresis)
  solver: heuristic
  102:scsi0  san-a → san-c  1.50 TiB  [y]es/[n]o skip/[a]ll remaining/[q]uit? n
  1. 102:scsi0      san-a → san-c     1.50 TiB   ~2.2h   Δimbalance -4.53   ℓ/z 1.67  → skipped: operator declined
  101:scsi1  san-a → san-b  1.00 TiB  [y]es/[n]o skip/[a]ll remaining/[q]uit? a
  2. 101:scsi1      san-a → san-b     1.00 TiB   ~1.5h   Δimbalance -2.00   ℓ/z 1.00  → moved: task UPID:... completed OK, source released
  3. 105:scsi0      san-c → san-b   512.00 GiB   ~43.7m   Δimbalance -0.40   ℓ/z 0.40  → moved: task UPID:... completed OK
  after: san-a=3.00  san-b=1.90  san-c=2.50
  spread: 255.4% → 44.6%
  payback: benefit 4.19e+06 load·s vs cost 3.15e+04 load·s → ratio 133 (need 10) ✓
```

Everything above the `→ status: detail` suffix on each move line is
identical to `plan`'s own output — the "after"/"spread"/"payback" lines
still describe the plan as scheduled, not adjusted for what a declined
move would have changed, since (as with a partial deadlock, see `plan`'s
manual page) reporting what was actually asked for is more honest than
recomputing a hypothetical.

## The `[y]es/[n]o skip/[a]ll remaining/[q]uit` prompt

Only in `confirm` mode, once per move, before it is issued — never for a
move `dry-run` would only report. `[a]ll remaining` stops prompting for
the rest of *this run* (every group, not just the current one); `[q]uit`
stops the whole run immediately, including any group not yet even
planned. An answer that is not one of the four is rejected right there
("please answer y, n, a or q") and asked again — it never reaches
`execute.py` at all, so a typo can never be mistaken for one of the four
real decisions.

## What "done" means for one move, and why it can take a while

A move is not finished when the `move_disk` task itself succeeds.
`IMPLEMENTATION_PLAN.md` section 9.3 requires all three, together: the
task reports `exitstatus: OK`, the source volume is gone from the source
storage's own content listing, and the VM's config lock is clear again. A
storage with `saferemove` enabled zeroes the old volume afterwards at
`saferemove_throughput` (default 10 MiB/s) — for a large disk, that can
run for hours after the task itself is long done. While it runs, `apply`
reports the move as `draining`, not `moved` and not `failed`: it is a
normal, expected state, bounded by `execution.source_release.timeout`
(default 48h), not an error. A `draining` move still counts as
"executed" for `state.json`'s bookkeeping below — the mirror itself
completed; only the source's own cleanup is still in flight. For the
*rest of this same run*, that storage is excluded as both a source and a
target for any later move: it holds a storage-level lock for as long as
the wipe runs, so a subsequent `move_disk` touching it would either queue
behind a wipe that can take days or fail outright. A move skipped this
way is reported plainly (`skipped`, naming the draining storage) rather
than attempted into that lock.

Before *every* move, `apply` re-checks the live cluster rather than
trusting the plan: the VM may have moved node, the disk may no longer be
on the expected source, a snapshot may have appeared, or the target
storage's free space may no longer satisfy the section 8.1 transient
invariant. Any of these stops the run for that group with
`replan_needed` rather than patching the plan around it — re-invoking
the whole pipeline automatically from the new observed state
(`IMPLEMENTATION_PLAN.md` section 9.2's re-plan protocol) is `cli.py`
-level orchestration this build does not yet implement; the operator
re-runs `apply` by hand once ready.

A VM config lock (`backup`, `snapshot`, `migrate`, or any other value —
this set is never whitelisted, see `docs/internals/92-execute.md`) makes
`apply` wait, not fail, up to `execution.locks.wait_timeout_seconds`.
What happens on that timeout depends on `execution.locks.on_timeout`:
`skip` (the default) reports the move `skipped` and continues with the
rest of the plan; `abort` reports it `failed` and stops the *whole run*
unconditionally — this one case ignores `execution.abort_on_failure`
entirely, because the manual's own words for `on_timeout: abort` are
"abort the run," a distinct, stronger promise than the general
"stop after any failed move" policy a plain task failure still goes
through.

## Failure and `abort_on_failure`

A failed `move_disk` task is reported `failed` with its detail; `apply`
then lists any volume left behind on the target that is not referenced in
the VM's config (`IMPLEMENTATION_PLAN.md` section 9.4) — **never deleted,
only reported**, exactly like every other orphan this project surfaces.
With `execution.abort_on_failure: true` (the default), the whole run
stops there; with it `false`, `apply` continues with the plan's remaining
moves. The lock-timeout-`abort` case above is the one exception that
always stops the run regardless of this setting.

## `state.json`: what a real run actually changes

`apply` is the one command that takes `state.json`'s advisory lock
(`docs/internals/15-state.md`) — checked first, before it ever touches
PVE or Prometheus, so a second concurrent `apply` (any mode, including
`dry-run`) exits `0` immediately and quietly rather than racing the first
one. After the run, for every group where at least one move actually
executed (`moved` or `draining` — both mean the mirror itself completed):

- `last_balance.load_vector` is replaced with that group's load as
  measured for this run, so the next run's drift gate compares against a
  real balance instead of treating every run as the first one.
- Every executed disk gets a fresh `gates.cooldown_per_disk` timestamp at
  its **new** location.
- **Both** of the move's storages — source and destination — get a fresh
  `gates.cooldown_per_storage` timestamp: section 6 says a storage
  "involved in a migration" accepts no new incoming moves, and section
  9.3's sizing rule for this cooldown is specifically about protecting a
  *source* still draining a `saferemove` wipe, so recording the
  destination alone could never deliver on it. What the cooldown actually
  *excludes* on the next run stays destination-only (the heuristic/MILP
  backends refuse a cooldown storage as an incoming-move target, never as
  a source a disk may still leave) — recording both endpoints only
  widens which storages carry a timestamp, not what that timestamp
  blocks.

A group that never executes anything (the gate said `NO ACTION`, or a
`load_error`/`replan_needed` stopped it before any move ran) leaves
`state.json` untouched for that group.

## `--json`

Identical to `plan`'s own `groups[]` shape (see `docs/manual/27-plan.md`),
with one addition per group: `"execution"`, either `null` (never reached
— a `load_error`, `NO ACTION`, or a group the run never got to because an
earlier one stopped it, e.g. an operator's `[q]uit`) or an object with
`stopped_early`, `stop_reason` (`null` unless the run stopped for this
group specifically) and `outcomes[]` — one entry per move actually
attempted, each with `disk_key`, `from_storage`, `to_storage`, `status`
(`would_move`/`moved`/`skipped`/`failed`/`draining`/`replan_needed`),
`detail`, `upid` (`null` unless `move_disk` was actually issued for this
move — always `null` for `would_move`/`replan_needed`, and for `skipped`
except a lock timeout that happened after issuing nothing yet, so still
`null` there too; a `failed` outcome carries one only when the task
itself ran and failed, not when a lock timeout aborted before it started)
and `orphaned_volumes` (only ever non-empty after a `failed` outcome).

## What `apply` does not yet do

- **`--mode auto` is refused outright**, not merely unsafe by default —
  see the table above and `docs/manual/30-safety-and-status.md`.
- **No automatic re-plan loop.** A `replan_needed` outcome stops the
  group's run cleanly; re-invoking gates/solve/schedule/payback from the
  newly observed state and continuing, capped at
  `execution.max_replans_per_run` (`IMPLEMENTATION_PLAN.md` section 9.2
  steps 3-4), is `cli.py`-level orchestration not implemented yet.
- **No crash recovery.** Section 13's "on startup, check for running
  `move_disk` UPIDs owned by the DRS user before planning anything" is
  not implemented — `state.json`'s `inflight_upids` field exists and
  round-trips but nothing writes or reads it yet.
