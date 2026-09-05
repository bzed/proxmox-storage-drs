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
today; the solver will pass a candidate assignment through the identical
shape later), so this module has no notion of "before" or "after" a plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from proxmox_storage_drs.topology import Disk, Storage


@dataclass(frozen=True, slots=True)
class ReserveStatus:
    """One storage's (C4)/(C5) evaluation at a given assignment."""

    largest_disk_bytes: int  # Z_s (C4)
    required_reserve_bytes: int  # R_s = max(f_s * Z_s, min_free_bytes) (C5)
    managed_used_bytes: int  # Sum_d z_d * x_{d,s} over disks assigned here
    shortfall_bytes: int  # r_s: 0 unless the reserve is already breached

    @property
    def violated(self) -> bool:
        return self.shortfall_bytes > 0


def largest_disk_bytes(disks: Iterable[Disk], storage_id: str) -> int:
    """Z_s: the largest disk currently on ``storage_id``, 0 if none (C4)."""
    return max((d.size_bytes for d in disks if d.current_storage == storage_id), default=0)


def managed_used_bytes(disks: Iterable[Disk], storage_id: str) -> int:
    """Sum_d z_d for every disk in `D` currently on ``storage_id`` -- the
    part of a storage's usage this tool is actually tracking, as opposed to
    ``Storage.foreign_used_bytes`` (section 5.1.1)."""
    return sum(d.size_bytes for d in disks if d.current_storage == storage_id)


def compute_reserve_status(
    storage: Storage, disks: Iterable[Disk], min_free_bytes: int
) -> ReserveStatus:
    """(C4)/(C5) evaluated for one storage at the assignment `disks` encode.

    ``min_free_bytes`` is ``snapshot_reserve.min_free_bytes`` -- a single
    cluster-wide floor, unlike ``reserve_factor`` which config.py already
    resolves per storage onto ``storage.reserve_factor``.
    """
    disks = list(disks)
    largest = largest_disk_bytes(disks, storage.id)
    required = max(round(storage.reserve_factor * largest), min_free_bytes)
    used = managed_used_bytes(disks, storage.id) + storage.foreign_used_bytes
    shortfall = max(0, used + required - storage.capacity_bytes)
    return ReserveStatus(
        largest_disk_bytes=largest,
        required_reserve_bytes=required,
        managed_used_bytes=used,
        shortfall_bytes=shortfall,
    )
