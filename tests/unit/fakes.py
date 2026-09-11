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


@dataclass
class FakeQueryResponse:
    """Matches ``metrics._ResponseLike``: ``.status_code`` and ``.json()``."""

    status_code: int = 200
    payload: Any = field(default_factory=dict)
    text: str = ""

    def json(self) -> Any:
        return self.payload


@dataclass
class FakePrometheusSession:
    """A ``metrics._SessionLike`` double capable of answering *many*
    distinct queries against one endpoint path -- ``FakeSession`` in
    ``test_metrics.py`` answers one canned value per path, which is not
    enough for ``collect.py``'s tests, where every one of the six raw
    metrics' quantile/range queries needs its own response. ``answers`` maps
    a path (matched by suffix, as ``FakeSession`` does) to either a fixed
    payload or a callable ``params -> payload``, so one entry can vary its
    answer by ``params["query"]``/``params["start"]``/etc.
    """

    answers: dict[str, Any]
    calls: list[tuple[str, dict[str, str]]] = field(default_factory=list)

    def get(
        self,
        url: str,
        params: dict[str, str],
        timeout: float,
        auth: object,
        headers: dict[str, str],
    ) -> FakeQueryResponse:
        del timeout, auth, headers
        for path, answer in self.answers.items():
            if url.endswith(path):
                self.calls.append((path, dict(params)))
                payload = answer(params) if callable(answer) else answer
                if isinstance(payload, BaseException):
                    raise payload
                return FakeQueryResponse(200, {"status": "success", "data": payload})
        self.calls.append((url, dict(params)))
        # No entry matched: an empty-but-valid default, shaped for whichever
        # endpoint this is -- a bare list for label_values, an empty
        # `result` for query/query_range -- so a collect.py/replay.py test
        # that only cares about a handful of specific queries does not have
        # to enumerate every internal call verify_metrics() itself makes.
        default: Any = [] if "/label/" in url else {"result": []}
        return FakeQueryResponse(200, {"status": "success", "data": default})
