# The MILP backends: CP-SAT and CBC

**What does this page answer?** How does `optimize.py` turn section 5.3's
constraint set into a real CP-SAT/CBC model, why is the reserve solved in
two lexicographic stages rather than one big-M objective, and what does
`cli.py`'s backend dispatch actually do when a MILP solver is unavailable
or fails? Describes `proxmox_storage_drs/optimize.py`.

## Both backends solve, then hand off to `heuristic.evaluate_assignment()`

`solve()` builds a model, extracts the winning `x_{d,s}` assignment, and
immediately calls the *same* `heuristic.evaluate_assignment()` the
heuristic backend uses to produce the reported
`ObjectiveBreakdown` — one implementation of the section 5.4 objective,
shared by every backend (AGENTS.md section 5; `heuristic.py`'s own module
docstring was written anticipating exactly this: "built specifically so
`optimize.py` can call the identical function"). A modeling mistake in
this module can therefore make the solver choose a *suboptimal* assignment
at worst — it can never make the tool *believe* an assignment is better
than it is, since the number that ends up in `plan`'s output is never this
module's own objective value.

## Lexicographic, not big-M — and why that is the only mode implemented

Section 5.3 describes two ways to keep a reserve violation from being
"traded away" by a large enough balance gain: a single-stage objective
with a calibrated penalty `P` (big-M), or a two-stage **lexicographic**
solve — minimize `Σ_s r_s` alone first, then fix that total as a hard
constraint and minimize the real objective. `optimize.py` implements only
the second, both because the plan itself says to ("use the lexicographic
solve by default... needs no calibration, its correctness does not depend
on `T_g`") and because there is no `solver.*` config knob that ever
selects big-M at runtime — it exists in the plan text to be *compared
against* the lexicographic solve, a comparison
`tests/fixtures/generate_expected.py` already does by exhaustive
enumeration on `reserve-tradeoff.yaml`, not something this module needs a
second code path for. `Σ r_s > 0` in a lexicographic result provably means
*no* assignment could do better, at any weight — never merely
"unattractive".

## CP-SAT: section 5.5's exact integer scaling

Every coefficient is folded and rounded exactly as section 5.5 specifies:

- `_LOAD_SCALE` (`K = 10⁶`) scales every load-valued quantity (`e_s`, `t`,
  `u*`). (C6)'s per-(disk, storage) coefficient is `a_{d,s} = round(K ·
  ℓ_d / c_s)` — folded and rounded *once*, per the plan's own warning
  against computing `round(K/c_s)` and multiplying separately (which
  rounds the capability weight itself and would make CP-SAT and CBC
  disagree for a non-integer `c_s`).
- `_WEIGHT_SCALE` (`W = 10⁴`) scales every objective weight
  (`α`/`β`/`γ`/`κ`). The `γ` term folds `z_d` into its own coefficient
  (`round(γ·W·K·z_d^TiB)`) rather than factoring out a standalone
  `γ_scaled = round(γ·K/2²⁰)` — the plan's own worked example of *why*
  that shortcut is wrong: at the default `γ = 0.05/TiB`, it rounds to
  zero and CP-SAT would silently stop caring about disk size when
  choosing what to move.
- Every size-valued quantity (`Z_s`, `R_s`, `r_s`, `z_d`, `C_s`,
  `Uˢᵉˣᵗ`, `min_free_bytes`) is a whole-MiB integer (`_mib()`), already
  exact, needing no scale of its own.
- `_RESERVE_FACTOR_SCALE` is this module's own addition, not named in the
  plan: (C5)'s `R_s ≥ f_s·Z_s` multiplies a *variable* (`Z_s`) by
  `reserve_factor`, which section 5.5's "fold constants into a
  coefficient" recipe does not directly cover (that recipe is for a
  constant multiplying a *binary* decision variable). Expressed instead
  as `SCALE·R_s ≥ round(f_s·SCALE)·Z_s` with `SCALE = 10⁶` — a single
  linear constraint, correct to within `1/SCALE` MiB, utterly negligible
  next to any real disk size.

`AddHint(x[d, σ₀(d)], 1)` warm-starts every candidate from the current
assignment, in both stages (harmless when unused, and stage 1's own
optimum is frequently "keep everyone where they are" when nothing already
violates (C5)).

## CBC: "direct transcription", deliberately not scaled

The plan's own words for this backend: "continuous `e_s`, `Z_s`, `r_s` are
fine." `_cbc_feasibility_constraints()`/`_cbc_objective_terms()` write the
identical constraints CP-SAT does, but with plain floats and PuLP's
`prob.add_variable(...)` (not the older `pulp.LpVariable(...)` constructor
PuLP's own v4 migration deprecates) — no `_LOAD_SCALE`/`_WEIGHT_SCALE`
anywhere, because CBC needs none of CP-SAT's integer-coefficient
discipline. `solver.mip_gap` and `solver.time_limit_seconds` map onto
`pulp.COIN_CMD(gapRel=..., timeLimit=...)` directly.

## `(C1)`/`(C3)`/`(C4)`/`(C5)` are shared code, factored once per backend

`_cpsat_feasibility_constraints()`/`_cbc_feasibility_constraints()` build
exactly the constraints both lexicographic stages need identically — only
the *objective* differs between stage 1 (`Minimize(Σ r_s)`) and stage 2
(the real section 5.4 objective, with `Σ r_s` fixed to stage 1's result as
a hard constraint). Each is called twice, with fresh variables each time,
rather than trying to mutate one model's objective in place — simpler to
reason about than partial reuse, at the cost of building the constraint
set twice per solve (irrelevant next to a MILP solve's own running time).

(C3)'s `y_{v,s}` linking honors `objective.affinity_counts_pinned_disks`
exactly as the plan's own text describes it: **false** (default) links
`y` to `x` over `D^mov` only, so a pinned disk never forces `y_{v,s}=1`
for its storage; **true** ranges the constraint over all of `D`, which
this module implements as forcing `y_{v,s}=1` outright wherever a pinned
disk of `v` already sits (the natural reading of "`x_{d,s} ≤ y_{v,s}`
for `d ∈ D`" when `x_{d,σ₀(d)}` is a constant `1`, not a variable, for a
pinned disk).

## `cli.py`'s dispatch: `auto` cascades, an explicit backend still falls back

`cli._solve_group()` implements `solver.backend`'s four values:
`"auto"` tries `cpsat` then `cbc`; `"cpsat"`/`"cbc"` try only that one;
`"heuristic"` skips `optimize.solve()` entirely. Whichever backend
`solve()` cannot use (library not importable, or no feasible solution
within `solver.time_limit_seconds`) returns `None` — never an exception —
and `_solve_group()` moves to the next one in the cascade, ending at
`heuristic.run_heuristic()` if every MILP attempt failed. This applies
**even to an explicitly forced backend**: section 13's failure-mode table
says "solver infeasible or timing out -> fall back to the heuristic;
never emit a partial/unvalidated assignment", with no carve-out for
`solver.backend: cpsat` specifically. The one difference: falling back
from an *explicit* backend logs a warning (an operator who named `cpsat`
to reproduce a specific result should not have to diff `--json` output to
notice `auto` quietly ran instead); falling back within `auto` itself is
expected and silent. `plan`'s human and `--json` output both report which
backend actually produced each group's plan (`solver: cpsat (optimal)` /
`"solver_backend": "cpsat", "solver_status": "optimal"`), precisely so
that distinction is never hidden.

## Deliberately not implemented in this pass

- **The storage cooldown is not enforced by either MILP model.**
  `solve()` accepts `cooldown_storages` for interface symmetry with
  `heuristic.run_heuristic()`, but hard-fixing `x_{d,s}=0` for a cooldown
  storage inside stage 2 — after stage 1 has already fixed the *value* of
  `Σ r_s`, not the specific assignment that achieves it — can make stage
  2 infeasible in a case the heuristic's sequential repair-then-descend
  never hits, because descend only ever *extends* repair's assignment
  rather than jointly re-deriving it against a competing hard constraint.
  `solve()` logs a warning whenever it is called with a non-empty
  `cooldown_storages`, so this is loud, not silent, the day
  `state.json`'s cooldowns stop being permanently empty (nothing calls
  `state.with_recorded_cooldown()` yet — see `docs/internals/15-state.md`).
- **(C2) format-compatibility eligibility** — the same gap `heuristic.py`
  already documents (`topology.Storage` does not expose storage
  type/format).
- **A live cluster's numpy/pandas footprint.** `ortools` pulls in numpy
  (and numpy pulls in nothing further this project cares about) purely as
  its own transitive dependency; nothing in this project imports numpy
  directly. A recent numpy's bundled type stubs use syntax newer than this
  project's `python_version = "3.11"` mypy target, which `mypy`'s
  `follow_imports = "skip"` (used for `ortools.*` itself) cannot rescue,
  because a stub-level *parse* error happens before mypy ever gets to
  apply a per-module setting to it. This surfaces only if `ortools` (via
  `pip install -e .[solver]`) or `statsmodels`'s own `[forecast]` extra
  happens to pull in an affected numpy version into the *same* venv
  `make typecheck` runs against — `make install`'s own `.[dev]` never
  does, so it does not affect this project's actual gate. Both MILP
  backends were still verified for real during development (`pip install
  -e .[solver]`, all of `test_optimize.py` passing and reproducing the
  section 14 and `reserve-tradeoff.yaml` fixtures' exact numbers for both
  CP-SAT and CBC) — see `tests/unit/test_optimize.py`'s own docstring.
