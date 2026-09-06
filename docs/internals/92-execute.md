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
re-fetches the VM's current node, config, running status, snapshot list
and exclusion tags fresh for every single move — deliberately bypassing
the per-run topology cache (`topology.py`'s section 3.5 cache exists to
avoid re-fetching for *planning*, not to avoid re-validating immediately
before a mutation). The exclusion re-check (section 9.2 step 3:
"untagged for exclusion", REVIEW.md S-06) is
`_is_excluded_by_tag_or_vmid()`, a small duplicate of `topology.py`'s own
vmid/tag predicate rather than an import of it — that name is private to
that module, matching this codebase's usual choice for a one-line filter
(AGENTS.md section 5; `optimize.py`'s `_movable_disks()` is the same
precedent). And `_live_transient_check()` re-derives the section 8.1
reserve formula
against the target's live `storage_status()`, not the in-memory model.
Either kind of mismatch stops the group's run with `"replan_needed"`
rather than trying to patch the plan around it — `IMPLEMENTATION_PLAN.md`
section 9.2 is explicit: "abandon the remaining moves... do not attempt to
patch it."

`_live_transient_check()`'s arithmetic is the identical section 8.1
formula `schedule.transient_invariant_ok()` checks against the in-memory
model, both now calling the same `reserve.transient_charge_ok()` (see
`95-schedule.md`) — this one re-typed against `PveClient.storage_status()`'s
live `used`/`total` instead of a summed disk list. The same *rule*, a
different *data source*, not a second implementation of it (AGENTS.md
section 5). `transient_charge_ok()` already takes a *list* of charges, not
one disk, so it is ready for a future concurrent executor to call with
every move currently in flight against the same target — this module does
not do that yet (see "What `execute_plan()` deliberately does not do"
below).

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

A `"draining"` outcome also adds that move's *source* to a `drained_storages`
set `execute_plan()` carries for the rest of the run (REVIEW.md S-05): the
next move whose own source or target is in that set is skipped outright,
`_drained_skip_outcome()` reporting it without a single API call. Section
9.3 asks for exactly this ("exclude it as both source and target for the
remainder of the run") — a draining storage holds a storage-level lock
for as long as the wipe runs, so a subsequent `move_disk` touching it
would either queue behind a potentially day-long wipe (the task-status
poll loop is unbounded) or fail outright, tripping `abort_on_failure` for
no reason a human would consider a real failure. An earlier revision of
this module tracked the *(C4) accounting* consequence of a draining
target (the paragraph above) but never actually excluded the storage
from later moves in the same run — found by a review pass, not a test,
since nothing at the time exercised two moves sharing a storage within
one run.

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

- **No re-plan loop inside this module.** A `"replan_needed"` outcome
  stops the group's run cleanly here; re-invoking the whole
  gate/solve/schedule/payback pipeline from the newly observed state is
  `cli.py`-level orchestration across multiple `execute_plan()` calls
  (`cli._run_auto_group()`, `auto` mode only — see below), not something
  this module does itself. `dry-run`/`confirm` never re-plan at all: the
  operator re-runs `apply` by hand once ready.
- **Section 7.3's saturation check is not enforced, concurrently or
  sequentially.** It is not implemented anywhere in this codebase yet
  (`docs/internals/96-payback.md`), so section 8.1 point 4 of
  `concurrency_ok` stays a documented gap the concurrent executor
  inherits rather than closes.
- **Crash recovery is not this module's own job.** `execute_plan()`
  accepts `on_inflight_started`/`on_inflight_finished` callbacks
  (`execute.InflightCallback`) and calls them around each `move_disk` --
  writing what they actually persist, and section 13's startup scan that
  reads it back, both live in `crashrecovery.py`/`cli.py`. See
  [`93-crashrecovery.md`](93-crashrecovery.md).

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

After a group's execution, `_record_executed_moves()` decides which moves
counted as "executed" for `state.json`'s own bookkeeping — `"moved"` and
`"draining"` (the mirror itself completed either way, mirroring
`execute.py`'s own (C4) accounting choice for those same two statuses),
never `"would_move"`/`"skipped"`/`"failed"`/`"replan_needed"`. It reads
straight off the final `ExecutionResult.outcomes`, never a `_GroupPlan`'s
own `schedule_result.order`: a payback refusal (S-02) can already make
`outcomes` a reordered subset of that order, and in `auto` mode a
re-plan (`_run_auto_group()`, below) can execute moves from a *later*
plan attempt that never appeared in the group's first-attempt order at
all — an earlier revision iterated the stale order and silently dropped
those later moves' cooldowns. For every move that counts, it calls
`state.with_recorded_balance()` (this group's measured load vector,
feeding the next run's drift gate) and `state.with_recorded_cooldown()`
— a fresh disk cooldown for every executed disk at its *new* location, and
a fresh storage cooldown for **both** of the move's storages, source and
destination (section 6: "a storage involved in a migration ... accepts no
new incoming moves" covers both; REVIEW.md S-03 — an earlier revision of
this code recorded the destination only, which meant no configured
`gates.cooldown_per_storage` could ever protect a still-draining
*source*, exactly the scenario section 9.3's knob-sizing rule and
`verify-storages`' own warning describe). Recording both endpoints is
independent of `heuristic.py`'s own *enforcement*, which stays
destination-only: a cooldown storage is excluded as a move/swap target,
never as a source a disk may still leave (`docs/internals/90-heuristic.md`).
The accumulated `state` is written once, at the very end of the whole run
(every group, not per-group), through `state.save_locked_state()` —
never `state.save_state_atomic()`'s rename, which would silently detach
the very lock `acquire_lock()` just took (see `docs/internals/15-state.md`'s
account of that bug) — and only then released via `state.release_lock()`,
in a `finally` so a mid-run exception never leaves the lock held.

## The payback gate: `apply` refuses on its own verdict (REVIEW.md S-02)

Section 7 calls the payback rule "a **hard acceptance test on the
finished plan**, not merely a soft `γ` penalty" — a verdict `plan` shows
the operator, not a suggestion. An earlier revision of `_handle_apply()`
computed `payback_result` and then ignored it entirely on the execution
path: a plan whose aggregate economics failed, or whose one move exceeded
`migration.max_single_move_duration` (`payback_result.rejected_moves`,
the *hard* per-move rule §7.3 separates from the aggregate one), was
executed anyway. `_apply_payback_gate()` is the fix: it never calls
`execute_plan()` at all for a move in `rejected_moves`, or for *any* move
in the group when `not payback_result.aggregate_ok` — both report a
`"skipped"` outcome ("refused: ...") through the exact same
`MoveOutcome`/`ExecutionResult` shapes `execute.py` itself produces, so
neither the renderers nor `state.json`'s bookkeeping need a special case:
a refused move was never "executed" (it is not `"moved"`/`"draining"`),
so it earns no cooldown and contributes nothing to `last_balance`. A plan
that clears both checks is passed to `execute_plan()` with its
individually-rejected moves (if any) simply absent from `order` — which
is also what makes `_wait_for_move_completion()`'s own docstring claim
("a move that was accepted at planning time already passed
`migration.max_single_move_duration`") true by construction rather than
merely asserted. In `confirm` mode, the group's payback lines print once,
before the first prompt — an operator confirming moves one at a time
sees the tool's own verdict before being asked anything, not only in the
post-run report.

## `auto` mode: `timewindow.py` and `_run_auto_group()` (phase 8)

`execute_plan()` itself grew two auto-only budgets, both `None` (inactive)
unless `cli.py` passes real values: a `deadline` (an absolute instant,
checked against `clock.now()` before starting each move, together with
that move's `payback.MoveCost` duration estimate from `move_costs_by_key`)
and a `max_migrations` count, decremented once per move actually attempted
(`"moved"`/`"draining"`/`"failed"` — never `"skipped"`/`"would_move"`/
`"replan_needed"`). Both stop the whole run cleanly (never mid-move) via
the same `_auto_budget_stop_outcome()` helper, since remaining time only
ever decreases and a spent cap stays spent — there is never a reason to
skip one move for a budget reason and then try a later one anyway.

The deadline is actually checked **twice** for a locked VM:
`_auto_budget_stop_outcome()`'s pre-flight check runs before any network
call for this move, but a VM-lock wait (`_wait_for_unlocked()`) can burn
a large, unpredictable share of the same budget — up to
`execution.locks.wait_timeout_seconds`, hours by default — entirely
*after* that first check already said yes. `_execute_one_move()`
re-checks the identical condition (`_deadline_exceeded()`, the one
shared implementation of "does this much more time still fit") right
after a lock clears and before committing to `move_disk`, refusing the
move there instead if the wait alone consumed what was left. Caught by
re-reading section 9.1 against the code before any test existed, not by
a failing test.

`timewindow.py` is a small, dependency-free module answering exactly one
question, `current_deadline(windows, now) -> datetime | None`: `None`
means no restriction at all (no `time_windows` configured), and a
non-`None` value is either the close time of whichever configured window
covers `now`, or `now` itself when none currently do (zero remaining
budget — deliberately not a separate "not in any window" signal, so a
caller's "does the next move fit before the deadline" arithmetic refuses
correctly without a second check). It works in **local time**, not UTC —
a documented, deliberate choice (the plan does not name a timezone for
this setting) matching `systemd.timer`'s own `OnCalendar=` default and
how an operator actually thinks about a maintenance window. The classic
overnight-window bug — a `days: [fri]` window tagged Friday still needing
to match at 2am *Saturday* — gets its own two-piece matching logic
(`is_window_active()`) and its own regression tests.

`timewindow.py` itself never reads the clock (every function takes `now`
as a parameter); `cli._real_local_now()` is what production actually
passes. It resolves the host's real IANA zone from `/etc/localtime`'s
own symlink target (the standard mechanism on Debian and virtually
every Linux distribution) rather than settling for
`datetime.now().astimezone()`'s *fixed*-offset result — the difference
matters specifically for `window_close()`'s "closes tomorrow" case,
which combines today's `tzinfo` with tomorrow's date: a real
`zoneinfo.ZoneInfo` re-resolves its own UTC offset for that date, a
frozen offset does not, so an overnight window could otherwise stay
"active" up to an hour longer than configured on the two nights a year
the local zone's clocks actually change. `_real_local_now()` falls back
to the frozen-offset form only when the zone name cannot be determined
at all, at which point that same narrow, two-nights-a-year discrepancy
returns — a residual, documented limitation, not a silent one.

`cli._run_auto_group()` is where section 9.2's re-plan protocol actually
lives: a loop, bounded by `execution.max_replans_per_run`, that calls
`_apply_payback_gate()` and then, only if the *last* outcome it produced
was `"replan_needed"`, re-fetches topology fresh
(`build_topology()` — not just re-running `_plan_group()` on the same
`Group` object, since whatever triggered the mismatch can mean the
group's own membership changed) and calls `_plan_group()` again before
retrying. A re-plan that concludes `NO ACTION` (or hits a load error) ends
the loop quietly, not as a failure — section 9.2's own words, "the gates
may well conclude no further action is needed." Exceeding the replan cap
rewrites the final `stop_reason` to name the setting explicitly, rather
than reporting the *symptom* (the last mismatch) as if it were the cause.

One deliberate simplification: everything the human/JSON report shows for
a group (`gate_decisions[name]`, `schedule_results[name]`, etc.) still
comes from the group's *first* planning attempt, even after `auto`
re-plans it — only the accumulated `ExecutionResult.outcomes` (every
attempt's outcomes, concatenated) and `last_balance`'s recorded load
vector reflect what actually happened. Returning a second `_GroupPlan`
from a successful re-plan would need `_handle_apply()`'s reporting dicts
to cope with the *first* attempt's fields being live while a later one
supersedes them, and — worse — a re-plan that lands on `NO ACTION` would
have to report a group whose `schedule_result`/`payback_result` are
`None` despite the group having `ACT`ed and moved something moments
earlier. Reporting the first attempt's plan alongside the full outcome
history is simpler and does not lose information: the report already
shows *why* it stopped and *what happened next* per outcome.

`execution.max_migrations_per_run` is a per-*invocation* budget, shared
across every group `_handle_apply()` visits — `_run_auto_group()` returns
the updated remaining count, which its caller threads into the next
group's call rather than resetting it.

## Concurrent execution: `_execute_concurrent()` and its non-blocking helpers

`execute_plan()` dispatches to `_execute_concurrent()`, an entirely
separate orchestration loop from `_execute_sequential()` above, whenever
`mode == "auto"` and either `execution.max_concurrent_migrations` or
`max_concurrent_per_storage` is configured above its default of `1`.
Every other case (`dry-run`, `confirm`, or `auto` at the default caps)
uses `_execute_sequential()` completely unchanged — this is a genuine
regression guarantee, not just a claim: every test written before
concurrency existed still passes unmodified, because none of them touch
the new dispatch condition.

**Why a second loop, not one generalized loop.** The sequential loop's
`_wait_for_unlocked()` and `_wait_for_move_completion()` both *block*,
sleeping in a tight loop until their own condition resolves. A concurrent
executor cannot reuse either directly: blocking on one move's lock or
completion would stall every *other* in-flight or candidate move for as
long as that wait lasts, which defeats the entire point of running
several at once. Both were refactored into a non-blocking step plus a
thin blocking wrapper *before* concurrency was added at all, so the
refactor's own correctness could be verified by the full pre-existing
test suite passing unchanged, independent of any new concurrent-specific
test:

- `_check_lock_once()` is the one live lock read; `_wait_for_unlocked()`
  is now just that read in a loop.
- `_poll_move_once()` is section 9.3.2's completion criterion as a single
  step, returning `None` while still in progress or `(status, detail)`
  once terminal; `_wait_for_move_completion()` is now just that in a
  loop. `_MoveWaitState` carries the one thing that has to survive across
  calls (`drain_start`, once the source-release phase begins) since there
  is no longer a local variable's lifetime to hold it.

**`_launch_decision()`** is section 9.2's five pre-flight re-checks plus
section 8.1's generalized transient invariant, for one poll cycle,
without blocking — the concurrent counterpart to `_execute_one_move()`'s
own pre-flight-then-lock-then-live-check sequence. `_LockWaitTracker`
plays the same role for a lock wait that `_MoveWaitState` plays for a
move's completion: `start`/`warned` survive across cycles so the
executor logs the "VM is locked" warning once, not once per poll, and
knows when `execution.locks.wait_timeout_seconds` has actually elapsed.
The generalized invariant itself lives in `reserve.transient_charge_ok()`
(`docs/internals/95-schedule.md`) — `_launch_decision()`'s only job is to
assemble its inputs: a live `storage_status()` read for `used`/`total`,
this run's own (C4) `largest_by_storage` tracking for `Z_b`, and
`_target_charges()` (every other in-flight move's own disk size, for
moves already landing on the same target) alongside the candidate's own
size.

**Strict FIFO, deliberately.** `_advance_pending()` only ever considers
`pending[0]` — the same move a sequential run would try next. If it
cannot launch yet (a per-storage cap, or a lock that has not cleared),
the executor does not skip ahead to a later candidate that might launch
immediately; it waits (polling everything already in flight in the
meantime) and re-evaluates the same head next cycle. Several moves
genuinely run concurrently once launched — nothing ever blocks waiting
for one to finish before starting another — but *which* move launches
next is always the scheduler's own next-in-line choice. A more
sophisticated scheduler could reorder around a blocked head to keep
every slot busy; this one can only ever under-deliver on throughput
doing that, never launch a move out of the payback-scored order
`schedule.order_moves()` computed, matching this codebase's existing
tolerance for a documented, safe simplification over a more optimal but
harder-to-verify one (`schedule.py`'s own deferred ordering-priority-2
and staging are the same trade).

**A stop condition drains, it does not abandon.** Once a budget is
exhausted, a move fails under `execution.abort_on_failure`, or a
pre-flight/live-invariant mismatch produces `"replan_needed"`,
`_execute_concurrent()` stops calling `_advance_pending()` (no further
moves launch) but keeps polling whatever is still in flight to its own
natural conclusion before returning — their outcomes, and their
crash-recovery callbacks, must still fire. Whatever is still in
`pending` at that point (never even pre-flighted) is abandoned
unreported, exactly like `_execute_sequential()`'s own early `return`
already leaves every move after the one that triggered a stop
completely unaccounted for.
