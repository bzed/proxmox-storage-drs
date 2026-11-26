# Ordering the moves

**What does this page answer?** How does `schedule.py` turn a target
assignment into an ordered, transient-feasible sequence of moves? What
happens when no order exists?

This page describes `proxmox_storage_drs/schedule.py`.

## One loop, reusing `heuristic.py`'s objective for the ratio

`order_moves()` implements section 8.2's pseudocode directly. While there are
pending moves, the loop finds the ones that are transient-feasible right now.
It schedules the best of them by persistent-objective-reduction-per-byte.
Moves that resolve a currently-violating storage win outright, regardless of
that ratio. The loop applies the move, then repeats.

"Persistent-objective reduction" sums the `alpha`, `delta`, `kappa*w_v`
**and** `mu` terms. `mu` is the large-VM split excess. These are the parts of
section 5.4's objective whose improvement outlives the plan. `beta` and
`gamma` are one-time migration costs that a completed move has already paid.

The loop calls `heuristic.evaluate_assignment()` twice, before and after the
candidate move. It diffs `.imbalance_term + .capacity_spread_term +
.fragmentation_term + .split_excess_term`.

This is not a second formula. The loop uses the same one `heuristic.py`
already computes. A plan's ordering therefore agrees with whatever
`objective.spread_metric`/`kappa_vm_affinity` is configured, exactly the way
the assignment that produced it did.

The `kappa*w_v` term joined this sum alongside section 5.4's `w_v` weighting
itself. Previously the sum was alpha+delta only. A fragmenting move now
visibly costs more in the ranking. It also costs more in the target
assignment the solver already chose.

## `cost_m` is `z_d` — except below `tiny_disk_bytes`, where it is `0`

Section 8.2's ratio is "persistent-objective reduction / `cost_m`".

`cost_m` here is simply the disk's size in bytes. It is not `payback.py`'s
real duration-based cost. That cost is mirror time plus, when `saferemove` is
on, wipe time. Wipe *throughput* is a per-storage config value. Two candidate
moves off different sources can have genuinely different wipe costs, even for
the same `z_d`.

`migration.bwlimit_bytes_per_sec` is one global config value. Every move's
*mirror* duration alone is therefore `z_d / bwlimit`. That divides a constant
into every disk's size equally. Dividing a reduction by `z_d` and dividing it
by `z_d / bwlimit` produce the **same ordering**. `bwlimit` is a positive
constant common to every candidate.

`cost_m = z_d` reproduces the true mirror-only ordering exactly. The value is
an approximation once a group has moves whose `saferemove` wipe cost differs
enough to change the ranking that `payback.py`'s full cost would produce.

Scoring candidates by `payback.compute_move_cost()` instead of `z_d` is a
natural follow-up. It is not yet done. This module predates `payback.py` and
has not been revisited to consume it (REVIEW.md R-04).

One exception is implemented today. A disk below `migration.tiny_disk_bytes`
gets `cost_m = 0` regardless of its real `z_d`. The ratio is `+inf` rather
than a division. That is section 8.2's own words: "cost_m = 0 ranks first:
free value, delivered before anything pays."

This is not merely a fall back to raw reduction. Raw reduction would not
necessarily beat a competing large candidate's own high ratio. A zero-cost
move is ranked ahead of *every* nonzero-cost one outright. A tiny
`efidisk0`/`tpmstate0` reunion is always scheduled before a real migration
that happens to reduce the objective by more in absolute terms.

That includes the larger disks of the small disk's *own* VM. The choice is
deliberate. A small disk's mirror and wipe take seconds. A large disk's source
can hold its storage's concurrency slot for many minutes while `saferemove`
zeroes it. Putting the small move first means it never waits behind that
wipe. If a run stops right after it, the VM is split until the next run.
Section 5.3 (C8) permits that. The rule constrains where a small disk *ends*,
not the order it gets there.

## The transient invariant, called with a single-move set always

Section 8.1 defines a generalized invariant over a whole in-flight set `M`,
specifically so it can be "implement[ed] as the single feasibility predicate
and call[ed] with `M = {m}` for the sequential case". This module is that
sequential case, always.

`transient_invariant_ok()` checks one move against `state`. That is the
assignment as of immediately before that move starts. Every
previously-scheduled move is assumed **fully complete** by then: the mirror is
finished, any `saferemove` wipe is finished, and the source is genuinely
freed, before this move begins.

That models `schedule.order_moves()`'s own job correctly regardless of
`execution.max_concurrent_migrations`. The module always computes one,
strictly-sequential *order*. That order becomes a launch queue that several
moves can run against concurrently. This happens only once `execute.py`'s own
executor gets hold of the queue (see `92-execute.md`'s "Concurrent execution"
section).

This module never reasons about overlapping in-flight windows. It does not
need to. `execute.py`'s own live re-checks (below) are what actually enforce
the invariant against whatever really ends up running together.

The actual arithmetic is
`used_b + sum(z_m) + f_b * max(Z_b, max_v(F_{v,b} + sum z_m of v)) <= C_b`.
The terms are as follows. `used_b` is storage `b`'s bytes already used. `z_m`
is each in-flight move's disk size, summed over every in-flight charge
landing on `b`. The reserve headroom is sized off the larger of the biggest
per-VM footprint already resident and the biggest footprint any in-flight
charge creates. `f_b` is the storage's own `reserve_factor`. `Z_b` is the
largest per-VM footprint already resident. `F_{v,b}` is VM `v`'s footprint
there. `C_b` is the storage's capacity in bytes.

A landing disk joins its *own* VM's footprint. A disk that reunites a VM on
`b` can raise the reserve even when the disk is small.

The arithmetic lives in `reserve.transient_charge_ok()`. The function takes a
*list* of charges rather than one disk. It degenerates to section 8.1's
original single-move form when called with one charge. This module calls it that
way, with `[(disk.vmid, disk_size_on(disk, target_storage))]`. For a move that
keeps the format of the disk, that size is `disk.size_bytes`. It generalizes correctly to several moves landing on
the same storage at once. `execute._launch_decision()` calls it with more
than one charge, for real, under concurrent execution.

AGENTS.md section 5: this is the *one* place that formula is written, not two
functions that happen to agree.

`execute._live_transient_check()` calls the function with live numbers instead
of this module's model-derived ones. Both the sequential executor and
`execute._launch_decision()` (concurrent) call `execute._live_transient_check()`.
It reads capacity from `storage_status()`. It sums `used_b` from the
target's content listing at *provisioned* sizes. That keeps the same quantity
this module computes, not PVE's lower allocated `used` on a thin pool (see
`92-execute.md`).

Section 5.3.1's transient floor is folded into the check the same way (C5)
folds `soft_s` into the steady-state one: `max(f_b * max(Z_b, F_{v(d),b} + z_d), hard_b)`.
The floor here is `hard_b` (`target_storage.free_space_hard_bytes`), not
`soft_b`.

Section 8.1's own formula does not mention a floor at all. There is no reason
a storage's configured minimum free space should stop applying just because a
migration happens to be in flight. `hard_b` (not `soft_b`) is what this
transient state is allowed to relax to.

With the default `hard: null` (`hard_b = soft_b`) the two floors coincide.
The check is exactly as strong as it would be with `soft_b`. An operator who
sets `hard` below `soft` deliberately allows a bounded, in-flight dip. The
finished plan still leaves that storage compliant (`.agents/domain-invariants.md`
section 2a). `topology.py` resolves both floors onto the `Storage` this
function already receives. No separate parameter threads either one in here.

## The heuristic can accept a residual violation; the scheduler cannot execute one

`heuristic.py`'s repair step can leave a storage still violating (C5). That
happens if no reachable assignment can fully clear it. The outcome is
genuine and sometimes unavoidable. The objective's `reserve_penalty_term`
reports it rather than hides it (see `90-heuristic.md`).

When `order_moves()` is asked to schedule the move that leads to exactly that
residual state, the transient check correctly says no. Landing a disk on a
target that still would not satisfy (C5) is not transient-feasible, full stop.
This module never treats "the heuristic already decided this was the best
available" as a reason to relax that.

The result is a deadlock report for that move. Section 8.3 option 3 is
"report... never force a move that breaches the reserve". The report is an
honest "this cannot be safely executed", not a false all-clear.

See `test_plan_reports_a_deadlock_when_even_the_best_target_still_violates` in
`tests/unit/test_cli.py` for the exact scenario, reproduced end to end.

## `final_assignment` is the schedule's own truth, not the heuristic's target

`ScheduleResult.final_assignment` is the assignment produced by actually
applying `order` in sequence. It starts from the current placement. It covers
every disk, not only the moved ones.

When nothing deadlocks, `final_assignment` is identical to the heuristic's
target assignment. When `deadlocked` is non-empty, the two assignments differ.
This is true when every move is deadlocked. It is also true, more subtly, when
only some moves are.

A caller reporting an "after" utilization/spread must evaluate
`final_assignment`, not `heuristic.HeuristicResult.assignment`. Otherwise the
caller reports numbers for moves that were never actually scheduled (REVIEW.md
R-02). `cli.py`'s `plan` originally did exactly this. That was correct only
when `order_moves()` scheduled every move a plan proposed.

## What this pass deliberately does not do

- **Reasoning about concurrency at scheduling time.** This module always
  produces one, strictly-sequential *order*. `execute.py`'s own executor is
  what actually runs several of that order's moves at once under
  `execution.max_concurrent_migrations > 1`. It re-validates section 8.1's
  generalized invariant live against whatever really ends up in flight
  together (see `92-execute.md`'s "Concurrent execution" section).
  `payback.py`'s move-duration estimates would let this module choose a
  smarter, concurrency-aware *order*, for example front-loading moves that can
  provably run together. The module instead leaves that entirely to
  `execute.py`'s own strict-FIFO launch discipline. That scheduling-time
  optimization is not implemented.
- **Ordering priority 2** ("moves that free space a later move needs") and
  **staging** (section 8.3 option 1). Both are refinements over a plan that is
  already feasible and safe without them. Priority 2 only affects how well a
  plan front-loads its value if interrupted. Staging only helps in a genuine
  pebble-motion deadlock. Omitting them can only make this module report a
  deadlock in a case a more sophisticated scheduler would have found a way
  through. Omitting them can never make
  this module produce an order that it considers safe but that is not safe.
- **Cooldowns**. `order_moves()` takes no cooldown input. The gates and the
  solvers apply cooldowns before a plan exists (`80-gates.md`,
  `90-heuristic.md`). `state.json` stores them after a run (`15-state.md`).

## Wired into `plan` and `apply`

`_plan_group()` in `cli.py` solves, schedules and prices every group that the
gate says to act on. It calls `schedule.order_moves()` for the schedule. Both
`plan` and `apply` call `_plan_group()`. `apply` therefore executes the order that
this module computes (see `92-execute.md`). `docs/manual/27-plan.md` describes the
rendered result.
