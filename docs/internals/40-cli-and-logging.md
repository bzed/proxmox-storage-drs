# Command dispatch, the mode-override rule, and why logs go to stderr

**What does this page answer?** How does `cli.py` turn `argv` into a
dispatched command? What does an override of `--mode` log, exactly? Why does
structured logging go to stderr instead of the stdout that the plan
originally specified? How does an unattended `apply` tell a monitoring
system what it did? This page describes `proxmox_storage_drs/cli.py`,
`proxmox_storage_drs/logging_setup.py` and `proxmox_storage_drs/statusfile.py`.

## One parser, global options first

`build_parser()` defines every global option (`-c`/`--config`, `--group`,
`--mode`, `--json`, `-v`/`--quiet`, `--version`, `--manual`) on the
**top-level** `ArgumentParser`, not on the subparsers. With that placement,
argparse enforces the rule "global options before the subcommand" of
`IMPLEMENTATION_PLAN.md` section 11.3 without extra code. No hand-written
ordering check exists anywhere. The defaults in `--help` come from the real
`default=` values passed to `add_argument`, together with
`argparse.ArgumentDefaultsHelpFormatter`. This module, the manpage and the
manual deliberately hold no second, hand-maintained list of options and
defaults (AGENTS.md section 8.5).

`main()` handles `--version` and `--manual`/`help` **before** it requires or
loads any configuration. Printing the version or the manual page must never
depend on `/etc/pve/drs.yaml` existing. The function calls
`config.load_config()` only once a real subcommand is present.

**`-v`/`--verbose` is otherwise purely a `logging_setup.py` concern** (see
below). Every subcommand's own stdout report is identical. The report stays
the same no matter how many times the flag is given. One exception exists.
`_handle_explain()` reads `args.verbose` directly. When the flag is set,
the function adds a `data source:` line to its own report. The line names
the section 3.4 node-scoping filter. It also names the window/rate
settings that the run's queries used (`docs/manual/29-explain.md`). This is
the one place where a global option's effect differs across commands. The
purpose of `explain` is to narrate *how* a result was produced. The other
commands' reports have no need to print that provenance.

## Command handlers: a dict, not a chain of `if`s

`_COMMAND_HANDLERS: dict[str, CommandHandler]` maps each subcommand name to
a function of `(ResolvedConfig, argparse.Namespace, effective_mode) -> int`.
A subcommand without an implementation gets a handler from
`_make_not_yet_implemented_handler(name)`. The factory is a closure, not a
`lambda` with a default-argument trick. The strict mode of mypy cannot infer
the parameter types of a bare lambda cleanly here. If you want to simplify the
factory back to a one-liner, read the comment at that function first.

Every subcommand in `_SUBCOMMANDS` now has a real handler (`explain` was the
last one; see
[`../manual/30-safety-and-status.md`](../manual/30-safety-and-status.md)).
The factory is therefore only the extension point for the next command. The
dict-comprehension initializer of `_COMMAND_HANDLERS` still runs the factory
for every name. Each real handler then overwrites its own entry. A new
command that you add to `_SUBCOMMANDS` without a handler assignment thus
fails honestly, instead of a `KeyError` from the dispatch of `main()`.

The real `_handle_verify_metrics` overwrote
`_COMMAND_HANDLERS["verify-metrics"]` once `metrics.py` existed to support
it. The same happened for every other command when its own module landed. The
handler of `apply` is `_handle_apply` (`execute.py`/`crashrecovery.py`). The
handler of `explain` is `_handle_explain`. It runs the identical
`_plan_group()` pipeline that `plan` runs. It narrates the pins, the
fragmentation that they cause, and the seven terms of the section 5.4
objective that `plan` itself never prints. To add a new implemented command,
write the handler and assign it into the dict. Nothing else changes. The
dispatch in `main()` stays the same.

## `--group`: filtered once, right after `build_topology()`

`_filter_groups(topology, args.group)` is the one place that reads `--group`.
`show-load`, `verify-storages`, `plan`, `explain` and `apply` each call it
immediately after `build_topology()`. The function replaces the `groups` tuple of that
`Topology` with the named subset. The subset keeps the topology order. Every
render function downstream iterates `topology.groups` as before. It needs no
`--group` awareness of its own.

`verify-metrics` does not call the function. That command checks the
configured metric and label names against Prometheus directly. It never
iterates groups, so `--group` has nothing to restrict there.

A name that matches no configured group raises `DrsError`. It never produces
an empty report without a message. `config.load_config()` applies the same
rule to `-c`/`--config PATH`: an explicitly named thing that does not resolve
is a hard failure. REVIEW.md R-03 records the reason: an earlier version
parsed and documented `--group`, but no handler ever read `args.group`.

## The `--mode` escalation rule

`apply_mode_override(configured_mode, override)` is the entire implementation
of the section 11.3 rule. The order of the modes is `dry-run < confirm <
auto`. A move *down* this order (toward more caution) logs at `INFO`. A move
*up* this order logs at `WARNING` and names both values. Such a move goes
toward less caution: it removes a barrier that the operator's own config set.
The function is deliberately a small, almost pure function. Its only side
effect is the log call. It is not inlined into `main()`. A unit test can thus
check it with a `caplog` fixture without a full CLI invocation.

## Why logs go to stderr, not stdout

`IMPLEMENTATION_PLAN.md` section 2.1 originally specified stdout for
structured JSON logs. The commit that added `logging_setup.py` amended the
plan. `--json` (section 9.5) emits the plan report on **stdout**. Log lines
mixed into that report on the same stream would make it impossible to parse
for anything downstream. Logging therefore goes to **stderr**. A systemd
service unit captures both streams into the same journal, so journald still
captures everything. This is the one place in the codebase where the
implementation and the *original* plan text disagree on purpose. The same
commit corrected the plan text, because AGENTS.md section 7 rule 2 forbids a
silent divergence between the plan and the code.

`main()` calls `configure_logging()` exactly once, via
`_start_logging_and_announce_run()`. The call comes after the early exits of
`--version`/`--manual`, which must not touch the logging configuration at
all. Since the section 2.3 rework, it also comes *after* `load_config()`, not
before it. That order is deliberate and slightly counter-intuitive. The
mandatory `INFO` floor depends on the effective execution mode. The tool does
not know that mode until it reads the config. `apply_mode_override()` itself
logs, so it must run after the tool decides the log level. As a result, one
thing now happens *before* logging exists: a config file that cannot be read
or parsed. The tool reports it with a plain `print()` to stderr. That is what
it always was: a usage failure, not an event in a run that never started.

## Levels, the mandatory floor, and why the handler is on root

`IMPLEMENTATION_PLAN.md` section 2.3 is the policy. `logging_setup.py` is
three small pure functions plus the installer. A test can thus check every
part of that policy without a command run:

- `resolve_level()`: the ladder `--quiet` < default < `-v` < `-vv`.
  `--log-level` wins over all of these.
- `floor_for_command()`: `INFO`, and only for `apply` in `confirm`/`auto`.
  The rule is: a run that can change the cluster logs what it did, whether or
  not anyone asks. It is a *floor*, not an override, so that `--quiet` can
  still win.
- `resolve_format()`: `text` and the legacy `auto` resolve to `text`. Only an
  explicit `json` selects JSON. Through 0.1.9, `auto` inspected the stream and
  chose JSON for any non-TTY. That put one JSON object per line into
  `journalctl -u pve-storage-drs`. A person reads that unattended path far
  more often than `jq` does. JSON stays for the operator who wants a record
  *as each move starts and finishes*: they pass `--log-format json` in the
  unit. The `--json` report at the end of a run cannot give that for a run
  that dies in the middle of a move.

**The handler goes on the root logger, and the package logger carries only a
level.** The first attempt used the obvious alternative: a handler on
`proxmox_storage_drs` with `propagate = False`. It is wrong for two reasons.
It hides every record from the `caplog` of pytest, whose handler sits on root,
and from any application that embeds this package. It also needs a *second*
handler on root anyway, so that third-party records are visible at `-vv`.
Levels give the same separation with one handler. The level of the package
logger filters our records, and they then propagate to the handler of root.
The level of root filters `urllib3` and similar libraries. That level stays at
`WARNING` unless `-vv` lowers it.

`logging` is global to the process. `tests/conftest.py` therefore restores the
level of the package logger and the handlers of root around every test.
Without this, a test that runs a command leaks its verbosity into the next
test. That happened exactly once: a `caplog`-based topology test passed alone
and failed in the suite.

## `JsonFormatter`: what ends up in one log line

Some fields of a `logging.LogRecord` are *not* standard attributes. The module
computes the set of standard attributes once, at import time, as
`_STANDARD_RECORD_ATTRS`. `JsonFormatter` folds every other field into the
JSON payload. Any module can therefore call
`logger.info("...", extra={"event": "gate_decision", "threshold": 0.2})`.
`event` and `threshold` then appear as top-level JSON keys, with no change to
the formatter. `sort_keys=True` keeps the output byte-stable for anything that
compares log lines, in a test or in a log-aggregation pipeline.

Two constraints apply to the content of `extra=`.

- **Every record carries an `event`.** The names are an interface:
  `jq 'select(.event=="move_started")'` is a supported way to use this tool.
  `test_logging_setup.py` parses `src/` with `ast` to prove that no call site
  forgets the name.
- `extra=` must not shadow a standard `LogRecord` attribute. `{"message":
  ...}` raises `KeyError: "Attempt to overwrite 'message' in LogRecord"` at
  run time. For this reason, the payload key of the `deadlock` record is
  `detail`.

`TextFormatter` is the default counterpart. It writes `LEVEL: message` for
anything above `INFO`, and bare text at `INFO`. An `INFO:` prefix on every
line of a narrative that the user asked for is noise, not information.

## `--manual`: preferring `man(1)`, falling back only when necessary

`show_manual()` tries `man pve-storage-drs` first, through `subprocess.run`
instead of `os.execvp`. `man(1)` itself detects a stdout that is not a tty and
disables its pager. That satisfies "never answer with a URL alone" (AGENTS.md
section 8.5), for an interactive call and for a piped call. This module does
not need to repeat the tty detection.

The tool uses `_fallback_manual_text()` only when `man(1)` is missing or has no
entry. Examples are a source checkout without installation, or a minimal system
without man-db. The function walks up from the location of `cli.py` and looks
for `man/pve-storage-drs.1.md` in a source tree. If that also fails, it prints
a short message. The message names the package to install and the file
`man/pve-storage-drs.1.md` in the source tree. The user can act on both. The
message is never a bare URL.

## The unfixable-shortfall report

`_render_group_plan_human()` (shared by `plan`, `apply` and `explain`) and
`_render_group_plan_json()` both end a group with the same derived fact.
`_unfixable_shortfall()` reads `final_breakdown.reserve_statuses`. This is the
reserve and free-space state of the assignment that the *solver and scheduler*
leave behind. When a storage is still short there, the function returns an
`_UnfixableShortfall`. It holds:

- the bytes per storage;
- whether the result is a proof (`proven`). Only a CBC solve with status
  `optimal` is a proof, because only its lexicographic stage 1 minimizes
  `Σ r_s` exactly;
- every pinned disk on a short storage.

The human output prints it as `⚠ unfixable shortfall: …` plus the pinned disks.
`--json` prints it as `groups[].unfixable_shortfall` (`null` when nothing is
short).

Before this report existed, a shortfall that nothing could relieve could force
a group to `ACT`. The group then printed its gate line, a `solver:` line and
nothing else. The run never mentioned the breach that caused it again. That
read as if the tool ignored the breach.

The report does not include moves that the solver *did* propose and that the
hard duration rule per move then refused. Those moves have their own
`⚠ blocked by the hard per-move duration rule` line. The status-file warning
(below) tracks the shortfall of the *executed* endpoint.

## "no moves made" in `plan` and `apply`

`_render_plan_no_moves_lines()` covers the other way an `ACT` group can end
empty: the objective prefers the current placement. The function prints nothing
in these cases:

- the gate did not act;
- any move is scheduled;
- the scheduler deadlocked (its own `⚠` line explains that);
- an unfixable shortfall is reported (that line explains it).

The function is deliberately cheap. It runs no extra solve and no candidate
search, because `plan` runs in every cycle. It points to `explain`, whose
`_render_no_moves_lines()` does the expensive part
(`best_single_disk_alternative()`). `explain` therefore calls the shared
renderer with `explain_no_moves=False`, so that the group does not get both.
The text claims "Scores best" only for a CBC solve with status `optimal`.

Sometimes only the capacity gate opens a group: `GateDecision.capacity_fraction`
is set, and reserve override, drift and imbalance are all unset. Such a group
gets a second line (`_capacity_gate_hint()`). The line names
`objective.beta_move_count`, `objective.gamma_move_bytes_per_tib` and
`objective.delta_capacity_spread` with their values. It also prints the
break-even disk size `X* = beta / (2 delta - gamma)` TiB. In such a group, the
I/O is usually balanced already. The data-spread term, priced per TiB, is then
the only term that can pay for a move. Only a disk above `X*` can pay for
itself (about 270 GiB at the defaults). At `2 delta <= gamma`, the line says
instead that no disk of any size can. The weights reach the renderer as an
optional `objective` argument. `_render_plan_human()`/`_render_apply_human()`
pass it through from the resolved config.

## The monitoring status file: `statusfile.py`

`monitoring.status_file` (section 2.4) makes `apply` leave a report that a
Nagios-style check can read. The module is deliberately two pure halves and one
side effect. A test can thus check the policy without a cluster:

- `build_run_status(RunReport) -> RunStatus` is the level policy. `RunReport` is
  the run reduced to what the policy needs: the mode, the exit code, counters,
  and two lists of single-sentence strings, `errors` and `warnings`.
  `cli._RunStats` collects these during the run. These sources fill it:
  - `_accumulate_move_stats()`/`_record_outcome_for_status()` (failed moves,
    `draining` sources, orphaned volumes, an exhausted re-plan cap,
    `ExecutionResult.abort_reason`);
  - `_handle_apply()` (the load error of a group, and a group that is still short
    of its reserve after its plan: `_GroupPlan.shortfall_bytes`);
  - the exception handler in `_run_handler()`.

  A non-zero exit code gives `CRITICAL`. Otherwise, any warning gives
  `WARNING`. Otherwise the level is `OK`. The module never produces `UNKNOWN`.
  The plugin uses that level for a missing or malformed file.
- `render_status(RunStatus) -> str` is the exact text of the file: the level
  word, then the summary followed by `| label=value` perfdata, then the detail
  lines, one line each. The headline already carries the first problem, so the
  details list the rest. Every message passes through `_one_line()`. A newline
  inside a message would become a line of its own in the output of the plugin and
  could push the summary off line 2.
- `write_status_file()` is the only function that touches the filesystem. It
  writes a temporary file in the same directory, sets the mode to `0644` with
  `fchmod`, calls `fsync` and then `os.replace`. The monitoring user is not the
  user that `apply` runs as, and `mkstemp` creates `0600`. For this reason, the
  function changes the mode. It creates the directory like
  `state.save_state_atomic()` does. It raises `StatusFileError` on any
  `OSError`.

**The format is the plugin's, not ours.** `check_statusfile` is a short Python
script. Line 1 must be exactly `OK`/`WARNING`/`CRITICAL`/`UNKNOWN`. The script
prints every later line verbatim, and there must be at least one. The mtime of
the file, not its content, decides staleness. These three facts fix the design.
The level words are constants. The summary is never empty (otherwise the plugin
reports "Found no output", which is `UNKNOWN`). The tool writes the file on every
run, including dry runs and runs that did nothing, so that the mtime means "the
timer still fires". `tests/unit/test_statusfile.py` and the CLI tests run the
real plugin over the output whenever it is installed. They do not assert our own
reading of it.

**When the tool writes the file** is decided in `cli._publish_status_file()`,
which `main()` calls after `_log_run_summary()`. The function writes only:

- for `apply`;
- not under `--replay`;
- not when `_RunStats.lock_held` says that another instance held the lock (the
  run produced no result);
- only when a path is configured.

The bug branch of `_run_handler()` also calls the function *before* it raises
the exception again. A crash thus leaves `CRITICAL`, not the `OK` of the
previous run. The function logs a `StatusFileError` (`status_file_write_failed`)
and swallows it. A monitoring file must not change what a run did or its exit
code. A file that stops updating turns `WARNING` by age anyway.
