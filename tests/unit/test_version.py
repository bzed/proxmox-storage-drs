# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""``__version__`` must agree with ``pyproject.toml`` and the install instructions."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import proxmox_storage_drs

REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALL_DOCS = ("README.md", "docs/manual/00-installation.md")


def test_version_matches_pyproject() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE)
    assert match is not None, "pyproject.toml has no [project] version"
    assert proxmox_storage_drs.__version__ == match.group(1)


# Debian's dh_auto_test runs pytest in pybuild's copy of the package and tests/
# only, where neither document exists; the check runs under `make check` and
# tests.yml from a full checkout (see test_documentation.py's docstring).
@pytest.mark.skipif(
    not all((REPO_ROOT / doc).is_file() for doc in INSTALL_DOCS),
    reason="needs the full source checkout (README.md, docs/), not just the installed package",
)
def test_install_instructions_name_the_current_version() -> None:
    # The README and the manual's installation page download a released .deb by
    # version; bumping the version without them would send readers to the
    # previous release.
    for doc in INSTALL_DOCS:
        text = (REPO_ROOT / doc).read_text(encoding="utf-8")
        versions = re.findall(r"^VERSION=(\S+)", text, re.MULTILINE)
        assert versions == [proxmox_storage_drs.__version__], doc
