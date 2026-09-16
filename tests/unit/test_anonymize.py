# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""anonymize.py: allowlists, pseudonyms, timestamp rebasing. See
IMPLEMENTATION_PLAN.md section 16.3."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from proxmox_storage_drs import anonymize as a
from proxmox_storage_drs.exceptions import BundleError

SALT_A = b"a" * 32
SALT_B = b"b" * 32
CAPTURE_START = 1_757_000_000.0  # an arbitrary, fixed instant


def make_mapper(
    salt: bytes = SALT_A,
    *,
    nodes: frozenset[str] = frozenset({"pve01", "pve02"}),
    storages: frozenset[str] = frozenset({"san-a", "san-b"}),
) -> a.Mapper:
    return a.Mapper(
        salt=salt, capture_start_epoch=CAPTURE_START, known_nodes=nodes, known_storages=storages
    )


# --------------------------------------------------------------- allowlists


def test_filter_allowed_fields_drops_everything_not_named() -> None:
    storage_def = {
        "storage": "san-a",
        "type": "iscsi",
        "content": "images",
        "shared": 1,
        "portal": "10.0.0.1:3260",
        "password": "hunter2",
    }
    filtered = a.filter_allowed_fields(storage_def, a.STORAGE_DEFINITION_FIELDS)
    assert filtered == {"storage": "san-a", "type": "iscsi", "content": "images", "shared": 1}
    assert "portal" not in filtered
    assert "password" not in filtered


def test_filter_disk_value_params_drops_iothread_and_discard() -> None:
    from proxmox_storage_drs.topology import parse_disk_spec

    _, _, params = parse_disk_spec("san-a:vm-101-disk-0,size=512G,iothread=1,discard=on")
    filtered = a.filter_disk_value_params(params)
    assert filtered == {"size": "512G"}


def test_filter_vm_config_fields_keeps_disk_keys_and_lock_template() -> None:
    raw_config = {
        "scsi0": "san-a:vm-101-disk-0,size=32G",
        "ide2": "none,media=cdrom",
        "net0": "virtio=AA:BB:CC:DD:EE:FF,bridge=vmbr0",
        "sshkeys": "ssh-ed25519 AAAA...",
        "lock": "backup",
        "template": 0,
        "name": "db-01",
        "description": "customer: acme corp",
    }
    filtered = a.filter_vm_config_fields(raw_config)
    assert filtered == {
        "scsi0": "san-a:vm-101-disk-0,size=32G",
        "ide2": "none,media=cdrom",
        "lock": "backup",
        "template": 0,
        "name": "db-01",
    }


def test_filter_vm_pending_entries_keeps_only_the_disk_signal() -> None:
    """Section 3.8/16.3: neither a disk key's own `pending` string (a full
    disk spec, storage id and volume name) nor a non-disk key's `value`/
    `pending` (free text, e.g. a queued VM `name`) survives -- only which
    disk devices carry an edit or a deletion."""
    raw: list[dict[str, object]] = [
        {"key": "name", "value": "db-01", "pending": "db-01-renamed"},  # free text -- dropped
        {"key": "memory", "value": "8192", "pending": "16384"},  # non-disk -- dropped
        {
            "key": "scsi0",
            "value": "san-a:vm-101-disk-0,size=32G",
            "pending": "san-a:vm-101-disk-0,size=64G",
        },
        {"key": "scsi1", "value": "san-a:vm-101-disk-1,size=5G", "delete": 1},
        {"key": "scsi2", "value": "san-a:vm-101-disk-2,size=5G"},  # no divergence -- dropped
    ]
    assert a.filter_vm_pending_entries(raw) == [
        {"key": "scsi0", "pending": True},
        {"key": "scsi1", "delete": 1},
    ]


def test_sanitize_snapshot_name() -> None:
    assert a.sanitize_snapshot_name("current") == "current"
    assert a.sanitize_snapshot_name("before-migration") == "snapshot"


# ----------------------------------------------------------------- pseudonym


def test_pseudonym_deterministic_for_same_salt() -> None:
    assert a.pseudonym(SALT_A, "node", "pve01") == a.pseudonym(SALT_A, "node", "pve01")


def test_pseudonym_differs_by_salt() -> None:
    assert a.pseudonym(SALT_A, "node", "pve01") != a.pseudonym(SALT_B, "node", "pve01")


def test_pseudonym_differs_by_kind_for_same_value() -> None:
    """A node and a storage that happen to share a name must not collide."""
    assert a.pseudonym(SALT_A, "node", "shared-name") != a.pseudonym(
        SALT_A, "storage", "shared-name"
    )


def test_salt_fingerprint_deterministic_and_salt_scoped() -> None:
    assert a.salt_fingerprint(SALT_A) == a.salt_fingerprint(SALT_A)
    assert a.salt_fingerprint(SALT_A) != a.salt_fingerprint(SALT_B)
    # The fingerprint must not itself be (or trivially reveal) the salt.
    assert a.salt_fingerprint(SALT_A) != SALT_A.hex()


def test_load_or_create_salt_persists_and_is_mode_0600(tmp_path: Path) -> None:
    path = tmp_path / "salt"
    first = a.load_or_create_salt(path)
    assert len(first) == 32
    assert path.stat().st_mode & 0o777 == 0o600
    second = a.load_or_create_salt(path)
    assert second == first  # persisted, not regenerated


def test_generate_new_salt_rotates_the_mapping(tmp_path: Path) -> None:
    path = tmp_path / "salt"
    first = a.load_or_create_salt(path)
    second = a.generate_new_salt(path)
    assert second != first
    assert a.load_or_create_salt(path) == second


# --------------------------------------------------------------------- clock


def test_week_aligned_offset_preserves_hour_and_weekday() -> None:
    from datetime import datetime, timezone

    offset = a.week_aligned_offset_seconds(CAPTURE_START)
    rebased = CAPTURE_START - offset
    original_dt = datetime.fromtimestamp(CAPTURE_START, tz=timezone.utc)
    rebased_dt = datetime.fromtimestamp(rebased, tz=timezone.utc)
    assert original_dt.weekday() == rebased_dt.weekday()
    assert original_dt.hour == rebased_dt.hour
    assert original_dt.minute == rebased_dt.minute


def test_rebase_timestamp_is_a_fixed_offset() -> None:
    mapper = make_mapper()
    t1 = CAPTURE_START
    t2 = CAPTURE_START + 3600
    assert mapper.rebase_timestamp(t2) - mapper.rebase_timestamp(t1) == 3600


# --------------------------------------------------------------------- vmid


def test_vmid_unregistered_returns_none_and_counts_as_dropped() -> None:
    mapper = make_mapper()
    assert mapper.vmid(101) is None
    assert mapper.dropped_records == 1


def test_vmid_registered_is_stable_and_in_range() -> None:
    mapper = make_mapper()
    mapper.register_vmids([101, 102, 103])
    first = mapper.vmid(101)
    assert first == mapper.vmid(101)  # stable across calls
    for vmid in (101, 102, 103):
        pseudo = mapper.vmid(vmid)
        assert pseudo is not None
        assert 100 <= pseudo < 1_000_000


def test_vmid_registration_is_order_independent() -> None:
    """Section 16.3: 'the result never depends on iteration order'."""
    forward = make_mapper()
    forward.register_vmids([101, 102, 103, 104])

    backward = make_mapper()
    backward.register_vmids([104, 103, 102, 101])

    for vmid in (101, 102, 103, 104):
        assert forward.vmid(vmid) == backward.vmid(vmid)


def test_vmid_collision_is_resolved_by_linear_probing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force two different vmids to hash to the same base slot and confirm
    both still get distinct, deterministic pseudonyms."""
    collisions = {"1": 500, "2": 500}  # str(original) -> forced base offset

    def fake_pseudonym_int(salt: bytes, kind: str, value: str, modulus: int) -> int:
        return collisions[value]

    monkeypatch.setattr(a, "_pseudonym_int", fake_pseudonym_int)
    mapper = make_mapper()
    mapper.register_vmids([1, 2])
    assert mapper.vmid(1) == 100 + 500
    assert mapper.vmid(2) == 100 + 501  # probed to the next free slot


def test_node_pseudonym_collision_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """X-09: `vmid`'s own linear probing makes a collision impossible, but
    nothing did the equivalent for node/storage names -- two of them
    hashing to the same 8-hex pseudonym would otherwise silently merge
    into one record in the bundle (same file name, same
    `groups[].storages[].id`). Refused loudly at `Mapper` construction
    instead."""
    real_pseudonym = a.pseudonym

    def colliding_pseudonym(salt: bytes, kind: str, value: str) -> str:
        if kind == "node":
            return "deadbeef"
        return real_pseudonym(salt, kind, value)

    monkeypatch.setattr(a, "pseudonym", colliding_pseudonym)
    with pytest.raises(BundleError, match="anonymization collision"):
        make_mapper(nodes=frozenset({"pve01", "pve02"}))


def test_storage_pseudonym_collision_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    real_pseudonym = a.pseudonym

    def colliding_pseudonym(salt: bytes, kind: str, value: str) -> str:
        if kind == "storage":
            return "deadbeef"
        return real_pseudonym(salt, kind, value)

    monkeypatch.setattr(a, "pseudonym", colliding_pseudonym)
    with pytest.raises(BundleError, match="anonymization collision"):
        make_mapper(storages=frozenset({"san-a", "san-b"}))


# ----------------------------------------------------------------- node/tag


def test_node_pseudonym_shape() -> None:
    mapper = make_mapper()
    assert mapper.node("pve01").startswith("node-")
    assert "." not in mapper.node("pve01")


def test_node_fqdn_shape_is_preserved() -> None:
    mapper = make_mapper()
    pseudo = mapper.node("pve01.example.com")
    assert pseudo.endswith(".invalid")
    assert pseudo.count(".") == 2  # node-XXXXXXXX . XXXXXXXX . invalid


def test_storage_group_tag_pool_pseudonyms_are_prefixed() -> None:
    mapper = make_mapper()
    assert mapper.storage("san-a").startswith("stor-")
    assert mapper.group("fc-tier1").startswith("group-")
    assert mapper.tag("no-drs").startswith("tag-")
    assert mapper.pool("prod").startswith("pool-")


def test_username_keeps_realm_verbatim() -> None:
    mapper = make_mapper()
    pseudo = mapper.username("drs@pve")
    assert pseudo.endswith("@pve")
    assert not pseudo.startswith("drs")


# --------------------------------------------------------------- volume ids


def test_volume_id_rebuilds_with_mapped_storage_and_vmid() -> None:
    mapper = make_mapper()
    mapper.register_vmids([101])
    pseudo = mapper.volume_id("san-a:vm-101-disk-0")
    assert pseudo is not None
    storage_part, _, name_part = pseudo.partition(":")
    assert storage_part == mapper.storage("san-a")
    assert name_part == f"vm-{mapper.vmid(101)}-disk-0"


def test_volume_id_unknown_storage_drops() -> None:
    mapper = make_mapper()
    mapper.register_vmids([101])
    assert mapper.volume_id("unknown-storage:vm-101-disk-0") is None


def test_volume_id_unregistered_vmid_drops() -> None:
    mapper = make_mapper()
    assert mapper.volume_id("san-a:vm-999-disk-0") is None


def test_volume_id_unrecognized_name_drops() -> None:
    mapper = make_mapper()
    mapper.register_vmids([101])
    assert mapper.volume_id("san-a:some-custom-volume-name") is None


def test_volume_id_base_prefix_and_cloudinit_fallback() -> None:
    mapper = make_mapper()
    mapper.register_vmids([101])
    base = mapper.volume_id("san-a:base-101-disk-0")
    assert base is not None and base.split(":")[1].startswith("base-")
    cloudinit = mapper.volume_id("san-a:vm-101-cloudinit")
    assert cloudinit is not None and cloudinit.endswith("-cloudinit")


def test_volume_id_preserves_a_format_extension_on_the_volume_name() -> None:
    """PVE's own `get_next_vm_diskname()` appends a literal `.<format>` to
    the volume *name* itself for a non-raw-default volume -- confirmed on a
    real cluster's qcow2-on-shared-LVM disk (`vm-101-disk-1.qcow2`, no
    separate `format=` param in the disk value at all). Every such disk was
    silently dropped ("unrecognized name") before this fix -- the `$`
    anchor in `_VOLUME_ID_RE` left no room for the extension."""
    mapper = make_mapper()
    mapper.register_vmids([101])
    pseudo = mapper.volume_id("san-a:vm-101-disk-1.qcow2")
    assert pseudo is not None
    storage_part, _, name_part = pseudo.partition(":")
    assert storage_part == mapper.storage("san-a")
    assert name_part == f"vm-{mapper.vmid(101)}-disk-1.qcow2"


def test_volume_id_preserves_a_format_extension_on_the_fallback_shapes() -> None:
    mapper = make_mapper()
    mapper.register_vmids([101])
    base = mapper.volume_id("san-a:base-101-disk-0.qcow2")
    assert base is not None and base.endswith(".qcow2")
    cloudinit = mapper.volume_id("san-a:vm-101-cloudinit.raw")
    assert cloudinit is not None and cloudinit.endswith("-cloudinit.raw")


# --------------------------------------------------------------------- upid


REAL_SHAPED_UPID = "UPID:pve01:00001234:0000ABCD:5F123456:qmmove:101:drs@pve!claude:"


def test_upid_round_trips_shape() -> None:
    mapper = make_mapper()
    mapper.register_vmids([101])
    pseudo = mapper.upid(REAL_SHAPED_UPID)
    assert pseudo is not None
    parts = pseudo.split(":")
    assert parts[0] == "UPID"
    assert parts[1] == mapper.node("pve01")
    assert parts[5] == "qmmove"
    assert parts[6] == str(mapper.vmid(101))
    assert parts[7].endswith("@pve!claude")
    assert parts[-1] == ""  # trailing colon preserved


def test_upid_unknown_node_drops() -> None:
    mapper = make_mapper(nodes=frozenset({"pve02"}))
    mapper.register_vmids([101])
    assert mapper.upid(REAL_SHAPED_UPID) is None


def test_upid_unregistered_vmid_drops() -> None:
    mapper = make_mapper()
    assert mapper.upid(REAL_SHAPED_UPID) is None


def test_upid_malformed_string_drops() -> None:
    mapper = make_mapper()
    assert mapper.upid("not-a-upid-at-all") is None


def test_upid_non_vm_scoped_task_keeps_empty_id() -> None:
    mapper = make_mapper()
    upid = "UPID:pve01:00001234:0000ABCD:5F123456:vzdump::drs@pve:"
    pseudo = mapper.upid(upid)
    assert pseudo is not None
    assert pseudo.split(":")[6] == ""


def test_upid_matches_crashrecovery_grammar() -> None:
    """anonymize.py's own UPID split must accept exactly what
    crashrecovery.parse_upid() accepts -- both are reading the same real
    grammar, confirmed live (see the project's own dev-cluster-access
    development notes)."""
    from proxmox_storage_drs.crashrecovery import parse_upid

    info = parse_upid(REAL_SHAPED_UPID)
    assert info is not None
    assert info.node == "pve01"
    assert info.vmid == 101
    assert info.user == "drs@pve!claude"

    mapper = make_mapper()
    mapper.register_vmids([101])
    pseudo = mapper.upid(REAL_SHAPED_UPID)
    assert pseudo is not None
    reparsed = parse_upid(pseudo)
    assert reparsed is not None
    assert reparsed.vmid == mapper.vmid(101)


@pytest.mark.parametrize("current_epoch", [time.time()])
def test_mapper_post_init_computes_time_offset(current_epoch: float) -> None:
    mapper = a.Mapper(salt=SALT_A, capture_start_epoch=current_epoch)
    assert mapper.time_offset_seconds == a.week_aligned_offset_seconds(current_epoch)
