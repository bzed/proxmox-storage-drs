#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regenerate the `*.expected.json` files next to their `*.yaml` inputs.

Every expectation is derived by exhaustively enumerating all |S|^|D| assignments,
so the recorded optimum is proven rather than hand-worked. Both section 5.3 solve
paths are covered: the single-stage big-M objective and the preferred
lexicographic two-stage solve, together with the threshold `P` above which the
two provably agree on that fixture. Execution order follows the section 8.2 rule,
with the section 8.1 transient checks recorded per move.

Fixtures:
  fc-tier1          IMPLEMENTATION_PLAN.md section 14, the acceptance example.
  reserve-tradeoff  A group where the reserve and the balance objective genuinely
                    conflict, so the two solve paths disagree unless P is large
                    enough. fc-tier1 cannot show that (see its threshold).
  affinity-repair   Section 14.7: a group whose I/O is already balanced and whose
                    only improving moves are a VM's tiny disks reuniting with it --
                    isolates section 5.4's w_v weighting and D^big exemption, and
                    section 7.2's kappa*dA benefit term, from the payback rule.

Usage:  python3 tests/fixtures/generate_expected.py [--check]
"""

from __future__ import annotations

import itertools
import json
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional, Tuple

try:
    import yaml
except ImportError:  # pragma: no cover - the message is the whole point
    sys.exit("PyYAML required: pip install pyyaml")

Assignment = Dict[str, str]
StorageState = Dict[str, Any]

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = ("fc-tier1", "reserve-tradeoff", "affinity-repair", "free-space-repair")
R = 6  # rounding for recorded values
TIB = 1 << 40


class Deadlock(Exception):
    """No move in the plan is individually feasible (section 8.3)."""


@dataclass(frozen=True)
class Fixture:
    """One group: its storages, its disks and the weights to solve it with.

    ``keys`` is movable disks only -- the set ``all_assignments()`` takes its
    product over. ``pinned_keys`` (section 14.7's ``exclude.vmids`` VMs) never
    appears in a generated assignment; every other per-disk dict (``size``,
    ``load``, ``vmid``, ``current``) spans *both* -- section 5.4's ``l_v``
    sums a VM's full load, pinned disks included, and (C4)/(C5)/(C6)/(C7)
    all count a pinned disk's bytes and load exactly like a movable one's."""

    name: str
    storages: List[str]
    capacity: Dict[str, float]
    weight: Dict[str, float]
    foreign: Dict[str, float]
    saferemove: Dict[str, bool]
    wipe_bps: Dict[str, float]
    reserve_factor: float
    keys: List[str]
    pinned_keys: List[str]
    size: Dict[str, float]
    load: Dict[str, float]
    vmid: Dict[str, int]
    current: Assignment
    objective: Dict[str, Any]
    migration: Dict[str, Any]
    # Section 5.3.1: free_space.soft per storage, TiB -- 0.0 (the default)
    # for every fixture that does not set it, which makes reserve_term()
    # below reduce exactly to `reserve_factor * largest` and leaves the
    # first three fixtures' numbers untouched.
    soft: Dict[str, float]
    # Section 5.3 (C2): the disk formats each storage accepts, and each
    # disk's own format -- ["raw", "qcow2"] / "raw" for every fixture that
    # does not set them, which admits every storage as an eligible target
    # for every disk, exactly as before this field existed.
    allowed_formats: Dict[str, List[str]]
    format: Dict[str, str]
    # Section 14.8 only: the free_space.hard values to sweep (None = "same
    # as soft"), and whether to record the free_space.soft: 0 counterfactual.
    # Empty/False for every other fixture -- both sections are then omitted
    # from the built output entirely.
    hard_sweep_tib: List[Optional[float]]
    counterfactual_soft_zero: bool

    @property
    def all_keys(self) -> List[str]:
        return self.keys + self.pinned_keys

    @property
    def total_load(self) -> float:
        return sum(self.load.values())

    @property
    def u_star(self) -> float:
        return self.total_load / sum(self.weight.values())

    @property
    def b_bar(self) -> float:
        """Section 5.3 (C7): `(Sum_d z_d + Sum_s U^ext) / (Sum_s C_s)` --
        the group's mean fill fraction, a constant like `u_star`."""
        total_used = sum(self.size.values()) + sum(self.foreign.values())
        total_capacity = sum(self.capacity.values())
        return total_used / total_capacity if total_capacity else 0.0

    @property
    def big_m_p(self) -> float:
        return float(self.objective.get("reserve_violation_penalty", 1000.0))

    @property
    def tiny_disk_tib(self) -> float:
        """Section 5.4's `D^big` threshold, converted from the fixture's
        `migration.tiny_disk_bytes` (bytes, matching config.py's own field
        name and unit) into the TiB unit every disk size here is expressed
        in."""
        return float(self.migration.get("tiny_disk_bytes", 0)) / TIB

    @property
    def vm_weights(self) -> Dict[int, float]:
        """Section 5.4's `w_v = max(1, l_v / l_bar)`. `V` (the vmids this
        returns weights for) is derived from movable disks only
        (`objective.affinity_counts_pinned_disks=False`, which every fixture
        here sets explicitly -- the engine's own default is True, and these
        fixtures carry section 14's worked arithmetic, so they state their
        semantics rather than tracking a default); `l_v` sums a VM's *entire* load across
        `all_keys`, pinned included. `l_bar`'s own denominator is wider
        still -- every distinct vmid with a disk in the group at all, not
        just `V` -- section 14.7's own worked number is explicit about this
        (`l_bar = 6.0/3`, dividing by all three of the group's VMs even
        though VM 309, pinned-only, never appears in `V`)."""
        vmids = sorted({self.vmid[k] for k in self.keys})
        if not vmids:
            return {}
        all_vmids = {self.vmid[k] for k in self.all_keys}
        load_per_vm: Dict[int, float] = {v: 0.0 for v in vmids}
        for k in self.all_keys:
            v = self.vmid[k]
            if v in load_per_vm:
                load_per_vm[v] += self.load[k]
        average = sum(self.load[k] for k in self.all_keys) / len(all_vmids)
        if not average:
            return {v: 1.0 for v in vmids}
        return {v: max(1.0, load_per_vm[v] / average) for v in vmids}


def storage_of(f: Fixture, assign: Assignment, key: str) -> str:
    """A disk's storage under `assign` -- `assign` only ever has entries for
    movable disks (`all_assignments()`'s own product), so a pinned disk
    always falls through to its fixed `f.current`."""
    return assign.get(key, f.current[key])


def load_fixture(stem: str) -> Fixture:
    with open(os.path.join(HERE, f"{stem}.yaml")) as fh:
        fx: Dict[str, Any] = yaml.safe_load(fh)
    g = fx["group"]
    disks = fx["disks"]
    movable = [d for d in disks if not d.get("pinned", False)]
    pinned = [d for d in disks if d.get("pinned", False)]
    return Fixture(
        name=stem,
        storages=[s["id"] for s in g["storages"]],
        capacity={s["id"]: float(s["capacity_tib"]) for s in g["storages"]},
        weight={s["id"]: float(s["capability_weight"]) for s in g["storages"]},
        foreign={s["id"]: float(s.get("foreign_used_tib", 0.0)) for s in g["storages"]},
        saferemove={s["id"]: bool(s.get("saferemove", False)) for s in g["storages"]},
        wipe_bps={
            s["id"]: float(s.get("saferemove_throughput_bytes_per_sec", 0.0)) for s in g["storages"]
        },
        reserve_factor=float(g["reserve_factor"]),
        keys=[d["key"] for d in movable],
        pinned_keys=[d["key"] for d in pinned],
        size={d["key"]: float(d["size_tib"]) for d in disks},
        load={d["key"]: float(d["load"]) for d in disks},
        vmid={d["key"]: int(d["vmid"]) for d in disks},
        current={d["key"]: d["current_storage"] for d in disks},
        objective=fx["objective"],
        migration=fx["migration"],
        soft={s["id"]: float(s.get("free_space_soft_tib", 0.0)) for s in g["storages"]},
        allowed_formats={
            s["id"]: list(s.get("allowed_formats", ["raw", "qcow2"])) for s in g["storages"]
        },
        format={d["key"]: d.get("format", "raw") for d in disks},
        hard_sweep_tib=list(fx.get("hard_sweep_tib", [])),
        counterfactual_soft_zero=bool(fx.get("counterfactual_soft_zero", False)),
    )


# --------------------------------------------------------------------------- #
# State of one assignment
# --------------------------------------------------------------------------- #


def eligible_storages(f: Fixture, key: str) -> List[str]:
    """Section 5.3 (C2): every storage whose `allowed_formats` holds this
    disk's own `format` -- the domain `all_assignments()` takes its product
    over, per disk rather than the flat `f.storages` every fixture without
    a format restriction still gets (every storage accepts "raw" by
    default, so this is a no-op there)."""
    return [s for s in f.storages if f.format[key] in f.allowed_formats[s]]


def all_assignments(f: Fixture) -> Iterator[Assignment]:
    """Every eligible placement of the movable disks -- (C2)'s per-disk
    domain restriction folded directly into the product, so an
    ineligible (disk, storage) pair is never even enumerated, matching
    both MILP backends fixing `x_{d,s}=0` for it rather than scoring it
    and losing."""
    domains = [eligible_storages(f, k) for k in f.keys]
    for combo in itertools.product(*domains):
        yield dict(zip(f.keys, combo))


def reserve_term(f: Fixture, s: str, largest: float) -> float:
    """Section 5.3 (C5)/5.3.1: `R_s = max(f_s * Z_s, soft_s)`."""
    return max(f.reserve_factor * largest, f.soft[s])


def largest_on(f: Fixture, assign: Assignment, s: str) -> float:
    return max((f.size[k] for k in f.all_keys if storage_of(f, assign, k) == s), default=0.0)


def used_on(f: Fixture, assign: Assignment, s: str) -> float:
    return f.foreign[s] + sum(f.size[k] for k in f.all_keys if storage_of(f, assign, k) == s)


def per_storage(f: Fixture, assign: Assignment) -> Dict[str, StorageState]:
    """Per-storage load, usage and reserve status for one assignment."""
    out: Dict[str, StorageState] = {}
    for s in f.storages:
        used = used_on(f, assign, s)
        largest = largest_on(f, assign, s)
        term = reserve_term(f, s, largest)
        out[s] = {
            "load": round(sum(f.load[k] for k in f.all_keys if storage_of(f, assign, k) == s), R),
            "used_tib": round(used, R),
            "largest_tib": round(largest, R),
            "required_tib": round(used + term, R),
            "violates_reserve": used + term > f.capacity[s] + 1e-9,
        }
    return out


def E_of(f: Fixture, assign: Assignment) -> float:
    """Section 5.3 (C6) L1 spread, Sum_s |u_s - u*|."""
    return sum(
        abs(
            sum(f.load[k] for k in f.all_keys if storage_of(f, assign, k) == s) / f.weight[s]
            - f.u_star
        )
        for s in f.storages
    )


def F_of(f: Fixture, assign: Assignment) -> float:
    """Section 5.3 (C7) L1 data spread, Sum_s |b_s - b_bar| / b_bar --
    always L1, unlike E_of there is no minmax alternative (section 5.4)."""
    b_bar = f.b_bar
    if not b_bar:
        return 0.0
    return sum(abs(used_on(f, assign, s) / f.capacity[s] - b_bar) / b_bar for s in f.storages)


def slack_of(f: Fixture, assign: Assignment) -> float:
    """Total reserve shortfall Sum_s r_s, in TiB."""
    return sum(
        max(
            0.0,
            used_on(f, assign, s) + reserve_term(f, s, largest_on(f, assign, s)) - f.capacity[s],
        )
        for s in f.storages
    )


def repair_markers(f: Fixture, assign: Assignment) -> Dict[str, bool]:
    """Section 7.3's revert test: for each disk `assign` actually moves,
    would holding it back on its current storage strictly raise the plan's
    total Sum r_s, evaluated on `assign` itself with that one disk held?
    A disk `assign` does not move is not scored -- there is nothing to
    revert."""
    base = slack_of(f, assign)
    markers: Dict[str, bool] = {}
    for k in f.keys:
        if assign[k] == f.current[k]:
            continue
        trial = dict(assign)
        trial[k] = f.current[k]
        markers[k] = slack_of(f, trial) > base + 1e-9
    return markers


def fragmentation(f: Fixture, assign: Assignment) -> float:
    """Section 5.4 kappa term, `A = Sum_v w_v * (extra storages)` -- V from
    movable disks only (objective.affinity_counts_pinned_disks=False, set
    explicitly by every fixture here; the engine's default is True), each
    vmid's own extra-storage
    count weighted by `f.vm_weights` (section 5.4's `w_v`, which sums a
    VM's *entire* load, pinned included -- see that property's docstring).
    """
    weights = f.vm_weights
    return sum(
        weights[v] * (len({assign[k] for k in f.keys if f.vmid[k] == v}) - 1)
        for v in sorted({f.vmid[k] for k in f.keys})
    )


# --------------------------------------------------------------------------- #
# The two solve paths of section 5.3
# --------------------------------------------------------------------------- #


def objective_nonreserve(f: Fixture, assign: Assignment, beta: float, delta: float) -> float:
    """The section 5.4 objective without the reserve term. `beta`/`gamma`
    range over `D^big` only (moved disks at or above `tiny_disk_bytes`,
    section 5.4) -- a tiny disk still counts as "moved" for every other
    purpose (`moves_of()`, ordering), just not for these two terms."""
    moved = [k for k in f.keys if assign[k] != f.current[k]]
    big_moved = [k for k in moved if f.size[k] >= f.tiny_disk_tib]
    return float(
        f.objective["alpha_spread"] * E_of(f, assign)
        + beta * len(big_moved)
        + f.objective["gamma_move_bytes_per_tib"] * sum(f.size[k] for k in big_moved)
        + f.objective["kappa_vm_affinity"] * fragmentation(f, assign)
        + delta * F_of(f, assign)
    )


def objective_big_m(f: Fixture, assign: Assignment, beta: float, delta: float, p: float) -> float:
    """Single-stage big-M objective: section 5.4 plus P * Sum_s r_s."""
    return objective_nonreserve(f, assign, beta, delta) + p * slack_of(f, assign)


def best_big_m(f: Fixture, beta: float, delta: float, p: float) -> Tuple[Assignment, float]:
    """Exhaustive minimum of the single-stage big-M objective at penalty p."""
    best: Assignment = {}
    best_val = float("inf")
    for a in all_assignments(f):
        v = objective_big_m(f, a, beta, delta, p)
        if v < best_val - 1e-12:
            best, best_val = a, v
    return best, best_val


def best_lexicographic(f: Fixture, beta: float, delta: float) -> Tuple[Assignment, float, float]:
    """Section 5.3 option 1: minimise Sum_s r_s first, then the rest.

    Returns (assignment, minimum total slack, non-reserve objective). No penalty
    weight is involved, so the answer cannot depend on the calibration of P.
    """
    min_slack = min(slack_of(f, a) for a in all_assignments(f))
    best: Assignment = {}
    best_val = float("inf")
    for a in all_assignments(f):
        if slack_of(f, a) > min_slack + 1e-12:
            continue
        v = objective_nonreserve(f, a, beta, delta)
        if v < best_val - 1e-12:
            best, best_val = a, v
    return best, min_slack, best_val


def big_m_agreement_threshold(f: Fixture, beta: float, delta: float) -> float:
    """Smallest P above which big-M provably matches the lexicographic solve.

    Big-M prefers a higher-slack assignment `a` over the lexicographic optimum
    `a*` exactly when `P * (slack(a) - slack_min) < obj_nr(a*) - obj_nr(a)`, so
    the threshold is the largest such ratio over every assignment carrying more
    slack than the minimum. `-inf` means no reserve-violating assignment can win
    at any P >= 0 -- the fixture simply does not exercise the distinction.
    """
    _, min_slack, best_nr = best_lexicographic(f, beta, delta)
    threshold = float("-inf")
    for a in all_assignments(f):
        extra = slack_of(f, a) - min_slack
        if extra <= 1e-12:
            continue
        threshold = max(threshold, (best_nr - objective_nonreserve(f, a, beta, delta)) / extra)
    return threshold


def computed_p_min(f: Fixture, beta: float, delta: float) -> float:
    """The section 5.3 build-time bound: U_obj / eps_r, with eps_r = 1 MiB.
    The kappa term's per-vmid worst case is `max_v w_v`, not a flat 1 --
    section 5.4's w_v can exceed 1 for an above-average-load VM, and this
    bound must stay a genuine upper bound regardless."""
    max_w = max(f.vm_weights.values(), default=1.0)
    u_obj = (
        2 * f.objective["alpha_spread"] * f.total_load
        + beta * len(f.keys)
        + f.objective["gamma_move_bytes_per_tib"] * sum(f.size.values())
        + f.objective["kappa_vm_affinity"]
        * max_w
        * len(set(f.vmid.values()))
        * (len(f.storages) - 1)
        + delta * 2 * len(f.storages)
    )
    return float(u_obj * (1 << 20))


# --------------------------------------------------------------------------- #
# Section 7.1 cost, section 8.2 ordering
# --------------------------------------------------------------------------- #


def duration_mirror(f: Fixture, key: str) -> float:
    """Section 7.1 drive-mirror time, seconds."""
    return f.size[key] * TIB / float(f.migration["bwlimit_bytes_per_sec"])


def duration_wipe(f: Fixture, key: str) -> float:
    """Section 7.1 saferemove zeroing time on the SOURCE storage, seconds.

    Zero unless the fixture both enables the accounting and marks the source
    storage as wiping. The section 14.5 arithmetic runs with it disabled.
    """
    src = f.current[key]
    if not f.migration.get("account_saferemove_wipe", True) or not f.saferemove[src]:
        return 0.0
    return f.size[key] * TIB / f.wipe_bps[src]


def duration(f: Fixture, key: str) -> float:
    return duration_mirror(f, key) + duration_wipe(f, key)


def cost(f: Fixture, key: str) -> float:
    """Section 7.1 cost in load-seconds: mirror on both ends, wipe on the
    source. Zero below `tiny_disk_bytes` (section 5.4/7.1) -- duration
    itself is unaffected, only the cost charged for it."""
    if f.size[key] < f.tiny_disk_tib:
        return 0.0
    omega_mirror = float(f.migration["source_load_weight"] + f.migration["target_load_weight"])
    omega_wipe = float(f.migration.get("wipe_load_weight", 1.0))
    return duration_mirror(f, key) * omega_mirror + duration_wipe(f, key) * omega_wipe


def order_moves(
    f: Fixture, target: Assignment, delta: float, hard: Optional[Dict[str, float]] = None
) -> List[Dict[str, Any]]:
    """Section 8.2 greedy, with the two priority exceptions.

    Raises Deadlock if no pending move satisfies the section 8.1 transient
    invariant -- which is what a plan that breaches the reserve looks like at
    schedule time. ``delta`` is the case's own swept
    ``delta_capacity_spread`` -- not read from ``f.objective``, which never
    carries a static value for it (only the ``delta_values`` sweep list).

    ``hard`` is section 5.3.1's per-storage transient floor -- defaults to
    ``f.soft`` (every fixture but free-space-repair never sets ``hard``
    differently from ``soft``, so this is a no-op there): the endpoint
    check inside ``per_storage()`` above always uses ``f.soft`` via
    ``reserve_term()``, but the *transient* feasibility check below uses
    this floor instead, per section 8.1's own distinction.
    """
    hard_map = hard if hard is not None else f.soft
    state = dict(f.current)
    pending = [k for k in f.keys if target[k] != f.current[k]]
    out: List[Dict[str, Any]] = []
    while pending:
        st = per_storage(f, state)
        # Section 8.2: feasibility is checked over EVERY pending move
        # first; priority-1 (source currently violating) then narrows
        # *which feasible move* is picked, exactly like the real
        # schedule.order_moves() -- restricting feasibility itself to the
        # violating-source subset (an earlier version of this function
        # did) can deadlock a plan the real scheduler orders just fine by
        # picking a different, still-feasible move first (section 14.8's
        # own free-space-repair fixture is what proves the two
        # implementations must agree here).
        feasible = []
        for k in pending:
            b = target[k]
            basis = max(st[b]["largest_tib"], f.size[k])
            floor = max(f.reserve_factor * basis, hard_map[b])
            if st[b]["used_tib"] + f.size[k] + floor <= f.capacity[b] + 1e-9:
                feasible.append(k)
        if not feasible:
            raise Deadlock(f"no feasible move among {sorted(pending)}")
        violating = {s for s, v in st.items() if v["violates_reserve"]}
        prio = [k for k in feasible if state[k] in violating] or feasible

        def ratio(k: str, _state: Assignment = state) -> float:
            # Section 8.2's revised ranking: "the alpha, delta and kappa*w
            # terms of section 5.4 -- the parts whose improvement persists;
            # beta/gamma are one-time costs." A move below tiny_disk_bytes
            # (cost 0) ranks first outright -- "free value, delivered
            # before anything pays" -- not merely via its own raw
            # persistent_reduction, which would not dominate a competing
            # nonzero-cost candidate.
            nxt = dict(_state)
            nxt[k] = target[k]
            alpha = float(f.objective["alpha_spread"])
            kappa = float(f.objective["kappa_vm_affinity"])
            persistent_reduction = (
                alpha * (E_of(f, _state) - E_of(f, nxt))
                + delta * (F_of(f, _state) - F_of(f, nxt))
                + kappa * (fragmentation(f, _state) - fragmentation(f, nxt))
            )
            c = cost(f, k)
            return float("inf") if c == 0.0 else persistent_reduction / c

        pick = max(prio, key=ratio)
        b = target[pick]
        used_b = st[b]["used_tib"]
        basis = max(st[b]["largest_tib"], f.size[pick])
        floor = max(f.reserve_factor * basis, hard_map[b])
        out.append(
            {
                "disk_key": pick,
                "move": f"{pick}:{state[pick]}->{b}",
                "transient_target_used_tib": round(used_b + f.size[pick], R),
                "transient_reserve_basis_tib": round(basis, R),
                "transient_required_tib": round(used_b + f.size[pick] + floor, R),
                "capacity_tib": f.capacity[b],
                "ok": True,
            }
        )
        state[pick] = b
        pending.remove(pick)
    return out


def try_order(
    f: Fixture, target: Assignment, delta: float, hard: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """order_moves, but record a deadlock instead of raising."""
    try:
        return {"orderable": True, "order": order_moves(f, target, delta, hard)}
    except Deadlock as exc:
        return {"orderable": False, "blocked_reason": str(exc)}


# --------------------------------------------------------------------------- #
# Assembly
# --------------------------------------------------------------------------- #


def moves_of(f: Fixture, assign: Assignment) -> List[str]:
    return [f"{k}:{f.current[k]}->{assign[k]}" for k in sorted(f.keys) if assign[k] != f.current[k]]


def spread(f: Fixture, state: Dict[str, StorageState]) -> float:
    per_unit = [float(state[s]["load"]) / f.weight[s] for s in f.storages]
    return (max(per_unit) - min(per_unit)) / f.u_star


def capacity_spread(f: Fixture, state: Dict[str, StorageState]) -> float:
    """Section 6's capacity-gate ratio, `(max_s b_s - min_s b_s) / b_bar`
    -- the gate-check quantity, distinct from `F_of()`'s sum-of-deviations
    objective term, the same way `spread()` is distinct from `E_of()`."""
    b_bar = f.b_bar
    if not b_bar:
        return 0.0
    per_unit = [float(state[s]["used_tib"]) / f.capacity[s] for s in f.storages]
    return (max(per_unit) - min(per_unit)) / b_bar


def case_for(f: Fixture, beta: float, delta: float) -> Dict[str, Any]:
    """One (beta, delta) pair: the big-M optimum, the lexicographic optimum, and order."""
    a, val = best_big_m(f, beta, delta, f.big_m_p)
    final = per_storage(f, a)
    lex_a, lex_slack, lex_nr = best_lexicographic(f, beta, delta)
    threshold = big_m_agreement_threshold(f, beta, delta)

    case: Dict[str, Any] = {
        "beta_move_count": beta,
        "delta_capacity_spread": delta,
        # Unrounded, for the payback arithmetic; not written to the expected file.
        "_exact_E_after": E_of(f, a),
        "_exact_F_after": F_of(f, a),
        "_exact_A_after": fragmentation(f, a),
        "_assignment": a,
        "expected_objective": round(val, R),
        "expected_move_count": len(moves_of(f, a)),
        "expected_E_after": round(E_of(f, a), R),
        "expected_F_after": round(F_of(f, a), R),
        "expected_fragmentation": round(fragmentation(f, a), R),
        "expected_moves": moves_of(f, a),
        "expected_order": order_moves(f, a, delta),
        "expected_final_loads": {s: final[s]["load"] for s in f.storages},
        "expected_final_reserve": final,
        "expected_spread_after": round(spread(f, final), R),
        "expected_capacity_spread_after": round(capacity_spread(f, final), R),
        # Section 5.3 option 1, the preferred solve. Recorded so an implementer
        # of the lexicographic path has something to assert against, rather than
        # only the big-M path above.
        "lexicographic": {
            "min_total_slack_tib": round(lex_slack, R),
            "expected_objective_nonreserve": round(lex_nr, R),
            "expected_move_count": len(moves_of(f, lex_a)),
            "expected_moves": moves_of(f, lex_a),
            "agrees_with_big_m_at_configured_p": lex_a == a,
            # Big-M with P above this value provably picks the lexicographic
            # optimum on this fixture. null means no reserve-violating
            # assignment can win at any P, so the fixture does not exercise the
            # distinction at all.
            "big_m_agreement_threshold_p": (
                None if threshold == float("-inf") else round(threshold, R)
            ),
            "big_m_p_configured": f.big_m_p,
            "big_m_p_min_computed": round(computed_p_min(f, beta, delta), 3),
        },
    }

    demo_p = f.objective.get("big_m_undersized_p_demo")
    if demo_p is not None:
        demo_a, demo_val = best_big_m(f, beta, delta, float(demo_p))
        demo = {
            "p": float(demo_p),
            "expected_objective": round(demo_val, R),
            "expected_moves": moves_of(f, demo_a),
            "total_slack_tib": round(slack_of(f, demo_a), R),
            "matches_lexicographic": demo_a == lex_a,
        }
        demo.update(try_order(f, demo_a, delta))
        case["big_m_undersized_p_demo"] = demo
    return case


def payback(
    f: Fixture,
    case: Dict[str, Any],
    e_after: float,
    f_after: float,
    a_after: float,
    assignment: Optional[Assignment] = None,
) -> Dict[str, Any]:
    """Section 7.2 payback arithmetic for one case:
    ``benefit = (alpha*(E_before-E_after) + delta*(F_before-F_after) +
    kappa*(A_before-A_after)) * H``.

    `e_after`/`f_after`/`a_after` are the EXACT objective of the chosen
    assignment. Taking them from `case["expected_E_after"]`/
    `case["expected_F_after"]`/`case["expected_fragmentation"]` instead would
    mix an exact *_before with a 6-decimal-rounded *_after and shift the
    recorded benefit off the section 14.5 value by a fraction of a
    load-second. A plan whose every move is below `tiny_disk_bytes` costs
    0 (section 7.1) -- `ratio` is then `inf`, matching `payback.py`'s own
    `PaybackResult.ratio` property, and `accepted` needs no guard since
    `benefit >= payback_ratio * 0` degrades to `benefit >= 0` correctly on
    its own.
    """
    keys = [m.split(":")[0] + ":" + m.split(":")[1] for m in case["expected_moves"]]
    per_move = [
        {
            "disk": k,
            "size_tib": f.size[k],
            "duration_mirror_seconds": round(duration_mirror(f, k), 2),
            "duration_wipe_seconds": round(duration_wipe(f, k), 2),
            "duration_seconds": round(duration(f, k), 2),
            "cost_load_seconds": round(cost(f, k), 2),
        }
        for k in keys
    ]
    total_cost = sum(cost(f, k) for k in keys)
    alpha = float(f.objective["alpha_spread"])
    kappa = float(f.objective["kappa_vm_affinity"])
    delta_weight = float(case["delta_capacity_spread"])
    delta_e = E_of(f, f.current) - e_after
    delta_f = F_of(f, f.current) - f_after
    delta_a = fragmentation(f, f.current) - a_after
    benefit = (alpha * delta_e + delta_weight * delta_f + kappa * delta_a) * float(
        f.migration["payback_horizon_seconds"]
    )
    aggregate_ok = benefit >= float(f.migration["payback_ratio"]) * total_cost
    out = {
        "beta_move_count": case["beta_move_count"],
        "delta_capacity_spread": case["delta_capacity_spread"],
        "per_move": per_move,
        "total_cost_load_seconds": round(total_cost, 2),
        "benefit_load_seconds": round(benefit, 2),
        # null (not a JSON-unsafe Infinity) when every move costs 0 --
        # matching payback.py's own PaybackResult.ratio, which returns
        # float("inf") for the identical case (see "big_m_agreement_
        # threshold_p" above for the same None-for-unbounded convention).
        "ratio": round(benefit / total_cost, 2) if total_cost else None,
        "aggregate_ok": aggregate_ok,
    }
    if assignment is not None:
        # Section 7.3's outcome trigger: repair_exempt iff this plan's own
        # final Sum r_s is strictly below the current assignment's --
        # independent of aggregate_ok, and overriding it when True.
        current_slack = slack_of(f, f.current)
        final_slack = slack_of(f, assignment)
        repair_exempt = final_slack < current_slack - 1e-9
        out["reserve_shortfall_tib_before"] = round(current_slack, R)
        out["reserve_shortfall_tib_after"] = round(final_slack, R)
        out["repair_exempt"] = repair_exempt
        out["accepted"] = aggregate_ok or repair_exempt
        out["repair_markers"] = repair_markers(f, assignment)
    else:
        out["accepted"] = aggregate_ok
    return out


def build(f: Fixture) -> Dict[str, Any]:
    """Derive the whole expected file for one fixture."""
    initial = per_storage(f, f.current)
    delta_values = f.objective.get("delta_values", [0.0])
    cases = [
        case_for(f, float(beta), float(delta))
        for beta, delta in itertools.product(f.objective["beta_values"], delta_values)
    ]

    out: Dict[str, Any] = {
        "schema_version": 1,
        "generated_by": "tests/fixtures/generate_expected.py (exhaustive enumeration)",
        # Stated explicitly so the payback numbers below are reproducible without
        # reading the plan prose for the saferemove assumption.
        "assumptions": {
            "account_saferemove_wipe": bool(f.migration.get("account_saferemove_wipe", True)),
            "wipe_load_weight": f.migration.get("wipe_load_weight", 1.0),
            "saferemove_by_storage": {s: f.saferemove[s] for s in f.storages},
        },
        "derived": {
            "total_load": round(f.total_load, R),
            "u_star": round(f.u_star, R),
            "b_bar": round(f.b_bar, R),
            "initial": initial,
            "E_before": round(E_of(f, f.current), R),
            "F_before": round(F_of(f, f.current), R),
            "spread_before": round(spread(f, initial), R),
            "capacity_spread_before": round(capacity_spread(f, initial), R),
        },
        "cases": [{k: v for k, v in c.items() if not k.startswith("_")} for c in cases],
    }

    # The section 14.3/14.5 worked example at the defaults: beta=0.25,
    # delta=0.5 -- the two-move plan. Falls back to any two-move case if
    # the defaults are not in the sweep (not the case for either fixture).
    two_move = [
        c
        for c in cases
        if c["expected_move_count"] == 2
        and c["beta_move_count"] == 0.25
        and c["delta_capacity_spread"] == 0.5
    ] or [c for c in cases if c["expected_move_count"] == 2]
    if two_move:
        chosen = two_move[0]
        out["payback_two_move_plan"] = payback(
            f,
            chosen,
            chosen["_exact_E_after"],
            chosen["_exact_F_after"],
            chosen["_exact_A_after"],
            chosen["_assignment"],
        )
        # Section 14.5's counter-example: a 4 TiB archive disk whose
        # relocation improves E by only 0.01 and leaves the data spread
        # essentially unchanged (delta*F contributes ~0) -- alpha/delta at
        # the same defaults as the two-move plan above.
        arch_size, arch_delta_e, arch_delta_f = 4.0, 0.01, 0.0
        alpha = float(f.objective["alpha_spread"])
        delta_weight = float(chosen["delta_capacity_spread"])
        omega = float(f.migration["source_load_weight"] + f.migration["target_load_weight"])
        # saferemove is off in this fixture, so there is no wipe term to add.
        arch_cost = arch_size * TIB / float(f.migration["bwlimit_bytes_per_sec"]) * omega
        arch_benefit = (alpha * arch_delta_e + delta_weight * arch_delta_f) * float(
            f.migration["payback_horizon_seconds"]
        )
        out["payback_rejected_archive_disk"] = {
            "size_tib": arch_size,
            "delta_E": arch_delta_e,
            "delta_F": arch_delta_f,
            "cost_load_seconds": round(arch_cost, 2),
            "benefit_load_seconds": round(arch_benefit, 2),
            "ratio": round(arch_benefit / arch_cost, 3),
            "accepted": arch_benefit / arch_cost >= float(f.migration["payback_ratio"]),
        }

    # Section 14.8's own two additions, both keyed off the SAME optimal
    # target assignment `two_move` already chose above -- the hard sweep
    # only ever changes *ordering* (section 8.1's transient floor), never
    # the target itself, and the counterfactual is a wholly separate solve
    # against a modified `f.soft`, not a different case of this one.
    if two_move and f.hard_sweep_tib:
        chosen = two_move[0]
        assignment = chosen["_assignment"]
        delta = float(chosen["delta_capacity_spread"])
        sweep = []
        for hard_tib in f.hard_sweep_tib:
            hard_map = {s: (f.soft[s] if hard_tib is None else float(hard_tib)) for s in f.storages}
            entry: Dict[str, Any] = {"hard_tib": hard_tib}
            entry.update(try_order(f, assignment, delta, hard_map))
            sweep.append(entry)
        out["hard_sweep"] = sweep

    if f.counterfactual_soft_zero:
        zero_soft = Fixture(**{**f.__dict__, "soft": {s: 0.0 for s in f.storages}})
        beta0 = float(f.objective["beta_values"][0])
        delta0 = float(f.objective.get("delta_values", [0.0])[0])
        zero_a, zero_val = best_big_m(zero_soft, beta0, delta0, zero_soft.big_m_p)
        out["counterfactual_free_space_soft_zero"] = {
            "beta_move_count": beta0,
            "delta_capacity_spread": delta0,
            "expected_objective": round(zero_val, R),
            "expected_moves": moves_of(zero_soft, zero_a),
            "expected_move_count": len(moves_of(zero_soft, zero_a)),
        }
    return out


def main(argv: List[str]) -> int:
    check = "--check" in argv
    stale: List[str] = []
    for stem in FIXTURES:
        text = json.dumps(build(load_fixture(stem)), indent=2) + "\n"
        path = os.path.join(HERE, f"{stem}.expected.json")
        if check:
            current: Optional[str] = None
            if os.path.exists(path):
                with open(path) as fh:
                    current = fh.read()
            if current != text:
                stale.append(f"{stem}.expected.json")
            continue
        with open(path, "w") as fh:
            fh.write(text)
        print(f"wrote {path}")
    if stale:
        print(f"stale, re-run without --check: {', '.join(stale)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
