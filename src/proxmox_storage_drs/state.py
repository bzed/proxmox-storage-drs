# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Persistent state at ``state.path``. See IMPLEMENTATION_PLAN.md section 11.2.

The only thing this tool remembers between runs: the load vector as of the
last *executed* balance (drift, section 6), per-disk/per-storage cooldown
timestamps (section 5.3 (C2)), in-flight migration UPIDs and staged disks
(both section 9 -- `execute.py` exists now, but neither crash recovery nor
staging is implemented yet, so nothing writes or reads these two fields),
and a node-local advisory lock. Local disk, one copy per host, deliberately
never `/etc/pve` (`.agents/domain-invariants.md` section 9: "state belongs
in `state.path` on local disk").

**Reading degrades, writing does not.** A missing file is the normal,
expected first-run state (:func:`load_state` returns :func:`empty_state`
silently); a present-but-corrupt or wrong-schema-version file logs a
warning and *also* degrades to :func:`empty_state`, rather than failing the
whole run -- section 11.2's own words are "losing this file is safe but
not free: cooldowns and drift history reset". This mirrors ``show-load``'s
choice to degrade rather than fail on a Prometheus outage (an essential
*input* -- config, or an explicitly-named `-c PATH` -- is a hard failure on
error, per `.agents/domain-invariants.md` section 9; this file is neither).
:func:`save_state_atomic` and the lock functions, by contrast, raise
:class:`~proxmox_storage_drs.exceptions.StateError` on failure -- those are
things the caller actively asked this module to do, not a read whose
absence has a well-defined fallback.

**Locking**: :func:`acquire_lock` takes a real ``fcntl.flock(LOCK_EX |
LOCK_NB)`` on the state file itself -- the actual, kernel-enforced mutual
exclusion section 11.2 asks for, correct by construction for two instances
on the *same host* (`.agents/domain-invariants.md` section 9: "the `fcntl`
lock cannot see another node" -- cross-node coordination is the separate
UPID scan, section 13, not this module's job). The `lock` field recorded
inside the JSON itself (pid/host/acquired-at) is **descriptive metadata for
an operator reading the file**, not the mechanism: by the time this
module's code overwrites it, the OS has already granted exclusive
ownership, so whatever a previous run last wrote there is necessarily
stale and is unconditionally replaced. Section 11.2's "if `lock.pid` is not
alive on `lock.host`, reclaim it" is naturally satisfied by this design
too -- a process that died released its `flock()` when its file
descriptor closed (on any exit, including a crash), so the *next*
`acquire_lock()` call simply succeeds; there is no separate liveness check
to get right or get wrong. ``acquire_lock()`` returns ``None`` (not an
exception) when another live instance holds it, matching section 11.2's "a
live PID means another instance is running: exit 0 quietly" -- the
caller's job, not this module's, to decide what "quietly" means for its
own command.

**`cli.py`'s ``apply`` is the one caller of the write side** (:func:`acquire_lock`,
:func:`with_recorded_balance`, :func:`with_recorded_cooldown`,
:func:`save_locked_state`, :func:`release_lock`) -- `plan`/`show-load`
never execute a migration, so section 11.2's "updated only after a run
that executed at least one migration" means they must never call it, and
taking the exclusive lock for a read-only report would make an
in-progress `apply` block `plan`/`show-load` for no safety reason this
codebase can find in the plan text. Cooldowns are stored, round-tripped
and queryable (:func:`active_disk_cooldowns`/:func:`active_storage_cooldowns`),
and both `topology.py` (the (C2) per-disk pin) and `heuristic.py` (the
per-storage target exclusion) consume them -- see
``docs/internals/15-state.md`` and ``docs/internals/92-execute.md`` for
the full wiring and its one deliberate asymmetry (repair moves ignore the
storage cooldown; nothing yet exempts a disk-cooldown pin the same way).
A group `apply` never acts on leaves its cooldowns/`last_balance` exactly
as they were before that run.
"""

from __future__ import annotations

import contextlib
import errno
import fcntl
import json
import logging
import os
import socket
import tempfile
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Mapping

from proxmox_storage_drs.exceptions import StateError

logger = logging.getLogger(__name__)

STATE_SCHEMA_VERSION = 1


def now_iso() -> str:
    """UTC, second precision, ``Z`` suffix -- exactly section 11.2's own
    example timestamps (``"2026-09-04T02:00:00Z"``), never a `+00:00`
    offset form."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True, slots=True)
class LockInfo:
    """Descriptive only -- see the module docstring's "Locking" section for
    why the real exclusion is `flock()`, not this."""

    pid: int
    host: str
    acquired_at: str


@dataclass(frozen=True, slots=True)
class LastBalance:
    """``at`` is ``None`` before any run has ever executed a migration --
    distinct from an empty ``load_vector``, which can happen even after a
    real balance if every disk it touched has since been re-balanced away
    from (section 11.2: "updated only after a run that executed at least
    one migration")."""

    at: str | None = None
    load_vector: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Cooldowns:
    disk: Mapping[str, str] = field(default_factory=dict)
    storage: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class State:
    schema_version: int = STATE_SCHEMA_VERSION
    lock: LockInfo | None = None
    last_balance: LastBalance = field(default_factory=LastBalance)
    cooldowns: Cooldowns = field(default_factory=Cooldowns)
    inflight_upids: tuple[str, ...] = ()
    staged_disks: tuple[str, ...] = ()


def empty_state() -> State:
    """First-run state: no lock, no recorded balance, no cooldowns, nothing
    in flight -- exactly what a missing or unreadable ``state.path``
    degrades to."""
    return State()


# ------------------------------------------------------------------- keys


def disk_state_key(group: str, vmid: int, device: str) -> str:
    """``"<group>:<vmid>:<device>"`` (section 11.2) -- the group prefix is
    what keeps a vmid reused after a VM is destroyed and recreated in a
    *different* group from colliding with its old entry.
    ``topology.Disk.key`` is already ``"<vmid>:<device>"`` (see that
    module's own comment pointing here), so this is always
    ``f"{group}:{disk.key}"`` in practice."""
    return f"{group}:{vmid}:{device}"


def storage_state_key(group: str, storage_id: str) -> str:
    """``"<group>:<storage>"`` (section 11.2)."""
    return f"{group}:{storage_id}"


# --------------------------------------------------------- (de)serialization


def _state_to_dict(state: State) -> dict[str, Any]:
    lock_out = None
    if state.lock is not None:
        lock_out = {
            "pid": state.lock.pid,
            "host": state.lock.host,
            "acquired_at": state.lock.acquired_at,
        }
    return {
        "schema_version": state.schema_version,
        "lock": lock_out,
        "last_balance": {
            "at": state.last_balance.at,
            "load_vector": dict(state.last_balance.load_vector),
        },
        "cooldowns": {
            "disk": dict(state.cooldowns.disk),
            "storage": dict(state.cooldowns.storage),
        },
        "inflight_upids": list(state.inflight_upids),
        "staged_disks": list(state.staged_disks),
    }


def _state_from_dict(data: dict[str, Any]) -> State:
    """Raises on any shape this module does not recognize -- the caller
    (:func:`load_state`) is what turns that into "log and degrade", so this
    function itself can stay strict and easy to reason about."""
    schema_version = data["schema_version"]
    if schema_version != STATE_SCHEMA_VERSION:
        raise ValueError(f"unsupported state schema_version {schema_version!r}")

    lock = None
    lock_raw = data.get("lock")
    if lock_raw is not None:
        lock = LockInfo(
            pid=int(lock_raw["pid"]),
            host=str(lock_raw["host"]),
            acquired_at=str(lock_raw["acquired_at"]),
        )

    balance_raw = data.get("last_balance") or {}
    last_balance = LastBalance(
        at=balance_raw.get("at"),
        load_vector={
            str(key): float(value) for key, value in (balance_raw.get("load_vector") or {}).items()
        },
    )

    cooldowns_raw = data.get("cooldowns") or {}
    cooldowns = Cooldowns(
        disk={str(k): str(v) for k, v in (cooldowns_raw.get("disk") or {}).items()},
        storage={str(k): str(v) for k, v in (cooldowns_raw.get("storage") or {}).items()},
    )

    return State(
        schema_version=schema_version,
        lock=lock,
        last_balance=last_balance,
        cooldowns=cooldowns,
        inflight_upids=tuple(data.get("inflight_upids") or ()),
        staged_disks=tuple(data.get("staged_disks") or ()),
    )


# --------------------------------------------------------------- read/write


def _parse_state_text(text: str, path: str) -> State:
    """The tolerant-parse half of :func:`load_state`, factored out so
    :func:`acquire_lock` can apply the identical "degrade and warn, never
    raise" rule to the content it reads through the already-open, already
    -locked fd (AGENTS.md section 5: one implementation). An empty string
    -- a file just created by ``O_CREAT``, or a genuinely empty pre
    -existing one -- is the ordinary "nothing recorded yet" case, exactly
    like a missing file, not something to warn about."""
    if text.strip() == "":
        return empty_state()
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning(
            "state file %s is not valid JSON, proceeding as if it were absent: %s",
            path,
            exc,
            extra={"event": "state_corrupt", "path": path},
        )
        return empty_state()
    try:
        return _state_from_dict(raw)
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning(
            "state file %s has an unexpected shape, proceeding as if it were absent: %s",
            path,
            exc,
            extra={"event": "state_corrupt", "path": path},
        )
        return empty_state()


def load_state(path: str) -> State:
    """Best-effort read of ``path``. See the module docstring: a missing
    file is the ordinary first-run case (silent); an unreadable or
    unrecognizable one is logged at warning and *also* treated as absent
    -- never raised, and never a reason to fail ``show-load``/``plan``."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except FileNotFoundError:
        return empty_state()
    except OSError as exc:
        logger.warning(
            "could not read state file %s, proceeding as if it were absent: %s",
            path,
            exc,
            extra={"event": "state_read_failed", "path": path},
        )
        return empty_state()
    return _parse_state_text(text, path)


def save_state_atomic(path: str, state: State) -> None:
    """Temp file in the same directory, ``fsync``, then ``os.replace`` --
    a reader (:func:`load_state`) can never observe a half-written file,
    which is what lets reads skip locking entirely (see the module
    docstring). Creates ``path``'s parent directory if missing (a fresh
    install's ``/var/lib/pve-storage-drs`` may not exist yet). Raises
    :class:`StateError` on any failure -- unlike :func:`load_state`, this
    is something the caller asked this module to do, not a read with a
    documented fallback."""
    directory = os.path.dirname(path) or "."
    tmp_path: str | None = None
    try:
        os.makedirs(directory, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(prefix=".state-", suffix=".tmp", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(_state_to_dict(state), fh, indent=2, sort_keys=True)
                fh.write("\n")
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_path, path)
            tmp_path = None
        finally:
            if tmp_path is not None:
                with contextlib.suppress(OSError):
                    os.remove(tmp_path)
    except OSError as exc:
        raise StateError(f"could not write state file {path!r}: {exc}") from exc


# --------------------------------------------------------- last_balance


def load_vector_for_group(state: State, group_name: str) -> dict[str, float] | None:
    """This group's slice of ``last_balance.load_vector``, re-keyed from
    ``"<group>:<vmid>:<device>"`` down to bare ``topology.Disk.key``
    (``"<vmid>:<device>"``) -- exactly the shape
    ``loadmodel.compute_group_load()``'s ``last_known_loads`` and
    ``gates.evaluate_group_gates()``'s ``last_load`` both expect.

    Returns ``None``, not ``{}``, when this group has no entries at all --
    ``gates.py``'s own contract for ``last_load`` is that ``None`` means "no
    such run has ever happened" (skip the drift gate outright), which is
    different from "a run happened and recorded zero load everywhere"."""
    prefix = f"{group_name}:"
    entries = {
        key[len(prefix) :]: value
        for key, value in state.last_balance.load_vector.items()
        if key.startswith(prefix)
    }
    return entries or None


def with_recorded_balance(
    state: State, group_name: str, load_by_key: Mapping[str, float], at: str | None = None
) -> State:
    """Pure: a new :class:`State` with ``group_name``'s slice of
    ``last_balance.load_vector`` replaced by ``load_by_key`` (every other
    group's entries untouched) and ``last_balance.at`` bumped to ``at``
    (``now_iso()`` if not given). For `execute.py` (not yet written) to
    call once a run has executed at least one migration for this group
    (section 11.2) -- not called by anything today, see the module
    docstring."""
    prefix = f"{group_name}:"
    kept = {k: v for k, v in state.last_balance.load_vector.items() if not k.startswith(prefix)}
    updated_vector = {**kept, **{f"{prefix}{key}": value for key, value in load_by_key.items()}}
    return replace(state, last_balance=LastBalance(at=at or now_iso(), load_vector=updated_vector))


# ----------------------------------------------------------------- cooldowns


def with_recorded_cooldown(
    state: State,
    *,
    disk_keys: Mapping[str, str] | None = None,
    storage_keys: Mapping[str, str] | None = None,
) -> State:
    """Pure: merges new disk/storage cooldown timestamps into ``state``,
    keyed exactly as :func:`disk_state_key`/:func:`storage_state_key`
    produce them. Called by `cli.py`'s `_handle_apply()` for every disk
    and **both storage endpoints** of an executed move (section 6: "a
    storage involved in a migration ... accepts no new incoming moves"
    covers source and destination alike; REVIEW.md S-03) -- recording
    both is independent of `heuristic.py`'s own *enforcement*, which
    stays destination-only (see ``docs/internals/90-heuristic.md``)."""
    disk = {**state.cooldowns.disk, **(disk_keys or {})}
    storage = {**state.cooldowns.storage, **(storage_keys or {})}
    return replace(state, cooldowns=Cooldowns(disk=disk, storage=storage))


def _parse_iso(timestamp: str) -> datetime | None:
    """Inverse of :func:`now_iso`. Returns ``None`` on anything that does
    not parse -- a hand-edited or otherwise foreign timestamp in
    ``cooldowns.disk``/``.storage`` must degrade to "no active cooldown",
    not crash a ``show-load``/``plan`` run, matching this module's
    read-side philosophy everywhere else (see the module docstring)."""
    try:
        return datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def cooldown_remaining_seconds(
    cooldowns: Mapping[str, str], key: str, cooldown_seconds: float, now: datetime
) -> float:
    """Seconds left in ``key``'s cooldown -- ``0.0`` if nothing is recorded
    for it, its timestamp does not parse, or it has already expired.
    ``cooldowns`` is ``state.cooldowns.disk`` or ``state.cooldowns.storage``;
    ``key`` is exactly what :func:`disk_state_key`/:func:`storage_state_key`
    produce. The one implementation of the expiry arithmetic (AGENTS.md
    section 5) both :func:`active_disk_cooldowns` and
    :func:`active_storage_cooldowns` build on."""
    recorded = cooldowns.get(key)
    if recorded is None:
        return 0.0
    parsed = _parse_iso(recorded)
    if parsed is None:
        return 0.0
    elapsed = (now - parsed).total_seconds()
    return max(cooldown_seconds - elapsed, 0.0)


def _active_cooldowns(
    cooldowns: Mapping[str, str], group_name: str, cooldown_seconds: float, now: datetime
) -> dict[str, float]:
    if cooldown_seconds <= 0:
        return {}  # section 11: a `0` cooldown disables the check, not "always in cooldown"
    prefix = f"{group_name}:"
    result: dict[str, float] = {}
    for key in cooldowns:
        if not key.startswith(prefix):
            continue
        remaining = cooldown_remaining_seconds(cooldowns, key, cooldown_seconds, now)
        if remaining > 0:
            result[key[len(prefix) :]] = remaining
    return result


def active_disk_cooldowns(
    state: State, group_name: str, cooldown_seconds: float, now: datetime
) -> dict[str, float]:
    """This group's disks still within ``gates.cooldown_per_disk_seconds``,
    keyed by bare ``topology.Disk.key`` (mirrors
    :func:`load_vector_for_group`'s own prefix-stripping) -> seconds
    remaining. Empty when the cooldown is disabled (``<= 0``) or nothing is
    recorded. For `topology.py`'s (C2) "within its per-disk cooldown ->
    pin to current" -- see ``docs/internals/15-state.md``."""
    return _active_cooldowns(state.cooldowns.disk, group_name, cooldown_seconds, now)


def active_storage_cooldowns(
    state: State, group_name: str, cooldown_seconds: float, now: datetime
) -> dict[str, float]:
    """This group's storages still within
    ``gates.cooldown_per_storage_seconds``, keyed by bare storage id ->
    seconds remaining. Empty when the cooldown is disabled (``<= 0``) or
    nothing is recorded. For `heuristic.py`'s "a storage involved in a
    migration within `cooldown_per_storage` accepts no new incoming moves"
    -- see ``docs/internals/15-state.md``."""
    return _active_cooldowns(state.cooldowns.storage, group_name, cooldown_seconds, now)


# --------------------------------------------------------------------- lock


def _pid_alive(pid: int) -> bool:
    """Best-effort, used only to make a "still held" log message useful to
    an operator -- the actual acquire/release decision never depends on
    this (see the module docstring's "Locking" section)."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        # Exists but owned by someone else (EPERM) -- alive either way.
        return True
    return True


@dataclass(frozen=True, slots=True)
class LockHandle:
    """Opaque -- pass to :func:`release_lock`. The open file descriptor is
    what actually holds the ``flock()``; do not construct this directly."""

    _fd: int
    _path: str


def _write_state_to_locked_fd(fd: int, state: State) -> None:
    """Writes ``state`` **in place** into the already-open, already-locked
    ``fd`` -- never via :func:`save_state_atomic`'s temp-file-plus-rename,
    which replaces the directory entry with a *new* inode the lock was
    never taken on, silently turning the held ``flock()`` into a lock on a
    file nothing points to any more (found by
    ``test_a_second_acquire_while_the_first_is_held_returns_none`` failing:
    a second `acquire_lock()` opened the post-rename inode fresh and
    locked it with no conflict at all). Truncating to the new, shorter
    payload length matters just as much as writing the longer one -- a
    stale tail from a previous, larger write must not survive."""
    payload = (json.dumps(_state_to_dict(state), indent=2, sort_keys=True) + "\n").encode("utf-8")
    os.lseek(fd, 0, os.SEEK_SET)
    os.write(fd, payload)
    os.ftruncate(fd, len(payload))
    os.fsync(fd)


def _read_locked_state(fd: int, path: str) -> State:
    """Re-reads whatever is currently written through an already-open,
    already-``flock()``'d fd -- the one implementation of that (AGENTS.md
    section 5) shared by :func:`acquire_lock`, :func:`release_lock` and
    :func:`save_locked_state`, all of which must read through the locked
    fd itself rather than :func:`load_state` (which reopens ``path`` by
    name, a distinct, unlocked file descriptor)."""
    os.lseek(fd, 0, os.SEEK_SET)
    chunks = []
    while chunk := os.read(fd, 65536):
        chunks.append(chunk)
    return _parse_state_text(b"".join(chunks).decode("utf-8"), path)


def acquire_lock(path: str) -> LockHandle | None:
    """Section 11.2's advisory lock: ``fcntl.flock(LOCK_EX | LOCK_NB)`` on
    ``path`` itself, non-blocking -- never sleeps and retries (no
    `time.sleep`, per `.agents/testing.md`'s "inject the clock": there is
    nothing to inject here because there is no wait loop). Returns ``None``
    when another live instance already holds it (section 11.2: "a live PID
    means another instance is running: exit 0 quietly" -- deciding what
    "quietly" means, and for which exit code, is the caller's job).
    Creates ``path`` (empty state) if it does not exist yet, so the very
    first ``apply``/``auto`` run on a fresh install can still take the
    lock. Raises :class:`StateError` for any other failure (permission
    denied, read-only filesystem, ...)."""
    directory = os.path.dirname(path) or "."
    try:
        os.makedirs(directory, exist_ok=True)
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    except OSError as exc:
        raise StateError(f"could not open state file {path!r} for locking: {exc}") from exc

    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        os.close(fd)
        if exc.errno in (errno.EACCES, errno.EAGAIN):
            return None
        raise StateError(  # pragma: no cover - flock(2) only ever fails EACCES/EAGAIN for LOCK_NB
            f"could not lock state file {path!r}: {exc}"
        ) from exc

    # We now hold exclusive OS-level ownership -- whatever `lock` metadata
    # a previous run left behind is necessarily stale (see module
    # docstring), so it is unconditionally overwritten, never inspected for
    # a liveness decision. Read and (below) write through `fd` itself, not
    # `load_state()`/`save_state_atomic()` -- the latter renames a new
    # inode over `path`, which would silently detach the very lock we just
    # took (see `_write_state_to_locked_fd`'s docstring).
    try:
        current = _read_locked_state(fd, path)
        updated = replace(
            current,
            lock=LockInfo(pid=os.getpid(), host=socket.gethostname(), acquired_at=now_iso()),
        )
        _write_state_to_locked_fd(fd, updated)
    except OSError as exc:  # pragma: no cover - needs a write failure after a successful open+lock
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        raise StateError(f"could not write state file {path!r}: {exc}") from exc
    return LockHandle(_fd=fd, _path=path)


def save_locked_state(handle: LockHandle, state: State) -> None:
    """Persists ``state``'s business fields (``last_balance``,
    ``cooldowns``, ``inflight_upids``, ``staged_disks``) into the
    still-open, still-``flock()``'d fd behind ``handle``, without
    releasing it -- for `execute.py`/`cli.py`'s ``apply`` to call once a
    run has recorded a completed migration's balance and cooldowns
    (:func:`with_recorded_balance`/:func:`with_recorded_cooldown`), before
    :func:`release_lock`. ``state.lock`` is ignored and replaced with
    whatever this handle's own :func:`acquire_lock` call last wrote --
    the caller's in-memory ``state`` was read *before* the lock was taken
    (for planning inputs) and so does not carry this instance's own
    ``pid``/``host``/``acquired_at``; reusing :func:`_write_state_to_locked_fd`
    here (never :func:`save_state_atomic`'s rename) is what keeps this
    write from detaching the lock the same way :func:`acquire_lock` and
    :func:`release_lock` already avoid doing (see
    ``_write_state_to_locked_fd``'s docstring)."""
    current = _read_locked_state(handle._fd, handle._path)
    _write_state_to_locked_fd(handle._fd, replace(state, lock=current.lock))


def release_lock(handle: LockHandle) -> None:
    """Clears the descriptive ``lock`` field and releases the OS-level
    lock, writing in place through the still-open, still-locked fd for the
    same reason :func:`acquire_lock` does. Safe to call even if writing the
    cleared state fails part way -- the ``flock()`` release in the
    ``finally`` always runs, so a write error here never leaves the lock
    held forever."""
    try:
        current = _read_locked_state(handle._fd, handle._path)
        _write_state_to_locked_fd(handle._fd, replace(current, lock=None))
    finally:
        fcntl.flock(handle._fd, fcntl.LOCK_UN)
        os.close(handle._fd)
