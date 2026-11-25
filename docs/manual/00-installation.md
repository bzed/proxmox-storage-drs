# Installation and requirements

## What you need

- **Proxmox VE 9.2**, or a management host with network access to a PVE 9.x
  cluster API (tcp/8006). The tool does not need to run on a cluster member.
- **A Prometheus-compatible backend** that already receives PVE's per-disk
  `blockstat` metrics via the InfluxDB external metric server. The backend
  can be plain Prometheus, VictoriaMetrics, or gigapipe on ClickHouse. The
  project's own cluster uses gigapipe. If your cluster dashboards already
  show per-VM disk I/O, the export side is already on. That is not the same
  as all six counters surviving the transport. Losing one counter is a real
  failure, and the failure is silent. Read
  [`05-metrics-pipeline.md`](05-metrics-pipeline.md) before you write the
  `metrics` block. Run `pve-storage-drs verify-metrics` before you rely on
  any plan. The tool needs no new exporter or collector.
- **A PVE user or API token** with read access to VM and storage inventory,
  plus permission to call `move_disk`. Use an API token for unattended
  operation (`execution.mode: auto`). Use a username and password for
  interactive use. The section "Setting up the PVE credential" below lists
  the exact privileges. The obvious
  approach, "just grant Audit everywhere", is not enough. The
  gap is silent, not an error.

## Setting up the PVE credential

Grant the following on **every storage the tool will manage** (the shared,
image-holding storages in your `groups`, not backup targets):

- `Datastore.Audit` **and `Datastore.Allocate`**, not Audit alone.
  The tool uses `GET /nodes/{node}/storage/{storage}/content` to cross-check
  each disk's real allocated size. Under an Audit-only permission that
  endpoint returns a `200` status, an empty list, and no error. The result
  looks the same as a storage that genuinely has nothing on it. Audit alone
  is enough for every *other* read call the tool makes. This one endpoint is
  the exception. A live PVE 9.2.11 cluster confirms the behavior (see
  `IMPLEMENTATION_PLAN.md` section 3.5's note). A missing permission does
  not make the tool fail. The tool under-counts what already occupies each
  storage instead. The under-count shrinks the **snapshot reserve**. The
  reserve is the free capacity `pve-storage-drs` keeps clear on every
  managed storage. The tool sizes it from
  `snapshot_reserve.factor`/`free_space.soft` (see
  [`10-configuration.md`](10-configuration.md)). The reserve keeps a
  snapshot, or a disk that exists on two storages during a migration, from
  running a LUN out of space. The under-count makes the storage appear to
  have more free space than it has. The tool then plans and runs migrations
  that reduce a safety margin it believes it still protects.
- Grant it **at each storage's own path** (`/storage/<id>`), not only at the
  parent `/storage`. The storage-path grant is
  the one that is confirmed to work.
- Also add `VM.Audit` cluster-wide (`/`) for VM inventory and config. If you
  use the built-in role `PVEAuditor` as a base, it already includes it.

**If you use an API token** (recommended, see above), Proxmox privilege
separation gives **the token its own ACL entries, separate from those of
its user**. A role granted to the user alone does not affect the token. A
role granted to the token alone does not affect it either unless the user
has it too. The token's effective permission is the *intersection* of the
two. Grant the same roles to both the user and `user@realm!tokenid`. Or
disable privilege separation on the token (Datacenter → Permissions →
API Tokens → uncheck "Privilege Separation"). Then the token always
matches its user's permissions exactly.

Here is a minimal setup. Create a role (e.g. `pve-storage-drs`) with
`Datastore.Allocate,Datastore.Audit,VM.Audit`. Add the role as an ACL entry
for both the user and the token. Add it at `/` for `VM.Audit`. Add it at
each managed storage's `/storage/<id>` path for the datastore privileges.

**`apply` needs two more VM-level privileges once it executes a move**:
`VM.Config.Disk` and `VM.Migrate`. Grant both cluster-wide (`/`), or at
least on every VM whose disks live in a managed group. Grant them to both
the user and the token, exactly as above. You do not need them for
`verify-metrics`, `show-load`, or `verify-storages`. Those commands only
read. `apply` needs them for `move_disk` itself, in every
`execution.mode` (`30-safety-and-status.md`). Grant them now, with the
privileges above. Then you do not revisit the credential later. If you set
the credential up read-only for now, add `VM.Config.Disk,VM.Migrate` to the
role before your first `apply` run.

## Installing the package

Install on a Debian trixie host. Proxmox VE 9.x runs on trixie. The project
publishes every release as a ready-made package on its GitHub releases page,
<https://github.com/bzed/proxmox-storage-drs/releases>. Each release has
one `pve-storage-drs_<version>_all.deb` file that works on any
architecture, with a `SHA256SUMS` file beside it. No apt repository exists
yet. Download the `.deb` and install it with `apt`. `apt` fetches the
dependencies from the trixie archive the host already uses:

```sh
VERSION=0.1.21      # the newest release on the releases page
BASE=https://github.com/bzed/proxmox-storage-drs/releases/download/debian/$VERSION
wget "$BASE/pve-storage-drs_${VERSION}_all.deb" "$BASE/SHA256SUMS"
sha256sum -c SHA256SUMS
apt install ./pve-storage-drs_${VERSION}_all.deb
```

The package is not signed. `SHA256SUMS` comes from the same page as the
`.deb`. The check detects a corrupted download, not a tampered release. The
project's CI publishes a release only after it builds the package in a clean
Debian trixie container. That run also checks the package with lintian,
installs it, and runs its tests. If you keep a local apt repository, put
the `.deb` into it. Then `apt install pve-storage-drs` and `apt upgrade`
work as usual. From a source checkout, `make deb` builds the same package.

The install puts the `pve-storage-drs` executable, its manpage, the example
configuration at `/usr/share/doc/pve-storage-drs/examples/drs.example.yaml`,
and the whole documentation set under `/usr/share/doc/pve-storage-drs/`.
The set has this manual as `manual/*.md`, the internals guide as
`internals/*.md`, and the specification as `IMPLEMENTATION_PLAN.md`. Each
file also ships as a typeset PDF. The Markdown files stay uncompressed on
purpose. A cluster node has no GUI. It often has no way to get a PDF off
the node. So the command `less
/usr/share/doc/pve-storage-drs/manual/20-verifying-metrics.md` must work on
the machine that has the problem.

`coinor-cbc` and `python3-pulp` are `Depends`: `apt install pve-storage-drs`
always gets a real MILP solver, no separate step needed. The tool still
plans without one — using the dependency-free heuristic of
`IMPLEMENTATION_PLAN.md` section 5.5 — but that is no longer what a Debian
install lands on by default; it is what a non-Debian `pip install` with no
solver extra, or a solve that fails or times out, falls back to.

## Where the configuration lives

`/etc/pve/drs.yaml`. On a cluster member this path is on `pmxcfs`, the
cluster filesystem, so the file is automatically the same on every node —
there is exactly one copy and no question of which one is authoritative. A
management host that is not itself a cluster member simply keeps an ordinary
file at that same path.

Two things follow from that placement, and both matter before you put a
password in the file:

- **An edit is live on every node the instant it is saved.** There is no
  staging step. This is why configuration mistakes are always hard failures
  (see [`30-safety-and-status.md`](30-safety-and-status.md)) rather than
  warnings, and why dry-run is the default execution mode.
- **Files under `/etc/pve` are group-readable by `www-data`** — the PVE web
  server's user. Check `ls -l /etc/pve/drs.yaml` on your cluster before
  deciding whether a plaintext `password:` is acceptable; the safer choice is
  an API token with `PVE_TOKEN_SECRET` set in the environment (or a systemd
  credential) rather than written into the file at all.

Copy `/usr/share/doc/pve-storage-drs/examples/drs.example.yaml` to `/etc/pve/drs.yaml`
and edit it — every key is commented with its default and what it does. The
full reference is [`10-configuration.md`](10-configuration.md).

## Where the configuration is *not*

`state.path` (default `/var/lib/pve-storage-drs/state.json`) is deliberately **not**
on `/etc/pve`. It is rewritten on every run, `pmxcfs` writes need cluster
quorum, and the state it holds — cooldown timestamps, the load vector at the
last balance, the run lock — is meaningful only to the one host that is
actually running the timer. See
[`10-configuration.md#statepath`](10-configuration.md#statepath).

## Running the timer on exactly one host

Putting the configuration on `pmxcfs` does not make the tool cluster-aware.
`state.json` is node-local: each node would keep its own cooldowns, its own
drift baseline and its own run lock, which do not coordinate with each
other. **Enable the systemd timer on exactly one host.** The one thing that
*does* cross the cluster is a startup scan for in-flight `move_disk` UPIDs
owned by the DRS user, which is what keeps two accidental instances from
actively conflicting (they degrade to "slow and redundant" instead).

## First steps after installing

1. Read [`05-metrics-pipeline.md`](05-metrics-pipeline.md) — where the six
   per-disk counters come from, and how a Telegraf-to-Prometheus transport
   can drop one of them without ever logging an error.
2. Read [`10-configuration.md`](10-configuration.md) and adjust the storage
   groups, thresholds and weights for your cluster.
3. `pve-storage-drs -c /etc/pve/drs.yaml verify-metrics` — confirms the
   configured metric and label names actually exist in your backend, and
   cross-checks the six metrics against each other. See
   [`20-verifying-metrics.md`](20-verifying-metrics.md).
4. See [`30-safety-and-status.md`](30-safety-and-status.md) for exactly which
   commands this build supports end to end today.
