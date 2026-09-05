# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Config loading, resolution order and section 11.1 semantic validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from proxmox_storage_drs import config
from proxmox_storage_drs.exceptions import ConfigError

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_CONFIG = REPO_ROOT / "config" / "drs.example.yaml"


def minimal_config_dict() -> dict[str, Any]:
    """The smallest config that passes structural + semantic validation."""
    return {
        "schema_version": 1,
        "proxmox": {"host": "pve01.example.com", "auth": {"username": "drs@pve"}},
        "prometheus": {"url": "http://localhost:9090"},
        "groups": [
            {
                "name": "fc-tier1",
                "storages": [{"id": "san-a"}, {"id": "san-b"}],
            }
        ],
    }


def write_config(tmp_path: Path, data: dict[str, Any], name: str = "drs.yaml") -> Path:
    path = tmp_path / name
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


# --------------------------------------------------------------- resolution


def test_resolve_config_path_prefers_cli_argument() -> None:
    path, explicit = config.resolve_config_path(
        "/tmp/x.yaml", env={config.ENV_CONFIG_VAR: "/tmp/y.yaml"}
    )
    assert path == "/tmp/x.yaml"
    assert explicit is True


def test_resolve_config_path_falls_back_to_env() -> None:
    path, explicit = config.resolve_config_path(None, env={config.ENV_CONFIG_VAR: "/tmp/y.yaml"})
    assert path == "/tmp/y.yaml"
    assert explicit is True


def test_resolve_config_path_default_is_not_explicit() -> None:
    path, explicit = config.resolve_config_path(None, env={})
    assert path == config.DEFAULT_CONFIG_PATH
    assert explicit is False


def test_missing_explicit_config_is_a_hard_failure(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.yaml"
    with pytest.raises(ConfigError):
        config.load_config(str(missing), env={})


def test_missing_default_config_points_at_the_example(tmp_path: Path) -> None:
    # No --config and no env var: DEFAULT_CONFIG_PATH is used, which does not
    # exist on this machine. The error must not fall back silently -- it must
    # still fail, and it must point the operator somewhere useful.
    with pytest.raises(ConfigError, match="drs.example.yaml"):
        config.load_config(None, env={})


# ------------------------------------------------------------------ loading


@pytest.mark.skipif(
    not EXAMPLE_CONFIG.is_file(),
    reason="config/ sits outside the installed package; absent under dh_auto_test's pybuild "
    "isolation (.agents/packaging.md), present in a full checkout",
)
def test_loads_the_shipped_example_config() -> None:
    resolved = config.load_config(str(EXAMPLE_CONFIG), env={})
    assert resolved.path == str(EXAMPLE_CONFIG)
    assert len(resolved.sha256) == 64
    group_names = [g.name for g in resolved.config.groups]
    assert group_names == ["fc-tier1", "fc-tier2"]


def test_sha256_is_of_the_actual_bytes_read(tmp_path: Path) -> None:
    import hashlib

    path = write_config(tmp_path, minimal_config_dict())
    resolved = config.load_config(str(path), env={})
    assert resolved.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()


def test_defaults_are_applied(tmp_path: Path) -> None:
    path = write_config(tmp_path, minimal_config_dict())
    resolved = config.load_config(str(path), env={})
    cfg = resolved.config
    assert cfg.window.lookback_seconds == 86400.0
    assert cfg.gates.drift_threshold == 0.10
    assert cfg.execution.mode == "dry-run"
    assert cfg.groups[0].storages[0].capability_weight == 1.0


def test_duration_and_size_strings_are_parsed(tmp_path: Path) -> None:
    data = minimal_config_dict()
    data["window"] = {"lookback": "12h"}
    data["migration"] = {"bwlimit_bytes_per_sec": "100MiB"}
    path = write_config(tmp_path, data)
    resolved = config.load_config(str(path), env={})
    assert resolved.config.window.lookback_seconds == 12 * 3600
    assert resolved.config.migration.bwlimit_bytes_per_sec == 100 * (1 << 20)


def test_not_a_mapping_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "drs.yaml"
    path.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="mapping"):
        config.load_config(str(path), env={})


def test_unparseable_yaml_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "drs.yaml"
    path.write_text("proxmox: [unterminated\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        config.load_config(str(path), env={})


# --------------------------------------------------------- secrets from env


def test_password_env_var_fills_in_null_password(tmp_path: Path) -> None:
    data = minimal_config_dict()
    data["proxmox"]["auth"]["password"] = None
    path = write_config(tmp_path, data)
    resolved = config.load_config(str(path), env={config.ENV_PASSWORD_VAR: "s3cret"})
    assert resolved.config.proxmox.auth.password == "s3cret"


def test_password_in_file_is_not_overridden_by_env(tmp_path: Path) -> None:
    data = minimal_config_dict()
    data["proxmox"]["auth"]["password"] = "in-the-file"
    path = write_config(tmp_path, data)
    resolved = config.load_config(str(path), env={config.ENV_PASSWORD_VAR: "from-env"})
    assert resolved.config.proxmox.auth.password == "in-the-file"


def test_token_secret_env_var(tmp_path: Path) -> None:
    data = minimal_config_dict()
    path = write_config(tmp_path, data)
    resolved = config.load_config(str(path), env={config.ENV_TOKEN_SECRET_VAR: "tok"})
    assert resolved.config.proxmox.auth.token_secret == "tok"


def test_token_secret_in_file_is_not_overridden_by_env(tmp_path: Path) -> None:
    data = minimal_config_dict()
    data["proxmox"]["auth"]["token_secret"] = "in-the-file"
    path = write_config(tmp_path, data)
    resolved = config.load_config(str(path), env={config.ENV_TOKEN_SECRET_VAR: "from-env"})
    assert resolved.config.proxmox.auth.token_secret == "in-the-file"


# ------------------------------------------------------------ jsonschema


def test_schema_rejects_unknown_top_level_key(tmp_path: Path) -> None:
    data = minimal_config_dict()
    data["not_a_real_key"] = True
    path = write_config(tmp_path, data)
    with pytest.raises(ConfigError):
        config.load_config(str(path), env={})


def test_schema_rejects_single_storage_group(tmp_path: Path) -> None:
    data = minimal_config_dict()
    data["groups"][0]["storages"] = [{"id": "san-a"}]
    path = write_config(tmp_path, data)
    with pytest.raises(ConfigError):
        config.load_config(str(path), env={})


def test_schema_rejects_bad_execution_mode(tmp_path: Path) -> None:
    data = minimal_config_dict()
    data["execution"] = {"mode": "yolo"}
    path = write_config(tmp_path, data)
    with pytest.raises(ConfigError):
        config.load_config(str(path), env={})


# --------------------------------------------------------- semantic rules


def test_unsupported_schema_version_major(tmp_path: Path) -> None:
    data = minimal_config_dict()
    data["schema_version"] = 2
    path = write_config(tmp_path, data)
    with pytest.raises(ConfigError, match="schema_version"):
        config.load_config(str(path), env={})


def test_storage_in_two_groups_is_rejected(tmp_path: Path) -> None:
    data = minimal_config_dict()
    data["groups"].append({"name": "other", "storages": [{"id": "san-a"}, {"id": "san-c"}]})
    path = write_config(tmp_path, data)
    with pytest.raises(ConfigError, match="san-a"):
        config.load_config(str(path), env={})


def test_duplicate_storage_within_one_group_is_rejected(tmp_path: Path) -> None:
    data = minimal_config_dict()
    data["groups"][0]["storages"].append({"id": "san-a"})
    path = write_config(tmp_path, data)
    with pytest.raises(ConfigError, match="more than once"):
        config.load_config(str(path), env={})


def test_upper_quantile_below_quantile_is_rejected(tmp_path: Path) -> None:
    data = minimal_config_dict()
    data["window"] = {"quantile": 0.95, "upper_quantile": 0.90}
    path = write_config(tmp_path, data)
    with pytest.raises(ConfigError, match="upper_quantile"):
        config.load_config(str(path), env={})


def test_duplicate_labels_are_rejected(tmp_path: Path) -> None:
    data = minimal_config_dict()
    data["metrics"] = {"labels": {"vmid": "same", "device": "same", "node": "nodename"}}
    path = write_config(tmp_path, data)
    with pytest.raises(ConfigError, match="pairwise distinct"):
        config.load_config(str(path), env={})


def test_rate_window_too_short_is_rejected(tmp_path: Path) -> None:
    data = minimal_config_dict()
    data["metrics"] = {"rate_window": "1m", "pvestatd_push_interval": "60s"}
    path = write_config(tmp_path, data)
    with pytest.raises(ConfigError, match="rate_window"):
        config.load_config(str(path), env={})


def test_lookback_shorter_than_holt_winters_requirement_is_rejected(tmp_path: Path) -> None:
    data = minimal_config_dict()
    data["forecast"] = {"model": "holt_winters"}
    # default lookback (24h) is well below the 48h holt_winters needs at the
    # default seasonal_periods=288 and a 5m step.
    path = write_config(tmp_path, data)
    with pytest.raises(ConfigError, match="holt_winters"):
        config.load_config(str(path), env={})


def test_lookback_long_enough_for_holt_winters_is_accepted(tmp_path: Path) -> None:
    data = minimal_config_dict()
    data["window"] = {"lookback": "48h"}
    data["forecast"] = {"model": "holt_winters"}
    path = write_config(tmp_path, data)
    resolved = config.load_config(str(path), env={})
    assert resolved.config.forecast.model == "holt_winters"


def test_time_window_start_equals_end_is_rejected(tmp_path: Path) -> None:
    data = minimal_config_dict()
    data["execution"] = {"time_windows": [{"days": ["mon"], "start": "22:00", "end": "22:00"}]}
    path = write_config(tmp_path, data)
    with pytest.raises(ConfigError, match="start == end"):
        config.load_config(str(path), env={})


def test_missing_saturation_load_is_a_warning_not_an_error(tmp_path: Path) -> None:
    path = write_config(tmp_path, minimal_config_dict())
    resolved = config.load_config(str(path), env={})
    assert any("saturation_load" in w for w in resolved.warnings)


def test_configured_saturation_load_silences_the_warning(tmp_path: Path) -> None:
    data = minimal_config_dict()
    data["groups"][0]["storages"] = [
        {"id": "san-a", "saturation_load": 64},
        {"id": "san-b", "saturation_load": 64},
    ]
    path = write_config(tmp_path, data)
    resolved = config.load_config(str(path), env={})
    assert resolved.warnings == ()


def test_multiple_errors_are_all_reported(tmp_path: Path) -> None:
    data = minimal_config_dict()
    data["schema_version"] = 2
    data["window"] = {"quantile": 0.95, "upper_quantile": 0.5}
    path = write_config(tmp_path, data)
    with pytest.raises(ConfigError) as excinfo:
        config.load_config(str(path), env={})
    message = str(excinfo.value)
    assert "schema_version" in message
    assert "upper_quantile" in message
