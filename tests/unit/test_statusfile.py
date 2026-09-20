# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""``statusfile.py`` (IMPLEMENTATION_PLAN.md section 2.4): the level policy, the
exact file shape, atomic writing, and -- when the plugin is installed -- the
real ``check_statusfile`` reading what we wrote."""

from __future__ import annotations

import datetime as dt
import os
import stat
import subprocess
from pathlib import Path

import pytest

from proxmox_storage_drs import statusfile
from proxmox_storage_drs.statusfile import (
    CRITICAL,
    MAX_DETAIL_LINES,
    OK,
    WARNING,
    RunReport,
    StatusFileError,
    build_run_status,
    render_status,
    write_status_file,
)

NOW = dt.datetime(2026, 9, 20, 20, 30, 0, tzinfo=dt.timezone.utc)

CHECK_STATUSFILE = "/usr/lib/nagios/plugins/check_statusfile"
needs_plugin = pytest.mark.skipif(
    not os.access(CHECK_STATUSFILE, os.X_OK),
    reason="check_statusfile (monitoring-plugins-contrib) is not installed",
)


def report(**kwargs: object) -> RunReport:
    base: dict[str, object] = {
        "mode": "auto",
        "exit_code": 0,
        "finished_at": NOW,
        "duration_seconds": 12.34,
    }
    base.update(kwargs)
    return RunReport(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------- level policy


def test_a_clean_run_is_ok() -> None:
    status = build_run_status(report(groups=2, moves_succeeded=3, bytes_moved=1 << 40))
    assert status.level == OK
    assert status.summary == "apply completed: 2 group(s), 3 move(s) executed"


def test_a_clean_dry_run_is_ok_and_says_nothing_moved() -> None:
    status = build_run_status(report(mode="dry-run", groups=1))
    assert status.level == OK
    assert "dry-run" in status.summary and "nothing moved" in status.summary


def test_warnings_on_an_exit_0_run_make_it_warning() -> None:
    status = build_run_status(report(warnings=("group g: gave up after 3 re-plans", "second")))
    assert status.level == WARNING
    assert status.summary.startswith("apply completed with 2 warnings: group g: gave up")
    assert "warning: second" in status.details


def test_a_single_warning_is_singular() -> None:
    assert "with 1 warning:" in build_run_status(report(warnings=("x",))).summary


def test_a_non_zero_exit_is_critical_even_with_warnings() -> None:
    status = build_run_status(
        report(exit_code=1, errors=("group g: load model unavailable: refused",), warnings=("w",))
    )
    assert status.level == CRITICAL
    assert status.summary == "apply failed: group g: load model unavailable: refused"
    assert "warning: w" in status.details


def test_a_non_zero_exit_with_no_recorded_error_still_says_something() -> None:
    status = build_run_status(report(exit_code=1))
    assert status.level == CRITICAL
    assert "exited 1" in status.summary


def test_the_headline_problem_is_not_repeated_in_the_details() -> None:
    status = build_run_status(report(warnings=("first", "second")))
    assert not any("first" in line for line in status.details)


def test_multiline_messages_are_flattened_so_the_summary_stays_on_line_2() -> None:
    status = build_run_status(report(exit_code=1, errors=("move failed\nwith a\n  second line",)))
    assert "\n" not in status.summary
    assert status.summary == "apply failed: move failed with a second line"


def test_an_overlong_message_is_cut_so_monitoring_does_not_truncate_the_perfdata() -> None:
    status = build_run_status(report(exit_code=1, errors=("x" * 5000,)))
    assert len(status.summary) <= len("apply failed: ") + statusfile.MAX_LINE_CHARS
    assert status.summary.endswith("...")


def test_details_are_capped() -> None:
    many = tuple(f"warning number {i}" for i in range(MAX_DETAIL_LINES + 10))
    status = build_run_status(report(warnings=many))
    assert any(line.startswith("... and ") and "more" in line for line in status.details)
    # cap + the "and N more" line + the version/mode/time footer
    assert len(status.details) == MAX_DETAIL_LINES + 2


# ------------------------------------------------------------------ file shape


def test_the_file_is_the_level_then_summary_with_perfdata_then_details() -> None:
    text = render_status(build_run_status(report(warnings=("a", "b"), groups=1, replans=2)))
    lines = text.splitlines()
    assert lines[0] == "WARNING"
    summary, _, perfdata = lines[1].partition(" | ")
    assert summary == "apply completed with 2 warnings: a"
    assert perfdata == (
        "groups=1 moves_succeeded=0 moves_failed=0 bytes_moved=0B "
        "replans=2 warnings=2 duration=12.3s"
    )
    assert lines[2] == "warning: b"
    assert lines[-1].startswith("pve-storage-drs ") and "finished 2026-09-20T20:30:00Z" in lines[-1]
    assert text.endswith("\n")


@pytest.mark.parametrize(
    "rep",
    [report(), report(warnings=("w",)), report(exit_code=1), report(exit_code=1, errors=("e",))],
)
def test_line_one_is_exactly_one_of_the_words_the_plugin_accepts(rep: RunReport) -> None:
    lines = render_status(build_run_status(rep)).splitlines()
    assert lines[0] in {"OK", "WARNING", "CRITICAL", "UNKNOWN"}
    # The plugin reports UNKNOWN for a file with nothing after line 1.
    assert len(lines) >= 2 and lines[1].strip()


# --------------------------------------------------------------------- writing


def test_write_creates_a_world_readable_file_and_leaves_no_temporary_behind(
    tmp_path: Path,
) -> None:
    path = tmp_path / "sub" / "dir" / "drs.status"  # parent directories do not exist yet
    write_status_file(str(path), build_run_status(report()))
    assert path.read_text(encoding="utf-8").startswith("OK\n")
    assert stat.S_IMODE(path.stat().st_mode) == 0o644
    assert [p.name for p in path.parent.iterdir()] == ["drs.status"]


def test_write_replaces_an_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "drs.status"
    write_status_file(str(path), build_run_status(report()))
    write_status_file(str(path), build_run_status(report(exit_code=1, errors=("boom",))))
    assert path.read_text(encoding="utf-8").startswith("CRITICAL\n")
    assert [p.name for p in tmp_path.iterdir()] == ["drs.status"]


def test_write_failure_raises_statusfileerror_and_cleans_up(tmp_path: Path) -> None:
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("x", encoding="utf-8")
    with pytest.raises(StatusFileError, match="could not write status file"):
        write_status_file(str(blocker / "drs.status"), build_run_status(report()))


def test_a_failed_replace_removes_the_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_a: object, **_k: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(StatusFileError, match="disk full"):
        write_status_file(str(tmp_path / "drs.status"), build_run_status(report()))
    assert list(tmp_path.iterdir()) == []


# ------------------------------------------------------------ the real plugin


def run_plugin(path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [CHECK_STATUSFILE, *extra, str(path)], capture_output=True, text=True, check=False
    )


@needs_plugin
@pytest.mark.parametrize(
    ("rep", "exit_code", "first_words"),
    [
        (report(groups=1, moves_succeeded=2), 0, "apply completed: 1 group(s), 2 move(s)"),
        (report(mode="dry-run"), 0, "apply (dry-run) completed"),
        (report(warnings=("w",)), 1, "apply completed with 1 warning: w"),
        (report(exit_code=1, errors=("boom",)), 2, "apply failed: boom"),
    ],
)
def test_check_statusfile_reads_what_we_write(
    tmp_path: Path, rep: RunReport, exit_code: int, first_words: str
) -> None:
    path = tmp_path / "drs.status"
    write_status_file(str(path), build_run_status(rep))
    result = run_plugin(path)
    assert result.returncode == exit_code, result.stdout
    # The plugin prints from line 2 on (line 1 is consumed as the state), so
    # the first thing on stdout must be our summary, perfdata after the pipe.
    first = result.stdout.splitlines()[0]
    assert first.startswith(first_words)
    assert " | groups=" in first and "duration=" in first
    assert result.stdout.splitlines()[-1].startswith("pve-storage-drs ")


@needs_plugin
def test_check_statusfile_calls_a_stale_file_warning_and_a_missing_one_unknown(
    tmp_path: Path,
) -> None:
    path = tmp_path / "drs.status"
    assert run_plugin(path).returncode == 3  # UNKNOWN: does not exist
    write_status_file(str(path), build_run_status(report()))
    assert run_plugin(path).returncode == 0
    old = NOW.timestamp() - 30 * 3600
    os.utime(path, (old, old))
    stale = run_plugin(path, "-a", "1h")
    assert stale.returncode == 1 and stale.stdout.startswith("WARNING:")


@needs_plugin
def test_the_plugin_rejects_the_shapes_the_module_never_writes(tmp_path: Path) -> None:
    """A guard on the guard: these are the two ways a status file goes wrong
    (wrong-case level word; nothing after line 1) and the plugin's verdict on
    each -- `test_line_one_is_exactly_one_of_the_words_the_plugin_accepts`
    exists so we never write either."""
    bad = tmp_path / "bad.status"
    bad.write_text("Ok\nsomething\n", encoding="utf-8")
    assert run_plugin(bad).returncode == 3
    only = tmp_path / "only.status"
    only.write_text("OK\n", encoding="utf-8")
    assert run_plugin(only).returncode == 3
