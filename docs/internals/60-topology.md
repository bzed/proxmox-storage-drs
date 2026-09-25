# Building the disk/storage/group model

**What does this page answer?** How does `topology.py` turn `pve.py`'s raw
API responses into the per-group `D`/`S` sets the rest of the engine needs,
and where does each `IMPLEMENTATION_PLAN.md` section 5.3 (C2) pin condition
actually get decided? Describes `proxmox_storage_drs/topology.py` and
`proxmox_storage_drs/reserve.py`.

## `D` means every disk this module places, pinned or not

This is stated at the top of `topology.py`'s own docstring because it is
the single easiest thing to get backwards: `D` (section 5.1) is *every*
disk this module puts into a group's `Group.disks`, whether or not **(C2)**
pins its placement. (C2) is the plan's per-disk eligibility constraint: a
pinned disk is still a full member of `D` — its bytes and its I/O still
count — it is simply excluded from ever being *reassigned*; the "Pin
priority" section below enumerates every condition that triggers it. A disk
this module never sees at all — a stopped VM excluded by
`exclude.running_only`, or a disk whose current storage is not in any
configured group — is what "foreign" (`Uˢᵉˣᵗ`, section 5.1.1) means.
Config-excluded disks (`exclude.vmids`/`exclude.disks`/tags) are *not*
foreign: (C2) pins them into `D` specifically so their bytes still count
toward a storage's reserve check — **(C4)/(C5)**: `Z_s`, the largest disk
resident on a storage, sets a reserve floor `R_s = max(reserve_factor_s ·
Z_s, soft_s)` that must stay free on top of every disk's actual usage
there (`soft_s` is section 5.3.1's configured free-space requirement,
resolved per storage onto `Storage.free_space_soft_bytes` below — the
exact shortfall arithmetic is in "`reserve.py`: one (C4)/(C5) evaluator,
shared" below) — and toward **`κ`**, the objective's
per-VM fragmentation penalty, which charges a VM for every extra storage
its disks are spread across (section 5.4; see `90-heuristic.md`) (section
3.6, "Pinned disks are modelled, not ignored"). An earlier draft of section
5.1.1 listed config-excluded disks as foreign, which directly contradicted
(C2) — that self-contradiction was found and fixed in the same commit that
first implemented this join; see that section's note if you need the
history.

## One pass, in the order section 3.5 lists

`build_topology()` fetches everything it needs exactly once, in six
stages: `_fetch_cluster_data`, a concurrent per-VM fetch phase
(`_fetch_vm()`) over `client.vm_resources()`, a concurrent per-`(node,
storage)` content-fetch phase, the single-threaded join
(`_join_vm_disks()`) that consumes both, and finally `_build_storages`:

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
4. `vm_config()`, `vm_snapshots()` and `vm_pending()` per considered VM. A VM is *not*
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
5. `storage_content()` again, per `(node, storage)` pair `_needed_content_node_pairs()`
   finds among the just-fetched VMs' own disks that step 3's single
   per-storage fetch does not already cover — see "Sizes" below for why a
   second per-node fetch is worth its own concurrent pool pass rather than
   reusing step 3's listing for everything. Runs the same
   `ThreadPoolExecutor(read_workers)` pattern as step 4, between it and the
   join. Bounded by distinct `(node, storage)` pairs, not by VM count
   (REVIEW.md W-05): worst case (VMs spread across every node, disks on
   every managed storage) is `|nodes| · |storages|` extra full content
   listings, though a typical cluster's VM placement is far more
   concentrated than that. `IMPLEMENTATION_PLAN.md` §3.5's expected
   call-count formula carries the `|extra content pairs|` term for this.
6. Non-QEMU resources (`type != "qemu"`) are skipped outright — this tool
   never touches LXC containers, and section 3.5's read/write paths are
   qemu-only throughout.

## The `lock` field comes from `vm_config()`, not a separate call

Section 9.3's own pseudocode says `lock` is readable from either
`/qemu/{vmid}/config` or `/status/current`. `_join_vm_disks` reads it
from the config response already being fetched for the disk join, so
planning-time lock detection costs no extra API call. `/status/current` is
still needed later, but only immediately before a specific move (section
9.2's pre-move re-validation, `execute.py`'s `_preflight()` — see
`92-execute.md`) — never here.

## Pin priority: `_pin_reason()`

One function, checked in the fixed order section 5.3 (C2) lists its
conditions: config exclusion (VM-level, then `exclude.disks`), a real
snapshot or an unreferenced companion volume (section 3.7,
`_disk_snapshot_or_orphan_reason` — the `"current"` entry `GET
.../snapshot` always returns, verified on a live cluster, is filtered out
before counting), an unapplied pending config change (section 3.8, below),
the per-disk cooldown (below), a VM lock, then an `unusedN` disk when
`exclude.include_unused_disks` is false. A disk gets at most one reason;
the first that applies wins, matching how an operator would explain it.

## The pending-change pin

`GET .../qemu/{vmid}/config` (`vm_config()`) is confirmed, against a real
cluster, to return a key's **pending** value once one exists — not the
value actually in effect. Only `GET .../qemu/{vmid}/pending`
(`vm_pending()`) exposes both, so `_fetch_vm()` fetches it alongside
`vm_config()`/`vm_snapshots()` for every considered VM, and
`pending_disk_reasons()` (public, unlike its sibling helpers here — see
below) reduces it to `device -> reason` for exactly the disk keys
(matching `DISK_KEY_RE`) that carry a `"pending"` field (an edit) or a
truthy `"delete"` field (a queued removal). `_join_vm_disks()` computes
this dict once per VM, the same way it already does for
`snapshot_reason`, and passes each disk's own entry into `_pin_reason()`.

Why this exists at all: `move_disk` acts on a disk's *current* volume, and
PVE does not reconcile that disk's `pending` entry as a side effect of the
move — the entry keeps describing a change relative to whatever the disk
looked like before it moved. Migrating a disk in this state would leave a
config key that is wrong the moment the operator's next reboot applies it.
Section 3.8 has the full reasoning and the live-cluster confirmation.

`pending_disk_reasons()` is exported (not underscore-prefixed) specifically
so `execute.py`'s `_preflight()` can call the identical parsing
immediately before issuing a move (section 9.2 step 6, `92-execute.md`) —
one implementation, per `AGENTS.md` section 5, rather than a second
`/pending` parser that could silently classify an entry differently from
this one.

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

## Sizes: content is authoritative, config is the fallback of last resort

`_resolve_disk_size_and_format` looks up the volume in a content listing
first (section 3.5: authoritative for what is actually allocated), in
three tiers: the entry's own `size` if present; its `approximate-size` if
`size` is not; the VM config's own `size=` (logged as a warning naming the
disk and which of the two content-listing gaps applied) only when the
entry has neither, or is missing from the listing entirely. Two
independently verified reasons the config fallback is not merely
defensive: the `Datastore.Allocate`-vs-`Audit` privilege gap
(`50-pve-api.md`), and an `unusedN` volume, deleted directly on the
storage backend outside Proxmox (confirmed with the cluster's operator),
that PVE's own config still referenced and that PVE itself never noticed
or refused to boot the VM over — `IMPLEMENTATION_PLAN.md` section 3.6's
note. `_build_storages`'s equivalent sum over *foreign* (unreferenced)
volumes uses the same `size`/`approximate-size` tiering, but has no VM
config to fall back to for a size at all — it skips the volume instead
(warning, undercounting the reserve) when neither is present.
`_parse_pve_config_size_bytes` parses PVE's own config-file size suffixes
(`512G` meaning binary GiB, no explicit `i`) — deliberately not
`units.py`'s parser, which is for *this project's* config file, a
different and coincidentally similarly-shaped format.

**Which node's content listing, though, is not a detail this function
gets to be careless about.** Confirmed live, by the operator who hit it:
PVE 9.2's qcow2-on-shared-LVM snapshot support means `size` for one of
these volumes is only readable from the node that has its LV *active* —
cheap on the node currently running the owning VM (PVE keeps it active
there), expensive or blocked entirely on a shared storage's other nodes,
which report `approximate-size` instead (PVE's own answer from LVM
metadata, without activating anything). `_pick_active_node()`'s one pick
per *storage* — the node every other section 3.5 call uses — is not
guaranteed to be that node. So a managed disk's size/format is resolved
against a content listing fetched from **that disk's own VM's node**
specifically (`_needed_content_node_pairs()`, step 5 above), not
`_pick_active_node()`'s pick; only the *foreign*-volume sum in
`_build_storages` still uses the storage-wide listing, since an
unreferenced volume has no owning VM to pick a node from. Before this
fix, a disk on this kind of storage could silently carry the storage's
generic pick's `approximate-size` (or fall further, to a possibly-stale
VM config `size=`) even when the exact figure was one call away.

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
`storage_definitions()` *and* `storage_resources()` both return -- the
latter's fetch was moved ahead of everything else that used to follow it
(REVIEW.md U-01) specifically so expansion can check a pattern match
against it -- and is the one thing that runs *before* the ordinary
literal-id validation described above. `_expand_group()` matches every
pattern entry in a group against the sorted list of the cluster's storage
ids with `re.fullmatch` (whole-id, case-sensitive: `/prod/` must not also
catch `preprod`), then folds in the group's literal entries on top, a
literal always overwriting whatever a pattern matched for that same id in
a plain `dict` assignment -- precedence is a dict overwrite, not a
positional rule, so entry order in the file never matters.

Three things a pattern can get wrong are checked right there, before
anything downstream sees the result, all in `_match_pattern_entries`: a
pattern matching zero storages is a `TopologyError` (same treatment
section 11.1 already gives a literal id that doesn't exist -- a typo is
the likelier cause); a matched storage that has a `GET /storage`
definition but is reported active by no node -- the shape of a disabled
storage -- is also fatal, naming the pattern and the storage (REVIEW.md
U-01: a literal reference to such a storage already hit the same wall in
`_pick_active_node`, just with a worse message, since that call is three
steps downstream of expansion and has no way to know a pattern was ever
involved; catching it here instead means the operator is told which
pattern is responsible); and two *different* patterns in the same group
matching the same storage is fatal too (`claimed_by`) -- which entry's
options should apply would be arbitrary. A fourth check,
`_check_cross_group_uniqueness`, runs once every group has been expanded:
it is what catches a pattern in one group and a literal (or another
pattern) in a different group matching the same real storage --
`config._check_group_storage_membership` cannot see that case at load time
because it only ever compares two groups' raw entry *text*, and `"san-a"`
and `"/san-.*/"` are different text even when they'd resolve to the same
storage.

One deliberate asymmetry remains, called out explicitly in section 11.4's
own closing paragraph: a pattern-matched storage does **not** get the
literal path's "must have `images` in its content list" check. An operator
who names a storage explicitly gets a hard error for a typo; a pattern that
happens to pick up an ISO-only or otherwise unusable LUN is a
balance-quality concern, not a safety one -- (C2) still keeps any disk from
ever landing there, and `u* = L_s / c_s` (section 4) simply divides by one
more `c_s` than intended. The not-`shared` warning is *not* a second such
asymmetry (an earlier draft left it literal-only, REVIEW.md U-03): it is
computed once, after expansion, uniformly over every final member of the
group regardless of whether a literal or a pattern named it -- a warning
carries no typo-safety rationale for staying quiet, unlike the content
check.

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

`compute_reserve_status()` computes, for one storage: `used = Σ_{d∈D on s} z_d
+ Uˢᵉˣᵗ_s` (every managed disk's bytes plus the foreign/unreferenced bytes
from "`Uˢᵉˣᵗ`: everything not referenced" above), `shortfall = max(0, used +
R_s − capacity_s)`, and `ReserveStatus.violated` is exactly `shortfall > 0`
— the boolean `gates.py`'s reserve-override gate reads directly
(`docs/internals/80-gates.md`). It is deliberately its own module, not a
method on `Storage`: `heuristic.py` needs to evaluate the identical formula
against a *candidate* assignment, not only the current one (`storage_of=`
overrides which storage each disk is treated as sitting on), and
`pve-storage-drs show-load`'s reporting needs it against the current
assignment today. Both
call the same function (AGENTS.md section 5) — `show-load`'s use of it is
already exercised end-to-end (see `cli.py`'s
`_render_show_load_human`/`_json`). `optimize.py`'s MILP path needs the
same (C4)/(C5) invariant but cannot call a Python function from inside a
solver's constraint system — see `91-optimize.md` for how it encodes the
equivalent bound directly as a scaled linear constraint instead. The
section 14 worked example's initial state (`tests/unit/test_reserve.py`)
is the proof this reproduces the plan's own arithmetic exactly, not merely
a self-consistent unit test.

## `free_space` resolution: `soft_s`/`hard_s`, resolved once, here

Section 5.3.1's `soft_s`/`hard_s` pair is resolved onto
`Storage.free_space_soft_bytes`/`.free_space_hard_bytes` in
`_build_storages()`, by `_resolve_free_space()` -- the same place and the
same per-storage pattern `_resolve_reserve_factor()` already uses for
`reserve_factor`, and for the same reason: a `/…/` pattern's `free_space`
entry applies to every storage it matches, a literal entry overrides it,
and only a real storage's `capacity_bytes` (known here, not in `config.py`)
can resolve a percentage. The mandated order is inheritance, then
percent-to-bytes conversion, then the two section 11.1 hard rules against
the resolved values (`hard_s <= soft_s`, `soft_s < C_s` -- both raise
`TopologyError`, exactly like the pattern-expansion rules above, since both
need the cluster inventory config.py never has). A *null* `hard` means
`hard_s = soft_s`. `_resolve_free_space()` returns
a `ResolvedFreeSpace`: the pair plus two display-only strings naming the level
each half came from (global, storage entry, `pattern /re/`, percent-converted),
carried on `Storage.free_space_soft_source`/`_hard_source` for
`verify-storages` and read by nothing else. By the time
`compute_reserve_status()` reads `storage.free_space_soft_bytes`, or
`schedule.transient_invariant_ok()` reads `.free_space_hard_bytes`, both
are plain, already-resolved byte constants -- section 5.3.1's own grammar
(percentages, patterns) is never seen again past this
module.

## (C2) format eligibility: `storage_type`/`allowed_formats`

`Storage` also carries `storage_type` (from `GET /storage`'s own `type`
field, never guessed) and `allowed_formats` -- the disk formats that type
can actually hold, from a fixed table keyed by the same storage-type
partition `_default_format()` already draws for the fallback format of a
content listing with no `format` field of its own: a block-backed type
(`lvmthin`, `zfspool`, `rbd`, `iscsi`, `iscsidirect`) holds `raw` only --
there is no image container on the array, a volume *is* the raw block
device -- and a file-backed type (`dir`, `nfs`, `cifs`, `cephfs`) holds
whatever `qemu-img` formats PVE offers a regular file for. Ordinary
(non-thin) `lvm` is the one block-backed exception: current PVE versions
also accept `qcow2` there, since PVE 9.2 added snapshot support on plain
LVM by formatting the LV itself as a qcow2 image rather than using it raw
(the same mechanism `_resolve_disk_size_and_format()`'s `approximate-size`
note above describes) -- `lvmthin` needs no such carve-out, since its
snapshots are native LVM-thin COW, never qcow2-on-the-LV. Section 5.3
(C2)'s "`s` cannot hold the disk's format" is `topology.
storage_accepts_format(storage, disk.format)` -- one function, called by
both MILP backends (`91-optimize.md`) and by `heuristic.py`'s own
candidate-generating helpers to fix `x_{d,s}=0` (or exclude the pair from
the neighbourhood the heuristic searches) for every ineligible target.
Unlike the free-space floor, format eligibility needs no per-run
resolution step of its own -- it is a pure function of `storage_type`,
computed once when `Storage` is built and read directly thereafter.
