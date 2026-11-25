# Migration cost and the payback test

**What does this page answer?** How does `payback.py` turn a scheduled move
into a cost? How does the module turn a plan into a benefit? How does the tool
turn the two into an accept/reject verdict? Why does a reserve-fixing plan
always pass?

This page describes `proxmox_storage_drs/payback.py`.

## Cost and benefit are computed from data other modules already have

`compute_move_cost()` needs only a `schedule.ScheduledMove` and its source
`topology.Storage`. It makes no new fetch and uses no new state.

`duration_mirror` is `z_d / migration.bwlimit_bytes_per_sec`. `duration_wipe`
is `z_d / |saferemove_throughput|` when `migration.account_saferemove_wipe` is
on and the source has `saferemove` on. Otherwise `duration_wipe` is zero.

`cost_load_seconds` is
`duration_mirror * (migration.source_load_weight + migration.target_load_weight) + duration_wipe * migration.wipe_load_weight`.

The term uses the same **load-seconds** unit (average in-flight I/O requests
multiplied by seconds) that `compute_benefit_load_seconds()` produces below.
That is what makes the two comparable at all.

The cost is the extra in-flight I/O the migration itself imposes on the
source and the target while the mirror runs. It also adds the extra load a
running `saferemove` wipe imposes on the source alone, for as long as the old
volume takes to be zeroed.

`cost_load_seconds` is zero below `migration.tiny_disk_bytes` (section
5.4/7.1). `duration_mirror` and `duration_wipe` are still the real numbers.
`exceeds_max_duration` still fires normally for a tiny disk that happens to
be throttled hard enough. Only the economic charge is waived.

`compute_benefit_load_seconds()` implements section 7.2's formula:

`benefit = (alpha_spread*(E_before-E_after) + delta_capacity_spread*(F_before-F_after) + kappa_vm_affinity*(A_before-A_after) + mu_vm_split_per_tib*(O_before-O_after)) * H`

See also sections 12 and, for the third term, the 5.4/7.2 affinity-payback
fix. `O` is the summed split excess of the large VMs in TiB, from
`heuristic.raw_split_excess_tib()`. The excess persists for as long as the
placement does. A move that piles a large VM back onto one storage pays for it
out of its other gains. A split is *not* a repair. A split gets no exemption
of its own.

`H` is `migration.payback_horizon_seconds` (default `365d`, converted to
seconds). `H` is the length of time the plan's improvement is assumed to keep
paying off.

Both sides of the payback ratio end up in the same **load-seconds** unit.
Benefit is a load-shaped quantity held for `H` seconds. Cost (below) is a
duration in seconds multiplied by a load-shaped weight.

`compute_benefit_load_seconds()` takes the pre-plan/post-plan pair of
`heuristic.raw_spread()` values (E, the *raw*, unweighted imbalance quantity).
It takes `heuristic.raw_capacity_spread()` values (F, the raw data-spread
quantity, section 5.3 (C7)). It takes `heuristic.raw_affinity_debt()` values
(A, the raw, `w_v`-weighted but not `kappa`-scaled affinity debt, section
5.4). It also takes `objective.alpha_spread`/`delta_capacity_spread`/
`kappa_vm_affinity` as explicit weight parameters. The function multiplies the
weighted sum by `migration.payback_horizon_seconds`.

**Never** pass `ObjectiveBreakdown.imbalance_term`/`.capacity_spread_term`/
`.fragmentation_term`. Those are the same quantities already scaled by
`alpha_spread`/`delta_capacity_spread`/`kappa_vm_affinity` for the section
5.4 *solver* objective. Passing them here would double-apply the weight
(REVIEW.md R-01). Earlier code passed `imbalance_term` directly. The bug
stayed invisible only while `alpha_spread`'s default of `1.0` made the two
numerically identical.

`compute_benefit_load_seconds()` applies the weights *inside* itself, as
explicit parameters rather than built into an already-scaled input. That
keeps R-01's principle intact. The principle now covers all three terms, not
just the first two. `_plan_group()` in `cli.py` computes all six raw values for the pre-plan and
post-plan assignments, for `plan` and `apply` alike. It passes the values, and all three
weights, through.

The `kappa` term's own inclusion here is the fix for a real live failure. A
plan whose entire value was reuniting VMs scored `benefit 9 load·s vs cost 232
load·s → ratio 0.0388` and was refused. The plan had two 528 KiB `efidisk0`s
among its four moves. The pre-fix formula had no way to value affinity at all.

See `IMPLEMENTATION_PLAN.md` section 7.2's own account. See
`tests/fixtures/affinity-repair.yaml` (section 14.7) for the fixture built to
reproduce the failure.

`A_before - A_after` can be negative. A balance move that *splits* a VM must
pay for the fragmentation out of its `alpha` gain.
`compute_benefit_load_seconds()` returns that negative contribution as
computed, never clamped. `evaluate_plan_payback()`'s own acceptance test
already rejects a genuinely negative benefit correctly.

## Why `compute_wipe_duration_seconds()` takes the magnitude

`saferemove_throughput` is signed. The sign is not part of the rate.

PVE hands the configured value straight to `cstream -t`. A **positive** number
is a session average. cstream accumulates its own error. It may exceed the
rate for a while to balance out earlier underutilization. A **negative**
number is an upper limit on each individual read/write syscall pair. That
limit is never exceeded.

Both values name the same `|num|` bytes/second. So `-1073741824` means
1 GiB/s.

Negative values are ordinary in PVE configurations. An operator writes a
negative value when the operator wants a rate the wipe can never burst above.

`compute_wipe_duration_seconds()` is the one implementation of the formula
(AGENTS.md section 5). `compute_move_cost()`, `cli.py`'s `verify-storages` and
`execute.py`'s `min_wipe_seconds` all go through it. `abs()` belongs there and
nowhere else.

`topology.py` deliberately keeps PVE's signed value on `Storage`.
`verify-storages --json` echoes the value back verbatim. An operator can match
it against their own `storage.cfg`. Normalizing it at parse time would change,
without notice, what the operator is shown.

Dividing by the signed value was a real bug, not a cosmetic one. The shape of
the bug is worth remembering.

`duration_wipe` came out negative. `duration_d = duration_mirror +
duration_wipe` therefore collapsed towards zero. It collapsed to **exactly**
zero on the common configuration where `|saferemove_throughput|` equals
`migration.bwlimit_bytes_per_sec`.

On such a cluster the `max_single_move_duration` rejection could not fire for
a disk of any size. The rule refuses outright a move whose mirror plus wipe
would run longer than the limit. A hypothetical 100 TiB move reported a total
duration of 0 s. The move passed the 6 h limit with no rejection.

`verify-storages`' two warnings were both permanently false. The warnings are
`cooldown_per_storage_too_short` and `max_single_move_duration_too_short`. A
negative number never exceeds a positive threshold.

The tool printed `implied wipe time for the largest disk (1.00 TiB): -17.1m`.
Nobody downstream noticed.

The project found the bug by replaying a corpus bundle from a cluster. The
cluster's three LVM storages all carry `saferemove_throughput -1073741824`.

## The mirror duration is `z_d / bwlimit`, and nothing else

Section 7.1 states `duration_mirror_d = z_d / bwlimit`.

An earlier draft of the plan wrote `min(bwlimit, headroom_src, headroom_dst)`.
The two headroom terms were never defined. They are gone.

`migration.bwlimit_bytes_per_sec` is the only throttle a migration needs. This
tool does not model how busy a storage is while a mirror runs. `execute.py`
passes the limit to every `move_disk` call.

## The reserve-override exemption

`evaluate_plan_payback()`'s aggregate ratio test is
`benefit_load_seconds >= migration.payback_ratio * total_cost_load_seconds`.
The default is `payback_ratio: 10.0`. A plan's benefit must be worth at least
ten times what executing it costs. Both sides use the same load-seconds unit
that `compute_benefit_load_seconds()` produces above.

`PaybackResult.ratio` is that same `benefit / cost` division, exposed for
reporting. The test itself never divides. That keeps the test well-defined
when `total_cost_load_seconds` is `0`.

Section 7's payback test weighs a move's cost against the *balance* benefit it
buys. That framing has an edge it does not name. A plan resolving an active
(C4)/(C5) violation is not optional the way a balance-driven move is. A plan
resolving section 5.3.1's configured free-space requirement is not optional
either. Its "benefit" under the section 7.2 formula can easily be zero or even
structurally zero. Moving the only loaded disk in a two-storage group between
the two storages changes which one carries it. It changes `E` not at all, no
matter how urgently the move is needed for capacity reasons.

Rejecting that move on economic grounds would contradict section 13's own
"the reserve is never traded against balance". `gates.py` already treats that
rule as absolute for the drift/imbalance gates.

`evaluate_plan_payback()` applies the identical rule. The function applies it
as an **outcome** trigger, not a per-move flag.

The function takes two extra parameters: `current_shortfall_bytes` and
`final_shortfall_bytes`. Both are `Σ r_s` (`reserve.total_shortfall_bytes()`).
The first measures the group's current assignment. The second measures the
plan's *executed* endpoint.

When `repair_exempt = final_shortfall_bytes < current_shortfall_bytes` is true,
the plan always passes the aggregate ratio test. The computed `ratio` does not
matter.

The hard per-move `max_single_move_duration` rule is not exempted this way.
Section 7.3 lists it as applying "regardless of the aggregate test". The rule
is an operational limit, not an economic one. A mirror that takes that long
has other costs an economic ratio does not capture.

**This replaced a per-move flag** (`ScheduledMove.resolves_reserve_violation`).
The flag is still there, but narrowed to section 8.2's own priority-1
scheduling signal, "this move's source was violating when scheduled first".
Payback never reads it anymore.

The old flag fired whenever *any* move's source was violating at scheduling
time. That condition is provably a superset of the outcome trigger. `Σ r_s`
can only fall if some storage's `used`/`Z_s` falls. That needs a disk to leave
a storage that was therefore violating when the disk left. Every
outcome-exempt plan was already flag-exempt, never the reverse. A plan that
moves a disk off a violating storage but leaves the group no less short is
flag-exempt but not outcome-exempt.

The two extra parameters are computed once, in `cli.py`'s `_plan_group()`.
That is the function's sole production caller. The function computes them from
objects it already has in hand. `current_shortfall_bytes` is
`reserve.total_shortfall_bytes()` over the current assignment (`group.disks`'
own `current_storage`). `final_shortfall_bytes` is the same sum over
`payback.executed_assignment()`'s result. That result is
`schedule_result.final_assignment` with every disk the hard per-move duration
rule excluded held back at its current storage. The exclusion set is
`exceeds_max_duration`, already known from `move_costs` by then.

That is "what the plan will really run", not merely what got scheduled. A
repair that a hard rule then blocks is correctly *not* exempt.

**The revert test, `payback.repair_markers()`**, is the per-move report a
caller shows an operator. The report answers "which move carried the repair".

A move is `repair: true` iff holding its own disk back on its current storage
would strictly raise `Σ r_s`. The test runs against that same
`executed_assignment()` result.

The marker asks a *different* question from the trigger, deliberately. The
trigger asks whether the plan as a whole reduced `Σ r_s`. The marker asks,
move by move, which moves the plan's own repair actually depends on.

The two can disagree in either direction. A redundant-repair plan has two
moves off a violating storage. Either move alone is sufficient. The plan
repairs with no move individually marked. Holding *either one back alone*
still leaves the other to do the job.

The marker also catches an *indirect* repair. That is a move whose own source
never violated anything. The move empties the destination another repair
needs. Section 14.8's `free-space-repair.yaml` is exactly this case:
`roomy`'s own move.

Both `executed_assignment()` and `repair_markers()` take the same `Group` and
assignment shape that `reserve.py`'s functions already use. The revert test is
two extra `total_shortfall_bytes()` calls per move. It is not a second
implementation of (C5)'s arithmetic.

`test_plan_json_output` and
`test_plan_json_output_accepts_payback_when_saferemove_is_off` in
`tests/unit/test_cli.py` exercise both halves of this, end to end.

The same reserve-driven, zero-benefit move is accepted when its duration is
within the limit. The move is rejected when a slow `saferemove` wipe pushes it
over `max_single_move_duration`. The rejection comes from the hard rule,
correctly, not the economic one.

In that second case the hard rule excludes the move from
`executed_assignment()`. The plan is *not* `repair_exempt` either, even
though the plan's aspirational target would have repaired the violation.

## What this pass deliberately does not do

- **Any materiality floor on the benefit.** A plan of nothing but tiny disks
  has `total_cost_load_seconds == 0`. `aggregate_ok` then reduces to
  `benefit_load_seconds >= 0`. `PaybackResult.ratio` reports `+inf`. Such a
  plan passes the aggregate test unconditionally. A repairing plan skips the
  test anyway, so the pass matters for the non-repairing case. That is
  intended. A disk below `tiny_disk_bytes` is exempt from the payback
  arithmetic. A 528 KiB `efidisk0` rejoining its VM does not have to out-earn
  a rule written for multi-terabyte migrations.

  What the code does not show is a consequence worth knowing before touching
  either module. For such a plan, **nothing downstream of the solver's
  objective asks whether the moves are worth making**. No objective term has a
  materiality floor either. Any `+ε` is enough.

  The affinity term's correctness matters for tiny moves in a way it does not
  for any other kind of move.

  That is not theoretical. While `objective.affinity_counts_pinned_disks`
  still defaulted to `false`, a disk that could not move was left out of the
  affinity count. A VM's pinned disks exerted no pull on its movable ones. Two
  528 KiB `efidisk0` moves on a real cluster were emitted on a `3.6e-7`
  capacity-spread difference. The relative improvement was `6e-8`. The
  then-two MILP backends (CP-SAT and CBC) did not even agree on it. The
  `kappa` gain was exactly zero. Each move was a live migration holding a VM
  lock and consuming `gates.cooldown_per_storage` on its target.

  Correcting that default turned the same two moves into genuine
  reunifications worth a discrete `1.0`. It also turned the backends into
  agreement.

  The tool adds no floor speculatively. The failure was a defect in the
  objective, not a missing gate. Any threshold here would be a magic number
  standing in for a decision the model does not otherwise need to make.

  If a future bundle shows tiny moves emitted with
  `affinity_debt_before == affinity_debt_after`, the narrowest fix is to
  require `affinity_debt_before > affinity_debt_after` for a zero-cost plan.
  No threshold is needed. The debt moves in discrete steps.

  `test_payback.py` pins the current behaviour, so no change of this kind can
  pass the test suite unnoticed.
- **The 3-retry re-solve-with-doubled-`beta`/`gamma` loop** (section 7.3) on
  aggregate payback failure. The loop is a real UX refinement. It converges
  on the smaller subset of high-value moves rather than abandoning the run. It
  is not a correctness requirement. Reporting accept/reject plainly already
  satisfies "reject a plan whose cost outweighs its benefit." Implementing the
  loop means re-invoking `heuristic.py`/`schedule.py` with adjusted weights
  from inside `cli.py`'s own orchestration. That is where the loop belongs
  when it is built, not half-done inside this module now.
- **Automatically dropping an individually-rejected move** and re-solving
  without it. The tool reports the move instead
  (`MoveCost.exceeds_max_duration`, `PaybackResult.rejected_moves`). That is
  the same "report, never force" choice that `schedule.py`'s deadlock
  reporting already makes for an unschedulable move.

## Wired into `plan` and `apply` alike, via `_plan_group()`

`cli.py`'s `_plan_group()` computes a `PaybackResult` for every group the gate
acts on. The function does so right after scheduling the group's moves.
`docs/internals/92-execute.md` describes this as the "one planning pipeline,
shared by `plan` and `apply`".

Both `plan`'s render functions and `apply`'s payback gate
(`_apply_payback_gate()`) consume the result. A rejected move never reaches
`execute.py`, regardless of mode.

`compute_wipe_duration_seconds()` is also used by `verify-storages`'s
existing wipe-time warning. That is one implementation of the formula, not two
(AGENTS.md section 5).
