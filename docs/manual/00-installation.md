# Installation and requirements

## What you need

- **Proxmox VE 9.2**, or a management host with network access to a PVE 9.x
  cluster's API (tcp/8006) — the tool does not need to run on a cluster
  member.
- **A Prometheus** already receiving PVE's per-disk `blockstat` metrics via
  the InfluxDB output plugin and Telegraf. If your cluster's dashboards
  already show per-VM disk I/O, this is already true; `pve-storage-drs
  verify-metrics` (page 2) confirms it before you rely on it. No new exporter
  or collector is required — see `IMPLEMENTATION_PLAN.md` section 3.1 if you
  want the detail of where the data comes from.
- **A PVE user or API token** with read access to VM and storage inventory
  and permission to call `move_disk`. An API token is preferred for
  unattended operation (`execution.mode: auto`); a username/password pair
  works for interactive use. See "Setting up the PVE credential" below for
  the exact privileges — the obvious-looking "just grant Audit everywhere"
  is not enough, and the gap is silent rather than an error.

## Setting up the PVE credential

Grant, on **every storage the tool will manage** (the shared, image-holding
storages in your `groups`, not backup targets):

- `Datastore.Audit` **and `Datastore.Allocate`** — not Audit alone.
  `GET /nodes/{node}/storage/{storage}/content`, which the tool uses to
  cross-check each disk's real allocated size, silently returns an empty
  list under Audit-only permission: a clean `200` response with no content
  and no error, indistinguishable from "this storage genuinely has nothing
  on it" unless you already know to be suspicious. Audit alone is enough for
  every *other* read call the tool makes; this one endpoint is the
  exception, verified against a live PVE 9.2.11 cluster (see
  `IMPLEMENTATION_PLAN.md` section 3.5's note). Getting this wrong does not
  make the tool fail loudly — it makes it under-count what already occupies
  each storage, which quietly erodes the section 5.3 snapshot reserve it
  exists to protect.
- Grant it **at each storage's own path** (`/storage/<id>`), not only at the
  parent `/storage` — that is the grant confirmed to work.
- Also add `VM.Audit` cluster-wide (`/`) for VM inventory and config, which
  `PVEAuditor` already includes if you use that built-in role as a base.

**If you are using an API token** (recommended — see above), Proxmox's
privilege separation means **the token has its own, separate ACL entries
from its owning user**. A role granted to the user alone has no effect on
the token, and a role granted to the token alone has no effect either unless
the user has it too: the token's effective permission is the *intersection*
of the two. Grant the same roles to both the user and `user@realm!tokenid`,
or disable privilege separation on the token (Datacenter → Permissions →
API Tokens → uncheck "Privilege Separation") so it always matches its
user's permissions exactly.

A concrete, minimal setup: create a role (e.g. `pve-storage-drs`) with
`Datastore.Allocate,Datastore.Audit,VM.Audit`, then add it as an ACL entry
for both the user and the token at `/` for `VM.Audit`, and at each managed
storage's `/storage/<id>` path for the datastore privileges.

**Two further, VM-level privileges are needed once `apply` executes a
move** — `VM.Config.Disk` and `VM.Migrate`, both cluster-wide (`/`) or at
least on every VM whose disks live in a managed group, granted to both the
user and the token exactly as above. Neither is needed for anything this
build actually runs today: `verify-metrics`, `show-load` and
`verify-storages` only read, and only `move_disk` (called by `apply`, not
yet implemented — `30-safety-and-status.md`) needs them. Grant them now
alongside the privileges above so the credential does not need revisiting
later; if you set up the credential read-only for now, add
`VM.Config.Disk,VM.Migrate` to the role before you first run `apply`.

## Installing the package

On a Debian trixie host (which is what Proxmox VE 9.x is built on):

```sh
apt install pve-storage-drs
```

This installs the `pve-storage-drs` executable, its manpage, the example
configuration at `/usr/share/doc/pve-storage-drs/examples/drs.example.yaml`, and this
manual and the specification as PDFs under `/usr/share/doc/pve-storage-drs/`.

`coinor-cbc` and `python3-pulp` are `Recommends`, not `Depends`: without them
the tool still plans, using the dependency-free heuristic of
`IMPLEMENTATION_PLAN.md` section 5.5, but a Debian install should have them —
`apt install pve-storage-drs` pulls them in by default.

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

1. `pve-storage-drs -c /etc/pve/drs.yaml verify-metrics` — confirms the
   configured metric and label names actually exist in your Prometheus. See
   [`20-verifying-metrics.md`](20-verifying-metrics.md).
2. Read [`10-configuration.md`](10-configuration.md) and adjust the storage
   groups, thresholds and weights for your cluster.
3. See [`30-safety-and-status.md`](30-safety-and-status.md) for exactly which
   commands this build supports end to end today, and which still report
   "not implemented yet".
