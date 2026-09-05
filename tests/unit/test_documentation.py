# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The cross-reference tests .agents/documentation.md promises.

These are what keep the manual, the manpage, the config schema and the CLI's
own option definitions from drifting apart -- see the "The tests that keep
it honest" table there. Nothing here talks to a live cluster or Prometheus;
it is all static analysis of files already in the tree.

Everything here except the schema itself (loaded the same way ``config.py``
loads it at runtime, via ``importlib.resources`` on the installed package)
needs the full source checkout: ``config/``, ``man/`` and ``docs/`` sit
beside, not inside, the installed ``proxmox_storage_drs`` package, so
Debian's ``dh_auto_test`` -- which runs pytest against pybuild's isolated
copy of only the package and ``tests/`` -- cannot see them. That copy is
real and deliberate (`.agents/packaging.md`), not a bug to work around, so
each such test is skipped when its sibling file is absent rather than
failing the Debian build; the checks still run in full under `make check`
and in tests.yml's plain `python3 -m pytest` from a full checkout, which is
where they belong.
"""

from __future__ import annotations

import importlib.resources
import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from proxmox_storage_drs import cli, config

REPO_ROOT = Path(__file__).resolve().parents[2]
MANPAGE_SRC = REPO_ROOT / "man" / "pve-storage-drs.1.md"
MANUAL_CONFIG_PAGE = REPO_ROOT / "docs" / "manual" / "10-configuration.md"
EXAMPLE_CONFIG = REPO_ROOT / "config" / "drs.example.yaml"

needs_full_checkout = pytest.mark.skipif(
    not (MANPAGE_SRC.is_file() and MANUAL_CONFIG_PAGE.is_file() and EXAMPLE_CONFIG.is_file()),
    reason="needs the full source checkout (config/, man/, docs/), not just the installed package",
)


def _load_schema() -> dict[str, Any]:
    # The same package resource config.py itself loads at runtime -- present
    # under both a dev checkout and pybuild's isolated build, unlike
    # config/man/docs, which live outside the installed package.
    text = (
        importlib.resources.files("proxmox_storage_drs")
        .joinpath("config_schema.json")
        .read_text(encoding="utf-8")
    )
    schema: dict[str, Any] = json.loads(text)
    return schema


def _flatten_schema_keys(schema: dict[str, Any], prefix: str = "") -> set[str]:
    """Every documentable leaf path in the schema, e.g. ``groups[].storages[].id``.

    An array of objects contributes a ``[]`` segment and recurses into its
    item schema; an array of scalars (``exclude.vmids``,
    ``execution.time_windows[].days``) is one leaf, not further expanded.
    """
    schema_type = schema.get("type")
    if schema_type == "object":
        properties = schema.get("properties", {})
        if not properties:
            return {prefix} if prefix else set()
        keys: set[str] = set()
        for name, sub_schema in properties.items():
            path = f"{prefix}.{name}" if prefix else name
            keys |= _flatten_schema_keys(sub_schema, path)
        return keys
    if schema_type == "array":
        item_schema = schema.get("items", {})
        if item_schema.get("type") == "object":
            return _flatten_schema_keys(item_schema, prefix + "[]")
        return {prefix}
    return {prefix}


def _manual_documented_keys() -> set[str]:
    """Every ``### `key.path` `` (optionally ``a`` / ``b``) heading in the manual."""
    text = MANUAL_CONFIG_PAGE.read_text(encoding="utf-8")
    keys: set[str] = set()
    for line in text.splitlines():
        if not line.startswith("### "):
            continue
        keys.update(re.findall(r"`([^`]+)`", line))
    return keys


# ------------------------------------------------------------------ schema


def test_schema_flatten_matches_known_shape() -> None:
    """Sanity check on the flattener itself against a small fixed schema."""
    schema = {
        "type": "object",
        "properties": {
            "a": {"type": "string"},
            "b": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"c": {"type": "number"}},
                },
            },
            "d": {"type": "array", "items": {"type": "string"}},
        },
    }
    assert _flatten_schema_keys(schema) == {"a", "b[].c", "d"}


@needs_full_checkout
def test_manual_covers_every_schema_key() -> None:
    schema_keys = _flatten_schema_keys(_load_schema())
    documented = _manual_documented_keys()
    missing = sorted(schema_keys - documented)
    assert not missing, f"config keys with no manual entry: {missing}"


@needs_full_checkout
def test_manual_does_not_document_a_nonexistent_key() -> None:
    schema_keys = _flatten_schema_keys(_load_schema())
    documented = _manual_documented_keys()
    extra = sorted(documented - schema_keys)
    assert not extra, f"manual documents keys not in the schema: {extra}"


@needs_full_checkout
def test_example_config_validates_against_the_schema() -> None:
    resolved = config.load_config(str(EXAMPLE_CONFIG), env={})
    assert resolved.config.groups  # loaded something real, not a stub


@needs_full_checkout
def test_example_config_carries_every_top_level_schema_key() -> None:
    """A knob missing from the example entirely would ship with an unseen default."""
    with open(EXAMPLE_CONFIG) as fh:
        raw = yaml.safe_load(fh)
    schema = _load_schema()
    top_level = set(schema["properties"])
    # load_weights/objective/etc. are all present; only genuinely optional
    # blocks that legitimately default to "absent" are allowed to be missing.
    missing = top_level - set(raw)
    assert not missing, f"config/drs.example.yaml has no block for: {missing}"


# ------------------------------------------------------------------- manpage


def _manpage_source_text() -> str:
    return MANPAGE_SRC.read_text(encoding="utf-8")


@needs_full_checkout
def test_help_covers_every_global_option() -> None:
    parser = cli.build_parser()
    text = _manpage_source_text()
    missing = []
    for action in parser._actions:
        for option in action.option_strings:
            if not re.search(rf"\*\*{re.escape(option)}\*\*", text):
                missing.append(option)
    assert not missing, f"options missing from {MANPAGE_SRC.name} OPTIONS: {missing}"


@needs_full_checkout
def test_manpage_names_every_subcommand() -> None:
    text = _manpage_source_text()
    missing = [name for name in cli._SUBCOMMANDS if f"**{name}**" not in text]
    assert not missing, f"subcommands missing from {MANPAGE_SRC.name}: {missing}"


@needs_full_checkout
@pytest.mark.parametrize("section", ["NAME", "SYNOPSIS", "OPTIONS", "EXIT STATUS", "AUTHOR"])
def test_manpage_has_required_sections(section: str) -> None:
    text = _manpage_source_text()
    assert re.search(rf"^# {re.escape(section)}$", text, re.MULTILINE), section
