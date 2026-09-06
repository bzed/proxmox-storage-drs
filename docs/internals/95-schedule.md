# Ordering the moves

**What does this page answer?** How does `schedule.py` turn a target
assignment into an ordered, transient-feasible sequence of moves, and what
happens when no order exists? Describes `proxmox_storage_drs/schedule.py`.

## One loop, reusing `heuristic.py`'s objective for the ratio

`order_moves()` implements section 8.2's pseudocode directly: while there
are pending moves, find the ones that are transient-feasible right now,
schedule the best by imbalance-reduction-per-byte (moves that resolve a
currently-violating storage win outright, regardless of that ratio), apply
it, repeat. "Imbalance reduction" is computed by calling
`heuristic.evaluate_assignment()` twice (before/after the candidate move)
and diffing `.imbalance_term` — not a second formula, the same one
`heuristic.py` already computes, so a plan's ordering agrees with whatever
`objective.spread_metric` is configured exactly the way the assignment
that produced it did.

## `cost_m` is `z_d` — and that is not an approximation today

Section 8.2's ratio is "imbalance reduction / `cost_m`". `cost_m` here is
simply the disk's size in bytes, not `payback.py`'s real duration-based
cost (mirror time plus, when `saferemove` is on, wipe time — and wipe
*throughput* is a per-storage config value, so two candidate moves off
different sources can have genuinely different wipe costs even for the
same `z_d`). `migration.bwlimit_bytes_per_sec` is one global config value,
so every move's *mirror* duration alone is `z_d / bwlimit`, a constant
divided into every disk's size equally — dividing an imbalance reduction
by `z_d` and dividing it by `z_d / bwlimit` produce the **same ordering**
(`bwlimit` is a positive constant common to every candidate). So
`cost_m = z_d` reproduces the true mirror-only ordering exactly, but is an
approximation once a group has moves whose `saferemove` wipe cost differs
enough to change the ranking `payback.py`'s full cost would produce.
Scoring candidates by `payback.compute_move_cost()` instead of `z_d` is a
natural follow-up, not yet done: this module predates `payback.py` and
has not been revisited to consume it (REVIEW.md R-04).

## The transient invariant, called with a single-move set always

Section 8.1 defines a generalized invariant over a whole in-flight set `M`
specifically so it can be "implement[ed] as the single feasibility
predicate and call[ed] with `M = {m}` for the sequential case" — this
module is that sequential case, always. `transient_invariant_ok()` checks
one move against `state`, the assignment as of immediately before that
move starts; every previously-scheduled move is assumed **fully
complete** by then (mirror finished, and any `saferemove` wipe finished,
source genuinely freed) before this one begins. That models
`schedule.order_moves()`'s own job correctly regardless of
`execution.max_concurrent_migrations` — it always computes one, strictly
-sequential *order*; that order becomes a launch queue several moves can
run against concurrently only once `execute.py`'s own executor gets hold
of it (`92-execute.md`'s "Concurrent execution" section) — this module
itself never reasons about overlapping in-flight windows, and does not
need to, since `execute.py`'s own live re-checks (below) are what
actually enforce the invariant against whatever really ends up running
together.

The actual arithmetic — `used_b + sum(z_m) + f_b * max(Z_b, max(z_m)) <=
C_b` — lives in `reserve.transient_charge_ok()`, taking a *list* of
charges rather than one disk, so it degenerates to section 8.1's original
single-move form when called with `[disk.size_bytes]` (what this module
does) and generalizes correctly to several moves landing on the same
storage at once when `execute._launch_decision()` calls it with more than
one, for real, under concurrent execution (AGENTS.md section 5: this is
the *one* place that formula is written, not two functions that happen to
agree). `execute._live_transient_check()` (sequential) and
`execute._launch_decision()` (concurrent) both call it against a live
`storage_status()` read instead of this module's model-derived numbers —
see `92-execute.md`.

The `min_free_bytes` floor is folded into the transient check the same way
(C5) folds it into the steady-state one (`max(f_b * max(Z_b, z_d),
min_free_bytes)`) — the plan's own section 8.1 formula does not mention
the floor, but there is no reason a storage's absolute minimum free space
should stop applying just because a migration happens to be in flight.

## The heuristic can accept a residual violation; the scheduler cannot execute one

`heuristic.py`'s repair step can leave a storage still violating (C5) if
no reachable assignment can fully clear it — a genuine, sometimes
unavoidable outcome the objective's `reserve_penalty_term` reports rather
than hides (see `90-heuristic.md`). When `order_moves()` is asked to
schedule the move that leads to exactly that residual state, the
transient check correctly says no: landing a disk on a target that still
would not satisfy (C5) is not transient-feasible, full stop, and this
module never treats "the heuristic already decided this was the best
available" as a reason to relax that. The result is a deadlock report
for that move (section 8.3 option 3, "report... never force a move that
breaches the reserve") — an honest "this cannot be safely executed",
not a false all-clear. See
`test_plan_reports_a_deadlock_when_even_the_best_target_still_violates`
in `tests/unit/test_cli.py` for the exact scenario reproduced end to end.

## `final_assignment` is the schedule's own truth, not the heuristic's target

`ScheduleResult.final_assignment` is the assignment produced by actually
applying `order` in sequence, starting from the current placement — every
disk, not only the moved ones. When nothing deadlocks it is identical to
the heuristic's target assignment, but when `deadlocked` is non-empty
(fully or, more subtly, only partially) it is not: a caller reporting an
"after" utilization/spread must evaluate `final_assignment`, not
`heuristic.HeuristicResult.assignment`, or it reports numbers for moves
that were never actually scheduled (REVIEW.md R-02 — `cli.py`'s `plan`
originally did exactly this, correct only when `order_moves()` scheduled
every move a plan proposed).

## What this pass deliberately does not do

- **Reasoning about concurrency at scheduling time.** This module always
  produces one, strictly-sequential *order* -- `execute.py`'s own
  executor is what actually runs several of that order's moves at once
  under `execution.max_concurrent_migrations > 1`, re-validating section
  8.1's generalized invariant live against whatever really ends up
  in flight together (`92-execute.md`'s "Concurrent execution" section).
  `payback.py`'s move-duration estimates would let this module choose a
  smarter, concurrency-aware *order* (e.g. front-loading moves that can
  provably run together) instead of leaving that entirely to
  `execute.py`'s own strict-FIFO launch discipline, but that scheduling
  -time optimization is not implemented.
- **Ordering priority 2** ("moves that free space a later move needs") and
  **staging** (section 8.3 option 1). Both are refinements over a plan
  that is already feasible and safe without them — priority 2 only
  affects how well a plan front-loads its value if interrupted, and
  staging only helps in a genuine pebble-motion deadlock. Omitting them
  can only make this module report a deadlock in a case a more
  sophisticated scheduler would have found a way through; it can never
  produce an order this module thinks is safe but is not.
- **Cooldowns**, for the same reason `gates.py` doesn't implement them yet:
  `state.json` (section 11.2), which would record the timestamps a real
  cooldown check needs, does not exist.
- **The section 7.3 saturation check** — belongs with `payback.py`
  (implemented; see `96-payback.md` for why the check itself is deferred).

## Wired into `plan`, not yet into `apply`

`cli.py`'s `plan` command calls `heuristic.run_heuristic()` then
`schedule.order_moves()` for every group the gate says to act on, and
renders the result (see `docs/manual/27-plan.md`). Nothing calls
`schedule.py` from `apply` yet, because `apply` itself does not exist
(`execute.py`, phase 7+) — `plan` only ever computes and prints.
