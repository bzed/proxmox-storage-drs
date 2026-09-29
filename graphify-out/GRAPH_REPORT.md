# Graph Report - proxmox-storage-drs  (2026-09-29)

## Corpus Check
- 5 files · ~310,359 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3815 nodes · 11015 edges · 158 communities (135 shown, 23 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 1656 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- build_topology
- MonkeyPatch
- execute.py
- generate_expected.py
- ObjectiveBreakdown
- test_config.py
- Topology
- test_statusfile.py
- topology.py
- test_cli.py
- test_execute.py
- run_concurrent
- ResolvedConfig
- _patch_plan_deps
- Storage
- test_optimize.py
- GroupLoad
- metrics.py
- test_anonymize.py
- Disk
- test_metrics.py
- loadmodel.py
- test_collect.py
- compute_group_load
- Configuration reference
- test_replay.py
- test_validate_corpus.py
- build_client
- Internals: The heuristic solver
- fake_api
- BundleError
- schedule.py
- schedule.py: Disk
- test_logging_setup.py
- Manual: Configuration reference
- test_documentation.py
- TimeWindow
- evaluate_assignment
- ExecutionConfig
- main
- Path
- test_free_space_repair_fixture.py
- evaluate_assignment: test_heuristic.py
- collect.py
- Config
- pve.py
- order_moves
- Dry-run is the default
- pseudonym
- ._get
- State
- heuristic.py
- free_space requirement soft_s / hard_s
- empty_state
- Payback rule and acceptance test
- anonymize.py
- Proxmox Storage DRS Implementation Plan
- make_config
- .agents/ index
- Proxmox VE API
- config.py
- capture_bundle
- crashrecovery.py
- stitch_range_results
- state.py
- ForecastReport
- FakePrometheusSession
- _run_two_onto_san_c
- test_small_disks.py
- Reading `apply`
- PveClient
- test_forecast.py
- 20-verifying-metrics.md
- pytest
- forecast.py
- 20-verifying-metrics.md: Manual: Configuration reference
- move_disk (drive-mirror, delete=1)
- Mapper
- Any
- empty_state: test_state.py
- cli.py
- loadmodel.py: safe_range_step_seconds()
- _handle_apply
- MoveCost
- 00-installation.md
- `execution` — how (and whether) moves actually happen
- Load model (average in-flight I/O)
- pve-storage-drs.1.md
- PrometheusClient
- Internals: CLI dispatch and logging
- test_plan_gate_also_reflects_real_drift_history_from_state_json
- Reading `apply`: Reading `apply`
- disk_factors
- test_affinity_repair_fixture.py
- loadmodel.py: build_rate_promql()
- Any: Any
- AGENTS.md working agreement
- State: _state_from_dict()
- units.py
- fakes.py
- Group
- Overview page
- Engine pipeline: collect, join, gate, solve, cost, order, execute
- Mapper: filter_vm_config_fields()
- Testing (.agents)
- Transient reserve invariant (operator explanation)
- series_of
- Execute page
- `proxmox` — the cluster API connection
- fake_api: PveApiError
- _FakeSession
- build_node_selector
- Execute page: order_moves
- `objective` — the solver's trade-off weights
- MetricsError
- Overview page: Load model page
- Persistent state: state.json
- Overview page: Gates page
- 00-installation.md: Installation and requirements
- Configuration reference: `exclude` — what DRS never touches
- 30-safety-and-status.md
- Group: _quantile_promql()
- Configuration page
- Overview page: Payback page
- Reading `apply`: 28-apply.md
- _findings_to_json
- ForecastConfig
- _forecast_fixture
- Logging: what lands where, and what an unattended run records
- C5 Capacity, snapshot reserve and free space
- forecast_group
- Logging: what lands where, and what an unattended run record
- filters.lua
- resolve_level
- test_unfixable_shortfall_is_proven_only_for_an_optimal_cbc_solve
- test_holt_winters_quantile_clamps_at_zero
- test_holt_winters_quantile_forecasts_ceil_window_over_step_steps
- test_holt_winters_quantile_is_none_for_a_non_finite_forecast
- ObjectiveBreakdown: What `plan` does not yet do
- _is_metrics_expected_absent
- import-all
- draining status
- run-with-system-python.sh
- _plan_group
- _plan_group: _log_load_digest()
- test_logging_setup.py: test_every_log_call_carries_an_event(
- build_paper.sh
- Over-provisioning Rule
- Check 3: configured labels present
- Check 6: observed sample spacing
- Lock timeout skip vs abort
- pve-storage-drs.1.md: Shared pandoc PDF metadata
- Plan output and explain narration
- importlib
- proxmox-storage-drs

## God Nodes (most connected - your core abstractions)
1. `Group` - 206 edges
2. `PveClient` - 121 edges
3. `Disk` - 85 edges
4. `write_config()` - 80 edges
5. `Proxmox Storage DRS Implementation Plan` - 78 edges
6. `PrometheusClient` - 74 edges
7. `build_topology()` - 73 edges
8. `run()` - 72 edges
9. `client_with()` - 71 edges
10. `make_move()` - 69 edges

## Surprising Connections (you probably didn't know these)
- `The `Group <name> → ACT`/`NO ACTION` line` --references--> `GroupLoad`  [INFERRED]
  docs/manual/25-show-load-and-verify-storages.md → src/proxmox_storage_drs/loadmodel.py
- `The `objective:` line` --references--> `ObjectiveBreakdown`  [INFERRED]
  docs/manual/29-explain.md → src/proxmox_storage_drs/heuristic.py
- `Single reauthenticate-and-retry in _call` --references--> `PveClient`  [EXTRACTED]
  docs/internals/50-pve-api.md → src/proxmox_storage_drs/pve.py
- `staged_disks field unimplemented` --references--> `State`  [EXTRACTED]
  docs/internals/15-state.md → src/proxmox_storage_drs/state.py
- `What `plan` does not yet do` --references--> `GroupLoad`  [INFERRED]
  docs/manual/27-plan.md → src/proxmox_storage_drs/loadmodel.py

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
- **Move completion: task OK, source released, VM unlocked** — docs_manual_28_apply_move_done_definition, docs_manual_28_apply_draining [INFERRED 0.85]
- **plan report output pipeline** — docs_manual_27_plan_solver_line, docs_manual_27_plan_payback_line, docs_internals_40_cli_and_logging_no_moves_made, docs_internals_40_cli_and_logging_unfixable_shortfall_report, docs_manual_27_plan_json_output [INFERRED 0.85]
- **Reserve/free space is never traded for balance** — docs_manual_27_plan_repair_exempt, docs_internals_95_schedule_deadlock_report, docs_internals_40_cli_and_logging_unfixable_shortfall_report, docs_manual_10_configuration_free_space, docs_manual_10_configuration_snapshot_reserve_factor [INFERRED 0.85]
- **Reserve and free-space safety invariants** — implementation_plan_c5_reserve, implementation_plan_snapshot_reserve, implementation_plan_free_space_config, implementation_plan_transient_invariant, implementation_plan_lexicographic_solve [INFERRED 0.85]
- **Heuristic and MILP share feasibility/objective functions** — docs_internals_90_heuristic_evaluate_assignment, docs_internals_60_topology_reserve_evaluator, docs_internals_91_optimize_shared_constraints_c1_c5, docs_internals_91_optimize_lexicographic_solve [INFERRED 0.85]
- **Storage cooldown enforcement across backends** — docs_manual_10_configuration_gates, docs_internals_90_heuristic_storage_cooldown_destination, docs_internals_91_optimize_storage_cooldown_both_stages [INFERRED 0.85]
- **Tiny-disk (EFI/TPM) free reunion with VM** — docs_manual_10_configuration_migration_tiny_disk_bytes, docs_internals_95_schedule_tiny_disk_first, docs_manual_27_plan_payback_line [INFERRED 0.85]
- **Domain safety invariants that must not be optimised away** — agents_domain_invariants_dry_run_default, agents_domain_invariants_snapshot_reserve, agents_three_floors_precedence, implementation_plan_transient_invariant, agents_finished_task_not_finished_move, agents_domain_invariants_never_auto_delete, agents_never_overprovision [EXTRACTED 1.00]
- **Operator onboarding flow: install, credential, verify metrics, plan, apply, monitor** — readme_debian_package_release, docs_manual_00_installation_pve_credential, readme_verify_metrics, readme_plan_explain, readme_apply_execution_modes, implementation_plan_monitoring_status_file [INFERRED 0.85]
- **Debian packaging, CI and release chain** — implementation_plan_debian_first, agents_autopkgtest, agents_ci_pipelines, agents_release_procedure, readme_debian_package_release [INFERRED 0.85]

## Communities (158 total, 23 thin omitted)

### Community 0 - "build_topology"
Cohesion: 0.06
Nodes (101): Disk-cooldown pin is not exempted for reserve repair, vm_config returns pending value; vm_pending exposes both, The cluster topology could not be built from the API responses. See…, TopologyError, disk_state_key(), ``"<group>:<vmid>:<device>"`` (section 11.2) -- the group prefix is what keeps…, build_topology(), pending_disk_reasons() (+93 more)

### Community 1 - "MonkeyPatch"
Cohesion: 0.05
Nodes (96): _all_pinned_sample_topology(), _fake_build_topology(), _fake_reconcile_inflight(), _patch_show_load_deps(), _patch_show_load_forecast(), CaptureFixture, Exception, MonkeyPatch (+88 more)

### Community 2 - "execute.py"
Cohesion: 0.05
Nodes (92): ExcludeConfig, _advance_pending(), _auto_budget_stop_outcome(), _check_lock_once(), Clock, _confirm_decision(), _deadline_exceeded(), _detect_orphan_volumes() (+84 more)

### Community 3 - "generate_expected.py"
Cohesion: 0.06
Nodes (80): The `payback:` line, The `objective:` line, Freshness: why every run rewrites the file, Monitoring: the status file, What is in the file, What makes a run `OK`, `WARNING` or `CRITICAL`, Wiring it into Nagios/NRPE, itertools (+72 more)

### Community 4 - "ObjectiveBreakdown"
Cohesion: 0.06
Nodes (72): What this build actually implements, shutil, _fragmented_vms(), _load_per_tib(), _log_payback_verdict(), _log_plan_selected(), _objective_breakdown_json(), _pin_action_hint() (+64 more)

### Community 5 - "test_config.py"
Cohesion: 0.09
Nodes (70): ConfigError, The configuration file is missing, unreadable or fails validation. See…, minimal_config_dict(), Any, parametrize, Path, skipif, The smallest config that passes structural + semantic validation. (+62 more)

### Community 6 - "Topology"
Cohesion: 0.06
Nodes (67): The whole cluster's worth of groups, as seen by this run. By the time anything…, Topology, _fragmented_group(), _make_group_plan(), _moved_outcome(), _one_disk_group(), _one_disk_group_load(), _one_move() (+59 more)

### Community 7 - "test_statusfile.py"
Cohesion: 0.06
Nodes (63): CompletedProcess, contextlib, datetime, `report`, `report.warn_pinned_load_fraction`, needs_plugin, os, DrsError (+55 more)

### Community 8 - "topology.py"
Cohesion: 0.06
Nodes (64): concurrent_futures, re, GroupConfig, StorageConfig, _allowed_formats(), _build_storages(), _check_cross_group_uniqueness(), _ClusterData (+56 more)

### Community 9 - "test_cli.py"
Cohesion: 0.04
Nodes (47): str, _FakeClient, _gate(), _no_move_schedule(), _NodeNamesClient, _outcome(), Any, LogCaptureFixture (+39 more)

### Community 10 - "test_execute.py"
Cohesion: 0.10
Nodes (60): client_with(), default_group(), make_move(), A move missing from `move_costs_by_key` is never refused for lack of an…, Section 13: `state.json` must learn about a UPID *before* this function goes on…, Not only the happy path -- a `move_disk` task that itself fails still finished…, `dry-run` never calls `move_disk` at all -- the callbacks must simply never…, `ExecutionConfig()`'s own defaults (both caps `1`) must dispatch to the… (+52 more)

### Community 11 - "run_concurrent"
Cohesion: 0.08
Nodes (52): ExecutionConfig, LocksConfig, concurrent_client_with(), log_messages(), datetime, LogCaptureFixture, REVIEW.md T-06: a lock-timeout `"skipped"` outcome never issued `move_disk`, so…, The defining property of concurrency: `move_disk` for the second move is issued… (+44 more)

### Community 12 - "ResolvedConfig"
Cohesion: 0.08
Nodes (58): Crash and two-instance recovery: crashrecovery.py, Mutable state box narrow exception to functional style, Startup scan folds excluded vmids before planning, Namespace, _apply_exit_code(), _apply_payback_gate(), _compute_group_load(), _dump_report_json() (+50 more)

### Community 13 - "_patch_plan_deps"
Cohesion: 0.08
Nodes (56): ExecutionResult, One group's ``execute_plan()`` call. ``stopped_early`` is true for any reason…, _balanced_apply_group_load(), _balanced_apply_topology(), _check_statusfile(), _monitored_config(), _patch_plan_deps(), Two evenly-sized, evenly-loaded disks on one storage, none on the other, no… (+48 more)

### Community 14 - "Storage"
Cohesion: 0.09
Nodes (56): MigrationConfig, compute_benefit_load_seconds(), compute_move_cost(), evaluate_plan_payback(), Section 7.1's cost for one scheduled move. Only ``source`` is needed (not the…, Section 7.2: ``benefit = (alpha*(E_before - E_after) + delta*(F_before -…, Section 7.3: the aggregate acceptance test over a whole plan, plus the hard…, One storage in a group, with the data section 5.3's constraints need. (+48 more)

### Community 15 - "test_optimize.py"
Cohesion: 0.10
Nodes (56): cbc_available(), Group, One storage group: section 5's independent optimization unit., make_disk(), make_storage(), LogCaptureFixture, MonkeyPatch, parametrize (+48 more)

### Community 16 - "GroupLoad"
Cohesion: 0.09
Nodes (54): GatesConfig, evaluate_group_gates(), _l1_drift(), Section 6, applied in the order it lists: reserve override, then the capacity…, ``(‖ℓ_last‖₁, ‖ℓ_now − ℓ_last‖₁)`` over the **union** of disk keys present in…, GroupLoad, Convenience for callers (``show-load``) keying off `Disk.key`., One storage's current `L_s`/`u_s`, at the assignment `Disk.current_storage`… (+46 more)

### Community 17 - "metrics.py"
Cohesion: 0.08
Nodes (52): MetricLabels, MetricsConfig, WindowConfig, _check_coverage(), _check_cross_metric_disk_consistency(), _check_device_label_collision(), _check_metric_names_exist(), _check_observed_spacing() (+44 more)

### Community 18 - "test_anonymize.py"
Cohesion: 0.06
Nodes (43): make_mapper(), MonkeyPatch, parametrize, Path, A node and a storage that happen to share a name must not collide., Section 16.3: 'the result never depends on iteration order'., Force two different vmids to hash to the same base slot and confirm both still…, X-09: `vmid`'s own linear probing makes a collision impossible, but nothing did… (+35 more)

### Community 19 - "Disk"
Cohesion: 0.08
Nodes (49): ObjectiveConfig, _capacity_spread(), Section 5.3 (C7)'s `(max_s b_s - min_s b_s) / b_bar`, or ``None`` when the gate…, group_average_fill(), group_average_utilization(), `u* = (Sum_d l_d) / (Sum_s c_s)` (C6) -- a constant under any reassignment of…, `b_bar = (Sum_d z_d + Sum_s U^ext) / (Sum_s C_s)` (section 5.3 (C7)) -- a…, _cbc_capacity_spread_term() (+41 more)

### Community 20 - "test_metrics.py"
Cohesion: 0.10
Nodes (47): PrometheusClient, Thin wrapper over the Prometheus HTTP API. See section 3.4/3.5. ``session`` is…, _all_metric_names(), FakeResponse, FakeSession, _full_metrics_config(), MonkeyPatch, Prometheus client, PromQL builders and verify-metrics. No test here talks to a… (+39 more)

### Community 21 - "loadmodel.py"
Cohesion: 0.07
Nodes (46): _RawTimeSeries, _aggregate_storages(), _blend_loads(), _combine_raw_values(), _combined_raw(), compute_disk_load_series(), _fetch_all_raw_quantities(), _fetch_all_raw_quantity_series() (+38 more)

### Community 22 - "test_collect.py"
Cohesion: 0.08
Nodes (44): capture(), _mapper(), Path, X-08: section 16.1's manifest line ("schema, versions, what was captured...")…, X-08: section 16.3 promises the manifest "flags" a non-node-shaped…, Z-03: `resolve_node_selector()`'s tier-1 precedence used to win on *both* sides…, A live capture against the dev cluster found the previous implementation's bug…, verify_metrics() never carries a node selector at all -- nothing to rewrite,… (+36 more)

### Community 23 - "compute_group_load"
Cohesion: 0.16
Nodes (45): LoadWeights, compute_group_load(), Compute one group's :class:`GroupLoad` for this run. Section 4.…, _client(), full_coverage(), make_disk(), make_storage(), 2/2 samples -- `expected_samples` for WINDOW/METRICS above is 2. (+37 more)

### Community 24 - "Configuration reference"
Cohesion: 0.05
Nodes (44): Configuration reference, `forecast.holt_winters.seasonal`, `forecast.holt_winters.seasonal_periods`, `forecast.holt_winters.trend`, forecast.model (quantile, holt_winters), `forecast` — placing disks for the load they will have, `free_space.hard`, `free_space` — keep N bytes (or N%) free on top of the snapshot reserve (+36 more)

### Community 25 - "test_replay.py"
Cohesion: 0.11
Nodes (42): PrometheusConfig, _captured_step(), _config_from_bundle(), _free_space_pairs(), MonkeyPatch, Path, AH-06: a live ``free_space`` config is collected as the resolved per-storage…, Section 16.5's one deliberate exception: a bundle captured before section 3.8… (+34 more)

### Community 26 - "test_validate_corpus.py"
Cohesion: 0.10
Nodes (43): tests_corpus, tests_corpus_validate_corpus, _case(), _invariant_inputs(), MonkeyPatch, needs_full_checkout, parametrize, Path (+35 more)

### Community 27 - "build_client"
Cohesion: 0.08
Nodes (38): The Proxmox VE API client, API token permission is intersection with owner, Best-effort ticket refresh tightening, build_client assembles auth once, bwlimit bytes/s to KiB/s conversion only in move_disk, Single reauthenticate-and-retry in _call, storage_content silently empty without Datastore.Allocate, storage_definitions uses the list form GET /storage (+30 more)

### Community 28 - "Internals: The heuristic solver"
Cohesion: 0.06
Nodes (37): Internals: Building the disk/storage/group model, (C2) format eligibility: storage_type/allowed_formats, D: every disk placed, pinned or not, Foreign usage U^ext (unreferenced volumes), Pending-change pin, Per-disk cooldown pin, Pin priority: _pin_reason(), reserve.py: shared (C4)/(C5) evaluator (+29 more)

### Community 29 - "fake_api"
Cohesion: 0.08
Nodes (37): proxmoxer, fake_api(), BaseException, _FakeHttpsBackend, _FakeProxmoxApiWithBackend, _FakeTicketAuth, Section 9.2: "convert at the call site and nowhere else" -- this is that site., A ticket that expired for reasons external to this call (a long confirm-mode… (+29 more)

### Community 30 - "BundleError"
Cohesion: 0.12
Nodes (19): BundleError, A diagnostic bundle (IMPLEMENTATION_PLAN.md section 16) could not be written or…, bundle_reference_now(), load_manifest(), _NeverSession, _parse_step_seconds(), Any, datetime (+11 more)

### Community 31 - "schedule.py"
Cohesion: 0.09
Nodes (38): compute_reserve_status(), (C4)/(C5) evaluated for one storage at the assignment ``storage_of`` encodes.…, ``size_bytes`` rounded *up* to the next whole MiB, in bytes. Up, never to…, IMPLEMENTATION_PLAN.md section 8.1's transient invariant, generalized to an…, round_up_to_mib(), transient_charge_ok(), make_disk(), make_storage() (+30 more)

### Community 32 - "schedule.py: Disk"
Cohesion: 0.10
Nodes (33): dataclasses, Section 6: decide whether to act on a group at all, before the solver runs.…, Migration cost and the payback acceptance test. See IMPLEMENTATION_PLAN.md…, _current_storage(), largest_disk_bytes(), managed_used_bytes(), The snapshot-reserve constraint. See IMPLEMENTATION_PLAN.md section 5.3…, Z_s: the largest disk on ``storage_id`` under ``storage_of``, 0 if none (C4). (+25 more)

### Community 33 - "test_logging_setup.py"
Cohesion: 0.10
Nodes (36): ast, io, configure_logging(), floor_for_command(), JsonFormatter, The mandatory ``INFO`` floor of section 2.3, or ``None``. A run that can change…, Install this run's log handler. Called once, from ``main()``. ``floor`` is…, Render one :class:`logging.LogRecord` as one JSON line. (+28 more)

### Community 34 - "Manual: Configuration reference"
Cohesion: 0.06
Nodes (37): drs.example.yaml (reference configuration), free_space soft_s/hard_s resolution, exclude rules, free_space.soft / free_space.hard, load_weights, `metrics.extra_selector`, `metrics.labels.device`, `metrics.labels.node` (+29 more)

### Community 35 - "test_documentation.py"
Cohesion: 0.10
Nodes (34): argparse, importlib_resources, sys, _flatten_schema_keys(), _load_schema(), _manpage_source_text(), _manual_documented_keys(), Any (+26 more)

### Community 36 - "TimeWindow"
Cohesion: 0.15
Nodes (34): date, TimeWindow, current_deadline(), _day_name(), is_window_active(), _parse_hhmm(), datetime, ``execution.time_windows``: when ``auto`` mode may execute moves. See… (+26 more)

### Community 37 - "evaluate_assignment"
Cohesion: 0.11
Nodes (34): best_single_disk_alternative(), evaluate_assignment(), _movable_disks(), `D^mov` (section 5.3): disks (C2) has not fixed in place. A pinned disk's…, Section 5.5 step 1: "seed with the current assignment (not from scratch -- we…, Section 5.4's objective for one candidate ``assignment``.…, The single-disk move closest to being worth taking, among every (movable disk,…, seed_assignment() (+26 more)

### Community 38 - "ExecutionConfig"
Cohesion: 0.13
Nodes (32): SourceReleaseConfig, _group_with_types(), make_disk(), make_storage(), parametrize, Section 9.3: a source_release timeout "does not fail the run: mark the storage…, Same as above, except the second move's *target* -- not source -- is the…, Section 9.3 point 3: PVE's own `saferemove_throughput` (already read live off… (+24 more)

### Community 39 - "main"
Cohesion: 0.07
Nodes (33): ArgumentParser, CommandHandler, _accumulate_move_stats(), apply_mode_override(), build_parser(), _fallback_manual_text(), _log_run_summary(), main() (+25 more)

### Community 40 - "Path"
Cohesion: 0.08
Nodes (30): load_config(), Resolve, read, parse and validate the configuration. See section 11 for…, Path, Section 13: a vmid `crashrecovery.reconcile_inflight()` reports is folded into…, REVIEW.md R-02: when the scheduler can only order *some* of the heuristic's…, Every real subcommand now has a real handler (``explain`` was the last one) so…, A real, on-disk diagnostic bundle -- built the same way test_collect.py does,…, X-10: `--replay ... --mode auto <cmd>` used to log `run_started` and an… (+22 more)

### Community 41 - "test_free_space_repair_fixture.py"
Cohesion: 0.11
Nodes (30): executed_assignment(), Assignment, Section 7.3: "what it will really run" -- ``final_assignment``…, Section 7.3's revert test, one verdict per scheduled move in ``order``: would…, repair_markers(), `Σ_s r_s` at the assignment ``storage_of`` encodes -- section 7.3's outcome…, total_shortfall_bytes(), _free_space_repair_group() (+22 more)

### Community 42 - "evaluate_assignment: test_heuristic.py"
Cohesion: 0.14
Nodes (31): compute_vm_weights(), Section 5.4's `w_v = max(1, l_v / l_bar)` -- the per-VM weight that scales…, Section 5.5's four-step heuristic (minus "polish"; see the module docstring),…, run_heuristic(), An idle group (every disk's load is 0) has no basis to weight one VM over…, Section 5.4: "l_v ... pinned disks included -- their I/O is the VM's I/O",…, Section 5.4: minmax is `t >= u_s` -- the hottest storage's own u_s, not its…, The heuristic solver. See proxmox_storage_drs/heuristic.py. Cross-checked… (+23 more)

### Community 43 - "collect.py"
Cohesion: 0.09
Nodes (29): functools, gzip, _anonymize_captured_prometheus(), _anonymize_prometheus_series(), _anonymize_query_text(), Bundle, CallRecord, _dump_json() (+21 more)

### Community 44 - "Config"
Cohesion: 0.10
Nodes (30): _check_connection_config(), _check_forecast_window(), _check_group_size(), _check_group_storage_membership(), _check_metrics(), _check_objective_weights(), _check_payback_horizon(), _check_schema_version() (+22 more)

### Community 45 - "pve.py"
Cohesion: 0.07
Nodes (15): Run one ``proxmoxer`` call, wrapping every failure as :class:`PveApiError`.…, ``GET /cluster/resources?type=vm``: VM inventory., ``GET /cluster/tasks``: recent/active tasks across **every** node -- the one…, ``GET /cluster/resources?type=storage``: storage inventory., ``GET /nodes``: every node in the cluster, by name. Section 3.4's node-scoping…, ``GET /version``: the running PVE's own version string (section 16.1/16.3's…, ``GET /storage``: every storage's full config, including ``saferemove``.…, ``GET /nodes/{node}/qemu/{vmid}/config``: disk -> storage mapping and size.… (+7 more)

### Community 46 - "order_moves"
Cohesion: 0.14
Nodes (29): order_moves(), Section 8.2's scheduling loop for one group. ``target_assignment`` is normally…, make_disk(), make_storage(), _one_move_that_would_leave_san_b_slightly_short(), The plan's own arithmetic: move 1 -> 5.0 <= 8.0, move 2 -> 4.5 <= 8.0, move 3…, A storage with no existing disks and a tiny arriving one must still reserve…, Two disks, both storages already full: the target assignment swaps them, which… (+21 more)

### Community 47 - "Dry-run is the default"
Cohesion: 0.09
Nodes (29): autopkgtest runtime-dependency check, GitHub Actions and Salsa GitLab CI pipelines, Dry-run is the default, Release procedure (version bump, changelog, debian/ tag, graphify commit), Monitoring status file (statusfile.py), /etc/pve/drs.yaml on pmxcfs, Installation and requirements (manual), state.json (node-local state) (+21 more)

### Community 48 - "pseudonym"
Cohesion: 0.10
Nodes (18): `metrics.labels.vmid`, `proxmox.auth.token_id`, Mapper, pseudonym(), ``HMAC-SHA256(salt, kind || "\\0" || value)``, truncated to 8 hex chars.…, The stateful half of anonymization: one instance per bundle capture. ``vmid``…, The pseudonym for a vmid already passed to :meth:`register_vmids`. ``None`` for…, ``node-<8 hex>``, or ``node-<8hex>.<8hex>.invalid`` for an FQDN -- shape… (+10 more)

### Community 49 - "._get"
Cohesion: 0.08
Nodes (19): Protocol, decimate_to_configured_step(), _disk_keys_seen(), Any, The inverse of :func:`safe_range_step_seconds`: recover a series at…, The subset of ``requests.Response`` this module relies on., The subset of ``requests.Session`` this module relies on. A structural type…, Issue one request and return the decoded ``data`` field. Typed ``Any`` rather… (+11 more)

### Community 50 - "State"
Cohesion: 0.12
Nodes (29): Section 11.2: ``last_balance``/cooldowns are "updated only after a run that…, _record_executed_moves(), Cooldowns, LastBalance, load_vector_for_group(), now_iso(), ``at`` is ``None`` before any run has ever executed a migration -- distinct…, This group's slice of ``last_balance.load_vector``, re-keyed from… (+21 more)

### Community 51 - "heuristic.py"
Cohesion: 0.12
Nodes (24): _RepairCandidate, _best_of(), _best_repair_candidate(), trial_storage_of(), _descend(), storage_of(), HeuristicResult, Assignment (+16 more)

### Community 52 - "free_space requirement soft_s / hard_s"
Cohesion: 0.13
Nodes (27): Snapshot reserve never traded for balance, Higher bar for safety-critical modules, Three floors precedence f_s*Z_s > hard_s > soft_s, Big-M penalty P fallback (computed P_min), (C4) Largest-disk linearization Z_s, C5 Capacity, snapshot reserve and free space, Generalized concurrent-move invariant / concurrency_ok, Failure modes and safety table (+19 more)

### Community 53 - "empty_state"
Cohesion: 0.17
Nodes (27): flock is the lock; JSON lock field is only a label, acquire_lock(), empty_state(), load_state(), First-run state: no lock, no recorded balance, no cooldowns, nothing in flight…, Best-effort read of ``path``. See the module docstring: a missing file is the…, Section 11.2's advisory lock: ``fcntl.flock(LOCK_EX | LOCK_NB)`` on ``path``…, Clears the descriptive ``lock`` field and releases the OS-level lock, writing… (+19 more)

### Community 54 - "Payback rule and acceptance test"
Cohesion: 0.13
Nodes (27): Affinity repair under payback fixture, beta term: number of migrations, bwlimit is the only throttle (saturation guard removed), C1 Assignment, (C3) VM affinity linking, (C8) Small disks follow their VM, Data spread as tunable delta preference, delta term: data spread / failure risk (+19 more)

### Community 55 - "anonymize.py"
Cohesion: 0.09
Nodes (20): hashlib, hmac, pathlib, proxmox_storage_drs, _check_no_pseudonym_collision(), generate_new_salt(), load_or_create_salt(), _pseudonym_int() (+12 more)

### Community 56 - "Proxmox Storage DRS Implementation Plan"
Cohesion: 0.12
Nodes (26): Anonymization allowlist, never denylist, Migrations throttled by bwlimit only, C7 Capacity-spread linearization, Capacity spread gate (default 0.25), Configuration and validation rules, Dependencies come from Debian (trixie), Diagnostic bundles (collect-testdata), Proxmox Storage DRS Implementation Plan (+18 more)

### Community 57 - "make_config"
Cohesion: 0.13
Nodes (26): make_config(), make_prometheus_client(), make_pve_client(), --no-series must skip the big, per-group superset range captures -- it does not…, Y-06: the manifest's version fields are machine-generated provenance, not free…, X-09: the printed query count used to treat a multi-day range as one range…, Z-05: a live capture stores every range series at…, Section 3.8/16.3: a real pending edit on the VM's own disk survives as the… (+18 more)

### Community 58 - ".agents/ index"
Cohesion: 0.09
Nodes (22): Config knob entry: type, default, unit, extremes, interactions, Tests keeping docs honest (help covers options, manual covers config), --help generated from argparse definitions, no hardcoded defaults, Internals pages: question first, name modules, explain why, ASCII diagrams, Manpage skeleton with complete OPTIONS, config/drs.example.yaml as documentation that parses, Change behaviour and documentation in the same commit, PDF is a build product; fix text not LaTeX (+14 more)

### Community 59 - "Proxmox VE API"
Cohesion: 0.09
Nodes (25): Allowlist-never-denylist anonymization, Per-disk blockstat via pvestatd/InfluxDB/Telegraf/Prometheus, Diagnostic bundle directory format, collect-testdata diagnostic bundle, tests/corpus and scrub audit, Datastore.Allocate needed for storage content listing, Disk identity join (vmid, device), gigapipe on ClickHouse backend (+17 more)

### Community 60 - "config.py"
Cohesion: 0.13
Nodes (24): jsonschema, ruamel_yaml, ruamel_yaml_error, _build_config(), FreeSpaceConfig, FreeSpaceValue, _load_schema(), MonitoringConfig (+16 more)

### Community 61 - "capture_bundle"
Cohesion: 0.15
Nodes (21): _handle_collect_testdata(), Section 16.4. Always the real clients -- collect-testdata needs a live cluster…, _build_manifest(), capture_bundle(), _capture_prometheus_files(), capture_range_seconds(), CaptureEstimate, CaptureLog (+13 more)

### Community 62 - "crashrecovery.py"
Cohesion: 0.15
Nodes (22): cluster/tasks vs task_status conventions differ, parse_upid PVE UPID grammar confirmed live, reconcile_inflight: recorded UPIDs plus foreign scan, AuthConfig, expected_task_user(), parse_upid(), The local half of the startup scan: re-checks every UPID ``state.json`` already…, The cluster-wide half: a still-running ``qmmove`` task from this tool's own… (+14 more)

### Community 63 - "stitch_range_results"
Cohesion: 0.09
Nodes (17): RangeStepMismatch, ``--replay`` found the requested range query, but at a different step than this…, _issue_chunked_range_query(), Any, ``client.range_query()``, issued in ``RANGE_QUERY_CHUNK_SECONDS``-sized sub-…, Merges several ``(start, end, result)`` ``query_range`` captures of the *same*…, stitch_range_results(), _RangeStepMismatchFakeClient (+9 more)

### Community 64 - "state.py"
Cohesion: 0.14
Nodes (21): Cooldown data stored here, interpreted by topology and heuristic, errno, fcntl, socket, _active_cooldowns(), active_disk_cooldowns(), active_storage_cooldowns(), cooldown_remaining_seconds() (+13 more)

### Community 65 - "ForecastReport"
Cohesion: 0.11
Nodes (21): _log_forecast(), Any, ``-v``'s addition to ``explain`` (section 3.4): exactly which query every…, ``explain``'s one line on what the forecast did to this group's loads., Section 12.1 point 6: one line per group, not one per disk. A failed backtest…, _render_collect_testdata_human(), _render_explain_data_source_line(), _render_explain_human() (+13 more)

### Community 66 - "FakePrometheusSession"
Cohesion: 0.13
Nodes (20): FakePrometheusSession, A ``metrics._SessionLike`` double capable of answering *many* distinct queries…, _instant_answer(), Any, BaseException, _Raise, _range_answer(), A live capture against the dev cluster found this one directly (section 16.3's… (+12 more)

### Community 67 - "_run_two_onto_san_c"
Cohesion: 0.10
Nodes (21): A `san-c` content responder plus a `move_disk` responder for 201. The listing…, 201's mirror target is already *listed* on san-c at its full 1 TiB by the time…, Between different storage types, or from thin to thick, `move_disk` allocates…, The match stays narrow: a same-VM volume that appeared after launch but has…, The exclusion is narrow: only 201's *own* mirror target (same VM, the disk's…, Between different storage types the target is allocated at the disk line's…, The same 2 TiB config `size=` and the same 4.5 TiB already on the target, but…, Section 5.3.1's `hard_b` -- resolved once onto `Storage. free_space_hard_bytes`… (+13 more)

### Community 68 - "test_small_disks.py"
Cohesion: 0.18
Nodes (21): current(), disk(), efi_repair_group(), parametrize, skipif, VM 301's big disks live in another group: its efidisk0 is alone here and never…, "slow" is short by 1000.2 MiB, so moving the 528 KiB EFI disk crosses a whole-…, Lexicographic stage 1 takes any shortfall reduction, however small, so without… (+13 more)

### Community 69 - "Reading `apply`"
Cohesion: 0.11
Nodes (20): cli.py backend dispatch: auto cascades, explicit falls back, gates (drift, imbalance, capacity spread, cooldowns), solver.backend (auto, cbc, heuristic), `solver.heuristic_iterations`, `solver.mip_gap`, `solver.time_limit_seconds`, `solver` — which backend plans, A negative `saferemove_throughput` is normal (+12 more)

### Community 70 - "PveClient"
Cohesion: 0.21
Nodes (20): Two failure modes, one in-flight UPID mechanism, Section 13's startup scan. Returns the vmids to exclude from this run's…, reconcile_inflight(), PveClient, One method per IMPLEMENTATION_PLAN.md section 3.5 endpoint. ``api`` is typed…, The same in-flight move already recorded in state.json also shows up in the…, Startup crash/two-instance recovery. See proxmox_storage_drs/crashrecovery.py., test_reconcile_assumes_still_running_when_the_check_itself_fails() (+12 more)

### Community 71 - "test_forecast.py"
Cohesion: 0.16
Nodes (18): Collection, random, forecast_group(), One group's forecast: run the backtest on the group aggregate, and only if…, _group_series(), _noise_series(), TimeSeries, Holt-Winters forecasting, its backtest gate, and the required-range rule. (+10 more)

### Community 72 - "20-verifying-metrics.md"
Cohesion: 0.10
Nodes (20): A reference implementation that is well tested, gigapipe with ClickHouse (reference backend), PVE InfluxDB external metric server, instance label collision, OpenTelemetry metric server rejected, Other backends, RRD rejected as data source, Six per-disk blockstat counters (+12 more)

### Community 73 - "pytest"
Cohesion: 0.11
Nodes (16): fixture, json, logging, LogRecord, pytest, json_safe(), One human-readable line per record: ``LEVEL: message``. Deliberately not a…, ``auto`` and ``text`` -> ``"text"``; ``json`` -> ``"json"``. JSON is opt-in. It… (+8 more)

### Community 74 - "forecast.py"
Cohesion: 0.15
Nodes (18): math, HoltWintersConfig, Backtest, holt_winters_quantile(), TimeSeries, _quantile(), One group's backtest: absolute error of each model's predicted p95 of ``[now-W,…, Section 10.2's backtest, comparing against a baseline: fit on ``[now-2W,… (+10 more)

### Community 75 - "20-verifying-metrics.md: Manual: Configuration reference"
Cohesion: 0.22
Nodes (12): .agents/ index, Python style (.agents), black vs flake8 disagreements (E203, W503, E704), One implementation of every rule (MILP and heuristic share), Units in names, Manual: Configuration reference, If it fails, Running it (+4 more)

### Community 76 - "move_disk (drive-mirror, delete=1)"
Cohesion: 0.15
Nodes (19): approximate-size fallback for qcow2-on-LVM volumes, Mandatory INFO audit floor for confirm/auto runs, (C2) Eligibility via variable fixing, Errors are not mismatches, Structured log event catalogue, Execution modes dry-run, confirm, auto, Logging policy (two audiences, levels, audit floor), Which disks can move online (all buses, efidisk0, tpmstate0, unused) (+11 more)

### Community 77 - "Mapper"
Cohesion: 0.15
Nodes (19): filter_allowed_fields(), Drop every key of ``obj`` not in ``allowed``. The one primitive both the…, The one meaningful value a snapshot ``name`` field can carry is the literal…, sanitize_snapshot_name(), _anonymize_cluster_tasks(), _anonymize_node_list(), _anonymize_storage_content(), _anonymize_storage_definitions() (+11 more)

### Community 78 - "Any"
Cohesion: 0.25
Nodes (5): _guarded(), Any, Run ``fn()``, recording its outcome in ``log``. Returns ``None`` (and records…, Wraps a real, already-authenticated :class:`PveClient` and records every call's…, RecordingPveClient

### Community 79 - "empty_state: test_state.py"
Cohesion: 0.16
Nodes (18): ``state.path`` could not be written, or its advisory lock could not be…, StateError, _pid_alive(), Temp file in the same directory, ``fsync``, then ``os.replace`` -- a reader…, Best-effort, used only to make a "still held" log message useful to an operator…, save_state_atomic(), skipif, The `finally` block's own cleanup, pinned directly rather than only inferred… (+10 more)

### Community 80 - "cli.py"
Cohesion: 0.14
Nodes (15): _make_confirm_move_interactively(), confirm(), Section 5.3's "report any residual `r_s > 0` prominently as an unfixable…, The human form of :class:`_UnfixableShortfall` -- printed whether or not the…, Builds ``execute.py``'s ``ConfirmCallback`` -- the only ``input()`` call in…, Section 4's per-storage `L_s`/`u_s` and per-disk size/measured-load/ pin…, _render_plan_move_line(), _render_storage_and_disk_load_lines() (+7 more)

### Community 81 - "loadmodel.py: safe_range_step_seconds()"
Cohesion: 0.11
Nodes (18): build_vmid_selector(), combine_selectors(), group_query_selectors(), The step to actually send Prometheus for a ``rate()``-based ``query_range``…, :func:`build_node_selector`'s counterpart for the numeric vmid label:…, Joins already-built ``label=~"..."``-shaped selector fragments (e.g.…, Splits ``vmids`` into fixed-size, sorted, deterministic batches -- the *only*…, The selector(s) a caller should issue one query per, for one group's own raw-… (+10 more)

### Community 82 - "_handle_apply"
Cohesion: 0.19
Nodes (17): Inflight UPIDs written and read for crash recovery, Rename-detaches-flock bug and in-place locked write, Write UPID to disk before the crash can happen, _make_inflight_callbacks(), on_finished(), on_started(), Builds the ``on_inflight_started``/``on_inflight_finished`` pair…, LockHandle (+9 more)

### Community 83 - "MoveCost"
Cohesion: 0.14
Nodes (13): MoveCost, Section 7.1's cost for one already-scheduled move., REVIEW.md R-05: an economic failure (benefit < ratio*cost) and a hard per-move…, test_render_plan_payback_lines_separates_economic_and_duration_failures(), make_result(), FakeClock, Section 9.1: the pre-loop time-window check (above) only knows the answer as of…, REVIEW.md T-06's collateral bug: before the fix, this "skipped" outcome let the… (+5 more)

### Community 84 - "00-installation.md"
Cohesion: 0.16
Nodes (16): fc-tier1 / reserve-tradeoff acceptance fixtures, AGENTS.md working agreement, AGPL-3.0-or-later licence and SPDX headers, black/flake8 E203 W503 E704 ignores, Branch-first git workflow, 85% coverage floor, Documentation pipeline (make docs / docs-check), make check (+8 more)

### Community 85 - "`execution` — how (and whether) moves actually happen"
Cohesion: 0.12
Nodes (16): `execution.abort_on_failure`, `execution` — how (and whether) moves actually happen, `execution.locks.on_timeout`, `execution.locks.poll_interval`, `execution.locks.task_retry_backoff`, `execution.locks.task_retry_limit`, `execution.locks.wait_timeout`, `execution.max_concurrent_migrations` (+8 more)

### Community 86 - "Load model (average in-flight I/O)"
Cohesion: 0.15
Nodes (16): Backtest gate: beat persistence baseline, Storage capability weight and utilization u_s, CP-SAT (ortools) backend, removed, Drift gate (L1 norm, default 0.10), Forecast scales l_d by f_d/h_d, Holt-Winters forecasting and backtest gate, gigapipe step >= range workaround, Holt-Winters seasonal forecast (engine-side) (+8 more)

### Community 87 - "pve-storage-drs.1.md"
Cohesion: 0.12
Nodes (15): AUTHOR, COLLECT-TESTDATA OPTIONS, COMMANDS, CONFIGURATION, COPYRIGHT, DESCRIPTION, ENVIRONMENT, EXIT STATUS (+7 more)

### Community 88 - "PrometheusClient"
Cohesion: 0.25
Nodes (15): Gigapipe step workaround, Metrics page, Node-scoping selector, PrometheusClient, PromQL builders, Range query chunking, SessionLike protocol, verify_metrics six checks (+7 more)

### Community 89 - "Internals: CLI dispatch and logging"
Cohesion: 0.14
Nodes (14): Internals: CLI dispatch and logging, Global options on top-level parser, Command handlers dispatched via dict, JsonFormatter, Structured logs go to stderr, Log levels, mandatory floor, handler on root, --manual prefers man(1), falls back to in-tree markdown, --manual prefers man(1), falls back to plain text (+6 more)

### Community 90 - "test_plan_gate_also_reflects_real_drift_history_from_state_json"
Cohesion: 0.15
Nodes (15): DiskLoad, One disk's `ℓ_d`. Section 4., _balanced_non_violating_topology(), _imbalanced_group_load(), _no_reserve_violation_topology(), Unlike `_sample_topology()`, san-a here does *not* violate (C5) -- needed to…, Two storages, generously sized -- unlike `_sample_topology()`, no (C4)/(C5)…, san-a all the load, san-b none -- imbalance is 200% of `u*`, far above the… (+7 more)

### Community 91 - "Reading `apply`: Reading `apply`"
Cohesion: 0.14
Nodes (13): Concurrent execution, Crash and two-instance recovery, Failure and `abort_on_failure`, `--json`, Reading `apply`, Reading `auto` mode, `state.json`: what a real run actually changes, The `[y]es/[n]o skip/[a]ll remaining/[q]uit` prompt (+5 more)

### Community 92 - "disk_factors"
Cohesion: 0.27
Nodes (13): disk_factors(), ``f_d / h_d`` for every disk that has one: ``f_d`` the Holt-Winters forecast…, _factor_series(), _FixedForecast, MonkeyPatch, 96 hourly samples whose last 24 are ``window_values`` (repeated)., Patches ``holt_winters_quantile`` to a constant so the ratio is exact., test_disk_factors_is_forecast_over_observed_p95() (+5 more)

### Community 93 - "test_affinity_repair_fixture.py"
Cohesion: 0.23
Nodes (13): Section 7.2's unweighted ``F`` -- ``sum(d_s)``, always L1 regardless of…, raw_capacity_spread(), _affinity_repair_group(), _loads(), _make_disk(), _make_storage(), parametrize, tests/fixtures/affinity-repair.yaml, built as real topology objects. (+5 more)

### Community 94 - "loadmodel.py: build_rate_promql()"
Cohesion: 0.14
Nodes (14): build_quantile_over_time_promql(), build_rate_promql(), _format_promql_duration(), The section 3.4 per-metric rate expression. ``sum by (vmid, device)…, Wrap a rate expression in the section 3.4 quantile-over-time reduction.…, Render a duration as a PromQL range-vector selector, e.g. ``"300s"``. Always in…, A 14-day lookback is 1209600s -- ``f"{1209600:g}s"`` renders as…, Section 3.4: the selector goes *inside* `rate()`'s own vector selector, before… (+6 more)

### Community 95 - "Any: Any"
Cohesion: 0.18
Nodes (8): FakeResponse, FakeSession, no_coverage(), Any, 0/2 samples: present in the coverage series but with nothing in it., Answers `/api/v1/query` and `/api/v1/query_range` by the exact `query` param…, A ``range_query`` stand-in that returns caller-supplied data keyed by the exact…, _WindowTrackingFakeClient

### Community 96 - "AGENTS.md working agreement"
Cohesion: 0.18
Nodes (13): Git workflow (.agents), Branch first, decided from the task, Merge --no-ff on green make check, Release process (version, changelog, tag, graphify), Packaging, dependencies and CI (.agents), Autopkgtest as the dependency test, coinor-cbc and python3-pulp as Depends, Debian-first dependency policy (trixie) (+5 more)

### Community 97 - "State: _state_from_dict()"
Cohesion: 0.15
Nodes (13): LockInfo, _parse_state_text(), Any, Raises on any shape this module does not recognize -- the caller…, The tolerant-parse half of :func:`load_state`, factored out so…, Re-reads whatever is currently written through an already-open,…, Descriptive only -- see the module docstring's "Locking" section for why the…, _read_locked_state() (+5 more)

### Community 98 - "units.py"
Cohesion: 0.24
Nodes (12): parse_duration_seconds(), parse_size_bytes(), Parse a size into an integer byte count. Accepts a bare number (bytes) or a…, Parse a duration into seconds. Accepts a bare number (seconds) or a string like…, parametrize, Unit parsing/formatting. See proxmox_storage_drs/units.py., test_format_bytes(), test_format_duration_seconds() (+4 more)

### Community 99 - "fakes.py"
Cohesion: 0.22
Nodes (5): FakeProxmoxResource, FakeQueryResponse, Any, Shared test doubles. Not collected by pytest (no ``test_`` prefix).…, Matches ``metrics._ResponseLike``: ``.status_code`` and ``.json()``.

### Community 100 - "Group"
Cohesion: 0.19
Nodes (13): range_series(), `range_seconds`/`step_seconds`/`now_epoch_seconds` are the caller's own choice,…, A `query_range`-shaped series with an explicit `[[ts, value], ...]` matrix,…, Build a `PrometheusClient` over a `FakeSession` answering…, Under the default weights section 4's rescale is an exact identity, l_d(t) =…, Two disks whose iotime split flips between the two timestamps -- normalizing…, 101:scsi0 has no sample at t=300 at all (a shorter series than 102:scsi0's) --…, _series_client() (+5 more)

### Community 101 - "Overview page"
Cohesion: 0.29
Nodes (12): config.py depends on forecast.py, Module layout, Overview page, Seven-stage pipeline, Two solver backends, Backtest gate, Drift baseline is effective load, Forecast provenance report (+4 more)

### Community 102 - "Engine pipeline: collect, join, gate, solve, cost, order, execute"
Cohesion: 0.20
Nodes (12): Engine pipeline: collect, join, gate, solve, cost, order, execute, Move completion criterion stronger than task success, Per-disk and per-storage cooldowns, Deadlock and staging, Failure handling (orphans, partial plan, supervision loss), Move states mirroring, draining, done, Implementation phases 1-15, saferemove wipe and signed saferemove_throughput (+4 more)

### Community 103 - "Mapper: filter_vm_config_fields()"
Cohesion: 0.20
Nodes (11): MappingType, filter_disk_value_params(), filter_vm_config_fields(), filter_vm_pending_entries(), Any, The allowlisted subset of a disk value's ``key=value`` parameters…, ``VM_CONFIG_EXTRA_FIELDS`` plus every disk key matching…, Section 3.8/16.3: reduce ``vm_pending()``'s response to the one boolean signal… (+3 more)

### Community 104 - "Testing (.agents)"
Cohesion: 0.20
Nodes (11): Disks with snapshots pinned, Testing (.agents), Acceptance fixtures and generate_expected.py, 85 percent coverage floor, No network, no real sleep, deterministic ties in tests, Codecov configuration, CI installs toolchain from apt, never pip, GitHub Actions Tests workflow (+3 more)

### Community 105 - "Transient reserve invariant (operator explanation)"
Cohesion: 0.20
Nodes (11): Transient reserve invariant (operator explanation), Concurrent execution with strict FIFO launch, confirm prompt [y]es/[n]o/[a]ll/[q]uit, apply modes: dry-run, confirm, auto, Pre-flight live re-check before each move, auto re-plan loop, Decision trail events, --log-format text vs json (+3 more)

### Community 106 - "series_of"
Cohesion: 0.18
Nodes (9): Any, A diurnal series that *ends at its trough*: the last forecast point (one day…, series_of(), test_backtest_is_none_without_a_fit_half(), test_backtest_is_none_without_an_actual_half(), test_holt_winters_quantile_is_none_for_a_constant_series(), test_holt_winters_quantile_is_none_on_a_convergence_warning(), test_holt_winters_quantile_is_none_with_too_few_samples() (+1 more)

### Community 107 - "Execute page"
Cohesion: 0.36
Nodes (10): Auto mode time window, Concurrent execution, Execute page, execute_plan live revalidation, Four-condition done, Injectable Clock, Live transient check provisioned, Orphans reported never deleted (+2 more)

### Community 108 - "`proxmox` — the cluster API connection"
Cohesion: 0.20
Nodes (10): `proxmox.auth.password`, `proxmox.auth.token_secret`, `proxmox.auth.username`, `proxmox.ca_file`, `proxmox.host`, `proxmox.port`, `proxmox.read_workers`, `proxmox` — the cluster API connection (+2 more)

### Community 109 - "fake_api: PveApiError"
Cohesion: 0.20
Nodes (9): PveApiError, Exception hierarchy for the project. Every error the tool can raise…, The Proxmox VE API returned an error or an unusable response. See…, raise_pve_error(), raise_error(), raise_error(), raise_error(), test_authentication_error_is_wrapped() (+1 more)

### Community 110 - "_FakeSession"
Cohesion: 0.24
Nodes (7): _FakeProxmoxApiWithSession, _FakeSession, Any, Confirmed live against a real multi-VM cluster: `requests`'s own default…, A small `read_workers` (or the field's own minimum) must not shrink the pool…, test_apply_connection_pool_size_mounts_an_adapter_sized_to_read_workers(), test_apply_connection_pool_size_never_shrinks_below_the_requests_default()

### Community 111 - "build_node_selector"
Cohesion: 0.22
Nodes (9): node_names uses GET /nodes, build_node_selector(), _escape_promql_regex_literal(), Escape one literal string for safe use inside a PromQL/RE2 ``=~`` alternation.…, Section 3.4's auto-derived node-scoping filter: ``<node_label>=~"n1|n2|..."``…, A node named `pve1.example.com` must match only that exact string in RE2 -- an…, test_build_node_selector_empty_list_is_none(), test_build_node_selector_escapes_dots_in_an_fqdn() (+1 more)

### Community 112 - "Execute page: order_moves"
Cohesion: 0.36
Nodes (9): Internals: Ordering the moves (schedule.py), cost_m tiny_disk_bytes, ScheduleResult.final_assignment, order_moves, Persistent-objective reduction per cost_m ranking, Residual violation unexecutable, Schedule page, Transient invariant called with single-move set (+1 more)

### Community 113 - "`objective` — the solver's trade-off weights"
Cohesion: 0.22
Nodes (9): `objective.affinity_counts_pinned_disks`, `objective.alpha_spread`, `objective.beta_move_count`, `objective.delta_capacity_spread`, `objective.gamma_move_bytes_per_tib`, `objective.kappa_vm_affinity`, `objective.reserve_violation_penalty`, `objective.spread_metric` (+1 more)

### Community 114 - "MetricsError"
Cohesion: 0.25
Nodes (8): MetricsError, Prometheus could not be queried, or the response was unusable. See…, refuse(), per_group_load(), fail(), raise_metrics_error(), test_verify_metrics_query_failure_is_reported(), raise_error()

### Community 115 - "Overview page: Load model page"
Cohesion: 0.39
Nodes (8): Symbols D S Uext, apply_forecast scaling, compute_disk_load_series, compute_group_load, Coverage rejection, Current-assignment L_s u_s, Idle group T_g zero, Load model page

### Community 116 - "Persistent state: state.json"
Cohesion: 0.25
Nodes (8): Persistent state: state.json, Drift history reaches the gates via last_balance, Reading degrades, writing raises, staged_disks field unimplemented, State dataclass tree mirrors section 11.2 JSON, ``"<group>:<storage>"`` (section 11.2)., storage_state_key(), test_storage_state_key_matches_section_11_2_shape()

### Community 117 - "Overview page: Gates page"
Cohesion: 0.39
Nodes (8): Cooldowns not in gates, Drift gate, evaluate_group_gates, Gates page, last_load state, Reserve override gate, (C6) Load spread, Imbalance gate (default 0.20)

### Community 118 - "00-installation.md: Installation and requirements"
Cohesion: 0.25
Nodes (8): First steps after installing, Installation and requirements, Installing the package, Running the timer on exactly one host, Setting up the PVE credential, What you need, Where the configuration is *not*, Where the configuration lives

### Community 119 - "Configuration reference: `exclude` — what DRS never touches"
Cohesion: 0.25
Nodes (8): `exclude.disks`, `exclude.include_unused_disks`, `exclude.running_only`, `exclude.skip_vms_with_snapshots`, `exclude.storages`, `exclude.tags`, `exclude.vmids`, `exclude` — what DRS never touches

### Community 120 - "30-safety-and-status.md"
Cohesion: 0.25
Nodes (8): forecast (Holt-Winters), verify-metrics exit status and severity levels, Failure to read ends the run with exit 1, forecast: line, Exit codes, Optional dependencies, Safety properties, exit codes, and what this build actually does, What is safe, unconditionally

### Community 121 - "Group: _quantile_promql()"
Cohesion: 0.25
Nodes (8): _coverage_promql(), _group_selector(), _quantile_promql(), _rate_promql(), The one combined selector `compute_group_load()`/`compute_disk_load_series()`…, The exact PromQL `_fetch_raw_quantity` builds for one raw field -- computed…, The exact PromQL `compute_disk_coverage` builds for its range query., The exact PromQL `_fetch_raw_quantity_series` builds for one raw field -- the…

### Community 122 - "Configuration page"
Cohesion: 0.43
Nodes (7): Config path resolution order, Configuration page, ResolvedConfig, Secrets from environment, Semantic validation rules, Two-stage validation, Units parsed once

### Community 123 - "Overview page: Payback page"
Cohesion: 0.52
Nodes (7): compute_move_cost, Mirror duration bwlimit, Payback page, Payback verdict, _plan_group wiring, Reserve-override exemption, Wipe duration magnitude

### Community 124 - "Reading `apply`: 28-apply.md"
Cohesion: 0.29
Nodes (6): Salted pseudonym anonymization, Bundle layout and manifest, collect-testdata command, Submitting a bundle to the corpus, --estimate and support.max_series_points refusal, --replay offline mode

### Community 125 - "_findings_to_json"
Cohesion: 0.29
Nodes (6): _findings_to_json(), ``verify_metrics()``'s own finding text, and this module's own call log (built…, Bundle-safe rewrite of one ``verify_metrics()`` finding message. Returns…, _redact_finding_message(), _redact_free_text(), VerifyMetricsReport

### Community 126 - "ForecastConfig"
Cohesion: 0.48
Nodes (7): ForecastConfig, The history ``forecast.model`` needs, in seconds. Called by ``config.py``'s…, required_range_seconds(), test_holt_winters_required_range_is_the_lookback_when_that_is_longer(), test_holt_winters_required_range_matches_plan_worked_example(), test_quantile_required_range_is_the_lookback(), test_required_range_unknown_model_raises()

### Community 127 - "_forecast_fixture"
Cohesion: 0.43
Nodes (7): apply_forecast(), Section 12.1 point 2: scale each disk's ``l_d`` by its forecast factor ``f_d /…, _forecast_fixture(), test_apply_forecast_leaves_idle_and_no_series_matched_alone(), test_apply_forecast_never_scales_a_flagged_disk_even_if_a_factor_is_given(), test_apply_forecast_scales_only_disks_with_a_factor_and_rebuilds_the_totals(), test_apply_forecast_with_no_factors_is_the_identity()

### Community 128 - "Logging: what lands where, and what an unattended run records"
Cohesion: 0.33
Nodes (6): Logging: what lands where, and what an unattended run records, Text or JSON, The decision trail, Unattended runs log this without being asked, Under systemd, Verbosity

### Community 129 - "C5 Capacity, snapshot reserve and free space"
Cohesion: 0.47
Nodes (6): CBC via PuLP MILP backend, CP-SAT ortools backend removed (AL-02), Heuristic fallback (seed, repair, descend, polish), Shared feasibility and objective functions (evaluate_assignment), Shared feasibility/objective implementation, CBC via PuLP (only MILP backend)

### Community 130 - "forecast_group"
Cohesion: 0.33
Nodes (6): group_aggregate_series(), Sum every disk's own series into one group-aggregate series, at the union of…, 101:scsi0 has no sample at t=1 at all -- that timestamp still appears (from…, test_group_aggregate_series_empty_input_is_empty(), test_group_aggregate_series_missing_disk_at_a_timestamp_contributes_zero(), test_group_aggregate_series_sums_across_disks_per_timestamp()

### Community 131 - "Logging: what lands where, and what an unattended run record"
Cohesion: 0.40
Nodes (5): `collect-testdata`: capturing a bundle, Diagnostic bundles: `collect-testdata` and `--replay`, `--replay`: running against a bundle offline, Sending one to the project, What is in a bundle, and what is not

### Community 133 - "resolve_level"
Cohesion: 0.50
Nodes (5): Section 2.3's ladder: ``--quiet`` < default < ``-v`` < ``-vv``. ``--log-level``…, resolve_level(), parametrize, test_log_level_wins_over_both_verbose_and_quiet(), test_resolve_level_ladder()

### Community 134 - "test_unfixable_shortfall_is_proven_only_for_an_optimal_cbc_solve"
Cohesion: 0.67
Nodes (3): test_unfixable_shortfall_is_proven_only_for_an_optimal_cbc_solve(), outcome(), proven()

### Community 139 - "_is_metrics_expected_absent"
Cohesion: 0.67
Nodes (3): _is_metrics_expected_absent(), parametrize, test_is_metrics_expected_absent()

## Knowledge Gaps
- **218 isolated node(s):** `state.path`, `Migrations throttled by bwlimit only`, `Keyed pseudonyms with salt`, `Storage group`, `max_single_move_duration hard rule` (+213 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1357 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Persistent state: state.json` connect `Persistent state: state.json` to `state.py`, `build_topology`, `execute.py`, `schedule.py: Disk`, `ObjectiveBreakdown`, `Overview page`, `topology.py`, `20-verifying-metrics.md: Manual: Configuration reference`, `ResolvedConfig`, `_handle_apply`, `heuristic.py`, `empty_state`, `loadmodel.py`, `crashrecovery.py`?**
  _High betweenness centrality (0.110) - this node is a cross-community bridge._
- **Why does `Manual: Configuration reference` connect `20-verifying-metrics.md: Manual: Configuration reference` to `Manual: Configuration reference`, `Reading `apply``, `Internals: The heuristic solver`, `Dry-run is the default`, `Persistent state: state.json`, `Configuration reference`, `Internals: CLI dispatch and logging`, `Configuration page`, `30-safety-and-status.md`?**
  _High betweenness centrality (0.100) - this node is a cross-community bridge._
- **Why does `Group` connect `test_optimize.py` to `build_topology`, `MonkeyPatch`, `execute.py`, `ObjectiveBreakdown`, `Topology`, `topology.py`, `test_execute.py`, `run_concurrent`, `ResolvedConfig`, `_patch_plan_deps`, `Storage`, `_plan_group`, `_plan_group: _log_load_digest()`, `GroupLoad`, `Disk`, `loadmodel.py`, `compute_group_load`, `schedule.py: Disk`, `evaluate_assignment`, `ExecutionConfig`, `main`, `Path`, `test_free_space_repair_fixture.py`, `evaluate_assignment: test_heuristic.py`, `collect.py`, `order_moves`, `heuristic.py`, `capture_bundle`, `ForecastReport`, `test_small_disks.py`, `cli.py`, `MoveCost`, `test_plan_gate_also_reflects_real_drift_history_from_state_json`, `test_affinity_repair_fixture.py`, `Group`, `Group: _quantile_promql()`, `_forecast_fixture`?**
  _High betweenness centrality (0.098) - this node is a cross-community bridge._
- **Are the 191 inferred relationships involving `Group` (e.g. with `_accumulate_move_stats()` and `_apply_payback_gate()`) actually correct?**
  _`Group` has 191 INFERRED edges - model-reasoned connections that need verification._
- **Are the 92 inferred relationships involving `PveClient` (e.g. with `_apply_payback_gate()` and `_pve_client_for()`) actually correct?**
  _`PveClient` has 92 INFERRED edges - model-reasoned connections that need verification._
- **What connects `state.path`, `Migrations throttled by bwlimit only`, `Keyed pseudonyms with salt` to the rest of the system?**
  _218 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `build_topology` be split into smaller, more focused modules?**
  _Cohesion score 0.06192972238400311 - nodes in this community are weakly interconnected._