# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Section 6: decide whether to act on a group at all, before the solver runs.

``evaluate_group_gates()`` is a pure function -- no network I/O, no
``state.json`` access -- taking an already-computed ``loadmodel.GroupLoad``,
the already-computed ``reserve.ReserveStatus`` per storage, the group's
``topology.Group`` (needed only for the capacity gate's `b_s`/`b_bar`,
section 5.3 (C7) -- `GroupLoad` carries I/O, never bytes/capacity), and
(once ``state.json`` exists; not yet written, see the ``last_load``
parameter's own note) the load vector recorded at the last *executed*
balance. This mirrors ``reserve.py``'s own framing: given the inputs,
evaluate one formula, so the solver and any read-only reporting command
call the exact same function rather than each re-deriving section 6's
rules.

**Cooldowns (``gates.cooldown_per_disk``/``cooldown_per_storage``) are
deliberately not here.** They do not decide whether to act on a *group* --
they pin individual disks/storages once a plan is already being built, the
same way (C2)'s other pin reasons do. That decision belongs with whatever
module builds the movable-disk set for the solver (`heuristic.py`/
`schedule.py`, phase 4, not yet written), not with this module's
act/no-act-per-group question.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from proxmox_storage_drs.config import GatesConfig
from proxmox_storage_drs.heuristic import group_average_fill
from proxmox_storage_drs.loadmodel import GroupLoad
from proxmox_storage_drs.reserve import ReserveStatus
from proxmox_storage_drs.topology import Group

# Section 6's "treat as fully drifted, proceed" degenerate case has no
# well-defined ratio (0/0) -- 1.0 (100%) is the sentinel used to mean
# exactly that: guaranteed to meet any `drift_threshold` in its valid
# range (0, 1], without claiming a specific, meaningless percentage.
_FULLY_DRIFTED = 1.0


@dataclass(frozen=True, slots=True)
class GateDecision:
    """One group's act/no-act verdict, section 6, with the reasoning shown
    (phase 3's own "done when") -- ``reason`` is meant to be printed
    verbatim, not just logged."""

    act: bool
    reason: str
    reserve_override: bool
    # None means "not evaluated" -- the reserve override short-circuited
    # before reaching that gate, not that it evaluated to zero.
    drift_fraction: float | None
    imbalance_fraction: float | None
    # None means "not evaluated": gates.capacity_spread_threshold is null,
    # or the group holds no data at all (mean fill 0, section 5.3 (C7)).
    capacity_fraction: float | None = None


def _l1_drift(load_now: Mapping[str, float], load_last: Mapping[str, float]) -> tuple[float, float]:
    """``(‖ℓ_last‖₁, ‖ℓ_now − ℓ_last‖₁)`` over the **union** of disk keys
    present in either vector (section 6: "a disk created since the last
    balance therefore contributes its full current load to the numerator,
    and a deleted disk contributes its full former load"), a missing key
    treated as load 0 in the vector it is absent from.
    """
    keys = set(load_now) | set(load_last)
    l1_last = sum(abs(load_last.get(key, 0.0)) for key in keys)
    l1_diff = sum(abs(load_now.get(key, 0.0) - load_last.get(key, 0.0)) for key in keys)
    return l1_last, l1_diff


def _capacity_spread(group: Group, reserve_statuses: Mapping[str, ReserveStatus]) -> float | None:
    """Section 5.3 (C7)'s `(max_s b_s - min_s b_s) / b_bar`, or ``None``
    when the gate cannot fire at all: "if b_bar = 0 the group holds no
    data: the term is inactive" -- an empty group has nothing to spread.
    ``reserve_statuses[s.id].managed_used_bytes`` already includes
    ``s.foreign_used_bytes`` (``reserve.compute_reserve_status()``), and
    ``heuristic.group_average_fill()`` is the one implementation of
    `b_bar` (AGENTS.md section 5), shared with the objective evaluator."""
    b_bar = group_average_fill(group)
    if not b_bar:
        return None
    fills = [
        reserve_statuses[s.id].managed_used_bytes / s.capacity_bytes
        for s in group.storages
        if s.capacity_bytes
    ]
    if not fills:
        return None
    return (max(fills) - min(fills)) / b_bar


def evaluate_group_gates(
    group_load: GroupLoad,
    reserve_statuses: Mapping[str, ReserveStatus],
    group: Group,
    gates: GatesConfig,
    last_load: Mapping[str, float] | None,
) -> GateDecision:
    """Section 6, applied in the order it lists: reserve override, then
    the capacity gate, then drift, then imbalance. Any gate that decides
    ends evaluation there.

    ``reserve_statuses`` is keyed by storage id -- one entry per
    ``group_load.storages``, from ``reserve.compute_reserve_status()`` (the
    caller's job; this function only reads ``.violated``/``.managed_used_bytes``,
    per AGENTS.md section 5's "one implementation of every rule" -- this is
    not a second one). ``group`` is needed only for the capacity gate's
    `b_s`/`b_bar` (section 5.3 (C7)): unlike the imbalance gate, this
    cannot be derived from ``group_load`` alone, which carries I/O, never
    bytes/capacity. ``last_load`` is the load vector recorded at the
    group's last *executed* balance, keyed by ``topology.Disk.key`` --
    ``None`` means no such run has ever happened (or ``state.json`` was
    reset), which section 6's own degenerate-case table says skips the
    drift gate outright, not "treat as zero drift". Passing ``None``
    unconditionally is exactly correct for any caller that has no
    ``state.json`` to read yet (nothing in this codebase does, as of this
    module).
    """
    violated = sorted(sid for sid, status in reserve_statuses.items() if status.violated)
    if violated:
        return GateDecision(
            act=True,
            reason=(
                f"reserve violated on {', '.join(violated)}; acting now regardless of the "
                "normal drift/imbalance thresholds -- a capacity shortfall is never delayed "
                "by them"
            ),
            reserve_override=True,
            drift_fraction=None,
            imbalance_fraction=None,
            capacity_fraction=None,
        )

    # Capacity gate: the data-spread counterpart of the imbalance gate,
    # evaluated on fill fractions rather than loads (section 6). It
    # bypasses the drift and imbalance gates the same way the reserve
    # override does -- "a stable workload is not a reason to keep data
    # concentrated" -- so it is checked here, before drift, not folded
    # into the imbalance branch below. `null` disables it outright.
    capacity_fraction: float | None = None
    if gates.capacity_spread_threshold is not None:
        capacity_fraction = _capacity_spread(group, reserve_statuses)
        if capacity_fraction is not None and capacity_fraction >= gates.capacity_spread_threshold:
            return GateDecision(
                act=True,
                reason=(
                    f"capacity spread {capacity_fraction:.1%} meets or exceeds "
                    f"gates.capacity_spread_threshold ({gates.capacity_spread_threshold:.1%}) -- "
                    "acting now regardless of I/O drift/imbalance"
                ),
                reserve_override=False,
                drift_fraction=None,
                imbalance_fraction=None,
                capacity_fraction=capacity_fraction,
            )

    load_now = group_load.load_by_disk_key()
    drift_fraction: float | None = None

    if last_load is not None:
        l1_last, l1_diff = _l1_drift(load_now, last_load)
        if l1_last == 0.0:
            if sum(abs(value) for value in load_now.values()) == 0.0:
                return GateDecision(
                    act=False,
                    reason="no measured load now or at the last balance -- nothing to balance",
                    reserve_override=False,
                    drift_fraction=0.0,
                    imbalance_fraction=None,
                    capacity_fraction=capacity_fraction,
                )
            drift_fraction = _FULLY_DRIFTED
        else:
            drift_fraction = l1_diff / l1_last
            if drift_fraction < gates.drift_threshold:
                return GateDecision(
                    act=False,
                    reason=(
                        f"drift {drift_fraction:.1%} is below gates.drift_threshold "
                        f"({gates.drift_threshold:.1%})"
                    ),
                    reserve_override=False,
                    drift_fraction=drift_fraction,
                    imbalance_fraction=None,
                    capacity_fraction=capacity_fraction,
                )

    if not group_load.storages or group_load.average_utilization == 0.0:
        # REVIEW.md W-06/W-07: a resolved node selector that matched zero
        # series looks identical to a genuinely idle group from here --
        # ``group_load`` already told them apart.
        reason = (
            "the resolved query filter matched no series at all -- this is not necessarily "
            "an idle group; check metrics.labels.node against verify-metrics"
            if group_load.no_series_matched
            else "group is idle: no measured I/O to balance"
        )
        return GateDecision(
            act=False,
            reason=reason,
            reserve_override=False,
            drift_fraction=drift_fraction,
            imbalance_fraction=0.0,
            capacity_fraction=capacity_fraction,
        )

    utilizations = [storage.utilization for storage in group_load.storages]
    spread = (max(utilizations) - min(utilizations)) / group_load.average_utilization
    act = spread >= gates.imbalance_threshold
    comparison = "meets or exceeds" if act else "is below"
    return GateDecision(
        act=act,
        reason=(
            f"imbalance {spread:.1%} {comparison} gates.imbalance_threshold "
            f"({gates.imbalance_threshold:.1%})"
        ),
        capacity_fraction=capacity_fraction,
        reserve_override=False,
        drift_fraction=drift_fraction,
        imbalance_fraction=spread,
    )
