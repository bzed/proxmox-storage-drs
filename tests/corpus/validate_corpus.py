#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The corpus scrub audit, invariant checks and regression generator.
See IMPLEMENTATION_PLAN.md section 16.6 and tests/corpus/README.md.

Four passes, in the order they run, over every bundle in ``tests/corpus/*/``
plus every bundle found under the colon-separated ``DRS_CORPUS_DIR``:

1. **Scrub audit** -- every ``pve/`` and ``prometheus/`` file, every key,
   checked against ``anonymize.py``'s own allowlists (the same ones the
   collector uses, so this cannot drift from what it permits; a
   ``prometheus/`` series' ``metric`` dict is checked against the bundle's
   own configured label names, read from its ``config.yaml``) plus a
   battery of regexes for the shapes a real secret or identifier takes (IP
   literal, email, ``iqn.``/``naa.``/``wwn.``, PEM block, a 64+-hex run, a
   public-suffix hostname, an unredacted transport-failure ``host='...'``
   literal, a JWT). ``manifest.json``/``findings.json`` are hand-authored
   bundle metadata with no ``anonymize.py`` allowlist of their own (they
   are governed by ``collect._redact_free_text()`` instead, on the
   collector side) -- the regex battery is what checks them here. Runs on
   every discovered bundle, always -- this is the privacy control, and it
   assumes the collector has a bug.
2. **Invariants** -- the plan pipeline runs, through ``--replay``, exactly
   as an operator would run it; every accepted move must target a storage
   the group actually permits, and the pipeline must complete without
   raising ``SchedulingDeadlock``/``ReserveViolation``-shaped failures for
   a group the gate decided to act on. This is what proves "the engine
   still behaves safely on this real, large instance" without needing a
   known-optimal answer (unlike ``tests/fixtures/*.yaml``, no bundle here
   is small enough to enumerate).
3. **MILP vs. heuristic** -- run the same bundle through both swept
   ``solver.backend`` values (``cbc`` and ``heuristic``) and compare the
   plan each produces; a heuristic that
   moves more disks or reaches a worse spread than the MILP means the two
   have drifted apart on the shared feasibility/objective functions.
4. **Regression** -- ``<bundle>.expected.json`` records the ``plan --json``
   report of every variant swept (solver backend x spread metric x
   forecast model x a beta sweep). Generated, never hand-edited;
   ``--check`` asserts it is current.

Usage: python3 tests/corpus/validate_corpus.py [--check] [--full-matrix]

Without ``--full-matrix``, only the committed-bundle-sized sweep runs (what
``make check`` does, per the 8 MiB rule in section 16.6); ``--full-matrix``
is ``make corpus``'s target and also walks ``DRS_CORPUS_DIR``.
"""

from __future__ import annotations

import ast
import contextlib
import io
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from proxmox_storage_drs import anonymize, cli  # noqa: E402
from proxmox_storage_drs.exceptions import DrsError  # noqa: E402
from proxmox_storage_drs.topology import DISK_KEY_RE  # noqa: E402

# ------------------------------------------------------------- discovery


@dataclass(frozen=True)
class Bundle:
    name: str
    directory: Path
    submission: Path
    expected: Path


def _corpus_dirs(full_matrix: bool) -> list[Path]:
    dirs = [HERE]
    if full_matrix:
        for entry in os.environ.get("DRS_CORPUS_DIR", "").split(":"):
            if entry.strip():
                dirs.append(Path(entry.strip()))
    return dirs


def discover_bundles(full_matrix: bool = False) -> list[Bundle]:
    bundles = []
    for corpus_dir in _corpus_dirs(full_matrix):
        if not corpus_dir.is_dir():
            continue
        for entry in sorted(corpus_dir.iterdir()):
            if not entry.is_dir():
                continue
            if not (entry / "manifest.json").is_file():
                continue
            submission = entry.parent / f"{entry.name}.submission.yaml"
            expected = entry.parent / f"{entry.name}.expected.json"
            bundles.append(Bundle(entry.name, entry, submission, expected))
    return bundles


# ------------------------------------------------------------- scrub audit

_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_IPV6_RE = re.compile(r"\b[0-9a-fA-F]{0,4}(?::[0-9a-fA-F]{0,4}){5,}\b")
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_IQN_RE = re.compile(r"\b(?:iqn|naa|wwn)\.[\w.\-:]+\b", re.IGNORECASE)
_PEM_RE = re.compile(r"-----BEGIN [A-Z ]+-----")
_HEX64_RE = re.compile(r"\b[0-9a-fA-F]{64,}\b")
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")
_PUBLIC_SUFFIX_HOSTNAME_RE = re.compile(
    r"\b[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\."
    r"(?:com|net|org|local|internal|corp|lan|home|example|test)\b"
)
# X-02: a transport-level failure's own exception text survives collect.py's
# stripping only if a future edit removes it -- this pattern is the audit's
# own backstop for exactly that regression, independent of domain suffix.
# Y-01: the negative lookahead excludes collect.py's own redaction sentinel
# (`_TRANSPORT_HOST_RE.sub("host='<redacted>'", ...)`) -- without it, this
# backstop matched the *correctly redacted* output of the fix it exists to
# guard, and the first real bundle whose capture hit a transport failure
# could never pass the corpus gate.
_TRANSPORT_HOST_LITERAL_RE = re.compile(r"host='(?!<redacted>')[^']*'")
_PSEUDONYM_RE = re.compile(
    r"^(node|stor|group|tag|pool|user)-[0-9a-f]{8}(\.[0-9a-f]{8}\.invalid)?$"
)

# A pseudonymized FQDN's own ".invalid" suffix and the salt-fingerprint hex
# in manifest.json are expected long-hex-looking strings; excluded from the
# 64-hex-run check by field name rather than by pattern (a real leak could
# coincidentally look like either).
_ALLOWED_HEX_FIELDS = frozenset({"salt_fingerprint"})

_VALUE_CHECKS = (
    ("ipv4", _IPV4_RE),
    ("ipv6", _IPV6_RE),
    ("email", _EMAIL_RE),
    ("iqn/naa/wwn", _IQN_RE),
    ("PEM block", _PEM_RE),
    ("64+ hex run", _HEX64_RE),
    ("JWT-shaped string", _JWT_RE),
    ("public-suffix hostname", _PUBLIC_SUFFIX_HOSTNAME_RE),
    ("unredacted transport host", _TRANSPORT_HOST_LITERAL_RE),
)

# Allowlists keyed by the file's own position in the bundle layout (section
# 16.1) -- the same constants collect.py anonymizes with, so this cannot
# permit a field the collector itself would not have written.
_PVE_ALLOWLISTS: dict[str, frozenset[str]] = {
    "cluster-resources-vm.json": anonymize.VM_RESOURCE_FIELDS,
    "cluster-resources-storage.json": anonymize.STORAGE_RESOURCE_FIELDS,
    "storage-definitions.json": anonymize.STORAGE_DEFINITION_FIELDS,
    "nodes.json": anonymize.NODE_LIST_FIELDS,
    "cluster-tasks.json": anonymize.CLUSTER_TASK_FIELDS,
}

# X-03: the five top-level files above were, until this fix, the *only*
# files checked against a key allowlist -- every per-VM/per-storage file
# got value-pattern checks only, despite section 16.6 and this module's own
# docstring claiming "every file, every key". These two dicts extend the
# same mechanism to the rest of ``pve/`` (``vm-config/`` is handled
# separately in ``_scrub_pve_dir``: its allowlist is not a fixed set, see
# ``_is_disk_config_key``).
_PVE_FLAT_ALLOWLISTS: dict[str, frozenset[str]] = {
    "vm-snapshots": anonymize.VM_SNAPSHOT_FIELDS,
    "vm-status-current": anonymize.VM_STATUS_CURRENT_FIELDS,
    "vm-pending": anonymize.VM_PENDING_FIELDS,
}
_PVE_NESTED_ALLOWLISTS: dict[str, frozenset[str]] = {
    "storage-status": anonymize.STORAGE_STATUS_FIELDS,
    "storage-content": anonymize.STORAGE_CONTENT_FIELDS,
}


def _iter_strings(obj: Any, path: str) -> list[tuple[str, str]]:
    """Every (path, string-value) pair in a JSON-shaped structure."""
    out: list[tuple[str, str]] = []
    if isinstance(obj, str):
        out.append((path, obj))
    elif isinstance(obj, dict):
        for key, value in obj.items():
            out.extend(_iter_strings(value, f"{path}.{key}"))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            out.extend(_iter_strings(item, f"{path}[{i}]"))
    return out


def _check_value_patterns(path: str, value: str, field_name: str) -> list[str]:
    violations = []
    for label, pattern in _VALUE_CHECKS:
        if label == "64+ hex run" and field_name in _ALLOWED_HEX_FIELDS:
            continue
        if pattern.search(value):
            violations.append(f"{path}: value looks like {label}: {value[:60]!r}")
    return violations


def _scrub_json_file(
    path: Path,
    allowlist: frozenset[str] | None,
    extra_key_ok: Callable[[str], bool] | None = None,
) -> list[str]:
    """``allowlist`` (when given) is checked against every top-level dict in
    the file (or every item of a top-level list of dicts); ``extra_key_ok``
    is an escape hatch for an allowlist that is not a fixed set of names --
    today only ``vm-config/*.json``, whose disk keys vary per VM (section
    3.5's bus regex, ``anonymize.DISK_KEY_RE`` -- the same predicate
    ``anonymize.filter_vm_config_fields`` applies on the collector side, so
    the two still cannot drift)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"{path}: could not read/parse: {exc}"]
    violations: list[str] = []
    if allowlist is not None:
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict):
                extra = sorted(
                    k for k in (set(item) - allowlist) if not (extra_key_ok and extra_key_ok(k))
                )
                if extra:
                    violations.append(f"{path}: key(s) not in the allowlist: {extra}")
    for field_path, value in _iter_strings(data, str(path.name)):
        field_name = field_path.rsplit(".", 1)[-1].split("[")[0]
        violations.extend(_check_value_patterns(f"{path}#{field_path}", value, field_name))
    return violations


def _is_disk_config_key(key: str) -> bool:
    return bool(DISK_KEY_RE.match(key))


def _scrub_node_or_storage_ids(bundle_dir: Path) -> list[str]:
    violations = []
    nodes_path = bundle_dir / "pve" / "nodes.json"
    if nodes_path.is_file():
        for entry in json.loads(nodes_path.read_text(encoding="utf-8")):
            name = entry.get("node", "")
            if name and not _PSEUDONYM_RE.match(name):
                violations.append(f"{nodes_path}: node id {name!r} is not a valid pseudonym")
    defs_path = bundle_dir / "pve" / "storage-definitions.json"
    if defs_path.is_file():
        for entry in json.loads(defs_path.read_text(encoding="utf-8")):
            sid = entry.get("storage", "")
            if sid and not _PSEUDONYM_RE.match(sid):
                violations.append(f"{defs_path}: storage id {sid!r} is not a valid pseudonym")
    return violations


def _scrub_pve_dir(pve_dir: Path) -> list[str]:
    violations: list[str] = []
    for name, allowlist in _PVE_ALLOWLISTS.items():
        path = pve_dir / name
        if path.is_file():
            violations.extend(_scrub_json_file(path, allowlist))
    vm_config_dir = pve_dir / "vm-config"
    if vm_config_dir.is_dir():
        for path in sorted(vm_config_dir.glob("*.json")):
            violations.extend(
                _scrub_json_file(path, anonymize.VM_CONFIG_EXTRA_FIELDS, _is_disk_config_key)
            )
    for sub, allowlist in _PVE_FLAT_ALLOWLISTS.items():
        subdir = pve_dir / sub
        if subdir.is_dir():
            for path in sorted(subdir.glob("*.json")):
                violations.extend(_scrub_json_file(path, allowlist))
    for sub, allowlist in _PVE_NESTED_ALLOWLISTS.items():
        subdir = pve_dir / sub
        if subdir.is_dir():
            for path in sorted(subdir.rglob("*.json")):
                violations.extend(_scrub_json_file(path, allowlist))
    return violations


# X-03/X-02: ``prometheus/`` structure (section 16.1's per-kind table).
# Top-level shape is fixed per query kind; the ``metric`` dict inside each
# series is checked against the *configured* label names, read from the
# bundle's own config.yaml, since a bundle can rename them.
_PROMETHEUS_TOP_FIELDS: dict[str, frozenset[str]] = {
    "instant": frozenset({"query", "result"}),
    "range": frozenset({"query", "start", "end", "step", "result"}),
    "label-values": frozenset({"label", "result"}),
}
_PROMETHEUS_SERIES_FIELDS = frozenset({"metric", "value", "values"})


def _configured_label_names(config_path: Path) -> frozenset[str]:
    if not config_path.is_file():
        return frozenset()
    import yaml

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    labels = raw.get("metrics", {}).get("labels", {})
    return frozenset(v for v in labels.values() if isinstance(v, str))


def _scrub_prometheus_series(path: Path, data: Any, label_names: frozenset[str]) -> list[str]:
    violations: list[str] = []
    result = data.get("result") if isinstance(data, dict) else None
    if not isinstance(result, list):
        return violations
    for i, series in enumerate(result):
        if not isinstance(series, dict):
            continue
        extra = sorted(set(series) - _PROMETHEUS_SERIES_FIELDS)
        if extra:
            violations.append(f"{path}: result[{i}] key(s) not allowed: {extra}")
        metric = series.get("metric")
        if isinstance(metric, dict) and label_names:
            extra_labels = sorted(set(metric) - label_names)
            if extra_labels:
                violations.append(
                    f"{path}: result[{i}].metric label(s) not in the configured set "
                    f"{sorted(label_names)}: {extra_labels}"
                )
    return violations


def _scrub_prometheus_dir(prom_dir: Path, config_path: Path) -> list[str]:
    label_names = _configured_label_names(config_path)
    violations: list[str] = []
    known_dirs = set()
    for kind, top_allowlist in _PROMETHEUS_TOP_FIELDS.items():
        subdir = prom_dir / kind
        if not subdir.is_dir():
            continue
        known_dirs.add(subdir)
        for path in sorted(subdir.glob("*.json")):
            violations.extend(_scrub_json_file(path, top_allowlist))
            if kind == "label-values":
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            violations.extend(_scrub_prometheus_series(path, data, label_names))
    # Anything under prometheus/ outside the three known kinds still gets
    # the value-pattern pass (unchanged from before this fix), rather than
    # being silently skipped by an unrecognised layout.
    for path in sorted(prom_dir.rglob("*.json")):
        if path.parent not in known_dirs:
            violations.extend(_scrub_json_file(path, None))
    return violations


def _scrub_config_yaml(config_path: Path) -> list[str]:
    if not config_path.is_file():
        return []
    text = config_path.read_text(encoding="utf-8")
    if "password" in text or "token_secret" in text or "host:" in text:
        return [f"{config_path}: looks like it still carries a credential/endpoint"]
    return []


# Z-01: `_check_sample_series()`'s "sample series labels" finding dumps a
# live series' entire raw label dict into free text. `collect.py`'s
# `_redact_finding_message()` (bb9417b) rebuilds that one message from the
# same vmid/device/node-only view the structured `sample_series` field next
# to it already uses -- but nothing checked that a *committed* message
# actually stayed within that view (an unmapped Telegraf `host` tag reached
# two committed bundles this way, invisible to every value-pattern check
# above: a bare hostname has no punctuation shape to match). This is a
# dedicated structural check instead: a dict-repr label key set is
# computable from the bundle's own config.yaml alone, no mapper needed, and
# must be a subset of it.
_SAMPLE_SERIES_LABELS_RE = re.compile(r"^(?P<metric>.+?): sample series labels (?P<labels>\{.*\})$")


def _scrub_sample_series_message(
    findings_path: Path, index: int, message: str, label_names: frozenset[str]
) -> str | None:
    """One "sample series labels" finding's own check -- factored out of
    :func:`_scrub_findings_json` so that function stays a simple loop."""
    match = _SAMPLE_SERIES_LABELS_RE.match(message)
    if not match:
        return None
    try:
        labels = ast.literal_eval(match.group("labels"))
    except (ValueError, SyntaxError):
        return f"{findings_path}: findings[{index}].message: unparseable label dict"
    if not isinstance(labels, dict):
        return None
    extra = sorted(set(labels) - label_names)
    if not extra:
        return None
    return (
        f"{findings_path}: findings[{index}].message carries label(s) outside the "
        f"configured set {sorted(label_names)}: {extra}"
    )


# AA-02: `_redact_free_text()`'s group-name substitution (87b4a6c) fixed
# new captures, but nothing checked that an *already-committed* bundle's
# `manifest.json` actually stayed within its own config.yaml's group
# names -- a real group name reached two committed bundles' call logs
# this way, invisible to every value-pattern check above: a bare group
# name has no punctuation shape to match, the same reason Z-01's bare
# Telegraf host tag needed its own structural check. This is that check
# for `_drive_group_series()`'s own "instant quantile_over_time ... (<group
# name>)" description shape.
_GROUP_QUALIFIER_RE = re.compile(r"^instant quantile_over_time \S+ q=[\d.]+ \((?P<group>.+)\)$")


def _configured_group_names(config_path: Path) -> frozenset[str]:
    if not config_path.is_file():
        return frozenset()
    import yaml

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    groups = raw.get("groups", [])
    return frozenset(g["name"] for g in groups if isinstance(g, dict) and "name" in g)


def _scrub_manifest_group_names(manifest_path: Path, config_path: Path) -> list[str]:
    if not manifest_path.is_file():
        return []
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"{manifest_path}: could not read/parse: {exc}"]
    group_names = _configured_group_names(config_path)
    if not group_names:
        return []
    calls = data.get("calls") if isinstance(data, dict) else None
    if not isinstance(calls, list):
        return []
    violations: list[str] = []
    for i, call in enumerate(calls):
        description = call.get("description") if isinstance(call, dict) else None
        if not isinstance(description, str):
            continue
        match = _GROUP_QUALIFIER_RE.match(description)
        if match and match.group("group") not in group_names:
            violations.append(
                f"{manifest_path}: calls[{i}].description carries group qualifier "
                f"{match.group('group')!r}, not one of this bundle's own group names "
                f"{sorted(group_names)}"
            )
    return violations


def _scrub_findings_json(findings_path: Path, config_path: Path) -> list[str]:
    if not findings_path.is_file():
        return []
    try:
        data = json.loads(findings_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"{findings_path}: could not read/parse: {exc}"]
    label_names = _configured_label_names(config_path)
    if not label_names:
        return []
    verify_metrics = data.get("verify_metrics") if isinstance(data, dict) else None
    findings = verify_metrics.get("findings") if isinstance(verify_metrics, dict) else None
    if not isinstance(findings, list):
        return []
    violations: list[str] = []
    for i, finding in enumerate(findings):
        message = finding.get("message") if isinstance(finding, dict) else None
        if not isinstance(message, str):
            continue
        violation = _scrub_sample_series_message(findings_path, i, message, label_names)
        if violation:
            violations.append(violation)
    return violations


def scrub_audit(bundle: Bundle) -> list[str]:
    """Section 16.6, check 1. Returns every violation found; empty means clean.

    Every ``pve/`` and ``prometheus/`` file is checked against a key
    allowlist derived from ``anonymize.py`` (X-03: this used to be true of
    only the five top-level ``pve/`` files; every per-VM/per-storage file
    and every ``prometheus/`` file got the value-pattern pass only).
    ``manifest.json`` and ``findings.json`` are hand-authored bundle
    metadata, not a captured PVE/Prometheus object shape -- they have no
    ``anonymize.py`` allowlist to check keys against, and are governed
    instead by ``collect._redact_free_text()`` on the collector side; here
    they get the same value-pattern pass as everything else, which is what
    actually catches a redaction miss in free text (X-02)."""
    violations: list[str] = []
    pve_dir = bundle.directory / "pve"
    if pve_dir.is_dir():
        violations.extend(_scrub_pve_dir(pve_dir))
    prom_dir = bundle.directory / "prometheus"
    if prom_dir.is_dir():
        violations.extend(_scrub_prometheus_dir(prom_dir, bundle.directory / "config.yaml"))
    for name in ("manifest.json", "findings.json"):
        path = bundle.directory / name
        if path.is_file():
            violations.extend(_scrub_json_file(path, None))
    violations.extend(
        _scrub_findings_json(bundle.directory / "findings.json", bundle.directory / "config.yaml")
    )
    violations.extend(
        _scrub_manifest_group_names(
            bundle.directory / "manifest.json", bundle.directory / "config.yaml"
        )
    )
    violations.extend(_scrub_node_or_storage_ids(bundle.directory))
    violations.extend(_scrub_config_yaml(bundle.directory / "config.yaml"))
    return violations


# --------------------------------------------------------- variant matrix

_SPREAD_METRICS = ("l1", "minmax")
_FORECAST_MODELS = ("quantile", "seasonal_naive", "holt_winters")
_BETA_SWEEP = (0.0, 0.25, 1.0)


@dataclass
class VariantResult:
    variant: dict[str, Any]
    report: dict[str, Any] | None
    skipped: str | None = None


def _variant_config_overrides(variant: dict[str, Any]) -> dict[str, Any]:
    return {
        "solver": {"backend": variant["solver_backend"]},
        "objective": {
            "spread_metric": variant["spread_metric"],
            "beta_move_count": variant["beta"],
        },
        "forecast": {"model": variant["forecast_model"]},
    }


def _merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def _run_plan(bundle_dir: Path, config_path: Path) -> dict[str, Any] | None:
    buffer = io.StringIO()
    argv = ["--replay", str(bundle_dir), "-c", str(config_path), "--json", "plan"]
    with contextlib.redirect_stdout(buffer):
        try:
            cli.main(argv)
        except DrsError:
            return None
    text = buffer.getvalue().strip()
    if not text:
        return None
    try:
        result: dict[str, Any] = json.loads(text)
    except ValueError:
        return None
    return result


def run_variant_matrix(bundle: Bundle, full_matrix: bool) -> list[VariantResult]:
    import yaml

    raw_config = yaml.safe_load((bundle.directory / "config.yaml").read_text(encoding="utf-8"))
    # Both backends are always swept: the heuristic needs nothing
    # importable, and a `cbc` variant whose pulp is missing degrades to
    # the heuristic inside the run itself (`solver.backend`'s own
    # fallback), exactly as a live `plan` would -- so there is no
    # "not installed" skip for backends at all any more. The skip
    # machinery this replaced existed for the former CP-SAT backend
    # (REVIEW.md AL-02 removed it), whose availability was machine-
    # dependent; X-10/Y-02's backends-vs-`available` distinction is why
    # `VariantResult.skipped` stays a property of the sweep, recorded per
    # variant, rather than of the machine that happened to regenerate the
    # expected file.
    backends = ["heuristic", "cbc"]
    spread_metrics = _SPREAD_METRICS if full_matrix else _SPREAD_METRICS[:1]
    forecast_models = _FORECAST_MODELS if full_matrix else _FORECAST_MODELS[:1]
    beta_sweep = _BETA_SWEEP if full_matrix else _BETA_SWEEP[:1]

    results = []
    for backend in backends:
        for spread_metric in spread_metrics:
            for forecast_model in forecast_models:
                for beta in beta_sweep:
                    variant = {
                        "solver_backend": backend,
                        "spread_metric": spread_metric,
                        "forecast_model": forecast_model,
                        "beta": beta,
                    }
                    merged = _merge(raw_config, _variant_config_overrides(variant))
                    tmp_config = bundle.directory.parent / f".{bundle.name}.variant.yaml"
                    tmp_config.write_text(yaml.safe_dump(merged), encoding="utf-8")
                    try:
                        report = _run_plan(bundle.directory, tmp_config)
                    finally:
                        tmp_config.unlink(missing_ok=True)
                    results.append(VariantResult(variant, report))
    return results


# ------------------------------------------------------------- invariants


def check_invariants(bundle: Bundle, results: list[VariantResult]) -> list[str]:
    """Section 16.6, check 2 -- the safety properties a real bundle can
    check without knowing the optimum, reconstructed from what
    ``plan --json``'s own group report already records per variant (X-07:
    this used to check only the first of these). Four checks, none
    requiring the emitted order or the objective breakdown that only
    ``explain --json`` carries -- section 8.1's per-step transient
    predicate and the objective-recompute equality stay a named,
    deliberate gap (see section 16.6's own note) rather than a claim this
    function does not back:

    1. **(C2) group/storage legality.** Every accepted move targets a
       storage this bundle's own config actually names in that group.
    2. **Section 7.3's duration rule.** No accepted move carries
       ``exceeds_max_duration: true`` -- the pipeline's own payback/
       scheduling stage must never hand ``order_moves()`` a move it has
       already flagged as exceeding ``migration.max_single_move_duration``.
    3. **Rejected moves are not accepted moves.** A disk payback
       rejected must not also appear as an accepted move -- the two lists
       (``payback.rejected_moves`` and ``moves``) are supposed to partition
       the candidate set, never overlap.
    4. **The plan never worsens the reserve shortfall.** The payback
       block's ``reserve_shortfall_bytes_after`` (the final ``Sigma r_s``
       over the executed plan, section 9.5) must not exceed
       ``..._before``. Deliberately *not* ``after == 0`` -- an oversized
       ``min_free_bytes`` or a group with no feasible repair legitimately
       ends above zero. Why "never raised" holds depends on the backend
       and on ``hard`` (REVIEW.md AI-01):

       * **cbc**: the lexicographic solve (section 5.3's slack
         ``r_s``, section 5.5's two-stage backend) minimises ``Sigma r_s``
         alone in stage 1, so the *solver's endpoint* is never above the
         current assignment's.
       * **heuristic**: no such stage. ``_descend()`` optimises the whole
         section 5.4 objective, where the shortfall enters only as
         ``objective.reserve_violation_penalty`` times TiB short -- the
         configured value, unfloored (section 5.3's V-01 as-built note),
         so a balance-improving move that raises the shortfall can be
         accepted.
       * **what holds for every backend when ``hard = soft``** (the two
         older bundles): ``schedule.order_moves()`` schedules a move
         only if its target clears ``hard`` on arrival, so the *executed*
         plan cannot raise ``Sigma r_s`` whatever the solver produced --
         and the executed plan is what this check reads.
       * **``hard < soft``** (a deliberate dip, section 5.3.1): that
         scheduler guarantee no longer covers the endpoint, and a dropped
         (rejected/deadlocked) move can leave a MILP endpoint
         higher than the solver's. A violation here is a real signal, not
         noise -- the heuristic trading reserve for balance is a known,
         documented limitation, not a bug in this check -- but it is the
         one configuration where it can fire without a regression.
         ``bzed-dev-cluster-free-space`` is the committed bundle in this
         configuration; every backend the narrow sweep runs passes.
    """
    import yaml

    raw_config = yaml.safe_load((bundle.directory / "config.yaml").read_text(encoding="utf-8"))
    allowed_by_group = {
        g["name"]: {s["id"] for s in g["storages"]} for g in raw_config.get("groups", [])
    }
    violations = []
    for result in results:
        if result.report is None:
            continue
        for group_report in result.report.get("groups", []):
            allowed = allowed_by_group.get(group_report["name"], set())
            accepted_keys = {m["disk_key"] for m in group_report.get("moves", [])}
            for move in group_report.get("moves", []):
                if move["to_storage"] not in allowed:
                    violations.append(
                        f"{bundle.name} [{result.variant}]: move to "
                        f"{move['to_storage']!r} is not in group "
                        f"{group_report['name']!r}'s configured storages"
                    )
                if move.get("exceeds_max_duration"):
                    violations.append(
                        f"{bundle.name} [{result.variant}]: accepted move "
                        f"{move['disk_key']!r} in group {group_report['name']!r} exceeds "
                        "migration.max_single_move_duration -- section 7.3's duration rule"
                    )
            payback = group_report.get("payback") or {}
            overlap = accepted_keys & set(payback.get("rejected_moves", []))
            if overlap:
                violations.append(
                    f"{bundle.name} [{result.variant}]: group {group_report['name']!r} "
                    f"accepted move(s) {sorted(overlap)} also appear in payback's own "
                    "rejected list"
                )
            before = payback.get("reserve_shortfall_bytes_before")
            after = payback.get("reserve_shortfall_bytes_after")
            if before is not None and after is not None and after > before:
                violations.append(
                    f"{bundle.name} [{result.variant}]: group {group_report['name']!r} "
                    f"plan raises the reserve shortfall from {before} to {after} bytes "
                    "-- see check 4's docstring: expected never to happen with hard = soft; "
                    "with hard < soft the heuristic's unfloored penalty (V-01) can do it"
                )
    return violations


def check_milp_vs_heuristic(bundle: Bundle, results: list[VariantResult]) -> list[str]:
    """Section 16.6, check 3: the MILP must never reach a *dominated* plan
    -- one worse than the heuristic's on both persistent-objective axes at
    once -- on the same variant. Compares each group's own ``after_spread``
    (I/O balance, section 5.3 (C6)) *and* ``after_capacity_spread`` (data
    spread, section 5.3 (C7); both ``plan --json``'s already-computed
    post-plan fractions, lower is better), group by group -- *not* move
    count, and *not* either spread axis in isolation. Move count is not a
    valid proxy for "worse": at objective.beta_move_count=0.0 moves cost
    nothing, so a MILP reaching a far better spread with more moves than
    the heuristic is exactly the outcome this check exists to want, not
    flag. (Found for real on a 7-day holt_winters capture --
    tests/corpus/bzed-dev-cluster-7d-holt-winters -- where the previous
    move-count check flagged the then-CP-SAT backend for using 13 moves
    against the heuristic's 4, when its after_spread was ~0.00002 against
    the heuristic's 0.41: strictly better, not worse.)

    Section 12 added a second persistent-objective axis
    (``delta_capacity_spread``), and a solver can legitimately accept a
    worse I/O balance for a much better data spread (or vice versa) --
    comparing ``after_spread`` alone, as this check originally did,
    reintroduces exactly the "one metric is not a valid proxy once a
    second objective term exists" trap the move-count fix above already
    named, just on the axis section 12 added rather than the one
    ``beta_move_count`` already covered. Found for real on the same
    holt_winters bundle: cbc's after_spread (0.0122) was ~96x the
    heuristic's (0.000127) at the section 12 defaults, but its full
    objective total was *lower* (0.201 against 1.085) -- cbc had correctly
    traded a little imbalance for a much better after_capacity_spread
    (0.120 against the heuristic's 0.571) and zero fragmentation, exactly
    the trade `delta_capacity_spread` exists to make available. A
    violation is therefore only real when the MILP's plan is worse on
    *both* axes at once (Pareto-dominated), not merely different on one."""
    violations = []
    tolerance = 1e-6
    by_key: dict[tuple[Any, ...], dict[str, VariantResult]] = {}
    for result in results:
        if result.report is None:
            continue
        key = (
            result.variant["spread_metric"],
            result.variant["forecast_model"],
            result.variant["beta"],
        )
        by_key.setdefault(key, {})[result.variant["solver_backend"]] = result
    for key, by_backend in by_key.items():
        heuristic = by_backend.get("heuristic")
        for backend_name in ("cbc",):
            milp = by_backend.get(backend_name)
            if heuristic is None or milp is None:
                continue
            if heuristic.report is None or milp.report is None:
                continue
            heuristic_by_name = {g["name"]: g for g in heuristic.report["groups"]}
            milp_by_name = {g["name"]: g for g in milp.report["groups"]}
            for name, h_group in heuristic_by_name.items():
                m_group = milp_by_name.get(name)
                if m_group is None:
                    continue
                h_spread = h_group.get("after_spread")
                m_spread = m_group.get("after_spread")
                h_capacity = h_group.get("after_capacity_spread")
                m_capacity = m_group.get("after_capacity_spread")
                # Either side not having acted leaves nothing comparable --
                # not a violation, just not this check's case.
                if h_spread is None or m_spread is None:
                    continue
                worse_spread = m_spread > h_spread + tolerance
                # A bundle captured before section 12 (or a group whose
                # mean fill is 0, section 5.3 (C7)) never populates
                # after_capacity_spread -- fall back to the single-axis
                # comparison rather than treating a missing value as
                # "better" and masking a real regression.
                if h_capacity is None or m_capacity is None:
                    worse_capacity = worse_spread
                else:
                    worse_capacity = m_capacity > h_capacity + tolerance
                if worse_spread and worse_capacity:
                    violations.append(
                        f"{bundle.name} {key} group {name!r}: {backend_name}'s plan is "
                        f"Pareto-dominated by the heuristic's -- after_spread ({m_spread:g} "
                        f"vs {h_spread:g}) and after_capacity_spread "
                        f"({m_capacity!r} vs {h_capacity!r}) are both worse"
                    )
    return violations


# X-07: "both MILP backends agree to within the section 5.5 tolerance" (the
# other half of check 3) never had a cbc-vs-cpsat check here, and now
# cannot: the CP-SAT backend was removed (REVIEW.md AL-02). A first
# attempt comparing `after_spread` against `solver.mip_gap` as a relative
# tolerance produced real, non-spurious disagreement on a committed bundle
# under --full-matrix: cbc 0.0016 vs cpsat 0.0034-0.0112 across several
# variants, all `mip_gap`-legitimate on the *objective* the solvers actually
# optimize, but a >5x difference in the derived `after_spread` metric alone
# -- `mip_gap` bounds suboptimality of the five-term objective, not of any
# one term taken in isolation, and a tiny baseline spread turns a small
# absolute gap into a huge relative one. Getting this right needs the
# objective breakdown itself, which today only `explain --json` emitted at
# the time this note was written -- `plan --json`'s own
# `before/after_objective_total` (added for REVIEW.md AA-01) closes that
# gap; `check_milp_objective_total()` below is the check this note used to
# say could not be shipped yet.


def check_milp_objective_total(bundle: Bundle, results: list[VariantResult]) -> list[str]:
    """REVIEW.md AA-01's own recommendation, the objective-level version of
    `check_milp_vs_heuristic()`'s dominance check: "not dominated" is
    checkable cheaply from the two spread axes alone, but "optimized the
    objective we wrote" needs the objective itself. CP-SAT's (C7)
    linearization once scaled `d_s` six orders of magnitude too strongly,
    so the default `auto` backend planned mass relocations that were
    *worse* than doing nothing on the very objective `solver.*`/
    `objective.*` configure -- invisible to the Pareto check above because
    the amplified plan traded a tiny, real gain on one axis for a huge,
    illegitimate one on the other, so neither spread axis alone was ever
    "both worse". Asserts each MILP backend's `after_objective_total` is
    no worse than the heuristic's by more than `solver.mip_gap` (the
    backend's own configured suboptimality tolerance on this exact
    objective) plus a small floor for near-zero objectives, catching this
    class of scaling defect at any `delta_capacity_spread`, for any future
    objective term, without needing a dedicated fixture for each."""
    import yaml

    violations = []
    raw_config = yaml.safe_load((bundle.directory / "config.yaml").read_text(encoding="utf-8"))
    mip_gap = raw_config.get("solver", {}).get("mip_gap", 0.02)
    by_key: dict[tuple[Any, ...], dict[str, VariantResult]] = {}
    for result in results:
        if result.report is None:
            continue
        key = (
            result.variant["spread_metric"],
            result.variant["forecast_model"],
            result.variant["beta"],
        )
        by_key.setdefault(key, {})[result.variant["solver_backend"]] = result
    for key, by_backend in by_key.items():
        heuristic = by_backend.get("heuristic")
        for backend_name in ("cbc",):
            milp = by_backend.get(backend_name)
            if heuristic is None or milp is None:
                continue
            if heuristic.report is None or milp.report is None:
                continue
            heuristic_by_name = {g["name"]: g for g in heuristic.report["groups"]}
            milp_by_name = {g["name"]: g for g in milp.report["groups"]}
            for name, h_group in heuristic_by_name.items():
                m_group = milp_by_name.get(name)
                if m_group is None:
                    continue
                h_total = h_group.get("after_objective_total")
                m_total = m_group.get("after_objective_total")
                if h_total is None or m_total is None:
                    continue
                tolerance = mip_gap * max(abs(h_total), abs(m_total), 1.0) + 1e-6
                if m_total > h_total + tolerance:
                    violations.append(
                        f"{bundle.name} {key} group {name!r}: {backend_name}'s plan scores "
                        f"{m_total:g} on the configured objective against the heuristic's "
                        f"{h_total:g} -- worse by more than solver.mip_gap ({mip_gap:g}), i.e. "
                        f"{backend_name} did not optimize the objective it was given"
                    )
    return violations


# ------------------------------------------------------------- regression


def build_expected(bundle: Bundle, results: list[VariantResult]) -> dict[str, Any]:
    cases = []
    for result in results:
        cases.append(
            {
                "variant": result.variant,
                "skipped": result.skipped,
                "report": result.report,
            }
        )
    return {"schema_version": 1, "bundle": bundle.name, "cases": cases}


# ------------------------------------------------------------------- main


def _submission_present(bundle: Bundle) -> list[str]:
    if not bundle.submission.is_file():
        return [
            f"{bundle.name}: no {bundle.submission.name} -- an unattributed dump, not a test case"
        ]
    return []


def main(argv: list[str]) -> int:
    check = "--check" in argv
    full_matrix = "--full-matrix" in argv
    bundles = discover_bundles(full_matrix=full_matrix)

    all_violations: list[str] = []
    stale: list[str] = []

    for bundle in bundles:
        all_violations.extend(_submission_present(bundle))
        all_violations.extend(scrub_audit(bundle))

        results = run_variant_matrix(bundle, full_matrix=full_matrix)
        all_violations.extend(check_invariants(bundle, results))
        all_violations.extend(check_milp_vs_heuristic(bundle, results))
        all_violations.extend(check_milp_objective_total(bundle, results))

        expected = build_expected(bundle, results)
        text = json.dumps(expected, indent=2, sort_keys=True) + "\n"
        if check:
            current = (
                bundle.expected.read_text(encoding="utf-8") if bundle.expected.is_file() else None
            )
            if current != text:
                stale.append(bundle.expected.name)
        else:
            bundle.expected.write_text(text, encoding="utf-8")
            print(f"wrote {bundle.expected}")

    if not bundles:
        print("no bundles found -- a clean pass (tests/corpus/README.md)")

    if all_violations:
        print(f"{len(all_violations)} violation(s):", file=sys.stderr)
        for v in all_violations:
            print(f"  {v}", file=sys.stderr)
    if stale:
        print(f"stale, re-run without --check: {', '.join(stale)}", file=sys.stderr)

    return 1 if (all_violations or stale) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
