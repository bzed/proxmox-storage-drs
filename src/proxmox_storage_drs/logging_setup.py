# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Structured JSON logging. See IMPLEMENTATION_PLAN.md section 2.1.

Every log record is one JSON object per line, written to **stderr** -- not
stdout, so that ``pve-storage-drs --json``'s machine-readable plan report
(section 9.5) can be captured from stdout alone with nothing interleaved.
A systemd service unit captures both streams into the same journal, so this
costs nothing when run under the timer, which is how the plan's "captured by
journald" property is preserved (see the section 2.1 note added alongside
this module).

``cli.py`` is the only caller of :func:`configure_logging`; every other
module gets its logger the ordinary way, ``logging.getLogger(__name__)``, and
passes structured context via the standard ``extra=`` mechanism rather than
formatting it into the message string -- that is what keeps the JSON output
machine-parseable.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

# Attributes every stdlib LogRecord carries. Anything else on the record was
# passed via `extra={...}` by the caller and belongs in the JSON payload.
_STANDARD_RECORD_ATTRS = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)


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
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, sort_keys=True)


def verbosity_to_level(verbose_count: int, quiet: bool) -> int:
    """Map ``-v``/``--quiet`` (section 11.3) to a stdlib logging level.

    ``--quiet`` wins over any ``-v`` count: the systemd timer that passes it
    wants warnings and errors only, full stop.
    """
    if quiet:
        return logging.WARNING
    if verbose_count <= 0:
        return logging.INFO
    return logging.DEBUG


def configure_logging(verbose_count: int = 0, quiet: bool = False) -> None:
    """Install the JSON handler on the root logger. Called once, from ``main()``."""
    level = verbosity_to_level(verbose_count, quiet)
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
