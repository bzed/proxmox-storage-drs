# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""PveClient and build_client(). See proxmox_storage_drs/pve.py.

No test here talks to a real Proxmox VE API (.agents/testing.md); see
tests/unit/fakes.py for FakeProxmoxResource, shared with test_topology.py.
"""

from __future__ import annotations

from typing import Any

import pytest
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


def test_storage_definitions() -> None:
    api = fake_api({"storage": [{"storage": "san-a", "type": "lvm", "saferemove": 1}]})
    client = PveClient(api)
    assert client.storage_definitions() == [{"storage": "san-a", "type": "lvm", "saferemove": 1}]
    # The list form, not one call per storage -- see the method's docstring.
    assert api.calls == [("GET", "storage", {})]


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
    with pytest.raises(PveApiError, match="request failed after re-authenticating"):
        client.vm_resources()


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
