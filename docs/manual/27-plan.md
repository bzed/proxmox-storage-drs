# Reading `plan`

`plan` computes what `pve-storage-drs` would do and prints it. It never
changes anything, in any `execution.mode` — that is `apply`'s job (not yet
implemented; see `30-safety-and-status.md`), and it needs a separate,
explicit invocation to run at all.

For each group, `plan`:

1. Fetches the same load (`ℓ_d`/`L_s`/`u_s`) `show-load` does, and
   evaluates the same section 6 gate.
2. If the gate says `NO ACTION`, stops there for that group — no solver
   runs, nothing more to show.
3. If it says `ACT`, runs the heuristic solver (`IMPLEMENTATION_PLAN.md`
   section 5.4/5.5) to compute a target assignment, orders its moves under
   the section 8 transient reserve invariant, and checks the whole plan
   against section 7's payback rule.

This example uses the same section 14 worked example `show-load`'s manual
page does, at the default weights (the three-move plan), so the numbers
are traceable to that section:

```
$ pve-storage-drs -c /etc/pve/drs.yaml plan
Group fc-tier1 → ACT: reserve violated on san-a; bypassing the drift and imbalance gates (section 13: safety is not subject to hysteresis)
  1. 102:scsi0      san-a → san-c     1.50 TiB   ~2.2h   Δimbalance -4.53   ℓ/z 1.67
  2. 101:scsi1      san-a → san-b     1.00 TiB   ~1.5h   Δimbalance -2.00   ℓ/z 1.00
  3. 105:scsi0      san-c → san-b   512.00 GiB   ~43.7m   Δimbalance -0.40   ℓ/z 0.40
  after: san-a=3.00  san-b=1.90  san-c=2.50
  spread: 255.4% → 44.6%
  payback: benefit 4.19e+06 load·s vs cost 3.15e+04 load·s → ratio 133 (need 10) ✓
```

The `after:`/`spread:` lines (and the payback numbers) reflect what the
scheduler actually managed to order, not the solver's target assignment —
identical here since all three moves scheduled cleanly, but see the
deadlock note below for when a plan cannot schedule everything it proposed.

A group the gate does not act on prints one line and stops:

```
Group fc-tier2 → NO ACTION: imbalance 0.0% is below gates.imbalance_threshold (20.0%)
```

## Reading a move line

`1. 102:scsi0  san-a → san-c  1.50 TiB  ~2.2h  Δimbalance -4.53  ℓ/z 1.67` —
the disk, its current and target storage, its size, the estimated mirror
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

`resolves_reserve_violation` (visible in `--json`, and implied by the
`ACT: reserve violated on ...` header in human output) marks a move
scheduled first *regardless* of its ratio, because the storage it leaves
is currently breaching (C4)/(C5) — safety is not subject to hysteresis
(section 13), so this always wins over a purely balance-driven move.

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
both sides in load-seconds. `benefit` is `(E_before - E_after) *
migration.payback_horizon` (section 7.2's own *unweighted* `E`, not the
solver's `alpha_spread`-scaled objective term — the two agree numerically
at the default `alpha_spread: 1.0`, but the payback ratio must not depend
on that tuning knob); `E_after` is evaluated against what `plan`'s own
scheduler actually managed to order, not the solver's aspirational target,
so a partially-deadlocked plan is scored on the moves it can really make,
not ones it cannot. `cost` sums every *scheduled* move's `duration_mirror *
(source_load_weight + target_load_weight) + duration_wipe *
wipe_load_weight` (section 7.1). A ✓ plan passed; a ✗ one did not.

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

**A plan resolving a reserve violation always passes this test**,
regardless of the ratio shown — the example above happens to pass on
merit (133 ≥ 10), but a plan whose *only* move fixes a (C4)/(C5) violation
with zero balance benefit (a real, common case: relocating the sole loaded
disk in a two-storage group changes which side carries it without
reducing spread at all) is accepted too. Section 13's "the reserve is
never traded against balance" applies here exactly as it does to the
gates: an operator does not get to decline a capacity emergency fix
because it scores poorly against `migration.payback_ratio`. The hard
per-move duration rule is not exempted this way — it is an operational
limit, not an economic one, and still blocks the plan.

**What a ✗ (or a rejected move) does *not* do today: automatically make
the plan smaller and retry.** Section 7.3 describes re-solving with `beta`
and `gamma` doubled, up to three times, converging on the highest-value
subset of moves. That loop is not implemented — a failing plan is reported
and left for you to review, not silently adjusted. See
`docs/internals/96-payback.md`.

## What `plan` does not yet do

- **No automatic re-solve-and-shrink on a failing payback test** (see
  above) — reported, not fixed for you.
- **No section 7.3 saturation-ceiling defer check.** Needs a forecaster
  upper bound this codebase does not compute yet, and no group in this
  project's own dogfooding cluster has `saturation_load` set — which the
  plan itself says is "fully supported... loses only this one advisory
  check." `max_single_move_duration` and the transient reserve invariant
  are the two *hard* bounds and are both already enforced.
- **No `state.json`.** Section 11.2's drift history does not exist yet, so
  the gate `plan` evaluates always treats this as the first run — see
  `docs/internals/80-gates.md` for exactly what that does and does not
  change about the verdict.
- **No cooldowns, no staging, no concurrent scheduling.** All documented
  as deliberate, not forgotten, in `docs/internals/90-heuristic.md` and
  `docs/internals/95-schedule.md`.

`--json` emits `groups[]`, each with `gate` (identical shape to
`show-load`'s), `moves[]` (`disk_key`, `vmid`, `device`, `from_storage`,
`to_storage`, `size_bytes`, `imbalance_reduction`,
`resolves_reserve_violation`, `load_per_tib`, `duration_mirror_seconds`,
`duration_wipe_seconds`, `cost_load_seconds`, `exceeds_max_duration`),
`deadlocked` (a list of disk keys) and `deadlock_message` (`null` if none),
`before_spread`/`after_spread` (the section 6 spread fraction, before the
plan and after every scheduled move), `load_error` (`null` unless
Prometheus failed for this group), and `payback` — `null` when there is no
`GroupLoad` or the gate said `NO ACTION`, otherwise an object with
`benefit_load_seconds`, `total_cost_load_seconds`, `ratio`, `aggregate_ok`
(the economic test alone, or `true` if exempted), `rejected_moves` (disk
keys failing the hard duration rule) and `accepted` (`aggregate_ok` and no
rejected move).
