# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Proxmox VE API client. See IMPLEMENTATION_PLAN.md section 3.5.

Built on ``proxmoxer`` rather than a hand-rolled ticket/CSRF client. The
decisive reason is ``proxmoxer``'s backend abstraction: the same
``ProxmoxAPI`` attribute-chaining interface
(``proxmox.nodes(node).qemu(vmid).config.get()``) is available over plain
HTTPS (what :func:`build_client` uses today) or over SSH (``openssh``,
shelling out to the system's own ``ssh``+``pvesh``, or ``ssh_paramiko``, an
in-process SSH client) -- a future deployment that cannot open the API port
to the management host becomes a one-line change in :func:`build_client`,
with no change to :class:`PveClient`'s methods or to anything that calls
them. ``proxmoxer`` is an optional-in-name-only hard dependency: it is
imported at module level because there is no meaningful code path in this
project that does not eventually need the PVE API.

Every method here is exactly one API call, with no caching and no retry
logic -- the per-run topology cache belongs to ``topology.py`` (section 3.5:
"a per-run topology cache -- one snapshot at the start of the run").
"""

from __future__ import annotations

from typing import Any

import requests
from proxmoxer import AuthenticationError, ProxmoxAPI, ResourceException

from proxmox_storage_drs.config import ProxmoxConfig
from proxmox_storage_drs.exceptions import PveApiError

# proxmoxer's own https-backend default (5s) is tuned for an interactive CLI
# rather than a bounded thread pool fetching hundreds of VM configs; 10s is a
# "short" per-request timeout in the sense section 3.5 means (as opposed to
# unbounded), not yet the configurable value that section's read-path
# thread-pool retry logic will eventually need -- that lands with
# topology.py's concurrent fetch implementation, not here.
_DEFAULT_TIMEOUT_SECONDS = 10.0


def build_client(config: ProxmoxConfig) -> "PveClient":
    """Construct a :class:`PveClient` from ``config.py``'s ``ProxmoxConfig``.

    Always the ``https`` ``proxmoxer`` backend today; see this module's
    docstring for why switching to an SSH backend later needs no change
    beyond this function.
    """
    auth = config.auth
    # requests (and so proxmoxer's https backend) accepts either a bool or a
    # CA-bundle path for "verify" -- config.py keeps these as two separate
    # knobs (verify_ssl, ca_file) because that is how an operator thinks
    # about them, so join them back into the one value proxmoxer wants here.
    verify: bool | str = config.ca_file if config.ca_file else config.verify_ssl

    kwargs: dict[str, Any] = {
        "host": config.host,
        "port": config.port,
        "verify_ssl": verify,
        "timeout": _DEFAULT_TIMEOUT_SECONDS,
    }
    if auth.token_id and auth.token_secret:
        # section 3.5: "user@realm!tokenname" -- proxmoxer wants the two
        # halves passed separately.
        user, separator, token_name = auth.token_id.partition("!")
        if not separator:
            raise PveApiError(
                f"proxmox.auth.token_id {auth.token_id!r} is not in 'user@realm!tokenname' form"
            )
        kwargs["user"] = user
        kwargs["token_name"] = token_name
        kwargs["token_value"] = auth.token_secret
    elif auth.username and auth.password:
        kwargs["user"] = auth.username
        kwargs["password"] = auth.password
    else:
        raise PveApiError(
            "proxmox.auth needs either token_id and token_secret, or username and password"
        )

    try:
        api = ProxmoxAPI(**kwargs)
    except (AuthenticationError, requests.RequestException) as exc:
        raise PveApiError(f"could not authenticate to the Proxmox VE API: {exc}") from exc
    return PveClient(api)


class PveClient:
    """One method per IMPLEMENTATION_PLAN.md section 3.5 endpoint.

    ``api`` is typed ``Any`` because ``proxmoxer.ProxmoxAPI`` resolves every
    attribute and call dynamically (no static shape to describe) and ships
    no type stubs; tests inject a small fake replicating that same
    attribute-chaining protocol rather than the real network-capable object
    (.agents/testing.md).
    """

    def __init__(self, api: Any) -> None:
        self._api = api

    def _call(self, description: str, action: Any) -> Any:
        """Run one ``proxmoxer`` call, wrapping every failure as :class:`PveApiError`.

        ``ResourceException`` covers HTTP-level API errors (4xx/5xx);
        ``requests.RequestException`` covers transport failures (connection
        refused, timeout) that ``proxmoxer``'s https backend does not wrap
        itself.
        """
        try:
            return action()
        except (ResourceException, AuthenticationError) as exc:
            raise PveApiError(f"{description}: {exc}") from exc
        except requests.RequestException as exc:
            raise PveApiError(f"{description}: request failed: {exc}") from exc

    # ------------------------------------------------------------ read path

    def vm_resources(self) -> list[dict[str, Any]]:
        """``GET /cluster/resources?type=vm``: VM inventory."""
        result: list[dict[str, Any]] = self._call(
            "fetching VM inventory", lambda: self._api.cluster.resources.get(type="vm")
        )
        return result

    def storage_resources(self) -> list[dict[str, Any]]:
        """``GET /cluster/resources?type=storage``: storage inventory."""
        result: list[dict[str, Any]] = self._call(
            "fetching storage inventory", lambda: self._api.cluster.resources.get(type="storage")
        )
        return result

    def storage_definitions(self) -> list[dict[str, Any]]:
        """``GET /storage``: every storage's full config, including ``saferemove``.

        Deliberately the list form, not the singular ``GET /storage/{id}``:
        verified against a live PVE 9.2.11 cluster that the singular form
        requires ``Datastore.Allocate`` while this one needs only
        ``Datastore.Audit`` for the identical data, one call for every
        storage instead of one per storage (section 3.5).
        """
        result: list[dict[str, Any]] = self._call(
            "fetching storage definitions", lambda: self._api.storage.get()
        )
        return result

    def vm_config(self, node: str, vmid: int) -> dict[str, Any]:
        """``GET /nodes/{node}/qemu/{vmid}/config``: disk -> storage mapping and size."""
        result: dict[str, Any] = self._call(
            f"fetching config for VM {vmid} on {node}",
            lambda: self._api.nodes(node).qemu(vmid).config.get(),
        )
        return result

    def storage_status(self, node: str, storage: str) -> dict[str, Any]:
        """``GET /nodes/{node}/storage/{storage}/status``: authoritative total/used/avail."""
        result: dict[str, Any] = self._call(
            f"fetching status of storage {storage!r} on {node}",
            lambda: self._api.nodes(node).storage(storage).status.get(),
        )
        return result

    def storage_content(self, node: str, storage: str) -> list[dict[str, Any]]:
        """``GET /nodes/{node}/storage/{storage}/content``: per-volume real sizes and owners."""
        result: list[dict[str, Any]] = self._call(
            f"fetching content of storage {storage!r} on {node}",
            lambda: self._api.nodes(node).storage(storage).content.get(),
        )
        return result

    def vm_snapshots(self, node: str, vmid: int) -> list[dict[str, Any]]:
        """``GET /nodes/{node}/qemu/{vmid}/snapshot``: snapshot/volume chains (section 3.7)."""
        result: list[dict[str, Any]] = self._call(
            f"fetching snapshots for VM {vmid} on {node}",
            lambda: self._api.nodes(node).qemu(vmid).snapshot.get(),
        )
        return result

    def vm_status_current(self, node: str, vmid: int) -> dict[str, Any]:
        """``GET .../status/current``: ``lock`` immediately before a move (section 9.3)."""
        result: dict[str, Any] = self._call(
            f"fetching current status for VM {vmid} on {node}",
            lambda: self._api.nodes(node).qemu(vmid).status.current.get(),
        )
        return result

    # ----------------------------------------------------------- write path

    def move_disk(
        self,
        node: str,
        vmid: int,
        disk: str,
        storage: str,
        *,
        delete: bool = True,
        bwlimit_bytes_per_sec: int | None = None,
        format: str | None = None,  # matches the PVE API's own parameter name
    ) -> str:
        """``POST /nodes/{node}/qemu/{vmid}/move_disk``. Returns the UPID.

        ``delete`` defaults ``True`` throughout this project (section 3.5):
        without it the old volume is left behind and the reserve arithmetic
        silently drifts. ``bwlimit_bytes_per_sec`` is converted to the API's
        native KiB/s **here and nowhere else** (section 9.2: "convert at the
        call site and nowhere else") -- every caller in this codebase works
        in bytes/s, matching ``migration.bwlimit_bytes_per_sec``. ``format``
        must stay ``None`` unless an operator has explicitly opted into
        format conversion (section 3.5): passing it changes the volume's
        on-disk format, which is a storage-policy decision, never one this
        tool makes silently.
        """
        params: dict[str, Any] = {"disk": disk, "storage": storage, "delete": 1 if delete else 0}
        if bwlimit_bytes_per_sec is not None:
            params["bwlimit"] = round(bwlimit_bytes_per_sec / 1024.0)
        if format is not None:
            params["format"] = format
        result: str = self._call(
            f"moving {vmid}:{disk} to {storage!r}",
            lambda: self._api.nodes(node).qemu(vmid).move_disk.post(**params),
        )
        return result

    def task_status(self, node: str, upid: str) -> dict[str, Any]:
        """``GET /nodes/{node}/tasks/{upid}/status``: ``status``/``exitstatus`` of a move."""
        result: dict[str, Any] = self._call(
            f"fetching task status for {upid}",
            lambda: self._api.nodes(node).tasks(upid).status.get(),
        )
        return result
