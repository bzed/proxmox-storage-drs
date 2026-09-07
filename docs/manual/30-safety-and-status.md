# Safety properties, exit codes, and what this build actually does

## What is safe, unconditionally

These hold regardless of `execution.mode`, and are not configurable away
(`.agents/domain-invariants.md`):

- **Dry-run is the default.** A missing or unparseable `execution.mode`
  means dry-run, never automatic execution.
- **The snapshot reserve is never traded for balance.** `pve-storage-drs`
  will leave a group imbalanced rather than breach
  `snapshot_reserve.factor`/`min_free_bytes` on any storage, and that reserve
  holds *during* a migration, not merely before and after it.
- **Nothing is ever deleted automatically.** An orphaned volume left by a
  failed move is reported, never removed. The operator deletes.
- **An explicitly named configuration that cannot be read or fails
  validation is a hard failure**, never a silent fallback to
  `/etc/pve/drs.yaml`.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success. A run that stopped at a gate, found nothing worth moving, or (for `verify-metrics`) found no error-level finding. |
| `1` | The run failed: invalid configuration, an unreachable Prometheus or PVE API, a failed check, or a command not yet implemented in this build (see below). |
| `2` | Usage error on the command line. |

## What this build actually implements

`IMPLEMENTATION_PLAN.md` section 12 lays out nine phases; all nine, and
every command in the table below, are implemented. Dogfooding against a
production cluster continues, and `REVIEW.md` tracks findings from that to
resolution — being honest about exactly where a still-evolving tool stands
matters more than a document that reads as finished and closed:

| Command | Status |
|---|---|
| `--version`, `--help`, `--manual` | Implemented. |
| `verify-metrics` | Implemented: all six `IMPLEMENTATION_PLAN.md` section 3.3 checks, human and `--json` output. |
| `show-load` | Implemented: every storage in every group, its disks (all buses), sizes, reserve status ((C4)/(C5)), per-disk/per-storage I/O load (`ℓ_d`/`L_s`/`u_s`, section 4), and a section 6 act/no-act verdict per group with its reasoning, pinned and low-coverage disks flagged with their reason (including a disk within `gates.cooldown_per_disk`, once `state.json` has recorded one), human and `--json` output. A Prometheus outage degrades this one group's load (and its gate verdict) to "unavailable" rather than failing the whole command — sizes and reserve status are unaffected. The gate verdict now reads real drift history from `state.json` when a group has one recorded; a group with none yet still evaluates as a first run (reserve override or imbalance only, never drift-suppressed) — see `docs/internals/15-state.md` and `docs/internals/80-gates.md`. |
| `verify-storages` | Implemented: `saferemove` and the implied wipe time per storage, warning when `gates.cooldown_per_storage` or `migration.max_single_move_duration` is shorter than it. |
| `plan` | Implemented: per group, evaluates the section 6 gate (reading real drift history from `state.json` when a group has one recorded — same as `show-load`, see `docs/internals/15-state.md`), and on `ACT` solves it with `solver.backend` (`auto` tries CP-SAT, then CBC, then the dependency-free heuristic — see `docs/internals/91-optimize.md`; both MILP backends and the heuristic exclude, as a migration target, any storage within `gates.cooldown_per_storage`, except when repairing a live reserve violation, which is never deferred for a cooldown, in the heuristic only — see `docs/internals/91-optimize.md`'s own note on that gap), orders its moves under the section 8 transient reserve invariant, and checks the whole plan against section 7's payback (cost/benefit) test, including the section 7.3 saturation-ceiling guard (mirroring phase only) for any storage that configures `saturation_load` (still none in this project's own dogfooding cluster) — a plan resolving a reserve violation is exempt from the economic half of that test but not from the hard per-move duration rule or the saturation guard. Human and `--json` output report which backend actually solved each group. **No automatic re-solve-and-shrink on a failing payback test** — a plan that fails is reported, not silently adjusted (section 7.3's 3-retry loop is not implemented). See `docs/manual/27-plan.md` and `docs/internals/90-heuristic.md`/`91-optimize.md`/`95-schedule.md`/`96-payback.md`. |
| `explain` | Implemented: runs the identical per-group gate/solve/schedule/payback pipeline `plan` does (`_plan_group()`), then narrates what `plan`'s own output does not print. Lists every disk pinned this run with its exact reason (section 3.6/3.7 — snapshots, an exclusion, a lock, or a still-running `gates.cooldown_per_disk`), names any VM a pin leaves with disks spread across more than one storage ("cannot fully consolidate"), and breaks the section 5.4 objective down into its five terms (`ObjectiveBreakdown`'s own reason for keeping them separate rather than only a `total`) when the gate acted. Also reports pinned load as a fraction of the group's total against `report.warn_pinned_load_fraction`, flagging when the residual imbalance is likely structural (too much load pinned to fix by moving anything) rather than a planning shortfall — alongside the best achievable spread the plan actually reached given those pins. Human and `--json` output, same shape as `plan`'s with these fields added. See `docs/internals/40-cli-and-logging.md` and `docs/internals/90-heuristic.md`. |
| `apply` | Implemented for all three `execution.mode` values. Before planning anything, checks for a `move_disk` left running by a crashed previous run or a second concurrent instance (section 13) and excludes its vmid from this run; runs the identical per-group gate/solve/schedule/payback pipeline `plan` prints, then executes it: pre-flight re-checks each move against the live cluster immediately before issuing it (including exclusion tags/vmids), waits out a VM config lock rather than failing, and does not consider a move done until the task succeeds *and* the source volume is gone *and* the VM's lock is clear — a `saferemove` wipe can hold those apart for hours (`draining`, excluded as both source and target for the rest of that run). `state.json`'s `inflight_upids` is written before each `move_disk` and cleared once its task finishes, so a crash mid-move leaves a trace the next run's own startup check finds. `auto` additionally honours `execution.time_windows` (local host time; refuses a move that cannot finish before the window closes) and `execution.max_migrations_per_run` (a shared budget across every group the run visits), and re-invokes the whole pipeline from freshly observed state on a `replan_needed` mismatch, bounded by `execution.max_replans_per_run` (section 9.2's re-plan protocol). `execution.max_concurrent_migrations`/`max_concurrent_per_storage` above their default of `1` are honoured in `auto` mode: section 8.1's generalized transient invariant and section 9.2's "poll all in-flight UPIDs" loop, strictly FIFO (never reordering the scheduler's own queue to keep every slot busy) — `dry-run`/`confirm` always run strictly sequentially regardless. See `docs/manual/28-apply.md`, `docs/internals/92-execute.md` and `docs/internals/93-crashrecovery.md`. |

Configuration loading and validation (this whole manual's
[`10-configuration.md`](10-configuration.md)) is complete and exercised by
every command: a config error is reported and the run exits `1` before
`main()` ever dispatches to a command's own handler, so validating a
configuration file does not require the rest of the engine to be involved
at all.

Every command in the table above now has a real handler, but the
dispatch mechanism that reports one honestly if it did not would still
print a message naming the plan section it belongs to, and exit `1` —
`docs/internals/40-cli-and-logging.md` describes it as the extension
point for the next new command this codebase adds, not dead code kept
around for its own sake.

## Optional dependencies

`pve-storage-drs` runs, plans and executes (`dry-run`/`confirm`; `auto` not
yet) with only `requests`, `ruamel.yaml` and `jsonschema` installed. Three
dependencies are
optional and are imported only where they are used, never at module level:

- **`pulp` + `coinor-cbc`** (Debian `Recommends`) — the packaged MILP solver
  path (`solver.backend: cbc`, or `auto` when CP-SAT is unavailable).
- **`ortools`** (`pip install proxmox-storage-drs[solver]`, **not** packaged
  for Debian — CP-SAT has no Debian package at all) — the preferred MILP
  backend (`solver.backend: cpsat`, or `auto`'s first choice) when installed
  by hand outside the Debian path.
- **`statsmodels`** (Debian `Suggests`) — needed only for
  `forecast.model: holt_winters`. Without it, that model logs a warning and
  falls back to `quantile` automatically rather than failing.

Without either MILP library, `solver.backend: auto` (the default) falls back
to the dependency-free heuristic; nothing in `pve-storage-drs` requires a
MILP solver to be installed at all — see `docs/internals/91-optimize.md`.
