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
like `[a]ll remaining` chosen up front, unprompted, and this module
enforces both of section 9.1's own per-move budgets for it -- refusing to
start (and stopping the run cleanly) a move that cannot finish before
``deadline``, or once ``max_migrations`` attempts have already been made
-- via the ``deadline``/``move_costs_by_key``/``max_migrations``
parameters `cli.py` supplies only in `auto` mode (section 12 phase 8).

**Concurrent execution** (`execution.max_concurrent_migrations`/
`max_concurrent_per_storage` above their default of `1`) is `auto`-only:
`execute_plan()` dispatches to `_execute_concurrent()` instead of the
strictly-sequential `_execute_sequential()` above either cap's default,
implementing section 8.1's generalized transient invariant
(`reserve.transient_charge_ok()`) and section 9.2's "poll all in-flight
UPIDs, launch the next queued move as each slot frees" loop -- see
`_execute_concurrent()`'s own docstring for exactly what it does and does
not do (strict-FIFO launching; no *execution-time* re-check of section
7.3's saturation ceiling against the live in-flight set, mirroring or
draining phase, under either executor -- the planning-time defer check
already excludes a flagged move from ever reaching here, see
`docs/internals/96-payback.md`). `dry-run`/`confirm` never use it,
matching section 9.1's own per-mode description, which discusses
concurrency only under `auto`.

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
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Callable, Mapping, Sequence

from proxmox_storage_drs.config import ExcludeConfig, ExecutionConfig, LocksConfig, MigrationConfig
from proxmox_storage_drs.exceptions import PveApiError
from proxmox_storage_drs.payback import MoveCost
from proxmox_storage_drs.pve import PveClient
from proxmox_storage_drs.reserve import largest_disk_bytes, transient_charge_ok
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
    `saferemove` wipe section 8.2 already models; ``execute_plan()``
    excludes that source as both source and target for every later move
    in the *same* run, per section 9.3), or ``"replan_needed"`` (a
    pre-flight or live transient-invariant mismatch -- the plan no longer
    matches reality).

    ``always_stop`` is set for a lock timeout with
    ``execution.locks.on_timeout: abort`` -- the manual's own words for that
    setting are "abort **the run**", a distinct, explicit per-config
    decision from ``execution.abort_on_failure``'s general "stop after any
    failed move" policy, which a plain `move_disk` task failure still goes
    through unmodified -- and for a ``"skipped"`` outcome from the
    post-lock-wait deadline re-check: both of `auto` mode's section 9.1
    budgets are `_auto_budget_stop_outcome()`'s own "stop cleanly, never
    skip this one and try a later move" (REVIEW.md T-06), which applies
    just as much to the budget going stale during a lock wait as to the
    pre-flight check that function itself makes."""

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

# Section 13 / 11.2's crash-recovery mechanism: `cli.py` supplies these so a
# UPID reaches `state.json` *before* the move it names can crash the engine,
# and is cleared once that task itself has finished -- see
# `crashrecovery.py`'s module docstring for the two failure modes this
# protects against, and `_execute_one_move()` below for exactly when each
# fires. `None` (the default, for `plan`/`show-load`'s own read-only paths
# and anything else that has no `state.json` to write) means "do nothing".
InflightCallback = Callable[[str], None]


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


def _is_excluded_by_tag_or_vmid(
    resource: dict[str, object], vmid: int, exclude: ExcludeConfig
) -> bool:
    """The vmid/tag half of `topology.py`'s own `_pin_reason()` exclusion
    predicate, duplicated rather than imported -- that name is private to
    that module, and every sibling in this codebase already prefers a
    small duplicate over reaching into another module's private names
    (AGENTS.md section 5; see `optimize.py`'s `_movable_disks()` for the
    same precedent). Only the vmid/tag half: section 9.2 step 3 says
    "untagged for exclusion", not the disk/storage exclusion lists, which
    a plan already accounts for by never proposing an excluded disk."""
    tags_raw = str(resource.get("tags", ""))
    tags = {t.strip() for t in tags_raw.replace(",", ";").split(";") if t.strip()}
    return vmid in set(exclude.vmids) or bool(tags & set(exclude.tags))


def _preflight(
    client: PveClient, disk: Disk, move: ScheduledMove, exclude: ExcludeConfig
) -> _PreflightResult:
    """Section 9.2's five re-checks, immediately before issuing one move.

    Re-fetches everything needed fresh -- the per-run topology cache
    (section 3.5) is deliberately bypassed here, since its whole point was
    to avoid re-fetching for *planning*, not to avoid re-validating right
    before a mutation."""
    resource = _vm_resource(client, disk.vmid)
    if resource is None:
        return _PreflightResult(f"VM {disk.vmid} no longer found in cluster resources")
    node = str(resource.get("node"))
    if _is_excluded_by_tag_or_vmid(resource, disk.vmid, exclude):
        return _PreflightResult(
            f"VM {disk.vmid} is now excluded (exclude.vmids or exclude.tags) since this plan "
            "was built"
        )

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


def _check_lock_once(client: PveClient, node: str, vmid: int) -> str | None:
    """The one live read behind section 9.3.1's lock check: the VM's
    current ``config.lock``, ``None`` when clear. Factored out so the
    sequential executor's blocking :func:`_wait_for_unlocked` and the
    concurrent executor's own non-blocking per-cycle check (below) share
    the identical read (AGENTS.md section 5) -- the concurrent case
    cannot block a whole poll cycle sleeping on one candidate's lock the
    way the sequential wait loop does, since other moves may be able to
    launch in the meantime."""
    return client.vm_status_current(node, vmid).get("lock")


def _wait_for_unlocked(
    client: PveClient, node: str, vmid: int, locks: LocksConfig, clock: Clock
) -> tuple[bool, str | None]:
    """Section 9.3.1: any non-empty ``lock`` means wait, never whitelist a
    value (`.agents/domain-invariants.md` rule 5). Returns ``(True, None)``
    once clear, or ``(False, last_seen_lock)`` on timeout. Sequential-mode
    only -- see the module docstring's "Concurrent execution" section for
    why the concurrent executor cannot reuse this blocking form."""
    start = clock.now()
    lock = _check_lock_once(client, node, vmid)
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
        lock = _check_lock_once(client, node, vmid)
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
    checks against, via the shared :func:`reserve.transient_charge_ok`
    (section 8.1's one arithmetic core, AGENTS.md section 5) -- the model
    function's ``used``/``total`` come from summing this tool's own disk
    list and ``Storage.capacity_bytes``, while a live re-check specifically
    wants PVE's own authoritative current ``used``/``total`` instead, which
    already reflects anything else that touched the storage since
    planning. Not a second implementation of the *rule*, only of the
    *data source* the model-based function was never built to accept."""
    status = client.storage_status(node, target.id)
    live_used = int(status["used"])
    live_total = int(status["total"])
    return transient_charge_ok(
        target.reserve_factor,
        live_total,
        live_used,
        existing_largest_bytes,
        [disk.size_bytes],
        min_free_bytes,
    )


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


@dataclass(frozen=True, slots=True)
class _MoveWaitState:
    """Carries :func:`_poll_move_once` state across non-blocking poll
    cycles -- the concurrent executor's per-in-flight-move counterpart to
    :func:`_wait_for_move_completion`'s own local ``start`` variable.
    ``drain_start`` is set the first cycle the source-release phase is
    entered (the task itself reported ``OK``, but the source has not
    released yet), so later cycles measure elapsed time from *that*
    instant, not from when polling of this move began."""

    drain_start: datetime | None = None


def _poll_move_once(
    client: PveClient,
    node: str,
    vmid: int,
    upid: str,
    source: Storage,
    volid: str,
    execution: ExecutionConfig,
    clock: Clock,
    wait_state: _MoveWaitState,
) -> tuple[tuple[str, str] | None, _MoveWaitState]:
    """One non-blocking step of section 9.3.2's three-condition completion
    criterion: ``(None, wait_state)`` while the move is still in progress
    (call again next cycle), or ``((status, detail), wait_state)`` once it
    has reached a terminal outcome (``"moved"``, ``"failed"`` or
    ``"draining"``). :func:`_wait_for_move_completion` is this function
    called in a tight loop until it stops returning ``None`` -- the one
    implementation of the criterion, shared by the sequential executor
    (via that blocking wrapper) and the concurrent executor (calling this
    directly, once per in-flight move per poll cycle, so waiting on one
    move's task or source-release never blocks progress on any other)."""
    task = client.task_status(node, upid)
    if task.get("status") != "stopped":
        return None, wait_state

    if task.get("exitstatus") != "OK":
        return ("failed", f"move_disk task {upid} failed: {task.get('exitstatus')}"), wait_state

    if not execution.source_release.wait or not source.saferemove:
        return ("moved", f"task {upid} completed OK"), wait_state

    drain_start = wait_state.drain_start or clock.now()
    content = client.storage_content(node, source.id)
    volume_present = any(item.get("volid") == volid for item in content)
    lock = _check_lock_once(client, node, vmid)
    if not volume_present and not lock:
        return ("moved", f"task {upid} completed OK, source released"), wait_state
    elapsed = (clock.now() - drain_start).total_seconds()
    if elapsed > execution.source_release.timeout_seconds:
        return (
            "draining",
            f"task {upid} completed OK, but the source volume ({volid}) is still present "
            f"after {elapsed:.0f}s -- saferemove wipe likely still running; the next run "
            "will see this storage as it actually is",
        ), wait_state
    return None, _MoveWaitState(drain_start=drain_start)


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
    """Section 9.3.2's three-condition completion criterion, blocking
    until it resolves. Polls the task first (unbounded -- the plan says
    "poll ... until status == 'stopped'" with no separate timeout of its
    own; a move that was accepted at planning time already passed
    `migration.max_single_move_duration`), then, only if
    ``execution.source_release.wait`` and the source actually
    ``saferemove``s, polls for the source volume's disappearance and the
    VM's lock clearing together, bounded by
    ``execution.source_release.timeout``. Sequential-mode only -- see
    :func:`_poll_move_once` for the non-blocking form the concurrent
    executor uses instead."""
    wait_state = _MoveWaitState()
    while True:
        result, wait_state = _poll_move_once(
            client, node, vmid, upid, source, volid, execution, clock, wait_state
        )
        if result is not None:
            return result
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
    exclude: ExcludeConfig,
    deadline: datetime | None,
    estimated_seconds: float,
    on_inflight_started: InflightCallback | None,
    on_inflight_finished: InflightCallback | None,
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

    preflight = _preflight(client, disk, move, exclude)
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
        # The lock wait can itself burn a large, unpredictable share of
        # `deadline`'s remaining budget (up to
        # `execution.locks.wait_timeout_seconds`, hours by default) --
        # `execute_plan()`'s own pre-loop check only knows the answer as
        # of *before* this wait, so it is re-checked here, right before
        # this function commits to actually issuing the move.
        if _deadline_exceeded(clock, deadline, estimated_seconds):
            return outcome(
                "skipped",
                "insufficient time remaining in execution.time_windows for this move "
                "after waiting for the VM lock to clear",
                always_stop=True,
            )

    target = storages_by_id[move.to_storage]
    if not _live_transient_check(
        client, preflight.node, target, disk, min_free_bytes, largest_by_storage[move.to_storage]
    ):
        return outcome(
            "replan_needed",
            f"{target.id!r} no longer has enough free space to safely hold this disk "
            "during the move, checked again just before starting",
        )

    upid = client.move_disk(
        preflight.node,
        disk.vmid,
        disk.device,
        move.to_storage,
        delete=True,
        bwlimit_bytes_per_sec=migration.bwlimit_bytes_per_sec,
    )
    # Section 11.2: written *before* this function does anything else with
    # `upid` -- if the engine crashes, is killed, or the host reboots
    # anywhere from here on, `state.json` already has a trace of this move
    # for the next startup's `crashrecovery.reconcile_inflight()` to find.
    if on_inflight_started is not None:
        on_inflight_started(upid)
    source = storages_by_id[move.from_storage]
    status, detail = _wait_for_move_completion(
        client, preflight.node, disk.vmid, upid, source, preflight.volid, execution, clock
    )
    # Deliberately *not* wrapped in try/finally: a "draining" source is
    # still tracked by its own content-listing poll, not by `upid` (see
    # `state.with_inflight_upid()`'s own docstring), so clearing it here
    # exactly once `_wait_for_move_completion()` returns -- for any status
    # -- is correct either way. If a call inside that wait itself raises
    # (a network failure mid-poll, say) this callback never fires and
    # `upid` stays recorded, which is exactly what section 13 wants: the
    # move might still be running, so the next startup's scan must still
    # find it.
    if on_inflight_finished is not None:
        on_inflight_finished(upid)
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


def _confirm_decision(
    move: ScheduledMove, confirm: ConfirmCallback | None
) -> tuple[str, MoveOutcome | None]:
    """Resolves one ``confirm`` callback answer to ``("quit", None)``,
    ``("all", None)``, ``("proceed", None)`` or ``("skip", outcome)`` --
    factored out of `execute_plan()`'s own loop purely to stay within
    this project's flake8 complexity limit. Raises ``ValueError`` on
    anything outside ``y``/``n``/``a``/``q``, exactly as before this was
    extracted -- `cli._confirm_move_interactively()` never produces one,
    since it retries bad input itself."""
    decision = confirm(move) if confirm is not None else "n"
    if decision == "q":
        return "quit", None
    if decision == "a":
        return "all", None
    if decision == "n":
        return "skip", MoveOutcome(
            move.disk_key, move.from_storage, move.to_storage, "skipped", "operator declined"
        )
    if decision == "y":
        return "proceed", None
    raise ValueError(f"confirm callback returned {decision!r}, expected y/n/a/q")


def _estimated_duration_seconds(
    move: ScheduledMove, move_costs_by_key: Mapping[str, MoveCost] | None
) -> float:
    """``payback.MoveCost``'s own mirror-plus-wipe estimate for ``move``
    -- the same one the hard per-move duration rule uses -- or ``0.0``
    when ``move`` has no entry, so a missing estimate never refuses a
    move for lack of one."""
    move_cost = (move_costs_by_key or {}).get(move.disk_key)
    if move_cost is None:
        return 0.0
    return move_cost.duration_mirror_seconds + move_cost.duration_wipe_seconds


def _deadline_exceeded(clock: Clock, deadline: datetime | None, estimated_seconds: float) -> bool:
    """``False`` whenever ``deadline`` is ``None`` (no time-window
    restriction at all). The one implementation of "does this much more
    time still fit," shared by the pre-loop check in `execute_plan()`
    and the post-lock-wait re-check in `_execute_one_move()` (AGENTS.md
    section 5)."""
    if deadline is None:
        return False
    return clock.now() + timedelta(seconds=estimated_seconds) > deadline


def _auto_budget_stop_outcome(
    move: ScheduledMove,
    clock: Clock,
    deadline: datetime | None,
    estimated_seconds: float,
    migrations_used: int,
    max_migrations: int | None,
) -> MoveOutcome | None:
    """``None`` when ``move`` may proceed; otherwise the ``"skipped"``
    outcome to report right before `execute_plan()` stops the *whole*
    run. Both of `auto` mode's section 9.1 budgets are "stop cleanly",
    never "skip this one and try a later move": remaining time only ever
    decreases as a run goes on, and a migration cap already reached stays
    reached, so nothing later in ``order`` could fit either. Checked in
    this order (the cap first) only because it is the cheaper check, not
    because one takes priority when both apply.

    This is the *pre-flight* time-window check, run before even a
    network call is made for this move -- `_execute_one_move()` repeats
    the deadline half of it again after a VM-lock wait (which can itself
    burn hours of the same budget) succeeds, since the answer here can
    no longer be trusted by then."""
    if max_migrations is not None and migrations_used >= max_migrations:
        return MoveOutcome(
            move.disk_key,
            move.from_storage,
            move.to_storage,
            "skipped",
            f"execution.max_migrations_per_run ({max_migrations}) reached for this invocation",
        )
    if _deadline_exceeded(clock, deadline, estimated_seconds):
        return MoveOutcome(
            move.disk_key,
            move.from_storage,
            move.to_storage,
            "skipped",
            "insufficient time remaining in execution.time_windows for this move "
            f"(needs ~{estimated_seconds:.0f}s more)",
        )
    return None


def _drained_skip_outcome(move: ScheduledMove, drained_storages: set[str]) -> MoveOutcome | None:
    """``None`` when neither of ``move``'s storages is draining this run;
    otherwise the ``"skipped"`` outcome for it -- factored out of
    `execute_plan()`'s own loop purely to stay within this project's
    flake8 complexity limit (the same reason `optimize.py`'s constraint
    builders are factored out)."""
    if move.from_storage not in drained_storages and move.to_storage not in drained_storages:
        return None
    drained = move.from_storage if move.from_storage in drained_storages else move.to_storage
    return MoveOutcome(
        move.disk_key,
        move.from_storage,
        move.to_storage,
        "skipped",
        f"{drained!r} is still draining a saferemove wipe from earlier in this run; "
        "re-evaluate on the next run",
    )


def _post_move_bookkeeping(
    result: MoveOutcome,
    move: ScheduledMove,
    disk: Disk,
    largest_by_storage: dict[str, int],
    drained_storages: set[str],
    execution: ExecutionConfig,
) -> str | None:
    """Updates this run's own (C4) largest-disk tracking and drained
    -storage exclusion after one move's outcome, returning a stop reason
    when the run must end here (a `"replan_needed"` mismatch, or a
    `"failed"` move that must stop it) or ``None`` to continue --
    factored out of `execute_plan()`'s own loop purely to stay within
    this project's flake8 complexity limit."""
    if result.status in ("moved", "draining"):
        # The mirror itself is done either way (the task reported OK) --
        # "draining" only means the *source* has not released yet, so
        # the target's own (C4) largest-disk accounting already needs to
        # include this disk for any later move's live transient check
        # against the same target.
        largest_by_storage[move.to_storage] = max(
            largest_by_storage[move.to_storage], disk.size_bytes
        )
        if result.status == "draining":
            drained_storages.add(move.from_storage)
        return None
    if result.status == "replan_needed":
        return result.detail
    if result.status == "failed" and (result.always_stop or execution.abort_on_failure):
        return f"{move.disk_key} failed: {result.detail}"
    if result.status == "skipped" and result.always_stop:
        # The post-lock-wait deadline re-check (REVIEW.md T-06) -- the
        # same "stop cleanly" policy `_auto_budget_stop_outcome()` already
        # documents for both of section 9.1's budgets, now honoured here
        # too rather than falling through to the next move in `order`.
        return result.detail
    return None


def execute_plan(
    client: PveClient,
    group: Group,
    schedule_result: ScheduleResult,
    migration: MigrationConfig,
    execution: ExecutionConfig,
    min_free_bytes: int,
    mode: str,
    exclude: ExcludeConfig,
    confirm: ConfirmCallback | None = None,
    clock: Clock = _REAL_CLOCK,
    deadline: datetime | None = None,
    move_costs_by_key: Mapping[str, MoveCost] | None = None,
    max_migrations: int | None = None,
    on_inflight_started: InflightCallback | None = None,
    on_inflight_finished: InflightCallback | None = None,
) -> ExecutionResult:
    """Execute (or, in ``dry-run``, merely report) one group's already
    -ordered plan. ``mode`` is ``"dry-run"``, ``"confirm"`` or ``"auto"``
    -- see the module docstring for what ``"auto"`` does and does not do
    here. ``confirm`` is required (and only ever called) in ``"confirm"``
    mode; ``cli.py`` owns the actual prompting. ``exclude`` is
    ``config.exclude`` -- section 9.2 step 3's "confirm the VM is still
    running and untagged for exclusion" re-check (REVIEW.md S-06), the
    same vmid/tag predicate `topology.py`'s own (C2) pin already applies
    at planning time.

    ``deadline``/``move_costs_by_key``/``max_migrations`` are ``auto``
    mode's own section 9.1 requirements ("refuse to start a move that
    cannot finish inside the remaining time window... honour
    `max_migrations_per_run`") -- ``cli.py`` is what only ever passes
    non-``None`` values for these in ``auto`` mode; left ``None`` (the
    default) for ``dry-run``/``confirm``, both checks are simply
    inactive. ``deadline`` is an absolute instant (typically derived from
    `timewindow.current_deadline()`) compared against ``clock.now()``,
    never wall-clock time read directly, so it is exercised by the same
    fake clock every other wait loop here uses. ``move_costs_by_key``
    supplies each move's estimated `duration_mirror_seconds +
    duration_wipe_seconds` (`payback.MoveCost`, the same estimate the
    hard per-move duration rule uses) for that check; a move missing from
    it is assumed to take no time at all, never refused for lack of an
    estimate.

    ``on_inflight_started``/``on_inflight_finished`` are section 13's
    crash-recovery hooks (see ``crashrecovery.py``'s module docstring):
    `cli.py` is the only caller that ever supplies them (`plan`/`show-load`
    have no `state.json` write path to hook into at all), and they are the
    *only* place in this module that reaches back out to a caller-owned
    mutable side effect rather than returning a value -- a deliberate,
    narrow exception to this codebase's otherwise-pure functional state
    -threading (see ``docs/internals/92-execute.md``), forced by the fact
    that persisting `state.json` only at the end of a whole `execute_plan()`
    call would never survive the exact crash section 13 exists to recover
    from.

    Dispatches to :func:`_execute_concurrent` only in ``"auto"`` mode with
    either concurrency cap configured above its default of `1` -- see that
    function's own docstring for why concurrency is `auto`-only, and
    :func:`_execute_sequential` (everything else, including `auto` at the
    default caps) for the strictly-sequential form this module has always
    used.
    """
    if mode == "auto" and (
        execution.max_concurrent_migrations > 1 or execution.max_concurrent_per_storage > 1
    ):
        return _execute_concurrent(
            client,
            group,
            schedule_result,
            migration,
            execution,
            min_free_bytes,
            exclude,
            clock,
            deadline,
            move_costs_by_key,
            max_migrations,
            on_inflight_started,
            on_inflight_finished,
        )
    return _execute_sequential(
        client,
        group,
        schedule_result,
        migration,
        execution,
        min_free_bytes,
        mode,
        exclude,
        confirm,
        clock,
        deadline,
        move_costs_by_key,
        max_migrations,
        on_inflight_started,
        on_inflight_finished,
    )


def _execute_sequential(
    client: PveClient,
    group: Group,
    schedule_result: ScheduleResult,
    migration: MigrationConfig,
    execution: ExecutionConfig,
    min_free_bytes: int,
    mode: str,
    exclude: ExcludeConfig,
    confirm: ConfirmCallback | None,
    clock: Clock,
    deadline: datetime | None,
    move_costs_by_key: Mapping[str, MoveCost] | None,
    max_migrations: int | None,
    on_inflight_started: InflightCallback | None,
    on_inflight_finished: InflightCallback | None,
) -> ExecutionResult:
    """`execute_plan()`'s original, strictly-sequential loop (one move in
    flight at a time) -- ``dry-run``, ``confirm``, and ``auto`` at the
    default concurrency caps all use this. See :func:`_execute_concurrent`
    for the `auto`-only alternative used above either cap's default."""
    disks_by_key = {d.key: d for d in group.disks}
    storages_by_id = {s.id: s for s in group.storages}
    # Section 8.1's "largest disk on the target" for the live transient
    # check, tracked as *this run's own* moves land -- a move earlier in
    # this same plan can already have changed a target's largest resident
    # disk before a later move checks the same storage.
    largest_by_storage = {s.id: largest_disk_bytes(group.disks, s.id) for s in group.storages}

    outcomes: list[MoveOutcome] = []
    # Section 9.3: a `source_release.timeout` "does not fail the run:
    # mark the storage draining, exclude it as both source and target for
    # the remainder of the run" (REVIEW.md S-05 -- an earlier revision
    # tracked the largest-disk accounting for a draining target (above)
    # but never actually excluded the storage from later moves in the
    # same run). The storage that goes here is the *source* of a
    # `"draining"` outcome -- the wipe holding a storage-level lock runs
    # there, per section 9.3's own account of what makes a subsequent
    # `move_disk` touching that storage fail.
    drained_storages: set[str] = set()
    auto_confirmed = mode != "confirm"
    migrations_used = 0
    for move in schedule_result.order:
        disk = disks_by_key[move.disk_key]

        drained_skip = _drained_skip_outcome(move, drained_storages)
        if drained_skip is not None:
            outcomes.append(drained_skip)
            continue

        estimated_seconds = _estimated_duration_seconds(move, move_costs_by_key)
        budget_stop = _auto_budget_stop_outcome(
            move, clock, deadline, estimated_seconds, migrations_used, max_migrations
        )
        if budget_stop is not None:
            outcomes.append(budget_stop)
            return ExecutionResult(tuple(outcomes), True, budget_stop.detail)

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
            verdict, skip_outcome = _confirm_decision(move, confirm)
            if verdict == "quit":
                return ExecutionResult(tuple(outcomes), True, "operator quit")
            if verdict == "all":
                auto_confirmed = True
            elif verdict == "skip":
                assert skip_outcome is not None
                outcomes.append(skip_outcome)
                continue

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
            exclude,
            deadline,
            estimated_seconds,
            on_inflight_started,
            on_inflight_finished,
        )
        outcomes.append(result)
        if result.upid is not None:
            # Launches only (REVIEW.md T-06), matching the concurrent
            # executor (`_advance_pending()` only ever increments its own
            # counter at the point it actually issues `move_disk`) -- a
            # lock-timeout or post-lock-wait-deadline `"skipped"` outcome
            # (`result.upid` is only ever set once `move_disk` returned)
            # never issued one, so it must not consume a slot of
            # `execution.max_migrations_per_run`.
            migrations_used += 1

        stop_reason = _post_move_bookkeeping(
            result, move, disk, largest_by_storage, drained_storages, execution
        )
        if stop_reason is not None:
            return ExecutionResult(tuple(outcomes), True, stop_reason)

    return ExecutionResult(tuple(outcomes), False, None)


# --------------------------------------------------------- concurrent execution
#
# `auto` mode only, and only once `execution.max_concurrent_migrations`/
# `max_concurrent_per_storage` is configured above its default of `1` (see
# `execute_plan()`'s own dispatch). Every helper below exists because a
# concurrent executor cannot use `_wait_for_unlocked()`/
# `_wait_for_move_completion()`'s blocking loops directly: blocking on one
# move's lock or completion would stall every *other* in-flight or
# candidate move for as long as that wait lasts, defeating the entire
# point of concurrency. `_poll_move_once()` (above) already provides the
# non-blocking form of the completion criterion; this section adds the
# non-blocking form of the lock wait (`_LockWaitTracker`/`_launch_decision`)
# and the orchestration loop itself.


@dataclass(frozen=True, slots=True)
class _InflightMove:
    """One concurrently-executing move's own state, carried across poll
    cycles -- the concurrent executor's counterpart to
    `_execute_one_move()`'s single local call stack. There is no call
    stack per move here, since nothing blocks waiting for one move before
    moving on to the next, so every in-flight move's progress
    (`wait_state`) has to be threaded explicitly instead."""

    move: ScheduledMove
    disk: Disk
    node: str
    upid: str
    source: Storage
    target: Storage
    volid: str
    wait_state: _MoveWaitState = _MoveWaitState()


def _per_storage_inflight_counts(inflight: Sequence[_InflightMove]) -> dict[str, int]:
    """Section 8.1 point 3: how many in-flight moves currently touch each
    storage as *either* source or target -- what
    `execution.max_concurrent_per_storage` ceilings."""
    counts: dict[str, int] = {}
    for im in inflight:
        counts[im.move.from_storage] = counts.get(im.move.from_storage, 0) + 1
        counts[im.move.to_storage] = counts.get(im.move.to_storage, 0) + 1
    return counts


def _target_charges(inflight: Sequence[_InflightMove], storage_id: str) -> list[int]:
    """Every in-flight move's ``z_m`` whose *target* is ``storage_id`` --
    the ``charge_sizes_bytes`` :func:`reserve.transient_charge_ok` needs
    to account for moves this run has already launched onto the same
    storage (see that function's own docstring for why this does not try
    to guess whether a live ``used`` read already reflects them)."""
    return [im.disk.size_bytes for im in inflight if im.move.to_storage == storage_id]


def _poll_inflight_once(
    client: PveClient,
    inflight: Sequence[_InflightMove],
    execution: ExecutionConfig,
    clock: Clock,
    largest_by_storage: dict[str, int],
    drained_storages: set[str],
    on_inflight_finished: InflightCallback | None,
) -> tuple[list[_InflightMove], list[MoveOutcome], str | None]:
    """One poll cycle across every currently in-flight move -- the
    concurrent counterpart to `_execute_one_move()`'s single blocking
    `_wait_for_move_completion()` call, via `_poll_move_once()` (AGENTS.md
    section 5: the identical per-move completion criterion, called once
    per in-flight move per cycle here instead of once, blocking, per
    move). Returns the still-in-flight subset, any outcomes newly
    resolved this cycle (in resolution order, each already run through
    `_post_move_bookkeeping()` for the (C4) largest-disk/drained-storage
    side effects), and a stop reason if one of them requires the run to
    stop launching further moves (only a `"failed"` move needing
    `execution.abort_on_failure`/`always_stop` can set this --
    `"replan_needed"` is only ever produced at launch time, by
    `_launch_decision()` below, never by polling an already-launched
    move)."""
    still_inflight: list[_InflightMove] = []
    resolved: list[MoveOutcome] = []
    stop_reason: str | None = None
    for im in inflight:
        result, wait_state = _poll_move_once(
            client,
            im.node,
            im.disk.vmid,
            im.upid,
            im.source,
            im.volid,
            execution,
            clock,
            im.wait_state,
        )
        if result is None:
            still_inflight.append(replace(im, wait_state=wait_state))
            continue
        status, detail = result
        if on_inflight_finished is not None:
            on_inflight_finished(im.upid)
        orphans: tuple[str, ...] = ()
        if status == "failed":
            orphans = _detect_orphan_volumes(client, im.node, im.move.to_storage, im.disk.vmid)
            if orphans:
                logger.warning(
                    "orphaned volume(s) left on %s after a failed move: %s",
                    im.move.to_storage,
                    ", ".join(orphans),
                    extra={
                        "event": "orphaned_volumes",
                        "storage": im.move.to_storage,
                        "volumes": orphans,
                    },
                )
        outcome = MoveOutcome(
            im.move.disk_key,
            im.move.from_storage,
            im.move.to_storage,
            status,
            detail,
            im.upid,
            orphans,
        )
        resolved.append(outcome)
        reason = _post_move_bookkeeping(
            outcome, im.move, im.disk, largest_by_storage, drained_storages, execution
        )
        if reason is not None and stop_reason is None:
            stop_reason = reason
    return still_inflight, resolved, stop_reason


@dataclass(frozen=True, slots=True)
class _LockWaitTracker:
    """Tracks how long the *current* head of ``pending`` has been seen
    locked, across poll cycles -- the non-blocking counterpart to
    `_wait_for_unlocked()`'s local ``start``/``warned`` variables. Strict
    -FIFO launching (see `_execute_concurrent()`'s own docstring) means
    there is only ever one candidate to track this for at a time, reset
    to a fresh, empty tracker by the caller whenever the head of
    ``pending`` changes for any reason."""

    start: datetime | None = None
    warned: bool = False


@dataclass(frozen=True, slots=True)
class _LaunchDecision:
    """:func:`_launch_decision`'s result. ``verdict`` is one of:

    - ``"wait"`` -- not launchable yet (a per-storage cap is saturated,
      or the VM is locked and has not timed out); try again next cycle
      with the same candidate still at the head of ``pending``.
      ``lock_wait`` carries the tracker state to resume from.
    - ``"launch"`` -- clear to launch; ``preflight`` is the resolved
      pre-flight result (`node`/`volid`) the caller needs to actually
      issue `move_disk` (this function makes no mutating API calls
      itself).
    - ``"resolved"`` -- the head of ``pending`` is done *without* ever
      launching (a pre-flight mismatch, a lock timeout, or the section
      8.1 transient invariant failing live); ``outcome`` is what the
      caller should record before popping it.
    """

    verdict: str
    outcome: MoveOutcome | None = None
    preflight: _PreflightResult | None = None
    lock_wait: _LockWaitTracker = _LockWaitTracker()


def _launch_lock_decision(
    candidate: ScheduledMove,
    disk: Disk,
    lock: str,
    locks: LocksConfig,
    clock: Clock,
    lock_wait: _LockWaitTracker,
) -> _LaunchDecision:
    """The non-blocking counterpart to `_wait_for_unlocked()`'s loop body,
    for one poll cycle. Factored out of :func:`_launch_decision` purely to
    stay within this project's flake8 complexity limit."""
    start = lock_wait.start or clock.now()
    elapsed = (clock.now() - start).total_seconds()
    if elapsed > locks.wait_timeout_seconds:
        detail = f"VM {disk.vmid} still locked ({lock}) after {locks.wait_timeout_seconds:.0f}s"
        always_stop = locks.on_timeout == "abort"
        outcome = MoveOutcome(
            candidate.disk_key,
            candidate.from_storage,
            candidate.to_storage,
            "failed" if always_stop else "skipped",
            detail,
            always_stop=always_stop,
        )
        return _LaunchDecision("resolved", outcome=outcome)
    if not lock_wait.warned:
        logger.warning(
            "VM %s is locked (%s); waiting up to %s",
            disk.vmid,
            lock,
            locks.wait_timeout_seconds,
            extra={"event": "vm_locked", "vmid": disk.vmid, "lock": lock},
        )
    return _LaunchDecision("wait", lock_wait=_LockWaitTracker(start=start, warned=True))


def _launch_decision(
    client: PveClient,
    candidate: ScheduledMove,
    disk: Disk,
    storages_by_id: dict[str, Storage],
    execution: ExecutionConfig,
    min_free_bytes: int,
    largest_by_storage: dict[str, int],
    exclude: ExcludeConfig,
    inflight: Sequence[_InflightMove],
    clock: Clock,
    lock_wait: _LockWaitTracker,
) -> _LaunchDecision:
    """Section 9.2's five pre-flight re-checks plus section 8.1's
    generalized transient invariant, for one candidate, one poll cycle,
    without ever blocking. See :class:`_LaunchDecision` for the three
    possible verdicts."""
    per_storage = _per_storage_inflight_counts(inflight)
    if (
        per_storage.get(candidate.from_storage, 0) >= execution.max_concurrent_per_storage
        or per_storage.get(candidate.to_storage, 0) >= execution.max_concurrent_per_storage
    ):
        return _LaunchDecision("wait", lock_wait=lock_wait)

    preflight = _preflight(client, disk, candidate, exclude)
    if preflight.mismatch is not None:
        outcome = MoveOutcome(
            candidate.disk_key,
            candidate.from_storage,
            candidate.to_storage,
            "replan_needed",
            preflight.mismatch,
        )
        return _LaunchDecision("resolved", outcome=outcome)
    assert (
        preflight.node is not None and preflight.volid is not None
    )  # guaranteed when mismatch is None

    if preflight.lock:
        return _launch_lock_decision(
            candidate, disk, preflight.lock, execution.locks, clock, lock_wait
        )

    target = storages_by_id[candidate.to_storage]
    status = client.storage_status(preflight.node, target.id)
    charges = _target_charges(inflight, target.id) + [disk.size_bytes]
    if not transient_charge_ok(
        target.reserve_factor,
        int(status["total"]),
        int(status["used"]),
        largest_by_storage[target.id],
        charges,
        min_free_bytes,
    ):
        outcome = MoveOutcome(
            candidate.disk_key,
            candidate.from_storage,
            candidate.to_storage,
            "replan_needed",
            f"{target.id!r} no longer has enough free space to safely hold this disk "
            "during the move, checked again just before starting",
        )
        return _LaunchDecision("resolved", outcome=outcome)

    return _LaunchDecision("launch", preflight=preflight)


def _advance_pending(
    client: PveClient,
    pending: list[ScheduledMove],
    outcomes: list[MoveOutcome],
    inflight: list[_InflightMove],
    disks_by_key: dict[str, Disk],
    storages_by_id: dict[str, Storage],
    migration: MigrationConfig,
    execution: ExecutionConfig,
    min_free_bytes: int,
    largest_by_storage: dict[str, int],
    drained_storages: set[str],
    exclude: ExcludeConfig,
    clock: Clock,
    lock_wait: _LockWaitTracker,
    deadline: datetime | None,
    move_costs_by_key: Mapping[str, MoveCost] | None,
    migrations_used: int,
    max_migrations: int | None,
    on_inflight_started: InflightCallback | None,
) -> tuple[_LockWaitTracker, int, str | None]:
    """One poll cycle's attempt to move ``pending[0]`` forward -- mutates
    ``pending``/``outcomes``/``inflight`` in place (the same style
    `_post_move_bookkeeping()` already uses for ``largest_by_storage``/
    ``drained_storages``) and returns the (possibly reset)
    :class:`_LockWaitTracker`, the updated ``migrations_used`` count, and
    a stop reason if this cycle's outcome requires one. Does nothing
    (returns its inputs unchanged) when ``pending`` is empty or every
    concurrency slot is already full. Factored out of
    `_execute_concurrent()`'s own loop purely to stay within this
    project's flake8 complexity limit."""
    if not pending:
        return lock_wait, migrations_used, None

    candidate = pending[0]
    disk = disks_by_key[candidate.disk_key]

    drained_skip = _drained_skip_outcome(candidate, drained_storages)
    if drained_skip is not None:
        outcomes.append(drained_skip)
        pending.pop(0)
        return _LockWaitTracker(), migrations_used, None

    estimated_seconds = _estimated_duration_seconds(candidate, move_costs_by_key)
    budget_stop = _auto_budget_stop_outcome(
        candidate, clock, deadline, estimated_seconds, migrations_used, max_migrations
    )
    if budget_stop is not None:
        outcomes.append(budget_stop)
        pending.pop(0)
        return _LockWaitTracker(), migrations_used, budget_stop.detail

    if len(inflight) >= execution.max_concurrent_migrations:
        return lock_wait, migrations_used, None

    decision = _launch_decision(
        client,
        candidate,
        disk,
        storages_by_id,
        execution,
        min_free_bytes,
        largest_by_storage,
        exclude,
        inflight,
        clock,
        lock_wait,
    )
    if decision.verdict == "wait":
        return decision.lock_wait, migrations_used, None

    if decision.verdict == "launch":
        assert decision.preflight is not None
        pf = decision.preflight
        assert pf.node is not None and pf.volid is not None
        upid = client.move_disk(
            pf.node,
            disk.vmid,
            disk.device,
            candidate.to_storage,
            delete=True,
            bwlimit_bytes_per_sec=migration.bwlimit_bytes_per_sec,
        )
        # Section 11.2: recorded before this function does anything else
        # with `upid`, exactly as `_execute_one_move()` does -- see that
        # function's own comment on why.
        if on_inflight_started is not None:
            on_inflight_started(upid)
        inflight.append(
            _InflightMove(
                move=candidate,
                disk=disk,
                node=pf.node,
                upid=upid,
                source=storages_by_id[candidate.from_storage],
                target=storages_by_id[candidate.to_storage],
                volid=pf.volid,
            )
        )
        pending.pop(0)
        return _LockWaitTracker(), migrations_used + 1, None

    assert decision.verdict == "resolved" and decision.outcome is not None
    outcomes.append(decision.outcome)
    pending.pop(0)
    stop_reason = _post_move_bookkeeping(
        decision.outcome, candidate, disk, largest_by_storage, drained_storages, execution
    )
    return _LockWaitTracker(), migrations_used, stop_reason


def _execute_concurrent(
    client: PveClient,
    group: Group,
    schedule_result: ScheduleResult,
    migration: MigrationConfig,
    execution: ExecutionConfig,
    min_free_bytes: int,
    exclude: ExcludeConfig,
    clock: Clock,
    deadline: datetime | None,
    move_costs_by_key: Mapping[str, MoveCost] | None,
    max_migrations: int | None,
    on_inflight_started: InflightCallback | None,
    on_inflight_finished: InflightCallback | None,
) -> ExecutionResult:
    """``auto`` mode's concurrent orchestration -- section 8.1's
    generalized transient invariant and section 9.2's "poll all in-flight
    UPIDs, launch the next queued move as each slot frees" loop. Used
    only once `execution.max_concurrent_migrations`/
    `max_concurrent_per_storage` is configured above its default of `1`
    (see `execute_plan()`'s own dispatch); every other case uses
    `_execute_sequential()` unchanged.

    **Strict FIFO, deliberately.** This launches at most ``pending[0]`` at
    a time -- it never skips ahead to a later candidate
    `schedule.order_moves()` placed behind one that cannot launch yet.
    Several moves genuinely run concurrently once launched (every
    in-flight move is polled each cycle via `_poll_move_once()`, and
    nothing ever blocks on one move's own completion or lock wait), but
    the *decision of which move to launch next* stays exactly the order
    the scheduler already computed. A more sophisticated scheduler could
    reorder around a blocked head to keep every concurrency slot busy;
    this one instead waits for the head to become launchable (or resolve
    without launching) before considering anything after it -- simpler to
    reason about and to test exhaustively, and, like `schedule.py`'s own
    documented ordering-priority-2/staging gaps, this can only ever
    under-deliver on throughput, never produce an unsafe launch order.

    **Section 7.3's saturation check is planning-time only, here as under
    the sequential executor.** The defer check itself is enforced (a
    flagged move is excluded from `schedule_result.order` before either
    executor ever sees it, see `docs/internals/96-payback.md`); what
    neither executor does is re-check the ceiling *during* execution
    against the live in-flight set, so section 8.1 point 4 of
    `concurrency_ok` (summing `ω_role` over everything actually in
    flight right now, mirroring or draining) stays a documented gap.

    See `execute_plan()`'s own docstring for every parameter; this
    function implements the identical contract (budgets, drained-storage
    exclusion, crash-recovery callbacks) for the concurrent case. Unlike
    `_execute_sequential()`, a stop condition here does not return
    immediately: other moves may already be in flight, and their
    outcomes/crash-recovery callbacks must still be recorded, so this
    function keeps polling (never launching anything new) until every
    in-flight move has resolved before returning.
    """
    disks_by_key = {d.key: d for d in group.disks}
    storages_by_id = {s.id: s for s in group.storages}
    largest_by_storage = {s.id: largest_disk_bytes(group.disks, s.id) for s in group.storages}

    outcomes: list[MoveOutcome] = []
    drained_storages: set[str] = set()
    inflight: list[_InflightMove] = []
    pending = list(schedule_result.order)
    migrations_used = 0
    stop_reason: str | None = None
    lock_wait = _LockWaitTracker()

    while pending or inflight:
        still_inflight, resolved, poll_stop = _poll_inflight_once(
            client,
            inflight,
            execution,
            clock,
            largest_by_storage,
            drained_storages,
            on_inflight_finished,
        )
        inflight = still_inflight
        outcomes.extend(resolved)
        if poll_stop is not None and stop_reason is None:
            stop_reason = poll_stop

        pending_len_before = len(pending)
        if stop_reason is None:
            lock_wait, migrations_used, advance_stop = _advance_pending(
                client,
                pending,
                outcomes,
                inflight,
                disks_by_key,
                storages_by_id,
                migration,
                execution,
                min_free_bytes,
                largest_by_storage,
                drained_storages,
                exclude,
                clock,
                lock_wait,
                deadline,
                move_costs_by_key,
                migrations_used,
                max_migrations,
                on_inflight_started,
            )
            if advance_stop is not None:
                stop_reason = advance_stop

        if not inflight and (not pending or stop_reason is not None):
            # Nothing left to poll, and either nothing left to launch
            # either, or a stop condition means we never will again --
            # once `stop_reason` is set, `_advance_pending()` is never
            # called again (the `if stop_reason is None:` guard above), so
            # a non-empty `pending` would otherwise never shrink and this
            # loop would spin forever waiting for it to. Those remaining
            # candidates are simply abandoned, unreported -- exactly what
            # `_execute_sequential()`'s own early `return` already does
            # for every move after the one that triggered a stop.
            break
        if resolved or len(pending) < pending_len_before:
            continue  # progress was made this cycle -- try again immediately
        clock.sleep(execution.poll_interval_seconds)

    return ExecutionResult(tuple(outcomes), stop_reason is not None, stop_reason)
