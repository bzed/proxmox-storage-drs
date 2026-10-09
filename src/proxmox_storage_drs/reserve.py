# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The snapshot-reserve constraint. See IMPLEMENTATION_PLAN.md section 5.3 (C4)/(C5), 5.3.3.

A pure, assignment-independent evaluation of one storage's reserve status:
given which disks currently sit on it, what does it need free, and is it
already short? This is deliberately factored out on its own so the solver
(``optimize.py``/``heuristic.py``, not yet built) and
``pve-storage-drs show-load``'s reporting call the **same** function rather
than each re-deriving (C4)/(C5) -- AGENTS.md section 5's "one implementation
of every rule."

Nothing here is specific to the *current* assignment: every function takes
the disk-to-storage assignment as data (``current_storage`` on each `Disk`
by default; ``storage_of`` lets ``heuristic.py`` pass a *candidate*
assignment through the identical shape instead), so this module has no
built-in notion of "before" or "after" a plan.

``Z_s`` is the largest **per-VM footprint** on a storage (section 5.3.3): a snapshot
is taken of a VM and snapshots every disk of it at once, so what a snapshot of VM ``v``
needs on ``s`` is the sum of all of ``v``'s disks on ``s`` -- not its largest one. The
footprint sum lives in :func:`vm_footprints_bytes` and nowhere else.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Mapping

from proxmox_storage_drs.topology import Disk, Storage, disk_size_on

# The default assignment source: `Disk.current_storage`, i.e. "the real,
# present-day placement." `heuristic.py` passes its own lookup (typically
# `assignment.__getitem__` or `assignment.get`) to evaluate a *candidate*
# assignment through these same functions instead -- see the module
# docstring; this is that "identical shape" made concrete.
StorageOf = Callable[[Disk], str]

#: The granularity every reserve/free-space shortfall is measured in
#: (section 5.3 (C5)): whole MiB, the same unit the MILP writes every
#: size-valued quantity in (section 5.5) and the `ε_r` the plan names as
#: the smallest shortfall worth refusing to trade (section 5.3).
BYTES_PER_MIB = 1 << 20


def round_up_to_mib(size_bytes: int) -> int:
    """``size_bytes`` rounded *up* to the next whole MiB, in bytes.

    Up, never to nearest: a shortfall of one byte is still a breach, and
    ``ReserveStatus.violated`` (``shortfall_bytes > 0``) must stay exactly
    the byte-exact predicate it always was. Only the *amount* is coarsened.
    Negative input is not meaningful here and is not handled."""
    return -(-size_bytes // BYTES_PER_MIB) * BYTES_PER_MIB


def _current_storage(disk: Disk) -> str:
    return disk.current_storage


@dataclass(frozen=True, slots=True)
class ReserveStatus:
    """One storage's (C4)/(C5) evaluation at a given assignment."""

    largest_footprint_bytes: int  # Z_s (C4, section 5.3.3): the largest per-VM footprint
    # The VM whose footprint is Z_s (lowest vmid on a tie), None on an empty storage --
    # what show-load/verify-storages print so an operator can see *which* VM drives it.
    largest_footprint_vmid: int | None
    required_reserve_bytes: int  # R_s = max(f_s * Z_s, soft_s) (C5, section 5.3.1)
    managed_used_bytes: int  # Sum_d z_d * x_{d,s} over disks assigned here
    # r_s: 0 unless the reserve is already breached, and then rounded up to
    # whole MiB (section 5.3 (C5)) -- see compute_reserve_status()
    shortfall_bytes: int

    @property
    def violated(self) -> bool:
        return self.shortfall_bytes > 0


def vm_footprints_bytes(
    disks: Iterable[Disk],
    storage_id: str,
    *,
    storage_of: StorageOf = _current_storage,
    storage: Storage | None = None,
) -> dict[int, int]:
    """``F_{v,s}`` for every VM with a disk on ``storage_id`` under ``storage_of``:
    ``{vmid: sum of z_{d,s} over that VM's disks on the storage}`` (section 5.3.3).

    Every disk in ``disks`` counts, movable or pinned -- a pinned disk is snapshotted with
    its VM like any other. Each disk counts at ``z_{d,s}`` (section 5.3.2) when ``storage``
    -- the :class:`Storage` named by ``storage_id`` -- is given, at ``size_bytes`` otherwise.
    Foreign volumes are not in ``disks`` and contribute no footprint (by decision, section
    5.3.3); their bytes are counted in ``Storage.foreign_used_bytes`` instead."""
    footprints: dict[int, int] = {}
    for d in disks:
        if storage_of(d) == storage_id:
            footprints[d.vmid] = footprints.get(d.vmid, 0) + _size_on(d, storage)
    return footprints


def largest_footprint(footprints: Mapping[int, int]) -> tuple[int, int | None]:
    """``(Z_s, vmid)`` of a ``{vmid: F_{v,s}}`` map: the largest footprint and the VM it
    belongs to (lowest vmid on a tie, so the answer is deterministic); ``(0, None)`` when
    the map is empty."""
    if not footprints:
        return 0, None
    vmid = min(footprints, key=lambda v: (-footprints[v], v))
    return footprints[vmid], vmid


def largest_footprint_bytes(
    disks: Iterable[Disk],
    storage_id: str,
    *,
    storage_of: StorageOf = _current_storage,
    storage: Storage | None = None,
) -> int:
    """Z_s: the largest per-VM footprint on ``storage_id`` under ``storage_of``, 0 if
    none (C4, section 5.3.3). See :func:`vm_footprints_bytes` for what counts."""
    return largest_footprint(
        vm_footprints_bytes(disks, storage_id, storage_of=storage_of, storage=storage)
    )[0]


def largest_disk_bytes(
    disks: Iterable[Disk],
    storage_id: str,
    *,
    storage_of: StorageOf = _current_storage,
    storage: Storage | None = None,
) -> int:
    """The largest single disk on ``storage_id``, 0 if none.

    **Not** ``Z_s``: the snapshot reserve is computed from the per-VM footprint
    (:func:`largest_footprint_bytes`, section 5.3.3). The per-disk maximum survives for
    the one thing that really is per volume -- the source-wipe time estimate of
    section 7.1/9.3 (``z_max``) -- and for ``verify-storages``'s informational line."""
    return max(
        (_size_on(d, storage) for d in disks if storage_of(d) == storage_id),
        default=0,
    )


def _size_on(disk: Disk, storage: Storage | None) -> int:
    return disk.size_bytes if storage is None else disk_size_on(disk, storage)


def managed_used_bytes(
    disks: Iterable[Disk],
    storage_id: str,
    *,
    storage_of: StorageOf = _current_storage,
    storage: Storage | None = None,
) -> int:
    """Sum_d z_d for every disk in `D` on ``storage_id`` under ``storage_of`` --
    the part of a storage's usage this tool is actually tracking, as opposed
    to ``Storage.foreign_used_bytes`` (section 5.1.1)."""
    return sum(_size_on(d, storage) for d in disks if storage_of(d) == storage_id)


def transient_charge_ok(
    reserve_factor: float,
    capacity_bytes: int,
    used_bytes: int,
    existing_largest_bytes: int,
    existing_footprints_bytes: Mapping[int, int],
    charges: Iterable[tuple[int, int]],
    hard_free_bytes: int,
) -> bool:
    """IMPLEMENTATION_PLAN.md section 8.1's transient invariant, generalized
    to an arbitrary set of moves landing on one storage at once::

        used_b + sum(z_m) + max(f_b * max(Z_b, max_v(F_v + sum z_m of v)), hard_b) <= C_b

    ``charges`` is every in-flight move's ``(vmid, z_m)`` (its VM and its disk's
    size) whose *target* is this storage — one element for section 8.1's
    original single-move form (a plain migration under the default
    ``max_concurrent_migrations: 1``), more than one only when several
    moves land on the same storage at once. This is the one arithmetic
    core both `schedule.py`'s planning-time check (model-derived
    ``used_bytes``/``existing_largest_bytes``, always a single charge) and
    `execute.py`'s live, execution-time check (``used_bytes`` summed from the
    target's live content listing at provisioned sizes, never PVE's own
    allocated ``used`` — section 5.1; one or more charges once concurrent
    execution launches more than one move onto the same target) call — AGENTS.md section 5:
    the *rule* is one implementation, and only the *source* of
    ``used_bytes``/``existing_largest_bytes``/``capacity_bytes`` legitimately
    differs between a model-based caller and a live one (a live re-check
    also wants a live ``total`` in place of ``Storage.capacity_bytes``, in
    case the LUN itself was resized since this run started — which is why
    this function takes plain numbers, never a whole ``Storage``, so
    neither caller has to fabricate one just to substitute one field).

    Deliberately conservative for the concurrent case: this function does
    not assume ``used_bytes`` already reflects any of ``charge_sizes_bytes``
    — the arithmetic is only ever *too* conservative if it does, never
    unsafe, and unsafe is the one direction this tool never accepts, see
    `.agents/domain-invariants.md`. A caller that can tell which listed
    volumes are its own in-flight mirror targets (`execute.py` does) leaves
    those out of ``used_bytes`` so each is counted once, not twice.

    ``existing_largest_bytes`` is ``Z_b`` *before* any of ``charges`` land — the
    largest per-VM footprint already resident on the target — and
    ``existing_footprints_bytes`` the ``{vmid: F_{v,b}}`` map it is the maximum of
    (section 5.3.3); a charged VM absent from it has footprint 0 there. A disk
    landing raises *its own VM's* footprint by ``z_m`` (two disks of one VM landing
    together raise it by both), which is what the inner ``max_v`` is; both come
    from whichever data source the caller is using. Returns
    ``True`` (vacuously satisfied) when ``charges`` is empty —
    there is nothing landing on this storage for the check to apply to.

    ``hard_free_bytes`` is the storage's resolved ``hard_b`` (section
    5.3.1) -- the *transient* floor, not the endpoint one: this is the one
    place the free-space floor may be lower than what (C5)/
    :func:`compute_reserve_status` demands, by design (an operator who sets
    ``free_space.hard`` below ``free_space.soft`` is deliberately buying the
    scheduler room for a bounded dip while a move is in flight). Pass
    ``storage.free_space_hard_bytes`` — resolved once at run start, plain
    bytes, never re-derived here.
    """
    landing = list(charges)
    if not landing:
        return True
    landed_by_vm: dict[int, int] = {}
    for vmid, size_bytes in landing:
        landed_by_vm[vmid] = landed_by_vm.get(vmid, 0) + size_bytes
    largest_after = max(
        existing_largest_bytes,
        max(existing_footprints_bytes.get(v, 0) + added for v, added in landed_by_vm.items()),
    )
    required = max(round(reserve_factor * largest_after), hard_free_bytes)
    return used_bytes + sum(landed_by_vm.values()) + required <= capacity_bytes


def total_shortfall_bytes(
    storages: Iterable[Storage], disks: Iterable[Disk], *, storage_of: StorageOf = _current_storage
) -> int:
    """`Σ_s r_s` at the assignment ``storage_of`` encodes -- section 7.3's
    outcome trigger (a plan's *final* `Σ r_s` strictly below its *current*
    one) and the revert test that marks which moves carried the repair
    both need this one group-wide sum, not any single storage's own
    shortfall. ``disks`` is materialized once and reused across every
    storage, matching :func:`compute_reserve_status`'s own contract."""
    disks = list(disks)
    return sum(
        compute_reserve_status(s, disks, storage_of=storage_of).shortfall_bytes for s in storages
    )


def compute_reserve_status(
    storage: Storage,
    disks: Iterable[Disk],
    *,
    storage_of: StorageOf = _current_storage,
) -> ReserveStatus:
    """(C4)/(C5) evaluated for one storage at the assignment ``storage_of`` encodes.

    ``R_s = max(f_s * Z_s, soft_s)`` -- ``soft_s`` is
    ``storage.free_space_soft_bytes``, resolved per storage by ``topology.py``
    (section 5.3.1: inheritance and percent-to-bytes conversion already
    applied), the same way
    ``reserve_factor`` is already resolved onto ``storage.reserve_factor``
    rather than threaded in as a separate scalar. ``storage_of`` defaults to
    ``Disk.current_storage`` (today's real placement); pass a
    candidate-assignment lookup (e.g. ``assignment.__getitem__``) to
    evaluate a hypothetical one instead -- ``Storage.foreign_used_bytes``
    is unaffected either way, since section 5.1.1 defines it as
    assignment-invariant (foreign volumes are never members of `D`).

    ``shortfall_bytes`` is measured in **whole MiB, rounded up** (section
    5.3 (C5)). Every consumer of a shortfall *difference* -- the heuristic's
    repair step, the MILP's lexicographic stage 1, section 7.3's repair
    exemption and its revert test -- compares these sums, and at byte
    resolution two of them disagree about sub-MiB noise: CBC reports its
    stage-1 optimum to about three decimals of a MiB, which once made the
    byte-exact stage-2 bound spuriously infeasible on every run with a
    non-round shortfall. Rounding up keeps ``violated`` byte-exact (one
    byte short is still short) and overstates the amount by less than
    1 MiB, the safe direction.
    """
    disks = list(disks)
    largest, largest_vmid = largest_footprint(
        vm_footprints_bytes(disks, storage.id, storage_of=storage_of, storage=storage)
    )
    required = max(round(storage.reserve_factor * largest), storage.free_space_soft_bytes)
    used = (
        managed_used_bytes(disks, storage.id, storage_of=storage_of, storage=storage)
        + storage.foreign_used_bytes
    )
    shortfall = round_up_to_mib(max(0, used + required - storage.capacity_bytes))
    return ReserveStatus(
        largest_footprint_bytes=largest,
        largest_footprint_vmid=largest_vmid,
        required_reserve_bytes=required,
        managed_used_bytes=used,
        shortfall_bytes=shortfall,
    )


def split_vm_caps(disks: Iterable[Disk], split_vm_footprint_bytes: int | None) -> dict[int, int]:
    """``{vmid: T_v}`` for every VM in ``V^split`` (section 5.3.3), empty when the rule is off.

    ``V^split`` is every VM whose disks in ``disks`` add up (at their listed size ``z_d``)
    to more than ``T``; a VM no larger than ``T`` can never exceed it on one storage.
    ``T_v = max(T, largest disk of v)``: a disk larger than ``T`` cannot be split, so its own
    storage may hold it in full."""
    if split_vm_footprint_bytes is None:
        return {}
    total: dict[int, int] = {}
    largest: dict[int, int] = {}
    for d in disks:
        total[d.vmid] = total.get(d.vmid, 0) + d.size_bytes
        largest[d.vmid] = max(largest.get(d.vmid, 0), d.size_bytes)
    return {
        vmid: max(split_vm_footprint_bytes, largest[vmid])
        for vmid, size in total.items()
        if size > split_vm_footprint_bytes
    }


def split_peak_footprints_bytes(
    storages: Iterable[Storage],
    disks: Iterable[Disk],
    caps: Iterable[int],
    *,
    storage_of: StorageOf = _current_storage,
) -> dict[int, int]:
    """``max_s F_{v,s}`` for every VM id in ``caps`` (section 5.3.3): the largest footprint any
    one storage holds of that VM under ``storage_of``, each disk at ``z_{d,s}``."""
    wanted = set(caps)
    if not wanted:
        return {}
    storages = list(storages)
    disks = list(disks)
    peak = {vmid: 0 for vmid in wanted}
    for storage in storages:
        for vmid, footprint in vm_footprints_bytes(
            disks, storage.id, storage_of=storage_of, storage=storage
        ).items():
            if vmid in wanted:
                peak[vmid] = max(peak[vmid], footprint)
    return peak


def split_excess_bytes(
    storages: Iterable[Storage],
    disks: Iterable[Disk],
    caps: Mapping[int, int],
    *,
    storage_of: StorageOf = _current_storage,
) -> dict[int, int]:
    """``o_v`` for every VM in ``caps`` (section 5.3.3, (C9)): the peak footprint any one
    storage holds of the VM beyond its cap, ``max(0, max_s F_{v,s} - T_v)``. The peak, not a
    sum over storages, because the reserve a storage needs is driven by the largest footprint
    on it."""
    peak = split_peak_footprints_bytes(storages, disks, caps, storage_of=storage_of)
    return {vmid: max(0, peak[vmid] - cap) for vmid, cap in caps.items()}
