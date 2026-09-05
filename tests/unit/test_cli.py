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
from proxmox_storage_drs.loadmodel import DiskLoad, GroupLoad, StorageLoad
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
    # "apply" (execute.py, phase 7+) is still a stub; "plan" is real now.
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "apply"]) == 1
    err = capsys.readouterr().err
    assert "'apply' is not implemented yet" in err


def test_drs_error_from_a_handler_is_reported_and_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from proxmox_storage_drs.exceptions import DrsError

    def raising_handler(resolved: object, args: object, mode: str) -> int:
        raise DrsError("boom")

    monkeypatch.setitem(cli._COMMAND_HANDLERS, "apply", raising_handler)
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "apply"]) == 1
    assert "boom" in capsys.readouterr().err


def test_every_subcommand_is_registered() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(["show-load"])
    assert args.command == "show-load"


def test_config_loaded_and_warnings_are_logged(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # "apply" is still a stub -- this test is about the config-load/warning
    # log events, which fire before dispatch regardless of command; "plan"
    # is real now and would need network mocking to use safely here.
    path = write_config(tmp_path)
    cli.main(["-c", str(path), "apply"])
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


def _sample_group_load() -> GroupLoad:
    """Matches `_sample_topology()`'s two disks (both on san-a) and adds
    san-b as a second, idle-for-this-group storage -- one flagged disk so
    the flagged-disk rendering path is exercised by the same fixture."""
    return GroupLoad(
        group_name="fc-tier1",
        idle=False,
        average_utilization=2.25,
        disks=(
            DiskLoad(disk_key="101:scsi0", load=3.0, flagged_reason=None),
            DiskLoad(
                disk_key="102:scsi0",
                load=0.0,
                flagged_reason="sample coverage 40% is below window.min_coverage (80%); "
                "no last known load recorded",
            ),
        ),
        storages=(
            StorageLoad(storage_id="san-a", load=3.0, utilization=3.0),
            StorageLoad(storage_id="san-b", load=0.0, utilization=0.0),
        ),
    )


def _patch_show_load_deps(
    monkeypatch: pytest.MonkeyPatch, group_load: GroupLoad | Exception
) -> None:
    monkeypatch.setattr("proxmox_storage_drs.cli.build_pve_client", lambda cfg: "fake-client")
    monkeypatch.setattr(
        "proxmox_storage_drs.cli.build_topology", lambda client, cfg: _sample_topology()
    )

    def fake_compute_group_load(
        prom_client: object, metrics: object, window: object, load_weights: object, group: object
    ) -> GroupLoad:
        if isinstance(group_load, Exception):
            raise group_load
        return group_load

    monkeypatch.setattr("proxmox_storage_drs.cli.compute_group_load", fake_compute_group_load)


def test_show_load_human_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_show_load_deps(monkeypatch, _sample_group_load())
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "show-load"]) == 0
    out = capsys.readouterr().out
    assert "Group fc-tier1" in out
    assert "101:scsi0" in out
    assert "[pinned: locked: backup]" in out
    assert "reserve short by" in out or "reserve OK" in out
    assert "ungrouped" in out
    assert "L=3.00 u=3.00" in out  # san-a's StorageLoad
    assert "ℓ 3.00" in out  # 101:scsi0's DiskLoad
    assert "102:scsi0: sample coverage 40%" in out  # the flagged disk
    # san-a's reserve is violated in this fixture (see the json test's own
    # comment) -- the gate must show the reserve override, not imbalance.
    assert "Group fc-tier1 → ACT: reserve violated on san-a" in out


def test_show_load_json_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_show_load_deps(monkeypatch, _sample_group_load())
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "--json", "show-load"]) == 0
    payload = json.loads(capsys.readouterr().out)
    group_payload = payload["groups"][0]
    assert group_payload["name"] == "fc-tier1"
    assert group_payload["load_computed"] is True
    assert group_payload["idle"] is False
    assert group_payload["load_error"] is None
    keys = {d["key"] for d in group_payload["disks"]}
    assert keys == {"101:scsi0", "102:scsi0"}
    disk_101 = next(d for d in group_payload["disks"] if d["key"] == "101:scsi0")
    assert disk_101["load"] == 3.0
    assert disk_101["load_flagged_reason"] is None
    disk_102 = next(d for d in group_payload["disks"] if d["key"] == "102:scsi0")
    assert disk_102["load_flagged_reason"] is not None
    gate = group_payload["gate"]
    assert gate["act"] is True
    assert gate["reserve_override"] is True
    assert gate["drift_fraction"] is None
    assert gate["imbalance_fraction"] is None
    assert "reserve violated on san-a" in gate["reason"]
    san_a = next(s for s in group_payload["storages"] if s["id"] == "san-a")
    # managed_used 3+2=5 TiB, largest=3 TiB, reserve=2.0*3=6 TiB, 5+6=11 > capacity 8 TiB.
    assert san_a["reserve_violated"] is True
    assert san_a["load"] == 3.0
    assert san_a["utilization"] == 3.0


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


def test_show_load_degrades_gracefully_on_a_metrics_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Prometheus outage must not hide the size/reserve report the rest of
    this command already has -- section 4's load is reported unavailable,
    not fatal."""
    from proxmox_storage_drs.exceptions import MetricsError

    _patch_show_load_deps(monkeypatch, MetricsError("connection refused"))
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "show-load"]) == 0
    out = capsys.readouterr().out
    assert "reserve short by" in out or "reserve OK" in out  # unaffected
    assert "per-disk load unavailable: connection refused" in out
    assert "Group fc-tier1\n" in out  # no gate verdict possible without a GroupLoad


def test_show_load_human_output_notes_an_idle_group(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    idle_load = GroupLoad(
        group_name="fc-tier1",
        idle=True,
        average_utilization=0.0,
        disks=(
            DiskLoad(disk_key="101:scsi0", load=0.0, flagged_reason=None),
            DiskLoad(disk_key="102:scsi0", load=0.0, flagged_reason=None),
        ),
        storages=(
            StorageLoad(storage_id="san-a", load=0.0, utilization=0.0),
            StorageLoad(storage_id="san-b", load=0.0, utilization=0.0),
        ),
    )
    _patch_show_load_deps(monkeypatch, idle_load)
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "show-load"]) == 0
    assert "idle: no measured I/O" in capsys.readouterr().out


def test_show_load_json_reports_a_metrics_error_per_group(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from proxmox_storage_drs.exceptions import MetricsError

    _patch_show_load_deps(monkeypatch, MetricsError("connection refused"))
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "--json", "show-load"]) == 0
    payload = json.loads(capsys.readouterr().out)
    group_payload = payload["groups"][0]
    assert group_payload["load_computed"] is False
    assert group_payload["idle"] is None
    assert group_payload["load_error"] == "connection refused"
    assert group_payload["gate"] is None  # no GroupLoad to evaluate gates against
    disk_101 = next(d for d in group_payload["disks"] if d["key"] == "101:scsi0")
    assert "load" not in disk_101


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


def _two_group_topology() -> Topology:
    """`_sample_topology()`'s one group plus a second, empty one -- enough
    to prove `--group` actually restricts which groups a handler visits
    (REVIEW.md R-03), without needing a second `GroupLoad` fixture for
    handlers that don't need one (`verify-storages`)."""
    base = _sample_topology()
    second = Group(name="fc-tier2", storages=base.groups[0].storages, disks=())
    return Topology(groups=(base.groups[0], second), warnings=())


def test_group_flag_restricts_verify_storages_to_the_named_group(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("proxmox_storage_drs.cli.build_pve_client", lambda cfg: "fake-client")
    monkeypatch.setattr(
        "proxmox_storage_drs.cli.build_topology", lambda client, cfg: _two_group_topology()
    )
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "--group", "fc-tier1", "verify-storages"]) == 0
    out = capsys.readouterr().out
    assert "Group fc-tier1" in out
    assert "Group fc-tier2" not in out


def test_group_flag_is_repeatable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("proxmox_storage_drs.cli.build_pve_client", lambda cfg: "fake-client")
    monkeypatch.setattr(
        "proxmox_storage_drs.cli.build_topology", lambda client, cfg: _two_group_topology()
    )
    path = write_config(tmp_path)
    args = ["-c", str(path), "--group", "fc-tier1", "--group", "fc-tier2", "verify-storages"]
    assert cli.main(args) == 0
    out = capsys.readouterr().out
    assert "Group fc-tier1" in out
    assert "Group fc-tier2" in out


def test_group_flag_with_an_unknown_name_is_a_hard_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("proxmox_storage_drs.cli.build_pve_client", lambda cfg: "fake-client")
    monkeypatch.setattr(
        "proxmox_storage_drs.cli.build_topology", lambda client, cfg: _sample_topology()
    )
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "--group", "no-such-group", "verify-storages"]) == 1
    err = capsys.readouterr().err
    assert "no-such-group" in err
    assert "fc-tier1" in err  # names the groups that do exist


# --------------------------------------------------------------------------- plan


def _patch_plan_deps(
    monkeypatch: pytest.MonkeyPatch, topology: Topology, group_load: GroupLoad
) -> None:
    monkeypatch.setattr("proxmox_storage_drs.cli.build_pve_client", lambda cfg: "fake-client")
    monkeypatch.setattr("proxmox_storage_drs.cli.build_topology", lambda client, cfg: topology)
    monkeypatch.setattr(
        "proxmox_storage_drs.cli.compute_group_load",
        lambda prom_client, metrics, window, load_weights, group: group_load,
    )


def _repairable_sample_topology() -> Topology:
    """`_sample_topology()` with san-b given more headroom (16 TiB instead
    of 8): san-a still violates (C5) exactly as in that fixture, but now
    the only possible move (101:scsi0, san-a -> san-b -- 102:scsi0 is
    pinned) actually fits at the other end too, so the plan can fully
    resolve it rather than merely improve it. `_sample_topology()` itself
    is intentionally left alone: several other tests depend on its exact
    numbers, including the fact that a 3 TiB disk does *not* fit cleanly
    into an 8 TiB, reserve_factor=2.0 storage on its own -- see
    ``test_plan_reports_a_deadlock_when_even_the_best_target_still_violates``,
    which relies on exactly that to test deadlock reporting honestly."""
    topology = _sample_topology()
    group = topology.groups[0]
    roomier_storages = tuple(
        Storage(
            id=s.id,
            capability_weight=s.capability_weight,
            reserve_factor=s.reserve_factor,
            saturation_load=s.saturation_load,
            capacity_bytes=16 * (1 << 40) if s.id == "san-b" else s.capacity_bytes,
            used_bytes=s.used_bytes,
            foreign_used_bytes=s.foreign_used_bytes,
            saferemove=s.saferemove,
            saferemove_throughput_bytes_per_sec=s.saferemove_throughput_bytes_per_sec,
        )
        for s in group.storages
    )
    roomier_group = Group(name=group.name, storages=roomier_storages, disks=group.disks)
    return Topology(groups=(roomier_group,), warnings=topology.warnings)


def test_plan_human_output_acts_via_reserve_override_and_shows_the_one_possible_move(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """san-a violates (C5); its only movable disk is 101:scsi0 (102:scsi0
    is pinned, `locked: backup`) -- moving it away is the only possible
    plan, and (with san-b's extra headroom) it fully resolves the
    violation."""
    _patch_plan_deps(monkeypatch, _repairable_sample_topology(), _sample_group_load())
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "plan"]) == 0
    out = capsys.readouterr().out
    assert "Group fc-tier1 → ACT: reserve violated on san-a" in out
    assert "101:scsi0" in out
    assert "san-a → san-b" in out
    assert "102:scsi0" not in out  # pinned -- never proposed as a move
    assert "payback" in out.lower()  # the phase-5-not-implemented caveat


def test_plan_json_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_plan_deps(monkeypatch, _repairable_sample_topology(), _sample_group_load())
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "--json", "plan"]) == 0
    payload = json.loads(capsys.readouterr().out)
    group_payload = payload["groups"][0]
    assert group_payload["gate"]["act"] is True
    assert group_payload["gate"]["reserve_override"] is True
    assert len(group_payload["moves"]) == 1
    move = group_payload["moves"][0]
    assert move["disk_key"] == "101:scsi0"
    assert move["from_storage"] == "san-a"
    assert move["to_storage"] == "san-b"
    assert move["resolves_reserve_violation"] is True
    assert move["duration_mirror_seconds"] > 0
    assert move["load_per_tib"] > 0
    assert group_payload["deadlocked"] == []
    assert group_payload["deadlock_message"] is None
    assert group_payload["before_spread"] is not None
    assert group_payload["after_spread"] is not None
    # san-a's saferemove throughput (10 MiB/s) makes the wipe of this 3 TiB
    # disk take far longer than the default 6h max_single_move_duration --
    # a real, useful case for the hard per-move duration rule to catch.
    assert move["duration_wipe_seconds"] > 0
    assert move["exceeds_max_duration"] is True
    payback = group_payload["payback"]
    assert payback["aggregate_ok"] is True  # exempted -- resolves a reserve violation
    assert payback["rejected_moves"] == ["101:scsi0"]
    assert payback["accepted"] is False  # but still blocked by the hard duration rule


def test_plan_json_output_accepts_payback_when_saferemove_is_off(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same repairable plan, but with san-a's `saferemove` off, so the
    hard duration rule no longer blocks it. This fixture's move has a real
    cost and exactly *zero* balance benefit (moving the only loaded disk
    between two storages, one of which holds nothing but a zero-load
    pinned disk, just relocates which side carries it -- `ratio` is
    genuinely 0.0, not a rounding artefact) -- it is accepted anyway
    because it resolves san-a's reserve violation, and section 13's
    "never traded against balance" applies to payback too
    (`evaluate_plan_payback()`'s own docstring)."""
    topology = _repairable_sample_topology()
    group = topology.groups[0]
    no_wipe_storages = tuple(
        Storage(
            id=s.id,
            capability_weight=s.capability_weight,
            reserve_factor=s.reserve_factor,
            saturation_load=s.saturation_load,
            capacity_bytes=s.capacity_bytes,
            used_bytes=s.used_bytes,
            foreign_used_bytes=s.foreign_used_bytes,
            saferemove=False,
            saferemove_throughput_bytes_per_sec=None,
        )
        for s in group.storages
    )
    topology = Topology(
        groups=(Group(name=group.name, storages=no_wipe_storages, disks=group.disks),),
        warnings=topology.warnings,
    )
    _patch_plan_deps(monkeypatch, topology, _sample_group_load())
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "--json", "plan"]) == 0
    payload = json.loads(capsys.readouterr().out)
    group_payload = payload["groups"][0]
    move = group_payload["moves"][0]
    assert move["duration_wipe_seconds"] == 0.0
    assert move["exceeds_max_duration"] is False
    payback = group_payload["payback"]
    assert payback["rejected_moves"] == []
    assert payback["aggregate_ok"] is True  # exempted -- resolves a reserve violation
    assert payback["accepted"] is True
    assert payback["benefit_load_seconds"] == 0.0  # genuinely zero, not a failure to compute it
    assert payback["ratio"] == 0.0  # a real cost with zero benefit -> ratio 0, still accepted


def test_plan_human_output_shows_the_payback_verdict(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_plan_deps(monkeypatch, _repairable_sample_topology(), _sample_group_load())
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "plan"]) == 0
    out = capsys.readouterr().out
    assert "payback: benefit" in out
    assert "⚠ exceeds migration.max_single_move_duration" in out
    # aggregate_ok is True here (exempted -- resolves a reserve violation), so
    # the *economic* failure line must not appear; only the hard-duration one
    # should (REVIEW.md R-05 -- these are reported separately, not conflated).
    assert "this plan's balance benefit does not outweigh its migration cost" not in out
    assert "blocked by the hard per-move duration rule" in out
    assert "101:scsi0" in out


def test_load_per_tib_is_zero_not_a_division_error_for_a_zero_size_disk() -> None:
    """REVIEW.md R-06: `move.size_bytes == 0` must not raise
    `ZeroDivisionError` -- PVE does not report zero-size disks in practice,
    but `config_schema.json` does not forbid it either, and the value comes
    from the PVE API rather than validated config."""
    from proxmox_storage_drs.schedule import ScheduledMove

    zero_size_move = ScheduledMove(
        disk_key="101:scsi0",
        vmid=101,
        device="scsi0",
        from_storage="san-a",
        to_storage="san-b",
        size_bytes=0,
        imbalance_reduction=0.0,
        resolves_reserve_violation=False,
    )
    assert cli._load_per_tib({"101:scsi0": 3.0}, zero_size_move) == 0.0


def test_render_plan_payback_lines_separates_economic_and_duration_failures() -> None:
    """REVIEW.md R-05: an economic failure (benefit < ratio*cost) and a hard
    per-move duration failure are different problems with different fixes,
    and must produce different warning text -- never the same generic
    "does not pass section 7.3's payback test" for both."""
    from proxmox_storage_drs.payback import MoveCost, PaybackResult

    def make_result(
        *, aggregate_ok: bool, rejected_moves: tuple[str, ...], resolves: bool = False
    ) -> PaybackResult:
        move_cost = MoveCost(
            disk_key="101:scsi0",
            duration_mirror_seconds=100.0,
            duration_wipe_seconds=0.0,
            cost_load_seconds=100.0,
            exceeds_max_duration=bool(rejected_moves),
            resolves_reserve_violation=resolves,
        )
        return PaybackResult(
            move_costs=(move_cost,),
            benefit_load_seconds=10.0,
            rejected_moves=rejected_moves,
            aggregate_ok=aggregate_ok,
        )

    # Economic failure only: no move exceeds the duration rule.
    economic = make_result(aggregate_ok=False, rejected_moves=())
    lines = cli._render_plan_payback_lines(economic, payback_ratio=10.0)
    text = "\n".join(lines)
    assert "does not outweigh its migration cost" in text
    assert "hard per-move duration rule" not in text

    # Hard-duration failure only: passes economically (e.g. reserve-exempt).
    duration = make_result(aggregate_ok=True, rejected_moves=("101:scsi0",), resolves=True)
    lines = cli._render_plan_payback_lines(duration, payback_ratio=10.0)
    text = "\n".join(lines)
    assert "does not outweigh its migration cost" not in text
    assert "hard per-move duration rule" in text
    assert "101:scsi0" in text

    # Both failures at once: both lines present.
    both = make_result(aggregate_ok=False, rejected_moves=("101:scsi0",))
    lines = cli._render_plan_payback_lines(both, payback_ratio=10.0)
    text = "\n".join(lines)
    assert "does not outweigh its migration cost" in text
    assert "hard per-move duration rule" in text

    # Fully accepted: neither warning line.
    accepted = make_result(aggregate_ok=True, rejected_moves=())
    lines = cli._render_plan_payback_lines(accepted, payback_ratio=10.0)
    assert len(lines) == 1


def test_plan_reports_a_deadlock_when_even_the_best_target_still_violates(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real `_sample_topology()`, unmodified: its 3 TiB 101:scsi0 does
    not fit *anywhere* in this two-storage, 8 TiB, reserve_factor=2.0 group
    without violating (C5) somewhere -- landing alone on either storage
    needs 6 TiB reserved on top of its own 3 TiB, which alone exceeds 8
    TiB. The heuristic still proposes moving it (group-wide shortfall
    drops from 3 TiB to 1 TiB, a real improvement), but the scheduler must
    refuse to actually schedule a move into a state that still violates
    the transient invariant -- reporting a deadlock is the safe, honest
    outcome, not a false all-clear."""
    _patch_plan_deps(monkeypatch, _sample_topology(), _sample_group_load())
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "--json", "plan"]) == 0
    payload = json.loads(capsys.readouterr().out)
    group_payload = payload["groups"][0]
    assert group_payload["gate"]["reserve_override"] is True  # still tries -- san-a violates
    assert group_payload["moves"] == []  # but nothing could actually be scheduled
    assert group_payload["deadlocked"] == ["101:scsi0"]
    assert group_payload["deadlock_message"] is not None
    assert "section 8.1" in group_payload["deadlock_message"]


def test_plan_after_and_payback_reflect_only_the_scheduled_moves_on_partial_deadlock(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """REVIEW.md R-02: when the scheduler can only order *some* of the
    heuristic's target moves, `after_spread` and the payback benefit must
    be computed from what actually got scheduled (`final_assignment`), not
    from the solver's full, partly-unreachable target. `run_heuristic()`
    and `order_moves()` are stubbed here so the scenario -- one move
    scheduled, one deadlocked -- is exact and deterministic, rather than
    relying on the heuristic and scheduler to happen to produce a partial
    deadlock on some fixture (that combination is `schedule.py`'s own
    concern, not this module's)."""
    from proxmox_storage_drs.config import load_config
    from proxmox_storage_drs.heuristic import (
        HeuristicResult,
        evaluate_assignment,
        group_average_utilization,
        raw_spread,
        seed_assignment,
    )
    from proxmox_storage_drs.schedule import ScheduledMove, ScheduleResult

    disks = (
        Disk(
            key="101:scsi0",
            vmid=101,
            device="scsi0",
            vm_name="a",
            node="pve01",
            size_bytes=1 * (1 << 40),
            current_storage="san-a",
            format="raw",
            pinned_reason=None,
        ),
        Disk(
            key="102:scsi0",
            vmid=102,
            device="scsi0",
            vm_name="b",
            node="pve01",
            size_bytes=1 * (1 << 40),
            current_storage="san-a",
            format="raw",
            pinned_reason=None,
        ),
    )
    storages = (
        Storage(
            id="san-a",
            capability_weight=1.0,
            reserve_factor=2.0,
            saturation_load=None,
            capacity_bytes=8 * (1 << 40),
            used_bytes=2 * (1 << 40),
            foreign_used_bytes=0,
            saferemove=False,
            saferemove_throughput_bytes_per_sec=None,
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
    topology = Topology(groups=(group,), warnings=())
    load_by_key = {"101:scsi0": 3.0, "102:scsi0": 1.0}
    group_load = GroupLoad(
        group_name="fc-tier1",
        idle=False,
        average_utilization=2.0,
        disks=(
            DiskLoad(disk_key="101:scsi0", load=3.0, flagged_reason=None),
            DiskLoad(disk_key="102:scsi0", load=1.0, flagged_reason=None),
        ),
        storages=(
            StorageLoad(storage_id="san-a", load=4.0, utilization=4.0),
            StorageLoad(storage_id="san-b", load=0.0, utilization=0.0),
        ),
    )
    _patch_plan_deps(monkeypatch, topology, group_load)
    path = write_config(tmp_path)
    resolved = load_config(str(path))
    objective = resolved.config.objective
    min_free_bytes = resolved.config.snapshot_reserve.min_free_bytes
    u_star = group_average_utilization(group, load_by_key)

    initial_breakdown = evaluate_assignment(
        group, seed_assignment(group), load_by_key, objective, min_free_bytes, u_star
    )
    # The heuristic's aspirational target: both disks move to san-b.
    target_assignment = {"101:scsi0": "san-b", "102:scsi0": "san-b"}
    target_breakdown = evaluate_assignment(
        group, target_assignment, load_by_key, objective, min_free_bytes, u_star
    )
    heuristic_result = HeuristicResult(
        assignment=target_assignment,
        breakdown=target_breakdown,
        initial_breakdown=initial_breakdown,
        repair_moves=0,
    )
    # The scheduler can only actually order 101:scsi0's move; 102:scsi0 is
    # left deadlocked, so the real reachable state keeps it on san-a.
    final_assignment = {"101:scsi0": "san-b", "102:scsi0": "san-a"}
    scheduled_move = ScheduledMove(
        disk_key="101:scsi0",
        vmid=101,
        device="scsi0",
        from_storage="san-a",
        to_storage="san-b",
        size_bytes=1 * (1 << 40),
        imbalance_reduction=1.0,
        resolves_reserve_violation=False,
    )
    schedule_result = ScheduleResult(
        order=(scheduled_move,), deadlocked=("102:scsi0",), final_assignment=final_assignment
    )
    monkeypatch.setattr("proxmox_storage_drs.cli.run_heuristic", lambda *a, **k: heuristic_result)
    monkeypatch.setattr("proxmox_storage_drs.cli.order_moves", lambda *a, **k: schedule_result)

    final_breakdown = evaluate_assignment(
        group, final_assignment, load_by_key, objective, min_free_bytes, u_star
    )
    expected_after_spread = cli._spread_fraction(
        final_breakdown.utilization, group_load.average_utilization
    )
    target_after_spread = cli._spread_fraction(
        target_breakdown.utilization, group_load.average_utilization
    )
    assert expected_after_spread != pytest.approx(target_after_spread)  # fixture sanity
    expected_benefit = (
        raw_spread(initial_breakdown, objective.spread_metric)
        - raw_spread(final_breakdown, objective.spread_metric)
    ) * resolved.config.migration.payback_horizon_seconds

    assert cli.main(["-c", str(path), "--json", "plan"]) == 0
    payload = json.loads(capsys.readouterr().out)
    group_payload = payload["groups"][0]
    assert group_payload["deadlocked"] == ["102:scsi0"]
    assert group_payload["after_spread"] == pytest.approx(expected_after_spread)
    assert group_payload["after_spread"] != pytest.approx(target_after_spread)
    assert group_payload["payback"]["benefit_load_seconds"] == pytest.approx(expected_benefit)


def test_plan_human_output_shows_the_deadlock_warning_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_plan_deps(monkeypatch, _sample_topology(), _sample_group_load())
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "plan"]) == 0
    out = capsys.readouterr().out
    assert "⚠" in out
    assert "section 8.1" in out


def _balanced_non_violating_topology() -> Topology:
    """Unlike `_sample_topology()`, san-a here does *not* violate (C5) --
    needed to reach a pure imbalance-based NO ACTION, since a reserve
    violation would otherwise always force ACT regardless of load."""
    disks = (
        Disk(
            key="101:scsi0",
            vmid=101,
            device="scsi0",
            vm_name="web01",
            node="pve01",
            size_bytes=1 * (1 << 40),
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
            size_bytes=1 * (1 << 40),
            current_storage="san-b",
            format="raw",
            pinned_reason=None,
        ),
    )
    storages = (
        Storage(
            id="san-a",
            capability_weight=1.0,
            reserve_factor=2.0,
            saturation_load=None,
            capacity_bytes=8 * (1 << 40),
            used_bytes=1 * (1 << 40),
            foreign_used_bytes=0,
            saferemove=False,
            saferemove_throughput_bytes_per_sec=None,
        ),
        Storage(
            id="san-b",
            capability_weight=1.0,
            reserve_factor=2.0,
            saturation_load=None,
            capacity_bytes=8 * (1 << 40),
            used_bytes=1 * (1 << 40),
            foreign_used_bytes=0,
            saferemove=False,
            saferemove_throughput_bytes_per_sec=None,
        ),
    )
    return Topology(groups=(Group(name="fc-tier1", storages=storages, disks=disks),), warnings=())


def test_plan_no_action_when_balanced_and_no_violation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("proxmox_storage_drs.cli.build_pve_client", lambda cfg: "fake-client")
    monkeypatch.setattr(
        "proxmox_storage_drs.cli.build_topology",
        lambda client, cfg: _balanced_non_violating_topology(),
    )
    balanced = GroupLoad(
        group_name="fc-tier1",
        idle=False,
        average_utilization=1.5,
        disks=(
            DiskLoad(disk_key="101:scsi0", load=1.5, flagged_reason=None),
            DiskLoad(disk_key="102:scsi0", load=1.5, flagged_reason=None),
        ),
        storages=(
            StorageLoad(storage_id="san-a", load=1.5, utilization=1.5),
            StorageLoad(storage_id="san-b", load=1.5, utilization=1.5),
        ),
    )
    monkeypatch.setattr(
        "proxmox_storage_drs.cli.compute_group_load",
        lambda prom_client, metrics, window, load_weights, group: balanced,
    )
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "plan"]) == 0
    out = capsys.readouterr().out
    assert "NO ACTION" in out
    assert "1." not in out  # no numbered move lines when there is nothing to schedule


def test_plan_reports_a_metrics_error_per_group(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from proxmox_storage_drs.exceptions import MetricsError

    monkeypatch.setattr("proxmox_storage_drs.cli.build_pve_client", lambda cfg: "fake-client")
    monkeypatch.setattr(
        "proxmox_storage_drs.cli.build_topology", lambda client, cfg: _sample_topology()
    )

    def raise_metrics_error(
        prom_client: object, metrics: object, window: object, load_weights: object, group: object
    ) -> None:
        raise MetricsError("connection refused")

    monkeypatch.setattr("proxmox_storage_drs.cli.compute_group_load", raise_metrics_error)
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "plan"]) == 0
    out = capsys.readouterr().out
    assert "plan unavailable: connection refused" in out


def test_mode_override_flows_through_main(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # "apply" is still a stub (no network access) -- this test is about the
    # mode-override log happening before dispatch, for any command, not
    # about "plan" specifically. "plan" itself is real now and would try a
    # genuine network connection here if used unmocked (.agents/testing.md).
    path = write_config(tmp_path)
    cli.main(["-c", str(path), "--mode", "auto", "apply"])
    err_lines = [ln for ln in capsys.readouterr().err.splitlines() if ln.startswith("{")]
    events = [json.loads(ln) for ln in err_lines]
    override_events = [e for e in events if e["event"] == "mode_override"]
    assert override_events
    assert override_events[0]["effective_mode"] == "auto"
    assert override_events[0]["level"] == "WARNING"
