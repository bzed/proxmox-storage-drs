# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The snapshot-reserve constraint. See IMPLEMENTATION_PLAN.md section 5.3 (C4)/(C5).

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
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from proxmox_storage_drs.topology import Disk, Storage

# The default assignment source: `Disk.current_storage`, i.e. "the real,
# present-day placement." `heuristic.py` passes its own lookup (typically
# `assignment.__getitem__` or `assignment.get`) to evaluate a *candidate*
# assignment through these same functions instead -- see the module
# docstring; this is that "identical shape" made concrete.
StorageOf = Callable[[Disk], str]


def _current_storage(disk: Disk) -> str:
    return disk.current_storage


@dataclass(frozen=True, slots=True)
class ReserveStatus:
    """One storage's (C4)/(C5) evaluation at a given assignment."""

    largest_disk_bytes: int  # Z_s (C4)
    required_reserve_bytes: int  # R_s = max(f_s * Z_s, soft_s) (C5, section 5.3.1)
    managed_used_bytes: int  # Sum_d z_d * x_{d,s} over disks assigned here
    shortfall_bytes: int  # r_s: 0 unless the reserve is already breached

    @property
    def violated(self) -> bool:
        return self.shortfall_bytes > 0


def largest_disk_bytes(
    disks: Iterable[Disk], storage_id: str, *, storage_of: StorageOf = _current_storage
) -> int:
    """Z_s: the largest disk on ``storage_id`` under ``storage_of``, 0 if none (C4)."""
    return max((d.size_bytes for d in disks if storage_of(d) == storage_id), default=0)


def managed_used_bytes(
    disks: Iterable[Disk], storage_id: str, *, storage_of: StorageOf = _current_storage
) -> int:
    """Sum_d z_d for every disk in `D` on ``storage_id`` under ``storage_of`` --
    the part of a storage's usage this tool is actually tracking, as opposed
    to ``Storage.foreign_used_bytes`` (section 5.1.1)."""
    return sum(d.size_bytes for d in disks if storage_of(d) == storage_id)


def transient_charge_ok(
    reserve_factor: float,
    capacity_bytes: int,
    used_bytes: int,
    existing_largest_bytes: int,
    charge_sizes_bytes: Iterable[int],
    hard_free_bytes: int,
) -> bool:
    """IMPLEMENTATION_PLAN.md section 8.1's transient invariant, generalized
    to an arbitrary set of moves landing on one storage at once::

        used_b + sum(z_m) + max(f_b * max(Z_b, max(z_m)), hard_b) <= C_b

    ``charge_sizes_bytes`` is every in-flight move's ``z_m`` (its disk's
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

    ``existing_largest_bytes`` is ``Z_b`` *before* any of
    ``charge_sizes_bytes`` land — the largest disk already resident on the
    target, from whichever data source the caller is using. Returns
    ``True`` (vacuously satisfied) when ``charge_sizes_bytes`` is empty —
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
    charges = list(charge_sizes_bytes)
    if not charges:
        return True
    required = max(
        round(reserve_factor * max(existing_largest_bytes, max(charges))), hard_free_bytes
    )
    return used_bytes + sum(charges) + required <= capacity_bytes


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
    (section 5.3.1: inheritance, percent-to-bytes conversion and the
    deprecated ``min_free_bytes`` fold all already applied), the same way
    ``reserve_factor`` is already resolved onto ``storage.reserve_factor``
    rather than threaded in as a separate scalar. ``storage_of`` defaults to
    ``Disk.current_storage`` (today's real placement); pass a
    candidate-assignment lookup (e.g. ``assignment.__getitem__``) to
    evaluate a hypothetical one instead -- ``Storage.foreign_used_bytes``
    is unaffected either way, since section 5.1.1 defines it as
    assignment-invariant (foreign volumes are never members of `D`).
    """
    disks = list(disks)
    largest = largest_disk_bytes(disks, storage.id, storage_of=storage_of)
    required = max(round(storage.reserve_factor * largest), storage.free_space_soft_bytes)
    used = managed_used_bytes(disks, storage.id, storage_of=storage_of) + storage.foreign_used_bytes
    shortfall = max(0, used + required - storage.capacity_bytes)
    return ReserveStatus(
        largest_disk_bytes=largest,
        required_reserve_bytes=required,
        managed_used_bytes=used,
        shortfall_bytes=shortfall,
    )
