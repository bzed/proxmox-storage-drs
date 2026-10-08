# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""PveClient and build_client(). See proxmox_storage_drs/pve.py.

No test here talks to a real Proxmox VE API (.agents/testing.md); see
tests/unit/fakes.py for FakeProxmoxResource, shared with test_topology.py.
"""

from __future__ import annotations

from typing import Any, Callable

import pytest
import requests
from proxmoxer import AuthenticationError, ResourceException

from proxmox_storage_drs.config import AuthConfig, ProxmoxConfig
from proxmox_storage_drs.exceptions import PveApiError
from proxmox_storage_drs.pve import PveClient, build_client
from tests.unit.fakes import fake_api

# --------------------------------------------------------------------- read path


def test_vm_resources() -> None:
    api = fake_api({"cluster/resources": [{"vmid": 101}]})
    client = PveClient(api)
    assert client.vm_resources() == [{"vmid": 101}]
    assert api.calls == [("GET", "cluster/resources", {"type": "vm"})]


def test_cluster_tasks() -> None:
    api = fake_api({"cluster/tasks": [{"upid": "UPID:pve01:...:qmconfig:104:root@pam:"}]})
    client = PveClient(api)
    assert client.cluster_tasks() == [{"upid": "UPID:pve01:...:qmconfig:104:root@pam:"}]
    assert api.calls == [("GET", "cluster/tasks", {})]


def test_storage_resources() -> None:
    api = fake_api({"cluster/resources": [{"storage": "san-a"}]})
    client = PveClient(api)
    assert client.storage_resources() == [{"storage": "san-a"}]
    assert api.calls == [("GET", "cluster/resources", {"type": "storage"})]


def test_version() -> None:
    api = fake_api({"version": {"version": "8.2.1", "release": "8.2"}})
    client = PveClient(api)
    assert client.version() == "8.2.1"
    assert api.calls == [("GET", "version", {})]


def test_version_missing_key_is_none() -> None:
    api = fake_api({"version": {"release": "8.2"}})
    client = PveClient(api)
    assert client.version() is None


def test_storage_definitions() -> None:
    api = fake_api({"storage": [{"storage": "san-a", "type": "lvm", "saferemove": 1}]})
    client = PveClient(api)
    assert client.storage_definitions() == [{"storage": "san-a", "type": "lvm", "saferemove": 1}]
    # The list form, not one call per storage -- see the method's docstring.
    assert api.calls == [("GET", "storage", {})]


def test_node_names() -> None:
    api = fake_api({"nodes": [{"node": "pve02"}, {"node": "pve01"}]})
    client = PveClient(api)
    # Sorted, not returned-order -- section 3.4's node selector builds a
    # deterministic query string from this, not one that reorders itself
    # depending on the API's own (unspecified) listing order.
    assert client.node_names() == ["pve01", "pve02"]
    assert api.calls == [("GET", "nodes", {})]


def test_node_names_dedupes_and_skips_a_missing_field() -> None:
    api = fake_api({"nodes": [{"node": "pve01"}, {"node": "pve01"}, {"status": "online"}]})
    client = PveClient(api)
    assert client.node_names() == ["pve01"]


def test_vm_config() -> None:
    api = fake_api({"nodes/pve01/qemu/101/config": {"scsi0": "san-a:vm-101-disk-0,size=32G"}})
    client = PveClient(api)
    cfg = client.vm_config("pve01", 101)
    assert cfg["scsi0"].startswith("san-a:")


def test_storage_status() -> None:
    api = fake_api({"nodes/pve01/storage/san-a/status": {"total": 100, "used": 50}})
    client = PveClient(api)
    assert client.storage_status("pve01", "san-a")["total"] == 100


def test_storage_content() -> None:
    api = fake_api({"nodes/pve01/storage/san-a/content": [{"volid": "san-a:vm-101-disk-0"}]})
    client = PveClient(api)
    assert client.storage_content("pve01", "san-a")[0]["volid"] == "san-a:vm-101-disk-0"


def test_vm_snapshots() -> None:
    api = fake_api({"nodes/pve01/qemu/101/snapshot": [{"name": "current"}]})
    client = PveClient(api)
    assert client.vm_snapshots("pve01", 101) == [{"name": "current"}]


def test_vm_pending() -> None:
    api = fake_api(
        {
            "nodes/pve01/qemu/101/pending": [
                {"key": "scsi0", "value": "san-a:vm-101-disk-0,size=32G", "pending": True}
            ]
        }
    )
    client = PveClient(api)
    assert client.vm_pending("pve01", 101)[0]["key"] == "scsi0"


def test_vm_status_current() -> None:
    api = fake_api({"nodes/pve01/qemu/101/status/current": {"lock": "backup"}})
    client = PveClient(api)
    assert client.vm_status_current("pve01", 101)["lock"] == "backup"


# -------------------------------------------------------------------- write path


def test_move_disk_defaults_delete_true_and_omits_optional_params() -> None:
    api = fake_api({"nodes/pve01/qemu/101/move_disk": "UPID:pve01:...:qmmove:"})
    client = PveClient(api)
    upid = client.move_disk("pve01", 101, "scsi0", "san-c")
    assert upid.startswith("UPID:")
    method, path, params = api.calls[0]
    assert method == "POST"
    assert path == "nodes/pve01/qemu/101/move_disk"
    assert params == {"disk": "scsi0", "storage": "san-c", "delete": 1}


def test_move_disk_delete_false() -> None:
    api = fake_api({"nodes/pve01/qemu/101/move_disk": "UPID:x"})
    client = PveClient(api)
    client.move_disk("pve01", 101, "scsi0", "san-c", delete=False)
    _, _, params = api.calls[0]
    assert params["delete"] == 0


def test_move_disk_converts_bwlimit_bytes_to_kib_at_this_call_site() -> None:
    """Section 9.2: "convert at the call site and nowhere else" -- this is that site."""
    api = fake_api({"nodes/pve01/qemu/101/move_disk": "UPID:x"})
    client = PveClient(api)
    client.move_disk("pve01", 101, "scsi0", "san-c", bwlimit_bytes_per_sec=209_715_200)
    _, _, params = api.calls[0]
    assert params["bwlimit"] == 204800  # 200 MiB/s -> 204800 KiB/s


def test_move_disk_format_is_omitted_unless_explicitly_given() -> None:
    api = fake_api({"nodes/pve01/qemu/101/move_disk": "UPID:x"})
    client = PveClient(api)
    client.move_disk("pve01", 101, "scsi0", "san-c")
    _, _, params = api.calls[0]
    assert "format" not in params


def test_move_disk_passes_format_when_given() -> None:
    api = fake_api({"nodes/pve01/qemu/101/move_disk": "UPID:x"})
    client = PveClient(api)
    client.move_disk("pve01", 101, "scsi0", "san-c", format="qcow2")
    _, _, params = api.calls[0]
    assert params["format"] == "qcow2"


def test_task_status() -> None:
    api = fake_api({"nodes/pve01/tasks/UPID:x/status": {"status": "stopped", "exitstatus": "OK"}})
    client = PveClient(api)
    status = client.task_status("pve01", "UPID:x")
    assert status["exitstatus"] == "OK"


# -------------------------------------------------------------------- error wrapping


def test_resource_exception_is_wrapped() -> None:
    api = fake_api({}, error=ResourceException(404, "Not Found", "no such VM"))
    client = PveClient(api)
    with pytest.raises(PveApiError, match="404"):
        client.vm_resources()


def test_authentication_error_is_wrapped() -> None:
    api = fake_api({}, error=AuthenticationError("bad ticket"))
    client = PveClient(api)
    with pytest.raises(PveApiError, match="bad ticket"):
        client.vm_resources()


def test_request_exception_is_wrapped() -> None:
    import requests

    api = fake_api({}, error=requests.ConnectionError("refused"))
    client = PveClient(api)
    with pytest.raises(PveApiError, match="request failed"):
        client.vm_resources()


# --------------------------------- REVIEW.md P-01: reauthenticate-and-retry-once


def test_reauthenticates_and_retries_once_on_authentication_error() -> None:
    """A ticket that expired for reasons external to this call (a long
    confirm-mode wait, a suspended process) gets one fresh login and one
    retry, transparently -- the caller never sees the first failure."""
    stale = fake_api({}, error=AuthenticationError("ticket expired"))
    fresh = fake_api({"cluster/resources": [{"vmid": 101}]})
    client = PveClient(stale, reauthenticate=lambda: fresh)
    assert client.vm_resources() == [{"vmid": 101}]
    assert client._api is fresh  # the client adopted the new session


def test_reports_clearly_when_reauthentication_itself_fails() -> None:
    def reauth() -> None:
        raise AuthenticationError("still bad credentials")

    stale = fake_api({}, error=AuthenticationError("ticket expired"))
    client = PveClient(stale, reauthenticate=reauth)
    with pytest.raises(PveApiError, match="re-authenticating failed too"):
        client.vm_resources()


def test_reports_clearly_when_the_retry_after_reauthentication_still_fails() -> None:
    """A successful re-login does not guarantee the retried call succeeds --
    e.g. the token was genuinely revoked, not merely stale."""
    stale = fake_api({}, error=AuthenticationError("ticket expired"))
    still_broken = fake_api({}, error=ResourceException(403, "Forbidden", "no access"))
    client = PveClient(stale, reauthenticate=lambda: still_broken)
    with pytest.raises(PveApiError, match="still failed after re-authenticating"):
        client.vm_resources()


def test_reports_transport_failure_after_reauthentication() -> None:
    import requests

    stale = fake_api({}, error=AuthenticationError("ticket expired"))
    unreachable = fake_api({}, error=requests.ConnectionError("refused"))
    client = PveClient(stale, reauthenticate=lambda: unreachable)
    client._sleep = lambda seconds: None
    with pytest.raises(PveApiError, match="request failed") as info:
        client.vm_resources()
    assert info.value.transient


def test_no_reauthenticate_callback_means_no_retry() -> None:
    """The default (and what every other test double in this suite uses):
    a bare ``PveClient(fake_api)`` behaves exactly as it did before P-01."""
    api = fake_api({}, error=AuthenticationError("bad ticket"))
    client = PveClient(api)
    assert client._reauthenticate is None
    with pytest.raises(PveApiError, match="bad ticket"):
        client.vm_resources()
    assert len(api.calls) == 1  # no retry attempted


# --------------------------------------------------------------------- build_client


def _config(**auth_kwargs: object) -> ProxmoxConfig:
    return ProxmoxConfig(
        host="pve.example.com",
        port=8006,
        verify_ssl=True,
        auth=AuthConfig(**auth_kwargs),  # type: ignore[arg-type]
    )


def test_build_client_uses_token_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_proxmox_api(**kwargs: Any) -> str:
        captured.update(kwargs)
        return "the-api-object"

    monkeypatch.setattr("proxmox_storage_drs.pve.ProxmoxAPI", fake_proxmox_api)
    config = _config(token_id="drs@pve!balancer", token_secret="s3cret")
    client = build_client(config)
    assert client._api == "the-api-object"
    assert captured["user"] == "drs@pve"
    assert captured["token_name"] == "balancer"
    assert captured["token_value"] == "s3cret"
    assert captured["host"] == "pve.example.com"


def test_build_client_uses_password_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        "proxmox_storage_drs.pve.ProxmoxAPI",
        lambda **kwargs: captured.update(kwargs) or "api",
    )
    config = _config(username="drs@pve", password="hunter2")
    build_client(config)
    assert captured["user"] == "drs@pve"
    assert captured["password"] == "hunter2"
    assert "token_name" not in captured


def test_build_client_ca_file_overrides_verify_ssl(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        "proxmox_storage_drs.pve.ProxmoxAPI",
        lambda **kwargs: captured.update(kwargs) or "api",
    )
    config = ProxmoxConfig(
        host="pve.example.com",
        verify_ssl=True,
        ca_file="/etc/ssl/certs/mycorp-ca.pem",
        auth=AuthConfig(token_id="drs@pve!balancer", token_secret="s3cret"),
    )
    build_client(config)
    assert captured["verify_ssl"] == "/etc/ssl/certs/mycorp-ca.pem"


def test_build_client_no_credentials_raises() -> None:
    config = _config()
    with pytest.raises(PveApiError, match="needs either"):
        build_client(config)


def test_build_client_malformed_token_id_raises() -> None:
    config = _config(token_id="not-in-the-right-form", token_secret="x")
    with pytest.raises(PveApiError, match="user@realm!tokenname"):
        build_client(config)


def test_build_client_wraps_authentication_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_auth_error(**kwargs: Any) -> None:
        raise AuthenticationError("nope")

    monkeypatch.setattr("proxmox_storage_drs.pve.ProxmoxAPI", raise_auth_error)
    config = _config(username="drs@pve", password="wrong")
    with pytest.raises(PveApiError, match="nope"):
        build_client(config)


# ------------------------------- REVIEW.md P-01: ticket_refresh_seconds wiring


class _FakeTicketAuth:
    renew_age = 3600  # proxmoxer's own hard-coded default


class _FakeHttpsBackend:
    def __init__(self) -> None:
        self.auth = _FakeTicketAuth()


class _FakeProxmoxApiWithBackend:
    def __init__(self) -> None:
        self._backend = _FakeHttpsBackend()


def test_build_client_applies_ticket_refresh_seconds_to_password_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeProxmoxApiWithBackend()
    monkeypatch.setattr("proxmox_storage_drs.pve.ProxmoxAPI", lambda **kwargs: fake)
    config = ProxmoxConfig(
        host="pve.example.com",
        verify_ssl=True,
        ticket_refresh_seconds=120.0,
        auth=AuthConfig(username="drs@pve", password="hunter2"),
    )
    build_client(config)
    assert fake._backend.auth.renew_age == 120.0


def test_apply_ticket_refresh_seconds_is_a_silent_no_op_without_a_backend() -> None:
    """Token auth, a non-https backend, or a future proxmoxer shape this
    can't reach must never crash -- see the function's own docstring."""
    from proxmox_storage_drs.pve import _apply_ticket_refresh_seconds

    config = _config(token_id="drs@pve!balancer", token_secret="s3cret")
    _apply_ticket_refresh_seconds("just-a-string", config)  # must not raise
    _apply_ticket_refresh_seconds(object(), config)  # must not raise


# ----------------------- connection pool sized to config.proxmox.read_workers


class _FakeSession:
    def __init__(self) -> None:
        self.mounted: dict[str, Any] = {}

    def mount(self, prefix: str, adapter: Any) -> None:
        self.mounted[prefix] = adapter


class _FakeProxmoxApiWithSession:
    def __init__(self, session: Any) -> None:
        self._store = {"session": session}


def test_apply_connection_pool_size_mounts_an_adapter_sized_to_read_workers() -> None:
    """Confirmed live against a real multi-VM cluster: `requests`'s own
    default `HTTPAdapter` pool (`pool_maxsize=10`) is smaller than
    `read_workers`'s own default (`12`), so `topology.py`'s concurrent
    fetch reliably logged urllib3's "Connection pool is full, discarding
    connection" warning until this was sized to match."""
    from proxmox_storage_drs.pve import _apply_connection_pool_size

    session = _FakeSession()
    fake = _FakeProxmoxApiWithSession(session)
    _apply_connection_pool_size(fake, read_workers=12)
    assert set(session.mounted) == {"https://", "http://"}
    for adapter in session.mounted.values():
        assert adapter._pool_maxsize == 12
        assert adapter._pool_connections == 12


def test_apply_connection_pool_size_never_shrinks_below_the_requests_default() -> None:
    """A small `read_workers` (or the field's own minimum) must not shrink
    the pool below `requests`'s own default of 10 -- there is no reason a
    smaller worker count should make single-threaded reads (`plan`'s own
    non-concurrent calls, say) worse than they already were."""
    from proxmox_storage_drs.pve import _apply_connection_pool_size

    session = _FakeSession()
    fake = _FakeProxmoxApiWithSession(session)
    _apply_connection_pool_size(fake, read_workers=1)
    assert session.mounted["https://"]._pool_maxsize == 10


def test_apply_connection_pool_size_is_a_silent_no_op_without_a_session() -> None:
    """A plain string, an object with no ``_store``, or a session-shaped
    object with no ``mount`` method must never crash -- mirrors
    `_apply_ticket_refresh_seconds()`'s own defensive contract."""
    from proxmox_storage_drs.pve import _apply_connection_pool_size

    _apply_connection_pool_size("just-a-string", read_workers=12)  # must not raise
    _apply_connection_pool_size(object(), read_workers=12)  # must not raise

    class _NoMountSession:
        pass

    class _ApiWithUnmountableSession:
        _store = {"session": _NoMountSession()}

    _apply_connection_pool_size(_ApiWithUnmountableSession(), read_workers=12)  # must not raise


def test_build_client_sizes_the_connection_pool_for_token_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    fake = _FakeProxmoxApiWithSession(session)
    monkeypatch.setattr("proxmox_storage_drs.pve.ProxmoxAPI", lambda **kwargs: fake)
    config = _config(token_id="drs@pve!balancer", token_secret="s3cret")
    build_client(config)
    assert session.mounted["https://"]._pool_maxsize == config.read_workers


def test_build_client_reauthenticate_callback_rebuilds_a_fresh_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []

    def fake_proxmox_api(**kwargs: Any) -> object:
        calls.append(kwargs)
        return object()

    monkeypatch.setattr("proxmox_storage_drs.pve.ProxmoxAPI", fake_proxmox_api)
    config = _config(token_id="drs@pve!balancer", token_secret="s3cret")
    client = build_client(config)
    assert len(calls) == 1
    assert client._reauthenticate is not None
    second_api = client._reauthenticate()
    assert len(calls) == 2
    assert second_api is not client._api  # a genuinely new object, not the same one


def _flaky(failures: int, exc: Exception) -> tuple[Callable[[], str], dict[str, int]]:
    calls = {"n": 0}

    def action() -> str:
        calls["n"] += 1
        if calls["n"] <= failures:
            raise exc
        return "ok"

    return action, calls


def _client_with_fake_time(
    reauthenticate: Callable[[], Any] | None = None,
) -> tuple[PveClient, list[float]]:
    client = PveClient(object(), reauthenticate=reauthenticate)
    client._random = lambda: 0.5  # jitter factor exactly 1.0
    slept: list[float] = []
    now = {"t": 0.0}

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        now["t"] += seconds

    client._sleep = sleep
    client._monotonic = lambda: now["t"]
    return client, slept


def test_unreachable_api_is_retried_inside_outage_tolerance() -> None:
    client, slept = _client_with_fake_time()
    action, calls = _flaky(3, requests.ConnectionError("down"))
    with client.outage_tolerance(600):
        assert client._call("x", action) == "ok"
    assert calls["n"] == 4 and slept == [5.0, 10.0, 20.0]


def test_outage_longer_than_tolerance_raises_a_transient_error() -> None:
    client, slept = _client_with_fake_time()
    action, _ = _flaky(10_000, requests.Timeout("slow"))
    with client.outage_tolerance(30):
        with pytest.raises(PveApiError) as info:
            client._call("x", action)
    assert info.value.transient and sum(slept) == 30


def test_non_transient_errors_and_non_idempotent_calls_are_never_retried() -> None:
    client, slept = _client_with_fake_time()
    for tolerance in (0, 600):
        with client.outage_tolerance(tolerance):
            with pytest.raises(PveApiError):
                client._call("x", _flaky(1, ResourceException(403, "no", ""))[0])
            with pytest.raises(PveApiError):
                client._call("x", _flaky(1, requests.ConnectionError("down"))[0], idempotent=False)
    assert slept == []


def test_short_retry_rides_out_a_blip_without_outage_tolerance() -> None:
    client, slept = _client_with_fake_time()
    action, calls = _flaky(3, requests.exceptions.SSLError("handshake failure"))
    assert client._call("x", action) == "ok"
    assert calls["n"] == 4 and slept == [1.0, 2.0, 4.0]


def test_short_retry_gives_up_and_reports_a_transient_error() -> None:
    client, slept = _client_with_fake_time()
    action, calls = _flaky(10, requests.ConnectionError("down"))
    with pytest.raises(PveApiError) as info:
        client._call("x", action)
    assert info.value.transient and calls["n"] == 4 and len(slept) == 3


def test_short_retry_delays_are_jittered() -> None:
    client, slept = _client_with_fake_time()
    client._random = lambda: 1.0  # upper bound: factor 1.5
    client._call("x", _flaky(1, requests.ConnectionError("down"))[0])
    assert slept == [1.5]


@pytest.mark.parametrize(
    "exc",
    [
        requests.exceptions.ChunkedEncodingError("truncated"),
        requests.exceptions.SSLError("tls"),
        requests.exceptions.ConnectionError("reset"),
        ValueError("Expecting value: line 1 column 1 (char 0)"),  # an HTML page, not JSON
        ResourceException(429, "Too Many Requests", ""),
        ResourceException(502, "Bad Gateway", ""),
        AuthenticationError("Couldn't authenticate user: u to https://h/access/ticket code: 502"),
    ],
)
def test_flaky_network_failures_are_transient_and_retried(exc: Exception) -> None:
    client, _ = _client_with_fake_time()
    assert client._call("x", _flaky(1, exc)[0]) == "ok"


@pytest.mark.parametrize(
    "exc",
    [
        requests.exceptions.InvalidURL("bad"),
        requests.exceptions.MissingSchema("bad"),
        ResourceException(400, "Bad Request", ""),
        ResourceException(401, "Unauthorized", ""),
        ResourceException(403, "Forbidden", ""),
        ResourceException(404, "Not Found", ""),
        AuthenticationError("Couldn't authenticate user: u to https://h/access/ticket code: 401"),
        AuthenticationError("Couldn't authenticate user: u to https://h/access/ticket code: 403"),
    ],
)
def test_authorization_and_malformed_requests_are_hard_errors(exc: Exception) -> None:
    client, slept = _client_with_fake_time()
    action, calls = _flaky(1, exc)
    with pytest.raises(PveApiError) as info:
        client._call("x", action)
    assert not info.value.transient and calls["n"] == 1 and slept == []


def test_not_authorized_login_is_not_retried_after_reauthenticating_either() -> None:
    bad = "Couldn't authenticate user: u to https://h/access/ticket code: 401"
    api = fake_api({}, error=AuthenticationError(bad))
    logins: list[int] = []

    def reauth() -> Any:
        logins.append(1)
        raise AuthenticationError(bad)

    client, slept = _client_with_fake_time(reauth)
    client._api = api
    with pytest.raises(PveApiError) as info:
        client.vm_resources()
    assert not info.value.transient and len(logins) == 1 and slept == []


def test_transport_failure_rebuilds_the_session_before_retrying() -> None:
    broken = fake_api({}, error=requests.exceptions.SSLError("handshake"))
    fresh = fake_api({"cluster/resources": [{"vmid": 7}]})
    client, _ = _client_with_fake_time(lambda: fresh)
    client._api = broken
    assert client.vm_resources() == [{"vmid": 7}]
    assert client._api is fresh


def test_failed_session_rebuild_does_not_mask_the_retry() -> None:
    def reauth() -> Any:
        raise requests.ConnectionError("still down")

    client, _ = _client_with_fake_time(reauth)
    assert client._call("x", _flaky(1, requests.ConnectionError("down"))[0]) == "ok"


def test_server_errors_do_not_rebuild_the_session() -> None:
    rebuilt: list[int] = []
    client, _ = _client_with_fake_time(lambda: rebuilt.append(1))
    client._call("x", _flaky(1, ResourceException(503, "unavailable", ""))[0])
    assert rebuilt == []


def test_5xx_is_transient_and_tolerance_is_restored() -> None:
    client, _ = _client_with_fake_time()
    action, _ = _flaky(1, ResourceException(595, "no route to host", ""))
    with client.outage_tolerance(600):
        assert client._call("x", action) == "ok"
    assert client._outage_tolerance == 0.0
