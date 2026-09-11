# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read a diagnostic bundle back and serve it through the same interfaces
:mod:`proxmox_storage_drs.pve` and :mod:`proxmox_storage_drs.metrics`
define. See IMPLEMENTATION_PLAN.md section 16.5.

Both clients below are real subclasses of :class:`~proxmox_storage_drs.pve.PveClient`
and :class:`~proxmox_storage_drs.metrics.PrometheusClient` respectively --
not merely duck-typed lookalikes -- so every existing ``client: PveClient``/
``client: PrometheusClient`` annotation in the rest of the codebase
(``topology.py``, ``metrics.verify_metrics()``, ...) accepts one with no
signature change anywhere else. Each constructs its parent with a ``None``
(or otherwise inert) transport and overrides every method that would
otherwise touch it, so nothing in this module can ever open a socket --
``cli.py``'s own unit test asserts this directly (section 16.5: "a bug
cannot fall back to a live cluster").

**Range queries and the trimming design.** A bundle captures exactly one
range file per (group, raw metric) pair, spanning ``support.capture_range``
-- the union of every forecaster's own ``required_range()``, not just the
one the operator had configured (section 16.2). A live replay run may ask
for a *narrower* window of that same series (a different, smaller
``required_range()`` from a forecaster selected via ``-c``, section 16.5),
always ending at this bundle's own fixed :func:`bundle_reference_now`.
:meth:`ReplayPrometheusClient._get` therefore does not key a range lookup on
the literal requested start/end at all -- it looks up the one stored series
for that query text and ``step``, then trims it to the requested window,
raising :class:`~proxmox_storage_drs.exceptions.BundleError` (section
16.5's "loud, specific" cache miss) if the request falls outside what was
actually captured, or asks for a different ``step``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from proxmox_storage_drs.collect import hash_label_name, hash_query_text
from proxmox_storage_drs.config import PrometheusConfig
from proxmox_storage_drs.exceptions import BundleError, PveApiError
from proxmox_storage_drs.metrics import PrometheusClient
from proxmox_storage_drs.pve import PveClient


def load_manifest(bundle_dir: str | Path) -> dict[str, Any]:
    path = Path(bundle_dir) / "manifest.json"
    if not path.is_file():
        raise BundleError(f"{bundle_dir}: not a bundle directory (no manifest.json)")
    try:
        manifest: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BundleError(f"{path}: could not read manifest: {exc}") from exc
    return manifest


def bundle_reference_now(bundle_dir: str | Path) -> datetime:
    """The fixed instant every replay run against this bundle treats as
    "now" -- the capture's own rebased instant (``manifest.json``'s
    ``capture.synthetic_now_epoch``, section 16.3), so two replay runs (or
    two commands in the same run) always compute the same absolute query
    window and hit the same cache keys."""
    manifest = load_manifest(bundle_dir)
    try:
        epoch = float(manifest["capture"]["synthetic_now_epoch"])
    except (KeyError, TypeError, ValueError) as exc:
        raise BundleError(
            f"{bundle_dir}: manifest.json has no usable capture.synthetic_now_epoch"
        ) from exc
    return datetime.fromtimestamp(epoch, tz=timezone.utc)


class ReplayPveClient(PveClient):
    """Serves ``pve.py``'s ten read methods from a bundle's ``pve/``
    directory. ``move_disk``/``task_status`` raise -- defense in depth,
    since ``cli.py`` refuses ``apply``/an escalated ``--mode`` under
    ``--replay`` before either could ever be reached."""

    def __init__(self, bundle_dir: str | Path) -> None:
        super().__init__(api=None)
        self._dir = Path(bundle_dir)

    def _load(self, relpath: str, description: str) -> Any:
        path = self._dir / "pve" / relpath
        if not path.is_file():
            raise BundleError(
                f"bundle has no recorded response for {description} "
                f"(expected {path.relative_to(self._dir)})"
            )
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise BundleError(f"{path}: could not read: {exc}") from exc

    def vm_resources(self) -> list[dict[str, Any]]:
        return list(self._load("cluster-resources-vm.json", "VM inventory"))

    def cluster_tasks(self) -> list[dict[str, Any]]:
        return list(self._load("cluster-tasks.json", "cluster task list"))

    def storage_resources(self) -> list[dict[str, Any]]:
        return list(self._load("cluster-resources-storage.json", "storage inventory"))

    def node_names(self) -> list[str]:
        raw = self._load("nodes.json", "node list")
        return sorted({str(n["node"]) for n in raw if n.get("node")})

    def storage_definitions(self) -> list[dict[str, Any]]:
        return list(self._load("storage-definitions.json", "storage definitions"))

    def vm_config(self, node: str, vmid: int) -> dict[str, Any]:
        del node  # the bundle keys VM files by vmid alone -- see this module's docstring
        return dict(self._load(f"vm-config/{vmid}.json", f"config for VM {vmid}"))

    def storage_status(self, node: str, storage: str) -> dict[str, Any]:
        return dict(
            self._load(f"storage-status/{node}/{storage}.json", f"status of {storage!r} on {node}")
        )

    def storage_content(self, node: str, storage: str) -> list[dict[str, Any]]:
        return list(
            self._load(
                f"storage-content/{node}/{storage}.json", f"content of {storage!r} on {node}"
            )
        )

    def vm_snapshots(self, node: str, vmid: int) -> list[dict[str, Any]]:
        del node
        return list(self._load(f"vm-snapshots/{vmid}.json", f"snapshots for VM {vmid}"))

    def vm_status_current(self, node: str, vmid: int) -> dict[str, Any]:
        del node
        return dict(self._load(f"vm-status-current/{vmid}.json", f"status for VM {vmid}"))

    def move_disk(self, *args: Any, **kwargs: Any) -> str:
        raise PveApiError("--replay is read-only: move_disk cannot be issued under replay")

    def task_status(self, node: str, upid: str) -> dict[str, Any]:
        del node, upid
        raise PveApiError("--replay is read-only: task_status cannot be issued under replay")


def _parse_step_seconds(step_text: str) -> float:
    """The inverse of ``metrics._format_promql_duration()``, which this
    project only ever emits as ``f"{seconds:g}s"``."""
    if step_text.endswith("s"):
        try:
            return float(step_text[:-1])
        except ValueError:
            pass
    raise BundleError(f"unrecognized Prometheus step parameter {step_text!r}")


def _trim_range_result(
    payload: dict[str, Any], requested_start: float, requested_end: float, requested_step: float
) -> list[dict[str, Any]]:
    stored_start = float(payload["start"])
    stored_end = float(payload["end"])
    stored_step = float(payload["step"])
    if abs(stored_step - requested_step) > 1e-6:
        raise BundleError(
            f"bundle has a range capture for {payload['query']!r} at step {stored_step:g}s, "
            f"but this replay requested step {requested_step:g}s -- captured with a different "
            "metrics.step?"
        )
    # A little slack for floating-point rounding across the anonymized
    # epoch rebase, not for a genuinely out-of-range request.
    if requested_start < stored_start - 1.0 or requested_end > stored_end + 1.0:
        raise BundleError(
            f"bundle has no recorded response for {payload['query']!r} over "
            f"[{requested_start:.0f},{requested_end:.0f}] -- captured range was "
            f"[{stored_start:.0f},{stored_end:.0f}]"
        )
    trimmed = []
    for series in payload["result"]:
        values = [
            [ts, val]
            for ts, val in series.get("values", [])
            if requested_start <= ts <= requested_end
        ]
        trimmed.append({"metric": series["metric"], "values": values})
    return trimmed


class ReplayPrometheusClient(PrometheusClient):
    """Overrides only ``_get`` -- ``instant_query``/``range_query``/
    ``label_values`` are inherited unchanged and funnel through it, exactly
    as the real client's do."""

    def __init__(self, config: PrometheusConfig, bundle_dir: str | Path) -> None:
        super().__init__(config, session=_NeverSession())
        self._dir = Path(bundle_dir)

    def _load(self, relpath: str) -> dict[str, Any]:
        path = self._dir / "prometheus" / relpath
        if not path.is_file():
            return {}
        try:
            data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise BundleError(f"{path}: could not read: {exc}") from exc
        return data

    def _get(self, path: str, params: dict[str, str]) -> Any:
        # Mirrors PrometheusClient._get()'s own contract exactly: `data` is
        # a bare list only for the label-values endpoint, and a dict with a
        # `result` key (what instant_query()/range_query() call `.get()` on)
        # for query/query_range -- metrics.py:258-278.
        if path == "/api/v1/query":
            query = params["query"]
            payload = self._load(f"instant/{hash_query_text(query)}.json")
            if not payload:
                raise BundleError(
                    f"bundle has no recorded response for the instant query {query!r}"
                )
            return {"result": payload["result"]}
        if path == "/api/v1/query_range":
            query = params["query"]
            payload = self._load(f"range/{hash_query_text(query)}.json")
            if not payload:
                raise BundleError(f"bundle has no recorded response for the range query {query!r}")
            trimmed = _trim_range_result(
                payload,
                float(params["start"]),
                float(params["end"]),
                _parse_step_seconds(params["step"]),
            )
            return {"result": trimmed}
        if path.startswith("/api/v1/label/") and path.endswith("/values"):
            label_name = path[len("/api/v1/label/") : -len("/values")]
            payload = self._load(f"label-values/{hash_label_name(label_name)}.json")
            if not payload:
                raise BundleError(f"bundle has no recorded label values for {label_name!r}")
            values: Any = payload["result"]
            return values
        raise BundleError(f"--replay does not support the Prometheus endpoint {path!r}")


class _NeverSession:
    """The ``session`` handed to :class:`PrometheusClient.__init__`. Its
    ``get`` is unreachable -- ``ReplayPrometheusClient._get`` never calls
    ``super()._get()`` -- and exists only so a bug that *did* reach it fails
    loudly instead of silently constructing a real ``requests.Session``
    (section 16.5's own explicit requirement, verified by a unit test)."""

    def get(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover - defense in depth
        raise BundleError("--replay must never make a real Prometheus request")
