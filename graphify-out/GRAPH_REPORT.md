# Graph Report - proxmox-storage-drs  (2026-09-24)

## Corpus Check
- 122 files · ~306,209 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 20 file(s) not represented in the graph (top: (none) 12, .sha256 3, .conf 1)

## Summary
- 3523 nodes · 11496 edges · 116 communities (105 shown, 11 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 1556 edges (avg confidence: 0.94)
- Token cost: 491,985 input · 0 output

## Community Hubs (Navigation)
- Topology and Disk Keys
- Execute Tests and Fixtures
- Config Errors and Durations
- Concurrent Executor
- Time Windows and Schema Checks
- Move Cost and Saturation
- Scheduler Test Helpers
- Exhaustive Solver Oracle
- PromQL Scoping and Load Blend
- Gigapipe Step Workarounds
- Empty State and Topology
- MILP Solver Guards
- Heuristic Evaluation
- Heuristic Solver Design
- Gates and Imbalance
- Persistent State Design
- Metrics Client
- Execution Results
- CLI Tests and Fake Clients
- Confirm Callback and CLI
- Move Wait Polling
- Status File Monitoring
- Reserve Invariants Overview
- Anonymizer Tests
- Topology Fetch and Sizes
- CBC and Feasibility Constraints
- Replay and Prometheus Config
- CLI Handler Design
- Plan Group Pipeline
- Collect Tests
- PVE API Errors
- Over-provisioning Rule
- PVE Connection Config
- Verify Metrics Command
- Replay Bundles
- Forecasting Protocol
- Floors and Lexicographic Solve
- Move Ordering
- Reserve Status
- Corpus Validation
- CLI Parser and Manual
- Config Loading
- Repair Scenario Tests
- Forecaster and CLI Dispatch
- Documentation Tests
- Cooldowns and Locks
- Pseudonym Hashing
- Anonymizer Mapper
- Test Client Factories
- Completion and Wipe Duration
- Bundle Capture Anonymization
- Range Step Mismatch
- Free-Space Repair
- Forecaster Factory
- Backtest and Quantile Forecast
- Logging Setup
- Advisory Lock
- Pipeline and Group Utilization
- PVE Client Reauthentication
- Recording Clients
- Fake Prometheus Session
- UPID and Task Status
- PVE Client Internals
- Agent Domain Invariants
- API Token Auth
- VM Locks
- Repair Candidates
- Auto Re-plan and Payback Gate
- Snapshot Sanitizing
- Guarded Recording Wrapper
- Group Aggregate Series
- Config Building
- Backtest Gate
- VM Config Filtering
- Git and Docs Workflow
- Drift History
- Human and JSON Rendering
- Node Selector
- State File Parsing
- JSON Log Formatter
- In-flight UPIDs
- Forecast Fallback
- PromQL Builders
- Content Responder Tests
- Range Query Chunking
- PVE Fakes
- Atomic State Save
- Exception Hierarchy
- Fake PVE Session
- README Monitoring Notes
- Debian Packaging Rules
- JSON Log Events
- Test Stdlib Imports
- Documentation Agent Guide
- Style and Autopkgtest
- Paper Log Check
- Apply Refusal Tests
- Git Workflow Guide
- PDF Freshness Stamp
- Testing Guide
- Output Format Resolution
- Orphan Volume Detection
- Pandoc Lua Filters
- Log Level Ladder
- Anonymized Config Export
- Fake HTTPS Backend
- Vmid Batches and Pseudonyms
- Rejected Candidates
- Metrics Expected Absent
- Import-All Script
- System Python Runner
- Paper Build Script
- Package Root

## God Nodes (most connected - your core abstractions)
1. `Group` - 199 edges
2. `PveClient` - 125 edges
3. `build_topology()` - 81 edges
4. `Disk` - 78 edges
5. `PrometheusClient` - 77 edges
6. `write_config()` - 76 edges
7. `run()` - 72 edges
8. `client_with()` - 71 edges
9. `make_move()` - 69 edges
10. `fake_api()` - 67 edges

## Surprising Connections (you probably didn't know these)
- `Mapper pseudonyms with order-independent vmid probing` --references--> `pseudonym()`  [EXTRACTED]
  docs/internals/97-collect-and-replay.md → src/proxmox_storage_drs/anonymize.py
- `Anonymization fails closed` --rationale_for--> `Mapper`  [EXTRACTED]
  docs/internals/97-collect-and-replay.md → src/proxmox_storage_drs/anonymize.py
- `Mapper pseudonyms with order-independent vmid probing` --references--> `Mapper`  [EXTRACTED]
  docs/internals/97-collect-and-replay.md → src/proxmox_storage_drs/anonymize.py
- `Three modules with one-way dependencies` --references--> `Mapper`  [EXTRACTED]
  docs/internals/97-collect-and-replay.md → src/proxmox_storage_drs/anonymize.py
- `Global options on the top-level parser` --references--> `build_parser()`  [EXTRACTED]
  docs/internals/40-cli-and-logging.md → src/proxmox_storage_drs/cli.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Free-space floor precedence: snapshot, hard, soft** — agents_three_floors_precedence, _agents_domain_invariants_hard_vs_soft_floor, agents_transient_invariant, agents_snapshot_reserve_never_traded [EXTRACTED 0.90]
- **Generated artefacts kept honest by stamps and tests** — agents_pdf_freshness_stamp, _agents_paper_sha256_stamp, _agents_documentation_doc_tests, _agents_packaging_pdf_verify_not_rebuild [INFERRED 0.85]
- **Release discipline: version, changelog, tag, green check** — agents_release_triple, _agents_git_workflow_release_tag, agents_make_check, _agents_packaging_two_identities [EXTRACTED 0.90]
- **Snapshot reserve, free-space floors and transient invariant enforce one safety property** — implementation_plan_snapshot_reserve, implementation_plan_free_space_soft, implementation_plan_free_space_hard, implementation_plan_transient_invariant, implementation_plan_lexicographic_solve, implementation_plan_c5 [EXTRACTED 1.00]
- **Gates, cooldowns and reserve override decide whether to act** — implementation_plan_drift_gate, implementation_plan_imbalance_gate, implementation_plan_capacity_gate, implementation_plan_cooldowns, implementation_plan_reserve_override, implementation_plan_state_json [EXTRACTED 1.00]
- **Move completion: task OK, source gone, lock clear, wipe floor elapsed** — implementation_plan_move_disk_api, implementation_plan_completion_criterion, implementation_plan_draining_state, implementation_plan_min_wipe_seconds, implementation_plan_config_lock_wait, implementation_plan_task_flock_retry [EXTRACTED 1.00]
- **Transient invariant: one formula, model and live callers** — src_proxmox_storage_drs_reserve_transient_charge_ok, src_proxmox_storage_drs_schedule_transient_invariant_ok, src_proxmox_storage_drs_execute_live_transient_check [EXTRACTED 1.00]
- **Reserve-is-never-traded principle across gate, repair and payback** — docs_internals_80_gates_reserve_override_bypasses_hysteresis, docs_internals_90_heuristic_repair_is_unconditional_not_weight_driven, docs_internals_96_payback_reserve_override_exemption_is_an_outcome_trigger, docs_internals_91_optimize_lexicographic_two_stage_reserve_solve_not_big_m [INFERRED 0.85]
- **Shared section 5.4 objective used by heuristic, MILP and scheduler** — src_proxmox_storage_drs_heuristic_evaluate_assignment, src_proxmox_storage_drs_optimize_solve, src_proxmox_storage_drs_schedule_order_moves, src_proxmox_storage_drs_reserve_compute_reserve_status [EXTRACTED 1.00]

## Communities (116 total, 11 thin omitted)

### Community 0 - "Topology and Disk Keys"
Cohesion: 0.05
Nodes (115): The cluster topology could not be built from the API responses. See…, TopologyError, disk_state_key(), ``"<group>:<vmid>:<device>"`` (section 11.2) -- the group prefix is what keeps…, _allowed_formats(), build_topology(), parse_pve_config_size_bytes(), pending_disk_reasons() (+107 more)

### Community 1 - "Execute Tests and Fixtures"
Cohesion: 0.07
Nodes (99): SourceReleaseConfig, client_with(), default_group(), FakeClock, _group_with_types(), make_disk(), make_move(), make_storage() (+91 more)

### Community 2 - "Config Errors and Durations"
Cohesion: 0.07
Nodes (83): ConfigError, The configuration file is missing, unreadable or fails validation. See…, parse_duration_seconds(), Parse a duration into seconds. Accepts a bare number (seconds) or a string like…, minimal_config_dict(), Any, Path, skipif (+75 more)

### Community 3 - "Concurrent Executor"
Cohesion: 0.06
Nodes (86): Concurrent executor with strict FIFO, Errors are not mismatches, Injectable Clock for wait loops, No double counting of in-flight mirror targets, Pre-flight re-validation against live cluster, move_disk task flock retry, ExcludeConfig, _advance_pending() (+78 more)

### Community 4 - "Time Windows and Schema Checks"
Cohesion: 0.05
Nodes (80): date, Auto-mode time-window and migration budgets, execution.time_windows gating of auto mode, jsonschema, ruamel_yaml, ruamel_yaml_error, _check_connection_config(), _check_forecast_window() (+72 more)

### Community 5 - "Move Cost and Saturation"
Cohesion: 0.06
Nodes (80): Move cost in load-seconds, Section 7.3 saturation guard defers, never rejects, _compute_one_move_cost(), One move's section 7.1 cost, plus (only when ``saturation_inputs`` is not…, MigrationConfig, compute_benefit_load_seconds(), compute_move_cost(), evaluate_plan_payback() (+72 more)

### Community 6 - "Scheduler Test Helpers"
Cohesion: 0.06
Nodes (77): _balanced_non_violating_topology(), _fake_build_topology(), _fake_reconcile_inflight(), _imbalanced_group_load(), _no_reserve_violation_topology(), _patch_show_load_deps(), CaptureFixture, Exception (+69 more)

### Community 7 - "Exhaustive Solver Oracle"
Cohesion: 0.07
Nodes (71): itertools, StorageState, all_assignments(), best_big_m(), best_lexicographic(), big_m_agreement_threshold(), build(), capacity_spread() (+63 more)

### Community 8 - "PromQL Scoping and Load Blend"
Cohesion: 0.09
Nodes (77): Scope every PromQL query to this cluster's nodes, REVIEW W-07 (no_series_matched), LoadWeights, _blend_loads(), compute_disk_load_series(), compute_group_load(), TimeSeries, Section 4's normalize-then-weight-then-rescale blend, given every key's own… (+69 more)

### Community 9 - "Gigapipe Step Workarounds"
Cohesion: 0.05
Nodes (74): gigapipe step >= range workaround, gigapipe step >= range workaround (safe step), _RawTimeSeries, REVIEW Z-04 (quantile_over_time safe-step shift), REVIEW Z-05 (estimate accounts for doubled points), MetricLabels, MetricsConfig, _combine_raw_values() (+66 more)

### Community 10 - "Empty State and Topology"
Cohesion: 0.07
Nodes (64): empty_state(), First-run state: no lock, no recorded balance, no cooldowns, nothing in flight…, The whole cluster's worth of groups, as seen by this run. By the time anything…, Topology, _fragmented_group(), _make_group_plan(), _moved_outcome(), _one_disk_group() (+56 more)

### Community 11 - "MILP Solver Guards"
Cohesion: 0.07
Nodes (66): importlib, _assert_nonzero_when_weighted(), _assert_objective_magnitude_within_int64(), cbc_available(), cpsat_available(), Section 5.5: "assert... every coefficient is a non-zero integer wherever its…, Section 5.5: "assert... the maximum objective magnitude is below 2**62"…, make_disk() (+58 more)

### Community 12 - "Heuristic Evaluation"
Cohesion: 0.08
Nodes (64): best_single_disk_alternative(), compute_vm_weights(), evaluate_assignment(), HeuristicResult, One group's heuristic solve. ``assignment`` is the final target placement…, Section 5.5 step 1: "seed with the current assignment (not from scratch -- we…, Section 5.4's `w_v = max(1, l_v / l_bar)` -- the per-VM weight that scales…, Section 5.4's objective for one candidate ``assignment``.… (+56 more)

### Community 13 - "Heuristic Solver Design"
Cohesion: 0.07
Nodes (63): staged_disks field unimplemented, The heuristic solver, best_single_disk_alternative explains why nothing moved, Descend explores single moves, swaps and whole-VM relocation, evaluate_assignment: objective separate from search, objective.spread_metric l1 vs minmax, Polish step not implemented (N-way rotation gap), Proof against section 14 worked example (+55 more)

### Community 14 - "Gates and Imbalance"
Cohesion: 0.08
Nodes (59): Imbalance gate, GatesConfig, _capacity_spread(), evaluate_group_gates(), _l1_drift(), Section 6, applied in the order it lists: reserve override, then the capacity…, ``(‖ℓ_last‖₁, ‖ℓ_now − ℓ_last‖₁)`` over the **union** of disk keys present in…, Section 5.3 (C7)'s `(max_s b_s - min_s b_s) / b_bar`, or ``None`` when the gate… (+51 more)

### Community 15 - "Persistent State Design"
Cohesion: 0.07
Nodes (59): Persistent state: state.json, Cooldown data stored here, interpreted by topology and heuristic, Disk-cooldown pin is not exempted for reserve repair, flock is the lock; JSON lock field is only a label, Reading degrades, writing raises, Rename-detaches-flock bug and in-place locked write, State dataclass tree mirrors section 11.2 JSON, Per-disk cooldown pin (+51 more)

### Community 16 - "Metrics Client"
Cohesion: 0.08
Nodes (56): Protocol-typed session for network-free tests, WindowConfig, MetricsError, Prometheus could not be queried, or the response was unusable. See…, _check_coverage(), PrometheusClient, Thin wrapper over the Prometheus HTTP API. See section 3.4/3.5. ``session`` is…, Section 3.3 step 5: report which disks fall below ``window.min_coverage``. (+48 more)

### Community 17 - "Execution Results"
Cohesion: 0.08
Nodes (58): ExecutionResult, One group's ``execute_plan()`` call. ``stopped_early`` is true for any reason…, Whether this group's execution failed in a way that must end the whole run…, _balanced_apply_group_load(), _balanced_apply_topology(), _check_statusfile(), _monitored_config(), _patch_plan_deps() (+50 more)

### Community 18 - "CLI Tests and Fake Clients"
Cohesion: 0.04
Nodes (40): str, _FakeClient, _NodeNamesClient, LogCaptureFixture, A model that §10.2 backtests (anything but ``quantile``) must fetch at least…, ``quantile`` is never backtested (`_backtest_gated_forecaster()` returns…, A model that fails its own backtest (or cannot be validated for lack of history…, REVIEW.md R-06: `move.size_bytes == 0` must not raise `ZeroDivisionError` --… (+32 more)

### Community 19 - "Confirm Callback and CLI"
Cohesion: 0.07
Nodes (56): Confirm callback lives in cli.py, shutil, _accumulate_move_stats(), _fragmented_vms(), _load_per_tib(), _log_plan_selected(), _make_confirm_move_interactively(), confirm() (+48 more)

### Community 20 - "Move Wait Polling"
Cohesion: 0.08
Nodes (50): ExecutionConfig, _MoveWaitState, _poll_move_once(), Carries :func:`_poll_move_once` state across non-blocking poll cycles -- the…, One non-blocking step of section 9.3.2's three-condition completion criterion:…, Section 9.3.2's three-condition completion criterion, blocking until it…, _wait_for_move_completion(), concurrent_client_with() (+42 more)

### Community 21 - "Status File Monitoring"
Cohesion: 0.08
Nodes (51): CompletedProcess, contextlib, datetime, Monitoring status file for check_statusfile, Monitoring status file (check_statusfile format), needs_plugin, os, Storage DRS for Proxmox VE 9.2. Balances disk I/O load across configurable… (+43 more)

### Community 22 - "Reserve Invariants Overview"
Cohesion: 0.08
Nodes (43): Higher bar for safety-critical modules (branch coverage), MILP and heuristic share one feasibility and objective implementation, dataclasses, Overview: what is built, and how it fits together, Strictly-sequential order as concurrent launch queue, anonymize.py, collect.py, replay.py: diagnostic bundles, Anonymization fails closed, bundle_reference_now rebased capture instant (+35 more)

### Community 23 - "Anonymizer Tests"
Cohesion: 0.06
Nodes (43): make_mapper(), MonkeyPatch, parametrize, Path, A node and a storage that happen to share a name must not collide., Section 16.3: 'the result never depends on iteration order'., Force two different vmids to hash to the same base slot and confirm both still…, X-09: `vmid`'s own linear probing makes a collision impossible, but nothing did… (+35 more)

### Community 24 - "Topology Fetch and Sizes"
Cohesion: 0.08
Nodes (51): concurrent_futures, One-pass fetch with bounded thread pool, Size resolution: content authoritative, config fallback, Storage pattern expansion once, before validation, GroupConfig, StorageConfig, _build_storages(), _check_cross_group_uniqueness() (+43 more)

### Community 25 - "CBC and Feasibility Constraints"
Cohesion: 0.09
Nodes (50): CBC direct unscaled transcription and pulp compatibility, Feasibility constraints built once per stage, CBC via PuLP backend, ObjectiveConfig, _cbc_capacity_spread_term(), _cbc_feasibility_constraints(), _cbc_objective_terms(), _cbc_storage_fill() (+42 more)

### Community 26 - "Replay and Prometheus Config"
Cohesion: 0.10
Nodes (47): requests, PrometheusConfig, _captured_step(), _config_from_bundle(), _free_space_pairs(), MonkeyPatch, Path, AH-01/AH-06: a live config carrying only the deprecated ``min_free_bytes`` is… (+39 more)

### Community 27 - "CLI Handler Design"
Cohesion: 0.09
Nodes (48): Command handler dict, not an if-chain, --group filtered once after build_topology, gates only reads last_balance, Mutable state box narrow exception to functional style, Startup scan folds excluded vmids before planning, Namespace, _apply_exit_code(), _dump_report_json() (+40 more)

### Community 28 - "Plan Group Pipeline"
Cohesion: 0.07
Nodes (40): show-load gate line is diagnostic, _plan_group shared planning pipeline for plan and apply, final_assignment is the schedule's own truth, _GroupPlan, _log_gate_decision(), _log_load_digest(), _log_payback_verdict(), _plan_group() (+32 more)

### Community 29 - "Collect Tests"
Cohesion: 0.08
Nodes (43): capture(), _mapper(), Path, X-08: section 16.1's manifest line ("schema, versions, what was captured...")…, X-08: section 16.3 promises the manifest "flags" a non-node-shaped…, Z-03: `resolve_node_selector()`'s tier-1 precedence used to win on *both* sides…, A live capture against the dev cluster found the previous implementation's bug…, verify_metrics() never carries a node selector at all -- nothing to rewrite,… (+35 more)

### Community 30 - "PVE API Errors"
Cohesion: 0.08
Nodes (42): proxmoxer, PveApiError, The Proxmox VE API returned an error or an unusable response. See…, fake_api(), BaseException, raise_pve_error(), raise_error(), raise_error() (+34 more)

### Community 31 - "Over-provisioning Rule"
Cohesion: 0.11
Nodes (42): Pool used figure is display-only, never a model input, Never consider over-provisioning (provisioned size only), The Proxmox VE API client, bwlimit bytes/s to KiB/s conversion only in move_disk, node_names uses GET /nodes, storage_content silently empty without Datastore.Allocate, storage_definitions uses the list form GET /storage, vm_config returns pending value; vm_pending exposes both (+34 more)

### Community 32 - "PVE Connection Config"
Cohesion: 0.06
Nodes (26): Best-effort ticket refresh tightening, ProxmoxConfig, _apply_connection_pool_size(), _apply_ticket_refresh_seconds(), _build_api(), Any, REVIEW.md P-01: wire ``proxmox.ticket_refresh_seconds`` through, best-effort.…, Run one ``proxmoxer`` call, wrapping every failure as :class:`PveApiError`.… (+18 more)

### Community 33 - "Verify Metrics Command"
Cohesion: 0.08
Nodes (39): verify_metrics runs six checks, verify-metrics command, build_vmid_selector(), _check_cross_metric_disk_consistency(), _check_device_label_collision(), _check_metric_names_exist(), _check_observed_spacing(), _check_sample_series() (+31 more)

### Community 34 - "Replay Bundles"
Cohesion: 0.11
Nodes (19): Replay clients are real subclasses, BundleError, A diagnostic bundle (IMPLEMENTATION_PLAN.md section 16) could not be written or…, bundle_reference_now(), load_manifest(), _NeverSession, _parse_step_seconds(), Any (+11 more)

### Community 35 - "Forecasting Protocol"
Cohesion: 0.11
Nodes (37): Forecasting: the protocol and its three implementations, HoltWintersForecaster optional statsmodels fallback, Per-disk summed forecast upper bound, SeasonalNaiveForecaster hour-of-day buckets, Single required-range rule with three pure functions, Use upper bound, never point estimate, for saturation guard, The Prometheus client and verify-metrics, Cross-metric disk consistency check (+29 more)

### Community 36 - "Floors and Lexicographic Solve"
Cohesion: 0.10
Nodes (36): hard_s binds in flight, soft_s binds at plan endpoint, Lexicographic two-stage solve is default; big-M P computed at build time, Snapshot reserve never traded for balance, Three floors precedence f_s*Z_s > hard_s > soft_s, Transient invariant holds during moves, Shared symbol glossary (D, S, U_ext, C2, C4, C5, l_d, L_s, u_s, u*), free_space soft/hard resolved once per storage, Live transient check uses provisioned sizes, never PVE used (+28 more)

### Community 37 - "Move Ordering"
Cohesion: 0.11
Nodes (34): order_moves(), _pending_moves(), Assignment, Section 8.2 priority 1: is ``disk``'s *current* (in ``state``) storage…, Section 8.2's scheduling loop for one group. ``target_assignment`` is normally…, _resolves_reserve_violation(), storage_of(), make_disk() (+26 more)

### Community 38 - "Reserve Status"
Cohesion: 0.10
Nodes (32): compute_reserve_status(), managed_used_bytes(), (C4)/(C5) evaluated for one storage at the assignment ``storage_of`` encodes.…, Sum_d z_d for every disk in `D` on ``storage_id`` under ``storage_of`` -- the…, StorageOf, make_disk(), make_storage(), After the plan's three-move solution (section 14.3): san-a keeps only 101:scsi0… (+24 more)

### Community 39 - "Corpus Validation"
Cohesion: 0.12
Nodes (31): tests_corpus, tests_corpus_validate_corpus, _invariant_inputs(), needs_full_checkout, parametrize, Path, X-03: `prometheus/` files previously got the value-pattern pass only -- a…, X-02: reproduced in 29.1 -- a `.example`/`.internal`/`.corp`/`.lan` host passed… (+23 more)

### Community 40 - "CLI Parser and Manual"
Cohesion: 0.08
Nodes (30): ArgumentParser, CommandHandler, --manual prefers man(1), apply_mode_override(), build_parser(), _fallback_manual_text(), _log_run_summary(), main() (+22 more)

### Community 41 - "Config Loading"
Cohesion: 0.09
Nodes (28): load_config(), Resolve, read, parse and validate the configuration. See section 11 for…, Path, REVIEW.md R-02: when the scheduler can only order *some* of the heuristic's…, Every real subcommand now has a real handler (``explain`` was the last one) so…, A real, on-disk diagnostic bundle -- built the same way test_collect.py does,…, X-10: `--replay ... --mode auto <cmd>` used to log `run_started` and an…, Section 2.3: in text format the log record *is* the human line, so the separate… (+20 more)

### Community 42 - "Repair Scenario Tests"
Cohesion: 0.10
Nodes (25): `_sample_topology()` with san-b given more headroom (16 TiB instead of 8):…, san-a violates (C5); its only movable disk is 101:scsi0 (102:scsi0 is pinned,…, The same repairable plan, but with san-a's `saferemove` off, so the hard…, A `Forecaster` whose `predict()` always returns the same, huge upper bound…, san-a (the source, and the only storage with any disk currently resident --…, `_apply_payback_gate()` must exclude a deferred move from what it hands to…, No storage in the group configures `saturation_load` -- the guard must not even…, `_repairable_sample_topology()`'s one move sits on a `saferemove` storage large… (+17 more)

### Community 43 - "Forecaster and CLI Dispatch"
Cohesion: 0.13
Nodes (26): QuantileForecaster dependency-free percentile, Command dispatch, the mode-override rule, and why logs go to stderr, Global options on the top-level parser, Log handler on root logger, level on package logger, Log level ladder, mandatory INFO floor and format resolution, Mode escalation rule, Structured logs to stderr not stdout, Mandatory INFO floor for confirm/auto runs (+18 more)

### Community 44 - "Documentation Tests"
Cohesion: 0.14
Nodes (26): importlib_resources, _flatten_schema_keys(), _load_schema(), _manpage_source_text(), _manual_documented_keys(), Any, needs_full_checkout, parametrize (+18 more)

### Community 45 - "Cooldowns and Locks"
Cohesion: 0.11
Nodes (26): cooldown_remaining_seconds(), Cooldowns, _pid_alive(), Pure: merges new disk/storage cooldown timestamps into ``state``, keyed exactly…, Seconds left in ``key``'s cooldown -- ``0.0`` if nothing is recorded for it,…, Best-effort, used only to make a "still held" log message useful to an operator…, with_recorded_cooldown(), subprocess (+18 more)

### Community 46 - "Pseudonym Hashing"
Cohesion: 0.09
Nodes (21): hashlib, hmac, Keyed pseudonym HMAC-SHA256 with persisted random salt, pathlib, re, REVIEW X-08 (metric names carried verbatim), _check_no_pseudonym_collision(), generate_new_salt() (+13 more)

### Community 47 - "Anonymizer Mapper"
Cohesion: 0.12
Nodes (16): Mapper, pseudonym(), ``HMAC-SHA256(salt, kind || "\\0" || value)``, truncated to 8 hex chars.…, The stateful half of anonymization: one instance per bundle capture. ``vmid``…, The pseudonym for a vmid already passed to :meth:`register_vmids`. ``None`` for…, ``node-<8 hex>``, or ``node-<8hex>.<8hex>.invalid`` for an FQDN -- shape…, ``user-<8 hex>@realm`` -- only ever seen inside a UPID (section 16.3). A value…, Rebuild a volume id as ``<storage-pseudonym>:<prefix>-<vmid… (+8 more)

### Community 48 - "Test Client Factories"
Cohesion: 0.13
Nodes (26): make_config(), make_prometheus_client(), make_pve_client(), --no-series must skip the big, per-group superset range captures -- it does not…, Y-06: the manifest's version fields are machine-generated provenance, not free…, X-09: the printed query count used to treat a multi-day range as one range…, Z-05: a live capture stores every range series at…, Section 3.8/16.3: a real pending edit on the VM's own disk survives as the… (+18 more)

### Community 49 - "Completion and Wipe Duration"
Cohesion: 0.09
Nodes (25): compute_wipe_duration_seconds takes magnitude, Anonymization: allowlist, never denylist, A finished task is not a finished move (completion criterion), concurrency_ok predicate, VM config lock wait (open-ended lock set), Corpus scrub audit, Draining state (source still allocated during wipe), Execution lifecycle: mirroring -> draining -> done (+17 more)

### Community 50 - "Bundle Capture Anonymization"
Cohesion: 0.11
Nodes (24): functools, gzip, _anonymize_captured_prometheus(), _anonymize_prometheus_series(), _anonymize_query_text(), Bundle, _dump_json(), hash_label_name() (+16 more)

### Community 51 - "Range Step Mismatch"
Cohesion: 0.10
Nodes (12): RangeStepMismatch, ``--replay`` found the requested range query, but at a different step than this…, _issue_chunked_range_query(), Any, ``client.range_query()``, issued in ``RANGE_QUERY_CHUNK_SECONDS``-sized sub-…, FakeResponse, Any, _RangeStepMismatchFakeClient (+4 more)

### Community 52 - "Free-Space Repair"
Cohesion: 0.15
Nodes (24): `Σ_s r_s` at the assignment ``storage_of`` encodes -- section 7.3's outcome…, total_shortfall_bytes(), _free_space_repair_group(), _loads(), _make_disk(), _make_storage(), parametrize, tests/fixtures/free-space-repair.yaml, built as real topology objects.… (+16 more)

### Community 53 - "Forecaster Factory"
Cohesion: 0.15
Nodes (19): build_forecaster single factory, ForecastConfig, build_forecaster(), _holt_winters_required_range_seconds(), HoltWintersForecaster, _quantile_required_range_seconds(), The history ``forecast.model`` needs, in seconds. Called by ``config.py``'s…, Median/p95 across samples at the same hour-of-day, over several days.… (+11 more)

### Community 54 - "Backtest and Quantile Forecast"
Cohesion: 0.12
Nodes (23): backtest_error(), QuantileForecaster, The default: p95 point estimate, p99 upper bound, over the whole series.…, Section 10.2's backtest: fit ``forecaster`` on ``[now-2*window, now-window)``,…, Section 10.1: ``L̂_s(Δ) = Σ_{d : x_{d,s}=1} û_d(Δ)`` -- every given disk's own…, storage_upper_bound(), Section 10.1: L_hat_s(Delta) = sum of each disk's own upper bound, forecast…, A disk key with no fetched series at all -- e.g. this run has no history for it… (+15 more)

### Community 55 - "Logging Setup"
Cohesion: 0.14
Nodes (23): configure_logging(), floor_for_command(), The mandatory ``INFO`` floor of section 2.3, or ``None``. A run that can change…, Install this run's log handler. Called once, from ``main()``. ``floor`` is…, CaptureFixture, A `--log-level` *more* verbose than the mandatory floor is unaffected by it --…, INFO at a terminal is the narrative the operator asked for; prefixing every…, `propagate = False` on the package logger would hide every record from pytest's… (+15 more)

### Community 56 - "Advisory Lock"
Cohesion: 0.19
Nodes (23): acquire_lock(), load_state(), Best-effort read of ``path``. See the module docstring: a missing file is the…, Section 11.2's advisory lock: ``fcntl.flock(LOCK_EX | LOCK_NB)`` on ``path``…, Clears the descriptive ``lock`` field and releases the OS-level lock, writing…, release_lock(), LogCaptureFixture, Path (+15 more)

### Community 57 - "Pipeline and Group Utilization"
Cohesion: 0.14
Nodes (21): Seven-stage pipeline (collect, join, gate, solve, cost, order, execute), group_average_fill(), group_average_utilization(), `u* = (Sum_d l_d) / (Sum_s c_s)` (C6) -- a constant under any reassignment of…, `b_bar = (Sum_d z_d + Sum_s U^ext) / (Sum_s C_s)` (section 5.3 (C7)) -- a…, OptimizeResult, One group's MILP solve. ``breakdown``/``initial_breakdown`` are computed by the…, Solve one group with ``backend`` (``"cpsat"`` or ``"cbc"``). ``probing`` says… (+13 more)

### Community 58 - "PVE Client Reauthentication"
Cohesion: 0.26
Nodes (21): Single reauthenticate-and-retry in _call, Section 13's startup scan. Returns the vmids to exclude from this run's…, reconcile_inflight(), PveClient, One method per IMPLEMENTATION_PLAN.md section 3.5 endpoint. ``api`` is typed…, State, The same in-flight move already recorded in state.json also shows up in the…, Startup crash/two-instance recovery. See proxmox_storage_drs/crashrecovery.py. (+13 more)

### Community 59 - "Recording Clients"
Cohesion: 0.17
Nodes (17): Recording clients wrap the real clients, _build_manifest(), CallRecord, capture_bundle(), _capture_prometheus_files(), capture_range_seconds(), CaptureLog, CaptureOptions (+9 more)

### Community 60 - "Fake Prometheus Session"
Cohesion: 0.13
Nodes (20): FakePrometheusSession, A ``metrics._SessionLike`` double capable of answering *many* distinct queries…, _instant_answer(), Any, BaseException, _Raise, _range_answer(), A live capture against the dev cluster found this one directly (section 16.3's… (+12 more)

### Community 61 - "UPID and Task Status"
Cohesion: 0.14
Nodes (21): cluster/tasks vs task_status conventions differ, parse_upid PVE UPID grammar confirmed live, reconcile_inflight: recorded UPIDs plus foreign scan, AuthConfig, expected_task_user(), parse_upid(), The local half of the startup scan: re-checks every UPID ``state.json`` already…, The cluster-wide half: a still-running ``qmmove`` task from this tool's own… (+13 more)

### Community 62 - "PVE Client Internals"
Cohesion: 0.11
Nodes (11): Any, Protocol, The subset of ``requests.Response`` this module relies on., The subset of ``requests.Session`` this module relies on. A structural type…, Issue one request and return the decoded ``data`` field. Typed ``Any`` rather…, ``GET /api/v1/query``. Returns the raw ``data.result`` list., ``GET /api/v1/query_range``. Returns the raw ``data.result`` list., ``GET /api/v1/label/<name>/values``. The one endpoint whose ``data`` is a bare… (+3 more)

### Community 63 - "Agent Domain Invariants"
Cohesion: 0.17
Nodes (19): Config lives on /etc/pve; never write to it; node-local state, Enumerate every disk bus (ide, sata, scsi, virtio, efidisk0, tpmstate0, unused), VM locks are an open set; never whitelist; timeout means skip, Deprecated min_free_bytes folds in per storage after validation, Disks with snapshots are pinned, not dropped, saferemove wipe holds source volume and lock after task OK, global hard:null is a value, per-storage hard:null is inheritance, Config-to-forecast deferred import (+11 more)

### Community 64 - "API Token Auth"
Cohesion: 0.16
Nodes (18): API token permission is intersection with owner, build_client assembles auth once, build_client(), Construct a :class:`PveClient` from ``config.py``'s ``ProxmoxConfig``. Always…, _config(), _FakeProxmoxApiWithBackend, MonkeyPatch, Token auth, a non-https backend, or a future proxmoxer shape this can't reach… (+10 more)

### Community 65 - "VM Locks"
Cohesion: 0.12
Nodes (17): VM locks waited out, never whitelisted, LocksConfig, _check_lock_once(), The one live read behind section 9.3.1's lock check: the VM's current…, Section 9.3.1: any non-empty ``lock`` means wait, never whitelist a value…, _wait_for_unlocked(), Section 9.1: the pre-loop time-window check (above) only knows the answer as of…, REVIEW.md T-06's collateral bug: before the fix, this "skipped" outcome let the… (+9 more)

### Community 66 - "Repair Candidates"
Cohesion: 0.15
Nodes (18): _RepairCandidate, _best_of(), _best_repair_candidate(), _descend(), storage_of(), _movable_disks(), Assignment, `D^mov` (section 5.3): disks (C2) has not fixed in place. A pinned disk's… (+10 more)

### Community 67 - "Auto Re-plan and Payback Gate"
Cohesion: 0.12
Nodes (19): Auto re-plan loop bounded by max_replans_per_run, _apply_payback_gate(), ConfirmCallback, datetime, InflightCallback, The two section 7.3 per-move exclusions -- the hard duration rule…, Section 7.3's payback verdict gates *execution*, not merely the report…, The host's local time, DST-aware across date arithmetic when possible -- reads… (+11 more)

### Community 68 - "Snapshot Sanitizing"
Cohesion: 0.15
Nodes (19): filter_allowed_fields(), Drop every key of ``obj`` not in ``allowed``. The one primitive both the…, The one meaningful value a snapshot ``name`` field can carry is the literal…, sanitize_snapshot_name(), _anonymize_cluster_tasks(), _anonymize_node_list(), _anonymize_storage_content(), _anonymize_storage_definitions() (+11 more)

### Community 69 - "Guarded Recording Wrapper"
Cohesion: 0.25
Nodes (5): _guarded(), Any, Run ``fn()``, recording its outcome in ``log``. Returns ``None`` (and records…, Wraps a real, already-authenticated :class:`PveClient` and records every call's…, RecordingPveClient

### Community 70 - "Group Aggregate Series"
Cohesion: 0.12
Nodes (18): group_aggregate_series(), Sum every disk's own series into one group-aggregate series, at the union of…, LogCaptureFixture, 101:scsi0 has no sample at t=1 at all -- that timestamp still appears (from…, Forecasters and the section 10.1 required-range rule., test_build_forecaster_unknown_model_raises(), test_group_aggregate_series_empty_input_is_empty(), test_group_aggregate_series_missing_disk_at_a_timestamp_contributes_zero() (+10 more)

### Community 71 - "Config Building"
Cohesion: 0.12
Nodes (18): _build_config(), FreeSpaceConfig, FreeSpaceValue, HoltWintersConfig, MonitoringConfig, _parse_free_space_value(), One parsed-but-unresolved ``free_space.soft``/``.hard`` entry (section 5.3.1's…, Parse one ``free_space.soft``/``.hard`` entry (section 5.3.1's grammar).… (+10 more)

### Community 72 - "Backtest Gate"
Cohesion: 0.15
Nodes (16): Backtest validation gate for seasonal models, _backtest_gated_forecaster(), TimeSeries, Section 7.3's saturation guard needs a forecaster and every disk's own load…, Section 10.2/phase 9's backtest validation gate: ``quantile`` itself is never…, _saturation_forecast_inputs(), backtest_validated(), Forecaster (+8 more)

### Community 73 - "VM Config Filtering"
Cohesion: 0.13
Nodes (16): MappingType, filter_disk_value_params(), filter_vm_config_fields(), filter_vm_pending_entries(), Any, The allowlisted subset of a disk value's ``key=value`` parameters…, ``VM_CONFIG_EXTRA_FIELDS`` plus every disk key matching…, Section 3.8/16.3: reduce ``vm_pending()``'s response to the one boolean signal… (+8 more)

### Community 74 - "Git and Docs Workflow"
Cohesion: 0.18
Nodes (15): Merge to main with --no-ff only when make check is green, AGENTS.md working agreement, Three documentation audiences: internals, manual, terminal, Dry-run is the default, A finished task is not a finished move, make check loop (fmt, lint, typecheck, test, fixtures, pdf-check), Executable name pve-storage-drs (never drs or pve-drs), Never auto-delete a volume (+7 more)

### Community 75 - "Drift History"
Cohesion: 0.17
Nodes (15): Drift history reaches the gates via last_balance, LastBalance, load_vector_for_group(), ``at`` is ``None`` before any run has ever executed a migration -- distinct…, This group's slice of ``last_balance.load_vector``, re-keyed from…, Pure: a new :class:`State` with ``group_name``'s slice of…, with_recorded_balance(), Distinct from `{}` -- `gates.py`'s `last_load=None` means "no such run has ever… (+7 more)

### Community 76 - "Human and JSON Rendering"
Cohesion: 0.15
Nodes (14): Any, _render_collect_testdata_human(), _render_show_load_human(), _render_show_load_json(), _render_verify_storages_human(), _render_verify_storages_json(), _source_suffix(), CaptureEstimate (+6 more)

### Community 77 - "Node Selector"
Cohesion: 0.13
Nodes (15): build_node_selector(), _escape_promql_regex_literal(), Escape one literal string for safe use inside a PromQL/RE2 ``=~`` alternation.…, Section 3.4's auto-derived node-scoping filter: ``<node_label>=~"n1|n2|..."``…, The one selector every query in this module inserts, resolved once per run…, resolve_node_selector(), A node named `pve1.example.com` must match only that exact string in RE2 -- an…, `metrics.extra_selector` wins outright, even over a real node list -- the… (+7 more)

### Community 78 - "State File Parsing"
Cohesion: 0.13
Nodes (15): LockInfo, _parse_state_text(), Any, Raises on any shape this module does not recognize -- the caller…, The tolerant-parse half of :func:`load_state`, factored out so…, Writes ``state`` **in place** into the already-open, already-locked ``fd`` --…, Re-reads whatever is currently written through an already-open,…, Descriptive only -- see the module docstring's "Locking" section for why the… (+7 more)

### Community 79 - "JSON Log Formatter"
Cohesion: 0.19
Nodes (13): ast, JsonFormatter, Render one :class:`logging.LogRecord` as one JSON line., Section 2.3: "Every log record carries an ``event``" -- the event names are an…, Logging policy. See proxmox_storage_drs/logging_setup.py and…, Found live: section 7's payback ratio is `+inf` for any plan with no moves to…, _strict(), test_a_non_finite_extra_still_produces_valid_json() (+5 more)

### Community 80 - "In-flight UPIDs"
Cohesion: 0.24
Nodes (14): Inflight UPIDs written and read for crash recovery, Write UPID to disk before the crash can happen, _make_inflight_callbacks(), on_finished(), on_started(), Builds the ``on_inflight_started``/``on_inflight_finished`` pair…, LockHandle, Pure: adds ``upid`` to ``state.inflight_upids`` (a no-op if already present).… (+6 more)

### Community 81 - "Forecast Fallback"
Cohesion: 0.25
Nodes (9): Forecast, TimeSeries, _quantile(), A point estimate and an upper bound over a horizon. Both are in the same unit…, Return a point estimate and an upper bound for ``horizon``., Linear-interpolation quantile, matching ``numpy.percentile``'s default.…, test_quantile_matches_numpy_percentile_convention(), test_quantile_of_empty_sequence_raises() (+1 more)

### Community 82 - "PromQL Builders"
Cohesion: 0.14
Nodes (14): build_quantile_over_time_promql(), build_rate_promql(), _format_promql_duration(), The section 3.4 per-metric rate expression. ``sum by (vmid, device)…, Wrap a rate expression in the section 3.4 quantile-over-time reduction.…, Render a duration as a PromQL range-vector selector, e.g. ``"300s"``. Always in…, A 14-day lookback is 1209600s -- ``f"{1209600:g}s"`` renders as…, Section 3.4: the selector goes *inside* `rate()`'s own vector selector, before… (+6 more)

### Community 83 - "Content Responder Tests"
Cohesion: 0.14
Nodes (13): A `san-c` content responder plus a `move_disk` responder for 201. The listing…, 201's mirror target is already *listed* on san-c at its full 1 TiB by the time…, Between different storage types, or from thin to thick, `move_disk` allocates…, The match stays narrow: a same-VM volume that appeared after launch but has…, The exclusion is narrow: only 201's *own* mirror target (same VM, the disk's…, _run_two_onto_san_c(), _san_c_content_after_201_launches(), content() (+5 more)

### Community 84 - "Range Query Chunking"
Cohesion: 0.19
Nodes (13): Range query chunking and stitching, Range queries chunked then stitched by query text, _issue_range_chunks(), Section 16.2: chunk a long range into day-sized sub-queries, deterministically…, Merges every ``(start, end, step, result)`` capture for one query text --…, _stitch_range_captures(), Merges several ``(start, end, result)`` ``query_range`` captures of the *same*…, stitch_range_results() (+5 more)

### Community 85 - "PVE Fakes"
Cohesion: 0.22
Nodes (5): FakeProxmoxResource, FakeQueryResponse, Any, Shared test doubles. Not collected by pytest (no ``test_`` prefix).…, Matches ``metrics._ResponseLike``: ``.status_code`` and ``.json()``.

### Community 86 - "Atomic State Save"
Cohesion: 0.23
Nodes (12): ``state.path`` could not be written, or its advisory lock could not be…, StateError, Temp file in the same directory, ``fsync``, then ``os.replace`` -- a reader…, save_state_atomic(), skipif, The `finally` block's own cleanup, pinned directly rather than only inferred…, test_acquire_lock_raises_state_error_on_a_permission_failure(), test_save_state_atomic_cleans_up_its_temp_file_when_replace_fails() (+4 more)

### Community 87 - "Exception Hierarchy"
Cohesion: 0.18
Nodes (11): DrsError, ExecutionError, Exception, Base class for every error this project raises on purpose., Neither solver backend could produce a feasible or heuristic plan. See…, No pending move in a plan is individually feasible right now. See…, A migration failed, or a precondition for executing one did not hold. See…, SchedulingDeadlock (+3 more)

### Community 88 - "Fake PVE Session"
Cohesion: 0.24
Nodes (8): _FakeProxmoxApiWithSession, _FakeSession, Any, Confirmed live against a real multi-VM cluster: `requests`'s own default…, A small `read_workers` (or the field's own minimum) must not shrink the pool…, test_apply_connection_pool_size_mounts_an_adapter_sized_to_read_workers(), test_apply_connection_pool_size_never_shrinks_below_the_requests_default(), test_build_client_sizes_the_connection_pool_for_token_auth()

### Community 89 - "README Monitoring Notes"
Cohesion: 0.31
Nodes (9): Do not state unverified Proxmox behaviour, Only apply can write to the cluster, gigapipe on ClickHouse is the tested backend, Transport between InfluxDB and Prometheus can silently drop one of six counters, Metrics pipeline: PVE InfluxDB export to Prometheus-compatible backend, Quickstart Steps 0-8 (steps 7-8 migrate data), Contributing real-cluster test data bundles (collect-testdata), pve-storage-drs verify-metrics (+1 more)

### Community 90 - "Debian Packaging Rules"
Cohesion: 0.22
Nodes (9): coinor-cbc and python3-pulp are hard Depends, Source format 3.0 native, ortools optional, single pip exception in GitHub Actions, Two identities: bzed@debian.org for changelog, bernd@bzed.de elsewhere, Vendor small pure-Python deps under _vendor with licence record, Debian-first dependency policy, AGPL-3.0-or-later SPDX header and copyright holder rule, Two CI pipelines: GitHub Actions and Salsa GitLab (+1 more)

### Community 91 - "JSON Log Events"
Cohesion: 0.20
Nodes (8): JSON log event interface, LogRecord, json_safe(), One human-readable line per record: ``LEVEL: message``. Deliberately not a…, Replace every non-finite float with ``None``, recursively. Python's JSON…, TextFormatter, test_json_safe_replaces_non_finite_floats_recursively(), test_text_formatter_includes_exception_info()

### Community 92 - "Test Stdlib Imports"
Cohesion: 0.22
Nodes (8): fixture, json, logging, math, pytest, Logging policy. See IMPLEMENTATION_PLAN.md section 2.3. Every log record goes…, Shared pytest fixtures. ``logging`` is process-global state, and…, _restore_logging_state()

### Community 93 - "Documentation Agent Guide"
Cohesion: 0.25
Nodes (8): Config knob entry: type, default, unit, extremes, interactions, Tests keeping docs honest (help covers options, manual covers config), --help generated from argparse definitions, no hardcoded defaults, Internals pages: question first, name modules, explain why, ASCII diagrams, Manpage skeleton with complete OPTIONS, config/drs.example.yaml as documentation that parses, Change behaviour and documentation in the same commit, Self-contained shipped documentation rule (delete-the-reference test)

### Community 94 - "Style and Autopkgtest"
Cohesion: 0.22
Nodes (8): Autopkgtest catches missing runtime deps and top-level optional imports, black and flake8 disagreements resolved for black (E203, W503, E704), Project exception hierarchy; except Exception only at CLI boundary, Frozen slotted dataclasses for value objects, Heuristic fallback importable without any solver, No I/O in pure functions; clients behind interfaces, Structured JSON logging; print only in cli.py, Units carried in identifier names

### Community 95 - "Paper Log Check"
Cohesion: 0.28
Nodes (8): argparse, sys, check(), _logical_lines(), main(), Path, Undo the log's hard wrap at 79 columns. TeX breaks log lines mid-message, which…, Fail the paper build on LaTeX problems that silently damage the PDF. `lualatex`…

### Community 96 - "Apply Refusal Tests"
Cohesion: 0.22
Nodes (6): `quantile` (the default `forecast.model`) does no fitting at all -- there is…, `_balanced_apply_topology()`'s one move easily clears the default…, test_apply_refuses_the_whole_plan_when_the_aggregate_payback_test_fails(), test_backtest_gate_skips_validation_for_the_quantile_model(), fail(), test_real_local_now_falls_back_when_the_zone_cannot_be_resolved()

### Community 97 - "Git Workflow Guide"
Cohesion: 0.29
Nodes (6): Branch prefixes feat fix chore docs review release, Never commit config/drs.yaml, state.json, .env, venvs, Annotated tag debian/<version> on the bump commit, Subagents work on own branch or worktree; parent decides merge, Branch first, not diff-sized, Release triple: version, changelog entry, debian tag

### Community 98 - "PDF Freshness Stamp"
Cohesion: 0.33
Nodes (6): debian/rules verifies PDF sha256 stamps, does not rebuild PDFs, PDF is a build product; fix text not LaTeX, Reproducible PDF via SOURCE_DATE_EPOCH, SHA-256 stamp freshness check for plan PDF (make pdf-check), Unicode font fallback chain and check_paper_log warning-to-failure, Generated PDF/manpage freshness by SHA-256 stamp

### Community 99 - "Testing Guide"
Cohesion: 0.29
Nodes (6): .agents/ index, Acceptance fixtures fc-tier1 and reserve-tradeoff, proven by exhaustive enumeration, Coverage floor 85 percent, assertions required, pragma no cover justified, No network, no writes outside tmp_path, inject the clock, Round once at the point of writing, 85 percent coverage floor

### Community 100 - "Output Format Resolution"
Cohesion: 0.29
Nodes (5): IO, ``auto`` -> ``"text"`` at a TTY, ``"json"`` anywhere else. A person gets prose;…, resolve_format(), _FakeTTY, test_resolve_format_follows_the_destination()

### Community 101 - "Orphan Volume Detection"
Cohesion: 0.33
Nodes (6): Orphaned volumes reported, never deleted, _detect_orphan_volumes(), Section 9.4/domain rule 6: after a failed or cancelled mirror, a target volume…, test_orphan_detection_finds_only_unreferenced_volumes_of_this_vm(), test_orphan_detection_handles_a_pve_api_error_gracefully(), raise_error()

### Community 103 - "Log Level Ladder"
Cohesion: 0.50
Nodes (5): Section 2.3's ladder: ``--quiet`` < default < ``-v`` < ``-vv``. ``--log-level``…, resolve_level(), parametrize, test_log_level_wins_over_both_verbose_and_quiet(), test_resolve_level_ladder()

### Community 104 - "Anonymized Config Export"
Cohesion: 0.50
Nodes (4): _anonymize_exclude_disk_key(), _anonymized_config_dict(), Section 16.3's "the configuration in the bundle": credentials and endpoints…, ``"vmid:device"`` -- an ``exclude.disks`` entry (section 16.3), the same shape…

### Community 108 - "Metrics Expected Absent"
Cohesion: 0.67
Nodes (3): _is_metrics_expected_absent(), parametrize, test_is_metrics_expected_absent()

## Knowledge Gaps
- **29 isolated node(s):** `proxmox-storage-drs`, `run-with-system-python.sh script`, `build_paper.sh script`, `execute._move_charge_bytes`, `pve-storage-drs verify-storages` (+24 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1128 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Group` connect `PromQL Scoping and Load Blend` to `Topology and Disk Keys`, `Execute Tests and Fixtures`, `Concurrent Executor`, `Move Cost and Saturation`, `Scheduler Test Helpers`, `Gigapipe Step Workarounds`, `Empty State and Topology`, `MILP Solver Guards`, `Heuristic Evaluation`, `Gates and Imbalance`, `Execution Results`, `CLI Tests and Fake Clients`, `Confirm Callback and CLI`, `Move Wait Polling`, `Reserve Invariants Overview`, `Topology Fetch and Sizes`, `CBC and Feasibility Constraints`, `Plan Group Pipeline`, `Floors and Lexicographic Solve`, `Move Ordering`, `CLI Parser and Manual`, `Config Loading`, `Repair Scenario Tests`, `Bundle Capture Anonymization`, `Free-Space Repair`, `Pipeline and Group Utilization`, `Recording Clients`, `VM Locks`, `Repair Candidates`, `Auto Re-plan and Payback Gate`, `Backtest Gate`?**
  _High betweenness centrality (0.092) - this node is a cross-community bridge._
- **Why does `PveClient` connect `PVE Client Reauthentication` to `Topology and Disk Keys`, `Execute Tests and Fixtures`, `Concurrent Executor`, `Confirm Callback and CLI`, `Move Wait Polling`, `Reserve Invariants Overview`, `Topology Fetch and Sizes`, `CLI Handler Design`, `PVE API Errors`, `Over-provisioning Rule`, `PVE Connection Config`, `Replay Bundles`, `Test Client Factories`, `Bundle Capture Anonymization`, `Pipeline and Group Utilization`, `Recording Clients`, `UPID and Task Status`, `Agent Domain Invariants`, `API Token Auth`, `VM Locks`, `Auto Re-plan and Payback Gate`, `Guarded Recording Wrapper`, `Orphan Volume Detection`?**
  _High betweenness centrality (0.082) - this node is a cross-community bridge._
- **Why does `build_topology()` connect `Topology and Disk Keys` to `Auto Re-plan and Payback Gate`, `Time Windows and Schema Checks`, `Replay and Prometheus Config`, `CLI Handler Design`, `PromQL Scoping and Load Blend`, `Empty State and Topology`, `Persistent State Design`, `Test Client Factories`, `Bundle Capture Anonymization`, `Confirm Callback and CLI`, `Topology Fetch and Sizes`, `Pipeline and Group Utilization`, `PVE Client Reauthentication`, `Recording Clients`, `Agent Domain Invariants`, `Over-provisioning Rule`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Are the 187 inferred relationships involving `Group` (e.g. with `_accumulate_move_stats()` and `_apply_payback_gate()`) actually correct?**
  _`Group` has 187 INFERRED edges - model-reasoned connections that need verification._
- **Are the 92 inferred relationships involving `PveClient` (e.g. with `_apply_payback_gate()` and `_pve_client_for()`) actually correct?**
  _`PveClient` has 92 INFERRED edges - model-reasoned connections that need verification._
- **What connects `proxmox-storage-drs`, `run-with-system-python.sh script`, `build_paper.sh script` to the rest of the system?**
  _29 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Topology and Disk Keys` be split into smaller, more focused modules?**
  _Cohesion score 0.05247376311844078 - nodes in this community are weakly interconnected._