# Persistent state: `state.json`

**What does this page answer?** What does `state.py` actually store, how
does reading it degrade instead of failing, why is the advisory lock a real
`flock()` rather than a JSON field, and what does today's wiring into
`show-load`/`plan` actually change? Describes `proxmox_storage_drs/state.py`.

## One dataclass tree, matching section 11.2's JSON exactly

`State` mirrors the plan's own example document field for field: `lock`
(`LockInfo | None`), `last_balance` (`at` plus a `"<group>:<vmid>:<device>"
-> ℓ_d` `load_vector`), `cooldowns` (`disk`/`storage`, each a key ->
timestamp mapping), `inflight_upids`, `staged_disks`. `disk_state_key()`/
`storage_state_key()` build the two key shapes section 11.2 specifies —
group-prefixed specifically so a vmid reused after a VM is destroyed and
recreated in a *different* group cannot collide with its old entry.
`empty_state()` is what a fresh install, or a lost file, degrades to: no
lock, no balance, no cooldowns, nothing in flight.

## Reading degrades; writing does not

`load_state()` never raises. A missing file is the ordinary first-run case
(silent); a present-but-corrupt, empty, or wrong-`schema_version` one is
still just `empty_state()`, but logged at `WARNING` — section 11.2's own
words are "losing this file is safe but not free: cooldowns and drift
history reset", not "state.json existing and being readable is required to
run". This mirrors `show-load`'s choice to degrade a group's load to
"unavailable" on a Prometheus outage rather than fail the whole command —
neither Prometheus nor `state.json` is an *explicitly requested* input the
way `-c/--config PATH` is, and only the latter is a hard failure on error
(`.agents/domain-invariants.md` section 9).

`save_state_atomic()`, by contrast, raises `StateError` on any failure —
writing (or locking) is something a caller actively asked this module to
do, not a read with a documented, safe fallback. It writes to a temp file
in the same directory, `fsync`s, then `os.replace()`s over the real path,
so a concurrent `load_state()` can never observe a half-written file —
which is exactly what lets every read in this codebase skip locking
entirely (next section).

## Locking: `flock()` is the mechanism, the JSON `lock` field is a label

`acquire_lock()` takes a real, non-blocking `fcntl.flock(LOCK_EX |
LOCK_NB)` on the state file itself. That is the actual, kernel-enforced
mutual exclusion section 11.2 asks for, and it is correct by construction
for two instances on the *same host* — `.agents/domain-invariants.md`
section 9 is explicit that "the `fcntl` lock cannot see another node";
cross-node coordination is the separate in-flight-UPID scan (section 13),
not this module's job.

The `lock: {pid, host, acquired_at}` field recorded *inside* the JSON is
**descriptive metadata for a human reading the file, not the exclusion
mechanism** — by the time this module's code overwrites it, the OS has
already granted exclusive ownership, so whatever a previous run last wrote
there is necessarily stale and is unconditionally replaced, never
inspected to decide whether to proceed. This is also how section 11.2's
"if `lock.pid` is not alive on `lock.host`, reclaim it" is satisfied,
without a separate liveness check to get subtly wrong: a process that died
released its `flock()` the moment its file descriptor closed (any exit,
including a crash), so the *next* `acquire_lock()` call simply succeeds.
`acquire_lock()` returns `None` — not an exception — when another live
instance already holds it, matching section 11.2's "a live PID means
another instance is running: exit 0 quietly"; deciding what "quietly"
means, and which exit code, is left to the caller.

**A real bug this design surfaced during testing, worth remembering if you
touch this code:** the first implementation had `acquire_lock()` write its
lock metadata via `save_state_atomic()` — the same temp-file-plus-`rename`
used everywhere else. That silently breaks the lock: a rename replaces the
directory entry with a *new* inode that was never `flock()`'d, so a second
`acquire_lock()` opens that new inode fresh and locks it with no conflict
at all — `test_a_second_acquire_while_the_first_is_held_returns_none`
caught this immediately. The fix, `_write_state_to_locked_fd()`, writes
**in place** into the already-open, already-locked file descriptor
(`lseek` to 0, `write`, `ftruncate` to the new length, `fsync`) — never a
rename — for as long as the lock is held.

## What today's wiring into `cli.py` actually changes

`show-load` and `plan` both call `_last_loads_by_group()` once, right after
reading configuration, and use the result for both
`loadmodel.compute_group_load()`'s `last_known_loads` and
`gates.evaluate_group_gates()`'s `last_load` — one state read per run, one
function computing the per-group slice, not two independent
implementations (AGENTS.md section 5). Neither command takes the advisory
lock: both are read-only reports that never execute a migration, and
taking the exclusive lock for one would make an in-progress `apply` block
`plan`/`show-load` for no safety reason the plan text supports.

The practical effect: a `state.json` with a real `last_balance` now makes
the drift gate genuinely suppress an `ACT` verdict the imbalance alone
would otherwise trigger — see
`test_show_load_gate_reflects_real_drift_history_from_state_json` and
`test_plan_gate_also_reflects_real_drift_history_from_state_json` in
`tests/unit/test_cli.py` for the exact before/after. Without a
`state.json` on disk (the common case until `execute.py` exists — see
below), behaviour is unchanged from before this module existed:
`last_load=None`, drift gate skipped, "reserve override, else imbalance".

## Deliberately not implemented in this pass

- **Nothing calls `acquire_lock()` or `with_recorded_balance()` yet.** Both
  exist and are fully tested, but only `execute.py` (phase 7, not yet
  written) has a reason to take the lock or record a balance — section
  11.2 itself says `last_balance` is "updated only after a run that
  executed at least one migration", and neither `show-load` nor `plan`
  ever does.
- **Cooldowns are stored and round-tripped (`Cooldowns`,
  `with_recorded_cooldown()`) but not yet *read* by anything that pins a
  disk or excludes a migration target.** Section 5.3 (C2)'s "within its
  per-disk cooldown -> pin to current" belongs with `topology.py`'s other
  (C2) pin reasons (locked, excluded, snapshotted — see
  `topology._pin_reason()`); the storage-side "accepts no new incoming
  moves" belongs with `heuristic.py`'s target eligibility. Both need a
  `State`/cooldown lookup threaded into a function that does not accept
  one today — a real, separately-scoped change to two other modules, not
  this one.
- **`inflight_upids`/`staged_disks`** exist in the dataclass and round-trip
  correctly, but nothing writes or reads them yet — they belong to
  `execute.py` (crash recovery, section 13) and `schedule.py`'s staging
  (section 8.3 option 1, also not implemented), respectively.
