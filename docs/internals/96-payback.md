# Migration cost and the payback test

**What does this page answer?** How does `payback.py` turn a scheduled
move into a cost, a plan into a benefit, and the two into an accept/reject
verdict — and why does a reserve-fixing plan always pass? Describes
`proxmox_storage_drs/payback.py`.

## Cost and benefit are computed from data other modules already have

`compute_move_cost()` needs only a `schedule.ScheduledMove` and its
source `topology.Storage` — no new fetch, no new state. `duration_mirror`
is `z_d / migration.bwlimit_bytes_per_sec`; `duration_wipe` is `z_d /
|saferemove_throughput|` when `migration.account_saferemove_wipe` and the
source has `saferemove` on, else zero. `cost_load_seconds` — in the same
**load-seconds** unit (average in-flight I/O requests multiplied by
seconds) `compute_benefit_load_seconds()` produces below, which is what
makes the two comparable at all — is `duration_mirror *
(migration.source_load_weight + migration.target_load_weight) +
duration_wipe * migration.wipe_load_weight`: the extra in-flight I/O the
migration itself imposes on the source and the target while the mirror
runs, plus, for as long as the old volume takes to be zeroed, the extra
load a running `saferemove` wipe imposes on the source alone. It is zero
below `migration.tiny_disk_bytes` (section 5.4/7.1) — `duration_mirror`/
`duration_wipe` are still the real numbers, so `exceeds_max_duration`/
`saturation_deferred` still fire normally for a tiny disk that happens to
be throttled hard enough; only the economic charge is waived.

`compute_benefit_load_seconds()` implements section 7.2's `benefit =
(alpha_spread*(E_before-E_after) + delta_capacity_spread*(F_before-F_after) +
kappa_vm_affinity*(A_before-A_after)) * H` (sections 12 and, for the third
term, 5.4/7.2's affinity-payback fix). `H` is
`migration.payback_horizon_seconds` (default `365d`, converted to
seconds) — the length of time the plan's improvement is assumed to keep
paying off, which is why both sides of the payback ratio end up in the
same **load-seconds** unit: benefit is a load-shaped quantity held for
`H` seconds, and cost (below) is a duration in seconds multiplied by a
load-shaped weight. `compute_benefit_load_seconds()` itself takes the
pre-plan/post-plan pair of `heuristic.raw_spread()` values (E, the *raw*, unweighted
imbalance quantity), `heuristic.raw_capacity_spread()` values (F, the raw
data-spread quantity, section 5.3 (C7)) and `heuristic.raw_affinity_debt()`
values (A, the raw — `w_v`-weighted but not `kappa`-scaled — affinity debt,
section 5.4), plus `objective.alpha_spread`/`delta_capacity_spread`/
`kappa_vm_affinity` as explicit weight parameters, and multiplies the
weighted sum by `migration.payback_horizon_seconds`. **Never** pass
`ObjectiveBreakdown.imbalance_term`/`.capacity_spread_term`/
`.fragmentation_term`: those are the same quantities already scaled by
`alpha_spread`/`delta_capacity_spread`/`kappa_vm_affinity` for the section
5.4 *solver* objective, and passing them here would double-apply the
weight (REVIEW.md R-01 — earlier code passed `imbalance_term` directly;
only invisible while `alpha_spread`'s default of `1.0` made the two
numerically identical). Applying the weights *inside*
`compute_benefit_load_seconds()`, as explicit parameters rather than baked
into an already-scaled input, is what keeps R-01's principle intact — now
extended to all three terms, not just the first two. `cli.py`'s `plan`
handler computes all six raw values for the pre-plan and post-plan
assignments and passes them, and all three weights, through.

The `kappa` term's own inclusion here is itself the fix for a real live
failure: a plan whose entire value was reuniting VMs (two 528 KiB
`efidisk0`s among its four moves) scored `benefit 9 load·s vs cost 232
load·s → ratio 0.0388` and was refused, because the pre-fix formula had no
way to value affinity at all — see `IMPLEMENTATION_PLAN.md` section 7.2's
own account, and `tests/fixtures/affinity-repair.yaml` (section 14.7) for
the fixture built to reproduce it. `A_before - A_after` can be negative —
a balance move that *splits* a VM must pay for the fragmentation out of its
`alpha` gain — and `compute_benefit_load_seconds()` returns that negative
contribution as computed, never clamped; `evaluate_plan_payback()`'s own
acceptance test already rejects a genuinely negative benefit correctly.

## Why `compute_wipe_duration_seconds()` takes the magnitude

`saferemove_throughput` is signed, and the sign is not part of the rate.
PVE hands the configured value straight to `cstream -t`, where a
**positive** number is a session average — cstream accumulates its own
error and may exceed the rate for a while to make good on earlier
underutilization — and a **negative** number is an upper limit on each
individual read/write syscall pair, which is never exceeded. Both name
the same `|num|` bytes/second, so `-1073741824` means 1 GiB/s. Negative
values are ordinary in PVE configurations: they are what an operator
writes when they want a rate the wipe can never burst above.

`compute_wipe_duration_seconds()` is the one implementation of the
formula (AGENTS.md section 5) — `compute_move_cost()`, `cli.py`'s
`verify-storages` and `execute.py`'s `min_wipe_seconds` all go through
it — so `abs()` belongs there and nowhere else. In particular
`topology.py` deliberately keeps PVE's signed value on `Storage`:
`verify-storages --json` echoes it back verbatim so an operator can match
it against their own `storage.cfg`, and normalizing it at parse time
would quietly change what they are shown.

Dividing by the signed value was a real bug, not a cosmetic one, and the
shape of it is worth remembering. `duration_wipe` came out negative;
`duration_d = duration_mirror + duration_wipe` therefore collapsed
towards zero, and to **exactly** zero on the common configuration where
`|saferemove_throughput|` equals `migration.bwlimit_bytes_per_sec`. On
such a cluster the `max_single_move_duration` rejection (a move whose
mirror plus wipe would run longer than that is refused outright) could
not fire for a disk of any size — a hypothetical 100 TiB move reported a
total duration of 0 s and sailed past a 6 h limit — and
`verify-storages`' two warnings (`cooldown_per_storage_too_short`,
`max_single_move_duration_too_short`) were both permanently false, since
a negative number never exceeds a positive threshold. It printed
`implied wipe time for the largest disk (1.00 TiB): -17.1m` and nobody
downstream noticed. Found by replaying a corpus bundle from a cluster
whose three LVM storages all carry `saferemove_throughput -1073741824`.

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

`evaluate_plan_payback()`'s aggregate ratio test is `benefit_load_seconds
>= migration.payback_ratio * total_cost_load_seconds` (default
`payback_ratio: 10.0` — a plan's benefit must be worth at least ten
times what executing it costs, both sides in the same load-seconds unit
`compute_benefit_load_seconds()` produces above). `PaybackResult.ratio`
is that same `benefit / cost` division exposed for reporting; the test
itself never divides, to stay well-defined when `total_cost_load_seconds`
is `0`.

Section 7's payback test weighs a move's cost against the *balance*
benefit it buys. That framing has an edge it does not name: a plan
resolving an active (C4)/(C5) violation, or section 5.3.1's configured
free-space requirement, is not optional the way a balance-driven move is,
and its "benefit" under the section 7.2 formula can easily be zero or even
structurally zero — moving the only loaded disk in a two-storage group
between the two storages changes which one carries it without changing
`E` at all, no matter how urgently the move is needed for capacity
reasons. Rejecting that move on economic grounds would contradict section
13's own "the reserve is never traded against balance," which `gates.py`
already treats as absolute for the drift/imbalance gates.
`evaluate_plan_payback()` applies the identical rule, but as an
**outcome** trigger, not a per-move flag: it takes two extra parameters,
`current_shortfall_bytes` and `final_shortfall_bytes` — `Σ r_s`
(`reserve.total_shortfall_bytes()`) on the group's current assignment and
on the plan's *executed* endpoint respectively — and `repair_exempt =
final_shortfall_bytes < current_shortfall_bytes` always passes the
aggregate ratio test when true, regardless of the computed `ratio`. The
hard per-move `max_single_move_duration` rule is not exempted this way —
section 7.3 lists it as applying "regardless of the aggregate test"
precisely because it is an operational limit (a mirror that takes that
long has other costs an economic ratio does not capture), not an economic
one.

**This replaced a per-move flag** (`ScheduledMove.resolves_reserve_violation`,
still there but narrowed to section 8.2's own priority-1 scheduling
signal — "this move's source was violating when scheduled first" — never
read by payback anymore). The flag fired whenever *any* move's source was
violating at scheduling time, which is provably a superset of the outcome
trigger (`Σ r_s` can only fall if some storage's `used`/`Z_s` falls, which
needs a disk to leave a storage that was therefore violating when it
left — so every outcome-exempt plan was already flag-exempt, never the
reverse): a plan that moves a disk off a violating storage but leaves the
group no less short is flag-exempt but not outcome-exempt. The two extra
parameters are computed once, in `cli.py`'s `_plan_group()` — the
function's sole production caller — from objects it already has in hand:
`current_shortfall_bytes` is `reserve.total_shortfall_bytes()` over the
current assignment (`group.disks`' own `current_storage`);
`final_shortfall_bytes` is the same sum over `payback.
executed_assignment()`'s result, `schedule_result.final_assignment` with
every disk a hard per-move rule excluded (`exceeds_max_duration` or
`saturation_deferred`, both already known from `move_costs` by then) held
back at its current storage — "what the plan will really run," not merely
what got scheduled, so a repair a hard rule then blocks is correctly
*not* exempt.

**The revert test, `payback.repair_markers()`**, is the per-move report a
caller shows an operator ("which move carried the repair"): a move is
`repair: true` iff holding its own disk back on its current storage —
against that same `executed_assignment()` result — would strictly raise
`Σ r_s`. This is deliberately a *different* question from the trigger:
the trigger asks whether the plan as a whole reduced `Σ r_s`; the marker
asks, move by move, which ones the plan's own repair actually depends on.
The two can disagree in either direction — a redundant-repair plan (two
moves off a violating storage, either alone sufficient) repairs with no
move individually marked, since holding *either one back alone* still
leaves the other to do the job — and the marker also catches an
*indirect* repair: a move whose own source never violated anything, but
which empties the destination another repair needs (section 14.8's
`free-space-repair.yaml`, `roomy`'s own move, is exactly this case). Both
`executed_assignment()` and `repair_markers()` take the same `Group` and
assignment shape `reserve.py`'s functions already use, so the revert test
is two extra `total_shortfall_bytes()` calls per move, not a second
implementation of (C5)'s arithmetic.

`test_plan_json_output` and
`test_plan_json_output_accepts_payback_when_saferemove_is_off` in
`tests/unit/test_cli.py` exercise both halves of this end to end: the
same reserve-driven, zero-benefit move is accepted when its duration is
within the limit and rejected (correctly, via the hard rule, not the
economic one) when a slow `saferemove` wipe pushes it over
`max_single_move_duration` — and, because that hard rule then excludes the
move from `executed_assignment()`, the plan is *not* `repair_exempt`
either in that second case, even though the plan's aspirational target
would have repaired the violation.

## The section 7.3 saturation guard: `compute_move_cost()`'s optional `target`

The guard defers a move (never rejects it outright) when the load it
would add to either endpoint, forecast over the mirror, would push that
storage past an operator-declared ceiling: a move is deferred whenever
`L_during(s) > saturation_ceiling * N_s` for either endpoint `s`. `N_s`
is that storage's own `storages[].saturation_load` — an operator-supplied
number, in the same average-in-flight-I/O-requests unit every other load
figure in this codebase uses, above which the operator judges the
storage should not run for a sustained period; it is optional, and a
storage that never sets it is never checked at all (below).
`saturation_ceiling` is `migration.saturation_ceiling` (default `0.85`),
the fraction of `N_s` a move's own forecast load is allowed to reach.
`L_during(s) = L_hat_s(duration_mirror) + omega_role(s)`: `L_hat_s
(duration_mirror)` is the forecast upper bound of `s`'s own load over the
move's mirror duration — `forecast.storage_upper_bound()`, section 10.1,
summed over the disks *currently* resident on that storage, not the
moving disk's own hypothetical arrival, since during mirroring it is
still served from `src` — and `omega_role(s)` is the same per-role load
charge the cost formula itself uses for a mirroring move,
`migration.source_load_weight` (`ω_src`) when `s` is the source or
`migration.target_load_weight` (`ω_dst`) when `s` is the target (never
both on the same endpoint).

`compute_move_cost()` stays pure (the module docstring's own promise:
"nothing fetches anything") by taking the guard's inputs already
computed, rather than fetching a forecast itself: `target`, and
`l_hat_src`/`l_hat_dst` — the caller's own already-computed
`L_hat_s(duration_mirror)` for each endpoint, per the formula above (its
`ω_dst` charge below already accounts for the moving disk's own
mirror-write traffic to `dst` separately, so `l_hat_dst` itself must
never double-count it). Left at their
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

`_saturation_deferred()` is where `L_during(s) > saturation_ceiling * N_s`
above is actually evaluated per endpoint — the same two `ω_src`/`ω_dst`
config values `compute_move_cost()`'s own cost formula already uses, not
a second pair invented for this check (AGENTS.md section 5).
`MoveCost.saturation_deferred`/`PaybackResult.deferred_moves`
mirror `exceeds_max_duration`/`rejected_moves`'s existing shape exactly,
but are kept as distinct fields — section 7.3 itself draws the same
distinction ("reject the move" vs. "defer the move to a later run"), and
a report should be able to say which of the two happened, one hard and
always active, the other best-effort and silently inactive wherever
`saturation_load` is unset. `PaybackResult.accepted` now requires
neither being non-empty.

## What this pass deliberately does not do

- **Any materiality floor on the benefit.** A plan of nothing but tiny
  disks has `total_cost_load_seconds == 0`, so `aggregate_ok` reduces to
  `benefit_load_seconds >= 0` and `PaybackResult.ratio` reports `+inf`:
  such a plan passes the aggregate test unconditionally (a repairing plan
  skips the test anyway, so this matters for the non-repairing case). That
  is intended: a disk below `tiny_disk_bytes` is exempt from the payback
  arithmetic precisely so that a 528 KiB `efidisk0` rejoining its VM does
  not have to out-earn a rule written for multi-terabyte migrations.

  What the code does not show, and what is worth knowing before touching
  either module, is the consequence: for such a plan **nothing downstream
  of the solver's objective asks whether the moves are worth making**,
  and no objective term has a materiality floor either, so any `+ε` is
  enough. The affinity term's correctness is load-bearing for tiny moves
  in a way it is not for any other kind of move. That is not theoretical:
  while `objective.affinity_counts_pinned_disks` still defaulted to
  `false` — so a disk that could not move was left out of the affinity
  count, and a VM's pinned disks exerted no pull on its movable ones — two
  528 KiB `efidisk0` moves on a real cluster were emitted on a `3.6e-7`
  capacity-spread difference — a relative improvement of `6e-8`, on which
  the then-two MILP backends (CP-SAT and CBC) did not even agree — with a `kappa` gain of exactly
  zero, each one a live migration holding a VM lock and burning
  `gates.cooldown_per_storage` on its target. Correcting that default
  turned the same two moves into genuine reunifications worth a discrete
  `1.0`, and the backends into agreement.

  No floor is added speculatively: the failure was a defect in the
  objective, not a missing gate, and any threshold here would be a magic
  number standing in for a decision the model does not otherwise need to
  make. If a future bundle shows tiny moves emitted with
  `affinity_debt_before == affinity_debt_after`, the narrowest fix is to
  require `affinity_debt_before > affinity_debt_after` for a zero-cost
  plan — no threshold needed, since the debt moves in discrete steps.
  `test_payback.py` pins the current behaviour so that change cannot be
  made silently.
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
  not a second, separate check for the *draining* phase (`ω_wipe` —
  `migration.wipe_load_weight`, the same weight the cost formula above
  charges for a running wipe — over `duration_wipe_seconds`), which the
  full generalized in-flight-set
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
