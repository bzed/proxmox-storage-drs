# Testing

## The floor

**85 % line coverage, enforced.** `pyproject.toml` sets `--cov-fail-under=85`; `make test`
fails below it. Raising the floor as the project matures is encouraged; lowering it needs a
reason in the commit message.

Coverage is a smoke detector, not a fire suppression system. Two rules keep it honest:

1. Every test asserts something about behaviour. A test that imports a module and calls a
   function without checking the result buys coverage and hides a gap — that is worse than
   having no test, because the number says you are covered.
2. `# pragma: no cover` is allowed only on genuinely unreachable defensive branches, and each
   use carries a comment saying why.

## Higher bar for the safety-critical modules

These carry the invariants that stop the tool from filling a SAN LUN or corrupting a running
VM's disk. They get **branch** coverage and an explicit test per documented edge case in the
plan:

| Module | Plan section | Must be tested to the edges |
|---|---|---|
| reserve / capacity constraint | §5.3 (C4), (C5) | `min_free_bytes` floor vs `f·Z`; already-violating start; `r_s > 0` reporting |
| transient invariant | §8.1 | single move; concurrent set `M`; incoming disk becomes the new largest |
| scheduling / ordering | §8.2, §8.3 | priority exceptions; deadlock; staging; `draining` accounting |
| payback | §7 | accept, reject, the saferemove wipe term, `max_single_move_duration` |
| locks and drain | §9.3 | lock present → wait; timeout → skip; task OK but volume still present |
| gates | §6 | first run; `‖ℓ_last‖₁ = 0`; disks appeared/disappeared |

## Layout

```
tests/
  unit/            one file per module, pure functions, no I/O
  integration/     pipeline slices wired together against recorded fixtures
  fixtures/        input data and expected results
```

`pytest-xdist` is available; per-group tests are independent and parallelise cleanly.

## The acceptance fixture

`tests/fixtures/fc-tier1.yaml` is `IMPLEMENTATION_PLAN.md` §14 in machine-readable form.
`fc-tier1.expected.json` holds the proven-optimal results — **generated, never hand-written**:

```sh
python3 tests/fixtures/generate_expected.py           # regenerate
python3 tests/fixtures/generate_expected.py --check   # assert it is current (CI, make check)
```

The generator solves by exhaustive enumeration of all |S|^|D| assignments, so the recorded
optimum is proven rather than hand-worked. It covers both the single-stage big-M solve and the
lexicographic two-stage solve, and records the threshold `P` at which the two agree.

`reserve-tradeoff.yaml` is the second fixture and exists because `fc-tier1` cannot fail the way
that matters: there, every reserve-violating assignment is *also* worse on balance, so the two
solve paths agree at any penalty. `reserve-tradeoff` puts them in genuine conflict — the
lexicographic solve leaves the group maximally imbalanced rather than breach the reserve by 1 TiB,
big-M with the configured `P = 1000` agrees, and big-M with `P = 5` moves the disk and produces a
plan the scheduler then refuses to order. Test the lexicographic path against that one.

If a change makes the expected file stale, that is a signal — read the diff before regenerating.
A change in those numbers means the model changed.

**Round once, at the point of writing.** Never derive a value from an already-rounded record.
The generator rounds to six decimals for the file; feeding one of those rounded values back into
a later computation (`benefit = (E_before − E_after) · H` taken from the rounded `E_after`) shifts
the result off the plan's prose by a fraction that is too small to notice and too annoying to
explain. Keep the exact value in a private field and round it on output.

## What must never happen in a test

- No network. Not to the PVE API, not to Prometheus, not to a package index.
- No writes outside `tmp_path`. Never to `state.json`, never to `config/`.
- No `time.sleep` for real durations; inject the clock.
- No test that depends on dict ordering, set iteration order, or filesystem ordering. The
  solver has ties; break them deterministically in the code and assert the deterministic result.
