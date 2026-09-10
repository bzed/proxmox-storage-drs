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
    username: str | None = None
    password: str | None = None
    token_id: str | None = None
    token_secret: str | None = None


@dataclass(frozen=True, slots=True)
class ProxmoxConfig:
    host: str = ""
    port: int = 8006
    verify_ssl: bool = True
    ca_file: str | None = None
    auth: AuthConfig = field(default_factory=AuthConfig)
    ticket_refresh_seconds: float = 3000.0
    read_workers: int = 12


@dataclass(frozen=True, slots=True)
class PrometheusConfig:
    url: str = ""
    timeout_seconds: float = 30.0
    username: str | None = None
    password: str | None = None
    bearer_token: str | None = None


@dataclass(frozen=True, slots=True)
class MetricLabels:
    vmid: str = "vmid"
    device: str = "instance"
    node: str = "nodename"
    cluster: str | None = None


@dataclass(frozen=True, slots=True)
class MetricsConfig:
    read_ops: str = "blockstat_rd_operations"
    write_ops: str = "blockstat_wr_operations"
    read_bytes: str = "blockstat_rd_bytes"
    write_bytes: str = "blockstat_wr_bytes"
    read_time_ns: str = "blockstat_rd_total_time_ns"
    write_time_ns: str = "blockstat_wr_total_time_ns"
    labels: MetricLabels = field(default_factory=MetricLabels)
    rate_window_seconds: float = 300.0
    step_seconds: float = 300.0
    pvestatd_push_interval_seconds: float = 60.0
    extra_selector: str | None = None


@dataclass(frozen=True, slots=True)
class WindowConfig:
    lookback_seconds: float = 86400.0
    quantile: float = 0.95
    upper_quantile: float = 0.99
    min_coverage: float = 0.80


@dataclass(frozen=True, slots=True)
class LoadWeights:
    iotime: float = 1.0
    ops: float = 0.0
    bytes: float = 0.0
    read_factor: float = 1.0
    write_factor: float = 1.0


@dataclass(frozen=True, slots=True)
class StorageConfig:
    id: str
    capability_weight: float = 1.0
    reserve_factor: float | None = None
    saturation_load: float | None = None


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
    name: str
    storages: tuple[StorageConfig, ...] = ()


@dataclass(frozen=True, slots=True)
class SnapshotReserveConfig:
    factor: float = 2.0
    min_free_bytes: int = 0
    count_foreign_volumes: bool = True


@dataclass(frozen=True, slots=True)
class GatesConfig:
    drift_threshold: float = 0.10
    imbalance_threshold: float = 0.20
    cooldown_per_disk_seconds: float = 86400.0
    cooldown_per_storage_seconds: float = 3600.0


@dataclass(frozen=True, slots=True)
class MigrationConfig:
    bwlimit_bytes_per_sec: int = 209_715_200  # 200 MiB/s
    source_load_weight: float = 1.0
    target_load_weight: float = 1.0
    payback_horizon_seconds: float = 604800.0  # 7d
    payback_ratio: float = 10.0
    max_single_move_duration_seconds: float = 21600.0  # 6h
    account_saferemove_wipe: bool = True
    wipe_load_weight: float = 1.0
    saturation_ceiling: float = 0.85
    assume_thick_provisioning: bool = True


@dataclass(frozen=True, slots=True)
class ObjectiveConfig:
    spread_metric: str = "l1"
    alpha_spread: float = 1.0
    beta_move_count: float = 0.25
    gamma_move_bytes_per_tib: float = 0.05
    kappa_vm_affinity: float = 0.50
    affinity_counts_pinned_disks: bool = False
    reserve_violation_penalty: float = 1000.0


@dataclass(frozen=True, slots=True)
class SolverConfig:
    backend: str = "auto"
    time_limit_seconds: float = 60.0
    mip_gap: float = 0.02
    heuristic_iterations: int = 5000


@dataclass(frozen=True, slots=True)
class LocksConfig:
    wait_timeout_seconds: float = 14400.0  # 4h
    poll_interval_seconds: float = 30.0
    on_timeout: str = "skip"


@dataclass(frozen=True, slots=True)
class SourceReleaseConfig:
    wait: bool = True
    timeout_seconds: float = 172800.0  # 48h


@dataclass(frozen=True, slots=True)
class TimeWindow:
    days: tuple[str, ...]
    start: str
    end: str


@dataclass(frozen=True, slots=True)
class ExecutionConfig:
    mode: str = "dry-run"
    max_concurrent_migrations: int = 1
    max_migrations_per_run: int = 5
    max_concurrent_per_storage: int = 1
    max_replans_per_run: int = 3
    abort_on_failure: bool = True
    poll_interval_seconds: float = 10.0
    locks: LocksConfig = field(default_factory=LocksConfig)
    source_release: SourceReleaseConfig = field(default_factory=SourceReleaseConfig)
    time_windows: tuple[TimeWindow, ...] = ()


@dataclass(frozen=True, slots=True)
class ExcludeConfig:
    vmids: tuple[int, ...] = ()
    disks: tuple[str, ...] = ()
    storages: tuple[str, ...] = ()
    tags: tuple[str, ...] = ("no-drs",)
    skip_vms_with_snapshots: bool = True
    running_only: bool = True
    include_unused_disks: bool = True


@dataclass(frozen=True, slots=True)
class ReportConfig:
    warn_pinned_load_fraction: float = 0.25


@dataclass(frozen=True, slots=True)
class StateConfig:
    path: str = "/var/lib/pve-storage-drs/state.json"


@dataclass(frozen=True, slots=True)
class HoltWintersConfig:
    seasonal_periods: int = 288
    trend: str = "add"
    seasonal: str = "add"
    residual_z: float = 2.0


@dataclass(frozen=True, slots=True)
class ForecastConfig:
    model: str = "quantile"
    seasonal_lookback_days: float = 7.0
    holt_winters: HoltWintersConfig = field(default_factory=HoltWintersConfig)


@dataclass(frozen=True, slots=True)
class Config:
    schema_version: int
    proxmox: ProxmoxConfig
    prometheus: PrometheusConfig
    metrics: MetricsConfig
    window: WindowConfig
    load_weights: LoadWeights
    groups: tuple[GroupConfig, ...]
    snapshot_reserve: SnapshotReserveConfig
    gates: GatesConfig
    migration: MigrationConfig
    objective: ObjectiveConfig
    solver: SolverConfig
    execution: ExecutionConfig
    exclude: ExcludeConfig
    report: ReportConfig
    state: StateConfig
    forecast: ForecastConfig


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
    cli_path: str | None = None, env: Mapping[str, str] | None = None
) -> ResolvedConfig:
    """Resolve, read, parse and validate the configuration.

    See section 11 for resolution order and section 11.1 for the semantic
    rules applied after JSON-schema structural validation. Raises
    :class:`ConfigError` on any failure -- there is deliberately no
    warn-and-continue path (AGENTS.md section 6: "a misconfigured balancer
    moving production disks is worse than one that refuses to start").
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
    warnings = _validate_semantics(config)

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
        cluster=labels_raw.get("cluster"),
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
            metrics_raw.get("pvestatd_push_interval", "60s")
        ),
        extra_selector=metrics_raw.get("extra_selector"),
    )

    window_raw = raw.get("window", {})
    window = WindowConfig(
        lookback_seconds=parse_duration_seconds(window_raw.get("lookback", "24h")),
        quantile=window_raw.get("quantile", 0.95),
        upper_quantile=window_raw.get("upper_quantile", 0.99),
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
                    saturation_load=s.get("saturation_load"),
                )
                for s in g.get("storages", [])
            ),
        )
        for g in raw.get("groups", [])
    )

    sr_raw = raw.get("snapshot_reserve", {})
    snapshot_reserve = SnapshotReserveConfig(
        factor=sr_raw.get("factor", 2.0),
        min_free_bytes=parse_size_bytes(sr_raw.get("min_free_bytes", 0)),
        count_foreign_volumes=sr_raw.get("count_foreign_volumes", True),
    )

    gates_raw = raw.get("gates", {})
    gates = GatesConfig(
        drift_threshold=gates_raw.get("drift_threshold", 0.10),
        imbalance_threshold=gates_raw.get("imbalance_threshold", 0.20),
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
        payback_horizon_seconds=parse_duration_seconds(mig_raw.get("payback_horizon", "7d")),
        payback_ratio=mig_raw.get("payback_ratio", 10.0),
        max_single_move_duration_seconds=parse_duration_seconds(
            mig_raw.get("max_single_move_duration", "6h")
        ),
        account_saferemove_wipe=mig_raw.get("account_saferemove_wipe", True),
        wipe_load_weight=mig_raw.get("wipe_load_weight", 1.0),
        saturation_ceiling=mig_raw.get("saturation_ceiling", 0.85),
        assume_thick_provisioning=mig_raw.get("assume_thick_provisioning", True),
    )

    obj_raw = raw.get("objective", {})
    objective = ObjectiveConfig(
        spread_metric=obj_raw.get("spread_metric", "l1"),
        alpha_spread=obj_raw.get("alpha_spread", 1.0),
        beta_move_count=obj_raw.get("beta_move_count", 0.25),
        gamma_move_bytes_per_tib=obj_raw.get("gamma_move_bytes_per_tib", 0.05),
        kappa_vm_affinity=obj_raw.get("kappa_vm_affinity", 0.50),
        affinity_counts_pinned_disks=obj_raw.get("affinity_counts_pinned_disks", False),
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
        running_only=excl_raw.get("running_only", True),
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
        trend=hw_raw.get("trend", "add"),
        seasonal=hw_raw.get("seasonal", "add"),
        residual_z=hw_raw.get("residual_z", 2.0),
    )
    forecast = ForecastConfig(
        model=fc_raw.get("model", "quantile"),
        seasonal_lookback_days=fc_raw.get("seasonal_lookback_days", 7.0),
        holt_winters=holt_winters,
    )

    return Config(
        schema_version=raw.get("schema_version", 1),
        proxmox=proxmox,
        prometheus=prometheus,
        metrics=metrics,
        window=window,
        load_weights=load_weights,
        groups=groups,
        snapshot_reserve=snapshot_reserve,
        gates=gates,
        migration=migration,
        objective=objective,
        solver=solver,
        execution=execution,
        exclude=exclude,
        report=report,
        state=state,
        forecast=forecast,
    )


# ------------------------------------------------------------ semantic rules


def _check_schema_version(config: Config, errors: list[str]) -> None:
    if config.schema_version != SUPPORTED_SCHEMA_MAJOR:
        errors.append(
            f"schema_version {config.schema_version} is not supported; "
            f"this build understands major version {SUPPORTED_SCHEMA_MAJOR}"
        )


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


def _check_window(config: Config, errors: list[str]) -> None:
    if config.window.upper_quantile < config.window.quantile:
        errors.append(
            "window.upper_quantile "
            f"({config.window.upper_quantile}) must be >= window.quantile "
            f"({config.window.quantile})"
        )


def _check_metrics(config: Config, errors: list[str]) -> None:
    # Label names non-empty (schema covers empty-string) and pairwise distinct:
    # a duplicate silently collapses series into one. cluster is optional
    # (None means "not configured, don't check it") but still joins this
    # check when set -- it is just as capable of colliding with the other
    # three as they are with each other.
    labels = config.metrics.labels
    label_values = [labels.vmid, labels.device, labels.node]
    if labels.cluster is not None:
        label_values.append(labels.cluster)
    if len(set(label_values)) != len(label_values):
        errors.append(
            "metrics.labels.vmid, .device, .node and .cluster (when set) must be pairwise "
            f"distinct (got {label_values}); a duplicate silently collapses series"
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
    """window.lookback must cover what the configured forecaster needs."""
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


def _check_saturation_load(config: Config, warnings: list[str]) -> None:
    """Warn (never error) where section 7.3's saturation guard is inactive.

    The warning text itself names no section: a plain-language explanation
    plus the exact config key to set is something an operator who has
    never opened IMPLEMENTATION_PLAN.md can act on; a bare "section 7.3"
    citation is not (the user's own words: "a normal user will not
    understand" it, and "error messages must point to the instructions
    with a wording" they can follow)."""
    for group in config.groups:
        for storage in group.storages:
            if storage.saturation_load is None:
                warnings.append(
                    f"group {group.name!r} storage {storage.id!r}: no saturation_load "
                    "configured, so migrations onto it are never checked against its I/O "
                    "capacity before starting -- set groups[].storages[].saturation_load "
                    "for it if you know the storage's queue-depth limit"
                )


def _check_time_windows(config: Config, errors: list[str]) -> None:
    for tw in config.execution.time_windows:
        if tw.start == tw.end:
            errors.append(
                f"execution.time_windows entry has start == end ({tw.start!r}); "
                "this would mean either 'never' or 'always' and must be explicit"
            )


def _validate_semantics(config: Config) -> list[str]:
    """Section 11.1 rules that jsonschema cannot express (cross-field, or need
    a value computed from two independently-optional settings). Returns
    non-fatal warnings; raises :class:`ConfigError` (with every error found,
    not just the first) for anything fatal.
    """
    errors: list[str] = []
    warnings: list[str] = []

    _check_schema_version(config, errors)
    _check_group_storage_membership(config, errors)
    _check_storage_patterns_compile(config, errors)
    _check_group_size(config, errors)
    _check_window(config, errors)
    _check_metrics(config, errors)
    _check_forecast_window(config, errors)
    _check_saturation_load(config, warnings)
    _check_time_windows(config, errors)

    if errors:
        raise ConfigError("config validation failed:\n  " + "\n  ".join(errors))

    return warnings
