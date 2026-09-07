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
logic beyond the one reauthenticate-and-retry-once step described on
:meth:`PveClient._call` (REVIEW.md P-01) -- the per-run topology cache
belongs to ``topology.py`` (section 3.5: "a per-run topology cache -- one
snapshot at the start of the run").
"""

from __future__ import annotations

import threading
from typing import Any, Callable

import requests
from proxmoxer import AuthenticationError, ProxmoxAPI, ResourceException

from proxmox_storage_drs.config import ProxmoxConfig
from proxmox_storage_drs.exceptions import PveApiError

# proxmoxer's own https-backend default (5s) is tuned for an interactive CLI
# rather than a bounded thread pool fetching hundreds of VM configs; 10s is a
# "short" per-request timeout in the sense section 3.5 means (as opposed to
# unbounded). topology.py's concurrent fetch (config.proxmox.read_workers
# threads, REVIEW.md P-02) shares this one client and its one timeout --
# there is no per-thread override yet, since nothing so far has needed one.
_DEFAULT_TIMEOUT_SECONDS = 10.0


def _build_api(config: ProxmoxConfig) -> Any:
    """Construct one fresh, logged-in ``proxmoxer.ProxmoxAPI``.

    Split out of :func:`build_client` so it can also serve as the
    reauthenticate callback :class:`PveClient` uses when a ticket that
    ``proxmoxer`` itself thought was still valid gets rejected mid-run
    (section P-01 of REVIEW.md: a long confirm-mode wait, or any other gap
    between calls, can outlast the ticket's server-side lifetime even
    though ``proxmoxer``'s own lazy renewal never noticed). Raises
    ``AuthenticationError``/``requests.RequestException`` uncaught -- both
    callers wrap them into :class:`PveApiError` themselves, with a message
    appropriate to which situation they are in.
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

    api = ProxmoxAPI(**kwargs)
    _apply_ticket_refresh_seconds(api, config)
    _apply_connection_pool_size(api, config.read_workers)
    return api


def _apply_connection_pool_size(api: Any, read_workers: int) -> None:
    """Size the underlying ``requests`` session's connection pool to fit
    ``config.proxmox.read_workers`` (REVIEW.md P-02's concurrent fetch),
    confirmed live against a real cluster: ``requests``'s own default
    ``HTTPAdapter`` pool (``pool_maxsize=10``, sized for a single
    interactive client, not a worker pool) is smaller than the default
    ``read_workers=12``, so ``topology.py``'s per-run fetch reliably logs
    urllib3's own "Connection pool is full, discarding connection" warning
    on every real multi-VM cluster -- and each discarded connection pays a
    fresh TCP+TLS handshake instead of reusing one, not just log noise.

    Reaches into ``proxmoxer``'s internal ``_store["session"]`` the same
    documented, best-effort way :func:`_apply_ticket_refresh_seconds`
    reaches ``_backend.auth`` -- no supported, public way to size this
    through ``ProxmoxAPI(...)``'s own constructor, so this mounts a
    larger-pooled ``HTTPAdapter`` onto the already-built session
    afterwards. Silently a no-op if this shape doesn't match (a future
    ``proxmoxer`` version, or a non-``https`` backend whose session isn't
    a plain ``requests.Session``) -- this only ever removes a warning and
    recovers some connection reuse, never something correctness depends
    on."""
    session = getattr(api, "_store", {}).get("session")
    if session is None or not hasattr(session, "mount"):
        return
    pool_size = max(read_workers, 10)
    adapter = requests.adapters.HTTPAdapter(pool_connections=pool_size, pool_maxsize=pool_size)
    session.mount("https://", adapter)
    session.mount("http://", adapter)


def _apply_ticket_refresh_seconds(api: Any, config: ProxmoxConfig) -> None:
    """REVIEW.md P-01: wire ``proxmox.ticket_refresh_seconds`` through, best-effort.

    Password/ticket auth's ``proxmoxer`` backend refreshes its ticket
    lazily -- on whichever request happens to run once its ``renew_age``
    (a hard-coded 3600s *class* attribute, not a ``ProxmoxAPI(...)`` keyword
    argument) has elapsed since login. There is no supported, public way to
    pass ``ticket_refresh_seconds`` through ``ProxmoxAPI``'s constructor in
    ``proxmoxer`` 2.x, so this reaches into ``_backend.auth`` -- internal,
    undocumented attribute access, not part of ``proxmoxer``'s public API --
    to override that instance's ``renew_age`` after construction. This is a
    deliberate, narrow exception to this module's own "no hand-rolled ticket
    client" rationale: it is strictly additive to what ``proxmoxer`` already
    does, never a replacement for it.

    API-token auth has no ticket to refresh at all (``auth`` is a
    ``ProxmoxHTTPApiTokenAuth`` with no ``renew_age``), and any shape this
    can't reach -- a non-``https`` backend, or a future ``proxmoxer`` version
    that restructures this -- is a silent no-op, never a crash: worst case,
    the knob stays a no-op and :meth:`PveClient._call`'s
    reauthenticate-and-retry-once still catches a ticket that expired
    despite it.
    """
    auth = getattr(getattr(api, "_backend", None), "auth", None)
    if auth is not None and hasattr(auth, "renew_age"):
        auth.renew_age = config.ticket_refresh_seconds


def build_client(config: ProxmoxConfig) -> "PveClient":
    """Construct a :class:`PveClient` from ``config.py``'s ``ProxmoxConfig``.

    Always the ``https`` ``proxmoxer`` backend today; see this module's
    docstring for why switching to an SSH backend later needs no change
    beyond this function. The returned client can rebuild its own session
    from scratch exactly once per failed call (see
    :meth:`PveClient._call`) by calling back into :func:`_build_api` with
    this same ``config`` -- a full fresh login, not a reuse of the ticket
    that just got rejected.
    """
    try:
        api = _build_api(config)
    except (AuthenticationError, requests.RequestException) as exc:
        raise PveApiError(f"could not authenticate to the Proxmox VE API: {exc}") from exc
    return PveClient(api, reauthenticate=lambda: _build_api(config))


class PveClient:
    """One method per IMPLEMENTATION_PLAN.md section 3.5 endpoint.

    ``api`` is typed ``Any`` because ``proxmoxer.ProxmoxAPI`` resolves every
    attribute and call dynamically (no static shape to describe) and ships
    no type stubs; tests inject a small fake replicating that same
    attribute-chaining protocol rather than the real network-capable object
    (.agents/testing.md).
    """

    def __init__(self, api: Any, *, reauthenticate: Callable[[], Any] | None = None) -> None:
        self._api = api
        # REVIEW.md P-01: how to get a completely fresh, logged-in ``api``
        # object when a ticket ``proxmoxer`` itself thought was still valid
        # gets rejected mid-run -- e.g. a long confirm-mode wait, or any
        # other gap between calls, outlasting the ticket's actual
        # server-side lifetime. ``None`` (the default, and what every test
        # double uses) means "no recovery is possible" -- a bare
        # ``PveClient(fake_api)`` behaves exactly as before this was added.
        self._reauthenticate = reauthenticate
        # Guards `_reauthenticate` itself, not the retried call: if several
        # of topology.py's `read_workers` threads hit an expired ticket at
        # the same moment, this serializes them onto one fresh login instead
        # of a stampede of concurrent ones. It does not *deduplicate* that
        # work (a thread that queues behind the lock still re-authenticates
        # once released, even though the ticket is fresh by then) -- a
        # correctness-preserving, if not maximally efficient, simplification
        # given re-authentication is expected to be rare.
        self._reauth_lock = threading.Lock()

    def _call(self, description: str, action: Any) -> Any:
        """Run one ``proxmoxer`` call, wrapping every failure as :class:`PveApiError`.

        ``ResourceException`` covers HTTP-level API errors (4xx/5xx);
        ``requests.RequestException`` covers transport failures (connection
        refused, timeout) that ``proxmoxer``'s https backend does not wrap
        itself. ``AuthenticationError`` gets one extra chance (P-01): rebuild
        the session from scratch via ``reauthenticate`` and retry ``action``
        exactly once before giving up -- covers a ticket that expired for a
        reason external to any single call (the operator took a long time to
        confirm a plan, the process was suspended, the clock jumped), not
        just a call that was doomed from the start. ``action`` always reads
        the API object through ``self._api`` (never a captured local), so
        reassigning it here is enough for the retried ``action()`` to use
        the new session with no other change.
        """
        try:
            return action()
        except AuthenticationError as exc:
            if self._reauthenticate is None:
                raise PveApiError(f"{description}: {exc}") from exc
            with self._reauth_lock:
                try:
                    self._api = self._reauthenticate()
                except (AuthenticationError, requests.RequestException) as reauth_exc:
                    raise PveApiError(
                        f"{description}: authentication ticket was rejected and "
                        f"re-authenticating failed too: {reauth_exc}"
                    ) from reauth_exc
            try:
                return action()
            except (ResourceException, AuthenticationError) as retry_exc:
                raise PveApiError(
                    f"{description}: still failed after re-authenticating: {retry_exc}"
                ) from retry_exc
            except requests.RequestException as retry_exc:
                raise PveApiError(
                    f"{description}: request failed after re-authenticating: {retry_exc}"
                ) from retry_exc
        except ResourceException as exc:
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

    def cluster_tasks(self) -> list[dict[str, Any]]:
        """``GET /cluster/tasks``: recent/active tasks across **every**
        node -- the one read that actually crosses the cluster (section
        13's startup scan for an in-flight `move_disk`; `state.json`'s own
        `fcntl.flock()` cannot see another node at all). Confirmed live
        against a real cluster: each entry carries `node`/`type`/`id`
        (the vmid, for a VM-scoped task type)/`upid`/`user`/`starttime`,
        plus `endtime`/`status` -- both present once the task has
        finished, both absent while it is still running (`status` is
        `"OK"` or an error string there, not the `"running"` value the
        per-task `task_status()` endpoint below uses)."""
        result: list[dict[str, Any]] = self._call(
            "fetching cluster-wide task list", lambda: self._api.cluster.tasks.get()
        )
        return result

    def storage_resources(self) -> list[dict[str, Any]]:
        """``GET /cluster/resources?type=storage``: storage inventory."""
        result: list[dict[str, Any]] = self._call(
            "fetching storage inventory", lambda: self._api.cluster.resources.get(type="storage")
        )
        return result

    def node_names(self) -> list[str]:
        """``GET /nodes``: every node in the cluster, by name.

        Section 3.4's node-scoping filter (`metrics.build_node_selector()`)
        is built from this, not from the ``node`` fields already visible on
        `vm_resources()`/`storage_resources()`: an idle node currently
        hosting no VM (or no shared storage) would silently be missing from
        either of those, and dropping a real cluster node out of the
        filter is exactly the kind of quiet under-count section 3.4 exists
        to avoid -- a query scoped to fewer nodes than the cluster actually
        has would treat a VM that migrated onto the missing one as if it
        had less history than it really does.
        """
        result: list[dict[str, Any]] = self._call(
            "fetching cluster node list", lambda: self._api.nodes.get()
        )
        return sorted({str(n["node"]) for n in result if n.get("node")})

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
