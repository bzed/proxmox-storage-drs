# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Every public class and function in the package has a docstring (AGENTS.md section 8.1).

The scan parses each module with :mod:`ast`. It sees methods, properties and
nested definitions as well as module-level ones, and it never imports the
package, so a module that fails to import cannot hide its own gaps.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = REPO_ROOT / "src" / "proxmox_storage_drs"


def _undocumented_public_items(path: Path) -> list[str]:
    """Return ``file:line name`` for each public class or function in ``path``
    that has no docstring. Names starting with ``_`` (private helpers and
    dunder methods) are exempt. The package uses no ``@overload`` stubs, so
    none are exempt either."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    missing: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.startswith("_"):
            continue
        if ast.get_docstring(node) is None:
            missing.append(f"{path.name}:{node.lineno} {node.name}")
    return missing


def test_every_public_definition_has_a_docstring() -> None:
    missing: list[str] = []
    for path in sorted(PACKAGE_DIR.glob("*.py")):
        missing.extend(_undocumented_public_items(path))
    assert (
        not missing
    ), "public definitions without a docstring (AGENTS.md section 8.1):\n  " + "\n  ".join(missing)


def test_scanner_flags_a_missing_docstring(tmp_path: Path) -> None:
    """The scan itself must work: it has to flag a bare public function and a
    bare public method, and accept private names and documented items."""
    module = tmp_path / "sample.py"
    module.write_text(
        '"""Sample."""\n'
        "def bare():\n"
        "    return 1\n"
        "def _private():\n"
        "    return 2\n"
        "class Documented:\n"
        '    """Has a docstring."""\n'
        "    def method(self):\n"
        "        return 3\n",
        encoding="utf-8",
    )
    missing = _undocumented_public_items(module)
    assert missing == ["sample.py:2 bare", "sample.py:8 method"]
