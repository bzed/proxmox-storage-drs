# Reading `explain`

`explain` runs the identical gate/solve/schedule/payback pipeline `plan`
does (`docs/manual/27-plan.md`) — same load, same gate, same solver, same
scheduler, same payback test, byte-for-byte the same numbers — and prints
everything `plan` already shows, plus the "why" `plan` itself never does:
the measured load every one of those numbers derives from, which disks are
pinned and the exact reason, which VMs a pin leaves spread across more than
one storage, the section 5.4 objective broken into its five terms, and
whether the pinned load is large enough that the residual imbalance is
structural rather than a planning shortfall. `-v` additionally names
exactly which Prometheus query produced all of it. It never changes
anything, in any `execution.mode` — exactly like `plan`.

This example extends the section 14 worked example `plan`'s own manual
page uses with one more VM, `106` (`archive01`): its `scsi0` carries two
real snapshots, so it is pinned (section 3.7), while its `scsi1` is an
ordinary movable disk on a different storage — the "cannot fully
consolidate" case section 3.6 exists to name:

```
$ pve-storage-drs -c /etc/pve/drs.yaml explain
Group fc-tier1 → ACT: imbalance 255% exceeds gates.imbalance_threshold (20%)
  solver: heuristic
  1. 102:scsi0      san-a → san-b     1.50 TiB   ~2.2h   Δimbalance -4.00   ℓ/z 1.67
  2. 101:scsi0      san-a → san-c     2.00 TiB   ~2.9h   Δimbalance -3.40   ℓ/z 1.50
  3. 103:scsi0      san-b → san-a   512.00 GiB   ~43.7m   Δimbalance -0.80   ℓ/z 0.80
  4. 105:scsi0      san-c → san-a   512.00 GiB   ~43.7m   Δimbalance -0.40   ℓ/z 0.40
  after: san-a=2.50  san-b=2.90  san-c=3.00
  spread: 257.1% → 17.9%
  payback: benefit 5.2e+06 load·s vs cost 4.72e+04 load·s → ratio 110 (need 10) ✓
  objective: imbalance 0.6 + moves 1 + bytes 0.225 + fragmentation 0.5 + reserve 0 = 2.32
  measured load:
  san-a  used 5.50 TiB/8.00 TiB  L=7.40 u=7.40  ⚠ reserve short by 1.50 TiB  (largest disk 2.00 TiB, requires 4.00 TiB free)
    101:scsi0        2.00 TiB  raw     ℓ 3.00
    101:scsi1        1.00 TiB  raw     ℓ 1.00
    102:scsi0        1.50 TiB  raw     ℓ 2.50
    106:scsi0        1.00 TiB  raw     ℓ 0.90  [pinned: snapshots present (2)]
  san-b  used 2.00 TiB/8.00 TiB  L=0.80 u=0.80  reserve OK  (largest disk 1.00 TiB, requires 2.00 TiB free)
    103:scsi0      512.00 GiB  raw     ℓ 0.40
    104:scsi0        1.00 TiB  raw     ℓ 0.30
    106:scsi1      512.00 GiB  raw     ℓ 0.10
  san-c  used 512.00 GiB/8.00 TiB  L=0.20 u=0.20  reserve OK  (largest disk 512.00 GiB, requires 1.00 TiB free)
    105:scsi0      512.00 GiB  raw     ℓ 0.20
  pinned (not movable this run):
    106:scsi0        1.00 TiB  on san-a  ℓ 0.90  ℓ/z 0.90  -- snapshots present (2)  → clear snapshots to unblock
  cannot fully consolidate:
    106 (archive01)  scsi0: snapshots present (2)
  pinned load 0.90 of 8.40 (10.7%, warn at 25%);  best achievable spread given pins: 17.9%
```

Everything up to and including the `payback:` line is identical to
`plan`'s own output for the same input — see `docs/manual/27-plan.md` for
how to read the move lines and the payback verdict. What follows is new.

## The `objective:` line

The section 5.4 objective the solver actually minimized, broken into its
five terms rather than only the total — `imbalance` (`alpha` times the
spread metric), `moves` (`beta` times the move count), `bytes` (`gamma`
times TiB moved), `fragmentation` (`kappa` times each VM's extra storage
count beyond one), and `reserve` (the penalty for any remaining (C5)
shortfall, zero on a plan that resolves or never had one). This is the
same `heuristic.ObjectiveBreakdown` the solver itself compares candidate
assignments with — the reason that class keeps the five terms apart
instead of collapsing to only `.total` in the first place. Only printed
when the gate said `ACT`; a `NO ACTION` group solved nothing this run, so
there is no objective to show.

## `measured load:`

The section 4 input every number above derives from — identical to
`show-load`'s own per-storage, per-disk report (`docs/manual/25-show-load-
and-verify-storages.md`): each storage's used/capacity, `L_s`/`u_s`,
reserve status, and every disk on it with its size, format, measured `ℓ_d`
when one was fetched, and `[pinned: ...]` when section 5.3 (C2) excludes
it. Always present, printed even for a `NO ACTION` group and even when no
migration was possible at all — it is the data the rest of `explain`'s
narrative is *about*, not part of the plan itself.

## `-v`: the `data source:` line

One extra line, printed once for the whole run rather than once per group
(every group here was computed against the identical selector and window):
the exact section 3.4 node-scoping filter this run's queries carried
(`(no node-scoping filter)` if none applied), and the
`window.lookback`/`quantile`/`metrics.rate_window`/`metrics.step` settings
the load above was computed from — see `docs/manual/10-configuration.md`
for what each controls and `IMPLEMENTATION_PLAN.md` section 3.4 for the
filter itself. This is the one piece of `explain`'s output that is about
*how* the data was fetched rather than what it is, which is why it is the
one thing here gated behind `-v` instead of always shown. By default this
is the node-list alternation from this cluster's own node names; with
`metrics.extra_selector` set, it is that instead:

```
$ pve-storage-drs -c /etc/pve/drs.yaml -v explain
data source: {nodename=~"pve01|pve02|pve03"}  window 1.0d lookback, quantile 0.95, rate_window 5.0m, step 5.0m

Group fc-tier1 → ACT: imbalance 255% exceeds gates.imbalance_threshold (20%)
  ...
```

(With `metrics.extra_selector: 'cluster="mycluster"'`, the same line
instead reads `data source: {cluster="mycluster"}`.)

## `pinned (not movable this run):`

Every disk section 5.3 (C2) excludes from this run's solve, in the same
`vmid:device` order `show-load` lists disks, with its size, current
storage, measured load (`ℓ`) and `ℓ/z` ratio when one is available, and
its exact reason — a real snapshot or an unreferenced companion volume
(section 3.7), a config exclusion, a still-running
`gates.cooldown_per_disk`, or a VM config lock. Identical text to what
`show-load` already prints per disk as `[pinned: ...]`; gathered here into
one block instead of interleaved with movable disks, because pins are
`explain`'s subject, not an aside.

A pin with something to actually act on or wait for gets a trailing
`→ <hint>` — "clear snapshots to unblock" for a real snapshot, "remove the
stale reference to unblock" for an orphaned volume, "re-check next run"
for a cooldown, "re-check next run once the lock releases" for a VM
lock. A standing policy exclusion (`exclude.*`, or a deliberately skipped
`unusedN` disk) carries no hint — that pin is not something to unblock,
it is a choice already made in the config.

## `cannot fully consolidate:`

Names a VM whose disks — after everything this run's plan actually
managed to schedule — still sit on more than one storage, *because* at
least one of them is pinned. A VM legitimately spread across storages by
an ordinary, unpinned plan is not reported here; that is the plan working
as intended, not a blocker. This is section 3.6's own example almost
verbatim: "evacuating a storage completely is ... not achievable [when] it
is because of a section 3.7 snapshot or an explicit exclusion, never
because of a device type" — `explain` names which one, and on which
device, rather than a plan quietly leaving a stray volume behind.

## `pinned load ... ; best achievable spread given pins: ...`

`report.warn_pinned_load_fraction` (default `0.25`) compared against this
group's pinned load as a fraction of its total measured load. Below the
threshold, as in the example above, this line is purely informative. Above
it, a second, `⚠`-prefixed line follows: the residual imbalance may be
structural — enough load is pinned that no achievable placement of the
*movable* disks alone gets the group much closer to balanced — rather than
a sign the solver or the weights need attention. `best achievable spread
given pins` is exactly the `after:` spread line above: every solve
(heuristic or MILP) already fixes every pinned disk at its current storage
and optimizes only the movable ones (section 5.1's `x_{d,sigma_0(d)} = 1`
for `d` outside `D^mov`), so what the plan actually reached *is* the best
that pinned set permits — clearing the pins named above is the only way to
do better, not a bigger `objective` weight or a longer `solver.time_limit_seconds`.
Omitted entirely for a group with no measured load at all (an idle group,
or one `explain` could not get a load for).

A `NO ACTION` group still gets the measured-load/pinned/fragmentation/
pinned-load sections above — they describe the state of the group's disks,
not the plan, so there is no reason to withhold them just because the gate
found nothing to balance this run.

`--json` emits everything `plan --json` does (`docs/manual/27-plan.md`'s
own field list) plus `objective` (the five terms above, `null` when the
gate said `NO ACTION`), `storages`/`disks` (the measured-load section
above, identical shape to `show-load --json`'s own fields of the same
name), `pinned_disks` (`disk_key`, `vmid`, `device`, `current_storage`,
`size_bytes`, `load`, `load_per_tib`, `reason`, `action_hint` — `null` for
a standing policy exclusion, same rule as the human report's `→` line),
`fragmentation` (a list of
`{vmid, vm_name, blockers}`, each blocker an object with `device`,
`disk_key`, `reason`), and `pinned_load` (`null` for an idle group,
otherwise `pinned_load`, `total_load`, `fraction` and `warn_fraction`).
Unlike the human report, JSON has no notion of `-v`: a top-level `query`
object (`node_selector`, `window_lookback_seconds`, `quantile`,
`rate_window_seconds`, `step_seconds`) is always present, once per
response rather than once per group, the JSON counterpart of the `-v`
`data source:` line above.
