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
| `auto` | Executes unattended, subject to `execution.time_windows`, `max_migrations_per_run`, and a bounded automatic re-plan loop — see "Reading `auto` mode" below. Also the only mode that honours `execution.max_concurrent_migrations`/`max_concurrent_per_storage` above their default of `1`, running several moves at once — see "Concurrent execution" below. |

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

## Reading `auto` mode

`auto` behaves like `[a]ll remaining` chosen up front, unprompted, plus
three things `dry-run`/`confirm` do not do at all
(`IMPLEMENTATION_PLAN.md` section 9.1/9.2):

- **`execution.time_windows`.** If any are configured, a move is refused
  (reported `skipped`, "outside execution.time_windows") unless the
  current moment — in the **local time of the host running
  `pve-storage-drs`**, not UTC — falls inside one of them, and before
  starting a move `auto` also refuses it if its estimated duration
  (mirror plus any `saferemove` wipe) would not finish before the window
  closes. No windows configured at all means no restriction. Either way,
  a move already in progress is never aborted at window close — the
  check only ever runs *before* issuing the next one.
- **`execution.max_migrations_per_run`.** A ceiling on how many moves
  the whole invocation executes, shared across every group it visits
  (not reset per group) — the remainder waits for the next scheduled
  run.
- **The re-plan loop.** A `replan_needed` mismatch does not end an
  `auto` run the way it ends a `dry-run`/`confirm` one: `apply`
  re-invokes the whole pipeline (gates, load model, solver, payback,
  ordering) from freshly observed cluster state and tries again, up to
  `execution.max_replans_per_run` times. The gate may well conclude no
  further action is needed on the re-plan — a normal, quiet outcome, not
  a failure. Exceeding the cap does end the run, with a message naming
  the setting: "a cluster churning faster than the engine can plan is a
  condition for a human to look at, not to iterate against."
  Cross-referencing the report's `outcomes[]` shows the whole story for
  a re-planned group: the mismatch that triggered each re-plan, and
  whatever the next attempt then did.

## Concurrent execution

Configuring `execution.max_concurrent_migrations`/`max_concurrent_per_storage`
above their default of `1` runs several moves at once in `auto` mode
(`dry-run`/`confirm` always run strictly sequentially, regardless of these
settings — concurrency only makes sense for unattended operation).
Section 8.1's transient reserve invariant generalizes to a whole in-flight
set of moves landing on the same storage at once, checked live before
every launch exactly like the sequential executor's own pre-flight
re-check; `max_concurrent_per_storage` counts a storage as occupied
whether a move touches it as source *or* target.

**Launch order stays strictly FIFO.** The scheduler's own queue (the same
one a sequential run would follow, one move at a time) is never
reordered to keep every concurrency slot busy: if the next queued move
cannot launch yet — its VM is locked, or a per-storage cap is already
reached — `apply` waits for it rather than skipping ahead to a later
move that could launch immediately. Several moves genuinely run at once
once launched (nothing blocks waiting for one move's own completion or
lock to affect any other), but which move launches *next* is always
decided in the order `plan` would have shown it. This can under-deliver
on throughput in a mixed queue, but never launches a move out of the
order the payback-scored plan itself computed.

A failure (or a budget/deadline limit) stops the run from launching
anything further, exactly as in the sequential case, but does not
abandon moves already in flight: `apply` keeps polling them to their own
natural conclusion (`moved`, `failed`, or `draining`) before returning,
so nothing already running is left unreported. Section 7.3's saturation
check is not enforced under concurrency any more than it is under the
sequential executor (`docs/manual/30-safety-and-status.md`'s own note on
that gap applies here too).

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
on the expected source, a snapshot may have appeared, it may have been
tagged for exclusion, or the target storage's free space may no longer
satisfy the section 8.1 transient invariant. Any of these stops the
group's run with `replan_needed`. In `dry-run`/`confirm`, that is the end
of it — the operator re-runs `apply` by hand once ready; see "Reading
`auto` mode" below for what `auto` itself does about it automatically.

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

## Crash and two-instance recovery

Before planning anything, every `apply` run (including `dry-run`) checks
for a `move_disk` left running by a crashed previous run or a second,
concurrently-running instance: `state.json`'s own `inflight_upids` are
re-checked, and every node's task list is scanned for a still-running
`qmmove` task from this tool's own configured user. Any vmid this finds is
excluded from this run's planning exactly like a manually-configured
`exclude.vmids` entry — it shows up pinned in the report with the reason
"excluded by config (`exclude.vmids`)", and a log line at `WARNING`
explains which check actually found it. It is never force-cancelled, and
this run never assumes it is safe to touch that VM's disk again.

During execution, `state.json`'s `inflight_upids` is written **before**
each `move_disk` is issued and cleared once that task itself has finished
— synchronously, so a crash (killed, OOM, host reboot) partway through a
move leaves a trace the *next* run's own startup check will find, rather
than only ever being updated at the very end of a whole `apply` run. See
`docs/internals/93-crashrecovery.md` for the full mechanism.

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
