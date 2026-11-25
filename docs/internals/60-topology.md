# Building the disk/storage/group model

**What does this page answer?** How does `topology.py` turn `pve.py`'s raw
API responses into the per-group `D`/`S` sets? Where does each
`IMPLEMENTATION_PLAN.md` section 5.3 (C2) pin condition get decided? This
page describes `proxmox_storage_drs/topology.py` and
`proxmox_storage_drs/reserve.py`.

## `D` means every disk this module places, pinned or not

`topology.py`'s own docstring states this first, because this is the
single easiest thing to get backwards. `D` (section 5.1) is *every* disk
this module puts into a group's `Group.disks`. This holds whether or not
**(C2)** pins the disk's placement. (C2) is the plan's per-disk
eligibility constraint. A pinned disk is still a full member of `D`. Its
bytes and its I/O still count. The disk is simply excluded from ever being
*reassigned*. The "Pin priority" section below lists every condition that
triggers the pin.

A disk this module never sees at all is what "foreign" (`Uˢᵉˣᵗ`, section
5.1.1) means. A stopped VM never enters the model. The tool never
considers or moves its disks. A disk whose current storage is not in any
configured group is foreign too.

Config-excluded disks (`exclude.vmids`/`exclude.disks`/tags) are *not*
foreign. (C2) pins them into `D`. The reason: their bytes still count
toward a storage's reserve check. That check is **(C4)/(C5)**. `Z_s` is
the largest per-VM *footprint* on a storage. It is the sum of all of one
VM's disks on that storage, since a snapshot covers every disk of the VM
at once. `Z_s` sets a reserve floor `R_s = max(reserve_factor_s · Z_s,
soft_s)`. That floor must stay free on top of every disk's actual usage
there. `soft_s` is section 5.3.1's configured free-space requirement. This
module resolves it per storage onto `Storage.free_space_soft_bytes` below.
The exact shortfall arithmetic is in "`reserve.py`: one (C4)/(C5)
evaluator, shared" below. The excluded bytes also count toward **`κ`**,
the objective's per-VM fragmentation penalty. It charges a VM for every
extra storage its disks are spread across (section 5.4; see `90-heuristic.md`)
(section 3.6, "Pinned disks are modelled, not ignored").

An earlier draft of section 5.1.1 listed config-excluded disks as foreign.
That contradicted (C2) directly. The same commit that first implemented
this join found and fixed the contradiction. See that section's note for
the history.

## One pass, in the order section 3.5 lists

`build_topology()` fetches everything it needs exactly once. The fetch
runs in six stages: `_fetch_cluster_data`, a concurrent per-VM fetch phase
(`_fetch_vm()`) over `client.vm_resources()`, a concurrent per-`(node,
storage)` content-fetch phase, the single-threaded join
(`_join_vm_disks()`) that consumes both, and finally `_build_storages`:

1. The module fetches `storage_definitions()` (the list form, see
   `50-pve-api.md`). Every `/…/` storage pattern (section 11.4, below) is
   matched against this list. The module then expands and validates the
   configured `groups` against it (`_expand_and_validate_groups`). A
   literal storage that does not exist is a fatal `TopologyError`
   (section 11.1: "storage ids exist in the cluster"). A literal storage
   that lacks `images` in its content types is a fatal `TopologyError`
   too. A storage that exists but is not marked `shared` is a warning, not
   a fatal error. That state is plausible, if unusual, for a single-node
   group.
2. The module fetches `storage_resources()` once. This picks one active
   node per storage (`_pick_active_node`, preferring one reporting
   `status: "available"`).
3. The module fetches `storage_content()` and `storage_status()` per
   group storage.
4. The module fetches `vm_config()`, `vm_snapshots()` and `vm_pending()`
   per considered VM. A stopped VM is *not* fetched at all
   (`exclude.stopped: false` is refused at load). That is the one case
   `cluster/resources`'s own fields can decide without a config fetch. The
   module fetches every other VM, including config-excluded ones. It can
   tell whether a specific disk is "ungrouped" only after it sees which
   storage the disk is on. A config-excluded VM's disk still needs its
   size for (C4)/(C5) (previous section).

   This is the one step that runs across a bounded thread pool
   (`config.proxmox.read_workers`, REVIEW.md P-02). Section 3.5 makes the
   point: `GET .../qemu/{vmid}/config` has no batch form. For a
   several-hundred-VM cluster, this is the read phase concurrency actually
   helps. The step splits into `_fetch_vm()` (network I/O only, run by the
   pool, one call per considered VM) and `_join_vm_disks()`. The latter is
   pure. It is the same function the old sequential
   `_collect_vm_disks()` was renamed from, unchanged in what it computes.
   `ThreadPoolExecutor.map()` returns each VM's fetch in the same order
   `client.vm_resources()` listed it. The fetches themselves complete in
   whatever order the pool schedules them. The join phase runs
   single-threaded, in the original order. `disks_by_group`,
   `referenced_volids` and `warnings` end up byte-for-byte identical to a
   fully sequential run. This holds regardless of `read_workers` or of
   thread scheduling. The join never needs a lock. `PveClient` itself may
   reauthenticate mid-fetch if several threads hit an expired ticket at
   once (`50-pve-api.md`'s P-01 note). The client's own lock serializes
   that reauthentication, not this join.
5. The module fetches `storage_content()` again, per `(node, storage)`
   pair. `_needed_content_node_pairs()` finds those pairs among the
   just-fetched VMs' own disks. Step 3's single per-storage fetch does not
   already cover them. See "Sizes" below for why the tool runs a second
   per-node fetch on its own concurrent pool pass, rather than reusing
   step 3's listing for everything. The step runs the same
   `ThreadPoolExecutor(read_workers)` pattern as step 4, between step 4
   and the join. The step is bounded by distinct `(node, storage)` pairs,
   not by VM count (REVIEW.md W-05). The worst case (VMs spread across
   every node, disks on every managed storage) adds `|nodes| · |storages|`
   full content listings. A typical cluster's VM placement is far more
   concentrated than that. `IMPLEMENTATION_PLAN.md` §3.5's expected
   call-count formula carries the `|extra content pairs|` term for this.
6. The tool skips non-QEMU resources (`type != "qemu"`) outright. This
   tool never touches LXC containers. Section 3.5's read/write paths are
   qemu-only throughout.

## The `lock` field comes from `vm_config()`, not a separate call

Section 9.3's own pseudocode says `lock` is readable from either
`/qemu/{vmid}/config` or `/status/current`. `_join_vm_disks` reads `lock`
from the config response already fetched for the disk join. Planning-time
lock detection costs no extra API call. The tool needs `/status/current`
later, but only immediately before a specific move. That is section 9.2's
pre-move re-validation, `execute.py`'s `_preflight()` (see
`92-execute.md`). This module never makes that call.

## Pin priority: `_pin_reason()`

`_pin_reason()` checks each disk in the fixed order section 5.3 (C2) lists its
conditions. The first condition is config exclusion (VM-level, then
`exclude.disks`). The second is a real snapshot or an unreferenced companion
volume (section 3.7). `_disk_snapshot_or_orphan_reason` handles it.
`GET .../snapshot` always returns a `"current"` entry. A live cluster
confirmed this. The function filters that entry out before counting. For an
unreferenced volume, the reason names the volume as `storage:volume`. It lists
the first two sorted, plus a count of the rest. The reason names the volume
because the volume appears nowhere else the operator looks. The third
condition is an unapplied pending config change (section 3.8, below). The
fourth is the per-disk cooldown (below). The fifth is a VM lock. The sixth is
an `unusedN` disk, when `exclude.include_unused_disks` is false. A disk gets
at most one reason. The first reason that applies wins. This matches how an
operator would explain it.

The module applies one more pin afterwards, per group rather than per
disk. The pin depends on the VM's *other* disks in the group.
`pin_lone_small_disks()` pins every still-movable disk below
`migration.tiny_disk_bytes`. The VM must have no larger disk in that
group. The reason is `LONE_SMALL_DISK_REASON`. This is section 5.3
(C8)'s degenerate case, made visible as a pin. A small disk may only move
to where a larger disk of its VM ends up. Here, no larger disk exists. The
rule lives beside the pin. `is_small_disk()` tests one disk.
`larger_vm_disks()` returns the VM's non-small disks *in this group*,
pinned included. Disks of the same VM in another group never anchor
anything. Nothing moves between groups. `small_disk_placement_ok()` checks
one disk. `small_disks_follow_their_vm()` checks a whole assignment in a
single pass. Both solvers use these functions (`docs/internals/90-heuristic.md`,
`91-optimize.md`).

## The pending-change pin

A real cluster confirmed this: `GET .../qemu/{vmid}/config`
(`vm_config()`) returns a key's **pending** value once one exists. It does
not return the value actually in effect. Only `GET .../qemu/{vmid}/pending`
(`vm_pending()`) exposes both. `_fetch_vm()` fetches it alongside
`vm_config()`/`vm_snapshots()` for every considered VM.
`pending_disk_reasons()` reduces it to `device -> reason`. It covers
exactly the disk keys (matching `DISK_KEY_RE`) that carry a `"pending"`
field (an edit) or a truthy `"delete"` field (a queued removal). The
function is public, unlike its sibling helpers here. See below for the
reason. `_join_vm_disks()` computes this dict once per VM. It does so the
same way it already does for `snapshot_reason`. The join passes each
disk's own entry into `_pin_reason()`.

Why does the pin exist? `move_disk` acts on a disk's *current* volume.
PVE does not reconcile that disk's `pending` entry as a side effect of the
move. The entry keeps describing a change relative to how the disk looked
before it moved. A move in this state would leave a config key that is
wrong the moment the operator's next reboot applies it. Section 3.8 has
the full reasoning and the live-cluster confirmation.

`pending_disk_reasons()` is exported (not underscore-prefixed) for one
reason: `execute.py`'s `_preflight()` calls the identical parsing
immediately before issuing a move (section 9.2 step 6, `92-execute.md`).
This keeps one implementation, per `AGENTS.md` section 5. A second
`/pending` parser could silently classify an entry differently.

## The per-disk cooldown pin

`build_topology()` takes an optional `state: state.State` and `now:
datetime`. Both default to "no cooldowns"/the real clock (see
`docs/internals/15-state.md`). The function computes
`state.active_disk_cooldowns()` once per group, before the per-VM join
loop. It stores the result in `cooldowns_by_group: dict[str, dict[str,
float]]`. The value maps bare `vmid:device` to seconds remaining. Inside
the loop, once a disk's `group_name` is known, the function reads
`cooldowns_by_group[group_name].get(key, 0.0)`. It passes that value to
`_pin_reason()` as `cooldown_remaining_seconds`. The value is a plain
float, not a second `State` lookup inside that function. This keeps
`_pin_reason()` a pure decision over already-resolved flags. That is
exactly how it checks every other condition. The reported reason names how
much of `gates.cooldown_per_disk` remains: `cooldown: moved recently, 1.0h
left on gates.cooldown_per_disk`.

This pin is **not** exempted when the disk's storage actively violates
(C4)/(C5). See `docs/internals/15-state.md`'s "Deliberately not
implemented" section. It explains why, and why that gap is bounded and
safe rather than silently wrong.

## Sizes: content is authoritative, config is the fallback of last resort

`_resolve_disk_size_and_format` looks up the volume in a content listing
first. Section 3.5 marks the listing authoritative for what is actually
allocated. The lookup runs in three tiers. Tier one is the entry's own
`size`, if present. Tier two is the entry's `approximate-size`, if `size`
is not present. Tier three is the VM config's own `size=`. The module uses
tier three only when the entry has neither field, or is missing from the
listing entirely. It logs a warning that names the disk and which of the
two content-listing gaps applied.

Two independently verified reasons explain why the config fallback is not
merely defensive. The first is the `Datastore.Allocate`-vs-`Audit`
privilege gap (`50-pve-api.md`). The second is an `unusedN` volume,
deleted directly on the storage backend outside Proxmox. The cluster's
operator confirmed this. PVE's own config still referenced that volume.
PVE itself never noticed. It never refused to boot the VM over it. See
`IMPLEMENTATION_PLAN.md` section 3.6's note.

`_build_storages` sums *foreign* (unreferenced) volumes the same way. The
sum uses the same `size`/`approximate-size` tiering. It has no VM config
to fall back to for a size at all. When neither field is present, the
module skips the volume. It logs a warning and undercounts the reserve.
`_parse_pve_config_size_bytes` parses PVE's own config-file size suffixes.
`512G` means binary GiB, with no explicit `i`. The module uses its own
parser on purpose. `units.py`'s parser is for *this project's* config
file. That format is different, and only by coincidence similarly shaped.

**The choice of the node for the content listing matters.** The operator who
hit this confirmed the behavior live. PVE 9.2 supports qcow2-on-shared-LVM
snapshots. Because of that support, `size` for one of these volumes is
readable only from the node that has its LV *active*. The read is cheap on the
node currently running the owning VM. PVE keeps the LV active there. The read
is expensive, or blocked entirely, on a shared storage's other nodes. Those
nodes report `approximate-size` instead. That value is PVE's own answer from
LVM metadata, without activating anything. `_pick_active_node()` picks one
node per *storage*. That is the node every other section 3.5 call uses. The
pick is not guaranteed to be the node with the active LV. The module resolves
a managed disk's size/format against a content listing fetched from **that
disk's own VM's node** specifically. It uses `_needed_content_node_pairs()`
(step 5 above), not `_pick_active_node()`'s pick. Only the *foreign*-volume
sum in `_build_storages` still uses the storage-wide listing. An unreferenced
volume has no owning VM to pick a node from. Before this fix, a disk on this
kind of storage could silently carry the storage's generic pick's
`approximate-size`. It could fall further, to a possibly-stale VM config
`size=`. The exact figure was one call away.

## `Uˢᵉˣᵗ`: everything not referenced

Every disk placed into a group's `D` records its volid in
`referenced_volids[storage_id]` as the module processes it.
`_build_storages` then sums the size of every content entry on that storage
whose volid was never referenced. Orphans, templates, other groups'
foreign volumes, and disks of VMs this run never fetched
(stopped-and-excluded, or ungrouped) all fall out of this one computation.
No special-casing per category is needed. This matches section 5.1.1's
definition read literally.

## Section 11.4: `/…/` storage patterns are expanded here, once

`groups[].storages[].id` may be a `/…/` pattern instead of a literal id.
The expansion happens inside `_fetch_cluster_data`. It runs right after
`storage_definitions()` *and* `storage_resources()` both return. The
module moved the `storage_resources()` fetch ahead of everything else that
used to follow it (REVIEW.md U-01). The reason: expansion checks a pattern
match against that list. Expansion is the one thing that runs *before* the
ordinary literal-id validation described above. `_expand_group()` matches
every pattern entry in a group against the sorted list of the cluster's
storage ids. It uses `re.fullmatch`. The match is whole-id and
case-sensitive: `/prod/` must not also catch `preprod`. The function then
folds in the group's literal entries on top. A literal always overwrites
whatever a pattern matched for that same id. The overwrite is a plain
`dict` assignment. Precedence is a dict overwrite, not a positional rule.
Entry order in the file never matters.

`_match_pattern_entries` checks three things a pattern can get wrong. The
checks run right there, before anything downstream sees the result. A pattern
matching zero storages is a `TopologyError`. Section 11.1 already gives that
treatment to a literal id that does not exist. A typo is the likelier cause. A
matched storage may have a `GET /storage` definition but be reported active by
no node. That is the shape of a disabled storage. The check is fatal and names
the pattern and the storage. A literal reference to such a storage already hit
the same condition in `_pick_active_node` (REVIEW.md U-01), with a worse
message. That call sits three steps downstream of expansion. It has no way to
know a pattern was involved. The check here tells the operator which pattern
is responsible. Two *different* patterns in the same group matching the same
storage is also fatal (`claimed_by`). The tool could not decide which entry's
options should apply. That choice would be arbitrary. A fourth check,
`_check_cross_group_uniqueness`, runs once every group is expanded. It catches
a pattern in one group and a literal (or another pattern) in a different group
that match the same real storage. `config._check_group_storage_membership`
cannot see that case at load time. It only compares two groups' raw entry
*text*. `"san-a"` and `"/san-.*/"` are different text, even when they resolve
to the same storage.

One deliberate asymmetry remains. Section 11.4's own closing paragraph
calls it out explicitly. A pattern-matched storage does **not** get the
literal path's "must have `images` in its content list" check. An operator
who names a storage explicitly gets a hard error for a typo. A pattern that
picks up an ISO-only or otherwise unusable LUN is a balance-quality
concern, not a safety one. (C2) still keeps any disk from ever landing
there. `u* = L_s / c_s` (section 4) simply divides by one more `c_s` than
intended. The not-`shared` warning is *not* a second such asymmetry. An
earlier draft left it literal-only (REVIEW.md U-03). The module computes
the warning once, after expansion. It applies uniformly over every final
member of the group. This holds regardless of whether a literal or a
pattern named the storage. A warning carries no typo-safety rationale for
staying quiet. The content check does.

The module logs every pattern's expansion at INFO. It logs the raw entry
and the ids it matched. The call is
`logger.info(..., extra={"event": "storage_pattern_expanded", ...})`. The
expansion is carried on `Topology.pattern_expansions` for `cli.py`'s
`verify-storages` to print (section 3.5). The module computes
`Topology.unmanaged_storage_ids` once, right after `groups`. The value is
every cluster storage id `storage_definitions()` returned, minus every id
`storage_group_of` resolved to. This is the storage-level twin of the
per-disk "ungrouped, not managed" warning `_join_vm_disks` already emits.
The value does not need a disk sitting on the storage to be visible.

By the time `_build_storages` runs, `data.expanded_by_group[group.name]`
holds real storage ids only. The function iterates that list, not
`group_cfg.storages`. `Storage.id` and everything keyed off it
(`storage_group_of`, cooldown keys, `state.json`) never carries pattern
text. Nothing past `_expand_and_validate_groups` knows a pattern was
involved. This holds in this module and in every module downstream of it.

## `reserve.py`: one (C4)/(C5) evaluator, shared

**The footprint.** A snapshot of a VM snapshots every disk of it at once.
What a snapshot of VM `v` needs on storage `s` is `F_{v,s} = Σ z_{d,s}`
over `v`'s disks *on `s`*. `Z_s = max_v F_{v,s}` (`vm_footprints_bytes()`,
`largest_footprint()`). Every disk in `D` counts, movable or pinned. Only
`s` itself is summed. The room on the VM's *other* storages is those
storages' own footprint. Foreign volumes and disks of stopped VMs
contribute bytes to `used`, but no footprint. A stopped VM is planned
neither for snapshots nor for I/O. `ReserveStatus` carries `Z_s` as
`largest_footprint_bytes`. It also carries the VM the value comes from
(`largest_footprint_vmid`, lowest vmid on a tie). `show-load` names that
VM. The per-disk maximum (`largest_disk_bytes()`) survives for exactly one
purpose. It is the saferemove wipe-time estimate, which really is per
volume. `split_vm_caps()` and `split_excess_bytes()` derive `V^split`.
They also derive each VM's cap `T_v = max(T, largest disk)` and its excess
`o_v`. The excess is the peak footprint beyond the cap. These values serve
the large-VM split rule (`91-optimize.md`, `80-gates.md`).

`compute_reserve_status()` computes, for one storage: `used = Σ_{d∈D on s} z_d
+ Uˢᵉˣᵗ_s`. That is every managed disk's bytes plus the foreign/unreferenced
bytes from "`Uˢᵉˣᵗ`: everything not referenced" above. It computes
`shortfall = max(0, used + R_s − capacity_s)`. The module rounds the result
**up to the next whole MiB** (`round_up_to_mib()`). `ReserveStatus.violated`
is exactly `shortfall > 0`. The rounding does not change that, since only a
zero shortfall rounds to zero. Every consumer of a shortfall *difference*
needs to agree on the MiB granularity. The consumers are the heuristic's
repair step, the MILP's lexicographic stage 1 (whose `r_s` are integer MiB,
`docs/internals/91-optimize.md`), and payback's repair exemption and
revert test (`docs/internals/96-payback.md`). They all compare these sums.
At byte resolution, they disagreed about sub-MiB noise. Rounding *up*
overstates a real shortfall by under a MiB. It never hides one.
`ReserveStatus.violated` is the boolean `gates.py`'s reserve-override gate
reads directly (`docs/internals/80-gates.md`). The evaluator is
deliberately its own module, not a method on `Storage`. `heuristic.py`
needs to evaluate the identical formula against a *candidate* assignment,
not only the current one. `storage_of=` overrides which storage each disk
is treated as sitting on. `pve-storage-drs show-load`'s reporting needs
the same formula against the current assignment today. Both call the same
function (AGENTS.md section 5). `show-load`'s use of it is already
exercised end-to-end (see `cli.py`'s `_render_show_load_human`/`_json`).
`optimize.py`'s MILP path needs the same (C4)/(C5) invariant. It cannot
call a Python function from inside a solver's constraint system. See
`91-optimize.md` for how it encodes the equivalent bound directly as scaled
linear constraints (one per VM and storage) instead. The section 14 worked
example's initial state (`tests/unit/test_reserve.py`) proves this
reproduces the plan's own arithmetic exactly. It is not merely a
self-consistent unit test.

## `free_space` resolution: `soft_s`/`hard_s`, resolved once, here

`_build_storages()` resolves section 5.3.1's `soft_s`/`hard_s` pair onto
`Storage.free_space_soft_bytes`/`.free_space_hard_bytes`.
`_resolve_free_space()` does the work. It uses the same place and the same
per-storage pattern `_resolve_reserve_factor()` already uses for
`reserve_factor`. The reason is the same: a `/…/` pattern's `free_space` entry
applies to every storage it matches. A literal entry overrides it. Only a real
storage's `capacity_bytes` can resolve a percentage. That value is known
here, not in `config.py`. The mandated order is inheritance. Then
percent-to-bytes conversion. Then the two section 11.1 hard rules against the
resolved values (`hard_s <= soft_s`, `soft_s < C_s`). Both rules raise
`TopologyError`. They behave exactly like the pattern-expansion rules above.
Both rules need the cluster inventory that `config.py` never has. A *null*
`hard` means `hard_s = soft_s`. `_resolve_free_space()` returns a
`ResolvedFreeSpace`. The value is the pair plus two display-only strings.
Each string names the level its half came from (global, storage entry,
`pattern /re/`, percent-converted). The strings are carried on
`Storage.free_space_soft_source`/`_hard_source` for `verify-storages`.
Nothing else reads them. By the time `compute_reserve_status()` reads
`storage.free_space_soft_bytes`, both values are plain, already-resolved byte
constants. The same holds when `schedule.transient_invariant_ok()` reads
`.free_space_hard_bytes`. Section 5.3.1's own grammar (percentages, patterns)
is never seen again past this module.

## (C2) format eligibility: `storage_type`/`allowed_formats`

`Storage` also carries `storage_type`. The value comes from `GET /storage`'s
own `type` field, never guessed. `Storage` also carries `allowed_formats`.
These are the disk formats that type can actually hold. The formats come
from a fixed table. The table is keyed by the same storage-type partition
`_default_format()` already draws. `_default_format()` picks the fallback
format for a content listing with no `format` field of its own. A
block-backed type (`lvmthin`, `zfspool`, `rbd`, `iscsi`, `iscsidirect`)
holds `raw` only. There is no image container on the array. A volume *is*
the raw block device. A file-backed type (`dir`, `nfs`, `cifs`, `cephfs`)
holds whatever `qemu-img` formats PVE offers a regular file for. Ordinary
(non-thin) `lvm` is the one block-backed exception. Current PVE versions
also accept `qcow2` there. PVE 9.2 added snapshot support on plain LVM.
PVE formats the LV itself as a qcow2 image rather than using it raw. The
mechanism is the same one `_resolve_disk_size_and_format()`'s
`approximate-size` note above describes. `lvmthin` needs no such carve-out.
Its snapshots are native LVM-thin COW, never qcow2-on-the-LV.

Section 5.3 (C2)'s "`s` cannot hold the disk's format" is
`topology.storage_accepts_format(storage, disk.format)`. Both MILP backends
call this one function (`91-optimize.md`). So do `heuristic.py`'s own
candidate-generating helpers. They fix `x_{d,s}=0` (or exclude the pair
from the neighbourhood the heuristic searches) for every ineligible target.
Unlike the free-space floor, format eligibility needs no per-run
resolution step of its own. It is a pure function of `storage_type`. The
module computes it once when `Storage` is built. Every later reader reads
it directly.

### `enforce_format`: `target_format()` and `disk_size_on()`

A storage entry may name the format every disk moved onto it arrives in.
The key is `groups[].storages[].enforce_format`. The value is `raw`,
`qcow2` or unset (plan section 5.3.2). `Storage.enforce_format` carries the
resolved value. `_match_pattern_entries` copies a pattern entry's value to
each storage it matches. A literal entry replaces the value wholesale, like
every per-storage option. `enforce_format_source` says which entry the
value came from, for `verify-storages`. `_expand_group` refuses a value the
storage's type cannot hold. One example is `qcow2` on an RBD, ZFS or
LVM-thin storage. It raises a `TopologyError` naming the storage.

Two functions implement the two questions enforcement adds.
`target_format(disk, storage)` is the plan's `phi(d,s)`. It returns the
storage's `enforce_format` for a disk that is *not* already on that
storage. For a disk already on the storage, it returns the disk's own
format. A `tpmstate0` always keeps its own format. (C2)'s eligibility is
then `storage_accepts_format(s, target_format(d, s))` at every call site.
The call sites are the two solver backends, the heuristic's candidate
generators and the executor. Enforcement can only widen what a storage
accepts.

`disk_size_on(disk, storage)` is `z_{d,s}`. It returns `Disk.size_bytes`,
unless the move changes the format. When the format changes, PVE allocates
a fresh volume. The charge is then `max(size_bytes, config_size_bytes)`.
`Disk.config_size_bytes` is the disk line's `size=`, 0 when absent. A
`qcow2` volume landing on an `lvm` storage is charged at least
`qcow2_lvm_allocation_bytes()`. The value is an upper bound on what PVE's
`LVMPlugin::alloc_image` creates. PVE sizes the LV from `qemu-img
measure`'s `fully-allocated` figure. That is the virtual size plus the
image's own metadata. The metadata is about 0.015 % with the default 64
KiB clusters. The charge is `size + size/4096 + 8 MiB`, never below the
real value. `reserve.py`, `schedule.py` and both solver backends read sizes
through `disk_size_on`. (C4), (C5), (C7) and the transient check agree.
The group mean fill `b_bar` and the move-cost terms deliberately stay at
`size_bytes`. They are targets and prices, not constraints. With no
`enforce_format` anywhere, `disk_size_on` is `size_bytes`. Every earlier
plan is unchanged.
