# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit parsing/formatting. See proxmox_storage_drs/units.py."""

from __future__ import annotations

import pytest

from proxmox_storage_drs.exceptions import ConfigError
from proxmox_storage_drs.units import (
    format_bytes,
    format_duration_seconds,
    parse_duration_seconds,
    parse_size_bytes,
)


@pytest.mark.parametrize(
    "value,expected_bytes",
    [
        (0, 0),
        (512, 512),
        (512.0, 512),
        ("512", 512),
        ("1KiB", 1024),
        ("200MiB", 200 * (1 << 20)),
        ("1.5TiB", int(1.5 * (1 << 40))),
        ("2PiB", 2 * (1 << 50)),
        ("2 GiB", 2 * (1 << 30)),  # a space between number and suffix is fine
        ("0", 0),
    ],
)
def test_parse_size_bytes_accepts(value: object, expected_bytes: int) -> None:
    assert parse_size_bytes(value) == expected_bytes  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ["not a size", "5XiB", -1, True, "-5MiB"])
def test_parse_size_bytes_rejects(value: object) -> None:
    with pytest.raises(ConfigError):
        parse_size_bytes(value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "value,expected_seconds",
    [
        (0, 0.0),
        (60, 60.0),
        ("60", 60.0),
        ("30s", 30.0),
        ("5m", 300.0),
        ("24h", 86400.0),
        ("7d", 604800.0),
        ("1.5h", 5400.0),
    ],
)
def test_parse_duration_seconds_accepts(value: object, expected_seconds: float) -> None:
    assert parse_duration_seconds(value) == expected_seconds  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ["not a duration", "5x", -1, True, "-5m"])
def test_parse_duration_seconds_rejects(value: object) -> None:
    with pytest.raises(ConfigError):
        parse_duration_seconds(value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "size_bytes,expected",
    [
        (0, "0 B"),
        (1023, "1023 B"),
        (1 << 10, "1.00 KiB"),
        (1 << 20, "1.00 MiB"),
        (int(1.5 * (1 << 40)), "1.50 TiB"),
        (1 << 50, "1.00 PiB"),
    ],
)
def test_format_bytes(size_bytes: int, expected: str) -> None:
    assert format_bytes(size_bytes) == expected


@pytest.mark.parametrize(
    "duration_seconds,expected",
    [
        (30, "30s"),
        (90, "1.5m"),
        (7200, "2.0h"),
        (172800, "2.0d"),
    ],
)
def test_format_duration_seconds(duration_seconds: float, expected: str) -> None:
    assert format_duration_seconds(duration_seconds) == expected
