# Safety properties, exit codes, and what this build actually does

## What is safe, unconditionally

These hold for every value of `execution.mode`. No setting can change them
(`.agents/domain-invariants.md`):

- **Dry-run is the default.** A missing or unparseable `execution.mode`
  means dry-run, never automatic execution.
- **The tool never trades the snapshot reserve, or the free space you
  configure, for balance.** `pve-storage-drs` leaves a group imbalanced
  rather than breach `snapshot_reserve.factor` or `free_space.soft` on any
  storage. The reserve holds *during* a migration, not merely before and
  after it. It holds down to `free_space.hard`, never below.
- **The tool never deletes anything automatically.** The tool reports an
  orphaned volume left by a failed move. The tool never removes it. The
  operator deletes.
- **An explicitly named configuration that cannot be read or fails
  validation is a hard failure**, never a silent fallback to
  `/etc/pve/drs.yaml`.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success. The run stopped at a gate. The run found nothing worth moving. A `verify-metrics` run found no error-level finding. |
| `1` | The run failed: the configuration is invalid, Prometheus or the PVE API is unreachable, a move failed, a check failed, or a command is not yet implemented in this build (see below). The list includes an API that fails mid-run, for any group, in the first plan or in a re-plan. A run that gives up because `execution.max_replans_per_run` was exhausted is not a failure. It exits `0`. |
| `2` | Usage error on the command line. |

## What this build actually implements

`IMPLEMENTATION_PLAN.md` section 12 defines thirteen phases. The tool now
implements all thirteen. Phase 10 adds `collect-testdata`, `--replay` and
the real-cluster test corpus of section 16. Phase 11 adds the section 2.3
logging policy (see [`35-logging.md`](35-logging.md)). The status file a
monitoring check reads is documented in [`36-monitoring.md`](36-monitoring.md).
Phase 12 adds the capacity-spread objective and gate, and section 5.3
(C7)/5.4's `δ` term. Phase 13 adds per-storage free-space requirements
(section 5.3.1). Tests against a production cluster continue.
`REVIEW.md` tracks findings from that work to resolution. The table below
states exactly where this still-evolving tool stands, because honest status
matters more than a document that reads as finished and closed:

| Command | Status |
|---|---|
| `--version`, `--help`, `--manual` | Implemented. |
| `verify-metrics` | Implemented: all six checks of `IMPLEMENTATION_PLAN.md` section 3.3, in human and `--json` output. |
| `show-load` | Implemented: every storage in every group, the disks of each storage (all buses), the sizes, the reserve status ((C4)/(C5)), and the per-disk/per-storage I/O load (`ℓ_d`, `L_s`, `u_s`, section 4). The command also prints a section 6 act/no-act verdict per group, with its reasoning. It flags pinned and low-coverage disks, with the reason for each (including a disk within `gates.cooldown_per_disk`, once `state.json` has recorded one). The output is human or `--json`. A Prometheus outage degrades this one group's load (and its gate verdict) to "unavailable" rather than failing the whole command. The sizes and the reserve status are unaffected. The gate verdict reads real drift history from `state.json` when a group has one recorded. A group with none yet evaluates as a first run: reserve override or imbalance only, never drift-suppressed. See `docs/internals/15-state.md` and `docs/internals/80-gates.md`. |
| `verify-storages` | Implemented. The command shows `saferemove` and the implied wipe time per storage. It shows the resolved `free_space.soft`/`.hard` bytes per storage (section 5.3.1). It also prints a warning when `gates.cooldown_per_storage` or `migration.max_single_move_duration` is shorter than the implied wipe time. |
| `plan` | Implemented: per group, the command evaluates the section 6 gate. It reads real drift history from `state.json` when a group has one recorded, same as `show-load` (see `docs/internals/15-state.md`). On `ACT` it solves the group with `solver.backend`. The value `auto` tries CBC first, then the dependency-free heuristic (see `docs/internals/91-optimize.md`). The MILP backend and the heuristic exclude, as a migration target, any storage within `gates.cooldown_per_storage`. The exception is a live reserve violation, which is never deferred for a cooldown, in the heuristic only (see `docs/internals/91-optimize.md`'s own note on that gap). The command orders the moves under the section 8 transient reserve invariant. It checks the whole plan against the section 7 payback (cost/benefit) test. A plan whose executed endpoint reduces the group's reserve/free-space shortfall (section 5.3.1 `free_space.soft`) is exempt from the economic half of that test, but not from the hard per-move duration rule. The human and `--json` output report which backend actually solved each group. **No automatic re-solve-and-shrink on a failing payback test**: a plan that fails is reported, not silently adjusted (section 7.3's 3-retry loop is not implemented). See `docs/manual/27-plan.md` and `docs/internals/90-heuristic.md`/`91-optimize.md`/`95-schedule.md`/`96-payback.md`. |
| `explain` | Implemented: the command runs the identical per-group gate/solve/schedule/payback pipeline that `plan` runs (`_plan_group()`). It then narrates what `plan`'s own output does not print. It lists every disk pinned this run, with its exact reason (section 3.6/3.7: snapshots, an exclusion, a lock, or a still-running `gates.cooldown_per_disk`). It names any VM that a pin leaves with disks spread across more than one storage ("cannot fully consolidate"). When the gate acted, it breaks the section 5.4 objective into its seven terms, because `ObjectiveBreakdown` keeps them separate rather than only a `total`. It also reports the pinned load as a fraction of the group's total, against `report.warn_pinned_load_fraction`. It flags the case where the residual imbalance is likely structural (too much load pinned to fix by moving anything) rather than a planning shortfall. The report shows the best achievable spread that the plan actually reached, given those pins. The human and `--json` output have the same shape as `plan`'s, with these fields added. See `docs/internals/40-cli-and-logging.md` and `docs/internals/90-heuristic.md`. |
| `apply` | Implemented for all three `execution.mode` values. Before it plans anything, the command checks for a `move_disk` left running by a crashed previous run or a second concurrent instance (section 13). It excludes the vmid of that `move_disk` from this run. It runs the identical per-group gate/solve/schedule/payback pipeline that `plan` prints, then executes the plan. The pre-flight check re-checks each move against the live cluster immediately before the command issues it (including exclusion tags/vmids). It waits out a VM config lock rather than failing. It does not consider a move done until the task succeeds, *and* the source volume is gone, *and* the VM's lock is clear. A `saferemove` wipe can hold those apart for hours (`draining`, excluded as both source and target for the rest of that run). The command writes `state.json`'s `inflight_upids` before each `move_disk`. It clears that field once the task finishes. A crash mid-move leaves a trace that the next run's own startup check finds. In `auto` mode the command honours `execution.time_windows` (local host time; it refuses a move that cannot finish before the window closes) and `execution.max_migrations_per_run` (a shared budget across every group the run visits). On a `replan_needed` mismatch, `auto` re-invokes the whole pipeline from freshly observed state, bounded by `execution.max_replans_per_run` (section 9.2's re-plan protocol). `auto` also honours `execution.max_concurrent_migrations`/`max_concurrent_per_storage` above their default of `1`: it applies section 8.1's generalized transient invariant and section 9.2's "poll all in-flight UPIDs" loop, strictly FIFO. It never reorders the scheduler's own queue to keep every slot busy. `dry-run` and `confirm` always run strictly sequentially, regardless. See `docs/manual/28-apply.md`, `docs/internals/92-execute.md` and `docs/internals/93-crashrecovery.md`. |
| `collect-testdata`, and the global `--replay` | Implemented (`IMPLEMENTATION_PLAN.md` section 16, phase 10). `collect-testdata` captures everything the engine can read from the PVE API and Prometheus. That is the superset of every forecaster's data range, not just the configured one. It replaces every identifier with a pseudonym keyed to a salt that never leaves the host (`support.salt_path`). It writes a bundle (a directory and a deterministic `.tar.gz`) that you can read before deciding whether to send it to the author as test data. `--estimate` prints the query/sample-point estimate. It refuses before fetching above `support.max_series_points`. `--replay BUNDLE` then runs `verify-metrics`, `verify-storages`, `show-load`, `plan` and `explain` against such a bundle, with no network access at all. It uses the bundle's own `config.yaml` unless `-c` overrides it. `apply` and any `--mode` above `dry-run` are a usage error under `--replay` (exit `2`). So is `collect-testdata` itself, because it needs a live cluster. See `docs/manual/26-collect-testdata-and-replay.md` and `tests/corpus/README.md`. That file documents what a bundle does and does not hide and the terms on which one is accepted into the project. |

Configuration loading and validation (this whole manual's
[`10-configuration.md`](10-configuration.md)) is complete. Every command
exercises it. The tool reports a config error. The run exits `1` before
`main()` dispatches to the command's own handler. Validating a
configuration file needs no other part of the engine.

Every command in the table above now has a real handler. If the dispatch
mechanism ever did not find one for a command, it would print a message
naming the plan section that command belongs to, and exit `1`.
`docs/internals/40-cli-and-logging.md` describes that mechanism as the
extension point for the next new command this codebase adds, not as dead
code.

## Optional dependencies

`pve-storage-drs` runs, plans and executes with only `requests`,
`ruamel.yaml` and `jsonschema` installed. This covers every
`execution.mode`: `dry-run`, `confirm` and `auto`. One dependency is still
optional. The tool imports it only where the code uses it, never at module
level:

- **`statsmodels`** (Debian `Suggests`) — the tool needs it only for
  `forecast.model: holt_winters`. Without it, that model logs a warning and
  falls back to `quantile` rather than failing.

**`pulp` + `coinor-cbc`** is a Debian `Depends`, not a `Recommends`. A
Debian install always has a real MILP solver: CBC through `pulp`. The
default `solver.backend: auto` uses it. The dependency-free heuristic of
`IMPLEMENTATION_PLAN.md` section 5.5 is still a genuine fallback, not dead
code. It runs when a non-Debian install has no solver extra, when a solve
fails or times out, or when the operator sets `solver.backend: heuristic`
explicitly. The heuristic is no longer the default of a plain `apt install
pve-storage-drs`. An optional `ortools`-based CP-SAT backend existed
through release 0.1.8. The tool removed it. `ortools` has no Debian
package, so that backend could never run on a PVE host. See
`docs/internals/91-optimize.md`.
