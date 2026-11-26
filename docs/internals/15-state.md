# Persistent state: `state.json`

**What does this page answer?** What does `state.py` store? How does
reading degrade instead of failing? Why is the advisory lock a real
`flock()` rather than a JSON field? What does the wiring into
`show-load`/`plan` change? This page describes `proxmox_storage_drs/state.py`.

## One dataclass tree, matching section 11.2's JSON exactly

`State` mirrors the plan's own example document field for field. The
fields are `lock` (`LockInfo | None`), `last_balance` (`at` plus a
`"<group>:<vmid>:<device>" -> ℓ_d` `load_vector`), `cooldowns`
(`disk`/`storage`, each a key -> timestamp mapping), `inflight_upids`,
and `staged_disks`. `disk_state_key()` and `storage_state_key()`
build the two key shapes that section 11.2 specifies. The keys are
group-prefixed. A vmid reused after a VM is destroyed and recreated in
a *different* group then cannot collide with its old entry.
`empty_state()` is what a fresh install, or a lost file, degrades to:
no lock, no balance, no cooldowns, nothing in flight.

## Reading degrades; writing does not

`load_state()` never raises. A missing file is the ordinary first-run
case. The function stays silent. A corrupt or wrong-`schema_version` file also yields `empty_state()`, and the
function logs that case at `WARNING`. An empty file yields `empty_state()`
silently, like a missing file. Section 11.2 puts it this way: "losing
this file is safe but not free: cooldowns and drift history reset",
not "state.json existing and being readable is required to run". This
mirrors the choice in `show-load`: on a Prometheus outage, the command
degrades a group's load to "unavailable" rather than fail the whole
command. Neither Prometheus nor `state.json` is an *explicitly
requested* input the way `-c/--config PATH` is. Only the latter fails
hard on an error (`.agents/domain-invariants.md` section 9).

`save_state_atomic()`, by contrast, raises `StateError` on any
failure. Writing (or locking) is an action a caller asked this module
to do, not a read with a documented, safe fallback. The function
writes to a temp file in the same directory. It `fsync`s the file. It
then `os.replace()`s the temp file over the real path. A concurrent
`load_state()` can then never observe a half-written file. That is
exactly what lets every read in this codebase skip locking entirely
(next section).

## Locking: `flock()` is the mechanism, the JSON `lock` field is a label

`acquire_lock()` takes a real, non-blocking `fcntl.flock(LOCK_EX |
LOCK_NB)` on the state file itself. That is the kernel-enforced mutual
exclusion that section 11.2 asks for. The lock is correct for two
instances on the *same host*. `.agents/domain-invariants.md` section 9
is explicit that "the `fcntl` lock cannot see another node".
Cross-node coordination is the separate in-flight-UPID scan
(section 13), not this module's job.

The `lock: {pid, host, acquired_at}` field recorded *inside* the JSON
is **descriptive metadata for a human reading the file, not the
exclusion mechanism**. By the time this module overwrites the field,
the OS has already granted exclusive ownership. Whatever a previous
run last wrote there is necessarily stale. The code replaces that
value unconditionally. It never inspects the value to decide whether
to proceed. Section 11.2 says: "if `lock.pid` is not alive on
`lock.host`, reclaim it". The design satisfies that rule without a
separate liveness check. A process that died released its `flock()`
the moment its file descriptor closed. That covers any exit,
including a crash. The *next* `acquire_lock()` call simply succeeds.
`acquire_lock()` returns `None`, not an exception, when another live
instance already holds the lock. Section 11.2 says: "a live PID means
another instance is running: exit 0 quietly". The caller decides what
"quietly" means and which exit code to use.

**A real bug this design surfaced during testing, worth remembering if
you touch this code:** the first implementation had `acquire_lock()`
write its lock metadata via `save_state_atomic()`. That is the same
temp-file-plus-`rename` flow used everywhere else. A rename breaks the
lock. It replaces the directory entry with a *new* inode. The new
inode was never `flock()`'d. A second `acquire_lock()` opens that new
inode fresh and locks it with no conflict at all.
`test_a_second_acquire_while_the_first_is_held_returns_none` caught
the bug immediately. The fix is `_write_state_to_locked_fd()`. It
writes **in place** into the already-open, already-locked file
descriptor (`lseek` to 0, `write`, `ftruncate` to the new length,
`fsync`). It never renames. It does this for as long as the lock is
held.

## What today's wiring into `cli.py` actually changes

`show-load` and `plan` both call `_last_loads_by_group()` once, right
after they read the configuration. They use the result for both
`loadmodel.compute_group_load()`'s `last_known_loads` and
`gates.evaluate_group_gates()`'s `last_load`. The run performs one
state read. One function computes the per-group slice. The code keeps
one implementation, not two independent implementations (AGENTS.md
section 5). Neither command takes the advisory lock. Both are
read-only reports. They never run a migration. If one of them took the
exclusive lock, an in-progress `apply` would block
`plan`/`show-load`. The plan text supports no safety reason for that
block. `apply` (`docs/internals/92-execute.md`) is the one command
that does take the lock. It takes the lock before it touches PVE or
Prometheus. A second concurrent instance exits quietly before it
performs any PVE or Prometheus round-trip.

The practical effect: a `state.json` with a real `last_balance` now
makes the drift gate genuinely suppress an `ACT` verdict. The
imbalance alone would trigger that verdict. See
`test_show_load_gate_reflects_real_drift_history_from_state_json` and
`test_plan_gate_also_reflects_real_drift_history_from_state_json` in
`tests/unit/test_cli.py` for the exact before/after. Without a
`state.json` on disk, behaviour is unchanged from before this module
existed. That absence is the common case until `apply` has actually
run a migration. The value is `last_load=None`. The drift gate is
skipped. The rule is "reserve override, else imbalance".

## Cooldowns: read by `topology.py` and `heuristic.py`, not by this module

`state.py` only stores and queries cooldown timestamps
(`active_disk_cooldowns()`/`active_storage_cooldowns()`). It does not
decide what a cooldown *means* to the solver. `build_topology()` takes
a new `state` parameter and a new `now` parameter. The `state`
parameter defaults to "no cooldowns". The `now` parameter defaults to
"real clock". The function computes each group's active disk
cooldowns once. It feeds them into `topology._pin_reason()`. That
implements section 5.3 (C2): "`d` is within its per-disk cooldown ->
also pin to current". The tool reports the pin as `cooldown: moved
recently, <time> left on gates.cooldown_per_disk`. The pin sits in the
plan's own priority order, after a snapshot pin and before a lock pin.
`cli.py` separately computes each group's active *storage* cooldowns.
It passes them to `heuristic.run_heuristic()`. The heuristic excludes
them as a move/swap **destination** in `_descend()` only. See
`docs/internals/60-topology.md` and `docs/internals/90-heuristic.md`
for the two halves in detail. The two pages also cover the deliberate
asymmetry. A live (C4)/(C5) repair move ignores the storage cooldown
entirely (section 13's reserve-override principle). Nothing yet
exempts a disk-cooldown pin from blocking a repair the same way. That
is a known, documented limitation, not an oversight.

`apply` now calls `with_recorded_cooldown()`. It calls the function
once per group. It calls it for every disk and storage that the
run's `execute_plan()` call actually migrated. The run records a
fresh disk cooldown at the disk's *new* location. It records a fresh
storage cooldown for **both** the source and the destination of the move
(`docs/internals/92-execute.md` explains why). The *enforcement* of that
cooldown stays destination-only, like `_descend()` above. A
group that `apply` never acts on keeps its cooldowns untouched,
exactly like before this was wired in. `apply` does not act on a
group when the gate said `NO ACTION`. It also does not act when
nothing executed before a `load_error`/`replan_needed` stopped the
run.

## Locking and writing: `apply`'s own responsibility

`acquire_lock()`, `release_lock()` and `save_locked_state()` are
exercised now. `apply` is the one command that can run a migration.
The lock protects that command (see `docs/internals/92-execute.md`).
The command acquires the lock first. It builds up the run's `State` in
memory as each group finishes executing
(`with_recorded_balance()`/`with_recorded_cooldown()`). It writes the state at the end of the run via `save_locked_state()`. It also
writes at the start and at the end of each migration (see below), so that a crash
leaves the UPID of an unfinished move on disk. It **never**
uses `save_state_atomic()`'s rename. That rename would detach the
very lock just taken. This page describes that bug above. The write
happens before `release_lock()`, in a `finally`. A mid-run exception
never leaves the lock held. `show-load`/`plan` still never take the
lock. They are read-only reports, the same reason as always.

The same run-time writes also record each migration's UPID into
`inflight_upids`. `cli.py` does this with a synchronous
`with_inflight_upid()`/`without_inflight_upid()` callback that it passes into
`execute_plan()`. At startup, the next run scans these UPIDs. `crashrecovery.py`
owns that scan. It also owns what a crash between the two runs leaves behind
(`docs/internals/93-crashrecovery.md`).

## Deliberately not implemented in this pass

- **A disk-cooldown pin is not exempted for an active reserve
  violation the way the storage cooldown is.** `topology.py` decides
  a disk's pin before the group's `reserve.ReserveStatus` is even
  computable. The status needs every disk in the group. The code is
  still building those disks. There is no cheap way today to ask
  "would un-pinning this disk help fix a live violation?" at the
  point the pin decision is made. The practical effect is bounded and
  safe. The outcome is never wrong. `heuristic._repair()` already
  reports an unresolvable residual violation via `reserve_penalty_term`.
  It reports it whenever no movable disk can fix it.
  `test_repair_does_not_oscillate_when_no_target_can_fully_absorb_the_violation`
  exercises the same path. A disk-cooldown pin can only add to the
  set of cases that hit that path. It never bypasses the reporting
  path. Revisiting this needs a restructuring of `topology.py` into
  two passes: build every disk first, compute the reserve status per
  storage, then finalize the cooldown pins. That is a real,
  separately-scoped change.
- **`staged_disks`** exists in the dataclass. It round-trips
  correctly. Nothing writes or reads the field yet. The field belongs
  to `schedule.py`'s staging (section 8.3 option 1). That staging is
  not implemented.
