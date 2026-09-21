# Reading `plan`

`plan` computes what `pve-storage-drs` would do and prints it. It never
changes anything, in any `execution.mode` — that is `apply`'s job (see
`docs/manual/28-apply.md`), and it needs a separate, explicit invocation to
run at all.

For each group, `plan`:

1. Fetches the same load (`ℓ_d`/`L_s`/`u_s`) `show-load` does, and
   evaluates the same section 6 gate.
2. If the gate says `NO ACTION`, stops there for that group — no solver
   runs, nothing more to show.
3. If it says `ACT`, solves it with whichever backend `solver.backend`
   selects (see `docs/internals/91-optimize.md` for the CP-SAT/CBC
   backends and `docs/internals/90-heuristic.md` for the dependency-free
   one) to compute a target assignment, orders its moves under the
   **transient reserve invariant** — while a move is in flight, the disk
   being migrated exists on *both* its source and target storage at once
   (the mirror is fully allocated on the target before the old copy is
   removed from the source), so the target's own snapshot reserve must
   already hold with that disk's bytes counted in, not only once the
   source frees them afterwards (`IMPLEMENTATION_PLAN.md` section 8.1 has
   the full formula, including the generalization to several moves
   landing on the same storage at once under concurrent execution — see
   `docs/manual/28-apply.md`) — and checks the whole plan against the
   payback rule below.

This example uses the same section 14 worked example `show-load`'s manual
page does, at the default weights (the two-move plan) and
`solver.backend: auto` with neither MILP library installed, so it falls
back to the heuristic — the numbers are traceable to that section either
way, since every backend reports through the identical objective
function:

```
$ pve-storage-drs -c /etc/pve/drs.yaml plan
Group fc-tier1 → ACT: reserve violated on san-a; acting now regardless of the normal drift/imbalance thresholds -- a capacity shortfall is never delayed by them
  solver: heuristic
  1. db01(102):scsi0            san-a → san-c     1.50 TiB   ~2.2h   Δimbalance -4.53   ℓ/z 1.67
  2. web01(101):scsi1           san-a → san-b     1.00 TiB   ~1.5h   Δimbalance -2.00   ℓ/z 1.00
  after: san-a=3.00  san-b=1.70  san-c=2.70
  spread: 255.4% → 52.7%
  payback: benefit 1.93e+08 load·s vs cost 2.62e+04 load·s → ratio 7.34e+03 (need 10) ✓
```

The `solver:` line names whichever backend actually produced this plan --
`heuristic`, `cpsat` or `cbc` -- plus, for a MILP backend, `(optimal)` or
`(feasible)` (the gap was not proven closed within `solver.time_limit_seconds`,
but a solution was still found). It is not always what `solver.backend`
says: `auto` tries CP-SAT then CBC before the heuristic, and even an
explicitly forced `cpsat`/`cbc` falls back to the heuristic (logged as a
warning in that case) rather than failing the whole run, if that library
is not installed or cannot solve within the time limit -- see
`docs/internals/91-optimize.md`.

The `after:`/`spread:` lines (and the payback numbers) reflect what the
scheduler actually managed to order, not the solver's target assignment —
identical here since both moves scheduled cleanly, but see the
deadlock note below for when a plan cannot schedule everything it proposed.

A group the gate does not act on prints one line and stops:

```
Group fc-tier2 → NO ACTION: imbalance 0.0% is below gates.imbalance_threshold (20.0%)
```

## Reading a move line

`1. db01(102):scsi0  san-a → san-c  1.50 TiB  ~2.2h  Δimbalance -4.53  ℓ/z 1.67` —
the disk (its VM's name, then its vmid in parentheses, then the device), its
current and target storage, its size, the estimated mirror
duration (`size / migration.bwlimit_bytes_per_sec`, plus a `+wipe <time>`
suffix when `saferemove` on the source storage adds one — see the payback
section below), this move's own effect on the group's imbalance metric at
the moment it was scheduled (negative means imbalance went down, which is
the usual case; a move scheduled mainly to resolve a reserve violation or
consolidate a VM can show a positive value and still be correct), and
`ℓ/z` — load per TiB, section 7.3's own "single best indicator of a good
migration candidate: high I/O concentrated in a small disk."

A move whose own duration exceeds `migration.max_single_move_duration`
carries a `⚠ exceeds migration.max_single_move_duration` suffix and always
fails the plan (see below) — this is a hard, per-move rule, independent of
whether the plan as a whole looks profitable.

A move scheduled first *regardless* of its ratio — because the storage it
leaves is currently breaching its snapshot reserve or its configured
`free_space.soft` requirement, the capacity a storage must always keep
free, sized to the larger of `snapshot_reserve.factor` times its largest
disk or `free_space.soft` (`IMPLEMENTATION_PLAN.md` section 5.3,
constraints (C4)/(C5)/5.3.1) — is implied by the `ACT: reserve violated
on ...` header in human output. Safety is not subject to hysteresis
(section 13), so this always wins over a purely balance-driven move.

`repair` (visible in `--json`, `[repair]` in human output) marks a move
the plan's own shortfall *depends on*: holding that one disk back on its
current storage, in the plan actually executed, would leave the group
short by more than it is. This is not the same question as "did this
move's own source violate something" — an *indirect* repair (a move that
empties the destination another repair needs) is marked too, even though
its own source was clean, and a *redundant* repair (either of two moves
alone would fix the violation) is marked on neither, since holding back
just one still leaves the other to finish the job. See the `payback:`
line below for what the plan as a whole being exempt actually depends on
— a per-move `repair: true` marker is a report, not itself the trigger.

**A `⚠` line means a deadlock, not a hidden failure.** If the target
assignment includes a move this run cannot find any transient-feasible
order for, `plan` says so explicitly (`IMPLEMENTATION_PLAN.md` section
8.3's "report, never force" path — staging and plan-splitting are not yet
implemented, so this is where a genuine cycle or an unavoidable capacity
shortfall currently surfaces) rather than silently omitting the move or,
worse, telling you a plan is clean when part of it is not achievable. When
only *some* moves deadlock, the `after:`/`spread:`/`payback:` lines report
the state reachable by the moves that did schedule, never the fuller
picture the undeliverable ones would have produced.

## The `payback:` line

Section 7.3's acceptance test: `benefit >= migration.payback_ratio * cost`,
both sides in load-seconds. `benefit` is `(alpha_spread * ΔE +
delta_capacity_spread * ΔF + kappa_vm_affinity * ΔA) *
migration.payback_horizon` (section 7.2's own *unweighted* `E`/`F`/`A`, not the
solver's already-scaled objective terms — passing those instead would
double-apply the weight); `ΔA` may be negative, and then it reduces the
benefit — a balance move that splits a VM pays for that fragmentation out
of its other gains. `E_after`/`F_after`/`A_after` are evaluated against
what `plan`'s own scheduler actually managed to order, not the solver's
aspirational target, so a partially-deadlocked plan is scored on the moves
it can really make, not ones it cannot. `cost` sums every *scheduled*
move's `duration_mirror * (source_load_weight + target_load_weight) +
duration_wipe * wipe_load_weight`, except a disk below
`migration.tiny_disk_bytes`, which costs `0` regardless of duration
(section 7.1). A ✓ plan passed; a ✗ one did not. A plan made entirely of
moves below `migration.tiny_disk_bytes` has `cost = 0` and renders as
`ratio inf (need 10) ✓` — a real, correct verdict, not a formatting bug.

A ✗ plan can fail for two different reasons, reported as two different
lines, because they call for different fixes:

- **Economic failure** — the balance benefit does not outweigh the
  migration cost. Adjust `objective`'s weights, `migration.payback_ratio`,
  or accept the plan is not worth running.
- **Hard-duration failure** — some move's own `duration_mirror +
  duration_wipe` exceeds `migration.max_single_move_duration`, regardless
  of whether the plan as a whole is profitable. Fix `saferemove`
  throughput, `migration.bwlimit_bytes_per_sec`, or the duration limit
  itself.

Either, both, or neither can apply to the same plan; `plan` names exactly
which happened rather than one generic "does not pass the payback test"
line for both.

**A plan that leaves the group with less reserve/free-space shortfall
than it found always passes this test**, regardless of the ratio shown —
the example above happens to pass on merit (133 ≥ 10), but a plan whose
*only* move fixes a snapshot-reserve or `free_space.soft` violation with
zero balance benefit (a real, common case: relocating the sole loaded
disk in a two-storage group changes which side carries it without
reducing spread at all) is accepted too. This is `--json`'s
`payback.repair_exempt`, decided on the plan's *outcome* — its executed
endpoint's `Σ r_s` strictly below the current assignment's
(`payback.reserve_shortfall_bytes_before`/`_after`) — not on any one
move's own flag, so a plan that moves a disk off a violating storage but
leaves the group no less short in total is **not** exempt. Section 13's
"the reserve is never traded against balance" applies here exactly as it
does to the gates: an operator does not get to decline a capacity
emergency fix because it scores poorly against `migration.payback_ratio`.
The hard per-move duration rule is not exempted this way — it is an
operational limit, not an economic one, and still blocks the plan, and a
move it excludes is also excluded from what `repair_exempt` scores: a
repair a hard rule then blocks is correctly not exempt either.

**What a ✗ (or a rejected move) does *not* do today: automatically make
the plan smaller and retry.** Section 7.3 describes re-solving with `beta`
and `gamma` doubled, up to three times, converging on the highest-value
subset of moves. That loop is not implemented — a failing plan is reported
and left for you to review, not silently adjusted. See
`docs/internals/96-payback.md`.

## What `plan` does not yet do

- **No pinned block, fragmentation naming, or pinned-load line.** Unlike
  `IMPLEMENTATION_PLAN.md` section 9.5's own example, `plan`/`apply` print
  only the move list and payback verdict — that narration (including the
  per-pin `→` action hint) lives in `pve-storage-drs explain` instead
  (`docs/manual/29-explain.md`); `show-load` also shows each pin inline,
  per disk.
- **No automatic re-solve-and-shrink on a failing payback test** (see
  above) — reported, not fixed for you.
- **The section 7.3 saturation-ceiling defer check only covers the
  mirroring phase**, not a second, separate check for the *draining*
  phase a `saferemove` wipe holds a storage in afterward — that needs
  `schedule.py` to reason about which moves actually overlap in time,
  which it does not do. The check itself is otherwise active for any
  storage that configures `saturation_load` (still none in this
  project's own dogfooding cluster) — a deferred move is reported
  separately from a hard-duration-rejected one (`deferred_moves`, not
  `rejected_moves`) and excluded from `apply` the same way. See
  `docs/internals/96-payback.md`.
- **`plan` itself still only reads `state.json`, never writes it.** Its
  gate reads real `last_balance` history when a group has one recorded
  (see `docs/internals/15-state.md`), and a disk/storage cooldown pins or
  excludes exactly as described below -- but `plan` never executes a
  migration, so it never has anything of its own to record. `apply` is
  what writes `last_balance` and cooldowns now, after a run that actually
  executed at least one migration (`docs/manual/28-apply.md`); a group
  with no `state.json` yet, or one `apply` has never touched, still
  evaluates as a first run (drift gate skipped).
- **Cooldowns.** A disk moved within `gates.cooldown_per_disk` is pinned
  and excluded from this run's solve — `plan` itself does not print pins
  at all (see above); `show-load`/`explain` both show it as
  `[pinned: cooldown: ...]`. A storage that was a migration's
  *destination* within `gates.cooldown_per_storage` accepts no new
  incoming moves from the heuristic. See `docs/internals/15-state.md`,
  `docs/internals/60-topology.md`
  and `docs/internals/90-heuristic.md`.
- **No staging, no concurrent scheduling.** Documented as deliberate, not
  forgotten, in `docs/internals/95-schedule.md`.

`--json` emits `groups[]`, each with `gate` (identical shape to
`show-load`'s), `solver_backend`/`solver_status` (`null`/`null` when the
gate said `NO ACTION`; otherwise `"heuristic"`/`null`, or `"cpsat"`/
`"cbc"` with `"optimal"`/`"feasible"` -- the same information the human
output's `solver:` line names), `moves[]` (`disk_key`, `vmid`, `vm_name`, `device`,
`from_storage`, `to_storage`, `size_bytes`, `imbalance_reduction`,
`repair` (the section 7.3 revert-test marker — see "The `payback:` line"
above), `load_per_tib`, `duration_mirror_seconds`,
`duration_wipe_seconds`, `cost_load_seconds`, `exceeds_max_duration`),
`deadlocked` (a list of disk keys) and `deadlock_message` (`null` if none),
`before_spread`/`after_spread` (the section 6 spread fraction, before the
plan and after every scheduled move), `before_capacity_spread`/
`after_capacity_spread` (the section 5.3 (C7) fill-fraction spread the same
way, `null` for a group whose mean fill is 0 or that has not solved),
`before_objective_total`/`after_objective_total` (the section 5.4 objective's
full `.total`, `evaluate_assignment()` re-scored at the same true weights
`validate_corpus.py`'s cross-backend check uses -- REVIEW.md AA-01), `load_error`
(`null` unless Prometheus failed for this group), and `payback` — `null` when there is no
`GroupLoad` or the gate said `NO ACTION`, otherwise an object with
`benefit_load_seconds`, `total_cost_load_seconds`, `ratio`, `aggregate_ok`
(the economic test alone, or `true` if exempted), `repair_exempt` (the
outcome trigger itself — see above), `reserve_shortfall_bytes_before`/
`_after` (`Σ r_s` on the current assignment and on the plan's executed
endpoint, what `repair_exempt` is decided from), `rejected_moves` (disk
keys failing the hard duration rule), `deferred_moves` (disk keys deferred
by the section 7.3 saturation guard — empty unless a storage in the group
configures `saturation_load`) and `accepted` (`aggregate_ok` and neither
list non-empty).
