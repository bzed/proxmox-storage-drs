# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The monitoring status file: one ``apply`` run's outcome, in the format the
``check_statusfile`` Nagios/Icinga plugin (``monitoring-plugins-contrib``)
reads. Implements IMPLEMENTATION_PLAN.md section 2.4.

**The format is the plugin's, and it is small.** ``check_statusfile`` reads
the file like this (its own source, not a description of it):

* line 1 is exactly ``OK``, ``WARNING``, ``CRITICAL`` or ``UNKNOWN`` -- the
  service state; anything else is reported UNKNOWN;
* every following line is the service output, printed verbatim; a file with
  nothing after line 1 is reported UNKNOWN ("Found no output");
* the file's *modification time* is its freshness: older than ``--age``
  (default 26 h) is reported WARNING. So the file is rewritten by every
  ``apply`` run that gets as far as a result, including runs that did nothing
  and dry runs -- a timer that stops firing must show up as a stale file, and
  a file that only changed when something moved would look stale on every
  quiet day.

Nagios reads the first line of the *output* (file line 2) for perfdata, so the
summary line carries ``label=value`` pairs after a ``|``.

The file is written atomically (temporary file in the same directory, then
``os.replace``): the plugin can run at any moment and must never see half of
one report. It is world-readable (0644) because the monitoring user is not the
user ``apply`` runs as, and contains only counts, group and storage names and
volume ids -- no credentials.

:func:`build_run_status` is pure (a :class:`RunReport` in, a
:class:`RunStatus` out), so the level policy is tested without a cluster;
:func:`write_status_file` is the only function that touches the filesystem.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import os
import tempfile
from dataclasses import dataclass, field

from proxmox_storage_drs import __version__
from proxmox_storage_drs.exceptions import DrsError

# Exactly the words check_statusfile accepts on line 1.
OK = "OK"
WARNING = "WARNING"
CRITICAL = "CRITICAL"

# Detail lines beyond this are summarised as "... and N more": a status file
# is read by a human on a monitoring dashboard, not archived.
MAX_DETAIL_LINES = 20

# Monitoring systems truncate plugin output (NRPE at 1 KiB by default), and an
# API or Prometheus error can carry a whole request URL. A message longer than
# this is cut, with an ellipsis: the full text is in the run log.
MAX_LINE_CHARS = 300


class StatusFileError(DrsError):
    """The status file could not be written."""


@dataclass(frozen=True, slots=True)
class RunReport:
    """What one ``apply`` run did, as the level policy needs it.

    ``errors`` are reasons the run failed (each one makes it CRITICAL);
    ``warnings`` are things a human should look at that did not fail the run
    (each one makes an otherwise-clean run WARNING). Both are single
    sentences naming the group, disk or storage concerned.
    """

    mode: str
    exit_code: int
    finished_at: dt.datetime
    duration_seconds: float
    groups: int = 0
    moves_succeeded: int = 0
    moves_failed: int = 0
    bytes_moved: int = 0
    replans: int = 0
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class RunStatus:
    """A report reduced to the file's content: ``level`` is line 1, ``summary``
    line 2 (perfdata follows it after ``|``), ``details`` the rest."""

    level: str
    summary: str
    details: tuple[str, ...] = ()
    perfdata: tuple[tuple[str, int | float, str], ...] = ()


def _one_line(text: str) -> str:
    """Collapse any run of whitespace, newlines included, to one space: a
    newline inside a message would otherwise become a line of its own in the
    plugin's output, and could push the summary off line 2. Cut at
    :data:`MAX_LINE_CHARS`."""
    flat = " ".join(text.split())
    if len(flat) > MAX_LINE_CHARS:
        return flat[: MAX_LINE_CHARS - 3] + "..."
    return flat


def build_run_status(report: RunReport) -> RunStatus:
    """The level policy (section 2.4).

    ``CRITICAL`` when the run exited non-zero: a failed move, or a PVE API or
    metrics error the run could not plan around. ``WARNING`` when it exited
    ``0`` but left something for a human: it gave up after too many external
    changes, a failed move's orphaned volume was reported, a source storage
    had not released after a move, or a group still breaches its reserve or
    free-space requirement after this run's plan. Otherwise ``OK``. ``UNKNOWN``
    is never produced here: a run that could not even read its configuration
    writes nothing, and the file then simply goes stale.
    """
    errors = [_one_line(e) for e in report.errors]
    warnings = [_one_line(w) for w in report.warnings]
    if report.exit_code != 0:
        level = CRITICAL
        errors = errors or [f"the run exited {report.exit_code}; see the run log"]
        headline = f"apply failed: {errors[0]}"
    elif warnings:
        level = WARNING
        headline = (
            f"apply completed with {len(warnings)} warning{'s' if len(warnings) != 1 else ''}: "
            f"{warnings[0]}"
        )
    else:
        level = OK
        if report.mode == "dry-run":
            headline = f"apply (dry-run) completed: {report.groups} group(s) checked, nothing moved"
        else:
            headline = (
                f"apply completed: {report.groups} group(s), "
                f"{report.moves_succeeded} move(s) executed"
            )

    # The headline already carries the first problem, so the detail lines list
    # the rest -- a dashboard shows both, and repeating one line is noise.
    items = [f"error: {e}" for e in errors] + [f"warning: {w}" for w in warnings]
    details = items[1:] if level != OK else []
    if len(details) > MAX_DETAIL_LINES:
        hidden = len(details) - MAX_DETAIL_LINES
        details = details[:MAX_DETAIL_LINES] + [f"... and {hidden} more (see the run log)"]
    details.append(
        f"pve-storage-drs {__version__}, mode {report.mode}, "
        f"finished {report.finished_at.astimezone(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}"
    )
    perfdata: tuple[tuple[str, int | float, str], ...] = (
        ("groups", report.groups, ""),
        ("moves_succeeded", report.moves_succeeded, ""),
        ("moves_failed", report.moves_failed, ""),
        ("bytes_moved", report.bytes_moved, "B"),
        ("replans", report.replans, ""),
        ("warnings", len(warnings), ""),
        ("duration", round(report.duration_seconds, 1), "s"),
    )
    return RunStatus(level, _one_line(headline), tuple(details), perfdata)


def render_status(status: RunStatus) -> str:
    """The file's exact text: level, summary ``| perfdata``, details, and a
    trailing newline -- see the module docstring for why it has this shape."""
    perf = " ".join(f"{label}={value}{unit}" for label, value, unit in status.perfdata)
    summary = f"{status.summary} | {perf}" if perf else status.summary
    lines = [status.level, summary, *status.details]
    return "\n".join(lines) + "\n"


def write_status_file(path: str, status: RunStatus) -> None:
    """Write ``status`` to ``path`` atomically, mode 0644, creating the parent
    directory if it is missing (a fresh install's directory may not exist yet,
    as with ``state.json``). Raises :class:`StatusFileError` on any failure --
    the caller decides that a monitoring file that cannot be written must not
    change what the run did (see ``cli._publish_status_file``)."""
    directory = os.path.dirname(path) or "."
    tmp_path: str | None = None
    # A separate flag rather than resetting `tmp_path`: the same mypy
    # narrowing quirk `state.save_state_atomic()` documents.
    replaced = False
    try:
        os.makedirs(directory, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(prefix=".status-", suffix=".tmp", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(render_status(status))
                fh.flush()
                os.fchmod(fh.fileno(), 0o644)
                os.fsync(fh.fileno())
            os.replace(tmp_path, path)
            replaced = True
        finally:
            if tmp_path is not None and not replaced:
                with contextlib.suppress(OSError):
                    os.remove(tmp_path)
    except OSError as exc:
        raise StatusFileError(f"could not write status file {path!r}: {exc}") from exc
