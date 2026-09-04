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
FIXTURES = ("fc-tier1", "reserve-tradeoff")
R = 6  # rounding for recorded values
TIB = 1 << 40


class Deadlock(Exception):
    """No move in the plan is individually feasible (section 8.3)."""


@dataclass(frozen=True)
class Fixture:
    """One group: its storages, its disks and the weights to solve it with."""

    name: str
    storages: List[str]
    capacity: Dict[str, float]
    weight: Dict[str, float]
    foreign: Dict[str, float]
    saferemove: Dict[str, bool]
    wipe_bps: Dict[str, float]
    reserve_factor: float
    keys: List[str]
    size: Dict[str, float]
    load: Dict[str, float]
    vmid: Dict[str, int]
    current: Assignment
    objective: Dict[str, Any]
    migration: Dict[str, Any]

    @property
    def total_load(self) -> float:
        return sum(self.load.values())

    @property
    def u_star(self) -> float:
        return self.total_load / sum(self.weight.values())

    @property
    def big_m_p(self) -> float:
        return float(self.objective.get("reserve_violation_penalty", 1000.0))


def load_fixture(stem: str) -> Fixture:
    with open(os.path.join(HERE, f"{stem}.yaml")) as fh:
        fx: Dict[str, Any] = yaml.safe_load(fh)
    g = fx["group"]
    disks = fx["disks"]
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
        keys=[d["key"] for d in disks],
        size={d["key"]: float(d["size_tib"]) for d in disks},
        load={d["key"]: float(d["load"]) for d in disks},
        vmid={d["key"]: int(d["vmid"]) for d in disks},
        current={d["key"]: d["current_storage"] for d in disks},
        objective=fx["objective"],
        migration=fx["migration"],
    )


# --------------------------------------------------------------------------- #
# State of one assignment
# --------------------------------------------------------------------------- #


def all_assignments(f: Fixture) -> Iterator[Assignment]:
    """Every |S|^|D| placement of the movable disks."""
    for combo in itertools.product(f.storages, repeat=len(f.keys)):
        yield dict(zip(f.keys, combo))


def largest_on(f: Fixture, assign: Assignment, s: str) -> float:
    return max((f.size[k] for k in f.keys if assign[k] == s), default=0.0)


def used_on(f: Fixture, assign: Assignment, s: str) -> float:
    return f.foreign[s] + sum(f.size[k] for k in f.keys if assign[k] == s)


def per_storage(f: Fixture, assign: Assignment) -> Dict[str, StorageState]:
    """Per-storage load, usage and reserve status for one assignment."""
    out: Dict[str, StorageState] = {}
    for s in f.storages:
        used = used_on(f, assign, s)
        largest = largest_on(f, assign, s)
        out[s] = {
            "load": round(sum(f.load[k] for k in f.keys if assign[k] == s), R),
            "used_tib": round(used, R),
            "largest_tib": round(largest, R),
            "required_tib": round(used + f.reserve_factor * largest, R),
            "violates_reserve": used + f.reserve_factor * largest > f.capacity[s] + 1e-9,
        }
    return out


def E_of(f: Fixture, assign: Assignment) -> float:
    """Section 5.3 (C6) L1 spread, Sum_s |u_s - u*|."""
    return sum(
        abs(sum(f.load[k] for k in f.keys if assign[k] == s) / f.weight[s] - f.u_star)
        for s in f.storages
    )


def slack_of(f: Fixture, assign: Assignment) -> float:
    """Total reserve shortfall Sum_s r_s, in TiB."""
    return sum(
        max(
            0.0,
            used_on(f, assign, s) + f.reserve_factor * largest_on(f, assign, s) - f.capacity[s],
        )
        for s in f.storages
    )


def fragmentation(f: Fixture, assign: Assignment) -> int:
    """Section 5.4 kappa term: extra storages a VM's disks are spread over."""
    return sum(
        len({assign[k] for k in f.keys if f.vmid[k] == v}) - 1
        for v in sorted({f.vmid[k] for k in f.keys})
    )


# --------------------------------------------------------------------------- #
# The two solve paths of section 5.3
# --------------------------------------------------------------------------- #


def objective_nonreserve(f: Fixture, assign: Assignment, beta: float) -> float:
    """The section 5.4 objective without the reserve term."""
    moved = [k for k in f.keys if assign[k] != f.current[k]]
    return float(
        f.objective["alpha_spread"] * E_of(f, assign)
        + beta * len(moved)
        + f.objective["gamma_move_bytes_per_tib"] * sum(f.size[k] for k in moved)
        + f.objective["kappa_vm_affinity"] * fragmentation(f, assign)
    )


def objective_big_m(f: Fixture, assign: Assignment, beta: float, p: float) -> float:
    """Single-stage big-M objective: section 5.4 plus P * Sum_s r_s."""
    return objective_nonreserve(f, assign, beta) + p * slack_of(f, assign)


def best_big_m(f: Fixture, beta: float, p: float) -> Tuple[Assignment, float]:
    """Exhaustive minimum of the single-stage big-M objective at penalty p."""
    best: Assignment = {}
    best_val = float("inf")
    for a in all_assignments(f):
        v = objective_big_m(f, a, beta, p)
        if v < best_val - 1e-12:
            best, best_val = a, v
    return best, best_val


def best_lexicographic(f: Fixture, beta: float) -> Tuple[Assignment, float, float]:
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
        v = objective_nonreserve(f, a, beta)
        if v < best_val - 1e-12:
            best, best_val = a, v
    return best, min_slack, best_val


def big_m_agreement_threshold(f: Fixture, beta: float) -> float:
    """Smallest P above which big-M provably matches the lexicographic solve.

    Big-M prefers a higher-slack assignment `a` over the lexicographic optimum
    `a*` exactly when `P * (slack(a) - slack_min) < obj_nr(a*) - obj_nr(a)`, so
    the threshold is the largest such ratio over every assignment carrying more
    slack than the minimum. `-inf` means no reserve-violating assignment can win
    at any P >= 0 -- the fixture simply does not exercise the distinction.
    """
    _, min_slack, best_nr = best_lexicographic(f, beta)
    threshold = float("-inf")
    for a in all_assignments(f):
        extra = slack_of(f, a) - min_slack
        if extra <= 1e-12:
            continue
        threshold = max(threshold, (best_nr - objective_nonreserve(f, a, beta)) / extra)
    return threshold


def computed_p_min(f: Fixture, beta: float) -> float:
    """The section 5.3 build-time bound: U_obj / eps_r, with eps_r = 1 MiB."""
    u_obj = (
        2 * f.objective["alpha_spread"] * f.total_load
        + beta * len(f.keys)
        + f.objective["gamma_move_bytes_per_tib"] * sum(f.size.values())
        + f.objective["kappa_vm_affinity"] * len(set(f.vmid.values())) * (len(f.storages) - 1)
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
    """Section 7.1 cost in load-seconds: mirror on both ends, wipe on the source."""
    omega_mirror = float(f.migration["source_load_weight"] + f.migration["target_load_weight"])
    omega_wipe = float(f.migration.get("wipe_load_weight", 1.0))
    return duration_mirror(f, key) * omega_mirror + duration_wipe(f, key) * omega_wipe


def order_moves(f: Fixture, target: Assignment) -> List[Dict[str, Any]]:
    """Section 8.2 greedy, with the two priority exceptions.

    Raises Deadlock if no pending move satisfies the section 8.1 transient
    invariant -- which is what a plan that breaches the reserve looks like at
    schedule time.
    """
    state = dict(f.current)
    pending = [k for k in f.keys if target[k] != f.current[k]]
    out: List[Dict[str, Any]] = []
    while pending:
        st = per_storage(f, state)
        violating = {s for s, v in st.items() if v["violates_reserve"]}
        prio = [k for k in pending if state[k] in violating] or pending
        feasible = []
        for k in prio:
            b = target[k]
            basis = max(st[b]["largest_tib"], f.size[k])
            if st[b]["used_tib"] + f.size[k] + f.reserve_factor * basis <= f.capacity[b] + 1e-9:
                feasible.append(k)
        if not feasible:
            raise Deadlock(f"no feasible move among {sorted(pending)}")

        def ratio(k: str, _state: Assignment = state) -> float:
            nxt = dict(_state)
            nxt[k] = target[k]
            return (E_of(f, _state) - E_of(f, nxt)) / cost(f, k)

        pick = max(feasible, key=ratio)
        b = target[pick]
        used_b = st[b]["used_tib"]
        basis = max(st[b]["largest_tib"], f.size[pick])
        out.append(
            {
                "move": f"{pick}:{state[pick]}->{b}",
                "transient_target_used_tib": round(used_b + f.size[pick], R),
                "transient_reserve_basis_tib": round(basis, R),
                "transient_required_tib": round(
                    used_b + f.size[pick] + f.reserve_factor * basis, R
                ),
                "capacity_tib": f.capacity[b],
                "ok": True,
            }
        )
        state[pick] = b
        pending.remove(pick)
    return out


def try_order(f: Fixture, target: Assignment) -> Dict[str, Any]:
    """order_moves, but record a deadlock instead of raising."""
    try:
        return {"orderable": True, "order": order_moves(f, target)}
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


def case_for(f: Fixture, beta: float) -> Dict[str, Any]:
    """One beta value: the big-M optimum, the lexicographic optimum, and order."""
    a, val = best_big_m(f, beta, f.big_m_p)
    final = per_storage(f, a)
    lex_a, lex_slack, lex_nr = best_lexicographic(f, beta)
    threshold = big_m_agreement_threshold(f, beta)

    case: Dict[str, Any] = {
        "beta_move_count": beta,
        # Unrounded, for the payback arithmetic; not written to the expected file.
        "_exact_E_after": E_of(f, a),
        "expected_objective": round(val, R),
        "expected_move_count": len(moves_of(f, a)),
        "expected_E_after": round(E_of(f, a), R),
        "expected_fragmentation": fragmentation(f, a),
        "expected_moves": moves_of(f, a),
        "expected_order": order_moves(f, a),
        "expected_final_loads": {s: final[s]["load"] for s in f.storages},
        "expected_final_reserve": final,
        "expected_spread_after": round(spread(f, final), R),
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
            "big_m_p_min_computed": round(computed_p_min(f, beta), 3),
        },
    }

    demo_p = f.objective.get("big_m_undersized_p_demo")
    if demo_p is not None:
        demo_a, demo_val = best_big_m(f, beta, float(demo_p))
        demo = {
            "p": float(demo_p),
            "expected_objective": round(demo_val, R),
            "expected_moves": moves_of(f, demo_a),
            "total_slack_tib": round(slack_of(f, demo_a), R),
            "matches_lexicographic": demo_a == lex_a,
        }
        demo.update(try_order(f, demo_a))
        case["big_m_undersized_p_demo"] = demo
    return case


def payback(f: Fixture, case: Dict[str, Any], e_after: float) -> Dict[str, Any]:
    """Section 7 payback arithmetic for one case.

    `e_after` is the EXACT objective of the chosen assignment. Taking it from
    `case["expected_E_after"]` instead would mix an exact E_before with a
    6-decimal-rounded E_after and shift the recorded benefit off the section 14.5
    value by a fraction of a load-second.
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
    delta_e = E_of(f, f.current) - e_after
    benefit = delta_e * float(f.migration["payback_horizon_seconds"])
    return {
        "beta_move_count": case["beta_move_count"],
        "per_move": per_move,
        "total_cost_load_seconds": round(total_cost, 2),
        "benefit_load_seconds": round(benefit, 2),
        "ratio": round(benefit / total_cost, 2),
        "accepted": benefit / total_cost >= float(f.migration["payback_ratio"]),
    }


def build(f: Fixture) -> Dict[str, Any]:
    """Derive the whole expected file for one fixture."""
    initial = per_storage(f, f.current)
    cases = [case_for(f, float(beta)) for beta in f.objective["beta_values"]]

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
            "initial": initial,
            "E_before": round(E_of(f, f.current), R),
            "spread_before": round(spread(f, initial), R),
        },
        "cases": [{k: v for k, v in c.items() if not k.startswith("_")} for c in cases],
    }

    two_move = [c for c in cases if c["expected_move_count"] == 2]
    if two_move:
        out["payback_two_move_plan"] = payback(f, two_move[0], two_move[0]["_exact_E_after"])
        arch_size, arch_delta_e = 4.0, 0.05
        omega = float(f.migration["source_load_weight"] + f.migration["target_load_weight"])
        # saferemove is off in this fixture, so there is no wipe term to add.
        arch_cost = arch_size * TIB / float(f.migration["bwlimit_bytes_per_sec"]) * omega
        arch_benefit = arch_delta_e * float(f.migration["payback_horizon_seconds"])
        out["payback_rejected_archive_disk"] = {
            "size_tib": arch_size,
            "delta_E": arch_delta_e,
            "cost_load_seconds": round(arch_cost, 2),
            "benefit_load_seconds": round(arch_benefit, 2),
            "ratio": round(arch_benefit / arch_cost, 3),
            "accepted": arch_benefit / arch_cost >= float(f.migration["payback_ratio"]),
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
