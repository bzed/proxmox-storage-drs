# Reading `explain`

`explain` runs the identical gate/solve/schedule/payback pipeline as `plan`
(`docs/manual/27-plan.md`). It uses the same load, the same gate, the same solver,
the same scheduler and the same payback test, and gets byte-for-byte the same
numbers. It prints everything that `plan` shows, plus the "why" that `plan` never
prints:

- the measured load from which every one of those numbers comes;
- which disks are pinned, and the exact reason;
- which VMs a pin leaves on more than one storage;
- the objective of section 5.4, broken into its seven terms;
- whether the pinned load is so large that the remaining imbalance is structural,
  not a shortfall of the planning.

`-v` also names exactly which Prometheus query produced all of this. The command
never changes anything, in any `execution.mode`, exactly like `plan`.

This example extends the worked example of section 14, which the manual page of
`plan` uses, with one more VM, `106` (`archive01`). Its `scsi0` has two real
snapshots, so the tool pins it (section 3.7). Its `scsi1` is an ordinary movable
disk on a different storage. This is the "cannot fully consolidate" case that
section 3.6 names:

```
$ pve-storage-drs -c /etc/pve/drs.yaml explain
Group fc-tier1 → ACT: imbalance 255% exceeds gates.imbalance_threshold (20%)
  solver: heuristic
  1. db01(102):scsi0            san-a → san-b     1.50 TiB   ~2.2h   Δimbalance -4.00   ℓ/z 1.67
  2. web01(101):scsi0           san-a → san-c     2.00 TiB   ~2.9h   Δimbalance -3.40   ℓ/z 1.50
  3. mail01(103):scsi0          san-b → san-a   512.00 GiB   ~43.7m   Δimbalance -0.80   ℓ/z 0.80
  4. cache01(105):scsi0         san-c → san-a   512.00 GiB   ~43.7m   Δimbalance -0.40   ℓ/z 0.40
  after: san-a=2.50  san-b=2.90  san-c=3.00
  spread: 257.1% → 17.9%
  payback: benefit 2.52e+08 load·s vs cost 4.72e+04 load·s → ratio 5.34e+03 (need 10) ✓
  objective: imbalance 0.6 + moves 1 + bytes 0.225 + fragmentation 1.43 + spread 0.25 + split 0 + reserve 0 = 3.5
  measured load:
  san-a  provisioned 5.50 TiB/8.00 TiB  L=7.40 u=7.40  ⚠ reserve short by 3.50 TiB  (largest VM footprint 3.00 TiB = web01(101), requires 6.00 TiB free)
    web01(101):scsi0             2.00 TiB  raw     ℓ 3.00
    web01(101):scsi1             1.00 TiB  raw     ℓ 1.00
    db01(102):scsi0              1.50 TiB  raw     ℓ 2.50
    archive01(106):scsi0         1.00 TiB  raw     ℓ 0.90  [pinned: snapshots present (2)]
  san-b  provisioned 2.00 TiB/8.00 TiB  L=0.80 u=0.80  reserve OK  (largest VM footprint 1.00 TiB = app01(104), requires 2.00 TiB free)
    mail01(103):scsi0          512.00 GiB  raw     ℓ 0.40
    app01(104):scsi0             1.00 TiB  raw     ℓ 0.30
    archive01(106):scsi1       512.00 GiB  raw     ℓ 0.10
  san-c  provisioned 512.00 GiB/8.00 TiB  L=0.20 u=0.20  reserve OK  (largest VM footprint 512.00 GiB = cache01(105), requires 1.00 TiB free)
    cache01(105):scsi0         512.00 GiB  raw     ℓ 0.20
  pinned (not movable this run):
    archive01(106):scsi0         1.00 TiB  on san-a  ℓ 0.90  ℓ/z 0.90  -- snapshots present (2)  → clear snapshots to unblock
  cannot fully consolidate:
    106 (archive01)  scsi0: snapshots present (2)
  pinned load 0.90 of 8.40 (10.7%, warn at 25%);  best achievable spread given pins: 17.9%
```

Everything up to and including the `payback:` line is identical to the output of
`plan` for the same input. See `docs/manual/27-plan.md` for how to read the move
lines and the payback verdict. The text after that line is new.

## The `forecast:` line

The line appears only under `forecast.model: holt_winters`, just before the
`objective:` line, once for each group whose load the tool computed:

```
  forecast: holt_winters used (backtest error 0.08 vs baseline 0.14): 37 disks scaled to their forecast p95, 5 kept as observed
  forecast: holt_winters not used -- it did not beat the quantile baseline on this group's recent history (or there is not enough of it yet); loads are as observed
```

`used` means that the tool scaled the load of each disk in the group (the `ℓ` in
every number above and below) to a Holt-Winters forecast of its p95 over the next
`window.lookback`. The two errors come from the backtest that made the decision
(see `forecast.model` in `docs/manual/10-configuration.md`). "Kept" disks are
flagged for low coverage, are idle, or had no fit. `plan --json` and
`explain --json` carry the same facts as a `forecast` object per group. `show-load`
prints the same line (and the `--json` object), so that nobody mistakes its loads
for observed loads.

## The `objective:` line

This is the objective of section 5.4 that the solver actually minimized, broken
into its seven terms instead of only the total:

- `imbalance`: `alpha` times the spread metric.
- `moves`: `beta` times the number of moves.
- `bytes`: `gamma` times the TiB moved.
- `fragmentation`: `kappa` times the I/O-weighted number of extra storages of each
  VM beyond one. The weight is `w_v` of section 5.4, so a VM that does several
  times the average I/O of the group costs correspondingly more to split.
- `spread`: `delta` times the data-spread deviation of section 5.3 (C7).
- `split`: `mu` times the TiB by which a VM above
  `snapshot_reserve.split_vm_footprint` exceeds its cap on its fullest storage. It
  is zero when no VM is that large.
- `reserve`: the penalty for any remaining (C5) shortfall. It is zero on a plan
  that resolves the shortfall or never had one.

The solver itself compares candidate assignments with the same
`heuristic.ObjectiveBreakdown`. That is why this class keeps the seven terms apart
instead of only a `.total`. The tool prints the line only when the gate said `ACT`.
A `NO ACTION` group solved nothing in this run, so it has no objective to show.

## `no moves made: ...` / `closest alternative: ...`

The tool prints these lines only when the gate said `ACT` *and* the optimum of the
solver still moves nothing: every disk is eligible, nothing is pinned, but the
objective is lowest at the current assignment. This is a real, expected outcome,
not a bug. It happens when the only move (or moves) that would improve the spread
clearly costs more, in `moves`/`bytes`/`fragmentation`, than the imbalance that it
repairs is worth under the configured weights. Without this section, you cannot
tell this case apart from "the solver did not try". The one-line verdict of `plan`
says `ACT` in both cases.

`explain` finds the single-disk move that is closest to being worth it. It tries
every movable disk against every other storage of the group. It evaluates each with
the same objective that the solver minimizes (the one-move neighbourhood of section
5.3). It shows the arithmetic, term by term, that rejected the move:

```
  objective: imbalance 0.576 + moves 0 + bytes 0 + fragmentation 0 + spread 0 + split 0 + reserve 0 = 0.576
  no moves made: the objective is lowest at the current assignment
  closest alternative: vm110(110):scsi1 VM-krbd → VM
    imbalance 0.576→0.0426, moves 0→0.25, bytes 0→0.00732, fragmentation 0→0.5, spread 0→0, split 0→0, reserve 0→0
    total 0.576 → 0.8  (worse by 0.223 -- rejected)
```

Read from left to right. A move of `vm110(110):scsi1` from `VM-krbd` to `VM` would
cut the imbalance term from `0.576` to `0.043`, a real improvement. But `110` is a
VM with two disks, and its other disk stays. The move therefore splits the VM
across two storages. The fragmentation penalty of `objective.kappa_vm_affinity` (`0`
→ `0.5`) for that split outweighs the gain. If you want to accept this trade-off
instead of rejecting it, lower `objective.kappa_vm_affinity` (or
`objective.beta_move_count`/`gamma_move_bytes_per_tib`, whichever term dominates
the rejection). A rejection is no reason to suspect the solver.

The tool omits these lines when there is nothing to compare against (every disk
pinned, or a group with one storage), or when the plan actually moved something.

## `measured load:`

This is the input of section 4 from which every number above comes. It is identical
to the report that `show-load` gives per storage and per disk
(`docs/manual/25-show-load-and-verify-storages.md`): the used and total capacity of
each storage, `L_s`/`u_s`, the reserve status, and every disk on the storage. For
each disk, it shows the size, the format, the measured `ℓ_d` when the tool fetched
one, and `[pinned: ...]` when section 5.3 (C2) excludes the disk. The block is
always present, also for a `NO ACTION` group and also when no migration was possible
at all. It is the data that the rest of the narrative of `explain` is *about*, not a
part of the plan itself.

## `-v`: the `data source:` line

This is one extra line. The tool prints it once for the whole run, not once per
group, because it computed every group here with the identical selector and window.
The line shows the node-scoping filter of section 3.4 that the queries of this run
used (`(no node-scoping filter)` if none applied), and the
`window.lookback`/`quantile`/`metrics.rate_window`/`metrics.step` settings behind
the load above. See `docs/manual/10-configuration.md` for what each setting
controls, and `IMPLEMENTATION_PLAN.md` section 3.4 for the filter itself. This is
the one part of the output of `explain` that is about *how* the tool fetched the
data, not about the data itself. For this reason, it is the one thing here that only
`-v` shows. By default, the line shows the alternation of the node names of this
cluster. With `metrics.extra_selector` set, it shows that value instead:

```
$ pve-storage-drs -c /etc/pve/drs.yaml -v explain
data source: {nodename=~"pve01|pve02|pve03"}  window 1.0d lookback, quantile 0.95, rate_window 5.0m, step 5.0m

Group fc-tier1 → ACT: imbalance 255% exceeds gates.imbalance_threshold (20%)
  ...
```

(With `metrics.extra_selector: 'cluster="mycluster"'`, the same line instead reads
`data source: {cluster="mycluster"}`.)

## `pinned (not movable this run):`

This block lists every disk that section 5.3 (C2) excludes from the solve of this
run, in the same `name(vmid):device` order as `show-load`. For each disk, it shows
the size, the current storage, the measured load (`ℓ`), the `ℓ/z` ratio when one is
available, and the exact reason. The possible reasons are:

- a real snapshot or an unreferenced companion volume (section 3.7);
- an unapplied pending config change (section 3.8);
- a config exclusion;
- a `gates.cooldown_per_disk` that is still running;
- a VM config lock;
- a small disk (below `migration.tiny_disk_bytes`) whose VM has no larger disk in
  this group to move with.

The text is identical to the `[pinned: ...]` text that `show-load` prints per disk.
`explain` collects it into one block instead of mixing it with movable disks,
because pins are the subject of `explain`, not a side note.

A pin with something that you can act on, or wait for, gets a trailing `→ <hint>`:

| Reason | Hint |
|---|---|
| real snapshot | "clear snapshots to unblock" |
| unreferenced volume (the reason names it as `storage:volume`) | "check that volume and, if it is a leftover copy, delete it by hand to unblock" |
| pending config change | "apply the pending change (reboot the VM) or revert it, then re-check" |
| cooldown | "re-check next run" |
| VM lock | "re-check next run once the lock releases" |

A standing policy exclusion (`exclude.*`, or an `unusedN` disk that the config
deliberately skips) has no hint. You do not unblock such a pin. It is a choice that
the config already made.

## `cannot fully consolidate:`

This block names a VM whose disks still sit on more than one storage after
everything that the plan of this run actually scheduled, *because* at least one of
them is pinned. The block does not report a VM that an ordinary plan without pins
spreads across storages on purpose. That is the plan working as intended, not a
blocker. This is almost exactly the example of section 3.6: "evacuating a storage
completely is ... not achievable [when] it is because of a section 3.7 snapshot or
an explicit exclusion, never because of a device type". `explain` names which one,
and on which device. A plan does not just leave a stray volume behind without a
word.

## `pinned load ... ; best achievable spread given pins: ...`

The line compares the pinned load of this group, as a fraction of its total
measured load, with `report.warn_pinned_load_fraction` (default `0.25`). Below the
threshold, as in the example above, the line is only information. Above it, a second
line with a `⚠` prefix follows: the remaining imbalance may be structural. So much
load is pinned that no achievable placement of the *movable* disks alone gets the
group much closer to balance. This is then not a sign that the solver or the
weights need attention. `best achievable spread given pins` is exactly the spread of
the `after:` line above. Every solve (heuristic or MILP) already keeps every pinned
disk on its current storage and optimizes only the movable disks
(`x_{d,sigma_0(d)} = 1` of section 5.1 for `d` outside `D^mov`). What the plan
reached *is* thus the best that this set of pins allows. Only the removal of the
pins named above can do better. A larger `objective` weight or a longer
`solver.time_limit_seconds` cannot. The tool omits the line for a group with no
measured load at all (an idle group, or a group whose load `explain` could not get).

A `NO ACTION` group still gets the sections above on measured load, pins,
fragmentation and pinned load. They describe the state of the disks of the group,
not the plan. A gate that finds nothing to balance in this run is no reason to hide
them.

`--json` shows everything that `plan --json` shows (the field list of
`docs/manual/27-plan.md`), plus these fields:

- `objective`: the seven terms above, or `null` when the gate said `NO ACTION`.
- `rejected_alternative`: `null` unless the "`no moves made`" case above applies.
  Otherwise it has `disk_key`, `vmid`, `vm_name`, `device`, `from_storage`,
  `to_storage`, `baseline`, `objective` and `worse_by`. `baseline` and `objective`
  use the same seven-term breakdown as the `objective` field above, for the current
  assignment and for the candidate. `worse_by` is the difference between the two
  totals.
- `storages`/`disks`: the measured-load section above, with the same shape as the
  fields of the same name in `show-load --json`.
- `pinned_disks`: `disk_key`, `vmid`, `vm_name`, `device`, `current_storage`,
  `size_bytes`, `load`, `load_per_tib`, `reason` and `action_hint` (`null` for a
  standing policy exclusion, the same rule as for the `→` line of the human report).
- `fragmentation`: a list of `{vmid, vm_name, blockers}`. Each blocker is an object
  with `device`, `disk_key` and `reason`.
- `pinned_load`: `null` for an idle group. Otherwise `pinned_load`, `total_load`,
  `fraction` and `warn_fraction`.

The JSON output has no notion of `-v`, unlike the human report. A top-level `query`
object (`node_selector`, `window_lookback_seconds`, `quantile`,
`rate_window_seconds`, `step_seconds`) is always present, once per response, not
once per group. It is the JSON counterpart of the `-v` `data source:` line above.
