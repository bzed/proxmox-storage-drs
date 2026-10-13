# Graph Report - proxmox-storage-drs  (2026-10-13)

## Corpus Check
- 133 files · ~342,168 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4073 nodes · 11170 edges · 236 communities (175 shown, 61 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 1510 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- MonkeyPatch
- build_topology
- _sample_topology
- Config
- test_config.py
- Topology
- Installation and requirements
- test_cli.py
- test_loadmodel.py
- test_metrics.py
- case_for
- test_execute.py
- Group
- topology.py
- Configuration reference
- GroupLoad
- optimize.py
- test_payback.py
- _balanced_apply_topology
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
- _run_two_onto_san_c
- TimeWindow
- Monitoring status file
- empty_state
- test_holt_winters_quantile_clamps_at_zero
- C5 Capacity, snapshot reserve and free space
- ExecutionConfig
- test_topology.py
- `metrics` — Telegraf/InfluxDB name mapping
- configure_logging
- free_space requirement soft_s / hard_s
- order_moves
- Transient invariant
- test_forecast.py
- _patch_forecast_deps
- test_state.py
- Overview page
- _anonymize_captured_prometheus
- test_documentation.py
- loadmodel.py
- test_statusfile.py
- BundleError
- cli.py
- Packaging, dependencies and CI (.agents)
- test_large_vm_split_fixture.py
- build_client
- Execute page
- Proxmox Storage DRS Implementation Plan
- _state_from_dict
- forecast_group
- _plan_group
- crashrecovery.py
- forecast.py
- test_affinity_repair_fixture.py
- test_small_disks.py
- move_disk (drive-mirror, delete=1)
- Reading `apply`
- Internals: Building the disk/storage/group model
- Where the numbers come from, and how a transport loses them
- pve-storage-drs.1.md
- excess_of
- test_reserve.py
- Disk
- fragmentation
- PveApiError
- holt_winters_quantile
- `migration` — cost, bandwidth and the payback rule
- test_show_load_gate_reflects_real_drift_history_from_state_json
- _exec_group
- `prometheus` — the metrics source
- filter_vm_config_fields
- capture_bundle
- ReplayPveClient
- json_safe
- _FakeClient
- PrometheusClient
- Internals: CLI dispatch and logging
- config.py
- _ResponseLike
- Python style (.agents)
- state.py
- State
- test_holt_winters_quantile_is_none_for_a_non_finite_forecast
- Mapper
- disk_factors
- _FakeSession
- FakeProxmoxResource
- pytest
- Manual: Reading plan
- MoveCost
- Manual: Configuration reference
- test_holt_winters_quantile_forecasts_ceil_window_over_step_steps
- Proxmox VE API
- save_locked_state
- _group_vmid_batches
- test_holt_winters_quantile_is_none_on_a_convergence_warning
- Payback rule and acceptance test
- proxmox_storage_drs
- Community 110
- _rebase_all_timestamps
- Community 112
- check_paper_log.py
- execute.py
- Community 115
- Community 116
- Any
- Logging: what lands where, and what an unattended run records
- split_gate_opens
- collect.py
- Community 121
- AGENTS.md working agreement
- Transient reserve invariant (operator explanation)
- Community 124
- `objective` — the solver's trade-off weights
- Path
- Assignment
- Diagnostic bundles: `collect-testdata` and `--replay`
- filters.lua
- _findings_to_json
- Community 131
- _join_vm_disks
- Community 133
- Monitoring: the status file
- Community 135
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
- resolve_level
- tests/__init__.py
- integration/__init__.py
- unit/__init__.py
- Configuration page
- Community 154
- test_unfixable_shortfall_is_proven_only_for_an_optimal_cbc_solve
- test_logging_setup.py
- Community 157
- proxmox-storage-drs
- FakeClock
- Community 160
- Community 161
- Community 162
- Community 163
- Community 164
- Community 165
- build_node_selector
- build_site.sh
- Community 168
- Community 169
- Community 170
- Community 171
- Community 172
- Community 173
- Community 174
- Community 175
- Community 176
- Community 177
- Persistent state: state.json
- Community 179
- Community 180
- Community 181
- Community 182
- Community 183
- Community 184
- metrics.py
- Community 186
- Community 187
- Community 188
- Community 190
- Community 191
- Community 192
- Community 193
- Community 194
- Community 195
- Community 196
- Community 197
- Community 198
- Community 199
- Community 200
- generate_expected.py
- Community 202
- Community 203
- Community 204
- Community 205
- Community 206
- Community 207
- Community 208
- Community 209
- Community 210
- Community 211
- Community 212
- Community 213
- Community 214
- Community 215
- Community 216
- Community 217
- Community 218
- Community 219
- Community 220
- Community 221
- Community 222
- Community 223
- Community 224
- Community 225
- Community 226
- Community 227
- Community 228
- Community 229
- Community 230
- Community 231
- Community 232

## God Nodes (most connected - your core abstractions)
1. `Group` - 229 edges
2. `PveClient` - 125 edges
3. `Disk` - 109 edges
4. `run()` - 84 edges
5. `write_config()` - 83 edges
6. `make_move()` - 81 edges
7. `client_with()` - 79 edges
8. `Storage` - 75 edges
9. `build_topology()` - 74 edges
10. `PrometheusClient` - 68 edges

## Surprising Connections (you probably didn't know these)
- `The `Group <name> → ACT`/`NO ACTION` line` --references--> `GroupLoad`  [INFERRED]
  docs/manual/25-show-load-and-verify-storages.md → src/proxmox_storage_drs/loadmodel.py
- `What is in the file` --references--> `duration()`  [INFERRED]
  docs/manual/36-monitoring.md → tests/fixtures/generate_expected.py
- `What `plan` does not yet do` --references--> `GroupLoad`  [INFERRED]
  docs/manual/27-plan.md → src/proxmox_storage_drs/loadmodel.py
- `staged_disks field unimplemented` --references--> `State`  [EXTRACTED]
  docs/internals/15-state.md → src/proxmox_storage_drs/state.py
- ``report`` --references--> `report()`  [INFERRED]
  docs/manual/10-configuration.md → tests/unit/test_statusfile.py

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

## Communities (236 total, 61 thin omitted)

### Community 0 - "MonkeyPatch"
Cohesion: 0.05
Nodes (90): _apply_payback_gate(), ConfirmCallback, Section 7.3's hard per-move duration rule (``rejected_moves``) rendered as…, Section 7.3's payback verdict gates *execution*, not merely the report…, _refused_move_outcomes(), ExcludeConfig, _active_task_on_vm(), _advance_pending() (+82 more)

### Community 1 - "build_topology"
Cohesion: 0.03
Nodes (65): load_config(), Resolve, read, parse and validate the configuration. See section 11 for…, _breakdown_with_split(), _fake_reconcile_inflight(), _NodeNamesClient, LogCaptureFixture, Every `apply` test here uses `build_pve_client`'s "fake-client" string stand-…, REVIEW.md R-02: when the scheduler can only order *some* of the heuristic's… (+57 more)

### Community 2 - "_sample_topology"
Cohesion: 0.07
Nodes (80): minimal_config_dict(), Any, parametrize, Path, skipif, The smallest config that passes structural + semantic validation., Config loading, resolution order and section 11.1 semantic validation., There is no ``metrics.labels.cluster`` any more -- an earlier revision's… (+72 more)

### Community 3 - "Config"
Cohesion: 0.06
Nodes (81): active_split_caps(), best_single_disk_alternative(), compute_vm_weights(), evaluate_assignment(), group_average_utilization(), Section 5.5 step 1: "seed with the current assignment (not from scratch -- we…, `u* = (Sum_d l_d) / (Sum_s c_s)` (C6) -- a constant under any reassignment of…, ``{vmid: T_v}`` for ``V^split`` (section 5.3.3), or empty when the rule is off… (+73 more)

### Community 4 - "test_config.py"
Cohesion: 0.07
Nodes (68): The whole cluster's worth of groups, as seen by this run. By the time anything…, Topology, _fragmented_group(), _make_group_plan(), _moved_outcome(), _one_disk_group(), _one_disk_group_load(), _one_move() (+60 more)

### Community 5 - "Topology"
Cohesion: 0.06
Nodes (69): MigrationConfig, compute_benefit_load_seconds(), compute_move_cost(), evaluate_plan_payback(), executed_assignment(), Assignment, Section 7.1's cost for one scheduled move. Only ``source`` is needed (not the…, Section 7.2: ``benefit = (alpha*(E_before - E_after) + delta*(F_before -… (+61 more)

### Community 6 - "Installation and requirements"
Cohesion: 0.05
Nodes (70): compute_reserve_status(), largest_disk_bytes(), largest_footprint(), largest_footprint_bytes(), managed_used_bytes(), ``(Z_s, vmid)`` of a ``{vmid: F_{v,s}}`` map: the largest footprint and the VM…, Z_s: the largest per-VM footprint on ``storage_id`` under ``storage_of``, 0 if…, The largest single disk on ``storage_id``, 0 if none. **Not** ``Z_s``: the… (+62 more)

### Community 7 - "test_cli.py"
Cohesion: 0.06
Nodes (63): _all_pinned_sample_topology(), _patch_show_load_deps(), _patch_show_load_forecast(), CaptureFixture, Exception, ForecastReport, parametrize, `_sample_topology()` with san-b given more headroom (16 TiB instead of 8):… (+55 more)

### Community 8 - "test_loadmodel.py"
Cohesion: 0.07
Nodes (66): needs_cbc, Solve one group with ``backend`` (``"cbc"``). ``probing`` says this backend was…, solve(), disk_size_on(), qcow2_lvm_allocation_bytes(), Upper bound on the LV ``alloc_image`` creates for a ``qcow2`` volume of…, Section 5.3.2's ``z_{d,s}``, in bytes: what ``disk`` occupies when placed on…, tests_unit (+58 more)

### Community 9 - "test_metrics.py"
Cohesion: 0.08
Nodes (62): ExecutionResult, One group's ``execute_plan()`` call. ``stopped_early`` is true for any reason…, _balanced_apply_group_load(), _balanced_apply_topology(), _check_statusfile(), _monitored_config(), _patch_plan_deps(), MonkeyPatch (+54 more)

### Community 10 - "case_for"
Cohesion: 0.07
Nodes (63): GatesConfig, evaluate_group_gates(), _l1_drift(), GroupLoad, Section 6, applied in the order it lists: reserve override, then the capacity…, ``(‖ℓ_last‖₁, ‖ℓ_now − ℓ_last‖₁)`` over the **union** of disk keys present in…, One storage's (C4)/(C5) evaluation at a given assignment., ReserveStatus (+55 more)

### Community 11 - "test_execute.py"
Cohesion: 0.09
Nodes (60): client_with(), default_group(), make_move(), parametrize, Fails safe: a volume with neither `size` nor `approximate-size` makes the…, A PVE API error while re-reading the target refuses the move and fails the run…, A move missing from `move_costs_by_key` is never refused for lack of an…, Section 13: `state.json` must learn about a UPID *before* this function goes on… (+52 more)

### Community 12 - "Group"
Cohesion: 0.07
Nodes (50): concurrent_futures, dataclasses, _RepairCandidate, _capacity_spread(), Section 6: decide whether to act on a group at all, before the solver runs.…, Section 5.3 (C7)'s `(max_s b_s - min_s b_s) / b_bar`, or ``None`` when the gate…, _best_of(), _best_repair_candidate() (+42 more)

### Community 13 - "topology.py"
Cohesion: 0.06
Nodes (56): jsonschema, ruamel_yaml, ruamel_yaml_error, _build_config(), _check_connection_config(), _check_forecast_window(), _check_group_size(), _check_group_storage_membership() (+48 more)

### Community 14 - "Configuration reference"
Cohesion: 0.08
Nodes (54): ObjectiveConfig, _cbc_capacity_spread_term(), _cbc_feasibility_constraints(), _cbc_objective_terms(), _cbc_small_disks_follow_their_vm(), _cbc_split_excess_term(), _cbc_storage_load(), _cbc_storage_used_mib() (+46 more)

### Community 15 - "GroupLoad"
Cohesion: 0.04
Nodes (53): Anonymization allowlist, never denylist, Big-M penalty P fallback (computed P_min), Migrations throttled by bwlimit only, (C2) Eligibility via variable fixing, (C3) VM affinity linking, (C4) Largest-disk linearization Z_s, (C6) Load spread, (C8) Small disks follow their VM (+45 more)

### Community 16 - "optimize.py"
Cohesion: 0.11
Nodes (52): cbc_available(), make_disk(), make_storage(), MonkeyPatch, parametrize, Deliberately *not* parametrized over the skip-guarded `BACKENDS` list above --…, Section 5.4's D^big: at beta_move_count=1.0, moving `201:efidisk0` (1 MiB) to…, IMPLEMENTATION_PLAN.md section 14.3's "delta knob, demonstrated at the… (+44 more)

### Community 17 - "test_payback.py"
Cohesion: 0.07
Nodes (45): The `payback:` line, functools, gzip, A value two bundles can compare to prove they share a mapping, without…, salt_fingerprint(), _anonymize_captured_prometheus(), _anonymize_prometheus_series(), _anonymize_query_text() (+37 more)

### Community 18 - "_balanced_apply_topology"
Cohesion: 0.06
Nodes (42): make_mapper(), MonkeyPatch, parametrize, Path, A node and a storage that happen to share a name must not collide., Section 16.3: 'the result never depends on iteration order'., Force two different vmids to hash to the same base slot and confirm both still…, X-09: `vmid`'s own linear probing makes a collision impossible, but nothing did… (+34 more)

### Community 19 - "pve.py"
Cohesion: 0.16
Nodes (49): LoadWeights, compute_group_load(), Compute one group's :class:`GroupLoad` for this run. Section 4.…, Group, One storage group: section 5's independent optimization unit., _client(), full_coverage(), make_disk() (+41 more)

### Community 20 - "test_optimize.py"
Cohesion: 0.06
Nodes (49): GroupConfig, StorageConfig, _allowed_formats(), _build_storages(), _check_cross_group_uniqueness(), _ClusterData, content_item_size(), _default_format() (+41 more)

### Community 21 - "Fixture"
Cohesion: 0.09
Nodes (47): tests_corpus, tests_corpus_validate_corpus, _case(), _invariant_inputs(), MonkeyPatch, needs_full_checkout, parametrize, Path (+39 more)

### Community 22 - "test_validate_corpus.py"
Cohesion: 0.11
Nodes (42): PrometheusConfig, _captured_step(), _config_from_bundle(), _free_space_pairs(), MonkeyPatch, Path, AH-06: a live ``free_space`` config is collected as the resolved per-storage…, Section 16.5's one deliberate exception: a bundle captured before section 3.8… (+34 more)

### Community 23 - "test_replay.py"
Cohesion: 0.13
Nodes (44): The cluster topology could not be built from the API responses. See…, TopologyError, build_topology(), datetime, State, Build the whole cluster's :class:`Topology` for this run. One pass: every read…, _cluster_client(), make_config() (+36 more)

### Community 24 - "run_concurrent"
Cohesion: 0.11
Nodes (39): _check_observed_spacing(), PrometheusClient, Thin wrapper over the Prometheus HTTP API. See section 3.4/3.5. ``session`` is…, Section 3.3 step 6: observed sample spacing vs. ``pvestatd_push_interval``.…, FakeResponse, FakeSession, _full_metrics_config(), Any (+31 more)

### Community 25 - ".agents/documentation.md"
Cohesion: 0.09
Nodes (36): FakeProxmoxResource, concurrent_client_with(), datetime, The defining property of concurrency: `move_disk` for the second move is issued…, Each move's own UPID reaches both callbacks correctly attributed --…, Two otherwise-independent moves landing on the *same* target: even with…, Section 8.1's generalized invariant, live: san-c has only 2 TiB of headroom…, A leftover 1 TiB volume of VM 201 already on san-c when 201 launched (an orphan… (+28 more)

### Community 26 - "PveClient"
Cohesion: 0.08
Nodes (40): CaptureEstimate, shutil, _capacity_gate_hint(), _footprint_text(), _fragmented_vms(), _load_per_tib(), _objective_breakdown_json(), _pin_action_hint() (+32 more)

### Community 27 - "test_anonymize.py"
Cohesion: 0.09
Nodes (38): capture(), Path, X-08: section 16.1's manifest line ("schema, versions, what was captured...")…, X-08: section 16.3 promises the manifest "flags" a non-node-shaped…, Z-03: `resolve_node_selector()`'s tier-1 precedence used to win on *both* sides…, A live capture against the dev cluster found the previous implementation's bug…, verify_metrics() never carries a node selector at all -- nothing to rewrite,…, Even when the configured model is ``quantile``, the bundle is captured with… (+30 more)

### Community 28 - "Internals: The heuristic solver"
Cohesion: 0.11
Nodes (24): filter_allowed_fields(), Drop every key of ``obj`` not in ``allowed``. The one primitive both the…, The one meaningful value a snapshot ``name`` field can carry is the literal…, sanitize_snapshot_name(), _anonymize_cluster_tasks(), _anonymize_node_list(), _anonymize_storage_content(), _anonymize_storage_definitions() (+16 more)

### Community 29 - "`execution` — how (and whether) moves actually happen"
Cohesion: 0.12
Nodes (33): What `plan` does not yet do, What this build actually implements, _log_plan_selected(), GroupLoad, ``(max_s u_s - min_s u_s) / u*`` -- gates.py's own imbalance formula (section…, Section 9.5: every ``v in V^split`` whose split excess the plan changes, plus…, The residual shortfall of ``final_breakdown`` (the assignment the plan actually…, Why ``plan``/``apply`` show a gate verdict of ACT and then no move. The gate… (+25 more)

### Community 30 - "test_collect.py"
Cohesion: 0.09
Nodes (36): PveClient, One method per IMPLEMENTATION_PLAN.md section 3.5 endpoint. ``api`` is typed…, Retry idempotent calls that fail because the API is unreachable for up to…, Section 9.2: "convert at the call site and nowhere else" -- this is that site., A ticket that expired for reasons external to this call (a long confirm-mode…, A successful re-login does not guarantee the retried call succeeds -- e.g. the…, The default (and what every other test double in this suite uses): a bare…, PveClient and build_client(). See proxmox_storage_drs/pve.py. No test here… (+28 more)

### Community 31 - "test_free_space_repair_fixture.py"
Cohesion: 0.11
Nodes (36): order_moves(), _pending_moves(), Assignment, Section 8.1's transient invariant, called with the single-move set ``{disk}``…, Section 8.2 priority 1: is ``disk``'s *current* (in ``state``) storage…, Section 8.2's scheduling loop for one group. ``target_assignment`` is normally…, _resolves_reserve_violation(), transient_invariant_ok() (+28 more)

### Community 32 - "_run_two_onto_san_c"
Cohesion: 0.15
Nodes (34): date, TimeWindow, current_deadline(), _day_name(), is_window_active(), _parse_hhmm(), datetime, ``execution.time_windows``: when ``auto`` mode may execute moves. See… (+26 more)

### Community 33 - "TimeWindow"
Cohesion: 0.07
Nodes (31): hashlib, hmac, MappingType, pathlib, re, filter_disk_value_params(), filter_vm_config_fields(), filter_vm_pending_entries() (+23 more)

### Community 34 - "Monitoring status file"
Cohesion: 0.08
Nodes (33): _balanced_non_violating_topology(), _fake_build_topology(), `_sample_topology()` plus a section 11.4 pattern expansion and one cluster…, Unlike `_sample_topology()`, san-a here does *not* violate (C5) -- needed to…, X-05: cli.py used to build one bare topology (for the estimate check) and then…, A ``cli.build_topology`` stand-in that ignores the ``state``/``now`` cooldown…, Section 7.1's signed `saferemove_throughput`, end to end: the configured value…, Section 3.5 / AH-04: the resolved pair is printed with its provenance, in both… (+25 more)

### Community 35 - "empty_state"
Cohesion: 0.08
Nodes (17): Any, Replace the session after a transport failure, best effort. A TLS handshake…, :meth:`_call_once`, retried while the failure is transient. Only ``idempotent``…, ``GET /cluster/resources?type=vm``: VM inventory., ``GET /cluster/tasks``: recent/active tasks across **every** node -- the one…, ``GET /cluster/resources?type=storage``: storage inventory., ``GET /nodes``: every node in the cluster, by name. Section 3.4's node-scoping…, ``GET /version``: the running PVE's own version string (section 16.1/16.3's… (+9 more)

### Community 36 - "test_holt_winters_quantile_clamps_at_zero"
Cohesion: 0.15
Nodes (33): acquire_lock(), empty_state(), load_state(), First-run state: no lock, no recorded balance, no cooldowns, nothing in flight…, Best-effort read of ``path``. See the module docstring: a missing file is the…, Section 11.2's advisory lock: ``fcntl.flock(LOCK_EX | LOCK_NB)`` on ``path``…, Clears the descriptive ``lock`` field and releases the OS-level lock, writing…, release_lock() (+25 more)

### Community 37 - "C5 Capacity, snapshot reserve and free space"
Cohesion: 0.07
Nodes (33): ArgumentParser, CommandHandler, _accumulate_move_stats(), apply_mode_override(), build_parser(), _fallback_manual_text(), _log_run_summary(), main() (+25 more)

### Community 38 - "ExecutionConfig"
Cohesion: 0.09
Nodes (32): Disk-cooldown pin is not exempted for reserve repair, pending_disk_reasons(), _pin_reason(), Section 3.8: which disk device keys in ``GET .../pending`` (section 3.5's…, Section 5.3 (C2)'s pin conditions, in the order the plan lists them -- the…, _one_vm_two_storage_cluster(), _pair(), Section 5.3 (C2) lists cooldown before the lock check -- both being true at… (+24 more)

### Community 39 - "test_topology.py"
Cohesion: 0.09
Nodes (21): `metrics.labels.vmid`, `proxmox.auth.token_id`, _check_no_pseudonym_collision(), Mapper, pseudonym(), ``HMAC-SHA256(salt, kind || "\\0" || value)``, truncated to 8 hex chars.…, 32-bit (8 hex char) truncation makes a same-``kind`` collision astronomically…, The single per-bundle offset :meth:`Mapper.rebase_timestamp` applies: the… (+13 more)

### Community 40 - "`metrics` — Telegraf/InfluxDB name mapping"
Cohesion: 0.13
Nodes (33): Namespace, _dump_report_json(), _filter_groups(), _handle_collect_testdata(), _handle_explain(), _handle_plan(), _handle_show_load(), _handle_verify_metrics() (+25 more)

### Community 41 - "configure_logging"
Cohesion: 0.09
Nodes (32): _drive_group_series(), Section 16.2 bullets 2-3, one raw metric at a time: the two…, build_vmid_selector(), _check_cross_metric_disk_consistency(), _check_metric_names_exist(), _check_sample_series(), combine_selectors(), _disk_keys_seen() (+24 more)

### Community 42 - "free_space requirement soft_s / hard_s"
Cohesion: 0.10
Nodes (30): Cooldown data stored here, interpreted by topology and heuristic, errno, fcntl, socket, _active_cooldowns(), active_disk_cooldowns(), active_storage_cooldowns(), cooldown_remaining_seconds() (+22 more)

### Community 43 - "order_moves"
Cohesion: 0.11
Nodes (30): Backtest gate, Drift baseline is effective load, Forecast provenance report, Forecast scaling ratio, Forecasting page, Holt-Winters forecast, statsmodels optional, Gigapipe step workaround (+22 more)

### Community 44 - "Transient invariant"
Cohesion: 0.11
Nodes (29): _RawTimeSeries, _combine_raw_values(), _combined_raw(), _fetch_all_raw_quantities(), _fetch_all_raw_quantity_series(), _fetch_raw_quantity(), _fetch_raw_quantity_series(), _per_disk_lookup() (+21 more)

### Community 45 - "test_forecast.py"
Cohesion: 0.15
Nodes (29): ExecutionConfig, SourceReleaseConfig, _group_with_types(), make_disk(), make_storage(), Section 9.3: a source_release timeout "does not fail the run: mark the storage…, Same as above, except the second move's *target* -- not source -- is the…, Section 9.3 point 3: PVE's own `saferemove_throughput` (already read live off… (+21 more)

### Community 46 - "_patch_forecast_deps"
Cohesion: 0.12
Nodes (27): LocksConfig, _exec_group(), _posted_move(), Any, The live transient check charges the converted size from the live `size=`., test_a_converting_move_is_refused_when_the_live_check_finds_no_room(), test_a_live_format_that_differs_from_the_plan_means_replan(), test_format_is_not_sent_when_the_disk_already_has_the_enforced_format() (+19 more)

### Community 47 - "test_state.py"
Cohesion: 0.09
Nodes (29): PrometheusClient, _compute_group_load(), _GroupPlan, _log_gate_decision(), _log_load_digest(), _log_payback_verdict(), _plan_group(), datetime (+21 more)

### Community 48 - "Overview page"
Cohesion: 0.13
Nodes (20): hash_label_name(), hash_query_text(), The cache key both this module (writing) and ``replay.py`` (reading) derive a…, BundleError, RangeStepMismatch, ``--replay`` found the requested range query, but at a different step than this…, A diagnostic bundle (IMPLEMENTATION_PLAN.md section 16) could not be written or…, bundle_reference_now() (+12 more)

### Community 49 - "_anonymize_captured_prometheus"
Cohesion: 0.10
Nodes (24): AuthenticationError, contextlib, proxmoxer, PveApiError, random, requests, ResourceException, _api_error() (+16 more)

### Community 50 - "test_documentation.py"
Cohesion: 0.07
Nodes (24): A negative `saferemove_throughput` is normal, Negative saferemove_throughput is normal, Reading `show-load` and `verify-storages`, `show-load`, show-load command, The `Group <name> → ACT`/`NO ACTION` line, ACT / NO ACTION gate verdict line, verify-storages command (+16 more)

### Community 51 - "loadmodel.py"
Cohesion: 0.14
Nodes (26): importlib_resources, _flatten_schema_keys(), _load_schema(), _manpage_source_text(), _manual_documented_keys(), Any, needs_full_checkout, parametrize (+18 more)

### Community 52 - "test_statusfile.py"
Cohesion: 0.13
Nodes (26): MetricLabels, MetricsConfig, _check_device_label_collision(), Section 3.3 step 4: warn if the device label is literally ``instance``. PVE's…, test_metrics.py's own ``_StepAwareFakeClient``, restated here for…, metrics.step >= metrics.rate_window (the failing gigapipe boundary, see…, --replay backward compatibility, the raw-series counterpart of…, A range wider than ``metrics.RANGE_QUERY_CHUNK_SECONDS`` (1d) is split into… (+18 more)

### Community 53 - "BundleError"
Cohesion: 0.13
Nodes (26): make_config(), make_prometheus_client(), make_pve_client(), --no-series must skip the big, per-group superset range captures -- it does not…, Y-06: the manifest's version fields are machine-generated provenance, not free…, X-09: the printed query count used to treat a multi-day range as one range…, Z-05: a live capture stores every range series at…, Section 3.8/16.3: a real pending edit on the VM's own disk survives as the… (+18 more)

### Community 54 - "cli.py"
Cohesion: 0.14
Nodes (24): Crash and two-instance recovery: crashrecovery.py, cluster/tasks vs task_status conventions differ, parse_upid PVE UPID grammar confirmed live, reconcile_inflight: recorded UPIDs plus foreign scan, Two failure modes, one in-flight UPID mechanism, AuthConfig, expected_task_user(), parse_upid() (+16 more)

### Community 55 - "Packaging, dependencies and CI (.agents)"
Cohesion: 0.10
Nodes (22): _make_confirm_move_interactively(), confirm(), The economic test (``aggregate_ok``) and the hard per-move duration rule…, Section 5.3's "report any residual `r_s > 0` prominently as an unfixable…, The human form of :class:`_UnfixableShortfall` -- printed whether or not the…, Only called when the gate decided to ACT but the *final* assignment moves…, ``None`` for a group ``apply`` never got as far as executing (a load error, or…, Builds ``execute.py``'s ``ConfirmCallback`` -- the only ``input()`` call in… (+14 more)

### Community 56 - "test_large_vm_split_fixture.py"
Cohesion: 0.15
Nodes (24): `Σ_s r_s` at the assignment ``storage_of`` encodes -- section 7.3's outcome…, total_shortfall_bytes(), _free_space_repair_group(), _loads(), _make_disk(), _make_storage(), parametrize, tests/fixtures/free-space-repair.yaml, built as real topology objects.… (+16 more)

### Community 57 - "build_client"
Cohesion: 0.08
Nodes (24): A `san-c` content responder plus a `move_disk` responder for 201. The listing…, 201's mirror target is already *listed* on san-c at its full 1 TiB by the time…, Between different storage types, or from thin to thick, `move_disk` allocates…, The match stays narrow: a same-VM volume that appeared after launch but has…, The exclusion is narrow: only 201's *own* mirror target (same VM, the disk's…, Section 8.1 / 5.3.3: VM 101 already has 3 TiB on san-b, another VM 3.5 TiB. A 1…, Between different storage types the target is allocated at the disk line's…, The same 2 TiB config `size=` and the same 4.5 TiB already on the target, but… (+16 more)

### Community 58 - "Execute page"
Cohesion: 0.13
Nodes (24): configure_logging(), floor_for_command(), The mandatory ``INFO`` floor of section 2.3, or ``None``. A run that can change…, Install this run's log handler. Called once, from ``main()``. ``floor`` is…, CaptureFixture, INFO at a terminal is the narrative the operator asked for; prefixing every…, `propagate = False` on the package logger would hide every record from pytest's…, One handler, on root, with the package logger carrying only a level: a second… (+16 more)

### Community 59 - "Proxmox Storage DRS Implementation Plan"
Cohesion: 0.16
Nodes (23): Section 5.3 (C8): a small disk ends a plan either where it is now, or on a…, small_disk_placement_ok(), current(), disk(), efi_repair_group(), parametrize, skipif, VM 301's big disks live in another group: its efidisk0 is alone here and never… (+15 more)

### Community 60 - "_state_from_dict"
Cohesion: 0.15
Nodes (23): Configuration reference, migration section payback rule, objective.mu_vm_split_per_tib, objective section, `objective.affinity_counts_pinned_disks`, `objective.alpha_spread`, `objective.beta_move_count`, `objective.delta_capacity_spread` (+15 more)

### Community 61 - "forecast_group"
Cohesion: 0.16
Nodes (21): ProxmoxConfig, _apply_ticket_refresh_seconds(), _build_api(), build_client(), REVIEW.md P-01: wire ``proxmox.ticket_refresh_seconds`` through, best-effort.…, Construct a :class:`PveClient` from ``config.py``'s ``ProxmoxConfig``. Always…, Construct one fresh, logged-in ``proxmoxer.ProxmoxAPI``. Split out of…, _config() (+13 more)

### Community 62 - "_plan_group"
Cohesion: 0.15
Nodes (20): ConfigError, The configuration file is missing, unreadable or fails validation. See…, Exception hierarchy for the project. Every error the tool can raise…, format_bytes(), format_duration_seconds(), parse_duration_seconds(), parse_size_bytes(), Render a duration in seconds as a human-readable string, e.g. ``"2.2h"``. (+12 more)

### Community 63 - "crashrecovery.py"
Cohesion: 0.19
Nodes (8): PveApiError, PveUnreachableError, The Proxmox VE API returned an error or an unusable response. See…, A :class:`PveApiError` with ``transient`` set: the API could not be reached, or…, Any, Unlike every other method here, a missing file is not a bundle defect: a bundle…, Serves ``pve.py``'s eleven read methods from a bundle's ``pve/`` directory.…, ReplayPveClient

### Community 64 - "forecast.py"
Cohesion: 0.11
Nodes (15): holt_winters_quantile(), ``window.quantile`` of the Holt-Winters forecast path over the next…, Any, A diurnal series that *ends at its trough*: the last forecast point (one day…, series_of(), test_backtest_is_none_without_a_fit_half(), test_backtest_is_none_without_an_actual_half(), test_holt_winters_quantile_clamps_at_zero() (+7 more)

### Community 65 - "test_affinity_repair_fixture.py"
Cohesion: 0.16
Nodes (20): Section 6's split gate: ``(vmid, reason)`` for the first large VM (``V^split``,…, split_gate(), _disk(), _footprints(), _group(), parametrize, No single move lowers a peak of 4 on three storages (4, 4, 2 -> 2, 4, 4)., The counterfactual recorded in the expected file. (+12 more)

### Community 66 - "test_small_disks.py"
Cohesion: 0.10
Nodes (22): Domain invariants (.agents), Dry-run is the default, Enumerate every disk bus, Finished task is not a finished move, Never auto-delete a volume, Provisioned size, never allocated, Disks with snapshots pinned, Snapshot reserve never traded for balance (+14 more)

### Community 67 - "move_disk (drive-mirror, delete=1)"
Cohesion: 0.20
Nodes (20): Section 13's startup scan. Returns the vmids to exclude from this run's…, reconcile_inflight(), fake_api(), BaseException, Shared test doubles. Not collected by pytest (no ``test_`` prefix).…, The same in-flight move already recorded in state.json also shows up in the…, Startup crash/two-instance recovery. See proxmox_storage_drs/crashrecovery.py., test_reconcile_assumes_still_running_when_the_check_itself_fails() (+12 more)

### Community 68 - "Reading `apply`"
Cohesion: 0.15
Nodes (18): _client_with_fake_time(), _flaky(), Exception, parametrize, test_5xx_is_transient_and_tolerance_is_restored(), test_authorization_and_malformed_requests_are_hard_errors(), test_failed_session_rebuild_does_not_mask_the_retry(), test_flaky_network_failures_are_transient_and_retried() (+10 more)

### Community 69 - "Internals: Building the disk/storage/group model"
Cohesion: 0.11
Nodes (19): config section objective, Storage cooldown excludes destination, Descend swaps and whole-VM moves, evaluate_assignment objective, Unconditional repair, objective.spread_metric, w_v and D^big, auto backend cascade (+11 more)

### Community 70 - "Where the numbers come from, and how a transport loses them"
Cohesion: 0.16
Nodes (17): ForecastReport, Any, What one group's forecast did this run -- the ``forecast`` block of ``explain``…, _group_series(), _noise_series(), TimeSeries, Holt-Winters forecasting, its backtest gate, and the required-range rule., Fewer than 2 * seasonal_periods samples before now - W: Holt-Winters cannot be… (+9 more)

### Community 71 - "pve-storage-drs.1.md"
Cohesion: 0.23
Nodes (19): build_run_status(), The level policy (section 2.4). ``CRITICAL`` when the run exited non-zero: a…, stat, subprocess, ``statusfile.py`` (IMPLEMENTATION_PLAN.md section 2.4): the level policy, the…, report(), test_a_clean_dry_run_is_ok_and_says_nothing_moved(), test_a_clean_run_is_ok() (+11 more)

### Community 72 - "excess_of"
Cohesion: 0.18
Nodes (20): best_lexicographic(), big_m_agreement_threshold(), E_of(), F_of(), objective_big_m(), objective_nonreserve(), payback(), Assignment (+12 more)

### Community 73 - "test_reserve.py"
Cohesion: 0.18
Nodes (20): build_fake_client(), _content(), _one_disk_cluster(), Any, Section 5.3 (C8): VM 301's only disk in this group is a 528 KiB efidisk0 (its…, Section 3.7 item 3: the operator must learn *which* volume blocks the VM. The…, A storage plugin can list a volid with no `size` key at all -- seen on a live…, The same content-listing gap, for a foreign (unreferenced) volume counted… (+12 more)

### Community 74 - "Disk"
Cohesion: 0.13
Nodes (17): Mutable state box narrow exception to functional style, Startup scan folds excluded vmids before planning, LockHandle, _apply_exit_code(), _handle_apply(), _InflightStateBox, _make_inflight_callbacks(), InflightCallback (+9 more)

### Community 75 - "fragmentation"
Cohesion: 0.13
Nodes (12): FakeResponse, FakeSession, no_coverage(), Any, _RangeStepMismatchFakeClient, 0/2 samples: present in the coverage series but with nothing in it., Answers `/api/v1/query` and `/api/v1/query_range` by the exact `query` param…, A ``range_query`` stand-in that returns caller-supplied data keyed by the exact… (+4 more)

### Community 76 - "PveApiError"
Cohesion: 0.12
Nodes (16): config section migration, auto mode timewindow, Concurrent execution, Done needs four conditions, VM locks open set, Orphans reported never deleted, Payback gate in apply, Live re-validation of every move (+8 more)

### Community 77 - "holt_winters_quantile"
Cohesion: 0.14
Nodes (17): itertools, computed_p_min(), cost(), Deadlock, duration(), duration_mirror(), duration_wipe(), load_fixture() (+9 more)

### Community 78 - "`migration` — cost, bandwidth and the payback rule"
Cohesion: 0.12
Nodes (11): decimate_to_configured_step(), Any, The inverse of :func:`safe_range_step_seconds`: recover a series at…, Issue one request and return the decoded ``data`` field. Typed ``Any`` rather…, ``GET /api/v1/query``. Returns the raw ``data.result`` list., ``GET /api/v1/query_range``. Returns the raw ``data.result`` list., ``GET /api/v1/label/<name>/values``. The one endpoint whose ``data`` is a bare…, ``GET /api/v1/status/buildinfo``: the running Prometheus's own version (section… (+3 more)

### Community 79 - "test_show_load_gate_reflects_real_drift_history_from_state_json"
Cohesion: 0.20
Nodes (18): StorageState, best_big_m(), build(), capacity_spread(), case_for(), moves_of(), order_moves(), per_storage() (+10 more)

### Community 80 - "_exec_group"
Cohesion: 0.14
Nodes (17): log_messages(), LogCaptureFixture, `execution.locks.on_timeout: skip` (the default): the locked head times out…, `/cluster/tasks` shape for a task still running: no endtime/status., The reported failure: an earlier move's "Erase data" (imgdel) job still holds…, Section 9.3 point 3: the very race this fix targets -- a `move_disk` task's own…, Crash recovery (section 11.2/13): a retried move is still always exactly one…, Rendered messages of the captured records carrying ``event``. (+9 more)

### Community 81 - "`prometheus` — the metrics source"
Cohesion: 0.13
Nodes (15): datetime, os, Storage DRS for Proxmox VE 9.2. Balances disk I/O load across configurable…, _one_line(), Collapse any run of whitespace, newlines included, to one space: a newline…, The file's exact text: level, summary ``| perfdata``, details, and a trailing…, The monitoring status file: one ``apply`` run's outcome, in the format the…, What one ``apply`` run did, as the level policy needs it. ``errors`` are… (+7 more)

### Community 82 - "filter_vm_config_fields"
Cohesion: 0.12
Nodes (17): `execution.abort_on_failure`, `execution` — how (and whether) moves actually happen, `execution.locks.on_timeout`, `execution.locks.poll_interval`, `execution.locks.task_retry_backoff`, `execution.locks.task_retry_limit`, `execution.locks.wait_timeout`, `execution.max_concurrent_migrations` (+9 more)

### Community 83 - "capture_bundle"
Cohesion: 0.17
Nodes (16): _aggregate_storages(), apply_forecast(), DiskLoad, GroupLoad, Convenience for callers (``show-load``) keying off `Disk.key`., Each storage's ``L_s``/``u_s`` from its disks' ``l_d``, and the group's ``u*``…, Section 12.1 point 2: scale each disk's ``l_d`` by its forecast factor ``f_d /…, One disk's `ℓ_d`. Section 4. (+8 more)

### Community 84 - "ReplayPveClient"
Cohesion: 0.19
Nodes (17): LockInfo, _parse_state_text(), Any, Raises on any shape this module does not recognize -- the caller…, The tolerant-parse half of :func:`load_state`, factored out so…, Temp file in the same directory, ``fsync``, then ``os.replace`` -- a reader…, Re-reads whatever is currently written through an already-open,…, Descriptive only -- see the module docstring's "Locking" section for why the… (+9 more)

### Community 85 - "json_safe"
Cohesion: 0.18
Nodes (17): FakePrometheusSession, A ``metrics._SessionLike`` double capable of answering *many* distinct queries…, _instant_answer(), _range_answer(), A live capture against the dev cluster found this one directly (section 16.3's…, A live capture against the dev cluster found this directly:…, A live capture found this the hard way: ``_check_sample_series()``'s "info"…, Z-02: `_check_coverage()`'s per-disk warning embeds a real vmid taken straight… (+9 more)

### Community 86 - "_FakeClient"
Cohesion: 0.13
Nodes (13): Config knob entry: type, default, unit, extremes, interactions, Tests keeping docs honest (help covers options, manual covers config), --help generated from argparse definitions, no hardcoded defaults, Internals pages: question first, name modules, explain why, ASCII diagrams, Manpage skeleton with complete OPTIONS, config/drs.example.yaml as documentation that parses, Change behaviour and documentation in the same commit, PDF is a build product; fix text not LaTeX (+5 more)

### Community 87 - "PrometheusClient"
Cohesion: 0.21
Nodes (15): CompletedProcess, needs_plugin, Write ``status`` to ``path`` atomically, mode 0644, creating the parent…, The status file could not be written., StatusFileError, write_status_file(), MonkeyPatch, Path (+7 more)

### Community 88 - "Internals: CLI dispatch and logging"
Cohesion: 0.18
Nodes (16): WindowConfig, _check_coverage(), compute_disk_coverage(), Run every section 3.3 check and assemble the report. Must be run before relying…, Section 3.3 step 5 / section 3.4's ``min_coverage`` rule: per-disk sample…, Section 3.3 step 5: report which disks fall below ``window.min_coverage``., verify_metrics(), _all_metric_names() (+8 more)

### Community 89 - "config.py"
Cohesion: 0.17
Nodes (16): _blend_loads(), compute_disk_load_series(), TimeSeries, Section 4's normalize-then-weight-then-rescale blend, given every key's own…, Section 4's `ℓ_d` blend, as a time series per disk over ``[now - range_seconds,…, range_series(), A `query_range`-shaped series with an explicit `[[ts, value], ...]` matrix,…, Build a `PrometheusClient` over a `FakeSession` answering… (+8 more)

### Community 90 - "_ResponseLike"
Cohesion: 0.13
Nodes (16): build_quantile_over_time_promql(), build_rate_promql(), _format_promql_duration(), The section 3.4 per-metric rate expression. ``sum by (vmid, device)…, Wrap a rate expression in the section 3.4 quantile-over-time reduction.…, Render a duration as a PromQL range-vector selector, e.g. ``"300s"``. Always in…, _quantile_promql(), The exact PromQL `_fetch_raw_quantity` builds for one raw field -- computed… (+8 more)

### Community 91 - "Python style (.agents)"
Cohesion: 0.17
Nodes (15): Drift history reaches the gates via last_balance, LastBalance, load_vector_for_group(), now_iso(), ``at`` is ``None`` before any run has ever executed a migration -- distinct…, This group's slice of ``last_balance.load_vector``, re-keyed from…, Pure: a new :class:`State` with ``group_name``'s slice of…, UTC, second precision, ``Z`` suffix -- exactly section 11.2's own example… (+7 more)

### Community 92 - "state.py"
Cohesion: 0.16
Nodes (13): cannot fully consolidate, forecast line, `measured load:`, `no moves made: ...` / `closest alternative: ...`, objective line, `pinned load ... ; best achievable spread given pins: ...`, `pinned (not movable this run):`, Reading `explain` (+5 more)

### Community 93 - "State"
Cohesion: 0.13
Nodes (15): build_node_selector(), _escape_promql_regex_literal(), Escape one literal string for safe use inside a PromQL/RE2 ``=~`` alternation.…, Section 3.4's auto-derived node-scoping filter: ``<node_label>=~"n1|n2|..."``…, The one selector every query in this module inserts, resolved once per run…, resolve_node_selector(), A node named `pve1.example.com` must match only that exact string in RE2 -- an…, `metrics.extra_selector` wins outright, even over a real node list -- the… (+7 more)

### Community 94 - "test_holt_winters_quantile_is_none_for_a_non_finite_forecast"
Cohesion: 0.13
Nodes (7): Fixture, Section 5.3 (C7): `(Sum_d z_d + Sum_s U^ext) / (Sum_s C_s)` -- the group's mean…, Section 5.4's `D^big` threshold, converted from the fixture's…, Section 5.4's mu (``objective.mu_vm_split_per_tib``), 0 when the split rule is…, ``{vmid: T_v}`` for ``V^split`` (section 5.3.3), written out independently of…, Section 5.4's `w_v = max(1, l_v / l_bar)`. `V` (the vmids this returns weights…, One group: its storages, its disks and the weights to solve it with. ``keys``…

### Community 95 - "Mapper"
Cohesion: 0.22
Nodes (13): _gate(), _no_move_schedule(), _outcome(), _patch_forecast_deps(), Any, A replayed dev-cluster bundle: capacity spread 112 %, I/O balanced, the gate…, At 2 * delta <= gamma the data-spread term cannot pay for a move of any size,…, The local cluster bundle under minmax: one disk carries 80 % of the group's… (+5 more)

### Community 96 - "disk_factors"
Cohesion: 0.22
Nodes (10): .agents/ index, If it fails, Running it, Verifying your setup, What each finding means, Safety properties, exit codes, status, Exit codes 0/1/2, Nothing deleted automatically (+2 more)

### Community 97 - "_FakeSession"
Cohesion: 0.19
Nodes (13): ast, io, JsonFormatter, Render one :class:`logging.LogRecord` as one JSON line., Section 2.3: "Every log record carries an ``event``" -- the event names are an…, Logging policy. See proxmox_storage_drs/logging_setup.py and…, Found live: section 7's payback ratio is `+inf` for any plan with no moves to…, _strict() (+5 more)

### Community 98 - "FakeProxmoxResource"
Cohesion: 0.15
Nodes (13): Collection, Backtest, forecast_group(), group_aggregate_series(), TimeSeries, One group's backtest: absolute error of each model's predicted p95 of ``[now-W,…, Sum every disk's own series into one group-aggregate series, at the union of…, Section 10.2's backtest, comparing against a baseline: fit on ``[now-2W,… (+5 more)

### Community 99 - "pytest"
Cohesion: 0.15
Nodes (14): Persistent state: state.json, flock is the lock; JSON lock field is only a label, Inflight UPIDs written and read for crash recovery, Reading degrades, writing raises, staged_disks field unimplemented, State dataclass tree mirrors section 11.2 JSON, Write UPID to disk before the crash can happen, ``"<group>:<storage>"`` (section 11.2). (+6 more)

### Community 100 - "Manual: Reading plan"
Cohesion: 0.14
Nodes (14): AUTHOR, COLLECT-TESTDATA OPTIONS, COMMANDS, CONFIGURATION, COPYRIGHT, DESCRIPTION, pve-storage-drs manpage, ENVIRONMENT (+6 more)

### Community 101 - "MoveCost"
Cohesion: 0.22
Nodes (13): math, ForecastConfig, HoltWintersConfig, Holt-Winters load forecasting. See IMPLEMENTATION_PLAN.md sections 10 and 12.1.…, The history ``forecast.model`` needs, in seconds. Called by ``config.py``'s…, required_range_seconds(), The shipped default (288 periods at a 5m step) over the two cycles the lookback…, test_holt_winters_fits_the_default_288_periods_on_two_bursty_days() (+5 more)

### Community 102 - "Manual: Configuration reference"
Cohesion: 0.18
Nodes (11): _apply_connection_pool_size(), Size the underlying ``requests`` session's connection pool to fit…, _FakeProxmoxApiWithSession, _FakeSession, Any, Confirmed live against a real multi-VM cluster: `requests`'s own default…, A small `read_workers` (or the field's own minimum) must not shrink the pool…, A plain string, an object with no ``_store``, or a session-shaped object with… (+3 more)

### Community 103 - "test_holt_winters_quantile_forecasts_ceil_window_over_step_steps"
Cohesion: 0.14
Nodes (12): _mapper(), Any, BaseException, _Raise, X-09: `manifest.json`'s `counts.dropped_records` is documented as counting…, A task's ``id`` is the vmid its UPID embeds. It used to be copied raw, leaving…, _tasks_by_kind(), test_anonymize_cluster_tasks_maps_the_task_id_with_the_upid() (+4 more)

### Community 104 - "Proxmox VE API"
Cohesion: 0.21
Nodes (13): fc-tier1 / reserve-tradeoff acceptance fixtures, AGENTS.md working agreement, AGPL-3.0-or-later licence and SPDX headers, black/flake8 E203 W503 E704 ignores, Branch-first git workflow, 85% coverage floor, Documentation pipeline (make docs / docs-check), make check (+5 more)

### Community 105 - "save_locked_state"
Cohesion: 0.18
Nodes (13): Git workflow (.agents), Branch first, decided from the task, Merge --no-ff on green make check, Release process (version, changelog, tag, graphify), Packaging, dependencies and CI (.agents), Autopkgtest as the dependency test, coinor-cbc and python3-pulp as Depends, Debian-first dependency policy (trixie) (+5 more)

### Community 106 - "_group_vmid_batches"
Cohesion: 0.15
Nodes (12): config section exclude, config section execution, config section forecast, config section groups, config section load_weights, config section metrics, config section monitoring, config section prometheus (+4 more)

### Community 107 - "test_holt_winters_quantile_is_none_on_a_convergence_warning"
Cohesion: 0.15
Nodes (13): `metrics.extra_selector`, `metrics.labels.device`, `metrics.labels.node`, `metrics.pvestatd_push_interval`, `metrics.rate_window`, `metrics.read_bytes`, `metrics.read_ops`, `metrics.read_time_ns` (+5 more)

### Community 108 - "Payback rule and acceptance test"
Cohesion: 0.18
Nodes (13): _inflight_target_volids(), _is_mirror_target(), _live_transient_check(), _LiveCheck, _move_charge_bytes(), _provisioned_used_bytes(), Any, :func:`_live_transient_check`'s result: ``refusal`` is ``None`` when the move… (+5 more)

### Community 109 - "proxmox_storage_drs"
Cohesion: 0.31
Nodes (12): disk_factors(), ``f_d / h_d`` for every disk that has one: ``f_d`` the Holt-Winters forecast…, _factor_series(), _FixedForecast, MonkeyPatch, 96 hourly samples whose last 24 are ``window_values`` (repeated)., Patches ``holt_winters_quantile`` to a constant so the ratio is exact., test_disk_factors_is_forecast_over_observed_p95() (+4 more)

### Community 110 - "Community 110"
Cohesion: 0.17
Nodes (12): gigapipe with ClickHouse (reference backend), PVE InfluxDB external metric server, instance label collision, OpenTelemetry metric server rejected, Other backends, RRD rejected as data source, Six per-disk blockstat counters, Silent counter loss from string fields in line protocol (+4 more)

### Community 111 - "_rebase_all_timestamps"
Cohesion: 0.18
Nodes (10): fixture, json, logging, pytest, ``auto`` and ``text`` -> ``"text"``; ``json`` -> ``"json"``. JSON is opt-in. It…, Logging policy. See IMPLEMENTATION_PLAN.md section 2.3. Every log record goes…, resolve_format(), Shared pytest fixtures. ``logging`` is process-global state, and… (+2 more)

### Community 112 - "Community 112"
Cohesion: 0.29
Nodes (11): _affinity_repair_group(), _loads(), _make_disk(), _make_storage(), parametrize, tests/fixtures/affinity-repair.yaml, built as real topology objects., The full pipeline -- solve, order, cost, benefit, accept -- exactly reproducing…, IMPLEMENTATION_PLAN.md section 14.7's fixture, exercised through the real… (+3 more)

### Community 113 - "check_paper_log.py"
Cohesion: 0.18
Nodes (11): Testing (.agents), Acceptance fixtures and generate_expected.py, 85 percent coverage floor, No network, no real sleep, deterministic ties in tests, Higher bar for safety-critical modules, Three floors precedence f_s*Z_s > hard_s > soft_s, Codecov configuration, CI installs toolchain from apt, never pip (+3 more)

### Community 114 - "execute.py"
Cohesion: 0.22
Nodes (10): config section gates, last_load, Three gates in order, d_s is absolute TiB, Diagnostic bundles collect-testdata and --replay (section 16), (C7) Capacity-spread linearization (absolute TiB), Capacity gate (section 6), cluster-6 production bundle (+2 more)

### Community 115 - "Community 115"
Cohesion: 0.18
Nodes (11): Configuration location, PVE credential setup, First steps after installing, Installation and requirements, Installing the package, Running the timer on exactly one host, Setting up the PVE credential, Running timer on exactly one host (+3 more)

### Community 116 - "Community 116"
Cohesion: 0.18
Nodes (11): `migration.account_saferemove_wipe`, `migration.assume_thick_provisioning`, `migration.bwlimit_bytes_per_sec`, `migration` — cost, bandwidth and the payback rule, `migration.max_single_move_duration`, `migration.payback_horizon`, `migration.payback_ratio`, `migration.source_load_weight` (+3 more)

### Community 117 - "Any"
Cohesion: 0.20
Nodes (11): Transient reserve invariant (operator explanation), Concurrent execution with strict FIFO launch, confirm prompt [y]es/[n]o/[a]ll/[q]uit, apply modes: dry-run, confirm, auto, Pre-flight live re-check before each move, auto re-plan loop, Decision trail events, --log-format text vs json (+3 more)

### Community 118 - "Logging: what lands where, and what an unattended run records"
Cohesion: 0.20
Nodes (11): ``state.path`` could not be written, or its advisory lock could not be…, StateError, _pid_alive(), Best-effort, used only to make a "still held" log message useful to an operator…, skipif, pid 1 (init) always exists but is not ours to signal as a normal user --…, test_acquire_lock_raises_state_error_on_a_permission_failure(), test_pid_alive_is_false_for_a_reaped_child() (+3 more)

### Community 119 - "split_gate_opens"
Cohesion: 0.25
Nodes (4): FakeProxmoxResource, FakeQueryResponse, Any, Matches ``metrics._ResponseLike``: ``.status_code`` and ``.json()``.

### Community 120 - "collect.py"
Cohesion: 0.22
Nodes (11): _imbalanced_group_load(), _no_reserve_violation_topology(), GroupLoad, Two storages, generously sized -- unlike `_sample_topology()`, no (C4)/(C5)…, san-a all the load, san-b none -- imbalance is 200% of `u*`, far above the…, Baseline for the next test: with no `state.json` at all, `last_load` is `None`,…, The same fixture as above, except `state.json` now records a `last_balance`…, Same drift-suppression scenario as `show-load`'s, through `plan` -- the two… (+3 more)

### Community 121 - "Community 121"
Cohesion: 0.22
Nodes (9): config section free_space, config section snapshot_reserve, enforce_format target_format, free_space soft_s/hard_s resolution, Storage name patterns expansion, Pin priority _pin_reason, reserve.py shared (C4)/(C5) evaluator, build_topology (+1 more)

### Community 122 - "AGENTS.md working agreement"
Cohesion: 0.29
Nodes (10): compute_benefit_load_seconds benefit formula, compute_move_cost cost_load_seconds, Migration cost and payback test, payback_horizon_seconds H, Affinity term kappa in benefit, REVIEW R-01 double-applied weights, Raw spread, capacity spread, affinity debt, Wipe duration uses magnitude of saferemove_throughput (+2 more)

### Community 123 - "Transient reserve invariant (operator explanation)"
Cohesion: 0.20
Nodes (10): `proxmox.auth.password`, `proxmox.auth.token_secret`, `proxmox.auth.username`, `proxmox.ca_file`, `proxmox.host`, `proxmox.port`, `proxmox.read_workers`, `proxmox` — the cluster API connection (+2 more)

### Community 124 - "Community 124"
Cohesion: 0.20
Nodes (10): _issue_chunked_range_query(), Any, ``client.range_query()``, issued in ``RANGE_QUERY_CHUNK_SECONDS``-sized sub-…, Merges several ``(start, end, result)`` ``query_range`` captures of the *same*…, stitch_range_results(), The common case: a wide range chunked by…, A repeat capture of the same query (not just adjacent chunks) can carry the…, test_stitch_range_results_dedupes_overlapping_timestamps() (+2 more)

### Community 125 - "`objective` — the solver's trade-off weights"
Cohesion: 0.28
Nodes (8): argparse, sys, check(), _logical_lines(), main(), Path, Undo the log's hard wrap at 79 columns. TeX breaks log lines mid-message, which…, Fail the paper build on LaTeX problems that silently damage the PDF. `lualatex`…

### Community 126 - "Path"
Cohesion: 0.33
Nodes (9): gates section, `gates.capacity_spread_threshold`, `gates.cooldown_per_disk`, `gates.cooldown_per_storage`, `gates` — deciding whether to act at all, `gates.drift_threshold`, `gates.imbalance_threshold`, Crash and two-instance recovery (inflight_upids) (+1 more)

### Community 127 - "Assignment"
Cohesion: 0.22
Nodes (7): LogRecord, json_safe(), One human-readable line per record: ``LEVEL: message``. Deliberately not a…, Replace every non-finite float with ``None``, recursively. Python's JSON…, TextFormatter, test_json_safe_replaces_non_finite_floats_recursively(), test_text_formatter_includes_exception_info()

### Community 128 - "Diagnostic bundles: `collect-testdata` and `--replay`"
Cohesion: 0.22
Nodes (9): DrsError, ExecutionError, Exception, Base class for every error this project raises on purpose., Neither solver backend could produce a feasible or heuristic plan. See…, No pending move in a plan is individually feasible right now. See…, A migration failed, or a precondition for executing one did not hold. See…, SchedulingDeadlock (+1 more)

### Community 129 - "filters.lua"
Cohesion: 0.25
Nodes (7): MetricsError, Prometheus could not be queried, or the response was unusable. See…, MonkeyPatch, Integration through the real caller: a field silently missing one disk the…, test_check_sample_series_reports_a_cross_metric_gap(), test_verify_metrics_query_failure_is_reported(), raise_error()

### Community 130 - "_findings_to_json"
Cohesion: 0.22
Nodes (9): _free_space_level(), _free_space_source(), Section 5.3.1: an absolute value is used as written; a percentage is…, One storage's resolved ``soft_s``/``hard_s`` and where each came from (section…, ``level`` (global / storage entry / pattern ``/re/``), plus the percent-to-…, Section 5.3.1: resolve ``soft_s``/``hard_s`` for one storage. The mandated…, _resolve_free_space(), _resolve_free_space_value() (+1 more)

### Community 131 - "Community 131"
Cohesion: 0.25
Nodes (8): A reference implementation that is well tested, Telegraf with a Prometheus remote-write output, The failure mode: a transport that cannot carry strings, The six counters, Two things deliberately not used, What catches it, What to do next, Where the numbers come from, and how a transport loses them

### Community 132 - "_join_vm_disks"
Cohesion: 0.25
Nodes (8): `exclude.disks`, `exclude.include_unused_disks`, `exclude.running_only`, `exclude.skip_vms_with_snapshots`, `exclude.storages`, `exclude.tags`, `exclude.vmids`, `exclude` — what DRS never touches

### Community 133 - "Community 133"
Cohesion: 0.29
Nodes (5): Protocol, The subset of ``requests.Response`` this module relies on., The subset of ``requests.Session`` this module relies on. A structural type…, _ResponseLike, _SessionLike

### Community 134 - "Monitoring: the status file"
Cohesion: 0.29
Nodes (8): _log_forecast(), _note_forecast(), ForecastReport, ``explain``'s one line on what the forecast did to this group's loads., Remember a group's forecast report, if it has one, for the JSON report., Section 12.1 point 6: one line per group, not one per disk. A failed backtest…, _render_forecast_line(), _render_show_load_human()

### Community 135 - "Community 135"
Cohesion: 0.25
Nodes (8): _dump_json(), Path, Recursively sort every mapping's keys -- section 16.1: "every file is...…, Write ``bundle`` as the canonical directory form (section 16.1): sorted keys,…, A deterministic ``.tar.gz`` of ``dir_path`` (section 16.1): sorted members,…, _sorted_dict(), write_bundle_dir(), write_tarball()

### Community 136 - "import-all"
Cohesion: 0.25
Nodes (8): The step to actually send Prometheus for a ``rate()``-based ``query_range``…, safe_range_step_seconds(), The common, correctly-behaving-backend case: nothing to work around., This project's own default (metrics.step == metrics.rate_window == 300s) sits…, A real observed shape (a 7-day-capture config's metrics.step: 1h against the…, test_safe_range_step_seconds_is_a_no_op_below_the_rate_window(), test_safe_range_step_seconds_shrinks_when_equal_to_the_rate_window(), test_safe_range_step_seconds_shrinks_when_step_is_far_above_the_rate_window()

### Community 137 - "draining status"
Cohesion: 0.25
Nodes (8): all_assignments(), eligible_storages(), A disk's storage under `assign` -- `assign` only ever has entries for movable…, Section 5.3 (C2): every storage whose `allowed_formats` holds this disk's own…, Every eligible placement of the movable disks -- (C2)'s per-disk domain…, Section 5.3 (C8), written out independently of the engine's…, small_disks_follow(), storage_of()

### Community 138 - "run-with-system-python.sh"
Cohesion: 0.25
Nodes (8): excess_of(), peak_footprint(), Section 5.3 (C5)/5.3.1: `R_s = max(f_s * Z_s, soft_s)`., ``max_s F_{v,s}`` -- the peak share of one VM any single storage holds., Section 5.3.3 (C9): ``O = sum_{v in V^split} o_v`` in TiB, ``o_v = max(0,…, Section 6's split gate, restated independently of ``gates.split_gate()``: some…, reserve_term(), split_gate_opens()

### Community 139 - "build_paper.sh"
Cohesion: 0.43
Nodes (7): Config path resolution order, Configuration page, ResolvedConfig, Secrets from environment, Semantic validation rules, Two-stage validation, Units parsed once

### Community 140 - "Never consider over-provisioning (provisioned size)"
Cohesion: 0.33
Nodes (7): Rename-detaches-flock bug and in-place locked write, LockHandle, Opaque -- pass to :func:`release_lock`. The open file descriptor is what…, Writes ``state`` **in place** into the already-open, already-locked ``fd`` --…, Persists ``state``'s business fields (``last_balance``, ``cooldowns``,…, save_locked_state(), _write_state_to_locked_fd()

### Community 141 - "Check 3: configured labels present"
Cohesion: 0.29
Nodes (6): Command dispatch dict, JsonFormatter, --mode escalation rule, 'no moves made' report, Monitoring status file statusfile.py, Logs go to stderr

### Community 142 - "Check 6: observed sample spacing"
Cohesion: 0.29
Nodes (7): LogCaptureFixture, The defect that prompted IMPLEMENTATION_PLAN.md section 2.3, in the operator's…, The other half: an operator who wrote `solver.backend: cbc` and is silently not…, The warning used to claim "within the time limit" for every status, including a…, test_a_missing_optional_solver_is_not_a_warning_under_auto(), test_an_explicitly_configured_solver_that_is_missing_still_warns(), test_no_feasible_solution_says_infeasible_rather_than_blaming_the_time_limit()

### Community 143 - "Lock timeout skip vs abort"
Cohesion: 0.33
Nodes (6): `groups[].name`, `groups` — storage groups, `groups[].storages[].capability_weight`, `groups[].storages[].free_space.soft` / `groups[].storages[].free_space.hard`, `groups[].storages[].id`, `groups[].storages[].reserve_factor`

### Community 144 - "Shared pandoc PDF metadata"
Cohesion: 0.33
Nodes (6): `load_weights.bytes`, `load_weights` — combining read/write and time/ops/bytes, `load_weights.iotime`, `load_weights.ops`, `load_weights.read_factor`, `load_weights.write_factor`

### Community 145 - "Plan output and explain narration"
Cohesion: 0.33
Nodes (6): verify-metrics exit status and severity levels, Failure to read ends the run with exit 1, Exit codes, Optional dependencies, Safety properties, exit codes, and what this build actually does, What is safe, unconditionally

### Community 146 - "importlib"
Cohesion: 0.33
Nodes (5): `collect-testdata`: capturing a bundle, Diagnostic bundles: `collect-testdata` and `--replay`, `--replay`: running against a bundle offline, Sending one to the project, What is in a bundle, and what is not

### Community 147 - "proxmox-storage-drs"
Cohesion: 0.33
Nodes (6): Logging: what lands where, and what an unattended run records, Text or JSON, The decision trail, Unattended runs log this without being asked, Under systemd, Verbosity

### Community 148 - "test_enforce_format.py"
Cohesion: 0.40
Nodes (5): MoveCost, Section 7.1's cost for one already-scheduled move., REVIEW.md R-05: an economic failure (benefit < ratio*cost) and a hard per-move…, test_render_plan_payback_lines_separates_economic_and_duration_failures(), make_result()

### Community 149 - "resolve_level"
Cohesion: 0.40
Nodes (6): footprint_on(), largest_on(), Section 5.3.3's ``F_{v,s}``: the sum of VM ``vmid``'s disks on ``s`` -- every…, Section 5.3 (C4) ``Z_s`` = ``max_v F_{v,s}``, the largest per-VM footprint on…, Section 8.1: the snapshot term's basis while ``key`` mirrors onto ``b``,…, transient_basis()

### Community 150 - "tests/__init__.py"
Cohesion: 0.33
Nodes (4): Network maintenance between issuing `move_disk` and its completion., test_api_outage_beyond_the_tolerance_still_raises(), test_api_outage_while_the_move_task_runs_does_not_fail_the_run(), task_status()

### Community 151 - "integration/__init__.py"
Cohesion: 0.33
Nodes (6): _coverage_promql(), _group_selector(), _rate_promql(), The one combined selector `compute_group_load()`/`compute_disk_load_series()`…, The exact PromQL `compute_disk_coverage` builds for its range query., The exact PromQL `_fetch_raw_quantity_series` builds for one raw field -- the…

### Community 152 - "unit/__init__.py"
Cohesion: 0.40
Nodes (5): `forecast.holt_winters.seasonal`, `forecast.holt_winters.seasonal_periods`, `forecast.holt_winters.trend`, forecast.model (quantile, holt_winters), `forecast` — placing disks for the load they will have

### Community 153 - "Configuration page"
Cohesion: 0.40
Nodes (5): `prometheus.bearer_token`, `prometheus` — the metrics source, `prometheus.timeout_seconds`, `prometheus.url`, `prometheus.username` / `prometheus.password`

### Community 154 - "Community 154"
Cohesion: 0.40
Nodes (5): solver.backend (auto, cbc, heuristic), `solver.heuristic_iterations`, `solver.mip_gap`, `solver.time_limit_seconds`, `solver` — which backend plans

### Community 155 - "test_unfixable_shortfall_is_proven_only_for_an_optimal_cbc_solve"
Cohesion: 0.40
Nodes (5): `support.bundle_dir`, `support.capture_range`, `support` — diagnostic bundles, `support.max_series_points`, `support.salt_path`

### Community 156 - "test_logging_setup.py"
Cohesion: 0.40
Nodes (4): `--json`, Whether this group's execution failed in a way that must end the whole run…, delayed_status(), status()

### Community 157 - "Community 157"
Cohesion: 0.40
Nodes (5): Freshness: why every run rewrites the file, Monitoring: the status file, What is in the file, What makes a run `OK`, `WARNING` or `CRITICAL`, Wiring it into Nagios/NRPE

### Community 159 - "FakeClock"
Cohesion: 0.40
Nodes (4): Getting the tool, proxmox-storage-drs, The documents, The safety properties to rely on

### Community 160 - "Community 160"
Cohesion: 0.40
Nodes (4): One large VM's (``V^split``, section 5.3.3) before/after numbers for the report., Section 9.5's ``split:`` lines. A result still above its cap says the solver…, _render_split_lines(), _VmSplit

### Community 161 - "Community 161"
Cohesion: 0.40
Nodes (5): _quantile(), Linear-interpolation quantile, matching ``numpy.percentile``'s default.…, test_holt_winters_quantile_follows_a_rising_trend_above_the_observed_p95(), test_quantile_matches_numpy_percentile_convention(), test_quantile_of_empty_sequence_raises()

### Community 162 - "Community 162"
Cohesion: 0.50
Nodes (5): Section 2.3's ladder: ``--quiet`` < default < ``-v`` < ``-vv``. ``--log-level``…, resolve_level(), parametrize, test_log_level_wins_over_both_verbose_and_quiet(), test_resolve_level_ladder()

### Community 163 - "Community 163"
Cohesion: 0.40
Nodes (5): disk_state_key(), ``"<group>:<vmid>:<device>"`` (section 11.2) -- the group prefix is what keeps…, test_disk_state_key_matches_section_11_2_shape(), test_build_topology_ignores_another_groups_cooldown_entry(), test_build_topology_pins_a_disk_within_its_cooldown()

### Community 164 - "Community 164"
Cohesion: 0.40
Nodes (3): str, _FakeClient, The ``"fake-client"`` sentinel every ``build_pve_client`` mock in this file…

### Community 165 - "Community 165"
Cohesion: 0.40
Nodes (3): _FakeHttpsBackend, _FakeProxmoxApiWithBackend, _FakeTicketAuth

### Community 166 - "build_node_selector"
Cohesion: 0.50
Nodes (4): Python style (.agents), black vs flake8 disagreements (E203, W503, E704), One implementation of every rule (MILP and heuristic share), Units in names

### Community 167 - "build_site.sh"
Cohesion: 0.50
Nodes (3): config.py depends on forecast.py, Module layout, Pipeline as specified and as built

### Community 168 - "Community 168"
Cohesion: 0.50
Nodes (3): move_disk bytes to KiB/s conversion, Why proxmoxer, PveClient

### Community 169 - "Community 169"
Cohesion: 0.50
Nodes (4): free_space.soft / free_space.hard, `snapshot_reserve.count_foreign_volumes`, snapshot_reserve.factor, `snapshot_reserve` — the free-space floor

### Community 170 - "Community 170"
Cohesion: 0.50
Nodes (4): `window.lookback`, `window.min_coverage`, `window.quantile`, `window` — the decision window

### Community 171 - "Community 171"
Cohesion: 0.67
Nodes (3): test_unfixable_shortfall_is_proven_only_for_an_optimal_cbc_solve(), outcome(), proven()

### Community 173 - "Community 173"
Cohesion: 0.67
Nodes (3): free_space section, free-space-repair fixture (plan 14.8), free_space.soft repair exemption

### Community 174 - "Community 174"
Cohesion: 0.67
Nodes (3): `free_space.hard`, `free_space` — keep N bytes (or N%) free on top of the snapshot reserve, `free_space.soft`

### Community 176 - "Community 176"
Cohesion: 0.67
Nodes (3): _is_metrics_expected_absent(), parametrize, test_is_metrics_expected_absent()

### Community 177 - "Community 177"
Cohesion: 0.67
Nodes (3): fc-tier1 fixture (plan 14 worked example), generate_expected.py exhaustive enumeration, beta x delta sweep contract

## Knowledge Gaps
- **314 isolated node(s):** `solver.backend (auto, cbc, heuristic)`, `solver: line (backend actually used)`, `execution.mode (dry-run default)`, `free_space.soft / free_space.hard`, `migration payback settings (payback_horizon, payback_ratio, max_single_move_duration)` (+309 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1581 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **61 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Configuration reference` connect `_state_from_dict` to `test_small_disks.py`, `_join_vm_disks`, `Community 169`, `Community 170`, `test_holt_winters_quantile_is_none_on_a_convergence_warning`, `test_unfixable_shortfall_is_proven_only_for_an_optimal_cbc_solve`, `Community 173`, `Community 174`, `Lock timeout skip vs abort`, `Shared pandoc PDF metadata`, `filter_vm_config_fields`, `Community 116`, `unit/__init__.py`, `Configuration page`, `Community 154`, `Transient reserve invariant (operator explanation)`, `Path`?**
  _High betweenness centrality (0.090) - this node is a cross-community bridge._
- **Why does `Group` connect `pve.py` to `MonkeyPatch`, `build_topology`, `Config`, `test_config.py`, `Topology`, `Monitoring: the status file`, `test_cli.py`, `test_loadmodel.py`, `test_metrics.py`, `case_for`, `test_execute.py`, `Group`, `Configuration reference`, `Check 6: observed sample spacing`, `optimize.py`, `test_payback.py`, `test_replay.py`, `integration/__init__.py`, `.agents/documentation.md`, `PveClient`, ``execution` — how (and whether) moves actually happen`, `test_free_space_repair_fixture.py`, `Monitoring status file`, `C5 Capacity, snapshot reserve and free space`, `configure_logging`, `Transient invariant`, `test_forecast.py`, `_patch_forecast_deps`, `test_state.py`, `Packaging, dependencies and CI (.agents)`, `test_large_vm_split_fixture.py`, `Proxmox Storage DRS Implementation Plan`, `test_affinity_repair_fixture.py`, `capture_bundle`, `config.py`, `_ResponseLike`, `Community 112`, `collect.py`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Why does `report()` connect `pve-storage-drs.1.md` to ``prometheus` — the metrics source`, `_state_from_dict`, `PrometheusClient`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Are the 214 inferred relationships involving `Group` (e.g. with `_accumulate_move_stats()` and `_apply_payback_gate()`) actually correct?**
  _`Group` has 214 INFERRED edges - model-reasoned connections that need verification._
- **Are the 93 inferred relationships involving `PveClient` (e.g. with `_apply_payback_gate()` and `_pve_client_for()`) actually correct?**
  _`PveClient` has 93 INFERRED edges - model-reasoned connections that need verification._
- **Are the 87 inferred relationships involving `Disk` (e.g. with `_footprint_text()` and `_fragmented_vms()`) actually correct?**
  _`Disk` has 87 INFERRED edges - model-reasoned connections that need verification._
- **What connects `solver.backend (auto, cbc, heuristic)`, `solver: line (backend actually used)`, `execution.mode (dry-run default)` to the rest of the system?**
  _314 weakly-connected nodes found - possible documentation gaps or missing edges._