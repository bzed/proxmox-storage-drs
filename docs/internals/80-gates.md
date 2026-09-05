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

## `last_load` is real now, for `show-load` and `plan`

`state.py` (section 11.2) exists: `cli.py`'s `_last_loads_by_group()` reads
`state.path` once per run and hands each group's slice of
`last_balance.load_vector` (re-keyed to plain `topology.Disk.key`, or
`None` if that group has no recorded balance yet) to
`evaluate_group_gates()` as `last_load` -- both `show-load` and `plan` do
this identically (`cli.py` calls the one function, not two copies).
`evaluate_group_gates()` itself needed no change at all: it already took
`last_load` as a parameter and treated `None` correctly (see
`docs/internals/15-state.md` for the read side, and this page's next
section for what is still missing).

**What this does not yet do.** `state.json`'s `last_balance` is only ever
*read* here -- nothing in this codebase calls `state.with_recorded_balance()`
yet, because nothing executes a migration yet (`execute.py`, phase 7). Until
then, `last_balance.load_vector` for any group stays exactly what it was
the last time a human (or a test) wrote it by hand; a config with no
`state.json` on disk, or a fresh install, still behaves exactly as this
page originally described -- `last_load=None`, drift gate skipped, decision
reduces to "reserve override, else imbalance". The wiring is real; the
writer that would make it self-sustaining is not built yet.

## `show-load`'s gate line is diagnostic, not a real decision

`pve-storage-drs show-load` prints each group's verdict
(`Group <name> → ACT: <reason>` / `→ NO ACTION: <reason>`) reusing
`GateDecision.reason` verbatim — deliberately the single source of truth
for the wording, rather than a second, similarly-but-not-identically
phrased string living in `cli.py`. Its verdict now reflects real drift
history whenever `state.json` has one, exactly like `plan`'s does — but
`show-load` still isn't what `apply` (not yet written) will actually gate
an execution on; it is `plan`/`apply`'s own gate evaluation, run at the
moment a plan is built or applied, that is authoritative.

## Cooldowns are not this module's job

`gates.cooldown_per_disk`/`cooldown_per_storage` decide which *individual*
disks or storages are movable once a plan is already being built — the
same kind of decision (C2)'s other pin reasons make in `topology.py`, not
a group-wide act/no-act verdict, so this module still has no cooldown
logic of its own. Both are now implemented, in the modules this page
always said they belonged with: the per-disk cooldown is a `topology.py`
(C2) pin (`docs/internals/60-topology.md`), and the per-storage cooldown
is a `heuristic.py` target-eligibility filter
(`docs/internals/90-heuristic.md`), both reading `state.py`'s cooldown
data (`docs/internals/15-state.md`).
