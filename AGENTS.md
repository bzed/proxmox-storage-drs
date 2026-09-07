# AGENTS.md — working agreement for this repository

This file configures **any** agent (Claude Code, Codex, Aider, a human) working on
`proxmox-storage-drs`. It is normative: if something here conflicts with a general habit,
this file wins. Detailed guidance lives in [`.agents/`](.agents/); this file is the index
and the short version.

---

## 0. Identity, licence, copyright

- **Project:** a Storage DRS replacement for Proxmox VE 9.2 — see
  [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md), which is the specification and the
  source of truth for behaviour.
- **Names, and they are not interchangeable:** the distribution is `proxmox-storage-drs`, the
  import package is `proxmox_storage_drs`, and the **installed executable is `pve-storage-drs`** —
  one `[project.scripts]` entry point onto `cli.py`. Every command in the documentation, in
  `--help`, in the manpage and in commit messages is written `pve-storage-drs <subcommand>`.
  Never `drs`, and never `pve-drs`: PVE 9.2 ships a Dynamic Load Balancer that moves *guests*
  between nodes, and a name that does not say **storage** invites the reader to think this tool
  replaces that one. The Debian source and binary package carry the same name.
- **Licence:** GNU **AGPL-3.0-or-later**. Full text in [`LICENSE`](LICENSE).
- **Copyright holder:** `Bernd Zeimetz <bernd@bzed.de>`. One exception, and it is not a typo:
  `debian/changelog` is signed `Bernd Zeimetz <bzed@debian.org>`, the Debian developer address,
  because that is the identity for packaging work. Everything else — SPDX headers,
  `debian/copyright`, `pyproject.toml`, the manpage — uses `bernd@bzed.de`.

**Rules that must survive every edit session:**

1. Never remove, rewrite or "modernise" the copyright line. If a file gains substantial new
   content the holder stays the same unless Bernd says otherwise.
2. Every new source file (`.py`, and any shipped script) starts with:
   ```python
   # SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
   # SPDX-License-Identifier: AGPL-3.0-or-later
   ```
   Two comment lines, before the module docstring. No year ranges to churn — bump the year
   only when a file is substantially rewritten.
3. `LICENSE` is verbatim FSF text. Never edit it, reflow it, or replace it with a summary.
4. AGPL is copyleft with a network clause. Do not vendor, copy in, or link code under a
   licence incompatible with AGPL-3.0-or-later. If a dependency's licence is unclear, stop
   and ask rather than guessing.

---

## 1. Language and toolchain

| Item | Value |
|---|---|
| Language | Python **3.11+** (developed on 3.14; do not use syntax newer than 3.11) |
| Formatter | **black**, line length **100** |
| Import order | **isort**, `profile = "black"` |
| Linter | **flake8**, `max-line-length = 100`, `extend-ignore = E203,E704,W503` |
| Types | **mypy** |
| Tests | **pytest** + **pytest-cov**, minimum **85 %** line coverage |
| Config | `pyproject.toml` (black, isort, mypy, pytest, coverage) and `.flake8` (flake8 only) |

**Why the ignores exist — do not "fix" them by deleting them.** black and flake8 genuinely
disagree in three places, and the config resolves each one in black's favour so the two tools
can never fight:

- `E203 whitespace before ':'` — black writes `ham[lower + offset : upper]`; PEP 8 as flake8
  reads it disagrees. black is right (slices are binary operators).
- `W503 line break before binary operator` — black breaks *before* operators, which is the
  style PEP 8 now recommends; `W503` encodes the older rule.
- `E704 statement on same line as def` — black writes `...`-bodied overloads on one line.
- `E501` stays **on**, and `max-line-length` is set to the same 100 as black, so a line black
  cannot split (a long URL, a long string) is still reported and you deal with it deliberately.

Run the formatter before the linter, always. `make fmt lint` does that in the right order.

---

## 2. The loop — never commit without running it

```sh
make check          # fmt-check + lint + typecheck + test-with-coverage + fixtures + pdf-check
```

`make check` is what CI runs and what you run before every commit. It must be green.
If you cannot make it green, **do not commit to a shared branch** — commit on your feature
branch with the failure described in the commit message, and keep going.

Individual targets: `make fmt`, `make lint`, `make typecheck`, `make test`, `make cov`,
`make fixtures`, `make pdf`, `make pdf-check`. `make venv` bootstraps `.venv/` with the dev
dependencies; the Python tools are **not** installed system-wide on this host, so start there.
`make typecheck` runs against a second, separate `.venv-typecheck/` (`make venv-typecheck`),
not `.venv/` — `test`/`cov` install the optional `solver`/`forecast` extras into `.venv/` for
full backend coverage, and a numpy those pull in ships stubs `mypy` cannot parse
(`docs/internals/91-optimize.md`); both `make check` and plain `make typecheck` create
whichever venv they need on their own, so this is usually invisible. The paper toolchain
(`pandoc`, `lualatex`) *is* system-wide and is not part of either venv.

---

## 3. Testing — the 85 % rule and what it actually means

- **Minimum 85 % line coverage**, enforced mechanically by `--cov-fail-under=85` in
  `pyproject.toml`. It is a floor, not a target.
- Coverage is necessary, not sufficient. A test that executes a line without asserting
  anything about it is worse than no test, because it buys coverage while hiding the gap.
- The modules that carry the safety invariants — the reserve constraint, the transient
  invariant, the payback rule, the lock/drain handling — are held to a **higher** bar:
  every branch, and every documented edge case from the plan, gets an explicit test.
- The worked example in `IMPLEMENTATION_PLAN.md` §14 is an executable acceptance fixture:
  `tests/fixtures/fc-tier1.yaml` (input) and `fc-tier1.expected.json` (proven-optimal output,
  generated by exhaustive enumeration); `reserve-tradeoff.yaml` is its counterpart for the
  reserve-versus-balance conflict. **Never hand-edit an expected file** — change the input or
  the generator and re-run `python3 tests/fixtures/generate_expected.py`.
  `--check` asserts they are current and runs in CI.
- Never write a test against the PVE API or Prometheus over the network. Both clients are
  behind interfaces; tests use recorded fixtures.

Details and the test-layout conventions: [`.agents/testing.md`](.agents/testing.md).

---

## 4. Git workflow — branch, commit often, merge on green

- **Feature branches for anything longer than a single self-contained change.**
  `feat/…`, `fix/…`, `chore/…`, `docs/…`, `review/…`.
- **Commit often.** Small commits that each leave the tree in a describable state are the
  goal; a green tree is nice but a work-in-progress commit on a feature branch is fine and
  preferable to a giant one at the end. Say so in the message when a commit is WIP.
- **Merge to `main` only when `make check` is green** on the branch tip. Merge with
  `--no-ff` so the branch's shape survives in history.
- `main` must stay green. Never push a red `main`.
- Long or parallelisable work may be delegated to a subagent **on its own branch** (or a git
  worktree); the subagent runs `make check` itself before reporting done, and the merge back
  to `main` is the parent's decision, not the subagent's.
- Commit messages: imperative subject ≤ 72 chars, blank line, body explaining *why*. Agent
  commits end with the `Co-Authored-By:` trailer for the model that wrote them.
- **Never commit:** `config/drs.yaml` (holds the PVE password), `state.json`, `.env`,
  `.claude/`, coverage artefacts, `.venv/`. All are in `.gitignore`; if you find yourself
  adding an exception, stop and ask.

Details: [`.agents/git-workflow.md`](.agents/git-workflow.md).

---

## 5. Code style beyond the formatter

- Type-annotate every public function. `from __future__ import annotations` at the top of
  every module.
- Prefer plain functions and frozen dataclasses over classes with mutable state. The engine
  is specified as stateless apart from `state.json`; keep it that way.
- The optimisation model and the heuristic **must share** the feasibility and objective
  functions — one implementation, two callers. A second copy of the reserve check is a bug.
- No bare `except:`; no `except Exception` without re-raising or logging with context.
- Money-shot numbers (sizes, loads, durations) carry their unit in the name: `size_bytes`,
  `duration_seconds`, `load_inflight`. Never a bare `size`.
- Logging is **structured** (JSON) per plan §2.1. No `print()` outside `cli.py`.
- Docstrings on every module and public function; reference the plan section that specifies
  the behaviour (`"""... See IMPLEMENTATION_PLAN.md §8.1."""`).

Details: [`.agents/python-style.md`](.agents/python-style.md).

---

## 6. Domain rules an agent must not "optimise away"

These come out of the plan and out of the fact that this tool moves live production data:

1. **Dry-run is the default.** Any change that makes the tool act without an explicit
   execution mode is a defect, no matter how convenient.
2. **The snapshot reserve is never traded for balance.** Lexicographic solve is the default;
   the big-M penalty is the fallback and its `P` is *computed*, never taken from config as-is.
3. **The transient invariant holds during moves, not just before and after.**
4. **A finished task is not a finished move** — the source volume must be observed gone and
   the VM config unlocked. See plan §9.3.
5. **Never auto-delete a volume.** Orphans are reported, never cleaned up automatically.
6. When the plan and the code disagree, **the plan is right and the code is a bug** — unless
   the plan is wrong, in which case fix the plan *in the same commit*.

Details: [`.agents/domain-invariants.md`](.agents/domain-invariants.md).

---

## 7. Working with the specification

`IMPLEMENTATION_PLAN.md` is large and precise. Before changing behaviour:

1. Find the section that specifies it (§ numbers are stable; the ToC is the heading list).
2. Change the plan and the code together. A code change that contradicts the plan without
   updating it is not done.
3. `REVIEW.md` holds external review findings with stable IDs (`F-…`, `N-…`, `M-…`).
   When you address one, record how in the plan and reference the ID in the commit message.
   You may also **refute** a finding — say so explicitly and explain why, rather than
   implementing a change you believe is wrong.
4. **The plan ships as a PDF too.** [`docs/IMPLEMENTATION_PLAN.pdf`](docs/IMPLEMENTATION_PLAN.pdf)
   is a rendering of the Markdown, committed alongside it because it is read outside a git
   checkout. It is a build product with a single source: **never edit the PDF, and never edit
   anything under `docs/paper/` to work around a problem in the text.** After any change to
   `IMPLEMENTATION_PLAN.md`, run `make pdf` and commit the regenerated PDF and its `.sha256`
   stamp in the *same* commit as the Markdown. `make pdf-check` — part of `make check` —
   compares the stamp against the current Markdown and fails when they have drifted, so a
   commit that updates only one of the two cannot pass. See
   [`.agents/paper.md`](.agents/paper.md).
5. **Do not state Proxmox behaviour you have not verified.** Read the PVE source, or ask the
   operator, or label the claim as unverified in the text. Forum threads from the PVE 6/7 era
   have repeatedly been wrong for 9.2. See [`.agents/domain-invariants.md`](.agents/domain-invariants.md).

---

## 8. Documentation we ship

Documentation is a deliverable, not a courtesy. Three audiences, three artefacts, and **every one
of them is generated from Markdown that lives in this repository** — nothing is authored directly
in PDF or in roff.

| Audience | Source | Generated |
|---|---|---|
| Whoever reads or changes the code | docstrings and comments, plus `docs/internals/*.md` | `docs/internals.pdf` |
| The operator who runs it | `docs/manual/*.md` | `docs/pve-storage-drs-manual.pdf`, `man/pve-storage-drs.1` |
| Somebody at a terminal, right now | the CLI's own option definitions | `pve-storage-drs --help`, `pve-storage-drs --manual` |

**Status:** all three pipelines exist. `docs/paper/` and `tools/build_paper.sh` are the one shared
pandoc+LuaLaTeX implementation behind `make pdf`, `make internals` and `make manual`
([`.agents/paper.md`](.agents/paper.md)); `make docs`/`make docs-check` build and verify all three
PDFs plus the manpage, and `docs-check` is part of `make check`. `docs/internals/*.md` and
`docs/manual/*.md` grow with the code: a phase that adds a module or a command adds the internals
page and manual section that describe it, in the same commit — they do not need to describe the
whole plan on day one, only what is actually built, and must say so honestly where it is not
(see `docs/manual/30-safety-and-status.md`'s per-command status table for the pattern).

### 8.1 Documentation inside the code

- Every module opens with a docstring saying what it does and **which plan section it implements**.
- Every public function and class: full type annotations, and a docstring that gives the units of
  every quantity, what it raises, and what it does *not* handle.
- Every non-obvious step carries a comment saying **why**, not what. "Why" includes the
  Proxmox behaviour or the plan constraint that forces the code into that shape.
- Docstrings are necessary and not sufficient: a reader must be able to understand the whole
  pipeline from `docs/internals/` **without** reading the source.

### 8.2 How the tool works: `docs/internals/`

The internals documentation explains the machine, in prose, to somebody who has to modify it. At
minimum it covers, each page naming the plan sections it expands and the modules it describes:

- the data path end to end — Prometheus and the PVE API in, load vector, gates, solver, plan,
  scheduler, executor, `state.json` out;
- the load model, and why average in-flight I/O rather than IOPS or bytes;
- the MILP: every variable, every constraint, the objective, and both solve paths;
- the heuristic fallback, and exactly where it may differ from the MILP;
- gating, hysteresis and cooldowns;
- migration cost and the payback rule;
- ordering and the transient invariant;
- the execution lifecycle — mirroring, draining, done — locks, and why a finished task is not a
  finished move;
- what is in `state.json`, who writes it, and how to recover from a crash mid-plan;
- failure modes, what the tool refuses to do, and why.

The plan describes the design **as specified**; `docs/internals/` describes the implementation
**as built**. When the two disagree, one of them is a bug — resolve it in the same commit, do not
leave the reader to guess which is current.

### 8.3 End-user documentation: `docs/manual/`

Written for an operator with a cluster to run and no interest in the solver's variables. It must
cover installation and requirements, mapping the metric names to their own Prometheus, the
verification commands, a first dry run and how to read the plan it prints, the three execution
modes, exit codes, troubleshooting, and the safety properties they are entitled to rely on
(dry-run default, the reserve is never traded, nothing is ever auto-deleted).

**Every configuration option is documented in full**: type, unit, default, what it interacts with,
what happens if it is set too high and too low. A knob that exists in the schema or in
`config/drs.example.yaml` but not in the manual is a bug, and so is the reverse.

### 8.4 The manpage: `man/pve-storage-drs.1`

Generated from `man/pve-storage-drs.1.md` with `pandoc -s -t man`. It is deliberately the short one — it
refers onward to the manual PDF for anything that needs more than a paragraph — with one
exception: **`OPTIONS` is complete**, because that is what people open a manpage for.

Sections, in this order: `NAME`, `SYNOPSIS`, `DESCRIPTION` (a few paragraphs, no theory),
`OPTIONS`, `CONFIGURATION` (the file's location and its top-level keys, then a pointer),
`FILES`, `EXIT STATUS`, `SEE ALSO`, `AUTHOR`, `COPYRIGHT`. It ships with the package and installs
to `share/man/man1`. It must never contradict the manual; when they disagree the manual wins and
the manpage is fixed.

### 8.5 `--help`

- `pve-storage-drs --help` prints a usage summary: every subcommand, every option, **with its default**.
  It is generated from the same argparse definitions the program runs on and the same constants
  the config loader uses, so it cannot drift from the behaviour.
- `pve-storage-drs <subcommand> --help` does the same for that subcommand.
- `pve-storage-drs --manual` (and `pve-storage-drs help`) shows the manpage: exec `man pve-storage-drs` when the page is installed and
  a pager makes sense, otherwise write the shipped plain-text rendering to stdout. Never answer
  with a URL alone — this runs on machines with no browser.

### 8.6 Keeping it all true

- `make docs` builds every artefact; `make docs-check` asserts that each committed artefact matches
  its Markdown by SHA-256 stamp, exactly as `make pdf-check` does, and is part of `make check`.
  Generated artefacts are committed for the same reason the plan's PDF is: they are read outside a
  checkout.
- Documentation changes in the **same commit** as the behaviour it describes. A pull request that
  changes a default and updates the manual later has shipped a lie in between.
- Tests, not good intentions, enforce the cross-references: every CLI option appears in the
  manpage's `OPTIONS` and in the manual; every config knob appears in the manual; every knob the
  manual documents exists in the schema.

Details: [`.agents/documentation.md`](.agents/documentation.md).

---

## 9. Dependencies, packaging and CI

The deployment target is Proxmox VE 9.x, which is Debian **trixie**. Everything below follows from
that one fact.

### 9.1 Debian first

**Prefer a module that trixie packages.** Not out of purism: a packaged module is one the operator
already trusts, already patches through their normal update path, and already has on a host with no
outbound network. Before adding a dependency, check it:

```sh
rmadison -s trixie python3-<name>
```

The order of preference, and there is no fourth option:

1. **In trixie** — add it to `debian/control` and to `pyproject.toml`, done.
2. **Not in trixie, pure Python, small** — vendor it into our source package, with its licence
   recorded in `debian/copyright` and its provenance and version in `.agents/packaging.md`.
3. **Not in trixie, and not vendorable** (a C extension, or simply too large — `ortools` is both) —
   it must be **optional**, imported where it is used and never at module level, with a code path
   that works without it. The autopkgtest of §9.2 is what enforces this.

### 9.2 The Debian package is a deliverable

`debian/` builds `pve-storage-drs`: the executable, the manpage, the example configuration and the
generated documentation. Three standing rules:

- **`debian/control` is the single source of truth for dependencies.** Build-Depends and Depends
  are updated in the *same commit* as the thing that needs them — a new Python import, a new
  document that needs a new tool, a new test that needs a new library. CI installs the build
  dependencies from `debian/control` with `mk-build-deps`, so a stale declaration fails there
  rather than silently working on a machine that happens to have the package.
- **Whenever documentation or a tool is added, the packaging is updated with it.** A new document
  goes into `debian/pve-storage-drs.docs`, a new manpage into `debian/pve-storage-drs.manpages`, a new example into
  `debian/pve-storage-drs.examples`, a new build step into `debian/rules`. A file that is generated but not
  installed is a file nobody will ever read.
- **The autopkgtest asks what the build cannot.** The build chroot has the Build-Depends installed
  and so cannot see a missing runtime dependency. `debian/tests` installs the package on a system
  carrying only its `Depends` and runs `pve-storage-drs --version`, `pve-storage-drs --help` and an import of every
  module in the package. Keep it that way: it is the test that catches an optional dependency
  imported at the top of a module.

`debian/changelog` and `pyproject.toml` must agree on the version; CI checks it.

### 9.3 Two pipelines

| | Where | What it proves |
|---|---|---|
| GitHub Actions | `debian:trixie` containers | The Debian-packaged toolchain is enough: lint, types, tests, coverage to Codecov, the document build against trixie's older pandoc, `dpkg-buildpackage`, lintian, and install-then-run |
| GitLab CI | Debian's Salsa pipeline (`debian/.gitlab-ci.yml`) | sbuild in an unshare chroot with **no network**, then lintian, piuparts, reprotest and autopkgtest |

CI installs its Python tooling **from apt, never from pip**. A CI that pip-installed its way around
a missing Debian package would hide the day §9.1 stopped being true, which is the only thing it is
there to detect. `make SYSTEM_TOOLS=1 <target>` is the switch that runs the ordinary targets against
the system toolchain.

The Salsa build has no network on purpose: that is what proves the package builds from trixie alone.
If a module genuinely has to be fetched during a build, vendor it (§9.1 rule 2). Setting
`SALSA_CI_SBUILD_ARGS: '--enable-network'` is the fallback, and it is a deliberate, reviewable edit
— never a default and never a quiet workaround.

Details: [`.agents/packaging.md`](.agents/packaging.md).

---

## 10. Review checklist

Before declaring anything done, walk [`.agents/review-checklist.md`](.agents/review-checklist.md).
