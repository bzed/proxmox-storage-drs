# Reading `apply`

`apply` runs the identical per-group pipeline that `plan` prints. It uses the same
gate, solver, scheduler and payback test. The manual
page of `plan`, `docs/manual/27-plan.md`, describes all four in detail. Then,
unless the mode is `dry-run`, `apply` issues the moves. `execution.mode` (or
`--mode`) selects what happens next:

| Mode | What `apply` does |
|---|---|
| `dry-run` *(default)* | Prints the same report as `plan`, plus a `would_move` outcome per move. Reads the cluster and Prometheus as `plan` does, and sends no write call. |
| `confirm` | Runs one move at a time and asks before each move: `[y]es`/`[n]o skip`/`[a]ll remaining`/`[q]uit`. |
| `auto` | Runs unattended. `execution.time_windows`, `max_migrations_per_run` and a bounded automatic re-plan loop limit the run (see "Reading `auto` mode" below). Only this mode honours `execution.max_concurrent_migrations`/`max_concurrent_per_storage` above their default of `1` and runs several moves at once (see "Concurrent execution" below). |

The following is a `confirm` run with the section 14 fixture that the manual page
of `plan` uses. The operator declines the first move and accepts the rest:

```
$ pve-storage-drs -c /etc/pve/drs.yaml --mode confirm apply
Group fc-tier1 → ACT: reserve violated on san-a; acting now regardless of the normal drift/imbalance thresholds -- a capacity shortfall is never delayed by them
  solver: heuristic
  db01(102):scsi0  san-a → san-c  1.50 TiB  [y]es/[n]o skip/[a]ll remaining/[q]uit? n
  1. db01(102):scsi0            san-a → san-c     1.50 TiB   ~2.2h   Δimbalance -4.53   ℓ/z 1.67  → skipped: operator declined
  web01(101):scsi1  san-a → san-b  1.00 TiB  [y]es/[n]o skip/[a]ll remaining/[q]uit? a
  2. web01(101):scsi1           san-a → san-b     1.00 TiB   ~1.5h   Δimbalance -2.00   ℓ/z 1.00  → moved: task UPID:... completed OK, source released
  after: san-a=5.50  san-b=1.70  san-c=0.20
  spread: 255.4% → 214.9%
  payback: benefit 3.02e+07 load·s vs cost 1.05e+04 load·s → ratio 2.88e+03 (need 10) ✓
```

Each move line is identical to the output of `plan`, up to the `→ status:
detail` suffix. The "after", "spread" and "payback" lines still describe the
plan as scheduled. The tool does not adjust them for what a declined move would
change. As with a partial deadlock (see the manual page of `plan`), a report of
what you asked for is more honest than a recomputed hypothetical.

## The `[y]es/[n]o skip/[a]ll remaining/[q]uit` prompt

The prompt appears only in `confirm` mode, once per move, before the tool issues
the move. It never appears for a move that `dry-run` would only report. `[a]ll
remaining` stops the prompt for the rest of *this run*: every group, not just the
current one. `[q]uit` stops the whole run at once, including any group that the
tool has not yet planned. The tool rejects any other answer right there ("please
answer y, n, a or q") and asks again. Such an answer never reaches `execute.py`,
so a typo can never count as one of the four real decisions.

## Reading `auto` mode

`auto` behaves like `[a]ll remaining` chosen in advance, without a prompt. It
also does three things that `dry-run`/`confirm` do not do at all
(`IMPLEMENTATION_PLAN.md` section 9.1/9.2):

- **`execution.time_windows`.** If you configure any window, the current moment
  must fall inside one of them. The tool uses the **local time of the host that
  runs `pve-storage-drs`**, not UTC. Otherwise the tool refuses the move and
  reports it as `skipped`, "outside execution.time_windows". Before it starts a
  move, `auto` also refuses a move whose estimated duration (mirror plus any
  `saferemove` wipe) would not end before the window closes. With no windows
  configured, no restriction applies. In both cases, the tool never aborts a move
  in progress when a window closes. The check only runs *before* the next move.
- **`execution.max_migrations_per_run`.** This is a ceiling on the number of
  moves that one call runs. All groups that the call visits share it. The tool
  does not reset it for each group. The remaining moves wait for the next
  scheduled run.
- **The re-plan loop.** A `replan_needed` mismatch does not end an `auto` run
  as it ends a `dry-run`/`confirm` run. `apply` runs the whole pipeline again
  (gates, load model, solver, payback, ordering) from freshly observed cluster
  state and tries again, up to `execution.max_replans_per_run` times. On a
  re-plan, the gate may well decide that no further action is needed. That is a
  normal, quiet outcome, not a failure. Above the cap, the run ends with a message
  that names the setting, and the run still exits `0`. Outside changes can be too many: VMs moved, disks created, another tool filled a
  target. That is a reason to try again later, not a failure of the tool. The next run starts from freshly
  observed state. A re-plan that cannot be computed because Prometheus cannot be
  read is different (see "When something cannot be read" below). The `outcomes[]` entries of the report show the whole story of a re-planned group.
  They show the mismatch that caused each re-plan, and what the next attempt did.

## Concurrent execution

If you set `execution.max_concurrent_migrations`/`max_concurrent_per_storage`
above their default of `1`, `auto` runs several moves at once. `dry-run` and
`confirm` always run strictly one move after another, whatever these settings say.
Concurrency only makes sense for unattended operation.

The **transient reserve invariant** (`docs/manual/27-plan.md`) is a rule about the
snapshot reserve of a storage. The reserve must hold while a disk that moves onto
the storage exists on both source and target. It is not enough that the reserve
holds after the move ends. The
rule extends to a whole set of moves in flight onto the same storage at the same
time (`IMPLEMENTATION_PLAN.md` section 8.1 gives its formula). The tool checks it
live before every launch, exactly like the pre-flight re-check of the sequential
executor. `max_concurrent_per_storage` counts a storage as occupied when a move
uses it as source *or* as target.

**Launch order stays strictly FIFO.** The tool never reorders the scheduler's own
queue (the queue that a sequential run follows, one move at a time) to keep every
concurrency slot busy. The next queued move may be unable to launch yet, because
its VM is locked or a per-storage cap is reached. `apply` then waits for it. It
does not skip ahead to a later move that could launch at once. Several moves
really run at once after launch: no move blocks another while it waits for its own
completion or lock. But the move that launches *next* always follows the order that
`plan` would show. This can give less throughput in a mixed queue. It never
launches a move out of the order that the payback-scored plan computed.

A failure, or a budget or deadline limit, stops the run from launching anything
more, exactly as in the sequential case. It does not abandon moves in flight.
`apply` continues to poll them to their own natural end (`moved`, `failed` or
`draining`) before it returns. No running move stays unreported.

## What "done" means for one move, and why it can take a while

A move is not finished when the `move_disk` task itself succeeds.
`IMPLEMENTATION_PLAN.md` section 9.3 requires all three of these together:

- the task reports `exitstatus: OK`;
- the source volume is gone from the content listing of the source storage;
- the config lock of the VM is clear again.

A storage with `saferemove` enabled zeroes the old volume afterwards, at
`saferemove_throughput`. The default is 10 MiB/s. A negative value in `storage.cfg`
is also a rate (see [`verify-storages`](25-show-load-and-verify-storages.md)). For a
large disk, this can run for hours after the task itself ends. During this time,
`apply` reports the move as `draining`, not `moved` and not `failed`. This is a
normal, expected state, not an error. `execution.source_release.timeout` (default
48h) bounds it.

A `draining` move still counts as "executed" for the bookkeeping in `state.json`
below: the mirror is complete, and only the cleanup of the source is still in
flight. For the *rest of this run*, the tool excludes that storage as source and
as target of any later move. The storage holds a storage-level lock as long as the
wipe runs. A later `move_disk` that uses it would queue behind a wipe that can
take days, or fail outright. The tool reports such a move plainly (`skipped`, with
the name of the draining storage) instead of running it into that lock.

Before *every* move, `apply` checks the live cluster again and does not trust the
plan. The check covers these cases:

- the VM moved to another node;
- the disk is no longer on the expected source;
- a snapshot appeared;
- someone tagged the VM for exclusion;
- the free space of the target no longer satisfies the transient invariant. The
  target must still hold every disk on it, plus the moving disk, plus the snapshot
  reserve, while both copies of the moving disk exist.

That last check reads the volume listing of the target again. It counts every
volume at its *provisioned* size, exactly as planning did. It does not use the
allocated figure of the pool. On a thin-provisioned pool, that figure is much
lower. It would let a move through onto a pool that other provisioning has filled
since planning. A mismatch (the VM moved, a snapshot appeared, the target has no
room any more) stops the run of the group with `replan_needed`. In
`dry-run`/`confirm`, that is the end of it: run `apply` again by hand when you are
ready. See "Reading `auto` mode" above for what `auto` does about it by itself.

Sometimes a check cannot be *made* at all: the PVE API fails while the tool reads
the VM or the target again, or the target lists a volume without a size. The tool
then refuses the move, and the whole run fails (see "When something cannot be
read").

A VM config lock makes `apply` wait, not fail, up to
`execution.locks.wait_timeout`. The lock can be `backup`, `snapshot`,
`migrate` or any other value. The tool never uses a whitelist of values (see
`docs/internals/92-execute.md`). A task that
still runs on the VM does the same. This is typically the "Erase data" job
(`imgdel`) of an earlier move. It can hold the lock of the config file itself, and
the move would then fail with `can't lock file ... - got timeout`. Console sessions
do not count. The tool applies the same wait, with the same timeout and the same
`on_timeout` handling. `execution.locks.on_timeout` decides what happens at the
timeout. `skip` (the default) reports the move as `skipped` and continues with the
rest of the plan. `abort` reports it as `failed` and stops the *whole run*
unconditionally. This one case ignores `execution.abort_on_failure` entirely. The
words of the manual for `on_timeout: abort` are "abort the run". That is a
distinct, stronger promise than the general policy "stop after any failed move",
which still applies to an ordinary task failure.

## Failure and `abort_on_failure`

`apply` reports a failed `move_disk` task as `failed`, with its detail. It then
lists any volume that remains on the target and that the config of the VM does not
reference (`IMPLEMENTATION_PLAN.md` section 9.4). The tool **never deletes such a
volume; it only reports it**, like every other orphan that this project shows. With
`execution.abort_on_failure: true` (the default), the whole run stops there. With
`false`, `apply` continues with the remaining moves of the plan. The lock-timeout
`abort` case above is the one exception: it always stops the run, whatever this
setting says.

## When something cannot be read

`apply` can plan around a mismatch between the plan and the cluster. It cannot plan
around a *failure to look*. The following failures end the whole run at once. The
tool then plans and runs no later group, and `apply` exits `1`:

- the PVE API fails while `apply` reads a VM or the target storage again just
  before a move (or the target lists a volume without a size);
- Prometheus cannot be read while the tool computes the load of a group, in the
  first plan or in an `auto` re-plan. (A re-plan that cannot be computed is a
  failed run, not "no further action needed".)

Moves that completed stay recorded in `state.json` and in the report. The report
says what could not be read. A plan around data that the tool could not observe
would be a worse plan, not a better one, so the tool does not try. Repair the
connection and run the command again. `plan` and `explain` change nothing. They
still report every group that they can, and they also exit `1` when the tool could
not compute the load of any group.

## `state.json`: what a real run actually changes

`apply` is the one command that takes the advisory lock of `state.json`
(`docs/internals/15-state.md`). It checks the lock first, before it touches PVE or
Prometheus. A second concurrent `apply` (any mode, including `dry-run`) thus exits
`0` at once and quietly, and does not race the first one. After the run, the tool
updates the state for every group in which at least one move ran (`moved` or
`draining`; both mean that the mirror completed):

- The tool replaces `last_balance.load_vector` with the load of that group in this
  run. This is the load that the balancer acted on, so it is forecast-scaled under
  `forecast.model: holt_winters`. The drift gate of the next run thus compares
  against a real balance instead of treating every run as the first one.
- Every moved disk gets a new `gates.cooldown_per_disk` timestamp at its **new**
  location.
- **Both** storages of the move, source and destination, get a new
  `gates.cooldown_per_storage` timestamp. Section 6 says that a storage "involved
  in a migration" accepts no new incoming moves. The sizing rule of section 9.3 for
  this cooldown protects a *source* that still drains a `saferemove` wipe. A record
  of the destination alone could never achieve that. On the next run, the cooldown only *excludes* destinations. The heuristic and MILP
  backends refuse a cooldown storage as the target of an incoming move. They never
  refuse it as a source that a disk may still leave. A record of both endpoints only increases the number of storages with
  a timestamp. It does not change what the timestamp blocks.

A group in which no move runs (the gate said `NO ACTION`, or a
`load_error`/`replan_needed` stopped it before any move ran) leaves `state.json`
unchanged for that group.

## Crash and two-instance recovery

Before it plans anything, every `apply` run (including `dry-run`) looks for a
`move_disk` that is still running. A crashed previous run, or a second instance
that runs at the same time, can leave one. It checks the `inflight_upids` of `state.json` again. It scans
the task list of every node for a still running `qmmove` task of the user that this
tool is configured with. The tool excludes any vmid that it finds from the planning
of this run, exactly like a manual `exclude.vmids` entry. The report shows the vmid
as pinned, with the reason "excluded by config (`exclude.vmids`)". A log line at
`WARNING` says which check found it. The tool never force-cancels the task, and
this run never assumes that it is safe to touch the disk of that VM again.

During execution, the tool writes `inflight_upids` to `state.json` **before** it
issues each `move_disk`. It clears the entry after that task itself ends. The write
is synchronous. A crash in the middle of a move (kill, out of memory, host reboot)
thus leaves a trace that the startup check of the *next* run finds. The tool does
not only update the file at the very end of a whole `apply` run. See
`docs/internals/93-crashrecovery.md` for the full mechanism.

## `--json`

The output has the same `groups[]` shape as `plan` (see `docs/manual/27-plan.md`),
with one addition per group: `"execution"`. It is `null` when the tool never reached the group. The causes are a `load_error`,
`NO ACTION`, or an earlier group that stopped the run (for example, a `[q]uit` of
the operator).
Otherwise it is an object with these fields:

- `stopped_early`;
- `stop_reason` (`null` unless the run stopped for this group specifically);
- `aborted` (`true` when the execution of this group met one of the failures above
  and the run ended because of it);
- `replans_exhausted` (`true` when `execution.max_replans_per_run` ran out; the run
  stops and exits `0`);
- `outcomes[]`: one entry for each move that the tool actually attempted.

Each outcome has `disk_key`, `vm_name`, `from_storage`, `to_storage`, `status`
(`would_move`/`moved`/`skipped`/`failed`/`draining`/`replan_needed`), `detail`,
`upid` and `orphaned_volumes`. `upid` is `null` unless the tool actually issued
`move_disk` for this move. It is always `null` for `would_move`/`replan_needed`. It
is also `null` for `skipped`: even a lock timeout in that case happens before the
tool issues anything. A `failed` outcome carries a UPID in `upid` only when the task itself
ran and failed, not when a lock timeout aborted the move before the task started.
`orphaned_volumes` is only non-empty after a `failed` outcome.
