# Proxmox Storage DRS — Implementation Plan

A specification for a VMware Storage DRS replacement targeting **Proxmox VE 9.2**.
It is written to be implementable without further research: every external fact it relies on is
stated inline, and section 14 is a worked numeric example that doubles as a test fixture.

---

## 1. Scope

### Goal

Given configurable **groups** of shared storages, continuously equalize **disk I/O load** across the
storages within each group by live-migrating individual VM disks, subject to:

- a disk may only move between storages in **its own group**;
- every storage must always retain free space for snapshots — by default **2× its largest disk** —
  and this must hold *during* migrations, not merely before and after;
- the number of migrations must be **minimal**;
- a VM's disks should stay **together** on one storage unless space or I/O forces otherwise;
- a migration's own I/O cost must not exceed the imbalance it removes.

### Non-goals

Compute/CPU/memory DRS, VM-to-node placement, HA, backup scheduling, storage provisioning,
thin-pool overcommit management, and any modification of guest configuration beyond disk location.

### Operating assumptions

- PVE 9.2, shared LVM (typically over FC) or any shared storage supporting `move_disk`.
- Only **running** VMs are considered by default; a stopped VM generates no I/O to balance, and its
  disks are moved only if a capacity constraint requires it.
- Disks are thick-provisioned by default, so migration cost is proportional to *provisioned* size.

---

## 2. Architecture

The engine is **stateless with respect to metrics** — all history lives in Prometheus. It keeps one
small local state file purely for hysteresis.

```
   ┌──────────────────────┐        ┌────────────────────────────┐
   │  Prometheus / VM     │        │   Proxmox VE API (9.2)     │
   │  per-disk blockstat  │        │   topology, sizes, actions │
   └──────────┬───────────┘        └─────────────┬──────────────┘
              │ PromQL, window W                 │ HTTPS + ticket
              ▼                                  ▼
        ┌───────────────────────────────────────────────────┐
        │                  DRS Engine                       │
        │  1 collect  → per-disk load vector ℓ              │
        │  2 join     → disk → storage → group topology     │
        │  3 gate     → drift / imbalance / cooldown        │
        │  4 solve    → target assignment x                 │
        │  5 cost     → payback acceptance test             │
        │  6 order    → transient-feasible migration list   │
        │  7 execute  → dry-run | confirm | auto            │
        └───────────────────────┬───────────────────────────┘
                                ▼
                         state.json (hysteresis only)
```

Two data sources are genuinely required, and neither substitutes for the other:

- **Prometheus** knows the load of `vmid=101, device=scsi0` but has **no idea which storage that disk
  lives on**.
- **The PVE API** knows the topology, sizes and capacities, and is the only way to *act*.

The join between them is the disk identity `(vmid, device)`, which both sides expose.

### Module layout

| Module | Responsibility |
|---|---|
| `config.py` | Load/validate YAML, defaults, unit parsing (`24h`, `200MiB`) |
| `metrics.py` | Prometheus client, PromQL construction, `verify-metrics` |
| `pve.py` | API client: auth, topology, storage status, `move_disk`, task polling |
| `topology.py` | Build the disk/storage/group model, eligibility rules |
| `loadmodel.py` | Reduce raw series to the scalar load vector `ℓ` |
| `forecast.py` | Pluggable forecaster (quantile, seasonal-naive, Holt-Winters) |
| `optimize.py` | MILP formulation (CP-SAT / CBC) |
| `heuristic.py` | Dependency-free greedy + local search fallback |
| `payback.py` | Migration cost model and acceptance test |
| `schedule.py` | Ordering under the transient reserve invariant |
| `execute.py` | Three execution modes, task supervision |
| `cli.py` | `plan`, `apply`, `verify-metrics`, `show-load`, `explain` |

---

## 3. Data acquisition

### 3.1 Where the per-disk data comes from

This is the single most important implementation fact, so it is stated precisely.

`pvestatd` calls `PVE::QemuServer::vmstatus(undef, 1)` — note the `full=1` flag. With `full` set,
`vmstatus` issues QMP `query-blockstats` and stores the result as:

```perl
$res->{$vmid}->{blockstat}->{$drive_id} = $blockstat->{stats};
```

where `$drive_id` is the QMP device name with the `drive-` prefix stripped — i.e. **`scsi0`,
`virtio0`, `ide2`**, matching the VM config keys exactly. The whole QMP stats hash is kept without
filtering, which includes:

```
rd_bytes  wr_bytes  rd_operations  wr_operations
rd_total_time_ns  wr_total_time_ns
flush_operations  flush_total_time_ns
rd_merged  wr_merged  failed_rd_operations  failed_wr_operations
invalid_rd_operations  invalid_wr_operations  account_invalid  account_failed  idle_time_ns
```

`PVE/Status/InfluxDB.pm` then flattens the nested hash so that the **first** nesting level becomes the
InfluxDB *measurement* (`blockstat`), the **second** becomes an *instance tag* (`instance=scsi0`), and
the leaves become *fields*. Combined with the base tags from `update_qemu_status`
(`object=qemu,vmid=…,nodename=…,host=<vm name>`), a series arrives in Prometheus roughly as:

```
blockstat_rd_operations{vmid="101", instance="scsi0", nodename="pve01", host="db-01"}
```

Everything needed for true per-disk IOPS, throughput **and latency** is therefore already present in
an existing PVE → InfluxDB → Telegraf → Prometheus pipeline. **No new exporter or collector is
required.**

### 3.2 Two paths deliberately not taken

**Do not use RRD.** `GET /nodes/{node}/qemu/{vmid}/rrddata` exposes only VM-aggregate
`diskread`/`diskwrite` in bytes/s — no per-disk breakdown and no operation counts. `GET
/nodes/{node}/storage/{storage}/rrddata` exposes only `used` and `total`, with no I/O metrics at all.
Prometheus supersedes RRD entirely here.

**Do not switch to the OpenTelemetry metric server** (new in PVE 9.1), despite it being the more
modern-looking option. Its `_convert_node_metrics_recursive` handles a nested hash by appending the
key to the metric **name**:

```perl
if (ref($value) eq 'HASH') {
    push @metrics, $class->_convert_node_metrics_recursive(
        $value, $ctime, "${metric_prefix}_${key}", $attributes,   # <-- name, not attribute
    );
}
```

so `blockstat.scsi0.rd_operations` becomes the metric **`proxmox_vm_blockstat_scsi0_rd_operations_total`**.
The device is baked into the metric name rather than carried as a label, which makes PromQL
aggregation across devices impossible without `label_replace` gymnastics and produces unbounded
metric-name cardinality. The InfluxDB path puts the device in a **label** and is strictly superior for
this use case. (The plugin also only supports OTLP/JSON encoding, not protobuf.)

### 3.3 Metric name mapping and verification

Telegraf naming is deployment-specific, so **every metric and label name is configuration**, not a
constant. Implement `drs verify-metrics` as a first-class command that must be run before anything
else. It shall:

1. query `/api/v1/label/__name__/values` and confirm each configured metric name exists;
2. run one instant query per metric and print a sample series with all labels;
3. confirm the configured `vmid`, `device` and `node` labels are present and non-empty;
4. warn loudly if the device label is literally `instance` — **PVE's `instance` tag collides with
   Prometheus's own scrape-target `instance` label**, and many Telegraf configurations rename or
   overwrite it. The implementer must confirm the real label name here before proceeding;
5. report per-disk sample coverage over the configured window, so gaps are visible up front.

### 3.4 PromQL

Let `R` be `metrics.rate_window` (default `5m`) and `W` be `window.lookback` (default `24h`).
Three raw quantities per disk, all keyed by `(vmid, device)`:

```promql
# average in-flight I/O (dimensionless) — the primary load signal
sum by (vmid, device) (
    rate(blockstat_rd_total_time_ns[5m]) + rate(blockstat_wr_total_time_ns[5m])
) / 1e9

# operations per second
sum by (vmid, device) (
    rate(blockstat_rd_operations[5m]) + rate(blockstat_wr_operations[5m])
)

# bytes per second
sum by (vmid, device) (
    rate(blockstat_rd_bytes[5m]) + rate(blockstat_wr_bytes[5m])
)
```

Reduce each to one scalar over the decision window with a robust quantile rather than a mean, so a
single spike neither triggers nor suppresses a migration:

```promql
quantile_over_time(0.95, ( <expression above> )[24h:5m])
```

Notes for the implementer:

- `rate()` already handles the counter resets that occur when a VM reboots or migrates between nodes.
- The `sum by` collapses the `nodename`/`host` labels, which is what we want: a VM that live-migrated
  between nodes during the window must remain **one** disk, not two.
- Use the **range** (`query_range`) form as well when the forecaster needs a series rather than a
  scalar; the same expression works with a `step`.
- Reject a disk whose sample coverage over `W` is below `window.min_coverage` and fall back to its
  last known load from `state.json`, flagging it in the plan output. Never treat missing data as zero
  load — that would silently invite migrations *onto* a busy storage.

### 3.5 PVE API

Authentication (username/password as specified):

```
POST /api2/json/access/ticket        {username, password}
  → data.ticket                      → Cookie: PVEAuthCookie=<ticket>
  → data.CSRFPreventionToken         → header CSRFPreventionToken on every write
```

Tickets are valid ~2h; refresh on the interval in `proxmox.ticket_refresh_seconds`. API tokens
(`Authorization: PVEAPIToken=USER@REALM!TOKENID=SECRET`) need no CSRF header and are preferred for
unattended `auto` mode.

Read path:

| Endpoint | Used for |
|---|---|
| `GET /cluster/resources?type=vm` | VM inventory: vmid, node, status, name, tags |
| `GET /cluster/resources?type=storage` | Storage inventory, `shared` flag, used/total per node |
| `GET /storage` | Storage definitions: type, `content`, `shared`, `nodes` restriction |
| `GET /nodes/{node}/qemu/{vmid}/config` | **disk → storage mapping and size** |
| `GET /nodes/{node}/storage/{storage}/status` | authoritative `total`/`used`/`avail` |
| `GET /nodes/{node}/storage/{storage}/content` | per-volume real allocated sizes, owner vmid |
| `GET /nodes/{node}/qemu/{vmid}/snapshot` | detect existing snapshot/volume chains |

Parsing a disk from the VM config: a key matching `^(scsi|virtio|sata|ide|efidisk|tpmstate)\d+$`
whose value looks like `san-a:vm-101-disk-0,size=512G,iothread=1`. The storage id is the part before
the first `:`; the size comes from the `size=` parameter, cross-checked against
`/storage/{storage}/content`, which is authoritative for what is actually allocated. Skip entries
containing `media=cdrom`, and skip `efidisk`/`tpmstate` volumes — they are tiny and moving them is
pointless and, for TPM state, unsupported alongside volume-chain snapshots.

Write path:

```
POST /api2/json/nodes/{node}/qemu/{vmid}/move_disk
     disk=scsi0  storage=san-c  delete=1  bwlimit=<KiB/s>  [format=qcow2]
  → UPID string
GET  /api2/json/nodes/{node}/tasks/{upid}/status   → status=running|stopped, exitstatus=OK|…
```

`bwlimit` is in **KiB/s**. `delete=1` removes the source volume after a successful mirror; without it
the old volume is left behind as an unreferenced volume and the reserve math will silently drift.

---

## 4. The load model

For each disk `d`, reduce the three raw quantities to a single scalar. The terms have wildly
different magnitudes (in-flight I/O ≈ 0–10, ops/s ≈ 0–50000, bytes/s ≈ 0–10⁹), so each is normalized
by the group total before weighting; otherwise the configured weights would be meaningless.

```
        iotime_d              ops_d               bytes_d
î_d = ───────────── ,  ô_d = ───────────  ,  b̂_d = ─────────────
       Σ_{e∈g} iotime_e      Σ_{e∈g} ops_e        Σ_{e∈g} bytes_e

ℓ_d  =  w_t·î_d  +  w_o·ô_d  +  w_b·b̂_d
```

with `w_t = 1, w_o = w_b = 0` by default — **I/O time is the primary quantity**.

Why I/O time is the right default. `rate(rd_total_time_ns + wr_total_time_ns) / 1e9` is, by Little's
law, the **average number of I/O requests in flight** for that disk. It is dimensionless, it is
additive across disks on the same storage, and it is directly comparable between storages of
different size and speed. Crucially it *self-weights*: a 1 MiB write that takes 8 ms contributes
eight times what a 4 KiB read taking 1 ms does, without anyone having to guess a read/write weight.
Pure IOPS treats those two operations as equal and so systematically under-counts large sequential
load; pure throughput does the reverse and under-counts small random load. `ops` and `bytes` remain
available as additional weighted terms for operators who want to express a policy the array's own
timings do not capture.

One caveat to document: I/O time is a *feedback* signal — it rises when the array is slow, including
when the slowness is caused by some other tenant. Combined with the drift gate and cooldowns this is
stable in practice, but an operator seeing oscillation should shift weight toward `ops`/`bytes`,
which measure only what the guest requested.

Storage load and utilization, where `c_s` is the configured capability weight:

```
L_s = Σ_d ℓ_d · x_{d,s}          u_s = L_s / c_s
```

`u_s` — not `L_s` — is what gets equalized, so a storage with half the spindles can be given
`capability_weight: 0.5` and will correctly be assigned half the load.

---

## 5. The optimization problem

Solved **independently per group** — groups share no variables and no constraints, so a cluster with
four groups is four small problems, not one large one.

### 5.1 Sets and data

| Symbol | Meaning |
|---|---|
| `g` | a storage group |
| `S` | storages in the group |
| `D` | movable disks currently in the group |
| `V` | VMs owning at least one disk in `D` |
| `v(d)` | the VM owning disk `d` |
| `σ₀(d)` | the storage disk `d` is on **now** |
| `z_d` | provisioned size of disk `d` (bytes) |
| `ℓ_d` | load of disk `d` (section 4) |
| `C_s` | total capacity of storage `s` |
| `Uˢᵉˣᵗ` | bytes on `s` consumed by volumes DRS does not manage |
| `c_s` | capability weight of `s` |
| `f_s` | snapshot reserve factor for `s` (default 2.0) |

### 5.2 Variables

| Variable | Domain | Meaning |
|---|---|---|
| `x_{d,s}` | `{0,1}` | disk `d` is placed on storage `s` |
| `y_{v,s}` | `{0,1}` | VM `v` has at least one disk on `s` |
| `Z_s` | `≥ 0` | size of the largest disk on `s` |
| `e_s` | `≥ 0` | absolute deviation of `u_s` from target (L1 objective) |
| `t` | `≥ 0` | maximum utilization (min–max objective) |
| `r_s` | `≥ 0` | reserve violation slack |

### 5.3 Constraints

**(C1) Assignment.** Every disk lands on exactly one storage in its group:

```
Σ_{s∈S} x_{d,s} = 1                                    ∀ d ∈ D
```

**(C2) Eligibility.** Fix `x_{d,s} = 0` wherever placement is impossible or forbidden. This is where
all the domain rules live, and doing it as variable fixing rather than as constraints keeps the model
small:

- `s` does not have `images` in its `content` list;
- `s` is not shared, or is restricted to nodes that cannot see the VM;
- `s` cannot hold the disk's format, or the disk is `efidisk`/`tpmstate`;
- `d` or `v(d)` is excluded by config (`exclude.vmids`, `exclude.disks`, tags, `no-drs`);
- `d` has an existing snapshot chain and `exclude.skip_vms_with_snapshots` is set — in which case
  additionally pin `x_{d,σ₀(d)} = 1`;
- `d` is within its per-disk cooldown — also pin to current.

**(C3) VM affinity linking.** Couple `y` to `x` in both directions so the objective term is exact:

```
x_{d,s}  ≤  y_{v(d),s}                                 ∀ d ∈ D, s ∈ S
y_{v,s}  ≤  Σ_{d : v(d)=v} x_{d,s}                     ∀ v ∈ V, s ∈ S
```

**(C4) Largest-disk linearization.** `Z_s = max{ z_d : x_{d,s}=1 }` is not linear, but because the
reserve constraint pushes `Z_s` *down* while this pushes it *up*, a one-sided bound is exact at the
optimum:

```
Z_s  ≥  z_d · x_{d,s}                                  ∀ d ∈ D, s ∈ S
```

**(C5) Capacity and snapshot reserve.** The core safety constraint:

```
Σ_d z_d·x_{d,s}  +  Uˢᵉˣᵗ  +  f_s · Z_s   ≤   C_s  +  r_s          ∀ s ∈ S
```

The `f_s · Z_s` term is the "always keep 2× the largest disk free" rule, and (C4) is what makes it
expressible in a linear model at all.

`r_s` is a **soft slack penalized heavily** in the objective rather than a hard `≤ C_s`. This is
essential: a storage can already be violating the reserve when the engine first runs (see the worked
example in section 14), and a hard constraint would make the model infeasible and the tool useless
exactly when it is most needed. With slack, the solver instead produces the plan that *repairs* the
violation. Report any residual `r_s > 0` prominently as an unfixable shortfall.

**(C6) Spread.** With `u* = (Σ_d ℓ_d) / (Σ_s c_s)` — a **constant**, since total group load is
invariant under reassignment — the L1 form is fully linear:

```
u_s = (Σ_d ℓ_d·x_{d,s}) / c_s
u_s − u*  ≤  e_s        and        u* − u_s  ≤  e_s     ∀ s ∈ S
```

The min–max alternative is `t ≥ u_s ∀s`. L1 is the default: min–max only sees the single hottest
storage and is indifferent to everything below it, which tends to produce plans that fix the worst
storage and ignore a second nearly-as-bad one.

### 5.4 Objective

```
min   α · Σ_{s∈S} e_s                            (imbalance)
    + β · Σ_{d∈D} (1 − x_{d,σ₀(d)})              (number of migrations)
    + γ · Σ_{d∈D} z_d · (1 − x_{d,σ₀(d)})        (bytes migrated)
    + κ · Σ_{v∈V} ( Σ_{s∈S} y_{v,s} − 1 )        (VM disk fragmentation)
    + P · Σ_{s∈S} r_s                            (reserve violation)
```

`(1 − x_{d,σ₀(d)})` is exactly 1 when disk `d` moves and 0 when it stays, so `β` directly implements
"minimize the number of migrations" and `γ` biases against moving *large* disks specifically. `κ`
counts the number of **extra** storages a VM is spread across, so it is 0 for a VM whose disks are all
together and grows by 1 per additional storage — a soft preference that free space (C5) or a strong
imbalance can legitimately override, as required.

Scaling matters: normalize `z_d` to TiB and `ℓ_d` to fractions of group total (section 4) before
applying the weights, so the defaults in the example config are meaningful.

### 5.5 Solver backends

**CP-SAT (preferred).** All coefficients must be integral, so scale `ℓ` by 10⁶ and `z` to MiB and
round. Warm-start from the current assignment via `AddHint(x[d, σ₀(d)], 1)`, which typically finds the
incumbent immediately and spends the rest of the time limit proving the gap.

**CBC via PuLP.** Direct transcription; continuous `e_s`, `Z_s`, `r_s` are fine.

**Heuristic fallback (no dependency, and the path for very large groups).**

1. **Seed** with the current assignment (not from scratch — we are minimizing *change*).
2. **Repair**: while any `s` violates (C5), move the disk from `s` that most reduces the violation per
   byte moved, to the feasible storage with the lowest `u_s`.
3. **Descend**: repeatedly evaluate every single-disk move and every pairwise swap; apply the one
   that most improves the full objective (including `β`, `γ`, `κ`); stop when no move improves it or
   `heuristic_iterations` is reached.
4. **Polish**: attempt to reunite fragmented VMs where doing so does not worsen imbalance beyond
   `imbalance_threshold`.

Swaps matter and must not be omitted: when both storages are near their capacity limit, no single
move is feasible, and only an exchange of two disks can improve the balance.

The heuristic must use the **same** feasibility and objective functions as the MILP path so the two
backends are directly comparable; make them shared pure functions.

---

## 6. Gating — deciding whether to act at all

Applied in order, before the solver runs. Any gate that fails ends the run with "no action".

**Drift gate** — the "minimum % of changed average traffic" requirement. Compare the current load
vector against the one recorded at the last *executed* balance:

```
‖ℓ_now − ℓ_last‖₁ / ‖ℓ_last‖₁   ≥   gates.drift_threshold      (default 0.10)
```

Using the L1 norm over the whole vector, rather than a per-disk test, means many small correlated
changes can legitimately trigger a re-plan while one noisy disk cannot. Disks that appeared or
disappeared since the last balance count their full load as drift.

**Imbalance gate** — the "% of IOPS difference over all storages in the group" requirement:

```
(max_s u_s − min_s u_s) / u*   ≥   gates.imbalance_threshold   (default 0.20)
```

Evaluated per group; a group that passes is planned, others are skipped.

**Cooldowns** — a disk moved within `cooldown_per_disk` (default 24h) is pinned in place; a storage
involved in a migration within `cooldown_per_storage` accepts no new incoming moves.

**Reserve override** — a storage in violation of (C5) bypasses the drift and imbalance gates
entirely. Safety is not subject to hysteresis.

---

## 7. Migration cost and the payback rule

This section implements the requirement that *migrating a very large disk may generate more traffic
than it saves*. It is expressed as a **hard acceptance test on the finished plan**, not merely as a
soft `γ` penalty, because a penalty can always be outweighed by a large enough imbalance term.

### 7.1 Cost

A `move_disk` on a running VM performs a QEMU `drive-mirror`: it reads the whole source volume and
writes it to the target, then switches over. For thick provisioning the full provisioned size is
transferred.

```
duration_d  =  z_d / min(bwlimit, headroom_src, headroom_dst)

cost_d      =  duration_d · (ω_src + ω_dst)
```

`ω_src` and `ω_dst` (default 1.0 each) are the added in-flight I/O on source and target — a mirror is
one sequential reader plus one sequential writer, so 1.0 each is the natural unit and is directly
comparable to `ℓ`, which is measured in the same units. `cost_d` is therefore in **load-seconds**.

### 7.2 Benefit

The plan reduces the imbalance objective from `E_before = Σ_s e_s` to `E_after`. That reduction
persists until the workload changes, which we bound by the payback horizon `H`:

```
benefit  =  (E_before − E_after) · H
```

also in load-seconds. Both sides of the comparison are thus in the same unit, which is the whole
point of using I/O time as the load metric.

### 7.3 Acceptance

```
accept plan   ⟺   benefit  ≥  migration.payback_ratio · Σ_d cost_d
```

with `H = 7d` and `λ = 10` by default. Additional **hard** rules, applied per move, that reject
individual migrations regardless of the aggregate test:

- `duration_d > migration.max_single_move_duration` (default 6h) → reject the move;
- the move would push `u_src` or `u_dst` above `migration.saturation_ceiling` *during* the mirror →
  defer the move to a later run rather than reject the plan;
- the move violates the transient reserve invariant of section 8 → reject.

If the plan fails the aggregate test, re-solve with `β` and `γ` doubled and retry, up to three times.
This naturally converges on the smaller subset of high-value moves rather than abandoning the run —
usually the one or two disks with the highest `ℓ_d / z_d` ratio, which is exactly the right thing to
move.

`ℓ_d / z_d` — load per byte — is worth surfacing in `drs explain` output. It is the single best
indicator of a good migration candidate: high I/O concentrated in a small disk.

---

## 8. Migration ordering

The solver produces a *target assignment*. It says nothing about the order of moves, and order
matters: the requirement that the snapshot reserve holds **even during storage migrations** is a
constraint on every intermediate state, not just the endpoints.

### 8.1 The transient invariant

During a `move_disk` of disk `d` from `a` to `b`, the volume exists on **both** storages — the mirror
target is fully allocated before the switchover, and the source is only removed afterwards by
`delete=1`. So while the move is in flight, `b` must satisfy:

```
used_b + z_d + f_b · max(Z_b, z_d)   ≤   C_b
```

Note the `max(Z_b, z_d)`: if the incoming disk is the new largest on `b`, the required reserve grows
at the same moment the disk arrives. This is the case most likely to be missed, and the one most
likely to fill a SAN LUN.

The source `a` gets no relief until the move completes, so a plan that depends on freeing space on `a`
to make room on `a` is simply infeasible and must be ordered around.

### 8.2 Scheduling algorithm

```
pending ← { moves implied by the target assignment }
state   ← current allocation
order   ← []

while pending:
    feasible ← { m ∈ pending : transient_invariant_ok(state, m)
                               and concurrency_ok(state, m)
                               and not in cooldown }
    if feasible is empty:
        if a staging move exists:  order.append(staging_move); continue
        else: report deadlock with the blocking storages; break

    m ← argmax over feasible of  (imbalance reduction) / cost_m
    order.append(m)
    state ← apply(state, m)          # source freed, target charged
```

Ordering by **imbalance reduction per unit cost** means the plan front-loads its value: if the
operator aborts halfway, or a maintenance window closes, the moves that mattered most have already
run. Two exceptions take priority and are scheduled first regardless of ratio:

1. moves that resolve a storage currently violating (C5);
2. moves that *free* space on a storage which some later move needs.

### 8.3 Deadlock and staging

Three storages each near capacity can produce a cycle in which no move is individually feasible
though the target assignment is perfectly valid — the classic pebble-motion deadlock. Resolution, in
order of preference:

1. **Staging move** — find any storage in the group with enough slack to temporarily accept the
   smallest disk in the cycle, move it there, complete the cycle, then move it to its target. Costs
   one extra migration; permit it only if the *whole* plan still passes the payback test with that
   extra cost included.
2. **Split the plan** — execute the feasible subset now, re-plan on the next run. Often the workload
   has changed anyway.
3. **Report** — emit the blocking set and stop. Never force a move that breaches the reserve.

Guard staging moves against loops: a disk may be staged at most once per plan, and a staged disk is
exempt from the per-disk cooldown for the duration of that plan only.

---

## 9. Execution

### 9.1 Modes

| Mode | Behaviour |
|---|---|
| `dry-run` *(default)* | Print the plan, the before/after balance, the payback arithmetic, and the exact API calls that *would* be issued. Change nothing. |
| `confirm` | Execute the plan one move at a time, prompting before each. Re-validate the transient invariant immediately before each prompt, since the cluster may have changed. Offer `[y]es / [n]o skip / [a]ll remaining / [q]uit`. |
| `auto` | Execute unattended, subject to concurrency caps and `execution.time_windows`. |

`auto` must additionally: refuse to start a move that cannot finish inside the remaining time window;
stop cleanly at window close rather than aborting an in-flight move; and honour
`max_migrations_per_run`.

### 9.2 Performing one move

```
POST /nodes/{node}/qemu/{vmid}/move_disk
     disk={device} storage={target} delete=1 bwlimit={KiB/s}
  → UPID
poll GET /nodes/{node}/tasks/{upid}/status every execution.poll_interval_seconds
  until status == "stopped"; success ⟺ exitstatus == "OK"
```

Before **every** move, re-read the live state rather than trusting the plan:

1. re-fetch `/nodes/{node}/qemu/{vmid}/config` and confirm the disk is still on the expected source
   — the VM may have been touched by an operator, or live-migrated to another node, changing `{node}`;
2. re-fetch `/nodes/{node}/storage/{target}/status` and re-check the transient invariant against
   *actual* current free space;
3. confirm the VM is still running and untagged for exclusion.

Any mismatch aborts that move and triggers a re-plan rather than proceeding on stale assumptions.

### 9.3 Failure handling

`move_disk` is atomic from the caller's perspective: on failure QEMU cancels the mirror and the source
volume remains authoritative, so there is nothing to roll back. The realistic hazards are:

- **Orphaned target volume.** A failed or cancelled mirror can leave `vm-101-disk-0` on the target.
  After any failure, list `/nodes/{node}/storage/{target}/content` and warn about volumes owned by the
  VM that are not referenced in its config. Do **not** delete them automatically — report them. They
  count against the reserve until removed, so surfacing them matters.
- **Partial plan.** With `abort_on_failure: true` (default), stop and report; the cluster is in a
  valid intermediate state and the next run will re-plan from reality.
- **Task supervision loss.** If the engine dies mid-move, the PVE task continues. On startup, check
  for running `move_disk` UPIDs owned by the DRS user before planning anything.

### 9.4 Output

Every mode emits the same machine-readable plan (JSON) plus a human summary. The example below
is the section 14 fixture at `beta_move_count: 0.5` (the two-move variant):

```
Group fc-tier1 — imbalance 255% (threshold 20%) → ACT
  san-a  u=6.50  ██████████████████████  used 4.5/8.0 TiB  ⚠ reserve short by 0.5 TiB
  san-b  u=0.70  ██                      used 1.5/8.0 TiB
  san-c  u=0.20  █                       used 0.5/8.0 TiB

  1. 102:scsi0  san-a → san-c   1.5 TiB   ~2.2h   Δimbalance −4.53   ℓ/z 1.67
  2. 101:scsi1  san-a → san-b   1.0 TiB   ~1.5h   Δimbalance −2.00   ℓ/z 1.00

  after: san-a u=3.00  san-b u=1.70  san-c u=2.70   spread 53% (from 255%)
  payback: benefit 3.95e6 load·s vs cost 2.62e4 load·s → ratio 151 (need 10) ✓
```

---

## 10. Forecasting

The default decision statistic is the p95 of the trailing window, which is deliberately conservative
and needs no model fitting. Forecasting is behind an interface so it can be strengthened without
touching the optimizer:

```python
class Forecaster(Protocol):
    def predict(self, series: TimeSeries, horizon: timedelta) -> Forecast:
        """Returns point estimate and an upper bound for the horizon."""
```

| Implementation | Behaviour |
|---|---|
| `quantile` *(default)* | p95 over `W`. No seasonality, no fitting, never surprising. |
| `seasonal_naive` | Compare the same hour-of-day over the last `seasonal_lookback_days`; take the p95 across those. Captures a nightly batch window with no model risk. |
| `holt_winters` | Triple exponential smoothing (`statsmodels.tsa.holtwinters.ExponentialSmoothing`, `trend='add'`, `seasonal='add'`, `seasonal_periods = 24h/step`). |

The optimizer consumes the **upper bound**, not the point estimate. Being wrong in the direction of
"this disk is busier than it looks" costs a slightly suboptimal balance; being wrong the other way
migrates a disk onto a storage that is about to be saturated.

Two implementation warnings:

- **Do not compute Holt-Winters in PromQL.** Prometheus's `holt_winters` was renamed
  `double_exponential_smoothing` in Prometheus 3.x and requires
  `--enable-feature=promql-experimental-functions`. More importantly, despite the historical name it
  is **double** exponential smoothing — level and trend only, with **no seasonal component** — so it
  cannot learn a daily cycle. Seasonal forecasting must happen engine-side on data pulled via
  `query_range`.
- Require at least `2 × seasonal_periods` samples before trusting a Holt-Winters fit, and fall back to
  `quantile` otherwise. Validate by backtesting against the last 24h before letting a forecast drive
  a migration.

---

## 11. Configuration

See [`config/drs.example.yaml`](config/drs.example.yaml) for the fully annotated reference. The
requirement-to-setting mapping:

| Requirement | Setting |
|---|---|
| Storage groups VMs may not leave | `groups[].storages[]` |
| 2× largest disk free for snapshots | `snapshot_reserve.factor` (default `2.0`), per-storage override |
| Min % changed traffic before migrating | `gates.drift_threshold` (default `0.10`) |
| % I/O difference across the group | `gates.imbalance_threshold` |
| Timeframe considered | `window.lookback` (default `24h`) |
| Minimal number of migrations | `objective.beta_move_count` |
| Keep a VM's disks together | `objective.kappa_vm_affinity` |
| Migration load accounted for | `migration.*`, `objective.gamma_move_bytes` |
| Manual vs automatic | `execution.mode` |
| Forecasting | `forecast.model` |

---

## 12. Implementation phases

Each phase is independently testable and useful on its own.

| # | Phase | Done when |
|---|---|---|
| 1 | `config.py`, `metrics.py`, `drs verify-metrics` | Real metric/label names confirmed against the live Prometheus; per-disk load printed |
| 2 | `pve.py`, `topology.py` | `drs show-load` prints every storage with its disks, sizes, loads and reserve status |
| 3 | `loadmodel.py` + gates | Correct act/no-act decision per group, with the reasoning shown |
| 4 | `heuristic.py` + `schedule.py` | End-to-end plan in `dry-run`, ordered and transient-feasible |
| 5 | `payback.py` | Plans rejected/trimmed on cost grounds, arithmetic shown |
| 6 | `optimize.py` (MILP) | Matches or beats the heuristic on the section 14 fixture |
| 7 | `execute.py` | `confirm` mode against a lab cluster |
| 8 | `auto` mode + time windows | Unattended operation |
| 9 | `forecast.py` beyond p95 | Seasonal-naive validated by backtest |

Phase 4 before phase 6 is deliberate: a working heuristic makes the MILP verifiable, and it is the
production fallback for large groups. Do not start with the solver.

---

## 13. Failure modes and safety

| Hazard | Handling |
|---|---|
| Metric gap / disk below `min_coverage` | Use last known load from state; flag in output; never treat as zero |
| Counter reset (VM reboot, node migration) | Handled by `rate()`; `sum by (vmid, device)` collapses node labels |
| VM live-migrated between nodes mid-plan | Re-fetch node before each move (§9.2); mismatch → abort move, re-plan |
| Disk has an existing snapshot chain | Excluded and pinned by default (`skip_vms_with_snapshots`) |
| Thin provisioning | `assume_thick_provisioning: false` uses allocated size from `/content`; note allocation can *grow* during a move |
| Foreign volumes on a storage | Counted via `count_foreign_volumes`; otherwise the reserve silently overstates free space |
| Orphaned target volume after a failure | Detected and reported, never auto-deleted (§9.3) |
| Storage already violating the reserve | Soft slack `r_s` keeps the model feasible; violation bypasses gates and is scheduled first |
| Two DRS instances running | Advisory lock in `state.json` plus a startup scan for in-flight `move_disk` UPIDs owned by the DRS user |
| Solver infeasible or timing out | Fall back to the heuristic; never emit a partial/unvalidated assignment |
| `bwlimit` misunderstood | It is **KiB/s** in the API; config is bytes/s and must be converted |

Overarching rule: **the reserve constraint is never traded against balance.** Every other objective
term is soft; (C5) is enforced before, during and after every move.

---

## 14. Worked example

A complete, self-consistent fixture. Implementations should reproduce these numbers exactly.

### 14.1 Input

Group `fc-tier1`, three storages of 8.0 TiB each, all `capability_weight = 1.0`, `f = 2.0`,
no foreign volumes.

| Disk | VM | `z_d` (TiB) | `ℓ_d` | On |
|---|---|---|---|---|
| `101:scsi0` | 101 | 2.0 | 3.0 | san-a |
| `101:scsi1` | 101 | 1.0 | 1.0 | san-a |
| `102:scsi0` | 102 | 1.5 | 2.5 | san-a |
| `103:scsi0` | 103 | 0.5 | 0.4 | san-b |
| `104:scsi0` | 104 | 1.0 | 0.3 | san-b |
| `105:scsi0` | 105 | 0.5 | 0.2 | san-c |

`Σℓ = 7.4`, so `u* = 7.4 / 3 = 2.4667`.

### 14.2 Initial state

| Storage | `L_s` | used | `Z_s` | `used + f·Z_s` | vs `C_s` |
|---|---|---|---|---|---|
| san-a | 6.50 | 4.5 | 2.0 | **8.5** | 8.0 → **violates by 0.5 TiB** |
| san-b | 0.70 | 1.5 | 1.0 | 3.5 | 8.0 ✓ |
| san-c | 0.20 | 0.5 | 0.5 | 1.5 | 8.0 ✓ |

- Spread `(6.50 − 0.20)/2.4667 = 2.554` → **255%**, far above the 20% gate.
- `E_before = |6.50−2.4667| + |0.70−2.4667| + |0.20−2.4667| = 4.0333 + 1.7667 + 2.2667 = 8.0667`
- san-a already breaches the snapshot reserve. This is why (C5) carries slack `r_s` rather than being
  hard — a hard constraint would report *infeasible* here and refuse to help.

### 14.3 Solution

With default weights (`α=1.0, β=0.25, γ=0.05/TiB, κ=0.5`) the optimum is **three** moves:

1. `102:scsi0` san-a → san-c
2. `101:scsi1` san-a → san-b
3. `105:scsi0` san-c → san-b

| Storage | `L_s` | used | `Z_s` | `used + f·Z_s` | ✓ |
|---|---|---|---|---|---|
| san-a | 3.00 | 2.0 | 2.0 | 6.0 | ✓ |
| san-b | 1.90 | 3.0 | 1.0 | 5.0 | ✓ |
| san-c | 2.50 | 1.5 | 1.5 | 4.5 | ✓ |

`E_after = 0.5333 + 0.5667 + 0.0333 = 1.1333`, spread **44.6%**. The reserve violation is repaired.

**The `β` knob, demonstrated.** The third move improves imbalance by only
`1.5333 − 1.1333 = 0.400`. Its objective contribution is:

```
α·ΔE + β·1 + γ·0.5 TiB  =  −0.400 + 0.250 + 0.025  =  −0.125   → accepted at β=0.25
                        =  −0.400 + 0.500 + 0.025  =  +0.125   → rejected at β=0.50
```

At `beta_move_count: 0.5` the solver returns the **two-move** plan instead, ending at
`(3.00, 1.70, 2.70)`, `E = 1.5333`, spread 53%. This is exactly the "minimal number of migrations"
trade-off made explicit and tunable; both plans are correct, and `β` chooses.

**The affinity trade-off, demonstrated.** Both plans split VM 101 (`scsi0` on san-a, `scsi1` on
san-b), incurring `κ = 0.5`. Keeping VM 101 together forces san-a to `L = 4.0` and the best reachable
`E` becomes `3.133`. Comparing: `3.133 + 0` (together) vs `1.1333 + 0.5` (split) `= 1.633`. Splitting
wins by 1.5, so high I/O legitimately overrides the affinity preference — precisely the intended
behaviour.

### 14.4 Ordering

`102:scsi0` is scheduled first: it alone repairs san-a's reserve violation (`4.5 → 3.0` used, so
`3.0 + 4.0 = 7.0 ≤ 8.0`), and it also has the largest imbalance reduction. Transient checks:

```
move 1 → san-c:  used 0.5 + 1.5 = 2.0,  max(Z_c, 1.5) = 1.5,  2.0 + 3.0 = 5.0 ≤ 8.0  ✓
move 2 → san-b:  used 1.5 + 1.0 = 2.5,  max(Z_b, 1.0) = 1.0,  2.5 + 2.0 = 4.5 ≤ 8.0  ✓
move 3 → san-b:  used 2.5 + 0.5 = 3.0,  max(Z_b, 0.5) = 1.0,  3.0 + 2.0 = 5.0 ≤ 8.0  ✓
```

### 14.5 Payback

At `bwlimit = 200 MiB/s`, `ω_src = ω_dst = 1.0`, `H = 7d = 604800 s`, `λ = 10`, for the two-move plan:

| Move | Size | Duration | `cost = 2 × duration` |
|---|---|---|---|
| `102:scsi0` | 1.5 TiB | 7 864 s (2.18 h) | 15 729 load·s |
| `101:scsi1` | 1.0 TiB | 5 243 s (1.46 h) | 10 486 load·s |
| | | **Σ** | **26 214 load·s** |

```
benefit = ΔE · H = 6.5333 × 604 800 = 3 951 360 load·s
ratio   = 3 951 360 / 26 214 = 150.7   ≥ λ = 10   → ACCEPT
```

**A move that fails payback.** Consider instead a 4.0 TiB archive disk with `ℓ = 0.1` whose relocation
would improve `E` by only 0.05:

```
cost    = 2 × (4.0 TiB / 200 MiB/s) = 2 × 20 972 = 41 943 load·s
benefit = 0.05 × 604 800 = 30 240 load·s
ratio   = 0.72   <  λ = 10   → REJECT
```

The migration would generate more I/O than it saves within the horizon. This is the requirement that
"migrating a very large disk might generate more traffic than we are trying to save", enforced
numerically.

---

## 15. Requirements traceability

| Original requirement | Where addressed |
|---|---|
| Proxmox API via user/password | §3.5 |
| Per-disk metrics for all running VMs | §3.1, §3.4 (blockstat via Prometheus, not RRD — see §3.2) |
| Equalize I/O across storages in a group | §4, §5.3 (C6), §5.4 |
| VMs confined to their storage group | §5.1, §5.3 (C1, C2) |
| Restrict to shared storages | §5.3 (C2) |
| 2× largest disk free for snapshots | §5.3 (C5) |
| …including *during* migrations | §8.1 transient invariant |
| Reserve factor configurable | `snapshot_reserve.factor`, per-storage override |
| Minimal number of migrations | §5.4 `β` term; demonstrated §14.3 |
| Min % changed traffic before acting (10%) | §6 drift gate |
| % I/O difference across the group | §6 imbalance gate |
| Keep a VM's disks together, unless space/IO forces otherwise | §5.3 (C3), §5.4 `κ`; demonstrated §14.3 |
| Mathematical optimization formulation | §5 |
| Migration order planned | §8 |
| Automatic or manual confirmation | §9.1 (`dry-run` / `confirm` / `auto`) |
| Forecasting (Holt-Winters or other) | §10 |
| Configurable decision timeframe, default 24h | `window.lookback`; §3.4 |
| Migration load counted against the benefit | §7; demonstrated §14.5 |
