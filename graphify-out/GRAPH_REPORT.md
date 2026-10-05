# Graph Report - proxmox-storage-drs  (2026-10-05)

## Corpus Check
- 116 files · ~322,903 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 21 file(s) not represented in the graph (top: (none) 12, .sha256 3, .conf 1)

## Summary
- 3957 nodes · 11513 edges · 166 communities (141 shown, 25 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 1704 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9db63081`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- MonkeyPatch
- test_topology.py
- save_locked_state
- generate_expected.py
- test_config.py
- Path
- .agents/documentation.md
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
- test_payback.py
- ExecutionResult
- ._call
- test_optimize.py
- test_statusfile.py
- test_validate_corpus.py
- test_replay.py
- ExecutionConfig
- test_state.py
- PveClient
- test_anonymize.py
- Manual: Reading plan
- _compute_group_load
- test_collect.py
- test_free_space_repair_fixture.py
- _vol
- TimeWindow
- Monitoring status file
- cli.py
- collect.py
- ForecastReport
- make_storage
- Transient invariant
- drs.example.yaml (reference configuration)
- test_logging_setup.py
- heuristic.py
- order_moves
- Manual: Configuration reference
- anonymize.py
- Migration cost (mirror plus saferemove wipe)
- make_config
- Overview page
- ObjectiveBreakdown
- test_documentation.py
- BundleError
- test_small_disks.py
- Topology
- Mapper
- `proxmox` — the cluster API connection
- series_of
- build_client
- Execute page
- Proxmox VE API
- Path
- _handle_apply
- config.py
- test_crashrecovery.py
- State
- test_affinity_repair_fixture.py
- _state_from_dict
- move_disk (drive-mirror, delete=1)
- Reading `apply`
- Any
- Where the numbers come from, and how a transport loses them
- capture_bundle
- FakePrometheusSession
- build_node_selector
- LastBalance
- acquire_lock
- `metrics` — Telegraf/InfluxDB name mapping
- DiskKey
- execute.py
- test_orphan_reason_names_at_most_two_volumes_then_counts_the_rest
- RangeStepMismatch
- order_moves
- metrics.py
- `execution` — how (and whether) moves actually happen
- pve-storage-drs.1.md
- test_forecast.py
- `exclude` — what DRS never touches
- PrometheusClient
- Internals: CLI dispatch and logging
- Internals: Building the disk/storage/group model
- ._get
- Internals: The heuristic solver
- forecast_group
- Engine pipeline: collect, join, gate, solve, cost, order, execute
- ForecastConfig
- PveApiError
- disk_factors
- _exec_group
- FakeProxmoxResource
- pytest
- FakeClock
- MoveCost
- Transient reserve invariant (operator explanation)
- Load model (average in-flight I/O)
- group_average_fill
- _apply_connection_pool_size
- pathlib
- Payback rule and acceptance test
- test_apply_refuses_the_whole_plan_when_the_aggregate_payback_test_fails
- AGENTS.md working agreement
- _pin_reason
- parse_disk_spec
- Installation and requirements
- cooldown_remaining_seconds
- Persistent state: state.json
- Configuration and validation rules
- `objective` — the solver's trade-off weights
- test_plan_after_and_payback_reflect_only_the_scheduled_moves_on_partial_deadlock
- Configuration page
- _client_with_fake_time
- _pid_alive
- Debian-first dependency policy
- test_holt_winters_quantile_clamps_at_zero
- Load model page
- Logging: what lands where, and what an unattended run records
- Proxmox Storage DRS Implementation Plan
- test_holt_winters_quantile_is_none_for_a_non_finite_forecast
- Safety properties, exit codes, and what this build actually does
- Diagnostic bundles: `collect-testdata` and `--replay`
- filters.lua
- _check_cross_metric_disk_consistency
- forecast.py
- Payback page
- _FakeClient
- test_a_crash_leaves_a_critical_status_file_and_still_raises
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
- test_enforce_format.py
- test_holt_winters_quantile_forecasts_ceil_window_over_step_steps
- proxmox_storage_drs
- Gates page
- resolve_level
- proxmox-storage-drs
- VerifyMetricsReport
- Monitoring: the status file
- test_manual_falls_back_when_man_exits_nonzero
- _anonymized_config_dict
- _FakeHttpsBackend
- loadmodel.py
- build_site.sh
- test_every_log_call_carries_an_event

## God Nodes (most connected - your core abstractions)
1. `Group` - 214 edges
2. `PveClient` - 125 edges
3. `Disk` - 93 edges
4. `run()` - 85 edges
5. `write_config()` - 83 edges
6. `make_move()` - 82 edges
7. `client_with()` - 80 edges
8. `build_topology()` - 78 edges
9. `Proxmox Storage DRS Implementation Plan` - 78 edges
10. `PrometheusClient` - 74 edges

## Surprising Connections (you probably didn't know these)
- `The `Group <name> → ACT`/`NO ACTION` line` --references--> `GroupLoad`  [INFERRED]
  docs/manual/25-show-load-and-verify-storages.md → src/proxmox_storage_drs/loadmodel.py
- `What is in the file` --references--> `duration()`  [INFERRED]
  docs/manual/36-monitoring.md → tests/fixtures/generate_expected.py
- `What this build actually implements` --references--> `_plan_group()`  [INFERRED]
  docs/manual/30-safety-and-status.md → src/proxmox_storage_drs/cli.py
- `The `objective:` line` --references--> `ObjectiveBreakdown`  [INFERRED]
  docs/manual/29-explain.md → src/proxmox_storage_drs/heuristic.py
- `What `plan` does not yet do` --references--> `evaluate_assignment()`  [INFERRED]
  docs/manual/27-plan.md → src/proxmox_storage_drs/heuristic.py

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

## Communities (166 total, 25 thin omitted)

### Community 0 - "MonkeyPatch"
Cohesion: 0.06
Nodes (94): _fake_build_topology(), _imbalanced_group_load(), _no_reserve_violation_topology(), _patch_show_load_deps(), _patch_show_load_forecast(), CaptureFixture, Exception, MonkeyPatch (+86 more)

### Community 1 - "test_topology.py"
Cohesion: 0.09
Nodes (80): The cluster topology could not be built from the API responses. See…, TopologyError, disk_state_key(), ``"<group>:<vmid>:<device>"`` (section 11.2) -- the group prefix is what keeps…, build_topology(), Build the whole cluster's :class:`Topology` for this run. One pass: every read…, test_a_format_the_storage_type_cannot_hold_is_refused(), test_disk_state_key_matches_section_11_2_shape() (+72 more)

### Community 2 - "save_locked_state"
Cohesion: 0.19
Nodes (17): Inflight UPIDs written and read for crash recovery, Rename-detaches-flock bug and in-place locked write, Write UPID to disk before the crash can happen, _make_inflight_callbacks(), on_finished(), on_started(), Builds the ``on_inflight_started``/``on_inflight_finished`` pair…, LockHandle (+9 more)

### Community 3 - "generate_expected.py"
Cohesion: 0.07
Nodes (74): The `objective:` line, itertools, StorageState, all_assignments(), best_big_m(), best_lexicographic(), big_m_agreement_threshold(), build() (+66 more)

### Community 4 - "test_config.py"
Cohesion: 0.09
Nodes (70): ConfigError, The configuration file is missing, unreadable or fails validation. See…, minimal_config_dict(), Any, parametrize, Path, skipif, The smallest config that passes structural + semantic validation. (+62 more)

### Community 5 - "Path"
Cohesion: 0.08
Nodes (62): _fragmented_group(), _make_group_plan(), _moved_outcome(), _one_disk_group(), _one_move(), Path, Section 13: a vmid `crashrecovery.reconcile_inflight()` reports is folded into…, The default model must cost nothing extra: no per-disk series fetch. (+54 more)

### Community 6 - ".agents/documentation.md"
Cohesion: 0.13
Nodes (13): Config knob entry: type, default, unit, extremes, interactions, Tests keeping docs honest (help covers options, manual covers config), --help generated from argparse definitions, no hardcoded defaults, Internals pages: question first, name modules, explain why, ASCII diagrams, Manpage skeleton with complete OPTIONS, config/drs.example.yaml as documentation that parses, Change behaviour and documentation in the same commit, PDF is a build product; fix text not LaTeX (+5 more)

### Community 7 - "test_cli.py"
Cohesion: 0.03
Nodes (69): _fake_reconcile_inflight(), _gate(), _no_move_schedule(), _NodeNamesClient, _one_disk_group_load(), _outcome(), _patch_forecast_deps(), Any (+61 more)

### Community 8 - "Group"
Cohesion: 0.10
Nodes (73): LoadWeights, compute_disk_load_series(), compute_group_load(), TimeSeries, Compute one group's :class:`GroupLoad` for this run. Section 4.…, Section 4's `ℓ_d` blend, as a time series per disk over ``[now - range_seconds,…, Group, One storage group: section 5's independent optimization unit. (+65 more)

### Community 9 - "test_metrics.py"
Cohesion: 0.07
Nodes (59): MetricsError, Prometheus could not be queried, or the response was unusable. See…, PrometheusClient, Thin wrapper over the Prometheus HTTP API. See section 3.4/3.5. ``session`` is…, refuse(), raise_metrics_error(), _all_metric_names(), FakeResponse (+51 more)

### Community 10 - "compute_reserve_status"
Cohesion: 0.08
Nodes (45): compute_reserve_status(), largest_disk_bytes(), managed_used_bytes(), IMPLEMENTATION_PLAN.md section 8.1's transient invariant, generalized to an…, (C4)/(C5) evaluated for one storage at the assignment ``storage_of`` encodes.…, ``size_bytes`` rounded *up* to the next whole MiB, in bytes. Up, never to…, Z_s: the largest disk on ``storage_id`` under ``storage_of``, 0 if none (C4).…, Sum_d z_d for every disk in `D` on ``storage_id`` under ``storage_of`` -- the… (+37 more)

### Community 11 - "test_execute.py"
Cohesion: 0.09
Nodes (74): client_with(), default_group(), make_move(), A PVE API error while re-reading the target refuses the move and fails the run…, A move missing from `move_costs_by_key` is never refused for lack of an…, Section 13: `state.json` must learn about a UPID *before* this function goes on…, Not only the happy path -- a `move_disk` task that itself fails still finished…, `dry-run` never calls `move_disk` at all -- the callbacks must simply never… (+66 more)

### Community 12 - "evaluate_assignment"
Cohesion: 0.07
Nodes (69): best_single_disk_alternative(), compute_vm_weights(), evaluate_assignment(), _movable_disks(), `D^mov` (section 5.3): disks (C2) has not fixed in place. A pinned disk's…, Section 5.5 step 1: "seed with the current assignment (not from scratch -- we…, Section 5.4's `w_v = max(1, l_v / l_bar)` -- the per-VM weight that scales…, Section 5.4's objective for one candidate ``assignment``.… (+61 more)

### Community 13 - "topology.py"
Cohesion: 0.05
Nodes (72): concurrent_futures, vm_config returns pending value; vm_pending exposes both, GroupConfig, is_storage_pattern(), A ``storages[].id`` value is a pattern iff it both begins and ends with ``/``…, The regular expression text of a pattern entry, its two ``/`` delimiters…, storage_pattern_text(), StorageConfig (+64 more)

### Community 14 - "Configuration reference"
Cohesion: 0.05
Nodes (44): Configuration reference, `forecast.holt_winters.seasonal`, `forecast.holt_winters.seasonal_periods`, `forecast.holt_winters.trend`, forecast.model (quantile, holt_winters), `forecast` — placing disks for the load they will have, `free_space.hard`, `free_space` — keep N bytes (or N%) free on top of the snapshot reserve (+36 more)

### Community 15 - "GroupLoad"
Cohesion: 0.08
Nodes (60): GatesConfig, _capacity_spread(), evaluate_group_gates(), _l1_drift(), Section 6, applied in the order it lists: reserve override, then the capacity…, Section 6: decide whether to act on a group at all, before the solver runs.…, ``(‖ℓ_last‖₁, ‖ℓ_now − ℓ_last‖₁)`` over the **union** of disk keys present in…, Section 5.3 (C7)'s `(max_s b_s - min_s b_s) / b_bar`, or ``None`` when the gate… (+52 more)

### Community 16 - "Disk"
Cohesion: 0.08
Nodes (54): ObjectiveConfig, group_average_utilization(), `u* = (Sum_d l_d) / (Sum_s c_s)` (C6) -- a constant under any reassignment of…, _cbc_capacity_spread_term(), _cbc_feasibility_constraints(), _cbc_objective_terms(), _cbc_small_disks_follow_their_vm(), _cbc_storage_fill() (+46 more)

### Community 17 - "test_payback.py"
Cohesion: 0.09
Nodes (55): MigrationConfig, compute_benefit_load_seconds(), compute_move_cost(), evaluate_plan_payback(), Section 7.1's cost for one scheduled move. Only ``source`` is needed (not the…, Section 7.2: ``benefit = (alpha*(E_before - E_after) + delta*(F_before -…, Section 7.3: the aggregate acceptance test over a whole plan, plus the hard…, move() (+47 more)

### Community 18 - "ExecutionResult"
Cohesion: 0.08
Nodes (57): `--json`, ExecutionResult, One group's ``execute_plan()`` call. ``stopped_early`` is true for any reason…, Whether this group's execution failed in a way that must end the whole run…, _balanced_apply_group_load(), _balanced_apply_topology(), _check_statusfile(), _monitored_config() (+49 more)

### Community 19 - "._call"
Cohesion: 0.08
Nodes (16): Any, :meth:`_call_once`, retried while the API is unreachable. Only inside…, ``GET /cluster/resources?type=vm``: VM inventory., ``GET /cluster/tasks``: recent/active tasks across **every** node -- the one…, ``GET /cluster/resources?type=storage``: storage inventory., ``GET /nodes``: every node in the cluster, by name. Section 3.4's node-scoping…, ``GET /version``: the running PVE's own version string (section 16.1/16.3's…, ``GET /storage``: every storage's full config, including ``saferemove``.… (+8 more)

### Community 20 - "test_optimize.py"
Cohesion: 0.09
Nodes (54): cbc_available(), make_disk(), make_storage(), LogCaptureFixture, MonkeyPatch, parametrize, Deliberately *not* parametrized over the skip-guarded `BACKENDS` list above --…, Section 5.4's D^big: at beta_move_count=1.0, moving `201:efidisk0` (1 MiB) to… (+46 more)

### Community 21 - "test_statusfile.py"
Cohesion: 0.06
Nodes (64): CompletedProcess, datetime, `report`, `report.warn_pinned_load_fraction`, needs_plugin, os, _publish_status_file(), Section 2.4: leave ``monitoring.status_file``'s ``check_statusfile`` report for… (+56 more)

### Community 22 - "test_validate_corpus.py"
Cohesion: 0.09
Nodes (45): tests_corpus, tests_corpus_validate_corpus, _case(), _invariant_inputs(), MonkeyPatch, needs_full_checkout, parametrize, Path (+37 more)

### Community 23 - "test_replay.py"
Cohesion: 0.11
Nodes (42): PrometheusConfig, _captured_step(), _config_from_bundle(), _free_space_pairs(), MonkeyPatch, Path, AH-06: a live ``free_space`` config is collected as the resolved per-storage…, Section 16.5's one deliberate exception: a bundle captured before section 3.8… (+34 more)

### Community 24 - "ExecutionConfig"
Cohesion: 0.09
Nodes (44): ExecutionConfig, concurrent_client_with(), The defining property of concurrency: `move_disk` for the second move is issued…, Each move's own UPID reaches both callbacks correctly attributed --…, Two otherwise-independent moves landing on the *same* target: even with…, Section 8.1's generalized invariant, live: san-c has only 2 TiB of headroom…, 201's mirror target is already *listed* on san-c at its full 1 TiB by the time…, Between different storage types, or from thin to thick, `move_disk` allocates… (+36 more)

### Community 25 - "test_state.py"
Cohesion: 0.15
Nodes (31): empty_state(), load_state(), _parse_state_text(), First-run state: no lock, no recorded balance, no cooldowns, nothing in flight…, The tolerant-parse half of :func:`load_state`, factored out so…, Best-effort read of ``path``. See the module docstring: a missing file is the…, Clears the descriptive ``lock`` field and releases the OS-level lock, writing…, release_lock() (+23 more)

### Community 26 - "PveClient"
Cohesion: 0.11
Nodes (39): PveClient, One method per IMPLEMENTATION_PLAN.md section 3.5 endpoint. ``api`` is typed…, Retry idempotent calls that fail because the API is unreachable for up to…, fake_api(), BaseException, Shared test doubles. Not collected by pytest (no ``test_`` prefix).…, Section 9.2: "convert at the call site and nowhere else" -- this is that site., A ticket that expired for reasons external to this call (a long confirm-mode… (+31 more)

### Community 27 - "test_anonymize.py"
Cohesion: 0.06
Nodes (42): make_mapper(), MonkeyPatch, parametrize, Path, A node and a storage that happen to share a name must not collide., Section 16.3: 'the result never depends on iteration order'., Force two different vmids to hash to the same base slot and confirm both still…, X-09: `vmid`'s own linear probing makes a collision impossible, but nothing did… (+34 more)

### Community 28 - "Manual: Reading plan"
Cohesion: 0.10
Nodes (21): cli.py backend dispatch: auto cascades, explicit falls back, gates (drift, imbalance, capacity spread, cooldowns), solver.backend (auto, cbc, heuristic), `solver.heuristic_iterations`, `solver.mip_gap`, `solver.time_limit_seconds`, `solver` — which backend plans, A negative `saferemove_throughput` is normal (+13 more)

### Community 29 - "_compute_group_load"
Cohesion: 0.19
Nodes (13): _compute_group_load(), _log_forecast(), Section 12.1 point 6: one line per group, not one per disk. A failed backtest…, ``compute_group_load()``, then -- only for ``forecast.model: holt_winters`` --…, _aggregate_storages(), apply_forecast(), Each storage's ``L_s``/``u_s`` from its disks' ``l_d``, and the group's ``u*``…, Section 12.1 point 2: scale each disk's ``l_d`` by its forecast factor ``f_d /… (+5 more)

### Community 30 - "test_collect.py"
Cohesion: 0.09
Nodes (38): capture(), Path, X-08: section 16.1's manifest line ("schema, versions, what was captured...")…, X-08: section 16.3 promises the manifest "flags" a non-node-shaped…, Z-03: `resolve_node_selector()`'s tier-1 precedence used to win on *both* sides…, A live capture against the dev cluster found the previous implementation's bug…, verify_metrics() never carries a node selector at all -- nothing to rewrite,…, Even when the configured model is ``quantile``, the bundle is captured with… (+30 more)

### Community 31 - "test_free_space_repair_fixture.py"
Cohesion: 0.11
Nodes (29): executed_assignment(), Assignment, Section 7.3: "what it will really run" -- ``final_assignment``…, Section 7.3's revert test, one verdict per scheduled move in ``order``: would…, repair_markers(), `Σ_s r_s` at the assignment ``storage_of`` encodes -- section 7.3's outcome…, total_shortfall_bytes(), _free_space_repair_group() (+21 more)

### Community 32 - "_vol"
Cohesion: 0.17
Nodes (12): A `san-c` content responder plus a `move_disk` responder for 201. The listing…, The exclusion is narrow: only 201's *own* mirror target (same VM, the disk's…, Between different storage types the target is allocated at the disk line's…, Section 5.3.1's `hard_b` -- resolved once onto `Storage. free_space_hard_bytes`…, _san_c_content_after_201_launches(), content(), move_disk_201(), test_concurrent_a_foreign_volume_appearing_after_launch_is_still_counted() (+4 more)

### Community 33 - "TimeWindow"
Cohesion: 0.15
Nodes (34): date, TimeWindow, current_deadline(), _day_name(), is_window_active(), _parse_hhmm(), datetime, ``execution.time_windows``: when ``auto`` mode may execute moves. See… (+26 more)

### Community 34 - "Monitoring status file"
Cohesion: 0.09
Nodes (28): GitHub Actions and Salsa GitLab CI pipelines, Dry-run is the default, Release procedure (version bump, changelog, debian/ tag, graphify commit), Monitoring status file (statusfile.py), /etc/pve/drs.yaml on pmxcfs, Installation and requirements (manual), state.json (node-local state), `monitoring` — telling your monitoring system what the last run did (+20 more)

### Community 35 - "cli.py"
Cohesion: 0.06
Nodes (72): ArgumentParser, CommandHandler, Namespace, shutil, _accumulate_move_stats(), apply_mode_override(), build_parser(), _dump_report_json() (+64 more)

### Community 36 - "collect.py"
Cohesion: 0.07
Nodes (34): functools, gzip, _anonymize_captured_prometheus(), _anonymize_prometheus_series(), _anonymize_query_text(), Bundle, CallRecord, _dump_json() (+26 more)

### Community 37 - "ForecastReport"
Cohesion: 0.28
Nodes (8): Any, ``explain``'s one line on what the forecast did to this group's loads., _render_forecast_line(), _render_show_load_human(), _render_show_load_json(), ForecastReport, Any, What one group's forecast did this run -- the ``forecast`` block of ``explain``…

### Community 38 - "make_storage"
Cohesion: 0.12
Nodes (30): SourceReleaseConfig, _group_with_types(), make_disk(), make_storage(), parametrize, Section 9.3: a source_release timeout "does not fail the run: mark the storage…, Same as above, except the second move's *target* -- not source -- is the…, Section 9.3 point 3: PVE's own `saferemove_throughput` (already read live off… (+22 more)

### Community 39 - "Transient invariant"
Cohesion: 0.09
Nodes (30): Domain invariants (.agents), Enumerate every disk bus, Finished task is not a finished move, Never auto-delete a volume, Provisioned size, never allocated, Disks with snapshots pinned, Snapshot reserve never traded for balance, VM locks are an open set (+22 more)

### Community 40 - "drs.example.yaml (reference configuration)"
Cohesion: 0.10
Nodes (24): drs.example.yaml (reference configuration), free_space soft_s/hard_s resolution, exclude rules, free_space.soft / free_space.hard, load_weights, `migration.account_saferemove_wipe`, `migration.assume_thick_provisioning`, `migration.bwlimit_bytes_per_sec` (+16 more)

### Community 41 - "test_logging_setup.py"
Cohesion: 0.10
Nodes (36): ast, io, configure_logging(), floor_for_command(), JsonFormatter, The mandatory ``INFO`` floor of section 2.3, or ``None``. A run that can change…, Install this run's log handler. Called once, from ``main()``. ``floor`` is…, Render one :class:`logging.LogRecord` as one JSON line. (+28 more)

### Community 42 - "heuristic.py"
Cohesion: 0.09
Nodes (31): dataclasses, Disk-cooldown pin is not exempted for reserve repair, _RepairCandidate, _best_of(), _best_repair_candidate(), trial_storage_of(), _descend(), storage_of() (+23 more)

### Community 43 - "order_moves"
Cohesion: 0.11
Nodes (36): order_moves(), _pending_moves(), Assignment, Section 8.1's transient invariant, called with the single-move set ``{disk}``…, Section 8.2 priority 1: is ``disk``'s *current* (in ``state``) storage…, Section 8.2's scheduling loop for one group. ``target_assignment`` is normally…, _resolves_reserve_violation(), transient_invariant_ok() (+28 more)

### Community 44 - "Manual: Configuration reference"
Cohesion: 0.10
Nodes (28): .agents/ index, Git workflow (.agents), Branch first, decided from the task, Merge --no-ff on green make check, Release process (version, changelog, tag, graphify), Packaging, dependencies and CI (.agents), Autopkgtest as the dependency test, coinor-cbc and python3-pulp as Depends (+20 more)

### Community 45 - "anonymize.py"
Cohesion: 0.11
Nodes (18): hashlib, hmac, _check_no_pseudonym_collision(), generate_new_salt(), load_or_create_salt(), _pseudonym_int(), Path, The one meaningful value a snapshot ``name`` field can carry is the literal… (+10 more)

### Community 46 - "Migration cost (mirror plus saferemove wipe)"
Cohesion: 0.18
Nodes (19): Affinity repair under payback fixture, beta term: number of migrations, bwlimit is the only throttle (saturation guard removed), Data spread as tunable delta preference, delta term: data spread / failure risk, Even data spread as second priority, gamma term: bytes migrated, kappa term: VM disk fragmentation (I/O weighted w_v) (+11 more)

### Community 47 - "make_config"
Cohesion: 0.13
Nodes (26): make_config(), make_prometheus_client(), make_pve_client(), --no-series must skip the big, per-group superset range captures -- it does not…, Y-06: the manifest's version fields are machine-generated provenance, not free…, X-09: the printed query count used to treat a multi-day range as one range…, Z-05: a live capture stores every range series at…, Section 3.8/16.3: a real pending edit on the VM's own disk survives as the… (+18 more)

### Community 48 - "Overview page"
Cohesion: 0.29
Nodes (12): config.py depends on forecast.py, Module layout, Overview page, Seven-stage pipeline, Two solver backends, Backtest gate, Drift baseline is effective load, Forecast provenance report (+4 more)

### Community 49 - "ObjectiveBreakdown"
Cohesion: 0.10
Nodes (34): What `plan` does not yet do, What this build actually implements, _log_plan_selected(), _objective_breakdown_json(), ``(max_s u_s - min_s u_s) / u*`` -- gates.py's own imbalance formula (section…, Section 5.3's "report any residual `r_s > 0` prominently as an unfixable…, The residual shortfall of ``final_breakdown`` (the assignment the plan actually…, Why ``plan``/``apply`` show a gate verdict of ACT and then no move. The gate… (+26 more)

### Community 50 - "test_documentation.py"
Cohesion: 0.10
Nodes (34): argparse, importlib_resources, sys, _flatten_schema_keys(), _load_schema(), _manpage_source_text(), _manual_documented_keys(), Any (+26 more)

### Community 51 - "BundleError"
Cohesion: 0.11
Nodes (22): hash_label_name(), hash_query_text(), The cache key both this module (writing) and ``replay.py`` (reading) derive a…, BundleError, A diagnostic bundle (IMPLEMENTATION_PLAN.md section 16) could not be written or…, bundle_reference_now(), load_manifest(), _NeverSession (+14 more)

### Community 52 - "test_small_disks.py"
Cohesion: 0.14
Nodes (26): _follows(), Section 5.3 (C8): a small disk ends a plan either where it is now, or on a…, (C8) for every small disk of ``group`` at the assignment ``storage_of`` encodes…, small_disk_placement_ok(), small_disks_follow_their_vm(), current(), disk(), efi_repair_group() (+18 more)

### Community 53 - "Topology"
Cohesion: 0.18
Nodes (12): The whole cluster's worth of groups, as seen by this run. By the time anything…, Topology, _all_pinned_sample_topology(), parametrize, `_sample_topology()` with its one movable disk pinned too: san-a violates (C5)…, Section 5.3/9.5: a residual `r_s > 0` is reported prominently, with the byte…, X-05: cli.py used to build one bare topology (for the estimate check) and then…, End to end on the all-pinned sample, with 64 TiB storages so its reserve breach… (+4 more)

### Community 54 - "Mapper"
Cohesion: 0.13
Nodes (28): MappingType, filter_allowed_fields(), filter_disk_value_params(), filter_vm_config_fields(), filter_vm_pending_entries(), Mapper, Any, Drop every key of ``obj`` not in ``allowed``. The one primitive both the… (+20 more)

### Community 55 - "`proxmox` — the cluster API connection"
Cohesion: 0.20
Nodes (10): `proxmox.auth.password`, `proxmox.auth.token_secret`, `proxmox.auth.username`, `proxmox.ca_file`, `proxmox.host`, `proxmox.port`, `proxmox.read_workers`, `proxmox` — the cluster API connection (+2 more)

### Community 56 - "series_of"
Cohesion: 0.16
Nodes (16): HoltWintersConfig, holt_winters_quantile(), ``window.quantile`` of the Holt-Winters forecast path over the next…, Any, The shipped default (288 periods at a 5m step) over the two cycles the lookback…, A diurnal series that *ends at its trough*: the last forecast point (one day…, series_of(), test_backtest_is_none_without_a_fit_half() (+8 more)

### Community 57 - "build_client"
Cohesion: 0.11
Nodes (30): The Proxmox VE API client, API token permission is intersection with owner, Best-effort ticket refresh tightening, build_client assembles auth once, bwlimit bytes/s to KiB/s conversion only in move_disk, Single reauthenticate-and-retry in _call, storage_content silently empty without Datastore.Allocate, storage_definitions uses the list form GET /storage (+22 more)

### Community 58 - "Execute page"
Cohesion: 0.36
Nodes (10): Auto mode time window, Concurrent execution, Execute page, execute_plan live revalidation, Four-condition done, Injectable Clock, Live transient check provisioned, Orphans reported never deleted (+2 more)

### Community 59 - "Proxmox VE API"
Cohesion: 0.09
Nodes (25): Allowlist-never-denylist anonymization, Anonymization allowlist, never denylist, Diagnostic bundle directory format, collect-testdata diagnostic bundle, tests/corpus and scrub audit, Datastore.Allocate needed for storage content listing, Diagnostic bundles (collect-testdata), Disk identity join (vmid, device) (+17 more)

### Community 60 - "Path"
Cohesion: 0.33
Nodes (11): _lvm_def(), Any, Path, test_a_literal_entry_can_set_its_own_value(), test_a_pattern_matching_a_storage_that_cannot_hold_it_names_that_storage(), test_config_has_no_global_enforce_format(), test_config_parses_enforce_format(), test_config_rejects_a_value_other_than_raw_qcow2_or_null() (+3 more)

### Community 61 - "_handle_apply"
Cohesion: 0.06
Nodes (41): Mutable state box narrow exception to functional style, Startup scan folds excluded vmids before planning, _apply_exit_code(), _apply_payback_gate(), _GroupPlan, _handle_apply(), _InflightStateBox, _log_gate_decision() (+33 more)

### Community 62 - "config.py"
Cohesion: 0.07
Nodes (48): jsonschema, ruamel_yaml, ruamel_yaml_error, _build_config(), _check_connection_config(), _check_forecast_window(), _check_group_size(), _check_group_storage_membership() (+40 more)

### Community 63 - "test_crashrecovery.py"
Cohesion: 0.09
Nodes (41): Crash and two-instance recovery: crashrecovery.py, cluster/tasks vs task_status conventions differ, parse_upid PVE UPID grammar confirmed live, reconcile_inflight: recorded UPIDs plus foreign scan, Two failure modes, one in-flight UPID mechanism, AuthConfig, expected_task_user(), parse_upid() (+33 more)

### Community 64 - "State"
Cohesion: 0.14
Nodes (26): Cooldown data stored here, interpreted by topology and heuristic, errno, fcntl, socket, _active_cooldowns(), active_disk_cooldowns(), active_storage_cooldowns(), Cooldowns (+18 more)

### Community 65 - "test_affinity_repair_fixture.py"
Cohesion: 0.29
Nodes (11): _affinity_repair_group(), _loads(), _make_disk(), _make_storage(), parametrize, tests/fixtures/affinity-repair.yaml, built as real topology objects., The full pipeline -- solve, order, cost, benefit, accept -- exactly reproducing…, IMPLEMENTATION_PLAN.md section 14.7's fixture, exercised through the real… (+3 more)

### Community 66 - "_state_from_dict"
Cohesion: 0.33
Nodes (6): Any, Raises on any shape this module does not recognize -- the caller…, _state_from_dict(), _state_to_dict(), Only `schema_version` present -- every other field must default the same way…, test_load_state_tolerates_a_minimal_document()

### Community 67 - "move_disk (drive-mirror, delete=1)"
Cohesion: 0.20
Nodes (15): approximate-size fallback for qcow2-on-LVM volumes, (C2) Eligibility via variable fixing, Errors are not mismatches, Which disks can move online (all buses, efidisk0, tpmstate0, unused), move_disk (drive-mirror, delete=1), Disks with unapplied pending change excluded, Pinned disks are modelled, not ignored, Pre-move live re-validation (+7 more)

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
Cohesion: 0.15
Nodes (22): _handle_collect_testdata(), Section 16.4. Always the real clients -- collect-testdata needs a live cluster…, _build_manifest(), capture_bundle(), _capture_prometheus_files(), capture_range_seconds(), CaptureEstimate, CaptureLog (+14 more)

### Community 72 - "FakePrometheusSession"
Cohesion: 0.18
Nodes (17): FakePrometheusSession, A ``metrics._SessionLike`` double capable of answering *many* distinct queries…, _instant_answer(), _range_answer(), A live capture against the dev cluster found this one directly (section 16.3's…, A live capture against the dev cluster found this directly:…, A live capture found this the hard way: ``_check_sample_series()``'s "info"…, Z-02: `_check_coverage()`'s per-disk warning embeds a real vmid taken straight… (+9 more)

### Community 73 - "build_node_selector"
Cohesion: 0.22
Nodes (9): node_names uses GET /nodes, build_node_selector(), _escape_promql_regex_literal(), Escape one literal string for safe use inside a PromQL/RE2 ``=~`` alternation.…, Section 3.4's auto-derived node-scoping filter: ``<node_label>=~"n1|n2|..."``…, A node named `pve1.example.com` must match only that exact string in RE2 -- an…, test_build_node_selector_empty_list_is_none(), test_build_node_selector_escapes_dots_in_an_fqdn() (+1 more)

### Community 74 - "LastBalance"
Cohesion: 0.17
Nodes (15): Drift history reaches the gates via last_balance, LastBalance, load_vector_for_group(), now_iso(), ``at`` is ``None`` before any run has ever executed a migration -- distinct…, This group's slice of ``last_balance.load_vector``, re-keyed from…, Pure: a new :class:`State` with ``group_name``'s slice of…, UTC, second precision, ``Z`` suffix -- exactly section 11.2's own example… (+7 more)

### Community 75 - "acquire_lock"
Cohesion: 0.20
Nodes (15): ``state.path`` could not be written, or its advisory lock could not be…, StateError, acquire_lock(), LockInfo, Temp file in the same directory, ``fsync``, then ``os.replace`` -- a reader…, Section 11.2's advisory lock: ``fcntl.flock(LOCK_EX | LOCK_NB)`` on ``path``…, Descriptive only -- see the module docstring's "Locking" section for why the…, save_state_atomic() (+7 more)

### Community 76 - "`metrics` — Telegraf/InfluxDB name mapping"
Cohesion: 0.15
Nodes (13): `metrics.extra_selector`, `metrics.labels.device`, `metrics.labels.node`, `metrics.pvestatd_push_interval`, `metrics.rate_window`, `metrics.read_bytes`, `metrics.read_ops`, `metrics.read_time_ns` (+5 more)

### Community 77 - "DiskKey"
Cohesion: 0.08
Nodes (30): _RawTimeSeries, _fetch_raw_quantity_series(), One of the six section 3.4 raw quantities as a raw time series over ``[start,…, DiskKey, parse_disk_range_series(), The ``query_range`` counterpart to :func:`parse_disk_series`: turns a…, The ``(vmid, device)`` identity both Prometheus and the PVE API expose. See…, FakeResponse (+22 more)

### Community 78 - "execute.py"
Cohesion: 0.05
Nodes (105): _render_verify_storages_json(), ExcludeConfig, _active_task_on_vm(), _advance_pending(), _auto_budget_stop_outcome(), _check_lock_once(), Clock, _confirm_decision() (+97 more)

### Community 80 - "RangeStepMismatch"
Cohesion: 0.24
Nodes (5): RangeStepMismatch, ``--replay`` found the requested range query, but at a different step than this…, Any, A minimal, in-process stand-in for a live cluster's Prometheus endpoint, for…, _StepAwareFakeClient

### Community 81 - "order_moves"
Cohesion: 0.43
Nodes (8): Internals: Ordering the moves (schedule.py), cost_m tiny_disk_bytes, ScheduleResult.final_assignment, order_moves, Residual violation unexecutable, Schedule page, Transient invariant called with single-move set, Tiny disks (cost_m = 0) scheduled first

### Community 82 - "metrics.py"
Cohesion: 0.06
Nodes (66): MetricLabels, MetricsConfig, WindowConfig, _fetch_raw_quantity(), One of the six section 3.4 raw quantities, quantile-reduced over the decision…, build_quantile_over_time_promql(), build_rate_promql(), _check_coverage() (+58 more)

### Community 83 - "`execution` — how (and whether) moves actually happen"
Cohesion: 0.12
Nodes (16): `execution.abort_on_failure`, `execution` — how (and whether) moves actually happen, `execution.locks.on_timeout`, `execution.locks.poll_interval`, `execution.locks.task_retry_backoff`, `execution.locks.task_retry_limit`, `execution.locks.wait_timeout`, `execution.max_concurrent_migrations` (+8 more)

### Community 84 - "pve-storage-drs.1.md"
Cohesion: 0.12
Nodes (15): AUTHOR, COLLECT-TESTDATA OPTIONS, COMMANDS, CONFIGURATION, COPYRIGHT, DESCRIPTION, ENVIRONMENT, EXIT STATUS (+7 more)

### Community 85 - "test_forecast.py"
Cohesion: 0.19
Nodes (15): random, _group_series(), _noise_series(), TimeSeries, Holt-Winters forecasting, its backtest gate, and the required-range rule., Fewer than 2 * seasonal_periods samples before now - W: Holt-Winters cannot be…, test_backtest_fails_on_white_noise(), test_backtest_hw_error_is_none_when_the_fit_half_is_too_short() (+7 more)

### Community 86 - "`exclude` — what DRS never touches"
Cohesion: 0.25
Nodes (8): `exclude.disks`, `exclude.include_unused_disks`, `exclude.running_only`, `exclude.skip_vms_with_snapshots`, `exclude.storages`, `exclude.tags`, `exclude.vmids`, `exclude` — what DRS never touches

### Community 87 - "PrometheusClient"
Cohesion: 0.25
Nodes (15): Gigapipe step workaround, Metrics page, Node-scoping selector, PrometheusClient, PromQL builders, Range query chunking, SessionLike protocol, verify_metrics six checks (+7 more)

### Community 88 - "Internals: CLI dispatch and logging"
Cohesion: 0.14
Nodes (14): Internals: CLI dispatch and logging, Global options on top-level parser, Command handlers dispatched via dict, JsonFormatter, Structured logs go to stderr, Log levels, mandatory floor, handler on root, --manual prefers man(1), falls back to in-tree markdown, --manual prefers man(1), falls back to plain text (+6 more)

### Community 89 - "Internals: Building the disk/storage/group model"
Cohesion: 0.10
Nodes (19): Internals: Building the disk/storage/group model, (C2) format eligibility: storage_type/allowed_formats, D: every disk placed, pinned or not, Foreign usage U^ext (unreferenced volumes), Pending-change pin, Per-disk cooldown pin, Pin priority: _pin_reason(), Disk sizes: content authoritative, config fallback (+11 more)

### Community 90 - "._get"
Cohesion: 0.07
Nodes (23): Protocol, decimate_to_configured_step(), _disk_keys_seen(), parse_disk_series(), Any, The inverse of :func:`safe_range_step_seconds`: recover a series at…, The subset of ``requests.Response`` this module relies on., The subset of ``requests.Session`` this module relies on. A structural type… (+15 more)

### Community 91 - "Internals: The heuristic solver"
Cohesion: 0.12
Nodes (19): reserve.py: shared (C4)/(C5) evaluator, Internals: The heuristic solver, Descend explores swaps, evaluate_assignment(): objective separate from search, objective.spread_metric: two different quantities, Storage cooldown excludes destination, never source, Repair is unconditional, not weight-driven, w_v: kappa weighted by VM I/O, and D^big (+11 more)

### Community 92 - "forecast_group"
Cohesion: 0.22
Nodes (10): Collection, forecast_group(), group_aggregate_series(), TimeSeries, Sum every disk's own series into one group-aggregate series, at the union of…, One group's forecast: run the backtest on the group aggregate, and only if…, 101:scsi0 has no sample at t=1 at all -- that timestamp still appears (from…, test_group_aggregate_series_empty_input_is_empty() (+2 more)

### Community 93 - "Engine pipeline: collect, join, gate, solve, cost, order, execute"
Cohesion: 0.14
Nodes (15): Engine pipeline: collect, join, gate, solve, cost, order, execute, Mandatory INFO audit floor for confirm/auto runs, Move completion criterion stronger than task success, Per-disk and per-storage cooldowns, Deadlock and staging, Structured log event catalogue, Execution modes dry-run, confirm, auto, Logging policy (two audiences, levels, audit floor) (+7 more)

### Community 94 - "ForecastConfig"
Cohesion: 0.48
Nodes (7): ForecastConfig, The history ``forecast.model`` needs, in seconds. Called by ``config.py``'s…, required_range_seconds(), test_holt_winters_required_range_is_the_lookback_when_that_is_longer(), test_holt_winters_required_range_matches_plan_worked_example(), test_quantile_required_range_is_the_lookback(), test_required_range_unknown_model_raises()

### Community 95 - "PveApiError"
Cohesion: 0.10
Nodes (23): contextlib, proxmoxer, RequestException, requests, ResourceException, PveApiError, PveUnreachableError, Exception hierarchy for the project. Every error the tool can raise… (+15 more)

### Community 96 - "disk_factors"
Cohesion: 0.27
Nodes (13): disk_factors(), ``f_d / h_d`` for every disk that has one: ``f_d`` the Holt-Winters forecast…, _factor_series(), _FixedForecast, MonkeyPatch, 96 hourly samples whose last 24 are ``window_values`` (repeated)., Patches ``holt_winters_quantile`` to a constant so the ratio is exact., test_disk_factors_is_forecast_over_observed_p95() (+5 more)

### Community 97 - "_exec_group"
Cohesion: 0.24
Nodes (10): _exec_disk(), _exec_group(), _posted_move(), The live transient check charges the converted size from the live `size=`., test_a_converting_move_is_refused_when_the_live_check_finds_no_room(), test_a_live_format_that_differs_from_the_plan_means_replan(), test_format_is_not_sent_when_the_disk_already_has_the_enforced_format(), test_format_is_not_sent_without_enforcement() (+2 more)

### Community 98 - "FakeProxmoxResource"
Cohesion: 0.25
Nodes (4): FakeProxmoxResource, FakeQueryResponse, Any, Matches ``metrics._ResponseLike``: ``.status_code`` and ``.json()``.

### Community 99 - "pytest"
Cohesion: 0.11
Nodes (16): fixture, json, logging, LogRecord, pytest, json_safe(), One human-readable line per record: ``LEVEL: message``. Deliberately not a…, ``auto`` and ``text`` -> ``"text"``; ``json`` -> ``"json"``. JSON is opt-in. It… (+8 more)

### Community 100 - "FakeClock"
Cohesion: 0.13
Nodes (19): LocksConfig, FakeClock, log_messages(), datetime, LogCaptureFixture, `/cluster/tasks` shape for a task still running: no endtime/status., The reported failure: an earlier move's "Erase data" (imgdel) job still holds…, Section 9.3 point 3: the very race this fix targets -- a `move_disk` task's own… (+11 more)

### Community 101 - "MoveCost"
Cohesion: 0.18
Nodes (10): MoveCost, Section 7.1's cost for one already-scheduled move., REVIEW.md R-05: an economic failure (benefit < ratio*cost) and a hard per-move…, test_render_plan_payback_lines_separates_economic_and_duration_failures(), make_result(), Section 9.1: the pre-loop time-window check (above) only knows the answer as of…, REVIEW.md T-06's collateral bug: before the fix, this "skipped" outcome let the…, test_deadline_recheck_after_a_lock_wait_refuses_a_move_that_no_longer_fits() (+2 more)

### Community 102 - "Transient reserve invariant (operator explanation)"
Cohesion: 0.20
Nodes (11): Transient reserve invariant (operator explanation), Concurrent execution with strict FIFO launch, confirm prompt [y]es/[n]o/[a]ll/[q]uit, apply modes: dry-run, confirm, auto, Pre-flight live re-check before each move, auto re-plan loop, Decision trail events, --log-format text vs json (+3 more)

### Community 103 - "Load model (average in-flight I/O)"
Cohesion: 0.12
Nodes (20): Backtest gate: beat persistence baseline, Storage capability weight and utilization u_s, Drift gate (L1 norm, default 0.10), Failure handling (orphans, partial plan, supervision loss), Forecast scales l_d by f_d/h_d, Holt-Winters forecasting and backtest gate, gigapipe step >= range workaround, Holt-Winters seasonal forecast (engine-side) (+12 more)

### Community 104 - "group_average_fill"
Cohesion: 0.07
Nodes (45): _fragmented_vms(), _load_per_tib(), _make_confirm_move_interactively(), confirm(), _pin_action_hint(), _pinned_disks(), _pinned_load_fraction(), Assignment (+37 more)

### Community 105 - "_apply_connection_pool_size"
Cohesion: 0.18
Nodes (11): _apply_connection_pool_size(), Size the underlying ``requests`` session's connection pool to fit…, _FakeProxmoxApiWithSession, _FakeSession, Any, Confirmed live against a real multi-VM cluster: `requests`'s own default…, A small `read_workers` (or the field's own minimum) must not shrink the pool…, A plain string, an object with no ``_store``, or a session-shaped object with… (+3 more)

### Community 106 - "pathlib"
Cohesion: 0.13
Nodes (18): pathlib, re, parse_duration_seconds(), parse_size_bytes(), Unit parsing and formatting for durations and byte sizes. ``config.py`` is the…, Parse a size into an integer byte count. Accepts a bare number (bytes) or a…, Parse a duration into seconds. Accepts a bare number (seconds) or a string like…, parametrize (+10 more)

### Community 107 - "Payback rule and acceptance test"
Cohesion: 0.19
Nodes (13): Failure modes and safety table, Companion fixture affinity repair, free_space requirement soft_s / hard_s, free-space repair fixture, free_space grammar (bytes, unit string, N%) and precedence, Free-space repair mandate fixture, Free-space repair mandate, max_single_move_duration hard rule (+5 more)

### Community 108 - "test_apply_refuses_the_whole_plan_when_the_aggregate_payback_test_fails"
Cohesion: 0.25
Nodes (5): `_balanced_apply_topology()`'s one move easily clears the default…, test_apply_exits_quietly_when_state_json_is_already_locked(), test_apply_refuses_the_whole_plan_when_the_aggregate_payback_test_fails(), fail(), test_real_local_now_falls_back_when_the_zone_cannot_be_resolved()

### Community 109 - "AGENTS.md working agreement"
Cohesion: 0.16
Nodes (16): fc-tier1 / reserve-tradeoff acceptance fixtures, AGENTS.md working agreement, AGPL-3.0-or-later licence and SPDX headers, black/flake8 E203 W503 E704 ignores, Branch-first git workflow, 85% coverage floor, Documentation pipeline (make docs / docs-check), make check (+8 more)

### Community 110 - "_pin_reason"
Cohesion: 0.17
Nodes (12): _pin_reason(), Section 5.3 (C2)'s pin conditions, in the order the plan lists them -- the…, Section 5.3 (C2) lists cooldown before the lock check -- both being true at…, Section 5.3 (C2) lists the pending-change pin (section 3.8) before the cooldown…, test_pin_reason_cooldown_is_reported_with_time_remaining(), test_pin_reason_cooldown_wins_over_lock_per_the_plans_own_order(), test_pin_reason_movable(), test_pin_reason_pending_change_wins_over_cooldown() (+4 more)

### Community 111 - "parse_disk_spec"
Cohesion: 0.08
Nodes (16): `metrics.labels.vmid`, `proxmox.auth.token_id`, pseudonym(), ``HMAC-SHA256(salt, kind || "\\0" || value)``, truncated to 8 hex chars.…, The pseudonym for a vmid already passed to :meth:`register_vmids`. ``None`` for…, ``node-<8 hex>``, or ``node-<8hex>.<8hex>.invalid`` for an FQDN -- shape…, ``user-<8 hex>@realm`` -- only ever seen inside a UPID (section 16.3). A value…, Rebuild a volume id as ``<storage-pseudonym>:<prefix>-<vmid… (+8 more)

### Community 112 - "Installation and requirements"
Cohesion: 0.25
Nodes (8): First steps after installing, Installation and requirements, Installing the package, Running the timer on exactly one host, Setting up the PVE credential, What you need, Where the configuration is *not*, Where the configuration lives

### Community 113 - "cooldown_remaining_seconds"
Cohesion: 0.29
Nodes (7): cooldown_remaining_seconds(), Seconds left in ``key``'s cooldown -- ``0.0`` if nothing is recorded for it,…, A hand-edited or foreign timestamp must degrade to "not in cooldown", not raise…, test_cooldown_remaining_seconds_counts_down_from_the_recorded_timestamp(), test_cooldown_remaining_seconds_is_zero_for_an_unparseable_timestamp(), test_cooldown_remaining_seconds_is_zero_once_expired(), test_cooldown_remaining_seconds_is_zero_when_the_key_is_absent()

### Community 114 - "Persistent state: state.json"
Cohesion: 0.25
Nodes (8): Persistent state: state.json, flock is the lock; JSON lock field is only a label, Reading degrades, writing raises, staged_disks field unimplemented, State dataclass tree mirrors section 11.2 JSON, ``"<group>:<storage>"`` (section 11.2)., storage_state_key(), test_storage_state_key_matches_section_11_2_shape()

### Community 115 - "Configuration and validation rules"
Cohesion: 0.40
Nodes (6): Configuration and validation rules, Companion fixture free-space repair mandate, free_space configuration (soft/hard floors), Requirements traceability, Storage name patterns /…/ in groups, Storage name /regex/ patterns

### Community 116 - "`objective` — the solver's trade-off weights"
Cohesion: 0.22
Nodes (9): `objective.affinity_counts_pinned_disks`, `objective.alpha_spread`, `objective.beta_move_count`, `objective.delta_capacity_spread`, `objective.gamma_move_bytes_per_tib`, `objective.kappa_vm_affinity`, `objective.reserve_violation_penalty`, `objective.spread_metric` (+1 more)

### Community 117 - "test_plan_after_and_payback_reflect_only_the_scheduled_moves_on_partial_deadlock"
Cohesion: 0.22
Nodes (9): load_config(), Resolve, read, parse and validate the configuration. See section 11 for…, REVIEW.md R-02: when the scheduler can only order *some* of the heuristic's…, test_metrics_client_for_returns_replay_client_when_replay_is_set(), test_plan_after_and_payback_reflect_only_the_scheduled_moves_on_partial_deadlock(), test_pve_client_for_returns_a_real_client_without_replay(), test_pve_client_for_returns_replay_client_when_replay_is_set(), test_state_path_for_replay_points_inside_the_bundle() (+1 more)

### Community 118 - "Configuration page"
Cohesion: 0.43
Nodes (7): Config path resolution order, Configuration page, ResolvedConfig, Secrets from environment, Semantic validation rules, Two-stage validation, Units parsed once

### Community 119 - "_client_with_fake_time"
Cohesion: 0.31
Nodes (7): _client_with_fake_time(), _flaky(), Exception, test_5xx_is_transient_and_tolerance_is_restored(), test_no_retry_by_default_for_non_transient_errors_or_non_idempotent_calls(), test_outage_longer_than_tolerance_raises_a_transient_error(), test_unreachable_api_is_retried_inside_outage_tolerance()

### Community 120 - "_pid_alive"
Cohesion: 0.33
Nodes (6): _pid_alive(), Best-effort, used only to make a "still held" log message useful to an operator…, pid 1 (init) always exists but is not ours to signal as a normal user --…, test_pid_alive_is_false_for_a_reaped_child(), test_pid_alive_is_true_for_a_process_we_cannot_signal(), test_pid_alive_is_true_for_our_own_process()

### Community 121 - "Debian-first dependency policy"
Cohesion: 0.40
Nodes (5): autopkgtest runtime-dependency check, Autopkgtest install-with-only-Depends check, Debian-first dependency policy, Debian package and CI pipelines (GitHub Actions, Salsa), MILP solver (CBC via python3-pulp) with heuristic fallback

### Community 123 - "Load model page"
Cohesion: 0.39
Nodes (8): Symbols D S Uext, apply_forecast scaling, compute_disk_load_series, compute_group_load, Coverage rejection, Current-assignment L_s u_s, Idle group T_g zero, Load model page

### Community 124 - "Logging: what lands where, and what an unattended run records"
Cohesion: 0.33
Nodes (6): Logging: what lands where, and what an unattended run records, Text or JSON, The decision trail, Unattended runs log this without being asked, Under systemd, Verbosity

### Community 125 - "Proxmox Storage DRS Implementation Plan"
Cohesion: 0.14
Nodes (30): Big-M penalty P fallback (computed P_min), Migrations throttled by bwlimit only, C1 Assignment, (C3) VM affinity linking, (C4) Largest-disk linearization Z_s, C5 Capacity, snapshot reserve and free space, (C6) Load spread, C7 Capacity-spread linearization (+22 more)

### Community 127 - "Safety properties, exit codes, and what this build actually does"
Cohesion: 0.25
Nodes (8): forecast (Holt-Winters), verify-metrics exit status and severity levels, Failure to read ends the run with exit 1, forecast: line, Exit codes, Optional dependencies, Safety properties, exit codes, and what this build actually does, What is safe, unconditionally

### Community 128 - "Diagnostic bundles: `collect-testdata` and `--replay`"
Cohesion: 0.40
Nodes (5): `collect-testdata`: capturing a bundle, Diagnostic bundles: `collect-testdata` and `--replay`, `--replay`: running against a bundle offline, Sending one to the project, What is in a bundle, and what is not

### Community 130 - "_check_cross_metric_disk_consistency"
Cohesion: 0.33
Nodes (6): _check_cross_metric_disk_consistency(), Flags a disk reported by *some* of the six configured metrics but not others --…, REVIEW.md-worthy real-world failure: Telegraf's Prometheus-compatible output…, test_cross_metric_disk_consistency_silent_when_all_metrics_agree(), test_cross_metric_disk_consistency_truncates_a_long_missing_list(), test_cross_metric_disk_consistency_warns_on_a_dropped_field()

### Community 131 - "forecast.py"
Cohesion: 0.18
Nodes (10): math, Backtest, _quantile(), One group's backtest: absolute error of each model's predicted p95 of ``[now-W,…, Section 10.2's backtest, comparing against a baseline: fit on ``[now-2W,…, Holt-Winters load forecasting. See IMPLEMENTATION_PLAN.md sections 10 and 12.1.…, Linear-interpolation quantile, matching ``numpy.percentile``'s default.…, test_quantile_matches_numpy_percentile_convention() (+2 more)

### Community 132 - "Payback page"
Cohesion: 0.52
Nodes (7): compute_move_cost, Mirror duration bwlimit, Payback page, Payback verdict, _plan_group wiring, Reserve-override exemption, Wipe duration magnitude

### Community 133 - "_FakeClient"
Cohesion: 0.40
Nodes (3): str, _FakeClient, The ``"fake-client"`` sentinel every ``build_pve_client`` mock in this file…

### Community 135 - "_mapper"
Cohesion: 0.14
Nodes (12): _mapper(), Any, BaseException, _Raise, X-09: `manifest.json`'s `counts.dropped_records` is documented as counting…, A task's ``id`` is the vmid its UPID embeds. It used to be copied raw, leaving…, _tasks_by_kind(), test_anonymize_cluster_tasks_maps_the_task_id_with_the_upid() (+4 more)

### Community 148 - "test_enforce_format.py"
Cohesion: 0.10
Nodes (53): needs_cbc, disk_size_on(), qcow2_lvm_allocation_bytes(), Upper bound on the LV ``alloc_image`` creates for a ``qcow2`` volume of…, Section 5.3.2's ``phi(d, s)``: the format ``disk`` would have on ``storage``.…, Section 5.3.2's ``z_{d,s}``, in bytes: what ``disk`` occupies when placed on…, target_format(), _crowded_group() (+45 more)

### Community 155 - "Gates page"
Cohesion: 0.53
Nodes (6): Cooldowns not in gates, Drift gate, evaluate_group_gates, Gates page, last_load state, Reserve override gate

### Community 156 - "resolve_level"
Cohesion: 0.50
Nodes (5): Section 2.3's ladder: ``--quiet`` < default < ``-v`` < ``-vv``. ``--log-level``…, resolve_level(), parametrize, test_log_level_wins_over_both_verbose_and_quiet(), test_resolve_level_ladder()

### Community 158 - "proxmox-storage-drs"
Cohesion: 0.40
Nodes (4): Getting the tool, proxmox-storage-drs, The documents, The safety properties to rely on

### Community 159 - "VerifyMetricsReport"
Cohesion: 0.22
Nodes (8): _findings_to_json(), ``verify_metrics()``'s own finding text, and this module's own call log (built…, Bundle-safe rewrite of one ``verify_metrics()`` finding message. Returns…, _redact_finding_message(), _redact_free_text(), format_cross_metric_finding(), Builds :func:`_check_cross_metric_disk_consistency`'s one finding shape from a…, VerifyMetricsReport

### Community 160 - "Monitoring: the status file"
Cohesion: 0.40
Nodes (5): Freshness: why every run rewrites the file, Monitoring: the status file, What is in the file, What makes a run `OK`, `WARNING` or `CRITICAL`, Wiring it into Nagios/NRPE

### Community 162 - "test_manual_falls_back_when_man_exits_nonzero"
Cohesion: 0.40
Nodes (3): test_manual_falls_back_when_man_exits_nonzero(), test_manual_flag_uses_man_when_available(), fake_run()

### Community 163 - "_anonymized_config_dict"
Cohesion: 0.50
Nodes (4): _anonymize_exclude_disk_key(), _anonymized_config_dict(), Section 16.3's "the configuration in the bundle": credentials and endpoints…, ``"vmid:device"`` -- an ``exclude.disks`` entry (section 16.3), the same shape…

### Community 165 - "_FakeHttpsBackend"
Cohesion: 0.40
Nodes (3): _FakeHttpsBackend, _FakeProxmoxApiWithBackend, _FakeTicketAuth

### Community 166 - "loadmodel.py"
Cohesion: 0.08
Nodes (28): _blend_loads(), _combine_raw_values(), _combined_raw(), _fetch_all_raw_quantities(), _fetch_all_raw_quantity_series(), _is_metrics_expected_absent(), _issue_chunked_range_query(), _per_disk_lookup() (+20 more)

## Knowledge Gaps
- **222 isolated node(s):** `proxmox-storage-drs`, `run-with-system-python.sh script`, `build_paper.sh script`, `build_site.sh script`, `The safety properties to rely on` (+217 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1396 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **25 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Persistent state: state.json` connect `Persistent state: state.json` to `State`, `save_locked_state`, `cli.py`, `loadmodel.py`, `heuristic.py`, `LastBalance`, `Manual: Configuration reference`, `topology.py`, `execute.py`, `GroupLoad`, `Overview page`, `test_crashrecovery.py`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Why does `Manual: Configuration reference` connect `Manual: Configuration reference` to `Monitoring status file`, `drs.example.yaml (reference configuration)`, ``metrics` — Telegraf/InfluxDB name mapping`, `Configuration reference`, `Persistent state: state.json`, `Configuration page`, `Internals: CLI dispatch and logging`, `Internals: Building the disk/storage/group model`, `Internals: The heuristic solver`, `Manual: Reading plan`, `Safety properties, exit codes, and what this build actually does`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._
- **Why does `Group` connect `Group` to `MonkeyPatch`, `test_topology.py`, `Path`, `test_execute.py`, `evaluate_assignment`, `topology.py`, `GroupLoad`, `Disk`, `test_payback.py`, `ExecutionResult`, `test_enforce_format.py`, `test_optimize.py`, `ExecutionConfig`, `_compute_group_load`, `test_free_space_repair_fixture.py`, `cli.py`, `collect.py`, `loadmodel.py`, `make_storage`, `heuristic.py`, `order_moves`, `ObjectiveBreakdown`, `test_small_disks.py`, `_handle_apply`, `test_affinity_repair_fixture.py`, `capture_bundle`, `execute.py`, `_exec_group`, `MoveCost`, `group_average_fill`, `test_plan_after_and_payback_reflect_only_the_scheduled_moves_on_partial_deadlock`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._
- **Are the 199 inferred relationships involving `Group` (e.g. with `_accumulate_move_stats()` and `_apply_payback_gate()`) actually correct?**
  _`Group` has 199 INFERRED edges - model-reasoned connections that need verification._
- **Are the 94 inferred relationships involving `PveClient` (e.g. with `_apply_payback_gate()` and `_pve_client_for()`) actually correct?**
  _`PveClient` has 94 INFERRED edges - model-reasoned connections that need verification._
- **Are the 73 inferred relationships involving `Disk` (e.g. with `_fragmented_vms()` and `_pinned_disks()`) actually correct?**
  _`Disk` has 73 INFERRED edges - model-reasoned connections that need verification._
- **What connects `proxmox-storage-drs`, `run-with-system-python.sh script`, `build_paper.sh script` to the rest of the system?**
  _222 weakly-connected nodes found - possible documentation gaps or missing edges._