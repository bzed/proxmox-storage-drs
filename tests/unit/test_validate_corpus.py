# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression pins for the X-02/X-03 fixes to `tests/corpus/validate_corpus.py`'s
scrub audit: the per-file key allowlist used to apply to five top-level
`pve/` files only, and the hostname value-pattern check missed a
`.example`/`.internal`/`.corp`/`.lan` suffix and an unredacted `host='...'`
transport-failure literal. See REVIEW.md section 29 (X-02, X-03).

`tests/corpus/` sits beside, not inside, the installed package (like
`config/`/`man/`/`docs/` -- `.agents/packaging.md`), so this module is
skipped when it is not present (Debian's isolated `dh_auto_test` copy)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from proxmox_storage_drs import anonymize, collect

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATE_CORPUS_SRC = REPO_ROOT / "tests" / "corpus" / "validate_corpus.py"

needs_full_checkout = pytest.mark.skipif(
    not VALIDATE_CORPUS_SRC.is_file(),
    reason="needs the full source checkout (tests/corpus/), not just the installed package",
)

if VALIDATE_CORPUS_SRC.is_file():
    from tests.corpus import validate_corpus as vc


@needs_full_checkout
def test_scrub_json_file_flags_a_key_not_in_the_allowlist(tmp_path: Path) -> None:
    path = tmp_path / "storage-status.json"
    path.write_text(json.dumps({"total": 1, "used": 1, "path": "/dev/sdb"}), encoding="utf-8")
    violations = vc._scrub_json_file(path, anonymize.STORAGE_STATUS_FIELDS)
    assert any("path" in v for v in violations)


@needs_full_checkout
def test_scrub_json_file_extra_key_ok_permits_a_disk_key(tmp_path: Path) -> None:
    path = tmp_path / "vm-config.json"
    path.write_text(json.dumps({"lock": "backup", "scsi0": "stor-aaaaaaaa:vm-101-disk-0"}), "utf-8")
    violations = vc._scrub_json_file(path, anonymize.VM_CONFIG_EXTRA_FIELDS, vc._is_disk_config_key)
    assert violations == []


@needs_full_checkout
def test_scrub_json_file_extra_key_ok_still_flags_a_non_disk_key(tmp_path: Path) -> None:
    path = tmp_path / "vm-config.json"
    path.write_text(json.dumps({"lock": "backup", "sshkeys": "ssh-rsa AAAA..."}), encoding="utf-8")
    violations = vc._scrub_json_file(path, anonymize.VM_CONFIG_EXTRA_FIELDS, vc._is_disk_config_key)
    assert any("sshkeys" in v for v in violations)


@needs_full_checkout
def test_scrub_pve_dir_now_checks_vm_snapshots_storage_content_and_status(
    tmp_path: Path,
) -> None:
    """X-03: before the fix, every one of these four subdirectories got
    the value-pattern pass only -- a leaked extra key went undetected."""
    pve_dir = tmp_path / "pve"
    (pve_dir / "vm-snapshots").mkdir(parents=True)
    (pve_dir / "vm-snapshots" / "101.json").write_text(
        json.dumps([{"name": "current", "description": "prod db, do not touch"}]),
        encoding="utf-8",
    )
    (pve_dir / "vm-status-current").mkdir(parents=True)
    (pve_dir / "vm-status-current" / "101.json").write_text(
        json.dumps({"lock": None, "pid": 12345}), encoding="utf-8"
    )
    (pve_dir / "vm-pending").mkdir(parents=True)
    (pve_dir / "vm-pending" / "101.json").write_text(
        json.dumps([{"key": "scsi0", "pending": True, "value": "stor-aaaaaaaa:vm-101-disk-0"}]),
        encoding="utf-8",
    )
    (pve_dir / "storage-content" / "node-aaaaaaaa").mkdir(parents=True)
    (pve_dir / "storage-content" / "node-aaaaaaaa" / "stor-bbbbbbbb.json").write_text(
        json.dumps([{"volid": "x", "vmid": 1, "size": 1, "notes": "leaked"}]), encoding="utf-8"
    )
    (pve_dir / "storage-status" / "node-aaaaaaaa").mkdir(parents=True)
    (pve_dir / "storage-status" / "node-aaaaaaaa" / "stor-bbbbbbbb.json").write_text(
        json.dumps({"total": 1, "used": 1, "path": "/dev/sdb"}), encoding="utf-8"
    )
    violations = vc._scrub_pve_dir(pve_dir)
    joined = "\n".join(violations)
    assert "description" in joined
    assert "pid" in joined
    assert "notes" in joined
    assert "path" in joined
    assert "value" in joined  # vm-pending/101.json: "value" is not in VM_PENDING_FIELDS


@needs_full_checkout
def test_scrub_prometheus_dir_flags_a_metric_label_outside_the_configured_set(
    tmp_path: Path,
) -> None:
    """X-03: `prometheus/` files previously got the value-pattern pass
    only -- a `metric` dict carrying a label outside the bundle's own
    `metrics.labels` set (e.g. a future edit that stops filtering) went
    undetected."""
    bundle_dir = tmp_path / "bundle"
    (bundle_dir / "prometheus" / "instant").mkdir(parents=True)
    (bundle_dir / "prometheus" / "instant" / "q1.json").write_text(
        json.dumps(
            {
                "query": "blockstat_rd_operations",
                "result": [
                    {
                        "metric": {"vmid": "101", "instance": "scsi0", "nodename": "leak"},
                        "value": [0, "1"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    config_path = bundle_dir / "config.yaml"
    config_path.write_text(
        "metrics:\n  labels:\n    vmid: vmid\n    device: instance\n    node: nodename\n",
        encoding="utf-8",
    )
    violations = vc._scrub_prometheus_dir(bundle_dir / "prometheus", config_path)
    assert violations == []  # "nodename" IS the configured node label -- clean

    # Now the bundle's own config renames the node label; the captured
    # file above still carries the old one, which must now be flagged.
    config_path.write_text(
        "metrics:\n  labels:\n    vmid: vmid\n    device: instance\n    node: host\n",
        encoding="utf-8",
    )
    violations = vc._scrub_prometheus_dir(bundle_dir / "prometheus", config_path)
    assert any("nodename" in v for v in violations)


@needs_full_checkout
def test_check_value_patterns_flags_internal_corp_and_lan_hostnames() -> None:
    """X-02: reproduced in 29.1 -- a `.example`/`.internal`/`.corp`/`.lan`
    host passed every value check before this fix."""
    # A real pseudonymized FQDN (Mapper.node()'s own "node-<8hex>.<8hex>
    # .invalid" shape) must NOT be flagged.
    assert vc._check_value_patterns("p", "node-1a2b3c4d.5e6f7a8b.invalid", "detail") == []
    for host in (
        "prometheus.corp",
        "pve01.internal",
        "backup.lan",
        "db.example",
    ):
        assert vc._check_value_patterns("p", f"connecting to {host} failed", "detail")


@needs_full_checkout
def test_check_value_patterns_flags_an_unredacted_transport_host_literal() -> None:
    text = "HTTPSConnectionPool(host='pve01.corp', port=8006): Max retries exceeded"
    assert vc._check_value_patterns("p", text, "detail")


@needs_full_checkout
def test_check_value_patterns_does_not_flag_the_collectors_own_sentinel() -> None:
    """Y-01: `collect._redact_free_text()`'s own replacement,
    `host='<redacted>'`, must not itself trip the backstop it satisfies --
    composed, the two halves of X-02's fix used to contradict each other."""
    assert vc._check_value_patterns("p", "HTTPSConnectionPool(host='<redacted>')", "detail") == []


@needs_full_checkout
def test_scrub_audit_passes_a_bundle_with_a_redacted_transport_failure(tmp_path: Path) -> None:
    """Y-01, end to end: a bundle whose capture hit a real transport failure
    (redacted correctly by X-02's collector-side fix) must pass the corpus
    gate, not be flagged by the audit's own backstop for the regression the
    fix closes. Reproduces the composition the two isolated X-02/Y-01 unit
    tests could not see on their own."""
    from tests.unit.test_collect import (
        CAPTURE_NOW,
        make_config,
        make_prometheus_client,
        make_pve_client,
    )

    resolved = make_config(tmp_path)
    options = collect.CaptureOptions(output_dir=str(tmp_path / "bundle"))
    client = make_pve_client(
        error_on="cluster/tasks",
        error_message=(
            "cluster/tasks: request failed: HTTPSConnectionPool("
            "host='pve01.internal.example.invalid', port=8006): "
            "Max retries exceeded with url: /api2/json/cluster/tasks"
        ),
    )
    bundle = collect.capture_bundle(
        client, make_prometheus_client(), resolved, options, now=CAPTURE_NOW
    )
    out = tmp_path / "bundle-dir"
    collect.write_bundle_dir(out, bundle)

    corpus_bundle = vc.Bundle(
        name="repro",
        directory=out,
        submission=tmp_path / "repro.submission.yaml",
        expected=tmp_path / "repro.expected.json",
    )
    violations = vc.scrub_audit(corpus_bundle)
    assert violations == []


@needs_full_checkout
def test_scrub_findings_json_flags_a_sample_series_label_outside_the_configured_set(
    tmp_path: Path,
) -> None:
    """Z-01: two committed corpus bundles carried a real, unmapped Telegraf
    ``host`` tag inside `_check_sample_series()`'s "sample series labels"
    message -- a dict-repr shape no value-pattern regex can catch (a bare
    hostname has no punctuation to match). This is the structural check
    that closes it: the message's own label key set must be a subset of
    the bundle's configured label names."""
    findings_path = tmp_path / "findings.json"
    findings_path.write_text(
        json.dumps(
            {
                "verify_metrics": {
                    "findings": [
                        {
                            "level": "info",
                            "message": (
                                "rd_operations: sample series labels {'host': 'data001', "
                                "'instance': 'ide2', 'nodename': 'node-9bcf256f', "
                                "'vmid': '389722'}"
                            ),
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "metrics:\n  labels:\n    vmid: vmid\n    device: instance\n    node: nodename\n",
        encoding="utf-8",
    )
    violations = vc._scrub_findings_json(findings_path, config_path)
    assert len(violations) == 1
    assert "host" in violations[0]


@needs_full_checkout
def test_scrub_findings_json_passes_the_allowlisted_view(tmp_path: Path) -> None:
    findings_path = tmp_path / "findings.json"
    findings_path.write_text(
        json.dumps(
            {
                "verify_metrics": {
                    "findings": [
                        {
                            "level": "info",
                            "message": (
                                "rd_operations: sample series labels {'instance': 'ide2', "
                                "'nodename': 'node-9bcf256f', 'vmid': '389722'}"
                            ),
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "metrics:\n  labels:\n    vmid: vmid\n    device: instance\n    node: nodename\n",
        encoding="utf-8",
    )
    assert vc._scrub_findings_json(findings_path, config_path) == []


@needs_full_checkout
def test_scrub_audit_catches_a_findings_json_label_leak_the_value_checks_miss(
    tmp_path: Path,
) -> None:
    """End to end through `scrub_audit()`: a bare, unmapped `host` value
    (no dot, no IP/email/hex/JWT shape) survives every existing
    value-pattern check -- only the Z-01 structural check catches it."""
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    (bundle_dir / "config.yaml").write_text(
        "metrics:\n  labels:\n    vmid: vmid\n    device: instance\n    node: nodename\n",
        encoding="utf-8",
    )
    (bundle_dir / "findings.json").write_text(
        json.dumps(
            {
                "verify_metrics": {
                    "findings": [
                        {
                            "level": "info",
                            "message": (
                                "rd_operations: sample series labels {'host': 'data001', "
                                "'instance': 'ide2', 'nodename': 'node-9bcf256f', "
                                "'vmid': '389722'}"
                            ),
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    corpus_bundle = vc.Bundle(
        name="repro",
        directory=bundle_dir,
        submission=tmp_path / "repro.submission.yaml",
        expected=tmp_path / "repro.expected.json",
    )
    violations = vc.scrub_audit(corpus_bundle)
    assert any("host" in v for v in violations)


@needs_full_checkout
def test_scrub_manifest_group_names_flags_a_group_name_outside_the_configured_set(
    tmp_path: Path,
) -> None:
    """AA-02: two committed corpus bundles carried a real, unpseudonymized
    group name inside `_drive_group_series()`'s own "instant
    quantile_over_time ... (<group name>)" call-log description -- a bare
    group name has no punctuation shape any value-pattern regex can catch.
    This is the structural check that closes it: the parenthesized
    qualifier must be one of the bundle's own configured group names."""
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "calls": [
                    {
                        "description": (
                            "instant quantile_over_time read_bytes q=0.95 (bzed-shared)"
                        ),
                        "detail": None,
                        "outcome": "ok",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "config.yaml"
    config_path.write_text("groups:\n- name: group-448ef164\n", encoding="utf-8")
    violations = vc._scrub_manifest_group_names(manifest_path, config_path)
    assert len(violations) == 1
    assert "bzed-shared" in violations[0]


@needs_full_checkout
def test_scrub_manifest_group_names_passes_the_pseudonymized_view(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "calls": [
                    {
                        "description": (
                            "instant quantile_over_time read_bytes q=0.95 (group-448ef164)"
                        ),
                        "detail": None,
                        "outcome": "ok",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "config.yaml"
    config_path.write_text("groups:\n- name: group-448ef164\n", encoding="utf-8")
    assert vc._scrub_manifest_group_names(manifest_path, config_path) == []


def _invariant_inputs(  # type: ignore[no-untyped-def]
    tmp_path: Path, shortfall_before: int, shortfall_after: int
):
    """A one-group, one-move plan whose payback block carries the given
    ``Sigma r_s`` pair -- everything else about it is legal."""
    (tmp_path / "config.yaml").write_text(
        "groups:\n- name: g1\n  storages:\n  - id: stor-a\n  - id: stor-b\n", encoding="utf-8"
    )
    bundle = vc.Bundle(
        name="b", directory=tmp_path, submission=tmp_path / "s", expected=tmp_path / "e"
    )
    report = {
        "groups": [
            {
                "name": "g1",
                "moves": [{"disk_key": "1:scsi0", "to_storage": "stor-b"}],
                "payback": {
                    "rejected_moves": [],
                    "reserve_shortfall_bytes_before": shortfall_before,
                    "reserve_shortfall_bytes_after": shortfall_after,
                },
            }
        ]
    }
    return bundle, [vc.VariantResult(variant={"solver_backend": "heuristic"}, report=report)]


@needs_full_checkout
def test_check_invariants_flags_a_plan_that_raises_the_reserve_shortfall(tmp_path: Path) -> None:
    bundle, results = _invariant_inputs(tmp_path, shortfall_before=100, shortfall_after=101)
    violations = vc.check_invariants(bundle, results)
    assert len(violations) == 1
    assert "raises the reserve shortfall from 100 to 101" in violations[0]


@needs_full_checkout
@pytest.mark.parametrize("before, after", [(100, 0), (100, 100), (0, 0), (5, 3)])
def test_check_invariants_accepts_a_plan_that_never_worsens_the_shortfall(
    tmp_path: Path, before: int, after: int
) -> None:
    """Including ``after > 0``: an unfixable shortfall is not a violation."""
    bundle, results = _invariant_inputs(tmp_path, before, after)
    assert vc.check_invariants(bundle, results) == []
