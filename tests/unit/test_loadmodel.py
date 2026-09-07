# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The section 4 load model. See proxmox_storage_drs/loadmodel.py.

No test here talks to a real Prometheus (.agents/testing.md): PrometheusClient
is exercised through a fake session, same as test_metrics.py, keyed by the
*exact* PromQL string loadmodel.py builds -- computed here with the same
public builder functions loadmodel.py itself uses, so a query-shape change
in either place shows up as a test failure rather than a silently stale fake.

The six-disk, three-storage scenario mirrors IMPLEMENTATION_PLAN.md section
14.2's worked example exactly (same keys, same storages, same `l_d` values)
so the default-weights test is a real cross-check against the plan's own
proven-optimal numbers, not just a self-consistent unit test -- the same
practice test_reserve.py already established.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from proxmox_storage_drs.config import (
    LoadWeights,
    MetricLabels,
    MetricsConfig,
    PrometheusConfig,
    WindowConfig,
)
from proxmox_storage_drs.loadmodel import (
    GroupLoad,
    _is_metrics_expected_absent,
    compute_disk_load_series,
    compute_group_load,
)
from proxmox_storage_drs.metrics import (
    PrometheusClient,
    build_quantile_over_time_promql,
    build_rate_promql,
    raw_metric_name,
)
from proxmox_storage_drs.topology import Disk, Group, Storage

TIB = 1 << 40


def make_disk(key: str, storage: str, *, size_tib: float = 1.0) -> Disk:
    vmid, device = key.split(":")
    return Disk(
        key=key,
        vmid=int(vmid),
        device=device,
        vm_name=f"vm{vmid}",
        node="pve01",
        size_bytes=round(size_tib * TIB),
        current_storage=storage,
        format="raw",
        pinned_reason=None,
    )


def make_storage(id_: str, *, capability_weight: float = 1.0) -> Storage:
    return Storage(
        id=id_,
        capability_weight=capability_weight,
        reserve_factor=2.0,
        saturation_load=None,
        capacity_bytes=round(8.0 * TIB),
        used_bytes=0,
        foreign_used_bytes=0,
        saferemove=False,
        saferemove_throughput_bytes_per_sec=None,
    )


# A small window/step so `expected_samples` in compute_disk_coverage works
# out to a round number (2) that is easy to hand-construct full/partial
# coverage for, rather than the real default's 289.
WINDOW = WindowConfig(lookback_seconds=300.0, quantile=0.95, upper_quantile=0.99, min_coverage=0.80)
METRICS = MetricsConfig(rate_window_seconds=300.0, step_seconds=300.0, labels=MetricLabels())
PROM_CONFIG = PrometheusConfig(url="http://prom.example.com:9090")


def _quantile_promql(field_name: str, node_selector: str | None = None) -> str:
    """The exact PromQL `_fetch_raw_quantity` builds for one raw field --
    computed with the same public builders loadmodel.py uses, not
    hand-copied, so this stays correct if either changes shape."""
    metric_name = raw_metric_name(METRICS, field_name)
    rate_expr = build_rate_promql(
        metric_name,
        METRICS.labels.vmid,
        METRICS.labels.device,
        METRICS.rate_window_seconds,
        selector=node_selector,
    )
    return build_quantile_over_time_promql(
        rate_expr, WINDOW.quantile, WINDOW.lookback_seconds, METRICS.step_seconds
    )


def _coverage_promql(node_selector: str | None = None) -> str:
    """The exact PromQL `compute_disk_coverage` builds for its range query."""
    return build_rate_promql(
        METRICS.read_ops,
        METRICS.labels.vmid,
        METRICS.labels.device,
        METRICS.rate_window_seconds,
        selector=node_selector,
    )


def series(vmid: int, device: str, value: float) -> dict[str, Any]:
    return {"metric": {"vmid": str(vmid), "instance": device}, "value": [0, str(value)]}


def full_coverage(vmid: int, device: str) -> dict[str, Any]:
    """2/2 samples -- `expected_samples` for WINDOW/METRICS above is 2."""
    return {"metric": {"vmid": str(vmid), "instance": device}, "values": [[0, "0"], [300, "0"]]}


def no_coverage(vmid: int, device: str) -> dict[str, Any]:
    """0/2 samples: present in the coverage series but with nothing in it."""
    return {"metric": {"vmid": str(vmid), "instance": device}, "values": []}


@dataclass
class FakeResponse:
    status_code: int = 200
    _payload: dict[str, Any] = field(default_factory=dict)
    text: str = ""

    def json(self) -> dict[str, Any]:
        return self._payload


@dataclass
class FakeSession:
    """Answers `/api/v1/query` and `/api/v1/query_range` by the exact
    `query` param value -- unlike test_metrics.py's `FakeSession` (keyed
    only by path, adequate there since each of its tests issues at most one
    distinct query per path), loadmodel.py issues one instant query per raw
    field plus one range query, all needing independently controlled
    results."""

    query_data: dict[str, list[dict[str, Any]]]
    range_data: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    calls: list[tuple[str, str]] = field(default_factory=list)
    range_params: list[dict[str, str]] = field(default_factory=list)

    def get(
        self,
        url: str,
        params: dict[str, str],
        timeout: float,
        auth: object,
        headers: dict[str, str],
    ) -> FakeResponse:
        del timeout, auth, headers
        query = params["query"]
        if url.endswith("/api/v1/query_range"):
            self.calls.append(("range", query))
            self.range_params.append(params)
            result = self.range_data[query]
        elif url.endswith("/api/v1/query"):
            self.calls.append(("query", query))
            result = self.query_data[query]
        else:
            raise AssertionError(f"unexpected request to {url}")
        return FakeResponse(200, {"status": "success", "data": {"result": result}})


def _client(
    *,
    read_time: list[dict[str, Any]] | None = None,
    write_time: list[dict[str, Any]] | None = None,
    read_ops: list[dict[str, Any]] | None = None,
    write_ops: list[dict[str, Any]] | None = None,
    read_bytes: list[dict[str, Any]] | None = None,
    write_bytes: list[dict[str, Any]] | None = None,
    coverage: list[dict[str, Any]] | None = None,
    node_selector: str | None = None,
) -> tuple[PrometheusClient, FakeSession]:
    """Build a `PrometheusClient` over a `FakeSession` answering every one of
    loadmodel.py's six raw-quantity queries plus the coverage range query.
    Every argument defaults to "no series at all" -- exactly what an idle or
    genuinely-absent (tpmstate0/unusedN) disk looks like. ``node_selector``
    must match what the caller passes to `compute_group_load()`/
    `compute_disk_load_series()` exactly: `FakeSession` looks answers up by
    the literal query string, so a mismatch here is a `KeyError`, not a
    silently-wrong result."""
    query_data = {
        _quantile_promql("read_time_ns", node_selector): read_time or [],
        _quantile_promql("write_time_ns", node_selector): write_time or [],
        _quantile_promql("read_ops", node_selector): read_ops or [],
        _quantile_promql("write_ops", node_selector): write_ops or [],
        _quantile_promql("read_bytes", node_selector): read_bytes or [],
        _quantile_promql("write_bytes", node_selector): write_bytes or [],
    }
    range_data = {_coverage_promql(node_selector): coverage or []}
    session = FakeSession(query_data=query_data, range_data=range_data)
    return PrometheusClient(PROM_CONFIG, session=session), session


# ------------------------------------------------------------- _is_metrics_expected_absent


@pytest.mark.parametrize(
    "device,expected",
    [
        ("tpmstate0", True),
        ("unused0", True),
        ("unused15", True),
        ("efidisk0", False),
        ("scsi0", False),
        ("virtio3", False),
    ],
)
def test_is_metrics_expected_absent(device: str, expected: bool) -> None:
    assert _is_metrics_expected_absent(device) is expected


# --------------------------------------------------------- section 14.2 cross-check


def _section_14_group() -> Group:
    disks = (
        make_disk("101:scsi0", "san-a", size_tib=2.0),
        make_disk("101:scsi1", "san-a", size_tib=1.0),
        make_disk("102:scsi0", "san-a", size_tib=1.5),
        make_disk("103:scsi0", "san-b", size_tib=0.5),
        make_disk("104:scsi0", "san-b", size_tib=1.0),
        make_disk("105:scsi0", "san-c", size_tib=0.5),
    )
    storages = (make_storage("san-a"), make_storage("san-b"), make_storage("san-c"))
    return Group(name="fc-tier1", storages=storages, disks=disks)


def test_default_weights_reproduce_section_14_2_loads_exactly() -> None:
    """Under the default weights (w_t=1, w_o=w_b=0) section 4 states the
    rescale is an exact identity, l_d = raw_t(d) -- put each disk's l_d
    value directly on read_time_ns (in ns/s, so *1e9) and expect it back
    unchanged, matching Sigma-l=7.4, u*=2.4667 from section 14.2."""
    group = _section_14_group()
    read_time = [
        series(101, "scsi0", 3.0e9),
        series(101, "scsi1", 1.0e9),
        series(102, "scsi0", 2.5e9),
        series(103, "scsi0", 0.4e9),
        series(104, "scsi0", 0.3e9),
        series(105, "scsi0", 0.2e9),
    ]
    coverage = [full_coverage(vmid, device) for vmid, device in [(101, "scsi0"), (101, "scsi1")]]
    coverage += [full_coverage(v, d) for v, d in [(102, "scsi0"), (103, "scsi0"), (104, "scsi0")]]
    coverage += [full_coverage(105, "scsi0")]
    client, _session = _client(read_time=read_time, coverage=coverage)

    result = compute_group_load(client, METRICS, WINDOW, LoadWeights(), group)

    loads = result.load_by_disk_key()
    assert loads["101:scsi0"] == pytest.approx(3.0)
    assert loads["101:scsi1"] == pytest.approx(1.0)
    assert loads["102:scsi0"] == pytest.approx(2.5)
    assert loads["103:scsi0"] == pytest.approx(0.4)
    assert loads["104:scsi0"] == pytest.approx(0.3)
    assert loads["105:scsi0"] == pytest.approx(0.2)
    assert sum(loads.values()) == pytest.approx(7.4)
    assert result.average_utilization == pytest.approx(7.4 / 3)
    assert not result.idle
    assert all(d.flagged_reason is None for d in result.disks)

    by_storage = {s.storage_id: s for s in result.storages}
    assert by_storage["san-a"].load == pytest.approx(6.5)
    assert by_storage["san-b"].load == pytest.approx(0.7)
    assert by_storage["san-c"].load == pytest.approx(0.2)
    # capability_weight = 1.0 everywhere in this fixture, so u_s == L_s.
    assert by_storage["san-a"].utilization == pytest.approx(6.5)


def test_capability_weight_divides_utilization_but_not_load() -> None:
    group = Group(
        name="g",
        storages=(make_storage("san-a", capability_weight=0.5),),
        disks=(make_disk("101:scsi0", "san-a"),),
    )
    coverage = [full_coverage(101, "scsi0")]
    client, _session = _client(read_time=[series(101, "scsi0", 4.0e9)], coverage=coverage)

    result = compute_group_load(client, METRICS, WINDOW, LoadWeights(), group)

    storage_load = result.storages[0]
    assert storage_load.load == pytest.approx(4.0)
    assert storage_load.utilization == pytest.approx(8.0)  # 4.0 / 0.5


# ------------------------------------------------------------------- weights


def test_read_write_factors_are_applied_before_normalization() -> None:
    """F-03: read_factor/write_factor combine reads and writes engine-side,
    before any normalization -- verified here with an asymmetric weight on
    a single disk carrying only write time."""
    group = Group(
        name="g", storages=(make_storage("san-a"),), disks=(make_disk("101:scsi0", "san-a"),)
    )
    coverage = [full_coverage(101, "scsi0")]
    client, _session = _client(write_time=[series(101, "scsi0", 2.0e9)], coverage=coverage)

    weights = LoadWeights(read_factor=1.0, write_factor=3.0)
    result = compute_group_load(client, METRICS, WINDOW, weights, group)

    # raw_t = rho*0 + omega*2.0 = 6.0; default weights (w_t=1) -> l_d = 6.0.
    assert result.load_by_disk_key()["101:scsi0"] == pytest.approx(6.0)


def test_ops_and_bytes_terms_blend_when_weighted() -> None:
    """Non-default weights bring in ops/bytes; each term is normalized
    against its own group total before the blend, per section 4's formula."""
    group = Group(
        name="g",
        storages=(make_storage("san-a"),),
        disks=(make_disk("101:scsi0", "san-a"), make_disk("102:scsi0", "san-a")),
    )
    coverage = [full_coverage(101, "scsi0"), full_coverage(102, "scsi0")]
    client, _session = _client(
        read_time=[series(101, "scsi0", 1.0e9), series(102, "scsi0", 1.0e9)],
        read_ops=[series(101, "scsi0", 100.0), series(102, "scsi0", 300.0)],
        coverage=coverage,
    )

    # Equal iotime -> equal i_d (0.5 each); ops split 25%/75% -> that term
    # should pull 102:scsi0 above 101:scsi0 once w_o > 0.
    weights = LoadWeights(iotime=1.0, ops=1.0, bytes=0.0)
    result = compute_group_load(client, METRICS, WINDOW, weights, group)
    loads = result.load_by_disk_key()

    t_total = 2.0  # raw_t sum
    i_d, o_d_101 = 0.5, 0.25
    o_d_102 = 0.75
    expected_101 = t_total * (1.0 * i_d + 1.0 * o_d_101) / 2.0
    expected_102 = t_total * (1.0 * i_d + 1.0 * o_d_102) / 2.0
    assert loads["101:scsi0"] == pytest.approx(expected_101)
    assert loads["102:scsi0"] == pytest.approx(expected_102)
    assert loads["101:scsi0"] < loads["102:scsi0"]


def test_zero_group_total_for_a_weighted_term_guards_division() -> None:
    """w_b > 0 but no disk has any byte-rate data at all: the bytes term
    must contribute 0, not raise or produce NaN."""
    group = Group(
        name="g", storages=(make_storage("san-a"),), disks=(make_disk("101:scsi0", "san-a"),)
    )
    coverage = [full_coverage(101, "scsi0")]
    client, _session = _client(read_time=[series(101, "scsi0", 1.0e9)], coverage=coverage)

    weights = LoadWeights(iotime=1.0, ops=0.0, bytes=1.0)
    result = compute_group_load(client, METRICS, WINDOW, weights, group)

    # bytes term contributes 0 (b_total == 0 guarded); iotime term alone:
    # l_d = 1.0 * (1.0*1.0 + 1.0*0.0) / 2.0 = 0.5.
    assert result.load_by_disk_key()["101:scsi0"] == pytest.approx(0.5)


# ---------------------------------------------------------------------- idle


def test_idle_group_has_zero_loads_and_is_flagged_idle() -> None:
    group = Group(
        name="g", storages=(make_storage("san-a"),), disks=(make_disk("101:scsi0", "san-a"),)
    )
    coverage = [full_coverage(101, "scsi0")]  # good coverage, just zero-rate data
    client, _session = _client(coverage=coverage)

    result = compute_group_load(client, METRICS, WINDOW, LoadWeights(), group)

    assert result.idle
    assert result.load_by_disk_key()["101:scsi0"] == pytest.approx(0.0)
    assert result.disks[0].flagged_reason is None  # genuinely idle, not missing data
    assert result.average_utilization == pytest.approx(0.0)


def test_empty_group_is_idle_with_no_disks_or_storages_and_makes_no_calls() -> None:
    group = Group(name="g", storages=(), disks=())
    client, session = _client()

    result = compute_group_load(client, METRICS, WINDOW, LoadWeights(), group)

    assert result == GroupLoad(
        group_name="g", idle=True, average_utilization=0.0, disks=(), storages=()
    )
    assert session.calls == []  # nothing to fetch for a group with no disks


# -------------------------------------------------------- node-scoping selector


def test_compute_group_load_applies_the_node_selector_to_every_query() -> None:
    """`node_selector` must reach every one of the six raw-quantity queries
    *and* the coverage query -- `_client()`'s `FakeSession` only has
    answers keyed by the query string embedding this selector, so a
    single query missing it is a `KeyError`, not a silently-passing test."""
    group = Group(
        name="g", storages=(make_storage("san-a"),), disks=(make_disk("101:scsi0", "san-a"),)
    )
    selector = 'nodename=~"pve01|pve02"'
    coverage = [full_coverage(101, "scsi0")]
    client, session = _client(
        read_time=[series(101, "scsi0", 2.0e9)], coverage=coverage, node_selector=selector
    )

    result = compute_group_load(
        client, METRICS, WINDOW, LoadWeights(), group, node_selector=selector
    )

    assert result.load_by_disk_key()["101:scsi0"] == pytest.approx(2.0)
    assert session.calls  # every call above resolved against the selector-scoped keys
    for _kind, query in session.calls:
        assert selector in query


def test_compute_group_load_node_selector_none_is_unchanged_from_before() -> None:
    """The default -- no behaviour change for a caller that never passes
    `node_selector` at all (every pre-existing test in this file)."""
    group = Group(
        name="g", storages=(make_storage("san-a"),), disks=(make_disk("101:scsi0", "san-a"),)
    )
    coverage = [full_coverage(101, "scsi0")]
    client, _session = _client(read_time=[series(101, "scsi0", 2.0e9)], coverage=coverage)
    result = compute_group_load(client, METRICS, WINDOW, LoadWeights(), group)
    assert result.load_by_disk_key()["101:scsi0"] == pytest.approx(2.0)


# ---------------------------------------------------------------- coverage rejection


def test_low_coverage_disk_falls_back_to_last_known_load() -> None:
    group = Group(
        name="g",
        storages=(make_storage("san-a"),),
        disks=(make_disk("101:scsi0", "san-a"), make_disk("102:scsi0", "san-a")),
    )
    # 101:scsi0 has good coverage; 102:scsi0 has 0/2 -- below min_coverage.
    coverage = [full_coverage(101, "scsi0"), no_coverage(102, "scsi0")]
    client, _session = _client(
        read_time=[series(101, "scsi0", 2.0e9), series(102, "scsi0", 999.0e9)],
        coverage=coverage,
    )

    result = compute_group_load(
        client, METRICS, WINDOW, LoadWeights(), group, last_known_loads={"102:scsi0": 1.5}
    )

    loads = result.load_by_disk_key()
    assert loads["102:scsi0"] == pytest.approx(1.5)  # substituted, not the garbage 999
    assert loads["101:scsi0"] == pytest.approx(2.0)  # unaffected by the rejected disk
    by_key = {d.disk_key: d for d in result.disks}
    assert by_key["102:scsi0"].flagged_reason is not None
    assert "using last known load" in by_key["102:scsi0"].flagged_reason
    assert by_key["101:scsi0"].flagged_reason is None


def test_low_coverage_disk_without_fallback_is_flagged_zero_not_silently_accepted() -> None:
    group = Group(
        name="g", storages=(make_storage("san-a"),), disks=(make_disk("101:scsi0", "san-a"),)
    )
    coverage = [no_coverage(101, "scsi0")]
    client, _session = _client(read_time=[series(101, "scsi0", 5.0e9)], coverage=coverage)

    result = compute_group_load(client, METRICS, WINDOW, LoadWeights(), group)

    disk_load = result.disks[0]
    assert disk_load.load == 0.0
    assert disk_load.flagged_reason is not None
    assert "no last known load recorded" in disk_load.flagged_reason


def test_disk_absent_from_coverage_series_entirely_is_treated_as_zero_coverage() -> None:
    """A disk with no entry at all in the coverage range-query result (not
    even a 0-sample series) must be rejected exactly like 0/N coverage --
    `.get(key, 0.0)`, not a KeyError or a free pass."""
    group = Group(
        name="g", storages=(make_storage("san-a"),), disks=(make_disk("101:scsi0", "san-a"),)
    )
    client, _session = _client(read_time=[series(101, "scsi0", 5.0e9)], coverage=[])

    result = compute_group_load(client, METRICS, WINDOW, LoadWeights(), group)

    assert result.disks[0].load == 0.0
    assert result.disks[0].flagged_reason is not None


def test_tpmstate0_and_unused_disks_are_never_coverage_rejected() -> None:
    """Section 3.4: these device kinds genuinely emit no blockstat series --
    l_d = 0 is correct, not a data-quality problem to flag."""
    group = Group(
        name="g",
        storages=(make_storage("san-a"),),
        disks=(make_disk("101:tpmstate0", "san-a"), make_disk("101:unused0", "san-a")),
    )
    client, _session = _client(coverage=[])  # no coverage series for either -- expected

    result = compute_group_load(client, METRICS, WINDOW, LoadWeights(), group)

    for disk_load in result.disks:
        assert disk_load.load == 0.0
        assert disk_load.flagged_reason is None


def test_efidisk0_is_held_to_the_normal_coverage_bar() -> None:
    """Unlike tpmstate0/unusedN, efidisk0 is a real QEMU drive and should
    appear in blockstat -- missing coverage for it is a genuine flag."""
    group = Group(
        name="g", storages=(make_storage("san-a"),), disks=(make_disk("101:efidisk0", "san-a"),)
    )
    client, _session = _client(coverage=[])

    result = compute_group_load(client, METRICS, WINDOW, LoadWeights(), group)

    assert result.disks[0].flagged_reason is not None


# ------------------------------------------------------------- GroupLoad helper


def _rate_promql(field_name: str, node_selector: str | None = None) -> str:
    """The exact PromQL `_fetch_raw_quantity_series` builds for one raw
    field -- the bare `rate(...)` expression, unlike `_quantile_promql`'s
    `quantile_over_time`-wrapped instant-query form."""
    metric_name = raw_metric_name(METRICS, field_name)
    return build_rate_promql(
        metric_name,
        METRICS.labels.vmid,
        METRICS.labels.device,
        METRICS.rate_window_seconds,
        selector=node_selector,
    )


def range_series(vmid: int, device: str, points: list[tuple[float, float]]) -> dict[str, Any]:
    """A `query_range`-shaped series with an explicit `[[ts, value], ...]`
    matrix, unlike `series()`'s single-`value` instant-query shape."""
    return {
        "metric": {"vmid": str(vmid), "instance": device},
        "values": [[ts, str(v)] for ts, v in points],
    }


def _series_client(
    *,
    read_time: list[dict[str, Any]] | None = None,
    write_time: list[dict[str, Any]] | None = None,
    read_ops: list[dict[str, Any]] | None = None,
    write_ops: list[dict[str, Any]] | None = None,
    read_bytes: list[dict[str, Any]] | None = None,
    write_bytes: list[dict[str, Any]] | None = None,
    node_selector: str | None = None,
) -> tuple[PrometheusClient, FakeSession]:
    """Build a `PrometheusClient` over a `FakeSession` answering
    `compute_disk_load_series()`'s own six raw-quantity range queries --
    `_client()`'s counterpart for the series path, keyed by the bare
    `rate(...)` expression rather than the quantile-wrapped instant-query
    form. Every argument defaults to no series at all."""
    range_data = {
        _rate_promql("read_time_ns", node_selector): read_time or [],
        _rate_promql("write_time_ns", node_selector): write_time or [],
        _rate_promql("read_ops", node_selector): read_ops or [],
        _rate_promql("write_ops", node_selector): write_ops or [],
        _rate_promql("read_bytes", node_selector): read_bytes or [],
        _rate_promql("write_bytes", node_selector): write_bytes or [],
    }
    session = FakeSession(query_data={}, range_data=range_data)
    return PrometheusClient(PROM_CONFIG, session=session), session


# ------------------------------------------------------------- compute_disk_load_series


def test_compute_disk_load_series_applies_the_node_selector_to_every_query() -> None:
    group = Group(
        name="g", storages=(make_storage("san-a"),), disks=(make_disk("101:scsi0", "san-a"),)
    )
    selector = 'nodename=~"pve01|pve02"'
    read_time = [range_series(101, "scsi0", [(0.0, 2.0e9), (300.0, 2.0e9)])]
    client, session = _series_client(read_time=read_time, node_selector=selector)

    result = compute_disk_load_series(
        client,
        METRICS,
        LoadWeights(),
        group,
        range_seconds=300.0,
        step_seconds=300.0,
        now_epoch_seconds=300.0,
        node_selector=selector,
    )

    assert result["101:scsi0"][0][1] == pytest.approx(2.0)
    assert session.calls
    for _kind, query in session.calls:
        assert selector in query


def test_compute_disk_load_series_matches_section_14_2_at_every_timestamp() -> None:
    """Under the default weights section 4's rescale is an exact identity,
    l_d(t) = raw_t(d, t) -- put each disk's l_d value directly on
    read_time_ns at two timestamps and expect both back unchanged, the
    section 14.2 cross-check reproduced per-timestamp instead of once."""
    group = _section_14_group()
    values = {
        "101:scsi0": 3.0e9,
        "101:scsi1": 1.0e9,
        "102:scsi0": 2.5e9,
        "103:scsi0": 0.4e9,
        "104:scsi0": 0.3e9,
        "105:scsi0": 0.2e9,
    }
    read_time = [
        range_series(int(k.split(":")[0]), k.split(":")[1], [(0.0, v), (300.0, v)])
        for k, v in values.items()
    ]
    client, _session = _series_client(read_time=read_time)

    result = compute_disk_load_series(
        client,
        METRICS,
        LoadWeights(),
        group,
        range_seconds=300.0,
        step_seconds=300.0,
        now_epoch_seconds=300.0,
    )

    for key, expected in values.items():
        ell_d = expected / 1e9
        assert dict(result[key]) == {0.0: pytest.approx(ell_d), 300.0: pytest.approx(ell_d)}


def test_compute_disk_load_series_normalizes_each_timestamp_independently() -> None:
    """Two disks whose iotime split flips between the two timestamps --
    normalizing over the *whole range* instead of per-timestamp would
    blend the two splits together; this must not happen."""
    group = Group(
        name="g",
        storages=(make_storage("san-a"),),
        disks=(make_disk("101:scsi0", "san-a"), make_disk("102:scsi0", "san-a")),
    )
    read_time = [
        range_series(101, "scsi0", [(0.0, 3.0e9), (300.0, 1.0e9)]),
        range_series(102, "scsi0", [(0.0, 1.0e9), (300.0, 3.0e9)]),
    ]
    client, _session = _series_client(read_time=read_time)

    result = compute_disk_load_series(
        client,
        METRICS,
        LoadWeights(),
        group,
        range_seconds=300.0,
        step_seconds=300.0,
        now_epoch_seconds=300.0,
    )

    # Default weights: l_d = raw_t exactly, so each disk keeps its own
    # value at each timestamp -- no cross-timestamp blending occurred.
    assert dict(result["101:scsi0"]) == {0.0: pytest.approx(3.0), 300.0: pytest.approx(1.0)}
    assert dict(result["102:scsi0"]) == {0.0: pytest.approx(1.0), 300.0: pytest.approx(3.0)}


def test_compute_disk_load_series_missing_sample_at_a_timestamp_defaults_to_zero() -> None:
    """101:scsi0 has no sample at t=300 at all (a shorter series than
    102:scsi0's) -- that timestamp must still appear (from 102:scsi0's own
    contribution to the timestamp union) with 101:scsi0 contributing 0,
    not KeyError."""
    group = Group(
        name="g",
        storages=(make_storage("san-a"),),
        disks=(make_disk("101:scsi0", "san-a"), make_disk("102:scsi0", "san-a")),
    )
    read_time = [
        range_series(101, "scsi0", [(0.0, 1.0e9)]),
        range_series(102, "scsi0", [(0.0, 1.0e9), (300.0, 1.0e9)]),
    ]
    client, _session = _series_client(read_time=read_time)

    result = compute_disk_load_series(
        client,
        METRICS,
        LoadWeights(),
        group,
        range_seconds=300.0,
        step_seconds=300.0,
        now_epoch_seconds=300.0,
    )

    assert dict(result["101:scsi0"]) == {0.0: pytest.approx(1.0), 300.0: pytest.approx(0.0)}
    assert dict(result["102:scsi0"]) == {0.0: pytest.approx(1.0), 300.0: pytest.approx(1.0)}


def test_compute_disk_load_series_returns_an_empty_series_for_a_disk_with_no_data() -> None:
    """Every disk in `group` gets an entry, even one with no samples at
    all -- an empty series, never a missing key."""
    group = Group(
        name="g", storages=(make_storage("san-a"),), disks=(make_disk("101:scsi0", "san-a"),)
    )
    client, _session = _series_client()

    result = compute_disk_load_series(
        client,
        METRICS,
        LoadWeights(),
        group,
        range_seconds=300.0,
        step_seconds=300.0,
        now_epoch_seconds=300.0,
    )

    assert result == {"101:scsi0": ()}


def test_compute_disk_load_series_empty_group_makes_no_calls() -> None:
    group = Group(name="g", storages=(), disks=())
    client, session = _series_client()

    result = compute_disk_load_series(
        client,
        METRICS,
        LoadWeights(),
        group,
        range_seconds=300.0,
        step_seconds=300.0,
        now_epoch_seconds=300.0,
    )

    assert result == {}
    assert session.calls == []


def test_compute_disk_load_series_uses_the_given_range_not_window_lookback() -> None:
    """`range_seconds`/`step_seconds`/`now_epoch_seconds` are the caller's
    own choice, not `window.lookback_seconds` (300.0 in this fixture) --
    confirmed by using a wildly different range/step/step and checking the
    actual `start`/`end`/`step` params a range query carried."""
    group = Group(
        name="g", storages=(make_storage("san-a"),), disks=(make_disk("101:scsi0", "san-a"),)
    )
    client, session = _series_client(read_time=[range_series(101, "scsi0", [(0.0, 1.0e9)])])

    compute_disk_load_series(
        client,
        METRICS,
        LoadWeights(),
        group,
        range_seconds=604800.0,
        step_seconds=3600.0,
        now_epoch_seconds=604800.0,
    )

    assert session.range_params  # at least one range query was actually issued
    params = session.range_params[0]
    assert float(params["start"]) == pytest.approx(0.0)  # 604800 - 604800
    assert float(params["end"]) == pytest.approx(604800.0)
    assert params["step"] == "3600s"


def test_load_by_disk_key_matches_disks_tuple() -> None:
    group = Group(
        name="g", storages=(make_storage("san-a"),), disks=(make_disk("101:scsi0", "san-a"),)
    )
    coverage = [full_coverage(101, "scsi0")]
    client, _session = _client(read_time=[series(101, "scsi0", 1.0e9)], coverage=coverage)

    result = compute_group_load(client, METRICS, WINDOW, LoadWeights(), group)

    assert result.load_by_disk_key() == {d.disk_key: d.load for d in result.disks}
