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
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from proxmox_storage_drs import __version__, collect, optimize, replay
from proxmox_storage_drs.config import (
    DEFAULT_CONFIG_PATH,
    ENV_CONFIG_VAR,
    ExcludeConfig,
    ExecutionConfig,
    ForecastConfig,
    GatesConfig,
    MetricsConfig,
    MigrationConfig,
    ObjectiveConfig,
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
)
from proxmox_storage_drs.gates import GateDecision, evaluate_group_gates
from proxmox_storage_drs.heuristic import (
    Assignment,
    ObjectiveBreakdown,
    best_single_disk_alternative,
    evaluate_assignment,
    group_average_fill,
    group_average_utilization,
    raw_affinity_debt,
    raw_capacity_spread,
    raw_spread,
    run_heuristic,
)
from proxmox_storage_drs.loadmodel import GroupLoad, compute_group_load
from proxmox_storage_drs.logging_setup import (
    LOG_FORMATS,
    LOG_LEVELS,
    configure_logging,
    floor_for_command,
    json_safe,
)
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
    executed_assignment,
    repair_markers,
)
from proxmox_storage_drs.pve import PveClient
from proxmox_storage_drs.pve import build_client as build_pve_client
from proxmox_storage_drs.reserve import (
    ReserveStatus,
    compute_reserve_status,
    largest_disk_bytes,
    total_shortfall_bytes,
)
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
from proxmox_storage_drs.statusfile import (
    RunReport,
    StatusFileError,
    build_run_status,
    write_status_file,
)
from proxmox_storage_drs.timewindow import current_deadline
from proxmox_storage_drs.topology import (
    Disk,
    Group,
    Topology,
    build_topology,
    format_disk_id,
)
from proxmox_storage_drs.units import format_bytes, format_duration_seconds, parse_duration_seconds

# Explicitly named, not `__name__`: this module is `__main__` whenever it is
# executed rather than imported, and a journalctl filter keyed on a logger
# name that changes with how the process was started is not a filter
# (IMPLEMENTATION_PLAN.md section 2.3).
logger = logging.getLogger("proxmox_storage_drs.cli")

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
    "collect-testdata": (
        "Capture an anonymized diagnostic bundle (topology, config, metrics). Read-only."
    ),
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
        help=(
            "-v logs this run's decision trail (gate, plan, payback, every move); "
            "-vv adds per-query detail and third-party library logs."
        ),
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help=(
            "Errors only. On an 'auto' run this also discards the audit trail such a "
            "run otherwise logs unconditionally -- the only record of what was moved."
        ),
    )
    parser.add_argument(
        "--log-level",
        choices=LOG_LEVELS,
        default=None,
        help=(
            "Set the log level explicitly. Wins over -v and --quiet, except that on an "
            "'auto'/'confirm' apply run a level below the mandatory audit-trail floor "
            "(info) is raised back up to it -- --quiet is the only way to discard that "
            "record."
        ),
    )
    parser.add_argument(
        "--log-format",
        choices=LOG_FORMATS,
        default="auto",
        help="auto selects human-readable text at a terminal and JSON anywhere else.",
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
    parser.add_argument(
        "--replay",
        metavar="PATH",
        default=None,
        help=(
            "Run against a collect-testdata bundle at PATH instead of the live cluster -- "
            "no network access at all (section 16.5). The bundle's own config.yaml is used "
            "unless -c is also given. apply and any --mode above dry-run are a usage error."
        ),
    )

    subparsers = parser.add_subparsers(dest="command", metavar="command")
    subparsers.add_parser("help", help="Alias for --manual.")
    for name, help_text in _SUBCOMMANDS.items():
        if name == "collect-testdata":
            continue  # has its own options, added below
        subparsers.add_parser(name, help=help_text)

    collect_parser = subparsers.add_parser(
        "collect-testdata", help=_SUBCOMMANDS["collect-testdata"]
    )
    collect_parser.add_argument(
        "-o",
        "--output",
        metavar="DIR",
        default=None,
        help="Where the bundle directory/tarball are written (default: support.bundle_dir).",
    )
    collect_parser.add_argument(
        "--estimate",
        action="store_true",
        help="Print the query count and payload estimate, then exit without fetching.",
    )
    collect_parser.add_argument(
        "--range",
        metavar="DURATION",
        default=None,
        help="Override the range of the series capture (default: support.capture_range).",
    )
    collect_parser.add_argument(
        "--step",
        metavar="DURATION",
        default=None,
        help="Override the series resolution (default: metrics.step).",
    )
    collect_parser.add_argument(
        "--no-series",
        action="store_true",
        help="Capture topology, instant queries and findings only -- no forecaster-sized series.",
    )
    collect_parser.add_argument(
        "--no-archive",
        action="store_true",
        help="Write the bundle directory only, no .tar.gz.",
    )
    collect_parser.add_argument(
        "--salt-file",
        metavar="PATH",
        default=None,
        help="Use a different anonymization salt file (default: support.salt_path).",
    )
    collect_parser.add_argument(
        "--new-salt",
        action="store_true",
        help="Generate a fresh salt, replacing the persisted one. Bundles made before and "
        "after no longer share a pseudonym mapping.",
    )

    return parser


# --------------------------------------------------------------- run summary


@dataclasses.dataclass
class _RunStats:
    """What ``run_summary`` reports, accumulated as the run goes.

    Carried on the ``argparse.Namespace`` every handler already receives
    rather than in a module global: there is exactly one of these per
    process, but "one per process" is what a global *means*, and a
    namespace attribute keeps it testable and keeps two runs in one pytest
    session from sharing it.
    """

    groups: int = 0
    moves_issued: int = 0
    moves_succeeded: int = 0
    moves_failed: int = 0
    bytes_moved: int = 0
    replans: int = 0
    # What the monitoring status file (section 2.4) reports: reasons the run
    # failed, and things a human should look at that did not fail it.
    errors: list[str] = dataclasses.field(default_factory=list)
    warnings: list[str] = dataclasses.field(default_factory=list)
    # Set by `_handle_apply()` when another instance held the lock and this
    # run exited quietly without doing anything -- it must not overwrite the
    # status file with a result it never produced.
    lock_held: bool = False


def _run_stats(args: argparse.Namespace) -> _RunStats:
    """The run's stats object, creating it if a caller (a test, or a handler
    invoked directly) never went through ``main()``."""
    stats = getattr(args, "run_stats", None)
    if stats is None:
        stats = _RunStats()
        args.run_stats = stats
    return stats


def _accumulate_move_stats(args: argparse.Namespace, group: Group, result: ExecutionResult) -> None:
    """Fold one group's execution into ``run_summary``'s counters.

    Counts *launches*, not plan entries: `MoveOutcome.upid is not None` is
    the same "was this actually issued" test `execution.max_migrations_per_run`
    uses (REVIEW.md T-06), so the summary cannot disagree with the budget
    about how many migrations a run performed.
    """
    stats = _run_stats(args)
    stats.groups += 1
    stats.replans += result.replans
    size_by_key = {d.key: d.size_bytes for d in group.disks}
    vm_name_by_key = _vm_name_map(group)
    for outcome in result.outcomes:
        _record_outcome_for_status(stats, group, outcome, vm_name_by_key)
        if outcome.upid is None:
            continue
        stats.moves_issued += 1
        if outcome.status == "moved":
            stats.moves_succeeded += 1
            stats.bytes_moved += size_by_key.get(outcome.disk_key, 0)
        elif outcome.status == "failed":
            stats.moves_failed += 1
    if result.abort_reason is not None:
        stats.errors.append(f"group {group.name}: {result.abort_reason}")
    if result.replans_exhausted and result.stop_reason is not None:
        # External churn the run gave up on: try again later, not a failure.
        stats.warnings.append(f"group {group.name}: {result.stop_reason}")


def _record_outcome_for_status(
    stats: _RunStats, group: Group, outcome: MoveOutcome, vm_name_by_key: dict[str, str]
) -> None:
    """Fold one move outcome into the status file's error/warning lists (the
    numeric counters stay in :func:`_accumulate_move_stats`)."""
    display_id = format_disk_id(outcome.disk_key, _vm_name_for(vm_name_by_key, outcome.disk_key))
    move = f"{display_id} {outcome.from_storage} -> {outcome.to_storage}"
    if outcome.status == "failed":
        stats.errors.append(f"group {group.name}: {move} failed: {outcome.detail}")
    elif outcome.status == "draining":
        stats.warnings.append(
            f"group {group.name}: {move}: source storage had not released the volume "
            "yet (still wiping?); it is excluded for the rest of the run"
        )
    if outcome.orphaned_volumes:
        stats.warnings.append(
            f"group {group.name}: {move}: volume(s) left on the target and NOT deleted: "
            + ", ".join(outcome.orphaned_volumes)
        )


def _start_logging_and_announce_run(
    args: argparse.Namespace, resolved: ResolvedConfig, configured_mode: str
) -> str:
    """Configure logging for this run and emit ``run_started``. Returns the
    log format actually selected (section 2.3).

    Logging is configured only once the effective mode is known, because
    that mode decides whether this run owes an audit trail regardless of
    what the operator asked for (section 2.3's mandatory floor). The mode is
    computed here rather than taken from `apply_mode_override()`, which is
    called afterwards, because that call *logs* -- and must land at the
    level this one picks.
    """
    intended_mode = args.mode if args.mode is not None else configured_mode
    log_format = configure_logging(
        args.verbose,
        args.quiet,
        log_level=args.log_level,
        log_format=args.log_format,
        floor=floor_for_command(args.command, intended_mode),
    )
    logger.info(
        "run started: %s (%s)",
        args.command,
        intended_mode,
        extra={
            "event": "run_started",
            "command": args.command,
            "mode": intended_mode,
            "version": __version__,
            "config_path": resolved.path,
            "config_sha256": resolved.sha256,
            "replay": args.replay,
        },
    )
    for warning in resolved.warnings:
        # INFO, not WARNING: an advisory about a file is equally true on
        # every run until someone edits it, and repeating it at warning
        # level every 15 minutes trains operators to ignore warnings
        # (section 2.3). `verify-storages` reports it where it is actionable.
        logger.info(warning, extra={"event": "config_warning"})
    return log_format


def _dump_report_json(payload: object) -> str:
    """Serialize one ``--json`` report. The single place section 9.5's
    machine-readable output is written (AGENTS.md section 5).

    ``json_safe()`` because section 7's payback ratio is `+inf` for any
    plan with no moves to pay for, and Python writes that as a bare
    ``Infinity`` literal RFC 8259 does not define -- `jq` reads it back as
    a different number and a strict parser refuses the line outright.
    ``allow_nan=False`` turns any future non-finite value into a loud
    failure here rather than a quietly unparseable report.
    """
    return json.dumps(json_safe(payload), indent=2, sort_keys=True, allow_nan=False)


def _log_run_summary(
    args: argparse.Namespace, effective_mode: str, exit_code: int, started_at: float
) -> None:
    """Section 2.3's closing record: one line saying what this run did.

    Emitted for every command, including failures -- "it exited 1 after
    issuing two moves, one of which failed" is exactly the sentence an
    operator reconstructing an unattended run needs, and it cannot be
    recovered from the per-move records alone if the run died between them.
    """
    stats = _run_stats(args)
    logger.info(
        "run finished: %s exit=%d",
        args.command,
        exit_code,
        extra={
            "event": "run_summary",
            "command": args.command,
            "mode": effective_mode,
            "exit_code": exit_code,
            "duration_seconds": round(time.monotonic() - started_at, 3),
            "groups": stats.groups,
            "moves_issued": stats.moves_issued,
            "moves_succeeded": stats.moves_succeeded,
            "moves_failed": stats.moves_failed,
            "bytes_moved": stats.bytes_moved,
        },
    )


def _publish_status_file(
    resolved: ResolvedConfig,
    args: argparse.Namespace,
    effective_mode: str,
    exit_code: int,
    started_at: float,
) -> None:
    """Section 2.4: leave ``monitoring.status_file``'s ``check_statusfile``
    report for this ``apply`` run. Every mode writes it, dry-run included, so
    that a stale file means "the timer stopped", never "nothing happened".

    Skipped for other commands (``plan`` and friends are interactive and would
    overwrite the scheduled run's result), for ``--replay`` (not a real run),
    and when another instance held the lock (this run produced no result --
    the file keeps the last real one). A write failure is logged, never
    raised: it must not change what the run did or its exit code, and a file
    that stops updating turns WARNING on its own once it is older than the
    plugin's ``--age``.
    """
    path = resolved.config.monitoring.status_file
    stats = _run_stats(args)
    if path is None or args.command != "apply" or args.replay or stats.lock_held:
        return
    report = RunReport(
        mode=effective_mode,
        exit_code=exit_code,
        finished_at=datetime.now(timezone.utc),
        duration_seconds=time.monotonic() - started_at,
        groups=stats.groups,
        moves_succeeded=stats.moves_succeeded,
        moves_failed=stats.moves_failed,
        bytes_moved=stats.bytes_moved,
        replans=stats.replans,
        errors=tuple(stats.errors),
        warnings=tuple(stats.warnings),
    )
    try:
        write_status_file(path, build_run_status(report))
    except StatusFileError as exc:
        logger.error(str(exc), extra={"event": "status_file_write_failed", "path": path})


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
    """Section 3.4's node-scoping filter for one command invocation.

    ``metrics.extra_selector`` short-circuits before any extra API call, as
    before; otherwise this cluster's own node list (``client.node_names()``,
    already needed to build this command's own topology) is the default
    filter (see ``metrics.resolve_node_selector()``'s own docstring for the
    full precedence). ``verify-metrics`` calls
    ``metrics.resolve_node_selector()`` directly instead, with
    ``node_names`` left ``None``, since it is deliberately independent of
    the PVE API entirely and never reaches this function at all."""
    if metrics.extra_selector:
        return metrics.extra_selector
    return resolve_node_selector(metrics, client.node_names())


def _pve_client_for(resolved: ResolvedConfig, args: argparse.Namespace) -> PveClient:
    """The one place a :class:`PveClient` is constructed for a command run
    (section 16.5) -- every handler calls this instead of
    ``build_pve_client()`` directly, so ``--replay`` substitutes
    :class:`~proxmox_storage_drs.replay.ReplayPveClient` here and nowhere
    else has to know the difference."""
    replay_path = getattr(args, "replay", None)
    if replay_path:
        return replay.ReplayPveClient(replay_path)
    return build_pve_client(resolved.config.proxmox)


def _metrics_client_for(resolved: ResolvedConfig, args: argparse.Namespace) -> PrometheusClient:
    """The Prometheus-side counterpart to :func:`_pve_client_for`."""
    replay_path = getattr(args, "replay", None)
    if replay_path:
        return replay.ReplayPrometheusClient(resolved.config.prometheus, replay_path)
    return PrometheusClient(resolved.config.prometheus)


def _now_for(args: argparse.Namespace) -> datetime:
    """The "now" every read-only handler builds its query time window
    from. Under ``--replay`` this must be the bundle's own fixed, rebased
    capture instant (``replay.bundle_reference_now()``) rather than the
    real wall clock -- otherwise every range query a replayed ``plan``/
    ``show-load``/``explain`` run constructs falls outside what the bundle
    actually captured, and every one of them is a guaranteed key miss
    (section 16.5)."""
    replay_path = getattr(args, "replay", None)
    if replay_path:
        return replay.bundle_reference_now(replay_path)
    return datetime.now(timezone.utc)


def _state_path_for(resolved: ResolvedConfig, args: argparse.Namespace) -> str:
    """Section 16.5: "state.json under replay is read from the bundle if
    present and written nowhere." Every read-only handler loads state
    through this instead of ``resolved.config.state.path`` directly; a
    replay never reaches ``save_locked_state()`` at all, since ``apply`` is
    refused under ``--replay`` before any handler runs (``main()``)."""
    replay_path = getattr(args, "replay", None)
    if replay_path:
        return str(Path(replay_path) / "state.json")
    return resolved.config.state.path


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
    client = _metrics_client_for(resolved, args)
    report = verify_metrics(
        client, resolved.config.metrics, resolved.config.window, now=_now_for(args).timestamp()
    )
    if args.json:
        print(_dump_report_json(_render_verify_metrics_json(report)))
    else:
        print(_render_verify_metrics_human(report))
    return 0 if report.ok else 1


def _vm_name_map(group: Group) -> dict[str, str]:
    """`Disk.key` -> `Disk.vm_name` for every disk in `group`, built once so
    output that only carries a bare `disk_key` (a `ScheduledMove`,
    `MoveOutcome`, `RejectedCandidate`, `DiskLoad`, ...) can still render
    `format_disk_id`'s "name(vmid):device" form."""
    return {d.key: d.vm_name for d in group.disks}


def _vm_name_for(vm_name_by_key: dict[str, str], disk_key: str) -> str:
    """`vm_name_by_key[disk_key]`, falling back to the bare vmid if the key
    is somehow not one of `group`'s own disks (should not happen -- every
    `disk_key` rendered here always originates from the same group)."""
    return vm_name_by_key.get(disk_key, disk_key.partition(":")[0])


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
    vm_name_by_key = _vm_name_map(group)
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
        # Section 5.1: the figure the reserve shortfall is computed from is
        # the *provisioned* sum, not PVE's own `used`. On a thick pool the
        # two agree and only the first is shown; on a thin one (Ceph RBD,
        # LVM-thin, ZFS) `used` is the lower, allocated figure, so it is
        # printed alongside rather than in the shortfall's place -- else
        # a shortfall beside a half-empty pool would read as a mistake.
        allocated_note = (
            f" (pool reports {format_bytes(storage.used_bytes)} allocated)"
            if storage.used_bytes != status.managed_used_bytes
            else ""
        )
        lines.append(
            f"  {storage.id}  provisioned {format_bytes(status.managed_used_bytes)}/"
            f"{format_bytes(storage.capacity_bytes)}{allocated_note}  "
            f"{load_prefix}{reserve_str}  "
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
                f"    {disk.display_id:<28} {format_bytes(disk.size_bytes):>10}  "
                f"{disk.format:<6}{load_suffix}{pin}"
            )
    if group_load is not None:
        for disk_load in group_load.disks:
            if disk_load.flagged_reason:
                display = format_disk_id(
                    disk_load.disk_key, _vm_name_for(vm_name_by_key, disk_load.disk_key)
                )
                lines.append(f"  ⚠ {display}: {disk_load.flagged_reason}")
        if group_load.no_series_matched:
            # REVIEW.md W-06/W-07: distinguish this from a genuinely idle
            # group -- every per-disk flag above is really one symptom of
            # the same cause, named once here instead of "idle".
            lines.append(
                "  ⚠ the resolved query filter matched no series at all -- not necessarily "
                "idle; check metrics.labels.node against verify-metrics"
            )
        elif group_load.idle:
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
            storage.id: compute_reserve_status(storage, group.disks) for storage in group.storages
        }
        header = f"Group {group.name}"
        if group_load is not None:
            decision = evaluate_group_gates(
                group_load,
                reserve_statuses,
                group,
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
            storage.id: compute_reserve_status(storage, group.disks) for storage in group.storages
        }
        storages_out = []
        for storage in group.storages:
            status = reserve_statuses[storage.id]
            entry: dict[str, object] = {
                "id": storage.id,
                "used_bytes": storage.used_bytes,
                "provisioned_used_bytes": status.managed_used_bytes,
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
                group,
                config.gates,
                last_load=last_loads_by_group.get(group.name),
            )
            gate_out = {
                "act": decision.act,
                "reason": decision.reason,
                "reserve_override": decision.reserve_override,
                "drift_fraction": decision.drift_fraction,
                "imbalance_fraction": decision.imbalance_fraction,
                "capacity_fraction": decision.capacity_fraction,
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
    client = _pve_client_for(resolved, args)
    # Read-only: never takes state.py's advisory lock (see its module
    # docstring) -- show-load never executes a migration, so there is
    # nothing here for the lock to protect against. Read once, reused for
    # both build_topology()'s (C2) cooldown pin and the gate's drift input.
    now = _now_for(args)
    state = load_state(_state_path_for(resolved, args))
    topology = _filter_groups(
        build_topology(client, resolved.config, state=state, now=now), args.group
    )
    prom_client = _metrics_client_for(resolved, args)
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
                now=now.timestamp(),
            )
        except MetricsError as exc:
            # Section 4's load numbers are not safety-critical the way (C4)/
            # (C5) reserve status is -- a Prometheus outage should not hide
            # accurate size/reserve info the rest of this command already
            # has, so this group's load is simply reported as unavailable.
            load_errors[group.name] = str(exc)
    if args.json:
        print(
            _dump_report_json(
                _render_show_load_json(
                    topology, resolved.config, group_loads, load_errors, last_loads_by_group
                ),
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
    vm_name: str,
    outcome: MoveOutcome | None = None,
) -> str:
    duration_str = "?"
    flag = ""
    if move_cost is not None:
        duration_str = f"~{format_duration_seconds(move_cost.duration_mirror_seconds)}"
        if move_cost.duration_wipe_seconds:
            duration_str += f" +wipe {format_duration_seconds(move_cost.duration_wipe_seconds)}"
        if move_cost.repair:
            flag += "  [repair]"
        if move_cost.exceeds_max_duration:
            flag += "  ⚠ exceeds migration.max_single_move_duration"
    change = -move.imbalance_reduction
    load_per_tib = _load_per_tib(load_by_key, move.disk_key, move.size_bytes)
    display_id = format_disk_id(move.disk_key, vm_name)
    line = (
        f"  {index}. {display_id:<28} {move.from_storage} → {move.to_storage}   "
        f"{format_bytes(move.size_bytes):>10}   {duration_str}   "
        f"Δimbalance {change:+.2f}   ℓ/z {load_per_tib:.2f}{flag}"
    )
    if outcome is not None:
        # `apply`'s per-move execution result (section 9.5): `plan` never
        # passes `outcome`, so this is a pure addition to the line, not a
        # second rendering of it (AGENTS.md section 5).
        line += f"  → {outcome.status}: {outcome.detail}"
    return line


def _render_plan_payback_lines(
    payback_result: PaybackResult, payback_ratio: float, vm_name_by_key: dict[str, str]
) -> list[str]:
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
    if payback_result.repair_exempt:
        lines.append(
            "  overridden: this plan repairs a reserve/free-space shortfall "
            f"({format_bytes(payback_result.reserve_shortfall_bytes_before)} → "
            f"{format_bytes(payback_result.reserve_shortfall_bytes_after)}), "
            "exempt from the economic test (section 7.3)"
        )
    if not payback_result.aggregate_ok:
        lines.append(
            "  ⚠ this plan's balance benefit does not outweigh its migration cost -- "
            "automatically re-solving with adjusted weights is not implemented yet; "
            "review before applying"
        )
    if payback_result.rejected_moves:
        lines.append(
            "  ⚠ blocked by the hard per-move duration rule (migration."
            "max_single_move_duration): "
            + ", ".join(
                format_disk_id(key, _vm_name_for(vm_name_by_key, key))
                for key in payback_result.rejected_moves
            )
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
    vm_name_by_key = _vm_name_map(group)
    for i, move in enumerate(schedule_result.order, start=1):
        outcome = outcomes_by_key.get(move.disk_key)
        lines.append(
            _render_plan_move_line(
                i,
                move,
                move_costs_by_key.get(move.disk_key),
                load_by_key,
                _vm_name_for(vm_name_by_key, move.disk_key),
                outcome,
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
            lines.extend(_render_plan_payback_lines(payback_result, payback_ratio, vm_name_by_key))
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
    vm_name_by_key = _vm_name_map(group)
    moves_out = []
    if schedule_result is not None:
        for move in schedule_result.order:
            move_cost = move_costs_by_key.get(move.disk_key)
            moves_out.append(
                {
                    "disk_key": move.disk_key,
                    "vmid": move.vmid,
                    "vm_name": _vm_name_for(vm_name_by_key, move.disk_key),
                    "device": move.device,
                    "from_storage": move.from_storage,
                    "to_storage": move.to_storage,
                    "size_bytes": move.size_bytes,
                    "imbalance_reduction": move.imbalance_reduction,
                    "repair": move_cost.repair if move_cost else None,
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
            "capacity_fraction": decision.capacity_fraction,
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
    # Section 5.3 (C7)'s counterpart to before_spread/after_spread, on fill
    # fraction rather than load -- needed alongside it (not in place of it)
    # for a fair MILP-vs-heuristic comparison once objective.delta_capacity_spread
    # is non-zero: a solve can legitimately trade a worse after_spread for a
    # much better after_capacity_spread (tests/corpus/validate_corpus.py's
    # check_milp_vs_heuristic() consumes both, not after_spread alone).
    before_capacity_spread = after_capacity_spread = None
    if solve_outcome is not None:
        average_fill = group_average_fill(group)
        before_capacity_spread = _spread_fraction(
            solve_outcome.initial_breakdown.fill_fraction, average_fill
        )
        if final_breakdown is not None:
            after_capacity_spread = _spread_fraction(final_breakdown.fill_fraction, average_fill)
    # REVIEW.md AA-01's own recommendation: "re-score every backend's
    # returned assignment through evaluate_assignment() at true weights" --
    # the full six-term objective (section 5.4), not one spread axis in
    # isolation, so a solver that is worse on the objective it was actually
    # asked to optimize is visible even when neither before_spread/
    # before_capacity_spread axis alone would show it.
    before_objective_total = after_objective_total = None
    if solve_outcome is not None:
        before_objective_total = solve_outcome.initial_breakdown.total
        if final_breakdown is not None:
            after_objective_total = final_breakdown.total
    payback_out = None
    if payback_result is not None:
        payback_out = {
            "benefit_load_seconds": payback_result.benefit_load_seconds,
            "total_cost_load_seconds": payback_result.total_cost_load_seconds,
            "ratio": payback_result.ratio,
            "aggregate_ok": payback_result.aggregate_ok,
            "rejected_moves": list(payback_result.rejected_moves),
            "accepted": payback_result.accepted,
            "repair_exempt": payback_result.repair_exempt,
            "reserve_shortfall_bytes_before": payback_result.reserve_shortfall_bytes_before,
            "reserve_shortfall_bytes_after": payback_result.reserve_shortfall_bytes_after,
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
        "before_capacity_spread": before_capacity_spread,
        "after_capacity_spread": after_capacity_spread,
        "before_objective_total": before_objective_total,
        "after_objective_total": after_objective_total,
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
    if reason.startswith("pending "):
        return "apply the pending change (reboot the VM) or revert it, then re-check"
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
            f"    {disk.display_id:<28} {format_bytes(disk.size_bytes):>10}  "
            f"on {disk.current_storage}"
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
    """The section 5.4 objective's six terms, individually -- the reason
    :class:`ObjectiveBreakdown` keeps them apart instead of collapsing to
    only ``.total`` in the first place (that class's own docstring)."""
    return (
        "  objective: "
        f"imbalance {breakdown.imbalance_term:.3g} + "
        f"moves {breakdown.move_count_term:.3g} + "
        f"bytes {breakdown.bytes_moved_term:.3g} + "
        f"fragmentation {breakdown.fragmentation_term:.3g} + "
        f"spread {breakdown.capacity_spread_term:.3g} + "
        f"reserve {breakdown.reserve_penalty_term:.3g} = {breakdown.total:.3g}"
    )


def _objective_breakdown_json(breakdown: ObjectiveBreakdown) -> dict[str, float]:
    """The one implementation ``explain --json``'s ``objective`` and
    ``rejected_alternative.{baseline,objective}`` fields all share (AGENTS.md
    section 5) -- so a third caller never has to guess which six keys a
    breakdown serializes to."""
    return {
        "imbalance_term": breakdown.imbalance_term,
        "move_count_term": breakdown.move_count_term,
        "bytes_moved_term": breakdown.bytes_moved_term,
        "fragmentation_term": breakdown.fragmentation_term,
        "capacity_spread_term": breakdown.capacity_spread_term,
        "reserve_penalty_term": breakdown.reserve_penalty_term,
        "total": breakdown.total,
    }


def _render_no_moves_lines(
    group: Group,
    group_plan: "_GroupPlan",
    objective: ObjectiveConfig,
    tiny_disk_bytes: int,
) -> list[str]:
    """Only called when the gate decided to ACT but the *final* assignment
    moves nothing -- an operator reading `plan`'s one-line verdict has no
    way to tell that apart from "the solver didn't try" without this.
    Shows the single-disk move closest to being worth taking and the
    term-by-term arithmetic that rejected it (section 5.4).

    X-10: a final assignment equal to the seed also happens when
    `order_moves()` staged away every move the solver *did* propose (total
    deadlock, `schedule_result.deadlocked` non-empty) -- there the
    objective was not lowest at the current assignment at all; the
    scheduler just could not reach anything else safely. The wording below
    only claims "objective is lowest" when nothing was deadlocked."""
    assert group_plan.group_load is not None and group_plan.final_breakdown is not None
    deadlocked_count = (
        len(group_plan.schedule_result.deadlocked) if group_plan.schedule_result else 0
    )
    deadlock_headline = (
        f"  no moves made: every proposed move was staged away by the scheduler "
        f"({deadlocked_count} deadlocked) -- not because the objective is lowest doing nothing"
    )
    candidate = best_single_disk_alternative(
        group,
        group_plan.group_load.load_by_disk_key(),
        objective,
        group_plan.group_load.average_utilization,
        group_average_fill(group),
        group_plan.final_breakdown,
        tiny_disk_bytes,
    )
    if candidate is None:
        if deadlocked_count:
            return [deadlock_headline]
        return [
            "  no moves made: no alternative exists to compare against "
            "(every disk is pinned, or the group has only one storage)"
        ]
    headline = (
        deadlock_headline
        if deadlocked_count
        else "  no moves made: the objective is lowest at the current assignment"
    )
    b, c = candidate.baseline, candidate.breakdown
    candidate_display_id = format_disk_id(
        candidate.disk_key, _vm_name_for(_vm_name_map(group), candidate.disk_key)
    )
    return [
        headline,
        f"  closest alternative: {candidate_display_id} {candidate.from_storage} → "
        f"{candidate.to_storage}",
        "    "
        + ", ".join(
            [
                f"imbalance {b.imbalance_term:.3g}→{c.imbalance_term:.3g}",
                f"moves {b.move_count_term:.3g}→{c.move_count_term:.3g}",
                f"bytes {b.bytes_moved_term:.3g}→{c.bytes_moved_term:.3g}",
                f"fragmentation {b.fragmentation_term:.3g}→{c.fragmentation_term:.3g}",
                f"spread {b.capacity_spread_term:.3g}→{c.capacity_spread_term:.3g}",
                f"reserve {b.reserve_penalty_term:.3g}→{c.reserve_penalty_term:.3g}",
            ]
        ),
        f"    total {b.total:.3g} → {c.total:.3g}  "
        f"(worse by {candidate.worse_by:.3g} -- rejected)",
    ]


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
        if group_plan.decision.act and not group_plan.final_breakdown.moved_disk_keys:
            extra.extend(
                _render_no_moves_lines(
                    group,
                    group_plan,
                    resolved.config.objective,
                    resolved.config.migration.tiny_disk_bytes,
                )
            )
    # The measured load every number above derives from -- show-load's own
    # per-storage/per-disk picture, section 4 (AGENTS.md section 5: one
    # implementation, reused rather than a second rendering of it).
    reserve_statuses = {
        storage.id: compute_reserve_status(storage, group.disks) for storage in group.storages
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
    group: Group,
    group_plan: "_GroupPlan",
    warn_fraction: float,
    objective: ObjectiveConfig,
    tiny_disk_bytes: int,
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
        storage.id: compute_reserve_status(storage, group.disks) for storage in group.storages
    }
    storages_out = []
    for storage in group.storages:
        status = reserve_statuses[storage.id]
        entry: dict[str, object] = {
            "id": storage.id,
            "used_bytes": storage.used_bytes,
            "provisioned_used_bytes": status.managed_used_bytes,
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
    out["objective"] = _objective_breakdown_json(breakdown) if breakdown is not None else None
    out["rejected_alternative"] = None
    if (
        group_plan.decision is not None
        and group_plan.decision.act
        and breakdown is not None
        and not breakdown.moved_disk_keys
        and group_plan.group_load is not None
    ):
        candidate = best_single_disk_alternative(
            group,
            load_by_key,
            objective,
            group_plan.group_load.average_utilization,
            group_average_fill(group),
            breakdown,
            tiny_disk_bytes,
        )
        if candidate is not None:
            out["rejected_alternative"] = {
                "disk_key": candidate.disk_key,
                "vmid": candidate.vmid,
                "vm_name": _vm_name_for(_vm_name_map(group), candidate.disk_key),
                "device": candidate.device,
                "from_storage": candidate.from_storage,
                "to_storage": candidate.to_storage,
                "baseline": _objective_breakdown_json(candidate.baseline),
                "objective": _objective_breakdown_json(candidate.breakdown),
                "worse_by": candidate.worse_by,
            }
    out["pinned_disks"] = [
        {
            "disk_key": d.key,
            "vmid": d.vmid,
            "vm_name": d.vm_name,
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
    groups_out = [
        _render_group_explain_json(
            group,
            group_plans[group.name],
            warn_fraction,
            resolved.config.objective,
            resolved.config.migration.tiny_disk_bytes,
        )
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


def _render_execution_json(
    result: ExecutionResult | None, vm_name_by_key: dict[str, str]
) -> dict[str, object] | None:
    """``None`` for a group ``apply`` never got as far as executing (a
    load error, or the gate said ``NO ACTION``) -- distinct from a group
    that executed and produced zero outcomes, which cannot happen in
    practice but would render as an empty list, not ``None``."""
    if result is None:
        return None
    return {
        "stopped_early": result.stopped_early,
        "stop_reason": result.stop_reason,
        "aborted": result.aborted,
        "replans_exhausted": result.replans_exhausted,
        "outcomes": [
            {
                "disk_key": outcome.disk_key,
                "vm_name": _vm_name_for(vm_name_by_key, outcome.disk_key),
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
        group_out["execution"] = _render_execution_json(
            execution_results.get(group.name), _vm_name_map(group)
        )
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
    backend: str  # "cbc" | "heuristic"
    status: str | None  # "optimal" | "feasible" for a MILP backend, None for the heuristic


def _solve_group(
    group: Group,
    load_by_key: dict[str, float],
    resolved: ResolvedConfig,
    cooldown_storages: frozenset[str],
) -> _SolveOutcome:
    """Section 5.5's backend dispatch. ``solver.backend: auto`` cascades
    CBC, then the heuristic; an explicitly forced backend that
    cannot produce a plan (library not importable, or no feasible solution
    within ``solver.time_limit_seconds``) falls back to the heuristic too
    -- section 13's failure-mode table says plainly "solver infeasible or
    timing out -> fall back to the heuristic; never emit a partial/
    unvalidated assignment", with no carve-out for a backend the operator
    explicitly named (`docs/manual/10-configuration.md`'s own
    `solver.backend` text: forcing one is "to reproduce or compare a
    result", not to disable this safety net). A forced backend that falls
    back anyway is logged at warning -- an operator who asked for `cbc`
    specifically should not have to diff `--json` output to notice `auto`
    quietly happened instead.
    """
    solver = resolved.config.solver
    cascade = {
        "auto": ("cbc",),
        "cbc": ("cbc",),
        "heuristic": (),
    }[solver.backend]
    for backend in cascade:
        result = optimize.solve(
            group,
            load_by_key,
            resolved.config.objective,
            backend,
            solver.time_limit_seconds,
            solver.mip_gap,
            cooldown_storages,
            # Under `auto` this call is a probe for whichever optional
            # solver is installed, and a missing one is the expected
            # answer, not a warning (section 2.3).
            probing=solver.backend == "auto",
            tiny_disk_bytes=resolved.config.migration.tiny_disk_bytes,
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
        solver.heuristic_iterations,
        cooldown_storages,
        resolved.config.migration.tiny_disk_bytes,
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
    # Sum of every storage's reserve/free-space shortfall (`r_s`) once this
    # run's plan has run -- or as things stand now when the gate decided not to
    # act. Only the monitoring status file reads it (section 2.4).
    shortfall_bytes: int = 0


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
    within ``gates.imbalance_threshold``) before anything trusts them at
    all. A model that fails -- or that cannot yet be
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
        "this run instead",
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


def _log_load_digest(group: Group, group_load: GroupLoad) -> None:
    """Section 2.3's ``load_digest``: what section 4 measured, compactly
    enough to put in a journal on every run and still reconstruct which
    storage was hot and how much of the group was measured at all."""
    logger.info(
        "group %s: load %.3f across %d disks",
        group.name,
        sum(s.load for s in group_load.storages),
        len(group_load.disks),
        extra={
            "event": "load_digest",
            "group": group.name,
            "idle": group_load.idle,
            "total_load": sum(s.load for s in group_load.storages),
            "average_utilization": group_load.average_utilization,
            "utilization": {s.storage_id: s.utilization for s in group_load.storages},
            "disks": len(group_load.disks),
            "disks_flagged": sum(1 for d in group_load.disks if d.flagged_reason is not None),
        },
    )


def _log_gate_decision(group: Group, decision: GateDecision, gates: GatesConfig) -> None:
    """Section 2.3's ``gate_decision``: the computed values *and* the
    thresholds they were compared against. Section 2.1's own wording --
    "each gate decision with its computed value and threshold" -- because
    "did not act" is only answerable months later if both halves are
    recorded, not just the verdict."""
    logger.info(
        "group %s: %s -- %s",
        group.name,
        "ACT" if decision.act else "NO ACTION",
        decision.reason,
        extra={
            "event": "gate_decision",
            "group": group.name,
            "act": decision.act,
            "reason": decision.reason,
            "reserve_override": decision.reserve_override,
            "drift_fraction": decision.drift_fraction,
            "imbalance_fraction": decision.imbalance_fraction,
            "capacity_fraction": decision.capacity_fraction,
            "drift_threshold": gates.drift_threshold,
            "imbalance_threshold": gates.imbalance_threshold,
            "capacity_spread_threshold": gates.capacity_spread_threshold,
        },
    )


def _log_plan_selected(
    group: Group,
    solve_outcome: "_SolveOutcome",
    schedule_result: ScheduleResult,
    final_breakdown: ObjectiveBreakdown,
    group_load: GroupLoad,
) -> None:
    """Section 2.3's ``plan_selected``, and ``deadlock`` when section 8's
    scheduler could not order part of the plan."""
    logger.info(
        "group %s: %s plan, %d move(s)",
        group.name,
        solve_outcome.backend,
        len(schedule_result.order),
        extra={
            "event": "plan_selected",
            "group": group.name,
            "backend": solve_outcome.backend,
            "solver_status": solve_outcome.status,
            "moves": len(schedule_result.order),
            "move_disk_keys": [m.disk_key for m in schedule_result.order],
            "objective": _objective_breakdown_json(final_breakdown),
            "before_spread": _spread_fraction(
                solve_outcome.initial_breakdown.utilization, group_load.average_utilization
            ),
            "after_spread": _spread_fraction(
                final_breakdown.utilization, group_load.average_utilization
            ),
        },
    )
    if schedule_result.deadlocked:
        logger.warning(
            "group %s: %s",
            group.name,
            schedule_result.deadlocked_msg,
            extra={
                "event": "deadlock",
                "group": group.name,
                "deadlocked": list(schedule_result.deadlocked),
                # `detail`, not `message`: the latter is a reserved
                # LogRecord attribute and `extra=` refuses to shadow it.
                "detail": schedule_result.deadlocked_msg,
            },
        )


def _log_payback_verdict(group: Group, payback: PaybackResult, required_ratio: float) -> None:
    """Section 2.3's ``payback_verdict``: section 7's arithmetic, not just
    its yes/no -- an operator asking "why did it refuse to move anything"
    needs the ratio it computed and the one it needed."""
    logger.info(
        "group %s: payback ratio %.3g (need %.3g) -> %s",
        group.name,
        payback.ratio,
        required_ratio,
        "accepted" if payback.accepted else "rejected",
        extra={
            "event": "payback_verdict",
            "group": group.name,
            "accepted": payback.accepted,
            "aggregate_ok": payback.aggregate_ok,
            "benefit_load_seconds": payback.benefit_load_seconds,
            "total_cost_load_seconds": payback.total_cost_load_seconds,
            "ratio": payback.ratio,
            "required_ratio": required_ratio,
            "rejected_moves": list(payback.rejected_moves),
            "repair_exempt": payback.repair_exempt,
            "reserve_shortfall_bytes_before": payback.reserve_shortfall_bytes_before,
            "reserve_shortfall_bytes_after": payback.reserve_shortfall_bytes_after,
        },
    )


def _plan_group(
    group: Group,
    resolved: ResolvedConfig,
    prom_client: PrometheusClient,
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
            now=now.timestamp(),
        )
    except MetricsError as exc:
        # Section 6: gating (and so planning) cannot proceed without a
        # load to gate on -- unlike show-load's size/reserve report,
        # nothing here is safe to show without it.
        logger.warning(
            "group %s: load model unavailable: %s",
            group.name,
            exc,
            extra={"event": "load_unavailable", "group": group.name},
        )
        return _GroupPlan(load_error=str(exc))

    _log_load_digest(group, group_load)
    reserve_statuses: dict[str, ReserveStatus] = {
        storage.id: compute_reserve_status(storage, group.disks) for storage in group.storages
    }
    decision = evaluate_group_gates(
        group_load,
        reserve_statuses,
        group,
        resolved.config.gates,
        last_load=last_loads_by_group.get(group.name),
    )
    _log_gate_decision(group, decision, resolved.config.gates)
    if not decision.act:
        return _GroupPlan(
            group_load=group_load,
            decision=decision,
            shortfall_bytes=total_shortfall_bytes(group.storages, group.disks),
        )

    cooldown_storages = frozenset(
        active_storage_cooldowns(
            state, group.name, resolved.config.gates.cooldown_per_storage_seconds, now
        )
    )
    solve_outcome = _solve_group(group, group_load.load_by_disk_key(), resolved, cooldown_storages)
    schedule_result = order_moves(
        group,
        solve_outcome.assignment,
        group_load.load_by_disk_key(),
        resolved.config.objective,
        resolved.config.migration.tiny_disk_bytes,
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
        group_average_utilization(group, group_load.load_by_disk_key()),
        group_average_fill(group),
        resolved.config.migration.tiny_disk_bytes,
    )

    storages_by_id = {s.id: s for s in group.storages}
    move_costs = [
        compute_move_cost(move, storages_by_id[move.from_storage], resolved.config.migration)
        for move in schedule_result.order
    ]
    spread_metric = resolved.config.objective.spread_metric
    benefit = compute_benefit_load_seconds(
        resolved.config.objective.alpha_spread,
        raw_spread(solve_outcome.initial_breakdown, spread_metric),
        raw_spread(final_breakdown, spread_metric),
        resolved.config.objective.delta_capacity_spread,
        raw_capacity_spread(solve_outcome.initial_breakdown),
        raw_capacity_spread(final_breakdown),
        resolved.config.migration.payback_horizon_seconds,
        resolved.config.objective.kappa_vm_affinity,
        raw_affinity_debt(solve_outcome.initial_breakdown),
        raw_affinity_debt(final_breakdown),
    )
    # Section 7.3's outcome trigger and revert test both score the plan's
    # *executed* endpoint -- final_assignment with every disk a hard
    # per-move rule has taken out (exceeds_max_duration, already
    # known from move_costs) held back at its current storage
    # -- not the solver's raw target. "What it will really run", not merely
    # "what got ordered".
    excluded_disk_keys = frozenset(mc.disk_key for mc in move_costs if mc.exceeds_max_duration)
    executed_final_assignment = executed_assignment(
        group, schedule_result.final_assignment, excluded_disk_keys
    )
    repair_by_key = repair_markers(group, schedule_result.order, executed_final_assignment)
    move_costs = [dataclasses.replace(mc, repair=repair_by_key[mc.disk_key]) for mc in move_costs]
    current_shortfall_bytes = total_shortfall_bytes(group.storages, group.disks)
    final_shortfall_bytes = total_shortfall_bytes(
        group.storages,
        group.disks,
        storage_of=lambda d: executed_final_assignment.get(d.key, d.current_storage),
    )
    payback_result = evaluate_plan_payback(
        move_costs,
        benefit,
        resolved.config.migration.payback_ratio,
        current_shortfall_bytes,
        final_shortfall_bytes,
    )
    _log_plan_selected(group, solve_outcome, schedule_result, final_breakdown, group_load)
    _log_payback_verdict(group, payback_result, resolved.config.migration.payback_ratio)
    return _GroupPlan(
        group_load=group_load,
        decision=decision,
        solve_outcome=solve_outcome,
        schedule_result=schedule_result,
        final_breakdown=final_breakdown,
        payback_result=payback_result,
        shortfall_bytes=final_shortfall_bytes,
    )


def _handle_plan(resolved: ResolvedConfig, args: argparse.Namespace, mode: str) -> int:
    del mode
    client = _pve_client_for(resolved, args)
    # Read-only: plan never executes a migration, so -- like show-load --
    # it never takes state.py's advisory lock (see that module's docstring).
    # Read once, reused for build_topology()'s (C2) cooldown pin, the
    # gate's drift input, and run_heuristic()'s storage-cooldown exclusion.
    now = _now_for(args)
    state = load_state(_state_path_for(resolved, args))
    topology = _filter_groups(
        build_topology(client, resolved.config, state=state, now=now), args.group
    )
    prom_client = _metrics_client_for(resolved, args)
    node_selector = _resolve_node_selector_for_run(client, resolved.config.metrics)
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
            _dump_report_json(
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
    # A group whose load model could not be computed (a Prometheus error) is
    # a failed plan, not a quiet one: exit 1 so a wrapper script or a
    # monitoring check cannot mistake "could not look" for "nothing to do".
    return 1 if load_errors else 0


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
    client = _pve_client_for(resolved, args)
    now = _now_for(args)
    state = load_state(_state_path_for(resolved, args))
    topology = _filter_groups(
        build_topology(client, resolved.config, state=state, now=now), args.group
    )
    prom_client = _metrics_client_for(resolved, args)
    node_selector = _resolve_node_selector_for_run(client, resolved.config.metrics)
    last_loads_by_group = _last_loads_by_group(state, topology)

    group_plans = {
        group.name: _plan_group(
            group,
            resolved,
            prom_client,
            last_loads_by_group,
            state,
            now,
            node_selector,
        )
        for group in topology.groups
    }

    if args.json:
        print(
            _dump_report_json(
                _render_explain_json(topology, group_plans, resolved, node_selector),
            )
        )
    else:
        print(
            _render_explain_human(
                topology, group_plans, resolved, node_selector, verbose=args.verbose > 0
            )
        )
    return 1 if any(gp.load_error is not None for gp in group_plans.values()) else 0


def _make_confirm_move_interactively(group: Group) -> Callable[[ScheduledMove], str]:
    """Builds ``execute.py``'s ``ConfirmCallback`` -- the only ``input()``
    call in this codebase -- closing over ``group`` so the prompt can show
    each move's VM name without widening the ``Callable[[ScheduledMove],
    str]`` contract execute.py itself relies on. ``execute.py``'s own
    module docstring reserves interactive prompting for ``cli.py``, since
    it is the only module allowed to talk to the terminal (see this
    module's own docstring)."""
    vm_name_by_key = _vm_name_map(group)

    def confirm(move: ScheduledMove) -> str:
        """Loops on anything but ``y``/``n``/``a``/``q`` rather than
        handing ``execute_plan()`` a value its ``ConfirmCallback`` contract
        does not accept -- retrying badly-typed input is this function's
        job, not a ``ValueError`` execute.py would have to raise and this
        function would have to catch anyway."""
        display_id = format_disk_id(move.disk_key, _vm_name_for(vm_name_by_key, move.disk_key))
        prompt = (
            f"  {display_id}  {move.from_storage} → {move.to_storage}  "
            f"{format_bytes(move.size_bytes)}  [y]es/[n]o skip/[a]ll remaining/[q]uit? "
        )
        while True:
            answer = input(prompt).strip().lower()
            if answer in ("y", "n", "a", "q"):
                return answer
            print("  please answer y, n, a or q", file=sys.stderr)

    return confirm


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
    """Section 7.3's hard per-move duration rule (``rejected_moves``)
    rendered as ``"skipped"`` outcomes. Factored out of
    :func:`_apply_payback_gate` purely to stay within this project's flake8
    complexity limit."""
    rejected_keys = set(payback.rejected_moves)
    outcomes: list[MoveOutcome] = []
    for m in order:
        if m.disk_key not in rejected_keys:
            continue
        detail = "refused: would take longer than migration.max_single_move_duration allows"
        outcomes.append(MoveOutcome(m.disk_key, m.from_storage, m.to_storage, "skipped", detail))
    return outcomes


def _apply_payback_gate(
    client: PveClient,
    group: Group,
    group_plan: _GroupPlan,
    migration: MigrationConfig,
    execution: ExecutionConfig,
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
    per-move `migration.max_single_move_duration` rule) must never reach `execute.py`
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
    excluded_keys = set(payback.rejected_moves)
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
    abort_reason: str | None = None
    replans_exhausted = False

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
        if result.aborted:
            # A check the executor could not make (a PVE API error while
            # re-reading the VM or the target) -- re-planning would run
            # into the same wall, so this ends the whole run, whatever
            # `replan_needed` outcomes accompany it.
            break
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
            replans_exhausted = True
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
            fresh_last_loads,
            state_box.value,
            fresh_now,
            node_selector,
        )
        if new_plan.load_error is not None:
            # A metrics error is not "no further action is needed": the
            # re-plan could not be computed at all, and treating that as a
            # clean stop would let a Prometheus outage end a run with exit
            # 0 (section 9.2, "Errors are not mismatches").
            abort_reason = f"load model unavailable while re-planning: {new_plan.load_error}"
            stopped_early = True
            stop_reason = abort_reason
            break
        if (
            new_plan.decision is None
            or not new_plan.decision.act
            or new_plan.schedule_result is None
        ):
            # Re-planning concluded no further action is needed -- "the
            # gates may well conclude no further action is needed, which
            # is a correct outcome" (section 9.2 step 3), not a failure to
            # report as one.
            stopped_early = False
            stop_reason = None
            break
        group = fresh_group
        group_plan = new_plan

    return (
        ExecutionResult(
            tuple(all_outcomes),
            stopped_early,
            stop_reason,
            abort_reason=abort_reason,
            replans_exhausted=replans_exhausted,
            replans=execution.max_replans_per_run - replans_left,
        ),
        migrations_budget,
    )


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
        _run_stats(args).lock_held = True
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
        client = _pve_client_for(resolved, args)
        resolved, state = _reconcile_inflight_and_fold_exclusions(client, resolved, state_box)

        topology = _filter_groups(
            build_topology(client, resolved.config, state=state, now=now), args.group
        )
        prom_client = _metrics_client_for(resolved, args)
        node_selector = _resolve_node_selector_for_run(client, resolved.config.metrics)
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
                last_loads_by_group,
                state,
                now,
                node_selector,
            )
            if group_plan.load_error is not None:
                # A metrics error fails the whole run: no later group is
                # planned or executed on a cluster the tool cannot fully
                # observe (moves already completed stay recorded).
                load_errors[group.name] = group_plan.load_error
                _run_stats(args).errors.append(
                    f"group {group.name}: load model unavailable: {group_plan.load_error}"
                )
                break
            assert group_plan.group_load is not None and group_plan.decision is not None
            group_loads[group.name] = group_plan.group_load
            gate_decisions[group.name] = group_plan.decision
            _note_shortfall_for_status(args, group, group_plan)
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
                    group_plan.payback_result,
                    resolved.config.migration.payback_ratio,
                    _vm_name_map(group),
                ):
                    print(line)

            if mode == "auto":
                result, migrations_budget = _run_auto_group(
                    client,
                    resolved,
                    prom_client,
                    state_box,
                    group,
                    group_plan,
                    migrations_budget,
                    node_selector=node_selector,
                    on_inflight_started=on_inflight_started,
                    on_inflight_finished=on_inflight_finished,
                )
            else:
                confirm_callback = (
                    _make_confirm_move_interactively(group) if mode == "confirm" else None
                )
                result = _apply_payback_gate(
                    client,
                    group,
                    group_plan,
                    resolved.config.migration,
                    resolved.config.execution,
                    mode,
                    resolved.config.migration.payback_ratio,
                    resolved.config.exclude,
                    confirm_callback,
                    on_inflight_started=on_inflight_started,
                    on_inflight_finished=on_inflight_finished,
                )
            execution_results[group.name] = result
            _accumulate_move_stats(args, group, result)
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

            if result.stop_reason == "operator quit" or result.aborted:
                # A human asked to stop the whole apply run, not just this
                # group -- section 9.1's `[q]uit` is an operator decision,
                # not a per-group one. An `aborted` result (an API or
                # metrics error the executor could not plan around) ends the
                # whole run the same way: no later group starts.
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
            _dump_report_json(
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

    return _apply_exit_code(execution_results, load_errors)


def _note_shortfall_for_status(
    args: argparse.Namespace, group: Group, group_plan: _GroupPlan
) -> None:
    """A group that still breaches its reserve or free-space requirement once
    this run's plan has run needs a human (the tool never trades the reserve
    for balance, so it will not fix this by itself): a status-file warning."""
    if group_plan.shortfall_bytes > 0:
        _run_stats(args).warnings.append(
            f"group {group.name}: {format_bytes(group_plan.shortfall_bytes)} short of its "
            "snapshot reserve / free-space requirement after this run's plan"
        )


def _apply_exit_code(
    execution_results: Mapping[str, ExecutionResult], load_errors: Mapping[str, str]
) -> int:
    """``apply``'s exit status: ``1`` for a failed move, an aborted group
    (a PVE or metrics error the run could not plan around) or a group whose
    load could not be computed; ``0`` otherwise -- including a run that
    bailed out after exhausting ``execution.max_replans_per_run``, which is
    external churn to retry later, not a failure (section 9.2)."""
    any_failure = any(
        outcome.status == "failed"
        for result in execution_results.values()
        for outcome in result.outcomes
    )
    aborted = any(result.aborted for result in execution_results.values())
    return 1 if (any_failure or aborted or load_errors) else 0


def _source_suffix(source: str) -> str:
    return f" ({source})" if source else ""


def _render_verify_storages_human(topology: Topology, config: Any) -> str:
    lines: list[str] = []
    for group in topology.groups:
        lines.append(f"Group {group.name}")
        for storage in group.storages:
            largest = largest_disk_bytes(group.disks, storage.id)
            state = "on" if storage.saferemove else "off"
            lines.append(f"  {storage.id}  saferemove={state}")
            lines.append(
                "    free_space: soft="
                f"{format_bytes(storage.free_space_soft_bytes)}"
                f"{_source_suffix(storage.free_space_soft_source)}  hard="
                f"{format_bytes(storage.free_space_hard_bytes)}"
                f"{_source_suffix(storage.free_space_hard_source)}"
            )
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
                    "free_space_soft_bytes": storage.free_space_soft_bytes,
                    "free_space_hard_bytes": storage.free_space_hard_bytes,
                    "free_space_soft_source": storage.free_space_soft_source,
                    "free_space_hard_source": storage.free_space_hard_source,
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
    client = _pve_client_for(resolved, args)
    topology = _filter_groups(build_topology(client, resolved.config), args.group)
    if args.json:
        print(_dump_report_json(_render_verify_storages_json(topology, resolved.config)))
    else:
        print(_render_verify_storages_human(topology, resolved.config))
    return 0


def _render_collect_testdata_human(estimate: collect.CaptureEstimate, config: Any) -> str:
    lines = [
        f"groups: {estimate.group_count}   disks: {estimate.disk_count}",
        f"range: {format_duration_seconds(estimate.range_seconds)}  "
        f"step: {format_duration_seconds(estimate.step_seconds)}",
        f"estimated Prometheus queries: {estimate.query_count}",
        f"estimated series sample points: {estimate.sample_points}",
    ]
    if estimate.exceeds(config.support.max_series_points):
        lines.append(
            f"REFUSED: exceeds support.max_series_points ({config.support.max_series_points}) "
            "-- pass --range/--step/--no-series to bring it under, or raise the config limit"
        )
    return "\n".join(lines)


def _handle_collect_testdata(resolved: ResolvedConfig, args: argparse.Namespace, mode: str) -> int:
    """Section 16.4. Always the real clients -- collect-testdata needs a
    live cluster and is refused outright under ``--replay`` (``main()``)."""
    del mode
    client = build_pve_client(resolved.config.proxmox)
    step_seconds = parse_duration_seconds(args.step) if args.step else None

    if args.estimate:
        # estimate_capture() needs a topology, which needs the full PVE
        # inventory read (every VM config, every content listing, every
        # status call) -- there is no cheaper way to size a capture, so
        # this is genuinely one read pass, not a fetch-nothing preview
        # (X-05; docs/manual/26-collect-testdata-and-replay.md's
        # --estimate row says so).
        topology = build_topology(client, resolved.config)
        range_seconds = (
            parse_duration_seconds(args.range)
            if args.range
            else collect.capture_range_seconds(resolved.config, None)
        )
        estimate = collect.estimate_capture(
            topology,
            resolved.config,
            range_seconds=range_seconds,
            step_seconds=step_seconds or resolved.config.metrics.step_seconds,
            no_series=args.no_series,
        )
        if args.json:
            print(
                _dump_report_json(
                    {
                        "group_count": estimate.group_count,
                        "disk_count": estimate.disk_count,
                        "query_count": estimate.query_count,
                        "sample_points": estimate.sample_points,
                        "range_seconds": estimate.range_seconds,
                        "step_seconds": estimate.step_seconds,
                        "refused": estimate.exceeds(resolved.config.support.max_series_points),
                    },
                )
            )
        else:
            print(_render_collect_testdata_human(estimate, resolved.config))
        return 0

    # Not --estimate: capture_bundle() below builds its own topology
    # through the *recording* client (so the read pass is captured into
    # the bundle) and runs the identical estimate/refusal check itself
    # before issuing a single Prometheus query. Building a second, bare
    # topology here first used to cost the cluster's API a second full
    # inventory read for nothing -- section 16.2's "one planning run's
    # worth of API calls, not a multiple of it" (X-05, fixed).
    prom_client = PrometheusClient(resolved.config.prometheus)
    options = collect.CaptureOptions(
        output_dir=args.output or resolved.config.support.bundle_dir,
        range_seconds=parse_duration_seconds(args.range) if args.range else None,
        step_seconds=step_seconds,
        no_series=args.no_series,
        no_archive=args.no_archive,
        salt_path=args.salt_file,
        new_salt=args.new_salt,
    )
    bundle = collect.capture_bundle(client, prom_client, resolved, options)
    collect.write_bundle_dir(options.output_dir, bundle)
    if not options.no_archive:
        collect.write_tarball(options.output_dir, f"{options.output_dir}.tar.gz")

    if args.json:
        print(_dump_report_json(bundle.manifest))
    else:
        counts = bundle.manifest["counts"]
        print(f"bundle: {options.output_dir}")
        print(
            f"groups={counts['groups']} storages={counts['storages']} vms={counts['vms']} "
            f"disks={counts['disks']}"
        )
        print(f"salt fingerprint: {bundle.salt_fingerprint}")
        failures = [c for c in bundle.manifest["calls"] if c["outcome"] == "http_error"]
        if failures:
            print(f"{len(failures)} capture call(s) failed (see manifest.json for detail):")
            for f in failures[:10]:
                print(f"  {f['description']}: {f['detail']}")
    return 0 if bundle.ok else 1


_COMMAND_HANDLERS: dict[str, CommandHandler] = {
    name: _make_not_yet_implemented_handler(name) for name in _SUBCOMMANDS
}
_COMMAND_HANDLERS["verify-metrics"] = _handle_verify_metrics
_COMMAND_HANDLERS["show-load"] = _handle_show_load
_COMMAND_HANDLERS["verify-storages"] = _handle_verify_storages
_COMMAND_HANDLERS["plan"] = _handle_plan
_COMMAND_HANDLERS["apply"] = _handle_apply
_COMMAND_HANDLERS["explain"] = _handle_explain
_COMMAND_HANDLERS["collect-testdata"] = _handle_collect_testdata


# ------------------------------------------------------------------- main


def _pre_config_usage_error(args: argparse.Namespace) -> str | None:
    """Section 16.4/16.5 usage errors decidable from ``args`` alone, before
    the network or even the config file is touched. Returns the message to
    print, or ``None`` if none apply."""
    if args.command == "collect-testdata" and args.mode in ("confirm", "auto"):
        return "collect-testdata is read-only; --mode confirm/auto is a usage error " "alongside it"
    if args.replay and args.command == "apply":
        return "apply is refused under --replay (section 16.5)"
    if args.replay and args.command == "collect-testdata":
        return "collect-testdata needs a live cluster; it cannot run under --replay"
    return None


def _replay_config_path(args: argparse.Namespace) -> tuple[str | None, bool]:
    """``(config_path, require_connection)`` for :func:`load_config` --
    section 16.5: the bundle's own ``config.yaml`` unless ``-c`` overrides
    it, and never a hard failure over the credentials/endpoints a bundle
    deliberately omits."""
    if args.replay:
        return args.config or str(Path(args.replay) / "config.yaml"), False
    return args.config, True


def _run_handler(
    resolved: ResolvedConfig,
    args: argparse.Namespace,
    effective_mode: str,
    log_format: str,
    started_at: float,
) -> int:
    """Run the command's handler and turn its outcome into an exit code: a
    ``DrsError`` is an operational failure (logged, exit ``1``); anything else
    is a bug and is re-raised -- after the monitoring status file has been told
    (section 2.4), so a crash cannot leave the previous run's ``OK`` in place."""
    handler = _COMMAND_HANDLERS[args.command]
    try:
        return handler(resolved, args, effective_mode)
    except DrsError as exc:
        logger.error(str(exc), extra={"event": "command_failed", "command": args.command})
        if log_format == "json":
            # In text format the record above *is* this line; printing both
            # would report one failure twice on one stream (section 2.3).
            print(f"pve-storage-drs: {exc}", file=sys.stderr)
        _run_stats(args).errors.append(str(exc))
        return 1
    except Exception as exc:
        _run_stats(args).errors.append(f"unexpected {type(exc).__name__}: {exc}")
        _publish_status_file(resolved, args, effective_mode, 1, started_at)
        raise


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

    usage_error = _pre_config_usage_error(args)
    if usage_error is not None:
        print(f"pve-storage-drs: {usage_error}", file=sys.stderr)
        return 2

    config_path, require_connection = _replay_config_path(args)
    try:
        resolved = load_config(config_path, require_connection=require_connection)
    except ConfigError as exc:
        # Before `configure_logging()` deliberately: a config this run could
        # not read is a usage failure, reported on stderr in plain text, not
        # an event in a run that never started.
        print(f"pve-storage-drs: {exc}", file=sys.stderr)
        return 1

    configured_mode = resolved.config.execution.mode
    # X-10: this refusal used to run *after* `_start_logging_and_announce_run()`
    # and `apply_mode_override()`, so `--replay ... --mode auto <cmd>` printed
    # `run_started` and an escalating `mode_override` WARNING -- announcing a
    # run it was about to refuse to start. Computed here, before either logs
    # a thing, from the same `args.mode or configured_mode` rule
    # `apply_mode_override()` itself applies -- no log call yet, so nothing to
    # reorder around.
    intended_effective_mode = args.mode if args.mode is not None else configured_mode
    if args.replay and intended_effective_mode != "dry-run":
        print(
            f"pve-storage-drs: --replay only ever runs dry-run; refusing effective mode "
            f"{intended_effective_mode!r} (section 16.5)",
            file=sys.stderr,
        )
        return 2

    log_format = _start_logging_and_announce_run(args, resolved, configured_mode)

    started_at = time.monotonic()
    effective_mode = configured_mode
    if args.mode is not None:
        effective_mode = apply_mode_override(configured_mode, args.mode)

    args.run_stats = _RunStats()
    exit_code = _run_handler(resolved, args, effective_mode, log_format, started_at)
    _log_run_summary(args, effective_mode, exit_code, started_at)
    _publish_status_file(resolved, args, effective_mode, exit_code, started_at)
    return exit_code


if __name__ == "__main__":  # pragma: no cover - exercised via the entry point
    sys.exit(main())
