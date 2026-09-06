# Executing a plan: `execute.py` and its `cli.py` wiring

**What does this page answer?** Why does a "completed" move need three
separate conditions, not one; why does a VM lock get waited out instead of
failing the run; how is the injectable `Clock` used to test all of this
without a real `sleep`; and what exactly does `cli.py`'s `apply` handler
add on top of `execute_plan()` itself? Describes
`proxmox_storage_drs/execute.py` and the `_handle_apply()`/`_plan_group()`
half of `proxmox_storage_drs/cli.py`.

## `execute_plan()` re-validates every move against the live cluster, not the plan

`schedule.ScheduleResult.order` was computed against a snapshot of the
cluster taken at planning time. By the time a move near the end of a long
`confirm` run is about to be issued, that snapshot can be stale in ways a
live cluster routinely produces: an operator touched the VM, PVE's own
Dynamic Load Balancer moved it to another node, a snapshot appeared, or
another process changed the target storage's free space. `_preflight()`
re-fetches the VM's current node, config, running status and snapshot list
fresh for every single move — deliberately bypassing the per-run topology
cache (`topology.py`'s section 3.5 cache exists to avoid re-fetching for
*planning*, not to avoid re-validating immediately before a mutation) —
and `_live_transient_check()` re-derives the section 8.1 reserve formula
against the target's live `storage_status()`, not the in-memory model.
Either kind of mismatch stops the group's run with `"replan_needed"`
rather than trying to patch the plan around it — `IMPLEMENTATION_PLAN.md`
section 9.2 is explicit: "abandon the remaining moves... do not attempt to
patch it."

`_live_transient_check()`'s arithmetic is the identical section 8.1
formula `schedule.transient_invariant_ok()` checks against the in-memory
model, re-typed against `PveClient.storage_status()`'s live `used`/`total`
instead of a summed disk list — the same *rule*, a different *data
source*, not a second implementation of it (AGENTS.md section 5;
`_live_transient_check()`'s own docstring makes this explicit, since it
looks at first glance like a duplicate of `schedule.py`'s function).

## Why "done" needs three conditions, not one

`IMPLEMENTATION_PLAN.md` section 9.3.2's completion criterion is
deliberately stronger than "the task succeeded":

```
move m from a to b is DONE  ⟺  task(upid) exitstatus == OK
                            ∧  volume(m) absent from GET /storage/{a}/content
                            ∧  config(vmid(m)).lock is empty
```

A storage with `saferemove` enabled keeps a storage-level lock on the
*source* for as long as it takes to zero the old volume at
`saferemove_throughput` (10 MiB/s by default) — hours or days for a large
disk, entirely after the `move_disk` task itself has already reported
success. `_wait_for_move_completion()` polls the task first (unbounded —
a move that was ever scheduled already passed
`migration.max_single_move_duration` at planning time, so there is no
separate timeout for the task loop itself), then, only when
`execution.source_release.wait` is true and the source actually
`saferemove`s, polls the source's own content listing and the VM's lock
together, bounded by `execution.source_release.timeout_seconds`. Hitting
that bound is not a failure — it is `"draining"`: the mirror is done, the
wipe is still running, and the next run will see the storage as it
actually is.

`execute_plan()`'s own `largest_by_storage` bookkeeping (section 8.1's
`Z_s`, the largest resident disk on a storage — needed for *later* moves
in the same run that check the same target's live transient invariant)
updates on `"moved"` **and** `"draining"`, not `"moved"` alone: the mirror
itself is physically complete either way, so a target storage's own
accounting must already include this disk regardless of whether its
*source* has finished releasing.

## VM locks are an open set, waited out, never whitelisted

`_wait_for_unlocked()` treats any non-empty `config.lock` as "wait," full
stop — never a lookup table of "harmless" values to skip past
(`.agents/domain-invariants.md` rule 5: a future PVE version can add a
lock value this codebase has never seen, and guessing wrong risks a
half-completed operation on someone else's backup or snapshot). What
happens after `execution.locks.wait_timeout_seconds` depends on
`execution.locks.on_timeout`:

- `"skip"` (the default) — report the move `"skipped"`, continue with the
  rest of the plan.
- `"abort"` — report it `"failed"` and set `MoveOutcome.always_stop`,
  which `execute_plan()`'s stop condition checks *independently* of
  `execution.abort_on_failure`. This was a real design bug caught by
  re-reading the manual's own wording before any test existed: the
  manual describes `on_timeout: abort` as "abort **the run**," a stronger
  and unconditional promise, distinct from `abort_on_failure`'s general
  "stop after any plain task failure" policy, which must still be
  respected on its own terms for an ordinary `move_disk` failure. Folding
  both into one flag would have made `abort_on_failure: false` silently
  defeat an operator's explicit `on_timeout: abort` choice.

## The injectable `Clock`

Every wait loop in this module measures elapsed time via `clock.now()`,
never by counting `clock.sleep()` calls — so a test's fake clock, whose
`sleep()` advances its own `now()` instantly instead of blocking
(`.agents/testing.md`: "no real `time.sleep`; inject the clock"), exercises
the *exact* timeout arithmetic production does, at zero wall-clock cost.
`_REAL_CLOCK` is a module-level singleton (`Clock` holds only function
references, never per-call state, so sharing one instance is safe) used as
`execute_plan()`'s default — a bare `Clock()` there would be a
flake8-bugbear B008 violation (a function call in a default expression).

## Orphaned volumes: reported, never deleted

`_detect_orphan_volumes()` runs only after a `"failed"` outcome, cross
-referencing the target storage's content listing against every volume
the VM's config actually still references (via the shared
`topology.parse_disk_spec()`/`topology.DISK_KEY_RE` — the same disk-spec
parser `topology.py` itself uses, not a second one). A volume owned by
the VM but not referenced anywhere in its config is reported in that
move's own `MoveOutcome.orphaned_volumes` and logged at warning — never
removed automatically (`.agents/domain-invariants.md` rule 6). A
`PveApiError` while checking (the storage or the VM briefly unreachable
right after a failure) is caught, logged, and degrades to an empty tuple
rather than turning an already-failed move into a crash.

## `confirm`'s callback lives in `cli.py`, not here

`execute.py`'s `ConfirmCallback` type is `Callable[[ScheduledMove], str]`
returning `"y"`/`"n"`/`"a"`/`"q"` — `execute_plan()` calls it, interprets
the four answers, and raises `ValueError` on anything else, but never
itself talks to a terminal. `cli.py` is the only module allowed to call
`print()`/`input()` (its own module docstring), so
`cli._confirm_move_interactively()` is where the actual prompt text lives
and where an out-of-set answer is *retried* rather than turned into the
`ValueError` `execute_plan()` would otherwise raise — a typo at the
keyboard should not look like a bug report.

## What `execute_plan()` deliberately does not do

- **No re-plan loop.** A `"replan_needed"` outcome stops the group's run
  cleanly; re-invoking the whole gate/solve/schedule/payback pipeline
  from the newly observed state and continuing, capped at
  `execution.max_replans_per_run` (`IMPLEMENTATION_PLAN.md` section 9.2
  steps 3-4), is `cli.py`-level orchestration across multiple
  `execute_plan()` calls — a real, separately-scoped piece of work, not
  implemented here or in `cli.py` yet.
- **`auto` mode's mechanics exist; its safety rails do not.** `mode ==
  "auto"` behaves like `[a]ll remaining` chosen up front, unprompted, but
  this module enforces none of `execution.time_windows`,
  `max_migrations_per_run`, or the multi-window concurrency caps —
  `IMPLEMENTATION_PLAN.md` section 12 phase 8, a distinct phase from this
  one (phase 7's own "done when" names only `confirm` mode). `cli.py`'s
  `_handle_apply()` refuses `--mode auto` outright rather than run
  unattended without the protections its own manual page documents for
  it.
- **No crash recovery.** Section 13's "on startup, check for running
  `move_disk` UPIDs owned by the DRS user before planning anything" is
  not implemented; `state.State.inflight_upids` exists and round-trips
  but nothing writes or reads it yet.

## `cli.py`: one planning pipeline, shared by `plan` and `apply`

`_plan_group()` is `_handle_plan()`'s former per-group loop body,
extracted so `_handle_apply()` calls the *same* function rather than
re-deriving "gate, then solve, then schedule, then payback" a second time
(AGENTS.md section 5) — `IMPLEMENTATION_PLAN.md` section 9.2's own re-plan
protocol says to re-run exactly this pipeline, not a parallel one `apply`
keeps to itself. `_GroupPlan` carries every stage's result (or `None` for
a stage that never ran because an earlier one stopped short, e.g.
`load_error` set or the gate said `NO ACTION`) so both handlers can tell
those cases apart without guessing from missing dict keys.

`_handle_apply()` acquires `state.py`'s advisory lock **before** touching
PVE or Prometheus at all — a second concurrent `apply` invocation (any
mode, including `dry-run`) exits `0` immediately without paying for either
round-trip first, matching section 11.2's "a live PID means another
instance is running: exit 0 quietly." Because an operator's `[q]uit` (or a
`replan_needed`, though that one is per-group and does not otherwise
propagate) can stop the whole run before every group is even planned,
`_render_group_plan_human()`/`_render_group_plan_json()` — the shared
per-group renderers behind both `plan`'s and `apply`'s output — look up
`gate_decisions` with `.get()`, not `[]`: `plan` always plans every group
first, but `apply` genuinely can leave a later group completely
unvisited, which must render as "not evaluated this run," not a
`KeyError`. This was caught by a test exercising the quit path, not by
inspection.

After a group's `execute_plan()` call, `_handle_apply()` decides which
moves counted as "executed" for `state.json`'s own bookkeeping — `"moved"`
and `"draining"` (the mirror itself completed either way, mirroring
`execute.py`'s own (C4) accounting choice for those same two statuses),
never `"would_move"`/`"skipped"`/`"failed"`/`"replan_needed"`. For those,
it calls `state.with_recorded_balance()` (this group's measured load
vector, feeding the next run's drift gate) and `state.with_recorded_cooldown()`
— a fresh disk cooldown for every executed disk at its *new* location, and
a fresh storage cooldown for every move's **destination** only, never its
source (`docs/internals/90-heuristic.md`: "the storage cooldown excludes a
destination, never a source"). The accumulated `state` is written once, at
the very end of the whole run (every group, not per-group), through
`state.save_locked_state()` — never `state.save_state_atomic()`'s
rename, which would silently detach the very lock `acquire_lock()` just
took (see `docs/internals/15-state.md`'s account of that bug) — and only
then released via `state.release_lock()`, in a `finally` so a mid-run
exception never leaves the lock held.
