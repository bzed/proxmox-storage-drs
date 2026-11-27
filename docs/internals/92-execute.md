# Executing a plan: `execute.py` and its `cli.py` wiring

**What does this page answer?** Why does a "completed" move need three
separate conditions, not one? Why does the tool wait out a VM lock
instead of failing the run? How does the tool test all of this with the
injectable `Clock` and no real `sleep`? What exactly does `cli.py`'s
`apply` handler add on top of `execute_plan()` itself? This page
describes `proxmox_storage_drs/execute.py` and the
`_handle_apply()`/`_plan_group()` half of `proxmox_storage_drs/cli.py`.

## `execute_plan()` re-validates every move against the live cluster, not the plan

`schedule.ScheduleResult.order` was computed against a snapshot of the
cluster taken at planning time. A move near the end of a long `confirm`
run may run against a stale snapshot. A live cluster produces this kind of
staleness routinely. An operator touched the VM. PVE's own Dynamic Load
Balancer moved it to another node. A snapshot appeared. An operator queued
a pending config change on the disk about to move (section 3.8). Another
process changed the target storage's free space. `_preflight()` re-fetches
the VM's current node, config, running status, snapshot list, pending-change
list, and exclusion tags fresh for every single move. It does so
deliberately, bypassing the per-run topology cache. `topology.py`'s
section 3.5 cache exists to avoid re-fetching for *planning*. It does not
exist to skip re-validation immediately before a mutation. The exclusion
re-check (section 9.2 step 3: "untagged for exclusion", REVIEW.md S-06) is
`_is_excluded_by_tag_or_vmid()`. It is a small duplicate of `topology.py`'s
own vmid/tag predicate, not an import of it. That name is private to that
module. The choice matches this codebase's usual pattern for a one-line
filter (AGENTS.md section 5; `optimize.py`'s `_movable_disks()` is the
same precedent). `_live_transient_check()` re-derives the section 8.1
transient invariant against the target's *live* content listing and
capacity, not the in-memory model. Either kind of mismatch stops the
group's run with `"replan_needed"`. It does not try to patch the plan
around it. `IMPLEMENTATION_PLAN.md` section 9.2 is explicit: "abandon the
remaining moves... do not attempt to patch it."

The pending-change re-check (section 9.2 step 6) makes the opposite choice
from the exclusion re-check above. It calls `topology.pending_disk_reasons()`
directly. It does not re-implement the `/pending` entry parsing. That
parsing is not a one-line predicate. `topology.py` exports it, unlike its
underscore-prefixed siblings. It does so specifically so this is the only
place the parsing lives (`60-topology.md`'s "The pending-change pin").

### The live transient check: provisioned, never allocated

`_live_transient_check()` uses the identical section 8.1 formula that
`schedule.transient_invariant_ok()` checks against the in-memory model.
While the move is in flight, the target must still hold `used_b + Σ z_m +
max(f_b·max(Z_b, max_v(F_{v,b} + Σ z_m of v)), hard_b) ≤ C_b`. `z_m` is
each move's disk size. `f_b` is the storage's snapshot-reserve factor.
`Z_b` is the largest per-VM footprint already resident. `F_{v,b}` is the
footprint VM `v` already has there. An incoming disk joins its *own* VM's
footprint. Two disks of one VM landing together raise it by both. `hard_b`
is the transient free-space floor. Both call the same
`reserve.transient_charge_ok()` (see `95-schedule.md`). The live check
differs only in where `used_b` and `C_b` come from. The *rule* is the
same; the *data source* is different. This is not a second implementation
of it (AGENTS.md section 5).

**`used_b` is the sum of `size` over the target's live content listing,
never `storage_status()`'s own `used`.** The tool counts every disk at
its *provisioned* size. It does so on thin-provisioned storage (Ceph RBD,
LVM-thin, ZFS) exactly as on thick. A plan that fits only while the disks
stay thin is a plan a growing guest can turn into a full pool. Nothing
here can bound that growth (`.agents/domain-invariants.md` rule 2b;
over-provisioning is never considered). The planner's `used_b` is `Σ z_d +
Uˢᵉˣᵗ`. That is the provisioned sizes of the managed disks plus the
foreign volumes on the storage. That is the listing's total. PVE's `used`
is the *allocated* figure. It is equal on a thick pool and far lower on a
thin one. The dev cluster had a pool with 3.36 TiB provisioned and 1.45
TiB allocated. A live check built on that figure could only confirm the
plan. It could never notice that other provisioning had filled the pool,
in provisioned terms, since planning. That is the one thing a live
re-check exists to catch. `C_b` still comes from `storage_status()`'s
`total`. A LUN can be resized after the run started.

Two properties keep the listing figure safe to trust:

- **It fails safe.** A PVE API error reading either endpoint refuses the
  move. A listed volume with neither `size` nor `approximate-size` also
  refuses it. The size then cannot be established. Planning's habit of
  skipping such a foreign volume with a warning is not available to a
  check that decides whether to touch the storage *now*. Because the case
  is an error and not a mismatch, the outcome is `"failed"` with
  `abort_run` set (see "Errors are not mismatches" below). The reason goes
  in the outcome's detail. The check never passes on a partial figure. It
  never raises an exception that crashes the run. `approximate-size`
  counts at its value, the same fallback tier planning uses
  (`topology.content_item_size()`).
- **One rule for the sizes.** `topology.content_item_size()` is the single
  place the `size` → `approximate-size` order lives, shared by the
  planner's disk and foreign-volume sums and this check.

**`Z_b` is a planning-time figure, on purpose.** The formula takes three
inputs from the world. `used_b` and `C_b` are read fresh. `Z_b`, the
largest per-VM footprint resident on the target, is not. It comes from
`execute_plan()`'s `footprints_by_storage` (`{storage: {vmid: F_{v,b}}}`).
That map starts as the model's `reserve.vm_footprints_bytes()`. This
run's own completed moves are the only thing that raise it. A landed disk
is added to its VM's footprint. The source's footprint is never lowered.
That can only make the check more conservative. The listing cannot replace
`Z_b`. `Z_b` is defined over *managed* disks (section 5.3's (C4)). A
listing entry does not say whether a volume belongs to a managed disk.
The residual case: something else lands a managed disk on the target
between planning and the move. The disk appears in `used_b` at its full
provisioned size. It does not raise `Z_b`. Only the reserve multiplier's
growth on the new largest footprint, `f_b·(Z_live − Z_model)`, goes
uncounted. The disk's own bytes are never uncounted. That is narrower than
the staleness the check had before it read the listing. It is a bound, not
a bug.

**No double counting under concurrency.** `execution.max_concurrent_migrations`
above `1` makes the invariant carry one charge `z_m` per move of this run
already in flight onto the same target. Those moves' own mirror targets
must not also be summed from the listing. On RBD (and other block
storage), the new volume is listed at its full provisioned size the moment
`move_disk` allocates it. A second sum would charge it twice.
`_LiveCheck.listed_volids` holds every volid the target's listing held at
the moment a move launched. The launched move stores it as
`_InflightMove.target_baseline_volids`. `_inflight_target_volids()` then
leaves out of the sum **at most one volume per in-flight move**. The
volume is not in that baseline. It belongs to the *same VM*. Its size is
one of the two sizes `move_disk` allocates a mirror target at
(`_is_mirror_target()`). As the operator describes PVE's behaviour (it
has not been read from PVE's source): between storages of the same thin
kind, the target is the same size as the source image. That size is
`Disk.size_bytes` from its content listing. Between different storage
types, or from thin to thick, the target is the disk line's `size=` in
the VM config. The pre-flight already parses that line.
`_PreflightResult.config_size_bytes` is carried onto
`_InflightMove.config_size_bytes`. A volume of either size matches. The
two sizes can differ when a volume was resized outside PVE or its storage
rounds sizes. If PVE allocates some third size, nothing matches. The
target is counted as well as charged. The check is then merely stricter
than necessary. The same two sizes decide what a move is *charged*.
`_move_charge_bytes()` returns the listed size. It differs when the move
changes the kind of volume made. That is when `Storage.storage_type`
differs between source and target, or a qcow2 disk lands on a target that
cannot hold qcow2 and PVE writes it raw. There, the target is allocated at
the config's `size=`, and the larger of the two is charged. A same-kind
move keeps the listed size. There, the target is a copy of the source
image. Charging more would refuse moves for a discrepancy that does not
apply. `_live_transient_check()` takes the candidate's charge as a number.
It computes each in-flight move's own charge the same way from its stored
`source`/`target`/`config_size_bytes`. A move onto an `enforce_format`
storage that changes the disk's format is the planned conversion case. Its
charge is at least `topology.disk_size_on()` (plan `z_{d,s}`), computed
from the live `size=`. That is the same number `schedule.py`'s plan-time
check used. The endpoint, the plan-time check, and the live check cannot
disagree about it. `_format_arg()` passes `format=` to `move_disk`
exactly when `target_format(disk, target)` differs from the disk's own
format. A move without enforcement is the call it always was. Before
issuing the move, `_preflight` re-derives the volume's *live* format from
its name. That is a `.qcow2`/`.vmdk` suffix, else raw. That is how
`LVMPlugin::parse_volname` and `Plugin::parse_volname` decide it.
`_preflight` refuses the move if the live format differs from the planned
one. The plan's conversion and size were computed for a different volume.
The next run plans again. The mirror-target matcher also accepts the
converted size. It only ever errs towards counting a volume twice. The
matching is deliberately narrow for the same reason. A foreign volume that
appeared since the launch is never excluded. Neither is a leftover of the
same VM that was already there (it is in the baseline). Wrongly keeping a
volume only tightens the check. Wrongly dropping one would weaken it.
Where nothing matches yet (the short window between `move_disk` returning
its UPID and the allocation), the move is charged by its `z_m` alone.
That is exactly right. The sequential executor has no in-flight set and
excludes nothing. The whole in-flight period, mirroring and draining,
keeps a move in the set. Its target volume is excluded and its `z_m`
charged for as long as it is. The move is counted once either way.

`transient_charge_ok()` takes a *list* of charges, not one disk. The
concurrent executor therefore calls it with every move currently in flight
against the same target (see "Concurrent execution" below).

## Why "done" needs four conditions, not one

`IMPLEMENTATION_PLAN.md` section 9.3.2's completion criterion is
deliberately stronger than "the task succeeded":

```
move m from a to b is DONE  ⟺  task(upid) exitstatus == OK
                            ∧  volume(m) absent from GET /storage/{a}/content
                            ∧  config(vmid(m)).lock is empty
                            ∧  elapsed(drain) ≥ min_wipe_seconds(m)
```

A storage with `saferemove` enabled keeps a storage-level lock on the
*source*. The lock lasts as long as it takes to zero the old volume at
`saferemove_throughput` (10 MiB/s by default). For a large disk that is
hours or days. The wipe runs entirely after the `move_disk` task itself
has already reported success. `_wait_for_move_completion()` polls the task
first. The poll is unbounded. A move that was ever scheduled already
passed `migration.max_single_move_duration` at planning time. There is no
separate timeout for the task loop itself. The function then polls the
source's own content listing and the VM's lock together. It does so only
when `execution.source_release.wait` is true and the source actually
`saferemove`s. The bound is the config key `execution.source_release.timeout` (default `48h`).
The loader stores it in `SourceReleaseConfig.timeout_seconds`.
Hitting that bound is not a failure. It is `"draining"`: the mirror is
done, the wipe is still running. The next run will see the storage as it
actually is.

**The fourth condition, `min_wipe_seconds`, was added after the first
three turned out not to be enough** (section 9.3 point 2's "found
dogfooding" paragraph). VM 101's `scsi1` move satisfied all three
conditions: task OK, volume gone, lock clear. The very next `move_disk`
for the same VM still failed with PVE's own `can't lock file ... - got
timeout`. PVE's wipe cleanup was still finishing at the OS level after
those API-visible signals had already cleared. `_poll_move_once()` computes
the condition as `payback.compute_wipe_duration_seconds(size_bytes,
source.saferemove_throughput_bytes_per_sec)`. That is the identical
formula `payback.compute_move_cost()` already uses for the planning-time
cost estimate (AGENTS.md section 5: one implementation, two callers, and
the one place `saferemove_throughput`'s sign is resolved to a rate; see
`96-payback.md`). The function folds the value into the same `drain_start`
clock the volume/lock poll already tracks. It costs no extra API call. The
value is `None`, and has no effect at all, whenever the storage has no
configured `saferemove_throughput`. The condition only tightens where
PVE's own config gives an exact number to tighten it with.

`execute_plan()`'s own `footprints_by_storage` bookkeeping tracks section
8.1's `Z_s`, the largest per-VM footprint on a storage. Later moves in the
same run need it when they check the same target's live transient
invariant. The bookkeeping updates on `"moved"` **and** `"draining"`, not
`"moved"` alone. The mirror is physically complete either way. A target
storage's own accounting must include this disk, regardless of whether its
*source* has finished releasing.

A `"draining"` outcome also adds that move's *source* to a
`drained_storages` set. `execute_plan()` carries the set for the rest of
the run (REVIEW.md S-05). The next move whose own source or target is in
that set is skipped outright. `_drained_skip_outcome()` reports it without
a single API call. Section 9.3 asks for exactly this ("exclude it as both
source and target for the remainder of the run"). A draining storage holds
a storage-level lock for as long as the wipe runs. A subsequent
`move_disk` touching it would queue behind a potentially day-long wipe.
The task-status poll loop is unbounded. The call could also fail
outright. That would trip `abort_on_failure` for no reason a human would
consider a real failure. An earlier revision of this module tracked the
*(C4) accounting* consequence of a draining target (the paragraph above).
It never actually excluded the storage from later moves in the same run. A
review pass found that, not a test. Nothing at the time exercised two
moves sharing a storage within one run.

## An unreachable API is waited out, reads only

`execute_plan()` (any mode but `dry-run`) runs inside
`PveClient.outage_tolerance(execution.api_outage_timeout_seconds)`. Inside
it, `PveClient._call()` retries a call that raised a `transient`
`PveApiError`. That covers a connection error/timeout/TLS failure,
429/5xx, including a failed re-login. The back-off is 5 s→60 s, until the
tolerance is spent. `move_disk` passes `idempotent=False`. A dropped POST
is ambiguous. A blind repeat could start a second move. Every poll, lock
check, and preflight read is covered in one place, in both executors, with
no per-loop code.

## VM locks are an open set, waited out, never whitelisted

`_wait_for_unlocked()` treats any non-empty `config.lock` as "wait," full
stop. It uses no lookup table of "harmless" values to skip past. A future
PVE version can add a lock value this codebase has never seen. Guessing
wrong risks a half-completed operation on someone else's backup or
snapshot (`.agents/domain-invariants.md` rule 5). What happens after
`execution.locks.wait_timeout` depends on
`execution.locks.on_timeout`:

`_check_lock_once()` also reports a task still running on the VM.
`_active_task_on_vm()` finds a `/cluster/tasks` entry with the vmid as
`id` and no `endtime`/`status`, confirmed by `task_status()`. Console task
types are excluded. An `imgdel` job from an earlier move can hold the
config flock while `lock:` reads clear. The `move_disk` task would then
die on `can't lock file`. The tool waits out that task through the same
path. The retry below stays the backstop when the task list cannot be
read.


- `"skip"` (the default): the tool reports the move `"skipped"` and
  continues with the rest of the plan.
- `"abort"`: the tool reports it `"failed"` and sets
  `MoveOutcome.always_stop`. `execute_plan()`'s stop condition checks that
  flag *independently* of `execution.abort_on_failure`. A re-read of the
  manual's own wording caught a real design bug here, before any test
  existed. The manual describes `on_timeout: abort` as "abort **the run**."
  That is a stronger and unconditional promise. It is distinct from
  `abort_on_failure`'s general "stop after any plain task failure" policy.
  That policy must still be respected on its own terms for an ordinary
  `move_disk` failure. Folding both into one flag would have made
  `abort_on_failure: false` silently defeat an operator's explicit
  `on_timeout: abort` choice.

## The `move_disk` task's own flock: a retry as the fallback under `min_wipe_seconds`

`min_wipe_seconds` above (section 9.3 point 2) closes the VM-101 race in
the one case it can be computed exactly: a configured
`saferemove_throughput`. Section 9.3 point 3 is the fallback for
everything that condition cannot cover. That includes no throughput
configured, or an inaccurate one. It also includes `can't lock file
'/var/lock/qemu-server/lock-<vmid>.conf' - got timeout` surfacing as a
`move_disk` task's own `exitstatus` for some other momentary reason
entirely. PVE clears the config `lock:` line before it releases the config
file's own flock. Nothing in `_wait_for_unlocked()`'s pre-flight check
could have polled this coming. The case is a task-level failure, not a
lock the executor was in a position to wait out in advance.

`_is_task_lock_timeout()` matches that exact PVE message against a failed
move's `exitstatus`. On a match, `_execute_one_move()` (sequential) and
`_poll_inflight_once()` (concurrent) both reissue `move_disk`. They allow
up to `execution.locks.task_retry_limit` extra attempts. They record the
crash-recovery `on_inflight_finished`/`on_inflight_started` pair for the
old and new UPID exactly as the first attempt did. Section 11.2 holds: a
retried move still has exactly one UPID in `state.json` at a time. The
sequential path sleeps `execution.locks.task_retry_backoff` on the
injected `Clock` before reissuing. That matches every other wait loop in
this module. The concurrent path does not sleep inline, on purpose.
Blocking one in-flight move would stall every other candidate and
in-flight move, the same way a blocking lock wait would (see "What
`execute_plan()` deliberately does not do" above). The concurrent path
picks the retry up on the next poll cycle. The spacing is
`execution.poll_interval_seconds`, unless something else already made
progress that cycle. A retry that still exhausts the limit is reported
`"failed"`, exactly like any other task failure. It goes through the same
`abort_on_failure`/orphan-detection path.

## The injectable `Clock`

Every wait loop in this module measures elapsed time via `clock.now()`.
It never counts `clock.sleep()` calls. A test's fake clock advances its
own `now()` instantly instead of blocking when `sleep()` runs. That is
`.agents/testing.md`: "no real `time.sleep`; inject the clock." The fake
clock exercises the *exact* timeout arithmetic production does, at zero
wall-clock cost. `_REAL_CLOCK` is a module-level singleton. `Clock` holds
only function references, never per-call state, so sharing one instance
is safe. `execute_plan()` uses it as the default. A bare `Clock()` there
would be a flake8-bugbear B008 violation: a function call in a default
expression.

## Orphaned volumes: reported, never deleted

`_detect_orphan_volumes()` runs only after a `"failed"` outcome. It
cross-references the target storage's content listing against every volume
the VM's config actually still references. It uses the shared
`topology.parse_disk_spec()`/`topology.DISK_KEY_RE`, the same disk-spec
parser `topology.py` itself uses, not a second one. A volume owned by the
VM but not referenced anywhere in its config is reported in that move's
own `MoveOutcome.orphaned_volumes`. It is logged at warning, never removed
automatically (`.agents/domain-invariants.md` rule 6). A `PveApiError`
while checking (the storage or the VM briefly unreachable right after a
failure) is caught and logged. The check degrades to an empty tuple. It
does not turn an already-failed move into a crash.

## `confirm`'s callback lives in `cli.py`, not here

`execute.py`'s `ConfirmCallback` type is `Callable[[ScheduledMove], str]`.
It returns `"y"`/`"n"`/`"a"`/`"q"`. `execute_plan()` calls it and
interprets the four answers. It raises `ValueError` on anything else. It
never talks to a terminal itself. `cli.py` is the only module allowed to
call `print()`/`input()` (its own module docstring).
`cli._make_confirm_move_interactively()` builds the callback. The callback holds
the actual prompt text. It also *retries* an out-of-set answer instead of turning it into the `ValueError`
that `execute_plan()` would otherwise raise. A typo at the keyboard should
not look like a bug report.

## What `execute_plan()` deliberately does not do

- **No re-plan loop inside this module.** A `"replan_needed"` outcome
  stops the group's run cleanly here. Re-invoking the whole
  gate/solve/schedule/payback pipeline from the newly observed state is
  `cli.py`-level orchestration. It spans multiple `execute_plan()` calls
  (`cli._run_auto_group()`, `auto` mode only — see below). This module
  does not do it itself. `dry-run`/`confirm` never re-plan at all. The
  operator re-runs `apply` by hand once ready.
- **Crash recovery is not this module's own job.** `execute_plan()`
  accepts `on_inflight_started`/`on_inflight_finished` callbacks
  (`execute.InflightCallback`). It calls them around each `move_disk`. The
  write they perform, what they persist, and section 13's startup scan that
  reads it back live in `crashrecovery.py`/`cli.py`. See
  [`93-crashrecovery.md`](93-crashrecovery.md).

## `cli.py`: one planning pipeline, shared by `plan` and `apply`

`_plan_group()` is `_handle_plan()`'s former per-group loop body,
extracted as a function. `_handle_apply()` now calls the *same* function.
It does not re-derive "gate, then solve, then schedule, then payback" a
second time (AGENTS.md section 5). `IMPLEMENTATION_PLAN.md` section 9.2's
own re-plan protocol says to re-run exactly this pipeline. It does not
allow a parallel one `apply` keeps to itself. `_GroupPlan` carries every
stage's result. A stage that never ran because an earlier one stopped
short carries `None` (e.g. `load_error` set, or the gate said `NO
ACTION`). Both handlers can tell those cases apart without guessing from
missing dict keys.

`_handle_apply()` acquires `state.py`'s advisory lock **before** touching
PVE or Prometheus at all. A second concurrent `apply` invocation (any
mode, including `dry-run`) exits `0` immediately. It pays for neither
round-trip first. That matches section 11.2's "a live PID means another
instance is running: exit 0 quietly." An operator's `[q]uit`, or an aborted run, can stop the whole
run before every group is even planned. A `replan_needed` outcome does not: it
stays inside its own group.
`_render_group_plan_human()`/`_render_group_plan_json()` are the shared
per-group renderers behind both `plan`'s and `apply`'s output. They look
up `gate_decisions` with `.get()`, not `[]`. `plan` always plans every
group first. `apply` can genuinely leave a later group completely
unvisited. That must render as "not evaluated this run," not a `KeyError`.
A test exercising the quit path caught this, not inspection.

After a group's execution, `_record_executed_moves()` decides which moves
count as "executed" for `state.json`'s own bookkeeping. It counts
`"moved"` and `"draining"`. The mirror completed either way, mirroring
`execute.py`'s own (C4) accounting choice for those same two statuses. It
never counts `"would_move"`/`"skipped"`/`"failed"`/`"replan_needed"`. It
reads straight off the final `ExecutionResult.outcomes`. It never reads a
`_GroupPlan`'s own `schedule_result.order`. A payback refusal (S-02) can
already make `outcomes` a reordered subset of that order. In `auto` mode,
a re-plan (`_run_auto_group()`, below) can execute moves from a *later*
plan attempt. Those moves never appeared in the group's first-attempt
order at all. An earlier revision iterated the stale order and silently
dropped those later moves' cooldowns. For every move that counts, the
function calls `state.with_recorded_balance()`. That records this group's
measured load vector, feeding the next run's drift gate. It also calls
`state.with_recorded_cooldown()`. That records a fresh disk cooldown for
every executed disk at its *new* location. It records a fresh storage
cooldown for **both** of the move's storages, source and destination.
Section 6 says "a storage involved in a migration ... accepts no new
incoming moves," and that covers both. REVIEW.md S-03 records the reason:
an earlier revision recorded the destination only. No configured
`gates.cooldown_per_storage` could then protect a still-draining *source*.
That is exactly the scenario section 9.3's knob-sizing rule and
`verify-storages`' own warning describe. Recording both endpoints is
independent of `heuristic.py`'s own *enforcement*, which stays
destination-only. A cooldown storage is excluded as a move/swap target,
never as a source a disk may still leave (`docs/internals/90-heuristic.md`).
The accumulated `state` is written once, at the very end of the whole
run, covering every group, not per-group. It goes through
`state.save_locked_state()`, never `state.save_state_atomic()`'s rename.
The rename would silently detach the very lock `acquire_lock()` just took
(see `docs/internals/15-state.md`'s account of that bug). The code
releases the lock only then, via `state.release_lock()`, in a `finally`. A
mid-run exception never leaves the lock held.

## The payback gate: `apply` refuses on its own verdict (REVIEW.md S-02)

Section 7 calls the payback rule "a **hard acceptance test on the finished
plan**, not merely a soft `γ` penalty". The solver's own
objective already charges a plan `γ` points for the size of a move
(`docs/internals/91-optimize.md`). The tool can still reject such a whole plan
here, after the fact. It does not only score the plan lower in advance. The rule
is a verdict `plan` shows the operator, not a suggestion. An earlier
revision of `_handle_apply()` computed `payback_result` and then ignored
it entirely on the execution path. It executed a plan whose aggregate
economics failed. It also executed a plan whose one move exceeded
`migration.max_single_move_duration` (`payback_result.rejected_moves`, the
*hard* per-move rule §7.3 separates from the aggregate one).
`_apply_payback_gate()` is the fix. It never calls `execute_plan()` at all
for a move in `rejected_moves`. It also never calls it for *any* move in
the group when `not payback_result.aggregate_ok`. Both cases report a
`"skipped"` outcome ("refused: ..."). They use the exact same
`MoveOutcome`/`ExecutionResult` shapes `execute.py` itself produces.
Neither the renderers nor `state.json`'s bookkeeping need a special case.
A refused move was never "executed" (it is not `"moved"`/`"draining"`).
It earns no cooldown and contributes nothing to `last_balance`. A plan
that clears both checks is passed to `execute_plan()`. Its
individually-rejected moves (if any) are simply absent from `order`. That
is also what makes `_wait_for_move_completion()`'s own docstring claim
("a move that was accepted at planning time already passed
`migration.max_single_move_duration`") true by construction rather than
merely asserted. In `confirm` mode, the group's payback lines print once,
before the first prompt. An operator confirming moves one at a time sees
the tool's own verdict before being asked anything, not only in the
post-run report.

## `auto` mode: `timewindow.py` and `_run_auto_group()` (phase 8)

`execute_plan()` gained two auto-only budgets. Both are `None` (inactive)
unless `cli.py` passes real values. The first is a `deadline`, an
absolute instant. The function checks it against `clock.now()` before
starting each move. It checks it together with that move's
`payback.MoveCost` duration estimate from `move_costs_by_key`. The second
is a `max_migrations` count. It is decremented once per move that `move_disk` actually
launched. A move that fails before the launch (a pre-flight or live-check
refusal, or a lock timeout) does not count. Neither does a `"skipped"`,
`"would_move"` or `"replan_needed"` outcome. Both budgets stop the whole run
cleanly, never mid-move, via the same `_auto_budget_stop_outcome()`
helper. Remaining time only ever decreases. A spent cap stays spent.
There is never a reason to skip one move for a budget reason and then try
a later one anyway.

The deadline is actually checked **twice** for a locked VM.
`_auto_budget_stop_outcome()`'s pre-flight check runs before any network
call for this move. A VM-lock wait (`_wait_for_unlocked()`) can burn a
large, unpredictable share of the same budget. It can burn up to
`execution.locks.wait_timeout`, hours by default, entirely *after*
that first check already said yes. `_execute_one_move()` re-checks the
identical condition right after a lock clears and before committing to
`move_disk`. The check is `_deadline_exceeded()`, the one shared
implementation of "does this much more time still fit". If the wait alone
consumed what was left, the function refuses the move there instead. A
re-read of section 9.1 against the code caught this, before any test
existed, not a failing test.

`timewindow.py` is a small, dependency-free module. It answers exactly one
question: `current_deadline(windows, now) -> datetime | None`. `None`
means no restriction at all (no `time_windows` configured). A non-`None`
value is the close time of whichever configured window covers `now`. When
no window covers `now`, the value is `now` itself. That means zero
remaining budget. The module deliberately does not emit a separate "not
in any window" signal. A caller's "does the next move fit before the
deadline" arithmetic then refuses correctly without a second check. The
module works in **local time**, not UTC. That is a documented, deliberate
choice. The plan does not name a timezone for this setting. Local time
matches `systemd.timer`'s own `OnCalendar=` default. It also matches how
an operator actually thinks about a maintenance window. The classic
overnight-window bug: a `days: [fri]` window tagged Friday still needs to
match at 2am *Saturday*. The bug gets its own two-piece matching logic
(`is_window_active()`) and its own regression tests.

`timewindow.py` itself never reads the clock. Every function takes `now`
as a parameter. `cli._real_local_now()` is what production actually
passes. It resolves the host's real IANA zone from `/etc/localtime`'s own
symlink target. That is the standard mechanism on Debian and virtually
every Linux distribution. The function does not settle for
`datetime.now().astimezone()`'s *fixed*-offset result. The difference
matters specifically for `window_close()`'s "closes tomorrow" case. That
case combines today's `tzinfo` with tomorrow's date. A real
`zoneinfo.ZoneInfo` re-resolves its own UTC offset for that date. A frozen
offset does not. An overnight window could otherwise stay "active" up to
an hour longer than configured. That happens on the two nights a year the
local zone's clocks actually change. `_real_local_now()` falls back to the
frozen-offset form only when the zone name cannot be determined at all. At
that point, the same narrow, two-nights-a-year discrepancy returns. That
is a residual, documented limitation, not a silent one.

`cli._run_auto_group()` is where section 9.2's re-plan protocol actually
lives. It is a loop, bounded by `execution.max_replans_per_run`. The loop
calls `_apply_payback_gate()`. If any outcome it produced is `"replan_needed"`, the loop re-fetches topology
fresh. It calls
`build_topology()`, not just re-runs `_plan_group()` on the same `Group`
object. Whatever triggered the mismatch can mean the group's own
membership changed. The loop then calls `_plan_group()` again before
retrying. A re-plan that concludes `NO ACTION` ends the loop quietly, not
as a failure. That is section 9.2's own words: "the gates may well
conclude no further action is needed." A re-plan that hits a load
(Prometheus) error is *not* that. It sets `ExecutionResult.abort_reason`,
and the run fails. Exceeding the replan cap rewrites the final
`stop_reason` to name the setting explicitly. It does not report the
*symptom* (the last mismatch) as if it were the cause. It also sets
`ExecutionResult.replans_exhausted`. That is a bail-out that exits `0`,
not a failure.

### Errors are not mismatches

`"replan_needed"` means the cluster differs from the plan. A re-plan can
cure that. An *error* means the executor could not observe the cluster at
all. That covers the PVE API failing while `_preflight()` re-reads the
VM's config. It covers `_live_transient_check()` re-reading the target,
and an unsized volume on the target. A re-plan would run into the same
wall. `_pre_move_refusal()` is the one place that decides which case it
is. A `fatal` refusal becomes `MoveOutcome("failed", ..., always_stop=True,
abort_run=True)`. Everything else becomes `"replan_needed"`.
`ExecutionResult.aborted` is true when any outcome carries `abort_run`.
It is also true when the re-plan loop set `abort_reason`.
`_run_auto_group()` never re-plans an aborted result. `_handle_apply()`
stops visiting groups and returns `1`. The same holds in
`_handle_apply()` for a group whose load could not be computed in the
first place (`_GroupPlan.load_error`). The handler breaks out of the group
loop. `plan` and `explain` keep going so the report is as complete as
possible, then return `1`.

One deliberate simplification: everything the human/JSON report shows for
a group (`gate_decisions[name]`, `schedule_results[name]`, etc.) still
comes from the group's *first* planning attempt. That holds even after
`auto` re-plans the group. Only the accumulated `ExecutionResult.outcomes`
(every attempt's outcomes, concatenated) reflect what actually happened.
So does `last_balance`'s recorded load vector. Returning a second
`_GroupPlan` from a successful re-plan would complicate the report.
`_handle_apply()`'s reporting dicts would have to cope with the *first*
attempt's fields being live while a later one supersedes them. Worse, a
re-plan that lands on `NO ACTION` would have to report a group whose
`schedule_result`/`payback_result` are `None`. That group would have
`ACT`ed and moved something moments earlier. Reporting the first attempt's
plan alongside the full outcome history is simpler. It does not lose
information: the report already shows *why* it stopped and *what happened
next* per outcome.

`execution.max_migrations_per_run` is a per-*invocation* budget. It is
shared across every group `_handle_apply()` visits. `_run_auto_group()`
returns the updated remaining count. Its caller threads that count into
the next group's call rather than resetting it.

## Concurrent execution: `_execute_concurrent()` and its non-blocking helpers

`execute_plan()` dispatches to `_execute_concurrent()`. That is an
entirely separate orchestration loop from `_execute_sequential()` above.
It dispatches whenever `mode == "auto"` and either
`execution.max_concurrent_migrations` or `max_concurrent_per_storage` is
configured above its default of `1`. Every other case (`dry-run`,
`confirm`, or `auto` at the default caps) uses `_execute_sequential()`
completely unchanged. That is a genuine regression guarantee, not just a
claim. Every test written before concurrency existed still passes
unmodified. None of them touch the new dispatch condition.

**Why a second loop, not one generalized loop.** The sequential loop's
`_wait_for_unlocked()` and `_wait_for_move_completion()` both *block*.
They sleep in a tight loop until their own condition resolves. A
concurrent executor cannot reuse either directly. Blocking on one move's
lock or completion would stall every *other* in-flight or candidate move
for as long as that wait lasts. That defeats the entire point of running
several at once. Both functions were refactored into a non-blocking step
plus a thin blocking wrapper *before* concurrency was added at all. The
full pre-existing test suite then verified the refactor's correctness,
passing unchanged, independent of any new concurrent-specific test:

- `_check_lock_once()` is the one live lock read. `_wait_for_unlocked()`
  is now just that read in a loop.
- `_poll_move_once()` is section 9.3.2's completion criterion as a single
  step. It returns `None` while the move is still in progress, or
  `(status, detail)` once terminal. `_wait_for_move_completion()` is now
  just that in a loop. `_MoveWaitState` carries the one thing that has to
  survive across calls: `drain_start`, once the source-release phase
  begins. There is no longer a local variable's lifetime to hold it.

**`_launch_decision()`** runs section 9.2's five pre-flight re-checks plus
section 8.1's generalized transient invariant, for one poll cycle, without
blocking. It is the concurrent counterpart to `_execute_one_move()`'s own
pre-flight-then-lock-then-live-check sequence. `_LockWaitTracker` plays the
same role for a lock wait that `_MoveWaitState` plays for a move's
completion. `start`/`warned` survive across cycles. The executor then logs
the "VM is locked" warning once, not once per poll. It also knows when
`execution.locks.wait_timeout` has actually elapsed. The
generalized invariant itself lives in `reserve.transient_charge_ok()`
(`docs/internals/95-schedule.md`). `_launch_decision()`'s only job is to
assemble its inputs. It calls the same `_live_transient_check()` the
sequential executor uses. It passes the in-flight moves whose target is
the candidate's (`_inflight_onto()`). The check reads the live provisioned
`used_b` and capacity. It takes `Z_b` from this run's own (C4)
`footprints_by_storage` tracking. It charges every other in-flight move's
disk size alongside the candidate's own. See "The live transient check"
above for why the in-flight targets are left out of the listing sum. On a
`"launch"` verdict, the target's listing at that instant travels back on
`_LaunchDecision.target_baseline_volids`. It is stored on the new
`_InflightMove`.

**Strict FIFO, deliberately.** `_advance_pending()` only ever considers
`pending[0]`. That is the same move a sequential run would try next. If
the move cannot launch yet (a per-storage cap, or a lock that has not
cleared), the executor does not skip ahead to a later candidate. It waits,
polling everything already in flight in the meantime. It re-evaluates the
same head next cycle. Several moves genuinely run concurrently once
launched. Nothing ever blocks, waiting for one to finish before starting
another. But *which* move launches next is always the scheduler's own
next-in-line choice. A more sophisticated scheduler could reorder around a
blocked head to keep every slot busy. This one would only ever
under-deliver on throughput doing that. It never launches a move out of
the payback-scored order `schedule.order_moves()` computed. That matches
this codebase's existing tolerance for a documented, safe simplification
over a more optimal but harder-to-verify one. `schedule.py`'s own
deferred ordering-priority-2 and staging are the same trade.

**A stop condition drains, it does not abandon.** Once a budget is
exhausted, or a move fails under `execution.abort_on_failure`, or a
pre-flight/live-invariant mismatch produces `"replan_needed"`,
`_execute_concurrent()` stops calling `_advance_pending()`. No further
moves launch. The function keeps polling whatever is still in flight to
its own natural conclusion before returning. Their outcomes, and their
crash-recovery callbacks, must still fire. Whatever is still in `pending`
at that point (never even pre-flighted) is abandoned unreported. That is
exactly like `_execute_sequential()`'s own early `return`. It already
leaves every move after the one that triggered a stop completely
unaccounted for.
