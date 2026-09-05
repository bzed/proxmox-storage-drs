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
import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Sequence

from proxmox_storage_drs import __version__
from proxmox_storage_drs.config import (
    DEFAULT_CONFIG_PATH,
    ENV_CONFIG_VAR,
    ResolvedConfig,
    load_config,
)
from proxmox_storage_drs.exceptions import ConfigError, DrsError
from proxmox_storage_drs.logging_setup import configure_logging
from proxmox_storage_drs.metrics import PrometheusClient, VerifyMetricsReport, verify_metrics
from proxmox_storage_drs.pve import build_client as build_pve_client
from proxmox_storage_drs.reserve import compute_reserve_status, largest_disk_bytes
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


def _render_show_load_human(topology: Topology, config: Any) -> str:
    lines: list[str] = []
    for group in topology.groups:
        lines.append(f"Group {group.name}")
        for storage in group.storages:
            status = compute_reserve_status(
                storage, group.disks, config.snapshot_reserve.min_free_bytes
            )
            reserve_str = (
                f"⚠ reserve short by {format_bytes(status.shortfall_bytes)}"
                if status.violated
                else "reserve OK"
            )
            lines.append(
                f"  {storage.id}  used {format_bytes(storage.used_bytes)}/"
                f"{format_bytes(storage.capacity_bytes)}  {reserve_str}  "
                f"(largest disk {format_bytes(status.largest_disk_bytes)}, "
                f"requires {format_bytes(status.required_reserve_bytes)} free)"
            )
            disks_here = sorted(
                (d for d in group.disks if d.current_storage == storage.id),
                key=lambda d: (d.vmid, d.device),
            )
            for disk in disks_here:
                pin = f"  [pinned: {disk.pinned_reason}]" if disk.pinned_reason else ""
                lines.append(
                    f"    {disk.key:<14} {format_bytes(disk.size_bytes):>10}  "
                    f"{disk.format:<6}{pin}"
                )
        lines.append("")
    if topology.warnings:
        lines.append("Warnings:")
        lines.extend(f"  - {warning}" for warning in topology.warnings)
        lines.append("")
    lines.append(
        "Note: per-disk I/O load is not yet computed -- loadmodel.py "
        "(IMPLEMENTATION_PLAN.md section 12 phase 3) is not implemented yet; "
        "sizes and reserve status above are accurate."
    )
    return "\n".join(lines)


def _render_show_load_json(topology: Topology, config: Any) -> dict[str, object]:
    groups_out = []
    for group in topology.groups:
        storages_out = []
        for storage in group.storages:
            status = compute_reserve_status(
                storage, group.disks, config.snapshot_reserve.min_free_bytes
            )
            storages_out.append(
                {
                    "id": storage.id,
                    "used_bytes": storage.used_bytes,
                    "capacity_bytes": storage.capacity_bytes,
                    "foreign_used_bytes": storage.foreign_used_bytes,
                    "largest_disk_bytes": status.largest_disk_bytes,
                    "required_reserve_bytes": status.required_reserve_bytes,
                    "reserve_violated": status.violated,
                    "reserve_shortfall_bytes": status.shortfall_bytes,
                }
            )
        disks_out = [
            {
                "key": d.key,
                "vmid": d.vmid,
                "device": d.device,
                "vm_name": d.vm_name,
                "size_bytes": d.size_bytes,
                "current_storage": d.current_storage,
                "format": d.format,
                "pinned_reason": d.pinned_reason,
            }
            for d in group.disks
        ]
        groups_out.append({"name": group.name, "storages": storages_out, "disks": disks_out})
    return {"groups": groups_out, "warnings": list(topology.warnings), "load_computed": False}


def _handle_show_load(resolved: ResolvedConfig, args: argparse.Namespace, mode: str) -> int:
    del mode
    client = build_pve_client(resolved.config.proxmox)
    topology = build_topology(client, resolved.config)
    if args.json:
        print(
            json.dumps(_render_show_load_json(topology, resolved.config), indent=2, sort_keys=True)
        )
    else:
        print(_render_show_load_human(topology, resolved.config))
    return 0


def _implied_wipe_seconds(disk_bytes: int, throughput_bytes_per_sec: float | None) -> float | None:
    """Sections 3.5/7.1/9.3: ``z_max / saferemove_throughput``.

    Not yet shared with ``payback.py``'s identical ``duration_wipe_d``
    formula (section 7.1), since that module does not exist yet -- extract
    this to one shared function the day it does (AGENTS.md section 5).
    """
    if not throughput_bytes_per_sec:
        return None
    return disk_bytes / throughput_bytes_per_sec


def _render_verify_storages_human(topology: Topology, config: Any) -> str:
    lines: list[str] = []
    for group in topology.groups:
        lines.append(f"Group {group.name}")
        for storage in group.storages:
            largest = largest_disk_bytes(group.disks, storage.id)
            state = "on" if storage.saferemove else "off"
            lines.append(f"  {storage.id}  saferemove={state}")
            wipe_seconds = _implied_wipe_seconds(
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
            wipe_seconds = _implied_wipe_seconds(
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
    topology = build_topology(client, resolved.config)
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
