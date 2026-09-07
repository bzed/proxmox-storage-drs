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

**That proof depends on stage 1 actually being solved to proven
optimality, not merely to `solver.mip_gap`** (REVIEW.md S-07). An earlier
revision applied the same `mip_gap` to both stages: CP-SAT's stage 1
accepted `FEASIBLE` (an incumbent, not a proven minimum) whenever the gap
was satisfied, and PuLP's own `LpStatus` string is `"Optimal"` whether
CBC proved the bound or merely stopped because `gapRel` was satisfied --
either way, stage 2 then pinned `Σ r_s` to that unproven incumbent
(`==`), which can both accept a shortfall up to the gap *and* forbid
finding less of it. Fixed by forcing stage 1's own gap to `0` in both
backends regardless of the configured `solver.mip_gap` (which now applies
to stage 2's real objective alone), requiring CP-SAT's stage 1 status to
be exactly `OPTIMAL` (never `FEASIBLE`), and changing stage 2's slack
constraint from `==` to `<=` in both backends -- monotone-safe (stage 2
can never do worse than the now-proven stage-1 value) rather than brittle
against a hypothetical disagreement between the two solves. Cheap in
practice: stage 1 is a near-feasibility problem that closes instantly on
realistic groups, so forcing an exact proof costs nothing measurable.

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

Section 5.5 also asks for two build-time assertions guarding this
folding, and `_cpsat_objective_terms()` now has both (REVIEW.md S-09):
`_assert_nonzero_when_weighted()` catches exactly the `γ` trap the
paragraph above describes — a non-zero configured weight whose *rounded*
coefficient collapsed to `0` (only ever a sub-kilobyte disk at the
default `γ`, per `test_gamma_trap_assertion_fires_end_to_end_for_a_sub_kilobyte_disk`)
— and `_assert_objective_magnitude_within_int64()` checks a coarse,
deliberately conservative worst-case sum of every term against `2⁶²`,
an order of magnitude under CP-SAT's own `2⁶³-1` domain limit. Neither
applies to CBC, whose continuous, unscaled model has no analogous
overflow risk.

`AddHint(x[d, σ₀(d)], 1)` warm-starts every candidate from the current
assignment, in both stages (harmless when unused, and stage 1's own
optimum is frequently "keep everyone where they are" when nothing already
violates (C5)).

## CBC: "direct transcription", deliberately not scaled

The plan's own words for this backend: "continuous `e_s`, `Z_s`, `r_s` are
fine." `_cbc_feasibility_constraints()`/`_cbc_objective_terms()` write the
identical constraints CP-SAT does, but with plain floats — no
`_LOAD_SCALE`/`_WEIGHT_SCALE` anywhere, because CBC needs none of
CP-SAT's integer-coefficient discipline. `solver.mip_gap` and
`solver.time_limit_seconds` map onto `pulp.COIN_CMD(gapRel=...,
timeLimit=...)` directly.

Every variable is built with `_lp_variable()`, a thin wrapper around the
direct `pulp.LpVariable(name, ...)` constructor — **not**
`prob.add_variable(...)`, PuLP v4's replacement, despite an earlier
version of this module having switched to it (REVIEW.md S-01, found by
running the CBC tests against the exact pulp version Debian trixie
packages). `LpProblem.add_variable` does not exist before pulp 3.3.1;
trixie packages 2.7.0, and section 2.1 designates CBC-through-`python3-pulp`
as *the* packaged solver path, so the "modernize to v4" choice crashed on
the platform this project targets, while working fine — and passing every
test — against a hand-picked newer pulp installed by hand. Direct
`LpVariable(...)` construction works unchanged across every pulp version
from 2.7.0 through 3.3.2 (bisected by wheel inspection); on 3.3+ it also
raises a `DeprecationWarning` recommending `add_variable`, which
`_lp_variable()` suppresses explicitly with a `warnings.catch_warnings()`
block — the warning is real, but the alternative it recommends is the one
that cannot run on the deployment target, so silencing it is the correct
fix, not a workaround. `_pulp_solve()` similarly turns a `PulpSolverError`
(Debian splits the `coinor-cbc` binary into a separate `Recommends`, not a
`Depends`, of `python3-pulp` — the library can import with no working
solver behind it) into this module's usual `None`, matching `solve()`'s
"never raises, `cli.py`'s fallback cascade handles it" contract instead of
a bare traceback.

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

## The storage cooldown: enforced in both stages, both backends (REVIEW.md S-04)

`_cpsat_feasibility_constraints()`/`_cbc_feasibility_constraints()` both
take `cooldown_storages` now and add one constraint per `(d, s)` pair
where `s` is in it and is not `d`'s current storage: `x_{d,s} = 0`.
Applied inside the shared feasibility-constraint builder, it lands in
*both* lexicographic stages automatically (built once per stage, per
`solve()`'s own architecture) — a disk cannot be assigned to a cooldown
storage it is not already on, in either the reserve-minimization stage or
the real-objective one, matching section 6's "accepts no new incoming
moves" and `heuristic._descend()`'s own identical `target.id in
cooldown_storages` check. A disk already resident on a cooldown storage
is left free to leave it, or to stay — the cooldown only ever blocks an
*arrival*.

An earlier revision of this module left the parameter accepted but
unenforced, reasoning that cooldowns were inert anyway since nothing
wrote `state.json`'s cooldown timestamps yet. That reasoning stopped
holding the moment `execute.py`/`apply` (phase 7) started calling
`state.with_recorded_cooldown()` — from that point on, `solver.backend:
auto`'s default cascade to CP-SAT/CBC could plan straight through a
cooldown the heuristic would have respected, silently disagreeing with it
on the exact case the cooldown exists for. Fixed as above.

**Not replicated**: `heuristic._repair()`'s own exemption from this same
cooldown when fixing a live (C4)/(C5) violation (section 13's
reserve-override principle — a repair move is never deferred for a
cooldown). The fix here is one constraint applied uniformly to both
solve stages, including stage 1's reserve-shortfall minimization itself,
so a cooldown storage stays excluded even when it is the *only* way to
resolve a violation — narrower than the heuristic's behaviour in that
one specific edge case (a group simultaneously mid-violation and
mid-cooldown on its one viable target). Reported honestly rather than
silently: stage 1's own slack is genuinely 0 achievable-within-constraints
with the cooldown storage excluded, so `plan` still reports an accurate
number, just a more conservative one than the heuristic would compute for
the identical input. Replicating the exemption exactly would need a
second, repair-only relaxation of the same constraint or a restructured
two-phase solve — a real, separately-scoped piece of work.

## Deliberately not implemented in this pass

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
  backends were verified for real during development (`pip install
  -e .[solver]`, all of `test_optimize.py` passing and reproducing the
  section 14 and `reserve-tradeoff.yaml` fixtures' exact numbers for both
  CP-SAT and CBC) — see `tests/unit/test_optimize.py`'s own docstring.
  That first pass installed pulp 3.3+ from PyPI, not the version actually
  packaged for the deployment target — a gap REVIEW.md's tenth pass
  caught (S-01): `python3-pulp 2.7.0+dfsg` (Debian trixie, also what CI's
  `debian:trixie` job installs) predates `LpProblem.add_variable`, PuLP
  v4's variable-construction API, which an earlier revision of this
  module had adopted and which crashed immediately on that version. Fixed
  by constructing every variable with `pulp.LpVariable(...)` directly
  (works unchanged on every pulp release from 2.7.0 through 3.3.2,
  bisected by wheel inspection) and suppressing the resulting v4-migration
  `DeprecationWarning` on 3.3+ explicitly, plus catching `PulpSolverError`
  around `prob.solve()` (the `coinor-cbc` binary is a separate Debian
  `Recommends`, not a `Depends`, of `python3-pulp` — the library can
  import with no working solver behind it) so a missing solver returns
  `None` like every other "this backend cannot produce a plan" case,
  rather than a bare traceback. `test_optimize.py`'s CBC cases now pass
  against pulp 2.7.0 too, verified directly against a throwaway venv
  pinned to that exact version — the packaged path, not just the newer
  one pip happens to resolve.

  That first verification pass was a one-off, done by hand. It no longer
  is: `.github/workflows/tests.yml`'s "test" job now `pip install`s
  `ortools` itself, specifically so `test_optimize.py`'s cpsat-marked
  cases run on every push rather than only in whichever developer's venv
  happens to have it — `coinor-cbc`/`python3-pulp` were already apt
  packages the container installs regardless, so CBC's cases needed no
  such step. The numpy/mypy footprint above is exactly why that install
  happens *after* `make typecheck`, never before it, in that job.
