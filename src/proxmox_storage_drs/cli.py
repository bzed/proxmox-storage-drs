# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""``pve-storage-drs`` entry point. See IMPLEMENTATION_PLAN.md section 11.3.

This is the only module allowed to call ``print()`` (AGENTS.md section 5):
everything else logs. ``print()`` here is reserved for the human/JSON report
on stdout; all logging goes to stderr via :mod:`proxmox_storage_drs.logging_setup`,
which is what keeps ``--json`` output on stdout uncontaminated.

Global options are defined on the top-level parser (not the subparsers) so
that argparse enforces "before the subcommand" (section 11.3) for free, and
``argparse.ArgumentDefaultsHelpFormatter`` plus real default values on every
``add_argument`` is what keeps ``--help`` unable to claim a default the code
does not use (AGENTS.md section 8.5) -- there is deliberately no second,
hand-kept list of options anywhere in this module or in the manpage/manual.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from proxmox_storage_drs import __version__, optimize
from proxmox_storage_drs.config import (
    DEFAULT_CONFIG_PATH,
    ENV_CONFIG_VAR,
    ExcludeConfig,
    ExecutionConfig,
    ForecastConfig,
    MetricsConfig,
    MigrationConfig,
    ResolvedConfig,
    load_config,
)
from proxmox_storage_drs.crashrecovery import reconcile_inflight
from proxmox_storage_drs.exceptions import ConfigError, DrsError, MetricsError
from proxmox_storage_drs.execute import (
    ConfirmCallback,
    ExecutionResult,
    InflightCallback,
    MoveOutcome,
    execute_plan,
)
from proxmox_storage_drs.forecast import (
    Forecaster,
    TimeSeries,
    backtest_validated,
    build_forecaster,
    group_aggregate_series,
    required_range_seconds,
    storage_upper_bound,
)
from proxmox_storage_drs.gates import GateDecision, evaluate_group_gates
from proxmox_storage_drs.heuristic import (
    Assignment,
    ObjectiveBreakdown,
    evaluate_assignment,
    group_average_utilization,
    raw_spread,
    run_heuristic,
)
from proxmox_storage_drs.loadmodel import GroupLoad, compute_disk_load_series, compute_group_load
from proxmox_storage_drs.logging_setup import configure_logging
from proxmox_storage_drs.metrics import (
    PrometheusClient,
    VerifyMetricsReport,
    resolve_node_selector,
    verify_metrics,
)
from proxmox_storage_drs.payback import (
    MoveCost,
    PaybackResult,
    compute_benefit_load_seconds,
    compute_move_cost,
    compute_wipe_duration_seconds,
    evaluate_plan_payback,
    mirror_duration_seconds,
)
from proxmox_storage_drs.pve import PveClient
from proxmox_storage_drs.pve import build_client as build_pve_client
from proxmox_storage_drs.reserve import ReserveStatus, compute_reserve_status, largest_disk_bytes
from proxmox_storage_drs.schedule import ScheduledMove, ScheduleResult, order_moves
from proxmox_storage_drs.state import (
    LockHandle,
    State,
    acquire_lock,
    active_storage_cooldowns,
    disk_state_key,
    load_state,
    load_vector_for_group,
    now_iso,
    release_lock,
    save_locked_state,
    storage_state_key,
    with_inflight_upid,
    with_recorded_balance,
    with_recorded_cooldown,
    without_inflight_upid,
)
from proxmox_storage_drs.timewindow import current_deadline
from proxmox_storage_drs.topology import Disk, Group, Storage, Topology, build_topology
from proxmox_storage_drs.units import format_bytes, format_duration_seconds

logger = logging.getLogger(__name__)

# Section 9.1: dry-run < confirm < auto. Used only to classify a --mode
# override as an escalation (warn) or a de-escalation (info) -- section 11.3.
_MODE_RANK = {"dry-run": 0, "confirm": 1, "auto": 2}

_EXECUTION_MODES = ("dry-run", "confirm", "auto")

# Subcommands from section 2 (module layout) / the manpage COMMANDS section,
# each with the one-line description shown in --help and in the manpage.
_SUBCOMMANDS: dict[str, str] = {
    "plan": "Compute and print a migration plan. Does not execute it.",
    "apply": "Execute a plan, subject to execution.mode, concurrency caps and time windows.",
    "show-load": "Print every storage with its disks, sizes, measured load and reserve status.",
    "explain": "Say why the tool did what it did: gates, pins, deferrals and payback arithmetic.",
    "verify-metrics": "Validate configured metric/label names against the live Prometheus.",
    "verify-storages": "Report saferemove and the implied wipe time per storage.",
}


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser that both ``main()`` and ``--help`` run on."""
    parser = argparse.ArgumentParser(
        prog="pve-storage-drs",
        description=(
            "Balance disk I/O load across Proxmox VE shared storages by "
            "live-migrating VM disks. Dry-run is the default: nothing is changed "
            "unless a less safe --mode is explicitly selected."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-c",
        "--config",
        metavar="PATH",
        default=None,
        help=(
            f"Read the configuration from PATH instead of {DEFAULT_CONFIG_PATH} "
            f"(env: {ENV_CONFIG_VAR}). A PATH named here that is missing, unreadable "
            "or invalid is a hard failure -- never a silent fallback to the default."
        ),
    )
    parser.add_argument(
        "--group",
        metavar="NAME",
        action="append",
        default=None,
        help="Restrict the run to one storage group. Repeatable. Groups are independent.",
    )
    parser.add_argument(
        "--mode",
        choices=_EXECUTION_MODES,
        default=None,
        help=(
            "Override execution.mode for this run only. Moving toward less safety "
            "(dry-run to confirm/auto, confirm to auto) is logged at warning level."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the machine-readable report instead of the human one.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="More detail on stderr. Repeatable.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Warnings and errors only. Intended for the systemd timer.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print the version and exit.",
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Show the pve-storage-drs(1) manual page and exit.",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="command")
    subparsers.add_parser("help", help="Alias for --manual.")
    for name, help_text in _SUBCOMMANDS.items():
        subparsers.add_parser(name, help=help_text)

    return parser


# ------------------------------------------------------------- mode override


def apply_mode_override(configured_mode: str, override: str) -> str:
    """Section 11.3: log a ``--mode`` override, at warning level if it escalates.

    Returns the effective mode (always ``override``, when one was given).
    Escalating means moving *up* dry-run < confirm < auto -- removing a
    safety barrier the operator themselves configured.
    """
    if override == configured_mode:
        return override
    escalating = _MODE_RANK[override] > _MODE_RANK[configured_mode]
    level = logging.WARNING if escalating else logging.INFO
    logger.log(
        level,
        "execution mode overridden on the command line",
        extra={
            "event": "mode_override",
            "configured_mode": configured_mode,
            "effective_mode": override,
            "escalating": escalating,
        },
    )
    return override


# ------------------------------------------------------------------- manual


def _fallback_manual_text() -> str:
    """Plain text used only when ``man(1)`` itself is unavailable.

    A packaged install always has ``man pve-storage-drs`` work -- the manpage is
    installed by ``debian/pve-storage-drs.manpages`` and ``man(1)`` itself detects a
    non-tty stdout and disables the pager on its own, which is what satisfies
    "never answer with a URL alone" even when piped. This fallback exists only
    for an uninstalled source checkout (or a minimal system with no man-db),
    where it reads the manpage source directly from the repository.
    """
    here = Path(__file__).resolve()
    for candidate in here.parents:
        candidate_path = candidate / "man" / "pve-storage-drs.1.md"
        if candidate_path.is_file():
            return candidate_path.read_text(encoding="utf-8")
    return (
        "pve-storage-drs manual is not available here: man(1) is not installed and "
        "this does not look like a source checkout. Install the pve-storage-drs "
        "package for `man pve-storage-drs`, or read man/pve-storage-drs.1.md in the "
        "source tree."
    )


def show_manual() -> int:
    """``--manual`` / ``help``: see AGENTS.md section 8.5."""
    if shutil.which("man") is not None:
        result = subprocess.run(["man", "pve-storage-drs"], check=False)
        if result.returncode == 0:
            return 0
    print(_fallback_manual_text())
    return 0


# -------------------------------------------------------------- subcommands
#
# Every subcommand in `_SUBCOMMANDS` now has a real handler (`explain` was
# the last one, section 12). `_make_not_yet_implemented_handler()` is kept
# as the extension point `docs/internals/40-cli-and-logging.md` describes
# for the *next* new command this codebase adds -- `_COMMAND_HANDLERS`'
# dict-comprehension initializer below still runs it for every name before
# each real handler overwrites its own entry, so a command added to
# `_SUBCOMMANDS` without a handler assignment fails honestly (AGENTS.md
# section 10: a partial/unvalidated result is worse than "not implemented
# yet") instead of a `KeyError` from `main()`'s dispatch.


CommandHandler = Callable[[ResolvedConfig, argparse.Namespace, str], int]


def _make_not_yet_implemented_handler(command: str) -> CommandHandler:
    def handler(resolved: ResolvedConfig, args: argparse.Namespace, mode: str) -> int:
        del resolved, args, mode
        print(
            f"pve-storage-drs: {command!r} is not implemented yet in this development "
            "build; see IMPLEMENTATION_PLAN.md section 12 for the phase it belongs to",
            file=sys.stderr,
        )
        return 1

    return handler


def _filter_groups(topology: Topology, names: list[str] | None) -> Topology:
    """``--group NAME`` (repeatable, section 11.3/the manpage): restrict a
    run to the named groups. Every group-iterating handler
    (``show-load``, ``verify-storages``, ``plan``) calls this right after
    ``build_topology()`` so there is one place implementing the flag, not
    one per handler (AGENTS.md section 5); ``verify-metrics`` does not,
    because it validates configured metric/label names against Prometheus
    directly and never iterates ``topology.groups`` at all.

    A name that matches no configured group is a hard failure, not a
    silent no-op -- the same "an explicitly named thing that cannot be
    found is an error" rule this codebase already applies to
    ``--config PATH`` (`docs/manual/30-safety-and-status.md`), and it is
    what keeps a typo'd ``--group`` from looking exactly like "this group
    has nothing to report" (REVIEW.md R-03: previously ``--group`` was
    parsed and documented but never read by any handler at all)."""
    if not names:
        return topology
    known = {g.name for g in topology.groups}
    unknown = sorted(set(names) - known)
    if unknown:
        raise DrsError(
            "--group named a group that does not exist in this configuration: "
            f"{', '.join(unknown)} (configured groups: {', '.join(sorted(known)) or 'none'})"
        )
    selected = set(names)
    return dataclasses.replace(
        topology, groups=tuple(g for g in topology.groups if g.name in selected)
    )


def _resolve_node_selector_for_run(client: PveClient, metrics: MetricsConfig) -> str | None:
    """Section 3.4's node/cluster-scoping filter for one command invocation.

    ``metrics.extra_selector`` short-circuits before any extra API call, as
    before. Otherwise ``client.cluster_name()`` is called whenever
    ``metrics.labels.cluster`` names a label at all -- true by default
    (``"cluster"``), so this is the normal path, not an opt-in one; only
    an explicit ``metrics.labels.cluster: null`` skips this call outright
    (see ``metrics.resolve_node_selector()``'s own docstring for the full
    precedence). ``client.node_names()`` is called only when the cluster
    name does not already settle it -- `null`, or a cluster with no
    ``type: "cluster"`` entry to name it -- so a run that got its answer
    from the cluster name never pays for the node-list call too. Every
    command that reaches here already has a live PVE client from building
    its own topology. ``verify-metrics`` calls
    ``metrics.resolve_node_selector()`` directly instead, with both
    ``node_names`` and ``cluster_name`` left ``None``, since it is
    deliberately independent of the PVE API entirely and never reaches
    this function at all."""
    if metrics.extra_selector:
        return metrics.extra_selector
    cluster_name = client.cluster_name() if metrics.labels.cluster else None
    if metrics.labels.cluster and cluster_name:
        return resolve_node_selector(metrics, None, cluster_name)
    return resolve_node_selector(metrics, client.node_names(), cluster_name)


def _last_loads_by_group(state: State, topology: Topology) -> dict[str, dict[str, float] | None]:
    """One :func:`state.load_vector_for_group` lookup per group, done once
    up front rather than re-reading ``state`` inside each render function
    -- both ``loadmodel.compute_group_load()``'s ``last_known_loads`` and
    ``gates.evaluate_group_gates()``'s ``last_load`` take the identical
    per-group ``dict[str, float] | None`` this produces."""
    return {group.name: load_vector_for_group(state, group.name) for group in topology.groups}


def _render_verify_metrics_human(report: VerifyMetricsReport) -> str:
    lines = [f"[{f.level:>7}] {f.message}" for f in report.findings]
    lines.append("")
    lines.append(
        "OK: verify-metrics found no blocking problems" if report.ok else "FAILED: see errors above"
    )
    return "\n".join(lines)


def _render_verify_metrics_json(report: VerifyMetricsReport) -> dict[str, object]:
    return {
        "ok": report.ok,
        "findings": [{"level": f.level, "message": f.message} for f in report.findings],
        "sample_series": report.sample_series,
        "coverage_by_disk": {
            f"{key.vmid}:{key.device}": fraction
            for key, fraction in report.coverage_by_disk.items()
        },
        "observed_spacing_seconds": report.observed_spacing_seconds,
    }


def _handle_verify_metrics(resolved: ResolvedConfig, args: argparse.Namespace, mode: str) -> int:
    del mode
    client = PrometheusClient(resolved.config.prometheus)
    report = verify_metrics(client, resolved.config.metrics, resolved.config.window)
    if args.json:
        print(json.dumps(_render_verify_metrics_json(report), indent=2, sort_keys=True))
    else:
        print(_render_verify_metrics_human(report))
    return 0 if report.ok else 1


def _render_storage_and_disk_load_lines(
    group: Group,
    group_load: GroupLoad | None,
    reserve_statuses: dict[str, ReserveStatus],
) -> list[str]:
    """Section 4's per-storage `L_s`/`u_s` and per-disk size/measured-load/
    pin picture -- ``show-load``'s own per-group body, factored out so
    ``explain`` can reuse it verbatim as its own "what was actually
    measured" section (AGENTS.md section 5): both commands report the
    identical `GroupLoad`, just for a different purpose."""
    load_by_key = group_load.load_by_disk_key() if group_load else {}
    storage_loads = {s.storage_id: s for s in group_load.storages} if group_load else {}
    lines: list[str] = []
    for storage in group.storages:
        status = reserve_statuses[storage.id]
        reserve_str = (
            f"⚠ reserve short by {format_bytes(status.shortfall_bytes)}"
            if status.violated
            else "reserve OK"
        )
        load_prefix = ""
        if storage.id in storage_loads:
            sl = storage_loads[storage.id]
            load_prefix = f"L={sl.load:.2f} u={sl.utilization:.2f}  "
        lines.append(
            f"  {storage.id}  used {format_bytes(storage.used_bytes)}/"
            f"{format_bytes(storage.capacity_bytes)}  {load_prefix}{reserve_str}  "
            f"(largest disk {format_bytes(status.largest_disk_bytes)}, "
            f"requires {format_bytes(status.required_reserve_bytes)} free)"
        )
        disks_here = sorted(
            (d for d in group.disks if d.current_storage == storage.id),
            key=lambda d: (d.vmid, d.device),
        )
        for disk in disks_here:
            load_suffix = f"  ℓ {load_by_key[disk.key]:.2f}" if disk.key in load_by_key else ""
            pin = f"  [pinned: {disk.pinned_reason}]" if disk.pinned_reason else ""
            lines.append(
                f"    {disk.key:<14} {format_bytes(disk.size_bytes):>10}  "
                f"{disk.format:<6}{load_suffix}{pin}"
            )
    if group_load is not None:
        for disk_load in group_load.disks:
            if disk_load.flagged_reason:
                lines.append(f"  ⚠ {disk_load.disk_key}: {disk_load.flagged_reason}")
        if group_load.idle:
            lines.append("  (idle: no measured I/O for this group this window)")
    return lines


def _render_show_load_human(
    topology: Topology,
    config: Any,
    group_loads: dict[str, GroupLoad],
    load_errors: dict[str, str],
    last_loads_by_group: dict[str, dict[str, float] | None],
) -> str:
    lines: list[str] = []
    for group in topology.groups:
        group_load = group_loads.get(group.name)
        reserve_statuses = {
            storage.id: compute_reserve_status(
                storage, group.disks, config.snapshot_reserve.min_free_bytes
            )
            for storage in group.storages
        }
        header = f"Group {group.name}"
        if group_load is not None:
            decision = evaluate_group_gates(
                group_load,
                reserve_statuses,
                config.gates,
                last_load=last_loads_by_group.get(group.name),
            )
            verdict = "ACT" if decision.act else "NO ACTION"
            header += f" → {verdict}: {decision.reason}"
        lines.append(header)
        lines.extend(_render_storage_and_disk_load_lines(group, group_load, reserve_statuses))
        if group.name in load_errors:
            lines.append(f"  ⚠ per-disk load unavailable: {load_errors[group.name]}")
        lines.append("")
    if topology.warnings:
        lines.append("Warnings:")
        lines.extend(f"  - {warning}" for warning in topology.warnings)
        lines.append("")
    return "\n".join(lines)


def _render_show_load_json(
    topology: Topology,
    config: Any,
    group_loads: dict[str, GroupLoad],
    load_errors: dict[str, str],
    last_loads_by_group: dict[str, dict[str, float] | None],
) -> dict[str, object]:
    groups_out = []
    for group in topology.groups:
        group_load = group_loads.get(group.name)
        load_by_key = group_load.load_by_disk_key() if group_load else {}
        flagged_by_key = (
            {d.disk_key: d.flagged_reason for d in group_load.disks} if group_load else {}
        )
        storage_loads = {s.storage_id: s for s in group_load.storages} if group_load else {}
        reserve_statuses = {
            storage.id: compute_reserve_status(
                storage, group.disks, config.snapshot_reserve.min_free_bytes
            )
            for storage in group.storages
        }
        storages_out = []
        for storage in group.storages:
            status = reserve_statuses[storage.id]
            entry: dict[str, object] = {
                "id": storage.id,
                "used_bytes": storage.used_bytes,
                "capacity_bytes": storage.capacity_bytes,
                "foreign_used_bytes": storage.foreign_used_bytes,
                "largest_disk_bytes": status.largest_disk_bytes,
                "required_reserve_bytes": status.required_reserve_bytes,
                "reserve_violated": status.violated,
                "reserve_shortfall_bytes": status.shortfall_bytes,
            }
            if storage.id in storage_loads:
                entry["load"] = storage_loads[storage.id].load
                entry["utilization"] = storage_loads[storage.id].utilization
            storages_out.append(entry)
        disks_out = []
        for d in group.disks:
            disk_entry: dict[str, object] = {
                "key": d.key,
                "vmid": d.vmid,
                "device": d.device,
                "vm_name": d.vm_name,
                "size_bytes": d.size_bytes,
                "current_storage": d.current_storage,
                "format": d.format,
                "pinned_reason": d.pinned_reason,
            }
            if d.key in load_by_key:
                disk_entry["load"] = load_by_key[d.key]
                disk_entry["load_flagged_reason"] = flagged_by_key.get(d.key)
            disks_out.append(disk_entry)
        gate_out: dict[str, object] | None = None
        if group_load is not None:
            decision = evaluate_group_gates(
                group_load,
                reserve_statuses,
                config.gates,
                last_load=last_loads_by_group.get(group.name),
            )
            gate_out = {
                "act": decision.act,
                "reason": decision.reason,
                "reserve_override": decision.reserve_override,
                "drift_fraction": decision.drift_fraction,
                "imbalance_fraction": decision.imbalance_fraction,
            }
        groups_out.append(
            {
                "name": group.name,
                "storages": storages_out,
                "disks": disks_out,
                "load_computed": group_load is not None,
                "idle": group_load.idle if group_load is not None else None,
                "load_error": load_errors.get(group.name),
                "gate": gate_out,
            }
        )
    return {"groups": groups_out, "warnings": list(topology.warnings)}


def _handle_show_load(resolved: ResolvedConfig, args: argparse.Namespace, mode: str) -> int:
    del mode
    client = build_pve_client(resolved.config.proxmox)
    # Read-only: never takes state.py's advisory lock (see its module
    # docstring) -- show-load never executes a migration, so there is
    # nothing here for the lock to protect against. Read once, reused for
    # both build_topology()'s (C2) cooldown pin and the gate's drift input.
    now = datetime.now(timezone.utc)
    state = load_state(resolved.config.state.path)
    topology = _filter_groups(
        build_topology(client, resolved.config, state=state, now=now), args.group
    )
    prom_client = PrometheusClient(resolved.config.prometheus)
    node_selector = _resolve_node_selector_for_run(client, resolved.config.metrics)
    last_loads_by_group = _last_loads_by_group(state, topology)
    group_loads: dict[str, GroupLoad] = {}
    load_errors: dict[str, str] = {}
    for group in topology.groups:
        try:
            group_loads[group.name] = compute_group_load(
                prom_client,
                resolved.config.metrics,
                resolved.config.window,
                resolved.config.load_weights,
                group,
                last_known_loads=last_loads_by_group.get(group.name),
                node_selector=node_selector,
            )
        except MetricsError as exc:
            # Section 4's load numbers are not safety-critical the way (C4)/
            # (C5) reserve status is -- a Prometheus outage should not hide
            # accurate size/reserve info the rest of this command already
            # has, so this group's load is simply reported as unavailable.
            load_errors[group.name] = str(exc)
    if args.json:
        print(
            json.dumps(
                _render_show_load_json(
                    topology, resolved.config, group_loads, load_errors, last_loads_by_group
                ),
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(
            _render_show_load_human(
                topology, resolved.config, group_loads, load_errors, last_loads_by_group
            )
        )
    return 0


def _spread_fraction(utilization: dict[str, float], average_utilization: float) -> float:
    """``(max_s u_s - min_s u_s) / u*`` -- gates.py's own imbalance formula
    (section 6), reused here for the plan's before/after summary rather
    than redefining "spread" a second way."""
    if not utilization or not average_utilization:
        return 0.0
    return (max(utilization.values()) - min(utilization.values())) / average_utilization


_BYTES_PER_TIB = 1 << 40


def _load_per_tib(load_by_key: dict[str, float], key: str, size_bytes: int) -> float:
    """Section 7.3's advisory ``ell/z`` ratio -- ``0.0`` for a zero-size
    disk rather than a ``ZeroDivisionError`` (PVE does not report these in
    practice, and ``config_schema.json`` does not forbid ``size_bytes: 0``
    since that value comes from the PVE API, not config; defense in depth,
    not a live bug -- REVIEW.md R-06). Takes a bare ``key``/``size_bytes``
    pair rather than a :class:`ScheduledMove` so ``explain`` (section
    3.6/7.3: "worth surfacing... output") can reuse it for a pinned
    :class:`~proxmox_storage_drs.topology.Disk` too, which never becomes a
    ``ScheduledMove`` (AGENTS.md section 5 -- one implementation of this
    ratio, not two identical ones)."""
    if size_bytes <= 0:
        return 0.0
    return load_by_key.get(key, 0.0) / (size_bytes / _BYTES_PER_TIB)


def _render_plan_move_line(
    index: int,
    move: ScheduledMove,
    move_cost: MoveCost | None,
    load_by_key: dict[str, float],
    outcome: MoveOutcome | None = None,
) -> str:
    duration_str = "?"
    flag = ""
    if move_cost is not None:
        duration_str = f"~{format_duration_seconds(move_cost.duration_mirror_seconds)}"
        if move_cost.duration_wipe_seconds:
            duration_str += f" +wipe {format_duration_seconds(move_cost.duration_wipe_seconds)}"
        if move_cost.exceeds_max_duration:
            flag = "  ⚠ exceeds migration.max_single_move_duration"
    change = -move.imbalance_reduction
    load_per_tib = _load_per_tib(load_by_key, move.disk_key, move.size_bytes)
    line = (
        f"  {index}. {move.disk_key:<14} {move.from_storage} → {move.to_storage}   "
        f"{format_bytes(move.size_bytes):>10}   {duration_str}   "
        f"Δimbalance {change:+.2f}   ℓ/z {load_per_tib:.2f}{flag}"
    )
    if outcome is not None:
        # `apply`'s per-move execution result (section 9.5): `plan` never
        # passes `outcome`, so this is a pure addition to the line, not a
        # second rendering of it (AGENTS.md section 5).
        line += f"  → {outcome.status}: {outcome.detail}"
    return line


def _render_plan_payback_lines(payback_result: PaybackResult, payback_ratio: float) -> list[str]:
    """The economic test (``aggregate_ok``) and the hard per-move duration
    rule (``rejected_moves``) are reported separately here, not folded into
    one "does not pass payback" warning -- they are different failures with
    different remedies: an economic failure means the balance gained is not
    worth the migration cost (adjust weights, or accept the plan is not
    worth doing), while a hard-duration failure means a specific move would
    take too long regardless of benefit (`migration.max_single_move_duration`
    or `saferemove` throughput needs attention). Conflating them under one
    "payback test" label previously misdescribed a reserve-exempted plan
    that passed its economic test but still had a too-slow move as failing
    "section 7.3's payback test" outright (REVIEW.md R-05)."""
    mark = "✓" if payback_result.accepted else "✗"
    lines = [
        f"  payback: benefit {payback_result.benefit_load_seconds:.3g} load·s vs "
        f"cost {payback_result.total_cost_load_seconds:.3g} load·s → "
        f"ratio {payback_result.ratio:.3g} (need {payback_ratio:g}) {mark}"
    ]
    if not payback_result.aggregate_ok:
        lines.append(
            "  ⚠ this plan's balance benefit does not outweigh its migration cost -- "
            "automatically re-solving with adjusted weights is not implemented yet; "
            "review before applying"
        )
    if payback_result.rejected_moves:
        lines.append(
            "  ⚠ blocked by the hard per-move duration rule (migration."
            "max_single_move_duration): " + ", ".join(payback_result.rejected_moves)
        )
    if payback_result.deferred_moves:
        lines.append(
            "  ⚠ deferred: would push a target storage's I/O over migration."
            "saturation_ceiling: " + ", ".join(payback_result.deferred_moves)
        )
    return lines


def _render_plan_solver_line(outcome: _SolveOutcome) -> str:
    suffix = f" ({outcome.status})" if outcome.status is not None else ""
    return f"  solver: {outcome.backend}{suffix}"


def _render_group_plan_human(
    group: Group,
    group_loads: dict[str, GroupLoad],
    gate_decisions: dict[str, GateDecision],
    solve_outcomes: dict[str, _SolveOutcome],
    schedule_results: dict[str, ScheduleResult],
    payback_results: dict[str, PaybackResult],
    final_breakdowns: dict[str, ObjectiveBreakdown],
    load_errors: dict[str, str],
    payback_ratio: float,
    execution_result: ExecutionResult | None = None,
) -> list[str]:
    """One group's worth of ``_render_plan_human()``'s report -- shared
    with ``_render_apply_human()`` (AGENTS.md section 5), which passes its
    real ``execution_result`` so each move line grows the ``→ status:
    detail`` suffix :func:`_render_plan_move_line` already knows how to
    add, plus a closing line reporting whether the group's run stopped
    early. ``plan`` itself always passes ``None``, unchanged from before
    this was extracted.

    ``gate_decisions`` is looked up with ``.get()``, not ``[]`` -- ``plan``
    always fills in every group before rendering, but ``apply`` can stop
    the whole run early (an operator's ``[q]uit``, section 9.1) with
    later groups never planned at all, and those still need a line here,
    not a ``KeyError``."""
    lines: list[str] = []
    if group.name in load_errors:
        lines.append(f"Group {group.name} — plan unavailable: {load_errors[group.name]}")
        lines.append("")
        return lines

    decision = gate_decisions.get(group.name)
    if decision is None:
        lines.append(f"Group {group.name} — not evaluated this run")
        lines.append("")
        return lines
    verdict = "ACT" if decision.act else "NO ACTION"
    lines.append(f"Group {group.name} → {verdict}: {decision.reason}")

    schedule_result = schedule_results.get(group.name)
    if schedule_result is None:
        lines.append("")
        return lines

    lines.append(_render_plan_solver_line(solve_outcomes[group.name]))
    group_load = group_loads[group.name]
    load_by_key = group_load.load_by_disk_key()
    payback_result = payback_results.get(group.name)
    move_costs_by_key = (
        {mc.disk_key: mc for mc in payback_result.move_costs} if payback_result else {}
    )

    # Keyed by disk_key, not position: a payback-refused move (section 7.3,
    # REVIEW.md S-02) never reaches `execute.py` at all, so
    # `execution_result.outcomes` can legitimately be a *reordered subset*
    # of `schedule_result.order` (refused moves' outcomes first, then
    # whatever `execute_plan()` actually attempted) -- positional
    # indexing would silently pair the wrong outcome with the wrong move.
    outcomes_by_key = {
        o.disk_key: o for o in (execution_result.outcomes if execution_result is not None else ())
    }
    for i, move in enumerate(schedule_result.order, start=1):
        outcome = outcomes_by_key.get(move.disk_key)
        lines.append(
            _render_plan_move_line(
                i, move, move_costs_by_key.get(move.disk_key), load_by_key, outcome
            )
        )
    if schedule_result.deadlocked_msg:
        lines.append(f"  ⚠ {schedule_result.deadlocked_msg}")
    if execution_result is not None and execution_result.stopped_early:
        lines.append(f"  ⚠ run stopped early: {execution_result.stop_reason}")

    final_breakdown = final_breakdowns[group.name]
    before_spread = _spread_fraction(
        {s.storage_id: s.utilization for s in group_load.storages},
        group_load.average_utilization,
    )
    after_spread = _spread_fraction(final_breakdown.utilization, group_load.average_utilization)
    if schedule_result.order:
        after_line = "  after: " + "  ".join(
            f"{sid}={u:.2f}" for sid, u in sorted(final_breakdown.utilization.items())
        )
        lines.append(after_line)
        lines.append(f"  spread: {before_spread:.1%} → {after_spread:.1%}")
        if payback_result is not None:
            lines.extend(_render_plan_payback_lines(payback_result, payback_ratio))
    lines.append("")
    return lines


def _render_plan_human(
    topology: Topology,
    group_loads: dict[str, GroupLoad],
    gate_decisions: dict[str, GateDecision],
    solve_outcomes: dict[str, _SolveOutcome],
    schedule_results: dict[str, ScheduleResult],
    payback_results: dict[str, PaybackResult],
    final_breakdowns: dict[str, ObjectiveBreakdown],
    load_errors: dict[str, str],
    payback_ratio: float,
) -> str:
    lines: list[str] = []
    for group in topology.groups:
        lines.extend(
            _render_group_plan_human(
                group,
                group_loads,
                gate_decisions,
                solve_outcomes,
                schedule_results,
                payback_results,
                final_breakdowns,
                load_errors,
                payback_ratio,
            )
        )
    if topology.warnings:
        lines.append("Warnings:")
        lines.extend(f"  - {warning}" for warning in topology.warnings)
        lines.append("")
    return "\n".join(lines)


def _render_apply_human(
    topology: Topology,
    group_loads: dict[str, GroupLoad],
    gate_decisions: dict[str, GateDecision],
    solve_outcomes: dict[str, _SolveOutcome],
    schedule_results: dict[str, ScheduleResult],
    payback_results: dict[str, PaybackResult],
    final_breakdowns: dict[str, ObjectiveBreakdown],
    load_errors: dict[str, str],
    payback_ratio: float,
    execution_results: dict[str, ExecutionResult],
) -> str:
    lines: list[str] = []
    for group in topology.groups:
        lines.extend(
            _render_group_plan_human(
                group,
                group_loads,
                gate_decisions,
                solve_outcomes,
                schedule_results,
                payback_results,
                final_breakdowns,
                load_errors,
                payback_ratio,
                execution_results.get(group.name),
            )
        )
    if topology.warnings:
        lines.append("Warnings:")
        lines.extend(f"  - {warning}" for warning in topology.warnings)
        lines.append("")
    return "\n".join(lines)


def _render_group_plan_json(
    group: Group,
    decision: GateDecision | None,
    solve_outcome: _SolveOutcome | None,
    schedule_result: ScheduleResult | None,
    payback_result: PaybackResult | None,
    group_load: GroupLoad | None,
    final_breakdown: ObjectiveBreakdown | None,
    load_error: str | None,
) -> dict[str, object]:
    """One group's worth of ``_render_plan_json()``'s report -- shared
    with ``_render_apply_json()`` (AGENTS.md section 5), which adds its
    own ``"execution"`` key to the returned dict afterwards rather than
    this function knowing anything about execution at all."""
    load_by_key = group_load.load_by_disk_key() if group_load else {}
    move_costs_by_key = (
        {mc.disk_key: mc for mc in payback_result.move_costs} if payback_result else {}
    )
    moves_out = []
    if schedule_result is not None:
        for move in schedule_result.order:
            move_cost = move_costs_by_key.get(move.disk_key)
            moves_out.append(
                {
                    "disk_key": move.disk_key,
                    "vmid": move.vmid,
                    "device": move.device,
                    "from_storage": move.from_storage,
                    "to_storage": move.to_storage,
                    "size_bytes": move.size_bytes,
                    "imbalance_reduction": move.imbalance_reduction,
                    "resolves_reserve_violation": move.resolves_reserve_violation,
                    "load_per_tib": _load_per_tib(load_by_key, move.disk_key, move.size_bytes),
                    "duration_mirror_seconds": (
                        move_cost.duration_mirror_seconds if move_cost else None
                    ),
                    "duration_wipe_seconds": (
                        move_cost.duration_wipe_seconds if move_cost else None
                    ),
                    "cost_load_seconds": move_cost.cost_load_seconds if move_cost else None,
                    "exceeds_max_duration": (move_cost.exceeds_max_duration if move_cost else None),
                }
            )
    gate_out = None
    if decision is not None:
        gate_out = {
            "act": decision.act,
            "reason": decision.reason,
            "reserve_override": decision.reserve_override,
            "drift_fraction": decision.drift_fraction,
            "imbalance_fraction": decision.imbalance_fraction,
        }
    before_spread = after_spread = None
    if group_load is not None:
        before_spread = _spread_fraction(
            {s.storage_id: s.utilization for s in group_load.storages},
            group_load.average_utilization,
        )
        if final_breakdown is not None:
            after_spread = _spread_fraction(
                final_breakdown.utilization, group_load.average_utilization
            )
    payback_out = None
    if payback_result is not None:
        payback_out = {
            "benefit_load_seconds": payback_result.benefit_load_seconds,
            "total_cost_load_seconds": payback_result.total_cost_load_seconds,
            "ratio": payback_result.ratio,
            "aggregate_ok": payback_result.aggregate_ok,
            "rejected_moves": list(payback_result.rejected_moves),
            "deferred_moves": list(payback_result.deferred_moves),
            "accepted": payback_result.accepted,
        }
    return {
        "name": group.name,
        "load_error": load_error,
        "gate": gate_out,
        "solver_backend": solve_outcome.backend if solve_outcome else None,
        "solver_status": solve_outcome.status if solve_outcome else None,
        "moves": moves_out,
        "deadlocked": list(schedule_result.deadlocked) if schedule_result else [],
        "deadlock_message": schedule_result.deadlocked_msg if schedule_result else None,
        "before_spread": before_spread,
        "after_spread": after_spread,
        "payback": payback_out,
    }


def _render_plan_json(
    topology: Topology,
    group_loads: dict[str, GroupLoad],
    gate_decisions: dict[str, GateDecision],
    solve_outcomes: dict[str, _SolveOutcome],
    schedule_results: dict[str, ScheduleResult],
    payback_results: dict[str, PaybackResult],
    final_breakdowns: dict[str, ObjectiveBreakdown],
    load_errors: dict[str, str],
) -> dict[str, object]:
    groups_out = [
        _render_group_plan_json(
            group,
            gate_decisions.get(group.name),
            solve_outcomes.get(group.name),
            schedule_results.get(group.name),
            payback_results.get(group.name),
            group_loads.get(group.name),
            final_breakdowns.get(group.name),
            load_errors.get(group.name),
        )
        for group in topology.groups
    ]
    return {"groups": groups_out, "warnings": list(topology.warnings)}


# ------------------------------------------------------------------ explain
#
# `explain` runs the identical gate/solve/schedule/payback pipeline `plan`
# does (`_plan_group()`, one `_GroupPlan` per group -- AGENTS.md section 5)
# and renders everything `_render_group_plan_human()`/`_render_group_plan_json()`
# already show, plus the "why" sections 3.6/7.3/9.5 ask for that nothing else
# prints: which disks are pinned and why, which VMs that keeps fragmented
# across more than one storage, and whether the pinned load is large enough
# that the residual imbalance is structural rather than a planning failure
# (`report.warn_pinned_load_fraction`).


def _pinned_disks(group: Group) -> list[Disk]:
    """Every disk in ``group`` section 5.3 (C2) pins this run, in the same
    order ``show-load`` already lists disks (AGENTS.md section 5 -- one
    canonical ordering)."""
    return sorted(
        (d for d in group.disks if d.pinned_reason is not None),
        key=lambda d: (d.vmid, d.device),
    )


def _fragmented_vms(
    group: Group, assignment: Assignment | None
) -> list[tuple[int, str, list[Disk]]]:
    """Section 3.6: name the actual pinned disk(s) keeping one VM's disks
    spread across more than one storage, rather than only ever emitting a
    plan that quietly leaves a stray volume behind. ``assignment`` is the
    plan's own final placement when one was computed -- section 8's
    scheduler can leave some moves deadlocked, so this reflects the
    group's *actual* outcome, not an aspirational one (the same reasoning
    ``_plan_group()``'s own ``final_breakdown`` already applies, REVIEW.md
    R-02). With no plan at all (no gate ACT, or a load error upstream)
    ``assignment`` is ``None`` and each disk's own ``current_storage`` is
    used instead, so a fragmented VM is still named even on a run that
    computed nothing.

    A VM only counts as fragmented when at least one of its disks is
    pinned: a VM merely spread across storages by an ordinary, unpinned
    plan is not a blocker to report here -- it is the plan working as
    intended.
    """
    by_vmid: dict[int, list[Disk]] = {}
    for disk in group.disks:
        by_vmid.setdefault(disk.vmid, []).append(disk)
    result: list[tuple[int, str, list[Disk]]] = []
    for vmid, disks in sorted(by_vmid.items()):
        storages = {(assignment or {}).get(d.key, d.current_storage) for d in disks}
        if len(storages) <= 1:
            continue
        pinned = [d for d in disks if d.pinned_reason is not None]
        if not pinned:
            continue
        result.append((vmid, disks[0].vm_name, sorted(pinned, key=lambda d: d.device)))
    return result


def _pinned_load_fraction(
    group: Group, load_by_key: dict[str, float]
) -> tuple[float, float] | None:
    """``(pinned_load, total_load)`` for ``report.warn_pinned_load_fraction``,
    or ``None`` when there is no load to divide by -- an idle group, or one
    ``explain`` never got a load for -- so the caller can skip the line
    entirely rather than report a meaningless ``0/0``."""
    total = sum(load_by_key.get(d.key, 0.0) for d in group.disks)
    if total <= 0:
        return None
    pinned = sum(load_by_key.get(d.key, 0.0) for d in group.disks if d.pinned_reason is not None)
    return pinned, total


def _pin_action_hint(reason: str | None) -> str | None:
    """Section 9.5's per-pin action hint: what to actually do about a
    pin, distinct from the reason text (which only says why). ``None``
    for a standing policy exclusion (``exclude.*``, or a deliberately
    skipped ``unusedN`` disk) -- there is nothing to "unblock", the
    operator chose this, matching section 9.5's own example (its
    "excluded by tag" pin carries no hint either)."""
    if reason is None:
        return None
    if reason.startswith("snapshots present ("):
        return "clear snapshots to unblock"
    if reason.startswith("unreferenced companion volume"):
        return "remove the stale reference to unblock"
    if reason.startswith("cooldown:"):
        return "re-check next run"
    if reason.startswith("locked:"):
        return "re-check next run once the lock releases"
    return None


def _render_pinned_lines(group: Group, load_by_key: dict[str, float]) -> list[str]:
    pinned = _pinned_disks(group)
    if not pinned:
        return []
    lines = ["  pinned (not movable this run):"]
    for disk in pinned:
        load_str = f"  ℓ {load_by_key[disk.key]:.2f}" if disk.key in load_by_key else ""
        ratio = _load_per_tib(load_by_key, disk.key, disk.size_bytes)
        hint = _pin_action_hint(disk.pinned_reason)
        hint_str = f"  → {hint}" if hint else ""
        lines.append(
            f"    {disk.key:<14} {format_bytes(disk.size_bytes):>10}  on {disk.current_storage}"
            f"{load_str}  ℓ/z {ratio:.2f}  -- {disk.pinned_reason}{hint_str}"
        )
    return lines


def _render_fragmentation_lines(group: Group, assignment: Assignment | None) -> list[str]:
    fragmented = _fragmented_vms(group, assignment)
    if not fragmented:
        return []
    lines = ["  cannot fully consolidate:"]
    for vmid, vm_name, pinned in fragmented:
        blockers = ", ".join(f"{d.device}: {d.pinned_reason}" for d in pinned)
        lines.append(f"    {vmid} ({vm_name})  {blockers}")
    return lines


def _render_objective_breakdown_line(breakdown: ObjectiveBreakdown) -> str:
    """The section 5.4 objective's five terms, individually -- the reason
    :class:`ObjectiveBreakdown` keeps them apart instead of collapsing to
    only ``.total`` in the first place (that class's own docstring)."""
    return (
        "  objective: "
        f"imbalance {breakdown.imbalance_term:.3g} + "
        f"moves {breakdown.move_count_term:.3g} + "
        f"bytes {breakdown.bytes_moved_term:.3g} + "
        f"fragmentation {breakdown.fragmentation_term:.3g} + "
        f"reserve {breakdown.reserve_penalty_term:.3g} = {breakdown.total:.3g}"
    )


def _render_pinned_load_lines(
    group: Group,
    load_by_key: dict[str, float],
    warn_fraction: float,
    achievable_spread: float | None,
) -> list[str]:
    fractions = _pinned_load_fraction(group, load_by_key)
    if fractions is None:
        return []
    pinned_load, total_load = fractions
    fraction = pinned_load / total_load
    spread_str = (
        f";  best achievable spread given pins: {achievable_spread:.1%}"
        if achievable_spread is not None
        else ""
    )
    lines = [
        f"  pinned load {pinned_load:.2f} of {total_load:.2f} "
        f"({fraction:.1%}, warn at {warn_fraction:.0%}){spread_str}"
    ]
    if fraction > warn_fraction:
        lines.append(
            "  ⚠ pinned load exceeds report.warn_pinned_load_fraction -- the residual "
            "imbalance here may be structural (clear the pins above to improve it "
            "further), not a planning failure"
        )
    return lines


def _render_explain_data_source_line(resolved: ResolvedConfig, node_selector: str | None) -> str:
    """``-v``'s addition to ``explain`` (section 3.4): exactly which query
    every number above came from -- the node-scoping selector actually
    used, and the window/rate settings the whole run was computed against.
    A single line, not a whole section, since every group in one run
    shares this -- it is not something to repeat per group."""
    window = resolved.config.window
    metrics = resolved.config.metrics
    scope = f"{{{node_selector}}}" if node_selector else "(no node-scoping filter)"
    return (
        f"data source: {scope}  window {format_duration_seconds(window.lookback_seconds)} "
        f"lookback, quantile {window.quantile:g}, rate_window "
        f"{format_duration_seconds(metrics.rate_window_seconds)}, step "
        f"{format_duration_seconds(metrics.step_seconds)}"
    )


def _render_group_explain_human(
    group: Group, group_plan: "_GroupPlan", resolved: ResolvedConfig
) -> list[str]:
    if group_plan.load_error is not None:
        return [f"Group {group.name} — plan unavailable: {group_plan.load_error}", ""]
    assert group_plan.decision is not None
    payback_ratio = resolved.config.migration.payback_ratio
    warn_fraction = resolved.config.report.warn_pinned_load_fraction
    plan_lines = _render_group_plan_human(
        group,
        {group.name: group_plan.group_load} if group_plan.group_load else {},
        {group.name: group_plan.decision},
        {group.name: group_plan.solve_outcome} if group_plan.solve_outcome else {},
        {group.name: group_plan.schedule_result} if group_plan.schedule_result else {},
        {group.name: group_plan.payback_result} if group_plan.payback_result else {},
        {group.name: group_plan.final_breakdown} if group_plan.final_breakdown else {},
        {},
        payback_ratio,
    )

    load_by_key = group_plan.group_load.load_by_disk_key() if group_plan.group_load else {}
    assignment = group_plan.schedule_result.final_assignment if group_plan.schedule_result else None
    extra: list[str] = []
    if group_plan.final_breakdown is not None:
        extra.append(_render_objective_breakdown_line(group_plan.final_breakdown))
    # The measured load every number above derives from -- show-load's own
    # per-storage/per-disk picture, section 4 (AGENTS.md section 5: one
    # implementation, reused rather than a second rendering of it).
    reserve_statuses = {
        storage.id: compute_reserve_status(
            storage, group.disks, resolved.config.snapshot_reserve.min_free_bytes
        )
        for storage in group.storages
    }
    extra.append("  measured load:")
    extra.extend(
        _render_storage_and_disk_load_lines(group, group_plan.group_load, reserve_statuses)
    )
    extra.extend(_render_pinned_lines(group, load_by_key))
    extra.extend(_render_fragmentation_lines(group, assignment))
    achievable_spread = None
    if group_plan.decision.act and group_plan.final_breakdown is not None:
        assert group_plan.group_load is not None
        achievable_spread = _spread_fraction(
            group_plan.final_breakdown.utilization, group_plan.group_load.average_utilization
        )
    extra.extend(_render_pinned_load_lines(group, load_by_key, warn_fraction, achievable_spread))

    # `extra` is never empty -- the measured-load header above is
    # unconditional -- so unlike some earlier revisions of this function,
    # there is no "nothing to add" case left to special-case here.
    # `plan_lines` always ends with one blank separator line
    # (`_render_group_plan_human()`'s own contract) -- insert before it
    # rather than after, so groups stay separated by exactly one blank line.
    return plan_lines[:-1] + extra + [""]


def _render_explain_human(
    topology: Topology,
    group_plans: dict[str, "_GroupPlan"],
    resolved: ResolvedConfig,
    node_selector: str | None,
    verbose: bool,
) -> str:
    lines: list[str] = []
    # One line for the whole run, not per group: every group here was
    # computed against the identical node selector and window/rate
    # settings, so repeating it per group would say the same thing
    # `len(topology.groups)` times. `-v` only, per the operator's own
    # request -- the default report already grew a measured-load section
    # unconditionally; this is the one piece that is genuinely about
    # *how* the numbers were fetched, not what they are.
    if verbose:
        lines.append(_render_explain_data_source_line(resolved, node_selector))
        lines.append("")
    for group in topology.groups:
        lines.extend(_render_group_explain_human(group, group_plans[group.name], resolved))
    if topology.warnings:
        lines.append("Warnings:")
        lines.extend(f"  - {warning}" for warning in topology.warnings)
        lines.append("")
    return "\n".join(lines)


def _render_group_explain_json(
    group: Group, group_plan: "_GroupPlan", warn_fraction: float, min_free_bytes: int
) -> dict[str, object]:
    out = _render_group_plan_json(
        group,
        group_plan.decision,
        group_plan.solve_outcome,
        group_plan.schedule_result,
        group_plan.payback_result,
        group_plan.group_load,
        group_plan.final_breakdown,
        group_plan.load_error,
    )
    load_by_key = group_plan.group_load.load_by_disk_key() if group_plan.group_load else {}
    # The measured load every other field above derives from -- identical
    # shape to `show-load --json`'s own `storages`/`disks` (AGENTS.md
    # section 5: one implementation of what a storage/disk entry looks
    # like, not a second one that happens to agree today).
    storage_loads = (
        {s.storage_id: s for s in group_plan.group_load.storages} if group_plan.group_load else {}
    )
    flagged_by_key = (
        {d.disk_key: d.flagged_reason for d in group_plan.group_load.disks}
        if group_plan.group_load
        else {}
    )
    reserve_statuses = {
        storage.id: compute_reserve_status(storage, group.disks, min_free_bytes)
        for storage in group.storages
    }
    storages_out = []
    for storage in group.storages:
        status = reserve_statuses[storage.id]
        entry: dict[str, object] = {
            "id": storage.id,
            "used_bytes": storage.used_bytes,
            "capacity_bytes": storage.capacity_bytes,
            "foreign_used_bytes": storage.foreign_used_bytes,
            "largest_disk_bytes": status.largest_disk_bytes,
            "required_reserve_bytes": status.required_reserve_bytes,
            "reserve_violated": status.violated,
            "reserve_shortfall_bytes": status.shortfall_bytes,
        }
        if storage.id in storage_loads:
            entry["load"] = storage_loads[storage.id].load
            entry["utilization"] = storage_loads[storage.id].utilization
        storages_out.append(entry)
    out["storages"] = storages_out
    disks_out = []
    for d in group.disks:
        disk_entry: dict[str, object] = {
            "key": d.key,
            "vmid": d.vmid,
            "device": d.device,
            "vm_name": d.vm_name,
            "size_bytes": d.size_bytes,
            "current_storage": d.current_storage,
            "format": d.format,
            "pinned_reason": d.pinned_reason,
        }
        if d.key in load_by_key:
            disk_entry["load"] = load_by_key[d.key]
            disk_entry["load_flagged_reason"] = flagged_by_key.get(d.key)
        disks_out.append(disk_entry)
    out["disks"] = disks_out
    breakdown = group_plan.final_breakdown
    out["objective"] = (
        {
            "imbalance_term": breakdown.imbalance_term,
            "move_count_term": breakdown.move_count_term,
            "bytes_moved_term": breakdown.bytes_moved_term,
            "fragmentation_term": breakdown.fragmentation_term,
            "reserve_penalty_term": breakdown.reserve_penalty_term,
            "total": breakdown.total,
        }
        if breakdown is not None
        else None
    )
    out["pinned_disks"] = [
        {
            "disk_key": d.key,
            "vmid": d.vmid,
            "device": d.device,
            "current_storage": d.current_storage,
            "size_bytes": d.size_bytes,
            "load": load_by_key.get(d.key),
            "load_per_tib": _load_per_tib(load_by_key, d.key, d.size_bytes),
            "reason": d.pinned_reason,
            "action_hint": _pin_action_hint(d.pinned_reason),
        }
        for d in _pinned_disks(group)
    ]
    assignment = group_plan.schedule_result.final_assignment if group_plan.schedule_result else None
    out["fragmentation"] = [
        {
            "vmid": vmid,
            "vm_name": vm_name,
            "blockers": [
                {"device": d.device, "disk_key": d.key, "reason": d.pinned_reason} for d in pinned
            ],
        }
        for vmid, vm_name, pinned in _fragmented_vms(group, assignment)
    ]
    fractions = _pinned_load_fraction(group, load_by_key)
    pinned_load_out: dict[str, object] | None = None
    if fractions is not None:
        pinned_load, total_load = fractions
        pinned_load_out = {
            "pinned_load": pinned_load,
            "total_load": total_load,
            "fraction": pinned_load / total_load,
            "warn_fraction": warn_fraction,
        }
    out["pinned_load"] = pinned_load_out
    return out


def _render_explain_json(
    topology: Topology,
    group_plans: dict[str, "_GroupPlan"],
    resolved: ResolvedConfig,
    node_selector: str | None,
) -> dict[str, object]:
    warn_fraction = resolved.config.report.warn_pinned_load_fraction
    min_free_bytes = resolved.config.snapshot_reserve.min_free_bytes
    groups_out = [
        _render_group_explain_json(group, group_plans[group.name], warn_fraction, min_free_bytes)
        for group in topology.groups
    ]
    window = resolved.config.window
    metrics = resolved.config.metrics
    # Always present, unlike the human report's `-v`-gated line: JSON has
    # no notion of verbosity, and a consumer parsing this should not have
    # to guess whether the query provenance was included this run.
    query_out = {
        "node_selector": node_selector,
        "window_lookback_seconds": window.lookback_seconds,
        "quantile": window.quantile,
        "rate_window_seconds": metrics.rate_window_seconds,
        "step_seconds": metrics.step_seconds,
    }
    return {"groups": groups_out, "warnings": list(topology.warnings), "query": query_out}


def _render_execution_json(result: ExecutionResult | None) -> dict[str, object] | None:
    """``None`` for a group ``apply`` never got as far as executing (a
    load error, or the gate said ``NO ACTION``) -- distinct from a group
    that executed and produced zero outcomes, which cannot happen in
    practice but would render as an empty list, not ``None``."""
    if result is None:
        return None
    return {
        "stopped_early": result.stopped_early,
        "stop_reason": result.stop_reason,
        "outcomes": [
            {
                "disk_key": outcome.disk_key,
                "from_storage": outcome.from_storage,
                "to_storage": outcome.to_storage,
                "status": outcome.status,
                "detail": outcome.detail,
                "upid": outcome.upid,
                "orphaned_volumes": list(outcome.orphaned_volumes),
            }
            for outcome in result.outcomes
        ],
    }


def _render_apply_json(
    topology: Topology,
    group_loads: dict[str, GroupLoad],
    gate_decisions: dict[str, GateDecision],
    solve_outcomes: dict[str, _SolveOutcome],
    schedule_results: dict[str, ScheduleResult],
    payback_results: dict[str, PaybackResult],
    final_breakdowns: dict[str, ObjectiveBreakdown],
    load_errors: dict[str, str],
    execution_results: dict[str, ExecutionResult],
) -> dict[str, object]:
    """``plan``'s own JSON shape (section 9.5: "every mode emits the same
    machine-readable plan") plus one ``"execution"`` key per group --
    the per-move outcomes ``plan`` never has anything to report for."""
    groups_out = []
    for group in topology.groups:
        group_out = _render_group_plan_json(
            group,
            gate_decisions.get(group.name),
            solve_outcomes.get(group.name),
            schedule_results.get(group.name),
            payback_results.get(group.name),
            group_loads.get(group.name),
            final_breakdowns.get(group.name),
            load_errors.get(group.name),
        )
        group_out["execution"] = _render_execution_json(execution_results.get(group.name))
        groups_out.append(group_out)
    return {"groups": groups_out, "warnings": list(topology.warnings)}


@dataclasses.dataclass(frozen=True, slots=True)
class _SolveOutcome:
    """One group's solve, whichever backend actually produced it --
    `_render_plan_human()`/`_render_plan_json()` report `backend`/`status`
    the same way regardless, and everything downstream (`order_moves()`,
    the payback benefit) only ever needs `assignment`/`initial_breakdown`,
    which both `heuristic.HeuristicResult` and `optimize.OptimizeResult`
    already carry identically (both built from the one shared
    `heuristic.evaluate_assignment()` -- see `optimize.py`'s own module
    docstring)."""

    assignment: Assignment
    initial_breakdown: ObjectiveBreakdown
    backend: str  # "cpsat" | "cbc" | "heuristic"
    status: str | None  # "optimal" | "feasible" for a MILP backend, None for the heuristic


def _solve_group(
    group: Group,
    load_by_key: dict[str, float],
    resolved: ResolvedConfig,
    min_free_bytes: int,
    cooldown_storages: frozenset[str],
) -> _SolveOutcome:
    """Section 5.5's backend dispatch. ``solver.backend: auto`` cascades
    CP-SAT, then CBC, then the heuristic; an explicitly forced backend that
    cannot produce a plan (library not importable, or no feasible solution
    within ``solver.time_limit_seconds``) falls back to the heuristic too
    -- section 13's failure-mode table says plainly "solver infeasible or
    timing out -> fall back to the heuristic; never emit a partial/
    unvalidated assignment", with no carve-out for a backend the operator
    explicitly named (`docs/manual/10-configuration.md`'s own
    `solver.backend` text: forcing one is "to reproduce or compare a
    result", not to disable this safety net). A forced backend that falls
    back anyway is logged at warning -- an operator who asked for `cpsat`
    specifically should not have to diff `--json` output to notice `auto`
    quietly happened instead.
    """
    solver = resolved.config.solver
    cascade = {
        "auto": ("cpsat", "cbc"),
        "cpsat": ("cpsat",),
        "cbc": ("cbc",),
        "heuristic": (),
    }[solver.backend]
    for backend in cascade:
        result = optimize.solve(
            group,
            load_by_key,
            resolved.config.objective,
            min_free_bytes,
            backend,
            solver.time_limit_seconds,
            solver.mip_gap,
            cooldown_storages,
        )
        if result is not None:
            return _SolveOutcome(
                assignment=result.assignment,
                initial_breakdown=result.initial_breakdown,
                backend=result.backend,
                status=result.status,
            )
        if solver.backend != "auto":
            logger.warning(
                "solver.backend=%s could not produce a plan for this group; "
                "falling back to the heuristic",
                solver.backend,
                extra={
                    "event": "solver_fallback",
                    "group": group.name,
                    "requested": solver.backend,
                },
            )

    heuristic_result = run_heuristic(
        group,
        load_by_key,
        resolved.config.objective,
        min_free_bytes,
        solver.heuristic_iterations,
        cooldown_storages,
    )
    return _SolveOutcome(
        assignment=heuristic_result.assignment,
        initial_breakdown=heuristic_result.initial_breakdown,
        backend="heuristic",
        status=None,
    )


@dataclasses.dataclass(frozen=True, slots=True)
class _GroupPlan:
    """One group's fully-computed plan, or as far as it got -- the one
    implementation (AGENTS.md section 5) of "gates, load model, solver,
    payback, ordering" that both ``plan`` and ``apply`` build on, since
    section 9.2's re-plan protocol says to re-run exactly this pipeline,
    not a second one apply keeps for itself.

    ``load_error`` set means the load model itself could not be computed
    (a Prometheus outage) -- every other field is then ``None``.
    Otherwise ``group_load``/``decision`` are always set; the rest stay
    ``None`` when the gate decided not to act, since there is nothing to
    solve, schedule or pay back for a group that is not moving anything
    this run."""

    load_error: str | None = None
    group_load: GroupLoad | None = None
    decision: GateDecision | None = None
    solve_outcome: _SolveOutcome | None = None
    schedule_result: ScheduleResult | None = None
    final_breakdown: ObjectiveBreakdown | None = None
    payback_result: PaybackResult | None = None


def _saturation_forecast_inputs(
    prom_client: PrometheusClient,
    resolved: ResolvedConfig,
    group: Group,
    now: datetime,
    node_selector: str | None,
) -> tuple[Forecaster, dict[str, TimeSeries]] | None:
    """Section 7.3's saturation guard needs a forecaster and every disk's
    own load history -- but only when at least one storage in ``group``
    actually configures ``saturation_load``. Returns ``None`` to skip the
    guard entirely otherwise, matching the plan's own words literally: a
    group that leaves it unset everywhere "loses only this one advisory
    check", at no Prometheus cost -- fetching a history no storage in
    this group could ever use would contradict that.

    ``range_seconds`` is the *configured forecaster's* own requirement
    (``forecast.required_range_seconds()``), not ``window.lookback`` --
    section 10.1's own "genuinely different things" (`docs/internals/20-forecasting.md`).
    """
    if not any(s.saturation_load is not None for s in group.storages):
        return None
    forecast_config = resolved.config.forecast
    window = resolved.config.window
    metrics = resolved.config.metrics
    range_seconds = required_range_seconds(
        forecast_config, window.lookback_seconds, metrics.step_seconds
    )
    now_epoch = now.timestamp()
    forecaster = build_forecaster(
        forecast_config,
        window.lookback_seconds,
        metrics.step_seconds,
        now_epoch,
        window.quantile,
        window.upper_quantile,
    )
    disk_series = compute_disk_load_series(
        prom_client,
        metrics,
        resolved.config.load_weights,
        group,
        range_seconds,
        metrics.step_seconds,
        now_epoch,
        node_selector=node_selector,
    )
    forecaster = _backtest_gated_forecaster(
        forecaster, forecast_config, resolved, disk_series, now_epoch, window.lookback_seconds
    )
    return forecaster, disk_series


def _backtest_gated_forecaster(
    forecaster: Forecaster,
    forecast_config: ForecastConfig,
    resolved: ResolvedConfig,
    disk_series: dict[str, TimeSeries],
    now_epoch: float,
    window_seconds: float,
) -> Forecaster:
    """Section 10.2/phase 9's backtest validation gate: ``quantile``
    itself is never backtested (no fitting occurs, so there is nothing to
    validate and nothing more conservative to fall back to);
    ``seasonal_naive``/``holt_winters`` must have actually predicted the
    group's own recent past accurately (``forecast.backtest_validated()``,
    within ``gates.imbalance_threshold``) before section 7.3's saturation
    guard trusts them at all. A model that fails -- or that cannot yet be
    validated for lack of history -- falls back to ``quantile`` for this
    run, logged once at warning; a fresh deployment is not given a free
    pass just because it has no track record yet
    (`forecast.backtest_validated()`'s own docstring)."""
    if forecast_config.model == "quantile":
        return forecaster
    aggregate = group_aggregate_series(disk_series)
    threshold = resolved.config.gates.imbalance_threshold
    if backtest_validated(forecaster, aggregate, now_epoch, window_seconds, threshold):
        return forecaster
    logger.warning(
        "forecast.model %r did not accurately predict this group's own recent history (or "
        "there is not enough history yet to check); using the simpler quantile model for "
        "this run's saturation guard instead",
        forecast_config.model,
        extra={"event": "forecast_backtest_failed", "model": forecast_config.model},
    )
    window = resolved.config.window
    return build_forecaster(
        dataclasses.replace(forecast_config, model="quantile"),
        window_seconds,
        resolved.config.metrics.step_seconds,
        now_epoch,
        window.quantile,
        window.upper_quantile,
    )


def _compute_one_move_cost(
    move: ScheduledMove,
    storages_by_id: dict[str, Storage],
    group: Group,
    migration: MigrationConfig,
    saturation_inputs: tuple[Forecaster, dict[str, TimeSeries]] | None,
) -> MoveCost:
    """One move's section 7.1 cost, plus (only when ``saturation_inputs``
    is not ``None``) section 7.3's saturation defer check -- computing
    each endpoint's own ``L_hat_s(duration_mirror)`` from its *currently*
    resident disks (`payback.compute_move_cost()`'s own docstring on why
    not the moving disk's hypothetical arrival) before handing off to the
    pure cost function. Factored out of `_plan_group()`'s own list
    comprehension purely to stay within this project's flake8 complexity
    limit."""
    source = storages_by_id[move.from_storage]
    if saturation_inputs is None:
        return compute_move_cost(move, source, migration)
    forecaster, disk_series = saturation_inputs
    target = storages_by_id[move.to_storage]
    horizon = timedelta(seconds=mirror_duration_seconds(move, migration))
    src_keys = [d.key for d in group.disks if d.current_storage == move.from_storage]
    dst_keys = [d.key for d in group.disks if d.current_storage == move.to_storage]
    l_hat_src = storage_upper_bound(forecaster, disk_series, src_keys, horizon)
    l_hat_dst = storage_upper_bound(forecaster, disk_series, dst_keys, horizon)
    return compute_move_cost(
        move, source, migration, target=target, l_hat_src=l_hat_src, l_hat_dst=l_hat_dst
    )


def _plan_group(
    group: Group,
    resolved: ResolvedConfig,
    prom_client: PrometheusClient,
    min_free_bytes: int,
    last_loads_by_group: dict[str, dict[str, float] | None],
    state: State,
    now: datetime,
    node_selector: str | None = None,
) -> _GroupPlan:
    """One group's worth of ``_handle_plan``'s former loop body, unchanged
    in behaviour -- see :class:`_GroupPlan` for why this is shared with
    ``apply`` rather than duplicated. ``node_selector`` is
    ``_resolve_node_selector_for_run()``'s result, computed once per
    invocation by the caller (a live PVE client is not otherwise needed
    here)."""
    try:
        group_load = compute_group_load(
            prom_client,
            resolved.config.metrics,
            resolved.config.window,
            resolved.config.load_weights,
            group,
            last_known_loads=last_loads_by_group.get(group.name),
            node_selector=node_selector,
        )
    except MetricsError as exc:
        # Section 6: gating (and so planning) cannot proceed without a
        # load to gate on -- unlike show-load's size/reserve report,
        # nothing here is safe to show without it.
        return _GroupPlan(load_error=str(exc))

    reserve_statuses: dict[str, ReserveStatus] = {
        storage.id: compute_reserve_status(storage, group.disks, min_free_bytes)
        for storage in group.storages
    }
    decision = evaluate_group_gates(
        group_load,
        reserve_statuses,
        resolved.config.gates,
        last_load=last_loads_by_group.get(group.name),
    )
    if not decision.act:
        return _GroupPlan(group_load=group_load, decision=decision)

    cooldown_storages = frozenset(
        active_storage_cooldowns(
            state, group.name, resolved.config.gates.cooldown_per_storage_seconds, now
        )
    )
    solve_outcome = _solve_group(
        group, group_load.load_by_disk_key(), resolved, min_free_bytes, cooldown_storages
    )
    schedule_result = order_moves(
        group,
        solve_outcome.assignment,
        group_load.load_by_disk_key(),
        resolved.config.objective,
        min_free_bytes,
    )

    # The heuristic's own `.breakdown` is the *target* assignment's
    # objective -- every move it proposed, whether or not `order_moves()`
    # could actually schedule it. `final_breakdown` is instead evaluated
    # against `schedule_result.final_assignment`, the state reachable by
    # the moves that actually got ordered, so "after" reporting and the
    # payback benefit below both reflect the plan as it will really run,
    # not an aspirational one a partial deadlock never reaches
    # (REVIEW.md R-02).
    final_breakdown = evaluate_assignment(
        group,
        schedule_result.final_assignment,
        group_load.load_by_disk_key(),
        resolved.config.objective,
        min_free_bytes,
        group_average_utilization(group, group_load.load_by_disk_key()),
    )

    storages_by_id = {s.id: s for s in group.storages}
    # Only when there is a move to cost (REVIEW.md T-07): a fully
    # deadlocked plan (`order` empty) has no `_compute_one_move_cost()`
    # call to feed, so skip the guard's own `query_range` fetches
    # entirely rather than pay for up to 7 days of history at a 5-minute
    # step and throw the result away unused.
    saturation_inputs = (
        _saturation_forecast_inputs(prom_client, resolved, group, now, node_selector)
        if schedule_result.order
        else None
    )
    move_costs = [
        _compute_one_move_cost(
            move, storages_by_id, group, resolved.config.migration, saturation_inputs
        )
        for move in schedule_result.order
    ]
    spread_metric = resolved.config.objective.spread_metric
    benefit = compute_benefit_load_seconds(
        raw_spread(solve_outcome.initial_breakdown, spread_metric),
        raw_spread(final_breakdown, spread_metric),
        resolved.config.migration.payback_horizon_seconds,
    )
    payback_result = evaluate_plan_payback(
        move_costs, benefit, resolved.config.migration.payback_ratio
    )
    return _GroupPlan(
        group_load=group_load,
        decision=decision,
        solve_outcome=solve_outcome,
        schedule_result=schedule_result,
        final_breakdown=final_breakdown,
        payback_result=payback_result,
    )


def _handle_plan(resolved: ResolvedConfig, args: argparse.Namespace, mode: str) -> int:
    del mode
    client = build_pve_client(resolved.config.proxmox)
    # Read-only: plan never executes a migration, so -- like show-load --
    # it never takes state.py's advisory lock (see that module's docstring).
    # Read once, reused for build_topology()'s (C2) cooldown pin, the
    # gate's drift input, and run_heuristic()'s storage-cooldown exclusion.
    now = datetime.now(timezone.utc)
    state = load_state(resolved.config.state.path)
    topology = _filter_groups(
        build_topology(client, resolved.config, state=state, now=now), args.group
    )
    prom_client = PrometheusClient(resolved.config.prometheus)
    node_selector = _resolve_node_selector_for_run(client, resolved.config.metrics)
    min_free_bytes = resolved.config.snapshot_reserve.min_free_bytes
    last_loads_by_group = _last_loads_by_group(state, topology)

    group_loads: dict[str, GroupLoad] = {}
    gate_decisions: dict[str, GateDecision] = {}
    solve_outcomes: dict[str, _SolveOutcome] = {}
    schedule_results: dict[str, ScheduleResult] = {}
    payback_results: dict[str, PaybackResult] = {}
    final_breakdowns: dict[str, ObjectiveBreakdown] = {}
    load_errors: dict[str, str] = {}

    for group in topology.groups:
        group_plan = _plan_group(
            group,
            resolved,
            prom_client,
            min_free_bytes,
            last_loads_by_group,
            state,
            now,
            node_selector,
        )
        if group_plan.load_error is not None:
            load_errors[group.name] = group_plan.load_error
            continue
        assert group_plan.group_load is not None and group_plan.decision is not None
        group_loads[group.name] = group_plan.group_load
        gate_decisions[group.name] = group_plan.decision
        if not group_plan.decision.act:
            continue
        assert (
            group_plan.solve_outcome is not None
            and group_plan.schedule_result is not None
            and group_plan.final_breakdown is not None
            and group_plan.payback_result is not None
        )
        solve_outcomes[group.name] = group_plan.solve_outcome
        schedule_results[group.name] = group_plan.schedule_result
        final_breakdowns[group.name] = group_plan.final_breakdown
        payback_results[group.name] = group_plan.payback_result

    if args.json:
        print(
            json.dumps(
                _render_plan_json(
                    topology,
                    group_loads,
                    gate_decisions,
                    solve_outcomes,
                    schedule_results,
                    payback_results,
                    final_breakdowns,
                    load_errors,
                ),
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(
            _render_plan_human(
                topology,
                group_loads,
                gate_decisions,
                solve_outcomes,
                schedule_results,
                payback_results,
                final_breakdowns,
                load_errors,
                resolved.config.migration.payback_ratio,
            )
        )
    return 0


def _handle_explain(resolved: ResolvedConfig, args: argparse.Namespace, mode: str) -> int:
    """``explain`` (section 12): the identical read-only
    gate/solve/schedule/payback pipeline ``plan`` runs (``_plan_group()``,
    the shared ``_GroupPlan`` -- AGENTS.md section 5), narrated with the
    "why" ``plan`` itself never prints: the measured load every number
    derives from (``show-load``'s own per-storage/per-disk section 4
    picture, reused verbatim), which disks are pinned and why, which VMs
    that leaves fragmented across more than one storage, and whether the
    pinned load is large enough that the residual imbalance is structural
    (``report.warn_pinned_load_fraction``) rather than a planning failure.
    ``-v`` additionally names the exact node-scoping selector and window/
    rate settings the whole run's queries were built from -- the one
    piece of this that is about *how* the data was fetched, not what it
    is, and shared by every group in the run rather than repeated per
    group. Never executes anything -- exactly like ``plan``, it never
    takes ``state.py``'s advisory lock."""
    del mode
    client = build_pve_client(resolved.config.proxmox)
    now = datetime.now(timezone.utc)
    state = load_state(resolved.config.state.path)
    topology = _filter_groups(
        build_topology(client, resolved.config, state=state, now=now), args.group
    )
    prom_client = PrometheusClient(resolved.config.prometheus)
    node_selector = _resolve_node_selector_for_run(client, resolved.config.metrics)
    min_free_bytes = resolved.config.snapshot_reserve.min_free_bytes
    last_loads_by_group = _last_loads_by_group(state, topology)

    group_plans = {
        group.name: _plan_group(
            group,
            resolved,
            prom_client,
            min_free_bytes,
            last_loads_by_group,
            state,
            now,
            node_selector,
        )
        for group in topology.groups
    }

    if args.json:
        print(
            json.dumps(
                _render_explain_json(topology, group_plans, resolved, node_selector),
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(
            _render_explain_human(
                topology, group_plans, resolved, node_selector, verbose=args.verbose > 0
            )
        )
    return 0


def _confirm_move_interactively(move: ScheduledMove) -> str:
    """The only ``input()`` call in this codebase -- ``execute.py``'s own
    module docstring reserves interactive prompting for ``cli.py``, since
    it is the only module allowed to talk to the terminal (see this
    module's own docstring). Loops on anything but ``y``/``n``/``a``/``q``
    rather than handing ``execute_plan()`` a value its ``ConfirmCallback``
    contract does not accept -- retrying badly-typed input is this
    function's job, not a ``ValueError`` execute.py would have to raise
    and this function would have to catch anyway."""
    prompt = (
        f"  {move.disk_key}  {move.from_storage} → {move.to_storage}  "
        f"{format_bytes(move.size_bytes)}  [y]es/[n]o skip/[a]ll remaining/[q]uit? "
    )
    while True:
        answer = input(prompt).strip().lower()
        if answer in ("y", "n", "a", "q"):
            return answer
        print("  please answer y, n, a or q", file=sys.stderr)


@dataclasses.dataclass
class _InflightStateBox:
    """A mutable box around the one field of ``state`` that
    `execute.execute_plan()`'s own crash-recovery callbacks (see
    ``execute.InflightCallback``) need to update *synchronously*, from
    inside a running move, rather than only once `_handle_apply()`'s own
    loop gets back control (see :func:`_make_inflight_callbacks`). A
    deliberate, narrow exception to this codebase's functional state
    -threading style everywhere else (AGENTS.md; `docs/internals/92-execute.md`),
    forced by section 13's own requirement: a value only ever persisted at
    the end of a whole `apply` run cannot protect against the engine
    itself dying (killed, host reboot) partway through one."""

    value: State


def _make_inflight_callbacks(
    lock_handle: LockHandle, box: _InflightStateBox
) -> tuple[InflightCallback, InflightCallback]:
    """Builds the ``on_inflight_started``/``on_inflight_finished`` pair
    `execute_plan()` calls immediately after issuing (respectively,
    completing) each `move_disk` in `confirm`/`auto` mode. Each write
    goes straight to disk via :func:`save_locked_state`, through the same
    still-held lock `_handle_apply()` itself will eventually release —
    see `crashrecovery.py`'s module docstring for why this has to happen
    in real time rather than only once at the end of the run."""

    def on_started(upid: str) -> None:
        box.value = with_inflight_upid(box.value, upid)
        save_locked_state(lock_handle, box.value)

    def on_finished(upid: str) -> None:
        box.value = without_inflight_upid(box.value, upid)
        save_locked_state(lock_handle, box.value)

    return on_started, on_finished


def _refused_move_outcomes(
    order: tuple[ScheduledMove, ...], payback: PaybackResult
) -> list[MoveOutcome]:
    """The two section 7.3 per-move exclusions -- the hard duration rule
    (``rejected_moves``) and the best-effort saturation guard
    (``deferred_moves``) -- rendered as ``"skipped"`` outcomes, in that
    priority order for a move flagged by both (the hard rule is the more
    definitive reason). Factored out of :func:`_apply_payback_gate` purely
    to stay within this project's flake8 complexity limit."""
    rejected_keys = set(payback.rejected_moves)
    deferred_keys = set(payback.deferred_moves)
    outcomes: list[MoveOutcome] = []
    for m in order:
        if m.disk_key in rejected_keys:
            detail = "refused: would take longer than migration.max_single_move_duration allows"
        elif m.disk_key in deferred_keys:
            detail = (
                "deferred: would push a target storage's I/O over migration."
                "saturation_ceiling -- re-evaluate on a later run"
            )
        else:
            continue
        outcomes.append(MoveOutcome(m.disk_key, m.from_storage, m.to_storage, "skipped", detail))
    return outcomes


def _apply_payback_gate(
    client: PveClient,
    group: Group,
    group_plan: _GroupPlan,
    migration: MigrationConfig,
    execution: ExecutionConfig,
    min_free_bytes: int,
    mode: str,
    payback_ratio: float,
    exclude: ExcludeConfig,
    confirm: ConfirmCallback | None,
    deadline: datetime | None = None,
    max_migrations: int | None = None,
    on_inflight_started: InflightCallback | None = None,
    on_inflight_finished: InflightCallback | None = None,
) -> ExecutionResult:
    """Section 7.3's payback verdict gates *execution*, not merely the
    report (REVIEW.md S-02): a move `rejected_moves` names (the hard
    per-move `migration.max_single_move_duration` rule) or `deferred_moves`
    names (the best-effort saturation guard) must never reach `execute.py`
    regardless of the plan's aggregate economics, and a plan that fails
    the aggregate economic test (``not aggregate_ok``) must not be
    executed at all. This is the same "report, never force" policy
    `payback.py` itself follows (a reserve-resolving plan is exempted
    from the economic half there, never from the hard duration rule) --
    applied here to mean the tool also refuses *on its own verdict*,
    rather than reporting a plan as rejected in one command and executing
    it anyway in the next. `execute.py`'s `_wait_for_move_completion()`
    docstring's assumption ("a move that was accepted at planning time
    already passed `migration.max_single_move_duration`") is only true by
    construction because of the filtering below -- until now it was
    simply false.

    A refused move's outcome is reported exactly like any other
    `execute_plan()` outcome (``status="skipped"``) so the shared
    renderers need no special case for it; ``execute_plan()`` itself is
    never called at all when the aggregate test fails, so a rejected plan
    issues zero API calls, the same as `dry-run`.

    ``deadline``/``max_migrations`` are threaded straight through to
    `execute.execute_plan()` -- ``auto`` mode's own section 9.1 budgets
    (`_handle_apply()` is the only caller that ever passes non-``None``
    values for either, and computes ``group_plan.payback_result.move_costs``
    into the ``move_costs_by_key`` `execute_plan()` needs for the deadline
    estimate).

    ``on_inflight_started``/``on_inflight_finished`` are threaded straight
    through too -- section 13's crash-recovery hooks, built once by
    `_handle_apply()` (:func:`_make_inflight_callbacks`) and passed down
    through here and (in ``auto`` mode) :func:`_run_auto_group` unchanged.
    """
    assert group_plan.schedule_result is not None and group_plan.payback_result is not None
    order = group_plan.schedule_result.order
    payback = group_plan.payback_result
    excluded_keys = set(payback.rejected_moves) | set(payback.deferred_moves)
    refused = _refused_move_outcomes(order, payback)

    if not payback.aggregate_ok:
        refused.extend(
            MoveOutcome(
                m.disk_key,
                m.from_storage,
                m.to_storage,
                "skipped",
                "refused: this plan's balance benefit does not outweigh its migration cost "
                f"(ratio {payback.ratio:.3g}, need {payback_ratio:g})",
            )
            for m in order
            if m.disk_key not in excluded_keys
        )
        return ExecutionResult(
            outcomes=tuple(refused),
            stopped_early=True,
            stop_reason="this plan's balance benefit does not outweigh its migration cost",
        )

    kept = tuple(m for m in order if m.disk_key not in excluded_keys)
    if not kept:
        # Every move was individually rejected -- nothing left to
        # execute, but that is not "stopped early": there was nothing
        # this run could have done about it either way.
        return ExecutionResult(outcomes=tuple(refused), stopped_early=False, stop_reason=None)

    filtered = dataclasses.replace(group_plan.schedule_result, order=kept)
    move_costs_by_key = {mc.disk_key: mc for mc in payback.move_costs}
    executed = execute_plan(
        client,
        group,
        filtered,
        migration,
        execution,
        min_free_bytes,
        mode,
        exclude,
        confirm=confirm,
        deadline=deadline,
        move_costs_by_key=move_costs_by_key,
        max_migrations=max_migrations,
        on_inflight_started=on_inflight_started,
        on_inflight_finished=on_inflight_finished,
    )
    return ExecutionResult(
        outcomes=tuple(refused) + executed.outcomes,
        stopped_early=executed.stopped_early,
        stop_reason=executed.stop_reason,
    )


def _real_local_now() -> datetime:
    """The host's local time, DST-aware across date arithmetic when
    possible -- reads ``/etc/localtime``'s own symlink target for the
    IANA zone name (the standard mechanism on Debian and virtually every
    other Linux distribution; this project packages for Debian only, see
    ``pyproject.toml``) rather than ``datetime.now().astimezone()``'s
    *fixed*-offset ``tzinfo``. The distinction matters specifically for
    `timewindow.window_close()`'s "closes tomorrow" case (an overnight
    window): a fixed offset carries today's UTC offset forward onto
    tomorrow's date unchanged, which is wrong by exactly the DST shift
    on the two nights a year a DST-observing zone's clocks actually
    change (an overnight window could then stay "active" up to an hour
    longer than configured, on that one night). Falls back to the
    fixed-offset form when the zone name cannot be determined (no
    ``/etc/localtime`` symlink, or a zone the local `tzdata` lacks) --
    correct on every date except those same two nights, exactly as
    `timewindow.py`'s own module docstring documents for that fallback
    case.
    """
    try:
        zone_name = os.path.realpath("/etc/localtime").split("zoneinfo/", 1)[1]
        return datetime.now(ZoneInfo(zone_name))
    except (IndexError, OSError, ZoneInfoNotFoundError):
        return datetime.now().astimezone()


def _run_auto_group(
    client: PveClient,
    resolved: ResolvedConfig,
    prom_client: PrometheusClient,
    min_free_bytes: int,
    state_box: _InflightStateBox,
    group: Group,
    group_plan: _GroupPlan,
    migrations_budget: int | None,
    node_selector: str | None = None,
    on_inflight_started: InflightCallback | None = None,
    on_inflight_finished: InflightCallback | None = None,
    local_now: Callable[[], datetime] = _real_local_now,
) -> tuple[ExecutionResult, int | None]:
    """``auto`` mode's own orchestration: section 9.1's time-window budget
    and section 9.2's re-plan protocol, bounded by
    ``execution.max_replans_per_run``. Everything reported here
    (`group_loads`/`gate_decisions`/etc.) still comes from the *initial*
    ``group_plan`` its caller already recorded -- a re-plan here changes
    what gets *executed*, not what the report says the group's plan was,
    which keeps this function from having to hand back a `_GroupPlan`
    that might, after a re-plan concludes "no action needed", have every
    solve/schedule/payback field `None`. What this function does return
    is one `ExecutionResult` accumulating *every* attempt's outcomes, so
    the report shows the whole story (initial attempt, why it stopped,
    what the re-plan did next), plus the updated, cross-group
    ``migrations_budget`` (``execution.max_migrations_per_run`` is a
    per-*invocation* cap, shared across every group `_handle_apply()`
    visits, not reset per group or per re-plan).

    ``state_box`` -- the same mutable box `_handle_apply()`'s own
    crash-recovery callbacks write ``inflight_upids`` through -- is
    threaded here (rather than a plain ``State``) so this function can
    record each *attempt's* own executed moves (cooldowns, ``last_balance``)
    into it immediately, before a re-plan re-invokes the pipeline: section
    9.2 step 2 requires the recording to precede step 3's re-plan, and a
    re-plan inside this same loop must see the previous attempt's own
    moves as history, not re-propose the disk that attempt just moved
    (REVIEW.md T-02). The same incremental write is also what lets
    `_handle_apply()`'s `finally` block save a mid-group crash's completed
    attempts' cooldowns, not just its `inflight_upids`.

    ``local_now`` -- real host local time by default -- is injectable for
    the same reason `execute.py`'s own `Clock` is: a test needs a
    deterministic answer to "is now inside this configured window"
    without actually waiting for (or being sensitive to) real wall-clock
    time (`.agents/testing.md`).

    ``on_inflight_started``/``on_inflight_finished`` are passed straight
    through to every `_apply_payback_gate()` call this function makes,
    including across a re-plan -- section 13's crash-recovery hooks do
    not care which plan attempt a move came from, only that every
    `move_disk` this run issues is bracketed by one of each.
    """
    execution = resolved.config.execution
    replans_left = execution.max_replans_per_run
    all_outcomes: list[MoveOutcome] = []
    stopped_early = False
    stop_reason: str | None = None

    while True:
        assert (
            group_plan.schedule_result is not None
            and group_plan.payback_result is not None
            and group_plan.group_load is not None
        )
        # Local wall-clock time -- `timewindow.py`'s own module docstring
        # explains why a human-configured HH:MM window is matched against
        # the host's local time, not UTC.
        now = local_now()
        deadline = current_deadline(execution.time_windows, now)
        if deadline is not None and deadline <= now:
            refused = tuple(
                MoveOutcome(
                    m.disk_key,
                    m.from_storage,
                    m.to_storage,
                    "skipped",
                    "outside execution.time_windows",
                )
                for m in group_plan.schedule_result.order
            )
            all_outcomes.extend(refused)
            stopped_early = True
            stop_reason = "outside execution.time_windows"
            break

        result = _apply_payback_gate(
            client,
            group,
            group_plan,
            resolved.config.migration,
            execution,
            min_free_bytes,
            "auto",
            resolved.config.migration.payback_ratio,
            resolved.config.exclude,
            None,
            deadline=deadline,
            max_migrations=migrations_budget,
            on_inflight_started=on_inflight_started,
            on_inflight_finished=on_inflight_finished,
        )
        all_outcomes.extend(result.outcomes)
        stopped_early = result.stopped_early
        stop_reason = result.stop_reason
        if migrations_budget is not None:
            # Launches only (REVIEW.md T-06), matching both executors'
            # own `migrations_used` counters: `o.upid` is only ever set
            # once `move_disk` actually returned one, which excludes a
            # lock-timeout-abort `"failed"` and every `"skipped"` outcome
            # (neither issued a move) from consuming this cross-group
            # budget.
            used = sum(1 for o in result.outcomes if o.upid is not None)
            migrations_budget = max(migrations_budget - used, 0)
        # Section 9.2 step 2, done *before* step 3 below re-plans (T-02):
        # record this attempt's own executed moves against `group_plan`'s
        # own load reading -- already computed, no extra
        # `compute_group_load()` call -- so a re-plan sees them as
        # history rather than re-deriving (or re-proposing) them.
        state_box.value = _record_executed_moves(
            state_box.value,
            group.name,
            group_plan.group_load.load_by_disk_key(),
            result.outcomes,
        )

        # Membership, not position (T-01): the concurrent executor cannot
        # return the moment a `replan_needed` mismatch is found -- it
        # keeps polling every other already-in-flight move to its own
        # conclusion first (`_execute_concurrent()`'s own docstring), so
        # a `replan_needed` outcome can land anywhere in `result.outcomes`,
        # not only last. `"replan_needed"` is only ever produced at launch
        # time, never by polling an in-flight move, so this cannot fire
        # for an outcome that was actually a clean completion.
        needs_replan = any(o.status == "replan_needed" for o in result.outcomes)
        if not needs_replan:
            break
        if replans_left <= 0:
            # Section 9.2 step 4: "on exceeding it, stop and report -- a
            # cluster churning faster than the engine can plan is a
            # condition for a human to look at, not to iterate against."
            stop_reason = (
                f"execution.max_replans_per_run ({execution.max_replans_per_run}) exceeded "
                f"(last mismatch: {stop_reason})"
            )
            break
        replans_left -= 1

        # Section 9.2 step 3: "re-invoke the whole pipeline from the new
        # observed state" -- topology included, not just the plan, since
        # whatever triggered the mismatch (a VM live-migrated, a storage
        # reconfigured) can mean the group's own membership changed too.
        fresh_now = datetime.now(timezone.utc)
        fresh_topology = build_topology(
            client, resolved.config, state=state_box.value, now=fresh_now
        )
        fresh_group = next((g for g in fresh_topology.groups if g.name == group.name), None)
        if fresh_group is None:
            stop_reason = f"group {group.name!r} no longer exists after re-planning"
            break
        fresh_last_loads = _last_loads_by_group(state_box.value, fresh_topology)
        new_plan = _plan_group(
            fresh_group,
            resolved,
            prom_client,
            min_free_bytes,
            fresh_last_loads,
            state_box.value,
            fresh_now,
            node_selector,
        )
        if (
            new_plan.load_error is not None
            or new_plan.decision is None
            or not new_plan.decision.act
            or new_plan.schedule_result is None
        ):
            # Re-planning concluded no further action is needed, or hit a
            # load error -- "the gates may well conclude no further
            # action is needed, which is a correct outcome" (section
            # 9.2 step 3), not a failure to report as one.
            stopped_early = False
            stop_reason = None
            break
        group = fresh_group
        group_plan = new_plan

    return ExecutionResult(tuple(all_outcomes), stopped_early, stop_reason), migrations_budget


def _record_executed_moves(
    state: State,
    group_name: str,
    load_by_key: dict[str, float],
    outcomes: tuple[MoveOutcome, ...],
) -> State:
    """Section 11.2: ``last_balance``/cooldowns are "updated only after a
    run that executed at least one migration" -- ``"moved"`` and
    ``"draining"`` both count (the mirror itself completed either way,
    mirroring `execute.py`'s own (C4) accounting choice for the same two
    statuses), ``"would_move"``/``"skipped"``/``"failed"``/
    ``"replan_needed"``/a payback refusal do not. Derived from
    ``outcomes`` directly, never a `_GroupPlan`'s own
    ``schedule_result.order``: a payback refusal (S-02) can already make
    ``outcomes`` a reordered subset of that order, and in ``auto`` mode a
    re-plan (:func:`_run_auto_group`) can execute moves from a *later*
    plan attempt that never appeared in the first attempt's order at
    all -- factored out of `_handle_apply()`'s own loop purely to stay
    within this project's flake8 complexity limit."""
    executed = [o for o in outcomes if o.status in ("moved", "draining")]
    if not executed:
        return state
    # The load reading recorded here is the caller's own -- in `auto`
    # mode after a re-plan, the *first* attempt's, not whichever later
    # attempt actually executed the move. A real, deliberate
    # simplification: re-fetching the load model again here just to
    # refresh `last_balance` by a few minutes' drift is not worth a
    # second `compute_group_load()` call on this path.
    state = with_recorded_balance(state, group_name, load_by_key)
    timestamp = now_iso()
    # Both endpoints get a timestamp -- section 6's own words are "a
    # storage **involved in** a migration ... accepts no new incoming
    # moves", and section 9.3's knob-sizing rule ("cooldown_per_storage
    # must exceed the expected wipe time ... or the next run will plan
    # moves onto a storage that is still draining") is specifically about
    # the *source*, where the saferemove wipe actually runs (REVIEW.md
    # S-03: recording the destination only can never protect a draining
    # source, no matter how long the cooldown is configured for). This is
    # a *recording* decision only -- which storages get a timestamp;
    # `heuristic.py`'s own *enforcement* of that cooldown stays
    # destination-only, excluding a cooldown storage as a move/swap
    # target but never as a source (docs/internals/90-heuristic.md),
    # which is unaffected by recording the source's own timestamp here
    # too.
    storage_keys = {storage_state_key(group_name, o.to_storage): timestamp for o in executed}
    storage_keys.update(
        {storage_state_key(group_name, o.from_storage): timestamp for o in executed}
    )
    disk_keys = {}
    for o in executed:
        vmid_str, device = o.disk_key.split(":", 1)
        disk_keys[disk_state_key(group_name, int(vmid_str), device)] = timestamp
    return with_recorded_cooldown(state, disk_keys=disk_keys, storage_keys=storage_keys)


def _reconcile_inflight_and_fold_exclusions(
    client: PveClient, resolved: ResolvedConfig, state_box: _InflightStateBox
) -> tuple[ResolvedConfig, State]:
    """Section 13's own words: "on startup, check for running move_disk
    UPIDs owned by the DRS user" -- *before planning anything*, which is
    why `_handle_apply()` calls this immediately after building the PVE
    client and nowhere else. A discovered vmid is folded into
    ``exclude.vmids`` on the returned, otherwise-identical
    ``ResolvedConfig``, reusing `topology.py`'s existing (C2) pin rather
    than a second exclusion mechanism (AGENTS.md section 5) --
    `crashrecovery.py`'s own `logger.warning()` calls already told the
    operator *why* a vmid it names shows up pinned in the report.
    Factored out of `_handle_apply()` purely to stay within this
    project's flake8 complexity limit."""
    inflight_vmids, state_box.value = reconcile_inflight(
        client, state_box.value, resolved.config.proxmox.auth
    )
    if not inflight_vmids:
        return resolved, state_box.value
    merged_vmids = tuple(sorted(set(resolved.config.exclude.vmids) | inflight_vmids))
    resolved = dataclasses.replace(
        resolved,
        config=dataclasses.replace(
            resolved.config,
            exclude=dataclasses.replace(resolved.config.exclude, vmids=merged_vmids),
        ),
    )
    return resolved, state_box.value


def _handle_apply(resolved: ResolvedConfig, args: argparse.Namespace, mode: str) -> int:
    """Section 9: execute (``confirm``/``auto``) or merely report
    (``dry-run``) the same per-group pipeline ``plan`` computes --
    :func:`_plan_group` is the one implementation of it every mode
    shares (AGENTS.md section 5), so there is no separate "apply's own
    solve/schedule" to drift out of sync with what ``plan`` just showed
    the operator. ``auto`` additionally runs :func:`_run_auto_group`'s
    section 9.1/9.2 orchestration (time windows, `max_migrations_per_run`,
    the bounded re-plan loop) instead of a single `_apply_payback_gate()`
    call.

    ``execution.max_concurrent_migrations``/``max_concurrent_per_storage``
    above `1` are honoured only in `auto` mode: `execute.execute_plan()`
    itself dispatches to its own concurrent executor once either is
    configured above its default of `1` (`docs/internals/92-execute.md`),
    strictly FIFO and `auto`-only -- `dry-run`/`confirm` always run
    strictly sequentially regardless of these settings, matching section
    9.1's own per-mode description, which discusses concurrency only
    under `auto`.
    """
    now = datetime.now(timezone.utc)
    state = load_state(resolved.config.state.path)

    # Unlike plan/show-load, apply can actually execute a migration, so it
    # is the one command state.py's advisory lock exists to protect
    # (state.py's own module docstring). Section 11.2: "a live PID means
    # another instance is running: exit 0 quietly" -- this is that "quiet
    # exit", for every mode including dry-run, so a second concurrent
    # invocation never races the first over which one gets to write
    # state.json's last_balance/cooldowns at the end. Checked before
    # touching PVE or Prometheus at all -- an instance that cannot run
    # this pass has no reason to pay for either round-trip first.
    lock_handle = acquire_lock(resolved.config.state.path)
    if lock_handle is None:
        logger.info(
            "state.json is already locked by another running instance; exiting quietly",
            extra={"event": "apply_lock_held", "path": resolved.config.state.path},
        )
        return 0

    # Section 13's own in-flight box: `execute.execute_plan()`'s
    # crash-recovery callbacks write into this synchronously (see
    # `_make_inflight_callbacks()`), so the plain `state` variable this
    # function otherwise threads functionally is re-synced from it after
    # every group's execution below, and again for the final
    # `save_locked_state()` call in `finally`.
    state_box = _InflightStateBox(state)
    on_inflight_started, on_inflight_finished = _make_inflight_callbacks(lock_handle, state_box)

    group_loads: dict[str, GroupLoad] = {}
    gate_decisions: dict[str, GateDecision] = {}
    solve_outcomes: dict[str, _SolveOutcome] = {}
    schedule_results: dict[str, ScheduleResult] = {}
    payback_results: dict[str, PaybackResult] = {}
    final_breakdowns: dict[str, ObjectiveBreakdown] = {}
    load_errors: dict[str, str] = {}
    execution_results: dict[str, ExecutionResult] = {}

    try:
        client = build_pve_client(resolved.config.proxmox)
        resolved, state = _reconcile_inflight_and_fold_exclusions(client, resolved, state_box)

        topology = _filter_groups(
            build_topology(client, resolved.config, state=state, now=now), args.group
        )
        prom_client = PrometheusClient(resolved.config.prometheus)
        node_selector = _resolve_node_selector_for_run(client, resolved.config.metrics)
        min_free_bytes = resolved.config.snapshot_reserve.min_free_bytes
        last_loads_by_group = _last_loads_by_group(state, topology)
        # execution.max_migrations_per_run is a per-*invocation* cap,
        # shared across every group this run visits -- not reset per
        # group. Only ever consulted in `auto` mode (`_run_auto_group()`
        # is the only caller that ever passes a non-`None` value on to
        # `execute_plan()`).
        migrations_budget: int | None = (
            resolved.config.execution.max_migrations_per_run if mode == "auto" else None
        )

        for group in topology.groups:
            group_plan = _plan_group(
                group,
                resolved,
                prom_client,
                min_free_bytes,
                last_loads_by_group,
                state,
                now,
                node_selector,
            )
            if group_plan.load_error is not None:
                load_errors[group.name] = group_plan.load_error
                continue
            assert group_plan.group_load is not None and group_plan.decision is not None
            group_loads[group.name] = group_plan.group_load
            gate_decisions[group.name] = group_plan.decision
            if not group_plan.decision.act:
                continue
            assert (
                group_plan.solve_outcome is not None
                and group_plan.schedule_result is not None
                and group_plan.final_breakdown is not None
                and group_plan.payback_result is not None
            )
            solve_outcomes[group.name] = group_plan.solve_outcome
            schedule_results[group.name] = group_plan.schedule_result
            final_breakdowns[group.name] = group_plan.final_breakdown
            payback_results[group.name] = group_plan.payback_result

            if mode == "confirm" and group_plan.schedule_result.order:
                # Section 7.3's verdict is shown *before* the first
                # prompt, not only in the post-run report -- an operator
                # confirming moves one at a time deserves to know the
                # tool's own payback verdict (including a hard-duration
                # rejection) before being asked anything, not after
                # everything already ran (REVIEW.md S-02). Just the
                # payback lines, not the whole group block the final
                # report already prints in full -- this is a preview, not
                # a second copy of it.
                for line in _render_plan_payback_lines(
                    group_plan.payback_result, resolved.config.migration.payback_ratio
                ):
                    print(line)

            if mode == "auto":
                result, migrations_budget = _run_auto_group(
                    client,
                    resolved,
                    prom_client,
                    min_free_bytes,
                    state_box,
                    group,
                    group_plan,
                    migrations_budget,
                    node_selector=node_selector,
                    on_inflight_started=on_inflight_started,
                    on_inflight_finished=on_inflight_finished,
                )
            else:
                confirm_callback = _confirm_move_interactively if mode == "confirm" else None
                result = _apply_payback_gate(
                    client,
                    group,
                    group_plan,
                    resolved.config.migration,
                    resolved.config.execution,
                    min_free_bytes,
                    mode,
                    resolved.config.migration.payback_ratio,
                    resolved.config.exclude,
                    confirm_callback,
                    on_inflight_started=on_inflight_started,
                    on_inflight_finished=on_inflight_finished,
                )
            execution_results[group.name] = result
            if mode == "auto":
                # `_run_auto_group()` already recorded every attempt's own
                # executed moves into `state_box` as it went (T-02), each
                # against that attempt's own load reading -- recording
                # again here with `group_plan`'s *first*-attempt reading
                # would silently overwrite a later re-plan attempt's own,
                # fresher `last_balance` with a stale one.
                state = state_box.value
            else:
                # Pick up whatever `on_inflight_started`/`on_inflight_finished`
                # wrote to `state_box` while this group's moves ran, before
                # layering this group's own cooldowns/balance on top -- and
                # push the combined result back into the box so the *next*
                # group's callbacks build on it rather than reverting these.
                state = _record_executed_moves(
                    state_box.value,
                    group.name,
                    group_plan.group_load.load_by_disk_key(),
                    result.outcomes,
                )
                state_box.value = state

            if result.stop_reason == "operator quit":
                # A human asked to stop the whole apply run, not just this
                # group -- section 9.1's `[q]uit` is an operator decision,
                # not a per-group one.
                break
    finally:
        # `state_box.value`, not the plain `state` variable: if an
        # exception propagates out of a group's execution (a `move_disk`
        # task's own status poll raising mid-wait, say), an
        # `on_inflight_started` callback earlier in that same group can
        # already have written a newer `inflight_upids` straight to disk
        # than whatever `state` was last assigned in this function's own
        # loop -- saving the (older) local variable here would silently
        # clobber that write and erase the very crash trace section 13
        # exists to leave behind.
        save_locked_state(lock_handle, state_box.value)
        release_lock(lock_handle)

    if args.json:
        print(
            json.dumps(
                _render_apply_json(
                    topology,
                    group_loads,
                    gate_decisions,
                    solve_outcomes,
                    schedule_results,
                    payback_results,
                    final_breakdowns,
                    load_errors,
                    execution_results,
                ),
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(
            _render_apply_human(
                topology,
                group_loads,
                gate_decisions,
                solve_outcomes,
                schedule_results,
                payback_results,
                final_breakdowns,
                load_errors,
                resolved.config.migration.payback_ratio,
                execution_results,
            )
        )

    any_failure = any(
        outcome.status == "failed"
        for result in execution_results.values()
        for outcome in result.outcomes
    )
    return 1 if any_failure else 0


def _render_verify_storages_human(topology: Topology, config: Any) -> str:
    lines: list[str] = []
    for group in topology.groups:
        lines.append(f"Group {group.name}")
        for storage in group.storages:
            largest = largest_disk_bytes(group.disks, storage.id)
            state = "on" if storage.saferemove else "off"
            lines.append(f"  {storage.id}  saferemove={state}")
            wipe_seconds = compute_wipe_duration_seconds(
                largest, storage.saferemove_throughput_bytes_per_sec
            )
            if wipe_seconds is None:
                lines.append("    saferemove is off or throughput unknown; no wipe-time check")
                continue
            lines.append(
                f"    implied wipe time for the largest disk ({format_bytes(largest)}): "
                f"{format_duration_seconds(wipe_seconds)}"
            )
            if wipe_seconds > config.gates.cooldown_per_storage_seconds:
                lines.append(
                    "    ⚠ gates.cooldown_per_storage "
                    f"({format_duration_seconds(config.gates.cooldown_per_storage_seconds)}) "
                    "is shorter than the implied wipe time -- the next run may plan onto a "
                    "still-draining storage"
                )
            max_move_seconds = config.migration.max_single_move_duration_seconds
            if wipe_seconds > max_move_seconds:
                lines.append(
                    "    ⚠ migration.max_single_move_duration "
                    f"({format_duration_seconds(max_move_seconds)}) "
                    "is shorter than the implied wipe time -- a move of the largest disk would "
                    "be rejected outright"
                )
        lines.append("")
    if topology.pattern_expansions:
        lines.append("Pattern expansions:")
        for expansion in topology.pattern_expansions:
            matched = ", ".join(expansion.matched_ids) if expansion.matched_ids else "(none)"
            lines.append(f"  [{expansion.group_name}] {expansion.pattern} → {matched}")
        lines.append("")
    if topology.unmanaged_storage_ids:
        lines.append("Cluster storages matched by no group:")
        lines.extend(f"  - {sid}" for sid in topology.unmanaged_storage_ids)
        lines.append("")
    return "\n".join(lines)


def _render_verify_storages_json(topology: Topology, config: Any) -> dict[str, object]:
    groups_out = []
    for group in topology.groups:
        storages_out = []
        for storage in group.storages:
            largest = largest_disk_bytes(group.disks, storage.id)
            wipe_seconds = compute_wipe_duration_seconds(
                largest, storage.saferemove_throughput_bytes_per_sec
            )
            storages_out.append(
                {
                    "id": storage.id,
                    "saferemove": storage.saferemove,
                    "saferemove_throughput_bytes_per_sec": (
                        storage.saferemove_throughput_bytes_per_sec
                    ),
                    "largest_disk_bytes": largest,
                    "implied_wipe_seconds": wipe_seconds,
                    "cooldown_per_storage_too_short": (
                        wipe_seconds is not None
                        and wipe_seconds > config.gates.cooldown_per_storage_seconds
                    ),
                    "max_single_move_duration_too_short": (
                        wipe_seconds is not None
                        and wipe_seconds > config.migration.max_single_move_duration_seconds
                    ),
                }
            )
        groups_out.append({"name": group.name, "storages": storages_out})
    return {
        "groups": groups_out,
        "pattern_expansions": [
            {
                "group": e.group_name,
                "pattern": e.pattern,
                "matched_ids": list(e.matched_ids),
            }
            for e in topology.pattern_expansions
        ],
        "unmanaged_storage_ids": list(topology.unmanaged_storage_ids),
    }


def _handle_verify_storages(resolved: ResolvedConfig, args: argparse.Namespace, mode: str) -> int:
    del mode
    client = build_pve_client(resolved.config.proxmox)
    topology = _filter_groups(build_topology(client, resolved.config), args.group)
    if args.json:
        print(
            json.dumps(
                _render_verify_storages_json(topology, resolved.config), indent=2, sort_keys=True
            )
        )
    else:
        print(_render_verify_storages_human(topology, resolved.config))
    return 0


_COMMAND_HANDLERS: dict[str, CommandHandler] = {
    name: _make_not_yet_implemented_handler(name) for name in _SUBCOMMANDS
}
_COMMAND_HANDLERS["verify-metrics"] = _handle_verify_metrics
_COMMAND_HANDLERS["show-load"] = _handle_show_load
_COMMAND_HANDLERS["verify-storages"] = _handle_verify_storages
_COMMAND_HANDLERS["plan"] = _handle_plan
_COMMAND_HANDLERS["apply"] = _handle_apply
_COMMAND_HANDLERS["explain"] = _handle_explain


# ------------------------------------------------------------------- main


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(f"pve-storage-drs {__version__}")
        return 0
    if args.manual or args.command == "help":
        return show_manual()
    if args.command is None:
        parser.print_usage(sys.stderr)
        return 2

    configure_logging(args.verbose, args.quiet)

    try:
        resolved = load_config(args.config)
    except ConfigError as exc:
        print(f"pve-storage-drs: {exc}", file=sys.stderr)
        return 1

    logger.info(
        "configuration loaded",
        extra={"event": "config_loaded", "path": resolved.path, "sha256": resolved.sha256},
    )
    for warning in resolved.warnings:
        logger.warning(warning, extra={"event": "config_warning"})

    effective_mode = resolved.config.execution.mode
    if args.mode is not None:
        effective_mode = apply_mode_override(resolved.config.execution.mode, args.mode)

    handler = _COMMAND_HANDLERS[args.command]
    try:
        return handler(resolved, args, effective_mode)
    except DrsError as exc:
        logger.error(str(exc), extra={"event": "command_failed", "command": args.command})
        print(f"pve-storage-drs: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover - exercised via the entry point
    sys.exit(main())
