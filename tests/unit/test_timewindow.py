# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""execution.time_windows. See proxmox_storage_drs/timewindow.py."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from proxmox_storage_drs.config import TimeWindow
from proxmox_storage_drs.timewindow import current_deadline, is_window_active, window_close

# A fixed local-time zone distinct from UTC, so a test bug that quietly
# used UTC instead of the caller-supplied local time would show up as a
# wrong answer rather than an accidental pass.
LOCAL = timezone(timedelta(hours=2))


def at(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=LOCAL)


# 2026-09-07 is a Monday.


def test_is_window_active_within_a_same_day_window() -> None:
    window = TimeWindow(days=("mon",), start="09:00", end="17:00")
    assert is_window_active(window, at(2026, 9, 7, 12, 0)) is True


def test_is_window_active_before_a_same_day_window() -> None:
    window = TimeWindow(days=("mon",), start="09:00", end="17:00")
    assert is_window_active(window, at(2026, 9, 7, 8, 59)) is False


def test_is_window_active_at_the_close_boundary_is_exclusive() -> None:
    window = TimeWindow(days=("mon",), start="09:00", end="17:00")
    assert is_window_active(window, at(2026, 9, 7, 17, 0)) is False


def test_is_window_active_wrong_day() -> None:
    window = TimeWindow(days=("tue",), start="09:00", end="17:00")
    assert is_window_active(window, at(2026, 9, 7, 12, 0)) is False


def test_is_window_active_empty_days_means_every_day() -> None:
    window = TimeWindow(days=(), start="09:00", end="17:00")
    assert is_window_active(window, at(2026, 9, 7, 12, 0)) is True


def test_is_window_active_overnight_evening_piece() -> None:
    """22:00-06:00 on Monday: still Monday evening, inside the window."""
    window = TimeWindow(days=("mon",), start="22:00", end="06:00")
    assert is_window_active(window, at(2026, 9, 7, 23, 0)) is True


def test_is_window_active_overnight_morning_piece_next_calendar_day() -> None:
    """The same Monday-tagged overnight window is still active at 02:00
    on Tuesday -- the classic day-of-week-vs-overnight bug this module's
    own docstring calls out."""
    window = TimeWindow(days=("mon",), start="22:00", end="06:00")
    assert is_window_active(window, at(2026, 9, 8, 2, 0)) is True


def test_is_window_active_overnight_morning_piece_respects_the_boundary() -> None:
    window = TimeWindow(days=("mon",), start="22:00", end="06:00")
    assert is_window_active(window, at(2026, 9, 8, 6, 0)) is False


def test_is_window_active_overnight_does_not_leak_into_the_wrong_evening() -> None:
    """A window tagged only Monday must not also activate on Tuesday
    evening just because Tuesday is "the day after Monday" in some other
    sense -- only the two pieces derived from Monday itself are valid."""
    window = TimeWindow(days=("mon",), start="22:00", end="06:00")
    assert is_window_active(window, at(2026, 9, 8, 23, 0)) is False  # Tuesday evening


def test_window_close_same_day() -> None:
    window = TimeWindow(days=("mon",), start="09:00", end="17:00")
    assert window_close(window, at(2026, 9, 7, 12, 0)) == at(2026, 9, 7, 17, 0)


def test_window_close_overnight_evening_piece_closes_tomorrow() -> None:
    window = TimeWindow(days=("mon",), start="22:00", end="06:00")
    assert window_close(window, at(2026, 9, 7, 23, 0)) == at(2026, 9, 8, 6, 0)


def test_window_close_overnight_morning_piece_closes_today() -> None:
    window = TimeWindow(days=("mon",), start="22:00", end="06:00")
    assert window_close(window, at(2026, 9, 8, 2, 0)) == at(2026, 9, 8, 6, 0)


def test_current_deadline_no_windows_configured_means_unrestricted() -> None:
    assert current_deadline((), at(2026, 9, 7, 12, 0)) is None


def test_current_deadline_outside_every_window_is_zero_budget() -> None:
    windows = (TimeWindow(days=("mon",), start="09:00", end="17:00"),)
    now = at(2026, 9, 7, 18, 0)
    assert current_deadline(windows, now) == now


def test_current_deadline_inside_a_window_is_its_close_time() -> None:
    windows = (TimeWindow(days=("mon",), start="09:00", end="17:00"),)
    assert current_deadline(windows, at(2026, 9, 7, 12, 0)) == at(2026, 9, 7, 17, 0)


def test_current_deadline_picks_the_latest_close_among_overlapping_active_windows() -> None:
    windows = (
        TimeWindow(days=("mon",), start="09:00", end="12:00"),
        TimeWindow(days=("mon",), start="10:00", end="18:00"),
    )
    assert current_deadline(windows, at(2026, 9, 7, 11, 0)) == at(2026, 9, 7, 18, 0)
