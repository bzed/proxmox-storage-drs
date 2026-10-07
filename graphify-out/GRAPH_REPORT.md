# Graph Report - proxmox-storage-drs  (2026-10-07)

## Corpus Check
- 116 files · ~323,345 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 21 file(s) not represented in the graph (top: (none) 12, .sha256 3, .conf 1)

## Summary
- 3962 nodes · 11517 edges · 176 communities (154 shown, 22 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 1705 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c6f1418d`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- MonkeyPatch
- build_topology
- _handle_apply
- generate_expected.py
- test_config.py
- Path
- Domain invariants (.agents)
- test_cli.py
- test_loadmodel.py
- test_metrics.py
- Storage
- run
- evaluate_assignment
- topology.py
- Configuration reference
- GroupLoad
- Disk
- test_payback.py
- ExecutionResult
- ._call
- test_optimize.py
- ResolvedConfig
- test_validate_corpus.py
- test_replay.py
- run_concurrent
- ScheduleResult
- PveClient
- test_anonymize.py
- drs.example.yaml (reference configuration)
- apply_forecast
- test_collect.py
- typing
- test_execute.py
- TimeWindow
- Monitoring status file
- load_state
- _anonymize_captured_prometheus
- format_bytes
- ExecutionConfig
- Engine pipeline: collect, join, gate, solve, cost, order, execute
- Manual: Configuration reference
- configure_logging
- build_fake_client
- schedule.py
- Packaging, dependencies and CI (.agents)
- Configuration and validation rules
- Payback rule and acceptance test
- make_config
- Overview page
- State
- test_documentation.py
- BundleError
- test_statusfile.py
- test_plan_reports_an_unfixable_shortfall_and_the_pins_that_block_it
- filter_allowed_fields
- `proxmox` — the cluster API connection
- heuristic.py
- build_client
- Execute page
- Proxmox Storage DRS Implementation Plan
- Path
- PveApiError
- config.py
- crashrecovery.py
- LastBalance
- test_affinity_repair_fixture.py
- test_small_disks.py
- move_disk (drive-mirror, delete=1)
- Reading `apply`
- Any
- Where the numbers come from, and how a transport loses them
- capture_bundle
- test_state.py
- build_node_selector
- state.py
- build_rate_promql
- test_topology.py
- Any
- execute.py
- WindowConfig
- `metrics` — Telegraf/InfluxDB name mapping
- order_moves
- metrics.py
- cli.py
- pve-storage-drs.1.md
- test_forecast.py
- `exclude` — what DRS never touches
- PrometheusClient
- Internals: CLI dispatch and logging
- _plan_group
- PrometheusClient
- Internals: The heuristic solver
- forecast_group
- Group
- Load model (average in-flight I/O)
- anonymize.py
- disk_factors
- _build_api
- fakes.py
- pytest
- FakeClock
- PaybackResult
- _expand_group
- test_plan_gate_also_reflects_real_drift_history_from_state_json
- case_for
- Persistent state: state.json
- units.py
- Lexicographic solve (reserve first, then balance)
- Transient invariant
- AGENTS.md working agreement
- C5 Capacity, snapshot reserve and free space
- Mapper
- Installation and requirements
- check_paper_log.py
- PrometheusConfig
- `execution` — how (and whether) moves actually happen
- fragmentation
- json_safe
- Assignment
- payback
- collect.py
- ReplayPveClient
- empty_state
- Internals: Building the disk/storage/group model
- Logging: what lands where, and what an unattended run records
- FakePrometheusSession
- _fetch_raw_quantity_series
- Fixture
- Diagnostic bundles: `collect-testdata` and `--replay`
- filters.lua
- MetricsError
- filter_vm_config_fields
- _one_vm_two_storage_cluster
- _exec_group
- Load model page
- Safety properties, exit codes, and what this build actually does
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
- _client_with_fake_time
- Configuration page
- disk_state_key
- Payback page
- 28-apply.md
- Gates page
- proxmox-storage-drs
- `gates` — deciding whether to act at all
- resolve_level
- `load_weights` — combining read/write and time/ops/bytes
- Decision trail events
- Monitoring: the status file
- decimate_to_configured_step
- DrsError
- loadmodel.py
- build_site.sh
- _mapper
- _FakeClient
- test_logging_setup.py
- test_a_crash_leaves_a_critical_status_file_and_still_raises
- .outage_tolerance
- test_build_topology_content_queried_from_vm_own_node_not_storage_active_node
- proxmox_storage_drs

## God Nodes (most connected - your core abstractions)
1. `Group` - 214 edges
2. `PveClient` - 125 edges
3. `Disk` - 93 edges
4. `run()` - 84 edges
5. `write_config()` - 83 edges
6. `make_move()` - 81 edges
7. `client_with()` - 79 edges
8. `Proxmox Storage DRS Implementation Plan` - 78 edges
9. `build_topology()` - 77 edges
10. `PrometheusClient` - 74 edges

## Surprising Connections (you probably didn't know these)
- `The `Group <name> → ACT`/`NO ACTION` line` --references--> `GroupLoad`  [INFERRED]
  docs/manual/25-show-load-and-verify-storages.md → src/proxmox_storage_drs/loadmodel.py
- `What is in the file` --references--> `duration()`  [INFERRED]
  docs/manual/36-monitoring.md → tests/fixtures/generate_expected.py
- `The `objective:` line` --references--> `ObjectiveBreakdown`  [INFERRED]
  docs/manual/29-explain.md → src/proxmox_storage_drs/heuristic.py
- `What `plan` does not yet do` --references--> `evaluate_assignment()`  [INFERRED]
  docs/manual/27-plan.md → src/proxmox_storage_drs/heuristic.py
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

## Communities (176 total, 22 thin omitted)

### Community 0 - "MonkeyPatch"
Cohesion: 0.05
Nodes (98): _fake_build_topology(), _fake_reconcile_inflight(), _patch_show_load_deps(), _patch_show_load_forecast(), CaptureFixture, Exception, MonkeyPatch, Every `apply` test here uses `build_pve_client`'s "fake-client" string stand-… (+90 more)

### Community 1 - "build_topology"
Cohesion: 0.16
Nodes (39): The cluster topology could not be built from the API responses. See…, TopologyError, build_topology(), datetime, Build the whole cluster's :class:`Topology` for this run. One pass: every read…, _cluster_client(), make_config(), LogCaptureFixture (+31 more)

### Community 2 - "_handle_apply"
Cohesion: 0.11
Nodes (27): Mutable state box narrow exception to functional style, Startup scan folds excluded vmids before planning, _apply_exit_code(), _apply_payback_gate(), _GroupPlan, _handle_apply(), _InflightStateBox, _make_inflight_callbacks() (+19 more)

### Community 3 - "generate_expected.py"
Cohesion: 0.16
Nodes (17): itertools, all_assignments(), best_lexicographic(), big_m_agreement_threshold(), Deadlock, eligible_storages(), load_fixture(), main() (+9 more)

### Community 4 - "test_config.py"
Cohesion: 0.09
Nodes (73): ConfigError, The configuration file is missing, unreadable or fails validation. See…, minimal_config_dict(), Any, parametrize, Path, skipif, The smallest config that passes structural + semantic validation. (+65 more)

### Community 5 - "Path"
Cohesion: 0.07
Nodes (72): The whole cluster's worth of groups, as seen by this run. By the time anything…, Topology, _fake_breakdown(), _fragmented_group(), _make_group_plan(), _moved_outcome(), _one_disk_group(), _one_disk_group_load() (+64 more)

### Community 6 - "Domain invariants (.agents)"
Cohesion: 0.09
Nodes (22): Config knob entry: type, default, unit, extremes, interactions, Tests keeping docs honest (help covers options, manual covers config), --help generated from argparse definitions, no hardcoded defaults, Internals pages: question first, name modules, explain why, ASCII diagrams, Manpage skeleton with complete OPTIONS, config/drs.example.yaml as documentation that parses, Change behaviour and documentation in the same commit, PDF is a build product; fix text not LaTeX (+14 more)

### Community 7 - "test_cli.py"
Cohesion: 0.03
Nodes (66): load_config(), Resolve, read, parse and validate the configuration. See section 11 for…, _gate(), _no_move_schedule(), _NodeNamesClient, _outcome(), Any, LogCaptureFixture (+58 more)

### Community 8 - "test_loadmodel.py"
Cohesion: 0.15
Nodes (46): LoadWeights, _blend_loads(), compute_group_load(), Section 4's normalize-then-weight-then-rescale blend, given every key's own…, Compute one group's :class:`GroupLoad` for this run. Section 4.…, _client(), full_coverage(), make_disk() (+38 more)

### Community 9 - "test_metrics.py"
Cohesion: 0.09
Nodes (37): parse_disk_range_series(), The ``query_range`` counterpart to :func:`parse_disk_series`: turns a…, _all_metric_names(), FakeResponse, FakeSession, Any, A 14-day lookback is 1209600s -- ``f"{1209600:g}s"`` renders as…, Prometheus client, PromQL builders and verify-metrics. No test here talks to a… (+29 more)

### Community 10 - "Storage"
Cohesion: 0.09
Nodes (42): compute_reserve_status(), _current_storage(), largest_disk_bytes(), managed_used_bytes(), (C4)/(C5) evaluated for one storage at the assignment ``storage_of`` encodes.…, The snapshot-reserve constraint. See IMPLEMENTATION_PLAN.md section 5.3…, ``size_bytes`` rounded *up* to the next whole MiB, in bytes. Up, never to…, Z_s: the largest disk on ``storage_id`` under ``storage_of``, 0 if none (C4).… (+34 more)

### Community 11 - "run"
Cohesion: 0.09
Nodes (62): client_with(), default_group(), make_move(), parametrize, A PVE API error while re-reading the target refuses the move and fails the run…, Section 13: `state.json` must learn about a UPID *before* this function goes on…, Not only the happy path -- a `move_disk` task that itself fails still finished…, `dry-run` never calls `move_disk` at all -- the callbacks must simply never… (+54 more)

### Community 12 - "evaluate_assignment"
Cohesion: 0.08
Nodes (63): compute_vm_weights(), evaluate_assignment(), Section 5.5 step 1: "seed with the current assignment (not from scratch -- we…, Section 5.4's `w_v = max(1, l_v / l_bar)` -- the per-VM weight that scales…, Section 5.4's objective for one candidate ``assignment``.…, Section 5.5's four-step heuristic (minus "polish"; see the module docstring),…, run_heuristic(), seed_assignment() (+55 more)

### Community 13 - "topology.py"
Cohesion: 0.11
Nodes (30): concurrent_futures, The regular expression text of a pattern entry, its two ``/`` delimiters…, storage_pattern_text(), _build_storages(), _ClusterData, content_item_size(), _default_format(), _disk_snapshot_or_orphan_reason() (+22 more)

### Community 14 - "Configuration reference"
Cohesion: 0.05
Nodes (43): Configuration reference, `forecast.holt_winters.seasonal`, `forecast.holt_winters.seasonal_periods`, `forecast.holt_winters.trend`, forecast.model (quantile, holt_winters), `forecast` — placing disks for the load they will have, `free_space.hard`, `free_space` — keep N bytes (or N%) free on top of the snapshot reserve (+35 more)

### Community 15 - "GroupLoad"
Cohesion: 0.08
Nodes (59): GatesConfig, _capacity_spread(), evaluate_group_gates(), _l1_drift(), Section 6, applied in the order it lists: reserve override, then the capacity…, Section 6: decide whether to act on a group at all, before the solver runs.…, ``(‖ℓ_last‖₁, ‖ℓ_now − ℓ_last‖₁)`` over the **union** of disk keys present in…, Section 5.3 (C7)'s `(max_s b_s - min_s b_s) / b_bar`, or ``None`` when the gate… (+51 more)

### Community 16 - "Disk"
Cohesion: 0.08
Nodes (52): ObjectiveConfig, group_average_utilization(), `u* = (Sum_d l_d) / (Sum_s c_s)` (C6) -- a constant under any reassignment of…, _cbc_capacity_spread_term(), _cbc_feasibility_constraints(), _cbc_objective_terms(), _cbc_small_disks_follow_their_vm(), _cbc_storage_fill() (+44 more)

### Community 17 - "test_payback.py"
Cohesion: 0.09
Nodes (55): MigrationConfig, compute_benefit_load_seconds(), compute_move_cost(), evaluate_plan_payback(), Section 7.1's cost for one scheduled move. Only ``source`` is needed (not the…, Section 7.2: ``benefit = (alpha*(E_before - E_after) + delta*(F_before -…, Section 7.3: the aggregate acceptance test over a whole plan, plus the hard…, move() (+47 more)

### Community 18 - "ExecutionResult"
Cohesion: 0.08
Nodes (57): ExecutionResult, One group's ``execute_plan()`` call. ``stopped_early`` is true for any reason…, _balanced_apply_group_load(), _balanced_apply_topology(), _check_statusfile(), _monitored_config(), _patch_plan_deps(), Two evenly-sized, evenly-loaded disks on one storage, none on the other, no… (+49 more)

### Community 19 - "._call"
Cohesion: 0.08
Nodes (16): Any, :meth:`_call_once`, retried while the API is unreachable. Only inside…, ``GET /cluster/resources?type=vm``: VM inventory., ``GET /cluster/tasks``: recent/active tasks across **every** node -- the one…, ``GET /cluster/resources?type=storage``: storage inventory., ``GET /nodes``: every node in the cluster, by name. Section 3.4's node-scoping…, ``GET /version``: the running PVE's own version string (section 16.1/16.3's…, ``GET /storage``: every storage's full config, including ``saferemove``.… (+8 more)

### Community 20 - "test_optimize.py"
Cohesion: 0.09
Nodes (54): cbc_available(), make_disk(), make_storage(), LogCaptureFixture, MonkeyPatch, parametrize, Deliberately *not* parametrized over the skip-guarded `BACKENDS` list above --…, Section 5.4's D^big: at beta_move_count=1.0, moving `201:efidisk0` (1 MiB) to… (+46 more)

### Community 21 - "ResolvedConfig"
Cohesion: 0.13
Nodes (33): Namespace, _dump_report_json(), _filter_groups(), _handle_collect_testdata(), _handle_explain(), _handle_plan(), _handle_show_load(), _handle_verify_metrics() (+25 more)

### Community 22 - "test_validate_corpus.py"
Cohesion: 0.09
Nodes (47): tests_corpus, tests_corpus_validate_corpus, _case(), _invariant_inputs(), MonkeyPatch, needs_full_checkout, parametrize, Path (+39 more)

### Community 23 - "test_replay.py"
Cohesion: 0.15
Nodes (28): _config_from_bundle(), _free_space_pairs(), MonkeyPatch, Path, AH-06: a live ``free_space`` config is collected as the resolved per-storage…, Section 16.5's one deliberate exception: a bundle captured before section 3.8…, replay.py: serving a diagnostic bundle through the pve.py/metrics.py interfaces…, X-10: `.tar.gz` (write_tarball()'s own transport form, section 16.1) is not a… (+20 more)

### Community 24 - "run_concurrent"
Cohesion: 0.10
Nodes (35): concurrent_client_with(), datetime, The defining property of concurrency: `move_disk` for the second move is issued…, Each move's own UPID reaches both callbacks correctly attributed --…, Two otherwise-independent moves landing on the *same* target: even with…, Section 8.1's generalized invariant, live: san-c has only 2 TiB of headroom…, A leftover 1 TiB volume of VM 201 already on san-c when 201 launched (an orphan…, The deliberate simplification documented in `_execute_concurrent()`'s own… (+27 more)

### Community 25 - "ScheduleResult"
Cohesion: 0.11
Nodes (31): _load_per_tib(), _pinned_disks(), Section 7.3's advisory ``ell/z`` ratio -- ``0.0`` for a zero-size disk rather…, Section 5.3's "report any residual `r_s > 0` prominently as an unfixable…, The residual shortfall of ``final_breakdown`` (the assignment the plan actually…, Why ``plan``/``apply`` show a gate verdict of ACT and then no move. The gate…, One group's worth of ``_render_plan_human()``'s report -- shared with…, One group's worth of ``_render_plan_json()``'s report -- shared with… (+23 more)

### Community 26 - "PveClient"
Cohesion: 0.09
Nodes (54): Section 13's startup scan. Returns the vmids to exclude from this run's…, reconcile_inflight(), PveClient, One method per IMPLEMENTATION_PLAN.md section 3.5 endpoint. ``api`` is typed…, fake_api(), BaseException, The same in-flight move already recorded in state.json also shows up in the…, Startup crash/two-instance recovery. See proxmox_storage_drs/crashrecovery.py. (+46 more)

### Community 27 - "test_anonymize.py"
Cohesion: 0.06
Nodes (43): make_mapper(), MonkeyPatch, parametrize, Path, A node and a storage that happen to share a name must not collide., Section 16.3: 'the result never depends on iteration order'., Force two different vmids to hash to the same base slot and confirm both still…, X-09: `vmid`'s own linear probing makes a collision impossible, but nothing did… (+35 more)

### Community 28 - "drs.example.yaml (reference configuration)"
Cohesion: 0.06
Nodes (40): drs.example.yaml (reference configuration), cli.py backend dispatch: auto cascades, explicit falls back, exclude rules, gates (drift, imbalance, capacity spread, cooldowns), load_weights, `migration.account_saferemove_wipe`, `migration.assume_thick_provisioning`, `migration.bwlimit_bytes_per_sec` (+32 more)

### Community 29 - "apply_forecast"
Cohesion: 0.31
Nodes (9): _aggregate_storages(), apply_forecast(), Each storage's ``L_s``/``u_s`` from its disks' ``l_d``, and the group's ``u*``…, Section 12.1 point 2: scale each disk's ``l_d`` by its forecast factor ``f_d /…, _forecast_fixture(), test_apply_forecast_leaves_idle_and_no_series_matched_alone(), test_apply_forecast_never_scales_a_flagged_disk_even_if_a_factor_is_given(), test_apply_forecast_scales_only_disks_with_a_factor_and_rebuilds_the_totals() (+1 more)

### Community 30 - "test_collect.py"
Cohesion: 0.09
Nodes (38): capture(), Path, X-08: section 16.1's manifest line ("schema, versions, what was captured...")…, X-08: section 16.3 promises the manifest "flags" a non-node-shaped…, Z-03: `resolve_node_selector()`'s tier-1 precedence used to win on *both* sides…, A live capture against the dev cluster found the previous implementation's bug…, verify_metrics() never carries a node selector at all -- nothing to rewrite,…, Even when the configured model is ``quantile``, the bundle is captured with… (+30 more)

### Community 31 - "typing"
Cohesion: 0.10
Nodes (32): dataclasses, executed_assignment(), Assignment, Section 7.3: "what it will really run" -- ``final_assignment``…, Section 7.3's revert test, one verdict per scheduled move in ``order``: would…, Migration cost and the payback acceptance test. See IMPLEMENTATION_PLAN.md…, repair_markers(), `Σ_s r_s` at the assignment ``storage_of`` encodes -- section 7.3's outcome… (+24 more)

### Community 32 - "test_execute.py"
Cohesion: 0.09
Nodes (27): A `san-c` content responder plus a `move_disk` responder for 201. The listing…, 201's mirror target is already *listed* on san-c at its full 1 TiB by the time…, Between different storage types, or from thin to thick, `move_disk` allocates…, The match stays narrow: a same-VM volume that appeared after launch but has…, The exclusion is narrow: only 201's *own* mirror target (same VM, the disk's…, Executing a plan. See proxmox_storage_drs/execute.py. No test here talks to a…, Between different storage types the target is allocated at the disk line's…, The same 2 TiB config `size=` and the same 4.5 TiB already on the target, but… (+19 more)

### Community 33 - "TimeWindow"
Cohesion: 0.15
Nodes (34): date, TimeWindow, current_deadline(), _day_name(), is_window_active(), _parse_hhmm(), datetime, ``execution.time_windows``: when ``auto`` mode may execute moves. See… (+26 more)

### Community 34 - "Monitoring status file"
Cohesion: 0.11
Nodes (25): GitHub Actions and Salsa GitLab CI pipelines, Dry-run is the default, Release procedure (version bump, changelog, debian/ tag, graphify commit), Monitoring status file (statusfile.py), /etc/pve/drs.yaml on pmxcfs, Installation and requirements (manual), state.json (node-local state), `monitoring` — telling your monitoring system what the last run did (+17 more)

### Community 35 - "load_state"
Cohesion: 0.15
Nodes (28): flock is the lock; JSON lock field is only a label, acquire_lock(), load_state(), LockHandle, LockInfo, Best-effort read of ``path``. See the module docstring: a missing file is the…, Opaque -- pass to :func:`release_lock`. The open file descriptor is what…, Section 11.2's advisory lock: ``fcntl.flock(LOCK_EX | LOCK_NB)`` on ``path``… (+20 more)

### Community 36 - "_anonymize_captured_prometheus"
Cohesion: 0.11
Nodes (19): _anonymize_captured_prometheus(), _anonymize_prometheus_series(), _anonymize_query_text(), _label_kind_for(), _label_value_for(), _parse_step_param(), Rewrites captured PromQL text so it matches what a ``--replay`` run…, Turns every ``(path, params, raw response)`` :class:`RecordingPrometheusClient`… (+11 more)

### Community 37 - "format_bytes"
Cohesion: 0.11
Nodes (27): _make_confirm_move_interactively(), confirm(), _pin_action_hint(), The economic test (``aggregate_ok``) and the hard per-move duration rule…, The human form of :class:`_UnfixableShortfall` -- printed whether or not the…, Section 9.5's per-pin action hint: what to actually do about a pin, distinct…, Only called when the gate decided to ACT but the *final* assignment moves…, ``None`` for a group ``apply`` never got as far as executing (a load error, or… (+19 more)

### Community 38 - "ExecutionConfig"
Cohesion: 0.15
Nodes (29): ExecutionConfig, SourceReleaseConfig, _group_with_types(), make_disk(), make_storage(), Section 9.3: a source_release timeout "does not fail the run: mark the storage…, Same as above, except the second move's *target* -- not source -- is the…, Section 9.3 point 3: PVE's own `saferemove_throughput` (already read live off… (+21 more)

### Community 39 - "Engine pipeline: collect, join, gate, solve, cost, order, execute"
Cohesion: 0.18
Nodes (14): Engine pipeline: collect, join, gate, solve, cost, order, execute, (C6) Load spread, Capacity spread gate (default 0.25), Move completion criterion stronger than task success, Per-disk and per-storage cooldowns, Deadlock and staging, Gating (drift, imbalance, capacity gates, cooldowns, reserve override), Imbalance gate (default 0.20) (+6 more)

### Community 40 - "Manual: Configuration reference"
Cohesion: 0.19
Nodes (14): .agents/ index, Python style (.agents), black vs flake8 disagreements (E203, W503, E704), One implementation of every rule (MILP and heuristic share), Units in names, Manual: Configuration reference, If it fails, Running it (+6 more)

### Community 41 - "configure_logging"
Cohesion: 0.13
Nodes (24): configure_logging(), floor_for_command(), The mandatory ``INFO`` floor of section 2.3, or ``None``. A run that can change…, Install this run's log handler. Called once, from ``main()``. ``floor`` is…, CaptureFixture, INFO at a terminal is the narrative the operator asked for; prefixing every…, `propagate = False` on the package logger would hide every record from pytest's…, One handler, on root, with the package logger carrying only a level: a second… (+16 more)

### Community 42 - "build_fake_client"
Cohesion: 0.18
Nodes (20): build_fake_client(), _content(), _one_disk_cluster(), Any, Section 5.3 (C8): VM 301's only disk in this group is a 528 KiB efidisk0 (its…, Section 3.7 item 3: the operator must learn *which* volume blocks the VM. The…, A storage plugin can list a volid with no `size` key at all -- seen on a live…, The same content-listing gap, for a foreign (unreferenced) volume counted… (+12 more)

### Community 43 - "schedule.py"
Cohesion: 0.08
Nodes (46): IMPLEMENTATION_PLAN.md section 8.1's transient invariant, generalized to an…, transient_charge_ok(), order_moves(), _pending_moves(), Assignment, Section 8.1's transient invariant, called with the single-move set ``{disk}``…, Section 8.2 priority 1: is ``disk``'s *current* (in ``state``) storage…, Section 8.2's scheduling loop for one group. ``target_assignment`` is normally… (+38 more)

### Community 44 - "Packaging, dependencies and CI (.agents)"
Cohesion: 0.16
Nodes (14): Git workflow (.agents), Branch first, decided from the task, Merge --no-ff on green make check, Release process (version, changelog, tag, graphify), Packaging, dependencies and CI (.agents), Autopkgtest as the dependency test, coinor-cbc and python3-pulp as Depends, Debian-first dependency policy (trixie) (+6 more)

### Community 45 - "Configuration and validation rules"
Cohesion: 0.22
Nodes (10): Configuration and validation rules, Failure handling (orphans, partial plan, supervision loss), Companion fixture free-space repair mandate, free_space configuration (soft/hard floors), Global command-line options, Mode override logging (escalation is a warning), Requirements traceability, state.json (hysteresis state) (+2 more)

### Community 46 - "Payback rule and acceptance test"
Cohesion: 0.14
Nodes (22): Affinity repair under payback fixture, beta term: number of migrations, bwlimit is the only throttle (saturation guard removed), C7 Capacity-spread linearization, Data spread as tunable delta preference, delta term: data spread / failure risk, Even data spread as second priority, Companion fixture affinity repair (+14 more)

### Community 47 - "make_config"
Cohesion: 0.12
Nodes (28): make_config(), make_prometheus_client(), make_pve_client(), --no-series must skip the big, per-group superset range captures -- it does not…, Y-06: the manifest's version fields are machine-generated provenance, not free…, X-09: the printed query count used to treat a multi-day range as one range…, Z-05: a live capture stores every range series at…, Section 3.8/16.3: a real pending edit on the VM's own disk survives as the… (+20 more)

### Community 48 - "Overview page"
Cohesion: 0.29
Nodes (12): config.py depends on forecast.py, Module layout, Overview page, Seven-stage pipeline, Two solver backends, Backtest gate, Drift baseline is effective load, Forecast provenance report (+4 more)

### Community 49 - "State"
Cohesion: 0.16
Nodes (20): Section 11.2: ``last_balance``/cooldowns are "updated only after a run that…, _record_executed_moves(), Cooldowns, _parse_state_text(), Any, Raises on any shape this module does not recognize -- the caller…, The tolerant-parse half of :func:`load_state`, factored out so…, Pure: merges new disk/storage cooldown timestamps into ``state``, keyed exactly… (+12 more)

### Community 50 - "test_documentation.py"
Cohesion: 0.14
Nodes (26): importlib_resources, _flatten_schema_keys(), _load_schema(), _manpage_source_text(), _manual_documented_keys(), Any, needs_full_checkout, parametrize (+18 more)

### Community 51 - "BundleError"
Cohesion: 0.08
Nodes (30): hash_label_name(), hash_query_text(), The cache key both this module (writing) and ``replay.py`` (reading) derive a…, BundleError, ExecutionError, RangeStepMismatch, ``--replay`` found the requested range query, but at a different step than this…, Exception hierarchy for the project. Every error the tool can raise… (+22 more)

### Community 52 - "test_statusfile.py"
Cohesion: 0.07
Nodes (54): CompletedProcess, datetime, `report`, `report.warn_pinned_load_fraction`, needs_plugin, os, Storage DRS for Proxmox VE 9.2. Balances disk I/O load across configurable…, build_run_status() (+46 more)

### Community 53 - "test_plan_reports_an_unfixable_shortfall_and_the_pins_that_block_it"
Cohesion: 0.40
Nodes (5): _all_pinned_sample_topology(), parametrize, `_sample_topology()` with its one movable disk pinned too: san-a violates (C5)…, Section 5.3/9.5: a residual `r_s > 0` is reported prominently, with the byte…, test_plan_reports_an_unfixable_shortfall_and_the_pins_that_block_it()

### Community 54 - "filter_allowed_fields"
Cohesion: 0.15
Nodes (19): filter_allowed_fields(), Drop every key of ``obj`` not in ``allowed``. The one primitive both the…, The one meaningful value a snapshot ``name`` field can carry is the literal…, sanitize_snapshot_name(), _anonymize_cluster_tasks(), _anonymize_node_list(), _anonymize_storage_content(), _anonymize_storage_definitions() (+11 more)

### Community 55 - "`proxmox` — the cluster API connection"
Cohesion: 0.20
Nodes (10): `proxmox.auth.password`, `proxmox.auth.token_secret`, `proxmox.auth.username`, `proxmox.ca_file`, `proxmox.host`, `proxmox.port`, `proxmox.read_workers`, `proxmox` — the cluster API connection (+2 more)

### Community 56 - "heuristic.py"
Cohesion: 0.11
Nodes (27): Disk-cooldown pin is not exempted for reserve repair, _RepairCandidate, _best_of(), _best_repair_candidate(), trial_storage_of(), best_single_disk_alternative(), _descend(), storage_of() (+19 more)

### Community 57 - "build_client"
Cohesion: 0.09
Nodes (29): The Proxmox VE API client, API token permission is intersection with owner, Best-effort ticket refresh tightening, build_client assembles auth once, bwlimit bytes/s to KiB/s conversion only in move_disk, Single reauthenticate-and-retry in _call, storage_content silently empty without Datastore.Allocate, storage_definitions uses the list form GET /storage (+21 more)

### Community 58 - "Execute page"
Cohesion: 0.36
Nodes (10): Auto mode time window, Concurrent execution, Execute page, execute_plan live revalidation, Four-condition done, Injectable Clock, Live transient check provisioned, Orphans reported never deleted (+2 more)

### Community 59 - "Proxmox Storage DRS Implementation Plan"
Cohesion: 0.11
Nodes (30): Anonymization allowlist, never denylist, Migrations throttled by bwlimit only, tests/corpus and scrub audit, Datastore.Allocate needed for storage content listing, Dependencies come from Debian (trixie), Diagnostic bundles (collect-testdata), Disk identity join (vmid, device), Proxmox Storage DRS Implementation Plan (+22 more)

### Community 60 - "Path"
Cohesion: 0.29
Nodes (12): _lvm_def(), Any, Path, test_a_format_the_storage_type_cannot_hold_is_refused(), test_a_literal_entry_can_set_its_own_value(), test_a_pattern_matching_a_storage_that_cannot_hold_it_names_that_storage(), test_config_has_no_global_enforce_format(), test_config_parses_enforce_format() (+4 more)

### Community 61 - "PveApiError"
Cohesion: 0.09
Nodes (24): contextlib, proxmoxer, RequestException, requests, ResourceException, PveApiError, PveUnreachableError, The Proxmox VE API returned an error or an unusable response. See… (+16 more)

### Community 62 - "config.py"
Cohesion: 0.07
Nodes (55): jsonschema, ruamel_yaml, ruamel_yaml_error, _build_config(), _check_connection_config(), _check_forecast_window(), _check_group_size(), _check_group_storage_membership() (+47 more)

### Community 63 - "crashrecovery.py"
Cohesion: 0.14
Nodes (24): Crash and two-instance recovery: crashrecovery.py, cluster/tasks vs task_status conventions differ, parse_upid PVE UPID grammar confirmed live, reconcile_inflight: recorded UPIDs plus foreign scan, Two failure modes, one in-flight UPID mechanism, AuthConfig, expected_task_user(), parse_upid() (+16 more)

### Community 64 - "LastBalance"
Cohesion: 0.15
Nodes (16): LastBalance, load_vector_for_group(), now_iso(), ``at`` is ``None`` before any run has ever executed a migration -- distinct…, This group's slice of ``last_balance.load_vector``, re-keyed from…, Pure: a new :class:`State` with ``group_name``'s slice of…, UTC, second precision, ``Z`` suffix -- exactly section 11.2's own example…, with_recorded_balance() (+8 more)

### Community 65 - "test_affinity_repair_fixture.py"
Cohesion: 0.29
Nodes (11): _affinity_repair_group(), _loads(), _make_disk(), _make_storage(), parametrize, tests/fixtures/affinity-repair.yaml, built as real topology objects., The full pipeline -- solve, order, cost, benefit, accept -- exactly reproducing…, IMPLEMENTATION_PLAN.md section 14.7's fixture, exercised through the real… (+3 more)

### Community 66 - "test_small_disks.py"
Cohesion: 0.14
Nodes (27): _follows(), Section 5.3 (C8): a small disk ends a plan either where it is now, or on a…, (C8) for every small disk of ``group`` at the assignment ``storage_of`` encodes…, small_disk_placement_ok(), small_disks_follow_their_vm(), current(), disk(), efi_repair_group() (+19 more)

### Community 67 - "move_disk (drive-mirror, delete=1)"
Cohesion: 0.13
Nodes (21): approximate-size fallback for qcow2-on-LVM volumes, Mandatory INFO audit floor for confirm/auto runs, (C2) Eligibility via variable fixing, Errors are not mismatches, Structured log event catalogue, Execution modes dry-run, confirm, auto, Logging policy (two audiences, levels, audit floor), Which disks can move online (all buses, efidisk0, tpmstate0, unused) (+13 more)

### Community 68 - "Reading `apply`"
Cohesion: 0.14
Nodes (13): Concurrent execution, Crash and two-instance recovery, Failure and `abort_on_failure`, `--json`, Reading `apply`, Reading `auto` mode, `state.json`: what a real run actually changes, The `[y]es/[n]o skip/[a]ll remaining/[q]uit` prompt (+5 more)

### Community 69 - "Any"
Cohesion: 0.24
Nodes (5): _guarded(), Any, Run ``fn()``, recording its outcome in ``log``. Returns ``None`` (and records…, Wraps a real, already-authenticated :class:`PveClient` and records every call's…, RecordingPveClient

### Community 70 - "Where the numbers come from, and how a transport loses them"
Cohesion: 0.10
Nodes (20): A reference implementation that is well tested, gigapipe with ClickHouse (reference backend), PVE InfluxDB external metric server, instance label collision, OpenTelemetry metric server rejected, Other backends, RRD rejected as data source, Six per-disk blockstat counters (+12 more)

### Community 71 - "capture_bundle"
Cohesion: 0.20
Nodes (17): _build_manifest(), capture_bundle(), _capture_prometheus_files(), CaptureLog, CaptureOptions, _drive_group_series(), _drive_label_values(), _issue_range_chunks() (+9 more)

### Community 72 - "test_state.py"
Cohesion: 0.16
Nodes (16): cooldown_remaining_seconds(), _pid_alive(), Seconds left in ``key``'s cooldown -- ``0.0`` if nothing is recorded for it,…, Best-effort, used only to make a "still held" log message useful to an operator…, skipif, Persistent state at ``state.path``. See proxmox_storage_drs/state.py. Every…, A hand-edited or foreign timestamp must degrade to "not in cooldown", not raise…, pid 1 (init) always exists but is not ours to signal as a normal user --… (+8 more)

### Community 73 - "build_node_selector"
Cohesion: 0.22
Nodes (9): node_names uses GET /nodes, build_node_selector(), _escape_promql_regex_literal(), Escape one literal string for safe use inside a PromQL/RE2 ``=~`` alternation.…, Section 3.4's auto-derived node-scoping filter: ``<node_label>=~"n1|n2|..."``…, A node named `pve1.example.com` must match only that exact string in RE2 -- an…, test_build_node_selector_empty_list_is_none(), test_build_node_selector_escapes_dots_in_an_fqdn() (+1 more)

### Community 74 - "state.py"
Cohesion: 0.21
Nodes (14): Cooldown data stored here, interpreted by topology and heuristic, errno, fcntl, socket, _active_cooldowns(), active_disk_cooldowns(), active_storage_cooldowns(), _parse_iso() (+6 more)

### Community 75 - "build_rate_promql"
Cohesion: 0.29
Nodes (7): build_rate_promql(), The section 3.4 per-metric rate expression. ``sum by (vmid, device)…, Section 3.4: the selector goes *inside* `rate()`'s own vector selector, before…, test_build_rate_promql(), test_build_rate_promql_large_window_is_not_scientific_notation(), test_build_rate_promql_selector_none_is_unchanged_from_before(), test_build_rate_promql_with_a_selector_scopes_the_metric_itself()

### Community 76 - "test_topology.py"
Cohesion: 0.07
Nodes (38): vm_config returns pending value; vm_pending exposes both, _allowed_formats(), pending_disk_reasons(), _pin_reason(), PVE tags as returned by `cluster/resources`: semicolon-separated, with comma…, Section 5.3 (C2): the disk formats ``storage_type`` can hold. An unrecognised…, Section 3.8: which disk device keys in ``GET .../pending`` (section 3.5's…, Section 5.3 (C2)'s pin conditions, in the order the plan lists them -- the… (+30 more)

### Community 77 - "Any"
Cohesion: 0.15
Nodes (10): FakeResponse, FakeSession, Any, _RangeStepMismatchFakeClient, Answers `/api/v1/query` and `/api/v1/query_range` by the exact `query` param…, A ``range_query`` stand-in that returns caller-supplied data keyed by the exact…, A range wider than ``metrics.RANGE_QUERY_CHUNK_SECONDS`` (1d) is split into…, Like ``_StepAwareFakeClient``, but raises ``RangeStepMismatch`` (carrying its… (+2 more)

### Community 78 - "execute.py"
Cohesion: 0.05
Nodes (102): Write UPID to disk before the crash can happen, ExcludeConfig, _active_task_on_vm(), _advance_pending(), _auto_budget_stop_outcome(), _check_lock_once(), Clock, _confirm_decision() (+94 more)

### Community 79 - "WindowConfig"
Cohesion: 0.12
Nodes (30): MetricLabels, WindowConfig, _check_coverage(), compute_disk_coverage(), Section 3.3 step 5 / section 3.4's ``min_coverage`` rule: per-disk sample…, Section 3.3 step 5: report which disks fall below ``window.min_coverage``., _full_metrics_config(), A minimal, in-process stand-in for a live cluster's Prometheus endpoint, for… (+22 more)

### Community 80 - "`metrics` — Telegraf/InfluxDB name mapping"
Cohesion: 0.15
Nodes (13): `metrics.extra_selector`, `metrics.labels.device`, `metrics.labels.node`, `metrics.pvestatd_push_interval`, `metrics.rate_window`, `metrics.read_bytes`, `metrics.read_ops`, `metrics.read_time_ns` (+5 more)

### Community 81 - "order_moves"
Cohesion: 0.21
Nodes (14): Internals: Ordering the moves (schedule.py), cost_m tiny_disk_bytes, ScheduleResult.final_assignment, order_moves, Residual violation unexecutable, Schedule page, Transient invariant called with single-move set, Tiny disks (cost_m = 0) scheduled first (+6 more)

### Community 82 - "metrics.py"
Cohesion: 0.08
Nodes (41): MetricsConfig, _check_cross_metric_disk_consistency(), _check_device_label_collision(), _check_metric_names_exist(), _check_observed_spacing(), _check_sample_series(), _disk_keys_seen(), Finding (+33 more)

### Community 83 - "cli.py"
Cohesion: 0.09
Nodes (34): shutil, _compute_group_load(), _fragmented_vms(), _log_forecast(), _pinned_load_fraction(), Any, Assignment, Section 3.6: name the actual pinned disk(s) keeping one VM's disks spread… (+26 more)

### Community 84 - "pve-storage-drs.1.md"
Cohesion: 0.12
Nodes (15): AUTHOR, COLLECT-TESTDATA OPTIONS, COMMANDS, CONFIGURATION, COPYRIGHT, DESCRIPTION, ENVIRONMENT, EXIT STATUS (+7 more)

### Community 85 - "test_forecast.py"
Cohesion: 0.08
Nodes (45): math, random, ForecastConfig, HoltWintersConfig, holt_winters_quantile(), _quantile(), Holt-Winters load forecasting. See IMPLEMENTATION_PLAN.md sections 10 and 12.1.…, Linear-interpolation quantile, matching ``numpy.percentile``'s default.… (+37 more)

### Community 86 - "`exclude` — what DRS never touches"
Cohesion: 0.25
Nodes (8): `exclude.disks`, `exclude.include_unused_disks`, `exclude.running_only`, `exclude.skip_vms_with_snapshots`, `exclude.storages`, `exclude.tags`, `exclude.vmids`, `exclude` — what DRS never touches

### Community 87 - "PrometheusClient"
Cohesion: 0.25
Nodes (15): Gigapipe step workaround, Metrics page, Node-scoping selector, PrometheusClient, PromQL builders, Range query chunking, SessionLike protocol, verify_metrics six checks (+7 more)

### Community 88 - "Internals: CLI dispatch and logging"
Cohesion: 0.14
Nodes (14): Internals: CLI dispatch and logging, Global options on top-level parser, Command handlers dispatched via dict, JsonFormatter, Structured logs go to stderr, Log levels, mandatory floor, handler on root, --manual prefers man(1), falls back to in-tree markdown, --manual prefers man(1), falls back to plain text (+6 more)

### Community 89 - "_plan_group"
Cohesion: 0.09
Nodes (27): What this build actually implements, _log_gate_decision(), _log_load_digest(), _log_payback_verdict(), _log_plan_selected(), _objective_breakdown_json(), _plan_group(), ``(max_s u_s - min_s u_s) / u*`` -- gates.py's own imbalance formula (section… (+19 more)

### Community 90 - "PrometheusClient"
Cohesion: 0.10
Nodes (17): Protocol, parse_disk_series(), PrometheusClient, Any, The subset of ``requests.Response`` this module relies on., The subset of ``requests.Session`` this module relies on. A structural type…, Thin wrapper over the Prometheus HTTP API. See section 3.4/3.5. ``session`` is…, Issue one request and return the decoded ``data`` field. Typed ``Any`` rather… (+9 more)

### Community 91 - "Internals: The heuristic solver"
Cohesion: 0.12
Nodes (19): reserve.py: shared (C4)/(C5) evaluator, Internals: The heuristic solver, Descend explores swaps, evaluate_assignment(): objective separate from search, objective.spread_metric: two different quantities, Storage cooldown excludes destination, never source, Repair is unconditional, not weight-driven, w_v: kappa weighted by VM I/O, and D^big (+11 more)

### Community 92 - "forecast_group"
Cohesion: 0.15
Nodes (13): Collection, Backtest, forecast_group(), group_aggregate_series(), TimeSeries, One group's backtest: absolute error of each model's predicted p95 of ``[now-W,…, Sum every disk's own series into one group-aggregate series, at the union of…, Section 10.2's backtest, comparing against a baseline: fit on ``[now-2W,… (+5 more)

### Community 93 - "Group"
Cohesion: 0.12
Nodes (29): compute_disk_load_series(), TimeSeries, Section 4's `ℓ_d` blend, as a time series per disk over ``[now - range_seconds,…, Group, One storage group: section 5's independent optimization unit., _coverage_promql(), _group_selector(), _quantile_promql() (+21 more)

### Community 94 - "Load model (average in-flight I/O)"
Cohesion: 0.18
Nodes (14): Backtest gate: beat persistence baseline, Storage capability weight and utilization u_s, Drift gate (L1 norm, default 0.10), Forecast scales l_d by f_d/h_d, Holt-Winters forecasting and backtest gate, gigapipe step >= range workaround, Holt-Winters seasonal forecast (engine-side), Average in-flight I/O requests unit (+6 more)

### Community 95 - "anonymize.py"
Cohesion: 0.09
Nodes (22): hashlib, hmac, Allowlist-never-denylist anonymization, Diagnostic bundle directory format, collect-testdata diagnostic bundle, HMAC pseudonyms with persisted random salt, Corpus scrub audit, pathlib (+14 more)

### Community 96 - "disk_factors"
Cohesion: 0.11
Nodes (16): disk_factors(), ``f_d / h_d`` for every disk that has one: ``f_d`` the Holt-Winters forecast…, _factor_series(), _FixedForecast, MonkeyPatch, 96 hourly samples whose last 24 are ``window_values`` (repeated)., Patches ``holt_winters_quantile`` to a constant so the ratio is exact., test_disk_factors_is_forecast_over_observed_p95() (+8 more)

### Community 97 - "_build_api"
Cohesion: 0.15
Nodes (14): _apply_connection_pool_size(), _build_api(), Size the underlying ``requests`` session's connection pool to fit…, Construct one fresh, logged-in ``proxmoxer.ProxmoxAPI``. Split out of…, _FakeProxmoxApiWithSession, _FakeSession, Any, Confirmed live against a real multi-VM cluster: `requests`'s own default… (+6 more)

### Community 98 - "fakes.py"
Cohesion: 0.22
Nodes (5): FakeProxmoxResource, FakeQueryResponse, Any, Shared test doubles. Not collected by pytest (no ``test_`` prefix).…, Matches ``metrics._ResponseLike``: ``.status_code`` and ``.json()``.

### Community 99 - "pytest"
Cohesion: 0.18
Nodes (10): fixture, json, logging, pytest, ``auto`` and ``text`` -> ``"text"``; ``json`` -> ``"json"``. JSON is opt-in. It…, Logging policy. See IMPLEMENTATION_PLAN.md section 2.3. Every log record goes…, resolve_format(), Shared pytest fixtures. ``logging`` is process-global state, and… (+2 more)

### Community 100 - "FakeClock"
Cohesion: 0.09
Nodes (30): LocksConfig, FakeClock, log_messages(), LogCaptureFixture, Section 9.1: the pre-loop time-window check (above) only knows the answer as of…, REVIEW.md T-06's collateral bug: before the fix, this "skipped" outcome let the…, A move missing from `move_costs_by_key` is never refused for lack of an…, `execution.locks.on_timeout: skip` (the default): the locked head times out… (+22 more)

### Community 101 - "PaybackResult"
Cohesion: 0.22
Nodes (8): What `plan` does not yet do, Section 7.3's hard per-move duration rule (``rejected_moves``) rendered as…, _refused_move_outcomes(), PaybackResult, One plan's section 7.3 acceptance verdict. ``aggregate_ok`` (``benefit >=…, REVIEW.md R-05: an economic failure (benefit < ratio*cost) and a hard per-move…, test_render_plan_payback_lines_separates_economic_and_duration_failures(), make_result()

### Community 102 - "_expand_group"
Cohesion: 0.13
Nodes (22): GroupConfig, StorageConfig, _check_cross_group_uniqueness(), _expand_and_validate_groups(), _expand_group(), _fetch_cluster_data(), _free_space_level(), _free_space_source() (+14 more)

### Community 103 - "test_plan_gate_also_reflects_real_drift_history_from_state_json"
Cohesion: 0.24
Nodes (10): _imbalanced_group_load(), _no_reserve_violation_topology(), Two storages, generously sized -- unlike `_sample_topology()`, no (C4)/(C5)…, san-a all the load, san-b none -- imbalance is 200% of `u*`, far above the…, Baseline for the next test: with no `state.json` at all, `last_load` is `None`,…, The same fixture as above, except `state.json` now records a `last_balance`…, Same drift-suppression scenario as `show-load`'s, through `plan` -- the two…, test_plan_gate_also_reflects_real_drift_history_from_state_json() (+2 more)

### Community 104 - "case_for"
Cohesion: 0.21
Nodes (16): StorageState, best_big_m(), build(), capacity_spread(), case_for(), moves_of(), order_moves(), Any (+8 more)

### Community 105 - "Persistent state: state.json"
Cohesion: 0.15
Nodes (16): Persistent state: state.json, Drift history reaches the gates via last_balance, Inflight UPIDs written and read for crash recovery, Reading degrades, writing raises, Rename-detaches-flock bug and in-place locked write, staged_disks field unimplemented, on_finished(), on_started() (+8 more)

### Community 106 - "units.py"
Cohesion: 0.22
Nodes (12): re, parse_duration_seconds(), Unit parsing and formatting for durations and byte sizes. ``config.py`` is the…, Parse a duration into seconds. Accepts a bare number (seconds) or a string like…, parametrize, Unit parsing/formatting. See proxmox_storage_drs/units.py., test_format_bytes(), test_format_duration_seconds() (+4 more)

### Community 107 - "Lexicographic solve (reserve first, then balance)"
Cohesion: 0.13
Nodes (19): Disks with snapshots pinned, Testing (.agents), Acceptance fixtures and generate_expected.py, 85 percent coverage floor, No network, no real sleep, deterministic ties in tests, Codecov configuration, GitHub Actions Tests workflow, Big-M penalty P fallback (computed P_min) (+11 more)

### Community 108 - "Transient invariant"
Cohesion: 0.26
Nodes (12): Snapshot reserve never traded for balance, Higher bar for safety-critical modules, Three floors precedence f_s*Z_s > hard_s > soft_s, Generalized concurrent-move invariant / concurrency_ok, free_space requirement soft_s / hard_s, free-space repair fixture, free_space grammar (bytes, unit string, N%) and precedence, Plan-level repair exemption and revert test (+4 more)

### Community 109 - "AGENTS.md working agreement"
Cohesion: 0.16
Nodes (16): fc-tier1 / reserve-tradeoff acceptance fixtures, AGENTS.md working agreement, AGPL-3.0-or-later licence and SPDX headers, black/flake8 E203 W503 E704 ignores, Branch-first git workflow, 85% coverage floor, Documentation pipeline (make docs / docs-check), make check (+8 more)

### Community 110 - "C5 Capacity, snapshot reserve and free space"
Cohesion: 0.14
Nodes (22): autopkgtest runtime-dependency check, Autopkgtest install-with-only-Depends check, C1 Assignment, (C3) VM affinity linking, (C4) Largest-disk linearization Z_s, C5 Capacity, snapshot reserve and free space, (C8) Small disks follow their VM, CBC via PuLP MILP backend (+14 more)

### Community 111 - "Mapper"
Cohesion: 0.10
Nodes (18): `metrics.labels.vmid`, `proxmox.auth.token_id`, Mapper, pseudonym(), ``HMAC-SHA256(salt, kind || "\\0" || value)``, truncated to 8 hex chars.…, The stateful half of anonymization: one instance per bundle capture. ``vmid``…, The pseudonym for a vmid already passed to :meth:`register_vmids`. ``None`` for…, ``node-<8 hex>``, or ``node-<8hex>.<8hex>.invalid`` for an FQDN -- shape… (+10 more)

### Community 112 - "Installation and requirements"
Cohesion: 0.25
Nodes (8): First steps after installing, Installation and requirements, Installing the package, Running the timer on exactly one host, Setting up the PVE credential, What you need, Where the configuration is *not*, Where the configuration lives

### Community 113 - "check_paper_log.py"
Cohesion: 0.28
Nodes (8): argparse, sys, check(), _logical_lines(), main(), Path, Undo the log's hard wrap at 79 columns. TeX breaks log lines mid-message, which…, Fail the paper build on LaTeX problems that silently damage the PDF. `lualatex`…

### Community 114 - "PrometheusConfig"
Cohesion: 0.13
Nodes (22): PrometheusConfig, The step to actually send Prometheus for a ``rate()``-based ``query_range``…, safe_range_step_seconds(), The common, correctly-behaving-backend case: nothing to work around., This project's own default (metrics.step == metrics.rate_window == 300s) sits…, A real observed shape (a 7-day-capture config's metrics.step: 1h against the…, test_safe_range_step_seconds_is_a_no_op_below_the_rate_window(), test_safe_range_step_seconds_shrinks_when_equal_to_the_rate_window() (+14 more)

### Community 115 - "`execution` — how (and whether) moves actually happen"
Cohesion: 0.12
Nodes (16): `execution.abort_on_failure`, `execution` — how (and whether) moves actually happen, `execution.locks.on_timeout`, `execution.locks.poll_interval`, `execution.locks.task_retry_backoff`, `execution.locks.task_retry_limit`, `execution.locks.wait_timeout`, `execution.max_concurrent_migrations` (+8 more)

### Community 116 - "fragmentation"
Cohesion: 0.14
Nodes (16): Pin priority: _pin_reason(), best_single_disk_alternative(), cannot fully consolidate, -v data source: line, `measured load:`, `no moves made: ...` / `closest alternative: ...`, `pinned load ... ; best achievable spread given pins: ...`, `pinned (not movable this run):` (+8 more)

### Community 117 - "json_safe"
Cohesion: 0.22
Nodes (7): LogRecord, json_safe(), One human-readable line per record: ``LEVEL: message``. Deliberately not a…, Replace every non-finite float with ``None``, recursively. Python's JSON…, TextFormatter, test_json_safe_replaces_non_finite_floats_recursively(), test_text_formatter_includes_exception_info()

### Community 118 - "Assignment"
Cohesion: 0.20
Nodes (17): largest_on(), objective_big_m(), per_storage(), Assignment, A disk's storage under `assign` -- `assign` only ever has entries for movable…, Section 5.3 (C8), written out independently of the engine's…, Section 5.3 (C5)/5.3.1: `R_s = max(f_s * Z_s, soft_s)`., Per-storage load, usage and reserve status for one assignment. (+9 more)

### Community 119 - "payback"
Cohesion: 0.21
Nodes (14): cost(), duration(), duration_mirror(), duration_wipe(), E_of(), F_of(), ratio(), payback() (+6 more)

### Community 120 - "collect.py"
Cohesion: 0.08
Nodes (29): functools, gzip, Bundle, CallRecord, capture_range_seconds(), CaptureEstimate, _dump_json(), estimate_capture() (+21 more)

### Community 121 - "ReplayPveClient"
Cohesion: 0.24
Nodes (4): Any, Unlike every other method here, a missing file is not a bundle defect: a bundle…, Serves ``pve.py``'s eleven read methods from a bundle's ``pve/`` directory.…, ReplayPveClient

### Community 122 - "empty_state"
Cohesion: 0.18
Nodes (16): ``state.path`` could not be written, or its advisory lock could not be…, StateError, empty_state(), First-run state: no lock, no recorded balance, no cooldowns, nothing in flight…, Temp file in the same directory, ``fsync``, then ``os.replace`` -- a reader…, save_state_atomic(), Only `schema_version` present -- every other field must default the same way…, The `finally` block's own cleanup, pinned directly rather than only inferred… (+8 more)

### Community 123 - "Internals: Building the disk/storage/group model"
Cohesion: 0.13
Nodes (14): Internals: Building the disk/storage/group model, (C2) format eligibility: storage_type/allowed_formats, D: every disk placed, pinned or not, Foreign usage U^ext (unreferenced volumes), free_space soft_s/hard_s resolution, Pending-change pin, Per-disk cooldown pin, Disk sizes: content authoritative, config fallback (+6 more)

### Community 124 - "Logging: what lands where, and what an unattended run records"
Cohesion: 0.33
Nodes (6): Logging: what lands where, and what an unattended run records, Text or JSON, The decision trail, Unattended runs log this without being asked, Under systemd, Verbosity

### Community 125 - "FakePrometheusSession"
Cohesion: 0.19
Nodes (15): FakePrometheusSession, A ``metrics._SessionLike`` double capable of answering *many* distinct queries…, _instant_answer(), _range_answer(), A live capture against the dev cluster found this one directly (section 16.3's…, A live capture against the dev cluster found this directly:…, A live capture found this the hard way: ``_check_sample_series()``'s "info"…, Z-02: `_check_coverage()`'s per-disk warning embeds a real vmid taken straight… (+7 more)

### Community 126 - "_fetch_raw_quantity_series"
Cohesion: 0.18
Nodes (13): _RawTimeSeries, _fetch_raw_quantity_series(), One of the six section 3.4 raw quantities as a raw time series over ``[start,…, test_metrics.py's own ``_StepAwareFakeClient``, restated here for…, metrics.step >= metrics.rate_window (the failing gigapipe boundary, see…, --replay backward compatibility, the raw-series counterpart of…, The BundleError fallback (see…, ``RangeStepMismatch`` (a ``--replay`` bundle captured with ``collect-testdata… (+5 more)

### Community 127 - "Fixture"
Cohesion: 0.15
Nodes (7): computed_p_min(), Fixture, Section 5.3 (C7): `(Sum_d z_d + Sum_s U^ext) / (Sum_s C_s)` -- the group's mean…, Section 5.4's `D^big` threshold, converted from the fixture's…, Section 5.4's `w_v = max(1, l_v / l_bar)`. `V` (the vmids this returns weights…, The section 5.3 build-time bound: U_obj / eps_r, with eps_r = 1 MiB. The kappa…, One group: its storages, its disks and the weights to solve it with. ``keys``…

### Community 128 - "Diagnostic bundles: `collect-testdata` and `--replay`"
Cohesion: 0.40
Nodes (5): `collect-testdata`: capturing a bundle, Diagnostic bundles: `collect-testdata` and `--replay`, `--replay`: running against a bundle offline, Sending one to the project, What is in a bundle, and what is not

### Community 130 - "MetricsError"
Cohesion: 0.17
Nodes (11): MetricsError, Prometheus could not be queried, or the response was unusable. See…, refuse(), per_group_load(), fail(), raise_metrics_error(), MonkeyPatch, Integration through the real caller: a field silently missing one disk the… (+3 more)

### Community 131 - "filter_vm_config_fields"
Cohesion: 0.20
Nodes (11): MappingType, filter_disk_value_params(), filter_vm_config_fields(), filter_vm_pending_entries(), Any, The allowlisted subset of a disk value's ``key=value`` parameters…, ``VM_CONFIG_EXTRA_FIELDS`` plus every disk key matching…, Section 3.8/16.3: reduce ``vm_pending()``'s response to the one boolean signal… (+3 more)

### Community 132 - "_one_vm_two_storage_cluster"
Cohesion: 0.24
Nodes (10): _one_vm_two_storage_cluster(), Section 5.3.1: ``hard_s > soft_s`` is a validation error -- a floor above the…, Section 5.3.1: ``soft_s >= C_s`` is a validation error -- a requirement no disk…, Section 3.5: ``verify-storages`` shows the resolved pair *with the level each…, _sources(), test_build_topology_rejects_a_hard_floor_above_its_resolved_soft(), test_build_topology_rejects_a_soft_floor_not_below_capacity(), test_free_space_provenance_global_percent_without_a_hard() (+2 more)

### Community 133 - "_exec_group"
Cohesion: 0.24
Nodes (10): _exec_disk(), _exec_group(), _posted_move(), The live transient check charges the converted size from the live `size=`., test_a_converting_move_is_refused_when_the_live_check_finds_no_room(), test_a_live_format_that_differs_from_the_plan_means_replan(), test_format_is_not_sent_when_the_disk_already_has_the_enforced_format(), test_format_is_not_sent_without_enforcement() (+2 more)

### Community 134 - "Load model page"
Cohesion: 0.39
Nodes (8): Symbols D S Uext, apply_forecast scaling, compute_disk_load_series, compute_group_load, Coverage rejection, Current-assignment L_s u_s, Idle group T_g zero, Load model page

### Community 135 - "Safety properties, exit codes, and what this build actually does"
Cohesion: 0.25
Nodes (8): forecast (Holt-Winters), verify-metrics exit status and severity levels, Failure to read ends the run with exit 1, forecast: line, Exit codes, Optional dependencies, Safety properties, exit codes, and what this build actually does, What is safe, unconditionally

### Community 148 - "test_enforce_format.py"
Cohesion: 0.09
Nodes (54): needs_cbc, disk_size_on(), qcow2_lvm_allocation_bytes(), Upper bound on the LV ``alloc_image`` creates for a ``qcow2`` volume of…, Section 5.3.2's ``phi(d, s)``: the format ``disk`` would have on ``storage``.…, Section 5.3.2's ``z_{d,s}``, in bytes: what ``disk`` occupies when placed on…, target_format(), tests_unit (+46 more)

### Community 149 - "_client_with_fake_time"
Cohesion: 0.31
Nodes (7): _client_with_fake_time(), _flaky(), Exception, test_5xx_is_transient_and_tolerance_is_restored(), test_no_retry_by_default_for_non_transient_errors_or_non_idempotent_calls(), test_outage_longer_than_tolerance_raises_a_transient_error(), test_unreachable_api_is_retried_inside_outage_tolerance()

### Community 153 - "Configuration page"
Cohesion: 0.43
Nodes (7): Config path resolution order, Configuration page, ResolvedConfig, Secrets from environment, Semantic validation rules, Two-stage validation, Units parsed once

### Community 154 - "disk_state_key"
Cohesion: 0.29
Nodes (7): State dataclass tree mirrors section 11.2 JSON, disk_state_key(), ``"<group>:<vmid>:<device>"`` (section 11.2) -- the group prefix is what keeps…, ``"<group>:<storage>"`` (section 11.2)., storage_state_key(), test_disk_state_key_matches_section_11_2_shape(), test_storage_state_key_matches_section_11_2_shape()

### Community 155 - "Payback page"
Cohesion: 0.52
Nodes (7): compute_move_cost, Mirror duration bwlimit, Payback page, Payback verdict, _plan_group wiring, Reserve-override exemption, Wipe duration magnitude

### Community 156 - "28-apply.md"
Cohesion: 0.29
Nodes (6): Salted pseudonym anonymization, Bundle layout and manifest, collect-testdata command, Submitting a bundle to the corpus, --estimate and support.max_series_points refusal, --replay offline mode

### Community 157 - "Gates page"
Cohesion: 0.53
Nodes (6): Cooldowns not in gates, Drift gate, evaluate_group_gates, Gates page, last_load state, Reserve override gate

### Community 158 - "proxmox-storage-drs"
Cohesion: 0.40
Nodes (4): Getting the tool, proxmox-storage-drs, The documents, The safety properties to rely on

### Community 159 - "`gates` — deciding whether to act at all"
Cohesion: 0.33
Nodes (6): `gates.capacity_spread_threshold`, `gates.cooldown_per_disk`, `gates.cooldown_per_storage`, `gates` — deciding whether to act at all, `gates.drift_threshold`, `gates.imbalance_threshold`

### Community 160 - "resolve_level"
Cohesion: 0.50
Nodes (5): Section 2.3's ladder: ``--quiet`` < default < ``-v`` < ``-vv``. ``--log-level``…, resolve_level(), parametrize, test_log_level_wins_over_both_verbose_and_quiet(), test_resolve_level_ladder()

### Community 161 - "`load_weights` — combining read/write and time/ops/bytes"
Cohesion: 0.33
Nodes (6): `load_weights.bytes`, `load_weights` — combining read/write and time/ops/bytes, `load_weights.iotime`, `load_weights.ops`, `load_weights.read_factor`, `load_weights.write_factor`

### Community 162 - "Decision trail events"
Cohesion: 0.40
Nodes (5): Decision trail events, --log-format text vs json, Report on stdout, log on stderr, Mandatory audit floor for confirm/auto apply, Verbosity flags (--quiet, -v, -vv, --log-level)

### Community 163 - "Monitoring: the status file"
Cohesion: 0.40
Nodes (5): Freshness: why every run rewrites the file, Monitoring: the status file, What is in the file, What makes a run `OK`, `WARNING` or `CRITICAL`, Wiring it into Nagios/NRPE

### Community 164 - "decimate_to_configured_step"
Cohesion: 0.40
Nodes (5): decimate_to_configured_step(), The inverse of :func:`safe_range_step_seconds`: recover a series at…, safe_range_step_seconds(300, 300) == 150 -- a series captured at that finer…, test_decimate_to_configured_step_is_a_no_op_when_steps_match(), test_decimate_to_configured_step_keeps_every_nth_point()

### Community 165 - "DrsError"
Cohesion: 0.07
Nodes (34): ArgumentParser, CommandHandler, _accumulate_move_stats(), apply_mode_override(), build_parser(), _fallback_manual_text(), _log_run_summary(), main() (+26 more)

### Community 166 - "loadmodel.py"
Cohesion: 0.12
Nodes (24): _combine_raw_values(), _combined_raw(), _fetch_all_raw_quantities(), _fetch_all_raw_quantity_series(), _fetch_raw_quantity(), _is_metrics_expected_absent(), _per_disk_lookup(), One of the six section 3.4 raw quantities, quantile-reduced over the decision… (+16 more)

### Community 169 - "_mapper"
Cohesion: 0.14
Nodes (12): _mapper(), Any, BaseException, _Raise, X-09: `manifest.json`'s `counts.dropped_records` is documented as counting…, A task's ``id`` is the vmid its UPID embeds. It used to be copied raw, leaving…, _tasks_by_kind(), test_anonymize_cluster_tasks_maps_the_task_id_with_the_upid() (+4 more)

### Community 170 - "_FakeClient"
Cohesion: 0.40
Nodes (3): str, _FakeClient, The ``"fake-client"`` sentinel every ``build_pve_client`` mock in this file…

### Community 171 - "test_logging_setup.py"
Cohesion: 0.19
Nodes (13): ast, io, JsonFormatter, Render one :class:`logging.LogRecord` as one JSON line., Section 2.3: "Every log record carries an ``event``" -- the event names are an…, Logging policy. See proxmox_storage_drs/logging_setup.py and…, Found live: section 7's payback ratio is `+inf` for any plan with no moves to…, _strict() (+5 more)

## Knowledge Gaps
- **222 isolated node(s):** `proxmox-storage-drs`, `run-with-system-python.sh script`, `build_paper.sh script`, `build_site.sh script`, `The safety properties to rely on` (+217 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1399 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **22 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Persistent state: state.json` connect `Persistent state: state.json` to `load_state`, `loadmodel.py`, `Manual: Configuration reference`, `state.py`, `topology.py`, `execute.py`, `GroupLoad`, `Overview page`, `cli.py`, `heuristic.py`, `disk_state_key`, `crashrecovery.py`?**
  _High betweenness centrality (0.087) - this node is a cross-community bridge._
- **Why does `Manual: Configuration reference` connect `Manual: Configuration reference` to `Monitoring status file`, `Safety properties, exit codes, and what this build actually does`, `Persistent state: state.json`, `Internals: The heuristic solver`, `Configuration reference`, ``metrics` — Telegraf/InfluxDB name mapping`, `fragmentation`, `Internals: CLI dispatch and logging`, `Configuration page`, `Internals: Building the disk/storage/group model`, `drs.example.yaml (reference configuration)`?**
  _High betweenness centrality (0.080) - this node is a cross-community bridge._
- **Why does `Group` connect `Group` to `MonkeyPatch`, `build_topology`, `_handle_apply`, `Path`, `_exec_group`, `test_cli.py`, `test_loadmodel.py`, `Storage`, `run`, `evaluate_assignment`, `topology.py`, `GroupLoad`, `Disk`, `test_payback.py`, `ExecutionResult`, `test_enforce_format.py`, `test_optimize.py`, `run_concurrent`, `ScheduleResult`, `apply_forecast`, `typing`, `format_bytes`, `DrsError`, `loadmodel.py`, `ExecutionConfig`, `schedule.py`, `heuristic.py`, `test_affinity_repair_fixture.py`, `test_small_disks.py`, `capture_bundle`, `execute.py`, `cli.py`, `_plan_group`, `FakeClock`, `test_plan_gate_also_reflects_real_drift_history_from_state_json`, `collect.py`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._
- **Are the 199 inferred relationships involving `Group` (e.g. with `_accumulate_move_stats()` and `_apply_payback_gate()`) actually correct?**
  _`Group` has 199 INFERRED edges - model-reasoned connections that need verification._
- **Are the 94 inferred relationships involving `PveClient` (e.g. with `_apply_payback_gate()` and `_pve_client_for()`) actually correct?**
  _`PveClient` has 94 INFERRED edges - model-reasoned connections that need verification._
- **Are the 73 inferred relationships involving `Disk` (e.g. with `_fragmented_vms()` and `_pinned_disks()`) actually correct?**
  _`Disk` has 73 INFERRED edges - model-reasoned connections that need verification._
- **What connects `proxmox-storage-drs`, `run-with-system-python.sh script`, `build_paper.sh script` to the rest of the system?**
  _222 weakly-connected nodes found - possible documentation gaps or missing edges._