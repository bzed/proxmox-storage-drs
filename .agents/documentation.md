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
  pve-storage-drs-manual.pdf       built from docs/manual/*.md
man/
  pve-storage-drs.1.md             source
  pve-storage-drs.1                built with pandoc -s -t man; installed to share/man/man1
config/
  drs.example.yaml                 the reference configuration; installed as an example
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
pandoc man/pve-storage-drs.1.md --standalone --to=man --output=man/pve-storage-drs.1
```

with the metadata block at the top of `pve-storage-drs.1.md` supplying the title, section, date and footer.

## Self-contained

[`../AGENTS.md`](../AGENTS.md) section 8.0 is the rule: the manual, `docs/internals/`, the manpage,
`--help` and `config/drs.example.yaml` never send a reader to `IMPLEMENTATION_PLAN.md` for
something they needed. The plan ships beside them in `/usr/share/doc/pve-storage-drs/`, and that is
precisely why this is easy to get wrong — the reference *works*, it looks like diligence, and the
reader still ends up alone in a specification hunting for one number.

The check, applied per sentence while editing: **delete the plan reference and re-read what is
left.** Still answers the question → it was a footnote, keep it. Now has a hole in it → the hole is
the sentence you owe the reader.

Before — a deferral wearing a citation:

> Cost and benefit are compared as described in `IMPLEMENTATION_PLAN.md` section 7.2.

After — the same paragraph, self-contained, with the citation demoted to what it actually is:

> A move is rejected unless `benefit > payback_ratio * cost` (default ratio: `10.0`). Both sides are
> in **load-seconds** — average in-flight I/O requests multiplied by seconds — which is what makes
> the comparison meaningful. Cost is the extra in-flight I/O the migration itself imposes:
> `source_load_weight` on the source and `target_load_weight` on the target for the mirror, which
> takes `disk_bytes / bwlimit_bytes_per_sec` seconds, plus — when `account_saferemove_wipe` is on
> and the source storage has `saferemove` set — `wipe_load_weight` on the source for as long as the
> old volume takes to be zeroed. Benefit is the improvement the plan buys in imbalance, in data
> spread and in VM affinity, each weighted as in the objective, held for `payback_horizon`
> (default `365d`). (Derived in `IMPLEMENTATION_PLAN.md` section 7.2.)

Longer, and that is the point: the second one can be read at 03:00 by somebody deciding whether to
raise `payback_ratio`.

Two things this rule does **not** say:

- Cross-references between the shipped artefacts are fine and encouraged — the manual sends a reader
  to the internals PDF for theory, the manpage sends them to the manual. They ship together, and
  each is written for a reader who has the others.
- Saying the same thing as the plan is not the duplication we avoid. That rule is for facts with a
  single generator — options, defaults, built artefacts — where a second copy goes stale silently.
  Prose written for the operator and prose written for the implementer are two texts, and they are
  *supposed* to drift in wording.

## Writing the reference configuration

`config/drs.example.yaml` is documentation that happens to parse. It is installed as an example,
it is what most operators copy to `/etc/pve/drs.yaml`, and its comments are frequently the only
thing they read before running the tool.

- Every value shown is the default, or is marked `REQUIRED`. Anything else teaches a wrong default.
- A comment says the **unit**, what the knob trades against, and what goes wrong at each extreme —
  the manual entry's five points, compressed to the two or three lines a config file can carry.
- Self-contained like everything else (section 8.0): no "see the plan for the semantics". If the
  semantics need a paragraph, write the paragraph here and say the rest is in the manual — that is
  a shipped artefact and a fair place to send the reader.
- It validates against the schema (`test_example_config_valid`), and every knob in it appears in
  the manual and in the schema. Add a knob in all three places in one commit, or in none.

## Writing the internals documentation

The audience has to change the code and is entitled to understand why it is shaped as it is.

- Start each page with the question it answers, then the answer. No preamble.
- Name the modules the page describes (`proxmox_storage_drs/solver/milp.py`) — that is what makes it
  maintainable — and, if you like, close the page with the plan sections it expands. The plan
  reference is a footnote, never the explanation: see *Self-contained* below.
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
- Say what is safe. Dry-run is the default, the reserve is never traded for balance, the free
  space the operator configured is held to the same standard (and `free_space.hard` is never
  crossed, not even mid-move), nothing is ever deleted automatically — an operator who does not
  know that will not run the tool at all.
- Cross-reference the internals PDF for theory rather than half-explaining it.

Every configuration option gets an entry of this shape:

```markdown
### `gates.drift_threshold`

Fraction, default `0.10`, dimensionless.

Replanning is skipped until the load vector has moved by this much in L1 relative to the vector
recorded at the last balance. Lower values react sooner and migrate more; higher values ride out
daily variation. Below roughly 0.05 the tool will chase noise on a busy cluster.

Interacts with `gates.imbalance_threshold` below: drift decides *whether to look*, imbalance decides
*whether to act*.
```

Type, default, unit, what it does, what happens at each extreme, what it interacts with. All five.

## Writing the manpage

Short on purpose — it refers onward — except `OPTIONS`, which is complete. Skeleton:

```markdown
% PVE-STORAGE-DRS(1) pve-storage-drs VERSION | Proxmox Storage DRS
% Bernd Zeimetz
% BUILD DATE

# NAME
pve-storage-drs - balance disk I/O across Proxmox VE shared storages

# SYNOPSIS
**pve-storage-drs** [*global options*] *command* [*command options*]

# DESCRIPTION
Three or four paragraphs. What it does, what it will never do without being asked, where the
configuration lives.  No theory.

# OPTIONS
Every global option and every subcommand option, with defaults.

# CONFIGURATION
Where the file lives, its top-level keys, one line each, then: "see pve-storage-drs-manual.pdf".

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
- `pve-storage-drs --manual` and `pve-storage-drs help`: `exec man pve-storage-drs` when the page is installed and stdout is a tty;
  otherwise write the shipped plain-text rendering to stdout so it pipes and greps. A URL is not an
  answer — these machines may have no browser.
- `pve-storage-drs --help` must fit the "what can this thing do" question in one screen per subcommand. Detail
  belongs in the manual.

## The tests that keep it honest

Documentation rots silently, so it is tested like code:

| Test | Asserts |
|---|---|
| `test_help_covers_options` | every argparse option appears in `man/pve-storage-drs.1.md` under `OPTIONS` |
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
