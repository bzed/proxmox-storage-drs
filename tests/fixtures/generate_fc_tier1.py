#!/usr/bin/env python3
"""Regenerate tests/fixtures/fc-tier1.expected.json from fc-tier1.yaml.

Exhaustively enumerates all |S|^|D| assignments per beta value, so the recorded
optimum is proven, not hand-worked. Also derives the execution order using the
section 8.2 rule and the section 8.1 transient checks for that order.

Usage:  python3 tests/fixtures/generate_fc_tier1.py [--check]
"""
import itertools
import json
import os
import sys

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required: pip install pyyaml")

HERE = os.path.dirname(os.path.abspath(__file__))
R = 6  # rounding for recorded values

fx = yaml.safe_load(open(os.path.join(HERE, "fc-tier1.yaml")))
G = fx["group"]
STOR = [s["id"] for s in G["storages"]]
CAP = {s["id"]: s["capacity_tib"] for s in G["storages"]}
CW = {s["id"]: s["capability_weight"] for s in G["storages"]}
EXT = {s["id"]: s.get("foreign_used_tib", 0.0) for s in G["storages"]}
F = G["reserve_factor"]
DISKS = fx["disks"]
KEYS = [d["key"] for d in DISKS]
SIZE = {d["key"]: d["size_tib"] for d in DISKS}
LOAD = {d["key"]: d["load"] for d in DISKS}
VM = {d["key"]: d["vmid"] for d in DISKS}
CUR = {d["key"]: d["current_storage"] for d in DISKS}
OBJ = fx["objective"]
MIG = fx["migration"]
P_RESERVE = OBJ.get("reserve_violation_penalty", 1000.0)

TOTAL_LOAD = sum(LOAD.values())
U_STAR = TOTAL_LOAD / sum(CW.values())


def per_storage(assign):
    out = {}
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


def E_of(assign):
    return sum(abs(sum(LOAD[k] for k in KEYS if assign[k] == s) / CW[s] - U_STAR) for s in STOR)


def objective(assign, beta):
    moved = [k for k in KEYS if assign[k] != CUR[k]]
    frag = sum(len({assign[k] for k in KEYS if VM[k] == v}) - 1 for v in sorted({VM[k] for k in KEYS}))
    slack = sum(max(0.0, st["used_tib"] + F * st["largest_tib"] - CAP[s])
                for s, st in per_storage(assign).items())
    return (OBJ["alpha_spread"] * E_of(assign)
            + beta * len(moved)
            + OBJ["gamma_move_bytes_per_tib"] * sum(SIZE[k] for k in moved)
            + OBJ["kappa_vm_affinity"] * frag
            + P_RESERVE * slack)


def best_for(beta):
    best, best_val = None, float("inf")
    for combo in itertools.product(STOR, repeat=len(KEYS)):
        a = dict(zip(KEYS, combo))
        v = objective(a, beta)
        if v < best_val - 1e-12:
            best, best_val = a, v
    return best, best_val


def duration(key):
    return SIZE[key] * (1 << 20) * (1 << 20) / MIG["bwlimit_bytes_per_sec"]


def cost(key):
    return duration(key) * (MIG["omega_src"] + MIG["omega_dst"])


def order_moves(target):
    """Section 8.2 greedy, with the two priority exceptions."""
    state = dict(CUR)
    pending = [k for k in KEYS if target[k] != CUR[k]]
    out = []
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

        def ratio(k):
            nxt = dict(state)
            nxt[k] = target[k]
            return (E_of(state) - E_of(nxt)) / cost(k)

        pick = max(feasible, key=ratio)
        b = target[pick]
        used_b = st[b]["used_tib"]
        zb = st[b]["largest_tib"]
        out.append({
            "move": f"{pick}:{state[pick]}->{b}",
            "transient_target_used_tib": round(used_b + SIZE[pick], R),
            "transient_reserve_basis_tib": round(max(zb, SIZE[pick]), R),
            "transient_required_tib": round(used_b + SIZE[pick] + F * max(zb, SIZE[pick]), R),
            "capacity_tib": CAP[b],
            "ok": True,
        })
        state[pick] = b
        pending.remove(pick)
    return out


initial = per_storage(CUR)
cases = []
case_assign = {}
for beta in OBJ["beta_values"]:
    a, val = best_for(beta)
    moved = sorted(k for k in KEYS if a[k] != CUR[k])
    frag = sum(len({a[k] for k in KEYS if VM[k] == v}) - 1 for v in sorted({VM[k] for k in KEYS}))
    final = per_storage(a)
    case_assign[beta] = a
    cases.append({
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
            (max(final[s]["load"] / CW[s] for s in STOR)
             - min(final[s]["load"] / CW[s] for s in STOR)) / U_STAR, R),
    })

two_idx = [i for i, c in enumerate(cases) if c["expected_move_count"] == 2][0]
two = cases[two_idx]
two_assign = case_assign[two["beta_move_count"]]
two_keys = [m.split(":")[0] + ":" + m.split(":")[1] for m in two["expected_moves"]]
per_move = [{"disk": k, "size_tib": SIZE[k],
             "duration_seconds": round(duration(k), 2),
             "cost_load_seconds": round(cost(k), 2)} for k in two_keys]
total_cost = sum(cost(k) for k in two_keys)
benefit = (E_of(CUR) - E_of(two_assign)) * MIG["payback_horizon_seconds"]

arch_size, arch_dE = 4.0, 0.05
arch_cost = arch_size * (1 << 40) / MIG["bwlimit_bytes_per_sec"] * (MIG["omega_src"] + MIG["omega_dst"])
arch_benefit = arch_dE * MIG["payback_horizon_seconds"]

out = {
    "schema_version": 1,
    "generated_by": "tests/fixtures/generate_fc_tier1.py (exhaustive enumeration)",
    "derived": {
        "total_load": round(TOTAL_LOAD, R),
        "u_star": round(U_STAR, R),
        "initial": initial,
        "E_before": round(E_of(CUR), R),
        "spread_before": round((max(initial[s]["load"] / CW[s] for s in STOR)
                                - min(initial[s]["load"] / CW[s] for s in STOR)) / U_STAR, R),
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

text = json.dumps(out, indent=2) + "\n"
path = os.path.join(HERE, "fc-tier1.expected.json")
if "--check" in sys.argv:
    cur = open(path).read()
    sys.exit(0 if cur == text else "fc-tier1.expected.json is stale; re-run without --check")
open(path, "w").write(text)
print(f"wrote {path}")
