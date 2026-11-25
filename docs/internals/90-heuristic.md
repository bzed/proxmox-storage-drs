# The heuristic solver

**What does this page answer?** How does `heuristic.py` turn the loads of a group
into a target assignment? Why is the section 5.4 objective its own function
instead of part of the search? What does this module deliberately not do yet? This
page describes `proxmox_storage_drs/heuristic.py`.

## `evaluate_assignment()` is the objective, kept separate from the search

Section 5.5 requires this explicitly: "the heuristic must use the **same**
feasibility and objective functions as the MILP path so the two backends are
directly comparable." `evaluate_assignment()` takes a `Group` and any candidate
`Assignment` (`dict[Disk.key, storage id]`). The candidate need not be reachable
from the current state by any sequence of moves. The function returns an
`ObjectiveBreakdown`. This keeps the five terms of the section 5.4 objective
separate instead of one number. There are two reasons. `explain` (not yet written)
needs to show the arithmetic. The tests that check the function against the worked
example of section 14 need to assert each term individually, because a total alone
could be right for the wrong reasons.

`reserve.py` made the same design choice first: a pure function of *data*, with no
notion of "the current run" built in. `heuristic.py` reuses
`reserve.compute_reserve_status()` directly for (C4)/(C5). It passes a
`storage_of` callback that closes over the candidate assignment under evaluation.
The docstring of `reserve.py` anticipated this extension point before this module
existed to use it: "the solver will pass a candidate assignment through the
identical shape".

## Repair is unconditional, not weight-driven

Section 13 says: "the reserve is never traded against balance." The heuristic
makes this literal instead of merely well weighted. `_repair()` runs *before*
`_descend()`. It repairs any (C5) violation by moving disks off the storage with
the worst violation, one iteration at a time, whatever the objective weights say.
No value of `beta`/`gamma` is large enough to switch this off. `beta` and `gamma`
are the weights of the objective per move: `objective.beta_move_count` for the
number of disks moved, and `objective.gamma_move_bytes_per_tib` for the number of
bytes moved. They are the two terms that a migration itself costs. For `alpha`,
the imbalance weight, see `objective.spread_metric` below. For `kappa`, the
VM-affinity weight, see "`w_v`: `kappa` weighted..." further down.

`objective.reserve_violation_penalty` still appears in
`ObjectiveBreakdown.reserve_penalty_term`. It only *reports* a remainder that
repair could not remove. Such a remainder is physically impossible to remove, not
just unattractive. By the time `_descend()` runs, `_repair()` has already resolved
every reserve violation that it can. In the common case, the term is therefore
exactly zero and does not influence the choices of the descent at all.
`test_reserve_violation_is_repaired_even_with_beta_high_enough_to_forbid_balance_moves`
is the regression test. With `beta=100`, no purely cosmetic balance move could
ever be worth a migration. The repair move still happens.

**The tool judges a candidate by the total shortfall of the whole group, not by the
shortfall of the source storage.** That total already counts what a move does to
`f_s·Z_s`. When a disk leaves, it can lower the footprint of its VM on the source.
The move then frees the reserve that this footprint drove, as well as the bytes of
the disk. Under the per-VM footprint, the repair of a storage that holds two disks
of one VM therefore prefers the move that breaks the footprint down (`101:scsi1` in
the section 14 example), not the largest disk.

A move of a disk off a violating storage always reduces the shortfall of *that*
storage: the storage has fewer bytes, and its largest-footprint requirement is the
same or smaller. The test "does the shortfall of the source fall" is therefore
tempting but wrong. It says yes even when the disk only moves the problem to the
storage that receives it, or makes the total of the group worse. An earlier version
of `_repair` used exactly that test. It moved a disk back and forth between two
storages, neither of which could hold it fully. It "successfully" reduced the
shortfall of the current worst storage on every iteration and never made net
progress. The rule that the total of the *group* must strictly decrease repairs
this. It also makes the iteration bound of the loop (movable disks times storages,
sized generously) a correct termination argument instead of a lucky one.
`test_repair_does_not_oscillate_when_no_target_can_fully_absorb_the_violation` is
the regression test. It uses two storages of 8 TiB with `reserve_factor: 2.0`.
A 3 TiB disk cannot fit alone on either of them. The disk moves exactly once. The move repairs what it can,
from a group-wide shortfall of 3 TiB down to 1 TiB, and the disk does not move
back and forth forever.

## Descend explores swaps, not only single moves

Section 5.5 is explicit that swaps are not an optional refinement: "when both
storages are near their capacity limit, no single move is feasible, and only an
exchange of two disks can improve the balance." In each iteration, `_descend()`
evaluates every move of one disk *and* every swap of a pair of movable disks. It
applies whichever reduces the objective most. It stops when nothing does, or after
`heuristic_iterations`. Both are plain new evaluations of `evaluate_assignment()`
against a trial dictionary. No separate logic checks swap feasibility, because a
swapped assignment is just another candidate that the same objective function
scores. `test_descend_uses_a_swap_when_no_single_move_is_feasible` builds exactly
the capacity-locked scenario of the plan: two storages, each with headroom smaller
than any single disk. It checks that the descent finds the only reachable
improvement, a swap.

## Descend also tries relocating a whole VM at once — a real gap, found by dogfooding

Neither of the two candidate kinds above can reach a third kind of improving
move. That move relocates *all* movable disks of a VM with several disks to one
new storage, together. A move of one disk cannot get there when the `kappa` (VM affinity) term
of the objective is large enough to make a move of only one disk of the VM a net
loss. The move temporarily *fragments* the VM (and pays `kappa`) before a second
move could reunite it elsewhere, and `_descend()` only takes a step that improves
by itself. A swap cannot get there either. It exchanges the positions of two disks
with *each other*. It never moves a whole set of disks to a third storage together.

This was not a theoretical gap. A test against a real production cluster found it,
not a review. A VM with two disks sat entirely on one storage that also carried a
large amount of *pinned* (immovable) load, with `kappa_vm_affinity` at its default
`0.50`. Every move of a single disk that `_descend()` tried was a net loss once it
paid for fragmentation. The descent therefore found *zero* improving moves and left
the cluster at its starting point with 196% imbalance. The MILP solver, with the
exact same data, found the relocation of both disks at once. A dependency-free
heuristic that can get stuck this badly on a real, unremarkable cluster undermines
the one thing that section 5.5 asks it to be: "the path for very large groups",
reliable with no optional solver installed at all.

The repair adds a third candidate family. The descent tries it in the same step
"evaluate everything, apply whichever wins" as the other two.
`_vm_relocation_candidates()` groups the movable disks by `vmid`. It skips any VM
with only one movable disk, because the plain single-move candidate already covers
that case. For each remaining VM, `_descend()` tries a move of *all* its disks to
each other storage in one trial. The same `evaluate_assignment()` call scores the
trial, so the descent can never choose a worse assignment this way. The trial
respects `cooldown_storages` as a destination exclusion, like the other two
candidates.
`test_descend_relocates_a_whole_multi_disk_vm_neither_single_moves_nor_swaps_can_reach`
reproduces the numbers of the production scenario by hand. A single move raises
the objective by +0.43. The joint move lowers it by -0.14. The test confirms that
`_descend()` only finds the improvement once this candidate exists.
`_best_of()`/`_single_move_trials()`/`_swap_trials()`/`_vm_relocation_trials()` are
helpers that the flake8 complexity limit forced out. They let all three candidate
families share one loop "keep whichever trial scores lowest" instead of three
copies of it.

## The storage cooldown excludes a destination, never a source

Section 6 says: "a storage involved in a migration within `cooldown_per_storage`
accepts no new incoming moves." The caller of `run_heuristic()` (`cli.py`) computes
the `cooldown_storages` parameter with `state.active_storage_cooldowns()`. It is a
plain `frozenset[str]`, not a `state.State` that this module reads itself.
`run_heuristic()` passes it to `_descend()` only. Both neighbourhoods of
`_descend()` respect it:

- The single-move loop skips any `target.id in cooldown_storages`.
- The swap loop skips a pair when *either* storage that a disk would land on is in
  cooldown. A swap always sends one disk to each of the two storages that it
  touches, so a cooldown storage on either side blocks the whole swap.

A disk that already sits on a cooldown storage is always free to move *away* from
it. The rule is about new arrivals, not existing occupants. For this reason, the
filter only appears on the destination side of a candidate, never on the source
side.

`_repair()` never receives `cooldown_storages`. This is a deliberate exemption, not
an oversight. It matches the rule of this module that repair is unconditional
(above). A storage that is actively needed to resolve a live (C4)/(C5) violation is
not deferred because something wrote to it recently. `gates.py` and `payback.py`
already apply the same reserve-override principle, to the drift and imbalance gates
and to the payback test. `test_run_heuristic_repair_ignores_storage_cooldown` is
the regression test: the tool still repairs a violation whose only viable full
repair target is in `cooldown_storages`.
`test_descend_blocks_new_arrivals_onto_a_cooldown_storage` and
`test_descend_still_allows_a_disk_to_move_away_from_a_cooldown_storage` cover the
two sides of the rule in `_descend()`, both against the section 14 fixture.

## `objective.spread_metric`: two different quantities, not one rescaled

Section 5.4/(C6) offers two imbalance forms, and `evaluate_assignment()`
implements both:

- `"l1"` (default) is `alpha * sum(e_s)`: the sum of the absolute deviation of every
  storage from `u*`.
- `"minmax"` is `alpha * max(u_s)`, the `t >= u_s` of the plan for all `s`: the
  *raw* utilization of the hottest storage alone.

These are not the same quantity with a different aggregation. `max(u_s)` and
`max(e_s)` can disagree. A storage far *below* `u*` produces a large deviation
`e_s` that minmax was never meant to notice. The manual says "indifferent to a
second nearly-as-bad storage", nearly as bad on the *high* side; minmax is not
designed to react to a cold storage at all. `ObjectiveBreakdown` carries both
`spread_e` (deviations) and `utilization` (raw `u_s`), whichever metric is active.
The function computes them once, in the same loop. A switch of the metric thus
never means computing something that the other mode did not already have.

REVIEW.md Q-01 found that an earlier version of this module silently ignored this
config key: it always used L1 and never read `objective.spread_metric`. P-01/P-02
found the same class of gap in `pve.py`/`topology.py`.
`test_spread_metric_minmax_is_indifferent_to_a_second_nearly_as_bad_storage` is the
regression test. It comes directly from the claim of the manual: two scenarios with
an identical hottest storage but a clearly different second-worst storage score
identically under minmax and differently under l1.

## `d_s` is absolute TiB, and why

`evaluate_assignment()` computes the data-spread term as
`delta_capacity_spread * Σ_s |B_s − b̄·C_s| / 2⁴⁰`. `B_s` is the managed bytes of the
storage at this assignment (`ReserveStatus.managed_used_bytes`), with foreign
volumes included and the reserve excluded. `b̄` is the mean fill of the group and
`C_s` the capacity, so `b̄·C_s` is the capacity-proportional share.
`ObjectiveBreakdown.fill_deviation` holds each `d_s` in TiB.

The earlier form divided by `b̄`. The gain per TiB moved was then `2δ/B̄` for a group
that averages `B̄` TiB per storage. The fixed costs per move (`beta`, and `gamma` per
TiB) therefore outgrew the gain as the group grew. Above `B̄ = 2δ/γ` (20 TiB at the
defaults), no move could ever pay. In TiB, the gain is `2δ` per TiB moved at any
size, and the break-even disk is `X* = β/(2δ − γ)`.

The same expression appears in the CBC model (`_cbc_capacity_spread_term()` of
`optimize.py`, with sizes in MiB and `delta` as `delta/2²⁰` per MiB). It also appears
in the oracle `tests/fixtures/generate_expected.py` (`F_of()`). The payback rule and
the move ordering read `raw_capacity_spread()`, the same sum without the weight, so
they follow without any change. The tool still reports `fill_fraction`: `explain`
and the capacity gate speak in fill fractions.

## Proof this reproduces the plan, not just itself

`tests/unit/test_heuristic.py` does not stop at "the assignment matches the prose".
At `delta_capacity_spread: 0`, it asserts that `ObjectiveBreakdown.total` equals
`3.384685` (three-move plan) and, at `beta_move_count: 0.50`, `4.009685` (two-move
plan). These are the exact totals that the revised arithmetic of section 14.3 gives
once `w_v` weights `kappa` (below). They are not values that this module invented
and then asserted against itself. A match to six decimal places is strong evidence. It shows that these parts are
correct together, not just consistent with each other: the seven terms of the
objective, their units (TiB for size, average in-flight I/O for load) and the
search that chooses among them.

## `w_v`: `kappa` weighted by a VM's own I/O, and `D^big`

Section 5.4 strengthens the affinity term in two ways. Both came after a test on a live cluster
found that the aggregate test of `payback.py` rejected a plan whose
entire value was to reunite VMs. That value had no place to be counted (see
`96-payback.md`).

First, `compute_vm_weights()` computes `w_v = max(1, l_v / l_bar)` once per group.
`l_v` is the total load of a VM over *every* one of its disks, pinned disks
included. `l_bar = T_g / |V|`, where `T_g` is the total load of the group and `|V|`
is the number of **every** distinct vmid with a disk in the group. `|V|` is not the
(possibly smaller) set of vmids over which the `kappa` sum itself runs after
`objective.affinity_counts_pinned_disks: false` has excluded a VM with only pinned
disks. The worked number of section 14.7 (`l_bar = 6.0/3`, not `6.0/2`, with VM 309
pinned out of the sum but still counted here) caught the first implementation, which
got this wrong. `evaluate_assignment()` uses `w_v` in `fragmentation_term` instead
of the old flat count per VM. Both MILP backends (`optimize.py`) import the identical function. They thus add
the coefficient per vmid to their own `kappa` term in the same way. The
weighting is not implemented twice (AGENTS.md section 5).

**Section 5.3 (C8), small disks follow their VM,** is enforced by discarding
candidates, not by scoring them:

- `_best_of()` skips any trial assignment for which
  `topology.small_disks_follow_their_vm()` is false. This covers all three
  neighbourhoods that `_descend()` explores (single moves, swaps, relocations of a
  whole VM).
- `_best_repair_candidate()` does the same for the moves of `_repair()`, so a small
  disk is never a (C5) repair by itself.
- `best_single_disk_alternative()` (the "closest alternative" of `explain`) never
  offers a small disk alone.

The check covers the whole assignment, not only the moving disk, because a move of a
*larger* disk away can strand a small disk that followed it earlier. The seed
(current) assignment always satisfies the rule, so the search never starts outside
the feasible region.

Second, `D^big = {d : z_d >= migration.tiny_disk_bytes}` (default 64 MiB).
`move_count_term` and `bytes_moved_term` sum only over moved disks at or above that
threshold. The reunion of an `efidisk0`/`tpmstate0` thus costs nothing on the
`beta`/`gamma` side. `moved_disk_keys` itself is unchanged, so a tiny disk still
appears as a real move everywhere else (reporting, the ordering in `schedule.py`,
the move list in `payback.py`). `ObjectiveBreakdown.affinity_debt` is the raw `A`, weighted by `w_v` but not
scaled by `kappa`. This field and `raw_affinity_debt()` exist for one purpose. The
benefit in `payback.py` uses the identical quantity that `kappa` charges here. It never derives a second quantity independently (the rule of REVIEW.md R-01,
extended to the third term).

## What this pass deliberately does not do

- **"Polish" (heuristic step 4)**: reuniting a fragmented VM when this does not
  make the imbalance worse than `gates.imbalance_threshold`. It is not implemented.
  Repair and descent alone reach the exact three-move and two-move solutions of the
  section 14 fixture (the tests above prove it). The reason is that the `kappa` term
  of the objective already makes the descent prefer co-location when it is not too
  costly. Since the repair above, the relocation of a whole VM in the descent also
  reaches the case with two or fewer disks directly. What remains for polish is strictly narrower than before. It is an *N-way
  rotation* across three or more storages (disk A needs S1→S2, disk B needs
  S2→S3, disk C needs S3→S1 in a cycle). In it, the move of no disk improves alone,
  and no two disks belong to the same VM. This is
  outside every candidate that `_descend()` tries today. The one fixture that exists
  to validate this module does not exercise it. This is a real gap, recorded here
  instead of being silently absent.
- **Format-compatibility eligibility of (C2)**: `topology.Storage` does not yet
  carry the information on storage type and format that this rule needs.
  `_default_format` in `topology.py` resolves it internally but never exposes it on
  `Storage`. For this reason, every storage of the group is currently an eligible
  target for every movable disk. The section 14 fixture is homogeneous (three
  storages of identical type) and does not exercise this gap either.

The `plan` command of `cli.py` uses `heuristic.py`, together with `schedule.py` (the
move ordering of section 8; see `95-schedule.md` and `docs/manual/27-plan.md`).
`apply` is fully implemented (see `92-execute.md`). `explain` (section 12) reuses
the identical `plan` pipeline (`cli._plan_group()`). It narrates the seven terms of
`ObjectiveBreakdown` individually, which is why this dataclass keeps them apart
instead of only a `.total` (its own docstring). It also shows which disks are pinned
and which VMs that leaves fragmented across more than one storage. See
`40-cli-and-logging.md` and `docs/manual/30-safety-and-status.md`.

## `best_single_disk_alternative()`: why `explain` says nothing moved

A test against a real cluster led to this function. The gate decided `ACT`
(every disk eligible, nothing pinned), and the optimum of the solver was still to
move nothing. This is the exact shape "kappa outweighs the repair", the opposite
direction of the case that the whole-VM relocation above handles. Here, only a split
of a VM with two disks could help significantly, and the penalty of
`objective.kappa_vm_affinity` for that split legitimately cost more than the
imbalance was worth. From the outside, the one-line verdict of `plan` cannot tell
this case apart from "the solver never tried".

`best_single_disk_alternative()` closes that gap for `explain` only. `plan` never
calls it: it only explains a decision that is already made, and does not make one.
It evaluates every pair `(movable disk, other group storage)` with the same
`evaluate_assignment()` that the solver itself uses. This is the one-move
neighbourhood of section 5.3, searched exhaustively instead of sampled. The number
of disks times the number of storages of a group is always small enough for
`explain` to afford this. `plan` must stay fast enough to run in every cycle. The
function returns the move with the lowest resulting objective total, that is, the
move closest to being worth it. `cli._render_no_moves_lines()` prints its
`ObjectiveBreakdown` beside the baseline, term by term. An operator can thus see
exactly which terms rejected the move and, if they disagree with that trade-off,
which weight to change. See the "`no moves made: ...`" section of
`docs/manual/29-explain.md` for the rendered example, and the note "As built, added
later" in `IMPLEMENTATION_PLAN.md` section 9.5.
