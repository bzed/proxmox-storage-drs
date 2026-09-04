# The PDF rendering of the plan

`IMPLEMENTATION_PLAN.md` is the source of truth. `docs/IMPLEMENTATION_PLAN.pdf` is a rendering of
it, committed to the repository so that the specification can be handed to somebody who does not
have a git checkout — a reviewer, an operator, an implementer working from a printout.

**The PDF is a build product. Never edit it, and never let it drift.**

```sh
make pdf         # rebuild docs/IMPLEMENTATION_PLAN.pdf from the Markdown
make pdf-check   # fail if the committed PDF was built from a different Markdown
```

## How staleness is prevented

`make pdf` writes `docs/IMPLEMENTATION_PLAN.pdf.sha256`, the SHA-256 of the **Markdown** the PDF
was built from. `make pdf-check` re-hashes the Markdown and compares. It is part of `make check`,
so the ordinary pre-commit loop already refuses a commit that changes the plan without rebuilding
the PDF. The `paper-current` hook in `.pre-commit-config.yaml` does the rebuild automatically for
anyone who ran `pre-commit install`.

A hash rather than file mtimes, because mtimes do not survive a clone: a fresh checkout has every
file stamped with the checkout time, in arbitrary order.

The same hash is printed on the title page, so a reader holding only the PDF can run
`sha256sum IMPLEMENTATION_PLAN.md` and prove the two are the same document.

`pdf-check` degrades to a warning when `pandoc` or `lualatex` are absent, so the repository stays
usable on a machine without the document toolchain. It never degrades to a warning when the
toolchain *is* present.

## What is where

| File | Role |
|---|---|
| `docs/paper/metadata.yaml` | Title, author, page geometry, fonts sizes — everything static that pandoc reads as metadata |
| `docs/paper/header.tex` | LaTeX preamble: fonts and the Unicode fallback chain, running heads, title page, code-block and table styling |
| `docs/paper/filters.lua` | Pandoc filters: drop the document's own H1, drive the running head, box the unlabelled code fences |
| `tools/check_paper_log.py` | Turns silent LaTeX warnings into a failed build |
| `docs/.build/` | Intermediates (`plan.tex`, `plan.log`); git-ignored, safe to delete |

## Things that will bite you

**Unicode.** The plan uses ℓ Σ ω ≤ ⟺ ∈ ∀, box-drawing characters, block elements and
sub/superscripts. No single well-shaped text font covers all of that, so `header.tex` installs a
luaotfload fallback chain ending in DejaVu Sans (`fonts-dejavu-core`), which does cover every
codepoint the document currently uses, with Symbola (`fonts-symbola`) behind it. The body font is
Gentium Book Plus (`fonts-sil-gentiumplus`). lualatex reports an uncovered glyph as a `Missing
character` **warning** and still exits 0 — a formula would silently lose a symbol. That is why
`tools/check_paper_log.py` exists and why it fails the build.

**Wide code blocks.** The widest line in the plan is 103 characters. The mono font is scaled so
that this fits; `fvextra` breaks anything longer rather than letting it run off the page. Overfull
boxes wider than 2 pt also fail the build, so a new very wide block gets noticed rather than
quietly overflowing into the margin.

**Reproducibility.** `SOURCE_DATE_EPOCH` is pinned to the commit date of the plan (or now, if the
plan has uncommitted changes), so rebuilding unchanged content produces a byte-identical PDF and
the committed binary does not churn.

**Do not fix the text from the LaTeX side.** If a table is too wide or a heading reads badly, the
answer is almost always to change `IMPLEMENTATION_PLAN.md`, which is what everyone actually reads.
`header.tex` is for typography that applies to the whole document.
