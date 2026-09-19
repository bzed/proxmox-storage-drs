# Review of `IMPLEMENTATION_PLAN.md` (Proxmox Storage DRS)

This document is a careful, verbose review of `IMPLEMENTATION_PLAN.md`, `README.md`,
`config/drs.example.yaml`, and `.gitignore` in this repository. It is structured to be
machine-parseable: each finding has a stable ID, a severity, a section anchor, a statement of
the issue, and a concrete recommendation. A summary table precedes the detail.

The reviewer independently re-derived every number in the section 14 worked example and
verified them by hand; the results of that verification are recorded in Appendix A. A few
load-bearing external facts were checked via web search and are reported in Appendix B.

A **second pass** (section 6) reviews the updated plan after the author addressed F-01..F-25.
All original findings are resolved; seven new findings (N-01..N-07) were identified in the new
and changed material.

A **third pass** (section 7) reviews the plan after the author addressed N-01..N-07 and added
substantial new material (all-bus enumeration, snapshot handling, saferemove wipe accounting,
VM locks, load-model rescale, saturation-load redesign, fixture generator). All N-findings
are resolved; six new findings (M-01..M-06) were identified, all Low or Info severity.

A **fourth pass** (section 8) reviews the plan after the author addressed M-01..M-06 and added
the `reserve-tradeoff` fixture, the lexicographic solver path, the `ω_wipe` state-dependent
saturation guard, AGENTS.md, and the Python toolchain. All M-findings are resolved; two new
findings (K-01..K-02) were identified, both Low severity.

A **fifth pass** (section 9) reviews the plan after the author addressed K-01..K-02. Both
findings are resolved. No new findings. The plan and fixtures are clean.

A **sixth pass** (section 10) reviews the substantial new material added after the fifth pass:
the `pve-storage-drs` naming, full Debian packaging (`debian/`), two CI pipelines, the PDF
paper pipeline (`docs/paper/`, `tools/check_paper_log.py`), the documentation policy and
manpage, config-on-pmxcfs, state path, and global CLI options. Five new findings (L-01..L-05)
are identified. The first three are Medium severity and concern packaging/CI consistency with
the plan; the remaining two are Low and Info.

A **seventh pass** (section 11) reviews the first actual implementation: phases 1 and 2 of the
plan (config, metrics, forecast, CLI skeleton, PVE API client, topology, reserve), plus the
full documentation suite (`docs/internals/`, `docs/manual/`), the generalized paper pipeline
(`tools/build_paper.sh`), and the L-finding fixes. Three new findings (P-01..P-03) are
identified, all concerning config knobs documented as functional but not yet wired through in
the code, or VM-level privileges the manual omits. **Section 12** records how all three were
resolved: `ticket_refresh_seconds` and `read_workers` are now both wired through (the former
also gained a reauthenticate-and-retry-once path for a ticket that expires from an external
cause, e.g. a long `apply --confirm` wait), and the manual now names the VM-level privileges
`apply` will need.

An **eighth pass** (section 13) reviews phases 3-4: `loadmodel.py` (the section 4 load model,
wired into `show-load`), `gates.py` (the section 6 act/no-act decision), `heuristic.py` (the
section 5.4/5.5 dependency-free solver), the `pve.py` reauthenticate-and-retry path and
`topology.py` concurrent fetch from the P-01/P-02 fixes, and the `reserve.py`/`metrics.py`
extensions those modules needed. Two new findings (Q-01..Q-02) are identified, both Low.
**Section 14** records how both were resolved: `evaluate_assignment()` now implements
`objective.spread_metric: minmax` correctly (as `max(u_s)`, not `max(e_s)` — the finding's own
suggested fix would have computed the wrong quantity), and the manual now documents the
per-group Prometheus query multiplier for multi-group configs.

A **ninth pass** (section 15) reviews phases 4-5: `schedule.py`, `payback.py` and the `plan`
command. Six findings (R-01..R-06) are identified; **section 16** records how all six were
resolved.

A **tenth pass** (section 17) reviews the state/cooldown work and phases 6-7: `state.py`
(section 11.2), the cooldown wiring, `optimize.py` (CP-SAT/CBC MILP backends) and `execute.py`
(move execution, `apply`). Nine findings (S-01..S-09) are identified — two High: the CBC
backend crashes on the pulp version Debian trixie actually ships (reproduced against 2.7.0;
CI installs exactly that version and its CBC tests cannot pass), and `apply` executes plans
that failed the section 7.3 payback acceptance test, including moves the hard per-move
duration rule rejected. **Section 18** records how all nine were resolved.

An **eleventh pass** (section 19) reviews the finalized implementation: everything that landed
after the S-01..S-09 fixes — phase 8 (`auto` mode, time windows, migration cap, the re-plan
loop), section 13 crash/two-instance recovery, the section 8.1 generalized transient invariant,
concurrent execution, per-disk load time series, the section 7.3 saturation guard and its wiring
into `plan`/`apply`, and phase 9's section 10.2 forecast backtest gate (~5,900 inserted lines,
two new modules). Seven new findings (T-01..T-07) are identified: three Medium (the re-plan loop
silently does not trigger under the concurrent executor; re-plans and mid-group crashes lose the
executed moves' cooldown recording that section 9.2 step 2 mandates; the manual and example
config claim the optimizer consumes the forecaster's upper bound, which it does not), three Low
(stale "saturation check not implemented anywhere" claims contradicted by the same range's own
saturation wiring; a stale `96-payback.md` paragraph that would reintroduce the R-01 bug; three
divergent semantics for the `max_migrations_per_run` counter), one Info. **Section 20** records
how all seven were resolved.

A **twelfth pass** (section 21) reviews everything after the T-fixes: two real bugs found
dogfooding against a production cluster (the heuristic's missing whole-VM co-relocation
candidate, and the `requests` connection pool smaller than `read_workers`), five CI repairs
found the first time the pipelines actually ran, and the section 11.4 `/regex/` storage-pattern
feature (the first new plan section added since the implementation was finished). Three new
findings (U-01..U-03) are identified: one Medium (the plan's section 11.4 names a different
pattern-matching endpoint than the code implements, and the untested matched-but-unavailable
edge aborts the run with an error that does not name the pattern), one Low (a six-location
cluster of stale "not yet written" documentation claims), one Info (an undocumented second
pattern asymmetry: matched storages skip the not-`shared` warning). **Section 22** records how
all three were resolved.

A **thirteenth pass** (section 23) reviews the finalized tool's next seven commits: the `explain`
command (the last unimplemented subcommand), section 3.4's node-scoping of every PromQL query
(with the `metrics.extra_selector` override), CI installing `ortools` so the CP-SAT path is
finally exercised, a dedicated mypy venv with a loud-not-swallowed solver install, the README
rewrite, and a sweep replacing bare "section N.M" citations in operator-facing messages with
plain language. Five new findings (V-01..V-05) are identified: two Medium (the manual's
`objective.reserve_violation_penalty` entry describes a provably-dominant-P computation that has
never existed anywhere in the code, and the §9.5 pinned block the plan calls "not optional
decoration" lives only in `explain`, without its action hints, while `27-plan.md` falsely claims
`plan` shows pins too), one Low (two internally inconsistent "used" figures in the new
`29-explain.md` worked example — every other number in it verifies by hand), one Low (the CI
pip-installs `ortools` as a documented-in-workflow-only exception to AGENTS.md §9.3's absolute
"apt, never pip" rule), one Info (an untracked, referenced-nowhere helper script in the working
tree). **Section 24** records how all five were resolved.

A **fourteenth pass** (section 25) reviews the next eight commits: the 0.1.0 version/changelog cut,
`python3-pulp`/`coinor-cbc` promoted from `Recommends` to `Depends`, three live-cluster fixes to
disk-size resolution in `topology.py` (a `KeyError('size')` crash on a present-but-sizeless content
item, a new `approximate-size` tier above the VM-config fallback, and querying a managed disk's
content listing from its own VM's node so the exact `size` — not the approximate one — is what gets
used), and a two-commit change to §3.4 query scoping (`verify-metrics`'s cluster-label discovery,
then `metrics.labels.cluster` defaulting to `"cluster"` so queries scope by the live cluster's own
name instead of its node list). Nine findings (W-01..W-09) are identified: one Medium — the
cluster-label default makes every load query match zero series, and the tool degrade to "idle", on
a Prometheus that carries no such label (the vanilla metric-server shape), and `verify-metrics`
cannot detect this because it deliberately never applies the tier it broke. Seven Low: five
documentation-staleness findings (a stale "`auto` not yet" on the manual's own authoritative
status page; phase mislabelling in the 0.1.0 changelog, which also records none of the range's
post-cut features; a stale "five stages"/`_collect_vm_disks` cluster around the internals page's
renumbered step list; the operator manual's warnings paragraph not extended for the three new size
warnings; and two locations — the example config's `extra_selector` comment and `explain`'s worked
example — still showing the old node-scoped default) plus two behaviour-adjacent ones (the runtime
presentation of a selector matching nothing as an idle group; every run now hard-requiring
`Sys.Audit` for `GET /cluster/status`). One Info: the content-listing read-path amplification,
and §3.5's stale expected-call-count formula, unquantified.

A **fifteenth pass** (section 29) reviews everything after the W-fixes: the 0.1.1 changelog, the
cluster-label removal (recorded as section 27) and the cross-metric fix (section 28), and then the
largest single addition since the engine itself — plan §16's `collect-testdata`/`--replay`
diagnostic-bundle subsystem (`anonymize.py`, `collect.py`, `replay.py`, the `support{}` config
block, `tests/corpus/` and its scrub audit, and two real-cluster corpus bundles), the §9.5
closest-rejected-move addition to `explain`, the §2.3 logging policy (phase 11), the non-finite
JSON fix, and the README quickstart/metrics-transport documentation work. Ten findings
(X-01..X-10) are identified: four Medium — `exclude.disks` is carried verbatim into a bundle's
`config.yaml`, leaking real vmids through the one §16.3 rule that names it explicitly; the
manifest call-log's `detail` can carry endpoint hostnames past both the redactor and the scrub
audit (verified empirically); the scrub audit applies its key allowlist to only five of the bundle's
file classes while the plan (and the script's own docstring) claim every file, every key; and the
0.1.1 changelog headline describes the cluster-scoping feature that section 27 removed, while
recording none of the range's actual features. Three Low: `collect-testdata` runs the whole PVE
topology read pass twice against §16.2's "one planning run's worth" claim; §2.3's handler-placement
paragraph says the opposite of what was built, and `--log-level` quietly bypasses the mandatory
audit-trail floor that plan and manual say only `--quiet` escapes; and `validate_corpus.py`
implements only one of §16.6's five promised invariant assertions and neither MILP-agreement check.
One Low on three §16.3 bundle promises never built (no `extra_selector` manifest flag, no PVE/
Prometheus version strings, no metric-name canonicalization), and two Info.

A **sixteenth pass** (section 31) verifies the X-01..X-10 fixes (recorded as section 30): all ten
are real — every reproduction from the fifteenth pass re-runs clean, and X-07's partial fix is the
honest shape its resolution claims. Seven new findings (Y-01..Y-07) come out of the fix range
itself, all Low or Info: the two halves of X-02's fix contradict each other in composition (the
scrub audit's new `host='…'` backstop flags the collector's own `host='<redacted>'` sentinel, so
the first real transport-failure bundle can never pass the corpus gate — reproduced end to end);
the skip-reason fix makes the committed `expected.json` files environment-dependent (an
ortools-less `validate_corpus.py --check` now exits 1 "stale", reproduced on the system toolchain);
and manual 26's corrected query-count example sits beside a sample-points figure that still does
not derive from its own inputs. Four Info: §16.6's check-4 bullet still promises expected-file
fields `plan --json` does not emit; §16.2's "prints the estimate before it fetches anything"
remains unimplemented on the real-capture path; the manifest's new version strings pass through
`_redact_free_text()`, whose vmid substitution can silently rewrite digits inside them; and the
rewritten 0.1.1 changelog bullet says "five" documentation fixes and lists four.

A **seventeenth pass** (section 33) reviews everything after the Y-fixes: releases 0.1.2 and
0.1.3, the `findings.json` label-leak fix found by hand-reading a fresh corpus submission
(`bb9417b`), and the gigapipe step-vs-range workaround (`29213e8`), with the review specifically
tasked to verify that generated `findings.json` files cannot contain confidential log lines.
Eight findings (Z-01..Z-08) are identified: three Medium — **both committed corpus bundles still
carry the exact leak the fix exists to prevent** (`host: 'data001'` in twelve "sample series
labels" messages, green under every gate, because the fix corrected only the uncommitted
`cluster-a` bundle); two further free-text finding shapes (per-disk coverage and cross-metric
consistency warnings) still leak real vmids for any disk outside the managed groups
(`_redact_free_text` substitutes registered vmids only — reproduced); and a capture from a
cluster with `metrics.extra_selector` set stores the operator's raw selector text verbatim in
~19 of its ~25 Prometheus query files (the `rate_expr_map` degenerates to the identity through
tier-1 precedence) while the bundle's nulled config makes it outright unreplayable — both
reproduced end to end. Three Low: the changelog's "no effect on an unaffected backend" is not
literally true for the `quantile_over_time` subquery path; `--estimate` and the
`support.max_series_points` refusal now understate a live capture's stored points by exactly
the workaround factor (2× at the defaults, 13× at `metrics.step: 1h`); and the workaround
landed with zero plan/manual/internals documentation. One Low on 0.1.3 being merged with a red
local `make check` (the in-progress `cluster-a` bundle sitting in the committed-bundle
namespace instead of the `tests/corpus/local/` scratch space), and one Info on §16's promise
that `findings.json` carries `verify-storages` output, which no build has ever implemented.

An **eighteenth pass** (section 35) reviews everything after the Z-fixes: release 0.1.4, plan
§12 (the capacity-spread objective/gate and one-year payback horizon) with its implementation,
four collect/replay/anonymize dogfooding fixes, and the AGENTS.md workflow hardening. Eight
findings (AA-01..AA-08) are identified: one **High** — the CP-SAT backend's new (C7) term is
integer-scaled six orders of magnitude too strongly, so with ortools installed (the default
`auto` cascade's first choice) the solver optimizes data spread with an effective
`delta_capacity_spread` of ~500,000 and returns plans up to 3.2× worse on the specified
objective than moving nothing — reproduced on a committed corpus bundle, and every gate is
blind to it; one Medium — both committed bundles still carry a real group name in their
`manifest.json` call logs, the exact leak shape the range's own last fix corrected for *new*
captures (Z-01's pattern, one identifier kind later); four Low (a wrong §14.6 table cell; the
revised §8.2 ordering rule never implemented; a stale "five terms" documentation cluster plus
the new `plan`/`show-load` JSON fields undocumented; §9.5's new "data:" sample line that no
renderer prints); one Low on process (eight substantive commits straight to `main`, one
knowingly red for two commits); one Info. **Section 36** records the resolution: AA-01..AA-06
and AA-08(a)'s underlying concern are fixed (AA-08(a) itself is refuted as unreachable, more
strongly than the finding claimed); AA-07 is acknowledged without a process change, and
AA-08(b) without a code change, both per the operator's own direction.

A **nineteenth pass** (section 37) reviews everything after the AA-fixes: the section 3.8
pending-change pin, releases 0.1.5 and 0.1.6, four dogfooding fixes (the `move_disk` task-lock
race and `min_wipe_seconds`, the section 10.2 backtest history floor, fixed-point PromQL
durations, day-chunked live range fetches), and the affinity-payback rework — section 5.4's
I/O-weighted `κ` (`w_v`) and `D^big` tiny-disk exemption, section 7.2's `κ·ΔA` benefit term, and
the new section 14.7 `affinity-repair` fixture — nineteen non-merge commits. Seven findings
(AB-01..AB-07) are identified: one Medium — section 14.7's headline claim that its fixture
"discriminates at the verdict" is false: replayed through the repository's own code, the
pre-fix (0.1.6) payback arithmetic **accepts** the fixture at ratio ≈ 438 (its `ΔF` is positive,
not the "negative by a rounding error" the plan prints; the "benefit ≈ −8 load·s" rejection
exists in no state newer than pre-phase-12), and reverts are caught only by the test's
exact-value assertions, not by any verdict flip. Five Low: section 14.7's own `b̄`/gate-spread
arithmetic disagrees with its committed fixture; section 5.4's `ℓ̄ = T_g/|V|` contradicts its own
worked example under the default `affinity_counts_pinned_disks`; a manual-staleness cluster
around the reworked `κ`/payback arithmetic (one worked example verified wrong by execution);
a three-location "pre-section-12" mislabel; and 0.1.6's changelog crediting 0.1.4 with the
capacity-spread term that shipped in 0.1.5. One Info. **Section 38** records the resolution:
AB-01 through AB-05 and AB-07 are fixed (documentation/comment corrections only, no behavioural
change); AB-06 is acknowledged without a change, since the changelog entry it names is already
tagged and released.

A **twentieth pass** (section 39) reviews commit `9b44ba9` — the plan-only redesign of the
free-space policy as per-storage requirements (§5.3.1, §5.3 (C5), the §6 override, the §7.3
repair exemption, §8.1's hard floor, and the §14.8 companion fixture), the first new plan
material since the nineteenth pass. Thirteen findings (AC-01..AC-13) are identified: five
blocking — §7.3's per-move "excluded from both sums" exemption contradicts the plan-level
override the built `payback.py` implements and, as written, changes `fc-tier1`'s recorded
payback numbers (against the commit message's own "every existing fixture stays valid"); the
exclusion semantics is undefined against §7.2's plan-level benefit while §14.8 renders the
override semantics the same commit abandoned; §14.8's unique-optimum claim rests on the (C2)
format rule both solver backends document as not implemented (the as-built optimum is a
one-move repair at objective 1.081, positive benefit, payback-passing); §14.8's capacity gate is
open at 127% against the 25% default, so its "the requirement, and nothing else" isolation
claim is false; and the `hard: null` reversed-order arithmetic drops the very floor the commit
introduced and uses a stale `Z_b`. Five spec gaps (the revert test vs the built "source
presently violating" detection, with its evaluation point unspecified; a migration path for a
per-storage `min_free_bytes` that never existed, with both-set precedence undefined; `hard:
null` overloaded between global and per-storage; `100%` accepted by the grammar and rejected by
`soft_s < C_s`; §8.1's false "relaxation of (C5)" claim, with a dip claim that fails whenever
`r_s > 0`). Three smaller (§9.5's unrendered repair marker; the unaddressed thrash risk of an
unsatisfiable requirement; phase 13's row missing the `min_free_bytes` signature-change sweep).
**Section 40** records the resolution: all thirteen fixed in the plan, and resolving AC-01/AC-02
surfaced one further defect in the commit's own semantics — a per-move trigger misses
**redundant repairs** (fc-tier1's own shape: either move alone repairs, so neither is marked),
which would let payback veto a repairing plan — so the exemption is re-hung on the plan's
*outcome* (final `Σ r_s` strictly below the current assignment's), with the revert test kept as
the per-move output marker; `fc-tier1`'s recorded numbers survive under every semantics
considered, and the plan now says so with the arithmetic.

A **twenty-first pass** (section 41) verifies the AC-01..AC-13 fixes in commit `15a8982` and
re-derives the arithmetic they changed. All thirteen are resolved, and the redundant-repair
defect the author found while resolving AC-01/AC-02 is confirmed independently (`fc-tier1`'s
own two-move plan contains no revert-test repair, so the per-move trigger would have lost its
exemption) — the outcome trigger is the right fix. Six new findings (AD-01..AD-06) are
identified, all in the fix commit's own new material: two Medium (the `min_free_bytes` /
`free_space.soft` both-set rule is self-contradicting and, because a fresh config spells out
`soft: 0`, can silently lower a configured floor on upgrade — `max()` is the fail-safe
resolution; and phase 13's row still misses the `evaluate_plan_payback()` signature change the
plan-level outcome trigger forces, plus two of the four test modules asserting the old flag),
three Low (an arithmetic slip and a stale `Z_b` in the two lines AC-05 rewrote; the exemption
trigger's breadth argued in only one direction), one Info (§7.3's converse example leans on
§8.2's exception 2, which the same commit documents as spec-only). **Section 42** records the
resolution: all six fixed in the plan — AD-01 by folding the deprecated key into its replacement
with `max()` (the fail-safe union) and adding the rule to §11.1's table, AD-02 by naming the
`evaluate_plan_payback()` signature/data-flow change and the two omitted test modules in phase
13's row, AD-03/AD-04 by correcting the two §14.8 lines, AD-05 by arguing the outcome trigger's
breadth in both directions, AD-06 by qualifying the exception-2 scheduling claim.

A **twenty-second pass** (section 43) verifies the AD-01..AD-06 fixes in commit `0feb648` and
re-derives the two §14.8 lines they corrected (`5.0` and `9.3` both check, and the fix
incidentally reconciles a third line that only holds at the corrected `Z_roomy = 0`). All six
are resolved, `make check` is green on the tree and the PDF stamp matches the Markdown, so §42's
verification line holds. Seven new findings (AE-01..AE-07), all in the fix commit's own new
material: three Medium — AD-01's `max()` is specified at the **global** level, where a
percentage has no single value and a per-storage `free_space.soft` still silently lowers the
deprecated floor (the built key is a floor on *every* storage, so taking the `max()` per storage
fixes both); that rule landed in §11.1's table, whose preamble says every row is a hard error
and **never** a warning-and-continue; and phase 13's artefact sweep still misses the two shipped
docs that document the flag being replaced (`docs/manual/27-plan.md`'s `--json` field list,
`docs/internals/96-payback.md`'s normative statement of the exemption) plus the example config
AD-01's own rationale now leans on — three Low (two further sweep gaps, the unpinned meaning of
"final assignment", and the deprecated key inheriting the new `soft_s < C_s` startup error) and
one Info (the outcome trigger is a strict *subset* of both §6's override and today's
`has_reserve_override`, which is a stronger and more useful claim than the "same condition" the
paragraph makes). **Section 44** records the resolution: all seven fixed in the plan — AE-01 by
taking the `max()` per storage after percent conversion (matching what `min_free_bytes` means in
the built code, and making the percentage case well defined), AE-02 by moving the both-set rule
out of §11.1's hard-error table into a new warn-and-continue resolution list, AE-03/AE-04 by
replacing phase 13's enumerated sweep with the two greps (`git grep -l resolves_reserve_violation`,
`git grep -l evaluate_plan_payback`) and naming the shipped docs, the corpus bundles, the fifth
call site and the example config, AE-05 by pinning "final assignment" to the R-02 scheduled state
and naming the `reserve_statuses` source for the threaded sums, AE-06 by exempting the folded
deprecated value from the `soft_s < C_s` startup error (warn and report as the unfixable shortfall
it always was), AE-07 by stating the strict-subset property in place of the "same condition"
claim.

A **twenty-third pass** (section 45) verifies the AE-01..AE-07 fixes in commit `2622e6b`. All
seven are resolved: the per-storage fold matches what the built key means (`reserve.py:143`,
`schedule.py:147`), both greps were re-run and their recorded file lists are exact, the trigger
is pinned to the scheduled assignment, and AE-07's strict-subset property holds as a proof.
`make check` is green and the PDF stamp matches. Six new findings (AF-01..AF-06): three Medium —
`config_schema.json` is missing from phase 13's row, and the schema is deliberately closed
(`additionalProperties: false` throughout), so the whole `free_space` config surface is
unreachable until it changes; the grep-defined sweep was applied to the flag and to one function
signature but *not* to the phase's largest change, the `min_free_bytes` scalar → `soft_s`/`hard_s`
pair and the deprecation of a documented config key (`git grep -l min_free_bytes` returns 30
files, including the manual's own reference section for the key and `.agents/domain-invariants.md`,
which states the invariant in terms of it); and the fold's place in the validate-then-resolve
pipeline is unspecified, leaving `soft_s < C_s` reading as an error on exactly the case the new
resolution list says must warn, and letting a `hard > soft` typo hide behind the deprecated key
until the operator deletes it as instructed — two Low (an absolute "cannot be lowered at all"
claim its own paragraph contradicts for `hard`; the example config's `free_space.hard` needing
to ship as `null`) and one Info (the commit message claims an example-config change the commit
does not contain). **Section 46** records the resolution: five fixed in the plan — AF-01 by
listing `config_schema.json` first in phase 13's row with the shape the closed schema needs,
AF-02 by defining the scalar sweep as a third grep (`git grep -l min_free_bytes`, 30 files
today) and naming `execute.py` and `collect.py` in the module list, AF-03 by pinning the
"validate as written, then fold" order in §5.3.1 and qualifying both §11.1 rows, AF-04 by
scoping the claim to the plan endpoint, AF-05 by fixing the example config's values at
`soft: 0` / `hard: null` — and AF-06 recorded rather than rewritten, because it is a defect in
a commit message already in history.

A **twenty-fourth pass** (section 47) reviews the accumulated `feat/free-space-requirements`
branch as a whole — the full diff of `IMPLEMENTATION_PLAN.md` against `main` (five commits: the
§5.3.1 redesign plus the AC-, AD-, AE- and AF-fix rounds), rather than the individual commits
passes 20-23 already covered. Per §46's own request it re-checks the AF fixes (all six hold),
re-runs the three sweep greps the phase-13 row is defined by (all three recorded lists exact),
and re-derives §5.3.1/§7.3/§8.1/§14.8's arithmetic against the final accumulated text. Eight
findings (AG-01..AG-08) are identified — five Low, three Info, none reopening a design decision.
The headline is a §14.8 parenthetical whose payback arithmetic does not verify: the as-built
one-move repair's benefit is negative (−6.2×10⁴ load·s) and it passes payback only via the same
exemption the sentence implies it does not need.

All eight are **resolved** (section 48), none refuted. Each was re-checked before being accepted
— AG-01 by re-deriving all three §14.8 assignments from §5.3/§5.4/§7.1-7.2 (the table in §48
reproduces every figure the plan states, and the one it does not), AG-04 against
`payback.py:352-354` and `cli.py`'s execution gate, where the composition hole is real in the
built code as well as in the specification. Two are fixed wider than the finding asked: AG-02 had
a second instance of the same stale attribution one paragraph further down, and AG-04's fix
covers the saturation deferral alongside the duration rejection.

---

## 0. Overall assessment

The plan is unusually thorough and, with the caveats below, implementable. Its strongest
properties:

1. **The worked example (section 14) is numerically correct.** I re-derived every value
   (loads, utilizations, reserve breaches, objective values, the β knob demonstration,
   ordering/transient checks, and payback arithmetic) and all of it checks out. This is rare
   and valuable; it gives the implementer an executable acceptance fixture.
2. **The data-acquisition argument (section 3) is the centerpiece and is well reasoned.** The
   decision to use the InfluxDB metric-server path (device as a *label*) rather than the
   OpenTelemetry path (device baked into the *metric name*) is correct for this use case, and
   the rationale is stated precisely.
3. **Safety is treated as a hard invariant, not a preference.** The transient reserve
   invariant (section 8.1), the soft-slack formulation of (C5) so an already-violating start
   stays repairable, and the "reserve is never traded against balance" rule (section 13) are
   the right engineering instincts.
4. **The optimizer/heuristic duality is sound.** Solving per-group, variable fixing for
   eligibility, warm-starting CP-SAT from the current assignment, and requiring the heuristic
   to share the exact feasibility/objective functions with the MILP are all good design.

The plan's main weaknesses are **omissions at the integration and operational boundaries**
rather than errors in the core model: the implementation language is never stated; deployment,
scheduling cadence, logging, and `state.json` schema are unspecified; concurrency interacts
with the transient invariant in a way that is only sketched; and several config knobs
(`min_free_bytes`, `read_factor`/`write_factor`, forecast data ranges) do not appear in the
formal model. None of these are blockers; all are fixable with small additions.

---

## 1. Summary of findings

| ID | Severity | Section | Topic |
|----|----------|---------|-------|
| F-01 | High | §2, whole doc | Implementation language is never stated |
| F-02 | High | §5.3 (C5) | `min_free_bytes` floor absent from the capacity constraint |
| F-03 | High | §4, §3.4 | `read_factor`/`write_factor` asymmetry defined in config but absent from the load formula and PromQL |
| F-04 | High | §10, config | Holt-Winters `seasonal_periods=288` needs 48h of data but `window.lookback=24h`; seasonal-naive needs 7d; the decision window cannot supply either |
| F-05 | High | §8.1, §8.2, §9 | Concurrency (`max_concurrent_migrations`, `max_concurrent_per_storage`) interacts with the transient invariant but the multi-move invariant and `concurrency_ok` are not defined |
| F-06 | Med | §6 | Drift gate is undefined on first run and when `‖ℓ_last‖₁ = 0`; alignment of disk-key union (appeared/disappeared disks) not specified |
| F-07 | Med | §9.2 | "Abort that move and trigger a re-plan" — the re-plan loop is not specified; risk of re-plan thrash mid-execution |
| F-08 | Med | §13, state | `state.json` schema is never defined (lock, last load vector, per-disk/per-storage cooldown timestamps, in-flight UPIDs) |
| F-09 | Med | §7.3 | `saturation_ceiling` "during the mirror" mixes a p95/forecast-bound `u_s` with an instantaneous added load `ω`; `u_during` is not well-defined |
| F-10 | Med | §10 | "Optimizer consumes the upper bound" — how the forecaster's upper bound is derived (especially for the default `quantile`) is unspecified |
| F-11 | Med | §3.5, §9 | Read path is O(VMs) API calls with no concurrency/batching/caching; large clusters may be slow; no rate-limit handling |
| F-12 | Med | §5.3 (C2) | A disk whose storage is in no group, or a storage appearing in two groups, is not handled; needs explicit rule + config validation |
| F-13 | Med | §5.3 (C5), §13 | Finite `reserve_violation_penalty` (1000) technically allows trading reserve for balance; tension with the §13 "never traded" claim |
| F-14 | Med | §5.5 | CP-SAT requires all coefficients integral; the concrete common scaling for continuous quantities (`e_s`, `Z_s`, `r_s`, `t`) and resulting rounding error is not specified |
| F-15 | Low | §1, §13 | "Minimal number of migrations" requirement is reinterpreted as a soft, tunable β penalty (confirmed intentional) — should be documented as an explicit requirement interpretation |
| F-16 | Low | §5.3 (C3) | VM affinity `κ` only counts within-group spread; a VM with disks in multiple groups is never counted as fragmented (acceptable, but undocumented) |
| F-17 | Low | §5.1 | `U^ext` ("foreign volumes") computation is described in prose but not given an exact formula |
| F-18 | Low | §3.5 | `format=qcow2` appears in the write path but format detection/compatibility for the eligibility rule (C2) is not described |
| F-19 | Low | §11, config | Config validation rules are not enumerated (capability_weight>0, non-empty groups, no storage in two groups, metric names non-empty, etc.) |
| F-20 | Low | §9.1, §12 | Deployment target, invocation cadence (cron/systemd), and logging are unspecified; affects `auto` mode design |
| F-21 | Low | §9.4, §12 | §14 fixture is human-readable prose only; no machine-readable fixture file (JSON/YAML) is provided for automated tests |
| F-22 | Low | §11 | No config schema version field; no migration path for future changes |
| F-23 | Info | §3.1, §3.2 | Deep Perl-internal claims (drive- prefix stripping, `instance=scsi0`, OTel name-baking) are plausible and internally consistent but unverified; the plan correctly defers to `verify-metrics` |
| F-24 | Info | §1, App. B | PVE 9.2 ships a built-in dynamic load balancer / Cluster Resource Scheduler; confirmed node-level only (does not balance across storages/FC LUNs); relationship should be documented in §1 |
| F-25 | Info | §3.4 | `quantile_over_time(0.95, (expr)[24h:5m])` subquery is valid PromQL and VictoriaMetrics-compatible; no issue, recorded for the implementer |

---

## 2. Language and technology recommendation (addresses F-01)

`IMPLEMENTATION_PLAN.md` never states the implementation language. The module layout uses `.py`
extensions and names Python-only libraries (OR-Tools CP-SAT, PuLP/CBC, `statsmodels`), and
`.gitignore` is Python-centric, so Python is strongly implied but never declared. This should
be stated explicitly with a version pin.

**Recommendation: Python 3.11+.** Justification:

| Criterion | Python 3.11+ | Go | Rust |
|---|---|---|---|
| OR-Tools CP-SAT (the preferred solver) | First-class (`ortools` wheels) | Cgo bindings only, painful | C bindings, immature |
| CBC via PuLP | Native (`pulp`) | None standard | None standard |
| `statsmodels` (Holt-Winters) | Native | Must reimplement | Must reimplement |
| Prometheus / HTTP client | `prometheus-api-client`, `requests` | Excellent stdlib | Good (`reqwest`) |
| YAML config + units | `pyyaml`/`ruamel` | Fine | Fine |
| Single-binary deployment | Not native (needs venv or PyInstaller/Nuitka) | Native | Native |
| Ops-team maintainability on a PVE host | High (PVE ships Python; staff know it) | Medium | Low |

The solver and forecasting libraries are the deciding factor: OR-Tools CP-SAT and statsmodels
have no usable equivalent in Go or Rust without significant reimplementation, and the plan
explicitly makes CP-SAT the *preferred* backend and Holt-Winters a required (if optional)
forecaster. A Python venv (or a Nuitka/PyInstaller-frozen binary) deployed to a management host
is the pragmatic choice. Go would only win if single-binary, no-runtime deployment were a hard
requirement — but the plan never makes that a requirement, and the heuristic fallback already
provides a dependency-free path for constrained environments.

**Concrete additions to the plan:**
- State "Python 3.11+" in section 2.
- Specify a `pyproject.toml` with pinned dependencies: `ortools>=9`, `pulp>=2.7` (CBC wheel),
  `statsmodels>=0.14`, `prometheus-api-client`, `requests`, `pyyaml`/`ruamel.yaml`,
  `jsonschema` (for config validation).
- Specify the test stack: `pytest`, `pytest-xdist` (independent per-group tests), and a
  machine-readable fixture (see F-21).
- Specify the deployment target explicitly (see F-20): a management host with network access
  to the PVE API (8006) and Prometheus, invoked via systemd timer / cron.

A Go port of the *heuristic-only* path would be a reasonable future option for an agent that
runs on the PVE hosts themselves, but that is out of scope for the first implementation.

---

## 3. Detailed findings

### F-01 — Implementation language never stated (High)
**Where:** section 2, whole document.
**Issue:** No language or version is declared; it is only implied by `.py` module names and
Python library references.
**Recommendation:** See section 2 above. Add an explicit "Implementation: Python 3.11+" line
and a dependency manifest to the plan.

### F-02 — `min_free_bytes` floor absent from (C5) (High)
**Where:** §5.3 (C5); config `snapshot_reserve.min_free_bytes`.
**Issue:** The config defines a flat free-space floor (`min_free_bytes`, "whichever is larger"),
but (C5) only models the `f_s · Z_s` term:
```
Σ_d z_d·x_{d,s} + U^ext + f_s·Z_s ≤ C_s + r_s
```
The floor never appears. An implementer following the formula literally would ignore it.
**Recommendation:** Replace the reserve term with `max(f_s·Z_s, min_free_bytes_s)` and note
that `max` of a continuous variable and a constant is linearizable with two constraints
(`R_s ≥ f_s·Z_s` and `R_s ≥ min_free_bytes_s`, then use `R_s` in (C5)). The transient
invariant in §8.1 must use the same `max`.

### F-03 — `read_factor`/`write_factor` absent from the load model (High)
**Where:** §4 load formula; §3.4 PromQL; config `load_weights.read_factor`/`write_factor`.
**Issue:** The config defines read/write asymmetry "applied within ops and bytes," but the §4
formula `ℓ_d = w_t·î_d + w_o·ô_d + w_b·b̂_d` treats reads and writes symmetrically, and the
§3.4 PromQL sums `rate(rd_*) + rate(wr_*)` with equal weight. There is no place where
`read_factor`/`write_factor` are applied, so the knob is currently dead configuration.
**Recommendation:** Decide and document where asymmetry is applied. Two clean options:
  - (a) In PromQL: `read_factor·rate(rd_X) + write_factor·rate(wr_X)` inside each `sum by`.
  - (b) In `loadmodel.py`: pull read and write series separately and combine with the factors
    engine-side (keeps PromQL simpler and the factors testable in isolation).
Option (b) is preferable because it keeps the factors in the tested engine rather than in
deployed PromQL strings, and because it also cleanly applies to the iotime term if desired.
Update §4's formula and the config comment to match.

### F-04 — Forecast data range vs. decision window (High)
**Where:** §10; config `window.lookback=24h`, `window.seasonal_lookback_days=7`,
`forecast.holt_winters.seasonal_periods=288`.
**Issue:** There are two latent inconsistencies:
  - Holt-Winters requires "at least 2×seasonal_periods samples." With `seasonal_periods=288`
    (24h at 5m step) that is 576 samples = 48h, but the default decision window is 24h. With the
    default window, Holt-Winters can **never** satisfy its minimum and will always fall back
    to `quantile`. The minimum-data rule is correct, but the defaults make the feature
    unreachable.
  - Seasonal-naive "compares the same hour-of-day over the last `seasonal_lookback_days`" (7),
    which needs 7 days of range data, also far outside the 24h decision window.
**Recommendation:** Make forecasters own their data acquisition. Specify that `metrics.py`
must support pulling an arbitrary range via `query_range` (not limited to `window.lookback`),
and that each forecaster declares the range it needs:
  - `quantile`: `window.lookback` (24h).
  - `seasonal_naive`: `max(window.lookback, seasonal_lookback_days)` (7d).
  - `holt_winters`: `max(window.lookback, 2·seasonal_periods·step)` (48h).
Document that enabling `seasonal_naive`/`holt_winters` requires Prometheus to retain that much
history. Alternatively, raise the default `lookback` when a seasonal model is selected, and
emit a config-validation error when the window is too short for the chosen forecaster.

### F-05 — Concurrency vs. the transient invariant (High)
**Where:** §8.1, §8.2, §9; config `max_concurrent_migrations`, `max_concurrent_per_storage`.
**Issue:** §8.1 states the transient invariant for a *single* in-flight move:
```
used_b + z_d + f_b·max(Z_b, z_d) ≤ C_b
```
But config permits `max_concurrent_migrations > 1` and `max_concurrent_per_storage > 1`. With
multiple moves in flight simultaneously, the target storage `b` must satisfy the reserve for
the **sum** of all in-flight disks landing on it at once, and the source relief does not occur
until each completes. §8.2 references `concurrency_ok(state, m)` but never defines it, and §9.2
describes a strictly sequential poll-then-next loop that implies concurrency = 1.
**Recommendation:**
  - Generalize the transient invariant to a *set* of in-flight moves `M`:
    ```
    used_b + Σ_{m∈M : dst(m)=b} z_{disk(m)} + f_b·max(Z_b, max_{m∈M:dst(m)=b} z_{disk(m)}) ≤ C_b
    ```
  - Define `concurrency_ok(state, m)` as: adding `m` to the current in-flight set keeps the
    generalized invariant on every storage, respects `max_concurrent_migrations` (global),
    `max_concurrent_per_storage` (per-storage, both as source and target), and any cooldown.
  - Reconcile §9.2 (sequential) with concurrency: either default `max_concurrent_migrations=1`
    (already the config default) and document that >1 requires the generalized invariant, or
    make §9.2 explicitly launch up to the cap and poll all in-flight UPIDs each cycle.
  - Note that with `max_concurrent_per_storage=1`, two moves targeting the same storage are
    serialized automatically, which is the common safe configuration.

### F-06 — Drift gate edge cases (Med)
**Where:** §6.
**Issue:** `‖ℓ_now − ℓ_last‖₁ / ‖ℓ_last‖₁` is undefined on the first run (no `ℓ_last`) and when
`‖ℓ_last‖₁ = 0` (all loads zero). The "appeared/disappeared disks count their full load as
drift" rule needs the two vectors aligned over the **union** of disk keys, with missing entries
treated as 0; this alignment is not specified.
**Recommendation:** Specify: on first run, skip the drift gate and proceed to the imbalance
gate. Treat `‖ℓ_last‖₁ = 0` as "always drifted" (i.e., proceed). Define alignment over the
union of disk keys present in either vector, with absent disks treated as load 0 in the
opposing vector. State that the drift vector is computed over the group's current movable
disk set union the last-balance movable disk set.

### F-07 — Re-plan loop during execution (Med)
**Where:** §9.2 ("mismatch → abort that move and trigger a re-plan").
**Issue:** Re-planning mid-execution is invoked but not defined. Does a re-plan re-run the
full pipeline (gates, solver, payback, ordering)? Is the already-executed prefix of the plan
treated as the new current state? Is there a bound on re-plan attempts to prevent a loop in a
churning cluster?
**Recommendation:** Specify a re-plan protocol: (1) on a per-move state mismatch, abort the
remaining plan, mark the executed moves as done in `state.json`, and re-invoke the whole
pipeline from the new current state; (2) cap re-plan attempts per run (e.g., 3) and degrade
to "report and stop" if exceeded; (3) in `auto` mode, ensure a re-plan still respects the
remaining time window. Document that re-plan is the expected, normal path, not an error.

### F-08 — `state.json` schema undefined (Med)
**Where:** §13; references throughout.
**Issue:** `state.json` is referenced for the advisory lock, last executed load vector,
per-disk cooldown, per-storage cooldown, and in-flight UPIDs, but its schema is never given.
**Recommendation:** Specify a versioned schema, e.g.:
```json
{
  "schema_version": 1,
  "lock": {"pid": int, "acquired_at": iso8601},
  "last_balance": {"at": iso8601, "load_vector": {"<group>:<vmid>:<device>": float}},
  "cooldowns": {
    "disk": {"<group>:<vmid>:<device>": iso8601_last_moved},
    "storage": {"<group>:<storage>": iso8601_last_involved}
  },
  "inflight_upids": ["UPID...", ...],
  "staged_disks": ["<group>:<vmid>:<device>"]
}
```
Also specify the lock mechanism (recommend `fcntl.LOCK_EX` on the file, with a stale-lock
recovery rule: if the PID in `lock.pid` is not alive, reclaim it) and atomic-write discipline
(write temp + `os.replace`).

### F-09 — `saturation_ceiling` "during the mirror" is ill-defined (Med)
**Where:** §7.3.
**Issue:** The rule defers a move if it "would push `u_src` or `u_dst` above
`saturation_ceiling` *during* the mirror." But `u_s` is a p95/forecast upper bound over the
lookback window, not an instantaneous load. Adding `ω` (in-flight I/O, ≈1.0) to a robust
statistic conflates a window statistic with an instantaneous addition.
**Recommendation:** Define `u_during_s` explicitly, e.g. `u_during_s = u_s_forecast + ω_src`
(or `ω_dst`), where `u_s_forecast` is the forecaster's upper bound for the move's expected
duration, and the ceiling check is `u_during_s ≤ saturation_ceiling`. Document that this is a
best-effort guard, not a hard physical limit, and that `max_single_move_duration` is the hard
per-move bound.

### F-10 — Forecaster "upper bound" derivation unspecified (Med)
**Where:** §10.
**Issue:** "The optimizer consumes the upper bound, not the point estimate." The `Forecaster`
protocol returns a point estimate and an upper bound, but how the upper bound is derived is
not defined — especially for the default `quantile`, where the point estimate *is* p95. Is the
upper bound p95 (same as point) or a higher quantile (p99)?
**Recommendation:** Specify per implementation:
  - `quantile`: upper bound = the same p95 (so point == upper bound; the optimizer consumes
    p95). Or introduce a separate `upper_quantile` (e.g., 0.99) for the bound.
  - `seasonal_naive`: upper bound = p95 across the same-hour-of-day samples (point = median or
    p50).
  - `holt_winters`: upper bound = point + z·σ from the fitted residuals (z=2), or a prediction
    interval.
Make the relationship between `window.quantile`, the point estimate, and the upper bound
explicit so the optimizer's input is unambiguous.

### F-11 — Read path is O(VMs) with no concurrency/caching (Med)
**Where:** §3.5, §9.
**Issue:** Per-VM disk config requires `GET /nodes/{node}/qemu/{vmid}/config` for every VM —
O(N) requests, plus per-storage `/status` and `/content`. For a few hundred VMs this is slow
and load-bearing for every run and every pre-move re-validation. No batching, concurrency,
caching, or rate-limit handling is discussed.
**Recommendation:** Specify a bounded-concurrency read phase (e.g., a thread pool of 8-16) for
the per-VM config fetches, with a short per-request timeout; cache topology within a single
run (the pre-move re-validation in §9.2 must bypass the cache for the specific VM/storage
being moved, but can reuse the rest). Document expected API call counts. Note that PVE has no
batch config endpoint, so concurrency is the only lever.

### F-12 — Ungrouped and multi-group storages (Med)
**Where:** §5.3 (C2), §11.
**Issue:** If a disk's current storage `σ₀(d)` is in no configured group, it has no eligible
targets and is effectively immovable; if a storage appears in two groups, a disk's group is
ambiguous. Neither case is handled or validated.
**Recommendation:** Add config validation: each storage may appear in at most one group
(error otherwise). Disks whose storage is in no group are excluded and pinned to current
(contributing to `U^ext` of their storage), and reported in `show-load`/`explain` as
"ungrouped, not managed."

### F-13 — Finite `reserve_violation_penalty` vs. "never traded" (Med)
**Where:** §5.3 (C5), §13.
**Issue:** §13 states "the reserve constraint is never traded against balance," but (C5) uses
a finite `P = reserve_violation_penalty = 1000`. With finite P, a sufficiently large imbalance
reduction could in principle outweigh a small reserve violation in the objective. In practice
P=1000 dominates the normalized objective (imbalance terms are O(number of storages)), so it
is *effectively* hard, but not *provably* hard.
**Recommendation:** Either (a) keep P finite and reword §13 to "the reserve is effectively
hard; the soft slack exists solely to keep already-violating starts feasible and is driven to
zero whenever physically possible," or (b) split into a hard `≤ C_s` constraint **plus** a
separate, non-objective repair slack used only when the hard model would be infeasible. Option
(a) is simpler and matches the worked example; recommend (a) with the rewording.

### F-14 — CP-SAT integral scaling underspecified (Med)
**Where:** §5.5.
**Issue:** CP-SAT requires all coefficients and variables integral. §5.5 says "scale ℓ by
10⁶ and z to MiB and round," but the objective also contains continuous-derived terms `e_s`
(utilization deviation), `Z_s`, `r_s`, and possibly `t`. Their concrete scaling and the
rounding error introduced (especially for `e_s`, which drives the primary objective) are not
given.
**Recommendation:** Specify a single integer scale factor `K = 10⁶` applied to all
load/utilization quantities (`ℓ`, `e_s`, `u_s`, `t`, `r_s`), and MiB for all sizes (`z_d`,
`Z_s`, capacities). Round after scaling; bound the rounding error (≤ 1e-6 in load units, ≤ 1
MiB in size) and assert it is negligible vs. the objective weights. Note that `β`, `κ` terms
are integer counts and need no scaling, and that `γ` is per-MiB so `γ·z_d` is integral when
`z_d` is MiB and `γ` is rational. Provide the scaled objective explicitly.

### F-15 — "Minimal migrations" reinterpreted as soft β (Low, confirmed intentional)
**Where:** §1, §5.4, §14.3.
**Issue:** The requirement "number of migrations must be minimal" is implemented as a soft,
tunable penalty that is traded off against imbalance (β=0.25 → 3 moves, β=0.50 → 2 moves in
the fixture). This is a reinterpretation, not a strict minimum.
**Recommendation:** Confirm and document this as an explicit requirement interpretation in
§1 or §15's traceability table: "'minimal' is implemented as a tunable preference (β) that
balances move count against imbalance reduction, demonstrated in §14.3." (Confirmed with the
author as intended.)

### F-16 — `κ` only counts within-group spread (Low)
**Where:** §5.3 (C3), §5.4.
**Issue:** The problem is solved per-group, so `y_{v,s}` and the `κ` term only count a VM's
spread across storages *within one group*. A VM with disks in two different groups is never
counted as fragmented. This is a reasonable consequence of per-group decomposition but is
undocumented.
**Recommendation:** Add one sentence to §5.4 noting that `κ` measures within-group
fragmentation only, and that cross-group disk placement is by definition immutable
(a disk never leaves its group), so cross-group spread is not a meaningful penalty.

### F-17 — `U^ext` formula not given (Low)
**Where:** §5.1, §13 (`count_foreign_volumes`).
**Issue:** `U^ext` is "bytes on `s` consumed by volumes DRS does not manage," described in
prose, but the exact computation (sum of which volumes, from which endpoint, with what owner
filter) is not given.
**Recommendation:** Specify: `U^ext_s = Σ_{vol ∈ /storage/s/content} size(vol)` for every
volume whose `(vmid, device)` is not in the current movable disk set `D` of `s`'s group
(includes templates, ISOs, orphaned volumes, and disks of excluded/ungrouped VMs). Note that
orphaned target volumes from prior failed moves (§9.3) are counted here until removed, which
is the intended behavior.

### F-18 — Disk format compatibility in eligibility (Low)
**Where:** §3.5, §5.3 (C2).
**Issue:** The write path mentions `[format=qcow2]`, and (C2) excludes a storage that "cannot
hold the disk's format," but how the source disk's format is detected and how target format
compatibility is decided is not described.
**Recommendation:** Specify: detect source format from the VM config (e.g., raw on LVM,
qcow2 on directory/zfs); for shared LVM the format is raw and `move_disk` defaults to raw on
the target; (C2) fixes `x_{d,s}=0` when `s`'s `content`/type cannot store the disk's format.
Note that format conversion (raw→qcow2) is out of scope and should be disabled by default.

### F-19 — Config validation rules not enumerated (Low)
**Where:** §11.
**Issue:** `config.py` "loads/validates YAML" but the validation rules are not listed.
**Recommendation:** Enumerate at least: `capability_weight > 0`; each group non-empty; each
storage in at most one group; `reserve_factor ≥ 0`; `0 ≤ drift_threshold, imbalance_threshold
≤ 1`; `quantile ∈ (0,1)`; `min_coverage ∈ (0,1]`; metric names non-empty; labels non-empty and
distinct; `rate_window ≥ 4×` the (configurable) push interval; `payback_ratio > 0`;
`saturation_ceiling ∈ (0,1]`; time-window `start < end` (or crosses midnight explicitly);
`window.lookback` long enough for the selected forecaster (see F-04). Validate with
`jsonschema` against a generated schema.

### F-20 — Deployment, cadence, logging unspecified (Low)
**Where:** §9.1, §12.
**Issue:** Where the engine runs, how often it is invoked in `auto` mode, and how it logs are
not specified.
**Recommendation:** Specify: runs on a management host (not necessarily a PVE node) with
network access to the PVE API and Prometheus; invoked by a systemd timer or cron (e.g., every
15-30 min); `time_windows` constrain when *moves* execute, not when the engine is invoked (the
engine may plan outside the window and execute within it). Specify logging: structured logs
(JSON) to a file and optionally syslog, with levels, including every gate decision, every move
issued and its UPID, and every abort/re-plan. This matters for unattended `auto` operation.

### F-21 — No machine-readable fixture (Low)
**Where:** §14, §12.
**Issue:** §14 is an excellent acceptance fixture but exists only as prose; an implementer
must transcribe it, risking transcription error.
**Recommendation:** Add `tests/fixtures/fc-tier1.yaml` (and a JSON variant of the expected
two-move and three-move plans) so tests can assert exact numbers. Include both β variants.

### F-22 — No config schema version (Low)
**Where:** §11.
**Issue:** No `schema_version` field; future config changes have no migration path.
**Recommendation:** Add `schema_version: 1` at the top of the config and have `config.py`
reject unknown major versions with a clear message.

### F-23 — Deep PVE Perl-internal claims unverified (Info)
**Where:** §3.1, §3.2.
**Issue:** The plan states specific Perl-internal behavior: `vmstatus(undef, 1)` with `full=1`
issuing QMP `query-blockstats`; the `drive-` prefix stripping so the device is `scsi0`; the
`InfluxDB.pm` flattening that puts the device in an `instance` tag; and the OpenTelemetry
plugin baking the device into the metric *name* via `_convert_node_metrics_recursive`. These
are the load-bearing facts for the entire data path. Web search did not independently confirm
the exact field/tag names (and some search results appeared unreliable).
**Recommendation:** These are plausible and internally consistent, and the plan correctly
mandates `drs verify-metrics` as the validation gate before any reliance. Treat §3.1/§3.2 as
*claims to be confirmed by `verify-metrics` against the live system*, not as verified facts.
Recommend the implementer run `verify-metrics` first against the actual PVE 9.2 + Telegraf
deployment and record the confirmed metric/label names before building anything else. If the
OTel name-baking claim is wrong, the "InfluxDB path is strictly superior" conclusion still
holds (device-as-label is the right design regardless), so the recommendation is robust to that
uncertainty.

### F-24 — Relationship to the PVE 9.2 built-in balancer (Info)
**Where:** §1.
**Issue:** PVE 9.2 (released 2026-05-21) ships a built-in dynamic load balancer / Cluster
Resource Scheduler. Per the author, it migrates VMs across hypervisors (nodes) only and does
not balance across storages or underlying FC LUNs — so it is complementary to this project,
not duplicative. This relationship is not stated in the plan.
**Recommendation:** Add a sentence to §1 (Non-goals or Operating assumptions) noting that the
PVE 9.2 built-in CRS handles node-level VM placement and explicitly does *not* perform
cross-storage disk balancing, which is the niche this tool fills. Also note an interaction
risk: the built-in CRS may live-migrate a VM between nodes during a Storage-DRS plan; §9.2
already re-fetches the node before each move, which mitigates this — reference that mitigation
here.

### F-25 — PromQL subquery validity (Info, no action)
**Where:** §3.4.
**Note:** `quantile_over_time(0.95, ( <expr> )[24h:5m])` is valid PromQL subquery syntax and is
supported by VictoriaMetrics. `rate()` over counter resets and `sum by (vmid, device)`
collapsing `nodename` are correct for a VM that live-migrated between nodes. No issue; recorded
so the implementer does not second-guess the query shape.

---

## 4. Cross-cutting recommendations

1. **Add an explicit "Implementation" subsection** to §2 covering: language (Python 3.11+),
   dependency manifest, deployment target, invocation cadence, and logging. These are all
   currently implied and should be explicit (F-01, F-20).
2. **Reconcile every config knob with the formal model.** Audit `config/drs.example.yaml`
   against §4-§9 and ensure every knob appears in exactly one formula: `min_free_bytes` (F-02),
   `read_factor`/`write_factor` (F-03), `max_concurrent_*` (F-05), `saturation_ceiling` (F-09).
   A knob with no formula is a bug waiting to happen.
3. **Specify the forecast data contract.** Let forecasters declare their required range and
   have `metrics.py` serve it (F-04, F-10).
4. **Generalize the transient invariant to sets of in-flight moves** and define
   `concurrency_ok` precisely (F-05).
5. **Provide a machine-readable fixture** for §14 and assert against it in CI (F-21).
6. **Specify `state.json`** schema, lock, and atomic writes (F-08).

---

## 5. Open questions for the author

These were put to the author and resolved during this review; recorded here for the
implementer.

1. **Built-in balancer overlap (resolved).** The PVE 9.2 CRS is node-level only; this project is
   complementary. Document the relationship (F-24).
2. **Language (resolved).** Author delegated the choice; this review recommends Python 3.11+
   (§2/F-01).
3. **"Minimal migrations" semantics (resolved).** The soft β penalty is intentional; document
   it as an explicit interpretation (F-15).

No further questions block the review. The remaining items are recommendations the implementer
should fold into the plan before or during implementation.

---

## 6. Second-pass review of the updated plan

The plan grew from 890 to 1305 lines. `config/drs.example.yaml` grew from 166 to 198 lines.
Two fixture files were added: `tests/fixtures/fc-tier1.yaml` (input) and
`tests/fixtures/fc-tier1.expected.json` (expected derivations). This section records the
resolution status of every original finding and presents new findings found in the updated
material.

### 6.1 Resolution of original findings

All 25 original findings (F-01..F-25) have been addressed. Summary:

| ID | Status | How resolved |
|----|--------|--------------|
| F-01 | Resolved | §2.1 states "Language: Python 3.11+" with dependency table, deployment, cadence, logging |
| F-02 | Resolved | §5.3 (C5) now has `R_s ≥ f_s·Z_s` and `R_s ≥ min_free_bytes_s`; linearization explained |
| F-03 | Resolved | §4 now has `raw_X(d) = ρ·rd_X + ω·wr_X` applied engine-side; §3.4 fetches read/write separately (six queries); config updated |
| F-04 | Resolved | §10.1: each forecaster declares `required_range()`; `metrics.py` serves arbitrary range; §11.1 validates `lookback ≥ required_range()` |
| F-05 | Resolved | §8.1 generalized invariant over in-flight set `M`; `concurrency_ok` defined with 5 conditions; §9.2 handles concurrent polling |
| F-06 | Resolved | §6: vector alignment over union of keys; degenerate-cases table; `ℓ_last` recorded only after executed migrations |
| F-07 | Resolved | §9.2: full 5-step re-plan protocol; `max_replans_per_run` (default 3); time-window inheritance |
| F-08 | Resolved | §11.2: versioned `state.json` schema; `fcntl.LOCK_EX`; stale-lock recovery; atomic writes; `inflight_upids` discipline |
| F-09 | Resolved | §7.3: `u_during(s) = û_s(duration_d) + Σω` defined explicitly; noted as best-effort |
| F-10 | Resolved | §10.1 table: `quantile` p95/p99, `seasonal_naive` median/p95, `holt_winters` point+z·σ; `upper_quantile` added to config |
| F-11 | Resolved | §3.5: bounded thread pool (8–16); per-run topology cache; cache-bypass for pre-move re-validation; expected call count |
| F-12 | Resolved | §5.3 (C2): ungrouped disks pinned, counted in `U^ext`, reported; §11.1 validates "no storage in two groups" |
| F-13 | Resolved | §5.3: two approaches — lexicographic (preferred, provably correct) and single-stage big-M (simpler); §13 restated precisely with the bound |
| F-14 | Resolved | §5.5: scaling table (K=10⁶ for load, MiB for size); pre-multiply for `c_s`; scaled objective given; rounding-error assertion |
| F-15 | Resolved | §1: "Requirement interpretation: minimal number of migrations" subsection added |
| F-16 | Resolved | §5.4: "κ measures within-group fragmentation only" with explanation |
| F-17 | Resolved | §5.1.1: explicit `U^ext` formula and composition |
| F-18 | Resolved | §3.5: "Disk format" paragraph — detect from `/content`, preserve source format, conversion out of scope |
| F-19 | Resolved | §11.1: full validation table (18 rules) |
| F-20 | Resolved | §2.1: deployment target, cadence (systemd timer, 15–30 min), structured JSON logging |
| F-21 | Resolved | `tests/fixtures/fc-tier1.yaml` + `fc-tier1.expected.json` added; expected values generated by exhaustive enumeration |
| F-22 | Resolved | `schema_version: 1` in config; §11 rejects unknown major versions |
| F-23 | Updated | §3.1 "Verification status" paragraph: Perl claims read from pve-manager/qemu-server source, operator confirmed empirically; Telegraf naming still deferred to `verify-metrics` |
| F-24 | Resolved | §1: "Relationship to the PVE 9.2 Dynamic Load Balancer" subsection; interaction risk noted |
| F-25 | No action | Still valid; no change needed |

### 6.2 New findings summary

| ID | Severity | Section | Topic |
|----|----------|---------|-------|
| N-01 | High | §5.5 | CP-SAT scaling silently zeroes the γ (bytes-migrated) term at default weight |
| N-02 | Med | §14, fixtures | Fixture input YAML omits `beta_move_count`; the beta sweep is only in the expected file |
| N-03 | Med | §14, fixtures | Fixture expected file doesn't test ordering or post-plan reserve status |
| N-04 | Low | config vs §14 | Config example has san-c `capability_weight: 0.5`; fixture and §14 use `1.0` — same names, different values |
| N-05 | Low | §7.3 | `saturation_ceiling · c_s` ambiguous: unclear whether `û_s` is `L_s` (load) or `u_s` (normalized utilization) |
| N-06 | Low | §11.1 | Validation requires `rate_window ≥ 4 × pvestatd push interval` but the push interval is not in config |
| N-07 | Low | §5.5 | `round(K / c_s)` introduces a capability-weight rounding error for non-binary `c_s` (e.g., 0.7) |

### 6.3 New findings — detail

#### N-01 — CP-SAT scaling silently zeroes the γ term at default weight (High)
**Where:** §5.5.
**Issue:** The plan specifies `γ_scaled = round(γ · K / 2²⁰)` per MiB, with `K = 10⁶`. At the
default `γ = 0.05/TiB`:
```
γ_scaled = round(0.05 × 10⁶ / 1,048,576) = round(0.0477) = 0
```
Verified by computation. The bytes-migrated penalty vanishes entirely in CP-SAT, making it
produce plans that ignore disk size when choosing which disks to move — a behavioral
divergence from CBC and the heuristic, which use continuous coefficients and preserve γ.
The §14 fixture's β-knob demonstration relies on `γ·0.5 TiB = 0.025` being non-zero; with
CP-SAT, that term would be zero, and the acceptance/rejection arithmetic at β=0.25 vs 0.50
would change (the third move's cost becomes `−0.400 + 0.250 + 0 = −0.125` vs
`−0.400 + 0.500 + 0 = +0.0.125` — still accepts/rejects, but for a different reason, and only
because γ is small enough that the sign doesn't flip in this case).

The minimum γ that survives rounding is `2²⁰ / (2·K) ≈ 0.524/TiB` — ten times the default.
Any operator using CP-SAT with the default `γ = 0.05` gets no bytes-migrated penalty at all,
silently.
**Recommendation:** Either (a) raise `K` so that `γ·K/2²⁰ ≥ 0.5` at the default γ (requires
`K ≥ 2²⁰/(2·0.05) ≈ 10.5 × 10⁶`, so `K = 10⁷` suffices and keeps numbers manageable); or (b)
express `z_d` in a coarser unit (e.g., centi-TiB, `2²⁰/100`) so `γ_scaled = round(γ·K/100) =
round(500) = 500`; or (c) document the minimum effective γ and emit a config-validation warning
when `γ` is below it and `solver.backend` is `cpsat` or `auto`. Option (a) is simplest: change
`K` to `10⁷` and re-derive the rounding bound. The plan should also add a test that asserts
`γ_scaled > 0` at default weights.

#### N-02 — Fixture input YAML omits `beta_move_count` (Med)
**Where:** `tests/fixtures/fc-tier1.yaml`, `tests/fixtures/fc-tier1.expected.json`.
**Issue:** The input fixture's `objective` block has `alpha_spread`, `gamma_move_bytes_per_tib`,
and `kappa_vm_affinity`, but no `beta_move_count`. The expected file has two cases with
`beta_move_count: 0.25` and `0.50`. An implementer reading the fixture must infer from the
expected file that beta is swept — the input doesn't say so. The fixture contract (what the
test harness feeds in, what it checks) is implicit.
**Recommendation:** Either add a `beta_values: [0.25, 0.50]` list to the input fixture's
`objective` block and have the test iterate over it, or add a comment to the expected file
naming the input convention. The current structure works but is under-documented for a
fixture meant to be consumed by an AI agent.

#### N-03 — Fixture doesn't test ordering or post-plan reserve status (Med)
**Where:** `tests/fixtures/fc-tier1.expected.json`.
**Issue:** The `expected_moves` arrays are alphabetically sorted by disk key, not in execution
order. §14.4 specifies `102:scsi0` first (it repairs the reserve violation), but the fixture
lists `101:scsi1` first. An implementer testing the scheduler (§8) against this fixture cannot
verify the ordering. The fixture also lacks post-plan reserve-violation status — the expected
file has `expected_final_loads` but not the `used + f·Z_s` values or the `violates_reserve`
flag for the final state. An implementer testing the transient invariant (§8.1) must derive
these separately.
**Recommendation:** Add an `expected_order` field to each case (an ordered list of move keys)
and an `expected_final_reserve` section mirroring the `initial` block (per-storage `used_tib`,
`largest_tib`, `required_tib`, `violates_reserve`). The §14.4 transient checks (5.0 ≤ 8.0,
4.5 ≤ 8.0, 5.0 ≤ 8.0) should be assertable from the fixture.

#### N-04 — Config example vs fixture discrepancy on san-c capability_weight (Low)
**Where:** `config/drs.example.yaml` vs `tests/fixtures/fc-tier1.yaml` and §14.
**Issue:** The config example has `san-c` with `capability_weight: 0.5` under group `fc-tier1`;
the fixture and §14.1 state "all `capability_weight = 1.0`". Same group name, same storage
names, different values. An implementer who assumes the config example matches the fixture
will get wrong numbers. The config is an illustrative example (showing the 0.5 feature), not
the fixture, but the reuse of names is confusing.
**Recommendation:** Either (a) set `san-c` to `capability_weight: 1.0` in the config example to
match the fixture (and show the 0.5 feature on a different storage, e.g., `san-d` in `fc-tier2`),
or (b) add a comment to the config: "Note: the §14 fixture uses capability_weight 1.0 for all
three; the 0.5 here is an unrelated illustration of the knob."

#### N-05 — `saturation_ceiling · c_s` ambiguity in §7.3 (Low)
**Where:** §7.3.
**Issue:** The check is `u_during(src) ≤ saturation_ceiling · c_src`. If `û_s` is the
forecaster's upper bound in *load* units (`L_s`), then `L_s + ω ≤ 0.85 · c_s` is correct and
equivalent to `u_s + ω/c_s ≤ 0.85`. If `û_s` is the *normalized* utilization (`u_s = L_s/c_s`),
then the check should be `u_s ≤ saturation_ceiling` without the `c_s` multiplication.
Multiplying by `c_s` when `u_during` is already normalized would set a *lower* ceiling for less
capable storages (e.g., 0.425 for `c=0.5`), double-penalizing them. The plan doesn't state
which `û_s` is.
**Recommendation:** Add one sentence: "`û_s` is the forecaster's upper bound on `L_s` (load,
not normalized utilization), so the check is `L_s + ω ≤ saturation_ceiling · c_s`, equivalently
`u_s + ω/c_s ≤ saturation_ceiling`." This makes the `c_s` factor's role clear.

#### N-06 — pvestatd push interval not in config (Low)
**Where:** §11.1.
**Issue:** The validation rule `rate_window ≥ 4 × pvestatd push interval` references a PVE-side
setting that is not in the config. The tool cannot validate this without knowing the push
interval. The config has no `pvestatd_interval` field.
**Recommendation:** Either add a `metrics.pvestatd_push_interval` config field (default `60s`,
matching PVE's default) and validate against it, or reword the rule to "the operator must
ensure `rate_window ≥ 4×` the pvestatd push interval; `verify-metrics` should report the
observed resolution and warn if `rate_window` is too short." The former is more automatable.

#### N-07 — `round(K / c_s)` capability-weight rounding (Low)
**Where:** §5.5.
**Issue:** "Scale each storage's load by `round(K / c_s)`" introduces a rounding error when
`c_s` is not a clean divisor of `K`. E.g., `c_s = 0.7` gives `round(10⁶/0.7) = 1,428,571` vs
the true `1,428,571.43`, a relative error of ~3×10⁻⁷. This causes a slight capability-weighting
error at the optimum — a storage assigned 0.7× capability gets 0.6999998× in CP-SAT. Negligible
for balance, but it means CP-SAT and CBC may produce slightly different assignments for
non-binary `c_s`, which complicates the "backends are directly comparable" requirement.
**Recommendation:** Document the bound: `|round(K/c_s) - K/c_s| / (K/c_s) ≤ c_s/(2K)`, which is
< 10⁻⁶ for any `c_s ≥ 1` and `K = 10⁶`. Note that this is below the solver's `mip_gap` (0.02)
and therefore cannot change the selected plan. No action needed beyond the documentation.

### 6.4 Fixture verification

The fixture's expected values were independently verified:

- **Objective values:** 3-move (β=0.25): `1.0×1.133333 + 0.25×3 + 0.05×3.0 + 0.5×1 = 2.533333` ✓.
  2-move (β=0.50): `1.0×1.533333 + 0.50×2 + 0.05×2.5 + 0.5×1 = 3.158333` ✓.
- **Payback:** duration/cost/benefit/ratio for both moves and the rejected archive disk all
  match to the precision given (see Appendix A).
- **β-knob consistency:** at β=0.25 the 3-move objective (2.533333) beats the 2-move
  (2.658333); at β=0.50 the 2-move (3.158333) beats the 3-move (3.283333). The crossover is
  correct.
- **Exhaustive-enumeration claim:** the plan states expectations were generated by enumerating
  all `3⁶ = 729` assignments. Spot-checks of alternative assignments (e.g., 102:scsi0→san-b
  instead of →san-c) confirm the stated optima are lower. The claim is plausible; full
  re-enumeration was not performed.

The fixture is a sound acceptance test. The gaps in N-02 and N-03 are about what it *doesn't*
test, not about wrong values.

---

## 7. Third-pass review of the updated plan

The plan grew from 1305 to 1721 lines. `config/drs.example.yaml` grew from 198 to 279 lines.
The expected fixture grew from 97 to 188 lines and the input fixture from 69 to 80 lines. A
new file `tests/fixtures/generate_fc_tier1.py` (208 lines) was added. Two further commits
beyond the N-01..N-07 fixes introduced substantial new material: all-bus disk enumeration
(§3.5/§3.6), snapshot exclusion policy (§3.7), load-model rescale back to in-flight-I/O units
(§4), computed big-M penalty (§5.3), CP-SAT coefficient folding (§5.5), saferemove wipe
accounting (§7.1, §9.3), saturation-load redesign with `N_s` (§7.3), draining state (§8.2),
VM lock handling (§9.3), and fixture improvements including ordering and post-plan reserve
status. This section records the resolution status of every N-finding and presents new
findings.

### 7.1 Resolution of second-pass findings

All 7 second-pass findings (N-01..N-07) have been addressed. Summary:

| ID | Status | How resolved |
|----|--------|--------------|
| N-01 | Resolved | §5.5 rewritten: instead of factoring γ out as a standalone per-MiB integer, each disk's coefficient is folded at full precision: `round(γ·W·K·z_d^TiB)`. The γ-trap is explicitly documented with the worked example showing `round(0.05·10⁶/2²⁰)=0` and why raising K doesn't fix it. An assertion at model-build time checks every non-zero weight produces a non-zero integer coefficient. Verified: `round(0.05·10⁴·10⁶·0.5) = 2.5×10⁸`, exact. |
| N-02 | Resolved | `beta_values: [0.25, 0.5]` added to the input fixture's `objective` block with a comment: "Swept by the harness; one cases[] entry in the expected file per value." The fixture contract is now explicit. |
| N-03 | Resolved | `expected_order` field added to each case (ordered list with per-move transient checks: `transient_target_used_tib`, `transient_reserve_basis_tib`, `transient_required_tib`, `capacity_tib`, `ok`). `expected_final_reserve` section added mirroring the `initial` block (per-storage `used_tib`, `largest_tib`, `required_tib`, `violates_reserve`). Both verified against §14.4. |
| N-04 | Resolved | Config example `fc-tier1` now has `san-c: capability_weight: 1.0`, matching the fixture. The 0.5 feature is illustrated on `san-e` in `fc-tier2`. A comment notes the alignment with the fixture. |
| N-05 | Resolved | §7.3 rewritten: `û_s` is now explicitly `L̂_s` (load, not normalized utilization). The check is `L_during(s) ≤ saturation_ceiling · N_s` where `N_s` is the storage's physical saturation load, not `c_s`. The old `saturation_ceiling · c_s` form is called out as the original defect. |
| N-06 | Resolved | `metrics.pvestatd_push_interval: 60s` added to config. `verify-metrics` (§3.3 step 6) now measures observed sample spacing and errors if it disagrees with config by >20%. §11.1 validation rule references the config field. |
| N-07 | Resolved | §5.5 now folds both `K` and `c_s` into a single per-(disk,storage) coefficient `a_{d,s} = round(K·ℓ_d/c_s)`, with error bound `≤ 0.5` (i.e. `≤ 5×10⁻⁷` in load units), independent of `c_s`. The old `round(K/c_s)` approach is explicitly called out as making CP-SAT and CBC disagree. |

### 7.2 New findings summary

| ID | Severity | Section | Topic |
|----|----------|---------|-------|
| M-01 | Low | §5.5, generator | Generator uses single-stage big-M (P=1000), not the preferred lexicographic solve; fixture doesn't test lexicographic |
| M-02 | Low | §7.1, §14.5 | §14.5 payback example silently assumes saferemove off, but the config default is `account_saferemove_wipe: true`; a naïve implementer will get different numbers |
| M-03 | Low | §8.2 | `draining` state holds source charged for the whole wipe, but the transient invariant (§8.1) doesn't model the wipe's own I/O load on the source |
| M-04 | Low | §3.6, §13 | `tpmstate0` online move was "verified on PVE 9.2" but the plan also says PVE may not use drive-mirror for it; the transient invariant assumption (both storages occupied) is unverified for swtpm |
| M-05 | Info | §4, §14 | Load-model rescale is correct but the §14 fixture's `ℓ_d` values are now reinterpreted as raw in-flight I/O (not normalized); old Appendix A verification still holds but the units description changed |
| M-06 | Info | §5.3 | Big-M `P_min` is computed from `T_g` (group absolute load), which changes per run; the plan correctly says to compute at model-build time, but the config `reserve_violation_penalty: 1000` as a floor may need to be much larger for small-`T_g` groups |

### 7.3 New findings — detail

#### M-01 — Generator tests big-M, not the preferred lexicographic solve (Low)
**Where:** `tests/fixtures/generate_fc_tier1.py`, §5.3.
**Issue:** The generator's `objective()` function includes `P_RESERVE * slack` as a
single-stage big-M term with `P=1000`. The plan states the lexicographic two-stage solve
(option 1) is the preferred default and option 2 (big-M) needs a computed `P`. The fixture
therefore validates the big-M path with a fixed `P=1000`, not the lexicographic path. For
this fixture both approaches give the same answer because `P=1000` is dominant here (the
initial violation is 0.5 TiB, so `P·0.5 = 500 >> 21.6` max non-reserve objective). But an
implementer who implements only the lexicographic solve has no fixture to test it against, and
an implementer who uses big-M with `P=1000` on a different group where the violation is
sub-GiB may get a different answer than lexicographic (the plan's own §5.3 computation shows
`P_min ≈ 2.27×10⁷` for mebibyte granularity, so `P=1000` is 4 orders of magnitude too small
there).
**Recommendation:** Either (a) add a second fixture or a second mode in the generator that
validates the lexicographic solve (minimize `Σr_s` first, then fix it and minimize the rest),
or (b) document that the fixture only tests big-M and that a lexicographic test must be added
when that path is implemented. This is low-severity because both paths agree on the fixture,
but it's a test-coverage gap.

#### M-02 — §14.5 payback silently assumes saferemove off (Low)
**Where:** §14.5, config `migration.account_saferemove_wipe: true`.
**Issue:** §14.5 now states "and **`saferemove` off on all three storages** so
`duration_wipe_d = 0`". This is necessary because the new §7.1 wipe accounting would otherwise
make the payback numbers much larger (a 1.5 TiB disk at 10 MiB/s wipe takes ~44h, dwarfing the
2.2h mirror). But the config default is `account_saferemove_wipe: true`. An implementer who
runs the fixture with the default config values will get payback numbers that don't match
unless they notice the saferemove-off assumption. The fixture's `migration` block doesn't
include `account_saferemove_wipe: false` or any saferemove-throughput field.
**Recommendation:** Add `account_saferemove_wipe: false` (or `saferemove_throughput: 0` per
storage) to the fixture's `migration` block so the fixture is self-contained and an
implementer doesn't have to infer the assumption from the prose. Alternatively, add
`saferemove_throughput_tib_per_sec: 0` per storage in the fixture's `group.storages` to make
the wipe-off assumption explicit in the data.

#### M-03 — Transient invariant doesn't model the wipe's I/O load (Low)
**Where:** §8.1, §8.2, §7.1.
**Issue:** The `draining` state (§8.2) keeps the source charged for `z_d` bytes until the
volume is observed gone, which is correct for the *capacity* invariant. But the wipe itself
is a sequential write at `saferemove_throughput` (§7.1) that generates I/O on the source
storage. §7.1 charges this as `duration_wipe_d · ω_src` in the cost model, but §8.1's
transient invariant — which checks *capacity* (`used + reserve ≤ C`) — does not check
*load* during the drain. A storage that is already near its `N_s` saturation load could be
pushed over by a wipe running in the background while the next move is being scheduled. The
`concurrency_ok` predicate (§8.1 condition 4) checks the §7.3 saturation guard for in-flight
*mirrors*, but a draining wipe is no longer in the in-flight set `M` (the task has reported
OK), so its load is not counted.
**Recommendation:** Either (a) include draining moves in the saturation check: a move stays
in a "load-in-flight" set (distinct from the capacity in-flight set `M`) until `done`, and
`concurrency_ok` sums `ω_src` for all draining moves at that storage; or (b) document that
the wipe load is best-effort and is not modeled in the transient invariant, and that
`cooldown_per_storage` (which §9.3 sizes against the wipe time) is the mitigation. Option (b)
is simpler and may be sufficient given that the wipe is a low-throughput sequential operation
(10 MiB/s default), but the plan should state this explicitly.

#### M-04 — tpmstate0 transient invariant assumption unverified for swtpm (Low)
**Where:** §3.6, §13.
**Issue:** §3.6 states `tpmstate0` is movable online on PVE 9.2 (verified empirically) but
also says "PVE may not use the `drive-mirror` path for it, since `swtpm` rather than QEMU
owns the state." The transient invariant (§8.1) assumes "the volume exists on **both**
storages — the mirror target is fully allocated before the switchover." If `swtpm` moves
state by a different mechanism (e.g., copy-then-delete, or atomic rename), the both-storages
assumption may not hold, and the conservative invariant may over-reserve during the move.
This is safe (over-reserving never causes a reserve breach), but it could make a
`tpmstate0` move unnecessarily infeasible on a tight storage.
**Recommendation:** The plan already says "no part of the model needs to know which mechanism
PVE picked" and the conservative assumption is the safe direction. Consider adding one
sentence: "If swtpm does not use drive-mirror, the both-storages invariant is conservative
(over-reserves) but never unsafe; a `tpmstate0` move that fails the transient check on a
tight storage should be treated as any other infeasible move — deferred, not forced."

#### M-05 — Load-model rescale reinterprets §14 fixture units (Info)
**Where:** §4, §14, Appendix A.
**Issue:** §4 was rewritten to rescale `ℓ_d` back onto the in-flight-I/O scale (`Σℓ_d = T_g`,
not 1.0). The §14 fixture's loads (3.0, 1.0, 2.5, etc.) are now explicitly described as "in
average in-flight I/O requests, *not* normalized to sum to one." This is a change in
*description*, not in values — the numbers are the same, but what they *mean* is now
different. The Appendix A verification in this review was performed under the old
description (normalized to sum to 1) but still holds because the values and ratios are
unchanged; only the unit label shifted.
**Recommendation:** No action needed. The change is correct and the payback comparison in §7
is now on a sounder footing (`ω = 1.0` is commensurable with `ℓ` because both are in
in-flight I/O requests). Recorded so the implementer knows the Appendix A verification
remains valid despite the units reinterpretation.

#### M-06 — Big-M `P_min` depends on `T_g`, which varies per run (Info)
**Where:** §5.3.
**Issue:** The computed big-M penalty `P_min = U_obj / ε_r` depends on `T_g` (the group's
total absolute load), which changes every run as workloads shift. On a quiet group with
`T_g = 0.1`, `U_obj` is tiny and `P_min` is small; on a busy group with `T_g = 20`, `P_min`
is large. The config `reserve_violation_penalty: 1000` is a *floor*, and the engine uses
`max(configured, P_min)`. This is correct, but it means the same config file produces
different effective `P` values on different groups and different runs. An operator who
sets `reserve_violation_penalty: 5000` thinking it's the actual penalty may not realize the
engine is silently raising it to `P_min` on busy groups.
**Recommendation:** The plan already says "logs a warning when it had to raise it," which is
the right mitigation. Consider also logging the computed `P_min` and the `T_g` it was
derived from, so an operator seeing the warning can verify the computation. No structural
change needed.

### 7.4 Fixture and generator verification

The fixture and generator were independently verified:

- **Generator freshness:** `python3 generate_fc_tier1.py --check` exits 0 — the committed
  `fc-tier1.expected.json` is current.
- **Objective values:** both β cases match the generator's exhaustive enumeration (verified
  in §6.4 and re-confirmed).
- **Ordering:** `expected_order` correctly places `102:scsi0` first (repairs the reserve
  violation) in both cases. Transient checks match §14.4: 5.0≤8.0, 4.5≤8.0, 5.0≤8.0.
- **Post-plan reserve:** `expected_final_reserve` for both cases shows no violations, matching
  §14.3's final-state table.
- **CP-SAT coefficient folding:** verified `round(0.05·10⁴·10⁶·0.5) = 2.5×10⁸` — the γ term is
  now exact, not zero. The N-01 defect is fixed.
- **Big-M bound:** `P_min = 21.625 / 2⁻²⁰ ≈ 2.27×10⁷`, matching the plan's §5.3 computation.
- **Generator covers the fixture's objective formula exactly** (`alpha·E + beta·moves +
  gamma·bytes + kappa·frag + P·slack`), including the `P·slack` term. The generator does not
  model the lexicographic two-stage solve (M-01).
- **Generator does not model `affinity_counts_pinned_disks`** or the `D^mov` distinction,
  but the fixture has no pinned disks so `D^mov = D` and the computation is correct.

---

## 8. Fourth-pass review of the updated plan

The plan grew from 1721 to 1842 lines. `config/drs.example.yaml` grew from 279 to 285 lines
(one new field: `migration.wipe_load_weight`). The generator was renamed from
`generate_fc_tier1.py` to `generate_expected.py` and rewritten (208→502 lines) to handle
multiple fixtures, the lexicographic solve path, and the `ω_wipe` cost model. A new fixture
pair `reserve-tradeoff.yaml`/`.expected.json` was added. `AGENTS.md`, `.agents/`, `LICENSE`
(AGPL-3.0), `pyproject.toml`, `Makefile`, and `.pre-commit-config.yaml` were added as project
tooling. This section records the resolution of every M-finding and presents new findings.

### 8.1 Resolution of third-pass findings

All 6 third-pass findings (M-01..M-06) have been addressed. Summary:

| ID | Status | How resolved |
|----|--------|--------------|
| M-01 | Resolved | New `reserve-tradeoff` fixture (§14.6) with a group where lexicographic and big-M provably disagree. Generator rewritten with `best_lexicographic()`, `big_m_agreement_threshold()`, and `computed_p_min()` functions. The expected file records both solve paths, the threshold P, and whether they agree at the configured P. The `big_m_undersized_p_demo` (P=5) shows big-M making the wrong choice and the resulting plan being unschedulable. |
| M-02 | Resolved | `fc-tier1.yaml` now has `saferemove: false` per storage and `account_saferemove_wipe: false` in the `migration` block. The expected file has an `assumptions` object echoing this. Per-move records carry `duration_mirror_seconds` and `duration_wipe_seconds` separately. §14.5 prose explicitly explains the assumption is in the data, not just the prose. |
| M-03 | Resolved | §7.3 now defines a state-dependent `ω_role(m,s)` table: `mirroring` charges `ω_src`/`ω_dst`, `draining` charges `ω_wipe`/0, `done` charges 0/0. §8.1 condition 4 sums `ω_role` over all moves in `M` including draining. New config field `migration.wipe_load_weight` (default 1.0) controls `ω_wipe`. The generator's `cost()` function implements the same split. |
| M-04 | Resolved | §3.6 now states: "if swtpm does not use drive-mirror, the both-storages assumption over-reserves during the move. Over-reserving can never cause a reserve breach, so it is safe; the only cost is that a tpmstate0 move onto a nearly-full storage may fail the transient check... Treat that exactly like any other infeasible move — defer it, never force it." |
| M-05 | Resolved (no action) | The units reinterpretation is now fully documented in §4 and §14.1. Appendix A verification in this review remains valid as noted. |
| M-06 | Resolved | §5.3 now requires logging `P_configured`, `P_min`, `P_used`, and the four inputs (`T_g`, `|D|`, `Σz_d`, `|V|·(|S|−1)`) plus `ε_r`, and repeating them in `drs explain`. The text explicitly addresses the "operator sets 5000 and sees 2.3×10⁷" scenario. |

### 8.2 New findings summary

| ID | Severity | Section | Topic |
|----|----------|---------|-------|
| K-01 | Low | generator, §14.5 | Payback `benefit_load_seconds` mixes exact `E_before` with rounded `E_after`; fixture says 3951360.2, prose says 3951360.0 |
| K-02 | Low | §7.1, §7.3, config | `ω_wipe` renamed to `wipe_load_weight` in config but the plan text uses `ω_wipe` and `migration.wipe_load_weight` inconsistently |

### 8.3 New findings — detail

#### K-01 — Payback benefit mixes exact and rounded E (Low)
**Where:** `tests/fixtures/generate_expected.py` `payback()` function, §14.5.
**Issue:** The generator's `payback()` function computes `delta_e = E_of(f, f.current) -
case["expected_E_after"]`, where `case["expected_E_after"]` is already rounded to 6 decimal
places. This mixes an exact `E_before` (8.0666666...) with a rounded `E_after` (1.533333),
producing `delta_e = 6.5333336...` instead of the exact `6.5333333...`. The benefit becomes
`3951360.2` instead of the exact `3951360.0` that the §14.5 prose states. The ratio is
unaffected (150.73 in both cases), so the payback acceptance test passes either way, but an
implementer asserting exact equality against the fixture will see a 0.2 load-seconds
discrepancy with the prose.
**Recommendation:** In the generator's `payback()` function, compute `delta_e` from the exact
assignment rather than from the rounded case value:
```python
# Instead of:
delta_e = E_of(f, f.current) - case["expected_E_after"]
# Use:
two_assign = best_big_m(f, case["beta_move_count"], f.big_m_p)[0]
delta_e = E_of(f, f.current) - E_of(f, two_assign)
```
Or simply pass the exact `E_after` into `payback()` alongside the rounded one. This is a
cosmetic fix — the 5×10⁻⁸ relative error has no physical consequence — but it eliminates a
prose-vs-fixture discrepancy that an implementer would have to explain.

#### K-02 — `ω_wipe` / `wipe_load_weight` naming inconsistency (Low)
**Where:** §7.1, §7.3, §15.1, `config/drs.example.yaml`.
**Issue:** The plan text in §7.1 and §7.3 refers to the wipe load weight as `ω_wipe`, and
§15.1 maps it to `migration.wipe_load_weight`. The config file has `wipe_load_weight: 1.0`
under `migration:`. This is consistent. However, the fixture's `migration` block uses
`omega_wipe: 1.0` (not `wipe_load_weight`), and the generator reads it as
`f.migration.get("omega_wipe", 1.0)`. So the fixture uses a different field name than the
config for the same quantity. An implementer who reads the config field name from
`drs.example.yaml` and then looks at the fixture will see two different names for the same
knob.
**Recommendation:** Rename `omega_wipe` to `wipe_load_weight` in the fixture YAML files
(`fc-tier1.yaml` and `reserve-tradeoff.yaml`) and in the generator's `migration.get()` call, to
match the config field name. This is purely a naming consistency issue; the values and
semantics are identical.

### 8.4 Fixture and generator verification

The updated fixtures and generator were independently verified:

- **Generator freshness:** `python3 tests/fixtures/generate_expected.py --check` exits 0 —
  both `fc-tier1.expected.json` and `reserve-tradeoff.expected.json` are current.
- **fc-tier1 numbers:** all objective values, ordering, transient checks, and post-plan
  reserve status match the §14 prose and the previous verification (§6.4, §7.4). The new
  `lexicographic` block correctly records that both paths agree (`agrees_with_big_m_at_configured_p:
  true`) and that the threshold is negative (`-3.273333`), meaning no P≥0 can make them
  disagree on this fixture.
- **reserve-tradeoff numbers:** all values verified by hand:
  - Both on roomy: E=10.0, slack=0, obj_nr=10.0 ✓
  - One to cramped: E=0.0, slack=1.0, obj_nr=0.30 ✓
  - Big-M P=1000: stays (1000.30 > 10.0) → 0 moves ✓
  - Big-M P=5: moves (5.30 < 10.0) → 1 move ✓
  - Flip threshold: P = 10.0 − 0.30 = 9.7 ✓
  - Transient check: 3.0 + 1.0 + 2×1.0 = 6.0 > 5.0 → deadlock ✓
  - P_min = 21.6 × 2²⁰ = 22649241.6 ✓
  - Lexicographic: min_slack=0, then min obj_nr=10.0 → 0 moves ✓
- **Cost model:** `ω_wipe` now separates the wipe load from the mirror load in both the cost
  function (§7.1) and the saturation guard (§7.3 `ω_role` table). Verified that with
  `saferemove: false` the payback numbers are unchanged.
- **Generator architecture:** the rewritten `generate_expected.py` is a significant
  improvement — it handles both fixtures, both solve paths, the threshold computation, and
  the deadlock detection in a single 502-line file with clean separation between state
  evaluation, objective computation, and ordering. The `Fixture` dataclass and the
  `all_assignments()` iterator make the exhaustive enumeration readable and trustworthy.

---

## 9. Fifth-pass review of the updated plan

Commit `78d9573` ("Address fourth-pass review findings K-01, K-02") made targeted fixes only;
the plan, config, and fixtures changed in three small ways. No new findings.

### 9.1 Resolution of fourth-pass findings

| ID | Status | How resolved |
|----|--------|--------------|
| K-01 | Resolved | `generate_expected.py` `payback()` now takes an `e_after` parameter (the exact, unrounded `E_of(f, a)`), passed via a `_exact_E_after` field on the case dict (stripped before writing with a `_`-prefix filter). `benefit_load_seconds` is now `3951360.0`, matching the §14.5 prose exactly. The `ratio` is unchanged at `150.73`. Verified: `generate_expected.py --check` exits 0. |
| K-02 | Resolved | Both fixture YAMLs renamed `omega_src`→`source_load_weight`, `omega_dst`→`target_load_weight`, `omega_wipe`→`wipe_load_weight` to match `config/drs.example.yaml`. The generator's `cost()` and `build()` functions updated to read the new names. The expected files' `assumptions` block renamed `omega_wipe`→`wipe_load_weight`. A field-naming convention comment was added to both fixture YAMLs documenting that fixture knobs mirror config names, with two deliberate exceptions (`payback_horizon_seconds` as integer vs config's `7d`, and `beta_values` as a list vs config's single `beta_move_count`). |

The plan also fixed two stale references in §11 and §15.1's traceability tables:
`gamma_move_bytes` → `gamma_move_bytes_per_tib` to match the actual config field name, and the
config itself was corrected from `gamma_move_bytes` to `gamma_move_bytes_per_tib`.

### 9.2 Verification

- `python3 tests/fixtures/generate_expected.py --check` exits 0 — both expected files current.
- `fc-tier1.expected.json` `benefit_load_seconds` = `3951360.0` (was `3951360.2`), matching §14.5.
- Fixture migration keys: `source_load_weight`, `target_load_weight`, `wipe_load_weight` —
  all match config field names.
- Fixture objective keys: `gamma_move_bytes_per_tib` — matches config.
- No changes to the plan's §5.5 CP-SAT scaling, §5.3 lexicographic/big-M, §7.1 cost model,
  §7.3 saturation guard, §8.1 transient invariant, or §14.6 reserve-tradeoff fixture.

### 9.3 Assessment

The plan and its fixtures are clean. Across five review passes, 40 findings (F-01..F-25,
N-01..N-07, M-01..M-06, K-01..K-02) have been raised and all are resolved. The remaining
open items are zero. The plan is ready for implementation.

---

## 10. Sixth-pass review of the updated plan

Commits `06fe472..3db38d3` added substantial new infrastructure: the `pve-storage-drs` naming
convention, full Debian packaging (`debian/` with control, rules, changelog, copyright, Salsa
CI), two GitHub Actions workflows (`tests.yml`, `debian-package.yml`), the PDF paper pipeline
(`docs/paper/header.tex`, `filters.lua`, `metadata.yaml`, `tools/check_paper_log.py`), the
documentation policy (AGENTS.md §8, `.agents/documentation.md`), the manpage
(`man/pve-storage-drs.1.md`), config-on-pmxcfs with resolution order and env-var support
(§11), the state path move to `/var/lib/pve-storage-drs/state.json`, global CLI options
(§11.3), Makefile `SYSTEM_TOOLS=1` support, `.codecov.yml`, and `.pre-commit-config.yaml`
updates.

The new material is well-structured and the packaging is thorough: the autopkgtest design
correctly catches optional-dependency import-at-module-level bugs, the Salsa no-network sbuild
proves the package builds from trixie alone, the PDF freshness stamp mechanism is sound, and
the `check_paper_log.py` script catches the two classes of silent LaTeX damage (missing
characters, overfull boxes). The manpage follows the AGENTS.md §8.4 section order exactly.
Five new findings, three of them Medium.

### 10.1 Summary of sixth-pass findings

| ID | Severity | Section / File | Topic |
|----|----------|----------------|-------|
| L-01 | Medium | §2.1, pyproject.toml, debian/control | `pulp` classified inconsistently: not marked optional in the plan, but optional in pyproject.toml and Recommends in debian/control |
| L-02 | Medium | §11.3, man/pve-storage-drs.1.md | Direct contradiction: plan says `-v, --quiet`; manpage says `-v, --verbose` |
| L-03 | Medium | .github/workflows/, debian/control | CBC/PuLP primary solver path is not exercised in any CI pipeline |
| L-04 | Low | §11.3 | `--mode auto` overriding a `confirm` config is not called out as a warning |
| L-05 | Info | debian/changelog | Uses `bernd@debian.org` while the rest of the repo uses `bernd@bzed.de` |

### 10.2 L-01 — `pulp` is not marked optional in the plan, but is optional in the packaging

**Severity:** Medium
**Files:** `IMPLEMENTATION_PLAN.md` §2.1, `pyproject.toml`, `debian/control`

The plan §2.1 dependency table lists `pulp` alongside hard dependencies (`requests`,
`ruamel.yaml`, `jsonschema`) without an "optional" qualifier:

```
| `pulp` | MILP via CBC — **the packaged solver path** | `python3-pulp` 2.7 + `coinor-cbc` 2.10 |
```

`ortools` is marked "optional and unpackaged" in the same table, but `pulp` gets no such
marking. The "optional extras" sentence below the table names only ortools and statsmodels:

> Make `ortools` and `statsmodels` **optional extras**. The tool must run, plan and execute
> with only `requests` + `ruamel.yaml` + `jsonschema` installed, falling back to the heuristic
> solver and the quantile forecaster.

But the "must run with only requests + ruamel.yaml + jsonschema" requirement makes `pulp`
functionally optional too: the heuristic path works without it. The packaging artifacts
confirm this — `pyproject.toml` puts `pulp` under `[project.optional-dependencies] solver`
(the comment there correctly says "ortools and pulp are therefore optional extras, not hard
requirements"), and `debian/control` puts `python3-pulp` under `Recommends:`, not `Depends:`.

The plan text creates an ambiguity: an implementer reading §2.1 in isolation could conclude
`pulp` is a hard dependency (it is listed without "optional", called "the packaged solver
path", and not mentioned in the "optional extras" sentence), while the packaging treats it as
optional. The AGENTS.md §9.1 rule 3 ("not in trixie, and not vendorable — it must be optional")
applies to ortools; pulp *is* in trixie, so the rule does not force it to be optional — yet
the architecture requires it because the heuristic path must work standalone.

**Recommendation:** Mark `pulp` as optional in the plan. Either add it to the "optional
extras" sentence ("Make `ortools`, `pulp`, and `statsmodels` optional extras") or add a note to
the table row (e.g., "optional, but `Recommends` on Debian — the MILP path needs it, the
heuristic does not"). The key point is that the plan, `pyproject.toml`, and `debian/control`
should agree on the classification, and right now the plan is the one that is ambiguous.

### 10.3 L-02 — `-v` means `--quiet` in the plan but `--verbose` in the manpage

**Severity:** Medium
**Files:** `IMPLEMENTATION_PLAN.md` §11.3, `man/pve-storage-drs.1.md`

The plan §11.3 global options table:

```
| `-v`, `--quiet` | normal | Log level; `--quiet` leaves only warnings and errors, for the timer |
```

This binds `-v` as the short form of `--quiet` (reduces verbosity). The plan does not mention
`--verbose` anywhere.

The manpage:

```
**-v**, **--verbose**
: More detail on stderr. Repeatable.

**--quiet**
: Warnings and errors only. Intended for the systemd timer.
```

This binds `-v` as the short form of `--verbose` (increases verbosity) and treats `--quiet`
as a separate, independent option.

These are directly contradictory: `-v` makes the tool quieter in the plan and more verbose in
the manpage. An operator who reads the manpage and then uses `-v` expecting more detail would
get the opposite. The manpage is generated from `man/pve-storage-drs.1.md`, which is a
hand-authored file (not generated from the plan), so there is no mechanical check that keeps
the two in sync yet.

**Recommendation:** Pick one design and align both. The manpage's design (`-v` = verbose,
`--quiet` = quiet, as independent flags) is more conventional and less surprising than the
plan's (`-v` = quiet). If the manpage design is chosen, update §11.3 to list `--verbose`
and `--quiet` as separate options with `-v` as the short form of `--verbose`. If the plan's
design is chosen, fix the manpage. Either way, the `--help` output (generated from argparse)
will be the mechanical source of truth once the CLI exists; until then the two documents must
agree by hand.

### 10.4 L-03 — The CBC/PuLP solver path is not exercised in any CI pipeline

**Severity:** Medium
**Files:** `.github/workflows/tests.yml`, `.github/workflows/debian-package.yml`,
`debian/control`

The plan §2.1 states: "on a Debian install the MILP is solved by **CBC through
`python3-pulp`**." This is the primary solver path on the target platform. However:

- `tests.yml` installs `python3-jsonschema python3-pytest python3-pytest-cov
  python3-pytest-xdist python3-requests python3-ruamel.yaml python3-yaml` — no `python3-pulp`
  or `coinor-cbc`.
- `debian-package.yml` installs build dependencies from `debian/control`, which has
  `python3-pulp` under `Recommends:`, not `Build-Depends`.
- The autopkgtest (`debian/tests/control`) runs with only `Depends: @` — `Recommends` are not
  installed — so the installed-package test also runs without pulp.

This means the CBC/MILP integration will not be tested in any CI pipeline once `optimize.py`
exists. The fixture generator (`generate_expected.py`) is solver-independent (exhaustive
enumeration), so it does not exercise the actual solver. The solver-integration tests that
verify CBC produces the same assignments as the enumeration will need pulp available.

The `tests.yml` "Is there code yet?" probe currently gates on `src/*/*.py`, and the MILP
tests would be among the first things added. Without pulp in the CI install list, those
tests will either fail (if they import pulp unconditionally) or skip (if they guard on
`pytest.importorskip("pulp")`) — and if they skip, the primary solver path on the target
platform is never tested in CI.

**Recommendation:** When the solver module lands, add `python3-pulp` and `coinor-cbc` to
`debian/control` `Build-Depends` with `<!nocheck>` (so `dh_auto_test` has them), and to the
`tests.yml` apt install list. The autopkgtest should continue to run without pulp (it tests
that the tool works with only `Depends`), but the build-time test suite should exercise the
MILP path. This is a forward-looking finding — the infrastructure is already in place to miss
it, so it is worth recording now rather than discovering when the first solver test
mysteriously skips.

### 10.5 L-04 — `--mode auto` on a `confirm` config is not warned

**Severity:** Low
**File:** `IMPLEMENTATION_PLAN.md` §11.3

The plan §11.3 says:

> `--mode` may make a run *safer* without ceremony, but `--mode auto` on a config that says
> `dry-run` is an operator deliberately overriding their own safety setting: log it at
> warning level, naming both values.

This covers `dry-run → auto` (removing both the dry-run barrier and the confirmation
barrier). But it does not mention `confirm → auto`, which also removes a safety barrier
(the per-step confirmation prompt). An operator who set `execution.mode: confirm` in the
config and then runs `--mode auto` is bypassing their own confirmation requirement, which is
the same class of override. The plan only calls out the `dry-run` case.

**Recommendation:** Extend the rule to cover any override that moves to a less safe mode:
log at warning when `--mode` is less safe than the configured mode, not only when the
configured mode is `dry-run`. "Less safe" is defined by the ordering `dry-run < confirm <
auto`, so `confirm → auto` and `dry-run → confirm` are both overrides toward less safe. Or
simply: warn whenever `--mode` is given and it differs from the configured mode, regardless
of direction, since any override is a deliberate act the operator should see in the log.

### 10.6 L-05 — `debian/changelog` uses a different email address

**Severity:** Info
**File:** `debian/changelog`

The changelog entry uses `bernd@debian.org`:

```
-- Bernd Zeimetz <bernd@debian.org>  Fri, 04 Sep 2026 23:30:47 +0200
```

Every other file in the repository — `pyproject.toml` (`authors`), `debian/copyright`
(`Upstream-Contact`), `man/pve-storage-drs.1.md` (`AUTHOR`), all SPDX headers, `AGENTS.md`
section 0 — uses `bernd@bzed.de`. This may be intentional (the `debian.org` address is the
Debian developer address, and some maintainers use it in changelogs by convention), but it is
the only place in the tree that does. Worth noting for consistency; not actionable unless the
maintainer wants uniformity.

### 10.7 Verification

- `python3 tests/fixtures/generate_expected.py --check` exits 0 — both expected files current.
- `sha256sum --check docs/IMPLEMENTATION_PLAN.pdf.sha256` passes — the committed PDF matches
  the committed Markdown.
- The manpage section order (`NAME`, `SYNOPSIS`, `DESCRIPTION`, `COMMANDS`, `OPTIONS`,
  `CONFIGURATION`, `ENVIRONMENT`, `FILES`, `EXIT STATUS`, `SEE ALSO`, `AUTHOR`,
  `COPYRIGHT`) matches AGENTS.md §8.4, with `COMMANDS` and `ENVIRONMENT` added (the §8.4 list
  is a minimum, not a maximum — `COMMANDS` is the manpage convention for subcommand listing
  and `ENVIRONMENT` documents `PVE_STORAGE_DRS_CONFIG` / `PVE_PASSWORD` / `PVE_TOKEN_SECRET`).
  This is correct.
- The `debian/control` `Depends` list (`python3-jsonschema`, `python3-requests`,
  `python3-ruamel.yaml`) matches the `pyproject.toml` `dependencies` list. `Recommends`
  (`python3-pulp`, `coinor-cbc`) and `Suggests` (`python3-statsmodels`) match the optional
  extras. The dependency declarations are consistent with the "must run with only
  requests + ruamel.yaml + jsonschema" requirement — except for the plan's ambiguity about
  pulp (L-01).
- `debian/changelog` version `0.0.1` matches `pyproject.toml` version `0.0.1`.
- The `import-all` autopkgtest correctly walks the package with `pkgutil.walk_packages` and
  catches `BaseException` (not just `Exception`), so a `SystemExit` from a bad import is also
  a failure.
- The Salsa CI config (`debian/.gitlab-ci.yml`) correctly sets `RELEASE: 'trixie'`, disables
  `BLHC` (nothing compiled), `APTLY`, and `BUILD_PACKAGE_ANY` (arch:all only), and leaves
  `SALSA_CI_SBUILD_ARGS` empty with the `--enable-network` fallback commented out.
- The Makefile `SYSTEM_TOOLS=1` path correctly avoids `.venv` for CI, and the `man` target
  does not depend on `$(VENVDEP)`, so `debian/rules`' `$(MAKE) man` works in the build chroot
  without a venv.
- `tools/check_paper_log.py` correctly undoes the 79-column log hard-wrap before pattern
  matching, and treats `SystemExit`-class exceptions as failures in the autopkgtest import
  walker.

### 10.8 Assessment

The packaging, CI, and documentation infrastructure is well-designed and internally
consistent in almost all respects. The autopkgtest-as-dependency-test pattern, the no-network
Salsa build, the PDF freshness stamp, and the `check_paper_log.py` log checker are all the
right mechanisms. The three Medium findings (L-01..L-03) are all in the same area: the
boundary between the plan's dependency classification and the packaging/CI that implements
it. Resolving them is a matter of documentation alignment (L-01, L-02) and a CI install-list
addition when the solver code lands (L-03). None are architectural.

---

## 11. Seventh-pass review of the first implementation

Commits `37c6392..cf532f2` are the transition from design to code: the L-finding fixes
(`aceb5e6`), then phase 1 (config loading, forecasting, CLI skeleton, metrics), phase 2 (PVE
API client, topology, reserve), and the full documentation suite (`docs/internals/*.md`,
`docs/manual/*.md`, `tools/build_paper.sh`). This is the largest single addition to the
repository since the plan itself: ~8300 lines across 60 files, including 2700 lines of tests.

The implementation is high quality. The code follows the plan closely, the frozen-dataclass
style from AGENTS.md is used throughout, optional dependencies (`statsmodels`) are imported
inside the function that needs them (not at module level), every public function has a
docstring referencing the plan section, and the test suite (223 tests, 1 skipped for
`statsmodels`) achieves 98.61% coverage — well above the 85% floor. The `FakeProxmoxResource`
test double correctly replicates `proxmoxer`'s dynamic attribute-chaining protocol. The
documentation cross-reference tests (`test_documentation.py`) enforce that every config
schema key appears in the manual and vice versa, and that every CLI option appears in the
manpage.

### 11.1 Resolution of sixth-pass findings

| ID | Status | How resolved |
|----|--------|--------------|
| L-01 | Resolved | The plan §2.1 table now marks `pulp` as "optional", and the "optional extras" sentence names `pulp` alongside `ortools` and `statsmodels`, with the distinction spelled out: "the packaged solver path" describes which MILP backend a Debian install gets, not that the MILP is mandatory. |
| L-02 | Resolved | Resolved in the manpage's favour: `-v`/`--verbose` and `--quiet` are now separate options in both the plan §11.3 and the manpage, with `-v` meaning more output. The CLI (`cli.py`) implements them correctly as `action="count"` and `action="store_true"` respectively. |
| L-03 | Resolved | `coinor-cbc` and `python3-pulp` are now `Build-Depends` under `<!nocheck>` and in the GitHub Actions install list. The autopkgtest deliberately keeps running without them. Both halves documented in `.agents/packaging.md`. |
| L-04 | Resolved | The warning rule now orders the modes `dry-run < confirm < auto` and warns on any move *up* that order, not only `dry-run -> auto`. `cli.py`'s `apply_mode_override()` implements this correctly using `_MODE_RANK`. |
| L-05 | Refuted | The finding's premise was wrong: the changelog uses `bzed@debian.org` (the Debian developer address), not `bernd@debian.org` as I wrote. The split is now documented in AGENTS.md §0 and `.agents/packaging.md`. |

### 11.2 Summary of seventh-pass findings

| ID | Severity | Section / File | Topic |
|----|----------|----------------|-------|
| P-01 | Medium | §3.5, config.py, pve.py, manual | `proxmox.ticket_refresh_seconds` is a dead config knob — parsed and documented but never passed to proxmoxer |
| P-02 | Medium | §3.5, config.py, topology.py, manual | `proxmox.read_workers` is a dead config knob — documented as the thread pool size but topology.py fetches sequentially |
| P-03 | Low | §3.5, manual/00-installation.md | Manual does not document `VM.Config.Disk` and `VM.Migrate` privileges needed for `move_disk` |

### 11.3 P-01 — `proxmox.ticket_refresh_seconds` is a dead config knob

**Severity:** Medium
**Files:** `config.py:68`, `pve.py`, `docs/manual/10-configuration.md:90`, `config/drs.example.yaml:38`

The plan §3.5 says: "Tickets are valid ~2h; `proxmoxer` refreshes them itself on its own
internal interval when using password auth." The `pve.py` `build_client()` function does not
pass `ticket_refresh_seconds` to `proxmoxer.ProxmoxAPI` — proxmoxer manages its own refresh.

Meanwhile, `ProxmoxConfig.ticket_refresh_seconds` exists as a field, is parsed from the config
file (`config.py:403-404`), is in the JSON schema (`config_schema.json:28`), is documented in
the example config (`config/drs.example.yaml:38` with a comment "PVE tickets last 2h; refresh
well before"), and the manual (`docs/manual/10-configuration.md:90-97`) describes it as "How
often a username/password ticket is refreshed" — as if the operator setting this value
controls the refresh interval.

The manual's description is misleading: the knob does nothing. An operator who sets
`ticket_refresh_seconds: 600` expecting more frequent refresh will get proxmoxer's own
internal interval regardless. The `30-safety-and-status.md` per-command status table is honest
about what commands are implemented, but the configuration reference does not distinguish
between knobs that are wired through and knobs that exist for future use.

**Recommendation:** Either wire `ticket_refresh_seconds` through to proxmoxer (if proxmoxer
exposes a way to configure it — it may not, in which case this is not possible), or remove
the field, the schema entry, the example config line, and the manual entry, and document in
the plan that proxmoxer handles ticket refresh internally and the knob is not needed. If the
field is kept as a placeholder for a future hand-rolled client, mark it clearly in the manual
as "not yet effective; proxmoxer manages its own refresh" — the manual must not describe a
knob as functional when the code ignores it.

### 11.4 P-02 — `proxmox.read_workers` is a dead config knob

**Severity:** Medium
**Files:** `config.py:69`, `topology.py`, `docs/manual/10-configuration.md:99`,
`config/drs.example.yaml:41`

The manual documents `proxmox.read_workers` as: "Size of the bounded thread pool used to
fetch per-VM configuration — `GET /nodes/{node}/qemu/{vmid}/config` has no batch form, so this
is what keeps a several-hundred-VM cluster's topology read from being serial."

But `topology.py`'s `build_topology()` fetches VM configs sequentially in a `for` loop
(`topology.py:448-455`), with no thread pool, no `concurrent.futures`, and no use of
`config.proxmox.read_workers` anywhere. The field is parsed by `config.py` (`config.py:406`)
but never consumed by any module.

The plan §3.5 specifies the concurrent read path and the updated call count formula
(`3 + 2|VMs| + 2|S|`), and the config knob is the right design for when the thread pool is
implemented. But the manual describes it as if it works now. An operator with 500 VMs who sets
`read_workers: 1` expecting serial fetches would get... serial fetches regardless (which is
what happens), but an operator who sets `read_workers: 20` expecting parallelism would also
get serial fetches. The manual's claim "this is what keeps a several-hundred-VM cluster's
topology read from being serial" is currently false.

**Recommendation:** Either implement the concurrent fetch path in `topology.py` (the plan
specifies it), or add a note to the manual entry saying the thread pool is not yet
implemented and `read_workers` has no effect in this build. The `30-safety-and-status.md`
table is the right pattern: be honest about what the code does, not what the plan says it will
do. A config knob that is parsed but silently ignored is exactly the kind of gap
`30-safety-and-status.md` exists to prevent.

### 11.5 P-03 — Manual omits `VM.Config.Disk` and `VM.Migrate` privileges

**Severity:** Low
**Files:** `docs/manual/00-installation.md`, `IMPLEMENTATION_PLAN.md` §3.5

The plan §3.5 says: "move_disk needs nothing beyond that on the storage side (the VM side
needs `VM.Config.Disk` and `VM.Migrate` or equivalent, out of scope for this note). Document
this precisely in the operator manual rather than repeating the more comfortable but wrong
'Audit is enough' claim."

The manual's installation section (`00-installation.md`) documents `Datastore.Allocate`,
`Datastore.Audit`, and `VM.Audit` in detail (including the silent-empty-list failure mode for
Audit-only on `/content`), but does not mention `VM.Config.Disk` or `VM.Migrate` at all. The
requirements section says "permission to call `move_disk`" without specifying what that means
in terms of PVE privileges. An operator setting up the credential today would not know to
grant these VM-level privileges, and would only discover the gap when `apply` is implemented
and fails with a permission error.

Since `apply` (which calls `move_disk`) is not yet implemented, this is forward-looking. But
the manual says "permission to call `move_disk`" in the requirements now, and the plan says
to document it precisely in the operator manual. The `Datastore.Allocate` finding is
documented excellently; the VM-level privileges should get the same treatment, even if only
as a note that these will be needed when `apply` is implemented.

**Recommendation:** Add a section to `00-installation.md` (or a note in the existing
"Setting up the PVE credential" section) naming `VM.Config.Disk` and `VM.Migrate` as the
privileges `move_disk` requires on the VM side, noting they are only needed for `apply` (not
for `verify-metrics`, `show-load`, or `verify-storages`, which only read).

### 11.6 Verification

- `python3 -m pytest`: 223 passed, 1 skipped (statsmodels not installed), 98.61% coverage —
  above the 85% floor. No failures.
- `python3 tests/fixtures/generate_expected.py --check`: exits 0 — both fixture expected
  files current.
- `sha256sum --check docs/IMPLEMENTATION_PLAN.pdf.sha256 docs/internals.pdf.sha256
  docs/pve-storage-drs-manual.pdf.sha256`: all pass — all three committed PDFs match their
  Markdown sources.
- `python3 -m pytest tests/unit/test_documentation.py -v`: 12 passed — every config schema
  key appears in the manual, the manual documents no nonexistent keys, the example config
  validates against the schema, every CLI option appears in the manpage, and the manpage has
  all required sections.
- `__version__` in `__init__.py` (`0.0.1`), `pyproject.toml` (`0.0.1`), and
  `debian/changelog` (`0.0.1`): all agree.
- `proxmoxer` is consistently classified as a hard dependency: `pyproject.toml`
  `dependencies`, `debian/control` `Depends` and `Build-Depends`, and `mypy.overrides`
  (`ignore_missing_imports` for no type stubs). The `pve.py` module-level import is safe
  because `python3-proxmoxer` is in `Depends`, so the autopkgtest's `import-all` will succeed.
- `config_schema.json` is packaged via `[tool.setuptools.package-data]`, so the
  `importlib.resources` load in `config.py` works from the installed package.
- The "Is there code yet?" probes in both GitHub Actions workflows were correctly removed
  now that `src/` exists, and the Makefile `test` target no longer has the "skip if no tests"
  guard.
- `tools/build_paper.sh` is a clean generalization of the previous inline Makefile recipe:
  one shared pandoc+LuaLaTeX pipeline for all three PDFs, with per-document title/subtitle.
- The `docs/manual/30-safety-and-status.md` per-command status table honestly reports which
  commands are implemented and which are not, including the note that `show-load` does not yet
  compute per-disk I/O load (needs `loadmodel.py`).

### 11.7 Assessment

The first implementation is strong. The code matches the plan, the test coverage is
excellent, the documentation cross-reference tests are the right mechanism, and the
honest "not implemented yet" handling in both the CLI and the manual's status table is
exactly the discipline the project's own rules demand. The three findings (P-01..P-03) are
all in the same category: config knobs or privileges that are documented as functional but
are not yet wired through. P-01 and P-02 are Medium because an operator could change a value
and see no effect, which erodes trust in the configuration system; P-03 is Low because
`apply` is not implemented yet, so the missing privileges cannot currently cause a failure.
None are architectural — resolving them is a matter of either implementing the feature or
marking the manual entry as "not yet effective in this build."

---

## 12. Resolution of seventh-pass findings (P-01..P-03)

| ID | Status | How resolved |
|----|--------|--------------|
| P-01 | Resolved | `proxmoxer` 2.x has no constructor argument for a password/ticket auth's refresh interval (`ProxmoxHTTPAuth.renew_age` is a hard-coded `3600` class attribute, confirmed by reading the installed `proxmoxer` 2.3.0 source, not guessed) — this was genuinely "not possible" via `proxmoxer`'s public interface, as the finding's own recommendation anticipated. `pve.py`'s `_apply_ticket_refresh_seconds()` now wires `ticket_refresh_seconds` through anyway by overriding that instance attribute after login (reaching into `api._backend.auth`, undocumented but stable across the installed version; `getattr`/`hasattr`-guarded, a silent no-op for API-token auth or a future `proxmoxer` shape). Going beyond the finding's own ask: `PveClient._call()` now also reauthenticates from scratch and retries once on any `AuthenticationError`, covering the case the operator raised directly — a ticket that expires for reasons external to any call (a long `apply --confirm` wait, a suspended process, a clock jump) where `proxmoxer`'s own lazy renewal, and even a correctly-tuned `renew_age`, cannot help, because the gap between calls is what invalidated it, not the passage of the process's own clock. |
| P-02 | Resolved | `topology.py`'s per-VM fetch (`vm_config`/`vm_snapshots`) now runs across a `concurrent.futures.ThreadPoolExecutor` bounded by `config.proxmox.read_workers`, split into a network-only fetch phase (`_fetch_vm`, run by the pool) and a pure join phase (`_join_vm_disks`, run single-threaded afterward in `ThreadPoolExecutor.map()`'s original order) so `disks_by_group`/`referenced_volids`/`warnings` stay byte-for-byte identical to a fully sequential run regardless of `read_workers` or thread scheduling. `PveClient` is shared across the pool's threads; its new P-01 reauthenticate path takes a lock so concurrently-expiring tickets serialize onto one fresh login rather than stampeding. |
| P-03 | Resolved | `docs/manual/00-installation.md` now names `VM.Config.Disk` and `VM.Migrate` explicitly, in the same "Setting up the PVE credential" section as the datastore privileges, with the same honesty discipline the rest of that section already has: stated as needed only once `apply` executes a move, not for any command implemented today. |

Verification: `python3 -m pytest` — 231 passed, 1 skipped (`statsmodels` not installed), 98.78%
coverage (`pve.py` at 100%, both new lines this round). `make lint typecheck` clean.

---

## 13. Eighth-pass review of phases 3-4

Commits `5994dc1..9a7c270` add phases 3 and 4: `loadmodel.py` (section 4), `gates.py` (section 6),
`heuristic.py` (section 5.4/5.5), plus the P-01/P-02/P-03 fixes and the unused-disk root-cause
documentation. The `reserve.py` and `metrics.py` modules were extended with the
`storage_of` callback and `compute_disk_coverage()` extraction those new modules needed, and
`cli.py`'s `show-load` now computes and displays per-disk/per-storage load and a per-group gate
verdict.

The implementation continues to be high quality. The heuristic's `evaluate_assignment()` is
correctly factored as a pure function shared with the future MILP path, the repair-before-descend
design makes the "reserve is never traded" invariant literal rather than merely well-weighted,
and the test suite cross-checks the heuristic's objective totals against REVIEW.md Appendix A's
hand-derived values to five decimal places (2.533333 / 3.158333). The gates module correctly
implements the three-gate cascade in section 6's order, with the degenerate-case table handled.
The `pve.py` reauthenticate-and-retry-once path is well-designed: the `threading.Lock` prevents
a stampede, the closure over `_trial` in `_repair`'s inner loop avoids the classic late-binding
bug, and the `storage_of` callback on `reserve.py` is the clean extension point the plan's
"identical shape" requirement demands.

### 13.1 Resolution of seventh-pass findings

All three (P-01..P-03) are resolved — see section 12 for the full record.

### 13.2 Summary of eighth-pass findings

| ID | Severity | Section / File | Topic |
|----|----------|----------------|-------|
| Q-01 | Low | §5.4, heuristic.py, config.py | `objective.spread_metric: minmax` is accepted by the schema and documented in the manual but silently ignored by the heuristic — always computes L1 |
| Q-02 | Low | §4, loadmodel.py, cli.py | `compute_group_load` fetches 7 Prometheus queries per group; a multi-group config re-fetches the same unfiltered series N times — acknowledged in internals docs but not in the manual |

### 13.3 Q-01 — `objective.spread_metric: minmax` silently ignored by the heuristic

**Severity:** Low
**Files:** `heuristic.py:157`, `config.py:164`, `config_schema.json:155`,
`docs/manual/10-configuration.md`

The config schema accepts `spread_metric: "l1"` or `"minmax"`. The manual documents both:
"`l1` (sum of each storage's deviation from the group's target utilization) or `minmax` (only
the single hottest storage)." The plan's section 5.4 defines both forms: `e_s` for L1
(`α · Σ e_s`), `t` for minmax. Section 15.1's traceability table maps `objective.spread_metric`
to "§5.3 (C6), L1 vs min–max".

But `heuristic.py`'s `evaluate_assignment()` always computes L1: `spread_e[storage.id] = abs(u_s
- average_utilization)` and `imbalance_term = objective.alpha_spread * sum(spread_e.values())`.
The `objective.spread_metric` field is never read. An operator who sets `spread_metric: minmax`
gets L1 behaviour regardless — the same class of silent-ignoring that P-01 and P-02 identified
for other config knobs.

This is Low rather than Medium because: (a) the default is `l1`, so an operator has to actively
choose `minmax` to be affected; (b) the heuristic is not yet wired into any CLI command, so no
production decision is currently made from this path; (c) the MILP path (`optimize.py`, not yet
written) is where `spread_metric` will matter most, since the CP-SAT/CBC model needs to
construct either the `e_s` variables or the `t` variable depending on it.

**Recommendation:** Either implement the minmax form in `evaluate_assignment()` (it is a
one-line change: `max(spread_e.values())` instead of `sum(spread_e.values())` when
`objective.spread_metric == "minmax"`), or — if the heuristic is intentionally L1-only and
minmax is a future MILP-only option — add a note to the manual's `spread_metric` entry saying
the heuristic always uses L1 and `minmax` only affects the MILP solver (not yet written). The
test suite should assert whichever behaviour is chosen.

### 13.4 Q-02 — Per-group Prometheus query redundancy in multi-group configs

**Severity:** Low
**Files:** `loadmodel.py:194-195`, `cli.py:416-424`, `docs/internals/70-loadmodel.md:30-37`

`compute_group_load()` calls `compute_disk_coverage()` (1 range query) and
`_fetch_all_raw_quantities()` (6 instant queries) — 7 Prometheus queries per group. Since
`show-load` calls it once per group in a loop (`cli.py:416`), a config with N groups makes 7N
queries. The coverage query and all six raw-quantity queries are unfiltered by group (they use
`sum by (vmid, device)` which returns all disks), so the same data is fetched N times and
discarded N-1 times.

The internals doc (`70-loadmodel.md:30-37`) acknowledges this as a "known limitation, not a bug"
and notes that "fetching once and slicing per group would be a straightforward follow-up if a real
deployment's group count ever makes this Prometheus load worth avoiding." This is honest, but
the manual does not mention it — an operator with 10 groups and a busy Prometheus might wonder
why `show-load` issues 70 queries when 7 would suffice.

This is Low because: the typical deployment has 1-3 groups (the worked example has 1); the
queries are instant queries (fast); and the redundancy is correct (each group's
coverage/rejection decisions are independent). It is a performance note, not a correctness issue.

**Recommendation:** Either add a note to the manual's `show-load` section mentioning that
multi-group configs issue queries per group (so an operator with many groups and a busy
Prometheus is not surprised), or leave it as an internals-only note since it is unlikely to
matter in practice. No code change is needed for correctness.

### 13.5 Verification

- `python3 -m pytest`: 277 passed, 1 skipped (statsmodels not installed), 98.69% coverage —
  above the 85% floor. No failures.
- `python3 tests/fixtures/generate_expected.py --check`: exits 0 — both fixture expected files
  current.
- `sha256sum --check` on all three PDF stamps (plan, internals, manual): all pass.
- Heuristic objective totals cross-checked against REVIEW.md Appendix A's hand-derived values:
  three-move (β=0.25) total = 2.533333 ✓; two-move (β=0.50) total = 3.158333 ✓; initial imbalance
  E_before = 8.0667 ✓. The test assertions match the Appendix A values to 5 decimal places.
- `gates.py`'s imbalance computation matches the plan's section 6 formula exactly:
  `(max(u_s) - min(u_s)) / u*` — this is the minmax form, correctly independent of
  `objective.spread_metric` (the gate always uses minmax per the plan, regardless of the
  objective's spread metric setting).
- `reserve.py`'s `storage_of` callback extension is correctly used by `heuristic.py` for
  candidate-assignment evaluation and by `cli.py`/`topology.py` for current-state reporting
  (defaulting to `_current_storage`). The `Storage.foreign_used_bytes` is correctly
  assignment-invariant (foreign volumes are never members of D).
- `pve.py`'s reauthenticate path: the `threading.Lock` serializes concurrent reauthentication,
  the `_build_api` split allows both initial login and reauth to share the same construction
  code, and the `_apply_ticket_refresh_seconds` is a guarded no-op for API-token auth and for
  any `proxmoxer` internal shape change. Test coverage: `test_pve.py` has 7 new tests covering
  reauth success, reauth failure, retry failure, transport failure after reauth, no-callback
  behaviour, `ticket_refresh_seconds` application, and `_apply_ticket_refresh_seconds` as
  no-op.
- `topology.py`'s concurrent fetch: `ThreadPoolExecutor.map()` preserves order, the
  fetch/join split keeps `disks_by_group`/`warnings` deterministic, and `read_workers=1`
  degenerates to sequential. The `PveClient` is shared across threads.
- `metrics.py`'s `compute_disk_coverage` extraction correctly shares the coverage computation
  between `verify-metrics`'s report and `loadmodel.py`'s per-disk gate — one implementation
  per AGENTS.md section 5.
- The `show-load` command now displays `ℓ_d`, `L_s`, `u_s`, gate verdicts, coverage warnings,
  and idle-group detection, and degrades gracefully on a per-group Prometheus outage. The
  manual's `30-safety-and-status.md` status table is updated to reflect the new
  functionality.
- `docs/internals/70-loadmodel.md`, `80-gates.md`, `90-heuristic.md` correctly describe what
  each module does, what it deliberately does not do yet (polish, format eligibility,
  `state.json` wiring, cooldowns), and cross-reference the plan sections and REVIEW.md
  Appendix A.

### 13.6 Assessment

Phases 3-4 are solid. The load model, gates, and heuristic all match the plan, the test suite
cross-checks the heuristic's objective arithmetic against independently hand-derived values, and
the honest "not yet implemented" handling continues in both the code (heuristic step 4 polish
and format eligibility are documented gaps) and the documentation (`30-safety-and-status.md`'s
status table, `90-heuristic.md`'s "what this pass deliberately does not do" section). The two
findings (Q-01..Q-02) are both Low: Q-01 is a config knob silently ignored by the heuristic
(same pattern as P-01/P-02, but lower severity because the heuristic is not yet wired into any
command and the default is the implemented value), and Q-02 is a per-group query redundancy
already acknowledged in the internals docs. Neither is a correctness issue.

## 14. Resolution of eighth-pass findings (Q-01..Q-02)

| ID | Status | How resolved |
|----|--------|--------------|
| Q-01 | Resolved | `evaluate_assignment()` now reads `objective.spread_metric`: `"l1"` (default, unchanged) sums every storage's deviation from `u*`; `"minmax"` uses `alpha * max(u_s)` — the plan's own `t >= u_s`, the *raw* utilization of the hottest storage, not `max(e_s)` (a deliberate correction of the finding's own one-line suggestion, which would have computed the wrong quantity — a cold storage's large deviation below `u*` would then wrongly influence a metric the plan and the manual both describe as reacting only to the single hottest storage). `ObjectiveBreakdown` gained a `utilization` field so both views are always available regardless of which metric is active. Three new tests, including one built directly from the manual's own "indifferent to a second nearly-as-bad storage" claim, made concrete with numbers. `docs/internals/90-heuristic.md` documents the distinction explicitly, since it is easy to get backwards. |
| Q-02 | Resolved | Documented rather than changed, per the finding's own recommendation: the manual's `show-load` page now states that an `N`-group config issues `7N` Prometheus queries, not 7, and why (each group's coverage/data-quality decisions are independent, so the fetch cannot be shared). No code change — the finding's own severity assessment (correct, just wasteful for many groups) still applies. |

Verification: `python3 -m pytest` — 280 passed, 1 skipped (`statsmodels` not installed). `make
lint typecheck` clean.

---

## 15. Ninth-pass review — phases 4-5 (schedule, payback, plan command)

Reviewed commit range `9a7c270..HEAD` (commits `9495f95` through `2ad37a5`).
Changes: Q-01/Q-02 fixes, `schedule.py` (new, 245 lines), `payback.py` (new, 229
lines), `heuristic.py` refactor (repair oscillation fix, `spread_metric` support,
`group_average_utilization` made public, `ObjectiveBreakdown.utilization` field
added), `cli.py` `_handle_plan` wired (336 new lines), 4 new test files (934 new
lines), 2 new internals pages, 1 new manual page, manpage and status-table
updates.

### Verification run

- `python3 -m pytest`: **311 passed, 1 skipped** (statsmodels), **98.54% coverage**.
- `python3 tests/fixtures/generate_expected.py --check`: OK (fixtures current).
- `sha256sum --check` on all three PDF stamps: all OK.
- §14.5 arithmetic independently re-derived: m1 cost 15728.64, m2 cost 10485.76,
  total 26214.4, benefit 3951360, ratio 150.73 — all match. Archive-disk ratio
  0.721 — matches.
- §14 three-move plan (manual's `plan` example): cost 31457, benefit 4193320,
  ratio 133.3, before→after spread 255.4%→44.6%, all Δimbalance and ℓ/z values —
  all match.

### Findings

| ID | Severity | Module | Summary |
|---|---|---|---|
| R-01 | Medium | `payback.py`/`cli.py` | Payback benefit uses `alpha`-scaled `imbalance_term`, not the plan's raw `Σ_s e_s` |
| R-02 | Medium | `cli.py` | `plan`'s `after:`/`after_spread` shows the target assignment, not the scheduled state — misleading when moves deadlock |
| R-03 | Low | `cli.py` | `--group` flag is accepted but silently ignored by every handler, including `plan` |
| R-04 | Low | `docs/internals/95-schedule.md` | Stale: says `payback.py` "does not exist yet" — it was added in this same review window |
| R-05 | Low | `cli.py` | Human-output payback warning conflates economic failure and hard-duration-rule failure |
| R-06 | Low | `cli.py` | `load_per_tib` division by zero when `move.size_bytes == 0` (unguarded) |

### 15.1 R-01 — Payback benefit is `alpha`-scaled, but the plan's `E` is not

**Plan §7.2** defines `E_before = Σ_s e_s` — the raw sum of per-storage deviations
from `u*`, with no `alpha_spread` multiplier. **The code** passes
`heuristic.ObjectiveBreakdown.imbalance_term` to
`compute_benefit_load_seconds()`, and `imbalance_term = alpha_spread * spread`
(where `spread` is `Σ_s e_s` for L1 or `max(u_s)` for minmax).

With the default `alpha_spread = 1.0` the two are identical and every §14
fixture cross-checks pass. But with `alpha_spread ≠ 1.0`:

- `benefit` is scaled by `alpha_spread` on both sides, so `(E_before - E_after)`
  is scaled by `alpha` while the migration cost is not.
- A higher `alpha` makes the payback ratio easier to pass; a lower one makes
  it harder. The economic acceptance test thus depends on the solver's tuning
  knob, not just on the imbalance reduction and migration cost.
- The `compute_benefit_load_seconds()` docstring calls this "the *unweighted*
  (`alpha_spread`-scaled, which defaults to 1.0)" — "unweighted" and
  "alpha_spread-scaled" are contradictory.

This is either a code bug (should pass `sum(spread_e.values())` for L1, or the
raw `max(utilization.values())` for minmax) or a plan gap (§7.2 should say
`E_before = alpha * Σ_s e_s` if the scaling is intentional). Either way, the
plan and the code should agree, and the docstring's "unweighted" label should
be corrected.

**No test exercises `alpha_spread ≠ 1.0` with payback** — the gap is invisible
to the suite.

### 15.2 R-02 — `after:`/`after_spread` reflects the target, not the schedule

`_render_plan_human` and `_render_plan_json` compute `after_spread` from
`heuristic_result.breakdown.utilization` — the heuristic's *target* assignment,
which includes every move the heuristic proposed. When `order_moves()`
deadlocks some of those moves (transient infeasibility), the `after:` line and
`spread:` line still show the utilization *as if all moves completed*,
overstating the achievable result.

The `after:`/`spread:` lines are gated on `if schedule_result.order:` (human)
and on `heuristic_result is not None` (JSON), so a *fully* deadlocked plan
(order is empty) does not show them. But a *partially* deadlocked plan — some
moves scheduled, some not — shows the full target's spread, not the scheduled
subset's. No test covers a partial-deadlock scenario; the existing deadlock
tests all have either zero or all moves deadlocked.

The scheduled state is tracked inside `order_moves()` (the `state` dict) but
not exposed in `ScheduleResult`. Fix: either expose the final scheduled state
in `ScheduleResult` and compute `after_spread` from it, or compute it in
`cli.py` by applying `schedule_result.order` to the initial assignment.

### 15.3 R-03 — `--group` flag silently ignored

The `--group` argument is defined in `build_parser()` (`action="append"`,
`default=None`) and documented in the manpage's OPTIONS section, but
`args.group` is never read by any handler — not `show-load`, not
`verify-storages`, not the new `plan`. `build_topology()` does not accept a
group filter. Every handler iterates `for group in topology.groups:` without
filtering.

This is pre-existing (the flag predates this review window) but the new `plan`
command inherits it: `pve-storage-drs --group fc-tier2 plan` silently runs
all groups, contradicting the manpage's "Restrict the run to one storage
group."

### 15.4 R-04 — Stale reference in `95-schedule.md`

`docs/internals/95-schedule.md` line 78:

> Reasoning correctly about overlapping in-flight windows needs move duration
> estimates from `payback.py`, which does not exist yet.

`payback.py` was added in commit `f0f955d`, within this review window. The
sentence should be updated to say the module exists but the concurrent
scheduling that would use its duration estimates is not yet implemented.

### 15.5 R-05 — Payback warning conflates two failure modes

`_render_plan_payback_lines` shows `"⚠ this plan does not pass section 7.3's
payback test"` whenever `payback_result.accepted` is False. But `accepted =
aggregate_ok and not rejected_moves`, so the warning fires for two distinct
cases:

1. **Economic failure**: `aggregate_ok` is False (benefit < ratio * cost).
2. **Hard-duration failure**: `aggregate_ok` is True but `rejected_moves` is
   non-empty (a move exceeds `max_single_move_duration`).

The existing test `test_plan_human_output_shows_the_payback_verdict` hits case
2 (a reserve-exempted plan with a slow `saferemove` wipe), and the warning text
says "does not pass section 7.3's payback test" even though the *economic* test
did pass — only the hard per-move rule blocked it. The JSON output keeps
`aggregate_ok` and `accepted` separate, so this is human-output only, but the
message is misleading for an operator reading the terminal.

### 15.6 R-06 — `load_per_tib` division by zero

`_render_plan_move_line` computes `load_per_tib = load / (move.size_bytes /
_BYTES_PER_TIB)`. If `move.size_bytes == 0` the denominator is 0.0 and the
division raises `ZeroDivisionError`. The same expression appears in
`_render_plan_json` (line 600-601).

PVE does not report zero-size disks in practice, and the schema does not
forbid `size_bytes: 0` explicitly (it is an `integer` with no `minimum` in
`config_schema.json`, but the value comes from the PVE API, not config). This
is a defense-in-depth gap, not a live bug.

### What this pass confirms

- The `_repair` oscillation fix (group-wide shortfall, not source-only) is
  correct and well-tested. The extracted `_best_repair_candidate` preserves the
  original comparison logic exactly.
- The `spread_metric: "minmax"` implementation is correct: `alpha * max(u_s)`,
  not `alpha * max(e_s)`, with both `spread_e` and `utilization` always
  populated. The test built from the manual's own "indifferent to a second
  nearly-as-bad storage" claim is a good regression guard.
- The reserve-override exemption in `evaluate_plan_payback` is sound: a
  reserve-fixing plan always passes the economic test (section 13), but the
  hard per-move duration rule still applies. Both halves are tested.
- `compute_wipe_duration_seconds` is correctly shared between `payback.py`
  and `verify-storages` (one implementation, not two — AGENTS.md §5).
- All §14 fixture arithmetic cross-checks pass. The manual's three-move `plan`
  example (ratio 133, spread 255.4%→44.6%) is internally consistent.

---

## 16. Resolution of ninth-pass findings (R-01..R-06)

All six findings were real; all six are fixed, not refuted.

| ID | Status | How resolved |
|----|--------|--------------|
| R-01 | Resolved | Added `heuristic.raw_spread(breakdown, spread_metric)`, returning the true unweighted §7.2 `E` (`sum(e_s)` or `max(u_s)`), and switched `cli._handle_plan()` to pass that to `compute_benefit_load_seconds()` instead of `ObjectiveBreakdown.imbalance_term` (which is `alpha_spread`-scaled). `payback.compute_benefit_load_seconds()`'s docstring no longer calls `imbalance_term` "unweighted" — it names `raw_spread()` as the required input and explains why `imbalance_term` is the wrong one. No behavior change at the default `alpha_spread: 1.0` (every existing §14 cross-check still passes byte-for-byte); a plan with `alpha_spread != 1.0` now gets a payback ratio independent of that tuning knob. |
| R-02 | Resolved | `ScheduleResult` gained `final_assignment`: the assignment actually reachable by applying `order` in sequence, computed by `order_moves()` itself (it already tracked this internally as `state`). `_handle_plan()` now evaluates a fresh `ObjectiveBreakdown` against `final_assignment` (via `heuristic.evaluate_assignment()`) and uses *that* — not the heuristic's own `.breakdown` on its full target assignment — for `after_spread`, the `after:` line, and (extending the same reasoning) the payback benefit's `E_after`. A partially- or fully-deadlocked plan is now scored and reported on what it can actually achieve, not on moves that never got scheduled. New test: `test_plan_after_and_payback_reflect_only_the_scheduled_moves_on_partial_deadlock`, which stubs `run_heuristic()`/`order_moves()` for an exact one-scheduled/one-deadlocked scenario and asserts the reported numbers match the scheduled-only state and *not* the aspirational target's. |
| R-03 | Resolved | Added `cli._filter_groups(topology, args.group)`, called by `show-load`, `verify-storages` and `plan` immediately after `build_topology()` (`verify-metrics` does not iterate groups at all, so it is correctly left alone). An unknown group name is a hard failure (`DrsError`, exit 1) rather than a silent no-op, matching the project's existing "an explicitly named thing that cannot be found is an error" rule for `-c`/`--config PATH`. Manpage and `docs/internals/40-cli-and-logging.md` updated; four new tests cover restriction, repeatability, and the unknown-name failure. |
| R-04 | Resolved | Both `schedule.py`'s own module docstring and `docs/internals/95-schedule.md` no longer say `payback.py` "does not exist yet" — they now say concurrent scheduling could use its duration estimates but does not yet, and (a related staleness the same lines implied) that `cost_m = z_d`'s "exact, not an approximation" ordering argument now has a caveat: `payback.py` gives moves individually different costs (per-storage `saferemove` throughput), so `z_d` alone is only mirror-duration-exact, not full-cost-exact, whenever wipe costs differ enough across candidates. |
| R-05 | Resolved | `_render_plan_payback_lines()` now checks `aggregate_ok` and `rejected_moves` separately and emits a distinct line for each: an economic failure ("this plan's balance benefit does not outweigh its migration cost") and a hard-duration failure ("blocked by the hard per-move duration rule", naming the disk keys) never share text, and either, both or neither can appear on the same plan. `docs/manual/27-plan.md`'s payback section explains the distinction and why it matters (different fixes for different failures). New direct test `test_render_plan_payback_lines_separates_economic_and_duration_failures` exercises all four combinations; the existing `test_plan_human_output_shows_the_payback_verdict` (case 2, hard-duration-only) now asserts the specific new message and asserts the economic-failure message is *absent*. |
| R-06 | Resolved | Extracted `_load_per_tib()`, returning `0.0` for `move.size_bytes <= 0` instead of dividing by zero; used by both the human move line and the JSON `load_per_tib` field (one implementation, not two — AGENTS.md §5). New direct test `test_load_per_tib_is_zero_not_a_division_error_for_a_zero_size_disk`. |

As a side effect of R-01/R-02 together, `_render_plan_human()`/`_render_plan_json()` no longer take a `heuristic_results` parameter at all — everything they previously read from it (`.breakdown.utilization` for "after") is now read from the new, more correct `final_breakdowns` dict instead, and nothing else in either render function ever needed the raw `HeuristicResult`.

Verification: `python3 -m pytest` — 317 passed, 1 skipped (`statsmodels` not installed), 98.68% coverage. `make check` clean (fmt, lint, typecheck, test, fixtures, docs-check — internals PDF rebuilt to 23 pages, manual PDF to 26).

---

## 17. Tenth-pass review — state, cooldowns, MILP backends (phase 6) and execution (phase 7)

Reviewed commit range `2ad37a5..HEAD`: `de7deda` (the R-01..R-06 fixes, already recorded in
section 16), `d0e9f2f` (`state.py`, section 11.2, drift history wired into `show-load`/`plan`),
`a573855` (cooldown wiring: `state.py` queries, `topology.py`'s (C2) per-disk pin,
`heuristic.py`'s per-storage target exclusion), `375d3a9` (`optimize.py`, phase 6: CP-SAT and
CBC MILP backends, wired into `plan`), `c6760c9` (`execute.py`, phase 7: move execution,
`apply` wiring). Roughly 5,500 inserted lines of source and tests across the five commits,
~2,700 of them tests.

The engineering quality remains high — the state-file locking design (and the
rename-detaches-the-`flock` trap it documents and tests), the section 5.5 coefficient folding,
the three-condition completion criterion and the injectable `Clock` are all better than the
plan strictly demands. But this pass also found the two most serious implementation defects
so far, and both are in the newest code: the CBC backend cannot run on the pulp version
Debian trixie ships (the packaged solver path, §2.1), and `apply` ignores the payback
acceptance test entirely.

### 17.1 Verification run

- Dev venv `python3 -m pytest`: **424 passed, 17 skipped** (ortools, pulp and statsmodels are
  absent from the venv), **90% line coverage** — above the 85% floor.
- `tests/fixtures/generate_expected.py --check`: OK. `sha256sum --check` on all three PDF
  stamps: OK. (`make check`-equivalent for the local toolchain is green.)
- **CI environment reproduced locally.** This host's system Python carries pulp **2.7.0** —
  the same version Debian trixie packages (`python3-pulp 2.7.0+dfsg-4`, confirmed with
  `rmadison`), which is also exactly what `.github/workflows/tests.yml` installs from apt in
  its `debian:trixie` container. Running the suite with it: **24 failed, 408 passed** — every
  CBC-parametrized test in `test_optimize.py` dies on the same `AttributeError` (S-01). The
  CBC tests do *not* skip there: `cbc_available()` only checks that `import pulp` succeeds,
  which it does.
- **The CBC logic itself is sound.** In a throwaway venv with pulp **3.3.2**, the same tests
  all pass — including both §14 fixture reproductions (β=0.25 three-move, β=0.50 two-move),
  the `reserve-tradeoff` lexicographic-optimum test and the minmax/heuristic-agreement test.
  The defect is purely library-version compatibility, not model logic.
- Bisected pulp's releases by downloading and inspecting each wheel: `LpProblem.add_variable`
  first exists in **pulp 3.3.1**; 3.3.0 and every earlier release (including 2.7.0) lack it.
- `python3 -c "import pulp; ..."` on the system 2.7.0 confirms `LpProblem` exposes only the
  camelCase `addVariable`/`addVariables`, and that `pulp.apis.coin_api` raises
  `PulpSolverError` when the cbc binary cannot be executed (relevant to S-01's second half).

### 17.2 Findings summary

| ID | Severity | Module(s) | Summary |
|----|----------|-----------|---------|
| S-01 | High | `optimize.py`, `pyproject.toml` | CBC backend calls `prob.add_variable()`, which needs pulp ≥ 3.3.1 — but the extra declares `pulp>=2.7` and the target platform packages 2.7.0, so the packaged solver path crashes; CI installs that version and its CBC tests cannot pass |
| S-02 | High | `cli.py`, `execute.py` | `apply` executes the scheduled plan regardless of the §7.3 payback verdict — including individual moves the *hard* per-move duration rule rejected; §7.3's re-solve-with-doubled-β/γ retry is absent too |
| S-03 | Medium | `cli.py`, `state.py` | the per-storage cooldown is recorded for the **destination** only, so a still-draining *source* storage is never protected — defeating the exact scenario §9.3's knob-sizing rule and `verify-storages`' own warning text describe |
| S-04 | Medium | `optimize.py` | the MILP backends ignore `cooldown_storages` (heuristic-only enforcement); the module docstring's "cooldowns are inert today" justification went stale the moment phase 7 landed, and §5.5's "backends directly comparable" requirement is now violated |
| S-05 | Medium | `execute.py` | §9.3's "mark the storage draining, exclude it as both source and target for the remainder of the run" is not implemented — a `draining` outcome changes nothing for later moves in the same run |
| S-06 | Low | `execute.py` | §9.2's pre-flight does not re-check exclusion tags (step 3's "untagged for exclusion"); a VM tagged `no-drs` between planning and execution is still moved |
| S-07 | Low | `optimize.py` | lexicographic stage 1 accepts a gapped incumbent as the reserve floor (CP-SAT `FEASIBLE`; CBC's gap-satisfied "Optimal"), weakening §5.3's "provably never traded" guarantee by up to `mip_gap`, and the two backends pin it differently (`==` vs `<=`) |
| S-08 | Low | `docs/manual/10-configuration.md` | the four phase-8 knobs are documented as functional with no "not yet effective" caveat — the same pattern P-01/P-02 established as a finding |
| S-09 | Low | `optimize.py` vs plan §5.5 | the plan's model-build-time assertions (non-zero integer coefficient wherever the unscaled weight is non-zero; objective magnitude < 2⁶²) are neither implemented nor removed from the plan; the docstring argues only against the *post-solve* half |

### 17.3 S-01 — the CBC backend requires pulp ≥ 3.3.1 but targets trixie's 2.7.0

**Severity:** High
**Files:** `src/proxmox_storage_drs/optimize.py:517-531`, `pyproject.toml:37`,
`docs/internals/91-optimize.md:80`, `IMPLEMENTATION_PLAN.md` §2.1

`_cbc_feasibility_constraints()` builds every variable with `prob.add_variable(...)`, with a
comment saying the direct `pulp.LpVariable(...)` constructor is "PuLP's v4 migration
deprecates". Two facts make that choice wrong for this project:

1. `LpProblem.add_variable` does not exist in pulp ≤ 3.3.0 — verified by wheel inspection
   across 2.7.0, 2.8.0, 2.9.0, 3.0.0, 3.1.1, 3.2.0, 3.2.2, 3.3.0 (absent) and 3.3.1, 3.3.2
   (present). The "v4 migration" is a *future* API; the present-tense deprecation direction
   only applies to 3.3+.
2. The deployment target packages **pulp 2.7.0** (`python3-pulp 2.7.0+dfsg-4` in trixie), and
   §2.1 says plainly: "on a Debian install the MILP is solved by **CBC through
   `python3-pulp`**". This is the packaged solver path.

Consequences, all reproduced locally:

- With pulp 2.7.0 installed, `_solve_cbc()` raises
  `AttributeError: 'LpProblem' object has no attribute 'add_variable'. Did you mean: 'addVariable'?`
  on the first variable — `solve()`'s "returns None, never raises" contract is violated, no
  heuristic fallback happens (§13's "solver infeasible or timing out → fall back to the
  heuristic" — a backend that *cannot construct its model* is at least that), and the whole
  `plan`/`apply` invocation crashes with a traceback.
- The test suite parametrizes every solve test over `cbc` with a skip condition of
  `not cbc_available()`, and `cbc_available()` only checks `import pulp`. On trixie, pulp
  imports — so the tests **run and fail**: 24 failures (17.1). `make check` in the dev venv is
  green only because the venv installs neither solver (17 skips). The GitHub Actions
  `debian:trixie` job installs `python3-pulp` from apt (this is precisely what the L-03 fix
  added) and runs `python3 -m pytest` — in that deterministic environment the job cannot be
  green on current `main` as committed (CI status was not directly observable from this
  checkout, but the container, the apt version and the test command all are). This is exactly
  the failure mode L-03 predicted in reverse: the local pip-or-nothing toolchain hid an
  apt-version incompatibility.
- `pyproject.toml`'s solver extra declares `pulp>=2.7`, so even a pip user following the
  project's own constraint can resolve a version (2.7–3.3.0) that crashes.

A second, smaller defect in the same function: `prob.solve()` is not wrapped for
`pulp.PulpSolverError`. Debian splits the CBC binary into `coinor-cbc` (a separate package,
`Recommends`, not `Depends`); a host with `python3-pulp` but without `coinor-cbc` hits
`PulpSolverError("Pulp: cannot execute ...")` — again a raised exception where the module
docstring promises `None` and §13 promises heuristic fallback.

**Recommendation:** construct variables with `pulp.LpVariable(...)` directly (works on every
version including 2.7.0 and 3.3.2; if the 3.3+ deprecation warnings are a concern, silence
them explicitly rather than adopting an API the target platform cannot provide), or
feature-detect `add_variable` with a fallback. Wrap `prob.solve()` in `except
pulp.PulpSolverError → return None`. Then either raise the extra to the version actually
required (`pulp>=3.3.1`, wrong for trixie) or — better — keep `>=2.7` and *prove* trixie
compatibility by running the CBC tests in CI, which the fix makes pass. Also correct
`91-optimize.md`'s claim that `add_variable` is "not the older constructor" in a way that
implies availability, and re-examine the module docstring's "both backends were exercised for
real during development" — true, but under pip's pulp 3.3+, which is not the packaged path
the plan designates as primary.

### 17.4 S-02 — `apply` executes plans that failed the payback acceptance test

**Severity:** High
**Files:** `src/proxmox_storage_drs/cli.py:1325-1358` (`_handle_apply`),
`src/proxmox_storage_drs/execute.py:281-304`, `IMPLEMENTATION_PLAN.md` §7, §7.3, §9

Section 7 is explicit that the payback rule is "a **hard acceptance test on the finished
plan**, not merely a soft `γ` penalty, because a penalty can always be outweighed by a large
enough imbalance term", and §7.3's per-move rules "**reject** individual migrations
regardless of the aggregate test" (`duration_d > max_single_move_duration` → reject the
move). §1 lists "a migration's own I/O cost must not exceed the imbalance it removes" as a
goal-scope requirement.

`_plan_group()` computes `payback_result` (the verdict, including `aggregate_ok` and
`rejected_moves`) — and nothing ever consults it on the execution path. `_handle_apply`
calls `execute_plan()` with `group_plan.schedule_result` whenever the gate said `act`, and
`execute_plan()` walks `order` unconditionally. Concretely:

- A plan that fails the aggregate economic test (benefit < `payback_ratio`·cost) is executed
  in full in `apply --mode confirm` — the operator is prompted move by move with no
  indication the tool's own §7.3 verdict was ✗, because the human/JSON report that *shows*
  the verdict is rendered only after all groups have executed. The tool's answer to "why did
  it move disks the payback test rejected" is, today, "it didn't check".
- Worse, a move whose `duration_d` (mirror + wipe) exceeds `max_single_move_duration` is
  listed in `rejected_moves` yet still sits in `schedule_result.order` and is issued to PVE.
  `_wait_for_move_completion()`'s own docstring claims "a move that was accepted at planning
  time already passed `migration.max_single_move_duration`" — nothing enforces that; the
  claim is false. §7.3's hard rule is exactly the operational guard against a multi-day
  wipe being started.
- §7.3's prescribed response to aggregate failure — "re-solve with `β` and `γ` doubled and
  retry, up to three times" — is implemented nowhere.

No test covers a payback-failing plan reaching `execute_plan` (grep confirms; the apply tests
cover prompts, declines, locks, failures, state writes — never the payback gate), so the gap
is invisible to the suite. The reserve-override exemption is already handled correctly
*inside* `evaluate_plan_payback` (a plan containing a reserve-resolving move passes the
economic test, and the hard duration rule still applies) — which makes the missing
enforcement the only thing between a rejected plan and production disks.

**Recommendation:** in `_handle_apply`, before executing a group: drop moves in
`rejected_moves` from the order (report them as refused per §7.3), and refuse to execute the
remaining plan when `not aggregate_ok` (report; §7.3's re-solve loop is the follow-up, and
until it exists, refusing is the correct conservative behavior — the reserve-override
exemption already lives in `aggregate_ok`). At minimum, in confirm mode show the payback
verdict *before* the first prompt, not in the post-execution report. `execute.py`'s
docstring claim about planning-time duration filtering should become true by construction.

### 17.5 S-03 — storage cooldown recorded for the destination only

**Severity:** Medium
**Files:** `src/proxmox_storage_drs/cli.py:1388-1391`, `docs/manual/28-apply.md:114-118`,
`state.py:362-363` (stale docstring), `IMPLEMENTATION_PLAN.md` §6, §9.3

`_handle_apply` records a `cooldowns.storage` timestamp for `move.to_storage` only, with an
inline justification ("a storage this run only moved disks away from is not a wear/churn
concern the cooldown protects against") echoed by the manual. The plan disagrees twice:

- §6: "a storage **involved in** a migration within `cooldown_per_storage` accepts no new
  incoming moves" — a migration has two endpoints, and the phrase covers both.
- §9.3's sizing rule is written *specifically about sources*: "`gates.cooldown_per_storage`
  must exceed the expected wipe time for that storage's largest disk, or the next run will
  plan moves onto a storage that is still draining". The wipe runs on the **source**. With
  destination-only recording, no value of `cooldown_per_storage` — however large — can ever
  protect a draining source, because sources never get a timestamp. The same inversion
  affects §11.1's validation warning and `verify-storages`' own message ("the next run may
  plan onto a still-draining storage"), which advertises a mitigation the implementation
  cannot deliver for the storage the warning is about.

The code comment (and `90-heuristic.md`) conflates two different statements: "the cooldown
excludes a storage as a *destination*, never as a source" (correct — it is about how the
cooldown is *enforced* against candidate moves) and "only destinations *get* a cooldown" (not
what §6/§9.3 say). On a saferemove cluster this is the difference between the next run
(15-30 min later, per §2.1's cadence) excluding a storage that will be zeroing a LUN for
44 hours, and planning a move onto it that then fails against the storage-level lock §9.3
warns about. Note also `state.with_recorded_cooldown`'s docstring still says "Not called by
anything today" — stale since `c6760c9`.

**Recommendation:** record timestamps for both endpoints (`from_storage` and `to_storage`);
keep the destination-only *exclusion* semantics in the heuristic/MILP exactly as they are.
Update `28-apply.md`, `15-state.md`, and the two stale docstrings. If the project genuinely
wants destination-only recording, that is a defensible policy — but then §6, §9.3, §11.1 and
the `verify-storages` message must be rewritten to stop promising source protection, in the
same commit (AGENTS.md §7.6).

### 17.6 S-04 — the MILP backends ignore `cooldown_storages`

**Severity:** Medium
**Files:** `src/proxmox_storage_drs/optimize.py:48-65, 210-215`, `schedule.py:44-46`

`solve()` accepts `cooldown_storages` "for interface symmetry" and logs a warning when it is
non-empty, but neither model excludes those storages as targets. The module docstring
justifies the gap with "Cooldowns are inert today anyway (nothing calls
`state.with_recorded_cooldown()` yet)" — true when phase 6 landed, **false since phase 7**:
`apply` now writes cooldown timestamps (S-03). The stated plan for the hard-fix
(a big-M penalty or per-solve feasibility check) is a real difficulty, but the consequence
is no longer hypothetical:

- After any `apply` run that executed a move, the next `plan`/`apply` within
  `cooldown_per_storage` — the exact scenario the cooldown exists for — will, whenever
  ortools or pulp is importable, solve with cpsat/cbc (the default `solver.backend: auto`
  cascades to them first) and may assign disks onto the cooling/draining storage. The
  heuristic would not. §5.5's "the heuristic must use the same feasibility and objective
  functions as the MILP path so the two backends are directly comparable" is violated —
  the backends can now return different optima for the same input, which is precisely the
  class of divergence that requirement exists to prevent.
- Nothing downstream catches it: `schedule.py` documents that it schedules "as if no
  cooldown applies", so §8.1's `concurrency_ok` condition 5 is unimplemented there too, and
  the executor's live transient check only guards *capacity*, not the wear/churn and
  storage-lock reasons the cooldown encodes.

**Recommendation:** for stage 2, hard-fix `x_{d,s} = 0` for `s ∈ cooldown_storages` *and*
re-run stage 1 (or verify stage 1's optimum still stands) so the lexicographic invariant is
not invalidated — or, simpler and matching the heuristic's own semantics, filter cooldown
storages out of the *candidate target set* for movable disks in both stages and treat the
current assignment (which never violates its own feasibility) as always available, exactly
as `_descend()` does. Either way, delete the "inert today" sentence: it is now misleading in
the direction that matters.

### 17.7 S-05 — a drained storage is not excluded for the remainder of the run

**Severity:** Medium
**Files:** `src/proxmox_storage_drs/execute.py:488-502`, `docs/internals/92-execute.md:55-73`

§9.3, on a `source_release` timeout: "do not fail the run: mark the storage `draining`,
**exclude it as both source and target for the remainder of the run**, report it". The
implementation does the "mark" (`status="draining"`, reported per-move) and the "do not
fail" (draining is treated like moved), but not the exclusion: `execute_plan()` simply
continues to the next move with nothing changed. A subsequent move in the same run whose
source or target is the drained storage proceeds — into the storage-level lock §9.3 says the
wipe holds, i.e. it either queues behind a potentially day-long wipe (the task-status loop
is unbounded) or fails, aborting the run under `abort_on_failure`. The live transient check
only partially protects the target direction (the un-wiped volume still counts in live
`used`), and does nothing for the source direction.

`92-execute.md` presents the draining state as fully handled ("the next run will see the
storage as it actually is") without mentioning that the *current* run keeps going — so this
is not an honestly-documented phase gap like the re-plan protocol, but an unimplemented
sentence of the section the module says it implements.

**Recommendation:** track drained storages in `execute_plan()`; skip (and report as skipped,
with the draining storage named) any later move whose `from_storage` or `to_storage` is in
that set, exactly like a cooldown skip. Cheap, self-contained, and it removes the one way
this run can still shoot itself in the foot after correctly detecting the wipe.

### 17.8 S-06 — pre-flight does not re-check exclusion tags

**Severity:** Low
**Files:** `src/proxmox_storage_drs/execute.py:155-195`, `IMPLEMENTATION_PLAN.md` §9.2 step 3

§9.2 step 3: "confirm the VM is still running **and untagged for exclusion**". `_preflight()`
re-checks existence, node, disk placement, running state, snapshots and lock — but not
`exclude.vmids`/tags/`no-drs`. The `resource` dict it already fetched carries `tags`, and
the config is in scope at the call site, so this is a two-line check. A VM tagged `no-drs`
between planning and execution is moved anyway. Low because the window is minutes and the
operator configured the exclusion at planning time, but §9.2 lists it as one of the five
re-checks and four of the five are implemented.

**Recommendation:** pass the exclusion predicate into `execute_plan()`/`_preflight()` (or
pre-resolve the excluded vmid set) and return `replan_needed` on a tag match, mirroring the
snapshot case.

### 17.9 S-07 — lexicographic stage 1 may stop at the gap, and the backends pin it differently

**Severity:** Low
**Files:** `src/proxmox_storage_drs/optimize.py:456-468` (CP-SAT), `654-672` (CBC)

The whole strength of the lexicographic solve (§5.3 option 1) is that stage 1's minimum is
*proven*, so "Σ r_s > 0 provably means physically impossible". Both implementations
compromise that proof in a different way:

- CP-SAT stage 1 accepts `OPTIMAL` **or** `FEASIBLE`, with `relative_gap_limit = mip_gap`
  (default 0.02). On `FEASIBLE`, `min_slack` is an incumbent, not the minimum — and stage 2
  pins `Σ r_s == min_slack`, which both allows trading up to the gap *and forbids finding
  less slack than the incumbent.
- CBC's `LpStatus == "Optimal"` does not distinguish a proven optimum from a search that
  stopped because `gapRel` was satisfied; its stage 2 uses `<= min_slack + 1e-6` —
  monotone-safe (cannot be worse than the incumbent) but still permits up-to-gap shortfall.

In practice stage 1 is a near-feasibility problem that closes instantly on realistic groups,
so this needs a big group, a positive slack and a slow solve to bite. But the code
structurally accepts the gapped case without distinguishing it, the two backends behave
differently when it happens (another §5.5 comparability dent), and the reported
"unfixable shortfall" could overstate what is physically possible.

**Recommendation:** run stage 1 with the gap forced to 0 (it is the cheap stage), or require
`status1 == OPTIMAL` and fall back to the heuristic otherwise; use `<=` rather than `==` for
stage 2 in both backends so stage 2 can only improve on the stage-1 value.

### 17.10 S-08 — phase-8 knobs documented as functional in the configuration reference

**Severity:** Low
**Files:** `docs/manual/10-configuration.md:656-697`, `28-apply.md`, `30-safety-and-status.md`

`execution.max_concurrent_migrations`, `max_migrations_per_run`,
`max_concurrent_per_storage` and `max_replans_per_run` each have a full configuration-reference
entry describing behaviour ("How many moves may be in flight...", "A ceiling on how many
moves one invocation executes...", "Caps concurrent moves touching one storage...", "A cap
on how many times one run may abandon its current plan and re-plan") with no hint that none
of it exists yet: the executor is strictly sequential, has no per-run cap, and never
re-plans. `28-apply.md` and the `30-safety-and-status.md` table *are* honest ("Its own
safety rails ... are phase 8"; "re-invoking the whole pipeline automatically ... is not
implemented yet") — but the reference page is where an operator looks a knob up, and it is
the exact P-01/P-02 pattern this review has twice established as a finding: a knob
documented as doing something the code does not do. The cross-reference tests only check
existence, not effect.

**Recommendation:** add the one-line "not yet effective in this build; the executor is
strictly sequential / re-planning is not implemented" caveat to each of the four entries in
`10-configuration.md` (and remove the caveat when phase 8 lands, in the same commit as the
behaviour).

### 17.11 S-09 — §5.5's model-build-time assertions are neither implemented nor removed

**Severity:** Low
**Files:** `src/proxmox_storage_drs/optimize.py:69-78`, `IMPLEMENTATION_PLAN.md` §5.5

§5.5: "Assert at model-build time that every coefficient is a non-zero integer wherever its
unscaled weight is non-zero — the regression test for the γ trap above — and that the
maximum objective magnitude is below 2⁶²." The code has neither assertion, and the plan was
not updated. The module docstring rebuts only the *other* assertion of that paragraph (the
post-solve floating-point agreement check, arguing `evaluate_assignment()` is a sharper
version — a fair argument). It does not address the build-time pair. Notably, the code's
`if gamma_scaled: terms.append(...)` pattern *silently drops* a zero coefficient — the exact
failure shape the demanded assertion exists to catch; it is unreachable at the default
weights after per-disk folding (a coefficient rounds to zero only for a sub-kilobyte disk),
but the plan's text is a requirement, and "practically can't happen" is what assertions are
for. Per AGENTS.md §7.6, either implement them or fix the plan in the same commit.

**Recommendation:** a three-line guard in `_cpsat_objective_terms` (raise/log when a
computed coefficient rounds to zero under a non-zero weight, and when any term's maximum
magnitude exceeds 2⁶²) costs nothing and turns §5.5's regression test back into code.
Alternatively, rewrite §5.5's sentence to delegate the guarantee to the shared
`evaluate_assignment()` recomputation — but then say so in the plan.

### 17.12 What this pass confirms

- **state.py's locking is genuinely well designed.** `flock()` on the file itself as the
  mechanism, the in-JSON `lock` field demoted to descriptive metadata (which dissolves the
  stale-lock-recovery question rather than answering it), and — the subtle one —
  `_write_state_to_locked_fd()`'s discovery that `save_state_atomic()`'s rename would
  *replace the inode the lock was taken on*, documented with the test that caught it
  (`test_a_second_acquire_while_the_first_is_held_returns_none`). Reads correctly skip
  locking because atomic writes make torn reads impossible. Read-degrades/write-raises is a
  coherent policy and consistently applied.
- **The cooldown wiring follows the plan's structure**: disk cooldowns as a (C2) pin in
  `topology.py` (reported with a human reason, in the plan's own priority order), storage
  cooldowns as a target exclusion in the heuristic, cooldown `<= 0` meaning "disabled"
  rather than "always cooling". The `_repair()`-ignores-cooldowns choice is a documented,
  defensible extension of the reserve-override principle.
- **optimize.py's model is a faithful transcription of §5.3-§5.5**: (C1)-(C6) all present,
  including the `affinity_counts_pinned_disks` variants of (C3) with the `y==1` forcing for
  pinned-of-VM disks; pinned disks counted in `Σ z·x`, `Z_s` and (C5) exactly as §3.6
  demands; warm start from the current assignment; the γ coefficient folded per-disk
  (`round(γ·W·K·z_d^TiB)`, the N-01 fix) rather than factored; `a_{d,s} = round(K·ℓ_d/c_s)`
  folding; the reserve factor's own fixed-point scale — a wrinkle the plan did not name and
  the implementation had to invent, correctly.
- **The shared-objective architecture pays off**: both MILP backends hand their assignment
  to `heuristic.evaluate_assignment()` for the reported numbers, so a modelling mistake can
  choose a worse plan but cannot mis-report one — and the fixture cross-checks (which pass
  on pulp 3.3.2, 17.1) are exactly the sharper guard the docstring claims.
- **execute.py's completion criterion, lock waiting and orphan handling match §9.3**: three
  conditions, open-ended lock set never whitelisted, orphans reported never deleted, the
  KiB/s conversion at the one call site, pre-flight re-fetches genuinely bypassing all
  caching (PveClient has none). The injectable `Clock` lets every wait loop's timeout
  arithmetic be tested without real sleeps, and the 30 execute tests use it.
- **`apply`'s state bookkeeping is right**: lock-first quiet-exit-0, `last_balance`/
  cooldowns written only after executed moves, `--mode auto` refused outright rather than
  run without its rails, `dry-run` issuing zero API calls (tested).

### 17.13 Assessment

The state, cooldown and executor work is careful and the MILP model itself is correct —
proven against both fixtures once the right pulp is present. But this is the first pass
whose findings include defects that make the tool *crash* or *act against its own safety
rules* rather than merely omit a feature: S-01 breaks the primary packaged solver path on
the target platform (and CI's own trixie job cannot be green with it in), and S-02 executes
plans §7.3 explicitly rejects — with the hard per-move duration rule, the one §7.3 calls an
operational limit rather than an economic one, as the sharpest instance. S-03/S-04/S-05 all
weaken the same protection from different directions: the cooldown/draining machinery that
§9.3 exists to keep a wiping storage out of trouble has, as implemented, a write-side gap
(S-03), a solver-side gap (S-04) and an executor-side gap (S-05). Fixing S-01 and S-02
should precede any further feature work; S-03..S-05 belong in the same fix series, since
each is small and they compose into one story — "a storage that is draining must be left
alone" — that the plan states three times and the implementation currently honours zero
times end to end.

---

## 18. Resolution of tenth-pass findings (S-01..S-09)

All nine findings were real; all nine are fixed, not refuted.

| ID | Status | How resolved |
|----|--------|--------------|
| S-01 | Resolved | Every MILP variable in both backends is now built via a new `_lp_variable()` helper wrapping `pulp.LpVariable(...)` directly (not `prob.add_variable(...)`, PuLP v4's replacement, absent before pulp 3.3.1), with the resulting v4-migration `DeprecationWarning` suppressed explicitly via `warnings.catch_warnings()` rather than adopting an API the packaged trixie version (`python3-pulp` 2.7.0) cannot provide. `_pulp_solve()` also wraps `prob.solve()` in `except pulp.PulpSolverError → None`, so a `python3-pulp` install without `coinor-cbc` degrades the same way an unimportable library does, never a bare traceback. Reproduced and verified against a throwaway venv pinned to pulp 2.7.0 (the exact version `rmadison`/CI's `debian:trixie` container installs): all CBC `test_optimize.py` cases pass; also re-verified against pulp 3.3.2 to confirm no regression there. `docs/internals/91-optimize.md` and the module docstring updated; the `pulp>=2.7` extra constraint is unchanged (now actually true, not merely declared). |
| S-02 | Resolved | New `cli._apply_payback_gate()`: a move in `payback_result.rejected_moves` (the hard per-move duration rule) is dropped from the order and reported `"skipped"` ("refused: exceeds migration.max_single_move_duration...") without ever reaching `execute_plan()`; when `not payback_result.aggregate_ok`, the *whole* group's remaining plan is refused the same way and `execute_plan()` is never called at all, issuing zero API calls, same as `dry-run`. `_handle_apply()` also prints the group's payback lines once, before the first `confirm` prompt, not only in the post-run report. `_render_group_plan_human()`'s move-line lookup switched from positional indexing to a `disk_key`-keyed dict, since a refusal can make `ExecutionResult.outcomes` a reordered subset of `schedule_result.order`. Six new `test_cli.py` cases cover: an individually-rejected move refused with `execute_plan` monkeypatched to raise on any call; a plan failing the aggregate test refused the same way; the payback preview appearing before the first prompt. |
| S-03 | Resolved | `_handle_apply()` now records a `gates.cooldown_per_storage` timestamp for **both** of an executed move's storages, source and destination — section 6's "involved in a migration" covers both, and section 9.3's sizing rule is specifically about protecting a still-draining *source*. `heuristic.py`'s own *enforcement* is untouched (destination-only exclusion, per `docs/internals/90-heuristic.md`) — this was a recording gap, not an enforcement one. `state.with_recorded_cooldown()`'s stale "not called by anything today" docstring, and the equivalent claims in `docs/manual/28-apply.md`/`docs/internals/92-execute.md`, are corrected. `test_apply_records_balance_and_cooldowns_after_an_executed_move` now asserts both storages get a cooldown, not just the destination. |
| S-04 | Resolved | Both `_cpsat_feasibility_constraints()` and `_cbc_feasibility_constraints()` now take `cooldown_storages` and add `x_{d,s} = 0` for every movable disk `d` and cooldown storage `s` that is not `d`'s current storage — applied identically in both lexicographic stages, matching `heuristic._descend()`'s own destination-only exclusion. `solve()`'s "not enforced yet" warning is removed; the module docstring's bullet is rewritten to describe what *is* now enforced and the one thing deliberately not replicated (`_repair()`'s reserve-override exemption from the same cooldown — a narrower, documented gap, not the original all-or-nothing one). New tests mirror `test_heuristic.py`'s own cooldown pair exactly (`test_solve_excludes_a_cooldown_storage_as_a_target_for_a_movable_disk`, `test_solve_still_allows_a_disk_to_move_away_from_a_cooldown_storage`), parametrized over both backends and verified against real `ortools`/pulp 2.7.0 installs. |
| S-05 | Resolved | `execute_plan()` now tracks a `drained_storages` set, adding a move's `from_storage` whenever its outcome is `"draining"`; `_drained_skip_outcome()` (factored out to stay within the flake8 complexity limit) skips — with zero API calls — any later move in the same run whose source or target is in that set, reporting it plainly rather than letting it queue behind or fail against the storage-level lock section 9.3 describes. Two new tests construct a two-move run where the first move drains a storage and assert the second (as source, then as target) is skipped without a single additional API call. |
| S-06 | Resolved | `_preflight()` takes a new `exclude: ExcludeConfig` parameter and re-checks `exclude.vmids`/`exclude.tags` via a new `_is_excluded_by_tag_or_vmid()` (a small duplicate of `topology.py`'s own private predicate, matching this codebase's established preference over reaching into another module's private name) — a VM tagged for exclusion (or added to `exclude.vmids`) between planning and execution now stops that move with `replan_needed` instead of moving it anyway. `execute_plan()`/`cli._apply_payback_gate()` thread the parameter through; two new tests cover the tag and vmid cases. |
| S-07 | Resolved | Stage 1 in both backends now forces its own solver gap to exactly `0` regardless of the configured `solver.mip_gap` (which now applies only to stage 2's real objective) — CP-SAT's stage 1 requires `status1 == OPTIMAL` (never accepts `FEASIBLE`), and CBC's stage 1 uses a separate `pulp.COIN_CMD(gapRel=0.0)`, since PuLP's own `LpStatus` string cannot otherwise distinguish a proven optimum from a search that merely satisfied `gapRel`. Stage 2's slack-pinning constraint changed from `==` to `<=` in both backends — monotone-safe, and equivalent to `==` now that stage 1 is exact. New test `test_stage_one_reserve_floor_ignores_a_generous_mip_gap` calls `solve()` directly (bypassing the test helper's hardcoded `mip_gap=0.0`) with `mip_gap=0.5` against the `reserve-tradeoff` fixture and asserts neither backend trades the reserve floor away; verified against real `ortools`/pulp 2.7.0. |
| S-08 | Resolved | Added a one-line "**Not yet effective in this build**" caveat, naming the phase-8 dependency and cross-referencing `docs/manual/30-safety-and-status.md`, to each of `execution.max_concurrent_migrations`, `max_migrations_per_run`, `max_concurrent_per_storage` and `max_replans_per_run` in `docs/manual/10-configuration.md`. |
| S-09 | Resolved | `_cpsat_objective_terms()` now calls two new assertions: `_assert_nonzero_when_weighted()` (raises if a non-zero configured weight's rounded, scaled coefficient collapsed to `0` — the exact γ-trap shape the `if gamma_scaled:` guard would otherwise silently absorb) for `beta_scaled`, `kappa_scaled`, `alpha_scaled` and every disk's `gamma_scaled`; and `_assert_objective_magnitude_within_int64()` (a coarse, deliberately conservative worst-case sum of every term, asserted below `2**62`, an order of magnitude under CP-SAT's own `2**63-1` domain). Both are CP-SAT-only, matching that this is specifically an integer-coefficient-discipline guard CBC's continuous model has no analogous need for. New direct unit tests for both helpers plus an end-to-end `test_gamma_trap_assertion_fires_end_to_end_for_a_sub_kilobyte_disk` (a synthetic 1.1×10⁻¹⁰ TiB disk, verified to actually trip the guard against a real `ortools` install), and the module docstring's bullet on the plan's assertion paragraph now names both as implemented rather than only rebutting the post-solve one. |

Verification: dev venv `python3 -m pytest` — 435 passed, 24 skipped (ortools/pulp/statsmodels
absent), 89.57% coverage. Every backend-parametrized new/changed test independently re-run
against a throwaway venv pinned to pulp **2.7.0** (the exact Debian trixie/CI version S-01's
own finding was about) and again against a separate venv with `ortools` installed (no working
CP-SAT venv existed from the ninth-pass review) — all pass under both, not merely under the
pip-resolved newer pulp the ninth-pass verification used. `make check` clean (fmt, lint,
typecheck, test, fixtures, docs-check — internals PDF rebuilt to 35 pages, manual PDF to 32).

---

## 19. Eleventh-pass review — phases 8-9, crash recovery, concurrency, saturation guard

Reviewed commit range `d5307f7..HEAD` (the S-01..S-09 fixes themselves are already recorded in
section 18): `c01c0d7` (auto mode, phase 8: time windows, migration cap, re-plan loop), `6f54308`
(auto-mode self-review: lock-wait deadline gap, DST), `76f0d2c` (section 13 crash and
two-instance recovery, new `crashrecovery.py`), `026e9d9` (section 8.1's generalized transient
invariant extracted into `reserve.transient_charge_ok()`), `a59c613` (concurrent execution),
`0447940` (per-disk load time series in `loadmodel.py`), `d94807a` (section 7.3's
saturation-ceiling defer check in `payback.py`), `10a9ead` (wiring the guard into
`plan`/`apply`), `f2c572e` (phase 9: the section 10.2 forecast backtest gate). Roughly 5,900
inserted lines across 38 files (~2,700 of them tests), two new modules (`timewindow.py`,
`crashrecovery.py`), and one new internals page. `IMPLEMENTATION_PLAN.md` itself is unchanged
across the entire range.

This is the pass that makes the tool an unattended one, and the engineering quality of the
individual mechanisms continues to be high: the time-window module's local-time-with-IANA-zone
DST handling (including the honest documentation of the fixed-offset fallback's two-nights-a-year
residual gap), the write-the-UPID-before-anything-else crash trace with the finally-block that
deliberately saves the callback's newer state over the loop's older local variable, the shared
`transient_charge_ok()` that makes the sequential and concurrent executors provably check the
same arithmetic, the non-blocking `_poll_move_once()`/`_LaunchDecision` decomposition of the
executor, and the `accepted`-vs-`deferred_moves` split in the payback verdict are all better
than the plan strictly demands. The three Medium findings are all at the seams between the new
mechanisms rather than inside any one of them.

### 19.1 Verification run

- Dev venv `python3 -m pytest`: **558 passed, 24 skipped** (ortools, pulp and statsmodels absent
  from the venv), **91.28% line coverage** — above the 85% floor, and *up* from the tenth
  pass's 89.57% despite ~2,650 new source lines under test: the new surface is well covered
  per-module (`execute.py` and `cli.py` both at 99% under their own test files;
  `crashrecovery.py` and `timewindow.py` have dedicated files with 19 and 16 tests).
- System Python (pulp **2.7.0**, the exact Debian trixie / CI version): `test_optimize.py`
  20 passed, 12 skipped — the S-01 fix holds on the packaged path. No CP-SAT-capable
  environment was available this pass; the ortools-parametrized cases remain skipped here.
- `tests/fixtures/generate_expected.py --check`: OK. `sha256sum --check` on all three PDF
  stamps (plan, internals, manual): all OK. `black --check`, `flake8`, `mypy`: clean.
- **The concurrent re-plan gap (T-01) was reproduced, not inferred**: a scripted scenario
  driving the real `_execute_concurrent()` (move 201 in flight and slow to resolve, move 202's
  VM vanished from `cluster/resources`) produces `outcomes == [(202, "replan_needed"),
  (201, "moved")]` with `stopped_early=True` — the `replan_needed` outcome is *not* last, so
  `cli.py:1723`'s `outcomes[-1].status == "replan_needed"` check answers False and no re-plan
  happens. The scenario uses only the existing test doubles (`concurrent_client_with` with
  201's task-status poll scripted to stay `"running"` for two cycles and 202 removed from
  `cluster/resources`), so it converts directly into the regression test T-01 asks for.
- Time-window behaviour spot-checked against the test suite's 16 cases (cross-midnight matching
  against the *start* day, DST spring-forward non-crash, `current_deadline()`'s
  "no active window → zero budget" and "no windows at all → unbounded" conventions) — all
  consistent with section 9.1 and the module's own docstrings.
- The §14 fixture arithmetic is untouched by this range (no solver or objective changes);
  fixture freshness re-confirmed above.

### 19.2 Findings summary

| ID | Severity | Module(s) | Summary |
|----|----------|-----------|---------|
| T-01 | Medium | `cli.py`, `execute.py` | `auto`'s re-plan loop never triggers under the concurrent executor — a launch-time mismatch resolved while another move is in flight is not the *last* outcome, and `outcomes[-1]` is how the loop detects it; the run stops early instead of re-planning (§9.2 step 3), and the manual's auto-mode "re-plan loop" promise silently does not apply under concurrency |
| T-02 | Medium | `cli.py` | §9.2 step 2 ("record the moves already completed in state.json, *including their cooldown timestamps*") is honored only after a group's whole auto loop ends — a re-plan inside the loop plans against the pre-group state, without the earlier attempts' cooldown pins or an updated `last_balance`, so a just-moved disk can be re-proposed (and moved back) within the same invocation; and if a later move raises, the finally-block save persists a state that never got those cooldowns at all |
| T-03 | Medium | `docs/manual/10-configuration.md`, `config/drs.example.yaml`, plan §10.1/§10.2 | The manual and example config claim the *optimizer* consumes `window.upper_quantile` / the forecaster's upper bound; in the finalized code the optimizer consumes the `window.quantile` (p95) decision statistic and only the section 7.3 saturation guard (when `saturation_load` is set) consumes bounds — the P-01/P-02/S-08 pattern again, plus a plan section now contradicted by the code with no annotation |
| T-04 | Low | `execute.py`, `docs/internals/92-execute.md` | Stale "section 7.3's saturation check … is not implemented anywhere in this codebase yet" claims (module docstring, `_execute_concurrent` docstring, `92-execute.md`) — contradicted by the saturation wiring that landed two commits later in this same range and by sibling docs that describe it |
| T-05 | Low | `docs/internals/96-payback.md` | The page still says the payback benefit "takes two `ObjectiveBreakdown.imbalance_term` values … passed straight through" — false since the R-01 fix switched to `raw_spread()`; an implementer following this page would reintroduce the R-01 bug |
| T-06 | Low | `execute.py`, `cli.py` | Three divergent semantics for the `max_migrations_per_run` counter: the sequential executor counts lock-timeout and post-lock-wait-deadline *skips* (moves never issued), the concurrent executor counts launches only, and `_run_auto_group`'s cross-group decrement counts moved/draining/failed — the cap is never exceeded, only under-consumed, but the one-rule discipline is broken; collateral: the post-lock-wait deadline skip continues the loop instead of stopping the run, contradicting `_auto_budget_stop_outcome`'s own documented "stop cleanly, never skip this one" policy |
| T-07 | Info | `cli.py` | `_plan_group()` computes `_saturation_forecast_inputs()` (six `query_range` calls over up to 7 days at 5-minute step) even when `schedule_result.order` is empty (full deadlock) — the guard's outputs are then unused; performance note only |

### 19.3 T-01 — the re-plan loop does not trigger under concurrent execution

**Severity:** Medium
**Files:** `src/proxmox_storage_drs/cli.py:1723`, `src/proxmox_storage_drs/execute.py:1176-1284`

`_run_auto_group()` decides whether to re-plan with:

```python
needs_replan = bool(result.outcomes) and result.outcomes[-1].status == "replan_needed"
```

This is correct for the sequential executor, where a `replan_needed` outcome always ends
`execute_plan()` immediately and is therefore last. The concurrent executor cannot return
early: once a stop condition is set it keeps polling the still-in-flight moves to their natural
conclusion (by design, and correctly — their outcomes and crash-recovery callbacks must still
be recorded), and those resolutions are appended to `outcomes` *after* the `replan_needed`
outcome that `_advance_pending()` recorded mid-run. Reproduced against the real executor
(19.1): outcomes arrive as `[(202, "replan_needed"), (201, "moved")]`, `outcomes[-1]` is the
`moved`, and the loop breaks without re-planning.

Consequences: under `execution.max_concurrent_migrations > 1` — the exact configuration the
concurrent executor exists for — a normal mid-run mismatch stops the run instead of triggering
section 9.2 step 3's "re-invoke the whole pipeline from the new observed state". The behavior
is conservative (nothing unsafe executes; the next timer invocation re-plans from reality), but
it contradicts the plan, diverges from the sequential path, and silently narrows the manual's
own auto-mode contract (`docs/manual/28-apply.md`'s "The re-plan loop" bullet promises the
re-plan for `auto` with no concurrency qualifier). The suite cannot see it: every re-plan test
stubs `_apply_payback_gate` with a single `replan_needed` outcome, and every concurrent
executor test that produces `replan_needed` has nothing else in flight (`test_concurrent_preflight_mismatch_replans_and_stops`).

**Recommendation:** decide re-planning on membership, not position — `any(o.status ==
"replan_needed" for o in result.outcomes)` over the per-attempt result (safe: `"replan_needed"`
is only ever produced at launch time, never by polling, so this cannot fire spuriously) — and
add a regression test that drives the real `_execute_concurrent()` with one move in flight
while the head of pending fails pre-flight.

### 19.4 T-02 — executed moves' cooldowns are not recorded where section 9.2 step 2 needs them

**Severity:** Medium
**Files:** `src/proxmox_storage_drs/cli.py:1630-1767` (`_run_auto_group`), `cli.py:1770-1822`
(`_record_executed_moves`), `IMPLEMENTATION_PLAN.md` §9.2 step 2

Section 9.2's re-plan protocol is explicit that recording precedes re-invoking: "Record the
moves already completed in `state.json` (including their cooldown timestamps) so the next pass
sees them as history rather than re-deriving them" (step 2), *then* "re-invoke the whole
pipeline" (step 3). The implementation records `last_balance` and per-disk/per-storage
cooldowns only in `_handle_apply()`'s loop, after `_run_auto_group()` has returned for the
whole group. Two consequences:

1. **The re-plan plans against stale state.** The loop's re-plan passes the `state` snapshot
   from *before the group started* to `build_topology(state=...)` (the (C2) per-disk cooldown
   pin) and `_plan_group(..., state, ...)` (`active_storage_cooldowns`, and the drift gate's
   `last_balance`). A move executed in attempt 1 has no cooldown recorded when attempt 2
   solves, so nothing structurally prevents attempt 2 from proposing the same disk again —
   including back to where it came from — which is precisely the churn `cooldown_per_disk`
   exists to prevent. It also means the re-plan's drift gate compares against a baseline that
   predates the moves this run already executed. The load-model/topology re-fetch limits the
   damage (the disk's new location is real, and the gate often concludes "no action"), but the
   protection the plan mandates for exactly this loop is absent.
2. **The crash window loses them entirely.** If a later move in the same group raises (a
   network failure mid-poll, say), the `finally` block saves `state_box.value` — which carries
   the live `inflight_upids` updates (by design) but none of the executed moves' cooldowns or
   `last_balance`, since `_record_executed_moves` was never reached. The next run then starts
   with no cooldown for disks that really moved, and no drift baseline. The UPID trace is
   cleared for tasks that finished, so nothing else marks those moves as recent history.

**Recommendation:** record per *attempt*, not per group: call `_record_executed_moves` (or a
subset of it, keyed on the attempt's own outcomes and load vector — the docstring already
notes which statuses count) inside `_run_auto_group()` after each `_apply_payback_gate()` call,
pushing the result into `state_box`/`state` before the re-plan re-invokes the pipeline; and
for the crash window, record after each *resolved* outcome (or at minimum wrap the per-group
call so an exception still records what completed before propagating). Either way the
`finally`-block comment's own reasoning — never clobber the newest state — extends naturally:
what is saved should also be the newest *cooldown* state, not just the newest inflight state.

### 19.5 T-03 — "the optimizer consumes the upper bound": manual and config say yes, code says no

**Severity:** Medium
**Files:** `docs/manual/10-configuration.md` (`window.upper_quantile`, `forecast.holt_winters.residual_z`),
`config/drs.example.yaml:86`, `IMPLEMENTATION_PLAN.md` §10.1/§10.2, `src/proxmox_storage_drs/loadmodel.py:113`

The finalized implementation has exactly one consumer of a `Forecaster`: the section 7.3
saturation guard (`cli._saturation_forecast_inputs()` → `forecast.storage_upper_bound()` →
`payback.compute_move_cost()`), and only when some storage in the group configures
`saturation_load`. The decision statistic that drives gates, solver, payback and ordering is
`compute_group_load()`'s PromQL `quantile_over_time` at `window.quantile` (p95, the point
estimate) — `loadmodel.py:113-114`. `docs/internals/20-forecasting.md` says so honestly:
"the optimizer does not consume a forecast at all yet."

The operator-facing documentation does not:

- `window.upper_quantile`: "The quantile the **optimizer** and the saturation guard actually
  consume" — the first half is false.
- `forecast.holt_winters.residual_z`: "this is what the optimizer actually consumes".
- `config/drs.example.yaml:86`: "the bound the OPTIMIZER consumes (>= quantile)".

This is the P-01/P-02/S-08 pattern a fourth time: a knob documented as feeding a consumer it
does not feed. An operator who raises `upper_quantile` (or tunes `residual_z`) expecting a more
conservative *placement* gets no change in placement at all unless they also set
`saturation_load`. Additionally, the plan's own §10.1 sentence — "The optimizer consumes the
**upper bound**, never the point estimate … so the optimizer sees p99" — and §10.2's "Refuse to
let a model whose backtest error exceeds the imbalance threshold **drive migrations**" are now
unconditionally contradicted by the finalized code, with no plan-side annotation (AGENTS.md
§7.6: resolve the disagreement in the same commit; `IMPLEMENTATION_PLAN.md` was not touched
once in this entire range).

**Recommendation:** either (a) fix the three operator-facing claims to name the only real
consumer ("the section 7.3 saturation guard, when `saturation_load` is set"), and add the
plan-side annotation ("as built, the decision statistic is `window.quantile`; the bound is
consumed by the saturation guard only — wiring forecasts into the optimizer remains future
work"), or (b) actually wire the bound into the decision statistic (fetch at
`window.upper_quantile`) if that was always the intent. (a) is the smaller, honest fix; (b)
changes every fixture cross-check and should not be done silently. The documentation
cross-reference tests only check knob *existence*, which is why this survived them.

### 19.6 T-04 — stale "saturation check not implemented anywhere" claims

**Severity:** Low
**Files:** `src/proxmox_storage_drs/execute.py:37-38`, `execute.py:1325-1329`,
`docs/internals/92-execute.md:169-171`, `docs/manual/28-apply.md` ("Concurrent execution")

`execute.py`'s module docstring and `_execute_concurrent()`'s docstring say section 7.3's
saturation check "is not enforced anywhere in this codebase yet", and `92-execute.md` repeats
"**It is not implemented anywhere in this codebase yet** (`docs/internals/96-payback.md`)".
All three were written in the concurrent-execution commit (`a59c613`) and were true then; the
saturation wiring landed two commits later (`d94807a`/`10a9ead`, same review range) and they
were never revisited — `10a9ead` does not touch `execute.py`. They now contradict
`96-payback.md`'s own saturation section and `30-safety-and-status.md`'s `plan` row ("including
the section 7.3 saturation-ceiling guard (mirroring phase only)"), so the documentation set
disagrees with itself. `28-apply.md`'s "Section 7.3's saturation check is not enforced under
concurrency any more than it is under the sequential executor" is misleading the same way: the
planning-time defer check gates `apply` in both paths (`_apply_payback_gate` excludes
`deferred_moves`). What remains true is the narrower statement — there is no *execution-time*
saturation re-check summing `ω_role` over the in-flight set (§8.1 condition 4), and no
draining-phase check.

**Recommendation:** reword the three claims to the narrow true statement ("the planning-time
defer check exists (`96-payback.md`); no execution-time re-check against the live in-flight
set, mirroring or draining phase, under either executor"). This is R-04's pattern — a doc
sentence whose truth ended mid-range — and the same-commit rule applies.

### 19.7 T-05 — `96-payback.md` would reintroduce the R-01 bug

**Severity:** Low
**Files:** `docs/internals/96-payback.md:13-17`

The page opens: "`compute_benefit_load_seconds()` takes two
`heuristic.ObjectiveBreakdown.imbalance_term` values — the pre-plan and post-plan `E` — and
multiplies their difference by `migration.payback_horizon_seconds`; `heuristic.HeuristicResult`
already carries both … so `cli.py`'s `plan` handler passes them straight through." Since the
R-01 fix (ninth pass, `de7deda`), none of that is true: the handler passes
`heuristic.raw_spread()` values, precisely because `imbalance_term` is `alpha_spread`-scaled
and made the payback ratio depend on a solver tuning knob. The paragraph dates from the phase-5
commit (`f0f955d`) and the R-01 fix updated the docstring and this review but not this page. An
implementer who reads `docs/internals/` (as AGENTS.md §8.2 tells them to) and trusts it over
the docstring would wire `imbalance_term` back in — reintroducing a resolved finding with a
`alpha_spread ≠ 1.0` plan silently getting wrong payback arithmetic.

**Recommendation:** rewrite the paragraph to name `raw_spread()` as the required input and
`imbalance_term` as the wrong one (mirroring `compute_benefit_load_seconds()`'s own
already-correct docstring).

### 19.8 T-06 — three semantics for one cap

**Severity:** Low
**Files:** `src/proxmox_storage_drs/execute.py:894` (sequential), `execute.py:1276`
(concurrent), `src/proxmox_storage_drs/cli.py:1719-1721` (cross-group budget)

`execution.max_migrations_per_run` is enforced by three counters that count different things:

- the sequential executor increments `migrations_used` after **every** `_execute_one_move()`
  outcome — including a lock-timeout `"skipped"` (`locks.on_timeout: skip`) and the
  post-lock-wait deadline `"skipped"`, neither of which issued a `move_disk`;
- the concurrent executor increments only on an actual **launch**;
- `_run_auto_group()` decrements the cross-group budget by outcomes with status
  `moved`/`draining`/`failed` — excluding exactly those skips.

The cap can therefore only ever be under-consumed (the sequential path stops earlier than
configured when lock-timeout skips occur), never exceeded, so this is not a safety issue — but
it is three implementations of one rule where AGENTS.md §5 asks for one, and the sequential and
concurrent executors give different answers to "did that skipped move consume budget?".
Collateral detail: the post-lock-wait deadline skip *continues* the loop (the next iteration's
budget check then stops the run), which contradicts `_auto_budget_stop_outcome()`'s own
documented policy that both budgets mean "stop cleanly, never skip this one and try a later
move" — the run ends one outcome and one skipped line later than that policy describes, having
also consumed one unit of the sequential counter for a move that never launched.

**Recommendation:** pick one semantics — launches only (matching the concurrent path and the
plan's own "how many moves one invocation *executes*") is the natural choice: increment only
for outcomes that actually issued a `move_disk`, in both executors, and have the cross-group
decrement match. Then the post-lock-wait deadline skip can stop the run directly instead of
falling through to the next iteration, matching the documented policy.

### 19.9 T-07 — saturation history fetched for a plan with nothing to check (Info)

`_plan_group()` calls `_saturation_forecast_inputs()` unconditionally after ordering
(`cli.py:1302`), before knowing whether `schedule_result.order` is empty. A fully-deadlocked
plan (order empty, `deadlocked` non-empty) still pays six `query_range` calls over the
configured forecaster's `required_range()` — up to 7 days at a 5-minute step for
`seasonal_naive` — for a guard whose inputs are then unused. Cheap fix if ever worth it: fetch
lazily only when `order` is non-empty. Recorded for completeness; no correctness impact.

### 19.10 What this pass confirms

- **The time-window module is right, including its hard parts.** Cross-midnight windows match
  the day the window *started* on; `current_deadline()`'s three-state convention (no windows →
  unbounded, none active → zero budget, several active → latest close) is exactly what an
  executor needs to refuse work without a second activeness check; local-vs-UTC is a
  deliberate, documented choice; and `_real_local_now()`'s `/etc/localtime` IANA-zone
  resolution closes the DST hole a bare `astimezone()` would leave in `window_close()`'s
  "closes tomorrow" case, with the residual fixed-offset fallback gap documented rather than
  hidden. `start == end` is rejected at config validation.
- **The crash trace is genuinely written before the crash can happen.** `on_inflight_started`
  persists through the still-held `flock` immediately after `move_disk()` returns and before
  any other use of the UPID; `on_inflight_finished` fires when the *task* resolves (including
  `draining`, correctly — the drain is tracked by the content poll, not the UPID); a raise
  mid-wait deliberately leaves the UPID recorded; and the `finally` block saves the box's
  newer state over the loop's older local variable so the trace cannot be clobbered. The
  startup scan's local half re-checks remembered UPIDs (a failed check assumes still-running,
  the safe direction), the cluster half scans `/cluster/tasks` for same-user `qmmove` tasks
  with the confirmed-live field convention, discovered vmids fold into `exclude.vmids` reusing
  the existing (C2) pin, and nothing is ever force-cancelled.
- **The generalized transient invariant is the one arithmetic core the plan asked for.**
  `reserve.transient_charge_ok()` implements `used + Σz_m + f·max(Z, max z_m) ≤ C` with the
  `min_free_bytes` floor (F-02) folded in; `schedule.transient_invariant_ok()` calls it with
  one charge, the sequential executor's live check with one charge against a live
  `storage_status()` read, and `_launch_decision()` with the whole in-flight target-charge set
  plus `largest_by_storage` updated by `_post_move_bookkeeping` — deliberately conservative
  about whether a live `used` already reflects an in-flight allocation.
- **The concurrent executor's decomposition is sound.** Strict FIFO (documented as
  under-delivering on throughput, never unsafe), non-blocking per-move polling via
  `_poll_move_once()` (the shared three-condition completion criterion), the two-condition
  stop-then-drain loop that never abandons an in-flight move, per-storage caps counting both
  endpoints, the deadline re-checked every cycle (so the sequential path's post-lock-wait
  re-check has a concurrent equivalent by construction), and the spin-guard break condition
  once `stop_reason` is set.
- **The saturation guard and backtest gate are honest about their own scope.** The defer check
  is per-endpoint, skipped where `saturation_load` is unset, charged with the same
  `ω_src`/`ω_dst` the cost model already uses, reported separately from hard rejections, and
  excluded from execution exactly like them; a reserve-resolving plan stays exempt from the
  economic test but not from the hard rules (documented in `30-safety-and-status.md`); the
  backtest gate never validates `quantile`, treats missing history as failure, falls back
  with one warning, and reuses `gates.imbalance_threshold` per the plan's own yardstick.
- **The S-02 payback gate survives the new modes intact**: `deferred_moves` join
  `rejected_moves` in `_refused_move_outcomes`, the aggregate failure still refuses the whole
  group with zero API calls, and the confirm-mode payback preview still prints before the
  first prompt.
- **Documentation discipline mostly held**: the S-08 "not yet effective" caveats were properly
  *removed* from the four phase-8 knobs now that phase 8 is real, `28-apply.md` documents FIFO
  concurrency and the drain-first behavior accurately, `15-state.md` was updated for the now-
  live `inflight_upids`, and `95-schedule.md` was rewritten rather than left claiming the
  generalized invariant was unimplemented. The exceptions are T-04/T-05 — both staleness
  introduced or left behind inside this same range.

### 19.11 Assessment

The finalized implementation is, mechanism for mechanism, the best-reviewed state of this
codebase: every phase of the plan now exists, the two High-severity classes of the tenth pass
(crash-the-packaged-solver, execute-what-was-rejected) stayed fixed, and the new unattended
machinery carries its own tests (123 new ones across the range: 459 → 582 total) and
mostly-current documentation. The three Medium findings are all composition bugs at the seams the plan
explicitly legislates — the re-plan protocol (T-01, T-02) and the forecast-consumption
contract (T-03) — and none of them makes the tool do something unsafe: T-01 and T-02 err
conservative (less work, possible churn within a run), T-03 is a documentation lie rather than
a behavior change. Fixing T-01 is a one-line predicate plus a regression test; T-02 is a
recording-point move; T-03 is three sentence-level corrections plus a plan annotation. After
those, the remaining open items in the codebase are the deliberately documented gaps
(execution-time saturation sums, §7.3's re-solve loop, staging, concurrency-aware ordering),
each of which the internals pages already name honestly.

---

## 20. Resolution of eleventh-pass findings (T-01..T-07)

All seven findings were real; all seven are fixed, not refuted.

| ID | Status | How resolved |
|----|--------|--------------|
| T-01 | Resolved | `cli._run_auto_group()`'s `needs_replan` now checks `any(o.status == "replan_needed" for o in result.outcomes)` instead of `outcomes[-1].status` — safe because `"replan_needed"` is only ever produced at launch time, never by polling an already-in-flight move to its own conclusion, so this cannot fire for an outcome that was actually a clean completion. New regression test `test_concurrent_replan_mismatch_can_land_before_a_still_inflight_moves_outcome` (`test_execute.py`) reproduces the exact scenario the review found against the real `_execute_concurrent()` (a slow-to-resolve in-flight move plus a vanished-VM mismatch behind it), and `test_run_auto_group_replans_when_the_mismatch_is_not_the_last_outcome` (`test_cli.py`) pins the fixed predicate itself. |
| T-02 | Resolved | `_run_auto_group()` now threads the caller's `_InflightStateBox` (renamed parameter, `state` → `state_box`) instead of a plain `State`, and calls `_record_executed_moves()` on `state_box.value` immediately after each attempt's own `_apply_payback_gate()` call — using that attempt's own `group_plan.group_load` reading, already computed, no extra fetch — *before* a re-plan's `build_topology()`/`_plan_group()` calls, which now read `state_box.value` rather than the pre-group snapshot. `_handle_apply()`'s own post-loop recording is skipped for `mode == "auto"` (it would otherwise overwrite a later attempt's fresher `last_balance` with the first attempt's stale one) and simply picks up `state_box.value`; the crash-window half is fixed for free, since `_handle_apply()`'s `finally` block already saves `state_box.value`, not the loop's local `state`. New test `test_run_auto_group_records_each_attempts_cooldown_before_replanning` asserts the re-plan's own `build_topology()` call already sees the first attempt's cooldown, and that the box a crash would save reflects it too. |
| T-03 | Resolved | Added an "As built" paragraph to `IMPLEMENTATION_PLAN.md` §10.1 stating plainly that the decision statistic driving gates/solver/payback/ordering is `window.quantile` (the point estimate), that the upper bound's only real consumer is the §7.3 saturation guard, and that wiring the bound into the optimizer's own input remains future work — the §15.1 knob table row updated to match. `docs/manual/10-configuration.md`'s `window.upper_quantile` and `forecast.holt_winters.residual_z` entries, and `config/drs.example.yaml`'s `upper_quantile` comment, rewritten to name the saturation guard as the actual consumer instead of "the optimizer". Chosen over actually wiring the bound into the optimizer (the review's option (b)) because that would change every fixture cross-check and should not be done as a documentation fix. |
| T-04 | Resolved | Reworded all three stale claims (`execute.py`'s module docstring, `_execute_concurrent()`'s own docstring, `docs/internals/92-execute.md`) to the narrower true statement: the §7.3 defer check is enforced at planning time (a flagged move never reaches either executor), and what remains unimplemented is only an *execution-time* re-check of the ceiling against the live in-flight set, mirroring or draining phase, under either executor. `docs/manual/28-apply.md`'s equivalent paragraph corrected the same way. |
| T-05 | Resolved | Rewrote the opening paragraph of `docs/internals/96-payback.md` to name `heuristic.raw_spread()` as `compute_benefit_load_seconds()`'s required input and `ObjectiveBreakdown.imbalance_term` as the wrong one (mirroring the R-01 fix's own already-correct docstring and rationale), replacing the phase-5-era claim that `cli.py` passes `imbalance_term` straight through. |
| T-06 | Resolved | Picked launches-only semantics everywhere, keyed off `MoveOutcome.upid is not None` (only ever set once `move_disk` actually returned one): `_execute_sequential()` now increments `migrations_used` only for a launched outcome, not a lock-timeout or post-lock-wait-deadline skip; `_run_auto_group()`'s cross-group budget decrement switched from `status in ("moved", "draining", "failed")` to `o.upid is not None` for the same reason (a lock-timeout-abort `"failed"` never launched either); the concurrent executor already counted launches only and needed no change. The collateral bug is fixed too: the post-lock-wait deadline skip now sets `always_stop=True` (extending, not narrowing, that field's existing purpose) and `_post_move_bookkeeping()` stops the run on a `"skipped"` outcome with `always_stop` set, matching `_auto_budget_stop_outcome()`'s own documented "stop cleanly, never skip this one" policy. Three new tests: `test_lock_timeout_skip_does_not_consume_the_max_migrations_per_run_budget` (budget untouched by a skip), `test_deadline_recheck_after_a_lock_wait_stops_the_whole_run_not_just_this_move` (a second, fully launchable move is never attempted), plus new assertions on the pre-existing single-move deadline-recheck test. |
| T-07 | Resolved | `_plan_group()` now computes `_saturation_forecast_inputs()` only when `schedule_result.order` is non-empty (`None` otherwise) — a fully deadlocked plan no longer pays the guard's `query_range` fetches (up to 7 days at a 5-minute step) for a result nothing will use. |

Verification: dev venv `python3 -m pytest` — **563 passed, 24 skipped** (ortools, pulp and
statsmodels absent), **91.31% line coverage** (up from the eleventh pass's 91.28% despite the
new regression tests; `execute.py`/`cli.py` both still at 99% under their own test files).
`make check` clean (fmt, lint, typecheck, test, fixtures, docs-check — `IMPLEMENTATION_PLAN.pdf`
rebuilt to 40 pages, internals PDF to 42, manual PDF to 34, all three stamps regenerated in the
same commit as their Markdown per AGENTS.md §7).

---

## 21. Twelfth-pass review — dogfooding fixes, CI repairs, section 11.4 storage patterns

Reviewed commit range `deeae75..HEAD` (the T-01..T-07 fixes themselves are already recorded in
section 20). Seven commits: `bc7df89` (two real bugs found dogfooding against the
`pve.bzed.at` production cluster — the heuristic's missing whole-VM co-relocation candidate,
and the `requests` connection pool being smaller than `read_workers`'s default), then five CI
repairs found the first time the pipelines actually ran (`bfccabb` python3-flake8-bugbear does
not exist in Debian; `22973b2` three tests assumed `solver.backend: auto` resolves to heuristic;
`8921bf7` ca-certificates dropped by `--no-install-recommends`; `f5f8830` mypy needs
python3-typeshed plus a state.py flow-narrowing refactor; `3c1000a` codecov's missing curl/gpg
and its deprecated test-results action), then `1bdb010` — the section 11.4 `/regex/`
storage-pattern feature, the first new plan section added since the implementation was
finished (bc7df89's §5.5 change above amended existing text rather than adding a section).
Roughly 1,200 inserted lines, of which ~500 are tests.

The range's quality bar stays high. The dogfooding fix is the right kind: found on a real
cluster, minimized into a hand-verified regression test whose arithmetic checks out to the
digit, scored exclusively through the shared `evaluate_assignment()` so the new candidate
family cannot regress the objective, with the plan's own §5.5 step 3/4 text updated in the
same commit (the whole-VM candidate documented, polish's remaining scope narrowed to the
N-way rotation). The §14 fixture totals are unaffected (the new family is a strict superset of
what descend could already reach, and the fixture tests still assert 2.533333/3.158333). The
pattern feature's expansion design is clean: expansion happens exactly once, in topology,
against the live cluster; nothing downstream — `D`/`S`, (C2), cooldown keys, `state.json` —
ever sees a pattern; literal-over-pattern precedence is a dict overwrite, so file order cannot
matter; both hard-error cases (zero matches, two patterns claiming one storage) plus the
cross-group collision get the same treatment section 11.1 already gives an unknown literal id;
and the schema change (structural `minItems` 2→1 vs. the semantic ≥2-after-expansion rule
deferred to topology) is a sensible factoring. The five CI repairs each document their root
cause in the workflow header and stay inside the §9.3 "apt, never pip" policy.

### 21.1 Verification run

- Dev venv `python3 -m pytest`: **586 passed, 24 skipped** (ortools, pulp, statsmodels absent),
  **91.65% line coverage** — above the 85% floor and up from the eleventh pass's 91.31%.
- System Python (pulp **2.7.0**, the exact Debian trixie / CI version): **597 passed,
  13 skipped** — the CBC backend exercised for real (the S-01 fix holds), and the `22973b2`
  test pinning means the environment-dependence is gone: with pulp importable, `auto` picks
  cbc and the heuristic-specific tests still pass because they now name their backend.
- `tests/fixtures/generate_expected.py --check`: OK. `sha256sum --check` on all three PDF
  stamps (plan, internals, manual): all OK. `make docs-check` exits 0. `black --check`,
  `flake8`, `mypy`: clean.
- **U-01's failure mode was reproduced, not inferred**: with a fake client carrying `san-z`
  in `GET /storage` definitions but absent from `GET /cluster/resources?type=storage` (the
  shape of a disabled storage), a group written as `/san-.*/` aborts the whole run with
  `TopologyError: storage 'san-z' is not reported active on any node` — a message naming a
  storage the operator never wrote, with no hint that a pattern pulled it in.
- **U-03's asymmetry was reproduced the same way**: the same not-`shared` storage produces
  the "not marked shared" warning when named literally and no warning at all when matched by
  a pattern.
- The new heuristic test's arithmetic hand-verified: initial `E = |1.26−0.63| + |0−0.63| =
  1.26` ✓; one disk moved alone `0.89 + 0.25 + 0.05 + 0.5(κ) = 1.69` — worse, exactly as the
  test asserts ✓; both disks together `0.52 + 0.5 + 0.1 = 1.12`, an improvement of 0.14 ✓
  (matching the docstring's −0.14).

### 21.2 Findings summary

| ID | Severity | Module(s) | Summary |
|----|----------|-----------|---------|
| U-01 | Medium | plan §11.4 vs `topology.py` | The plan says patterns are matched against `GET /cluster/resources?type=storage`; the code matches against `GET /storage` (definitions) — and the untested matched-but-unavailable edge aborts the run with `_pick_active_node`'s generic error, which does not name the pattern that pulled the storage in |
| U-02 | Low | `docs/internals/*.md`, `docs/manual/25-*.md` | Six stale "not yet written"/"remain stubs" claims (`execute.py`, `optimize.py`, `heuristic.py`, `apply`), all false since phases 4-7; one is operator-facing manual text about `last_balance` never being written |
| U-03 | Info | `topology.py`, plan §11.4 | Second, undocumented pattern asymmetry: a matched storage skips the not-`shared` warning a literal entry gets — §11.4 documents only the `images` asymmetry |

### 21.3 U-01 — plan names one endpoint for pattern matching, code matches another; the unmatched edge aborts unhelpfully

**Severity:** Medium
**Files:** `IMPLEMENTATION_PLAN.md` §11.4, `src/proxmox_storage_drs/topology.py:419-449`
(`_fetch_cluster_data`), `topology.py:203-215` (`_pick_active_node`)

Plan §11.4: "Every pattern is matched once per run against the storage inventory
(`GET /cluster/resources?type=storage`, §3.5)". The code matches against
`definitions_by_id`, built from `client.storage_definitions()` = `GET /storage` — storage
*definitions*, which §3.5's own table distinguishes from the *inventory*. The internals doc
(`60-topology.md`) describes the definitions endpoint, so the plan is the outlier; per
AGENTS.md §7.6, one of them is wrong and they should have agreed in the same commit. This is
the T-03 pattern (plan text contradicted by the built code with no annotation) applied to a
mechanism rather than a consumer.

The two sets are not identical: definitions include storages the resource inventory does not
report (a disabled storage still has a definition). That difference has a concrete, reproduced
failure mode (21.1): a pattern that matches such a storage passes expansion cleanly, becomes
a group member, and then dies in `_pick_active_node` with "storage 'san-z' is not reported
active on any node" — an error that names neither the group's pattern nor the fact that a
pattern matched the storage at all. The operator never wrote `san-z`; they wrote `/san-.*/`,
and the one piece of context that would explain the failure is absent. No test covers the
case. It also undercuts §11.4's own framing of over-broad matches ("a pattern that captures
an ISO-only or otherwise unusable LUN skews the balance target even though (C2) keeps any
disk from ever landing there"): for the not-active LUN that story is wrong — the run does not
degrade to a balance-quality concern, it aborts outright.

Two mitigating facts, for fairness: the behavior is fail-safe (hard error, nothing executes),
and a *literal* reference to a disabled storage hits the same wall today, so the crash itself
is pre-existing — what the pattern adds is a new, quieter route into it (you no longer have
to name the storage to pull it in) plus the plan/code text disagreement.

**Recommendation:** (a) fix the plan's §11.4 sentence to name `GET /storage` (definitions) —
which is also what literal-id validation uses, so plan and code then tell one story; (b) add
a test for the matched-but-unavailable storage; (c) make the error name the cause: during
expansion, check each matched id against the resource inventory and raise a pattern-specific
`TopologyError` there ("group 'g1' pattern '/san-.*/' matched storage 'san-z', which no node
reports active — disable-safe patterns must exclude it"), rather than letting
`_pick_active_node`'s storage-only message surface three steps later. Deciding *which* set is
semantically right is the author's call — matching definitions makes `unmanaged_storage_ids`
complete, matching the inventory would exclude disabled storages naturally — but the plan,
the code, and the error message must agree, and the case must be tested either way.

### 21.4 U-02 — six stale "not yet written" claims across the internals and manual

**Severity:** Low
**Files:** `docs/internals/60-topology.md:78,198`, `docs/internals/80-gates.md:65`,
`docs/internals/90-heuristic.md:218,223`, `docs/manual/25-show-load-and-verify-storages.md:62`

A sweep for "not yet written"/"remain stubs" found six claims that later phases falsified and
nobody revisited:

| Location | Claim | False since |
|---|---|---|
| `60-topology.md:78` | "`execute.py`, not yet written" | phase 7 (`c6760c9`) |
| `60-topology.md:198` | "the solver (`optimize.py`/`heuristic.py`, not yet written)" | phase 4 (heuristic) / phase 6 (optimize) |
| `80-gates.md:65` | "`apply` (not yet written)" | phase 7 (`c6760c9`) |
| `90-heuristic.md:218` | "`optimize.py`, not yet written" | phase 6 (`375d3a9`) |
| `90-heuristic.md:223` | "`explain`/`apply` remain stubs" | phase 7 — the `explain` half is still true, the `apply` half is not |
| `25-show-load-and-verify-storages.md:62` | "nothing yet *writes* `last_balance` (that needs `execute.py`, not yet written)" | phase 7, and the T-02 fix now records it per auto-mode attempt |

This is the R-04/T-04/T-05 class at cluster scale: each phase landed without sweeping the
*older* internals pages for claims its own landing invalidated — the per-command status table
(`30-safety-and-status.md`) and the newer pages were kept honest, but the prose in the
foundational pages was not. The manual entry is the worst of the six because it is
operator-facing and asserts something false about state writes ("this stays the common case
until a migration has actually run" is now wrong in both directions: `apply` writes
`last_balance`, and after any executed move the drift gate has real history). The
documentation cross-reference tests check knob existence and CLI-option coverage, not prose
truth — already noted in T-03 — which is how six of these survived three review passes that
each fixed one instance of the same disease.

**Recommendation:** one sweep commit fixing all six, in the same commit-style as T-04/T-05.
Mechanical guard worth considering: a documentation test that greps the docs for module-name
mentions in "not yet written"/"not yet implemented" phrasings and fails when the named module
exists and is wired — cheap, and it turns this whole class from "found by reviewer" into
"found by `make check`".

### 21.5 U-03 — matched storages silently skip the not-`shared` warning (Info)

**Severity:** Info
**Files:** `src/proxmox_storage_drs/topology.py` (`_expand_group`), plan §11.4

`_expand_group`'s "not marked shared" warning lives inside the literal-entry loop only, so a
storage matched by a pattern gets no warning even though the manual and `60-topology.md`
describe the warning as a property of the storage, not of how it was named. Reproduced
(21.1): the same not-`shared` storage warns when written literally, is silent when matched by
`/san-.*/`. §11.4 documents exactly one asymmetry (the `images` content check) and grounds it
in the typo-vs-overreach distinction; the `shared` warning is the same kind of
quality-not-safety signal and almost certainly intends the same treatment, but nothing says
so — an operator reading §11.4's "a matched storage becomes a full member of the group,
exactly as a literal entry" could reasonably expect the warning.

**Recommendation:** one sentence in §11.4's closing paragraph (and `60-topology.md`'s
asymmetry paragraph) extending the documented asymmetry to the not-`shared` warning — or,
simpler and arguably better, emit the warning for pattern matches too (the definition is in
hand; there is no typo-exemption reason to stay quiet about a non-shared match). Either way,
the plan's claim "exactly as a literal entry" should stop over-promising.

### 21.6 What this pass confirms

- **The heuristic fix is the model dogfooding outcome.** The production failure (196%
  imbalance, zero improving moves, two-disk VM pinned in place by `κ`'s fragmentation penalty)
  is minimized into a test whose every number hand-checks; the new `_vm_relocation_trials()`
  family is scored by the same `evaluate_assignment()` as the other two (AGENTS.md §5's
  one-implementation rule), respects `cooldown_storages` as a destination exclusion exactly
  like them, and is restricted to VMs with more than one *movable* disk — the single-movable-
  disk case already being the plain single-move candidate, so nothing is tried twice. The
  `_best_of()` extraction preserves the incumbent comparison semantics exactly (strict `<`,
  deterministic family order); §5.5's step 3 was amended and step 4's remaining scope
  narrowed in the same commit, per AGENTS.md §7.6.
- **The connection-pool fix follows the house pattern for proxmoxer internals.**
  `_apply_connection_pool_size()` reaches into `_store["session"]` exactly the documented,
  best-effort way `_apply_ticket_refresh_seconds()` does; it never shrinks below `requests`'
  own default of 10; it is a guarded no-op for every wrong-shaped future; it is applied in
  `_build_api()` so reauthenticate-rebuilt sessions get it too; and the no-op shapes are
  tested. Mounting one adapter instance on both scheme prefixes is sound (urllib3 keys an
  adapter's pools by scheme+host, so sharing one adapter is standard practice).
- **Pattern expansion leaves no pattern-shaped holes downstream.** Every consumer of group
  storages — `D`/`S`, gates, load model, heuristic, MILP, scheduler, executor, cooldown keys,
  `verify-storages` — reads the topology `Group.storages` built from the expanded list;
  nothing past topology ever reads raw `config.groups[*].storages` (the only remaining
  consumers are `config.py`'s own load-time validators, which must see the raw entries to
  check them). Expansion ordering is deterministic (sorted ids),
  `matched_ids` is stable across runs for `verify-storages` and the INFO log, and the
  `state.json` cooldown-key story (group-name-embedded keys, stale entries harmless) is
  carried through §11.4 correctly.
- **The schema/semantic validation split is right.** `minItems: 1` is the structural floor;
  "≥ 2 after expansion" is enforced where the count is knowable — immediately for
  pure-literal groups (`_check_group_size`), at topology time for pattern groups — with the
  zero-match, same-group double-claim, and cross-group collision cases each tested, and
  `test_pattern_matching_is_fullmatch_not_substring` pinning the `preprod` hazard §11.4
  itself calls out.
- **The `22973b2` test pinning is the correct fix for a real environment dependence**: three
  tests were asserting dispatch outcomes that legitimately differ between the dev venv (no
  solvers → heuristic) and CI/the Debian build (pulp+cbc installed → cbc). Pinning
  `backend: heuristic` in tests *about* the heuristic, while backend dispatch keeps its own
  monkeypatch-based tests, is the honest split; my pulp-installed run (597 passed) confirms
  it end to end.
- **The CI repairs stay inside the project's own policy.** ca-certificates/typeshed/curl+gpg
  are explicit apt additions with root causes documented in the workflow headers (the
  `--no-install-recommends` trap each of them hit); python3-flake8-bugbear's removal is
  verified against Debian and changes nothing CI enforces; the codecov move to
  `codecov-action@v7` with `report_type: test_results` follows the deprecation. None of them
  pip-installs around a missing Debian package. `debian/control` correctly needs no change:
  the range adds no dependency (`re` is stdlib, `requests` is already `Depends`), and mypy is
  not part of the package build, so typeshed is a tests.yml-only concern.
- **The state.py mkstemp refactor removes the ambiguity at its source** (`tmp_path` assigned
  once, a `replaced` flag instead of a mid-`try` `None` reassignment) and — better than the
  fix itself — adds the direct regression test for temp-file cleanup that previously existed
  only by inference from `StateError`.

### 21.7 Assessment

This is the smallest and healthiest range since the implementation was declared finished: one
production bug class found by actually running the tool (and fixed with the plan, not just
the code), five CI repairs that each make the "Debian-packaged toolchain is enough" claim
more literally true, and one clean, well-fenced feature addition that extends configuration
without touching any engine arithmetic. All three findings are at the boundaries the previous
eleven passes consistently found: U-01 is a plan/code text disagreement plus an untested edge
(the T-03/S-08 family), U-02 is documentation prose whose truth ended mid-history (the
R-04/T-04/T-05 family, now with a mechanical-guard recommendation), and U-03 is an
over-promising sentence in an otherwise careful amendment. None touches a safety invariant:
dry-run default, reserve-never-traded, transient invariant, no-auto-delete, and the payback
gate are all untouched by the range and re-verified green by the suite. Fixing U-01 should
come first — the plan/code endpoint disagreement is one sentence, but the error-message and
test gaps are the part an operator would actually hit.

---

## 22. Resolution of twelfth-pass findings (U-01..U-03)

All three findings were real; all three are fixed, not refuted.

| ID | Status | How resolved |
|----|--------|--------------|
| U-01 | Resolved | Plan §11.4 now names `GET /storage` (definitions) as what a pattern is matched against, agreeing with `topology.py` and with the same call literal-id validation already uses. `storage_resources()`'s fetch moved ahead of expansion in `_fetch_cluster_data()` specifically so `_match_pattern_entries()` can check every matched id against it: a pattern-matched storage with a definition but reported active by no node (disabled) is now a `TopologyError` naming the pattern and the storage, raised during expansion rather than surfacing three steps later as `_pick_active_node()`'s generic message. New test `test_pattern_matching_a_disabled_storage_raises_naming_the_pattern` reproduces the exact scenario the review found (a `_cluster_client(..., inactive=...)` storage present in `GET /storage` but absent from the resource inventory) and asserts the message names both the pattern and the storage. A literal reference to the same disabled storage is intentionally left on its existing path (`_pick_active_node`) — its message already names a storage the operator wrote themselves, so there was no opacity to fix there. |
| U-02 | Resolved | All six stale claims fixed in one sweep: `60-topology.md`'s two "not yet written" mentions now name `execute.py`'s `_preflight()` and correct the `reserve.py` paragraph to say `heuristic.py` calls `compute_reserve_status()` directly while `optimize.py`'s MILP path encodes the equivalent bound as a scaled linear constraint instead (it cannot call a Python function from inside a solver's constraint system); `80-gates.md`'s `apply (not yet written)` parenthetical dropped, reworded to contrast `show-load`'s possibly-stale printed line against `plan`/`apply`'s fresh evaluation; `90-heuristic.md`'s "CP-SAT/CBC coefficient scaling ... not yet written" bullet removed outright from "what this pass deliberately does not do" (`optimize.py` implements section 5.5's scaling in full, including the `_assert_nonzero_when_weighted` regression guard the plan's own gamma-trap finding required) and its `explain`/`apply` stubs sentence corrected to `apply` is fully implemented, only `explain` remains a stub; the manual's `last_balance` paragraph rewritten to state that `apply` writes it once a run actually executes a move (`confirm`/`auto`, never `dry-run`), so the first-run behaviour is only the common case before a group's first successful migration. The mechanical-guard idea (a documentation test grepping for stale "not yet written" mentions of modules that now exist) is noted but not built in this pass — a follow-up, not a defect. |
| U-03 | Resolved | The not-`shared` warning is no longer computed inside the literal-only loop: `_expand_group()` now emits it once, after expansion, uniformly over every final member of the group's storages — literal or pattern-matched alike — reading straight from `definitions_by_id`. Plan §11.4 needed no change (it never claimed the asymmetry; the code did), but `60-topology.md`'s asymmetry paragraph was extended to say so explicitly, so a future reader does not have to rediscover it by reading the diff. New test `test_pattern_matching_an_unshared_storage_still_warns` reproduces the review's scenario (a not-`shared` storage matched only by a pattern) and asserts the warning now appears. |

Verification: dev venv `python3 -m pytest` — **588 passed, 24 skipped** (ortools, pulp,
statsmodels absent), **91.65% line coverage**, unchanged from the twelfth pass's own run since
the two new tests exercise lines the existing suite already reached from other angles.
`make check` clean (fmt, lint, typecheck, test, fixtures, docs-check — `IMPLEMENTATION_PLAN.pdf`
rebuilt to 42 pages, internals PDF to 44, manual PDF unchanged at 34 pages, all three stamps
regenerated in the same commit as their Markdown per AGENTS.md §7).

---

## 23. Thirteenth-pass review — `explain`, node-scoped queries, CI solver coverage, plain-language messages

Reviewed commit range `66aacc1..HEAD` (the U-01..U-03 fixes themselves are already recorded in
section 22). Seven commits: `5680d58` (README rewritten as a quickstart, six stale claims fixed
— U-02's sweep), `54ec527` (`explain`, the last unimplemented subcommand, plus
`docs/manual/29-explain.md` and the manpage entry), `a605391` (CI pip-installs `ortools` so
`test_optimize.py`'s CP-SAT cases actually run), `0c4485b` (a dedicated `.venv-typecheck/` for
mypy, and `make venv`/`test`/`cov` stop swallowing a failed solver-extras install), `981adce`
(section 3.4's node-scoping of every PromQL query, auto-derived from `GET /nodes`, with the new
`metrics.extra_selector` override — the second new plan section ever), `84ea838` (`explain`
grows the measured-load section and `-v` provenance), `73fc0aa` (every bare "section N.M"
citation in operator-facing strings replaced with plain language naming the config knob to act
on). Roughly 2,070 inserted lines across 48 files, ~1,000 of them tests.

The range's quality stays high. `explain` is built the right way — it runs the *identical*
`_plan_group()` pipeline (`plan` and `apply` share, so it cannot drift) and adds only rendering:
the pinned block with exact per-disk reasons, §3.6's "cannot fully consolidate" naming with the
blocker per device, the five-term objective breakdown (`ObjectiveBreakdown`'s own stated reason
for existing), pinned-load-as-structural-imbalance warning, show-load's measured-load picture
reused verbatim, and JSON that always carries query provenance. Node scoping is correct where it
is easy to get wrong: the matcher sits *inside* `rate()`'s vector selector before `sum by`
collapses labels; every node name is escaped as a regex literal (an FQDN's `.` otherwise matches
more than the node); the list comes from `GET /nodes` rather than the VM/storage inventories (an
idle node would silently drop out of either); `extra_selector` wins outright; `verify-metrics`
stays deliberately unscoped-and-independent-of-PVE; and the whole thing is threaded as one
resolved `str | None` per run. The plain-language sweep is genuine, not cosmetic — each reworded
message names the config knob to act on, and the manual's worked examples were updated to match
the new strings in the same commit. Both new findings of substance are documentation-accuracy
issues the mechanical cross-reference tests structurally cannot catch, in the same family as
P-01/T-03.

### 23.1 Verification run

- Dev venv `python3 -m pytest`: **649 passed, 1 warning** (a statsmodels `ConvergenceWarning`
  from one Holt-Winters fit test — benign, unasserted test noise), **98.66% line coverage**.
  For the first time in this review's history the dev venv carries all optional backends
  (`ortools` 9.x, `pulp` 3.3.2, `statsmodels` 0.15 — the `0c4485b` solver-extras install), so
  nothing skips and the CP-SAT path is covered locally too.
- System Python (pulp **2.7.0**, the exact Debian trixie/CI version, no ortools): **636 passed,
  13 skipped** — only the cpsat-parametrized cases skip; the CBC and heuristic paths are green
  on the packaged toolchain.
- `tests/fixtures/generate_expected.py --check`: OK. `sha256sum --check` on all three PDF stamps
  (plan, internals, manual): OK. `black --check`, `flake8`, and `mypy` (in its own
  `.venv-typecheck/`, per the new Makefile split): all clean.
- **Node-selector construction verified empirically**:
  `build_node_selector('nodename', ['pve01.example.com', 'pve02.example.com', 'pve02.example.com', 'pve-1'])`
  → `nodename=~"pve-1|pve01\.example\.com|pve02\.example\.com"` (escaped dots, deduplicated,
  sorted); `extra_selector` wins verbatim; both-unset degrades to `None` (no filter).
- **The new `29-explain.md` worked example was re-derived by hand** (the reviewer tradition for
  §14 applies to this one too). With VM 106 added (scsi0 1.0 TiB/ℓ 0.9 pinned on san-a, scsi1
  0.5 TiB/ℓ 0.1 on san-b): Σℓ = 8.40 ✓, u* = 2.80 ✓, L_san-a = 7.40 ✓, L_san-b = 0.80 ✓,
  spread 257.1% → 17.9% ✓, all four Δimbalance values (−4.00, −3.40, −0.80, −0.40) ✓, objective
  terms 0.6 + 1 + 0.225 + 0.5 + 0 = 2.32 ✓ (VM 101's split κ-charged, VM 106's not — consistent
  with the implemented `affinity_counts_pinned_disks` rule), benefit 8.6 × 604800 = 5.20e6 ✓,
  cost 4.72e4 ✓, ratio 110 ✓, all three reserve "requires" lines ✓. **Two "used" figures are
  wrong** — see V-03.
- The `reserve-tradeoff`/`fc-tier1` fixtures are untouched by this range (no solver or objective
  change); `--check` confirms both expected files current.
- CI workflow review: `ortools` is installed *after* `make SYSTEM_TOOLS=1 fmt-check lint
  typecheck` runs, so the stub-parse problem that motivated the mypy venv can never reach the
  typecheck step; the packaged-path story (cbc + heuristic from apt) is unchanged by the pip
  exception (see V-04).

### 23.2 Findings summary

| ID | Severity | Module(s) | Summary |
|----|----------|-----------|---------|
| V-01 | Medium | `docs/manual/10-configuration.md`, `heuristic.py`, plan §5.3 | The `objective.reserve_violation_penalty` entry describes a computation that has never existed anywhere in the code ("the engine computes a provably-dominant P … and uses `max(configured, computed)`, warning when it had to raise it" — no `P_min` exists in `src/`), while denying the key's one live consumer: the heuristic backend's objective — which `explain`'s new `objective:` line prints, and the §14 fixture totals carry — multiplies this key by any remaining (C5) shortfall |
| V-02 | Medium | plan §9.5, `cli.py`, `docs/manual/27-plan.md` | §9.5 specifies the pinned block ("not optional decoration … the only place an operator learns which snapshots to clear", with per-pin action hints) as part of **every mode's** plan output; the implementation prints it in `explain` only, with no action hints ("→ clear snapshots to unblock", "→ waited 0s, re-check next run" exist nowhere), and `27-plan.md` claims "`show-load`/`plan` both show it as `[pinned: …]`" — false for `plan` (neither renderer has any pinned field) |
| V-03 | Low | `docs/manual/29-explain.md` | The new worked example's `used` figures are internally inconsistent with its own disk listings and its own reserve lines: san-a prints `used 4.50 TiB` but its disks sum to 5.50 TiB and its "short by 1.50 TiB" is only correct for 5.50; san-b prints `1.50 TiB` vs a listed 2.00 TiB — both stale by exactly VM 106's disks, the example's own extension |
| V-04 | Low | `.github/workflows/tests.yml`, AGENTS.md §9.3, `.agents/packaging.md` | CI pip-installs `ortools` (`--break-system-packages`) as an exception to §9.3's absolute "CI installs its Python tooling from apt, never from pip" — the reasoning is sound and stated in the workflow's own header comment, but neither AGENTS.md nor `.agents/packaging.md` references it, so the policy documents and the pipeline they govern now disagree on paper |
| V-05 | Info | working tree | `run-with-system-python.sh` sits untracked in the checkout: a complete, SPDX-headed helper (runs the CLI against the system toolchain, no venv — the `SYSTEM_TOOLS=1` story made convenient) referenced nowhere in Makefile, AGENTS.md, `.agents/` or `docs/`; invisible to review, CI and the package alike, it will bitrot silently |

### 23.3 V-01 — the manual describes a penalty computation that has never existed

**Severity:** Medium
**Files:** `docs/manual/10-configuration.md:633-642`, `src/proxmox_storage_drs/heuristic.py:241`,
`IMPLEMENTATION_PLAN.md` §5.3

The manual entry for `objective.reserve_violation_penalty` (untouched since the phase-1/2 docs
commit `f484a6a` — verified with `git log -L`) says:

> A **floor**, not the value actually used, for the single-stage big-M fallback solve path (…):
> the engine computes a provably-dominant `P` from the group's own load and disk sizes at solve
> time and uses `max(configured, computed)`, warning when it had to raise it. The default
> lexicographic two-stage solve (option 1, and the default) needs no penalty at all and is
> unaffected by this key.

Three claims, two of them wrong:

1. **No provably-dominant `P` computation exists anywhere in `src/`** — `grep` for `P_min`/
   `p_min`/`computed_p`/`dominant` returns nothing. The M-06 resolution added the requirement
   to the *plan* (§5.3: "the model uses `P = max(configured, P_min)` and logs a warning … and
   repeat them in `pve-storage-drs explain`"), but the code that would compute it was never
   written: `91-optimize.md` documents that the MILP is lexicographic-only by design, and the
   heuristic multiplies the *configured* value straight into its objective
   (`reserve_penalty_term = objective.reserve_violation_penalty * reserve_shortfall_tib`).
   The §5.3 requirement to repeat the numbers in `explain` is therefore dormant — no big-M
   path exists to raise `P` — but the manual describes the dormant machinery as the key's
   *actual behaviour*.
2. **"Unaffected by this key" is false in a fully reachable configuration.** The heuristic
   backend (`solver.backend: heuristic`, or `auto` with neither solver installed — exactly the
   packaged-without-Recommends install the autopkgtest tests) uses this key directly: it scores
   every candidate assignment with the `P × shortfall` term, so whenever a group's (C5)
   violation is physically unresolvable, the configured value influences which assignment the
   descent settles on and what the objective totals report. The §14 fixture's own expected
   files carry `big_m_p` for exactly this arithmetic. And as of this range, `explain`'s new
   `objective:` line prints the term — an operator can now *see* the key doing something the
   manual says nothing in the default path does.

This is the P-01/P-02/S-08/T-03 family a fifth time over, and it survived U-02's stale-claim
sweep because that sweep grepped for "not yet written"/"remain stubs" phrasing, not for
confident descriptions of never-implemented computations.

**Recommendation:** rewrite the entry to describe what the key actually does today: it is the
reserve-violation weight in the heuristic backend's objective (and the `reserve` term
`explain` prints and the §14 fixture totals carry), it exists so the heuristic's candidate
comparisons stay commensurable with the big-M objective the plan describes, the MILP backends
are lexicographic and never consult it, and the §5.3 `max(configured, P_min)` floor applies to
the unimplemented single-stage alternative only. Either that, or implement the floor where the
heuristic consults the key — but a documentation fix is the honest minimum, and per AGENTS.md
§7.6 the plan's §5.3 sentence should gain the same "as built" annotation §10.1 got for T-03.

### 23.4 V-02 — §9.5's pinned block: specified for every mode, implemented for `explain` only

**Severity:** Medium
**Files:** `IMPLEMENTATION_PLAN.md` §9.5 (lines 1549-1557, unchanged since the original spec),
`src/proxmox_storage_drs/cli.py` (`_render_group_plan_human`/`_render_group_plan_json`),
`docs/manual/27-plan.md:169-170`

§9.5's output example — explicitly "Every mode emits the same machine-readable plan (JSON) plus
a human summary" — ends with the pinned block and its closing paragraph: "The pinned block is
not optional decoration — it is the 'complain' half of the skip-and-complain policy of §3.7,
and it is the only place an operator learns which snapshots to clear." The spec's block carries
per-pin action hints ("`→ clear snapshots to unblock`", "`→ waited 0s, re-check next run`") and
the pinned-load/best-achievable-spread line.

The implementation: `plan` and `apply` print none of it — neither human nor JSON renderers have
a single pinned field (verified by inspection of both). `explain`, as of this range, prints the
block (exact reasons, sizes, loads, ℓ/z), the "cannot fully consolidate" naming, and the
pinned-load line — good, and clearly the right home for the narration. But (a) the per-pin
action hints exist nowhere in any command's output, including `explain`; (b) the plan's §9.5
example still shows the block as part of the plan output with no "as built" annotation, eleven
passes after `plan` first shipped without it; and (c) `27-plan.md` asserts "`show-load`/`plan`
both show it as `[pinned: cooldown: ...]`" — true for `show-load`'s per-disk lines and
`explain`, flatly false for `plan`.

An operator following the manual's own reading would run `plan`, see three moves and no pins,
and never learn the fourth VM is pinned by snapshots — the exact §3.7 complaint obligation,
deferred to a command the manual's plan page never points them at for it.

**Recommendation:** the cheapest coherent resolution is documentation, not code: add the "as
built" note to §9.5 (the pinned block, fragmentation naming and pinned-load line live in
`explain` — and inline per-disk pins in `show-load`; `plan`/`apply` deliberately print only
what they will act on), fix the `27-plan.md` sentence to name `show-load`/`explain`, and have
`27-plan.md`'s "What `plan` does not yet do" list say plainly that pins are not shown here.
The per-pin action hints are worth restoring inside `explain`'s pinned block — they are one
format string each, and §9.5's own justification for the block is teaching the operator *what
to do* about each pin, not merely that it exists.

### 23.5 V-03 — two stale "used" figures in the new `explain` example

**Severity:** Low
**Files:** `docs/manual/29-explain.md:34,39`

Hand re-derivation (23.1) found every computed number in the new worked example correct except
the two per-storage `used` figures, both stale by exactly the added VM 106's disks — the
example was extended from `plan`'s §14-based one by adding VM 106 without updating the used
totals:

- san-a lists 101:scsi0 (2.00) + 101:scsi1 (1.00) + 102:scsi0 (1.50) + 106:scsi0 (1.00) =
  **5.50 TiB**, prints `used 4.50 TiB` — and its own `⚠ reserve short by 1.50 TiB` line is
  only correct for 5.50 (5.5 + 4.0 required − 8.0 capacity = 1.5; with 4.5 it would be 0.5),
  so the example contradicts *itself* one line apart;
- san-b lists 0.50 + 1.00 + 0.50 = **2.00 TiB**, prints `used 1.50 TiB` (reserve OK either
  way, so only the listing-vs-total inconsistency shows).

Everything else — loads, spreads, all four Δimbalance values, the objective's five terms,
benefit/cost/ratio, all three "requires" lines — verifies to the digit. This is the first
worked example in the manual set that no fixture or test asserts against, which is how a
stale number survived a range that otherwise updated its examples meticulously (the
plain-language commit updated gate-reason strings in three manual pages in lockstep).

**Recommendation:** fix the two values (5.50, 2.00). Worth considering alongside: the §14
tradition in this project is that worked examples are *executable* — a test that builds this
exact group (the §14 fixture plus VM 106) and asserts the rendered `explain` output's numbers
would have caught both figures and keeps the page honest the way the fixture tests keep §14
honest.

### 23.6 V-04 — the CI pip exception is documented everywhere except the policy documents

**Severity:** Low
**Files:** `.github/workflows/tests.yml` (header + `Install ortools` step), `AGENTS.md` §9.3,
`.agents/packaging.md`

AGENTS.md §9.3 states an absolute rule: "CI installs its Python tooling **from apt, never from
pip**. A CI that pip-installed its way around a missing Debian package would hide the day
§9.1 stopped being true." As of `a605391`, `tests.yml` runs
`pip install --break-system-packages 'ortools>=9.8'` — with a workflow-header comment that
argues the exception properly (ortools has no Debian package at all; it is optional at runtime;
the packaged path is unchanged; installation is ordered after typecheck so the numpy-stubs
problem cannot reach mypy). The argument is sound. The problem is only *where* it lives: a
reader of AGENTS.md §9.3 or `.agents/packaging.md` (whose ortools row still says only "pip-only
bonus", with no mention of CI) has no pointer to it, and by the documents' own absolutist
wording the pipeline is in violation. Policy documents that silently contradict the pipeline
they govern train readers to ignore both.

**Recommendation:** one sentence in `.agents/packaging.md`'s ortools discussion (and/or a
parenthetical in AGENTS.md §9.3) naming the exception, its reason, and pointing at the workflow
header — the same treatment the Salsa `--enable-network` fallback gets ("a deliberate,
reviewable edit — never a default").

### 23.7 V-05 — an untracked helper script (Info)

`run-with-system-python.sh` sits untracked in the checkout: ~35 lines, SPDX-headed, runs the
CLI straight out of the tree against the system python and its Debian-packaged modules — a
convenience wrapper for exactly the `SYSTEM_TOOLS=1`/CI toolchain story, with an accurate
header comment (including that `solver.backend: auto` degrades to CBC there, by design).
Referenced nowhere: not the Makefile, not AGENTS.md, not `.agents/`, not the docs. Untracked
means it is invisible to this review's usual checks, to CI, and to anyone cloning the repo —
it will bitrot silently the next time the CLI's invocation changes. Either commit it (it is a
legitimate developer convenience and would want a `.agents/packaging.md` mention) or delete
it; the only state that is wrong is the current one.

### 23.8 What this pass confirms

- **`explain` reuses rather than reimplements.** The gate/solve/schedule/payback pipeline is
  the same `_plan_group()` `plan` and `apply` call (so its numbers are byte-identical by
  construction, not by discipline); the measured-load section is `show-load`'s own renderer;
  the objective terms are the breakdown class's own five fields; `_fragmented_vms()` uses the
  *final* assignment (the R-02 lesson applied unprompted), counts a VM as blocked only when a
  pin is what keeps it spread, and works even for a `NO ACTION` group with no plan at all.
  The JSON always carries query provenance (no verbosity notion to guess about), the human
  `-v` line is documented as the one deliberate global-option exception, and the status
  table's `explain` row plus the manpage entry match the implementation.
- **Node scoping is the right shape end to end.** One resolved selector per run; `GET /nodes`
  (not the VM/storage inventories, whose idle-node blind spot the `node_names()` docstring
  names); regex-literal escaping (empirically verified); `extra_selector` verbatim override
  with its own schema/manual/example-config documentation; `verify-metrics` deliberately
  unscoped with the reasoning written down in `30-metrics.md`; the plan gained the §3.4 note
  and the `GET /nodes` read-path row in the same commit; and every load path (decision
  statistic, coverage, and the saturation guard's per-disk series) threads the same selector
  so no query family can drift unscoped.
- **The plain-language sweep is complete and consistent.** Grep finds no remaining bare
  "(section N.M)" in any user-facing string (the two matches left are docstrings, where the
  citation scheme belongs); the reworded messages name actionable config keys
  (`saturation_load`, the time-window/deadline knobs); and the manual's three worked examples
  that quote gate/output strings were updated in the same commit — the discipline V-03's two
  stale numbers fell just outside of.
- **The mypy-venv split solves a real problem without weakening anything.** The
  numpy-stubs-vs-`python_version=3.11` parse failure is verified and documented in three
  places (Makefile comment, pyproject comment, `91-optimize.md`); `SYSTEM_TOOLS=1` still runs
  system mypy; and the loud-not-swallowed solver-extras install means a broken `ortools`
  install now prints an explicit warning about exactly which test cases will be skipped
  instead of silently degrading — which is also why this pass could report 649/649 with zero
  skips for the first time.
- **T-01..T-07 and U-01..U-03 stay fixed.** The re-plan membership predicate, per-attempt
  cooldown recording (`state_box` threading visible in `_run_auto_group`'s new signature),
  the upper-quantile "as built" annotations (retained verbatim through this range's manual
  edits), the saturation-claim rewordings, `raw_spread()` as the benefit input, the unified
  migration-cap counter, and the §11.4 pattern validation are all still in place and green.

### 23.9 Assessment

This range closes the tool's last functional gap (`explain` was the final stub), hardens its
data path against a real multi-cluster-Prometheus failure mode, and gets its CI to exercise
the CP-SAT path it ships as `solver.backend: auto`'s first choice — all without touching the
solver, the safety machinery, or a single fixture number, and with the plan amended in the
same commits for both new behaviours. The five findings are all documentation-accuracy or
working-tree hygiene: none changes behaviour, and the two Mediums (V-01, V-02) are precisely
the residue the mechanical cross-reference tests cannot catch — confident prose describing
machinery that was never built (V-01), and a spec's output contract that drifted from every
renderer eleven passes ago without an annotation (V-02). Both are fixable with an afternoon of
writing; V-03 is two digits. After those, the documentation set would finally meet the
standard the code has held since the tenth pass.

---

## 24. Resolution of thirteenth-pass findings (V-01..V-05)

All five findings were real; all five are fixed, not refuted.

| ID | Status | How resolved |
|----|--------|--------------|
| V-01 | Resolved | `IMPLEMENTATION_PLAN.md` §5.3 gained an "As built" note (matching T-03's own, §10.1) stating plainly that option 2's `P_min`/`max(configured, P_min)` machinery was never implemented, that both MILP backends never consult `objective.reserve_violation_penalty` at all (option 1 only), and that the heuristic backend is the key's one live consumer, using it exactly as configured. `docs/manual/10-configuration.md`'s entry for the key was rewritten to describe that heuristic-objective behaviour as the primary fact, with the MILP lexicographic solve and the unimplemented option 2 floor named as the reason the key does *not* apply there. |
| V-02 | Resolved | `IMPLEMENTATION_PLAN.md` §9.5 gained an "As built" note: the pinned block, fragmentation naming and pinned-load line live in `explain` (with `show-load` also naming individual pins inline), not in `plan`/`apply`. `docs/manual/27-plan.md`'s false "`show-load`/`plan` both show it" sentence now names `show-load`/`explain`, and a new bullet in "What `plan` does not yet do" states outright that no pinned block exists there. The per-pin action hints the spec's own example shows (`→ clear snapshots to unblock`, etc.) were restored where the review recommended — inside `explain`'s pinned block, via a new `_pin_action_hint()` (human report's `→ <hint>` suffix and JSON's `pinned_disks[].action_hint`, `null` for a standing policy exclusion, same as the spec's own "excluded by tag" pin carrying none). New test `test_pin_action_hint_names_something_to_do_only_when_there_is_something` plus updated assertions in the existing pinned-block/JSON tests. |
| V-03 | Resolved | `docs/manual/29-explain.md`'s worked example's two stale `used` figures fixed to match their own disk listings: san-a 4.50→5.50 TiB (now consistent with its own "short by 1.50 TiB" line), san-b 1.50→2.00 TiB. |
| V-04 | Resolved | AGENTS.md §9.3 and `.agents/packaging.md` (the `ortools` row and a new paragraph) now name the CI pip exception explicitly — what it installs, why, and that it is the one place the "apt, never pip" rule has a reviewed exception — pointing at `tests.yml`'s own header comment for the full reasoning, so the policy documents and the pipeline agree on paper. |
| V-05 | Resolved | `run-with-system-python.sh` committed (it is a legitimate, accurate developer convenience, not dead weight) and referenced from `Makefile` (a comment next to `SYSTEM_TOOLS=1`) and `.agents/packaging.md` (both the CI section and the `ortools`-adjacent `SYSTEM_TOOLS` mention), so it is no longer invisible to review, CI, or a future reader. |

Verification: dev venv `python3 -m pytest` — **650 passed, 1 warning** (the same benign
`ConvergenceWarning` V-05's predecessor pass noted), **98.67% line coverage** (one line up from
the thirteenth pass's 98.66%: the new `_pin_action_hint()` branch). `make check` clean (fmt,
lint, typecheck, test, fixtures, docs-check — `IMPLEMENTATION_PLAN.pdf` rebuilt to 42 pages,
internals PDF to 46, manual PDF to 37, all three stamps regenerated in the same commit as their
Markdown per AGENTS.md §7).

---

## 25. Fourteenth-pass review — 0.1.0, CBC as a hard `Depends`, three live-cluster size fixes, and cluster-name query scoping

Reviewed commit range `fd5180e..HEAD` (the V-01..V-05 fixes themselves are already recorded in
section 24). Eight non-merge commits: `4f1172a` (the 0.1.0 `debian/changelog` entry, with
`pyproject.toml`/`__init__.py` bumped to match), `64f4022` (the entry's distribution set to
`trixie` rather than `UNRELEASED`), `b4447ca` (`coinor-cbc` and `python3-pulp` moved from
`Recommends` to `Depends` in `debian/control`, with the plan, both relevant manual pages,
`.agents/packaging.md`, the `import-all` autopkgtest comment and the changelog bullet all updated
together — plus a genuine factual correction: the old claim that Debian's `python3-pulp` itself
merely `Recommends` `coinor-cbc` was wrong), `59cda4c` (fix a real `KeyError('size')` crash when a
content-listing entry matches a VM disk's volid but carries no `size` key — the same latent
unguarded `item["size"]` fixed in `_build_storages()`'s foreign-volume sum too), `f2ddeeb` (a new
middle tier: a `size`-less content item's `approximate-size` beats the VM config's own `size=`),
`f25a201` (query a managed disk's content listing from *its own VM's node*, because PVE 9.2's
qcow2-on-shared-LVM volumes report their exact `size` only from the node with the LV active),
`a189a6f` (§3.4 grows a second auto-derived scoping tier — the live cluster's own name, from a new
`PveClient.cluster_name()` (`GET /cluster/status`) — plus a `verify-metrics` discovery scan that
reports every cluster-label value seen across the metrics, so an operator on a shared Prometheus
finds out what to configure), and `3b5f031` (operator-directed: `metrics.labels.cluster` defaults
to `"cluster"` rather than `null`, making cluster-name scoping the default tier for
`plan`/`show-load`/`apply`/`explain`). Roughly 1,150 net inserted lines across 34 files (≈1,350
across the individual commits before `3b5f031`'s rewording overwrote `a189a6f`'s), about 460 of
them tests.

The range's quality stays high. All three code fixes are driven by incidents on a live cluster,
each lands with regression tests that would have reproduced the original failure, and each updates
the plan and `docs/internals/60-topology.md` in the same commit — including an unusually honest
correction of the *previous* commit's own wrong guess (f2ddeeb attributed `approximate-size` to a
dir/NFS storage; f25a201 replaced that with the operator's actual mechanism and said so). The
node-pair pre-pass in f25a201 is engineered the right way: deduplicated as a set (bounded by
distinct nodes, not VMs), fetched concurrently under the same `read_workers` pattern as the per-VM
phase, deterministically ordered (sorted pairs, `Executor.map`'s order-preserving results, and the
join still single-threaded in `cluster-resources` order, so warning order is run-stable), with
`_disk_specs_from_config()` factored out so the pre-pass and the join can never parse one VM's
disks two different ways, and the active-pick listing reused rather than re-fetched wherever it
already covers the pair. The packaging move is coherent end to end, states its one real trade —
the autopkgtest can no longer prove heuristic-only operation at install time — honestly in three
places, and its factual correction about `python3-pulp` checks out (verified below). The scoping
work is built with the same discipline — one resolved selector per run threaded everywhere, a
tier precedence that is unit-tested tier by tier including the opt-out and the
caller-passes-a-name-while-config-opted-out corner, call-skipping proven by tests whose fakes
*raise* if a skipped API call is made, string-literal escaping in the new selector builder, and
seven documents (plus the schema, the example config and both PDFs) rewritten across the two
commits — but its second half flips a default, and that flip is where this pass's one Medium
finding lives (W-06): the silence and the runtime symptoms calibrated for the old opt-in design
were kept when the default changed. Otherwise, every finding this pass is documentation residue of
the exact family the last three passes kept finding: the operator-facing or summary layers (the
status page, the warnings paragraph, the changelog, one internals header, two worked examples)
lagging behaviour changes that the plan and internals otherwise tracked.

### 25.1 Verification run

- Dev venv `python3 -m pytest`: **674 passed, 1 warning** (the same benign statsmodels
  `ConvergenceWarning` noted since the eleventh pass), **98.65% line coverage**. `make check`
  clean: fmt-check, flake8, mypy (in its own `.venv-typecheck/`), test-with-coverage, the fixture
  `--check`, and docs-check over all three PDF stamps plus the manpage.
- System Python (pulp **2.7.0**, the exact Debian trixie/CI version, no `ortools`): **661 passed,
  13 skipped** — only the cpsat-parametrized cases skip; the CBC and heuristic paths stay green on
  the packaged toolchain, as they have since the S-01 fix.
- **The new warning strings were exercised directly** (fake-client fixture, both tiers): a
  size-less item with `approximate-size` warns `201:scsi0: 'san-a:vm-201-disk-0' has no exact
  size= in 'san-a''s content listing; using its approximate-size instead`; one with neither warns
  `... has no size= or approximate-size in ... using the VM config's own size= instead, which can
  be stale if the volume was resized outside Proxmox`. Sizes resolve to 9 GiB and 4 GiB
  respectively — the tiers work as the commit messages claim.
- **The scoping flip's failure mode was traced end to end by code reading, not assumed**: with the
  default `metrics.labels.cluster: "cluster"` and a Prometheus whose series carry no such label,
  every load query embeds `cluster="<name>"` and returns zero series; `compute_group_load()`
  then rejects every disk (`sample coverage 0% is below window.min_coverage`), substitutes 0.0 /
  last-known, and the gate's verdict is `gates.py`'s "group is idle: no measured I/O to balance" —
  a working, busy Prometheus presented as an idle one, with nothing naming the selector as the
  cause. `verify-metrics` in the same state is **fully green**: it resolves its selector with
  `resolve_node_selector(metrics, None)` (no node list, no cluster name), so tiers 2 and 3 never
  apply to its own queries by design, and the discovery scan reports nothing (no series carries
  the label) — the absence of a finding is the only trace. See W-06.
- **External fact checks** (the Appendix B tradition), all against primary sources:
  - `packages.debian.org/trixie/python3-pulp` (2.7.0+dfsg-4): **depends** on `coinor-cbc` —
    `b4447ca`'s correction of the long-standing "Debian splits cbc into a mere Recommends" claim
    is accurate. It also retroactively explains why S-01's crash was never observed on a real
    Debian install: only a non-Debian `pip install pulp` can produce importable-pulp-without-cbc
    there, which is exactly the residual case the `PulpSolverError` catch now names.
  - pve-storage.git commit `7ce747e3a365` ("api/cli: list content: declare size optional and add
    approximate-size", Fiona Ebner, 2026-05-18): "For inactive qcow2 volumes on LVM, currently no
    size information is returned, because that would require activating each LV to scan the
    qcow2 header. For a shared LVM, an LV might already be active on another node, so it cannot be
    activated." — upstream independently confirms the operator's mechanism account that f25a201
    built its fix on, essentially verbatim.
  - pve-storage.git commit `025067598cc3` ("api: content: note typical upper-bound semantics for
    approximate-size", Thomas Lamprecht): "The LVM plugin sets it to the LV allocation size
    (qcow2 fully-allocated), which is an upper bound on the qcow2 virtual size", with the API
    schema reading "Present instead of 'size' ... Will typically be an upper bound on the actual
    size, but the exact semantics depend on the storage plugin." Two consequences verify the
    implementation's choices: `size` and `approximate-size` are mutually exclusive upstream, which
    the code's `if "size" in ... elif "approximate-size" in ...` tiering mirrors; and for its one
    current producer the approximate figure is an *upper bound on the virtual size*, so the new
    tier errs in the conservative direction for this project's thick-provisioning reserve model —
    a property neither the plan nor `60-topology.md` states but that makes the tier strictly safer
    than this review would otherwise have to question.
  - pve-manager.git `PVE/API2/Cluster.pm`, `get_status` (the `GET /cluster/status` handler):
    `permissions => { check => ['perm', '/', ['Sys.Audit']] }` — the new privilege requirement
    `cluster_name()`'s docstring and the manual state is accurate, and it is indeed the one call
    in this project that needs it.
- V-01..V-05 all still in place (spot-checked: the rewritten `reserve_violation_penalty` entry,
  `_pin_action_hint()` in both renderers, `29-explain.md`'s corrected 5.50/2.00 figures, AGENTS.md
  §9.3's named CI pip exception, and the now-tracked `run-with-system-python.sh` referenced from
  both the Makefile and `.agents/packaging.md`).
- Version hygiene: 0.1.0 agrees across `debian/changelog`, `pyproject.toml` and `__init__.py`
  (`test_version.py`), and `debian-package.yml`'s `dpkg-parsechangelog` check enforces the first
  against the second.

### 25.2 Findings summary

| ID | Severity | Module(s) | Summary |
|----|----------|-----------|---------|
| W-01 | Low | `docs/manual/30-safety-and-status.md` | The Optional-dependencies paragraph still says the tool executes "`dry-run`/`confirm`; `auto` not yet" — stale since phase 8 landed, contradicted by the same page's own `apply` status row above, by the manpage, the README and the changelog, and left standing by `b4447ca`, which rewrote the very sentence it sits in |
| W-02 | Low | `debian/changelog` | The 0.1.0 entry's per-phase bullets mislabel `explain` as "phase 8" (that phase is `auto` mode + time windows) and `state.py` as "phase 7" (that phase is `execute.py`), while the actual phase-8 and phase-9 work appears nowhere — under an opening bullet claiming "all nine IMPLEMENTATION_PLAN.md phases are now built"; and none of the range's own post-cut features (the size tiers, the VM-own-node fetch, the cluster-scoping tier and its default) has a bullet either |
| W-03 | Low | `docs/internals/60-topology.md`, `topology.py` | The step-list header still says "in five stages" over the six-item list `f25a201` created (it inserted step 5 and renumbered without touching the header), and three references to `_collect_vm_disks` — the header, the lock section, and `_ClusterData`'s docstring, whose "one argument bundle rather than seven" is now eight parameters — name a function renamed away in the P-02 split |
| W-04 | Low | `docs/manual/25-show-load-and-verify-storages.md` | The Warnings-block paragraph documents one size warning and interprets it as the absent-volume/dangling-reference case with `qm unlink` advice; this range adds two new warnings to that same block (plus the foreign-volume undercount warning) that it does not mention, and for the sizeless-item variant its interpretation actively misdirects — the volume is right there in the listing |
| W-05 | Info | plan §3.5, `docs/internals/60-topology.md` | The VM-own-node fix multiplies content-listing calls from one per managed storage to one per distinct (node, storage) pair hosting a managed disk — worst case nodes × storages full listings per run, deduplicated and `read_workers`-bounded but quantified nowhere; §3.5's own "expected call count" formula (`3 + 2·|VMs| + 2·|storages|`, unchanged since the F-fix era) is now stale three ways: no `/nodes`, no `/cluster/status`, no per-node content listings |
| W-06 | Medium | `metrics.py`, `cli.py`, `gates.py` | `metrics.labels.cluster`'s new default makes `cluster="<name>"` the scoping of every load query — which matches *zero series* on a Prometheus that carries no such label (the vanilla metric-server shape: §3.1/§3.2's own tag inventory has none), and the tool then degrades silently: every disk flagged "sample coverage 0%", every gate verdict "group is idle", `verify-metrics` fully green (it never applies tiers 2/3 to its own queries, and the discovery scan's silence was calibrated for the old opt-in default). The one clue — the absent discovery line — is documented, but nothing warns, at verification time or run time |
| W-07 | Low | `loadmodel.py`, `metrics.py`, `docs/manual/25-*.md` | The runtime half of W-06: a resolved non-`None` selector matching zero series is presented as "group is idle: no measured I/O to balance" plus per-disk coverage-0 flags — misattributing a scoping mismatch to the data; the manual's own advice for that presentation ("check `verify-metrics` first") dead-ends because verify-metrics is green |
| W-08 | Low | `pve.py`, `cli.py`, `docs/manual/00-installation.md` | `GET /cluster/status` (`Sys.Audit` at `/`, verified against pve-manager) is now called on every `plan`/`show-load`/`apply`/`explain` run by default, so a credential provisioned per the pre-`3b5f031` manual fails the *whole* run — including read-only `show-load` — with a `PveApiError`, rather than degrading to the equally-safe node-list tier (403 → `cluster_name()` unavailable → tier 3) with a warning |
| W-09 | Low | `config/drs.example.yaml`, `docs/manual/29-explain.md` | Two siblings of the documents `3b5f031` did rewrite: the example config's `extra_selector` comment still describes node-list scoping as "every query ... automatically" (now the fallback tier) with `cluster="mycluster"` as its override example — literally the new default — and `explain`'s worked example still prints its query-provenance line as the node alternation, the opt-out configuration's output |

### 25.3 W-01 — "`auto` not yet" on the page the README calls authoritative

**Severity:** Low
**Files:** `docs/manual/30-safety-and-status.md:62-63`; touched (the sentence rewritten) by
`b4447ca`

The Optional-dependencies section opens: "`pve-storage-drs` runs, plans and executes
(`dry-run`/`confirm`; `auto` not yet) with only `requests`, `ruamel.yaml` and `jsonschema`
installed." The parenthetical has been false since phase 8 landed (eleventh-pass range): `apply`
is implemented for all three `execution.mode` values, and *this same page's own* `apply` row says
so at length — time windows, the migration cap, the re-plan loop, concurrent execution and all.
The manpage (`--mode dry-run|confirm|auto`), the README ("Every command, including `apply`'s
unattended `auto` mode ... is implemented") and the 0.1.0 changelog agree. `b4447ca` rewrote the
sentence containing the parenthetical ("Three dependencies" → "Two dependencies") and kept it.

Two things make this more than a typo: the README explicitly delegates authority to this page
("`docs/manual/30-safety-and-status.md` is the authoritative, per-command status table — trust
that over any impression given elsewhere"), and the page's own framing is that being honest about
what is built "matters more than a document that reads as finished". A reader who trusts it will
simply not use `auto` mode — conservative, but still wrong, and it is the sixth finding in the
P-01/T-03/V-01 line of self-contradicting documentation. It survived the U-02 and T-05
stale-claim sweeps because it matches neither their "not yet written" nor their
"not implemented anywhere" phrasings.

**Recommendation:** delete the parenthetical (the sentence's actual subject — minimal-dependency
operation — does not need an execution-mode caveat), or rewrite it to "... executes in every
`execution.mode` ...". Worth doing in the same sweep as W-04, and worth adding "`auto` not yet"
to whatever pattern the next stale-claim grep uses.

### 25.4 W-02 — the 0.1.0 changelog mislabels two phases and omits two

**Severity:** Low
**Files:** `debian/changelog:3-25`

The entry's opening bullet claims "all nine IMPLEMENTATION_PLAN.md phases are now built", but the
per-phase bullets that follow name the wrong work for two phases and never mention two more:
"explain (phase 8)" — the plan's phase 8 is "`auto` mode + time windows", and `explain` belongs
to no phase (it is §9.5's narration command); "state.py (phase 7, section 11.2)" — the plan's
phase 7 is `execute.py`, which the entry never names at all; and neither the real phase-8 work
(auto mode, time windows, the migration cap, the re-plan loop) nor phase-9's (the seasonal-naive
backtest gate, which pass eleven reviewed landing) appears anywhere in the entry. `debian/changelog`
is a shipped, write-once artefact once uploaded, and this range is the one that declared the
version final for trixie — and then kept landing features after the cut with no bullet at all:
none of the range's own user-visible work (the `approximate-size` tier, the VM-own-node size
fetch, the cluster-scoping tier and its default) is recorded in the 0.1.0 entry either, even
though it is still unreleased and therefore still appendable.

**Recommendation:** fix the two labels and add the two missing items while the entry is still
unreleased — the project's own stated convention (never rewrite a past entry's own text, per
`4f1172a`) protects 0.0.1's honest "not yet buildable" from 0.0.1's own time, not a present-tense
error in a brand-new entry.

### 25.5 W-03 — "in five stages" over a six-item list, and a dead function name

**Severity:** Low
**Files:** `docs/internals/60-topology.md:27-29,81`; `src/proxmox_storage_drs/topology.py:436-439`

`f25a201` inserted a new step 5 into `60-topology.md`'s numbered fetch-stage list and renumbered
the old step 5 to 6 — but not the sentence directly above the list: "`build_topology()` fetches
everything it needs exactly once, in five stages (`_fetch_cluster_data`, then a loop over
`client.vm_resources()` calling `_collect_vm_disks` per VM, then `_build_storages`)". Three
things in that one sentence are now wrong: the count (six items), the shape it sketches (there
are now two concurrent fetch phases plus a single-threaded join, not fetch-loop-build), and the
function name — `_collect_vm_disks` has not existed since the P-02 concurrency split renamed it
`_fetch_vm()`/`_join_vm_disks()` (the rename is even explained six lines below, at step 4, which
makes the header's use of the old name a genuine trip-up rather than a harmless anachronism).
The same dead name survives in the page's lock section (line 81) and in `_ClusterData`'s own
docstring (`topology.py:438`), whose "takes one argument bundle rather than seven" claim
f25a201 also aged: `_join_vm_disks()` takes eight parameters now that `content_by_node` threads
through it.

**Recommendation:** rewrite the header sentence to match the list it introduces (six stages,
`_fetch_cluster_data` → per-VM concurrent fetch → per-pair content fetch → join →
`_build_storages`), fix the two remaining `_collect_vm_disks` references, and re-count the
`_ClusterData` docstring's parameters.

### 25.6 W-04 — the operator manual's warnings paragraph predates three new warnings

**Severity:** Low
**Files:** `docs/manual/25-show-load-and-verify-storages.md:92-103`; warnings added by
`59cda4c`/`f2ddeeb`

The manual's Warnings-block paragraph documents exactly one size-resolution warning — "a disk
whose size came from its own config rather than the storage's authoritative content listing" —
and interprets it: the volume usually no longer exists, most often removed behind Proxmox's back,
so check and `qm unlink` the dangling reference. This range added three new operator-visible
warnings to that same block without extending the paragraph:

- *"has no size= or approximate-size in ... using the VM config's own size= instead"* — the
  volume **is** in the listing (this is the KeyError case, fixed); the plugin just could not
  report a size cheaply. The manual's absent-volume interpretation and `qm unlink` advice are the
  wrong first move here: the right one is to note the fallback happened and, if the figure
  matters, ask why the plugin could not size it.
- *"has no exact size= ... using its approximate-size instead"* — benign by construction (PVE
  answered approximately; upstream documents the figure as typically an upper bound), needs no
  action, and is exactly what a stopped VM's disks on qcow2-on-shared-LVM will produce.
- *"foreign volume ... has no size= or approximate-size ... not counted toward the snapshot
  reserve, which may therefore be an undercount"* — the one warning of the three that deserves
  operator attention, and the only one the manual's paragraph cannot even gesture at.

The plan (§3.5) and `60-topology.md` were updated in the same commits; the operator manual — the
layer these warnings are actually addressed to — was not. This is the P-01/T-03/V-01 family a
seventh time (W-01 above being the sixth), with the twist that the strings were *new* rather than
reworded, so nothing forced a manual touch the way the plain-language sweep did.

**Recommendation:** extend the paragraph to enumerate the now-four size warnings with one
interpretation each (gone-vs-could-not-size-vs-approximate-vs-undercount), in the same style as
the existing dangling-reference guidance. A structural fix is also available and cheap: the
cross-reference tests already assert that CLI options appear in the manual; asserting that every
warning string `topology.py` emits appears somewhere in `docs/manual/` would have caught W-04 (if
not W-01) mechanically.

### 25.7 W-05 — the content-listing read-path amplification is quantified nowhere (Info)

`f25a201` turns `GET /nodes/{node}/storage/{storage}/content` from one call per managed storage
into one additional call per *distinct (node, storage) pair* beyond the active pick that hosts a
managed disk — worst case (VMs spread over every node, disks on every storage) nodes × storages
full volume listings per run, every run, each potentially large on a many-thousand-volume
storage. The design mitigations are right (set-deduplication bounds it by distinct nodes rather
than VMs; the fetches share the per-VM phase's `read_workers` pool; pairs already covered by the
active pick are not re-fetched), but neither plan §3.5's read-path table and its new mechanism
paragraph nor `60-topology.md`'s step 5 states the bound or the growth at all. F-11 made
read-path cost a Medium finding when the per-VM O(VMs) cost was unspecified; this is the same
question one layer down, now with a concrete multiplier. Recorded as Info because the fix's
correctness does not depend on it, the dogfooding cluster is small, and `read_workers` remains
the documented lever — but the next reader of §3.5 should not have to re-derive the worst case
from the code.

While re-reading §3.5's cost text, its "Expected call count per run: `3 + 2·|VMs considered| +
2·|storages|` — three cluster-wide calls" formula turns out to have gone stale *three* times
without an edit (`git log -L` confirms it is unchanged since the F-fix era): the thirteenth
pass's `GET /nodes` added a fourth cluster-wide call whenever tier 3 is used, `a189a6f`'s
`GET /cluster/status` adds another by default (§3.5's own new read-path row documents the call
but not the formula), and `f25a201` multiplied the per-storage `content` term. The formula is
exactly the kind of sentence F-11's resolution added so the next reader would not have to
re-derive costs — it should be recomputed (or replaced by a per-tier statement) in whichever
commit addresses the amplification above.

### 25.8 W-06 — the cluster-scoping default silently disables the tool on a label-less Prometheus

**Severity:** Medium
**Files:** `src/proxmox_storage_drs/metrics.py:403-462` (`_check_sample_series`),
`src/proxmox_storage_drs/cli.py` (`_resolve_node_selector_for_run`), `gates.py:131-138`,
`IMPLEMENTATION_PLAN.md` §3.4, `docs/manual/10-configuration.md` (`metrics.labels.cluster`)

`3b5f031`'s default flip is operator-directed and documented as such, and the operator's estate
carries a cluster-naming tag — but the flip changes what *every* deployment gets out of the box,
and the vanilla shape is the broken one. PVE's own metric-server path (§3.1/§3.2, the plan's own
tag inventory: `vmid`, `instance`, `nodename`, ...) emits **no** `cluster` label; the tag exists
on this operator's Prometheus because their own tagging adds it. On a deployment without it, the
default resolves every load query's selector to `cluster="<live name>"`, which matches zero
series. The consequences were traced end to end (25.1): every disk fails the coverage gate and is
flagged with load 0.0, `t_total` is 0, and the gate's verdict — the tool's own summary of the
situation — is "group is idle: no measured I/O to balance". Nothing unsafe happens (no load, no
moves), which is why this is Medium and not High; but the tool's core function is silently off,
the stated reason is false (the cluster is not idle), and the per-disk flags misattribute the
cause to sample coverage.

The design intended to catch this — verify-metrics, "must be run before relying on any plan"
(§3.3) — is structurally blind to it, for two composed reasons:

1. `verify_metrics()` resolves its own selector with `resolve_node_selector(metrics, None)` —
   deliberately, so it stays PVE-independent — so its queries never carry tier 2 or tier 3 and
   pass green on the very Prometheus where tier 2 will match nothing. The manual's `labels.node`
   entry says "verify-metrics never applies this auto-derived filter", which is honest, but it
   means the command verifies *different queries* than the ones the tool runs, for the first
   time since scoping existed (tier 3's node list had the same property, but a node-list
   alternation built from the live cluster cannot match nothing on a Prometheus that has the
   metrics at all — `nodename` is in the metric-server's own tag set; `cluster` is not, which is
   the whole difference).
2. The one check that *does* look at the label — `a189a6f`'s discovery scan — was calibrated for
   the opt-in design `a189a6f` itself shipped: "silent (no finding) when nothing carries it --
   most deployments never will, and that must not become routine noise". That reasoning was
   correct when `labels.cluster` defaulted to `null` (an absent label harmed nobody). `3b5f031`
   flipped the default and kept the silence: absence went from "fine" to "every query this tool
   issues matches nothing", and the scan still says nothing. The routine-noise argument now runs
   exactly backwards — the noise is the silence.

The documentation does connect the dots for a careful reader (the `labels.cluster` entry: "Set
this to `null` to opt back out on a Prometheus that genuinely carries no such label" and
"**Confirm what's actually there with `verify-metrics`** before assuming the default is right"),
and both commits rewrote seven documents apiece. But docs-as-mitigation for a silent default-on
failure is the P-01/T-03/W-01 family with behaviour attached, and this review has six precedents
saying the manual sentence is not enough.

**Recommendation:** keep the operator's chosen default, add the guard that must come with it.
(a) In `_check_sample_series`: when `metrics.labels.cluster` is set (default or explicit) and
the discovery scan found *no* series carrying it, emit a **warning** — not silence — naming the
label and the fix ("no series carries a `<label>` label; with the default
`metrics.labels.cluster` every load query would match nothing — set it to null or fix your
tagging"). Silence stays correct only for the explicit-`null` probe case, where the label is not
relied on. (b) At run time, one cheap signal closes W-07's half with it: when the resolved
selector is non-`None` and all six raw queries return zero series, say *that* (name the
selector) rather than letting the gate call the group idle. With those two, the default is as
safe to ship as the node tier it replaced.

### 25.9 W-07 — a selector that matches nothing is presented as an idle group (Low)

**Severity:** Low
**Files:** `src/proxmox_storage_drs/loadmodel.py` (`compute_group_load`), `gates.py:131-138`,
`docs/manual/25-show-load-and-verify-storages.md:86-90`

The runtime presentation half of W-06, separable because it has its own fix and its own
audience. A Prometheus outage and a selector-matching-nothing are indistinguishable in the
output today — per-disk "sample coverage 0% is below window.min_coverage" flags plus either
"per-disk load unavailable" or "group is idle" — but they have opposite diagnoses, and the
manual's own troubleshooting advice for that presentation ("**A Prometheus outage does not fail
this command** ... check `verify-metrics` first if you see this") dead-ends on the
selector case, because verify-metrics is green there (25.1). The information needed to
distinguish is already in hand at the point of decision: `compute_group_load()` knows the
selector it passed to every query and sees that all six came back empty. One warning — "the
resolved query filter {selector} matched no series at all" — placed next to the flags would turn
a misattributed idle into a one-line diagnosis.

### 25.10 W-08 — every run now hard-requires `Sys.Audit` for one scoping lookup (Low)

**Severity:** Low
**Files:** `src/proxmox_storage_drs/pve.py` (`cluster_name`), `cli.py`
(`_resolve_node_selector_for_run`), `docs/manual/00-installation.md:42-47`

With the default on, `_resolve_node_selector_for_run()` calls `client.cluster_name()` —
`GET /cluster/status`, which requires `Sys.Audit` at `/` (verified against pve-manager's
`PVE/API2/Cluster.pm`; also the one call in this project needing it) — on *every*
`plan`/`show-load`/`apply`/`explain` run. `PveClient._call()` wraps every HTTP error as a hard
`PveApiError`, so a token provisioned exactly per the pre-`3b5f031` manual (Datastore +
VM.Audit, no Sys.Audit) now fails the entire run with an error naming the call — including
`show-load`, a read-only diagnostic. `3b5f031` does update the manual to ask for `Sys.Audit`
unconditionally, so a *new* setup following current docs works; what breaks is the upgrade path,
and the breakage is a clean, explained error rather than a traceback. Two softer designs were
available: degrade a 403 to "no cluster name available" and fall through to the node-list tier —
which is *equally correct scoping*, not a weakening, and which `cluster_name()`'s own
"let the caller decide" contract already sketches for the missing-entry case — logging one
warning about the missing privilege; or catch it in `_resolve_node_selector_for_run()` only.
Hard-failing is a legitimate choice (fail loudly rather than silently run less-precisely
scoped), but it should be a *stated* choice: neither the commit message, the manual's
privilege note, nor the plan's §3.4 text mentions that the lookup failing takes the whole run
down rather than degrading.

**Recommendation:** either document the hard-fail as deliberate ("a run that cannot even
determine its own scoping stops"), or degrade with a warning — the latter costs nothing in
correctness and keeps `show-load` diagnostic. If degrading, keep it narrow (403/`PveApiError`
from this one call only), never a blanket swallow, per AGENTS.md §5.

### 25.11 W-09 — two sibling artefacts still show the old node-scoped default (Low)

**Severity:** Low
**Files:** `config/drs.example.yaml:86-93`, `docs/manual/29-explain.md:96`

`3b5f031` reworded the node-scoping story across seven documents and updated `20-verifying-metrics.md`'s
worked example to show what a real run prints now (a `cluster` label on the sample series and the
discovery line) — and left two siblings behind:

- `config/drs.example.yaml`'s `extra_selector` comment block still opens "**Every query is scoped
  to `labels.node =~` \"<this cluster's own node names>\"** automatically (fetched from the PVE
  API)" — now a description of the tier-3 *fallback*, not the default — and its example value
  `cluster="mycluster"` is now literally what the tool does unconfigured. The `labels.cluster`
  comment eleven lines above was rewritten for the new default; this block, which describes the
  same machinery, was not.
- `29-explain.md`'s worked example still prints its query-provenance line as
  `{nodename=~"pve01|pve02|pve03"}` — the opt-out configuration's output. An operator who reads
  the manual top to bottom (the `labels.cluster` entry says the default is `cluster="<name>"`)
  then meets an example showing the node alternation will reasonably wonder which one they will
  get.

Both are self-consistent snapshots of the pre-flip behaviour, exactly V-03's shape: the range
updated one example meticulously and the sibling fell outside the sweep.

**Recommendation:** rewrite the example-config block to describe the two auto-derived tiers in
order (cluster name by default, node list when opted out or unnamed) with `extra_selector` as the
outright override, and change `29-explain.md`'s provenance line to `cluster="..."` (or, better,
keep both and caption the null opt-out explicitly — but pick one deliberately). The
warning-string cross-reference test proposed in W-04 could grow an example-config counterpart
cheaply, but two hand fixes suffice.

### 25.12 What this pass confirms

- **The three size fixes are conservative in the right directions wherever a choice existed.**
  A present-but-sizeless managed disk falls to the VM config's `size=` (the plan's own
  pessimistic-when-wrong direction, and the tier upstream's schema makes the rare case);
  `approximate-size` now counts for foreign volumes instead of being dropped — strictly
  shrinking the one documented unsafe-direction gap in the data path (the reserve undercount),
  and upstream-verified to be an upper bound on virtual size for its only current producer; and
  the VM-own-node fetch makes the exact figure the common case rather than the approximate one.
  The residual gap — a foreign volume with *neither* field — still skips-and-warns toward
  undercounting the reserve; it is documented in the plan, the internals page and the warning
  itself, and `f2ddeeb` reduced its reach, but it is worth remembering the next time a plugin
  surfaces with neither field: `compute_reserve_status` builds its `used` from
  managed + `foreign_used_bytes`, not from `storage_status()`'s own `used`, so a skipped foreign
  volume is invisible to (C4)/(C5), not merely to the display.
- **The node-pair pre-pass cannot drift from the join.** `_disk_specs_from_config()` is the one
  parser both phases call; `_needed_content_node_pairs()` excludes unmanaged storages the join
  warns-and-skips anyway; the join's fallback to the storage-wide listing is unreachable for any
  pair the pre-pass could have missed (and harmless if it ever were); and `content_by_node`
  aliases the already-fetched per-storage listings rather than re-fetching them. The regression
  test asserts the VM's own node's endpoint was actually *called* (via the fake client's log),
  not merely that the final number matches — the stronger claim, and the right one.
- **`_pick_active_node()`'s corrected docstring is itself correct per upstream**: the *set* of
  volids does not vary by node (`approximate-size` rides on the same entries), which is what
  keeps snapshot-companion detection and the foreign-volume sum safe on the single per-storage
  pick; only per-item size fields do vary, and those are exactly what now goes to the VM's own
  node.
- **The packaging move loses one guarantee and says so.** With pulp a `Depends`, no Debian
  install can be solver-less, so the autopkgtest no longer proves heuristic-only operation at
  install time — `.agents/packaging.md`, the plan §2.1 rewrite and the `import-all` comment all
  state that narrower scope explicitly and name where the guarantee now lives (the unit suite's
  mocked-unavailable-backend cases) instead of quietly inheriting it. Build-Depends (under
  `<!nocheck>`) and the CI install list still exercise the MILP path, so build-time and
  install-time now agree rather than covering opposite configurations. The factual correction it
  carries is true (verified against `packages.debian.org`), and it explains a small historical
  mystery: why S-01's pulp-without-cbc crash never surfaced on a Debian install.
- **The changelog/version cut is mechanically sound**: 0.1.0 agrees in all three places,
  `test_version.py` and the CI `dpkg-parsechangelog` check both enforce it, the 0.0.1 entry is
  left as written by stated convention, and `trixie` as distribution matches both pipelines'
  build target. The entry's content is another matter — W-02.
- **The scoping feature's mechanics are built and tested to the project's usual standard.**
  The tier precedence is unit-tested tier by tier, including both corners easy to get wrong
  (`extra_selector` wins without any API call; a caller passing a `cluster_name` while the config
  opted out changes nothing); the call-skipping claims are proven by fakes that *raise* if a
  skipped call is made (`_NodeNamesClient`), not merely unasserted; `build_cluster_selector()`
  is an exact match with string-literal escaping, verified by test; `cluster_name()` handles all
  three response shapes (named, no-cluster-entry, unnamed) against a fake mirroring the
  live-confirmed response; the discovery scan covers configured-name, fallback-probe,
  silent-when-absent and values-across-metrics; and `labels.cluster`'s parsing, default,
  explicit-null and label-collision cases are all pinned. `_FakeClient` growing
  `cluster_name() -> None` keeps ~30 existing plan/apply/explain tests honestly on the
  node-selector path rather than silently re-routing through the new tier.
- **The two commits' documentation discipline is otherwise exemplary**: §3.4's tier list, the
  §3.5 read-path row for `GET /cluster/status`, `30-metrics.md`'s precedence walk-through,
  `50-pve-api.md`, the installation manual's privilege note, the configuration reference, the
  verifying-metrics page (both prose and worked example) and the example config's
  `labels.cluster` comment were all rewritten *twice* — once for the opt-in design, once for the
  default — with the PDFs rebuilt and stamped each time, and the second commit's message
  accurately says only the default moved, not the code paths. W-06 is about the one guard the
  flip needed and did not get, not about awareness or effort.

### 25.13 Assessment

The pass covers the most heterogeneous range since the eleventh: a release cut, a packaging
decision, three live-cluster fixes to one module, and a two-commit default change to how every
Prometheus query is scoped. The code quality holds throughout — every incident-driven fix
external-claim-checked against primary sources (two corroborated by pve-storage's own commits
nearly verbatim, one privilege claim corroborated by pve-manager's own ACL declaration), every
fix regression-tested on its failure mode, the node-pair pre-pass deterministic and
parser-shared, and the scoping tier's precedence, escaping and call-skipping all pinned by tests
that fail loudly if the guarantees drift. The Medium finding (W-06) is not carelessness but a
calibration that did not travel: the discovery scan's silence and the idle-mode presentation were
both *correct* when `labels.cluster` was an opt-in with a `null` default, and the commit that
flipped the default rewrote seven documents without revisiting either. That is precisely the
shape this review has learned to look for at defaults boundaries — the S-08/P-01 lesson in a new
place: behaviour flipped, guards left behind. W-06's fix is two warnings (one at verification
time, one at run time) that make the operator's chosen default as safe to ship as the tier it
replaced; W-08 wants the same treatment for the privilege boundary (degrade or document). The
remaining six findings are the documentation residue now characteristic of this codebase's
otherwise-clean ranges — five stale claims and a stale formula, an afternoon of writing, with
W-04's proposed warning-string cross-reference test still the structural fix that would retire
the whole class. Fix W-06 (and the changelog, W-02, before the first upload) and the range is
clean end to end.

---

## 26. Resolution of fourteenth-pass findings (W-01..W-09)

All nine findings were real; all nine are fixed, not refuted.

| ID | Status | How resolved |
|----|--------|--------------|
| W-01 | Resolved | The Optional-dependencies sentence in `docs/manual/30-safety-and-status.md` no longer carries the stale `auto` not yet" parenthetical; it now says plainly that every `execution.mode` runs with the minimal dependency set. |
| W-02 | Resolved | `debian/changelog`'s 0.1.0 entry relabelled: `execute.py` (not `state.py`) is phase 7, `auto` mode/time windows is phase 8, `forecast.py`'s seasonal-naive backtest is phase 9, and `explain` is its own bullet rather than a misattributed phase. The range's own post-cut features (the size tiers, the VM-own-node fetch, the cluster-scoping tier and its default, and this pass's own W-01..W-09 fixes) were initially folded into the 0.1.0 entry as two extra bullets; a follow-up commit moved them to their own `0.1.1` entry instead (operator correction: a changelog entry should summarize everything since the *previous* entry, not just the most recent commit, and post-cut work belongs in a new entry rather than backfilled into an old one) -- `debian/changelog`'s current `0.1.0` stanza is back to describing only what that version actually was. |
| W-03 | Resolved | `docs/internals/60-topology.md`'s stage-list header now says "six stages" and sketches the actual two-concurrent-phases-plus-join shape; its two remaining `_collect_vm_disks` references (the header and the lock section) are now `_join_vm_disks`/`_fetch_vm`; `topology.py`'s `_ClusterData` docstring now says "one argument bundle (plus `content_by_node`)" instead of the stale seven-parameter count. |
| W-04 | Resolved | `docs/manual/25-show-load-and-verify-storages.md`'s Warnings-block paragraph now names the two new size-fallback warnings and the foreign-volume-undercount warning, alongside the existing dangling-reference case, each with its own one-line interpretation. |
| W-05 | Resolved | `IMPLEMENTATION_PLAN.md` §3.5's expected-call-count formula recomputed (`GET /cluster/status`, the node-list tier's `GET /nodes`, and an explicit `\|extra content pairs\|` term for the per-`(node, storage)` amplification, with its worst-case bound stated); `docs/internals/60-topology.md`'s step 5 gained the same bound. |
| W-06 | Resolved | `_check_sample_series()` now emits a **warning** (not silence) when `metrics.labels.cluster` is set (default included) and no series anywhere carries that label, naming the label and the fix. Silence is now reserved for the explicit `metrics.labels.cluster: null` opt-out. `IMPLEMENTATION_PLAN.md` §3.4 and `docs/internals/30-metrics.md` updated to match. |
| W-07 | Resolved | `loadmodel.GroupLoad` gained `no_series_matched: bool`, set by `compute_group_load()` when a non-`None` selector was applied and all six raw queries plus the coverage query came back with zero series anywhere — distinct from an ordinary idle group. `gates.evaluate_group_gates()` and `cli.py`'s show-load human renderer both name the scoping mismatch explicitly ("the resolved query filter matched no series at all") instead of reporting the group as idle. `docs/manual/25-show-load-and-verify-storages.md` documents the new line. |
| W-08 | Resolved | `cli._resolve_node_selector_for_run()` now catches `PveApiError` from `client.cluster_name()` narrowly, logs one warning naming the cause, and falls through to the node-list tier — equally correct scoping, per the recommendation, rather than failing the whole run (including read-only `show-load`) over a denied `Sys.Audit` call. `docs/manual/00-installation.md` and `docs/internals/50-pve-api.md` updated to describe the degrade. |
| W-09 | Resolved | `config/drs.example.yaml`'s `extra_selector` comment block rewritten to describe both auto-derived tiers (cluster name by default, node list as fallback) instead of only the pre-flip node-scoping story, and its example value changed off the now-live-by-default `cluster="mycluster"`. `docs/manual/29-explain.md`'s worked example's `data source:` line changed to the default cluster-scoped form, with the node-list form kept as a captioned alternative for the `null` opt-out. |

New/updated regression tests: `test_check_sample_series_warns_when_relied_on_cluster_label_absent`
and a renamed `test_check_sample_series_silent_when_opted_out_and_no_cluster_label_anywhere`
(`test_metrics.py`); `test_resolve_node_selector_for_run_degrades_to_nodes_on_a_denied_cluster_call`
(`test_cli.py`); `test_compute_group_load_flags_a_selector_matching_no_series_at_all` plus two
sibling tests pinning `no_series_matched` False in the ordinary-idle and real-data cases
(`test_loadmodel.py`); `test_no_series_matched_reports_the_query_filter_not_idle` (`test_gates.py`);
`test_show_load_human_output_names_a_selector_matching_nothing_not_idle` (`test_cli.py`).

Verification: dev venv `python3 -m pytest` — **681 passed, 1 warning** (the same benign
`ConvergenceWarning`), **98.66% line coverage**. `make check` clean (fmt, lint, typecheck, test,
fixtures, docs-check — `IMPLEMENTATION_PLAN.pdf` rebuilt to 44 pages, internals PDF to 47, manual
PDF to 38, all three stamps regenerated alongside their Markdown).

---

## 27. Operator correction: the cluster-naming-label default was a wrong assumption

The whole `metrics.labels.cluster` auto-scoping tier added in pass 25/26 (§3.4's tier 2,
`build_cluster_selector()`, `PveClient.cluster_name()`, the W-06/W-07/W-08 fixes above) rested on
one claim, stated as fact in that pass's own writing: "this project's deployments carry [a
cluster-naming tag] as standard practice." Diagnosing a live `verify-metrics` false-positive
("no series to measure coverage on" despite the metric genuinely existing) surfaced that this
claim was simply wrong — there is no such convention across this project's real deployments, and
nothing about the Telegraf/InfluxDB `blockstat` pipeline guarantees a `cluster` label at all. The
operator: "Yesterday I wrongly assumed that there is a fixed 'cluster' metric label that matches
the cluster by default, this assumption was totally wrong."

**Fix, applied forward (not by rewriting the fourteenth-pass sections above, which stand as the
historical record of what was believed and done at the time):**

- `metrics.resolve_node_selector()` loses tier 2 entirely. The precedence is back to two tiers:
  `metrics.extra_selector` (operator-set, verbatim) when set, else the auto-derived node-list
  filter from this cluster's own `GET /nodes` — the same default the tool had before pass 25 ever
  introduced the cluster-name tier.
- `build_cluster_selector()`, `PveClient.cluster_name()` (`GET /cluster/status`, the `Sys.Audit`
  privilege it alone needed), `metrics.labels.cluster` (config field, schema property,
  `_check_metrics`'s pairwise-distinctness check), and `_check_sample_series()`'s cluster-label
  discovery scan/warning are all removed as dead code built on the mistaken premise — not merely
  disabled behind an opt-out.
- `cli._resolve_node_selector_for_run()` simplifies to `extra_selector` else `resolve_node_selector(metrics,
  client.node_names())` — no more API call, no more privilege-degrade branch, since there is no
  longer a second tier to degrade from.
- `loadmodel.GroupLoad.no_series_matched` and its gates.py/cli.py "the resolved query filter
  matched no series at all" reporting (W-07) are kept as-is: a node-selector mismatch is just as
  real a failure mode as a cluster-selector one was, so that diagnostic still earns its place —
  only its message wording dropped the now-nonexistent `metrics.labels.cluster` mention.
- Every doc this feature touched (`IMPLEMENTATION_PLAN.md` §3.4/§3.5, `docs/internals/30-metrics.md`,
  `docs/internals/50-pve-api.md`, `docs/manual/00-installation.md`, `docs/manual/10-configuration.md`,
  `docs/manual/20-verifying-metrics.md`, `docs/manual/25-show-load-and-verify-storages.md`,
  `docs/manual/29-explain.md`, `config/drs.example.yaml`) rewritten to match, each carrying a short
  note that the removed tier existed only on a mistaken assumption, not a Prometheus finding.
- Regression tests removed with the code they tested (`test_build_cluster_selector_*`,
  `test_resolve_node_selector_*cluster*`, `test_check_sample_series_*cluster*label*`,
  `test_cluster_name*` in `test_pve.py`, `test_cluster_label_*` in `test_config.py`, the
  `cluster_name`-aware branches of `_NodeNamesClient`/`_FakeClient` in `test_cli.py`); the four
  `_resolve_node_selector_for_run` tests that still make sense (override wins, node-list default,
  none-resolves) kept, renamed where the cluster-tier framing no longer applied.

Net effect: a config that never set `metrics.labels.cluster` (i.e. relied on the removed default)
now gets the plain node-list filter it always would have gotten pre-pass-25 — a strictly more
conservative, already-correct scoping, not a new risk. A config that explicitly set
`metrics.labels.cluster` to a real value now fails schema validation (`additionalProperties:
false`) rather than being silently ignored; the equivalent filter is
`metrics.extra_selector: '<label>="<value>"'`.

Verification: `make check` clean (fmt, lint, typecheck, test, fixtures, docs-check —
`IMPLEMENTATION_PLAN.pdf`/internals/manual PDFs rebuilt) — **661 passed**, **98.64% line
coverage**.

---

## 28. Real-world finding: a non-numeric value silently drops one metric per disk, independently of the other five

Live dogfooding against a second production cluster (a fresh InfluxDB-transport/gigapipe metrics
pipeline switch) surfaced a real gap in `compute_disk_coverage()`'s own documented assumption:
"coverage gaps are a property of the underlying Telegraf scrape, not of which of the six raw
quantities is read." That holds for *timing* gaps (the scrape didn't happen), but not for one
specific *type*-based gap: InfluxDB's line protocol fixes a field's type from its first write, and
Telegraf's Prometheus-compatible output silently drops a field the instant it observes a
non-numeric value for it — Prometheus/OpenMetrics has no string sample type. That drop is per
*field*, not per scrape cycle, so it can hit exactly one of the six configured metrics for one
disk while the other five (including `read_ops`, the one metric `compute_disk_coverage` actually
checks) keep reporting normally. A coverage check that only ever looks at `read_ops` — by design,
to avoid six times the Prometheus load — cannot see this if the dropped field is one of the other
five.

**Fix:** `_check_sample_series()` (which already runs one instant query per metric, for steps 2-3)
now also collects the full `(vmid, device)` set each of the six metrics reports, and a new pure
helper, `_check_cross_metric_disk_consistency()`, compares each metric's set against the union
across all six — warning, naming the metric and the specific disk(s), whenever one metric's set is
a strict subset of another's. This costs nothing extra: it reuses instant-query results
`_check_sample_series` already fetches for an unrelated purpose, rather than issuing any additional
Prometheus queries. `_check_metric_names_exist`'s "does not exist" error and `_check_sample_series`'s
"no series returned" warning both gained the same explanatory hint, since a metric missing
*everywhere* (rather than for just one disk) is the same underlying cause taken to its extreme.
`IMPLEMENTATION_PLAN.md` §3.3, `docs/internals/30-metrics.md`, and
`docs/manual/20-verifying-metrics.md` updated to describe the new check and its "if it fails"
guidance.

New regression tests (`test_metrics.py`): `test_disk_keys_seen_skips_series_missing_either_label`,
`test_cross_metric_disk_consistency_silent_when_all_metrics_agree`,
`test_cross_metric_disk_consistency_warns_on_a_dropped_field`,
`test_cross_metric_disk_consistency_truncates_a_long_missing_list`,
`test_check_sample_series_reports_a_cross_metric_gap`.

Verification: `make check` clean — **666 passed**, **98.65% line coverage**; all three PDFs
rebuilt.

---

## 29. Fifteenth-pass review — `collect-testdata`/`--replay` (§16), the corpus, phase-11 logging, and the dogfooding fixes

Reviewed commit range `31f03e4..HEAD` (the W-01..W-09 fixes are recorded in section 26; the
cluster-label removal and the cross-metric fix, which this range also contains, are already
recorded as sections 27 and 28 and are not re-reviewed here). Twenty-nine non-merge commits,
≈8,600 inserted lines of code, tests and documentation (plus ≈736,000 lines of committed corpus
data), the largest single addition to the tool since the engine itself:

- `6ca584a` — plan §16 written ahead of the code (the specification habit this review has
  endorsed since the F-passes): the bundle layout, the superset capture, the anonymization rules,
  the command, `--replay`, and `tests/corpus/`.
- `ff68910` — `config.py`/schema gain the `support{}` block; `proxmox.host`/`prometheus.url`
  become schema-optional with the presence check moved to `load_config(require_connection=...)`,
  so a bundle's credential-free `config.yaml` validates.
- `74812e5`, `87529a3`, `492b281`, `7937177` — `anonymize.py` (pure), `collect.py` (capture,
  recording clients, manifest, deterministic writer), `replay.py` (the two replay clients), the
  CLI wiring (`collect-testdata`, the global `--replay`), and `tests/corpus/validate_corpus.py`.
- `f7cbcf1` and eight `fix/collect-testdata-*` commits — the docs, and the eight real bugs the
  first live capture against the dev cluster found (pattern-expanded storages lost from
  `config.yaml`, anonymized selectors issued to the real Prometheus, sort-order-dependent query
  text, un-rebased sample timestamps, a dropped node label, a device-label collision with
  Prometheus's own `instance` scrape label, metric names validated as device keys, and real names
  in the manifest call log).
- `f7946db`, `9d4dd51`, `8dc3934`, `8f237ff` — the two committed corpus bundles (7.3 MB and
  4.6 MB, both under the 8 MiB ceiling), the docs marking phase 10 landed, and the
  move-count-as-proxy fix in `check_milp_vs_heuristic` (the false positive the 7-day bundle found).
- `72fb157` — `explain`'s closest-rejected-move section (`heuristic.best_single_disk_alternative()`).
- `59ff95c`, `44471e8` — plan §2.3 (the logging policy re-plan) and its implementation, phase 11.
- `687322e` — `json_safe()`: no `Infinity`/`NaN` in any log record or `--json` report.
- `0be3d44`, `3215cfe` — the README quickstart, `docs/manual/05-metrics-pipeline.md`, shipping the
  Markdown sources in the package, and the manpage's previously-hand-maintained `collect-testdata`
  option list.
- `2bcd2c3`, `7386477` — the 0.1.1 version/changelog cut (pre-dating most of the above; see X-04).

### 29.1 Verification run

- Dev venv `python3 -m pytest`: **804 passed, 1 warning** (the same benign statsmodels
  `ConvergenceWarning` noted since the eleventh pass), **95.94% line coverage** — a drop from the
  98.6% of the last three passes, accounted for by the new modules landing at `collect.py` 85%,
  `replay.py` 86%, `anonymize.py` 95% (the aggregate floor of 85% still clears; per-module floors
  do not exist). `make check` clean end to end: fmt-check, flake8, mypy (in its own
  `.venv-typecheck/`), test-with-coverage, the §14 fixture `--check`, **corpus-check** (the new
  gate: scrub audit + invariants + MILP-vs-heuristic + regression `--check` over both committed
  bundles, passing), and docs-check over all three PDF stamps plus the manpage.
- **The full capture → write → replay round trip was exercised at the CLI level** against the
  committed `bzed-dev-cluster-24h` bundle: `--replay ... plan/explain/show-load/verify-metrics/
  verify-storages` all complete, `--replay ... apply` and `--replay ... --mode auto <cmd>` exit 2
  as §16.5 requires, and `tests/unit/test_replay.py`'s never-constructs-a-`requests.Session`
  assertions hold on this tree.
- **The X-02 leak was reproduced empirically, not inferred**: a `requests.RequestException`
  raised against `https://prometheus.internal.example.invalid:9090/...` renders as
  `HTTPSConnectionPool(host='prometheus.internal.example.invalid', port=9090): Max retries
  exceeded ...`; that string, run through `_redact_free_text()` with a node named `pve01`
  configured, comes out as `... host='node-<8hex>.corp.example' ...` — the node name is mapped,
  **the DNS domain is not**, and `_check_value_patterns()` (the scrub audit's own checker, invoked
  directly) returns **zero violations** for it, because `_PUBLIC_SUFFIX_HOSTNAME_RE` matches only
  `.com|.net|.org|.local`. A `.example`/`.internal`/`.corp`/`.lan`/bare host passes all nine
  value checks.
- **X-01 was confirmed against the shipped bundles' shape**: both committed `config.yaml`s carry
  `exclude: {disks: []}` — the leak is latent in the code path
  (`collect.py`'s `"disks": list(exclude.disks)`), not present in the corpus, which is exactly why
  neither the audit nor this suite can currently see it.
- **The determinism claim of §16.1 was checked as specified**: `test_write_bundle_dir_is_
  deterministic` runs the *collector* twice against the same fakes and salt (fixed `now`), not
  merely the writer, and compares every file byte-for-byte — the claim is tested at the strength
  the plan states.
- **`debian/` packaging kept step**: `debian/copyright` gained the `tests/corpus/*` stanza the
  same month the first bundle landed (§16.6); `debian/pve-storage-drs.docs` now ships the
  Markdown sources of all three documents beside the PDFs, with `override_dh_compress` keeping
  both uncompressed; the manpage's `OPTIONS` documents all eight `collect-testdata` options plus
  `--replay`/`--log-format`/`--log-level`, and the new `test_help_covers_every_subcommand_option`
  extends the options-coverage test from the global parser down to subcommands (closing the second
  hand-kept list `.agents/documentation.md` forbids).
- The §15.1 traceability, example-config and manual rows for all four `support.*` knobs landed in
  the implementing commit, as §16.7 requires; the corpus README carries §16.3's honesty statement
  ("safe to hand to the author, not safe to publish") for the author's side.

### 29.2 Findings summary

| ID | Severity | Module(s) | Summary |
|----|----------|-----------|---------|
| X-01 | Medium | `collect.py` | `exclude.disks` (`"vmid:device"` strings) is carried verbatim into the bundle's `config.yaml` — §16.3 explicitly lists it among the identifiers that must move with the mapping, so a real vmid leaks into the one file an operator is told to read before sending, and the exclusion silently stops matching anything at replay |
| X-02 | Medium | `collect.py`, `pve.py`, `metrics.py` | A transport-level failure during capture (connection refused, timeout, DNS) writes the endpoint's hostname/FQDN into `manifest.json`'s call-log `detail` via the exception's own text — `_redact_free_text` maps only vmids/node names/storage names, and the scrub audit's hostname pattern covers only `.com/.net/.org/.local` (reproduced end to end) |
| X-03 | Medium | `tests/corpus/validate_corpus.py` | The scrub audit applies its key allowlist to only the five top-level `pve/` files; every per-VM/per-storage file, every `prometheus/` file, `manifest.json` and `findings.json` get value-pattern checks only — while §16.6 and the script's own docstring claim "every file, every key, checked against anonymize.py's allowlist". X-01 is a live collector bug this audit could not see |
| X-04 | Medium | `debian/changelog` | The unreleased 0.1.1 entry's second bullet describes the cluster-scoping feature section 27 removed — `metrics.labels.cluster` default-on, the discovery scan, the W-06/W-07/W-08 behaviours — and advises "set that key to null", which the current schema rejects outright; and it records none of the range's actual post-cut features (`collect-testdata`, `--replay`, `support{}`, the corpus, the logging policy and its two new global options, the JSON fix, the cross-metric check, `explain`'s rejected-alternative) |
| X-05 | Low | `cli.py`, `collect.py`, `docs/manual/26-*.md` | Every `collect-testdata` run performs the full PVE topology read pass twice — once bare for the estimate, once again through the recording client inside `capture_bundle()` — contradicting §16.2's "the cost is one planning run's worth of API calls, not a multiple of it"; and manual 26's `--estimate` row says "exits; fetches nothing" when it performs that entire PVE inventory read (only Prometheus is skipped) |
| X-06 | Low | `logging_setup.py`, plan §2.3 | §2.3's "Where the handler is attached" mandates the handler on the `proxmox_storage_drs` logger, "not the root logger"; the built code puts one handler on root with the package logger carrying only a level — a deliberate, well-argued deviation (the commit message explains caplog/embedding/no-duplicate-emission) that was never written back into a plan section marked "Status: implemented". Same subsystem: `--log-level warning|error` silently bypasses the mandatory `INFO` audit-trail floor, which plan and manual both describe as yielding to `--quiet` alone |
| X-07 | Low | `tests/corpus/validate_corpus.py`, plan §16.6 | §16.6's "What the suite asserts" promises five invariant properties (Σ r_s = 0, §8.1's transient predicate at every step, (C2) format/group legality, §7.3's per-move duration and saturation guards, objective re-equality) plus "both MILP backends agree to within the §5.5 tolerance"; `check_invariants()` implements only group-storage membership and no MILP-vs-MILP check exists at all — the plan presents as running on every `make check` what is in fact left to the pipeline's own internal enforcement |
| X-08 | Low | `collect.py`, plan §16.1/§16.3 | Three §16 bundle promises were never built: the manifest does not flag the `extra_selector` rewrite ("says so in the manifest" — §16.3); no PVE/Prometheus version strings are captured anywhere in a bundle (§16.1's "versions", §16.3's preserved list — they exist only in `submission.yaml` on the corpus side); and metric names are carried verbatim rather than canonicalized to `drs_*` (the per-kind table's "Metric name" row describes a mapping that does not exist — the built behaviour is self-consistent and leaks nothing, but it is not what the plan says) |
| X-09 | Info | `anonymize.py`, `collect.py` | Anonymization small print: the 8-hex (32-bit) pseudonym truncation has collision handling only for vmids — two storages/nodes colliding would silently merge bundle records (~n²/2³³, tiny but undetected); `counts.dropped_records` undercounts (the `None` returns of `_anonymize_disk_value`/`_anonymize_vm_config` and the unknown-node pruning of storage `nodes` fields never increment it); and `--estimate`'s query count treats a multi-day range as one query — day-sized chunking (§16.2) means the real HTTP request count at the 7 d default is ≈7× the range-side figure printed |
| X-10 | Info | `replay.py`, `cli.py`, `heuristic.py`, `validate_corpus.py` | Assorted: `--replay bundle.tar.gz` — the form a bundle is actually sent in — fails with "not a bundle directory" and no "unpack it first" hint, and manual 26 never says to unpack; `explain`'s new "no moves made: the objective is lowest at the current assignment" line asserts what it does not verify (a fully deadlocked plan also moves nothing); the non-full-matrix sweep records cpsat as "not installed" on machines where it is installed; and a `--replay ... --mode auto` run announces itself (run_started, and a mode_override WARNING at the default level) before the exit-2 refusal that says it will not start |

### 29.3 X-01 — `exclude.disks` is carried verbatim into a bundle's `config.yaml`

**Severity:** Medium
**Files:** `src/proxmox_storage_drs/collect.py:1346-1354` (`_anonymized_config_dict`)

§16.3, "The configuration in the bundle": "**Every identifier is mapped with the same mapping as
the data**: `groups[].name`, `groups[].storages[].id`, `exclude.vmids`, `exclude.storages`,
`exclude.disks` and `exclude.tags`. A knob the engine compares against a captured value must move
together with it or the exclusion silently stops applying, which is a quiet behaviour change in a
file that claims to reproduce a run." The implementation maps four of the six: `exclude.vmids`
through `mapper.vmid()` (dropping unregistered ones), `exclude.storages` through
`mapper.storage()`, `exclude.tags` through `mapper.tag()` — and then `"disks": list(exclude.disks)`
carries the entries **verbatim**. An `exclude.disks` entry is a `"vmid:device"` string
(`docs/manual/10-configuration.md` §`exclude.disks`, `config/drs.example.yaml`), so:

- **Privacy:** the real vmid — an identifier §16.3's own per-kind table pseudonymizes everywhere
  else it appears, and whose mapping is the whole point of `exclude.vmids` two lines above — is
  written into the bundle in the clear. It is not an incidental number: an operator who excluded
  `101:scsi1` made a deliberate, meaningful choice about a specific VM, in the one file the manual
  tells them to read before sending. The scrub audit cannot see it (`config.yaml` gets only the
  credential-words check; `"101:scsi1"` matches none of the nine value patterns), and the
  committed bundles are clean only because their operators never configured `exclude.disks`.
- **Behaviour:** at replay, `topology.py` compares `config.exclude.disks` against disk keys built
  from *pseudonymized* vmids — `101:scsi1` matches nothing, and the exclusion silently stops
  applying. This is precisely the "quiet behaviour change in a file that claims to reproduce a
  run" the quoted sentence exists to forbid.

**Recommendation:** map the vmid component through `mapper.vmid()` (device keys pass through
unchanged, per §16.3's device rule), dropping entries whose vmid was never registered — the exact
shape of the `exclude.vmids` line above it. A one-line addition to the capture test asserting a
configured `exclude.disks` round-trips pseudonymized would pin it; extending the scrub audit's
`config.yaml` check to reject a `vmid:device`-shaped string under `exclude.disks` that is not a
registered pseudonym (X-03's fix) would catch a regression of it mechanically.

### 29.4 X-02 — a transport failure during capture writes the endpoint hostname into the manifest

**Severity:** Medium
**Files:** `collect.py:203-217` (`_guarded`), `collect.py:334-346`
(`RecordingPrometheusClient._get`), `collect.py:1417-1434` (manifest call log),
`pve.py:239-244`, `metrics.py:242-254`

The call log exists to record failures ("failures are recorded, never rendered as absence",
§16.2) — and it is exactly a failure that leaks. `_guarded()` and `RecordingPrometheusClient._get`
store `str(exc)` as the call's `detail`; for the transport-level failures the log is for,
`pve.py`'s `f"...: request failed: {exc}"` and `metrics.py`'s
`f"Prometheus request to {path} failed: {exc}"` embed the `requests` exception's own text, which
begins `HTTPSConnectionPool(host='<hostname>', port=...)` — the *configured endpoint*, whose
presence in a bundle §16.3 is otherwise careful to prevent (`proxmox.host`, `prometheus.url` and
every auth field are dropped from `config.yaml` precisely because a hostname is an identifier).
`_build_manifest` runs every `detail` through `_redact_free_text()`, but that function substitutes
only registered vmids, known node names and known storage names — an endpoint hostname shares a
substring with a node name only by coincidence (and then only the node part is mapped, leaving the
domain: see 29.1). The scrub audit is the designated backstop and does not catch it either: its
hostname pattern covers four suffixes, `.com|.net|.org|.local`, and a Prometheus or PVE host in
`.example`/`.internal`/`.corp`/`.lan` — or a bare hostname — passes all nine value checks, which
29.1 demonstrated directly.

This needs a connection failure during capture to fire, which is not exotic: a Prometheus restart
mid-capture, a API-timeout on a large `/content` listing, a DNS blip. And the manifest is shipped
to a third party by design.

**Recommendation:** three cheap layers, any two of which suffice. (a) In `_build_manifest`,
strip `https?://…` (and `host='…'`/`url: …` fragments) from `detail` before redaction — or record
the exception *class* plus the outcome and keep the full text for stderr, where §2.3's log already
carries it locally and no bundle is involved. (b) Teach the scrub audit a `host=`/URL-shaped
pattern that is not suffix-dependent. (c) A capture test that fails one call with a
`requests.ConnectionError` whose message embeds a `.example` host, asserting the manifest stays
clean — the test the current suite lacks for the whole `detail` channel.

### 29.5 X-03 — the scrub audit checks keys against the allowlist for five files only

**Severity:** Medium
**Files:** `tests/corpus/validate_corpus.py:132-138` (`_PVE_ALLOWLISTS`), `:165-181`
(`_scrub_json_file`), `:201-217` (`_scrub_pve_dir`); plan §16.6; the module docstring

§16.6, check 1: the scrub audit "walks every file and fails on: **any key not in
`anonymize.py`'s allowlist** (the same allowlist the collector uses, so the two cannot drift)";
`validate_corpus.py`'s own docstring opens "every file, every key, checked against
`anonymize.py`'s allowlists". The implementation applies a key allowlist to exactly five files —
the top-level `cluster-resources-{vm,storage}.json`, `storage-definitions.json`, `nodes.json` and
`cluster-tasks.json`. Everything else — all of `vm-config/`, `vm-snapshots/`,
`vm-status-current/`, `storage-status/`, `storage-content/`, every `prometheus/` payload,
`manifest.json` and `findings.json` — is passed `allowlist=None` and receives only the nine
value-pattern checks. The per-kind allowlists for those files (`VM_CONFIG_EXTRA_FIELDS` +
`DISK_KEY_RE`, `VM_SNAPSHOT_FIELDS`, `VM_STATUS_CURRENT_FIELDS`, `STORAGE_CONTENT_FIELDS`,
`STORAGE_STATUS_FIELDS`) exist in `anonymize.py` and are simply never consulted by the audit.

The gap is the audit's own reason for existing. It "assumes the collector has a bug, which is the
only useful assumption to make about a privacy control" (§16.6) — and a collector bug of exactly
the assumed shape (a future edit that stops filtering, or filters by a denylist, before writing
`vm-config/<vmid>.json`) would produce extra keys in precisely the files that carry the richest
free text (a VM config's `description`, `sshkeys`, `net0` are all one failed filter away), with
the audit green. X-01 is a present-tense demonstration of the class: a real identifier reaching a
bundle through a channel the audit does not model. The `prometheus/` side has the same shape one
level down: §16.3's table drops every label except the three configured ones, and nothing checks
that either.

**Recommendation:** the per-file allowlists already exist; wire them in — a mapping from bundle
path pattern to `anonymize.py` constant (`vm-config` → `filter_vm_config_fields`'s key set,
`vm-snapshots` → `VM_SNAPSHOT_FIELDS`, and so on), failing on any extra key, exactly as the five
top-level files already do. For `prometheus/instant|range` files the structural keys are fixed
(`query`/`result`/`start`/`end`/`step`) and the `metric` dicts can be checked against the three
label names the bundle's own `config.yaml` carries. Then fix the docstring to match whatever
scope is actually enforced. This is the W-04 lesson (the structural test that retires the class)
applied to privacy instead of warnings.

### 29.6 X-04 — the 0.1.1 changelog describes a feature that no longer exists

**Severity:** Medium
**Files:** `debian/changelog:3-23` (last touched by `7386477`, before `77370cf`)

The 0.1.1 entry's second bullet, in full, is a description of the cluster-scoping feature:
"verify-metrics now reports every cluster-naming label value it sees across your metrics, and
plan/show-load/apply/explain scope every query by this cluster's own name by default
(`metrics.labels.cluster`, default `cluster`) ... set that key to null to opt back out" — and a
third bullet walks through the W-06/W-07/W-08 fixes built on it, including "A denied
`GET /cluster/status` ... degrades to the node-list scoping tier". Section 27 then removed the
entire tier: `metrics.labels.cluster` no longer exists in the schema (a config carrying it now
fails `additionalProperties: false`), the discovery scan is gone, `cluster_name()` and its
`Sys.Audit` privilege are gone. An operator reading the entry for the release they are about to
install would be told to configure a key the release rejects, and told about behaviours
(`verify-metrics` cluster-label reporting, the 403 degrade) that are not in it. Meanwhile the
entry records none of what the release actually adds beyond the size fixes: no
`collect-testdata`, no `--replay`, no `support{}` block (four new config knobs), no corpus, no
`--log-format`/`--log-level`, no `json_safe` fix, no cross-metric consistency check, no
`explain`'s rejected-alternative, no quickstart/metrics-pipeline documentation.

This is W-02's family one release later, with the aggravation that the entry does not merely
mislabel history — it instructs the reader to use a key that errors. The convention the W-02
resolution itself recorded ("a changelog entry should summarize everything since the previous
entry, not just the most recent commit") was applied once, in `7386477`, and then not again
across the twenty-seven commits that followed it.

**Recommendation:** while 0.1.1 is still unreleased: delete the cluster-scoping bullet and the
parts of the W-fixes bullet that describe removed behaviour (W-07's `no_series_matched` reporting
survives — keep that half), and add the missing features. The structural fix is the same one
W-02 got: when a feature is *removed* before its release, the changelog entry that announced it
is part of the removal commit's blast radius, alongside the seven documents section 27 did rewrite.

### 29.7 X-05 — `collect-testdata` walks the PVE read path twice; `--estimate` is not side-effect-free

**Severity:** Low
**Files:** `src/proxmox_storage_drs/cli.py:3315-3316` (`_handle_collect_testdata`),
`collect.py:1017` (`capture_bundle`), `docs/manual/26-collect-testdata-and-replay.md:44`

§16.2: "This is the same read path a `plan` run performs (§3.5's 'expected call count per run'),
so the cost is one planning run's worth of API calls, not a multiple of it." The implementation
runs it twice on every invocation: `_handle_collect_testdata()` builds a topology with the bare
client (for the estimate), and `capture_bundle()` immediately builds it *again* through the
`RecordingPveClient` — two full inventory passes (every VM config, every content listing, every
status call) on a production API, per capture. The plan's own intent — "derived from the topology
pass it has already done" — describes passing the first topology (or the recording client) into
the estimate. Relatedly, manual 26's `--estimate` row reads "Print the estimate above and exit;
**fetches nothing**": the estimate requires the complete PVE inventory read described above; only
Prometheus is untouched. An operator reassuring themselves with `--estimate` before touching a
busy cluster is told something false about what it does to that cluster's API.

**Recommendation:** build the recording client first and derive both the estimate and the capture
from its one topology pass (the recording client exists to make exactly this reuse safe); until
then, `--estimate`'s row should say "reads the full PVE inventory (one planning run's worth of
API calls); fetches nothing from Prometheus". The per-call amplification is bounded and read-only,
which is why this is Low — but §3.5's call-count formula was just recomputed for W-05, and this
doubles it again for one command.

### 29.8 X-06 — §2.3's handler-placement text says the opposite of the build, and `--log-level` escapes the mandatory floor

**Severity:** Low
**Files:** `logging_setup.py:203-205, 219-229`; `IMPLEMENTATION_PLAN.md` §2.3 ("Where the handler
is attached"); `docs/manual/35-logging.md:53-56`

Two drifts in one subsystem, both defensible builds over stale/aspirational text:

1. §2.3, verbatim: "On the `proxmox_storage_drs` logger, **not the root logger**." The built code
   attaches its single handler to *root* and puts the run's level on the package logger
   (`root.handlers = [handler]`, `package.setLevel(level)`, `propagate = True`), with a comment
   explaining why: handler-on-package plus `propagate = False` was tried and hides records from
   pytest's `caplog` and from anything embedding the package. The behavioural requirements
   (third-party loggers stay at `WARNING` under `-v`, raised only by `-vv`; no record emitted
   twice) are met and tested — but the plan section is banner-marked "Status: implemented", and
   its one structural instruction is the opposite of the implementation. AGENTS.md §7's rule —
   plan and code change together, and if the plan was wrong, fix the plan in the same commit —
   was followed for the three level corrections and the file-sink retraction (both called out in
   §2.3 itself) but not for this paragraph.
2. The mandatory `INFO` floor exists because "an unattended timer that silently migrated 400 GiB
   is not acceptable output regardless of how the unit file was written" (§2.3), and both plan and
   manual name exactly one escape hatch: `--quiet`. The build grants a second, undocumented one:
   `configure_logging()` treats *any* explicit `--log-level` as opting out
   (`explicitly_lowered = quiet or log_level is not None`), so `apply --mode auto --log-level
   warning` runs unattended with no audit trail, and neither §2.3, `--log-level`'s help text
   ("Wins over -v and --quiet") nor manual 35 mentions the floor interaction. The code's own
   docstring documents the choice; nothing operator-facing does.

**Recommendation:** (1) rewrite the placement paragraph to describe the built design (one root
handler; the package logger carries the level; third-party floors at root do the separation) with
the caplog/embedding rationale, exactly as §2.3 already does for its other as-built corrections.
(2) Either let the floor win over `--log-level` values *below* it for `confirm`/`auto` (matching
the documented "only `--quiet` escapes"), or keep the build and add one sentence to §2.3, the
`--log-level` help text and manual 35's timer paragraph naming `--log-level error|warning` as the
second way to discard an `auto` run's only record.

### 29.9 X-07 — `validate_corpus.py` implements one of §16.6's five invariant assertions

**Severity:** Low
**Files:** `tests/corpus/validate_corpus.py:360-383` (`check_invariants`), `:386-438`
(`check_milp_vs_heuristic`); plan §16.6

§16.6 presents four kinds of assertion the corpus provides, and the plan's phrasing is that they
run: "The scrub audit — ... runs on every bundle in the corpus on every `make check`"; "2.
**Invariants, not optima.** For every bundle and every variant: `Σ r_s = 0` ... §8.1's transient
predicate holds at every step of the emitted order; every move ... (C2) permits ...; §7.3's
per-move duration rule and saturation guard hold for every accepted move; the objective the
scheduler was handed equals the objective recomputed from the final assignment." The built
`check_invariants()` verifies one thing — that each move's target is in the group's configured
storage list — which is a weak slice of (C2) and none of the other four. Check 3 as built
compares `after_spread` (the `8f237ff` fix, an improvement on its own terms) but drops both
promises the plan still makes around it: "the MILP objective is `≤` the heuristic's" and "both
MILP backends agree to within the §5.5 tolerance" — no cbc-vs-cpsat comparison exists anywhere.

The pragmatic defence — the replayed pipeline enforces these properties internally, so a
completing plan already satisfies them — is true and is presumably why nothing caught the gap,
but it is the wrong shape for a check whose value is catching the *engine's own* drift: an
`order_moves()` that stopped checking the transient invariant would still produce plans, and
`validate_corpus.py` would still pass, on every bundle, forever. That is the AGENTS.md §6
higher-bar class of invariant, and the corpus was sold as the place real data checks it.

**Recommendation:** most of the data is already in `plan --json`'s report — each move entry
carries `size_bytes`, `duration_mirror_seconds`/`duration_wipe_seconds`, `exceeds_max_duration`
and the per-move cost, and the `payback` block carries the rejections and deferrals, so the §7.3
duration/saturation assertions are reconstructible from what the corpus already records per
variant; Σ r_s and §8.1's per-step transient walk need the *order*, and the objective-recompute
needs the breakdown, which today only `explain --json` emits — either sweep that too (the corpus
already runs the identical pipeline) or add the two fields to `plan --json`'s group report. Also
add the cbc-vs-cpsat `after_spread` agreement check (the §5.5 tolerance only matters for the
objective, which either path then provides). If some assertions are deliberately out of scope,
say so in §16.6 the way it already says so for pattern expansion ("a real and deliberate gap
named here rather than discovered later").

### 29.10 X-08 — three §16 bundle promises that were never built (Low)

**Files:** `collect.py:1268-1270, 1379-1436`; plan §16.1, §16.3

- **The `extra_selector` manifest flag.** §16.3: "`metrics.extra_selector` is rewritten, not
  carried ... the collector replaces it with the equivalent anonymized node alternation ... and
  **the manifest flags that it did**. A bundle from a cluster whose selector does something the
  default tier cannot express is therefore not byte-faithful to its live queries, and says so in
  the manifest instead of quietly producing a plan from differently-scoped data." The built
  `config.yaml` sets `extra_selector: null` — functionally the right outcome (the default tier
  then builds the node alternation from the replayed node list, and the query keys line up) — but
  the manifest carries no flag, so the one honesty signal the plan promises for a
  non-node-shaped original selector ("`cluster="prod"`", "`customer="acme"`") does not exist.
  An author has no way to tell a bundle whose live queries were scoped differently from one whose
  were not.
- **PVE and Prometheus version strings.** §16.1's manifest line ("schema, versions, what was
  captured, what failed, counts") and §16.3's preserved list both include them; nothing in the
  bundle carries either (the manifest's only version is `generated_by`). They live in
  `submission.yaml` on the corpus side — which §16.6 does specify — but a bundle sent to the
  author without a submission file carries no version information at all, and §16.3's claim
  about the bundle itself is simply untrue as built.
- **Metric-name canonicalization.** §16.3's per-kind table maps "Metric name" to "canonical
  `drs_rd_operations`, `drs_wr_bytes`, ..."; the build carries the operator's configured names
  verbatim everywhere (config, query text, `label_values` captures) — self-consistent, leak-free
  (the names are the operator's own config, already in `config.yaml`), and arguably better than
  the table, but the table describes a mapping that does not exist.

**Recommendation:** either build the three (the manifest flag is one line in
`_anonymized_config_dict`'s caller plus one manifest key; the version strings are two extra
captured calls — `GET /version` and `/api/v1/status/buildinfo` — both already in the spirit of
the superset capture) or correct §16.1/§16.3 the way the plan already corrects itself elsewhere
("as built" notes). What should not stand is a §16 that reads as a description of the shipped
bundle format while the bundle format silently differs in three places.

### 29.11 X-09 — anonymization small print (Info)

Three independent observations, none worth a finding on its own:

- **32-bit pseudonym truncation has no collision handling outside vmids.** `pseudonym()` returns
  8 hex chars; only `register_vmids()` probes on collision (it needs to — its range is 899,900).
  Two storages (or nodes, or groups) hashing to the same 8 hex would silently merge in the
  bundle: same `storage-content/<node>/<stor>.json` filename, same `groups[].storages[].id`,
  a topology with one storage where the cluster had two. At ~n²/2³³ this is negligible for real
  cluster sizes and would fail visibly at replay (impossible sizes) rather than quietly — but a
  `Mapper.__post_init__`-time collision check across the registered sets costs three lines and
  turns "negligible" into "impossible".
- **`counts.dropped_records` undercounts.** §16.3: "it drops the containing record, logs a
  warning and **counts it in the manifest**." `Mapper.vmid()`/`volume_id()`/`upid()` increment
  `dropped_records`, but `_anonymize_disk_value()`'s unknown-storage `None` (a whole disk
  reference dropped from a VM config), `_anonymize_vm_config()`'s dropped disk values, the
  unknown-node entries pruned from storage-definition `nodes` fields, and
  `_anonymize_storage_resources()`'/`_anonymize_vm_resources()`' `continue`s never do. The number
  in the manifest is a lower bound presented as a count.
- **`--estimate`'s query count understates HTTP requests at the default range.** §16.2's own
  formula ("the query count is `6 · |groups| · (1 range + 3 instant) + 3 label_values`") treats a
  7 d range as one query; the same section's day-sized chunking means the collector issues
  ≈7 range *requests* per (group, metric) at the defaults, plus `verify-metrics`' own extra
  instant queries and `label_values("__name__")`. The printed "estimated Prometheus queries" is
  therefore ~5-7× below the request count an operator taxing a busy Prometheus actually cares
  about, while the sample-point estimate (the one the refusal threshold uses) is exact.

### 29.12 X-10 — assorted rough edges (Info)

- **`--replay` a tarball.** The transport form a bundle actually arrives in (`.tar.gz`, per
  §16.1) is not the form `--replay` takes: `load_manifest()` reports "not a bundle directory (no
  manifest.json)" with no hint to unpack, and manual 26 never says to. One sentence in the manual
  and one clause in the error close it.
- **`explain`'s "no moves made: the objective is lowest at the current assignment"** is an
  inference, not a verified fact: it is printed whenever the *final* assignment equals the seed,
  which also happens when `order_moves()` staged away every proposed move (total deadlock) — in
  that case the objective was *not* lowest at the current assignment, and the line misattributes
  the scheduler's decision to the solver. Cheap guard: only print the "objective is lowest"
  wording when `solve_outcome`'s own breakdown equals the baseline, else name the staging.
- **`validate_corpus.py`'s skip reason lies in the narrow sweep**: without `--full-matrix`, cpsat
  is recorded as `"cpsat not installed"` on machines where it *is* installed (it is merely not
  being swept) — and that string is what the committed `expected.json` files carry. "not swept
  without --full-matrix" would be true in both cases.
- **`run_started` (and a `mode_override` WARNING) precede the replay-mode refusal**:
  `_start_logging_and_announce_run()` runs before `main()` checks `--replay ... --mode auto` and
  exits 2 — verified live: `--replay <bundle> --mode auto plan` prints a `mode_override` WARNING
  record to stderr (visible at the default level, since it "escalates") and then refuses to
  start the run it just announced an escalation for. Cosmetic, but backwards: the refusal should
  come first.

### 29.13 What this pass confirms

- **The §16 architecture is the right shape, built to the project's standards.** The pure/IO
  split the plan mandates holds (`anonymize.py` has no I/O beyond the two salt helpers; the
  collector's recording clients are the only network touch); the allowlist constants are one
  implementation shared by collector and audit so they cannot drift *where the audit uses them*;
  the pseudonym construction (kind-separated HMAC, per-host salt, fingerprint instead of salt,
  `machine-id` explicitly rejected) matches §16.3's cryptanalysis; vmid probing is
  order-independent by construction and tested for it; and the unmapped-means-dropped rule is
  followed everywhere it was written down (X-01's `exclude.disks` is the one place the rule was
  specified and not applied).
- **The replay design earns its safety claims.** Both replay clients are real subclasses of the
  clients they replace, with inert transports and a `_NeverSession` whose `get` raises;
  `move_disk`/`task_status` refuse in the clients *and* `apply`/escalated `--mode` are refused in
  `main()` *and* collect-testdata refuses `--mode confirm|auto` — three independent layers, each
  unit-tested, including tests that assert no `requests.Session` is ever constructed on the
  replay path. A key miss is a loud, named `BundleError` quoting the query and range (§16.5), and
  the superset-then-trim range design is the right answer to the forecaster-matrix problem.
- **The eight live-capture fixes are the process working.** Every one is a real bug found by the
  first capture against a real cluster, fixed with a regression test reproducing it, and each fix
  is in the direction of failing closed (a device label that is not a device key is dropped; a
  metric name is never validated as one; the node selector is rebuilt independently rather than
  text-substituted, precisely because sorting real names and pseudonyms can disagree — the kind
  of reasoning this review has been endorsing since F-23).
- **Phase 11's logging policy is built and tested at the policy level, not just the formatter
  level** — the exact gap §2.3 opens by describing. The clean-run-silence, the unasked-for audit
  trail on `apply --mode confirm|auto`, `--quiet`'s documented cost, `--log-format auto`'s
  TTY/pipe split, the `-v`/`-vv` third-party boundary, stream separation under `--json`, the
  one-fact-one-line error rule, and the ast-walk test that makes the event catalogue an
  interface are all present as tests. `json_safe()` closes a real RFC 8259 defect (a `+inf`
  payback ratio on every no-move ACT run) in both output channels at once, with
  `allow_nan=False` as the tripwire against regression.
- **The corpus gate is wired where the plan says**: `make check` runs scrub + invariants +
  MILP-vs-heuristic + regression `--check` over the committed bundles (passing on this tree), the
  full matrix is `make corpus`'s own target with `DRS_CORPUS_DIR` for outsized bundles, an empty
  corpus is a clean pass, and the submission-file requirement is enforced (an unattributed
  directory fails). Both committed bundles are under the 8 MiB ceiling, carry submission files
  with honest `what_this_reproduces` prose (including naming the bugs they found), and — the
  detail that makes the corpus credible — the 7-day bundle's own commit history shows it
  immediately falsifying the `check_milp_vs_heuristic` move-count proxy and getting the
  after_spread comparison in return.
- **The documentation range is unusually self-critical**: the quickstart marks its own
  data-moving steps and says out loud that no repository and no timer unit exist; the new
  metrics-pipeline page documents the InfluxDB-line-protocol-to-Prometheus type trap that
  §3.3's cross-metric check exists for, names the tested backend, and marks the OTel path
  untested; and the manpage's hand-maintained option list — the exact defect class
  `.agents/documentation.md` forbids — was discharged into the coverage test.

### 29.14 Assessment

This range adds the first genuinely new *subsystem* since the engine was finished, plus its own
specification (§16, written first), its own test corpus discipline, a re-planned and implemented
logging policy, and a documentation push that reads like the dogfooding it came from. The
engineering quality holds at the standard the last five passes established: allowlist-not-denylist
with a shared implementation, fail-closed on every unmapped value, deterministic writers asserted
by running the collector twice, replay safety in three independently-tested layers, and eight
incident fixes each landing with the test that reproduces the incident.

The four Medium findings are all in the new subsystem's *boundary* — the places where the bundle
meets an operator who configured something (X-01), where the cluster fails mid-capture (X-02),
where the audit's claims meet its coverage (X-03), and where the release notes meet the code
(X-04). Three of the four are the same shape at heart: a privacy control whose *written* contract
is stronger than its *enforced* one. §16.3's governing rule names the right principle — "a field
reaches the bundle only if `anonymize.py` names it" — and X-01/X-02/X-03 are each a channel that
rule was not extended to cover (a config list, an exception string, the audit's own scope). The
fixes are small and local: one dict comprehension, one scrub step, one allowlist wiring, one
changelog edit. Fix those four and the first bundle a stranger sends is as safe as §16.3 says it
is; fix X-07's missing assertions too and the corpus checks what the plan has been promising it
checks all along.

---

## 30. Resolution of fifteenth-pass findings (X-01..X-10)

All ten findings were real. Nine are fixed outright; X-07 is fixed where it could be fixed safely
and the rest of its promise is retracted, with the reason stated, rather than left standing as an
unbacked claim or shipped as a check that would have been flaky on the first real bundle to
exercise it.

| ID | Status | How resolved |
|----|--------|--------------|
| X-01 | Resolved | New `collect._anonymize_exclude_disk_key()` maps the vmid component of an `exclude.disks` entry through `mapper.vmid()` (device passes through unchanged), dropping an entry whose vmid was never registered — the same shape `exclude.vmids` already had. `_anonymized_config_dict()`'s `"disks"` list uses it instead of carrying `exclude.disks` verbatim. |
| X-02 | Resolved | `collect._redact_free_text()` strips `https?://…` and `host='…'` fragments (replacing the latter with `host='<redacted>'`) before the existing vmid/node/storage substitution — the channel a transport failure's own exception text used to leak an endpoint hostname through. The scrub audit's public-suffix pattern gained `.internal`/`.corp`/`.lan`/`.home`/`.example`/`.test` (the four it had missed `.example`/`.internal`/`.corp` demonstrated live in 29.1) plus a dedicated `host='...'` literal check as a second, independent backstop. |
| X-03 | Resolved | The scrub audit's key allowlist, previously wired to five top-level `pve/` files only, now covers `vm-config/` (via a new `extra_key_ok` predicate parameter to `_scrub_json_file()`, permitting `topology.DISK_KEY_RE`-matched keys alongside `VM_CONFIG_EXTRA_FIELDS`), `vm-snapshots/`, `vm-status-current/`, `storage-status/`, `storage-content/`, and every `prometheus/instant|range|label-values` file (new `_scrub_prometheus_dir()`: fixed top-level keys per query kind, plus each series' `metric` dict checked against the bundle's own configured label names read from `config.yaml`). `manifest.json`/`findings.json` are documented as governed by `_redact_free_text()` instead of a key allowlist (they are hand-authored bundle metadata, not a captured PVE/Prometheus object shape) rather than silently left unclaimed. |
| X-04 | Resolved | `debian/changelog`'s unreleased 0.1.1 entry rewritten: the cluster-scoping bullet and the removed-behaviour half of the W-fixes bullet are gone (W-07's `no_series_matched` reporting, which survived section 27's removal, is kept); new bullets added for `collect-testdata`/`--replay`/`support{}`, the corpus, the phase 11 logging policy, `json_safe()`, the cross-metric consistency check, `explain`'s rejected-alternative section, and the quickstart/metrics-pipeline documentation. |
| X-05 | Resolved | `cli._handle_collect_testdata()` restructured: the bare, unrecorded `build_topology()` call now runs only inside the `--estimate` branch (where a topology is unavoidably needed to size the capture); the ordinary capture path no longer builds one before `collect.capture_bundle()` builds its own, recorded one — one PVE read pass per invocation, not two, as §16.2 states. Manual 26's `--estimate` row and prose corrected to say what it actually reads (the full PVE inventory; Prometheus only is skipped). |
| X-06 | Resolved | §2.3's "Where the handler is attached" rewritten as an "As built" note describing the real design (one handler on root; the package logger carries the level; the caplog/embedding rationale) instead of a stale instruction the code never followed. `logging_setup.configure_logging()` changed so the mandatory `INFO` floor for `apply --mode confirm/auto` is no longer escaped by an explicit `--log-level` below it — `--quiet` is now the *only* documented escape, matching what §2.3 already said elsewhere; `--log-level`'s CLI help, the manpage entry and manual 35 updated to state the interaction. |
| X-07 | Partially resolved, rest retracted with reason stated | `check_invariants()` gained two of the promised assertions, reconstructed from data `plan --json` already carries: no accepted move may carry `exceeds_max_duration: true` (§7.3's duration rule), and payback's own `rejected_moves`/`deferred_moves` must never overlap the accepted `moves` (§7.3's saturation guard, structurally). `Σ r_s = 0`, §8.1's per-step transient predicate and the objective-recompute equality remain unchecked — they need the emitted order or the five-term breakdown, which today only `explain --json` emits — and §16.6/the module docstring now say so explicitly instead of implying they run. A first attempt at the MILP-vs-MILP agreement check (comparing `after_spread` against `solver.mip_gap` as a relative tolerance) was built, run against the committed corpus under `--full-matrix`, and **found to be wrong**: it flagged real, legitimate cbc/cpsat disagreement (`mip_gap` bounds the five-term objective, not one derived metric in isolation) as a violation. It was removed rather than shipped, and §16.6/the source both now name this as the same objective-breakdown gap, with the false-positive numbers that falsified the naive approach recorded so the next attempt does not repeat it. |
| X-08 | Resolved | The manifest gained `capture.extra_selector_rewritten` (set whenever `metrics.extra_selector` was configured — the honesty signal §16.3 promised but never emitted) and `capture.pve_version`/`capture.prometheus_version` (new `PveClient.version()`/`RecordingPveClient.version()`, `PrometheusClient.buildinfo()`, both `None` on a failed call, neither an identifier so neither needs anonymization). §16.3's per-kind table corrected for metric-name canonicalization: the built behaviour (verbatim, self-consistent, leak-free) is now documented as-built rather than as a `drs_*` mapping that was never implemented — building that mapping instead would have made the bundle worse, per the pass's own assessment. |
| X-09 | Resolved | `Mapper.__post_init__()` now calls a new `_check_no_pseudonym_collision()` over `known_nodes`/`known_storages`, raising `BundleError` on a same-kind collision instead of silently merging two bundle records (vmid collisions were already impossible by construction). `dropped_records` now also counts: `_anonymize_disk_value()`'s unknown-storage drop, an unknown node pruned from a storage definition's `nodes` list, and the unknown-node `continue`s in `_anonymize_storage_resources()`/`_anonymize_vm_resources()` (malformed-API-shape `continue`s, not identifier drops, are deliberately left uncounted). `estimate_capture()`'s `query_count` now multiplies the range-query term by the day-sized chunk count instead of treating a multi-day range as one query, and both the manual's worked example and §16.2's own formula were recomputed to match. |
| X-10 | Resolved | `replay.load_manifest()` now names `tar -xzf` when the given path ends `.tar.gz`/`.tgz`; manual 26 states the bundle directory (not the tarball) is what `--replay` takes. `cli._render_no_moves_lines()` only prints "the objective is lowest at the current assignment" when `schedule_result.deadlocked` is empty; a total-deadlock case now names the staging failure instead. `validate_corpus.py`'s narrow (non-`--full-matrix`) sweep distinguishes "not installed" from "not swept without --full-matrix" by checking `_available_backends()` independently of which backends the narrow sweep actually runs. `cli.main()`'s `--replay ... --mode auto <cmd>` refusal moved before `_start_logging_and_announce_run()`/`apply_mode_override()`, so nothing is logged before a run that will not start. |

New/updated regression tests: `test_capture_bundle_config_yaml_maps_exclude_disks_vmid`,
`test_capture_bundle_manifest_scrubs_a_transport_failures_own_hostname`,
`test_capture_bundle_manifest_flags_an_extra_selector_rewrite`,
`test_capture_bundle_manifest_carries_pve_and_prometheus_versions` (+ the failed-call case),
`test_estimate_capture_query_count_accounts_for_day_chunking`,
`test_anonymize_storage_definitions_counts_a_pruned_unknown_node` and three siblings for the other
`dropped_records` gaps (`test_collect.py`); `test_node_pseudonym_collision_is_refused` and
`test_storage_pseudonym_collision_is_refused` (`test_anonymize.py`); `test_version`/
`test_version_missing_key_is_none` (`test_pve.py`), `test_buildinfo_returns_the_version_string`/
`test_buildinfo_missing_key_is_none` (`test_metrics.py`);
`test_handle_collect_testdata_actual_capture_does_not_repeat_the_topology_pass` (`test_cli.py`);
`test_explicit_log_level_below_the_floor_does_not_escape_it`/
`test_explicit_log_level_above_the_floor_still_works` (`test_logging_setup.py`);
`test_render_group_explain_human_names_a_total_deadlock_not_the_objective`,
`test_main_replay_mode_auto_refusal_precedes_the_run_announcement` (`test_cli.py`);
`test_load_manifest_names_the_tarball_still_needs_unpacking` (`test_replay.py`); a new
`tests/unit/test_validate_corpus.py` (skipped outside a full checkout, matching
`test_documentation.py`'s own pattern) pinning the X-02/X-03 scrub-audit wiring directly, since
`tests/corpus/validate_corpus.py` is exercised end-to-end but had no unit tests of its own before
this pass.

Verification: dev venv `python3 -m pytest` — **832 passed**, **96.19% line coverage** (the new
`collect.py`/`replay.py` branches added by this pass keep both modules above the aggregate floor;
no per-module floor exists, noted since the fourteenth pass). `make check` clean end to end: fmt,
lint, typecheck (`mypy src tests tools` — the X-01..X-10 fixes surfaced four pre-existing
implicit-reexport gaps in test code reaching through a module's own re-imported names, e.g.
`cli.collect.X`/`vc.anonymize.X`; fixed by importing each name directly rather than chaining
through it), test-with-coverage, fixtures, corpus-check (scrub audit + invariants +
MILP-vs-heuristic + regression `--check`, both committed bundles, passing — including under
`--full-matrix`, which is what surfaced and then falsified the MILP-vs-MILP attempt above), and
docs-check (`IMPLEMENTATION_PLAN.pdf` rebuilt to 59 pages, the manual PDF to 46, the manpage
regenerated; `docs/internals/*` unchanged, since nothing this pass touched was already documented
incorrectly there).

---

## 31. Sixteenth-pass review — verification of the X-01..X-10 fixes

Reviewed commit range `b107c19..81df865`: one non-merge commit (`cd497ae`, merged as `81df865`),
≈1,130 lines of code and tests plus section 30's own 562-line resolution record, across 29 files
(`collect.py` +141, `validate_corpus.py` +244, `cli.py` +104, `anonymize.py`/`logging_setup.py`/
`pve.py`/`metrics.py`/`replay.py` touched, six test files grown, one new
`tests/unit/test_validate_corpus.py`, the plan, the changelog, manual 26/35, the manpage source
and both PDF stamps).

### 31.1 Verification run

- Dev venv `python3 -m pytest`: **832 passed, 1 warning** (the same benign statsmodels
  `ConvergenceWarning`), **96.19% line coverage** — exactly what section 30 reports. `make check`
  clean end to end (fmt, lint, typecheck over `src tests tools` in the unchanged
  `.venv-typecheck/`, test-with-coverage, fixtures, corpus-check over both committed bundles,
  docs-check). The full-matrix corpus run section 30 used to falsify its MILP-vs-MILP attempt
  was **not** re-run here (~108 variant plans, tens of minutes); the narrow corpus gate is green
  on this tree.
- **Every reproduction from the fifteenth pass was re-run against the fix, not inferred**:
  - X-01: `"101:scsi1"` through `_anonymize_exclude_disk_key()` → `<pseudonym>:scsi1`; an
    unregistered vmid and a malformed entry both drop (`None`, counted).
  - X-02: the pass-15 exception string (`host='pve01.corp.example'`, a `.corp` domain) comes out
    of `_redact_free_text()` as `host='<redacted>'` with the URL stripped, and the old
    eight-pattern battery — which passed it before; section 29's own "nine value checks" was a
    miscount, the ninth pattern is the one this fix adds — now flags the *unredacted* form via
    both the extended suffix list and the new `host='…'` literal.
  - X-06: `configure_logging(floor=INFO, log_level="error")` leaves the package logger at INFO;
    `--quiet` still escapes to ERROR; `debug` (above the floor) still wins.
  - X-10: `--replay <bundle> --mode auto plan` attaches a capturing handler to root, runs `main()`,
    and exits 2 with **zero** log records — the refusal now precedes the announcement (verified
    live; the fifteenth pass's same probe printed a `mode_override` WARNING first).
  - X-05: `test_handle_collect_testdata_actual_capture_does_not_repeat_the_topology_pass` pins
    `build_topology` to zero calls on the capture path (the recording client's own pass runs inside
    `capture_bundle()`); `--estimate` keeps its one bare pass, and manual 26 now says so honestly.
- The three invariant assertions X-07 added are visible in the code and pinned by
  `tests/unit/test_validate_corpus.py`; §16.6's rewritten check 2/3 text matches what
  `check_invariants()` actually does, and the falsified MILP-vs-MILP attempt is documented in both
  the plan and a source comment with the numbers that killed it — the right way to record a
  negative result.
- The ten findings' status, one line each: **X-01 fixed** (vmid mapped, device kept, drops
  counted), **X-02 fixed** (strip-then-substitute in `_redact_free_text`, plus two new audit
  patterns — but see Y-01), **X-03 fixed** (per-file allowlists wired for all of `pve/`, Prometheus
  top-level keys and `metric` label sets checked against the bundle's own configured labels,
  manifest/findings honestly re-scoped to value-patterns-plus-redaction), **X-04 fixed** (the
  0.1.1 entry now describes what ships, including an honest account of the cluster-label
  add-and-remove), **X-05 fixed**, **X-06 fixed** (plan rewritten as-built; floor clamped; help,
  manpage and manual all state the interaction), **X-07 partially fixed with the remainder
  retracted and the reason stated** — the correct resolution shape for a check that would have
  been flaky, **X-08 fixed** (manifest flag + both version calls; the metric-name table row now
  documents the verbatim behaviour), **X-09 fixed** (collision refusal, drop counting, chunk-aware
  estimate), **X-10 fixed** (tarball hint, deadlock-aware wording, honest skip reasons — but see
  Y-02, environmental dependence, and Y-03's stale neighbour figure).

### 31.2 Findings summary

| ID | Severity | Module(s) | Summary |
|----|----------|-----------|---------|
| Y-01 | Low | `collect.py`, `tests/corpus/validate_corpus.py` | The two halves of X-02's fix contradict each other in composition: the audit's new `_TRANSPORT_HOST_LITERAL_RE` flags every `host='…'` literal — including the collector's own `host='<redacted>'` sentinel — so a bundle whose capture hit a transport failure (redacted correctly, exactly as X-02's fix provides) fails the scrub audit with "value looks like unredacted transport host" (reproduced end to end: capture → write → `scrub_audit()` → 1 violation). The first real-world bundle with a connection blip mid-capture can never pass `make check`'s corpus gate |
| Y-02 | Low | `tests/corpus/validate_corpus.py`, committed `*.expected.json` | The skip-reason fix makes the committed expected files environment-dependent: they record `"not swept without --full-matrix"` because they were generated with `ortools` importable, and on a solver-less environment the same `--check` now computes `"cpsat not installed"` and **exits 1 "stale"** (reproduced on the system toolchain: pulp 2.7.0, no ortools). The old always-"not installed" label was inaccurate but stable across environments; the accurate one flips with the venv. `make check` masks this only because its `test` target installs the solver extras before `corpus-check` runs |
| Y-03 | Low | `docs/manual/26-collect-testdata-and-replay.md` | The corrected worked example fixed one line and left its neighbour stale: `estimated Prometheus queries: 117` now derives exactly (18 + 2·6·8 + 3), but the untouched `estimated series sample points: 573104` does not — the example's own inputs (`disks: 47`, `range: 7d`, `step: 5m`) give 47·6·2016 = **568,512**. The V-03 family again: a figure nobody re-derived when the block was edited |
| Y-04 | Info | plan §16.6 (check 4) | The regression bullet still says `<name>.expected.json` "records, per variant, the gate verdict, the plan …, **the order, the objective breakdown**, the payback arithmetic and the findings" — `plan --json`'s group report carries neither an order field nor the objective breakdown (the exact gap X-07's own fix documents for checks 2 and 3), so the expected files cannot contain them. The honesty sweep fixed the sibling bullets and skipped this one |
| Y-05 | Info | `collect.py`/`cli.py`, plan §16.2 | §16.2's "the collector **prints the estimate and the query count before it fetches anything**" remains unimplemented on the real-capture path: only `--estimate` prints; a full capture computes the estimate internally (for the refusal check) and proceeds silently. Pre-existing since phase 10, but the fix range edited the formula in the very sentence above it and left the print promise standing |
| Y-06 | Info | `collect.py` | The manifest's new `capture.pve_version`/`prometheus_version` are run through `_redact_free_text()`, whose registered-vmid substitution rewrites whole digit runs anywhere in the text: with vmid 11 registered, `"pve-manager/9.2.11"` becomes `"pve-manager/9.2.<pseudonym>"` (verified). Safe direction (no leak), but the provenance field X-08 added can silently carry a wrong version; version strings are not free text and should skip the vmid pass |
| Y-07 | Info | `debian/changelog` | The rewritten 0.1.1 W-fixes bullet opens "Plus **five** documentation-residue fixes that still apply:" and lists four (changelog phase mislabelling, topology stage count/dead name, warnings paragraph, call-count formula). W-01's status-page parenthetical — the fifth, still applied — is unnamed; either the count or the list is off by one |

### 31.3 Y-01 — the audit flags the collector's own redaction sentinel

**Severity:** Low
**Files:** `src/proxmox_storage_drs/collect.py` (`_TRANSPORT_HOST_RE`), `tests/corpus/
validate_corpus.py` (`_TRANSPORT_HOST_LITERAL_RE`), `tests/unit/test_collect.py`
(`test_capture_bundle_manifest_scrubs_a_transport_failures_own_hostname`),
`tests/unit/test_validate_corpus.py` (`test_check_value_patterns_flags_an_unredacted_transport_
host_literal`)

X-02's fix has two halves. The collector half replaces `host='[^']*'` with the literal
`host='<redacted>'` (and `https?://\S+` with `<url-redacted>`). The audit half adds
`_TRANSPORT_HOST_LITERAL_RE = host='[^']*'` as a backstop "for exactly that regression". Composed,
the backstop matches the sentinel: `[^']*` happily matches `<redacted>`. Reproduced end to end
(a `capture_bundle()` run with one scripted transport failure, written with `write_bundle_dir()`
and put through the real `scrub_audit()`), it reports

```
manifest.json#...calls[67].detail: value looks like unredacted transport host:
"cluster/tasks: request failed: HTTPSConnectionPool(host='<re..."
```

— a violation against the *correctly redacted* value. The two regression tests each pin their own
half in isolation (the collector test asserts the sentinel *appears*; the audit test asserts a
real hostname is flagged) and neither composes them, which is exactly how the contradiction
survived: this is AGENTS.md §3's "a test that executes a line without asserting anything about
the composition" — or rather, two such tests whose composition nobody ran.

The direction of failure is safe (fail-closed: a false positive, not a miss), which is why this
is Low. But the first submitted bundle whose capture hit a connection blip — the precise
population X-02 was about — now cannot pass the corpus gate until someone edits the audit, and a
false "unredacted" accusation against a correctly-redacted bundle trains exactly the
alarm-fatigue §2.3's level policy argues against.

**Recommendation:** make the backstop skip its own sentinel — `host='(?!<redacted>')[^']*'` (and
decide whether `<url-redacted>` needs the same treatment for any future URL-shaped pattern) — and
add the missing composition test: build the pass-15 failure bundle, run `scrub_audit()` on it,
assert **zero** violations. That test is the one that would have caught this.

### 31.4 Y-02 — the expected files now encode one environment's solver set

**Severity:** Low
**Files:** `tests/corpus/validate_corpus.py` (`run_variant_matrix`), `tests/corpus/
bzed-dev-cluster-{24h,7d-holt-winters}.expected.json`

Before the fix, a cpsat skipped variant was always labelled `"cpsat not installed"` — wrong on an
ortools machine (X-10's point) but *identical* in every environment, so the committed expected
files were stable. After the fix the label is accurate and environment-dependent, and the
committed files (regenerated on an ortools machine) pin `"not swept without --full-matrix"`.
Reproduced: on this host's system toolchain (pulp 2.7.0, no ortools — the exact shape of a fresh
Debian checkout without the solver extras), `python3 tests/corpus/validate_corpus.py --check`
reports both committed files **stale** and exits 1. Consequences:

- `make corpus-check` standalone on a solver-less venv fails with a misleading message ("stale,
  re-run without --check") that names no environment cause;
- regenerating in that environment commits `"cpsat not installed"` — which then makes `make check`
  (whose `test` target installs the extras first) fail in the *other* direction. The committed
  answer flip-flops with whichever venv last regenerated it;
- the Makefile's own "loud-not-swallowed solver install" warning exists because solver installs
  fail; a failed extras install followed by `make check` now dies at corpus-check instead of at
  the tests that needed the solver.

**Recommendation:** the narrow sweep's skip reason should be a property of the *sweep*, not of the
machine: record `"not swept without --full-matrix"` unconditionally in the narrow mode (it is
true on every machine — cpsat is not being swept), and let `"not installed"` appear only in
`--full-matrix` runs, where availability genuinely determines the row. Alternatively (heavier):
pin availability in the expected file per environment the way CI does. The one-line fix restores
the old cross-environment stability while keeping the accurate label where it is accurate.

### 31.5 Y-03 — the corrected example's neighbour figure does not derive

**Severity:** Low
**Files:** `docs/manual/26-collect-testdata-and-replay.md` (`--estimate` worked example)

The fix corrected the query-count line (42 → 117, which now derives exactly from
`3·6 + |groups|·6·(1 + ⌈7d/1d⌉) + 3` with the example's `groups: 2`) and recomputed §16.2's
formula — but the block's `estimated series sample points: 573104` was left untouched, and it
does not derive from the example's own printed inputs: 47 disks × 6 metrics × (604800/300 = 2016
points) = **568,512**. The manual even gained a new paragraph in this same edit explaining how
the query count is computed — the sample-points line directly below it was still not re-derived.
This is V-03's family (two stale `used` figures in `29-explain.md`'s worked example) a third
time, and the same structural cure applies: worked examples that are executable assertions (or
at least generated), not hand-maintained prose numbers.

**Recommendation:** correct the figure (568,512), and when doing so check the neighbouring
`disks: 47`/`range: 7d`/`step: 5m` triple is the intended one. The V-03 recommendation — build
the example's exact inputs and assert the rendered output — retires the whole class and is
cheaper here than anywhere else (the example *is* one call to `--estimate`).

### 31.6 Y-07 — "five" fixes, four listed (Info)

The rewritten 0.1.1 bullet: "Plus five documentation-residue fixes that still apply: changelog
phase mislabelling, a stale topology stage count and dead function name, the operator manual's
warnings paragraph (now covers all four size-resolution warnings), and the read-path call-count
formula (W-01..W-05)." Four items are named; the fifth (W-01's "`auto` not yet" parenthetical on
the status page — applied, still in place) is not. One word either way ("four", or name the
fifth). Recorded because this entry was *just* rewritten for X-04 specifically to stop
misdescribing its own range.

### 31.7 Y-04, Y-05, Y-06 — three small plan/manual drifts left inside the fixed paragraphs (Info)

- **Y-04, §16.6 check 4.** The X-07 fix rewrote checks 1-3 with honest as-built scope and named
  their gaps — and left check 4 claiming the expected files record "the order, the objective
  breakdown" alongside the plan and payback arithmetic. `plan --json`'s group report carries
  neither (no `order` field; the five-term breakdown is `explain`-only — the very gap check 2
  now names), so no expected file can contain them. One clause ("as built: the gate verdict, the
  plan with per-move costs, the payback arithmetic and the findings") brings the fourth bullet
  up to the honesty standard the fix established for the other three.
- **Y-05, §16.2's estimate-print bullet.** "The collector **prints** the estimate and the query
  count **before it fetches anything**" — on the real-capture path nothing is printed; the
  estimate is computed internally for the refusal check only, and the operator sees output after
  the fetch completes. Only `--estimate` prints. Either print the estimate (and the refusal
  headroom) at the top of every capture — arguably what §16.2 always wanted, and it costs one
  line now that the estimate rides the same topology pass — or soften the plan's "prints" to
  "computes and enforces". Pre-existing since phase 10, but this fix range edited the formula in
  the sentence directly above it.
- **Y-06, version strings through the vmid redactor.** `_build_manifest` runs the new
  `pve_version`/`prometheus_version` through `_redact_free_text()`, whose registered-vmid
  substitution matches *any* whole digit run: with vmid 11 registered, `pve-manager/9.2.11`
  renders as `pve-manager/9.2.272705` (verified). No leak — the wrong direction to be unsafe —
  but the field X-08 added for honest provenance can silently lie about the version. Version
  strings are not operator free text; passing them to the vmid pass buys nothing (they contain no
  vmids) and risks this. Either skip `_redact_free_text` for these two fields (they are
  machine-generated version strings, not free text — the same reasoning the metric-name row now
  uses for carrying config names verbatim) or document the mangling.

### 31.8 What this pass confirms

- **All ten X-findings are genuinely fixed, and fixed the way section 30 claims** — every fix was
  verified against the code *and* by re-running the fifteenth pass's reproductions, not by
  reading the resolution table. The fixes follow the house style: the vmid mapping for
  `exclude.disks` reuses the exact `exclude.vmids` shape; the transport redaction runs before
  substitution so nothing shaped like a connection target survives; the per-file allowlists are
  the *same constants* the collector filters with (so the two still cannot drift), including the
  `extra_key_ok` escape hatch that reuses `anonymize.DISK_KEY_RE` rather than a second regex; and
  the dropped-records counter now counts every identifier drop the plan's sentence covers.
- **X-07's resolution is the best kind of partial fix.** The two added assertions are
  reconstructed from data the corpus already records (no new report fields needed); the MILP-vs-
  MILP attempt was built, *run against the real committed corpus*, found to produce legitimate-
  disagreement false positives, removed, and documented with the falsifying numbers in both the
  plan and the source — a negative result recorded so the next person does not rebuild it. The
  remaining three invariant properties are named as unbuilt in §16.6 itself rather than left as
  implied promises. This is exactly what "resolve or refute, and say which" should look like.
- **X-04's changelog rewrite is honest in both directions**: it no longer advises configuring the
  removed `metrics.labels.cluster` key, and it now *describes the add-and-remove* ("added on this
  pass's own mistaken assumption … removed again in full") rather than silently omitting it —
  turning the W-02/X-04 defect class into a one-sentence history the release notes can carry.
- **The logging-floor fix chose the right direction**: the mandatory audit trail now yields only
  to `--quiet`, exactly as plan, manual, manpage and `--help` all now say in one voice (verified
  behaviourally at all three corners: below-floor clamped, `--quiet` escapes, above-floor wins).
  The §2.3 handler-placement rewrite describes the built mechanism with its rationale instead of
  prescribing the opposite — the AGENTS.md §7.6 debt paid in full.
- **The scrub-audit extension is structurally sound**: value-pattern checks still run over
  everything; the key allowlists apply where a captured object shape exists; Prometheus series
  labels are validated against the bundle's *own configured* label names (so a renamed-label
  bundle neither false-flags nor gets a pass it should not); files outside the three known
  Prometheus kinds keep the old checks rather than being skipped; and manifest/findings are
  honestly re-scoped in both the docstring and §16.6 instead of being quietly claimed. The one
  defect found in it (Y-01) is a composition false-positive, not a coverage gap.
- **The corpus-expected regeneration discipline held for the intended path** — both committed
  files were regenerated in the same commit as the skip-reason change that altered them, and
  `make check`'s default flow (extras installed by `test` before `corpus-check`) keeps the gate
  green everywhere it actually runs. Y-02 is the residual environment coupling, not a broken
  gate.

### 31.9 Assessment

The fix range is faithful: ten findings, ten real fixes (one honestly partial with the remainder
retracted and the reason recorded), each carrying its regression test, each with the plan/manual
text updated in the same commit, and both PDF stamps (plus the manpage source) kept current. The
seven new findings are all Low or Info, and five of the seven are the classic residue of fixing
a finding *around* its neighbours without re-examining them: the corrected example line beside a
stale one (Y-03), the corrected plan bullet beside an uncorrected one (Y-04, Y-05), the new
field routed through an old redactor without asking what that redactor does to it (Y-06), and
the corrected count beside an unlisted item (Y-07). The two that are not that shape are
composition defects the individual tests could not see: two halves of one fix that contradict
when run together (Y-01), and an expected-file whose new accuracy made it environment-dependent
(Y-02). Both have one-line fixes and both want the same test-shape upgrade: compose the pieces
(`scrub_audit()` over a redacted-failure bundle; `--check` under a solver-less interpreter)
rather than pinning each piece alone.

Fix Y-01 and Y-02 (both mechanical), correct the three figures/counts (Y-03, Y-07, and Y-06's
version handling), and align the two plan sentences (Y-04, Y-05) — none of it an afternoon — and
the fifteenth pass's findings are closed end to end with nothing new standing in their place.

---

## 32. Resolution of sixteenth-pass findings (Y-01..Y-07)

All seven findings were real. All seven are fixed.

| ID | Status | How resolved |
|----|--------|--------------|
| Y-01 | Resolved | `validate_corpus._TRANSPORT_HOST_LITERAL_RE` gained a negative lookahead excluding `collect.py`'s own `host='<redacted>'` sentinel (`host='(?!<redacted>')[^']*'`), so the backstop no longer flags the correctly-redacted output of the fix it exists to guard. New composition tests: `test_check_value_patterns_does_not_flag_the_collectors_own_sentinel` pins the regex directly, and `test_scrub_audit_passes_a_bundle_with_a_redacted_transport_failure` reproduces 31.3's exact end-to-end scenario (capture a transport failure → write the bundle → `scrub_audit()`) and asserts zero violations — the composition test the pass named as the one that would have caught this. |
| Y-02 | Resolved | `run_variant_matrix()`'s skip reason is now a function of `full_matrix` alone, not of `_available_backends()` in narrow mode: a narrow-sweep skip is always `"not swept without --full-matrix"` (true on every machine, since the narrow sweep hardcodes cpsat out regardless of availability); `"<backend> not installed"` is only ever computed under `--full-matrix`, where `backends == available` and the two conditions coincide exactly. The committed `expected.json` files (which already recorded the now-unconditional narrow-mode reason) needed no regeneration; verified stable across both the ortools-backed dev venv and a simulated solver-less run of the narrow sweep. |
| Y-03 | Resolved | Manual 26's stale `estimated series sample points: 573104` corrected to `568512` — `47 disks · 6 metrics · 2016 points (604800s / 300s)`, re-derived from the example's own printed inputs and matching `estimate_capture()`'s actual formula. |
| Y-04 | Resolved | §16.6 check 4's bullet no longer claims the expected files record "the order, the objective breakdown" — reworded to "the plan (as a sorted list of moves with their per-move costs), the payback arithmetic and the findings", with an explicit cross-reference to the same as-built gap checks 2 and 3 already name, instead of being the one bullet the honesty sweep skipped. |
| Y-05 | Resolved | §16.2's "the collector prints the estimate and the query count before it fetches anything" softened to describe what a real capture actually does: computes the estimate internally and enforces `support.max_series_points` against it, printing nothing before proceeding; only `--estimate` prints. No code change — the plan's claim was ahead of a real-capture feature that was never built, and printing it unconditionally was judged not worth the extra line of output on every capture for this pass; the gap is now named rather than implied away. |
| Y-06 | Resolved | `_build_manifest()`'s `pve_version`/`prometheus_version` no longer pass through `_redact_free_text()` — they are machine-generated provenance strings with no vmids, node or storage names to redact, and the vmid pass's whole-digit-run substitution could silently corrupt a real version string containing a registered vmid's digits (`pve-manager/8.2.101` → `pve-manager/8.2.<pseudonym>` with vmid 101 registered). New regression: `test_capture_bundle_manifest_version_is_not_mangled_by_vmid_redaction`. |
| Y-07 | Resolved | `debian/changelog`'s 0.1.1 entry now names all five documentation-residue fixes the `(W-01..W-05)` parenthetical already promised: the manual's stale `"auto" not yet` status-page parenthetical (W-01) is listed alongside the changelog phase mislabelling, the stale topology stage count/dead function name, the warnings paragraph and the call-count formula. |

New/updated regression tests: `test_check_value_patterns_does_not_flag_the_collectors_own_sentinel`,
`test_scrub_audit_passes_a_bundle_with_a_redacted_transport_failure` (`test_validate_corpus.py`);
`test_capture_bundle_manifest_version_is_not_mangled_by_vmid_redaction` (`test_collect.py`).

Verification: dev venv `python3 -m pytest` — **835 passed**, **96.19% line coverage** (three new
tests, no coverage regression). `make check` clean end to end: fmt, lint, typecheck
(`mypy src tests tools`), test-with-coverage, fixtures, corpus-check (both committed bundles clean
under the narrow sweep `make check` runs — including the Y-01 composition test's own live
`scrub_audit()` call, and the Y-02 fix verified to keep both committed `expected.json` files
current with no regeneration needed), and docs-check (`IMPLEMENTATION_PLAN.pdf` rebuilt to the same
59 pages, the manual PDF to the same 46, both stamps refreshed; `make man` reports nothing to do,
since `man/pve-storage-drs.1.md` was untouched by this pass). A `--full-matrix --check` run was
also attempted directly (not part of `make check`); it reports the same two committed bundles stale
for a reason predating this pass entirely (reproduced identically on the pre-fix commit `81df865`,
via `git stash`) — unrelated to Y-01..Y-07 and out of this pass's scope, consistent with section
30's own note that the full-matrix sweep was not re-run there either.

---

## 33. Seventeenth-pass review — the findings.json label-leak fix, the gigapipe step workaround, releases 0.1.2/0.1.3

Reviewed commit range `81df865..HEAD` (the Y-01..Y-07 fixes themselves are recorded in section
32 and are verified here rather than re-reviewed). Six non-merge commits: `9e80f6c` (the
Y-fixes), `46583a0` (Release 0.1.2: README AI-disclaimer section, changelog entry, version
bump), `bb9417b` (the `findings.json` label-leak fix — `_check_sample_series()`'s "info"
finding dumps a live series' entire raw label dict into free text, and a real Telegraf `host`
tag that `_redact_free_text()` cannot recognize reached a bundle; found by hand-reading the
fresh, never-committed `tests/corpus/cluster-a/` submission), `29213e8` (the gigapipe
step-vs-range workaround: two live-confirmed deployments of a recently updated gigapipe return
zero series for any range-vector function whenever the query's own step `>=` the function's
range-vector duration — exactly this project's default `metrics.step == metrics.rate_window` —
binary-searched to the second, with a second confirmed quirk forcing whole-second steps),
`b4c7de6` (Release 0.1.3), plus the subsequent removal of the untracked `cluster-a/` working
tree. This pass was specifically tasked with verifying that generated `findings.json` files
cannot contain confidential log lines (the motivating example being a former run's
`rd_operations: sample series labels {'service_name': 'unknown', 'vmid': '143', …, 'cluster':
'secret-clustername', 'host': 'secret-hostname', …}` message).

The answer to the tasked question, up front: **a fresh capture is clean for the one message
shape that was fixed, but not for two other shapes that leak real vmids, and the two committed
corpus bundles still contain the original leak outright** (Z-01, Z-02). The fix itself
(`_redact_finding_message()` rebuilding the message from the same vmid/device/node-only view
the structured `sample_series` field already uses) is the right shape and is pinned by a
regression test; the audit and the committed corpus were simply never extended to match it.

### 33.1 Verification run

- Dev venv `python3 -m pytest`: **847 passed, 1 warning** (the same benign statsmodels
  `ConvergenceWarning` noted since the eleventh pass), **96.19% line coverage**. The two
  privacy regression tests (`test_capture_bundle_findings_json_does_not_leak_unconfigured_labels`,
  `test_capture_bundle_manifest_version_is_not_mangled_by_vmid_redaction`) re-run individually:
  green.
- `tests/fixtures/generate_expected.py --check`: OK. `make docs-check`: OK. Version agreement:
  0.1.3 in `debian/changelog`, `pyproject.toml` and `__init__.py`.
- **Corpus gate under both toolchains**: `validate_corpus.py --check` exits 0 in the dev venv
  (ortools, pulp 3.3.2) *and* under the system Python (pulp 2.7.0, no ortools) — the Y-02 fix
  demonstrably holds cross-environment now — and regeneration in the dev venv reproduces both
  committed `.expected.json` files byte-for-byte (no diff).
- **The committed-bundle leak was measured, not inferred**: both
  `tests/corpus/bzed-dev-cluster-{24h,7d-holt-winters}/findings.json` carry six
  `"…: sample series labels {'host': 'data001', …}"` messages each (twelve total), beside the
  correctly-filtered structured `sample_series` field (`{"instance": "ide2",
  "nodename": "node-9bcf256f", "vmid": "389722"}`). The scrub audit exits 0 over both bundles.
  A `grep` for the other raw-label markers (`service_name`, `measurement`) confines the leak to
  `findings.json` — the `prometheus/` payload files are correctly label-filtered.
- **The unregistered-vmid channel was reproduced end to end**: a capture whose Prometheus
  reports a low-coverage disk for vmid 777 (no such VM in the PVE topology — the shape of a
  deleted VM, a VM on ungrouped storages, or a foreign cluster sharing the Prometheus) writes
  `"777:scsi0: coverage 0% is below window.min_coverage (80%)"` into `findings.json` while the
  structured `coverage_by_disk` next to it correctly drops the disk. Only managed-group disk
  vmids are registered with the mapper (`collect.py:1110`), and `_redact_free_text()` substitutes
  registered vmids only.
- **The extra_selector channel was reproduced end to end**: a capture with
  `metrics.extra_selector: 'cluster="prod"'` stores that text verbatim inside 19 of its 25
  Prometheus query files (`quantile_over_time(0.95, (sum by (vmid, instance)
  (rate(blockstat_rd_operations{cluster="prod"}[300s])))[86400s:150s])`), sets
  `extra_selector: null` in the bundle's `config.yaml`, records
  `extra_selector_rewritten: true` in the manifest — and a replay attempt against the written
  bundle dies on the first load query with `BundleError: bundle has no recorded response for
  the instant query '…rate(blockstat_rd_operations[300s]…'` (replay reconstructs the default
  tier's unscoped/node-alternation text, which matches nothing stored).
- `safe_range_step_seconds()`/`decimate_to_configured_step()` arithmetic hand-checked for the
  realistic (step, rate_window) pairs: 300/300→150 (exact), 600/300→200 (exact), 900/300→225
  (exact), 7200/300→288 (exact), 3600/300→276 (**inexact**: 13·276=3588≠3600, a 0.33%/point
  grid drift, documented in the docstring as "approximately, by rounded division"), 3600/900→720
  (exact). Decimation of a range response keeps indices 0, N, 2N… of a grid anchored at the same
  `start`, so for every exact divisor the retained points are *the identical instants at the
  identical values* a plain configured-step query would have returned — the range paths
  (coverage, forecaster raw series, saturation series) are truly unchanged on a healthy backend.
- All seven Y-fixes spot-verified in place: the lookahead regex (`validate_corpus.py:125`), the
  `full_matrix`-only skip reason, manual 26's `568512`, §16.6's "sorted list of moves" wording,
  §16.2's "computes it internally" wording, the version strings bypassing `_redact_free_text`
  (`collect.py:1133-1148`), and the changelog's five named W-fixes.

### 33.2 Findings summary

| ID | Severity | Module(s) | Summary |
|----|----------|-----------|---------|
| Z-01 | Medium | `tests/corpus/*/findings.json`, `validate_corpus.py` | Both *committed* corpus bundles still contain the exact label leak `bb9417b` fixed: `'host': 'data001'` (a real, unmapped Telegraf host tag) in twelve "sample series labels" messages — the fix corrected only the uncommitted `cluster-a` bundle, and the scrub audit is structurally blind to the dict-repr label shape, so every gate is green over the leak |
| Z-02 | Medium | `collect.py`, `metrics.py` | Two further free-text finding shapes leak real vmids into `findings.json`: the per-disk coverage warning and the cross-metric consistency warning embed `vmid:device` for any vmid not registered with the mapper (any disk outside the managed groups), which `_redact_free_text()` passes through raw — reproduced; the structured `coverage_by_disk` drops the same disk, so file contradicts itself |
| Z-03 | Medium | `collect.py`, plan §16.3 | A capture with `metrics.extra_selector` set stores the operator's raw selector text verbatim in ~19 of ~25 Prometheus query files (the `rate_expr_map` degenerates to the identity because `resolve_node_selector()`'s tier-1 precedence wins on *both* sides), contradicting §16.3's "rewritten, not carried — the collector replaces it with the equivalent anonymized node alternation"; the bundle is then *unreplayable* (config nulls the selector, every replay-reconstructed query text mismatches → `BundleError`), and the manifest's `extra_selector_rewritten: true` asserts a rewrite that never happened |
| Z-04 | Low | `metrics.py`, `loadmodel.py`, changelog | "No effect on an unaffected backend" (0.1.3 changelog; echoed by `safe_range_step_seconds()`'s "costs nothing (a no-op)") is not literally true for the `quantile_over_time` decision statistic: at the default config the subquery resolution silently changes 300s→150s on *every* backend — a denser p95 sample grid and ~2× the server-side inner evaluations |
| Z-05 | Low | `collect.py` | `estimate_capture()` still computes sample points at the *configured* step, so `--estimate`'s printed figure, the `support.max_series_points` refusal check and the manifest's refusal record all understate a live capture's actually-stored dense range points by exactly the workaround factor — 2× at the defaults, 13× at `metrics.step: 1h`/rw 300 (the committed 7d bundle's shape) |
| Z-06 | Low | plan §3.4, `docs/manual/`, `docs/internals/` | The gigapipe workaround landed with zero documentation: no §3.4 "as built" note, no manual touch (`metrics.step`'s entry still says only "The sampling step used for range queries"), no internals page — violating AGENTS.md §8.6 (docs in the same commit) and §7.6 (plan and code together); the code comments are excellent, the operator- and plan-facing layers were skipped |
| Z-07 | Low | release process, `tests/corpus/` | 0.1.3 was cut and merged while the developer's `make check` was red — corpus-check failing over the untracked `cluster-a/` sitting in the committed-bundle namespace instead of the `tests/corpus/local/` scratch space the corpus `.gitignore` provides for exactly this; documented in the commit message as "an unrelated, pre-existing gap" when the gap was the placement. Related: the disclosed hand-correction of `cluster-a`'s `findings.json` shows the project has no sanctioned procedure for repairing an already-captured bundle — the same procedure Z-01's fix needs |
| Z-08 | Info | plan §16.1/§16.2 | §16 promises `findings.json` carries "the verbatim output of `verify-metrics` **and `verify-storages`**"; no build has ever run `verify-storages` during capture (`collect.py` has zero references), and `_findings_to_json()` handles the verify-metrics report only — the X-08 family (a §16 sentence describing bundle content that does not exist), pre-existing since phase 10 and unreported by passes 15/16 |

### 33.3 Z-01 — the committed bundles still leak the label the fix removes

**Severity:** Medium
**Files:** `tests/corpus/bzed-dev-cluster-24h/findings.json`,
`tests/corpus/bzed-dev-cluster-7d-holt-winters/findings.json`, `tests/corpus/validate_corpus.py`

`bb9417b` fixed the collector and hand-corrected the one bundle that had not yet been committed
(`cluster-a`), updating its `SHA256SUMS` — and left the two *committed* bundles untouched. Both
still carry six `"…: sample series labels {'host': 'data001', 'instance': 'ide2',
'measurement': 'blockstat', 'nodename': 'node-9bcf256f', 'object': 'qemu',
'service_name': 'unknown', 'vmid': '389722', '__name__': …}"` messages each: a real Telegraf
`host` tag, unmapped (had `data001` been a cluster node name, `_redact_free_text()`'s node
substitution would have rewritten it — its survival next to the mapped `node-9bcf256f` is
itself proof it is something else), committed to the repository, inside the exact message
shape the fix rebuilds. The structured `sample_series` field beside each message shows the
correct three-label view, so each file contradicts itself line by line — the same asymmetry
the fix eliminates for new captures.

Every gate is green over it, and that is the structural half of the finding: the scrub audit's
value patterns cannot see the shape. `data001` is a bare host (no dot, so no public-suffix
match), and the `host='…'` literal check added for X-02/Y-01 is the *requests-exception*
equals-shape — a Python dict repr writes `host: 'data001'`, colon not equals. The audit is a
blocklist over shapes its authors could enumerate; an arbitrary Prometheus/Telegraf label value
is by construction not enumerable. `findings.json` was honestly re-scoped to value-patterns-only
by X-03's resolution, but nothing checks the one free-text field whose *structured twin sits in
the same file*.

**Recommendation:** (a) Correct both committed bundles' findings.json by rebuilding each
"sample series labels" message from the structured `sample_series` entry beside it — the
transformation is mechanical (the fixed collector's own output for the same captured data,
which is precisely how `cluster-a` was hand-corrected), needs no salt, and is verifiable;
update `SHA256SUMS` in the same commit. (b) Teach the scrub audit the shape: every
`"<metric>: sample series labels {...}"` message in a bundle's findings.json must carry a label
key set ⊆ the bundle config's three configured label names — computable from the bundle alone,
no mapper needed. That one check turns both this committed instance and any future collector
regression of `bb9417b` into a red `make check` instead of a reviewer's good fortune.

### 33.4 Z-02 — coverage and cross-metric warnings leak unregistered vmids

**Severity:** Medium
**Files:** `src/proxmox_storage_drs/metrics.py:718-741`, `collect.py`
(`_redact_free_text`, `_findings_to_json`), `collect.py:1110`

`_check_coverage()`'s per-disk warning and `_check_cross_metric_disk_consistency()`'s warning
both embed `vmid:device` strings built from the Prometheus series themselves — every series the
coverage query returns, not the managed disk set. The mapper registers only the vmids of disks
in configured groups (`mapper.register_vmids(disk.vmid for group in topology.groups …)`), and
`_redact_free_text()` substitutes *registered* vmids only, so any disk outside the managed
groups — a deleted VM whose series linger, a VM whose disks all sit on ungrouped storages, a
same-numbered vmid from another cluster sharing the Prometheus (the exact scenario §3.4's node
selector exists to exclude from *data*, while this channel carries its *identifier*) — reaches
`findings.json` as a bare real vmid. Reproduced (33.1): `"777:scsi0: coverage 0% is below
window.min_coverage (80%)"` beside an empty structured `coverage_by_disk`. §16.3's rule is
"unmapped means dropped"; the structured fields follow it, these two message shapes do not.
This is the same rebuild-from-the-allowlisted-view fix `bb9417b` applied to the sample-series
shape, two shapes over — the blocklist approach cannot be extended to cover it, because
nothing distinguishes a vmid-shaped number that is a vmid from one that is not.

**Recommendation:** route both message shapes through structured rebuilds like
`_redact_finding_message()` does: drop (or placeholder) a disk whose vmid is unregistered,
using the same predicate the structured `coverage_by_disk` already applies. Add the
composition regression the current test suite lacks: a capture with one managed and one
foreign-vmid low-coverage disk, asserting neither message carries the foreign vmid while the
managed one appears pseudonymized.

### 33.5 Z-03 — an `extra_selector` capture leaks the selector verbatim and cannot replay

**Severity:** Medium
**Files:** `src/proxmox_storage_drs/collect.py:1015-1048`, `collect.py:1407-1409`,
`IMPLEMENTATION_PLAN.md` §16.3 (line 2791ff)

§16.3 is explicit: "`metrics.extra_selector` is rewritten, not carried … The collector replaces
it with the equivalent anonymized node alternation — the selector §3.4's default tier would
have built — and the manifest flags that it did." The implementation *tries* to build both
sides of the `rate_expr_map` through `resolve_node_selector()` — but that function's tier-1
precedence returns `metrics.extra_selector` on **both** calls (real node names and pseudonym
node names are never consulted when the operator set a selector), so the map is the identity
for all six fields. Empirically (33.1): 19 of 25 query files carry `cluster="prod"` verbatim;
`config.yaml` says `extra_selector: null`; the manifest says `extra_selector_rewritten: true`.
Three consequences, in increasing order:

1. **Privacy**: the operator-authored PromQL over real label values — the plan's own words for
   why it must not be carried — reaches the bundle's `prometheus/` files. `extra_selector`
   exists for shared-Prometheus deployments, so its text plausibly names exactly the things a
   submission is supposed to abstract (cluster/customer identifiers).
2. **Replay**: with the selector nulled in the bundle config, every replay-reconstructed query
   (load, coverage, even `verify-metrics`' own probes, which also carried the selector at
   capture time through `resolve_node_selector(metrics, None)`) textually mismatches every
   stored query, and the first one raises `BundleError`. A bundle from the one configuration
   `extra_selector` exists for is useless for its purpose — loudly, but only after the author
   has received it.
3. **Honesty**: the manifest flag asserts a rewrite that never happened — the X-08 mechanism
   recording the opposite of the truth.

The fix is the plan's own sentence: build the anonymized side of the map with the node
alternation *directly* (`build_node_selector(labels.node, sorted(pseudonyms))`, bypassing tier
1) instead of through `resolve_node_selector`. Then stored queries carry the alternation,
replay reconstructs the alternation, the config's null is honest, the flag is true, and the
residual not-byte-faithfulness is exactly what §16.3 already accepts and the flag already
names. A capture test with `extra_selector` set, asserting (a) no query file carries the
configured text and (b) the written bundle replays, closes both halves; the existing
`test_capture_bundle_manifest_flags_an_extra_selector_rewrite` checks only the flag.

### 33.6 Z-04 — "no effect on an unaffected backend" is not literally true for the quantile path

**Severity:** Low
**Files:** `src/proxmox_storage_drs/metrics.py:118-161`, `loadmodel.py:134-152`,
`debian/changelog` (0.1.3)

The range-query paths are exact: decimation keeps indices 0, N, 2N… of a grid anchored at the
same `start`, so for every exact divisor the retained points are the identical instants and
values a configured-step query would have returned (33.1's arithmetic). The
`quantile_over_time` path cannot decimate — an instant query returns one scalar — and its
subquery resolution step is now unconditionally the safe step: at the default config,
`quantile_over_time(0.95, (rate(…)[24h:150s]))` evaluates the inner expression on a 2×-denser
grid than the pre-workaround `:300s` did, on every backend, healthy or not. The p95 over 576
highly-correlated samples is a slightly different statistic than over 288 (bounded by about one
order-statistic notch, small but real and it feeds gates, solver, payback and ordering), and
the server does ~2× the inner evaluations. `loadmodel.py`'s comment is honest about *why* no
decimation happens but not about *that the scalar shifts*; the changelog's "no effect on an
unaffected backend" and `safe_range_step_seconds()`'s "costs nothing (a no-op) against a
correctly-behaving backend" both overstate. The unconditional choice itself is defensible (the
symptom — zero series — is indistinguishable from genuinely absent data, so retry-on-empty
would be data-dependent and messy); what should change is the wording, in the changelog's case
as a 0.1.4 correction since 0.1.3 is released.

**Recommendation:** one honest sentence in each place: the range paths are bit-identical; the
quantile path's subquery resolution changes on every backend at boundary configs (defaults),
shifting the p95 by at most an order-statistic notch.

### 33.7 Z-05 — the estimate and the refusal threshold understate by the workaround factor

**Severity:** Low
**Files:** `src/proxmox_storage_drs/collect.py` (`estimate_capture`), `cli.py:3327-3331`

`estimate_capture()` computes `points_per_disk = range_seconds / step_seconds` at the
*configured* step, but a live capture now issues (and stores in the bundle, before any
consumption-side decimation) the *safe* step's dense response whenever the workaround triggers
— which at the default config is always. At the defaults the stored range points are 2× the
printed figure; at `metrics.step: 1h`/rw 300 — the committed 7d bundle's own shape — they are
13×. Both the printed `--estimate` figure and the `support.max_series_points` refusal check
(compare `estimate.sample_points`, `cli.py:3329`) therefore understate by exactly that factor,
so an operator sizing a capture against a busy Prometheus or against the 8 MiB commit ceiling
is told a number the capture will exceed by 2-13×, and the refusal guard passes captures the
config's own threshold was meant to stop. Note the interplay with Y-03: that fix made manual
26's example *internally* consistent with `estimate_capture()`'s formula one day before this
commit made the formula itself systematically wrong for every default-config live capture.

**Recommendation:** `estimate_capture()` should compute `points_per_disk` at
`safe_range_step_seconds(step_seconds, rate_window_seconds)` (the step the capture will
actually issue and store), and the manual's example should follow. If the intention is that
the threshold govern *stored* points, this is exactly the quantity that changed.

### 33.8 Z-06 — the workaround landed with zero documentation

**Severity:** Low
**Files:** `IMPLEMENTATION_PLAN.md` §3.4, `docs/manual/10-configuration.md` (`metrics.step`,
`metrics.rate_window`), `docs/internals/30-metrics.md`, `docs/manual/05-metrics-pipeline.md`

`29213e8` touched three source files and three test files, and not one document. The manual's
`metrics.step` entry still reads "The sampling step used for range queries (forecasting,
coverage checks). Independent of `metrics.rate_window`, though the two are usually set equal" —
with no hint that at the usual-equal setting the *issued* step is now half the configured one
(and the subquery resolution with it, Z-04). §3.4, the plan's query-construction spec, carries
no "as built" note for the workaround — the same AGENTS.md §7.6 debt T-03/U-01 established as
findings, in a commit whose code-level documentation is otherwise exemplary (the docstrings on
`safe_range_step_seconds`/`decimate_to_configured_step` and the call-site comments are among
the best in the codebase). `05-metrics-pipeline.md` documents gigapipe as a tested backend and
says "point `prometheus.url` at gigapipe's query endpoint. Nothing else [to configure]" — true
only *since* this workaround, which is exactly the sentence that should say so.

**Recommendation:** a documentation-only commit: §3.4 "as built" note (the workaround, its
trigger, its exactness guarantees per path), the manual's `step`/`rate_window` entries and the
gigapipe paragraph in `05-metrics-pipeline.md`, and an internals note in `30-metrics.md`.

### 33.9 Z-07 — 0.1.3 merged on a red local `make check`; no sanctioned bundle-repair procedure

**Severity:** Low
**Files:** release process, `tests/corpus/.gitignore`, `tests/corpus/README.md`

The 0.1.3 commit message is honest that "the target as a whole still exits non-zero for
tests/corpus/cluster-a, an unrelated, pre-existing gap (a new corpus submission still missing
its own cluster-a.submission.yaml)". Two things are off. First, the gap was the *placement*:
the corpus `.gitignore` provides `tests/corpus/local/` as "scratch space for bundles being
reviewed before they are either committed or discarded" precisely so the committed-bundle gate
(README: "A bundle without [a submission file] is an unattributed dump … and the suite fails on
it") keeps meaning what it says; `cluster-a` sat directly in the committed namespace, the gate
failed *correctly*, and the release proceeded anyway — AGENTS.md §4's "Merge to `main` only
when `make check` is green" is about the branch tip's check, not only CI's (which was green
only because an untracked directory does not exist in a checkout). The directory has since
been removed from the tree, so this is now historical — but the next submission will repeat it
unless the README's "Adding a bundle" section names `local/` as where a bundle under review
belongs. Second, and more useful going forward: `bb9417b`'s disclosed hand-correction of
`cluster-a`'s `findings.json` (with `SHA256SUMS` updated to match) improvised the procedure
that Z-01's fix now needs for the committed bundles. The corpus README should name the
sanctioned repair: rebuild the affected derived file from the bundle's own recorded payloads
with the fixed code (for findings.json, from the structured fields beside the damage), verify
with the scrub audit plus the Z-01 shape check, and record the repair in the submission file —
so a repaired bundle remains an honest artifact rather than an undetectable edit of captured
data.

### 33.10 Z-08 — §16's findings.json promise includes output no build ever captured (Info)

**Severity:** Info
**Files:** `IMPLEMENTATION_PLAN.md` §16.1 (line 2566), §16.2 (line 2666)

Both sentences say `findings.json` carries "the verbatim output of `verify-metrics` and
`verify-storages`". `collect.py` has never run `verify-storages` (zero references; the
command's findings are rendered by `cli.py` only), and `_findings_to_json()` handles the
verify-metrics report alone. Pre-existing since phase 10, missed by the fifteenth pass's X-08
sweep (which checked three other §16.3 bundle promises) and by the sixteenth. One "as built"
clause — or one line actually capturing the verify-storages report, which the topology pass
has already produced — closes it.

### 33.11 What this pass confirms

- **The label-leak fix is the right shape and works.** Rebuilding the message from the same
  filtered view the structured field uses (rather than blocklist-redacting an open-ended dict)
  is exactly the allowlist principle §16.3 states, the two can never disagree again by
  construction, the prefix-match is safe (the `": sample series labels "` suffix makes one
  metric name unable to prefix-collide with another), and the regression test drives the real
  `capture_bundle()` with an extra-label series. The committed-bundles gap (Z-01) is a
  blast-radius omission, not a defect in the fix.
- **The gigapipe workaround is engineered to the project's standard.** The trigger analysis
  (live-confirmed on two deployments, binary-searched to the exact second, the fractional-step
  parser quirk discovered and worked around while building the fix), the exactness argument
  for the range paths, the unconditional-live/replay-fallback split that keeps both committed
  bundles replaying byte-identically (verified: the corpus `--check` and the regenerated
  expected files are unchanged), the whole-second floor, and the tests pinning decimation and
  the `BundleError` fallback are all exactly right. The findings against it (Z-04..Z-06) are
  about *claims made elsewhere* (changelog, estimate, docs), not about the mechanism.
- **The releases are otherwise clean.** Version agreement across all three files, both
  changelog entries detailed and accurate down to the mechanism (0.1.2's Y-fix bullet names
  the mangled-version and sentinel-flag examples correctly; 0.1.3's two bullets describe the
  two fixes faithfully, modulo Z-04's one overclaim), and the README AI-disclaimer section is
  accurate and appropriately placed. The W-02/X-04 changelog-hygiene disease is cured.
- **The Y-fixes all hold**, verified by the suite, by spot-checks of each fix in the source,
  and — for Y-02, the one that mattered cross-environment — by running the corpus `--check`
  under the ortools-less system toolchain: exit 0, no regeneration needed.
- **The scrub audit's architecture is being asked to do something it cannot**: findings.json
  is free text over data whose identifier set is unbounded (arbitrary label names, unregistered
  vmids, operator selectors). Every finding in this pass's Medium tier is one more instance of
  the same lesson X-01/X-02 taught: free-text channels need per-shape structural rebuilds plus
  audit-side shape checks, and each new producer of a finding message must be treated as a new
  privacy surface with its own test. The `verify_metrics()` finding catalogue is small (about
  a dozen shapes); enumerating them in one place — which shapes carry cluster-derived
  identifiers, and how each is redacted — would have made Z-02 and Z-03 visible when their
  code landed.

### 33.12 Assessment

This is the shortest range since the twelfth pass — five substantive commits, two of them
releases — but it carries the project's first *privacy incident response*: a real leak found
by the submission-review discipline working as designed, fixed within a day, and released. The
fix is good; the response's blast radius is not. The committed corpus — the artefact the whole
§16 machinery exists to make shareable — still contains the leak the fix removed, the audit
still cannot see the shape, and two neighbouring message shapes carry the same class of
identifier through the same redactor. Z-01 and Z-02 together are an afternoon: rebuild twelve
messages, teach the audit one shape, extend the rebuild pattern to two more shapes, and add
the composition tests. Z-03 is the only finding with design content (build the anonymized
selector side without tier 1), and it is a five-line change with a two-assertion test. The
gigapipe work is the best-engineered change in the range and needs only honesty in the claims
around it (Z-04, Z-05, Z-06). None of the eight findings touches a safety invariant; all three
Mediums touch the same one property — *a bundle is safe to hand over* — which §16 exists to
guarantee and which, as of this pass, holds for fresh default captures of the sample-series
shape only.

---

## 34. Resolution of seventeenth-pass findings (Z-01..Z-08)

All eight findings were real. All eight are fixed except the changelog-wording half of Z-04,
deferred to the next release cut (see its own row).

| ID | Status | How resolved |
|----|--------|--------------|
| Z-01 | Resolved | Both committed bundles' `findings.json` had their six "sample series labels" messages each rebuilt from the structured `sample_series` entry beside them (mechanical, no salt needed — `data001` and every other unmapped label dropped), `SHA256SUMS` updated to match; `validate_corpus.py` gained `_scrub_findings_json()`, a structural check (new `_SAMPLE_SERIES_LABELS_RE` + `ast.literal_eval` on the message's dict-repr suffix) asserting every such message's label key set is a subset of the bundle's own configured label names — verified to flag the pre-fix committed files (reproduced against the pre-fix git blob) and pass the corrected ones. `tests/corpus/README.md` gained a "Repairing an already-committed bundle" procedure and named `local/` as where a bundle under review belongs (closing the placement half of Z-07 too); both bundles' `.submission.yaml` record this repair. |
| Z-02 | Resolved | `VerifyMetricsReport` gained `missing_disks_by_metric` (the full, untruncated real `(vmid, device)` lists `_check_cross_metric_disk_consistency()` already computed but only truncated into free text); `format_cross_metric_finding()` factors the message-building rule out so `collect.py` can call it again on a filtered view. `_redact_finding_message()` now recognizes the coverage-warning shape (matched by the exact real `coverage_by_disk` key as a prefix, mirroring the sample-series trick) and the cross-metric shape (matched by metric-name prefix against `missing_disks_by_metric`), rebuilding each with only registered vmids and returning `None` — meaning "drop this finding" — when none remain; `_findings_to_json()` filters `None`s out. Two new end-to-end regression tests reproduce the exact scenario 33.1 measured (a foreign vmid 777 low-coverage disk, and a foreign vmid missing from one of six metrics) and assert `"777"` is absent from the whole `findings.json`, not just from the structured fields. |
| Z-03 | Resolved | The anonymized side of `rate_expr_map` now calls `build_node_selector()` directly instead of `resolve_node_selector()`, which was returning `metrics.extra_selector` verbatim on *both* sides (tier 1 winning regardless of which node list was passed) — the actual root cause. Testing this by hand also found a second, undocumented instance of the same defect class: `_check_observed_spacing()`'s bare `f"{metric_name}{{{selector}}}"` probe carries the selector outside any `rate_expr_map`-shaped text at all, so `_anonymize_query_text()` and `_redact_free_text()` both gained a second, direct substring-replacement fallback (`node_selector`/`anon_node_selector`, threaded from `_capture_prometheus_files()` through to `_findings_to_json()`) for exactly that shape. Three new regression tests: no captured query file carries the configured selector text; the resulting bundle actually replays end to end (`ReplayPrometheusClient` against the bundle's own nulled-selector `config.yaml`, reproducing what a real `--replay` run resolves) with real data surviving the round trip. |
| Z-04 | Partially resolved | The two docstring overclaims are fixed: `safe_range_step_seconds()` now states the range paths are a true no-op and the `quantile_over_time` path is not; `loadmodel.py`'s comment states the reduced statistic shifts even though nothing needs decimating. The `debian/changelog` 0.1.3 entry itself is left as released text (never rewritten) — its wording carries the same overclaim, and per this project's own practice a correction belongs in the changelog entry of the next actual release, not backfilled into 0.1.3's; deferred, not forgotten. |
| Z-05 | Resolved | `estimate_capture()` now computes `points_per_disk` at `safe_range_step_seconds(step_seconds, rate_window_seconds)` — the step a live capture actually issues and stores — instead of the configured step verbatim; `estimate.step_seconds` itself is untouched (manifest/replay still need the configured value). New regression pins the exact factor (2x at the defaults) against `estimate_capture()`'s own disk count. Manual §26's worked example recomputed: `568512` → `1137024` (`47 disks · 6 metrics · 4032 points`, `604800s / 150s`), with a note explaining the doubling. |
| Z-06 | Resolved | Documentation-only follow-up commit, as recommended: an "as built" note in plan §3.4 (trigger, exactness guarantees per path, the quantile exception); `docs/manual/10-configuration.md`'s `metrics.step` entry now describes the workaround and its point-count effect; `docs/manual/05-metrics-pipeline.md`'s "nothing else changes" gigapipe sentence now says what *does* change; a new `docs/internals/30-metrics.md` section on `safe_range_step_seconds()`/`decimate_to_configured_step()`. |
| Z-07 | Resolved | Both halves closed: the placement half by `tests/corpus/README.md` now naming `local/` as scratch space for a bundle under review (Z-01's row above); the missing-repair-procedure half by the new "Repairing an already-committed bundle" section, applied to Z-01's own fix as its first real use. The historical 0.1.3-merged-on-red-`make check` incident itself is not undone (the directory in question is already gone from the tree) — the fix is procedural, for the next time. |
| Z-08 | Resolved | Corrected the plan's own overstatement rather than building a redundant feature: `verify-storages`'s report is a pure function of the topology and config a bundle already carries in `pve/`/`config.yaml`, so `--replay <bundle> verify-storages` already reproduces it byte-for-byte with no separate capture needed — unlike `verify-metrics`, whose report depends on a live Prometheus response that is otherwise lost. §16.1's file-listing comment, §16.2's failure-visibility paragraph and its "at a glance" table row all corrected to say so explicitly, closing the promise/reality gap without adding dead-weight duplicate data to every bundle. |

New/updated regression tests: `test_capture_bundle_extra_selector_never_reaches_a_query_file`,
`test_capture_bundle_findings_json_drops_a_foreign_vmids_coverage_warning`,
`test_capture_bundle_findings_json_drops_a_foreign_vmid_from_cross_metric_finding`,
`test_estimate_capture_sample_points_uses_the_safe_step` (`test_collect.py`);
`test_replay_prometheus_client_range_query_survives_a_captured_extra_selector` (`test_replay.py`);
`test_scrub_findings_json_flags_a_sample_series_label_outside_the_configured_set`,
`test_scrub_findings_json_passes_the_allowlisted_view`,
`test_scrub_audit_catches_a_findings_json_label_leak_the_value_checks_miss`
(`test_validate_corpus.py`); plus signature-shape updates to
`test_cross_metric_disk_consistency_*`/`test_check_sample_series_reports_a_cross_metric_gap`
(`test_metrics.py`) for the new `missing_disks_by_metric` return value.

Verification: dev venv `python3 -m pytest` — **855 passed**, **96.32% line coverage** (no
regression; up from 96.19% with the new tests). `make check` clean end to end: fmt, lint
(`_scrub_findings_json`'s first cut needed splitting to clear flake8's complexity limit),
typecheck, test-with-coverage, fixtures, corpus-check (both committed bundles' scrub audit and
`--check` clean, including the new Z-01 shape check), and docs-check (`IMPLEMENTATION_PLAN.pdf`
rebuilt at 60 pages, `internals.pdf` at 52, the manual PDF at 46 — all three touched by this
pass's documentation fixes, all three stamps refreshed). A `--full-matrix --check` run reports the
same two committed bundles stale for the pre-existing, unrelated reason section 32 already
documented (the narrow-vs-full-matrix skip-reason difference for `seasonal_naive`/`holt_winters`
against a 24h-lookback bundle) — reproduced identically, out of this pass's scope for the same
reason it was out of the sixteenth pass's.

---

## 35. Eighteenth-pass review — plan §12 (capacity spread, one-year payback), its implementation, release 0.1.4, and four dogfooding fixes

Reviewed commit range `5397c45..HEAD` (the Z-01..Z-08 fixes themselves are recorded in section
34 and are verified here rather than re-reviewed). Nine non-merge commits: `32db294` (AGENTS.md
release rules: changelog entry + annotated `debian/<version>` tag on every version bump),
`036617c` (Release 0.1.4), `a4fbaa8` (a shared storage's capture node is picked from the same
pseudonym-sorted view `--replay` will derive its pick from — a real bundle, `cluster-g`, hit the
disagreement), `9b053d8` (`anonymize.py` accepts PVE's `.<format>` suffix on volume names,
found on a real cluster's qcow2-on-shared-LVM disks whose volids were silently dropped whole),
`97368f0` (the plan change: §12 — `δ`/§5.3 (C7) data-spread term, §6 capacity gate, §7.2's
`H = 365d` and two-term benefit, §14 rewritten around them), `df77140` (a range capture taken
with `collect-testdata --step` replays: a step mismatch is now a recoverable
`RangeStepMismatch` carrying the bundle's real step, not a hard `BundleError`), `71c306f` (the
phase 12 implementation: config, heuristic, gates, both MILP backends, payback, CLI, fixtures,
corpus), `87b4a6c` (`_redact_free_text()` substitutes group names — real group names reached
committed bundles' `manifest.json` call logs), and `e4240fa`/`ee2d805` (AGENTS.md's branch-first
rule made mechanical — the range's only branch-merged commit). This pass was tasked with the
updated implementation as a whole, with §12 as its centre of gravity.

The headline, up front: **the §12 specification work is of this plan's usual quality, the
heuristic/CBC/gate/payback wiring implements it correctly, and the CP-SAT backend does not** —
its (C7) term carries a six-orders-of-magnitude scaling error that makes the default `auto`
cascade plan mass relocations for fill evenness while ignoring migration penalties and I/O
balance (AA-01, reproduced on a committed bundle). Every gate — suite, fixtures, corpus,
cross-backend check — is blind to it, each for an unrelated, individually-reasonable reason.

### 35.1 Verification run

- `make check` at HEAD (`ee2d805`): green end to end — fmt-check, lint, typecheck, **878 passed,
  1 warning** (the same benign statsmodels `ConvergenceWarning` noted since the eleventh pass),
  **96.31% line coverage**, `generate_expected.py --check` OK, `validate_corpus.py --check` OK,
  docs-check OK.
- Release hygiene: version agreement (0.1.4 in `debian/changelog`, `pyproject.toml`,
  `__init__.py`); the 0.1.4 changelog entry covers the whole Z-range accurately, including the
  Z-04 correction its resolution deferred to "the next actual release"; annotated tag
  `debian/0.1.4` on `036617c`, tagger `Bernd Zeimetz <bernd@bzed.de>`, message `pve-storage-drs
  0.1.4` — the first release shipped under `32db294`'s new rule, and it complies.
- **All eight Z-fixes verified in place**: `data001` gone from both committed `findings.json`
  (0 hits); `_scrub_findings_json()` and its three tests in `validate_corpus.py`; the Z-02
  rebuild shapes (`missing_disks_by_metric`, the coverage/cross-metric `_redact_finding_message`
  paths, both end-to-end foreign-vmid regression tests); the Z-03 root-cause fix
  (`build_node_selector()` for the anonymized map side, the bare-probe fallback, the
  no-selector-in-any-query-file and bundle-replays tests); Z-05's `estimate_capture()` at
  `safe_range_step_seconds()` with the pinned-factor test; Z-06's four documents; Z-07's
  `local/` and "Repairing an already-committed bundle" README sections; Z-08's §16 wording.
- §14's new numbers re-derived by hand: §14.2's fills 56%/19%/6%, `b̄ = 0.2708`, `F_before =
  2.1538`, capacity gate `(0.5625−0.0625)/0.2708 = 1.85` ✓; §14.3's two-move `E_after = 1.5333`,
  `F_after = 0.3077`, full objectives 2.812 vs 2.918, the δ=0 β-flip at 0.375, and the affinity
  comparison 3.52 vs 2.19 ✓; §14.5's benefit 235,145,354, ratio 8,970, and the rejected 4-TiB
  move at ratio 7.5 ✓; §14.6's rows one and two (11.25, 2.18), flip point 9.08 and `P_min =
  23.6·2²⁰ ≈ 2.47×10⁷` ✓ — all matching the regenerated fixtures byte-for-byte, except one cell
  (AA-03).
- The regenerated `fc-tier1` fixture sweeps `(β, δ) ∈ {0.25, 0.5} × {0.0, 0.5}` at
  `payback_horizon: 365d`; the δ=0 cases record the three-move plan, the defaults the two-move
  plan, exactly as §14.3's two knob demonstrations claim.
- The CP-SAT experiments of AA-01 were run in the dev venv (ortools 9.15) against the §14 group
  and, end to end, against the committed `bzed-dev-cluster-24h` bundle (in-process at the
  bundle's own configured weights, and via `--replay … plan`, where `solver.backend: auto`
  resolves to cpsat).

### 35.2 Findings summary

| ID | Severity | Module(s) | Summary |
|----|----------|-----------|---------|
| AA-01 | High | `optimize.py` (CP-SAT), plan §5.5 | The (C7) integer linearization builds `d_s` at a 10¹² scale (`_FILL_SCALE`) while `delta_scaled = round(δ·W)` presumes §5.5's 10⁶ scale — CP-SAT's effective `delta_capacity_spread` is the configured value ×10⁶ (500,000 at the defaults), swamping α/β/γ/κ; with ortools installed the default `auto` backend returns plans up to 3.2× worse on the specified objective than moving nothing (reproduced on a committed bundle), and no gate catches it: the corpus default sweep skips cpsat, the fixture's δ=0.5 case cannot distinguish the amplified objective, and the MILP-vs-heuristic check was relaxed to two-axis Pareto dominance in the same commit |
| AA-02 | Medium | `tests/corpus/*/manifest.json`, `validate_corpus.py` | Both committed bundles still carry the real group name `bzed-shared` twelve times each in their `manifest.json` call-log free text — the exact leak shape `87b4a6c` fixed for new captures, whose own test docstring names committed bundles as the find; the fix corrected only the collector, the audit still cannot see a bare group name, and the Z-07 repair procedure was not applied |
| AA-03 | Low | plan §14.6 | The "both moved to `cramped`" non-reserve-objective cell says 11.85; (C7) gives F = 5.0 (`b_roomy = 0`, `b_cramped = 1.0` against `b̄ = 0.2`), so the cell is 10 + 0.5 + 0.1 + 2.5 = **13.10** — 11.85 reuses the current assignment's F = 2.5; inert to the section's conclusions (the flip point compares against 11.25) but §14 is the plan's hand-verifiable worked example |
| AA-04 | Low | `schedule.py`, `generate_expected.py`, plan §8.2/§14.4 | §8.2's revised ordering rule ("persistent-objective reduction … the α and δ terms") and §14.4's matching claim were never implemented: `order_moves()` — in both the engine and the fixture generator — still ranks by α-only `imbalance_term`; code and fixture agree with each other and with the *old* §8.2 |
| AA-05 | Low | plan §2.3, `docs/manual/`, `docs/internals/` | The six-term objective landed over a stale "five terms" cluster — plan §2.3's `plan_selected` audit row, manual 29-explain (prose + JSON field list), manual 30's explain row, manual 10:710, internals 40:61 and 90:190,221 — and both PDFs were rebuilt and re-stamped *with* the stale text, so docs-check now enforces it; also `plan --json`'s new `before/after_capacity_spread` are missing from 27-plan.md's field list and `show-load --json`'s new `capacity_fraction` from manual 25's gate-field description |
| AA-06 | Low | plan §9.5, `cli.py` | §9.5's updated sample gained a `data:  fill 25%/31%/25%  deviation 31% (from 215%)` line that no renderer prints — `plan`/`apply` print `after:`/`spread:` only, `explain` has no fill line either — and the V-02 "As built" paragraph directly below, which exists to say which sample lines belong to `explain`, was not extended to cover it |
| AA-07 | Low | git workflow | Eight substantive commits landed straight on `main` with no branch (`32db294`, `036617c`, `a4fbaa8`, `9b053d8`, `97368f0`, `df77140`, `71c306f`, `87b4a6c`) — the exact "string of small, individually-reasonable-looking commits" pattern `e4240fa`'s rule exists to stop, and the rule-hardening commit is the range's only branch; `9b053d8` additionally landed with `make pdf-check` red (disclosed in its commit message, healed two commits later by `97368f0`) against §7.4's same-commit rule and §4's main-must-stay-green |
| AA-08 | Info | `collect.py`, `tests/unit/` | (a) `a4fbaa8`'s `real_node_by_pseudonym.get()` silently drops the (node, storage) capture pair when the picked node is absent from `/nodes` — the bundle then lacks the content/status file replay will ask for and fails late; (b) `9b053d8`/`87b4a6c`'s test docstrings quote real production identifiers verbatim (`dc6_con-abn-pve-dc6_T2T3_001:vm-101-disk-1.qcow2…`, `dc6_T2`) into committed sources, a posture inconsistency with the anonymization machinery rather than a bundle leak |

### 35.3 AA-01 — CP-SAT's (C7) term is scaled 10⁶× too strongly; the default backend optimizes the wrong objective

**Severity:** High
**Files:** `src/proxmox_storage_drs/optimize.py` (`_FILL_SCALE`, `_cpsat_fill_scale_for()`,
`_cpsat_capacity_spread_term()`), `IMPLEMENTATION_PLAN.md` §5.5

The (C7) linearization builds, per storage, `k_s = round(_FILL_SCALE / (b̄·C_s_MiB))` with
`_FILL_SCALE = 10¹²`, and `d_s ≥ k_s·|numerator_MiB − round(b̄·C_s_MiB)|` — so `d_s` is a
**10¹²-scaled** relative fill deviation (`d_s ≈ 10¹²·|b_s − b̄|/b̄`; the code comment itself
derives this shape). Every other objective variable in the model is scaled by §5.5's
`K = 10⁶` (`e_s` via `a_{d,s} = round(K·ℓ_d/c_s)`), and every weight by `W = 10⁴` — including
`delta_scaled = round(δ·W)`, which per §5.5's own scaling table presumes `d_s` sits on the same
10⁶ scale as `e_s` ("`K` | the load-valued variables `e_s`, `t`, the fill-deviation variables
`d_s` … | 10⁶"). Multiplying a 10¹²-scale variable by a 10⁶-scale weight makes the term's
effective magnitude `round(δ·W)·10¹²/(W·K) = δ·10⁶` relative to the rest of the objective:

- at the new default `δ = 0.5`, CP-SAT optimizes with an **effective δ of 500,000** against
  `α = 1` — §5.4's "`δ` defaults to half of `α`" and §1's "I/O stays first priority by weight
  and by scale" are both simply false for this backend;
- at `δ = 10⁻⁴` (total term contribution ~3×10⁻⁵ — the true optimum is the δ=0 optimum), the
  effective δ is ~100;
- at `δ ∈ (0, 5×10⁻⁵)`, `round(δ·W)` is 0 and `_assert_nonzero_when_weighted` raises
  `AssertionError: delta_scaled rounded to 0 …` on a schema-legal config — this half is §5.5's
  mandated zero-coefficient guard behaving as it already does for α/β/γ/κ, not a separate
  defect, but it marks the granularity floor.

**Reproduced twice.** (1) The §14 group at `δ = 10⁻⁴`: the heuristic returns the three-move
plan (the δ=0 optimum, as expected for a negligible δ); CP-SAT returns the two-move plan —
on the specified objective that plan is worse by 0.125, and its advantage exists only on the
amplified capacity term. (2) The committed `bzed-dev-cluster-24h` bundle at its own configured
weights (α=1, β=0.25, γ=0.05, κ=0.5, δ=0.5 by default), evaluated through the same
`evaluate_assignment()` the engine uses: the specified objective's optimum is **no moves**
(total 0.6457; imbalance term 0.086, capacity term 0.559) — the heuristic and CBC both find it;
**CP-SAT returns a 4-move plan that splits VM 612603 across storages** (move-count term 1.0,
fragmentation 0.5, bytes 0.057) **for a total of 2.0951 — 3.2× worse than doing nothing** —
buying `after_capacity_spread` 0.0011 from 1.119 with real migrations no term of the specified
objective justify. `solver.backend: auto` is `("cpsat", "cbc")`, so every environment with
ortools (the dev venv's `solver` extra, CI) plans with the broken backend by default; a plain
`--replay tests/corpus/bzed-dev-cluster-24h plan` on this checkout exhibits it (capacity gate
ACT at 111.9%, four moves, payback accepted at the one-year horizon — in `apply`'s execution
modes this plan would be executed). The packaged Debian install falls through to CBC and is
unaffected — which is also why production dogfooding has not yet hit it.

**Why every gate is blind.** The corpus default sweep skips cpsat entirely ("not swept without
`--full-matrix`"), so the committed expected files record heuristic and cbc only.
`test_optimize.py`'s two §12 tests are δ=0 (term not built) and δ=0.5 — on the §14 group the
minimum-F assignment set happens to *coincide* with the true optimum, so CP-SAT "agrees" with
the fixture at exactly the one δ the fixture sweeps. And `check_milp_vs_heuristic()` was
relaxed in the same commit from `after_spread` alone to two-axis Pareto dominance — a correct
generalization on its own terms (CBC demonstrably and legitimately trades imbalance for spread
at the true weights), but exactly the property that lets a plan which is better *only* on the
capacity axis through: the amplified plan is never dominated. The commit's own corpus narrative
("cbc's after_spread was ~96× the heuristic's … but its full objective total was *lower*")
observed the legitimate version of this trade and generalized the check past the point where it
could catch the broken one.

**Recommendation.** Make the term commensurate with the rest of the model — either build the
per-(disk, storage) coefficients `round(K·z_d/(b̄·C_s))` with the constant
`round(K·(1 − Uˢᵉˣᵗ/(C_s·b̄)))` exactly as §5.5 specifies (`K = 10⁶`; the coefficient is ≥ 1
for any disk of ~2 MiB and up at §14's shape — only sub-MiB volumes round to zero, worth an
as-built note), or keep the per-storage `k_s` decomposition and rescale `delta_scaled` by
`K/_FILL_SCALE`. Then add the regression that fails today: cpsat-vs-heuristic at
`delta_capacity_spread: 0.0001` on the §14 group asserting the three-move optimum — and,
stronger and δ-independent, re-score every backend's returned assignment through
`evaluate_assignment()` at true weights inside the corpus check and assert the MILP's total ≤
the heuristic's plus the `mip_gap` tolerance ("the MILP optimized the objective we wrote", the
objective-level version of the dominance check). Update §5.5's table row and folding sentence
to the as-built decomposition, and regenerate the `--full-matrix` expected files, which
currently record the amplified cpsat behaviour.

### 35.4 AA-02 — the committed bundles still carry the group-name leak the range's last fix removes

**Severity:** Medium
**Files:** `tests/corpus/bzed-dev-cluster-24h/manifest.json`,
`tests/corpus/bzed-dev-cluster-7d-holt-winters/manifest.json`, `tests/corpus/validate_corpus.py`

`87b4a6c` extended `_redact_free_text()` with group-name substitution, registered
`known_groups` on the mapper (with the pseudonym-collision check), and pinned the shape with a
regression test — and its own test docstring records the find: "real group names (e.g. `dc6_T2`)
reached committed corpus bundles' `manifest.json` verbatim". Like `bb9417b` before it (Z-01),
the fix corrected only the collector. Both committed bundles still carry the real group name
`bzed-shared` **twelve times each** in `manifest.json`'s call-log free text
(`instant quantile_over_time write_time_ns q=0.95 (bzed-shared)`), while each bundle's
`config.yaml` carries only the pseudonym `group-448ef164` — the file contradicts itself, the
scrub audit's value patterns cannot see a bare group name (no dot, no public suffix, and group
names appear in no allowlist), and the "Repairing an already-committed bundle" procedure that
Z-07's fix added to the corpus README for exactly this contingency was not applied. One nuance
the seventeenth pass did not have: the 24h bundle's `.submission.yaml` deliberately names
`bzed-shared` as provenance, so *this* name is not secret in this repository — but the manifest
is the channel §16.3's redaction rules govern, the fix's motivating example was a *production*
group name, and a collector whose committed corpus still contradicts it is precisely the state
Z-01 existed to end.

**Recommendation:** repair both manifests by replacing the group qualifier with each bundle's
own `group-<8hex>` pseudonym (mechanical, salt-free — the pseudonym is in the bundle's own
`config.yaml`), update `SHA256SUMS`, and record the repair in the submission files per the
README procedure. Teach the audit the shape: every parenthesised group qualifier in a call
description must be one of the bundle config's own group names.

### 35.5 AA-03 — §14.6's "both moved" cell does not derive

**Severity:** Low
**Files:** `IMPLEMENTATION_PLAN.md` §14.6

The table's third row says both disks moved to `cramped` costs a non-reserve objective of
11.85 at `β = 0.25, δ = 0.5`. The four other terms give `10 + 0.5 + 0.1 = 10.6`, so 11.85
implies `δ·F = 1.25`, i.e. `F = 2.5` — the F of the *current* assignment (row one). Both disks
on `cramped` gives `b_roomy = 0`, `b_cramped = 5/5 = 1.0` against `b̄ = 0.2`, so `F = 1 + 4 =
5.0`, `δ·F = 2.5`, and the cell is **13.10** — confirmed with the generator's own
`objective_nonreserve()` (`current: 11.25 / one-moved: 2.175 / both-moved: 13.100`). The error
is inert — the row is dominated either way, the `big_m_agreement_threshold_p` of 9.08 compares
against 11.25, and `P_min = 23.6·2²⁰` all verify against the regenerated fixture — but §14 is
the plan's executable acceptance fixture, its tradition is that every number hand-derives, and
this pass's own regeneration made the table newly checkable in exactly this shape.

### 35.6 AA-04 — §8.2's revised ordering rule was never implemented

**Severity:** Low
**Files:** `src/proxmox_storage_drs/schedule.py` (`order_moves`),
`tests/fixtures/generate_expected.py` (`order_moves`), plan §8.2, §14.4

`97368f0` rewrote §8.2's scheduling pseudocode to `m ← argmax over feasible of
(persistent-objective reduction) / cost_m` with the gloss "the α and δ terms of §5.4 — the
parts whose improvement persists; β/γ are one-time costs", and §14.4 now claims move 1 "has
the largest persistent-objective reduction per unit cost". The engine still ranks candidates by
`evaluate_assignment(...).imbalance_term` — α only — and the fixture generator mirrors it with
`(E_of(state) − E_of(next)) / cost`, so code and fixture agree with each other and with the
*pre-§12* §8.2, while the plan describes a rule neither implements. The divergence is invisible
on the §14 fixture (the ordering coincides) but real whenever a pending move trades I/O balance
for data spread — exactly the trade δ exists to express, so the front-loaded-value ordering
§8.2's prose argues for would differ. Per AGENTS.md §7.6, one of the two is a bug: either
score `α·ΔE + δ·ΔF` in both implementations, or revert §8.2/§14.4 to "imbalance reduction" and
say why δ stays out of the ratio (its ΔF is often dominated by the assignment's *final* state,
not the move's own effect, which is a legitimate design argument — but it has to be made in the
plan, not silently contradicted by the code).

### 35.7 AA-05 — the six-term objective over a stale "five terms" documentation cluster

**Severity:** Low
**Files:** `IMPLEMENTATION_PLAN.md` §2.3, `docs/manual/29-explain.md`,
`docs/manual/30-safety-and-status.md`, `docs/manual/10-configuration.md`,
`docs/manual/27-plan.md`, `docs/manual/25-show-load-and-verify-storages.md`,
`docs/internals/40-cli-and-logging.md`, `docs/internals/90-heuristic.md`

`71c306f` added the sixth term to `ObjectiveBreakdown`, `explain --json`'s `objective`, the
audit log, and both "closest alternative" renderers — and updated the plan's §9.5 sample and
§16.6, but not the layer that documents the output shape. Still saying "five terms" (or "the
five terms" as an exhaustive list) after the change: plan §2.3's `plan_selected` audit row
("move count, the five objective terms" — the built audit log carries the six-term
`_objective_breakdown_json`); `29-explain.md`'s `objective:` line prose and its `--json` field
list (twice); `30-safety-and-status.md`'s explain row; `10-configuration.md`'s
reserve-penalty cross-reference (line 710); `40-cli-and-logging.md` line 61; `90-heuristic.md`
lines 190 and 221. Both PDFs were rebuilt and re-stamped in the same commit *with* the stale
text, so `make docs-check` now enforces the lie. Two neighbouring field-list gaps: `plan
--json` gained `before_capacity_spread`/`after_capacity_spread` (consumed by
`validate_corpus.py`) but `27-plan.md`'s field list still ends at `before_spread`/`after_spread`
(line 195), and `show-load --json`'s gate block gained `capacity_fraction` but
`25-show-load-and-verify-storages.md` documents `drift_fraction`/`imbalance_fraction` only —
the AGENTS.md §8.6 "tests, not good intentions" enforcement apparently covers CLI options and
config knobs, not JSON field lists.

**Recommendation:** one documentation sweep: the seven "five terms" locations, the two field
lists, rebuild both PDFs; consider a tiny test asserting `29-explain.md`'s documented objective
key set equals `_objective_breakdown_json()`'s keys, which would have failed here and holds
the manual to the same standard the config-knob tests already hold §8.3.

### 35.8 AA-06 — §9.5's new "data:" sample line is printed by nothing

**Severity:** Low
**Files:** `IMPLEMENTATION_PLAN.md` §9.5, `src/proxmox_storage_drs/cli.py`

`97368f0`/`71c306f` added a `data:  fill 25%/31%/25%  deviation 31% (from 215%)` line to §9.5's
sample plan output. No renderer prints it: `plan`/`apply`'s human output ends at `after:` /
`spread:` / payback (`_render_group_plan_human()`), and `explain`'s human output has no fill
line either — the fill quantities reach a human only indirectly, via the gate reason and the
`spread` term of the objective line. The V-02 "As built" paragraph immediately below the
sample — which exists precisely to say which of the sample's lines belong to `explain` rather
than `plan` — was not extended to cover the new line, so a reader matching output to spec will
look for a line that never appears, the exact V-02 failure mode the paragraph was written to
close. (Phase 12's acceptance bullet "`explain` reports the fill deviation" is satisfied only
by `--json` scalars — `before/after_capacity_spread` and the objective's `capacity_spread_term`
— which is defensible, but then the sample and its disclaimer should say so.)

### 35.9 AA-07 — eight substantive commits straight to `main`, one knowingly red

**Severity:** Low
**Files:** git history `5397c45..ee2d805`, AGENTS.md §4/§7.4

The range's eight substantive commits (all listed in 35.1's first paragraph) landed linearly on
`main` with no branch and no merge — against AGENTS.md §4's branch-first rule as it already
stood ("Branch before you edit, not after … 'just fix this one thing' is not an exception"),
the exact pattern `e4240fa`'s rewrite names as its target ("a string of small,
individually-reasonable-looking commits landing straight on `main`"), with the sharpening
commit itself the range's only branch. `9b053d8` additionally landed with `make pdf-check` red
— its commit message discloses the sandbox-local `make pdf` failure and says "make pdf-check
will fail until then", which is honest and exactly the wrong state for `main` per §7.4 ("run
`make pdf` and commit the regenerated PDF … in the *same* commit as the Markdown") and §4
("main must stay green"); `97368f0` healed the drift two commits later. Z-07 made this same
point about 0.1.3; the pattern then repeated inside the very range that hardened the rule
against it. Nothing shipped broken — HEAD is green, the release tag is clean — which is the
mitigation, not the excuse: the rule's value is reviewability of each step, not merely the
end state.

### 35.10 AA-08 — two small edges (Info)

(a) `a4fbaa8`'s pseudonym→real back-map (`real_node_by_pseudonym.get(new_node)`) silently drops
the (node, storage) capture pair when `_pick_active_node()` picks a node that is not in
`known_nodes` (the `/nodes` response) — a storage reported `available` on a node absent from
`/nodes` produces a bundle missing the content/status file replay will later ask for, failing
late with a `BundleError` instead of warning at capture time. Unreachable in the committed
bundles' shape; a one-line warning would localize it when it happens.

(b) `9b053d8`'s and `87b4a6c`'s test docstrings quote the production cluster's identifiers
verbatim (`dc6_con-abn-pve-dc6_T2T3_001:vm-101-disk-1.qcow2,discard=on,…`, `dc6_T2`) as the
"confirmed against a real cluster" evidence. The whole §16.3 machinery exists to keep such
identifiers out of shareable artefacts, and the same commits' corpus discipline did; the test
files are the repo's own, and this is self-disclosure rather than a leak — but the habit of
pasting the evidencing value whole, where a redacted-but-shape-preserving example would carry
the same information, is how the next bundle leak will happen. Noted, not actionable beyond
awareness.

### 35.11 What this pass confirms

- **The Z-01..Z-08 fixes are all real and hold** — each spot-verified in the tree (35.1), the
  suite and both corpus gates green over them, and the committed bundles clean of the shapes
  the fixes removed (the `data001` label, the foreign-vmid findings, the verbatim selector).
  Section 34's claims are accurate, including the deliberately-partial Z-04 whose changelog
  correction 0.1.4 now carries.
- **Release 0.1.4 is clean and is the first release under the new §9.2 rules** — changelog
  complete and mechanism-accurate, three-way version agreement, annotated `debian/0.1.4` tag
  with the right identity and message on the release commit. The W-02/X-04/Z-07 release
  hygiene arc is, on its own terms, cured.
- **The dogfooding fixes in the range are exemplary.** `a4fbaa8` finds the capture/replay
  disagreement at its root (the tie-break depends on list order, and the committed list is
  sorted by pseudonym) and closes it by making the two sides agree *by construction*, with a
  salt-adaptive test that cannot pass by accident. `9b053d8` root-causes the dropped qcow2
  volumes to PVE's own `.<format>` volume-name convention, carries the extension through
  verbatim for the right reason (replay must still match the content listing), and updates the
  plan's §16.3 row in the same commit. `df77140` gets the exception taxonomy right — a step
  mismatch is recoverable because the bundle itself carries the true step, a genuine cache
  miss is not — implements exactly one retry with the named step, and keeps the loud-failure
  path re-pinned by a test. `87b4a6c` is the right fix shape (register the identifier kind,
  substitute whole strings longest-first, extend the collision check); only its blast radius is
  short (AA-02).
- **The §12 plan change itself is well-argued and its numbers hand-verify**: the
  "spread data evenly" interpretation as a tunable preference (with the honest reason a strict
  lexicographic order could never act), the three-things-`H`-is-not paragraph, the scale-free
  `b̄` normalization with its empty-group edge, the δ knob and affinity demonstrations in
  §14.3, and the regenerated fixtures agreeing with the plan to the digit (mod AA-03). The
  capacity gate's wiring is correct and well-tested (bypass order after the reserve override,
  null-disable, `b̄ = 0`, the §14.2 1.85 pin), payback's R-01 discipline survives the two-term
  formula (raw quantities in, weights explicit, the internals page updated to explain why),
  and CBC's (C7) path is correct as built.
- **The corpus relaxation was argued honestly and still masked AA-01** — the docstring
  documents a real, legitimate cbc trade at true weights, and the two-axis dominance rule is
  the right *minimal* claim; what was missing is the objective-level check (re-scoring each
  backend's plan at true weights) that no relaxation can talk its way past.

### 35.12 Assessment

This is the range where the project's two habits — specification-first rigour and
dogfooding-driven fixes — met the first feature specified ahead of the implementation (§12),
and the result is both the best-engineered plan change since §14 itself and the project's
first true solver-correctness bug that every gate blesses. AA-01 is the plainest kind of
integer-scaling defect — two scales built by different rules twenty lines apart in the same
function — and it survived because each safety net that should have caught it was exactly one
coincidence or one honest generalization away from blind: the fixture sweeps the one δ whose
optimum coincides with the amplified objective's, the corpus sweep never runs cpsat by default,
and the cross-backend check was relaxed, for a correctly-argued reason, in the same commit that
needed it most. The durable lesson is §16.6-shaped: "not dominated" is checkable cheaply, but
"optimized the objective we wrote" needs the objective — re-scoring every backend's plan
through `evaluate_assignment()` at true weights, inside the corpus check, closes this class at
any δ, in any sweep, for any future term. AA-02 is Z-01 replayed one identifier kind later and
should be closed the same afternoon, with the procedure Z-07 already wrote. Everything else in
the range — the payback horizon's honest re-derivation, the gate, the collect/replay fixes,
the release — is work this reviewer would sign off on unchanged.

---

## 36. Resolution of eighteenth-pass findings (AA-01..AA-08)

Seven findings fixed, one (AA-07) acknowledged without a code/process change per the operator's
own direction (its row explains why), one half of AA-08 fixed and the other refuted as
unreachable given code this pass verified more closely than the finding itself did.

| ID | Status | How resolved |
|----|--------|--------------|
| AA-01 | Resolved | `optimize.py`'s (C7) linearization rebuilt to fold exactly like (C6) (section 5.5's own words for it): `_cpsat_fill_scale_for()`/`_cpsat_storage_used_mib()`/`_FILL_SCALE` (a 10¹² scale distinct from every other term's 10⁶) removed outright, replaced by `_cpsat_storage_fill_lhs()`, a per-(disk, storage) folded coefficient at the same `_LOAD_SCALE` (`K`) every other term uses — `round(K·z_d/(b̄·C_s))` per disk plus a `round(K·(1−Uˢᵉˣᵗ/(C_s·b̄)))` constant, precisely §5.5's specified decomposition, with a domain bound derived from the coefficients themselves rather than a separate oversized constant. New regression `test_delta_negligible_does_not_swamp_the_objective` (both backends) pins the fix at `delta_capacity_spread=0.0001`, where the pre-fix amplification returned the wrong (two-move) plan; reproduced end to end against the committed `bzed-dev-cluster-24h` bundle — CP-SAT now agrees with CBC exactly (`moves: []`, `after_capacity_spread == before_capacity_spread`), where it previously returned a 4-move, 3.2×-worse plan. Per the recommendation's stronger half: `plan`/`apply --json` gained `before_objective_total`/`after_objective_total` (the full six-term `.total`, re-scored through the same `evaluate_assignment()` the engine uses), and `validate_corpus.py` gained `check_milp_objective_total()`, asserting every MILP backend's objective is no worse than the heuristic's by more than `solver.mip_gap` — the objective-level check X-07's own note (§35.3) said could not be shipped without exactly this field. Both committed bundles' `.expected.json` regenerated (narrow mode, matching the committed shape); a full `--full-matrix` run is clean too (zero violations from either cross-backend check, across every spread metric/forecast model/beta combination on both bundles). |
| AA-02 | Resolved | Both committed bundles' `manifest.json` had their twelve `bzed-shared` group-name occurrences mechanically replaced with the bundle's own `group-448ef164` pseudonym (from its own `config.yaml`, no salt needed), `SHA256SUMS` recomputed, both `.submission.yaml` recording the repair per `tests/corpus/README.md`'s procedure. `validate_corpus.py` gained the structural check the audit was missing: `_scrub_manifest_group_names()` matches `_drive_group_series()`'s own `"instant quantile_over_time ... (<group>)"` shape and asserts the qualifier is one of the bundle's own configured group names — verified to flag the pre-repair files and pass the corrected ones, with unit regressions in `test_validate_corpus.py`. |
| AA-03 | Resolved | §14.6's "both moved to `cramped`" cell corrected from 11.85 to 13.10 — confirmed against `generate_expected.py`'s own `objective_nonreserve()` (`11.25 / 2.175 / 13.1` for the three rows), which the erroneous cell had silently disagreed with. |
| AA-04 | Resolved | Code changed to match the plan, per AGENTS.md §7 ("change the plan and the code together" — the plan's own persistent-vs-one-time-cost argument for including `δ` in the ranking is the one worth keeping). `schedule.order_moves()` now ranks candidates by `(imbalance_term + capacity_spread_term)` reduction per byte, not `imbalance_term` alone — both already carry their own weight, so no rescaling is needed; `ScheduledMove.imbalance_reduction`'s *reported* value is untouched (still alpha-only, matching every existing caller/test). `generate_expected.py`'s mirror `order_moves()`/`ratio()` updated the same way, now taking the case's own swept `delta` explicitly rather than reading a `f.objective["delta_capacity_spread"]` key that never existed outside the `delta_values` sweep list (a latent bug the fix surfaced, not introduced — the old code path was reading a nonexistent dict key that happened never to run with the term guarding it nonzero at a nonzero delta). New regression `test_ordering_prefers_the_larger_persistent_reduction_once_delta_matters` constructs a two-disk case where the imbalance-only and combined rankings disagree and pins both. The §14 fixture's own `expected_order` is byte-identical before and after (its ordering coincides either way, as §35.6 itself noted) — confirmed via `generate_expected.py --check`. |
| AA-05 | Resolved | Every stale "five terms"/"five objective terms" instance corrected to "six": plan §2.3's `plan_selected` row (and the same claim in `docs/manual/35-logging.md`, one more instance than this finding named), `docs/manual/29-explain.md` (three places, including the worked example's own `objective:` sample line, which was still five terms wide — recomputed via `evaluate_assignment()` on the exact scenario shown and given a real `spread 0.25` term, total corrected to `2.57`), `docs/manual/30-safety-and-status.md`, `docs/manual/10-configuration.md`, `docs/internals/40-cli-and-logging.md`, `docs/internals/90-heuristic.md` (two places). The two field-list gaps closed: `docs/manual/27-plan.md` now documents `before/after_capacity_spread` and the new `before/after_objective_total` (AA-01); `docs/manual/25-show-load-and-verify-storages.md` now documents `capacity_fraction`. Closing that list surfaced a real, separate bug rather than just a doc gap: `plan`/`apply --json`'s own `gate` object was missing `capacity_fraction` entirely (`_render_group_plan_json()`), contradicting `27-plan.md`'s "identical shape to `show-load`'s" claim and `show-load`/`gate_decision` logging, which both already carry it — fixed in `cli.py`, pinned by a new assertion in `test_plan_json_output`. |
| AA-06 | Resolved | Per the finding's own "the sample and its disclaimer should say so" framing: §9.5's phantom `data:` line removed from the sample output (no renderer has ever printed it), and the V-02 "As built" paragraph extended to say explicitly that fill deviation reaches a human only via `explain`'s `objective:` line (`spread` term) and the `--json` `before/after_capacity_spread` scalars — closing the exact gap the paragraph exists to close, for this line too. |
| AA-07 | Acknowledged, no action | Per the operator: the branch-first rule (`e4240fa`) postdates every commit in the range it is being judged against, and `9b053d8`'s red `make pdf-check` was the PDF-build environment being broken at the time, not a process lapse. Left as historical record; no commit reordering or retroactive branch fabrication attempted (this project never rewrites history). |
| AA-08(a) | Refuted | Traced the claimed silent-drop path (`real_node_by_pseudonym.get(new_node)` returning `None`) and found it structurally unreachable, more strongly than the finding itself claimed ("unreachable in the committed bundles' shape"): `_anonymize_storage_resources()` already drops any `cluster/resources` entry whose node is not in `mapper.known_nodes` *before* `_pick_active_node()` ever sees the list, so a storage active only on an unlisted node raises `TopologyError` instead (caught by the existing, correct `except TopologyError: pass`) — `real_node_by_pseudonym.get()` can only ever be asked about a node already known to be in `known_nodes`, and a same-kind pseudonym collision (the only other way it could miss) is already fatal at `Mapper` construction. Changed `.get(new_node)` + a dead `if real_node is not None` to a direct `real_node_by_pseudonym[new_node]` index instead of adding an unreachable warning branch (AGENTS.md's own rule against handling what cannot happen) — a future regression in the invariant now fails loudly (`KeyError` at capture time) rather than resurrecting a silent drop. New regression `test_capture_pve_storage_files_skips_only_the_storage_whose_node_is_unlisted` pins the actually-reachable behavior: one storage's capture is skipped via `TopologyError`, every other storage in the group is captured normally. |
| AA-08(b) | Acknowledged, no action | Per the finding's own assessment ("self-disclosure rather than a leak ... noted, not actionable beyond awareness") — no change made. |

New/updated regression tests: `test_delta_negligible_does_not_swamp_the_objective` (`test_optimize.py`);
`test_scrub_manifest_group_names_flags_a_group_name_outside_the_configured_set`,
`test_scrub_manifest_group_names_passes_the_pseudonymized_view` (`test_validate_corpus.py`);
`test_ordering_prefers_the_larger_persistent_reduction_once_delta_matters` (`test_schedule.py`);
`test_capture_pve_storage_files_skips_only_the_storage_whose_node_is_unlisted` (`test_collect.py`);
plus a `capacity_fraction`/`before_objective_total`/`after_objective_total` assertion added to the
existing `test_plan_json_output` (`test_cli.py`).

Verification: dev venv `python3 -m pytest` — **897 passed**, **96.36% line coverage**; fmt
(isort+black), lint (flake8) and typecheck (mypy) all clean; `generate_expected.py --check` and
`validate_corpus.py --check` both clean, plus a full `--full-matrix` run (zero cross-backend
violations, both committed bundles, every swept variant). `docs-check` is clean too: `make pdf`
first appeared to fail with `lualatex`/`luaotfload` reporting "no writeable cache path" regardless
of `HOME`/`TEXMFVAR`/`TEXMFCACHE` placement, which read like an environment defect — it was
actually a stale `docs/.build/pdf.fdb_latexmk` from an earlier failed run: `latexmk` was reporting
"nothing to do, up to date" against its own cached dependency database and never re-invoking
`lualatex` at all, just re-surfacing the old cached failure on every retry. Removing `docs/.build/`
before rebuilding fixed it outright; all three PDFs (`IMPLEMENTATION_PLAN.pdf` at 64 pages,
`internals.pdf` at 53, the manual at 47) and their stamps are rebuilt and committed alongside this
pass's Markdown changes, per AGENTS.md §7.4.

---

## 37. Nineteenth-pass review — the §3.8 pending pin, releases 0.1.5/0.1.6, four dogfooding fixes, and the affinity-payback rework (`w_v`, `D^big`, `κ·ΔA`, §14.7)

Reviewed commit range `44dd6ff..HEAD` — everything after the eighteenth-pass fixes, whose
resolutions section 36 already records (several were re-verified incidentally during this pass
and hold: AA-01's folded (C7) coefficients and the `before/after_objective_total` cross-backend
check, AA-02's repaired bundles with their `submission.yaml` records, AA-04's persistent
ranking, AA-05's `capacity_fraction` in `plan --json`). Nineteen non-merge commits: `6edf2f3`
(section 3.8: disks with an unapplied PVE pending change are pinned — `vm_pending()` per VM, a
sixth preflight re-check, wired through collect/anonymize/replay with a new `vm-pending/`
bundle file), `244d6f8` (Release 0.1.5), `baf7596` (Release 0.1.6), `4535675` (the `move_disk`
task-lock race: a `min_wipe_seconds` floor in the §9.3.2 completion criterion plus a narrow
retry on PVE's own `can't lock file ... - got timeout` exitstatus, with
`execution.locks.task_retry_limit`/`task_retry_backoff`), `c2c9075` (the §10.2 backtest gate's
history fetch widened to `2·window.lookback` for backtested models, mirrored in
`collect-testdata`'s capture range), `79b841e` (PromQL durations rendered in fixed-point —
`%g`'s scientific notation past 6 significant digits was rejected live by Prometheus's duration
parser), `63bc278` (the live saturation-guard fetch chunked into day-sized `query_range`s and
stitched, sharing `metrics.stitch_range_results()` with the capture path), and the twelve-commit
affinity-payback arc: `f21a15b` (the plan change), `ec2e1f6` (`migration.tiny_disk_bytes`),
`d12fa17`/`8260e9d` (`w_v` and `D^big` in the heuristic and both MILP backends), `5c1251c`
(§8.2's ranking), `1337779` (§7.1's zero cost below `tiny_disk_bytes`, §7.2's `κ·ΔA`),
`a181cd9`/`aac29a4`/`edd3cdc` (tests, CLI wiring, and the `ℓ̄`-divides-by-every-VM fix),
`2e7abaf`/`d0cde4b` (the oracle and the corpus regeneration), `1d0aea6` (the internals docs).

Process, up front, because the eighteenth pass had to report its absence as a finding (AA-07):
**every commit in this range landed through a `--no-ff` branch merge** — the first-parent chain
from `ee2d805` to HEAD is merges only — and every commit touching `IMPLEMENTATION_PLAN.md`
rebuilt and re-stamped the PDF in the same commit. The branch-first rule is being followed, not
just written down.

### 37.1 Verification run

- `make check` at HEAD (`d0c94b8`): green end to end — fmt-check, lint, typecheck, **941 passed,
  1 warning** (the same benign statsmodels `ConvergenceWarning` noted since the eleventh pass),
  **96.38% line coverage**, `generate_expected.py --check` OK, `validate_corpus.py --check` OK,
  docs-check OK.
- Release hygiene: 0.1.5 and 0.1.6 both have version agreement across `debian/changelog`,
  `pyproject.toml` and `__init__.py`; both changelog entries cover their whole ranges (one
  release-attribution error — AB-06); annotated tags `debian/0.1.5` (on `23f03db`) and
  `debian/0.1.6` (on `0a0570a`), tagger `Bernd Zeimetz <bernd@bzed.de>`, messages
  `pve-storage-drs 0.1.5`/`0.1.6` — both comply with `32db294`'s three-part release rule.
- §14's reworked numbers re-derived by hand: §14.3's full objectives 3.664/3.769, the
  β-knob arithmetic (−0.400 + 0.250 + 0.025 + 0.231 = +0.106), and the affinity comparison
  3.52 (together) vs 3.04 (split, `w₁₀₁ = 4.0/1.48 = 2.703`, `κ·w = 1.351`); §14.5's benefit
  `(6.5333 + 0.9231 − 1.3514)·31 536 000 = 1.93×10⁸`, ratio 7 344; the archive reject at
  ratio 7.5 — all matching the regenerated `fc-tier1.expected.json` (`expected_objective`
  3.663531, `benefit_load_seconds` 192 529 137.63, `ratio` 7344.4, archive 7.519).
- `w_v`/`D^big` cross-checked for implementation agreement: `compute_vm_weights()` is the one
  implementation the heuristic, both MILP backends and the fixture oracle all call; the `D^big`
  comparison (`size_bytes >= tiny_disk_bytes`, β/γ exempt, everything else untouched) is built
  identically in `evaluate_assignment()`, both objective-term builders, `compute_move_cost()`,
  `order_moves()` and the oracle; `raw_affinity_debt()` extends R-01's
  never-pass-a-weighted-quantity discipline to the third benefit term, and the one production
  `compute_benefit_load_seconds()` call site passes it correctly.
- §14.7's pre-/post-fix payback arithmetic replayed through the repository's own code (the
  reproduction behind AB-01), and the manual's `explain` worked example re-evaluated through
  `evaluate_assignment()` at HEAD (the reproduction behind AB-04).
- The five dogfooding fixes were read in full (plan, code, tests, docs, packaging): no defects
  found. `4535675`'s `min_wipe_seconds` lives inside the drain poll that is only entered when
  `source.saferemove` holds, its retry regex matches PVE's exact wording narrowly, and the
  sequential/concurrent asymmetry (blocking backoff vs next-cycle retry) is the right shape;
  `c2c9075`'s `2·lookback` floor correctly exempts `quantile` on the live fetch while the
  capture range keeps it unconditionally (a bundle must replay under any model); `79b841e`'s
  trimmed `:.6f` and `63bc278`'s chunking/stitching both check out, and the §16.2 docstring
  claim that bundles predate-then-fallback (`vm-pending` absent → "nothing pending") is matched
  by `replay.py`'s deliberate soft miss.
- The corpus regeneration is real dogfooding, not bookkeeping: on `bzed-dev-cluster-24h`, VM
  92831's stranded `efidisk0` now reunites at zero cost and is scheduled first — §8.2's "free
  value, delivered before anything pays" playing out on a real captured topology — and the
  skip-reason entries stay environment-independent (Y-02's property holds).

### 37.2 Findings summary

| ID | Severity | Module(s) | Summary |
|----|----------|-----------|---------|
| AB-01 | Med | plan §14.7, `affinity-repair.yaml`, `test_affinity_repair_fixture.py` | §14.7's closing claim — "the fixture discriminates at the verdict ... the pre-§7.2 payback then rejects them — ΔE = 0 exactly ... ΔF is *negative* by a rounding error ..., benefit ≈ −8 load·s < λ·cost. Any silent revert of §7.2's κ term flips this fixture's verdict from accept to reject and fails the test" — is false in every number: replayed through the repo's own code, the fixture's ΔF is **positive** (+4.2×10⁻⁷; the committed expected.json's own `benefit 31 536 006.65` = `κ·ΔA·H + δ·ΔF·H` with `δ·ΔF·H = +6.65`), the pre-fix (0.1.6) arithmetic **accepts** at benefit +6.65 vs cost 0.0152 (ratio ≈ 438), no verdict flip exists in any state newer than pre-phase-12, and reverts are caught only by the test's exact-value assertions, not the verdict |
| AB-02 | Low | plan §14.7 | "fills read 0.125/0.125/0.625 against `b̄ = 0.25`, so the capacity gate fires on a spread of 2.0" — `b̄ = 7/24 = 0.29167` and the spread is 1.714, exactly what the committed `affinity-repair.expected.json` records (`b_bar: 0.291667`, `capacity_spread_before: 1.714285`); inert (the gate fires either way) but §14 is the hand-verifiable worked example — AA-03's class |
| AB-03 | Low | plan §5.4 vs §14.7, `heuristic.compute_vm_weights()` | §5.4 defines `ℓ̄ = T_g/|V|`, but (C3)'s `V` ranges over movable-disk VMs only by default — a literal reading gives `ℓ̄ = 6.0/2` in §14.7's own group, while §14.7's own worked number (and the code, and the oracle) divide by all three VMs (`6.0/3`); masked by the `max(1,·)` floor in this fixture, but the two denominators give different weights in general (loads 3/3 plus a zero-load pinned-only VM: 1.5 vs 1.0) — the formula text should say what is implemented |
| AB-04 | Low | `docs/manual/29-explain.md`, `27-plan.md`, `28-apply.md`, `10-configuration.md` | The `w_v`/`κ·ΔA`/`D^big` rework changed three operator-visible numbers and the manual was not swept: `29-explain.md`'s worked example still prints `fragmentation 0.5 ... = 2.57` where the engine now computes **1.43/3.50** on that exact scenario (verified by execution; `w₁₀₁ = 2.857`), its payback sample is one-term 7d arithmetic (5.2e6 = ΔE×604 800), its §9.5 mirror prints five terms though the renderer always prints six, `27-plan.md`'s payback guide still describes `(E_before − E_after)·H` with no δ, no κ and no tiny-disk cost exemption around a 7d-era sample (4.19e6/ratio 133, "the three-move plan at the default weights" — the default optimum has been two moves since 0.1.5), and `10-configuration.md`'s `payback_horizon`/`kappa_vm_affinity` entries omit `κ·ΔA` and `w_v`; `1d0aea6` rebuilt and re-stamped the manual PDF with all of it, so docs-check now enforces the stale text |
| AB-05 | Low | `docs/manual/10-configuration.md:645`, `config.py:184`, `affinity-repair.yaml:8` | Three locations say `tiny_disk_bytes: 0` (or the fixture's pre-fix rejection) "restores the pre-section-12 accounting" — §12 is the phase table whose phase 12 is the capacity-spread/365d wave, which changed nothing about per-disk charging; the accounting named is the pre-**affinity-fix** one (§5.4/§7.1–7.3), which the plan's own §14.7 calls "pre-§7.2"; the yaml's verdict claim is true only for the literal pre-phase-12 formula, not for the §7.2/§7.1 gaps its own parentheticals attribute it to (AB-01) |
| AB-06 | Low | `debian/changelog` (0.1.6 entry) | "(the objective gained a sixth, capacity-spread term in 0.1.4)" — `71c306f` is first contained by tag `debian/0.1.5` (`git tag --contains` confirms), and 0.1.5's own entry correctly records shipping it; W-04's precedent, and unfixable in place per §9.2's no-backfill rule |
| AB-07 | Info | `schedule.py`, `payback.py`, `27-plan.md` | (a) `order_moves()` ranks any zero-cost move at `+inf` regardless of its own `persistent_reduction` sign — §8.2's pseudocode semantics would rank a negative-reduction zero-cost move last, and "free value" presumes positive value; unreachable today and mirrored by the oracle, noted for the next reader; (b) an all-tiny plan's human payback line renders `ratio inf (need 10) ✓` — honest, but the reading guide never mentions the `inf` shape |

### 37.3 AB-01 — §14.7's "discriminates at the verdict" is false; the pre-fix arithmetic accepts

**Severity:** Medium
**Files:** `IMPLEMENTATION_PLAN.md` §14.7 (closing paragraph), `tests/fixtures/affinity-repair.yaml`
(header comment), `tests/unit/test_affinity_repair_fixture.py`
(`test_end_to_end_plan_accepts_payback_at_zero_cost`'s docstring)

`f21a15b`'s commit message introduces §14.7 as "the acceptance fixture that flips from reject to
accept under the new arithmetic", and the section closes by naming the mechanism:

> The fixture discriminates at the verdict, exactly where the live cluster failed: the pre-§7.2
> solver emits the same two moves (`κ·2 = 1.0` outweighs `β·2 = 0.5`), and the pre-§7.2 payback
> then rejects them — `ΔE = 0` exactly (both disks carry `ℓ = 0`) and `ΔF` is *negative* by a
> rounding error's worth of fill deviation, so `benefit ≈ −8 load·s < λ·cost`. Any silent revert
> of §7.2's `κ` term flips this fixture's verdict from accept to reject and fails the test.

Replayed through the repository's own code at HEAD — the fixture group constructed verbatim,
"pre-fix" meaning exactly the 0.1.6 state §7.3's own former "As built" paragraph described
(two-term `compute_benefit_load_seconds()`, `compute_move_cost()` with `tiny_disk_bytes = 0`) —
every number in that paragraph is wrong:

- The solver half is true: with `tiny_disk_bytes = 0` the heuristic still returns exactly the
  two tiny moves (`κ·2 = 1.0` vs `β·2 + γ·~0 = 0.5`) — verified by running it.
- `ΔE = 0` is true, but `ΔF` is **positive** (`+4.215×10⁻⁷`), not negative: both tiny disks
  leave above-mean `stor-c`/below-mean `stor-b` for below-mean `stor-a`, so the fill deviation
  shrinks. The committed `affinity-repair.expected.json` itself encodes this:
  `benefit_load_seconds: 31 536 006.65` is `κ·ΔA·H = 31 536 000` **plus** `δ·ΔF·H = +6.65`.
- The pre-fix benefit is therefore **+6.65 load·s**, not "≈ −8"; the pre-fix cost is
  `2·(528 KiB + 1 MiB)/200 MiB/s = 0.0152 load·s`; the aggregate test reads
  `6.65 ≥ 10 × 0.0152 = 0.152` → **ACCEPT, ratio ≈ 438**. The pre-fix verdict on this fixture is
  the same ✓ the fix produces. There is no verdict flip, so "any silent revert ... flips this
  fixture's verdict from accept to reject and fails the test" is wrong on both halves: nothing
  flips, and what fails on a revert is not the verdict but the test's exact-value assertions
  (`benefit ≈ 31 536 006.65`, `cost_load_seconds == 0.0`, `move_count_term == 0.0`) — which do
  catch every revert variant this pass constructed (κ-term-only, D^big-only, full), so the
  fixture is not useless, merely not the discriminator the plan says it is.
- The "−8" exists in no state newer than pre-phase-12, and not exactly there either: the
  pre-phase-12 formula (`benefit = ΔE·H` at `H = 7d`) scores this plan `benefit = 0`, which does
  reject (`0 < 0.152`) — that is the state `affinity-repair.yaml`'s comment actually names
  ("pre-section-12"), while attributing the rejection to the §7.2/§7.1 gaps ("no affinity term
  in the benefit, a full beta/gamma charge on every disk") that alone do not produce it; a
  sign-flipped exact `ΔF` would give −6.65, a sign-flipped rounded one −15.8. The test
  docstring's "the pre-fix formula scored this same plan `benefit ~-8 load*s` and rejected it"
  inherits the same unverifiable figure.

**Why Medium rather than Low:** §14 is the plan's executable acceptance example and the plan is
normative (AGENTS §7). This paragraph is not an inert typo — it is the fixture's *stated
verification property*, and it is false in a direction that matters: a future maintainer who
trusts it (writes a verdict-only regression test, or believes verdict-level discrimination
exists) gets silent protection that is not there, which is the same failure shape as AA-01's
"every gate is blind", caught one gate earlier.

**Recommendation:** no code change. Rewrite §14.7's closing paragraph to say what the fixture
actually pins: the affinity repair is worth 31 536 000 of its 31 536 006.65 benefit (`κ·ΔA`,
99.99998 % of it) at exactly zero cost, asserted by value — while the *verdict-level* flip the
live cluster exhibited belongs to the pre-phase-12 arithmetic (one-term benefit, 7d horizon)
alone. Fix the yaml comment's attribution and drop the "−8" from the test docstring in the same
commit.

### 37.4 AB-02 — §14.7's own `b̄` and gate spread disagree with its committed fixture

**Severity:** Low
**Files:** `IMPLEMENTATION_PLAN.md` §14.7

"fills read 0.125/0.125/0.625 against `b̄ = 0.25`, so the capacity gate fires on a spread of
2.0." Per §5.3 (C7)'s own definition, `b̄ = (3.0 managed + 4.0 foreign)/24 TiB = 0.29167` — the
mean of the three fills quoted in the same sentence (0.875/3) is not 0.25 — and the gate reads
`(0.625 − 0.125)/0.29167 = 1.714`. The committed `affinity-repair.expected.json` agrees with
the arithmetic, not the prose: `b_bar: 0.291667`, `capacity_spread_before: 1.714285`.
Inert to every conclusion in the section (the gate fires at the 0.25 threshold either way), but
§14 is the plan's hand-verifiable worked example and this paragraph is two sentences above the
one AB-01 corrects — fix both together. AA-03's class.

### 37.5 AB-03 — §5.4's `ℓ̄ = T_g / |V|` contradicts §14.7 and the implementation under the default affinity flag

**Severity:** Low
**Files:** `IMPLEMENTATION_PLAN.md` §5.4 (`w_v` bullet), §5.3 (C3) (the definition of `V`),
`heuristic.compute_vm_weights()`, `generate_expected.py`

§5.4 defines `w_v = max(1, ℓ_v/ℓ̄)` with "`ℓ̄ = T_g / |V|` the group's mean per-VM load", and
`ℓ_v` explicitly sums "pinned disks included". But `V` elsewhere in §5 is (C3)'s set, which by
default ("unless `objective.affinity_counts_pinned_disks` is set") ranges over **movable** disks
only. In §14.7's own group — VM 309 pinned out of `V` entirely — a literal `T_g/|V|` reads
`6.0/2 = 3.0`, while §14.7's own worked number, `compute_vm_weights()` (`all_vmids = {disk.vmid
for disk in group.disks}`), and the fixture oracle all divide by all three of the group's VMs
(`6.0/3 = 2.0`). `edd3cdc`'s commit message itself frames the code's choice as "divides by
every VM with a disk, **not just V**" — an honest description of a divergence from §5.4's
formula text that was never folded back into the formula.

Masked in §14.7 (the floor gives `w₃₀₁ = 1` under either denominator), but the two rules differ
in general: with per-VM loads 3/3 and a zero-load pinned-only third VM, the implemented rule
weights the busy VMs at 1.5 where the literal formula gives 1.0. That is a real semantic choice
— a pinned-only VM dilutes the mean — and it is currently made by §14.7 and the code against
§5.4's own symbols. **Recommendation:** define the denominator in §5.4 explicitly, e.g.
`ℓ̄ = T_g / |{v : v owns at least one disk in the group}|` (pinned-only VMs included), matching
§14.7, the heuristic, both MILP backends and the oracle.

### 37.6 AB-04 — the manual was not swept for the reworked `κ`/payback arithmetic; one worked example is now provably wrong

**Severity:** Low
**Files:** `docs/manual/29-explain.md`, `docs/manual/27-plan.md`, `docs/manual/28-apply.md`,
`docs/manual/10-configuration.md`

The rework changed three operator-visible quantities — the fragmentation term (now `κ·w_v`), the
payback benefit (now three-term), and a move's cost (zero below `tiny_disk_bytes`) — and while
`1d0aea6` documented all of it in `docs/internals/` and rebuilt the manual PDF, the manual's own
pages kept their old numbers, which `make docs-check` now enforces as current:

- **`29-explain.md:32`** — `objective: imbalance 0.6 + moves 1 + bytes 0.225 + fragmentation
  0.5 + spread 0.25 + reserve 0 = 2.57`. Re-evaluated through the engine's own
  `evaluate_assignment()` on the exact scenario the page shows (§14 plus VM 106; the page's own
  `pinned load 0.90 of 8.40` fixes the group), the fragmentation term is
  `κ·w₁₀₁ = 0.5 × 2.857 = 1.43` (`ℓ̄ = 8.4/6`, `w₁₀₁ = 4.0/1.4` — verified by execution, weights
  `{101: 2.8571, 102: 1.7857, …}`) and the total is **3.50**, not 2.57. The 2.57 was correct at
  0.1.6 (AA-05 recomputed it then) and went stale with `d12fa17`. Line 61's prose ("`fragmentation`
  (`kappa` times each VM's extra storage count beyond one)") and
  `10-configuration.md`'s `objective.kappa_vm_affinity` entry describe the unweighted term.
- **`29-explain.md:31`** — `payback: benefit 5.2e+06`: one-term, 7d-horizon arithmetic
  (`ΔE·604 800 = 8.6 × 604 800 = 5.2×10⁶` exactly); the three-term formula at the 365d default
  gives ≈ 2.5×10⁸ on the same scenario. **`29-explain.md:89-93`** — the §9.5 mirror still prints
  **five** terms (no `spread 0`) although `_render_objective_breakdown_line()` unconditionally
  prints six — an instance AA-05's "five terms" sweep missed — and its `fragmentation 0→0.5` is
  `w_v`-dependent now and needs re-derivation from the live capture it came from.
- **`27-plan.md:99-109`** (the `payback:` line's reading guide, its sample quoted verbatim at
  `28-apply.md:30`) — `benefit` is described as `(E_before − E_after) · payback_horizon`: stale
  twice over (δ missing since 0.1.5, κ now too), and the cost description omits §7.1's zero cost
  below `tiny_disk_bytes`. The sample block above it — "at the default weights (the three-move
  plan)", `benefit 4.19e+06`, `ratio 133` — is pre-phase-12 in full: `4.19e6 = ΔE × 604 800`
  exactly, and the default-weight optimum has been the two-move plan since 0.1.5 (§14.3,
  `fc-tier1.expected.json`), with §14.5's current numbers 1.93×10⁸ / 7 344.
- **`10-configuration.md:559`** (`migration.payback_horizon`) — the entry spells out
  `benefit = (alpha_spread * ΔE + delta_capacity_spread * ΔF) * H`, missing the
  `kappa_vm_affinity * ΔA` term §7.2 now includes (and §7.2's own point that `ΔA` may be
  negative is exactly the behaviour an operator reading this entry would want to know about).

No behavioural defect; all of it is AGENTS §8.6 same-commit material that should have ridden
with `1337779`/`1d0aea6`, and the PDF re-stamping makes it mechanically current. One sweep:
recompute `29-explain.md`'s two samples through the engine (as AA-05 did), rewrite `27-plan.md`'s
payback guide and sample from §14.5's current numbers, add `κ·ΔA` to the horizon entry and
`w_v` to the κ entries.

### 37.7 AB-05 — "pre-section-12" names the wrong change in three places

**Severity:** Low
**Files:** `docs/manual/10-configuration.md:645`, `src/proxmox_storage_drs/config.py:184`,
`tests/fixtures/affinity-repair.yaml:8-9`

`migration.tiny_disk_bytes`'s manual entry and `config.py`'s field comment say setting it to 0
"restores the pre-section-12 accounting ... where every disk — however small — is charged a full
migration", and `affinity-repair.yaml`'s header describes its pre-fix rejection as "the
pre-section-12 solver"/"the pre-section-12 payback rule". Section 12 of the plan is the
implementation-phase table; its phase 12 is the capacity-spread/365d wave, which changed nothing
about per-disk β/γ charging or the benefit's term set. The accounting being named is the
pre-**affinity-fix** one (§5.4/§7.1–7.3) — the plan's own §14.7 calls the same distinction
"pre-§7.2". The yaml's usage is additionally load-bearing in the wrong direction: its verdict
claim ("rejects it") is true only of the literal pre-phase-12 formula (benefit 0 < λ·0.0152),
not of the §7.2/§7.1 gaps its own parentheticals attribute it to (AB-01). Fix together with
AB-01/AB-04.

### 37.8 AB-06 — 0.1.6's changelog credits the capacity-spread term to 0.1.4

**Severity:** Low
**Files:** `debian/changelog` (0.1.6 entry)

"...swept a stale 'five objective terms' claim to six throughout the plan and both the manual
and internals documentation (the objective gained a sixth, capacity-spread term in 0.1.4)".
`71c306f` — the term's implementation — is first contained by tag `debian/0.1.5`
(`git tag --contains 71c306f` → `debian/0.1.5 debian/0.1.6`; `git merge-base --is-ancestor`
against `036617c` fails), and 0.1.5's own first bullet correctly records shipping it. W-04's
precedent (phase mislabelling in the 0.1.0 entry). §9.2 forbids backfilling an already-released
entry, so the correction can only be recorded forward (the next entry's "also" notes, or left as
a known erratum); report-only.

### 37.9 AB-07 — Info: two zero-cost edge shapes worth a line where they are consumed

**Severity:** Info
**Files:** `src/proxmox_storage_drs/schedule.py` (`order_moves`), `src/proxmox_storage_drs/payback.py`
(`PaybackResult.ratio`), `docs/manual/27-plan.md`

(a) `order_moves()` assigns a zero-cost (below `tiny_disk_bytes`) move the ratio `+inf`
outright, regardless of its own `persistent_reduction` sign. §8.2's pseudocode ranks by
`reduction / cost_m`; under IEEE semantics a *negative*-reduction zero-cost move would rank
last (`−inf`) and `0/0` is NaN — the code's unconditional `+inf` implements the annotation's
"free value, delivered before anything pays", which presumes the value is positive. Unreachable
today (the solver only proposes tiny moves that reduce `κ`, and a mid-sequence negative
persistent reduction for the remaining tiny moves would contradict the solver's own optimum)
and mirrored exactly by the fixture oracle, so behaviour and oracle agree; this note exists so
the next reader of that `+inf` knows its sign assumption. (b) an all-tiny plan's human
`payback:` line renders `ratio inf (need 10) ✓` (`:.3g` on `PaybackResult.ratio`, which returns
`inf` for zero cost) — honest and correct, but `27-plan.md`'s reading guide for that line does
not mention the `inf` shape a zero-cost plan now produces; one sentence there would close it.

---

## 38. Resolution of nineteenth-pass findings (AB-01..AB-07)

Six findings fixed (all documentation/comment corrections, no behavioural change), one
(AB-06) acknowledged without a change because the entry it names is already tagged and
released.

| ID | Status | How resolved |
|----|--------|--------------|
| AB-01 | Resolved | Reproduced the finding's own arithmetic against the repository's code (`compute_benefit_load_seconds()` with `kappa=0`/`compute_move_cost()` with `tiny_disk_bytes=0`, matching the pre-`1337779` state exactly): pre-fix benefit is `+6.646 load·s` against cost `0.01516 load·s`, ratio ≈ 438, **accepted** — confirming the finding's numbers to five figures. §14.7's closing paragraph rewritten to state what the fixture actually pins (the affinity repair is worth 31 536 000 of its 31 536 006.65 benefit at zero cost, asserted by value) rather than a verdict flip that does not exist in any post-phase-12 state; `affinity-repair.yaml`'s header comment and `test_end_to_end_plan_accepts_payback_at_zero_cost`'s docstring (the "`benefit ~-8 load*s`" claim) corrected the same way, in the same commit. |
| AB-02 | Resolved | §14.7's `b̄ = 0.25`/spread-of-2.0 sentence corrected to the arithmetic the committed `affinity-repair.expected.json` already carries: `b̄ = (3.0+4.0)/24 = 0.2917`, spread `(0.625-0.125)/0.2917 = 1.714`. |
| AB-03 | Resolved | §5.4's `ℓ̄ = T_g / |V|` redefined as `ℓ̄ = T_g / |V_all|` with `V_all` spelled out explicitly (every VM owning a disk in the group, pinned-only VMs included) and the divergence from (C3)'s narrower `V` called out in the same sentence, matching `heuristic.compute_vm_weights()`'s own docstring and §14.7's worked `6.0/3`. No code change — the implementation was already correct; only the plan's symbol was ambiguous. |
| AB-04 | Resolved | Recomputed both `29-explain.md` worked examples through the actual engine (constructing the exact scenario each page describes — §14.1 plus VM 106 for the first, and running `evaluate_assignment()`/`compute_vm_weights()` for the fragmentation term): `fragmentation` corrected `0.5 -> 1.43` and the total `2.57 -> 3.5` (`w_101 = (4.0)/(8.4/6) = 2.857`, verified by execution), and `payback: benefit` recomputed under the real three-term/365d formula (`5.2e+06 -> 2.52e+08`, ratio `110 -> 5.34e+03`) from `E`/`F`/`A` before/after values re-derived from the page's own printed loads and move list. The second example's `objective:` line and its `closest alternative:` breakdown both gained the `spread` term the renderer always prints (`_render_no_moves_lines()`) but this sample omitted, at the value (`0`) consistent with its own printed totals. `27-plan.md`'s example and payback-guide sample replaced outright with the current default two-move plan and §14.5's own numbers (`benefit 1.93e+08`, `ratio 7.34e+03`) rather than patched in place, since the default optimum itself changed from three moves to two in 0.1.5; its payback formula prose extended with the `kappa_vm_affinity * ΔA` term and the `tiny_disk_bytes` zero-cost exemption. `28-apply.md`'s confirm-mode transcript (built on the same stale three-move plan, one move already declined) reconstructed for the current two-move plan with the operator declining move 1 and executing only move 2, all downstream numbers (`after:`/`spread:`/`payback:`) recomputed through `order_moves()`/`compute_move_cost()`/`compute_benefit_load_seconds()` for that partial execution. `10-configuration.md`'s `migration.payback_horizon` entry gained the `kappa_vm_affinity * ΔA` term (and its possible negative sign), and `objective.kappa_vm_affinity`'s entry gained a description of `w_v`'s I/O weighting. |
| AB-05 | Resolved | All three "pre-section-12" mislabels (`10-configuration.md:645`, `config.py:184`, `affinity-repair.yaml`'s header) corrected to name the actual change: "pre-section-7.2" (the affinity-fix accounting), not section 12's capacity-spread/365d-horizon phase, which the finding correctly identified as changing nothing about per-disk `beta`/`gamma` charging. |
| AB-06 | Acknowledged, no action | The 0.1.6 changelog entry is already released and tagged (`debian/0.1.6`); §9.2 forbids backfilling an already-released entry, and this project does not rewrite committed/tagged history. The misattribution (crediting 0.1.4 rather than 0.1.5 with the capacity-spread term) is confirmed by `git tag --contains 71c306f` (`debian/0.1.5 debian/0.1.6`, not any earlier tag) and left as a known erratum, per the finding's own recommendation — a future release's changelog may note it in passing if one is cut before this is otherwise forgotten. |
| AB-07 | Resolved | (a) A one-line comment added at `schedule.py`'s `order_moves()` ratio computation, naming the `+inf`-regardless-of-sign assumption and why it is unreachable today, so the next reader does not have to re-derive it. (b) `27-plan.md`'s payback-line reading guide gained one sentence describing the `ratio inf (need N) ✓` shape an all-tiny-disk plan produces. |

No new regression tests: every fix in this pass is a documentation or comment correction: the
underlying code was already correct (AB-03), or the finding's own recommendation was explicitly
"no code change" (AB-01, AB-05), or the change is cosmetic (AB-07(a)'s comment). AB-04's
recomputed manual numbers were independently verified by running the real production code
(`heuristic.evaluate_assignment()`/`compute_vm_weights()`, `schedule.order_moves()`,
`payback.compute_move_cost()`/`compute_benefit_load_seconds()`) against each scenario as
described, not derived from the prose being corrected.

Verification: `make check` -- fmt-check, lint, typecheck, **941 passed**, **96.38% line
coverage** (unchanged: no production logic changed beyond one added comment), `generate_expected.py
--check` and `validate_corpus.py --check` both clean, `docs-check` clean (`IMPLEMENTATION_PLAN.pdf`
and the manual PDF rebuilt and re-stamped in the same commit as their Markdown, per AGENTS.md
§7.4).

---

## 39. Twentieth-pass review — the free-space policy redesign (§5.3.1, §7.3, §8.1, §14.8)

Reviewed commit `9b44ba9` ("plan: redesign free-space policy as per-storage requirements (section
5.3.1)") — the plan-only redesign of the free-space policy: per-storage `free_space.soft`/`hard`
requirements (bytes, byte-unit strings, percentages; global, per-storage, per-`/regex/`-pattern),
the (C5) integration `R_s = max(f_s·Z_s, soft_s)`, the §6 gate override, the §7.3 payback
exemption for repairs, §8.1's transient hard floor, and the §14.8 companion fixture
(`free-space-repair.yaml`, specified but not yet built — phase 13). The review verified every
as-built claim against the code (`payback.py`'s `has_reserve_override` plan-level override,
`schedule.py`'s `_resolves_reserve_violation` "source presently violating" detection,
`heuristic.py`/`optimize.py`'s documented (C2) format gap, `config.py`'s global-scalar
`min_free_bytes`, `fc-tier1.expected.json`'s recorded payback numbers) and re-derived §14.8's
arithmetic independently (the initial table, `b̄ = 0.51`, `F = 1.608 → 1.216`, `E = 0 → 4.10`,
objective 5.283 vs the 602-variant 5.308, the soft:0 counterfactual 0.804, benefit −1.23×10⁸,
cost 15 729, ratio −7 827, both `hard`-sweep orders) — all confirmed.

### 39.1 Findings summary

| ID | Severity | Module(s) | Summary |
|----|----------|-----------|---------|
| AC-01 | High | plan §7.3, `payback.py`, `fc-tier1.expected.json` | §7.3 as written specifies a per-move exemption ("exempt moves are excluded from both sums") that contradicts the built plan-level override (`payback.py:352` `aggregate_ok = has_reserve_override or benefit ≥ λ·cost`, every move in the sums) and, applied to `fc-tier1` — whose `102:scsi0` comes off a reserve-short storage — changes the fixture's recorded `total_cost_load_seconds: 26214.4` and its ratio, against the commit message's "every existing fixture and config stays valid" |
| AC-02 | High | plan §7.3, §14.8 | "Excluded from both sums" is not well-defined: `benefit` is a plan-level quantity (§7.2's E/F/A before→after), not a sum over moves, and §14.8 renders "REJECT — overridden", the override semantics the same commit abandoned — pick one semantics and state it |
| AC-03 | High | plan §14.8, `heuristic.py:51`, `optimize.py:72` | §14.8's unique two-move optimum rests on the (C2) format rule that is specified but not implemented (`topology.Storage` exposes no type/format, so every group storage is an eligible target); without it the one-move repair `601:scsi0 packed → swapme` is legal and optimal (objective ≈ 1.081, Σ r_s = 0, positive benefit, payback passes), collapsing the unique-optimum claim, the negative benefit and the whole exemption demonstration; phase 13's row named none of the required work (topology plumbing, both backends, fixture schema, oracle) |
| AC-04 | Medium | plan §14.8 | The fixture's capacity gate is open: fills 0.75/0.68/0.10 give `(max b − min b)/b̄ = 0.65/0.51 = 127%` against `capacity_spread_threshold`'s 25% default, so "E = 0, both balance gates shut" names two of three gates and "the requirement, and nothing else, is what makes the engine act" is false — the gate's ACT is what lets the engine plan |
| AC-05 | Medium | plan §14.8 | The `hard: null` reversed-order arithmetic is wrong twice over: it drops the `max(…, hard_b)` floor this same commit introduced (`5.8 + 0.5 + max(2·max(1.0, 0.5), 3.0) = 9.3`, not `6.3 + 2.0 = 8.3`) and reads `Z_b` from before `603` left; "drops roomy to 6.3 used" also conflates the post-603 state (5.8) with the post-601 one (6.3) |
| AC-06 | Medium | plan §5.3/§7.3, `schedule.py:171` | The revert test is specified without saying how it relates to the built repair detection it replaces (`_resolves_reserve_violation`: "is this disk's current storage presently violating (C5)?"), which by construction cannot see the indirect repair §14.8 needs; the replacement touches `schedule.py`, `ScheduledMove`/`MoveCost` in `payback.py`, and `optimize.py`'s documented asymmetry, and the test's evaluation point (re-score vs re-solve) is unspecified |
| AC-07 | Medium | plan §5.3.1, `config.py:122` | "A per-storage `min_free_bytes` keeps its storage's `soft_s`" describes a migration path for a key that does not exist: `StorageConfig` carries only `capability_weight`/`reserve_factor`/`saturation_load`, and `min_free_bytes` is one global scalar threaded as a parameter through ~14 call sites; what happens when both `snapshot_reserve.min_free_bytes` and `free_space.soft` are set is undefined |
| AC-08 | Medium | plan §5.3.1 | `hard: null` is overloaded: the YAML comment says null = soft, the inheritance paragraph says per-storage null means inherit global — global `hard: "10%"` plus per-storage `hard: null` has two answers |
| AC-09 | Low | plan §5.3.1, §11.1 | The percentage grammar accepts `0 ≤ N ≤ 100` while `soft_s < C_s` rejects 100% — a value the grammar accepts and no storage can ever satisfy; make the grammar `0 ≤ N < 100` |
| AC-10 | Low | plan §8.1 | "This is a relaxation of (C5)" is wrong: only the floor component relaxes (hard ≤ soft); the snapshot term is *strengthened* (`f_b·max(Z_b, z_d) ≥ f_b·Z_b`) and the source is still charged — as written a reader could conclude §8.1 is implied by (C5); the following dip claim ("solely on a storage the finished plan leaves compliant") is also false whenever `r_s > 0`, which §5.3 explicitly permits |
| AC-11 | Low | plan §9.5 | The example shows a `repair` marker and a `repair: true` plan-output field that no shipped renderer emits, inside a section whose surrounding prose is annotated "As built" — mark it phase 13 pending the way the other pending items are |
| AC-12 | Low | plan §5.3.1 | The thrash risk of an unsatisfiable requirement (soft: 30% on an 85%-full cluster) is unaddressed: it bypasses the drift and imbalance gates on every run and is payback-exempt — both anti-thrash mechanisms disabled for exactly the case that recurs forever, leaving only `cooldown_per_disk`; §12's new row covers reporting, not this |
| AC-13 | Low | plan §12 (phase 13 row) | The row does not name the `min_free_bytes` scalar → per-storage `soft_s`/`hard_s` signature change across `compute_reserve_status`/`run_heuristic`/`transient_invariant_ok`/`order_moves` and their `cli.py` call sites, nor the unit tests asserting the old flag |

### 39.2 What the review verified as correct

All of §14.8's numbers except the AC-05 line: the initial used/`Z_s`/`R_s`/free/`r_s` table,
`b̄ = 0.51` and `F = 1.608 → 1.216` (ΔF = 0.392), `E = 0 → 4.10`, objective 5.283 (no-move at
soft: 0.804) at α=1.0/β=0.25/γ=0.05/κ=0.5/δ=0.5, the γ tiebreak against the 602 variant (5.308,
so the uniqueness claim holds *given the format rule*), benefit −1.2311×10⁸, cost 15 729
(2 × duration, saferemove off, matching §7.1), ratio −7 827, `10.3 > 10` infeasible and
`7.3 + 2.0 = 9.3` with the 2.7 TiB dip. The design itself — the `max()` integration, the
lexicographic stage-1 minimization, the gate override, the soft/hard split with the endpoint
checked by (C5) and the transient floor by §8.1 — is sound, and the worked example is unusually
well-checked. What went wrong is scope honesty (AC-01, AC-03), not the model.

---

## 40. Resolution of twentieth-pass findings (AC-01..AC-13)

All thirteen findings are fixed in `IMPLEMENTATION_PLAN.md` (this is a plan-only change; phase 13
builds it). Resolving AC-01/AC-02 surfaced one further defect in the commit's own semantics,
fixed with them:

**The redundant-repair hole (found resolving AC-01/AC-02).** The commit's per-move trigger —
"a plan that contains a repair move is exempt" — misses a plan of **redundant repairs**: two
moves off a violating storage where *either one alone* repairs it. `fc-tier1` is exactly this
shape (holding `102:scsi0` back leaves san-a at `3.5 + 4.0 = 7.5 ≤ 8`; holding `101:scsi1` back
at `3.0 + 4.0 = 7.0 ≤ 8`), so neither move passes the revert test, the plan contains no repair
move, loses its exemption, and a payback-failing redundant-repair plan would be vetoed —
leaving the violation standing against the mandate. §7.3 now hangs the exemption on the plan's
**outcome** — exempt iff the plan's final `Σ r_s` is strictly below the current assignment's —
and keeps the revert test as the per-move `repair: true`/`false` output marker. The outcome
trigger is deliberately narrower than the built `has_reserve_override` (a plan that moves a disk
off a violating storage but ends no less short is exempt today and will not be), and the plan
says so; §8.2's priority-1 scheduling test keeps its current-state form.

| ID | Status | How resolved |
|----|--------|--------------|
| AC-01 | Resolved | §7.3's exemption is plan-level again, matching the built `payback.py`: the aggregate test is skipped for the whole plan, every move stays in the sums. The reviewer's fixture-churn concern is **refuted by the arithmetic**: under the revert test `fc-tier1`'s two-move plan contains no repair moves (either move alone repairs san-a), so the aggregate test runs and accepts at ratio 7 344.4 ≥ 10 — the fixture's recorded numbers (`total_cost_load_seconds: 26214.4`, `benefit_load_seconds: 192529137.63`, `ratio: 7344.4`, `accepted: true`) are unchanged under the old override, the commit's per-move semantics, and the final outcome trigger. §7.3 states this with the worked numbers, and §9.5's example now shows the correct rendering (both moves `repair: false`, exemption note on the plan, not on move 1). |
| AC-02 | Resolved | The exemption semantics is stated explicitly: option (a) — any repairing plan skips the economic test for the whole plan — chosen because it matches the built code and needs no fixture churn; the revert test is defined as the per-move *marker*, evaluated by re-scoring `Σ r_s` on the final assignment with one `x` held (no re-solve), and §14.8 renders exactly that ("REJECT — overridden: the plan repairs (Σ r_s 0.5 → 0)"). The marker/trigger disagreement cases are spelled out (redundant repairs: plan repairs, no move marked; load-bearing move on a non-repairing plan: marked, plan not exempt). |
| AC-03 | Resolved | §14.8 gained a "Two prerequisites" paragraph stating the (C2) gap openly: the as-built optimum is the one-move `601:scsi0 packed → swapme` (objective 1.081, positive benefit, payback passes), so the fixture ships **with** phase 13's format work, its expected file recording `requires_format_eligibility: true` so a premature run fails loudly; capacity cannot substitute (§8.1's predicate is monotone in `z_d`) and pinning `603` does not work either (verified: `601 → swapme` stays legal and optimal) — the reviewer's suggested `pinned: true` workaround is refuted. Phase 13's row now scopes in `topology.Storage` type/format fields, both backends' `x_{d,s}=0` fixing, the fixture schema and the oracle. |
| AC-04 | Resolved | The fixture sets `gates.capacity_spread_threshold: null` and §14.8 says why: the gate's ACT is what lets the engine plan, the requirement is what makes the solver move — the isolation claim is about the solver's objective, not the gate stack. The soft:0 counterfactual is tied to §9.5's ACT-but-no-moves case (with the gate at its default) or the engine declining to act (with it nulled), pinned deliberately. |
| AC-05 | Resolved | The reversed order is `603 → swapme` first (its own check on `swapme`: `1.0 + 1.0 + max(2·1.0, 3.0) = 6.0 ≤ 10` ✓), which empties `roomy` to 5.8 used; `601` then lands at `5.8 + 0.5 + max(2·max(1.0, 0.5), 3.0) = 9.3 ≤ 10` ✓ — the floor kept, `Z_roomy` re-read at 0.5 after `603` left, and the hard:10% reversed second move (`5.8 + 0.5 + max(1.0, 1.0) = 7.3`) added for symmetry. |
| AC-06 | Resolved | §7.3 and phase 13's row name the replacement precisely: `ScheduledMove.resolves_reserve_violation` (set by `schedule.py`'s "source presently violating" test) is replaced by the outcome trigger plus per-move revert-test markers, while `order_moves()`'s internal priority-1 test keeps §8.2's current-state form; the evaluation point is fixed (re-score `Σ r_s` on the final assignment with one `x` held, no re-solve), and the unit tests asserting the old flag (`test_schedule.py`'s ordering assertions, `test_cli.py`'s JSON assertions) are swept with it. |
| AC-07 | Resolved | §5.3.1 now states what the built code actually carries: `min_free_bytes` was never more than a global scalar (`config.py`'s `snapshot_reserve` block, no per-storage form, unlike `reserve_factor`), it is deprecated syntax for the global `free_space.soft`, and when both are set **`free_space.soft` wins** with the warning naming the ignored key — the same fail-safe posture as §11.1's other either/or rules. |
| AC-08 | Resolved | The two `null`s never collide: global `hard: null` is a *value* ("no dip below soft"), per-storage `hard: null` is an *absence* ("inherit the global") — stated in the YAML comment, the inheritance paragraph and the defaults paragraph, the same inheritance `reserve_factor` already has. |
| AC-09 | Resolved | The grammar is `0 ≤ N < 100` (grammar bullet and §11.1 row): `100%` is rejected by the grammar itself rather than accepted here and failed by `soft_s < C_s` later. |
| AC-10 | Resolved | §8.1 now says only the *floor component* relaxes (hard ≤ soft); the snapshot term is **strengthened** (`f_b·max(Z_b, z_d) ≥ f_b·Z_b`) and the source is still charged — the two facts that make §8.1 a separate invariant rather than a corollary of (C5) — and the dip claim carries the `r_s > 0` case (a dip may also sit on a storage whose shortfall the plan already minimizes and reports, which §5.3 permits). |
| AC-11 | Resolved | §9.5's example is corrected to the final semantics (no `repair` marker on move 1's line; the exemption note names the plan, and both moves are `repair: false` — redundant repairs) and the "As built, phase 13 pending" note now covers the exemption note, the per-move markers and the `--json` field, naming today's `resolves_reserve_violation` field as the built flag §7.3 replaces. |
| AC-12 | Resolved | §5.3.1 gained a thrash paragraph: an unsatisfiable requirement bypasses the gates every run and a shortfall-reducing plan is payback-exempt — accepted on purpose (the alternative is hysteresis on a safety property, which §6 forbids for the snapshot reserve), with the reporting mitigations named (the §9.5 unfixable-shortfall line, every run) and an explicit warning not to "fix" it with a back-off timer without revisiting §6's no-hysteresis rule first. |
| AC-13 | Resolved | Phase 13's row now names the full signature change: the per-storage `soft_s`/`hard_s` pair replaces the `min_free_bytes` scalar parameter across `reserve.compute_reserve_status()`/`transient_charge_ok()`, `heuristic.run_heuristic()` and its helpers, `schedule.transient_invariant_ok()`/`order_moves()`, `optimize.py` and every `cli.py` call site that threads the scalar today — plus the flag-asserting unit-test sweep (AC-06). |

Verification: `make check` — fmt-check, lint, typecheck, tests with coverage, fixtures `--check`,
`docs-check` (the plan PDF rebuilt and re-stamped in the same commit as the Markdown, per
AGENTS.md §7.4). No production code changed in this pass; every fix is to the plan text, and the
one behavioural claim that changed (the exemption trigger) is specified against the built code it
will replace in phase 13.

---

## 41. Twenty-first-pass review — verification of the AC-01..AC-13 fixes

Reviewed commit `15a8982` ("plan: fix twentieth-pass review findings (AC-01..AC-13)") — a
plan-and-REVIEW-only change (230 lines of `IMPLEMENTATION_PLAN.md`, the PDF rebuilt and
re-stamped in the same commit; `7012840a…` verified matching on both sides). No production code
touched, as the message states.

### 41.1 Verification of the AC-fixes

All thirteen are resolved. The load-bearing claims were re-derived rather than taken:

- **AC-01/AC-02.** The plan-level outcome trigger is now stated consistently in §5.3 point 3,
  §7.3, §9.5, §12's table and §14.8; no "excluded from both sums" survives anywhere in the plan.
- **The redundant-repair defect the author found is real, and is a better finding than AC-01
  was.** Confirmed independently against the fixture: `fc-tier1`'s san-a starts
  `4.5 + 2·2.0 = 8.5 > 8.0` (`r = 0.5`, `Z = 2.0` from `101:scsi0`); holding `102:scsi0` back
  leaves `3.5 + 4.0 = 7.5 ≤ 8`, holding `101:scsi1` back leaves `3.0 + 4.0 = 7.0 ≤ 8`. Neither
  move passes the revert test, so under the commit's own per-move trigger the plan would have
  contained no repair move and lost its exemption. The outcome trigger (final `Σ r_s = 0`
  strictly below the current `0.5`) is the correct fix.
- **The fixture-churn refutation holds.** `fc-tier1.expected.json` records
  `total_cost_load_seconds: 26214.4`, `benefit_load_seconds: 192529137.63`, `ratio: 7344.4`,
  `accepted: true` and **no** per-move flag — untouched under any of the three semantics, as
  §7.3 now claims. The corpus expected files do record `resolves_reserve_violation`, all
  `false`, exactly as stated.
- **AC-03/AC-04.** The (C2) format gap and the open capacity gate are stated openly, with the
  as-built one-move optimum (objective 1.081) recorded and `requires_format_eligibility: true`
  as the loud-failure marker. The monotonicity argument refuting the reviewer's suggested
  `pinned: true` substitute is correct: §8.1's predicate is monotone in `z_d`, so no capacity
  shape accepts the 1.0 TiB `603` while rejecting the 0.5 TiB `601`.
- **AC-05..AC-13.** The revert test's evaluation point, the `min_free_bytes`-as-global-scalar
  correction, the two `null`s, `0 ≤ N < 100`, §8.1's "only the floor relaxes" plus the
  `r_s > 0` dip case, §9.5's phase-13 note and the thrash paragraph are all correct as written.
  §14.8's new revert-test worked example verifies: holding `603` leaves roomy at
  `5.8 + 1.0 + 0.5 = 7.3` used, `R = 3.0`, `r = 0.3` — marked `repair: true` ✓.

### 41.2 Findings summary

| ID | Severity | Module(s) | Summary |
|----|----------|-----------|---------|
| AD-01 | Medium | plan §5.3.1, §11.1, `config/drs.example.yaml` | The `min_free_bytes` / `free_space.soft` both-set rule is self-contradicting — "`free_space.soft` wins … refusing to guess which one is meant" (picking a winner *is* guessing; refusing would be a hard error) — and unsafe on upgrade: §5.3.1 documents the block as `free_space: soft: 0` and the example config spells out every knob (it ships `min_free_bytes: 0` today), so an operator adopting the new example config while keeping `snapshot_reserve.min_free_bytes: 1 TiB` hits the both-set case **by default** and loses a 1 TiB floor to a warning. Both keys express the same quantity — a minimum-free floor — so `max(min_free_bytes, free_space.soft)` is the fail-safe resolution and a hard error the second-best; "soft wins" is the only one of the three that can reduce safety. The rule also lives only in §5.3.1 prose: §11.1's table, the normative load-time rule list, has no row for it |
| AD-02 | Medium | plan §12 (phase 13 row), `payback.py:319`, `cli.py:2415`, `tests/unit/test_payback.py` | The phase-13 row describes the AC-01 fix as replacing a flag, but `evaluate_plan_payback(move_costs, benefit_load_seconds, payback_ratio)` has no access to `Σ r_s` at all — the plan-level outcome trigger needs the current and final slack threaded in from its sole caller (`cli.py:2415`), i.e. a signature and data-flow change, not a flag swap. The named test sweep also lists only `test_schedule.py` and `test_cli.py`; `test_payback.py` (two tests construct `resolves_reserve_violation=True` purely to assert the override being replaced, at `:334` and `:369`) and `test_execute.py` are omitted |
| AD-03 | Low | plan §14.8 | Arithmetic slip on a line added to fix an arithmetic slip: the new `swapme` transient check reads `1.0 + 1.0 + max(2·1.0, 3.0) = 6.0 ≤ 10`; it is `5.0`. Verdict unchanged |
| AD-04 | Low | plan §14.8 | AC-05's stale `Z_b` is only half-fixed: the corrected line still reads `max(2·max(1.0, 0.5), 3.0)`, contradicting the clause immediately after it ("`Z_roomy` has dropped to 0.5 with `603` gone") and the `hard: "10%"` parenthetical two bullets down, which correctly uses `2·0.5`. With `603` gone roomy holds no *managed* disk (the 5.8 TiB is foreign), so the inner term is `max(0, 0.5) = 0.5`. The `hard` floor dominates either way, so `9.3` stands — but this is the exact line AC-05 was raised about |
| AD-05 | Low | plan §7.3, §5.3.1 | §7.3 argues the outcome trigger's breadth in one direction only (narrower than the built `has_reserve_override`) and never states the other: one byte of shortfall reduction exempts the **entire** plan — arbitrarily expensive balance moves included — from the economic test. Combined with §5.3.1's own new thrash paragraph (a permanently-short cluster yields a shortfall-reducing plan on every run), every plan on such a cluster is fully payback-exempt forever. Not a regression (the built override is broader still) and per-move exclusion was correctly rejected, but it is now a deliberate documented choice and deserves the same paragraph the thrash risk got |
| AD-06 | Info | plan §7.3, §14.8 | §7.3's converse example says such a move is "scheduled first by §8.2's exception 2", while §14.8 in the same commit notes exception 2 is spec-only and phase 13 does not scope it — qualify it ("once exception 2 lands") or drop the scheduling half of the claim |

### 41.3 Assessment

The substantive redesign is right, and the commit is honest about what it changes in built
behaviour — which is what the twentieth pass was actually complaining about. Four of the six
new findings are presentational (AD-03, AD-04, AD-06) or a documentation gap in an argument that
is itself sound (AD-05). AD-02 is ordinary scope bookkeeping for phase 13. **AD-01 is the one
item that should not ship as written**: it is the only remaining finding that can make a running
cluster less safe rather than a plan less clear, and the fix — resolve the deprecated key and
its replacement with `max()` rather than a winner, and put the rule in §11.1's table — costs a
sentence.

---

## 42. Resolution of twenty-first-pass findings (AD-01..AD-06)

All six findings are fixed in `IMPLEMENTATION_PLAN.md` (plan-only, as with the two commits the
findings are about; phase 13 builds all of it). None is refuted — each was verified against the
built code before fixing (`payback.py:319`'s signature and its sole production caller
`cli.py:2415`, `test_payback.py:334`/`:369` and `test_execute.py:117`'s flag constructions,
`config/drs.example.yaml`'s `min_free_bytes: 0`), and the two arithmetic findings were re-derived
by hand.

| ID | Status | How resolved |
|----|--------|--------------|
| AD-01 | Resolved | §5.3.1's both-set rule is now the fail-safe union: the global soft floor is `max(min_free_bytes, free_space.soft)`, the warning names both keys and the resolved floor, and the paragraph states the upgrade scenario that makes a "winner" rule unsafe (adopting the new example config's `free_space: soft: 0` while keeping an old `min_free_bytes: 1 TiB` would drop a configured floor to zero behind a deprecation-shaped warning). §11.1's table gains the rule as a normative row, and §12's phase-13 row carries the same `max()` resolution so the implementation cannot reintroduce the winner semantics. |
| AD-02 | Resolved | Phase 13's row now states the outcome trigger as a signature and data-flow change: `evaluate_plan_payback(move_costs, benefit_load_seconds, payback_ratio)` has no access to `Σ r_s`, so the current and final slack are threaded in from its sole production caller (`cli.py`'s plan builder). The test sweep names all four modules: `test_schedule.py`'s ordering assertions, `test_cli.py`'s `resolves_reserve_violation` JSON assertions, `test_payback.py`'s two override tests (`:334`, `:369`) and `test_execute.py`'s `ScheduledMove` constructions. |
| AD-03 | Resolved | §14.8's `swapme` transient check corrected to `1.0 + 1.0 + max(2·1.0, 3.0) = 5.0 ≤ 10`. Verdict unchanged. |
| AD-04 | Resolved | §14.8's reversed-order second move corrected to `max(2·max(0, 0.5), 3.0)`: with `603` gone `roomy` holds no managed disk (the 5.8 TiB is foreign, `601` has not arrived), so the inner term is `max(0, 0.5) = 0.5` and the `hard` floor of 3.0 dominates either way — `9.3` stands, now derived from the correct `Z_roomy = 0`. |
| AD-05 | Resolved | §7.3 now argues the outcome trigger's breadth in both directions: the narrow side as before (narrower than the built `has_reserve_override`), and the wide side as a deliberate documented cost — one byte of shortfall reduction exempts the whole plan, so on a permanently-short cluster (§5.3.1's thrash paragraph) every shortfall-reducing plan is fully payback-exempt for as long as the shortfall stands. The paragraph gives the reason (the mandate does not grade repairs by size, and the plan-level benefit of §7.2 leaves no principled way to price only part of a repairing plan) and the bounds (the three hard rules still apply per move, the plan output carries every move's cost and `repair` marker, and the trigger requires an actual shortfall reduction — the same condition §6's override singles out). |
| AD-06 | Resolved | §7.3's converse example no longer asserts the scheduling half unconditionally: the move is marked `repair: true`, and scheduled first only "once §8.2's exception 2 is implemented (it is spec-only today, as §14.8 records)". |

Verification: `make check` — fmt-check, lint, typecheck, tests with coverage, fixtures `--check`,
`docs-check` (the plan PDF rebuilt and re-stamped in the same commit as the Markdown, per
AGENTS.md §7.4). No production code changed; every fix is to the plan text and to this file.

---

## 43. Twenty-second-pass review — verification of the AD-01..AD-06 fixes

Reviewed commit `0feb648` ("plan: fix twenty-first-pass review findings (AD-01..AD-06)") — 50
lines of `IMPLEMENTATION_PLAN.md` and 103 of this file, the PDF rebuilt and re-stamped in the
same commit (`3c7ab684…` verified matching the Markdown on both sides). No production code
touched, as the message states. `make check` runs clean on the tree (941 passed, 96.38%
coverage, `generate_expected.py --check` and `validate_corpus.py --check` both OK), so §42's
verification line holds.

### 43.1 Verification of the AD-fixes

All six are resolved, and the two arithmetic ones were re-derived rather than taken:

- **AD-03 ✓.** With `603 → swapme` scheduled first, `swapme` holds 1.0 used (`604:scsi0`),
  `z_d = 1.0`, `Z_swapme = 1.0`, so §8.1's predicate is
  `1.0 + 1.0 + max(2·max(1.0, 1.0), 3.0) = 5.0 ≤ 10` ✓ — as the line now reads.
- **AD-04 ✓, and it repairs a line the finding did not name.** With `603` gone `roomy` holds
  only the 5.8 TiB of foreign volumes, so `Z_roomy = 0` and `601` arriving gives
  `5.8 + 0.5 + max(2·max(0, 0.5), 3.0) = 9.3 ≤ 10` ✓. The `hard: "10%"` bullet's parenthetical
  — `5.8 + 0.5 + max(1.0, 1.0) = 7.3` — was already written against `Z_roomy = 0` (at the stale
  `Z = 1.0` it would read `8.3`), so the two derivations agreed only after this fix; they
  contradicted each other before it.
- **AD-01/AD-02/AD-05/AD-06 ✓** are in the plan as §42 describes. The code claims in AD-02's new
  row check out: `evaluate_plan_payback(move_costs, benefit_load_seconds, payback_ratio)` at
  `payback.py:319`, its sole production call site at `cli.py:2415`, `test_payback.py:334`/`:369`
  and `test_execute.py`'s `ScheduledMove` constructions.
- **AD-05's substance is right and its conclusion understated** — the true relation between the
  outcome trigger and the conditions it is compared to is a strict subset, not a rough match;
  see AE-07.

The findings below are all in this commit's own new material, and none of them reopens a
decision the plan has made: AD-01's resolution rule is right, and AE-01/AE-02 are about *where*
it applies and *where* it is written down.

### 43.2 Findings summary

| ID | Severity | Module(s) | Summary |
|----|----------|-----------|---------|
| AE-01 | Medium | plan §5.3.1, `reserve.py:143` | The `max()` is specified at the **global** level — "the global soft floor is `max(min_free_bytes, free_space.soft)`" — then handed to most-specific-wins inheritance. Two gaps. (a) **A percentage has no global value**: §5.3.1's own grammar makes `"10%"` a per-storage number ("one `"10%"` … demands 2 TiB and 200 GiB"), so with `soft: "10%"` and `min_free_bytes: 1 TiB` there is no single `max()` to take and no single "resolved floor" for the warning to name — the percentage wins on the 20 TiB LUN, the deprecated scalar on the 2 TiB one. (b) **A per-storage `free_space.soft` still silently lowers the deprecated floor**: fold-to-global-then-override means `storages[].free_space.soft: 100 GiB` beats a global `min_free_bytes: 1 TiB` on that storage — AD-01's hazard exactly, one level down, in the same mid-migration config shape. The built semantics settles both: `min_free_bytes` is applied today as a floor on *every* storage (`reserve.py:143`, `required = max(round(reserve_factor * largest), min_free_bytes)`), with no per-storage form, so resolving it per storage — `soft_s = max(soft_s_resolved, min_free_bytes)`, after percent conversion — preserves what the key means today *and* makes the percentage case well defined. The warning then says the deprecated floor applies as a lower bound to every storage instead of naming one number |
| AE-02 | Medium | plan §11.1 | The new row is in the wrong table, and the table says so itself: §11.1's preamble reads "Every one of them is a failure that produces a clear error and a non-zero exit, **never a warning-and-continue** — a misconfigured balancer moving production disks is worse than one that refuses to start." The row immediately below it is a warn-and-continue *resolution* rule — the one `free_space` case §5.3.1 explicitly does not fail. An implementer working from §11.1 (where load-time rules are supposed to live) would make a both-set config a startup refusal, contradicting §5.3.1's "the old key keeps working" and turning the routine upgrade shape AD-01 is about into a hard stop. AD-01 asked for the rule to be normative alongside the other config rules; the table it landed in inverts its semantics. A short "resolution rules (warn and continue)" list under the table fixes it — the `free_space` rows that *are* errors stay where they are |
| AE-03 | Medium | plan §12 (phase 13 row), `docs/manual/27-plan.md`, `docs/internals/96-payback.md`, `config/drs.example.yaml` | The sweep AD-02 extended covers the tests but not the **shipped documentation** of the field being replaced. `docs/manual/27-plan.md:208` lists `resolves_reserve_violation` as a `moves[]` field of `--json` output and `:86-94` documents its meaning in prose; `docs/internals/96-payback.md:105` states the exemption normatively — "a plan containing any move with `resolves_reserve_violation=True` always passes the aggregate ratio test". §7.3 replaces both: the field becomes the per-move `repair` marker with a revert-test definition, and the exemption becomes plan-level. The manual's prose is not even a rename — it fuses the scheduling rule (§8.2 priority 1, which *keeps* the current-state form) with the payback exemption (which does not), so phase 13 has to split it in two. Neither file appears in the row, which says only "the manual documents the block" — a different edit, about `free_space`. AGENTS.md §8.0 (every shipped artefact stands without the plan) makes a stale `--json` field list and a false normative sentence a shipped defect, not a docs chore. The row also omits `config/drs.example.yaml`, which AD-01's rationale now leans on ("the new example config … spells out `free_space: soft: 0`"): it is a shipped artefact (§0, line 235) and today carries `snapshot_reserve.min_free_bytes` with no `free_space` block at all |
| AE-04 | Low | plan §12 (phase 13 row), §7.3 | Two more items the sweep list misses. (a) `evaluate_plan_payback()` has a **fifth** call site: `tests/unit/test_affinity_repair_fixture.py:226` calls it positionally with three arguments and asserts nothing about the flag — it breaks on the *signature* change the row now asserts, not on the flag removal, so "all four modules asserting the old flag" does not cover it. (b) `tests/corpus/*.expected.json` record the flag 41 times across the two bundles, and §7.3 sends the reader to §12's row for them ("re-validated in phase 13 with everything else that asserts the old flag — see §12's row") — but the row never mentions `tests/corpus/` |
| AE-05 | Low | plan §7.3, §12 (phase 13 row), `cli.py:2374` | §7.3 triggers on "its final assignment's `Σ r_s`" without saying *which* final assignment, and the codebase has already decided this once: `cli.py:2374` evaluates `final_breakdown` against `schedule_result.final_assignment` — "the state reachable by the moves that actually got ordered … not an aspirational one a partial deadlock never reaches (REVIEW.md R-02)" — while the solver's own `.breakdown` is the target. A partially deadlocked plan can reach `Σ r_s = 0` in the target and not move the needle in the scheduled plan; taking the target would exempt a plan that does not repair. One clause, citing R-02, pins it. While there: the two numbers the row wants threaded in already exist at that call site — `ObjectiveBreakdown.reserve_statuses` carries `shortfall_bytes` per storage (`heuristic.py:103`, `:335`), and both `solve_outcome.initial_breakdown` and `final_breakdown` are in hand two lines above the `evaluate_plan_payback()` call. Naming that source makes the "data-flow change" actionable and bounds it: two sums over objects already passed to the benefit computation, no new plumbing through the solver |
| AE-06 | Low | plan §5.3.1, §11.1 | Folding the deprecated key into `free_space.soft` also subjects it to the new `soft_s < C_s` **hard error**, and the `max()` rule can only raise the folded value. Today a `min_free_bytes` above some storage's capacity is not an error: `reserve.py:143` simply makes `R_s` unsatisfiable, that storage reports a permanent shortfall, and the tool keeps balancing (§9.5's unfixable-shortfall line is this case). After the fold the tool refuses to start — on upgrade, for a config that has been running. Defensible as typo-catching, but it is not "the old key keeps working". Either exempt the folded value from `soft_s < C_s` (warn, and let it report as an unfixable shortfall as today), or say in §5.3.1 that the fold deliberately promotes it to a startup error |
| AE-07 | Info | plan §7.3 | The new bounding sentence says the trigger "requires an actual shortfall reduction, the same condition §6's override already singles out". Not the same condition: §6 fires on a storage **being** in violation at plan time, the outcome trigger on the plan **reducing** the total. The real relation is stronger and worth stating, because it is a migration-safety property: `Σ r_s` can only fall if some storage's `used_s` or `Z_s` falls, which requires a disk to *leave* that storage — and that storage was in violation. So every outcome-exempt plan is also exempt under today's `has_reserve_override`, and §6's override was already open for it: the change can only **remove** exemptions, never create one. The rarity argument survives intact (a subset of a rare condition is at least as rare), and "deliberately narrower" becomes a provable claim rather than a comparison |

### 43.3 Assessment

The commit does what its message says, and the two arithmetic fixes are right — including one
line the AD-04 finding did not name, which only becomes consistent with the rest of §14.8 now.
Nothing here reopens a decision: AD-01's `max()` is the correct resolution, AD-05's wide-side
argument is honest about a real cost, and AD-06's qualification is exactly the scope the
as-built code supports.

**AE-01 is the one that should not ship as written.** It is the only finding left that can still
lower a configured floor on a running cluster, and it does so through the two config shapes
§5.3.1 itself blesses — a percentage soft, and a per-storage override. The fix is smaller than
the rule it replaces: take the `max()` per storage after percent conversion, which is also
precisely what `min_free_bytes` means in the built code today. AE-02 is next by cost-to-fix
ratio (a misplaced row that tells an implementer to fail a config the prose says must keep
working), then AE-03, which is the difference between phase 13 shipping with a manual that
documents a `--json` field the code no longer emits.

One structural note, since this is the third consecutive pass to find the same shape of defect:
every one of AD-02, AE-03 and AE-04 is an *enumerated* sweep list that turned out to be one or
two items short. The enumeration is the defect. Phase 13's row could say instead: "every file
that mentions `resolves_reserve_violation` — `git grep -l` gives the list — is updated with it,"
which is self-maintaining, shorter than the sentence it replaces, and today returns exactly the
thirteen files at issue (four test modules, two corpus expected files, two shipped docs, three
source modules, plus the plan and this file). The signature change needs its own grep — `git
grep -l evaluate_plan_payback`, which is what surfaces AE-04's fifth call site, the one file
that touches the function without ever naming the flag.

---

## 44. Resolution of twenty-second-pass findings (AE-01..AE-07)

All seven findings are fixed in `IMPLEMENTATION_PLAN.md` (plan-only, as with the three commits the
findings are about; phase 13 builds all of it). None is refuted — each was verified against the
built code before fixing (`reserve.py:143`'s per-storage `max(round(f_s·largest), min_free_bytes)`,
`95-schedule.md`'s documented fold of the same floor into the transient check, `27-plan.md`'s
`--json` field list and fused prose, `96-payback.md:105`'s normative exemption sentence,
`test_affinity_repair_fixture.py:226`'s positional call, the 41 corpus flag records,
`cli.py:2374`'s R-02 comment), and both greps were run to confirm the file lists the structural
note names.

| ID | Status | How resolved |
|----|--------|--------------|
| AE-01 | Resolved | §5.3.1's fold is now per storage, after percent-to-bytes conversion: `soft_s = max(soft_s_resolved, min_free_bytes)` for every storage. The paragraph states both reasons: the built key is a floor on *every* storage (`reserve.py` applies it per storage, and the built transient check charges it on every in-flight state the same way), and a percentage has no global value to fold into (`"10%"` is 2 TiB on one LUN and 200 GiB on another). The warning now reports the deprecated key as a lower bound on every storage rather than one resolved number, and the paragraph notes the transient side needs no rule of its own (`hard: null` default keeps §8.1 exactly as strong as the built check). Phase 13's row carries the same per-storage fold. |
| AE-02 | Resolved | The both-set rule is out of §11.1's hard-error table and into a new "Resolution rules (warn and continue)" list directly under it, which states explicitly that everything in the table is a hard error and that these two situations are resolutions that warn and continue by design. The `free_space` rows that are errors stay in the table. |
| AE-03 | Resolved | Phase 13's row no longer enumerates the sweep: it is defined by `git grep -l resolves_reserve_violation` (with today's file list recorded: three source modules, four test modules, both corpus expected bundles, `docs/manual/27-plan.md`, `docs/internals/96-payback.md`, plus the plan and REVIEW.md) and `git grep -l evaluate_plan_payback` (adding `test_affinity_repair_fixture.py` and `docs/internals/00-overview.md`). The row names the manual's prose as a *split*, not a rename — its scheduling half keeps §8.2 priority 1's current-state form, its exemption half becomes the plan-level outcome trigger — and adds `config/drs.example.yaml` to the phase (it gains the `free_space` block in the same commit; today it carries `snapshot_reserve.min_free_bytes` with no `free_space` block at all). |
| AE-04 | Resolved | Both sub-items are covered by the grep-defined sweep: the fifth `evaluate_plan_payback` call site (`test_affinity_repair_fixture.py`, whose positional three-argument call breaks on the signature change without ever naming the flag) is named explicitly in the row as the reason the second grep exists, and the corpus bundles are in the first grep's recorded list. |
| AE-05 | Resolved | §7.3 pins "final assignment" to the **scheduled** one — `schedule_result.final_assignment`, the same R-02 distinction the payback benefit already draws — and says why: a partially deadlocked plan is scored on what it will really run, and a plan whose target repairs but whose schedule never gets there is not exempt. §5.3 point 3 and the revert-test sentence carry the same pinning. Phase 13's row names the data source for the threaded sums: `Σ shortfall_bytes` over `ObjectiveBreakdown.reserve_statuses`, with `solve_outcome.initial_breakdown` and the R-02 `final_breakdown` already in hand at the call site — two sums over objects already passed to the benefit computation, no new plumbing through the solver. |
| AE-06 | Resolved | §5.3.1 states the deliberate non-promotion: the fold does not subject the deprecated value to the `soft_s < C_s` startup error — a `min_free_bytes` above some storage's capacity has never been a startup failure (the built code reports it as that storage's permanent shortfall, §9.5), and "the old key keeps working" cannot mean a running config refuses to start on upgrade. The error applies to the new knob's own value; an oversized deprecated floor warns and reports as the unfixable shortfall it always was. The rule is also the second entry of §11.1's new resolution list. |
| AE-07 | Resolved | §7.3's bounding sentence now states the strict-subset property instead of the "same condition" claim: `Σ r_s` can only fall if some storage's `used_s` or `Z_s` falls, which requires a disk to *leave* that storage — and a storage whose shortfall a move reduces was in violation when the move left it — so every outcome-exempt plan is also exempt under today's `has_reserve_override` and §6's override was already open for it. The change can only remove exemptions, never create one, which is what makes "deliberately narrower" a provable claim rather than a comparison. The rarity argument survives (a subset of a rare condition is at least as rare). |

Verification: `make check` — fmt-check, lint, typecheck, tests with coverage, fixtures `--check`,
`docs-check` (the plan PDF rebuilt and re-stamped in the same commit as the Markdown, per
AGENTS.md §7.4). No production code changed; every fix is to the plan text and to this file.

---

## 45. Twenty-third-pass review — verification of the AE-01..AE-07 fixes

Reviewed commit `2622e6b` ("plan: fix twenty-second-pass review findings (AE-01..AE-07)") — 83
lines of `IMPLEMENTATION_PLAN.md` and 130 of this file, the PDF rebuilt and re-stamped in the
same commit (`dcd84304…` verified matching the Markdown on both sides). No production code
touched. `make check` runs clean (941 passed, 96.38% coverage, fixtures and corpus `--check`
OK), so §44's verification line holds.

### 45.1 Verification of the AE-fixes

All seven are resolved, and the code claims the fixes rest on were checked against the tree:

- **AE-01 ✓.** The fold is per storage, after percent conversion, and both of its stated reasons
  are true of the built code: `reserve.py:143` applies `min_free_bytes` as a floor on every
  storage (`required = max(round(reserve_factor * largest), min_free_bytes)`), and
  `schedule.py:147` folds the same floor into the transient check (`docs/internals/95-schedule.md:95`
  documents it). One benefit the paragraph does not claim: because the deprecated key is now a
  *bound* rather than a resolved number, the warning no longer needs storage capacities and can
  be emitted at config-load time, where the rest of the deprecation lives.
- **AE-02 ✓.** The row is out of the hard-error table and into a "Resolution rules (warn and
  continue)" list that opens by saying everything above it is a hard error. See AF-03 for the
  two hard-error statements that were not adjusted to match it.
- **AE-03/AE-04 ✓.** Both greps were re-run here and the recorded lists are exact:
  `git grep -l resolves_reserve_violation` returns the thirteen files the row names, and
  `git grep -l evaluate_plan_payback` adds exactly `test_affinity_repair_fixture.py` and
  `docs/internals/00-overview.md`. The manual's prose is correctly described as a *split*
  rather than a rename.
- **AE-05 ✓.** §7.3 and §5.3 point 3 both pin the trigger to `schedule_result.final_assignment`,
  and the phase-13 row names `Σ shortfall_bytes` over `ObjectiveBreakdown.reserve_statuses` as
  the source — which is right: both breakdowns are in hand at `cli.py:2415`, and `cli.py:2374`
  already evaluates `final_breakdown` against the scheduled assignment for R-02's reason.
- **AE-06 ✓** in §5.3.1 and in the new resolution list — but not in the two places an
  implementer reads the validation rules from; see AF-03.
- **AE-07 ✓.** The strict-subset argument is sound as stated: `Σ r_s` is a sum of non-negative
  terms, so it can only fall if some `r_s` falls; `r_s` can only fall if `used_s` or `Z_s` falls,
  which requires a disk to leave `s`; and `r_s > 0` before means `s` was in violation in the
  current assignment, which is exactly what `schedule.py:171`'s test asks. Every outcome-exempt
  plan is therefore `has_reserve_override`-exempt today.

The findings below are in this commit's new material and in what its two structural fixes did
*not* reach. None of them reopens a resolved decision.

### 45.2 Findings summary

| ID | Severity | Module(s) | Summary |
|----|----------|-----------|---------|
| AF-01 | Medium | plan §12 (phase 13 row), `src/proxmox_storage_drs/config_schema.json` | Phase 13's row never mentions `config_schema.json`, and the schema is **deliberately closed**: its own `$comment` says "`additionalProperties: false` throughout is deliberate: a typo'd key is a knob with no formula … this is where it is caught". So until the schema gains a top-level `free_space` object *and* a `free_space` property on `groups[].storages[]`, every config using the block §5.3.1 specifies is rejected by structural validation before a line of the new `config.py` code can run — §11.1's own pipeline is "validate with `jsonschema` for structure, **then** apply these semantic rules". The row enumerates seven source modules and the schema is not one of them. It also needs §5.3.1's grammar, which is wider than the existing `min_free_bytes` entry's: `{"type": ["string", "number", "null"]}` for `soft` and `hard` in both locations (integer bytes, byte-unit string, `"N%"`, and `null` with two distinct meanings by level) |
| AF-02 | Medium | plan §12 (phase 13 row), `docs/manual/10-configuration.md`, `docs/internals/{60,91,95}-*.md`, `.agents/domain-invariants.md` | The grep-defined sweep was applied to the flag and to `evaluate_plan_payback()` — but not to phase 13's *larger* change, the `min_free_bytes` scalar → `soft_s`/`hard_s` pair and the deprecation of a **documented config key**. That half is still an enumeration of source modules with no artefact list at all. `git grep -l min_free_bytes` returns 30 files; beyond the seven modules the row names and the files the other two greps cover, it adds `docs/manual/10-configuration.md:504` (a dedicated `### snapshot_reserve.min_free_bytes` reference section — the page where a deprecation has to be announced and the `free_space` block documented; the row says only "the manual documents the block"), `docs/manual/00-installation.md:42`, `docs/manual/30-safety-and-status.md:12`, `docs/internals/60-topology.md:25`, `docs/internals/91-optimize.md:81`, `docs/internals/95-schedule.md:95`, `.agents/domain-invariants.md:16` — which states invariant 2 as `used + max(f·Z_s, min_free_bytes) ≤ C_s`, the contract file agents read before touching this code — `.agents/testing.md:25`, `config_schema.json` (AF-01), and both `tests/corpus/*/config.yaml` inputs. §44 cites `95-schedule.md` as evidence for AE-01's fix, so that file was read during this commit and still did not enter the sweep. The remedy is the one the row already applies twice: define it as `git grep -l min_free_bytes` and record today's list |
| AF-03 | Medium | plan §11.1, §5.3.1, §12 (phase 13 row) | The fold's position in the validate-then-resolve pipeline is unspecified, and two hard-error statements read as though it has already happened. (a) The table row `free_space.soft < C_s` **for every storage, after resolution** now covers the folded value, which is exactly the case the resolution list below it says must warn and continue — the row was not qualified when AE-06's exception was written, and phase 13's row repeats it unqualified ("validates `hard ≤ soft` and `soft < C_s`"). (b) Unaddressed anywhere: the fold can only *raise* `soft_s`, so a config whose written `hard` exceeds its written `soft` passes `hard ≤ soft` while a large `min_free_bytes` is present and becomes a **hard error the moment the operator deletes the deprecated key** — the deprecation warning's own advice turns a running config into a startup failure. One sentence fixes both: validate the `free_space` values as written, *then* fold the deprecated floor in, and say that order — with the `< C_s` row qualified as "the `free_space` value's own, before the fold (see the resolution rules)" |
| AF-04 | Low | plan §5.3.1 | "Folded per storage, the deprecated floor cannot be lowered by the new knob **at all** — not by a smaller global `soft`, not by a per-storage override, not by a percentage landing on a small LUN" is contradicted three sentences later by the same paragraph: "an operator who then sets `hard` below it is using the new knob for the dip it exists to allow". The concession is the right call — `hard` exists to allow a transient dip — but "at all" is an absolute claim about a knob that demonstrably can lower the floor on the transient side. Say "cannot be lowered as a plan-endpoint floor", and let the `hard` sentence stand as the one deliberate exception |
| AF-05 | Low | plan §12 (phase 13 row), `config/drs.example.yaml` | The row now requires the example config to gain the `free_space` block but not what it must contain, and one value is load-bearing: it must ship `hard: null`. With `soft: 0` the per-storage fold protects the deprecated floor at the plan endpoint (`max(0, min_free_bytes)`), but an example that spelled out any `hard` below that floor would weaken §8.1's transient charge for precisely the operators the fold exists to protect — the built check charges `min_free_bytes` on every in-flight state (`schedule.py:147`), and `hard_s` replaces it. `hard: null` (= `soft`) is the only value that leaves an upgrading deprecated-key config exactly as strong as it is today. One clause in the row, or a sentence in §5.3.1's example block |
| AF-06 | Info | commit message | The message says the grep sweep pulls in "`docs/internals/00-overview.md`, and `config/drs.example.yaml`, **which gains the `free_space` block in the same commit**". It does not: this commit changes four files and the example config is not among them (it still has no `free_space` block). The plan's own wording is correct — in §12's row, "the same commit" means phase 13's implementation commit — but the sentence reads in `git log` as a claim about this commit, and the git record is the one artefact no later fix can amend |

### 45.3 Assessment

Both structural fixes in this commit are the right shape. Replacing an enumerated sweep with
`git grep -l` is the correct generalisation of AE-03/AE-04, and the per-storage fold (AE-01) is
strictly better than the global one: it matches what the built key means, it makes the
percentage case well defined, and it turns the deprecation warning into something emittable at
config-load time. AE-07's subset property is now a proof rather than a comparison, and it holds.

**AF-01 and AF-02 are the two that should not ship as written**, and they are the same defect
seen from two sides. The row generalised the sweep for the flag and for one function signature —
the two things the previous pass happened to name — and left the phase's largest change, the one
that deprecates a **documented config key**, on the enumeration that has now come up short three
passes running. `config_schema.json` is the sharp end of it: a closed schema means the feature's
entire config surface is unreachable until that file changes, and it is the one file in the
phase whose omission cannot be discovered by reading the code the row does name. A third grep —
`git grep -l min_free_bytes`, 30 files today — closes both, and would have closed AF-01 without
anyone thinking about schemas at all.

AF-03 is next, because it is the only finding here that can still turn a running configuration
into a refusal to start, and (b) does it at the exact moment the operator follows the
deprecation warning's instructions. AF-04 through AF-06 are one clause each.

---

## 46. Resolution of twenty-third-pass findings (AF-01..AF-06)

Five of the six are fixed in `IMPLEMENTATION_PLAN.md` (plan-only, as with the three commits the
findings are about; phase 13 builds all of it). AF-06 is a defect in a commit message that is
already in history and is recorded rather than rewritten — history is not rewritten in this
repository — with the plan wording that invited it disambiguated so it cannot recur.

**These fixes were written by the reviewer who raised the findings**, unlike §§40/42/44, where
the finder and the fixer were different. This section is therefore a record, not an independent
verification: a later pass should re-check it the way §45 re-checked §44.

| ID | Status | How resolved |
|----|--------|--------------|
| AF-01 | Resolved | §12's phase-13 row now lists `config_schema.json` **first**, with the reason (the schema is closed — `additionalProperties: false` throughout, deliberately — so a `free_space:` key is rejected structurally before `config.py` sees it) and the shape (a top-level `free_space` object and a `free_space` property on `groups[].storages[]`, each with `soft`/`hard` typed `["string", "number", "null"]` for §5.3.1's grammar). §5.3.1's closing sentence carries the same point, so the constraint is stated where the block is specified as well as where it is built. |
| AF-02 | Resolved | The row defines the scalar → `soft_s`/`hard_s` sweep by `git grep -l min_free_bytes` — the third grep, alongside the two AE-03/AE-04 added — and records today's list of 30 files, calling out what the enumeration had missed: `docs/manual/10-configuration.md`'s `### snapshot_reserve.min_free_bytes` reference section (which becomes the deprecation notice and the `free_space` documentation), the other three manual pages, `docs/internals/{60-topology,91-optimize,95-schedule}.md`, `.agents/domain-invariants.md` (whose invariant 2 reads `used + max(f·Z_s, min_free_bytes) ≤ C_s` and becomes `soft_s`), `.agents/testing.md`, both `tests/corpus/*/config.yaml` replay inputs, and the seven test modules. Two source files the module list had also missed are now named in it: `execute.py`'s live execution-time re-check and `collect.py`'s bundle manifest, which serialises the scalar so a replayed bundle must carry the pair. |
| AF-03 | Resolved | §5.3.1 gains a **"Validate as written, then fold"** paragraph pinning the pipeline — inheritance, percent-to-bytes conversion, §11.1's two `free_space` checks against the written values, *then* the fold — with both failure modes spelled out: `hard ≤ soft` checked after the fold lets a written `hard > soft` hide behind a large `min_free_bytes` and surface as a startup failure the moment the operator deletes the deprecated key (the very thing the warning asks for), and `soft_s < C_s` checked after the fold errors on the oversized deprecated floor that AE-06 deliberately does not promote. §11.1's two table rows carry the same qualification — `hard ≤ soft` "**before** the deprecated `min_free_bytes` fold", and `soft_s < C_s` "the `free_space` value's own, **not** the folded `min_free_bytes`" — and phase 13's row now says "on the written values, before that fold". |
| AF-04 | Resolved | §5.3.1's absolute claim is scoped: the deprecated floor cannot be lowered **as a plan-endpoint requirement**, and the sentence now says outright that the transient floor is the one place the new knob may move it, pointing at the `hard` sentence that makes that deliberate. |
| AF-05 | Resolved | Phase 13's row states the example config's values, not just that it gains the block: `soft: 0` / `hard: null`, with `hard: null` marked load-bearing — any spelled-out `hard` below the folded floor would weaken §8.1's transient charge for exactly the operators the fold protects, since the built check charges `min_free_bytes` on every in-flight state and `hard_s` replaces it, while `hard: null` (= `soft`) leaves an upgrading deprecated-key config exactly as strong as it is today. |
| AF-06 | Recorded, not fixable | The message of `2622e6b` says `config/drs.example.yaml` "gains the `free_space` block in the same commit"; it does not — that commit changes four files and the example config is not among them. The commit is in history and history is not rewritten here (AGENTS.md §4), so the correction lives in this section: **the example config gains the block in phase 13's implementation commit, not in `2622e6b`.** The plan sentence that invited the misreading now says "in **phase 13's own commit**" instead of "in the same commit". |

Verification: `make check` — fmt-check, lint, typecheck, tests with coverage, fixtures `--check`,
`docs-check` (the plan PDF rebuilt and re-stamped alongside the Markdown, per AGENTS.md §7.4).
No production code changed; every fix is to the plan text and to this file.

---

## 47. Twenty-fourth-pass review — the free-space branch as a whole

Reviewed the accumulated `feat/free-space-requirements` branch against `main`: the full diff of
`IMPLEMENTATION_PLAN.md` (+477/−21 over five commits — `9b44ba9`'s §5.3.1 redesign and the
`15a8982`/`0feb648`/`2622e6b`/`b089bc6` AC/AD/AE/AF fix rounds), REVIEW.md's own passes 20-23,
and the rebuilt PDF stamps. The four fix commits were each reviewed on landing (§§39, 41, 43,
45); this pass reviews what none of them could see — the final accumulated text, where four
rounds of fixes sit on top of one another — and, per §46's own request ("a later pass should
re-check it the way §45 re-checked §44"), independently verifies the AF fixes, whose finder and
fixer were the same reviewer.

The accumulated design is sound and, for the first time in this feature's history, internally
consistent on every load-bearing rule: the grammar, the two-level `null` semantics, the
per-storage fold, the validate-as-written-then-fold order, the outcome trigger and the revert
test now say the same thing in §5.3, §5.3.1, §7.3, §11.1, §12 and §14.8. What remains is
residue of the fix rounds themselves: one number in §14.8 that does not verify (AG-01), three
sentences that survived a later fix's blast radius (AG-02, AG-03, AG-06), one composition edge
the newly precise trigger definition left unpinched (AG-04), and two small specification gaps
(AG-05, AG-08).

### 47.1 Verification run

- `make check` at branch tip (`b089bc6`): green end to end — fmt-check, lint, typecheck,
  **941 passed, 1 warning**, **96.38% line coverage**, `generate_expected.py --check` OK,
  `validate_corpus.py --check` OK, and the PDF stamp matching the Markdown
  (`sha256sum --check docs/IMPLEMENTATION_PLAN.pdf.sha256` → OK).
- **All three sweep greps re-run; the phase-13 row's recorded lists are exact.**
  `git grep -l resolves_reserve_violation` → 13 files, exactly the row's list (3 source modules,
  4 test modules, both corpus expected files, `docs/manual/27-plan.md`,
  `docs/internals/96-payback.md`, the plan, this file). `git grep -l evaluate_plan_payback` → 9
  files; relative to the first list it adds exactly `test_affinity_repair_fixture.py` and
  `docs/internals/00-overview.md`, as recorded. `git grep -l min_free_bytes` → **30 files**,
  matching the row's count and its enumeration category by category (8 `src/` files — `config`,
  `reserve`, `heuristic`, `schedule`, `optimize`, `execute`, `cli`, `collect`; 7 test modules —
  including `test_gates.py` and `test_reserve.py`, which no enumeration had ever named; both
  corpus `config.yaml` replay inputs; `config_schema.json`; `config/drs.example.yaml`; 4 manual
  pages; 3 internals pages; both `.agents/` files; the plan and this file). No file outside the
  recorded sweep.
- **The row's artefact claims verified**: `config/drs.example.yaml:196` carries
  `min_free_bytes: 0` under `snapshot_reserve` with no `free_space` block anywhere, exactly as
  the row states; the corpus expected files record `resolves_reserve_violation` **41 times, all
  `false`**, exactly as §7.3's fc-tier1 paragraph claims.
- **§14.8 re-derived in full against the final text** (the pass-20/21/22 tradition, on the
  accumulated wording rather than per commit): the initial table (`r_packed = 10.5 − 10 = 0.5`,
  free 2.5/3.2/9.0), `b̄ = 0.51`, gate 127% (1.2745), `F_before = 0.82/0.51 = 1.6078`, both
  `Σ r = 0` candidates with the γ tiebreak (5.2828 vs 5.3078 — the uniqueness claim holds), the
  final table (roomy 6.3 used, `Z = 0.5`, free 3.7), `E: 0 → 4.10`, `F → 0.62/0.51 = 1.2157`,
  benefit `(−4.1 + 0.098) × 31 536 000 = −123 114 071 ≈ −1.23×10⁸`, cost 15 728.64, ratio
  **−7 827.4**, the soft:0 counterfactual optimum 0.8039, both `hard`-sweep orders (10.3 > 10
  infeasible; 5.0, 9.3, 7.3 all ≤ 10; the 2.7-TiB dip and the 3.7 endpoint), and both
  revert-test scores (holding `601` → `Σ r = 0.5`; holding `603` → 0.3 — both moves marked
  `repair: true`, which §7.3's marker rule and §14.8's text are jointly consistent on). Every
  number checks — **except the as-built one-move parenthetical (AG-01)**, whose benefit is
  negative where the plan says positive.
- **AE-07's strict-subset property re-proven from the accumulated definitions**: `Σ r_s` is a
  sum of non-negative per-storage slacks; each `r_s` depends only on `used_s`, `Z_s` and the
  fixed `R_s = max(f_s·Z_s, soft_s)`; so `Σ r_s` strictly falling requires some `r_s` to fall,
  which requires a managed disk to leave that storage, and that storage had `r_s > 0` in the
  current assignment — the exact condition `has_reserve_override` and §6's override test. Every
  outcome-exempt plan is exempt today; the change only removes exemptions.
- **The AF fixes all hold** as §46 records them: the schema listed first with its shape (AF-01),
  the third grep and its 30 files (AF-02), the validate-then-fold paragraph with both §11.1 rows
  qualified (AF-03), the scoped "plan-endpoint" claim (AF-04), `soft: 0`/`hard: null` with the
  load-bearing reason (AF-05), and the "phase 13's own commit" wording (AF-06). §46's
  self-verification is accurate on every row.

### 47.2 Findings summary

| ID | Severity | Location | Summary |
|----|----------|----------|---------|
| AG-01 | Low | §14.8 | The as-built one-move parenthetical "(objective 1.081, positive benefit, payback passes)" does not verify: the plan's benefit is **−61 835 load·s** (`α·ΔE + δ·ΔF = −0.10 + 0.098 < 0`; ratio −11.8; the aggregate test fails at λ·cost = 52 429), and it passes payback only via the repair exemption — which its own `Σ r_s: 0.5 → 0` grants under both the built override and the outcome trigger. The sentence's contrast (as-built passes on merit; "the negative benefit and the whole exemption demonstration depend on phase 13") is wrong in both halves: both variants have negative benefit and both are exemption cases; the format rule changes the plan's *shape* (two moves, the indirect repair, the revert-test marker), not its exemption status |
| AG-02 | Low | §5.3.1 | The percentage grammar's stale dash-clause: the bullet narrows to `0 ≤ N < 100` (AC-09's fix) and then says "`100%` is rejected by §11.1's `soft_s < C_s` rule rather than accepted here and failed there" — the pre-AC-09 mechanism, contradicting the grammar bound in the same bullet, §11.1's own row (which carries `0 ≤ N < 100` as a load-time rule), and AC-09's recorded resolution ("rejected by the grammar itself"). Parse-time and inventory-time rejection are different error surfaces; the plan names both |
| AG-03 | Low | §5.3 point 3 | "decided on the plan's outcome ... **exactly as** the built `payback.py`'s `has_reserve_override` short-circuits the aggregate test" equates the new outcome trigger with the built source-violating trigger that §7.3, five sections later, explicitly calls narrower-than-built — the mirror image of AE-07's "same condition" claim. A reader of §5.3 alone — the section an implementer builds (C5)'s repair semantics from — would implement (or believe already built) the wrong trigger |
| AG-04 | Low | §7.3 | The trigger is pinned to `schedule_result.final_assignment`, but duration-rule rejections happen at the payback gate, *after* scheduling: a repair move exceeding `max_single_move_duration` sits in the order, makes the scheduled assignment repairing, grants the exemption, is then dropped as refused — and the remaining balance moves execute with no economic test on a plan that no longer repairs. The transient-invariant half is self-consistent (`order_moves` enforces §8.1, so a breaching move never reaches the order); the duration half is the hole |
| AG-05 | Low | §9.5, §7.3, §16.6 | The exemption has no specified machine-readable surface: the pending note names only the per-move `repair` field reaching `--json`; the plan-level exemption note exists only in the human sample, nothing emits the `Σ r_s` pair it could be derived from (the X-07/Y-04 gap), and the corpus expected files' "payback arithmetic" would conflate accepted-on-merit with accepted-by-exemption in a bare `accepted: true` — the exact distinction §14.8's demonstration turns on |
| AG-06 | Info | §13 | The hazard row's "its repair moves are scheduled first" is contradicted by §14.8's own worked example: `603 → swapme` is marked `repair: true` and scheduled *second* — exception 1 (built, and kept by phase 13) ranks only the direct repair first; the indirect, revert-test-marked repair waits for exception 2, which is spec-only and not scoped in phase 13 |
| AG-07 | Info | §14.8 | Fix-round residue: the capacity-gate rationale appears twice (the "Second," prerequisite paragraph AC-04 added, and the original parenthetical it paraphrases), and the `hard: "10%"` bullet scopes roomy's dip "for the duration of the mirror" — 601's mirror — when the dip (7.3 used, 2.7 free) persists until 603's source release, through 603's entire mirror. The invariant claims are unaffected |
| AG-08 | Info | §3.5 | `verify-storages` is untouched by the branch: it reports `saferemove`, sizes and the largest disk, but not the resolved per-storage `soft_s`/`hard_s` — the number that now drives the §6 override, the §7.3 exemption and §9.5's shortfall lines, and the one place where a percentage, a pattern-level setting and the deprecated-key fold resolve differently per LUN. Phase 13 does not scope it |

### 47.3 AG-01 — the as-built one-move parenthetical's payback arithmetic does not verify

**Severity:** Low
**Where:** §14.8, the "Two prerequisites" paragraph.

The sentence: "under that as-built behaviour the fixture's optimum is the *one*-move repair
`601:scsi0 packed → swapme` (objective 1.081, positive benefit, payback passes) — the two-move
shape, the negative benefit and the whole exemption demonstration depend on phase 13 landing the
format rule first."

The objective figure verifies (1.0809 = `E 0.10 + β 0.25 + γ 0.025 + δ·F 0.706`). Neither payback
claim does. The one-move plan relocates the ℓ = 0.05 disk off a perfectly balanced group: loads
become 2.00/2.05/2.10 (`E: 0 → 0.10`, so `ΔE = −0.10`) and fills become 0.70/0.68/0.15
(`F: 1.6078 → 1.4118`, so `ΔF = +0.196`), giving

```
benefit = (α·ΔE + δ·ΔF) · H = (−0.10 + 0.5 × 0.196) × 31 536 000 ≈ −6.2×10⁴ load·s
cost    = 2 × (0.5 TiB / 200 MiB/s) = 5 243 load·s
ratio   = −11.8   <   λ = 10   → the aggregate test REJECTS
```

(Computed with the same script that reproduces every other §14.8 number to the digit.) The plan
passes payback anyway — **via the exemption**: its final `Σ r_s` is also 0 (packed 7.0 + 3.0 =
10.0, swapme 1.5 + 3.0 = 4.5), so both the built `has_reserve_override` (601's source is
violating at scheduling time) and §7.3's outcome trigger (0.5 → 0) exempt it. So "positive
benefit" is false, "payback passes" is true only for the reason the same sentence says the
two-move variant alone needs, and the dash-clause is wrong on two of its three items: the
negative benefit and the exemption demonstration do *not* depend on the format rule — the
one-move counterfactual has both. What actually depends on it is the plan's *shape*: two moves
instead of one, the indirect repair, the revert-test marker and the `hard`-sweep ordering flip.

The claim entered the plan through AC-03's own finding text ("objective ≈ 1.081, Σ r_s = 0,
positive benefit, payback passes") and was copied into §14.8 by the AC fixes unverified; the
twentieth pass's verification run (§39.2) re-derived the two-move, counterfactual and γ-tiebreak
numbers but never the one-move *payback* figures. This is AA-03/AB-02's class — a §14 number
that does not hand-derive — with a behavioural edge: an implementer writing the fixture's
partial-landing test from this sentence would assert the aggregate test passes and find that it
does not. Inert to the mechanism the sentence serves (the `requires_format_eligibility: true`
loud-failure marker does not depend on the payback numbers), hence Low.

**Recommendation:** correct the parenthetical to "(objective 1.081, benefit ≈ −6.2×10⁴ load·s —
it too passes only via the repair exemption)" and re-scope the dash-clause to what actually
depends on the format rule: "the two-move shape, the indirect repair and both `hard`-sweep
orders".

### 47.4 AG-02 — the percentage bullet names two rejection mechanisms for one typo

**Severity:** Low
**Where:** §5.3.1, the grammar's percentage bullet.

The bullet reads: "a string ending in `%` (`"10%"`), resolved as `round(C_s · N/100)` against
*that storage's own capacity*, with `0 ≤ N < 100` — `100%` is rejected by §11.1's `soft_s < C_s`
rule rather than accepted here and failed there." AC-09 narrowed the grammar to `N < 100`
precisely so that, per its own recorded resolution (§40), "`100%` is rejected by the grammar
itself rather than accepted here and failed by `soft_s < C_s` later" — and the trailing clause,
which predates that fix, still attributes the rejection to the old mechanism. As the bullet now
stands it contradicts itself (the bound rejects N = 100 at parse time; the clause says the
semantic check does), contradicts §11.1's own row (which carries `0 ≤ N < 100` as a load-time
validation rule), and specifies two different failure surfaces for the same typo: a
config-parse error at load time versus the inventory-load error the `soft_s < C_s` row itself
describes ("caught only once the inventory is loaded"). An implementer must pick one, and a test
writer cannot know which failure mode a `"100%"` config should produce.

**Recommendation:** one clause — "`100%` is rejected by the grammar itself, so §11.1's
`soft_s < C_s` rule never needs to see it" — or delete the clause outright (§11.1's row already
carries the bound).

### 47.5 AG-03 — §5.3 point 3's "exactly as" equates the outcome trigger with the built one

**Severity:** Low
**Where:** §5.3 (C5)'s mandate paragraph, point 3.

"The exemption is **plan-level** — decided on the plan's outcome, the `Σ r_s` of the scheduled
assignment it ends at ... against the current assignment's — **exactly as** the built
`payback.py`'s `has_reserve_override` short-circuits the aggregate test for a plan containing a
reserve-resolving move." §7.3, five sections later, says the opposite about the same built
function: "This is deliberately narrower in its trigger than the built `payback.py` already
implements (`has_reserve_override` fires when *any* move's source was violating at scheduling
time — a plan that moves a disk off a violating storage but ends no less short is exempt today
and will not be under the outcome trigger)". The two sections share a plan-level *shape*
(skip the aggregate test for the whole plan) but not a *trigger*, and "exactly as" asserts
equivalence of the whole exemption. This is AE-07's mirror image: that pass replaced §7.3's
"same condition" claim with the strict-subset property, and §5.3's phrase survived because
grammatically it can be read as attaching to "short-circuits the aggregate test". But §5.3 is
the section an implementer builds (C5)'s repair semantics from, and the risk is the
T-03/V-01 family: confident prose describing machinery that works differently — here, a reader
would either implement the source-violating trigger to match what they believe is built, or
assume no change is needed because it already works that way.

**Recommendation:** "— in the same plan-level way as the built `payback.py`'s
`has_reserve_override` short-circuits the aggregate test, a trigger §7.3 then deliberately
narrows."

### 47.6 AG-04 — the exemption is granted on a schedule the duration rule then amputates

**Severity:** Low
**Where:** §7.3.

The trigger's evaluation point is pinned (AE-05): the scheduled assignment,
`schedule_result.final_assignment`. But the three hard per-move rules fire at the payback gate,
*after* scheduling — the built gate drops `rejected_moves` from the order and only then consults
`aggregate_ok` (the S-02 fix), and §7.3 keeps that shape ("the three hard rules above still
apply to every move in an exempt plan"). Compose them: a repair move whose `duration_d` exceeds
`max_single_move_duration` **is in the order** — scheduling knows nothing of the duration rule —
so the scheduled assignment repairs, the outcome trigger grants the plan-level exemption, the
gate then drops the repair move as refused, and the remaining balance moves — the ones the
aggregate test exists to price — execute with no economic test, on a plan that no longer
repairs and whose shortfall §9.5 now reports as unmet. The transient-invariant half of the same
sentence is self-consistent by construction (`order_moves` enforces §8.1, so a
transient-breaching move deadlocks out of the order and the trigger already scores the real
schedule); the duration half is the hole. The closing sentence ("A repair that cannot finish
inside `max_single_move_duration` ... is rejected like any other move and the shortfall
reported as unfixable") addresses the move's fate, not the exemption of what remains. The same
composition exists in the built override today, but phase 13 is the moment the trigger acquires
a precise evaluation point, and the pinning should say which move set it scores.

**Recommendation:** one sentence in §7.3: the trigger is evaluated on the order *after* the
hard per-move rules' refusals — the plan's outcome is what it will actually run — with the
phase-13 row naming where in `cli.py`'s gate sequence the sums are taken (after
`_apply_payback_gate`'s drops, not before).

### 47.7 AG-05 — the exemption has no machine-readable surface

**Severity:** Low
**Where:** §9.5's pending note, §7.3, §16.6 check 4.

§9.5's "As built, phase 13 pending" note names exactly one JSON arrival: "The
`repair: true`/`false` field likewise reaches `--json` only with phase 13". The exemption
itself — the fact that the aggregate test was skipped, which §7.3 calls the plan's headline
verdict and §9.5's human sample renders as the note under the payback line — has no specified
`--json` field, and nothing emits the before/after `Σ r_s` from which it could be derived:
`plan --json` carries no reserve-shortfall totals (the X-07/Y-04 gap, already documented twice
in this file), and the per-move marker alone cannot distinguish "accepted, and would have
passed anyway" (fc-tier1) from "accepted only because exempt" (§14.8) — the exact distinction
§14.8's demonstration turns on. Downstream, §16.6's check 4 records "the payback arithmetic"
per variant in the corpus expected files, where a bare `accepted: true` would conflate the two
cases in a regression artefact. The cheapest closure rides with AE-05's data flow: the current
and final slack are already threaded to `evaluate_plan_payback()` in phase 13 — one
serialization of either the flag or the two sums into the payback block, named in §9.5's
pending-note list.

### 47.8 AG-06 — §13's "repair moves are scheduled first" vs §14.8's own second-scheduled repair

**Severity:** Info
**Where:** §13, the `free_space.soft` hazard row.

The row: "a repairing plan is payback-exempt (§7.3) and its repair moves are scheduled first".
§14.8's preferred order schedules `601 → roomy` first (exception 1: its source is violating)
and `603 → swapme` — marked `repair: true` by the very test §7.3 defines — *second*, and §14.8
says so ("exception 2 applies to that move too ..., but rule 1 outranks rule 2"). Exception 1
is a current-state rule and cannot rank an indirect repair; exception 2, which would, is
spec-only and explicitly not scoped in phase 13. "Its *direct* repair is scheduled first" is
what both the build and phase 13 deliver; the unconditional plural over-promises against the
plan's own worked example.

### 47.9 AG-07 — two fix-round residues inside §14.8

**Severity:** Info
**Where:** §14.8.

(a) The capacity-gate rationale now appears twice: the "Second, ..." prerequisite paragraph
AC-04's fix added ("the group's fills (0.75/0.68/0.10) put the capacity gate at ... 127%, far
above the 25% default — the gate is what lets the engine *plan* here, and the fixture sets
`gates.capacity_spread_threshold: null` ...") and the older parenthetical after the initial
state ("The capacity gate is open on this group — 127%, above — which is why the fixture nulls
it: the gate's ACT is what lets the engine plan ..."), which the fix paraphrased rather than
replaced. (b) The `hard: "10%"` bullet scopes roomy's dip "below its 3.0 soft requirement for
the duration of the mirror" — 601's mirror — but the dip (roomy at 7.3 used, 2.7 free) begins
with 601's target allocation and persists until 603's *source release*, i.e. through 603's
entire mirror and drain; "for the duration of the repair" would be accurate. Both invariant
claims (never below `hard`; endpoint back to 3.7) are unaffected, as is every number.

### 47.10 AG-08 — `verify-storages` does not surface the resolved requirement

**Severity:** Info
**Where:** §3.5, `pve-storage-drs verify-storages`.

The branch touches every consumer of the free-space policy except the one command whose §3.5
charter is storage-config diagnosis: `verify-storages` reports `type`, `shared`, `content`,
`saferemove`, throughput, sizes and the largest disk, but not the resolved per-storage
`soft_s`/`hard_s` — the number that now drives the §6 override, the §7.3 exemption and §9.5's
shortfall lines, and the one quantity whose *derivation* (pattern expansion, percentage
conversion against each LUN's own capacity, the deprecated-key fold) an operator cannot
predict without exactly the display this command exists to provide. §3.5's own justification
for showing the pattern expansion there — "so an over-broad or dead pattern is visible before
any plan relies on it" — is the same argument one feature later. Not a defect (once phase 13
lands, `show-load`/`plan` reserve status carries the shortfall), but phase 13's row does not
scope it, and the row is where it would naturally belong.

### 47.11 What this pass confirms

- **The accumulated text is self-consistent on every rule the four fix rounds touched**: the
  grammar ↔ §11.1's rows ↔ the resolution list; the fold's position ↔ both row qualifications;
  the two `null`s; the trigger ↔ the marker ↔ §5.3 point 3's numbers; §8.1's predicate ↔
  §14.8's two orders; the phase-13 row ↔ the greps that define it (verified exact, all three).
  Passes 20-23 each fixed the commit in front of them; this pass confirms the fixes compose.
- **§46's self-verification is accurate.** All six AF resolutions hold as described, including
  the two a same-person fix is most likely to overstate: AF-02's 30-file list is exact to the
  file, and AF-03's ordering constraint is carried in all three places it needs to be (§5.3.1,
  both §11.1 rows, the row).
- **§14.8's specified arithmetic verifies to the digit**, including the γ tiebreak's second
  candidate (5.3078), both `hard`-sweep orders, and both revert-test scores — the fixture's
  future generator has a fully checked target. The one failure (AG-01) is in the *as-built
  counterfactual* paragraph, the only part of §14.8 no previous pass had computed.
- **AE-07's strict-subset property holds as a proof**, not a plausibility argument, on the
  accumulated definitions — and AG-03 notwithstanding, it is stated correctly in §7.3 itself.
- **The branch's process discipline held where the eighteenth pass's did not**: five commits,
  each on the feature branch, each rebuilding and re-stamping the PDF in the same commit
  (AF-06's commit-message erratum aside — already recorded in §46), no production code touched,
  `make check` green at tip.

### 47.12 Assessment

Four fix rounds in five commits have converged: every design decision this review series has
examined — the outcome trigger over the per-move exemption, the revert test as marker rather
than trigger, the per-storage fold, the validate-as-written-then-fold order, the strict-subset
property — survives independent re-derivation from the final text, and the grep-defined sweeps
that replaced three consecutive passes of one-short enumerations are exact against the tree.
What is left is small and mostly cosmetic: one wrong parenthetical (AG-01, the only §14.8
number that fails verification, and the one an implementer writing the partial-landing test
will read), two stale sentences naming superseded mechanisms (AG-02, AG-03), one scheduling
claim §14.8 itself contradicts (AG-06), one edge to pinch while the trigger is being
implemented (AG-04 — a sentence, but one that decides whether an economic test runs at all in
its corner), and two gaps an afternoon covers (AG-05's JSON field, AG-08's display line). Fix
AG-01 before phase 13 starts; AG-02/AG-03/AG-04 belong in phase 13's specification tidying;
the rest is optional. None of the eight blocks the branch's purpose: the free-space
requirements design is now specified completely enough to build.

---

## 48. Resolution of twenty-fourth-pass findings (AG-01..AG-08)

All eight are fixed in `IMPLEMENTATION_PLAN.md`. Every one was independently re-checked against
the plan text and, where it makes a claim about behaviour, against `src/` before being accepted —
none was taken on the finding's own word, and none was refuted. Two are fixed slightly wider than
the finding asked: AG-02 had a second instance the finding did not name, and AG-04's fix covers
the saturation deferral as well as the duration rejection, which have the same shape.

**Verification of AG-01 before fixing it.** The §14.8 fixture was re-derived from scratch — all
three assignments (current, the as-built one-move optimum, the two-move optimum) scored against
§5.3 (C5)/(C6)/(C7), §5.4 and §7.1/§7.2 with the fixture's own weights (`α = 1.0`, `β = 0.25`,
`γ = 0.05`, `δ = 0.5`, `f = 2.0`, `soft = 3.0`, `H = 365d`, `λ = 10`, 200 MiB/s, `ω = 2`):

| | used | loads | `E` | `F` | `Σ r_s` | objective | benefit | cost | ratio |
|---|---|---|---|---|---|---|---|---|---|
| current | 7.5 / 6.8 / 1.0 | 2.05 / 2.05 / 2.05 | 0 | 1.6078 | 0.5 | 0.8039 | — | — | — |
| one-move (as built) | 7.0 / 6.8 / 1.5 | 2.00 / 2.05 / 2.10 | 0.10 | 1.4118 | 0 | 1.0809 | **−61 835** | 5 243 | **−11.79** |
| two-move (with C2) | 7.0 / 6.3 / 2.0 | 2.00 / 0.05 / 4.10 | 4.10 | 1.2157 | 0 | 5.2828 | −123 114 071 | 15 729 | −7 827.4 |

Every figure §14.8 states is reproduced to the digit — the initial table, `b̄ = 0.51`, both
objectives, the `soft: 0` counterfactual's 0.8039, the two-move benefit/cost/ratio. The only
figure that is *not* reproduced is the one AG-01 names: the as-built one-move plan's benefit is
**−61 835 load·s**, not positive, its ratio is −11.79 against `λ = 10`, and the aggregate test
therefore fails on it (`λ·cost = 52 429`). It clears the gate through the repair exemption, its
own `Σ r_s` falling 0.5 → 0 — which both the built `has_reserve_override` (601's source is
violating when the move leaves it) and §7.3's outcome trigger grant. The finding is exactly
right, including its reading of why the dash-clause is wrong in two of its three items.

**Verification of AG-04 against the built pipeline.** The composition hole is real in the code as
well as in the specification. `payback.py:352-354` computes `aggregate_ok = has_reserve_override
or benefit >= λ·cost` and `rejected` from `exceeds_max_duration` in the same call, and
`cli.py`'s execution gate then tests `aggregate_ok` *first* and only afterwards filters
`rejected_moves | deferred_moves` out of the order (`excluded_keys`, the S-02 fix). So a plan
whose repair move exceeds `max_single_move_duration` today: sets the override, passes
`aggregate_ok`, loses the repair move to the filter, and executes its remaining balance moves
with no economic test on a plan that no longer repairs. Phase 13 inherits the shape unless the
trigger's evaluation point says otherwise, which is what AG-04 asked for.

| ID | Status | How resolved |
|----|--------|--------------|
| AG-01 | Resolved | §14.8's as-built parenthetical now states the arithmetic instead of asserting the opposite of it: objective 1.081, `E: 0 → 0.10` against `F: 1.608 → 1.412`, benefit ≈ −6.2×10⁴ load·s against a 5 243 load·s cost, ratio −11.8, clearing the gate only through the same repair exemption the two-move plan needs (its own `Σ r_s: 0.5 → 0`, which both the built override and the outcome trigger fire on). The dash-clause is re-scoped to what actually depends on the format rule — the plan's **shape**: the two-move repair, the indirect repair the revert test marks, and both `hard`-sweep orders — with "not its economics" said outright, since the one-move counterfactual carries the negative benefit and the exemption too. |
| AG-02 | Resolved, and wider | The grammar bullet now attributes the rejection to the grammar itself, at config-parse time, and names §11.1's `soft_s < C_s` rule as the *other*, inventory-time surface it therefore never reaches. **A second instance the finding did not name got the same fix**: §5.3.1's "Two validation rules" paragraph closed with "Percentages above 100 are therefore rejected by the same rule", the identical pre-AC-09 attribution, and now says they never reach that rule. Fixing only the bullet would have left the contradiction one paragraph further down. |
| AG-03 | Resolved | §5.3 point 3's "exactly as" is gone. The sentence now says the exemption is plan-level *in the same way* the built `has_reserve_override` short-circuits the aggregate test for the whole plan, but on a deliberately **narrower trigger** than that flag's "some move's source was violating at scheduling time" — with a pointer to §7.3, which states the difference and proves the strict subset, and an explicit "do not read 'plan-level' as 'already built'" for the implementer who reads §5.3 alone. |
| AG-04 | Resolved | §7.3's pinning gains the move set, not just the assignment: "what it will really run" is defined as *after* the hard per-move rules have taken their moves out, the sums are taken over the order minus the refused and deferred moves, and the reason it is well-defined is stated (neither refusal depends on the exemption — both are per-move verdicts on `cost_d`/`duration_d`, computed before the aggregate test is consulted). The saturation deferral is covered alongside the duration rejection: same shape, same hole. §8.1's transient invariant is explicitly excluded, since `order_moves()` enforces it while building the order. Phase 13's row carries the implementation consequence: the refusal computation that today lives inside `evaluate_plan_payback()` must produce its verdicts *before* the trigger's sums are taken, and `_execute_group_plan()`'s `excluded_keys` filtering stops being the only place the drop is applied. |
| AG-05 | Resolved | §9.5's pending note now specifies the surface: `repair_exempt` plus the `reserve_shortfall_bytes_before`/`_after` pair the trigger is computed from, in `--json`'s payback block. The note says why the existing fields do not cover it (`aggregate_ok`/`accepted` do not say *why* the test passed; the per-move `repair` markers cannot, since the redundant-repair plan is exempt with no marked move) and concedes the one thing the finding did not: a consumer *can* re-derive it as `aggregate_ok and ratio < λ`, but only by supplying a `payback_ratio` the block does not carry — re-deriving a verdict the tool already reached is not a specification. The pair is also the first instalment on §16.6's X-07/Y-04 gap: it makes check 2's `Σ r_s = 0` invariant checkable from `plan --json` without the emitted order, and lets check 4's expected files distinguish accepted-on-merit from accepted-by-exemption. Named in phase 13's row too. |
| AG-06 | Resolved | §13's `free_space.soft` hazard row now says the **direct** repair — the move off the short storage — is scheduled first, cites §8.2 exception 1 as the rule that does it, and says an *indirect* repair waits for the spec-only exception 2, "as §14.8's second move shows". The row and the worked example now agree. |
| AG-07 | Resolved | (a) The older capacity-gate parenthetical no longer restates the 127% figure and the fixture's nulling of the gate — it keeps only what the prerequisite paragraph does not say (the gate's ACT lets the engine plan, the requirement makes the solver move, and the isolation claim is about the objective rather than the gate stack) and points at the prerequisite for the arithmetic. (b) The `hard: "10%"` bullet's dip is re-scoped from "for the duration of the mirror" to its actual span: from `601`'s target allocation until `603`'s source volume is observed gone — both mirrors and the drain between them. No number changed; both invariant claims were already correct. |
| AG-08 | Resolved | §3.5's `verify-storages` report gains the resolved `soft_s`/`hard_s` per storage with the level each came from, and the paragraph gives the same argument that put the pattern expansion there: a percentage resolves against each LUN's own capacity, a pattern entry's `free_space` lands on every storage it matched, and the deprecated `min_free_bytes` folds in per storage on top — three ways for one line of config to mean a different number per LUN, and `soft_s` now drives §6's override, §7.3's exemption and §9.5's shortfall lines. Phase 13's row scopes it, **and names the sweep consequence the finding did not**: `docs/manual/25-show-load-and-verify-storages.md` matches none of the row's three greps today, so it joins the phase's file set explicitly rather than being missed by a grep re-run that comes back "exact". |

### 48.1 What a later pass should re-check

As with §46, **these fixes were written by the reviewer who raised the findings** — §47's own
caveat applies again. Three specific things to re-check rather than take on trust:

- **AG-04's fix is the only one with build consequences.** It changes where `Σ r_s` is summed,
  which is a sequencing constraint on a signature change phase 13 has not made yet. Re-check
  that §7.3's wording and the phase-13 row's wording describe the same order of operations, and
  that neither contradicts §7.2's benefit, which is still evaluated against the unfiltered
  `final_breakdown` at `cli.py:2374` — the plan does not (yet) say whether the benefit should
  move with the trigger, and that is a real open question, not an oversight this section closed.
- **AG-05 and AG-08 add specified output** — two JSON fields and one `verify-storages` line —
  to a phase that is already the largest in §12. Neither is load-bearing for the mandate; if
  phase 13 is split, both belong with the reporting half.
- **The §14.8 arithmetic is now verified in full**, as-built counterfactual included, by the
  derivation above. A future change to the fixture's weights invalidates the table in this
  section, not just §14.8's prose.

---

## 49. Twenty-fifth-pass review — the phase 13 implementation

Reviewed `ba1f0eb` ("feat: implement phase 13 free-space requirements"), the implementation commit
of §12's phase 13, against the specification that passes 20-24 built: §5.3.1's grammar and
resolution order, §7.3's outcome trigger and revert test, §8.1's `hard_b` floor, §9.5's reporting,
the (C2) format eligibility the mandate needs, and the three grep-defined sweeps the §12 row
uses to define "done". The method is the one §45/§47 established for implementation passes:
re-derive the fixture arithmetic independently, read every consumer of the changed surfaces, and
check the plan's as-built notes against the code that actually landed — the plan is the
specification, so a shipped behaviour that contradicts it is a finding regardless of how
reasonable the code looks.

The implementation is faithful to the specification on every rule this series examined — with
one exception, and it is not documentation: the resolver's global-`hard: null` path drops the
deprecated `min_free_bytes` floor from the transient charge (AH-01), silently weakening §8.1 for
exactly the upgrading configs the fold exists to protect. Everything else is plan-text and sweep
residue: four as-built passages the implementation commit left describing the pre-implementation
tree (AH-02), a fixture marker the plan says is recorded and is not (AH-03), a display line missing
its specified provenance half (AH-04), a stale `.agents/` note (AH-05), two un-swept replay
inputs (AH-06), an ineffective remedy string in a warning (AH-07), and the manpage's top-level
key list (AH-08).

### 49.1 Verification run

- `make check` at branch tip (`ba1f0eb`): green end to end — fmt-check (black + isort), lint,
  typecheck, **981 passed, 1 warning**, **96.22% line coverage**, `generate_expected.py --check`
  OK, `validate_corpus.py --check` OK, and all three PDF stamps matching their Markdown
  (`sha256sum --check` → OK for the plan, the internals and the manual).
- **§14.8's specified arithmetic reproduced to the digit, two ways.** The independent exhaustive
  oracle (`generate_expected.py`) and the real engine (`test_free_space_repair_fixture.py`,
  which drives the actual `src/` pipeline) agree on: the initial table (`r_packed = 0.5`, free
  2.5/3.2/9.0), `b̄ = 0.51`, the gate's 127%, `E: 0 → 4.10`, `F: 1.607843 → 1.215686`, objective
  5.282843, benefit −123 114 070.59, cost 15 728.64, ratio −7 827.38, `Σ r_s: 0.5 → 0`, both
  revert-test markers `true` (the *indirect* repair — `roomy`'s own move, whose source never
  violated — is marked, exactly as §7.3's marker rule requires), both `hard`-sweep orders
  (603-first at `hard: null`, 601-first at `hard: "10%"` — the reversal), and the
  `soft: 0` counterfactual's no-moves optimum (0.803922).
- **The grammar and the schema match the spec**: percentages outside `0 ≤ N < 100` are rejected
  at parse time (the grammar itself, per AC-09/AG-02 — verified by test), the closed schema
  carries `free_space` at both levels with `soft`/`hard` typed `["string", "number", "null"]`,
  and the two `null`s keep their distinct meanings (global null = "no dip", per-storage null =
  "inherit the global").
- **Validate-as-written-then-fold is built as specified**: `hard ≤ soft` and `soft < C_s` are
  checked against the written values before the fold (`topology.py:290-301`), and an oversized
  *deprecated* floor warns instead of erroring — §5.3.1's one deliberate non-promotion.
- **(C2) format eligibility is one function, everywhere**: `storage_accepts_format()` is called
  by both MILP backends (via the shared `_fixed_zero_pairs()`) and by every heuristic
  candidate-generating helper; a disk already resident on a storage is never fixed away from it;
  and the `lvm`-also-accepts-`qcow2` correction is confirmed against real dogfooding data and
  documented in `60-topology.md` with its PVE 9.2 mechanism.
- **AG-04's sequencing constraint is respected**: `move_costs` verdicts → `excluded_disk_keys`
  → `executed_assignment()` → the two `total_shortfall_bytes()` sums →
  `evaluate_plan_payback()` (`cli.py:2392-2437`), and the execution path filters exactly the
  same set (`rejected_moves | deferred_moves`), so the exemption's move set is precisely what
  runs — a repair a hard rule blocks is correctly *not* exempt, and `96-payback.md` documents
  that consequence.
- **The exemption surface is complete**: `repair_exempt` plus
  `reserve_shortfall_bytes_before`/`_after` in `--json` (`cli.py:1284-1286`), the
  `overridden:` note in human output (996-1002), `[repair]` per move (959-960), and both corpus
  expected files record all of it (`validate_corpus.py --check` passes on the regenerated
  files).
- **`collect.py` writes the resolved per-storage pair and drops the scalar** — the bundle shape
  §16.3 specifies, with the "resolved, not re-derivable" choice `reserve_factor` already made.
- **`order_moves()` keeps §8.2's current-state priority-1 test**: `resolves_reserve_violation`
  survives as a scheduling signal only, never read by payback — and `payback.py`'s docstring
  records the strict-subset property (the outcome trigger can only remove exemptions).
- **The manual documents the block in full** (`10-configuration.md`: grammar, two-level nulls,
  per-storage percentage semantics, the deprecation fold), the safety page extends "never
  traded" to the configured free space, and `27-plan.md` splits the old flag's prose exactly as
  §12's row requires — scheduling half kept, exemption half replaced.

### 49.2 Findings summary

| ID | Severity | Location | Summary |
|----|----------|----------|---------|
| AH-01 | High | `topology.py` `_resolve_free_space()` | Global `hard: null` resolves to the **pre-fold** soft, but the deprecated-key fold raises only soft — so a config carrying `snapshot_reserve.min_free_bytes: 1 TiB` with no `free_space` block gets `soft_s = 1 TiB, hard_s = 0`: the §8.1 transient charge loses the floor the built code charged (`max(f·max(Z,z), min_free_bytes)`), silently (the deprecation warning is deliberately silent in the min_free_bytes-only case), in both the scheduler's model check and `execute.py`'s live re-check. Violates §5.3.1's own "the folded floor keeps the §8.1 predicate exactly as strong as the built check" and §12's "leaves an upgrading deprecated-key config exactly as strong as it is today". The fixture oracle implements the plan correctly (`hard_map = f.soft`, folded) — production disagrees with its own oracle, and no test drives `min_free_bytes > 0` through `build_topology()` to catch it |
| AH-02 | Medium | `IMPLEMENTATION_PLAN.md` §7.3/§9.5/§14.8/§16.6 | `ba1f0eb` changed the code without updating the plan's as-built notes in the same commit (AGENTS §7 rule 7). Four passages now contradict the built state: §14.8's "Two prerequisites" still says the (C2) format rule is "not yet implemented" and `topology.Storage` lacks type/format (both false); §9.5's "As built, phase 13 pending" still says no renderer emits the exemption note, the markers or `repair_exempt` (all false); §7.3's "fc-tier1.expected.json records no per-move flag, so it is untouched" (the branch adds `disk_key`, `repair_markers`, `repair_exempt` and the shortfall pair — the recorded *numbers* are unchanged, the file is not); and §16.6's check-2/check-4 gap bullets still say `Σ r_s` "needs the emitted order, which no `plan --json` field carries" — contradicted by §9.5's own new instalment sentence, added on this branch, and by the `reserve_shortfall_bytes_after` field the corpus expected files now record |
| AH-03 | Low | `tests/fixtures/free-space-repair.expected.json` | The expected file records neither the `requires_format_eligibility: true` marker nor the as-built one-move optimum that §14.8 ("its expected file records the as-built one-move optimum as an explicit `requires_format_eligibility: true` marker") and §12's row say it records — the string exists only in the plan and this file. The marker's purpose (fail loudly before the format rule lands) is moot now that the rule landed in the same commit, but the plan's claim is false, and the AG-01-corrected one-move figures (objective 1.0809, benefit ≈ −6.2×10⁴, ratio −11.8) are recorded nowhere machine-checkable |
| AH-04 | Low | `cli.py` `verify-storages` | Prints the resolved `soft`/`hard` bytes but not "the level each came from" — §3.5's own updated text and §12's row both specify the provenance (global / per-storage literal / pattern / percent-converted / folded), and §3.5's argument for it is exactly that three config shapes can produce one number per LUN that an operator cannot otherwise predict. The manual documents what *is* printed, so no doc lie — the spec is simply half-met |
| AH-05 | Low | `.agents/domain-invariants.md` | The "As built" note added by `0dbd33c` "until phase 13 lands" survived the landing: it still says `soft_s` "is still the global scalar `snapshot_reserve.min_free_bytes` (`reserve.py:143`)" — false on both the claim and the line number (`reserve.py:166` now reads `storage.free_space_soft_bytes`). §12's sweep names this file explicitly |
| AH-06 | Low | `tests/corpus/*/config.yaml` | Both replay inputs still carry `snapshot_reserve.min_free_bytes: 0` with no `free_space` block, though §12's min_free_bytes sweep names them as updated with the scalar→pair replacement — they are the one swept file type the branch did not touch, and they no longer match the shape `collect.py` now writes. Behaviorally identical at 0, but it also means the corpus never exercises the deprecated-key path through the new resolver: the one end-to-end `min_free_bytes > 0` coverage that would have caught AH-01 does not exist |
| AH-07 | Info | `topology.py:304-311` | The oversized-deprecated-floor warning lists "overridden with a smaller `free_space.soft`" as a remedy — ineffective by construction: the fold is `max(soft_written, min_free_bytes)`, so a smaller `free_space.soft` cannot lower the folded floor. The remedy list should be "lowered or removed" only. The branch is also uncovered (no test drives an oversized deprecated floor through `build_topology()`) |
| AH-08 | Low | `man/pve-storage-drs.1.md` | The CONFIGURATION section enumerates the top-level keys and `free_space` is absent — neither the `.1.md` nor the generated page was touched by the branch, and no test guards the manpage's key list against the schema (`test_documentation.py` checks manual↔schema and help↔manpage, not this), so the gap is invisible to `make check`. AGENTS §8.4 makes the top-level key list the manpage's job; `solver`/`schema_version` were already absent pre-branch, but `free_space` is this branch's omission |

### 49.3 AH-01 — global `hard: null` drops the deprecated floor from the transient charge

**Severity:** High
**Where:** `src/proxmox_storage_drs/topology.py:255-312` (`_resolve_free_space`), consumed by
`schedule.transient_invariant_ok()` and `execute.py`'s live re-check (lines 382, 1460).

The resolver computes `hard_bytes = soft_written` when the global `hard` is null (lines 284-288),
then folds the deprecated scalar into soft *only* (line 303: `soft_bytes = max(soft_written,
config.snapshot_reserve.min_free_bytes)`). So for the exact config the fold exists to protect —
`min_free_bytes: 1 TiB`, no `free_space` block at all — the resolved pair is `soft_s = 1 TiB,
hard_s = 0`. Reproduced live against the branch:

```
soft_s = 1.0 TiB   hard_s = 0.0 TiB   warnings=[]
```

The §8.1 transient predicate is `used_b + z_d + max(f_b·max(Z_b, z_d), hard_b) ≤ C_b`, so the
floor component drops from the built `min_free_bytes` (1 TiB) to zero. With the plan's own
motivating shape for the deprecated key — a small largest disk on a big LUN, `f = 2.0`,
`Z_b = 0.1 TiB` — the built check charged `max(0.2, 1.0) = 1.0 TiB`; the branch charges
`max(0.2, 0.0) = 0.2 TiB`. A mirror target may be left 0.8 TiB below the operator's configured
absolute floor, mid-migration, on every storage, and the weakening is **silent**: the
deprecation warning deliberately does not fire for a `min_free_bytes`-only config
(`test_free_space_deprecation_warning_silent_with_only_min_free_bytes` asserts exactly that),
and the fold itself never warns below the oversized case.

This contradicts the specification in its own words, three times over:

- §5.3.1: "`hard: null` (the default) means `hard_s = soft_s`, so the folded floor keeps the
  §8.1 predicate **exactly as strong as** the built `max(f_b·max(Z_b,z_d), min_free_bytes)`
  check" — the folded floor keeps nothing if `hard_s` is the pre-fold soft.
- §12's phase-13 row: "`hard: null` (= `soft`) leaves an upgrading deprecated-key config
  exactly as strong as it is today" — the row's own load-bearing argument for the example
  config's `hard: null`.
- `.agents/domain-invariants.md` §2a: "The default `hard: null` means `hard_s = soft_s`: no dip
  at all, and §8.1 exactly as strong as before free-space requirements existed."

The branch's own test oracle implements the plan correctly — `generate_expected.py`'s ordering
oracle uses `hard_map = hard if hard is not None else f.soft`, where `f.soft` is the *resolved*
(folded) soft — so production disagrees with its own oracle. The fixture cannot catch it
because `free-space-repair.yaml` sets `soft` explicitly (30% → 3.0 TiB) with no `min_free_bytes`,
so folded equals written there. And no test anywhere drives `min_free_bytes > 0` through
`build_topology()` into the transient check: the only such tests are config-level warning tests
(`test_config.py:541-574`), which never load an inventory. A collected bundle bakes the weakened
`hard` in as an explicit value too (`collect.py` writes `s.free_space_hard_bytes` verbatim), so
replays reproduce it as a seemingly deliberate config.

This is S-01/AA-01's class — a shipped correctness bug in the safety-critical path — and it
weakens the very invariant AGENTS §6 point 4 protects. **Recommendation:** resolve global-null
`hard` to the *folded* soft (validation stays pre-fold on the written values, exactly as
§5.3.1's "validate as written, then fold" requires — a written `hard` remains as written and
warned, per the plan's "an operator who then sets `hard` below it is using the new knob for the
dip it exists to allow"); add the missing test (`min_free_bytes > 0`, no `free_space` block,
assert `free_space_hard_bytes == min_free_bytes`); and re-run the corpus and fixtures.

### 49.4 AH-02 — four as-built passages the implementation commit left behind

**Severity:** Medium
**Where:** `IMPLEMENTATION_PLAN.md` §7.3 (line 1997), §9.5 (lines 2458-2478), §14.8 (lines
3228-3250), §16.6 (lines 3852-3880).

AGENTS §7 rule 7 and §7 point 2 require the plan and the code to move together. `ba1f0eb`
touches 46 files; `IMPLEMENTATION_PLAN.md` is not among them — the plan's phase-13 text was
finalized in `4d06dce` and earlier, and its as-built notes still describe the pre-implementation
tree. Four passages are now false:

1. **§14.8's "Two prerequisites"** still says the (C2) format rule "is specified but **not yet
   implemented**: `topology.Storage` does not expose storage type/format, so both solver
   backends currently treat every group storage as an eligible target" — all false:
   `Storage.storage_type`/`allowed_formats` exist (`topology.py:195-196`), both backends fix
   `x_{d,s}=0` via the shared `_fixed_zero_pairs()`, and the heuristic excludes ineligible
   targets. The paragraph's as-built one-move counterfactual is moot with it.
2. **§9.5's "As built, phase 13 pending"** still says the exemption note and the per-move
   `repair` markers "are emitted by no shipped renderer yet — `plan`/`apply` print neither" and
   that the field "reaches `--json` only with phase 13" — all false: `cli.py:996-1002` prints
   the note, 959-960 prints `[repair]`, 1217 emits the field, 1284-1286 emit `repair_exempt`
   and the shortfall pair.
3. **§7.3's fc-tier1 sentence** — "`fc-tier1.expected.json` records no per-move flag, so it is
   untouched" — the branch adds `disk_key`, `aggregate_ok`, `reserve_shortfall_tib_before`/
   `_after`, `repair_exempt` and `repair_markers` to it. The recorded payback numbers are
   indeed unchanged (verified by diff: cost 26 214.4, benefit 1.93×10⁸, ratio 7 344.4,
   `accepted: true` all intact), so the sentence's substance survives; "untouched" does not.
4. **§16.6's check-2/check-4 gap bullets** still say `Σ r_s = 0` "need[s] the emitted *order*,
   which no `plan --json` field carries" and "no expected file can record them" — contradicted
   by §9.5's own new instalment sentence (added on this branch): "check 2's `Σ r_s = 0`
   invariant becomes checkable from `plan --json` without the emitted order", and by the
   `reserve_shortfall_bytes_after` field both corpus expected files now record. The plan now
   disagrees with itself between §9.5 and §16.6.

**Recommendation:** one plan-only commit: delete or convert each as-built note to past tense
with its REVIEW.md ID (the §14.8 prerequisites paragraph in particular — its one-move
counterfactual is now historical), and reconcile §16.6's two bullets with §9.5's instalment
sentence (the `Σ r_s` half of the gap is closed; the emitted-order and objective-breakdown
halves are not). Rebuild and re-stamp the PDF in the same commit.

### 49.5 AH-03 — the fixture's expected file is missing the marker the plan says it records

**Severity:** Low
**Where:** `tests/fixtures/free-space-repair.expected.json` vs §14.8 (lines 3243-3245) and
§12's phase-13 row.

§14.8: "its expected file records the as-built one-move optimum as an explicit
`requires_format_eligibility: true` marker so a premature run fails loudly rather than passing
vacuously." The expected file records neither: `requires_format_eligibility` appears nowhere in
`tests/` (grep — only the plan and this file carry the string), and the file's `cases` list has
one entry (the two-move plan); the one-move optimum (objective 1.0809, benefit ≈ −6.2×10⁴
load·s, ratio −11.8 — the AG-01-corrected figures §14.8 now derives in prose) is recorded
nowhere machine-checkable. Since `ba1f0eb` landed the format rule in the same commit as the
fixture, the marker's failure mode can no longer fire — the premise is gone — but the plan's
claim about the file is false, and the §14.8 paragraph an implementer reads to understand the
fixture's design points at a record that does not exist. **Recommendation:** either record both
(the marker as an inert-but-true field, the one-move case as a second `cases` entry with its
own payback block) or fix the plan to say the marker was dropped because the rule landed in
the same commit — the latter is smaller and honest.

### 49.6 AH-04 — `verify-storages` prints the pair but not the level each came from

**Severity:** Low
**Where:** `src/proxmox_storage_drs/cli.py:3319-3321` vs §3.5 (lines 773-788) and §12's row.

§3.5's updated text — added on this branch — specifies the report carries "the **resolved**
free-space requirement `soft_s`/`hard_s` **with the level each came from**", and §12's row
repeats it ("with the level each came from"). The built renderer prints
`free_space: soft=0 B  hard=0 B` — byte values only. The provenance is the whole point of the
§3.5 paragraph: a percentage resolves against each LUN's own capacity, a pattern entry lands
on every storage it matched, and the deprecated key folds in per storage — "three ways for one
line of config to mean a different number per storage, and this is the one command where that
derivation is visible before a plan depends on it". An operator staring at `soft=3221225472 B`
cannot tell a global `"15%"` from a per-LUN `"30%"` from a folded `min_free_bytes` without
exactly the display this sentence specifies. The manual (`25-show-load-and-verify-storages.md`)
documents what *is* printed, so there is no doc lie — the specification is half-met.
**Recommendation:** extend the line with the provenance (e.g. `soft=3.0TiB (pattern "10%" of
30TiB) hard=1.0TiB (literal)`) and update the manual's sample in the same commit; the
`--json` side already carries the resolved pair and needs only a `source` field if the same
argument applies there.

### 49.7 AH-05 — the `.agents/` "until phase 13 lands" note outlived phase 13

**Severity:** Low
**Where:** `.agents/domain-invariants.md` lines 26-28.

`0dbd33c` added: "**As built:** `soft_s` is still the global scalar
`snapshot_reserve.min_free_bytes` (`reserve.py:143`, `required = max(round(f·largest),
min_free_bytes)`). Phase 13 replaces that scalar with the per-storage `soft_s`/`hard_s` pair
everywhere it is threaded; until it lands, read `soft_s` here as that one number applied to
every storage." Phase 13 landed in `ba1f0eb`; the note is now false on both the claim and the
line number — `reserve.py:166` reads `required = max(round(storage.reserve_factor * largest),
storage.free_space_soft_bytes)`. §12's min_free_bytes sweep names this file explicitly, and the
note is the first thing an agent working on the reserve reads. **Recommendation:** delete the
note (the surrounding §2/§2a text is already correct — and is one of the three plan-equivalent
statements AH-01 violates, which makes removing the stale half more important, not less).

### 49.8 AH-06 — the corpus replay inputs kept the deprecated shape

**Severity:** Low
**Where:** `tests/corpus/bzed-dev-cluster-24h/config.yaml:97`,
`tests/corpus/bzed-dev-cluster-7d-holt-winters/config.yaml:97`.

§12's min_free_bytes sweep names "both `tests/corpus/*/config.yaml` replay inputs" as updated
with the scalar→pair replacement; the branch touched only the two `.expected.json` files. Both
replay inputs still carry `snapshot_reserve: {min_free_bytes: 0}` with no `free_space` block —
no longer the shape `collect.py` writes for a new bundle (per-storage `free_space` pair, scalar
dropped). At `0` the behaviour is identical (the fold is `max(soft, 0)`; global-null hard
resolves to the same 0), so this is sweep-completeness, not behaviour. But it has a testing
cost the sweep's own standard makes worth naming: the corpus is the only end-to-end harness
that drives a *config file* through the full resolver, and with the deprecated key pinned at 0
it never exercises the fold — the one path where AH-01 lives. **Recommendation:** rewrite both
to the new shape (`free_space: {soft: 0, hard: null}`, `min_free_bytes` removed) in the fix
commit for AH-01, and add one corpus- or fixture-level case with `min_free_bytes > 0` so the
fold path has end-to-end coverage from then on.

### 49.9 AH-07 — the oversized-floor warning offers a remedy that cannot work

**Severity:** Info
**Where:** `src/proxmox_storage_drs/topology.py:304-311`.

The warning ends: "until the deprecated key is lowered, removed, or overridden with a smaller
`free_space.soft`". The third remedy is ineffective by the fold's own construction —
`soft_bytes = max(soft_written, min_free_bytes)` — a smaller `free_space.soft` cannot lower a
floor the deprecated key props up; only lowering or removing `min_free_bytes` can. An operator
who follows the warning's advice will conclude the tool is broken. The branch is also
uncovered: `topology.py:305` appears in the coverage report's missing-lines list, and no test
drives an oversized deprecated floor through `build_topology()`. **Recommendation:** drop the
third remedy from the string and add the missing test (an oversized `min_free_bytes` warns and
does not raise — the §5.3.1 non-promotion, which is currently asserted nowhere).

### 49.10 AH-08 — the manpage's top-level key list is missing `free_space`

**Severity:** Low
**Where:** `man/pve-storage-drs.1.md` CONFIGURATION (lines 204-210).

The manpage's CONFIGURATION section enumerates the top-level keys — "Top-level keys:
**proxmox** … **snapshot_reserve**, **load** … **forecast** and **support**" — and `free_space`
is absent: the branch touched neither the `.1.md` nor the generated `.1`. AGENTS §8.4 assigns
the manpage's CONFIGURATION section "the file's location and its top-level keys", and §8.6's
test-enforced cross-references cover manual↔schema (`test_manual_covers_every_schema_key`) and
help↔manpage, but nothing asserts the manpage's key list against the schema — so this gap is
invisible to `make check` and will recur for the next new block. (`solver` and `schema_version`
are also absent from the list, but that predates this branch; `free_space` is this branch's
omission, and the one a reader upgrading for the new feature will look for.)
**Recommendation:** add `free_space` to the list in the same commit that fixes AH-02's plan
text (both are the phase's documentation tail), and add a
`test_manpage_names_every_top_level_schema_key` to `test_documentation.py` so the list cannot
drift again.

### 49.11 What this pass confirms

- **The specification built over passes 20-24 was implemented as written, on every rule this
  series derived**: the grammar and its parse-time rejection, the closed schema at both levels,
  the two `null`s, the per-storage fold, validate-as-written-then-fold, the (C2) format rule in
  one shared function across both backends and the heuristic, the outcome trigger with its
  AG-04 sequencing, the revert test as marker (indirect repairs marked, redundant ones not),
  the `--json`/human exemption surfaces, the bundle's resolved pair, and the manual's split of
  the old flag's prose. The grep-defined sweeps are exact against the tree for
  `resolves_reserve_violation` (now a scheduling signal only, as specified) and
  `evaluate_plan_payback` (the signature change landed with every caller updated).
- **§14.8's arithmetic is now verified three ways** — the twentieth pass's hand derivation, the
  oracle's exhaustive enumeration, and the real engine — and they agree to the digit, including
  the hard-sweep order reversal and the soft:0 counterfactual. The fixture is a genuine
  acceptance test of the mandate, not a self-consistent one.
- **`make check` is green at tip** with the coverage floor cleared by 11 points (96.22% vs the
  85% floor), and the three PDF stamps match their Markdown — the branch's process discipline
  (docs and PDFs in the same commit as the code) held for every artefact it did touch.
- **The one behavioural defect (AH-01) is narrow and precisely bounded**: it requires a
  non-zero `min_free_bytes`, no `free_space` block, and a snapshot term below the deprecated
  floor — and it is invisible to every shipped test, which is the finding's second half.

### 49.12 Assessment

Phase 13 landed the free-space mandate substantially as specified: the mandate's repair
semantics, the exemption's outcome trigger, the revert-test markers and the format rule all
verify against the plan and against independent re-derivation. What this pass adds to the
record is one real defect and a documentation tail. AH-01 is the only finding that changes
behaviour, and it should block the merge to `main`: it silently weakens §8.1 for exactly the
upgrading configs the deprecation fold was designed to protect, it contradicts the plan in
three places, and the branch's own oracle implements the correct rule — so the fix is small,
the test that pins it is easy to write, and the corpus inputs (AH-06) are the natural place to
give it end-to-end coverage. AH-02's four stale passages and AH-08's manpage line are the
phase's unfinished documentation tail — one plan-only commit plus a manpage line, with the PDF
rebuilt in the same commit. AH-03 through AH-07 are small and can follow. None of the eight
undermines the design: the specification is sound, and the implementation now needs to be made
to agree with it in one resolver line and a handful of sentences.

---


## 50. Resolution of twenty-fifth-pass findings (AH-01..AH-08)

Seven fixed, one fixed in a narrower form than the finding asked (AH-06's remedy is refuted; its
concern is addressed another way). Every finding was checked against the tree before acting;
AH-01 was reproduced first, and its two regression tests were confirmed to **fail on the
pre-fix resolver** before the fix went in.

**AH-01 verified.** Reading `_resolve_free_space()` gave the reviewer's account exactly:
`hard_bytes = soft_written` on a global null, then `soft_bytes = max(soft_written,
min_free_bytes)` — so `min_free_bytes: 1 TiB` alone produced `(soft, hard) = (1 TiB, 0)`, against
§5.3.1's "`hard: null` means `hard_s = soft_s`, so the folded floor keeps the §8.1 predicate
exactly as strong". The reviewer is also right that nothing caught it: the only tests with
`min_free_bytes > 0` are config-level warning tests that never build a topology.

| ID | Status | How resolved |
|----|--------|--------------|
| AH-01 | Resolved | `topology._resolve_free_space()` now settles a null `hard` **after** the fold, from the folded `soft_s`. Validation stays on the written values (a written `hard` is still checked against the written `soft` and is never raised by the fold), exactly as §5.3.1 says. Four `build_topology()` tests pin it: deprecated key alone → `(floor, floor)`; a written `hard` below the folded floor stays as written; global-null `hard` follows whichever of written-soft and deprecated floor won the `max()`; and the oversized-floor non-promotion (AH-07). Two of the four fail on the old resolver. Two end-to-end replay tests drive the same path through a captured bundle and through a pre-`free_space` bundle. §5.3.1 gained a paragraph stating the ordering consequence outright — the "validate as written, then fold" list is easy to over-apply to a null, which is how the code came to read it — and `docs/internals/60-topology.md` says the same. |
| AH-02 | Resolved | All four passages verified false against the tree and rewritten: §7.3's fc-tier1 sentence (now records the new fields, notes `repair_exempt: true`, and says every payback *number* is unchanged — checked by diffing the file across the commit), §9.5's "phase 13 pending" note (now "as built": `[repair]`, the exemption note and the JSON fields), §14.8's "Two prerequisites" (the format rule is history, not a gap), and §16.6's check-2/check-4 bullets (the `Σ r_s` half of the gap is closed by `reserve_shortfall_bytes_after`; the order and objective-breakdown halves are not). §12's row was also reconciled. The PDF and its stamp were rebuilt in the same commit. |
| AH-03 | Resolved (plan side) | The smaller remedy the finding offered: §14.8 and §12's row now say the marker was never recorded **because the rule landed in the same commit as the fixture**, so the premature run it guarded against cannot occur. The one-move figures stay where AG-01 derived them (REVIEW.md §48). Recording an inert `requires_format_eligibility: true` field, or a second case for a plan the engine can no longer produce, would add an assertion about a state that no longer exists. |
| AH-04 | Resolved | `verify-storages` prints the level each half came from — `global`, `storage entry`, `pattern /re/`, `…, N% of <capacity>`, `folded from snapshot_reserve.min_free_bytes`, and `= soft (no dip)` for a null `hard` — via a display-only `ResolvedFreeSpace`/`Storage.free_space_*_source` pair that no solver, scheduler or executor path reads. `--json` gets the same two strings. The manual's sample and a legend table were updated; three topology tests and one CLI test (both renderers) cover it. |
| AH-05 | Resolved | The stale "as built … until it lands" note is deleted from `.agents/domain-invariants.md`. The surrounding §2/§2a text was already correct. |
| AH-06 | **Refuted as a remedy; concern addressed** | The finding asks to rewrite both `tests/corpus/*/config.yaml` files to the new shape. Not done, and §12's sweep sentence now says so. A committed bundle is real captured data — `tests/corpus/README.md` calls it "not something to hand-edit freely" and describes exactly one repair path, for a *collector bug* (rebuild the derived file from the bundle's own data, recompute `SHA256SUMS`, record it in the submission note); "make it look like what a newer collector writes" is not that. It would also delete the one piece of evidence that a bundle captured *before* `free_space` still replays: a real operator holding an old bundle is exactly the case the deprecated-key path exists for. Behaviour at `min_free_bytes: 0` is identical either way (`validate_corpus.py --check` passes). What *is* right in the finding is that the fold path had no end-to-end coverage. That is closed without touching captured data: `test_replay.py` now replays (a) a freshly captured bundle from a `min_free_bytes > 0` config and (b) the same bundle with its `config.yaml` rewritten to the pre-`free_space` shape, and asserts both resolve to `(floor, floor)`. |
| AH-07 | Resolved | The warning now offers "lowered or removed" only; the "overridden with a smaller `free_space.soft`" remedy is gone (the finding's argument is right: the fold is a `max()`). A test drives an oversized `min_free_bytes` through `build_topology()`, asserting it warns rather than raises — §5.3.1's one deliberate non-promotion, previously asserted nowhere — and that the string names no ineffective remedy. |
| AH-08 | Resolved, wider | The manpage's top-level key list is now the schema's list. It was wrong in more than the reviewer's three places: besides `free_space`, `schema_version` and `solver` it named **`load`**, which is not a key (`load_weights` is). `test_manpage_names_every_top_level_schema_key` reads `properties` from the shipped schema and fails on any key the CONFIGURATION section does not name in bold — confirmed to fail against the old list, naming all four. |

### 50.1 What a later pass should re-check

- **AH-01's fix changes a shipped number.** A config with a non-zero `min_free_bytes` now plans
  with a *stronger* transient check than the branch tip before it (the correct one, equal to the
  built pre-phase-13 check). Any expected file recorded from such a config — none is committed
  today — would move. Worth one look at any operator-supplied bundle a later pass replays.
- **The provenance strings are free text.** They are display-only by construction (nothing reads
  them), which is why they are plain `str` rather than an enum; if a machine consumer of
  `verify-storages --json` ever appears, that should become a structured field first.
- **`validate_corpus.py`'s `check_invariants()` now asserts the `Σ r_s` invariant** — but as
  `after ≤ before`, not the `= 0` this section first proposed and §16.6 first named: an oversized
  deprecated `min_free_bytes`, or a group with no feasible repair, legitimately ends above zero, so
  `= 0` would false-positive on exactly the configs AH-01 concerns. The lexicographic stage
  minimises `Σ r_s` first, so "never raised" is what actually holds.

---


## Appendix A — Independent verification of the §14 worked example

All values re-derived by hand from §14.1's input.

**Initial state (§14.2).**
- san-a: disks 101:scsi0 (2.0TiB, ℓ=3.0), 101:scsi1 (1.0, 1.0), 102:scsi0 (1.5, 2.5).
  used = 4.5 ✓; L = 6.50 ✓; Z = 2.0 ✓; used+f·Z = 8.5 ✓; violates by 0.5 ✓.
- san-b: 103:scsi0 (0.5, 0.4), 104:scsi0 (1.0, 0.3). used = 1.5 ✓; L = 0.70 ✓; Z = 1.0 ✓;
  3.5 ✓.
- san-c: 105:scsi0 (0.5, 0.2). used = 0.5 ✓; L = 0.20 ✓; Z = 0.5 ✓; 1.5 ✓.
- Σℓ = 7.4 ✓; u* = 2.4667 ✓.
- Spread = (6.50−0.20)/2.4667 = 2.554 → 255% ✓.
- E_before = 4.0333 + 1.7667 + 2.2667 = 8.0667 ✓.

**Three-move solution (§14.3), β=0.25.** Moves: 102:scsi0→san-c, 101:scsi1→san-b,
105:scsi0→san-b.
- san-a: 101:scsi0 only → L=3.0 ✓, used=2.0 ✓, Z=2.0 ✓, 6.0 ✓.
- san-b: 103,104,101:scsi1,105 → L=0.4+0.3+1.0+0.2=1.90 ✓, used=3.0 ✓, Z=1.0 ✓, 5.0 ✓.
- san-c: 102:scsi0 → L=2.50 ✓, used=1.5 ✓, Z=1.5 ✓, 4.5 ✓.
- E_after = 0.5333 + 0.5667 + 0.0333 = 1.1333 ✓; spread = (3.00−1.90)/2.4667 = 44.6% ✓.
- β knob: third move ΔE = 1.5333 − 1.1333 = 0.400 ✓; at β=0.25: −0.400+0.250+0.025 = −0.125
  (accept) ✓; at β=0.50: −0.400+0.500+0.025 = +0.125 (reject) ✓.

**Two-move solution, β=0.50.** Moves: 102:scsi0→san-c, 101:scsi1→san-b; 105 stays on san-c.
- san-a: L=3.0; san-b: L=1.70; san-c: 102+105 → L=2.70. State (3.00, 1.70, 2.70) ✓.
- E = 0.5333 + 0.7667 + 0.2333 = 1.5333 ✓; spread = (3.00−1.70)/2.4667 = 53% ✓.
- This matches the §9.4 output ("san-c u=2.70", "spread 53%") ✓.

**Affinity trade-off (§14.3).** Keeping VM 101 together forces san-a L=4.0, best E=3.133.
Split (with κ=0.5): 1.1333+0.5 = 1.633; together: 3.133+0 = 3.133. Split wins by 1.5 ✓.

**Ordering (§14.4).** 102:scsi0 first (repairs san-a reserve: 4.5→3.0 used, 3.0+4.0=7.0≤8.0 ✓).
Transient checks for all three moves verified: 5.0≤8.0, 4.5≤8.0, 5.0≤8.0 ✓.

**Payback (§14.5), two-move plan.** bwlimit=200 MiB/s, ω=2, H=604800, λ=10.
- 102:scsi0: 1.5 TiB = 1,572,864 MiB / 200 = 7864 s ✓; cost = 2×7864 = 15728 ✓.
- 101:scsi1: 1.0 TiB / 200 = 5243 s ✓; cost = 10486 ✓; Σ = 26214 ✓.
- benefit = ΔE·H = 6.5333×604800 = 3,951,360 ✓; ratio = 3,951,360/26,214 = 150.7 ≥ 10 ✓.
- Failed-payback example (4 TiB, ΔE=0.05): cost=2×20972=41943 ✓; benefit=0.05×604800=30240 ✓;
  ratio=0.72 < 10 ✓.

**Conclusion:** The §14 fixture is fully self-consistent. It can be used directly as an
acceptance test (transcribe to a machine-readable fixture per F-21).

---

## Appendix B — External-fact checks (web search)

- **PVE 9.2 release.** Proxmox VE 9.2 was released 2026-05-21 (Debian 13.5 "Trixie", kernel
  7.0, QEMU 11.0). It introduced a built-in dynamic load balancer. Relevant because the plan
  targets "PVE 9.2"; the built-in balancer is complementary (node-level only) — see F-24.
- **`move_disk` semantics.** Confirmed: `delete=1` removes the source volume after a successful
  `drive-mirror`; the VM stays running (online). Community reports of `delete` occasionally
  leaving an orphaned source volume exist — the plan already handles this in §9.3 (detect and
  report, never auto-delete), which aligns with real-world behavior.
- **blockstat / InfluxDB field and tag names.** Web search did **not** reliably confirm the
  exact field names (`rd_bytes`, etc.) or the `instance=scsi0` tag claim; some search results
  were unreliable. The plan's claims remain plausible and internally consistent, and the
  `verify-metrics` command is the correct validation gate. See F-23.
- **PromQL / VictoriaMetrics.** `quantile_over_time`, subquery ranges, `rate()`, and the
  `/api/v1/label/__name__/values` endpoint are supported by both Prometheus and VictoriaMetrics.
  See F-25.
