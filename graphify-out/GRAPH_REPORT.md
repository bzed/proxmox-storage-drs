# Graph Report - proxmox-storage-drs  (2026-10-09)

## Corpus Check
- 118 files · ~340,440 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 21 file(s) not represented in the graph (top: (none) 12, .sha256 3, .conf 1)

## Summary
- 4127 nodes · 12042 edges · 164 communities (141 shown, 23 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 1766 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `dd45f7d1`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- MonkeyPatch
- build_topology
- _sample_topology
- config.py
- test_config.py
- Path
- Installation and requirements
- test_cli.py
- test_loadmodel.py
- test_metrics.py
- case_for
- run
- evaluate_assignment
- topology.py
- Configuration reference
- GroupLoad
- Group
- test_payback.py
- ExecutionResult
- pve.py
- test_optimize.py
- Fixture
- test_validate_corpus.py
- test_replay.py
- run_concurrent
- .agents/documentation.md
- PveClient
- test_anonymize.py
- Internals: The heuristic solver
- `execution` — how (and whether) moves actually happen
- test_collect.py
- test_free_space_repair_fixture.py
- test_execute.py
- TimeWindow
- Installation and requirements (manual)
- empty_state
- series_of
- C5 Capacity, snapshot reserve and free space
- ExecutionConfig
- test_topology.py
- Manual: Configuration reference
- configure_logging
- Transient invariant
- order_moves
- Lexicographic solve (reserve first, then balance)
- test_forecast.py
- build_fake_client
- make_config
- Overview page
- Engine pipeline: collect, join, gate, solve, cost, order, execute
- test_documentation.py
- loadmodel.py
- test_statusfile.py
- Any
- cli.py
- `proxmox` — the cluster API connection
- test_large_vm_split_fixture.py
- build_client
- Execute page
- Proxmox Storage DRS Implementation Plan
- state.py
- forecast_group
- save_state_atomic
- State
- forecast.py
- test_affinity_repair_fixture.py
- test_small_disks.py
- move_disk (drive-mirror, delete=1)
- Reading `apply`
- FakePrometheusSession
- Where the numbers come from, and how a transport loses them
- pve-storage-drs.1.md
- _check_sample_series
- compute_reserve_status
- Internals: Building the disk/storage/group model
- fragmentation
- test_live_transient_check_fails_safe_when_the_live_read_errors
- Backtest
- stitch_range_results
- test_plan_gate_also_reflects_real_drift_history_from_state_json
- _exec_group
- `migration` — cost, bandwidth and the payback rule
- anonymize.py
- _fragmented_vms
- metrics.py
- json_safe
- What `plan` does not yet do
- PrometheusClient
- Internals: CLI dispatch and logging
- test_units.py
- ._get
- Safety properties, exit codes, and what this build actually does
- _state_from_dict
- test_state.py
- Load model page
- Mapper
- disk_factors
- _FakeSession
- FakeProxmoxResource
- pytest
- 25-show-load-and-verify-storages.md
- MoveCost
- README.md
- test_holt_winters_quantile_forecasts_ceil_window_over_step_steps
- excess_of
- save_locked_state
- Payback page
- free_space requirement soft_s / hard_s
- Payback rule and acceptance test
- 28-apply.md
- Load model (average in-flight I/O)
- E_of
- Monitoring status file
- check_paper_log.py
- execute.py
- Gates page
- `groups` — storage groups
- `load_weights` — combining read/write and time/ops/bytes
- Logging: what lands where, and what an unattended run records
- split_gate_opens
- collect.py
- `forecast` — placing disks for the load they will have
- AGENTS.md working agreement
- Decision trail events
- _anonymized_config_dict
- `metrics` — Telegraf/InfluxDB name mapping
- test_reconcile_inflight_and_fold_exclusions_merges_discovered_vmids
- Assignment
- Diagnostic bundles: `collect-testdata` and `--replay`
- filters.lua
- test_a_crash_leaves_a_critical_status_file_and_still_raises
- `exclude` — what DRS never touches
- proxmox_storage_drs
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
- Configuration page
- test_logging_setup.py
- proxmox-storage-drs
- FakeClock
- test_manual_falls_back_when_man_exits_nonzero
- Path
- resolve_node_selector
- build_site.sh
- _mapper
- _FakeClient
- Persistent state: state.json
- build_rate_promql
- order_moves
- generate_expected.py

## God Nodes (most connected - your core abstractions)
1. `Group` - 229 edges
2. `PveClient` - 127 edges
3. `Disk` - 109 edges
4. `run()` - 84 edges
5. `write_config()` - 83 edges
6. `make_move()` - 81 edges
7. `client_with()` - 80 edges
8. `Proxmox Storage DRS Implementation Plan` - 78 edges
9. `build_topology()` - 77 edges
10. `Storage` - 75 edges

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

## Communities (164 total, 23 thin omitted)

### Community 0 - "MonkeyPatch"
Cohesion: 0.07
Nodes (68): _patch_show_load_deps(), _patch_show_load_forecast(), CaptureFixture, Exception, MonkeyPatch, parametrize, `_sample_topology()` with san-b given more headroom (16 TiB instead of 8):…, san-a violates (C5); its only movable disk is 101:scsi0 (102:scsi0 is pinned,… (+60 more)

### Community 1 - "build_topology"
Cohesion: 0.14
Nodes (45): The cluster topology could not be built from the API responses. See…, TopologyError, build_topology(), Build the whole cluster's :class:`Topology` for this run. One pass: every read…, _lvm_def(), test_a_format_the_storage_type_cannot_hold_is_refused(), test_a_literal_entry_can_set_its_own_value(), test_a_pattern_matching_a_storage_that_cannot_hold_it_names_that_storage() (+37 more)

### Community 2 - "_sample_topology"
Cohesion: 0.08
Nodes (35): _all_pinned_sample_topology(), _fake_build_topology(), _fake_reconcile_inflight(), `_sample_topology()` plus a section 11.4 pattern expansion and one cluster…, Every `apply` test here uses `build_pve_client`'s "fake-client" string stand-…, `_sample_topology()` with its one movable disk pinned too: san-a violates (C5)…, X-05: cli.py used to build one bare topology (for the estimate check) and then…, A ``cli.build_topology`` stand-in that ignores the ``state``/``now`` cooldown… (+27 more)

### Community 3 - "config.py"
Cohesion: 0.06
Nodes (58): jsonschema, re, ruamel_yaml, ruamel_yaml_error, _build_config(), _check_connection_config(), _check_forecast_window(), _check_group_size() (+50 more)

### Community 4 - "test_config.py"
Cohesion: 0.08
Nodes (79): ConfigError, The configuration file is missing, unreadable or fails validation. See…, minimal_config_dict(), Any, parametrize, Path, skipif, The smallest config that passes structural + semantic validation. (+71 more)

### Community 5 - "Path"
Cohesion: 0.07
Nodes (69): The whole cluster's worth of groups, as seen by this run. By the time anything…, Topology, _fragmented_group(), _make_group_plan(), _moved_outcome(), _one_disk_group(), _one_disk_group_load(), _one_move() (+61 more)

### Community 6 - "Installation and requirements"
Cohesion: 0.25
Nodes (8): First steps after installing, Installation and requirements, Installing the package, Running the timer on exactly one host, Setting up the PVE credential, What you need, Where the configuration is *not*, Where the configuration lives

### Community 7 - "test_cli.py"
Cohesion: 0.03
Nodes (69): load_config(), Resolve, read, parse and validate the configuration. See section 11 for…, _balanced_non_violating_topology(), _breakdown_with_split(), _gate(), _no_move_schedule(), _NodeNamesClient, _outcome() (+61 more)

### Community 8 - "test_loadmodel.py"
Cohesion: 0.07
Nodes (81): LoadWeights, apply_forecast(), _blend_loads(), compute_disk_load_series(), compute_group_load(), _is_metrics_expected_absent(), TimeSeries, Section 4's normalize-then-weight-then-rescale blend, given every key's own… (+73 more)

### Community 9 - "test_metrics.py"
Cohesion: 0.07
Nodes (65): WindowConfig, MetricsError, Prometheus could not be queried, or the response was unusable. See…, _check_coverage(), _check_metric_names_exist(), _check_observed_spacing(), PrometheusClient, Run every section 3.3 check and assemble the report. Must be run before relying… (+57 more)

### Community 10 - "case_for"
Cohesion: 0.20
Nodes (18): StorageState, best_big_m(), build(), capacity_spread(), case_for(), moves_of(), order_moves(), per_storage() (+10 more)

### Community 11 - "run"
Cohesion: 0.09
Nodes (62): client_with(), default_group(), make_move(), Fails safe: a volume with neither `size` nor `approximate-size` makes the…, A move missing from `move_costs_by_key` is never refused for lack of an…, Section 13: `state.json` must learn about a UPID *before* this function goes on…, Not only the happy path -- a `move_disk` task that itself fails still finished…, `dry-run` never calls `move_disk` at all -- the callbacks must simply never… (+54 more)

### Community 12 - "evaluate_assignment"
Cohesion: 0.05
Nodes (91): best_single_disk_alternative(), compute_vm_weights(), evaluate_assignment(), group_average_utilization(), HeuristicResult, _movable_disks(), One group's heuristic solve. ``assignment`` is the final target placement…, `D^mov` (section 5.3): disks (C2) has not fixed in place. A pinned disk's… (+83 more)

### Community 13 - "topology.py"
Cohesion: 0.05
Nodes (71): concurrent_futures, approximate-size fallback for qcow2-on-LVM volumes, Which disks can move online (all buses, efidisk0, tpmstate0, unused), GroupConfig, is_storage_pattern(), A ``storages[].id`` value is a pattern iff it both begins and ends with ``/``…, The regular expression text of a pattern entry, its two ``/`` delimiters…, storage_pattern_text() (+63 more)

### Community 14 - "Configuration reference"
Cohesion: 0.05
Nodes (42): Configuration reference, `free_space.hard`, `free_space` — keep N bytes (or N%) free on top of the snapshot reserve, `free_space.soft`, `gates.capacity_spread_threshold`, `gates.cooldown_per_disk`, `gates.cooldown_per_storage`, `gates` — deciding whether to act at all (+34 more)

### Community 15 - "GroupLoad"
Cohesion: 0.07
Nodes (69): GatesConfig, evaluate_group_gates(), _l1_drift(), Section 6, applied in the order it lists: reserve override, then the capacity…, ``(‖ℓ_last‖₁, ‖ℓ_now − ℓ_last‖₁)`` over the **union** of disk keys present in…, _aggregate_storages(), DiskLoad, GroupLoad (+61 more)

### Community 16 - "Group"
Cohesion: 0.05
Nodes (94): Disk-cooldown pin is not exempted for reserve repair, _RepairCandidate, ObjectiveConfig, _capacity_spread(), Section 5.3 (C7)'s `(max_s b_s - min_s b_s) / b_bar`, or ``None`` when the gate…, active_split_caps(), _best_of(), _best_repair_candidate() (+86 more)

### Community 17 - "test_payback.py"
Cohesion: 0.07
Nodes (65): MigrationConfig, compute_benefit_load_seconds(), compute_move_cost(), evaluate_plan_payback(), Section 7.1's cost for one scheduled move. Only ``source`` is needed (not the…, Section 7.2: ``benefit = (alpha*(E_before - E_after) + delta*(F_before -…, Section 7.3: the aggregate acceptance test over a whole plan, plus the hard…, The mu*dO term is what pays here: kappa*dA alone is negative. (+57 more)

### Community 18 - "ExecutionResult"
Cohesion: 0.08
Nodes (56): ExecutionResult, One group's ``execute_plan()`` call. ``stopped_early`` is true for any reason…, _balanced_apply_group_load(), _balanced_apply_topology(), _check_statusfile(), _monitored_config(), _patch_plan_deps(), Two evenly-sized, evenly-loaded disks on one storage, none on the other, no… (+48 more)

### Community 19 - "pve.py"
Cohesion: 0.04
Nodes (49): AuthenticationError, contextlib, proxmoxer, requests, ResourceException, PveUnreachableError, A :class:`PveApiError` with ``transient`` set: the API could not be reached, or…, _api_error() (+41 more)

### Community 20 - "test_optimize.py"
Cohesion: 0.09
Nodes (58): cbc_available(), make_disk(), make_storage(), LogCaptureFixture, MonkeyPatch, parametrize, Deliberately *not* parametrized over the skip-guarded `BACKENDS` list above --…, Section 5.4's D^big: at beta_move_count=1.0, moving `201:efidisk0` (1 MiB) to… (+50 more)

### Community 21 - "Fixture"
Cohesion: 0.12
Nodes (9): computed_p_min(), Fixture, Section 5.3 (C7): `(Sum_d z_d + Sum_s U^ext) / (Sum_s C_s)` -- the group's mean…, Section 5.4's `D^big` threshold, converted from the fixture's…, Section 5.4's mu (``objective.mu_vm_split_per_tib``), 0 when the split rule is…, ``{vmid: T_v}`` for ``V^split`` (section 5.3.3), written out independently of…, Section 5.4's `w_v = max(1, l_v / l_bar)`. `V` (the vmids this returns weights…, The section 5.3 build-time bound: U_obj / eps_r, with eps_r = 1 MiB. The kappa… (+1 more)

### Community 22 - "test_validate_corpus.py"
Cohesion: 0.09
Nodes (47): tests_corpus, tests_corpus_validate_corpus, _case(), _invariant_inputs(), MonkeyPatch, needs_full_checkout, parametrize, Path (+39 more)

### Community 23 - "test_replay.py"
Cohesion: 0.11
Nodes (42): PrometheusConfig, _captured_step(), _config_from_bundle(), _free_space_pairs(), MonkeyPatch, Path, AH-06: a live ``free_space`` config is collected as the resolved per-storage…, Section 16.5's one deliberate exception: a bundle captured before section 3.8… (+34 more)

### Community 24 - "run_concurrent"
Cohesion: 0.09
Nodes (36): concurrent_client_with(), datetime, The defining property of concurrency: `move_disk` for the second move is issued…, Each move's own UPID reaches both callbacks correctly attributed --…, Two otherwise-independent moves landing on the *same* target: even with…, Section 8.1's generalized invariant, live: san-c has only 2 TiB of headroom…, A leftover 1 TiB volume of VM 201 already on san-c when 201 launched (an orphan…, The deliberate simplification documented in `_execute_concurrent()`'s own… (+28 more)

### Community 25 - ".agents/documentation.md"
Cohesion: 0.13
Nodes (13): Config knob entry: type, default, unit, extremes, interactions, Tests keeping docs honest (help covers options, manual covers config), --help generated from argparse definitions, no hardcoded defaults, Internals pages: question first, name modules, explain why, ASCII diagrams, Manpage skeleton with complete OPTIONS, config/drs.example.yaml as documentation that parses, Change behaviour and documentation in the same commit, PDF is a build product; fix text not LaTeX (+5 more)

### Community 26 - "PveClient"
Cohesion: 0.08
Nodes (60): PveApiError, The Proxmox VE API returned an error or an unusable response. See…, PveClient, One method per IMPLEMENTATION_PLAN.md section 3.5 endpoint. ``api`` is typed…, Retry idempotent calls that fail because the API is unreachable for up to…, fake_api(), BaseException, Shared test doubles. Not collected by pytest (no ``test_`` prefix).… (+52 more)

### Community 27 - "test_anonymize.py"
Cohesion: 0.06
Nodes (42): make_mapper(), MonkeyPatch, parametrize, Path, A node and a storage that happen to share a name must not collide., Section 16.3: 'the result never depends on iteration order'., Force two different vmids to hash to the same base slot and confirm both still…, X-09: `vmid`'s own linear probing makes a collision impossible, but nothing did… (+34 more)

### Community 28 - "Internals: The heuristic solver"
Cohesion: 0.14
Nodes (17): reserve.py: shared (C4)/(C5) evaluator, Internals: The heuristic solver, best_single_disk_alternative(), Descend explores swaps, evaluate_assignment(): objective separate from search, Storage cooldown excludes destination, never source, Repair is unconditional, not weight-driven, w_v: kappa weighted by VM I/O, and D^big (+9 more)

### Community 29 - "`execution` — how (and whether) moves actually happen"
Cohesion: 0.12
Nodes (16): `execution.abort_on_failure`, `execution` — how (and whether) moves actually happen, `execution.locks.on_timeout`, `execution.locks.poll_interval`, `execution.locks.task_retry_backoff`, `execution.locks.task_retry_limit`, `execution.locks.wait_timeout`, `execution.max_concurrent_migrations` (+8 more)

### Community 30 - "test_collect.py"
Cohesion: 0.09
Nodes (38): capture(), Path, X-08: section 16.1's manifest line ("schema, versions, what was captured...")…, X-08: section 16.3 promises the manifest "flags" a non-node-shaped…, Z-03: `resolve_node_selector()`'s tier-1 precedence used to win on *both* sides…, A live capture against the dev cluster found the previous implementation's bug…, verify_metrics() never carries a node selector at all -- nothing to rewrite,…, Even when the configured model is ``quantile``, the bundle is captured with… (+30 more)

### Community 31 - "test_free_space_repair_fixture.py"
Cohesion: 0.11
Nodes (29): executed_assignment(), Assignment, Section 7.3: "what it will really run" -- ``final_assignment``…, Section 7.3's revert test, one verdict per scheduled move in ``order``: would…, repair_markers(), `Σ_s r_s` at the assignment ``storage_of`` encodes -- section 7.3's outcome…, total_shortfall_bytes(), _free_space_repair_group() (+21 more)

### Community 32 - "test_execute.py"
Cohesion: 0.08
Nodes (30): A `san-c` content responder plus a `move_disk` responder for 201. The listing…, 201's mirror target is already *listed* on san-c at its full 1 TiB by the time…, Between different storage types, or from thin to thick, `move_disk` allocates…, The match stays narrow: a same-VM volume that appeared after launch but has…, The exclusion is narrow: only 201's *own* mirror target (same VM, the disk's…, Section 8.1 / 5.3.3: VM 101 already has 3 TiB on san-b, another VM 3.5 TiB. A 1…, Executing a plan. See proxmox_storage_drs/execute.py. No test here talks to a…, `/cluster/tasks` shape for a task still running: no endtime/status. (+22 more)

### Community 33 - "TimeWindow"
Cohesion: 0.15
Nodes (34): date, TimeWindow, current_deadline(), _day_name(), is_window_active(), _parse_hhmm(), datetime, ``execution.time_windows``: when ``auto`` mode may execute moves. See… (+26 more)

### Community 34 - "Installation and requirements (manual)"
Cohesion: 0.12
Nodes (22): GitHub Actions and Salsa GitLab CI pipelines, Dry-run is the default, Release procedure (version bump, changelog, debian/ tag, graphify commit), /etc/pve/drs.yaml on pmxcfs, Installation and requirements (manual), state.json (node-local state), Nothing is ever deleted automatically, Unconditional safety properties (+14 more)

### Community 35 - "empty_state"
Cohesion: 0.15
Nodes (31): flock is the lock; JSON lock field is only a label, acquire_lock(), empty_state(), load_state(), _parse_state_text(), First-run state: no lock, no recorded balance, no cooldowns, nothing in flight…, The tolerant-parse half of :func:`load_state`, factored out so…, Best-effort read of ``path``. See the module docstring: a missing file is the… (+23 more)

### Community 36 - "series_of"
Cohesion: 0.12
Nodes (14): holt_winters_quantile(), ``window.quantile`` of the Holt-Winters forecast path over the next…, Any, A diurnal series that *ends at its trough*: the last forecast point (one day…, series_of(), test_backtest_is_none_without_a_fit_half(), test_backtest_is_none_without_an_actual_half(), test_holt_winters_quantile_clamps_at_zero() (+6 more)

### Community 37 - "C5 Capacity, snapshot reserve and free space"
Cohesion: 0.14
Nodes (21): autopkgtest runtime-dependency check, Autopkgtest install-with-only-Depends check, C1 Assignment, (C3) VM affinity linking, (C4) Largest-disk linearization Z_s, C5 Capacity, snapshot reserve and free space, CBC via PuLP MILP backend, CP-SAT ortools backend removed (AL-02) (+13 more)

### Community 38 - "ExecutionConfig"
Cohesion: 0.15
Nodes (29): ExecutionConfig, SourceReleaseConfig, _group_with_types(), make_disk(), make_storage(), Section 9.3: a source_release timeout "does not fail the run: mark the storage…, Same as above, except the second move's *target* -- not source -- is the…, Section 9.3 point 3: PVE's own `saferemove_throughput` (already read live off… (+21 more)

### Community 39 - "test_topology.py"
Cohesion: 0.09
Nodes (31): vm_config returns pending value; vm_pending exposes both, disk_state_key(), ``"<group>:<vmid>:<device>"`` (section 11.2) -- the group prefix is what keeps…, pending_disk_reasons(), _pin_reason(), Section 3.8: which disk device keys in ``GET .../pending`` (section 3.5's…, Section 5.3 (C2)'s pin conditions, in the order the plan lists them -- the…, _one_disk_cluster() (+23 more)

### Community 40 - "Manual: Configuration reference"
Cohesion: 0.10
Nodes (33): drs.example.yaml (reference configuration), free_space soft_s/hard_s resolution, objective.spread_metric: two different quantities, cli.py backend dispatch: auto cascades, explicit falls back, Persistent-objective reduction per cost_m ranking, Manual: Configuration reference, exclude rules, execution.mode (dry-run default) (+25 more)

### Community 41 - "configure_logging"
Cohesion: 0.12
Nodes (26): Configure logging for this run and emit ``run_started``. Returns the log format…, _start_logging_and_announce_run(), configure_logging(), floor_for_command(), The mandatory ``INFO`` floor of section 2.3, or ``None``. A run that can change…, Install this run's log handler. Called once, from ``main()``. ``floor`` is…, CaptureFixture, INFO at a terminal is the narrative the operator asked for; prefixing every… (+18 more)

### Community 42 - "Transient invariant"
Cohesion: 0.18
Nodes (16): Domain invariants (.agents), Enumerate every disk bus, Finished task is not a finished move, Never auto-delete a volume, Provisioned size, never allocated, Snapshot reserve never traded for balance, VM locks are an open set, A finished task is not a finished move (+8 more)

### Community 43 - "order_moves"
Cohesion: 0.11
Nodes (36): order_moves(), _pending_moves(), Assignment, Section 8.1's transient invariant, called with the single-move set ``{disk}``…, Section 8.2 priority 1: is ``disk``'s *current* (in ``state``) storage…, Section 8.2's scheduling loop for one group. ``target_assignment`` is normally…, _resolves_reserve_violation(), transient_invariant_ok() (+28 more)

### Community 44 - "Lexicographic solve (reserve first, then balance)"
Cohesion: 0.17
Nodes (15): Disks with snapshots pinned, Testing (.agents), Acceptance fixtures and generate_expected.py, 85 percent coverage floor, No network, no real sleep, deterministic ties in tests, Codecov configuration, GitHub Actions Tests workflow, Big-M penalty P fallback (computed P_min) (+7 more)

### Community 45 - "test_forecast.py"
Cohesion: 0.21
Nodes (14): random, _group_series(), _noise_series(), TimeSeries, Holt-Winters forecasting, its backtest gate, and the required-range rule., Fewer than 2 * seasonal_periods samples before now - W: Holt-Winters cannot be…, test_backtest_fails_on_white_noise(), test_backtest_hw_error_is_none_when_the_fit_half_is_too_short() (+6 more)

### Community 46 - "build_fake_client"
Cohesion: 0.13
Nodes (26): build_fake_client(), _content(), _one_vm_two_storage_cluster(), _pair(), Any, Section 5.3 (C8): VM 301's only disk in this group is a 528 KiB efidisk0 (its…, Section 3.7 item 3: the operator must learn *which* volume blocks the VM. The…, Section 3.5: ``verify-storages`` shows the resolved pair *with the level each… (+18 more)

### Community 47 - "make_config"
Cohesion: 0.14
Nodes (24): make_config(), make_prometheus_client(), make_pve_client(), --no-series must skip the big, per-group superset range captures -- it does not…, Y-06: the manifest's version fields are machine-generated provenance, not free…, X-09: the printed query count used to treat a multi-day range as one range…, Z-05: a live capture stores every range series at…, Section 3.8/16.3: a real pending edit on the VM's own disk survives as the… (+16 more)

### Community 48 - "Overview page"
Cohesion: 0.29
Nodes (12): config.py depends on forecast.py, Module layout, Overview page, Seven-stage pipeline, Two solver backends, Backtest gate, Drift baseline is effective load, Forecast provenance report (+4 more)

### Community 49 - "Engine pipeline: collect, join, gate, solve, cost, order, execute"
Cohesion: 0.16
Nodes (16): Engine pipeline: collect, join, gate, solve, cost, order, execute, (C6) Load spread, Capacity spread gate (default 0.25), Move completion criterion stronger than task success, Per-disk and per-storage cooldowns, Deadlock and staging, Failure handling (orphans, partial plan, supervision loss), Gating (drift, imbalance, capacity gates, cooldowns, reserve override) (+8 more)

### Community 50 - "test_documentation.py"
Cohesion: 0.14
Nodes (26): importlib_resources, _flatten_schema_keys(), _load_schema(), _manpage_source_text(), _manual_documented_keys(), Any, needs_full_checkout, parametrize (+18 more)

### Community 51 - "loadmodel.py"
Cohesion: 0.05
Nodes (76): _RawTimeSeries, MetricLabels, MetricsConfig, _combine_raw_values(), _combined_raw(), _fetch_all_raw_quantities(), _fetch_all_raw_quantity_series(), _fetch_raw_quantity() (+68 more)

### Community 52 - "test_statusfile.py"
Cohesion: 0.07
Nodes (59): CompletedProcess, datetime, needs_plugin, os, DrsError, ExecutionError, Exception, Base class for every error this project raises on purpose. (+51 more)

### Community 53 - "Any"
Cohesion: 0.19
Nodes (6): FakeResponse, Any, _RangeStepMismatchFakeClient, A ``range_query`` stand-in that returns caller-supplied data keyed by the exact…, Like ``_StepAwareFakeClient``, but raises ``RangeStepMismatch`` (carrying its…, _WindowTrackingFakeClient

### Community 54 - "cli.py"
Cohesion: 0.02
Nodes (197): ArgumentParser, CommandHandler, Mutable state box narrow exception to functional style, What this build actually implements, Namespace, shutil, _accumulate_move_stats(), _apply_exit_code() (+189 more)

### Community 55 - "`proxmox` — the cluster API connection"
Cohesion: 0.20
Nodes (10): `proxmox.auth.password`, `proxmox.auth.token_secret`, `proxmox.auth.username`, `proxmox.ca_file`, `proxmox.host`, `proxmox.port`, `proxmox.read_workers`, `proxmox` — the cluster API connection (+2 more)

### Community 56 - "test_large_vm_split_fixture.py"
Cohesion: 0.16
Nodes (21): Section 6's split gate: ``(vmid, reason)`` for the first large VM (``V^split``,…, split_gate(), _disk(), _footprints(), _group(), parametrize, No single move lowers a peak of 4 on three storages (4, 4, 2 -> 2, 4, 4)., The counterfactual recorded in the expected file. (+13 more)

### Community 57 - "build_client"
Cohesion: 0.09
Nodes (29): The Proxmox VE API client, API token permission is intersection with owner, Best-effort ticket refresh tightening, build_client assembles auth once, bwlimit bytes/s to KiB/s conversion only in move_disk, Single reauthenticate-and-retry in _call, storage_content silently empty without Datastore.Allocate, storage_definitions uses the list form GET /storage (+21 more)

### Community 58 - "Execute page"
Cohesion: 0.36
Nodes (10): Auto mode time window, Concurrent execution, Execute page, execute_plan live revalidation, Four-condition done, Injectable Clock, Live transient check provisioned, Orphans reported never deleted (+2 more)

### Community 59 - "Proxmox Storage DRS Implementation Plan"
Cohesion: 0.09
Nodes (35): Anonymization allowlist, never denylist, Migrations throttled by bwlimit only, Configuration and validation rules, tests/corpus and scrub audit, Dependencies come from Debian (trixie), Diagnostic bundles (collect-testdata), Disk identity join (vmid, device), Proxmox Storage DRS Implementation Plan (+27 more)

### Community 60 - "state.py"
Cohesion: 0.10
Nodes (31): Cooldown data stored here, interpreted by topology and heuristic, errno, fcntl, socket, _active_cooldowns(), active_disk_cooldowns(), active_storage_cooldowns(), cooldown_remaining_seconds() (+23 more)

### Community 61 - "forecast_group"
Cohesion: 0.22
Nodes (10): Collection, forecast_group(), group_aggregate_series(), TimeSeries, Sum every disk's own series into one group-aggregate series, at the union of…, One group's forecast: run the backtest on the group aggregate, and only if…, 101:scsi0 has no sample at t=1 at all -- that timestamp still appears (from…, test_group_aggregate_series_empty_input_is_empty() (+2 more)

### Community 62 - "save_state_atomic"
Cohesion: 0.20
Nodes (14): ``state.path`` could not be written, or its advisory lock could not be…, StateError, LockInfo, Temp file in the same directory, ``fsync``, then ``os.replace`` -- a reader…, Descriptive only -- see the module docstring's "Locking" section for why the…, save_state_atomic(), skipif, The `finally` block's own cleanup, pinned directly rather than only inferred… (+6 more)

### Community 63 - "State"
Cohesion: 0.10
Nodes (45): Crash and two-instance recovery: crashrecovery.py, cluster/tasks vs task_status conventions differ, parse_upid PVE UPID grammar confirmed live, reconcile_inflight: recorded UPIDs plus foreign scan, Startup scan folds excluded vmids before planning, Two failure modes, one in-flight UPID mechanism, Section 13's own words: "on startup, check for running move_disk UPIDs owned by…, _reconcile_inflight_and_fold_exclusions() (+37 more)

### Community 64 - "forecast.py"
Cohesion: 0.18
Nodes (15): Backtest gate: beat persistence baseline, Holt-Winters seasonal forecast (engine-side), math, ForecastConfig, HoltWintersConfig, Holt-Winters load forecasting. See IMPLEMENTATION_PLAN.md sections 10 and 12.1.…, The history ``forecast.model`` needs, in seconds. Called by ``config.py``'s…, required_range_seconds() (+7 more)

### Community 65 - "test_affinity_repair_fixture.py"
Cohesion: 0.19
Nodes (15): Section 7.2's unweighted ``E`` -- ``sum(e_s)`` (``"l1"``) or ``max(u_s)``…, Section 7.2's unweighted (by ``kappa``, but ``w_v``-weighted) ``A`` -- ``Sum_v…, raw_affinity_debt(), raw_spread(), _affinity_repair_group(), _loads(), _make_disk(), _make_storage() (+7 more)

### Community 66 - "test_small_disks.py"
Cohesion: 0.18
Nodes (21): current(), disk(), efi_repair_group(), parametrize, skipif, VM 301's big disks live in another group: its efidisk0 is alone here and never…, "slow" is short by 1000.2 MiB, so moving the 528 KiB EFI disk crosses a whole-…, Lexicographic stage 1 takes any shortfall reduction, however small, so without… (+13 more)

### Community 67 - "move_disk (drive-mirror, delete=1)"
Cohesion: 0.16
Nodes (18): Mandatory INFO audit floor for confirm/auto runs, (C2) Eligibility via variable fixing, Errors are not mismatches, Structured log event catalogue, Execution modes dry-run, confirm, auto, Logging policy (two audiences, levels, audit floor), move_disk (drive-mirror, delete=1), Disks with unapplied pending change excluded (+10 more)

### Community 68 - "Reading `apply`"
Cohesion: 0.14
Nodes (13): Concurrent execution, Crash and two-instance recovery, Failure and `abort_on_failure`, `--json`, Reading `apply`, Reading `auto` mode, `state.json`: what a real run actually changes, The `[y]es/[n]o skip/[a]ll remaining/[q]uit` prompt (+5 more)

### Community 69 - "FakePrometheusSession"
Cohesion: 0.18
Nodes (17): FakePrometheusSession, A ``metrics._SessionLike`` double capable of answering *many* distinct queries…, _instant_answer(), _range_answer(), A live capture against the dev cluster found this one directly (section 16.3's…, A live capture against the dev cluster found this directly:…, A live capture found this the hard way: ``_check_sample_series()``'s "info"…, Z-02: `_check_coverage()`'s per-disk warning embeds a real vmid taken straight… (+9 more)

### Community 70 - "Where the numbers come from, and how a transport loses them"
Cohesion: 0.10
Nodes (20): A reference implementation that is well tested, gigapipe with ClickHouse (reference backend), PVE InfluxDB external metric server, instance label collision, OpenTelemetry metric server rejected, Other backends, RRD rejected as data source, Six per-disk blockstat counters (+12 more)

### Community 71 - "pve-storage-drs.1.md"
Cohesion: 0.12
Nodes (15): AUTHOR, COLLECT-TESTDATA OPTIONS, COMMANDS, CONFIGURATION, COPYRIGHT, DESCRIPTION, ENVIRONMENT, EXIT STATUS (+7 more)

### Community 72 - "_check_sample_series"
Cohesion: 0.20
Nodes (12): _check_cross_metric_disk_consistency(), _check_sample_series(), Finding, format_cross_metric_finding(), One line of ``verify-metrics`` output. ``level`` is info/warning/error., Builds :func:`_check_cross_metric_disk_consistency`'s one finding shape from a…, Flags a disk reported by *some* of the six configured metrics but not others --…, Section 3.3 step 2/3/4: one sample series per metric, with its labels. (+4 more)

### Community 73 - "compute_reserve_status"
Cohesion: 0.05
Nodes (88): dataclasses, Any, _render_show_load_json(), _render_verify_storages_human(), _render_verify_storages_json(), _source_suffix(), Section 6: decide whether to act on a group at all, before the solver runs.…, compute_wipe_duration_seconds() (+80 more)

### Community 74 - "Internals: Building the disk/storage/group model"
Cohesion: 0.20
Nodes (9): Internals: Building the disk/storage/group model, (C2) format eligibility: storage_type/allowed_formats, D: every disk placed, pinned or not, Foreign usage U^ext (unreferenced volumes), Pending-change pin, Per-disk cooldown pin, Pin priority: _pin_reason(), Disk sizes: content authoritative, config fallback (+1 more)

### Community 75 - "fragmentation"
Cohesion: 0.20
Nodes (12): cannot fully consolidate, -v data source: line, `measured load:`, `no moves made: ...` / `closest alternative: ...`, `pinned load ... ; best achievable spread given pins: ...`, `pinned (not movable this run):`, Reading `explain`, The `forecast:` line (+4 more)

### Community 76 - "test_live_transient_check_fails_safe_when_the_live_read_errors"
Cohesion: 0.25
Nodes (8): parametrize, A PVE API error while re-reading the target refuses the move and fails the run…, test_live_transient_check_fails_safe_when_the_live_read_errors(), raise_error(), test_move_charge_bytes_rule(), test_orphan_detection_handles_a_pve_api_error_gracefully(), raise_error(), raise_error()

### Community 77 - "Backtest"
Cohesion: 0.20
Nodes (9): Backtest, _quantile(), One group's backtest: absolute error of each model's predicted p95 of ``[now-W,…, Section 10.2's backtest, comparing against a baseline: fit on ``[now-2W,…, Linear-interpolation quantile, matching ``numpy.percentile``'s default.…, test_backtest_passed_needs_a_holt_winters_error_not_worse_than_the_baseline(), test_holt_winters_quantile_follows_a_rising_trend_above_the_observed_p95(), test_quantile_matches_numpy_percentile_convention() (+1 more)

### Community 78 - "stitch_range_results"
Cohesion: 0.20
Nodes (10): _issue_chunked_range_query(), Any, ``client.range_query()``, issued in ``RANGE_QUERY_CHUNK_SECONDS``-sized sub-…, Merges several ``(start, end, result)`` ``query_range`` captures of the *same*…, stitch_range_results(), The common case: a wide range chunked by…, A repeat capture of the same query (not just adjacent chunks) can carry the…, test_stitch_range_results_dedupes_overlapping_timestamps() (+2 more)

### Community 79 - "test_plan_gate_also_reflects_real_drift_history_from_state_json"
Cohesion: 0.24
Nodes (10): _imbalanced_group_load(), _no_reserve_violation_topology(), Two storages, generously sized -- unlike `_sample_topology()`, no (C4)/(C5)…, san-a all the load, san-b none -- imbalance is 200% of `u*`, far above the…, Baseline for the next test: with no `state.json` at all, `last_load` is `None`,…, The same fixture as above, except `state.json` now records a `last_balance`…, Same drift-suppression scenario as `show-load`'s, through `plan` -- the two…, test_plan_gate_also_reflects_real_drift_history_from_state_json() (+2 more)

### Community 80 - "_exec_group"
Cohesion: 0.24
Nodes (10): _exec_disk(), _exec_group(), _posted_move(), The live transient check charges the converted size from the live `size=`., test_a_converting_move_is_refused_when_the_live_check_finds_no_room(), test_a_live_format_that_differs_from_the_plan_means_replan(), test_format_is_not_sent_when_the_disk_already_has_the_enforced_format(), test_format_is_not_sent_without_enforcement() (+2 more)

### Community 81 - "`migration` — cost, bandwidth and the payback rule"
Cohesion: 0.22
Nodes (9): `migration.account_saferemove_wipe`, `migration.bwlimit_bytes_per_sec`, `migration` — cost, bandwidth and the payback rule, `migration.max_single_move_duration`, `migration.payback_horizon`, `migration.payback_ratio`, `migration.source_load_weight`, `migration.target_load_weight` (+1 more)

### Community 82 - "anonymize.py"
Cohesion: 0.05
Nodes (42): hashlib, hmac, Allowlist-never-denylist anonymization, Diagnostic bundle directory format, collect-testdata diagnostic bundle, HMAC pseudonyms with persisted random salt, Corpus scrub audit, MappingType (+34 more)

### Community 83 - "_fragmented_vms"
Cohesion: 0.67
Nodes (4): _fragmented_vms(), Assignment, Section 3.6: name the actual pinned disk(s) keeping one VM's disks spread…, _render_fragmentation_lines()

### Community 84 - "metrics.py"
Cohesion: 0.09
Nodes (26): BundleError, RangeStepMismatch, ``--replay`` found the requested range query, but at a different step than this…, Exception hierarchy for the project. Every error the tool can raise…, A diagnostic bundle (IMPLEMENTATION_PLAN.md section 16) could not be written or…, Prometheus client, PromQL construction and ``pve-storage-drs verify-metrics``.…, Splits ``vmids`` into fixed-size, sorted, deterministic batches -- the *only*…, vmid_query_batches() (+18 more)

### Community 85 - "json_safe"
Cohesion: 0.22
Nodes (7): LogRecord, json_safe(), One human-readable line per record: ``LEVEL: message``. Deliberately not a…, Replace every non-finite float with ``None``, recursively. Python's JSON…, TextFormatter, test_json_safe_replaces_non_finite_floats_recursively(), test_text_formatter_includes_exception_info()

### Community 87 - "PrometheusClient"
Cohesion: 0.25
Nodes (15): Gigapipe step workaround, Metrics page, Node-scoping selector, PrometheusClient, PromQL builders, Range query chunking, SessionLike protocol, verify_metrics six checks (+7 more)

### Community 88 - "Internals: CLI dispatch and logging"
Cohesion: 0.15
Nodes (13): Internals: CLI dispatch and logging, Global options on top-level parser, Command handlers dispatched via dict, JsonFormatter, Structured logs go to stderr, Log levels, mandatory floor, handler on root, --manual prefers man(1), falls back to in-tree markdown, --manual prefers man(1), falls back to plain text (+5 more)

### Community 89 - "test_units.py"
Cohesion: 0.36
Nodes (8): parametrize, Unit parsing/formatting. See proxmox_storage_drs/units.py., test_format_bytes(), test_format_duration_seconds(), test_parse_duration_seconds_accepts(), test_parse_duration_seconds_rejects(), test_parse_size_bytes_accepts(), test_parse_size_bytes_rejects()

### Community 90 - "._get"
Cohesion: 0.08
Nodes (19): Protocol, decimate_to_configured_step(), _disk_keys_seen(), Any, The inverse of :func:`safe_range_step_seconds`: recover a series at…, The subset of ``requests.Response`` this module relies on., The subset of ``requests.Session`` this module relies on. A structural type…, Issue one request and return the decoded ``data`` field. Typed ``Any`` rather… (+11 more)

### Community 91 - "Safety properties, exit codes, and what this build actually does"
Cohesion: 0.40
Nodes (5): verify-metrics exit status and severity levels, Failure to read ends the run with exit 1, Exit codes, Safety properties, exit codes, and what this build actually does, What is safe, unconditionally

### Community 92 - "_state_from_dict"
Cohesion: 0.33
Nodes (6): Any, Raises on any shape this module does not recognize -- the caller…, _state_from_dict(), _state_to_dict(), Only `schema_version` present -- every other field must default the same way…, test_load_state_tolerates_a_minimal_document()

### Community 93 - "test_state.py"
Cohesion: 0.12
Nodes (23): LastBalance, load_vector_for_group(), _pid_alive(), ``at`` is ``None`` before any run has ever executed a migration -- distinct…, This group's slice of ``last_balance.load_vector``, re-keyed from…, Pure: a new :class:`State` with ``group_name``'s slice of…, Best-effort, used only to make a "still held" log message useful to an operator…, with_recorded_balance() (+15 more)

### Community 94 - "Load model page"
Cohesion: 0.39
Nodes (8): Symbols D S Uext, apply_forecast scaling, compute_disk_load_series, compute_group_load, Coverage rejection, Current-assignment L_s u_s, Idle group T_g zero, Load model page

### Community 95 - "Mapper"
Cohesion: 0.08
Nodes (32): `metrics.labels.vmid`, `proxmox.auth.token_id`, filter_allowed_fields(), Mapper, pseudonym(), Drop every key of ``obj`` not in ``allowed``. The one primitive both the…, ``HMAC-SHA256(salt, kind || "\\0" || value)``, truncated to 8 hex chars.…, The stateful half of anonymization: one instance per bundle capture. ``vmid``… (+24 more)

### Community 96 - "disk_factors"
Cohesion: 0.27
Nodes (13): disk_factors(), ``f_d / h_d`` for every disk that has one: ``f_d`` the Holt-Winters forecast…, _factor_series(), _FixedForecast, MonkeyPatch, 96 hourly samples whose last 24 are ``window_values`` (repeated)., Patches ``holt_winters_quantile`` to a constant so the ratio is exact., test_disk_factors_is_forecast_over_observed_p95() (+5 more)

### Community 97 - "_FakeSession"
Cohesion: 0.24
Nodes (7): _FakeProxmoxApiWithSession, _FakeSession, Any, Confirmed live against a real multi-VM cluster: `requests`'s own default…, A small `read_workers` (or the field's own minimum) must not shrink the pool…, test_apply_connection_pool_size_mounts_an_adapter_sized_to_read_workers(), test_apply_connection_pool_size_never_shrinks_below_the_requests_default()

### Community 98 - "FakeProxmoxResource"
Cohesion: 0.25
Nodes (4): FakeProxmoxResource, FakeQueryResponse, Any, Matches ``metrics._ResponseLike``: ``.status_code`` and ``.json()``.

### Community 99 - "pytest"
Cohesion: 0.18
Nodes (10): fixture, json, logging, pytest, ``auto`` and ``text`` -> ``"text"``; ``json`` -> ``"json"``. JSON is opt-in. It…, Logging policy. See IMPLEMENTATION_PLAN.md section 2.3. Every log record goes…, resolve_format(), Shared pytest fixtures. ``logging`` is process-global state, and… (+2 more)

### Community 100 - "25-show-load-and-verify-storages.md"
Cohesion: 0.32
Nodes (7): A negative `saferemove_throughput` is normal, Group ACT/NO ACTION gate line, Negative saferemove_throughput is normal, Reading `show-load` and `verify-storages`, `show-load`, The `Group <name> → ACT`/`NO ACTION` line, `verify-storages`

### Community 101 - "MoveCost"
Cohesion: 0.18
Nodes (10): MoveCost, Section 7.1's cost for one already-scheduled move., REVIEW.md R-05: an economic failure (benefit < ratio*cost) and a hard per-move…, test_render_plan_payback_lines_separates_economic_and_duration_failures(), make_result(), Section 9.1: the pre-loop time-window check (above) only knows the answer as of…, REVIEW.md T-06's collateral bug: before the fix, this "skipped" outcome let the…, test_deadline_recheck_after_a_lock_wait_refuses_a_move_that_no_longer_fits() (+2 more)

### Community 102 - "README.md"
Cohesion: 0.08
Nodes (32): .agents/ index, Git workflow (.agents), Branch first, decided from the task, Merge --no-ff on green make check, Release process (version, changelog, tag, graphify), Packaging, dependencies and CI (.agents), Autopkgtest as the dependency test, coinor-cbc and python3-pulp as Depends (+24 more)

### Community 104 - "excess_of"
Cohesion: 0.25
Nodes (8): excess_of(), footprint_on(), peak_footprint(), Section 5.3.3's ``F_{v,s}``: the sum of VM ``vmid``'s disks on ``s`` -- every…, ``max_s F_{v,s}`` -- the peak share of one VM any single storage holds., Section 5.3.3 (C9): ``O = sum_{v in V^split} o_v`` in TiB, ``o_v = max(0,…, Section 8.1: the snapshot term's basis while ``key`` mirrors onto ``b``,…, transient_basis()

### Community 105 - "save_locked_state"
Cohesion: 0.19
Nodes (17): Inflight UPIDs written and read for crash recovery, Rename-detaches-flock bug and in-place locked write, Write UPID to disk before the crash can happen, _make_inflight_callbacks(), on_finished(), on_started(), Builds the ``on_inflight_started``/``on_inflight_finished`` pair…, LockHandle (+9 more)

### Community 106 - "Payback page"
Cohesion: 0.52
Nodes (7): compute_move_cost, Mirror duration bwlimit, Payback page, Payback verdict, _plan_group wiring, Reserve-override exemption, Wipe duration magnitude

### Community 107 - "free_space requirement soft_s / hard_s"
Cohesion: 0.28
Nodes (9): Failure modes and safety table, free_space requirement soft_s / hard_s, free-space repair fixture, free_space grammar (bytes, unit string, N%) and precedence, Free-space repair mandate fixture, Free-space repair mandate, Plan-level repair exemption and revert test, Overarching rule: reserve never traded against balance (+1 more)

### Community 108 - "Payback rule and acceptance test"
Cohesion: 0.13
Nodes (25): Affinity repair under payback fixture, beta term: number of migrations, bwlimit is the only throttle (saturation guard removed), C7 Capacity-spread linearization, (C8) Small disks follow their VM, Data spread as tunable delta preference, delta term: data spread / failure risk, Even data spread as second priority (+17 more)

### Community 109 - "28-apply.md"
Cohesion: 0.29
Nodes (6): Salted pseudonym anonymization, Bundle layout and manifest, collect-testdata command, Submitting a bundle to the corpus, --estimate and support.max_series_points refusal, --replay offline mode

### Community 110 - "Load model (average in-flight I/O)"
Cohesion: 0.19
Nodes (14): Storage capability weight and utilization u_s, Drift gate (L1 norm, default 0.10), Forecast scales l_d by f_d/h_d, Holt-Winters forecasting and backtest gate, gigapipe step >= range workaround, Holt-Winters p95 forecast with backtest gate, Average in-flight I/O requests unit, Load model (average in-flight I/O) (+6 more)

### Community 111 - "E_of"
Cohesion: 0.29
Nodes (7): E_of(), ratio(), A disk's storage under `assign` -- `assign` only ever has entries for movable…, Section 5.3 (C8), written out independently of the engine's…, Section 5.3 (C6) L1 spread, Sum_s |u_s - u*|., small_disks_follow(), storage_of()

### Community 112 - "Monitoring status file"
Cohesion: 0.40
Nodes (6): Monitoring status file (statusfile.py), `monitoring` — telling your monitoring system what the last run did, check_statusfile Nagios plugin (monitoring-plugins-contrib), Status file freshness by mtime, Monitoring status file, Structured JSON logging and event catalogue

### Community 113 - "check_paper_log.py"
Cohesion: 0.28
Nodes (8): argparse, sys, check(), _logical_lines(), main(), Path, Undo the log's hard wrap at 79 columns. TeX breaks log lines mid-message, which…, Fail the paper build on LaTeX problems that silently damage the PDF. `lualatex`…

### Community 114 - "execute.py"
Cohesion: 0.05
Nodes (99): ExcludeConfig, _active_task_on_vm(), _advance_pending(), _auto_budget_stop_outcome(), _check_lock_once(), Clock, _confirm_decision(), _deadline_exceeded() (+91 more)

### Community 115 - "Gates page"
Cohesion: 0.53
Nodes (6): Cooldowns not in gates, Drift gate, evaluate_group_gates, Gates page, last_load state, Reserve override gate

### Community 116 - "`groups` — storage groups"
Cohesion: 0.33
Nodes (6): `groups[].name`, `groups` — storage groups, `groups[].storages[].capability_weight`, `groups[].storages[].free_space.soft` / `groups[].storages[].free_space.hard`, `groups[].storages[].id`, `groups[].storages[].reserve_factor`

### Community 117 - "`load_weights` — combining read/write and time/ops/bytes"
Cohesion: 0.33
Nodes (6): `load_weights.bytes`, `load_weights` — combining read/write and time/ops/bytes, `load_weights.iotime`, `load_weights.ops`, `load_weights.read_factor`, `load_weights.write_factor`

### Community 118 - "Logging: what lands where, and what an unattended run records"
Cohesion: 0.33
Nodes (6): Logging: what lands where, and what an unattended run records, Text or JSON, The decision trail, Unattended runs log this without being asked, Under systemd, Verbosity

### Community 119 - "split_gate_opens"
Cohesion: 0.33
Nodes (6): eligible_storages(), Section 5.3 (C2): every storage whose `allowed_formats` holds this disk's own…, Section 5.3 (C5)/5.3.1: `R_s = max(f_s * Z_s, soft_s)`., Section 6's split gate, restated independently of ``gates.split_gate()``: some…, reserve_term(), split_gate_opens()

### Community 120 - "collect.py"
Cohesion: 0.05
Nodes (63): functools, gzip, _handle_collect_testdata(), Section 16.4. Always the real clients -- collect-testdata needs a live cluster…, _anonymize_captured_prometheus(), _anonymize_prometheus_series(), _anonymize_query_text(), _build_manifest() (+55 more)

### Community 121 - "`forecast` — placing disks for the load they will have"
Cohesion: 0.40
Nodes (5): `forecast.holt_winters.seasonal`, `forecast.holt_winters.seasonal_periods`, `forecast.holt_winters.trend`, forecast.model (quantile, holt_winters), `forecast` — placing disks for the load they will have

### Community 122 - "AGENTS.md working agreement"
Cohesion: 0.16
Nodes (16): fc-tier1 / reserve-tradeoff acceptance fixtures, AGENTS.md working agreement, AGPL-3.0-or-later licence and SPDX headers, black/flake8 E203 W503 E704 ignores, Branch-first git workflow, 85% coverage floor, Documentation pipeline (make docs / docs-check), make check (+8 more)

### Community 123 - "Decision trail events"
Cohesion: 0.40
Nodes (5): Decision trail events, --log-format text vs json, Report on stdout, log on stderr, Mandatory audit floor for confirm/auto apply, Verbosity flags (--quiet, -v, -vv, --log-level)

### Community 124 - "_anonymized_config_dict"
Cohesion: 0.50
Nodes (4): _anonymize_exclude_disk_key(), _anonymized_config_dict(), Section 16.3's "the configuration in the bundle": credentials and endpoints…, ``"vmid:device"`` -- an ``exclude.disks`` entry (section 16.3), the same shape…

### Community 125 - "`metrics` — Telegraf/InfluxDB name mapping"
Cohesion: 0.15
Nodes (13): `metrics.extra_selector`, `metrics.labels.device`, `metrics.labels.node`, `metrics.pvestatd_push_interval`, `metrics.rate_window`, `metrics.read_bytes`, `metrics.read_ops`, `metrics.read_time_ns` (+5 more)

### Community 127 - "Assignment"
Cohesion: 0.17
Nodes (20): all_assignments(), best_lexicographic(), big_m_agreement_threshold(), F_of(), largest_on(), objective_big_m(), objective_nonreserve(), Assignment (+12 more)

### Community 128 - "Diagnostic bundles: `collect-testdata` and `--replay`"
Cohesion: 0.33
Nodes (5): `collect-testdata`: capturing a bundle, Diagnostic bundles: `collect-testdata` and `--replay`, `--replay`: running against a bundle offline, Sending one to the project, What is in a bundle, and what is not

### Community 131 - "`exclude` — what DRS never touches"
Cohesion: 0.25
Nodes (8): `exclude.disks`, `exclude.include_unused_disks`, `exclude.running_only`, `exclude.skip_vms_with_snapshots`, `exclude.storages`, `exclude.tags`, `exclude.vmids`, `exclude` — what DRS never touches

### Community 148 - "test_enforce_format.py"
Cohesion: 0.10
Nodes (51): needs_cbc, disk_size_on(), qcow2_lvm_allocation_bytes(), Upper bound on the LV ``alloc_image`` creates for a ``qcow2`` volume of…, Section 5.3.2's ``phi(d, s)``: the format ``disk`` would have on ``storage``.…, Section 5.3.2's ``z_{d,s}``, in bytes: what ``disk`` occupies when placed on…, target_format(), tests_unit (+43 more)

### Community 153 - "Configuration page"
Cohesion: 0.43
Nodes (7): Config path resolution order, Configuration page, ResolvedConfig, Secrets from environment, Semantic validation rules, Two-stage validation, Units parsed once

### Community 156 - "test_logging_setup.py"
Cohesion: 0.14
Nodes (18): ast, io, JsonFormatter, Section 2.3's ladder: ``--quiet`` < default < ``-v`` < ``-vv``. ``--log-level``…, Render one :class:`logging.LogRecord` as one JSON line., resolve_level(), parametrize, Section 2.3: "Every log record carries an ``event``" -- the event names are an… (+10 more)

### Community 158 - "proxmox-storage-drs"
Cohesion: 0.40
Nodes (4): Getting the tool, proxmox-storage-drs, The documents, The safety properties to rely on

### Community 159 - "FakeClock"
Cohesion: 0.13
Nodes (21): LocksConfig, FakeClock, log_messages(), LogCaptureFixture, `execution.locks.on_timeout: skip` (the default): the locked head times out…, The reported failure: an earlier move's "Erase data" (imgdel) job still holds…, Section 9.3 point 3: the very race this fix targets -- a `move_disk` task's own…, A `Clock` whose `sleep()` advances its own `now()` instantly. (+13 more)

### Community 163 - "test_manual_falls_back_when_man_exits_nonzero"
Cohesion: 0.40
Nodes (3): test_manual_falls_back_when_man_exits_nonzero(), test_manual_flag_uses_man_when_available(), fake_run()

### Community 164 - "Path"
Cohesion: 0.33
Nodes (9): Any, parametrize, Path, With 64 KiB clusters qcow2 needs an 8-byte L2 and a 2-byte refcount entry per…, test_config_has_no_global_enforce_format(), test_config_parses_enforce_format(), test_config_rejects_a_value_other_than_raw_qcow2_or_null(), test_lvm_qcow2_bound_is_never_below_qemus_default_layout() (+1 more)

### Community 166 - "resolve_node_selector"
Cohesion: 0.12
Nodes (16): node_names uses GET /nodes, build_node_selector(), _escape_promql_regex_literal(), Escape one literal string for safe use inside a PromQL/RE2 ``=~`` alternation.…, Section 3.4's auto-derived node-scoping filter: ``<node_label>=~"n1|n2|..."``…, The one selector every query in this module inserts, resolved once per run…, resolve_node_selector(), A node named `pve1.example.com` must match only that exact string in RE2 -- an… (+8 more)

### Community 169 - "_mapper"
Cohesion: 0.14
Nodes (12): _mapper(), Any, BaseException, _Raise, X-09: `manifest.json`'s `counts.dropped_records` is documented as counting…, A task's ``id`` is the vmid its UPID embeds. It used to be copied raw, leaving…, _tasks_by_kind(), test_anonymize_cluster_tasks_maps_the_task_id_with_the_upid() (+4 more)

### Community 170 - "_FakeClient"
Cohesion: 0.40
Nodes (3): str, _FakeClient, The ``"fake-client"`` sentinel every ``build_pve_client`` mock in this file…

### Community 178 - "Persistent state: state.json"
Cohesion: 0.25
Nodes (8): Persistent state: state.json, Drift history reaches the gates via last_balance, Reading degrades, writing raises, staged_disks field unimplemented, State dataclass tree mirrors section 11.2 JSON, ``"<group>:<storage>"`` (section 11.2)., storage_state_key(), test_storage_state_key_matches_section_11_2_shape()

### Community 185 - "build_rate_promql"
Cohesion: 0.13
Nodes (16): build_quantile_over_time_promql(), build_rate_promql(), _format_promql_duration(), The section 3.4 per-metric rate expression. ``sum by (vmid, device)…, Wrap a rate expression in the section 3.4 quantile-over-time reduction.…, Render a duration as a PromQL range-vector selector, e.g. ``"300s"``. Always in…, _quantile_promql(), The exact PromQL `_fetch_raw_quantity` builds for one raw field -- computed… (+8 more)

### Community 190 - "order_moves"
Cohesion: 0.21
Nodes (14): Internals: Ordering the moves (schedule.py), cost_m tiny_disk_bytes, ScheduleResult.final_assignment, order_moves, Residual violation unexecutable, Schedule page, Transient invariant called with single-move set, Tiny disks (cost_m = 0) scheduled first (+6 more)

### Community 201 - "generate_expected.py"
Cohesion: 0.18
Nodes (16): itertools, cost(), Deadlock, duration(), duration_mirror(), duration_wipe(), load_fixture(), main() (+8 more)

## Knowledge Gaps
- **222 isolated node(s):** `proxmox-storage-drs`, `run-with-system-python.sh script`, `build_paper.sh script`, `build_site.sh script`, `The safety properties to rely on` (+217 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1457 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Group` connect `Group` to `MonkeyPatch`, `build_topology`, `_sample_topology`, `Path`, `test_cli.py`, `test_loadmodel.py`, `run`, `evaluate_assignment`, `topology.py`, `GroupLoad`, `test_payback.py`, `ExecutionResult`, `test_enforce_format.py`, `test_optimize.py`, `run_concurrent`, `test_free_space_repair_fixture.py`, `ExecutionConfig`, `order_moves`, `loadmodel.py`, `cli.py`, `test_large_vm_split_fixture.py`, `build_rate_promql`, `test_affinity_repair_fixture.py`, `test_small_disks.py`, `compute_reserve_status`, `test_plan_gate_also_reflects_real_drift_history_from_state_json`, `_exec_group`, `_fragmented_vms`, `MoveCost`, `execute.py`, `collect.py`?**
  _High betweenness centrality (0.095) - this node is a cross-community bridge._
- **Why does `Persistent state: state.json` connect `Persistent state: state.json` to `empty_state`, `Manual: Configuration reference`, `save_locked_state`, `compute_reserve_status`, `topology.py`, `Overview page`, `Group`, `execute.py`, `loadmodel.py`, `cli.py`, `state.py`, `State`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Why does `Manual: Configuration reference` connect `Manual: Configuration reference` to `Diagnostic bundles: `collect-testdata` and `--replay``, ``forecast` — placing disks for the load they will have`, `25-show-load-and-verify-storages.md`, `README.md`, `fragmentation`, `Configuration reference`, `Monitoring status file`, `Persistent state: state.json`, `Configuration page`, ``metrics` — Telegraf/InfluxDB name mapping`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Are the 214 inferred relationships involving `Group` (e.g. with `_accumulate_move_stats()` and `_apply_payback_gate()`) actually correct?**
  _`Group` has 214 INFERRED edges - model-reasoned connections that need verification._
- **Are the 94 inferred relationships involving `PveClient` (e.g. with `_apply_payback_gate()` and `_pve_client_for()`) actually correct?**
  _`PveClient` has 94 INFERRED edges - model-reasoned connections that need verification._
- **Are the 87 inferred relationships involving `Disk` (e.g. with `_footprint_text()` and `_fragmented_vms()`) actually correct?**
  _`Disk` has 87 INFERRED edges - model-reasoned connections that need verification._
- **What connects `proxmox-storage-drs`, `run-with-system-python.sh script`, `build_paper.sh script` to the rest of the system?**
  _222 weakly-connected nodes found - possible documentation gaps or missing edges._