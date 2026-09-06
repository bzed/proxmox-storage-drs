# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""``execution.time_windows``: when ``auto`` mode may execute moves.
See IMPLEMENTATION_PLAN.md section 9.1 and section 2.1's "the engine may
plan at any time and simply decline to act outside the window."

Applies to ``auto`` mode only (section 9.1's own table; the manual's own
words for ``time_windows[].days``: "``dry-run`` and ``confirm`` are not
time-restricted, since neither changes anything without a human already
present"). ``plan``/``show-load``/``confirm`` never call anything here.

**Local time, not UTC.** A maintenance window like ``22:00``-``06:00`` is
something an operator configures thinking in their own server's wall
clock, the same convention `systemd.timer`'s own ``OnCalendar=`` uses by
default. This is a deliberate, documented choice (`IMPLEMENTATION_PLAN.md`
does not name a timezone for this setting) -- distinct from the rest of
this codebase's own bookkeeping (`state.json` timestamps, cooldown
arithmetic), which stays UTC throughout since those are machine-to
-machine instants, not a human-configured wall-clock window. Every
function here takes ``now`` as a parameter rather than reading the clock
itself, so a caller supplies local time explicitly (typically
``datetime.now().astimezone()``) and tests supply a fixed one; the
returned deadline is a normal timezone-aware ``datetime``, safely
comparable against a UTC ``now`` elsewhere (Python compares aware
datetimes by absolute instant, not by which zone either one is
expressed in), so nothing downstream needs to know this module thought
in local time at all.

**DST correctness depends on the caller's ``now`` carrying a real IANA
zone, not a frozen UTC offset.** :func:`window_close`'s "closes
tomorrow" case (an overnight window) combines *today's* `tzinfo` with
*tomorrow's* date -- correct only if that `tzinfo` can re-resolve its
own UTC offset for a different date, which a `zoneinfo.ZoneInfo` does
and a fixed `datetime.timezone` (what bare ``datetime.now().astimezone()``
returns) cannot. `cli._real_local_now()` -- the real callers' source for
``now`` -- goes to the extra effort of resolving the host's actual IANA
zone for exactly this reason; see its own docstring for the narrower
residual gap that remains only in its own fallback path.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from proxmox_storage_drs.config import TimeWindow

_DAY_NAMES = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _parse_hhmm(value: str) -> time:
    hh, mm = value.split(":")
    return time(int(hh), int(mm))


def _day_name(d: date) -> str:
    return _DAY_NAMES[d.weekday()]


def is_window_active(window: TimeWindow, now: datetime) -> bool:
    """True when ``now`` falls inside ``window``, including one that
    crosses midnight (``start > end``, e.g. ``22:00``-``06:00``) -- the
    day-of-week check for the overnight half must match the day the
    window *started* on, not the calendar day ``now`` currently is,
    or a Friday-night window would stop matching the moment it ticks
    past midnight into Saturday. An empty ``window.days`` means every
    day (the config loader already fills this in when unset, but this
    function stays correct for a directly-constructed ``TimeWindow`` too,
    e.g. from a test)."""
    days = set(window.days) if window.days else set(_DAY_NAMES)
    start = _parse_hhmm(window.start)
    end = _parse_hhmm(window.end)
    current = now.time()
    today = _day_name(now.date())
    if start < end:
        return today in days and start <= current < end
    # Crosses midnight: two disjoint pieces of the same logical window.
    evening_piece = today in days and current >= start
    yesterday = _day_name(now.date() - timedelta(days=1))
    morning_piece = yesterday in days and current < end
    return evening_piece or morning_piece


def window_close(window: TimeWindow, now: datetime) -> datetime:
    """The absolute instant ``window`` (assumed active at ``now`` --
    callers check :func:`is_window_active` first) closes next."""
    start = _parse_hhmm(window.start)
    end = _parse_hhmm(window.end)
    if start < end:
        return datetime.combine(now.date(), end, tzinfo=now.tzinfo)
    if now.time() >= start:
        # The evening piece: closes tomorrow.
        return datetime.combine(now.date() + timedelta(days=1), end, tzinfo=now.tzinfo)
    # The morning piece: closes today.
    return datetime.combine(now.date(), end, tzinfo=now.tzinfo)


def current_deadline(windows: tuple[TimeWindow, ...], now: datetime) -> datetime | None:
    """``None`` means "no restriction at all" -- section 2.1's "the engine
    may plan at any time" for the common case of no ``time_windows``
    configured, which callers must treat as an unbounded deadline, never
    as "never allowed". A non-empty ``windows`` with none of them active
    right now returns ``now`` itself: zero remaining budget, so a caller
    checking "does the next move fit before the deadline" correctly
    refuses everything without a separate "are we even in a window at
    all" check of its own. When more than one configured window is
    active simultaneously, the latest of their close times is used --
    auto mode may keep going as long as at least one of them still
    covers ``now``."""
    if not windows:
        return None
    active_closes = [window_close(w, now) for w in windows if is_window_active(w, now)]
    if not active_closes:
        return now
    return max(active_closes)
