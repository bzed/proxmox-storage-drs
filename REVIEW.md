# Review of `IMPLEMENTATION_PLAN.md` (Proxmox Storage DRS)

This document is a careful, verbose review of `IMPLEMENTATION_PLAN.md`, `README.md`,
`config/drs.example.yaml`, and `.gitignore` in this repository. It is structured to be
machine-parseable: each finding has a stable ID, a severity, a section anchor, a statement of
the issue, and a concrete recommendation. A summary table precedes the detail.

The reviewer independently re-derived every number in the section 14 worked example and
verified them by hand; the results of that verification are recorded in Appendix A. A few
load-bearing external facts were checked via web search and are reported in Appendix B.

A **second pass** (section 6) reviews the updated plan after the author addressed F-01..F-25.
All original findings are resolved; seven new findings (N-01..N-07) were identified in the new
and changed material.

A **third pass** (section 7) reviews the plan after the author addressed N-01..N-07 and added
substantial new material (all-bus enumeration, snapshot handling, saferemove wipe accounting,
VM locks, load-model rescale, saturation-load redesign, fixture generator). All N-findings
are resolved; six new findings (M-01..M-06) were identified, all Low or Info severity.

A **fourth pass** (section 8) reviews the plan after the author addressed M-01..M-06 and added
the `reserve-tradeoff` fixture, the lexicographic solver path, the `ω_wipe` state-dependent
saturation guard, AGENTS.md, and the Python toolchain. All M-findings are resolved; two new
findings (K-01..K-02) were identified, both Low severity.

A **fifth pass** (section 9) reviews the plan after the author addressed K-01..K-02. Both
findings are resolved. No new findings. The plan and fixtures are clean.

A **sixth pass** (section 10) reviews the substantial new material added after the fifth pass:
the `pve-storage-drs` naming, full Debian packaging (`debian/`), two CI pipelines, the PDF
paper pipeline (`docs/paper/`, `tools/check_paper_log.py`), the documentation policy and
manpage, config-on-pmxcfs, state path, and global CLI options. Five new findings (L-01..L-05)
are identified. The first three are Medium severity and concern packaging/CI consistency with
the plan; the remaining two are Low and Info.

A **seventh pass** (section 11) reviews the first actual implementation: phases 1 and 2 of the
plan (config, metrics, forecast, CLI skeleton, PVE API client, topology, reserve), plus the
full documentation suite (`docs/internals/`, `docs/manual/`), the generalized paper pipeline
(`tools/build_paper.sh`), and the L-finding fixes. Three new findings (P-01..P-03) are
identified, all concerning config knobs documented as functional but not yet wired through in
the code, or VM-level privileges the manual omits. **Section 12** records how all three were
resolved: `ticket_refresh_seconds` and `read_workers` are now both wired through (the former
also gained a reauthenticate-and-retry-once path for a ticket that expires from an external
cause, e.g. a long `apply --confirm` wait), and the manual now names the VM-level privileges
`apply` will need.

An **eighth pass** (section 13) reviews phases 3-4: `loadmodel.py` (the section 4 load model,
wired into `show-load`), `gates.py` (the section 6 act/no-act decision), `heuristic.py` (the
section 5.4/5.5 dependency-free solver), the `pve.py` reauthenticate-and-retry path and
`topology.py` concurrent fetch from the P-01/P-02 fixes, and the `reserve.py`/`metrics.py`
extensions those modules needed. Two new findings (Q-01..Q-02) are identified, both Low.
**Section 14** records how both were resolved: `evaluate_assignment()` now implements
`objective.spread_metric: minmax` correctly (as `max(u_s)`, not `max(e_s)` — the finding's own
suggested fix would have computed the wrong quantity), and the manual now documents the
per-group Prometheus query multiplier for multi-group configs.

A **ninth pass** (section 15) reviews phases 4-5: `schedule.py`, `payback.py` and the `plan`
command. Six findings (R-01..R-06) are identified; **section 16** records how all six were
resolved.

A **tenth pass** (section 17) reviews the state/cooldown work and phases 6-7: `state.py`
(section 11.2), the cooldown wiring, `optimize.py` (CP-SAT/CBC MILP backends) and `execute.py`
(move execution, `apply`). Nine findings (S-01..S-09) are identified — two High: the CBC
backend crashes on the pulp version Debian trixie actually ships (reproduced against 2.7.0;
CI installs exactly that version and its CBC tests cannot pass), and `apply` executes plans
that failed the section 7.3 payback acceptance test, including moves the hard per-move
duration rule rejected. **Section 18** records how all nine were resolved.

An **eleventh pass** (section 19) reviews the finalized implementation: everything that landed
after the S-01..S-09 fixes — phase 8 (`auto` mode, time windows, migration cap, the re-plan
loop), section 13 crash/two-instance recovery, the section 8.1 generalized transient invariant,
concurrent execution, per-disk load time series, the section 7.3 saturation guard and its wiring
into `plan`/`apply`, and phase 9's section 10.2 forecast backtest gate (~5,900 inserted lines,
two new modules). Seven new findings (T-01..T-07) are identified: three Medium (the re-plan loop
silently does not trigger under the concurrent executor; re-plans and mid-group crashes lose the
executed moves' cooldown recording that section 9.2 step 2 mandates; the manual and example
config claim the optimizer consumes the forecaster's upper bound, which it does not), three Low
(stale "saturation check not implemented anywhere" claims contradicted by the same range's own
saturation wiring; a stale `96-payback.md` paragraph that would reintroduce the R-01 bug; three
divergent semantics for the `max_migrations_per_run` counter), one Info. **Section 20** records
how all seven were resolved.

A **twelfth pass** (section 21) reviews everything after the T-fixes: two real bugs found
dogfooding against a production cluster (the heuristic's missing whole-VM co-relocation
candidate, and the `requests` connection pool smaller than `read_workers`), five CI repairs
found the first time the pipelines actually ran, and the section 11.4 `/regex/` storage-pattern
feature (the first new plan section added since the implementation was finished). Three new
findings (U-01..U-03) are identified: one Medium (the plan's section 11.4 names a different
pattern-matching endpoint than the code implements, and the untested matched-but-unavailable
edge aborts the run with an error that does not name the pattern), one Low (a six-location
cluster of stale "not yet written" documentation claims), one Info (an undocumented second
pattern asymmetry: matched storages skip the not-`shared` warning). **Section 22** records how
all three were resolved.

A **thirteenth pass** (section 23) reviews the finalized tool's next seven commits: the `explain`
command (the last unimplemented subcommand), section 3.4's node-scoping of every PromQL query
(with the `metrics.extra_selector` override), CI installing `ortools` so the CP-SAT path is
finally exercised, a dedicated mypy venv with a loud-not-swallowed solver install, the README
rewrite, and a sweep replacing bare "section N.M" citations in operator-facing messages with
plain language. Five new findings (V-01..V-05) are identified: two Medium (the manual's
`objective.reserve_violation_penalty` entry describes a provably-dominant-P computation that has
never existed anywhere in the code, and the §9.5 pinned block the plan calls "not optional
decoration" lives only in `explain`, without its action hints, while `27-plan.md` falsely claims
`plan` shows pins too), one Low (two internally inconsistent "used" figures in the new
`29-explain.md` worked example — every other number in it verifies by hand), one Low (the CI
pip-installs `ortools` as a documented-in-workflow-only exception to AGENTS.md §9.3's absolute
"apt, never pip" rule), one Info (an untracked, referenced-nowhere helper script in the working
tree). **Section 24** records how all five were resolved.

---

## 0. Overall assessment

The plan is unusually thorough and, with the caveats below, implementable. Its strongest
properties:

1. **The worked example (section 14) is numerically correct.** I re-derived every value
   (loads, utilizations, reserve breaches, objective values, the β knob demonstration,
   ordering/transient checks, and payback arithmetic) and all of it checks out. This is rare
   and valuable; it gives the implementer an executable acceptance fixture.
2. **The data-acquisition argument (section 3) is the centerpiece and is well reasoned.** The
   decision to use the InfluxDB metric-server path (device as a *label*) rather than the
   OpenTelemetry path (device baked into the *metric name*) is correct for this use case, and
   the rationale is stated precisely.
3. **Safety is treated as a hard invariant, not a preference.** The transient reserve
   invariant (section 8.1), the soft-slack formulation of (C5) so an already-violating start
   stays repairable, and the "reserve is never traded against balance" rule (section 13) are
   the right engineering instincts.
4. **The optimizer/heuristic duality is sound.** Solving per-group, variable fixing for
   eligibility, warm-starting CP-SAT from the current assignment, and requiring the heuristic
   to share the exact feasibility/objective functions with the MILP are all good design.

The plan's main weaknesses are **omissions at the integration and operational boundaries**
rather than errors in the core model: the implementation language is never stated; deployment,
scheduling cadence, logging, and `state.json` schema are unspecified; concurrency interacts
with the transient invariant in a way that is only sketched; and several config knobs
(`min_free_bytes`, `read_factor`/`write_factor`, forecast data ranges) do not appear in the
formal model. None of these are blockers; all are fixable with small additions.

---

## 1. Summary of findings

| ID | Severity | Section | Topic |
|----|----------|---------|-------|
| F-01 | High | §2, whole doc | Implementation language is never stated |
| F-02 | High | §5.3 (C5) | `min_free_bytes` floor absent from the capacity constraint |
| F-03 | High | §4, §3.4 | `read_factor`/`write_factor` asymmetry defined in config but absent from the load formula and PromQL |
| F-04 | High | §10, config | Holt-Winters `seasonal_periods=288` needs 48h of data but `window.lookback=24h`; seasonal-naive needs 7d; the decision window cannot supply either |
| F-05 | High | §8.1, §8.2, §9 | Concurrency (`max_concurrent_migrations`, `max_concurrent_per_storage`) interacts with the transient invariant but the multi-move invariant and `concurrency_ok` are not defined |
| F-06 | Med | §6 | Drift gate is undefined on first run and when `‖ℓ_last‖₁ = 0`; alignment of disk-key union (appeared/disappeared disks) not specified |
| F-07 | Med | §9.2 | "Abort that move and trigger a re-plan" — the re-plan loop is not specified; risk of re-plan thrash mid-execution |
| F-08 | Med | §13, state | `state.json` schema is never defined (lock, last load vector, per-disk/per-storage cooldown timestamps, in-flight UPIDs) |
| F-09 | Med | §7.3 | `saturation_ceiling` "during the mirror" mixes a p95/forecast-bound `u_s` with an instantaneous added load `ω`; `u_during` is not well-defined |
| F-10 | Med | §10 | "Optimizer consumes the upper bound" — how the forecaster's upper bound is derived (especially for the default `quantile`) is unspecified |
| F-11 | Med | §3.5, §9 | Read path is O(VMs) API calls with no concurrency/batching/caching; large clusters may be slow; no rate-limit handling |
| F-12 | Med | §5.3 (C2) | A disk whose storage is in no group, or a storage appearing in two groups, is not handled; needs explicit rule + config validation |
| F-13 | Med | §5.3 (C5), §13 | Finite `reserve_violation_penalty` (1000) technically allows trading reserve for balance; tension with the §13 "never traded" claim |
| F-14 | Med | §5.5 | CP-SAT requires all coefficients integral; the concrete common scaling for continuous quantities (`e_s`, `Z_s`, `r_s`, `t`) and resulting rounding error is not specified |
| F-15 | Low | §1, §13 | "Minimal number of migrations" requirement is reinterpreted as a soft, tunable β penalty (confirmed intentional) — should be documented as an explicit requirement interpretation |
| F-16 | Low | §5.3 (C3) | VM affinity `κ` only counts within-group spread; a VM with disks in multiple groups is never counted as fragmented (acceptable, but undocumented) |
| F-17 | Low | §5.1 | `U^ext` ("foreign volumes") computation is described in prose but not given an exact formula |
| F-18 | Low | §3.5 | `format=qcow2` appears in the write path but format detection/compatibility for the eligibility rule (C2) is not described |
| F-19 | Low | §11, config | Config validation rules are not enumerated (capability_weight>0, non-empty groups, no storage in two groups, metric names non-empty, etc.) |
| F-20 | Low | §9.1, §12 | Deployment target, invocation cadence (cron/systemd), and logging are unspecified; affects `auto` mode design |
| F-21 | Low | §9.4, §12 | §14 fixture is human-readable prose only; no machine-readable fixture file (JSON/YAML) is provided for automated tests |
| F-22 | Low | §11 | No config schema version field; no migration path for future changes |
| F-23 | Info | §3.1, §3.2 | Deep Perl-internal claims (drive- prefix stripping, `instance=scsi0`, OTel name-baking) are plausible and internally consistent but unverified; the plan correctly defers to `verify-metrics` |
| F-24 | Info | §1, App. B | PVE 9.2 ships a built-in dynamic load balancer / Cluster Resource Scheduler; confirmed node-level only (does not balance across storages/FC LUNs); relationship should be documented in §1 |
| F-25 | Info | §3.4 | `quantile_over_time(0.95, (expr)[24h:5m])` subquery is valid PromQL and VictoriaMetrics-compatible; no issue, recorded for the implementer |

---

## 2. Language and technology recommendation (addresses F-01)

`IMPLEMENTATION_PLAN.md` never states the implementation language. The module layout uses `.py`
extensions and names Python-only libraries (OR-Tools CP-SAT, PuLP/CBC, `statsmodels`), and
`.gitignore` is Python-centric, so Python is strongly implied but never declared. This should
be stated explicitly with a version pin.

**Recommendation: Python 3.11+.** Justification:

| Criterion | Python 3.11+ | Go | Rust |
|---|---|---|---|
| OR-Tools CP-SAT (the preferred solver) | First-class (`ortools` wheels) | Cgo bindings only, painful | C bindings, immature |
| CBC via PuLP | Native (`pulp`) | None standard | None standard |
| `statsmodels` (Holt-Winters) | Native | Must reimplement | Must reimplement |
| Prometheus / HTTP client | `prometheus-api-client`, `requests` | Excellent stdlib | Good (`reqwest`) |
| YAML config + units | `pyyaml`/`ruamel` | Fine | Fine |
| Single-binary deployment | Not native (needs venv or PyInstaller/Nuitka) | Native | Native |
| Ops-team maintainability on a PVE host | High (PVE ships Python; staff know it) | Medium | Low |

The solver and forecasting libraries are the deciding factor: OR-Tools CP-SAT and statsmodels
have no usable equivalent in Go or Rust without significant reimplementation, and the plan
explicitly makes CP-SAT the *preferred* backend and Holt-Winters a required (if optional)
forecaster. A Python venv (or a Nuitka/PyInstaller-frozen binary) deployed to a management host
is the pragmatic choice. Go would only win if single-binary, no-runtime deployment were a hard
requirement — but the plan never makes that a requirement, and the heuristic fallback already
provides a dependency-free path for constrained environments.

**Concrete additions to the plan:**
- State "Python 3.11+" in section 2.
- Specify a `pyproject.toml` with pinned dependencies: `ortools>=9`, `pulp>=2.7` (CBC wheel),
  `statsmodels>=0.14`, `prometheus-api-client`, `requests`, `pyyaml`/`ruamel.yaml`,
  `jsonschema` (for config validation).
- Specify the test stack: `pytest`, `pytest-xdist` (independent per-group tests), and a
  machine-readable fixture (see F-21).
- Specify the deployment target explicitly (see F-20): a management host with network access
  to the PVE API (8006) and Prometheus, invoked via systemd timer / cron.

A Go port of the *heuristic-only* path would be a reasonable future option for an agent that
runs on the PVE hosts themselves, but that is out of scope for the first implementation.

---

## 3. Detailed findings

### F-01 — Implementation language never stated (High)
**Where:** section 2, whole document.
**Issue:** No language or version is declared; it is only implied by `.py` module names and
Python library references.
**Recommendation:** See section 2 above. Add an explicit "Implementation: Python 3.11+" line
and a dependency manifest to the plan.

### F-02 — `min_free_bytes` floor absent from (C5) (High)
**Where:** §5.3 (C5); config `snapshot_reserve.min_free_bytes`.
**Issue:** The config defines a flat free-space floor (`min_free_bytes`, "whichever is larger"),
but (C5) only models the `f_s · Z_s` term:
```
Σ_d z_d·x_{d,s} + U^ext + f_s·Z_s ≤ C_s + r_s
```
The floor never appears. An implementer following the formula literally would ignore it.
**Recommendation:** Replace the reserve term with `max(f_s·Z_s, min_free_bytes_s)` and note
that `max` of a continuous variable and a constant is linearizable with two constraints
(`R_s ≥ f_s·Z_s` and `R_s ≥ min_free_bytes_s`, then use `R_s` in (C5)). The transient
invariant in §8.1 must use the same `max`.

### F-03 — `read_factor`/`write_factor` absent from the load model (High)
**Where:** §4 load formula; §3.4 PromQL; config `load_weights.read_factor`/`write_factor`.
**Issue:** The config defines read/write asymmetry "applied within ops and bytes," but the §4
formula `ℓ_d = w_t·î_d + w_o·ô_d + w_b·b̂_d` treats reads and writes symmetrically, and the
§3.4 PromQL sums `rate(rd_*) + rate(wr_*)` with equal weight. There is no place where
`read_factor`/`write_factor` are applied, so the knob is currently dead configuration.
**Recommendation:** Decide and document where asymmetry is applied. Two clean options:
  - (a) In PromQL: `read_factor·rate(rd_X) + write_factor·rate(wr_X)` inside each `sum by`.
  - (b) In `loadmodel.py`: pull read and write series separately and combine with the factors
    engine-side (keeps PromQL simpler and the factors testable in isolation).
Option (b) is preferable because it keeps the factors in the tested engine rather than in
deployed PromQL strings, and because it also cleanly applies to the iotime term if desired.
Update §4's formula and the config comment to match.

### F-04 — Forecast data range vs. decision window (High)
**Where:** §10; config `window.lookback=24h`, `window.seasonal_lookback_days=7`,
`forecast.holt_winters.seasonal_periods=288`.
**Issue:** There are two latent inconsistencies:
  - Holt-Winters requires "at least 2×seasonal_periods samples." With `seasonal_periods=288`
    (24h at 5m step) that is 576 samples = 48h, but the default decision window is 24h. With the
    default window, Holt-Winters can **never** satisfy its minimum and will always fall back
    to `quantile`. The minimum-data rule is correct, but the defaults make the feature
    unreachable.
  - Seasonal-naive "compares the same hour-of-day over the last `seasonal_lookback_days`" (7),
    which needs 7 days of range data, also far outside the 24h decision window.
**Recommendation:** Make forecasters own their data acquisition. Specify that `metrics.py`
must support pulling an arbitrary range via `query_range` (not limited to `window.lookback`),
and that each forecaster declares the range it needs:
  - `quantile`: `window.lookback` (24h).
  - `seasonal_naive`: `max(window.lookback, seasonal_lookback_days)` (7d).
  - `holt_winters`: `max(window.lookback, 2·seasonal_periods·step)` (48h).
Document that enabling `seasonal_naive`/`holt_winters` requires Prometheus to retain that much
history. Alternatively, raise the default `lookback` when a seasonal model is selected, and
emit a config-validation error when the window is too short for the chosen forecaster.

### F-05 — Concurrency vs. the transient invariant (High)
**Where:** §8.1, §8.2, §9; config `max_concurrent_migrations`, `max_concurrent_per_storage`.
**Issue:** §8.1 states the transient invariant for a *single* in-flight move:
```
used_b + z_d + f_b·max(Z_b, z_d) ≤ C_b
```
But config permits `max_concurrent_migrations > 1` and `max_concurrent_per_storage > 1`. With
multiple moves in flight simultaneously, the target storage `b` must satisfy the reserve for
the **sum** of all in-flight disks landing on it at once, and the source relief does not occur
until each completes. §8.2 references `concurrency_ok(state, m)` but never defines it, and §9.2
describes a strictly sequential poll-then-next loop that implies concurrency = 1.
**Recommendation:**
  - Generalize the transient invariant to a *set* of in-flight moves `M`:
    ```
    used_b + Σ_{m∈M : dst(m)=b} z_{disk(m)} + f_b·max(Z_b, max_{m∈M:dst(m)=b} z_{disk(m)}) ≤ C_b
    ```
  - Define `concurrency_ok(state, m)` as: adding `m` to the current in-flight set keeps the
    generalized invariant on every storage, respects `max_concurrent_migrations` (global),
    `max_concurrent_per_storage` (per-storage, both as source and target), and any cooldown.
  - Reconcile §9.2 (sequential) with concurrency: either default `max_concurrent_migrations=1`
    (already the config default) and document that >1 requires the generalized invariant, or
    make §9.2 explicitly launch up to the cap and poll all in-flight UPIDs each cycle.
  - Note that with `max_concurrent_per_storage=1`, two moves targeting the same storage are
    serialized automatically, which is the common safe configuration.

### F-06 — Drift gate edge cases (Med)
**Where:** §6.
**Issue:** `‖ℓ_now − ℓ_last‖₁ / ‖ℓ_last‖₁` is undefined on the first run (no `ℓ_last`) and when
`‖ℓ_last‖₁ = 0` (all loads zero). The "appeared/disappeared disks count their full load as
drift" rule needs the two vectors aligned over the **union** of disk keys, with missing entries
treated as 0; this alignment is not specified.
**Recommendation:** Specify: on first run, skip the drift gate and proceed to the imbalance
gate. Treat `‖ℓ_last‖₁ = 0` as "always drifted" (i.e., proceed). Define alignment over the
union of disk keys present in either vector, with absent disks treated as load 0 in the
opposing vector. State that the drift vector is computed over the group's current movable
disk set union the last-balance movable disk set.

### F-07 — Re-plan loop during execution (Med)
**Where:** §9.2 ("mismatch → abort that move and trigger a re-plan").
**Issue:** Re-planning mid-execution is invoked but not defined. Does a re-plan re-run the
full pipeline (gates, solver, payback, ordering)? Is the already-executed prefix of the plan
treated as the new current state? Is there a bound on re-plan attempts to prevent a loop in a
churning cluster?
**Recommendation:** Specify a re-plan protocol: (1) on a per-move state mismatch, abort the
remaining plan, mark the executed moves as done in `state.json`, and re-invoke the whole
pipeline from the new current state; (2) cap re-plan attempts per run (e.g., 3) and degrade
to "report and stop" if exceeded; (3) in `auto` mode, ensure a re-plan still respects the
remaining time window. Document that re-plan is the expected, normal path, not an error.

### F-08 — `state.json` schema undefined (Med)
**Where:** §13; references throughout.
**Issue:** `state.json` is referenced for the advisory lock, last executed load vector,
per-disk cooldown, per-storage cooldown, and in-flight UPIDs, but its schema is never given.
**Recommendation:** Specify a versioned schema, e.g.:
```json
{
  "schema_version": 1,
  "lock": {"pid": int, "acquired_at": iso8601},
  "last_balance": {"at": iso8601, "load_vector": {"<group>:<vmid>:<device>": float}},
  "cooldowns": {
    "disk": {"<group>:<vmid>:<device>": iso8601_last_moved},
    "storage": {"<group>:<storage>": iso8601_last_involved}
  },
  "inflight_upids": ["UPID...", ...],
  "staged_disks": ["<group>:<vmid>:<device>"]
}
```
Also specify the lock mechanism (recommend `fcntl.LOCK_EX` on the file, with a stale-lock
recovery rule: if the PID in `lock.pid` is not alive, reclaim it) and atomic-write discipline
(write temp + `os.replace`).

### F-09 — `saturation_ceiling` "during the mirror" is ill-defined (Med)
**Where:** §7.3.
**Issue:** The rule defers a move if it "would push `u_src` or `u_dst` above
`saturation_ceiling` *during* the mirror." But `u_s` is a p95/forecast upper bound over the
lookback window, not an instantaneous load. Adding `ω` (in-flight I/O, ≈1.0) to a robust
statistic conflates a window statistic with an instantaneous addition.
**Recommendation:** Define `u_during_s` explicitly, e.g. `u_during_s = u_s_forecast + ω_src`
(or `ω_dst`), where `u_s_forecast` is the forecaster's upper bound for the move's expected
duration, and the ceiling check is `u_during_s ≤ saturation_ceiling`. Document that this is a
best-effort guard, not a hard physical limit, and that `max_single_move_duration` is the hard
per-move bound.

### F-10 — Forecaster "upper bound" derivation unspecified (Med)
**Where:** §10.
**Issue:** "The optimizer consumes the upper bound, not the point estimate." The `Forecaster`
protocol returns a point estimate and an upper bound, but how the upper bound is derived is
not defined — especially for the default `quantile`, where the point estimate *is* p95. Is the
upper bound p95 (same as point) or a higher quantile (p99)?
**Recommendation:** Specify per implementation:
  - `quantile`: upper bound = the same p95 (so point == upper bound; the optimizer consumes
    p95). Or introduce a separate `upper_quantile` (e.g., 0.99) for the bound.
  - `seasonal_naive`: upper bound = p95 across the same-hour-of-day samples (point = median or
    p50).
  - `holt_winters`: upper bound = point + z·σ from the fitted residuals (z=2), or a prediction
    interval.
Make the relationship between `window.quantile`, the point estimate, and the upper bound
explicit so the optimizer's input is unambiguous.

### F-11 — Read path is O(VMs) with no concurrency/caching (Med)
**Where:** §3.5, §9.
**Issue:** Per-VM disk config requires `GET /nodes/{node}/qemu/{vmid}/config` for every VM —
O(N) requests, plus per-storage `/status` and `/content`. For a few hundred VMs this is slow
and load-bearing for every run and every pre-move re-validation. No batching, concurrency,
caching, or rate-limit handling is discussed.
**Recommendation:** Specify a bounded-concurrency read phase (e.g., a thread pool of 8-16) for
the per-VM config fetches, with a short per-request timeout; cache topology within a single
run (the pre-move re-validation in §9.2 must bypass the cache for the specific VM/storage
being moved, but can reuse the rest). Document expected API call counts. Note that PVE has no
batch config endpoint, so concurrency is the only lever.

### F-12 — Ungrouped and multi-group storages (Med)
**Where:** §5.3 (C2), §11.
**Issue:** If a disk's current storage `σ₀(d)` is in no configured group, it has no eligible
targets and is effectively immovable; if a storage appears in two groups, a disk's group is
ambiguous. Neither case is handled or validated.
**Recommendation:** Add config validation: each storage may appear in at most one group
(error otherwise). Disks whose storage is in no group are excluded and pinned to current
(contributing to `U^ext` of their storage), and reported in `show-load`/`explain` as
"ungrouped, not managed."

### F-13 — Finite `reserve_violation_penalty` vs. "never traded" (Med)
**Where:** §5.3 (C5), §13.
**Issue:** §13 states "the reserve constraint is never traded against balance," but (C5) uses
a finite `P = reserve_violation_penalty = 1000`. With finite P, a sufficiently large imbalance
reduction could in principle outweigh a small reserve violation in the objective. In practice
P=1000 dominates the normalized objective (imbalance terms are O(number of storages)), so it
is *effectively* hard, but not *provably* hard.
**Recommendation:** Either (a) keep P finite and reword §13 to "the reserve is effectively
hard; the soft slack exists solely to keep already-violating starts feasible and is driven to
zero whenever physically possible," or (b) split into a hard `≤ C_s` constraint **plus** a
separate, non-objective repair slack used only when the hard model would be infeasible. Option
(a) is simpler and matches the worked example; recommend (a) with the rewording.

### F-14 — CP-SAT integral scaling underspecified (Med)
**Where:** §5.5.
**Issue:** CP-SAT requires all coefficients and variables integral. §5.5 says "scale ℓ by
10⁶ and z to MiB and round," but the objective also contains continuous-derived terms `e_s`
(utilization deviation), `Z_s`, `r_s`, and possibly `t`. Their concrete scaling and the
rounding error introduced (especially for `e_s`, which drives the primary objective) are not
given.
**Recommendation:** Specify a single integer scale factor `K = 10⁶` applied to all
load/utilization quantities (`ℓ`, `e_s`, `u_s`, `t`, `r_s`), and MiB for all sizes (`z_d`,
`Z_s`, capacities). Round after scaling; bound the rounding error (≤ 1e-6 in load units, ≤ 1
MiB in size) and assert it is negligible vs. the objective weights. Note that `β`, `κ` terms
are integer counts and need no scaling, and that `γ` is per-MiB so `γ·z_d` is integral when
`z_d` is MiB and `γ` is rational. Provide the scaled objective explicitly.

### F-15 — "Minimal migrations" reinterpreted as soft β (Low, confirmed intentional)
**Where:** §1, §5.4, §14.3.
**Issue:** The requirement "number of migrations must be minimal" is implemented as a soft,
tunable penalty that is traded off against imbalance (β=0.25 → 3 moves, β=0.50 → 2 moves in
the fixture). This is a reinterpretation, not a strict minimum.
**Recommendation:** Confirm and document this as an explicit requirement interpretation in
§1 or §15's traceability table: "'minimal' is implemented as a tunable preference (β) that
balances move count against imbalance reduction, demonstrated in §14.3." (Confirmed with the
author as intended.)

### F-16 — `κ` only counts within-group spread (Low)
**Where:** §5.3 (C3), §5.4.
**Issue:** The problem is solved per-group, so `y_{v,s}` and the `κ` term only count a VM's
spread across storages *within one group*. A VM with disks in two different groups is never
counted as fragmented. This is a reasonable consequence of per-group decomposition but is
undocumented.
**Recommendation:** Add one sentence to §5.4 noting that `κ` measures within-group
fragmentation only, and that cross-group disk placement is by definition immutable
(a disk never leaves its group), so cross-group spread is not a meaningful penalty.

### F-17 — `U^ext` formula not given (Low)
**Where:** §5.1, §13 (`count_foreign_volumes`).
**Issue:** `U^ext` is "bytes on `s` consumed by volumes DRS does not manage," described in
prose, but the exact computation (sum of which volumes, from which endpoint, with what owner
filter) is not given.
**Recommendation:** Specify: `U^ext_s = Σ_{vol ∈ /storage/s/content} size(vol)` for every
volume whose `(vmid, device)` is not in the current movable disk set `D` of `s`'s group
(includes templates, ISOs, orphaned volumes, and disks of excluded/ungrouped VMs). Note that
orphaned target volumes from prior failed moves (§9.3) are counted here until removed, which
is the intended behavior.

### F-18 — Disk format compatibility in eligibility (Low)
**Where:** §3.5, §5.3 (C2).
**Issue:** The write path mentions `[format=qcow2]`, and (C2) excludes a storage that "cannot
hold the disk's format," but how the source disk's format is detected and how target format
compatibility is decided is not described.
**Recommendation:** Specify: detect source format from the VM config (e.g., raw on LVM,
qcow2 on directory/zfs); for shared LVM the format is raw and `move_disk` defaults to raw on
the target; (C2) fixes `x_{d,s}=0` when `s`'s `content`/type cannot store the disk's format.
Note that format conversion (raw→qcow2) is out of scope and should be disabled by default.

### F-19 — Config validation rules not enumerated (Low)
**Where:** §11.
**Issue:** `config.py` "loads/validates YAML" but the validation rules are not listed.
**Recommendation:** Enumerate at least: `capability_weight > 0`; each group non-empty; each
storage in at most one group; `reserve_factor ≥ 0`; `0 ≤ drift_threshold, imbalance_threshold
≤ 1`; `quantile ∈ (0,1)`; `min_coverage ∈ (0,1]`; metric names non-empty; labels non-empty and
distinct; `rate_window ≥ 4×` the (configurable) push interval; `payback_ratio > 0`;
`saturation_ceiling ∈ (0,1]`; time-window `start < end` (or crosses midnight explicitly);
`window.lookback` long enough for the selected forecaster (see F-04). Validate with
`jsonschema` against a generated schema.

### F-20 — Deployment, cadence, logging unspecified (Low)
**Where:** §9.1, §12.
**Issue:** Where the engine runs, how often it is invoked in `auto` mode, and how it logs are
not specified.
**Recommendation:** Specify: runs on a management host (not necessarily a PVE node) with
network access to the PVE API and Prometheus; invoked by a systemd timer or cron (e.g., every
15-30 min); `time_windows` constrain when *moves* execute, not when the engine is invoked (the
engine may plan outside the window and execute within it). Specify logging: structured logs
(JSON) to a file and optionally syslog, with levels, including every gate decision, every move
issued and its UPID, and every abort/re-plan. This matters for unattended `auto` operation.

### F-21 — No machine-readable fixture (Low)
**Where:** §14, §12.
**Issue:** §14 is an excellent acceptance fixture but exists only as prose; an implementer
must transcribe it, risking transcription error.
**Recommendation:** Add `tests/fixtures/fc-tier1.yaml` (and a JSON variant of the expected
two-move and three-move plans) so tests can assert exact numbers. Include both β variants.

### F-22 — No config schema version (Low)
**Where:** §11.
**Issue:** No `schema_version` field; future config changes have no migration path.
**Recommendation:** Add `schema_version: 1` at the top of the config and have `config.py`
reject unknown major versions with a clear message.

### F-23 — Deep PVE Perl-internal claims unverified (Info)
**Where:** §3.1, §3.2.
**Issue:** The plan states specific Perl-internal behavior: `vmstatus(undef, 1)` with `full=1`
issuing QMP `query-blockstats`; the `drive-` prefix stripping so the device is `scsi0`; the
`InfluxDB.pm` flattening that puts the device in an `instance` tag; and the OpenTelemetry
plugin baking the device into the metric *name* via `_convert_node_metrics_recursive`. These
are the load-bearing facts for the entire data path. Web search did not independently confirm
the exact field/tag names (and some search results appeared unreliable).
**Recommendation:** These are plausible and internally consistent, and the plan correctly
mandates `drs verify-metrics` as the validation gate before any reliance. Treat §3.1/§3.2 as
*claims to be confirmed by `verify-metrics` against the live system*, not as verified facts.
Recommend the implementer run `verify-metrics` first against the actual PVE 9.2 + Telegraf
deployment and record the confirmed metric/label names before building anything else. If the
OTel name-baking claim is wrong, the "InfluxDB path is strictly superior" conclusion still
holds (device-as-label is the right design regardless), so the recommendation is robust to that
uncertainty.

### F-24 — Relationship to the PVE 9.2 built-in balancer (Info)
**Where:** §1.
**Issue:** PVE 9.2 (released 2026-05-21) ships a built-in dynamic load balancer / Cluster
Resource Scheduler. Per the author, it migrates VMs across hypervisors (nodes) only and does
not balance across storages or underlying FC LUNs — so it is complementary to this project,
not duplicative. This relationship is not stated in the plan.
**Recommendation:** Add a sentence to §1 (Non-goals or Operating assumptions) noting that the
PVE 9.2 built-in CRS handles node-level VM placement and explicitly does *not* perform
cross-storage disk balancing, which is the niche this tool fills. Also note an interaction
risk: the built-in CRS may live-migrate a VM between nodes during a Storage-DRS plan; §9.2
already re-fetches the node before each move, which mitigates this — reference that mitigation
here.

### F-25 — PromQL subquery validity (Info, no action)
**Where:** §3.4.
**Note:** `quantile_over_time(0.95, ( <expr> )[24h:5m])` is valid PromQL subquery syntax and is
supported by VictoriaMetrics. `rate()` over counter resets and `sum by (vmid, device)`
collapsing `nodename` are correct for a VM that live-migrated between nodes. No issue; recorded
so the implementer does not second-guess the query shape.

---

## 4. Cross-cutting recommendations

1. **Add an explicit "Implementation" subsection** to §2 covering: language (Python 3.11+),
   dependency manifest, deployment target, invocation cadence, and logging. These are all
   currently implied and should be explicit (F-01, F-20).
2. **Reconcile every config knob with the formal model.** Audit `config/drs.example.yaml`
   against §4-§9 and ensure every knob appears in exactly one formula: `min_free_bytes` (F-02),
   `read_factor`/`write_factor` (F-03), `max_concurrent_*` (F-05), `saturation_ceiling` (F-09).
   A knob with no formula is a bug waiting to happen.
3. **Specify the forecast data contract.** Let forecasters declare their required range and
   have `metrics.py` serve it (F-04, F-10).
4. **Generalize the transient invariant to sets of in-flight moves** and define
   `concurrency_ok` precisely (F-05).
5. **Provide a machine-readable fixture** for §14 and assert against it in CI (F-21).
6. **Specify `state.json`** schema, lock, and atomic writes (F-08).

---

## 5. Open questions for the author

These were put to the author and resolved during this review; recorded here for the
implementer.

1. **Built-in balancer overlap (resolved).** The PVE 9.2 CRS is node-level only; this project is
   complementary. Document the relationship (F-24).
2. **Language (resolved).** Author delegated the choice; this review recommends Python 3.11+
   (§2/F-01).
3. **"Minimal migrations" semantics (resolved).** The soft β penalty is intentional; document
   it as an explicit interpretation (F-15).

No further questions block the review. The remaining items are recommendations the implementer
should fold into the plan before or during implementation.

---

## 6. Second-pass review of the updated plan

The plan grew from 890 to 1305 lines. `config/drs.example.yaml` grew from 166 to 198 lines.
Two fixture files were added: `tests/fixtures/fc-tier1.yaml` (input) and
`tests/fixtures/fc-tier1.expected.json` (expected derivations). This section records the
resolution status of every original finding and presents new findings found in the updated
material.

### 6.1 Resolution of original findings

All 25 original findings (F-01..F-25) have been addressed. Summary:

| ID | Status | How resolved |
|----|--------|--------------|
| F-01 | Resolved | §2.1 states "Language: Python 3.11+" with dependency table, deployment, cadence, logging |
| F-02 | Resolved | §5.3 (C5) now has `R_s ≥ f_s·Z_s` and `R_s ≥ min_free_bytes_s`; linearization explained |
| F-03 | Resolved | §4 now has `raw_X(d) = ρ·rd_X + ω·wr_X` applied engine-side; §3.4 fetches read/write separately (six queries); config updated |
| F-04 | Resolved | §10.1: each forecaster declares `required_range()`; `metrics.py` serves arbitrary range; §11.1 validates `lookback ≥ required_range()` |
| F-05 | Resolved | §8.1 generalized invariant over in-flight set `M`; `concurrency_ok` defined with 5 conditions; §9.2 handles concurrent polling |
| F-06 | Resolved | §6: vector alignment over union of keys; degenerate-cases table; `ℓ_last` recorded only after executed migrations |
| F-07 | Resolved | §9.2: full 5-step re-plan protocol; `max_replans_per_run` (default 3); time-window inheritance |
| F-08 | Resolved | §11.2: versioned `state.json` schema; `fcntl.LOCK_EX`; stale-lock recovery; atomic writes; `inflight_upids` discipline |
| F-09 | Resolved | §7.3: `u_during(s) = û_s(duration_d) + Σω` defined explicitly; noted as best-effort |
| F-10 | Resolved | §10.1 table: `quantile` p95/p99, `seasonal_naive` median/p95, `holt_winters` point+z·σ; `upper_quantile` added to config |
| F-11 | Resolved | §3.5: bounded thread pool (8–16); per-run topology cache; cache-bypass for pre-move re-validation; expected call count |
| F-12 | Resolved | §5.3 (C2): ungrouped disks pinned, counted in `U^ext`, reported; §11.1 validates "no storage in two groups" |
| F-13 | Resolved | §5.3: two approaches — lexicographic (preferred, provably correct) and single-stage big-M (simpler); §13 restated precisely with the bound |
| F-14 | Resolved | §5.5: scaling table (K=10⁶ for load, MiB for size); pre-multiply for `c_s`; scaled objective given; rounding-error assertion |
| F-15 | Resolved | §1: "Requirement interpretation: minimal number of migrations" subsection added |
| F-16 | Resolved | §5.4: "κ measures within-group fragmentation only" with explanation |
| F-17 | Resolved | §5.1.1: explicit `U^ext` formula and composition |
| F-18 | Resolved | §3.5: "Disk format" paragraph — detect from `/content`, preserve source format, conversion out of scope |
| F-19 | Resolved | §11.1: full validation table (18 rules) |
| F-20 | Resolved | §2.1: deployment target, cadence (systemd timer, 15–30 min), structured JSON logging |
| F-21 | Resolved | `tests/fixtures/fc-tier1.yaml` + `fc-tier1.expected.json` added; expected values generated by exhaustive enumeration |
| F-22 | Resolved | `schema_version: 1` in config; §11 rejects unknown major versions |
| F-23 | Updated | §3.1 "Verification status" paragraph: Perl claims read from pve-manager/qemu-server source, operator confirmed empirically; Telegraf naming still deferred to `verify-metrics` |
| F-24 | Resolved | §1: "Relationship to the PVE 9.2 Dynamic Load Balancer" subsection; interaction risk noted |
| F-25 | No action | Still valid; no change needed |

### 6.2 New findings summary

| ID | Severity | Section | Topic |
|----|----------|---------|-------|
| N-01 | High | §5.5 | CP-SAT scaling silently zeroes the γ (bytes-migrated) term at default weight |
| N-02 | Med | §14, fixtures | Fixture input YAML omits `beta_move_count`; the beta sweep is only in the expected file |
| N-03 | Med | §14, fixtures | Fixture expected file doesn't test ordering or post-plan reserve status |
| N-04 | Low | config vs §14 | Config example has san-c `capability_weight: 0.5`; fixture and §14 use `1.0` — same names, different values |
| N-05 | Low | §7.3 | `saturation_ceiling · c_s` ambiguous: unclear whether `û_s` is `L_s` (load) or `u_s` (normalized utilization) |
| N-06 | Low | §11.1 | Validation requires `rate_window ≥ 4 × pvestatd push interval` but the push interval is not in config |
| N-07 | Low | §5.5 | `round(K / c_s)` introduces a capability-weight rounding error for non-binary `c_s` (e.g., 0.7) |

### 6.3 New findings — detail

#### N-01 — CP-SAT scaling silently zeroes the γ term at default weight (High)
**Where:** §5.5.
**Issue:** The plan specifies `γ_scaled = round(γ · K / 2²⁰)` per MiB, with `K = 10⁶`. At the
default `γ = 0.05/TiB`:
```
γ_scaled = round(0.05 × 10⁶ / 1,048,576) = round(0.0477) = 0
```
Verified by computation. The bytes-migrated penalty vanishes entirely in CP-SAT, making it
produce plans that ignore disk size when choosing which disks to move — a behavioral
divergence from CBC and the heuristic, which use continuous coefficients and preserve γ.
The §14 fixture's β-knob demonstration relies on `γ·0.5 TiB = 0.025` being non-zero; with
CP-SAT, that term would be zero, and the acceptance/rejection arithmetic at β=0.25 vs 0.50
would change (the third move's cost becomes `−0.400 + 0.250 + 0 = −0.125` vs
`−0.400 + 0.500 + 0 = +0.0.125` — still accepts/rejects, but for a different reason, and only
because γ is small enough that the sign doesn't flip in this case).

The minimum γ that survives rounding is `2²⁰ / (2·K) ≈ 0.524/TiB` — ten times the default.
Any operator using CP-SAT with the default `γ = 0.05` gets no bytes-migrated penalty at all,
silently.
**Recommendation:** Either (a) raise `K` so that `γ·K/2²⁰ ≥ 0.5` at the default γ (requires
`K ≥ 2²⁰/(2·0.05) ≈ 10.5 × 10⁶`, so `K = 10⁷` suffices and keeps numbers manageable); or (b)
express `z_d` in a coarser unit (e.g., centi-TiB, `2²⁰/100`) so `γ_scaled = round(γ·K/100) =
round(500) = 500`; or (c) document the minimum effective γ and emit a config-validation warning
when `γ` is below it and `solver.backend` is `cpsat` or `auto`. Option (a) is simplest: change
`K` to `10⁷` and re-derive the rounding bound. The plan should also add a test that asserts
`γ_scaled > 0` at default weights.

#### N-02 — Fixture input YAML omits `beta_move_count` (Med)
**Where:** `tests/fixtures/fc-tier1.yaml`, `tests/fixtures/fc-tier1.expected.json`.
**Issue:** The input fixture's `objective` block has `alpha_spread`, `gamma_move_bytes_per_tib`,
and `kappa_vm_affinity`, but no `beta_move_count`. The expected file has two cases with
`beta_move_count: 0.25` and `0.50`. An implementer reading the fixture must infer from the
expected file that beta is swept — the input doesn't say so. The fixture contract (what the
test harness feeds in, what it checks) is implicit.
**Recommendation:** Either add a `beta_values: [0.25, 0.50]` list to the input fixture's
`objective` block and have the test iterate over it, or add a comment to the expected file
naming the input convention. The current structure works but is under-documented for a
fixture meant to be consumed by an AI agent.

#### N-03 — Fixture doesn't test ordering or post-plan reserve status (Med)
**Where:** `tests/fixtures/fc-tier1.expected.json`.
**Issue:** The `expected_moves` arrays are alphabetically sorted by disk key, not in execution
order. §14.4 specifies `102:scsi0` first (it repairs the reserve violation), but the fixture
lists `101:scsi1` first. An implementer testing the scheduler (§8) against this fixture cannot
verify the ordering. The fixture also lacks post-plan reserve-violation status — the expected
file has `expected_final_loads` but not the `used + f·Z_s` values or the `violates_reserve`
flag for the final state. An implementer testing the transient invariant (§8.1) must derive
these separately.
**Recommendation:** Add an `expected_order` field to each case (an ordered list of move keys)
and an `expected_final_reserve` section mirroring the `initial` block (per-storage `used_tib`,
`largest_tib`, `required_tib`, `violates_reserve`). The §14.4 transient checks (5.0 ≤ 8.0,
4.5 ≤ 8.0, 5.0 ≤ 8.0) should be assertable from the fixture.

#### N-04 — Config example vs fixture discrepancy on san-c capability_weight (Low)
**Where:** `config/drs.example.yaml` vs `tests/fixtures/fc-tier1.yaml` and §14.
**Issue:** The config example has `san-c` with `capability_weight: 0.5` under group `fc-tier1`;
the fixture and §14.1 state "all `capability_weight = 1.0`". Same group name, same storage
names, different values. An implementer who assumes the config example matches the fixture
will get wrong numbers. The config is an illustrative example (showing the 0.5 feature), not
the fixture, but the reuse of names is confusing.
**Recommendation:** Either (a) set `san-c` to `capability_weight: 1.0` in the config example to
match the fixture (and show the 0.5 feature on a different storage, e.g., `san-d` in `fc-tier2`),
or (b) add a comment to the config: "Note: the §14 fixture uses capability_weight 1.0 for all
three; the 0.5 here is an unrelated illustration of the knob."

#### N-05 — `saturation_ceiling · c_s` ambiguity in §7.3 (Low)
**Where:** §7.3.
**Issue:** The check is `u_during(src) ≤ saturation_ceiling · c_src`. If `û_s` is the
forecaster's upper bound in *load* units (`L_s`), then `L_s + ω ≤ 0.85 · c_s` is correct and
equivalent to `u_s + ω/c_s ≤ 0.85`. If `û_s` is the *normalized* utilization (`u_s = L_s/c_s`),
then the check should be `u_s ≤ saturation_ceiling` without the `c_s` multiplication.
Multiplying by `c_s` when `u_during` is already normalized would set a *lower* ceiling for less
capable storages (e.g., 0.425 for `c=0.5`), double-penalizing them. The plan doesn't state
which `û_s` is.
**Recommendation:** Add one sentence: "`û_s` is the forecaster's upper bound on `L_s` (load,
not normalized utilization), so the check is `L_s + ω ≤ saturation_ceiling · c_s`, equivalently
`u_s + ω/c_s ≤ saturation_ceiling`." This makes the `c_s` factor's role clear.

#### N-06 — pvestatd push interval not in config (Low)
**Where:** §11.1.
**Issue:** The validation rule `rate_window ≥ 4 × pvestatd push interval` references a PVE-side
setting that is not in the config. The tool cannot validate this without knowing the push
interval. The config has no `pvestatd_interval` field.
**Recommendation:** Either add a `metrics.pvestatd_push_interval` config field (default `60s`,
matching PVE's default) and validate against it, or reword the rule to "the operator must
ensure `rate_window ≥ 4×` the pvestatd push interval; `verify-metrics` should report the
observed resolution and warn if `rate_window` is too short." The former is more automatable.

#### N-07 — `round(K / c_s)` capability-weight rounding (Low)
**Where:** §5.5.
**Issue:** "Scale each storage's load by `round(K / c_s)`" introduces a rounding error when
`c_s` is not a clean divisor of `K`. E.g., `c_s = 0.7` gives `round(10⁶/0.7) = 1,428,571` vs
the true `1,428,571.43`, a relative error of ~3×10⁻⁷. This causes a slight capability-weighting
error at the optimum — a storage assigned 0.7× capability gets 0.6999998× in CP-SAT. Negligible
for balance, but it means CP-SAT and CBC may produce slightly different assignments for
non-binary `c_s`, which complicates the "backends are directly comparable" requirement.
**Recommendation:** Document the bound: `|round(K/c_s) - K/c_s| / (K/c_s) ≤ c_s/(2K)`, which is
< 10⁻⁶ for any `c_s ≥ 1` and `K = 10⁶`. Note that this is below the solver's `mip_gap` (0.02)
and therefore cannot change the selected plan. No action needed beyond the documentation.

### 6.4 Fixture verification

The fixture's expected values were independently verified:

- **Objective values:** 3-move (β=0.25): `1.0×1.133333 + 0.25×3 + 0.05×3.0 + 0.5×1 = 2.533333` ✓.
  2-move (β=0.50): `1.0×1.533333 + 0.50×2 + 0.05×2.5 + 0.5×1 = 3.158333` ✓.
- **Payback:** duration/cost/benefit/ratio for both moves and the rejected archive disk all
  match to the precision given (see Appendix A).
- **β-knob consistency:** at β=0.25 the 3-move objective (2.533333) beats the 2-move
  (2.658333); at β=0.50 the 2-move (3.158333) beats the 3-move (3.283333). The crossover is
  correct.
- **Exhaustive-enumeration claim:** the plan states expectations were generated by enumerating
  all `3⁶ = 729` assignments. Spot-checks of alternative assignments (e.g., 102:scsi0→san-b
  instead of →san-c) confirm the stated optima are lower. The claim is plausible; full
  re-enumeration was not performed.

The fixture is a sound acceptance test. The gaps in N-02 and N-03 are about what it *doesn't*
test, not about wrong values.

---

## 7. Third-pass review of the updated plan

The plan grew from 1305 to 1721 lines. `config/drs.example.yaml` grew from 198 to 279 lines.
The expected fixture grew from 97 to 188 lines and the input fixture from 69 to 80 lines. A
new file `tests/fixtures/generate_fc_tier1.py` (208 lines) was added. Two further commits
beyond the N-01..N-07 fixes introduced substantial new material: all-bus disk enumeration
(§3.5/§3.6), snapshot exclusion policy (§3.7), load-model rescale back to in-flight-I/O units
(§4), computed big-M penalty (§5.3), CP-SAT coefficient folding (§5.5), saferemove wipe
accounting (§7.1, §9.3), saturation-load redesign with `N_s` (§7.3), draining state (§8.2),
VM lock handling (§9.3), and fixture improvements including ordering and post-plan reserve
status. This section records the resolution status of every N-finding and presents new
findings.

### 7.1 Resolution of second-pass findings

All 7 second-pass findings (N-01..N-07) have been addressed. Summary:

| ID | Status | How resolved |
|----|--------|--------------|
| N-01 | Resolved | §5.5 rewritten: instead of factoring γ out as a standalone per-MiB integer, each disk's coefficient is folded at full precision: `round(γ·W·K·z_d^TiB)`. The γ-trap is explicitly documented with the worked example showing `round(0.05·10⁶/2²⁰)=0` and why raising K doesn't fix it. An assertion at model-build time checks every non-zero weight produces a non-zero integer coefficient. Verified: `round(0.05·10⁴·10⁶·0.5) = 2.5×10⁸`, exact. |
| N-02 | Resolved | `beta_values: [0.25, 0.5]` added to the input fixture's `objective` block with a comment: "Swept by the harness; one cases[] entry in the expected file per value." The fixture contract is now explicit. |
| N-03 | Resolved | `expected_order` field added to each case (ordered list with per-move transient checks: `transient_target_used_tib`, `transient_reserve_basis_tib`, `transient_required_tib`, `capacity_tib`, `ok`). `expected_final_reserve` section added mirroring the `initial` block (per-storage `used_tib`, `largest_tib`, `required_tib`, `violates_reserve`). Both verified against §14.4. |
| N-04 | Resolved | Config example `fc-tier1` now has `san-c: capability_weight: 1.0`, matching the fixture. The 0.5 feature is illustrated on `san-e` in `fc-tier2`. A comment notes the alignment with the fixture. |
| N-05 | Resolved | §7.3 rewritten: `û_s` is now explicitly `L̂_s` (load, not normalized utilization). The check is `L_during(s) ≤ saturation_ceiling · N_s` where `N_s` is the storage's physical saturation load, not `c_s`. The old `saturation_ceiling · c_s` form is called out as the original defect. |
| N-06 | Resolved | `metrics.pvestatd_push_interval: 60s` added to config. `verify-metrics` (§3.3 step 6) now measures observed sample spacing and errors if it disagrees with config by >20%. §11.1 validation rule references the config field. |
| N-07 | Resolved | §5.5 now folds both `K` and `c_s` into a single per-(disk,storage) coefficient `a_{d,s} = round(K·ℓ_d/c_s)`, with error bound `≤ 0.5` (i.e. `≤ 5×10⁻⁷` in load units), independent of `c_s`. The old `round(K/c_s)` approach is explicitly called out as making CP-SAT and CBC disagree. |

### 7.2 New findings summary

| ID | Severity | Section | Topic |
|----|----------|---------|-------|
| M-01 | Low | §5.5, generator | Generator uses single-stage big-M (P=1000), not the preferred lexicographic solve; fixture doesn't test lexicographic |
| M-02 | Low | §7.1, §14.5 | §14.5 payback example silently assumes saferemove off, but the config default is `account_saferemove_wipe: true`; a naïve implementer will get different numbers |
| M-03 | Low | §8.2 | `draining` state holds source charged for the whole wipe, but the transient invariant (§8.1) doesn't model the wipe's own I/O load on the source |
| M-04 | Low | §3.6, §13 | `tpmstate0` online move was "verified on PVE 9.2" but the plan also says PVE may not use drive-mirror for it; the transient invariant assumption (both storages occupied) is unverified for swtpm |
| M-05 | Info | §4, §14 | Load-model rescale is correct but the §14 fixture's `ℓ_d` values are now reinterpreted as raw in-flight I/O (not normalized); old Appendix A verification still holds but the units description changed |
| M-06 | Info | §5.3 | Big-M `P_min` is computed from `T_g` (group absolute load), which changes per run; the plan correctly says to compute at model-build time, but the config `reserve_violation_penalty: 1000` as a floor may need to be much larger for small-`T_g` groups |

### 7.3 New findings — detail

#### M-01 — Generator tests big-M, not the preferred lexicographic solve (Low)
**Where:** `tests/fixtures/generate_fc_tier1.py`, §5.3.
**Issue:** The generator's `objective()` function includes `P_RESERVE * slack` as a
single-stage big-M term with `P=1000`. The plan states the lexicographic two-stage solve
(option 1) is the preferred default and option 2 (big-M) needs a computed `P`. The fixture
therefore validates the big-M path with a fixed `P=1000`, not the lexicographic path. For
this fixture both approaches give the same answer because `P=1000` is dominant here (the
initial violation is 0.5 TiB, so `P·0.5 = 500 >> 21.6` max non-reserve objective). But an
implementer who implements only the lexicographic solve has no fixture to test it against, and
an implementer who uses big-M with `P=1000` on a different group where the violation is
sub-GiB may get a different answer than lexicographic (the plan's own §5.3 computation shows
`P_min ≈ 2.27×10⁷` for mebibyte granularity, so `P=1000` is 4 orders of magnitude too small
there).
**Recommendation:** Either (a) add a second fixture or a second mode in the generator that
validates the lexicographic solve (minimize `Σr_s` first, then fix it and minimize the rest),
or (b) document that the fixture only tests big-M and that a lexicographic test must be added
when that path is implemented. This is low-severity because both paths agree on the fixture,
but it's a test-coverage gap.

#### M-02 — §14.5 payback silently assumes saferemove off (Low)
**Where:** §14.5, config `migration.account_saferemove_wipe: true`.
**Issue:** §14.5 now states "and **`saferemove` off on all three storages** so
`duration_wipe_d = 0`". This is necessary because the new §7.1 wipe accounting would otherwise
make the payback numbers much larger (a 1.5 TiB disk at 10 MiB/s wipe takes ~44h, dwarfing the
2.2h mirror). But the config default is `account_saferemove_wipe: true`. An implementer who
runs the fixture with the default config values will get payback numbers that don't match
unless they notice the saferemove-off assumption. The fixture's `migration` block doesn't
include `account_saferemove_wipe: false` or any saferemove-throughput field.
**Recommendation:** Add `account_saferemove_wipe: false` (or `saferemove_throughput: 0` per
storage) to the fixture's `migration` block so the fixture is self-contained and an
implementer doesn't have to infer the assumption from the prose. Alternatively, add
`saferemove_throughput_tib_per_sec: 0` per storage in the fixture's `group.storages` to make
the wipe-off assumption explicit in the data.

#### M-03 — Transient invariant doesn't model the wipe's I/O load (Low)
**Where:** §8.1, §8.2, §7.1.
**Issue:** The `draining` state (§8.2) keeps the source charged for `z_d` bytes until the
volume is observed gone, which is correct for the *capacity* invariant. But the wipe itself
is a sequential write at `saferemove_throughput` (§7.1) that generates I/O on the source
storage. §7.1 charges this as `duration_wipe_d · ω_src` in the cost model, but §8.1's
transient invariant — which checks *capacity* (`used + reserve ≤ C`) — does not check
*load* during the drain. A storage that is already near its `N_s` saturation load could be
pushed over by a wipe running in the background while the next move is being scheduled. The
`concurrency_ok` predicate (§8.1 condition 4) checks the §7.3 saturation guard for in-flight
*mirrors*, but a draining wipe is no longer in the in-flight set `M` (the task has reported
OK), so its load is not counted.
**Recommendation:** Either (a) include draining moves in the saturation check: a move stays
in a "load-in-flight" set (distinct from the capacity in-flight set `M`) until `done`, and
`concurrency_ok` sums `ω_src` for all draining moves at that storage; or (b) document that
the wipe load is best-effort and is not modeled in the transient invariant, and that
`cooldown_per_storage` (which §9.3 sizes against the wipe time) is the mitigation. Option (b)
is simpler and may be sufficient given that the wipe is a low-throughput sequential operation
(10 MiB/s default), but the plan should state this explicitly.

#### M-04 — tpmstate0 transient invariant assumption unverified for swtpm (Low)
**Where:** §3.6, §13.
**Issue:** §3.6 states `tpmstate0` is movable online on PVE 9.2 (verified empirically) but
also says "PVE may not use the `drive-mirror` path for it, since `swtpm` rather than QEMU
owns the state." The transient invariant (§8.1) assumes "the volume exists on **both**
storages — the mirror target is fully allocated before the switchover." If `swtpm` moves
state by a different mechanism (e.g., copy-then-delete, or atomic rename), the both-storages
assumption may not hold, and the conservative invariant may over-reserve during the move.
This is safe (over-reserving never causes a reserve breach), but it could make a
`tpmstate0` move unnecessarily infeasible on a tight storage.
**Recommendation:** The plan already says "no part of the model needs to know which mechanism
PVE picked" and the conservative assumption is the safe direction. Consider adding one
sentence: "If swtpm does not use drive-mirror, the both-storages invariant is conservative
(over-reserves) but never unsafe; a `tpmstate0` move that fails the transient check on a
tight storage should be treated as any other infeasible move — deferred, not forced."

#### M-05 — Load-model rescale reinterprets §14 fixture units (Info)
**Where:** §4, §14, Appendix A.
**Issue:** §4 was rewritten to rescale `ℓ_d` back onto the in-flight-I/O scale (`Σℓ_d = T_g`,
not 1.0). The §14 fixture's loads (3.0, 1.0, 2.5, etc.) are now explicitly described as "in
average in-flight I/O requests, *not* normalized to sum to one." This is a change in
*description*, not in values — the numbers are the same, but what they *mean* is now
different. The Appendix A verification in this review was performed under the old
description (normalized to sum to 1) but still holds because the values and ratios are
unchanged; only the unit label shifted.
**Recommendation:** No action needed. The change is correct and the payback comparison in §7
is now on a sounder footing (`ω = 1.0` is commensurable with `ℓ` because both are in
in-flight I/O requests). Recorded so the implementer knows the Appendix A verification
remains valid despite the units reinterpretation.

#### M-06 — Big-M `P_min` depends on `T_g`, which varies per run (Info)
**Where:** §5.3.
**Issue:** The computed big-M penalty `P_min = U_obj / ε_r` depends on `T_g` (the group's
total absolute load), which changes every run as workloads shift. On a quiet group with
`T_g = 0.1`, `U_obj` is tiny and `P_min` is small; on a busy group with `T_g = 20`, `P_min`
is large. The config `reserve_violation_penalty: 1000` is a *floor*, and the engine uses
`max(configured, P_min)`. This is correct, but it means the same config file produces
different effective `P` values on different groups and different runs. An operator who
sets `reserve_violation_penalty: 5000` thinking it's the actual penalty may not realize the
engine is silently raising it to `P_min` on busy groups.
**Recommendation:** The plan already says "logs a warning when it had to raise it," which is
the right mitigation. Consider also logging the computed `P_min` and the `T_g` it was
derived from, so an operator seeing the warning can verify the computation. No structural
change needed.

### 7.4 Fixture and generator verification

The fixture and generator were independently verified:

- **Generator freshness:** `python3 generate_fc_tier1.py --check` exits 0 — the committed
  `fc-tier1.expected.json` is current.
- **Objective values:** both β cases match the generator's exhaustive enumeration (verified
  in §6.4 and re-confirmed).
- **Ordering:** `expected_order` correctly places `102:scsi0` first (repairs the reserve
  violation) in both cases. Transient checks match §14.4: 5.0≤8.0, 4.5≤8.0, 5.0≤8.0.
- **Post-plan reserve:** `expected_final_reserve` for both cases shows no violations, matching
  §14.3's final-state table.
- **CP-SAT coefficient folding:** verified `round(0.05·10⁴·10⁶·0.5) = 2.5×10⁸` — the γ term is
  now exact, not zero. The N-01 defect is fixed.
- **Big-M bound:** `P_min = 21.625 / 2⁻²⁰ ≈ 2.27×10⁷`, matching the plan's §5.3 computation.
- **Generator covers the fixture's objective formula exactly** (`alpha·E + beta·moves +
  gamma·bytes + kappa·frag + P·slack`), including the `P·slack` term. The generator does not
  model the lexicographic two-stage solve (M-01).
- **Generator does not model `affinity_counts_pinned_disks`** or the `D^mov` distinction,
  but the fixture has no pinned disks so `D^mov = D` and the computation is correct.

---

## 8. Fourth-pass review of the updated plan

The plan grew from 1721 to 1842 lines. `config/drs.example.yaml` grew from 279 to 285 lines
(one new field: `migration.wipe_load_weight`). The generator was renamed from
`generate_fc_tier1.py` to `generate_expected.py` and rewritten (208→502 lines) to handle
multiple fixtures, the lexicographic solve path, and the `ω_wipe` cost model. A new fixture
pair `reserve-tradeoff.yaml`/`.expected.json` was added. `AGENTS.md`, `.agents/`, `LICENSE`
(AGPL-3.0), `pyproject.toml`, `Makefile`, and `.pre-commit-config.yaml` were added as project
tooling. This section records the resolution of every M-finding and presents new findings.

### 8.1 Resolution of third-pass findings

All 6 third-pass findings (M-01..M-06) have been addressed. Summary:

| ID | Status | How resolved |
|----|--------|--------------|
| M-01 | Resolved | New `reserve-tradeoff` fixture (§14.6) with a group where lexicographic and big-M provably disagree. Generator rewritten with `best_lexicographic()`, `big_m_agreement_threshold()`, and `computed_p_min()` functions. The expected file records both solve paths, the threshold P, and whether they agree at the configured P. The `big_m_undersized_p_demo` (P=5) shows big-M making the wrong choice and the resulting plan being unschedulable. |
| M-02 | Resolved | `fc-tier1.yaml` now has `saferemove: false` per storage and `account_saferemove_wipe: false` in the `migration` block. The expected file has an `assumptions` object echoing this. Per-move records carry `duration_mirror_seconds` and `duration_wipe_seconds` separately. §14.5 prose explicitly explains the assumption is in the data, not just the prose. |
| M-03 | Resolved | §7.3 now defines a state-dependent `ω_role(m,s)` table: `mirroring` charges `ω_src`/`ω_dst`, `draining` charges `ω_wipe`/0, `done` charges 0/0. §8.1 condition 4 sums `ω_role` over all moves in `M` including draining. New config field `migration.wipe_load_weight` (default 1.0) controls `ω_wipe`. The generator's `cost()` function implements the same split. |
| M-04 | Resolved | §3.6 now states: "if swtpm does not use drive-mirror, the both-storages assumption over-reserves during the move. Over-reserving can never cause a reserve breach, so it is safe; the only cost is that a tpmstate0 move onto a nearly-full storage may fail the transient check... Treat that exactly like any other infeasible move — defer it, never force it." |
| M-05 | Resolved (no action) | The units reinterpretation is now fully documented in §4 and §14.1. Appendix A verification in this review remains valid as noted. |
| M-06 | Resolved | §5.3 now requires logging `P_configured`, `P_min`, `P_used`, and the four inputs (`T_g`, `|D|`, `Σz_d`, `|V|·(|S|−1)`) plus `ε_r`, and repeating them in `drs explain`. The text explicitly addresses the "operator sets 5000 and sees 2.3×10⁷" scenario. |

### 8.2 New findings summary

| ID | Severity | Section | Topic |
|----|----------|---------|-------|
| K-01 | Low | generator, §14.5 | Payback `benefit_load_seconds` mixes exact `E_before` with rounded `E_after`; fixture says 3951360.2, prose says 3951360.0 |
| K-02 | Low | §7.1, §7.3, config | `ω_wipe` renamed to `wipe_load_weight` in config but the plan text uses `ω_wipe` and `migration.wipe_load_weight` inconsistently |

### 8.3 New findings — detail

#### K-01 — Payback benefit mixes exact and rounded E (Low)
**Where:** `tests/fixtures/generate_expected.py` `payback()` function, §14.5.
**Issue:** The generator's `payback()` function computes `delta_e = E_of(f, f.current) -
case["expected_E_after"]`, where `case["expected_E_after"]` is already rounded to 6 decimal
places. This mixes an exact `E_before` (8.0666666...) with a rounded `E_after` (1.533333),
producing `delta_e = 6.5333336...` instead of the exact `6.5333333...`. The benefit becomes
`3951360.2` instead of the exact `3951360.0` that the §14.5 prose states. The ratio is
unaffected (150.73 in both cases), so the payback acceptance test passes either way, but an
implementer asserting exact equality against the fixture will see a 0.2 load-seconds
discrepancy with the prose.
**Recommendation:** In the generator's `payback()` function, compute `delta_e` from the exact
assignment rather than from the rounded case value:
```python
# Instead of:
delta_e = E_of(f, f.current) - case["expected_E_after"]
# Use:
two_assign = best_big_m(f, case["beta_move_count"], f.big_m_p)[0]
delta_e = E_of(f, f.current) - E_of(f, two_assign)
```
Or simply pass the exact `E_after` into `payback()` alongside the rounded one. This is a
cosmetic fix — the 5×10⁻⁸ relative error has no physical consequence — but it eliminates a
prose-vs-fixture discrepancy that an implementer would have to explain.

#### K-02 — `ω_wipe` / `wipe_load_weight` naming inconsistency (Low)
**Where:** §7.1, §7.3, §15.1, `config/drs.example.yaml`.
**Issue:** The plan text in §7.1 and §7.3 refers to the wipe load weight as `ω_wipe`, and
§15.1 maps it to `migration.wipe_load_weight`. The config file has `wipe_load_weight: 1.0`
under `migration:`. This is consistent. However, the fixture's `migration` block uses
`omega_wipe: 1.0` (not `wipe_load_weight`), and the generator reads it as
`f.migration.get("omega_wipe", 1.0)`. So the fixture uses a different field name than the
config for the same quantity. An implementer who reads the config field name from
`drs.example.yaml` and then looks at the fixture will see two different names for the same
knob.
**Recommendation:** Rename `omega_wipe` to `wipe_load_weight` in the fixture YAML files
(`fc-tier1.yaml` and `reserve-tradeoff.yaml`) and in the generator's `migration.get()` call, to
match the config field name. This is purely a naming consistency issue; the values and
semantics are identical.

### 8.4 Fixture and generator verification

The updated fixtures and generator were independently verified:

- **Generator freshness:** `python3 tests/fixtures/generate_expected.py --check` exits 0 —
  both `fc-tier1.expected.json` and `reserve-tradeoff.expected.json` are current.
- **fc-tier1 numbers:** all objective values, ordering, transient checks, and post-plan
  reserve status match the §14 prose and the previous verification (§6.4, §7.4). The new
  `lexicographic` block correctly records that both paths agree (`agrees_with_big_m_at_configured_p:
  true`) and that the threshold is negative (`-3.273333`), meaning no P≥0 can make them
  disagree on this fixture.
- **reserve-tradeoff numbers:** all values verified by hand:
  - Both on roomy: E=10.0, slack=0, obj_nr=10.0 ✓
  - One to cramped: E=0.0, slack=1.0, obj_nr=0.30 ✓
  - Big-M P=1000: stays (1000.30 > 10.0) → 0 moves ✓
  - Big-M P=5: moves (5.30 < 10.0) → 1 move ✓
  - Flip threshold: P = 10.0 − 0.30 = 9.7 ✓
  - Transient check: 3.0 + 1.0 + 2×1.0 = 6.0 > 5.0 → deadlock ✓
  - P_min = 21.6 × 2²⁰ = 22649241.6 ✓
  - Lexicographic: min_slack=0, then min obj_nr=10.0 → 0 moves ✓
- **Cost model:** `ω_wipe` now separates the wipe load from the mirror load in both the cost
  function (§7.1) and the saturation guard (§7.3 `ω_role` table). Verified that with
  `saferemove: false` the payback numbers are unchanged.
- **Generator architecture:** the rewritten `generate_expected.py` is a significant
  improvement — it handles both fixtures, both solve paths, the threshold computation, and
  the deadlock detection in a single 502-line file with clean separation between state
  evaluation, objective computation, and ordering. The `Fixture` dataclass and the
  `all_assignments()` iterator make the exhaustive enumeration readable and trustworthy.

---

## 9. Fifth-pass review of the updated plan

Commit `78d9573` ("Address fourth-pass review findings K-01, K-02") made targeted fixes only;
the plan, config, and fixtures changed in three small ways. No new findings.

### 9.1 Resolution of fourth-pass findings

| ID | Status | How resolved |
|----|--------|--------------|
| K-01 | Resolved | `generate_expected.py` `payback()` now takes an `e_after` parameter (the exact, unrounded `E_of(f, a)`), passed via a `_exact_E_after` field on the case dict (stripped before writing with a `_`-prefix filter). `benefit_load_seconds` is now `3951360.0`, matching the §14.5 prose exactly. The `ratio` is unchanged at `150.73`. Verified: `generate_expected.py --check` exits 0. |
| K-02 | Resolved | Both fixture YAMLs renamed `omega_src`→`source_load_weight`, `omega_dst`→`target_load_weight`, `omega_wipe`→`wipe_load_weight` to match `config/drs.example.yaml`. The generator's `cost()` and `build()` functions updated to read the new names. The expected files' `assumptions` block renamed `omega_wipe`→`wipe_load_weight`. A field-naming convention comment was added to both fixture YAMLs documenting that fixture knobs mirror config names, with two deliberate exceptions (`payback_horizon_seconds` as integer vs config's `7d`, and `beta_values` as a list vs config's single `beta_move_count`). |

The plan also fixed two stale references in §11 and §15.1's traceability tables:
`gamma_move_bytes` → `gamma_move_bytes_per_tib` to match the actual config field name, and the
config itself was corrected from `gamma_move_bytes` to `gamma_move_bytes_per_tib`.

### 9.2 Verification

- `python3 tests/fixtures/generate_expected.py --check` exits 0 — both expected files current.
- `fc-tier1.expected.json` `benefit_load_seconds` = `3951360.0` (was `3951360.2`), matching §14.5.
- Fixture migration keys: `source_load_weight`, `target_load_weight`, `wipe_load_weight` —
  all match config field names.
- Fixture objective keys: `gamma_move_bytes_per_tib` — matches config.
- No changes to the plan's §5.5 CP-SAT scaling, §5.3 lexicographic/big-M, §7.1 cost model,
  §7.3 saturation guard, §8.1 transient invariant, or §14.6 reserve-tradeoff fixture.

### 9.3 Assessment

The plan and its fixtures are clean. Across five review passes, 40 findings (F-01..F-25,
N-01..N-07, M-01..M-06, K-01..K-02) have been raised and all are resolved. The remaining
open items are zero. The plan is ready for implementation.

---

## 10. Sixth-pass review of the updated plan

Commits `06fe472..3db38d3` added substantial new infrastructure: the `pve-storage-drs` naming
convention, full Debian packaging (`debian/` with control, rules, changelog, copyright, Salsa
CI), two GitHub Actions workflows (`tests.yml`, `debian-package.yml`), the PDF paper pipeline
(`docs/paper/header.tex`, `filters.lua`, `metadata.yaml`, `tools/check_paper_log.py`), the
documentation policy (AGENTS.md §8, `.agents/documentation.md`), the manpage
(`man/pve-storage-drs.1.md`), config-on-pmxcfs with resolution order and env-var support
(§11), the state path move to `/var/lib/pve-storage-drs/state.json`, global CLI options
(§11.3), Makefile `SYSTEM_TOOLS=1` support, `.codecov.yml`, and `.pre-commit-config.yaml`
updates.

The new material is well-structured and the packaging is thorough: the autopkgtest design
correctly catches optional-dependency import-at-module-level bugs, the Salsa no-network sbuild
proves the package builds from trixie alone, the PDF freshness stamp mechanism is sound, and
the `check_paper_log.py` script catches the two classes of silent LaTeX damage (missing
characters, overfull boxes). The manpage follows the AGENTS.md §8.4 section order exactly.
Five new findings, three of them Medium.

### 10.1 Summary of sixth-pass findings

| ID | Severity | Section / File | Topic |
|----|----------|----------------|-------|
| L-01 | Medium | §2.1, pyproject.toml, debian/control | `pulp` classified inconsistently: not marked optional in the plan, but optional in pyproject.toml and Recommends in debian/control |
| L-02 | Medium | §11.3, man/pve-storage-drs.1.md | Direct contradiction: plan says `-v, --quiet`; manpage says `-v, --verbose` |
| L-03 | Medium | .github/workflows/, debian/control | CBC/PuLP primary solver path is not exercised in any CI pipeline |
| L-04 | Low | §11.3 | `--mode auto` overriding a `confirm` config is not called out as a warning |
| L-05 | Info | debian/changelog | Uses `bernd@debian.org` while the rest of the repo uses `bernd@bzed.de` |

### 10.2 L-01 — `pulp` is not marked optional in the plan, but is optional in the packaging

**Severity:** Medium
**Files:** `IMPLEMENTATION_PLAN.md` §2.1, `pyproject.toml`, `debian/control`

The plan §2.1 dependency table lists `pulp` alongside hard dependencies (`requests`,
`ruamel.yaml`, `jsonschema`) without an "optional" qualifier:

```
| `pulp` | MILP via CBC — **the packaged solver path** | `python3-pulp` 2.7 + `coinor-cbc` 2.10 |
```

`ortools` is marked "optional and unpackaged" in the same table, but `pulp` gets no such
marking. The "optional extras" sentence below the table names only ortools and statsmodels:

> Make `ortools` and `statsmodels` **optional extras**. The tool must run, plan and execute
> with only `requests` + `ruamel.yaml` + `jsonschema` installed, falling back to the heuristic
> solver and the quantile forecaster.

But the "must run with only requests + ruamel.yaml + jsonschema" requirement makes `pulp`
functionally optional too: the heuristic path works without it. The packaging artifacts
confirm this — `pyproject.toml` puts `pulp` under `[project.optional-dependencies] solver`
(the comment there correctly says "ortools and pulp are therefore optional extras, not hard
requirements"), and `debian/control` puts `python3-pulp` under `Recommends:`, not `Depends:`.

The plan text creates an ambiguity: an implementer reading §2.1 in isolation could conclude
`pulp` is a hard dependency (it is listed without "optional", called "the packaged solver
path", and not mentioned in the "optional extras" sentence), while the packaging treats it as
optional. The AGENTS.md §9.1 rule 3 ("not in trixie, and not vendorable — it must be optional")
applies to ortools; pulp *is* in trixie, so the rule does not force it to be optional — yet
the architecture requires it because the heuristic path must work standalone.

**Recommendation:** Mark `pulp` as optional in the plan. Either add it to the "optional
extras" sentence ("Make `ortools`, `pulp`, and `statsmodels` optional extras") or add a note to
the table row (e.g., "optional, but `Recommends` on Debian — the MILP path needs it, the
heuristic does not"). The key point is that the plan, `pyproject.toml`, and `debian/control`
should agree on the classification, and right now the plan is the one that is ambiguous.

### 10.3 L-02 — `-v` means `--quiet` in the plan but `--verbose` in the manpage

**Severity:** Medium
**Files:** `IMPLEMENTATION_PLAN.md` §11.3, `man/pve-storage-drs.1.md`

The plan §11.3 global options table:

```
| `-v`, `--quiet` | normal | Log level; `--quiet` leaves only warnings and errors, for the timer |
```

This binds `-v` as the short form of `--quiet` (reduces verbosity). The plan does not mention
`--verbose` anywhere.

The manpage:

```
**-v**, **--verbose**
: More detail on stderr. Repeatable.

**--quiet**
: Warnings and errors only. Intended for the systemd timer.
```

This binds `-v` as the short form of `--verbose` (increases verbosity) and treats `--quiet`
as a separate, independent option.

These are directly contradictory: `-v` makes the tool quieter in the plan and more verbose in
the manpage. An operator who reads the manpage and then uses `-v` expecting more detail would
get the opposite. The manpage is generated from `man/pve-storage-drs.1.md`, which is a
hand-authored file (not generated from the plan), so there is no mechanical check that keeps
the two in sync yet.

**Recommendation:** Pick one design and align both. The manpage's design (`-v` = verbose,
`--quiet` = quiet, as independent flags) is more conventional and less surprising than the
plan's (`-v` = quiet). If the manpage design is chosen, update §11.3 to list `--verbose`
and `--quiet` as separate options with `-v` as the short form of `--verbose`. If the plan's
design is chosen, fix the manpage. Either way, the `--help` output (generated from argparse)
will be the mechanical source of truth once the CLI exists; until then the two documents must
agree by hand.

### 10.4 L-03 — The CBC/PuLP solver path is not exercised in any CI pipeline

**Severity:** Medium
**Files:** `.github/workflows/tests.yml`, `.github/workflows/debian-package.yml`,
`debian/control`

The plan §2.1 states: "on a Debian install the MILP is solved by **CBC through
`python3-pulp`**." This is the primary solver path on the target platform. However:

- `tests.yml` installs `python3-jsonschema python3-pytest python3-pytest-cov
  python3-pytest-xdist python3-requests python3-ruamel.yaml python3-yaml` — no `python3-pulp`
  or `coinor-cbc`.
- `debian-package.yml` installs build dependencies from `debian/control`, which has
  `python3-pulp` under `Recommends:`, not `Build-Depends`.
- The autopkgtest (`debian/tests/control`) runs with only `Depends: @` — `Recommends` are not
  installed — so the installed-package test also runs without pulp.

This means the CBC/MILP integration will not be tested in any CI pipeline once `optimize.py`
exists. The fixture generator (`generate_expected.py`) is solver-independent (exhaustive
enumeration), so it does not exercise the actual solver. The solver-integration tests that
verify CBC produces the same assignments as the enumeration will need pulp available.

The `tests.yml` "Is there code yet?" probe currently gates on `src/*/*.py`, and the MILP
tests would be among the first things added. Without pulp in the CI install list, those
tests will either fail (if they import pulp unconditionally) or skip (if they guard on
`pytest.importorskip("pulp")`) — and if they skip, the primary solver path on the target
platform is never tested in CI.

**Recommendation:** When the solver module lands, add `python3-pulp` and `coinor-cbc` to
`debian/control` `Build-Depends` with `<!nocheck>` (so `dh_auto_test` has them), and to the
`tests.yml` apt install list. The autopkgtest should continue to run without pulp (it tests
that the tool works with only `Depends`), but the build-time test suite should exercise the
MILP path. This is a forward-looking finding — the infrastructure is already in place to miss
it, so it is worth recording now rather than discovering when the first solver test
mysteriously skips.

### 10.5 L-04 — `--mode auto` on a `confirm` config is not warned

**Severity:** Low
**File:** `IMPLEMENTATION_PLAN.md` §11.3

The plan §11.3 says:

> `--mode` may make a run *safer* without ceremony, but `--mode auto` on a config that says
> `dry-run` is an operator deliberately overriding their own safety setting: log it at
> warning level, naming both values.

This covers `dry-run → auto` (removing both the dry-run barrier and the confirmation
barrier). But it does not mention `confirm → auto`, which also removes a safety barrier
(the per-step confirmation prompt). An operator who set `execution.mode: confirm` in the
config and then runs `--mode auto` is bypassing their own confirmation requirement, which is
the same class of override. The plan only calls out the `dry-run` case.

**Recommendation:** Extend the rule to cover any override that moves to a less safe mode:
log at warning when `--mode` is less safe than the configured mode, not only when the
configured mode is `dry-run`. "Less safe" is defined by the ordering `dry-run < confirm <
auto`, so `confirm → auto` and `dry-run → confirm` are both overrides toward less safe. Or
simply: warn whenever `--mode` is given and it differs from the configured mode, regardless
of direction, since any override is a deliberate act the operator should see in the log.

### 10.6 L-05 — `debian/changelog` uses a different email address

**Severity:** Info
**File:** `debian/changelog`

The changelog entry uses `bernd@debian.org`:

```
-- Bernd Zeimetz <bernd@debian.org>  Fri, 04 Sep 2026 23:30:47 +0200
```

Every other file in the repository — `pyproject.toml` (`authors`), `debian/copyright`
(`Upstream-Contact`), `man/pve-storage-drs.1.md` (`AUTHOR`), all SPDX headers, `AGENTS.md`
section 0 — uses `bernd@bzed.de`. This may be intentional (the `debian.org` address is the
Debian developer address, and some maintainers use it in changelogs by convention), but it is
the only place in the tree that does. Worth noting for consistency; not actionable unless the
maintainer wants uniformity.

### 10.7 Verification

- `python3 tests/fixtures/generate_expected.py --check` exits 0 — both expected files current.
- `sha256sum --check docs/IMPLEMENTATION_PLAN.pdf.sha256` passes — the committed PDF matches
  the committed Markdown.
- The manpage section order (`NAME`, `SYNOPSIS`, `DESCRIPTION`, `COMMANDS`, `OPTIONS`,
  `CONFIGURATION`, `ENVIRONMENT`, `FILES`, `EXIT STATUS`, `SEE ALSO`, `AUTHOR`,
  `COPYRIGHT`) matches AGENTS.md §8.4, with `COMMANDS` and `ENVIRONMENT` added (the §8.4 list
  is a minimum, not a maximum — `COMMANDS` is the manpage convention for subcommand listing
  and `ENVIRONMENT` documents `PVE_STORAGE_DRS_CONFIG` / `PVE_PASSWORD` / `PVE_TOKEN_SECRET`).
  This is correct.
- The `debian/control` `Depends` list (`python3-jsonschema`, `python3-requests`,
  `python3-ruamel.yaml`) matches the `pyproject.toml` `dependencies` list. `Recommends`
  (`python3-pulp`, `coinor-cbc`) and `Suggests` (`python3-statsmodels`) match the optional
  extras. The dependency declarations are consistent with the "must run with only
  requests + ruamel.yaml + jsonschema" requirement — except for the plan's ambiguity about
  pulp (L-01).
- `debian/changelog` version `0.0.1` matches `pyproject.toml` version `0.0.1`.
- The `import-all` autopkgtest correctly walks the package with `pkgutil.walk_packages` and
  catches `BaseException` (not just `Exception`), so a `SystemExit` from a bad import is also
  a failure.
- The Salsa CI config (`debian/.gitlab-ci.yml`) correctly sets `RELEASE: 'trixie'`, disables
  `BLHC` (nothing compiled), `APTLY`, and `BUILD_PACKAGE_ANY` (arch:all only), and leaves
  `SALSA_CI_SBUILD_ARGS` empty with the `--enable-network` fallback commented out.
- The Makefile `SYSTEM_TOOLS=1` path correctly avoids `.venv` for CI, and the `man` target
  does not depend on `$(VENVDEP)`, so `debian/rules`' `$(MAKE) man` works in the build chroot
  without a venv.
- `tools/check_paper_log.py` correctly undoes the 79-column log hard-wrap before pattern
  matching, and treats `SystemExit`-class exceptions as failures in the autopkgtest import
  walker.

### 10.8 Assessment

The packaging, CI, and documentation infrastructure is well-designed and internally
consistent in almost all respects. The autopkgtest-as-dependency-test pattern, the no-network
Salsa build, the PDF freshness stamp, and the `check_paper_log.py` log checker are all the
right mechanisms. The three Medium findings (L-01..L-03) are all in the same area: the
boundary between the plan's dependency classification and the packaging/CI that implements
it. Resolving them is a matter of documentation alignment (L-01, L-02) and a CI install-list
addition when the solver code lands (L-03). None are architectural.

---

## 11. Seventh-pass review of the first implementation

Commits `37c6392..cf532f2` are the transition from design to code: the L-finding fixes
(`aceb5e6`), then phase 1 (config loading, forecasting, CLI skeleton, metrics), phase 2 (PVE
API client, topology, reserve), and the full documentation suite (`docs/internals/*.md`,
`docs/manual/*.md`, `tools/build_paper.sh`). This is the largest single addition to the
repository since the plan itself: ~8300 lines across 60 files, including 2700 lines of tests.

The implementation is high quality. The code follows the plan closely, the frozen-dataclass
style from AGENTS.md is used throughout, optional dependencies (`statsmodels`) are imported
inside the function that needs them (not at module level), every public function has a
docstring referencing the plan section, and the test suite (223 tests, 1 skipped for
`statsmodels`) achieves 98.61% coverage — well above the 85% floor. The `FakeProxmoxResource`
test double correctly replicates `proxmoxer`'s dynamic attribute-chaining protocol. The
documentation cross-reference tests (`test_documentation.py`) enforce that every config
schema key appears in the manual and vice versa, and that every CLI option appears in the
manpage.

### 11.1 Resolution of sixth-pass findings

| ID | Status | How resolved |
|----|--------|--------------|
| L-01 | Resolved | The plan §2.1 table now marks `pulp` as "optional", and the "optional extras" sentence names `pulp` alongside `ortools` and `statsmodels`, with the distinction spelled out: "the packaged solver path" describes which MILP backend a Debian install gets, not that the MILP is mandatory. |
| L-02 | Resolved | Resolved in the manpage's favour: `-v`/`--verbose` and `--quiet` are now separate options in both the plan §11.3 and the manpage, with `-v` meaning more output. The CLI (`cli.py`) implements them correctly as `action="count"` and `action="store_true"` respectively. |
| L-03 | Resolved | `coinor-cbc` and `python3-pulp` are now `Build-Depends` under `<!nocheck>` and in the GitHub Actions install list. The autopkgtest deliberately keeps running without them. Both halves documented in `.agents/packaging.md`. |
| L-04 | Resolved | The warning rule now orders the modes `dry-run < confirm < auto` and warns on any move *up* that order, not only `dry-run -> auto`. `cli.py`'s `apply_mode_override()` implements this correctly using `_MODE_RANK`. |
| L-05 | Refuted | The finding's premise was wrong: the changelog uses `bzed@debian.org` (the Debian developer address), not `bernd@debian.org` as I wrote. The split is now documented in AGENTS.md §0 and `.agents/packaging.md`. |

### 11.2 Summary of seventh-pass findings

| ID | Severity | Section / File | Topic |
|----|----------|----------------|-------|
| P-01 | Medium | §3.5, config.py, pve.py, manual | `proxmox.ticket_refresh_seconds` is a dead config knob — parsed and documented but never passed to proxmoxer |
| P-02 | Medium | §3.5, config.py, topology.py, manual | `proxmox.read_workers` is a dead config knob — documented as the thread pool size but topology.py fetches sequentially |
| P-03 | Low | §3.5, manual/00-installation.md | Manual does not document `VM.Config.Disk` and `VM.Migrate` privileges needed for `move_disk` |

### 11.3 P-01 — `proxmox.ticket_refresh_seconds` is a dead config knob

**Severity:** Medium
**Files:** `config.py:68`, `pve.py`, `docs/manual/10-configuration.md:90`, `config/drs.example.yaml:38`

The plan §3.5 says: "Tickets are valid ~2h; `proxmoxer` refreshes them itself on its own
internal interval when using password auth." The `pve.py` `build_client()` function does not
pass `ticket_refresh_seconds` to `proxmoxer.ProxmoxAPI` — proxmoxer manages its own refresh.

Meanwhile, `ProxmoxConfig.ticket_refresh_seconds` exists as a field, is parsed from the config
file (`config.py:403-404`), is in the JSON schema (`config_schema.json:28`), is documented in
the example config (`config/drs.example.yaml:38` with a comment "PVE tickets last 2h; refresh
well before"), and the manual (`docs/manual/10-configuration.md:90-97`) describes it as "How
often a username/password ticket is refreshed" — as if the operator setting this value
controls the refresh interval.

The manual's description is misleading: the knob does nothing. An operator who sets
`ticket_refresh_seconds: 600` expecting more frequent refresh will get proxmoxer's own
internal interval regardless. The `30-safety-and-status.md` per-command status table is honest
about what commands are implemented, but the configuration reference does not distinguish
between knobs that are wired through and knobs that exist for future use.

**Recommendation:** Either wire `ticket_refresh_seconds` through to proxmoxer (if proxmoxer
exposes a way to configure it — it may not, in which case this is not possible), or remove
the field, the schema entry, the example config line, and the manual entry, and document in
the plan that proxmoxer handles ticket refresh internally and the knob is not needed. If the
field is kept as a placeholder for a future hand-rolled client, mark it clearly in the manual
as "not yet effective; proxmoxer manages its own refresh" — the manual must not describe a
knob as functional when the code ignores it.

### 11.4 P-02 — `proxmox.read_workers` is a dead config knob

**Severity:** Medium
**Files:** `config.py:69`, `topology.py`, `docs/manual/10-configuration.md:99`,
`config/drs.example.yaml:41`

The manual documents `proxmox.read_workers` as: "Size of the bounded thread pool used to
fetch per-VM configuration — `GET /nodes/{node}/qemu/{vmid}/config` has no batch form, so this
is what keeps a several-hundred-VM cluster's topology read from being serial."

But `topology.py`'s `build_topology()` fetches VM configs sequentially in a `for` loop
(`topology.py:448-455`), with no thread pool, no `concurrent.futures`, and no use of
`config.proxmox.read_workers` anywhere. The field is parsed by `config.py` (`config.py:406`)
but never consumed by any module.

The plan §3.5 specifies the concurrent read path and the updated call count formula
(`3 + 2|VMs| + 2|S|`), and the config knob is the right design for when the thread pool is
implemented. But the manual describes it as if it works now. An operator with 500 VMs who sets
`read_workers: 1` expecting serial fetches would get... serial fetches regardless (which is
what happens), but an operator who sets `read_workers: 20` expecting parallelism would also
get serial fetches. The manual's claim "this is what keeps a several-hundred-VM cluster's
topology read from being serial" is currently false.

**Recommendation:** Either implement the concurrent fetch path in `topology.py` (the plan
specifies it), or add a note to the manual entry saying the thread pool is not yet
implemented and `read_workers` has no effect in this build. The `30-safety-and-status.md`
table is the right pattern: be honest about what the code does, not what the plan says it will
do. A config knob that is parsed but silently ignored is exactly the kind of gap
`30-safety-and-status.md` exists to prevent.

### 11.5 P-03 — Manual omits `VM.Config.Disk` and `VM.Migrate` privileges

**Severity:** Low
**Files:** `docs/manual/00-installation.md`, `IMPLEMENTATION_PLAN.md` §3.5

The plan §3.5 says: "move_disk needs nothing beyond that on the storage side (the VM side
needs `VM.Config.Disk` and `VM.Migrate` or equivalent, out of scope for this note). Document
this precisely in the operator manual rather than repeating the more comfortable but wrong
'Audit is enough' claim."

The manual's installation section (`00-installation.md`) documents `Datastore.Allocate`,
`Datastore.Audit`, and `VM.Audit` in detail (including the silent-empty-list failure mode for
Audit-only on `/content`), but does not mention `VM.Config.Disk` or `VM.Migrate` at all. The
requirements section says "permission to call `move_disk`" without specifying what that means
in terms of PVE privileges. An operator setting up the credential today would not know to
grant these VM-level privileges, and would only discover the gap when `apply` is implemented
and fails with a permission error.

Since `apply` (which calls `move_disk`) is not yet implemented, this is forward-looking. But
the manual says "permission to call `move_disk`" in the requirements now, and the plan says
to document it precisely in the operator manual. The `Datastore.Allocate` finding is
documented excellently; the VM-level privileges should get the same treatment, even if only
as a note that these will be needed when `apply` is implemented.

**Recommendation:** Add a section to `00-installation.md` (or a note in the existing
"Setting up the PVE credential" section) naming `VM.Config.Disk` and `VM.Migrate` as the
privileges `move_disk` requires on the VM side, noting they are only needed for `apply` (not
for `verify-metrics`, `show-load`, or `verify-storages`, which only read).

### 11.6 Verification

- `python3 -m pytest`: 223 passed, 1 skipped (statsmodels not installed), 98.61% coverage —
  above the 85% floor. No failures.
- `python3 tests/fixtures/generate_expected.py --check`: exits 0 — both fixture expected
  files current.
- `sha256sum --check docs/IMPLEMENTATION_PLAN.pdf.sha256 docs/internals.pdf.sha256
  docs/pve-storage-drs-manual.pdf.sha256`: all pass — all three committed PDFs match their
  Markdown sources.
- `python3 -m pytest tests/unit/test_documentation.py -v`: 12 passed — every config schema
  key appears in the manual, the manual documents no nonexistent keys, the example config
  validates against the schema, every CLI option appears in the manpage, and the manpage has
  all required sections.
- `__version__` in `__init__.py` (`0.0.1`), `pyproject.toml` (`0.0.1`), and
  `debian/changelog` (`0.0.1`): all agree.
- `proxmoxer` is consistently classified as a hard dependency: `pyproject.toml`
  `dependencies`, `debian/control` `Depends` and `Build-Depends`, and `mypy.overrides`
  (`ignore_missing_imports` for no type stubs). The `pve.py` module-level import is safe
  because `python3-proxmoxer` is in `Depends`, so the autopkgtest's `import-all` will succeed.
- `config_schema.json` is packaged via `[tool.setuptools.package-data]`, so the
  `importlib.resources` load in `config.py` works from the installed package.
- The "Is there code yet?" probes in both GitHub Actions workflows were correctly removed
  now that `src/` exists, and the Makefile `test` target no longer has the "skip if no tests"
  guard.
- `tools/build_paper.sh` is a clean generalization of the previous inline Makefile recipe:
  one shared pandoc+LuaLaTeX pipeline for all three PDFs, with per-document title/subtitle.
- The `docs/manual/30-safety-and-status.md` per-command status table honestly reports which
  commands are implemented and which are not, including the note that `show-load` does not yet
  compute per-disk I/O load (needs `loadmodel.py`).

### 11.7 Assessment

The first implementation is strong. The code matches the plan, the test coverage is
excellent, the documentation cross-reference tests are the right mechanism, and the
honest "not implemented yet" handling in both the CLI and the manual's status table is
exactly the discipline the project's own rules demand. The three findings (P-01..P-03) are
all in the same category: config knobs or privileges that are documented as functional but
are not yet wired through. P-01 and P-02 are Medium because an operator could change a value
and see no effect, which erodes trust in the configuration system; P-03 is Low because
`apply` is not implemented yet, so the missing privileges cannot currently cause a failure.
None are architectural — resolving them is a matter of either implementing the feature or
marking the manual entry as "not yet effective in this build."

---

## 12. Resolution of seventh-pass findings (P-01..P-03)

| ID | Status | How resolved |
|----|--------|--------------|
| P-01 | Resolved | `proxmoxer` 2.x has no constructor argument for a password/ticket auth's refresh interval (`ProxmoxHTTPAuth.renew_age` is a hard-coded `3600` class attribute, confirmed by reading the installed `proxmoxer` 2.3.0 source, not guessed) — this was genuinely "not possible" via `proxmoxer`'s public interface, as the finding's own recommendation anticipated. `pve.py`'s `_apply_ticket_refresh_seconds()` now wires `ticket_refresh_seconds` through anyway by overriding that instance attribute after login (reaching into `api._backend.auth`, undocumented but stable across the installed version; `getattr`/`hasattr`-guarded, a silent no-op for API-token auth or a future `proxmoxer` shape). Going beyond the finding's own ask: `PveClient._call()` now also reauthenticates from scratch and retries once on any `AuthenticationError`, covering the case the operator raised directly — a ticket that expires for reasons external to any call (a long `apply --confirm` wait, a suspended process, a clock jump) where `proxmoxer`'s own lazy renewal, and even a correctly-tuned `renew_age`, cannot help, because the gap between calls is what invalidated it, not the passage of the process's own clock. |
| P-02 | Resolved | `topology.py`'s per-VM fetch (`vm_config`/`vm_snapshots`) now runs across a `concurrent.futures.ThreadPoolExecutor` bounded by `config.proxmox.read_workers`, split into a network-only fetch phase (`_fetch_vm`, run by the pool) and a pure join phase (`_join_vm_disks`, run single-threaded afterward in `ThreadPoolExecutor.map()`'s original order) so `disks_by_group`/`referenced_volids`/`warnings` stay byte-for-byte identical to a fully sequential run regardless of `read_workers` or thread scheduling. `PveClient` is shared across the pool's threads; its new P-01 reauthenticate path takes a lock so concurrently-expiring tickets serialize onto one fresh login rather than stampeding. |
| P-03 | Resolved | `docs/manual/00-installation.md` now names `VM.Config.Disk` and `VM.Migrate` explicitly, in the same "Setting up the PVE credential" section as the datastore privileges, with the same honesty discipline the rest of that section already has: stated as needed only once `apply` executes a move, not for any command implemented today. |

Verification: `python3 -m pytest` — 231 passed, 1 skipped (`statsmodels` not installed), 98.78%
coverage (`pve.py` at 100%, both new lines this round). `make lint typecheck` clean.

---

## 13. Eighth-pass review of phases 3-4

Commits `5994dc1..9a7c270` add phases 3 and 4: `loadmodel.py` (section 4), `gates.py` (section 6),
`heuristic.py` (section 5.4/5.5), plus the P-01/P-02/P-03 fixes and the unused-disk root-cause
documentation. The `reserve.py` and `metrics.py` modules were extended with the
`storage_of` callback and `compute_disk_coverage()` extraction those new modules needed, and
`cli.py`'s `show-load` now computes and displays per-disk/per-storage load and a per-group gate
verdict.

The implementation continues to be high quality. The heuristic's `evaluate_assignment()` is
correctly factored as a pure function shared with the future MILP path, the repair-before-descend
design makes the "reserve is never traded" invariant literal rather than merely well-weighted,
and the test suite cross-checks the heuristic's objective totals against REVIEW.md Appendix A's
hand-derived values to five decimal places (2.533333 / 3.158333). The gates module correctly
implements the three-gate cascade in section 6's order, with the degenerate-case table handled.
The `pve.py` reauthenticate-and-retry-once path is well-designed: the `threading.Lock` prevents
a stampede, the closure over `_trial` in `_repair`'s inner loop avoids the classic late-binding
bug, and the `storage_of` callback on `reserve.py` is the clean extension point the plan's
"identical shape" requirement demands.

### 13.1 Resolution of seventh-pass findings

All three (P-01..P-03) are resolved — see section 12 for the full record.

### 13.2 Summary of eighth-pass findings

| ID | Severity | Section / File | Topic |
|----|----------|----------------|-------|
| Q-01 | Low | §5.4, heuristic.py, config.py | `objective.spread_metric: minmax` is accepted by the schema and documented in the manual but silently ignored by the heuristic — always computes L1 |
| Q-02 | Low | §4, loadmodel.py, cli.py | `compute_group_load` fetches 7 Prometheus queries per group; a multi-group config re-fetches the same unfiltered series N times — acknowledged in internals docs but not in the manual |

### 13.3 Q-01 — `objective.spread_metric: minmax` silently ignored by the heuristic

**Severity:** Low
**Files:** `heuristic.py:157`, `config.py:164`, `config_schema.json:155`,
`docs/manual/10-configuration.md`

The config schema accepts `spread_metric: "l1"` or `"minmax"`. The manual documents both:
"`l1` (sum of each storage's deviation from the group's target utilization) or `minmax` (only
the single hottest storage)." The plan's section 5.4 defines both forms: `e_s` for L1
(`α · Σ e_s`), `t` for minmax. Section 15.1's traceability table maps `objective.spread_metric`
to "§5.3 (C6), L1 vs min–max".

But `heuristic.py`'s `evaluate_assignment()` always computes L1: `spread_e[storage.id] = abs(u_s
- average_utilization)` and `imbalance_term = objective.alpha_spread * sum(spread_e.values())`.
The `objective.spread_metric` field is never read. An operator who sets `spread_metric: minmax`
gets L1 behaviour regardless — the same class of silent-ignoring that P-01 and P-02 identified
for other config knobs.

This is Low rather than Medium because: (a) the default is `l1`, so an operator has to actively
choose `minmax` to be affected; (b) the heuristic is not yet wired into any CLI command, so no
production decision is currently made from this path; (c) the MILP path (`optimize.py`, not yet
written) is where `spread_metric` will matter most, since the CP-SAT/CBC model needs to
construct either the `e_s` variables or the `t` variable depending on it.

**Recommendation:** Either implement the minmax form in `evaluate_assignment()` (it is a
one-line change: `max(spread_e.values())` instead of `sum(spread_e.values())` when
`objective.spread_metric == "minmax"`), or — if the heuristic is intentionally L1-only and
minmax is a future MILP-only option — add a note to the manual's `spread_metric` entry saying
the heuristic always uses L1 and `minmax` only affects the MILP solver (not yet written). The
test suite should assert whichever behaviour is chosen.

### 13.4 Q-02 — Per-group Prometheus query redundancy in multi-group configs

**Severity:** Low
**Files:** `loadmodel.py:194-195`, `cli.py:416-424`, `docs/internals/70-loadmodel.md:30-37`

`compute_group_load()` calls `compute_disk_coverage()` (1 range query) and
`_fetch_all_raw_quantities()` (6 instant queries) — 7 Prometheus queries per group. Since
`show-load` calls it once per group in a loop (`cli.py:416`), a config with N groups makes 7N
queries. The coverage query and all six raw-quantity queries are unfiltered by group (they use
`sum by (vmid, device)` which returns all disks), so the same data is fetched N times and
discarded N-1 times.

The internals doc (`70-loadmodel.md:30-37`) acknowledges this as a "known limitation, not a bug"
and notes that "fetching once and slicing per group would be a straightforward follow-up if a real
deployment's group count ever makes this Prometheus load worth avoiding." This is honest, but
the manual does not mention it — an operator with 10 groups and a busy Prometheus might wonder
why `show-load` issues 70 queries when 7 would suffice.

This is Low because: the typical deployment has 1-3 groups (the worked example has 1); the
queries are instant queries (fast); and the redundancy is correct (each group's
coverage/rejection decisions are independent). It is a performance note, not a correctness issue.

**Recommendation:** Either add a note to the manual's `show-load` section mentioning that
multi-group configs issue queries per group (so an operator with many groups and a busy
Prometheus is not surprised), or leave it as an internals-only note since it is unlikely to
matter in practice. No code change is needed for correctness.

### 13.5 Verification

- `python3 -m pytest`: 277 passed, 1 skipped (statsmodels not installed), 98.69% coverage —
  above the 85% floor. No failures.
- `python3 tests/fixtures/generate_expected.py --check`: exits 0 — both fixture expected files
  current.
- `sha256sum --check` on all three PDF stamps (plan, internals, manual): all pass.
- Heuristic objective totals cross-checked against REVIEW.md Appendix A's hand-derived values:
  three-move (β=0.25) total = 2.533333 ✓; two-move (β=0.50) total = 3.158333 ✓; initial imbalance
  E_before = 8.0667 ✓. The test assertions match the Appendix A values to 5 decimal places.
- `gates.py`'s imbalance computation matches the plan's section 6 formula exactly:
  `(max(u_s) - min(u_s)) / u*` — this is the minmax form, correctly independent of
  `objective.spread_metric` (the gate always uses minmax per the plan, regardless of the
  objective's spread metric setting).
- `reserve.py`'s `storage_of` callback extension is correctly used by `heuristic.py` for
  candidate-assignment evaluation and by `cli.py`/`topology.py` for current-state reporting
  (defaulting to `_current_storage`). The `Storage.foreign_used_bytes` is correctly
  assignment-invariant (foreign volumes are never members of D).
- `pve.py`'s reauthenticate path: the `threading.Lock` serializes concurrent reauthentication,
  the `_build_api` split allows both initial login and reauth to share the same construction
  code, and the `_apply_ticket_refresh_seconds` is a guarded no-op for API-token auth and for
  any `proxmoxer` internal shape change. Test coverage: `test_pve.py` has 7 new tests covering
  reauth success, reauth failure, retry failure, transport failure after reauth, no-callback
  behaviour, `ticket_refresh_seconds` application, and `_apply_ticket_refresh_seconds` as
  no-op.
- `topology.py`'s concurrent fetch: `ThreadPoolExecutor.map()` preserves order, the
  fetch/join split keeps `disks_by_group`/`warnings` deterministic, and `read_workers=1`
  degenerates to sequential. The `PveClient` is shared across threads.
- `metrics.py`'s `compute_disk_coverage` extraction correctly shares the coverage computation
  between `verify-metrics`'s report and `loadmodel.py`'s per-disk gate — one implementation
  per AGENTS.md section 5.
- The `show-load` command now displays `ℓ_d`, `L_s`, `u_s`, gate verdicts, coverage warnings,
  and idle-group detection, and degrades gracefully on a per-group Prometheus outage. The
  manual's `30-safety-and-status.md` status table is updated to reflect the new
  functionality.
- `docs/internals/70-loadmodel.md`, `80-gates.md`, `90-heuristic.md` correctly describe what
  each module does, what it deliberately does not do yet (polish, format eligibility,
  `state.json` wiring, cooldowns), and cross-reference the plan sections and REVIEW.md
  Appendix A.

### 13.6 Assessment

Phases 3-4 are solid. The load model, gates, and heuristic all match the plan, the test suite
cross-checks the heuristic's objective arithmetic against independently hand-derived values, and
the honest "not yet implemented" handling continues in both the code (heuristic step 4 polish
and format eligibility are documented gaps) and the documentation (`30-safety-and-status.md`'s
status table, `90-heuristic.md`'s "what this pass deliberately does not do" section). The two
findings (Q-01..Q-02) are both Low: Q-01 is a config knob silently ignored by the heuristic
(same pattern as P-01/P-02, but lower severity because the heuristic is not yet wired into any
command and the default is the implemented value), and Q-02 is a per-group query redundancy
already acknowledged in the internals docs. Neither is a correctness issue.

## 14. Resolution of eighth-pass findings (Q-01..Q-02)

| ID | Status | How resolved |
|----|--------|--------------|
| Q-01 | Resolved | `evaluate_assignment()` now reads `objective.spread_metric`: `"l1"` (default, unchanged) sums every storage's deviation from `u*`; `"minmax"` uses `alpha * max(u_s)` — the plan's own `t >= u_s`, the *raw* utilization of the hottest storage, not `max(e_s)` (a deliberate correction of the finding's own one-line suggestion, which would have computed the wrong quantity — a cold storage's large deviation below `u*` would then wrongly influence a metric the plan and the manual both describe as reacting only to the single hottest storage). `ObjectiveBreakdown` gained a `utilization` field so both views are always available regardless of which metric is active. Three new tests, including one built directly from the manual's own "indifferent to a second nearly-as-bad storage" claim, made concrete with numbers. `docs/internals/90-heuristic.md` documents the distinction explicitly, since it is easy to get backwards. |
| Q-02 | Resolved | Documented rather than changed, per the finding's own recommendation: the manual's `show-load` page now states that an `N`-group config issues `7N` Prometheus queries, not 7, and why (each group's coverage/data-quality decisions are independent, so the fetch cannot be shared). No code change — the finding's own severity assessment (correct, just wasteful for many groups) still applies. |

Verification: `python3 -m pytest` — 280 passed, 1 skipped (`statsmodels` not installed). `make
lint typecheck` clean.

---

## 15. Ninth-pass review — phases 4-5 (schedule, payback, plan command)

Reviewed commit range `9a7c270..HEAD` (commits `9495f95` through `2ad37a5`).
Changes: Q-01/Q-02 fixes, `schedule.py` (new, 245 lines), `payback.py` (new, 229
lines), `heuristic.py` refactor (repair oscillation fix, `spread_metric` support,
`group_average_utilization` made public, `ObjectiveBreakdown.utilization` field
added), `cli.py` `_handle_plan` wired (336 new lines), 4 new test files (934 new
lines), 2 new internals pages, 1 new manual page, manpage and status-table
updates.

### Verification run

- `python3 -m pytest`: **311 passed, 1 skipped** (statsmodels), **98.54% coverage**.
- `python3 tests/fixtures/generate_expected.py --check`: OK (fixtures current).
- `sha256sum --check` on all three PDF stamps: all OK.
- §14.5 arithmetic independently re-derived: m1 cost 15728.64, m2 cost 10485.76,
  total 26214.4, benefit 3951360, ratio 150.73 — all match. Archive-disk ratio
  0.721 — matches.
- §14 three-move plan (manual's `plan` example): cost 31457, benefit 4193320,
  ratio 133.3, before→after spread 255.4%→44.6%, all Δimbalance and ℓ/z values —
  all match.

### Findings

| ID | Severity | Module | Summary |
|---|---|---|---|
| R-01 | Medium | `payback.py`/`cli.py` | Payback benefit uses `alpha`-scaled `imbalance_term`, not the plan's raw `Σ_s e_s` |
| R-02 | Medium | `cli.py` | `plan`'s `after:`/`after_spread` shows the target assignment, not the scheduled state — misleading when moves deadlock |
| R-03 | Low | `cli.py` | `--group` flag is accepted but silently ignored by every handler, including `plan` |
| R-04 | Low | `docs/internals/95-schedule.md` | Stale: says `payback.py` "does not exist yet" — it was added in this same review window |
| R-05 | Low | `cli.py` | Human-output payback warning conflates economic failure and hard-duration-rule failure |
| R-06 | Low | `cli.py` | `load_per_tib` division by zero when `move.size_bytes == 0` (unguarded) |

### 15.1 R-01 — Payback benefit is `alpha`-scaled, but the plan's `E` is not

**Plan §7.2** defines `E_before = Σ_s e_s` — the raw sum of per-storage deviations
from `u*`, with no `alpha_spread` multiplier. **The code** passes
`heuristic.ObjectiveBreakdown.imbalance_term` to
`compute_benefit_load_seconds()`, and `imbalance_term = alpha_spread * spread`
(where `spread` is `Σ_s e_s` for L1 or `max(u_s)` for minmax).

With the default `alpha_spread = 1.0` the two are identical and every §14
fixture cross-checks pass. But with `alpha_spread ≠ 1.0`:

- `benefit` is scaled by `alpha_spread` on both sides, so `(E_before - E_after)`
  is scaled by `alpha` while the migration cost is not.
- A higher `alpha` makes the payback ratio easier to pass; a lower one makes
  it harder. The economic acceptance test thus depends on the solver's tuning
  knob, not just on the imbalance reduction and migration cost.
- The `compute_benefit_load_seconds()` docstring calls this "the *unweighted*
  (`alpha_spread`-scaled, which defaults to 1.0)" — "unweighted" and
  "alpha_spread-scaled" are contradictory.

This is either a code bug (should pass `sum(spread_e.values())` for L1, or the
raw `max(utilization.values())` for minmax) or a plan gap (§7.2 should say
`E_before = alpha * Σ_s e_s` if the scaling is intentional). Either way, the
plan and the code should agree, and the docstring's "unweighted" label should
be corrected.

**No test exercises `alpha_spread ≠ 1.0` with payback** — the gap is invisible
to the suite.

### 15.2 R-02 — `after:`/`after_spread` reflects the target, not the schedule

`_render_plan_human` and `_render_plan_json` compute `after_spread` from
`heuristic_result.breakdown.utilization` — the heuristic's *target* assignment,
which includes every move the heuristic proposed. When `order_moves()`
deadlocks some of those moves (transient infeasibility), the `after:` line and
`spread:` line still show the utilization *as if all moves completed*,
overstating the achievable result.

The `after:`/`spread:` lines are gated on `if schedule_result.order:` (human)
and on `heuristic_result is not None` (JSON), so a *fully* deadlocked plan
(order is empty) does not show them. But a *partially* deadlocked plan — some
moves scheduled, some not — shows the full target's spread, not the scheduled
subset's. No test covers a partial-deadlock scenario; the existing deadlock
tests all have either zero or all moves deadlocked.

The scheduled state is tracked inside `order_moves()` (the `state` dict) but
not exposed in `ScheduleResult`. Fix: either expose the final scheduled state
in `ScheduleResult` and compute `after_spread` from it, or compute it in
`cli.py` by applying `schedule_result.order` to the initial assignment.

### 15.3 R-03 — `--group` flag silently ignored

The `--group` argument is defined in `build_parser()` (`action="append"`,
`default=None`) and documented in the manpage's OPTIONS section, but
`args.group` is never read by any handler — not `show-load`, not
`verify-storages`, not the new `plan`. `build_topology()` does not accept a
group filter. Every handler iterates `for group in topology.groups:` without
filtering.

This is pre-existing (the flag predates this review window) but the new `plan`
command inherits it: `pve-storage-drs --group fc-tier2 plan` silently runs
all groups, contradicting the manpage's "Restrict the run to one storage
group."

### 15.4 R-04 — Stale reference in `95-schedule.md`

`docs/internals/95-schedule.md` line 78:

> Reasoning correctly about overlapping in-flight windows needs move duration
> estimates from `payback.py`, which does not exist yet.

`payback.py` was added in commit `f0f955d`, within this review window. The
sentence should be updated to say the module exists but the concurrent
scheduling that would use its duration estimates is not yet implemented.

### 15.5 R-05 — Payback warning conflates two failure modes

`_render_plan_payback_lines` shows `"⚠ this plan does not pass section 7.3's
payback test"` whenever `payback_result.accepted` is False. But `accepted =
aggregate_ok and not rejected_moves`, so the warning fires for two distinct
cases:

1. **Economic failure**: `aggregate_ok` is False (benefit < ratio * cost).
2. **Hard-duration failure**: `aggregate_ok` is True but `rejected_moves` is
   non-empty (a move exceeds `max_single_move_duration`).

The existing test `test_plan_human_output_shows_the_payback_verdict` hits case
2 (a reserve-exempted plan with a slow `saferemove` wipe), and the warning text
says "does not pass section 7.3's payback test" even though the *economic* test
did pass — only the hard per-move rule blocked it. The JSON output keeps
`aggregate_ok` and `accepted` separate, so this is human-output only, but the
message is misleading for an operator reading the terminal.

### 15.6 R-06 — `load_per_tib` division by zero

`_render_plan_move_line` computes `load_per_tib = load / (move.size_bytes /
_BYTES_PER_TIB)`. If `move.size_bytes == 0` the denominator is 0.0 and the
division raises `ZeroDivisionError`. The same expression appears in
`_render_plan_json` (line 600-601).

PVE does not report zero-size disks in practice, and the schema does not
forbid `size_bytes: 0` explicitly (it is an `integer` with no `minimum` in
`config_schema.json`, but the value comes from the PVE API, not config). This
is a defense-in-depth gap, not a live bug.

### What this pass confirms

- The `_repair` oscillation fix (group-wide shortfall, not source-only) is
  correct and well-tested. The extracted `_best_repair_candidate` preserves the
  original comparison logic exactly.
- The `spread_metric: "minmax"` implementation is correct: `alpha * max(u_s)`,
  not `alpha * max(e_s)`, with both `spread_e` and `utilization` always
  populated. The test built from the manual's own "indifferent to a second
  nearly-as-bad storage" claim is a good regression guard.
- The reserve-override exemption in `evaluate_plan_payback` is sound: a
  reserve-fixing plan always passes the economic test (section 13), but the
  hard per-move duration rule still applies. Both halves are tested.
- `compute_wipe_duration_seconds` is correctly shared between `payback.py`
  and `verify-storages` (one implementation, not two — AGENTS.md §5).
- All §14 fixture arithmetic cross-checks pass. The manual's three-move `plan`
  example (ratio 133, spread 255.4%→44.6%) is internally consistent.

---

## 16. Resolution of ninth-pass findings (R-01..R-06)

All six findings were real; all six are fixed, not refuted.

| ID | Status | How resolved |
|----|--------|--------------|
| R-01 | Resolved | Added `heuristic.raw_spread(breakdown, spread_metric)`, returning the true unweighted §7.2 `E` (`sum(e_s)` or `max(u_s)`), and switched `cli._handle_plan()` to pass that to `compute_benefit_load_seconds()` instead of `ObjectiveBreakdown.imbalance_term` (which is `alpha_spread`-scaled). `payback.compute_benefit_load_seconds()`'s docstring no longer calls `imbalance_term` "unweighted" — it names `raw_spread()` as the required input and explains why `imbalance_term` is the wrong one. No behavior change at the default `alpha_spread: 1.0` (every existing §14 cross-check still passes byte-for-byte); a plan with `alpha_spread != 1.0` now gets a payback ratio independent of that tuning knob. |
| R-02 | Resolved | `ScheduleResult` gained `final_assignment`: the assignment actually reachable by applying `order` in sequence, computed by `order_moves()` itself (it already tracked this internally as `state`). `_handle_plan()` now evaluates a fresh `ObjectiveBreakdown` against `final_assignment` (via `heuristic.evaluate_assignment()`) and uses *that* — not the heuristic's own `.breakdown` on its full target assignment — for `after_spread`, the `after:` line, and (extending the same reasoning) the payback benefit's `E_after`. A partially- or fully-deadlocked plan is now scored and reported on what it can actually achieve, not on moves that never got scheduled. New test: `test_plan_after_and_payback_reflect_only_the_scheduled_moves_on_partial_deadlock`, which stubs `run_heuristic()`/`order_moves()` for an exact one-scheduled/one-deadlocked scenario and asserts the reported numbers match the scheduled-only state and *not* the aspirational target's. |
| R-03 | Resolved | Added `cli._filter_groups(topology, args.group)`, called by `show-load`, `verify-storages` and `plan` immediately after `build_topology()` (`verify-metrics` does not iterate groups at all, so it is correctly left alone). An unknown group name is a hard failure (`DrsError`, exit 1) rather than a silent no-op, matching the project's existing "an explicitly named thing that cannot be found is an error" rule for `-c`/`--config PATH`. Manpage and `docs/internals/40-cli-and-logging.md` updated; four new tests cover restriction, repeatability, and the unknown-name failure. |
| R-04 | Resolved | Both `schedule.py`'s own module docstring and `docs/internals/95-schedule.md` no longer say `payback.py` "does not exist yet" — they now say concurrent scheduling could use its duration estimates but does not yet, and (a related staleness the same lines implied) that `cost_m = z_d`'s "exact, not an approximation" ordering argument now has a caveat: `payback.py` gives moves individually different costs (per-storage `saferemove` throughput), so `z_d` alone is only mirror-duration-exact, not full-cost-exact, whenever wipe costs differ enough across candidates. |
| R-05 | Resolved | `_render_plan_payback_lines()` now checks `aggregate_ok` and `rejected_moves` separately and emits a distinct line for each: an economic failure ("this plan's balance benefit does not outweigh its migration cost") and a hard-duration failure ("blocked by the hard per-move duration rule", naming the disk keys) never share text, and either, both or neither can appear on the same plan. `docs/manual/27-plan.md`'s payback section explains the distinction and why it matters (different fixes for different failures). New direct test `test_render_plan_payback_lines_separates_economic_and_duration_failures` exercises all four combinations; the existing `test_plan_human_output_shows_the_payback_verdict` (case 2, hard-duration-only) now asserts the specific new message and asserts the economic-failure message is *absent*. |
| R-06 | Resolved | Extracted `_load_per_tib()`, returning `0.0` for `move.size_bytes <= 0` instead of dividing by zero; used by both the human move line and the JSON `load_per_tib` field (one implementation, not two — AGENTS.md §5). New direct test `test_load_per_tib_is_zero_not_a_division_error_for_a_zero_size_disk`. |

As a side effect of R-01/R-02 together, `_render_plan_human()`/`_render_plan_json()` no longer take a `heuristic_results` parameter at all — everything they previously read from it (`.breakdown.utilization` for "after") is now read from the new, more correct `final_breakdowns` dict instead, and nothing else in either render function ever needed the raw `HeuristicResult`.

Verification: `python3 -m pytest` — 317 passed, 1 skipped (`statsmodels` not installed), 98.68% coverage. `make check` clean (fmt, lint, typecheck, test, fixtures, docs-check — internals PDF rebuilt to 23 pages, manual PDF to 26).

---

## 17. Tenth-pass review — state, cooldowns, MILP backends (phase 6) and execution (phase 7)

Reviewed commit range `2ad37a5..HEAD`: `de7deda` (the R-01..R-06 fixes, already recorded in
section 16), `d0e9f2f` (`state.py`, section 11.2, drift history wired into `show-load`/`plan`),
`a573855` (cooldown wiring: `state.py` queries, `topology.py`'s (C2) per-disk pin,
`heuristic.py`'s per-storage target exclusion), `375d3a9` (`optimize.py`, phase 6: CP-SAT and
CBC MILP backends, wired into `plan`), `c6760c9` (`execute.py`, phase 7: move execution,
`apply` wiring). Roughly 5,500 inserted lines of source and tests across the five commits,
~2,700 of them tests.

The engineering quality remains high — the state-file locking design (and the
rename-detaches-the-`flock` trap it documents and tests), the section 5.5 coefficient folding,
the three-condition completion criterion and the injectable `Clock` are all better than the
plan strictly demands. But this pass also found the two most serious implementation defects
so far, and both are in the newest code: the CBC backend cannot run on the pulp version
Debian trixie ships (the packaged solver path, §2.1), and `apply` ignores the payback
acceptance test entirely.

### 17.1 Verification run

- Dev venv `python3 -m pytest`: **424 passed, 17 skipped** (ortools, pulp and statsmodels are
  absent from the venv), **90% line coverage** — above the 85% floor.
- `tests/fixtures/generate_expected.py --check`: OK. `sha256sum --check` on all three PDF
  stamps: OK. (`make check`-equivalent for the local toolchain is green.)
- **CI environment reproduced locally.** This host's system Python carries pulp **2.7.0** —
  the same version Debian trixie packages (`python3-pulp 2.7.0+dfsg-4`, confirmed with
  `rmadison`), which is also exactly what `.github/workflows/tests.yml` installs from apt in
  its `debian:trixie` container. Running the suite with it: **24 failed, 408 passed** — every
  CBC-parametrized test in `test_optimize.py` dies on the same `AttributeError` (S-01). The
  CBC tests do *not* skip there: `cbc_available()` only checks that `import pulp` succeeds,
  which it does.
- **The CBC logic itself is sound.** In a throwaway venv with pulp **3.3.2**, the same tests
  all pass — including both §14 fixture reproductions (β=0.25 three-move, β=0.50 two-move),
  the `reserve-tradeoff` lexicographic-optimum test and the minmax/heuristic-agreement test.
  The defect is purely library-version compatibility, not model logic.
- Bisected pulp's releases by downloading and inspecting each wheel: `LpProblem.add_variable`
  first exists in **pulp 3.3.1**; 3.3.0 and every earlier release (including 2.7.0) lack it.
- `python3 -c "import pulp; ..."` on the system 2.7.0 confirms `LpProblem` exposes only the
  camelCase `addVariable`/`addVariables`, and that `pulp.apis.coin_api` raises
  `PulpSolverError` when the cbc binary cannot be executed (relevant to S-01's second half).

### 17.2 Findings summary

| ID | Severity | Module(s) | Summary |
|----|----------|-----------|---------|
| S-01 | High | `optimize.py`, `pyproject.toml` | CBC backend calls `prob.add_variable()`, which needs pulp ≥ 3.3.1 — but the extra declares `pulp>=2.7` and the target platform packages 2.7.0, so the packaged solver path crashes; CI installs that version and its CBC tests cannot pass |
| S-02 | High | `cli.py`, `execute.py` | `apply` executes the scheduled plan regardless of the §7.3 payback verdict — including individual moves the *hard* per-move duration rule rejected; §7.3's re-solve-with-doubled-β/γ retry is absent too |
| S-03 | Medium | `cli.py`, `state.py` | the per-storage cooldown is recorded for the **destination** only, so a still-draining *source* storage is never protected — defeating the exact scenario §9.3's knob-sizing rule and `verify-storages`' own warning text describe |
| S-04 | Medium | `optimize.py` | the MILP backends ignore `cooldown_storages` (heuristic-only enforcement); the module docstring's "cooldowns are inert today" justification went stale the moment phase 7 landed, and §5.5's "backends directly comparable" requirement is now violated |
| S-05 | Medium | `execute.py` | §9.3's "mark the storage draining, exclude it as both source and target for the remainder of the run" is not implemented — a `draining` outcome changes nothing for later moves in the same run |
| S-06 | Low | `execute.py` | §9.2's pre-flight does not re-check exclusion tags (step 3's "untagged for exclusion"); a VM tagged `no-drs` between planning and execution is still moved |
| S-07 | Low | `optimize.py` | lexicographic stage 1 accepts a gapped incumbent as the reserve floor (CP-SAT `FEASIBLE`; CBC's gap-satisfied "Optimal"), weakening §5.3's "provably never traded" guarantee by up to `mip_gap`, and the two backends pin it differently (`==` vs `<=`) |
| S-08 | Low | `docs/manual/10-configuration.md` | the four phase-8 knobs are documented as functional with no "not yet effective" caveat — the same pattern P-01/P-02 established as a finding |
| S-09 | Low | `optimize.py` vs plan §5.5 | the plan's model-build-time assertions (non-zero integer coefficient wherever the unscaled weight is non-zero; objective magnitude < 2⁶²) are neither implemented nor removed from the plan; the docstring argues only against the *post-solve* half |

### 17.3 S-01 — the CBC backend requires pulp ≥ 3.3.1 but targets trixie's 2.7.0

**Severity:** High
**Files:** `src/proxmox_storage_drs/optimize.py:517-531`, `pyproject.toml:37`,
`docs/internals/91-optimize.md:80`, `IMPLEMENTATION_PLAN.md` §2.1

`_cbc_feasibility_constraints()` builds every variable with `prob.add_variable(...)`, with a
comment saying the direct `pulp.LpVariable(...)` constructor is "PuLP's v4 migration
deprecates". Two facts make that choice wrong for this project:

1. `LpProblem.add_variable` does not exist in pulp ≤ 3.3.0 — verified by wheel inspection
   across 2.7.0, 2.8.0, 2.9.0, 3.0.0, 3.1.1, 3.2.0, 3.2.2, 3.3.0 (absent) and 3.3.1, 3.3.2
   (present). The "v4 migration" is a *future* API; the present-tense deprecation direction
   only applies to 3.3+.
2. The deployment target packages **pulp 2.7.0** (`python3-pulp 2.7.0+dfsg-4` in trixie), and
   §2.1 says plainly: "on a Debian install the MILP is solved by **CBC through
   `python3-pulp`**". This is the packaged solver path.

Consequences, all reproduced locally:

- With pulp 2.7.0 installed, `_solve_cbc()` raises
  `AttributeError: 'LpProblem' object has no attribute 'add_variable'. Did you mean: 'addVariable'?`
  on the first variable — `solve()`'s "returns None, never raises" contract is violated, no
  heuristic fallback happens (§13's "solver infeasible or timing out → fall back to the
  heuristic" — a backend that *cannot construct its model* is at least that), and the whole
  `plan`/`apply` invocation crashes with a traceback.
- The test suite parametrizes every solve test over `cbc` with a skip condition of
  `not cbc_available()`, and `cbc_available()` only checks `import pulp`. On trixie, pulp
  imports — so the tests **run and fail**: 24 failures (17.1). `make check` in the dev venv is
  green only because the venv installs neither solver (17 skips). The GitHub Actions
  `debian:trixie` job installs `python3-pulp` from apt (this is precisely what the L-03 fix
  added) and runs `python3 -m pytest` — in that deterministic environment the job cannot be
  green on current `main` as committed (CI status was not directly observable from this
  checkout, but the container, the apt version and the test command all are). This is exactly
  the failure mode L-03 predicted in reverse: the local pip-or-nothing toolchain hid an
  apt-version incompatibility.
- `pyproject.toml`'s solver extra declares `pulp>=2.7`, so even a pip user following the
  project's own constraint can resolve a version (2.7–3.3.0) that crashes.

A second, smaller defect in the same function: `prob.solve()` is not wrapped for
`pulp.PulpSolverError`. Debian splits the CBC binary into `coinor-cbc` (a separate package,
`Recommends`, not `Depends`); a host with `python3-pulp` but without `coinor-cbc` hits
`PulpSolverError("Pulp: cannot execute ...")` — again a raised exception where the module
docstring promises `None` and §13 promises heuristic fallback.

**Recommendation:** construct variables with `pulp.LpVariable(...)` directly (works on every
version including 2.7.0 and 3.3.2; if the 3.3+ deprecation warnings are a concern, silence
them explicitly rather than adopting an API the target platform cannot provide), or
feature-detect `add_variable` with a fallback. Wrap `prob.solve()` in `except
pulp.PulpSolverError → return None`. Then either raise the extra to the version actually
required (`pulp>=3.3.1`, wrong for trixie) or — better — keep `>=2.7` and *prove* trixie
compatibility by running the CBC tests in CI, which the fix makes pass. Also correct
`91-optimize.md`'s claim that `add_variable` is "not the older constructor" in a way that
implies availability, and re-examine the module docstring's "both backends were exercised for
real during development" — true, but under pip's pulp 3.3+, which is not the packaged path
the plan designates as primary.

### 17.4 S-02 — `apply` executes plans that failed the payback acceptance test

**Severity:** High
**Files:** `src/proxmox_storage_drs/cli.py:1325-1358` (`_handle_apply`),
`src/proxmox_storage_drs/execute.py:281-304`, `IMPLEMENTATION_PLAN.md` §7, §7.3, §9

Section 7 is explicit that the payback rule is "a **hard acceptance test on the finished
plan**, not merely a soft `γ` penalty, because a penalty can always be outweighed by a large
enough imbalance term", and §7.3's per-move rules "**reject** individual migrations
regardless of the aggregate test" (`duration_d > max_single_move_duration` → reject the
move). §1 lists "a migration's own I/O cost must not exceed the imbalance it removes" as a
goal-scope requirement.

`_plan_group()` computes `payback_result` (the verdict, including `aggregate_ok` and
`rejected_moves`) — and nothing ever consults it on the execution path. `_handle_apply`
calls `execute_plan()` with `group_plan.schedule_result` whenever the gate said `act`, and
`execute_plan()` walks `order` unconditionally. Concretely:

- A plan that fails the aggregate economic test (benefit < `payback_ratio`·cost) is executed
  in full in `apply --mode confirm` — the operator is prompted move by move with no
  indication the tool's own §7.3 verdict was ✗, because the human/JSON report that *shows*
  the verdict is rendered only after all groups have executed. The tool's answer to "why did
  it move disks the payback test rejected" is, today, "it didn't check".
- Worse, a move whose `duration_d` (mirror + wipe) exceeds `max_single_move_duration` is
  listed in `rejected_moves` yet still sits in `schedule_result.order` and is issued to PVE.
  `_wait_for_move_completion()`'s own docstring claims "a move that was accepted at planning
  time already passed `migration.max_single_move_duration`" — nothing enforces that; the
  claim is false. §7.3's hard rule is exactly the operational guard against a multi-day
  wipe being started.
- §7.3's prescribed response to aggregate failure — "re-solve with `β` and `γ` doubled and
  retry, up to three times" — is implemented nowhere.

No test covers a payback-failing plan reaching `execute_plan` (grep confirms; the apply tests
cover prompts, declines, locks, failures, state writes — never the payback gate), so the gap
is invisible to the suite. The reserve-override exemption is already handled correctly
*inside* `evaluate_plan_payback` (a plan containing a reserve-resolving move passes the
economic test, and the hard duration rule still applies) — which makes the missing
enforcement the only thing between a rejected plan and production disks.

**Recommendation:** in `_handle_apply`, before executing a group: drop moves in
`rejected_moves` from the order (report them as refused per §7.3), and refuse to execute the
remaining plan when `not aggregate_ok` (report; §7.3's re-solve loop is the follow-up, and
until it exists, refusing is the correct conservative behavior — the reserve-override
exemption already lives in `aggregate_ok`). At minimum, in confirm mode show the payback
verdict *before* the first prompt, not in the post-execution report. `execute.py`'s
docstring claim about planning-time duration filtering should become true by construction.

### 17.5 S-03 — storage cooldown recorded for the destination only

**Severity:** Medium
**Files:** `src/proxmox_storage_drs/cli.py:1388-1391`, `docs/manual/28-apply.md:114-118`,
`state.py:362-363` (stale docstring), `IMPLEMENTATION_PLAN.md` §6, §9.3

`_handle_apply` records a `cooldowns.storage` timestamp for `move.to_storage` only, with an
inline justification ("a storage this run only moved disks away from is not a wear/churn
concern the cooldown protects against") echoed by the manual. The plan disagrees twice:

- §6: "a storage **involved in** a migration within `cooldown_per_storage` accepts no new
  incoming moves" — a migration has two endpoints, and the phrase covers both.
- §9.3's sizing rule is written *specifically about sources*: "`gates.cooldown_per_storage`
  must exceed the expected wipe time for that storage's largest disk, or the next run will
  plan moves onto a storage that is still draining". The wipe runs on the **source**. With
  destination-only recording, no value of `cooldown_per_storage` — however large — can ever
  protect a draining source, because sources never get a timestamp. The same inversion
  affects §11.1's validation warning and `verify-storages`' own message ("the next run may
  plan onto a still-draining storage"), which advertises a mitigation the implementation
  cannot deliver for the storage the warning is about.

The code comment (and `90-heuristic.md`) conflates two different statements: "the cooldown
excludes a storage as a *destination*, never as a source" (correct — it is about how the
cooldown is *enforced* against candidate moves) and "only destinations *get* a cooldown" (not
what §6/§9.3 say). On a saferemove cluster this is the difference between the next run
(15-30 min later, per §2.1's cadence) excluding a storage that will be zeroing a LUN for
44 hours, and planning a move onto it that then fails against the storage-level lock §9.3
warns about. Note also `state.with_recorded_cooldown`'s docstring still says "Not called by
anything today" — stale since `c6760c9`.

**Recommendation:** record timestamps for both endpoints (`from_storage` and `to_storage`);
keep the destination-only *exclusion* semantics in the heuristic/MILP exactly as they are.
Update `28-apply.md`, `15-state.md`, and the two stale docstrings. If the project genuinely
wants destination-only recording, that is a defensible policy — but then §6, §9.3, §11.1 and
the `verify-storages` message must be rewritten to stop promising source protection, in the
same commit (AGENTS.md §7.6).

### 17.6 S-04 — the MILP backends ignore `cooldown_storages`

**Severity:** Medium
**Files:** `src/proxmox_storage_drs/optimize.py:48-65, 210-215`, `schedule.py:44-46`

`solve()` accepts `cooldown_storages` "for interface symmetry" and logs a warning when it is
non-empty, but neither model excludes those storages as targets. The module docstring
justifies the gap with "Cooldowns are inert today anyway (nothing calls
`state.with_recorded_cooldown()` yet)" — true when phase 6 landed, **false since phase 7**:
`apply` now writes cooldown timestamps (S-03). The stated plan for the hard-fix
(a big-M penalty or per-solve feasibility check) is a real difficulty, but the consequence
is no longer hypothetical:

- After any `apply` run that executed a move, the next `plan`/`apply` within
  `cooldown_per_storage` — the exact scenario the cooldown exists for — will, whenever
  ortools or pulp is importable, solve with cpsat/cbc (the default `solver.backend: auto`
  cascades to them first) and may assign disks onto the cooling/draining storage. The
  heuristic would not. §5.5's "the heuristic must use the same feasibility and objective
  functions as the MILP path so the two backends are directly comparable" is violated —
  the backends can now return different optima for the same input, which is precisely the
  class of divergence that requirement exists to prevent.
- Nothing downstream catches it: `schedule.py` documents that it schedules "as if no
  cooldown applies", so §8.1's `concurrency_ok` condition 5 is unimplemented there too, and
  the executor's live transient check only guards *capacity*, not the wear/churn and
  storage-lock reasons the cooldown encodes.

**Recommendation:** for stage 2, hard-fix `x_{d,s} = 0` for `s ∈ cooldown_storages` *and*
re-run stage 1 (or verify stage 1's optimum still stands) so the lexicographic invariant is
not invalidated — or, simpler and matching the heuristic's own semantics, filter cooldown
storages out of the *candidate target set* for movable disks in both stages and treat the
current assignment (which never violates its own feasibility) as always available, exactly
as `_descend()` does. Either way, delete the "inert today" sentence: it is now misleading in
the direction that matters.

### 17.7 S-05 — a drained storage is not excluded for the remainder of the run

**Severity:** Medium
**Files:** `src/proxmox_storage_drs/execute.py:488-502`, `docs/internals/92-execute.md:55-73`

§9.3, on a `source_release` timeout: "do not fail the run: mark the storage `draining`,
**exclude it as both source and target for the remainder of the run**, report it". The
implementation does the "mark" (`status="draining"`, reported per-move) and the "do not
fail" (draining is treated like moved), but not the exclusion: `execute_plan()` simply
continues to the next move with nothing changed. A subsequent move in the same run whose
source or target is the drained storage proceeds — into the storage-level lock §9.3 says the
wipe holds, i.e. it either queues behind a potentially day-long wipe (the task-status loop
is unbounded) or fails, aborting the run under `abort_on_failure`. The live transient check
only partially protects the target direction (the un-wiped volume still counts in live
`used`), and does nothing for the source direction.

`92-execute.md` presents the draining state as fully handled ("the next run will see the
storage as it actually is") without mentioning that the *current* run keeps going — so this
is not an honestly-documented phase gap like the re-plan protocol, but an unimplemented
sentence of the section the module says it implements.

**Recommendation:** track drained storages in `execute_plan()`; skip (and report as skipped,
with the draining storage named) any later move whose `from_storage` or `to_storage` is in
that set, exactly like a cooldown skip. Cheap, self-contained, and it removes the one way
this run can still shoot itself in the foot after correctly detecting the wipe.

### 17.8 S-06 — pre-flight does not re-check exclusion tags

**Severity:** Low
**Files:** `src/proxmox_storage_drs/execute.py:155-195`, `IMPLEMENTATION_PLAN.md` §9.2 step 3

§9.2 step 3: "confirm the VM is still running **and untagged for exclusion**". `_preflight()`
re-checks existence, node, disk placement, running state, snapshots and lock — but not
`exclude.vmids`/tags/`no-drs`. The `resource` dict it already fetched carries `tags`, and
the config is in scope at the call site, so this is a two-line check. A VM tagged `no-drs`
between planning and execution is moved anyway. Low because the window is minutes and the
operator configured the exclusion at planning time, but §9.2 lists it as one of the five
re-checks and four of the five are implemented.

**Recommendation:** pass the exclusion predicate into `execute_plan()`/`_preflight()` (or
pre-resolve the excluded vmid set) and return `replan_needed` on a tag match, mirroring the
snapshot case.

### 17.9 S-07 — lexicographic stage 1 may stop at the gap, and the backends pin it differently

**Severity:** Low
**Files:** `src/proxmox_storage_drs/optimize.py:456-468` (CP-SAT), `654-672` (CBC)

The whole strength of the lexicographic solve (§5.3 option 1) is that stage 1's minimum is
*proven*, so "Σ r_s > 0 provably means physically impossible". Both implementations
compromise that proof in a different way:

- CP-SAT stage 1 accepts `OPTIMAL` **or** `FEASIBLE`, with `relative_gap_limit = mip_gap`
  (default 0.02). On `FEASIBLE`, `min_slack` is an incumbent, not the minimum — and stage 2
  pins `Σ r_s == min_slack`, which both allows trading up to the gap *and forbids finding
  less slack than the incumbent.
- CBC's `LpStatus == "Optimal"` does not distinguish a proven optimum from a search that
  stopped because `gapRel` was satisfied; its stage 2 uses `<= min_slack + 1e-6` —
  monotone-safe (cannot be worse than the incumbent) but still permits up-to-gap shortfall.

In practice stage 1 is a near-feasibility problem that closes instantly on realistic groups,
so this needs a big group, a positive slack and a slow solve to bite. But the code
structurally accepts the gapped case without distinguishing it, the two backends behave
differently when it happens (another §5.5 comparability dent), and the reported
"unfixable shortfall" could overstate what is physically possible.

**Recommendation:** run stage 1 with the gap forced to 0 (it is the cheap stage), or require
`status1 == OPTIMAL` and fall back to the heuristic otherwise; use `<=` rather than `==` for
stage 2 in both backends so stage 2 can only improve on the stage-1 value.

### 17.10 S-08 — phase-8 knobs documented as functional in the configuration reference

**Severity:** Low
**Files:** `docs/manual/10-configuration.md:656-697`, `28-apply.md`, `30-safety-and-status.md`

`execution.max_concurrent_migrations`, `max_migrations_per_run`,
`max_concurrent_per_storage` and `max_replans_per_run` each have a full configuration-reference
entry describing behaviour ("How many moves may be in flight...", "A ceiling on how many
moves one invocation executes...", "Caps concurrent moves touching one storage...", "A cap
on how many times one run may abandon its current plan and re-plan") with no hint that none
of it exists yet: the executor is strictly sequential, has no per-run cap, and never
re-plans. `28-apply.md` and the `30-safety-and-status.md` table *are* honest ("Its own
safety rails ... are phase 8"; "re-invoking the whole pipeline automatically ... is not
implemented yet") — but the reference page is where an operator looks a knob up, and it is
the exact P-01/P-02 pattern this review has twice established as a finding: a knob
documented as doing something the code does not do. The cross-reference tests only check
existence, not effect.

**Recommendation:** add the one-line "not yet effective in this build; the executor is
strictly sequential / re-planning is not implemented" caveat to each of the four entries in
`10-configuration.md` (and remove the caveat when phase 8 lands, in the same commit as the
behaviour).

### 17.11 S-09 — §5.5's model-build-time assertions are neither implemented nor removed

**Severity:** Low
**Files:** `src/proxmox_storage_drs/optimize.py:69-78`, `IMPLEMENTATION_PLAN.md` §5.5

§5.5: "Assert at model-build time that every coefficient is a non-zero integer wherever its
unscaled weight is non-zero — the regression test for the γ trap above — and that the
maximum objective magnitude is below 2⁶²." The code has neither assertion, and the plan was
not updated. The module docstring rebuts only the *other* assertion of that paragraph (the
post-solve floating-point agreement check, arguing `evaluate_assignment()` is a sharper
version — a fair argument). It does not address the build-time pair. Notably, the code's
`if gamma_scaled: terms.append(...)` pattern *silently drops* a zero coefficient — the exact
failure shape the demanded assertion exists to catch; it is unreachable at the default
weights after per-disk folding (a coefficient rounds to zero only for a sub-kilobyte disk),
but the plan's text is a requirement, and "practically can't happen" is what assertions are
for. Per AGENTS.md §7.6, either implement them or fix the plan in the same commit.

**Recommendation:** a three-line guard in `_cpsat_objective_terms` (raise/log when a
computed coefficient rounds to zero under a non-zero weight, and when any term's maximum
magnitude exceeds 2⁶²) costs nothing and turns §5.5's regression test back into code.
Alternatively, rewrite §5.5's sentence to delegate the guarantee to the shared
`evaluate_assignment()` recomputation — but then say so in the plan.

### 17.12 What this pass confirms

- **state.py's locking is genuinely well designed.** `flock()` on the file itself as the
  mechanism, the in-JSON `lock` field demoted to descriptive metadata (which dissolves the
  stale-lock-recovery question rather than answering it), and — the subtle one —
  `_write_state_to_locked_fd()`'s discovery that `save_state_atomic()`'s rename would
  *replace the inode the lock was taken on*, documented with the test that caught it
  (`test_a_second_acquire_while_the_first_is_held_returns_none`). Reads correctly skip
  locking because atomic writes make torn reads impossible. Read-degrades/write-raises is a
  coherent policy and consistently applied.
- **The cooldown wiring follows the plan's structure**: disk cooldowns as a (C2) pin in
  `topology.py` (reported with a human reason, in the plan's own priority order), storage
  cooldowns as a target exclusion in the heuristic, cooldown `<= 0` meaning "disabled"
  rather than "always cooling". The `_repair()`-ignores-cooldowns choice is a documented,
  defensible extension of the reserve-override principle.
- **optimize.py's model is a faithful transcription of §5.3-§5.5**: (C1)-(C6) all present,
  including the `affinity_counts_pinned_disks` variants of (C3) with the `y==1` forcing for
  pinned-of-VM disks; pinned disks counted in `Σ z·x`, `Z_s` and (C5) exactly as §3.6
  demands; warm start from the current assignment; the γ coefficient folded per-disk
  (`round(γ·W·K·z_d^TiB)`, the N-01 fix) rather than factored; `a_{d,s} = round(K·ℓ_d/c_s)`
  folding; the reserve factor's own fixed-point scale — a wrinkle the plan did not name and
  the implementation had to invent, correctly.
- **The shared-objective architecture pays off**: both MILP backends hand their assignment
  to `heuristic.evaluate_assignment()` for the reported numbers, so a modelling mistake can
  choose a worse plan but cannot mis-report one — and the fixture cross-checks (which pass
  on pulp 3.3.2, 17.1) are exactly the sharper guard the docstring claims.
- **execute.py's completion criterion, lock waiting and orphan handling match §9.3**: three
  conditions, open-ended lock set never whitelisted, orphans reported never deleted, the
  KiB/s conversion at the one call site, pre-flight re-fetches genuinely bypassing all
  caching (PveClient has none). The injectable `Clock` lets every wait loop's timeout
  arithmetic be tested without real sleeps, and the 30 execute tests use it.
- **`apply`'s state bookkeeping is right**: lock-first quiet-exit-0, `last_balance`/
  cooldowns written only after executed moves, `--mode auto` refused outright rather than
  run without its rails, `dry-run` issuing zero API calls (tested).

### 17.13 Assessment

The state, cooldown and executor work is careful and the MILP model itself is correct —
proven against both fixtures once the right pulp is present. But this is the first pass
whose findings include defects that make the tool *crash* or *act against its own safety
rules* rather than merely omit a feature: S-01 breaks the primary packaged solver path on
the target platform (and CI's own trixie job cannot be green with it in), and S-02 executes
plans §7.3 explicitly rejects — with the hard per-move duration rule, the one §7.3 calls an
operational limit rather than an economic one, as the sharpest instance. S-03/S-04/S-05 all
weaken the same protection from different directions: the cooldown/draining machinery that
§9.3 exists to keep a wiping storage out of trouble has, as implemented, a write-side gap
(S-03), a solver-side gap (S-04) and an executor-side gap (S-05). Fixing S-01 and S-02
should precede any further feature work; S-03..S-05 belong in the same fix series, since
each is small and they compose into one story — "a storage that is draining must be left
alone" — that the plan states three times and the implementation currently honours zero
times end to end.

---

## 18. Resolution of tenth-pass findings (S-01..S-09)

All nine findings were real; all nine are fixed, not refuted.

| ID | Status | How resolved |
|----|--------|--------------|
| S-01 | Resolved | Every MILP variable in both backends is now built via a new `_lp_variable()` helper wrapping `pulp.LpVariable(...)` directly (not `prob.add_variable(...)`, PuLP v4's replacement, absent before pulp 3.3.1), with the resulting v4-migration `DeprecationWarning` suppressed explicitly via `warnings.catch_warnings()` rather than adopting an API the packaged trixie version (`python3-pulp` 2.7.0) cannot provide. `_pulp_solve()` also wraps `prob.solve()` in `except pulp.PulpSolverError → None`, so a `python3-pulp` install without `coinor-cbc` degrades the same way an unimportable library does, never a bare traceback. Reproduced and verified against a throwaway venv pinned to pulp 2.7.0 (the exact version `rmadison`/CI's `debian:trixie` container installs): all CBC `test_optimize.py` cases pass; also re-verified against pulp 3.3.2 to confirm no regression there. `docs/internals/91-optimize.md` and the module docstring updated; the `pulp>=2.7` extra constraint is unchanged (now actually true, not merely declared). |
| S-02 | Resolved | New `cli._apply_payback_gate()`: a move in `payback_result.rejected_moves` (the hard per-move duration rule) is dropped from the order and reported `"skipped"` ("refused: exceeds migration.max_single_move_duration...") without ever reaching `execute_plan()`; when `not payback_result.aggregate_ok`, the *whole* group's remaining plan is refused the same way and `execute_plan()` is never called at all, issuing zero API calls, same as `dry-run`. `_handle_apply()` also prints the group's payback lines once, before the first `confirm` prompt, not only in the post-run report. `_render_group_plan_human()`'s move-line lookup switched from positional indexing to a `disk_key`-keyed dict, since a refusal can make `ExecutionResult.outcomes` a reordered subset of `schedule_result.order`. Six new `test_cli.py` cases cover: an individually-rejected move refused with `execute_plan` monkeypatched to raise on any call; a plan failing the aggregate test refused the same way; the payback preview appearing before the first prompt. |
| S-03 | Resolved | `_handle_apply()` now records a `gates.cooldown_per_storage` timestamp for **both** of an executed move's storages, source and destination — section 6's "involved in a migration" covers both, and section 9.3's sizing rule is specifically about protecting a still-draining *source*. `heuristic.py`'s own *enforcement* is untouched (destination-only exclusion, per `docs/internals/90-heuristic.md`) — this was a recording gap, not an enforcement one. `state.with_recorded_cooldown()`'s stale "not called by anything today" docstring, and the equivalent claims in `docs/manual/28-apply.md`/`docs/internals/92-execute.md`, are corrected. `test_apply_records_balance_and_cooldowns_after_an_executed_move` now asserts both storages get a cooldown, not just the destination. |
| S-04 | Resolved | Both `_cpsat_feasibility_constraints()` and `_cbc_feasibility_constraints()` now take `cooldown_storages` and add `x_{d,s} = 0` for every movable disk `d` and cooldown storage `s` that is not `d`'s current storage — applied identically in both lexicographic stages, matching `heuristic._descend()`'s own destination-only exclusion. `solve()`'s "not enforced yet" warning is removed; the module docstring's bullet is rewritten to describe what *is* now enforced and the one thing deliberately not replicated (`_repair()`'s reserve-override exemption from the same cooldown — a narrower, documented gap, not the original all-or-nothing one). New tests mirror `test_heuristic.py`'s own cooldown pair exactly (`test_solve_excludes_a_cooldown_storage_as_a_target_for_a_movable_disk`, `test_solve_still_allows_a_disk_to_move_away_from_a_cooldown_storage`), parametrized over both backends and verified against real `ortools`/pulp 2.7.0 installs. |
| S-05 | Resolved | `execute_plan()` now tracks a `drained_storages` set, adding a move's `from_storage` whenever its outcome is `"draining"`; `_drained_skip_outcome()` (factored out to stay within the flake8 complexity limit) skips — with zero API calls — any later move in the same run whose source or target is in that set, reporting it plainly rather than letting it queue behind or fail against the storage-level lock section 9.3 describes. Two new tests construct a two-move run where the first move drains a storage and assert the second (as source, then as target) is skipped without a single additional API call. |
| S-06 | Resolved | `_preflight()` takes a new `exclude: ExcludeConfig` parameter and re-checks `exclude.vmids`/`exclude.tags` via a new `_is_excluded_by_tag_or_vmid()` (a small duplicate of `topology.py`'s own private predicate, matching this codebase's established preference over reaching into another module's private name) — a VM tagged for exclusion (or added to `exclude.vmids`) between planning and execution now stops that move with `replan_needed` instead of moving it anyway. `execute_plan()`/`cli._apply_payback_gate()` thread the parameter through; two new tests cover the tag and vmid cases. |
| S-07 | Resolved | Stage 1 in both backends now forces its own solver gap to exactly `0` regardless of the configured `solver.mip_gap` (which now applies only to stage 2's real objective) — CP-SAT's stage 1 requires `status1 == OPTIMAL` (never accepts `FEASIBLE`), and CBC's stage 1 uses a separate `pulp.COIN_CMD(gapRel=0.0)`, since PuLP's own `LpStatus` string cannot otherwise distinguish a proven optimum from a search that merely satisfied `gapRel`. Stage 2's slack-pinning constraint changed from `==` to `<=` in both backends — monotone-safe, and equivalent to `==` now that stage 1 is exact. New test `test_stage_one_reserve_floor_ignores_a_generous_mip_gap` calls `solve()` directly (bypassing the test helper's hardcoded `mip_gap=0.0`) with `mip_gap=0.5` against the `reserve-tradeoff` fixture and asserts neither backend trades the reserve floor away; verified against real `ortools`/pulp 2.7.0. |
| S-08 | Resolved | Added a one-line "**Not yet effective in this build**" caveat, naming the phase-8 dependency and cross-referencing `docs/manual/30-safety-and-status.md`, to each of `execution.max_concurrent_migrations`, `max_migrations_per_run`, `max_concurrent_per_storage` and `max_replans_per_run` in `docs/manual/10-configuration.md`. |
| S-09 | Resolved | `_cpsat_objective_terms()` now calls two new assertions: `_assert_nonzero_when_weighted()` (raises if a non-zero configured weight's rounded, scaled coefficient collapsed to `0` — the exact γ-trap shape the `if gamma_scaled:` guard would otherwise silently absorb) for `beta_scaled`, `kappa_scaled`, `alpha_scaled` and every disk's `gamma_scaled`; and `_assert_objective_magnitude_within_int64()` (a coarse, deliberately conservative worst-case sum of every term, asserted below `2**62`, an order of magnitude under CP-SAT's own `2**63-1` domain). Both are CP-SAT-only, matching that this is specifically an integer-coefficient-discipline guard CBC's continuous model has no analogous need for. New direct unit tests for both helpers plus an end-to-end `test_gamma_trap_assertion_fires_end_to_end_for_a_sub_kilobyte_disk` (a synthetic 1.1×10⁻¹⁰ TiB disk, verified to actually trip the guard against a real `ortools` install), and the module docstring's bullet on the plan's assertion paragraph now names both as implemented rather than only rebutting the post-solve one. |

Verification: dev venv `python3 -m pytest` — 435 passed, 24 skipped (ortools/pulp/statsmodels
absent), 89.57% coverage. Every backend-parametrized new/changed test independently re-run
against a throwaway venv pinned to pulp **2.7.0** (the exact Debian trixie/CI version S-01's
own finding was about) and again against a separate venv with `ortools` installed (no working
CP-SAT venv existed from the ninth-pass review) — all pass under both, not merely under the
pip-resolved newer pulp the ninth-pass verification used. `make check` clean (fmt, lint,
typecheck, test, fixtures, docs-check — internals PDF rebuilt to 35 pages, manual PDF to 32).

---

## 19. Eleventh-pass review — phases 8-9, crash recovery, concurrency, saturation guard

Reviewed commit range `d5307f7..HEAD` (the S-01..S-09 fixes themselves are already recorded in
section 18): `c01c0d7` (auto mode, phase 8: time windows, migration cap, re-plan loop), `6f54308`
(auto-mode self-review: lock-wait deadline gap, DST), `76f0d2c` (section 13 crash and
two-instance recovery, new `crashrecovery.py`), `026e9d9` (section 8.1's generalized transient
invariant extracted into `reserve.transient_charge_ok()`), `a59c613` (concurrent execution),
`0447940` (per-disk load time series in `loadmodel.py`), `d94807a` (section 7.3's
saturation-ceiling defer check in `payback.py`), `10a9ead` (wiring the guard into
`plan`/`apply`), `f2c572e` (phase 9: the section 10.2 forecast backtest gate). Roughly 5,900
inserted lines across 38 files (~2,700 of them tests), two new modules (`timewindow.py`,
`crashrecovery.py`), and one new internals page. `IMPLEMENTATION_PLAN.md` itself is unchanged
across the entire range.

This is the pass that makes the tool an unattended one, and the engineering quality of the
individual mechanisms continues to be high: the time-window module's local-time-with-IANA-zone
DST handling (including the honest documentation of the fixed-offset fallback's two-nights-a-year
residual gap), the write-the-UPID-before-anything-else crash trace with the finally-block that
deliberately saves the callback's newer state over the loop's older local variable, the shared
`transient_charge_ok()` that makes the sequential and concurrent executors provably check the
same arithmetic, the non-blocking `_poll_move_once()`/`_LaunchDecision` decomposition of the
executor, and the `accepted`-vs-`deferred_moves` split in the payback verdict are all better
than the plan strictly demands. The three Medium findings are all at the seams between the new
mechanisms rather than inside any one of them.

### 19.1 Verification run

- Dev venv `python3 -m pytest`: **558 passed, 24 skipped** (ortools, pulp and statsmodels absent
  from the venv), **91.28% line coverage** — above the 85% floor, and *up* from the tenth
  pass's 89.57% despite ~2,650 new source lines under test: the new surface is well covered
  per-module (`execute.py` and `cli.py` both at 99% under their own test files;
  `crashrecovery.py` and `timewindow.py` have dedicated files with 19 and 16 tests).
- System Python (pulp **2.7.0**, the exact Debian trixie / CI version): `test_optimize.py`
  20 passed, 12 skipped — the S-01 fix holds on the packaged path. No CP-SAT-capable
  environment was available this pass; the ortools-parametrized cases remain skipped here.
- `tests/fixtures/generate_expected.py --check`: OK. `sha256sum --check` on all three PDF
  stamps (plan, internals, manual): all OK. `black --check`, `flake8`, `mypy`: clean.
- **The concurrent re-plan gap (T-01) was reproduced, not inferred**: a scripted scenario
  driving the real `_execute_concurrent()` (move 201 in flight and slow to resolve, move 202's
  VM vanished from `cluster/resources`) produces `outcomes == [(202, "replan_needed"),
  (201, "moved")]` with `stopped_early=True` — the `replan_needed` outcome is *not* last, so
  `cli.py:1723`'s `outcomes[-1].status == "replan_needed"` check answers False and no re-plan
  happens. The scenario uses only the existing test doubles (`concurrent_client_with` with
  201's task-status poll scripted to stay `"running"` for two cycles and 202 removed from
  `cluster/resources`), so it converts directly into the regression test T-01 asks for.
- Time-window behaviour spot-checked against the test suite's 16 cases (cross-midnight matching
  against the *start* day, DST spring-forward non-crash, `current_deadline()`'s
  "no active window → zero budget" and "no windows at all → unbounded" conventions) — all
  consistent with section 9.1 and the module's own docstrings.
- The §14 fixture arithmetic is untouched by this range (no solver or objective changes);
  fixture freshness re-confirmed above.

### 19.2 Findings summary

| ID | Severity | Module(s) | Summary |
|----|----------|-----------|---------|
| T-01 | Medium | `cli.py`, `execute.py` | `auto`'s re-plan loop never triggers under the concurrent executor — a launch-time mismatch resolved while another move is in flight is not the *last* outcome, and `outcomes[-1]` is how the loop detects it; the run stops early instead of re-planning (§9.2 step 3), and the manual's auto-mode "re-plan loop" promise silently does not apply under concurrency |
| T-02 | Medium | `cli.py` | §9.2 step 2 ("record the moves already completed in state.json, *including their cooldown timestamps*") is honored only after a group's whole auto loop ends — a re-plan inside the loop plans against the pre-group state, without the earlier attempts' cooldown pins or an updated `last_balance`, so a just-moved disk can be re-proposed (and moved back) within the same invocation; and if a later move raises, the finally-block save persists a state that never got those cooldowns at all |
| T-03 | Medium | `docs/manual/10-configuration.md`, `config/drs.example.yaml`, plan §10.1/§10.2 | The manual and example config claim the *optimizer* consumes `window.upper_quantile` / the forecaster's upper bound; in the finalized code the optimizer consumes the `window.quantile` (p95) decision statistic and only the section 7.3 saturation guard (when `saturation_load` is set) consumes bounds — the P-01/P-02/S-08 pattern again, plus a plan section now contradicted by the code with no annotation |
| T-04 | Low | `execute.py`, `docs/internals/92-execute.md` | Stale "section 7.3's saturation check … is not implemented anywhere in this codebase yet" claims (module docstring, `_execute_concurrent` docstring, `92-execute.md`) — contradicted by the saturation wiring that landed two commits later in this same range and by sibling docs that describe it |
| T-05 | Low | `docs/internals/96-payback.md` | The page still says the payback benefit "takes two `ObjectiveBreakdown.imbalance_term` values … passed straight through" — false since the R-01 fix switched to `raw_spread()`; an implementer following this page would reintroduce the R-01 bug |
| T-06 | Low | `execute.py`, `cli.py` | Three divergent semantics for the `max_migrations_per_run` counter: the sequential executor counts lock-timeout and post-lock-wait-deadline *skips* (moves never issued), the concurrent executor counts launches only, and `_run_auto_group`'s cross-group decrement counts moved/draining/failed — the cap is never exceeded, only under-consumed, but the one-rule discipline is broken; collateral: the post-lock-wait deadline skip continues the loop instead of stopping the run, contradicting `_auto_budget_stop_outcome`'s own documented "stop cleanly, never skip this one" policy |
| T-07 | Info | `cli.py` | `_plan_group()` computes `_saturation_forecast_inputs()` (six `query_range` calls over up to 7 days at 5-minute step) even when `schedule_result.order` is empty (full deadlock) — the guard's outputs are then unused; performance note only |

### 19.3 T-01 — the re-plan loop does not trigger under concurrent execution

**Severity:** Medium
**Files:** `src/proxmox_storage_drs/cli.py:1723`, `src/proxmox_storage_drs/execute.py:1176-1284`

`_run_auto_group()` decides whether to re-plan with:

```python
needs_replan = bool(result.outcomes) and result.outcomes[-1].status == "replan_needed"
```

This is correct for the sequential executor, where a `replan_needed` outcome always ends
`execute_plan()` immediately and is therefore last. The concurrent executor cannot return
early: once a stop condition is set it keeps polling the still-in-flight moves to their natural
conclusion (by design, and correctly — their outcomes and crash-recovery callbacks must still
be recorded), and those resolutions are appended to `outcomes` *after* the `replan_needed`
outcome that `_advance_pending()` recorded mid-run. Reproduced against the real executor
(19.1): outcomes arrive as `[(202, "replan_needed"), (201, "moved")]`, `outcomes[-1]` is the
`moved`, and the loop breaks without re-planning.

Consequences: under `execution.max_concurrent_migrations > 1` — the exact configuration the
concurrent executor exists for — a normal mid-run mismatch stops the run instead of triggering
section 9.2 step 3's "re-invoke the whole pipeline from the new observed state". The behavior
is conservative (nothing unsafe executes; the next timer invocation re-plans from reality), but
it contradicts the plan, diverges from the sequential path, and silently narrows the manual's
own auto-mode contract (`docs/manual/28-apply.md`'s "The re-plan loop" bullet promises the
re-plan for `auto` with no concurrency qualifier). The suite cannot see it: every re-plan test
stubs `_apply_payback_gate` with a single `replan_needed` outcome, and every concurrent
executor test that produces `replan_needed` has nothing else in flight (`test_concurrent_preflight_mismatch_replans_and_stops`).

**Recommendation:** decide re-planning on membership, not position — `any(o.status ==
"replan_needed" for o in result.outcomes)` over the per-attempt result (safe: `"replan_needed"`
is only ever produced at launch time, never by polling, so this cannot fire spuriously) — and
add a regression test that drives the real `_execute_concurrent()` with one move in flight
while the head of pending fails pre-flight.

### 19.4 T-02 — executed moves' cooldowns are not recorded where section 9.2 step 2 needs them

**Severity:** Medium
**Files:** `src/proxmox_storage_drs/cli.py:1630-1767` (`_run_auto_group`), `cli.py:1770-1822`
(`_record_executed_moves`), `IMPLEMENTATION_PLAN.md` §9.2 step 2

Section 9.2's re-plan protocol is explicit that recording precedes re-invoking: "Record the
moves already completed in `state.json` (including their cooldown timestamps) so the next pass
sees them as history rather than re-deriving them" (step 2), *then* "re-invoke the whole
pipeline" (step 3). The implementation records `last_balance` and per-disk/per-storage
cooldowns only in `_handle_apply()`'s loop, after `_run_auto_group()` has returned for the
whole group. Two consequences:

1. **The re-plan plans against stale state.** The loop's re-plan passes the `state` snapshot
   from *before the group started* to `build_topology(state=...)` (the (C2) per-disk cooldown
   pin) and `_plan_group(..., state, ...)` (`active_storage_cooldowns`, and the drift gate's
   `last_balance`). A move executed in attempt 1 has no cooldown recorded when attempt 2
   solves, so nothing structurally prevents attempt 2 from proposing the same disk again —
   including back to where it came from — which is precisely the churn `cooldown_per_disk`
   exists to prevent. It also means the re-plan's drift gate compares against a baseline that
   predates the moves this run already executed. The load-model/topology re-fetch limits the
   damage (the disk's new location is real, and the gate often concludes "no action"), but the
   protection the plan mandates for exactly this loop is absent.
2. **The crash window loses them entirely.** If a later move in the same group raises (a
   network failure mid-poll, say), the `finally` block saves `state_box.value` — which carries
   the live `inflight_upids` updates (by design) but none of the executed moves' cooldowns or
   `last_balance`, since `_record_executed_moves` was never reached. The next run then starts
   with no cooldown for disks that really moved, and no drift baseline. The UPID trace is
   cleared for tasks that finished, so nothing else marks those moves as recent history.

**Recommendation:** record per *attempt*, not per group: call `_record_executed_moves` (or a
subset of it, keyed on the attempt's own outcomes and load vector — the docstring already
notes which statuses count) inside `_run_auto_group()` after each `_apply_payback_gate()` call,
pushing the result into `state_box`/`state` before the re-plan re-invokes the pipeline; and
for the crash window, record after each *resolved* outcome (or at minimum wrap the per-group
call so an exception still records what completed before propagating). Either way the
`finally`-block comment's own reasoning — never clobber the newest state — extends naturally:
what is saved should also be the newest *cooldown* state, not just the newest inflight state.

### 19.5 T-03 — "the optimizer consumes the upper bound": manual and config say yes, code says no

**Severity:** Medium
**Files:** `docs/manual/10-configuration.md` (`window.upper_quantile`, `forecast.holt_winters.residual_z`),
`config/drs.example.yaml:86`, `IMPLEMENTATION_PLAN.md` §10.1/§10.2, `src/proxmox_storage_drs/loadmodel.py:113`

The finalized implementation has exactly one consumer of a `Forecaster`: the section 7.3
saturation guard (`cli._saturation_forecast_inputs()` → `forecast.storage_upper_bound()` →
`payback.compute_move_cost()`), and only when some storage in the group configures
`saturation_load`. The decision statistic that drives gates, solver, payback and ordering is
`compute_group_load()`'s PromQL `quantile_over_time` at `window.quantile` (p95, the point
estimate) — `loadmodel.py:113-114`. `docs/internals/20-forecasting.md` says so honestly:
"the optimizer does not consume a forecast at all yet."

The operator-facing documentation does not:

- `window.upper_quantile`: "The quantile the **optimizer** and the saturation guard actually
  consume" — the first half is false.
- `forecast.holt_winters.residual_z`: "this is what the optimizer actually consumes".
- `config/drs.example.yaml:86`: "the bound the OPTIMIZER consumes (>= quantile)".

This is the P-01/P-02/S-08 pattern a fourth time: a knob documented as feeding a consumer it
does not feed. An operator who raises `upper_quantile` (or tunes `residual_z`) expecting a more
conservative *placement* gets no change in placement at all unless they also set
`saturation_load`. Additionally, the plan's own §10.1 sentence — "The optimizer consumes the
**upper bound**, never the point estimate … so the optimizer sees p99" — and §10.2's "Refuse to
let a model whose backtest error exceeds the imbalance threshold **drive migrations**" are now
unconditionally contradicted by the finalized code, with no plan-side annotation (AGENTS.md
§7.6: resolve the disagreement in the same commit; `IMPLEMENTATION_PLAN.md` was not touched
once in this entire range).

**Recommendation:** either (a) fix the three operator-facing claims to name the only real
consumer ("the section 7.3 saturation guard, when `saturation_load` is set"), and add the
plan-side annotation ("as built, the decision statistic is `window.quantile`; the bound is
consumed by the saturation guard only — wiring forecasts into the optimizer remains future
work"), or (b) actually wire the bound into the decision statistic (fetch at
`window.upper_quantile`) if that was always the intent. (a) is the smaller, honest fix; (b)
changes every fixture cross-check and should not be done silently. The documentation
cross-reference tests only check knob *existence*, which is why this survived them.

### 19.6 T-04 — stale "saturation check not implemented anywhere" claims

**Severity:** Low
**Files:** `src/proxmox_storage_drs/execute.py:37-38`, `execute.py:1325-1329`,
`docs/internals/92-execute.md:169-171`, `docs/manual/28-apply.md` ("Concurrent execution")

`execute.py`'s module docstring and `_execute_concurrent()`'s docstring say section 7.3's
saturation check "is not enforced anywhere in this codebase yet", and `92-execute.md` repeats
"**It is not implemented anywhere in this codebase yet** (`docs/internals/96-payback.md`)".
All three were written in the concurrent-execution commit (`a59c613`) and were true then; the
saturation wiring landed two commits later (`d94807a`/`10a9ead`, same review range) and they
were never revisited — `10a9ead` does not touch `execute.py`. They now contradict
`96-payback.md`'s own saturation section and `30-safety-and-status.md`'s `plan` row ("including
the section 7.3 saturation-ceiling guard (mirroring phase only)"), so the documentation set
disagrees with itself. `28-apply.md`'s "Section 7.3's saturation check is not enforced under
concurrency any more than it is under the sequential executor" is misleading the same way: the
planning-time defer check gates `apply` in both paths (`_apply_payback_gate` excludes
`deferred_moves`). What remains true is the narrower statement — there is no *execution-time*
saturation re-check summing `ω_role` over the in-flight set (§8.1 condition 4), and no
draining-phase check.

**Recommendation:** reword the three claims to the narrow true statement ("the planning-time
defer check exists (`96-payback.md`); no execution-time re-check against the live in-flight
set, mirroring or draining phase, under either executor"). This is R-04's pattern — a doc
sentence whose truth ended mid-range — and the same-commit rule applies.

### 19.7 T-05 — `96-payback.md` would reintroduce the R-01 bug

**Severity:** Low
**Files:** `docs/internals/96-payback.md:13-17`

The page opens: "`compute_benefit_load_seconds()` takes two
`heuristic.ObjectiveBreakdown.imbalance_term` values — the pre-plan and post-plan `E` — and
multiplies their difference by `migration.payback_horizon_seconds`; `heuristic.HeuristicResult`
already carries both … so `cli.py`'s `plan` handler passes them straight through." Since the
R-01 fix (ninth pass, `de7deda`), none of that is true: the handler passes
`heuristic.raw_spread()` values, precisely because `imbalance_term` is `alpha_spread`-scaled
and made the payback ratio depend on a solver tuning knob. The paragraph dates from the phase-5
commit (`f0f955d`) and the R-01 fix updated the docstring and this review but not this page. An
implementer who reads `docs/internals/` (as AGENTS.md §8.2 tells them to) and trusts it over
the docstring would wire `imbalance_term` back in — reintroducing a resolved finding with a
`alpha_spread ≠ 1.0` plan silently getting wrong payback arithmetic.

**Recommendation:** rewrite the paragraph to name `raw_spread()` as the required input and
`imbalance_term` as the wrong one (mirroring `compute_benefit_load_seconds()`'s own
already-correct docstring).

### 19.8 T-06 — three semantics for one cap

**Severity:** Low
**Files:** `src/proxmox_storage_drs/execute.py:894` (sequential), `execute.py:1276`
(concurrent), `src/proxmox_storage_drs/cli.py:1719-1721` (cross-group budget)

`execution.max_migrations_per_run` is enforced by three counters that count different things:

- the sequential executor increments `migrations_used` after **every** `_execute_one_move()`
  outcome — including a lock-timeout `"skipped"` (`locks.on_timeout: skip`) and the
  post-lock-wait deadline `"skipped"`, neither of which issued a `move_disk`;
- the concurrent executor increments only on an actual **launch**;
- `_run_auto_group()` decrements the cross-group budget by outcomes with status
  `moved`/`draining`/`failed` — excluding exactly those skips.

The cap can therefore only ever be under-consumed (the sequential path stops earlier than
configured when lock-timeout skips occur), never exceeded, so this is not a safety issue — but
it is three implementations of one rule where AGENTS.md §5 asks for one, and the sequential and
concurrent executors give different answers to "did that skipped move consume budget?".
Collateral detail: the post-lock-wait deadline skip *continues* the loop (the next iteration's
budget check then stops the run), which contradicts `_auto_budget_stop_outcome()`'s own
documented policy that both budgets mean "stop cleanly, never skip this one and try a later
move" — the run ends one outcome and one skipped line later than that policy describes, having
also consumed one unit of the sequential counter for a move that never launched.

**Recommendation:** pick one semantics — launches only (matching the concurrent path and the
plan's own "how many moves one invocation *executes*") is the natural choice: increment only
for outcomes that actually issued a `move_disk`, in both executors, and have the cross-group
decrement match. Then the post-lock-wait deadline skip can stop the run directly instead of
falling through to the next iteration, matching the documented policy.

### 19.9 T-07 — saturation history fetched for a plan with nothing to check (Info)

`_plan_group()` calls `_saturation_forecast_inputs()` unconditionally after ordering
(`cli.py:1302`), before knowing whether `schedule_result.order` is empty. A fully-deadlocked
plan (order empty, `deadlocked` non-empty) still pays six `query_range` calls over the
configured forecaster's `required_range()` — up to 7 days at a 5-minute step for
`seasonal_naive` — for a guard whose inputs are then unused. Cheap fix if ever worth it: fetch
lazily only when `order` is non-empty. Recorded for completeness; no correctness impact.

### 19.10 What this pass confirms

- **The time-window module is right, including its hard parts.** Cross-midnight windows match
  the day the window *started* on; `current_deadline()`'s three-state convention (no windows →
  unbounded, none active → zero budget, several active → latest close) is exactly what an
  executor needs to refuse work without a second activeness check; local-vs-UTC is a
  deliberate, documented choice; and `_real_local_now()`'s `/etc/localtime` IANA-zone
  resolution closes the DST hole a bare `astimezone()` would leave in `window_close()`'s
  "closes tomorrow" case, with the residual fixed-offset fallback gap documented rather than
  hidden. `start == end` is rejected at config validation.
- **The crash trace is genuinely written before the crash can happen.** `on_inflight_started`
  persists through the still-held `flock` immediately after `move_disk()` returns and before
  any other use of the UPID; `on_inflight_finished` fires when the *task* resolves (including
  `draining`, correctly — the drain is tracked by the content poll, not the UPID); a raise
  mid-wait deliberately leaves the UPID recorded; and the `finally` block saves the box's
  newer state over the loop's older local variable so the trace cannot be clobbered. The
  startup scan's local half re-checks remembered UPIDs (a failed check assumes still-running,
  the safe direction), the cluster half scans `/cluster/tasks` for same-user `qmmove` tasks
  with the confirmed-live field convention, discovered vmids fold into `exclude.vmids` reusing
  the existing (C2) pin, and nothing is ever force-cancelled.
- **The generalized transient invariant is the one arithmetic core the plan asked for.**
  `reserve.transient_charge_ok()` implements `used + Σz_m + f·max(Z, max z_m) ≤ C` with the
  `min_free_bytes` floor (F-02) folded in; `schedule.transient_invariant_ok()` calls it with
  one charge, the sequential executor's live check with one charge against a live
  `storage_status()` read, and `_launch_decision()` with the whole in-flight target-charge set
  plus `largest_by_storage` updated by `_post_move_bookkeeping` — deliberately conservative
  about whether a live `used` already reflects an in-flight allocation.
- **The concurrent executor's decomposition is sound.** Strict FIFO (documented as
  under-delivering on throughput, never unsafe), non-blocking per-move polling via
  `_poll_move_once()` (the shared three-condition completion criterion), the two-condition
  stop-then-drain loop that never abandons an in-flight move, per-storage caps counting both
  endpoints, the deadline re-checked every cycle (so the sequential path's post-lock-wait
  re-check has a concurrent equivalent by construction), and the spin-guard break condition
  once `stop_reason` is set.
- **The saturation guard and backtest gate are honest about their own scope.** The defer check
  is per-endpoint, skipped where `saturation_load` is unset, charged with the same
  `ω_src`/`ω_dst` the cost model already uses, reported separately from hard rejections, and
  excluded from execution exactly like them; a reserve-resolving plan stays exempt from the
  economic test but not from the hard rules (documented in `30-safety-and-status.md`); the
  backtest gate never validates `quantile`, treats missing history as failure, falls back
  with one warning, and reuses `gates.imbalance_threshold` per the plan's own yardstick.
- **The S-02 payback gate survives the new modes intact**: `deferred_moves` join
  `rejected_moves` in `_refused_move_outcomes`, the aggregate failure still refuses the whole
  group with zero API calls, and the confirm-mode payback preview still prints before the
  first prompt.
- **Documentation discipline mostly held**: the S-08 "not yet effective" caveats were properly
  *removed* from the four phase-8 knobs now that phase 8 is real, `28-apply.md` documents FIFO
  concurrency and the drain-first behavior accurately, `15-state.md` was updated for the now-
  live `inflight_upids`, and `95-schedule.md` was rewritten rather than left claiming the
  generalized invariant was unimplemented. The exceptions are T-04/T-05 — both staleness
  introduced or left behind inside this same range.

### 19.11 Assessment

The finalized implementation is, mechanism for mechanism, the best-reviewed state of this
codebase: every phase of the plan now exists, the two High-severity classes of the tenth pass
(crash-the-packaged-solver, execute-what-was-rejected) stayed fixed, and the new unattended
machinery carries its own tests (123 new ones across the range: 459 → 582 total) and
mostly-current documentation. The three Medium findings are all composition bugs at the seams the plan
explicitly legislates — the re-plan protocol (T-01, T-02) and the forecast-consumption
contract (T-03) — and none of them makes the tool do something unsafe: T-01 and T-02 err
conservative (less work, possible churn within a run), T-03 is a documentation lie rather than
a behavior change. Fixing T-01 is a one-line predicate plus a regression test; T-02 is a
recording-point move; T-03 is three sentence-level corrections plus a plan annotation. After
those, the remaining open items in the codebase are the deliberately documented gaps
(execution-time saturation sums, §7.3's re-solve loop, staging, concurrency-aware ordering),
each of which the internals pages already name honestly.

---

## 20. Resolution of eleventh-pass findings (T-01..T-07)

All seven findings were real; all seven are fixed, not refuted.

| ID | Status | How resolved |
|----|--------|--------------|
| T-01 | Resolved | `cli._run_auto_group()`'s `needs_replan` now checks `any(o.status == "replan_needed" for o in result.outcomes)` instead of `outcomes[-1].status` — safe because `"replan_needed"` is only ever produced at launch time, never by polling an already-in-flight move to its own conclusion, so this cannot fire for an outcome that was actually a clean completion. New regression test `test_concurrent_replan_mismatch_can_land_before_a_still_inflight_moves_outcome` (`test_execute.py`) reproduces the exact scenario the review found against the real `_execute_concurrent()` (a slow-to-resolve in-flight move plus a vanished-VM mismatch behind it), and `test_run_auto_group_replans_when_the_mismatch_is_not_the_last_outcome` (`test_cli.py`) pins the fixed predicate itself. |
| T-02 | Resolved | `_run_auto_group()` now threads the caller's `_InflightStateBox` (renamed parameter, `state` → `state_box`) instead of a plain `State`, and calls `_record_executed_moves()` on `state_box.value` immediately after each attempt's own `_apply_payback_gate()` call — using that attempt's own `group_plan.group_load` reading, already computed, no extra fetch — *before* a re-plan's `build_topology()`/`_plan_group()` calls, which now read `state_box.value` rather than the pre-group snapshot. `_handle_apply()`'s own post-loop recording is skipped for `mode == "auto"` (it would otherwise overwrite a later attempt's fresher `last_balance` with the first attempt's stale one) and simply picks up `state_box.value`; the crash-window half is fixed for free, since `_handle_apply()`'s `finally` block already saves `state_box.value`, not the loop's local `state`. New test `test_run_auto_group_records_each_attempts_cooldown_before_replanning` asserts the re-plan's own `build_topology()` call already sees the first attempt's cooldown, and that the box a crash would save reflects it too. |
| T-03 | Resolved | Added an "As built" paragraph to `IMPLEMENTATION_PLAN.md` §10.1 stating plainly that the decision statistic driving gates/solver/payback/ordering is `window.quantile` (the point estimate), that the upper bound's only real consumer is the §7.3 saturation guard, and that wiring the bound into the optimizer's own input remains future work — the §15.1 knob table row updated to match. `docs/manual/10-configuration.md`'s `window.upper_quantile` and `forecast.holt_winters.residual_z` entries, and `config/drs.example.yaml`'s `upper_quantile` comment, rewritten to name the saturation guard as the actual consumer instead of "the optimizer". Chosen over actually wiring the bound into the optimizer (the review's option (b)) because that would change every fixture cross-check and should not be done as a documentation fix. |
| T-04 | Resolved | Reworded all three stale claims (`execute.py`'s module docstring, `_execute_concurrent()`'s own docstring, `docs/internals/92-execute.md`) to the narrower true statement: the §7.3 defer check is enforced at planning time (a flagged move never reaches either executor), and what remains unimplemented is only an *execution-time* re-check of the ceiling against the live in-flight set, mirroring or draining phase, under either executor. `docs/manual/28-apply.md`'s equivalent paragraph corrected the same way. |
| T-05 | Resolved | Rewrote the opening paragraph of `docs/internals/96-payback.md` to name `heuristic.raw_spread()` as `compute_benefit_load_seconds()`'s required input and `ObjectiveBreakdown.imbalance_term` as the wrong one (mirroring the R-01 fix's own already-correct docstring and rationale), replacing the phase-5-era claim that `cli.py` passes `imbalance_term` straight through. |
| T-06 | Resolved | Picked launches-only semantics everywhere, keyed off `MoveOutcome.upid is not None` (only ever set once `move_disk` actually returned one): `_execute_sequential()` now increments `migrations_used` only for a launched outcome, not a lock-timeout or post-lock-wait-deadline skip; `_run_auto_group()`'s cross-group budget decrement switched from `status in ("moved", "draining", "failed")` to `o.upid is not None` for the same reason (a lock-timeout-abort `"failed"` never launched either); the concurrent executor already counted launches only and needed no change. The collateral bug is fixed too: the post-lock-wait deadline skip now sets `always_stop=True` (extending, not narrowing, that field's existing purpose) and `_post_move_bookkeeping()` stops the run on a `"skipped"` outcome with `always_stop` set, matching `_auto_budget_stop_outcome()`'s own documented "stop cleanly, never skip this one" policy. Three new tests: `test_lock_timeout_skip_does_not_consume_the_max_migrations_per_run_budget` (budget untouched by a skip), `test_deadline_recheck_after_a_lock_wait_stops_the_whole_run_not_just_this_move` (a second, fully launchable move is never attempted), plus new assertions on the pre-existing single-move deadline-recheck test. |
| T-07 | Resolved | `_plan_group()` now computes `_saturation_forecast_inputs()` only when `schedule_result.order` is non-empty (`None` otherwise) — a fully deadlocked plan no longer pays the guard's `query_range` fetches (up to 7 days at a 5-minute step) for a result nothing will use. |

Verification: dev venv `python3 -m pytest` — **563 passed, 24 skipped** (ortools, pulp and
statsmodels absent), **91.31% line coverage** (up from the eleventh pass's 91.28% despite the
new regression tests; `execute.py`/`cli.py` both still at 99% under their own test files).
`make check` clean (fmt, lint, typecheck, test, fixtures, docs-check — `IMPLEMENTATION_PLAN.pdf`
rebuilt to 40 pages, internals PDF to 42, manual PDF to 34, all three stamps regenerated in the
same commit as their Markdown per AGENTS.md §7).

---

## 21. Twelfth-pass review — dogfooding fixes, CI repairs, section 11.4 storage patterns

Reviewed commit range `deeae75..HEAD` (the T-01..T-07 fixes themselves are already recorded in
section 20). Seven commits: `bc7df89` (two real bugs found dogfooding against the
`pve.bzed.at` production cluster — the heuristic's missing whole-VM co-relocation candidate,
and the `requests` connection pool being smaller than `read_workers`'s default), then five CI
repairs found the first time the pipelines actually ran (`bfccabb` python3-flake8-bugbear does
not exist in Debian; `22973b2` three tests assumed `solver.backend: auto` resolves to heuristic;
`8921bf7` ca-certificates dropped by `--no-install-recommends`; `f5f8830` mypy needs
python3-typeshed plus a state.py flow-narrowing refactor; `3c1000a` codecov's missing curl/gpg
and its deprecated test-results action), then `1bdb010` — the section 11.4 `/regex/`
storage-pattern feature, the first new plan section added since the implementation was
finished (bc7df89's §5.5 change above amended existing text rather than adding a section).
Roughly 1,200 inserted lines, of which ~500 are tests.

The range's quality bar stays high. The dogfooding fix is the right kind: found on a real
cluster, minimized into a hand-verified regression test whose arithmetic checks out to the
digit, scored exclusively through the shared `evaluate_assignment()` so the new candidate
family cannot regress the objective, with the plan's own §5.5 step 3/4 text updated in the
same commit (the whole-VM candidate documented, polish's remaining scope narrowed to the
N-way rotation). The §14 fixture totals are unaffected (the new family is a strict superset of
what descend could already reach, and the fixture tests still assert 2.533333/3.158333). The
pattern feature's expansion design is clean: expansion happens exactly once, in topology,
against the live cluster; nothing downstream — `D`/`S`, (C2), cooldown keys, `state.json` —
ever sees a pattern; literal-over-pattern precedence is a dict overwrite, so file order cannot
matter; both hard-error cases (zero matches, two patterns claiming one storage) plus the
cross-group collision get the same treatment section 11.1 already gives an unknown literal id;
and the schema change (structural `minItems` 2→1 vs. the semantic ≥2-after-expansion rule
deferred to topology) is a sensible factoring. The five CI repairs each document their root
cause in the workflow header and stay inside the §9.3 "apt, never pip" policy.

### 21.1 Verification run

- Dev venv `python3 -m pytest`: **586 passed, 24 skipped** (ortools, pulp, statsmodels absent),
  **91.65% line coverage** — above the 85% floor and up from the eleventh pass's 91.31%.
- System Python (pulp **2.7.0**, the exact Debian trixie / CI version): **597 passed,
  13 skipped** — the CBC backend exercised for real (the S-01 fix holds), and the `22973b2`
  test pinning means the environment-dependence is gone: with pulp importable, `auto` picks
  cbc and the heuristic-specific tests still pass because they now name their backend.
- `tests/fixtures/generate_expected.py --check`: OK. `sha256sum --check` on all three PDF
  stamps (plan, internals, manual): all OK. `make docs-check` exits 0. `black --check`,
  `flake8`, `mypy`: clean.
- **U-01's failure mode was reproduced, not inferred**: with a fake client carrying `san-z`
  in `GET /storage` definitions but absent from `GET /cluster/resources?type=storage` (the
  shape of a disabled storage), a group written as `/san-.*/` aborts the whole run with
  `TopologyError: storage 'san-z' is not reported active on any node` — a message naming a
  storage the operator never wrote, with no hint that a pattern pulled it in.
- **U-03's asymmetry was reproduced the same way**: the same not-`shared` storage produces
  the "not marked shared" warning when named literally and no warning at all when matched by
  a pattern.
- The new heuristic test's arithmetic hand-verified: initial `E = |1.26−0.63| + |0−0.63| =
  1.26` ✓; one disk moved alone `0.89 + 0.25 + 0.05 + 0.5(κ) = 1.69` — worse, exactly as the
  test asserts ✓; both disks together `0.52 + 0.5 + 0.1 = 1.12`, an improvement of 0.14 ✓
  (matching the docstring's −0.14).

### 21.2 Findings summary

| ID | Severity | Module(s) | Summary |
|----|----------|-----------|---------|
| U-01 | Medium | plan §11.4 vs `topology.py` | The plan says patterns are matched against `GET /cluster/resources?type=storage`; the code matches against `GET /storage` (definitions) — and the untested matched-but-unavailable edge aborts the run with `_pick_active_node`'s generic error, which does not name the pattern that pulled the storage in |
| U-02 | Low | `docs/internals/*.md`, `docs/manual/25-*.md` | Six stale "not yet written"/"remain stubs" claims (`execute.py`, `optimize.py`, `heuristic.py`, `apply`), all false since phases 4-7; one is operator-facing manual text about `last_balance` never being written |
| U-03 | Info | `topology.py`, plan §11.4 | Second, undocumented pattern asymmetry: a matched storage skips the not-`shared` warning a literal entry gets — §11.4 documents only the `images` asymmetry |

### 21.3 U-01 — plan names one endpoint for pattern matching, code matches another; the unmatched edge aborts unhelpfully

**Severity:** Medium
**Files:** `IMPLEMENTATION_PLAN.md` §11.4, `src/proxmox_storage_drs/topology.py:419-449`
(`_fetch_cluster_data`), `topology.py:203-215` (`_pick_active_node`)

Plan §11.4: "Every pattern is matched once per run against the storage inventory
(`GET /cluster/resources?type=storage`, §3.5)". The code matches against
`definitions_by_id`, built from `client.storage_definitions()` = `GET /storage` — storage
*definitions*, which §3.5's own table distinguishes from the *inventory*. The internals doc
(`60-topology.md`) describes the definitions endpoint, so the plan is the outlier; per
AGENTS.md §7.6, one of them is wrong and they should have agreed in the same commit. This is
the T-03 pattern (plan text contradicted by the built code with no annotation) applied to a
mechanism rather than a consumer.

The two sets are not identical: definitions include storages the resource inventory does not
report (a disabled storage still has a definition). That difference has a concrete, reproduced
failure mode (21.1): a pattern that matches such a storage passes expansion cleanly, becomes
a group member, and then dies in `_pick_active_node` with "storage 'san-z' is not reported
active on any node" — an error that names neither the group's pattern nor the fact that a
pattern matched the storage at all. The operator never wrote `san-z`; they wrote `/san-.*/`,
and the one piece of context that would explain the failure is absent. No test covers the
case. It also undercuts §11.4's own framing of over-broad matches ("a pattern that captures
an ISO-only or otherwise unusable LUN skews the balance target even though (C2) keeps any
disk from ever landing there"): for the not-active LUN that story is wrong — the run does not
degrade to a balance-quality concern, it aborts outright.

Two mitigating facts, for fairness: the behavior is fail-safe (hard error, nothing executes),
and a *literal* reference to a disabled storage hits the same wall today, so the crash itself
is pre-existing — what the pattern adds is a new, quieter route into it (you no longer have
to name the storage to pull it in) plus the plan/code text disagreement.

**Recommendation:** (a) fix the plan's §11.4 sentence to name `GET /storage` (definitions) —
which is also what literal-id validation uses, so plan and code then tell one story; (b) add
a test for the matched-but-unavailable storage; (c) make the error name the cause: during
expansion, check each matched id against the resource inventory and raise a pattern-specific
`TopologyError` there ("group 'g1' pattern '/san-.*/' matched storage 'san-z', which no node
reports active — disable-safe patterns must exclude it"), rather than letting
`_pick_active_node`'s storage-only message surface three steps later. Deciding *which* set is
semantically right is the author's call — matching definitions makes `unmanaged_storage_ids`
complete, matching the inventory would exclude disabled storages naturally — but the plan,
the code, and the error message must agree, and the case must be tested either way.

### 21.4 U-02 — six stale "not yet written" claims across the internals and manual

**Severity:** Low
**Files:** `docs/internals/60-topology.md:78,198`, `docs/internals/80-gates.md:65`,
`docs/internals/90-heuristic.md:218,223`, `docs/manual/25-show-load-and-verify-storages.md:62`

A sweep for "not yet written"/"remain stubs" found six claims that later phases falsified and
nobody revisited:

| Location | Claim | False since |
|---|---|---|
| `60-topology.md:78` | "`execute.py`, not yet written" | phase 7 (`c6760c9`) |
| `60-topology.md:198` | "the solver (`optimize.py`/`heuristic.py`, not yet written)" | phase 4 (heuristic) / phase 6 (optimize) |
| `80-gates.md:65` | "`apply` (not yet written)" | phase 7 (`c6760c9`) |
| `90-heuristic.md:218` | "`optimize.py`, not yet written" | phase 6 (`375d3a9`) |
| `90-heuristic.md:223` | "`explain`/`apply` remain stubs" | phase 7 — the `explain` half is still true, the `apply` half is not |
| `25-show-load-and-verify-storages.md:62` | "nothing yet *writes* `last_balance` (that needs `execute.py`, not yet written)" | phase 7, and the T-02 fix now records it per auto-mode attempt |

This is the R-04/T-04/T-05 class at cluster scale: each phase landed without sweeping the
*older* internals pages for claims its own landing invalidated — the per-command status table
(`30-safety-and-status.md`) and the newer pages were kept honest, but the prose in the
foundational pages was not. The manual entry is the worst of the six because it is
operator-facing and asserts something false about state writes ("this stays the common case
until a migration has actually run" is now wrong in both directions: `apply` writes
`last_balance`, and after any executed move the drift gate has real history). The
documentation cross-reference tests check knob existence and CLI-option coverage, not prose
truth — already noted in T-03 — which is how six of these survived three review passes that
each fixed one instance of the same disease.

**Recommendation:** one sweep commit fixing all six, in the same commit-style as T-04/T-05.
Mechanical guard worth considering: a documentation test that greps the docs for module-name
mentions in "not yet written"/"not yet implemented" phrasings and fails when the named module
exists and is wired — cheap, and it turns this whole class from "found by reviewer" into
"found by `make check`".

### 21.5 U-03 — matched storages silently skip the not-`shared` warning (Info)

**Severity:** Info
**Files:** `src/proxmox_storage_drs/topology.py` (`_expand_group`), plan §11.4

`_expand_group`'s "not marked shared" warning lives inside the literal-entry loop only, so a
storage matched by a pattern gets no warning even though the manual and `60-topology.md`
describe the warning as a property of the storage, not of how it was named. Reproduced
(21.1): the same not-`shared` storage warns when written literally, is silent when matched by
`/san-.*/`. §11.4 documents exactly one asymmetry (the `images` content check) and grounds it
in the typo-vs-overreach distinction; the `shared` warning is the same kind of
quality-not-safety signal and almost certainly intends the same treatment, but nothing says
so — an operator reading §11.4's "a matched storage becomes a full member of the group,
exactly as a literal entry" could reasonably expect the warning.

**Recommendation:** one sentence in §11.4's closing paragraph (and `60-topology.md`'s
asymmetry paragraph) extending the documented asymmetry to the not-`shared` warning — or,
simpler and arguably better, emit the warning for pattern matches too (the definition is in
hand; there is no typo-exemption reason to stay quiet about a non-shared match). Either way,
the plan's claim "exactly as a literal entry" should stop over-promising.

### 21.6 What this pass confirms

- **The heuristic fix is the model dogfooding outcome.** The production failure (196%
  imbalance, zero improving moves, two-disk VM pinned in place by `κ`'s fragmentation penalty)
  is minimized into a test whose every number hand-checks; the new `_vm_relocation_trials()`
  family is scored by the same `evaluate_assignment()` as the other two (AGENTS.md §5's
  one-implementation rule), respects `cooldown_storages` as a destination exclusion exactly
  like them, and is restricted to VMs with more than one *movable* disk — the single-movable-
  disk case already being the plain single-move candidate, so nothing is tried twice. The
  `_best_of()` extraction preserves the incumbent comparison semantics exactly (strict `<`,
  deterministic family order); §5.5's step 3 was amended and step 4's remaining scope
  narrowed in the same commit, per AGENTS.md §7.6.
- **The connection-pool fix follows the house pattern for proxmoxer internals.**
  `_apply_connection_pool_size()` reaches into `_store["session"]` exactly the documented,
  best-effort way `_apply_ticket_refresh_seconds()` does; it never shrinks below `requests`'
  own default of 10; it is a guarded no-op for every wrong-shaped future; it is applied in
  `_build_api()` so reauthenticate-rebuilt sessions get it too; and the no-op shapes are
  tested. Mounting one adapter instance on both scheme prefixes is sound (urllib3 keys an
  adapter's pools by scheme+host, so sharing one adapter is standard practice).
- **Pattern expansion leaves no pattern-shaped holes downstream.** Every consumer of group
  storages — `D`/`S`, gates, load model, heuristic, MILP, scheduler, executor, cooldown keys,
  `verify-storages` — reads the topology `Group.storages` built from the expanded list;
  nothing past topology ever reads raw `config.groups[*].storages` (the only remaining
  consumers are `config.py`'s own load-time validators, which must see the raw entries to
  check them). Expansion ordering is deterministic (sorted ids),
  `matched_ids` is stable across runs for `verify-storages` and the INFO log, and the
  `state.json` cooldown-key story (group-name-embedded keys, stale entries harmless) is
  carried through §11.4 correctly.
- **The schema/semantic validation split is right.** `minItems: 1` is the structural floor;
  "≥ 2 after expansion" is enforced where the count is knowable — immediately for
  pure-literal groups (`_check_group_size`), at topology time for pattern groups — with the
  zero-match, same-group double-claim, and cross-group collision cases each tested, and
  `test_pattern_matching_is_fullmatch_not_substring` pinning the `preprod` hazard §11.4
  itself calls out.
- **The `22973b2` test pinning is the correct fix for a real environment dependence**: three
  tests were asserting dispatch outcomes that legitimately differ between the dev venv (no
  solvers → heuristic) and CI/the Debian build (pulp+cbc installed → cbc). Pinning
  `backend: heuristic` in tests *about* the heuristic, while backend dispatch keeps its own
  monkeypatch-based tests, is the honest split; my pulp-installed run (597 passed) confirms
  it end to end.
- **The CI repairs stay inside the project's own policy.** ca-certificates/typeshed/curl+gpg
  are explicit apt additions with root causes documented in the workflow headers (the
  `--no-install-recommends` trap each of them hit); python3-flake8-bugbear's removal is
  verified against Debian and changes nothing CI enforces; the codecov move to
  `codecov-action@v7` with `report_type: test_results` follows the deprecation. None of them
  pip-installs around a missing Debian package. `debian/control` correctly needs no change:
  the range adds no dependency (`re` is stdlib, `requests` is already `Depends`), and mypy is
  not part of the package build, so typeshed is a tests.yml-only concern.
- **The state.py mkstemp refactor removes the ambiguity at its source** (`tmp_path` assigned
  once, a `replaced` flag instead of a mid-`try` `None` reassignment) and — better than the
  fix itself — adds the direct regression test for temp-file cleanup that previously existed
  only by inference from `StateError`.

### 21.7 Assessment

This is the smallest and healthiest range since the implementation was declared finished: one
production bug class found by actually running the tool (and fixed with the plan, not just
the code), five CI repairs that each make the "Debian-packaged toolchain is enough" claim
more literally true, and one clean, well-fenced feature addition that extends configuration
without touching any engine arithmetic. All three findings are at the boundaries the previous
eleven passes consistently found: U-01 is a plan/code text disagreement plus an untested edge
(the T-03/S-08 family), U-02 is documentation prose whose truth ended mid-history (the
R-04/T-04/T-05 family, now with a mechanical-guard recommendation), and U-03 is an
over-promising sentence in an otherwise careful amendment. None touches a safety invariant:
dry-run default, reserve-never-traded, transient invariant, no-auto-delete, and the payback
gate are all untouched by the range and re-verified green by the suite. Fixing U-01 should
come first — the plan/code endpoint disagreement is one sentence, but the error-message and
test gaps are the part an operator would actually hit.

---

## 22. Resolution of twelfth-pass findings (U-01..U-03)

All three findings were real; all three are fixed, not refuted.

| ID | Status | How resolved |
|----|--------|--------------|
| U-01 | Resolved | Plan §11.4 now names `GET /storage` (definitions) as what a pattern is matched against, agreeing with `topology.py` and with the same call literal-id validation already uses. `storage_resources()`'s fetch moved ahead of expansion in `_fetch_cluster_data()` specifically so `_match_pattern_entries()` can check every matched id against it: a pattern-matched storage with a definition but reported active by no node (disabled) is now a `TopologyError` naming the pattern and the storage, raised during expansion rather than surfacing three steps later as `_pick_active_node()`'s generic message. New test `test_pattern_matching_a_disabled_storage_raises_naming_the_pattern` reproduces the exact scenario the review found (a `_cluster_client(..., inactive=...)` storage present in `GET /storage` but absent from the resource inventory) and asserts the message names both the pattern and the storage. A literal reference to the same disabled storage is intentionally left on its existing path (`_pick_active_node`) — its message already names a storage the operator wrote themselves, so there was no opacity to fix there. |
| U-02 | Resolved | All six stale claims fixed in one sweep: `60-topology.md`'s two "not yet written" mentions now name `execute.py`'s `_preflight()` and correct the `reserve.py` paragraph to say `heuristic.py` calls `compute_reserve_status()` directly while `optimize.py`'s MILP path encodes the equivalent bound as a scaled linear constraint instead (it cannot call a Python function from inside a solver's constraint system); `80-gates.md`'s `apply (not yet written)` parenthetical dropped, reworded to contrast `show-load`'s possibly-stale printed line against `plan`/`apply`'s fresh evaluation; `90-heuristic.md`'s "CP-SAT/CBC coefficient scaling ... not yet written" bullet removed outright from "what this pass deliberately does not do" (`optimize.py` implements section 5.5's scaling in full, including the `_assert_nonzero_when_weighted` regression guard the plan's own gamma-trap finding required) and its `explain`/`apply` stubs sentence corrected to `apply` is fully implemented, only `explain` remains a stub; the manual's `last_balance` paragraph rewritten to state that `apply` writes it once a run actually executes a move (`confirm`/`auto`, never `dry-run`), so the first-run behaviour is only the common case before a group's first successful migration. The mechanical-guard idea (a documentation test grepping for stale "not yet written" mentions of modules that now exist) is noted but not built in this pass — a follow-up, not a defect. |
| U-03 | Resolved | The not-`shared` warning is no longer computed inside the literal-only loop: `_expand_group()` now emits it once, after expansion, uniformly over every final member of the group's storages — literal or pattern-matched alike — reading straight from `definitions_by_id`. Plan §11.4 needed no change (it never claimed the asymmetry; the code did), but `60-topology.md`'s asymmetry paragraph was extended to say so explicitly, so a future reader does not have to rediscover it by reading the diff. New test `test_pattern_matching_an_unshared_storage_still_warns` reproduces the review's scenario (a not-`shared` storage matched only by a pattern) and asserts the warning now appears. |

Verification: dev venv `python3 -m pytest` — **588 passed, 24 skipped** (ortools, pulp,
statsmodels absent), **91.65% line coverage**, unchanged from the twelfth pass's own run since
the two new tests exercise lines the existing suite already reached from other angles.
`make check` clean (fmt, lint, typecheck, test, fixtures, docs-check — `IMPLEMENTATION_PLAN.pdf`
rebuilt to 42 pages, internals PDF to 44, manual PDF unchanged at 34 pages, all three stamps
regenerated in the same commit as their Markdown per AGENTS.md §7).

---

## 23. Thirteenth-pass review — `explain`, node-scoped queries, CI solver coverage, plain-language messages

Reviewed commit range `66aacc1..HEAD` (the U-01..U-03 fixes themselves are already recorded in
section 22). Seven commits: `5680d58` (README rewritten as a quickstart, six stale claims fixed
— U-02's sweep), `54ec527` (`explain`, the last unimplemented subcommand, plus
`docs/manual/29-explain.md` and the manpage entry), `a605391` (CI pip-installs `ortools` so
`test_optimize.py`'s CP-SAT cases actually run), `0c4485b` (a dedicated `.venv-typecheck/` for
mypy, and `make venv`/`test`/`cov` stop swallowing a failed solver-extras install), `981adce`
(section 3.4's node-scoping of every PromQL query, auto-derived from `GET /nodes`, with the new
`metrics.extra_selector` override — the second new plan section ever), `84ea838` (`explain`
grows the measured-load section and `-v` provenance), `73fc0aa` (every bare "section N.M"
citation in operator-facing strings replaced with plain language naming the config knob to act
on). Roughly 2,070 inserted lines across 48 files, ~1,000 of them tests.

The range's quality stays high. `explain` is built the right way — it runs the *identical*
`_plan_group()` pipeline (`plan` and `apply` share, so it cannot drift) and adds only rendering:
the pinned block with exact per-disk reasons, §3.6's "cannot fully consolidate" naming with the
blocker per device, the five-term objective breakdown (`ObjectiveBreakdown`'s own stated reason
for existing), pinned-load-as-structural-imbalance warning, show-load's measured-load picture
reused verbatim, and JSON that always carries query provenance. Node scoping is correct where it
is easy to get wrong: the matcher sits *inside* `rate()`'s vector selector before `sum by`
collapses labels; every node name is escaped as a regex literal (an FQDN's `.` otherwise matches
more than the node); the list comes from `GET /nodes` rather than the VM/storage inventories (an
idle node would silently drop out of either); `extra_selector` wins outright; `verify-metrics`
stays deliberately unscoped-and-independent-of-PVE; and the whole thing is threaded as one
resolved `str | None` per run. The plain-language sweep is genuine, not cosmetic — each reworded
message names the config knob to act on, and the manual's worked examples were updated to match
the new strings in the same commit. Both new findings of substance are documentation-accuracy
issues the mechanical cross-reference tests structurally cannot catch, in the same family as
P-01/T-03.

### 23.1 Verification run

- Dev venv `python3 -m pytest`: **649 passed, 1 warning** (a statsmodels `ConvergenceWarning`
  from one Holt-Winters fit test — benign, unasserted test noise), **98.66% line coverage**.
  For the first time in this review's history the dev venv carries all optional backends
  (`ortools` 9.x, `pulp` 3.3.2, `statsmodels` 0.15 — the `0c4485b` solver-extras install), so
  nothing skips and the CP-SAT path is covered locally too.
- System Python (pulp **2.7.0**, the exact Debian trixie/CI version, no ortools): **636 passed,
  13 skipped** — only the cpsat-parametrized cases skip; the CBC and heuristic paths are green
  on the packaged toolchain.
- `tests/fixtures/generate_expected.py --check`: OK. `sha256sum --check` on all three PDF stamps
  (plan, internals, manual): OK. `black --check`, `flake8`, and `mypy` (in its own
  `.venv-typecheck/`, per the new Makefile split): all clean.
- **Node-selector construction verified empirically**:
  `build_node_selector('nodename', ['pve01.example.com', 'pve02.example.com', 'pve02.example.com', 'pve-1'])`
  → `nodename=~"pve-1|pve01\.example\.com|pve02\.example\.com"` (escaped dots, deduplicated,
  sorted); `extra_selector` wins verbatim; both-unset degrades to `None` (no filter).
- **The new `29-explain.md` worked example was re-derived by hand** (the reviewer tradition for
  §14 applies to this one too). With VM 106 added (scsi0 1.0 TiB/ℓ 0.9 pinned on san-a, scsi1
  0.5 TiB/ℓ 0.1 on san-b): Σℓ = 8.40 ✓, u* = 2.80 ✓, L_san-a = 7.40 ✓, L_san-b = 0.80 ✓,
  spread 257.1% → 17.9% ✓, all four Δimbalance values (−4.00, −3.40, −0.80, −0.40) ✓, objective
  terms 0.6 + 1 + 0.225 + 0.5 + 0 = 2.32 ✓ (VM 101's split κ-charged, VM 106's not — consistent
  with the implemented `affinity_counts_pinned_disks` rule), benefit 8.6 × 604800 = 5.20e6 ✓,
  cost 4.72e4 ✓, ratio 110 ✓, all three reserve "requires" lines ✓. **Two "used" figures are
  wrong** — see V-03.
- The `reserve-tradeoff`/`fc-tier1` fixtures are untouched by this range (no solver or objective
  change); `--check` confirms both expected files current.
- CI workflow review: `ortools` is installed *after* `make SYSTEM_TOOLS=1 fmt-check lint
  typecheck` runs, so the stub-parse problem that motivated the mypy venv can never reach the
  typecheck step; the packaged-path story (cbc + heuristic from apt) is unchanged by the pip
  exception (see V-04).

### 23.2 Findings summary

| ID | Severity | Module(s) | Summary |
|----|----------|-----------|---------|
| V-01 | Medium | `docs/manual/10-configuration.md`, `heuristic.py`, plan §5.3 | The `objective.reserve_violation_penalty` entry describes a computation that has never existed anywhere in the code ("the engine computes a provably-dominant P … and uses `max(configured, computed)`, warning when it had to raise it" — no `P_min` exists in `src/`), while denying the key's one live consumer: the heuristic backend's objective — which `explain`'s new `objective:` line prints, and the §14 fixture totals carry — multiplies this key by any remaining (C5) shortfall |
| V-02 | Medium | plan §9.5, `cli.py`, `docs/manual/27-plan.md` | §9.5 specifies the pinned block ("not optional decoration … the only place an operator learns which snapshots to clear", with per-pin action hints) as part of **every mode's** plan output; the implementation prints it in `explain` only, with no action hints ("→ clear snapshots to unblock", "→ waited 0s, re-check next run" exist nowhere), and `27-plan.md` claims "`show-load`/`plan` both show it as `[pinned: …]`" — false for `plan` (neither renderer has any pinned field) |
| V-03 | Low | `docs/manual/29-explain.md` | The new worked example's `used` figures are internally inconsistent with its own disk listings and its own reserve lines: san-a prints `used 4.50 TiB` but its disks sum to 5.50 TiB and its "short by 1.50 TiB" is only correct for 5.50; san-b prints `1.50 TiB` vs a listed 2.00 TiB — both stale by exactly VM 106's disks, the example's own extension |
| V-04 | Low | `.github/workflows/tests.yml`, AGENTS.md §9.3, `.agents/packaging.md` | CI pip-installs `ortools` (`--break-system-packages`) as an exception to §9.3's absolute "CI installs its Python tooling from apt, never from pip" — the reasoning is sound and stated in the workflow's own header comment, but neither AGENTS.md nor `.agents/packaging.md` references it, so the policy documents and the pipeline they govern now disagree on paper |
| V-05 | Info | working tree | `run-with-system-python.sh` sits untracked in the checkout: a complete, SPDX-headed helper (runs the CLI against the system toolchain, no venv — the `SYSTEM_TOOLS=1` story made convenient) referenced nowhere in Makefile, AGENTS.md, `.agents/` or `docs/`; invisible to review, CI and the package alike, it will bitrot silently |

### 23.3 V-01 — the manual describes a penalty computation that has never existed

**Severity:** Medium
**Files:** `docs/manual/10-configuration.md:633-642`, `src/proxmox_storage_drs/heuristic.py:241`,
`IMPLEMENTATION_PLAN.md` §5.3

The manual entry for `objective.reserve_violation_penalty` (untouched since the phase-1/2 docs
commit `f484a6a` — verified with `git log -L`) says:

> A **floor**, not the value actually used, for the single-stage big-M fallback solve path (…):
> the engine computes a provably-dominant `P` from the group's own load and disk sizes at solve
> time and uses `max(configured, computed)`, warning when it had to raise it. The default
> lexicographic two-stage solve (option 1, and the default) needs no penalty at all and is
> unaffected by this key.

Three claims, two of them wrong:

1. **No provably-dominant `P` computation exists anywhere in `src/`** — `grep` for `P_min`/
   `p_min`/`computed_p`/`dominant` returns nothing. The M-06 resolution added the requirement
   to the *plan* (§5.3: "the model uses `P = max(configured, P_min)` and logs a warning … and
   repeat them in `pve-storage-drs explain`"), but the code that would compute it was never
   written: `91-optimize.md` documents that the MILP is lexicographic-only by design, and the
   heuristic multiplies the *configured* value straight into its objective
   (`reserve_penalty_term = objective.reserve_violation_penalty * reserve_shortfall_tib`).
   The §5.3 requirement to repeat the numbers in `explain` is therefore dormant — no big-M
   path exists to raise `P` — but the manual describes the dormant machinery as the key's
   *actual behaviour*.
2. **"Unaffected by this key" is false in a fully reachable configuration.** The heuristic
   backend (`solver.backend: heuristic`, or `auto` with neither solver installed — exactly the
   packaged-without-Recommends install the autopkgtest tests) uses this key directly: it scores
   every candidate assignment with the `P × shortfall` term, so whenever a group's (C5)
   violation is physically unresolvable, the configured value influences which assignment the
   descent settles on and what the objective totals report. The §14 fixture's own expected
   files carry `big_m_p` for exactly this arithmetic. And as of this range, `explain`'s new
   `objective:` line prints the term — an operator can now *see* the key doing something the
   manual says nothing in the default path does.

This is the P-01/P-02/S-08/T-03 family a fifth time over, and it survived U-02's stale-claim
sweep because that sweep grepped for "not yet written"/"remain stubs" phrasing, not for
confident descriptions of never-implemented computations.

**Recommendation:** rewrite the entry to describe what the key actually does today: it is the
reserve-violation weight in the heuristic backend's objective (and the `reserve` term
`explain` prints and the §14 fixture totals carry), it exists so the heuristic's candidate
comparisons stay commensurable with the big-M objective the plan describes, the MILP backends
are lexicographic and never consult it, and the §5.3 `max(configured, P_min)` floor applies to
the unimplemented single-stage alternative only. Either that, or implement the floor where the
heuristic consults the key — but a documentation fix is the honest minimum, and per AGENTS.md
§7.6 the plan's §5.3 sentence should gain the same "as built" annotation §10.1 got for T-03.

### 23.4 V-02 — §9.5's pinned block: specified for every mode, implemented for `explain` only

**Severity:** Medium
**Files:** `IMPLEMENTATION_PLAN.md` §9.5 (lines 1549-1557, unchanged since the original spec),
`src/proxmox_storage_drs/cli.py` (`_render_group_plan_human`/`_render_group_plan_json`),
`docs/manual/27-plan.md:169-170`

§9.5's output example — explicitly "Every mode emits the same machine-readable plan (JSON) plus
a human summary" — ends with the pinned block and its closing paragraph: "The pinned block is
not optional decoration — it is the 'complain' half of the skip-and-complain policy of §3.7,
and it is the only place an operator learns which snapshots to clear." The spec's block carries
per-pin action hints ("`→ clear snapshots to unblock`", "`→ waited 0s, re-check next run`") and
the pinned-load/best-achievable-spread line.

The implementation: `plan` and `apply` print none of it — neither human nor JSON renderers have
a single pinned field (verified by inspection of both). `explain`, as of this range, prints the
block (exact reasons, sizes, loads, ℓ/z), the "cannot fully consolidate" naming, and the
pinned-load line — good, and clearly the right home for the narration. But (a) the per-pin
action hints exist nowhere in any command's output, including `explain`; (b) the plan's §9.5
example still shows the block as part of the plan output with no "as built" annotation, eleven
passes after `plan` first shipped without it; and (c) `27-plan.md` asserts "`show-load`/`plan`
both show it as `[pinned: cooldown: ...]`" — true for `show-load`'s per-disk lines and
`explain`, flatly false for `plan`.

An operator following the manual's own reading would run `plan`, see three moves and no pins,
and never learn the fourth VM is pinned by snapshots — the exact §3.7 complaint obligation,
deferred to a command the manual's plan page never points them at for it.

**Recommendation:** the cheapest coherent resolution is documentation, not code: add the "as
built" note to §9.5 (the pinned block, fragmentation naming and pinned-load line live in
`explain` — and inline per-disk pins in `show-load`; `plan`/`apply` deliberately print only
what they will act on), fix the `27-plan.md` sentence to name `show-load`/`explain`, and have
`27-plan.md`'s "What `plan` does not yet do" list say plainly that pins are not shown here.
The per-pin action hints are worth restoring inside `explain`'s pinned block — they are one
format string each, and §9.5's own justification for the block is teaching the operator *what
to do* about each pin, not merely that it exists.

### 23.5 V-03 — two stale "used" figures in the new `explain` example

**Severity:** Low
**Files:** `docs/manual/29-explain.md:34,39`

Hand re-derivation (23.1) found every computed number in the new worked example correct except
the two per-storage `used` figures, both stale by exactly the added VM 106's disks — the
example was extended from `plan`'s §14-based one by adding VM 106 without updating the used
totals:

- san-a lists 101:scsi0 (2.00) + 101:scsi1 (1.00) + 102:scsi0 (1.50) + 106:scsi0 (1.00) =
  **5.50 TiB**, prints `used 4.50 TiB` — and its own `⚠ reserve short by 1.50 TiB` line is
  only correct for 5.50 (5.5 + 4.0 required − 8.0 capacity = 1.5; with 4.5 it would be 0.5),
  so the example contradicts *itself* one line apart;
- san-b lists 0.50 + 1.00 + 0.50 = **2.00 TiB**, prints `used 1.50 TiB` (reserve OK either
  way, so only the listing-vs-total inconsistency shows).

Everything else — loads, spreads, all four Δimbalance values, the objective's five terms,
benefit/cost/ratio, all three "requires" lines — verifies to the digit. This is the first
worked example in the manual set that no fixture or test asserts against, which is how a
stale number survived a range that otherwise updated its examples meticulously (the
plain-language commit updated gate-reason strings in three manual pages in lockstep).

**Recommendation:** fix the two values (5.50, 2.00). Worth considering alongside: the §14
tradition in this project is that worked examples are *executable* — a test that builds this
exact group (the §14 fixture plus VM 106) and asserts the rendered `explain` output's numbers
would have caught both figures and keeps the page honest the way the fixture tests keep §14
honest.

### 23.6 V-04 — the CI pip exception is documented everywhere except the policy documents

**Severity:** Low
**Files:** `.github/workflows/tests.yml` (header + `Install ortools` step), `AGENTS.md` §9.3,
`.agents/packaging.md`

AGENTS.md §9.3 states an absolute rule: "CI installs its Python tooling **from apt, never from
pip**. A CI that pip-installed its way around a missing Debian package would hide the day
§9.1 stopped being true." As of `a605391`, `tests.yml` runs
`pip install --break-system-packages 'ortools>=9.8'` — with a workflow-header comment that
argues the exception properly (ortools has no Debian package at all; it is optional at runtime;
the packaged path is unchanged; installation is ordered after typecheck so the numpy-stubs
problem cannot reach mypy). The argument is sound. The problem is only *where* it lives: a
reader of AGENTS.md §9.3 or `.agents/packaging.md` (whose ortools row still says only "pip-only
bonus", with no mention of CI) has no pointer to it, and by the documents' own absolutist
wording the pipeline is in violation. Policy documents that silently contradict the pipeline
they govern train readers to ignore both.

**Recommendation:** one sentence in `.agents/packaging.md`'s ortools discussion (and/or a
parenthetical in AGENTS.md §9.3) naming the exception, its reason, and pointing at the workflow
header — the same treatment the Salsa `--enable-network` fallback gets ("a deliberate,
reviewable edit — never a default").

### 23.7 V-05 — an untracked helper script (Info)

`run-with-system-python.sh` sits untracked in the checkout: ~35 lines, SPDX-headed, runs the
CLI straight out of the tree against the system python and its Debian-packaged modules — a
convenience wrapper for exactly the `SYSTEM_TOOLS=1`/CI toolchain story, with an accurate
header comment (including that `solver.backend: auto` degrades to CBC there, by design).
Referenced nowhere: not the Makefile, not AGENTS.md, not `.agents/`, not the docs. Untracked
means it is invisible to this review's usual checks, to CI, and to anyone cloning the repo —
it will bitrot silently the next time the CLI's invocation changes. Either commit it (it is a
legitimate developer convenience and would want a `.agents/packaging.md` mention) or delete
it; the only state that is wrong is the current one.

### 23.8 What this pass confirms

- **`explain` reuses rather than reimplements.** The gate/solve/schedule/payback pipeline is
  the same `_plan_group()` `plan` and `apply` call (so its numbers are byte-identical by
  construction, not by discipline); the measured-load section is `show-load`'s own renderer;
  the objective terms are the breakdown class's own five fields; `_fragmented_vms()` uses the
  *final* assignment (the R-02 lesson applied unprompted), counts a VM as blocked only when a
  pin is what keeps it spread, and works even for a `NO ACTION` group with no plan at all.
  The JSON always carries query provenance (no verbosity notion to guess about), the human
  `-v` line is documented as the one deliberate global-option exception, and the status
  table's `explain` row plus the manpage entry match the implementation.
- **Node scoping is the right shape end to end.** One resolved selector per run; `GET /nodes`
  (not the VM/storage inventories, whose idle-node blind spot the `node_names()` docstring
  names); regex-literal escaping (empirically verified); `extra_selector` verbatim override
  with its own schema/manual/example-config documentation; `verify-metrics` deliberately
  unscoped with the reasoning written down in `30-metrics.md`; the plan gained the §3.4 note
  and the `GET /nodes` read-path row in the same commit; and every load path (decision
  statistic, coverage, and the saturation guard's per-disk series) threads the same selector
  so no query family can drift unscoped.
- **The plain-language sweep is complete and consistent.** Grep finds no remaining bare
  "(section N.M)" in any user-facing string (the two matches left are docstrings, where the
  citation scheme belongs); the reworded messages name actionable config keys
  (`saturation_load`, the time-window/deadline knobs); and the manual's three worked examples
  that quote gate/output strings were updated in the same commit — the discipline V-03's two
  stale numbers fell just outside of.
- **The mypy-venv split solves a real problem without weakening anything.** The
  numpy-stubs-vs-`python_version=3.11` parse failure is verified and documented in three
  places (Makefile comment, pyproject comment, `91-optimize.md`); `SYSTEM_TOOLS=1` still runs
  system mypy; and the loud-not-swallowed solver-extras install means a broken `ortools`
  install now prints an explicit warning about exactly which test cases will be skipped
  instead of silently degrading — which is also why this pass could report 649/649 with zero
  skips for the first time.
- **T-01..T-07 and U-01..U-03 stay fixed.** The re-plan membership predicate, per-attempt
  cooldown recording (`state_box` threading visible in `_run_auto_group`'s new signature),
  the upper-quantile "as built" annotations (retained verbatim through this range's manual
  edits), the saturation-claim rewordings, `raw_spread()` as the benefit input, the unified
  migration-cap counter, and the §11.4 pattern validation are all still in place and green.

### 23.9 Assessment

This range closes the tool's last functional gap (`explain` was the final stub), hardens its
data path against a real multi-cluster-Prometheus failure mode, and gets its CI to exercise
the CP-SAT path it ships as `solver.backend: auto`'s first choice — all without touching the
solver, the safety machinery, or a single fixture number, and with the plan amended in the
same commits for both new behaviours. The five findings are all documentation-accuracy or
working-tree hygiene: none changes behaviour, and the two Mediums (V-01, V-02) are precisely
the residue the mechanical cross-reference tests cannot catch — confident prose describing
machinery that was never built (V-01), and a spec's output contract that drifted from every
renderer eleven passes ago without an annotation (V-02). Both are fixable with an afternoon of
writing; V-03 is two digits. After those, the documentation set would finally meet the
standard the code has held since the tenth pass.

---

## 24. Resolution of thirteenth-pass findings (V-01..V-05)

All five findings were real; all five are fixed, not refuted.

| ID | Status | How resolved |
|----|--------|--------------|
| V-01 | Resolved | `IMPLEMENTATION_PLAN.md` §5.3 gained an "As built" note (matching T-03's own, §10.1) stating plainly that option 2's `P_min`/`max(configured, P_min)` machinery was never implemented, that both MILP backends never consult `objective.reserve_violation_penalty` at all (option 1 only), and that the heuristic backend is the key's one live consumer, using it exactly as configured. `docs/manual/10-configuration.md`'s entry for the key was rewritten to describe that heuristic-objective behaviour as the primary fact, with the MILP lexicographic solve and the unimplemented option 2 floor named as the reason the key does *not* apply there. |
| V-02 | Resolved | `IMPLEMENTATION_PLAN.md` §9.5 gained an "As built" note: the pinned block, fragmentation naming and pinned-load line live in `explain` (with `show-load` also naming individual pins inline), not in `plan`/`apply`. `docs/manual/27-plan.md`'s false "`show-load`/`plan` both show it" sentence now names `show-load`/`explain`, and a new bullet in "What `plan` does not yet do" states outright that no pinned block exists there. The per-pin action hints the spec's own example shows (`→ clear snapshots to unblock`, etc.) were restored where the review recommended — inside `explain`'s pinned block, via a new `_pin_action_hint()` (human report's `→ <hint>` suffix and JSON's `pinned_disks[].action_hint`, `null` for a standing policy exclusion, same as the spec's own "excluded by tag" pin carrying none). New test `test_pin_action_hint_names_something_to_do_only_when_there_is_something` plus updated assertions in the existing pinned-block/JSON tests. |
| V-03 | Resolved | `docs/manual/29-explain.md`'s worked example's two stale `used` figures fixed to match their own disk listings: san-a 4.50→5.50 TiB (now consistent with its own "short by 1.50 TiB" line), san-b 1.50→2.00 TiB. |
| V-04 | Resolved | AGENTS.md §9.3 and `.agents/packaging.md` (the `ortools` row and a new paragraph) now name the CI pip exception explicitly — what it installs, why, and that it is the one place the "apt, never pip" rule has a reviewed exception — pointing at `tests.yml`'s own header comment for the full reasoning, so the policy documents and the pipeline agree on paper. |
| V-05 | Resolved | `run-with-system-python.sh` committed (it is a legitimate, accurate developer convenience, not dead weight) and referenced from `Makefile` (a comment next to `SYSTEM_TOOLS=1`) and `.agents/packaging.md` (both the CI section and the `ortools`-adjacent `SYSTEM_TOOLS` mention), so it is no longer invisible to review, CI, or a future reader. |

Verification: dev venv `python3 -m pytest` — **650 passed, 1 warning** (the same benign
`ConvergenceWarning` V-05's predecessor pass noted), **98.67% line coverage** (one line up from
the thirteenth pass's 98.66%: the new `_pin_action_hint()` branch). `make check` clean (fmt,
lint, typecheck, test, fixtures, docs-check — `IMPLEMENTATION_PLAN.pdf` rebuilt to 42 pages,
internals PDF to 46, manual PDF to 37, all three stamps regenerated in the same commit as their
Markdown per AGENTS.md §7).

---

## Appendix A — Independent verification of the §14 worked example

All values re-derived by hand from §14.1's input.

**Initial state (§14.2).**
- san-a: disks 101:scsi0 (2.0TiB, ℓ=3.0), 101:scsi1 (1.0, 1.0), 102:scsi0 (1.5, 2.5).
  used = 4.5 ✓; L = 6.50 ✓; Z = 2.0 ✓; used+f·Z = 8.5 ✓; violates by 0.5 ✓.
- san-b: 103:scsi0 (0.5, 0.4), 104:scsi0 (1.0, 0.3). used = 1.5 ✓; L = 0.70 ✓; Z = 1.0 ✓;
  3.5 ✓.
- san-c: 105:scsi0 (0.5, 0.2). used = 0.5 ✓; L = 0.20 ✓; Z = 0.5 ✓; 1.5 ✓.
- Σℓ = 7.4 ✓; u* = 2.4667 ✓.
- Spread = (6.50−0.20)/2.4667 = 2.554 → 255% ✓.
- E_before = 4.0333 + 1.7667 + 2.2667 = 8.0667 ✓.

**Three-move solution (§14.3), β=0.25.** Moves: 102:scsi0→san-c, 101:scsi1→san-b,
105:scsi0→san-b.
- san-a: 101:scsi0 only → L=3.0 ✓, used=2.0 ✓, Z=2.0 ✓, 6.0 ✓.
- san-b: 103,104,101:scsi1,105 → L=0.4+0.3+1.0+0.2=1.90 ✓, used=3.0 ✓, Z=1.0 ✓, 5.0 ✓.
- san-c: 102:scsi0 → L=2.50 ✓, used=1.5 ✓, Z=1.5 ✓, 4.5 ✓.
- E_after = 0.5333 + 0.5667 + 0.0333 = 1.1333 ✓; spread = (3.00−1.90)/2.4667 = 44.6% ✓.
- β knob: third move ΔE = 1.5333 − 1.1333 = 0.400 ✓; at β=0.25: −0.400+0.250+0.025 = −0.125
  (accept) ✓; at β=0.50: −0.400+0.500+0.025 = +0.125 (reject) ✓.

**Two-move solution, β=0.50.** Moves: 102:scsi0→san-c, 101:scsi1→san-b; 105 stays on san-c.
- san-a: L=3.0; san-b: L=1.70; san-c: 102+105 → L=2.70. State (3.00, 1.70, 2.70) ✓.
- E = 0.5333 + 0.7667 + 0.2333 = 1.5333 ✓; spread = (3.00−1.70)/2.4667 = 53% ✓.
- This matches the §9.4 output ("san-c u=2.70", "spread 53%") ✓.

**Affinity trade-off (§14.3).** Keeping VM 101 together forces san-a L=4.0, best E=3.133.
Split (with κ=0.5): 1.1333+0.5 = 1.633; together: 3.133+0 = 3.133. Split wins by 1.5 ✓.

**Ordering (§14.4).** 102:scsi0 first (repairs san-a reserve: 4.5→3.0 used, 3.0+4.0=7.0≤8.0 ✓).
Transient checks for all three moves verified: 5.0≤8.0, 4.5≤8.0, 5.0≤8.0 ✓.

**Payback (§14.5), two-move plan.** bwlimit=200 MiB/s, ω=2, H=604800, λ=10.
- 102:scsi0: 1.5 TiB = 1,572,864 MiB / 200 = 7864 s ✓; cost = 2×7864 = 15728 ✓.
- 101:scsi1: 1.0 TiB / 200 = 5243 s ✓; cost = 10486 ✓; Σ = 26214 ✓.
- benefit = ΔE·H = 6.5333×604800 = 3,951,360 ✓; ratio = 3,951,360/26,214 = 150.7 ≥ 10 ✓.
- Failed-payback example (4 TiB, ΔE=0.05): cost=2×20972=41943 ✓; benefit=0.05×604800=30240 ✓;
  ratio=0.72 < 10 ✓.

**Conclusion:** The §14 fixture is fully self-consistent. It can be used directly as an
acceptance test (transcribe to a machine-readable fixture per F-21).

---

## Appendix B — External-fact checks (web search)

- **PVE 9.2 release.** Proxmox VE 9.2 was released 2026-05-21 (Debian 13.5 "Trixie", kernel
  7.0, QEMU 11.0). It introduced a built-in dynamic load balancer. Relevant because the plan
  targets "PVE 9.2"; the built-in balancer is complementary (node-level only) — see F-24.
- **`move_disk` semantics.** Confirmed: `delete=1` removes the source volume after a successful
  `drive-mirror`; the VM stays running (online). Community reports of `delete` occasionally
  leaving an orphaned source volume exist — the plan already handles this in §9.3 (detect and
  report, never auto-delete), which aligns with real-world behavior.
- **blockstat / InfluxDB field and tag names.** Web search did **not** reliably confirm the
  exact field names (`rd_bytes`, etc.) or the `instance=scsi0` tag claim; some search results
  were unreliable. The plan's claims remain plausible and internally consistent, and the
  `verify-metrics` command is the correct validation gate. See F-23.
- **PromQL / VictoriaMetrics.** `quantile_over_time`, subquery ranges, `rate()`, and the
  `/api/v1/label/__name__/values` endpoint are supported by both Prometheus and VictoriaMetrics.
  See F-25.
