# Graph Report - proxmox-storage-drs  (2026-09-28)

## Corpus Check
- 24 files · ~307,330 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3806 nodes · 10462 edges · 156 communities (135 shown, 21 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 1299 edges (avg confidence: 0.93)
- Token cost: 66,346 input · 0 output

## Community Hubs (Navigation)
- CLI Apply & Statusfile Tests
- Fixture Expected Generator
- Config Loading Tests
- Internals Overview & Pipeline
- CLI Plan Rendering Tests
- Load Model Tests
- Gates & Drift Evaluation
- Heuristic Objective & Weights
- Prometheus Raw Quantities
- Agent Docs Rules
- Prometheus Client Tests
- Reserve & Capacity Gate
- CLI Fake Client Tests
- Status File Writer
- Payback Cost & Benefit
- CBC MILP Model
- Optimize Tests
- Anonymizer Tests
- Execution Config Reference
- State File & Locking
- Scheduler & Fragmentation
- Replay Bundle Reader
- Collect Testdata Tests
- Plan Decision Logging
- CLI Dispatch & Exit Codes
- Executor Move Lifecycle
- CLI Report Rendering
- Executor Tests
- Replay Tests
- Corpus Validator Tests
- Bundle Capture
- Topology Sizes & Small Disks
- PVE API Client Design
- PVE Client Tests
- Repair & Transient Checks
- State Drift & Inflight
- Raw Series Combination
- Topology Build Tests
- Concurrent Execution Tests
- Crash Recovery & Confirm
- Time Windows
- PromQL Builders
- Free-Space Repair Fixture
- Operator Manual Monitoring
- Inflight Move Tracking
- Source Release Tests
- CLI Subcommand Tests
- CLI Command Handlers
- Show-Load Tests
- Pin Reasons & Formats
- PVE API Calls
- Cross-Type Move Tests
- Safety & Config Manual
- Plan Constraints & Objective
- Config Schema & Build
- CLI Topology Stubs
- Cooldown State
- Group Storage Expansion
- Config Validation Checks
- Documentation Tests
- test_execute (27)
- test_collect (26)
- anonymize (25)
- 90-heuristic (24)
- crashrecovery (23)
- anonymize (23)
- test_logging_setup (23)
- 40-cli-and-logging (22)
- topology (22)
- test_metrics (22)
- test_collect (22)
- test_cli (22)
- test_crashrecovery (21)
- 05-metrics-pipeline (21)
- collect (21)
- test_logging_setup (20)
- test_topology (20)
- IMPLEMENTATION_PLAN (19)
- collect (19)
- units (19)
- pve-storage-drs.1 (18)
- test_forecast (18)
- cli (17)
- test_forecast (17)
- execute (17)
- cli (16)
- 29-explain (15)
- test_loadmodel (15)
- test_loadmodel (15) #2
- IMPLEMENTATION_PLAN (14)
- check_paper_log (14)
- forecast (14)
- 00-installation (14)
- 25-show-load-and-verify-storages (14)
- 28-apply (14)
- IMPLEMENTATION_PLAN (14) #2
- forecast (14) #2
- IMPLEMENTATION_PLAN (14) #3
- 10-configuration (13)
- test_forecast (13)
- fakes (13)
- IMPLEMENTATION_PLAN (12)
- anonymize (12)
- collect (12)
- 60-topology (11)
- 28-apply (11)
- IMPLEMENTATION_PLAN (11)
- IMPLEMENTATION_PLAN (11) #2
- exceptions (11)
- test_cli (11)
- 10-configuration (10)
- IMPLEMENTATION_PLAN (10)
- test_pve (10)
- test_topology (10)
- metrics (9)
- 10-configuration (9)
- 10-configuration (9) #2
- IMPLEMENTATION_PLAN (9)
- logging_setup (9)
- collect (9)
- test_execute (9)
- forecast (9)
- 10-configuration (8)
- test_execute (8)
- state (7)
- 00-installation (7)
- test_loadmodel (7)
- test_execute (7)
- 10-configuration (6)
- 26-collect-testdata-and-replay (6)
- test_state (6)
- 10-configuration (5)
- filters (5)
- test_cli (5)
- collect (4)
- test_cli (4)
- test_forecast (4)
- test_forecast (4) #2
- test_forecast (4) #3
- import-all (2)
- 28-apply (2)
- run-with-system-python (2)
- build_paper (2)
- 20-verifying-metrics (1)
- 20-verifying-metrics (1) #2
- 28-apply (1)
- IMPLEMENTATION_PLAN (1)
- misc (1)
- pyproject (1)
- misc (1) #2
- misc (1) #3
- misc (1) #4
- misc (1) #5

## God Nodes (most connected - your core abstractions)
1. `Group` - 206 edges
2. `PveClient` - 100 edges
3. `Proxmox Storage DRS Implementation Plan` - 92 edges
4. `Disk` - 85 edges
5. `write_config()` - 79 edges
6. `run()` - 72 edges
7. `client_with()` - 71 edges
8. `build_topology()` - 71 edges
9. `make_move()` - 69 edges
10. `PrometheusClient` - 68 edges

## Surprising Connections (you probably didn't know these)
- `The `Group <name> → ACT`/`NO ACTION` line` --references--> `GroupLoad`  [INFERRED]
  docs/manual/25-show-load-and-verify-storages.md → src/proxmox_storage_drs/loadmodel.py
- `What is in the file` --references--> `duration()`  [INFERRED]
  docs/manual/36-monitoring.md → tests/fixtures/generate_expected.py
- `Single reauthenticate-and-retry in _call` --references--> `PveClient`  [EXTRACTED]
  docs/internals/50-pve-api.md → src/proxmox_storage_drs/pve.py
- `staged_disks field unimplemented` --references--> `State`  [EXTRACTED]
  docs/internals/15-state.md → src/proxmox_storage_drs/state.py
- ``report`` --references--> `report()`  [INFERRED]
  docs/manual/10-configuration.md → tests/unit/test_statusfile.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Diagnostic bundle capture, anonymize, replay, audit** — implementation_plan_collect_testdata, implementation_plan_anon_allowlist, implementation_plan_pseudonym_salt, implementation_plan_bundle, implementation_plan_replay, implementation_plan_corpus, implementation_plan_scrub_audit [EXTRACTED 0.95]
- **DRS engine pipeline: gate, solve, payback, order, execute** — implementation_plan_gating, implementation_plan_milp, implementation_plan_payback_acceptance, implementation_plan_scheduling, implementation_plan_exec_modes, implementation_plan_state_json [EXTRACTED 0.95]
- **Move completion safety checks** — docs_internals_92_execute_four_condition_done, docs_internals_92_execute_vm_locks_waited_out, docs_internals_92_execute_orphans_reported_never_deleted, docs_internals_92_execute_live_transient_check_provisioned [EXTRACTED 0.95]
- **Gate, solve, order, cost planning pipeline** — docs_internals_80_gates_evaluate_group_gates, docs_internals_95_schedule_order_moves, docs_internals_96_payback_payback_verdict [EXTRACTED 0.95]
- **Reserve safety mechanism across plan, gate and execution** — implementation_plan_snapshot_reserve, implementation_plan_free_space, implementation_plan_c5_reserve, implementation_plan_lexicographic_solve, implementation_plan_reserve_override, implementation_plan_repair_exemption, implementation_plan_transient_invariant [EXTRACTED 0.95]
- **Generated acceptance fixtures for the plan** — tests_fixtures_fc_tier1_fixture, tests_fixtures_reserve_tradeoff_fixture, tests_fixtures_free_space_repair_fixture, tests_fixtures_affinity_repair_fixture [EXTRACTED 1.00]
- **Safety invariants that must not be optimised away** — agents_domain_invariants_snapshot_reserve, implementation_plan_three_floors, implementation_plan_transient_invariant, agents_domain_invariants_finished_task_not_finished_move, agents_domain_invariants_never_auto_delete, agents_domain_invariants_dry_run_default [EXTRACTED 1.00]
- **CI and quality gates enforcing the make check loop** — github_workflows_tests_tests_workflow, github_workflows_debian_package_debian_package_workflow, debian_gitlab_ci_salsa_ci_pipeline, pre_commit_config_pre_commit_hooks, codecov_yml_codecov_config [INFERRED 0.85]
- **Generated artefacts kept honest by stamps and tests** — _agents_paper_sha256_stamp, _agents_documentation_doc_tests [INFERRED 0.85]
- **Move completion: task OK, source released, VM unlocked** — docs_manual_28_apply_move_done_definition, docs_manual_28_apply_draining [INFERRED 0.85]
- **DRS engine pipeline stages** — src_proxmox_storage_drs_metrics, src_proxmox_storage_drs_pve, src_proxmox_storage_drs_topology, src_proxmox_storage_drs_loadmodel, src_proxmox_storage_drs_optimize, src_proxmox_storage_drs_payback, src_proxmox_storage_drs_schedule, src_proxmox_storage_drs_execute [EXTRACTED 1.00]
- **Reserve and free-space safety invariants** — implementation_plan_c5_reserve, implementation_plan_snapshot_reserve, implementation_plan_free_space_config, implementation_plan_transient_invariant, implementation_plan_lexicographic_solve [INFERRED 0.85]
- **Gating decides whether to act** — implementation_plan_drift_gate, implementation_plan_imbalance_gate, implementation_plan_capacity_gate, implementation_plan_cooldowns [EXTRACTED 1.00]
- **Heuristic and MILP share feasibility/objective functions** — docs_internals_90_heuristic_evaluate_assignment, docs_internals_60_topology_reserve_evaluator, docs_internals_91_optimize_shared_constraints_c1_c5, docs_internals_91_optimize_lexicographic_solve [INFERRED 0.85]
- **Unattended apply reports via status file** — docs_manual_10_configuration_monitoring_status_file, docs_internals_40_cli_and_logging_statusfile, docs_manual_36_monitoring_check_statusfile, docs_manual_36_monitoring_status_ok_warning_critical, docs_manual_36_monitoring_freshness_why_every_run_rewrites_the_file [INFERRED 0.85]
- **Storage cooldown enforcement across backends** — docs_manual_10_configuration_gates, docs_internals_90_heuristic_storage_cooldown_destination, docs_internals_91_optimize_storage_cooldown_both_stages [INFERRED 0.85]

## Communities (156 total, 21 thin omitted)

### Community 0 - "CLI Apply & Statusfile Tests"
Cohesion: 0.06
Nodes (75): CaptureFixture, _balanced_apply_group_load(), _balanced_apply_topology(), _check_statusfile(), _monitored_config(), _patch_plan_deps(), `_sample_topology()` with san-b given more headroom (16 TiB instead of 8):…, san-a violates (C5); its only movable disk is 101:scsi0 (102:scsi0 is pinned,… (+67 more)

### Community 1 - "Fixture Expected Generator"
Cohesion: 0.07
Nodes (74): The `objective:` line, itertools, StorageState, all_assignments(), best_big_m(), best_lexicographic(), big_m_agreement_threshold(), build() (+66 more)

### Community 2 - "Config Loading Tests"
Cohesion: 0.09
Nodes (70): ConfigError, The configuration file is missing, unreadable or fails validation. See…, minimal_config_dict(), Any, parametrize, Path, skipif, The smallest config that passes structural + semantic validation. (+62 more)

### Community 3 - "Internals Overview & Pipeline"
Cohesion: 0.05
Nodes (72): config.py depends on forecast.py, Module layout, Overview page, Seven-stage pipeline, Symbols D S Uext, Two solver backends, Config path resolution order, Configuration page (+64 more)

### Community 4 - "CLI Plan Rendering Tests"
Cohesion: 0.06
Nodes (64): The whole cluster's worth of groups, as seen by this run. By the time anything…, Topology, _fragmented_group(), _make_group_plan(), _moved_outcome(), _one_disk_group(), _one_move(), MoveOutcome (+56 more)

### Community 5 - "Load Model Tests"
Cohesion: 0.10
Nodes (67): LoadWeights, _blend_loads(), compute_disk_load_series(), compute_group_load(), TimeSeries, Section 4's normalize-then-weight-then-rescale blend, given every key's own…, Compute one group's :class:`GroupLoad` for this run. Section 4.…, Section 4's `ℓ_d` blend, as a time series per disk over ``[now - range_seconds,… (+59 more)

### Community 6 - "Gates & Drift Evaluation"
Cohesion: 0.07
Nodes (61): What `plan` does not yet do, GatesConfig, evaluate_group_gates(), GateDecision, _l1_drift(), Section 6, applied in the order it lists: reserve override, then the capacity…, One group's act/no-act verdict, section 6, with the reasoning shown (phase 3's…, ``(‖ℓ_last‖₁, ‖ℓ_now − ℓ_last‖₁)`` over the **union** of disk keys present in… (+53 more)

### Community 7 - "Heuristic Objective & Weights"
Cohesion: 0.08
Nodes (60): compute_vm_weights(), evaluate_assignment(), Section 5.5 step 1: "seed with the current assignment (not from scratch -- we…, Section 5.4's `w_v = max(1, l_v / l_bar)` -- the per-VM weight that scales…, Section 5.4's objective for one candidate ``assignment``.…, Section 5.5's four-step heuristic (minus "polish"; see the module docstring),…, run_heuristic(), seed_assignment() (+52 more)

### Community 8 - "Prometheus Raw Quantities"
Cohesion: 0.05
Nodes (61): MetricsConfig, MetricsError, Prometheus could not be queried, or the response was unusable. See…, _fetch_raw_quantity(), One of the six section 3.4 raw quantities, quantile-reduced over the decision…, _check_coverage(), _check_cross_metric_disk_consistency(), _check_device_label_collision() (+53 more)

### Community 9 - "Agent Docs Rules"
Cohesion: 0.05
Nodes (59): Config knob entry: type, default, unit, extremes, interactions, Tests keeping docs honest (help covers options, manual covers config), --help generated from argparse definitions, no hardcoded defaults, Internals pages: question first, name modules, explain why, ASCII diagrams, Manpage skeleton with complete OPTIONS, config/drs.example.yaml as documentation that parses, Change behaviour and documentation in the same commit, PDF is a build product; fix text not LaTeX (+51 more)

### Community 10 - "Prometheus Client Tests"
Cohesion: 0.08
Nodes (51): PrometheusClient, Thin wrapper over the Prometheus HTTP API. See section 3.4/3.5. ``session`` is…, _all_metric_names(), FakeResponse, FakeSession, _full_metrics_config(), Any, MonkeyPatch (+43 more)

### Community 11 - "Reserve & Capacity Gate"
Cohesion: 0.07
Nodes (52): dataclasses, _capacity_spread(), Section 6: decide whether to act on a group at all, before the solver runs.…, Section 5.3 (C7)'s `(max_s b_s - min_s b_s) / b_bar`, or ``None`` when the gate…, compute_reserve_status(), _current_storage(), largest_disk_bytes(), managed_used_bytes() (+44 more)

### Community 12 - "CLI Fake Client Tests"
Cohesion: 0.04
Nodes (36): str, _fake_reconcile_inflight(), _FakeClient, _NodeNamesClient, Every `apply` test here uses `build_pve_client`'s "fake-client" string stand-…, REVIEW.md R-06: `move.size_bytes == 0` must not raise `ZeroDivisionError` --…, REVIEW.md R-05: an economic failure (benefit < ratio*cost) and a hard per-move…, On a real Linux host (this project's only packaged target), the result should… (+28 more)

### Community 13 - "Status File Writer"
Cohesion: 0.09
Nodes (49): CompletedProcess, contextlib, datetime, needs_plugin, os, Storage DRS for Proxmox VE 9.2. Balances disk I/O load across configurable…, build_run_status(), _one_line() (+41 more)

### Community 14 - "Payback Cost & Benefit"
Cohesion: 0.10
Nodes (52): MigrationConfig, compute_benefit_load_seconds(), compute_move_cost(), evaluate_plan_payback(), Section 7.1's cost for one scheduled move. Only ``source`` is needed (not the…, Section 7.2: ``benefit = (alpha*(E_before - E_after) + delta*(F_before -…, Section 7.3: the aggregate acceptance test over a whole plan, plus the hard…, move() (+44 more)

### Community 15 - "CBC MILP Model"
Cohesion: 0.08
Nodes (51): _cbc_capacity_spread_term(), _cbc_feasibility_constraints(), _cbc_objective_terms(), _cbc_small_disks_follow_their_vm(), _cbc_storage_fill(), _cbc_storage_load(), _log_backend_unavailable(), _lp_variable() (+43 more)

### Community 16 - "Optimize Tests"
Cohesion: 0.10
Nodes (52): cbc_available(), make_disk(), make_storage(), LogCaptureFixture, MonkeyPatch, ObjectiveConfig, parametrize, Deliberately *not* parametrized over the skip-guarded `BACKENDS` list above --… (+44 more)

### Community 17 - "Anonymizer Tests"
Cohesion: 0.06
Nodes (43): make_mapper(), MonkeyPatch, parametrize, Path, A node and a storage that happen to share a name must not collide., Section 16.3: 'the result never depends on iteration order'., Force two different vmids to hash to the same base slot and confirm both still…, X-09: `vmid`'s own linear probing makes a collision impossible, but nothing did… (+35 more)

### Community 18 - "Execution Config Reference"
Cohesion: 0.04
Nodes (50): Configuration reference, `execution.abort_on_failure`, `execution` — how (and whether) moves actually happen, `execution.locks.on_timeout`, `execution.locks.poll_interval`, `execution.locks.task_retry_backoff`, `execution.locks.task_retry_limit`, `execution.locks.wait_timeout` (+42 more)

### Community 19 - "State File & Locking"
Cohesion: 0.11
Nodes (48): flock is the lock; JSON lock field is only a label, Reading degrades, writing raises, ``state.path`` could not be written, or its advisory lock could not be…, StateError, acquire_lock(), empty_state(), load_state(), LockInfo (+40 more)

### Community 20 - "Scheduler & Fragmentation"
Cohesion: 0.10
Nodes (44): _fragmented_vms(), Assignment, Section 3.6: name the actual pinned disk(s) keeping one VM's disks spread…, _render_fragmentation_lines(), ObjectiveConfig, order_moves(), _pending_moves(), Assignment (+36 more)

### Community 21 - "Replay Bundle Reader"
Cohesion: 0.09
Nodes (24): hash_label_name(), hash_query_text(), The cache key both this module (writing) and ``replay.py`` (reading) derive a…, BundleError, RangeStepMismatch, A diagnostic bundle (IMPLEMENTATION_PLAN.md section 16) could not be written or…, ``--replay`` found the requested range query, but at a different step than this…, bundle_reference_now() (+16 more)

### Community 22 - "Collect Testdata Tests"
Cohesion: 0.08
Nodes (44): capture(), _mapper(), Path, X-08: section 16.1's manifest line ("schema, versions, what was captured...")…, X-08: section 16.3 promises the manifest "flags" a non-node-shaped…, Z-03: `resolve_node_selector()`'s tier-1 precedence used to win on *both* sides…, A live capture against the dev cluster found the previous implementation's bug…, verify_metrics() never carries a node selector at all -- nothing to rewrite,… (+36 more)

### Community 23 - "Plan Decision Logging"
Cohesion: 0.07
Nodes (44): What this build actually implements, GatesConfig, _log_gate_decision(), _log_load_digest(), _log_payback_verdict(), _log_plan_selected(), _objective_breakdown_json(), _plan_group() (+36 more)

### Community 24 - "CLI Dispatch & Exit Codes"
Cohesion: 0.07
Nodes (44): ArgumentParser, CommandHandler, shutil, _accumulate_move_stats(), _apply_exit_code(), apply_mode_override(), build_parser(), _fallback_manual_text() (+36 more)

### Community 25 - "Executor Move Lifecycle"
Cohesion: 0.09
Nodes (43): Write UPID to disk before the crash can happen, _advance_pending(), _auto_budget_stop_outcome(), Clock, _confirm_decision(), _deadline_exceeded(), _drained_skip_outcome(), _estimated_duration_seconds() (+35 more)

### Community 26 - "CLI Report Rendering"
Cohesion: 0.10
Nodes (45): ExecutionResult, GateDecision, PaybackResult, ScheduleResult, _load_per_tib(), _pin_action_hint(), _pinned_disks(), GroupLoad (+37 more)

### Community 27 - "Executor Tests"
Cohesion: 0.10
Nodes (45): client_with(), default_group(), A move missing from `move_costs_by_key` is never refused for lack of an…, Section 13: `state.json` must learn about a UPID *before* this function goes on…, Not only the happy path -- a `move_disk` task that itself fails still finished…, `dry-run` never calls `move_disk` at all -- the callbacks must simply never…, `ExecutionConfig()`'s own defaults (both caps `1`) must dispatch to the…, IMPLEMENTATION_PLAN.md section 2.1 has always required "every `move_disk`… (+37 more)

### Community 28 - "Replay Tests"
Cohesion: 0.11
Nodes (42): PrometheusConfig, _captured_step(), _config_from_bundle(), _free_space_pairs(), MonkeyPatch, Path, AH-06: a live ``free_space`` config is collected as the resolved per-storage…, Section 16.5's one deliberate exception: a bundle captured before section 3.8… (+34 more)

### Community 29 - "Corpus Validator Tests"
Cohesion: 0.10
Nodes (43): tests_corpus, tests_corpus_validate_corpus, _case(), _invariant_inputs(), MonkeyPatch, needs_full_checkout, parametrize, Path (+35 more)

### Community 30 - "Bundle Capture"
Cohesion: 0.09
Nodes (36): functools, gzip, _build_manifest(), CallRecord, capture_bundle(), _capture_prometheus_files(), capture_range_seconds(), CaptureEstimate (+28 more)

### Community 31 - "Topology Sizes & Small Disks"
Cohesion: 0.08
Nodes (40): concurrent_futures, _provisioned_used_bytes(), Sum of every listed volume's *provisioned* size, skipping ``mirror_volids``, as…, _ClusterData, content_item_size(), _default_format(), _follows(), parse_pve_config_size_bytes() (+32 more)

### Community 32 - "PVE API Client Design"
Cohesion: 0.08
Nodes (38): The Proxmox VE API client, API token permission is intersection with owner, Best-effort ticket refresh tightening, build_client assembles auth once, bwlimit bytes/s to KiB/s conversion only in move_disk, Single reauthenticate-and-retry in _call, storage_content silently empty without Datastore.Allocate, storage_definitions uses the list form GET /storage (+30 more)

### Community 33 - "PVE Client Tests"
Cohesion: 0.08
Nodes (38): proxmoxer, fake_api(), BaseException, _FakeHttpsBackend, _FakeProxmoxApiWithBackend, _FakeTicketAuth, Section 9.2: "convert at the call site and nowhere else" -- this is that site., A ticket that expired for reasons external to this call (a long confirm-mode… (+30 more)

### Community 34 - "Repair & Transient Checks"
Cohesion: 0.08
Nodes (39): _RepairCandidate, _live_transient_check(), _LiveCheck, _move_charge_bytes(), :func:`_live_transient_check`'s result: ``refusal`` is ``None`` when the move…, ``z_m`` for section 8.1's transient invariant: the bytes this move puts on…, Section 9.2 step 2 -- section 8.1's transient invariant re-derived from *live*…, _best_of() (+31 more)

### Community 35 - "State Drift & Inflight"
Cohesion: 0.09
Nodes (40): Drift history reaches the gates via last_balance, Inflight UPIDs written and read for crash recovery, Rename-detaches-flock bug and in-place locked write, errno, fcntl, socket, LastBalance, load_vector_for_group() (+32 more)

### Community 36 - "Raw Series Combination"
Cohesion: 0.07
Nodes (40): _RawTimeSeries, _combine_raw_values(), _combined_raw(), _fetch_all_raw_quantities(), _fetch_all_raw_quantity_series(), _fetch_raw_quantity_series(), _is_metrics_expected_absent(), _issue_chunked_range_query() (+32 more)

### Community 37 - "Topology Build Tests"
Cohesion: 0.14
Nodes (41): build_topology(), datetime, State, Build the whole cluster's :class:`Topology` for this run. One pass: every read…, _cluster_client(), make_config(), Config, LogCaptureFixture (+33 more)

### Community 38 - "Concurrent Execution Tests"
Cohesion: 0.11
Nodes (33): concurrent_client_with(), datetime, The defining property of concurrency: `move_disk` for the second move is issued…, Each move's own UPID reaches both callbacks correctly attributed --…, Two otherwise-independent moves landing on the *same* target: even with…, A leftover 1 TiB volume of VM 201 already on san-c when 201 launched (an orphan…, The deliberate simplification documented in `_execute_concurrent()`'s own…, `max_migrations=1`: 201 is allowed to launch (bringing the count to the cap),… (+25 more)

### Community 39 - "Crash Recovery & Confirm"
Cohesion: 0.08
Nodes (34): ConfirmCallback, Crash and two-instance recovery: crashrecovery.py, Mutable state box narrow exception to functional style, Startup scan folds excluded vmids before planning, ExcludeConfig, ExecutionConfig, InflightCallback, LockHandle (+26 more)

### Community 40 - "Time Windows"
Cohesion: 0.15
Nodes (34): date, TimeWindow, current_deadline(), _day_name(), is_window_active(), _parse_hhmm(), datetime, ``execution.time_windows``: when ``auto`` mode may execute moves. See… (+26 more)

### Community 41 - "PromQL Builders"
Cohesion: 0.06
Nodes (25): Protocol, build_quantile_over_time_promql(), _format_promql_duration(), Any, Merges several ``(start, end, result)`` ``query_range`` captures of the *same*…, The subset of ``requests.Response`` this module relies on., The subset of ``requests.Session`` this module relies on. A structural type…, Wrap a rate expression in the section 3.4 quantile-over-time reduction.… (+17 more)

### Community 42 - "Free-Space Repair Fixture"
Cohesion: 0.10
Nodes (31): executed_assignment(), Assignment, Section 7.3: "what it will really run" -- ``final_assignment``…, Section 7.3's revert test, one verdict per scheduled move in ``order``: would…, Migration cost and the payback acceptance test. See IMPLEMENTATION_PLAN.md…, repair_markers(), `Σ_s r_s` at the assignment ``storage_of`` encodes -- section 7.3's outcome…, total_shortfall_bytes() (+23 more)

### Community 43 - "Operator Manual Monitoring"
Cohesion: 0.07
Nodes (30): Naming: pve-storage-drs, not drs, Monitoring status file (statusfile.py), Debian package install (coinor-cbc, python3-pulp Depends), verify-metrics exit status and severity levels, If it fails, Running it, Verifying your setup, What each finding means (+22 more)

### Community 44 - "Inflight Move Tracking"
Cohesion: 0.11
Nodes (32): ExcludeConfig, _inflight_onto(), _inflight_target_volids(), _InflightMove, _is_excluded_by_tag_or_vmid(), _is_mirror_target(), _launch_decision(), _launch_lock_decision() (+24 more)

### Community 45 - "Source Release Tests"
Cohesion: 0.16
Nodes (31): ExecutionConfig, SourceReleaseConfig, make_disk(), make_move(), make_storage(), Section 9.3: a source_release timeout "does not fail the run: mark the storage…, Same as above, except the second move's *target* -- not source -- is the…, Section 9.3 point 3: PVE's own `saferemove_throughput` (already read live off… (+23 more)

### Community 46 - "CLI Subcommand Tests"
Cohesion: 0.07
Nodes (29): Path, Section 13: a vmid `crashrecovery.reconcile_inflight()` reports is folded into…, Every real subcommand now has a real handler (``explain`` was the last one) so…, Section 2.3: ``run_started`` replaces ``config_loaded``, and a configuration…, A real, on-disk diagnostic bundle -- built the same way test_collect.py does,…, X-10: `--replay ... --mode auto <cmd>` used to log `run_started` and an…, Section 2.3: in text format the log record *is* the human line, so the separate…, A bug must not leave the previous run's OK in place. (+21 more)

### Community 47 - "CLI Command Handlers"
Cohesion: 0.14
Nodes (31): MetricsConfig, Namespace, _dump_report_json(), _filter_groups(), _handle_collect_testdata(), _handle_explain(), _handle_plan(), _handle_show_load() (+23 more)

### Community 48 - "Show-Load Tests"
Cohesion: 0.09
Nodes (26): _patch_show_load_deps(), _patch_show_load_forecast(), Exception, ForecastReport, MonkeyPatch, REVIEW.md AM-01: forecast-scaled loads must not pass as measured ones., A Prometheus outage must not hide the size/reserve report the rest of this…, REVIEW.md W-06/W-07: the same all-zero GroupLoad as the idle test above, but… (+18 more)

### Community 49 - "Pin Reasons & Formats"
Cohesion: 0.09
Nodes (29): Disk-cooldown pin is not exempted for reserve repair, _allowed_formats(), _pin_reason(), PVE tags as returned by `cluster/resources`: semicolon-separated, with comma…, Section 5.3 (C2): the disk formats ``storage_type`` can hold. An unrecognised…, Section 5.3 (C2)'s pin conditions, in the order the plan lists them -- the…, _split_tags(), _pair() (+21 more)

### Community 50 - "PVE API Calls"
Cohesion: 0.07
Nodes (15): Run one ``proxmoxer`` call, wrapping every failure as :class:`PveApiError`.…, ``GET /cluster/resources?type=vm``: VM inventory., ``GET /cluster/tasks``: recent/active tasks across **every** node -- the one…, ``GET /cluster/resources?type=storage``: storage inventory., ``GET /nodes``: every node in the cluster, by name. Section 3.4's node-scoping…, ``GET /version``: the running PVE's own version string (section 16.1/16.3's…, ``GET /storage``: every storage's full config, including ``saferemove``.…, ``GET /nodes/{node}/qemu/{vmid}/config``: disk -> storage mapping and size.… (+7 more)

### Community 51 - "Cross-Type Move Tests"
Cohesion: 0.10
Nodes (28): _group_with_types(), A `san-c` content responder plus a `move_disk` responder for 201. The listing…, 201's mirror target is already *listed* on san-c at its full 1 TiB by the time…, Between different storage types, or from thin to thick, `move_disk` allocates…, The match stays narrow: a same-VM volume that appeared after launch but has…, The exclusion is narrow: only 201's *own* mirror target (same VM, the disk's…, Executing a plan. See proxmox_storage_drs/execute.py. No test here talks to a…, The deviation this replaced: PVE's `used` on a thin pool (Ceph RBD, LVM-thin,… (+20 more)

### Community 52 - "Safety & Config Manual"
Cohesion: 0.11
Nodes (28): Dry-run is the default, drs.example.yaml (reference configuration), exclude rules, `execution.mode`, forecast (Holt-Winters), free_space soft/hard, gates (drift/imbalance/cooldowns), load_weights (+20 more)

### Community 53 - "Plan Constraints & Objective"
Cohesion: 0.11
Nodes (29): affinity-repair fixture, beta term: number of migrations, bwlimit is the only throttle (saturation guard removed), C1 Assignment, C3 VM affinity linking, (C6) Load spread, C7 Capacity-spread linearization, (C8) Small disks follow their VM (+21 more)

### Community 54 - "Config Schema & Build"
Cohesion: 0.12
Nodes (28): jsonschema, ruamel_yaml, ruamel_yaml_error, _build_config(), FreeSpaceConfig, FreeSpaceValue, GroupConfig, load_config() (+20 more)

### Community 55 - "CLI Topology Stubs"
Cohesion: 0.10
Nodes (26): _fake_build_topology(), X-05: cli.py used to build one bare topology (for the estimate check) and then…, A ``cli.build_topology`` stand-in that ignores the ``state``/``now`` cooldown…, Section 7.1's signed `saferemove_throughput`, end to end: the configured value…, Section 3.5 / AH-04: the resolved pair is printed with its provenance, in both…, `_sample_topology()`'s one group plus a second, empty one -- enough to prove…, `_sample_topology()` plus a section 11.4 pattern expansion and one cluster…, _sample_topology() (+18 more)

### Community 56 - "Cooldown State"
Cohesion: 0.10
Nodes (28): Persistent state: state.json, Cooldown data stored here, interpreted by topology and heuristic, staged_disks field unimplemented, _active_cooldowns(), active_disk_cooldowns(), active_storage_cooldowns(), cooldown_remaining_seconds(), Cooldowns (+20 more)

### Community 57 - "Group Storage Expansion"
Cohesion: 0.11
Nodes (28): FreeSpaceValue, GroupConfig, _build_storages(), _check_cross_group_uniqueness(), _entry_level(), _expand_and_validate_groups(), _expand_group(), _fetch_cluster_data() (+20 more)

### Community 58 - "Config Validation Checks"
Cohesion: 0.11
Nodes (28): _check_connection_config(), _check_forecast_window(), _check_group_size(), _check_group_storage_membership(), _check_metrics(), _check_objective_weights(), _check_payback_horizon(), _check_schema_version() (+20 more)

### Community 59 - "Documentation Tests"
Cohesion: 0.14
Nodes (26): importlib_resources, _flatten_schema_keys(), _load_schema(), _manpage_source_text(), _manual_documented_keys(), Any, needs_full_checkout, parametrize (+18 more)

### Community 60 - "test_execute (27)"
Cohesion: 0.11
Nodes (22): LocksConfig, MoveCost, Section 7.1's cost for one already-scheduled move., FakeClock, Section 9.1: the pre-loop time-window check (above) only knows the answer as of…, REVIEW.md T-06's collateral bug: before the fix, this "skipped" outcome let the…, Section 9.3 point 3: the very race this fix targets -- a `move_disk` task's own…, Crash recovery (section 11.2/13): a retried move is still always exactly one… (+14 more)

### Community 61 - "test_collect (26)"
Cohesion: 0.13
Nodes (26): make_config(), make_prometheus_client(), make_pve_client(), --no-series must skip the big, per-group superset range captures -- it does not…, Y-06: the manifest's version fields are machine-generated provenance, not free…, X-09: the printed query count used to treat a multi-day range as one range…, Z-05: a live capture stores every range series at…, Section 3.8/16.3: a real pending edit on the VM's own disk survives as the… (+18 more)

### Community 62 - "anonymize (25)"
Cohesion: 0.09
Nodes (22): hashlib, hmac, Allowlist-never-denylist anonymization, collect-testdata diagnostic bundle, HMAC pseudonyms with persisted random salt, _check_no_pseudonym_collision(), generate_new_salt(), load_or_create_salt() (+14 more)

### Community 63 - "90-heuristic (24)"
Cohesion: 0.10
Nodes (22): reserve.py: shared (C4)/(C5) evaluator, Internals: The heuristic solver, Descend explores swaps, evaluate_assignment(): objective separate from search, objective.spread_metric: two different quantities, Storage cooldown excludes destination, never source, Repair is unconditional, not weight-driven, w_v: kappa weighted by VM I/O, and D^big (+14 more)

### Community 64 - "crashrecovery (23)"
Cohesion: 0.15
Nodes (22): cluster/tasks vs task_status conventions differ, parse_upid PVE UPID grammar confirmed live, reconcile_inflight: recorded UPIDs plus foreign scan, AuthConfig, expected_task_user(), parse_upid(), The local half of the startup scan: re-checks every UPID ``state.json`` already…, The cluster-wide half: a still-running ``qmmove`` task from this tool's own… (+14 more)

### Community 65 - "anonymize (23)"
Cohesion: 0.09
Nodes (14): `metrics.labels.vmid`, `proxmox.auth.token_id`, pseudonym(), ``HMAC-SHA256(salt, kind || "\\0" || value)``, truncated to 8 hex chars.…, The pseudonym for a vmid already passed to :meth:`register_vmids`. ``None`` for…, ``node-<8 hex>``, or ``node-<8hex>.<8hex>.invalid`` for an FQDN -- shape…, ``user-<8 hex>@realm`` -- only ever seen inside a UPID (section 16.3). A value…, Rebuild a volume id as ``<storage-pseudonym>:<prefix>-<vmid… (+6 more)

### Community 66 - "test_logging_setup (23)"
Cohesion: 0.14
Nodes (23): configure_logging(), floor_for_command(), The mandatory ``INFO`` floor of section 2.3, or ``None``. A run that can change…, Install this run's log handler. Called once, from ``main()``. ``floor`` is…, CaptureFixture, INFO at a terminal is the narrative the operator asked for; prefixing every…, `propagate = False` on the package logger would hide every record from pytest's…, One handler, on root, with the package logger carrying only a level: a second… (+15 more)

### Community 67 - "40-cli-and-logging (22)"
Cohesion: 0.10
Nodes (19): Internals: CLI dispatch and logging, Global options on top-level parser, Command handlers dispatched via dict, JsonFormatter, Structured logs go to stderr, Log levels, mandatory floor, handler on root, --manual prefers man(1), falls back to plain text, --mode escalation rule (+11 more)

### Community 68 - "topology (22)"
Cohesion: 0.11
Nodes (22): vm_config returns pending value; vm_pending exposes both, _disk_snapshot_or_orphan_reason(), _disk_specs_from_config(), _fetch_vm(), _join_vm_disks(), _needed_content_node_pairs(), pending_disk_reasons(), Any (+14 more)

### Community 69 - "test_metrics (22)"
Cohesion: 0.14
Nodes (22): MetricLabels, WindowConfig, compute_disk_coverage(), Section 3.3 step 5 / section 3.4's ``min_coverage`` rule: per-disk sample…, test_metrics.py's own ``_StepAwareFakeClient``, restated here for…, metrics.step >= metrics.rate_window (the failing gigapipe boundary, see…, --replay backward compatibility, the raw-series counterpart of…, The BundleError fallback (see… (+14 more)

### Community 70 - "test_collect (22)"
Cohesion: 0.13
Nodes (20): FakePrometheusSession, A ``metrics._SessionLike`` double capable of answering *many* distinct queries…, _instant_answer(), Any, BaseException, _Raise, _range_answer(), A live capture against the dev cluster found this one directly (section 16.3's… (+12 more)

### Community 71 - "test_cli (22)"
Cohesion: 0.12
Nodes (17): _one_disk_group_load(), _patch_forecast_deps(), Any, LogCaptureFixture, The default model must cost nothing extra: no per-disk series fetch., test_apply_exits_quietly_when_state_json_is_already_locked(), test_apply_mode_override_deescalation_is_info(), test_apply_mode_override_escalation_warns() (+9 more)

### Community 72 - "test_crashrecovery (21)"
Cohesion: 0.21
Nodes (20): Two failure modes, one in-flight UPID mechanism, Section 13's startup scan. Returns the vmids to exclude from this run's…, reconcile_inflight(), PveClient, One method per IMPLEMENTATION_PLAN.md section 3.5 endpoint. ``api`` is typed…, The same in-flight move already recorded in state.json also shows up in the…, Startup crash/two-instance recovery. See proxmox_storage_drs/crashrecovery.py., test_reconcile_assumes_still_running_when_the_check_itself_fails() (+12 more)

### Community 73 - "05-metrics-pipeline (21)"
Cohesion: 0.10
Nodes (20): A reference implementation that is well tested, gigapipe with ClickHouse (reference backend), PVE InfluxDB external metric server, instance label collision, OpenTelemetry metric server rejected, Other backends, RRD rejected as data source, Six per-disk blockstat counters (+12 more)

### Community 74 - "collect (21)"
Cohesion: 0.18
Nodes (21): filter_allowed_fields(), Mapper, Drop every key of ``obj`` not in ``allowed``. The one primitive both the…, The stateful half of anonymization: one instance per bundle capture. ``vmid``…, _anonymize_cluster_tasks(), _anonymize_node_list(), _anonymize_storage_content(), _anonymize_storage_definitions() (+13 more)

### Community 75 - "test_logging_setup (20)"
Cohesion: 0.13
Nodes (19): ast, io, JsonFormatter, Section 2.3's ladder: ``--quiet`` < default < ``-v`` < ``-vv``. ``--log-level``…, Render one :class:`logging.LogRecord` as one JSON line., resolve_level(), parametrize, Section 2.3: "Every log record carries an ``event``" -- the event names are an… (+11 more)

### Community 76 - "test_topology (20)"
Cohesion: 0.20
Nodes (20): build_fake_client(), _content(), _one_disk_cluster(), Any, PveClient, Section 5.3 (C8): VM 301's only disk in this group is a 528 KiB efidisk0 (its…, A storage plugin can list a volid with no `size` key at all -- seen on a live…, The same content-listing gap, for a foreign (unreferenced) volume counted… (+12 more)

### Community 77 - "IMPLEMENTATION_PLAN (19)"
Cohesion: 0.15
Nodes (19): Anonymization: allowlist, never denylist; keyed pseudonyms, Migrations throttled by bwlimit only, Dependencies come from Debian (trixie), Diagnostic bundles collect-testdata, Companion fixture free-space repair mandate, free_space configuration (soft/hard floors), Holt-Winters p95 forecast with backtest gate, Implementation phases (1-14) (+11 more)

### Community 78 - "collect (19)"
Cohesion: 0.25
Nodes (5): _guarded(), Any, Run ``fn()``, recording its outcome in ``log``. Returns ``None`` (and records…, Wraps a real, already-authenticated :class:`PveClient` and records every call's…, RecordingPveClient

### Community 79 - "units (19)"
Cohesion: 0.17
Nodes (17): format_bytes(), format_duration_seconds(), parse_duration_seconds(), parse_size_bytes(), Render a duration in seconds as a human-readable string, e.g. ``"2.2h"``., Unit parsing and formatting for durations and byte sizes. ``config.py`` is the…, Parse a size into an integer byte count. Accepts a bare number (bytes) or a…, Parse a duration into seconds. Accepts a bare number (seconds) or a string like… (+9 more)

### Community 80 - "pve-storage-drs.1 (18)"
Cohesion: 0.11
Nodes (17): Three documentation artefacts (internals, manual, manpage/help), Shared pandoc PDF metadata, AUTHOR, COLLECT-TESTDATA OPTIONS, COMMANDS, CONFIGURATION, COPYRIGHT, DESCRIPTION (+9 more)

### Community 81 - "test_forecast (18)"
Cohesion: 0.18
Nodes (16): random, _group_series(), _noise_series(), TimeSeries, Holt-Winters forecasting, its backtest gate, and the required-range rule., Fewer than 2 * seasonal_periods samples before now - W: Holt-Winters cannot be…, test_backtest_fails_on_white_noise(), test_backtest_hw_error_is_none_when_the_fit_half_is_too_short() (+8 more)

### Community 82 - "cli (17)"
Cohesion: 0.14
Nodes (17): CaptureEstimate, PrometheusClient, _compute_group_load(), _log_forecast(), Any, datetime, ForecastReport, ``explain``'s one line on what the forecast did to this group's loads. (+9 more)

### Community 83 - "test_forecast (17)"
Cohesion: 0.18
Nodes (15): HoltWintersConfig, holt_winters_quantile(), ``window.quantile`` of the Holt-Winters forecast path over the next…, Any, The shipped default (288 periods at a 5m step) over the two cycles the lookback…, A diurnal series that *ends at its trough*: the last forecast point (one day…, series_of(), test_holt_winters_fits_the_default_288_periods_on_two_bursty_days() (+7 more)

### Community 84 - "execute (17)"
Cohesion: 0.12
Nodes (17): _check_lock_once(), _issue_move_disk_and_wait(), _MoveWaitState, _poll_move_once(), The one live read behind section 9.3.1's lock check: the VM's current…, Section 9.3.1: any non-empty ``lock`` means wait, never whitelist a value…, Carries :func:`_poll_move_once` state across non-blocking poll cycles -- the…, One non-blocking step of section 9.3.2's three-condition completion criterion:… (+9 more)

### Community 85 - "cli (16)"
Cohesion: 0.14
Nodes (14): MoveCost, _make_confirm_move_interactively(), confirm(), ScheduledMove, Section 5.3's "report any residual `r_s > 0` prominently as an unfixable…, The human form of :class:`_UnfixableShortfall` -- printed whether or not the…, Builds ``execute.py``'s ``ConfirmCallback`` -- the only ``input()`` call in…, Section 7.3's hard per-move duration rule (``rejected_moves``) rendered as… (+6 more)

### Community 86 - "29-explain (15)"
Cohesion: 0.17
Nodes (11): best_single_disk_alternative(), cannot fully consolidate, -v data source: line, forecast: line, `measured load:`, `no moves made: ...` / `closest alternative: ...`, `pinned load ... ; best achievable spread given pins: ...`, `pinned (not movable this run):` (+3 more)

### Community 87 - "test_loadmodel (15)"
Cohesion: 0.15
Nodes (15): build_rate_promql(), The section 3.4 per-metric rate expression. ``sum by (vmid, device)…, _coverage_promql(), _group_selector(), _quantile_promql(), _rate_promql(), The one combined selector `compute_group_load()`/`compute_disk_load_series()`…, The exact PromQL `_fetch_raw_quantity` builds for one raw field -- computed… (+7 more)

### Community 88 - "test_loadmodel (15) #2"
Cohesion: 0.17
Nodes (8): FakeResponse, Any, _RangeStepMismatchFakeClient, A ``range_query`` stand-in that returns caller-supplied data keyed by the exact…, ``RangeStepMismatch`` (a ``--replay`` bundle captured with ``collect-testdata…, Like ``_StepAwareFakeClient``, but raises ``RangeStepMismatch`` (carrying its…, test_fetch_raw_quantity_series_range_step_mismatch_fallback_fires_once_across_chunks(), _WindowTrackingFakeClient

### Community 89 - "IMPLEMENTATION_PLAN (14)"
Cohesion: 0.21
Nodes (14): Higher bar for safety-critical modules, Move completion criterion stronger than task success, Generalized concurrent-move invariant / concurrency_ok, Deadlock and staging, free_space requirement soft_s / hard_s, free-space repair fixture, free_space grammar (bytes, unit string, N%) and precedence, Move states mirroring, draining, done (+6 more)

### Community 90 - "check_paper_log (14)"
Cohesion: 0.18
Nodes (11): argparse, pathlib, re, sys, ``__version__`` and ``pyproject.toml`` must never drift apart., check(), _logical_lines(), main() (+3 more)

### Community 91 - "forecast (14)"
Cohesion: 0.14
Nodes (13): Collection, forecast_group(), ForecastReport, group_aggregate_series(), Any, Sum every disk's own series into one group-aggregate series, at the union of…, What one group's forecast did this run -- the ``forecast`` block of ``explain``…, One group's forecast: run the backtest on the group aggregate, and only if… (+5 more)

### Community 92 - "00-installation (14)"
Cohesion: 0.14
Nodes (13): API token privilege separation (intersection of ACLs), First steps after installing, Installation and requirements, Installing the package, PVE credential privileges (Datastore.Audit + Allocate), Running the timer on exactly one host, Setting up the PVE credential, Snapshot reserve (+5 more)

### Community 93 - "25-show-load-and-verify-storages (14)"
Cohesion: 0.16
Nodes (12): VM.Config.Disk and VM.Migrate privileges for apply, A negative `saferemove_throughput` is normal, Group ACT/NO ACTION gate line, Negative saferemove_throughput is normal, Reading `show-load` and `verify-storages`, `show-load`, The `Group <name> → ACT`/`NO ACTION` line, `verify-storages` (+4 more)

### Community 94 - "28-apply (14)"
Cohesion: 0.14
Nodes (13): Concurrent execution, Crash and two-instance recovery, Failure and `abort_on_failure`, `--json`, Reading `apply`, Reading `auto` mode, `state.json`: what a real run actually changes, The `[y]es/[n]o skip/[a]ll remaining/[q]uit` prompt (+5 more)

### Community 95 - "IMPLEMENTATION_PLAN (14) #2"
Cohesion: 0.20
Nodes (14): approximate-size fallback for qcow2-on-LVM volumes, (C2) Eligibility / pinning constraint, Errors are not mismatches, Which disks can move online (all buses, efidisk0, tpmstate0, unused), move_disk call and task polling, Disks with unapplied pending change pinned, Pinned disks are modelled, not ignored, Pre-move live re-validation (+6 more)

### Community 96 - "forecast (14) #2"
Cohesion: 0.21
Nodes (13): Backtest gate: beat persistence baseline, Forecasting (quantile vs holt_winters), Holt-Winters seasonal forecast (engine-side), math, ForecastConfig, Holt-Winters load forecasting. See IMPLEMENTATION_PLAN.md sections 10 and 12.1.…, The history ``forecast.model`` needs, in seconds. Called by ``config.py``'s…, required_range_seconds() (+5 more)

### Community 97 - "IMPLEMENTATION_PLAN (14) #3"
Cohesion: 0.15
Nodes (14): Per-disk blockstat via pvestatd/InfluxDB/Telegraf/Prometheus, Datastore.Allocate needed for storage content listing, Join on disk identity (vmid, device), gigapipe on ClickHouse backend, Do not switch to OpenTelemetry metric server, Do not use OpenTelemetry metric server, Prometheus per-disk blockstat, proxmoxer client with swappable backends (+6 more)

### Community 98 - "10-configuration (13)"
Cohesion: 0.15
Nodes (13): `metrics.extra_selector`, `metrics.labels.device`, `metrics.labels.node`, `metrics.pvestatd_push_interval`, `metrics.rate_window`, `metrics.read_bytes`, `metrics.read_ops`, `metrics.read_time_ns` (+5 more)

### Community 99 - "test_forecast (13)"
Cohesion: 0.31
Nodes (12): disk_factors(), ``f_d / h_d`` for every disk that has one: ``f_d`` the Holt-Winters forecast…, _factor_series(), _FixedForecast, MonkeyPatch, 96 hourly samples whose last 24 are ``window_values`` (repeated)., Patches ``holt_winters_quantile`` to a constant so the ratio is exact., test_disk_factors_is_forecast_over_observed_p95() (+4 more)

### Community 100 - "fakes (13)"
Cohesion: 0.22
Nodes (5): FakeProxmoxResource, FakeQueryResponse, Any, Shared test doubles. Not collected by pytest (no ``test_`` prefix).…, Matches ``metrics._ResponseLike``: ``.status_code`` and ``.json()``.

### Community 101 - "IMPLEMENTATION_PLAN (12)"
Cohesion: 0.17
Nodes (12): Engine pipeline: collect, join, gate, solve, cost, order, execute, Mandatory INFO audit floor for confirm/auto runs, Cooldowns (cooldown_per_disk), Structured log event catalogue, Execution modes dry-run, confirm, auto, Failure handling (orphans, partial plan, supervision loss), Logging policy (two audiences, levels, audit floor), Implementation phases 1-15 (+4 more)

### Community 102 - "anonymize (12)"
Cohesion: 0.20
Nodes (11): MappingType, filter_disk_value_params(), filter_vm_config_fields(), filter_vm_pending_entries(), Any, The allowlisted subset of a disk value's ``key=value`` parameters…, ``VM_CONFIG_EXTRA_FIELDS`` plus every disk key matching…, Section 3.8/16.3: reduce ``vm_pending()``'s response to the one boolean signal… (+3 more)

### Community 103 - "collect (12)"
Cohesion: 0.17
Nodes (12): _anonymize_captured_prometheus(), _anonymize_prometheus_series(), _anonymize_query_text(), _label_kind_for(), _label_value_for(), _parse_step_param(), Rewrites captured PromQL text so it matches what a ``--replay`` run…, Turns every ``(path, params, raw response)`` :class:`RecordingPrometheusClient`… (+4 more)

### Community 104 - "60-topology (11)"
Cohesion: 0.18
Nodes (10): Internals: Building the disk/storage/group model, (C2) format eligibility: storage_type/allowed_formats, D: every disk placed, pinned or not, Foreign usage U^ext (unreferenced volumes), free_space soft_s/hard_s resolution, Pending-change pin, Per-disk cooldown pin, Pin priority: _pin_reason() (+2 more)

### Community 105 - "28-apply (11)"
Cohesion: 0.20
Nodes (11): Transient reserve invariant, Concurrent execution with strict FIFO launch, confirm prompt [y]es/[n]o/[a]ll/[q]uit, apply modes: dry-run, confirm, auto, Pre-flight live re-check before each move, auto re-plan loop, Decision trail events, --log-format text vs json (+3 more)

### Community 106 - "IMPLEMENTATION_PLAN (11)"
Cohesion: 0.25
Nodes (11): Big-M penalty P fallback (computed P_min), C4 Largest-disk linearization, C5 Capacity, snapshot reserve and free space, Failure modes and safety table, Companion fixture reserve-tradeoff, Lexicographic solve (default), Overarching rule: reserve never traded against balance, Snapshot reserve (2x largest disk, f_s*Z_s) (+3 more)

### Community 107 - "IMPLEMENTATION_PLAN (11) #2"
Cohesion: 0.20
Nodes (11): capability_weight c_s and utilization u_s, Drift gate, Forecast scales l_d by f_d/h_d, gigapipe step >= range workaround, Average in-flight I/O requests unit, Load model l_d (average in-flight I/O), Never treat missing data as zero load (min_coverage), Cluster-node scoping of PromQL queries (extra_selector / node regex) (+3 more)

### Community 108 - "exceptions (11)"
Cohesion: 0.24
Nodes (10): DrsError, ExecutionError, Exception, Base class for every error this project raises on purpose., Exception hierarchy for the project. Every error the tool can raise…, Neither solver backend could produce a feasible or heuristic plan. See…, No pending move in a plan is individually feasible right now. See…, A migration failed, or a precondition for executing one did not hold. See… (+2 more)

### Community 109 - "test_cli (11)"
Cohesion: 0.22
Nodes (11): _imbalanced_group_load(), _no_reserve_violation_topology(), GroupLoad, Two storages, generously sized -- unlike `_sample_topology()`, no (C4)/(C5)…, san-a all the load, san-b none -- imbalance is 200% of `u*`, far above the…, Baseline for the next test: with no `state.json` at all, `last_load` is `None`,…, The same fixture as above, except `state.json` now records a `last_balance`…, Same drift-suppression scenario as `show-load`'s, through `plan` -- the two… (+3 more)

### Community 110 - "10-configuration (10)"
Cohesion: 0.20
Nodes (10): `proxmox.auth.password`, `proxmox.auth.token_secret`, `proxmox.auth.username`, `proxmox.ca_file`, `proxmox.host`, `proxmox.port`, `proxmox.read_workers`, `proxmox` — the cluster API connection (+2 more)

### Community 111 - "IMPLEMENTATION_PLAN (10)"
Cohesion: 0.20
Nodes (10): Diagnostic bundle directory format, Configuration /etc/pve/drs.yaml, tests/corpus and scrub audit, Global command-line options, Mode override logging (escalation is a warning), --replay global option, Requirements traceability (knob -> formula), Corpus scrub audit (+2 more)

### Community 112 - "test_pve (10)"
Cohesion: 0.24
Nodes (7): _FakeProxmoxApiWithSession, _FakeSession, Any, Confirmed live against a real multi-VM cluster: `requests`'s own default…, A small `read_workers` (or the field's own minimum) must not shrink the pool…, test_apply_connection_pool_size_mounts_an_adapter_sized_to_read_workers(), test_apply_connection_pool_size_never_shrinks_below_the_requests_default()

### Community 113 - "test_topology (10)"
Cohesion: 0.24
Nodes (10): _one_vm_two_storage_cluster(), Section 5.3.1: ``hard_s > soft_s`` is a validation error -- a floor above the…, Section 5.3.1: ``soft_s >= C_s`` is a validation error -- a requirement no disk…, Section 3.5: ``verify-storages`` shows the resolved pair *with the level each…, _sources(), test_build_topology_rejects_a_hard_floor_above_its_resolved_soft(), test_build_topology_rejects_a_soft_floor_not_below_capacity(), test_free_space_provenance_global_percent_without_a_hard() (+2 more)

### Community 114 - "metrics (9)"
Cohesion: 0.22
Nodes (9): node_names uses GET /nodes, build_node_selector(), _escape_promql_regex_literal(), Escape one literal string for safe use inside a PromQL/RE2 ``=~`` alternation.…, Section 3.4's auto-derived node-scoping filter: ``<node_label>=~"n1|n2|..."``…, A node named `pve1.example.com` must match only that exact string in RE2 -- an…, test_build_node_selector_empty_list_is_none(), test_build_node_selector_escapes_dots_in_an_fqdn() (+1 more)

### Community 115 - "10-configuration (9)"
Cohesion: 0.22
Nodes (9): `migration.account_saferemove_wipe`, `migration.bwlimit_bytes_per_sec`, `migration` — cost, bandwidth and the payback rule, `migration.max_single_move_duration`, `migration.payback_horizon`, `migration.payback_ratio`, `migration.source_load_weight`, `migration.target_load_weight` (+1 more)

### Community 116 - "10-configuration (9) #2"
Cohesion: 0.22
Nodes (9): `objective.affinity_counts_pinned_disks`, `objective.alpha_spread`, `objective.beta_move_count`, `objective.delta_capacity_spread`, `objective.gamma_move_bytes_per_tib`, `objective.kappa_vm_affinity`, `objective.reserve_violation_penalty`, `objective.spread_metric` (+1 more)

### Community 117 - "IMPLEMENTATION_PLAN (9)"
Cohesion: 0.25
Nodes (9): Autopkgtest install-with-only-Depends check, CBC via PuLP MILP backend, CP-SAT ortools backend removed (AL-02), Debian-first dependency policy, Debian package and CI pipelines (GitHub Actions, Salsa), Heuristic fallback (seed, repair, descend, polish), Heuristic fallback (seed/repair/descend), Shared feasibility/objective implementation (+1 more)

### Community 118 - "logging_setup (9)"
Cohesion: 0.22
Nodes (7): LogRecord, json_safe(), One human-readable line per record: ``LEVEL: message``. Deliberately not a…, Replace every non-finite float with ``None``, recursively. Python's JSON…, TextFormatter, test_json_safe_replaces_non_finite_floats_recursively(), test_text_formatter_includes_exception_info()

### Community 119 - "collect (9)"
Cohesion: 0.22
Nodes (9): Bundle, _dump_json(), Path, Recursively sort every mapping's keys -- section 16.1: "every file is...…, Write ``bundle`` as the canonical directory form (section 16.1): sorted keys,…, A deterministic ``.tar.gz`` of ``dir_path`` (section 16.1): sorted members,…, _sorted_dict(), write_bundle_dir() (+1 more)

### Community 120 - "test_execute (9)"
Cohesion: 0.28
Nodes (9): PveApiError, The Proxmox VE API returned an error or an unusable response. See…, _detect_orphan_volumes(), Section 9.4/domain rule 6: after a failed or cancelled mirror, a target volume…, raise_error(), raise_error(), test_orphan_detection_handles_a_pve_api_error_gracefully(), raise_error() (+1 more)

### Community 121 - "forecast (9)"
Cohesion: 0.22
Nodes (8): Backtest, TimeSeries, _quantile(), One group's backtest: absolute error of each model's predicted p95 of ``[now-W,…, Section 10.2's backtest, comparing against a baseline: fit on ``[now-2W,…, Linear-interpolation quantile, matching ``numpy.percentile``'s default.…, test_quantile_matches_numpy_percentile_convention(), test_quantile_of_empty_sequence_raises()

### Community 122 - "10-configuration (8)"
Cohesion: 0.25
Nodes (8): `exclude.disks`, `exclude.include_unused_disks`, `exclude.running_only`, `exclude.skip_vms_with_snapshots`, `exclude.storages`, `exclude.tags`, `exclude.vmids`, `exclude` — what DRS never touches

### Community 123 - "test_execute (8)"
Cohesion: 0.36
Nodes (8): log_messages(), LogCaptureFixture, `execution.locks.on_timeout: skip` (the default): the locked head times out…, Rendered messages of the captured records carrying ``event``., test_a_dry_run_issues_no_move_and_logs_none(), test_concurrent_lock_timeout_with_skip_semantics_continues_to_the_next_move(), test_task_failure_marks_failed_and_detects_orphans(), test_vm_lock_timeout_with_on_timeout_skip()

### Community 124 - "state (7)"
Cohesion: 0.29
Nodes (7): State dataclass tree mirrors section 11.2 JSON, disk_state_key(), ``"<group>:<vmid>:<device>"`` (section 11.2) -- the group prefix is what keeps…, ``"<group>:<storage>"`` (section 11.2)., storage_state_key(), test_disk_state_key_matches_section_11_2_shape(), test_storage_state_key_matches_section_11_2_shape()

### Community 125 - "00-installation (7)"
Cohesion: 0.29
Nodes (7): Configuration on pmxcfs (/etc/pve/drs.yaml), Run the systemd timer on exactly one host, state.json is node-local, not on /etc/pve, `state`, state.path, Crash and two-instance recovery (inflight_upids), state.json updates after a real run

### Community 126 - "test_loadmodel (7)"
Cohesion: 0.43
Nodes (7): apply_forecast(), Section 12.1 point 2: scale each disk's ``l_d`` by its forecast factor ``f_d /…, _forecast_fixture(), test_apply_forecast_leaves_idle_and_no_series_matched_alone(), test_apply_forecast_never_scales_a_flagged_disk_even_if_a_factor_is_given(), test_apply_forecast_scales_only_disks_with_a_factor_and_rebuilds_the_totals(), test_apply_forecast_with_no_factors_is_the_identity()

### Community 127 - "test_execute (7)"
Cohesion: 0.29
Nodes (7): parametrize, An API error re-reading the VM is not a mismatch re-planning can cure: the move…, A PVE API error while re-reading the target refuses the move and fails the run…, test_live_transient_check_fails_safe_when_the_live_read_errors(), test_move_charge_bytes_rule(), test_preflight_vm_config_fetch_error_fails_the_run(), raise_error()

### Community 128 - "10-configuration (6)"
Cohesion: 0.33
Nodes (6): `groups[].name`, `groups` — storage groups, `groups[].storages[].capability_weight`, `groups[].storages[].free_space.soft` / `groups[].storages[].free_space.hard`, `groups[].storages[].id`, `groups[].storages[].reserve_factor`

### Community 129 - "26-collect-testdata-and-replay (6)"
Cohesion: 0.33
Nodes (5): `collect-testdata`: capturing a bundle, Diagnostic bundles: `collect-testdata` and `--replay`, `--replay`: running against a bundle offline, Sending one to the project, What is in a bundle, and what is not

### Community 130 - "test_state (6)"
Cohesion: 0.33
Nodes (6): _pid_alive(), Best-effort, used only to make a "still held" log message useful to an operator…, pid 1 (init) always exists but is not ours to signal as a normal user --…, test_pid_alive_is_false_for_a_reaped_child(), test_pid_alive_is_true_for_a_process_we_cannot_signal(), test_pid_alive_is_true_for_our_own_process()

### Community 131 - "10-configuration (5)"
Cohesion: 0.40
Nodes (5): `support.bundle_dir`, `support.capture_range`, `support` — diagnostic bundles, `support.max_series_points`, `support.salt_path`

### Community 133 - "test_cli (5)"
Cohesion: 0.40
Nodes (5): _all_pinned_sample_topology(), parametrize, `_sample_topology()` with its one movable disk pinned too: san-a violates (C5)…, Section 5.3/9.5: a residual `r_s > 0` is reported prominently, with the byte…, test_plan_reports_an_unfixable_shortfall_and_the_pins_that_block_it()

### Community 134 - "collect (4)"
Cohesion: 0.50
Nodes (4): _anonymize_exclude_disk_key(), _anonymized_config_dict(), Section 16.3's "the configuration in the bundle": credentials and endpoints…, ``"vmid:device"`` -- an ``exclude.disks`` entry (section 16.3), the same shape…

### Community 135 - "test_cli (4)"
Cohesion: 0.67
Nodes (3): test_unfixable_shortfall_is_proven_only_for_an_optimal_cbc_solve(), outcome(), proven()

## Knowledge Gaps
- **212 isolated node(s):** `snapshot_reserve.factor`, ``migration.account_saferemove_wipe``, ``migration.bwlimit_bytes_per_sec``, ``migration.max_single_move_duration``, ``migration.payback_horizon`` (+207 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1376 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **21 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Group` connect `Scheduler & Fragmentation` to `CLI Apply & Statusfile Tests`, `CLI Plan Rendering Tests`, `Load Model Tests`, `Gates & Drift Evaluation`, `Heuristic Objective & Weights`, `Reserve & Capacity Gate`, `Payback Cost & Benefit`, `CBC MILP Model`, `Optimize Tests`, `Plan Decision Logging`, `CLI Dispatch & Exit Codes`, `Executor Move Lifecycle`, `CLI Report Rendering`, `Executor Tests`, `Bundle Capture`, `Topology Sizes & Small Disks`, `Repair & Transient Checks`, `Raw Series Combination`, `Topology Build Tests`, `Concurrent Execution Tests`, `Crash Recovery & Confirm`, `Free-Space Repair Fixture`, `Inflight Move Tracking`, `Source Release Tests`, `Cross-Type Move Tests`, `CLI Topology Stubs`, `test_execute (27)`, `cli (17)`, `cli (16)`, `test_loadmodel (15)`, `test_cli (11)`, `test_loadmodel (7)`?**
  _High betweenness centrality (0.098) - this node is a cross-community bridge._
- **Why does `Persistent state: state.json` connect `Cooldown State` to `crashrecovery (23)`, `Repair & Transient Checks`, `Internals Overview & Pipeline`, `State Drift & Inflight`, `Raw Series Combination`, `Crash Recovery & Confirm`, `Reserve & Capacity Gate`, `Inflight Move Tracking`, `Pin Reasons & Formats`, `State File & Locking`, `Safety & Config Manual`, `CLI Dispatch & Exit Codes`, `state (7)`, `Topology Sizes & Small Disks`?**
  _High betweenness centrality (0.087) - this node is a cross-community bridge._
- **Why does `Proxmox Storage DRS Implementation Plan` connect `IMPLEMENTATION_PLAN (19)` to `Internals Overview & Pipeline`, `Prometheus Raw Quantities`, `Agent Docs Rules`, `CBC MILP Model`, `Scheduler & Fragmentation`, `Replay Bundle Reader`, `CLI Dispatch & Exit Codes`, `Bundle Capture`, `Topology Sizes & Small Disks`, `PVE API Client Design`, `Repair & Transient Checks`, `Raw Series Combination`, `Free-Space Repair Fixture`, `Operator Manual Monitoring`, `Inflight Move Tracking`, `Plan Constraints & Objective`, `Config Schema & Build`, `anonymize (25)`, `IMPLEMENTATION_PLAN (14)`, `IMPLEMENTATION_PLAN (14) #2`, `forecast (14) #2`, `IMPLEMENTATION_PLAN (14) #3`, `IMPLEMENTATION_PLAN (12)`, `IMPLEMENTATION_PLAN (11)`, `IMPLEMENTATION_PLAN (11) #2`, `IMPLEMENTATION_PLAN (10)`, `IMPLEMENTATION_PLAN (9)`?**
  _High betweenness centrality (0.081) - this node is a cross-community bridge._
- **Are the 191 inferred relationships involving `Group` (e.g. with `_accumulate_move_stats()` and `_apply_payback_gate()`) actually correct?**
  _`Group` has 191 INFERRED edges - model-reasoned connections that need verification._
- **Are the 73 inferred relationships involving `PveClient` (e.g. with `capture_bundle()` and `reconcile_inflight()`) actually correct?**
  _`PveClient` has 73 INFERRED edges - model-reasoned connections that need verification._
- **What connects `snapshot_reserve.factor`, ``migration.account_saferemove_wipe``, ``migration.bwlimit_bytes_per_sec`` to the rest of the system?**
  _212 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `CLI Apply & Statusfile Tests` be split into smaller, more focused modules?**
  _Cohesion score 0.06388666132050254 - nodes in this community are weakly interconnected._