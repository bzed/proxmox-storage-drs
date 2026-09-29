# Graph Report - proxmox-storage-drs  (2026-09-29)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 3893 nodes · 10680 edges · 156 communities (134 shown, 22 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 1412 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5533cef2`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- MonkeyPatch
- test_topology.py
- execute.py
- generate_expected.py
- test_config.py
- Path
- metrics.py
- test_cli.py
- test_loadmodel.py
- test_metrics.py
- schedule.py
- run
- Group
- topology.py
- Configuration reference
- test_gates.py
- Disk
- test_payback.py
- _balanced_apply_topology
- pve.py
- test_optimize.py
- test_statusfile.py
- test_validate_corpus.py
- test_replay.py
- run_concurrent
- test_state.py
- PveClient
- test_anonymize.py
- Manual: Reading plan
- make_config
- test_collect.py
- test_free_space_repair_fixture.py
- test_execute.py
- TimeWindow
- AGENTS.md working agreement
- cli.py
- collect.py
- ResolvedConfig
- ExecutionConfig
- main
- drs.example.yaml (reference configuration)
- test_logging_setup.py
- heuristic.py
- order_moves
- Manual: Configuration reference
- anonymize.py
- MILP optimization problem
- format_disk_id
- Overview page
- _render_group_plan_human
- test_documentation.py
- BundleError
- test_small_disks.py
- Transient invariant
- Mapper
- Proxmox Storage DRS Implementation Plan
- series_of
- build_client
- Execute page
- Proxmox VE API
- config.py
- _plan_group
- Config
- crashrecovery.py
- state.py
- test_affinity_repair_fixture.py
- test_crashrecovery.py
- move_disk (drive-mirror, delete=1)
- Reading `apply`
- Any
- Where the numbers come from, and how a transport loses them
- capture_bundle
- State
- Any
- Persistent state: state.json
- C5 Capacity, snapshot reserve and free space
- Mapper
- ReplayPveClient
- _handle_apply
- pathlib
- JsonFormatter
- .agents/documentation.md
- resolve_node_selector
- `execution` — how (and whether) moves actually happen
- pve-storage-drs.1.md
- test_forecast.py
- LastBalance
- PrometheusClient
- Internals: CLI dispatch and logging
- Internals: Building the disk/storage/group model
- _check_sample_series
- Packaging, dependencies and CI (.agents)
- forecast_group
- Engine pipeline: collect, join, gate, solve, cost, order, execute
- forecast.py
- PveApiError
- disk_factors
- exceptions.py
- FakeProxmoxResource
- pytest
- ._get
- test_running_task_on_the_vm_is_waited_out_before_move_disk
- Transient reserve invariant (operator explanation)
- Load model (average in-flight I/O)
- ForecastReport
- _FakeSession
- `proxmox` — the cluster API connection
- _issue_chunked_range_query
- _outcome
- test_node_pseudonym_collision_is_refused
- _mapper
- _client_with_fake_time
- Installation and requirements
- Safety properties, exit codes, and what this build actually does
- _ResponseLike
- safe_range_step_seconds
- test_apply_refuses_the_whole_plan_when_the_aggregate_payback_test_fails
- _findings_to_json
- Configuration page
- State dataclass tree mirrors section 11.2 JSON
- parse_disk_spec
- _forecast_fixture
- Monitoring status file
- What `plan` does not yet do
- Logging: what lands where, and what an unattended run records
- Heuristic fallback (seed, repair, descend, polish)
- _pid_alive
- test_api_outage_beyond_the_tolerance_still_raises
- Diagnostic bundles: `collect-testdata` and `--replay`
- filters.lua
- ForecastReport
- _quantile
- resolve_level
- _FakeClient
- _all_pinned_sample_topology
- _Raise
- import-all
- draining status
- run-with-system-python.sh
- build_paper.sh
- Never consider over-provisioning (provisioned size)
- Check 3: configured labels present
- Check 6: observed sample spacing
- Lock timeout skip vs abort
- Shared pandoc PDF metadata
- Plan output and explain narration
- importlib
- proxmox-storage-drs
- proxmox_storage_drs
- Assignment
- CaptureFixture
- BaseException
- needs_full_checkout

## God Nodes (most connected - your core abstractions)
1. `Group` - 206 edges
2. `PveClient` - 125 edges
3. `Disk` - 85 edges
4. `write_config()` - 80 edges
5. `Proxmox Storage DRS Implementation Plan` - 78 edges
6. `run()` - 77 edges
7. `client_with()` - 76 edges
8. `make_move()` - 75 edges
9. `build_topology()` - 71 edges
10. `PrometheusClient` - 58 edges

## Surprising Connections (you probably didn't know these)
- `The `Group <name> → ACT`/`NO ACTION` line` --references--> `GroupLoad`  [INFERRED]
  docs/manual/25-show-load-and-verify-storages.md → src/proxmox_storage_drs/loadmodel.py
- `What is in the file` --references--> `duration()`  [INFERRED]
  docs/manual/36-monitoring.md → tests/fixtures/generate_expected.py
- `What `plan` does not yet do` --references--> `GroupLoad`  [INFERRED]
  docs/manual/27-plan.md → src/proxmox_storage_drs/loadmodel.py
- `Single reauthenticate-and-retry in _call` --references--> `PveClient`  [EXTRACTED]
  docs/internals/50-pve-api.md → src/proxmox_storage_drs/pve.py
- `The `objective:` line` --references--> `ObjectiveBreakdown`  [INFERRED]
  docs/manual/29-explain.md → src/proxmox_storage_drs/heuristic.py

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
- **Domain safety invariants that must not be optimised away** — agents_domain_invariants_dry_run_default, agents_domain_invariants_snapshot_reserve, agents_three_floors_precedence, implementation_plan_transient_invariant, agents_finished_task_not_finished_move, agents_domain_invariants_never_auto_delete, agents_never_overprovision [EXTRACTED 1.00]
- **Gating decides whether to act** — implementation_plan_drift_gate, implementation_plan_imbalance_gate, implementation_plan_capacity_gate, implementation_plan_cooldowns [EXTRACTED 1.00]
- **Diagnostic bundle capture, anonymization and replay** — implementation_plan_diagnostic_bundles, implementation_plan_anonymization_allowlist, implementation_plan_keyed_pseudonyms, implementation_plan_replay, implementation_plan_test_corpus [EXTRACTED 1.00]
- **Engine stages collect-gate-solve-cost-order-execute** — implementation_plan_load_model, implementation_plan_gating, implementation_plan_milp_model, implementation_plan_payback_rule, implementation_plan_scheduling, implementation_plan_execution_modes [EXTRACTED 1.00]
- **Reserve and free-space floors (f_s*Z_s, hard_s, soft_s)** — implementation_plan_snapshot_reserve, implementation_plan_free_space_config, implementation_plan_c5_reserve, implementation_plan_transient_invariant, implementation_plan_free_space_repair_mandate [EXTRACTED 1.00]
- **DRS engine pipeline stages** — src_proxmox_storage_drs_metrics, src_proxmox_storage_drs_pve, src_proxmox_storage_drs_topology, src_proxmox_storage_drs_loadmodel, src_proxmox_storage_drs_optimize, src_proxmox_storage_drs_payback, src_proxmox_storage_drs_schedule, src_proxmox_storage_drs_execute [EXTRACTED 1.00]
- **CI and quality gates enforcing the make check loop** — github_workflows_tests_tests_workflow, github_workflows_debian_package_debian_package_workflow, debian_gitlab_ci_salsa_ci_pipeline, pre_commit_config_pre_commit_hooks, codecov_yml_codecov_config [INFERRED 0.85]
- **Generated artefacts kept honest by stamps and tests** — _agents_paper_sha256_stamp, _agents_documentation_doc_tests [INFERRED 0.85]
- **Move completion: task OK, source released, VM unlocked** — docs_manual_28_apply_move_done_definition, docs_manual_28_apply_draining [INFERRED 0.85]
- **Operator onboarding flow: install, credential, verify metrics, plan, apply, monitor** — readme_debian_package_release, docs_manual_00_installation_pve_credential, readme_verify_metrics, readme_plan_explain, readme_apply_execution_modes, implementation_plan_monitoring_status_file [INFERRED 0.85]
- **plan report output pipeline** — docs_manual_27_plan_solver_line, docs_manual_27_plan_payback_line, docs_internals_40_cli_and_logging_no_moves_made, docs_internals_40_cli_and_logging_unfixable_shortfall_report, docs_manual_27_plan_json_output [INFERRED 0.85]
- **Debian packaging, CI and release chain** — implementation_plan_debian_first, agents_autopkgtest, agents_ci_pipelines, agents_release_procedure, readme_debian_package_release [INFERRED 0.85]
- **Reserve/free space is never traded for balance** — docs_manual_27_plan_repair_exempt, docs_internals_95_schedule_deadlock_report, docs_internals_40_cli_and_logging_unfixable_shortfall_report, docs_manual_10_configuration_free_space, docs_manual_10_configuration_snapshot_reserve_factor [INFERRED 0.85]
- **Reserve and free-space safety invariants** — implementation_plan_c5_reserve, implementation_plan_snapshot_reserve, implementation_plan_free_space_config, implementation_plan_transient_invariant, implementation_plan_lexicographic_solve [INFERRED 0.85]
- **Heuristic and MILP share feasibility/objective functions** — docs_internals_90_heuristic_evaluate_assignment, docs_internals_60_topology_reserve_evaluator, docs_internals_91_optimize_shared_constraints_c1_c5, docs_internals_91_optimize_lexicographic_solve [INFERRED 0.85]
- **Storage cooldown enforcement across backends** — docs_manual_10_configuration_gates, docs_internals_90_heuristic_storage_cooldown_destination, docs_internals_91_optimize_storage_cooldown_both_stages [INFERRED 0.85]
- **Tiny-disk (EFI/TPM) free reunion with VM** — docs_manual_10_configuration_migration_tiny_disk_bytes, docs_internals_95_schedule_tiny_disk_first, docs_manual_27_plan_payback_line [INFERRED 0.85]

## Communities (156 total, 22 thin omitted)

### Community 0 - "MonkeyPatch"
Cohesion: 0.06
Nodes (101): CaptureFixture, _fake_build_topology(), _imbalanced_group_load(), _no_reserve_violation_topology(), _patch_plan_deps(), _patch_show_load_deps(), _patch_show_load_forecast(), Exception (+93 more)

### Community 1 - "test_topology.py"
Cohesion: 0.06
Nodes (100): Disk-cooldown pin is not exempted for reserve repair, vm_config returns pending value; vm_pending exposes both, The cluster topology could not be built from the API responses. See…, TopologyError, build_topology(), pending_disk_reasons(), _pin_reason(), datetime (+92 more)

### Community 2 - "execute.py"
Cohesion: 0.05
Nodes (95): ExcludeConfig, _active_task_on_vm(), _advance_pending(), _auto_budget_stop_outcome(), _check_lock_once(), Clock, _confirm_decision(), _deadline_exceeded() (+87 more)

### Community 3 - "generate_expected.py"
Cohesion: 0.05
Nodes (85): Pin priority: _pin_reason(), best_single_disk_alternative(), cannot fully consolidate, -v data source: line, `measured load:`, `no moves made: ...` / `closest alternative: ...`, `pinned load ... ; best achievable spread given pins: ...`, `pinned (not movable this run):` (+77 more)

### Community 4 - "test_config.py"
Cohesion: 0.07
Nodes (87): ConfigError, The configuration file is missing, unreadable or fails validation. See…, format_bytes(), format_duration_seconds(), parse_duration_seconds(), parse_size_bytes(), Render a duration in seconds as a human-readable string, e.g. ``"2.2h"``., Unit parsing and formatting for durations and byte sizes. ``config.py`` is the… (+79 more)

### Community 5 - "Path"
Cohesion: 0.07
Nodes (76): ExecutionResult, One group's ``execute_plan()`` call. ``stopped_early`` is true for any reason…, The whole cluster's worth of groups, as seen by this run. By the time anything…, Topology, _fake_breakdown(), _fragmented_group(), _make_group_plan(), _moved_outcome() (+68 more)

### Community 6 - "metrics.py"
Cohesion: 0.05
Nodes (81): _RawTimeSeries, MetricLabels, MetricsConfig, _combine_raw_values(), _combined_raw(), _fetch_all_raw_quantities(), _fetch_all_raw_quantity_series(), _fetch_raw_quantity() (+73 more)

### Community 7 - "test_cli.py"
Cohesion: 0.03
Nodes (62): load_config(), Resolve, read, parse and validate the configuration. See section 11 for…, _fake_reconcile_inflight(), _NodeNamesClient, LogCaptureFixture, Every `apply` test here uses `build_pve_client`'s "fake-client" string stand-…, REVIEW.md R-06: `move.size_bytes == 0` must not raise `ZeroDivisionError` --…, REVIEW.md R-05: an economic failure (benefit < ratio*cost) and a hard per-move… (+54 more)

### Community 8 - "test_loadmodel.py"
Cohesion: 0.08
Nodes (78): LoadWeights, _blend_loads(), compute_disk_load_series(), compute_group_load(), _is_metrics_expected_absent(), TimeSeries, Section 4's normalize-then-weight-then-rescale blend, given every key's own…, Compute one group's :class:`GroupLoad` for this run. Section 4.… (+70 more)

### Community 9 - "test_metrics.py"
Cohesion: 0.06
Nodes (72): WindowConfig, MetricsError, Prometheus could not be queried, or the response was unusable. See…, _check_coverage(), _check_observed_spacing(), PrometheusClient, Run every section 3.3 check and assemble the report. Must be run before relying…, Thin wrapper over the Prometheus HTTP API. See section 3.4/3.5. ``session`` is… (+64 more)

### Community 10 - "schedule.py"
Cohesion: 0.05
Nodes (66): dataclasses, _capacity_spread(), Section 6: decide whether to act on a group at all, before the solver runs.…, Section 5.3 (C7)'s `(max_s b_s - min_s b_s) / b_bar`, or ``None`` when the gate…, Migration cost and the payback acceptance test. See IMPLEMENTATION_PLAN.md…, compute_reserve_status(), _current_storage(), largest_disk_bytes() (+58 more)

### Community 11 - "run"
Cohesion: 0.09
Nodes (66): LocksConfig, client_with(), default_group(), FakeClock, make_move(), Section 9.1: the pre-loop time-window check (above) only knows the answer as of…, A move missing from `move_costs_by_key` is never refused for lack of an…, Section 13: `state.json` must learn about a UPID *before* this function goes on… (+58 more)

### Community 12 - "Group"
Cohesion: 0.09
Nodes (65): best_single_disk_alternative(), compute_vm_weights(), evaluate_assignment(), Section 5.5 step 1: "seed with the current assignment (not from scratch -- we…, Section 5.4's `w_v = max(1, l_v / l_bar)` -- the per-VM weight that scales…, Section 5.4's objective for one candidate ``assignment``.…, The single-disk move closest to being worth taking, among every (movable disk,…, Section 5.5's four-step heuristic (minus "polish"; see the module docstring),… (+57 more)

### Community 13 - "topology.py"
Cohesion: 0.06
Nodes (65): concurrent_futures, re, GroupConfig, is_storage_pattern(), A ``storages[].id`` value is a pattern iff it both begins and ends with ``/``…, The regular expression text of a pattern entry, its two ``/`` delimiters…, storage_pattern_text(), StorageConfig (+57 more)

### Community 14 - "Configuration reference"
Cohesion: 0.03
Nodes (63): Configuration reference, `exclude.disks`, `exclude.include_unused_disks`, `exclude.running_only`, `exclude.skip_vms_with_snapshots`, `exclude.storages`, `exclude.tags`, `exclude.vmids` (+55 more)

### Community 15 - "test_gates.py"
Cohesion: 0.08
Nodes (58): GatesConfig, evaluate_group_gates(), GateDecision, _l1_drift(), Section 6, applied in the order it lists: reserve override, then the capacity…, One group's act/no-act verdict, section 6, with the reasoning shown (phase 3's…, ``(‖ℓ_last‖₁, ‖ℓ_now − ℓ_last‖₁)`` over the **union** of disk keys present in…, _aggregate_storages() (+50 more)

### Community 16 - "Disk"
Cohesion: 0.07
Nodes (56): ObjectiveConfig, group_average_fill(), group_average_utilization(), `u* = (Sum_d l_d) / (Sum_s c_s)` (C6) -- a constant under any reassignment of…, `b_bar = (Sum_d z_d + Sum_s U^ext) / (Sum_s C_s)` (section 5.3 (C7)) -- a…, _cbc_capacity_spread_term(), _cbc_feasibility_constraints(), _cbc_objective_terms() (+48 more)

### Community 17 - "test_payback.py"
Cohesion: 0.09
Nodes (54): MigrationConfig, compute_benefit_load_seconds(), compute_move_cost(), compute_wipe_duration_seconds(), evaluate_plan_payback(), MoveCost, ``duration_wipe_d`` (section 7.1) for one disk on one storage, or ``None`` if…, Section 7.1's cost for one scheduled move. Only ``source`` is needed (not the… (+46 more)

### Community 18 - "_balanced_apply_topology"
Cohesion: 0.06
Nodes (54): _balanced_apply_group_load(), _balanced_apply_topology(), _check_statusfile(), _monitored_config(), Two evenly-sized, evenly-loaded disks on one storage, none on the other, no…, Matches `_balanced_apply_topology()`: both disks on san-a, load 5.0 each (200%…, `execute.execute_plan()` itself now dispatches to a concurrent executor once…, Dry-run's own `execute_plan()` path issues zero API calls (see… (+46 more)

### Community 19 - "pve.py"
Cohesion: 0.05
Nodes (37): contextlib, proxmoxer, RequestException, requests, ResourceException, ProxmoxConfig, _apply_connection_pool_size(), _apply_ticket_refresh_seconds() (+29 more)

### Community 20 - "test_optimize.py"
Cohesion: 0.09
Nodes (54): cbc_available(), make_disk(), make_storage(), LogCaptureFixture, MonkeyPatch, parametrize, Deliberately *not* parametrized over the skip-guarded `BACKENDS` list above --…, Section 5.4's D^big: at beta_move_count=1.0, moving `201:efidisk0` (1 MiB) to… (+46 more)

### Community 21 - "test_statusfile.py"
Cohesion: 0.10
Nodes (47): CompletedProcess, datetime, needs_plugin, os, build_run_status(), _one_line(), Collapse any run of whitespace, newlines included, to one space: a newline…, The level policy (section 2.4). ``CRITICAL`` when the run exited non-zero: a… (+39 more)

### Community 22 - "test_validate_corpus.py"
Cohesion: 0.09
Nodes (47): needs_full_checkout, tests_corpus, tests_corpus_validate_corpus, _case(), _invariant_inputs(), MonkeyPatch, parametrize, Path (+39 more)

### Community 23 - "test_replay.py"
Cohesion: 0.11
Nodes (44): PrometheusConfig, _captured_step(), _config_from_bundle(), _free_space_pairs(), MonkeyPatch, Path, AH-06: a live ``free_space`` config is collected as the resolved per-storage…, Section 16.5's one deliberate exception: a bundle captured before section 3.8… (+36 more)

### Community 24 - "run_concurrent"
Cohesion: 0.09
Nodes (39): FakeProxmoxResource, concurrent_client_with(), datetime, MoveCost, ScheduledMove, The defining property of concurrency: `move_disk` for the second move is issued…, Each move's own UPID reaches both callbacks correctly attributed --…, Two otherwise-independent moves landing on the *same* target: even with… (+31 more)

### Community 25 - "test_state.py"
Cohesion: 0.12
Nodes (44): ``state.path`` could not be written, or its advisory lock could not be…, StateError, acquire_lock(), empty_state(), load_state(), LockInfo, First-run state: no lock, no recorded balance, no cooldowns, nothing in flight…, Best-effort read of ``path``. See the module docstring: a missing file is the… (+36 more)

### Community 26 - "PveClient"
Cohesion: 0.07
Nodes (40): PveClient, One method per IMPLEMENTATION_PLAN.md section 3.5 endpoint. ``api`` is typed…, Retry idempotent calls that fail because the API is unreachable for up to…, _FakeHttpsBackend, _FakeProxmoxApiWithBackend, _FakeTicketAuth, Section 9.2: "convert at the call site and nowhere else" -- this is that site., A ticket that expired for reasons external to this call (a long confirm-mode… (+32 more)

### Community 27 - "test_anonymize.py"
Cohesion: 0.07
Nodes (35): make_mapper(), parametrize, Path, A node and a storage that happen to share a name must not collide., Section 16.3: 'the result never depends on iteration order'., anonymize.py: allowlists, pseudonyms, timestamp rebasing. See…, PVE's own `get_next_vm_diskname()` appends a literal `.<format>` to the volume…, anonymize.py's own UPID split must accept exactly what… (+27 more)

### Community 28 - "Manual: Reading plan"
Cohesion: 0.06
Nodes (40): reserve.py: shared (C4)/(C5) evaluator, Internals: The heuristic solver, Descend explores swaps, evaluate_assignment(): objective separate from search, objective.spread_metric: two different quantities, Storage cooldown excludes destination, never source, Repair is unconditional, not weight-driven, w_v: kappa weighted by VM I/O, and D^big (+32 more)

### Community 29 - "make_config"
Cohesion: 0.09
Nodes (42): pseudonym(), _instant_answer(), make_config(), make_prometheus_client(), make_pve_client(), Any, PrometheusClient, _range_answer() (+34 more)

### Community 30 - "test_collect.py"
Cohesion: 0.09
Nodes (38): capture(), Path, X-08: section 16.1's manifest line ("schema, versions, what was captured...")…, X-08: section 16.3 promises the manifest "flags" a non-node-shaped…, Z-03: `resolve_node_selector()`'s tier-1 precedence used to win on *both* sides…, A live capture against the dev cluster found the previous implementation's bug…, verify_metrics() never carries a node selector at all -- nothing to rewrite,…, Even when the configured model is ``quantile``, the bundle is captured with… (+30 more)

### Community 31 - "test_free_space_repair_fixture.py"
Cohesion: 0.09
Nodes (34): executed_assignment(), Assignment, Section 7.3: "what it will really run" -- ``final_assignment``…, Section 7.3's revert test, one verdict per scheduled move in ``order``: would…, repair_markers(), `Σ_s r_s` at the assignment ``storage_of`` encodes -- section 7.3's outcome…, total_shortfall_bytes(), _free_space_repair_group() (+26 more)

### Community 32 - "test_execute.py"
Cohesion: 0.08
Nodes (35): parametrize, A PVE API error while re-reading the target refuses the move and fails the run…, A `san-c` content responder plus a `move_disk` responder for 201. The listing…, 201's mirror target is already *listed* on san-c at its full 1 TiB by the time…, Between different storage types, or from thin to thick, `move_disk` allocates…, The match stays narrow: a same-VM volume that appeared after launch but has…, The exclusion is narrow: only 201's *own* mirror target (same VM, the disk's…, Executing a plan. See proxmox_storage_drs/execute.py. No test here talks to a… (+27 more)

### Community 33 - "TimeWindow"
Cohesion: 0.15
Nodes (34): date, TimeWindow, current_deadline(), _day_name(), is_window_active(), _parse_hhmm(), datetime, ``execution.time_windows``: when ``auto`` mode may execute moves. See… (+26 more)

### Community 34 - "AGENTS.md working agreement"
Cohesion: 0.08
Nodes (35): fc-tier1 / reserve-tradeoff acceptance fixtures, AGENTS.md working agreement, AGPL-3.0-or-later licence and SPDX headers, autopkgtest runtime-dependency check, black/flake8 E203 W503 E704 ignores, Branch-first git workflow, GitHub Actions and Salsa GitLab CI pipelines, 85% coverage floor (+27 more)

### Community 35 - "cli.py"
Cohesion: 0.10
Nodes (32): Assignment, shutil, _fallback_manual_text(), _fragmented_vms(), _load_per_tib(), _objective_breakdown_json(), _pin_action_hint(), _pinned_disks() (+24 more)

### Community 36 - "collect.py"
Cohesion: 0.08
Nodes (30): functools, gzip, _anonymize_captured_prometheus(), _anonymize_prometheus_series(), _anonymize_query_text(), Bundle, CallRecord, capture_range_seconds() (+22 more)

### Community 37 - "ResolvedConfig"
Cohesion: 0.14
Nodes (32): Namespace, _dump_report_json(), _filter_groups(), _handle_collect_testdata(), _handle_explain(), _handle_plan(), _handle_show_load(), _handle_verify_metrics() (+24 more)

### Community 38 - "ExecutionConfig"
Cohesion: 0.14
Nodes (30): ExecutionConfig, SourceReleaseConfig, _group_with_types(), make_disk(), make_storage(), Section 9.3: a source_release timeout "does not fail the run: mark the storage…, Same as above, except the second move's *target* -- not source -- is the…, Section 9.3 point 3: PVE's own `saferemove_throughput` (already read live off… (+22 more)

### Community 39 - "main"
Cohesion: 0.08
Nodes (31): ArgumentParser, CommandHandler, _accumulate_move_stats(), apply_mode_override(), build_parser(), _log_run_summary(), main(), _make_not_yet_implemented_handler() (+23 more)

### Community 40 - "drs.example.yaml (reference configuration)"
Cohesion: 0.07
Nodes (31): drs.example.yaml (reference configuration), exclude rules, load_weights, `metrics.extra_selector`, `metrics.labels.device`, `metrics.labels.node`, `metrics.pvestatd_push_interval`, `metrics.rate_window` (+23 more)

### Community 41 - "test_logging_setup.py"
Cohesion: 0.13
Nodes (29): ast, io, configure_logging(), floor_for_command(), The mandatory ``INFO`` floor of section 2.3, or ``None``. A run that can change…, Install this run's log handler. Called once, from ``main()``. ``floor`` is…, CaptureFixture, INFO at a terminal is the narrative the operator asked for; prefixing every… (+21 more)

### Community 42 - "heuristic.py"
Cohesion: 0.11
Nodes (26): _RepairCandidate, _best_of(), _best_repair_candidate(), trial_storage_of(), _descend(), storage_of(), HeuristicResult, _movable_disks() (+18 more)

### Community 43 - "order_moves"
Cohesion: 0.14
Nodes (29): order_moves(), Section 8.2's scheduling loop for one group. ``target_assignment`` is normally…, make_disk(), make_storage(), _one_move_that_would_leave_san_b_slightly_short(), The plan's own arithmetic: move 1 -> 5.0 <= 8.0, move 2 -> 4.5 <= 8.0, move 3…, A storage with no existing disks and a tiny arriving one must still reserve…, Two disks, both storages already full: the target assignment swaps them, which… (+21 more)

### Community 44 - "Manual: Configuration reference"
Cohesion: 0.12
Nodes (22): .agents/ index, Python style (.agents), black vs flake8 disagreements (E203, W503, E704), One implementation of every rule (MILP and heuristic share), Units in names, Manual: Configuration reference, `snapshot_reserve.count_foreign_volumes`, snapshot_reserve.factor (+14 more)

### Community 45 - "anonymize.py"
Cohesion: 0.09
Nodes (26): hashlib, hmac, MappingType, filter_allowed_fields(), filter_disk_value_params(), filter_vm_config_fields(), filter_vm_pending_entries(), generate_new_salt() (+18 more)

### Community 46 - "MILP optimization problem"
Cohesion: 0.12
Nodes (29): Affinity repair under payback fixture, beta term: number of migrations, bwlimit is the only throttle (saturation guard removed), C1 Assignment, (C3) VM affinity linking, (C6) Load spread, C7 Capacity-spread linearization, (C8) Small disks follow their VM (+21 more)

### Community 47 - "format_disk_id"
Cohesion: 0.08
Nodes (26): ReserveStatus, _make_confirm_move_interactively(), confirm(), MoveCost, ScheduledMove, The economic test (``aggregate_ok``) and the hard per-move duration rule…, Section 5.3's "report any residual `r_s > 0` prominently as an unfixable…, The human form of :class:`_UnfixableShortfall` -- printed whether or not the… (+18 more)

### Community 48 - "Overview page"
Cohesion: 0.14
Nodes (27): config.py depends on forecast.py, Module layout, Overview page, Seven-stage pipeline, Symbols D S Uext, Two solver backends, Backtest gate, Drift baseline is effective load (+19 more)

### Community 49 - "_render_group_plan_human"
Cohesion: 0.19
Nodes (27): GateDecision, PaybackResult, _log_plan_selected(), GroupLoad, ObjectiveBreakdown, ScheduleResult, ``(max_s u_s - min_s u_s) / u*`` -- gates.py's own imbalance formula (section…, The residual shortfall of ``final_breakdown`` (the assignment the plan actually… (+19 more)

### Community 50 - "test_documentation.py"
Cohesion: 0.14
Nodes (26): importlib_resources, _flatten_schema_keys(), _load_schema(), _manpage_source_text(), _manual_documented_keys(), Any, needs_full_checkout, parametrize (+18 more)

### Community 51 - "BundleError"
Cohesion: 0.13
Nodes (20): hash_label_name(), hash_query_text(), The cache key both this module (writing) and ``replay.py`` (reading) derive a…, BundleError, RangeStepMismatch, ``--replay`` found the requested range query, but at a different step than this…, A diagnostic bundle (IMPLEMENTATION_PLAN.md section 16) could not be written or…, bundle_reference_now() (+12 more)

### Community 52 - "test_small_disks.py"
Cohesion: 0.14
Nodes (26): _follows(), Section 5.3 (C8): a small disk ends a plan either where it is now, or on a…, (C8) for every small disk of ``group`` at the assignment ``storage_of`` encodes…, small_disk_placement_ok(), small_disks_follow_their_vm(), current(), disk(), efi_repair_group() (+18 more)

### Community 53 - "Transient invariant"
Cohesion: 0.10
Nodes (26): Domain invariants (.agents), Enumerate every disk bus, Finished task is not a finished move, Never auto-delete a volume, Provisioned size, never allocated, Disks with snapshots pinned, Snapshot reserve never traded for balance, VM locks are an open set (+18 more)

### Community 54 - "Mapper"
Cohesion: 0.11
Nodes (15): `metrics.labels.vmid`, `proxmox.auth.token_id`, _check_no_pseudonym_collision(), Mapper, pseudonym(), ``HMAC-SHA256(salt, kind || "\\0" || value)``, truncated to 8 hex chars.…, 32-bit (8 hex char) truncation makes a same-``kind`` collision astronomically…, The single per-bundle offset :meth:`Mapper.rebase_timestamp` applies: the… (+7 more)

### Community 55 - "Proxmox Storage DRS Implementation Plan"
Cohesion: 0.11
Nodes (26): Anonymization allowlist, never denylist, Migrations throttled by bwlimit only, Configuration and validation rules, Dependencies come from Debian (trixie), Diagnostic bundles (collect-testdata), Proxmox Storage DRS Implementation Plan, Execution modes (dry-run default, confirm, auto), Companion fixture free-space repair mandate (+18 more)

### Community 56 - "series_of"
Cohesion: 0.10
Nodes (15): holt_winters_quantile(), ``window.quantile`` of the Holt-Winters forecast path over the next…, Any, A diurnal series that *ends at its trough*: the last forecast point (one day…, series_of(), test_backtest_is_none_without_a_fit_half(), test_backtest_is_none_without_an_actual_half(), test_holt_winters_quantile_clamps_at_zero() (+7 more)

### Community 57 - "build_client"
Cohesion: 0.12
Nodes (23): The Proxmox VE API client, API token permission is intersection with owner, Best-effort ticket refresh tightening, build_client assembles auth once, bwlimit bytes/s to KiB/s conversion only in move_disk, Single reauthenticate-and-retry in _call, storage_content silently empty without Datastore.Allocate, storage_definitions uses the list form GET /storage (+15 more)

### Community 58 - "Execute page"
Cohesion: 0.14
Nodes (25): Auto mode time window, Concurrent execution, Execute page, execute_plan live revalidation, Four-condition done, Injectable Clock, Live transient check provisioned, Orphans reported never deleted (+17 more)

### Community 59 - "Proxmox VE API"
Cohesion: 0.09
Nodes (25): Allowlist-never-denylist anonymization, Per-disk blockstat via pvestatd/InfluxDB/Telegraf/Prometheus, Diagnostic bundle directory format, collect-testdata diagnostic bundle, tests/corpus and scrub audit, Datastore.Allocate needed for storage content listing, Disk identity join (vmid, device), gigapipe on ClickHouse backend (+17 more)

### Community 60 - "config.py"
Cohesion: 0.13
Nodes (24): jsonschema, ruamel_yaml, ruamel_yaml_error, _build_config(), FreeSpaceConfig, FreeSpaceValue, _load_schema(), MonitoringConfig (+16 more)

### Community 61 - "_plan_group"
Cohesion: 0.11
Nodes (24): _apply_payback_gate(), _compute_group_load(), _GroupPlan, _log_gate_decision(), _log_load_digest(), _log_payback_verdict(), _plan_group(), ConfirmCallback (+16 more)

### Community 62 - "Config"
Cohesion: 0.13
Nodes (24): _check_connection_config(), _check_forecast_window(), _check_group_size(), _check_group_storage_membership(), _check_metrics(), _check_objective_weights(), _check_payback_horizon(), _check_schema_version() (+16 more)

### Community 63 - "crashrecovery.py"
Cohesion: 0.15
Nodes (22): cluster/tasks vs task_status conventions differ, parse_upid PVE UPID grammar confirmed live, reconcile_inflight: recorded UPIDs plus foreign scan, AuthConfig, expected_task_user(), parse_upid(), The local half of the startup scan: re-checks every UPID ``state.json`` already…, The cluster-wide half: a still-running ``qmmove`` task from this tool's own… (+14 more)

### Community 64 - "state.py"
Cohesion: 0.14
Nodes (21): Cooldown data stored here, interpreted by topology and heuristic, errno, fcntl, socket, _active_cooldowns(), active_disk_cooldowns(), active_storage_cooldowns(), cooldown_remaining_seconds() (+13 more)

### Community 65 - "test_affinity_repair_fixture.py"
Cohesion: 0.14
Nodes (20): What this build actually implements, ObjectiveBreakdown, Section 7.2's unweighted ``F`` -- ``sum(d_s)``, always L1 regardless of…, Section 7.2's unweighted ``E`` -- ``sum(e_s)`` (``"l1"``) or ``max(u_s)``…, Section 7.2's unweighted (by ``kappa``, but ``w_v``-weighted) ``A`` -- ``Sum_v…, The section 5.4 objective, evaluated for one candidate assignment, broken into…, raw_affinity_debt(), raw_capacity_spread() (+12 more)

### Community 66 - "test_crashrecovery.py"
Cohesion: 0.20
Nodes (20): Section 13's startup scan. Returns the vmids to exclude from this run's…, reconcile_inflight(), fake_api(), BaseException, Shared test doubles. Not collected by pytest (no ``test_`` prefix).…, The same in-flight move already recorded in state.json also shows up in the…, Startup crash/two-instance recovery. See proxmox_storage_drs/crashrecovery.py., test_reconcile_assumes_still_running_when_the_check_itself_fails() (+12 more)

### Community 67 - "move_disk (drive-mirror, delete=1)"
Cohesion: 0.13
Nodes (21): pve-storage-drs executable name, approximate-size fallback for qcow2-on-LVM volumes, Mandatory INFO audit floor for confirm/auto runs, (C2) Eligibility via variable fixing, Errors are not mismatches, Structured log event catalogue, Execution modes dry-run, confirm, auto, Logging policy (two audiences, levels, audit floor) (+13 more)

### Community 68 - "Reading `apply`"
Cohesion: 0.10
Nodes (19): Salted pseudonym anonymization, Bundle layout and manifest, collect-testdata command, Submitting a bundle to the corpus, --estimate and support.max_series_points refusal, --replay offline mode, Concurrent execution, Crash and two-instance recovery (+11 more)

### Community 69 - "Any"
Cohesion: 0.21
Nodes (8): _anonymize_vm_snapshots(), _capture_pve_vm_files(), _guarded(), Any, Run ``fn()``, recording its outcome in ``log``. Returns ``None`` (and records…, Wraps a real, already-authenticated :class:`PveClient` and records every call's…, ``RecordingPveClient``'s own methods already guard and record each call (never…, RecordingPveClient

### Community 70 - "Where the numbers come from, and how a transport loses them"
Cohesion: 0.10
Nodes (20): A reference implementation that is well tested, gigapipe with ClickHouse (reference backend), PVE InfluxDB external metric server, instance label collision, OpenTelemetry metric server rejected, Other backends, RRD rejected as data source, Six per-disk blockstat counters (+12 more)

### Community 71 - "capture_bundle"
Cohesion: 0.21
Nodes (16): _build_manifest(), capture_bundle(), _capture_prometheus_files(), CaptureLog, CaptureOptions, _drive_group_series(), _drive_label_values(), _issue_range_chunks() (+8 more)

### Community 72 - "State"
Cohesion: 0.16
Nodes (20): Cooldowns, _parse_state_text(), Any, Raises on any shape this module does not recognize -- the caller…, The tolerant-parse half of :func:`load_state`, factored out so…, Pure: merges new disk/storage cooldown timestamps into ``state``, keyed exactly…, Re-reads whatever is currently written through an already-open,…, _read_locked_state() (+12 more)

### Community 73 - "Any"
Cohesion: 0.13
Nodes (12): FakeResponse, Any, _RangeStepMismatchFakeClient, test_metrics.py's own ``_StepAwareFakeClient``, restated here for…, A ``range_query`` stand-in that returns caller-supplied data keyed by the exact…, The BundleError fallback (see…, ``RangeStepMismatch`` (a ``--replay`` bundle captured with ``collect-testdata…, Like ``_StepAwareFakeClient``, but raises ``RangeStepMismatch`` (carrying its… (+4 more)

### Community 74 - "Persistent state: state.json"
Cohesion: 0.13
Nodes (19): Persistent state: state.json, flock is the lock; JSON lock field is only a label, Inflight UPIDs written and read for crash recovery, Reading degrades, writing raises, Rename-detaches-flock bug and in-place locked write, staged_disks field unimplemented, Crash and two-instance recovery: crashrecovery.py, Two failure modes, one in-flight UPID mechanism (+11 more)

### Community 75 - "C5 Capacity, snapshot reserve and free space"
Cohesion: 0.17
Nodes (19): Big-M penalty P fallback (computed P_min), (C4) Largest-disk linearization Z_s, C5 Capacity, snapshot reserve and free space, Failure modes and safety table, Companion fixture reserve-tradeoff, free_space requirement soft_s / hard_s, free-space repair fixture, free_space grammar (bytes, unit string, N%) and precedence (+11 more)

### Community 76 - "Mapper"
Cohesion: 0.16
Nodes (19): Mapper, _anonymize_cluster_tasks(), _anonymize_exclude_disk_key(), _anonymize_node_list(), _anonymize_storage_content(), _anonymize_storage_definitions(), _anonymize_storage_resources(), _anonymize_vm_resources() (+11 more)

### Community 77 - "ReplayPveClient"
Cohesion: 0.24
Nodes (4): Any, Unlike every other method here, a missing file is not a bundle defect: a bundle…, Serves ``pve.py``'s eleven read methods from a bundle's ``pve/`` directory.…, ReplayPveClient

### Community 78 - "_handle_apply"
Cohesion: 0.14
Nodes (16): Mutable state box narrow exception to functional style, Startup scan folds excluded vmids before planning, LockHandle, _apply_exit_code(), _handle_apply(), _InflightStateBox, _make_inflight_callbacks(), State (+8 more)

### Community 79 - "pathlib"
Cohesion: 0.13
Nodes (13): argparse, pathlib, Storage DRS for Proxmox VE 9.2. Balances disk I/O load across configurable…, sys, skipif, ``__version__`` must agree with ``pyproject.toml`` and the install instructions., test_install_instructions_name_the_current_version(), check() (+5 more)

### Community 80 - "JsonFormatter"
Cohesion: 0.12
Nodes (15): LogRecord, json_safe(), JsonFormatter, One human-readable line per record: ``LEVEL: message``. Deliberately not a…, Replace every non-finite float with ``None``, recursively. Python's JSON…, Render one :class:`logging.LogRecord` as one JSON line., TextFormatter, Found live: section 7's payback ratio is `+inf` for any plan with no moves to… (+7 more)

### Community 81 - ".agents/documentation.md"
Cohesion: 0.13
Nodes (13): Config knob entry: type, default, unit, extremes, interactions, Tests keeping docs honest (help covers options, manual covers config), --help generated from argparse definitions, no hardcoded defaults, Internals pages: question first, name modules, explain why, ASCII diagrams, Manpage skeleton with complete OPTIONS, config/drs.example.yaml as documentation that parses, Change behaviour and documentation in the same commit, PDF is a build product; fix text not LaTeX (+5 more)

### Community 82 - "resolve_node_selector"
Cohesion: 0.12
Nodes (16): node_names uses GET /nodes, build_node_selector(), _escape_promql_regex_literal(), Escape one literal string for safe use inside a PromQL/RE2 ``=~`` alternation.…, Section 3.4's auto-derived node-scoping filter: ``<node_label>=~"n1|n2|..."``…, The one selector every query in this module inserts, resolved once per run…, resolve_node_selector(), A node named `pve1.example.com` must match only that exact string in RE2 -- an… (+8 more)

### Community 83 - "`execution` — how (and whether) moves actually happen"
Cohesion: 0.12
Nodes (16): `execution.abort_on_failure`, `execution` — how (and whether) moves actually happen, `execution.locks.on_timeout`, `execution.locks.poll_interval`, `execution.locks.task_retry_backoff`, `execution.locks.task_retry_limit`, `execution.locks.wait_timeout`, `execution.max_concurrent_migrations` (+8 more)

### Community 84 - "pve-storage-drs.1.md"
Cohesion: 0.12
Nodes (15): AUTHOR, COLLECT-TESTDATA OPTIONS, COMMANDS, CONFIGURATION, COPYRIGHT, DESCRIPTION, ENVIRONMENT, EXIT STATUS (+7 more)

### Community 85 - "test_forecast.py"
Cohesion: 0.21
Nodes (14): random, _group_series(), _noise_series(), TimeSeries, Holt-Winters forecasting, its backtest gate, and the required-range rule., Fewer than 2 * seasonal_periods samples before now - W: Holt-Winters cannot be…, test_backtest_fails_on_white_noise(), test_backtest_hw_error_is_none_when_the_fit_half_is_too_short() (+6 more)

### Community 86 - "LastBalance"
Cohesion: 0.17
Nodes (15): Drift history reaches the gates via last_balance, LastBalance, load_vector_for_group(), now_iso(), ``at`` is ``None`` before any run has ever executed a migration -- distinct…, This group's slice of ``last_balance.load_vector``, re-keyed from…, Pure: a new :class:`State` with ``group_name``'s slice of…, UTC, second precision, ``Z`` suffix -- exactly section 11.2's own example… (+7 more)

### Community 87 - "PrometheusClient"
Cohesion: 0.25
Nodes (15): Gigapipe step workaround, Metrics page, Node-scoping selector, PrometheusClient, PromQL builders, Range query chunking, SessionLike protocol, verify_metrics six checks (+7 more)

### Community 88 - "Internals: CLI dispatch and logging"
Cohesion: 0.14
Nodes (14): Internals: CLI dispatch and logging, Global options on top-level parser, Command handlers dispatched via dict, JsonFormatter, Structured logs go to stderr, Log levels, mandatory floor, handler on root, --manual prefers man(1), falls back to in-tree markdown, --manual prefers man(1), falls back to plain text (+6 more)

### Community 89 - "Internals: Building the disk/storage/group model"
Cohesion: 0.13
Nodes (14): Internals: Building the disk/storage/group model, (C2) format eligibility: storage_type/allowed_formats, D: every disk placed, pinned or not, Foreign usage U^ext (unreferenced volumes), free_space soft_s/hard_s resolution, Pending-change pin, Per-disk cooldown pin, Disk sizes: content authoritative, config fallback (+6 more)

### Community 90 - "_check_sample_series"
Cohesion: 0.15
Nodes (15): _check_cross_metric_disk_consistency(), _check_sample_series(), _disk_keys_seen(), Finding, format_cross_metric_finding(), One line of ``verify-metrics`` output. ``level`` is info/warning/error., Every distinct ``(vmid, device)`` pair carried by an…, Builds :func:`_check_cross_metric_disk_consistency`'s one finding shape from a… (+7 more)

### Community 91 - "Packaging, dependencies and CI (.agents)"
Cohesion: 0.16
Nodes (14): Git workflow (.agents), Branch first, decided from the task, Merge --no-ff on green make check, Release process (version, changelog, tag, graphify), Packaging, dependencies and CI (.agents), Autopkgtest as the dependency test, coinor-cbc and python3-pulp as Depends, Debian-first dependency policy (trixie) (+6 more)

### Community 92 - "forecast_group"
Cohesion: 0.15
Nodes (13): Collection, Backtest, forecast_group(), group_aggregate_series(), TimeSeries, One group's backtest: absolute error of each model's predicted p95 of ``[now-W,…, Sum every disk's own series into one group-aggregate series, at the union of…, Section 10.2's backtest, comparing against a baseline: fit on ``[now-2W,… (+5 more)

### Community 93 - "Engine pipeline: collect, join, gate, solve, cost, order, execute"
Cohesion: 0.18
Nodes (14): Engine pipeline: collect, join, gate, solve, cost, order, execute, Capacity spread gate (default 0.25), Move completion criterion stronger than task success, Per-disk and per-storage cooldowns, Deadlock and staging, Failure handling (orphans, partial plan, supervision loss), Gating (drift, imbalance, capacity gates, cooldowns, reserve override), Move states mirroring, draining, done (+6 more)

### Community 94 - "forecast.py"
Cohesion: 0.22
Nodes (13): math, ForecastConfig, HoltWintersConfig, Holt-Winters load forecasting. See IMPLEMENTATION_PLAN.md sections 10 and 12.1.…, The history ``forecast.model`` needs, in seconds. Called by ``config.py``'s…, required_range_seconds(), The shipped default (288 periods at a 5m step) over the two cycles the lookback…, test_holt_winters_fits_the_default_288_periods_on_two_bursty_days() (+5 more)

### Community 95 - "PveApiError"
Cohesion: 0.18
Nodes (13): PveApiError, PveUnreachableError, The Proxmox VE API returned an error or an unusable response. See…, A :class:`PveApiError` with ``transient`` set: the API could not be reached, or…, _detect_orphan_volumes(), Section 9.4/domain rule 6: after a failed or cancelled mirror, a target volume…, _api_error(), raise_pve_error() (+5 more)

### Community 96 - "disk_factors"
Cohesion: 0.27
Nodes (13): disk_factors(), ``f_d / h_d`` for every disk that has one: ``f_d`` the Holt-Winters forecast…, _factor_series(), _FixedForecast, MonkeyPatch, 96 hourly samples whose last 24 are ``window_values`` (repeated)., Patches ``holt_winters_quantile`` to a constant so the ratio is exact., test_disk_factors_is_forecast_over_observed_p95() (+5 more)

### Community 97 - "exceptions.py"
Cohesion: 0.19
Nodes (12): DrsError, ExecutionError, Exception, Base class for every error this project raises on purpose., Exception hierarchy for the project. Every error the tool can raise…, Neither solver backend could produce a feasible or heuristic plan. See…, No pending move in a plan is individually feasible right now. See…, A migration failed, or a precondition for executing one did not hold. See… (+4 more)

### Community 98 - "FakeProxmoxResource"
Cohesion: 0.21
Nodes (6): FakePrometheusSession, FakeProxmoxResource, FakeQueryResponse, Any, Matches ``metrics._ResponseLike``: ``.status_code`` and ``.json()``., A ``metrics._SessionLike`` double capable of answering *many* distinct queries…

### Community 99 - "pytest"
Cohesion: 0.18
Nodes (10): fixture, json, logging, pytest, ``auto`` and ``text`` -> ``"text"``; ``json`` -> ``"json"``. JSON is opt-in. It…, Logging policy. See IMPLEMENTATION_PLAN.md section 2.3. Every log record goes…, resolve_format(), Shared pytest fixtures. ``logging`` is process-global state, and… (+2 more)

### Community 100 - "._get"
Cohesion: 0.17
Nodes (5): Issue one request and return the decoded ``data`` field. Typed ``Any`` rather…, ``GET /api/v1/query``. Returns the raw ``data.result`` list., ``GET /api/v1/query_range``. Returns the raw ``data.result`` list., ``GET /api/v1/label/<name>/values``. The one endpoint whose ``data`` is a bare…, ``GET /api/v1/status/buildinfo``: the running Prometheus's own version (section…

### Community 101 - "test_running_task_on_the_vm_is_waited_out_before_move_disk"
Cohesion: 0.23
Nodes (12): log_messages(), LogCaptureFixture, `execution.locks.on_timeout: skip` (the default): the locked head times out…, `/cluster/tasks` shape for a task still running: no endtime/status., The reported failure: an earlier move's "Erase data" (imgdel) job still holds…, Rendered messages of the captured records carrying ``event``., running_imgdel(), test_a_dry_run_issues_no_move_and_logs_none() (+4 more)

### Community 102 - "Transient reserve invariant (operator explanation)"
Cohesion: 0.20
Nodes (11): Transient reserve invariant (operator explanation), Concurrent execution with strict FIFO launch, confirm prompt [y]es/[n]o/[a]ll/[q]uit, apply modes: dry-run, confirm, auto, Pre-flight live re-check before each move, auto re-plan loop, Decision trail events, --log-format text vs json (+3 more)

### Community 103 - "Load model (average in-flight I/O)"
Cohesion: 0.25
Nodes (11): Backtest gate: beat persistence baseline, Storage capability weight and utilization u_s, Drift gate (L1 norm, default 0.10), Forecast scales l_d by f_d/h_d, Holt-Winters forecasting and backtest gate, Holt-Winters seasonal forecast (engine-side), Holt-Winters p95 forecast with backtest gate, Average in-flight I/O requests unit (+3 more)

### Community 104 - "ForecastReport"
Cohesion: 0.22
Nodes (11): _log_forecast(), _note_forecast(), Any, ForecastReport, ``explain``'s one line on what the forecast did to this group's loads., Remember a group's forecast report, if it has one, for the JSON report., Section 12.1 point 6: one line per group, not one per disk. A failed backtest…, _render_forecast_line() (+3 more)

### Community 105 - "_FakeSession"
Cohesion: 0.24
Nodes (8): _FakeProxmoxApiWithSession, _FakeSession, Any, Confirmed live against a real multi-VM cluster: `requests`'s own default…, A small `read_workers` (or the field's own minimum) must not shrink the pool…, test_apply_connection_pool_size_mounts_an_adapter_sized_to_read_workers(), test_apply_connection_pool_size_never_shrinks_below_the_requests_default(), test_build_client_sizes_the_connection_pool_for_token_auth()

### Community 106 - "`proxmox` — the cluster API connection"
Cohesion: 0.20
Nodes (10): `proxmox.auth.password`, `proxmox.auth.token_secret`, `proxmox.auth.username`, `proxmox.ca_file`, `proxmox.host`, `proxmox.port`, `proxmox.read_workers`, `proxmox` — the cluster API connection (+2 more)

### Community 107 - "_issue_chunked_range_query"
Cohesion: 0.20
Nodes (10): _issue_chunked_range_query(), Any, ``client.range_query()``, issued in ``RANGE_QUERY_CHUNK_SECONDS``-sized sub-…, Merges several ``(start, end, result)`` ``query_range`` captures of the *same*…, stitch_range_results(), The common case: a wide range chunked by…, A repeat capture of the same query (not just adjacent chunks) can carry the…, test_stitch_range_results_dedupes_overlapping_timestamps() (+2 more)

### Community 108 - "_outcome"
Cohesion: 0.36
Nodes (10): _gate(), _no_move_schedule(), _outcome(), Any, A replayed dev-cluster bundle: capacity spread 112 %, I/O balanced, the gate…, The local cluster bundle under minmax: one disk carries 80 % of the group's…, test_a_capacity_gated_empty_plan_names_the_two_weights_that_decided_it(), test_an_imbalance_gated_empty_plan_gets_only_the_general_line() (+2 more)

### Community 109 - "test_node_pseudonym_collision_is_refused"
Cohesion: 0.25
Nodes (7): MonkeyPatch, Force two different vmids to hash to the same base slot and confirm both still…, X-09: `vmid`'s own linear probing makes a collision impossible, but nothing did…, test_node_pseudonym_collision_is_refused(), colliding_pseudonym(), test_storage_pseudonym_collision_is_refused(), test_vmid_collision_is_resolved_by_linear_probing()

### Community 110 - "_mapper"
Cohesion: 0.22
Nodes (9): _mapper(), X-09: `manifest.json`'s `counts.dropped_records` is documented as counting…, A task's ``id`` is the vmid its UPID embeds. It used to be copied raw, leaving…, _tasks_by_kind(), test_anonymize_cluster_tasks_maps_the_task_id_with_the_upid(), test_anonymize_disk_value_counts_an_unknown_storage(), test_anonymize_storage_definitions_counts_a_pruned_unknown_node(), test_anonymize_storage_resources_counts_an_unknown_node() (+1 more)

### Community 111 - "_client_with_fake_time"
Cohesion: 0.31
Nodes (7): _client_with_fake_time(), _flaky(), Exception, test_5xx_is_transient_and_tolerance_is_restored(), test_no_retry_by_default_for_non_transient_errors_or_non_idempotent_calls(), test_outage_longer_than_tolerance_raises_a_transient_error(), test_unreachable_api_is_retried_inside_outage_tolerance()

### Community 112 - "Installation and requirements"
Cohesion: 0.25
Nodes (8): First steps after installing, Installation and requirements, Installing the package, Running the timer on exactly one host, Setting up the PVE credential, What you need, Where the configuration is *not*, Where the configuration lives

### Community 113 - "Safety properties, exit codes, and what this build actually does"
Cohesion: 0.25
Nodes (8): forecast (Holt-Winters), verify-metrics exit status and severity levels, Failure to read ends the run with exit 1, forecast: line, Exit codes, Optional dependencies, Safety properties, exit codes, and what this build actually does, What is safe, unconditionally

### Community 114 - "_ResponseLike"
Cohesion: 0.29
Nodes (5): Protocol, The subset of ``requests.Response`` this module relies on., The subset of ``requests.Session`` this module relies on. A structural type…, _ResponseLike, _SessionLike

### Community 115 - "safe_range_step_seconds"
Cohesion: 0.25
Nodes (8): The step to actually send Prometheus for a ``rate()``-based ``query_range``…, safe_range_step_seconds(), The common, correctly-behaving-backend case: nothing to work around., This project's own default (metrics.step == metrics.rate_window == 300s) sits…, A real observed shape (a 7-day-capture config's metrics.step: 1h against the…, test_safe_range_step_seconds_is_a_no_op_below_the_rate_window(), test_safe_range_step_seconds_shrinks_when_equal_to_the_rate_window(), test_safe_range_step_seconds_shrinks_when_step_is_far_above_the_rate_window()

### Community 116 - "test_apply_refuses_the_whole_plan_when_the_aggregate_payback_test_fails"
Cohesion: 0.25
Nodes (5): `_balanced_apply_topology()`'s one move easily clears the default…, test_apply_exits_quietly_when_state_json_is_already_locked(), test_apply_refuses_the_whole_plan_when_the_aggregate_payback_test_fails(), fail(), test_real_local_now_falls_back_when_the_zone_cannot_be_resolved()

### Community 117 - "_findings_to_json"
Cohesion: 0.29
Nodes (7): DiskKey, _findings_to_json(), VerifyMetricsReport, ``verify_metrics()``'s own finding text, and this module's own call log (built…, Bundle-safe rewrite of one ``verify_metrics()`` finding message. Returns…, _redact_finding_message(), _redact_free_text()

### Community 118 - "Configuration page"
Cohesion: 0.43
Nodes (7): Config path resolution order, Configuration page, ResolvedConfig, Secrets from environment, Semantic validation rules, Two-stage validation, Units parsed once

### Community 119 - "State dataclass tree mirrors section 11.2 JSON"
Cohesion: 0.29
Nodes (7): State dataclass tree mirrors section 11.2 JSON, disk_state_key(), ``"<group>:<vmid>:<device>"`` (section 11.2) -- the group prefix is what keeps…, ``"<group>:<storage>"`` (section 11.2)., storage_state_key(), test_disk_state_key_matches_section_11_2_shape(), test_storage_state_key_matches_section_11_2_shape()

### Community 120 - "parse_disk_spec"
Cohesion: 0.29
Nodes (7): _anonymize_disk_value(), _anonymize_vm_config(), parse_disk_spec(), Split a VM config disk value into ``(storage_id, volume_name, params)``. E.g.…, test_filter_disk_value_params_drops_iothread_and_discard(), test_parse_disk_spec(), test_parse_disk_spec_no_params()

### Community 121 - "_forecast_fixture"
Cohesion: 0.43
Nodes (7): apply_forecast(), Section 12.1 point 2: scale each disk's ``l_d`` by its forecast factor ``f_d /…, _forecast_fixture(), test_apply_forecast_leaves_idle_and_no_series_matched_alone(), test_apply_forecast_never_scales_a_flagged_disk_even_if_a_factor_is_given(), test_apply_forecast_scales_only_disks_with_a_factor_and_rebuilds_the_totals(), test_apply_forecast_with_no_factors_is_the_identity()

### Community 122 - "Monitoring status file"
Cohesion: 0.40
Nodes (6): Monitoring status file (statusfile.py), `monitoring` — telling your monitoring system what the last run did, check_statusfile Nagios plugin (monitoring-plugins-contrib), Status file freshness by mtime, Monitoring status file, Structured JSON logging and event catalogue

### Community 123 - "What `plan` does not yet do"
Cohesion: 0.40
Nodes (3): What `plan` does not yet do, PaybackResult, One plan's section 7.3 acceptance verdict. ``aggregate_ok`` (``benefit >=…

### Community 124 - "Logging: what lands where, and what an unattended run records"
Cohesion: 0.33
Nodes (6): Logging: what lands where, and what an unattended run records, Text or JSON, The decision trail, Unattended runs log this without being asked, Under systemd, Verbosity

### Community 125 - "Heuristic fallback (seed, repair, descend, polish)"
Cohesion: 0.47
Nodes (6): CBC via PuLP MILP backend, CP-SAT ortools backend removed (AL-02), Heuristic fallback (seed, repair, descend, polish), Shared feasibility and objective functions (evaluate_assignment), Shared feasibility/objective implementation, CBC via PuLP (only MILP backend)

### Community 126 - "_pid_alive"
Cohesion: 0.33
Nodes (6): _pid_alive(), Best-effort, used only to make a "still held" log message useful to an operator…, pid 1 (init) always exists but is not ours to signal as a normal user --…, test_pid_alive_is_false_for_a_reaped_child(), test_pid_alive_is_true_for_a_process_we_cannot_signal(), test_pid_alive_is_true_for_our_own_process()

### Community 127 - "test_api_outage_beyond_the_tolerance_still_raises"
Cohesion: 0.33
Nodes (4): Network maintenance between issuing `move_disk` and its completion., test_api_outage_beyond_the_tolerance_still_raises(), test_api_outage_while_the_move_task_runs_does_not_fail_the_run(), task_status()

### Community 128 - "Diagnostic bundles: `collect-testdata` and `--replay`"
Cohesion: 0.40
Nodes (5): `collect-testdata`: capturing a bundle, Diagnostic bundles: `collect-testdata` and `--replay`, `--replay`: running against a bundle offline, Sending one to the project, What is in a bundle, and what is not

### Community 130 - "ForecastReport"
Cohesion: 0.40
Nodes (4): ForecastReport, Any, What one group's forecast did this run -- the ``forecast`` block of ``explain``…, test_forecast_report_as_dict_has_the_documented_keys()

### Community 131 - "_quantile"
Cohesion: 0.40
Nodes (5): _quantile(), Linear-interpolation quantile, matching ``numpy.percentile``'s default.…, test_holt_winters_quantile_follows_a_rising_trend_above_the_observed_p95(), test_quantile_matches_numpy_percentile_convention(), test_quantile_of_empty_sequence_raises()

### Community 132 - "resolve_level"
Cohesion: 0.50
Nodes (5): Section 2.3's ladder: ``--quiet`` < default < ``-v`` < ``-vv``. ``--log-level``…, resolve_level(), parametrize, test_log_level_wins_over_both_verbose_and_quiet(), test_resolve_level_ladder()

### Community 133 - "_FakeClient"
Cohesion: 0.40
Nodes (3): str, _FakeClient, The ``"fake-client"`` sentinel every ``build_pve_client`` mock in this file…

### Community 134 - "_all_pinned_sample_topology"
Cohesion: 0.40
Nodes (3): _all_pinned_sample_topology(), `_sample_topology()` with its one movable disk pinned too: san-a violates (C5)…, test_unfixable_shortfall_is_proven_only_for_an_optimal_cbc_solve()

## Knowledge Gaps
- **218 isolated node(s):** `Storage capability weight and utilization u_s`, `state.path`, `max_single_move_duration hard rule`, `Migrations throttled by bwlimit only`, `Keyed pseudonyms with salt` (+213 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1393 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **22 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Persistent state: state.json` connect `Persistent state: state.json` to `state.py`, `test_topology.py`, `execute.py`, `cli.py`, `metrics.py`, `schedule.py`, `heuristic.py`, `Manual: Configuration reference`, `topology.py`, `Overview page`, `LastBalance`, `State dataclass tree mirrors section 11.2 JSON`, `crashrecovery.py`?**
  _High betweenness centrality (0.103) - this node is a cross-community bridge._
- **Why does `Manual: Configuration reference` connect `Manual: Configuration reference` to `generate_expected.py`, `drs.example.yaml (reference configuration)`, `Persistent state: state.json`, `Configuration reference`, `Safety properties, exit codes, and what this build actually does`, `Configuration page`, `Internals: CLI dispatch and logging`, `Internals: Building the disk/storage/group model`, `Monitoring status file`, `Manual: Reading plan`?**
  _High betweenness centrality (0.103) - this node is a cross-community bridge._
- **Why does `Group` connect `Group` to `MonkeyPatch`, `test_topology.py`, `execute.py`, `Path`, `metrics.py`, `test_cli.py`, `test_loadmodel.py`, `schedule.py`, `run`, `topology.py`, `test_gates.py`, `Disk`, `_balanced_apply_topology`, `test_optimize.py`, `run_concurrent`, `test_free_space_repair_fixture.py`, `cli.py`, `collect.py`, `ExecutionConfig`, `main`, `heuristic.py`, `order_moves`, `format_disk_id`, `_render_group_plan_human`, `test_small_disks.py`, `_plan_group`, `test_affinity_repair_fixture.py`, `capture_bundle`, `ForecastReport`, `_forecast_fixture`?**
  _High betweenness centrality (0.092) - this node is a cross-community bridge._
- **Are the 191 inferred relationships involving `Group` (e.g. with `_accumulate_move_stats()` and `_apply_payback_gate()`) actually correct?**
  _`Group` has 191 INFERRED edges - model-reasoned connections that need verification._
- **Are the 94 inferred relationships involving `PveClient` (e.g. with `_apply_payback_gate()` and `_pve_client_for()`) actually correct?**
  _`PveClient` has 94 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Storage capability weight and utilization u_s`, `state.path`, `max_single_move_duration hard rule` to the rest of the system?**
  _218 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `MonkeyPatch` be split into smaller, more focused modules?**
  _Cohesion score 0.05531135531135531 - nodes in this community are weakly interconnected._