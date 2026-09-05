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
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from proxmox_storage_drs import __version__
from proxmox_storage_drs.config import (
    DEFAULT_CONFIG_PATH,
    ENV_CONFIG_VAR,
    ResolvedConfig,
    load_config,
)
from proxmox_storage_drs.exceptions import ConfigError, DrsError, MetricsError
from proxmox_storage_drs.gates import GateDecision, evaluate_group_gates
from proxmox_storage_drs.heuristic import (
    HeuristicResult,
    ObjectiveBreakdown,
    evaluate_assignment,
    group_average_utilization,
    raw_spread,
    run_heuristic,
)
from proxmox_storage_drs.loadmodel import GroupLoad, compute_group_load
from proxmox_storage_drs.logging_setup import configure_logging
from proxmox_storage_drs.metrics import PrometheusClient, VerifyMetricsReport, verify_metrics
from proxmox_storage_drs.payback import (
    MoveCost,
    PaybackResult,
    compute_benefit_load_seconds,
    compute_move_cost,
    compute_wipe_duration_seconds,
    evaluate_plan_payback,
)
from proxmox_storage_drs.pve import build_client as build_pve_client
from proxmox_storage_drs.reserve import ReserveStatus, compute_reserve_status, largest_disk_bytes
from proxmox_storage_drs.schedule import ScheduledMove, ScheduleResult, order_moves
from proxmox_storage_drs.state import (
    State,
    active_storage_cooldowns,
    load_state,
    load_vector_for_group,
)
from proxmox_storage_drs.topology import Topology, build_topology
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
        help="Emit the machine-readable report (section 9.5) instead of the human one.",
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
# pve.py, topology.py and the solver/scheduler/executor modules do not exist
# yet (IMPLEMENTATION_PLAN.md section 12 phases 2-9 are still in progress).
# Each such handler is honest about that rather than pretending to succeed --
# AGENTS.md section 10 forbids emitting a partial/unvalidated result, and
# "not implemented yet" is a true statement, not a silent wrong action.


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
        load_by_key = group_load.load_by_disk_key() if group_load else {}
        storage_loads = {s.storage_id: s for s in group_load.storages} if group_load else {}
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


def _load_per_tib(load_by_key: dict[str, float], move: ScheduledMove) -> float:
    """Section 7.3's advisory ``ell/z`` ratio for one move -- ``0.0`` for a
    zero-size disk rather than a ``ZeroDivisionError`` (PVE does not report
    these in practice, and ``config_schema.json`` does not forbid
    ``size_bytes: 0`` since that value comes from the PVE API, not config;
    defense in depth, not a live bug -- REVIEW.md R-06)."""
    if move.size_bytes <= 0:
        return 0.0
    return load_by_key.get(move.disk_key, 0.0) / (move.size_bytes / _BYTES_PER_TIB)


def _render_plan_move_line(
    index: int, move: ScheduledMove, move_cost: MoveCost | None, load_by_key: dict[str, float]
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
    load_per_tib = _load_per_tib(load_by_key, move)
    return (
        f"  {index}. {move.disk_key:<14} {move.from_storage} → {move.to_storage}   "
        f"{format_bytes(move.size_bytes):>10}   {duration_str}   "
        f"Δimbalance {change:+.2f}   ℓ/z {load_per_tib:.2f}{flag}"
    )


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
            "  ⚠ this plan's balance benefit does not outweigh its migration cost "
            "(section 7.3) -- automatically re-solving with adjusted weights is "
            "not yet implemented (phase 5 gap); review before applying"
        )
    if payback_result.rejected_moves:
        lines.append(
            "  ⚠ blocked by the hard per-move duration rule (migration."
            "max_single_move_duration): " + ", ".join(payback_result.rejected_moves)
        )
    return lines


def _render_plan_human(
    topology: Topology,
    group_loads: dict[str, GroupLoad],
    gate_decisions: dict[str, GateDecision],
    schedule_results: dict[str, ScheduleResult],
    payback_results: dict[str, PaybackResult],
    final_breakdowns: dict[str, ObjectiveBreakdown],
    load_errors: dict[str, str],
    payback_ratio: float,
) -> str:
    lines: list[str] = []
    for group in topology.groups:
        if group.name in load_errors:
            lines.append(f"Group {group.name} — plan unavailable: {load_errors[group.name]}")
            lines.append("")
            continue

        decision = gate_decisions[group.name]
        verdict = "ACT" if decision.act else "NO ACTION"
        lines.append(f"Group {group.name} → {verdict}: {decision.reason}")

        schedule_result = schedule_results.get(group.name)
        if schedule_result is None:
            lines.append("")
            continue

        group_load = group_loads[group.name]
        load_by_key = group_load.load_by_disk_key()
        payback_result = payback_results.get(group.name)
        move_costs_by_key = (
            {mc.disk_key: mc for mc in payback_result.move_costs} if payback_result else {}
        )

        for i, move in enumerate(schedule_result.order, start=1):
            lines.append(
                _render_plan_move_line(i, move, move_costs_by_key.get(move.disk_key), load_by_key)
            )
        if schedule_result.deadlocked_msg:
            lines.append(f"  ⚠ {schedule_result.deadlocked_msg}")

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
    if topology.warnings:
        lines.append("Warnings:")
        lines.extend(f"  - {warning}" for warning in topology.warnings)
        lines.append("")
    return "\n".join(lines)


def _render_plan_json(
    topology: Topology,
    group_loads: dict[str, GroupLoad],
    gate_decisions: dict[str, GateDecision],
    schedule_results: dict[str, ScheduleResult],
    payback_results: dict[str, PaybackResult],
    final_breakdowns: dict[str, ObjectiveBreakdown],
    load_errors: dict[str, str],
) -> dict[str, object]:
    groups_out = []
    for group in topology.groups:
        decision = gate_decisions.get(group.name)
        schedule_result = schedule_results.get(group.name)
        payback_result = payback_results.get(group.name)
        group_load = group_loads.get(group.name)
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
                        "load_per_tib": _load_per_tib(load_by_key, move),
                        "duration_mirror_seconds": (
                            move_cost.duration_mirror_seconds if move_cost else None
                        ),
                        "duration_wipe_seconds": (
                            move_cost.duration_wipe_seconds if move_cost else None
                        ),
                        "cost_load_seconds": move_cost.cost_load_seconds if move_cost else None,
                        "exceeds_max_duration": (
                            move_cost.exceeds_max_duration if move_cost else None
                        ),
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
        final_breakdown = final_breakdowns.get(group.name)
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
                "accepted": payback_result.accepted,
            }
        groups_out.append(
            {
                "name": group.name,
                "load_error": load_errors.get(group.name),
                "gate": gate_out,
                "moves": moves_out,
                "deadlocked": list(schedule_result.deadlocked) if schedule_result else [],
                "deadlock_message": schedule_result.deadlocked_msg if schedule_result else None,
                "before_spread": before_spread,
                "after_spread": after_spread,
                "payback": payback_out,
            }
        )
    return {"groups": groups_out, "warnings": list(topology.warnings)}


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
    min_free_bytes = resolved.config.snapshot_reserve.min_free_bytes
    last_loads_by_group = _last_loads_by_group(state, topology)

    group_loads: dict[str, GroupLoad] = {}
    gate_decisions: dict[str, GateDecision] = {}
    heuristic_results: dict[str, HeuristicResult] = {}
    schedule_results: dict[str, ScheduleResult] = {}
    payback_results: dict[str, PaybackResult] = {}
    final_breakdowns: dict[str, ObjectiveBreakdown] = {}
    load_errors: dict[str, str] = {}

    for group in topology.groups:
        try:
            group_load = compute_group_load(
                prom_client,
                resolved.config.metrics,
                resolved.config.window,
                resolved.config.load_weights,
                group,
                last_known_loads=last_loads_by_group.get(group.name),
            )
        except MetricsError as exc:
            # Section 6: gating (and so planning) cannot proceed without a
            # load to gate on -- unlike show-load's size/reserve report,
            # nothing here is safe to show without it.
            load_errors[group.name] = str(exc)
            continue
        group_loads[group.name] = group_load

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
        gate_decisions[group.name] = decision
        if not decision.act:
            continue

        cooldown_storages = frozenset(
            active_storage_cooldowns(
                state, group.name, resolved.config.gates.cooldown_per_storage_seconds, now
            )
        )
        heuristic_result = run_heuristic(
            group,
            group_load.load_by_disk_key(),
            resolved.config.objective,
            min_free_bytes,
            resolved.config.solver.heuristic_iterations,
            cooldown_storages,
        )
        heuristic_results[group.name] = heuristic_result
        schedule_result = order_moves(
            group,
            heuristic_result.assignment,
            group_load.load_by_disk_key(),
            resolved.config.objective,
            min_free_bytes,
        )
        schedule_results[group.name] = schedule_result

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
        final_breakdowns[group.name] = final_breakdown

        storages_by_id = {s.id: s for s in group.storages}
        move_costs = [
            compute_move_cost(move, storages_by_id[move.from_storage], resolved.config.migration)
            for move in schedule_result.order
        ]
        spread_metric = resolved.config.objective.spread_metric
        benefit = compute_benefit_load_seconds(
            raw_spread(heuristic_result.initial_breakdown, spread_metric),
            raw_spread(final_breakdown, spread_metric),
            resolved.config.migration.payback_horizon_seconds,
        )
        payback_results[group.name] = evaluate_plan_payback(
            move_costs, benefit, resolved.config.migration.payback_ratio
        )

    if args.json:
        print(
            json.dumps(
                _render_plan_json(
                    topology,
                    group_loads,
                    gate_decisions,
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
                schedule_results,
                payback_results,
                final_breakdowns,
                load_errors,
                resolved.config.migration.payback_ratio,
            )
        )
    return 0


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
                    "still-draining storage (section 9.3)"
                )
            max_move_seconds = config.migration.max_single_move_duration_seconds
            if wipe_seconds > max_move_seconds:
                lines.append(
                    "    ⚠ migration.max_single_move_duration "
                    f"({format_duration_seconds(max_move_seconds)}) "
                    "is shorter than the implied wipe time -- a move of the largest disk would "
                    "be rejected outright (section 7.3)"
                )
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
    return {"groups": groups_out}


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
