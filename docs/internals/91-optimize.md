# The MILP backend: CBC via pulp

**What does this page answer?** How does `optimize.py` turn section 5.3's
constraint set into a real CBC model, built through `pulp`? Why does the
tool solve the reserve in two lexicographic stages instead of one big-M
objective? What does `cli.py`'s backend dispatch do when the MILP solver
is unavailable or fails? This page describes
`proxmox_storage_drs/optimize.py`.

A CP-SAT (`ortools`) backend shared this module until REVIEW.md AL-02
removed it. `ortools` is not in Debian. The plan's own dependency rules
exclude it from vendoring. Operators do not install it by hand on PVE
hosts. On every deployment, `solver.backend: auto` resolved to CBC
regardless. The removal took the integral-coefficient scaling discipline
of section 5.5's former CP-SAT paragraphs. That includes the `K`/`W`
scales, per-coefficient constant folding, the `γ`-quantization trap of
REVIEW.md F-14, and the S-09 int64 assertions. The removal also took the
`cpsat_available()` probe, the `cpsat` arm of `cli.py`'s cascade and of
the corpus sweep matrix, and a `pip install ortools` exception in GitHub
Actions. Any future integer backend must re-earn F-14's analysis rather
than inherit it.

## The backend solves, then hands off to `heuristic.evaluate_assignment()`

`solve()` builds a model. It extracts the winning `x_{d,s}` assignment.
It then calls the *same* `heuristic.evaluate_assignment()` that the
heuristic backend uses to produce the reported `ObjectiveBreakdown`.
That is one implementation of the section 5.4 objective, shared by the
solver and the heuristic alike (AGENTS.md section 5). `heuristic.py`'s own
module docstring was written anticipating exactly this: "built specifically
so `optimize.py` can call the identical function". A modeling mistake in
this module can make the solver choose a *suboptimal* assignment at
worst. It can never make the tool *believe* an assignment is better than
it is. The number that ends up in `plan`'s output is never this module's
own objective value.

## Lexicographic, not big-M — and why that is the only mode implemented

Section 5.3 describes two ways to keep a reserve violation from being
"traded away" by a large enough balance gain. The first is a single-stage
objective with a calibrated penalty `P` (big-M). The second is a
two-stage **lexicographic** solve: minimize `Σ_s r_s` alone first, then
fix that total as a hard constraint and minimize the real objective.
`optimize.py` implements only the second. The plan itself says to ("use
the lexicographic solve by default... needs no calibration, its correctness
does not depend on `T_g`"). There is also no `solver.*` config knob that
ever selects big-M at runtime. Big-M exists in the plan text to be
*compared against* the lexicographic solve.
`tests/fixtures/generate_expected.py` already does that comparison by
exhaustive enumeration on `reserve-tradeoff.yaml`. This module needs no
second code path for it. `Σ r_s > 0` in a lexicographic result provably
means *no* assignment could do better, at any weight. It never merely
means "unattractive".

**That proof depends on stage 1 actually being solved to proven
optimality, not merely to `solver.mip_gap`** (REVIEW.md S-07). An earlier
revision applied the same `mip_gap` to both stages. PuLP's own `LpStatus`
string is `"Optimal"` whether CBC proved the bound or merely stopped
because `gapRel` was satisfied. Either way, stage 2 then pinned `Σ r_s`
to that unproven incumbent (`==`). That can both accept a shortfall up to
the gap *and* forbid finding less of it. The fix forces stage 1's own gap
to `0` regardless of the configured `solver.mip_gap`. That setting now
applies to stage 2's real objective alone. The fix also changes stage 2's
slack constraint from `==` to `<=`. That change is monotone-safe: stage 2
can never do worse than the now-proven stage-1 value. It is not brittle
against a hypothetical disagreement between the two solves. The cost is
low in practice. Stage 1 is a near-feasibility problem that closes
instantly on realistic groups. Forcing an exact proof costs nothing
measurable.

**The shortfall variables are integers, in whole MiB, and stage 2's bound
is exact.** Stage 2 reads stage 1's optimum back from CBC. It requires
`Σ r_s ≤` that value. With continuous `r_s`, the readback is only as
precise as CBC's solution file: about three decimals of a MiB. The bound
used to carry a tolerance of `1e-6`. A comment called it "a fraction of a
MiB". In fact it was a fraction of a millionth of one, about a byte. On
any group whose minimum shortfall was not a round number of MiB, stage 2
was `Infeasible` on every run. The group then fell back to the heuristic
silently. The tool found this on a real bundle: 231 GiB short, with two
528 KiB EFI disks the only movable disks on the short storages. Now each
`r_s` is an integer variable. The capacity constraint `Σ z_d x_{d,s} + … +
R_s ≤ C_s + r_s` has integer `r_s ≥ 0`. That makes `r_s` exactly the
shortfall rounded up to the next whole MiB. It is the same quantity
`reserve.compute_reserve_status()` reports (`docs/internals/60-topology.md`).
Stage 2's bound is the integer `round(min Σ r_s)`, with no tolerance at
all. `round()` only strips CBC's integrality noise (a value like
141308.9999999). There are `|S|` such integers per model, a handful. The
solve time does not change measurably.

**What the warning says when a stage produces nothing.**
`_no_feasible_solution()` takes PuLP's status string. It blames the clock
only for `Not Solved`: "hit solver.time_limit_seconds before finding a
feasible solution". It prints any other status verbatim ("returned no
usable solution (CBC status: Infeasible)"). It carries that status as
`solver_status` in the structured log record. Stage 1 is never
legitimately infeasible. The current assignment satisfies every one of its
constraints with `r_s` large enough. Stage 2 is feasible by construction
once its bound is exact. An `Infeasible` from either stage is a modelling
bug, not something more time would fix.

## CBC via pulp: "direct transcription", deliberately unscaled

The plan's own words for this backend: "continuous `e_s`, `Z_s`, `r_s`
are fine." `_cbc_feasibility_constraints()`/`_cbc_objective_terms()`
write the section 5.3/5.4 constraints directly, in plain floats. They use
no scaling anywhere and satisfy no integer-coefficient discipline.
`solver.mip_gap` and `solver.time_limit_seconds` map onto
`pulp.COIN_CMD(gapRel=..., timeLimit=...)` directly.

**(C7) is written in MiB.** `_cbc_storage_used_mib()` assembles `B_s` in
MiB, like every size in the model: assigned disks, pinned disks, and
foreign volumes. `_cbc_capacity_spread_term()` adds `d_s ≥ ±(B_s −
b̄·C_s)` rows. It scales `delta` by `2²⁰/2⁴⁰` per MiB. The term is `delta`
per TiB of absolute deviation. It matches `heuristic.evaluate_assignment()`
exactly. Raw bytes would badly condition the matrix. A fill *fraction*
(the earlier form) would price spread relative to the group. That is what
made the term vanish on large groups.

**`gapRel` is only meaningful against the real objective, so stage 2's
constant is kept.** PuLP hands the model to CBC without the objective
expression's constant term. CBC measures its relative gap against the
value it can see. Stage 2 writes "did disk `d` move" as `1 − x_{d,σ₀(d)}`.
Its objective then carries a large negative constant (−11.18 on the
committed 24h corpus bundle, against a true optimum of 0.30). A 2 % gap on
the shifted value was an absolute tolerance of about 0.23. CBC stopped at
0.389 and reported it `optimal`. `_objective_with_offset_as_variable()`
moves the constant onto a variable fixed to `[1, 1]`. CBC's objective is
then the real one, and `solver.mip_gap` means what it says. Stage 1's
objective, `Σ r_s`, has no constant. The function leaves it untouched.

Every size-valued quantity (`Z_s`, `R_s`, `r_s`, `z_d`, `C_s`,
`Uˢᵉˣᵗ`, `soft_s`/`hard_s`) is expressed in MiB (bytes divided by
`_BYTES_PER_MIB`). Every
load uses section 4's average in-flight I/O requests, before the weights
are applied. The reason is LP conditioning, not exactness: floats would
be exact enough. Raw bytes (~10¹²-10¹⁴) alongside load values (~1-10)
badly condition the matrix for CBC's simplex. CBC does not raise on that.
It silently returns a numerically poor "optimal". The tool confirmed this
on a real corpus bundle. There, an unscaled model made CBC's own post-plan
spread almost 100× worse than the heuristic's on the same weights.
`soft_s` is `storage.free_space_soft_bytes`. `topology.py` resolves it
once per storage (`60-topology.md`). It is never a scalar threaded in
from config. `r[s.id] >= s.free_space_soft_bytes / _BYTES_PER_MIB` is the model's
one-sided bound on `R_s`, alongside the `reserve_factor·Z_s` one.

Every variable is built with `_lp_variable()`. It is a thin wrapper
around the direct `pulp.LpVariable(name, ...)` constructor. It is
**not** `prob.add_variable(...)`, PuLP v4's replacement. An earlier
version of this module switched to it (REVIEW.md S-01). Running the CBC
tests against the exact pulp version Debian trixie packages found it.
`LpProblem.add_variable` does not exist before pulp 3.3.1. Trixie packages
2.7.0. Section 2.1 designates CBC-through-`python3-pulp` as *the*
packaged solver path. The "modernize to v4" choice crashed on the platform
this project targets. It worked fine, and passed every test, against a
hand-picked newer pulp installed by hand. Direct `LpVariable(...)`
construction works unchanged on every pulp version from 2.7.0 through
3.3.2 (bisected by wheel inspection). On 3.3+, it also raises a
`DeprecationWarning` recommending `add_variable`. `_lp_variable()`
suppresses it explicitly with a `warnings.catch_warnings()` block. The
warning is real. But the alternative it recommends is the one that cannot
run on the deployment target. Silencing it is the correct fix, not a
workaround. `_pulp_solve()` turns a `PulpSolverError` into this module's
usual `None`. That error is raised when `pulp` is importable but the
`cbc` binary either is not on `PATH` or fails to execute. This matches
`solve()`'s "never raises, `cli.py`'s fallback cascade handles it"
contract instead of a bare traceback. That scenario is not the Debian
package split an earlier version of this page claimed. `python3-pulp`'s
own control file already `Depends: coinor-cbc`. `rmadison` and
`apt-cache show` against trixie confirm that; the page does not assume
it. `debian/control` here now makes both `Depends` of `pve-storage-drs`
itself too. A Debian install cannot end up with one and not the other
short of a deliberately broken one. Two cases remain that
justify the catch. That is a non-Debian `pip install pulp` with no system
`cbc` at all, and a `cbc` invocation that fails for some other reason (a
malformed model, a killed subprocess). Either way, the result is still
"this backend cannot produce a plan", never a bare traceback.

## `kappa*w_v` and `D^big`: weighting folded as data

Section 5.4's `w_v = max(1, l_v/l_bar)` is data, not a variable.
`heuristic.compute_vm_weights()` computes it once per group. This module
imports it and never recomputes it. It folds the value into a **per-vmid**
`kappa` coefficient. It folds it exactly like `u*`/`b_bar` are already
folded elsewhere in this file: `kappa · w_v` multiplies each vmid's own
`pulp.lpSum(y[v, s.id] ...)` term directly, at full float precision.

**(C8), small disks follow their VM**, is one linear constraint per
(small movable disk, storage other than its current one).
`_cbc_small_disks_follow_their_vm()` builds it inside the shared
feasibility builder. Both lexicographic stages carry it: `x_{d,s} ≤ Σ
x_{b,s}` over the VM's larger movable disks in the group, plus the number
of its larger *pinned* disks already on `s`. The rule adds no new
variables. It stops stage 1 from "repairing" a shortfall with a sub-MiB
EFI disk that crosses a MiB boundary. `tests/unit/test_small_disks.py`
has that case. It shows CBC does move the disk with the rule switched
off. `topology.small_disk_placement_ok()` is the definition this
transcribes.

`D^big = {d : z_d >= migration.tiny_disk_bytes}` restricts `beta`/`gamma`
to `movable` disks at or above the configured threshold. The model skips
an excluded disk's terms entirely. It does not give the disk a coefficient
of `0`. `test_optimize.py` exercises the rule end to end, not just at the
coefficient level, with `test_tiny_disk_bytes_lets_a_tiny_disk_reunite_with_its_vm_for_free`.
At `tiny_disk_bytes: 0`, a 1 MiB `efidisk0` is not worth a full `beta`
migration. Once the threshold covers it, the disk can reunite with its VM
at no cost. `tests/unit/test_affinity_repair_fixture.py` also exercises the
rule. It runs section 14.7's whole fixture through `solve()` and confirms
the result agrees with the heuristic.

## `(C1)`/`(C3)`/`(C4)`/`(C5)` are shared code, built once per stage

`_cbc_feasibility_constraints()` builds exactly the constraints both
lexicographic stages need identically. Only the *objective* differs
between stage 1 (`Minimize(Σ r_s)`) and stage 2 (the real section 5.4
objective, with `Σ r_s` fixed to stage 1's result as a hard constraint).
The module calls the builder twice, with fresh variables each time. It
does not try to mutate one model's objective in place. That is simpler to
reason about than partial reuse. The cost is building the constraint set
twice per solve. That cost is irrelevant next to a MILP solve's own
running time.

(C4) is one row per VM and storage: `Z_s ≥ F_{v,s}` for every VM with any
disk in the group. `F_{v,s}` is the sum of the VM's movable disks that
land on `s` (at `z_{d,s}`, times `x_{d,s}`) plus its pinned disks already
there. `_cbc_vm_footprint()` is the one place the model sums a VM's disks
on a storage. A VM whose disks are all pinned still contributes its
constant footprint. `Z_s` is only bounded from below. That is exact at the
optimum by the same one-sided argument as before: `r_s ≥ f_s·Z_s` pushes
it down.

(C9), the large-VM split rule, lives in stage 2 only
(`_cbc_split_excess_term()`). The term adds one continuous `o_v ≥ 0` per
`v ∈ V^split`. `heuristic.active_split_caps()` gives `V^split`. It is
empty when `snapshot_reserve.split_vm_footprint` is `null` or
`objective.mu_vm_split_per_tib` is `0`. The term bounds `o_v` below by
`F_{v,s} − T_v` on every storage. It charges `μ` per TiB. The variable is
in TiB, the unit `μ` and `γ` are quoted in. The term lives in stage 2
only, because a split is a preference. It must never displace a reserve
repair. Stage 1 settles the repair first. `compute_vm_weights()` returns
`w_v = 1` for every `v ∈ V^split`. A busy large VM's I/O cannot veto its
own split. The big-M variant of the plan is not built, so its `U_obj`
bound has no counterpart here.

(C3)'s `y_{v,s}` linking honors `objective.affinity_counts_pinned_disks`
exactly as the plan's own text describes it. **false** links `y` to `x`
over `D^mov` only. A pinned disk then never forces `y_{v,s}=1` for its
storage. **true** (the default) ranges the constraint over all of `D`.
This module implements that as forcing `y_{v,s}=1` outright wherever a
pinned disk of `v` already sits. That is the natural reading of
"`x_{d,s} ≤ y_{v,s}` for `d ∈ D`" when `x_{d,σ₀(d)}` is a constant `1`,
not a variable, for a pinned disk.

## `cli.py`'s dispatch: `auto` cascades, an explicit backend still falls back

`cli._solve_group()` implements `solver.backend`'s three values.
`"auto"` tries `cbc`. `"cbc"` tries only that one. `"heuristic"` skips
`optimize.solve()` entirely. A backend that `solve()` cannot use returns
`None`, never an exception. That happens when the library is not
importable, or when a stage has no usable solution (timed out or
otherwise, see above). `_solve_group()` then moves to the next backend in
the cascade. If every MILP attempt failed, it ends at
`heuristic.run_heuristic()`. This applies **even to an explicitly forced
backend**. Section 13's failure-mode table says "solver infeasible or
timing out -> fall back to the heuristic; never emit a partial/unvalidated
assignment". It makes no carve-out for `solver.backend: cbc` specifically.
The one difference is a log line. Falling back from an *explicit* backend
logs a warning. An operator who named `cbc` to reproduce a specific result
should not have to diff `--json` output to notice `auto` ran instead.
Falling back within `auto` itself is expected and silent. `plan`'s human
and `--json` output both report which backend actually produced each
group's plan (`solver: cbc (optimal)` / `"solver_backend": "cbc",
"solver_status": "optimal"`). The distinction is never hidden.

## Excluded storages: never a destination

`_fixed_zero_pairs()` also fixes `x_{d,s} = 0` for every storage `s` with
`excluded=True` (`exclude.storages`), when `s` is not the current storage of `d`.
It asks `topology.storage_accepts_incoming()`, the same function the heuristic
and the split gate ask. The constraint lands in both stages. The disks on an
excluded storage are pinned by `topology.py`, so no disk leaves either. Unlike
the cooldown, no repair exemption exists: a repair move never uses an excluded
storage in the heuristic or in the MILP.

## The storage cooldown: enforced in both stages (REVIEW.md S-04)

`_cbc_feasibility_constraints()` takes `cooldown_storages`. It adds one
constraint per `(d, s)` pair where `s` is in it and is not `d`'s current
storage: `x_{d,s} = 0`. The builder is shared, so the constraint lands in
*both* lexicographic stages automatically. It is built once per stage, per
`solve()`'s own architecture. A disk cannot be assigned to a cooldown
storage it is not already on. That holds in both the reserve-minimization
stage and the real-objective one. The rule matches section 6's "accepts
no new incoming moves" and `heuristic._descend()`'s own identical
`target.id in cooldown_storages` check. A disk already resident on a
cooldown storage can leave it, or stay. The cooldown only ever blocks an
*arrival*.

An earlier revision of this module accepted the parameter but did not
enforce it. The reasoning was that cooldowns were inert anyway, since
nothing wrote `state.json`'s cooldown timestamps yet. The reasoning stopped
holding the moment `execute.py`/`apply` (phase 7) started calling
`state.with_recorded_cooldown()`. From that point on, `solver.backend:
auto`'s cascade to the MILP could plan straight through a cooldown the
heuristic would have respected. The cascade would then disagree with the
heuristic silently, on the exact case the cooldown exists for. The fix is
as above.

**Not replicated**: `heuristic._repair()`'s own exemption from this same
cooldown when fixing a live (C4)/(C5) violation. That exemption follows
section 13's reserve-override principle: a repair move is never deferred
for a cooldown. The fix here is one constraint applied uniformly to both
solve stages. It includes stage 1's reserve-shortfall minimization itself.
A cooldown storage stays excluded even when it is the *only* way to
resolve a violation. That is narrower than the heuristic's behaviour in
that one specific edge case (a group simultaneously mid-violation and
mid-cooldown on its one viable target). The module reports the difference
rather than hiding it. Stage 1's own slack is genuinely 0 achievable
within constraints with the cooldown storage excluded. `plan` still
reports an accurate number, just a more conservative one than the
heuristic would compute for the identical input. Replicating the exemption
exactly would need a second, repair-only relaxation of the same
constraint, or a restructured two-phase solve. That is a real,
separately-scoped piece of work.

**(C2) format-compatibility eligibility is implemented**, in the same
place and the same way as the cooldown fix just above. `_fixed_zero_pairs()`
is the one generator `_cbc_feasibility_constraints()` calls to decide
which `(disk, storage)` pairs get `x_{d,s}=0`. It yields a pair whenever
the storage is in `cooldown_storages` **or**
`topology.storage_accepts_format(s, target_format(d, s))` is false. One shared
function replaces the cooldown check and the format check duplicated
inline in the model builder. Factoring the *decision* out, not just the
loop, keeps the builder under this project's own complexity limit. A disk
already resident on a storage is never fixed away from it by either rule.

## Deliberately not implemented in this pass

- **A live cluster's numpy/pandas footprint.** `statsmodels` (the
  `[forecast]` extra) pulls in numpy purely as its own transitive
  dependency. Nothing in this project imports numpy directly. A recent
  numpy's bundled type stubs use syntax newer than this project's
  `python_version = "3.11"` mypy target. No per-module mypy setting can
  rescue it. A stub-level *parse* error happens before mypy can apply a
  setting to it. The former `ortools` backend surfaced the same problem
  through `pip install -e .[solver]`. The developers verified it directly:
  extending an override to `pulp.*`/`statsmodels.*`/`numpy.*` does not
  rescue it either. That is that hard a parse error. `make typecheck`
  does not risk this at all. It runs mypy against its own dedicated
  `.venv-typecheck` (`make venv-typecheck`, `.[dev]` only). It never uses
  the `.venv` that `make test`/`make cov` install `solver`/`forecast`
  into for full backend coverage. That venv is *separate*, not a reused
  one cleaned up later. Nothing either target does to `.venv` can ever
  reach it. See the `Makefile`'s own comment on `TCVENV`. The developers
  verified the CBC backend for real during development (`pip install
  -e .[solver]`). All of `test_optimize.py` passed, reproducing the
  section 14 and `reserve-tradeoff.yaml` fixtures' exact numbers. That
  first pass ran with both backends, before CP-SAT's removal. See
  `tests/unit/test_optimize.py`'s own docstring. That first pass
  installed pulp 3.3+ from PyPI, not the version actually packaged for
  the deployment target. REVIEW.md's tenth pass caught that gap (S-01).
  `python3-pulp 2.7.0+dfsg` (Debian trixie, also what CI's
  `debian:trixie` job installs) predates `LpProblem.add_variable`, PuLP
  v4's variable-construction API. An earlier revision of this module had
  adopted the API. It crashed immediately on that version. The fix
  constructs every variable with `pulp.LpVariable(...)` directly. That
  works unchanged on every pulp release from 2.7.0 through 3.3.2,
  bisected by wheel inspection. The fix also suppresses the resulting
  v4-migration `DeprecationWarning` on 3.3+ explicitly. It catches
  `PulpSolverError` around `prob.solve()`. `pulp` can still import with
  no working `cbc` binary behind it (a non-Debian `pip install pulp`,
  say), even though `python3-pulp` itself `Depends: coinor-cbc` on
  Debian. A missing solver then returns `None`, like every other "this
  backend cannot produce a plan" case, rather than a bare traceback.
  `test_optimize.py`'s CBC cases now pass against pulp 2.7.0 too. A
  direct check against a throwaway venv pinned to that exact version
  confirmed it. That is the packaged path, not just the newer one pip
  happens to resolve.

  That first verification pass was a one-off, done by hand. It no longer
  is, in either place this project runs tests. CI
  (`.github/workflows/tests.yml`'s "test" job) apt-installs
  `coinor-cbc`/`python3-pulp` up front. Nothing pip-installs anything any
  more. The former `ortools` step was removed with the backend (AL-02).
  That also removed the only ordering constraint that single-container
  environment ever had. Locally, `make test`/`make cov` install
  `solver`/`forecast` into `.venv` themselves. If that install fails, the
  targets report it loudly but never fatally. That is `Makefile`'s own
  `SOLVER_EXTRAS`. The CBC cases then run there too, without a developer
  knowing to do it by hand. `make typecheck` never touches that venv at
  all. It uses its own `.venv-typecheck` instead. There is no ordering to
  get right the way CI's single environment once needed.
