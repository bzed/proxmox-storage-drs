# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Logging policy. See proxmox_storage_drs/logging_setup.py and
IMPLEMENTATION_PLAN.md section 2.3.

The formatter tests here are the old ones; everything about *policy* --
which level, which format, whose loggers -- is new, and exists because the
policy drifted once already behind tests that only checked the plumbing.
"""

from __future__ import annotations

import ast
import io
import json
import logging
import pathlib

import pytest

from proxmox_storage_drs.logging_setup import (
    JsonFormatter,
    TextFormatter,
    configure_logging,
    floor_for_command,
    resolve_format,
    resolve_level,
)


class _FakeTTY(io.StringIO):
    def __init__(self, isatty: bool) -> None:
        super().__init__()
        self._isatty = isatty

    def isatty(self) -> bool:
        return self._isatty


# ------------------------------------------------------------------ levels


@pytest.mark.parametrize(
    "verbose_count,quiet,expected",
    [
        (0, False, logging.WARNING),  # a clean run says nothing
        (1, False, logging.INFO),  # -v: this run's decision trail
        (2, False, logging.DEBUG),  # -vv: and the libraries
        (3, False, logging.DEBUG),  # no level below DEBUG to reach
        (0, True, logging.ERROR),
        (3, True, logging.ERROR),  # --quiet wins over -v
    ],
)
def test_resolve_level_ladder(verbose_count: int, quiet: bool, expected: int) -> None:
    assert resolve_level(verbose_count, quiet) == expected


@pytest.mark.parametrize("level", ["error", "warning", "info", "debug"])
def test_log_level_wins_over_both_verbose_and_quiet(level: str) -> None:
    expected = getattr(logging, level.upper())
    assert resolve_level(0, False, level) == expected
    assert resolve_level(2, False, level) == expected
    assert resolve_level(0, True, level) == expected


# ------------------------------------------------------------------- floor


def test_floor_applies_only_to_a_run_that_can_change_the_cluster() -> None:
    assert floor_for_command("apply", "auto") == logging.INFO
    assert floor_for_command("apply", "confirm") == logging.INFO
    assert floor_for_command("apply", "dry-run") is None
    for command in ("plan", "explain", "show-load", "verify-metrics", "collect-testdata"):
        assert floor_for_command(command, "auto") is None


def test_auto_run_logs_its_audit_trail_without_being_asked(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Section 2.3's point: an audit trail gated behind a flag the operator
    has to remember is not an audit trail."""
    configure_logging(0, False, log_format="json", floor=floor_for_command("apply", "auto"))
    logging.getLogger("proxmox_storage_drs.test.floor").info("issued", extra={"event": "x"})
    assert "issued" in capsys.readouterr().err


def test_quiet_still_wins_over_the_mandatory_floor(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(0, True, log_format="json", floor=floor_for_command("apply", "auto"))
    logging.getLogger("proxmox_storage_drs.test.floorquiet").info("issued", extra={"event": "x"})
    assert capsys.readouterr().err == ""


def test_explicit_log_level_also_overrides_the_floor(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(
        0, False, log_level="error", log_format="json", floor=floor_for_command("apply", "auto")
    )
    logging.getLogger("proxmox_storage_drs.test.floorlevel").info("issued", extra={"event": "x"})
    assert capsys.readouterr().err == ""


# ------------------------------------------------------------------ format


def test_resolve_format_follows_the_destination() -> None:
    assert resolve_format("auto", _FakeTTY(True)) == "text"
    assert resolve_format("auto", _FakeTTY(False)) == "json"
    # An explicit choice overrides the sniffing in both directions.
    assert resolve_format("json", _FakeTTY(True)) == "json"
    assert resolve_format("text", _FakeTTY(False)) == "text"


def test_text_format_emits_no_json(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(1, False, log_format="text")
    logging.getLogger("proxmox_storage_drs.test.text").warning("disk is busy", extra={"event": "x"})
    err = capsys.readouterr().err
    assert err.strip() == "WARNING: disk is busy"
    with pytest.raises(json.JSONDecodeError):
        json.loads(err)


def test_text_format_does_not_prefix_the_audit_trail(capsys: pytest.CaptureFixture[str]) -> None:
    """INFO at a terminal is the narrative the operator asked for; prefixing
    every line of it with ``INFO:`` is noise, not information."""
    configure_logging(1, False, log_format="text")
    logging.getLogger("proxmox_storage_drs.test.textinfo").info(
        "move started", extra={"event": "x"}
    )
    assert capsys.readouterr().err.strip() == "move started"


def test_json_format_on_a_tty_is_still_json(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(1, False, log_format="json")
    logging.getLogger("proxmox_storage_drs.test.json").info("hello", extra={"event": "x"})
    assert json.loads(capsys.readouterr().err.strip())["message"] == "hello"


# ------------------------------------------------------- third-party noise


def test_our_records_still_propagate_to_root(capsys: pytest.CaptureFixture[str]) -> None:
    """`propagate = False` on the package logger would hide every record
    from pytest's own `caplog` (whose handler sits on root) and from any
    application embedding this package -- so the separation is done with
    levels instead, and this asserts the property that choice preserves."""
    configure_logging(1, False, log_format="json")
    assert logging.getLogger("proxmox_storage_drs").propagate is True


def test_v_does_not_raise_third_party_loggers(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(1, False, log_format="json")
    logging.getLogger("urllib3.connectionpool").info("Starting new HTTPS connection")
    assert capsys.readouterr().err == ""


def test_vv_does_raise_third_party_loggers(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(2, False, log_format="json")
    logging.getLogger("urllib3.connectionpool").debug("Starting new HTTPS connection")
    assert "Starting new HTTPS connection" in capsys.readouterr().err


def test_our_records_are_not_emitted_twice(capsys: pytest.CaptureFixture[str]) -> None:
    """One handler, on root, with the package logger carrying only a level:
    a second handler on the package logger would print every one of our
    records twice, once per handler."""
    configure_logging(1, False, log_format="json")
    logging.getLogger("proxmox_storage_drs.test.dup").info("once", extra={"event": "x"})
    assert len(capsys.readouterr().err.strip().splitlines()) == 1


# -------------------------------------------------------------- formatters


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


def test_text_formatter_includes_exception_info() -> None:
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
    rendered = TextFormatter().format(record)
    assert rendered.startswith("ERROR: failed")
    assert "ValueError" in rendered


def test_configure_logging_writes_to_stderr_only(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(verbose_count=1, quiet=False, log_format="json")
    logging.getLogger("proxmox_storage_drs.test.configure").info("marker-message")
    captured = capsys.readouterr()
    assert captured.out == ""
    payload = json.loads(captured.err.strip().splitlines()[-1])
    assert payload["message"] == "marker-message"


# ------------------------------------------------------- the catalogue rule


def test_every_log_call_carries_an_event() -> None:
    """Section 2.3: "Every log record carries an ``event``" -- the event
    names are an interface (``jq 'select(.event=="move_started")'``), so a
    call that forgets one silently adds an unnameable member to the
    catalogue. Parsed rather than grepped: the first version of this test
    matched the string ``logger.warning()`` inside a *docstring* and
    reported it as a violation, which is exactly the kind of false positive
    that gets a lint test deleted instead of fixed.
    """
    src = pathlib.Path(__file__).resolve().parents[2] / "src" / "proxmox_storage_drs"
    methods = {"debug", "info", "warning", "error", "exception", "critical", "log"}
    offenders: list[str] = []
    for path in sorted(src.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute) or func.attr not in methods:
                continue
            if not isinstance(func.value, ast.Name) or func.value.id != "logger":
                continue
            extra = next((kw.value for kw in node.keywords if kw.arg == "extra"), None)
            keys: list[str] = []
            if isinstance(extra, ast.Dict):
                keys = [
                    k.value
                    for k in extra.keys
                    if isinstance(k, ast.Constant) and isinstance(k.value, str)
                ]
            elif extra is not None:
                # A computed `extra=` (a variable, a call, `{**a, "event": ...}`)
                # cannot be checked statically; those are spelled inline in
                # this codebase, so treat anything else as needing review.
                keys = ["event"] if "event" in ast.dump(extra) else []
            if "event" not in keys:
                offenders.append(f"{path.name}:{node.lineno}")
    assert offenders == [], f"log calls with no event= in extra: {offenders}"
