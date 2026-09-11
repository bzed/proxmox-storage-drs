# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Storage DRS for Proxmox VE 9.2.

Balances disk I/O load across configurable groups of shared storages by
live-migrating individual VM disks. See ``IMPLEMENTATION_PLAN.md`` at the
repository root for the full specification; ``__version__`` below and
``pyproject.toml`` must always agree, which ``tests/unit/test_version.py``
asserts.
"""

from __future__ import annotations

__version__ = "0.1.1"
