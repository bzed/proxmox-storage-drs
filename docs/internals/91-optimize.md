# The MILP backend: CBC via pulp

**What does this page answer?** How does `optimize.py` turn section 5.3's
constraint set into a real CBC model (built through `pulp`), why is the
reserve solved in two lexicographic stages rather than one big-M
objective, and what does `cli.py`'s backend dispatch actually do when the
MILP solver is unavailable or fails? Describes
`proxmox_storage_drs/optimize.py`.

A CP-SAT (`ortools`) backend shared this module until REVIEW.md AL-02
removed it: `ortools` is not in Debian, is excluded from vendoring by the
plan's own dependency rules, and is not something operators install by
hand on PVE hosts, so on every deployment `solver.backend: auto`
resolved to CBC regardless. What went with it: the integral-coefficient
scaling discipline of section 5.5's former CP-SAT paragraphs (the
`K`/`W` scales, per-coefficient constant folding, the `γ`-quantization
trap of REVIEW.md F-14, the S-09 int64 assertions), the
`cpsat_available()` probe, the `cpsat` arm of `cli.py`'s cascade and of
the corpus sweep matrix, and a `pip install ortools` exception in GitHub
Actions. Any future integer backend must re-earn F-14's analysis rather
than inherit it.

## The backend solves, then hands off to `heuristic.evaluate_assignment()`

`solve()` builds a model, extracts the winning `x_{d,s}` assignment, and
immediately calls the *same* `heuristic.evaluate_assignment()` the
heuristic backend uses to produce the reported
`ObjectiveBreakdown` — one implementation of the section 5.4 objective,
shared by the solver and the heuristic alike (AGENTS.md section 5; `heuristic.py`'s own module
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
revision applied the same `mip_gap` to both stages, and PuLP's own
`LpStatus` string is `"Optimal"` whether CBC proved the bound or merely
stopped because `gapRel` was satisfied —
either way, stage 2 then pinned `Σ r_s` to that unproven incumbent
(`==`), which can both accept a shortfall up to the gap *and* forbid
finding less of it. Fixed by forcing stage 1's own gap to `0` regardless
of the configured `solver.mip_gap` (which now applies
to stage 2's real objective alone) and changing stage 2's slack
constraint from `==` to `<=` -- monotone-safe (stage 2
can never do worse than the now-proven stage-1 value) rather than brittle
against a hypothetical disagreement between the two solves. Cheap in
practice: stage 1 is a near-feasibility problem that closes instantly on
realistic groups, so forcing an exact proof costs nothing measurable.

## CBC via pulp: "direct transcription", deliberately unscaled

The plan's own words for this backend: "continuous `e_s`, `Z_s`, `r_s` are
fine." `_cbc_feasibility_constraints()`/`_cbc_objective_terms()` write the
section 5.3/5.4 constraints directly, in plain floats — no scaling
anywhere, no integer-coefficient discipline to satisfy.
`solver.mip_gap` and `solver.time_limit_seconds` map onto
`pulp.COIN_CMD(gapRel=..., timeLimit=...)` directly.

Every size-valued quantity (`Z_s`, `R_s`, `r_s`, `z_d`, `C_s`,
`Uˢᵉˣᵗ`, `soft_s`/`hard_s`) is expressed in whole MiB (`_mib()`) and
every load in section 4's average in-flight I/O requests, before the
weights are applied — not for exactness (floats would be exact enough)
but for LP conditioning: raw bytes (~10¹²-10¹⁴) alongside load values
(~1-10) badly condition the matrix for CBC's simplex, and CBC does not
raise on that, it silently returns a numerically poor "optimal"
(confirmed on a real corpus bundle, where an unscaled model made CBC's
own post-plan spread almost 100× worse than the heuristic's on the same
weights). `soft_s` is `storage.
free_space_soft_bytes` — resolved once per storage by `topology.py`
(`60-topology.md`), never a scalar threaded in from config; `r[s.id] >=
_mib(s.free_space_soft_bytes)` is the model's one-sided bound on
`R_s`, alongside the `reserve_factor·Z_s` one.

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
fix, not a workaround. `_pulp_solve()` similarly turns a `PulpSolverError` —
raised when `pulp` is importable but the `cbc` binary either is not on
`PATH` or fails to execute — into this module's usual `None`, matching
`solve()`'s "never raises, `cli.py`'s fallback cascade handles it" contract
instead of a bare traceback. That scenario is not the Debian package split
an earlier version of this page claimed: `python3-pulp`'s own control file
already `Depends: coinor-cbc` (confirmed by `rmadison`/`apt-cache show`
against trixie, not just assumed), and `debian/control` here now makes
both `Depends` of `pve-storage-drs` itself too, so a Debian install cannot
end up with one and not the other short of a deliberately broken one. The
catch earns its keep from the two cases that remain: a non-Debian
`pip install pulp` with no system `cbc` at all, and a `cbc` invocation
that fails for some other reason (a malformed model, a killed subprocess)
— either way, still "this backend cannot produce a plan", never a bare
traceback.

## `kappa*w_v` and `D^big`: weighting folded as data

Section 5.4's `w_v = max(1, l_v/l_bar)` is data, not a variable — computed
once per group by `heuristic.compute_vm_weights()` (imported by this
module, never recomputed here) and folded into a **per-vmid** `kappa`
coefficient, exactly like `u*`/`b_bar` are already folded elsewhere in this
file: `kappa · w_v` multiplies each vmid's own `pulp.lpSum(y[v, s.id] ...)`
term directly, at full float precision.

`D^big = {d : z_d >= migration.tiny_disk_bytes}` restricts `beta`/`gamma`
to `movable` disks at or above the configured threshold — not a coefficient
of `0` for an excluded disk, but the disk's terms skipped entirely. This is
exercised end to end, not just at the
coefficient level, by `test_optimize.py`'s
`test_tiny_disk_bytes_lets_a_tiny_disk_reunite_with_its_vm_for_free` — a
1 MiB `efidisk0` that is not worth a full `beta` migration at
`tiny_disk_bytes: 0` becomes free to reunite with its VM once the
threshold covers it — and by
`tests/unit/test_affinity_repair_fixture.py`, which runs section 14.7's
whole fixture through `solve()` and confirms it agrees
with the heuristic.

## `(C1)`/`(C3)`/`(C4)`/`(C5)` are shared code, built once per stage

`_cbc_feasibility_constraints()` builds
exactly the constraints both lexicographic stages need identically — only
the *objective* differs between stage 1 (`Minimize(Σ r_s)`) and stage 2
(the real section 5.4 objective, with `Σ r_s` fixed to stage 1's result as
a hard constraint). Each is called twice, with fresh variables each time,
rather than trying to mutate one model's objective in place — simpler to
reason about than partial reuse, at the cost of building the constraint
set twice per solve (irrelevant next to a MILP solve's own running time).

(C3)'s `y_{v,s}` linking honors `objective.affinity_counts_pinned_disks`
exactly as the plan's own text describes it: **false** links
`y` to `x` over `D^mov` only, so a pinned disk never forces `y_{v,s}=1`
for its storage; **true** (the default) ranges the constraint over all of `D`, which
this module implements as forcing `y_{v,s}=1` outright wherever a pinned
disk of `v` already sits (the natural reading of "`x_{d,s} ≤ y_{v,s}`
for `d ∈ D`" when `x_{d,σ₀(d)}` is a constant `1`, not a variable, for a
pinned disk).

## `cli.py`'s dispatch: `auto` cascades, an explicit backend still falls back

`cli._solve_group()` implements `solver.backend`'s three values:
`"auto"` tries `cbc`; `"cbc"` tries only that one;
`"heuristic"` skips `optimize.solve()` entirely. Whichever backend
`solve()` cannot use (library not importable, or no feasible solution
within `solver.time_limit_seconds`) returns `None` — never an exception —
and `_solve_group()` moves to the next one in the cascade, ending at
`heuristic.run_heuristic()` if every MILP attempt failed. This applies
**even to an explicitly forced backend**: section 13's failure-mode table
says "solver infeasible or timing out -> fall back to the heuristic;
never emit a partial/unvalidated assignment", with no carve-out for
`solver.backend: cbc` specifically. The one difference: falling back
from an *explicit* backend logs a warning (an operator who named `cbc`
to reproduce a specific result should not have to diff `--json` output to
notice `auto` quietly ran instead); falling back within `auto` itself is
expected and silent. `plan`'s human and `--json` output both report which
backend actually produced each group's plan (`solver: cbc (optimal)` /
`"solver_backend": "cbc", "solver_status": "optimal"`), precisely so
that distinction is never hidden.

## The storage cooldown: enforced in both stages (REVIEW.md S-04)

`_cbc_feasibility_constraints()`
takes `cooldown_storages` and adds one constraint per `(d, s)` pair
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
auto`'s cascade to the MILP could plan straight through a
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

**(C2) format-compatibility eligibility is implemented**, in the same
place and the same way as the cooldown fix just above: `_fixed_zero_pairs()`
is the one generator `_cbc_feasibility_constraints()`
calls to decide which `(disk, storage)`
pairs get `x_{d,s}=0`, yielding a pair whenever the storage is in
`cooldown_storages` **or** `topology.storage_accepts_format(s, d.format)`
is false — one shared function rather than the cooldown check and the
format check duplicated inline in the model builder (factoring the
*decision* out, not just the loop, is what keeps the builder under this
project's own complexity limit). A disk already
resident on a storage is never fixed away from it by either rule.

## Deliberately not implemented in this pass

- **A live cluster's numpy/pandas footprint.** `statsmodels` (the
  `[forecast]` extra) pulls in numpy purely as its own transitive
  dependency; nothing in this project imports numpy directly. A recent
  numpy's bundled type stubs use syntax newer than this project's
  `python_version = "3.11"` mypy target, and no per-module mypy setting
  can rescue it, because a stub-level *parse* error happens before mypy
  ever gets to apply a setting to it. (When the former `ortools` backend
  existed, its own numpy dependency surfaced the same problem through
  `pip install -e .[solver]` — verified directly, extending an override
  to `pulp.*`/`statsmodels.*`/`numpy.*` does not rescue it either, it is
  that hard a parse error.) `make typecheck` does
  not risk this at all: it runs mypy against its own dedicated
  `.venv-typecheck` (`make venv-typecheck`, `.[dev]` only), never the
  `.venv` that `make test`/`make cov` install `solver`/`forecast` into for
  full backend coverage -- a *separate* venv, not a reused one later
  cleaned up, so nothing either target does to `.venv` can ever reach it.
  See the `Makefile`'s own comment on `TCVENV`. The CBC backend was
  verified for real during development (`pip install
  -e .[solver]`, all of `test_optimize.py` passing and reproducing the
  section 14 and `reserve-tradeoff.yaml` fixtures' exact numbers —
  first with both backends, before CP-SAT's removal) — see
  `tests/unit/test_optimize.py`'s own docstring.
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
  around `prob.solve()` (`pulp` can still import with no working `cbc`
  binary behind it — a non-Debian `pip install pulp`, say — even though
  `python3-pulp` itself `Depends: coinor-cbc` on Debian) so a missing
  solver returns `None` like every other "this backend cannot produce a
  plan" case, rather than a bare traceback. `test_optimize.py`'s CBC cases now pass
  against pulp 2.7.0 too, verified directly against a throwaway venv
  pinned to that exact version — the packaged path, not just the newer
  one pip happens to resolve.

  That first verification pass was a one-off, done by hand. It no longer
  is, in either place this project runs tests. CI
  (`.github/workflows/tests.yml`'s "test" job) apt-installs
  `coinor-cbc`/`python3-pulp` up front, and
  nothing pip-installs anything any more — the former `ortools` step was
  removed with the backend (AL-02), which also removed the only ordering
  constraint that single-container environment ever had. Locally,
  `make test`/`make cov` install `solver`/`forecast` into
  `.venv` themselves (loudly, never fatally, if that install fails —
  `Makefile`'s own `SOLVER_EXTRAS`), so the CBC cases
  run there too without a developer needing to know to do it by hand;
  `make typecheck` never touches that venv at all, using its own
  `.venv-typecheck` instead, so there is no ordering to get right the way
  CI's single environment once needed.
