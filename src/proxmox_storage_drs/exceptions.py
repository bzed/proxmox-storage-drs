# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Exception hierarchy for the project.

Every error the tool can raise deliberately (as opposed to a bug surfacing as
an unhandled built-in exception) is a subclass of :class:`DrsError`, so
``cli.py`` can catch one type at its boundary, log it with context and exit
non-zero -- see AGENTS.md section 5 ("no bare except").
"""

from __future__ import annotations


class DrsError(Exception):
    """Base class for every error this project raises on purpose."""


class ConfigError(DrsError):
    """The configuration file is missing, unreadable or fails validation.

    See IMPLEMENTATION_PLAN.md section 11: an explicitly requested config that
    is invalid is always a hard failure, never a fallback to the default.
    """


class MetricsError(DrsError):
    """Prometheus could not be queried, or the response was unusable.

    See IMPLEMENTATION_PLAN.md section 3.3/3.4.
    """


class PveApiError(DrsError):
    """The Proxmox VE API returned an error or an unusable response.

    See IMPLEMENTATION_PLAN.md section 3.5.
    """


class TopologyError(DrsError):
    """The cluster topology could not be built from the API responses.

    See IMPLEMENTATION_PLAN.md section 3.5/3.6.
    """


class SolverError(DrsError):
    """Neither solver backend could produce a feasible or heuristic plan.

    See IMPLEMENTATION_PLAN.md section 5.5.
    """


class SchedulingDeadlock(DrsError):
    """No pending move in a plan is individually feasible right now.

    See IMPLEMENTATION_PLAN.md section 8.3. This is a reportable outcome, not
    a bug: the caller is expected to catch it and report the blocking set.
    """


class ExecutionError(DrsError):
    """A migration failed, or a precondition for executing one did not hold.

    See IMPLEMENTATION_PLAN.md section 9.4.
    """
