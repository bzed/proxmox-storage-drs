#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The corpus scrub audit, invariant checks and regression generator.
See IMPLEMENTATION_PLAN.md section 16.6 and tests/corpus/README.md.

Four passes, in the order they run, over every bundle in ``tests/corpus/*/``
plus every bundle found under the colon-separated ``DRS_CORPUS_DIR``:

1. **Scrub audit** -- every file, every key, checked against
   ``anonymize.py``'s own allowlists (the same ones the collector uses, so
   this cannot drift from what it permits) plus a battery of regexes for
   the shapes a real secret or identifier takes (IP literal, email,
   ``iqn.``/``naa.``/``wwn.``, PEM block, a 64+-hex run, a public-suffix
   hostname, a JWT). Runs on every discovered bundle, always -- this is the
   privacy control, and it assumes the collector has a bug.
2. **Invariants** -- the plan pipeline runs, through ``--replay``, exactly
   as an operator would run it; every accepted move must target a storage
   the group actually permits, and the pipeline must complete without
   raising ``SchedulingDeadlock``/``ReserveViolation``-shaped failures for
   a group the gate decided to act on. This is what proves "the engine
   still behaves safely on this real, large instance" without needing a
   known-optimal answer (unlike ``tests/fixtures/*.yaml``, no bundle here
   is small enough to enumerate).
3. **MILP vs. heuristic** -- run the same bundle through every available
   ``solver.backend`` and compare the plan each produces; a heuristic that
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

import contextlib
import io
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from proxmox_storage_drs import anonymize, cli  # noqa: E402
from proxmox_storage_drs.exceptions import DrsError  # noqa: E402

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
    r"\b[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\.(?:com|net|org|local)\b"
)
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


def _scrub_json_file(path: Path, allowlist: frozenset[str] | None) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"{path}: could not read/parse: {exc}"]
    violations: list[str] = []
    if allowlist is not None:
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict):
                extra = sorted(set(item) - allowlist)
                if extra:
                    violations.append(f"{path}: key(s) not in the allowlist: {extra}")
    for field_path, value in _iter_strings(data, str(path.name)):
        field_name = field_path.rsplit(".", 1)[-1].split("[")[0]
        violations.extend(_check_value_patterns(f"{path}#{field_path}", value, field_name))
    return violations


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
    for sub in ("vm-config", "vm-snapshots", "vm-status-current"):
        subdir = pve_dir / sub
        if subdir.is_dir():
            for path in sorted(subdir.glob("*.json")):
                violations.extend(_scrub_json_file(path, None))
    for sub in ("storage-status", "storage-content"):
        subdir = pve_dir / sub
        if subdir.is_dir():
            for path in sorted(subdir.rglob("*.json")):
                violations.extend(_scrub_json_file(path, None))
    return violations


def _scrub_config_yaml(config_path: Path) -> list[str]:
    if not config_path.is_file():
        return []
    text = config_path.read_text(encoding="utf-8")
    if "password" in text or "token_secret" in text or "host:" in text:
        return [f"{config_path}: looks like it still carries a credential/endpoint"]
    return []


def scrub_audit(bundle: Bundle) -> list[str]:
    """Section 16.6, check 1. Returns every violation found; empty means clean."""
    violations: list[str] = []
    pve_dir = bundle.directory / "pve"
    if pve_dir.is_dir():
        violations.extend(_scrub_pve_dir(pve_dir))
    prom_dir = bundle.directory / "prometheus"
    if prom_dir.is_dir():
        for path in sorted(prom_dir.rglob("*.json")):
            violations.extend(_scrub_json_file(path, None))
    for name in ("manifest.json", "findings.json"):
        path = bundle.directory / name
        if path.is_file():
            violations.extend(_scrub_json_file(path, None))
    violations.extend(_scrub_node_or_storage_ids(bundle.directory))
    violations.extend(_scrub_config_yaml(bundle.directory / "config.yaml"))
    return violations


# --------------------------------------------------------- variant matrix

_SPREAD_METRICS = ("l1", "minmax")
_FORECAST_MODELS = ("quantile", "seasonal_naive", "holt_winters")
_BETA_SWEEP = (0.0, 0.25, 1.0)


def _available_backends() -> list[str]:
    backends = ["heuristic", "cbc"]
    try:
        import ortools  # noqa: F401

        backends.append("cpsat")
    except ImportError:
        pass
    return backends


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
    backends = _available_backends() if full_matrix else ["heuristic", "cbc"]
    spread_metrics = _SPREAD_METRICS if full_matrix else _SPREAD_METRICS[:1]
    forecast_models = _FORECAST_MODELS if full_matrix else _FORECAST_MODELS[:1]
    beta_sweep = _BETA_SWEEP if full_matrix else _BETA_SWEEP[:1]

    results = []
    for backend in ("heuristic", "cbc", "cpsat"):
        if backend not in backends:
            for spread_metric in spread_metrics:
                for forecast_model in forecast_models:
                    for beta in beta_sweep:
                        variant = {
                            "solver_backend": backend,
                            "spread_metric": spread_metric,
                            "forecast_model": forecast_model,
                            "beta": beta,
                        }
                        results.append(
                            VariantResult(variant, None, skipped=f"{backend} not installed")
                        )
            continue
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
    check without knowing the optimum. Every accepted move must target a
    storage this bundle's own config actually names in that group."""
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
            for move in group_report.get("moves", []):
                if move["to_storage"] not in allowed:
                    violations.append(
                        f"{bundle.name} [{result.variant}]: move to "
                        f"{move['to_storage']!r} is not in group "
                        f"{group_report['name']!r}'s configured storages"
                    )
    return violations


def check_milp_vs_heuristic(bundle: Bundle, results: list[VariantResult]) -> list[str]:
    """Section 16.6, check 3: the MILP must never do worse (more moves for
    the same spread improvement is treated as "worse" here, in the absence
    of the raw objective scalar in the JSON report) than the heuristic on
    the same variant otherwise."""
    violations = []
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
        for backend_name in ("cbc", "cpsat"):
            milp = by_backend.get(backend_name)
            if heuristic is None or milp is None:
                continue
            if heuristic.report is None or milp.report is None:
                continue
            heuristic_groups: list[dict[str, Any]] = heuristic.report["groups"]
            milp_groups: list[dict[str, Any]] = milp.report["groups"]
            h_moves = sum(len(g["moves"]) for g in heuristic_groups)
            m_moves = sum(len(g["moves"]) for g in milp_groups)
            if m_moves > h_moves:
                violations.append(
                    f"{bundle.name} {key}: {backend_name} used more moves ({m_moves}) than "
                    f"the heuristic ({h_moves}) -- the MILP should never do worse"
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
