# Domain invariants

This tool live-migrates disks of running production VMs between SAN LUNs. The failure modes are
"fill a LUN and stop a cluster" and "corrupt a mirror in flight". The rules below are not style
preferences; they are why the design looks the way it does. Each one names the plan section that
specifies it.

## 1. Dry-run is the default (§9.1)

Three modes: `dry-run` (default), per-step confirmation, fully automatic. Any refactor that
makes the tool act without an explicitly selected execution mode is a defect. A missing or
unparseable mode means dry-run, never automatic.

## 2. The snapshot reserve is never traded against balance (§5.3, §13)

`used + max(f·Z_s, soft_s) ≤ C_s`. The `r_s` slack exists only so an already-violating storage
does not make the model infeasible. The **lexicographic two-stage solve is the default**:
minimise `Σ r_s`, fix it, then optimise balance. The single-stage big-M form is a fallback and
its `P` is **computed at model-build time** from the group's absolute load — the config value is
a floor, not the value used. A hard-coded `P` is a bug.

One slack per storage, not one per reason: `Σ r_s` covers the snapshot term and the configured
free-space requirement together, so a byte of configured free space is exactly as non-negotiable
as a byte of snapshot reserve.

## 2a. The three floors, and which one wins (§5.3 (C5), §5.3.1, §8.1)

Three quantities want space free on a storage, and they compose in **one fixed order**. Get this
wrong and you either fill a LUN or refuse every plan:

1. **`f_s · Z_s`, the snapshot reserve, wins outright.** It enters as the first argument of a
   `max()`, never as an addend and never as something a free-space knob can reduce. Whenever the
   snapshot term is the larger of the two, it *is* the requirement and the configured free space
   is irrelevant. "If the snapshot reserve is bigger than the configured free space, the snapshot
   reserve wins" — §5.3 (C5). There is no config key that lowers it.
2. **`hard_s` is the floor at every instant, and it is what binds during a move.** §8.1's
   transient predicate is `used_b + z_d + max(f_b·max(Z_b, z_d), hard_b) ≤ C_b` — the snapshot
   term still first, but the floor component is `hard_s`, not `soft_s`. A storage may sit below
   its soft requirement while moves are in flight; it may **never** cross `hard_s`. So where the
   two disagree during execution, `hard_s` is the one the scheduler enforces.
3. **`soft_s` is the plan endpoint only.** (C5) enforces it on the finished assignment, the
   lexicographic stage repairs it, §6's override bypasses the gates for it and §7.3 exempts a
   repairing plan from payback. It says nothing about intermediate states.

`hard_s ≤ soft_s` is a hard validation error if violated (§11.1), so the transient floor is
always a relaxation of the endpoint one — never the other way round. The default `hard: null`
means `hard_s = soft_s`: no dip at all, and §8.1 exactly as strong as before free-space
requirements existed. An operator who sets `hard` strictly below `soft` is deliberately buying
the scheduler room for a bounded, planned dip on a storage the finished plan leaves compliant.

Two `null`s, and they do not mean the same thing: **global** `hard: null` is a *value* ("no dip",
`hard_s = soft_s`); **per-storage** `hard: null` is an *absence* ("inherit the global"). Same
inheritance `reserve_factor` already has.

The deprecated `snapshot_reserve.min_free_bytes` folds in **per storage, after percent-to-bytes
conversion, as the last step**: `soft_s = max(soft_s_resolved, min_free_bytes)`. Validate the
written values *first* (`hard ≤ soft`, `soft < C_s`), then fold — checking after the fold would
let a written `hard > soft` hide behind the deprecated key and blow up the moment the operator
deletes it, which is exactly what the deprecation warning asks them to do.

## 2b. Provisioned size, never allocated — over-provisioning is never considered (§5.1)

`z_d` is the disk's *provisioned* size and a storage is counted as holding `Σ z_d·x_{d,s} + Uˢᵉˣᵗ`,
on thin-provisioned pools (Ceph RBD, LVM-thin, ZFS) exactly as on thick ones. The pool's own `used`
(from `GET .../status`) is thinner and is **display-only**: feeding it into the reserve, the
free-space requirement or the transient check would let a plan "fit" only while the disks stay thin,
which nothing bounds. Consequence to expect, not to fix: on a thin pool a `free_space.soft` can show
a shortfall the pool's numbers do not. Do not add an allocated-size mode; the
`assume_thick_provisioning: false` setting is refused for exactly that reason.

**No exceptions, execution included.** `execute.py`'s live pre-move re-check (`_live_transient_check()`,
called by both the sequential path and the concurrent launch check) sums `size` over the target's live
`GET .../content` — provisioned, like the plan's own check — and takes only `total` from `/status`;
plan §9.2 step 2. A live re-check that read `used` would be weaker than the plan it guards on a thin
pool and could only ever confirm it. Under concurrency the in-flight moves' own mirror targets are left
out of that sum (at most one volume per move: not in the launch-time listing, same VM, the moved disk's
size) because each is already charged as a `z_m`; the match is narrow on purpose — keeping a volume
too many only tightens the check, dropping one too many would weaken it. A live read that errors, or a
listed volume with no size, refuses the move (`replan_needed`); it never falls back to `used` and never
passes on a partial figure. `show-load` prints the provisioned figure and the pool's own alongside.

## 3. The invariant holds *during* moves (§8.1)

While a move is in flight the volume occupies **both** storages. The target must satisfy
`used_b + z_d + max(f_b·max(Z_b, z_d), hard_b) ≤ C_b`, generalised to the whole in-flight set
when concurrency > 1 (the sum over in-flight arrivals, the inner `max` over the same set).
There is exactly one implementation of this predicate, called with `M = {m}` for the sequential
case.

Two halves, and only one of them is a relaxation of (C5): the **floor** component drops from
`soft_b` to `hard_b`, but the **snapshot** component grows to `f_b·max(Z_b, z_d)` the moment the
incoming disk is the new largest, and the source is still charged in full. Never read §8.1 as
implied by (C5) — on the snapshot side it is strictly stronger.

## 4. A finished task is not a finished move (§8.2, §9.3)

`mirroring → draining → done`. The `move_disk` task reporting `OK` does **not** free the source:
with `saferemove` the old volume is zeroed at ~10 MiB/s first, which for a 1.5 TiB disk is ~44
hours, and it holds a lock while it runs. A move is done only when all three hold: the task
succeeded, the source volume is gone from `/storage/{src}/content`, and the VM config `lock` is
empty. Never optimistically credit the source with freed bytes.

## 5. VM locks are an open set (§9.3)

`backup`, `clone`, `create`, `migrate`, `rollback`, `snapshot`, `snapshot-delete`, `suspending`,
`suspended` — and whatever a future PVE adds. **Never whitelist lock values.** Any non-empty
`lock` means wait; the wait is bounded by config and the timeout action is `skip`, not `force`.

## 6. Never auto-delete a volume (§9.3, §13)

Orphaned target volumes from a failed move are detected and **reported**, never removed by this
tool. The operator deletes.

## 7. Disks with snapshots are excluded, loudly (§3.7)

`move_disk delete=1` is refused on a volume with snapshots, and PVE does not carry snapshots
across. Such disks are **pinned**, not dropped: their bytes and load still count in the model.
The run warns every time, naming the VMs.

## 8. Enumerate every bus (§3.5, §3.6)

`ide*`, `sata*`, `scsi*`, `virtio*`, `efidisk0`, `tpmstate0`, `unused*`. Only `media=cdrom`
entries are excluded. A regex that only matches `scsi\d+` will silently leave volumes behind and
make "evacuate this LUN" a lie.

## 9. The config lives on the cluster filesystem (§11)

The default is `/etc/pve/drs.yaml`, overridable with `-c/--config` or `$PVE_STORAGE_DRS_CONFIG`; an
explicitly named config that cannot be read is a hard failure and never falls back to the default.
Three things follow, and none of them are optional:

- **Never write to it.** It is input. Nothing the tool learns goes back into `/etc/pve` — state
  belongs in `state.path` on local disk, which is also the only place that survives a quorum loss.
- **Assume the web server can read it.** `/etc/pve` files are group `www-data`. Secrets belong in
  the environment (`PVE_PASSWORD`, `PVE_TOKEN_SECRET`), not in the file, and an API token beats a
  password.
- **A shared config is not cluster coordination.** `state.json` is node-local; the `fcntl` lock
  cannot see another node. Only the in-flight UPID scan crosses the cluster. The timer runs on one
  host.

An edit to this file is live on every node the instant it is saved, which is the reason §11.1
validation errors are fatal rather than advisory.

## 10. Do not state Proxmox behaviour you have not verified

This has bitten the project twice. Both times the mechanism was the same: a web search returned
PVE 6.x/7.x-era forum threads, undated, and the summary was written into the plan as a current
design constraint.

- The plan once asserted `efidisk0`/`tpmstate0` cannot move online. They can, on 9.2 —
  the operator did it.
- The plan once concluded per-disk metrics were unavailable. They were already in the operator's
  Prometheus.

The rule: read the PVE source, or ask the operator, or **label the claim as unverified in the
text**. If a fetch of the source truncates, retry narrower — do not silently substitute a forum
anecdote. `pve-storage-drs verify-metrics` and `pve-storage-drs verify-storages` exist precisely so claims about the live
system are checked rather than assumed.

## 11. The plan is the specification

`IMPLEMENTATION_PLAN.md` §15 is a traceability table from the original requirements to the
sections that satisfy them, and §15.1 maps every config knob to the formula that consumes it.
A knob with no formula is a bug waiting to happen; a formula with no knob is undocumented
behaviour. Keep both tables current — they are how the next agent finds its way in.
