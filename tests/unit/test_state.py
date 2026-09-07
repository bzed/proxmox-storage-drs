# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Persistent state at ``state.path``. See proxmox_storage_drs/state.py.

Every test here writes only under ``tmp_path`` (`.agents/testing.md`: "no
writes outside `tmp_path`. Never to `state.json`") -- the two permission
-failure tests are the deliberate exception, pointed at a path this test
user (`bzed`, not root) cannot create, never at a real file.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from proxmox_storage_drs.exceptions import StateError
from proxmox_storage_drs.state import (
    Cooldowns,
    LastBalance,
    LockInfo,
    State,
    _pid_alive,
    acquire_lock,
    active_disk_cooldowns,
    active_storage_cooldowns,
    cooldown_remaining_seconds,
    disk_state_key,
    empty_state,
    load_state,
    load_vector_for_group,
    release_lock,
    save_locked_state,
    save_state_atomic,
    storage_state_key,
    with_recorded_balance,
    with_recorded_cooldown,
)

# --------------------------------------------------------------------- keys


def test_disk_state_key_matches_section_11_2_shape() -> None:
    assert disk_state_key("fc-tier1", 101, "scsi0") == "fc-tier1:101:scsi0"


def test_storage_state_key_matches_section_11_2_shape() -> None:
    assert storage_state_key("fc-tier1", "san-b") == "fc-tier1:san-b"


# ------------------------------------------------------------- empty_state


def test_empty_state_has_no_lock_no_balance_nothing_in_flight() -> None:
    state = empty_state()
    assert state.schema_version == 1
    assert state.lock is None
    assert state.last_balance == LastBalance(at=None, load_vector={})
    assert state.cooldowns == Cooldowns(disk={}, storage={})
    assert state.inflight_upids == ()
    assert state.staged_disks == ()


# --------------------------------------------------------------- load_state


def test_load_state_on_a_missing_file_is_silently_empty(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        state = load_state(str(tmp_path / "does-not-exist" / "state.json"))
    assert state == empty_state()
    assert caplog.records == []  # missing is the ordinary first-run case, not a warning


def test_load_state_on_corrupt_json_degrades_and_warns(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    path = tmp_path / "state.json"
    path.write_text("{not json", encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        state = load_state(str(path))
    assert state == empty_state()
    assert any(
        "state_corrupt" in r.message or "not valid JSON" in r.message for r in caplog.records
    )


def test_load_state_on_unsupported_schema_version_degrades_and_warns(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"schema_version": 999}), encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        state = load_state(str(path))
    assert state == empty_state()
    assert any(r.levelno == logging.WARNING for r in caplog.records)


@pytest.mark.skipif(os.geteuid() == 0, reason="root can read anything")
def test_load_state_on_an_unreadable_file_degrades_and_warns(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    path = tmp_path / "state.json"
    path.write_text("{}", encoding="utf-8")
    path.chmod(0)
    try:
        with caplog.at_level(logging.WARNING):
            state = load_state(str(path))
        assert state == empty_state()
        assert any(r.levelno == logging.WARNING for r in caplog.records)
    finally:
        path.chmod(0o600)  # tmp_path cleanup needs this back


def test_load_state_tolerates_a_minimal_document() -> None:
    """Only `schema_version` present -- every other field must default the
    same way `empty_state()` does, not raise a KeyError."""
    from proxmox_storage_drs.state import _state_from_dict

    state = _state_from_dict({"schema_version": 1})
    assert state == empty_state()


def test_load_state_round_trips_a_full_document(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    state = State(
        schema_version=1,
        lock=LockInfo(pid=12345, host="mgmt01", acquired_at="2026-09-04T02:00:00Z"),
        last_balance=LastBalance(
            at="2026-09-03T22:14:03Z",
            load_vector={"fc-tier1:101:scsi0": 3.0, "fc-tier1:102:scsi0": 2.5},
        ),
        cooldowns=Cooldowns(
            disk={"fc-tier1:101:scsi1": "2026-09-03T22:41:55Z"},
            storage={"fc-tier1:san-b": "2026-09-03T22:41:55Z"},
        ),
        inflight_upids=("UPID:mgmt01:...",),
        staged_disks=("102:scsi0",),
    )
    save_state_atomic(str(path), state)
    assert load_state(str(path)) == state


def test_saved_file_matches_section_11_2s_own_example_shape(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    state = State(
        lock=LockInfo(pid=12345, host="mgmt01", acquired_at="2026-09-04T02:00:00Z"),
        last_balance=LastBalance(
            at="2026-09-03T22:14:03Z",
            load_vector={"fc-tier1:101:scsi0": 3.0, "fc-tier1:102:scsi0": 2.5},
        ),
    )
    save_state_atomic(str(path), state)
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk["schema_version"] == 1
    assert on_disk["lock"] == {
        "pid": 12345,
        "host": "mgmt01",
        "acquired_at": "2026-09-04T02:00:00Z",
    }
    assert on_disk["last_balance"]["at"] == "2026-09-03T22:14:03Z"
    assert on_disk["cooldowns"] == {"disk": {}, "storage": {}}
    assert on_disk["inflight_upids"] == []
    assert on_disk["staged_disks"] == []


# ------------------------------------------------------ save_state_atomic


def test_save_state_atomic_creates_the_parent_directory(tmp_path: Path) -> None:
    path = tmp_path / "fresh" / "install" / "state.json"
    save_state_atomic(str(path), empty_state())
    assert path.is_file()


def test_save_state_atomic_leaves_no_temp_file_behind(tmp_path: Path) -> None:
    save_state_atomic(str(tmp_path / "state.json"), empty_state())
    assert [p.name for p in tmp_path.iterdir()] == ["state.json"]


def test_save_state_atomic_raises_state_error_when_the_target_is_a_directory(
    tmp_path: Path,
) -> None:
    path = tmp_path / "state.json"
    path.mkdir()  # os.replace(tmp_file, an existing directory) fails on POSIX
    with pytest.raises(StateError):
        save_state_atomic(str(path), empty_state())


def test_save_state_atomic_cleans_up_its_temp_file_when_replace_fails(tmp_path: Path) -> None:
    """The `finally` block's own cleanup, pinned directly rather than only
    inferred from `StateError` being raised (the test above): a failed
    `os.replace()` must not leave a `.state-*.tmp` file behind in the
    target directory."""
    path = tmp_path / "state.json"
    path.mkdir()
    with pytest.raises(StateError):
        save_state_atomic(str(path), empty_state())
    assert list(tmp_path.iterdir()) == [path]  # only the pre-existing directory


@pytest.mark.skipif(os.geteuid() == 0, reason="root can write anywhere")
def test_save_state_atomic_raises_state_error_on_a_permission_failure() -> None:
    with pytest.raises(StateError):
        save_state_atomic("/root/pve-storage-drs-test-unwritable/state.json", empty_state())


# -------------------------------------------------------- load_vector_for_group


def test_load_vector_for_group_strips_the_prefix() -> None:
    state = State(
        last_balance=LastBalance(
            at="2026-09-03T22:14:03Z",
            load_vector={"fc-tier1:101:scsi0": 3.0, "fc-tier1:102:scsi0": 2.5},
        )
    )
    assert load_vector_for_group(state, "fc-tier1") == {"101:scsi0": 3.0, "102:scsi0": 2.5}


def test_load_vector_for_group_is_none_when_the_group_has_no_entries() -> None:
    """Distinct from `{}` -- `gates.py`'s `last_load=None` means "no such
    run has ever happened", not "a run happened with zero load"."""
    state = State(last_balance=LastBalance(at="...", load_vector={"other-group:101:scsi0": 1.0}))
    assert load_vector_for_group(state, "fc-tier1") is None


def test_load_vector_for_group_is_none_on_an_entirely_fresh_state() -> None:
    assert load_vector_for_group(empty_state(), "fc-tier1") is None


def test_load_vector_for_group_does_not_confuse_a_group_name_that_is_a_prefix_of_another() -> None:
    """`"fc-tier10:101:scsi0"` must not leak into `"fc-tier1"`'s vector --
    the delimiter after the group name is part of the prefix comparison."""
    state = State(
        last_balance=LastBalance(
            at="...",
            load_vector={"fc-tier1:101:scsi0": 3.0, "fc-tier10:201:scsi0": 9.0},
        )
    )
    assert load_vector_for_group(state, "fc-tier1") == {"101:scsi0": 3.0}


# -------------------------------------------------------- with_recorded_balance


def test_with_recorded_balance_replaces_only_the_named_groups_entries() -> None:
    state = State(
        last_balance=LastBalance(
            at="2026-09-03T22:14:03Z",
            load_vector={"fc-tier1:101:scsi0": 1.0, "fc-tier2:201:scsi0": 9.0},
        )
    )
    updated = with_recorded_balance(
        state, "fc-tier1", {"101:scsi0": 3.0, "102:scsi0": 2.5}, at="2026-09-04T00:00:00Z"
    )
    assert updated.last_balance.at == "2026-09-04T00:00:00Z"
    assert updated.last_balance.load_vector == {
        "fc-tier1:101:scsi0": 3.0,
        "fc-tier1:102:scsi0": 2.5,
        "fc-tier2:201:scsi0": 9.0,  # untouched
    }
    # Original is unmodified -- this is a pure function.
    assert state.last_balance.load_vector == {"fc-tier1:101:scsi0": 1.0, "fc-tier2:201:scsi0": 9.0}


def test_with_recorded_balance_defaults_at_to_now_when_not_given() -> None:
    updated = with_recorded_balance(empty_state(), "fc-tier1", {"101:scsi0": 1.0})
    assert updated.last_balance.at is not None
    assert updated.last_balance.at.endswith("Z")


# -------------------------------------------------------- with_recorded_cooldown


def test_with_recorded_cooldown_merges_without_clobbering_existing_entries() -> None:
    state = State(
        cooldowns=Cooldowns(
            disk={"fc-tier1:101:scsi1": "2026-09-03T22:41:55Z"},
            storage={"fc-tier1:san-b": "2026-09-03T22:41:55Z"},
        )
    )
    updated = with_recorded_cooldown(
        state,
        disk_keys={"fc-tier1:102:scsi0": "2026-09-04T00:00:00Z"},
        storage_keys={"fc-tier1:san-c": "2026-09-04T00:00:00Z"},
    )
    assert updated.cooldowns.disk == {
        "fc-tier1:101:scsi1": "2026-09-03T22:41:55Z",
        "fc-tier1:102:scsi0": "2026-09-04T00:00:00Z",
    }
    assert updated.cooldowns.storage == {
        "fc-tier1:san-b": "2026-09-03T22:41:55Z",
        "fc-tier1:san-c": "2026-09-04T00:00:00Z",
    }
    # Original is unmodified -- this is a pure function.
    assert state.cooldowns.disk == {"fc-tier1:101:scsi1": "2026-09-03T22:41:55Z"}


def test_with_recorded_cooldown_with_no_arguments_is_a_no_op() -> None:
    state = State(cooldowns=Cooldowns(disk={"a": "b"}))
    assert with_recorded_cooldown(state) == state


# ---------------------------------------------------- cooldown expiry queries

_NOW = datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc)


def test_cooldown_remaining_seconds_counts_down_from_the_recorded_timestamp() -> None:
    cooldowns = {"fc-tier1:101:scsi1": "2026-09-06T11:00:00Z"}  # 1h ago
    remaining = cooldown_remaining_seconds(cooldowns, "fc-tier1:101:scsi1", 86400.0, _NOW)
    assert remaining == pytest.approx(86400.0 - 3600.0)


def test_cooldown_remaining_seconds_is_zero_once_expired() -> None:
    cooldowns = {"fc-tier1:101:scsi1": "2026-09-05T00:00:00Z"}  # 36h ago
    assert cooldown_remaining_seconds(cooldowns, "fc-tier1:101:scsi1", 86400.0, _NOW) == 0.0


def test_cooldown_remaining_seconds_is_zero_when_the_key_is_absent() -> None:
    assert cooldown_remaining_seconds({}, "fc-tier1:101:scsi1", 86400.0, _NOW) == 0.0


def test_cooldown_remaining_seconds_is_zero_for_an_unparseable_timestamp() -> None:
    """A hand-edited or foreign timestamp must degrade to "not in
    cooldown", not raise -- this module's read-side philosophy applies to
    every field, not just the ones `load_state()` itself parses."""
    cooldowns = {"fc-tier1:101:scsi1": "not-a-timestamp"}
    assert cooldown_remaining_seconds(cooldowns, "fc-tier1:101:scsi1", 86400.0, _NOW) == 0.0


def test_active_disk_cooldowns_filters_by_group_and_expiry() -> None:
    state = State(
        cooldowns=Cooldowns(
            disk={
                "fc-tier1:101:scsi1": "2026-09-06T11:00:00Z",  # 1h ago -- active
                "fc-tier1:102:scsi0": "2026-09-01T00:00:00Z",  # long expired
                "fc-tier2:201:scsi0": "2026-09-06T11:59:00Z",  # different group
            }
        )
    )
    result = active_disk_cooldowns(state, "fc-tier1", 86400.0, _NOW)
    assert result == {"101:scsi1": pytest.approx(86400.0 - 3600.0)}


def test_active_storage_cooldowns_filters_by_group_and_expiry() -> None:
    state = State(
        cooldowns=Cooldowns(
            storage={
                "fc-tier1:san-b": "2026-09-06T11:30:00Z",  # 30m ago -- active
                "fc-tier1:san-c": "2020-01-01T00:00:00Z",  # long expired
                "fc-tier2:san-b": "2026-09-06T11:59:00Z",  # different group
            }
        )
    )
    result = active_storage_cooldowns(state, "fc-tier1", 3600.0, _NOW)
    assert result == {"san-b": pytest.approx(3600.0 - 1800.0)}


def test_active_cooldowns_are_empty_when_the_cooldown_is_disabled() -> None:
    """`cooldown_*_seconds <= 0` disables the check entirely -- never
    "everything is permanently in cooldown"."""
    state = State(cooldowns=Cooldowns(disk={"fc-tier1:101:scsi1": "2026-09-06T12:00:00Z"}))
    assert active_disk_cooldowns(state, "fc-tier1", 0.0, _NOW) == {}
    assert active_disk_cooldowns(state, "fc-tier1", -1.0, _NOW) == {}


def test_active_cooldowns_are_empty_on_a_fresh_state() -> None:
    assert active_disk_cooldowns(empty_state(), "fc-tier1", 86400.0, _NOW) == {}
    assert active_storage_cooldowns(empty_state(), "fc-tier1", 3600.0, _NOW) == {}


# --------------------------------------------------------------------- lock


def test_acquire_lock_creates_a_fresh_file_and_records_our_identity(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    handle = acquire_lock(str(path))
    assert handle is not None
    try:
        assert path.is_file()
        state = load_state(str(path))
        assert state.lock is not None
        assert state.lock.pid == os.getpid()
    finally:
        release_lock(handle)


def test_release_lock_clears_the_descriptive_lock_field(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    handle = acquire_lock(str(path))
    assert handle is not None
    release_lock(handle)
    assert load_state(str(path)).lock is None


def test_a_second_acquire_while_the_first_is_held_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    first = acquire_lock(str(path))
    assert first is not None
    try:
        second = acquire_lock(str(path))
        assert second is None  # section 11.2: "exit 0 quietly"
    finally:
        release_lock(first)


def test_acquiring_again_after_release_succeeds(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    first = acquire_lock(str(path))
    assert first is not None
    release_lock(first)
    second = acquire_lock(str(path))
    assert second is not None
    release_lock(second)


def test_acquire_lock_overwrites_a_stale_lock_field_left_by_a_dead_process(
    tmp_path: Path,
) -> None:
    """A crashed run's `flock()` is released by the kernel on process exit,
    so the *next* `acquire_lock()` simply succeeds -- but the descriptive
    `lock` JSON field it left behind (a pid that is no longer running) must
    be overwritten, not preserved or used to refuse the new acquisition."""
    path = tmp_path / "state.json"
    save_state_atomic(
        str(path),
        State(
            lock=LockInfo(pid=999999, host="some-other-host", acquired_at="2020-01-01T00:00:00Z")
        ),
    )
    handle = acquire_lock(str(path))
    assert handle is not None
    try:
        state = load_state(str(path))
        assert state.lock is not None
        assert state.lock.pid == os.getpid()
        assert state.lock.host != "some-other-host"
    finally:
        release_lock(handle)


def test_acquire_lock_survives_a_pre_existing_corrupt_file(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text("{not json at all", encoding="utf-8")
    handle = acquire_lock(str(path))
    assert handle is not None
    try:
        assert load_state(str(path)).lock is not None
    finally:
        release_lock(handle)


@pytest.mark.skipif(os.geteuid() == 0, reason="root can write anywhere")
def test_acquire_lock_raises_state_error_on_a_permission_failure() -> None:
    with pytest.raises(StateError):
        acquire_lock("/root/pve-storage-drs-test-unwritable/state.json")


def test_save_locked_state_persists_business_fields_while_still_held(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    handle = acquire_lock(str(path))
    assert handle is not None
    try:
        updated = with_recorded_balance(empty_state(), "fc-tier1", {"101:scsi0": 1.5})
        save_locked_state(handle, updated)

        # Still held: a concurrent acquire must still be refused.
        assert acquire_lock(str(path)) is None
        # And the write is visible to a plain read even before release.
        seen = load_state(str(path))
        assert seen.last_balance.load_vector == {"fc-tier1:101:scsi0": 1.5}
    finally:
        release_lock(handle)
    assert load_state(str(path)).last_balance.load_vector == {"fc-tier1:101:scsi0": 1.5}


def test_save_locked_state_preserves_this_handles_own_lock_metadata(tmp_path: Path) -> None:
    """The caller's in-memory `state` was read *before* the lock was taken,
    so it never carries this instance's own pid/host -- passing a `state`
    with `lock=None` must not erase what `acquire_lock()` already wrote."""
    path = tmp_path / "state.json"
    handle = acquire_lock(str(path))
    assert handle is not None
    try:
        save_locked_state(handle, empty_state())
        assert load_state(str(path)).lock is not None
        assert load_state(str(path)).lock.pid == os.getpid()  # type: ignore[union-attr]
    finally:
        release_lock(handle)


# ----------------------------------------------------------------- _pid_alive


def test_pid_alive_is_true_for_our_own_process() -> None:
    assert _pid_alive(os.getpid()) is True


def test_pid_alive_is_false_for_a_reaped_child() -> None:
    proc = subprocess.Popen(["true"])
    proc.wait()
    assert _pid_alive(proc.pid) is False


@pytest.mark.skipif(os.geteuid() == 0, reason="root can signal anything, incl. pid 1")
def test_pid_alive_is_true_for_a_process_we_cannot_signal() -> None:
    """pid 1 (init) always exists but is not ours to signal as a normal
    user -- `os.kill(1, 0)` raises `PermissionError`, which must still mean
    "alive", not "dead"."""
    assert _pid_alive(1) is True
