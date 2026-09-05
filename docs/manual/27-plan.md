# Reading `plan`

`plan` computes what `pve-storage-drs` would do and prints it. It never
changes anything, in any `execution.mode` — that is `apply`'s job (not yet
implemented; see `30-safety-and-status.md`), and it needs a separate,
explicit invocation to run at all.

For each group, `plan`:

1. Fetches the same load (`ℓ_d`/`L_s`/`u_s`) `show-load` does, and
   evaluates the same section 6 gate.
2. If the gate says `NO ACTION`, stops there for that group — no solver
   runs, nothing more to show.
3. If it says `ACT`, runs the heuristic solver (`IMPLEMENTATION_PLAN.md`
   section 5.4/5.5) to compute a target assignment, then orders its moves
   under the section 8 transient reserve invariant.

This example uses the same section 14 worked example `show-load`'s manual
page does, so the numbers are traceable to that section:

```
$ pve-storage-drs -c /etc/pve/drs.yaml plan
Group fc-tier1 → ACT: reserve violated on san-a; bypassing the drift and imbalance gates (section 13: safety is not subject to hysteresis)
  1. 102:scsi0      san-a → san-c     1.50 TiB      ~2.2h   Δimbalance -4.53
  2. 101:scsi1      san-a → san-b     1.00 TiB      ~1.5h   Δimbalance -2.00
  3. 105:scsi0      san-c → san-b   512.00 GiB     ~43.7m   Δimbalance -0.40
  after: san-a=3.00  san-b=1.90  san-c=2.50
  spread: 255.4% → 44.6%
  Note: payback (cost/benefit) validation is not yet implemented (IMPLEMENTATION_PLAN.md phase 5) -- these moves have not been checked against migration.payback_ratio, and the duration above is mirror time only (no saferemove wipe accounted for).
```

A group the gate does not act on prints one line and stops:

```
Group fc-tier2 → NO ACTION: imbalance 0.0% is below gates.imbalance_threshold (20.0%)
```

## Reading a move line

`1. 102:scsi0  san-a → san-c  1.50 TiB  ~2.2h  Δimbalance -4.53` — the disk,
its current and target storage, its size, an estimated mirror-only
duration (`size / migration.bwlimit_bytes_per_sec` — **not** including a
`saferemove` wipe, since that needs `payback.py`'s accounting, not yet
written), and this move's own effect on the group's imbalance metric at
the moment it was scheduled (negative means imbalance went down, which is
the usual case; a move scheduled mainly to resolve a reserve violation or
consolidate a VM can show a positive value and still be correct — see the
next section).

`resolves_reserve_violation` (visible in `--json`, and implied by the
`ACT: reserve violated on ...` header in human output) marks a move
scheduled first *regardless* of its ratio, because the storage it leaves
is currently breaching (C4)/(C5) — safety is not subject to hysteresis
(section 13), so this always wins over a purely balance-driven move.

**A `⚠` line means a deadlock, not a hidden failure.** If the target
assignment includes a move this run cannot find any transient-feasible
order for, `plan` says so explicitly (`IMPLEMENTATION_PLAN.md` section
8.3's "report, never force" path — staging and plan-splitting are not yet
implemented, so this is where a genuine cycle or an unavoidable capacity
shortfall currently surfaces) rather than silently omitting the move or,
worse, telling you a plan is clean when part of it is not achievable.

## What `plan` does not yet do

- **No cost/benefit check.** Every proposed move is shown as computed by
  the balance objective alone; `IMPLEMENTATION_PLAN.md` section 7's
  payback rule (a move must save more traffic than it costs within
  `migration.payback_horizon`) is phase 5, not yet written. The `Note:`
  line under a plan with moves says this every time, deliberately, rather
  than once in this manual page alone.
- **No `state.json`.** Section 11.2's drift history does not exist yet, so
  the gate `plan` evaluates always treats this as the first run — see
  `docs/internals/80-gates.md` for exactly what that does and does not
  change about the verdict.
- **No cooldowns, no staging, no concurrent scheduling.** All documented
  as deliberate, not forgotten, in `docs/internals/90-heuristic.md` and
  `docs/internals/95-schedule.md`.

`--json` emits `groups[]`, each with `gate` (identical shape to
`show-load`'s), `moves[]` (`disk_key`, `vmid`, `device`, `from_storage`,
`to_storage`, `size_bytes`, `imbalance_reduction`,
`resolves_reserve_violation`, `estimated_mirror_duration_seconds`),
`deadlocked` (a list of disk keys) and `deadlock_message` (`null` if none),
`before_spread`/`after_spread` (the section 6 spread fraction, before the
plan and after every scheduled move), `load_error` (`null` unless
Prometheus failed for this group), and `payback_validated: false` always,
for now — a machine-readable version of the same caveat.
