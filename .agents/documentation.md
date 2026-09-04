# Documentation

[`../AGENTS.md`](../AGENTS.md) section 8 is the normative short version. This file is the how.

The rule behind all of it: **every artefact is generated from Markdown in this repository.**
Nobody edits a PDF, nobody hand-writes roff, and nobody writes a second copy of something that
already exists in the code. When a fact lives in two places, one of them is stale — the only
question is which.

## Layout

```
docs/
  paper/                 shared pandoc + LaTeX machinery (see paper.md)
  internals/             how the tool works, for whoever changes it
    01-data-path.md          Prometheus + PVE API in, plan out
    02-load-model.md         ...one file per topic, numbered for reading order
  manual/                how to run it, for the operator
    01-installation.md
    02-configuration.md      every knob, in full
    ...
  IMPLEMENTATION_PLAN.pdf  the specification, built from ../IMPLEMENTATION_PLAN.md
  internals.pdf            built from docs/internals/*.md
  drs-manual.pdf           built from docs/manual/*.md
man/
  drs.1.md               source
  drs.1                   built with pandoc -s -t man; installed to share/man/man1
```

Multi-file sources are concatenated in filename order, which is why the files are numbered. Keep
the numbers sparse (10, 20, 30) if you expect to insert.

## Building

`make docs` builds everything; `make docs-check` fails when a committed artefact does not match its
Markdown, and runs as part of `make check`. Freshness works exactly as it does for the plan — a
SHA-256 of the *sources*, stored next to the artefact — and for the same reason: mtimes do not
survive a clone. [`paper.md`](paper.md) explains the mechanism and the traps in the PDF pipeline
(the Unicode fallback chain, the log checker, reproducible builds); all of it applies here, because
these documents use the same `docs/paper/` machinery.

The manpage build is the one different invocation:

```sh
pandoc man/drs.1.md --standalone --to=man --output=man/drs.1
```

with the metadata block at the top of `drs.1.md` supplying the title, section, date and footer.

## Writing the internals documentation

The audience has to change the code and is entitled to understand why it is shaped as it is.

- Start each page with the question it answers, then the answer. No preamble.
- Name the plan sections it expands (`§7.3`) and the modules it describes (`drs/solver/milp.py`).
  Those two references are what make the page maintainable.
- Explain the **why**. That the scheduler re-reads the VM's node before every move is visible in
  the code; that it does so because the PVE Dynamic Load Balancer may have moved the VM mid-plan
  is not.
- Diagrams as ASCII in a fenced block. They survive review, diff and the PDF build.
- Worked numbers beat prose for anything with arithmetic in it. The plan's §14 is the model.
- If you find yourself describing behaviour you have not verified, stop and read the source or ask
  the operator — [`domain-invariants.md`](domain-invariants.md) exists because that has gone wrong
  before.

## Writing the manual

The audience has a cluster to run and no interest in the solver's variables.

- Second person, imperative, present tense. "Set `window` to the period you want balanced."
- Every section starts from something the operator wants to achieve, not from a feature.
- Show the command and its real output. Invented output is worse than none.
- Say what is safe. Dry-run is the default, the reserve is never traded for balance, nothing is
  ever deleted automatically — an operator who does not know that will not run the tool at all.
- Cross-reference the internals PDF for theory rather than half-explaining it.

Every configuration option gets an entry of this shape:

```markdown
### `gates.drift_threshold`

Fraction, default `0.10`, dimensionless.

Replanning is skipped until the load vector has moved by this much in L1 relative to the vector
recorded at the last balance. Lower values react sooner and migrate more; higher values ride out
daily variation. Below roughly 0.05 the tool will chase noise on a busy cluster.

Interacts with `gates.imbalance_threshold` (§6): drift decides *whether to look*, imbalance decides
*whether to act*.
```

Type, default, unit, what it does, what happens at each extreme, what it interacts with. All five.

## Writing the manpage

Short on purpose — it refers onward — except `OPTIONS`, which is complete. Skeleton:

```markdown
% DRS(1) drs VERSION | Proxmox Storage DRS
% Bernd Zeimetz
% BUILD DATE

# NAME
drs - balance disk I/O across Proxmox VE shared storages

# SYNOPSIS
**drs** [*global options*] *command* [*command options*]

# DESCRIPTION
Three or four paragraphs. What it does, what it will never do without being asked, where the
configuration lives.  No theory.

# OPTIONS
Every global option and every subcommand option, with defaults.

# CONFIGURATION
Where the file lives, its top-level keys, one line each, then: "see drs-manual.pdf".

# FILES
# EXIT STATUS
# SEE ALSO
# AUTHOR
# COPYRIGHT
```

`VERSION` and `BUILD DATE` are substituted by the build, not typed by hand.

## `--help`

- Generated from the argparse definitions the program actually runs on. Never a second, hand-kept
  list of options.
- Defaults printed in help come from the same constants the config loader reads, so
  `--help` cannot claim a default the code does not use. `argparse.ArgumentDefaultsHelpFormatter`
  plus real default values in `add_argument` is enough; a hardcoded default in a help string is a
  bug.
- Every option's help text says the **unit**.
- `drs --manual` and `drs help`: `exec man drs` when the page is installed and stdout is a tty;
  otherwise write the shipped plain-text rendering to stdout so it pipes and greps. A URL is not an
  answer — these machines may have no browser.
- `drs --help` must fit the "what can this thing do" question in one screen per subcommand. Detail
  belongs in the manual.

## The tests that keep it honest

Documentation rots silently, so it is tested like code:

| Test | Asserts |
|---|---|
| `test_help_covers_options` | every argparse option appears in `man/drs.1.md` under `OPTIONS` |
| `test_manual_covers_config` | every key in the config schema appears in `docs/manual/` |
| `test_config_covers_manual` | every key the manual documents exists in the schema |
| `test_example_config_valid` | `config/drs.example.yaml` validates against the schema |
| `make docs-check` | every committed PDF and manpage matches its Markdown |

These are cheap, they run in the normal suite, and they are the reason nobody has to remember any
of the rules above.

## When you change behaviour

In the same commit: the code, the plan section that specifies it, the internals page that explains
it, the manual entry that documents it, the manpage if an option changed, and the regenerated
artefacts. If that feels like a lot, it is the honest cost of the change — splitting it across
commits does not reduce the work, it just ships a lie in the middle.
