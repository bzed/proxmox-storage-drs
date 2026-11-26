# Gating: deciding whether to act at all

**What does this page answer?** How does `gates.py` turn a `loadmodel.GroupLoad`
and the `reserve.ReserveStatus` of each storage into the act/no-act verdict of
section 6? Why is the cooldown handling not here? This page describes
`proxmox_storage_drs/gates.py`.

## One function, five gates, in the order section 6 lists them

`evaluate_group_gates()` is pure: it does no network I/O and does not access
`state.json`. It takes these inputs:

- the `GroupLoad` of a group, already computed;
- a `storage id -> ReserveStatus` mapping. The caller builds it with
  `reserve.compute_reserve_status()`. This module never computes it again, per
  the rule "one implementation of every rule" (AGENTS.md section 5);
- the `GatesConfig` of the group;
- the load vector recorded at the last *executed* balance of the group
  (`last_load`, or `None` when there is none).

It checks the gates in the order of section 6 and stops at the first gate that
decides:

1. **Reserve override.** `.violated` is `reserve.ReserveStatus.violated`. It is
   `True` exactly when the committed usage of a storage plus its snapshot-reserve
   floor exceeds the capacity. The shortfall arithmetic is in the section
   "`reserve.py`: one (C4)/(C5) evaluator, shared" of
   `docs/internals/60-topology.md`. Any storage in `reserve_statuses` with
   `.violated` set forces `act=True` at once. It bypasses drift and imbalance
   entirely. This makes "safety is not subject to hysteresis" of section 13
   literal, not just documented intent.
2. **Capacity gate.** The test is
   `(max_s b_s − min_s b_s) / b̄ ≥ gates.capacity_spread_threshold`. It uses fill
   fractions instead of loads, and `b̄` is the mean fill of the group. The gate is
   inactive when `b̄` is 0 or the threshold is `null`. Like the reserve override,
   it bypasses drift and imbalance. Unlike the override, it is a preference:
   cooldowns, payback and the transient invariant still apply.
3. **Split gate** (`gates.split_gate()`). It runs only when the caller hands
   `evaluate_group_gates()` the objective weights. The gate opens the group when
   the large-VM split rule (`snapshot_reserve.split_vm_footprint`,
   `objective.mu_vm_split_per_tib`) can make progress. That is the case when some
   VM above the threshold (`V^split`) has a movable disk and an eligible storage.
   An eligible storage accepts the format of the disk and is not in storage
   cooldown. A move of *that one disk alone* must strictly lower the peak
   footprint of the VM on any one storage. It must also leave the target without a
   reserve shortfall (the shared `reserve.compute_reserve_status()`). The gate
   bypasses drift and imbalance, and it is off when the rule is off. The
   single-move test is deliberate. A VM can sit at the best split that its
   storages allow (four, four and two TiB on three storages). No single move then
   lowers its peak, so the gate stops holding the group open on every run. The
   test is sufficient, not exact. A split that only a *pair* of moves improves does
   not open the group by itself. The next run that passes any other gate picks it
   up. `GateDecision.split_vmid` names the VM that opened the group.
4. **Drift gate.** The test is
   `‖ℓ_now − ℓ_last‖₁ / ‖ℓ_last‖₁ ≥ gates.drift_threshold`. `ℓ_now` and `ℓ_last`
   are the load vectors per disk of this run and of the last executed balance.
   Each entry is the `ℓ_d` of one disk (section 4; see
   `docs/internals/70-loadmodel.md`). `‖·‖₁` is the sum of the absolute values over
   every entry. The gate aligns the vectors over the **union** of the disk keys. A
   disk that is absent on one side counts with its full load from the other side as
   drift: a new or deleted disk is a real change to the I/O profile of the group.
   Both vectors are *effective* loads, whatever `cli._compute_group_load()`
   returned, that is, forecast-scaled under `holt_winters`. A change of the
   forecast state between runs (the model switched, the backtest verdict flipped)
   therefore reads as drift on purpose, because the basis that the balancer places
   against changed (REVIEW.md AM-05). The change only opens the imbalance gate.
   Payback still gates execution. `last_load=None` skips this gate entirely, per
   the degenerate-case table of section 6. It does not mean "treat as zero drift".
   That reading would make the very first run of an operator fail to act on a
   cluster that is already imbalanced.
5. **Imbalance gate.** The test is
   `(max_s u_s − min_s u_s) / u* ≥ gates.imbalance_threshold`. `u_s` is the load of each
   storage divided by its declared capability (`L_s / c_s`), not a byte fill, and
   `u*` is the average of the group
   (`GroupLoad.average_utilization`; both section 4, see
   `docs/internals/70-loadmodel.md`). The gate thus fires when the spread between the most and the least utilized
   storage, relative to `u*`, crosses the threshold. `u* == 0` (an idle group, section 4) always means no
   act, because there is nothing to spread evenly.

## `last_load` is real now, for `show-load` and `plan`

`state.py` (section 11.2) exists. `cli.py` loads
`state.path` once per run. `_last_loads_by_group()` then reads the load vector of
each group from that `State`. It hands the slice of `last_balance.load_vector` for
each group to `evaluate_group_gates()` as `last_load`. The keys are rewritten to
plain `topology.Disk.key`. The value is `None` when the group has no recorded
balance yet. Both `show-load` and `plan` do this identically: `cli.py` calls the
one function, not two copies. `evaluate_group_gates()` itself needed no change. It
already took `last_load` as a parameter and handled `None` correctly (see
`docs/internals/15-state.md` for the read side, and the next section of this page
for what is still missing).

**This module only ever reads `last_balance`.** `gates.py` itself never calls
`state.with_recorded_balance()`. That write happens once, in `_handle_apply()` of
`cli.py`, after any group whose plan actually ran at least one migration (a
`"moved"` or `"draining"` outcome; see `docs/internals/92-execute.md`). Until the
first `apply` run of a group writes the value, `last_balance.load_vector` of that
group stays exactly as a person (or a test) last wrote it by hand. A config with
no `state.json` on disk, or a fresh install, still behaves exactly as this page
originally described: `last_load=None`, the drift gate skipped, and the decision
reduced to "reserve override, else imbalance".

## `show-load`'s gate line is diagnostic, not a real decision

`pve-storage-drs show-load` prints the verdict of each group
(`Group <name> → ACT: <reason>` / `→ NO ACTION: <reason>`). It reuses
`GateDecision.reason` verbatim. That string is deliberately the single source of
truth for the wording. `cli.py` holds no second string with similar but not
identical text. The verdict of `show-load` now shows real drift history whenever
`state.json` has one, exactly like the verdict of `plan`. But the printed verdict
of `show-load` is still not what `apply` actually uses to gate an execution. The
gate evaluation of `plan`/`apply`, run fresh at the moment the tool builds or
applies a plan, is authoritative. The line that `show-load` printed a moment (or a
run) earlier may be stale.

## Cooldowns are not this module's job

`gates.cooldown_per_disk`/`cooldown_per_storage` decide which *individual* disks
or storages are movable once the tool already builds a plan. This is the same kind
of decision as the other pin reasons of (C2) in `topology.py`. (C2) is the
eligibility constraint of the plan for each disk: a pinned disk cannot be
reassigned at all, see `docs/internals/60-topology.md`. The cooldown is not an
act/no-act verdict for the whole group, so this module still has no cooldown logic
of its own. Both cooldowns are now implemented, in the modules where this page
always said they belong:

- The cooldown per disk is a (C2) pin in `topology.py`
  (`docs/internals/60-topology.md`).
- The cooldown per storage is a target-eligibility filter in `heuristic.py`
  (`docs/internals/90-heuristic.md`).

Both read the cooldown data of `state.py` (`docs/internals/15-state.md`).
