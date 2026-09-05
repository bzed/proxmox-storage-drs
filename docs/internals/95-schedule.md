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
simply the disk's size in bytes. That looks like a placeholder for the
real duration-based cost section 7 defines, and it will need to become one
once `payback.py` exists and storages can have different `bwlimit`s or
wipe times — but as of this module, `migration.bwlimit_bytes_per_sec` is
one global config value, so every move's mirror duration is
`z_d / bwlimit`, a constant divided into every disk's size equally.
Dividing an imbalance reduction by `z_d` and dividing it by `z_d / bwlimit`
produce the **same ordering** (`bwlimit` is a positive constant common to
every candidate in the comparison), so `cost_m = z_d` is not an
approximation of "cost by mirror duration" here, it is that ordering
exactly, until `payback.py` gives moves individually different costs
(saferemove wipe time, per-storage throughput) that this equivalence no
longer holds for.

## The transient invariant, called with a single-move set always

Section 8.1 defines a generalized invariant over a whole in-flight set `M`
specifically so it can be "implement[ed] as the single feasibility
predicate and call[ed] with `M = {m}` for the sequential case" — this
module is that sequential case. `transient_invariant_ok()` checks one move
against `state`, the assignment as of immediately before that move starts;
every previously-scheduled move is assumed **fully complete** by then
(mirror finished, and any `saferemove` wipe finished, source genuinely
freed) before this one begins. That is the correct model for
`execution.max_concurrent_migrations: 1` (the default, and the
plan's own "recommended configuration") — see the next section for why it
is deliberately not generalized to more than one in-flight move yet.

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

## What this pass deliberately does not do

- **Concurrent scheduling** (`execution.max_concurrent_migrations > 1`).
  Reasoning correctly about overlapping in-flight windows needs move
  duration estimates from `payback.py`, which does not exist yet. This
  module schedules strictly sequentially regardless of the configured
  value; section 8.1's own generalized invariant is what a future version
  would evaluate against the real in-flight set instead of `{m}`.
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
- **The section 7.3 saturation check** — belongs with `payback.py`.

## Wired into `plan`, not yet into `apply`

`cli.py`'s `plan` command calls `heuristic.run_heuristic()` then
`schedule.order_moves()` for every group the gate says to act on, and
renders the result (see `docs/manual/27-plan.md`). Nothing calls
`schedule.py` from `apply` yet, because `apply` itself does not exist
(`execute.py`, phase 7+) — `plan` only ever computes and prints.
