# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""CLI argument parsing and dispatch. See proxmox_storage_drs/cli.py."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
import yaml

from proxmox_storage_drs import __version__, cli

MINIMAL_CONFIG = {
    "schema_version": 1,
    "proxmox": {"host": "pve01.example.com", "auth": {"username": "drs@pve"}},
    "prometheus": {"url": "http://localhost:9090"},
    "groups": [{"name": "fc-tier1", "storages": [{"id": "san-a"}, {"id": "san-b"}]}],
}


def write_config(tmp_path: Path, **overrides: object) -> Path:
    data = {**MINIMAL_CONFIG, **overrides}
    path = tmp_path / "drs.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


# --------------------------------------------------------------------- --version


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["--version"]) == 0
    assert __version__ in capsys.readouterr().out


# --------------------------------------------------------------------- no command


def test_no_command_prints_usage_and_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main([]) == 2
    assert "usage:" in capsys.readouterr().err


def test_unknown_subcommand_is_a_usage_error() -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["not-a-real-command"])
    assert excinfo.value.code == 2


# --------------------------------------------------------------------- --manual


def test_manual_flag_uses_man_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def fake_which(name: str) -> str | None:
        return "/usr/bin/man"

    def fake_run(cmd: list[str], check: bool = False) -> object:
        calls.append(cmd)

        class _Result:
            returncode = 0

        return _Result()

    monkeypatch.setattr("proxmox_storage_drs.cli.shutil.which", fake_which)
    monkeypatch.setattr("proxmox_storage_drs.cli.subprocess.run", fake_run)
    assert cli.main(["--manual"]) == 0
    assert calls == [["man", "pve-storage-drs"]]


def test_manual_falls_back_when_man_exits_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    # man(1) is installed but has no entry for us (e.g. running uninstalled).
    def fake_run(cmd: list[str], check: bool = False) -> object:
        class _Result:
            returncode = 1

        return _Result()

    monkeypatch.setattr("proxmox_storage_drs.cli.shutil.which", lambda name: "/usr/bin/man")
    monkeypatch.setattr("proxmox_storage_drs.cli.subprocess.run", fake_run)
    assert cli.main(["--manual"]) == 0


def test_manual_falls_back_when_man_is_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("proxmox_storage_drs.cli.shutil.which", lambda name: None)
    assert cli.main(["help"]) == 0
    out = capsys.readouterr().out
    assert "pve-storage-drs" in out.lower() or "PVE-STORAGE-DRS" in out


def test_manual_fallback_text_with_no_source_tree_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "Path", lambda *_a, **_k: Path("/nonexistent-root-only"))
    text = cli._fallback_manual_text()
    assert "not available" in text


# --------------------------------------------------------------------- --mode


def test_apply_mode_override_no_change_is_silent(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        result = cli.apply_mode_override("dry-run", "dry-run")
    assert result == "dry-run"
    assert caplog.records == []


def test_apply_mode_override_escalation_warns(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        result = cli.apply_mode_override("dry-run", "auto")
    assert result == "auto"
    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.WARNING


def test_apply_mode_override_deescalation_is_info(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        result = cli.apply_mode_override("auto", "dry-run")
    assert result == "dry-run"
    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.INFO


# --------------------------------------------------------------------- config errors


def test_missing_config_is_reported_and_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "nope.yaml"
    assert cli.main(["-c", str(missing), "plan"]) == 1
    assert "pve-storage-drs:" in capsys.readouterr().err


# --------------------------------------------------------------------- dispatch


def test_valid_config_dispatches_to_the_not_yet_implemented_handler(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "plan"]) == 1
    err = capsys.readouterr().err
    assert "'plan' is not implemented yet" in err


def test_drs_error_from_a_handler_is_reported_and_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from proxmox_storage_drs.exceptions import DrsError

    def raising_handler(resolved: object, args: object, mode: str) -> int:
        raise DrsError("boom")

    monkeypatch.setitem(cli._COMMAND_HANDLERS, "plan", raising_handler)
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "plan"]) == 1
    assert "boom" in capsys.readouterr().err


def test_every_subcommand_is_registered() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(["show-load"])
    assert args.command == "show-load"


def test_config_loaded_and_warnings_are_logged(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_config(tmp_path)
    cli.main(["-c", str(path), "plan"])
    err_lines = [ln for ln in capsys.readouterr().err.splitlines() if ln.startswith("{")]
    events = [json.loads(ln)["event"] for ln in err_lines]
    assert "config_loaded" in events
    assert "config_warning" in events  # no saturation_load configured


def test_mode_override_flows_through_main(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_config(tmp_path)
    cli.main(["-c", str(path), "--mode", "auto", "plan"])
    err_lines = [ln for ln in capsys.readouterr().err.splitlines() if ln.startswith("{")]
    events = [json.loads(ln) for ln in err_lines]
    override_events = [e for e in events if e["event"] == "mode_override"]
    assert override_events
    assert override_events[0]["effective_mode"] == "auto"
    assert override_events[0]["level"] == "WARNING"
