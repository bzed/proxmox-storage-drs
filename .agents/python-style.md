# Python style

## Baseline

Everything the formatter can decide, the formatter decides. Do not argue with black in review;
change the config or accept the output.

```
black       line-length 100
isort       profile = black, line_length 100
flake8      max-line-length 100, extend-ignore = E203,E704,W503, max-complexity 12
mypy        strict-ish (see pyproject.toml); new modules must type-check clean
```

All four are configured in `pyproject.toml` except flake8, which cannot read `pyproject.toml`
without a plugin and therefore lives in `.flake8`. The two files must agree on line length —
if you change one, change the other, and say so in the commit message.

### The three disagreements, resolved

| Code | flake8 says | black does | We keep |
|---|---|---|---|
| `E203` | no whitespace before `:` | `ham[lower + offset : upper]` | black — slices are binary operators, PEP 8 agrees since 2020 |
| `W503` | no line break *before* a binary operator | breaks before operators | black — this is now the recommended style; `W503` is the legacy rule |
| `E704` | no statement on the same line as `def` | one-line `...` bodies for overloads/protocols | black |

`E501` (line too long) is deliberately **not** ignored. black splits what it can; what is left
is a long string or URL that a human should look at.

## Conventions

- `from __future__ import annotations` first line of code in every module.
- SPDX header (two comment lines) above the module docstring:
  ```python
  # SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
  # SPDX-License-Identifier: AGPL-3.0-or-later
  ```
- Type-annotate every public function, including the return type. `-> None` is not optional.
- Frozen `@dataclass(frozen=True, slots=True)` for value objects (a disk, a storage, a move,
  a plan). The engine is stateless except for `state.json`; mutable objects invite the kind of
  aliasing bug that silently corrupts a migration plan.
- **Units in names.** `size_bytes`, `size_tib`, `duration_seconds`, `load_inflight`,
  `throughput_bytes_per_sec`. A bare `size` or `load` in a signature is a review comment.
  The plan mixes TiB (worked example), MiB (CP-SAT scaling) and bytes (API); the names are the
  only defence against a unit error, and a unit error here overfills a SAN.
- **One implementation of every rule.** The MILP path and the heuristic path share the
  feasibility predicates and the objective function. If you need the reserve check in a second
  place, import it; do not rewrite it.
- Errors: define an exception hierarchy rooted at a project base exception. No bare `except:`.
  `except Exception` only at the CLI boundary, and it logs with context and exits non-zero.
- Logging: structured JSON via the project logger (plan §2.1). `print()` only in `cli.py` for
  human-facing output. Every gate decision, every issued move with its UPID, every abort and
  every re-plan gets a log record — this tool runs unattended and the log is the only witness.
- No I/O in pure functions. The solver, the load model, the payback rule and the scheduler take
  data structures and return data structures; the API and Prometheus clients are the only things
  that touch the network, and they sit behind interfaces so tests can substitute recorded data.

## Dependencies

Pinned in `pyproject.toml`. Adding one is a deliberate act: it must be licence-compatible with
AGPL-3.0-or-later, packaged for Debian/PVE if plausible, and justified in the commit message.
The heuristic fallback path must stay importable with **no** solver dependency installed —
that is a plan requirement, and a test asserts it.
