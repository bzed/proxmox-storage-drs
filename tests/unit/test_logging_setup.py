# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Structured JSON logging. See proxmox_storage_drs/logging_setup.py."""

from __future__ import annotations

import io
import json
import logging

import pytest

from proxmox_storage_drs.logging_setup import (
    JsonFormatter,
    configure_logging,
    verbosity_to_level,
)


@pytest.mark.parametrize(
    "verbose_count,quiet,expected",
    [
        (0, False, logging.INFO),
        (1, False, logging.DEBUG),
        (2, False, logging.DEBUG),
        (0, True, logging.WARNING),
        (3, True, logging.WARNING),  # --quiet wins over -v
    ],
)
def test_verbosity_to_level(verbose_count: int, quiet: bool, expected: int) -> None:
    assert verbosity_to_level(verbose_count, quiet) == expected


def test_json_formatter_emits_one_parseable_object_per_record() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="proxmox_storage_drs.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello %s",
        args=("world",),
        exc_info=None,
    )
    payload = json.loads(formatter.format(record))
    assert payload["message"] == "hello world"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "proxmox_storage_drs.test"
    assert "timestamp" in payload


def test_json_formatter_includes_extra_fields() -> None:
    formatter = JsonFormatter()
    logger = logging.getLogger("proxmox_storage_drs.test.extra")
    logger.setLevel(logging.INFO)
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(formatter)
    logger.handlers = [handler]
    logger.propagate = False

    logger.info("gate decision", extra={"event": "gate", "threshold": 0.2})

    payload = json.loads(stream.getvalue())
    assert payload["event"] == "gate"
    assert payload["threshold"] == 0.2


def test_json_formatter_includes_exception_info() -> None:
    formatter = JsonFormatter()
    try:
        raise ValueError("boom")
    except ValueError:
        record = logging.LogRecord(
            name="x",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="failed",
            args=(),
            exc_info=__import__("sys").exc_info(),
        )
    payload = json.loads(formatter.format(record))
    assert "ValueError" in payload["exc_info"]


def test_configure_logging_writes_json_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(verbose_count=1, quiet=False)
    logging.getLogger("proxmox_storage_drs.test.configure").info("marker-message")
    captured = capsys.readouterr()
    assert captured.out == ""
    payload = json.loads(captured.err.strip().splitlines()[-1])
    assert payload["message"] == "marker-message"
