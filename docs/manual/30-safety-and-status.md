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

`IMPLEMENTATION_PLAN.md` section 12 lays out nine phases. This is a
work in progress; being honest about exactly where it stands matters more
than a document that reads as if the tool were finished:

| Command | Status |
|---|---|
| `--version`, `--help`, `--manual` | Implemented. |
| `verify-metrics` | Implemented: all six `IMPLEMENTATION_PLAN.md` section 3.3 checks, human and `--json` output. |
| `show-load` | Implemented: every storage in every group, its disks (all buses), sizes, reserve status ((C4)/(C5)), per-disk/per-storage I/O load (`ℓ_d`/`L_s`/`u_s`, section 4), and a section 6 act/no-act verdict per group with its reasoning, pinned and low-coverage disks flagged with their reason (including a disk within `gates.cooldown_per_disk`, once `state.json` has recorded one), human and `--json` output. A Prometheus outage degrades this one group's load (and its gate verdict) to "unavailable" rather than failing the whole command — sizes and reserve status are unaffected. The gate verdict now reads real drift history from `state.json` when a group has one recorded; a group with none yet still evaluates as a first run (reserve override or imbalance only, never drift-suppressed) — see `docs/internals/15-state.md` and `docs/internals/80-gates.md`. |
| `verify-storages` | Implemented: `saferemove` and the implied wipe time per storage, warning when `gates.cooldown_per_storage` or `migration.max_single_move_duration` is shorter than it. |
| `plan` | Implemented: per group, evaluates the section 6 gate (reading real drift history from `state.json` when a group has one recorded — same as `show-load`, see `docs/internals/15-state.md`), and on `ACT` solves it with `solver.backend` (`auto` tries CP-SAT, then CBC, then the dependency-free heuristic — see `docs/internals/91-optimize.md`; both MILP backends and the heuristic exclude, as a migration target, any storage within `gates.cooldown_per_storage`, except when repairing a live reserve violation, which is never deferred for a cooldown, in the heuristic only — see `docs/internals/91-optimize.md`'s own note on that gap), orders its moves under the section 8 transient reserve invariant, and checks the whole plan against section 7's payback (cost/benefit) test — a plan resolving a reserve violation is exempt from the economic half of that test but not from the hard per-move duration rule. Human and `--json` output report which backend actually solved each group. **No automatic re-solve-and-shrink on a failing payback test** — a plan that fails is reported, not silently adjusted (section 7.3's 3-retry loop is not implemented). **No section 7.3 saturation-ceiling check** — needs a forecaster upper bound this codebase does not compute yet; fully supported to be absent per the plan's own words, since it is the one advisory (not hard) check. See `docs/manual/27-plan.md` and `docs/internals/90-heuristic.md`/`91-optimize.md`/`95-schedule.md`/`96-payback.md`. |
| `explain` | Not implemented yet — needs the payback arithmetic it exists to explain (phase 5). |
| `apply` | Not implemented yet — needs `execute.py` (phase 7 onward). |

Configuration loading and validation (this whole manual's
[`10-configuration.md`](10-configuration.md)) is complete and exercised by
every command, including the ones above that are not yet implemented: a
config error is reported and the run exits `1` before reaching the
"not implemented" message, so validating a configuration file does not
require waiting for the rest of the engine.

Running a command that is not implemented yet prints a message naming the
plan section it belongs to, and exits `1`:

```
$ pve-storage-drs apply
pve-storage-drs: 'apply' is not implemented yet in this development build; see IMPLEMENTATION_PLAN.md section 12 for the phase it belongs to
```

## Optional dependencies

`pve-storage-drs` runs, plans and (once implemented) executes with only
`requests`, `ruamel.yaml` and `jsonschema` installed. Three dependencies are
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
