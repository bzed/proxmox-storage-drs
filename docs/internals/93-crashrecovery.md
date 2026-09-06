# Crash and two-instance recovery: `crashrecovery.py`

**What does this page answer?** How does an `apply` run notice a `move_disk`
left running by a crashed previous run, or by a second instance running
concurrently; how does `state.json`'s `inflight_upids` actually reach disk
*before* the move it names can crash the engine; and what does a discovered
vmid do to the rest of the run? Describes
`proxmox_storage_drs/crashrecovery.py`, `state.py`'s `with_inflight_upid()`/
`without_inflight_upid()`, and the `execute.py`/`cli.py` wiring around them.

## The two failure modes section 13 names, one mechanism

"Engine crashes mid-move" and "Two DRS instances running" are different
causes with the same shape: a `move_disk` task keeps running against a VM
this run does not know about. `state.json`'s `inflight_upids` field exists
so a run notices either case *before planning anything* (section 13's own
words) rather than proposing a second, conflicting move against the same
disk:

1. **A local trace.** `execute.py` writes a UPID into `inflight_upids`
   immediately after `move_disk()` returns for it, and clears it once that
   task itself has finished — see "Writing before the crash" below. A
   process that dies mid-move (killed, OOM, host reboot) leaves that UPID
   behind; the *next* run's startup scan finds it.
2. **A cluster-wide scan.** `state.json`'s own `fcntl.flock()`
   (`docs/internals/15-state.md`) is real, kernel-enforced mutual exclusion
   for two instances on the *same host*, but cannot see another node at
   all. `PveClient.cluster_tasks()` (`GET /cluster/tasks`) is the one read
   that actually crosses the cluster — `crashrecovery.py` scans it for a
   still-running `qmmove` task from this tool's own configured user that
   the local trace does not already know about. `IMPLEMENTATION_PLAN.md` is
   explicit that this is what degrades "two instances running" from
   "conflicting" to merely "slow and redundant" — the correct fix is still
   "run the timer on exactly one host" (`cron`/`systemd` configuration, not
   this code); this is the safety net for when that is not honoured.

Either way, `reconcile_inflight()` reports the affected vmid for
`cli.py` to exclude from this run's planning — **never** force-cancelled,
never assumed safe to ignore.

## `parse_upid()`: PVE's UPID grammar, confirmed live

A UPID is `UPID:{node}:{pid}:{pstart}:{starttime}:{type}:{id}:{user}:`.
`id` is the vmid, as a string, for a VM-scoped task type (`qmmove` among
them); it is empty for a cluster-scoped one (`vzdump`, say). This shape is
not general PVE-API knowledge taken on faith — `.agents/domain-invariants.md`
rule 10 forbids stating unverified PVE behaviour — it was confirmed live
against the real dev cluster (`[[dev-cluster-access]]`) by reading an actual
`qmconfig` task's own UPID before `parse_upid()` was written to depend on
it. `parse_upid()` returns `None` for anything that does not parse as a
UPID at all (a foreign or malformed string), never raises — a scan finding
one unparseable entry must degrade to "cannot use this one," not abort.

## `/cluster/tasks`' own convention

`PveClient.cluster_tasks()` (`GET /cluster/tasks`) returns every node's
recent/active tasks as `{node, type, id, upid, user, starttime, saved}`,
plus `endtime`/`status` — **both present once the task has finished, both
absent while it is still running**. This is a different convention from the
per-task `PveClient.task_status()` endpoint (`GET
/nodes/{node}/tasks/{upid}/status`), whose own `status` field is the string
`"running"` or `"stopped"` — confirmed live against the same cluster
alongside the UPID grammar above, and the reason
`_scan_cluster_for_foreign_inflight()` uses `"endtime" in task or "status"
in task` to filter obviously-finished candidates cheaply, then
`_task_is_running()` (below, wrapping `task_status()`) to actually confirm
one that looks live — never the reverse, and never treating
`/cluster/tasks`' own `status` string as if it used `task_status()`'s
`"running"`/`"stopped"` vocabulary.

## `reconcile_inflight()`: both halves

```python
def reconcile_inflight(
    client: PveClient, state: State, auth: AuthConfig
) -> tuple[frozenset[int], State]:
```

Split into two helpers purely to stay within this project's flake8
complexity limit:

- **`_reconcile_recorded_upids()`** re-checks every UPID `state.json`
  already remembers via `_task_is_running()` (which wraps
  `task_status()`, not `/cluster/tasks`' own convention — see above). One
  whose task has since finished is dropped from the returned
  `inflight_upids` (an ordinary reconciliation of a move the engine never
  got to clear itself, logged at `INFO`); one still running is kept and its
  vmid excluded. A malformed or vmid-less recorded entry is dropped
  outright — there is no future run in which it could ever resolve either.
- **`_scan_cluster_for_foreign_inflight()`** is the cluster-wide half
  described above, skipped entirely (`frozenset()`, no API call at all)
  when `expected_task_user()` cannot determine this tool's own configured
  user (neither `token_id` nor `username` set — config validation makes
  this unreachable in practice, but the function degrades safely rather
  than guessing). `already_known` (the still-inflight subset of
  `state.json`'s own recorded UPIDs) is subtracted first, so a run's own
  in-flight move never logs a spurious "found a foreign task" warning about
  itself.

`_task_is_running()` returns `None`, not an exception, when the check
itself fails (the node is unreachable, say) — logged at `WARNING` and
treated by both callers as "assume still running." That is the safe
direction to guess wrong in: excluding a VM that turned out to be free
costs one skipped move on this run; assuming free a VM that was not risks
a second `move_disk` racing the first.

## Writing before the crash: `execute.py`'s callbacks

Persisting `inflight_upids` only at the *end* of a whole `apply` run — the
way `last_balance`/`cooldowns` are persisted — would never survive the
exact crash this mechanism exists to recover from: if the engine is killed
mid-move, nothing after that point ever runs. `execute_plan()` therefore
accepts two optional callbacks, `execute.InflightCallback = Callable[[str],
None]`:

- **`on_inflight_started`** fires in `_execute_one_move()` immediately
  after `move_disk()` returns a UPID — before anything else happens with
  it, including the (potentially very long) wait for it to finish.
- **`on_inflight_finished`** fires immediately after
  `_wait_for_move_completion()` returns, for *any* outcome including
  `"failed"` and `"draining"`. A `"draining"` source is no longer tracked by
  this UPID at all once its task itself has finished — only by its own
  content-listing poll (`state.without_inflight_upid()`'s own docstring) —
  so it is cleared here exactly as promptly as a `"moved"` outcome, not
  left recorded until the source actually releases.

Neither call is wrapped in `try`/`finally`: if something inside the wait
itself raises (a network failure mid-poll), `on_inflight_finished` simply
never fires and the UPID stays recorded — which is correct, since the move
might still be running and the next startup's scan must still find it.

`cli.py`'s `_make_inflight_callbacks()` is what the two callbacks actually
do: write straight to disk via `state.with_inflight_upid()`/
`without_inflight_upid()` followed by `state.save_locked_state()`, through
the same `LockHandle` `_handle_apply()` itself holds for the whole run. This
is the one deliberate, narrow exception to this codebase's otherwise-pure
functional state-threading style (`_handle_apply()`'s `state` variable is
reassigned throughout, never mutated) — `_InflightStateBox` is a mutable
box purely so a closure passed several call-frames deep into
`execute_plan()` can still reach it. `_handle_apply()`'s own `finally`
block saves `state_box.value`, never the plain `state` variable, for
exactly this reason: if an exception propagates out of a group's execution,
a callback earlier in that same group can already have written a newer
`inflight_upids` straight to disk than whatever `state` was last assigned
in the surrounding loop, and saving the stale local variable would silently
clobber that write.

## `cli.py`: the startup scan, before planning anything

`_handle_apply()` calls `_reconcile_inflight_and_fold_exclusions()`
immediately after building the PVE client, before `build_topology()` for
planning — section 13's own "before planning anything." A non-empty result
is folded into `exclude.vmids` on the `ResolvedConfig` used for the rest of
this run, reusing `topology.py`'s existing (C2) vmid/tag pin rather than a
second exclusion mechanism (AGENTS.md section 5: one implementation); the
report shows such a vmid pinned with the generic "excluded by config
(exclude.vmids)" reason, and `crashrecovery.py`'s own `logger.warning()`
calls are what tell the operator *why* it is there. This runs for every
mode, including `dry-run` — an accurate dry-run report should already
reflect a vmid a real `apply` run would also have excluded, and reconciling
a since-finished recorded UPID away is harmless (and useful) even when
nothing gets executed this run.
