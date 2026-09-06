# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Startup crash/two-instance recovery. See IMPLEMENTATION_PLAN.md section 13.

"Engine crashes mid-move" and "Two DRS instances running" share one
mechanism: `state.json`'s `inflight_upids` is written *before* issuing
each `move_disk` and cleared once that task itself finishes (`execute.py`,
via a callback `cli.py` supplies), so a crashed run leaves a real trace
behind. `reconcile_inflight()` is what `apply` calls on startup, *before
planning anything* (section 9.4's own words) -- it does two things:

1. Re-checks every UPID `state.json` already remembers. One whose task
   has since finished is dropped (a normal reconciliation of a completed
   move the engine never got to clear itself); one still running means
   this VM must not be touched by a second, conflicting `move_disk` this
   run.
2. Scans **every node's** task list (`PveClient.cluster_tasks()` -- the
   one read that actually crosses the cluster, since `state.json`'s own
   `flock()` cannot, see `docs/internals/15-state.md`) for a still
   -running `qmmove` task from this tool's own configured user that
   is not already accounted for above. `IMPLEMENTATION_PLAN.md` is
   explicit that this is what degrades "two instances running" from
   "conflicting" to merely "slow and redundant" -- the correct fix is
   still "run the timer on exactly one host," this is the safety net
   for when that is not honoured.

Either way, the affected vmid is reported for the caller to exclude from
this run's planning (`cli.py` folds it into `exclude.vmids`, reusing
`topology.py`'s existing (C2) pin rather than inventing a second
exclusion mechanism -- AGENTS.md section 5) -- never force-cancelled,
never assumed to be safe to ignore.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace

from proxmox_storage_drs.config import AuthConfig
from proxmox_storage_drs.exceptions import PveApiError
from proxmox_storage_drs.pve import PveClient
from proxmox_storage_drs.state import State

logger = logging.getLogger(__name__)


def expected_task_user(auth: AuthConfig) -> str | None:
    """The exact string PVE records as a task's ``user`` field for
    credentials this tool authenticates with: ``auth.token_id`` verbatim
    for token auth (already in ``user@realm!tokenname`` form -- see
    `pve.py`'s own token construction, which passes it through
    unchanged), or ``auth.username`` for password auth. ``None`` when
    neither is configured, which config validation elsewhere already
    makes unreachable in practice."""
    if auth.token_id:
        return auth.token_id
    return auth.username


@dataclass(frozen=True, slots=True)
class UpidInfo:
    node: str
    task_type: str
    vmid: int | None
    user: str


def parse_upid(upid: str) -> UpidInfo | None:
    """PVE's UPID grammar, confirmed against a real cluster (see
    ``dev-cluster-access`` in this project's own development notes):
    ``UPID:{node}:{pid}:{pstart}:{starttime}:{type}:{id}:{user}:`` --
    ``id`` is the vmid, as a string, for a VM-scoped task type such as
    ``qmmove`` (confirmed live for ``qmconfig``), empty for others (e.g.
    ``vzdump``). Returns ``None`` for anything that does not parse as a
    UPID at all, rather than raising -- a malformed or foreign string
    here must degrade to "cannot use this one," not crash the scan."""
    parts = upid.split(":")
    if len(parts) < 8 or parts[0] != "UPID":
        return None
    node, task_type, task_id, user = parts[1], parts[5], parts[6], parts[7]
    vmid = int(task_id) if task_id.isdigit() else None
    return UpidInfo(node=node, task_type=task_type, vmid=vmid, user=user)


def _task_is_running(client: PveClient, node: str, upid: str) -> bool | None:
    """``True``/``False`` from the one already-tested implementation of
    "is this task still running" (`PveClient.task_status()`, the
    per-task endpoint -- not ``/cluster/tasks``' own, differently
    -shaped ``endtime``/``status`` convention, even though that is what
    first flags a candidate). ``None`` when the check itself failed
    (the node is unreachable, say) -- treated by callers as "assume
    still running": the safe direction to guess wrong in is excluding a
    VM that turned out to be free, never the reverse."""
    try:
        status = client.task_status(node, upid)
    except PveApiError as exc:
        logger.warning(
            "could not check task %s, assuming it is still running: %s",
            upid,
            exc,
            extra={"event": "inflight_check_failed", "upid": upid},
        )
        return None
    return status.get("status") != "stopped"


def _reconcile_recorded_upids(
    client: PveClient, recorded_upids: tuple[str, ...]
) -> tuple[frozenset[int], tuple[str, ...]]:
    """The local half of the startup scan: re-checks every UPID
    ``state.json`` already remembers. Returns the vmids still in flight
    and the subset of ``recorded_upids`` whose task has *not* finished
    (what ``inflight_upids`` should become) -- factored out of
    :func:`reconcile_inflight` purely to stay within this project's
    flake8 complexity limit."""
    excluded_vmids: set[int] = set()
    still_inflight: list[str] = []
    for upid in recorded_upids:
        info = parse_upid(upid)
        if info is None or info.vmid is None:
            # Cannot make sense of it -- drop it rather than block a
            # vmid forever on a malformed entry no future run could ever
            # resolve either.
            continue
        if _task_is_running(client, info.node, upid) is False:
            logger.info(
                "a previously in-flight move_disk task has since finished: %s",
                upid,
                extra={"event": "inflight_reconciled", "upid": upid},
            )
            continue
        still_inflight.append(upid)
        excluded_vmids.add(info.vmid)
    return frozenset(excluded_vmids), tuple(still_inflight)


def _scan_cluster_for_foreign_inflight(
    client: PveClient, auth: AuthConfig, already_known: frozenset[str]
) -> frozenset[int]:
    """The cluster-wide half: a still-running ``qmmove`` task from this
    tool's own configured user that ``already_known`` (the locally
    -recorded UPIDs) does not already account for -- a second,
    concurrently-running instance, most likely. Factored out of
    :func:`reconcile_inflight` for the same reason as the function
    above."""
    expected_user = expected_task_user(auth)
    if expected_user is None:
        return frozenset()
    try:
        cluster_tasks = client.cluster_tasks()
    except PveApiError as exc:
        logger.warning(
            "could not scan the cluster for in-flight migrations: %s",
            exc,
            extra={"event": "cluster_task_scan_failed"},
        )
        return frozenset()

    excluded_vmids: set[int] = set()
    for task in cluster_tasks:
        if task.get("type") != "qmmove" or task.get("user") != expected_user:
            continue
        if "endtime" in task or "status" in task:
            continue  # already finished, per /cluster/tasks' own convention
        candidate_upid = task.get("upid")
        if not isinstance(candidate_upid, str) or candidate_upid in already_known:
            continue
        info = parse_upid(candidate_upid)
        if info is None or info.vmid is None:
            continue
        if _task_is_running(client, info.node, candidate_upid) is False:
            continue
        logger.warning(
            "found an in-flight move_disk task for VM %s from another instance or a "
            "crashed run; excluding it from this run: %s",
            info.vmid,
            candidate_upid,
            extra={"event": "inflight_found", "vmid": info.vmid, "upid": candidate_upid},
        )
        excluded_vmids.add(info.vmid)
    return frozenset(excluded_vmids)


def reconcile_inflight(
    client: PveClient, state: State, auth: AuthConfig
) -> tuple[frozenset[int], State]:
    """Section 13's startup scan. Returns the vmids to exclude from this
    run's planning, and ``state`` with any UPID whose task has since
    finished dropped from ``inflight_upids`` -- the caller (`cli.py`)
    persists that update the same way it persists everything else
    learned during a run."""
    local_vmids, still_inflight = _reconcile_recorded_upids(client, state.inflight_upids)
    foreign_vmids = _scan_cluster_for_foreign_inflight(client, auth, frozenset(still_inflight))

    if still_inflight != state.inflight_upids:
        state = replace(state, inflight_upids=still_inflight)
    return local_vmids | foreign_vmids, state
