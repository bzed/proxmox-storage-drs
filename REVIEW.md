# Review of `IMPLEMENTATION_PLAN.md` (Proxmox Storage DRS)

This document is a careful, verbose review of `IMPLEMENTATION_PLAN.md`, `README.md`,
`config/drs.example.yaml`, and `.gitignore` in this repository. It is structured to be
machine-parseable: each finding has a stable ID, a severity, a section anchor, a statement of
the issue, and a concrete recommendation. A summary table precedes the detail.

The reviewer independently re-derived every number in the section 14 worked example and
verified them by hand; the results of that verification are recorded in Appendix A. A few
load-bearing external facts were checked via web search and are reported in Appendix B.

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
