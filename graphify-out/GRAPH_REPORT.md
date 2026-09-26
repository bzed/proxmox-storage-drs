# Graph Report - proxmox-storage-drs  (2026-09-26)

## Corpus Check
- 84 files · ~300,292 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3701 nodes · 10111 edges · 181 communities (156 shown, 25 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 1361 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- cli: cli.py
- test_cli: CaptureFixture
- cli: _handle_apply()
- test_config: test_config.py
- test_loadmodel: test_loadmodel.py
- test_reserve: Disk
- test_topology: test_topology.py
- metrics: metrics.py
- test_heuristic: Group
- test_gates: GroupLoad
- test_cli: ExecutionResult
- test_metrics: test_metrics.py
- test_cli: _patch_plan_deps()
- topology: topology.py
- test_execute: run()
- test_cli: test_cli.py
- test_payback: Storage
- config: config.py
- execute: execute.py
- pve: PveClient
- test_optimize: test_optimize.py
- test_collect: test_collect.py
- test_validate_corpus: test_validate_corpus.py
- test_execute: ExecutionConfig
- 10-configuration: Configuration reference
- test_statusfile: test_statusfile.py
- optimize: optimize.py
- test_pve: test_pve.py
- AGENTS: AGENTS.md working agreement
- collect: collect.py
- test_schedule: order_moves()
- test_execute: test_execute.py
- test_timewindow: TimeWindow
- exceptions: exceptions.py
- anonymize: anonymize.py
- test_anonymize: test_anonymize.py
- test_loadmodel: MetricsConfig
- test_cli: load_config()
- test_logging_setup: test_logging_setup.py
- test_replay: test_replay.py
- test_state: empty_state()
- 10-configuration: metrics — Telegraf/InfluxDB name mapping
- execute: _launch_decision()
- heuristic: heuristic.py
- collect: capture_bundle()
- state: state.py
- 25-show-load-and-verify-storages: show-load
- test_documentation: test_documentation.py
- test_execute: make_storage()
- test_pve: build_client()
- 27-plan: 28-apply.md
- metrics: ._get()
- 36-monitoring: .agents/ index
- replay: replay.py
- test_forecast: series_of()
- state: crashrecovery.py
- crashrecovery: AuthConfig
- anonymize: Mapper
- pve: pve.py
- generate_expected: case_for()
- test_collect: _instant_answer()
- logging_setup: logging_setup.py
- replay: ReplayPveClient
- test_collect: make_pve_client()
- collect: RecordingPveClient
- test_cli: _patch_forecast_deps()
- test_state: LastBalance
- 29-explain: fragmentation()
- documentation: .agents/documentation.md
- 10-configuration: snapshot_reserve.factor
- IMPLEMENTATION_PLAN: Optimization problem (MILP per group)
- test_forecast: test_forecast.py
- test_state: test_state.py
- check_paper_log: pathlib
- 36-monitoring: Unconditional safety properties
- 10-configuration: execution.abort_on_failure
- test_affinity_repair_fixture: test_affinity_repair_fixture.p
- test_forecast: disk_factors()
- 30-metrics: PrometheusClient
- test_replay: make_config()
- generate_expected: Assignment
- fakes: fakes.py
- 90-heuristic: evaluate_assignment objective
- 28-apply: Reading apply
- forecast: forecast.py
- generate_expected: generate_expected.py
- test_execute: LocksConfig
- test_anonymize: BundleError
- test_state: save_state_atomic()
- test_metrics: build_rate_promql()
- test_loadmodel: _RangeStepMismatchFakeClient
- drs.example: Dry-run is the default
- pve-storage-drs.1: pve-storage-drs.1.md
- topology: parse_pve_config_size_bytes()
- generate_expected: Fixture
- statusfile: statusfile.py
- 20-forecasting: Seven-stage pipeline
- IMPLEMENTATION_PLAN: Execution modes dry-run, confirm, auto
- payback: repair_markers()
- test_topology: _pin_reason()
- test_pve: _FakeSession
- IMPLEMENTATION_PLAN: C5 Capacity, snapshot reserve and free 
- 92-execute: Execute page
- 10-configuration: migration.account_saferemove_wipe
- 10-configuration: proxmox — the cluster API connection
- collect: _anonymize_captured_prometheus()
- execute: _poll_move_once()
- test_metrics: stitch_range_results()
- generate_expected: objective_nonreserve()
- test_cli: _no_reserve_violation_topology()
- IMPLEMENTATION_PLAN: Transient invariant during moves
- 10-configuration: Configuration page
- metrics: build_node_selector()
- 60-topology: Topology page
- 26-collect-testdata-and-replay: Bundle layout and manifest
- collect: write_bundle_dir()
- forecast: forecast_group()
- domain-invariants: Domain invariants (.agents)
- 70-loadmodel: compute_group_load
- 40-cli-and-logging: Command handlers dict
- test_topology: pending_disk_reasons()
- 00-installation: Installation and requirements
- 05-metrics-pipeline: The six counters
- 10-configuration: exclude — what DRS never touches
- IMPLEMENTATION_PLAN: move_disk call and task polling
- IMPLEMENTATION_PLAN: Load model l_d (average in-flight I/O)
- forecast: Backtest
- test_logging_setup: JsonFormatter
- test_execute: test_move_charge_bytes_rule()
- state: disk_state_key()
- 80-gates: Gates page
- 91-optimize: CBC via pulp
- 96-payback: Payback page
- IMPLEMENTATION_PLAN: beta term: number of migrations
- IMPLEMENTATION_PLAN: Per-disk and per-storage cooldowns
- IMPLEMENTATION_PLAN: free_space requirement soft_s / hard_s
- execute: parse_disk_spec()
- test_loadmodel: apply_forecast()
- test_execute: status_current()
- 10-configuration: gates — deciding whether to act at all
- 10-configuration: groups — storage groups
- 35-logging: Text or JSON
- test_metrics: _check_cross_metric_disk_consistency()
- payback: MoveCost
- 10-configuration: prometheus — the metrics source
- 26-collect-testdata-and-replay: collect-testdata: capturing 
- filters: filters.lua
- conftest: conftest.py
- IMPLEMENTATION_PLAN: CBC via PuLP (only MILP backend)
- IMPLEMENTATION_PLAN: verify-metrics command
- anonymize: _check_no_pseudonym_collision()
- cli: _apply_payback_gate()
- test_collect: pseudonym()
- test_anonymize: test_generate_new_salt_rotates_the_mapping()
- cli: show_manual()
- test_forecast: fit()
- test_forecast: fit()
- test_pve: _FakeHttpsBackend
- anonymize: .register_vmids()
- loadmodel: _is_metrics_expected_absent()
- generate_expected: Deadlock
- import-all: import-all
- 10-configuration: Lock timeout skip vs abort
- 36-monitoring: Atomic write and non-fatal write failure
- run-with-system-python: run-with-system-python.sh
- test_anonymize: test_mapper_post_init_computes_time_offset()
- test_anonymize: test_anonymize
- test_cli: test_cli
- test_payback: test_payback
- build_paper: build_paper.sh
- IMPLEMENTATION_PLAN: Plan output and explain narration
- misc: importlib
- pyproject: proxmox-storage-drs
- misc: proxmox_storage_drs
- misc: misc
- misc: misc
- misc: misc
- misc: needs_full_checkout

## God Nodes (most connected - your core abstractions)
1. `Group` - 195 edges
2. `write_config()` - 78 edges
3. `Disk` - 74 edges
4. `PrometheusClient` - 73 edges
5. `run()` - 72 edges
6. `client_with()` - 70 edges
7. `build_topology()` - 69 edges
8. `make_move()` - 69 edges
9. `PveClient` - 67 edges
10. `GroupLoad` - 57 edges

## Surprising Connections (you probably didn't know these)
- `What is in the file` --references--> `duration()`  [INFERRED]
  docs/manual/36-monitoring.md → tests/fixtures/generate_expected.py
- `The `Group <name> → ACT`/`NO ACTION` line` --references--> `GroupLoad`  [INFERRED]
  docs/manual/25-show-load-and-verify-storages.md → src/proxmox_storage_drs/loadmodel.py
- `Single reauthenticate-and-retry in _call` --references--> `PveClient`  [EXTRACTED]
  docs/internals/50-pve-api.md → src/proxmox_storage_drs/pve.py
- `staged_disks field unimplemented` --references--> `State`  [EXTRACTED]
  docs/internals/15-state.md → src/proxmox_storage_drs/state.py
- `The `payback:` line` --references--> `cost()`  [INFERRED]
  docs/manual/27-plan.md → tests/fixtures/generate_expected.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Generated artefacts kept honest by stamps and tests** — _agents_paper_sha256_stamp, _agents_documentation_doc_tests [INFERRED 0.85]
- **Reserve safety mechanism across plan, gate and execution** — implementation_plan_snapshot_reserve, implementation_plan_free_space, implementation_plan_c5_reserve, implementation_plan_lexicographic_solve, implementation_plan_reserve_override, implementation_plan_repair_exemption, implementation_plan_transient_invariant [EXTRACTED 0.95]
- **DRS engine pipeline: gate, solve, payback, order, execute** — implementation_plan_gating, implementation_plan_milp, implementation_plan_payback_acceptance, implementation_plan_scheduling, implementation_plan_exec_modes, implementation_plan_state_json [EXTRACTED 0.95]
- **Diagnostic bundle capture, anonymize, replay, audit** — implementation_plan_collect_testdata, implementation_plan_anon_allowlist, implementation_plan_pseudonym_salt, implementation_plan_bundle, implementation_plan_replay, implementation_plan_corpus, implementation_plan_scrub_audit [EXTRACTED 0.95]
- **Generated acceptance fixtures for the plan** — tests_fixtures_fc_tier1_fixture, tests_fixtures_reserve_tradeoff_fixture, tests_fixtures_free_space_repair_fixture, tests_fixtures_affinity_repair_fixture [EXTRACTED 1.00]
- **CI and quality gates enforcing the make check loop** — github_workflows_tests_tests_workflow, github_workflows_debian_package_debian_package_workflow, debian_gitlab_ci_salsa_ci_pipeline, pre_commit_config_pre_commit_hooks, codecov_yml_codecov_config [INFERRED 0.85]
- **Safety invariants that must not be optimised away** — agents_domain_invariants_snapshot_reserve, implementation_plan_three_floors, implementation_plan_transient_invariant, agents_domain_invariants_finished_task_not_finished_move, agents_domain_invariants_never_auto_delete, agents_domain_invariants_dry_run_default [EXTRACTED 1.00]
- **Gate, solve, order, cost planning pipeline** — docs_internals_80_gates_evaluate_group_gates, docs_internals_90_heuristic_evaluate_assignment_objective, docs_internals_95_schedule_order_moves, docs_internals_96_payback_payback_verdict [EXTRACTED 0.95]
- **Move completion safety checks** — docs_internals_92_execute_four_condition_done, docs_internals_92_execute_vm_locks_waited_out, docs_internals_92_execute_orphans_reported_never_deleted, docs_internals_92_execute_live_transient_check_provisioned [EXTRACTED 0.95]
- **Snapshot reserve, free_space.soft and free_space.hard floors** — docs_manual_10_configuration_snapshot_reserve_factor, docs_manual_10_configuration_free_space, docs_manual_27_plan_transient_reserve_invariant [INFERRED 0.85]
- **Gate evaluation order for act/no-act verdict** — docs_manual_25_show_load_and_verify_storages_gate_order, docs_manual_25_show_load_and_verify_storages_capacity_gate, docs_manual_10_configuration_gates, docs_manual_28_apply_state_json_updates [INFERRED 0.75]
- **Move completion: task OK, source released, VM unlocked** — docs_manual_28_apply_move_done_definition, docs_manual_28_apply_draining, docs_manual_10_configuration_source_release, docs_manual_10_configuration_locks [INFERRED 0.85]

## Communities (181 total, 25 thin omitted)

### Community 0 - "cli: cli.py"
Cohesion: 0.04
Nodes (103): What `plan` does not yet do, What this build actually implements, GateDecision, shutil, _accumulate_move_stats(), _fragmented_vms(), _GroupPlan, _load_per_tib() (+95 more)

### Community 1 - "test_cli: CaptureFixture"
Cohesion: 0.06
Nodes (85): Exception, _fake_build_topology(), _patch_show_load_deps(), _patch_show_load_forecast(), CaptureFixture, MonkeyPatch, `_sample_topology()` with san-b given more headroom (16 TiB instead of 8):…, san-a violates (C5); its only movable disk is 101:scsi0 (102:scsi0 is pinned,… (+77 more)

### Community 2 - "cli: _handle_apply()"
Cohesion: 0.05
Nodes (79): ArgumentParser, CommandHandler, Mutable state box narrow exception to functional style, Startup scan folds excluded vmids before planning, LockHandle, Namespace, _apply_exit_code(), apply_mode_override() (+71 more)

### Community 3 - "test_config: test_config.py"
Cohesion: 0.09
Nodes (68): skipif, minimal_config_dict(), Any, parametrize, Path, The smallest config that passes structural + semantic validation., Config loading, resolution order and section 11.1 semantic validation., There is no ``metrics.labels.cluster`` any more -- an earlier revision's… (+60 more)

### Community 4 - "test_loadmodel: test_loadmodel.py"
Cohesion: 0.08
Nodes (73): LoadWeights, _blend_loads(), compute_disk_load_series(), compute_group_load(), TimeSeries, Section 4's normalize-then-weight-then-rescale blend, given every key's own…, Compute one group's :class:`GroupLoad` for this run. Section 4.…, Section 4's `ℓ_d` blend, as a time series per disk over ``[now - range_seconds,… (+65 more)

### Community 5 - "test_reserve: Disk"
Cohesion: 0.06
Nodes (67): dataclasses, Migration cost and the payback acceptance test. See IMPLEMENTATION_PLAN.md…, compute_reserve_status(), _current_storage(), largest_disk_bytes(), managed_used_bytes(), `Σ_s r_s` at the assignment ``storage_of`` encodes -- section 7.3's outcome…, (C4)/(C5) evaluated for one storage at the assignment ``storage_of`` encodes.… (+59 more)

### Community 6 - "test_topology: test_topology.py"
Cohesion: 0.10
Nodes (71): build_topology(), State, Build the whole cluster's :class:`Topology` for this run. One pass: every read…, build_fake_client(), _cluster_client(), _content(), make_config(), _one_disk_cluster() (+63 more)

### Community 7 - "metrics: metrics.py"
Cohesion: 0.05
Nodes (68): WindowConfig, _combine_raw_values(), _combined_raw(), _fetch_all_raw_quantities(), _fetch_raw_quantity(), _per_disk_lookup(), One of the six section 3.4 raw quantities, quantile-reduced over the decision…, The six section 3.4 series, fetched once and reused for every disk. (+60 more)

### Community 8 - "test_heuristic: Group"
Cohesion: 0.08
Nodes (67): best_single_disk_alternative(), compute_vm_weights(), evaluate_assignment(), _movable_disks(), `D^mov` (section 5.3): disks (C2) has not fixed in place. A pinned disk's…, Section 5.5 step 1: "seed with the current assignment (not from scratch -- we…, Section 5.4's `w_v = max(1, l_v / l_bar)` -- the per-VM weight that scales…, Section 5.4's objective for one candidate ``assignment``.… (+59 more)

### Community 9 - "test_gates: GroupLoad"
Cohesion: 0.06
Nodes (64): GatesConfig, _capacity_spread(), evaluate_group_gates(), GateDecision, _l1_drift(), Section 6, applied in the order it lists: reserve override, then the capacity…, Section 6: decide whether to act on a group at all, before the solver runs.…, One group's act/no-act verdict, section 6, with the reasoning shown (phase 3's… (+56 more)

### Community 10 - "test_cli: ExecutionResult"
Cohesion: 0.07
Nodes (61): ExecutionResult, One group's ``execute_plan()`` call. ``stopped_early`` is true for any reason…, The whole cluster's worth of groups, as seen by this run. By the time anything…, Topology, _fragmented_group(), _make_group_plan(), _moved_outcome(), _one_disk_group() (+53 more)

### Community 11 - "test_metrics: test_metrics.py"
Cohesion: 0.07
Nodes (54): _check_observed_spacing(), PrometheusClient, Thin wrapper over the Prometheus HTTP API. See section 3.4/3.5. ``session`` is…, Section 3.3 step 6: observed sample spacing vs. ``pvestatd_push_interval``.…, _all_metric_names(), FakeResponse, FakeSession, _full_metrics_config() (+46 more)

### Community 12 - "test_cli: _patch_plan_deps()"
Cohesion: 0.07
Nodes (54): _balanced_apply_group_load(), _balanced_apply_topology(), _check_statusfile(), _monitored_config(), _patch_plan_deps(), Two evenly-sized, evenly-loaded disks on one storage, none on the other, no…, Matches `_balanced_apply_topology()`: both disks on san-a, load 5.0 each (200%…, `execute.execute_plan()` itself now dispatches to a concurrent executor once… (+46 more)

### Community 13 - "topology: topology.py"
Cohesion: 0.07
Nodes (55): concurrent_futures, GroupConfig, is_storage_pattern(), A ``storages[].id`` value is a pattern iff it both begins and ends with ``/``…, The regular expression text of a pattern entry, its two ``/`` delimiters…, storage_pattern_text(), StorageConfig, _build_storages() (+47 more)

### Community 14 - "test_execute: run()"
Cohesion: 0.11
Nodes (55): client_with(), default_group(), make_move(), Section 13: `state.json` must learn about a UPID *before* this function goes on…, Not only the happy path -- a `move_disk` task that itself fails still finished…, `dry-run` never calls `move_disk` at all -- the callbacks must simply never…, `ExecutionConfig()`'s own defaults (both caps `1`) must dispatch to the…, IMPLEMENTATION_PLAN.md section 2.1 has always required "every `move_disk`… (+47 more)

### Community 15 - "test_cli: test_cli.py"
Cohesion: 0.04
Nodes (36): str, _balanced_non_violating_topology(), _fake_reconcile_inflight(), _FakeClient, _NodeNamesClient, Every `apply` test here uses `build_pve_client`'s "fake-client" string stand-…, Unlike `_sample_topology()`, san-a here does *not* violate (C5) -- needed to…, On a real Linux host (this project's only packaged target), the result should… (+28 more)

### Community 16 - "test_payback: Storage"
Cohesion: 0.10
Nodes (52): MigrationConfig, compute_benefit_load_seconds(), compute_move_cost(), evaluate_plan_payback(), Section 7.1's cost for one scheduled move. Only ``source`` is needed (not the…, Section 7.2: ``benefit = (alpha*(E_before - E_after) + delta*(F_before -…, Section 7.3: the aggregate acceptance test over a whole plan, plus the hard…, One storage in a group, with the data section 5.3's constraints need. (+44 more)

### Community 17 - "config: config.py"
Cohesion: 0.07
Nodes (51): Configuration file /etc/pve/drs.yaml on pmxcfs, Storage name /regex/ patterns, Validation rules (hard failures), jsonschema, ruamel_yaml, ruamel_yaml_error, _build_config(), _check_connection_config() (+43 more)

### Community 18 - "execute: execute.py"
Cohesion: 0.10
Nodes (50): ExcludeConfig, _advance_pending(), _auto_budget_stop_outcome(), Clock, _confirm_decision(), _deadline_exceeded(), _drained_skip_outcome(), _estimated_duration_seconds() (+42 more)

### Community 19 - "pve: PveClient"
Cohesion: 0.07
Nodes (34): Section 13's startup scan. Returns the vmids to exclude from this run's…, reconcile_inflight(), PveClient, One method per IMPLEMENTATION_PLAN.md section 3.5 endpoint. ``api`` is typed…, Run one ``proxmoxer`` call, wrapping every failure as :class:`PveApiError`.…, ``GET /cluster/resources?type=vm``: VM inventory., ``GET /cluster/tasks``: recent/active tasks across **every** node -- the one…, ``GET /cluster/resources?type=storage``: storage inventory. (+26 more)

### Community 20 - "test_optimize: test_optimize.py"
Cohesion: 0.11
Nodes (48): cbc_available(), make_disk(), make_storage(), LogCaptureFixture, MonkeyPatch, parametrize, Deliberately *not* parametrized over the skip-guarded `BACKENDS` list above --…, Section 5.4's D^big: at beta_move_count=1.0, moving `201:efidisk0` (1 MiB) to… (+40 more)

### Community 21 - "test_collect: test_collect.py"
Cohesion: 0.08
Nodes (44): capture(), _mapper(), Path, X-08: section 16.1's manifest line ("schema, versions, what was captured...")…, X-08: section 16.3 promises the manifest "flags" a non-node-shaped…, Z-03: `resolve_node_selector()`'s tier-1 precedence used to win on *both* sides…, A live capture against the dev cluster found the previous implementation's bug…, verify_metrics() never carries a node selector at all -- nothing to rewrite,… (+36 more)

### Community 22 - "test_validate_corpus: test_validate_corpus.py"
Cohesion: 0.09
Nodes (45): needs_full_checkout, tests_corpus, tests_corpus_validate_corpus, _case(), _invariant_inputs(), MonkeyPatch, parametrize, Path (+37 more)

### Community 23 - "test_execute: ExecutionConfig"
Cohesion: 0.10
Nodes (39): FakeProxmoxResource, ExecutionConfig, concurrent_client_with(), PveClient, REVIEW.md T-06: a lock-timeout `"skipped"` outcome never issued `move_disk`, so…, The defining property of concurrency: `move_disk` for the second move is issued…, Each move's own UPID reaches both callbacks correctly attributed --…, Two otherwise-independent moves landing on the *same* target: even with… (+31 more)

### Community 24 - "10-configuration: Configuration reference"
Cohesion: 0.05
Nodes (42): Configuration reference, `forecast.holt_winters.seasonal`, `forecast.holt_winters.seasonal_periods`, `forecast.holt_winters.trend`, `forecast.model`, `forecast` — placing disks for the load they will have, `free_space.hard`, `free_space` — keep N bytes (or N%) free on top of the snapshot reserve (+34 more)

### Community 25 - "test_statusfile: test_statusfile.py"
Cohesion: 0.13
Nodes (37): CompletedProcess, needs_plugin, build_run_status(), The level policy (section 2.4). ``CRITICAL`` when the run exited non-zero: a…, Write ``status`` to ``path`` atomically, mode 0644, creating the parent…, The status file could not be written., What one ``apply`` run did, as the level policy needs it. ``errors`` are…, RunReport (+29 more)

### Community 26 - "optimize: optimize.py"
Cohesion: 0.10
Nodes (38): ObjectiveConfig, group_average_fill(), group_average_utilization(), `u* = (Sum_d l_d) / (Sum_s c_s)` (C6) -- a constant under any reassignment of…, `b_bar = (Sum_d z_d + Sum_s U^ext) / (Sum_s C_s)` (section 5.3 (C7)) -- a…, _cbc_capacity_spread_term(), _cbc_feasibility_constraints(), _cbc_objective_terms() (+30 more)

### Community 27 - "test_pve: test_pve.py"
Cohesion: 0.10
Nodes (37): PveApiError, The Proxmox VE API returned an error or an unusable response. See…, fake_api(), BaseException, Section 9.2: "convert at the call site and nowhere else" -- this is that site., A ticket that expired for reasons external to this call (a long confirm-mode…, A successful re-login does not guarantee the retried call succeeds -- e.g. the…, The default (and what every other test double in this suite uses): a bare… (+29 more)

### Community 28 - "AGENTS: AGENTS.md working agreement"
Cohesion: 0.07
Nodes (38): Disks with snapshots pinned, Git workflow (.agents), Branch first, decided from the task, Merge --no-ff on green make check, Release process (version, changelog, tag, graphify), Identity, AGPL licence, copyright rules, make check loop, Naming: pve-storage-drs, not drs (+30 more)

### Community 29 - "collect: collect.py"
Cohesion: 0.10
Nodes (36): functools, gzip, Mapper, _anonymize_cluster_tasks(), _anonymize_disk_value(), _anonymize_exclude_disk_key(), _anonymize_node_list(), _anonymize_storage_content() (+28 more)

### Community 30 - "test_schedule: order_moves()"
Cohesion: 0.11
Nodes (36): order_moves(), _pending_moves(), Assignment, Section 8.1's transient invariant, called with the single-move set ``{disk}``…, Section 8.2 priority 1: is ``disk``'s *current* (in ``state``) storage…, Section 8.2's scheduling loop for one group. ``target_assignment`` is normally…, _resolves_reserve_violation(), transient_invariant_ok() (+28 more)

### Community 31 - "test_execute: test_execute.py"
Cohesion: 0.08
Nodes (32): FakeClock, _group_with_types(), datetime, A move missing from `move_costs_by_key` is never refused for lack of an…, 201's mirror target is already *listed* on san-c at its full 1 TiB by the time…, Between different storage types, or from thin to thick, `move_disk` allocates…, The match stays narrow: a same-VM volume that appeared after launch but has…, The exclusion is narrow: only 201's *own* mirror target (same VM, the disk's… (+24 more)

### Community 32 - "test_timewindow: TimeWindow"
Cohesion: 0.15
Nodes (34): date, TimeWindow, current_deadline(), _day_name(), is_window_active(), _parse_hhmm(), datetime, ``execution.time_windows``: when ``auto`` mode may execute moves. See… (+26 more)

### Community 33 - "exceptions: exceptions.py"
Cohesion: 0.09
Nodes (33): ConfigError, DrsError, ExecutionError, MetricsError, Exception, Base class for every error this project raises on purpose., The configuration file is missing, unreadable or fails validation. See…, Prometheus could not be queried, or the response was unusable. See… (+25 more)

### Community 34 - "anonymize: anonymize.py"
Cohesion: 0.07
Nodes (33): hashlib, hmac, Allowlist-never-denylist anonymization, Diagnostic bundle directory format, collect-testdata diagnostic bundle, tests/corpus and scrub audit, Global command-line options, Mode override logging (escalation is a warning) (+25 more)

### Community 35 - "test_anonymize: test_anonymize.py"
Cohesion: 0.09
Nodes (27): make_mapper(), Section 16.3: 'the result never depends on iteration order'., anonymize.py: allowlists, pseudonyms, timestamp rebasing. See…, PVE's own `get_next_vm_diskname()` appends a literal `.<format>` to the volume…, anonymize.py's own UPID split must accept exactly what…, test_node_fqdn_shape_is_preserved(), test_node_pseudonym_shape(), test_rebase_timestamp_is_a_fixed_offset() (+19 more)

### Community 36 - "test_loadmodel: MetricsConfig"
Cohesion: 0.10
Nodes (34): _RawTimeSeries, MetricLabels, MetricsConfig, _fetch_all_raw_quantity_series(), _fetch_raw_quantity_series(), One of the six section 3.4 raw quantities as a raw time series over ``[start,…, _check_device_label_collision(), The one selector every query in this module inserts, resolved once per run… (+26 more)

### Community 37 - "test_cli: load_config()"
Cohesion: 0.08
Nodes (30): load_config(), Resolve, read, parse and validate the configuration. See section 11 for…, Path, Section 13: a vmid `crashrecovery.reconcile_inflight()` reports is folded into…, REVIEW.md R-02: when the scheduler can only order *some* of the heuristic's…, Every real subcommand now has a real handler (``explain`` was the last one) so…, A real, on-disk diagnostic bundle -- built the same way test_collect.py does,…, X-10: `--replay ... --mode auto <cmd>` used to log `run_started` and an… (+22 more)

### Community 38 - "test_logging_setup: test_logging_setup.py"
Cohesion: 0.12
Nodes (31): ast, io, Configure logging for this run and emit ``run_started``. Returns the log format…, _start_logging_and_announce_run(), configure_logging(), floor_for_command(), The mandatory ``INFO`` floor of section 2.3, or ``None``. A run that can change…, Install this run's log handler. Called once, from ``main()``. ``floor`` is… (+23 more)

### Community 39 - "test_replay: test_replay.py"
Cohesion: 0.14
Nodes (30): _config_from_bundle(), _free_space_pairs(), MonkeyPatch, Path, AH-06: a live ``free_space`` config is collected as the resolved per-storage…, Section 16.5's one deliberate exception: a bundle captured before section 3.8…, replay.py: serving a diagnostic bundle through the pve.py/metrics.py interfaces…, The real bug, end to end: ``collect-testdata --step 180`` on a cluster whose… (+22 more)

### Community 40 - "test_state: empty_state()"
Cohesion: 0.15
Nodes (31): flock is the lock; JSON lock field is only a label, acquire_lock(), empty_state(), load_state(), _parse_state_text(), First-run state: no lock, no recorded balance, no cooldowns, nothing in flight…, The tolerant-parse half of :func:`load_state`, factored out so…, Best-effort read of ``path``. See the module docstring: a missing file is the… (+23 more)

### Community 41 - "10-configuration: metrics — Telegraf/InfluxDB name mapping"
Cohesion: 0.07
Nodes (31): gigapipe with ClickHouse (reference backend), PVE InfluxDB external metric server, instance label collision, OpenTelemetry metric server rejected, Other backends, RRD rejected as data source, Six per-disk blockstat counters, Silent counter loss from string fields in line protocol (+23 more)

### Community 42 - "execute: _launch_decision()"
Cohesion: 0.09
Nodes (31): _inflight_onto(), _inflight_target_volids(), _InflightMove, _is_excluded_by_tag_or_vmid(), _is_mirror_target(), _launch_decision(), _LaunchDecision, _live_transient_check() (+23 more)

### Community 43 - "heuristic: heuristic.py"
Cohesion: 0.11
Nodes (26): Disk-cooldown pin is not exempted for reserve repair, Heuristic fallback (seed, repair, descend, polish), Shared feasibility/objective implementation, _RepairCandidate, _best_of(), _best_repair_candidate(), _descend(), storage_of() (+18 more)

### Community 44 - "collect: capture_bundle()"
Cohesion: 0.12
Nodes (25): _handle_collect_testdata(), Section 16.4. Always the real clients -- collect-testdata needs a live cluster…, _render_collect_testdata_human(), _build_manifest(), CallRecord, capture_bundle(), _capture_prometheus_files(), capture_range_seconds() (+17 more)

### Community 45 - "state: state.py"
Cohesion: 0.14
Nodes (28): Cooldown data stored here, interpreted by topology and heuristic, errno, fcntl, socket, _active_cooldowns(), active_disk_cooldowns(), active_storage_cooldowns(), Cooldowns (+20 more)

### Community 46 - "25-show-load-and-verify-storages: show-load"
Cohesion: 0.09
Nodes (27): exclude (vmids, disks, storages, tags, snapshots), free_space.soft and free_space.hard, gates (drift, imbalance, capacity spread, cooldowns), groups[].storages (patterns, capability_weight), Load as average in-flight I/O (Little's law), load_weights blend (iotime, ops, bytes, factors), execution.source_release (wait for source volume gone), A negative `saferemove_throughput` is normal (+19 more)

### Community 47 - "test_documentation: test_documentation.py"
Cohesion: 0.14
Nodes (26): importlib_resources, _flatten_schema_keys(), _load_schema(), _manpage_source_text(), _manual_documented_keys(), Any, needs_full_checkout, parametrize (+18 more)

### Community 48 - "test_execute: make_storage()"
Cohesion: 0.13
Nodes (25): SourceReleaseConfig, make_disk(), make_storage(), Section 9.3: a source_release timeout "does not fail the run: mark the storage…, Same as above, except the second move's *target* -- not source -- is the…, Section 9.3 point 3: PVE's own `saferemove_throughput` (already read live off…, No `saferemove_throughput` configured on the storage (e.g. Ceph RBD or ZFS,…, A "draining" source is no longer tracked by this UPID at all (only by its own… (+17 more)

### Community 49 - "test_pve: build_client()"
Cohesion: 0.12
Nodes (23): The Proxmox VE API client, API token permission is intersection with owner, Best-effort ticket refresh tightening, build_client assembles auth once, bwlimit bytes/s to KiB/s conversion only in move_disk, Single reauthenticate-and-retry in _call, storage_content silently empty without Datastore.Allocate, storage_definitions uses the list form GET /storage (+15 more)

### Community 50 - "27-plan: 28-apply.md"
Cohesion: 0.09
Nodes (21): VM.Config.Disk and VM.Migrate privileges for apply, Never consider over-provisioning (assume_thick_provisioning), execution concurrency limits and max_replans_per_run, execution.time_windows (local host time), Provisioned vs allocated size accounting, Deadlock report (report, never force), Per-group plan pipeline (gate, solve, schedule, payback), Reading a move line (+13 more)

### Community 51 - "metrics: ._get()"
Cohesion: 0.10
Nodes (13): Protocol, _disk_keys_seen(), Any, The subset of ``requests.Response`` this module relies on., The subset of ``requests.Session`` this module relies on. A structural type…, Issue one request and return the decoded ``data`` field. Typed ``Any`` rather…, ``GET /api/v1/query``. Returns the raw ``data.result`` list., ``GET /api/v1/label/<name>/values``. The one endpoint whose ``data`` is a bare… (+5 more)

### Community 52 - "36-monitoring: .agents/ index"
Cohesion: 0.16
Nodes (15): .agents/ index, metrics.* name mapping, support (salt, bundle_dir, max_series_points, capture_range), If it fails, Running it, Verifying your setup, What each finding means, What plan does not yet do (no re-solve-and-shrink, no staging) (+7 more)

### Community 53 - "replay: replay.py"
Cohesion: 0.13
Nodes (17): hash_label_name(), hash_query_text(), _parse_step_param(), The cache key both this module (writing) and ``replay.py`` (reading) derive a…, bundle_reference_now(), load_manifest(), _NeverSession, _parse_step_seconds() (+9 more)

### Community 54 - "test_forecast: series_of()"
Cohesion: 0.13
Nodes (17): HoltWintersConfig, holt_winters_quantile(), ``window.quantile`` of the Holt-Winters forecast path over the next…, Any, The shipped default (288 periods at a 5m step) over the two cycles the lookback…, A diurnal series that *ends at its trough*: the last forecast point (one day…, series_of(), test_backtest_is_none_without_a_fit_half() (+9 more)

### Community 55 - "state: crashrecovery.py"
Cohesion: 0.12
Nodes (20): Persistent state: state.json, Inflight UPIDs written and read for crash recovery, Reading degrades, writing raises, Rename-detaches-flock bug and in-place locked write, staged_disks field unimplemented, Crash and two-instance recovery: crashrecovery.py, Two failure modes, one in-flight UPID mechanism, Write UPID to disk before the crash can happen (+12 more)

### Community 56 - "crashrecovery: AuthConfig"
Cohesion: 0.14
Nodes (21): cluster/tasks vs task_status conventions differ, parse_upid PVE UPID grammar confirmed live, reconcile_inflight: recorded UPIDs plus foreign scan, AuthConfig, expected_task_user(), parse_upid(), The local half of the startup scan: re-checks every UPID ``state.json`` already…, The cluster-wide half: a still-running ``qmmove`` task from this tool's own… (+13 more)

### Community 57 - "anonymize: Mapper"
Cohesion: 0.15
Nodes (11): `metrics.labels.vmid`, `proxmox.auth.token_id`, Mapper, pseudonym(), ``HMAC-SHA256(salt, kind || "\\0" || value)``, truncated to 8 hex chars.…, The stateful half of anonymization: one instance per bundle capture. ``vmid``…, The pseudonym for a vmid already passed to :meth:`register_vmids`. ``None`` for…, ``node-<8 hex>``, or ``node-<8hex>.<8hex>.invalid`` for an FQDN -- shape… (+3 more)

### Community 58 - "pve: pve.py"
Cohesion: 0.13
Nodes (19): proxmoxer client with swappable backends, PVE API read/write path, verify-storages command, proxmoxer, requests, ProxmoxConfig, _apply_connection_pool_size(), _apply_ticket_refresh_seconds() (+11 more)

### Community 59 - "generate_expected: case_for()"
Cohesion: 0.16
Nodes (21): StorageState, best_big_m(), build(), capacity_spread(), case_for(), E_of(), F_of(), moves_of() (+13 more)

### Community 60 - "test_collect: _instant_answer()"
Cohesion: 0.13
Nodes (18): BaseException, _instant_answer(), Any, _Raise, _range_answer(), A live capture against the dev cluster found this one directly (section 16.3's…, A live capture against the dev cluster found this directly:…, A live capture found this the hard way: ``_check_sample_series()``'s "info"… (+10 more)

### Community 61 - "logging_setup: logging_setup.py"
Cohesion: 0.11
Nodes (17): json, LogRecord, json_safe(), One human-readable line per record: ``LEVEL: message``. Deliberately not a…, Section 2.3's ladder: ``--quiet`` < default < ``-v`` < ``-vv``. ``--log-level``…, ``auto`` and ``text`` -> ``"text"``; ``json`` -> ``"json"``. JSON is opt-in. It…, Logging policy. See IMPLEMENTATION_PLAN.md section 2.3. Every log record goes…, Replace every non-finite float with ``None``, recursively. Python's JSON… (+9 more)

### Community 62 - "replay: ReplayPveClient"
Cohesion: 0.22
Nodes (5): Any, PveClient, Unlike every other method here, a missing file is not a bundle defect: a bundle…, Serves ``pve.py``'s eleven read methods from a bundle's ``pve/`` directory.…, ReplayPveClient

### Community 63 - "test_collect: make_pve_client()"
Cohesion: 0.12
Nodes (20): make_prometheus_client(), make_pve_client(), PveClient, --no-series must skip the big, per-group superset range captures -- it does not…, Y-06: the manifest's version fields are machine-generated provenance, not free…, X-09: the printed query count used to treat a multi-day range as one range…, Z-05: a live capture stores every range series at…, Section 3.8/16.3: a real pending edit on the VM's own disk survives as the… (+12 more)

### Community 64 - "collect: RecordingPveClient"
Cohesion: 0.25
Nodes (5): _guarded(), Any, Run ``fn()``, recording its outcome in ``log``. Returns ``None`` (and records…, Wraps a real, already-authenticated :class:`PveClient` and records every call's…, RecordingPveClient

### Community 65 - "test_cli: _patch_forecast_deps()"
Cohesion: 0.14
Nodes (15): _one_disk_group_load(), _patch_forecast_deps(), Any, LogCaptureFixture, The default model must cost nothing extra: no per-disk series fetch., test_apply_mode_override_deescalation_is_info(), test_apply_mode_override_escalation_warns(), test_apply_mode_override_no_change_is_silent() (+7 more)

### Community 66 - "test_state: LastBalance"
Cohesion: 0.14
Nodes (18): Drift history reaches the gates via last_balance, LastBalance, load_vector_for_group(), now_iso(), ``at`` is ``None`` before any run has ever executed a migration -- distinct…, This group's slice of ``last_balance.load_vector``, re-keyed from…, Pure: a new :class:`State` with ``group_name``'s slice of…, UTC, second precision, ``Z`` suffix -- exactly section 11.2's own example… (+10 more)

### Community 67 - "29-explain: fragmentation()"
Cohesion: 0.14
Nodes (16): migration payback (horizon, ratio, cost model), `migration.tiny_disk_bytes`, objective weighted sum (alpha, beta, gamma, kappa, delta), kappa_vm_affinity and pinned-disk counting, payback verdict (benefit vs payback_ratio * cost), Economic vs hard-duration payback failure, `no moves made: ...` / `closest alternative: ...`, objective line: six-term breakdown (+8 more)

### Community 68 - "documentation: .agents/documentation.md"
Cohesion: 0.12
Nodes (14): Config knob entry: type, default, unit, extremes, interactions, Tests keeping docs honest (help covers options, manual covers config), --help generated from argparse definitions, no hardcoded defaults, Internals pages: question first, name modules, explain why, ASCII diagrams, Manpage skeleton with complete OPTIONS, config/drs.example.yaml as documentation that parses, Change behaviour and documentation in the same commit, PDF is a build product; fix text not LaTeX (+6 more)

### Community 69 - "10-configuration: snapshot_reserve.factor"
Cohesion: 0.12
Nodes (17): Debian package install (coinor-cbc, python3-pulp Depends), forecast.model quantile vs holt_winters with backtest gate, objective.reserve_violation_penalty (heuristic only), `snapshot_reserve.count_foreign_volumes`, snapshot_reserve.factor, `snapshot_reserve` — the free-space floor, solver (backend auto/cbc/heuristic, time limit, mip_gap), window (lookback, quantile, min_coverage) (+9 more)

### Community 70 - "IMPLEMENTATION_PLAN: Optimization problem (MILP per group)"
Cohesion: 0.15
Nodes (17): affinity-repair fixture, approximate-size fallback for qcow2-on-LVM volumes, C1 Assignment, C3 VM affinity linking, C6 Load spread (L1 vs min-max), C7 Capacity-spread linearization, Capacity gate (fill fraction spread), delta term: data spread / failure risk (+9 more)

### Community 71 - "test_forecast: test_forecast.py"
Cohesion: 0.19
Nodes (15): random, _group_series(), _noise_series(), TimeSeries, Holt-Winters forecasting, its backtest gate, and the required-range rule., Fewer than 2 * seasonal_periods samples before now - W: Holt-Winters cannot be…, test_backtest_fails_on_white_noise(), test_backtest_hw_error_is_none_when_the_fit_half_is_too_short() (+7 more)

### Community 72 - "test_state: test_state.py"
Cohesion: 0.15
Nodes (16): cooldown_remaining_seconds(), _pid_alive(), Seconds left in ``key``'s cooldown -- ``0.0`` if nothing is recorded for it,…, Best-effort, used only to make a "still held" log message useful to an operator…, Only `schema_version` present -- every other field must default the same way…, Persistent state at ``state.path``. See proxmox_storage_drs/state.py. Every…, A hand-edited or foreign timestamp must degrade to "not in cooldown", not raise…, pid 1 (init) always exists but is not ours to signal as a normal user --… (+8 more)

### Community 73 - "check_paper_log: pathlib"
Cohesion: 0.15
Nodes (12): argparse, pathlib, re, Storage DRS for Proxmox VE 9.2. Balances disk I/O load across configurable…, sys, ``__version__`` and ``pyproject.toml`` must never drift apart., check(), _logical_lines() (+4 more)

### Community 74 - "36-monitoring: Unconditional safety properties"
Cohesion: 0.13
Nodes (16): Configuration on pmxcfs (/etc/pve/drs.yaml), Run the systemd timer on exactly one host, state.json is node-local, not on /etc/pve, `state`, state.path, Move line fields (duration, imbalance delta, l/z), repair_exempt payback exemption, repair move marker (+8 more)

### Community 75 - "10-configuration: execution.abort_on_failure"
Cohesion: 0.12
Nodes (16): `execution.abort_on_failure`, `execution` — how (and whether) moves actually happen, `execution.locks.on_timeout`, `execution.locks.poll_interval`, `execution.locks.task_retry_backoff`, `execution.locks.task_retry_limit`, `execution.locks.wait_timeout`, `execution.max_concurrent_migrations` (+8 more)

### Community 76 - "test_affinity_repair_fixture: test_affinity_repair_fixture.p"
Cohesion: 0.19
Nodes (15): Section 7.2's unweighted ``F`` -- ``sum(d_s)``, always L1 regardless of…, Section 7.2's unweighted (by ``kappa``, but ``w_v``-weighted) ``A`` -- ``Sum_v…, raw_affinity_debt(), raw_capacity_spread(), _affinity_repair_group(), _loads(), _make_disk(), _make_storage() (+7 more)

### Community 77 - "test_forecast: disk_factors()"
Cohesion: 0.25
Nodes (14): Collection, disk_factors(), ``f_d / h_d`` for every disk that has one: ``f_d`` the Holt-Winters forecast…, _factor_series(), _FixedForecast, MonkeyPatch, 96 hourly samples whose last 24 are ``window_values`` (repeated)., Patches ``holt_winters_quantile`` to a constant so the ratio is exact. (+6 more)

### Community 78 - "30-metrics: PrometheusClient"
Cohesion: 0.25
Nodes (15): Gigapipe step workaround, Metrics page, Node-scoping selector, PrometheusClient, PromQL builders, Range query chunking, SessionLike protocol, verify_metrics six checks (+7 more)

### Community 79 - "test_replay: make_config()"
Cohesion: 0.26
Nodes (15): PrometheusConfig, make_config(), _captured_step(), Reconstructs section 3.4's rate expression exactly as a real ``--replay``…, The step a range/subquery capture is actually stored at -- ``make_config()``'s…, A step mismatch is the one BundleError case that carries its own recovery:…, Z-03: a bundle captured with `metrics.extra_selector` set must still replay.…, A light end-to-end sanity check: replayed range data is still valid input to… (+7 more)

### Community 80 - "generate_expected: Assignment"
Cohesion: 0.23
Nodes (15): largest_on(), objective_big_m(), per_storage(), Assignment, A disk's storage under `assign` -- `assign` only ever has entries for movable…, Section 5.3 (C5)/5.3.1: `R_s = max(f_s * Z_s, soft_s)`., Per-storage load, usage and reserve status for one assignment., Total reserve shortfall Sum_s r_s, in TiB. (+7 more)

### Community 81 - "fakes: fakes.py"
Cohesion: 0.19
Nodes (7): FakePrometheusSession, FakeProxmoxResource, FakeQueryResponse, Any, Shared test doubles. Not collected by pytest (no ``test_`` prefix).…, Matches ``metrics._ResponseLike``: ``.status_code`` and ``.json()``., A ``metrics._SessionLike`` double capable of answering *many* distinct queries…

### Community 82 - "90-heuristic: evaluate_assignment objective"
Cohesion: 0.25
Nodes (14): best_single_disk_alternative, Descend swaps and VM relocation, evaluate_assignment objective, Heuristic page, spread_metric, Storage cooldown excludes destination, Unconditional repair, w_v kappa weighting and D big (+6 more)

### Community 83 - "28-apply: Reading apply"
Cohesion: 0.14
Nodes (13): Concurrent execution, Crash and two-instance recovery, Failure and `abort_on_failure`, `--json`, Reading `apply`, Reading `auto` mode, `state.json`: what a real run actually changes, The `[y]es/[n]o skip/[a]ll remaining/[q]uit` prompt (+5 more)

### Community 84 - "forecast: forecast.py"
Cohesion: 0.21
Nodes (13): Backtest gate: beat persistence baseline, Forecasting (quantile vs holt_winters), Holt-Winters seasonal forecast (engine-side), math, ForecastConfig, Holt-Winters load forecasting. See IMPLEMENTATION_PLAN.md sections 10 and 12.1.…, The history ``forecast.model`` needs, in seconds. Called by ``config.py``'s…, required_range_seconds() (+5 more)

### Community 85 - "generate_expected: generate_expected.py"
Cohesion: 0.24
Nodes (13): itertools, cost(), duration(), duration_mirror(), duration_wipe(), load_fixture(), main(), payback() (+5 more)

### Community 86 - "test_execute: LocksConfig"
Cohesion: 0.22
Nodes (13): LocksConfig, log_messages(), LogCaptureFixture, `execution.locks.on_timeout: skip` (the default): the locked head times out…, Section 9.3 point 3: the very race this fix targets -- a `move_disk` task's own…, Crash recovery (section 11.2/13): a retried move is still always exactly one…, Rendered messages of the captured records carrying ``event``., test_concurrent_lock_timeout_with_skip_semantics_continues_to_the_next_move() (+5 more)

### Community 87 - "test_anonymize: BundleError"
Cohesion: 0.16
Nodes (11): BundleError, RangeStepMismatch, A diagnostic bundle (IMPLEMENTATION_PLAN.md section 16) could not be written or…, ``--replay`` found the requested range query, but at a different step than this…, MonkeyPatch, Force two different vmids to hash to the same base slot and confirm both still…, X-09: `vmid`'s own linear probing makes a collision impossible, but nothing did…, test_node_pseudonym_collision_is_refused() (+3 more)

### Community 88 - "test_state: save_state_atomic()"
Cohesion: 0.20
Nodes (14): ``state.path`` could not be written, or its advisory lock could not be…, StateError, LockInfo, Temp file in the same directory, ``fsync``, then ``os.replace`` -- a reader…, Descriptive only -- see the module docstring's "Locking" section for why the…, save_state_atomic(), skipif, The `finally` block's own cleanup, pinned directly rather than only inferred… (+6 more)

### Community 89 - "test_metrics: build_rate_promql()"
Cohesion: 0.14
Nodes (14): build_quantile_over_time_promql(), build_rate_promql(), _format_promql_duration(), The section 3.4 per-metric rate expression. ``sum by (vmid, device)…, Wrap a rate expression in the section 3.4 quantile-over-time reduction.…, Render a duration as a PromQL range-vector selector, e.g. ``"300s"``. Always in…, A 14-day lookback is 1209600s -- ``f"{1209600:g}s"`` renders as…, Section 3.4: the selector goes *inside* `rate()`'s own vector selector, before… (+6 more)

### Community 90 - "test_loadmodel: _RangeStepMismatchFakeClient"
Cohesion: 0.19
Nodes (6): FakeResponse, Any, _RangeStepMismatchFakeClient, A ``range_query`` stand-in that returns caller-supplied data keyed by the exact…, Like ``_StepAwareFakeClient``, but raises ``RangeStepMismatch`` (carrying its…, _WindowTrackingFakeClient

### Community 91 - "drs.example: Dry-run is the default"
Cohesion: 0.18
Nodes (13): Dry-run is the default, Three documentation artefacts (internals, manual, manpage/help), API token auth preferred, secrets from environment, Config lookup order (--config, env, /etc/pve/drs.yaml), Metric name mapping (blockstat), Reference configuration drs.example.yaml, `execution.mode`, Shared pandoc PDF metadata (+5 more)

### Community 92 - "pve-storage-drs.1: pve-storage-drs.1.md"
Cohesion: 0.15
Nodes (12): AUTHOR, COLLECT-TESTDATA OPTIONS, CONFIGURATION, COPYRIGHT, DESCRIPTION, ENVIRONMENT, EXIT STATUS, FILES (+4 more)

### Community 93 - "topology: parse_pve_config_size_bytes()"
Cohesion: 0.15
Nodes (13): _allowed_formats(), _default_format(), parse_pve_config_size_bytes(), Parse a `size=` value from a VM config line, e.g. ``"512G"``. Returns ``None``…, PVE tags as returned by `cluster/resources`: semicolon-separated, with comma…, Section 5.3 (C2): the disk formats ``storage_type`` can hold. An unrecognised…, _split_tags(), parametrize (+5 more)

### Community 94 - "generate_expected: Fixture"
Cohesion: 0.15
Nodes (7): computed_p_min(), Fixture, Section 5.3 (C7): `(Sum_d z_d + Sum_s U^ext) / (Sum_s C_s)` -- the group's mean…, Section 5.4's `D^big` threshold, converted from the fixture's…, Section 5.4's `w_v = max(1, l_v / l_bar)`. `V` (the vmids this returns weights…, The section 5.3 build-time bound: U_obj / eps_r, with eps_r = 1 MiB. The kappa…, One group: its storages, its disks and the weights to solve it with. ``keys``…

### Community 95 - "statusfile: statusfile.py"
Cohesion: 0.18
Nodes (11): contextlib, datetime, os, _one_line(), Collapse any run of whitespace, newlines included, to one space: a newline…, The file's exact text: level, summary ``| perfdata``, details, and a trailing…, The monitoring status file: one ``apply`` run's outcome, in the format the…, A report reduced to the file's content: ``level`` is line 1, ``summary`` line 2… (+3 more)

### Community 96 - "20-forecasting: Seven-stage pipeline"
Cohesion: 0.27
Nodes (12): config.py depends on forecast.py, Module layout, Overview page, Seven-stage pipeline, Two solver backends, Backtest gate, Drift baseline is effective load, Forecast provenance report (+4 more)

### Community 97 - "IMPLEMENTATION_PLAN: Execution modes dry-run, confirm, auto"
Cohesion: 0.17
Nodes (12): Engine pipeline: collect, join, gate, solve, cost, order, execute, Mandatory INFO audit floor for confirm/auto runs, Structured log event catalogue, Execution modes dry-run, confirm, auto, Logging policy (two audiences, levels, audit floor), Implementation phases 1-15, Proxmox Storage DRS Implementation Plan, PVE 9.2 Dynamic Load Balancer (+4 more)

### Community 98 - "payback: repair_markers()"
Cohesion: 0.18
Nodes (10): executed_assignment(), Assignment, Section 7.3: "what it will really run" -- ``final_assignment``…, Section 7.3's revert test, one verdict per scheduled move in ``order``: would…, repair_markers(), Storage `a`: 6 TiB disk on a 10 TiB storage, `reserve_factor=2.0` -- required…, The direct case: the sole move IS what repairs `a`'s violation, so holding it…, _revert_test_group() (+2 more)

### Community 99 - "test_topology: _pin_reason()"
Cohesion: 0.17
Nodes (12): _pin_reason(), Section 5.3 (C2)'s pin conditions, in the order the plan lists them -- the…, Section 5.3 (C2) lists cooldown before the lock check -- both being true at…, Section 5.3 (C2) lists the pending-change pin (section 3.8) before the cooldown…, test_pin_reason_cooldown_is_reported_with_time_remaining(), test_pin_reason_cooldown_wins_over_lock_per_the_plans_own_order(), test_pin_reason_movable(), test_pin_reason_pending_change_wins_over_cooldown() (+4 more)

### Community 100 - "test_pve: _FakeSession"
Cohesion: 0.24
Nodes (8): _FakeProxmoxApiWithSession, _FakeSession, Any, Confirmed live against a real multi-VM cluster: `requests`'s own default…, A small `read_workers` (or the field's own minimum) must not shrink the pool…, test_apply_connection_pool_size_mounts_an_adapter_sized_to_read_workers(), test_apply_connection_pool_size_never_shrinks_below_the_requests_default(), test_build_client_sizes_the_connection_pool_for_token_auth()

### Community 101 - "IMPLEMENTATION_PLAN: C5 Capacity, snapshot reserve and free "
Cohesion: 0.24
Nodes (10): Snapshot reserve never traded for balance, Single-stage big-M penalty P (computed P_min), C4 Largest-disk linearization, C5 Capacity, snapshot reserve and free space, Datastore.Allocate needed for storage content listing, Lexicographic two-stage solve, Snapshot reserve f_s * Z_s (2x largest disk), Never consider over-provisioning (provisioned size only) (+2 more)

### Community 102 - "92-execute: Execute page"
Cohesion: 0.36
Nodes (10): Auto mode time window, Concurrent execution, Execute page, execute_plan live revalidation, Four-condition done, Injectable Clock, Live transient check provisioned, Orphans reported never deleted (+2 more)

### Community 103 - "10-configuration: migration.account_saferemove_wipe"
Cohesion: 0.20
Nodes (10): `migration.account_saferemove_wipe`, `migration.assume_thick_provisioning`, `migration.bwlimit_bytes_per_sec`, `migration` — cost, bandwidth and the payback rule, `migration.max_single_move_duration`, `migration.payback_horizon`, `migration.payback_ratio`, `migration.source_load_weight` (+2 more)

### Community 104 - "10-configuration: proxmox — the cluster API connection"
Cohesion: 0.20
Nodes (10): `proxmox.auth.password`, `proxmox.auth.token_secret`, `proxmox.auth.username`, `proxmox.ca_file`, `proxmox.host`, `proxmox.port`, `proxmox.read_workers`, `proxmox` — the cluster API connection (+2 more)

### Community 105 - "collect: _anonymize_captured_prometheus()"
Cohesion: 0.20
Nodes (10): _anonymize_captured_prometheus(), _anonymize_prometheus_series(), _anonymize_query_text(), _label_kind_for(), _label_value_for(), Rewrites captured PromQL text so it matches what a ``--replay`` run…, Turns every ``(path, params, raw response)`` :class:`RecordingPrometheusClient`…, Merges every ``(start, end, step, result)`` capture for one query text --… (+2 more)

### Community 106 - "execute: _poll_move_once()"
Cohesion: 0.22
Nodes (10): _check_lock_once(), _MoveWaitState, _poll_move_once(), The one live read behind section 9.3.1's lock check: the VM's current…, Section 9.3.1: any non-empty ``lock`` means wait, never whitelist a value…, Carries :func:`_poll_move_once` state across non-blocking poll cycles -- the…, One non-blocking step of section 9.3.2's three-condition completion criterion:…, Section 9.3.2's three-condition completion criterion, blocking until it… (+2 more)

### Community 107 - "test_metrics: stitch_range_results()"
Cohesion: 0.20
Nodes (10): _issue_chunked_range_query(), Any, ``client.range_query()``, issued in ``RANGE_QUERY_CHUNK_SECONDS``-sized sub-…, Merges several ``(start, end, result)`` ``query_range`` captures of the *same*…, stitch_range_results(), The common case: a wide range chunked by…, A repeat capture of the same query (not just adjacent chunks) can carry the…, test_stitch_range_results_dedupes_overlapping_timestamps() (+2 more)

### Community 108 - "generate_expected: objective_nonreserve()"
Cohesion: 0.24
Nodes (10): all_assignments(), best_lexicographic(), big_m_agreement_threshold(), eligible_storages(), objective_nonreserve(), Section 5.3 (C2): every storage whose `allowed_formats` holds this disk's own…, Every eligible placement of the movable disks -- (C2)'s per-disk domain…, The section 5.4 objective without the reserve term. `beta`/`gamma` range over… (+2 more)

### Community 109 - "test_cli: _no_reserve_violation_topology()"
Cohesion: 0.24
Nodes (10): _imbalanced_group_load(), _no_reserve_violation_topology(), Two storages, generously sized -- unlike `_sample_topology()`, no (C4)/(C5)…, san-a all the load, san-b none -- imbalance is 200% of `u*`, far above the…, Baseline for the next test: with no `state.json` at all, `last_load` is `None`,…, The same fixture as above, except `state.json` now records a `last_balance`…, Same drift-suppression scenario as `show-load`'s, through `plan` -- the two…, test_plan_gate_also_reflects_real_drift_history_from_state_json() (+2 more)

### Community 110 - "IMPLEMENTATION_PLAN: Transient invariant during moves"
Cohesion: 0.31
Nodes (9): Higher bar for safety-critical modules, Move completion criterion stronger than task success, Generalized concurrent-move invariant / concurrency_ok, Deadlock and staging moves, Move states mirroring, draining, done, Scheduling algorithm (objective reduction per cost), Three floors precedence f*Z, hard, soft, Transient invariant during moves (+1 more)

### Community 111 - "10-configuration: Configuration page"
Cohesion: 0.31
Nodes (9): Config path resolution order, Configuration page, ResolvedConfig, Secrets from environment, Semantic validation rules, Two-stage validation, Units parsed once, free_space soft hard resolution (+1 more)

### Community 112 - "metrics: build_node_selector()"
Cohesion: 0.22
Nodes (9): node_names uses GET /nodes, build_node_selector(), _escape_promql_regex_literal(), Escape one literal string for safe use inside a PromQL/RE2 ``=~`` alternation.…, Section 3.4's auto-derived node-scoping filter: ``<node_label>=~"n1|n2|..."``…, A node named `pve1.example.com` must match only that exact string in RE2 -- an…, test_build_node_selector_empty_list_is_none(), test_build_node_selector_escapes_dots_in_an_fqdn() (+1 more)

### Community 113 - "60-topology: Topology page"
Cohesion: 0.36
Nodes (9): C2 format eligibility, D means every placed disk, Pending-change pin, Per-disk cooldown pin, Pin priority, Size resolution, Storage pattern expansion, Topology page (+1 more)

### Community 114 - "26-collect-testdata-and-replay: Bundle layout and manifest"
Cohesion: 0.22
Nodes (9): API token privilege separation (intersection of ACLs), PVE credential privileges (Datastore.Audit + Allocate), Snapshot reserve, proxmox.auth (username, password, token), Salted pseudonym anonymization, Bundle layout and manifest, collect-testdata command, Submitting a bundle to the corpus (+1 more)

### Community 115 - "collect: write_bundle_dir()"
Cohesion: 0.22
Nodes (9): Bundle, _dump_json(), Path, Recursively sort every mapping's keys -- section 16.1: "every file is...…, Write ``bundle`` as the canonical directory form (section 16.1): sorted keys,…, A deterministic ``.tar.gz`` of ``dir_path`` (section 16.1): sorted members,…, _sorted_dict(), write_bundle_dir() (+1 more)

### Community 116 - "forecast: forecast_group()"
Cohesion: 0.25
Nodes (9): forecast_group(), group_aggregate_series(), TimeSeries, Sum every disk's own series into one group-aggregate series, at the union of…, One group's forecast: run the backtest on the group aggregate, and only if…, 101:scsi0 has no sample at t=1 at all -- that timestamp still appears (from…, test_group_aggregate_series_empty_input_is_empty(), test_group_aggregate_series_missing_disk_at_a_timestamp_contributes_zero() (+1 more)

### Community 117 - "domain-invariants: Domain invariants (.agents)"
Cohesion: 0.29
Nodes (8): Domain invariants (.agents), Enumerate every disk bus, Finished task is not a finished move, Never auto-delete a volume, Provisioned size, never allocated, VM locks are an open set, IMPLEMENTATION_PLAN.md as specification, Never consider over-provisioning

### Community 118 - "70-loadmodel: compute_group_load"
Cohesion: 0.39
Nodes (8): Symbols D S Uext, apply_forecast scaling, compute_disk_load_series, compute_group_load, Coverage rejection, Current-assignment L_s u_s, Idle group T_g zero, Load model page

### Community 119 - "40-cli-and-logging: Command handlers dict"
Cohesion: 0.39
Nodes (8): CLI and logging page, Command handlers dict, Global options parser, JsonFormatter, Logs to stderr, --manual man fallback, --mode escalation rule, monitoring.status_file

### Community 120 - "test_topology: pending_disk_reasons()"
Cohesion: 0.25
Nodes (8): vm_config returns pending value; vm_pending exposes both, pending_disk_reasons(), Section 3.8: which disk device keys in ``GET .../pending`` (section 3.5's…, A key with only `value` (no `pending`/`delete`) is fully in effect -- the…, test_pending_disk_reasons_flags_a_deletion(), test_pending_disk_reasons_flags_an_edited_disk_key(), test_pending_disk_reasons_ignores_a_key_with_no_divergence(), test_pending_disk_reasons_ignores_non_disk_keys_even_when_pending()

### Community 121 - "00-installation: Installation and requirements"
Cohesion: 0.25
Nodes (8): First steps after installing, Installation and requirements, Installing the package, Running the timer on exactly one host, Setting up the PVE credential, What you need, Where the configuration is *not*, Where the configuration lives

### Community 122 - "05-metrics-pipeline: The six counters"
Cohesion: 0.25
Nodes (8): A reference implementation that is well tested, Telegraf with a Prometheus remote-write output, The failure mode: a transport that cannot carry strings, The six counters, Two things deliberately not used, What catches it, What to do next, Where the numbers come from, and how a transport loses them

### Community 123 - "10-configuration: exclude — what DRS never touches"
Cohesion: 0.25
Nodes (8): `exclude.disks`, `exclude.include_unused_disks`, `exclude.running_only`, `exclude.skip_vms_with_snapshots`, `exclude.storages`, `exclude.tags`, `exclude.vmids`, `exclude` — what DRS never touches

### Community 124 - "IMPLEMENTATION_PLAN: move_disk call and task polling"
Cohesion: 0.36
Nodes (8): C2 Eligibility (variable fixing/pinning), Errors are not mismatches, move_disk call and task polling, Disks with unapplied pending change pinned, Pre-move live re-validation, Disks with snapshots pinned, loudly, Task flock retry (task_retry_limit), VM config lock wait (open-ended lock set)

### Community 125 - "IMPLEMENTATION_PLAN: Load model l_d (average in-flight I/O)"
Cohesion: 0.25
Nodes (8): capability_weight c_s and utilization u_s, Average in-flight I/O requests unit, Load model l_d (average in-flight I/O), Never treat missing data as zero load (min_coverage), Cluster-node scoping of PromQL queries (extra_selector / node regex), PromQL queries and quantile_over_time reduction, read_factor / write_factor asymmetry, gigapipe step >= range workaround (safe_range_step_seconds)

### Community 126 - "forecast: Backtest"
Cohesion: 0.25
Nodes (7): Backtest, _quantile(), One group's backtest: absolute error of each model's predicted p95 of ``[now-W,…, Section 10.2's backtest, comparing against a baseline: fit on ``[now-2W,…, Linear-interpolation quantile, matching ``numpy.percentile``'s default.…, test_quantile_matches_numpy_percentile_convention(), test_quantile_of_empty_sequence_raises()

### Community 127 - "test_logging_setup: JsonFormatter"
Cohesion: 0.25
Nodes (8): JsonFormatter, Render one :class:`logging.LogRecord` as one JSON line., Found live: section 7's payback ratio is `+inf` for any plan with no moves to…, _strict(), test_a_non_finite_extra_still_produces_valid_json(), test_json_formatter_emits_one_parseable_object_per_record(), test_json_formatter_includes_exception_info(), test_json_formatter_includes_extra_fields()

### Community 128 - "test_execute: test_move_charge_bytes_rule()"
Cohesion: 0.25
Nodes (6): parametrize, A PVE API error while re-reading the target refuses the move and fails the run…, test_live_transient_check_fails_safe_when_the_live_read_errors(), test_move_charge_bytes_rule(), test_orphan_detection_handles_a_pve_api_error_gracefully(), raise_error()

### Community 129 - "state: disk_state_key()"
Cohesion: 0.29
Nodes (7): State dataclass tree mirrors section 11.2 JSON, disk_state_key(), ``"<group>:<vmid>:<device>"`` (section 11.2) -- the group prefix is what keeps…, ``"<group>:<storage>"`` (section 11.2)., storage_state_key(), test_disk_state_key_matches_section_11_2_shape(), test_storage_state_key_matches_section_11_2_shape()

### Community 130 - "80-gates: Gates page"
Cohesion: 0.48
Nodes (7): Cooldowns not in gates, Drift gate, evaluate_group_gates, Gates page, last_load state, Reserve override gate, Imbalance gate

### Community 131 - "91-optimize: CBC via pulp"
Cohesion: 0.52
Nodes (7): Backend dispatch cascade, Big-M fallback not implemented, CBC via pulp, CP-SAT removal AL-02, Lexicographic solve, Optimize page, Shared constraint code

### Community 132 - "96-payback: Payback page"
Cohesion: 0.52
Nodes (7): compute_move_cost, Mirror duration bwlimit, Payback page, Payback verdict, _plan_group wiring, Reserve-override exemption, Wipe duration magnitude

### Community 133 - "IMPLEMENTATION_PLAN: beta term: number of migrations"
Cohesion: 0.33
Nodes (7): beta term: number of migrations, bwlimit is the only throttle (saturation guard removed), Migration cost (mirror + saferemove wipe) in load-seconds, Minimal migrations as tunable preference, Payback acceptance test and hard per-move rules, tiny_disk_bytes exemption, Worked example fc-tier1 fixture

### Community 134 - "IMPLEMENTATION_PLAN: Per-disk and per-storage cooldowns"
Cohesion: 0.33
Nodes (7): Per-disk and per-storage cooldowns, Drift gate (L1 norm of load change), Forecast scales l_d by f_d/h_d, Gating (drift, imbalance, capacity, cooldown, reserve override), Re-plan protocol (bounded), saferemove wipe and signed saferemove_throughput, state.json (hysteresis state, cooldowns, lock, inflight UPIDs)

### Community 135 - "IMPLEMENTATION_PLAN: free_space requirement soft_s / hard_s"
Cohesion: 0.38
Nodes (7): Failure modes and safety table, free_space requirement soft_s / hard_s, free-space repair fixture, free_space grammar (bytes, unit string, N%) and precedence, Plan-level repair exemption and revert test, Overarching rule: reserve never traded against balance, Reserve override bypasses gates

### Community 136 - "execute: parse_disk_spec()"
Cohesion: 0.29
Nodes (7): _detect_orphan_volumes(), Section 9.4/domain rule 6: after a failed or cancelled mirror, a target volume…, parse_disk_spec(), Split a VM config disk value into ``(storage_id, volume_name, params)``. E.g.…, test_filter_disk_value_params_drops_iothread_and_discard(), test_parse_disk_spec(), test_parse_disk_spec_no_params()

### Community 137 - "test_loadmodel: apply_forecast()"
Cohesion: 0.43
Nodes (7): apply_forecast(), Section 12.1 point 2: scale each disk's ``l_d`` by its forecast factor ``f_d /…, _forecast_fixture(), test_apply_forecast_leaves_idle_and_no_series_matched_alone(), test_apply_forecast_never_scales_a_flagged_disk_even_if_a_factor_is_given(), test_apply_forecast_scales_only_disks_with_a_factor_and_rebuilds_the_totals(), test_apply_forecast_with_no_factors_is_the_identity()

### Community 138 - "test_execute: status_current()"
Cohesion: 0.29
Nodes (5): Section 9.1: the pre-loop time-window check (above) only knows the answer as of…, REVIEW.md T-06's collateral bug: before the fix, this "skipped" outcome let the…, test_deadline_recheck_after_a_lock_wait_refuses_a_move_that_no_longer_fits(), test_deadline_recheck_after_a_lock_wait_stops_the_whole_run_not_just_this_move(), status_current()

### Community 139 - "10-configuration: gates — deciding whether to act at all"
Cohesion: 0.33
Nodes (6): `gates.capacity_spread_threshold`, `gates.cooldown_per_disk`, `gates.cooldown_per_storage`, `gates` — deciding whether to act at all, `gates.drift_threshold`, `gates.imbalance_threshold`

### Community 140 - "10-configuration: groups — storage groups"
Cohesion: 0.33
Nodes (6): `groups[].name`, `groups` — storage groups, `groups[].storages[].capability_weight`, `groups[].storages[].free_space.soft` / `groups[].storages[].free_space.hard`, `groups[].storages[].id`, `groups[].storages[].reserve_factor`

### Community 141 - "35-logging: Text or JSON"
Cohesion: 0.33
Nodes (6): Logging: what lands where, and what an unattended run records, Text or JSON, The decision trail, Unattended runs log this without being asked, Under systemd, Verbosity

### Community 142 - "test_metrics: _check_cross_metric_disk_consistency()"
Cohesion: 0.33
Nodes (6): _check_cross_metric_disk_consistency(), Flags a disk reported by *some* of the six configured metrics but not others --…, REVIEW.md-worthy real-world failure: Telegraf's Prometheus-compatible output…, test_cross_metric_disk_consistency_silent_when_all_metrics_agree(), test_cross_metric_disk_consistency_truncates_a_long_missing_list(), test_cross_metric_disk_consistency_warns_on_a_dropped_field()

### Community 143 - "payback: MoveCost"
Cohesion: 0.40
Nodes (5): MoveCost, Section 7.1's cost for one already-scheduled move., REVIEW.md R-05: an economic failure (benefit < ratio*cost) and a hard per-move…, test_render_plan_payback_lines_separates_economic_and_duration_failures(), make_result()

### Community 144 - "10-configuration: prometheus — the metrics source"
Cohesion: 0.40
Nodes (5): `prometheus.bearer_token`, `prometheus` — the metrics source, `prometheus.timeout_seconds`, `prometheus.url`, `prometheus.username` / `prometheus.password`

### Community 145 - "26-collect-testdata-and-replay: collect-testdata: capturing "
Cohesion: 0.40
Nodes (5): `collect-testdata`: capturing a bundle, Diagnostic bundles: `collect-testdata` and `--replay`, `--replay`: running against a bundle offline, Sending one to the project, What is in a bundle, and what is not

### Community 147 - "conftest: conftest.py"
Cohesion: 0.40
Nodes (4): fixture, pytest, Shared pytest fixtures. ``logging`` is process-global state, and…, _restore_logging_state()

### Community 148 - "IMPLEMENTATION_PLAN: CBC via PuLP (only MILP backend)"
Cohesion: 0.50
Nodes (5): Autopkgtest install-with-only-Depends check, CP-SAT ortools backend removed (AL-02), Debian-first dependency policy, Debian package and CI pipelines (GitHub Actions, Salsa), CBC via PuLP (only MILP backend)

### Community 149 - "IMPLEMENTATION_PLAN: verify-metrics command"
Cohesion: 0.40
Nodes (5): Per-disk blockstat via pvestatd/InfluxDB/Telegraf/Prometheus, gigapipe on ClickHouse backend, Do not use OpenTelemetry metric server, Do not use RRD, verify-metrics command

### Community 150 - "anonymize: _check_no_pseudonym_collision()"
Cohesion: 0.40
Nodes (4): _check_no_pseudonym_collision(), 32-bit (8 hex char) truncation makes a same-``kind`` collision astronomically…, The single per-bundle offset :meth:`Mapper.rebase_timestamp` applies: the…, week_aligned_offset_seconds()

### Community 151 - "cli: _apply_payback_gate()"
Cohesion: 0.40
Nodes (5): _apply_payback_gate(), ConfirmCallback, Section 7.3's hard per-move duration rule (``rejected_moves``) rendered as…, Section 7.3's payback verdict gates *execution*, not merely the report…, _refused_move_outcomes()

### Community 152 - "test_collect: pseudonym()"
Cohesion: 0.40
Nodes (5): pseudonym(), --replay's build_topology() derives which node to read a shared storage's…, REVIEW.md AA-08(a): investigates whether a storage `cluster/resources` reports…, test_capture_bundle_storage_capture_agrees_with_replays_active_node_pick(), test_capture_pve_storage_files_skips_only_the_storage_whose_node_is_unlisted()

### Community 153 - "test_anonymize: test_generate_new_salt_rotates_the_mapping()"
Cohesion: 0.30
Nodes (5): Path, A node and a storage that happen to share a name must not collide., test_generate_new_salt_rotates_the_mapping(), test_load_or_create_salt_persists_and_is_mode_0600(), test_pseudonym_differs_by_kind_for_same_value()

### Community 154 - "cli: show_manual()"
Cohesion: 0.50
Nodes (4): _fallback_manual_text(), Plain text used only when ``man(1)`` itself is unavailable. A packaged install…, ``--manual`` / ``help``: see AGENTS.md section 8.5., show_manual()

### Community 159 - "loadmodel: _is_metrics_expected_absent()"
Cohesion: 0.67
Nodes (3): _is_metrics_expected_absent(), parametrize, test_is_metrics_expected_absent()

### Community 160 - "generate_expected: Deadlock"
Cohesion: 0.67
Nodes (3): Deadlock, Exception, No move in the plan is individually feasible (section 8.3).

## Knowledge Gaps
- **234 isolated node(s):** ``prometheus.bearer_token``, ``prometheus.timeout_seconds``, ``prometheus.url``, ``prometheus.username` / `prometheus.password``, `build_paper.sh script` (+229 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1323 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **25 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Persistent state: state.json` connect `state: crashrecovery.py` to `cli: cli.py`, `state: disk_state_key()`, `test_state: LastBalance`, `metrics: metrics.py`, `test_state: empty_state()`, `test_gates: GroupLoad`, `heuristic: heuristic.py`, `state: state.py`, `topology: topology.py`, `execute: execute.py`, `36-monitoring: .agents/ index`?**
  _High betweenness centrality (0.155) - this node is a cross-community bridge._
- **Why does `Configuration reference` connect `10-configuration: Configuration reference` to `10-configuration: snapshot_reserve.factor`, `10-configuration: migration.account_saferemove_wipe`, `10-configuration: proxmox — the cluster API connection`, `10-configuration: metrics — Telegraf/InfluxDB name mapping`, `36-monitoring: Unconditional safety properties`, `10-configuration: execution.abort_on_failure`, `10-configuration: groups — storage groups`, `10-configuration: gates — deciding whether to act at all`, `10-configuration: prometheus — the metrics source`, `36-monitoring: .agents/ index`, `10-configuration: exclude — what DRS never touches`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Why does `Group` connect `test_heuristic: Group` to `cli: cli.py`, `test_cli: CaptureFixture`, `cli: _handle_apply()`, `test_loadmodel: test_loadmodel.py`, `test_reserve: Disk`, `test_topology: test_topology.py`, `metrics: metrics.py`, `test_gates: GroupLoad`, `test_loadmodel: apply_forecast()`, `test_cli: ExecutionResult`, `test_cli: _patch_plan_deps()`, `topology: topology.py`, `test_execute: run()`, `test_cli: test_cli.py`, `test_execute: status_current()`, `test_payback: Storage`, `execute: execute.py`, `test_optimize: test_optimize.py`, `cli: _apply_payback_gate()`, `test_execute: ExecutionConfig`, `optimize: optimize.py`, `collect: collect.py`, `test_schedule: order_moves()`, `test_execute: test_execute.py`, `test_cli: load_config()`, `heuristic: heuristic.py`, `collect: capture_bundle()`, `test_execute: make_storage()`, `test_affinity_repair_fixture: test_affinity_repair_fixture.p`, `payback: repair_markers()`, `test_cli: _no_reserve_violation_topology()`?**
  _High betweenness centrality (0.085) - this node is a cross-community bridge._
- **Are the 183 inferred relationships involving `Group` (e.g. with `_accumulate_move_stats()` and `_apply_payback_gate()`) actually correct?**
  _`Group` has 183 INFERRED edges - model-reasoned connections that need verification._
- **What connects ``prometheus.bearer_token``, ``prometheus.timeout_seconds``, ``prometheus.url`` to the rest of the system?**
  _234 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `cli: cli.py` be split into smaller, more focused modules?**
  _Cohesion score 0.03969974979149291 - nodes in this community are weakly interconnected._
- **Should `test_cli: CaptureFixture` be split into smaller, more focused modules?**
  _Cohesion score 0.05750350631136045 - nodes in this community are weakly interconnected._