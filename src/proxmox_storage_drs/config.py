# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Load, validate and resolve the configuration file.

See IMPLEMENTATION_PLAN.md section 11 for the full specification: the
resolution order (``--config`` > ``$PVE_STORAGE_DRS_CONFIG`` > the default
``/etc/pve/drs.yaml``), why the file lives on pmxcfs, and why an explicitly
named config that cannot be read is always a hard failure rather than a
fallback. Section 11.1 lists the semantic validation rules; section 15.1 maps
every knob here to the formula that consumes it -- keep that table current
when adding a knob.

Every default in this module is also what ``cli.py --help`` prints and what
``config/drs.example.yaml`` documents; the three must never drift apart
(``.agents/documentation.md``).
"""

from __future__ import annotations

import hashlib
import importlib.resources
import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Mapping

import jsonschema
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from proxmox_storage_drs.exceptions import ConfigError
from proxmox_storage_drs.units import parse_duration_seconds, parse_size_bytes

# ----------------------------------------------------------------- resolution
DEFAULT_CONFIG_PATH = "/etc/pve/drs.yaml"
ENV_CONFIG_VAR = "PVE_STORAGE_DRS_CONFIG"
ENV_PASSWORD_VAR = "PVE_PASSWORD"
ENV_TOKEN_SECRET_VAR = "PVE_TOKEN_SECRET"

SUPPORTED_SCHEMA_MAJOR = 1

_DAY_NAMES = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


# --------------------------------------------------------------------- model
#
# Frozen, slotted value objects per .agents/python-style.md. Every duration or
# size field is stored already converted to its canonical unit (seconds,
# bytes) with that unit in the name, so nothing downstream re-parses a string
# or silently mixes units.


@dataclass(frozen=True, slots=True)
class AuthConfig:
    """Credentials for the PVE API, from the ``proxmox.auth`` block.

    Fields, with their YAML keys:

    - ``username`` (``proxmox.auth.username``, string, default None): PVE user name,
      used with ``password``.
    - ``password`` (``proxmox.auth.password``, string, default None): password for
      ``username``. When the key is absent, the loader reads ``$PVE_PASSWORD``.
    - ``token_id`` (``proxmox.auth.token_id``, string, default None): API token id,
      used with ``token_secret``.
    - ``token_secret`` (``proxmox.auth.token_secret``, string, default None): secret
      of ``token_id``. When the key is absent, the loader reads
      ``$PVE_TOKEN_SECRET``.

    The loader does not check that a usable pair is present. The PVE client
    reports a failed login when it connects.
    """

    username: str | None = None
    password: str | None = None
    token_id: str | None = None
    token_secret: str | None = None


@dataclass(frozen=True, slots=True)
class ProxmoxConfig:
    """PVE API endpoint and client settings, from the ``proxmox`` block.

    Fields, with their YAML keys:

    - ``host`` (``proxmox.host``, string, default ``""``): host name or address of
      the PVE API. An empty value fails validation for every run that connects.
    - ``port`` (``proxmox.port``, integer 1 to 65535, default 8006): TCP port of the
      PVE API.
    - ``verify_ssl`` (``proxmox.verify_ssl``, boolean, default True): check the
      server certificate.
    - ``ca_file`` (``proxmox.ca_file``, path or null, default None): CA bundle for
      the certificate check.
    - ``auth`` (``proxmox.auth``): credentials, see :class:`AuthConfig`.
    - ``ticket_refresh_seconds`` (``proxmox.ticket_refresh_seconds``, duration in
      seconds, default 3000): age after which the client renews its login ticket.
    - ``read_workers`` (``proxmox.read_workers``, integer at least 1, default 12):
      number of concurrent PVE API reads. The client connection pool holds at least
      10 connections, whatever this value is.
    """

    host: str = ""
    port: int = 8006
    verify_ssl: bool = True
    ca_file: str | None = None
    auth: AuthConfig = field(default_factory=AuthConfig)
    ticket_refresh_seconds: float = 3000.0
    read_workers: int = 12


@dataclass(frozen=True, slots=True)
class PrometheusConfig:
    """Prometheus query endpoint, from the ``prometheus`` block.

    Fields, with their YAML keys:

    - ``url`` (``prometheus.url``, string, default ``""``): base URL of the
      Prometheus server. An empty value fails validation for every run that
      connects.
    - ``timeout_seconds`` (``prometheus.timeout_seconds``, duration in seconds,
      default 30): timeout for one query.
    - ``username`` (``prometheus.username``, string, default None): user name for
      HTTP basic authentication.
    - ``password`` (``prometheus.password``, string, default None): password for
      ``username``.
    - ``bearer_token`` (``prometheus.bearer_token``, string, default None): bearer
      token for the ``Authorization`` header.
    """

    url: str = ""
    timeout_seconds: float = 30.0
    username: str | None = None
    password: str | None = None
    bearer_token: str | None = None


@dataclass(frozen=True, slots=True)
class MetricLabels:
    """Label names that identify a series in Prometheus, from ``metrics.labels``.

    Each field names the label that carries one identity:

    - ``vmid`` (``metrics.labels.vmid``, default ``"vmid"``): label holding the VM id.
    - ``device`` (``metrics.labels.device``, default ``"instance"``): label holding
      the disk (device) name.
    - ``node`` (``metrics.labels.node``, default ``"nodename"``): label holding the
      node name.

    The three names must differ. Equal names would merge distinct series into one
    (checked by the semantic validation).
    """

    vmid: str = "vmid"
    device: str = "instance"
    node: str = "nodename"


@dataclass(frozen=True, slots=True)
class MetricsConfig:
    """Prometheus metric names and query settings, from the ``metrics`` block.

    Metric names (strings). The defaults are the ``blockstat_*`` counters:

    - ``read_ops`` (``metrics.read_ops``): read operation counter.
    - ``write_ops`` (``metrics.write_ops``): write operation counter.
    - ``read_bytes`` (``metrics.read_bytes``): bytes-read counter.
    - ``write_bytes`` (``metrics.write_bytes``): bytes-written counter.
    - ``read_time_ns`` (``metrics.read_time_ns``): cumulative read time counter, in
      nanoseconds.
    - ``write_time_ns`` (``metrics.write_time_ns``): cumulative write time counter,
      in nanoseconds.

    Other fields:

    - ``labels`` (``metrics.labels``): label names, see :class:`MetricLabels`.
    - ``rate_window_seconds`` (``metrics.rate_window``, duration, default ``"5m"``,
      that is 300 seconds): window of the ``rate()`` query. It must be at least four
      times ``pvestatd_push_interval_seconds``.
    - ``step_seconds`` (``metrics.step``, duration, default ``"5m"``, that is 300
      seconds): resolution of the range query.
    - ``pvestatd_push_interval_seconds`` (``metrics.pvestatd_push_interval``,
      duration, default ``"10s"``): interval at which pvestatd writes the counters.
    - ``extra_selector`` (``metrics.extra_selector``, string or null, default None):
      extra label matcher for the metric selectors. It is used as written.
    """

    read_ops: str = "blockstat_rd_operations"
    write_ops: str = "blockstat_wr_operations"
    read_bytes: str = "blockstat_rd_bytes"
    write_bytes: str = "blockstat_wr_bytes"
    read_time_ns: str = "blockstat_rd_total_time_ns"
    write_time_ns: str = "blockstat_wr_total_time_ns"
    labels: MetricLabels = field(default_factory=MetricLabels)
    rate_window_seconds: float = 300.0
    step_seconds: float = 300.0
    pvestatd_push_interval_seconds: float = 10.0
    extra_selector: str | None = None


@dataclass(frozen=True, slots=True)
class WindowConfig:
    """How much history the load model reads, from the ``window`` block.

    - ``lookback_seconds`` (``window.lookback``, duration, default ``"24h"``, that
      is 86400 seconds): length of the history window. Must cover the forecast
      model's needs (checked by the semantic validation).
    - ``quantile`` (``window.quantile``, number strictly between 0 and 1, default
      0.95): quantile of the per-disk load series taken over the window.
    - ``min_coverage`` (``window.min_coverage``, number from above 0 up to 1,
      default 0.80): fraction of the window that must hold samples. A disk below
      this fraction is flagged. Its load falls back to its last known load in
      ``state.json``, or to 0.0 when none is known.
    """

    lookback_seconds: float = 86400.0
    quantile: float = 0.95
    min_coverage: float = 0.80


@dataclass(frozen=True, slots=True)
class LoadWeights:
    """Weights and factors that turn the raw I/O counters into one load value per
    disk, from the ``load_weights`` block.

    For each disk, the raw measures are I/O time, operations and bytes. Each
    measure is divided by the group total of that measure, which gives three
    shares. The load is the weighted mean of the three shares, multiplied by the
    group total of the I/O time measure. The weights are dimensionless.

    - ``iotime`` (``load_weights.iotime``, default 1.0): weight of the I/O time share.
    - ``ops`` (``load_weights.ops``, default 0.0): weight of the operations share.
    - ``bytes`` (``load_weights.bytes``, default 0.0): weight of the bytes share.
    - ``read_factor`` (``load_weights.read_factor``, default 1.0): multiplier of the
      read counters before they are summed with the write counters.
    - ``write_factor`` (``load_weights.write_factor``, default 1.0): multiplier of
      the write counters before they are summed with the read counters.

    All weights are at least 0. When the three weights sum to 0, every disk has
    load 0.
    """

    iotime: float = 1.0
    ops: float = 0.0
    bytes: float = 0.0
    read_factor: float = 1.0
    write_factor: float = 1.0


@dataclass(frozen=True, slots=True)
class FreeSpaceValue:
    """One parsed-but-unresolved ``free_space.soft``/``.hard`` entry
    (section 5.3.1's grammar): either an absolute byte count or a
    percentage of the storage's own capacity. Exactly one field is set.
    Percent resolution needs ``C_s``, which is only known once the cluster
    inventory is loaded (topology.py, after pattern expansion) -- this type
    is what a resolved-later value looks like before that point, the same
    role a ``/…/`` pattern plays for storage ids.
    """

    absolute_bytes: int | None = None
    percent: float | None = None  # 0 <= percent < 100, section 5.3.1's grammar


@dataclass(frozen=True, slots=True)
class StorageConfig:
    """One storage entry in a group, from ``groups[].storages[]``.

    - ``id`` (``groups[].storages[].id``, string, required): PVE storage id, or a
      pattern written as ``/regex/``.
    - ``capability_weight`` (``groups[].storages[].capability_weight``, number above
      0, default 1.0): relative capability of the storage. The load of a storage
      is divided by this weight.
    - ``reserve_factor`` (``groups[].storages[].reserve_factor``, number at least 0
      or null, default None): snapshot reserve factor for this storage. None
      inherits ``snapshot_reserve.factor``.
    - ``free_space_soft`` (``groups[].storages[].free_space.soft``): free-space
      floor at the plan endpoint. None inherits the global ``free_space.soft``.
    - ``free_space_hard`` (``groups[].storages[].free_space.hard``): free-space floor
      at every instant of a move. None inherits the global ``free_space.hard``.
    - ``enforce_format`` (``groups[].storages[].enforce_format``, ``"raw"``,
      ``"qcow2"`` or null, default None): format that every disk moved onto this
      storage must have. None keeps the source format.
    """

    id: str
    capability_weight: float = 1.0
    reserve_factor: float | None = None
    # None means inherit the group's free_space.soft/.hard -- the same
    # per-storage-null-means-inherit rule reserve_factor already has
    # (section 5.3.1).
    free_space_soft: FreeSpaceValue | None = None
    free_space_hard: FreeSpaceValue | None = None
    # Section 5.3.2: the format every disk moved onto this storage arrives in
    # (``"raw"`` or ``"qcow2"``), or None to preserve the source's format.
    enforce_format: str | None = None


def _parse_free_space_value(raw: Any, *, where: str) -> FreeSpaceValue | None:
    """Parse one ``free_space.soft``/``.hard`` entry (section 5.3.1's
    grammar). ``None`` (written or absent) is returned as ``None`` --
    callers decide what that means at their level: the global default (an
    absolute 0 for ``soft``, "= soft" for ``hard``) or per-storage
    inheritance.

    A string ending in ``%`` is a percentage, ``0 <= N < 100`` -- rejected
    here, at parse time, rather than left to the ``soft_s < C_s`` check
    once the cluster is known: ``100%`` is a typo, not a policy, and the
    grammar itself is where it belongs. Anything else goes through the same
    unit parser as ``migration.bwlimit_bytes_per_sec``.
    """
    if raw is None:
        return None
    if isinstance(raw, str) and raw.strip().endswith("%"):
        text = raw.strip()[:-1]
        try:
            percent = float(text)
        except ValueError as exc:
            raise ConfigError(f"{where}: {raw!r} is not a valid percentage") from exc
        if not (0 <= percent < 100):
            raise ConfigError(f"{where}: {raw!r} must be at least 0% and strictly below 100%")
        return FreeSpaceValue(percent=percent)
    return FreeSpaceValue(absolute_bytes=parse_size_bytes(raw))


def is_storage_pattern(storage_id: str) -> bool:
    """A ``storages[].id`` value is a pattern iff it both begins and ends
    with ``/`` (section 11.4). PVE storage ids never contain ``/``, so a
    value wrapped in slashes cannot collide with a literal one -- it can
    only have been meant as a pattern.
    """
    return len(storage_id) >= 2 and storage_id.startswith("/") and storage_id.endswith("/")


def storage_pattern_text(storage_id: str) -> str:
    """The regular expression text of a pattern entry, its two ``/``
    delimiters stripped. Only meaningful when :func:`is_storage_pattern` is
    True for ``storage_id``.
    """
    return storage_id[1:-1]


@dataclass(frozen=True, slots=True)
class GroupConfig:
    """A balancing group, one entry of ``groups[]``.

    - ``name`` (``groups[].name``, string, required): unique group name.
    - ``storages`` (``groups[].storages``, list): the storages that the group
      balances against each other, see :class:`StorageConfig`. A group needs at
      least two storages.

    Disks move only between storages of the same group.
    """

    name: str
    storages: tuple[StorageConfig, ...] = ()


@dataclass(frozen=True, slots=True)
class SnapshotReserveConfig:
    """Snapshot reserve rule, from the ``snapshot_reserve`` block.

    - ``factor`` (``snapshot_reserve.factor``, number at least 0, default 2.0): the
      reserve that a storage keeps free is ``factor`` times the size of the largest
      disk on that storage. A storage's own ``reserve_factor`` replaces this value.
    - ``count_foreign_volumes`` (``snapshot_reserve.count_foreign_volumes``,
      boolean, default True): when True, volumes that the tool does not manage are
      counted in the reserve computation.
    - ``split_vm_footprint_bytes`` (``snapshot_reserve.split_vm_footprint``, size
      or null, default ``"2TiB"``): the most of one VM that one storage should hold.
      Null turns the split rule off. Must be above 0 when set.
    """

    factor: float = 2.0
    count_foreign_volumes: bool = True
    # Section 5.3.3's ``T``: the most of one VM that one storage should hold. ``None`` switches
    # the split rule (C9), the ``mu`` term and the split gate off.
    split_vm_footprint_bytes: int | None = 2 * (1 << 40)


@dataclass(frozen=True, slots=True)
class FreeSpaceConfig:
    """Section 5.3.1's global ``free_space`` block. ``soft`` defaults to an
    absolute 0 -- no requirement beyond the snapshot reserve, the
    pre-section-5.3.1 behaviour. ``hard`` defaults to ``None``, meaning
    ``hard_s = soft_s`` for every storage that does not override it: no
    transient dip below ``soft`` at all, the conservative reading."""

    soft: FreeSpaceValue = field(default_factory=lambda: FreeSpaceValue(absolute_bytes=0))
    hard: FreeSpaceValue | None = None


@dataclass(frozen=True, slots=True)
class GatesConfig:
    """Thresholds and cooldowns that decide whether a run plans moves, from the
    ``gates`` block.

    - ``drift_threshold`` (``gates.drift_threshold``, number from 0 to 1, default
      0.10): drift is the L1 distance between the current load vector and the last
      recorded load vector, divided by the L1 norm of the last recorded load vector.
      A drift below this value does not trigger a plan.
    - ``imbalance_threshold`` (``gates.imbalance_threshold``, number from 0 to 1,
      default 0.20): imbalance at or above this value triggers a plan.
    - ``capacity_spread_threshold`` (``gates.capacity_spread_threshold``, number
      above 0 or null, default 0.25): spread of the fill fraction across storages.
      Null disables the capacity gate.
    - ``cooldown_per_disk_seconds`` (``gates.cooldown_per_disk``, duration, default
      ``"24h"``, that is 86400 seconds): time after a move before the same disk may
      move again.
    - ``cooldown_per_storage_seconds`` (``gates.cooldown_per_storage``, duration,
      default ``"1h"``, that is 3600 seconds): time after a move before the same
      storage takes part in another move.
    """

    drift_threshold: float = 0.10
    imbalance_threshold: float = 0.20
    # None disables the capacity gate outright (section 6); 0.25 default.
    capacity_spread_threshold: float | None = 0.25
    cooldown_per_disk_seconds: float = 86400.0
    cooldown_per_storage_seconds: float = 3600.0


@dataclass(frozen=True, slots=True)
class MigrationConfig:
    """Cost model and limits for one disk move, from the ``migration`` block.

    - ``bwlimit_bytes_per_sec`` (``migration.bwlimit_bytes_per_sec``, size in bytes
      per second, default 209715200, that is 200 MiB/s): bandwidth limit of one
      disk copy.
    - ``source_load_weight`` (``migration.source_load_weight``, number at least 0,
      default 1.0): weight of the load that the copy puts on the source storage.
    - ``target_load_weight`` (``migration.target_load_weight``, number at least 0,
      default 1.0): weight of the load that the copy puts on the target storage.
    - ``payback_horizon_seconds`` (``migration.payback_horizon``, duration, default
      ``"365d"``, that is 31536000 seconds): time over which a move must repay its
      cost. Set it near the real lifetime of a placement. Values below 30 days are
      warned about.
    - ``payback_ratio`` (``migration.payback_ratio``, number above 0, default 10.0):
      the benefit of a plan must be at least ``payback_ratio`` times its total
      move cost.
    - ``max_single_move_duration_seconds`` (``migration.max_single_move_duration``,
      duration, default ``"6h"``, that is 21600 seconds): longest time that one move
      may take.
    - ``account_saferemove_wipe`` (``migration.account_saferemove_wipe``, boolean,
      default True): add the cost of the wipe that saferemove runs on the source
      volume.
    - ``wipe_load_weight`` (``migration.wipe_load_weight``, number at least 0,
      default 1.0): weight of that wipe load.
    - ``assume_thick_provisioning`` (``migration.assume_thick_provisioning``,
      boolean, default True): kept only so old configs still load. False is refused:
      the tool never models over-provisioning, so every disk counts at its
      provisioned size.
    - ``tiny_disk_bytes`` (``migration.tiny_disk_bytes``, size in bytes, default
      ``67108864``, that is 64 MiB): disks smaller than this carry no move cost and
      need no payback check. Zero charges every disk.
    """

    bwlimit_bytes_per_sec: int = 209_715_200  # 200 MiB/s
    source_load_weight: float = 1.0
    target_load_weight: float = 1.0
    payback_horizon_seconds: float = 31_536_000.0  # 365d
    payback_ratio: float = 10.0
    max_single_move_duration_seconds: float = 21600.0  # 6h
    account_saferemove_wipe: bool = True
    wipe_load_weight: float = 1.0
    assume_thick_provisioning: bool = True
    # Below this size, a disk carries zero beta/gamma and needs no payback
    # verdict (section 5.4 D^big, section 7.1/7.3) -- comfortably above an
    # EFI var store or TPM state, far below anything the payback rule was
    # written for. 0 restores the pre-section-7.2 accounting for every disk
    # (every disk charged a full migration, however small).
    tiny_disk_bytes: int = 67_108_864  # 64 MiB


@dataclass(frozen=True, slots=True)
class ObjectiveConfig:
    """Weights of the optimisation objective, from the ``objective`` block.

    The MILP and the heuristic both minimise a sum of these terms. Units are given
    per term.

    - ``spread_metric`` (``objective.spread_metric``, ``"l1"`` or ``"minmax"``,
      default ``"l1"``): form of the spread term. ``l1`` sums the absolute
      deviation of each storage load from the group average. ``minmax`` minimises
      the largest storage load.
    - ``alpha_spread`` (``objective.alpha_spread``, number at least 0, default 1.0):
      weight of the spread term.
    - ``beta_move_count`` (``objective.beta_move_count``, number at least 0, default
      0.25): cost per disk moved, for disks at or above ``migration.tiny_disk_bytes``.
    - ``gamma_move_bytes_per_tib`` (``objective.gamma_move_bytes_per_tib``, number at
      least 0, default 0.05): cost per TiB of disk moved, for disks at or above
      ``migration.tiny_disk_bytes``.
    - ``kappa_vm_affinity`` (``objective.kappa_vm_affinity``, number at least 0,
      default 0.50): cost per VM for each storage that the VM uses beyond the first.
      It keeps the disks of one VM on few storages.
    - ``delta_capacity_spread`` (``objective.delta_capacity_spread``, number at least
      0, default 0.5): weight of the capacity spread term, per TiB.
    - ``mu_vm_split_per_tib`` (``objective.mu_vm_split_per_tib``, number at least 0,
      default 1.0): weight, per TiB of split excess, of the large-VM split rule.
    - ``affinity_counts_pinned_disks`` (``objective.affinity_counts_pinned_disks``,
      boolean, default True): when True, pinned disks count in the affinity term of
      their VM. When False, only movable disks count.
    - ``reserve_violation_penalty`` (``objective.reserve_violation_penalty``, number
      at least 0, default 1000.0): cost per TiB of snapshot reserve shortfall in the
      heuristic objective.
    """

    spread_metric: str = "l1"
    alpha_spread: float = 1.0
    beta_move_count: float = 0.25
    gamma_move_bytes_per_tib: float = 0.05
    kappa_vm_affinity: float = 0.50
    delta_capacity_spread: float = 0.5
    # Section 5.3.3 ``mu``: weight, per TiB of split excess, of the large-VM split rule.
    mu_vm_split_per_tib: float = 1.0
    # Section 5.3 (C3): default True -- a pinned disk is a fixed anchor its
    # VM's movable disks can be drawn back to, not a veto. See the plan's
    # own note on why the opposite default was wrong.
    affinity_counts_pinned_disks: bool = True
    reserve_violation_penalty: float = 1000.0


@dataclass(frozen=True, slots=True)
class SolverConfig:
    """Solver selection and limits, from the ``solver`` block.

    - ``backend`` (``solver.backend``, ``"auto"``, ``"cbc"`` or ``"heuristic"``,
      default ``"auto"``): ``cbc`` solves the MILP with CBC through PuLP. ``heuristic``
      never calls the MILP. ``auto`` tries CBC and falls back to the heuristic when
      CBC cannot run.
    - ``time_limit_seconds`` (``solver.time_limit_seconds``, duration, default 60):
      time limit of one MILP solve.
    - ``mip_gap`` (``solver.mip_gap``, number from 0 to 1, default 0.02): relative
      optimality gap at which the MILP stops.
    - ``heuristic_iterations`` (``solver.heuristic_iterations``, integer above 0,
      default 5000): iteration limit of the heuristic.
    """

    backend: str = "auto"
    time_limit_seconds: float = 60.0
    mip_gap: float = 0.02
    heuristic_iterations: int = 5000


@dataclass(frozen=True, slots=True)
class LocksConfig:
    """Handling of VM and disk locks during execution, from
    ``execution.locks``.

    - ``wait_timeout_seconds`` (``execution.locks.wait_timeout``, duration, default
      ``"4h"``, that is 14400 seconds): longest wait for a VM lock to clear.
    - ``poll_interval_seconds`` (``execution.locks.poll_interval``, duration,
      default ``"30s"``): interval between lock checks.
    - ``on_timeout`` (``execution.locks.on_timeout``, ``"skip"`` or ``"abort"``,
      default ``"skip"``): action when the wait ends. ``skip`` records the move as
      skipped and the run continues. ``abort`` records the move as failed and stops
      the whole run.
    - ``task_retry_limit`` (``execution.locks.task_retry_limit``, integer at least 0,
      default 2): number of retries when a move task fails at once on a lock held
      by a cleanup task.
    - ``task_retry_backoff_seconds`` (``execution.locks.task_retry_backoff``,
      duration, default ``"15s"``): delay before each retry.
    """

    wait_timeout_seconds: float = 14400.0  # 4h
    poll_interval_seconds: float = 30.0
    on_timeout: str = "skip"
    # section 9.3 point 3: a `move_disk` *task* can fail immediately with
    # PVE's own "can't lock file '...' - got timeout" -- a different lock
    # than `wait_timeout` above waits out, momentarily still held by
    # another task's cleanup even after the config `lock:` attribute has
    # already cleared. Retried, not waited on, since there is nothing to
    # poll that shows it coming.
    task_retry_limit: int = 2
    task_retry_backoff_seconds: float = 15.0


@dataclass(frozen=True, slots=True)
class SourceReleaseConfig:
    """When the tool waits for the source volume to disappear, from
    ``execution.source_release``.

    A move is not finished until the source volume is gone and the VM config is
    unlocked.

    - ``wait`` (``execution.source_release.wait``, boolean, default True): wait for
      the source volume to disappear before the move counts as done.
    - ``timeout_seconds`` (``execution.source_release.timeout``, duration, default
      ``"48h"``, that is 172800 seconds): longest wait for the source volume. A
      source still present after this time gives status ``draining``, which is not
      a failure.
    """

    wait: bool = True
    timeout_seconds: float = 172800.0  # 48h


@dataclass(frozen=True, slots=True)
class TimeWindow:
    """One allowed time window for ``auto`` mode, an entry of
    ``execution.time_windows[]``.

    - ``days`` (``execution.time_windows[].days``, list of ``"mon"`` to ``"sun"``,
      default all seven days): weekdays on which the window is open. The day is the
      day on which the window starts.
    - ``start`` (``execution.time_windows[].start``, string ``HH:MM`` in 24-hour
      time): start of the window, in the host's local time.
    - ``end`` (``execution.time_windows[].end``, string ``HH:MM``): end of the window,
      in local time. ``end`` must differ from ``start``. The semantic validation
      rejects equal values because they would mean both "never" and "always".

    A window with ``end`` earlier than ``start`` crosses midnight.
    """

    days: tuple[str, ...]
    start: str
    end: str


@dataclass(frozen=True, slots=True)
class ExecutionConfig:
    """How and when moves run, from the ``execution`` block.

    - ``mode`` (``execution.mode``, ``"dry-run"``, ``"confirm"`` or ``"auto"``,
      default ``"dry-run"``): ``dry-run`` only reports the plan and issues nothing.
      ``confirm`` asks the operator before each move. ``auto`` runs the moves
      without asking. Only ``auto`` respects ``time_windows``.
    - ``max_concurrent_migrations`` (``execution.max_concurrent_migrations``, integer
      at least 1, default 1): moves in flight at once. Values above 1 apply only in
      ``auto`` mode.
    - ``max_migrations_per_run`` (``execution.max_migrations_per_run``, integer at
      least 1, default 5): moves started in one run.
    - ``max_concurrent_per_storage`` (``execution.max_concurrent_per_storage``,
      integer at least 1, default 1): moves in flight that use the same storage.
      Values above 1 apply only in ``auto`` mode.
    - ``max_replans_per_run`` (``execution.max_replans_per_run``, integer at least 0,
      default 3): number of times one run may plan again after the plan no longer
      matches the cluster.
    - ``abort_on_failure`` (``execution.abort_on_failure``, boolean, default True):
      stop the run when one move task fails.
    - ``poll_interval_seconds`` (``execution.poll_interval_seconds``, number above 0,
      default 10): seconds between checks of a running move task.
    - ``api_outage_timeout_seconds`` (``execution.api_outage_timeout``, duration,
      default ``"1h"``, that is 3600 seconds): how long one PVE read may keep failing
      before the run gives up. Zero turns the retries off.
    - ``locks`` (``execution.locks``): see :class:`LocksConfig`.
    - ``source_release`` (``execution.source_release``): see
      :class:`SourceReleaseConfig`.
    - ``time_windows`` (``execution.time_windows``, list): see :class:`TimeWindow`.
      Empty means ``auto`` mode may act at any time.
    """

    mode: str = "dry-run"
    max_concurrent_migrations: int = 1
    max_migrations_per_run: int = 5
    max_concurrent_per_storage: int = 1
    max_replans_per_run: int = 3
    abort_on_failure: bool = True
    poll_interval_seconds: float = 10.0
    # How long one PVE API read may keep failing because the API is
    # unreachable (network maintenance, a node restarting) before the run
    # gives up. Applies only while executing; 0 disables the retrying.
    api_outage_timeout_seconds: float = 3600.0
    locks: LocksConfig = field(default_factory=LocksConfig)
    source_release: SourceReleaseConfig = field(default_factory=SourceReleaseConfig)
    time_windows: tuple[TimeWindow, ...] = ()


@dataclass(frozen=True, slots=True)
class ExcludeConfig:
    """Disks and VMs that the tool never moves, from the ``exclude`` block.

    - ``vmids`` (``exclude.vmids``, list of integers, default empty): VM ids to
      exclude.
    - ``disks`` (``exclude.disks``, list of strings, default empty): disk names to
      exclude.
    - ``storages`` (``exclude.storages``, list of strings, default empty): storage
      ids whose disks are not moved.
    - ``tags`` (``exclude.tags``, list of strings, default ``["no-drs"]``): VMs with
      one of these tags are excluded.
    - ``skip_vms_with_snapshots`` (``exclude.skip_vms_with_snapshots``, boolean,
      default True): always True. False is refused, because PVE rejects a disk move
      for a VM with snapshots.
    - ``stopped`` (``exclude.stopped``, boolean, default True): always True. False is
      refused. The disks of a stopped VM are never moved, because backup and
      replication tools track volumes by location.
    - ``include_unused_disks`` (``exclude.include_unused_disks``, boolean, default
      True): when False, unused disks (device names starting with ``unused``) are
      excluded from planning.
    """

    vmids: tuple[int, ...] = ()
    disks: tuple[str, ...] = ()
    storages: tuple[str, ...] = ()
    tags: tuple[str, ...] = ("no-drs",)
    skip_vms_with_snapshots: bool = True
    stopped: bool = True
    include_unused_disks: bool = True


@dataclass(frozen=True, slots=True)
class ReportConfig:
    """Report settings, from the ``report`` block.

    - ``warn_pinned_load_fraction`` (``report.warn_pinned_load_fraction``, number
      above 0 and at most 1, default 0.25): the report warns when pinned disks carry
      more than this fraction of a storage's load.
    """

    warn_pinned_load_fraction: float = 0.25


@dataclass(frozen=True, slots=True)
class StateConfig:
    """Location of the persistent state file, from the ``state`` block.

    - ``path`` (``state.path``, path, default ``/var/lib/pve-storage-drs/state.json``):
      file where the tool keeps its persistent state between runs.
    """

    path: str = "/var/lib/pve-storage-drs/state.json"


@dataclass(frozen=True, slots=True)
class HoltWintersConfig:
    """Holt-Winters model settings, from ``forecast.holt_winters``.

    - ``seasonal_periods`` (``forecast.holt_winters.seasonal_periods``, integer above
      0, default 288): number of samples in one season. At the default step of 5
      minutes, 288 samples is one day.
    - ``trend`` (``forecast.holt_winters.trend``, ``"add"``, ``"mul"`` or ``"none"``,
      default ``"none"``): trend component.
    - ``seasonal`` (``forecast.holt_winters.seasonal``, ``"add"``, ``"mul"`` or
      ``"none"``, default ``"add"``): seasonal component.
    """

    seasonal_periods: int = 288
    trend: str = "none"
    seasonal: str = "add"


@dataclass(frozen=True, slots=True)
class ForecastConfig:
    """Forecast settings, from the ``forecast`` block.

    - ``model`` (``forecast.model``, ``"quantile"`` or ``"holt_winters"``, default
      ``"quantile"``): ``quantile`` takes the quantile of the window. ``holt_winters``
      fits a seasonal model and takes a quantile of its forecast.
    - ``holt_winters`` (``forecast.holt_winters``): settings of the Holt-Winters
      model, see :class:`HoltWintersConfig`. They apply only when ``model`` is
      ``holt_winters``.
    """

    model: str = "quantile"
    holt_winters: HoltWintersConfig = field(default_factory=HoltWintersConfig)


@dataclass(frozen=True, slots=True)
class SupportConfig:
    """Section 16.7. Diagnostic-bundle support: the anonymization salt, the
    default ``collect-testdata`` output directory, the hard refusal ceiling
    on a series capture, and the capture range (``"auto"`` for section 16.2's
    computed maximum of what ``holt_winters`` needs, or an
    explicit ``units.parse_duration_seconds()``-parseable duration)."""

    salt_path: str = "/var/lib/pve-storage-drs/anonymization-salt"
    bundle_dir: str = "/var/lib/pve-storage-drs/testdata"
    max_series_points: int = 5_000_000
    capture_range: str = "auto"


@dataclass(frozen=True, slots=True)
class MonitoringConfig:
    """Section 2.4. ``status_file`` is where ``apply`` leaves a one-run status
    report in the format the ``check_statusfile`` monitoring plugin reads
    (first line ``OK``/``WARNING``/``CRITICAL``/``UNKNOWN``, then the plugin
    output); ``None`` (the default) writes nothing."""

    status_file: str | None = None


@dataclass(frozen=True, slots=True)
class Config:
    """The whole validated configuration, one field per top-level YAML key.

    Each field holds one section of the file. Durations are stored in seconds and
    sizes in bytes. Each section class lists its own YAML keys:

    - ``schema_version`` (``schema_version``, integer, default 1): must match the
      major version this build supports.
    - ``proxmox`` (``proxmox``): :class:`ProxmoxConfig`.
    - ``prometheus`` (``prometheus``): :class:`PrometheusConfig`.
    - ``metrics`` (``metrics``): :class:`MetricsConfig`.
    - ``window`` (``window``): :class:`WindowConfig`.
    - ``load_weights`` (``load_weights``): :class:`LoadWeights`.
    - ``groups`` (``groups``): tuple of :class:`GroupConfig`.
    - ``snapshot_reserve`` (``snapshot_reserve``): :class:`SnapshotReserveConfig`.
    - ``free_space`` (``free_space``): :class:`FreeSpaceConfig`. The global
      free-space floors. Each is an absolute size or a percentage of the storage
      capacity.
    - ``gates`` (``gates``): :class:`GatesConfig`.
    - ``migration`` (``migration``): :class:`MigrationConfig`.
    - ``objective`` (``objective``): :class:`ObjectiveConfig`.
    - ``solver`` (``solver``): :class:`SolverConfig`.
    - ``execution`` (``execution``): :class:`ExecutionConfig`.
    - ``exclude`` (``exclude``): :class:`ExcludeConfig`.
    - ``report`` (``report``): :class:`ReportConfig`.
    - ``state`` (``state``): :class:`StateConfig`.
    - ``forecast`` (``forecast``): :class:`ForecastConfig`.
    - ``support`` (``support``): :class:`SupportConfig`.
    - ``monitoring`` (``monitoring``): :class:`MonitoringConfig`.

    The schema requires ``schema_version``, ``proxmox``, ``prometheus`` and ``groups``.
    Every other section is optional. A missing section takes the defaults of its
    class. This class raises nothing itself. :func:`load_config` raises
    :class:`ConfigError` when a value is invalid.
    """

    schema_version: int
    proxmox: ProxmoxConfig
    prometheus: PrometheusConfig
    metrics: MetricsConfig
    window: WindowConfig
    load_weights: LoadWeights
    groups: tuple[GroupConfig, ...]
    snapshot_reserve: SnapshotReserveConfig
    free_space: FreeSpaceConfig
    gates: GatesConfig
    migration: MigrationConfig
    objective: ObjectiveConfig
    solver: SolverConfig
    execution: ExecutionConfig
    exclude: ExcludeConfig
    report: ReportConfig
    state: StateConfig
    forecast: ForecastConfig
    support: SupportConfig
    monitoring: MonitoringConfig = MonitoringConfig()


@dataclass(frozen=True, slots=True)
class ResolvedConfig:
    """A loaded, validated config plus where it came from.

    ``path`` and ``sha256`` are logged on every run (IMPLEMENTATION_PLAN.md
    section 11: "every run logs the resolved path and the SHA-256 of the file
    it actually read"), and ``warnings`` are semantic issues that do not
    block a run but that the CLI must surface.
    """

    config: Config
    path: str
    sha256: str
    warnings: tuple[str, ...] = ()


# ------------------------------------------------------------------ resolving


def resolve_config_path(
    cli_path: str | None, env: Mapping[str, str] | None = None
) -> tuple[str, bool]:
    """Apply the section 11 resolution order.

    Returns ``(path, was_explicit)``. ``was_explicit`` is True for the
    ``--config``/env-var sources, where a read failure must never fall back
    to the default (section 11: "An explicitly requested config that is
    missing, unreadable or invalid is a hard failure").
    """
    if cli_path:
        return cli_path, True
    environ = env if env is not None else os.environ
    env_path = environ.get(ENV_CONFIG_VAR)
    if env_path:
        return env_path, True
    return DEFAULT_CONFIG_PATH, False


def load_config(
    cli_path: str | None = None,
    env: Mapping[str, str] | None = None,
    *,
    require_connection: bool = True,
) -> ResolvedConfig:
    """Resolve, read, parse and validate the configuration.

    See section 11 for resolution order and section 11.1 for the semantic
    rules applied after JSON-schema structural validation. Raises
    :class:`ConfigError` on any failure -- there is deliberately no
    warn-and-continue path (AGENTS.md section 6: "a misconfigured balancer
    moving production disks is worse than one that refuses to start").

    ``require_connection`` gates the one semantic rule that does not apply
    under ``--replay`` (section 16.5): a diagnostic bundle's ``config.yaml``
    deliberately omits ``proxmox.host``/``auth`` and ``prometheus.url``
    (section 16.3 -- "dropped, not blanked"), so ``cli.py`` passes ``False``
    when loading a bundle's own configuration. Every other caller keeps the
    default, which preserves today's behaviour: a missing host or URL is a
    hard failure before anything is planned.
    """
    environ = env if env is not None else os.environ
    path, was_explicit = resolve_config_path(cli_path, environ)

    try:
        with open(path, "rb") as fh:
            raw_bytes = fh.read()
    except OSError as exc:
        if was_explicit:
            raise ConfigError(f"cannot read config {path!r}: {exc}") from exc
        raise ConfigError(
            f"cannot read config {path!r}: {exc}. "
            "See config/drs.example.yaml in the source tree for a fully "
            "annotated reference, or pass --config to use a different path."
        ) from exc

    sha256 = hashlib.sha256(raw_bytes).hexdigest()

    yaml = YAML(typ="safe")
    try:
        raw: Any = yaml.load(raw_bytes)
    except YAMLError as exc:
        raise ConfigError(f"cannot parse config {path!r}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"config {path!r} must be a YAML mapping at the top level")

    _validate_schema(raw)
    config = _build_config(raw, environ)
    warnings = _validate_semantics(config, require_connection=require_connection)

    return ResolvedConfig(config=config, path=path, sha256=sha256, warnings=tuple(warnings))


# -------------------------------------------------------------- jsonschema


def _load_schema() -> dict[str, Any]:
    text = (
        importlib.resources.files("proxmox_storage_drs")
        .joinpath("config_schema.json")
        .read_text(encoding="utf-8")
    )
    schema: dict[str, Any] = json.loads(text)
    return schema


def _validate_schema(raw: dict[str, Any]) -> None:
    schema = _load_schema()
    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    errors = sorted(validator.iter_errors(raw), key=lambda e: list(e.absolute_path))
    if errors:
        messages = [
            f"{'.'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in errors
        ]
        raise ConfigError("config validation failed:\n  " + "\n  ".join(messages))


# ------------------------------------------------------------ building


def _build_config(raw: dict[str, Any], environ: Mapping[str, str]) -> Config:
    proxmox_raw = raw.get("proxmox", {})
    auth_raw = proxmox_raw.get("auth", {})
    password = auth_raw.get("password")
    if password is None:
        password = environ.get(ENV_PASSWORD_VAR)
    token_secret = auth_raw.get("token_secret")
    if token_secret is None:
        token_secret = environ.get(ENV_TOKEN_SECRET_VAR)
    auth = AuthConfig(
        username=auth_raw.get("username"),
        password=password,
        token_id=auth_raw.get("token_id"),
        token_secret=token_secret,
    )
    proxmox = ProxmoxConfig(
        host=proxmox_raw.get("host", ""),
        port=proxmox_raw.get("port", 8006),
        verify_ssl=proxmox_raw.get("verify_ssl", True),
        ca_file=proxmox_raw.get("ca_file"),
        auth=auth,
        ticket_refresh_seconds=parse_duration_seconds(
            proxmox_raw.get("ticket_refresh_seconds", 3000)
        ),
        read_workers=proxmox_raw.get("read_workers", 12),
    )

    prom_raw = raw.get("prometheus", {})
    prometheus = PrometheusConfig(
        url=prom_raw.get("url", ""),
        timeout_seconds=parse_duration_seconds(prom_raw.get("timeout_seconds", 30)),
        username=prom_raw.get("username"),
        password=prom_raw.get("password"),
        bearer_token=prom_raw.get("bearer_token"),
    )

    metrics_raw = raw.get("metrics", {})
    labels_raw = metrics_raw.get("labels", {})
    labels = MetricLabels(
        vmid=labels_raw.get("vmid", "vmid"),
        device=labels_raw.get("device", "instance"),
        node=labels_raw.get("node", "nodename"),
    )
    metrics = MetricsConfig(
        read_ops=metrics_raw.get("read_ops", "blockstat_rd_operations"),
        write_ops=metrics_raw.get("write_ops", "blockstat_wr_operations"),
        read_bytes=metrics_raw.get("read_bytes", "blockstat_rd_bytes"),
        write_bytes=metrics_raw.get("write_bytes", "blockstat_wr_bytes"),
        read_time_ns=metrics_raw.get("read_time_ns", "blockstat_rd_total_time_ns"),
        write_time_ns=metrics_raw.get("write_time_ns", "blockstat_wr_total_time_ns"),
        labels=labels,
        rate_window_seconds=parse_duration_seconds(metrics_raw.get("rate_window", "5m")),
        step_seconds=parse_duration_seconds(metrics_raw.get("step", "5m")),
        pvestatd_push_interval_seconds=parse_duration_seconds(
            metrics_raw.get("pvestatd_push_interval", "10s")
        ),
        extra_selector=metrics_raw.get("extra_selector"),
    )

    window_raw = raw.get("window", {})
    window = WindowConfig(
        lookback_seconds=parse_duration_seconds(window_raw.get("lookback", "24h")),
        quantile=window_raw.get("quantile", 0.95),
        min_coverage=window_raw.get("min_coverage", 0.80),
    )

    lw_raw = raw.get("load_weights", {})
    load_weights = LoadWeights(
        iotime=lw_raw.get("iotime", 1.0),
        ops=lw_raw.get("ops", 0.0),
        bytes=lw_raw.get("bytes", 0.0),
        read_factor=lw_raw.get("read_factor", 1.0),
        write_factor=lw_raw.get("write_factor", 1.0),
    )

    groups = tuple(
        GroupConfig(
            name=g["name"],
            storages=tuple(
                StorageConfig(
                    id=s["id"],
                    capability_weight=s.get("capability_weight", 1.0),
                    reserve_factor=s.get("reserve_factor"),
                    free_space_soft=_parse_free_space_value(
                        s.get("free_space", {}).get("soft"),
                        where=f"groups[{g['name']!r}].storages[{s['id']!r}].free_space.soft",
                    ),
                    enforce_format=s.get("enforce_format"),
                    free_space_hard=_parse_free_space_value(
                        s.get("free_space", {}).get("hard"),
                        where=f"groups[{g['name']!r}].storages[{s['id']!r}].free_space.hard",
                    ),
                )
                for s in g.get("storages", [])
            ),
        )
        for g in raw.get("groups", [])
    )

    sr_raw = raw.get("snapshot_reserve", {})
    snapshot_reserve = SnapshotReserveConfig(
        factor=sr_raw.get("factor", 2.0),
        count_foreign_volumes=sr_raw.get("count_foreign_volumes", True),
        split_vm_footprint_bytes=(
            None
            if "split_vm_footprint" in sr_raw and sr_raw["split_vm_footprint"] is None
            else parse_size_bytes(sr_raw.get("split_vm_footprint", "2TiB"))
        ),
    )

    fs_raw = raw.get("free_space", {})
    free_space = FreeSpaceConfig(
        soft=_parse_free_space_value(fs_raw.get("soft"), where="free_space.soft")
        or FreeSpaceValue(absolute_bytes=0),
        hard=_parse_free_space_value(fs_raw.get("hard"), where="free_space.hard"),
    )

    gates_raw = raw.get("gates", {})
    gates = GatesConfig(
        drift_threshold=gates_raw.get("drift_threshold", 0.10),
        imbalance_threshold=gates_raw.get("imbalance_threshold", 0.20),
        capacity_spread_threshold=gates_raw.get("capacity_spread_threshold", 0.25),
        cooldown_per_disk_seconds=parse_duration_seconds(gates_raw.get("cooldown_per_disk", "24h")),
        cooldown_per_storage_seconds=parse_duration_seconds(
            gates_raw.get("cooldown_per_storage", "1h")
        ),
    )

    mig_raw = raw.get("migration", {})
    migration = MigrationConfig(
        bwlimit_bytes_per_sec=parse_size_bytes(mig_raw.get("bwlimit_bytes_per_sec", 209715200)),
        source_load_weight=mig_raw.get("source_load_weight", 1.0),
        target_load_weight=mig_raw.get("target_load_weight", 1.0),
        payback_horizon_seconds=parse_duration_seconds(mig_raw.get("payback_horizon", "365d")),
        payback_ratio=mig_raw.get("payback_ratio", 10.0),
        max_single_move_duration_seconds=parse_duration_seconds(
            mig_raw.get("max_single_move_duration", "6h")
        ),
        account_saferemove_wipe=mig_raw.get("account_saferemove_wipe", True),
        wipe_load_weight=mig_raw.get("wipe_load_weight", 1.0),
        assume_thick_provisioning=mig_raw.get("assume_thick_provisioning", True),
        tiny_disk_bytes=parse_size_bytes(mig_raw.get("tiny_disk_bytes", 67_108_864)),
    )

    obj_raw = raw.get("objective", {})
    objective = ObjectiveConfig(
        spread_metric=obj_raw.get("spread_metric", "l1"),
        alpha_spread=obj_raw.get("alpha_spread", 1.0),
        beta_move_count=obj_raw.get("beta_move_count", 0.25),
        gamma_move_bytes_per_tib=obj_raw.get("gamma_move_bytes_per_tib", 0.05),
        kappa_vm_affinity=obj_raw.get("kappa_vm_affinity", 0.50),
        delta_capacity_spread=obj_raw.get("delta_capacity_spread", 0.5),
        mu_vm_split_per_tib=obj_raw.get("mu_vm_split_per_tib", 1.0),
        affinity_counts_pinned_disks=obj_raw.get("affinity_counts_pinned_disks", True),
        reserve_violation_penalty=obj_raw.get("reserve_violation_penalty", 1000.0),
    )

    solver_raw = raw.get("solver", {})
    solver = SolverConfig(
        backend=solver_raw.get("backend", "auto"),
        time_limit_seconds=parse_duration_seconds(solver_raw.get("time_limit_seconds", 60)),
        mip_gap=solver_raw.get("mip_gap", 0.02),
        heuristic_iterations=solver_raw.get("heuristic_iterations", 5000),
    )

    exec_raw = raw.get("execution", {})
    locks_raw = exec_raw.get("locks", {})
    locks = LocksConfig(
        wait_timeout_seconds=parse_duration_seconds(locks_raw.get("wait_timeout", "4h")),
        poll_interval_seconds=parse_duration_seconds(locks_raw.get("poll_interval", "30s")),
        on_timeout=locks_raw.get("on_timeout", "skip"),
        task_retry_limit=locks_raw.get("task_retry_limit", 2),
        task_retry_backoff_seconds=parse_duration_seconds(
            locks_raw.get("task_retry_backoff", "15s")
        ),
    )
    sr2_raw = exec_raw.get("source_release", {})
    source_release = SourceReleaseConfig(
        wait=sr2_raw.get("wait", True),
        timeout_seconds=parse_duration_seconds(sr2_raw.get("timeout", "48h")),
    )
    time_windows = tuple(
        TimeWindow(
            days=tuple(tw.get("days", list(_DAY_NAMES))),
            start=tw["start"],
            end=tw["end"],
        )
        for tw in exec_raw.get("time_windows", [])
    )
    execution = ExecutionConfig(
        mode=exec_raw.get("mode", "dry-run"),
        max_concurrent_migrations=exec_raw.get("max_concurrent_migrations", 1),
        max_migrations_per_run=exec_raw.get("max_migrations_per_run", 5),
        max_concurrent_per_storage=exec_raw.get("max_concurrent_per_storage", 1),
        max_replans_per_run=exec_raw.get("max_replans_per_run", 3),
        abort_on_failure=exec_raw.get("abort_on_failure", True),
        poll_interval_seconds=parse_duration_seconds(exec_raw.get("poll_interval_seconds", 10)),
        api_outage_timeout_seconds=parse_duration_seconds(exec_raw.get("api_outage_timeout", "1h")),
        locks=locks,
        source_release=source_release,
        time_windows=time_windows,
    )

    excl_raw = raw.get("exclude", {})
    exclude = ExcludeConfig(
        vmids=tuple(excl_raw.get("vmids", [])),
        disks=tuple(excl_raw.get("disks", [])),
        storages=tuple(excl_raw.get("storages", [])),
        tags=tuple(excl_raw.get("tags", ["no-drs"])),
        skip_vms_with_snapshots=excl_raw.get("skip_vms_with_snapshots", True),
        stopped=excl_raw.get("stopped", True),
        include_unused_disks=excl_raw.get("include_unused_disks", True),
    )

    report_raw = raw.get("report", {})
    report = ReportConfig(
        warn_pinned_load_fraction=report_raw.get("warn_pinned_load_fraction", 0.25),
    )

    state_raw = raw.get("state", {})
    state = StateConfig(path=state_raw.get("path", "/var/lib/pve-storage-drs/state.json"))

    fc_raw = raw.get("forecast", {})
    hw_raw = fc_raw.get("holt_winters", {})
    holt_winters = HoltWintersConfig(
        seasonal_periods=hw_raw.get("seasonal_periods", 288),
        trend=hw_raw.get("trend", "none"),
        seasonal=hw_raw.get("seasonal", "add"),
    )
    forecast = ForecastConfig(
        model=fc_raw.get("model", "quantile"),
        holt_winters=holt_winters,
    )

    support_raw = raw.get("support", {})
    support = SupportConfig(
        salt_path=support_raw.get("salt_path", "/var/lib/pve-storage-drs/anonymization-salt"),
        bundle_dir=support_raw.get("bundle_dir", "/var/lib/pve-storage-drs/testdata"),
        max_series_points=support_raw.get("max_series_points", 5_000_000),
        capture_range=support_raw.get("capture_range", "auto"),
    )

    monitoring = MonitoringConfig(status_file=raw.get("monitoring", {}).get("status_file"))

    return Config(
        schema_version=raw.get("schema_version", 1),
        proxmox=proxmox,
        prometheus=prometheus,
        metrics=metrics,
        window=window,
        load_weights=load_weights,
        groups=groups,
        snapshot_reserve=snapshot_reserve,
        free_space=free_space,
        gates=gates,
        migration=migration,
        objective=objective,
        solver=solver,
        execution=execution,
        exclude=exclude,
        report=report,
        state=state,
        forecast=forecast,
        support=support,
        monitoring=monitoring,
    )


# ------------------------------------------------------------ semantic rules


def _check_schema_version(config: Config, errors: list[str]) -> None:
    if config.schema_version != SUPPORTED_SCHEMA_MAJOR:
        errors.append(
            f"schema_version {config.schema_version} is not supported; "
            f"this build understands major version {SUPPORTED_SCHEMA_MAJOR}"
        )


def _check_group_names_unique(config: Config, errors: list[str]) -> None:
    """Section 11.1: ``groups[].name`` is unique. A later group with the same
    name would silently replace the earlier one when the topology is built
    (keyed by name), hiding the earlier group's storages from every check."""
    seen: set[str] = set()
    for group in config.groups:
        if group.name in seen:
            errors.append(f"duplicate group name {group.name!r}: groups[].name must be unique")
        seen.add(group.name)


def _check_group_storage_membership(config: Config, errors: list[str]) -> None:
    """No storage twice in one group, and no storage in two groups.

    A disk's group would otherwise be ambiguous (section 11.1). This check
    compares raw entry text only -- it catches the same literal id (or the
    same pattern, character for character) written twice, but it cannot
    know which real storages two *different* ``/…/`` patterns match: that
    comparison needs the cluster's storage inventory, so it is done again,
    on the expanded result, once that inventory is available (section 11.4,
    ``topology._expand_and_validate_groups``).
    """
    seen_storages: dict[str, str] = {}
    for group in config.groups:
        group_storage_ids = [s.id for s in group.storages]
        if len(group_storage_ids) != len(set(group_storage_ids)):
            errors.append(f"group {group.name!r} lists the same storage id more than once")
        for storage_id in group_storage_ids:
            other = seen_storages.get(storage_id)
            if other is not None and other != group.name:
                errors.append(
                    f"storage {storage_id!r} appears in both group {other!r} "
                    f"and group {group.name!r}"
                )
            seen_storages[storage_id] = group.name


def _check_storage_patterns_compile(config: Config, errors: list[str]) -> None:
    """Section 11.4: every ``/…/`` pattern must compile as a Python regular
    expression, checked here at load time so a malformed one fails with the
    compiler's own message rather than surfacing later, once a cluster is
    involved, as an opaque "matches nothing".
    """
    for group in config.groups:
        for storage in group.storages:
            if not is_storage_pattern(storage.id):
                continue
            try:
                re.compile(storage_pattern_text(storage.id))
            except re.error as exc:
                errors.append(
                    f"group {group.name!r} storage pattern {storage.id!r} does not "
                    f"compile as a regular expression: {exc}"
                )


def _check_group_size(config: Config, errors: list[str]) -> None:
    """A one-storage group has nothing to balance (section 11.1).

    Pattern expansion can only add storages, never remove them, so a group
    with no ``/…/`` entry at all has its post-expansion count already known
    here, with no cluster access needed: entries written *is* storages
    matched. A group that does have a pattern is instead checked once the
    cluster inventory is available (section 11.4,
    ``topology._expand_and_validate_groups``), since it is not yet known
    here how many storages the pattern will match.
    """
    for group in config.groups:
        if any(is_storage_pattern(s.id) for s in group.storages):
            continue
        if len(group.storages) < 2:
            errors.append(
                f"group {group.name!r} has only {len(group.storages)} storage(s); "
                "a group needs at least 2 to balance"
            )


def _check_thick_provisioning(config: Config, errors: list[str]) -> None:
    """``migration.assume_thick_provisioning`` survives only so an existing
    config that spells it out still loads. Over-provisioning is never
    modelled (section 5.1): every disk counts at its provisioned size, on a
    thin-provisioned storage too, so ``false`` promises a mode that does not
    exist and is refused rather than silently ignored."""
    if not config.migration.assume_thick_provisioning:
        errors.append(
            "migration.assume_thick_provisioning: false is not supported -- this tool never "
            "considers over-provisioning: every disk counts at its provisioned size, on "
            "thin-provisioned storage (Ceph RBD, LVM-thin, ZFS) as much as on thick. Remove "
            "the key, or set it to true"
        )


def _check_stopped_vms(config: Config, errors: list[str]) -> None:
    """``exclude.stopped`` survives only so a config that spells it out still
    loads. A stopped VM's disks are never moved, whatever capacity or reserve
    violation they cause (section 3.5): replication and backup products such
    as Veeam track a VM's volumes by location, and moving them breaks the
    replica. The apply-time pre-move check refuses a stopped VM too, so
    ``false`` would only plan moves that can never run -- refused rather than
    silently ignored."""
    if not config.exclude.stopped:
        errors.append(
            "exclude.stopped: false is not supported -- this tool never moves the disks of a "
            "stopped VM, whatever violation they cause (replication and backup tools such as "
            "Veeam break when a replicated VM's volumes move). Remove the key, or set it to true"
        )


def _check_snapshot_skip(config: Config, errors: list[str]) -> None:
    """``exclude.skip_vms_with_snapshots`` survives only so a config that spells
    it out still loads. PVE rejects a disk move for a VM that has snapshots
    (section 3.7), and the tool always pins such disks, so ``false`` would
    promise a mode that does not exist -- refused rather than silently
    ignored."""
    if not config.exclude.skip_vms_with_snapshots:
        errors.append(
            "exclude.skip_vms_with_snapshots: false is not supported -- PVE rejects a disk "
            "move for a VM that has snapshots, so this tool always pins such disks. Remove "
            "the key, or set it to true"
        )


def _check_metrics(config: Config, errors: list[str]) -> None:
    # Label names non-empty (schema covers empty-string) and pairwise distinct:
    # a duplicate silently collapses series into one.
    labels = config.metrics.labels
    label_values = [labels.vmid, labels.device, labels.node]
    if len(set(label_values)) != len(label_values):
        errors.append(
            "metrics.labels.vmid, .device and .node must be pairwise distinct "
            f"(got {label_values}); a duplicate silently collapses series"
        )

    # rate_window >= 4 * pvestatd_push_interval, or rate() sees too few points.
    min_rate_window = 4 * config.metrics.pvestatd_push_interval_seconds
    if config.metrics.rate_window_seconds < min_rate_window:
        errors.append(
            "metrics.rate_window "
            f"({config.metrics.rate_window_seconds:g}s) must be at least 4x "
            f"metrics.pvestatd_push_interval "
            f"({config.metrics.pvestatd_push_interval_seconds:g}s) = "
            f"{min_rate_window:g}s, or rate() sees too few points"
        )


def _check_forecast_window(config: Config, errors: list[str]) -> None:
    """window.lookback must cover what the configured forecast model needs."""
    from proxmox_storage_drs.forecast import required_range_seconds

    required = required_range_seconds(
        config.forecast, config.window.lookback_seconds, config.metrics.step_seconds
    )
    if config.window.lookback_seconds < required:
        errors.append(
            f"window.lookback ({config.window.lookback_seconds:g}s) is shorter than "
            f"forecast.model={config.forecast.model!r} needs ({required:g}s); "
            "either lengthen window.lookback or Prometheus retention, or choose a "
            "less demanding forecast.model"
        )


def _check_payback_horizon(config: Config, warnings: list[str]) -> None:
    """Warn (never error) below the horizon section 7.2 treats as a sane assumption
    about VM lifetime -- ``payback_horizon > 0`` is already enforced structurally by
    the schema."""
    horizon = config.migration.payback_horizon_seconds
    if horizon < 30 * 86400:
        warnings.append(
            f"migration.payback_horizon ({horizon:g}s) is below 30 days -- a short "
            "horizon rejects slow-accruing but real balancing benefit; set it to "
            "approximate how long a placement actually lasts (e.g. real VM lifetime), "
            "not operator patience"
        )


def _check_objective_weights(config: Config, warnings: list[str]) -> None:
    """Warn (never error) while ``0 < 2 * delta_capacity_spread <= gamma_move_bytes_per_tib``
    (section 11.1): the data-spread term is switched on, but a TiB moved toward the targets
    earns ``2 * delta`` and costs at least ``gamma``, so no disk of any size can pay for its
    move. ``delta_capacity_spread >= 0`` is already enforced structurally by the schema.
    The earlier warning against ``delta > alpha`` is gone: ``delta`` is per TiB and ``alpha``
    per in-flight request, so that compared unlike units."""
    delta = config.objective.delta_capacity_spread
    gamma = config.objective.gamma_move_bytes_per_tib
    if 0 < 2 * delta <= gamma:
        warnings.append(
            f"objective.delta_capacity_spread ({delta:g}) is at most half of "
            f"objective.gamma_move_bytes_per_tib ({gamma:g}) -- a TiB moved toward an even "
            "spread earns 2 * delta and costs at least gamma, so the data-spread term can "
            "never pay for a move; raise delta_capacity_spread or set it to 0 to say so"
        )


def _check_vm_split(config: Config, errors: list[str], warnings: list[str]) -> None:
    """Section 11.1: ``split_vm_footprint`` is ``null`` or a byte value above 0 (a ``0`` would
    cap every multi-disk VM at its largest disk and spread all of them -- a typo, not a
    policy); warn when ``mu_vm_split_per_tib`` is above 0 but below ``kappa_vm_affinity``,
    where one TiB of split excess no longer pays for opening a new storage.
    ``mu >= 0`` is already enforced structurally by the schema."""
    threshold = config.snapshot_reserve.split_vm_footprint_bytes
    if threshold is not None and threshold <= 0:
        errors.append(
            "snapshot_reserve.split_vm_footprint must be null (rule off) or a size above 0, "
            f"got {threshold}"
        )
    mu = config.objective.mu_vm_split_per_tib
    if threshold is not None and 0 < mu < config.objective.kappa_vm_affinity:
        warnings.append(
            f"objective.mu_vm_split_per_tib ({mu:g}) is below objective.kappa_vm_affinity "
            f"({config.objective.kappa_vm_affinity:g}) -- one TiB of split excess no longer "
            "pays for opening a new storage, so the large-VM split rule will rarely act"
        )


def _check_time_windows(config: Config, errors: list[str]) -> None:
    for tw in config.execution.time_windows:
        if tw.start == tw.end:
            errors.append(
                f"execution.time_windows entry has start == end ({tw.start!r}); "
                "this would mean either 'never' or 'always' and must be explicit"
            )


def _check_support(config: Config, errors: list[str]) -> None:
    """``support.capture_range`` is the literal ``"auto"`` (section 16.2's
    computed maximum) or a duration ``units.parse_duration_seconds()`` can
    parse -- anything else is a typo that would otherwise surface only when
    ``collect-testdata`` runs, minutes into a capture."""
    capture_range = config.support.capture_range
    if capture_range != "auto":
        try:
            parse_duration_seconds(capture_range)
        except ConfigError as exc:
            errors.append(
                f"support.capture_range {capture_range!r} is neither 'auto' nor a "
                f"parseable duration: {exc}"
            )


def _check_connection_config(config: Config, errors: list[str]) -> None:
    """A live run needs somewhere to connect to; a ``--replay`` bundle's own
    ``config.yaml`` deliberately has neither (section 16.3: credentials and
    endpoints are dropped, not blanked), so this check runs only when the
    caller asked for it (``load_config(require_connection=True)``, the
    default for every path except loading a bundle -- section 16.5).

    Deliberately just presence, matching exactly what the JSON schema
    enforced before ``proxmox.host``/``prometheus.url`` became structurally
    optional: this is a like-for-like move of that rule from the schema to
    here, not a new, stricter one. Whether ``proxmox.auth`` actually holds a
    usable credential (a file value, or one of ``PVE_PASSWORD``/
    ``PVE_TOKEN_SECRET`` from the environment) is left to ``pve.py``'s own
    connection attempt, exactly as before -- ``config/drs.example.yaml``
    ships with no real credential on purpose, and must keep validating."""
    if not config.proxmox.host:
        errors.append("proxmox.host is required")
    if not config.prometheus.url:
        errors.append("prometheus.url is required")


def _validate_semantics(config: Config, *, require_connection: bool = True) -> list[str]:
    """Section 11.1 rules that jsonschema cannot express (cross-field, or need
    a value computed from two independently-optional settings). Returns
    non-fatal warnings; raises :class:`ConfigError` (with every error found,
    not just the first) for anything fatal.
    """
    errors: list[str] = []
    warnings: list[str] = []

    _check_schema_version(config, errors)
    if require_connection:
        _check_connection_config(config, errors)
    _check_group_names_unique(config, errors)
    _check_group_storage_membership(config, errors)
    _check_storage_patterns_compile(config, errors)
    _check_group_size(config, errors)
    _check_thick_provisioning(config, errors)
    _check_stopped_vms(config, errors)
    _check_snapshot_skip(config, errors)
    _check_metrics(config, errors)
    _check_forecast_window(config, errors)
    _check_payback_horizon(config, warnings)
    _check_objective_weights(config, warnings)
    _check_vm_split(config, errors, warnings)
    _check_time_windows(config, errors)
    _check_support(config, errors)

    if errors:
        raise ConfigError("config validation failed:\n  " + "\n  ".join(errors))

    return warnings
