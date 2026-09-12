# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared pytest fixtures.

``logging`` is process-global state, and
``logging_setup.configure_logging()`` (which every ``cli.main()`` call runs)
sets a level on the ``proxmox_storage_drs`` logger and replaces the root
handler. Without the reset below, a test that runs a command leaks its
verbosity into every test that runs afterwards -- which showed up exactly
once, as a ``caplog``-based topology test passing alone and failing in the
suite, and would otherwise keep showing up as order-dependent flakes for
whoever adds the next logging assertion.
"""

from __future__ import annotations

import logging
from typing import Iterator

import pytest

from proxmox_storage_drs.logging_setup import PACKAGE_LOGGER


@pytest.fixture(autouse=True)
def _restore_logging_state() -> Iterator[None]:
    package = logging.getLogger(PACKAGE_LOGGER)
    root = logging.getLogger()
    saved = (package.level, package.propagate, list(root.handlers), root.level)
    yield
    package.setLevel(saved[0])
    package.propagate = saved[1]
    root.handlers = saved[2]
    root.setLevel(saved[3])
