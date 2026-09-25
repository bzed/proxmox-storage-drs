# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Execute an already-scheduled plan. See IMPLEMENTATION_PLAN.md section 9.

``execute_plan()`` walks one group's ``schedule.ScheduleResult.order`` and,
for each move, re-validates it against the *live* cluster immediately
before issuing it (section 9.2: never trust the plan alone -- the VM may
have moved node, the disk may no longer be on the expected source, a
snapshot may have appeared, an operator may have queued a pending config
change on the very disk about to move -- section 3.8), waits out any VM
config lock rather than
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
not do (strict-FIFO launching). `dry-run`/`confirm` never use it,
matching section 9.1's own per-mode description, which discusses
concurrency only under `auto`.

A move never gets a second chance to "fix" the plan around it: any
pre-flight mismatch, or a live transient-invariant check that no longer
holds, stops the run with ``status="replan_needed"`` rather than adjusting
anything (section 9.2's re-plan protocol: "abandon the remaining moves...
do not attempt to patch it"). The one exception is a check the executor
could not *make* -- the PVE API erroring while it re-reads the VM or the
target, or a target volume of unknowable size: that is not a mismatch
re-planning can cure, so it is a ``"failed"`` outcome with ``abort_run`` set
and the whole run ends non-zero (:func:`_pre_move_refusal`). **This module
does not itself re-invoke the
whole pipeline** (gates/solve/payback/order) the way section 9.2's re-plan
protocol's steps 3-5 describe -- that needs `cli.py`-level orchestration
across multiple `execute_plan()` calls, which is a real, separately-scoped
piece of work, not implemented here; see ``docs/internals/92-execute.md``.

Orphaned target volumes (section 9.4, domain rule 6) are detected after a
failed move and reported in that move's own outcome -- **never deleted**.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping, Sequence

from proxmox_storage_drs.config import ExcludeConfig, ExecutionConfig, LocksConfig, MigrationConfig
from proxmox_storage_drs.exceptions import PveApiError
from proxmox_storage_drs.payback import MoveCost, compute_wipe_duration_seconds
from proxmox_storage_drs.pve import PveClient
from proxmox_storage_drs.reserve import largest_disk_bytes, transient_charge_ok
from proxmox_storage_drs.schedule import ScheduledMove, ScheduleResult
from proxmox_storage_drs.topology import (
    DISK_KEY_RE,
    Disk,
    Group,
    Storage,
    content_item_size,
    parse_disk_spec,
    parse_pve_config_size_bytes,
    pending_disk_reasons,
    storage_accepts_format,
)
from proxmox_storage_drs.units import format_bytes

logger = logging.getLogger(__name__)


def _vm_label(disk: Disk) -> str:
    """``"name(vmid)"`` for a VM-level log line -- the VM half of
    `Disk.display_id`, so a lock warning names the VM the same way the
    move records around it do."""
    return f"{disk.vm_name}({disk.vmid})"


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
    matches reality, and re-planning from fresh state can fix it).

    ``abort_run`` marks a ``"failed"`` outcome that is *not* a `move_disk`
    task failure but a check the executor could not make before starting
    the move -- the PVE API errored while re-reading the VM or the target
    storage, or the target's listing holds a volume whose size cannot be
    established (section 9.2, "Errors are not mismatches"). Re-planning
    cannot repair those (a plan built on the same unreadable data would be
    refused again), so the whole run ends, every remaining group included,
    and exits non-zero; it is always set together with ``always_stop``.

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
    abort_run: bool = False


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """One group's ``execute_plan()`` call. ``stopped_early`` is true for
    any reason the remaining moves were never attempted -- an operator
    quitting confirm mode is not a failure, a `replan_needed` or (with
    ``execution.abort_on_failure``) a genuine failure both are; the
    distinction is in ``outcomes``, not in this flag.

    ``abort_reason`` is set by the re-plan loop when a re-plan could not
    even be computed (the load model was unavailable, a Prometheus error);
    together with any outcome's ``abort_run`` it makes :attr:`aborted` true,
    which tells ``apply`` to stop visiting further groups and exit non-zero.
    ``replans_exhausted`` is set when ``execution.max_replans_per_run`` ran
    out: the run bails out and the next one starts from fresh state -- a
    warning, not a failure (section 9.2's re-plan protocol)."""

    outcomes: tuple[MoveOutcome, ...]
    stopped_early: bool
    stop_reason: str | None
    abort_reason: str | None = None
    replans_exhausted: bool = False
    # How many times the re-plan loop re-planned this group; only ever
    # non-zero from `cli._run_auto_group()`. Reported in the status file.
    replans: int = 0

    @property
    def aborted(self) -> bool:
        """Whether this group's execution failed in a way that must end the
        whole run (every later group included) with a non-zero exit."""
        return self.abort_reason is not None or any(o.abort_run for o in self.outcomes)


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
    # `mismatch` is set because the PVE API errored while re-reading the VM,
    # not because the cluster differs from the plan -- see `_pre_move_refusal`.
    fatal: bool = False
    # The disk line's own `size=` in the VM config, in bytes: what PVE
    # allocates the mirror target at for a move between different storage
    # types or from thin to thick, where the target is not a copy of the
    # source image's own size. `None` when the line carries no parseable one.
    config_size_bytes: int | None = None


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
    """Section 9.2's six re-checks, immediately before issuing one move.

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
        return _PreflightResult(
            f"could not re-fetch VM {disk.vmid}'s config on {node!r}: {exc}", fatal=True
        )

    value = config.get(move.device)
    if not isinstance(value, str):
        return _PreflightResult(f"{disk.display_id} is no longer present in the VM's config")
    storage_id, volume_name, params = parse_disk_spec(value)
    if storage_id != move.from_storage:
        return _PreflightResult(
            f"{disk.display_id} is now on {storage_id!r}, not the planned {move.from_storage!r}"
        )

    if resource.get("status") != "running":
        return _PreflightResult(f"VM {disk.vmid} is no longer running")

    real_snapshots = [s for s in client.vm_snapshots(node, disk.vmid) if s.get("name") != "current"]
    if real_snapshots:
        return _PreflightResult(
            f"VM {disk.vmid} now has {len(real_snapshots)} snapshot(s) that did not exist when "
            "this plan was built -- move_disk delete=1 would be rejected"
        )

    # Step 6 (section 3.8/9.2): only `/pending` -- not the `config` already
    # fetched above -- distinguishes a key's pending value from the one
    # actually in effect, so this needs its own live call. An operator can
    # queue a pending change in the PVE UI at any point between planning and
    # this exact moment, the same way a lock or a new snapshot can.
    pending = client.vm_pending(node, disk.vmid)
    pending_reason = pending_disk_reasons(pending).get(move.device)
    if pending_reason is not None:
        return _PreflightResult(
            f"{disk.display_id} now has a {pending_reason} that did not exist when this plan was "
            "built -- PVE does not reconcile a disk's pending entry when it is moved, so it "
            "would be left referring to pre-move state"
        )

    lock = config.get("lock")
    volid = f"{move.from_storage}:{volume_name}"
    return _PreflightResult(
        None,
        node=node,
        lock=lock if isinstance(lock, str) else None,
        volid=volid,
        config_size_bytes=parse_pve_config_size_bytes(params.get("size", "")),
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
    client: PveClient,
    node: str,
    vmid: int,
    locks: LocksConfig,
    clock: Clock,
    vm_label: str | None = None,
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
                vm_label or vmid,
                lock,
                locks.wait_timeout_seconds,
                extra={"event": "vm_locked", "vmid": vmid, "lock": lock},
            )
            warned = True
        clock.sleep(locks.poll_interval_seconds)
        lock = _check_lock_once(client, node, vmid)
    return True, None


_TASK_LOCK_TIMEOUT_RE = re.compile(r"can't lock file '[^']*' - got timeout")


def _is_task_lock_timeout(detail: str) -> bool:
    """Section 9.3 point 3: a `move_disk` *task*'s own `exitstatus` can be
    PVE's `can't lock file '<path>' - got timeout` -- the VM config file's
    flock, a different lock than the `lock:` config attribute
    `_wait_for_unlocked()` waits out above, momentarily still held (typically
    by the previous move's own cleanup for the same VM) even after that
    attribute already reads clear. Matched narrowly against PVE's own exact
    wording, not any task failure, so this never retries a genuine failure
    that happens to mention "lock" for an unrelated reason."""
    return bool(_TASK_LOCK_TIMEOUT_RE.search(detail))


def _log_task_lock_retry(
    disk: Disk, attempt: int, limit: int, detail: str, *, concurrent: bool
) -> None:
    logger.warning(
        "retrying move_disk of %s after a task lock timeout (attempt %s/%s): %s",
        disk.display_id,
        attempt,
        limit,
        detail,
        extra={
            "event": "move_disk_task_lock_retry",
            "disk_key": disk.key,
            "vmid": disk.vmid,
            "attempt": attempt,
            "limit": limit,
            "concurrent": concurrent,
        },
    )


@dataclass(frozen=True, slots=True)
class _LiveCheck:
    """:func:`_live_transient_check`'s result: ``refusal`` is ``None`` when
    the move may start, else the operator-facing reason it may not (the
    refusal outcome's ``detail``). ``listed_volids`` is every
    volume the target's content listing showed at that instant -- the
    concurrent executor records it on the move it then launches, as the
    baseline :func:`_inflight_target_volids` needs to recognise that move's
    own mirror target later."""

    refusal: str | None
    listed_volids: frozenset[str] = frozenset()
    # The refusal is an unreadable target, not a full one: see `_pre_move_refusal`.
    fatal: bool = False


def _is_mirror_target(item: Mapping[str, Any], im: _InflightMove, taken: set[str]) -> bool:
    """Is this content entry the volume ``im``'s ``move_disk`` created on
    its target? A mirror target is a volume that (a) was not in the target's
    listing when ``im`` launched, (b) belongs to the same VM, and (c) has
    one of the two sizes ``move_disk`` allocates it at: the source image's
    own size (``im.disk.size_bytes``, from its content listing) for a move
    between storages of the same thin kind, or the disk line's ``size=`` in
    the VM config (``im.config_size_bytes``) when moving between different
    storage types or from thin to thick. Either can differ from the other
    when a volume was resized outside PVE or its storage rounds sizes, so
    both are accepted. ``taken`` are volids an earlier in-flight move
    already claimed, so two moves never share one."""
    volid = item.get("volid")
    sized = content_item_size(item)
    return (
        isinstance(volid, str)
        and volid not in taken
        and volid not in im.target_baseline_volids
        and item.get("vmid") == im.disk.vmid
        and sized is not None
        and sized[0] in (im.disk.size_bytes, im.config_size_bytes)
    )


def _inflight_target_volids(
    content: Sequence[Mapping[str, Any]], inflight_here: Sequence[_InflightMove]
) -> set[str]:
    """The volids in ``content`` that are the mirror targets of this run's
    own in-flight moves onto this storage -- at most one per move.

    Those volumes are already charged as ``z_m`` by :func:`_live_transient_check`,
    so counting them again from the listing would charge every in-flight
    move twice. Whether a target is listed yet is not something the caller
    can assume either way: on Ceph RBD, LVM and file storage the new image
    exists at its full provisioned size the moment ``move_disk`` allocates
    it, but there is a window between ``move_disk`` returning its UPID and
    that allocation. A move whose target is not listed yet simply matches
    nothing here and stays charged by ``z_m`` alone.

    Deliberately narrow (see :func:`_is_mirror_target`): when nothing
    matches, nothing is excluded, and the volume is counted -- a wrongly
    kept volume only makes the check stricter, a wrongly dropped one would
    make it weaker, and weaker is the direction this tool never accepts."""
    taken: set[str] = set()
    for im in inflight_here:
        for item in content:
            if _is_mirror_target(item, im, taken):
                taken.add(str(item["volid"]))
                break
    return taken


def _provisioned_used_bytes(
    content: Sequence[Mapping[str, Any]], mirror_volids: set[str]
) -> tuple[int, str | None]:
    """Sum of every listed volume's *provisioned* size, skipping
    ``mirror_volids``, as ``(bytes, None)`` -- or ``(0, volid)`` naming the
    first volume with neither ``size`` nor ``approximate-size``, whose size
    is unknowable from the listing. Planning skips such a foreign volume
    with a warning; a check that decides whether to touch the storage
    right now cannot, so the caller refuses instead."""
    total = 0
    for item in content:
        if item.get("volid") in mirror_volids:
            continue
        sized = content_item_size(item)
        if sized is None:
            return 0, str(item.get("volid", "?"))
        total += sized[0]
    return total, None


def _move_charge_bytes(
    disk: Disk, config_size_bytes: int | None, source: Storage, target: Storage
) -> int:
    """``z_m`` for section 8.1's transient invariant: the bytes this move
    puts on ``target``. That is the disk's listed size (``Disk.size_bytes``,
    the source image's own) unless the move changes what kind of volume is
    made -- between different storage types, or a qcow2 disk landing on a
    target that cannot hold qcow2, so PVE writes it raw -- where the target
    is allocated at the disk line's ``size=`` in the VM config and the larger
    of the two is charged (``config_size_bytes`` is ``None`` when the line
    carries no parseable ``size=``, which leaves the listed size).

    This is what the operator describes PVE doing (not read from PVE's
    source). A same-kind move keeps the listed size on purpose: there the
    target is a copy of the source image, and charging more would refuse
    moves for a discrepancy that does not apply. This tool never passes
    ``format=`` to ``move_disk`` and (C2) keeps a qcow2 disk off storage that
    cannot hold it, so the conversion case is a guard rather than something
    a plan produces today."""
    changes_kind = source.storage_type != target.storage_type
    converts_to_raw = disk.format == "qcow2" and not storage_accepts_format(target, "qcow2")
    if (changes_kind or converts_to_raw) and config_size_bytes is not None:
        return max(disk.size_bytes, config_size_bytes)
    return disk.size_bytes


def _pre_move_refusal(move: ScheduledMove, detail: str, *, fatal: bool) -> MoveOutcome:
    """The outcome for a move the executor declined to start.

    Two different things can make it decline, and they need different
    responses (section 9.2, "Errors are not mismatches"). When the cluster
    simply no longer matches the plan -- the VM moved, a snapshot appeared,
    the target filled up -- the outcome is ``"replan_needed"``: the run
    re-plans from fresh state, bounded by ``execution.max_replans_per_run``.
    When the check itself could not be made (the PVE API errored, or the
    target lists a volume of unknowable size) re-planning would only run
    into the same wall, so the outcome is a ``"failed"`` ``abort_run`` one
    and the whole run ends non-zero."""
    if fatal:
        return MoveOutcome(
            move.disk_key,
            move.from_storage,
            move.to_storage,
            "failed",
            detail,
            always_stop=True,
            abort_run=True,
        )
    return MoveOutcome(move.disk_key, move.from_storage, move.to_storage, "replan_needed", detail)


def _live_transient_check(
    client: PveClient,
    node: str,
    target: Storage,
    charge_bytes: int,
    existing_largest_bytes: int,
    inflight_here: Sequence[_InflightMove] = (),
) -> _LiveCheck:
    """Section 9.2 step 2 -- section 8.1's transient invariant re-derived
    from *live* figures, via the shared :func:`reserve.transient_charge_ok`
    (one arithmetic core, AGENTS.md section 5), for a move that puts
    ``charge_bytes`` (:func:`_move_charge_bytes`) onto ``target`` and has
    not been issued yet.

    **Provisioned, never allocated** (section 5.1, domain rule 8): the
    ``used`` this feeds the rule is the sum of ``size`` over the target's
    live content listing -- what every volume there was *provisioned* at,
    which is exactly the quantity ``schedule.transient_invariant_ok()``
    sums from the model -- and never ``storage_status()``'s own ``used``.
    On a thin pool (Ceph RBD, LVM-thin, ZFS) that is the allocated figure
    and far lower, and a re-check built on it could only ever confirm the
    plan, never notice that other provisioning filled the pool since. What
    still comes from ``storage_status()`` is ``total``, the capacity, for
    the same reason planning takes it there: the LUN may have been resized.

    ``inflight_here`` is every move of *this run* currently in flight onto
    ``target`` (the concurrent executor's; the sequential one has none).
    Their mirror targets are excluded from the listing sum
    (:func:`_inflight_target_volids`) because the caller charges each of
    them as a ``z_m`` already.

    Fails safe: an API error, or a listed volume with no size to count,
    refuses the move rather than checking against a partial figure -- and
    ``fatal`` is set on that refusal, so the run ends non-zero instead of
    re-planning (see :func:`_pre_move_refusal`). A target that is merely
    too full is not fatal: that refusal is ``replan_needed``. The floor
    stays ``target.free_space_hard_bytes`` -- section 5.3.1's ``hard_b``,
    resolved once at run start; only the usage and capacity are re-read
    live."""
    try:
        status = client.storage_status(node, target.id)
        content = client.storage_content(node, target.id)
    except PveApiError as exc:
        logger.warning(
            "could not re-read %s for the live transient check: %s",
            target.id,
            exc,
            extra={"event": "live_check_failed", "storage": target.id},
        )
        return _LiveCheck(
            f"could not re-read {target.id!r}'s live state ({exc}); not starting a move "
            "onto it without that",
            fatal=True,
        )
    listed = frozenset(str(i["volid"]) for i in content if "volid" in i)
    live_used, unsized_volid = _provisioned_used_bytes(
        content, _inflight_target_volids(content, inflight_here)
    )
    if unsized_volid is not None:
        return _LiveCheck(
            f"{target.id!r} lists {unsized_volid!r} with no size, so its provisioned use "
            "cannot be established just before starting; not moving onto it blind",
            listed,
            fatal=True,
        )
    live_total = int(status["total"])
    charges = [
        _move_charge_bytes(im.disk, im.config_size_bytes, im.source, im.target)
        for im in inflight_here
    ] + [charge_bytes]
    if transient_charge_ok(
        target.reserve_factor,
        live_total,
        live_used,
        existing_largest_bytes,
        charges,
        target.free_space_hard_bytes,
    ):
        return _LiveCheck(None, listed)
    return _LiveCheck(
        f"{target.id!r} no longer has enough free space to safely hold this disk "
        "during the move, checked again just before starting "
        f"(provisioned {format_bytes(live_used)} of {format_bytes(live_total)})",
        listed,
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
    size_bytes: int,
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
    move's task or source-release never blocks progress on any other).

    ``size_bytes`` is ``move``'s own disk size, needed only for the
    ``min_wipe_seconds`` floor below -- see that variable's own comment
    for why the volume-gone/lock-clear pair alone is not always enough."""
    task = client.task_status(node, upid)
    if task.get("status") != "stopped":
        return None, wait_state

    if task.get("exitstatus") != "OK":
        return ("failed", f"move_disk task {upid} failed: {task.get('exitstatus')}"), wait_state

    if not execution.source_release.wait or not source.saferemove:
        return ("moved", f"task {upid} completed OK"), wait_state

    drain_start = wait_state.drain_start or clock.now()
    elapsed = (clock.now() - drain_start).total_seconds()
    content = client.storage_content(node, source.id)
    volume_present = any(item.get("volid") == volid for item in content)
    lock = _check_lock_once(client, node, vmid)
    # Section 9.3 point 3: PVE's own `saferemove_throughput` (already read
    # live off the storage definition, section 3.5) gives an exact floor on
    # how long this disk's wipe can possibly take -- `min_wipe_seconds` is
    # `None` only when the storage has no configured throughput to compute
    # one from. Observed against a real cluster: the content listing and
    # the config `lock:` attribute can both already read clear while PVE's
    # own wipe cleanup for this VM is still finishing, so a subsequent
    # `move_disk` for the *same* VM can still fail with `can't lock file
    # ... - got timeout` even though this move's own three conditions
    # looked satisfied. Never declaring "moved" before this floor elapses
    # closes that race in the one case it can be computed exactly, sharing
    # `payback.compute_wipe_duration_seconds()`'s formula (AGENTS.md
    # section 5) rather than a second copy of it.
    min_wipe_seconds = compute_wipe_duration_seconds(
        size_bytes, source.saferemove_throughput_bytes_per_sec
    )
    if (
        not volume_present
        and not lock
        and (min_wipe_seconds is None or elapsed >= min_wipe_seconds)
    ):
        return ("moved", f"task {upid} completed OK, source released"), wait_state
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
    size_bytes: int,
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
    VM's lock clearing together (plus, when computable, section 9.3 point
    3's ``min_wipe_seconds`` floor -- see :func:`_poll_move_once`), bounded
    by ``execution.source_release.timeout``. Sequential-mode only -- see
    :func:`_poll_move_once` for the non-blocking form the concurrent
    executor uses instead."""
    wait_state = _MoveWaitState()
    while True:
        result, wait_state = _poll_move_once(
            client, node, vmid, upid, source, volid, size_bytes, execution, clock, wait_state
        )
        if result is not None:
            return result
        clock.sleep(execution.poll_interval_seconds)


def _issue_move_disk_and_wait(
    client: PveClient,
    node: str,
    disk: Disk,
    move: ScheduledMove,
    source: Storage,
    volid: str,
    migration: MigrationConfig,
    execution: ExecutionConfig,
    clock: Clock,
    on_inflight_started: InflightCallback | None,
    on_inflight_finished: InflightCallback | None,
) -> tuple[str, str, str]:
    """Issues one `move_disk` attempt and blocks for section 9.3.2's
    completion criterion -- factored out of `_execute_one_move()` purely
    to stay within this project's flake8 complexity limit (AGENTS.md
    section 5; `_confirm_decision()`/`_launch_lock_decision()` are the
    same precedent), since `_execute_one_move()` now calls this once per
    section 9.3 point 3 retry attempt rather than once. Returns
    ``(upid, status, detail)``; drives `on_inflight_started`/
    `on_inflight_finished` and the `move_started`/`move_finished` log
    records exactly as a single, non-retried attempt always did -- a
    retried attempt is still always exactly one UPID in flight at a
    time, from `state.json`'s point of view."""
    upid = client.move_disk(
        node,
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
    # Section 2.1/2.3: "every `move_disk` issued with its UPID". This is the
    # one record that makes an unattended run reconstructable afterwards --
    # it is what lets an operator tie a PVE task in the cluster's own task
    # log back to the plan that decided to issue it.
    logger.info(
        "move started: %s %s -> %s (%s)",
        disk.display_id,
        move.from_storage,
        move.to_storage,
        upid,
        extra={
            "event": "move_started",
            "upid": upid,
            "disk_key": move.disk_key,
            "vmid": disk.vmid,
            "device": disk.device,
            "node": node,
            "from_storage": move.from_storage,
            "to_storage": move.to_storage,
            "size_bytes": disk.size_bytes,
        },
    )
    # `clock.now()`, not `time.monotonic()`: the injected fake clock tests
    # use advances this instantly (`.agents/testing.md`), so the duration
    # this record reports is the one the wait loop itself measured.
    started_at = clock.now()
    status, detail = _wait_for_move_completion(
        client, node, disk.vmid, upid, source, volid, disk.size_bytes, execution, clock
    )
    logger.info(
        "move finished: %s -> %s (%s)",
        disk.display_id,
        status,
        upid,
        extra={
            "event": "move_finished",
            "upid": upid,
            "disk_key": move.disk_key,
            "from_storage": move.from_storage,
            "to_storage": move.to_storage,
            "size_bytes": disk.size_bytes,
            "status": status,
            "detail": detail,
            "duration_seconds": round((clock.now() - started_at).total_seconds(), 3),
        },
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
    return upid, status, detail


def _execute_one_move(
    client: PveClient,
    disk: Disk,
    move: ScheduledMove,
    storages_by_id: dict[str, Storage],
    migration: MigrationConfig,
    execution: ExecutionConfig,
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
        return _pre_move_refusal(move, preflight.mismatch, fatal=preflight.fatal)
    assert (
        preflight.node is not None and preflight.volid is not None
    )  # guaranteed when mismatch is None

    if preflight.lock:
        cleared, last_lock = _wait_for_unlocked(
            client, preflight.node, disk.vmid, execution.locks, clock, _vm_label(disk)
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
    live = _live_transient_check(
        client,
        preflight.node,
        target,
        _move_charge_bytes(
            disk, preflight.config_size_bytes, storages_by_id[move.from_storage], target
        ),
        largest_by_storage[move.to_storage],
    )
    if live.refusal is not None:
        return _pre_move_refusal(move, live.refusal, fatal=live.fatal)

    source = storages_by_id[move.from_storage]
    task_retries_used = 0
    while True:
        upid, status, detail = _issue_move_disk_and_wait(
            client,
            preflight.node,
            disk,
            move,
            source,
            preflight.volid,
            migration,
            execution,
            clock,
            on_inflight_started,
            on_inflight_finished,
        )
        # Section 9.3 point 3: the task's own flock on the VM config file is
        # not the `lock:` config attribute the pre-flight check above waits
        # on -- it can still be held for a moment by another task's cleanup
        # even after that attribute reads clear, with nothing to poll that
        # would have shown it coming. Retried here, narrowly, rather than
        # reported as an ordinary failure.
        if (
            status == "failed"
            and task_retries_used < execution.locks.task_retry_limit
            and _is_task_lock_timeout(detail)
            and not _deadline_exceeded(clock, deadline, estimated_seconds)
        ):
            task_retries_used += 1
            _log_task_lock_retry(
                disk,
                task_retries_used,
                execution.locks.task_retry_limit,
                detail,
                concurrent=False,
            )
            clock.sleep(execution.locks.task_retry_backoff_seconds)
            continue
        break
    orphans: tuple[str, ...] = ()
    if status == "failed":
        orphans = _detect_orphan_volumes(client, preflight.node, move.to_storage, disk.vmid)
        if orphans:
            logger.warning(
                "orphaned volume(s) left on %s after the failed move of %s: %s",
                move.to_storage,
                disk.display_id,
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
        return f"{disk.display_id} failed: {result.detail}"
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
    # Section 9.3 point 3's task-lock-timeout retry count for this move,
    # the concurrent counterpart to `_execute_one_move()`'s own local
    # `task_retries_used` -- carried here since nothing on this path holds
    # a call stack per move across poll cycles.
    task_retries_used: int = 0
    # Every volid the target storage's content listing showed at the
    # instant this move launched -- what `_inflight_target_volids()` needs
    # to tell this move's own mirror target from a volume that was already
    # there (which section 5.1's provisioned sum must keep counting).
    target_baseline_volids: frozenset[str] = frozenset()
    # `_PreflightResult.config_size_bytes` at launch -- the second size
    # `_is_mirror_target()` recognises this move's mirror target by.
    config_size_bytes: int | None = None


def _per_storage_inflight_counts(inflight: Sequence[_InflightMove]) -> dict[str, int]:
    """Section 8.1 point 3: how many in-flight moves currently touch each
    storage as *either* source or target -- what
    `execution.max_concurrent_per_storage` ceilings."""
    counts: dict[str, int] = {}
    for im in inflight:
        counts[im.move.from_storage] = counts.get(im.move.from_storage, 0) + 1
        counts[im.move.to_storage] = counts.get(im.move.to_storage, 0) + 1
    return counts


def _inflight_onto(inflight: Sequence[_InflightMove], storage_id: str) -> list[_InflightMove]:
    """This run's in-flight moves whose *target* is ``storage_id``."""
    return [im for im in inflight if im.move.to_storage == storage_id]


def _poll_inflight_once(
    client: PveClient,
    inflight: Sequence[_InflightMove],
    migration: MigrationConfig,
    execution: ExecutionConfig,
    clock: Clock,
    largest_by_storage: dict[str, int],
    drained_storages: set[str],
    on_inflight_started: InflightCallback | None,
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
            im.disk.size_bytes,
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
        logger.info(
            "move finished: %s -> %s (%s)",
            im.disk.display_id,
            status,
            im.upid,
            extra={
                "event": "move_finished",
                "upid": im.upid,
                "disk_key": im.move.disk_key,
                "from_storage": im.move.from_storage,
                "to_storage": im.move.to_storage,
                "size_bytes": im.disk.size_bytes,
                "status": status,
                "detail": detail,
                "concurrent": True,
            },
        )
        # Section 9.3 point 3, the concurrent counterpart of
        # `_execute_one_move()`'s own retry loop. No inline `clock.sleep()`
        # here on purpose -- blocking this poll cycle would stall every
        # other in-flight and candidate move exactly like a blocking lock
        # wait would; the retry is instead reissued immediately and picked
        # up again next cycle, naturally spaced by
        # `execution.poll_interval_seconds` unless something else already
        # made progress this cycle.
        if (
            status == "failed"
            and im.task_retries_used < execution.locks.task_retry_limit
            and _is_task_lock_timeout(detail)
        ):
            retries_used = im.task_retries_used + 1
            _log_task_lock_retry(
                im.disk,
                retries_used,
                execution.locks.task_retry_limit,
                detail,
                concurrent=True,
            )
            new_upid = client.move_disk(
                im.node,
                im.disk.vmid,
                im.disk.device,
                im.move.to_storage,
                delete=True,
                bwlimit_bytes_per_sec=migration.bwlimit_bytes_per_sec,
            )
            if on_inflight_started is not None:
                on_inflight_started(new_upid)
            logger.info(
                "move started: %s %s -> %s (%s)",
                im.disk.display_id,
                im.move.from_storage,
                im.move.to_storage,
                new_upid,
                extra={
                    "event": "move_started",
                    "upid": new_upid,
                    "disk_key": im.move.disk_key,
                    "vmid": im.disk.vmid,
                    "device": im.disk.device,
                    "node": im.node,
                    "from_storage": im.move.from_storage,
                    "to_storage": im.move.to_storage,
                    "size_bytes": im.disk.size_bytes,
                    "concurrent": True,
                },
            )
            still_inflight.append(
                replace(
                    im,
                    upid=new_upid,
                    wait_state=_MoveWaitState(),
                    task_retries_used=retries_used,
                )
            )
            continue
        orphans: tuple[str, ...] = ()
        if status == "failed":
            orphans = _detect_orphan_volumes(client, im.node, im.move.to_storage, im.disk.vmid)
            if orphans:
                logger.warning(
                    "orphaned volume(s) left on %s after the failed move of %s: %s",
                    im.move.to_storage,
                    im.disk.display_id,
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
    # The target's listing at the moment of the live check, for a
    # ``"launch"`` verdict: becomes the launched move's
    # `_InflightMove.target_baseline_volids`.
    target_baseline_volids: frozenset[str] = frozenset()


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
            _vm_label(disk),
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
        outcome = _pre_move_refusal(candidate, preflight.mismatch, fatal=preflight.fatal)
        return _LaunchDecision("resolved", outcome=outcome)
    assert (
        preflight.node is not None and preflight.volid is not None
    )  # guaranteed when mismatch is None

    if preflight.lock:
        return _launch_lock_decision(
            candidate, disk, preflight.lock, execution.locks, clock, lock_wait
        )

    target = storages_by_id[candidate.to_storage]
    live = _live_transient_check(
        client,
        preflight.node,
        target,
        _move_charge_bytes(
            disk, preflight.config_size_bytes, storages_by_id[candidate.from_storage], target
        ),
        largest_by_storage[target.id],
        _inflight_onto(inflight, target.id),
    )
    if live.refusal is not None:
        outcome = _pre_move_refusal(candidate, live.refusal, fatal=live.fatal)
        return _LaunchDecision("resolved", outcome=outcome)

    return _LaunchDecision("launch", preflight=preflight, target_baseline_volids=live.listed_volids)


def _advance_pending(
    client: PveClient,
    pending: list[ScheduledMove],
    outcomes: list[MoveOutcome],
    inflight: list[_InflightMove],
    disks_by_key: dict[str, Disk],
    storages_by_id: dict[str, Storage],
    migration: MigrationConfig,
    execution: ExecutionConfig,
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
        # Section 2.3's `move_started`, same record the sequential executor
        # emits: every `move_disk` issued, by either path, is in the journal
        # with its UPID.
        logger.info(
            "move started: %s %s -> %s (%s)",
            disk.display_id,
            candidate.from_storage,
            candidate.to_storage,
            upid,
            extra={
                "event": "move_started",
                "upid": upid,
                "disk_key": candidate.disk_key,
                "vmid": disk.vmid,
                "device": disk.device,
                "node": pf.node,
                "from_storage": candidate.from_storage,
                "to_storage": candidate.to_storage,
                "size_bytes": disk.size_bytes,
                "concurrent": True,
            },
        )
        inflight.append(
            _InflightMove(
                move=candidate,
                disk=disk,
                node=pf.node,
                upid=upid,
                source=storages_by_id[candidate.from_storage],
                target=storages_by_id[candidate.to_storage],
                volid=pf.volid,
                target_baseline_volids=decision.target_baseline_volids,
                config_size_bytes=pf.config_size_bytes,
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
            migration,
            execution,
            clock,
            largest_by_storage,
            drained_storages,
            on_inflight_started,
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
