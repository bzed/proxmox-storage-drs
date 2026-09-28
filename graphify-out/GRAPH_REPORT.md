# Graph Report - proxmox-storage-drs  (2026-09-28)

## Corpus Check
- 8 files · ~0 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3844 nodes · 10525 edges · 160 communities (128 shown, 32 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 1251 edges (avg confidence: 0.93)
- Token cost: 164,182 input · 0 output

## Community Hubs (Navigation)
- Executor Move Lifecycle
- Topology Build Tests
- Fixture Expected Generator
- Optimize Tests
- CLI Fake Client Tests
- CLI Plan Rendering Tests
- Load Model Tests
- Config Loading Tests
- CLI Apply & Statusfile Tests
- Gates & Drift Evaluation
- Heuristic Objective & Weights
- Status File Writer
- Prometheus Raw Quantities
- Prometheus Client Tests
- Payback Cost & Benefit
- Execution Config Reference
- Executor Tests
- CLI Apply & Statusfile Tests #2
- Anonymizer Tests
- CBC MILP Model
- Replay Tests
- Reserve & Capacity Gate
- Operator Manual Monitoring
- Raw Series Combination
- CLI Topology Stubs
- Collect Testdata Tests
- PVE API Client Design
- Corpus Validator Tests
- test_metrics (22)
- Replay Bundle Reader
- CLI Dispatch & Exit Codes
- Scheduler & Fragmentation
- 90-heuristic (24)
- PVE Client Tests
- Concurrent Execution Tests
- CLI Command Handlers
- Safety & Config Manual
- IMPLEMENTATION_PLAN (19)
- CLI Report Rendering
- Time Windows
- Crash Recovery & Confirm
- Config Validation Checks
- Internals Overview & Pipeline
- Repair & Transient Checks
- anonymize (23)
- collect (19)
- collect (12)
- Free-Space Repair Fixture
- anonymize (25)
- Source Release Tests
- PVE API Calls
- CLI Report Rendering #2
- Bundle Capture
- test_logging_setup (23)
- State File & Locking
- Documentation Tests
- Plan Constraints & Objective
- Group Storage Expansion
- test_crashrecovery (21)
- Plan Decision Logging
- test_collect (26)
- Cross-Type Move Tests
- cli (17)
- crashrecovery (23)
- units (19)
- pve-storage-drs.1 (18)
- test_collect (22)
- Agent Docs Rules
- Cooldown State
- topology (22)
- Agent Docs Rules #2
- Plan Constraints & Objective #2
- IMPLEMENTATION_PLAN (14) #2
- test_forecast (18)
- Internals Overview & Pipeline #2
- test_execute (8)
- test_forecast (17)
- Agent Docs Rules #3
- test_loadmodel (15) #2
- Cooldown State #2
- State Drift & Inflight
- 25-show-load-and-verify-storages (14)
- Execution Config Reference #2
- IMPLEMENTATION_PLAN (11) #2
- Config Schema & Build
- forecast (9)
- Cooldown State #3
- Internals Overview & Pipeline #3
- 40-cli-and-logging (22)
- Agent Docs Rules #4
- State Drift & Inflight #2
- 28-apply (14)
- State File & Locking #2
- test_forecast (13)
- Pin Reasons & Formats
- fakes (13)
- test_cli (22)
- 05-metrics-pipeline (21)
- 28-apply (11)
- IMPLEMENTATION_PLAN (12)
- 40-cli-and-logging (22) #2
- Group Storage Expansion #2
- PromQL Builders
- test_execute (27)
- test_pve (10)
- check_paper_log (14)
- 10-configuration (9) #2
- 40-cli-and-logging (22) #3
- IMPLEMENTATION_PLAN (10)
- IMPLEMENTATION_PLAN (9)
- logging_setup (9)
- 00-installation (14)
- 10-configuration (8)
- PromQL Builders #2
- test_logging_setup (20)
- test_execute (7)
- Internals Overview & Pipeline #4
- State Drift & Inflight #3
- 00-installation (7)
- forecast (14) #2
- Execution Config Reference #3
- 26-collect-testdata-and-replay (6)
- cli (16)
- cli (16) #2
- forecast (14)
- Execution Config Reference #4
- filters (5)
- Show-Load Tests
- PVE Client Tests #2
- test_forecast (4)
- test_forecast (4) #2
- test_forecast (4) #3
- CLI Subcommand Tests
- CLI Subcommand Tests #2
- import-all (2)
- 28-apply (2)
- run-with-system-python (2)
- test_logging_setup (20) #2
- Prometheus Raw Quantities #2
- Prometheus Raw Quantities #3
- build_paper (2)
- 20-verifying-metrics (1)
- 20-verifying-metrics (1) #2
- 28-apply (1)
- IMPLEMENTATION_PLAN (1)
- misc (1)
- pyproject (1)
- Scheduler & Fragmentation #2
- misc (1) #3
- cli (17) #2
- misc (1) #4
- misc (1) #5
- Show-Load Tests #2
- test_cli (22) #2
- Show-Load Tests #3
- test_cli (5)
- CLI Subcommand Tests #3

## God Nodes (most connected - your core abstractions)
1. `Group` - 158 edges
2. `PveClient` - 115 edges
3. `write_config()` - 80 edges
4. `Proxmox Storage DRS Implementation Plan` - 80 edges
5. `Disk` - 74 edges
6. `run()` - 72 edges
7. `client_with()` - 71 edges
8. `make_move()` - 69 edges
9. `PrometheusClient` - 68 edges
10. `fake_api()` - 67 edges

## Surprising Connections (you probably didn't know these)
- `The `Group <name> → ACT`/`NO ACTION` line` --references--> `GroupLoad`  [INFERRED]
  docs/manual/25-show-load-and-verify-storages.md → src/proxmox_storage_drs/loadmodel.py
- `What is in the file` --references--> `duration()`  [INFERRED]
  docs/manual/36-monitoring.md → tests/fixtures/generate_expected.py
- `Single reauthenticate-and-retry in _call` --references--> `PveClient`  [EXTRACTED]
  docs/internals/50-pve-api.md → src/proxmox_storage_drs/pve.py
- `staged_disks field unimplemented` --references--> `State`  [EXTRACTED]
  docs/internals/15-state.md → src/proxmox_storage_drs/state.py
- `The `objective:` line` --references--> `spread()`  [INFERRED]
  docs/manual/29-explain.md → tests/fixtures/generate_expected.py

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
- **Gating decides whether to act** — implementation_plan_drift_gate, implementation_plan_imbalance_gate, implementation_plan_capacity_gate, implementation_plan_cooldowns [EXTRACTED 1.00]
- **Diagnostic bundle capture, anonymization and replay** — implementation_plan_diagnostic_bundles, implementation_plan_anonymization_allowlist, implementation_plan_keyed_pseudonyms, implementation_plan_replay, implementation_plan_test_corpus [EXTRACTED 1.00]
- **Engine stages collect-gate-solve-cost-order-execute** — implementation_plan_load_model, implementation_plan_gating, implementation_plan_milp_model, implementation_plan_payback_rule, implementation_plan_scheduling, implementation_plan_execution_modes [EXTRACTED 1.00]
- **Reserve and free-space floors (f_s*Z_s, hard_s, soft_s)** — implementation_plan_snapshot_reserve, implementation_plan_free_space_config, implementation_plan_c5_reserve, implementation_plan_transient_invariant, implementation_plan_free_space_repair_mandate [EXTRACTED 1.00]
- **DRS engine pipeline stages** — src_proxmox_storage_drs_metrics, src_proxmox_storage_drs_pve, src_proxmox_storage_drs_topology, src_proxmox_storage_drs_loadmodel, src_proxmox_storage_drs_optimize, src_proxmox_storage_drs_payback, src_proxmox_storage_drs_schedule, src_proxmox_storage_drs_execute [EXTRACTED 1.00]
- **CI and quality gates enforcing the make check loop** — github_workflows_tests_tests_workflow, github_workflows_debian_package_debian_package_workflow, debian_gitlab_ci_salsa_ci_pipeline, pre_commit_config_pre_commit_hooks, codecov_yml_codecov_config [INFERRED 0.85]
- **Generated artefacts kept honest by stamps and tests** — _agents_paper_sha256_stamp, _agents_documentation_doc_tests [INFERRED 0.85]
- **Unattended apply reports via status file** — implementation_plan_monitoring_status_file, docs_internals_40_cli_and_logging_statusfile, docs_manual_36_monitoring_check_statusfile, docs_manual_36_monitoring_status_ok_warning_critical, docs_manual_36_monitoring_freshness_why_every_run_rewrites_the_file [INFERRED 0.85]
- **Move completion: task OK, source released, VM unlocked** — docs_manual_28_apply_move_done_definition, docs_manual_28_apply_draining [INFERRED 0.85]
- **plan report output pipeline** — docs_manual_27_plan_solver_line, docs_manual_27_plan_payback_line, docs_internals_40_cli_and_logging_no_moves_made, docs_internals_40_cli_and_logging_unfixable_shortfall_report, docs_manual_27_plan_json_output [INFERRED 0.85]
- **Reserve/free space is never traded for balance** — docs_manual_27_plan_repair_exempt, docs_internals_95_schedule_deadlock_report, docs_internals_40_cli_and_logging_unfixable_shortfall_report, docs_manual_10_configuration_free_space, docs_manual_10_configuration_snapshot_reserve_factor [INFERRED 0.85]
- **Reserve and free-space safety invariants** — implementation_plan_c5_reserve, implementation_plan_snapshot_reserve, implementation_plan_free_space_config, implementation_plan_transient_invariant, implementation_plan_lexicographic_solve [INFERRED 0.85]
- **Heuristic and MILP share feasibility/objective functions** — docs_internals_90_heuristic_evaluate_assignment, docs_internals_60_topology_reserve_evaluator, docs_internals_91_optimize_shared_constraints_c1_c5, docs_internals_91_optimize_lexicographic_solve [INFERRED 0.85]
- **Storage cooldown enforcement across backends** — docs_manual_10_configuration_gates, docs_internals_90_heuristic_storage_cooldown_destination, docs_internals_91_optimize_storage_cooldown_both_stages [INFERRED 0.85]
- **Tiny-disk (EFI/TPM) free reunion with VM** — docs_manual_10_configuration_migration_tiny_disk_bytes, docs_internals_95_schedule_tiny_disk_first, docs_manual_27_plan_payback_line [INFERRED 0.85]

## Communities (160 total, 32 thin omitted)

### Community 0 - "Executor Move Lifecycle"
Cohesion: 0.05
Nodes (98): ExcludeConfig, _advance_pending(), _auto_budget_stop_outcome(), _check_lock_once(), Clock, _confirm_decision(), _deadline_exceeded(), _detect_orphan_volumes() (+90 more)

### Community 1 - "Topology Build Tests"
Cohesion: 0.07
Nodes (98): vm_config returns pending value; vm_pending exposes both, The cluster topology could not be built from the API responses. See…, TopologyError, disk_state_key(), ``"<group>:<vmid>:<device>"`` (section 11.2) -- the group prefix is what keeps…, build_topology(), pending_disk_reasons(), _pin_reason() (+90 more)

### Community 2 - "Fixture Expected Generator"
Cohesion: 0.06
Nodes (74): The `payback:` line, itertools, StorageState, all_assignments(), best_big_m(), best_lexicographic(), big_m_agreement_threshold(), build() (+66 more)

### Community 3 - "Optimize Tests"
Cohesion: 0.06
Nodes (79): cbc_available(), OptimizeResult, One group's MILP solve. ``breakdown``/``initial_breakdown`` are computed by the…, Solve one group with ``backend`` (``"cbc"``). ``probing`` says this backend was…, solve(), make_disk(), make_storage(), LogCaptureFixture (+71 more)

### Community 4 - "CLI Fake Client Tests"
Cohesion: 0.03
Nodes (59): LogCaptureFixture, str, _fake_reconcile_inflight(), _FakeClient, _NodeNamesClient, Every `apply` test here uses `build_pve_client`'s "fake-client" string stand-…, REVIEW.md R-06: `move.size_bytes == 0` must not raise `ZeroDivisionError` --…, REVIEW.md R-05: an economic failure (benefit < ratio*cost) and a hard per-move… (+51 more)

### Community 5 - "CLI Plan Rendering Tests"
Cohesion: 0.07
Nodes (72): Path, _fake_breakdown(), _fragmented_group(), _make_group_plan(), _moved_outcome(), _one_disk_group(), _one_disk_group_load(), _one_move() (+64 more)

### Community 6 - "Load Model Tests"
Cohesion: 0.08
Nodes (79): LoadWeights, _aggregate_storages(), apply_forecast(), compute_group_load(), Compute one group's :class:`GroupLoad` for this run. Section 4.…, Each storage's ``L_s``/``u_s`` from its disks' ``l_d``, and the group's ``u*``…, Section 12.1 point 2: scale each disk's ``l_d`` by its forecast factor ``f_d /…, Group (+71 more)

### Community 7 - "Config Loading Tests"
Cohesion: 0.09
Nodes (70): ConfigError, The configuration file is missing, unreadable or fails validation. See…, minimal_config_dict(), Any, parametrize, Path, skipif, The smallest config that passes structural + semantic validation. (+62 more)

### Community 8 - "CLI Apply & Statusfile Tests"
Cohesion: 0.07
Nodes (68): CaptureFixture, Exception, MonkeyPatch, parametrize, _patch_show_load_deps(), _patch_show_load_forecast(), ForecastReport, `_sample_topology()` with san-b given more headroom (16 TiB instead of 8):… (+60 more)

### Community 9 - "Gates & Drift Evaluation"
Cohesion: 0.07
Nodes (64): What `plan` does not yet do, GatesConfig, _capacity_spread(), evaluate_group_gates(), GateDecision, _l1_drift(), Section 6, applied in the order it lists: reserve override, then the capacity…, Section 6: decide whether to act on a group at all, before the solver runs.… (+56 more)

### Community 10 - "Heuristic Objective & Weights"
Cohesion: 0.08
Nodes (65): best_single_disk_alternative(), compute_vm_weights(), evaluate_assignment(), group_average_utilization(), Section 5.5 step 1: "seed with the current assignment (not from scratch -- we…, `u* = (Sum_d l_d) / (Sum_s c_s)` (C6) -- a constant under any reassignment of…, Section 5.4's `w_v = max(1, l_v / l_bar)` -- the per-VM weight that scales…, Section 5.4's objective for one candidate ``assignment``.… (+57 more)

### Community 11 - "Status File Writer"
Cohesion: 0.06
Nodes (61): CompletedProcess, contextlib, `report`, `report.warn_pinned_load_fraction`, needs_plugin, os, DrsError, ExecutionError (+53 more)

### Community 12 - "Prometheus Raw Quantities"
Cohesion: 0.07
Nodes (53): WindowConfig, MetricsError, Prometheus could not be queried, or the response was unusable. See…, _check_coverage(), _check_cross_metric_disk_consistency(), _check_metric_names_exist(), _check_observed_spacing(), _check_sample_series() (+45 more)

### Community 13 - "Prometheus Client Tests"
Cohesion: 0.05
Nodes (58): node_names uses GET /nodes, build_node_selector(), build_rate_promql(), _escape_promql_regex_literal(), The section 3.4 per-metric rate expression. ``sum by (vmid, device)…, Escape one literal string for safe use inside a PromQL/RE2 ``=~`` alternation.…, Section 3.4's auto-derived node-scoping filter: ``<node_label>=~"n1|n2|..."``…, The one selector every query in this module inserts, resolved once per run… (+50 more)

### Community 14 - "Payback Cost & Benefit"
Cohesion: 0.08
Nodes (60): MigrationConfig, compute_benefit_load_seconds(), compute_move_cost(), compute_wipe_duration_seconds(), evaluate_plan_payback(), ``duration_wipe_d`` (section 7.1) for one disk on one storage, or ``None`` if…, Section 7.1's cost for one scheduled move. Only ``source`` is needed (not the…, Section 7.2: ``benefit = (alpha*(E_before - E_after) + delta*(F_before -… (+52 more)

### Community 15 - "Execution Config Reference"
Cohesion: 0.03
Nodes (60): Configuration reference, `free_space.hard`, `free_space` — keep N bytes (or N%) free on top of the snapshot reserve, `free_space.soft`, `gates.capacity_spread_threshold`, `gates.cooldown_per_disk`, `gates.cooldown_per_storage`, `gates` — deciding whether to act at all (+52 more)

### Community 16 - "Executor Tests"
Cohesion: 0.10
Nodes (58): client_with(), default_group(), FakeClock, A move missing from `move_costs_by_key` is never refused for lack of an…, Section 13: `state.json` must learn about a UPID *before* this function goes on…, Not only the happy path -- a `move_disk` task that itself fails still finished…, `dry-run` never calls `move_disk` at all -- the callbacks must simply never…, `ExecutionConfig()`'s own defaults (both caps `1`) must dispatch to the… (+50 more)

### Community 17 - "CLI Apply & Statusfile Tests #2"
Cohesion: 0.07
Nodes (48): _balanced_apply_group_load(), _balanced_apply_topology(), _check_statusfile(), _monitored_config(), _patch_plan_deps(), GroupLoad, Two evenly-sized, evenly-loaded disks on one storage, none on the other, no…, Matches `_balanced_apply_topology()`: both disks on san-a, load 5.0 each (200%… (+40 more)

### Community 18 - "Anonymizer Tests"
Cohesion: 0.06
Nodes (43): make_mapper(), MonkeyPatch, parametrize, Path, A node and a storage that happen to share a name must not collide., Section 16.3: 'the result never depends on iteration order'., Force two different vmids to hash to the same base slot and confirm both still…, X-09: `vmid`'s own linear probing makes a collision impossible, but nothing did… (+35 more)

### Community 19 - "CBC MILP Model"
Cohesion: 0.08
Nodes (49): ObjectiveConfig, _cbc_capacity_spread_term(), _cbc_feasibility_constraints(), _cbc_objective_terms(), _cbc_small_disks_follow_their_vm(), _cbc_storage_fill(), _cbc_storage_load(), _fixed_zero_pairs() (+41 more)

### Community 20 - "Replay Tests"
Cohesion: 0.10
Nodes (48): PrometheusConfig, The step to actually send Prometheus for a ``rate()``-based ``query_range``…, safe_range_step_seconds(), The common, correctly-behaving-backend case: nothing to work around., test_safe_range_step_seconds_is_a_no_op_below_the_rate_window(), _captured_step(), _config_from_bundle(), _free_space_pairs() (+40 more)

### Community 21 - "Reserve & Capacity Gate"
Cohesion: 0.08
Nodes (47): dataclasses, compute_reserve_status(), _current_storage(), largest_disk_bytes(), managed_used_bytes(), (C4)/(C5) evaluated for one storage at the assignment ``storage_of`` encodes.…, The snapshot-reserve constraint. See IMPLEMENTATION_PLAN.md section 5.3…, ``size_bytes`` rounded *up* to the next whole MiB, in bytes. Up, never to… (+39 more)

### Community 22 - "Operator Manual Monitoring"
Cohesion: 0.05
Nodes (43): .agents/ index, Python style (.agents), One implementation of every rule (MILP and heuristic share), Units in names, API token privilege separation (intersection of ACLs), Debian package install (coinor-cbc, python3-pulp Depends), PVE credential privileges (Datastore.Audit + Allocate), Snapshot reserve (+35 more)

### Community 23 - "Raw Series Combination"
Cohesion: 0.06
Nodes (47): _blend_loads(), _combine_raw_values(), _combined_raw(), compute_disk_load_series(), _fetch_all_raw_quantities(), _fetch_all_raw_quantity_series(), _fetch_raw_quantity(), _is_metrics_expected_absent() (+39 more)

### Community 24 - "CLI Topology Stubs"
Cohesion: 0.06
Nodes (42): _all_pinned_sample_topology(), _balanced_non_violating_topology(), _fake_build_topology(), _imbalanced_group_load(), _no_reserve_violation_topology(), Topology, `_sample_topology()` with its one movable disk pinned too: san-a violates (C5)…, Unlike `_sample_topology()`, san-a here does *not* violate (C5) -- needed to… (+34 more)

### Community 25 - "Collect Testdata Tests"
Cohesion: 0.08
Nodes (44): capture(), _mapper(), Path, X-08: section 16.1's manifest line ("schema, versions, what was captured...")…, X-08: section 16.3 promises the manifest "flags" a non-node-shaped…, Z-03: `resolve_node_selector()`'s tier-1 precedence used to win on *both* sides…, A live capture against the dev cluster found the previous implementation's bug…, verify_metrics() never carries a node selector at all -- nothing to rewrite,… (+36 more)

### Community 26 - "PVE API Client Design"
Cohesion: 0.08
Nodes (40): The Proxmox VE API client, API token permission is intersection with owner, Best-effort ticket refresh tightening, build_client assembles auth once, bwlimit bytes/s to KiB/s conversion only in move_disk, Single reauthenticate-and-retry in _call, storage_content silently empty without Datastore.Allocate, storage_definitions uses the list form GET /storage (+32 more)

### Community 27 - "Corpus Validator Tests"
Cohesion: 0.10
Nodes (43): tests_corpus, tests_corpus_validate_corpus, _case(), _invariant_inputs(), MonkeyPatch, needs_full_checkout, parametrize, Path (+35 more)

### Community 28 - "test_metrics (22)"
Cohesion: 0.08
Nodes (43): _RawTimeSeries, MetricLabels, MetricsConfig, _fetch_raw_quantity_series(), One of the six section 3.4 raw quantities as a raw time series over ``[start,…, _check_device_label_collision(), compute_disk_coverage(), decimate_to_configured_step() (+35 more)

### Community 29 - "Replay Bundle Reader"
Cohesion: 0.10
Nodes (22): hash_label_name(), hash_query_text(), The cache key both this module (writing) and ``replay.py`` (reading) derive a…, BundleError, A diagnostic bundle (IMPLEMENTATION_PLAN.md section 16) could not be written or…, bundle_reference_now(), load_manifest(), _NeverSession (+14 more)

### Community 30 - "CLI Dispatch & Exit Codes"
Cohesion: 0.08
Nodes (41): ArgumentParser, CommandHandler, Namespace, proxmox_storage_drs, shutil, _accumulate_move_stats(), apply_mode_override(), build_parser() (+33 more)

### Community 31 - "Scheduler & Fragmentation"
Cohesion: 0.10
Nodes (39): group_average_fill(), `b_bar = (Sum_d z_d + Sum_s U^ext) / (Sum_s C_s)` (section 5.3 (C7)) -- a…, order_moves(), _pending_moves(), Assignment, Section 8.1's transient invariant, called with the single-move set ``{disk}``…, Section 8.2 priority 1: is ``disk``'s *current* (in ``state``) storage…, Section 8.2's scheduling loop for one group. ``target_assignment`` is normally… (+31 more)

### Community 32 - "90-heuristic (24)"
Cohesion: 0.06
Nodes (38): Internals: Building the disk/storage/group model, (C2) format eligibility: storage_type/allowed_formats, D: every disk placed, pinned or not, Foreign usage U^ext (unreferenced volumes), free_space soft_s/hard_s resolution, Pending-change pin, Per-disk cooldown pin, Pin priority: _pin_reason() (+30 more)

### Community 33 - "PVE Client Tests"
Cohesion: 0.12
Nodes (39): PveClient, One method per IMPLEMENTATION_PLAN.md section 3.5 endpoint. ``api`` is typed…, fake_api(), BaseException, --replay's build_topology() derives which node to read a shared storage's…, test_capture_bundle_storage_capture_agrees_with_replays_active_node_pick(), Section 9.2: "convert at the call site and nowhere else" -- this is that site., A ticket that expired for reasons external to this call (a long confirm-mode… (+31 more)

### Community 34 - "Concurrent Execution Tests"
Cohesion: 0.10
Nodes (32): concurrent_client_with(), datetime, The defining property of concurrency: `move_disk` for the second move is issued…, Each move's own UPID reaches both callbacks correctly attributed --…, Two otherwise-independent moves landing on the *same* target: even with…, Section 8.1's generalized invariant, live: san-c has only 2 TiB of headroom…, A leftover 1 TiB volume of VM 201 already on san-c when 201 launched (an orphan…, The deliberate simplification documented in `_execute_concurrent()`'s own… (+24 more)

### Community 35 - "CLI Command Handlers"
Cohesion: 0.11
Nodes (37): CaptureEstimate, _dump_report_json(), _filter_groups(), _handle_collect_testdata(), _handle_explain(), _handle_plan(), _handle_show_load(), _handle_verify_metrics() (+29 more)

### Community 36 - "Safety & Config Manual"
Cohesion: 0.09
Nodes (37): drs.example.yaml (reference configuration), 'no moves made' line in plan/apply, objective.spread_metric: two different quantities, Manual: Configuration reference, exclude rules, execution.mode (dry-run default), forecast (Holt-Winters), free_space.soft / free_space.hard (+29 more)

### Community 37 - "IMPLEMENTATION_PLAN (19)"
Cohesion: 0.09
Nodes (37): Anonymization allowlist, never denylist, Per-disk blockstat via pvestatd/InfluxDB/Telegraf/Prometheus, Migrations throttled by bwlimit only, Configuration and validation rules, Dependencies come from Debian (trixie), Diagnostic bundles (collect-testdata), Disk identity join (vmid, device), Proxmox Storage DRS Implementation Plan (+29 more)

### Community 38 - "CLI Report Rendering"
Cohesion: 0.10
Nodes (36): Assignment, Disk, ReserveStatus, _fragmented_vms(), _load_per_tib(), _make_confirm_move_interactively(), confirm(), _pin_action_hint() (+28 more)

### Community 39 - "Time Windows"
Cohesion: 0.15
Nodes (34): date, TimeWindow, current_deadline(), _day_name(), is_window_active(), _parse_hhmm(), datetime, ``execution.time_windows``: when ``auto`` mode may execute moves. See… (+26 more)

### Community 40 - "Crash Recovery & Confirm"
Cohesion: 0.08
Nodes (33): ConfirmCallback, Mutable state box narrow exception to functional style, Startup scan folds excluded vmids before planning, ExcludeConfig, ExecutionConfig, InflightCallback, LockHandle, MetricsConfig (+25 more)

### Community 41 - "Config Validation Checks"
Cohesion: 0.10
Nodes (34): jsonschema, ruamel_yaml, ruamel_yaml_error, _check_connection_config(), _check_forecast_window(), _check_group_size(), _check_group_storage_membership(), _check_metrics() (+26 more)

### Community 42 - "Internals Overview & Pipeline"
Cohesion: 0.11
Nodes (33): config.py depends on forecast.py, Module layout, Overview page, Seven-stage pipeline, Symbols D S Uext, Two solver backends, Backtest gate, Drift baseline is effective load (+25 more)

### Community 43 - "Repair & Transient Checks"
Cohesion: 0.10
Nodes (29): Disk-cooldown pin is not exempted for reserve repair, _RepairCandidate, _best_of(), _best_repair_candidate(), trial_storage_of(), _descend(), storage_of(), HeuristicResult (+21 more)

### Community 44 - "anonymize (23)"
Cohesion: 0.09
Nodes (24): `proxmox.auth.token_id`, Mapper, pseudonym(), ``HMAC-SHA256(salt, kind || "\\0" || value)``, truncated to 8 hex chars.…, The stateful half of anonymization: one instance per bundle capture. ``vmid``…, The pseudonym for a vmid already passed to :meth:`register_vmids`. ``None`` for…, ``node-<8 hex>``, or ``node-<8hex>.<8hex>.invalid`` for an FQDN -- shape…, ``user-<8 hex>@realm`` -- only ever seen inside a UPID (section 16.3). A value… (+16 more)

### Community 45 - "collect (19)"
Cohesion: 0.14
Nodes (19): filter_allowed_fields(), Drop every key of ``obj`` not in ``allowed``. The one primitive both the…, _anonymize_cluster_tasks(), _anonymize_node_list(), _anonymize_storage_content(), _anonymize_storage_definitions(), _anonymize_storage_resources(), _anonymize_vm_resources() (+11 more)

### Community 46 - "collect (12)"
Cohesion: 0.08
Nodes (30): functools, gzip, The one meaningful value a snapshot ``name`` field can carry is the literal…, sanitize_snapshot_name(), _anonymize_captured_prometheus(), _anonymize_prometheus_series(), _anonymize_query_text(), _anonymize_vm_snapshots() (+22 more)

### Community 47 - "Free-Space Repair Fixture"
Cohesion: 0.11
Nodes (29): executed_assignment(), Assignment, Section 7.3: "what it will really run" -- ``final_assignment``…, Section 7.3's revert test, one verdict per scheduled move in ``order``: would…, repair_markers(), `Σ_s r_s` at the assignment ``storage_of`` encodes -- section 7.3's outcome…, total_shortfall_bytes(), _free_space_repair_group() (+21 more)

### Community 48 - "anonymize (25)"
Cohesion: 0.08
Nodes (27): hashlib, hmac, MappingType, pathlib, _check_no_pseudonym_collision(), filter_disk_value_params(), filter_vm_config_fields(), filter_vm_pending_entries() (+19 more)

### Community 49 - "Source Release Tests"
Cohesion: 0.18
Nodes (29): ExecutionConfig, SourceReleaseConfig, make_disk(), make_move(), make_storage(), Section 9.3: a source_release timeout "does not fail the run: mark the storage…, Same as above, except the second move's *target* -- not source -- is the…, Section 9.3 point 3: PVE's own `saferemove_throughput` (already read live off… (+21 more)

### Community 50 - "PVE API Calls"
Cohesion: 0.07
Nodes (15): Run one ``proxmoxer`` call, wrapping every failure as :class:`PveApiError`.…, ``GET /cluster/resources?type=vm``: VM inventory., ``GET /cluster/tasks``: recent/active tasks across **every** node -- the one…, ``GET /cluster/resources?type=storage``: storage inventory., ``GET /nodes``: every node in the cluster, by name. Section 3.4's node-scoping…, ``GET /version``: the running PVE's own version string (section 16.1/16.3's…, ``GET /storage``: every storage's full config, including ``saferemove``.…, ``GET /nodes/{node}/qemu/{vmid}/config``: disk -> storage mapping and size.… (+7 more)

### Community 51 - "CLI Report Rendering #2"
Cohesion: 0.16
Nodes (29): ExecutionResult, GateDecision, ObjectiveConfig, PaybackResult, ScheduleResult, _log_plan_selected(), _objective_breakdown_json(), GroupLoad (+21 more)

### Community 52 - "Bundle Capture"
Cohesion: 0.12
Nodes (24): _anonymize_exclude_disk_key(), _anonymized_config_dict(), _build_manifest(), CallRecord, capture_bundle(), _capture_prometheus_files(), CaptureEstimate, CaptureLog (+16 more)

### Community 53 - "test_logging_setup (23)"
Cohesion: 0.14
Nodes (27): ast, io, configure_logging(), floor_for_command(), The mandatory ``INFO`` floor of section 2.3, or ``None``. A run that can change…, Install this run's log handler. Called once, from ``main()``. ``floor`` is…, CaptureFixture, INFO at a terminal is the narrative the operator asked for; prefixing every… (+19 more)

### Community 54 - "State File & Locking"
Cohesion: 0.17
Nodes (27): flock is the lock; JSON lock field is only a label, acquire_lock(), empty_state(), load_state(), First-run state: no lock, no recorded balance, no cooldowns, nothing in flight…, Best-effort read of ``path``. See the module docstring: a missing file is the…, Section 11.2's advisory lock: ``fcntl.flock(LOCK_EX | LOCK_NB)`` on ``path``…, Clears the descriptive ``lock`` field and releases the OS-level lock, writing… (+19 more)

### Community 55 - "Documentation Tests"
Cohesion: 0.14
Nodes (26): importlib_resources, _flatten_schema_keys(), _load_schema(), _manpage_source_text(), _manual_documented_keys(), Any, needs_full_checkout, parametrize (+18 more)

### Community 56 - "Plan Constraints & Objective"
Cohesion: 0.13
Nodes (26): beta term: number of migrations, C1 Assignment, (C3) VM affinity linking, (C4) Largest-disk linearization Z_s, C5 Capacity, snapshot reserve and free space, (C6) Load spread, C7 Capacity-spread linearization, (C8) Small disks follow their VM (+18 more)

### Community 57 - "Group Storage Expansion"
Cohesion: 0.16
Nodes (24): concurrent_futures, GroupConfig, is_storage_pattern(), A ``storages[].id`` value is a pattern iff it both begins and ends with ``/``…, The regular expression text of a pattern entry, its two ``/`` delimiters…, storage_pattern_text(), StorageConfig, _build_storages() (+16 more)

### Community 58 - "test_crashrecovery (21)"
Cohesion: 0.14
Nodes (24): Two failure modes, one in-flight UPID mechanism, AuthConfig, expected_task_user(), Section 13's startup scan. Returns the vmids to exclude from this run's…, The exact string PVE records as a task's ``user`` field for credentials this…, reconcile_inflight(), The same in-flight move already recorded in state.json also shows up in the…, Startup crash/two-instance recovery. See proxmox_storage_drs/crashrecovery.py. (+16 more)

### Community 59 - "Plan Decision Logging"
Cohesion: 0.13
Nodes (21): The `objective:` line, What this build actually implements, ObjectiveBreakdown, Section 7.2's unweighted ``F`` -- ``sum(d_s)``, always L1 regardless of…, Section 7.2's unweighted ``E`` -- ``sum(e_s)`` (``"l1"``) or ``max(u_s)``…, Section 7.2's unweighted (by ``kappa``, but ``w_v``-weighted) ``A`` -- ``Sum_v…, The section 5.4 objective, evaluated for one candidate assignment, broken into…, raw_affinity_debt() (+13 more)

### Community 60 - "test_collect (26)"
Cohesion: 0.14
Nodes (24): make_config(), make_prometheus_client(), make_pve_client(), --no-series must skip the big, per-group superset range captures -- it does not…, Y-06: the manifest's version fields are machine-generated provenance, not free…, X-09: the printed query count used to treat a multi-day range as one range…, Z-05: a live capture stores every range series at…, Section 3.8/16.3: a real pending edit on the VM's own disk survives as the… (+16 more)

### Community 61 - "Cross-Type Move Tests"
Cohesion: 0.09
Nodes (23): _group_with_types(), A `san-c` content responder plus a `move_disk` responder for 201. The listing…, 201's mirror target is already *listed* on san-c at its full 1 TiB by the time…, Between different storage types, or from thin to thick, `move_disk` allocates…, The match stays narrow: a same-VM volume that appeared after launch but has…, The exclusion is narrow: only 201's *own* mirror target (same VM, the disk's…, Between different storage types the target is allocated at the disk line's…, The same 2 TiB config `size=` and the same 4.5 TiB already on the target, but… (+15 more)

### Community 62 - "cli (17)"
Cohesion: 0.10
Nodes (23): datetime, GatesConfig, PrometheusClient, _compute_group_load(), _log_forecast(), _log_gate_decision(), _log_load_digest(), _log_payback_verdict() (+15 more)

### Community 63 - "crashrecovery (23)"
Cohesion: 0.14
Nodes (22): Crash and two-instance recovery: crashrecovery.py, cluster/tasks vs task_status conventions differ, parse_upid PVE UPID grammar confirmed live, reconcile_inflight: recorded UPIDs plus foreign scan, parse_upid(), The local half of the startup scan: re-checks every UPID ``state.json`` already…, The cluster-wide half: a still-running ``qmmove`` task from this tool's own…, Startup crash/two-instance recovery. See IMPLEMENTATION_PLAN.md section 13.… (+14 more)

### Community 64 - "units (19)"
Cohesion: 0.13
Nodes (21): pytest, re, capture_range_seconds(), Section 16.2's ``capture_range = max(...)`` -- what ``holt_winters`` needs, not…, format_bytes(), format_duration_seconds(), parse_duration_seconds(), parse_size_bytes() (+13 more)

### Community 65 - "pve-storage-drs.1 (18)"
Cohesion: 0.09
Nodes (21): Dry-run is the default, Three documentation artefacts (internals, manual, manpage/help), Nothing is ever deleted automatically, Unconditional safety properties, Shared pandoc PDF metadata, Orphaned volumes reported, never auto-deleted, AUTHOR, COLLECT-TESTDATA OPTIONS (+13 more)

### Community 66 - "test_collect (22)"
Cohesion: 0.13
Nodes (20): FakePrometheusSession, A ``metrics._SessionLike`` double capable of answering *many* distinct queries…, _instant_answer(), Any, BaseException, _Raise, _range_answer(), A live capture against the dev cluster found this one directly (section 16.3's… (+12 more)

### Community 67 - "Agent Docs Rules"
Cohesion: 0.13
Nodes (21): Git workflow (.agents), Branch first, decided from the task, Merge --no-ff on green make check, Release process (version, changelog, tag, graphify), Identity, AGPL licence, copyright rules, make check loop, Naming: pve-storage-drs, not drs, Release rule: version, changelog, tag, graphify (+13 more)

### Community 68 - "Cooldown State"
Cohesion: 0.16
Nodes (21): Cooldowns, LockInfo, _parse_state_text(), Any, Raises on any shape this module does not recognize -- the caller…, The tolerant-parse half of :func:`load_state`, factored out so…, Pure: merges new disk/storage cooldown timestamps into ``state``, keyed exactly…, Re-reads whatever is currently written through an already-open,… (+13 more)

### Community 69 - "topology (22)"
Cohesion: 0.13
Nodes (20): _ClusterData, _disk_snapshot_or_orphan_reason(), _disk_specs_from_config(), _fetch_vm(), format_disk_id(), _join_vm_disks(), _needed_content_node_pairs(), Any (+12 more)

### Community 70 - "Agent Docs Rules #2"
Cohesion: 0.12
Nodes (20): Disks with snapshots pinned, Toolchain (black, isort, flake8, mypy, pytest), black vs flake8 disagreements (E203, W503, E704), Testing (.agents), Acceptance fixtures and generate_expected.py, 85 percent coverage floor, No network, no real sleep, deterministic ties in tests, Codecov configuration (+12 more)

### Community 71 - "Plan Constraints & Objective #2"
Cohesion: 0.14
Nodes (20): Affinity repair under payback fixture, bwlimit is the only throttle (saturation guard removed), Companion fixture affinity repair, free_space requirement soft_s / hard_s, free-space repair fixture, free_space grammar (bytes, unit string, N%) and precedence, Free-space repair mandate fixture, Free-space repair mandate (+12 more)

### Community 72 - "IMPLEMENTATION_PLAN (14) #2"
Cohesion: 0.14
Nodes (20): approximate-size fallback for qcow2-on-LVM volumes, Mandatory INFO audit floor for confirm/auto runs, (C2) Eligibility via variable fixing, Errors are not mismatches, Structured log event catalogue, Execution modes dry-run, confirm, auto, Logging policy (two audiences, levels, audit floor), Which disks can move online (all buses, efidisk0, tpmstate0, unused) (+12 more)

### Community 73 - "test_forecast (18)"
Cohesion: 0.13
Nodes (18): Collection, forecast_group(), ForecastReport, Any, What one group's forecast did this run -- the ``forecast`` block of ``explain``…, One group's forecast: run the backtest on the group aggregate, and only if…, _group_series(), _noise_series() (+10 more)

### Community 74 - "Internals Overview & Pipeline #2"
Cohesion: 0.18
Nodes (19): Auto mode time window, Concurrent execution, Execute page, execute_plan live revalidation, Four-condition done, Injectable Clock, Live transient check provisioned, Orphans reported never deleted (+11 more)

### Community 75 - "test_execute (8)"
Cohesion: 0.15
Nodes (18): LocksConfig, log_messages(), LogCaptureFixture, `execution.locks.on_timeout: abort` under concurrency: the locked head never…, `execution.locks.on_timeout: skip` (the default): the locked head times out…, Section 9.3 point 3: the very race this fix targets -- a `move_disk` task's own…, Crash recovery (section 11.2/13): a retried move is still always exactly one…, Rendered messages of the captured records carrying ``event``. (+10 more)

### Community 76 - "test_forecast (17)"
Cohesion: 0.16
Nodes (14): math, random, Any, Holt-Winters forecasting, its backtest gate, and the required-range rule., A diurnal series that *ends at its trough*: the last forecast point (one day…, series_of(), test_backtest_is_none_without_a_fit_half(), test_backtest_is_none_without_an_actual_half() (+6 more)

### Community 77 - "Agent Docs Rules #3"
Cohesion: 0.12
Nodes (14): Config knob entry: type, default, unit, extremes, interactions, Tests keeping docs honest (help covers options, manual covers config), --help generated from argparse definitions, no hardcoded defaults, Internals pages: question first, name modules, explain why, ASCII diagrams, Manpage skeleton with complete OPTIONS, config/drs.example.yaml as documentation that parses, Change behaviour and documentation in the same commit, PDF is a build product; fix text not LaTeX (+6 more)

### Community 78 - "test_loadmodel (15) #2"
Cohesion: 0.15
Nodes (8): RangeStepMismatch, ``--replay`` found the requested range query, but at a different step than this…, FakeResponse, Any, _RangeStepMismatchFakeClient, A ``range_query`` stand-in that returns caller-supplied data keyed by the exact…, Like ``_StepAwareFakeClient``, but raises ``RangeStepMismatch`` (carrying its…, _WindowTrackingFakeClient

### Community 79 - "Cooldown State #2"
Cohesion: 0.15
Nodes (16): cooldown_remaining_seconds(), _pid_alive(), Seconds left in ``key``'s cooldown -- ``0.0`` if nothing is recorded for it,…, Best-effort, used only to make a "still held" log message useful to an operator…, Only `schema_version` present -- every other field must default the same way…, Persistent state at ``state.path``. See proxmox_storage_drs/state.py. Every…, A hand-edited or foreign timestamp must degrade to "not in cooldown", not raise…, pid 1 (init) always exists but is not ours to signal as a normal user --… (+8 more)

### Community 80 - "State Drift & Inflight"
Cohesion: 0.14
Nodes (17): LastBalance, load_vector_for_group(), now_iso(), ``at`` is ``None`` before any run has ever executed a migration -- distinct…, This group's slice of ``last_balance.load_vector``, re-keyed from…, Pure: a new :class:`State` with ``group_name``'s slice of…, UTC, second precision, ``Z`` suffix -- exactly section 11.2's own example…, with_recorded_balance() (+9 more)

### Community 81 - "25-show-load-and-verify-storages (14)"
Cohesion: 0.14
Nodes (14): VM.Config.Disk and VM.Migrate privileges for apply, A negative `saferemove_throughput` is normal, Group ACT/NO ACTION gate line, Negative saferemove_throughput is normal, Reading `show-load` and `verify-storages`, `show-load`, The `Group <name> → ACT`/`NO ACTION` line, `verify-storages` (+6 more)

### Community 82 - "Execution Config Reference #2"
Cohesion: 0.12
Nodes (16): `execution.abort_on_failure`, `execution` — how (and whether) moves actually happen, `execution.locks.on_timeout`, `execution.locks.poll_interval`, `execution.locks.task_retry_backoff`, `execution.locks.task_retry_limit`, `execution.locks.wait_timeout`, `execution.max_concurrent_migrations` (+8 more)

### Community 83 - "IMPLEMENTATION_PLAN (11) #2"
Cohesion: 0.15
Nodes (16): Backtest gate: beat persistence baseline, Storage capability weight and utilization u_s, CP-SAT (ortools) backend, removed, Drift gate (L1 norm, default 0.10), Forecast scales l_d by f_d/h_d, Holt-Winters forecasting and backtest gate, gigapipe step >= range workaround, Holt-Winters seasonal forecast (engine-side) (+8 more)

### Community 84 - "Config Schema & Build"
Cohesion: 0.14
Nodes (16): _build_config(), FreeSpaceConfig, _load_schema(), MonitoringConfig, _parse_free_space_value(), Any, Parse one ``free_space.soft``/``.hard`` entry (section 5.3.1's grammar).…, Section 5.3.1's global ``free_space`` block. ``soft`` defaults to an absolute 0… (+8 more)

### Community 85 - "forecast (9)"
Cohesion: 0.18
Nodes (15): HoltWintersConfig, Backtest, holt_winters_quantile(), TimeSeries, _quantile(), One group's backtest: absolute error of each model's predicted p95 of ``[now-W,…, Section 10.2's backtest, comparing against a baseline: fit on ``[now-2W,…, Linear-interpolation quantile, matching ``numpy.percentile``'s default.… (+7 more)

### Community 86 - "Cooldown State #3"
Cohesion: 0.21
Nodes (14): Cooldown data stored here, interpreted by topology and heuristic, errno, fcntl, socket, _active_cooldowns(), active_disk_cooldowns(), active_storage_cooldowns(), _parse_iso() (+6 more)

### Community 87 - "Internals Overview & Pipeline #3"
Cohesion: 0.25
Nodes (15): Gigapipe step workaround, Metrics page, Node-scoping selector, PrometheusClient, PromQL builders, Range query chunking, SessionLike protocol, verify_metrics six checks (+7 more)

### Community 88 - "40-cli-and-logging (22)"
Cohesion: 0.14
Nodes (14): Internals: CLI dispatch and logging, Global options on top-level parser, Command handlers dispatched via dict, JsonFormatter, Structured logs go to stderr, Log levels, mandatory floor, handler on root, --manual prefers man(1), falls back to in-tree markdown, --manual prefers man(1), falls back to plain text (+6 more)

### Community 89 - "Agent Docs Rules #4"
Cohesion: 0.20
Nodes (14): Domain invariants (.agents), Enumerate every disk bus, Finished task is not a finished move, Never auto-delete a volume, Provisioned size, never allocated, Snapshot reserve never traded for balance, VM locks are an open set, IMPLEMENTATION_PLAN.md as specification (+6 more)

### Community 90 - "State Drift & Inflight #2"
Cohesion: 0.15
Nodes (14): Persistent state: state.json, Drift history reaches the gates via last_balance, Inflight UPIDs written and read for crash recovery, Reading degrades, writing raises, staged_disks field unimplemented, State dataclass tree mirrors section 11.2 JSON, Write UPID to disk before the crash can happen, ``"<group>:<storage>"`` (section 11.2). (+6 more)

### Community 91 - "28-apply (14)"
Cohesion: 0.14
Nodes (13): Concurrent execution, Crash and two-instance recovery, Failure and `abort_on_failure`, `--json`, Reading `apply`, Reading `auto` mode, `state.json`: what a real run actually changes, The `[y]es/[n]o skip/[a]ll remaining/[q]uit` prompt (+5 more)

### Community 92 - "State File & Locking #2"
Cohesion: 0.21
Nodes (12): Exception hierarchy for the project. Every error the tool can raise…, ``state.path`` could not be written, or its advisory lock could not be…, StateError, Temp file in the same directory, ``fsync``, then ``os.replace`` -- a reader…, save_state_atomic(), skipif, The `finally` block's own cleanup, pinned directly rather than only inferred…, test_acquire_lock_raises_state_error_on_a_permission_failure() (+4 more)

### Community 93 - "test_forecast (13)"
Cohesion: 0.31
Nodes (12): disk_factors(), ``f_d / h_d`` for every disk that has one: ``f_d`` the Holt-Winters forecast…, _factor_series(), _FixedForecast, MonkeyPatch, 96 hourly samples whose last 24 are ``window_values`` (repeated)., Patches ``holt_winters_quantile`` to a constant so the ratio is exact., test_disk_factors_is_forecast_over_observed_p95() (+4 more)

### Community 94 - "Pin Reasons & Formats"
Cohesion: 0.15
Nodes (13): _allowed_formats(), _default_format(), parse_pve_config_size_bytes(), Parse a `size=` value from a VM config line, e.g. ``"512G"``. Returns ``None``…, PVE tags as returned by `cluster/resources`: semicolon-separated, with comma…, Section 5.3 (C2): the disk formats ``storage_type`` can hold. An unrecognised…, _split_tags(), parametrize (+5 more)

### Community 95 - "fakes (13)"
Cohesion: 0.22
Nodes (5): FakeProxmoxResource, FakeQueryResponse, Any, Shared test doubles. Not collected by pytest (no ``test_`` prefix).…, Matches ``metrics._ResponseLike``: ``.status_code`` and ``.json()``.

### Community 96 - "test_cli (22)"
Cohesion: 0.24
Nodes (11): _gate(), _no_move_schedule(), _outcome(), _patch_forecast_deps(), Any, A replayed dev-cluster bundle: capacity spread 112 %, I/O balanced, the gate…, The local cluster bundle under minmax: one disk carries 80 % of the group's…, test_a_capacity_gated_empty_plan_names_the_two_weights_that_decided_it() (+3 more)

### Community 97 - "05-metrics-pipeline (21)"
Cohesion: 0.17
Nodes (12): gigapipe with ClickHouse (reference backend), PVE InfluxDB external metric server, instance label collision, OpenTelemetry metric server rejected, Other backends, RRD rejected as data source, Six per-disk blockstat counters, Silent counter loss from string fields in line protocol (+4 more)

### Community 98 - "28-apply (11)"
Cohesion: 0.20
Nodes (11): Transient reserve invariant (operator explanation), Concurrent execution with strict FIFO launch, confirm prompt [y]es/[n]o/[a]ll/[q]uit, apply modes: dry-run, confirm, auto, Pre-flight live re-check before each move, auto re-plan loop, Decision trail events, --log-format text vs json (+3 more)

### Community 99 - "IMPLEMENTATION_PLAN (12)"
Cohesion: 0.22
Nodes (11): Engine pipeline: collect, join, gate, solve, cost, order, execute, Move completion criterion stronger than task success, Per-disk and per-storage cooldowns, Deadlock and staging, Gating (drift, imbalance, capacity gates, cooldowns, reserve override), Move states mirroring, draining, done, Implementation phases 1-15, saferemove wipe and signed saferemove_throughput (+3 more)

### Community 100 - "40-cli-and-logging (22) #2"
Cohesion: 0.20
Nodes (10): json, Section 2.3's ladder: ``--quiet`` < default < ``-v`` < ``-vv``. ``--log-level``…, ``auto`` and ``text`` -> ``"text"``; ``json`` -> ``"json"``. JSON is opt-in. It…, Logging policy. See IMPLEMENTATION_PLAN.md section 2.3. Every log record goes…, resolve_format(), resolve_level(), parametrize, test_log_level_wins_over_both_verbose_and_quiet() (+2 more)

### Community 101 - "Group Storage Expansion #2"
Cohesion: 0.22
Nodes (11): FreeSpaceValue, One parsed-but-unresolved ``free_space.soft``/``.hard`` entry (section 5.3.1's…, _free_space_level(), _free_space_source(), Section 5.3.1: an absolute value is used as written; a percentage is…, One storage's resolved ``soft_s``/``hard_s`` and where each came from (section…, ``level`` (global / storage entry / pattern ``/re/``), plus the percent-to-…, Section 5.3.1: resolve ``soft_s``/``hard_s`` for one storage. The mandated… (+3 more)

### Community 102 - "PromQL Builders"
Cohesion: 0.20
Nodes (10): _issue_chunked_range_query(), Any, ``client.range_query()``, issued in ``RANGE_QUERY_CHUNK_SECONDS``-sized sub-…, Merges several ``(start, end, result)`` ``query_range`` captures of the *same*…, stitch_range_results(), The common case: a wide range chunked by…, A repeat capture of the same query (not just adjacent chunks) can carry the…, test_stitch_range_results_dedupes_overlapping_timestamps() (+2 more)

### Community 103 - "test_execute (27)"
Cohesion: 0.22
Nodes (7): MoveCost, Section 7.1's cost for one already-scheduled move., Section 9.1: the pre-loop time-window check (above) only knows the answer as of…, REVIEW.md T-06's collateral bug: before the fix, this "skipped" outcome let the…, test_deadline_recheck_after_a_lock_wait_refuses_a_move_that_no_longer_fits(), test_deadline_recheck_after_a_lock_wait_stops_the_whole_run_not_just_this_move(), status_current()

### Community 104 - "test_pve (10)"
Cohesion: 0.24
Nodes (7): _FakeProxmoxApiWithSession, _FakeSession, Any, Confirmed live against a real multi-VM cluster: `requests`'s own default…, A small `read_workers` (or the field's own minimum) must not shrink the pool…, test_apply_connection_pool_size_mounts_an_adapter_sized_to_read_workers(), test_apply_connection_pool_size_never_shrinks_below_the_requests_default()

### Community 105 - "check_paper_log (14)"
Cohesion: 0.28
Nodes (8): argparse, sys, check(), _logical_lines(), main(), Path, Undo the log's hard wrap at 79 columns. TeX breaks log lines mid-message, which…, Fail the paper build on LaTeX problems that silently damage the PDF. `lualatex`…

### Community 106 - "10-configuration (9) #2"
Cohesion: 0.22
Nodes (9): `objective.affinity_counts_pinned_disks`, `objective.alpha_spread`, `objective.beta_move_count`, `objective.delta_capacity_spread`, `objective.gamma_move_bytes_per_tib`, `objective.kappa_vm_affinity`, `objective.reserve_violation_penalty`, `objective.spread_metric` (+1 more)

### Community 107 - "40-cli-and-logging (22) #3"
Cohesion: 0.25
Nodes (7): fixture, logging, Holt-Winters load forecasting. See IMPLEMENTATION_PLAN.md sections 10 and 12.1.…, Shared pytest fixtures. ``logging`` is process-global state, and…, _restore_logging_state(), typing, warnings

### Community 108 - "IMPLEMENTATION_PLAN (10)"
Cohesion: 0.25
Nodes (9): Allowlist-never-denylist anonymization, Diagnostic bundle directory format, collect-testdata diagnostic bundle, tests/corpus and scrub audit, Global command-line options, Mode override logging (escalation is a warning), HMAC pseudonyms with persisted random salt, --replay global option (+1 more)

### Community 109 - "IMPLEMENTATION_PLAN (9)"
Cohesion: 0.31
Nodes (9): Autopkgtest install-with-only-Depends check, CBC via PuLP MILP backend, CP-SAT ortools backend removed (AL-02), Debian-first dependency policy, Debian package and CI pipelines (GitHub Actions, Salsa), Heuristic fallback (seed, repair, descend, polish), Shared feasibility and objective functions (evaluate_assignment), Shared feasibility/objective implementation (+1 more)

### Community 110 - "logging_setup (9)"
Cohesion: 0.22
Nodes (7): LogRecord, json_safe(), One human-readable line per record: ``LEVEL: message``. Deliberately not a…, Replace every non-finite float with ``None``, recursively. Python's JSON…, TextFormatter, test_json_safe_replaces_non_finite_floats_recursively(), test_text_formatter_includes_exception_info()

### Community 111 - "00-installation (14)"
Cohesion: 0.25
Nodes (8): First steps after installing, Installation and requirements, Installing the package, Running the timer on exactly one host, Setting up the PVE credential, What you need, Where the configuration is *not*, Where the configuration lives

### Community 112 - "10-configuration (8)"
Cohesion: 0.25
Nodes (8): `exclude.disks`, `exclude.include_unused_disks`, `exclude.running_only`, `exclude.skip_vms_with_snapshots`, `exclude.storages`, `exclude.tags`, `exclude.vmids`, `exclude` — what DRS never touches

### Community 113 - "PromQL Builders #2"
Cohesion: 0.29
Nodes (5): Protocol, The subset of ``requests.Response`` this module relies on., The subset of ``requests.Session`` this module relies on. A structural type…, _ResponseLike, _SessionLike

### Community 114 - "test_logging_setup (20)"
Cohesion: 0.25
Nodes (8): JsonFormatter, Render one :class:`logging.LogRecord` as one JSON line., Found live: section 7's payback ratio is `+inf` for any plan with no moves to…, _strict(), test_a_non_finite_extra_still_produces_valid_json(), test_json_formatter_emits_one_parseable_object_per_record(), test_json_formatter_includes_exception_info(), test_json_formatter_includes_extra_fields()

### Community 115 - "test_execute (7)"
Cohesion: 0.25
Nodes (8): parametrize, An API error re-reading the VM is not a mismatch re-planning can cure: the move…, A PVE API error while re-reading the target refuses the move and fails the run…, test_live_transient_check_fails_safe_when_the_live_read_errors(), test_move_charge_bytes_rule(), test_orphan_detection_handles_a_pve_api_error_gracefully(), test_preflight_vm_config_fetch_error_fails_the_run(), raise_error()

### Community 116 - "Internals Overview & Pipeline #4"
Cohesion: 0.43
Nodes (7): Config path resolution order, Configuration page, ResolvedConfig, Secrets from environment, Semantic validation rules, Two-stage validation, Units parsed once

### Community 117 - "State Drift & Inflight #3"
Cohesion: 0.33
Nodes (7): Rename-detaches-flock bug and in-place locked write, LockHandle, Opaque -- pass to :func:`release_lock`. The open file descriptor is what…, Writes ``state`` **in place** into the already-open, already-locked ``fd`` --…, Persists ``state``'s business fields (``last_balance``, ``cooldowns``,…, save_locked_state(), _write_state_to_locked_fd()

### Community 118 - "00-installation (7)"
Cohesion: 0.29
Nodes (7): Configuration on pmxcfs (/etc/pve/drs.yaml), Run the systemd timer on exactly one host, state.json is node-local, not on /etc/pve, `state`, state.path, Crash and two-instance recovery (inflight_upids), state.json updates after a real run

### Community 119 - "forecast (14) #2"
Cohesion: 0.48
Nodes (7): ForecastConfig, The history ``forecast.model`` needs, in seconds. Called by ``config.py``'s…, required_range_seconds(), test_holt_winters_required_range_is_the_lookback_when_that_is_longer(), test_holt_winters_required_range_matches_plan_worked_example(), test_quantile_required_range_is_the_lookback(), test_required_range_unknown_model_raises()

### Community 120 - "Execution Config Reference #3"
Cohesion: 0.33
Nodes (6): `load_weights.bytes`, `load_weights` — combining read/write and time/ops/bytes, `load_weights.iotime`, `load_weights.ops`, `load_weights.read_factor`, `load_weights.write_factor`

### Community 121 - "26-collect-testdata-and-replay (6)"
Cohesion: 0.33
Nodes (5): `collect-testdata`: capturing a bundle, Diagnostic bundles: `collect-testdata` and `--replay`, `--replay`: running against a bundle offline, Sending one to the project, What is in a bundle, and what is not

### Community 122 - "cli (16)"
Cohesion: 0.40
Nodes (6): MoveCost, MoveOutcome, ScheduledMove, Section 7.3's hard per-move duration rule (``rejected_moves``) rendered as…, _refused_move_outcomes(), _render_plan_move_line()

### Community 123 - "cli (16) #2"
Cohesion: 0.33
Nodes (4): Section 5.3's "report any residual `r_s > 0` prominently as an unfixable…, The human form of :class:`_UnfixableShortfall` -- printed whether or not the…, _render_unfixable_shortfall_lines(), _UnfixableShortfall

### Community 124 - "forecast (14)"
Cohesion: 0.33
Nodes (6): group_aggregate_series(), Sum every disk's own series into one group-aggregate series, at the union of…, 101:scsi0 has no sample at t=1 at all -- that timestamp still appears (from…, test_group_aggregate_series_empty_input_is_empty(), test_group_aggregate_series_missing_disk_at_a_timestamp_contributes_zero(), test_group_aggregate_series_sums_across_disks_per_timestamp()

### Community 125 - "Execution Config Reference #4"
Cohesion: 0.40
Nodes (5): `forecast.holt_winters.seasonal`, `forecast.holt_winters.seasonal_periods`, `forecast.holt_winters.trend`, forecast.model (quantile, holt_winters), `forecast` — placing disks for the load they will have

### Community 127 - "Show-Load Tests"
Cohesion: 0.40
Nodes (3): test_manual_falls_back_when_man_exits_nonzero(), test_manual_flag_uses_man_when_available(), fake_run()

### Community 128 - "PVE Client Tests #2"
Cohesion: 0.40
Nodes (3): _FakeHttpsBackend, _FakeProxmoxApiWithBackend, _FakeTicketAuth

## Knowledge Gaps
- **213 isolated node(s):** `First steps after installing`, `Installing the package`, `Running the timer on exactly one host`, `Setting up the PVE credential`, `What you need` (+208 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1389 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **32 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Group` connect `Load Model Tests` to `Executor Move Lifecycle`, `Topology Build Tests`, `Optimize Tests`, `Gates & Drift Evaluation`, `Heuristic Objective & Weights`, `Payback Cost & Benefit`, `Executor Tests`, `CBC MILP Model`, `Raw Series Combination`, `Scheduler & Fragmentation`, `Concurrent Execution Tests`, `Repair & Transient Checks`, `collect (12)`, `Free-Space Repair Fixture`, `Source Release Tests`, `Bundle Capture`, `Group Storage Expansion`, `Plan Decision Logging`, `Cross-Type Move Tests`, `test_execute (27)`?**
  _High betweenness centrality (0.081) - this node is a cross-community bridge._
- **Why does `Persistent state: state.json` connect `State Drift & Inflight #2` to `Executor Move Lifecycle`, `Safety & Config Manual`, `Gates & Drift Evaluation`, `Internals Overview & Pipeline`, `Repair & Transient Checks`, `Raw Series Combination`, `State Drift & Inflight #3`, `State File & Locking`, `Cooldown State #3`, `Group Storage Expansion`, `CLI Dispatch & Exit Codes`, `crashrecovery (23)`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Why does `Manual: Configuration reference` connect `Safety & Config Manual` to `90-heuristic (24)`, `Execution Config Reference`, `25-show-load-and-verify-storages (14)`, `Internals Overview & Pipeline #4`, `Operator Manual Monitoring`, `26-collect-testdata-and-replay (6)`, `State Drift & Inflight #2`, `Execution Config Reference #4`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Are the 144 inferred relationships involving `Group` (e.g. with `_drive_group_series()` and `_execute_concurrent()`) actually correct?**
  _`Group` has 144 INFERRED edges - model-reasoned connections that need verification._
- **Are the 87 inferred relationships involving `PveClient` (e.g. with `capture_bundle()` and `reconcile_inflight()`) actually correct?**
  _`PveClient` has 87 INFERRED edges - model-reasoned connections that need verification._
- **What connects `First steps after installing`, `Installing the package`, `Running the timer on exactly one host` to the rest of the system?**
  _213 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Executor Move Lifecycle` be split into smaller, more focused modules?**
  _Cohesion score 0.047722772277227724 - nodes in this community are weakly interconnected._