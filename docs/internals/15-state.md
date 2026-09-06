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
`plan`/`show-load` for no safety reason the plan text supports. `apply`
(`docs/internals/92-execute.md`) is the one command that does take it —
before touching PVE or Prometheus at all, so a second concurrent instance
exits quietly without paying for either round-trip first.

The practical effect: a `state.json` with a real `last_balance` now makes
the drift gate genuinely suppress an `ACT` verdict the imbalance alone
would otherwise trigger — see
`test_show_load_gate_reflects_real_drift_history_from_state_json` and
`test_plan_gate_also_reflects_real_drift_history_from_state_json` in
`tests/unit/test_cli.py` for the exact before/after. Without a
`state.json` on disk (the common case until `apply` has actually executed
a migration), behaviour is unchanged from before this module existed:
`last_load=None`, drift gate skipped, "reserve override, else imbalance".

## Cooldowns: read by `topology.py` and `heuristic.py`, not by this module

`state.py` only stores and queries cooldown timestamps
(`active_disk_cooldowns()`/`active_storage_cooldowns()`); it does not
decide what a cooldown *means* to the solver. `build_topology()` (via a
new `state`/`now` parameter, both defaulting to "no cooldowns"/"real
clock") computes each group's active disk cooldowns once and feeds them
into `topology._pin_reason()` — section 5.3 (C2)'s "`d` is within its
per-disk cooldown -> also pin to current", reported as `cooldown: moved
recently, <time> left on gates.cooldown_per_disk`, in the plan's own
priority order (after a snapshot pin, before a lock pin). `cli.py`
separately computes each group's active *storage* cooldowns and passes
them to `heuristic.run_heuristic()`, which excludes them as a move/swap
**destination** in `_descend()` only — see `docs/internals/60-topology.md`
and `docs/internals/90-heuristic.md` for the two halves in detail,
including the deliberate asymmetry: a live (C4)/(C5) repair move ignores
the storage cooldown entirely (section 13's reserve-override principle),
while nothing yet exempts a disk-cooldown pin from blocking a repair the
same way — a known, documented limitation, not an oversight.

`apply` is what actually calls `with_recorded_cooldown()` now, once per
group, for every disk/storage a run's `execute_plan()` call actually
migrated — a fresh disk cooldown at the disk's *new* location, and a fresh
storage cooldown for the move's **destination** only, mirroring
`_descend()`'s own asymmetry above (`docs/internals/92-execute.md`). A
group `apply` never acts on (the gate said `NO ACTION`, or nothing
executed before a `load_error`/`replan_needed` stopped it) leaves that
group's cooldowns untouched, exactly like before this was wired in.

## Locking and writing: `apply`'s own responsibility

`acquire_lock()`/`release_lock()`/`save_locked_state()` are exercised now:
`apply` is the one command that can execute a migration, so it is the one
this lock protects (see `docs/internals/92-execute.md`). It acquires the
lock first, builds up the run's `State` in memory as each group finishes
executing (`with_recorded_balance()`/`with_recorded_cooldown()`), and
writes it once at the very end via `save_locked_state()` — **never**
`save_state_atomic()`'s rename, which would silently detach the very lock
just taken (see this page's own account of that bug, above) — before
`release_lock()` in a `finally`, so a mid-run exception never leaves the
lock held. `show-load`/`plan` still never take it, for the same
read-only-report reason as always.

## Deliberately not implemented in this pass

- **A disk-cooldown pin is not exempted for an active reserve violation
  the way the storage cooldown is.** `topology.py` decides a disk's pin
  before the group's `reserve.ReserveStatus` is even computable (it needs
  every disk in the group, which is still being built), so there is no
  cheap way today to ask "would un-pinning this disk help fix a live
  violation?" at the point the pin decision is made. The practical effect
  is bounded and safe, never silently wrong: `heuristic._repair()` already
  reports an unresolvable residual violation via `reserve_penalty_term`
  whenever no movable disk can fix it (the same path
  `test_repair_does_not_oscillate_when_no_target_can_fully_absorb_the_violation`
  exercises) — a disk-cooldown pin can only ever add to the set of cases
  that hit that path, never bypass it. Revisiting this needs restructuring
  `topology.py` into two passes (build every disk first, compute reserve
  status per storage, then finalize cooldown pins), which is a real,
  separately-scoped change.
- **`inflight_upids`/`staged_disks`** exist in the dataclass and round-trip
  correctly, but nothing writes or reads them yet — they belong to
  `execute.py` (crash recovery, section 13) and `schedule.py`'s staging
  (section 8.3 option 1, also not implemented), respectively.
