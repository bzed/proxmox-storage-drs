# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pure allowlist + pseudonym implementation for diagnostic bundles.

See IMPLEMENTATION_PLAN.md section 16.3. This module is deliberately pure --
no I/O beyond the two small salt-file helpers, which are the one place this
module touches a filesystem, and even those never touch the network or a
bundle. It is the single implementation :mod:`proxmox_storage_drs.collect`
(the collector) and ``tests/corpus/validate_corpus.py`` (the scrub audit)
both import, so the audit cannot drift from what the collector permits
(section 16.3: "The allowlist is derived from pve.py's own accessors and is
the single implementation... shared by the collector and the corpus scrub
audit").

Two independent mechanisms, used together by every caller:

1. **Allowlists** (``*_FIELDS`` constants + :func:`filter_allowed_fields`):
   a field reaches a bundle only if it is named here. Not "every field
   except the sensitive ones" -- every field the engine actually reads
   (``pve.py``, ``topology.py``, ``crashrecovery.py``), and nothing else.
2. **Pseudonyms** (:class:`Mapper`): a keyed, salted, one-way mapping from a
   real identifier to a structurally-similar fake one, stable for the life
   of the salt. :func:`pseudonym` is the primitive; ``Mapper``'s methods are
   the per-kind rules of section 16.3's table.

Timestamp rebasing (:func:`week_aligned_offset_seconds`,
:meth:`Mapper.rebase_timestamp`) is a third, independent transform: it
preserves hour-of-day and day-of-week (what the seasonal forecasters of
section 10.1 need to learn from) while discarding the absolute date.

**Unmapped means dropped, always.** Every ``Mapper`` method that cannot
resolve its input to something it already knows about returns ``None``
rather than inventing a mapping or passing the original through -- callers
must drop the containing record on ``None``, never substitute a placeholder
that looks like real data.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import stat
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from typing import Mapping as MappingType

from proxmox_storage_drs.exceptions import BundleError
from proxmox_storage_drs.topology import DISK_KEY_RE, parse_disk_spec

# --------------------------------------------------------------- allowlists
#
# One frozenset per PVE object shape this codebase's read path (pve.py's own
# accessors, topology.py, crashrecovery.py) treats as meaningful. A key not
# listed here never reaches a bundle, regardless of what a future PVE
# release adds to the same endpoint.

#: ``GET /storage`` (pve.py's ``storage_definitions()``). Section 3.5/16.3:
#: PVE also returns fingerprint/password/encryption-key/keyring/server/
#: portal/target/export/monhost/username/options/comment -- none of them
#: read by this codebase, none of them allowed through.
STORAGE_DEFINITION_FIELDS = frozenset(
    {
        "storage",
        "type",
        "content",
        "shared",
        "nodes",
        "disable",
        "saferemove",
        "saferemove_throughput",
    }
)

#: ``GET /cluster/resources?type=storage`` (``storage_resources()``):
#: ``_pick_active_node()`` reads ``storage``/``status``/``node`` only.
STORAGE_RESOURCE_FIELDS = frozenset({"storage", "status", "node"})

#: ``GET /nodes/{node}/storage/{storage}/status`` (``storage_status()``):
#: the reserve/capacity model reads ``total``/``used`` only (section 5.1).
STORAGE_STATUS_FIELDS = frozenset({"total", "used"})

#: ``GET /nodes/{node}/storage/{storage}/content`` (``storage_content()``):
#: volume identity, owner, and the two competing size sources of section 3.5.
STORAGE_CONTENT_FIELDS = frozenset({"volid", "vmid", "size", "approximate-size", "format"})

#: ``GET /cluster/resources?type=vm`` (``vm_resources()``): inventory fields
#: ``build_topology()`` actually reads. ``name`` is carried only as the
#: config-name fallback's *source*; the value itself is free text and is
#: replaced, never passed through (section 16.3's per-kind table).
VM_RESOURCE_FIELDS = frozenset({"vmid", "node", "status", "type", "name", "tags"})

#: ``GET /nodes/{node}/qemu/{vmid}/config`` (``vm_config()``): ``lock`` and
#: ``template`` plus every disk key matching ``topology.DISK_KEY_RE``
#: (section 3.5's bus regex) -- the disk *keys* are allowed here;
#: :func:`filter_disk_value` governs what survives inside each disk's own
#: value string. ``name`` is the free-text VM name, handled like the
#: resource-list one above.
VM_CONFIG_EXTRA_FIELDS = frozenset({"lock", "template", "name"})

#: Sub-fields of one disk value (``storage:volid,size=...,...``) that
#: survive re-serialization -- section 16.3: "parsed into its volume id,
#: size, format and media and re-serialized from those four". Everything
#: else in the value (``iothread``, ``discard``, ...) is dropped because
#: nothing reads it.
DISK_VALUE_FIELDS = frozenset({"size", "format", "media"})

#: ``GET /nodes/{node}/qemu/{vmid}/snapshot``: only whether an entry is the
#: ``"current"`` pseudo-entry matters (section 3.7's per-volume detection
#: counts real entries); the snapshot's own name is free text and is never
#: carried through as anything but a fixed placeholder -- see
#: :func:`sanitize_snapshot_name`.
VM_SNAPSHOT_FIELDS = frozenset({"name"})

#: ``GET .../status/current`` (``vm_status_current()``): ``lock`` only
#: (section 9.3).
VM_STATUS_CURRENT_FIELDS = frozenset({"lock"})

#: ``GET /cluster/tasks`` (``cluster_tasks()``): the shape ``pve.py``'s own
#: docstring documents and section 13's crash-recovery scan reads (``type``,
#: ``user``, ``endtime``, ``status``, ``upid`` directly; ``node``/``id`` are
#: also part of the documented per-entry shape even though the scan itself
#: recovers them by parsing the embedded UPID instead).
CLUSTER_TASK_FIELDS = frozenset(
    {"node", "type", "id", "upid", "user", "starttime", "endtime", "status"}
)

#: ``GET /nodes`` (``node_names()``): only the ``node`` key.
NODE_LIST_FIELDS = frozenset({"node"})


def filter_allowed_fields(obj: MappingType[str, Any], allowed: frozenset[str]) -> dict[str, Any]:
    """Drop every key of ``obj`` not in ``allowed``. The one primitive both
    the collector and the scrub audit use -- see this module's docstring."""
    return {key: value for key, value in obj.items() if key in allowed}


def filter_disk_value_params(params: MappingType[str, str]) -> dict[str, str]:
    """The allowlisted subset of a disk value's ``key=value`` parameters
    (``DISK_VALUE_FIELDS``) -- ``iothread=1,discard=on,...`` never survives."""
    return {key: value for key, value in params.items() if key in DISK_VALUE_FIELDS}


def filter_vm_config_fields(raw_config: MappingType[str, Any]) -> dict[str, Any]:
    """``VM_CONFIG_EXTRA_FIELDS`` plus every disk key matching
    ``topology.DISK_KEY_RE`` (section 3.5's bus regex) -- the one place both
    allowlists that make up a VM config's own top level are applied
    together, so the collector and the scrub audit share this instead of
    each re-deriving it."""
    return {
        key: value
        for key, value in raw_config.items()
        if key in VM_CONFIG_EXTRA_FIELDS or DISK_KEY_RE.match(key)
    }


def sanitize_snapshot_name(name: str) -> str:
    """The one meaningful value a snapshot ``name`` field can carry is the
    literal sentinel ``"current"`` (section 3.7's own-VM-snapshot pseudo
    -entry) -- everything else is an operator-chosen, free-text snapshot
    name (section 16.3's per-kind table: "dropped") and becomes this fixed
    placeholder instead, so a real snapshot's *existence* still counts
    toward section 3.7's pinning without naming it."""
    return "current" if name == "current" else "snapshot"


# ----------------------------------------------------------------- pseudonym

_PSEUDONYM_HEX_LEN = 8  # 4 bytes -- section 16.3's "-<8 hex>" grammar throughout
_SALT_FINGERPRINT_KIND = "drs-salt-fingerprint"


def pseudonym(salt: bytes, kind: str, value: str) -> str:
    """``HMAC-SHA256(salt, kind || "\\0" || value)``, truncated to 8 hex
    chars. ``kind`` keeps a node and a storage that happen to share a name
    from colliding into one pseudonym -- section 16.3."""
    digest = hmac.new(salt, kind.encode("utf-8") + b"\0" + value.encode("utf-8"), hashlib.sha256)
    return digest.hexdigest()[:_PSEUDONYM_HEX_LEN]


def _pseudonym_int(salt: bytes, kind: str, value: str, modulus: int) -> int:
    digest = hmac.new(salt, kind.encode("utf-8") + b"\0" + value.encode("utf-8"), hashlib.sha256)
    return int.from_bytes(digest.digest(), "big") % modulus


def _check_no_pseudonym_collision(salt: bytes, kind: str, values: Iterable[str]) -> None:
    """32-bit (8 hex char) truncation makes a same-``kind`` collision
    astronomically unlikely for real cluster sizes (~n^2/2^33) but not
    impossible, and nothing checked for one outside ``Mapper.vmid()``'s own
    linear probing (X-09) -- two nodes or two storages colliding would
    silently merge into one record in the bundle (same file name, same
    ``groups[].storages[].id``) rather than failing loudly. ``values`` is
    always a small, finite, already-known set (``known_nodes``/
    ``known_storages``), so this costs nothing worth measuring."""
    seen: dict[str, str] = {}
    for value in values:
        digest = pseudonym(salt, kind, value)
        collision = seen.get(digest)
        if collision is not None and collision != value:
            raise BundleError(
                f"anonymization collision: {kind}s {value!r} and {collision!r} hash to the "
                f"same pseudonym ({digest!r}) -- capture refused rather than silently merging "
                "them in the bundle. This should not happen for a real cluster's node/storage "
                "count; if it does, rotate the salt (--new-salt) and try again."
            )
        seen[digest] = value


def salt_fingerprint(salt: bytes) -> str:
    """A value two bundles can compare to prove they share a mapping,
    without revealing the salt or letting anyone test a guess against it
    (section 16.3)."""
    return hmac.new(salt, _SALT_FINGERPRINT_KIND.encode("ascii"), hashlib.sha256).hexdigest()


def load_or_create_salt(path: str | Path) -> bytes:
    """Read the persisted salt at ``path``, creating it (32 bytes of
    ``os.urandom()``, mode 0600) if it does not exist yet. Never logs or
    returns anything that would let the salt leak into a bundle -- callers
    must keep it out of every written structure except via
    :func:`salt_fingerprint`."""
    salt_path = Path(path)
    try:
        data = salt_path.read_bytes()
    except FileNotFoundError:
        return generate_new_salt(salt_path)
    if len(data) < 32:
        raise ValueError(f"salt file {salt_path} is truncated ({len(data)} bytes, need >= 32)")
    return data


def generate_new_salt(path: str | Path) -> bytes:
    """Generate and persist a fresh 32-byte salt at ``path``, overwriting
    any existing one -- ``--new-salt``. The caller is responsible for
    logging the rotation at warning level (section 16.3: "bundles made
    before and after no longer share a mapping")."""
    salt_path = Path(path)
    salt_path.parent.mkdir(parents=True, exist_ok=True)
    salt = os.urandom(32)
    fd = os.open(salt_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, salt)
    finally:
        os.close(fd)
    os.chmod(salt_path, stat.S_IRUSR | stat.S_IWUSR)
    return salt


# -------------------------------------------------------------------- clock
#
# "Timestamps are rebased" (section 16.3): every absolute timestamp in a
# bundle is shifted by a single per-bundle offset, chosen so the shift is an
# exact multiple of one week -- that preserves hour-of-day and day-of-week
# for every timestamp (what the seasonal forecasters need) while discarding
# the real date. The reference epoch is an arbitrary fixed Monday; only the
# *offset* it produces matters, never the reference date itself.

_SYNTHETIC_REFERENCE_EPOCH = datetime(2000, 1, 3, tzinfo=timezone.utc).timestamp()  # a Monday
_WEEK_SECONDS = 7 * 86400.0


def week_aligned_offset_seconds(
    capture_start_epoch: float, reference_epoch: float = _SYNTHETIC_REFERENCE_EPOCH
) -> float:
    """The single per-bundle offset :meth:`Mapper.rebase_timestamp` applies:
    the largest whole-week shift that brings ``capture_start_epoch`` to
    within one week of ``reference_epoch``, so every rebased timestamp keeps
    its hour-of-day and day-of-week exactly."""
    weeks = (capture_start_epoch - reference_epoch) // _WEEK_SECONDS
    return weeks * _WEEK_SECONDS


# ------------------------------------------------------------------- Mapper

#: PVE's own `get_next_vm_diskname()` appends a literal `.<format>` suffix
#: to the volume *name itself* (not just the disk value's separate
#: `format=` param) whenever the volume isn't the storage type's own raw
#: default -- confirmed against a real cluster's qcow2-on-shared-LVM volumes
#: (`vm-101-disk-1.qcow2`; `topology.py`'s own `_resolve_disk_size_and_format`
#: docstring already names this PVE 9.2+ feature). Optional and captured so
#: :meth:`Mapper.volume_id` can re-attach it verbatim -- it is a structural
#: format marker, not free text, and dropping it would leave the
#: reconstructed volid unable to match its own storage-content listing entry
#: at replay time.
_VOLUME_EXT_RE = r"(?P<ext>\.[a-zA-Z0-9]+)?"
_VOLUME_ID_RE = re.compile(
    rf"^(?P<prefix>vm|base)-(?P<vmid>\d+)-disk-(?P<index>\d+){_VOLUME_EXT_RE}$"
)
# A narrower fallback for the handful of other PVE-generated shapes this
# tool's own read path can encounter (cloud-init volumes, EFI/TPM state) --
# prefix and vmid are remapped, the fixed suffix is not free text and
# survives verbatim; anything else is dropped (fail closed).
_VOLUME_ID_FALLBACK_RE = re.compile(
    rf"^(?P<prefix>[a-zA-Z]+)-(?P<vmid>\d+)-"
    rf"(?P<suffix>cloudinit|disk-\d+-state-\d+){_VOLUME_EXT_RE}$"
)


@dataclass
class Mapper:
    """The stateful half of anonymization: one instance per bundle capture.

    ``vmid`` is the only kind needing state beyond the salt itself (the
    linear-probe collision rule, section 16.3), so every vmid a bundle will
    ever need to anonymize must be registered up front via
    :meth:`register_vmids` -- this is what makes the result independent of
    the order callers happen to visit VMs in (section 16.3: "Probing walks
    candidates in order of *original* vmid so the result never depends on
    iteration order"). Every other method is a pure function of ``salt``
    plus its own argument and needs no registration.
    """

    salt: bytes
    capture_start_epoch: float
    time_offset_seconds: float = field(init=False)
    known_nodes: frozenset[str] = frozenset()
    known_storages: frozenset[str] = frozenset()
    known_groups: frozenset[str] = frozenset()
    dropped_records: int = field(default=0, init=False)
    _vmid_map: dict[int, int] = field(default_factory=dict, init=False)
    _vmid_taken: set[int] = field(default_factory=set, init=False)

    def __post_init__(self) -> None:
        self.time_offset_seconds = week_aligned_offset_seconds(self.capture_start_epoch)
        # X-09: turns a ~n^2/2^33 silent merge into a loud, named refusal --
        # see _check_no_pseudonym_collision(). Vmid collisions are already
        # impossible by construction (register_vmids()'s own linear probe).
        _check_no_pseudonym_collision(self.salt, "node", self.known_nodes)
        _check_no_pseudonym_collision(self.salt, "storage", self.known_storages)
        _check_no_pseudonym_collision(self.salt, "group", self.known_groups)

    # -------------------------------------------------------------- clock

    def rebase_timestamp(self, epoch_seconds: float) -> float:
        return epoch_seconds - self.time_offset_seconds

    # -------------------------------------------------------------- vmid

    def register_vmids(self, vmids: Iterable[int]) -> None:
        """Assign every not-yet-seen vmid in ``vmids`` its pseudonym,
        processing candidates in ascending order of the *original* vmid
        regardless of the order ``vmids`` itself is given in -- section
        16.3's determinism requirement."""
        for original in sorted(set(vmids) - self._vmid_map.keys()):
            candidate = 100 + _pseudonym_int(self.salt, "vmid", str(original), 899_900)
            while candidate in self._vmid_taken:
                candidate = 100 + ((candidate - 100 + 1) % 899_900)
            self._vmid_taken.add(candidate)
            self._vmid_map[original] = candidate

    def vmid(self, original: int) -> int | None:
        """The pseudonym for a vmid already passed to :meth:`register_vmids`.
        ``None`` for one that was not -- section 16.3's "unmapped means
        dropped", e.g. a foreign volume owned by a VM outside every group."""
        result = self._vmid_map.get(original)
        if result is None:
            self.dropped_records += 1
        return result

    def registered_vmids(self) -> MappingType[int, int]:
        """Every original vmid -> pseudonym pair registered so far. Exposed
        (read-only) for the one caller outside this class with a legitimate
        need to walk the whole mapping rather than look up one vmid at a
        time: redacting a free-text message that might embed a real vmid
        anywhere in it (``collect._redact_free_text``)."""
        return dict(self._vmid_map)

    # ------------------------------------------------------------ simple

    def node(self, name: str) -> str:
        """``node-<8 hex>``, or ``node-<8hex>.<8hex>.invalid`` for an FQDN
        -- shape preserved only for FQDN-ness, so the PromQL dot-escaping
        path stays exercised (section 16.3)."""
        if "." in name:
            host_hex = pseudonym(self.salt, "node", name)
            domain_hex = pseudonym(self.salt, "node-domain", name)
            return f"node-{host_hex}.{domain_hex}.invalid"
        return f"node-{pseudonym(self.salt, 'node', name)}"

    def storage(self, storage_id: str) -> str:
        return f"stor-{pseudonym(self.salt, 'storage', storage_id)}"

    def group(self, name: str) -> str:
        return f"group-{pseudonym(self.salt, 'group', name)}"

    def tag(self, value: str) -> str:
        return f"tag-{pseudonym(self.salt, 'tag', value)}"

    def pool(self, value: str) -> str:
        return f"pool-{pseudonym(self.salt, 'pool', value)}"

    def username(self, value: str) -> str:
        """``user-<8 hex>@realm`` -- only ever seen inside a UPID (section
        16.3). A value with no ``@`` (should not occur for a real PVE
        username) is pseudonymized whole, with no ``@`` appended."""
        user, sep, realm = value.partition("@")
        digest = pseudonym(self.salt, "username", value)
        if not sep:
            return f"user-{digest}"
        return f"user-{digest}@{realm}"

    # ------------------------------------------------------------- volids

    def volume_id(self, volid: str) -> str | None:
        """Rebuild a volume id as ``<storage-pseudonym>:<prefix>-<vmid
        -pseudonym>-disk-<n>[.<ext>]`` (section 16.3) -- the optional
        ``.<ext>`` (e.g. ``.qcow2``) is PVE's own format marker on the
        volume name itself (see ``_VOLUME_EXT_RE``), carried through
        verbatim, never dropped, since it is structural rather than free
        text. ``None`` (record dropped) if the storage is outside every
        group, the owning vmid was never registered, or the volume name
        matches neither the common ``vm``/``base`` disk pattern nor the
        narrow allowlisted fallback."""
        storage_id, volume_name, _params = parse_disk_spec(volid)
        if storage_id not in self.known_storages:
            self.dropped_records += 1
            return None
        new_storage = self.storage(storage_id)

        match = _VOLUME_ID_RE.match(volume_name)
        if match:
            new_vmid = self.vmid(int(match.group("vmid")))
            if new_vmid is None:
                return None
            ext = match.group("ext") or ""
            return (
                f"{new_storage}:{match.group('prefix')}-{new_vmid}-disk-{match.group('index')}{ext}"
            )

        fallback = _VOLUME_ID_FALLBACK_RE.match(volume_name)
        if fallback:
            new_vmid = self.vmid(int(fallback.group("vmid")))
            if new_vmid is None:
                return None
            ext = fallback.group("ext") or ""
            return (
                f"{new_storage}:{fallback.group('prefix')}-{new_vmid}-"
                f"{fallback.group('suffix')}{ext}"
            )

        # "A volume whose name does not match the pattern keeps only its
        # prefix and index" (section 16.3) -- there is no safe generic
        # prefix/index to extract from an arbitrary name, so fail closed.
        self.dropped_records += 1
        return None

    # --------------------------------------------------------------- upid

    def upid(self, value: str) -> str | None:
        """Rebuild ``UPID:{node}:{pid}:{pstart}:{starttime}:{type}:{id}:{user}:``
        (the grammar :mod:`proxmox_storage_drs.crashrecovery` confirmed
        against a live cluster) with ``node``/``id``/``user`` mapped,
        ``starttime`` rebased, and ``pid``/``pstart`` replaced by fixed
        constants -- they identify a process on a named host and nothing
        the engine reads (section 16.3). ``None`` if the node is unknown,
        the string does not parse as a UPID at all, or ``id`` is a vmid
        that was never registered."""
        parts = value.split(":")
        if len(parts) < 8 or parts[0] != "UPID":
            self.dropped_records += 1
            return None
        node, _pid, _pstart, starttime, task_type, task_id, user = parts[1:8]
        if node not in self.known_nodes:
            self.dropped_records += 1
            return None
        new_id = ""
        if task_id:
            if not task_id.isdigit():
                self.dropped_records += 1
                return None
            new_vmid = self.vmid(int(task_id))
            if new_vmid is None:
                return None
            new_id = str(new_vmid)
        try:
            new_starttime = f"{self.rebase_timestamp(float(int(starttime, 16))):08x}"
        except ValueError:
            new_starttime = starttime
        return (
            f"UPID:{self.node(node)}:00000000:00000000:{new_starttime}:"
            f"{task_type}:{new_id}:{self.username(user)}:"
        )
