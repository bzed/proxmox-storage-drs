# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reduce raw per-disk metrics to the scalar load vector `ℓ`. See
IMPLEMENTATION_PLAN.md section 4.

This module fetches nothing about topology and never talks to the PVE API --
it takes an already-built ``topology.Group`` (one group's `D`/`S`) and a
``metrics.PrometheusClient``, and produces one load value per disk plus the
per-storage `L_s`/`u_s` and group-wide `u*` that ``show-load`` and the
gates/solver (not yet written) need. Every quantity here is in **average
in-flight I/O requests** unless documented otherwise -- section 4 is
explicit that the rescale back onto that absolute scale is not cosmetic:
everything downstream (the saturation guard, the big-M bound, the objective
weights) is calibrated against it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from proxmox_storage_drs.config import LoadWeights, MetricsConfig, WindowConfig
from proxmox_storage_drs.metrics import (
    RAW_METRIC_FIELDS,
    DiskKey,
    PrometheusClient,
    build_quantile_over_time_promql,
    build_rate_promql,
    compute_disk_coverage,
    parse_disk_series,
    raw_metric_name,
)
from proxmox_storage_drs.topology import Group

# Section 3.4's own note: "tpmstate0 and unused{N} are not QEMU block
# devices, so no series will exist for them and ℓ_d = 0 under the
# min_coverage rule... that is correct rather than a gap." A disk of one of
# these device kinds is never rejected/flagged for low coverage -- its true
# load is legitimately (not just apparently) zero. efidisk0 *is* a QEMU
# drive and should appear in blockstat, so it is not in this set and is
# held to the same coverage bar as scsi/virtio/ide/sata.
_METRICS_EXPECTED_ABSENT_PREFIXES = ("unused",)
_METRICS_EXPECTED_ABSENT_EXACT = frozenset({"tpmstate0"})


def _is_metrics_expected_absent(device: str) -> bool:
    if device in _METRICS_EXPECTED_ABSENT_EXACT:
        return True
    return device.startswith(_METRICS_EXPECTED_ABSENT_PREFIXES)


@dataclass(frozen=True, slots=True)
class DiskLoad:
    """One disk's `ℓ_d`. Section 4."""

    disk_key: str  # topology.Disk.key ("vmid:device")
    load: float
    # None: a normal, trusted measurement. Otherwise section 3.4's
    # min_coverage rule fired -- `load` is either a state.json-recorded
    # last known value (not yet wired through; see the module docstring
    # note below `compute_group_load`) or 0.0, and this says which so a
    # caller never mistakes a flagged 0.0 for a genuinely idle disk.
    flagged_reason: str | None


@dataclass(frozen=True, slots=True)
class StorageLoad:
    """One storage's current `L_s`/`u_s`, at the assignment `Disk.current_storage`
    already encodes -- not a candidate assignment (that is the solver's job,
    not yet written), matching ``reserve.py``'s identical "current state"
    framing."""

    storage_id: str
    load: float  # L_s = Sum_d l_d over disks currently on this storage
    utilization: float  # u_s = L_s / c_s


@dataclass(frozen=True, slots=True)
class GroupLoad:
    """One group's whole load picture for this run. Section 4/6."""

    group_name: str
    # Section 4: "if T_g = 0 the entire group is idle -- skip it, there is
    # nothing to balance." True only when every *accepted* (not
    # coverage-rejected) disk's raw in-flight I/O is zero -- see
    # `compute_group_load`'s docstring for why an all-rejected group is
    # deliberately reported the same way (safe: "unknown" and "idle" both
    # mean "don't act").
    idle: bool
    average_utilization: float  # u* = (Sum_d l_d) / (Sum_s c_s), section 5.3 (C6)
    disks: tuple[DiskLoad, ...]
    storages: tuple[StorageLoad, ...]

    def load_by_disk_key(self) -> dict[str, float]:
        """Convenience for callers (``show-load``) keying off `Disk.key`."""
        return {d.disk_key: d.load for d in self.disks}


def _fetch_raw_quantity(
    client: PrometheusClient, metrics: MetricsConfig, window: WindowConfig, field: str
) -> dict[DiskKey, float]:
    """One of the six section 3.4 raw quantities, quantile-reduced over the
    decision window, for every disk Prometheus currently reports -- not
    filtered to one group, since a single query covering everything is one
    call instead of one per group and Python-side filtering by `DiskKey` is
    free."""
    metric_name = raw_metric_name(metrics, field)
    rate_expr = build_rate_promql(
        metric_name, metrics.labels.vmid, metrics.labels.device, metrics.rate_window_seconds
    )
    promql = build_quantile_over_time_promql(
        rate_expr, window.quantile, window.lookback_seconds, metrics.step_seconds
    )
    result = client.instant_query(promql)
    return parse_disk_series(result, metrics.labels.vmid, metrics.labels.device)


@dataclass(frozen=True, slots=True)
class _RawQuantities:
    """The six section 3.4 series, fetched once and reused for every disk."""

    read_ops: dict[DiskKey, float]
    write_ops: dict[DiskKey, float]
    read_bytes: dict[DiskKey, float]
    write_bytes: dict[DiskKey, float]
    read_time_ns: dict[DiskKey, float]
    write_time_ns: dict[DiskKey, float]


def _fetch_all_raw_quantities(
    client: PrometheusClient, metrics: MetricsConfig, window: WindowConfig
) -> _RawQuantities:
    fetched = {
        field: _fetch_raw_quantity(client, metrics, window, field) for field in RAW_METRIC_FIELDS
    }
    return _RawQuantities(**fetched)


def _combined_raw(
    key: DiskKey, raw: _RawQuantities, load_weights: LoadWeights
) -> tuple[float, float, float]:
    """`(raw_t, raw_o, raw_b)` for one disk, section 4:

    ``raw_t/o/b(d) = rho*rd_X(d) + omega*wr_X(d)``, read and write combined
    *before* normalization using the configured asymmetry factors. A key
    absent from a series (no data at all, e.g. an idle disk or a
    tpmstate0/unusedN device -- section 3.4's note) contributes 0, not a
    missing-key error: `.get(key, 0.0)` is deliberate here, not a shortcut --
    absence is exactly what "no I/O this window" looks like for a disk that
    genuinely has none. ``raw_time_ns`` is converted to seconds (section
    3.4's PromQL divides by 1e9 inline; this project applies that conversion
    here instead, engine-side, for the same reason F-03 moved
    read_factor/write_factor engine-side: one tested unit conversion beats
    the same constant repeated across deployed query strings).
    """
    rho, omega = load_weights.read_factor, load_weights.write_factor
    raw_t = (rho * raw.read_time_ns.get(key, 0.0) + omega * raw.write_time_ns.get(key, 0.0)) / 1e9
    raw_o = rho * raw.read_ops.get(key, 0.0) + omega * raw.write_ops.get(key, 0.0)
    raw_b = rho * raw.read_bytes.get(key, 0.0) + omega * raw.write_bytes.get(key, 0.0)
    return raw_t, raw_o, raw_b


def compute_group_load(
    client: PrometheusClient,
    metrics: MetricsConfig,
    window: WindowConfig,
    load_weights: LoadWeights,
    group: Group,
    last_known_loads: Mapping[str, float] | None = None,
) -> GroupLoad:
    """Compute one group's :class:`GroupLoad` for this run. Section 4.

    ``last_known_loads`` is section 3.4's "fall back to its last known load
    from ``state.json``" -- keyed by ``Disk.key``. Pass ``None`` (the
    default) until ``state.json`` persistence exists (not yet written; see
    IMPLEMENTATION_PLAN.md section 11.2): a disk that fails the
    ``min_coverage`` check with no entry here is flagged with load ``0.0``
    rather than silently accepted as zero -- the "never treat missing data
    as zero load" rule (section 3.4) is about not *pretending* an unknown
    load is zero, not about refusing to run before ``state.json`` exists;
    callers must check ``DiskLoad.flagged_reason``, not just filter it out.

    Coverage rejection excludes a disk's raw contribution from its group's
    normalization totals entirely, so one noisy or half-missing series
    cannot bias every other disk's normalized share -- the rejected disk's
    own `ℓ_d` is then substituted from ``last_known_loads`` (or flagged
    0.0), independent of the group blend.
    """
    if not group.disks:
        return GroupLoad(
            group_name=group.name, idle=True, average_utilization=0.0, disks=(), storages=()
        )

    coverage = compute_disk_coverage(client, metrics, window)
    raw = _fetch_all_raw_quantities(client, metrics, window)
    fallback = last_known_loads or {}

    accepted_raw: dict[str, tuple[float, float, float]] = {}
    rejected: dict[str, str] = {}  # disk key -> reason
    for disk in group.disks:
        key = DiskKey(vmid=disk.vmid, device=disk.device)
        fraction = coverage.get(key, 0.0)
        if fraction < window.min_coverage and not _is_metrics_expected_absent(disk.device):
            rejected[disk.key] = (
                f"sample coverage {fraction:.0%} is below window.min_coverage "
                f"({window.min_coverage:.0%})"
            )
            continue
        accepted_raw[disk.key] = _combined_raw(key, raw, load_weights)

    t_total = sum(t for t, _o, _b in accepted_raw.values())
    o_total = sum(o for _t, o, _b in accepted_raw.values())
    b_total = sum(b for _t, _o, b in accepted_raw.values())

    w_t, w_o, w_b = load_weights.iotime, load_weights.ops, load_weights.bytes
    weight_sum = w_t + w_o + w_b

    disk_loads: list[DiskLoad] = []
    for disk in group.disks:
        if disk.key in rejected:
            if disk.key in fallback:
                disk_loads.append(
                    DiskLoad(
                        disk_key=disk.key,
                        load=fallback[disk.key],
                        flagged_reason=f"{rejected[disk.key]}; using last known load",
                    )
                )
            else:
                disk_loads.append(
                    DiskLoad(
                        disk_key=disk.key,
                        load=0.0,
                        flagged_reason=f"{rejected[disk.key]}; no last known load recorded",
                    )
                )
            continue

        raw_t, raw_o, raw_b = accepted_raw[disk.key]
        # Section 4: guard every division -- a zero group total for one term
        # means that term contributes 0 for every disk, not NaN.
        i_d = raw_t / t_total if t_total else 0.0
        o_d = raw_o / o_total if o_total else 0.0
        b_d = raw_b / b_total if b_total else 0.0
        blended = (w_t * i_d + w_o * o_d + w_b * b_d) / weight_sum if weight_sum else 0.0
        disk_loads.append(DiskLoad(disk_key=disk.key, load=t_total * blended, flagged_reason=None))

    load_by_key = {d.disk_key: d.load for d in disk_loads}
    storage_loads: list[StorageLoad] = []
    total_load = 0.0
    total_capability = 0.0
    for storage in group.storages:
        storage_load = sum(
            load_by_key[d.key] for d in group.disks if d.current_storage == storage.id
        )
        utilization = storage_load / storage.capability_weight if storage.capability_weight else 0.0
        storage_loads.append(
            StorageLoad(storage_id=storage.id, load=storage_load, utilization=utilization)
        )
        total_load += storage_load
        total_capability += storage.capability_weight

    average_utilization = total_load / total_capability if total_capability else 0.0

    return GroupLoad(
        group_name=group.name,
        idle=t_total == 0.0,
        average_utilization=average_utilization,
        disks=tuple(disk_loads),
        storages=tuple(storage_loads),
    )
