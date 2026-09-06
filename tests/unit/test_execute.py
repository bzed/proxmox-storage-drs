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
