# Building the disk/storage/group model

**What does this page answer?** How does `topology.py` turn `pve.py`'s raw
API responses into the per-group `D`/`S` sets the rest of the engine needs,
and where does each `IMPLEMENTATION_PLAN.md` section 5.3 (C2) pin condition
actually get decided? Describes `proxmox_storage_drs/topology.py` and
`proxmox_storage_drs/reserve.py`.

## `D` means every disk this module places, pinned or not

This is stated at the top of `topology.py`'s own docstring because it is
the single easiest thing to get backwards: `D` (section 5.1) is *every*
disk this module puts into a group's `Group.disks`, whether or not (C2)
pins its placement. A disk this module never sees at all — a stopped VM
excluded by `exclude.running_only`, or a disk whose current storage is not
in any configured group — is what "foreign" (`Uˢᵉˣᵗ`, section 5.1.1) means.
Config-excluded disks (`exclude.vmids`/`exclude.disks`/tags) are *not*
foreign: (C2) pins them into `D` specifically so their bytes still count in
(C4)/(C5) and their fragmentation toward `κ` (section 3.6, "Pinned disks are
modelled, not ignored"). An earlier draft of section 5.1.1 listed config-excluded
disks as foreign, which directly contradicted (C2) — that self-contradiction
was found and fixed in the same commit that first implemented this join;
see that section's note if you need the history.

## One pass, in the order section 3.5 lists

`build_topology()` fetches everything it needs exactly once, in five
stages (`_fetch_cluster_data`, then a loop over `client.vm_resources()`
calling `_collect_vm_disks` per VM, then `_build_storages`):

1. `storage_definitions()` (the list form — see `50-pve-api.md`), which is
   also what every `/…/` storage pattern (section 11.4, below) is matched
   against, then the configured `groups` are expanded and validated against
   it (`_expand_and_validate_groups`): a literal storage that does not
   exist, or that lacks `images` in its content types, is a fatal
   `TopologyError` (section 11.1: "storage ids exist in the cluster"). A
   storage that exists but is not marked `shared` is a warning, not a fatal
   error — plausible, if unusual, for a single-node group.
2. `storage_resources()` once, to pick one active node per storage
   (`_pick_active_node`, preferring one reporting `status: "available"`).
3. `storage_content()` and `storage_status()` per group storage.
4. `vm_config()` and `vm_snapshots()` per considered VM. A VM is *not*
   fetched at all when `exclude.running_only` is set and it is stopped —
   the one case `cluster/resources`'s own fields can decide without a
   config fetch. Every other VM is fetched, including config-excluded ones:
   whether a specific disk turns out to be "ungrouped" is only knowable
   after seeing which storage it is actually on, and a config-excluded
   VM's disk still needs its size for (C4)/(C5) (previous section).

   This is the one step that runs across a bounded thread pool
   (`config.proxmox.read_workers`, REVIEW.md P-02): section 3.5's whole
   point is that `GET .../qemu/{vmid}/config` has no batch form, so for a
   several-hundred-VM cluster this is the read phase concurrency actually
   helps. It is split into `_fetch_vm()` (network I/O only, run by the
   pool, one call per considered VM) and `_join_vm_disks()` (pure —
   the same function the old sequential `_collect_vm_disks()` was renamed
   from, unchanged in what it computes). `ThreadPoolExecutor.map()`
   returns each VM's fetch in the same order `client.vm_resources()`
   listed it, even though the fetches themselves complete in whatever order
   the pool schedules them, so the join phase runs single-threaded and in
   the original order — `disks_by_group`, `referenced_volids` and
   `warnings` end up byte-for-byte identical to a fully sequential run
   regardless of `read_workers` or of thread scheduling, and never need a
   lock. `PveClient` itself may reauthenticate mid-fetch if several threads
   hit an expired ticket at once (`50-pve-api.md`'s P-01 note); that
   reauthentication is what its own lock serializes, not this join.
5. Non-QEMU resources (`type != "qemu"`) are skipped outright — this tool
   never touches LXC containers, and section 3.5's read/write paths are
   qemu-only throughout.

## The `lock` field comes from `vm_config()`, not a separate call

Section 9.3's own pseudocode says `lock` is readable from either
`/qemu/{vmid}/config` or `/status/current`. `_collect_vm_disks` reads it
from the config response already being fetched for the disk join, so
planning-time lock detection costs no extra API call. `/status/current` is
still needed later, but only immediately before a specific move (section
9.2's pre-move re-validation, `execute.py`, not yet written) — never here.

## Pin priority: `_pin_reason()`

One function, checked in the fixed order section 5.3 (C2) lists its
conditions: config exclusion (VM-level, then `exclude.disks`), a real
snapshot or an unreferenced companion volume (section 3.7,
`_disk_snapshot_or_orphan_reason` — the `"current"` entry `GET
.../snapshot` always returns, verified on a live cluster, is filtered out
before counting), the per-disk cooldown (below), a VM lock, then an
`unusedN` disk when `exclude.include_unused_disks` is false. A disk gets
at most one reason; the first that applies wins, matching how an operator
would explain it.

## The per-disk cooldown pin

`build_topology()` takes an optional `state: state.State` and `now:
datetime` (both default to "no cooldowns"/the real clock — see
`docs/internals/15-state.md`) and computes
`state.active_disk_cooldowns()` once per group, before the per-VM join
loop, into `cooldowns_by_group: dict[str, dict[str, float]]` (bare
`vmid:device` -> seconds remaining). Inside the loop, once a disk's
`group_name` is known, `cooldowns_by_group[group_name].get(key, 0.0)` is
passed to `_pin_reason()` as `cooldown_remaining_seconds` — a plain float,
not a second `State` lookup inside that function, keeping `_pin_reason()`
a pure decision over already-resolved flags exactly like every other
condition it checks. The reported reason names how much of
`gates.cooldown_per_disk` remains: `cooldown: moved recently, 1.0h left on
gates.cooldown_per_disk`.

This pin is **not** exempted when the disk's storage is actively
violating (C4)/(C5) — see `docs/internals/15-state.md`'s "Deliberately not
implemented" section for why, and why that gap is bounded and safe rather
than silently wrong.

## Sizes: content is authoritative, config is the fallback

`_resolve_disk_size_and_format` looks up the volume in that storage's
content listing first (section 3.5: authoritative for what is actually
allocated) and falls back to parsing the VM config's own `size=` only when
the volume is missing from content — logged as a warning naming the
disk, since assume-thick-provisioning sizing from a stale or unlisted
config value is a real, if rare, source of drift. Two independently
verified reasons this fallback path is not merely defensive: the
`Datastore.Allocate`-vs-`Audit` privilege gap (`50-pve-api.md`), and an
`unusedN` volume, deleted directly on the storage backend outside Proxmox
(confirmed with the cluster's operator), that PVE's own config still
referenced and that PVE itself never noticed or refused to boot the VM
over — `IMPLEMENTATION_PLAN.md` section 3.6's note. `_parse_pve_config_size_bytes` parses PVE's own config-file
size suffixes (`512G` meaning binary GiB, no explicit `i`) — deliberately
not `units.py`'s parser, which is for *this project's* config file, a
different and coincidentally similarly-shaped format.

## `Uˢᵉˣᵗ`: everything not referenced

Every disk actually placed into a group's `D` records its volid in
`referenced_volids[storage_id]` as it is processed. `_build_storages` then
sums the size of every content entry on that storage whose volid was never
referenced — orphans, templates, other groups' foreign volumes, and disks
of VMs this run never fetched (stopped-and-excluded, or ungrouped) all fall
out of this one computation with no special-casing per category, which is
exactly section 5.1.1's definition read literally.

## Section 11.4: `/…/` storage patterns are expanded here, once

`groups[].storages[].id` may be a `/…/` pattern instead of a literal id.
Expansion happens inside `_fetch_cluster_data`, right after
`storage_definitions()` returns, and is the one thing that runs *before*
the ordinary literal-id validation described above -- `_expand_group()`
matches every pattern entry in a group against the sorted list of the
cluster's storage ids with `re.fullmatch` (whole-id, case-sensitive: `/prod/`
must not also catch `preprod`), then folds in the group's literal entries
on top, a literal always overwriting whatever a pattern matched for that
same id in a plain `dict` assignment -- precedence is a dict overwrite, not
a positional rule, so entry order in the file never matters.

Two things a pattern can get wrong are checked right there, before
anything downstream sees the result: a pattern matching zero storages is a
`TopologyError` (`_match_pattern_entries`, same treatment section 11.1
already gives a literal id that doesn't exist -- a typo is the likelier
cause), and two *different* patterns in the same group matching the same
storage is also fatal (`claimed_by` in `_match_pattern_entries`) -- which
entry's options should apply would be arbitrary. A third check,
`_check_cross_group_uniqueness`, runs once every group has been expanded:
it is what catches a pattern in one group and a literal (or another
pattern) in a different group matching the same real storage --
`config._check_group_storage_membership` cannot see that case at load time
because it only ever compares two groups' raw entry *text*, and `"san-a"`
and `"/san-.*/"` are different text even when they'd resolve to the same
storage.

One deliberate asymmetry: a pattern-matched storage does **not** get the
literal path's "must have `images` in its content list" check. An operator
who names a storage explicitly gets a hard error for a typo; a pattern that
happens to pick up an ISO-only or otherwise unusable LUN is a
balance-quality concern, not a safety one -- (C2) still keeps any disk from
ever landing there, and `u* = L_s / c_s` (section 4) simply divides by one
more `c_s` than intended. This is called out explicitly in section 11.4's
own closing paragraph, not an oversight here.

Every pattern's expansion -- the raw entry and the ids it matched -- is
logged at INFO (`logger.info(..., extra={"event": "storage_pattern_expanded", ...})`)
and carried on `Topology.pattern_expansions` for `cli.py`'s
`verify-storages` to print (section 3.5). `Topology.unmanaged_storage_ids`
is computed once, right after `groups` -- every cluster storage id
`storage_definitions()` returned minus every id `storage_group_of` resolved
to -- and is the storage-level twin of the per-disk "ungrouped, not
managed" warning `_join_vm_disks` already emits: it does not need a disk to
actually be sitting on the storage to be visible.

By the time `_build_storages` runs, `data.expanded_by_group[group.name]`
holds real storage ids only -- it iterates that, not `group_cfg.storages`,
so `Storage.id` and everything keyed off it (`storage_group_of`, cooldown
keys, `state.json`) never carries pattern text. Nothing past
`_expand_and_validate_groups` in this module, or in any module downstream
of it, needs to know a pattern was ever involved.

## `reserve.py`: one (C4)/(C5) evaluator, shared

`compute_reserve_status()` is deliberately its own module, not a method on
`Storage`: the solver (`optimize.py`/`heuristic.py`, not yet written) will
need to evaluate the identical formula against a *candidate* assignment,
not only the current one, and `pve-storage-drs show-load`'s reporting needs
it against the current assignment today. Both call the same function
(AGENTS.md section 5) — `show-load`'s use of it is already exercised
end-to-end (see `cli.py`'s `_render_show_load_human`/`_json`). The section
14 worked example's initial state (`tests/unit/test_reserve.py`) is the
proof this reproduces the plan's own arithmetic exactly, not merely a
self-consistent unit test.
