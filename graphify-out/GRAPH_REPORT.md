# Graph Report - proxmox-storage-drs  (2026-11-27)

## Corpus Check
- 117 files · ~352,017 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 21 file(s) not represented in the graph (top: (none) 12, .sha256 3, .conf 1)

## Summary
- 4076 nodes · 11533 edges · 218 communities (155 shown, 63 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 1666 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `80648bb1`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- execute.py
- test_cli.py
- test_config.py
- seed_assignment
- ExecutionResult
- test_payback.py
- compute_reserve_status
- Path
- test_enforce_format.py
- MonkeyPatch
- GroupLoad
- run
- Disk
- config.py
- optimize.py
- IMPLEMENTATION_PLAN.md
- test_optimize.py
- collect.py
- test_anonymize.py
- Group
- topology.py
- test_validate_corpus.py
- test_replay.py
- test_topology.py
- test_metrics.py
- ExecutionConfig
- capture_bundle
- test_collect.py
- Any
- ObjectiveBreakdown
- PveClient
- evaluate_assignment
- TimeWindow
- anonymize.py
- _sample_topology
- ._call
- test_state.py
- balanced_load
- ResolvedConfig
- Mapper
- Metrics page
- metrics.py
- state.py
- Load model page
- _is_metrics_expected_absent
- test_execute.py
- FakeClock
- run_heuristic
- BundleError
- cli.py
- Reading `apply`
- test_documentation.py
- Mapper
- make_config
- crashrecovery.py
- format_bytes
- Reading `plan`
- _vol
- test_logging_setup.py
- test_small_disks.py
- objective section
- PveApiError
- test_heuristic.py
- ._call_once
- series_of
- test_large_vm_split_fixture.py
- Domain invariants (.agents)
- FakePrometheusSession
- test_pve.py
- docs/internals/90-heuristic.md
- test_schedule.py
- test_statusfile.py
- Assignment
- main
- _handle_apply
- Any
- docs/internals/92-execute.md
- _plan_group
- _ResponseLike
- case_for
- _exec_group
- State
- `execution` — how (and whether) moves actually happen
- test_forecast.py
- generate_expected.py
- disk_factors
- .agents/documentation.md
- forecast.py
- (C7) Capacity-spread linearization (absolute TiB)
- split_gate_opens
- _quantile_promql
- LastBalance
- Reading `explain`
- _redact_finding_message
- Fixture
- test_running_task_on_the_vm_is_waited_out_before_move_disk
- .agents/ index
- forecast_group
- _group_vmid_batches
- test_plan_gate_also_reflects_real_drift_history_from_state_json
- pve-storage-drs manpage
- test_live_transient_check_fails_safe_when_the_live_read_errors
- _apply_connection_pool_size
- _mapper
- AGENTS.md working agreement
- Packaging, dependencies and CI (.agents)
- config/drs.example.yaml
- `metrics` — Telegraf/InfluxDB name mapping
- build_node_selector
- storage_of
- PVE InfluxDB external metric server
- pytest
- test_affinity_repair_fixture.py
- ForecastConfig
- apply_forecast
- Installation and requirements
- `migration` — cost, bandwidth and the payback rule
- apply modes: dry-run, confirm, auto
- empty_state
- fakes.py
- test_no_feasible_solution_says_infeasible_rather_than_blaming_the_time_limit
- _pid_alive
- Migration cost and payback test
- `proxmox` — the cluster API connection
- _render_split_lines
- pathlib
- Configuration reference
- test_solve_returns_none_when_the_library_is_unavailable
- test_plan_reports_an_unfixable_shortfall_and_the_pins_that_block_it
- test_manual_falls_back_when_man_exits_nonzero
- _UnfixableShortfall
- Where the numbers come from, and how a transport loses them
- `exclude` — what DRS never touches
- test_unfixable_shortfall_is_proven_only_for_an_optimal_cbc_solve
- test_task_lock_timeout_retry_drives_inflight_callbacks_for_both_upids
- test_holt_winters_quantile_clamps_at_zero
- test_holt_winters_quantile_forecasts_ceil_window_over_step_steps
- test_holt_winters_quantile_is_none_for_a_non_finite_forecast
- test_objective_offset_is_carried_by_a_variable_fixed_to_one
- Configuration page
- Persistent state: state.json
- docs/internals/00-overview.md
- datetime
- `groups` — storage groups
- `load_weights` — combining read/write and time/ops/bytes
- Safety properties, exit codes, and what this build actually does
- Diagnostic bundles: `collect-testdata` and `--replay`
- Logging: what lands where, and what an unattended run records
- Path
- footprint_on
- `forecast` — placing disks for the load they will have
- `prometheus` — the metrics source
- `solver` — which backend plans
- `support` — diagnostic bundles
- `--json`
- filters.lua
- proxmox-storage-drs
- resolve_level
- _FakeClient
- `snapshot_reserve` — the free-space floor
- `window` — the decision window
- `free_space` — keep N bytes (or N%) free on top of the snapshot reserve
- Dry-run default; apply is the only writing command
- fc-tier1 fixture (plan 14 worked example)
- import-all
- draining status
- run-with-system-python.sh
- build_paper.sh
- build_site.sh
- autopkgtest runtime-dependency check
- GitHub Actions and Salsa GitLab CI pipelines
- Never consider over-provisioning (provisioned size)
- Structured logs go to stderr
- --manual prefers man(1), falls back to in-tree markdown
- 'no moves made' line in plan/apply
- Unfixable-shortfall report
- Deadlock report for residual violations
- ScheduleResult.final_assignment
- Persistent-objective reduction per cost_m ranking
- Transient invariant called with single-move set
- Tiny disks (cost_m = 0) scheduled first
- migration payback settings (payback_horizon, payback_ratio, max_single_move_duration)
- Check 5: per-disk coverage
- Check 3: configured labels present
- Check 6: observed sample spacing
- plan --json groups[] schema
- payback: line (benefit >= payback_ratio * cost)
- payback.repair_exempt
- solver: line (backend actually used)
- Lock timeout skip vs abort
- Shared pandoc PDF metadata
- Affinity repair under payback fixture
- Storage capability weight and utilization u_s
- CP-SAT (ortools) backend, removed
- Execution modes (dry-run default, confirm, auto)
- Holt-Winters forecasting and backtest gate
- Free-space repair mandate fixture
- Free-space repair mandate
- Keyed pseudonyms with salt
- max_single_move_duration hard rule
- Migration benefit over horizon H
- Per-group MILP optimization model
- move_disk (drive-mirror, delete=1)
- Objective (alpha imbalance, beta migrations, gamma bytes, kappa fragmentation, delta spread, P reserve)
- Prometheus per-disk blockstat metrics
- Reserve override
- reserve-tradeoff companion fixture
- Shared feasibility and objective functions (evaluate_assignment)
- Deadlock resolution and staging moves
- Storage group
- Storage name patterns /…/ in groups
- Provisioned-size (thick) accounting
- importlib
- proxmox-storage-drs

## God Nodes (most connected - your core abstractions)
1. `Group` - 200 edges
2. `PveClient` - 122 edges
3. `Disk` - 84 edges
4. `run()` - 84 edges
5. `write_config()` - 83 edges
6. `make_move()` - 81 edges
7. `client_with()` - 80 edges
8. `build_topology()` - 75 edges
9. `PrometheusClient` - 70 edges
10. `fake_api()` - 69 edges

## Surprising Connections (you probably didn't know these)
- `The `Group <name> → ACT`/`NO ACTION` line` --references--> `GroupLoad`  [INFERRED]
  docs/manual/25-show-load-and-verify-storages.md → src/proxmox_storage_drs/loadmodel.py
- `What is in the file` --references--> `duration()`  [INFERRED]
  docs/manual/36-monitoring.md → tests/fixtures/generate_expected.py
- `The `objective:` line` --references--> `ObjectiveBreakdown`  [INFERRED]
  docs/manual/29-explain.md → src/proxmox_storage_drs/heuristic.py
- `What this build actually implements` --references--> `ObjectiveBreakdown`  [INFERRED]
  docs/manual/30-safety-and-status.md → src/proxmox_storage_drs/heuristic.py
- `What `plan` does not yet do` --references--> `evaluate_assignment()`  [INFERRED]
  docs/manual/27-plan.md → src/proxmox_storage_drs/heuristic.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Safety invariants that must not be optimised away** — agents_domain_invariants_snapshot_reserve, implementation_plan_transient_invariant, agents_domain_invariants_finished_task_not_finished_move, agents_domain_invariants_never_auto_delete, agents_domain_invariants_dry_run_default [EXTRACTED 1.00]
- **Domain safety invariants that must not be optimised away** — agents_domain_invariants_dry_run_default, agents_domain_invariants_snapshot_reserve, agents_three_floors_precedence, implementation_plan_transient_invariant, agents_finished_task_not_finished_move, agents_domain_invariants_never_auto_delete, agents_never_overprovision [EXTRACTED 1.00]
- **Execution safety chain** — docs_internals_92_execute_revalidate, docs_internals_92_execute_done4, docs_internals_92_execute_locks, docs_internals_92_execute_orphans, implementation_plan_transient [INFERRED 0.75]
- **Absolute-TiB capacity spread implementation** — implementation_plan_c7_capacity_spread, implementation_plan_delta, implementation_plan_x_star, docs_internals_90_heuristic_ds_abs, implementation_plan_phase18 [INFERRED 0.85]
- **CI and quality gates enforcing the make check loop** — github_workflows_tests_tests_workflow, github_workflows_debian_package_debian_package_workflow, debian_gitlab_ci_salsa_ci_pipeline, pre_commit_config_pre_commit_hooks, codecov_yml_codecov_config [INFERRED 0.85]
- **Plan section 14 fixtures** — tests_fixtures_fc_tier1_doc, tests_fixtures_affinity_repair_doc, tests_fixtures_free_space_repair_doc, tests_fixtures_large_vm_split_doc, tests_fixtures_reserve_tradeoff_doc [INFERRED 0.85]
- **Generated artefacts kept honest by stamps and tests** — _agents_paper_sha256_stamp, _agents_documentation_doc_tests [INFERRED 0.85]
- **Move completion: task OK, source released, VM unlocked** — docs_manual_28_apply_move_done_definition, docs_manual_28_apply_draining [INFERRED 0.85]
- **Payback benefit terms** — docs_internals_96_payback_benefit, docs_manual_10_configuration_objective_alpha_spread, docs_manual_10_configuration_objective_delta_capacity_spread, docs_manual_10_configuration_objective_kappa_vm_affinity, docs_manual_10_configuration_mu [INFERRED 0.85]
- **Debian packaging, CI and release chain** — agents_autopkgtest, agents_ci_pipelines, agents_release_procedure [INFERRED 0.85]
- **Shared objective across MILP and heuristic** — docs_internals_90_heuristic_evaluate, docs_internals_91_optimize_cbc, docs_internals_91_optimize_shared, implementation_plan_objective [INFERRED 0.85]

## Communities (218 total, 63 thin omitted)

### Community 0 - "execute.py"
Cohesion: 0.05
Nodes (97): Write UPID to disk before the crash can happen, ExcludeConfig, _active_task_on_vm(), _advance_pending(), _auto_budget_stop_outcome(), _check_lock_once(), Clock, _confirm_decision() (+89 more)

### Community 1 - "test_cli.py"
Cohesion: 0.03
Nodes (72): _balanced_non_violating_topology(), _breakdown_with_split(), _gate(), _no_move_schedule(), _NodeNamesClient, _one_disk_group_load(), _outcome(), _patch_forecast_deps() (+64 more)

### Community 2 - "test_config.py"
Cohesion: 0.07
Nodes (90): ConfigError, The configuration file is missing, unreadable or fails validation. See…, minimal_config_dict(), Any, parametrize, Path, skipif, The smallest config that passes structural + semantic validation. (+82 more)

### Community 3 - "seed_assignment"
Cohesion: 0.08
Nodes (42): Section 5.5 step 1: "seed with the current assignment (not from scratch -- we…, seed_assignment(), _large_vm_group(), storage(), make_disk(), make_storage(), parametrize, Section 5.4: "l_v ... pinned disks included -- their I/O is the VM's I/O",… (+34 more)

### Community 4 - "ExecutionResult"
Cohesion: 0.06
Nodes (68): ExecutionResult, One group's ``execute_plan()`` call. ``stopped_early`` is true for any reason…, The whole cluster's worth of groups, as seen by this run. By the time anything…, Topology, _fragmented_group(), _make_group_plan(), _moved_outcome(), _one_disk_group() (+60 more)

### Community 5 - "test_payback.py"
Cohesion: 0.06
Nodes (71): MigrationConfig, compute_benefit_load_seconds(), compute_move_cost(), evaluate_plan_payback(), executed_assignment(), Assignment, Section 7.1's cost for one scheduled move. Only ``source`` is needed (not the…, Section 7.2: ``benefit = (alpha*(E_before - E_after) + delta*(F_before -… (+63 more)

### Community 6 - "compute_reserve_status"
Cohesion: 0.07
Nodes (52): compute_reserve_status(), (C4)/(C5) evaluated for one storage at the assignment ``storage_of`` encodes.…, ``size_bytes`` rounded *up* to the next whole MiB, in bytes. Up, never to…, round_up_to_mib(), _each_own_vm(), make_disk(), make_storage(), parametrize (+44 more)

### Community 7 - "Path"
Cohesion: 0.06
Nodes (72): load_config(), Apply the section 11 resolution order. Returns ``(path, was_explicit)``.…, Resolve, read, parse and validate the configuration. See section 11 for…, resolve_config_path(), _patch_show_load_deps(), _patch_show_load_forecast(), CaptureFixture, Exception (+64 more)

### Community 8 - "test_enforce_format.py"
Cohesion: 0.08
Nodes (59): needs_cbc, disk_size_on(), qcow2_lvm_allocation_bytes(), Upper bound on the LV ``alloc_image`` creates for a ``qcow2`` volume of…, Section 5.3.2's ``phi(d, s)``: the format ``disk`` would have on ``storage``.…, Section 5.3.2's ``z_{d,s}``, in bytes: what ``disk`` occupies when placed on…, target_format(), tests_unit (+51 more)

### Community 9 - "MonkeyPatch"
Cohesion: 0.09
Nodes (53): _balanced_apply_group_load(), _balanced_apply_topology(), _check_statusfile(), _monitored_config(), _patch_plan_deps(), MonkeyPatch, Two evenly-sized, evenly-loaded disks on one storage, none on the other, no…, Matches `_balanced_apply_topology()`: both disks on san-a, load 5.0 each (200%… (+45 more)

### Community 10 - "GroupLoad"
Cohesion: 0.08
Nodes (57): GatesConfig, _capacity_spread(), evaluate_group_gates(), _l1_drift(), Section 6, applied in the order it lists: reserve override, then the capacity…, ``(‖ℓ_last‖₁, ‖ℓ_now − ℓ_last‖₁)`` over the **union** of disk keys present in…, Section 5.3 (C7)'s `(max_s b_s - min_s b_s) / b_bar`, or ``None`` when the gate…, _aggregate_storages() (+49 more)

### Community 11 - "run"
Cohesion: 0.10
Nodes (60): client_with(), default_group(), make_move(), Fails safe: a volume with neither `size` nor `approximate-size` makes the…, A move missing from `move_costs_by_key` is never refused for lack of an…, Section 13: `state.json` must learn about a UPID *before* this function goes on…, Not only the happy path -- a `move_disk` task that itself fails still finished…, `dry-run` never calls `move_disk` at all -- the callbacks must simply never… (+52 more)

### Community 12 - "Disk"
Cohesion: 0.07
Nodes (58): dataclasses, Section 6: decide whether to act on a group at all, before the solver runs.…, Migration cost and the payback acceptance test. See IMPLEMENTATION_PLAN.md…, _current_storage(), largest_disk_bytes(), largest_footprint(), largest_footprint_bytes(), managed_used_bytes() (+50 more)

### Community 13 - "config.py"
Cohesion: 0.06
Nodes (62): contextlib, jsonschema, re, requests, ruamel_yaml, ruamel_yaml_error, _build_config(), _check_connection_config() (+54 more)

### Community 14 - "optimize.py"
Cohesion: 0.11
Nodes (44): _cbc_capacity_spread_term(), _cbc_feasibility_constraints(), _cbc_objective_terms(), _cbc_small_disks_follow_their_vm(), _cbc_split_excess_term(), _cbc_storage_load(), _cbc_storage_used_mib(), _cbc_vm_footprint() (+36 more)

### Community 15 - "IMPLEMENTATION_PLAN.md"
Cohesion: 0.04
Nodes (55): Anonymization allowlist, never denylist, Big-M penalty P fallback (computed P_min), Migrations throttled by bwlimit only, (C2) Eligibility via variable fixing, (C3) VM affinity linking, (C4) Largest-disk linearization Z_s, (C6) Load spread, (C8) Small disks follow their VM (+47 more)

### Community 16 - "test_optimize.py"
Cohesion: 0.12
Nodes (48): make_disk(), make_storage(), parametrize, Section 5.4's D^big: at beta_move_count=1.0, moving `201:efidisk0` (1 MiB) to…, IMPLEMENTATION_PLAN.md section 14.3's "delta knob, demonstrated at the…, The MILP solver backend. See proxmox_storage_drs/optimize.py. Cross-checked…, REVIEW.md AA-01: the then-CP-SAT backend's (C7) linearization once built `d_s`…, The inverse check: explicitly disabling delta must restore beta's own three-… (+40 more)

### Community 17 - "collect.py"
Cohesion: 0.09
Nodes (27): functools, gzip, Path, proxmox_storage_drs, _anonymize_captured_prometheus(), _anonymize_prometheus_series(), _anonymize_query_text(), Bundle (+19 more)

### Community 18 - "test_anonymize.py"
Cohesion: 0.06
Nodes (42): make_mapper(), MonkeyPatch, parametrize, Path, A node and a storage that happen to share a name must not collide., Section 16.3: 'the result never depends on iteration order'., Force two different vmids to hash to the same base slot and confirm both still…, X-09: `vmid`'s own linear probing makes a collision impossible, but nothing did… (+34 more)

### Community 19 - "Group"
Cohesion: 0.11
Nodes (67): LoadWeights, _blend_loads(), compute_disk_load_series(), compute_group_load(), TimeSeries, Section 4's normalize-then-weight-then-rescale blend, given every key's own…, Compute one group's :class:`GroupLoad` for this run. Section 4.…, Section 4's `ℓ_d` blend, as a time series per disk over ``[now - range_seconds,… (+59 more)

### Community 20 - "topology.py"
Cohesion: 0.06
Nodes (65): concurrent_futures, GroupConfig, is_storage_pattern(), A ``storages[].id`` value is a pattern iff it both begins and ends with ``/``…, The regular expression text of a pattern entry, its two ``/`` delimiters…, storage_pattern_text(), StorageConfig, _allowed_formats() (+57 more)

### Community 21 - "test_validate_corpus.py"
Cohesion: 0.09
Nodes (47): tests_corpus, tests_corpus_validate_corpus, _case(), _invariant_inputs(), MonkeyPatch, needs_full_checkout, parametrize, Path (+39 more)

### Community 22 - "test_replay.py"
Cohesion: 0.11
Nodes (42): PrometheusConfig, _captured_step(), _config_from_bundle(), _free_space_pairs(), MonkeyPatch, Path, AH-06: a live ``free_space`` config is collected as the resolved per-storage…, Section 16.5's one deliberate exception: a bundle captured before section 3.8… (+34 more)

### Community 23 - "test_topology.py"
Cohesion: 0.05
Nodes (115): Disk-cooldown pin is not exempted for reserve repair, The cluster topology could not be built from the API responses. See…, TopologyError, disk_state_key(), ``"<group>:<vmid>:<device>"`` (section 11.2) -- the group prefix is what keeps…, build_topology(), pending_disk_reasons(), _pin_reason() (+107 more)

### Community 24 - "test_metrics.py"
Cohesion: 0.04
Nodes (89): MetricsError, Prometheus could not be queried, or the response was unusable. See…, _issue_chunked_range_query(), Any, ``client.range_query()``, issued in ``RANGE_QUERY_CHUNK_SECONDS``-sized sub-…, _disk_keys_seen(), PrometheusClient, Any (+81 more)

### Community 25 - "ExecutionConfig"
Cohesion: 0.09
Nodes (47): ExecutionConfig, LocksConfig, concurrent_client_with(), log_messages(), LogCaptureFixture, The defining property of concurrency: `move_disk` for the second move is issued…, Each move's own UPID reaches both callbacks correctly attributed --…, Two otherwise-independent moves landing on the *same* target: even with… (+39 more)

### Community 26 - "capture_bundle"
Cohesion: 0.12
Nodes (28): Config, datetime, PrometheusClient, PveClient, ResolvedConfig, _handle_collect_testdata(), Section 16.4. Always the real clients -- collect-testdata needs a live cluster…, _build_manifest() (+20 more)

### Community 27 - "test_collect.py"
Cohesion: 0.09
Nodes (38): capture(), Path, X-08: section 16.1's manifest line ("schema, versions, what was captured...")…, X-08: section 16.3 promises the manifest "flags" a non-node-shaped…, Z-03: `resolve_node_selector()`'s tier-1 precedence used to win on *both* sides…, A live capture against the dev cluster found the previous implementation's bug…, verify_metrics() never carries a node selector at all -- nothing to rewrite,…, Even when the configured model is ``quantile``, the bundle is captured with… (+30 more)

### Community 28 - "Any"
Cohesion: 0.25
Nodes (5): _guarded(), Any, Run ``fn()``, recording its outcome in ``log``. Returns ``None`` (and records…, Wraps a real, already-authenticated :class:`PveClient` and records every call's…, RecordingPveClient

### Community 29 - "ObjectiveBreakdown"
Cohesion: 0.07
Nodes (51): What `plan` does not yet do, _capacity_gate_hint(), _GroupPlan, _load_per_tib(), _log_plan_selected(), _note_forecast(), _objective_breakdown_json(), ``(max_s u_s - min_s u_s) / u*`` -- gates.py's own imbalance formula (section… (+43 more)

### Community 30 - "PveClient"
Cohesion: 0.09
Nodes (49): Section 13's startup scan. Returns the vmids to exclude from this run's…, reconcile_inflight(), PveClient, One method per IMPLEMENTATION_PLAN.md section 3.5 endpoint. ``api`` is typed…, Retry idempotent calls that fail because the API is unreachable for up to…, fake_api(), BaseException, The same in-flight move already recorded in state.json also shows up in the… (+41 more)

### Community 31 - "evaluate_assignment"
Cohesion: 0.11
Nodes (36): _RepairCandidate, active_split_caps(), _best_of(), _best_repair_candidate(), trial_storage_of(), best_single_disk_alternative(), compute_vm_weights(), _descend() (+28 more)

### Community 32 - "TimeWindow"
Cohesion: 0.15
Nodes (34): date, TimeWindow, current_deadline(), _day_name(), is_window_active(), _parse_hhmm(), datetime, ``execution.time_windows``: when ``auto`` mode may execute moves. See… (+26 more)

### Community 33 - "anonymize.py"
Cohesion: 0.07
Nodes (30): hashlib, hmac, MappingType, filter_disk_value_params(), filter_vm_config_fields(), filter_vm_pending_entries(), generate_new_salt(), load_or_create_salt() (+22 more)

### Community 34 - "_sample_topology"
Cohesion: 0.09
Nodes (33): _fake_build_topology(), _fake_reconcile_inflight(), `_sample_topology()` plus a section 11.4 pattern expansion and one cluster…, Every `apply` test here uses `build_pve_client`'s "fake-client" string stand-…, X-05: cli.py used to build one bare topology (for the estimate check) and then…, A ``cli.build_topology`` stand-in that ignores the ``state``/``now`` cooldown…, Section 7.1's signed `saferemove_throughput`, end to end: the configured value…, Section 3.5 / AH-04: the resolved pair is printed with its provenance, in both… (+25 more)

### Community 35 - "._call"
Cohesion: 0.08
Nodes (17): Any, Replace the session after a transport failure, best effort. A TLS handshake…, :meth:`_call_once`, retried while the failure is transient. Only ``idempotent``…, ``GET /cluster/resources?type=vm``: VM inventory., ``GET /cluster/tasks``: recent/active tasks across **every** node -- the one…, ``GET /cluster/resources?type=storage``: storage inventory., ``GET /nodes``: every node in the cluster, by name. Section 3.4's node-scoping…, ``GET /version``: the running PVE's own version string (section 16.1/16.3's… (+9 more)

### Community 36 - "test_state.py"
Cohesion: 0.18
Nodes (28): flock is the lock; JSON lock field is only a label, acquire_lock(), load_state(), LockInfo, Best-effort read of ``path``. See the module docstring: a missing file is the…, Section 11.2's advisory lock: ``fcntl.flock(LOCK_EX | LOCK_NB)`` on ``path``…, Clears the descriptive ``lock`` field and releases the OS-level lock, writing…, Descriptive only -- see the module docstring's "Locking" section for why the… (+20 more)

### Community 37 - "balanced_load"
Cohesion: 0.21
Nodes (15): balanced_load(), fill_reserve_statuses(), make_disk(), make_storage(), Section 14.2's initial byte layout: san-a/b/c used 4.5/1.5/0.5 TiB of 8.0 TiB…, A perfectly I/O-balanced GroupLoad for ``group`` -- so only the capacity gate,…, Section 6: the capacity gate acts even though the group is perfectly…, Section 5.3 (C7): "if b_bar = 0 the group holds no data: the term is inactive"… (+7 more)

### Community 38 - "ResolvedConfig"
Cohesion: 0.11
Nodes (38): CommandHandler, Namespace, _dump_report_json(), _filter_groups(), _handle_explain(), _handle_plan(), _handle_show_load(), _handle_verify_metrics() (+30 more)

### Community 39 - "Mapper"
Cohesion: 0.18
Nodes (23): Mapper, filter_allowed_fields(), Drop every key of ``obj`` not in ``allowed``. The one primitive both the…, _anonymize_cluster_tasks(), _anonymize_disk_value(), _anonymize_exclude_disk_key(), _anonymize_node_list(), _anonymize_storage_content() (+15 more)

### Community 40 - "Metrics page"
Cohesion: 0.25
Nodes (15): Gigapipe step workaround, Metrics page, Node-scoping selector, PrometheusClient, PromQL builders, Range query chunking, SessionLike protocol, verify_metrics six checks (+7 more)

### Community 41 - "metrics.py"
Cohesion: 0.04
Nodes (116): _RawTimeSeries, MetricLabels, MetricsConfig, WindowConfig, RangeStepMismatch, ``--replay`` found the requested range query, but at a different step than this…, _combine_raw_values(), _combined_raw() (+108 more)

### Community 42 - "state.py"
Cohesion: 0.14
Nodes (21): Cooldown data stored here, interpreted by topology and heuristic, errno, fcntl, socket, _active_cooldowns(), active_disk_cooldowns(), active_storage_cooldowns(), cooldown_remaining_seconds() (+13 more)

### Community 43 - "Load model page"
Cohesion: 0.22
Nodes (15): Backtest gate, Drift baseline is effective load, Forecast provenance report, Forecast scaling ratio, Forecasting page, Holt-Winters forecast, statsmodels optional, apply_forecast scaling (+7 more)

### Community 44 - "_is_metrics_expected_absent"
Cohesion: 0.67
Nodes (3): _is_metrics_expected_absent(), parametrize, test_is_metrics_expected_absent()

### Community 45 - "test_execute.py"
Cohesion: 0.12
Nodes (36): SourceReleaseConfig, _group_with_types(), make_disk(), make_storage(), Section 9.3: a source_release timeout "does not fail the run: mark the storage…, Same as above, except the second move's *target* -- not source -- is the…, Section 9.3 point 3: PVE's own `saferemove_throughput` (already read live off…, No `saferemove_throughput` configured on the storage (e.g. Ceph RBD or ZFS,… (+28 more)

### Community 46 - "FakeClock"
Cohesion: 0.12
Nodes (13): Section 9.3.1: any non-empty ``lock`` means wait, never whitelist a value…, _wait_for_unlocked(), MoveCost, Section 7.1's cost for one already-scheduled move., FakeClock, datetime, Section 9.1: the pre-loop time-window check (above) only knows the answer as of…, REVIEW.md T-06's collateral bug: before the fix, this "skipped" outcome let the… (+5 more)

### Community 47 - "run_heuristic"
Cohesion: 0.13
Nodes (29): group_average_fill(), group_average_utilization(), HeuristicResult, One group's heuristic solve. ``assignment`` is the final target placement…, `u* = (Sum_d l_d) / (Sum_s c_s)` (C6) -- a constant under any reassignment of…, `b_bar = (Sum_d z_d + Sum_s U^ext) / (Sum_s C_s)` (section 5.3 (C7)) -- a…, Section 7.2's unweighted ``F`` -- ``sum(d_s)``, always L1 regardless of…, Section 7.2's unweighted ``E`` -- ``sum(e_s)`` (``"l1"``) or ``max(u_s)``… (+21 more)

### Community 48 - "BundleError"
Cohesion: 0.10
Nodes (22): hash_label_name(), hash_query_text(), The cache key both this module (writing) and ``replay.py`` (reading) derive a…, BundleError, A diagnostic bundle (IMPLEMENTATION_PLAN.md section 16) could not be written or…, bundle_reference_now(), load_manifest(), _NeverSession (+14 more)

### Community 49 - "cli.py"
Cohesion: 0.11
Nodes (25): shutil, _fragmented_vms(), _pin_action_hint(), _pinned_disks(), _pinned_load_fraction(), Assignment, Every disk in ``group`` section 5.3 (C2) pins this run, in the same order…, Section 3.6: name the actual pinned disk(s) keeping one VM's disks spread… (+17 more)

### Community 50 - "Reading `apply`"
Cohesion: 0.07
Nodes (24): A negative `saferemove_throughput` is normal, Negative saferemove_throughput is normal, Reading `show-load` and `verify-storages`, `show-load`, show-load command, The `Group <name> → ACT`/`NO ACTION` line, ACT / NO ACTION gate verdict line, verify-storages command (+16 more)

### Community 51 - "test_documentation.py"
Cohesion: 0.14
Nodes (26): importlib_resources, _flatten_schema_keys(), _load_schema(), _manpage_source_text(), _manual_documented_keys(), Any, needs_full_checkout, parametrize (+18 more)

### Community 52 - "Mapper"
Cohesion: 0.11
Nodes (16): `proxmox.auth.token_id`, _check_no_pseudonym_collision(), Mapper, pseudonym(), ``HMAC-SHA256(salt, kind || "\\0" || value)``, truncated to 8 hex chars.…, 32-bit (8 hex char) truncation makes a same-``kind`` collision astronomically…, The single per-bundle offset :meth:`Mapper.rebase_timestamp` applies: the…, The stateful half of anonymization: one instance per bundle capture. ``vmid``… (+8 more)

### Community 53 - "make_config"
Cohesion: 0.13
Nodes (26): make_config(), make_prometheus_client(), make_pve_client(), --no-series must skip the big, per-group superset range captures -- it does not…, Y-06: the manifest's version fields are machine-generated provenance, not free…, X-09: the printed query count used to treat a multi-day range as one range…, Z-05: a live capture stores every range series at…, Section 3.8/16.3: a real pending edit on the VM's own disk survives as the… (+18 more)

### Community 54 - "crashrecovery.py"
Cohesion: 0.14
Nodes (24): Crash and two-instance recovery: crashrecovery.py, cluster/tasks vs task_status conventions differ, parse_upid PVE UPID grammar confirmed live, reconcile_inflight: recorded UPIDs plus foreign scan, Two failure modes, one in-flight UPID mechanism, AuthConfig, expected_task_user(), parse_upid() (+16 more)

### Community 55 - "format_bytes"
Cohesion: 0.08
Nodes (36): _footprint_text(), _make_confirm_move_interactively(), confirm(), Any, The economic test (``aggregate_ok``) and the hard per-move duration rule…, The human form of :class:`_UnfixableShortfall` -- printed whether or not the…, Only called when the gate decided to ACT but the *final* assignment moves…, ``None`` for a group ``apply`` never got as far as executing (a load error, or… (+28 more)

### Community 56 - "Reading `plan`"
Cohesion: 0.29
Nodes (6): Payback rule check, plan command (never changes anything), Reading a move line, Reading `plan`, solver line (heuristic or cbc), The `payback:` line

### Community 57 - "_vol"
Cohesion: 0.12
Nodes (16): A `san-c` content responder plus a `move_disk` responder for 201. The listing…, The exclusion is narrow: only 201's *own* mirror target (same VM, the disk's…, Section 8.1 / 5.3.3: VM 101 already has 3 TiB on san-b, another VM 3.5 TiB. A 1…, Between different storage types the target is allocated at the disk line's…, The same 2 TiB config `size=` and the same 4.5 TiB already on the target, but…, Section 5.3.1's `hard_b` -- resolved once onto `Storage. free_space_hard_bytes`…, _san_c_content_after_201_launches(), content() (+8 more)

### Community 58 - "test_logging_setup.py"
Cohesion: 0.10
Nodes (37): ast, io, configure_logging(), floor_for_command(), JsonFormatter, The mandatory ``INFO`` floor of section 2.3, or ``None``. A run that can change…, Install this run's log handler. Called once, from ``main()``. ``floor`` is…, Render one :class:`logging.LogRecord` as one JSON line. (+29 more)

### Community 59 - "test_small_disks.py"
Cohesion: 0.16
Nodes (23): Section 5.3 (C8): a small disk ends a plan either where it is now, or on a…, small_disk_placement_ok(), current(), disk(), efi_repair_group(), parametrize, skipif, VM 301's big disks live in another group: its efidisk0 is alone here and never… (+15 more)

### Community 60 - "objective section"
Cohesion: 0.21
Nodes (13): objective.mu_vm_split_per_tib, objective section, `objective.affinity_counts_pinned_disks`, `objective.alpha_spread`, `objective.beta_move_count`, `objective.gamma_move_bytes_per_tib`, `objective.reserve_violation_penalty`, `objective.spread_metric` (+5 more)

### Community 61 - "PveApiError"
Cohesion: 0.10
Nodes (32): ProxmoxConfig, PveApiError, The Proxmox VE API returned an error or an unusable response. See…, _apply_ticket_refresh_seconds(), _build_api(), build_client(), REVIEW.md P-01: wire ``proxmox.ticket_refresh_seconds`` through, best-effort.…, Construct a :class:`PveClient` from ``config.py``'s ``ProxmoxConfig``. Always… (+24 more)

### Community 62 - "test_heuristic.py"
Cohesion: 0.16
Nodes (25): An idle group (every disk's load is 0) has no basis to weight one VM over…, Section 5.4: minmax is `t >= u_s` -- the hottest storage's own u_s, not its…, The heuristic solver. See proxmox_storage_drs/heuristic.py. Cross-checked…, The plan's own demonstration: at beta=0.25 the three-move plan beats the two-…, ``heuristic_iterations`` caps descend's own loop: capped at 1, only the single…, Safety first: even a beta so high that no balance-only move is ever worth it…, Section 6: "a storage involved in a migration within `cooldown_per_storage`…, Cooldown blocks incoming moves, never outgoing ones -- structural, like… (+17 more)

### Community 63 - "._call_once"
Cohesion: 0.13
Nodes (18): AuthenticationError, ResourceException, PveUnreachableError, A :class:`PveApiError` with ``transient`` set: the API could not be reached, or…, _api_error(), _auth_failure_is_transient(), _describe(), _is_server_error() (+10 more)

### Community 64 - "series_of"
Cohesion: 0.16
Nodes (16): HoltWintersConfig, holt_winters_quantile(), ``window.quantile`` of the Holt-Winters forecast path over the next…, Any, The shipped default (288 periods at a 5m step) over the two cycles the lookback…, A diurnal series that *ends at its trough*: the last forecast point (one day…, series_of(), test_backtest_is_none_without_a_fit_half() (+8 more)

### Community 65 - "test_large_vm_split_fixture.py"
Cohesion: 0.16
Nodes (20): Section 6's split gate: ``(vmid, reason)`` for the first large VM (``V^split``,…, split_gate(), _disk(), _footprints(), _group(), parametrize, No single move lowers a peak of 4 on three storages (4, 4, 2 -> 2, 4, 4)., The counterfactual recorded in the expected file. (+12 more)

### Community 66 - "Domain invariants (.agents)"
Cohesion: 0.12
Nodes (20): Domain invariants (.agents), Dry-run is the default, Enumerate every disk bus, Finished task is not a finished move, Never auto-delete a volume, Provisioned size, never allocated, Disks with snapshots pinned, Snapshot reserve never traded for balance (+12 more)

### Community 67 - "FakePrometheusSession"
Cohesion: 0.18
Nodes (17): FakePrometheusSession, A ``metrics._SessionLike`` double capable of answering *many* distinct queries…, _instant_answer(), _range_answer(), A live capture against the dev cluster found this one directly (section 16.3's…, A live capture against the dev cluster found this directly:…, A live capture found this the hard way: ``_check_sample_series()``'s "info"…, Z-02: `_check_coverage()`'s per-disk warning embeds a real vmid taken straight… (+9 more)

### Community 68 - "test_pve.py"
Cohesion: 0.13
Nodes (24): proxmoxer, _client_with_fake_time(), _FakeHttpsBackend, _FakeProxmoxApiWithBackend, _FakeTicketAuth, _flaky(), Exception, parametrize (+16 more)

### Community 69 - "docs/internals/90-heuristic.md"
Cohesion: 0.11
Nodes (19): config section objective, Storage cooldown excludes destination, Descend swaps and whole-VM moves, evaluate_assignment objective, Unconditional repair, objective.spread_metric, w_v and D^big, auto backend cascade (+11 more)

### Community 70 - "test_schedule.py"
Cohesion: 0.14
Nodes (25): make_disk(), make_storage(), _one_move_that_would_leave_san_b_slightly_short(), The plan's own arithmetic: move 1 -> 5.0 <= 8.0, move 2 -> 4.5 <= 8.0, move 3…, A storage with no existing disks and a tiny arriving one must still reserve…, Two disks, both storages already full: the target assignment swaps them, which…, Section 8.2 priority 1: among the *feasible* moves, one resolving a currently-…, REVIEW.md AA-04: section 8.2 was revised to rank candidates by "the alpha and… (+17 more)

### Community 71 - "test_statusfile.py"
Cohesion: 0.07
Nodes (60): CompletedProcess, `report`, `report.warn_pinned_load_fraction`, needs_plugin, os, DrsError, ExecutionError, Exception (+52 more)

### Community 72 - "Assignment"
Cohesion: 0.18
Nodes (20): best_lexicographic(), big_m_agreement_threshold(), E_of(), F_of(), objective_big_m(), objective_nonreserve(), payback(), Assignment (+12 more)

### Community 73 - "main"
Cohesion: 0.09
Nodes (24): ArgumentParser, _accumulate_move_stats(), apply_mode_override(), build_parser(), _fallback_manual_text(), _log_run_summary(), main(), _note_shortfall_for_status() (+16 more)

### Community 74 - "_handle_apply"
Cohesion: 0.12
Nodes (23): Mutable state box narrow exception to functional style, Startup scan folds excluded vmids before planning, _apply_exit_code(), _apply_payback_gate(), _handle_apply(), _InflightStateBox, _make_inflight_callbacks(), ConfirmCallback (+15 more)

### Community 75 - "Any"
Cohesion: 0.15
Nodes (10): FakeResponse, FakeSession, no_coverage(), Any, _RangeStepMismatchFakeClient, 0/2 samples: present in the coverage series but with nothing in it., Answers `/api/v1/query` and `/api/v1/query_range` by the exact `query` param…, A ``range_query`` stand-in that returns caller-supplied data keyed by the exact… (+2 more)

### Community 76 - "docs/internals/92-execute.md"
Cohesion: 0.12
Nodes (16): config section migration, auto mode timewindow, Concurrent execution, Done needs four conditions, VM locks open set, Orphans reported never deleted, Payback gate in apply, Live re-validation of every move (+8 more)

### Community 77 - "_plan_group"
Cohesion: 0.11
Nodes (17): What this build actually implements, _compute_group_load(), _log_forecast(), _log_gate_decision(), _log_load_digest(), _log_payback_verdict(), _plan_group(), Section 5.5's backend dispatch. ``solver.backend: auto`` cascades CBC, then the… (+9 more)

### Community 78 - "_ResponseLike"
Cohesion: 0.29
Nodes (5): Protocol, The subset of ``requests.Response`` this module relies on., The subset of ``requests.Session`` this module relies on. A structural type…, _ResponseLike, _SessionLike

### Community 79 - "case_for"
Cohesion: 0.20
Nodes (18): StorageState, best_big_m(), build(), capacity_spread(), case_for(), moves_of(), order_moves(), per_storage() (+10 more)

### Community 80 - "_exec_group"
Cohesion: 0.24
Nodes (10): _exec_disk(), _exec_group(), _posted_move(), The live transient check charges the converted size from the live `size=`., test_a_converting_move_is_refused_when_the_live_check_finds_no_room(), test_a_live_format_that_differs_from_the_plan_means_replan(), test_format_is_not_sent_when_the_disk_already_has_the_enforced_format(), test_format_is_not_sent_without_enforcement() (+2 more)

### Community 81 - "State"
Cohesion: 0.13
Nodes (24): State dataclass tree mirrors section 11.2 JSON, Section 11.2: ``last_balance``/cooldowns are "updated only after a run that…, _record_executed_moves(), Cooldowns, _parse_state_text(), Any, ``"<group>:<storage>"`` (section 11.2)., Raises on any shape this module does not recognize -- the caller… (+16 more)

### Community 82 - "`execution` — how (and whether) moves actually happen"
Cohesion: 0.12
Nodes (17): `execution.abort_on_failure`, `execution` — how (and whether) moves actually happen, `execution.locks.on_timeout`, `execution.locks.poll_interval`, `execution.locks.task_retry_backoff`, `execution.locks.task_retry_limit`, `execution.locks.wait_timeout`, `execution.max_concurrent_migrations` (+9 more)

### Community 83 - "test_forecast.py"
Cohesion: 0.19
Nodes (15): random, _group_series(), _noise_series(), TimeSeries, Holt-Winters forecasting, its backtest gate, and the required-range rule., Fewer than 2 * seasonal_periods samples before now - W: Holt-Winters cannot be…, test_backtest_fails_on_white_noise(), test_backtest_hw_error_is_none_when_the_fit_half_is_too_short() (+7 more)

### Community 84 - "generate_expected.py"
Cohesion: 0.14
Nodes (17): itertools, computed_p_min(), cost(), Deadlock, duration(), duration_mirror(), duration_wipe(), load_fixture() (+9 more)

### Community 85 - "disk_factors"
Cohesion: 0.27
Nodes (13): disk_factors(), ``f_d / h_d`` for every disk that has one: ``f_d`` the Holt-Winters forecast…, _factor_series(), _FixedForecast, MonkeyPatch, 96 hourly samples whose last 24 are ``window_values`` (repeated)., Patches ``holt_winters_quantile`` to a constant so the ratio is exact., test_disk_factors_is_forecast_over_observed_p95() (+5 more)

### Community 86 - ".agents/documentation.md"
Cohesion: 0.13
Nodes (13): Config knob entry: type, default, unit, extremes, interactions, Tests keeping docs honest (help covers options, manual covers config), --help generated from argparse definitions, no hardcoded defaults, Internals pages: question first, name modules, explain why, ASCII diagrams, Manpage skeleton with complete OPTIONS, config/drs.example.yaml as documentation that parses, Change behaviour and documentation in the same commit, PDF is a build product; fix text not LaTeX (+5 more)

### Community 87 - "forecast.py"
Cohesion: 0.18
Nodes (10): math, Backtest, _quantile(), One group's backtest: absolute error of each model's predicted p95 of ``[now-W,…, Section 10.2's backtest, comparing against a baseline: fit on ``[now-2W,…, Holt-Winters load forecasting. See IMPLEMENTATION_PLAN.md sections 10 and 12.1.…, Linear-interpolation quantile, matching ``numpy.percentile``'s default.…, test_quantile_matches_numpy_percentile_convention() (+2 more)

### Community 88 - "(C7) Capacity-spread linearization (absolute TiB)"
Cohesion: 0.22
Nodes (10): config section gates, last_load, Three gates in order, d_s is absolute TiB, Diagnostic bundles collect-testdata and --replay (section 16), (C7) Capacity-spread linearization (absolute TiB), Capacity gate (section 6), cluster-6 production bundle (+2 more)

### Community 89 - "split_gate_opens"
Cohesion: 0.25
Nodes (8): excess_of(), peak_footprint(), Section 5.3 (C5)/5.3.1: `R_s = max(f_s * Z_s, soft_s)`., ``max_s F_{v,s}`` -- the peak share of one VM any single storage holds., Section 5.3.3 (C9): ``O = sum_{v in V^split} o_v`` in TiB, ``o_v = max(0,…, Section 6's split gate, restated independently of ``gates.split_gate()``: some…, reserve_term(), split_gate_opens()

### Community 90 - "_quantile_promql"
Cohesion: 0.33
Nodes (6): _coverage_promql(), _group_selector(), _quantile_promql(), The one combined selector `compute_group_load()`/`compute_disk_load_series()`…, The exact PromQL `_fetch_raw_quantity` builds for one raw field -- computed…, The exact PromQL `compute_disk_coverage` builds for its range query.

### Community 91 - "LastBalance"
Cohesion: 0.15
Nodes (16): LastBalance, load_vector_for_group(), now_iso(), ``at`` is ``None`` before any run has ever executed a migration -- distinct…, This group's slice of ``last_balance.load_vector``, re-keyed from…, Pure: a new :class:`State` with ``group_name``'s slice of…, UTC, second precision, ``Z`` suffix -- exactly section 11.2's own example…, with_recorded_balance() (+8 more)

### Community 92 - "Reading `explain`"
Cohesion: 0.16
Nodes (13): cannot fully consolidate, forecast line, `measured load:`, `no moves made: ...` / `closest alternative: ...`, objective line, `pinned load ... ; best achievable spread given pins: ...`, `pinned (not movable this run):`, Reading `explain` (+5 more)

### Community 93 - "_redact_finding_message"
Cohesion: 0.40
Nodes (5): DiskKey, ``verify_metrics()``'s own finding text, and this module's own call log (built…, Bundle-safe rewrite of one ``verify_metrics()`` finding message. Returns…, _redact_finding_message(), _redact_free_text()

### Community 94 - "Fixture"
Cohesion: 0.13
Nodes (7): Fixture, Section 5.3 (C7): `(Sum_d z_d + Sum_s U^ext) / (Sum_s C_s)` -- the group's mean…, Section 5.4's `D^big` threshold, converted from the fixture's…, Section 5.4's mu (``objective.mu_vm_split_per_tib``), 0 when the split rule is…, ``{vmid: T_v}`` for ``V^split`` (section 5.3.3), written out independently of…, Section 5.4's `w_v = max(1, l_v / l_bar)`. `V` (the vmids this returns weights…, One group: its storages, its disks and the weights to solve it with. ``keys``…

### Community 95 - "test_running_task_on_the_vm_is_waited_out_before_move_disk"
Cohesion: 0.18
Nodes (9): `/cluster/tasks` shape for a task still running: no endtime/status., The reported failure: an earlier move's "Erase data" (imgdel) job still holds…, Network maintenance between issuing `move_disk` and its completion., running_imgdel(), test_api_outage_beyond_the_tolerance_still_raises(), test_api_outage_while_the_move_task_runs_does_not_fail_the_run(), test_running_task_on_the_vm_is_waited_out_before_move_disk(), task_status() (+1 more)

### Community 96 - ".agents/ index"
Cohesion: 0.12
Nodes (18): .agents/ index, Python style (.agents), black vs flake8 disagreements (E203, W503, E704), One implementation of every rule (MILP and heuristic share), Units in names, If it fails, Running it, Verifying your setup (+10 more)

### Community 97 - "forecast_group"
Cohesion: 0.22
Nodes (10): Collection, forecast_group(), group_aggregate_series(), TimeSeries, Sum every disk's own series into one group-aggregate series, at the union of…, One group's forecast: run the backtest on the group aggregate, and only if…, 101:scsi0 has no sample at t=1 at all -- that timestamp still appears (from…, test_group_aggregate_series_empty_input_is_empty() (+2 more)

### Community 99 - "test_plan_gate_also_reflects_real_drift_history_from_state_json"
Cohesion: 0.24
Nodes (10): _imbalanced_group_load(), _no_reserve_violation_topology(), Two storages, generously sized -- unlike `_sample_topology()`, no (C4)/(C5)…, san-a all the load, san-b none -- imbalance is 200% of `u*`, far above the…, Baseline for the next test: with no `state.json` at all, `last_load` is `None`,…, The same fixture as above, except `state.json` now records a `last_balance`…, Same drift-suppression scenario as `show-load`'s, through `plan` -- the two…, test_plan_gate_also_reflects_real_drift_history_from_state_json() (+2 more)

### Community 100 - "pve-storage-drs manpage"
Cohesion: 0.14
Nodes (14): AUTHOR, COLLECT-TESTDATA OPTIONS, COMMANDS, CONFIGURATION, COPYRIGHT, DESCRIPTION, pve-storage-drs manpage, ENVIRONMENT (+6 more)

### Community 101 - "test_live_transient_check_fails_safe_when_the_live_read_errors"
Cohesion: 0.25
Nodes (8): _detect_orphan_volumes(), Section 9.4/domain rule 6: after a failed or cancelled mirror, a target volume…, parametrize, A PVE API error while re-reading the target refuses the move and fails the run…, test_live_transient_check_fails_safe_when_the_live_read_errors(), test_orphan_detection_finds_only_unreferenced_volumes_of_this_vm(), test_orphan_detection_handles_a_pve_api_error_gracefully(), raise_error()

### Community 102 - "_apply_connection_pool_size"
Cohesion: 0.18
Nodes (11): _apply_connection_pool_size(), Size the underlying ``requests`` session's connection pool to fit…, _FakeProxmoxApiWithSession, _FakeSession, Any, Confirmed live against a real multi-VM cluster: `requests`'s own default…, A small `read_workers` (or the field's own minimum) must not shrink the pool…, A plain string, an object with no ``_store``, or a session-shaped object with… (+3 more)

### Community 103 - "_mapper"
Cohesion: 0.14
Nodes (12): _mapper(), Any, BaseException, _Raise, X-09: `manifest.json`'s `counts.dropped_records` is documented as counting…, A task's ``id`` is the vmid its UPID embeds. It used to be copied raw, leaving…, _tasks_by_kind(), test_anonymize_cluster_tasks_maps_the_task_id_with_the_upid() (+4 more)

### Community 104 - "AGENTS.md working agreement"
Cohesion: 0.21
Nodes (13): fc-tier1 / reserve-tradeoff acceptance fixtures, AGENTS.md working agreement, AGPL-3.0-or-later licence and SPDX headers, black/flake8 E203 W503 E704 ignores, Branch-first git workflow, 85% coverage floor, Documentation pipeline (make docs / docs-check), make check (+5 more)

### Community 105 - "Packaging, dependencies and CI (.agents)"
Cohesion: 0.10
Nodes (21): Git workflow (.agents), Branch first, decided from the task, Merge --no-ff on green make check, Release process (version, changelog, tag, graphify), Packaging, dependencies and CI (.agents), Autopkgtest as the dependency test, coinor-cbc and python3-pulp as Depends, Debian-first dependency policy (trixie) (+13 more)

### Community 106 - "config/drs.example.yaml"
Cohesion: 0.09
Nodes (21): config section exclude, config section execution, config section forecast, config section free_space, config section groups, config section load_weights, config section metrics, config section monitoring (+13 more)

### Community 107 - "`metrics` — Telegraf/InfluxDB name mapping"
Cohesion: 0.14
Nodes (14): `metrics.extra_selector`, `metrics.labels.device`, `metrics.labels.node`, `metrics.labels.vmid`, `metrics.pvestatd_push_interval`, `metrics.rate_window`, `metrics.read_bytes`, `metrics.read_ops` (+6 more)

### Community 108 - "build_node_selector"
Cohesion: 0.25
Nodes (8): build_node_selector(), _escape_promql_regex_literal(), Escape one literal string for safe use inside a PromQL/RE2 ``=~`` alternation.…, Section 3.4's auto-derived node-scoping filter: ``<node_label>=~"n1|n2|..."``…, A node named `pve1.example.com` must match only that exact string in RE2 -- an…, test_build_node_selector_empty_list_is_none(), test_build_node_selector_escapes_dots_in_an_fqdn(), test_build_node_selector_sorts_and_dedupes()

### Community 109 - "storage_of"
Cohesion: 0.25
Nodes (8): all_assignments(), eligible_storages(), A disk's storage under `assign` -- `assign` only ever has entries for movable…, Section 5.3 (C2): every storage whose `allowed_formats` holds this disk's own…, Every eligible placement of the movable disks -- (C2)'s per-disk domain…, Section 5.3 (C8), written out independently of the engine's…, small_disks_follow(), storage_of()

### Community 110 - "PVE InfluxDB external metric server"
Cohesion: 0.17
Nodes (12): gigapipe with ClickHouse (reference backend), PVE InfluxDB external metric server, instance label collision, OpenTelemetry metric server rejected, Other backends, RRD rejected as data source, Six per-disk blockstat counters, Silent counter loss from string fields in line protocol (+4 more)

### Community 111 - "pytest"
Cohesion: 0.10
Nodes (17): fixture, json, logging, LogRecord, pytest, json_safe(), One human-readable line per record: ``LEVEL: message``. Deliberately not a…, ``auto`` and ``text`` -> ``"text"``; ``json`` -> ``"json"``. JSON is opt-in. It… (+9 more)

### Community 112 - "test_affinity_repair_fixture.py"
Cohesion: 0.33
Nodes (9): _affinity_repair_group(), _loads(), _make_disk(), _make_storage(), parametrize, tests/fixtures/affinity-repair.yaml, built as real topology objects., IMPLEMENTATION_PLAN.md section 14.7's fixture, exercised through the real…, test_both_milp_backends_agree_with_the_heuristic() (+1 more)

### Community 113 - "ForecastConfig"
Cohesion: 0.48
Nodes (7): ForecastConfig, The history ``forecast.model`` needs, in seconds. Called by ``config.py``'s…, required_range_seconds(), test_holt_winters_required_range_is_the_lookback_when_that_is_longer(), test_holt_winters_required_range_matches_plan_worked_example(), test_quantile_required_range_is_the_lookback(), test_required_range_unknown_model_raises()

### Community 114 - "apply_forecast"
Cohesion: 0.43
Nodes (7): apply_forecast(), Section 12.1 point 2: scale each disk's ``l_d`` by its forecast factor ``f_d /…, _forecast_fixture(), test_apply_forecast_leaves_idle_and_no_series_matched_alone(), test_apply_forecast_never_scales_a_flagged_disk_even_if_a_factor_is_given(), test_apply_forecast_scales_only_disks_with_a_factor_and_rebuilds_the_totals(), test_apply_forecast_with_no_factors_is_the_identity()

### Community 115 - "Installation and requirements"
Cohesion: 0.18
Nodes (11): Configuration location, PVE credential setup, First steps after installing, Installation and requirements, Installing the package, Running the timer on exactly one host, Setting up the PVE credential, Running timer on exactly one host (+3 more)

### Community 116 - "`migration` — cost, bandwidth and the payback rule"
Cohesion: 0.18
Nodes (11): `migration.account_saferemove_wipe`, `migration.assume_thick_provisioning`, `migration.bwlimit_bytes_per_sec`, `migration` — cost, bandwidth and the payback rule, `migration.max_single_move_duration`, `migration.payback_horizon`, `migration.payback_ratio`, `migration.source_load_weight` (+3 more)

### Community 117 - "apply modes: dry-run, confirm, auto"
Cohesion: 0.20
Nodes (11): Transient reserve invariant (operator explanation), Concurrent execution with strict FIFO launch, confirm prompt [y]es/[n]o/[a]ll/[q]uit, apply modes: dry-run, confirm, auto, Pre-flight live re-check before each move, auto re-plan loop, Decision trail events, --log-format text vs json (+3 more)

### Community 118 - "empty_state"
Cohesion: 0.18
Nodes (17): ``state.path`` could not be written, or its advisory lock could not be…, StateError, empty_state(), First-run state: no lock, no recorded balance, no cooldowns, nothing in flight…, Temp file in the same directory, ``fsync``, then ``os.replace`` -- a reader…, save_state_atomic(), skipif, Only `schema_version` present -- every other field must default the same way… (+9 more)

### Community 119 - "fakes.py"
Cohesion: 0.22
Nodes (5): FakeProxmoxResource, FakeQueryResponse, Any, Shared test doubles. Not collected by pytest (no ``test_`` prefix).…, Matches ``metrics._ResponseLike``: ``.status_code`` and ``.json()``.

### Community 120 - "test_no_feasible_solution_says_infeasible_rather_than_blaming_the_time_limit"
Cohesion: 0.29
Nodes (7): LogCaptureFixture, The defect that prompted IMPLEMENTATION_PLAN.md section 2.3, in the operator's…, The other half: an operator who wrote `solver.backend: cbc` and is silently not…, The warning used to claim "within the time limit" for every status, including a…, test_a_missing_optional_solver_is_not_a_warning_under_auto(), test_an_explicitly_configured_solver_that_is_missing_still_warns(), test_no_feasible_solution_says_infeasible_rather_than_blaming_the_time_limit()

### Community 121 - "_pid_alive"
Cohesion: 0.33
Nodes (6): _pid_alive(), Best-effort, used only to make a "still held" log message useful to an operator…, pid 1 (init) always exists but is not ours to signal as a normal user --…, test_pid_alive_is_false_for_a_reaped_child(), test_pid_alive_is_true_for_a_process_we_cannot_signal(), test_pid_alive_is_true_for_our_own_process()

### Community 122 - "Migration cost and payback test"
Cohesion: 0.25
Nodes (11): compute_benefit_load_seconds benefit formula, compute_move_cost cost_load_seconds, Migration cost and payback test, payback_horizon_seconds H, Affinity term kappa in benefit, REVIEW R-01 double-applied weights, Raw spread, capacity spread, affinity debt, Wipe duration uses magnitude of saferemove_throughput (+3 more)

### Community 123 - "`proxmox` — the cluster API connection"
Cohesion: 0.20
Nodes (10): `proxmox.auth.password`, `proxmox.auth.token_secret`, `proxmox.auth.username`, `proxmox.ca_file`, `proxmox.host`, `proxmox.port`, `proxmox.read_workers`, `proxmox` — the cluster API connection (+2 more)

### Community 124 - "_render_split_lines"
Cohesion: 0.40
Nodes (4): One large VM's (``V^split``, section 5.3.3) before/after numbers for the report., Section 9.5's ``split:`` lines. A result still above its cap says the solver…, _render_split_lines(), _VmSplit

### Community 125 - "pathlib"
Cohesion: 0.15
Nodes (12): argparse, pathlib, sys, skipif, ``__version__`` must agree with ``pyproject.toml`` and the install instructions., test_install_instructions_name_the_current_version(), check(), _logical_lines() (+4 more)

### Community 126 - "Configuration reference"
Cohesion: 0.22
Nodes (16): Configuration reference, gates section, `gates.capacity_spread_threshold`, `gates.cooldown_per_disk`, `gates.cooldown_per_storage`, `gates` — deciding whether to act at all, `gates.drift_threshold`, `gates.imbalance_threshold` (+8 more)

### Community 127 - "test_solve_returns_none_when_the_library_is_unavailable"
Cohesion: 0.50
Nodes (5): cbc_available(), MonkeyPatch, Deliberately *not* parametrized over the skip-guarded `BACKENDS` list above --…, test_cbc_available_is_false_when_pulp_is_not_importable(), test_solve_returns_none_when_the_library_is_unavailable()

### Community 128 - "test_plan_reports_an_unfixable_shortfall_and_the_pins_that_block_it"
Cohesion: 0.40
Nodes (5): _all_pinned_sample_topology(), parametrize, `_sample_topology()` with its one movable disk pinned too: san-a violates (C5)…, Section 5.3/9.5: a residual `r_s > 0` is reported prominently, with the byte…, test_plan_reports_an_unfixable_shortfall_and_the_pins_that_block_it()

### Community 129 - "test_manual_falls_back_when_man_exits_nonzero"
Cohesion: 0.40
Nodes (3): test_manual_falls_back_when_man_exits_nonzero(), test_manual_flag_uses_man_when_available(), fake_run()

### Community 131 - "Where the numbers come from, and how a transport loses them"
Cohesion: 0.25
Nodes (8): A reference implementation that is well tested, Telegraf with a Prometheus remote-write output, The failure mode: a transport that cannot carry strings, The six counters, Two things deliberately not used, What catches it, What to do next, Where the numbers come from, and how a transport loses them

### Community 132 - "`exclude` — what DRS never touches"
Cohesion: 0.25
Nodes (8): `exclude.disks`, `exclude.include_unused_disks`, `exclude.running_only`, `exclude.skip_vms_with_snapshots`, `exclude.storages`, `exclude.tags`, `exclude.vmids`, `exclude` — what DRS never touches

### Community 133 - "test_unfixable_shortfall_is_proven_only_for_an_optimal_cbc_solve"
Cohesion: 0.67
Nodes (3): test_unfixable_shortfall_is_proven_only_for_an_optimal_cbc_solve(), outcome(), proven()

### Community 134 - "test_task_lock_timeout_retry_drives_inflight_callbacks_for_both_upids"
Cohesion: 0.50
Nodes (3): Crash recovery (section 11.2/13): a retried move is still always exactly one…, move_disk(), test_task_lock_timeout_retry_drives_inflight_callbacks_for_both_upids()

### Community 138 - "test_objective_offset_is_carried_by_a_variable_fixed_to_one"
Cohesion: 0.67
Nodes (3): skipif, PuLP drops an objective's constant when handing the model to CBC, so CBC's…, test_objective_offset_is_carried_by_a_variable_fixed_to_one()

### Community 139 - "Configuration page"
Cohesion: 0.43
Nodes (7): Config path resolution order, Configuration page, ResolvedConfig, Secrets from environment, Semantic validation rules, Two-stage validation, Units parsed once

### Community 140 - "Persistent state: state.json"
Cohesion: 0.13
Nodes (18): Persistent state: state.json, Drift history reaches the gates via last_balance, Inflight UPIDs written and read for crash recovery, Reading degrades, writing raises, Rename-detaches-flock bug and in-place locked write, staged_disks field unimplemented, on_finished(), on_started() (+10 more)

### Community 141 - "docs/internals/00-overview.md"
Cohesion: 0.13
Nodes (12): config.py depends on forecast.py, Module layout, Pipeline as specified and as built, Command dispatch dict, JsonFormatter, --mode escalation rule, 'no moves made' report, Monitoring status file statusfile.py (+4 more)

### Community 143 - "`groups` — storage groups"
Cohesion: 0.33
Nodes (6): `groups[].name`, `groups` — storage groups, `groups[].storages[].capability_weight`, `groups[].storages[].free_space.soft` / `groups[].storages[].free_space.hard`, `groups[].storages[].id`, `groups[].storages[].reserve_factor`

### Community 144 - "`load_weights` — combining read/write and time/ops/bytes"
Cohesion: 0.33
Nodes (6): `load_weights.bytes`, `load_weights` — combining read/write and time/ops/bytes, `load_weights.iotime`, `load_weights.ops`, `load_weights.read_factor`, `load_weights.write_factor`

### Community 145 - "Safety properties, exit codes, and what this build actually does"
Cohesion: 0.33
Nodes (6): verify-metrics exit status and severity levels, Failure to read ends the run with exit 1, Exit codes, Optional dependencies, Safety properties, exit codes, and what this build actually does, What is safe, unconditionally

### Community 146 - "Diagnostic bundles: `collect-testdata` and `--replay`"
Cohesion: 0.33
Nodes (5): `collect-testdata`: capturing a bundle, Diagnostic bundles: `collect-testdata` and `--replay`, `--replay`: running against a bundle offline, Sending one to the project, What is in a bundle, and what is not

### Community 147 - "Logging: what lands where, and what an unattended run records"
Cohesion: 0.29
Nodes (7): Logging, Logging: what lands where, and what an unattended run records, Text or JSON, The decision trail, Unattended runs log this without being asked, Under systemd, Verbosity

### Community 149 - "footprint_on"
Cohesion: 0.40
Nodes (6): footprint_on(), largest_on(), Section 5.3.3's ``F_{v,s}``: the sum of VM ``vmid``'s disks on ``s`` -- every…, Section 5.3 (C4) ``Z_s`` = ``max_v F_{v,s}``, the largest per-VM footprint on…, Section 8.1: the snapshot term's basis while ``key`` mirrors onto ``b``,…, transient_basis()

### Community 152 - "`forecast` — placing disks for the load they will have"
Cohesion: 0.40
Nodes (5): `forecast.holt_winters.seasonal`, `forecast.holt_winters.seasonal_periods`, `forecast.holt_winters.trend`, forecast.model (quantile, holt_winters), `forecast` — placing disks for the load they will have

### Community 153 - "`prometheus` — the metrics source"
Cohesion: 0.40
Nodes (5): `prometheus.bearer_token`, `prometheus` — the metrics source, `prometheus.timeout_seconds`, `prometheus.url`, `prometheus.username` / `prometheus.password`

### Community 154 - "`solver` — which backend plans"
Cohesion: 0.40
Nodes (5): solver.backend (auto, cbc, heuristic), `solver.heuristic_iterations`, `solver.mip_gap`, `solver.time_limit_seconds`, `solver` — which backend plans

### Community 155 - "`support` — diagnostic bundles"
Cohesion: 0.40
Nodes (5): `support.bundle_dir`, `support.capture_range`, `support` — diagnostic bundles, `support.max_series_points`, `support.salt_path`

### Community 156 - "`--json`"
Cohesion: 0.33
Nodes (5): `--json`, Whether this group's execution failed in a way that must end the whole run…, fake_execute_plan(), delayed_status(), status()

### Community 159 - "proxmox-storage-drs"
Cohesion: 0.40
Nodes (4): Getting the tool, proxmox-storage-drs, The documents, The safety properties to rely on

### Community 162 - "resolve_level"
Cohesion: 0.50
Nodes (5): Section 2.3's ladder: ``--quiet`` < default < ``-v`` < ``-vv``. ``--log-level``…, resolve_level(), parametrize, test_log_level_wins_over_both_verbose_and_quiet(), test_resolve_level_ladder()

### Community 164 - "_FakeClient"
Cohesion: 0.40
Nodes (3): str, _FakeClient, The ``"fake-client"`` sentinel every ``build_pve_client`` mock in this file…

### Community 169 - "`snapshot_reserve` — the free-space floor"
Cohesion: 0.50
Nodes (4): free_space.soft / free_space.hard, `snapshot_reserve.count_foreign_volumes`, snapshot_reserve.factor, `snapshot_reserve` — the free-space floor

### Community 170 - "`window` — the decision window"
Cohesion: 0.50
Nodes (4): `window.lookback`, `window.min_coverage`, `window.quantile`, `window` — the decision window

### Community 173 - "`free_space` — keep N bytes (or N%) free on top of the snapshot reserve"
Cohesion: 0.27
Nodes (6): free_space section, `free_space.hard`, `free_space` — keep N bytes (or N%) free on top of the snapshot reserve, `free_space.soft`, free-space-repair fixture (plan 14.8), free_space.soft repair exemption

### Community 177 - "fc-tier1 fixture (plan 14 worked example)"
Cohesion: 0.67
Nodes (3): fc-tier1 fixture (plan 14 worked example), generate_expected.py exhaustive enumeration, beta x delta sweep contract

## Knowledge Gaps
- **314 isolated node(s):** `state.path`, `Migrations throttled by bwlimit only`, `(C2) Eligibility via variable fixing`, `(C3) VM affinity linking`, `(C4) Largest-disk linearization Z_s` (+309 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1564 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **63 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Group` connect `Group` to `execute.py`, `test_cli.py`, `seed_assignment`, `ExecutionResult`, `test_payback.py`, `Path`, `test_enforce_format.py`, `MonkeyPatch`, `GroupLoad`, `run`, `Disk`, `test_optimize.py`, `topology.py`, `test_topology.py`, `ExecutionConfig`, `ObjectiveBreakdown`, `_sample_topology`, `balanced_load`, `metrics.py`, `test_execute.py`, `FakeClock`, `run_heuristic`, `cli.py`, `format_bytes`, `test_small_disks.py`, `test_heuristic.py`, `test_large_vm_split_fixture.py`, `test_schedule.py`, `main`, `_handle_apply`, `_plan_group`, `_exec_group`, `_quantile_promql`, `test_plan_gate_also_reflects_real_drift_history_from_state_json`, `test_affinity_repair_fixture.py`, `apply_forecast`, `test_no_feasible_solution_says_infeasible_rather_than_blaming_the_time_limit`, `test_solve_returns_none_when_the_library_is_unavailable`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **Why does `PveClient` connect `PveClient` to `execute.py`, `._call`, `test_pve.py`, `test_live_transient_check_fails_safe_when_the_live_read_errors`, `ResolvedConfig`, `_handle_apply`, `run`, `config.py`, `FakeClock`, `BundleError`, `cli.py`, `topology.py`, `make_config`, `crashrecovery.py`, `test_topology.py`, `ExecutionConfig`, `PveApiError`, `._call_once`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Why does `Crash and two-instance recovery: crashrecovery.py` connect `crashrecovery.py` to `execute.py`, `_handle_apply`, `state.py`, `Persistent state: state.json`, `docs/internals/00-overview.md`, `docs/internals/92-execute.md`, `config.py`, `cli.py`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Are the 188 inferred relationships involving `Group` (e.g. with `_accumulate_move_stats()` and `_apply_payback_gate()`) actually correct?**
  _`Group` has 188 INFERRED edges - model-reasoned connections that need verification._
- **Are the 93 inferred relationships involving `PveClient` (e.g. with `_apply_payback_gate()` and `_pve_client_for()`) actually correct?**
  _`PveClient` has 93 INFERRED edges - model-reasoned connections that need verification._
- **What connects `state.path`, `Migrations throttled by bwlimit only`, `(C2) Eligibility via variable fixing` to the rest of the system?**
  _314 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `execute.py` be split into smaller, more focused modules?**
  _Cohesion score 0.04864976293547722 - nodes in this community are weakly interconnected._