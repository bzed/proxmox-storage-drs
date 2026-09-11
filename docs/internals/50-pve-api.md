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
caches anything, and the per-run topology cache belongs to `topology.py`
(section 3.5), which is also where the bounded thread pool for the O(VMs)
config fetch lives (`60-topology.md`, REVIEW.md P-02).

`_call()` does retry exactly one failure mode: `proxmoxer.AuthenticationError`
gets one reauthenticate-and-retry cycle (REVIEW.md P-01) before becoming a
`PveApiError`, via a `reauthenticate` callback `build_client()` wires in —
a full fresh login through `_build_api()` again, not a reuse of the
rejected ticket. This is not a general retry policy (a `ResourceException`
or a transport failure still fails immediately, on the first attempt); it
exists specifically because a ticket can expire for reasons with nothing to
do with the call that hits it — a long `apply --confirm` wait, a suspended
process, a clock jump — and `proxmoxer`'s own lazy per-request renewal only
notices the age of its *own* clock, not whether the server-side ticket
actually outlived a gap that long. A test double built with a bare
`PveClient(fake_api)` (no `reauthenticate=`) gets none of this — it behaves
exactly as it did before P-01, which is what every existing fake in
`tests/unit/fakes.py` relies on.

`build_client()` also applies `proxmox.ticket_refresh_seconds` to the
constructed session, best-effort: `proxmoxer` 2.x has no constructor
argument for a password/ticket auth's refresh interval (it is a hard-coded
`renew_age = 3600` class attribute on `ProxmoxHTTPAuth`, checked lazily on
whichever request happens to run after it elapses), so
`_apply_ticket_refresh_seconds()` reaches into `api._backend.auth` —
undocumented `proxmoxer` internals, not its public interface — to override
that instance's `renew_age` after login. Deliberately narrow: it only ever
*tightens* proxmoxer's own schedule, never replaces its refresh logic, and
if a future `proxmoxer` version reshapes this (or the backend is not
`https`, or the auth is API-token, which has no ticket at all), the
`getattr`/`hasattr` guards make it a silent no-op — the P-01
reauthenticate-and-retry above still catches the case this can't reach.

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

**`node_names()` uses `GET /nodes`, not the `node` fields already visible on
`vm_resources()`/`storage_resources()`.** Section 3.4's PromQL node-scoping
filter (`metrics.build_node_selector()`) is built from this list, and it
needs *every* cluster node, not only the ones currently hosting a VM or a
shared storage — an idle node would silently be missing from either of
those, and dropping a real node out of the filter is exactly the kind of
quiet under-count section 3.4 exists to avoid (a VM that migrated onto the
missing node partway through the window would look like it has less
history than it really does). Called once per command invocation
(`cli._resolve_node_selector_for_run()`), not per group.

**`cluster_name()` uses `GET /cluster/status`, filtered to the one entry
whose `type` is `"cluster"`** (every other entry is `type: "node"`) --
confirmed live against a real PVE 9.2 cluster, `{"type": "cluster", "name":
"pvezebe", "nodes": 3, "quorate": 1, ...}`. Needs `Sys.Audit` at `/`, the
one privilege none of this project's other read calls require --
`docs/manual/00-installation.md` asks for it unconditionally, since
`metrics.labels.cluster` defaults to a real label name (`"cluster"`) and
so this is the normal call every `plan`/`show-load`/`apply`/`explain` run
makes, not a conditional one. Returns `None` rather than raising when the
entry is missing or unnamed, the same "let the caller decide" contract
`node_names()` already has -- `metrics.resolve_node_selector()` treats
that `None` as "fall back to the node list," not fatal. A denied call
(`PveApiError` -- missing `Sys.Audit`, most often a token provisioned
before this tier existed) is caught the same way, one layer up in
`cli._resolve_node_selector_for_run()` itself: logged as a warning, then
treated identically to `None` -- REVIEW.md W-08, so a run never fails
outright over a scoping lookup that has an equally-correct fallback.
Called at most once per command invocation (`cli._resolve_node_selector_for_run()`), and
skipped only when `metrics.labels.cluster` is explicitly `null`.

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
