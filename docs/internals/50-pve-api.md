# The Proxmox VE API client

**What does this page answer?** Why is `pve.py` built on `proxmoxer` instead
of a hand-rolled ticket/CSRF client, and what does each of its methods
actually call? Describes `proxmox_storage_drs/pve.py`.

## Why `proxmoxer`

`IMPLEMENTATION_PLAN.md` section 3.5 explains the decision in full; the
short version is `proxmoxer`'s **backend abstraction**. The same
`ProxmoxAPI` attribute-chaining interface
(`api.nodes(node).qemu(vmid).config.get()`) is available over plain HTTPS
(what `build_client()` uses today) or over SSH, either shelling out to the
system's own `ssh`+`pvesh` (`openssh`) or with an in-process client
(`ssh_paramiko`). A deployment that cannot open the API port to the
management host becomes a different keyword argument in `build_client()`,
with no change anywhere else — not to `PveClient`'s methods, and not to any
of their callers.

## `build_client()`: the one place auth is assembled

`config.py`'s `ProxmoxConfig` keeps `verify_ssl` (bool) and `ca_file`
(path-or-`None`) as two separate knobs, because that is how an operator
thinks about them; `requests` (and so `proxmoxer`'s https backend) wants one
value, a bool or a CA-bundle path, passed as `verify`. `build_client()` is
the one place that reconciles the two. It is also the one place
`proxmox.auth.token_id`'s `user@realm!tokenname` format is split into
`proxmoxer`'s separate `user`/`token_name` keyword arguments — never
duplicate that parsing anywhere else.

Every failure `ProxmoxAPI(...)` itself can raise
(`proxmoxer.AuthenticationError`, or a `requests.RequestException` if the
host is simply unreachable) is caught here and re-raised as `PveApiError`,
so every caller of `build_client()` and every `PveClient` method has exactly
one exception type to catch.

## `PveClient`: one method per section 3.5 endpoint

Every method is a single API call, wrapped through the private `_call()`
helper, which is the one place `proxmoxer.ResourceException` (HTTP-level API
errors) and `requests.RequestException` (transport failures `proxmoxer`'s
https backend does not wrap itself) both become `PveApiError`. No method
caches anything and none retries — the per-run topology cache and any retry
policy belong to `topology.py` (not yet written), which is also where the
section 3.5 bounded thread pool for the O(VMs) config fetch will live.

**`storage_definitions()` deliberately uses `GET /storage` (the list form),
never the singular `GET /storage/{id}`, even though only one storage's
config is needed in some callers.** This was verified empirically against a
real PVE 9.2.11 cluster during development
([[dev-cluster-access]] in the maintainer's notes, not reproduced here): an
API token granted only `Datastore.Audit` can list every storage's full
config — including `saferemove`/`saferemove_throughput` — via `GET
/storage`, but the identical data via `GET /storage/{id}` for the same
storage returns `403 Forbidden (Datastore.Allocate)`. The single-item route
apparently backs an edit-UI flow gated by the ability to change the config,
not merely read it. Since the list form returns the same per-storage object
for every storage in one call, there is no reason to ever call the singular
form, and using it would quietly force a Storage DRS token to hold more
privilege than the tool actually needs. `IMPLEMENTATION_PLAN.md` section 3.5
was corrected to match once this was found — see that section's note.

**`storage_content()` returned an empty list for every RBD-pool-backed
storage on that same test cluster**, across every node and every filter
tried (`content=images`, a `vmid` filter), with no error at any privilege
level tested. `pve.py` does not paper over this: the method returns exactly
what the API returned, because guessing at *why* a real cluster behaves this
way — a Ceph-side permission the audit token cannot see, or a genuine
limitation of `/content` listing for RBD-backed storage on this specific
setup — is exactly what `.agents/domain-invariants.md` rule 10 warns
against doing from an agent's own inference. `topology.py`, when it consumes
this method, needs a documented fallback for the case where `/content` is
authoritative for nothing (falling back to the VM config's own `size=`
value, per section 3.5's "cross-checked against `/storage/{storage}/content`
_which is authoritative for what is actually allocated_" — that sentence
assumes content listing works, and this cluster is a live counterexample)
rather than assuming every deployment's storage backend populates it.

## `move_disk()`: the one and only bytes/s -> KiB/s conversion

Section 9.2 is explicit that `bwlimit`'s bytes/s-to-KiB/s conversion happens
"at the call site and nowhere else." `PveClient.move_disk()` is that call
site: every caller in this codebase, present and future, passes
`bwlimit_bytes_per_sec` in the same unit `migration.bwlimit_bytes_per_sec`
already uses, and the division by 1024 (rounded, since the API wants an
integer) happens exactly once, inside this method. `format` defaults to
`None` and is only ever forwarded when a caller explicitly passes one —
`move_disk` without `format=` preserves the source format, which is what
section 3.5 requires by default.
