# Crash and two-instance recovery: `crashrecovery.py`

**What does this page answer?** How does an `apply` run notice a `move_disk`
left running by a crashed previous run, or by a second instance running
concurrently? How does `state.json`'s `inflight_upids` actually reach disk
*before* the move it names can crash the engine? What does a discovered vmid
do to the rest of the run?

This page describes `proxmox_storage_drs/crashrecovery.py`, `state.py`'s
`with_inflight_upid()`/`without_inflight_upid()`, and the `execute.py`/`cli.py`
wiring around them.

## The two failure modes section 13 names, one mechanism

"Engine crashes mid-move" and "Two DRS instances running" have different
causes. They share one shape: a `move_disk` task keeps running against a VM
this run does not know about.

`state.json`'s `inflight_upids` field exists so a run notices either case
*before planning anything* (section 13's own words), not after it proposes a
second, conflicting move against the same disk:

1. **A local trace.** `execute.py` writes a UPID into `inflight_upids`
   immediately after `move_disk()` returns for it. It clears the UPID once
   that task itself has finished. See "Writing before the crash" below. A
   process that dies mid-move (killed, OOM, host reboot) leaves that UPID
   behind. The *next* run's startup scan finds it.
2. **A cluster-wide scan.** `state.json`'s own `fcntl.flock()`
   (`docs/internals/15-state.md`) is real, kernel-enforced mutual exclusion
   for two instances on the *same host*. It cannot see another node at all.
   `PveClient.cluster_tasks()` (`GET /cluster/tasks`) is the one read that
   actually crosses the cluster. `crashrecovery.py` scans it for a
   still-running `qmmove` task from this tool's own configured user that the
   local trace does not already know about. `IMPLEMENTATION_PLAN.md` is
   explicit that this degrades "two instances running" from "conflicting" to
   merely "slow and redundant". The correct fix is still "run the timer on
   exactly one host". That is `cron`/`systemd` configuration, not this code.
   This code is the fallback for when that is not honoured.

Either way, `reconcile_inflight()` reports the affected vmid to `cli.py`.
`cli.py` excludes the vmid from this run's planning. The tool **never**
force-cancels the running task. The tool never assumes the task is safe to
ignore.

## `parse_upid()`: PVE's UPID grammar, confirmed live

A UPID has the shape `UPID:{node}:{pid}:{pstart}:{starttime}:{type}:{id}:{user}:`.
`id` is the vmid, as a string, for a VM-scoped task type such as `qmmove`.
`id` is empty for a cluster-scoped type such as `vzdump`.

This shape is not general PVE-API knowledge taken on faith.
`.agents/domain-invariants.md` rule 10 forbids stating unverified PVE
behaviour. This project confirmed the shape live against the real dev
cluster. It read an actual `qmconfig` task's own
UPID before `parse_upid()` was written to depend on it.

`parse_upid()` returns `None` for anything that does not parse as a UPID at
all, such as a foreign or malformed string. The function never raises. A scan
that finds one unparseable entry must degrade to "cannot use this one," not
abort.

## `/cluster/tasks`' own convention

`PveClient.cluster_tasks()` (`GET /cluster/tasks`) returns every node's
recent/active tasks as `{node, type, id, upid, user, starttime, saved}`. It
also returns `endtime` and `status`, **both present once the task has
finished, both absent while it is still running**.

This is a different convention from the per-task `PveClient.task_status()`
endpoint (`GET /nodes/{node}/tasks/{upid}/status`). That endpoint's own
`status` field is the string `"running"` or `"stopped"`. This project
confirmed both conventions live against the same cluster, alongside the UPID
grammar above.

`_scan_cluster_for_foreign_inflight()` uses `"endtime" in task or "status" in
task` to filter obviously-finished candidates cheaply. It then calls
`_task_is_running()` (below, wrapping `task_status()`) to confirm a candidate
that looks live. It never does the reverse. It never treats `/cluster/tasks`'
own `status` string as if it used `task_status()`'s `"running"`/`"stopped"`
vocabulary.

## `reconcile_inflight()`: both halves

```python
def reconcile_inflight(
    client: PveClient, state: State, auth: AuthConfig
) -> tuple[frozenset[int], State]:
```

The function splits into two helpers purely to stay within this project's
flake8 complexity limit:

- **`_reconcile_recorded_upids()`** re-checks every UPID `state.json`
  already remembers, via `_task_is_running()`. That helper wraps
  `task_status()`, not `/cluster/tasks`' own convention (see above). A UPID
  whose task has since finished is dropped from the returned
  `inflight_upids`. That is an ordinary reconciliation of a move the engine
  could not clear itself. The drop is logged at `INFO`. The helper keeps a
  still-running UPID and excludes its vmid. A malformed or vmid-less recorded
  entry is dropped outright. No future run could ever resolve it either.
- **`_scan_cluster_for_foreign_inflight()`** is the cluster-wide half
  described above. The function is skipped entirely (`frozenset()`, no API
  call at all) when `expected_task_user()` cannot determine this tool's own
  configured user. That is the case when neither `token_id` nor `username` is
  set. Config validation makes this unreachable in practice. The function
  degrades safely rather than guessing. `already_known` (the still-inflight
  subset of `state.json`'s own recorded UPIDs) is subtracted first. A run's
  own in-flight move then never logs a spurious "found a foreign task"
  warning about itself.

`_task_is_running()` returns `None`, not an exception, when the check itself
fails, say when the node is unreachable. The failure is logged at `WARNING`.
Both callers treat the `None` as "assume still running." That is the safe
direction to guess wrong in. Excluding a VM that turned out to be free costs
one skipped move on this run. Assuming free a VM that was not risks a second
`move_disk` racing the first.

## Writing before the crash: `execute.py`'s callbacks

The tool persists `last_balance` and `cooldowns` only at the *end* of a run.
Persisting `inflight_upids` that way would never survive the exact crash this
mechanism exists to recover from: if the engine is killed mid-move, nothing
after that point ever runs. `execute_plan()` therefore accepts two optional
callbacks, `execute.InflightCallback = Callable[[str], None]`:

- **`on_inflight_started`** fires in `_execute_one_move()` immediately after
  `move_disk()` returns a UPID. It fires before anything else happens with
  the UPID. That includes the wait for the task to finish, which can be very
  long.
- **`on_inflight_finished`** fires immediately after
  `_wait_for_move_completion()` returns. It fires for *any* outcome,
  including `"failed"` and `"draining"`. A `"draining"` source is no longer
  tracked by this UPID at all once its task itself has finished. The source
  is then tracked only by its own content-listing poll (see
  `state.without_inflight_upid()`'s own docstring). The callback clears the
  UPID here exactly as promptly as a `"moved"` outcome. It does not leave the
  UPID recorded until the source actually releases.

The text above describes the sequential executor. The concurrent executor fires
the same pair: from `_advance_pending()` at the launch, and from
`_poll_inflight_once()` at each retry and at completion.

Neither call is wrapped in `try`/`finally`. If something inside the wait
itself raises, say a network failure mid-poll, `on_inflight_finished` simply
never fires and the UPID stays recorded. That is correct. The move might
still be running. The next startup's scan must still find it.

`cli.py`'s `_make_inflight_callbacks()` is what the two callbacks actually
do. They write straight to disk via `state.with_inflight_upid()`/
`without_inflight_upid()`. They then call `state.save_locked_state()`. The
write goes through the same `LockHandle` that `_handle_apply()` itself holds
for the whole run.

This is the one deliberate, narrow exception to this codebase's
otherwise-pure functional state-threading style. `_handle_apply()`'s `state`
variable is reassigned throughout and never mutated. `_InflightStateBox` is a
mutable box. The box exists purely so a closure passed several call-frames
deep into `execute_plan()` can still reach it.

`_handle_apply()`'s own `finally` block saves `state_box.value`, never the
plain `state` variable. The reason is this: if an exception propagates out of
a group's execution, a callback earlier in that same group can already have
written a newer `inflight_upids` straight to disk. That write is newer than
whatever `state` was last assigned in the surrounding loop. Saving the stale
local variable would erase the newer write.

## `cli.py`: the startup scan, before planning anything

`_handle_apply()` calls `_reconcile_inflight_and_fold_exclusions()`
immediately after building the PVE client. It calls the function before
`build_topology()`, for planning. That is section 13's own "before planning
anything."

A non-empty result is folded into `exclude.vmids` on the `ResolvedConfig`
used for the rest of this run. The fold reuses `topology.py`'s existing (C2)
vmid/tag pin. It does not add a second exclusion mechanism (AGENTS.md
section 5: one implementation).

The report shows such a vmid pinned with the generic "excluded by config
(exclude.vmids)" reason. `crashrecovery.py`'s own `logger.warning()` calls
tell the operator *why* the vmid is there.

This runs for every mode, including `dry-run`. An accurate dry-run report
should already reflect a vmid a real `apply` run would also have excluded.
Reconciling a since-finished recorded UPID away is harmless and useful, even
when nothing gets executed this run.
