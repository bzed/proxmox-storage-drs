# Command dispatch, the mode-override rule, and why logs go to stderr

**What does this page answer?** How does `cli.py` turn `argv` into a
dispatched command, what exactly does overriding `--mode` log, and why does
structured logging go to stderr instead of the stdout the plan originally
specified? Describes `proxmox_storage_drs/cli.py` and
`proxmox_storage_drs/logging_setup.py`.

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
section 5.4 objective's five terms that `plan` itself never prints.
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

`configure_logging()` is called exactly once, from `main()`, after the
`--version`/`--manual` early exits (which must not touch logging
configuration at all) and before any config-dependent code runs, so that a
config-loading failure is itself logged consistently with everything after
it.

## `JsonFormatter`: what ends up in one log line

Every field on a `logging.LogRecord` that is *not* one of the standard
attributes (computed once, at import time, into `_STANDARD_RECORD_ATTRS`) is
folded into the JSON payload — this is what lets any module call
`logger.info("...", extra={"event": "gate_decision", "threshold": 0.2})` and
have `event`/`threshold` appear as top-level JSON keys with no formatter
changes required. `sort_keys=True` keeps output byte-stable for anything
that diffs log lines in a test or a log-aggregation pipeline.

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
