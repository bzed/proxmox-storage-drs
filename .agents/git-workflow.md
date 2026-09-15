# Git workflow

## Branches

| Prefix | For |
|---|---|
| `feat/` | new capability |
| `fix/` | bug fix |
| `chore/` | tooling, packaging, housekeeping |
| `docs/` | plan/README/agent-instruction changes only |
| `review/` | addressing a batch of `REVIEW.md` findings |
| `release/` | a version bump — see "Releases" below |

**Decide before you touch a file, not after looking at the diff.** The failure mode this
guards against is a string of small, individually-reasonable-looking commits landing straight
on `main` because each one, in isolation, felt too small to bother branching for. It adds up to
exactly the un-reviewable history that branches exist to prevent. So the test is mechanical,
not a judgment call:

- Touches one file, one line, no code/test/spec content (a comment typo, a dead link, a
  one-word doc correction) → `main` directly is fine.
- Anything else — multiple files, any line of `src/`, `tests/`, `debian/`, or
  `IMPLEMENTATION_PLAN.md`, even a "small" one — gets a branch, created with
  `git checkout -b <prefix>/<slug>` **before** the first edit.

If you're not sure which bucket a change falls into, it's the second one. A branch you didn't
strictly need costs a `git checkout main && git branch -d`; a multi-file change committed
straight to `main` costs a rewritten history to undo, which this repo does not do
([`AGENTS.md`](../AGENTS.md) §4, never rewrite history past a pushed commit). Cheap-if-wrong
beats expensive-if-wrong.

## Commit cadence

Commit often. The target is a sequence of commits that each leave the tree in a state you can
describe in one line — not one heroic commit at the end. On a feature branch a work-in-progress
commit that does not pass `make check` is acceptable and often correct; say `WIP:` in the
subject and describe what is broken in the body. On `main` it never is.

Message shape:

```
Short imperative subject, no trailing period, <= 72 chars

Why this change exists. What it does that is not obvious from the diff.
Which REVIEW.md findings it addresses (M-03, M-04) or which plan section it
implements (§8.2).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

The `Co-Authored-By` trailer goes on commits an agent wrote. Attribution and copyright are
separate things — the copyright holder stays `Bernd Zeimetz <bernd@bzed.de>` regardless of who
typed the diff.

## Merging

```sh
make check          # must be green on the branch tip
git checkout main
git merge --no-ff <branch>
```

`--no-ff` keeps the branch visible in history, which matters when a branch corresponds to a
batch of review findings. Delete the branch after merging.

`main` is always green. If a merge breaks it, fix forward immediately or revert the merge —
do not leave it red while investigating.

## Releases

A version bump is not just an edit to `pyproject.toml` — see AGENTS.md §9.2 for the three things
that must land together (version files, a `debian/changelog` entry, a git tag) and never one
without the others. Mechanically:

```sh
make check                                   # must be green before tagging anything
git tag -a debian/<version> -m "pve-storage-drs <version>"
```

The tag is annotated (`-a`), named `debian/<version>` to match this repo's existing tags
(`git tag -l`), and created on the commit that lands the version bump once it is on `main` — not
on a `release/*` branch tip before it merges. Push tags explicitly (`git push --tags` or
`git push origin <tag>`); a plain `git push` does not push tags.

## Delegating to a subagent

Long or parallelisable work (a batch of independent review findings, a module with a large test
surface) can go to a subagent. Rules:

1. The subagent works **on its own branch**, or in its own git worktree if it runs concurrently
   with other work. Two agents on one branch will clobber each other.
2. The subagent runs `make check` itself and reports the result honestly, including failures.
3. The **merge to `main` is the parent's decision.** A subagent does not merge.
4. The subagent gets the same instructions: this directory and `AGENTS.md` apply to it too.

## Never commit

`config/drs.yaml` (contains the PVE password), `state.json`, `.env`, `.claude/`, `.venv/`,
`.coverage`, `htmlcov/`, `docs/.build/`. They are in `.gitignore`. Adding a `!` exception for any
of them is a stop-and-ask moment.

The one deliberate exception to "do not commit build products" is
`docs/IMPLEMENTATION_PLAN.pdf`: it is a deliverable, it is read outside a checkout, and
`make pdf-check` makes a stale copy impossible to commit. See [`paper.md`](paper.md).

Before a first push to a remote, check for secrets in the *history*, not just the worktree.
