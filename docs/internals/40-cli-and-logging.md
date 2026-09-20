# Command dispatch, the mode-override rule, and why logs go to stderr

**What does this page answer?** How does `cli.py` turn `argv` into a
dispatched command, what exactly does overriding `--mode` log, and why does
structured logging go to stderr instead of the stdout the plan originally
specified, and how does an unattended `apply` tell a monitoring system what it
did? Describes `proxmox_storage_drs/cli.py`,
`proxmox_storage_drs/logging_setup.py` and `proxmox_storage_drs/statusfile.py`.

## One parser, global options first

`build_parser()` defines every global option (`-c`/`--config`, `--group`,
`--mode`, `--json`, `-v`/`--quiet`, `--version`, `--manual`) on the
**top-level** `ArgumentParser`, not on the subparsers, which is what makes
argparse itself enforce `IMPLEMENTATION_PLAN.md` section 11.3's "global
options before the subcommand" for free — there is no hand-written ordering
check anywhere. `--help`'s defaults come from the real `default=` values
passed to `add_argument`, combined with
`argparse.ArgumentDefaultsHelpFormatter`; there is deliberately no second,
hand-maintained list of options and defaults anywhere in this module, the
manpage, or the manual (AGENTS.md section 8.5).

`main()` handles `--version` and `--manual`/`help` **before** requiring or
loading any configuration — printing the version or the manual page must
never depend on `/etc/pve/drs.yaml` existing. Only once a real subcommand is
present does it call `config.load_config()`.

**`-v`/`--verbose` is otherwise purely a `logging_setup.py` concern** (see
below) — every subcommand's own stdout report is identical regardless of
how many times it was given, with one deliberate exception:
`_handle_explain()` reads `args.verbose` directly and adds a `data
source:` line to its own report when set, naming the section 3.4
node-scoping filter and window/rate settings the run's queries used
(`docs/manual/29-explain.md`). This is the one place a global option's
effect is not identical across every command, because `explain`'s entire
purpose is narrating *how* a result was produced — provenance the other
commands' reports have no occasion to print.

## Command handlers: a dict, not a chain of `if`s

`_COMMAND_HANDLERS: dict[str, CommandHandler]` maps each subcommand name to
a function of `(ResolvedConfig, argparse.Namespace, effective_mode) -> int`.
A subcommand not yet implemented gets a handler from
`_make_not_yet_implemented_handler(name)`, a closure factory rather than a
`lambda` with a default-argument trick, because mypy's strict mode cannot
infer a bare lambda's parameter types cleanly here — see the comment at that
function if you are tempted to simplify it back to a one-liner. Every
subcommand in `_SUBCOMMANDS` now has a real handler (`explain` was the
last one — see
[`../manual/30-safety-and-status.md`](../manual/30-safety-and-status.md)),
so this factory is currently only the extension point for the next one:
`_COMMAND_HANDLERS`'s dict-comprehension initializer still runs it for
every name before each real handler overwrites its own entry, so a new
command added to `_SUBCOMMANDS` without a handler assignment fails
honestly instead of a `KeyError` from `main()`'s dispatch.
`_COMMAND_HANDLERS["verify-metrics"]` is overwritten with the real
`_handle_verify_metrics` once `metrics.py` exists to back it, and likewise
for every other command as its own module landed — `apply`'s handler is
`_handle_apply` (`execute.py`/`crashrecovery.py`); `explain`'s is
`_handle_explain`, which runs the identical `_plan_group()` pipeline
`plan` does and narrates the pins, the fragmentation they cause, and the
section 5.4 objective's six terms that `plan` itself never prints.
Adding a new implemented command is exactly this: write the handler,
assign it into the
dict, done — `main()`'s dispatch does not change.

## `--group`: filtered once, right after `build_topology()`

`_filter_groups(topology, args.group)` is the one place `--group` is
actually read. `show-load`, `verify-storages` and `plan` each call it
immediately after `build_topology()`, replacing that `Topology`'s
`groups` tuple with the (still topology-order) subset named — every
render function downstream just iterates `topology.groups` as before and
needs no `--group` awareness of its own. `verify-metrics` does not call
it: that command validates configured metric/label names against
Prometheus directly and never iterates groups at all, so there is nothing
for `--group` to restrict there. A name that matches no configured group
raises `DrsError` rather than silently producing an empty report — the
same "an explicitly named thing that doesn't resolve is a hard failure"
rule `config.load_config()` already applies to `-c`/`--config PATH`
(REVIEW.md R-03: `--group` was previously parsed and documented, but no
handler ever read `args.group` at all).

## The `--mode` escalation rule

`apply_mode_override(configured_mode, override)` is the entire
implementation of section 11.3's rule: moving *down* the ordering `dry-run <
confirm < auto` (toward more caution) logs at `INFO`; moving *up* it (toward
less caution — removing a barrier the operator's own config set) logs at
`WARNING`, naming both values. This is deliberately a small pure-ish
function (its only side effect is the log call) rather than inlined into
`main()`, so it is unit-testable against a `caplog` fixture without
constructing a full CLI invocation.

## Why logs go to stderr, not stdout

`IMPLEMENTATION_PLAN.md` section 2.1 originally specified stdout for
structured JSON logs. This was amended in the same commit that added
`logging_setup.py`: `--json` (section 9.5) emits the plan report on
**stdout**, and interleaving log lines with that report on the same stream
would make it unparseable by anything downstream. Logging instead goes to
**stderr**; a systemd service unit captures both streams into the same
journal regardless, so nothing about "captured by journald" is lost. This is
the one place in the codebase where the implementation and
`IMPLEMENTATION_PLAN.md` disagree with the *original* plan text on purpose —
AGENTS.md section 7 rule 2 is why the plan text itself was corrected in the
same commit rather than left to silently diverge from the code.

`configure_logging()` is called exactly once, from `main()` via
`_start_logging_and_announce_run()`, after the `--version`/`--manual` early
exits (which must not touch logging configuration at all) — and, since the
section 2.3 rework, *after* `load_config()` rather than before it. That
ordering is deliberate and slightly counter-intuitive, so it is worth
stating why: the mandatory `INFO` floor depends on the effective execution
mode, which is not known until the config is read, and `apply_mode_override()`
itself logs, so it has to run after the level it should be logged at has
been decided. The one thing that moves *before* logging exists as a result —
a config file that could not be read or parsed — is reported with a plain
`print()` to stderr, which is what it always was: a usage failure, not an
event in a run that never started.

## Levels, the mandatory floor, and why the handler is on root

`IMPLEMENTATION_PLAN.md` section 2.3 is the policy; `logging_setup.py` is
three small pure functions plus the installer, so that every part of that
policy is testable without running a command:

- `resolve_level()` — the `--quiet` < default < `-v` < `-vv` ladder, with
  `--log-level` winning over all of it.
- `floor_for_command()` — `INFO`, and only for `apply` in `confirm`/`auto`.
  This is the "a run that can change the cluster logs what it did whether or
  not anyone asked" rule, and it is a *floor* rather than an override
  precisely so `--quiet` can still win.
- `resolve_format()` — `auto` resolves to `text` at a TTY and `json`
  everywhere else. A systemd unit therefore gets JSON without the unit
  saying anything, and an operator at a terminal gets prose without passing
  a flag; that one rule is the entire fix for "why is my terminal full of
  JSON".

**The handler goes on the root logger, and the package logger carries only
a level.** The obvious-looking alternative — handler on
`proxmox_storage_drs`, `propagate = False` — was tried first and is wrong
twice over: it hides every record from pytest's `caplog` (whose handler sits
on root) and from any application embedding this package, and it needs a
*second* handler on root anyway for third-party records to be visible at
`-vv`. Setting levels instead gets the same separation with one handler:
our records are filtered by the package logger's level and then propagate to
root's handler, while `urllib3` and friends are filtered by root's own
level, which stays at `WARNING` unless `-vv` lowered it.

Because `logging` is process-global, `tests/conftest.py` restores the
package logger's level and root's handlers around every test. Without it a
test that runs a command leaks its verbosity into whatever runs next — which
showed up exactly once, as a `caplog`-based topology test that passed alone
and failed in the suite.

## `JsonFormatter`: what ends up in one log line

Every field on a `logging.LogRecord` that is *not* one of the standard
attributes (computed once, at import time, into `_STANDARD_RECORD_ATTRS`) is
folded into the JSON payload — this is what lets any module call
`logger.info("...", extra={"event": "gate_decision", "threshold": 0.2})` and
have `event`/`threshold` appear as top-level JSON keys with no formatter
changes required. `sort_keys=True` keeps output byte-stable for anything
that diffs log lines in a test or a log-aggregation pipeline.

Two constraints on what may go in `extra=`. First, **every record carries an
`event`** — the names are an interface (`jq 'select(.event=="move_started")'`
is a supported way to use this tool), and `test_logging_setup.py` parses
`src/` with `ast` to prove no call site forgot one. Second, `extra=` may not
shadow a standard `LogRecord` attribute: `{"message": ...}` raises
`KeyError: "Attempt to overwrite 'message' in LogRecord"` at runtime, which
is how the `deadlock` record's payload key came to be `detail`.

`TextFormatter` is the `auto`-at-a-TTY counterpart: `LEVEL: message` for
anything above `INFO`, and bare prose at `INFO`, because prefixing every
line of a requested narrative with `INFO:` is noise rather than
information.

## `--manual`: preferring `man(1)`, falling back only when necessary

`show_manual()` tries `man pve-storage-drs` first, via `subprocess.run` rather
than `os.execvp`: `man(1)` itself detects a non-tty stdout and disables its
pager automatically, which is what satisfies "never answer with a URL
alone" (AGENTS.md section 8.5) whether the invocation is interactive or
piped — there is no need for this module to duplicate that tty detection.
`_fallback_manual_text()` is reached only when `man(1)` itself is missing or
has no entry (an uninstalled source checkout, or a minimal system with no
man-db): it walks up from `cli.py`'s own file location looking for
`man/pve-storage-drs.1.md` in a source tree, and only if that also fails
prints a short message naming the real installed-package path and the
in-tree file — a local, actionable path, never a bare URL.

## The monitoring status file: `statusfile.py`

`monitoring.status_file` (section 2.4) makes `apply` leave a report a
Nagios-style check can read. The module is deliberately two pure halves and one
side effect, so the policy is testable without a cluster:

- `build_run_status(RunReport) -> RunStatus` is the level policy. `RunReport` is
  the run reduced to what the policy needs (mode, exit code, counters, and two
  lists of single-sentence strings: `errors` and `warnings`); `cli._RunStats` is
  where those accumulate while the run goes, filled by
  `_accumulate_move_stats()`/`_record_outcome_for_status()` (failed moves,
  `draining` sources, orphaned volumes, an exhausted re-plan cap,
  `ExecutionResult.abort_reason`), by `_handle_apply()` (a group's load error, a
  group still short of its reserve after its plan — `_GroupPlan.shortfall_bytes`)
  and by the exception handler in `_run_handler()`. A non-zero exit code is
  `CRITICAL`; otherwise any warning is `WARNING`; otherwise `OK`. `UNKNOWN` is
  never produced — it is what the plugin says about a missing or malformed
  file.
- `render_status(RunStatus) -> str` is the file's exact text: the level word,
  then the summary followed by `| label=value` perfdata, then the detail lines
  (the headline already carries the first problem, so the details list the
  rest), one line each. Every message is passed through `_one_line()` because a
  newline inside one would become a line of its own in the plugin's output and
  could push the summary off line 2.
- `write_status_file()` is the only function that touches the filesystem: a
  temporary file in the same directory, `fchmod` to `0644` (the monitoring user
  is not the user `apply` runs as, and `mkstemp` creates `0600`), `fsync`,
  `os.replace`. It creates the directory like `state.save_state_atomic()` does
  and raises `StatusFileError` on any `OSError`.

**The format is the plugin's, not ours.** `check_statusfile` is a short Python
script: line 1 must be exactly `OK`/`WARNING`/`CRITICAL`/`UNKNOWN`; every later
line is printed verbatim and there must be at least one; the file's mtime, not
its content, decides staleness. Those three facts fix the design: the level
words are constants, the summary is never empty (otherwise "Found no output" →
`UNKNOWN`), and the file is written on every run (including dry runs and runs
that did nothing) so that mtime means "the timer is still firing".
`tests/unit/test_statusfile.py` and the CLI tests run the real plugin over the
output whenever it is installed rather than asserting our own reading of it.

**When it is written** is `cli._publish_status_file()`, called from `main()`
after `_log_run_summary()`: only for `apply`, not under `--replay`, not when
`_RunStats.lock_held` says another instance held the lock (no result was
produced), and only when a path is configured. It is also called from
`_run_handler()`'s bug branch *before* the exception is re-raised, so a crash
leaves `CRITICAL`, not the previous run's `OK`. A `StatusFileError` is logged
(`status_file_write_failed`) and swallowed: a monitoring file must not change
what a run did or its exit code, and a file that stops updating turns
`WARNING` by age anyway.

