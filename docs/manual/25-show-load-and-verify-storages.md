# Reading `show-load` and `verify-storages`

Both commands only read — neither ever changes anything, in any
`execution.mode`. Run them any time you want to see what the tool sees.

## `show-load`

Prints every storage in every configured group, its disks, and its
snapshot-reserve status. This example uses the group from
`IMPLEMENTATION_PLAN.md` section 14's worked example (`config/drs.example.yaml`
ships the same group and weights) so the numbers are traceable to that
section rather than invented for this page:

```
$ pve-storage-drs -c /etc/pve/drs.yaml show-load
Group fc-tier1
  san-a  used 4.50 TiB/8.00 TiB  L=6.50 u=6.50  ⚠ reserve short by 512.00 GiB  (largest disk 2.00 TiB, requires 4.00 TiB free)
    101:scsi0        2.00 TiB  raw     ℓ 3.00
    101:scsi1        1.00 TiB  raw     ℓ 1.00
    102:scsi0        1.50 TiB  raw     ℓ 2.50
  san-b  used 1.50 TiB/8.00 TiB  L=0.70 u=0.70  reserve OK  (largest disk 1.00 TiB, requires 2.00 TiB free)
    103:scsi0      512.00 GiB  raw     ℓ 0.40
    104:scsi0        1.00 TiB  raw     ℓ 0.30
  san-c  used 512.00 GiB/8.00 TiB  L=0.20 u=0.20  reserve OK  (largest disk 512.00 GiB, requires 1.00 TiB free)
    105:scsi0      512.00 GiB  raw     ℓ 0.20
```

`L=`/`u=` on a storage's line are section 4's `L_s` (summed `ℓ` of the
disks currently on it) and `u_s = L_s / capability_weight`; `ℓ` after a
disk's size/format is that disk's own share. Both come from
`IMPLEMENTATION_PLAN.md` section 14's worked example, so the numbers above
are traceable to that section rather than invented for this page.

A pinned disk carries `[pinned: <reason>]` after its size and format —
`snapshots present (N)`, `locked: <lock>`, `excluded by config`, or
`excluded: unused disk (exclude.include_unused_disks=false)`, matching
`IMPLEMENTATION_PLAN.md` section 5.3 (C2) exactly; that reason is the
answer to "why won't it move this disk."

A disk whose measured I/O falls below `window.min_coverage` (section 3.4)
gets a `⚠ <disk> : <reason>` line of its own, right after that group's
disks, instead of a silently wrong `ℓ` — it either shows a `state.json`-
recorded last known load (not yet wired through; see
`docs/internals/70-loadmodel.md`) or `0.0`, and either way the warning says
which. `tpmstate0` and `unusedN` disks are never flagged this way: they
genuinely emit no I/O metrics, so `ℓ 0.00` for them is correct, not a gap.
A group with no measured I/O at all gets one `(idle: no measured I/O for
this group this window)` line instead of per-disk warnings.

**A Prometheus outage does not fail this command.** Sizes and reserve
status never depend on Prometheus at all; if the load fetch for a group
fails, that group's storage/disk lines simply omit `L=`/`u=`/`ℓ`, and a
`⚠ per-disk load unavailable: <reason>` line explains why — check
`verify-metrics` first if you see this.

A **`Warnings:`** block, when present, lists things worth a look but not
fatal: a disk on a storage that is not in any configured group ("ungrouped,
not managed" — check whether that storage belongs in a group), or a disk
whose size came from its own config rather than the storage's authoritative
content listing. The latter usually means the volume no longer exists on
the storage — most often because it was removed directly on the storage
backend rather than through Proxmox, which leaves a dangling reference
behind that PVE does not clean up or even notice on its own (a VM starts
fine with one; see `IMPLEMENTATION_PLAN.md` section 3.6 for a confirmed
case). If you see this warning, check whether the named volume still
exists on the storage and, if it genuinely does not, remove the stale
reference (`qm unlink <vmid> <device>` for an `unusedN` entry).

`--json` emits the same information as one object with `groups[].storages[]`
(including the exact byte counts behind the reserve check, plus `load` and
`utilization` when available) and `groups[].disks[]` (plus `load` and
`load_flagged_reason` when available), with each group carrying its own
`load_computed`, `idle` and `load_error` fields — a Prometheus outage on
one group never prevents another group's `load_computed: true` from being
reported.

## `verify-storages`

Reports `saferemove` and the wipe time it implies for the largest disk on
each storage, and warns when your configured cooldown or move-duration
limits are shorter than that implied wipe — the condition
`IMPLEMENTATION_PLAN.md` section 9.3 describes as "the next run plans onto a
storage that is still draining". Section 14's fixture has `saferemove` off
everywhere (stated explicitly there, so its payback arithmetic is
reproducible); this example instead assumes an LVM `san-b` with
`saferemove` on at PVE's default 10 MiB/s throughput, to show what the
warning looks like:

```
$ pve-storage-drs -c /etc/pve/drs.yaml verify-storages
Group fc-tier1
  san-a  saferemove=off
    saferemove is off or throughput unknown; no wipe-time check
  san-b  saferemove=on
    implied wipe time for the largest disk (1.00 TiB): 1.2d
    ⚠ gates.cooldown_per_storage (1.0h) is shorter than the implied wipe time -- the next run may plan onto a still-draining storage (section 9.3)
    ⚠ migration.max_single_move_duration (6.0h) is shorter than the implied wipe time -- a move of the largest disk would be rejected outright (section 7.3)
  san-c  saferemove=off
    saferemove is off or throughput unknown; no wipe-time check
```

Storage types without `saferemove` at all (Ceph RBD, ZFS) always report
`saferemove=off` and skip the check — there is nothing to wipe.
