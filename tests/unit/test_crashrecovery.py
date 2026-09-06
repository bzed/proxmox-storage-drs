# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Startup crash/two-instance recovery. See proxmox_storage_drs/crashrecovery.py."""

from __future__ import annotations

from proxmox_storage_drs.config import AuthConfig
from proxmox_storage_drs.crashrecovery import (
    UpidInfo,
    expected_task_user,
    parse_upid,
    reconcile_inflight,
)
from proxmox_storage_drs.exceptions import PveApiError
from proxmox_storage_drs.pve import PveClient
from proxmox_storage_drs.state import State
from tests.unit.fakes import fake_api

# A real UPID's exact shape, confirmed against a live cluster (see the
# dev-cluster-access notes): UPID:{node}:{pid}:{pstart}:{starttime}:
# {type}:{id}:{user}:
QMMOVE_UPID = "UPID:pve01:00001234:00ABCDEF:6A9D55C2:qmmove:101:drs@pve:"
QMMOVE_UPID_2 = "UPID:pve02:00005678:00ABCDEE:6A9D55C3:qmmove:102:drs@pve:"


# --------------------------------------------------------------- expected_task_user


def test_expected_task_user_prefers_the_token_id() -> None:
    auth = AuthConfig(username="drs@pve", token_id="drs@pve!auto", token_secret="x")
    assert expected_task_user(auth) == "drs@pve!auto"


def test_expected_task_user_falls_back_to_username() -> None:
    auth = AuthConfig(username="drs@pve", password="x")
    assert expected_task_user(auth) == "drs@pve"


def test_expected_task_user_is_none_with_neither_configured() -> None:
    assert expected_task_user(AuthConfig()) is None


# --------------------------------------------------------------------- parse_upid


def test_parse_upid_extracts_node_type_vmid_user() -> None:
    assert parse_upid(QMMOVE_UPID) == UpidInfo(
        node="pve01", task_type="qmmove", vmid=101, user="drs@pve"
    )


def test_parse_upid_empty_id_field_is_no_vmid() -> None:
    # vzdump's own id field is empty, confirmed live.
    info = parse_upid("UPID:pve01:00001234:00ABCDEF:6A9D55C2:vzdump::root@pam:")
    assert info is not None
    assert info.vmid is None


def test_parse_upid_rejects_garbage() -> None:
    assert parse_upid("not a upid") is None
    assert parse_upid("UPID:too:few:fields") is None


# ----------------------------------------------------------------- reconcile_inflight

AUTH = AuthConfig(username="drs@pve", token_id="drs@pve!auto", token_secret="x")


def test_reconcile_drops_a_recorded_upid_whose_task_has_finished() -> None:
    api = fake_api(
        {
            f"nodes/pve01/tasks/{QMMOVE_UPID}/status": {"status": "stopped", "exitstatus": "OK"},
            "cluster/tasks": [],
        }
    )
    client = PveClient(api)
    state = State(inflight_upids=(QMMOVE_UPID,))
    excluded, new_state = reconcile_inflight(client, state, AUTH)
    assert excluded == frozenset()
    assert new_state.inflight_upids == ()


def test_reconcile_keeps_a_recorded_upid_that_is_still_running() -> None:
    api = fake_api(
        {
            f"nodes/pve01/tasks/{QMMOVE_UPID}/status": {"status": "running"},
            "cluster/tasks": [],
        }
    )
    client = PveClient(api)
    state = State(inflight_upids=(QMMOVE_UPID,))
    excluded, new_state = reconcile_inflight(client, state, AUTH)
    assert excluded == frozenset({101})
    assert new_state.inflight_upids == (QMMOVE_UPID,)


def test_reconcile_assumes_still_running_when_the_check_itself_fails() -> None:
    api = fake_api({"cluster/tasks": []}, error=PveApiError("connection refused"))
    client = PveClient(api)
    state = State(inflight_upids=(QMMOVE_UPID,))
    excluded, new_state = reconcile_inflight(client, state, AUTH)
    assert excluded == frozenset({101})
    assert new_state.inflight_upids == (QMMOVE_UPID,)


def test_reconcile_drops_a_malformed_recorded_upid() -> None:
    api = fake_api({"cluster/tasks": []})
    client = PveClient(api)
    state = State(inflight_upids=("not-a-upid",))
    excluded, new_state = reconcile_inflight(client, state, AUTH)
    assert excluded == frozenset()
    assert new_state.inflight_upids == ()


def test_reconcile_finds_a_foreign_inflight_task_from_the_same_user() -> None:
    api = fake_api(
        {
            "cluster/tasks": [
                {
                    "upid": QMMOVE_UPID,
                    "type": "qmmove",
                    "user": "drs@pve!auto",
                    "node": "pve01",
                }
            ],
            f"nodes/pve01/tasks/{QMMOVE_UPID}/status": {"status": "running"},
        }
    )
    client = PveClient(api)
    excluded, new_state = reconcile_inflight(client, State(), AUTH)
    assert excluded == frozenset({101})
    # Not our own recorded UPID -- state.json's own list is untouched.
    assert new_state.inflight_upids == ()


def test_reconcile_ignores_a_foreign_task_already_finished() -> None:
    api = fake_api(
        {
            "cluster/tasks": [
                {
                    "upid": QMMOVE_UPID,
                    "type": "qmmove",
                    "user": "drs@pve!auto",
                    "node": "pve01",
                    "endtime": 123,
                    "status": "OK",
                }
            ],
        }
    )
    client = PveClient(api)
    excluded, _state = reconcile_inflight(client, State(), AUTH)
    assert excluded == frozenset()


def test_reconcile_ignores_a_task_from_a_different_user() -> None:
    api = fake_api(
        {
            "cluster/tasks": [
                {"upid": QMMOVE_UPID, "type": "qmmove", "user": "someone-else@pve", "node": "pve01"}
            ],
        }
    )
    client = PveClient(api)
    excluded, _state = reconcile_inflight(client, State(), AUTH)
    assert excluded == frozenset()


def test_reconcile_ignores_a_non_qmmove_task_from_our_own_user() -> None:
    api = fake_api(
        {
            "cluster/tasks": [
                {"upid": QMMOVE_UPID, "type": "vzdump", "user": "drs@pve!auto", "node": "pve01"}
            ],
        }
    )
    client = PveClient(api)
    excluded, _state = reconcile_inflight(client, State(), AUTH)
    assert excluded == frozenset()


def test_reconcile_does_not_double_count_a_upid_already_known_locally() -> None:
    """The same in-flight move already recorded in state.json also shows
    up in the cluster-wide scan -- must not be double-processed (or
    trigger a spurious "found a foreign task" warning about our own
    move)."""
    api = fake_api(
        {
            f"nodes/pve01/tasks/{QMMOVE_UPID}/status": {"status": "running"},
            "cluster/tasks": [
                {"upid": QMMOVE_UPID, "type": "qmmove", "user": "drs@pve!auto", "node": "pve01"}
            ],
        }
    )
    client = PveClient(api)
    state = State(inflight_upids=(QMMOVE_UPID,))
    excluded, new_state = reconcile_inflight(client, state, AUTH)
    assert excluded == frozenset({101})
    assert new_state.inflight_upids == (QMMOVE_UPID,)


def test_reconcile_combines_local_and_foreign_findings() -> None:
    api = fake_api(
        {
            f"nodes/pve01/tasks/{QMMOVE_UPID}/status": {"status": "running"},
            f"nodes/pve02/tasks/{QMMOVE_UPID_2}/status": {"status": "running"},
            "cluster/tasks": [
                {
                    "upid": QMMOVE_UPID_2,
                    "type": "qmmove",
                    "user": "drs@pve!auto",
                    "node": "pve02",
                }
            ],
        }
    )
    client = PveClient(api)
    state = State(inflight_upids=(QMMOVE_UPID,))
    excluded, new_state = reconcile_inflight(client, state, AUTH)
    assert excluded == frozenset({101, 102})
    assert new_state.inflight_upids == (QMMOVE_UPID,)


def test_reconcile_ignores_a_foreign_candidate_with_no_vmid() -> None:
    # e.g. a qmmove-typed task somehow lacking a VM-scoped id -- cannot be
    # turned into an exclusion, so it must be skipped rather than crash.
    api = fake_api(
        {
            "cluster/tasks": [
                {
                    "upid": "UPID:pve01:00001234:00ABCDEF:6A9D55C2:qmmove::drs@pve:",
                    "type": "qmmove",
                    "user": "drs@pve!auto",
                    "node": "pve01",
                }
            ],
        }
    )
    client = PveClient(api)
    excluded, _state = reconcile_inflight(client, State(), AUTH)
    assert excluded == frozenset()


def test_reconcile_ignores_a_foreign_task_that_has_since_finished() -> None:
    # /cluster/tasks itself still shows it as running (no endtime/status
    # yet), but the per-task status endpoint says otherwise by the time we
    # check -- an ordinary race, not a bug; must not be excluded.
    api = fake_api(
        {
            "cluster/tasks": [
                {
                    "upid": QMMOVE_UPID,
                    "type": "qmmove",
                    "user": "drs@pve!auto",
                    "node": "pve01",
                }
            ],
            f"nodes/pve01/tasks/{QMMOVE_UPID}/status": {"status": "stopped", "exitstatus": "OK"},
        }
    )
    client = PveClient(api)
    excluded, _state = reconcile_inflight(client, State(), AUTH)
    assert excluded == frozenset()


def test_reconcile_with_no_configured_user_skips_the_cluster_scan() -> None:
    api = fake_api({}, error=AssertionError("cluster/tasks must never be called"))
    client = PveClient(api)
    excluded, _state = reconcile_inflight(client, State(), AuthConfig())
    assert excluded == frozenset()
