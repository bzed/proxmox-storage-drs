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
    assert "does not pass section 7.3's payback test" in out


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
