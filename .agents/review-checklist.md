# Before you say "done"

Walk this list. It is short on purpose.

## Mechanical

- [ ] `make check` is green (format, lint, types, tests, coverage ≥ 85 %, fixture freshness).
- [ ] New files carry the SPDX header with `Bernd Zeimetz <bernd@bzed.de>`.
- [ ] No secrets, no `config/drs.yaml`, no `state.json`, no `.venv/` in the diff
      (`git status --short` and `git diff --cached --stat` both clean of them).
- [ ] `.flake8` and `pyproject.toml` still agree on line length.

## Substantive

- [ ] Every new public function has a type annotation and a docstring naming the plan section
      it implements.
- [ ] Every number in a signature carries its unit in the name.
- [ ] The rule you implemented exists in exactly **one** place; the MILP and heuristic paths
      call the same predicate.
- [ ] The safety invariants in [`domain-invariants.md`](domain-invariants.md) still hold —
      in particular: dry-run default, reserve never traded, invariant checked during moves,
      no auto-delete.
- [ ] Any claim about Proxmox behaviour in the diff is either verified against the source /
      the operator, or explicitly labelled unverified.

## Documentation

- [ ] `IMPLEMENTATION_PLAN.md` updated in the **same commit** if behaviour changed.
- [ ] §15 traceability and §15.1 knob→formula tables still complete.
- [ ] `config/drs.example.yaml` carries any new knob, with a comment explaining what happens
      at the default and what happens if you get it wrong.
- [ ] If this addressed a `REVIEW.md` finding, the finding ID is in the commit message, and
      findings you **refuted** rather than fixed say so and why.

## Honesty

- [ ] The commit message describes what actually happened, including what you did not finish.
- [ ] Tests that fail are reported as failing, with the output — never summarised as "mostly
      passing".
