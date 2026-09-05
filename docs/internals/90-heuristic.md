# The heuristic solver

**What does this page answer?** How does `heuristic.py` turn a group's
loads into a target assignment, why is the section 5.4 objective its own
function rather than baked into the search, and what does this module
deliberately not do yet? Describes `proxmox_storage_drs/heuristic.py`.

## `evaluate_assignment()` is the objective, kept separate from the search

Section 5.5 requires it explicitly: "the heuristic must use the **same**
feasibility and objective functions as the MILP path so the two backends
are directly comparable." `evaluate_assignment()` takes a `Group` and an
arbitrary candidate `Assignment` (`dict[Disk.key, storage id]`, not
necessarily reachable from the current state by any sequence of moves)
and returns an `ObjectiveBreakdown` — the section 5.4 objective's five
terms kept separate, not collapsed into a single number, because `explain`
(not yet written) needs the arithmetic shown, and because the tests
cross-checking this against section 14's worked example need to assert
each term individually, not just a total that could be right for the
wrong reasons.

This is the same design choice `reserve.py` made first: a pure function of
*data*, with no notion of "the current run" baked in. `heuristic.py`
reuses `reserve.compute_reserve_status()` directly for (C4)/(C5), passing
it a `storage_of` callback closed over the candidate assignment being
evaluated — the extension point `reserve.py`'s own docstring already
anticipated ("the solver will pass a candidate assignment through the
identical shape") before this module existed to use it.

## Repair is unconditional, not weight-driven

Section 13: "the reserve is never traded against balance." The heuristic
makes this literal rather than merely well-weighted: `_repair()` runs
*before* `_descend()` and fixes any (C5) violation by moving disks off the
worst-violating storage, one iteration at a time, regardless of what the
objective weights say — there is no `beta`/`gamma` value large enough to
switch this off. `objective.reserve_violation_penalty` still appears in
`ObjectiveBreakdown.reserve_penalty_term`, but only for *reporting* a
residual that repair could not fix (physically impossible, not merely
unattractive) — by the time `_descend()` runs, every reserve violation
`_repair()` could resolve already has been, so in the common case this
term is exactly zero and does not influence descend's choices at all.
`test_reserve_violation_is_repaired_even_with_beta_high_enough_to_forbid_balance_moves`
is the regression test for this: `beta=100` (so no purely-cosmetic balance
move could ever be worth a migration) still sees the repair move happen.

**A candidate is judged by the group-wide total shortfall, not the source
storage's own.** Moving a disk off a violating storage always reduces
*that* storage's own shortfall — it has fewer bytes, and if anything a
smaller largest-disk requirement — which makes "does the source's
shortfall fall" a tempting but wrong test: it says yes even when the disk
only relocates the problem to whichever storage receives it, or makes the
group's total worse. An earlier version of `_repair` used exactly that
test and would oscillate a disk back and forth between two storages
neither of which can fully hold it, "successfully" reducing the current
worst offender's shortfall on every iteration while never making net
progress. Requiring the *group* total to strictly decrease fixes this and
is also what makes the loop's iteration bound (movable disks times
storages, generously sized rather than tightly) actually a correct
termination argument rather than a lucky one.
`test_repair_does_not_oscillate_when_no_target_can_fully_absorb_the_violation`
is the regression test: a 3 TiB disk that cannot fit, alone, on either of
two 8 TiB/`reserve_factor: 2.0` storages is moved exactly once (repairing
what can be repaired, from a 3 TiB group-wide shortfall down to 1 TiB), not
shuffled back and forth forever.

## Descend explores swaps, not only single moves

Section 5.5 is explicit that swaps are not an optional refinement: "when
both storages are near their capacity limit, no single move is feasible,
and only an exchange of two disks can improve the balance." `_descend()`
evaluates every single-disk move *and* every pairwise swap of two movable
disks each iteration, applying whichever most reduces the objective, and
stopping when nothing does or after `heuristic_iterations`. Both are
plain re-evaluations of `evaluate_assignment()` against a trial
dictionary — no separate swap-feasibility logic exists, because a swapped
assignment is just another candidate the same objective function scores.
`test_descend_uses_a_swap_when_no_single_move_is_feasible` constructs
exactly the capacity-locked scenario the plan describes (two storages each
with headroom smaller than any single disk) and checks the only reachable
improvement — a swap — is the one found.

## `objective.spread_metric`: two different quantities, not one rescaled

Section 5.4/(C6) offers two imbalance forms, and `evaluate_assignment()`
implements both: `"l1"` (default) is `alpha * sum(e_s)`, every storage's
absolute deviation from `u*` summed; `"minmax"` is `alpha * max(u_s)` --
the plan's own `t >= u_s` for all `s`, the *raw* utilization of the single
hottest storage. These are not the same quantity with a different
aggregation: `max(u_s)` and `max(e_s)` can disagree, because a storage
sitting far *below* `u*` produces a large deviation `e_s` that minmax was
never meant to notice (the manual's own words: "indifferent to a second
nearly-as-bad storage" — nearly-as-bad on the *high* side; a cold storage
is not what minmax was designed to react to at all). `ObjectiveBreakdown`
carries both `spread_e` (deviations) and `utilization` (raw `u_s`)
regardless of which metric is active, computed once in the same loop, so
switching metrics never means computing something the other mode didn't
already have on hand.

REVIEW.md's Q-01 found this config knob silently ignored by an earlier
version of this module (always L1, `objective.spread_metric` never read)
— the same class of gap P-01/P-02 found in `pve.py`/`topology.py`.
`test_spread_metric_minmax_is_indifferent_to_a_second_nearly_as_bad_storage`
is the regression test, built directly from the manual's own claim: two
scenarios with an identical hottest storage but a materially different
second-worst one score identically under minmax and differently under l1.

## Proof this reproduces the plan, not just itself

`tests/unit/test_heuristic.py` doesn't stop at "the assignment matches the
prose." At the default weights it asserts `ObjectiveBreakdown.total`
equals `2.533333` (three-move plan) and, at `beta_move_count: 0.50`,
`3.158333` (two-move plan) — the exact totals `REVIEW.md` Appendix A
independently re-derived by hand from the plan's own numbers, not values
this module invented and then asserted against itself. Getting both to
five decimal places is strong evidence the objective's five terms, their
units (TiB for size, average in-flight I/O for load), and the search that
picks among them are all correct together, not merely internally
consistent.

## What this pass deliberately does not do

- **"Polish" (heuristic step 4)** — reuniting a fragmented VM when doing so
  does not worsen imbalance beyond `gates.imbalance_threshold`. Not
  implemented: the section 14 fixture's exact three-move and two-move
  solutions are both reachable by repair+descend alone (proven by the
  tests above), because the objective's own `kappa` term already makes
  descend prefer co-location whenever it is not too costly. Polish would
  matter for an affinity fix that needs three or more disks to rotate
  simultaneously — outside single-move/pairwise-swap reach — which the one
  fixture that exists to validate this module does not exercise. A real
  gap, tracked here rather than silently absent.
- **(C2) format-compatibility eligibility** — `topology.Storage` does not
  yet carry the storage type/format information that rule needs (it is
  resolved internally in `topology.py`'s `_default_format` but never
  exposed on `Storage`), so every group storage is currently an eligible
  target for every movable disk. The section 14 fixture is homogeneous
  (three identically-typed storages) and does not exercise this gap either.
- **CP-SAT/CBC coefficient scaling (section 5.5)** — belongs to
  `optimize.py`, not yet written. `evaluate_assignment()`'s plain
  floating-point objective is what the MILP path will need to agree with,
  not a stand-in for its own separately-scaled integer objective.
`heuristic.py` is wired into `cli.py`'s `plan` command, together with
`schedule.py` (section 8's move ordering) — see `95-schedule.md` and
`docs/manual/27-plan.md`. `explain`/`apply` remain stubs
(`docs/manual/30-safety-and-status.md`).
