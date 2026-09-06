# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""CLI argument parsing and dispatch. See proxmox_storage_drs/cli.py."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from proxmox_storage_drs import __version__, cli
from proxmox_storage_drs.config import ResolvedConfig
from proxmox_storage_drs.execute import MoveOutcome
from proxmox_storage_drs.heuristic import ObjectiveBreakdown
from proxmox_storage_drs.loadmodel import DiskLoad, GroupLoad, StorageLoad
from proxmox_storage_drs.schedule import ScheduledMove
from proxmox_storage_drs.state import empty_state, load_state
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


def _fake_build_topology(topology: Topology) -> object:
    """A ``cli.build_topology`` stand-in that ignores the ``state``/``now``
    cooldown parameters entirely -- every test that only cares about the
    topology itself uses this, so a future parameter added to the real
    function does not require updating every call site by hand."""

    def build(client: object, cfg: object, state: object = None, now: object = None) -> Topology:
        return topology

    return build


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
    # "explain" (not scoped to any phase yet) is still a stub; "plan" and
    # "apply" are both real now (phases 4-7).
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "explain"]) == 1
    err = capsys.readouterr().err
    assert "'explain' is not implemented yet" in err


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
        "proxmox_storage_drs.cli.build_topology", _fake_build_topology(_sample_topology())
    )

    def fake_compute_group_load(
        prom_client: object,
        metrics: object,
        window: object,
        load_weights: object,
        group: object,
        last_known_loads: object = None,
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

    def raise_pve_error(
        client: object, cfg: object, state: object = None, now: object = None
    ) -> None:
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


# --------------------------------------------------------------------- state.json wiring


def _no_reserve_violation_topology() -> Topology:
    """Two storages, generously sized -- unlike `_sample_topology()`, no
    (C4)/(C5) violation anywhere, so the drift/imbalance gates (not the
    reserve override) are what actually decide act/no-act, which is what
    these tests need to isolate."""
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
            current_storage="san-b",
            format="raw",
            pinned_reason=None,
        ),
    )
    storages = tuple(
        Storage(
            id=sid,
            capability_weight=1.0,
            reserve_factor=2.0,
            saturation_load=None,
            capacity_bytes=100 * (1 << 40),
            used_bytes=1 * (1 << 40),
            foreign_used_bytes=0,
            saferemove=False,
            saferemove_throughput_bytes_per_sec=None,
        )
        for sid in ("san-a", "san-b")
    )
    return Topology(groups=(Group(name="fc-tier1", storages=storages, disks=disks),), warnings=())


def _imbalanced_group_load() -> GroupLoad:
    """san-a all the load, san-b none -- imbalance is 200% of `u*`, far
    above the default `gates.imbalance_threshold` (20%), so this group ACTs
    whenever the drift gate does not intervene first."""
    return GroupLoad(
        group_name="fc-tier1",
        idle=False,
        average_utilization=5.0,
        disks=(
            DiskLoad(disk_key="101:scsi0", load=10.0, flagged_reason=None),
            DiskLoad(disk_key="102:scsi0", load=0.0, flagged_reason=None),
        ),
        storages=(
            StorageLoad(storage_id="san-a", load=10.0, utilization=10.0),
            StorageLoad(storage_id="san-b", load=0.0, utilization=0.0),
        ),
    )


def test_show_load_acts_on_imbalance_when_there_is_no_state_json_yet(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Baseline for the next test: with no `state.json` at all,
    `last_load` is `None`, the drift gate is skipped outright (section 6's
    own first-run rule), and this fixture's 200% imbalance triggers ACT."""
    monkeypatch.setattr("proxmox_storage_drs.cli.build_pve_client", lambda cfg: "fake-client")
    monkeypatch.setattr(
        "proxmox_storage_drs.cli.build_topology",
        _fake_build_topology(_no_reserve_violation_topology()),
    )
    monkeypatch.setattr(
        "proxmox_storage_drs.cli.compute_group_load",
        lambda prom_client, metrics, window, load_weights, group, last_known_loads=None: (
            _imbalanced_group_load()
        ),
    )
    state_path = tmp_path / "state.json"
    path = write_config(tmp_path, state={"path": str(state_path)})
    assert cli.main(["-c", str(path), "show-load"]) == 0
    out = capsys.readouterr().out
    assert "ACT: imbalance" in out


def test_show_load_gate_reflects_real_drift_history_from_state_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same fixture as above, except `state.json` now records a
    `last_balance` identical to the current load -- zero drift -- which
    must suppress the ACT the imbalance alone would otherwise trigger.
    This is the actual behavioural payoff of state.py's wiring into
    `show-load`: the gate verdict now depends on real history, not
    `last_load=None` pretending every run is the first one ever."""
    from proxmox_storage_drs.state import LastBalance, State, save_state_atomic

    monkeypatch.setattr("proxmox_storage_drs.cli.build_pve_client", lambda cfg: "fake-client")
    monkeypatch.setattr(
        "proxmox_storage_drs.cli.build_topology",
        _fake_build_topology(_no_reserve_violation_topology()),
    )
    monkeypatch.setattr(
        "proxmox_storage_drs.cli.compute_group_load",
        lambda prom_client, metrics, window, load_weights, group, last_known_loads=None: (
            _imbalanced_group_load()
        ),
    )
    state_path = tmp_path / "state.json"
    save_state_atomic(
        str(state_path),
        State(
            last_balance=LastBalance(
                at="2026-09-05T00:00:00Z",
                load_vector={"fc-tier1:101:scsi0": 10.0, "fc-tier1:102:scsi0": 0.0},
            )
        ),
    )
    path = write_config(tmp_path, state={"path": str(state_path)})
    assert cli.main(["-c", str(path), "show-load"]) == 0
    out = capsys.readouterr().out
    assert "NO ACTION: drift" in out
    assert "below gates.drift_threshold" in out


def test_plan_gate_also_reflects_real_drift_history_from_state_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same drift-suppression scenario as `show-load`'s, through `plan` --
    the two commands share `_last_loads_by_group()`, not two independent
    readings of `state.json` (AGENTS.md section 5)."""
    from proxmox_storage_drs.state import LastBalance, State, save_state_atomic

    _patch_plan_deps(monkeypatch, _no_reserve_violation_topology(), _imbalanced_group_load())
    state_path = tmp_path / "state.json"
    save_state_atomic(
        str(state_path),
        State(
            last_balance=LastBalance(
                at="2026-09-05T00:00:00Z",
                load_vector={"fc-tier1:101:scsi0": 10.0, "fc-tier1:102:scsi0": 0.0},
            )
        ),
    )
    path = write_config(tmp_path, state={"path": str(state_path)})
    assert cli.main(["-c", str(path), "plan"]) == 0
    out = capsys.readouterr().out
    assert "NO ACTION: drift" in out
    assert "below gates.drift_threshold" in out


def test_plan_passes_active_storage_cooldowns_to_the_heuristic(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`_handle_plan()` must compute `state.active_storage_cooldowns()` for
    this group and pass it through to `run_heuristic()` -- checked by
    spying on the real function (still exercised, not replaced) rather
    than needing a full rebalancing scenario to observe the effect only
    indirectly."""
    from datetime import datetime, timedelta, timezone

    import proxmox_storage_drs.heuristic as heuristic_module
    from proxmox_storage_drs.state import Cooldowns, State, save_state_atomic, storage_state_key

    real_run_heuristic = heuristic_module.run_heuristic
    captured: dict[str, object] = {}

    def spy(*args: object, **kwargs: object) -> object:
        captured["cooldown_storages"] = kwargs.get(
            "cooldown_storages", args[5] if len(args) > 5 else frozenset()
        )
        return real_run_heuristic(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr("proxmox_storage_drs.cli.run_heuristic", spy)
    _patch_plan_deps(monkeypatch, _sample_topology(), _sample_group_load())
    state_path = tmp_path / "state.json"
    # 30 minutes ago, relative to whenever this test actually runs -- cli.py
    # uses the real clock (datetime.now(timezone.utc)) for `now`, so this
    # timestamp cannot be a fixed literal without becoming flaky.
    recent = (datetime.now(timezone.utc) - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    save_state_atomic(
        str(state_path),
        State(cooldowns=Cooldowns(storage={storage_state_key("fc-tier1", "san-b"): recent})),
    )
    path = write_config(tmp_path, state={"path": str(state_path)})

    assert cli.main(["-c", str(path), "plan"]) == 0
    assert captured["cooldown_storages"] == frozenset({"san-b"})


# --------------------------------------------------------------------- verify-storages


def test_verify_storages_human_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("proxmox_storage_drs.cli.build_pve_client", lambda cfg: "fake-client")
    monkeypatch.setattr(
        "proxmox_storage_drs.cli.build_topology", _fake_build_topology(_sample_topology())
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
        "proxmox_storage_drs.cli.build_topology", _fake_build_topology(_sample_topology())
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
        "proxmox_storage_drs.cli.build_topology", _fake_build_topology(_two_group_topology())
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
        "proxmox_storage_drs.cli.build_topology", _fake_build_topology(_two_group_topology())
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
        "proxmox_storage_drs.cli.build_topology", _fake_build_topology(_sample_topology())
    )
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "--group", "no-such-group", "verify-storages"]) == 1
    err = capsys.readouterr().err
    assert "no-such-group" in err
    assert "fc-tier1" in err  # names the groups that do exist


# --------------------------------------------------------------------------- plan


def _fake_reconcile_inflight(
    client: object, state: object, auth: object
) -> tuple[frozenset[int], object]:
    """Every `apply` test here uses `build_pve_client`'s "fake-client"
    string stand-in, which `crashrecovery.reconcile_inflight()`'s own
    `client.cluster_tasks()`/`client.task_status()` calls cannot run
    against -- this is `_handle_apply()`'s crash-recovery scan finding
    nothing in flight and leaving ``state`` untouched, the ordinary case
    every test not specifically about that scan should get by default
    (see `test_crashrecovery.py` for the scan's own unit tests, and
    `test_reconcile_inflight_and_fold_exclusions_merges_discovered_vmids`
    below for `_handle_apply()`'s wiring of a non-empty result)."""
    return frozenset(), state


def test_reconcile_inflight_and_fold_exclusions_merges_discovered_vmids(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Section 13: a vmid `crashrecovery.reconcile_inflight()` reports is
    folded into ``exclude.vmids`` on the *returned* `ResolvedConfig`
    -- reusing `topology.py`'s existing (C2) pin (AGENTS.md section 5)
    rather than a second exclusion mechanism -- deduplicated against
    whatever the config already excluded."""

    def fake_reconcile(
        client: object, state: object, auth: object
    ) -> tuple[frozenset[int], object]:
        assert client == "fake-client"
        return frozenset({101, 105}), state

    monkeypatch.setattr("proxmox_storage_drs.cli.reconcile_inflight", fake_reconcile)
    resolved = _resolved_config(tmp_path, exclude={"vmids": [105, 200]})
    box = cli._InflightStateBox(empty_state())
    new_resolved, new_state = cli._reconcile_inflight_and_fold_exclusions(
        "fake-client", resolved, box  # type: ignore[arg-type]
    )
    assert new_resolved.config.exclude.vmids == (101, 105, 200)
    # The original ResolvedConfig is untouched -- callers that still hold
    # a reference to it (there are none today, but nothing here should
    # assume otherwise) must not see the fold-in reach through it.
    assert resolved.config.exclude.vmids == (105, 200)
    assert new_state is box.value


def test_reconcile_inflight_and_fold_exclusions_is_a_noop_when_nothing_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("proxmox_storage_drs.cli.reconcile_inflight", _fake_reconcile_inflight)
    resolved = _resolved_config(tmp_path)
    box = cli._InflightStateBox(empty_state())
    new_resolved, _new_state = cli._reconcile_inflight_and_fold_exclusions(
        "fake-client", resolved, box  # type: ignore[arg-type]
    )
    assert new_resolved is resolved


def _patch_plan_deps(
    monkeypatch: pytest.MonkeyPatch, topology: Topology, group_load: GroupLoad
) -> None:
    monkeypatch.setattr("proxmox_storage_drs.cli.build_pve_client", lambda cfg: "fake-client")
    monkeypatch.setattr("proxmox_storage_drs.cli.build_topology", _fake_build_topology(topology))
    monkeypatch.setattr(
        "proxmox_storage_drs.cli.compute_group_load",
        lambda prom_client, metrics, window, load_weights, group, last_known_loads=None: group_load,
    )
    monkeypatch.setattr("proxmox_storage_drs.cli.reconcile_inflight", _fake_reconcile_inflight)


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


class _StubForecaster:
    """A `Forecaster` whose `predict()` always returns the same, huge
    upper bound regardless of input -- deterministically triggers section
    7.3's saturation guard without needing to hand-derive a real
    quantile/seasonal_naive/holt_winters number."""

    def __init__(self, upper_bound: float) -> None:
        self._upper_bound = upper_bound

    def required_range(self) -> object:
        return None

    def predict(self, series: object, horizon: object) -> object:
        from proxmox_storage_drs.forecast import Forecast

        return Forecast(point_estimate=0.0, upper_bound=self._upper_bound)


def test_plan_json_output_defers_a_move_via_the_saturation_guard(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """san-a (the source, and the only storage with any disk currently
    resident -- san-b starts empty in this fixture) configures a tight
    `saturation_load` -- with `cli.build_forecaster()` stubbed to always
    forecast a huge upper bound, the move is deferred by section 7.3's
    guard, not merely scored, and `deferred_moves` (not `rejected_moves`)
    is what reports it."""
    topology = _repairable_sample_topology()
    group = topology.groups[0]
    storages = tuple(
        Storage(
            id=s.id,
            capability_weight=s.capability_weight,
            reserve_factor=s.reserve_factor,
            saturation_load=10.0 if s.id == "san-a" else s.saturation_load,
            capacity_bytes=s.capacity_bytes,
            used_bytes=s.used_bytes,
            foreign_used_bytes=s.foreign_used_bytes,
            saferemove=False,
            saferemove_throughput_bytes_per_sec=None,
        )
        for s in group.storages
    )
    topology = Topology(
        groups=(Group(name=group.name, storages=storages, disks=group.disks),),
        warnings=topology.warnings,
    )
    _patch_plan_deps(monkeypatch, topology, _sample_group_load())
    monkeypatch.setattr(
        "proxmox_storage_drs.cli.build_forecaster", lambda *a, **k: _StubForecaster(1000.0)
    )
    monkeypatch.setattr("proxmox_storage_drs.cli.compute_disk_load_series", lambda *a, **k: {})
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "--json", "plan"]) == 0
    payload = json.loads(capsys.readouterr().out)
    payback = payload["groups"][0]["payback"]
    assert payback["deferred_moves"] == ["101:scsi0"]
    assert payback["rejected_moves"] == []  # a defer is not a hard-duration rejection
    assert payback["accepted"] is False


def test_apply_excludes_a_saturation_deferred_move_from_execution(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`_apply_payback_gate()` must exclude a deferred move from what it
    hands to `execute_plan()`, exactly like a hard-duration-rejected one
    -- exercised here via `dry-run`, which reports every move's outcome
    without needing a fake PVE API at all."""
    topology = _repairable_sample_topology()
    group = topology.groups[0]
    storages = tuple(
        Storage(
            id=s.id,
            capability_weight=s.capability_weight,
            reserve_factor=s.reserve_factor,
            saturation_load=10.0 if s.id == "san-a" else s.saturation_load,
            capacity_bytes=s.capacity_bytes,
            used_bytes=s.used_bytes,
            foreign_used_bytes=s.foreign_used_bytes,
            saferemove=False,
            saferemove_throughput_bytes_per_sec=None,
        )
        for s in group.storages
    )
    topology = Topology(
        groups=(Group(name=group.name, storages=storages, disks=group.disks),),
        warnings=topology.warnings,
    )
    _patch_plan_deps(monkeypatch, topology, _sample_group_load())
    monkeypatch.setattr(
        "proxmox_storage_drs.cli.build_forecaster", lambda *a, **k: _StubForecaster(1000.0)
    )
    monkeypatch.setattr("proxmox_storage_drs.cli.compute_disk_load_series", lambda *a, **k: {})
    path = write_config(tmp_path, state={"path": str(tmp_path / "state.json")})
    assert cli.main(["-c", str(path), "--mode", "dry-run", "apply"]) == 0
    out = capsys.readouterr().out
    assert "101:scsi0" in out
    assert "skipped: deferred: section 7.3 saturation guard" in out
    assert "would_move" not in out  # the only move in this plan was deferred, never executed


def test_plan_json_output_saturation_guard_is_skipped_without_any_saturation_load(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """No storage in the group configures `saturation_load` -- the guard
    must not even call `compute_disk_load_series()`/`build_forecaster()`,
    matching the plan's own "loses only this one advisory check, at no
    Prometheus cost" promise."""

    def fail(*_a: object, **_k: object) -> None:
        raise AssertionError("the saturation guard must not fetch anything when unconfigured")

    _patch_plan_deps(monkeypatch, _repairable_sample_topology(), _sample_group_load())
    monkeypatch.setattr("proxmox_storage_drs.cli.build_forecaster", fail)
    monkeypatch.setattr("proxmox_storage_drs.cli.compute_disk_load_series", fail)
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "--json", "plan"]) == 0
    payload = json.loads(capsys.readouterr().out)
    payback = payload["groups"][0]["payback"]
    assert payback["deferred_moves"] == []


# ------------------------------------------------------- backtest validation gate


def test_backtest_gate_skips_validation_for_the_quantile_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`quantile` (the default `forecast.model`) does no fitting at all --
    there is nothing to validate and nothing more conservative to fall
    back to, so the gate must not even call `backtest_validated()`/
    `group_aggregate_series()`."""

    def fail(*_a: object, **_k: object) -> None:
        raise AssertionError("quantile must never be backtested")

    monkeypatch.setattr("proxmox_storage_drs.cli.backtest_validated", fail)
    monkeypatch.setattr("proxmox_storage_drs.cli.group_aggregate_series", fail)
    resolved = _resolved_config(tmp_path)
    sentinel = object()
    result = cli._backtest_gated_forecaster(
        sentinel,  # type: ignore[arg-type]
        resolved.config.forecast,
        resolved,
        {},
        now_epoch=0.0,
        window_seconds=100.0,
    )
    assert result is sentinel


def test_backtest_gate_keeps_the_forecaster_when_validated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("proxmox_storage_drs.cli.backtest_validated", lambda *a, **k: True)
    resolved = _resolved_config(
        tmp_path, forecast={"model": "seasonal_naive", "seasonal_lookback_days": 1}
    )
    sentinel = object()
    result = cli._backtest_gated_forecaster(
        sentinel,  # type: ignore[arg-type]
        resolved.config.forecast,
        resolved,
        {},
        now_epoch=0.0,
        window_seconds=100.0,
    )
    assert result is sentinel


def test_backtest_gate_falls_back_to_quantile_when_validation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A model that fails its own backtest (or cannot be validated for
    lack of history -- `backtest_validated()` returns `False` for both)
    falls back to a fresh `QuantileForecaster`, not to the failed
    forecaster it was just handed, and says so at warning level."""
    from proxmox_storage_drs.forecast import QuantileForecaster

    monkeypatch.setattr("proxmox_storage_drs.cli.backtest_validated", lambda *a, **k: False)
    resolved = _resolved_config(
        tmp_path, forecast={"model": "seasonal_naive", "seasonal_lookback_days": 1}
    )
    sentinel = object()
    with caplog.at_level(logging.WARNING):
        result = cli._backtest_gated_forecaster(
            sentinel,  # type: ignore[arg-type]
            resolved.config.forecast,
            resolved,
            {},
            now_epoch=0.0,
            window_seconds=100.0,
        )
    assert isinstance(result, QuantileForecaster)
    assert any("backtest" in r.message for r in caplog.records)


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
        _fake_build_topology(_balanced_non_violating_topology()),
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
        lambda prom_client, metrics, window, load_weights, group, last_known_loads=None: balanced,
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
        "proxmox_storage_drs.cli.build_topology", _fake_build_topology(_sample_topology())
    )

    def raise_metrics_error(
        prom_client: object,
        metrics: object,
        window: object,
        load_weights: object,
        group: object,
        last_known_loads: object = None,
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
    # "apply --mode auto" refuses outright before touching the network
    # (phase 8 is not implemented yet) -- this test is about the
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


# --------------------------------------------------------------------- apply


def _balanced_apply_topology() -> Topology:
    """Two evenly-sized, evenly-loaded disks on one storage, none on the
    other, no `saferemove` -- deliberately *not*
    `_repairable_sample_topology()`: that fixture's one movable disk sits
    on a `saferemove` storage and is large enough that its wipe alone
    exceeds `migration.max_single_move_duration`, so REVIEW.md S-02's
    payback gate now refuses it outright. Every apply test that only
    cares about execution mechanics (dry-run, confirm, state recording,
    `--json` shape, a failed move) uses this fixture instead, so the
    payback gate never has an opinion about them; S-02's own gate
    behaviour gets its own dedicated fixtures/tests below."""
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
    storages = tuple(
        Storage(
            id=sid,
            capability_weight=1.0,
            reserve_factor=2.0,
            saturation_load=None,
            capacity_bytes=100 * (1 << 40),
            used_bytes=2 * (1 << 40) if sid == "san-a" else 0,
            foreign_used_bytes=0,
            saferemove=False,
            saferemove_throughput_bytes_per_sec=None,
        )
        for sid in ("san-a", "san-b")
    )
    return Topology(groups=(Group(name="fc-tier1", storages=storages, disks=disks),), warnings=())


def _balanced_apply_group_load() -> GroupLoad:
    """Matches `_balanced_apply_topology()`: both disks on san-a, load 5.0
    each (200% imbalance -> ACT), san-b idle. The heuristic's one
    resulting move (101:scsi0 san-a -> san-b) mirrors in under 1.5h with
    no wipe, and its huge load-imbalance benefit clears
    `migration.payback_ratio` (10, by default) by two orders of
    magnitude -- both halves of section 7.3's test pass comfortably."""
    return GroupLoad(
        group_name="fc-tier1",
        idle=False,
        average_utilization=5.0,
        disks=(
            DiskLoad(disk_key="101:scsi0", load=5.0, flagged_reason=None),
            DiskLoad(disk_key="102:scsi0", load=5.0, flagged_reason=None),
        ),
        storages=(
            StorageLoad(storage_id="san-a", load=10.0, utilization=10.0),
            StorageLoad(storage_id="san-b", load=0.0, utilization=0.0),
        ),
    )


def test_apply_auto_mode_honours_a_configured_concurrency_above_the_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`execute.execute_plan()` itself now dispatches to a concurrent
    executor once either cap is configured above `1`
    (`docs/internals/92-execute.md`) -- `_handle_apply()` no longer
    refuses this outright the way it once did; the configured
    `ExecutionConfig` simply reaches `execute_plan()` unchanged, exactly
    as it always has for every other setting."""
    from proxmox_storage_drs.execute import ExecutionResult, MoveOutcome

    _patch_plan_deps(monkeypatch, _balanced_apply_topology(), _balanced_apply_group_load())
    seen_execution: list[object] = []

    def fake_execute_plan(
        client: object,
        group: object,
        schedule_result: object,
        migration: object,
        execution: object,
        min_free_bytes: object,
        mode: object,
        exclude: object,
        confirm: object = None,
        clock: object = None,
        deadline: object = None,
        move_costs_by_key: object = None,
        max_migrations: object = None,
        on_inflight_started: object = None,
        on_inflight_finished: object = None,
    ) -> ExecutionResult:
        seen_execution.append(execution)
        move = schedule_result.order[0]  # type: ignore[attr-defined]
        return ExecutionResult(
            (MoveOutcome(move.disk_key, move.from_storage, move.to_storage, "moved", "ok"),),
            False,
            None,
        )

    monkeypatch.setattr("proxmox_storage_drs.cli.execute_plan", fake_execute_plan)
    path = write_config(
        tmp_path,
        state={"path": str(tmp_path / "state.json")},
        execution={"max_concurrent_migrations": 3, "max_concurrent_per_storage": 2},
    )
    assert cli.main(["-c", str(path), "--mode", "auto", "apply"]) == 0
    assert len(seen_execution) == 1
    assert seen_execution[0].max_concurrent_migrations == 3  # type: ignore[attr-defined]
    assert seen_execution[0].max_concurrent_per_storage == 2  # type: ignore[attr-defined]


def test_apply_dry_run_reports_would_move_and_writes_no_state(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dry-run's own `execute_plan()` path issues zero API calls (see
    `test_execute.py`), so `build_pve_client`'s "fake-client" string is
    never actually called into -- this only checks `_handle_apply()`'s
    wiring, not `execute.py`'s own dry-run behaviour again."""
    _patch_plan_deps(monkeypatch, _balanced_apply_topology(), _balanced_apply_group_load())
    state_path = tmp_path / "state.json"
    path = write_config(tmp_path, state={"path": str(state_path)})
    assert cli.main(["-c", str(path), "--mode", "dry-run", "apply"]) == 0
    out = capsys.readouterr().out
    assert "101:scsi0" in out
    assert "would_move" in out
    # Nothing was executed, so section 11.2's "updated only after a run
    # that executed at least one migration" must not have fired.
    assert not state_path.exists() or load_state(str(state_path)).last_balance.at is None


def test_apply_confirm_mode_prompts_and_honours_a_decline(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A declined move never reaches `execute.py`'s own move-issuing code
    (see `execute_plan()`), so "fake-client" is never called into here
    either -- this checks that `_handle_apply()` wires the interactive
    `input()`-based callback through correctly and honours its answer."""
    _patch_plan_deps(monkeypatch, _balanced_apply_topology(), _balanced_apply_group_load())
    prompts = []

    def fake_input(prompt: str) -> str:
        prompts.append(prompt)
        return "n"

    monkeypatch.setattr("builtins.input", fake_input)
    state_path = tmp_path / "state.json"
    path = write_config(tmp_path, state={"path": str(state_path)})
    assert cli.main(["-c", str(path), "--mode", "confirm", "apply"]) == 0
    assert len(prompts) == 1
    assert "101:scsi0" in prompts[0]
    assert "san-a → san-b" in prompts[0]
    out = capsys.readouterr().out
    assert "skipped: operator declined" in out
    assert load_state(str(state_path)).last_balance.at is None


def test_apply_confirm_mode_retries_on_unrecognized_input(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_plan_deps(monkeypatch, _balanced_apply_topology(), _balanced_apply_group_load())
    answers = iter(["maybe", "n"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    state_path = tmp_path / "state.json"
    path = write_config(tmp_path, state={"path": str(state_path)})
    assert cli.main(["-c", str(path), "--mode", "confirm", "apply"]) == 0
    err = capsys.readouterr().err
    assert "please answer y, n, a or q" in err


def test_apply_records_balance_and_cooldowns_after_an_executed_move(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`_handle_apply()` itself decides which moves count as "executed"
    (section 11.2) -- this stubs `execute_plan()` (already covered, move
    by move, in `test_execute.py`) so the test is only about that
    decision and its `state.json` write, not about re-driving a fake PVE
    API through the whole executor again."""
    from proxmox_storage_drs.execute import ExecutionResult, MoveOutcome
    from proxmox_storage_drs.state import disk_state_key, storage_state_key

    _patch_plan_deps(monkeypatch, _balanced_apply_topology(), _balanced_apply_group_load())

    def fake_execute_plan(
        client: object,
        group: object,
        schedule_result: object,
        migration: object,
        execution: object,
        min_free_bytes: object,
        mode: object,
        exclude: object = None,
        confirm: object = None,
        clock: object = None,
        deadline: object = None,
        move_costs_by_key: object = None,
        max_migrations: object = None,
        on_inflight_started: object = None,
        on_inflight_finished: object = None,
    ) -> ExecutionResult:
        return ExecutionResult(
            outcomes=(
                MoveOutcome(
                    disk_key="101:scsi0",
                    from_storage="san-a",
                    to_storage="san-b",
                    status="moved",
                    detail="task UPID:... completed OK",
                    upid="UPID:pve01:00001234:00ABCDEF:qmmove:101:root@pam:",
                ),
            ),
            stopped_early=False,
            stop_reason=None,
        )

    monkeypatch.setattr("proxmox_storage_drs.cli.execute_plan", fake_execute_plan)
    state_path = tmp_path / "state.json"
    path = write_config(tmp_path, state={"path": str(state_path)})
    assert cli.main(["-c", str(path), "--mode", "confirm", "apply"]) == 0
    out = capsys.readouterr().out
    assert "moved: task UPID" in out

    saved = load_state(str(state_path))
    assert saved.last_balance.at is not None
    assert saved.last_balance.load_vector == {"fc-tier1:101:scsi0": 5.0, "fc-tier1:102:scsi0": 5.0}
    disk_key = disk_state_key("fc-tier1", 101, "scsi0")
    assert disk_key in saved.cooldowns.disk
    # Both endpoints -- section 6's "a storage involved in a migration
    # ... accepts no new incoming moves" covers source and destination
    # alike (REVIEW.md S-03); recording is independent of the heuristic's
    # own destination-only *enforcement* of the cooldown.
    assert storage_state_key("fc-tier1", "san-b") in saved.cooldowns.storage
    assert storage_state_key("fc-tier1", "san-a") in saved.cooldowns.storage


def test_apply_writes_inflight_upid_to_disk_synchronously_during_a_move(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Section 13's whole point: `state.json` must carry the UPID
    *before* the move that owns it can crash the engine, and lose it
    again once that move has finished -- not only once `_handle_apply()`
    itself gets back control after `execute_plan()` returns. Stubs
    `execute_plan()` to call `on_inflight_started()`/`on_inflight_finished()`
    itself (mirroring exactly when `execute.py`'s own `_execute_one_move()`
    calls them) and reads `state.json` straight off disk in between, the
    same way a crash-dump inspection or a second instance's own startup
    scan would."""
    from proxmox_storage_drs.execute import ExecutionResult, MoveOutcome

    _patch_plan_deps(monkeypatch, _balanced_apply_topology(), _balanced_apply_group_load())
    upid = "UPID:pve01:00001234:00ABCDEF:qmmove:101:root@pam:"
    state_path = tmp_path / "state.json"
    observed: dict[str, tuple[str, ...]] = {}

    def fake_execute_plan(
        client: object,
        group: object,
        schedule_result: object,
        migration: object,
        execution: object,
        min_free_bytes: object,
        mode: object,
        exclude: object = None,
        confirm: object = None,
        clock: object = None,
        deadline: object = None,
        move_costs_by_key: object = None,
        max_migrations: object = None,
        on_inflight_started: object = None,
        on_inflight_finished: object = None,
    ) -> ExecutionResult:
        assert on_inflight_started is not None and on_inflight_finished is not None
        on_inflight_started(upid)  # type: ignore[operator]
        observed["during"] = load_state(str(state_path)).inflight_upids
        on_inflight_finished(upid)  # type: ignore[operator]
        observed["after"] = load_state(str(state_path)).inflight_upids
        return ExecutionResult(
            outcomes=(
                MoveOutcome(
                    disk_key="101:scsi0",
                    from_storage="san-a",
                    to_storage="san-b",
                    status="moved",
                    detail="task UPID:... completed OK",
                    upid=upid,
                ),
            ),
            stopped_early=False,
            stop_reason=None,
        )

    monkeypatch.setattr("proxmox_storage_drs.cli.execute_plan", fake_execute_plan)
    path = write_config(tmp_path, state={"path": str(state_path)})
    assert cli.main(["-c", str(path), "--mode", "confirm", "apply"]) == 0
    assert observed["during"] == (upid,)
    assert observed["after"] == ()
    # And the run's own final save (recording this move's cooldowns) must
    # not have reverted `on_inflight_finished()`'s own already-persisted
    # clearing of it (see `_handle_apply()`'s own `finally` block).
    assert load_state(str(state_path)).inflight_upids == ()


def test_apply_stops_the_whole_run_when_the_operator_quits(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from proxmox_storage_drs.execute import ExecutionResult

    balanced = _balanced_apply_topology()
    two_groups = Topology(
        groups=(
            balanced.groups[0],
            Group(name="fc-tier2", storages=balanced.groups[0].storages, disks=()),
        ),
        warnings=(),
    )
    _patch_plan_deps(monkeypatch, two_groups, _balanced_apply_group_load())

    def fake_execute_plan(
        client: object,
        group: object,
        schedule_result: object,
        migration: object,
        execution: object,
        min_free_bytes: object,
        mode: object,
        exclude: object = None,
        confirm: object = None,
        clock: object = None,
        deadline: object = None,
        move_costs_by_key: object = None,
        max_migrations: object = None,
        on_inflight_started: object = None,
        on_inflight_finished: object = None,
    ) -> ExecutionResult:
        return ExecutionResult(outcomes=(), stopped_early=True, stop_reason="operator quit")

    monkeypatch.setattr("proxmox_storage_drs.cli.execute_plan", fake_execute_plan)
    path = write_config(tmp_path, state={"path": str(tmp_path / "state.json")})
    assert cli.main(["-c", str(path), "--mode", "confirm", "apply"]) == 0
    out = capsys.readouterr().out
    # Only the first group's own report -- fc-tier2 was never even planned
    # once the operator quit on fc-tier1.
    assert out.count("→ ACT") == 1


def test_apply_exits_quietly_when_state_json_is_already_locked(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from proxmox_storage_drs.state import acquire_lock, release_lock

    def fail(*_a: object, **_k: object) -> None:
        raise AssertionError("a locked run must never reach PVE at all")

    monkeypatch.setattr("proxmox_storage_drs.cli.build_pve_client", fail)
    state_path = tmp_path / "state.json"
    path = write_config(tmp_path, state={"path": str(state_path)})
    handle = acquire_lock(str(state_path))
    assert handle is not None
    try:
        assert cli.main(["-c", str(path), "--mode", "dry-run", "apply"]) == 0
        assert capsys.readouterr().out == ""
    finally:
        release_lock(handle)


def test_apply_reports_a_metrics_error_and_a_no_action_group_without_executing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from proxmox_storage_drs.exceptions import MetricsError

    two_groups = _two_group_topology()
    monkeypatch.setattr("proxmox_storage_drs.cli.build_pve_client", lambda cfg: "fake-client")
    monkeypatch.setattr("proxmox_storage_drs.cli.build_topology", _fake_build_topology(two_groups))
    monkeypatch.setattr("proxmox_storage_drs.cli.reconcile_inflight", _fake_reconcile_inflight)

    def per_group_load(
        prom_client: object,
        metrics: object,
        window: object,
        load_weights: object,
        group: Group,
        last_known_loads: object = None,
    ) -> GroupLoad:
        if group.name == "fc-tier1":
            raise MetricsError("connection refused")
        return GroupLoad(
            group_name=group.name,
            idle=True,
            average_utilization=0.0,
            disks=(),
            storages=(
                StorageLoad(storage_id="san-a", load=0.0, utilization=0.0),
                StorageLoad(storage_id="san-b", load=0.0, utilization=0.0),
            ),
        )

    monkeypatch.setattr("proxmox_storage_drs.cli.compute_group_load", per_group_load)
    path = write_config(tmp_path, state={"path": str(tmp_path / "state.json")})
    assert cli.main(["-c", str(path), "--mode", "dry-run", "apply"]) == 0
    out = capsys.readouterr().out
    assert "fc-tier1 — plan unavailable: connection refused" in out
    assert "fc-tier2 → NO ACTION" in out


def test_apply_json_output_includes_the_execution_key(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_plan_deps(monkeypatch, _balanced_apply_topology(), _balanced_apply_group_load())
    path = write_config(tmp_path, state={"path": str(tmp_path / "state.json")})
    assert cli.main(["-c", str(path), "--mode", "dry-run", "--json", "apply"]) == 0
    payload = json.loads(capsys.readouterr().out)
    group_out = next(g for g in payload["groups"] if g["name"] == "fc-tier1")
    assert group_out["execution"]["stopped_early"] is False
    assert group_out["execution"]["outcomes"][0]["status"] == "would_move"


def test_apply_exits_1_when_a_move_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from proxmox_storage_drs.execute import ExecutionResult, MoveOutcome

    _patch_plan_deps(monkeypatch, _balanced_apply_topology(), _balanced_apply_group_load())

    def fake_execute_plan(
        client: object,
        group: object,
        schedule_result: object,
        migration: object,
        execution: object,
        min_free_bytes: object,
        mode: object,
        exclude: object = None,
        confirm: object = None,
        clock: object = None,
        deadline: object = None,
        move_costs_by_key: object = None,
        max_migrations: object = None,
        on_inflight_started: object = None,
        on_inflight_finished: object = None,
    ) -> ExecutionResult:
        return ExecutionResult(
            outcomes=(
                MoveOutcome(
                    disk_key="101:scsi0",
                    from_storage="san-a",
                    to_storage="san-b",
                    status="failed",
                    detail="move_disk task failed: mirror error",
                ),
            ),
            stopped_early=True,
            stop_reason="101:scsi0 failed: move_disk task failed: mirror error",
        )

    monkeypatch.setattr("proxmox_storage_drs.cli.execute_plan", fake_execute_plan)
    path = write_config(tmp_path, state={"path": str(tmp_path / "state.json")})
    assert cli.main(["-c", str(path), "--mode", "confirm", "apply"]) == 1
    out = capsys.readouterr().out
    assert "failed: move_disk task failed" in out
    assert "run stopped early" in out


# ------------------------------------------------------ apply's payback gate (S-02)


def test_apply_refuses_a_move_rejected_by_the_hard_duration_rule(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`_repairable_sample_topology()`'s one move sits on a `saferemove`
    storage large enough that its wipe alone exceeds the default
    `migration.max_single_move_duration` (6h) -- `payback_result.rejected_moves`
    names it, `aggregate_ok` is still `True` (the reserve-override
    exemption). Section 7.3's hard per-move rule must refuse it
    regardless: `execute_plan()` must never be called at all (REVIEW.md
    S-02), not merely have its outcome relabeled afterwards."""

    def fail(*_a: object, **_k: object) -> None:
        raise AssertionError("a payback-rejected move must never reach execute_plan()")

    monkeypatch.setattr("proxmox_storage_drs.cli.execute_plan", fail)
    _patch_plan_deps(monkeypatch, _repairable_sample_topology(), _sample_group_load())
    path = write_config(tmp_path, state={"path": str(tmp_path / "state.json")})
    assert cli.main(["-c", str(path), "--mode", "confirm", "apply"]) == 0
    out = capsys.readouterr().out
    assert (
        "101:scsi0" in out
        and "refused: exceeds migration.max_single_move_duration" in out
        and "section 7.3" in out
    )


def test_apply_refuses_the_whole_plan_when_the_aggregate_payback_test_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`_balanced_apply_topology()`'s one move easily clears the default
    `migration.payback_ratio` (10) on its own economics -- raising the
    configured ratio well above its real one (≈577) fails the *aggregate*
    test without tripping the hard per-move duration rule, so this
    exercises the other half of S-02's gate: refuse the whole plan,
    never call `execute_plan()` at all, even though nothing about this
    move is individually rejected."""

    def fail(*_a: object, **_k: object) -> None:
        raise AssertionError("a plan failing the aggregate payback test must never execute")

    monkeypatch.setattr("proxmox_storage_drs.cli.execute_plan", fail)
    _patch_plan_deps(monkeypatch, _balanced_apply_topology(), _balanced_apply_group_load())
    path = write_config(
        tmp_path,
        state={"path": str(tmp_path / "state.json")},
        migration={"payback_ratio": 1000},
    )
    assert cli.main(["-c", str(path), "--mode", "confirm", "apply"]) == 0
    out = capsys.readouterr().out
    assert "101:scsi0" in out
    assert "refused: plan failed the payback acceptance test" in out
    assert "section 7.3" in out
    # Refused, not failed -- state.json must be untouched, same as a
    # group the gate never acted on.
    assert load_state(str(tmp_path / "state.json")).last_balance.at is None


def test_apply_confirm_mode_shows_the_payback_verdict_before_the_first_prompt(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_plan_deps(monkeypatch, _balanced_apply_topology(), _balanced_apply_group_load())
    seen_before_prompt = {}

    def fake_input(prompt: str) -> str:
        seen_before_prompt["out"] = capsys.readouterr().out
        return "n"

    monkeypatch.setattr("builtins.input", fake_input)
    path = write_config(tmp_path, state={"path": str(tmp_path / "state.json")})
    assert cli.main(["-c", str(path), "--mode", "confirm", "apply"]) == 0
    assert "payback:" in seen_before_prompt["out"]
    assert "✓" in seen_before_prompt["out"]


# --------------------------------------------------------- auto mode (phase 8)


def test_real_local_now_resolves_a_real_iana_zone_when_available() -> None:
    """On a real Linux host (this project's only packaged target), the
    result should carry a genuine `zoneinfo.ZoneInfo`, not a frozen UTC
    offset -- the whole reason `cli._real_local_now()` exists instead of
    a bare `datetime.now().astimezone()` call."""
    import os
    from zoneinfo import ZoneInfo

    if not os.path.exists("/etc/localtime"):
        pytest.skip("no /etc/localtime on this system")
    now = cli._real_local_now()
    assert isinstance(now.tzinfo, ZoneInfo)


def test_real_local_now_falls_back_when_the_zone_cannot_be_resolved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*_a: object, **_k: object) -> str:
        raise OSError("no such file")

    monkeypatch.setattr("proxmox_storage_drs.cli.os.path.realpath", fail)
    now = cli._real_local_now()
    # Still a usable, timezone-aware datetime -- just not IANA-backed.
    assert now.tzinfo is not None


def test_real_local_now_falls_back_for_an_unknown_zone_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "proxmox_storage_drs.cli.os.path.realpath", lambda _p: "/usr/share/zoneinfo/Nowhere/Fake"
    )
    now = cli._real_local_now()
    assert now.tzinfo is not None


def _make_group_plan(
    group: Group,
    resolved: ResolvedConfig,
    moves: tuple[ScheduledMove, ...],
    act: bool = True,
    rejected_moves: tuple[str, ...] = (),
    aggregate_ok: bool = True,
) -> cli._GroupPlan:
    from proxmox_storage_drs.gates import GateDecision
    from proxmox_storage_drs.payback import MoveCost, PaybackResult
    from proxmox_storage_drs.schedule import ScheduleResult

    load_by_key = {d.key: 1.0 for d in group.disks}
    decision = GateDecision(
        act=act,
        reason="test",
        reserve_override=False,
        drift_fraction=None,
        imbalance_fraction=0.5,
    )
    if not act:
        return cli._GroupPlan(
            group_load=GroupLoad(
                group_name=group.name,
                idle=False,
                average_utilization=1.0,
                disks=(),
                storages=(),
            ),
            decision=decision,
        )
    group_load = GroupLoad(
        group_name=group.name,
        idle=False,
        average_utilization=1.0,
        disks=tuple(DiskLoad(disk_key=d.key, load=1.0, flagged_reason=None) for d in group.disks),
        storages=tuple(
            StorageLoad(storage_id=s.id, load=0.0, utilization=0.0) for s in group.storages
        ),
    )
    schedule_result = ScheduleResult(
        order=moves, deadlocked=(), final_assignment={d.key: d.current_storage for d in group.disks}
    )
    move_costs = tuple(
        MoveCost(m.disk_key, 100.0, 0.0, 100.0, m.disk_key in rejected_moves, False) for m in moves
    )
    payback_result = PaybackResult(
        move_costs=move_costs,
        benefit_load_seconds=1_000_000.0,
        rejected_moves=rejected_moves,
        aggregate_ok=aggregate_ok,
    )
    return cli._GroupPlan(
        group_load=group_load,
        decision=decision,
        solve_outcome=None,
        schedule_result=schedule_result,
        final_breakdown=_fake_breakdown(group, load_by_key, resolved),
        payback_result=payback_result,
    )


def _one_move(group: Group) -> ScheduledMove:
    disk = group.disks[0]
    return ScheduledMove(
        disk_key=disk.key,
        vmid=disk.vmid,
        device=disk.device,
        from_storage="san-a",
        to_storage="san-b",
        size_bytes=disk.size_bytes,
        imbalance_reduction=1.0,
        resolves_reserve_violation=False,
    )


def _moved_outcome(move: ScheduledMove) -> MoveOutcome:
    return MoveOutcome(move.disk_key, move.from_storage, move.to_storage, "moved", "task OK")


def _replan_needed_outcome(move: ScheduledMove) -> MoveOutcome:
    return MoveOutcome(
        move.disk_key, move.from_storage, move.to_storage, "replan_needed", "no longer matches"
    )


def test_run_auto_group_refuses_outside_every_configured_time_window(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from proxmox_storage_drs.execute import ExecutionResult

    resolved = _resolved_config(
        tmp_path,
        execution={
            "time_windows": [{"days": ["mon"], "start": "01:00", "end": "02:00"}],
        },
    )
    group = _one_disk_group()
    move = _one_move(group)
    group_plan = _make_group_plan(group, resolved, (move,))

    def fail(*_a: object, **_k: object) -> ExecutionResult:
        raise AssertionError("outside every window: _apply_payback_gate must never be called")

    monkeypatch.setattr("proxmox_storage_drs.cli._apply_payback_gate", fail)

    # 2026-09-07 is a Monday; 12:00 is well outside 01:00-02:00.
    fixed_now = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)
    result, budget = cli._run_auto_group(
        "fake-client",  # type: ignore[arg-type]
        resolved,
        "fake-prom",  # type: ignore[arg-type]
        0,
        empty_state(),
        group,
        group_plan,
        None,
        local_now=lambda: fixed_now,
    )
    assert result.stopped_early is True
    assert result.stop_reason == "outside execution.time_windows"
    assert result.outcomes[0].status == "skipped"
    assert budget is None


def test_run_auto_group_allows_execution_inside_a_configured_window(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from proxmox_storage_drs.execute import ExecutionResult

    resolved = _resolved_config(
        tmp_path,
        execution={
            "time_windows": [{"days": ["mon"], "start": "00:00", "end": "23:59"}],
        },
    )
    group = _one_disk_group()
    move = _one_move(group)
    group_plan = _make_group_plan(group, resolved, (move,))

    monkeypatch.setattr(
        "proxmox_storage_drs.cli._apply_payback_gate",
        lambda *a, **k: ExecutionResult((_moved_outcome(move),), False, None),
    )
    fixed_now = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)
    result, _budget = cli._run_auto_group(
        "fake-client",  # type: ignore[arg-type]
        resolved,
        "fake-prom",  # type: ignore[arg-type]
        0,
        empty_state(),
        group,
        group_plan,
        None,
        local_now=lambda: fixed_now,
    )
    assert result.outcomes[0].status == "moved"
    assert result.stopped_early is False


def test_run_auto_group_no_time_windows_configured_means_unrestricted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from proxmox_storage_drs.execute import ExecutionResult

    resolved = _resolved_config(tmp_path)
    group = _one_disk_group()
    move = _one_move(group)
    group_plan = _make_group_plan(group, resolved, (move,))
    monkeypatch.setattr(
        "proxmox_storage_drs.cli._apply_payback_gate",
        lambda *a, **k: ExecutionResult((_moved_outcome(move),), False, None),
    )
    result, _budget = cli._run_auto_group(
        "fake-client",  # type: ignore[arg-type]
        resolved,
        "fake-prom",  # type: ignore[arg-type]
        0,
        empty_state(),
        group,
        group_plan,
        None,
    )
    assert result.outcomes[0].status == "moved"


def test_run_auto_group_replans_and_succeeds_on_the_second_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from proxmox_storage_drs.execute import ExecutionResult

    resolved = _resolved_config(tmp_path)
    group = _one_disk_group()
    move = _one_move(group)
    group_plan = _make_group_plan(group, resolved, (move,))
    second_plan = _make_group_plan(group, resolved, (move,))

    calls = {"n": 0}

    def fake_gate(*a: object, **k: object) -> ExecutionResult:
        calls["n"] += 1
        if calls["n"] == 1:
            return ExecutionResult((_replan_needed_outcome(move),), True, "no longer matches")
        return ExecutionResult((_moved_outcome(move),), False, None)

    monkeypatch.setattr("proxmox_storage_drs.cli._apply_payback_gate", fake_gate)
    monkeypatch.setattr(
        "proxmox_storage_drs.cli.build_topology",
        lambda *a, **k: Topology(groups=(group,), warnings=()),
    )
    monkeypatch.setattr("proxmox_storage_drs.cli._plan_group", lambda *a, **k: second_plan)

    result, _budget = cli._run_auto_group(
        "fake-client",  # type: ignore[arg-type]
        resolved,
        "fake-prom",  # type: ignore[arg-type]
        0,
        empty_state(),
        group,
        group_plan,
        None,
    )
    assert calls["n"] == 2
    assert [o.status for o in result.outcomes] == ["replan_needed", "moved"]
    assert result.stopped_early is False
    assert result.stop_reason is None


def test_run_auto_group_stops_cleanly_when_a_replan_concludes_no_action_needed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from proxmox_storage_drs.execute import ExecutionResult

    resolved = _resolved_config(tmp_path)
    group = _one_disk_group()
    move = _one_move(group)
    group_plan = _make_group_plan(group, resolved, (move,))
    no_action_plan = _make_group_plan(group, resolved, (), act=False)

    monkeypatch.setattr(
        "proxmox_storage_drs.cli._apply_payback_gate",
        lambda *a, **k: ExecutionResult((_replan_needed_outcome(move),), True, "no longer matches"),
    )
    monkeypatch.setattr(
        "proxmox_storage_drs.cli.build_topology",
        lambda *a, **k: Topology(groups=(group,), warnings=()),
    )
    monkeypatch.setattr("proxmox_storage_drs.cli._plan_group", lambda *a, **k: no_action_plan)

    result, _budget = cli._run_auto_group(
        "fake-client",  # type: ignore[arg-type]
        resolved,
        "fake-prom",  # type: ignore[arg-type]
        0,
        empty_state(),
        group,
        group_plan,
        None,
    )
    assert [o.status for o in result.outcomes] == ["replan_needed"]
    assert result.stopped_early is False
    assert result.stop_reason is None


def test_run_auto_group_stops_after_exhausting_max_replans_per_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from proxmox_storage_drs.execute import ExecutionResult

    resolved = _resolved_config(tmp_path, execution={"max_replans_per_run": 2})
    group = _one_disk_group()
    move = _one_move(group)
    group_plan = _make_group_plan(group, resolved, (move,))

    monkeypatch.setattr(
        "proxmox_storage_drs.cli._apply_payback_gate",
        lambda *a, **k: ExecutionResult((_replan_needed_outcome(move),), True, "no longer matches"),
    )
    monkeypatch.setattr(
        "proxmox_storage_drs.cli.build_topology",
        lambda *a, **k: Topology(groups=(group,), warnings=()),
    )
    monkeypatch.setattr(
        "proxmox_storage_drs.cli._plan_group",
        lambda *a, **k: _make_group_plan(group, resolved, (move,)),
    )

    result, _budget = cli._run_auto_group(
        "fake-client",  # type: ignore[arg-type]
        resolved,
        "fake-prom",  # type: ignore[arg-type]
        0,
        empty_state(),
        group,
        group_plan,
        None,
    )
    # One initial attempt plus two re-plans = three replan_needed outcomes.
    assert [o.status for o in result.outcomes] == ["replan_needed"] * 3
    assert result.stopped_early is True
    assert result.stop_reason is not None
    assert "max_replans_per_run" in result.stop_reason
    assert "exceeded" in result.stop_reason


def test_run_auto_group_stops_when_the_group_vanishes_after_replanning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An edge case (every storage in the group removed from config
    between plans), but a real one: `build_topology()`'s fresh result may
    simply no longer contain a group by this name."""
    from proxmox_storage_drs.execute import ExecutionResult

    resolved = _resolved_config(tmp_path)
    group = _one_disk_group()
    move = _one_move(group)
    group_plan = _make_group_plan(group, resolved, (move,))

    monkeypatch.setattr(
        "proxmox_storage_drs.cli._apply_payback_gate",
        lambda *a, **k: ExecutionResult((_replan_needed_outcome(move),), True, "no longer matches"),
    )
    monkeypatch.setattr(
        "proxmox_storage_drs.cli.build_topology", lambda *a, **k: Topology(groups=(), warnings=())
    )

    result, _budget = cli._run_auto_group(
        "fake-client",  # type: ignore[arg-type]
        resolved,
        "fake-prom",  # type: ignore[arg-type]
        0,
        empty_state(),
        group,
        group_plan,
        None,
    )
    assert [o.status for o in result.outcomes] == ["replan_needed"]
    assert result.stopped_early is True
    assert result.stop_reason is not None
    assert "no longer exists" in result.stop_reason


def test_run_auto_group_decrements_the_shared_migrations_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from proxmox_storage_drs.execute import ExecutionResult

    resolved = _resolved_config(tmp_path)
    group = _one_disk_group()
    move = _one_move(group)
    group_plan = _make_group_plan(group, resolved, (move,))
    monkeypatch.setattr(
        "proxmox_storage_drs.cli._apply_payback_gate",
        lambda *a, **k: ExecutionResult((_moved_outcome(move),), False, None),
    )
    _result, budget = cli._run_auto_group(
        "fake-client",  # type: ignore[arg-type]
        resolved,
        "fake-prom",  # type: ignore[arg-type]
        0,
        empty_state(),
        group,
        group_plan,
        3,
    )
    assert budget == 2


def test_apply_auto_mode_shares_max_migrations_per_run_across_groups(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`execution.max_migrations_per_run` is a per-*invocation* cap
    (`IMPLEMENTATION_PLAN.md` section 9.1: "auto must... honour
    max_migrations_per_run"), shared across every group `apply` visits in
    one run, not reset per group -- this exercises `_handle_apply()`'s
    own threading of the budget from group to group, end to end through
    `cli.main()`, distinct from `_run_auto_group()`'s already-unit-tested
    arithmetic for a single group."""
    from proxmox_storage_drs.execute import ExecutionResult, MoveOutcome

    balanced = _balanced_apply_topology()
    two_groups = Topology(
        groups=(
            balanced.groups[0],
            Group(
                name="fc-tier2",
                storages=balanced.groups[0].storages,
                disks=balanced.groups[0].disks,
            ),
        ),
        warnings=(),
    )
    _patch_plan_deps(monkeypatch, two_groups, _balanced_apply_group_load())

    calls: list[tuple[str, object]] = []

    def fake_execute_plan(
        client: object,
        group: Group,
        schedule_result: object,
        migration: object,
        execution: object,
        min_free_bytes: object,
        mode: object,
        exclude: object,
        confirm: object = None,
        clock: object = None,
        deadline: object = None,
        move_costs_by_key: object = None,
        max_migrations: object = None,
        on_inflight_started: object = None,
        on_inflight_finished: object = None,
    ) -> ExecutionResult:
        calls.append((group.name, max_migrations))
        move = schedule_result.order[0]  # type: ignore[attr-defined]
        return ExecutionResult(
            (MoveOutcome(move.disk_key, move.from_storage, move.to_storage, "moved", "ok"),),
            False,
            None,
        )

    monkeypatch.setattr("proxmox_storage_drs.cli.execute_plan", fake_execute_plan)
    path = write_config(
        tmp_path,
        state={"path": str(tmp_path / "state.json")},
        execution={"max_migrations_per_run": 1},
    )
    assert cli.main(["-c", str(path), "--mode", "auto", "apply"]) == 0
    assert [name for name, _budget in calls] == ["fc-tier1", "fc-tier2"]
    assert calls[0][1] == 1  # the full budget, for the first group
    assert calls[1][1] == 0  # already spent by the first group's one move


# --------------------------------------------------------- solver backend dispatch


def _resolved_config(tmp_path: Path, **overrides: object) -> ResolvedConfig:
    from proxmox_storage_drs.config import load_config

    path = write_config(tmp_path, **overrides)
    return load_config(str(path), env={})


def _one_disk_group() -> Group:
    storages = tuple(
        Storage(
            id=sid,
            capability_weight=1.0,
            reserve_factor=2.0,
            saturation_load=None,
            capacity_bytes=8 * (1 << 40),
            used_bytes=0,
            foreign_used_bytes=0,
            saferemove=False,
            saferemove_throughput_bytes_per_sec=None,
        )
        for sid in ("san-a", "san-b")
    )
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
    )
    return Group(name="fc-tier1", storages=storages, disks=disks)


def _fake_breakdown(
    group: Group, loads: dict[str, float], resolved: ResolvedConfig
) -> ObjectiveBreakdown:
    from proxmox_storage_drs.heuristic import (
        evaluate_assignment,
        group_average_utilization,
        seed_assignment,
    )

    u_star = group_average_utilization(group, loads)
    return evaluate_assignment(
        group, seed_assignment(group), loads, resolved.config.objective, 0, u_star
    )


def test_solve_group_uses_the_milp_result_when_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from proxmox_storage_drs.optimize import OptimizeResult

    resolved = _resolved_config(tmp_path, solver={"backend": "cpsat"})
    group = _one_disk_group()
    loads = {"101:scsi0": 1.0}
    breakdown = _fake_breakdown(group, loads, resolved)
    fake_result = OptimizeResult(
        assignment={"101:scsi0": "san-b"},
        breakdown=breakdown,
        initial_breakdown=breakdown,
        backend="cpsat",
        status="optimal",
    )
    calls: list[str] = []

    def fake_solve(
        group: object,
        load_by_key: object,
        objective: object,
        min_free_bytes: object,
        backend: str,
        time_limit_seconds: object,
        mip_gap: object,
        cooldown_storages: object = frozenset(),
    ) -> object:
        calls.append(backend)
        return fake_result

    def fail_heuristic(*args: object, **kwargs: object) -> None:
        raise AssertionError("must not fall back to the heuristic when cpsat succeeds")

    monkeypatch.setattr("proxmox_storage_drs.cli.optimize.solve", fake_solve)
    monkeypatch.setattr("proxmox_storage_drs.cli.run_heuristic", fail_heuristic)

    outcome = cli._solve_group(group, loads, resolved, 0, frozenset())

    assert calls == ["cpsat"]
    assert outcome.backend == "cpsat"
    assert outcome.status == "optimal"
    assert outcome.assignment == {"101:scsi0": "san-b"}


def test_solve_group_auto_cascades_cpsat_then_cbc_then_heuristic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    resolved = _resolved_config(tmp_path)  # solver.backend defaults to "auto"
    group = _one_disk_group()
    loads = {"101:scsi0": 1.0}
    calls: list[str] = []

    def fake_solve(*args: object, **kwargs: object) -> None:
        calls.append(args[4])  # type: ignore[arg-type]
        return None

    monkeypatch.setattr("proxmox_storage_drs.cli.optimize.solve", fake_solve)

    outcome = cli._solve_group(group, loads, resolved, 0, frozenset())

    assert calls == ["cpsat", "cbc"]
    assert outcome.backend == "heuristic"
    assert outcome.status is None
    assert outcome.assignment == {"101:scsi0": "san-a"}  # nothing improves a lone disk's spread


def test_solve_group_never_calls_optimize_when_backend_is_heuristic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    resolved = _resolved_config(tmp_path, solver={"backend": "heuristic"})
    group = _one_disk_group()

    def fail_solve(*args: object, **kwargs: object) -> None:
        raise AssertionError("solver.backend=heuristic must never call optimize.solve")

    monkeypatch.setattr("proxmox_storage_drs.cli.optimize.solve", fail_solve)

    outcome = cli._solve_group(group, {"101:scsi0": 1.0}, resolved, 0, frozenset())
    assert outcome.backend == "heuristic"


def test_solve_group_warns_when_an_explicit_backend_falls_back(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    import logging

    resolved = _resolved_config(tmp_path, solver={"backend": "cpsat"})
    group = _one_disk_group()
    monkeypatch.setattr("proxmox_storage_drs.cli.optimize.solve", lambda *a, **k: None)

    with caplog.at_level(logging.WARNING):
        outcome = cli._solve_group(group, {"101:scsi0": 1.0}, resolved, 0, frozenset())

    assert outcome.backend == "heuristic"
    assert any("falling back to the heuristic" in r.message for r in caplog.records)


def test_plan_human_output_shows_the_solver_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_plan_deps(monkeypatch, _repairable_sample_topology(), _sample_group_load())
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "plan"]) == 0
    out = capsys.readouterr().out
    assert "solver: heuristic" in out  # no solver extras installed in the test venv


def test_plan_json_output_includes_the_solver_backend_and_status(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_plan_deps(monkeypatch, _repairable_sample_topology(), _sample_group_load())
    path = write_config(tmp_path)
    assert cli.main(["-c", str(path), "--json", "plan"]) == 0
    payload = json.loads(capsys.readouterr().out)
    group_payload = payload["groups"][0]
    assert group_payload["solver_backend"] == "heuristic"
    assert group_payload["solver_status"] is None
