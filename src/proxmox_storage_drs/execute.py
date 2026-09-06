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
**Still not enforced here**: the `max_concurrent_migrations`/
`max_concurrent_per_storage` caps -- every move remains strictly
sequential (one in flight at a time), which is trivially compliant with
either cap's *default* of `1` but not with a value above it; `cli.py`
refuses to start `auto` mode at all when either is configured above `1`,
rather than silently running sequentially against a cap that asked for
concurrency this module does not implement -- see
``docs/internals/92-execute.md``.

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
from datetime import datetime, timedelta, timezone
from typing import Callable, Mapping

from proxmox_storage_drs.config import ExcludeConfig, ExecutionConfig, LocksConfig, MigrationConfig
from proxmox_storage_drs.exceptions import PveApiError
from proxmox_storage_drs.payback import MoveCost
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
    `saferemove` wipe section 8.2 already models; ``execute_plan()``
    excludes that source as both source and target for every later move
    in the *same* run, per section 9.3), or ``"replan_needed"`` (a
    pre-flight or live transient-invariant mismatch -- the plan no longer
    matches reality).

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
            )

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
        f"{drained!r} is still draining a saferemove wipe from earlier in this run "
        "(section 9.3); re-evaluate on the next run",
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
    """
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
        migrations_used += 1

        stop_reason = _post_move_bookkeeping(
            result, move, disk, largest_by_storage, drained_storages, execution
        )
        if stop_reason is not None:
            return ExecutionResult(tuple(outcomes), True, stop_reason)

    return ExecutionResult(tuple(outcomes), False, None)
