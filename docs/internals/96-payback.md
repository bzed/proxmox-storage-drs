# Migration cost and the payback test

**What does this page answer?** How does `payback.py` turn a scheduled
move into a cost, a plan into a benefit, and the two into an accept/reject
verdict — and why does a reserve-fixing plan always pass? Describes
`proxmox_storage_drs/payback.py`.

## Cost and benefit are computed from data other modules already have

`compute_move_cost()` needs only a `schedule.ScheduledMove` and its
source `topology.Storage` — no new fetch, no new state. `duration_mirror`
is `z_d / migration.bwlimit_bytes_per_sec`; `duration_wipe` is `z_d /
saferemove_throughput` when `migration.account_saferemove_wipe` and the
source has `saferemove` on, else zero. `compute_benefit_load_seconds()`
takes two `heuristic.ObjectiveBreakdown.imbalance_term` values — the
pre-plan and post-plan `E` — and multiplies their difference by
`migration.payback_horizon_seconds`; `heuristic.HeuristicResult` already
carries both (`initial_breakdown`/`breakdown`), so `cli.py`'s `plan`
handler passes them straight through.

## `headroom_src`/`headroom_dst`: a plan formula this project cannot fill in

Section 7.1 writes `duration_mirror_d = z_d / min(bwlimit, headroom_src,
headroom_dst)`. Neither `headroom_src` nor `headroom_dst` is defined
anywhere else in `IMPLEMENTATION_PLAN.md`, and no config field or
`topology.Storage` attribute represents a per-storage effective throughput
ceiling distinct from the one global `migration.bwlimit_bytes_per_sec`.
`compute_move_cost()` uses `z_d / bwlimit` only — exactly what the
formula reduces to whenever neither storage's own throughput is the
binding constraint, which is the case `bwlimit` exists to enforce in the
first place. This is recorded as a known simplification of the plan's own
underspecified formula, not silently worked around.

## The reserve-override exemption

Section 7's payback test weighs a move's cost against the *balance*
benefit it buys. That framing has an edge it does not name: a move
resolving an active (C4)/(C5) violation is not optional the way a
balance-driven move is, and its "benefit" under the section 7.2 formula
can easily be zero or even structurally zero — moving the only loaded disk
in a two-storage group between the two storages changes which one carries
it without changing `E` at all, no matter how urgently the move is needed
for capacity reasons. Rejecting that move on economic grounds would
contradict section 13's own "the reserve is never traded against
balance," which `gates.py` already treats as absolute for the drift/
imbalance gates. `evaluate_plan_payback()` applies the identical rule
here: **a plan containing any move with `resolves_reserve_violation=True`
always passes the aggregate ratio test**, regardless of the computed
`ratio`. The hard per-move `max_single_move_duration` rule is not
exempted this way — section 7.3 lists it as applying "regardless of the
aggregate test" precisely because it is an operational limit (a mirror
that takes that long has other costs an economic ratio does not capture),
not an economic one.

`test_plan_json_output` and
`test_plan_json_output_accepts_payback_when_saferemove_is_off` in
`tests/unit/test_cli.py` exercise both halves of this end to end: the
same reserve-driven, zero-benefit move is accepted when its duration is
within the limit and rejected (correctly, via the hard rule, not the
economic one) when a slow `saferemove` wipe pushes it over
`max_single_move_duration`.

## The section 7.3 saturation guard: `compute_move_cost()`'s optional `target`

`compute_move_cost()` stays pure (the module docstring's own promise:
"nothing fetches anything") by taking the guard's inputs already
computed, rather than fetching a forecast itself: `target`, and
`l_hat_src`/`l_hat_dst` — the caller's own already-computed
`L_hat_s(duration_mirror)` for each endpoint
(`forecast.storage_upper_bound()`, section 10.1, summed over the disks
*currently* resident on that storage — not the moving disk's own
hypothetical arrival, since during mirroring it is still served from
`src`, and its mirror-write traffic to `dst` is exactly what the
`ω_dst` charge below already accounts for separately). Left at their
defaults (`target=None`, both `0.0`) the check is simply inactive — every
call site written before this existed, and `cli.py`'s own `dry-run`/
`plan` paths that have not been updated to compute a forecast, keep
working unchanged.

`mirror_duration_seconds()` is `compute_move_cost()`'s own
`duration_mirror_d` arithmetic, factored out so a caller can learn it
*before* calling `compute_move_cost()` — a genuine ordering dependency:
the guard's forecast horizon is this move's own mirror duration, but
`compute_move_cost()` is also what turns that forecast into the
`saturation_deferred` verdict. A caller wanting the check active must:
call `mirror_duration_seconds()`, use it as the horizon for
`forecast.storage_upper_bound()` against each endpoint's own resident
disks, then call `compute_move_cost()` with the results.

`_saturation_deferred()` charges `migration.source_load_weight`/
`target_load_weight` (`ω_src`/`ω_dst`) on top of each endpoint's own
`l_hat`, matching section 7.3's `ω_role` table for the mirroring state —
the same two config values `compute_move_cost()`'s own cost formula
already uses (AGENTS.md section 5: no second pair of weights invented
for this). `MoveCost.saturation_deferred`/`PaybackResult.deferred_moves`
mirror `exceeds_max_duration`/`rejected_moves`'s existing shape exactly,
but are kept as distinct fields — section 7.3 itself draws the same
distinction ("reject the move" vs. "defer the move to a later run"), and
a report should be able to say which of the two happened, one hard and
always active, the other best-effort and silently inactive wherever
`saturation_load` is unset. `PaybackResult.accepted` now requires
neither being non-empty.

## What this pass deliberately does not do

- **The 3-retry re-solve-with-doubled-`beta`/`gamma` loop** (section 7.3)
  on aggregate payback failure. A real UX refinement — it converges on the
  smaller subset of high-value moves rather than abandoning the run — but
  not a correctness requirement: reporting accept/reject plainly already
  satisfies "reject a plan whose cost outweighs its benefit." Implementing
  the loop means re-invoking `heuristic.py`/`schedule.py` with adjusted
  weights from inside `cli.py`'s own orchestration, which is where it
  belongs when it is built, not half-done inside this module now.
- **Automatically dropping an individually-rejected move** and
  re-solving without it. Reported instead
  (`MoveCost.exceeds_max_duration`, `PaybackResult.rejected_moves`) — the
  same "report, never force" choice `schedule.py`'s deadlock reporting
  already makes for an unschedulable move.
- **The section 7.3 saturation-ceiling defer check beyond its mirroring
  -phase reading.** `compute_move_cost()` now implements `L_during(s) <=
  saturation_ceiling * N_s` for each endpoint (see the section above),
  but only at the mirroring-phase horizon the section's own
  header names ("push either endpoint above ... during *the mirror*") —
  not a second, separate check for the *draining* phase (`ω_wipe` over
  `duration_wipe_seconds`), which the full generalized in-flight-set
  model implies but which needs `schedule.py` to reason about overlapping
  moves, something it does not do (`95-schedule.md`). `N_s` unset on a
  storage still skips the check for that endpoint entirely, exactly as
  the plan's own words allow ("fully supported... loses only this one
  advisory check").

## Wired into `plan` and `apply` alike, via `_plan_group()`

`cli.py`'s `_plan_group()` (`docs/internals/92-execute.md`'s "one planning
pipeline, shared by `plan` and `apply`") computes a `PaybackResult` for
every group the gate acts on, right after scheduling its moves, and both
`plan`'s render functions and `apply`'s payback gate
(`_apply_payback_gate()`) consume it — a rejected or deferred move never
reaches `execute.py` regardless of mode. `_saturation_forecast_inputs()`
is what builds the saturation guard's own forecaster and per-disk load
history, once per group, only when at least one of its storages
configures `saturation_load` — skipped entirely otherwise, so a cluster
that never sets it pays no Prometheus cost for a check it cannot use.
`_compute_one_move_cost()` then derives each move's own
`l_hat_src`/`l_hat_dst` (`forecast.storage_upper_bound()` over each
endpoint's *currently* resident disks, at that move's own mirror
duration) before calling `compute_move_cost()`. `compute_wipe_duration_seconds()`
is also used by `verify-storages`'s existing wipe-time warning — one
implementation of the formula, not two (AGENTS.md section 5).
