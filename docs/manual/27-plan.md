# Reading `plan`

`plan` computes what `pve-storage-drs` would do. It prints the result.
It never changes anything, in any `execution.mode`. Making changes is
`apply`'s job (see `docs/manual/28-apply.md`). `apply` needs a separate,
explicit invocation to run at all.

For each group, `plan`:

1. Fetches the same load (`ℓ_d`/`L_s`/`u_s`) that `show-load` fetches.
   It also evaluates the same section 6 gate.
2. If the gate says `NO ACTION`, it stops there for that group. No
   solver runs. Nothing more to show.
3. If it says `ACT`, it solves the group with the backend that
   `solver.backend` selects. `docs/internals/91-optimize.md` covers the
   CBC backend. `docs/internals/90-heuristic.md` covers the
   dependency-free one. The solver computes a target assignment. `plan`
   then orders its moves under the **transient reserve invariant**. While
   a move is in flight, the disk being migrated exists on *both* its
   source and target storage at once. The mirror is fully allocated on
   the target before the old copy leaves the source. So the target's own
   snapshot reserve must already hold with that disk's bytes counted in,
   not only once the source frees them afterwards. `IMPLEMENTATION_PLAN.md`
   section 8.1 has the full formula, including the generalization to
   several moves landing on the same storage at once under concurrent
   execution (see `docs/manual/28-apply.md`). `plan` then checks the
   whole plan against the payback rule below.

This example uses the same section 14 worked example that the `show-load`
manual page uses, at the default weights (the two-move plan). It also
uses `solver.backend: auto` with neither MILP library installed, so the
run falls back to the heuristic. The numbers stay traceable to that
section either way. Every backend reports through the same objective
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

The `solver:` line names the backend that actually produced this plan --
`heuristic` or `cbc`. For the MILP backend it also shows `(optimal)` or
`(feasible)`. `(feasible)` means CBC did not prove the gap closed within
`solver.time_limit_seconds`, but a solution was still found. The line is
not always what `solver.backend` says. `auto` tries CBC before the
heuristic. If that library is not installed or cannot produce a
solution, even an explicitly forced `cbc` falls back to the heuristic
instead of failing the whole run. The fallback is logged as a warning in
that case (see `docs/internals/91-optimize.md`). When CBC is what
failed, the warning says why in CBC's own terms:
`hit solver.time_limit_seconds before finding a feasible solution` means
raising that limit may help. Anything else (for instance
`returned no usable solution (CBC status: Infeasible)`) is not a matter
of time. It is worth a bug report with a `collect-testdata` bundle
attached.

The `after:`/`spread:` lines (and the payback numbers) reflect what the
scheduler actually ordered, not the solver's target assignment. They are
identical here, since both moves scheduled cleanly. When a plan cannot
schedule everything it proposed, see the deadlock note below.

A group the gate does not act on prints one line and stops:

```
Group fc-tier2 → NO ACTION: imbalance 0.0% is below gates.imbalance_threshold (20.0%)
```

## Reading a move line

`1. db01(102):scsi0  san-a → san-c  1.50 TiB  ~2.2h  Δimbalance -4.53  ℓ/z 1.67`
shows the disk (its VM's name, then its vmid in parentheses, then the
device), the current and target storage, the size, the estimated mirror
duration, and `ℓ/z`. The mirror duration is
`size / migration.bwlimit_bytes_per_sec`, plus a `+wipe <time>` suffix
when `saferemove` on the source storage adds one (see the payback section
below). The `Δimbalance` value is this move's own effect on the group's
imbalance metric at the moment it was scheduled. A negative value means
imbalance went down, the usual case. A move scheduled mainly to resolve a
reserve violation or consolidate a VM can show a positive value and still
be correct. `ℓ/z` is load per TiB. Section 7.3 calls it the "single best
indicator of a good migration candidate: high I/O concentrated in a small
disk."

A move whose own duration exceeds `migration.max_single_move_duration`
carries a `⚠ exceeds migration.max_single_move_duration` suffix. It also
always fails the plan (see below). This is a hard, per-move rule,
independent of whether the plan as a whole looks profitable.

The scheduler orders some moves first *regardless* of their ratio. It does so
when the storage a move leaves currently breaches its snapshot reserve or its
configured `free_space.soft` requirement. `free_space.soft` is the capacity a
storage must always keep free. The requirement is the larger of two values: `snapshot_reserve.factor`
times the largest footprint of one VM on the storage (the sum of its disks
there), or `free_space.soft` (`IMPLEMENTATION_PLAN.md` section 5.3, constraints
(C4)/(C5)/5.3.1). The `ACT: reserve violated on ...` header in human output
implies such a move. Safety is not subject to hysteresis (section 13). So such a
move always wins over a purely balance-driven move.

`repair` (visible in `--json`, `[repair]` in human output) marks a move
that the plan's own shortfall *depends on*. Hold that one disk back on
its current storage, in the plan actually executed, and the group ends
short by more than it is. This is not the same question as "did this
move's own source violate something". An *indirect* repair (a move that
empties the destination another repair needs) is marked too, even though
its own source was clean. A *redundant* repair (either of two moves alone
would fix the violation) is marked on neither. Holding back just one
still leaves the other to finish the job. See the `payback:` line below
for what the plan as a whole being exempt actually depends on. A
per-move `repair: true` marker is a report, not itself the trigger.

**`⚠ unfixable shortfall` means the plan cannot free what you asked for.**
Every storage must end a plan with its snapshot reserve free and its
configured `free_space.soft` free. When no placement of the disks this
run is allowed to move gets there, `plan` (and `explain`, and `apply`)
says so. It names the amount still missing per storage. It also lists
the *pinned* disks sitting on those storages -- the ones you can unpin
(apply or revert a pending config change, clear snapshots, wait out a
lock) to give the next run something to move:

```
Group tier2 → ACT: reserve violated on slow-a, slow-b; acting now regardless of the normal drift/imbalance thresholds -- a capacity shortfall is never delayed by them
  solver: cbc (optimal)
  ⚠ unfixable shortfall: 231.05 GiB still short of the snapshot reserve / free-space requirement after this plan (slow-a 138.00 GiB, slow-b 93.05 GiB) -- no assignment of the movable disks can close it
    pinned on the short storages (unpin to let the next run move them):
      app01(144592):scsi0 on slow-a -- pending config change (unapplied)
      db02(337307):scsi0 on slow-b -- snapshots present (2)
```

A group whose gate forced `ACT` because of a shortfall and that then moves
nothing is not being ignored. This line is the answer to "why not". Under
`solver: cbc (optimal)` it is a proof. CBC first minimizes the total
shortfall on its own, before anything else. So no placement of the movable
disks does better. Under `solver: heuristic` the line says it is not
proven. Shortfalls are counted in whole MiB, rounded up. One byte short
is short. It prints as 1.00 MiB. The line repeats on every run until the
cause is fixed. The monitoring status file carries the same warning.

**`no moves made` means the plan chose to stay put.** The gate decides
that a group is *planned*. The objective decides whether anything moves.
Keeping every disk where it is can be the best plan. When the gate said
`ACT` and nothing moves, and neither a deadlock nor an unfixable shortfall
explains it, `plan` and `apply` say so:

```
Group tier1 → ACT: capacity spread 112.2% meets or exceeds gates.capacity_spread_threshold (25.0%) -- acting now regardless of I/O drift/imbalance
  solver: cbc (optimal)
  no moves made: keeping the current placement scores best under the configured objective weights -- the gate decides that a group is planned, not that the plan must move something (explain shows the closest rejected move and why)
    the capacity gate opened this group: with beta 0.25 per move, gamma 0.05 and delta 0.5 per TiB only a disk larger than X* = 269 GiB can pay for its move; raise objective.delta_capacity_spread or lower objective.beta_move_count to spread data more aggressively, or raise gates.capacity_spread_threshold (null disables it) to stop planning for it
```

Under `solver: cbc (optimal)` "scores best" is proven. Under the heuristic
the line says it is not. The second line appears only when the capacity
gate opened the group. There the I/O is typically balanced already, and the
data-spread weight alone has to pay for every move. It is a price per
TiB, so only a disk larger than the break-even size `X*` printed on the
line can pay for its own move (the configuration chapter's
`objective.delta_capacity_spread` entry derives it). After an imbalance
gate the usual cause is a hotspot no placement can relieve, typically
one disk carrying most of the group's load. `explain`'s pinned-load line
gives the best spread achievable. `explain` prints its own, fuller
version: the closest rejected move and the objective arithmetic that
rejected it.

**A `⚠` line means a deadlock, not a hidden failure.** If the target
assignment includes a move this run cannot find any transient-feasible
order for, `plan` says so explicitly. That is `IMPLEMENTATION_PLAN.md`
section 8.3's "report, never force" path. Staging and plan-splitting are
not yet implemented, so this is where a genuine cycle or an unavoidable
capacity shortfall currently surfaces. The tool does not silently omit
the move. It also does not tell you a plan is clean when part of it is
not achievable. When only *some* moves deadlock, the
`after:`/`spread:`/`payback:` lines report the state reachable by the
moves that did schedule. They never report the fuller picture the
undeliverable ones would have produced.

## The `split:` line

A group can hold a VM larger than `snapshot_reserve.split_vm_footprint`
(default 2 TiB). For each such VM that the plan changes, or that is still
above its cap afterwards, the group's output carries one line:

```
  split: VM 701 largest footprint 10.00 TiB → 4.00 TiB (cap 2.00 TiB, excess 8.00 TiB → 2.00 TiB — the solver found no better split across 3 storages)
```

*Largest footprint* is the most of that VM any one storage holds. It is
the sum of the VM's disks on that storage. A snapshot of the VM has to
find room for that figure, doubled at the default reserve factor. *Cap*
is the threshold the VM is spread towards. A single disk larger than the
threshold raises its own VM's cap to that disk's size. *Excess* is how
far the largest footprint is above the cap. With fewer storages than
disks the cap is usually unreachable, and the line says so. A result
still above the cap ends "the solver found no better split across 3
storages" when the MILP settled on it. The solver minimizes the whole
objective within `solver.mip_gap`, so this is not a proof that no other
split has a lower peak. Otherwise the line ends "still above the cap".
A group is planned for this reason even when its I/O and data are in
balance (the gate reads "VM 701 holds … against a … cap … acting now
regardless of I/O drift/imbalance"). Such a plan has to pay for itself
like any balance plan. Splitting is a preference, not a repair. It gets
no exemption from the `payback:` test below.

## The `payback:` line

Section 7.3's acceptance test is `benefit >= migration.payback_ratio *
cost`. Both sides are in load-seconds. `benefit` is `(alpha_spread * ΔE +
delta_capacity_spread * ΔF + kappa_vm_affinity * ΔA + mu_vm_split_per_tib *
ΔO) * migration.payback_horizon`. `O` is the summed split excess of large
VMs (see "The `split:` line" below). The `E`/`F`/`A`/`O` here are section
7.2's own *unweighted* terms, not the solver's already-scaled objective
terms. Passing the scaled terms instead would double-apply the weight.
`ΔA` may be negative. A negative `ΔA` reduces the benefit. A balance move
that splits a VM pays for that fragmentation out of its other gains.
`E_after`/`F_after`/`A_after` are evaluated against what `plan`'s own
scheduler actually ordered, not the solver's aspirational target. So a
partially-deadlocked plan is scored on the moves it can really make, not
on moves it cannot. `cost` sums every *scheduled* move's
`duration_mirror * (source_load_weight + target_load_weight) +
duration_wipe * wipe_load_weight`. A disk below `migration.tiny_disk_bytes`
costs `0` regardless of duration (section 7.1). A ✓ plan passed. A ✗ one
did not. A plan made entirely of moves below `migration.tiny_disk_bytes`
has `cost = 0`. It renders as `ratio inf (need 10) ✓`. That is a real,
correct verdict, not a formatting bug.

A ✗ plan can fail for two different reasons, reported as two different
lines, because they call for different fixes:

- **Economic failure**: the balance benefit does not outweigh the
  migration cost. Adjust `objective`'s weights, `migration.payback_ratio`,
  or accept the plan is not worth running.
- **Hard-duration failure**: some move's own `duration_mirror +
  duration_wipe` exceeds `migration.max_single_move_duration`, regardless
  of whether the plan as a whole is profitable. Fix `saferemove`
  throughput, `migration.bwlimit_bytes_per_sec`, or the duration limit
  itself.

Either, both, or neither can apply to the same plan. `plan` names exactly
which happened. It does not print one generic "does not pass the payback
test" line for both.

**A plan that leaves the group with less reserve/free-space shortfall
than it found always passes this test.** This holds regardless of the
ratio shown. The example above happens to pass on merit (133 ≥ 10). A
plan whose *only* move fixes a snapshot-reserve or `free_space.soft`
violation with zero balance benefit is accepted too. That is a real,
common case. Relocating the sole loaded disk in a two-storage group
changes which side carries it. It does not reduce spread at all. The
exemption is `--json`'s `payback.repair_exempt`. It is decided on the
plan's *outcome*, not on any one move's own flag. The test compares the
executed endpoint's `Σ r_s` to the current assignment's
(`payback.reserve_shortfall_bytes_before`/`_after`): the endpoint must be
strictly lower. A plan that moves a disk off a violating storage but
leaves the group no less short in total is **not** exempt. Section 13's
"the reserve is never traded against balance" applies here exactly as it
does to the gates. An operator does not get to decline a capacity
emergency fix because it scores poorly against
`migration.payback_ratio`. The hard per-move duration rule is not
exempted this way. It is an operational limit, not an economic one. It
still blocks the plan. A move it excludes is also excluded from what
`repair_exempt` scores. A repair that a hard rule blocks is correctly not
exempt either.

**What a ✗ (or a rejected move) does *not* do today: automatically make
the plan smaller and retry.** Section 7.3 describes re-solving with
`beta` and `gamma` doubled, up to three times. That loop converges on the
highest-value subset of moves. It is not implemented. A failing plan is
reported and left for you to review. The tool does not adjust it
silently. See `docs/internals/96-payback.md`.

## What `plan` does not yet do

- **No pinned block, fragmentation naming, or pinned-load line.** Unlike
  `IMPLEMENTATION_PLAN.md` section 9.5's own example, `plan`/`apply` print
  only the move list and the payback verdict. That narration (including
  the per-pin `→` action hint) lives in `pve-storage-drs explain` instead
  (`docs/manual/29-explain.md`). `show-load` also shows each pin inline,
  per disk.
- **No automatic re-solve-and-shrink on a failing payback test** (see
  above). A failing plan is reported. The tool does not fix it for you.
- **`plan` itself still only reads `state.json`, never writes it.** Its
  gate reads real `last_balance` history when a group has one recorded
  (see `docs/internals/15-state.md`). A disk or storage cooldown pins or
  excludes exactly as described below. But `plan` never executes a
  migration. So it never has anything of its own to record. `apply` is
  what writes `last_balance` and cooldowns now, after a run that actually
  executed at least one migration (`docs/manual/28-apply.md`). A group
  with no `state.json` yet, or one `apply` has never touched, still
  evaluates as a first run (drift gate skipped).
- **Cooldowns.** A disk moved within `gates.cooldown_per_disk` is pinned
  and excluded from this run's solve. `plan` itself does not print pins
  at all (see above). `show-load`/`explain` both show it as
  `[pinned: cooldown: ...]`. A storage that was a migration's
  *destination* within `gates.cooldown_per_storage` accepts no new
  incoming moves from either backend. See `docs/internals/15-state.md`,
  `docs/internals/60-topology.md`
  and `docs/internals/90-heuristic.md`.
- **No staging, no concurrent scheduling.** Documented as deliberate, not
  forgotten, in `docs/internals/95-schedule.md`.

`--json` emits `groups[]`. Each group has `gate` (identical shape to
`show-load`'s) and `solver_backend`/`solver_status`. That pair is
`null`/`null` when the gate said `NO ACTION`. Otherwise it is
`"heuristic"`/`null`, or `"cbc"` with `"optimal"`/`"feasible"` -- the same
information the human output's `solver:` line names. Each group also has
`moves[]`. A move carries `disk_key`, `vmid`, `vm_name`, `device`,
`from_storage`, `to_storage`, `size_bytes`, `imbalance_reduction`,
`format_from`/`format_to`, `repair`, `load_per_tib`,
`duration_mirror_seconds`, `duration_wipe_seconds`, `cost_load_seconds`,
`exceeds_max_duration`. `format_from`/`format_to` is the disk's format
before the move and the one it arrives in. The two are equal unless the
target storage sets `enforce_format`. They are `null` on a hand-built
move. `repair` is the section 7.3 revert-test marker (see "The `payback:`
line" above). The group also has `vm_splits[]`, one entry per `split:`
line: `vmid`, `cap_bytes`,
`peak_footprint_bytes_before`/`_after`, `excess_bytes_before`/`_after`. It
also has `deadlocked` (a list of disk keys) and `deadlock_message`
(`null` if none). It has `before_spread`/`after_spread`, the section 6
spread fraction before the plan and after every scheduled move. It has
`before_capacity_spread`/`after_capacity_spread`. These two fields hold
the *relative* fill-fraction spread that the capacity gate compares, before
and after in the same way. The spread is `(max − min) / mean` of bytes used /
capacity. It is a fraction, not the TiB term that
`objective.delta_capacity_spread` prices. The value is
`null` for a group whose mean fill is 0 or that has not solved. The
group also has `before_objective_total`/`after_objective_total`, the
section 5.4 objective's full `.total`. `evaluate_assignment()` re-scores
it at the same true weights `validate_corpus.py`'s cross-backend check
uses -- REVIEW.md AA-01. It has `load_error` (`null` unless Prometheus
failed for this group) and `payback`. `payback` is `null` when there is
no `GroupLoad` or the gate said `NO ACTION`. Otherwise it is an object
with `benefit_load_seconds`, `total_cost_load_seconds`, `ratio`,
`aggregate_ok`, `repair_exempt`,
`reserve_shortfall_bytes_before`/`_after`,
`split_excess_bytes_before`/`_after`, `rejected_moves` and `accepted`.
`aggregate_ok` holds the economic test alone, or `true` if exempted.
`repair_exempt` is the outcome trigger itself (see above).
`reserve_shortfall_bytes_before`/`_after` holds `Σ r_s` on the current
assignment and on the plan's executed endpoint. `repair_exempt` is
decided from it. `split_excess_bytes_before`/`_after` holds the summed
split excess of the group's large VMs, in bytes. The `split:` lines are
drawn from the same pair of figures. `rejected_moves` holds the disk keys
failing the hard duration rule. `accepted` is `true` when `aggregate_ok`
is `true` and `rejected_moves` is empty. `unfixable_shortfall` is `null` unless the
plan leaves a storage short. It then holds an object with `total_bytes`,
`by_storage`, `proven`, `pinned_blockers`. `by_storage` maps a storage id
to the bytes still short, whole MiB rounded up. `proven` is `true` only
for `solver_backend: "cbc"` with `solver_status: "optimal"`.
`pinned_blockers` holds `disk_key`, `storage`, `reason` for every pinned
disk on a short storage. Under `forecast.model: holt_winters` the group
also has a `forecast` object: `model`, `used`, `backtest_error`,
`baseline_error`, `disks_scaled`, `disks_kept`. The object is absent
under the default `quantile`.
