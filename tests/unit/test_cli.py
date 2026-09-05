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
from proxmox_storage_drs.topology import Disk, Group, Storage, Topology

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


def test_verify_metrics_dispatches_and_renders_human(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from proxmox_storage_drs.metrics import Finding, VerifyMetricsReport

    fake_report = VerifyMetricsReport(
        findings=(Finding("info", "all good"),),
        sample_series={},
        coverage_by_disk={},
        observed_spacing_seconds=300.0,
    )
    monkeypatch.setattr("proxmox_storage_drs.cli.verify_metrics", lambda *a, **k: fake_report)
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "verify-metrics"]) == 0
    assert "all good" in capsys.readouterr().out


def test_verify_metrics_json_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from proxmox_storage_drs.metrics import DiskKey, Finding, VerifyMetricsReport

    fake_report = VerifyMetricsReport(
        findings=(Finding("error", "bad"),),
        sample_series={},
        coverage_by_disk={DiskKey(101, "scsi0"): 0.9},
        observed_spacing_seconds=None,
    )
    monkeypatch.setattr("proxmox_storage_drs.cli.verify_metrics", lambda *a, **k: fake_report)
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "--json", "verify-metrics"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["coverage_by_disk"] == {"101:scsi0": 0.9}


def _sample_topology() -> Topology:
    disks = (
        Disk(
            key="101:scsi0",
            vmid=101,
            device="scsi0",
            vm_name="web01",
            node="pve01",
            size_bytes=3 * (1 << 40),
            current_storage="san-a",
            format="raw",
            pinned_reason=None,
        ),
        Disk(
            key="102:scsi0",
            vmid=102,
            device="scsi0",
            vm_name="db01",
            node="pve01",
            size_bytes=2 * (1 << 40),
            current_storage="san-a",
            format="raw",
            pinned_reason="locked: backup",
        ),
    )
    storages = (
        Storage(
            id="san-a",
            capability_weight=1.0,
            reserve_factor=2.0,
            saturation_load=None,
            capacity_bytes=8 * (1 << 40),
            used_bytes=3 * (1 << 40),
            foreign_used_bytes=0,
            saferemove=True,
            saferemove_throughput_bytes_per_sec=10 * (1 << 20),
        ),
        Storage(
            id="san-b",
            capability_weight=1.0,
            reserve_factor=2.0,
            saturation_load=None,
            capacity_bytes=8 * (1 << 40),
            used_bytes=0,
            foreign_used_bytes=0,
            saferemove=False,
            saferemove_throughput_bytes_per_sec=None,
        ),
    )
    group = Group(name="fc-tier1", storages=storages, disks=disks)
    return Topology(groups=(group,), warnings=("108:scsi0 is ungrouped, not managed",))


# --------------------------------------------------------------------- show-load


def test_show_load_human_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("proxmox_storage_drs.cli.build_pve_client", lambda cfg: "fake-client")
    monkeypatch.setattr(
        "proxmox_storage_drs.cli.build_topology", lambda client, cfg: _sample_topology()
    )
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "show-load"]) == 0
    out = capsys.readouterr().out
    assert "Group fc-tier1" in out
    assert "101:scsi0" in out
    assert "[pinned: locked: backup]" in out
    assert "reserve short by" in out or "reserve OK" in out
    assert "ungrouped" in out
    assert "not yet computed" in out


def test_show_load_json_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("proxmox_storage_drs.cli.build_pve_client", lambda cfg: "fake-client")
    monkeypatch.setattr(
        "proxmox_storage_drs.cli.build_topology", lambda client, cfg: _sample_topology()
    )
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "--json", "show-load"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["load_computed"] is False
    group_payload = payload["groups"][0]
    assert group_payload["name"] == "fc-tier1"
    keys = {d["key"] for d in group_payload["disks"]}
    assert keys == {"101:scsi0", "102:scsi0"}
    san_a = next(s for s in group_payload["storages"] if s["id"] == "san-a")
    # managed_used 3+2=5 TiB, largest=3 TiB, reserve=2.0*3=6 TiB, 5+6=11 > capacity 8 TiB.
    assert san_a["reserve_violated"] is True


def test_show_load_reports_a_pve_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from proxmox_storage_drs.exceptions import PveApiError

    def raise_pve_error(client: object, cfg: object) -> None:
        raise PveApiError("cluster unreachable")

    monkeypatch.setattr("proxmox_storage_drs.cli.build_pve_client", lambda cfg: "fake-client")
    monkeypatch.setattr("proxmox_storage_drs.cli.build_topology", raise_pve_error)
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "show-load"]) == 1
    assert "cluster unreachable" in capsys.readouterr().err


# --------------------------------------------------------------------- verify-storages


def test_verify_storages_human_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("proxmox_storage_drs.cli.build_pve_client", lambda cfg: "fake-client")
    monkeypatch.setattr(
        "proxmox_storage_drs.cli.build_topology", lambda client, cfg: _sample_topology()
    )
    path = write_config(tmp_path, gates={"cooldown_per_storage": "1s"})
    assert cli.main(["-c", str(path), "verify-storages"]) == 0
    out = capsys.readouterr().out
    assert "san-a  saferemove=on" in out
    assert "implied wipe time" in out
    assert "gates.cooldown_per_storage" in out  # 1s is far shorter than the implied wipe
    assert "san-b  saferemove=off" in out
    assert "no wipe-time check" in out


def test_verify_storages_json_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("proxmox_storage_drs.cli.build_pve_client", lambda cfg: "fake-client")
    monkeypatch.setattr(
        "proxmox_storage_drs.cli.build_topology", lambda client, cfg: _sample_topology()
    )
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "--json", "verify-storages"]) == 0
    payload = json.loads(capsys.readouterr().out)
    san_a = next(s for s in payload["groups"][0]["storages"] if s["id"] == "san-a")
    assert san_a["saferemove"] is True
    assert san_a["implied_wipe_seconds"] == pytest.approx(3 * (1 << 40) / (10 * (1 << 20)))
    san_b = next(s for s in payload["groups"][0]["storages"] if s["id"] == "san-b")
    assert san_b["implied_wipe_seconds"] is None


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
