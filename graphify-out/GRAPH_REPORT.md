# Graph Report - proxmox-storage-drs  (2026-09-23)

## Corpus Check
- 69 files · ~157,143 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 4 file(s) not represented in the graph (top: .sha256 3, .tex 1)

## Summary
- 1805 nodes · 4243 edges · 87 communities (86 shown, 1 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 567 edges (avg confidence: 0.94)
- Token cost: 66,269 input · 0 output

## Community Hubs (Navigation)
- Storage Pattern Matching
- State File & Locking
- Config Loading & Validation
- CLI Command Handlers
- Apply & Plan Rendering
- Load Model Computation
- Crash Recovery & Auth
- Config Schema Fragment A
- Execute Config & Confirmation
- Config Schema Fragment B
- Metrics Validation Checks
- Diagnostic Bundle Loading
- Config Schema Fragment C
- Structured Logging Setup
- Forecasting & Backtest Gate
- Heuristic Solver
- Plan Group Cost Logging
- Anonymization Field Filters
- Disk Pinning & Fragmentation
- MILP Solver Dispatch
- CLI Entry Point & Manual
- Config Schema Fragment D
- Execution Safety Invariants
- Gating Logic
- Snapshot Anonymization
- Prometheus Capture Pipeline
- Move Launch Decisions
- Config Schema Fragment E
- CBC Objective Terms
- Config Schema Fragment F
- Collect-Testdata Command
- Manual: Core Concepts
- Anonymization Salt & Pseudonyms
- Live-Testing Discovered Quirks
- Monitoring Status File
- Manual: Configuration Reference
- Anonymization ID Mapper
- Config Schema Fragment G
- Config Schema Fragment H
- Config Schema: Forecast Params
- Move Scheduling & Reversion
- Config Schema Fragment I
- Config Schema: Bundle Capture
- Config Schema: Top Level
- Inflight Move Callbacks
- Time Window Scheduling
- Manual: Installation & Metrics
- Migration Cost Estimation
- VM Config Field Filtering
- Domain Invariants: Safety Rules
- Packaging & CI Pipelines
- Exception Hierarchy
- PVE API Client
- Config Schema: Reserve Params
- Execute Preflight Checks
- Config Schema: Lock Handling
- Documentation Working Agreement
- Python Style & Domain Rules
- Config Schema: Concurrency Limits
- Config Schema: Free Space Block
- Config Schema: Source Release
- Plan: Table of Contents
- Config Schema: Monitoring Status
- Config Schema: Pinned Load Warning
- Replay Range Query Stitching
- Move Wait & Deadline Clock
- PVE Client Protocol Types
- Testing: Fixtures & Coverage
- Config Schema: State Path
- Payback Revert Test
- Git Workflow Rules
- Metrics Finding Redaction
- Plan: Data Acquisition
- Plan: Architecture & Logging
- Pandoc PDF Filters
- Payback Gate & Confirmation
- Payback: Plan Acceptance Test
- PromQL Query Building
- CLI Parser Construction
- Config Schema: Execution Block
- Config Schema: Locks Block
- Config Schema: Max Concurrent Migrations
- Config Schema: Max Replans
- Config Schema: Execution Mode Enum
- Config Schema: Poll Interval
- Config Schema: Poll Interval Seconds
- Config Schema: Task Retry Backoff

## God Nodes (most connected - your core abstractions)
1. `Group` - 79 edges
2. `PveClient` - 59 edges
3. `Disk` - 56 edges
4. `Mapper` - 44 edges
5. `PrometheusClient` - 39 edges
6. `_handle_apply()` - 38 edges
7. `_plan_group()` - 37 edges
8. `Config` - 35 edges
9. `_build_config()` - 34 edges
10. `ResolvedConfig` - 31 edges

## Surprising Connections (you probably didn't know these)
- `Self-contained documentation principle (section 8.0)` --semantically_similar_to--> `Section 1: Scope, goal, non-goals, operating assumptions`  [INFERRED] [semantically similar]
  .agents/documentation.md → docs/IMPLEMENTATION_PLAN.pdf
- `Anonymization: unmapped means dropped, fail closed` --references--> `Mapper`  [EXTRACTED]
  docs/internals/97-collect-and-replay.md → src/proxmox_storage_drs/anonymize.py
- `solver.backend auto cascade: cpsat -> cbc -> heuristic` --references--> `_solve_group()`  [EXTRACTED]
  docs/internals/91-optimize.md → src/proxmox_storage_drs/cli.py
- `Concurrent execution: strict FIFO launch queue over one sequential order` --references--> `execute_plan()`  [EXTRACTED]
  docs/internals/92-execute.md → src/proxmox_storage_drs/execute.py
- `Descend's whole-VM relocation candidate family` --references--> `_vm_relocation_candidates()`  [EXTRACTED]
  docs/internals/90-heuristic.md → src/proxmox_storage_drs/heuristic.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Modules that jointly enforce "the reserve is never traded against balance"** — concept_reserve_override_principle, docs_internals_80_gates, docs_internals_90_heuristic, docs_internals_91_optimize, docs_internals_96_payback [INFERRED 0.85]
- **The single transient-invariant implementation shared by planning-time ordering and live execution** — concept_transient_invariant, src_proxmox_storage_drs_reserve_transient_charge_ok, docs_internals_95_schedule, docs_internals_92_execute [INFERRED 0.80]
- **The capture/anonymize/replay diagnostic bundle pipeline** — docs_internals_97_collect_and_replay, src_proxmox_storage_drs_collect_capture_bundle, src_proxmox_storage_drs_anonymize_mapper, src_proxmox_storage_drs_replay_replaypveclient [EXTRACTED 1.00]
- **Getting metrics right: blockstat counters, transport failure mode, gigapipe reference backend, and verify-metrics as the check** — docs_manual_05_metrics_pipeline_blockstat_counters, docs_manual_05_metrics_pipeline_influxdb_transport_failure, docs_manual_05_metrics_pipeline_gigapipe, docs_manual_20_verifying_metrics_command [EXTRACTED 1.00]
- **plan/apply/explain share the identical gate-solve-schedule-payback pipeline** — docs_manual_27_plan_command, docs_manual_28_apply_command, docs_manual_29_explain_command, docs_manual_25_show_load_command [EXTRACTED 1.00]
- **The reserve/free-space floor is never traded for balance across gates, transient invariant, and payback exemption** — docs_manual_10_configuration_snapshot_reserve, docs_manual_10_configuration_free_space, docs_manual_27_transient_reserve_invariant, docs_manual_27_repair_exempt, docs_manual_30_safety_properties [EXTRACTED 1.00]
- **The three free-space floors that together define the storage safety envelope** — agents_domain_invariants_three_floors, agents_domain_invariants_snapshot_reserve, agents_domain_invariants_transient_invariant [INFERRED 0.85]
- **Shared pandoc+LaTeX documentation build pipeline behind the plan, internals and manual PDFs** — agents_paper_guide, agents_documentation_guide, docs_paper_metadata_config, docs_implementation_plan_spec [EXTRACTED 1.00]
- **Files that jointly define what 'done' means before a commit (mechanical, substantive, docs, packaging, honesty checks)** — agents_review_checklist_guide, agents_domain_invariants_guide, agents_testing_guide, agents_git_workflow_guide, agents_packaging_guide [INFERRED 0.85]
- **Status file state determination (OK / WARNING / CRITICAL / UNKNOWN)** — docs_manual_36_monitoring_status_ok, docs_manual_36_monitoring_status_warning, docs_manual_36_monitoring_status_critical, docs_manual_36_monitoring_status_unknown [EXTRACTED 1.00]
- **End-to-end monitoring integration: apply writes the status file, check_statusfile reads it, Nagios/NRPE wires it up** — docs_manual_36_monitoring_apply_command, docs_manual_36_monitoring_monitoring_status_file_config, docs_manual_36_monitoring_check_statusfile, docs_manual_36_monitoring_nagios_nrpe_wiring, docs_manual_36_monitoring_state_json [INFERRED 0.85]
- **Cases where the status file is deliberately not rewritten or fails to write** — docs_manual_36_monitoring_lock_held_case, docs_manual_36_monitoring_readonly_commands, docs_manual_36_monitoring_atomic_write, docs_manual_36_monitoring_status_file_write_failed [INFERRED 0.80]

## Communities (87 total, 1 thin omitted)

### Community 0 - "Storage Pattern Matching"
Cohesion: 0.06
Nodes (71): concurrent_futures, _check_storage_patterns_compile(), GroupConfig, is_storage_pattern(), A ``storages[].id`` value is a pattern iff it both begins and ends with ``/``…, The regular expression text of a pattern entry, its two ``/`` delimiters…, Section 11.4: every ``/…/`` pattern must compile as a Python regular…, storage_pattern_text() (+63 more)

### Community 1 - "State File & Locking"
Cohesion: 0.06
Nodes (62): errno, fcntl, socket, Section 11.2: ``last_balance``/cooldowns are "updated only after a run that…, _record_executed_moves(), ``state.path`` could not be written, or its advisory lock could not be…, StateError, acquire_lock() (+54 more)

### Community 2 - "Config Loading & Validation"
Cohesion: 0.05
Nodes (60): importlib_resources, jsonschema, re, ruamel_yaml, ruamel_yaml_error, _build_config(), _check_connection_config(), _check_forecast_window() (+52 more)

### Community 3 - "CLI Command Handlers"
Cohesion: 0.07
Nodes (55): CommandHandler, Namespace, _dump_report_json(), _filter_groups(), _handle_explain(), _handle_plan(), _handle_show_load(), _handle_verify_metrics() (+47 more)

### Community 4 - "Apply & Plan Rendering"
Cohesion: 0.08
Nodes (46): _accumulate_move_stats(), _apply_exit_code(), _GroupPlan, _handle_apply(), _log_plan_selected(), _objective_breakdown_json(), ``(max_s u_s - min_s u_s) / u*`` -- gates.py's own imbalance formula (section…, One group's worth of ``_render_plan_human()``'s report -- shared with… (+38 more)

### Community 5 - "Load Model Computation"
Cohesion: 0.08
Nodes (51): _RawTimeSeries, LoadWeights, MetricsConfig, WindowConfig, _blend_loads(), _combine_raw_values(), _combined_raw(), compute_disk_load_series() (+43 more)

### Community 6 - "Crash Recovery & Auth"
Cohesion: 0.07
Nodes (35): AuthConfig, expected_task_user(), parse_upid(), The local half of the startup scan: re-checks every UPID ``state.json`` already…, The cluster-wide half: a still-running ``qmmove`` task from this tool's own…, Section 13's startup scan. Returns the vmids to exclude from this run's…, Startup crash/two-instance recovery. See IMPLEMENTATION_PLAN.md section 13.…, The exact string PVE records as a task's ``user`` field for credentials this… (+27 more)

### Community 7 - "Config Schema Fragment A"
Cohesion: 0.04
Nodes (47): additionalProperties, properties, type, type, type, minLength, type, type (+39 more)

### Community 8 - "Execute Config & Confirmation"
Cohesion: 0.14
Nodes (41): ExcludeConfig, ExecutionConfig, MigrationConfig, _advance_pending(), _auto_budget_stop_outcome(), Clock, _confirm_decision(), _deadline_exceeded() (+33 more)

### Community 9 - "Config Schema Fragment B"
Cohesion: 0.05
Nodes (41): minLength, type, minLength, type, additionalProperties, properties, type, properties (+33 more)

### Community 10 - "Metrics Validation Checks"
Cohesion: 0.09
Nodes (33): MetricsError, Prometheus could not be queried, or the response was unusable. See…, _check_coverage(), _check_cross_metric_disk_consistency(), _check_device_label_collision(), _check_metric_names_exist(), _check_observed_spacing(), _check_sample_series() (+25 more)

### Community 11 - "Diagnostic Bundle Loading"
Cohesion: 0.11
Nodes (20): hash_label_name(), BundleError, A diagnostic bundle (IMPLEMENTATION_PLAN.md section 16) could not be written or…, bundle_reference_now(), load_manifest(), _NeverSession, _parse_step_seconds(), Any (+12 more)

### Community 12 - "Config Schema Fragment C"
Cohesion: 0.06
Nodes (40): items, type, additionalProperties, properties, type, items, minItems, type (+32 more)

### Community 13 - "Structured Logging Setup"
Cohesion: 0.06
Nodes (34): monitoring.status_file: Nagios-style OK/WARNING/CRITICAL report, contextlib, datetime, IO, json, logging, LogRecord, math (+26 more)

### Community 14 - "Forecasting & Backtest Gate"
Cohesion: 0.10
Nodes (27): Section 10.2 backtest validation gate for seasonal/holt-winters models, ForecastConfig, backtest_error(), backtest_validated(), Forecast, _holt_winters_required_range_seconds(), HoltWintersForecaster, TimeSeries (+19 more)

### Community 15 - "Heuristic Solver"
Cohesion: 0.11
Nodes (33): _RepairCandidate, _best_of(), _best_repair_candidate(), best_single_disk_alternative(), _descend(), evaluate_assignment(), storage_of(), HeuristicResult (+25 more)

### Community 16 - "Plan Group Cost Logging"
Cohesion: 0.07
Nodes (37): _backtest_gated_forecaster(), _compute_one_move_cost(), _log_gate_decision(), _log_load_digest(), _log_payback_verdict(), _plan_group(), datetime, TimeSeries (+29 more)

### Community 17 - "Anonymization Field Filters"
Cohesion: 0.13
Nodes (22): filter_allowed_fields(), Drop every key of ``obj`` not in ``allowed``. The one primitive both the…, The one meaningful value a snapshot ``name`` field can carry is the literal…, sanitize_snapshot_name(), _anonymize_cluster_tasks(), _anonymize_node_list(), _anonymize_storage_content(), _anonymize_storage_definitions() (+14 more)

### Community 18 - "Disk Pinning & Fragmentation"
Cohesion: 0.08
Nodes (36): _fragmented_vms(), _load_per_tib(), _make_confirm_move_interactively(), confirm(), _pin_action_hint(), _pinned_disks(), _pinned_load_fraction(), Assignment (+28 more)

### Community 19 - "MILP Solver Dispatch"
Cohesion: 0.11
Nodes (32): ObjectiveConfig, group_average_fill(), `b_bar = (Sum_d z_d + Sum_s U^ext) / (Sum_s C_s)` (section 5.3 (C7)) -- a…, _cbc_feasibility_constraints(), _cpsat_feasibility_constraints(), _fixed_zero_pairs(), _log_backend_unavailable(), _mib() (+24 more)

### Community 20 - "CLI Entry Point & Manual"
Cohesion: 0.08
Nodes (32): argparse, shutil, _fallback_manual_text(), Any, ``pve-storage-drs`` entry point. See IMPLEMENTATION_PLAN.md section 11.3. This…, Plain text used only when ``man(1)`` itself is unavailable. A packaged install…, ``--manual`` / ``help``: see AGENTS.md section 8.5., _render_collect_testdata_human() (+24 more)

### Community 21 - "Config Schema Fragment D"
Cohesion: 0.06
Nodes (33): type, type, exclusiveMinimum, type, exclusiveMinimum, type, properties, exclusiveMinimum (+25 more)

### Community 22 - "Execution Safety Invariants"
Cohesion: 0.14
Nodes (32): Concurrent execution: strict FIFO launch queue over one sequential order, state.json inflight_upids: local trace + cluster-wide scan, Deadlock reported, never a forced reserve-breaching move, fcntl.flock() as the real exclusion mechanism, JSON lock field as metadata, free_space soft_s/hard_s resolution and precedence, Lexicographic two-stage reserve solve (vs big-M), Live pre-move re-check counts provisioned bytes, never allocated, min_wipe_seconds: fourth completion condition for saferemove drain (+24 more)

### Community 23 - "Gating Logic"
Cohesion: 0.11
Nodes (28): dataclasses, GatesConfig, _capacity_spread(), evaluate_group_gates(), _l1_drift(), Section 6, applied in the order it lists: reserve override, then the capacity…, Section 6: decide whether to act on a group at all, before the solver runs.…, ``(‖ℓ_last‖₁, ‖ℓ_now − ℓ_last‖₁)`` over the **union** of disk keys present in… (+20 more)

### Community 24 - "Snapshot Anonymization"
Cohesion: 0.10
Nodes (27): functools, gzip, _anonymize_captured_prometheus(), _anonymize_prometheus_series(), _anonymize_query_text(), Bundle, _dump_json(), hash_query_text() (+19 more)

### Community 25 - "Prometheus Capture Pipeline"
Cohesion: 0.10
Nodes (21): CallRecord, _capture_prometheus_files(), CaptureLog, _drive_group_series(), _drive_label_values(), _group_vmid_batches(), _issue_range_chunks(), Section 16.2: chunk a long range into day-sized sub-queries, deterministically… (+13 more)

### Community 26 - "Move Launch Decisions"
Cohesion: 0.10
Nodes (28): LocksConfig, _inflight_onto(), _inflight_target_volids(), _InflightMove, _is_mirror_target(), _launch_decision(), _launch_lock_decision(), _LaunchDecision (+20 more)

### Community 27 - "Config Schema Fragment E"
Cohesion: 0.07
Nodes (27): type, minimum, type, minimum, type, minimum, type, minimum (+19 more)

### Community 28 - "CBC Objective Terms"
Cohesion: 0.12
Nodes (26): compute_vm_weights(), Section 5.4's `w_v = max(1, l_v / l_bar)` -- the per-VM weight that scales…, _assert_nonzero_when_weighted(), _assert_objective_magnitude_within_int64(), _cbc_capacity_spread_term(), _cbc_objective_terms(), _cbc_storage_fill(), _cbc_storage_load() (+18 more)

### Community 29 - "Config Schema Fragment F"
Cohesion: 0.08
Nodes (26): additionalProperties, properties, type, additionalProperties, properties, type, enum, type (+18 more)

### Community 30 - "Collect-Testdata Command"
Cohesion: 0.13
Nodes (23): _handle_collect_testdata(), Section 16.4. Always the real clients -- collect-testdata needs a live cluster…, _anonymize_exclude_disk_key(), _anonymized_config_dict(), _build_manifest(), capture_bundle(), capture_range_seconds(), CaptureEstimate (+15 more)

### Community 31 - "Manual: Core Concepts"
Cohesion: 0.14
Nodes (21): objective (solver trade-off weights), solver.backend (CP-SAT / CBC / heuristic), state.path / state.json, show-load command, verify-storages command, Bundle anonymization: salted pseudonyms, dropped free text, Diagnostic bundles: collect-testdata and --replay, collect-testdata command (+13 more)

### Community 32 - "Anonymization Salt & Pseudonyms"
Cohesion: 0.11
Nodes (18): hashlib, hmac, pathlib, _check_no_pseudonym_collision(), generate_new_salt(), load_or_create_salt(), _pseudonym_int(), Path (+10 more)

### Community 33 - "Live-Testing Discovered Quirks"
Cohesion: 0.16
Nodes (20): Anonymization: unmapped means dropped, fail closed, Datastore.Allocate vs Audit: storage_content() silent false negative, gigapipe step>=range zero-series workaround, PromQL node-scoping selector to avoid cross-cluster contamination, The pending-change pin: vm_pending vs vm_config discrepancy, saferemove_throughput sign bug: must take the magnitude, (C2) storage format eligibility: storage_type/allowed_formats, Section 11.4: /pattern/ storage id expansion and validation (+12 more)

### Community 34 - "Monitoring Status File"
Cohesion: 0.11
Nodes (20): docs/manual/10-configuration.md (referenced manual chapter), pve-storage-drs apply --mode auto, Atomic write (temp file + rename) for the status file, check_statusfile (Nagios plugin, monitoring-plugins-contrib), Monitoring: the status file (manual chapter), Freshness-by-mtime rewrite rule (why every run rewrites the status file), Lock-held run (another instance holds the lock, file left alone), execution.max_replans_per_run config key (+12 more)

### Community 35 - "Manual: Configuration Reference"
Cohesion: 0.15
Nodes (19): Configuration reference, execution.mode (dry-run / confirm / auto), forecast.model (quantile / seasonal_naive / holt_winters), free_space.soft/.hard (plan-endpoint and transient floors), gates (drift / imbalance / capacity-spread / cooldown), migration payback rule (payback_ratio, payback_horizon), saturation guard (window.upper_quantile / migration.saturation_ceiling), snapshot_reserve (the never-traded reserve floor) (+11 more)

### Community 36 - "Anonymization ID Mapper"
Cohesion: 0.17
Nodes (9): Mapper, pseudonym(), ``HMAC-SHA256(salt, kind || "\\0" || value)``, truncated to 8 hex chars.…, The stateful half of anonymization: one instance per bundle capture. ``vmid``…, The pseudonym for a vmid already passed to :meth:`register_vmids`. ``None`` for…, ``node-<8 hex>``, or ``node-<8hex>.<8hex>.invalid`` for an FQDN -- shape…, ``user-<8 hex>@realm`` -- only ever seen inside a UPID (section 16.3). A value…, Rebuild a volume id as ``<storage-pseudonym>:<prefix>-<vmid… (+1 more)

### Community 37 - "Config Schema Fragment G"
Cohesion: 0.11
Nodes (19): minimum, type, minimum, type, additionalProperties, properties, type, minimum (+11 more)

### Community 38 - "Config Schema Fragment H"
Cohesion: 0.11
Nodes (19): exclusiveMinimum, type, type, type, maximum, minimum, type, additionalProperties (+11 more)

### Community 39 - "Config Schema: Forecast Params"
Cohesion: 0.11
Nodes (18): type, exclusiveMinimum, maximum, type, lookback, min_coverage, quantile, upper_quantile (+10 more)

### Community 40 - "Move Scheduling & Reversion"
Cohesion: 0.20
Nodes (16): group_average_utilization(), `u* = (Sum_d l_d) / (Sum_s c_s)` (C6) -- a constant under any reassignment of…, IMPLEMENTATION_PLAN.md section 8.1's transient invariant, generalized to an…, transient_charge_ok(), order_moves(), _pending_moves(), Assignment, Section 8.1's transient invariant, called with the single-move set ``{disk}``… (+8 more)

### Community 41 - "Config Schema Fragment I"
Cohesion: 0.12
Nodes (17): enum, type, exclusiveMinimum, type, maximum, minimum, type, backend (+9 more)

### Community 42 - "Config Schema: Bundle Capture"
Cohesion: 0.12
Nodes (17): minLength, type, minLength, type, exclusiveMinimum, type, bundle_dir, capture_range (+9 more)

### Community 43 - "Config Schema: Top Level"
Cohesion: 0.12
Nodes (15): additionalProperties, $comment, additionalProperties, type, additionalProperties, type, properties, metrics (+7 more)

### Community 44 - "Inflight Move Callbacks"
Cohesion: 0.16
Nodes (15): _InflightStateBox, _make_inflight_callbacks(), on_finished(), on_started(), InflightCallback, A mutable box around the one field of ``state`` that `execute.execute_plan()`'s…, Builds the ``on_inflight_started``/``on_inflight_finished`` pair…, ``auto`` mode's own orchestration: section 9.1's time-window budget and section… (+7 more)

### Community 45 - "Time Window Scheduling"
Cohesion: 0.26
Nodes (13): date, TimeWindow, current_deadline(), _day_name(), is_window_active(), _parse_hhmm(), datetime, ``execution.time_windows``: when ``auto`` mode may execute moves. See… (+5 more)

### Community 46 - "Manual: Installation & Metrics"
Cohesion: 0.20
Nodes (14): Installation and requirements, Config on pmxcfs (/etc/pve/drs.yaml) is live cluster-wide instantly, PVE credential privileges (Datastore.Audit + Datastore.Allocate), Run the systemd timer on exactly one host, API token privilege separation (intersection of user and token ACLs), Where the numbers come from, and how a transport loses them, The six per-disk blockstat counters, gigapipe on ClickHouse (reference metrics backend) (+6 more)

### Community 47 - "Migration Cost Estimation"
Cohesion: 0.18
Nodes (12): _estimated_duration_seconds(), _pre_move_refusal(), ``payback.MoveCost``'s own mirror-plus-wipe estimate for ``move`` -- the same…, The outcome for a move the executor declined to start. Two different things can…, compute_move_cost(), mirror_duration_seconds(), MoveCost, Section 7.1's ``duration_mirror_d = z_d / bwlimit`` (see the module docstring's… (+4 more)

### Community 48 - "VM Config Field Filtering"
Cohesion: 0.20
Nodes (11): MappingType, filter_disk_value_params(), filter_vm_config_fields(), filter_vm_pending_entries(), Any, The allowlisted subset of a disk value's ``key=value`` parameters…, ``VM_CONFIG_EXTRA_FIELDS`` plus every disk key matching…, Section 3.8/16.3: reduce ``vm_pending()``'s response to the one boolean signal… (+3 more)

### Community 49 - "Domain Invariants: Safety Rules"
Cohesion: 0.27
Nodes (11): Dry-run is the default execution mode, Enumerate every disk bus (ide/sata/scsi/virtio/efidisk0/tpmstate0/unused*), A finished task is not a finished move, domain-invariants.md (safety rules for live disk migration), Never auto-delete a volume, Transient invariant holds during moves, not just before/after, Do not state Proxmox behaviour you have not verified, VM locks are an open set -- never whitelist lock values (+3 more)

### Community 50 - "Packaging & CI Pipelines"
Cohesion: 0.22
Nodes (11): autopkgtest as the only real runtime-dependency test, packaging.md (dependencies, Debian package, CI), Two CI pipelines: GitHub Actions (trixie containers) and GitLab/Salsa (no-network sbuild), Two git identities: bzed@debian.org for packaging, bernd@bzed.de for upstream, paper.md (PDF rendering machinery for IMPLEMENTATION_PLAN.md), Reproducible PDF builds via pinned SOURCE_DATE_EPOCH, SHA-256-based staleness prevention (make pdf / make pdf-check), Unicode font fallback chain (Gentium Book Plus -> DejaVu Sans -> Symbola) (+3 more)

### Community 51 - "Exception Hierarchy"
Cohesion: 0.24
Nodes (10): Exception, DrsError, ExecutionError, Base class for every error this project raises on purpose., Exception hierarchy for the project. Every error the tool can raise…, Neither solver backend could produce a feasible or heuristic plan. See…, No pending move in a plan is individually feasible right now. See…, A migration failed, or a precondition for executing one did not hold. See… (+2 more)

### Community 52 - "PVE API Client"
Cohesion: 0.22
Nodes (10): proxmoxer, requests, _apply_connection_pool_size(), _apply_ticket_refresh_seconds(), _build_api(), REVIEW.md P-01: wire ``proxmox.ticket_refresh_seconds`` through, best-effort.…, Proxmox VE API client. See IMPLEMENTATION_PLAN.md section 3.5. Built on…, Construct one fresh, logged-in ``proxmoxer.ProxmoxAPI``. Split out of… (+2 more)

### Community 53 - "Config Schema: Reserve Params"
Cohesion: 0.18
Nodes (11): type, minimum, type, type, count_foreign_volumes, factor, min_free_bytes, snapshot_reserve (+3 more)

### Community 54 - "Execute Preflight Checks"
Cohesion: 0.18
Nodes (11): _detect_orphan_volumes(), _is_excluded_by_tag_or_vmid(), _preflight(), _PreflightResult, ``mismatch`` is ``None`` when every section 9.2 re-check passed; ``volid``…, The vmid/tag half of `topology.py`'s own `_pin_reason()` exclusion predicate,…, Section 9.2's six re-checks, immediately before issuing one move. Re-fetches…, Section 9.4/domain rule 6: after a failed or cancelled mirror, a target volume… (+3 more)

### Community 55 - "Config Schema: Lock Handling"
Cohesion: 0.20
Nodes (10): properties, enum, type, on_timeout, task_retry_limit, wait_timeout, minimum, type (+2 more)

### Community 56 - "Documentation Working Agreement"
Cohesion: 0.22
Nodes (9): documentation.md (docs working agreement), Writing docs/internals/ (implementer documentation), Manpage skeleton (man/pve-storage-drs.1.md), Writing the operator manual (docs/manual/), Writing config/drs.example.yaml as documentation, Self-contained documentation principle (section 8.0), Tests that keep documentation honest, Relationship to the PVE 9.2 Dynamic Load Balancer (+1 more)

### Community 57 - "Python Style & Domain Rules"
Cohesion: 0.25
Nodes (9): Provisioned size, never allocated -- no over-provisioning mode, Three free-space floors and their fixed precedence (f_s.Z_s, hard_s, soft_s), ortools/CP-SAT pip-install exception in CI, The three resolved black/flake8 disagreements (E203, W503, E704), python-style.md (formatting, typing, module conventions), One implementation of every rule (MILP and heuristic share predicates), SPDX header convention on every source file, Units-in-names convention (size_bytes, duration_seconds, load_inflight) (+1 more)

### Community 58 - "Config Schema: Concurrency Limits"
Cohesion: 0.22
Nodes (9): type, properties, minimum, type, minimum, type, abort_on_failure, max_concurrent_per_storage (+1 more)

### Community 59 - "Config Schema: Free Space Block"
Cohesion: 0.22
Nodes (9): additionalProperties, $comment, properties, type, type, free_space, hard, soft (+1 more)

### Community 60 - "Config Schema: Source Release"
Cohesion: 0.22
Nodes (9): source_release, timeout, wait, additionalProperties, properties, type, exclusiveMinimum, type (+1 more)

### Community 61 - "Plan: Table of Contents"
Cohesion: 0.25
Nodes (8): Config lives on the cluster filesystem (/etc/pve/drs.yaml), never written to, Section 11: Configuration (validation rules, state.json, CLI options), Section 16: Diagnostic bundles (collect-testdata and --replay), Section 10: Forecasting (pluggable forecaster, quantile/Holt-Winters), Section 6: Gating -- deciding whether to act at all, Section 7: Migration cost and the payback rule, Section 15: Requirements traceability and config knob -> formula table, IMPLEMENTATION_PLAN.pdf -- Proxmox Storage DRS specification

### Community 62 - "Config Schema: Monitoring Status"
Cohesion: 0.25
Nodes (8): additionalProperties, $comment, properties, type, monitoring, status_file, minLength, type

### Community 63 - "Config Schema: Pinned Load Warning"
Cohesion: 0.25
Nodes (8): report, warn_pinned_load_fraction, additionalProperties, properties, type, exclusiveMinimum, maximum, type

### Community 64 - "Replay Range Query Stitching"
Cohesion: 0.25
Nodes (7): RangeStepMismatch, ``--replay`` found the requested range query, but at a different step than this…, _issue_chunked_range_query(), Any, ``client.range_query()``, issued in ``RANGE_QUERY_CHUNK_SECONDS``-sized sub-…, Merges several ``(start, end, result)`` ``query_range`` captures of the *same*…, stitch_range_results()

### Community 65 - "Move Wait & Deadline Clock"
Cohesion: 0.29
Nodes (8): _check_lock_once(), _MoveWaitState, _poll_move_once(), The one live read behind section 9.3.1's lock check: the VM's current…, Carries :func:`_poll_move_once` state across non-blocking poll cycles -- the…, One non-blocking step of section 9.3.2's three-condition completion criterion:…, Section 9.3.2's three-condition completion criterion, blocking until it…, _wait_for_move_completion()

### Community 66 - "PVE Client Protocol Types"
Cohesion: 0.29
Nodes (5): Protocol, The subset of ``requests.Response`` this module relies on., The subset of ``requests.Session`` this module relies on. A structural type…, _ResponseLike, _SessionLike

### Community 67 - "Testing: Fixtures & Coverage"
Cohesion: 0.33
Nodes (7): Snapshot reserve never traded against balance, fc-tier1 acceptance fixture, proven optimal by exhaustive enumeration, 85% line coverage floor as a smoke detector, not a target, testing.md (test layout, coverage floor, fixtures), reserve-tradeoff.yaml fixture (reserve vs balance conflict), Higher branch-coverage bar for safety-critical modules, Section 14: Worked example (fc-tier1 acceptance fixture source)

### Community 68 - "Config Schema: State Path"
Cohesion: 0.29
Nodes (7): minLength, type, path, state, additionalProperties, properties, type

### Community 69 - "Payback Revert Test"
Cohesion: 0.29
Nodes (5): executed_assignment(), Assignment, Section 7.3: "what it will really run" -- ``final_assignment``…, Section 7.3's revert test, one verdict per scheduled move in ``order``: would…, repair_markers()

### Community 70 - "Git Workflow Rules"
Cohesion: 0.33
Nodes (6): Branch-first rule, decided before touching a file, Commit often, WIP commits allowed on feature branches, git-workflow.md (branching, commits, releases), Never commit: drs.yaml, state.json, .env, .venv, build artefacts, Release process: version bump + changelog entry + annotated git tag, Delegating work to a subagent on its own branch/worktree

### Community 71 - "Metrics Finding Redaction"
Cohesion: 0.33
Nodes (6): ``verify_metrics()``'s own finding text, and this module's own call log (built…, Bundle-safe rewrite of one ``verify_metrics()`` finding message. Returns…, _redact_finding_message(), _redact_free_text(), format_cross_metric_finding(), Builds :func:`_check_cross_metric_disk_consistency`'s one finding shape from a…

### Community 72 - "Plan: Data Acquisition"
Cohesion: 0.40
Nodes (5): Disks with snapshots are excluded, loudly (pinned not dropped), Section 3: Data acquisition (Prometheus + PVE API per-disk data), gigapipe-on-ClickHouse as the dogfooded Prometheus backend, Section 3.4: PromQL queries for in-flight I/O, ops/s, bytes/s, Section 3.5: PVE API client built on proxmoxer (pve.py)

### Community 73 - "Plan: Architecture & Logging"
Cohesion: 0.40
Nodes (5): Debian-trixie-first dependency policy (rmadison check), Section 2: Architecture (DRS engine pipeline, deployment, CI, logging), Section 2.3: Structured logging policy (two audiences, event catalogue), Module layout table (config.py, metrics.py, pve.py, topology.py, loadmodel.py, forecast.py, optimize.py, heuristic.py, payback.py, schedule.py, execute.py, anonymize.py, collect.py, replay.py, cli.py), Section 2.4: Monitoring status file (check_statusfile Nagios format)

### Community 75 - "Payback Gate & Confirmation"
Cohesion: 0.40
Nodes (5): _apply_payback_gate(), ConfirmCallback, The two section 7.3 per-move exclusions -- the hard duration rule…, Section 7.3's payback verdict gates *execution*, not merely the report…, _refused_move_outcomes()

### Community 76 - "Payback: Plan Acceptance Test"
Cohesion: 0.50
Nodes (4): Section 7 payback: hard acceptance test on the finished plan, Repair-exempt outcome trigger in payback (Σr_s falls), evaluate_plan_payback(), Section 7.3: the aggregate acceptance test over a whole plan, plus the hard…

### Community 77 - "PromQL Query Building"
Cohesion: 0.50
Nodes (4): build_quantile_over_time_promql(), _format_promql_duration(), Wrap a rate expression in the section 3.4 quantile-over-time reduction.…, Render a duration as a PromQL range-vector selector, e.g. ``"300s"``. Always in…

### Community 78 - "CLI Parser Construction"
Cohesion: 0.67
Nodes (3): ArgumentParser, build_parser(), Build the argument parser that both ``main()`` and ``--help`` run on.

### Community 79 - "Config Schema: Execution Block"
Cohesion: 0.67
Nodes (3): additionalProperties, type, execution

### Community 80 - "Config Schema: Locks Block"
Cohesion: 0.67
Nodes (3): additionalProperties, type, locks

### Community 81 - "Config Schema: Max Concurrent Migrations"
Cohesion: 0.67
Nodes (3): minimum, type, max_concurrent_migrations

### Community 82 - "Config Schema: Max Replans"
Cohesion: 0.67
Nodes (3): minimum, type, max_replans_per_run

### Community 83 - "Config Schema: Execution Mode Enum"
Cohesion: 0.67
Nodes (3): enum, type, mode

### Community 84 - "Config Schema: Poll Interval"
Cohesion: 0.67
Nodes (3): exclusiveMinimum, type, poll_interval

### Community 85 - "Config Schema: Poll Interval Seconds"
Cohesion: 0.67
Nodes (3): exclusiveMinimum, type, poll_interval_seconds

### Community 86 - "Config Schema: Task Retry Backoff"
Cohesion: 0.67
Nodes (3): task_retry_backoff, exclusiveMinimum, type

## Knowledge Gaps
- **293 isolated node(s):** `$schema`, `$comment`, `type`, `required`, `additionalProperties` (+288 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 805 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `properties` connect `Config Schema: Top Level` to `Config Schema: State Path`, `Config Schema Fragment G`, `Config Schema Fragment H`, `Config Schema Fragment A`, `Config Schema Fragment E`, `Config Schema Fragment I`, `Config Schema: Bundle Capture`, `Config Schema: Forecast Params`, `Config Schema Fragment C`, `Config Schema: Execution Block`, `Config Schema: Reserve Params`, `Config Schema: Free Space Block`, `Config Schema Fragment F`, `Config Schema: Monitoring Status`, `Config Schema: Pinned Load Warning`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Why does `PveClient` connect `Crash Recovery & Auth` to `Storage Pattern Matching`, `Live-Testing Discovered Quirks`, `Move Wait & Deadline Clock`, `CLI Command Handlers`, `Execute Config & Confirmation`, `Payback Gate & Confirmation`, `Inflight Move Callbacks`, `Diagnostic Bundle Loading`, `Anonymization Field Filters`, `CLI Entry Point & Manual`, `PVE API Client`, `Execute Preflight Checks`, `Snapshot Anonymization`, `Prometheus Capture Pipeline`, `Move Launch Decisions`, `Collect-Testdata Command`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Why does `Group` connect `Move Scheduling & Reversion` to `Storage Pattern Matching`, `CLI Command Handlers`, `Apply & Plan Rendering`, `Load Model Computation`, `Payback Revert Test`, `Execute Config & Confirmation`, `Payback Gate & Confirmation`, `Inflight Move Callbacks`, `Heuristic Solver`, `Plan Group Cost Logging`, `Disk Pinning & Fragmentation`, `MILP Solver Dispatch`, `CLI Entry Point & Manual`, `Gating Logic`, `Snapshot Anonymization`, `Prometheus Capture Pipeline`, `CBC Objective Terms`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Are the 67 inferred relationships involving `Group` (e.g. with `_accumulate_move_stats()` and `_apply_payback_gate()`) actually correct?**
  _`Group` has 67 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `PveClient` (e.g. with `_apply_payback_gate()` and `_pve_client_for()`) actually correct?**
  _`PveClient` has 30 INFERRED edges - model-reasoned connections that need verification._
- **Are the 45 inferred relationships involving `Disk` (e.g. with `_fragmented_vms()` and `_pinned_disks()`) actually correct?**
  _`Disk` has 45 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `Mapper` (e.g. with `_anonymize_captured_prometheus()` and `_anonymize_cluster_tasks()`) actually correct?**
  _`Mapper` has 25 INFERRED edges - model-reasoned connections that need verification._