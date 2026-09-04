#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regenerate tests/fixtures/fc-tier1.expected.json from fc-tier1.yaml.

Exhaustively enumerates all |S|^|D| assignments per beta value, so the recorded
optimum is proven, not hand-worked. Also derives the execution order using the
section 8.2 rule and the section 8.1 transient checks for that order.

Usage:  python3 tests/fixtures/generate_fc_tier1.py [--check]
"""

from __future__ import annotations

import itertools
import json
import os
import sys
from typing import Any, Dict, Iterator, List, Tuple

try:
    import yaml
except ImportError:  # pragma: no cover - the message is the whole point
    sys.exit("PyYAML required: pip install pyyaml")

Assignment = Dict[str, str]
StorageState = Dict[str, Any]

HERE = os.path.dirname(os.path.abspath(__file__))
R = 6  # rounding for recorded values

with open(os.path.join(HERE, "fc-tier1.yaml")) as _fh:
    fx: Dict[str, Any] = yaml.safe_load(_fh)
G: Dict[str, Any] = fx["group"]
STOR: List[str] = [s["id"] for s in G["storages"]]
CAP: Dict[str, float] = {s["id"]: s["capacity_tib"] for s in G["storages"]}
CW: Dict[str, float] = {s["id"]: s["capability_weight"] for s in G["storages"]}
EXT: Dict[str, float] = {s["id"]: s.get("foreign_used_tib", 0.0) for s in G["storages"]}
F: float = G["reserve_factor"]
DISKS: List[Dict[str, Any]] = fx["disks"]
KEYS: List[str] = [d["key"] for d in DISKS]
SIZE: Dict[str, float] = {d["key"]: d["size_tib"] for d in DISKS}
LOAD: Dict[str, float] = {d["key"]: d["load"] for d in DISKS}
VM: Dict[str, int] = {d["key"]: d["vmid"] for d in DISKS}
CUR: Assignment = {d["key"]: d["current_storage"] for d in DISKS}
OBJ: Dict[str, Any] = fx["objective"]
MIG: Dict[str, Any] = fx["migration"]
P_RESERVE: float = OBJ.get("reserve_violation_penalty", 1000.0)

TOTAL_LOAD = sum(LOAD.values())
U_STAR = TOTAL_LOAD / sum(CW.values())


def all_assignments() -> Iterator[Assignment]:
    """Every |S|^|D| placement of the movable disks."""
    for combo in itertools.product(STOR, repeat=len(KEYS)):
        yield dict(zip(KEYS, combo))


def per_storage(assign: Assignment) -> Dict[str, StorageState]:
    """Per-storage load, usage and reserve status for one assignment."""
    out: Dict[str, StorageState] = {}
    for s in STOR:
        ks = [k for k in KEYS if assign[k] == s]
        used = EXT[s] + sum(SIZE[k] for k in ks)
        largest = max((SIZE[k] for k in ks), default=0.0)
        out[s] = {
            "load": round(sum(LOAD[k] for k in ks), R),
            "used_tib": round(used, R),
            "largest_tib": round(largest, R),
            "required_tib": round(used + F * largest, R),
            "violates_reserve": used + F * largest > CAP[s] + 1e-9,
        }
    return out


def E_of(assign: Assignment) -> float:
    """Section 5.3 (C6) L1 spread, Sum_s |u_s - u*|."""
    return sum(abs(sum(LOAD[k] for k in KEYS if assign[k] == s) / CW[s] - U_STAR) for s in STOR)


def slack_of(assign: Assignment) -> float:
    """Total reserve shortfall Sum_s r_s, in TiB."""
    return sum(
        max(
            0.0,
            EXT[s]
            + sum(SIZE[k] for k in KEYS if assign[k] == s)
            + F * largest_on(assign, s)
            - CAP[s],
        )
        for s in STOR
    )


def largest_on(assign: Assignment, s: str) -> float:
    return max((SIZE[k] for k in KEYS if assign[k] == s), default=0.0)


def objective_nonreserve(assign: Assignment, beta: float) -> float:
    """The section 5.4 objective without the reserve term."""
    moved = [k for k in KEYS if assign[k] != CUR[k]]
    frag = sum(
        len({assign[k] for k in KEYS if VM[k] == v}) - 1 for v in sorted({VM[k] for k in KEYS})
    )
    return float(
        OBJ["alpha_spread"] * E_of(assign)
        + beta * len(moved)
        + OBJ["gamma_move_bytes_per_tib"] * sum(SIZE[k] for k in moved)
        + OBJ["kappa_vm_affinity"] * frag
    )


def objective(assign: Assignment, beta: float) -> float:
    """Single-stage big-M objective: section 5.4 plus P * Sum_s r_s."""
    return objective_nonreserve(assign, beta) + P_RESERVE * slack_of(assign)


def best_for(beta: float) -> Tuple[Assignment, float]:
    """Exhaustive minimum of the single-stage big-M objective."""
    best: Assignment = {}
    best_val = float("inf")
    for a in all_assignments():
        v = objective(a, beta)
        if v < best_val - 1e-12:
            best, best_val = a, v
    return best, best_val


def duration(key: str) -> float:
    return float(SIZE[key] * (1 << 20) * (1 << 20) / MIG["bwlimit_bytes_per_sec"])


def cost(key: str) -> float:
    return duration(key) * float(MIG["omega_src"] + MIG["omega_dst"])


def order_moves(target: Assignment) -> List[Dict[str, Any]]:
    """Section 8.2 greedy, with the two priority exceptions."""
    state = dict(CUR)
    pending = [k for k in KEYS if target[k] != CUR[k]]
    out: List[Dict[str, Any]] = []
    while pending:
        st = per_storage(state)
        violating = {s for s, v in st.items() if v["violates_reserve"]}
        prio = [k for k in pending if state[k] in violating] or pending
        feasible = []
        for k in prio:
            b = target[k]
            used_b = st[b]["used_tib"]
            zb = st[b]["largest_tib"]
            if used_b + SIZE[k] + F * max(zb, SIZE[k]) <= CAP[b] + 1e-9:
                feasible.append(k)
        if not feasible:
            raise SystemExit("deadlock while ordering; fixture needs a staging move")

        def ratio(k: str, _state: Assignment = state) -> float:
            nxt = dict(_state)
            nxt[k] = target[k]
            return (E_of(_state) - E_of(nxt)) / cost(k)

        pick = max(feasible, key=ratio)
        b = target[pick]
        used_b = st[b]["used_tib"]
        zb = st[b]["largest_tib"]
        out.append(
            {
                "move": f"{pick}:{state[pick]}->{b}",
                "transient_target_used_tib": round(used_b + SIZE[pick], R),
                "transient_reserve_basis_tib": round(max(zb, SIZE[pick]), R),
                "transient_required_tib": round(used_b + SIZE[pick] + F * max(zb, SIZE[pick]), R),
                "capacity_tib": CAP[b],
                "ok": True,
            }
        )
        state[pick] = b
        pending.remove(pick)
    return out


def build() -> Dict[str, Any]:
    """Derive the whole expected file."""
    initial = per_storage(CUR)
    cases: List[Dict[str, Any]] = []
    case_assign: Dict[float, Assignment] = {}
    for beta in OBJ["beta_values"]:
        a, val = best_for(beta)
        moved = sorted(k for k in KEYS if a[k] != CUR[k])
        frag = sum(
            len({a[k] for k in KEYS if VM[k] == v}) - 1 for v in sorted({VM[k] for k in KEYS})
        )
        final = per_storage(a)
        case_assign[beta] = a
        cases.append(
            {
                "beta_move_count": beta,
                "expected_objective": round(val, R),
                "expected_move_count": len(moved),
                "expected_E_after": round(E_of(a), R),
                "expected_fragmentation": frag,
                "expected_moves": [f"{k}:{CUR[k]}->{a[k]}" for k in moved],
                "expected_order": order_moves(a),
                "expected_final_loads": {s: final[s]["load"] for s in STOR},
                "expected_final_reserve": final,
                "expected_spread_after": round(
                    (
                        max(final[s]["load"] / CW[s] for s in STOR)
                        - min(final[s]["load"] / CW[s] for s in STOR)
                    )
                    / U_STAR,
                    R,
                ),
            }
        )

    two_idx = [i for i, c in enumerate(cases) if c["expected_move_count"] == 2][0]
    two = cases[two_idx]
    two_assign = case_assign[two["beta_move_count"]]
    two_keys = [m.split(":")[0] + ":" + m.split(":")[1] for m in two["expected_moves"]]
    per_move = [
        {
            "disk": k,
            "size_tib": SIZE[k],
            "duration_seconds": round(duration(k), 2),
            "cost_load_seconds": round(cost(k), 2),
        }
        for k in two_keys
    ]
    total_cost = sum(cost(k) for k in two_keys)
    benefit = (E_of(CUR) - E_of(two_assign)) * MIG["payback_horizon_seconds"]

    arch_size, arch_dE = 4.0, 0.05
    arch_cost = (
        arch_size * (1 << 40) / MIG["bwlimit_bytes_per_sec"] * (MIG["omega_src"] + MIG["omega_dst"])
    )
    arch_benefit = arch_dE * MIG["payback_horizon_seconds"]

    return {
        "schema_version": 1,
        "generated_by": "tests/fixtures/generate_fc_tier1.py (exhaustive enumeration)",
        "derived": {
            "total_load": round(TOTAL_LOAD, R),
            "u_star": round(U_STAR, R),
            "initial": initial,
            "E_before": round(E_of(CUR), R),
            "spread_before": round(
                (
                    max(initial[s]["load"] / CW[s] for s in STOR)
                    - min(initial[s]["load"] / CW[s] for s in STOR)
                )
                / U_STAR,
                R,
            ),
        },
        "cases": cases,
        "payback_two_move_plan": {
            "per_move": per_move,
            "total_cost_load_seconds": round(total_cost, 2),
            "benefit_load_seconds": round(benefit, 2),
            "ratio": round(benefit / total_cost, 2),
            "accepted": benefit / total_cost >= MIG["payback_ratio"],
        },
        "payback_rejected_archive_disk": {
            "size_tib": arch_size,
            "delta_E": arch_dE,
            "cost_load_seconds": round(arch_cost, 2),
            "benefit_load_seconds": round(arch_benefit, 2),
            "ratio": round(arch_benefit / arch_cost, 3),
            "accepted": arch_benefit / arch_cost >= MIG["payback_ratio"],
        },
    }


def main(argv: List[str]) -> int:
    text = json.dumps(build(), indent=2) + "\n"
    path = os.path.join(HERE, "fc-tier1.expected.json")
    if "--check" in argv:
        with open(path) as fh:
            if fh.read() != text:
                print("fc-tier1.expected.json is stale; re-run without --check", file=sys.stderr)
                return 1
        return 0
    with open(path, "w") as fh:
        fh.write(text)
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
