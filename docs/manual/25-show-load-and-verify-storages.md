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
  san-a  used 4.50 TiB/8.00 TiB  ⚠ reserve short by 512.00 GiB  (largest disk 2.00 TiB, requires 4.00 TiB free)
    101:scsi0        2.00 TiB  raw
    101:scsi1        1.00 TiB  raw
    102:scsi0        1.50 TiB  raw
  san-b  used 1.50 TiB/8.00 TiB  reserve OK  (largest disk 1.00 TiB, requires 2.00 TiB free)
    103:scsi0      512.00 GiB  raw
    104:scsi0        1.00 TiB  raw
  san-c  used 512.00 GiB/8.00 TiB  reserve OK  (largest disk 512.00 GiB, requires 1.00 TiB free)
    105:scsi0      512.00 GiB  raw

Note: per-disk I/O load is not yet computed -- loadmodel.py (IMPLEMENTATION_PLAN.md
section 12 phase 3) is not implemented yet; sizes and reserve status above are accurate.
```

A pinned disk carries `[pinned: <reason>]` after its size and format —
`snapshots present (N)`, `locked: <lock>`, `excluded by config`, or
`excluded: unused disk (exclude.include_unused_disks=false)`, matching
`IMPLEMENTATION_PLAN.md` section 5.3 (C2) exactly; that reason is the
answer to "why won't it move this disk."

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
(including the exact byte counts behind the reserve check) and
`groups[].disks[]`, plus `"load_computed": false`.

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
