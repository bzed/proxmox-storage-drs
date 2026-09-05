# Gating: deciding whether to act at all

**What does this page answer?** How does `gates.py` turn a `loadmodel.GroupLoad`
and per-storage `reserve.ReserveStatus` into the section 6 act/no-act
verdict, and why isn't cooldown handling here? Describes
`proxmox_storage_drs/gates.py`.

## One function, three gates, in the order section 6 lists them

`evaluate_group_gates()` is pure — no network I/O, no `state.json` access —
taking a group's already-computed `GroupLoad`, a `storage id -> ReserveStatus`
mapping (the caller's job, via `reserve.compute_reserve_status()` — this
module never recomputes it, per AGENTS.md section 5's "one implementation
of every rule"), the group's `GatesConfig`, and the load vector recorded at
the group's last *executed* balance (`last_load`, `None` if there isn't
one). It checks, in section 6's own order, stopping at the first that
decides:

1. **Reserve override.** Any storage in `reserve_statuses` with `.violated`
   set forces `act=True` immediately, bypassing drift and imbalance
   entirely — section 13's "safety is not subject to hysteresis" made
   literal, not just documented intent.
2. **Drift gate.** `‖ℓ_now − ℓ_last‖₁ / ‖ℓ_last‖₁ ≥ gates.drift_threshold`,
   vectors aligned over the **union** of disk keys (a disk absent from one
   side contributes its full load in the other as drift — a new or deleted
   disk is a genuine change to the group's I/O profile). `last_load=None`
   skips this gate outright, per section 6's own degenerate-case table —
   not "treat as zero drift", which would make an operator's very first run
   fail to act on an already-imbalanced cluster.
3. **Imbalance gate.** `(max_s u_s − min_s u_s) / u* ≥ gates.imbalance_threshold`,
   `u*` from `GroupLoad.average_utilization`. `u* == 0` (idle group, section
   4) always means no-act — there is nothing to spread evenly.

## `last_load=None` everywhere in this codebase, for now

`state.json` (section 11.2) is not yet written, so nothing in this codebase
has an actual "last executed balance" to read. Every current caller
(`show-load`) passes `last_load=None`, which per the degenerate-case table
means the drift gate is always skipped and every decision reduces to
"reserve override, else imbalance" — an accurate live snapshot, but not
the real hysteresis behaviour section 6 describes once a plan actually
executes and starts recording `ℓ_last`. `evaluate_group_gates()` itself
needs no change when `state.json` exists; only its caller does.

## `show-load`'s gate line is diagnostic, not a real decision

`pve-storage-drs show-load` prints each group's verdict
(`Group <name> → ACT: <reason>` / `→ NO ACTION: <reason>`) reusing
`GateDecision.reason` verbatim — deliberately the single source of truth
for the wording, rather than a second, similarly-but-not-identically
phrased string living in `cli.py`. This is useful today (an operator can
see whether the tool *would* act, and why) but is not what `plan`/`apply`
(not yet written) will actually gate an execution on, once
`last_load` is real: `show-load`'s verdict, precisely because it always
passes `last_load=None`, can only ever show "reserve override" or
"imbalance", never a drift-suppressed "no action" a real run with history
would correctly show.

## Cooldowns are not this module's job

`gates.cooldown_per_disk`/`cooldown_per_storage` decide which *individual*
disks or storages are movable once a plan is already being built — the
same kind of decision (C2)'s other pin reasons make in `topology.py`, not
a group-wide act/no-act verdict. They need `state.json`'s per-disk/
per-storage "last moved at" timestamps, which do not exist yet either, so
implementing them here now would be speculative machinery with no caller
and no real timestamp source to test against. They belong with whichever
module builds the solver's movable-disk set (`heuristic.py`/`schedule.py`,
phase 4) when that is written.
