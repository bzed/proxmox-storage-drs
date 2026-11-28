# Graph Report - proxmox-storage-drs  (2026-11-28)

## Corpus Check
- 135 files · ~358,369 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4291 nodes · 11734 edges · 189 communities (154 shown, 35 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 1526 edges (avg confidence: 0.94)
- Token cost: 916,913 input · 0 output

## Community Hubs (Navigation)
- execute.py
- collect.py
- metrics.py
- test_cli.py
- test_config.py
- test_heuristic.py
- Path
- CaptureFixture
- test_metrics.py
- compute_reserve_status
- test_execute.py
- GroupLoad
- test_optimize.py
- AGENTS.md working agreement
- BundleError
- RecordingPveClient
- Group
- test_enforce_format.py
- Disk
- test_anonymize.py
- Disk
- 20-verifying-metrics.md
- test_replay.py
- MonkeyPatch
- test_validate_corpus.py
- ._call
- State
- cli.py
- PveClient
- Configuration reference
- test_collect.py
- run_concurrent
- pve-storage-drs manpage
- ResolvedConfig
- test_topology.py
- TimeWindow
- config.py
- order_moves
- `proxmox` — the cluster API connection
- _sample_topology
- topology.py
- _render_group_plan_human
- test_topology.py
- ResolvedConfig
- test_logging_setup.py
- _handle_apply
- State
- ExecutionConfig
- IMPLEMENTATION_PLAN.md
- test_documentation.py
- _plan_group
- 29-explain.md
- empty_state
- exceptions.py
- `migration` — cost, bandwidth and the payback rule
- Overview: what is built, and how it fits together
- config.py
- FakeClock
- Assignment
- make_config
- heuristic.py
- ._get
- test_free_space_repair_fixture.py
- test_forecast.py
- exceptions.py
- format_bytes
- PveApiError
- _run_two_onto_san_c
- test_topology.py
- Safety properties, exit codes, status
- build_client
- test_state.py
- test_small_disks.py
- topology.py
- forecast.py
- test_payback.py
- Group
- test_statusfile.py
- json_safe
- stitch_range_results
- config/drs.example.yaml
- test_payback.py
- `execution` — how (and whether) moves actually happen
- generate_expected.py
- case_for
- test_statusfile.py
- apply modes: dry-run, confirm, auto
- apply_forecast
- metrics.py
- FakePrometheusSession
- Testing (.agents)
- Logging
- check_paper_log.py
- Reading `explain`
- _apply_connection_pool_size
- test_state.py
- Fixture
- save_locked_state
- build_rate_promql()
- PaybackResult
- Reading `apply`
- pytest
- _mapper
- test_payback.py
- repair_markers
- gates section
- IMPLEMENTATION_PLAN.md
- disk_factors
- FakeProxmoxResource
- `metrics` — Telegraf/InfluxDB name mapping
- test_payback.py
- _outcome
- evaluate_assignment(): shared section 5.4 objective
- Test corpus tests/corpus/
- topology.py
- test_statusfile.py
- FakeClock
- _exec_group
- Transient invariant
- Cooldowns
- build_topology() one-pass join
- reserve.py shared (C4)/(C5) footprint evaluator
- IMPLEMENTATION_PLAN.md
- move_disk (drive-mirror, delete=1)
- Objective function (alpha, beta, gamma, kappa, delta, mu, P)
- split_gate_opens()
- test_affinity_repair_fixture.py
- RangeStepMismatch
- test_topology.py
- test_docstrings.py
- forecast_group
- save_state_atomic
- test_topology.py
- test_plan_gate_also_reflects_real_drift_history_from_state_json
- test_statusfile.py
- delta data spread weight per TiB
- test_statusfile.py
- Migration cost and payback test
- `exclude` — what DRS never touches
- forecast.py
- metrics.py
- test_apply_exits_quietly_when_state_json_is_already_locked
- test_enforce_format.py
- Pin priority _pin_reason() (C2)
- Payback acceptance test
- (C4)/(C5) Snapshot reserve and free-space constraint
- _vm_splits
- Assignment
- filters.lua
- _FakeClient
- test_optimize.py
- test_optimize.py
- series_of
- series_of
- test_holt_winters_quantile_is_none_for_a_non_finite_forecast
- last_load drift baseline
- loadmodel.py
- fc-tier1 fixture (plan 14 worked example)
- MonkeyPatch
- series_of
- import-all
- DeepWiki
- Lock timeout skip vs abort
- Contributing test data with collect-testdata and --replay
- run-with-system-python.sh
- `free_space` — keep N bytes (or N%) free on top of the snapshot reserve
- Group
- build_paper.sh
- build_site.sh
- Transient invariant called with single-move set
- solver: line (backend actually used)
- apply modes: dry-run, confirm, auto
- Shared pandoc PDF metadata
- Affinity repair under payback fixture
- Free-space repair mandate fixture
- Per-group MILP optimization model
- Objective (alpha imbalance, beta migrations, gamma bytes, kappa fragmentation, delta spread, P reserve)
- reserve-tradeoff companion fixture
- Provisioned-size (thick) accounting
- importlib
- proxmox-storage-drs
- proxmox_storage_drs
- forecast_group
- CaptureFixture
- CaptureFixture
- test_documentation.py

## God Nodes (most connected - your core abstractions)
1. `Group` - 232 edges
2. `Disk` - 111 edges
3. `write_config()` - 86 edges
4. `run()` - 84 edges
5. `make_move()` - 81 edges
6. `client_with()` - 80 edges
7. `build_topology()` - 78 edges
8. `PveClient` - 77 edges
9. `PrometheusClient` - 76 edges
10. `Storage` - 76 edges

## Surprising Connections (you probably didn't know these)
- `The `Group <name> → ACT`/`NO ACTION` line` --references--> `GroupLoad`  [INFERRED]
  docs/manual/25-show-load-and-verify-storages.md → src/proxmox_storage_drs/loadmodel.py
- `What is in the file` --references--> `duration()`  [INFERRED]
  docs/manual/36-monitoring.md → tests/fixtures/generate_expected.py
- `Seven-stage pipeline: collect, join, gate, solve, cost, order, execute` --references--> `_plan_group()`  [INFERRED]
  docs/internals/00-overview.md → src/proxmox_storage_drs/cli.py
- `What `plan` does not yet do` --references--> `GroupLoad`  [INFERRED]
  docs/manual/27-plan.md → src/proxmox_storage_drs/loadmodel.py
- `apply_forecast(): scaling, never replacing` --references--> `apply_forecast()`  [EXTRACTED]
  docs/internals/70-loadmodel.md → src/proxmox_storage_drs/loadmodel.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Safety invariants that must not be optimised away** — agents_domain_invariants_snapshot_reserve, implementation_plan_transient_invariant, agents_domain_invariants_finished_task_not_finished_move, agents_domain_invariants_never_auto_delete, agents_domain_invariants_dry_run_default [EXTRACTED 1.00]
- **CI and quality gates enforcing the make check loop** — github_workflows_tests_tests_workflow, github_workflows_debian_package_debian_package_workflow, debian_gitlab_ci_salsa_ci_pipeline, pre_commit_config_pre_commit_hooks, codecov_yml_codecov_config [INFERRED 0.85]
- **Plan section 14 fixtures** — tests_fixtures_fc_tier1_doc, tests_fixtures_affinity_repair_doc, tests_fixtures_free_space_repair_doc, tests_fixtures_large_vm_split_doc, tests_fixtures_reserve_tradeoff_doc [INFERRED 0.85]
- **Per-group decision pipeline: load, gates, solve, payback, order, execute** — implementation_plan_load_model, implementation_plan_gating, implementation_plan_milp, implementation_plan_payback, implementation_plan_scheduling, implementation_plan_move_disk [EXTRACTED 1.00]
- **Reserve and free-space safety enforced before, during and after moves** — implementation_plan_reserve, implementation_plan_lexicographic_solve, implementation_plan_reserve_override, implementation_plan_repair_exemption, implementation_plan_transient_invariant [EXTRACTED 1.00]
- **Collect, anonymize, replay and corpus flow** — implementation_plan_diagnostic_bundles, implementation_plan_anonymization_allowlist, implementation_plan_keyed_pseudonyms, implementation_plan_replay, implementation_plan_test_corpus [EXTRACTED 1.00]
- **One transient reserve invariant shared by scheduler and executor** — docs_internals_95_schedule_transient, docs_internals_92_execute_live_transient_provisioned, docs_internals_92_execute_no_double_counting, docs_internals_60_topology_reserve_py [EXTRACTED 1.00]
- **Reserve is never traded against balance** — docs_internals_80_gates_reserve_override, docs_internals_90_heuristic_repair, docs_internals_91_optimize_lex, docs_internals_96_payback_repair_exemption, docs_internals_95_schedule_deadlock_report [INFERRED 0.95]
- **In-flight UPID crash recovery flow** — docs_internals_15_state_inflight_upids_written_and_read_for_crash_recovery, docs_internals_93_crashrecovery_write_upid_to_disk_before_the_crash_can_happen, docs_internals_93_crashrecovery_reconcile_inflight_recorded_upids_plus_foreign_scan, docs_internals_93_crashrecovery_startup_scan_folds_excluded_vmids_before_planning [EXTRACTED 1.00]
- **Unconditional safety properties** — agents_domain_invariants_dry_run_default, docs_manual_30_safety_and_status_reserve_never_traded, docs_manual_30_safety_and_status_nodelete [EXTRACTED 1.00]
- **Silent counter loss and its detection** — docs_manual_05_metrics_pipeline_six_counters, docs_manual_05_metrics_pipeline_string_field_drop, docs_manual_05_metrics_pipeline_telegraf_remote_write, docs_manual_20_verifying_metrics_sample_series_subset_check [EXTRACTED 1.00]
- **Lifecycle of one executed move** — docs_manual_28_apply_preflight_recheck, docs_manual_28_apply_move_done_definition, docs_manual_28_apply_draining, docs_manual_28_apply_state_json_updates, docs_manual_28_apply_crash_recovery [INFERRED 0.85]
- **Domain safety invariants that must not be optimised away** — agents_domain_invariants_dry_run_default, agents_reserve_never_traded, agents_three_floors_precedence, implementation_plan_transient_invariant, implementation_plan_finished_move, agents_never_overprovision [EXTRACTED 1.00]
- **Debian packaging, CI and release chain** — agents_debian_first, agents_autopkgtest, agents_ci_pipelines, agents_release_procedure [INFERRED 0.85]
- **Rules keeping shipped documentation honest** — _agents_documentation_doc_tests, _agents_documentation_same_commit_rule, _agents_documentation_help_from_argparse, _agents_documentation_reference_config [INFERRED 0.85]

## Communities (189 total, 35 thin omitted)

### Community 0 - "execute.py"
Cohesion: 0.04
Nodes (109): Move done needs four conditions, Draining outcome excludes source storage, Injectable Clock, VM locks are an open set, waited out, Orphaned volumes reported, never deleted, Retry on move_disk task flock timeout, Wipe duration uses magnitude of saferemove_throughput, ExcludeConfig (+101 more)

### Community 1 - "collect.py"
Cohesion: 0.04
Nodes (101): anonymize.py pure allowlist shared with scrub audit, Fail-closed pseudonym anonymization, functools, gzip, hashlib, hmac, MappingType, re (+93 more)

### Community 2 - "metrics.py"
Cohesion: 0.04
Nodes (93): Group-scoped, batched raw queries (REVIEW Q-02), _RawTimeSeries, MetricLabels, MetricsConfig, Label names that identify a series in Prometheus, from ``metrics.labels``. Each…, Prometheus metric names and query settings, from the ``metrics`` block. Metric…, _fetch_all_raw_quantities(), _fetch_all_raw_quantity_series() (+85 more)

### Community 3 - "test_cli.py"
Cohesion: 0.03
Nodes (73): load_config(), Resolve, read, parse and validate the configuration. See section 11 for…, _balanced_non_violating_topology(), _breakdown_with_split(), _NodeNamesClient, LogCaptureFixture, REVIEW.md R-06: `move.size_bytes == 0` must not raise `ZeroDivisionError` --…, REVIEW.md R-02: when the scheduler can only order *some* of the heuristic's… (+65 more)

### Community 4 - "test_config.py"
Cohesion: 0.07
Nodes (85): minimal_config_dict(), Any, parametrize, Path, skipif, The smallest config that passes structural + semantic validation., Config loading, resolution order and section 11.1 semantic validation., There is no ``metrics.labels.cluster`` any more -- an earlier revision's… (+77 more)

### Community 5 - "test_heuristic.py"
Cohesion: 0.06
Nodes (86): Return the pseudonym of a group name, in the form ``group-<hash>``. The hash…, active_split_caps(), compute_vm_weights(), evaluate_assignment(), Section 5.5 step 1: "seed with the current assignment (not from scratch -- we…, ``{vmid: T_v}`` for ``V^split`` (section 5.3.3), or empty when the rule is off…, Section 5.4's `w_v = max(1, l_v / l_bar)` -- the per-VM weight that scales…, Section 5.4's objective for one candidate ``assignment``.… (+78 more)

### Community 6 - "Path"
Cohesion: 0.07
Nodes (71): The whole cluster's worth of groups, as seen by this run. By the time anything…, Topology, _fragmented_group(), _make_group_plan(), _moved_outcome(), _one_disk_group(), _one_disk_group_load(), _one_move() (+63 more)

### Community 7 - "CaptureFixture"
Cohesion: 0.07
Nodes (75): CaptureFixture, Exception, _patch_plan_deps(), _patch_show_load_deps(), _patch_show_load_forecast(), MonkeyPatch, parametrize, `_sample_topology()` with san-b given more headroom (16 TiB instead of 8):… (+67 more)

### Community 8 - "test_metrics.py"
Cohesion: 0.06
Nodes (69): How much history the load model reads, from the ``window`` block. -…, WindowConfig, _check_coverage(), PrometheusClient, Thin wrapper over the Prometheus HTTP API. See section 3.4/3.5. ``session`` is…, Section 3.3 step 5: report which disks fall below ``window.min_coverage``., _all_metric_names(), FakeResponse (+61 more)

### Community 9 - "compute_reserve_status"
Cohesion: 0.06
Nodes (72): dataclasses, Migration cost and the payback acceptance test. See IMPLEMENTATION_PLAN.md…, compute_reserve_status(), _current_storage(), largest_disk_bytes(), largest_footprint(), largest_footprint_bytes(), managed_used_bytes() (+64 more)

### Community 10 - "test_execute.py"
Cohesion: 0.09
Nodes (71): client_with(), default_group(), make_move(), parametrize, Fails safe: a volume with neither `size` nor `approximate-size` makes the…, A PVE API error while re-reading the target refuses the move and fails the run…, A move missing from `move_costs_by_key` is never refused for lack of an…, Section 13: `state.json` must learn about a UPID *before* this function goes on… (+63 more)

### Community 11 - "GroupLoad"
Cohesion: 0.06
Nodes (68): GatesConfig, Thresholds and cooldowns that decide whether a run plans moves, from the…, _capacity_spread(), evaluate_group_gates(), _l1_drift(), GroupLoad, Section 6, applied in the order it lists: reserve override, then the capacity…, ``(‖ℓ_last‖₁, ‖ℓ_now − ℓ_last‖₁)`` over the **union** of disk keys present in… (+60 more)

### Community 12 - "test_optimize.py"
Cohesion: 0.10
Nodes (61): _movable_disks(), OptimizeResult, `D^mov` (section 5.3) -- identical filter to `heuristic._movable_disks()`,…, One group's MILP solve. ``breakdown``/``initial_breakdown`` are computed by the…, Solve one group with ``backend`` (``"cbc"``). ``probing`` says this backend was…, solve(), Group, One storage group: section 5's independent optimization unit. (+53 more)

### Community 13 - "AGENTS.md working agreement"
Cohesion: 0.05
Nodes (55): ASD-STE100 writing at 80 % compliance, Config knob entry: type, default, unit, extremes, interactions, Tests keeping docs honest (help covers options, manual covers config), --help generated from argparse definitions, no hardcoded defaults, Internals pages: question first, name modules, explain why, ASCII diagrams, Manpage skeleton with complete OPTIONS, Payback rule: benefit > payback_ratio * cost in load-seconds, Change behaviour and documentation in the same commit (+47 more)

### Community 14 - "BundleError"
Cohesion: 0.06
Nodes (36): The Prometheus client and verify-metrics, PrometheusClient single _get() request path, SessionLike protocol for network-free tests, Replay clients are real subclasses, bundle_reference_now(), load_manifest(), _NeverSession, _parse_step_seconds() (+28 more)

### Community 15 - "RecordingPveClient"
Cohesion: 0.05
Nodes (35): CallRecord, _capture_prometheus_files(), CaptureLog, _drive_group_series(), _drive_label_values(), _group_vmid_batches(), _guarded(), _issue_range_chunks() (+27 more)

### Community 16 - "Group"
Cohesion: 0.12
Nodes (54): LoadWeights, Weights and factors that turn the raw I/O counters into one load value per…, compute_group_load(), Compute one group's :class:`GroupLoad` for this run. Section 4.…, _client(), full_coverage(), make_disk(), make_storage() (+46 more)

### Community 17 - "test_enforce_format.py"
Cohesion: 0.10
Nodes (51): enforce_format: target_format() and disk_size_on(), (C2) format eligibility, needs_cbc, disk_size_on(), qcow2_lvm_allocation_bytes(), Upper bound on the LV ``alloc_image`` creates for a ``qcow2`` volume of…, Section 5.3.2's ``z_{d,s}``, in bytes: what ``disk`` occupies when placed on…, tests_unit (+43 more)

### Community 18 - "Disk"
Cohesion: 0.09
Nodes (51): Feasibility constraints shared by both stages, ObjectiveConfig, Weights of the optimisation objective, from the ``objective`` block. The MILP…, _cbc_capacity_spread_term(), _cbc_feasibility_constraints(), _cbc_objective_terms(), _cbc_small_disks_follow_their_vm(), _cbc_split_excess_term() (+43 more)

### Community 19 - "test_anonymize.py"
Cohesion: 0.06
Nodes (42): make_mapper(), MonkeyPatch, parametrize, Path, A node and a storage that happen to share a name must not collide., Section 16.3: 'the result never depends on iteration order'., Force two different vmids to hash to the same base slot and confirm both still…, X-09: `vmid`'s own linear probing makes a collision impossible, but nothing did… (+34 more)

### Community 20 - "Disk"
Cohesion: 0.08
Nodes (46): 'no moves made' line in plan/apply, best_single_disk_alternative() for explain, Descend: moves, swaps and whole-VM relocation, _RepairCandidate, Section 6: decide whether to act on a group at all, before the solver runs.…, _best_of(), _best_repair_candidate(), trial_storage_of() (+38 more)

### Community 21 - "20-verifying-metrics.md"
Cohesion: 0.05
Nodes (46): apply privileges VM.Config.Disk and VM.Migrate, Configuration location /etc/pve/drs.yaml, PVE credential setup (Datastore.Audit and Datastore.Allocate, VM.Audit), First steps after installing, Installation and requirements, Installing the package, Running the timer on exactly one host, Setting up the PVE credential (+38 more)

### Community 22 - "test_replay.py"
Cohesion: 0.10
Nodes (45): PrometheusConfig, Prometheus query endpoint, from the ``prometheus`` block. Fields, with their…, BundleError, A diagnostic bundle (IMPLEMENTATION_PLAN.md section 16) could not be written or…, _captured_step(), _config_from_bundle(), _free_space_pairs(), MonkeyPatch (+37 more)

### Community 23 - "MonkeyPatch"
Cohesion: 0.09
Nodes (45): ExecutionResult, One group's ``execute_plan()`` call. ``stopped_early`` is true for any reason…, _balanced_apply_group_load(), _balanced_apply_topology(), _check_statusfile(), _monitored_config(), Two evenly-sized, evenly-loaded disks on one storage, none on the other, no…, Matches `_balanced_apply_topology()`: both disks on san-a, load 5.0 each (200%… (+37 more)

### Community 24 - "test_validate_corpus.py"
Cohesion: 0.09
Nodes (45): tests_corpus, tests_corpus_validate_corpus, _case(), _invariant_inputs(), MonkeyPatch, needs_full_checkout, parametrize, Path (+37 more)

### Community 25 - "._call"
Cohesion: 0.06
Nodes (28): move_disk(): single bytes/s to KiB/s conversion, Retry policy: reauthentication and transient failures, storage_definitions() uses the GET /storage list form, API outage tolerance for reads, Mirror duration is z_d / bwlimit, _apply_ticket_refresh_seconds(), _build_api(), Any (+20 more)

### Community 26 - "State"
Cohesion: 0.09
Nodes (42): cluster/tasks vs task_status conventions differ, parse_upid() grammar confirmed live, reconcile_inflight(): recorded UPIDs plus foreign scan, AuthConfig, Credentials for the PVE API, from the ``proxmox.auth`` block. Fields, with…, expected_task_user(), parse_upid(), PveClient (+34 more)

### Community 27 - "cli.py"
Cohesion: 0.08
Nodes (43): shutil, _apply_exit_code(), _capacity_gate_hint(), _footprint_text(), _fragmented_vms(), _load_per_tib(), _objective_breakdown_json(), _pin_action_hint() (+35 more)

### Community 28 - "PveClient"
Cohesion: 0.11
Nodes (41): PveClient, One method per IMPLEMENTATION_PLAN.md section 3.5 endpoint. ``api`` is typed…, Retry idempotent calls that fail because the API is unreachable for up to…, fake_api(), BaseException, Section 9.2: "convert at the call site and nowhere else" -- this is that site., A ticket that expired for reasons external to this call (a long confirm-mode…, A successful re-login does not guarantee the retried call succeeds -- e.g. the… (+33 more)

### Community 29 - "Configuration reference"
Cohesion: 0.05
Nodes (41): Configuration reference, exclude section (vmids, disks, storages, tags, stopped VMs), `forecast.holt_winters.seasonal`, `forecast.holt_winters.seasonal_periods`, `forecast.holt_winters.trend`, forecast.model (quantile, holt_winters), `forecast` — placing disks for the load they will have, `free_space.hard` (+33 more)

### Community 30 - "test_collect.py"
Cohesion: 0.09
Nodes (38): capture(), Path, X-08: section 16.1's manifest line ("schema, versions, what was captured...")…, X-08: section 16.3 promises the manifest "flags" a non-node-shaped…, Z-03: `resolve_node_selector()`'s tier-1 precedence used to win on *both* sides…, A live capture against the dev cluster found the previous implementation's bug…, verify_metrics() never carries a node selector at all -- nothing to rewrite,…, Even when the configured model is ``quantile``, the bundle is captured with… (+30 more)

### Community 31 - "run_concurrent"
Cohesion: 0.10
Nodes (35): concurrent_client_with(), datetime, The defining property of concurrency: `move_disk` for the second move is issued…, Each move's own UPID reaches both callbacks correctly attributed --…, Two otherwise-independent moves landing on the *same* target: even with…, Section 8.1's generalized invariant, live: san-c has only 2 TiB of headroom…, A leftover 1 TiB volume of VM 201 already on san-c when 201 launched (an orphan…, The deliberate simplification documented in `_execute_concurrent()`'s own… (+27 more)

### Community 32 - "pve-storage-drs manpage"
Cohesion: 0.06
Nodes (37): Release procedure (version bump, changelog, debian/ tag, graphify commit), A reference implementation that is well tested, Other backends, Telegraf with a Prometheus remote-write output, The failure mode: a transport that cannot carry strings, The six counters, Two things deliberately not used, What catches it (+29 more)

### Community 33 - "ResolvedConfig"
Cohesion: 0.11
Nodes (38): ResolvedConfig with path and sha256, Controllable now for byte-identical bundles, Namespace, _dump_report_json(), _filter_groups(), _handle_apply(), _handle_explain(), _handle_plan() (+30 more)

### Community 34 - "test_topology.py"
Cohesion: 0.15
Nodes (39): The cluster topology could not be built from the API responses. See…, TopologyError, build_topology(), datetime, Build the whole cluster's :class:`Topology` for this run. One pass: every read…, _lvm_def(), test_a_format_the_storage_type_cannot_hold_is_refused(), test_a_literal_entry_can_set_its_own_value() (+31 more)

### Community 35 - "TimeWindow"
Cohesion: 0.14
Nodes (36): date, auto mode budgets and time windows, One allowed time window for ``auto`` mode, an entry of…, TimeWindow, current_deadline(), _day_name(), is_window_active(), _parse_hhmm() (+28 more)

### Community 36 - "config.py"
Cohesion: 0.10
Nodes (37): jsonschema, ruamel_yaml, ruamel_yaml_error, _check_connection_config(), _check_forecast_window(), _check_group_names_unique(), _check_group_size(), _check_group_storage_membership() (+29 more)

### Community 37 - "order_moves"
Cohesion: 0.11
Nodes (36): order_moves(), _pending_moves(), Assignment, Section 8.1's transient invariant, called with the single-move set ``{disk}``…, Section 8.2 priority 1: is ``disk``'s *current* (in ``state``) storage…, Section 8.2's scheduling loop for one group. ``target_assignment`` is normally…, _resolves_reserve_violation(), transient_invariant_ok() (+28 more)

### Community 38 - "`proxmox` — the cluster API connection"
Cohesion: 0.06
Nodes (27): `metrics.labels.vmid`, `proxmox.auth.password`, `proxmox.auth.token_id`, `proxmox.auth.token_secret`, `proxmox.auth.username`, `proxmox.ca_file`, `proxmox.host`, `proxmox.port` (+19 more)

### Community 39 - "_sample_topology"
Cohesion: 0.08
Nodes (34): _all_pinned_sample_topology(), _fake_build_topology(), _fake_reconcile_inflight(), `_sample_topology()` plus a section 11.4 pattern expansion and one cluster…, Every `apply` test here uses `build_pve_client`'s "fake-client" string stand-…, `_sample_topology()` with its one movable disk pinned too: san-a violates (C5)…, X-05: cli.py used to build one bare topology (for the estimate check) and then…, A ``cli.build_topology`` stand-in that ignores the ``state``/``now`` cooldown… (+26 more)

### Community 40 - "topology.py"
Cohesion: 0.09
Nodes (35): concurrent_futures, Disk size resolution: content listing first, per VM node, _build_storages(), _ClusterData, content_item_size(), _default_format(), _disk_snapshot_or_orphan_reason(), _disk_specs_from_config() (+27 more)

### Community 41 - "_render_group_plan_human"
Cohesion: 0.12
Nodes (34): What this build actually implements, _log_plan_selected(), GroupLoad, ``(max_s u_s - min_s u_s) / u*`` -- gates.py's own imbalance formula (section…, Section 9.5: every ``v in V^split`` whose split excess the plan changes, plus…, The residual shortfall of ``final_breakdown`` (the assignment the plan actually…, Why ``plan``/``apply`` show a gate verdict of ACT and then no move. The gate…, One group's worth of ``_render_plan_human()``'s report -- shared with… (+26 more)

### Community 42 - "test_topology.py"
Cohesion: 0.08
Nodes (34): _allowed_formats(), pending_disk_reasons(), _pin_reason(), PVE tags as returned by `cluster/resources`: semicolon-separated, with comma…, Section 5.3 (C2): the disk formats ``storage_type`` can hold. An unrecognised…, Section 3.8: which disk device keys in ``GET .../pending`` (section 3.5's…, Section 5.3 (C2)'s pin conditions, in the order the plan lists them -- the…, _split_tags() (+26 more)

### Community 43 - "ResolvedConfig"
Cohesion: 0.07
Nodes (34): ArgumentParser, CommandHandler, --manual prefers man(1), falls back to in-tree markdown, --mode escalation rule, _accumulate_move_stats(), apply_mode_override(), build_parser(), _fallback_manual_text() (+26 more)

### Community 44 - "test_logging_setup.py"
Cohesion: 0.11
Nodes (33): Log levels, mandatory INFO floor and root handler, Structured logs go to stderr, io, configure_logging(), floor_for_command(), The mandatory ``INFO`` floor of section 2.3, or ``None``. A run that can change…, ``auto`` and ``text`` -> ``"text"``; ``json`` -> ``"json"``. JSON is opt-in. It…, Install this run's log handler. Called once, from ``main()``. ``floor`` is… (+25 more)

### Community 45 - "_handle_apply"
Cohesion: 0.07
Nodes (32): Forecast provenance report, Payback gate in apply (REVIEW S-02), Bounded re-plan loop; errors are not mismatches, _plan_group(): one pipeline for plan and apply, Mutable state box exception to functional style, _apply_payback_gate(), _compute_group_load(), _GroupPlan (+24 more)

### Community 46 - "State"
Cohesion: 0.11
Nodes (32): errno, fcntl, socket, Section 11.2: ``last_balance``/cooldowns are "updated only after a run that…, _record_executed_moves(), _active_cooldowns(), active_disk_cooldowns(), active_storage_cooldowns() (+24 more)

### Community 47 - "ExecutionConfig"
Cohesion: 0.13
Nodes (31): ExecutionConfig, When the tool waits for the source volume to disappear, from…, How and when moves run, from the ``execution`` block. - ``mode``…, SourceReleaseConfig, _group_with_types(), make_disk(), make_storage(), Section 9.3: a source_release timeout "does not fail the run: mark the storage… (+23 more)

### Community 48 - "IMPLEMENTATION_PLAN.md"
Cohesion: 0.09
Nodes (30): Big-M penalty P fallback (computed P_min), Migrations throttled by bwlimit only, (C4) Largest-disk linearization Z_s, (C6) Load spread, Storage capability weight and utilization u_s, Per-disk and per-storage cooldowns, Data spread as tunable delta preference, Deadlock and staging (+22 more)

### Community 49 - "test_documentation.py"
Cohesion: 0.12
Nodes (30): importlib_resources, needs_full_checkout, _flatten_schema_keys(), _load_schema(), _manpage_source_text(), _manual_documented_keys(), Any, parametrize (+22 more)

### Community 50 - "_plan_group"
Cohesion: 0.09
Nodes (29): auto backend cascade to heuristic, _log_gate_decision(), _log_load_digest(), _log_snapshot_pins(), _plan_group(), Section 5.5's backend dispatch. ``solver.backend: auto`` cascades CBC, then the…, Section 2.3's ``load_digest``: what section 4 measured, compactly enough to put…, Section 3.7 point 3, "Complain, every run, at WARN": one ``snapshot_pinned``… (+21 more)

### Community 51 - "29-explain.md"
Cohesion: 0.08
Nodes (26): A negative `saferemove_throughput` is normal, Prometheus outage degrades only per-group load, Seven Prometheus queries per group, Reading `show-load` and `verify-storages`, `show-load`, show-load command, The `Group <name> → ACT`/`NO ACTION` line, `verify-storages` (+18 more)

### Community 52 - "empty_state"
Cohesion: 0.16
Nodes (29): acquire_lock(), empty_state(), load_state(), _parse_state_text(), First-run state: no lock, no recorded balance, no cooldowns, nothing in flight…, The tolerant-parse half of :func:`load_state`, factored out so…, Best-effort read of ``path``. See the module docstring: a missing file is the…, Re-reads whatever is currently written through an already-open,… (+21 more)

### Community 53 - "exceptions.py"
Cohesion: 0.10
Nodes (25): AuthenticationError, contextlib, proxmoxer, random, requests, ResourceException, PveUnreachableError, A :class:`PveApiError` with ``transient`` set: the API could not be reached, or… (+17 more)

### Community 54 - "`migration` — cost, bandwidth and the payback rule"
Cohesion: 0.08
Nodes (28): saferemove wipe cost accounting, migration.bwlimit_bytes_per_sec, `migration` — cost, bandwidth and the payback rule, `migration.max_single_move_duration`, migration payback settings (payback_horizon, payback_ratio, max_single_move_duration), `migration.payback_horizon`, `migration.payback_ratio`, `migration.source_load_weight` (+20 more)

### Community 55 - "Overview: what is built, and how it fits together"
Cohesion: 0.09
Nodes (26): config.py depends on forecast.py via deferred import, Overview: what is built, and how it fits together, Module layout, Seven-stage pipeline: collect, join, gate, solve, cost, order, execute, Persistent state: state.json, staged_disks field unimplemented, State dataclass tree mirrors section 11.2 JSON, Forecasting: Holt-Winters scaling of each disk's load (+18 more)

### Community 56 - "config.py"
Cohesion: 0.09
Nodes (26): Config path resolution order, How a YAML file becomes a validated Config, Secrets from environment only when file value is null, Schema, build and semantic validation of the config, _build_config(), FreeSpaceConfig, _load_schema(), MonitoringConfig (+18 more)

### Community 57 - "FakeClock"
Cohesion: 0.12
Nodes (24): LocksConfig, Handling of VM and disk locks during execution, from ``execution.locks``. -…, FakeClock, log_messages(), LogCaptureFixture, `execution.locks.on_timeout: skip` (the default): the locked head times out…, `/cluster/tasks` shape for a task still running: no endtime/status., The reported failure: an earlier move's "Erase data" (imgdel) job still holds… (+16 more)

### Community 58 - "Assignment"
Cohesion: 0.14
Nodes (26): all_assignments(), best_lexicographic(), big_m_agreement_threshold(), E_of(), F_of(), objective_big_m(), objective_nonreserve(), payback() (+18 more)

### Community 59 - "make_config"
Cohesion: 0.13
Nodes (26): make_config(), make_prometheus_client(), make_pve_client(), --no-series must skip the big, per-group superset range captures -- it does not…, Y-06: the manifest's version fields are machine-generated provenance, not free…, X-09: the printed query count used to treat a multi-day range as one range…, Z-05: a live capture stores every range series at…, Section 3.8/16.3: a real pending edit on the VM's own disk survives as the… (+18 more)

### Community 60 - "heuristic.py"
Cohesion: 0.14
Nodes (22): Large-VM split gate, (C9) large-VM split excess term, Section 6's split gate: ``(vmid, reason)`` for the first large VM (``V^split``,…, split_gate(), _disk(), _footprints(), _group(), parametrize (+14 more)

### Community 61 - "._get"
Cohesion: 0.09
Nodes (15): Protocol, _disk_keys_seen(), Any, The subset of ``requests.Response`` this module relies on., Return the response body decoded from JSON., The subset of ``requests.Session`` this module relies on. A structural type…, Issue one request and return the decoded ``data`` field. Typed ``Any`` rather…, ``GET /api/v1/query``. Returns the raw ``data.result`` list. (+7 more)

### Community 62 - "test_free_space_repair_fixture.py"
Cohesion: 0.15
Nodes (24): `Σ_s r_s` at the assignment ``storage_of`` encodes -- section 7.3's outcome…, total_shortfall_bytes(), _free_space_repair_group(), _loads(), _make_disk(), _make_storage(), parametrize, tests/fixtures/free-space-repair.yaml, built as real topology objects.… (+16 more)

### Community 63 - "test_forecast.py"
Cohesion: 0.15
Nodes (23): _group_series(), _noise_series(), Any, TimeSeries, Holt-Winters forecasting, its backtest gate, and the required-range rule., Fewer than 2 * seasonal_periods samples before now - W: Holt-Winters cannot be…, A diurnal series that *ends at its trough*: the last forecast point (one day…, series_of() (+15 more)

### Community 64 - "exceptions.py"
Cohesion: 0.14
Nodes (21): Durations and sizes parsed once into canonical units, ConfigError, The configuration file is missing, unreadable or fails validation. See…, Exception hierarchy for the project. Every error the tool can raise…, format_bytes(), format_duration_seconds(), parse_duration_seconds(), parse_size_bytes() (+13 more)

### Community 65 - "format_bytes"
Cohesion: 0.10
Nodes (21): confirm callback owned by cli.py, _make_confirm_move_interactively(), confirm(), The economic test (``aggregate_ok``) and the hard per-move duration rule…, Section 5.3's "report any residual `r_s > 0` prominently as an unfixable…, Sum of the pinned bytes over every storage, in bytes., Return the pinned-disk summary as a JSON-ready dict. Byte values are in bytes.…, The human form of :class:`_UnfixableShortfall` -- printed whether or not the… (+13 more)

### Community 66 - "PveApiError"
Cohesion: 0.14
Nodes (21): PveApiError, The Proxmox VE API returned an error or an unusable response. See…, raise_error(), raise_error(), raise_error(), broken(), _client_with_fake_time(), _flaky() (+13 more)

### Community 67 - "_run_two_onto_san_c"
Cohesion: 0.09
Nodes (23): A `san-c` content responder plus a `move_disk` responder for 201. The listing…, 201's mirror target is already *listed* on san-c at its full 1 TiB by the time…, Between different storage types, or from thin to thick, `move_disk` allocates…, The match stays narrow: a same-VM volume that appeared after launch but has…, The exclusion is narrow: only 201's *own* mirror target (same VM, the disk's…, Section 8.1 / 5.3.3: VM 101 already has 3 TiB on san-b, another VM 3.5 TiB. A 1…, Between different storage types the target is allocated at the disk line's…, The same 2 TiB config `size=` and the same 4.5 TiB already on the target, but… (+15 more)

### Community 68 - "test_topology.py"
Cohesion: 0.13
Nodes (24): build_fake_client(), _content(), _pair(), Any, PveClient, Section 5.3 (C8): VM 301's only disk in this group is a 528 KiB efidisk0 (its…, Section 3.7 item 3: the operator must learn *which* volume blocks the VM. The…, A storage plugin can list a volid with no `size` key at all -- seen on a live… (+16 more)

### Community 69 - "Safety properties, exit codes, status"
Cohesion: 0.10
Nodes (22): Dry-run is the default, Command handler dispatch dict, Command dispatch, mode override and logging to stderr, free_space.soft / free_space.hard, solver.backend (auto, cbc, heuristic), `solver.heuristic_iterations`, `solver.mip_gap`, `solver.time_limit_seconds` (+14 more)

### Community 70 - "build_client"
Cohesion: 0.14
Nodes (19): Why proxmoxer: backend abstraction, ProxmoxConfig, PVE API endpoint and client settings, from the ``proxmox`` block. Fields, with…, build_client(), Construct a :class:`PveClient` from ``config.py``'s ``ProxmoxConfig``. Always…, _config(), _FakeHttpsBackend, _FakeProxmoxApiWithBackend (+11 more)

### Community 71 - "test_state.py"
Cohesion: 0.12
Nodes (22): ``state.path`` could not be written, or its advisory lock could not be…, StateError, cooldown_remaining_seconds(), _pid_alive(), Seconds left in ``key``'s cooldown -- ``0.0`` if nothing is recorded for it,…, Best-effort, used only to make a "still held" log message useful to an operator…, skipif, The `finally` block's own cleanup, pinned directly rather than only inferred… (+14 more)

### Community 72 - "test_small_disks.py"
Cohesion: 0.17
Nodes (22): current(), disk(), efi_repair_group(), parametrize, skipif, VM 301's big disks live in another group: its efidisk0 is alone here and never…, "slow" is short by 1000.2 MiB, so moving the 528 KiB EFI disk crosses a whole-…, Lexicographic stage 1 takes any shortfall reduction, however small, so without… (+14 more)

### Community 73 - "topology.py"
Cohesion: 0.14
Nodes (22): Storage name pattern expansion, GroupConfig, is_storage_pattern(), One storage entry in a group, from ``groups[].storages[]``. - ``id``…, A ``storages[].id`` value is a pattern iff it both begins and ends with ``/``…, The regular expression text of a pattern entry, its two ``/`` delimiters…, A balancing group, one entry of ``groups[]``. - ``name`` (``groups[].name``,…, storage_pattern_text() (+14 more)

### Community 74 - "forecast.py"
Cohesion: 0.13
Nodes (20): math, HoltWintersConfig, Holt-Winters model settings, from ``forecast.holt_winters``. -…, Backtest, holt_winters_quantile(), _quantile(), One group's backtest: absolute error of each model's predicted p95 of ``[now-W,…, True when Holt-Winters was fitted and its error is at most the baseline error.… (+12 more)

### Community 75 - "test_payback.py"
Cohesion: 0.18
Nodes (22): MigrationConfig, Cost model and limits for one disk move, from the ``migration`` block. -…, compute_move_cost(), Section 7.1's cost for one scheduled move. Only ``source`` is needed (not the…, move(), `saferemove=True` with no known throughput (e.g. never surfaced by `GET…, The regression this fixes, at the exact shape that found it: a real cluster…, The exemption above is from the *economic* test only -- the hard per-move… (+14 more)

### Community 76 - "Group"
Cohesion: 0.10
Nodes (21): Forecast applied as a ratio f_d/h_d, never a substitution, apply_forecast(): scaling, never replacing, compute_disk_load_series(): same blend as a time series, _blend_loads(), _combine_raw_values(), _combined_raw(), compute_disk_load_series(), TimeSeries (+13 more)

### Community 77 - "test_statusfile.py"
Cohesion: 0.22
Nodes (20): build_run_status(), The level policy (section 2.4). ``CRITICAL`` when the run exited non-zero: a…, stat, subprocess, ``statusfile.py`` (IMPLEMENTATION_PLAN.md section 2.4): the level policy, the…, report(), test_a_clean_dry_run_is_ok_and_says_nothing_moved(), test_a_clean_run_is_ok() (+12 more)

### Community 78 - "json_safe"
Cohesion: 0.10
Nodes (18): JsonFormatter and event-named log records, LogRecord, json_safe(), JsonFormatter, One human-readable line per record: ``LEVEL: message``. Deliberately not a…, Render ``record`` as one line of text. Records at level INFO or below print the…, Replace every non-finite float with ``None``, recursively. Python's JSON…, Render one :class:`logging.LogRecord` as one JSON line. (+10 more)

### Community 79 - "stitch_range_results"
Cohesion: 0.11
Nodes (17): Backtest gate: beat the persistence baseline, Range query chunking and stitching, Capture chunks range queries, stitches by query text, RangeStepMismatch, ``--replay`` found the requested range query, but at a different step than this…, _issue_chunked_range_query(), Any, ``client.range_query()``, issued in ``RANGE_QUERY_CHUNK_SECONDS``-sized sub-… (+9 more)

### Community 80 - "config/drs.example.yaml"
Cohesion: 0.12
Nodes (17): config/drs.example.yaml as documentation that parses, Never consider over-provisioning (provisioned size), config section exclude, config section forecast, config section groups, config section load_weights, config section metrics, config section migration (+9 more)

### Community 81 - "test_payback.py"
Cohesion: 0.14
Nodes (18): Reserve override: safety is not subject to hysteresis, ScheduleResult.final_assignment, Outcome-based reserve repair exemption, evaluate_plan_payback(), Section 7.3: the aggregate acceptance test over a whole plan, plus the hard…, no_saferemove_storage(), Reworked by section 5.4/7.2's affinity-payback fix: the plan splits VM 101…, The plan's own counter-example: a 4 TiB disk whose relocation improves E by… (+10 more)

### Community 82 - "`execution` — how (and whether) moves actually happen"
Cohesion: 0.11
Nodes (18): `execution.abort_on_failure`, `execution` — how (and whether) moves actually happen, `execution.locks.on_timeout`, `execution.locks.poll_interval`, `execution.locks.task_retry_backoff`, `execution.locks.task_retry_limit`, `execution.locks.wait_timeout`, `execution.max_concurrent_migrations` (+10 more)

### Community 83 - "generate_expected.py"
Cohesion: 0.14
Nodes (17): itertools, computed_p_min(), cost(), Deadlock, duration(), duration_mirror(), duration_wipe(), load_fixture() (+9 more)

### Community 84 - "case_for"
Cohesion: 0.20
Nodes (18): StorageState, best_big_m(), build(), capacity_spread(), case_for(), moves_of(), order_moves(), per_storage() (+10 more)

### Community 85 - "test_statusfile.py"
Cohesion: 0.13
Nodes (15): datetime, os, Storage DRS for Proxmox VE 9.2. Balances disk I/O load across configurable…, _one_line(), Collapse any run of whitespace, newlines included, to one space: a newline…, The file's exact text: level, summary ``| perfdata``, details, and a trailing…, The monitoring status file: one ``apply`` run's outcome, in the format the…, What one ``apply`` run did, as the level policy needs it. ``errors`` are… (+7 more)

### Community 86 - "apply modes: dry-run, confirm, auto"
Cohesion: 0.12
Nodes (17): execution.source_release wait and timeout, `migration.assume_thick_provisioning`, Deadlock report (report, never force), Transient reserve invariant, Concurrent execution with strict FIFO launch, confirm prompt [y]es/[n]o/[a]ll/[q]uit, draining status, apply modes: dry-run, confirm, auto (+9 more)

### Community 87 - "apply_forecast"
Cohesion: 0.17
Nodes (16): _aggregate_storages(), apply_forecast(), DiskLoad, GroupLoad, Convenience for callers (``show-load``) keying off `Disk.key`., Each storage's ``L_s``/``u_s`` from its disks' ``l_d``, and the group's ``u*``…, Section 12.1 point 2: scale each disk's ``l_d`` by its forecast factor ``f_d /…, One disk's `ℓ_d`. Section 4. (+8 more)

### Community 88 - "metrics.py"
Cohesion: 0.12
Nodes (17): build_node_selector(), _escape_promql_regex_literal(), Escape one literal string for safe use inside a PromQL/RE2 ``=~`` alternation.…, Section 3.4's auto-derived node-scoping filter: ``<node_label>=~"n1|n2|..."``…, The one selector every query in this module inserts, resolved once per run…, resolve_node_selector(), A node named `pve1.example.com` must match only that exact string in RE2 -- an…, `metrics.extra_selector` wins outright, even over a real node list -- the… (+9 more)

### Community 89 - "FakePrometheusSession"
Cohesion: 0.18
Nodes (17): FakePrometheusSession, A ``metrics._SessionLike`` double capable of answering *many* distinct queries…, _instant_answer(), _range_answer(), A live capture against the dev cluster found this one directly (section 16.3's…, A live capture against the dev cluster found this directly:…, A live capture found this the hard way: ``_check_sample_series()``'s "info"…, Z-02: `_check_coverage()`'s per-disk warning embeds a real vmid taken straight… (+9 more)

### Community 90 - "Testing (.agents)"
Cohesion: 0.12
Nodes (16): Release process (version, changelog, tag, graphify), Autopkgtest as the dependency test, Debian-first dependency policy (trixie), Testing (.agents), Acceptance fixtures and generate_expected.py, 85 percent coverage floor, No network, no real sleep, deterministic ties in tests, Higher bar for safety-critical modules (+8 more)

### Community 91 - "Logging"
Cohesion: 0.12
Nodes (15): support section (salt_path, bundle_dir, max_series_points, capture_range), `collect-testdata`: capturing a bundle, Diagnostic bundles: `collect-testdata` and `--replay`, `--replay`: running against a bundle offline, Sending one to the project, What is in a bundle, and what is not, Per-command implementation status table, Logging (+7 more)

### Community 92 - "check_paper_log.py"
Cohesion: 0.15
Nodes (12): argparse, pathlib, sys, skipif, ``__version__`` must agree with ``pyproject.toml`` and the install instructions., test_install_instructions_name_the_current_version(), check(), _logical_lines() (+4 more)

### Community 93 - "Reading `explain`"
Cohesion: 0.16
Nodes (12): `measured load:`, `no moves made: ...` / `closest alternative: ...`, `pinned load ... ; best achievable spread given pins: ...`, `pinned (not movable this run):`, Reading `explain`, The `forecast:` line, The `objective:` line, `-v`: the `data source:` line (+4 more)

### Community 94 - "_apply_connection_pool_size"
Cohesion: 0.17
Nodes (12): _apply_connection_pool_size(), Size the underlying ``requests`` session's connection pool to fit…, _FakeProxmoxApiWithSession, _FakeSession, Any, Confirmed live against a real multi-VM cluster: `requests`'s own default…, A small `read_workers` (or the field's own minimum) must not shrink the pool…, A plain string, an object with no ``_store``, or a session-shaped object with… (+4 more)

### Community 95 - "test_state.py"
Cohesion: 0.16
Nodes (15): LastBalance, load_vector_for_group(), ``at`` is ``None`` before any run has ever executed a migration -- distinct…, This group's slice of ``last_balance.load_vector``, re-keyed from…, Pure: a new :class:`State` with ``group_name``'s slice of…, with_recorded_balance(), Distinct from `{}` -- `gates.py`'s `last_load=None` means "no such run has ever…, `"fc-tier10:101:scsi0"` must not leak into `"fc-tier1"`'s vector -- the… (+7 more)

### Community 96 - "Fixture"
Cohesion: 0.13
Nodes (7): Fixture, Section 5.3 (C7): `(Sum_d z_d + Sum_s U^ext) / (Sum_s C_s)` -- the group's mean…, Section 5.4's `D^big` threshold, converted from the fixture's…, Section 5.4's mu (``objective.mu_vm_split_per_tib``), 0 when the split rule is…, ``{vmid: T_v}`` for ``V^split`` (section 5.3.3), written out independently of…, Section 5.4's `w_v = max(1, l_v / l_bar)`. `V` (the vmids this returns weights…, One group: its storages, its disks and the weights to solve it with. ``keys``…

### Community 97 - "save_locked_state"
Cohesion: 0.20
Nodes (14): Inflight UPIDs persisted for crash recovery, Write UPID to disk before the crash can happen, _make_inflight_callbacks(), on_finished(), on_started(), Builds the ``on_inflight_started``/``on_inflight_finished`` pair…, LockHandle, Pure: adds ``upid`` to ``state.inflight_upids`` (a no-op if already present).… (+6 more)

### Community 98 - "build_rate_promql()"
Cohesion: 0.15
Nodes (14): Pure PromQL builders, build_rate_promql(), The section 3.4 per-metric rate expression. ``sum by (vmid, device)…, _group_selector(), _quantile_promql(), _rate_promql(), The one combined selector `compute_group_load()`/`compute_disk_load_series()`…, The exact PromQL `_fetch_raw_quantity` builds for one raw field -- computed… (+6 more)

### Community 99 - "PaybackResult"
Cohesion: 0.16
Nodes (11): What `plan` does not yet do, _log_payback_verdict(), Section 2.3's ``payback_verdict``: section 7's arithmetic, not just its yes/no…, PaybackResult, Sum of the move costs of the plan, in load-seconds. This is the sum of…, Benefit of the plan divided by its total move cost. Dimensionless. Returns…, True when the plan passes the payback test and no single move is rejected. The…, One plan's section 7.3 acceptance verdict. ``aggregate_ok`` (``benefit >=… (+3 more)

### Community 100 - "Reading `apply`"
Cohesion: 0.14
Nodes (13): Concurrent execution, Crash and two-instance recovery, Failure and `abort_on_failure`, `--json`, Reading `apply`, Reading `auto` mode, `state.json`: what a real run actually changes, The `[y]es/[n]o skip/[a]ll remaining/[q]uit` prompt (+5 more)

### Community 101 - "pytest"
Cohesion: 0.16
Nodes (12): fixture, json, logging, pytest, Section 2.3's ladder: ``--quiet`` < default < ``-v`` < ``-vv``. ``--log-level``…, Logging policy. See IMPLEMENTATION_PLAN.md section 2.3. Every log record goes…, resolve_level(), Shared pytest fixtures. ``logging`` is process-global state, and… (+4 more)

### Community 102 - "_mapper"
Cohesion: 0.14
Nodes (12): _mapper(), Any, BaseException, _Raise, X-09: `manifest.json`'s `counts.dropped_records` is documented as counting…, A task's ``id`` is the vmid its UPID embeds. It used to be copied raw, leaving…, _tasks_by_kind(), test_anonymize_cluster_tasks_maps_the_task_id_with_the_upid() (+4 more)

### Community 103 - "test_payback.py"
Cohesion: 0.18
Nodes (13): Section 7.1: PVE hands `saferemove_throughput` straight to `cstream -t`, where…, Migration cost and the payback test. See proxmox_storage_drs/payback.py. Cross-…, Storage `a`: 6 TiB disk on a 10 TiB storage, `reserve_factor=2.0` -- required…, The direct case: the sole move IS what repairs `a`'s violation, so holding it…, Storage `a` (6 TiB, f=2) holds two single-disk 2 TiB VMs: 4 + 2*2 = 8 > 6,…, Section 7.3: two moves from a violating storage, either of which alone repairs…, _revert_test_group(), test_a_redundant_repair_plan_is_exempt_with_no_marked_move() (+5 more)

### Community 104 - "repair_markers"
Cohesion: 0.15
Nodes (11): Per-move repair marker revert test, executed_assignment(), Assignment, Section 7.3: "what it will really run" -- ``final_assignment``…, Section 7.3's revert test, one verdict per scheduled move in ``order``: would…, repair_markers(), A move whose disk never carried the group's own violation (nothing here needed…, Per-VM footprint (section 5.3.3): VM 101's two disks on `a` make a 3 TiB… (+3 more)

### Community 105 - "gates section"
Cohesion: 0.18
Nodes (13): Running timer on exactly one host, execution.api_outage_timeout (read retry with back-off), gates section, `gates.capacity_spread_threshold`, `gates.cooldown_per_disk`, `gates.cooldown_per_storage`, `gates` — deciding whether to act at all, `gates.drift_threshold` (+5 more)

### Community 106 - "IMPLEMENTATION_PLAN.md"
Cohesion: 0.18
Nodes (13): Negative saferemove_throughput is normal, Configuration and validation rules, Disk identity join (vmid, device), Failure handling (orphans, partial plan, supervision loss), Do not switch to OpenTelemetry metric server, Prometheus per-disk blockstat metrics, Proxmox VE API, Requirements traceability (+5 more)

### Community 107 - "disk_factors"
Cohesion: 0.31
Nodes (12): disk_factors(), ``f_d / h_d`` for every disk that has one: ``f_d`` the Holt-Winters forecast…, _factor_series(), _FixedForecast, MonkeyPatch, 96 hourly samples whose last 24 are ``window_values`` (repeated)., Patches ``holt_winters_quantile`` to a constant so the ratio is exact., test_disk_factors_is_forecast_over_observed_p95() (+4 more)

### Community 108 - "FakeProxmoxResource"
Cohesion: 0.22
Nodes (5): FakeProxmoxResource, FakeQueryResponse, Any, Shared test doubles. Not collected by pytest (no ``test_`` prefix).…, Matches ``metrics._ResponseLike``: ``.status_code`` and ``.json()``.

### Community 109 - "`metrics` — Telegraf/InfluxDB name mapping"
Cohesion: 0.17
Nodes (12): load_weights normalize, blend and rescale, `metrics.labels.device`, `metrics.labels.node`, `metrics.pvestatd_push_interval`, `metrics.rate_window`, `metrics.read_bytes`, `metrics.read_ops`, `metrics.read_time_ns` (+4 more)

### Community 110 - "test_payback.py"
Cohesion: 0.17
Nodes (12): compute_benefit_load_seconds(), Section 7.2: ``benefit = (alpha*(E_before - E_after) + delta*(F_before -…, The mu*dO term is what pays here: kappa*dA alone is negative., test_payback_without_the_mu_term_would_reject(), A plan that makes imbalance worse (possible if beta/gamma/kappa dominate) must…, Section 7.2: "dA may be negative, and then it reduces the benefit: a balance…, Section 14.7's affinity-repair fixture in miniature: two tiny disks reunite…, Section 7.2: `mu * (O_before - O_after) * H`, and a negative `dO` reduces the… (+4 more)

### Community 111 - "_outcome"
Cohesion: 0.30
Nodes (12): _gate(), _no_move_schedule(), _outcome(), Any, A replayed dev-cluster bundle: capacity spread 112 %, I/O balanced, the gate…, At 2 * delta <= gamma the data-spread term cannot pay for a move of any size,…, The local cluster bundle under minmax: one disk carries 80 % of the group's…, test_a_capacity_gated_empty_plan_names_the_two_weights_that_decided_it() (+4 more)

### Community 112 - "evaluate_assignment(): shared section 5.4 objective"
Cohesion: 0.18
Nodes (11): Data-spread term d_s in absolute TiB, evaluate_assignment(): shared section 5.4 objective, objective.spread_metric l1 vs minmax, Unscaled CBC model in MiB, CP-SAT backend removal (REVIEW AL-02), The MILP backend: CBC via pulp, Concurrent execution with strict FIFO, No double counting of in-flight mirror targets (+3 more)

### Community 113 - "Test corpus tests/corpus/"
Cohesion: 0.20
Nodes (11): Anonymization allowlist, never denylist, CBC via PuLP MILP backend, CP-SAT (ortools) backend removed, Dependencies come from Debian trixie, Diagnostic bundles (collect-testdata), Heuristic fallback (repair, descend, polish), Keyed pseudonyms with salt, Debian packaging, autopkgtest and two CI pipelines (+3 more)

### Community 114 - "topology.py"
Cohesion: 0.22
Nodes (11): FreeSpaceValue, One parsed-but-unresolved ``free_space.soft``/``.hard`` entry (section 5.3.1's…, _free_space_level(), _free_space_source(), Section 5.3.1: an absolute value is used as written; a percentage is…, One storage's resolved ``soft_s``/``hard_s`` and where each came from (section…, ``level`` (global / storage entry / pattern ``/re/``), plus the percent-to-…, Section 5.3.1: resolve ``soft_s``/``hard_s`` for one storage. The mandated… (+3 more)

### Community 115 - "test_statusfile.py"
Cohesion: 0.18
Nodes (11): DrsError, ExecutionError, MetricsError, Exception, Base class for every error this project raises on purpose., Prometheus could not be queried, or the response was unusable. See…, Neither solver backend could produce a feasible or heuristic plan. See…, No pending move in a plan is individually feasible right now. See… (+3 more)

### Community 116 - "FakeClock"
Cohesion: 0.20
Nodes (8): MoveCost, Section 7.1's cost for one already-scheduled move., Total time of one move, in seconds. This is the mirror time plus the wipe time:…, Section 9.1: the pre-loop time-window check (above) only knows the answer as of…, REVIEW.md T-06's collateral bug: before the fix, this "skipped" outcome let the…, test_deadline_recheck_after_a_lock_wait_refuses_a_move_that_no_longer_fits(), test_deadline_recheck_after_a_lock_wait_stops_the_whole_run_not_just_this_move(), status_current()

### Community 117 - "_exec_group"
Cohesion: 0.24
Nodes (11): _exec_disk(), _exec_group(), _posted_move(), Any, The live transient check charges the converted size from the live `size=`., test_a_converting_move_is_refused_when_the_live_check_finds_no_room(), test_a_live_format_that_differs_from_the_plan_means_replan(), test_format_is_not_sent_when_the_disk_already_has_the_enforced_format() (+3 more)

### Community 118 - "Transient invariant"
Cohesion: 0.22
Nodes (10): config section execution, draining state (source not yet released), enforce_format per-storage target format, A finished task is not a finished move, free_space configuration (soft/hard floors), LVM saferemove and saferemove_throughput, Migration scheduling algorithm, Deadlock resolution and staging moves (+2 more)

### Community 119 - "Cooldowns"
Cohesion: 0.20
Nodes (10): flock is the lock; JSON lock field is only a label, Rename-detaches-flock bug and in-place locked write, Any, Raises on any shape this module does not recognize -- the caller…, Writes ``state`` **in place** into the already-open, already-locked ``fd`` --…, _state_from_dict(), _state_to_dict(), _write_state_to_locked_fd() (+2 more)

### Community 120 - "build_topology() one-pass join"
Cohesion: 0.20
Nodes (10): Cross-metric disk consistency check for silently dropped fields, Node-scoping selector, verify_metrics() check functions, The Proxmox VE API client, PveClient: one method per endpoint, Building the disk/storage/group model, D: every placed disk, pinned or not, build_topology() one-pass join (+2 more)

### Community 121 - "reserve.py shared (C4)/(C5) footprint evaluator"
Cohesion: 0.20
Nodes (10): Unfixable-shortfall report, storage_content() silently empty without Datastore.Allocate, Foreign volume usage U_ext, free_space soft_s/hard_s resolution, reserve.py shared (C4)/(C5) footprint evaluator, Unconditional reserve repair, Lexicographic two-stage reserve solve, Live transient check at provisioned size (+2 more)

### Community 122 - "IMPLEMENTATION_PLAN.md"
Cohesion: 0.22
Nodes (10): The heuristic solver, beta/gamma migration count and bytes terms, (C2) Eligibility via variable fixing, (C8) Small disks follow their VM, MILP optimization problem, Online-movable disk set (all buses, efidisk0, tpmstate0, unused), Disks with unapplied pending change excluded, Disks with snapshots excluded, loudly (+2 more)

### Community 123 - "move_disk (drive-mirror, delete=1)"
Cohesion: 0.22
Nodes (10): `monitoring` — telling your monitoring system what the last run did, Global command-line options and --mode override logging, PVE 9.2 Dynamic Load Balancer relationship, Execution modes (dry-run default, confirm, auto), Monitoring status file, move_disk (drive-mirror, delete=1), Disks count at provisioned size, never over-provisioned, Re-plan protocol and errors-are-not-mismatches (+2 more)

### Community 124 - "Objective function (alpha, beta, gamma, kappa, delta, mu, P)"
Cohesion: 0.22
Nodes (10): (C3) VM affinity linking, Companion fixture affinity repair, large-vm-split companion fixture, kappa VM affinity term weighted by w_v, (C9) Large-VM split rule (split_vm_footprint, mu), Migration benefit over horizon H, Objective function (alpha, beta, gamma, kappa, delta, mu, P), Pinned disks are modelled, not ignored (+2 more)

### Community 125 - "split_gate_opens()"
Cohesion: 0.20
Nodes (10): eligible_storages(), excess_of(), peak_footprint(), Section 5.3 (C2): every storage whose `allowed_formats` holds this disk's own…, Section 5.3 (C5)/5.3.1: `R_s = max(f_s * Z_s, soft_s)`., ``max_s F_{v,s}`` -- the peak share of one VM any single storage holds., Section 5.3.3 (C9): ``O = sum_{v in V^split} o_v`` in TiB, ``o_v = max(0,…, Section 6's split gate, restated independently of ``gates.split_gate()``: some… (+2 more)

### Community 126 - "test_affinity_repair_fixture.py"
Cohesion: 0.33
Nodes (9): _affinity_repair_group(), _loads(), _make_disk(), _make_storage(), parametrize, tests/fixtures/affinity-repair.yaml, built as real topology objects., IMPLEMENTATION_PLAN.md section 14.7's fixture, exercised through the real…, test_both_milp_backends_agree_with_the_heuristic() (+1 more)

### Community 127 - "RangeStepMismatch"
Cohesion: 0.27
Nodes (4): FakeResponse, Any, A ``range_query`` stand-in that returns caller-supplied data keyed by the exact…, _WindowTrackingFakeClient

### Community 128 - "test_topology.py"
Cohesion: 0.24
Nodes (10): _one_vm_two_storage_cluster(), Section 5.3.1: ``hard_s > soft_s`` is a validation error -- a floor above the…, Section 5.3.1: ``soft_s >= C_s`` is a validation error -- a requirement no disk…, Section 3.5: ``verify-storages`` shows the resolved pair *with the level each…, _sources(), test_build_topology_rejects_a_hard_floor_above_its_resolved_soft(), test_build_topology_rejects_a_soft_floor_not_below_capacity(), test_free_space_provenance_global_percent_without_a_hard() (+2 more)

### Community 129 - "test_docstrings.py"
Cohesion: 0.31
Nodes (8): ast, Path, Return ``file:line name`` for each public class or function in ``path`` that…, Every public class and function in the package has a docstring (AGENTS.md…, The scan itself must work: it has to flag a bare public function and a bare…, test_every_public_definition_has_a_docstring(), test_scanner_flags_a_missing_docstring(), _undocumented_public_items()

### Community 130 - "forecast_group"
Cohesion: 0.22
Nodes (9): Collection, forecast_group(), group_aggregate_series(), Sum every disk's own series into one group-aggregate series, at the union of…, One group's forecast: run the backtest on the group aggregate, and only if…, 101:scsi0 has no sample at t=1 at all -- that timestamp still appears (from…, test_group_aggregate_series_empty_input_is_empty(), test_group_aggregate_series_missing_disk_at_a_timestamp_contributes_zero() (+1 more)

### Community 131 - "save_state_atomic"
Cohesion: 0.28
Nodes (9): Reading degrades, writing raises, LockInfo, Temp file in the same directory, ``fsync``, then ``os.replace`` -- a reader…, Descriptive only -- see the module docstring's "Locking" section for why the…, save_state_atomic(), A crashed run's `flock()` is released by the kernel on process exit, so the…, test_acquire_lock_overwrites_a_stale_lock_field_left_by_a_dead_process(), test_load_state_round_trips_a_full_document() (+1 more)

### Community 132 - "test_topology.py"
Cohesion: 0.28
Nodes (9): disk_state_key(), ``"<group>:<vmid>:<device>"`` (section 11.2) -- the group prefix is what keeps…, _one_disk_cluster(), The default (`state=None`) must be indistinguishable from an empty state --…, test_build_topology_does_not_pin_once_the_cooldown_has_expired(), test_build_topology_ignores_another_groups_cooldown_entry(), test_build_topology_pins_a_disk_within_its_cooldown(), test_build_topology_pins_disks_on_an_excluded_storage() (+1 more)

### Community 133 - "test_plan_gate_also_reflects_real_drift_history_from_state_json"
Cohesion: 0.25
Nodes (9): _imbalanced_group_load(), _no_reserve_violation_topology(), GroupLoad, Two storages, generously sized -- unlike `_sample_topology()`, no (C4)/(C5)…, san-a all the load, san-b none -- imbalance is 200% of `u*`, far above the…, Baseline for the next test: with no `state.json` at all, `last_load` is `None`,…, The same fixture as above, except `state.json` now records a `last_balance`…, test_show_load_acts_on_imbalance_when_there_is_no_state_json_yet() (+1 more)

### Community 134 - "test_statusfile.py"
Cohesion: 0.43
Nodes (8): CompletedProcess, needs_plugin, Path, A guard on the guard: these are the two ways a status file goes wrong (wrong-…, run_plugin(), test_check_statusfile_calls_a_stale_file_warning_and_a_missing_one_unknown(), test_check_statusfile_reads_what_we_write(), test_the_plugin_rejects_the_shapes_the_module_never_writes()

### Community 135 - "delta data spread weight per TiB"
Cohesion: 0.25
Nodes (8): config section gates, config section objective, (C7) Capacity-spread linearization in absolute TiB, Capacity gate (section 6), delta data spread weight per TiB, Plan output and explain narration, Relative-fill capacity form rejected, Break-even disk size X* = beta/(2delta-gamma)

### Community 136 - "test_statusfile.py"
Cohesion: 0.29
Nodes (7): Monitoring status file (statusfile.py), Write ``status`` to ``path`` atomically, mode 0644, creating the parent…, The status file could not be written., StatusFileError, write_status_file(), MonkeyPatch, test_a_failed_replace_removes_the_temporary_file()

### Community 137 - "Migration cost and payback test"
Cohesion: 0.25
Nodes (8): kappa weighted by VM I/O (w_v) and D^big, Plan benefit in load-seconds, Payback horizon H, Affinity term in benefit, No materiality floor on benefit, Raw terms, never weighted terms (REVIEW R-01), affinity-repair fixture (plan 14.7), kappa*dA affinity benefit isolation

### Community 138 - "`exclude` — what DRS never touches"
Cohesion: 0.25
Nodes (8): `exclude.disks`, `exclude.include_unused_disks`, `exclude.running_only`, `exclude.skip_vms_with_snapshots`, `exclude.storages`, `exclude.tags`, `exclude.vmids`, `exclude` — what DRS never touches

### Community 139 - "forecast.py"
Cohesion: 0.39
Nodes (8): ForecastConfig, Forecast settings, from the ``forecast`` block. - ``model``…, The history ``forecast.model`` needs, in seconds. Called by ``config.py``'s…, required_range_seconds(), test_holt_winters_required_range_is_the_lookback_when_that_is_longer(), test_holt_winters_required_range_matches_plan_worked_example(), test_quantile_required_range_is_the_lookback(), test_required_range_unknown_model_raises()

### Community 140 - "metrics.py"
Cohesion: 0.25
Nodes (8): _check_cross_metric_disk_consistency(), format_cross_metric_finding(), Builds :func:`_check_cross_metric_disk_consistency`'s one finding shape from a…, Flags a disk reported by *some* of the six configured metrics but not others --…, REVIEW.md-worthy real-world failure: Telegraf's Prometheus-compatible output…, test_cross_metric_disk_consistency_silent_when_all_metrics_agree(), test_cross_metric_disk_consistency_truncates_a_long_missing_list(), test_cross_metric_disk_consistency_warns_on_a_dropped_field()

### Community 141 - "test_apply_exits_quietly_when_state_json_is_already_locked"
Cohesion: 0.25
Nodes (5): `_balanced_apply_topology()`'s one move easily clears the default…, test_apply_exits_quietly_when_state_json_is_already_locked(), test_apply_refuses_the_whole_plan_when_the_aggregate_payback_test_fails(), fail(), test_real_local_now_falls_back_when_the_zone_cannot_be_resolved()

### Community 142 - "test_enforce_format.py"
Cohesion: 0.36
Nodes (8): parametrize, Path, With 64 KiB clusters qcow2 needs an 8-byte L2 and a 2-byte refcount entry per…, test_config_has_no_global_enforce_format(), test_config_parses_enforce_format(), test_config_rejects_a_value_other_than_raw_qcow2_or_null(), test_lvm_qcow2_bound_is_never_below_qemus_default_layout(), _write()

### Community 143 - "Pin priority _pin_reason() (C2)"
Cohesion: 0.29
Nodes (7): Cooldown data stored here, interpreted by topology and solvers, Disk-cooldown pin is not exempted for reserve repair, Pin priority _pin_reason() (C2), Storage cooldown excludes destinations; repair exempt, MILP storage cooldown and fixed-zero pairs, Recording balance and cooldowns after execution, Startup scan folds in-flight vmids into exclude.vmids

### Community 144 - "Payback acceptance test"
Cohesion: 0.33
Nodes (7): Worked example fixture fc-tier1, free-space-repair companion fixture, Free-space repair mandate, max_single_move_duration hard rule, Payback acceptance test, Repair exemption (outcome trigger and revert test), Reserve override

### Community 145 - "(C4)/(C5) Snapshot reserve and free-space constraint"
Cohesion: 0.40
Nodes (6): config section free_space, config section snapshot_reserve, Unsized volume fallbacks and approximate-size, (C4)/(C5) Snapshot reserve and free-space constraint, Failure modes and never-trade-the-reserve rule, Foreign usage U_ext computation

### Community 146 - "_vm_splits"
Cohesion: 0.33
Nodes (5): One large VM's (``V^split``, section 5.3.3) before/after numbers for the report., Return the split figures of this VM as a JSON-ready dict. Byte values keep…, Section 9.5's ``split:`` lines. A result still above its cap says the solver…, _render_split_lines(), _VmSplit

### Community 147 - "Assignment"
Cohesion: 0.40
Nodes (6): footprint_on(), largest_on(), Section 5.3.3's ``F_{v,s}``: the sum of VM ``vmid``'s disks on ``s`` -- every…, Section 5.3 (C4) ``Z_s`` = ``max_v F_{v,s}``, the largest per-VM footprint on…, Section 8.1: the snapshot term's basis while ``key`` mirrors onto ``b``,…, transient_basis()

### Community 149 - "_FakeClient"
Cohesion: 0.40
Nodes (3): str, _FakeClient, The ``"fake-client"`` sentinel every ``build_pve_client`` mock in this file…

### Community 150 - "test_optimize.py"
Cohesion: 0.40
Nodes (5): LogCaptureFixture, The defect that prompted IMPLEMENTATION_PLAN.md section 2.3, in the operator's…, The other half: an operator who wrote `solver.backend: cbc` and is silently not…, test_a_missing_optional_solver_is_not_a_warning_under_auto(), test_an_explicitly_configured_solver_that_is_missing_still_warns()

### Community 151 - "test_optimize.py"
Cohesion: 0.50
Nodes (4): cbc_available(), True when the ``pulp`` module can be imported. This does not check that the CBC…, MonkeyPatch, test_cbc_available_is_false_when_pulp_is_not_importable()

### Community 155 - "last_load drift baseline"
Cohesion: 0.67
Nodes (3): Drift history reaches the gates via last_balance, Drift baseline is the effective load, last_load drift baseline

### Community 156 - "loadmodel.py"
Cohesion: 0.67
Nodes (3): _is_metrics_expected_absent(), parametrize, test_is_metrics_expected_absent()

### Community 157 - "fc-tier1 fixture (plan 14 worked example)"
Cohesion: 0.67
Nodes (3): fc-tier1 fixture (plan 14 worked example), generate_expected.py exhaustive enumeration, beta x delta sweep contract

## Knowledge Gaps
- **278 isolated node(s):** `Transient reserve invariant (operator explanation)`, `(C4) Largest-disk linearization Z_s`, `Deadlock and staging`, `14b Holt-Winters-driven l_d`, `Prometheus per-disk blockstat` (+273 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1621 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **35 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Group` connect `test_optimize.py` to `execute.py`, `collect.py`, `metrics.py`, `test_cli.py`, `test_heuristic.py`, `Path`, `test_plan_gate_also_reflects_real_drift_history_from_state_json`, `CaptureFixture`, `compute_reserve_status`, `test_execute.py`, `GroupLoad`, `RecordingPveClient`, `Group`, `test_enforce_format.py`, `Disk`, `Disk`, `MonkeyPatch`, `cli.py`, `run_concurrent`, `test_topology.py`, `order_moves`, `Group`, `_sample_topology`, `topology.py`, `_render_group_plan_human`, `ResolvedConfig`, `_handle_apply`, `ExecutionConfig`, `_plan_group`, `heuristic.py`, `test_free_space_repair_fixture.py`, `format_bytes`, `test_small_disks.py`, `Group`, `apply_forecast`, `build_rate_promql()`, `PaybackResult`, `test_payback.py`, `repair_markers`, `FakeClock`, `_exec_group`, `test_affinity_repair_fixture.py`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Why does `Configuration reference` connect `Configuration reference` to `Safety properties, exit codes, status`, ``proxmox` — the cluster API connection`, `gates section`, ``exclude` — what DRS never touches`, `Logging`, ``metrics` — Telegraf/InfluxDB name mapping`, ``execution` — how (and whether) moves actually happen`, `20-verifying-metrics.md`, ``migration` — cost, bandwidth and the payback rule`, `move_disk (drive-mirror, delete=1)`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Why does `.agents/ index` connect `AGENTS.md working agreement` to `pve-storage-drs manpage`, `Safety properties, exit codes, status`, `20-verifying-metrics.md`, `Testing (.agents)`, `Logging`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Are the 217 inferred relationships involving `Group` (e.g. with `_accumulate_move_stats()` and `_apply_payback_gate()`) actually correct?**
  _`Group` has 217 INFERRED edges - model-reasoned connections that need verification._
- **Are the 89 inferred relationships involving `Disk` (e.g. with `_footprint_text()` and `_fragmented_vms()`) actually correct?**
  _`Disk` has 89 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Transient reserve invariant (operator explanation)`, `(C4) Largest-disk linearization Z_s`, `Deadlock and staging` to the rest of the system?**
  _278 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `execute.py` be split into smaller, more focused modules?**
  _Cohesion score 0.044062244062244064 - nodes in this community are weakly interconnected._