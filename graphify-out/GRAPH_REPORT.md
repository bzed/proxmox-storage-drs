# Graph Report - proxmox-storage-drs  (2026-10-03)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 3869 nodes · 11153 edges · 169 communities (142 shown, 27 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 1673 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ab758315`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- MonkeyPatch
- test_topology.py
- execute.py
- generate_expected.py
- test_config.py
- Topology
- metrics.py
- test_cli.py
- Group
- test_metrics.py
- compute_reserve_status
- test_execute.py
- evaluate_assignment
- topology.py
- Configuration reference
- GroupLoad
- Disk
- Storage
- ExecutionResult
- pve.py
- test_optimize.py
- test_statusfile.py
- test_validate_corpus.py
- test_replay.py
- ExecutionConfig
- test_state.py
- PveClient
- test_anonymize.py
- Manual: Reading plan
- make_config
- test_collect.py
- test_free_space_repair_fixture.py
- _vol
- TimeWindow
- Installation and requirements (manual)
- main
- collect.py
- ResolvedConfig
- make_storage
- Transient invariant
- drs.example.yaml (reference configuration)
- test_logging_setup.py
- heuristic.py
- schedule.py
- Manual: Configuration reference
- anonymize.py
- MILP optimization problem
- format_bytes
- Overview page
- ObjectiveBreakdown
- test_documentation.py
- BundleError
- test_small_disks.py
- Monitoring status file
- Mapper
- Proxmox Storage DRS Implementation Plan
- series_of
- build_client
- Execute page
- --replay global option
- _render_group_explain_json
- _plan_group
- config.py
- State
- state.py
- test_affinity_repair_fixture.py
- Path
- move_disk (drive-mirror, delete=1)
- Reading `apply`
- Any
- Where the numbers come from, and how a transport loses them
- capture_bundle
- FakePrometheusSession
- resolve_node_selector
- save_locked_state
- C5 Capacity, snapshot reserve and free space
- _anonymized_config_dict
- reserve.py
- _launch_decision
- pathlib
- json_safe
- Domain invariants (.agents)
- MetricsConfig
- `execution` — how (and whether) moves actually happen
- pve-storage-drs.1.md
- test_forecast.py
- _handle_apply
- PrometheusClient
- Internals: CLI dispatch and logging
- Internals: Building the disk/storage/group model
- parse_disk_range_series
- Testing (.agents)
- forecast_group
- Engine pipeline: collect, join, gate, solve, cost, order, execute
- ForecastConfig
- test_live_transient_check_fails_safe_when_the_live_read_errors
- disk_factors
- _preflight
- fakes.py
- pytest
- balanced_load
- FakeClock
- Transient reserve invariant (operator explanation)
- Load model (average in-flight I/O)
- cli.py
- _FakeSession
- units.py
- Packaging, dependencies and CI (.agents)
- _pin_reason
- AGENTS.md working agreement
- parse_pve_config_size_bytes
- parse_disk_spec
- Installation and requirements
- `proxmox` — the cluster API connection
- repair_markers
- test_plan_gate_also_reflects_real_drift_history_from_state_json
- `objective` — the solver's trade-off weights
- stitch_range_results
- Configuration page
- pending_disk_reasons
- filter_vm_config_fields
- timewindow.py
- test_node_pseudonym_collision_is_refused
- Load model page
- Logging: what lands where, and what an unattended run records
- Heuristic fallback (seed, repair, descend, polish)
- order_moves
- Safety properties, exit codes, and what this build actually does
- Diagnostic bundles: `collect-testdata` and `--replay`
- filters.lua
- _check_cross_metric_disk_consistency
- forecast.py
- Payback page
- _FakeClient
- test_unfixable_shortfall_is_proven_only_for_an_optimal_cbc_solve
- _mapper
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
- test_holt_winters_quantile_forecasts_ceil_window_over_step_steps
- test_load_per_tib_is_zero_not_a_division_error_for_a_zero_size_disk
- test_negative_saferemove_throughput_is_a_rate_not_a_negative_duration
- Gates page
- `load_weights` — combining read/write and time/ops/bytes
- Monitoring: the status file
- proxmox-storage-drs
- _findings_to_json
- Path
- test_task_lock_timeout_retry_drives_inflight_callbacks_for_both_upids
- test_holt_winters_quantile_clamps_at_zero
- test_holt_winters_quantile_is_none_for_a_non_finite_forecast
- `report`
- .load_by_disk_key
- test_pseudonym_differs_by_kind_for_same_value
- build_site.sh

## God Nodes (most connected - your core abstractions)
1. `Group` - 206 edges
2. `PveClient` - 125 edges
3. `Disk` - 85 edges
4. `write_config()` - 80 edges
5. `run()` - 78 edges
6. `Proxmox Storage DRS Implementation Plan` - 78 edges
7. `client_with()` - 77 edges
8. `make_move()` - 75 edges
9. `PrometheusClient` - 74 edges
10. `build_topology()` - 73 edges

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

## Communities (169 total, 27 thin omitted)

### Community 0 - "MonkeyPatch"
Cohesion: 0.05
Nodes (95): _all_pinned_sample_topology(), _fake_build_topology(), _fake_reconcile_inflight(), _patch_show_load_deps(), _patch_show_load_forecast(), CaptureFixture, Exception, MonkeyPatch (+87 more)

### Community 1 - "test_topology.py"
Cohesion: 0.10
Nodes (75): The cluster topology could not be built from the API responses. See…, TopologyError, disk_state_key(), ``"<group>:<vmid>:<device>"`` (section 11.2) -- the group prefix is what keeps…, build_topology(), Build the whole cluster's :class:`Topology` for this run. One pass: every read…, build_fake_client(), _cluster_client() (+67 more)

### Community 2 - "execute.py"
Cohesion: 0.09
Nodes (54): ExcludeConfig, _advance_pending(), _auto_budget_stop_outcome(), Clock, _confirm_decision(), _deadline_exceeded(), _detect_orphan_volumes(), _drained_skip_outcome() (+46 more)

### Community 3 - "generate_expected.py"
Cohesion: 0.07
Nodes (74): The `objective:` line, itertools, StorageState, all_assignments(), best_big_m(), best_lexicographic(), big_m_agreement_threshold(), build() (+66 more)

### Community 4 - "test_config.py"
Cohesion: 0.09
Nodes (70): ConfigError, The configuration file is missing, unreadable or fails validation. See…, minimal_config_dict(), Any, parametrize, Path, skipif, The smallest config that passes structural + semantic validation. (+62 more)

### Community 5 - "Topology"
Cohesion: 0.07
Nodes (64): empty_state(), First-run state: no lock, no recorded balance, no cooldowns, nothing in flight…, The whole cluster's worth of groups, as seen by this run. By the time anything…, Topology, _fragmented_group(), _make_group_plan(), _moved_outcome(), _one_disk_group() (+56 more)

### Community 6 - "metrics.py"
Cohesion: 0.06
Nodes (48): _fetch_all_raw_quantities(), _fetch_raw_quantity(), One of the six section 3.4 raw quantities, quantile-reduced over the decision…, The six section 3.4 series, fetched once and reused for every disk., Reduce raw per-disk metrics to the scalar load vector `ℓ`. See…, _RawQuantities, build_quantile_over_time_promql(), build_rate_promql() (+40 more)

### Community 7 - "test_cli.py"
Cohesion: 0.04
Nodes (54): _balanced_non_violating_topology(), _gate(), _no_move_schedule(), _NodeNamesClient, _one_disk_group_load(), _outcome(), _patch_forecast_deps(), Any (+46 more)

### Community 8 - "Group"
Cohesion: 0.06
Nodes (97): LoadWeights, _aggregate_storages(), apply_forecast(), _blend_loads(), _combine_raw_values(), _combined_raw(), compute_disk_load_series(), compute_group_load() (+89 more)

### Community 9 - "test_metrics.py"
Cohesion: 0.08
Nodes (54): MetricsError, Prometheus could not be queried, or the response was unusable. See…, _check_observed_spacing(), PrometheusClient, Thin wrapper over the Prometheus HTTP API. See section 3.4/3.5. ``session`` is…, Section 3.3 step 6: observed sample spacing vs. ``pvestatd_push_interval``.…, refuse(), raise_metrics_error() (+46 more)

### Community 10 - "compute_reserve_status"
Cohesion: 0.09
Nodes (38): compute_reserve_status(), largest_disk_bytes(), managed_used_bytes(), (C4)/(C5) evaluated for one storage at the assignment ``storage_of`` encodes.…, Z_s: the largest disk on ``storage_id`` under ``storage_of``, 0 if none (C4)., Sum_d z_d for every disk in `D` on ``storage_id`` under ``storage_of`` -- the…, StorageOf, make_disk() (+30 more)

### Community 11 - "test_execute.py"
Cohesion: 0.10
Nodes (68): client_with(), default_group(), make_move(), A move missing from `move_costs_by_key` is never refused for lack of an…, Section 13: `state.json` must learn about a UPID *before* this function goes on…, Not only the happy path -- a `move_disk` task that itself fails still finished…, `dry-run` never calls `move_disk` at all -- the callbacks must simply never…, `ExecutionConfig()`'s own defaults (both caps `1`) must dispatch to the… (+60 more)

### Community 12 - "evaluate_assignment"
Cohesion: 0.08
Nodes (63): best_single_disk_alternative(), compute_vm_weights(), evaluate_assignment(), Section 5.5 step 1: "seed with the current assignment (not from scratch -- we…, Section 5.4's `w_v = max(1, l_v / l_bar)` -- the per-VM weight that scales…, Section 5.4's objective for one candidate ``assignment``.…, The single-disk move closest to being worth taking, among every (movable disk,…, Section 5.5's four-step heuristic (minus "polish"; see the module docstring),… (+55 more)

### Community 13 - "topology.py"
Cohesion: 0.06
Nodes (59): concurrent_futures, FreeSpaceValue, GroupConfig, is_storage_pattern(), One parsed-but-unresolved ``free_space.soft``/``.hard`` entry (section 5.3.1's…, A ``storages[].id`` value is a pattern iff it both begins and ends with ``/``…, The regular expression text of a pattern entry, its two ``/`` delimiters…, storage_pattern_text() (+51 more)

### Community 14 - "Configuration reference"
Cohesion: 0.04
Nodes (46): Configuration reference, `exclude.disks`, `exclude.include_unused_disks`, `exclude.running_only`, `exclude.skip_vms_with_snapshots`, `exclude.storages`, `exclude.tags`, `exclude.vmids` (+38 more)

### Community 15 - "GroupLoad"
Cohesion: 0.15
Nodes (36): evaluate_group_gates(), Section 6, applied in the order it lists: reserve override, then the capacity…, DiskLoad, GroupLoad, One disk's `ℓ_d`. Section 4., One storage's current `L_s`/`u_s`, at the assignment `Disk.current_storage`…, One group's whole load picture for this run. Section 4/6., StorageLoad (+28 more)

### Community 16 - "Disk"
Cohesion: 0.08
Nodes (55): ObjectiveConfig, group_average_fill(), group_average_utilization(), `u* = (Sum_d l_d) / (Sum_s c_s)` (C6) -- a constant under any reassignment of…, `b_bar = (Sum_d z_d + Sum_s U^ext) / (Sum_s C_s)` (section 5.3 (C7)) -- a…, _cbc_capacity_spread_term(), _cbc_feasibility_constraints(), _cbc_objective_terms() (+47 more)

### Community 17 - "Storage"
Cohesion: 0.10
Nodes (53): MigrationConfig, compute_benefit_load_seconds(), compute_move_cost(), evaluate_plan_payback(), Section 7.1's cost for one scheduled move. Only ``source`` is needed (not the…, Section 7.2: ``benefit = (alpha*(E_before - E_after) + delta*(F_before -…, Migration cost and the payback acceptance test. See IMPLEMENTATION_PLAN.md…, Section 7.3: the aggregate acceptance test over a whole plan, plus the hard… (+45 more)

### Community 18 - "ExecutionResult"
Cohesion: 0.07
Nodes (62): `--json`, ExecutionResult, One group's ``execute_plan()`` call. ``stopped_early`` is true for any reason…, Whether this group's execution failed in a way that must end the whole run…, load_state(), Best-effort read of ``path``. See the module docstring: a missing file is the…, _balanced_apply_group_load(), _balanced_apply_topology() (+54 more)

### Community 19 - "pve.py"
Cohesion: 0.05
Nodes (37): proxmoxer, RequestException, requests, ResourceException, PveUnreachableError, A :class:`PveApiError` with ``transient`` set: the API could not be reached, or…, _api_error(), _apply_connection_pool_size() (+29 more)

### Community 20 - "test_optimize.py"
Cohesion: 0.09
Nodes (54): cbc_available(), make_disk(), make_storage(), LogCaptureFixture, MonkeyPatch, parametrize, Deliberately *not* parametrized over the skip-guarded `BACKENDS` list above --…, Section 5.4's D^big: at beta_move_count=1.0, moving `201:efidisk0` (1 MiB) to… (+46 more)

### Community 21 - "test_statusfile.py"
Cohesion: 0.10
Nodes (46): CompletedProcess, contextlib, datetime, needs_plugin, build_run_status(), _one_line(), Collapse any run of whitespace, newlines included, to one space: a newline…, The level policy (section 2.4). ``CRITICAL`` when the run exited non-zero: a… (+38 more)

### Community 22 - "test_validate_corpus.py"
Cohesion: 0.09
Nodes (47): tests_corpus, tests_corpus_validate_corpus, _case(), _invariant_inputs(), MonkeyPatch, needs_full_checkout, parametrize, Path (+39 more)

### Community 23 - "test_replay.py"
Cohesion: 0.11
Nodes (44): PrometheusConfig, _captured_step(), _config_from_bundle(), _free_space_pairs(), MonkeyPatch, Path, AH-06: a live ``free_space`` config is collected as the resolved per-storage…, Section 16.5's one deliberate exception: a bundle captured before section 3.8… (+36 more)

### Community 24 - "ExecutionConfig"
Cohesion: 0.08
Nodes (49): ExecutionConfig, concurrent_client_with(), log_messages(), LogCaptureFixture, The defining property of concurrency: `move_disk` for the second move is issued…, Each move's own UPID reaches both callbacks correctly attributed --…, Two otherwise-independent moves landing on the *same* target: even with…, Section 8.1's generalized invariant, live: san-c has only 2 TiB of headroom… (+41 more)

### Community 25 - "test_state.py"
Cohesion: 0.06
Nodes (64): Drift history reaches the gates via last_balance, flock is the lock; JSON lock field is only a label, ``state.path`` could not be written, or its advisory lock could not be…, StateError, acquire_lock(), LastBalance, load_vector_for_group(), LockInfo (+56 more)

### Community 26 - "PveClient"
Cohesion: 0.07
Nodes (55): PveApiError, The Proxmox VE API returned an error or an unusable response. See…, PveClient, One method per IMPLEMENTATION_PLAN.md section 3.5 endpoint. ``api`` is typed…, Retry idempotent calls that fail because the API is unreachable for up to…, fake_api(), BaseException, raise_pve_error() (+47 more)

### Community 27 - "test_anonymize.py"
Cohesion: 0.09
Nodes (28): make_mapper(), parametrize, Section 16.3: 'the result never depends on iteration order'., anonymize.py: allowlists, pseudonyms, timestamp rebasing. See…, PVE's own `get_next_vm_diskname()` appends a literal `.<format>` to the volume…, anonymize.py's own UPID split must accept exactly what…, test_mapper_post_init_computes_time_offset(), test_node_fqdn_shape_is_preserved() (+20 more)

### Community 28 - "Manual: Reading plan"
Cohesion: 0.11
Nodes (21): cli.py backend dispatch: auto cascades, explicit falls back, gates (drift, imbalance, capacity spread, cooldowns), solver.backend (auto, cbc, heuristic), `solver.heuristic_iterations`, `solver.mip_gap`, `solver.time_limit_seconds`, `solver` — which backend plans, A negative `saferemove_throughput` is normal (+13 more)

### Community 29 - "make_config"
Cohesion: 0.14
Nodes (24): make_config(), make_prometheus_client(), make_pve_client(), --no-series must skip the big, per-group superset range captures -- it does not…, Y-06: the manifest's version fields are machine-generated provenance, not free…, X-09: the printed query count used to treat a multi-day range as one range…, Z-05: a live capture stores every range series at…, Section 3.8/16.3: a real pending edit on the VM's own disk survives as the… (+16 more)

### Community 30 - "test_collect.py"
Cohesion: 0.09
Nodes (38): capture(), Path, X-08: section 16.1's manifest line ("schema, versions, what was captured...")…, X-08: section 16.3 promises the manifest "flags" a non-node-shaped…, Z-03: `resolve_node_selector()`'s tier-1 precedence used to win on *both* sides…, A live capture against the dev cluster found the previous implementation's bug…, verify_metrics() never carries a node selector at all -- nothing to rewrite,…, Even when the configured model is ``quantile``, the bundle is captured with… (+30 more)

### Community 31 - "test_free_space_repair_fixture.py"
Cohesion: 0.15
Nodes (24): `Σ_s r_s` at the assignment ``storage_of`` encodes -- section 7.3's outcome…, total_shortfall_bytes(), _free_space_repair_group(), _loads(), _make_disk(), _make_storage(), parametrize, tests/fixtures/free-space-repair.yaml, built as real topology objects.… (+16 more)

### Community 32 - "_vol"
Cohesion: 0.14
Nodes (14): A `san-c` content responder plus a `move_disk` responder for 201. The listing…, The exclusion is narrow: only 201's *own* mirror target (same VM, the disk's…, Between different storage types the target is allocated at the disk line's…, The same 2 TiB config `size=` and the same 4.5 TiB already on the target, but…, Section 5.3.1's `hard_b` -- resolved once onto `Storage. free_space_hard_bytes`…, _san_c_content_after_201_launches(), content(), move_disk_201() (+6 more)

### Community 33 - "TimeWindow"
Cohesion: 0.19
Nodes (27): TimeWindow, current_deadline(), is_window_active(), True when ``now`` falls inside ``window``, including one that crosses midnight…, ``None`` means "no restriction at all" -- section 2.1's "the engine may plan at…, at(), datetime, execution.time_windows. See proxmox_storage_drs/timewindow.py. (+19 more)

### Community 34 - "Installation and requirements (manual)"
Cohesion: 0.09
Nodes (27): autopkgtest runtime-dependency check, GitHub Actions and Salsa GitLab CI pipelines, Dry-run is the default, Release procedure (version bump, changelog, debian/ tag, graphify commit), /etc/pve/drs.yaml on pmxcfs, Installation and requirements (manual), state.json (node-local state), Nothing is ever deleted automatically (+19 more)

### Community 35 - "main"
Cohesion: 0.10
Nodes (22): ArgumentParser, apply_mode_override(), build_parser(), _fallback_manual_text(), _log_run_summary(), main(), _note_shortfall_for_status(), _pre_config_usage_error() (+14 more)

### Community 36 - "collect.py"
Cohesion: 0.08
Nodes (31): functools, gzip, _anonymize_captured_prometheus(), _anonymize_prometheus_series(), _anonymize_query_text(), Bundle, CallRecord, _dump_json() (+23 more)

### Community 37 - "ResolvedConfig"
Cohesion: 0.11
Nodes (38): CommandHandler, Namespace, _dump_report_json(), _filter_groups(), _handle_explain(), _handle_plan(), _handle_show_load(), _handle_verify_metrics() (+30 more)

### Community 38 - "make_storage"
Cohesion: 0.13
Nodes (27): SourceReleaseConfig, _group_with_types(), make_disk(), make_storage(), Section 9.3: a source_release timeout "does not fail the run: mark the storage…, Same as above, except the second move's *target* -- not source -- is the…, Section 9.3 point 3: PVE's own `saferemove_throughput` (already read live off…, No `saferemove_throughput` configured on the storage (e.g. Ceph RBD or ZFS,… (+19 more)

### Community 39 - "Transient invariant"
Cohesion: 0.15
Nodes (21): Higher bar for safety-critical modules, Affinity repair under payback fixture, bwlimit is the only throttle (saturation guard removed), Generalized concurrent-move invariant / concurrency_ok, Companion fixture affinity repair, free_space requirement soft_s / hard_s, free-space repair fixture, free_space grammar (bytes, unit string, N%) and precedence (+13 more)

### Community 40 - "drs.example.yaml (reference configuration)"
Cohesion: 0.06
Nodes (37): drs.example.yaml (reference configuration), free_space soft_s/hard_s resolution, exclude rules, free_space.soft / free_space.hard, load_weights, `metrics.extra_selector`, `metrics.labels.device`, `metrics.labels.node` (+29 more)

### Community 41 - "test_logging_setup.py"
Cohesion: 0.10
Nodes (37): ast, io, configure_logging(), floor_for_command(), JsonFormatter, The mandatory ``INFO`` floor of section 2.3, or ``None``. A run that can change…, Install this run's log handler. Called once, from ``main()``. ``floor`` is…, Render one :class:`logging.LogRecord` as one JSON line. (+29 more)

### Community 42 - "heuristic.py"
Cohesion: 0.11
Nodes (27): Disk-cooldown pin is not exempted for reserve repair, _RepairCandidate, _best_of(), _best_repair_candidate(), trial_storage_of(), _descend(), storage_of(), HeuristicResult (+19 more)

### Community 43 - "schedule.py"
Cohesion: 0.10
Nodes (38): dataclasses, order_moves(), _pending_moves(), Assignment, Section 8.1's transient invariant, called with the single-move set ``{disk}``…, Section 8.2 priority 1: is ``disk``'s *current* (in ``state``) storage…, Section 8.2's scheduling loop for one group. ``target_assignment`` is normally…, Order a target assignment's moves. See IMPLEMENTATION_PLAN.md section 8.… (+30 more)

### Community 44 - "Manual: Configuration reference"
Cohesion: 0.19
Nodes (14): .agents/ index, Python style (.agents), black vs flake8 disagreements (E203, W503, E704), One implementation of every rule (MILP and heuristic share), Units in names, Manual: Configuration reference, If it fails, Running it (+6 more)

### Community 45 - "anonymize.py"
Cohesion: 0.10
Nodes (21): hashlib, hmac, os, _check_no_pseudonym_collision(), generate_new_salt(), load_or_create_salt(), _pseudonym_int(), Path (+13 more)

### Community 46 - "MILP optimization problem"
Cohesion: 0.20
Nodes (18): beta term: number of migrations, (C3) VM affinity linking, C7 Capacity-spread linearization, (C8) Small disks follow their VM, Data spread as tunable delta preference, delta term: data spread / failure risk, Even data spread as second priority, gamma term: bytes migrated (+10 more)

### Community 47 - "format_bytes"
Cohesion: 0.11
Nodes (27): _accumulate_move_stats(), _make_confirm_move_interactively(), confirm(), The economic test (``aggregate_ok``) and the hard per-move duration rule…, The human form of :class:`_UnfixableShortfall` -- printed whether or not the…, Only called when the gate decided to ACT but the *final* assignment moves…, ``None`` for a group ``apply`` never got as far as executing (a load error, or…, Builds ``execute.py``'s ``ConfirmCallback`` -- the only ``input()`` call in… (+19 more)

### Community 48 - "Overview page"
Cohesion: 0.29
Nodes (12): config.py depends on forecast.py, Module layout, Overview page, Seven-stage pipeline, Two solver backends, Backtest gate, Drift baseline is effective load, Forecast provenance report (+4 more)

### Community 49 - "ObjectiveBreakdown"
Cohesion: 0.09
Nodes (35): What `plan` does not yet do, What this build actually implements, _log_plan_selected(), ``(max_s u_s - min_s u_s) / u*`` -- gates.py's own imbalance formula (section…, Section 5.3's "report any residual `r_s > 0` prominently as an unfixable…, The residual shortfall of ``final_breakdown`` (the assignment the plan actually…, Why ``plan``/``apply`` show a gate verdict of ACT and then no move. The gate…, One group's worth of ``_render_plan_human()``'s report -- shared with… (+27 more)

### Community 50 - "test_documentation.py"
Cohesion: 0.14
Nodes (26): importlib_resources, _flatten_schema_keys(), _load_schema(), _manpage_source_text(), _manual_documented_keys(), Any, needs_full_checkout, parametrize (+18 more)

### Community 51 - "BundleError"
Cohesion: 0.07
Nodes (35): BundleError, DrsError, ExecutionError, Exception, RangeStepMismatch, ``--replay`` found the requested range query, but at a different step than this…, Base class for every error this project raises on purpose., Exception hierarchy for the project. Every error the tool can raise… (+27 more)

### Community 52 - "test_small_disks.py"
Cohesion: 0.14
Nodes (26): _follows(), Section 5.3 (C8): a small disk ends a plan either where it is now, or on a…, (C8) for every small disk of ``group`` at the assignment ``storage_of`` encodes…, small_disk_placement_ok(), small_disks_follow_their_vm(), current(), disk(), efi_repair_group() (+18 more)

### Community 53 - "Monitoring status file"
Cohesion: 0.14
Nodes (15): Never auto-delete a volume, Snapshot reserve never traded for balance, A finished task is not a finished move, Three floors precedence f_s*Z_s > hard_s > soft_s, Monitoring status file (statusfile.py), PVE credential privileges (Datastore.Audit+Allocate, VM.Audit, VM.Config.Disk, VM.Migrate), Snapshot reserve, API token privilege separation (intersection of ACLs) (+7 more)

### Community 54 - "Mapper"
Cohesion: 0.11
Nodes (26): `proxmox.auth.token_id`, filter_allowed_fields(), Mapper, pseudonym(), Drop every key of ``obj`` not in ``allowed``. The one primitive both the…, ``HMAC-SHA256(salt, kind || "\\0" || value)``, truncated to 8 hex chars.…, The stateful half of anonymization: one instance per bundle capture. ``vmid``…, ``node-<8 hex>``, or ``node-<8hex>.<8hex>.invalid`` for an FQDN -- shape… (+18 more)

### Community 55 - "Proxmox Storage DRS Implementation Plan"
Cohesion: 0.10
Nodes (34): Anonymization allowlist, never denylist, Migrations throttled by bwlimit only, C1 Assignment, Configuration and validation rules, Dependencies come from Debian (trixie), Diagnostic bundles (collect-testdata), Disk identity join (vmid, device), Proxmox Storage DRS Implementation Plan (+26 more)

### Community 56 - "series_of"
Cohesion: 0.16
Nodes (16): HoltWintersConfig, holt_winters_quantile(), ``window.quantile`` of the Holt-Winters forecast path over the next…, Any, The shipped default (288 periods at a 5m step) over the two cycles the lookback…, A diurnal series that *ends at its trough*: the last forecast point (one day…, series_of(), test_backtest_is_none_without_a_fit_half() (+8 more)

### Community 57 - "build_client"
Cohesion: 0.12
Nodes (26): The Proxmox VE API client, API token permission is intersection with owner, Best-effort ticket refresh tightening, build_client assembles auth once, bwlimit bytes/s to KiB/s conversion only in move_disk, Single reauthenticate-and-retry in _call, storage_content silently empty without Datastore.Allocate, storage_definitions uses the list form GET /storage (+18 more)

### Community 58 - "Execute page"
Cohesion: 0.36
Nodes (10): Auto mode time window, Concurrent execution, Execute page, execute_plan live revalidation, Four-condition done, Injectable Clock, Live transient check provisioned, Orphans reported never deleted (+2 more)

### Community 59 - "--replay global option"
Cohesion: 0.25
Nodes (9): Allowlist-never-denylist anonymization, Diagnostic bundle directory format, collect-testdata diagnostic bundle, tests/corpus and scrub audit, Global command-line options, Mode override logging (escalation is a warning), HMAC pseudonyms with persisted random salt, --replay global option (+1 more)

### Community 60 - "_render_group_explain_json"
Cohesion: 0.13
Nodes (20): _fragmented_vms(), _load_per_tib(), _objective_breakdown_json(), _pin_action_hint(), _pinned_disks(), _pinned_load_fraction(), Assignment, Section 7.3's advisory ``ell/z`` ratio -- ``0.0`` for a zero-size disk rather… (+12 more)

### Community 61 - "_plan_group"
Cohesion: 0.08
Nodes (29): _apply_payback_gate(), _GroupPlan, _log_gate_decision(), _log_load_digest(), _log_payback_verdict(), _plan_group(), ConfirmCallback, datetime (+21 more)

### Community 62 - "config.py"
Cohesion: 0.08
Nodes (46): jsonschema, ruamel_yaml, ruamel_yaml_error, _build_config(), _check_connection_config(), _check_forecast_window(), _check_group_size(), _check_group_storage_membership() (+38 more)

### Community 63 - "State"
Cohesion: 0.09
Nodes (49): Persistent state: state.json, Reading degrades, writing raises, staged_disks field unimplemented, State dataclass tree mirrors section 11.2 JSON, Crash and two-instance recovery: crashrecovery.py, cluster/tasks vs task_status conventions differ, parse_upid PVE UPID grammar confirmed live, reconcile_inflight: recorded UPIDs plus foreign scan (+41 more)

### Community 64 - "state.py"
Cohesion: 0.08
Nodes (38): Cooldown data stored here, interpreted by topology and heuristic, errno, fcntl, socket, _active_cooldowns(), active_disk_cooldowns(), active_storage_cooldowns(), cooldown_remaining_seconds() (+30 more)

### Community 65 - "test_affinity_repair_fixture.py"
Cohesion: 0.33
Nodes (9): _affinity_repair_group(), _loads(), _make_disk(), _make_storage(), parametrize, tests/fixtures/affinity-repair.yaml, built as real topology objects., IMPLEMENTATION_PLAN.md section 14.7's fixture, exercised through the real…, test_both_milp_backends_agree_with_the_heuristic() (+1 more)

### Community 66 - "Path"
Cohesion: 0.09
Nodes (28): load_config(), Resolve, read, parse and validate the configuration. See section 11 for…, Path, REVIEW.md R-02: when the scheduler can only order *some* of the heuristic's…, Every real subcommand now has a real handler (``explain`` was the last one) so…, A real, on-disk diagnostic bundle -- built the same way test_collect.py does,…, X-10: `--replay ... --mode auto <cmd>` used to log `run_started` and an…, Section 2.3: in text format the log record *is* the human line, so the separate… (+20 more)

### Community 67 - "move_disk (drive-mirror, delete=1)"
Cohesion: 0.15
Nodes (19): approximate-size fallback for qcow2-on-LVM volumes, Mandatory INFO audit floor for confirm/auto runs, (C2) Eligibility via variable fixing, Errors are not mismatches, Structured log event catalogue, Execution modes dry-run, confirm, auto, Logging policy (two audiences, levels, audit floor), Which disks can move online (all buses, efidisk0, tpmstate0, unused) (+11 more)

### Community 68 - "Reading `apply`"
Cohesion: 0.12
Nodes (15): Salted pseudonym anonymization, Bundle layout and manifest, collect-testdata command, Submitting a bundle to the corpus, --estimate and support.max_series_points refusal, --replay offline mode, Concurrent execution, Crash and two-instance recovery (+7 more)

### Community 69 - "Any"
Cohesion: 0.25
Nodes (5): _guarded(), Any, Run ``fn()``, recording its outcome in ``log``. Returns ``None`` (and records…, Wraps a real, already-authenticated :class:`PveClient` and records every call's…, RecordingPveClient

### Community 70 - "Where the numbers come from, and how a transport loses them"
Cohesion: 0.10
Nodes (20): A reference implementation that is well tested, gigapipe with ClickHouse (reference backend), PVE InfluxDB external metric server, instance label collision, OpenTelemetry metric server rejected, Other backends, RRD rejected as data source, Six per-disk blockstat counters (+12 more)

### Community 71 - "capture_bundle"
Cohesion: 0.13
Nodes (21): _build_manifest(), capture_bundle(), _capture_prometheus_files(), capture_range_seconds(), CaptureEstimate, CaptureLog, CaptureOptions, _drive_group_series() (+13 more)

### Community 72 - "FakePrometheusSession"
Cohesion: 0.18
Nodes (17): FakePrometheusSession, A ``metrics._SessionLike`` double capable of answering *many* distinct queries…, _instant_answer(), _range_answer(), A live capture against the dev cluster found this one directly (section 16.3's…, A live capture against the dev cluster found this directly:…, A live capture found this the hard way: ``_check_sample_series()``'s "info"…, Z-02: `_check_coverage()`'s per-disk warning embeds a real vmid taken straight… (+9 more)

### Community 73 - "resolve_node_selector"
Cohesion: 0.12
Nodes (16): node_names uses GET /nodes, build_node_selector(), _escape_promql_regex_literal(), Escape one literal string for safe use inside a PromQL/RE2 ``=~`` alternation.…, Section 3.4's auto-derived node-scoping filter: ``<node_label>=~"n1|n2|..."``…, The one selector every query in this module inserts, resolved once per run…, resolve_node_selector(), A node named `pve1.example.com` must match only that exact string in RE2 -- an… (+8 more)

### Community 74 - "save_locked_state"
Cohesion: 0.19
Nodes (17): Inflight UPIDs written and read for crash recovery, Rename-detaches-flock bug and in-place locked write, Write UPID to disk before the crash can happen, _make_inflight_callbacks(), on_finished(), on_started(), Builds the ``on_inflight_started``/``on_inflight_finished`` pair…, LockHandle (+9 more)

### Community 75 - "C5 Capacity, snapshot reserve and free space"
Cohesion: 0.19
Nodes (15): Big-M penalty P fallback (computed P_min), (C4) Largest-disk linearization Z_s, C5 Capacity, snapshot reserve and free space, Datastore.Allocate needed for storage content listing, Failure modes and safety table, Companion fixture reserve-tradeoff, Lexicographic solve (reserve first, then balance), Per-group MILP optimization model (+7 more)

### Community 76 - "_anonymized_config_dict"
Cohesion: 0.50
Nodes (4): _anonymize_exclude_disk_key(), _anonymized_config_dict(), Section 16.3's "the configuration in the bundle": credentials and endpoints…, ``"vmid:device"`` -- an ``exclude.disks`` entry (section 16.3), the same shape…

### Community 77 - "reserve.py"
Cohesion: 0.14
Nodes (14): GatesConfig, _capacity_spread(), _l1_drift(), Section 6: decide whether to act on a group at all, before the solver runs.…, ``(‖ℓ_last‖₁, ‖ℓ_now − ℓ_last‖₁)`` over the **union** of disk keys present in…, Section 5.3 (C7)'s `(max_s b_s - min_s b_s) / b_bar`, or ``None`` when the gate…, _current_storage(), The snapshot-reserve constraint. See IMPLEMENTATION_PLAN.md section 5.3… (+6 more)

### Community 78 - "_launch_decision"
Cohesion: 0.11
Nodes (25): _inflight_onto(), _inflight_target_volids(), _InflightMove, _is_mirror_target(), _launch_decision(), _LaunchDecision, _live_transient_check(), _LiveCheck (+17 more)

### Community 79 - "pathlib"
Cohesion: 0.13
Nodes (13): argparse, pathlib, Storage DRS for Proxmox VE 9.2. Balances disk I/O load across configurable…, sys, skipif, ``__version__`` must agree with ``pyproject.toml`` and the install instructions., test_install_instructions_name_the_current_version(), check() (+5 more)

### Community 80 - "json_safe"
Cohesion: 0.22
Nodes (7): LogRecord, json_safe(), One human-readable line per record: ``LEVEL: message``. Deliberately not a…, Replace every non-finite float with ``None``, recursively. Python's JSON…, TextFormatter, test_json_safe_replaces_non_finite_floats_recursively(), test_text_formatter_includes_exception_info()

### Community 81 - "Domain invariants (.agents)"
Cohesion: 0.11
Nodes (18): Config knob entry: type, default, unit, extremes, interactions, Tests keeping docs honest (help covers options, manual covers config), --help generated from argparse definitions, no hardcoded defaults, Internals pages: question first, name modules, explain why, ASCII diagrams, Manpage skeleton with complete OPTIONS, config/drs.example.yaml as documentation that parses, Change behaviour and documentation in the same commit, PDF is a build product; fix text not LaTeX (+10 more)

### Community 82 - "MetricsConfig"
Cohesion: 0.07
Nodes (57): _RawTimeSeries, MetricLabels, MetricsConfig, WindowConfig, _fetch_all_raw_quantity_series(), _fetch_raw_quantity_series(), _per_disk_lookup(), One of the six section 3.4 raw quantities as a raw time series over ``[start,… (+49 more)

### Community 83 - "`execution` — how (and whether) moves actually happen"
Cohesion: 0.12
Nodes (16): `execution.abort_on_failure`, `execution` — how (and whether) moves actually happen, `execution.locks.on_timeout`, `execution.locks.poll_interval`, `execution.locks.task_retry_backoff`, `execution.locks.task_retry_limit`, `execution.locks.wait_timeout`, `execution.max_concurrent_migrations` (+8 more)

### Community 84 - "pve-storage-drs.1.md"
Cohesion: 0.12
Nodes (15): AUTHOR, COLLECT-TESTDATA OPTIONS, COMMANDS, CONFIGURATION, COPYRIGHT, DESCRIPTION, ENVIRONMENT, EXIT STATUS (+7 more)

### Community 85 - "test_forecast.py"
Cohesion: 0.19
Nodes (15): random, _group_series(), _noise_series(), TimeSeries, Holt-Winters forecasting, its backtest gate, and the required-range rule., Fewer than 2 * seasonal_periods samples before now - W: Holt-Winters cannot be…, test_backtest_fails_on_white_noise(), test_backtest_hw_error_is_none_when_the_fit_half_is_too_short() (+7 more)

### Community 86 - "_handle_apply"
Cohesion: 0.15
Nodes (16): Mutable state box narrow exception to functional style, Startup scan folds excluded vmids before planning, _apply_exit_code(), _handle_apply(), _InflightStateBox, _note_forecast(), Remember a group's forecast report, if it has one, for the JSON report., A mutable box around the one field of ``state`` that `execute.execute_plan()`'s… (+8 more)

### Community 87 - "PrometheusClient"
Cohesion: 0.25
Nodes (15): Gigapipe step workaround, Metrics page, Node-scoping selector, PrometheusClient, PromQL builders, Range query chunking, SessionLike protocol, verify_metrics six checks (+7 more)

### Community 88 - "Internals: CLI dispatch and logging"
Cohesion: 0.14
Nodes (14): Internals: CLI dispatch and logging, Global options on top-level parser, Command handlers dispatched via dict, JsonFormatter, Structured logs go to stderr, Log levels, mandatory floor, handler on root, --manual prefers man(1), falls back to in-tree markdown, --manual prefers man(1), falls back to plain text (+6 more)

### Community 89 - "Internals: Building the disk/storage/group model"
Cohesion: 0.06
Nodes (38): Internals: Building the disk/storage/group model, (C2) format eligibility: storage_type/allowed_formats, D: every disk placed, pinned or not, Foreign usage U^ext (unreferenced volumes), Pending-change pin, Per-disk cooldown pin, Pin priority: _pin_reason(), reserve.py: shared (C4)/(C5) evaluator (+30 more)

### Community 90 - "parse_disk_range_series"
Cohesion: 0.08
Nodes (19): Protocol, _disk_keys_seen(), parse_disk_range_series(), Any, The subset of ``requests.Response`` this module relies on., The subset of ``requests.Session`` this module relies on. A structural type…, Issue one request and return the decoded ``data`` field. Typed ``Any`` rather…, ``GET /api/v1/query``. Returns the raw ``data.result`` list. (+11 more)

### Community 91 - "Testing (.agents)"
Cohesion: 0.22
Nodes (10): Disks with snapshots pinned, Testing (.agents), Acceptance fixtures and generate_expected.py, 85 percent coverage floor, No network, no real sleep, deterministic ties in tests, Codecov configuration, GitHub Actions Tests workflow, pre-commit hooks (+2 more)

### Community 92 - "forecast_group"
Cohesion: 0.22
Nodes (10): Collection, forecast_group(), group_aggregate_series(), TimeSeries, Sum every disk's own series into one group-aggregate series, at the union of…, One group's forecast: run the backtest on the group aggregate, and only if…, 101:scsi0 has no sample at t=1 at all -- that timestamp still appears (from…, test_group_aggregate_series_empty_input_is_empty() (+2 more)

### Community 93 - "Engine pipeline: collect, join, gate, solve, cost, order, execute"
Cohesion: 0.18
Nodes (14): Engine pipeline: collect, join, gate, solve, cost, order, execute, (C6) Load spread, Capacity spread gate (default 0.25), Move completion criterion stronger than task success, Per-disk and per-storage cooldowns, Deadlock and staging, Gating (drift, imbalance, capacity gates, cooldowns, reserve override), Imbalance gate (default 0.20) (+6 more)

### Community 94 - "ForecastConfig"
Cohesion: 0.48
Nodes (7): ForecastConfig, The history ``forecast.model`` needs, in seconds. Called by ``config.py``'s…, required_range_seconds(), test_holt_winters_required_range_is_the_lookback_when_that_is_longer(), test_holt_winters_required_range_matches_plan_worked_example(), test_quantile_required_range_is_the_lookback(), test_required_range_unknown_model_raises()

### Community 95 - "test_live_transient_check_fails_safe_when_the_live_read_errors"
Cohesion: 0.33
Nodes (6): parametrize, A PVE API error while re-reading the target refuses the move and fails the run…, test_live_transient_check_fails_safe_when_the_live_read_errors(), test_move_charge_bytes_rule(), test_orphan_detection_handles_a_pve_api_error_gracefully(), raise_error()

### Community 96 - "disk_factors"
Cohesion: 0.27
Nodes (13): disk_factors(), ``f_d / h_d`` for every disk that has one: ``f_d`` the Holt-Winters forecast…, _factor_series(), _FixedForecast, MonkeyPatch, 96 hourly samples whose last 24 are ``window_values`` (repeated)., Patches ``holt_winters_quantile`` to a constant so the ratio is exact., test_disk_factors_is_forecast_over_observed_p95() (+5 more)

### Community 97 - "_preflight"
Cohesion: 0.12
Nodes (17): _active_task_on_vm(), _check_lock_once(), _is_excluded_by_tag_or_vmid(), _MoveWaitState, _poll_move_once(), _preflight(), _PreflightResult, ``mismatch`` is ``None`` when every section 9.2 re-check passed; ``volid``… (+9 more)

### Community 98 - "fakes.py"
Cohesion: 0.22
Nodes (5): FakeProxmoxResource, FakeQueryResponse, Any, Shared test doubles. Not collected by pytest (no ``test_`` prefix).…, Matches ``metrics._ResponseLike``: ``.status_code`` and ``.json()``.

### Community 99 - "pytest"
Cohesion: 0.13
Nodes (15): fixture, json, logging, pytest, Section 2.3's ladder: ``--quiet`` < default < ``-v`` < ``-vv``. ``--log-level``…, ``auto`` and ``text`` -> ``"text"``; ``json`` -> ``"json"``. JSON is opt-in. It…, Logging policy. See IMPLEMENTATION_PLAN.md section 2.3. Every log record goes…, resolve_format() (+7 more)

### Community 100 - "balanced_load"
Cohesion: 0.21
Nodes (15): balanced_load(), fill_reserve_statuses(), make_disk(), make_storage(), Section 14.2's initial byte layout: san-a/b/c used 4.5/1.5/0.5 TiB of 8.0 TiB…, A perfectly I/O-balanced GroupLoad for ``group`` -- so only the capacity gate,…, Section 6: the capacity gate acts even though the group is perfectly…, Section 5.3 (C7): "if b_bar = 0 the group holds no data: the term is inactive"… (+7 more)

### Community 101 - "FakeClock"
Cohesion: 0.11
Nodes (19): LocksConfig, MoveCost, Section 7.1's cost for one already-scheduled move., FakeClock, datetime, Section 9.1: the pre-loop time-window check (above) only knows the answer as of…, REVIEW.md T-06's collateral bug: before the fix, this "skipped" outcome let the…, `/cluster/tasks` shape for a task still running: no endtime/status. (+11 more)

### Community 102 - "Transient reserve invariant (operator explanation)"
Cohesion: 0.20
Nodes (11): Transient reserve invariant (operator explanation), Concurrent execution with strict FIFO launch, confirm prompt [y]es/[n]o/[a]ll/[q]uit, apply modes: dry-run, confirm, auto, Pre-flight live re-check before each move, auto re-plan loop, Decision trail events, --log-format text vs json (+3 more)

### Community 103 - "Load model (average in-flight I/O)"
Cohesion: 0.16
Nodes (16): Backtest gate: beat persistence baseline, Storage capability weight and utilization u_s, Drift gate (L1 norm, default 0.10), Forecast scales l_d by f_d/h_d, Holt-Winters forecasting and backtest gate, gigapipe step >= range workaround, Holt-Winters seasonal forecast (engine-side), Holt-Winters p95 forecast with backtest gate (+8 more)

### Community 104 - "cli.py"
Cohesion: 0.11
Nodes (28): shutil, _compute_group_load(), _handle_collect_testdata(), _log_forecast(), Any, ``explain``'s one line on what the forecast did to this group's loads., Section 12.1 point 6: one line per group, not one per disk. A failed backtest…, ``compute_group_load()``, then -- only for ``forecast.model: holt_winters`` --… (+20 more)

### Community 105 - "_FakeSession"
Cohesion: 0.24
Nodes (7): _FakeProxmoxApiWithSession, _FakeSession, Any, Confirmed live against a real multi-VM cluster: `requests`'s own default…, A small `read_workers` (or the field's own minimum) must not shrink the pool…, test_apply_connection_pool_size_mounts_an_adapter_sized_to_read_workers(), test_apply_connection_pool_size_never_shrinks_below_the_requests_default()

### Community 106 - "units.py"
Cohesion: 0.20
Nodes (14): re, parse_duration_seconds(), parse_size_bytes(), Unit parsing and formatting for durations and byte sizes. ``config.py`` is the…, Parse a size into an integer byte count. Accepts a bare number (bytes) or a…, Parse a duration into seconds. Accepts a bare number (seconds) or a string like…, parametrize, Unit parsing/formatting. See proxmox_storage_drs/units.py. (+6 more)

### Community 107 - "Packaging, dependencies and CI (.agents)"
Cohesion: 0.16
Nodes (14): Git workflow (.agents), Branch first, decided from the task, Merge --no-ff on green make check, Release process (version, changelog, tag, graphify), Packaging, dependencies and CI (.agents), Autopkgtest as the dependency test, coinor-cbc and python3-pulp as Depends, Debian-first dependency policy (trixie) (+6 more)

### Community 108 - "_pin_reason"
Cohesion: 0.17
Nodes (12): _pin_reason(), Section 5.3 (C2)'s pin conditions, in the order the plan lists them -- the…, Section 5.3 (C2) lists cooldown before the lock check -- both being true at…, Section 5.3 (C2) lists the pending-change pin (section 3.8) before the cooldown…, test_pin_reason_cooldown_is_reported_with_time_remaining(), test_pin_reason_cooldown_wins_over_lock_per_the_plans_own_order(), test_pin_reason_movable(), test_pin_reason_pending_change_wins_over_cooldown() (+4 more)

### Community 109 - "AGENTS.md working agreement"
Cohesion: 0.21
Nodes (13): fc-tier1 / reserve-tradeoff acceptance fixtures, AGENTS.md working agreement, AGPL-3.0-or-later licence and SPDX headers, black/flake8 E203 W503 E704 ignores, Branch-first git workflow, 85% coverage floor, Documentation pipeline (make docs / docs-check), make check (+5 more)

### Community 110 - "parse_pve_config_size_bytes"
Cohesion: 0.17
Nodes (12): _allowed_formats(), parse_pve_config_size_bytes(), Parse a `size=` value from a VM config line, e.g. ``"512G"``. Returns ``None``…, PVE tags as returned by `cluster/resources`: semicolon-separated, with comma…, Section 5.3 (C2): the disk formats ``storage_type`` can hold. An unrecognised…, _split_tags(), parametrize, test_allowed_formats() (+4 more)

### Community 111 - "parse_disk_spec"
Cohesion: 0.18
Nodes (8): `metrics.labels.vmid`, The pseudonym for a vmid already passed to :meth:`register_vmids`. ``None`` for…, Rebuild a volume id as ``<storage-pseudonym>:<prefix>-<vmid…, parse_disk_spec(), Split a VM config disk value into ``(storage_id, volume_name, params)``. E.g.…, test_filter_disk_value_params_drops_iothread_and_discard(), test_parse_disk_spec(), test_parse_disk_spec_no_params()

### Community 112 - "Installation and requirements"
Cohesion: 0.25
Nodes (8): First steps after installing, Installation and requirements, Installing the package, Running the timer on exactly one host, Setting up the PVE credential, What you need, Where the configuration is *not*, Where the configuration lives

### Community 113 - "`proxmox` — the cluster API connection"
Cohesion: 0.20
Nodes (10): `proxmox.auth.password`, `proxmox.auth.token_secret`, `proxmox.auth.username`, `proxmox.ca_file`, `proxmox.host`, `proxmox.port`, `proxmox.read_workers`, `proxmox` — the cluster API connection (+2 more)

### Community 114 - "repair_markers"
Cohesion: 0.18
Nodes (10): executed_assignment(), Assignment, Section 7.3: "what it will really run" -- ``final_assignment``…, Section 7.3's revert test, one verdict per scheduled move in ``order``: would…, repair_markers(), Storage `a`: 6 TiB disk on a 10 TiB storage, `reserve_factor=2.0` -- required…, The direct case: the sole move IS what repairs `a`'s violation, so holding it…, _revert_test_group() (+2 more)

### Community 115 - "test_plan_gate_also_reflects_real_drift_history_from_state_json"
Cohesion: 0.24
Nodes (10): _imbalanced_group_load(), _no_reserve_violation_topology(), Two storages, generously sized -- unlike `_sample_topology()`, no (C4)/(C5)…, san-a all the load, san-b none -- imbalance is 200% of `u*`, far above the…, Baseline for the next test: with no `state.json` at all, `last_load` is `None`,…, The same fixture as above, except `state.json` now records a `last_balance`…, Same drift-suppression scenario as `show-load`'s, through `plan` -- the two…, test_plan_gate_also_reflects_real_drift_history_from_state_json() (+2 more)

### Community 116 - "`objective` — the solver's trade-off weights"
Cohesion: 0.22
Nodes (9): `objective.affinity_counts_pinned_disks`, `objective.alpha_spread`, `objective.beta_move_count`, `objective.delta_capacity_spread`, `objective.gamma_move_bytes_per_tib`, `objective.kappa_vm_affinity`, `objective.reserve_violation_penalty`, `objective.spread_metric` (+1 more)

### Community 117 - "stitch_range_results"
Cohesion: 0.20
Nodes (10): _issue_chunked_range_query(), Any, ``client.range_query()``, issued in ``RANGE_QUERY_CHUNK_SECONDS``-sized sub-…, Merges several ``(start, end, result)`` ``query_range`` captures of the *same*…, stitch_range_results(), The common case: a wide range chunked by…, A repeat capture of the same query (not just adjacent chunks) can carry the…, test_stitch_range_results_dedupes_overlapping_timestamps() (+2 more)

### Community 118 - "Configuration page"
Cohesion: 0.43
Nodes (7): Config path resolution order, Configuration page, ResolvedConfig, Secrets from environment, Semantic validation rules, Two-stage validation, Units parsed once

### Community 119 - "pending_disk_reasons"
Cohesion: 0.25
Nodes (8): vm_config returns pending value; vm_pending exposes both, pending_disk_reasons(), Section 3.8: which disk device keys in ``GET .../pending`` (section 3.5's…, A key with only `value` (no `pending`/`delete`) is fully in effect -- the…, test_pending_disk_reasons_flags_a_deletion(), test_pending_disk_reasons_flags_an_edited_disk_key(), test_pending_disk_reasons_ignores_a_key_with_no_divergence(), test_pending_disk_reasons_ignores_non_disk_keys_even_when_pending()

### Community 120 - "filter_vm_config_fields"
Cohesion: 0.22
Nodes (9): MappingType, filter_disk_value_params(), filter_vm_config_fields(), filter_vm_pending_entries(), Any, The allowlisted subset of a disk value's ``key=value`` parameters…, ``VM_CONFIG_EXTRA_FIELDS`` plus every disk key matching…, Section 3.8/16.3: reduce ``vm_pending()``'s response to the one boolean signal… (+1 more)

### Community 121 - "timewindow.py"
Cohesion: 0.28
Nodes (8): date, _day_name(), _parse_hhmm(), datetime, ``execution.time_windows``: when ``auto`` mode may execute moves. See…, The absolute instant ``window`` (assumed active at ``now`` -- callers check…, window_close(), time

### Community 122 - "test_node_pseudonym_collision_is_refused"
Cohesion: 0.25
Nodes (7): MonkeyPatch, Force two different vmids to hash to the same base slot and confirm both still…, X-09: `vmid`'s own linear probing makes a collision impossible, but nothing did…, test_node_pseudonym_collision_is_refused(), colliding_pseudonym(), test_storage_pseudonym_collision_is_refused(), test_vmid_collision_is_resolved_by_linear_probing()

### Community 123 - "Load model page"
Cohesion: 0.39
Nodes (8): Symbols D S Uext, apply_forecast scaling, compute_disk_load_series, compute_group_load, Coverage rejection, Current-assignment L_s u_s, Idle group T_g zero, Load model page

### Community 124 - "Logging: what lands where, and what an unattended run records"
Cohesion: 0.33
Nodes (6): Logging: what lands where, and what an unattended run records, Text or JSON, The decision trail, Unattended runs log this without being asked, Under systemd, Verbosity

### Community 125 - "Heuristic fallback (seed, repair, descend, polish)"
Cohesion: 0.47
Nodes (6): CBC via PuLP MILP backend, CP-SAT ortools backend removed (AL-02), Heuristic fallback (seed, repair, descend, polish), Shared feasibility and objective functions (evaluate_assignment), Shared feasibility/objective implementation, CBC via PuLP (only MILP backend)

### Community 126 - "order_moves"
Cohesion: 0.43
Nodes (8): Internals: Ordering the moves (schedule.py), cost_m tiny_disk_bytes, ScheduleResult.final_assignment, order_moves, Residual violation unexecutable, Schedule page, Transient invariant called with single-move set, Tiny disks (cost_m = 0) scheduled first

### Community 127 - "Safety properties, exit codes, and what this build actually does"
Cohesion: 0.25
Nodes (8): forecast (Holt-Winters), verify-metrics exit status and severity levels, Failure to read ends the run with exit 1, forecast: line, Exit codes, Optional dependencies, Safety properties, exit codes, and what this build actually does, What is safe, unconditionally

### Community 128 - "Diagnostic bundles: `collect-testdata` and `--replay`"
Cohesion: 0.40
Nodes (5): `collect-testdata`: capturing a bundle, Diagnostic bundles: `collect-testdata` and `--replay`, `--replay`: running against a bundle offline, Sending one to the project, What is in a bundle, and what is not

### Community 130 - "_check_cross_metric_disk_consistency"
Cohesion: 0.25
Nodes (8): _check_cross_metric_disk_consistency(), format_cross_metric_finding(), Builds :func:`_check_cross_metric_disk_consistency`'s one finding shape from a…, Flags a disk reported by *some* of the six configured metrics but not others --…, REVIEW.md-worthy real-world failure: Telegraf's Prometheus-compatible output…, test_cross_metric_disk_consistency_silent_when_all_metrics_agree(), test_cross_metric_disk_consistency_truncates_a_long_missing_list(), test_cross_metric_disk_consistency_warns_on_a_dropped_field()

### Community 131 - "forecast.py"
Cohesion: 0.18
Nodes (10): math, Backtest, _quantile(), One group's backtest: absolute error of each model's predicted p95 of ``[now-W,…, Section 10.2's backtest, comparing against a baseline: fit on ``[now-2W,…, Holt-Winters load forecasting. See IMPLEMENTATION_PLAN.md sections 10 and 12.1.…, Linear-interpolation quantile, matching ``numpy.percentile``'s default.…, test_quantile_matches_numpy_percentile_convention() (+2 more)

### Community 132 - "Payback page"
Cohesion: 0.52
Nodes (7): compute_move_cost, Mirror duration bwlimit, Payback page, Payback verdict, _plan_group wiring, Reserve-override exemption, Wipe duration magnitude

### Community 133 - "_FakeClient"
Cohesion: 0.40
Nodes (3): str, _FakeClient, The ``"fake-client"`` sentinel every ``build_pve_client`` mock in this file…

### Community 134 - "test_unfixable_shortfall_is_proven_only_for_an_optimal_cbc_solve"
Cohesion: 0.67
Nodes (3): test_unfixable_shortfall_is_proven_only_for_an_optimal_cbc_solve(), outcome(), proven()

### Community 135 - "_mapper"
Cohesion: 0.14
Nodes (12): _mapper(), Any, BaseException, _Raise, X-09: `manifest.json`'s `counts.dropped_records` is documented as counting…, A task's ``id`` is the vmid its UPID embeds. It used to be copied raw, leaving…, _tasks_by_kind(), test_anonymize_cluster_tasks_maps_the_task_id_with_the_upid() (+4 more)

### Community 155 - "Gates page"
Cohesion: 0.53
Nodes (6): Cooldowns not in gates, Drift gate, evaluate_group_gates, Gates page, last_load state, Reserve override gate

### Community 156 - "`load_weights` — combining read/write and time/ops/bytes"
Cohesion: 0.33
Nodes (6): `load_weights.bytes`, `load_weights` — combining read/write and time/ops/bytes, `load_weights.iotime`, `load_weights.ops`, `load_weights.read_factor`, `load_weights.write_factor`

### Community 157 - "Monitoring: the status file"
Cohesion: 0.40
Nodes (5): Freshness: why every run rewrites the file, Monitoring: the status file, What is in the file, What makes a run `OK`, `WARNING` or `CRITICAL`, Wiring it into Nagios/NRPE

### Community 158 - "proxmox-storage-drs"
Cohesion: 0.40
Nodes (4): Getting the tool, proxmox-storage-drs, The documents, The safety properties to rely on

### Community 159 - "_findings_to_json"
Cohesion: 0.40
Nodes (5): _findings_to_json(), ``verify_metrics()``'s own finding text, and this module's own call log (built…, Bundle-safe rewrite of one ``verify_metrics()`` finding message. Returns…, _redact_finding_message(), _redact_free_text()

### Community 160 - "Path"
Cohesion: 0.30
Nodes (5): Path, Section 3.8/16.3: neither a disk key's own `pending` string (a full disk spec,…, test_filter_vm_pending_entries_keeps_only_the_disk_signal(), test_generate_new_salt_rotates_the_mapping(), test_load_or_create_salt_persists_and_is_mode_0600()

### Community 161 - "test_task_lock_timeout_retry_drives_inflight_callbacks_for_both_upids"
Cohesion: 0.50
Nodes (3): Crash recovery (section 11.2/13): a retried move is still always exactly one…, move_disk(), test_task_lock_timeout_retry_drives_inflight_callbacks_for_both_upids()

## Knowledge Gaps
- **222 isolated node(s):** `Storage capability weight and utilization u_s`, `state.path`, `Free-space repair mandate fixture`, `max_single_move_duration hard rule`, `Migrations throttled by bwlimit only` (+217 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1382 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **27 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Group` connect `Group` to `MonkeyPatch`, `test_topology.py`, `execute.py`, `Topology`, `metrics.py`, `test_cli.py`, `test_execute.py`, `evaluate_assignment`, `topology.py`, `GroupLoad`, `Disk`, `Storage`, `ExecutionResult`, `test_optimize.py`, `ExecutionConfig`, `test_free_space_repair_fixture.py`, `main`, `collect.py`, `make_storage`, `heuristic.py`, `schedule.py`, `format_bytes`, `ObjectiveBreakdown`, `test_small_disks.py`, `_render_group_explain_json`, `_plan_group`, `test_affinity_repair_fixture.py`, `Path`, `capture_bundle`, `reserve.py`, `_handle_apply`, `balanced_load`, `FakeClock`, `cli.py`, `repair_markers`, `test_plan_gate_also_reflects_real_drift_history_from_state_json`?**
  _High betweenness centrality (0.091) - this node is a cross-community bridge._
- **Why does `Persistent state: state.json` connect `State` to `state.py`, `execute.py`, `metrics.py`, `cli.py`, `heuristic.py`, `save_locked_state`, `Manual: Configuration reference`, `reserve.py`, `topology.py`, `Overview page`, `test_state.py`?**
  _High betweenness centrality (0.081) - this node is a cross-community bridge._
- **Why does `Manual: Configuration reference` connect `Manual: Configuration reference` to `drs.example.yaml (reference configuration)`, `Manual: Reading plan`, `Configuration reference`, `Monitoring status file`, `Configuration page`, `Internals: CLI dispatch and logging`, `Internals: Building the disk/storage/group model`, `Safety properties, exit codes, and what this build actually does`, `State`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._
- **Are the 191 inferred relationships involving `Group` (e.g. with `_accumulate_move_stats()` and `_apply_payback_gate()`) actually correct?**
  _`Group` has 191 INFERRED edges - model-reasoned connections that need verification._
- **Are the 94 inferred relationships involving `PveClient` (e.g. with `_apply_payback_gate()` and `_pve_client_for()`) actually correct?**
  _`PveClient` has 94 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Storage capability weight and utilization u_s`, `state.path`, `Free-space repair mandate fixture` to the rest of the system?**
  _222 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `MonkeyPatch` be split into smaller, more focused modules?**
  _Cohesion score 0.05353535353535353 - nodes in this community are weakly interconnected._