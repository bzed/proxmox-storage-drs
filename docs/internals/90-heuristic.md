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

## Descend also tries relocating a whole VM at once — a real gap, found by dogfooding

Neither of the two candidates above can reach a third kind of improving
move: relocating *every* one of a multi-disk VM's movable disks to one
new storage, together. A single-disk move can't get there when the
objective's `kappa` (VM affinity) term is large enough to make moving
just one of the VM's disks a net loss on its own — it temporarily
*fragments* the VM (paying `kappa`) before a second move could reunite it
elsewhere, and `_descend()` only ever takes a step that is itself
improving. A swap can't either: it exchanges two disks' positions with
*each other*, never relocates a whole disk set to a third storage
together.

This was not a theoretical gap — it was found by testing against a real
production cluster (not by review): a two-disk VM sat entirely on one
storage that also carried a large amount of *pinned* (immovable) load,
with `kappa_vm_affinity` at its default `0.50`. Every individual disk
move `_descend()` tried was a net loss once fragmentation was paid for,
so it found *zero* improving moves at all and left the cluster at its
full, 196%-imbalance starting point — even though CP-SAT, given the exact
same data, found the two-disk relocation immediately. A dependency-free
heuristic that can get stuck this badly on a real, unremarkable cluster
undermines the one thing section 5.5 asks it to be: "the path for very
large groups," reliable with no optional solver installed at all.

The fix adds a third candidate family, tried in the same
"evaluate everything, apply whichever wins" step as the other two:
`_vm_relocation_candidates()` groups movable disks by `vmid` (skipping
any VM with only one movable disk — that case is already the plain
single-move candidate), and for each such VM, `_descend()` tries moving
*all* of its disks to each other storage in one trial. Scored by the
exact same `evaluate_assignment()` call as everything else, so it can
never itself choose a worse assignment, and it respects
`cooldown_storages` as a destination exclusion the same way the other two
candidates do. `test_descend_relocates_a_whole_multi_disk_vm_neither_single_moves_nor_swaps_can_reach`
reproduces the production scenario's numbers by hand (a single move
raises the objective by +0.43; the joint move lowers it by -0.14) and
confirms `_descend()` only finds the improvement once this candidate
exists. `_best_of()`/`_single_move_trials()`/`_swap_trials()`/
`_vm_relocation_trials()` are the flake8-complexity-driven extraction
that let all three candidate families share one "keep whichever trial
scores lowest" loop rather than three copies of it.

## The storage cooldown excludes a destination, never a source

Section 6: "a storage involved in a migration within
`cooldown_per_storage` accepts no new incoming moves." `run_heuristic()`'s
`cooldown_storages` parameter — a plain `frozenset[str]` its caller
(`cli.py`, via `state.active_storage_cooldowns()`) computes, not a
`state.State` this module reads itself — is threaded through to
`_descend()` only. Both of `_descend()`'s neighbourhoods respect it: the
single-move loop skips any `target.id in cooldown_storages`, and the swap
loop skips a pair whenever *either* storage a disk would land on is in
cooldown (a swap always sends one disk to each of the two storages it
touches, so either side landing on a cooldown storage blocks the whole
swap). A disk already resident on a cooldown storage is always free to
move *away* from it — the rule is about new arrivals, not existing
occupants — which is why the filter only ever appears on the destination
side of a candidate, never the source.

`_repair()` never receives `cooldown_storages` at all — a deliberate
exemption, not an oversight, matching this module's own repair-is
-unconditional stance above: a storage actively needed to resolve a live
(C4)/(C5) violation is not deferred for having been written to recently,
the same reserve-override principle `gates.py` and `payback.py` already
apply to the drift/imbalance gates and the payback test respectively.
`test_run_heuristic_repair_ignores_storage_cooldown` is the regression
test: a violation whose only viable full repair target is in
`cooldown_storages` is still repaired.
`test_descend_blocks_new_arrivals_onto_a_cooldown_storage` and
`test_descend_still_allows_a_disk_to_move_away_from_a_cooldown_storage`
cover `_descend()`'s own two sides of the rule, both against the section
14 fixture.

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
  descend prefer co-location whenever it is not too costly, and (since the
  fix above) descend's own whole-VM co-relocation candidate now reaches
  the two-or-fewer-disk case directly. What's left for polish is strictly
  narrower than it once was: an *N-way rotation* across three or more
  storages (disk A needs S1→S2, disk B needs S2→S3, disk C needs S3→S1 in
  a cycle) where no disk's own move improves alone and no two disks share
  a VM — outside every candidate `_descend()` tries today. The one fixture
  that exists to validate this module does not exercise it. A real gap,
  tracked here rather than silently absent.
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
