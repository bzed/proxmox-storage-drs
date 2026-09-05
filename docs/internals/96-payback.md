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
- **The section 7.3 saturation-ceiling defer check**
  (`L_during(s) <= saturation_ceiling * N_s`). It needs the forecaster's
  upper bound over a horizon equal to a specific move's own duration,
  which `forecast.py`'s `Forecaster` protocol does not expose (it answers
  for `window.lookback` only); and no group in this project's own
  dogfooding cluster has `storages[].saturation_load` set, which the plan
  itself says makes this check's absence "fully supported... loses only
  this one advisory check." `max_single_move_duration` (implemented) and
  the transient reserve invariant (`schedule.py`, already enforced before
  a move is ever scheduled) are the two bounds section 7.3 calls "always
  active"; this deferred one is explicitly the best-effort extra.

## Wired into `plan`, not yet into `apply`

`cli.py`'s `_handle_plan()` computes a `PaybackResult` for every group the
gate acts on, right after scheduling its moves, and both render functions
show it (`docs/manual/27-plan.md`). `compute_wipe_duration_seconds()` is
also used by `verify-storages`'s existing wipe-time warning — one
implementation of the formula, not two (AGENTS.md section 5). Nothing
calls this module from `apply`, because `apply` does not exist yet
(`execute.py`, phase 7+).
