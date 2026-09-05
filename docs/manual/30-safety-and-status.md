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
| `plan` | Not implemented yet — needs `pve.py`/`topology.py` (phase 2) and the load model, gates, scheduler and solver (phases 3-6). |
| `show-load` | Not implemented yet — needs `pve.py`/`topology.py` (phase 2). |
| `explain` | Not implemented yet — needs the same, plus the payback and scheduling machinery it explains. |
| `verify-storages` | Not implemented yet — needs `pve.py` (phase 2). |
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
$ pve-storage-drs plan
pve-storage-drs: 'plan' is not implemented yet in this development build; see IMPLEMENTATION_PLAN.md section 12 for the phase it belongs to
```

## Optional dependencies

`pve-storage-drs` runs, plans and (once implemented) executes with only
`requests`, `ruamel.yaml` and `jsonschema` installed. Two dependencies are
optional and are imported only where they are used, never at module level:

- **`pulp` + `coinor-cbc`** (Debian `Recommends`) — the packaged MILP solver
  path. Without it, the solver falls back to the dependency-free heuristic.
- **`statsmodels`** (Debian `Suggests`) — needed only for
  `forecast.model: holt_winters`. Without it, that model logs a warning and
  falls back to `quantile` automatically rather than failing.
