# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Execute an already-scheduled plan. See IMPLEMENTATION_PLAN.md section 9.

``execute_plan()`` walks one group's ``schedule.ScheduleResult.order`` and,
for each move, re-validates it against the *live* cluster immediately
before issuing it (section 9.2: never trust the plan alone -- the VM may
have moved node, the disk may no longer be on the expected source, a
snapshot may have appeared), waits out any VM config lock rather than
failing (section 9.3.1, `.agents/domain-invariants.md` rule 5: locks are
an open set, never whitelisted), issues ``move_disk``, and does not
consider the move done until **three** things hold, not one (section
9.3.2, domain rule 4): the task reports ``exitstatus: OK``, the source
volume is gone from the source storage's content listing, and the VM's
config lock is clear again -- ``saferemove`` can hold the first two apart
by hours.

``dry-run`` issues no API calls at all. ``confirm`` asks its caller (via
``ConfirmCallback`` -- interactive prompting is `cli.py`'s job, the only
module allowed to talk to the terminal) before each move, honouring
`[y]es/[n]o skip/[a]ll remaining/[q]uit` (section 9.1). ``auto`` behaves
like `[a]ll remaining` chosen up front, unprompted -- **but this module
does not itself enforce `execution.time_windows`, `max_migrations_per_run`
or the multi-window concurrency caps**; those are section 12 phase 8
("auto mode + time windows"), a later, separate phase from this one
(phase 7's own "done when" names only `confirm` mode). `cli.py` is what
currently refuses to run `apply` in `auto` mode at all, rather than run it
unattended without the safety rails its own manual page documents for it
-- see ``docs/internals/92-execute.md``.

A move never gets a second chance to "fix" the plan around it: any
pre-flight mismatch, or a live transient-invariant check that no longer
holds, stops the run with ``status="replan_needed"`` rather than adjusting
anything (section 9.2's re-plan protocol: "abandon the remaining moves...
do not attempt to patch it"). **This module does not itself re-invoke the
whole pipeline** (gates/solve/payback/order) the way section 9.2's re-plan
protocol's steps 3-5 describe -- that needs `cli.py`-level orchestration
across multiple `execute_plan()` calls, which is a real, separately-scoped
piece of work, not implemented here; see ``docs/internals/92-execute.md``.

Orphaned target volumes (section 9.4, domain rule 6) are detected after a
failed move and reported in that move's own outcome -- **never deleted**.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from proxmox_storage_drs.config import ExecutionConfig, LocksConfig, MigrationConfig
from proxmox_storage_drs.exceptions import PveApiError
from proxmox_storage_drs.pve import PveClient
from proxmox_storage_drs.reserve import largest_disk_bytes
from proxmox_storage_drs.schedule import ScheduledMove, ScheduleResult
from proxmox_storage_drs.topology import DISK_KEY_RE, Disk, Group, Storage, parse_disk_spec

logger = logging.getLogger(__name__)


def _real_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class Clock:
    """Real by default. Tests inject a fake whose ``sleep()`` advances
    ``now()`` instantly instead of actually waiting
    (`.agents/testing.md`: "no `time.sleep` for real durations; inject the
    clock") -- every wait loop below measures elapsed time via ``now()``,
    never by counting `sleep()` calls, so a fake clock exercises the exact
    same timeout arithmetic production does."""

    now: Callable[[], datetime] = _real_now
    sleep: Callable[[float], None] = time.sleep


# One shared, stateless instance -- `Clock` holds only function references,
# never per-call state, so reusing it as `execute_plan()`'s default (rather
# than constructing a fresh one at every call, or the flake8-bugbear-flagged
# `Clock()` call-in-a-default-expression) is safe.
_REAL_CLOCK = Clock()


@dataclass(frozen=True, slots=True)
class MoveOutcome:
    """One move's fate, for section 9.5's per-move report.

    ``status``: ``"would_move"`` (dry-run, nothing issued), ``"moved"``
    (all three of section 9.3.2's conditions held), ``"skipped"``
    (operator declined, or a lock timeout with
    ``execution.locks.on_timeout: skip``), ``"failed"`` (the `move_disk`
    task itself did not succeed, or a lock timeout with
    ``execution.locks.on_timeout: abort``), ``"draining"`` (task succeeded
    but the source has not released within
    ``execution.source_release.timeout`` -- not a failure, an ongoing
    `saferemove` wipe section 8.2 already models), or ``"replan_needed"``
    (a pre-flight or live transient-invariant mismatch -- the plan no
    longer matches reality).

    ``always_stop`` is set only for a lock timeout with
    ``execution.locks.on_timeout: abort`` -- the manual's own words for that
    setting are "abort **the run**", a distinct, explicit per-config
    decision from ``execution.abort_on_failure``'s general "stop after any
    failed move" policy, which a plain `move_disk` task failure still goes
    through unmodified."""

    disk_key: str
    from_storage: str
    to_storage: str
    status: str
    detail: str
    upid: str | None = None
    orphaned_volumes: tuple[str, ...] = ()
    always_stop: bool = False


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """One group's ``execute_plan()`` call. ``stopped_early`` is true for
    any reason the remaining moves were never attempted -- an operator
    quitting confirm mode is not a failure, a `replan_needed` or (with
    ``execution.abort_on_failure``) a genuine failure both are; the
    distinction is in ``outcomes``, not in this flag."""

    outcomes: tuple[MoveOutcome, ...]
    stopped_early: bool
    stop_reason: str | None


ConfirmCallback = Callable[[ScheduledMove], str]  # returns "y" | "n" | "a" | "q"


@dataclass(frozen=True, slots=True)
class _PreflightResult:
    """``mismatch`` is ``None`` when every section 9.2 re-check passed;
    ``volid`` (needed only when ``mismatch`` is ``None``) is the exact
    volume id section 9.3.2's completion check watches for."""

    mismatch: str | None
    node: str | None = None
    lock: str | None = None
    volid: str | None = None


def _vm_resource(client: PveClient, vmid: int) -> dict[str, object] | None:
    for resource in client.vm_resources():
        if resource.get("vmid") == vmid:
            return resource
    return None


def _preflight(client: PveClient, disk: Disk, move: ScheduledMove) -> _PreflightResult:
    """Section 9.2's five re-checks, immediately before issuing one move.

    Re-fetches everything needed fresh -- the per-run topology cache
    (section 3.5) is deliberately bypassed here, since its whole point was
    to avoid re-fetching for *planning*, not to avoid re-validating right
    before a mutation."""
    resource = _vm_resource(client, disk.vmid)
    if resource is None:
        return _PreflightResult(f"VM {disk.vmid} no longer found in cluster resources")
    node = str(resource.get("node"))

    try:
        config = client.vm_config(node, disk.vmid)
    except PveApiError as exc:
        return _PreflightResult(f"could not re-fetch VM {disk.vmid}'s config on {node!r}: {exc}")

    value = config.get(move.device)
    if not isinstance(value, str):
        return _PreflightResult(f"{move.disk_key} is no longer present in the VM's config")
    storage_id, volume_name, _params = parse_disk_spec(value)
    if storage_id != move.from_storage:
        return _PreflightResult(
            f"{move.disk_key} is now on {storage_id!r}, not the planned {move.from_storage!r}"
        )

    if resource.get("status") != "running":
        return _PreflightResult(f"VM {disk.vmid} is no longer running")

    real_snapshots = [s for s in client.vm_snapshots(node, disk.vmid) if s.get("name") != "current"]
    if real_snapshots:
        return _PreflightResult(
            f"VM {disk.vmid} now has {len(real_snapshots)} snapshot(s) that did not exist when "
            "this plan was built -- move_disk delete=1 would be rejected"
        )

    lock = config.get("lock")
    volid = f"{move.from_storage}:{volume_name}"
    return _PreflightResult(
        None, node=node, lock=lock if isinstance(lock, str) else None, volid=volid
    )


def _wait_for_unlocked(
    client: PveClient, node: str, vmid: int, locks: LocksConfig, clock: Clock
) -> tuple[bool, str | None]:
    """Section 9.3.1: any non-empty ``lock`` means wait, never whitelist a
    value (`.agents/domain-invariants.md` rule 5). Returns ``(True, None)``
    once clear, or ``(False, last_seen_lock)`` on timeout."""
    start = clock.now()
    lock = client.vm_status_current(node, vmid).get("lock")
    warned = False
    while lock:
        elapsed = (clock.now() - start).total_seconds()
        if elapsed > locks.wait_timeout_seconds:
            return False, lock
        if not warned:
            logger.warning(
                "VM %s is locked (%s); waiting up to %s",
                vmid,
                lock,
                locks.wait_timeout_seconds,
                extra={"event": "vm_locked", "vmid": vmid, "lock": lock},
            )
            warned = True
        clock.sleep(locks.poll_interval_seconds)
        lock = client.vm_status_current(node, vmid).get("lock")
    return True, None


def _live_transient_check(
    client: PveClient,
    node: str,
    target: Storage,
    disk: Disk,
    min_free_bytes: int,
    existing_largest_bytes: int,
) -> bool:
    """Section 9.2 step 2, re-derived from a *live* ``storage_status()``
    call rather than the in-memory model ``schedule.transient_invariant_ok()``
    checks against -- the same section 8.1 formula
    (``used + z_d + max(f·max(Z,z_d), min_free) <= C``), but the model
    function's ``used`` comes from summing this tool's own disk list, and a
    live re-check specifically wants PVE's own authoritative current
    ``used`` instead, which already reflects anything else that touched the
    storage since planning. Not a second implementation of the *rule*,
    only of the *arithmetic*, against a data source the model-based
    function was never built to accept (AGENTS.md section 5)."""
    status = client.storage_status(node, target.id)
    live_used = int(status["used"])
    live_total = int(status["total"])
    required = max(
        round(target.reserve_factor * max(existing_largest_bytes, disk.size_bytes)), min_free_bytes
    )
    return live_used + disk.size_bytes + required <= live_total


def _detect_orphan_volumes(
    client: PveClient, node: str, storage_id: str, vmid: int
) -> tuple[str, ...]:
    """Section 9.4/domain rule 6: after a failed or cancelled mirror, a
    target volume can be left behind. Reported here, never deleted -- the
    operator removes it."""
    try:
        content = client.storage_content(node, storage_id)
        config = client.vm_config(node, vmid)
    except PveApiError as exc:
        logger.warning(
            "could not check %s for orphaned volumes after a failed move: %s",
            storage_id,
            exc,
            extra={"event": "orphan_check_failed", "storage": storage_id, "vmid": vmid},
        )
        return ()
    referenced = set()
    for key, value in config.items():
        if DISK_KEY_RE.match(key) and isinstance(value, str):
            ref_storage, volume_name, _params = parse_disk_spec(value)
            referenced.add(f"{ref_storage}:{volume_name}")
    return tuple(
        item["volid"]
        for item in content
        if item.get("vmid") == vmid and item.get("volid") not in referenced
    )


def _wait_for_move_completion(
    client: PveClient,
    node: str,
    vmid: int,
    upid: str,
    source: Storage,
    volid: str,
    execution: ExecutionConfig,
    clock: Clock,
) -> tuple[str, str]:
    """Section 9.3.2's three-condition completion criterion. Polls the
    task first (unbounded -- the plan says "poll ... until status ==
    'stopped'" with no separate timeout of its own; a move that was
    accepted at planning time already passed
    `migration.max_single_move_duration`), then, only if
    ``execution.source_release.wait`` and the source actually
    ``saferemove``s, polls for the source volume's disappearance and the
    VM's lock clearing together, bounded by
    ``execution.source_release.timeout``."""
    while True:
        task = client.task_status(node, upid)
        if task.get("status") == "stopped":
            break
        clock.sleep(execution.poll_interval_seconds)

    if task.get("exitstatus") != "OK":
        return "failed", f"move_disk task {upid} failed: {task.get('exitstatus')}"

    if not execution.source_release.wait or not source.saferemove:
        return "moved", f"task {upid} completed OK"

    start = clock.now()
    while True:
        content = client.storage_content(node, source.id)
        volume_present = any(item.get("volid") == volid for item in content)
        lock = client.vm_status_current(node, vmid).get("lock")
        if not volume_present and not lock:
            return "moved", f"task {upid} completed OK, source released"
        elapsed = (clock.now() - start).total_seconds()
        if elapsed > execution.source_release.timeout_seconds:
            return "draining", (
                f"task {upid} completed OK, but the source volume ({volid}) is still present "
                f"after {elapsed:.0f}s -- saferemove wipe likely still running (section 8.2 "
                "'draining'); the next run will see this storage as it actually is"
            )
        clock.sleep(execution.poll_interval_seconds)


def _execute_one_move(
    client: PveClient,
    disk: Disk,
    move: ScheduledMove,
    storages_by_id: dict[str, Storage],
    migration: MigrationConfig,
    execution: ExecutionConfig,
    min_free_bytes: int,
    largest_by_storage: dict[str, int],
    clock: Clock,
) -> MoveOutcome:
    def outcome(
        status: str,
        detail: str,
        upid: str | None = None,
        orphans: tuple[str, ...] = (),
        always_stop: bool = False,
    ) -> MoveOutcome:
        return MoveOutcome(
            move.disk_key,
            move.from_storage,
            move.to_storage,
            status,
            detail,
            upid,
            orphans,
            always_stop,
        )

    preflight = _preflight(client, disk, move)
    if preflight.mismatch is not None:
        return outcome("replan_needed", preflight.mismatch)
    assert (
        preflight.node is not None and preflight.volid is not None
    )  # guaranteed when mismatch is None

    if preflight.lock:
        cleared, last_lock = _wait_for_unlocked(
            client, preflight.node, disk.vmid, execution.locks, clock
        )
        if not cleared:
            detail = (
                f"VM {disk.vmid} still locked ({last_lock}) after "
                f"{execution.locks.wait_timeout_seconds:.0f}s"
            )
            if execution.locks.on_timeout == "abort":
                return outcome("failed", detail, always_stop=True)
            return outcome("skipped", detail)

    target = storages_by_id[move.to_storage]
    if not _live_transient_check(
        client, preflight.node, target, disk, min_free_bytes, largest_by_storage[move.to_storage]
    ):
        return outcome(
            "replan_needed",
            f"the section 8.1 transient invariant no longer holds for {target.id!r} "
            "against its live storage status",
        )

    upid = client.move_disk(
        preflight.node,
        disk.vmid,
        disk.device,
        move.to_storage,
        delete=True,
        bwlimit_bytes_per_sec=migration.bwlimit_bytes_per_sec,
    )
    source = storages_by_id[move.from_storage]
    status, detail = _wait_for_move_completion(
        client, preflight.node, disk.vmid, upid, source, preflight.volid, execution, clock
    )
    orphans: tuple[str, ...] = ()
    if status == "failed":
        orphans = _detect_orphan_volumes(client, preflight.node, move.to_storage, disk.vmid)
        if orphans:
            logger.warning(
                "orphaned volume(s) left on %s after a failed move: %s",
                move.to_storage,
                ", ".join(orphans),
                extra={"event": "orphaned_volumes", "storage": move.to_storage, "volumes": orphans},
            )
    return outcome(status, detail, upid, orphans)


def execute_plan(
    client: PveClient,
    group: Group,
    schedule_result: ScheduleResult,
    migration: MigrationConfig,
    execution: ExecutionConfig,
    min_free_bytes: int,
    mode: str,
    confirm: ConfirmCallback | None = None,
    clock: Clock = _REAL_CLOCK,
) -> ExecutionResult:
    """Execute (or, in ``dry-run``, merely report) one group's already
    -ordered plan. ``mode`` is ``"dry-run"``, ``"confirm"`` or ``"auto"``
    -- see the module docstring for what ``"auto"`` does and does not do
    here. ``confirm`` is required (and only ever called) in ``"confirm"``
    mode; ``cli.py`` owns the actual prompting.
    """
    disks_by_key = {d.key: d for d in group.disks}
    storages_by_id = {s.id: s for s in group.storages}
    # Section 8.1's "largest disk on the target" for the live transient
    # check, tracked as *this run's own* moves land -- a move earlier in
    # this same plan can already have changed a target's largest resident
    # disk before a later move checks the same storage.
    largest_by_storage = {s.id: largest_disk_bytes(group.disks, s.id) for s in group.storages}

    outcomes: list[MoveOutcome] = []
    auto_confirmed = mode != "confirm"
    for move in schedule_result.order:
        disk = disks_by_key[move.disk_key]

        if mode == "dry-run":
            outcomes.append(
                MoveOutcome(
                    move.disk_key,
                    move.from_storage,
                    move.to_storage,
                    "would_move",
                    "no changes made (dry-run)",
                )
            )
            continue

        if not auto_confirmed:
            decision = confirm(move) if confirm is not None else "n"
            if decision == "q":
                return ExecutionResult(tuple(outcomes), True, "operator quit")
            if decision == "a":
                auto_confirmed = True
            elif decision == "n":
                outcomes.append(
                    MoveOutcome(
                        move.disk_key,
                        move.from_storage,
                        move.to_storage,
                        "skipped",
                        "operator declined",
                    )
                )
                continue
            elif decision != "y":
                raise ValueError(f"confirm callback returned {decision!r}, expected y/n/a/q")

        result = _execute_one_move(
            client,
            disk,
            move,
            storages_by_id,
            migration,
            execution,
            min_free_bytes,
            largest_by_storage,
            clock,
        )
        outcomes.append(result)

        if result.status in ("moved", "draining"):
            # The mirror itself is done either way (the task reported OK) --
            # "draining" only means the *source* has not released yet, so
            # the target's own (C4) largest-disk accounting already needs
            # to include this disk for any later move's live transient
            # check against the same target.
            largest_by_storage[move.to_storage] = max(
                largest_by_storage[move.to_storage], disk.size_bytes
            )
        elif result.status == "replan_needed":
            return ExecutionResult(tuple(outcomes), True, result.detail)
        elif result.status == "failed" and (result.always_stop or execution.abort_on_failure):
            return ExecutionResult(
                tuple(outcomes), True, f"{move.disk_key} failed: {result.detail}"
            )

    return ExecutionResult(tuple(outcomes), False, None)
