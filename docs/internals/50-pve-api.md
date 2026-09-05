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

**`storage_content()` returned an empty list — not an error — on every
storage, node and content-type filter tried, until the token also held
`Datastore.Allocate` on that storage.** This was genuinely surprising and
worth calling out precisely because it is a *silent* false negative:
`Datastore.Audit` alone gives a clean `200` with `{"data": []}`, which looks
exactly like "this storage legitimately has no tracked content" rather than
"the caller cannot see it." It was not guessed at — see
`IMPLEMENTATION_PLAN.md` section 3.5's note, which records the exact
before/after (0 entries with Audit only, 37 and 1 entries respectively for
two real storages once `Datastore.Allocate` was added) on the same live
cluster. **The practical consequence: `pve.py`'s own "keep the token to
Audit-only" goal for `storage_definitions()` does not extend to
`storage_content()`** — a Storage DRS token genuinely needs
`Datastore.Allocate` (bundled with `Datastore.Audit` in one role) on every
storage it manages, or `topology.py` will silently compute `Uˢᵉˣᵗ` (section
5.1.1) as if every storage were empty of untracked volumes, with no error to
notice by. `docs/manual/00-installation.md` states the exact minimum ACL
grant an operator needs; this is not a place to economize on privilege out
of a preference that turned out not to match reality.

Two more things about Proxmox's ACL model this surfaced, both now reflected
in the manual's token-setup instructions: **an API token's effective
permission is the *intersection* of its owning user's permissions and
whatever is granted to the token itself** when privilege separation is on
(the default) — granting a role to only one of the two has no effect, both
need it; and the grant that was confirmed to work was made explicitly at
each `/storage/{id}` rather than only at the parent `/storage` path, so that
is what the manual instructs, rather than relying on propagation that was
not cleanly isolated as working or not.

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
