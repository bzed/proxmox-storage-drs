# Overview: what is built, and how it fits together

**What does this page answer?** Where does an invocation of `pve-storage-drs` go,
which module owns which piece, and how much of `IMPLEMENTATION_PLAN.md`'s
section 2 architecture actually exists right now?

## The pipeline, as specified and as built

`IMPLEMENTATION_PLAN.md` section 2 describes seven stages: collect, join,
gate, solve, cost, order, execute. As of this page, stages 1 (collect)
through 6 (cost/order — sections 5-8 minus the MILP backend) exist for the
heuristic path — the MILP path (an alternative stage-4 backend) and
execute are `IMPLEMENTATION_PLAN.md` section 12 phases 6-9 and are not yet
written. Do not take this page as a claim that the whole pipeline runs end
to end — [`../manual/30-safety-and-status.md`](../manual/30-safety-and-status.md)
is the authoritative per-command status: `plan` is real and prints an
ordered, transient-feasible, payback-checked dry-run plan (see
[`../manual/27-plan.md`](../manual/27-plan.md)), but nothing yet *executes*
one (no `apply`). `state.json` itself exists (`state.py`) and is read by
both `show-load` and `plan` for real drift history — see
[`15-state.md`](15-state.md) and [`80-gates.md`](80-gates.md) — but nothing
writes it yet, since only `execute.py` (not yet written) has a reason to.

```
   ┌──────────────────────┐        ┌────────────────────────────┐
   │  Prometheus          │        │   Proxmox VE API           │
   │  (metrics.py)         │        │   (pve.py, via proxmoxer)  │
   └──────────┬────────────┘        └──────────────┬─────────────┘
              │ PrometheusClient,                   │ PveClient,
              │ PromQL builders,                    │ build_client()
              │ verify_metrics()                    │
              ▼                                     ▼
                                         topology.py (build_topology():
                                         the disk/storage/group join, D/S/U^ext)
                                                     │
                              ┌──────────────────────┴──────────────────────┐
                              ▼                                             ▼
                reserve.py (compute_reserve_status():           loadmodel.py (compute_group_load():
                (C4)/(C5), shared with the solver)               l_d/L_s/u_s, section 4)
                              │                                             │
                              └──────────────────────┬──────────────────────┘
                                                      ▼
                                     gates.py (evaluate_group_gates():
                                     reserve override / drift / imbalance, section 6)
                                                      │
                                     heuristic.py (run_heuristic():
                                     seed / repair / descend, section 5.4/5.5)
                                                      │
                                     schedule.py (order_moves():
                                     transient reserve invariant, section 8)
                                                      │
                                     payback.py (evaluate_plan_payback():
                                     cost/benefit acceptance test, section 7)
                                                      │
        ┌───────────────────────────────────────────────────────────────────┐
        │            cli.py  (argument parsing, command dispatch,           │
        │      mode-override rule, show-load, verify-storages, plan)        │
        └───────────────────────┬─────────────────────────────────────────┘
                                 │
                     config.py (load + validate)
                     state.py (state.json: drift history in, section 11.2)
                     forecast.py (Forecaster protocol + 3 models)
                     logging_setup.py (structured JSON to stderr)
                     units.py (duration/size parsing)
                     exceptions.py (error hierarchy)
```

## Module layout, as it stands

| Module | Responsibility | Plan section |
|---|---|---|
| `exceptions.py` | The `DrsError` hierarchy every deliberate failure raises | AGENTS.md section 5 |
| `units.py` | Duration/size parsing (`"24h"`, `"200MiB"`) and human-readable formatting | section 11 |
| `config.py` | Load `/etc/pve/drs.yaml`, jsonschema + semantic validation, the frozen dataclass config model | section 11 |
| `config_schema.json` | The jsonschema structural half of validation | section 11.1 |
| `state.py` | `state.json`: the load vector as of the last executed balance, cooldowns, the node-local advisory `flock()` — reading degrades, writing raises | section 11.2 |
| `forecast.py` | The `Forecaster` protocol, `required_range_seconds`, and `quantile`/`seasonal_naive`/`holt_winters` | section 10 |
| `logging_setup.py` | Structured JSON logging to **stderr** | section 2.1 (amended, see [`40-cli-and-logging.md`](40-cli-and-logging.md)) |
| `metrics.py` | `PrometheusClient`, PromQL construction, `verify_metrics()`, `compute_disk_coverage()` | sections 3.1-3.4 |
| `pve.py` | `PveClient` (built on `proxmoxer`), `build_client()` | section 3.5 |
| `topology.py` | `build_topology()`: the disk/storage/group join, `D`, `S`, `Uˢᵉˣᵗ`, (C2) pins | sections 3.5-3.7, 5.1, 5.3 (C2) |
| `reserve.py` | `compute_reserve_status()`: (C4)/(C5), shared by `show-load` today and the solver later | section 5.3 (C4)/(C5) |
| `loadmodel.py` | `compute_group_load()`: the raw-series-to-`ℓ_d` blend, `min_coverage` rejection, current `L_s`/`u_s` | section 4 |
| `gates.py` | `evaluate_group_gates()`: reserve override, drift, imbalance — the act/no-act verdict, with reasoning | section 6 |
| `heuristic.py` | `run_heuristic()`: seed/repair/descend, and `evaluate_assignment()`, the section 5.4 objective shared with the (unwritten) MILP path | sections 5.4/5.5 |
| `schedule.py` | `order_moves()`: transient-feasible ordering of a target assignment's moves, deadlock reporting | section 8 |
| `payback.py` | `evaluate_plan_payback()`: the cost/benefit acceptance test, with a reserve-override exemption mirroring `gates.py`'s | section 7 |
| `cli.py` | Argument parsing, command dispatch, `--manual`, the mode-override rule, `show-load`, `verify-storages`, `plan` | section 11.3 |

Not yet written: `optimize.py`, `execute.py`. Cooldowns are now read:
`topology.py`'s (C2) per-disk pin and `heuristic.py`'s per-storage
target exclusion both consume `state.py`'s cooldown data (see
[`15-state.md`](15-state.md), [`60-topology.md`](60-topology.md) and
[`90-heuristic.md`](90-heuristic.md)) — only *writing* a cooldown still
waits on `execute.py`. Within modules that do exist: heuristic step 4
"polish" and (C2) format-compatibility eligibility in `heuristic.py` (see
[`90-heuristic.md`](90-heuristic.md)), concurrent scheduling, priority-2
ordering and staging in `schedule.py` (see [`95-schedule.md`](95-schedule.md)),
and the payback re-solve-and-retry loop plus the section 7.3 saturation
check in `payback.py` (see [`96-payback.md`](96-payback.md)).

## Why config.py depends on forecast.py

`config.py`'s semantic validation (`_check_forecast_window`) must reject a
`window.lookback` too short for the configured `forecast.model` at startup
(section 11.1) — that check needs `forecast.required_range_seconds()`. Since
`forecast.py` in turn needs `config.ForecastConfig` for its type signatures,
the import is deferred to inside the validation function rather than at
module level, breaking what would otherwise be an import cycle. See the
comment at the top of `config.py`'s `_check_forecast_window` if you touch
this.

## Where to read next

- [`10-configuration.md`](10-configuration.md) — how a YAML file becomes a
  validated `Config`, and where every default actually lives.
- [`15-state.md`](15-state.md) — `state.json`'s dataclasses, why reading it
  degrades but writing raises, the real `flock()` lock and the rename-vs
  -in-place bug it takes to get that wrong, what `show-load`/`plan`
  actually get from it today, and how its cooldown data reaches
  `topology.py`/`heuristic.py`.
- [`20-forecasting.md`](20-forecasting.md) — the forecaster protocol and its
  three implementations.
- [`30-metrics.md`](30-metrics.md) — the Prometheus client and the six
  `verify-metrics` checks.
- [`40-cli-and-logging.md`](40-cli-and-logging.md) — command dispatch, the
  `--mode` escalation rule, and why logs go to stderr.
- [`50-pve-api.md`](50-pve-api.md) — the PVE API client, why it is built on
  `proxmoxer`, and two things verified against a real cluster.
- [`60-topology.md`](60-topology.md) — the disk/storage/group join, the
  section 5.1.1 foreign-volume accounting, the shared (C4)/(C5) evaluator,
  and the per-disk cooldown pin.
- [`70-loadmodel.md`](70-loadmodel.md) — the section 4 raw-series-to-`ℓ_d`
  blend, `min_coverage` rejection, and why `tpmstate0`/`unusedN` are exempt
  from it but `efidisk0` is not.
- [`80-gates.md`](80-gates.md) — the section 6 act/no-act verdict, how
  `state.json`'s drift history now reaches it, and why the per-disk/
  per-storage cooldowns live in `topology.py`/`heuristic.py` instead.
- [`90-heuristic.md`](90-heuristic.md) — the section 5.4/5.5 objective and
  the seed/repair/descend search, cross-checked against section 14's exact
  objective totals, the storage-cooldown destination filter and its
  repair-side exemption, and what "polish" and format eligibility still owe.
- [`95-schedule.md`](95-schedule.md) — ordering a target assignment's
  moves under the section 8 transient invariant, why `cost_m = z_d` is
  exact today (not an approximation), and why the heuristic accepting a
  residual violation can still mean the scheduler reports a deadlock.
- [`96-payback.md`](96-payback.md) — the section 7 cost/benefit test,
  the `headroom_src`/`headroom_dst` gap in the plan's own cost formula,
  and why a reserve-fixing plan always passes the economic test.
