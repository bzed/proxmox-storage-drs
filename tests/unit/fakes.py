# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared test doubles. Not collected by pytest (no ``test_`` prefix).

:class:`FakeProxmoxResource` replicates proxmoxer's own dynamic
``ProxmoxResource`` protocol (attribute access and calling both extend a
path; only a terminal ``get()``/``post()`` does anything) closely enough
that :class:`~proxmox_storage_drs.pve.PveClient` cannot tell it apart from
the real, network-capable ``proxmoxer.ProxmoxAPI`` it is normally
constructed with -- see ``.agents/testing.md``: no test talks to a real PVE.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FakeProxmoxResource:
    responses: dict[str, Any]
    calls: list[tuple[str, str, dict[str, Any]]]
    error: BaseException | None = None
    _path: tuple[str, ...] = field(default_factory=tuple)

    def __getattr__(self, item: str) -> "FakeProxmoxResource":
        if item.startswith("_"):
            raise AttributeError(item)
        return FakeProxmoxResource(self.responses, self.calls, self.error, self._path + (item,))

    def __call__(self, resource_id: object) -> "FakeProxmoxResource":
        return FakeProxmoxResource(
            self.responses, self.calls, self.error, self._path + (str(resource_id),)
        )

    def _resolve(self, method: str, kwargs: dict[str, Any]) -> Any:
        path = "/".join(self._path)
        self.calls.append((method, path, kwargs))
        if self.error is not None:
            raise self.error
        value = self.responses[path]
        # A callable response lets one path answer differently by query
        # param -- needed for e.g. `cluster/resources`, which both
        # vm_resources() and storage_resources() call with a different
        # `type=` and must not collide on a single canned value.
        return value(**kwargs) if callable(value) else value

    def get(self, **params: Any) -> Any:
        return self._resolve("GET", params)

    def post(self, **data: Any) -> Any:
        return self._resolve("POST", data)


def fake_api(responses: dict[str, Any], error: BaseException | None = None) -> FakeProxmoxResource:
    return FakeProxmoxResource(responses=responses, calls=[], error=error)
