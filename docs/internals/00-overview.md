# Overview: what is built, and how it fits together

**What does this page answer?** Where does an invocation of `pve-storage-drs` go,
which module owns which piece, and how much of `IMPLEMENTATION_PLAN.md`'s
section 2 architecture actually exists right now?

## The pipeline, as specified and as built

`IMPLEMENTATION_PLAN.md` section 2 describes seven stages: collect, join,
gate, solve, cost, order, execute. As of this page, stage 1 (collect — both
Prometheus and the PVE API) and the surrounding configuration/CLI
scaffolding exist; join through execute are `IMPLEMENTATION_PLAN.md` section
12 phases 2-9 and are not yet written. Do not take this page as a claim that
the whole pipeline runs end to end — [`../manual/30-safety-and-status.md`](../manual/30-safety-and-status.md)
is the authoritative per-command status.

```
   ┌──────────────────────┐        ┌────────────────────────────┐
   │  Prometheus          │        │   Proxmox VE API           │
   │  (metrics.py)         │        │   (pve.py, via proxmoxer)  │
   └──────────┬────────────┘        └──────────────┬─────────────┘
              │ PrometheusClient,                   │ PveClient,
              │ PromQL builders,                    │ build_client()
              │ verify_metrics()                    │
              ▼                                     ▼
        ┌───────────────────────────────────────────────────┐
        │            cli.py  (argument parsing,              │
        │            command dispatch, mode-override rule)   │
        └───────────────────────┬───────────────────────────┘
                                 │
                     config.py (load + validate)
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
| `forecast.py` | The `Forecaster` protocol, `required_range_seconds`, and `quantile`/`seasonal_naive`/`holt_winters` | section 10 |
| `logging_setup.py` | Structured JSON logging to **stderr** | section 2.1 (amended, see [`40-cli-and-logging.md`](40-cli-and-logging.md)) |
| `metrics.py` | `PrometheusClient`, PromQL construction, `verify_metrics()` | sections 3.1-3.4 |
| `pve.py` | `PveClient` (built on `proxmoxer`), `build_client()` | section 3.5 |
| `cli.py` | Argument parsing, command dispatch, `--manual`, the mode-override rule | section 11.3 |

Not yet written: `topology.py`, `loadmodel.py`, `optimize.py`,
`heuristic.py`, `payback.py`, `schedule.py`, `execute.py`.

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
- [`20-forecasting.md`](20-forecasting.md) — the forecaster protocol and its
  three implementations.
- [`30-metrics.md`](30-metrics.md) — the Prometheus client and the six
  `verify-metrics` checks.
- [`40-cli-and-logging.md`](40-cli-and-logging.md) — command dispatch, the
  `--mode` escalation rule, and why logs go to stderr.
- [`50-pve-api.md`](50-pve-api.md) — the PVE API client, why it is built on
  `proxmoxer`, and two things verified against a real cluster.
