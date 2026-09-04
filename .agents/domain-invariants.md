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

`used + max(f·Z_s, min_free_bytes) ≤ C_s`. The `r_s` slack exists only so an already-violating
storage does not make the model infeasible. The **lexicographic two-stage solve is the default**:
minimise `Σ r_s`, fix it, then optimise balance. The single-stage big-M form is a fallback and
its `P` is **computed at model-build time** from the group's absolute load — the config value is
a floor, not the value used. A hard-coded `P` is a bug.

## 3. The invariant holds *during* moves (§8.1)

While a move is in flight the volume occupies **both** storages. The target must satisfy
`used_b + z_d + f_b·max(Z_b, z_d) ≤ C_b`, generalised to the whole in-flight set when
concurrency > 1. There is exactly one implementation of this predicate, called with `M = {m}`
for the sequential case.

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

## 9. Do not state Proxmox behaviour you have not verified

This has bitten the project twice. Both times the mechanism was the same: a web search returned
PVE 6.x/7.x-era forum threads, undated, and the summary was written into the plan as a current
design constraint.

- The plan once asserted `efidisk0`/`tpmstate0` cannot move online. They can, on 9.2 —
  the operator did it.
- The plan once concluded per-disk metrics were unavailable. They were already in the operator's
  Prometheus.

The rule: read the PVE source, or ask the operator, or **label the claim as unverified in the
text**. If a fetch of the source truncates, retry narrower — do not silently substitute a forum
anecdote. `drs verify-metrics` and `drs verify-storages` exist precisely so claims about the live
system are checked rather than assumed.

## 10. The plan is the specification

`IMPLEMENTATION_PLAN.md` §15 is a traceability table from the original requirements to the
sections that satisfy them, and §15.1 maps every config knob to the formula that consumes it.
A knob with no formula is a bug waiting to happen; a formula with no knob is undocumented
behaviour. Keep both tables current — they are how the next agent finds its way in.
