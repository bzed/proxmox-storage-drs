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
