# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit parsing and formatting for durations and byte sizes.

``config.py`` is the only caller that needs to *parse* these (config values
like ``"24h"`` or ``"200MiB"`` per IMPLEMENTATION_PLAN.md section 11); the
formatters are used wherever a human-readable report is built (``cli.py``,
``schedule.py``'s explain output). Keeping both here, rather than repeating a
regex in every module that reads a duration, is the "one implementation of
every rule" convention from AGENTS.md section 5.
"""

from __future__ import annotations

import re

from proxmox_storage_drs.exceptions import ConfigError

# Binary (IEC) size suffixes, per IMPLEMENTATION_PLAN.md section 2.1's use of
# MiB/TiB throughout. Deliberately no decimal (KB/MB/GB) suffixes: the plan
# never uses them and accepting both invites a config that means something
# different from what its author intended.
_SIZE_UNITS = {
    "b": 1,
    "kib": 1 << 10,
    "mib": 1 << 20,
    "gib": 1 << 30,
    "tib": 1 << 40,
    "pib": 1 << 50,
}

# Duration suffixes used throughout the plan: seconds, minutes, hours, days.
_DURATION_UNITS = {
    "s": 1,
    "m": 60,
    "h": 3600,
    "d": 86400,
}

_SIZE_RE = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*([A-Za-z]*)\s*$")
_DURATION_RE = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*([A-Za-z]*)\s*$")


def parse_size_bytes(value: int | float | str) -> int:
    """Parse a size into an integer byte count.

    Accepts a bare number (bytes) or a string like ``"200MiB"``, ``"1.5TiB"``
    or ``"512"``. Raises :class:`ConfigError` on anything else -- this is
    config-facing, so an unparseable value is a hard failure, never a silent
    zero (IMPLEMENTATION_PLAN.md section 11.1).
    """
    if isinstance(value, bool):  # bool is an int subclass; reject explicitly
        raise ConfigError(f"not a size: {value!r}")
    if isinstance(value, (int, float)):
        if value < 0:
            raise ConfigError(f"size must not be negative: {value!r}")
        return int(value)
    match = _SIZE_RE.match(value)
    if not match:
        raise ConfigError(f"not a size: {value!r}")
    number, suffix = match.groups()
    unit = _SIZE_UNITS.get(suffix.lower() or "b")
    if unit is None:
        raise ConfigError(f"unknown size unit {suffix!r} in {value!r}")
    return int(round(float(number) * unit))


def parse_duration_seconds(value: int | float | str) -> float:
    """Parse a duration into seconds.

    Accepts a bare number (seconds) or a string like ``"24h"``, ``"5m"``,
    ``"30s"`` or ``"7d"``. Raises :class:`ConfigError` on anything else.
    """
    if isinstance(value, bool):
        raise ConfigError(f"not a duration: {value!r}")
    if isinstance(value, (int, float)):
        if value < 0:
            raise ConfigError(f"duration must not be negative: {value!r}")
        return float(value)
    match = _DURATION_RE.match(value)
    if not match:
        raise ConfigError(f"not a duration: {value!r}")
    number, suffix = match.groups()
    unit = _DURATION_UNITS.get(suffix.lower() or "s")
    if unit is None:
        raise ConfigError(f"unknown duration unit {suffix!r} in {value!r}")
    return float(number) * unit


def format_bytes(size_bytes: float) -> str:
    """Render a byte count as a human-readable IEC string, e.g. ``"1.50 TiB"``.

    Used only for human-facing reports; never round-trip this through
    :func:`parse_size_bytes` -- keep the exact value for arithmetic and format
    only at the point of display (see .agents/testing.md, "round once").
    """
    size = float(size_bytes)
    for suffix, factor in (("PiB", 1 << 50), ("TiB", 1 << 40), ("GiB", 1 << 30)):
        if abs(size) >= factor:
            return f"{size / factor:.2f} {suffix}"
    for suffix, factor in (("MiB", 1 << 20), ("KiB", 1 << 10)):
        if abs(size) >= factor:
            return f"{size / factor:.2f} {suffix}"
    return f"{size:.0f} B"


def format_duration_seconds(duration_seconds: float) -> str:
    """Render a duration in seconds as a human-readable string, e.g. ``"2.2h"``."""
    duration = float(duration_seconds)
    for suffix, factor in (("d", 86400.0), ("h", 3600.0), ("m", 60.0)):
        if abs(duration) >= factor:
            return f"{duration / factor:.1f}{suffix}"
    return f"{duration:.0f}s"
