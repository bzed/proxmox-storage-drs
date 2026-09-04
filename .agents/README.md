# `.agents/` — detailed working instructions

[`../AGENTS.md`](../AGENTS.md) is the entry point and the normative short version. These files
expand on it. They are written for an agent that has just been dropped into this repository
with no memory of previous sessions.

| File | Covers |
|---|---|
| [`python-style.md`](python-style.md) | Formatting, typing, module conventions, why the flake8/black config looks like it does |
| [`testing.md`](testing.md) | Test layout, the 85 % coverage floor, fixtures, what must never be tested over the network |
| [`git-workflow.md`](git-workflow.md) | Branching, commit cadence, merge criteria, subagent/worktree delegation |
| [`domain-invariants.md`](domain-invariants.md) | The safety rules that come from moving live VM disks, and the "do not assert unverified PVE behaviour" rule |
| [`review-checklist.md`](review-checklist.md) | The list to walk before saying "done" |

Read `python-style.md` and `testing.md` before writing code, `domain-invariants.md` before
touching the solver, scheduler or executor, and `git-workflow.md` before your first commit.
