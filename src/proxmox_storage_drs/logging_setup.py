# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Logging policy. See IMPLEMENTATION_PLAN.md section 2.3.

Every log record goes to **stderr** -- not stdout, so that
``pve-storage-drs --json``'s machine-readable report (section 9.5) can be
captured from stdout alone with nothing interleaved.

Two audiences, one set of records. A person at a terminal wants silence
unless something is wrong; a journal read three weeks later wants every
decision that changed the cluster, in a form ``journalctl``/``jq`` can
filter. Section 2.3 resolves that with a level ladder (``--quiet`` <
default < ``-v`` < ``-vv``), a format that follows the destination
(:func:`resolve_format` -- text for a TTY, JSON for anything else), and a
mandatory ``INFO`` floor for any run that can actually change the cluster
(:func:`floor_for_command`), since an audit trail gated behind a flag the
operator has to remember is not an audit trail.

``cli.py`` is the only caller of :func:`configure_logging`; every other
module gets its logger the ordinary way, ``logging.getLogger(__name__)``,
and passes structured context via the standard ``extra=`` mechanism rather
than formatting it into the message string -- that is what keeps the JSON
output machine-parseable, and it is enforced by
``tests/unit/test_logging_setup.py``'s catalogue test.
"""

from __future__ import annotations

import json
import logging
import math
import sys
from datetime import datetime, timezone
from typing import IO

#: The package's own logger namespace. :func:`configure_logging` sets this
#: logger's *level* (the handler itself goes on root) so that ``-v`` raises
#: *this* tool's verbosity without also switching on
#: urllib3/proxmoxer/statsmodels debug output -- which is not what an
#: operator asking for more detail about this tool meant (section 2.3).
PACKAGE_LOGGER = "proxmox_storage_drs"

#: Third-party loggers stay here regardless of ``-v``; only ``-vv`` (which
#: is explicitly "and the libraries too") lets them through.
_THIRD_PARTY_FLOOR = logging.WARNING

# Attributes every stdlib LogRecord carries. Anything else on the record was
# passed via `extra={...}` by the caller and belongs in the JSON payload.
_STANDARD_RECORD_ATTRS = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)

LOG_LEVELS = ("error", "warning", "info", "debug")
LOG_FORMATS = ("auto", "text", "json")


def json_safe(value: object) -> object:
    """Replace every non-finite float with ``None``, recursively.

    Python's JSON encoder emits bare ``Infinity``/``NaN`` literals, which
    **RFC 8259 does not define**: Go's `encoding/json`, Rust's `serde_json`
    and Loki all reject such a line outright, and `jq` -- the consumer
    section 2.3 names explicitly -- silently reads it back as `1.79e308`,
    a different number. Either way the "machine-readable" half of this
    tool's output is not.

    Found by running ``apply --mode auto`` against a real cluster: section
    7's payback ratio is `+inf` whenever a plan's total cost is zero, which
    is not an edge case at all -- it is every run whose gate acts and whose
    solver then decides to move nothing. ``None`` (JSON ``null``) is also
    the honest reading of that number: with no moves to pay for, the ratio
    is not infinite so much as not applicable, which is what the
    accompanying ``total_cost_load_seconds: 0`` already says.

    Shared by this module's own formatter and ``cli.py``'s ``--json``
    reports (AGENTS.md section 5), because the requirement -- everything
    this tool prints as JSON is JSON -- is the same for both.
    """
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


class JsonFormatter(logging.Formatter):
    """Render one :class:`logging.LogRecord` as one JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_ATTRS and key not in payload:
                payload[key] = json_safe(value)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        # `allow_nan=False` so this can never regress quietly: a non-finite
        # value that slipped past `json_safe()` raises here rather than
        # writing a line no strict parser can read.
        return json.dumps(payload, default=str, sort_keys=True, allow_nan=False)


class TextFormatter(logging.Formatter):
    """One human-readable line per record: ``LEVEL: message``.

    Deliberately not a second rendering of the record's structured fields:
    an operator reading this at a terminal is being told something went
    wrong, and the ``extra=`` context exists for the machine-readable half
    of section 2.3. The one exception is ``INFO``, which at a terminal is
    the audit trail the operator asked for with ``-v`` (or that an ``auto``
    run emits unasked) -- it prints unprefixed, because prefixing every
    line of a requested narrative with ``INFO:`` is noise, not information.
    """

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        line = message if record.levelno <= logging.INFO else f"{record.levelname}: {message}"
        if record.exc_info:
            line = f"{line}\n{self.formatException(record.exc_info)}"
        return line


def resolve_level(verbose_count: int, quiet: bool, log_level: str | None = None) -> int:
    """Section 2.3's ladder: ``--quiet`` < default < ``-v`` < ``-vv``.

    ``--log-level`` (``log_level``) is the explicit form and wins over both
    of the others -- automation states a level rather than counting ``v``s.
    ``--quiet`` otherwise wins over ``-v``: an operator asking for silence
    on the same command line that asks for detail meant the silence.
    """
    if log_level is not None:
        level: int = getattr(logging, log_level.upper())
        return level
    if quiet:
        return logging.ERROR
    if verbose_count <= 0:
        return logging.WARNING
    if verbose_count == 1:
        return logging.INFO
    return logging.DEBUG


def floor_for_command(command: str, effective_mode: str) -> int | None:
    """The mandatory ``INFO`` floor of section 2.3, or ``None``.

    A run that can change the cluster logs its audit trail whether or not
    anyone asked for it: section 2.1's "in ``auto`` mode this log is the
    only record a human will see" cannot be satisfied by an option the
    operator has to remember to pass, and an unattended timer that silently
    migrated 400 GiB is not acceptable output however the unit file was
    written. ``--quiet`` still wins (:func:`configure_logging` applies this
    as a floor, not an override) -- an operator may insist on silence, at
    the documented cost of the only record of what moved.

    Read-only commands and ``apply --mode dry-run`` change nothing, so they
    have nothing to audit and keep the ordinary default.
    """
    if command == "apply" and effective_mode in ("confirm", "auto"):
        return logging.INFO
    return None


def resolve_format(log_format: str, stream: IO[str] | None = None) -> str:
    """``auto`` -> ``"text"`` at a TTY, ``"json"`` anywhere else.

    A person gets prose; journald, a pipe and a redirect get the JSON object
    a script can parse. This is what makes a systemd unit correct without
    the unit having to say anything, and what keeps JSON out of an
    interactive terminal -- section 2.3's whole format story, in one rule.
    An explicit ``text``/``json`` overrides it in either direction.
    """
    if log_format != "auto":
        return log_format
    target = sys.stderr if stream is None else stream
    try:
        return "text" if target.isatty() else "json"
    except (AttributeError, ValueError):  # pragma: no cover - detached/closed stream
        return "json"


def configure_logging(
    verbose_count: int = 0,
    quiet: bool = False,
    *,
    log_level: str | None = None,
    log_format: str = "auto",
    floor: int | None = None,
) -> str:
    """Install this run's log handler. Called once, from ``main()``.

    ``floor`` is :func:`floor_for_command`'s mandatory minimum verbosity,
    applied only when the operator has not explicitly asked for less
    (``--quiet``/``--log-level`` both win over it). Returns the format
    actually selected, which ``cli.py`` needs in order to decide whether a
    failure's human-readable line would duplicate its own log record
    (section 2.3: "an error is one fact, logged once").
    """
    level = resolve_level(verbose_count, quiet, log_level)
    # X-06: the mandatory floor's one documented escape hatch is `--quiet`
    # ("an operator may insist on silence, at the documented cost of the
    # only record of what moved") -- an explicit `--log-level` used to
    # count as opting out too, so `apply --mode auto --log-level warning`
    # ran unattended with no audit trail and no warning that it would.
    # `--log-level` still *raises* verbosity past the floor freely (`min`
    # is a no-op whenever the requested level is already at or below it);
    # only a level *less* verbose than the floor gets clamped back up to
    # it, exactly as an unset `--log-level` already would.
    if floor is not None and not quiet:
        level = min(level, floor)

    resolved_format = resolve_format(log_format)
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(JsonFormatter() if resolved_format == "json" else TextFormatter())

    # One handler, on the root logger, and the *levels* do the separating.
    # A record from `proxmox_storage_drs.*` is filtered by the package
    # logger's own level and then propagates to this handler; a record from
    # urllib3 is filtered by root's level, which it inherits. So our
    # verbosity and the libraries' are independent without a second handler
    # to keep in sync, without `propagate = False` (which would also hide
    # our records from pytest's `caplog` and from anything embedding this
    # package), and with no record emitted twice.
    root = logging.getLogger()
    root.handlers = [handler]
    # Libraries only follow us down to DEBUG, never to INFO: `-v` means
    # "tell me more about what this tool decided", not "show me every HTTP
    # connection urllib3 opened". `-vv` is the one that means both.
    root.setLevel(logging.DEBUG if level <= logging.DEBUG else _THIRD_PARTY_FLOOR)

    package = logging.getLogger(PACKAGE_LOGGER)
    package.handlers = []
    package.propagate = True
    package.setLevel(level)
    return resolved_format
