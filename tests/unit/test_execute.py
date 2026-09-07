# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Executing a plan. See proxmox_storage_drs/execute.py.

No test here talks to a real Proxmox VE API or sleeps for a real duration
(`.agents/testing.md`): :class:`FakeProxmoxResource` (``tests/unit/fakes.py``)
stands in for the API, and :class:`FakeClock` stands in for wall-clock time
-- its ``sleep()`` advances its own ``now()`` instantly instead of blocking,
so a wait loop's timeout arithmetic is exercised for real without an
actual wait.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import pytest

from proxmox_storage_drs.config import (
    ExcludeConfig,
    ExecutionConfig,
    LocksConfig,
    MigrationConfig,
    SourceReleaseConfig,
)
from proxmox_storage_drs.exceptions import PveApiError
from proxmox_storage_drs.execute import (
    Clock,
    ExecutionResult,
    _detect_orphan_volumes,
    _live_transient_check,
    _preflight,
    _vm_resource,
    _wait_for_unlocked,
    execute_plan,
)
from proxmox_storage_drs.payback import MoveCost
from proxmox_storage_drs.pve import PveClient
from proxmox_storage_drs.schedule import ScheduledMove, ScheduleResult
from proxmox_storage_drs.topology import Disk, Group, Storage
from tests.unit.fakes import FakeProxmoxResource, fake_api

TIB = 1 << 40
UPID = "UPID:pve01:00001234:00ABCDEF:qmmove:101:root@pam:"


@dataclass
class FakeClock:
    """A `Clock` whose `sleep()` advances its own `now()` instantly."""

    current: datetime
    slept: list[float] = field(default_factory=list)

    def now(self) -> datetime:
        return self.current

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.current += timedelta(seconds=seconds)

    def clock(self) -> Clock:
        return Clock(now=self.now, sleep=self.sleep)


def make_disk(key: str, size_tib: float, storage: str, node: str = "pve01") -> Disk:
    vmid, device = key.split(":")
    return Disk(
        key=key,
        vmid=int(vmid),
        device=device,
        vm_name=f"vm{vmid}",
        node=node,
        size_bytes=round(size_tib * TIB),
        current_storage=storage,
        format="raw",
        pinned_reason=None,
    )


def make_storage(
    id_: str,
    capacity_tib: float = 8.0,
    saferemove: bool = False,
    saferemove_throughput: float | None = None,
) -> Storage:
    return Storage(
        id=id_,
        capability_weight=1.0,
        reserve_factor=2.0,
        saturation_load=None,
        capacity_bytes=round(capacity_tib * TIB),
        used_bytes=0,
        foreign_used_bytes=0,
        saferemove=saferemove,
        saferemove_throughput_bytes_per_sec=saferemove_throughput,
    )


def make_move(
    disk_key: str = "101:scsi0",
    vmid: int = 101,
    device: str = "scsi0",
    from_storage: str = "san-a",
    to_storage: str = "san-b",
) -> ScheduledMove:
    return ScheduledMove(
        disk_key=disk_key,
        vmid=vmid,
        device=device,
        from_storage=from_storage,
        to_storage=to_storage,
        size_bytes=round(1.0 * TIB),
        imbalance_reduction=1.0,
        resolves_reserve_violation=False,
    )


def default_group() -> Group:
    return Group(
        name="fc-tier1",
        storages=(make_storage("san-a"), make_storage("san-b")),
        disks=(make_disk("101:scsi0", 1.0, "san-a"),),
    )


DEFAULT_RESPONSES: dict[str, object] = {
    "cluster/resources": [{"vmid": 101, "node": "pve01", "status": "running"}],
    "nodes/pve01/qemu/101/config": {"scsi0": "san-a:vm-101-disk-0,size=1024G"},
    "nodes/pve01/qemu/101/snapshot": [{"name": "current"}],
    "nodes/pve01/storage/san-b/status": {"total": 8 * TIB, "used": 0},
    "nodes/pve01/qemu/101/move_disk": UPID,
    f"nodes/pve01/tasks/{UPID}/status": {"status": "stopped", "exitstatus": "OK"},
    "nodes/pve01/qemu/101/status/current": {"lock": None},
}


def client_with(overrides: dict[str, object]) -> tuple[PveClient, FakeProxmoxResource]:
    responses = {**DEFAULT_RESPONSES, **overrides}
    api = fake_api(responses)
    return PveClient(api), api


MIGRATION = MigrationConfig(bwlimit_bytes_per_sec=209_715_200)
EXECUTION = ExecutionConfig()
EXCLUDE = ExcludeConfig()


def run(
    client: PveClient,
    group: Group,
    moves: tuple[ScheduledMove, ...],
    mode: str = "auto",
    execution: ExecutionConfig = EXECUTION,
    clock: FakeClock | None = None,
    confirm: object = None,
    exclude: ExcludeConfig = EXCLUDE,
    deadline: datetime | None = None,
    move_costs_by_key: dict[str, MoveCost] | None = None,
    max_migrations: int | None = None,
    on_inflight_started: object = None,
    on_inflight_finished: object = None,
) -> ExecutionResult:
    schedule_result = ScheduleResult(
        order=moves, deadlocked=(), final_assignment={d.key: d.current_storage for d in group.disks}
    )
    fc = clock or FakeClock(datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc))
    return execute_plan(
        client,
        group,
        schedule_result,
        MIGRATION,
        execution,
        0,
        mode,
        exclude,
        confirm=confirm,  # type: ignore[arg-type]
        clock=fc.clock(),
        deadline=deadline,
        move_costs_by_key=move_costs_by_key,
        max_migrations=max_migrations,
        on_inflight_started=on_inflight_started,  # type: ignore[arg-type]
        on_inflight_finished=on_inflight_finished,  # type: ignore[arg-type]
    )


# --------------------------------------------------------------------- happy path


def test_happy_path_move_completes_without_saferemove() -> None:
    client, api = client_with({})
    result = run(client, default_group(), (make_move(),))

    assert result.stopped_early is False
    assert len(result.outcomes) == 1
    assert result.outcomes[0].status == "moved"
    assert result.outcomes[0].upid == UPID
    expected = (
        "POST",
        "nodes/pve01/qemu/101/move_disk",
        {"disk": "scsi0", "storage": "san-b", "delete": 1, "bwlimit": 204800},
    )
    assert expected in [c for c in api.calls if c[0] == "POST"]


def test_bwlimit_is_converted_to_kib_at_the_call_site() -> None:
    client, api = client_with({})
    run(client, default_group(), (make_move(),))
    move_call = next(c for c in api.calls if c[1] == "nodes/pve01/qemu/101/move_disk")
    assert move_call[2]["bwlimit"] == round(209_715_200 / 1024.0)


# --------------------------------------------------------------------------- dry-run


def test_dry_run_issues_no_api_calls() -> None:
    client, api = client_with({})
    result = run(client, default_group(), (make_move(),), mode="dry-run")
    assert api.calls == []
    assert result.outcomes[0].status == "would_move"
    assert result.stopped_early is False


# --------------------------------------------------------------------------- confirm


def test_confirm_mode_yes_executes_the_move() -> None:
    client, _api = client_with({})
    result = run(client, default_group(), (make_move(),), mode="confirm", confirm=lambda m: "y")
    assert result.outcomes[0].status == "moved"


def test_confirm_mode_no_skips_the_move() -> None:
    client, api = client_with({})
    result = run(client, default_group(), (make_move(),), mode="confirm", confirm=lambda m: "n")
    assert result.outcomes[0].status == "skipped"
    assert result.outcomes[0].detail == "operator declined"
    assert not any(c[0] == "POST" for c in api.calls)


def test_confirm_mode_quit_stops_immediately() -> None:
    group = Group(
        name="g",
        storages=(make_storage("san-a"), make_storage("san-b")),
        disks=(make_disk("101:scsi0", 1.0, "san-a"), make_disk("102:scsi0", 1.0, "san-a")),
    )
    moves = (make_move(), make_move("102:scsi0", 102, "scsi0"))
    client, api = client_with(
        {
            "cluster/resources": [
                {"vmid": 101, "node": "pve01", "status": "running"},
                {"vmid": 102, "node": "pve01", "status": "running"},
            ]
        }
    )
    result = run(client, group, moves, mode="confirm", confirm=lambda m: "q")
    assert result.stopped_early is True
    assert result.stop_reason == "operator quit"
    assert result.outcomes == ()
    assert api.calls == []  # quit before even the first pre-flight re-check


def test_confirm_mode_all_remaining_stops_prompting() -> None:
    group = Group(
        name="g",
        storages=(make_storage("san-a"), make_storage("san-b")),
        disks=(make_disk("101:scsi0", 1.0, "san-a"), make_disk("102:scsi0", 1.0, "san-a")),
    )
    moves = (make_move(), make_move("102:scsi0", 102, "scsi0"))
    upid2 = "UPID:pve01:00001235:00ABCDEF:qmmove:102:root@pam:"
    client, _api = client_with(
        {
            "cluster/resources": [
                {"vmid": 101, "node": "pve01", "status": "running"},
                {"vmid": 102, "node": "pve01", "status": "running"},
            ],
            "nodes/pve01/qemu/102/config": {"scsi0": "san-a:vm-102-disk-0,size=1024G"},
            "nodes/pve01/qemu/102/snapshot": [{"name": "current"}],
            "nodes/pve01/qemu/102/status/current": {"lock": None},
            "nodes/pve01/qemu/102/move_disk": upid2,
            f"nodes/pve01/tasks/{upid2}/status": {"status": "stopped", "exitstatus": "OK"},
        }
    )
    calls = []

    def confirm(move: ScheduledMove) -> str:
        calls.append(move.disk_key)
        return "a"

    result = run(client, group, moves, mode="confirm", confirm=confirm)
    assert calls == ["101:scsi0"]  # only prompted once
    assert [o.status for o in result.outcomes] == ["moved", "moved"]


def test_confirm_mode_invalid_decision_raises() -> None:
    client, _api = client_with({})
    with pytest.raises(ValueError, match="expected y/n/a/q"):
        run(client, default_group(), (make_move(),), mode="confirm", confirm=lambda m: "x")


def test_confirm_mode_no_callback_defaults_to_skip() -> None:
    client, api = client_with({})
    result = run(client, default_group(), (make_move(),), mode="confirm", confirm=None)
    assert result.outcomes[0].status == "skipped"
    assert api.calls == []


# ---------------------------------------------------------------------- VM locks


def test_vm_lock_clears_within_timeout_then_proceeds() -> None:
    calls = {"n": 0}

    def status_current(**kwargs: object) -> dict[str, object]:
        calls["n"] += 1
        return {"lock": "backup" if calls["n"] < 3 else None}

    client, _api = client_with(
        {
            # _preflight reads the initial `lock` off the VM's *config*
            # (matching PVE's own "lock: backup" config line) -- only the
            # follow-up wait loop polls status/current.
            "nodes/pve01/qemu/101/config": {
                "scsi0": "san-a:vm-101-disk-0,size=1024G",
                "lock": "backup",
            },
            "nodes/pve01/qemu/101/status/current": status_current,
        }
    )
    fc = FakeClock(datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc))
    result = run(client, default_group(), (make_move(),), clock=fc)
    assert result.outcomes[0].status == "moved"
    assert len(fc.slept) >= 1


def test_vm_lock_timeout_with_on_timeout_skip() -> None:
    client, _api = client_with(
        {
            "nodes/pve01/qemu/101/config": {
                "scsi0": "san-a:vm-101-disk-0,size=1024G",
                "lock": "backup",
            },
            "nodes/pve01/qemu/101/status/current": {"lock": "backup"},
        }
    )
    execution = ExecutionConfig(
        locks=LocksConfig(wait_timeout_seconds=100.0, poll_interval_seconds=30.0, on_timeout="skip")
    )
    fc = FakeClock(datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc))
    result = run(client, default_group(), (make_move(),), execution=execution, clock=fc)
    assert result.outcomes[0].status == "skipped"
    assert "still locked" in result.outcomes[0].detail
    assert result.outcomes[0].always_stop is False
    assert result.stopped_early is False


def test_vm_lock_timeout_with_on_timeout_abort_stops_the_run_regardless_of_abort_on_failure() -> (
    None
):
    client, _api = client_with(
        {
            "nodes/pve01/qemu/101/config": {
                "scsi0": "san-a:vm-101-disk-0,size=1024G",
                "lock": "backup",
            },
            "nodes/pve01/qemu/101/status/current": {"lock": "backup"},
        }
    )
    execution = ExecutionConfig(
        abort_on_failure=False,
        locks=LocksConfig(
            wait_timeout_seconds=100.0, poll_interval_seconds=30.0, on_timeout="abort"
        ),
    )
    fc = FakeClock(datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc))
    result = run(client, default_group(), (make_move(),), execution=execution, clock=fc)
    assert result.outcomes[0].status == "failed"
    assert result.outcomes[0].always_stop is True
    assert result.stopped_early is True


def test_wait_for_unlocked_helper_directly() -> None:
    client, _api = client_with({"nodes/pve01/qemu/101/status/current": {"lock": None}})
    fc = FakeClock(datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc))
    cleared, last_lock = _wait_for_unlocked(
        client, "pve01", 101, LocksConfig(wait_timeout_seconds=10.0), fc.clock()
    )
    assert cleared is True
    assert last_lock is None


# ------------------------------------------------------------------ pre-flight


def test_preflight_storage_changed_triggers_replan() -> None:
    client, _api = client_with(
        {"nodes/pve01/qemu/101/config": {"scsi0": "san-c:vm-101-disk-0,size=1024G"}}
    )
    result = run(client, default_group(), (make_move(),))
    assert result.outcomes[0].status == "replan_needed"
    assert "san-c" in result.outcomes[0].detail
    assert result.stopped_early is True


def test_preflight_snapshot_appeared_triggers_replan() -> None:
    client, _api = client_with(
        {"nodes/pve01/qemu/101/snapshot": [{"name": "current"}, {"name": "before-upgrade"}]}
    )
    result = run(client, default_group(), (make_move(),))
    assert result.outcomes[0].status == "replan_needed"
    assert "snapshot" in result.outcomes[0].detail


def test_preflight_vm_not_running_triggers_replan() -> None:
    client, _api = client_with(
        {"cluster/resources": [{"vmid": 101, "node": "pve01", "status": "stopped"}]}
    )
    result = run(client, default_group(), (make_move(),))
    assert result.outcomes[0].status == "replan_needed"
    assert "no longer running" in result.outcomes[0].detail


def test_preflight_vm_missing_from_cluster_resources_triggers_replan() -> None:
    client, _api = client_with({"cluster/resources": []})
    result = run(client, default_group(), (make_move(),))
    assert result.outcomes[0].status == "replan_needed"
    assert "no longer found" in result.outcomes[0].detail


def test_preflight_device_removed_from_config_triggers_replan() -> None:
    client, _api = client_with({"nodes/pve01/qemu/101/config": {}})
    result = run(client, default_group(), (make_move(),))
    assert result.outcomes[0].status == "replan_needed"
    assert "no longer present" in result.outcomes[0].detail


def test_preflight_vm_config_fetch_error_triggers_replan() -> None:
    def raise_error(**kwargs: object) -> dict[str, object]:
        raise PveApiError("connection refused")

    client, _api = client_with({"nodes/pve01/qemu/101/config": raise_error})
    result = run(client, default_group(), (make_move(),))
    assert result.outcomes[0].status == "replan_needed"
    assert "connection refused" in result.outcomes[0].detail


def test_preflight_tagged_for_exclusion_since_planning_triggers_replan() -> None:
    """Section 9.2 step 3: "confirm the VM is still running **and
    untagged for exclusion**" (REVIEW.md S-06) -- an operator tagging a
    VM `no-drs` between planning and execution must stop this move, not
    move it anyway."""
    client, _api = client_with(
        {
            "cluster/resources": [
                {"vmid": 101, "node": "pve01", "status": "running", "tags": "no-drs"}
            ]
        }
    )
    result = run(client, default_group(), (make_move(),))
    assert result.outcomes[0].status == "replan_needed"
    assert "excluded" in result.outcomes[0].detail


def test_preflight_vmid_added_to_exclude_list_since_planning_triggers_replan() -> None:
    client, _api = client_with({})
    exclude = ExcludeConfig(vmids=(101,))
    result = run(client, default_group(), (make_move(),), exclude=exclude)
    assert result.outcomes[0].status == "replan_needed"
    assert "excluded" in result.outcomes[0].detail


def test_preflight_helper_returns_lock_and_volid_on_success() -> None:
    client, _api = client_with({})
    result = _preflight(client, default_group().disks[0], make_move(), EXCLUDE)
    assert result.mismatch is None
    assert result.node == "pve01"
    assert result.volid == "san-a:vm-101-disk-0"


def test_vm_resource_returns_none_when_not_found() -> None:
    client, _api = client_with({"cluster/resources": []})
    assert _vm_resource(client, 999) is None


# --------------------------------------------------------- live transient check


def test_live_transient_check_failure_triggers_replan() -> None:
    # san-b nearly full: 7.9 TiB used of 8 TiB, leaves no room for the 1 TiB
    # move plus its 2x reserve.
    client, _api = client_with(
        {"nodes/pve01/storage/san-b/status": {"total": 8 * TIB, "used": round(7.9 * TIB)}}
    )
    result = run(client, default_group(), (make_move(),))
    assert result.outcomes[0].status == "replan_needed"
    assert "transient invariant" in result.outcomes[0].detail


def test_live_transient_check_helper_directly() -> None:
    client, _api = client_with({"nodes/pve01/storage/san-b/status": {"total": 8 * TIB, "used": 0}})
    target = make_storage("san-b", capacity_tib=8.0)
    disk = default_group().disks[0]
    assert _live_transient_check(client, "pve01", target, disk, 0, 0) is True

    client2, _api2 = client_with(
        {"nodes/pve01/storage/san-b/status": {"total": 8 * TIB, "used": round(7.9 * TIB)}}
    )
    assert _live_transient_check(client2, "pve01", target, disk, 0, 0) is False


# --------------------------------------------------------------------- failures


def test_task_failure_marks_failed_and_detects_orphans() -> None:
    client, _api = client_with(
        {
            f"nodes/pve01/tasks/{UPID}/status": {
                "status": "stopped",
                "exitstatus": "mirror failed",
            },
            "nodes/pve01/storage/san-b/content": [
                {"volid": "san-b:vm-101-disk-0", "vmid": 101},
            ],
        }
    )
    result = run(client, default_group(), (make_move(),))
    assert result.outcomes[0].status == "failed"
    assert result.outcomes[0].orphaned_volumes == ("san-b:vm-101-disk-0",)
    assert result.stopped_early is True  # abort_on_failure defaults True


def test_task_failure_continues_when_abort_on_failure_false() -> None:
    group = Group(
        name="g",
        storages=(make_storage("san-a"), make_storage("san-b")),
        disks=(make_disk("101:scsi0", 1.0, "san-a"), make_disk("102:scsi0", 1.0, "san-a")),
    )
    moves = (make_move(), make_move("102:scsi0", 102, "scsi0"))
    upid2 = "UPID:pve01:00001236:00ABCDEF:qmmove:102:root@pam:"
    client, _api = client_with(
        {
            "cluster/resources": [
                {"vmid": 101, "node": "pve01", "status": "running"},
                {"vmid": 102, "node": "pve01", "status": "running"},
            ],
            "nodes/pve01/qemu/102/config": {"scsi0": "san-a:vm-102-disk-0,size=1024G"},
            "nodes/pve01/qemu/102/snapshot": [{"name": "current"}],
            "nodes/pve01/qemu/102/status/current": {"lock": None},
            "nodes/pve01/qemu/102/move_disk": upid2,
            f"nodes/pve01/tasks/{upid2}/status": {"status": "stopped", "exitstatus": "OK"},
            f"nodes/pve01/tasks/{UPID}/status": {"status": "stopped", "exitstatus": "failed"},
            "nodes/pve01/storage/san-b/content": [],
        }
    )
    result = run(client, group, moves, execution=ExecutionConfig(abort_on_failure=False))
    assert [o.status for o in result.outcomes] == ["failed", "moved"]
    assert result.stopped_early is False


def test_orphan_detection_handles_a_pve_api_error_gracefully() -> None:
    def raise_error(**kwargs: object) -> list[dict[str, object]]:
        raise PveApiError("boom")

    client, _api = client_with({"nodes/pve01/storage/san-b/content": raise_error})
    orphans = _detect_orphan_volumes(client, "pve01", "san-b", 101)
    assert orphans == ()


def test_orphan_detection_finds_only_unreferenced_volumes_of_this_vm() -> None:
    client, _api = client_with(
        {
            "nodes/pve01/storage/san-b/content": [
                {"volid": "san-b:vm-101-disk-0", "vmid": 101},  # referenced -- not an orphan
                {"volid": "san-b:vm-101-disk-1", "vmid": 101},  # unreferenced -- orphan
                {"volid": "san-b:vm-102-disk-0", "vmid": 102},  # someone else's volume
            ],
            "nodes/pve01/qemu/101/config": {"scsi0": "san-b:vm-101-disk-0,size=1024G"},
        }
    )
    assert _detect_orphan_volumes(client, "pve01", "san-b", 101) == ("san-b:vm-101-disk-1",)


# --------------------------------------------------------------------- draining


def test_saferemove_source_never_releases_within_timeout_marks_draining() -> None:
    group = Group(
        name="g",
        storages=(
            make_storage("san-a", saferemove=True, saferemove_throughput=10 * (1 << 20)),
            make_storage("san-b"),
        ),
        disks=(make_disk("101:scsi0", 1.0, "san-a"),),
    )
    client, _api = client_with(
        {"nodes/pve01/storage/san-a/content": [{"volid": "san-a:vm-101-disk-0"}]}
    )
    execution = ExecutionConfig(
        poll_interval_seconds=3600.0,
        source_release=SourceReleaseConfig(wait=True, timeout_seconds=7200.0),
    )
    fc = FakeClock(datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc))
    result = run(client, group, (make_move(),), execution=execution, clock=fc)
    assert result.outcomes[0].status == "draining"
    assert "still running" in result.outcomes[0].detail
    assert result.stopped_early is False  # draining is not a failure


def test_a_draining_storage_is_excluded_as_a_source_for_later_moves_in_the_same_run() -> None:
    """Section 9.3: a source_release timeout "does not fail the run: mark
    the storage draining, exclude it as both source and target for the
    remainder of the run" (REVIEW.md S-05). The second move's own
    *source* is the storage the first move just left draining -- it must
    be skipped without ever reaching the API, not queued behind the
    storage-level lock the wipe holds."""
    group = Group(
        name="g",
        storages=(
            make_storage("san-a", saferemove=True, saferemove_throughput=10 * (1 << 20)),
            make_storage("san-b"),
            make_storage("san-c"),
        ),
        disks=(
            make_disk("101:scsi0", 1.0, "san-a"),
            make_disk("102:scsi0", 1.0, "san-a"),
        ),
    )
    client, api = client_with(
        {"nodes/pve01/storage/san-a/content": [{"volid": "san-a:vm-101-disk-0"}]}
    )
    execution = ExecutionConfig(
        poll_interval_seconds=3600.0,
        source_release=SourceReleaseConfig(wait=True, timeout_seconds=7200.0),
    )
    fc = FakeClock(datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc))
    moves = (
        make_move("101:scsi0", 101, "scsi0", from_storage="san-a", to_storage="san-b"),
        make_move("102:scsi0", 102, "scsi0", from_storage="san-a", to_storage="san-c"),
    )
    result = run(client, group, moves, execution=execution, clock=fc)
    assert result.outcomes[0].status == "draining"
    assert result.outcomes[1].status == "skipped"
    assert "san-a" in result.outcomes[1].detail
    assert "draining" in result.outcomes[1].detail
    assert result.stopped_early is False
    # Only the first move's move_disk was ever issued.
    assert len([c for c in api.calls if c[0] == "POST"]) == 1


def test_a_draining_storage_is_excluded_as_a_target_for_later_moves_in_the_same_run() -> None:
    """Same as above, except the second move's *target* -- not source --
    is the storage draining from the first move."""
    group = Group(
        name="g",
        storages=(
            make_storage("san-a", saferemove=True, saferemove_throughput=10 * (1 << 20)),
            make_storage("san-b"),
            make_storage("san-c"),
        ),
        disks=(
            make_disk("101:scsi0", 1.0, "san-a"),
            make_disk("102:scsi0", 1.0, "san-c"),
        ),
    )
    client, api = client_with(
        {"nodes/pve01/storage/san-a/content": [{"volid": "san-a:vm-101-disk-0"}]}
    )
    execution = ExecutionConfig(
        poll_interval_seconds=3600.0,
        source_release=SourceReleaseConfig(wait=True, timeout_seconds=7200.0),
    )
    fc = FakeClock(datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc))
    moves = (
        make_move("101:scsi0", 101, "scsi0", from_storage="san-a", to_storage="san-b"),
        make_move("102:scsi0", 102, "scsi0", from_storage="san-c", to_storage="san-a"),
    )
    result = run(client, group, moves, execution=execution, clock=fc)
    assert result.outcomes[0].status == "draining"
    assert result.outcomes[1].status == "skipped"
    assert "san-a" in result.outcomes[1].detail
    assert len([c for c in api.calls if c[0] == "POST"]) == 1


def test_saferemove_source_releases_before_timeout() -> None:
    group = Group(
        name="g",
        storages=(
            make_storage("san-a", saferemove=True, saferemove_throughput=10 * (1 << 20)),
            make_storage("san-b"),
        ),
        disks=(make_disk("101:scsi0", 1.0, "san-a"),),
    )
    calls = {"n": 0}

    def content(**kwargs: object) -> list[dict[str, object]]:
        calls["n"] += 1
        return [{"volid": "san-a:vm-101-disk-0"}] if calls["n"] < 2 else []

    client, _api = client_with({"nodes/pve01/storage/san-a/content": content})
    execution = ExecutionConfig(
        source_release=SourceReleaseConfig(wait=True, timeout_seconds=7200.0)
    )
    fc = FakeClock(datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc))
    result = run(client, group, (make_move(),), execution=execution, clock=fc)
    assert result.outcomes[0].status == "moved"


def test_source_release_wait_false_skips_the_drain_check_entirely() -> None:
    group = Group(
        name="g",
        storages=(
            make_storage("san-a", saferemove=True, saferemove_throughput=10 * (1 << 20)),
            make_storage("san-b"),
        ),
        disks=(make_disk("101:scsi0", 1.0, "san-a"),),
    )
    # No "nodes/pve01/storage/san-a/content" response at all -- if the drain
    # check were consulted despite `wait: false`, this would KeyError.
    client, _api = client_with({})
    execution = ExecutionConfig(source_release=SourceReleaseConfig(wait=False))
    result = run(client, group, (make_move(),), execution=execution)
    assert result.outcomes[0].status == "moved"


# --------------------------------------------------------- auto mode budgets


def test_max_migrations_per_run_stops_the_run_before_the_next_attempt() -> None:
    group = Group(
        name="g",
        storages=(make_storage("san-a"), make_storage("san-b")),
        disks=(make_disk("101:scsi0", 1.0, "san-a"), make_disk("102:scsi0", 1.0, "san-a")),
    )
    upid2 = "UPID:pve01:00001235:00ABCDEF:qmmove:102:root@pam:"
    client, api = client_with(
        {
            "cluster/resources": [
                {"vmid": 101, "node": "pve01", "status": "running"},
                {"vmid": 102, "node": "pve01", "status": "running"},
            ],
            "nodes/pve01/qemu/102/config": {"scsi0": "san-a:vm-102-disk-0,size=1024G"},
            "nodes/pve01/qemu/102/snapshot": [{"name": "current"}],
            "nodes/pve01/qemu/102/status/current": {"lock": None},
            "nodes/pve01/qemu/102/move_disk": upid2,
            f"nodes/pve01/tasks/{upid2}/status": {"status": "stopped", "exitstatus": "OK"},
        }
    )
    moves = (make_move(), make_move("102:scsi0", 102, "scsi0"))
    result = run(client, group, moves, max_migrations=1)
    assert [o.status for o in result.outcomes] == ["moved", "skipped"]
    assert "max_migrations_per_run" in result.outcomes[1].detail
    assert result.stopped_early is True
    assert result.stop_reason is not None and "max_migrations_per_run" in result.stop_reason
    # The second move never even reached a pre-flight check.
    assert not any("102" in c[1] for c in api.calls)


def test_max_migrations_per_run_of_zero_refuses_the_first_move_too() -> None:
    client, api = client_with({})
    result = run(client, default_group(), (make_move(),), max_migrations=0)
    assert result.outcomes[0].status == "skipped"
    assert api.calls == []


def test_deadline_refuses_a_move_that_cannot_finish_in_time() -> None:
    move_costs = {"101:scsi0": MoveCost("101:scsi0", 7200.0, 0.0, 7200.0, False, False)}
    fc = FakeClock(datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc))
    deadline = datetime(2026, 9, 6, 12, 30, 0, tzinfo=timezone.utc)  # only 30 min left
    client, api = client_with({})
    result = run(
        client,
        default_group(),
        (make_move(),),
        clock=fc,
        deadline=deadline,
        move_costs_by_key=move_costs,
    )
    assert result.outcomes[0].status == "skipped"
    assert "execution.time_windows" in result.outcomes[0].detail
    assert result.stopped_early is True
    assert api.calls == []


def test_deadline_allows_a_move_that_fits() -> None:
    move_costs = {"101:scsi0": MoveCost("101:scsi0", 1800.0, 0.0, 1800.0, False, False)}
    fc = FakeClock(datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc))
    deadline = datetime(2026, 9, 6, 13, 0, 0, tzinfo=timezone.utc)  # 1h left, needs 30m
    client, _api = client_with({})
    result = run(
        client,
        default_group(),
        (make_move(),),
        clock=fc,
        deadline=deadline,
        move_costs_by_key=move_costs,
    )
    assert result.outcomes[0].status == "moved"


def test_deadline_recheck_after_a_lock_wait_refuses_a_move_that_no_longer_fits() -> None:
    """Section 9.1: the pre-loop time-window check (above) only knows the
    answer as of *before* a VM-lock wait -- that wait can itself burn a
    large, unpredictable share of the remaining window. This move fits
    comfortably when first checked, but the lock takes long enough to
    clear that the *post*-wait re-check inside `_execute_one_move()` must
    refuse it before ever issuing `move_disk`."""
    calls = {"n": 0}

    def status_current(**kwargs: object) -> dict[str, object]:
        calls["n"] += 1
        return {"lock": "backup" if calls["n"] < 3 else None}

    client, api = client_with(
        {
            "nodes/pve01/qemu/101/config": {
                "scsi0": "san-a:vm-101-disk-0,size=1024G",
                "lock": "backup",
            },
            "nodes/pve01/qemu/101/status/current": status_current,
        }
    )
    execution = ExecutionConfig(
        locks=LocksConfig(wait_timeout_seconds=600.0, poll_interval_seconds=200.0)
    )
    move_costs = {"101:scsi0": MoveCost("101:scsi0", 60.0, 0.0, 60.0, False, False)}
    fc = FakeClock(datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc))
    # At t=0, 60s needed vs. 450s remaining: comfortably fits. But the
    # lock takes 400s (two 200s polls) to clear, leaving only 50s -- no
    # longer enough for the move's own 60s.
    deadline = datetime(2026, 9, 6, 12, 7, 30, tzinfo=timezone.utc)
    result = run(
        client,
        default_group(),
        (make_move(),),
        execution=execution,
        clock=fc,
        deadline=deadline,
        move_costs_by_key=move_costs,
    )
    assert result.outcomes[0].status == "skipped"
    assert "after waiting for the VM lock" in result.outcomes[0].detail
    assert not any("move_disk" in c[1] for c in api.calls)
    # REVIEW.md T-06: this is `_auto_budget_stop_outcome()`'s own "stop
    # cleanly, never skip this one and try a later move" policy, applying
    # just as much to a budget that went stale *during* the lock wait as
    # to the pre-flight check that function itself makes.
    assert result.outcomes[0].always_stop is True
    assert result.stopped_early is True
    assert result.stop_reason == result.outcomes[0].detail


def test_deadline_recheck_after_a_lock_wait_stops_the_whole_run_not_just_this_move() -> None:
    """REVIEW.md T-06's collateral bug: before the fix, this "skipped"
    outcome let the loop fall through to the *next* move instead of
    stopping the run -- contradicting `_auto_budget_stop_outcome()`'s own
    documented policy. A second, perfectly launchable move must never be
    attempted once the deadline goes stale for the first. Same lock-clears
    -after-two-polls setup as
    `test_deadline_recheck_after_a_lock_wait_refuses_a_move_that_no_longer_fits`,
    with a second, fully launchable move appended."""
    calls = {"n": 0}

    def status_current(**kwargs: object) -> dict[str, object]:
        calls["n"] += 1
        return {"lock": "backup" if calls["n"] < 3 else None}

    group = Group(
        name="g",
        storages=(make_storage("san-a"), make_storage("san-b")),
        disks=(make_disk("101:scsi0", 1.0, "san-a"), make_disk("102:scsi0", 1.0, "san-a")),
    )
    upid2 = "UPID:pve01:00001235:00ABCDEF:qmmove:102:root@pam:"
    client, api = client_with(
        {
            "cluster/resources": [
                {"vmid": 101, "node": "pve01", "status": "running"},
                {"vmid": 102, "node": "pve01", "status": "running"},
            ],
            "nodes/pve01/qemu/101/config": {
                "scsi0": "san-a:vm-101-disk-0,size=1024G",
                "lock": "backup",
            },
            "nodes/pve01/qemu/101/status/current": status_current,
            "nodes/pve01/qemu/102/config": {"scsi0": "san-a:vm-102-disk-0,size=1024G"},
            "nodes/pve01/qemu/102/snapshot": [{"name": "current"}],
            "nodes/pve01/qemu/102/status/current": {"lock": None},
            "nodes/pve01/qemu/102/move_disk": upid2,
            f"nodes/pve01/tasks/{upid2}/status": {"status": "stopped", "exitstatus": "OK"},
        }
    )
    execution = ExecutionConfig(
        locks=LocksConfig(wait_timeout_seconds=600.0, poll_interval_seconds=200.0)
    )
    move_costs = {
        "101:scsi0": MoveCost("101:scsi0", 60.0, 0.0, 60.0, False, False),
        "102:scsi0": MoveCost("102:scsi0", 60.0, 0.0, 60.0, False, False),
    }
    fc = FakeClock(datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc))
    # Same numbers as the single-move version: fits at t=0 (450s left, 60s
    # needed), but the 400s lock wait leaves only 50s -- no longer enough.
    deadline = datetime(2026, 9, 6, 12, 7, 30, tzinfo=timezone.utc)
    moves = (make_move(), make_move("102:scsi0", 102, "scsi0"))
    result = run(
        client,
        group,
        moves,
        execution=execution,
        clock=fc,
        deadline=deadline,
        move_costs_by_key=move_costs,
    )
    assert [o.status for o in result.outcomes] == ["skipped"]
    assert result.stopped_early is True
    # 102 was never even pre-flighted.
    assert not any("102" in c[1] for c in api.calls)


def test_lock_timeout_skip_does_not_consume_the_max_migrations_per_run_budget() -> None:
    """REVIEW.md T-06: a lock-timeout `"skipped"` outcome never issued
    `move_disk`, so it must not consume a slot of
    `execution.max_migrations_per_run` -- the second, real move must
    still be allowed to launch against a budget of `1`."""
    group = Group(
        name="g",
        storages=(make_storage("san-a"), make_storage("san-b")),
        disks=(make_disk("101:scsi0", 1.0, "san-a"), make_disk("102:scsi0", 1.0, "san-a")),
    )
    upid2 = "UPID:pve01:00001235:00ABCDEF:qmmove:102:root@pam:"
    client, api = client_with(
        {
            "cluster/resources": [
                {"vmid": 101, "node": "pve01", "status": "running"},
                {"vmid": 102, "node": "pve01", "status": "running"},
            ],
            "nodes/pve01/qemu/101/config": {
                "scsi0": "san-a:vm-101-disk-0,size=1024G",
                "lock": "backup",
            },
            "nodes/pve01/qemu/101/status/current": {"lock": "backup"},
            "nodes/pve01/qemu/102/config": {"scsi0": "san-a:vm-102-disk-0,size=1024G"},
            "nodes/pve01/qemu/102/snapshot": [{"name": "current"}],
            "nodes/pve01/qemu/102/status/current": {"lock": None},
            "nodes/pve01/qemu/102/move_disk": upid2,
            f"nodes/pve01/tasks/{upid2}/status": {"status": "stopped", "exitstatus": "OK"},
        }
    )
    execution = ExecutionConfig(
        locks=LocksConfig(wait_timeout_seconds=10.0, poll_interval_seconds=30.0, on_timeout="skip")
    )
    moves = (make_move(), make_move("102:scsi0", 102, "scsi0"))
    result = run(client, group, moves, execution=execution, max_migrations=1)
    assert [o.status for o in result.outcomes] == ["skipped", "moved"]
    assert result.outcomes[0].upid is None
    assert result.stopped_early is False


def test_deadline_with_no_cost_estimate_assumes_zero_duration() -> None:
    """A move missing from `move_costs_by_key` is never refused for lack
    of an estimate -- it is assumed to take no time at all."""
    fc = FakeClock(datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc))
    deadline = datetime(2026, 9, 6, 12, 0, 1, tzinfo=timezone.utc)  # 1 second left
    client, _api = client_with({})
    result = run(
        client, default_group(), (make_move(),), clock=fc, deadline=deadline, move_costs_by_key={}
    )
    assert result.outcomes[0].status == "moved"


def test_deadline_already_passed_refuses_immediately() -> None:
    fc = FakeClock(datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc))
    deadline = datetime(2026, 9, 6, 11, 0, 0, tzinfo=timezone.utc)  # already in the past
    client, api = client_with({})
    result = run(client, default_group(), (make_move(),), clock=fc, deadline=deadline)
    assert result.outcomes[0].status == "skipped"
    assert api.calls == []


# --------------------------------------------------------- crash-recovery hooks


def test_inflight_started_fires_right_after_move_disk_before_it_is_waited_on() -> None:
    """Section 13: `state.json` must learn about a UPID *before* this
    function goes on to wait for it -- a crash during that wait must still
    find the UPID recorded."""
    events: list[str] = []
    client, _api = client_with({})
    result = run(
        client,
        default_group(),
        (make_move(),),
        on_inflight_started=lambda upid: events.append(f"started:{upid}"),
        on_inflight_finished=lambda upid: events.append(f"finished:{upid}"),
    )
    assert result.outcomes[0].status == "moved"
    assert events == [f"started:{UPID}", f"finished:{UPID}"]


def test_inflight_finished_fires_for_a_failed_move_too() -> None:
    """Not only the happy path -- a `move_disk` task that itself fails
    still finished (`exitstatus` is known), so `state.json` must stop
    tracking it exactly as promptly as a successful one."""
    events: list[str] = []
    client, _api = client_with(
        {
            f"nodes/pve01/tasks/{UPID}/status": {"status": "stopped", "exitstatus": "some error"},
            "nodes/pve01/storage/san-b/content": [],
        }
    )
    result = run(
        client,
        default_group(),
        (make_move(),),
        on_inflight_started=lambda upid: events.append(f"started:{upid}"),
        on_inflight_finished=lambda upid: events.append(f"finished:{upid}"),
    )
    assert result.outcomes[0].status == "failed"
    assert events == [f"started:{UPID}", f"finished:{UPID}"]


def test_inflight_finished_fires_for_a_draining_move_too() -> None:
    """A "draining" source is no longer tracked by this UPID at all (only
    by its own content-listing poll, see `state.without_inflight_upid()`'s
    own docstring) -- cleared here exactly as promptly as a `"moved"`
    one, not left recorded until the source actually releases."""
    saferemove_group = Group(
        name="fc-tier1",
        storages=(make_storage("san-a", saferemove=True), make_storage("san-b")),
        disks=(make_disk("101:scsi0", 1.0, "san-a"),),
    )
    events: list[str] = []
    client, _api = client_with(
        {"nodes/pve01/storage/san-a/content": [{"volid": "san-a:vm-101-disk-0", "vmid": 101}]}
    )
    execution = ExecutionConfig(source_release=SourceReleaseConfig(timeout_seconds=0.0))
    result = run(
        client,
        saferemove_group,
        (make_move(),),
        execution=execution,
        on_inflight_started=lambda upid: events.append(f"started:{upid}"),
        on_inflight_finished=lambda upid: events.append(f"finished:{upid}"),
    )
    assert result.outcomes[0].status == "draining"
    assert events == [f"started:{UPID}", f"finished:{UPID}"]


def test_no_inflight_callback_needed_for_dry_run() -> None:
    """`dry-run` never calls `move_disk` at all -- the callbacks must
    simply never fire, not be required."""
    events: list[str] = []
    client, _api = client_with({})
    result = run(
        client,
        default_group(),
        (make_move(),),
        mode="dry-run",
        on_inflight_started=lambda upid: events.append(f"started:{upid}"),
        on_inflight_finished=lambda upid: events.append(f"finished:{upid}"),
    )
    assert result.outcomes[0].status == "would_move"
    assert events == []


# ------------------------------------------------------- concurrent execution
#
# Two disjoint moves (different vmids, different sources, different
# targets) so `execution.max_concurrent_per_storage`'s default of `1`
# never blocks them from running together -- each test below overrides
# only what it needs to exercise (a shared storage, a tight target, a
# locked VM, ...).

UPID_A = "UPID:pve01:00001234:00ABCDEF:qmmove:201:root@pam:"
UPID_B = "UPID:pve01:00001235:00ABCDEF:qmmove:202:root@pam:"


def two_source_two_target_group() -> Group:
    return Group(
        name="fc-tier1",
        storages=(
            make_storage("san-a"),
            make_storage("san-b"),
            make_storage("san-c"),
            make_storage("san-d"),
        ),
        disks=(
            make_disk("201:scsi0", 1.0, "san-a"),
            make_disk("202:scsi0", 1.0, "san-b"),
        ),
    )


def two_disjoint_moves() -> tuple[ScheduledMove, ...]:
    return (
        make_move("201:scsi0", 201, "scsi0", "san-a", "san-c"),
        make_move("202:scsi0", 202, "scsi0", "san-b", "san-d"),
    )


def concurrent_client_with(overrides: dict[str, object]) -> tuple[PveClient, FakeProxmoxResource]:
    responses: dict[str, object] = {
        "cluster/resources": [
            {"vmid": 201, "node": "pve01", "status": "running"},
            {"vmid": 202, "node": "pve01", "status": "running"},
        ],
        "nodes/pve01/qemu/201/config": {"scsi0": "san-a:vm-201-disk-0,size=1024G"},
        "nodes/pve01/qemu/201/snapshot": [{"name": "current"}],
        "nodes/pve01/qemu/201/status/current": {"lock": None},
        "nodes/pve01/qemu/201/move_disk": UPID_A,
        f"nodes/pve01/tasks/{UPID_A}/status": {"status": "stopped", "exitstatus": "OK"},
        "nodes/pve01/qemu/202/config": {"scsi0": "san-b:vm-202-disk-0,size=1024G"},
        "nodes/pve01/qemu/202/snapshot": [{"name": "current"}],
        "nodes/pve01/qemu/202/status/current": {"lock": None},
        "nodes/pve01/qemu/202/move_disk": UPID_B,
        f"nodes/pve01/tasks/{UPID_B}/status": {"status": "stopped", "exitstatus": "OK"},
        "nodes/pve01/storage/san-c/status": {"total": 8 * TIB, "used": 0},
        "nodes/pve01/storage/san-d/status": {"total": 8 * TIB, "used": 0},
    }
    responses.update(overrides)
    api = fake_api(responses)
    return PveClient(api), api


def run_concurrent(
    client: PveClient,
    group: Group,
    moves: tuple[ScheduledMove, ...],
    execution: ExecutionConfig,
    clock: FakeClock | None = None,
    deadline: datetime | None = None,
    move_costs_by_key: dict[str, MoveCost] | None = None,
    max_migrations: int | None = None,
    on_inflight_started: object = None,
    on_inflight_finished: object = None,
) -> ExecutionResult:
    schedule_result = ScheduleResult(
        order=moves, deadlocked=(), final_assignment={d.key: d.current_storage for d in group.disks}
    )
    fc = clock or FakeClock(datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc))
    return execute_plan(
        client,
        group,
        schedule_result,
        MIGRATION,
        execution,
        0,
        "auto",
        EXCLUDE,
        clock=fc.clock(),
        deadline=deadline,
        move_costs_by_key=move_costs_by_key,
        max_migrations=max_migrations,
        on_inflight_started=on_inflight_started,  # type: ignore[arg-type]
        on_inflight_finished=on_inflight_finished,  # type: ignore[arg-type]
    )


def test_execute_plan_uses_the_sequential_path_at_default_concurrency() -> None:
    """`ExecutionConfig()`'s own defaults (both caps `1`) must dispatch to
    the strictly-sequential executor, not the concurrent one -- this is
    what makes every pre-existing test in this file (all written before
    concurrency existed) a real regression check on `execute_plan()`'s
    dispatch, not just on `_execute_sequential()` in isolation."""
    client, api = client_with({})
    result = run(client, default_group(), (make_move(),))
    assert result.outcomes[0].status == "moved"
    # Exactly the calls the sequential path always made -- confirms this
    # request never touched the concurrent machinery's own extra
    # `storage_status()` read inside `_launch_decision()` (the sequential
    # path's own `_live_transient_check()` already covers that).
    assert [c[1] for c in api.calls].count("nodes/pve01/storage/san-b/status") == 1


def test_concurrent_launches_both_moves_before_either_resolves() -> None:
    """The defining property of concurrency: `move_disk` for the second
    move is issued while the first is still running, not after it
    completes -- `task_status` reports 201's task as still `"running"` for
    its first poll, only `"stopped"` from the second poll on, so 202 can
    only have launched *during* that window if this test's own move_disk
    call for it appears before 201's task ever resolves."""
    poll_count = {"n": 0}

    def upid_a_status(**kwargs: object) -> dict[str, object]:
        poll_count["n"] += 1
        return (
            {"status": "running"}
            if poll_count["n"] == 1
            else {"status": "stopped", "exitstatus": "OK"}
        )

    client, api = concurrent_client_with({f"nodes/pve01/tasks/{UPID_A}/status": upid_a_status})
    execution = ExecutionConfig(max_concurrent_migrations=2)
    result = run_concurrent(client, two_source_two_target_group(), two_disjoint_moves(), execution)

    assert {o.disk_key: o.status for o in result.outcomes} == {
        "201:scsi0": "moved",
        "202:scsi0": "moved",
    }
    move_disk_calls = [c[1] for c in api.calls if c[1].endswith("/move_disk")]
    b_move_disk_call = next(
        i for i, c in enumerate(api.calls) if c[1] == "nodes/pve01/qemu/202/move_disk"
    )
    a_status_calls_before_b = sum(
        1 for c in api.calls[:b_move_disk_call] if c[1] == f"nodes/pve01/tasks/{UPID_A}/status"
    )
    assert move_disk_calls == ["nodes/pve01/qemu/201/move_disk", "nodes/pve01/qemu/202/move_disk"]
    # 202's move_disk was issued after only 201's *first* status poll (the
    # one that still reported "running") -- i.e. before 201 had any
    # chance to be known-finished.
    assert a_status_calls_before_b == 1


def test_concurrent_inflight_callbacks_fire_independently_per_move() -> None:
    """Each move's own UPID reaches both callbacks correctly attributed --
    `test_concurrent_launches_both_moves_before_either_resolves` already
    covers the overlap property itself; this test's own fixture resolves
    each move on its first poll (no artificial delay), so it would not
    demonstrate overlap even if it asserted one."""
    events: list[str] = []
    client, _api = concurrent_client_with({})
    execution = ExecutionConfig(max_concurrent_migrations=2)
    result = run_concurrent(
        client,
        two_source_two_target_group(),
        two_disjoint_moves(),
        execution,
        on_inflight_started=lambda upid: events.append(f"started:{upid}"),
        on_inflight_finished=lambda upid: events.append(f"finished:{upid}"),
    )
    assert all(o.status == "moved" for o in result.outcomes)
    assert set(events) == {
        f"started:{UPID_A}",
        f"finished:{UPID_A}",
        f"started:{UPID_B}",
        f"finished:{UPID_B}",
    }
    # Each UPID's own start strictly precedes its own finish.
    assert events.index(f"started:{UPID_A}") < events.index(f"finished:{UPID_A}")
    assert events.index(f"started:{UPID_B}") < events.index(f"finished:{UPID_B}")


def test_concurrent_max_concurrent_per_storage_serializes_a_shared_target() -> None:
    """Two otherwise-independent moves landing on the *same* target: even
    with `max_concurrent_migrations=2`, the default
    `max_concurrent_per_storage: 1` means the second cannot launch until
    the first resolves."""
    moves = (
        make_move("201:scsi0", 201, "scsi0", "san-a", "san-c"),
        make_move("202:scsi0", 202, "scsi0", "san-b", "san-c"),
    )
    client, api = concurrent_client_with({})
    execution = ExecutionConfig(max_concurrent_migrations=2)
    result = run_concurrent(client, two_source_two_target_group(), moves, execution)
    assert [o.status for o in result.outcomes] == ["moved", "moved"]
    # 202 could not have launched before 201's task resolved: its
    # move_disk call must come after 201's task_status ever reports
    # "stopped".
    move_disk_calls = [
        i for i, c in enumerate(api.calls) if c[1] == "nodes/pve01/qemu/202/move_disk"
    ]
    a_status_calls = [
        i for i, c in enumerate(api.calls) if c[1] == f"nodes/pve01/tasks/{UPID_A}/status"
    ]
    assert move_disk_calls[0] > a_status_calls[0]


def test_concurrent_transient_invariant_blocks_a_second_move_onto_a_tight_target() -> None:
    """Section 8.1's generalized invariant, live: san-c has only 2 TiB of
    headroom (capacity 3 TiB, nothing used yet, reserve_factor 2.0 ->
    after one 1 TiB charge, required reserve is already 2 TiB, leaving no
    room for a second 1 TiB charge onto the *same* storage). 201's task
    is made to take one extra poll to resolve, so 202 is evaluated for
    launch *while* 201 is still occupying its charge against san-c --
    without that, 201 would already have finished and freed its charge
    before 202 is ever considered, and this test would prove nothing."""
    poll_count = {"n": 0}

    def upid_a_status(**kwargs: object) -> dict[str, object]:
        poll_count["n"] += 1
        return (
            {"status": "running"}
            if poll_count["n"] == 1
            else {"status": "stopped", "exitstatus": "OK"}
        )

    moves = (
        make_move("201:scsi0", 201, "scsi0", "san-a", "san-c"),
        make_move("202:scsi0", 202, "scsi0", "san-b", "san-c"),
    )
    group = Group(
        name="fc-tier1",
        storages=(
            make_storage("san-a"),
            make_storage("san-b"),
            make_storage("san-c", capacity_tib=3.0),
        ),
        disks=(make_disk("201:scsi0", 1.0, "san-a"), make_disk("202:scsi0", 1.0, "san-b")),
    )
    # max_concurrent_per_storage raised so the per-storage-count gate does
    # not mask the transient-invariant gate this test actually targets.
    # The live `storage_status()` reply must match the model's own 3 TiB
    # capacity too -- `concurrent_client_with()`'s own default (8 TiB) is
    # for its own two-disjoint-move fixture, not this test's tight target.
    client, _api = concurrent_client_with(
        {
            f"nodes/pve01/tasks/{UPID_A}/status": upid_a_status,
            "nodes/pve01/storage/san-c/status": {"total": 3 * TIB, "used": 0},
        }
    )
    execution = ExecutionConfig(max_concurrent_migrations=2, max_concurrent_per_storage=2)
    result = run_concurrent(client, group, moves, execution)
    outcomes_by_key = {o.disk_key: o for o in result.outcomes}
    assert outcomes_by_key["201:scsi0"].status == "moved"
    assert outcomes_by_key["202:scsi0"].status == "replan_needed"
    assert "transient invariant" in outcomes_by_key["202:scsi0"].detail


def test_concurrent_strict_fifo_does_not_skip_a_locked_head() -> None:
    """The deliberate simplification documented in `_execute_concurrent()`'s
    own docstring: 201 (the head of the queue) is locked for its first
    pre-flight re-check and clears by its second -- 202 could have
    launched immediately on its own merit while 201 was still locked, but
    this executor never considers a candidate behind an unresolved head,
    so 202's `move_disk` must not appear before 201's own."""
    config_calls = {"n": 0}

    def vm_201_config(**kwargs: object) -> dict[str, object]:
        config_calls["n"] += 1
        config: dict[str, object] = {"scsi0": "san-a:vm-201-disk-0,size=1024G"}
        if config_calls["n"] == 1:
            config["lock"] = "backup"
        return config

    client, api = concurrent_client_with({"nodes/pve01/qemu/201/config": vm_201_config})
    execution = ExecutionConfig(
        max_concurrent_migrations=2,
        locks=LocksConfig(wait_timeout_seconds=600.0, poll_interval_seconds=5.0),
    )
    result = run_concurrent(client, two_source_two_target_group(), two_disjoint_moves(), execution)
    outcomes_by_key = {o.disk_key: o for o in result.outcomes}
    assert outcomes_by_key["201:scsi0"].status == "moved"
    assert outcomes_by_key["202:scsi0"].status == "moved"
    a_move_disk_call = next(
        i for i, c in enumerate(api.calls) if c[1] == "nodes/pve01/qemu/201/move_disk"
    )
    b_move_disk_call = next(
        i for i, c in enumerate(api.calls) if c[1] == "nodes/pve01/qemu/202/move_disk"
    )
    assert a_move_disk_call < b_move_disk_call


def test_concurrent_max_migrations_stops_launching_but_drains_inflight() -> None:
    """`max_migrations=1`: 201 is allowed to launch (bringing the count to
    the cap), 202 is refused *before* ever being pre-flighted -- but 201,
    already in flight, is still polled to completion and reported, not
    abandoned."""
    client, api = concurrent_client_with({})
    execution = ExecutionConfig(max_concurrent_migrations=2)
    result = run_concurrent(
        client, two_source_two_target_group(), two_disjoint_moves(), execution, max_migrations=1
    )
    outcomes_by_key = {o.disk_key: o for o in result.outcomes}
    assert outcomes_by_key["201:scsi0"].status == "moved"
    assert outcomes_by_key["202:scsi0"].status == "skipped"
    assert "max_migrations_per_run" in outcomes_by_key["202:scsi0"].detail
    assert result.stopped_early is True
    assert not any(c[1] == "nodes/pve01/qemu/202/move_disk" for c in api.calls)


def test_concurrent_deadline_stops_launching_but_drains_inflight() -> None:
    fc = FakeClock(datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc))
    deadline = datetime(2026, 9, 6, 12, 0, 1, tzinfo=timezone.utc)
    move_costs = {
        "201:scsi0": MoveCost("201:scsi0", 0.0, 0.0, 0.0, False, False),
        "202:scsi0": MoveCost("202:scsi0", 3600.0, 0.0, 3600.0, False, False),
    }
    client, api = concurrent_client_with({})
    execution = ExecutionConfig(max_concurrent_migrations=2)
    result = run_concurrent(
        client,
        two_source_two_target_group(),
        two_disjoint_moves(),
        execution,
        clock=fc,
        deadline=deadline,
        move_costs_by_key=move_costs,
    )
    statuses = {o.disk_key: o.status for o in result.outcomes}
    assert statuses["201:scsi0"] == "moved"
    assert statuses["202:scsi0"] == "skipped"
    assert result.stopped_early is True
    assert not any(c[1] == "nodes/pve01/qemu/202/move_disk" for c in api.calls)


def test_concurrent_failed_move_with_abort_on_failure_stops_launching_but_drains_inflight() -> None:
    """201 fails outright (its very first poll already reports the task
    stopped with a non-OK exitstatus, so there is no window in which 202
    could have already launched concurrently) -- `execution.abort_on_failure`
    means 202 is never even pre-flighted, exactly like
    `_execute_sequential()`'s own early `return` leaves every move after
    the one that failed completely unreported, not merely skipped."""
    client, api = concurrent_client_with(
        {
            f"nodes/pve01/tasks/{UPID_A}/status": {
                "status": "stopped",
                "exitstatus": "mirror failed",
            },
            "nodes/pve01/storage/san-c/content": [],
        }
    )
    execution = ExecutionConfig(max_concurrent_migrations=2, abort_on_failure=True)
    result = run_concurrent(client, two_source_two_target_group(), two_disjoint_moves(), execution)
    assert [o.disk_key for o in result.outcomes] == ["201:scsi0"]
    assert result.outcomes[0].status == "failed"
    assert result.stopped_early is True
    assert not any(c[1] == "nodes/pve01/qemu/202/move_disk" for c in api.calls)


def test_concurrent_draining_source_excludes_a_later_move_off_the_same_source() -> None:
    """A `saferemove` source that goes `"draining"` is excluded as both
    source and target for the rest of *this* run (section 9.3) --
    `_drained_skip_outcome()` is reused unchanged by the concurrent
    executor's own `_advance_pending()`, so 202 (sharing 201's source,
    san-a) is skipped once 201 resolves `"draining"`, not launched once
    the concurrency slot frees up. This is a stronger exclusion than the
    concurrency-slot bookkeeping alone would give: even after 201's own
    `_InflightMove` is gone from the in-flight set (freeing the slot),
    202 still cannot use the same source this run."""
    moves = (
        make_move("201:scsi0", 201, "scsi0", "san-a", "san-c"),
        make_move("202:scsi0", 202, "scsi0", "san-a", "san-d"),
    )
    group = Group(
        name="fc-tier1",
        storages=(
            make_storage("san-a", saferemove=True),
            make_storage("san-c"),
            make_storage("san-d"),
        ),
        disks=(make_disk("201:scsi0", 1.0, "san-a"), make_disk("202:scsi0", 1.0, "san-a")),
    )
    client, _api = concurrent_client_with(
        {
            "cluster/resources": [
                {"vmid": 201, "node": "pve01", "status": "running"},
                {"vmid": 202, "node": "pve01", "status": "running"},
            ],
            "nodes/pve01/qemu/202/config": {"scsi0": "san-a:vm-202-disk-0,size=1024G"},
            "nodes/pve01/storage/san-a/content": [
                {"volid": "san-a:vm-201-disk-0", "vmid": 201},
            ],
        }
    )
    execution = ExecutionConfig(
        max_concurrent_migrations=2,
        source_release=SourceReleaseConfig(timeout_seconds=0.0),
    )
    result = run_concurrent(client, group, moves, execution)
    outcomes_by_key = {o.disk_key: o for o in result.outcomes}
    assert outcomes_by_key["201:scsi0"].status == "draining"
    assert outcomes_by_key["202:scsi0"].status == "skipped"
    assert "still draining" in outcomes_by_key["202:scsi0"].detail


def test_concurrent_lock_timeout_with_abort_semantics_fails_and_stops() -> None:
    """`execution.locks.on_timeout: abort` under concurrency: the locked
    head never clears, resolves `"failed"` with `always_stop`, and 202
    (never even pre-flighted) is abandoned entirely -- the non-blocking
    counterpart to `_execute_one_move()`'s own identical lock-timeout
    -abort path."""
    client, api = concurrent_client_with(
        {
            "nodes/pve01/qemu/201/config": {
                "scsi0": "san-a:vm-201-disk-0,size=1024G",
                "lock": "backup",
            }
        }
    )
    execution = ExecutionConfig(
        max_concurrent_migrations=2,
        locks=LocksConfig(wait_timeout_seconds=5.0, poll_interval_seconds=10.0, on_timeout="abort"),
    )
    result = run_concurrent(client, two_source_two_target_group(), two_disjoint_moves(), execution)
    assert [o.disk_key for o in result.outcomes] == ["201:scsi0"]
    assert result.outcomes[0].status == "failed"
    assert result.outcomes[0].always_stop is True
    assert "still locked" in result.outcomes[0].detail
    assert result.stopped_early is True
    assert not any(c[1] == "nodes/pve01/qemu/202/move_disk" for c in api.calls)


def test_concurrent_lock_timeout_with_skip_semantics_continues_to_the_next_move() -> None:
    """`execution.locks.on_timeout: skip` (the default): the locked head
    times out `"skipped"`, not `"failed"`, and -- unlike the abort case --
    the queue simply advances to 202, which launches normally."""
    client, api = concurrent_client_with(
        {
            "nodes/pve01/qemu/201/config": {
                "scsi0": "san-a:vm-201-disk-0,size=1024G",
                "lock": "backup",
            }
        }
    )
    execution = ExecutionConfig(
        max_concurrent_migrations=2,
        locks=LocksConfig(wait_timeout_seconds=5.0, poll_interval_seconds=10.0, on_timeout="skip"),
    )
    result = run_concurrent(client, two_source_two_target_group(), two_disjoint_moves(), execution)
    outcomes_by_key = {o.disk_key: o for o in result.outcomes}
    assert outcomes_by_key["201:scsi0"].status == "skipped"
    assert outcomes_by_key["201:scsi0"].always_stop is False
    assert outcomes_by_key["202:scsi0"].status == "moved"
    assert result.stopped_early is False
    assert any(c[1] == "nodes/pve01/qemu/202/move_disk" for c in api.calls)


def test_concurrent_preflight_mismatch_replans_and_stops() -> None:
    """201 vanished from `cluster/resources` since this plan was built (a
    live-migration or deletion) -- the concurrent executor's own
    `_launch_decision()` re-checks this exactly like
    `_execute_one_move()`'s `_preflight()` always has, and stops the run
    with `"replan_needed"`, abandoning 202 unreported."""
    client, api = concurrent_client_with(
        {"cluster/resources": [{"vmid": 202, "node": "pve01", "status": "running"}]}
    )
    execution = ExecutionConfig(max_concurrent_migrations=2)
    result = run_concurrent(client, two_source_two_target_group(), two_disjoint_moves(), execution)
    assert [o.disk_key for o in result.outcomes] == ["201:scsi0"]
    assert result.outcomes[0].status == "replan_needed"
    assert "no longer found" in result.outcomes[0].detail
    assert result.stopped_early is True
    assert not any(c[1] == "nodes/pve01/qemu/202/move_disk" for c in api.calls)


def test_concurrent_replan_mismatch_can_land_before_a_still_inflight_moves_outcome() -> None:
    """REVIEW.md T-01, reproduced directly: 202 vanished from
    `cluster/resources` (simulating a live-migration/deletion since the
    plan was built), but 201 -- already launched and still `"running"` --
    has not resolved yet when 202's pre-flight is checked one cycle later.
    The concurrent executor cannot return the moment 202's mismatch is
    found (201 is still in flight and must be polled to its own
    conclusion first), so `outcomes` ends up `[202's replan_needed, 201's
    moved]` -- the mismatch is *not* last. `cli._run_auto_group()`'s own
    `needs_replan` check must key off membership, not position, for a
    caller to ever notice this outcome and re-plan (T-01's fix); this test
    only pins down that the executor really does produce outcomes in this
    order, independent of that fix."""
    poll_count = {"n": 0}

    def upid_a_status(**kwargs: object) -> dict[str, object]:
        poll_count["n"] += 1
        return (
            {"status": "running"}
            if poll_count["n"] == 1
            else {"status": "stopped", "exitstatus": "OK"}
        )

    client, api = concurrent_client_with(
        {
            # 202 is simply absent -- vanished since this plan was built.
            "cluster/resources": [{"vmid": 201, "node": "pve01", "status": "running"}],
            f"nodes/pve01/tasks/{UPID_A}/status": upid_a_status,
        }
    )
    execution = ExecutionConfig(max_concurrent_migrations=2)
    result = run_concurrent(client, two_source_two_target_group(), two_disjoint_moves(), execution)

    assert [(o.disk_key, o.status) for o in result.outcomes] == [
        ("202:scsi0", "replan_needed"),
        ("201:scsi0", "moved"),
    ]
    assert result.stopped_early is True
    assert not any(c[1] == "nodes/pve01/qemu/202/move_disk" for c in api.calls)


def test_concurrent_waits_for_a_free_slot_before_launching_a_third_move() -> None:
    """Three fully-disjoint moves, `max_concurrent_migrations=2`: the
    third cannot even be pre-flighted while both slots are occupied.
    Every poll cycle resolves at most one move at a time here (each
    of 201/202 needs three polls, staggered so neither ever resolves on
    the exact same cycle as the other) -- without that staggering, a
    slot freed by polling would always be immediately available to the
    *same* cycle's launch attempt, and the "no free slot, wait" branch
    this test targets would never actually be exercised."""
    poll_counts = {"a": 0, "b": 0}

    def delayed_status(counter_key: str) -> object:
        def status(**kwargs: object) -> dict[str, object]:
            poll_counts[counter_key] += 1
            return (
                {"status": "running"}
                if poll_counts[counter_key] < 3
                else {"status": "stopped", "exitstatus": "OK"}
            )

        return status

    group = Group(
        name="fc-tier1",
        storages=(
            make_storage("san-a"),
            make_storage("san-b"),
            make_storage("san-c"),
            make_storage("san-d"),
            make_storage("san-e"),
            make_storage("san-f"),
        ),
        disks=(
            make_disk("201:scsi0", 1.0, "san-a"),
            make_disk("202:scsi0", 1.0, "san-b"),
            make_disk("203:scsi0", 1.0, "san-e"),
        ),
    )
    moves = (
        make_move("201:scsi0", 201, "scsi0", "san-a", "san-c"),
        make_move("202:scsi0", 202, "scsi0", "san-b", "san-d"),
        make_move("203:scsi0", 203, "scsi0", "san-e", "san-f"),
    )
    upid_c = "UPID:pve01:00001236:00ABCDEF:qmmove:203:root@pam:"
    client, api = concurrent_client_with(
        {
            "cluster/resources": [
                {"vmid": 201, "node": "pve01", "status": "running"},
                {"vmid": 202, "node": "pve01", "status": "running"},
                {"vmid": 203, "node": "pve01", "status": "running"},
            ],
            "nodes/pve01/qemu/203/config": {"scsi0": "san-e:vm-203-disk-0,size=1024G"},
            "nodes/pve01/qemu/203/snapshot": [{"name": "current"}],
            "nodes/pve01/qemu/203/status/current": {"lock": None},
            "nodes/pve01/qemu/203/move_disk": upid_c,
            f"nodes/pve01/tasks/{upid_c}/status": {"status": "stopped", "exitstatus": "OK"},
            "nodes/pve01/storage/san-f/status": {"total": 8 * TIB, "used": 0},
            f"nodes/pve01/tasks/{UPID_A}/status": delayed_status("a"),
            f"nodes/pve01/tasks/{UPID_B}/status": delayed_status("b"),
        }
    )
    execution = ExecutionConfig(max_concurrent_migrations=2)
    result = run_concurrent(client, group, moves, execution)
    assert {o.disk_key: o.status for o in result.outcomes} == {
        "201:scsi0": "moved",
        "202:scsi0": "moved",
        "203:scsi0": "moved",
    }
    # 203 is never even pre-flighted (`_advance_pending()`'s own free-slot
    # check returns before ever calling `_launch_decision()`) until a slot
    # has actually freed -- i.e. not before 201's task was polled at least
    # once.
    first_203_config_call = next(
        i for i, c in enumerate(api.calls) if c[1] == "nodes/pve01/qemu/203/config"
    )
    first_a_status_call = next(
        i for i, c in enumerate(api.calls) if c[1] == f"nodes/pve01/tasks/{UPID_A}/status"
    )
    assert first_a_status_call < first_203_config_call


def test_concurrent_orphan_detection_after_a_move_fails_while_polled() -> None:
    """A `"failed"` outcome resolved by polling (not at launch time) still
    runs the section 9.4 orphan check -- `_poll_inflight_once()`'s own
    counterpart to `_execute_one_move()`'s identical check."""
    client, _api = concurrent_client_with(
        {
            f"nodes/pve01/tasks/{UPID_A}/status": {
                "status": "stopped",
                "exitstatus": "mirror failed",
            },
            "nodes/pve01/storage/san-c/content": [{"volid": "san-c:vm-201-disk-0", "vmid": 201}],
        }
    )
    execution = ExecutionConfig(max_concurrent_migrations=2)
    result = run_concurrent(client, two_source_two_target_group(), two_disjoint_moves(), execution)
    assert result.outcomes[0].status == "failed"
    assert result.outcomes[0].orphaned_volumes == ("san-c:vm-201-disk-0",)
