# The Proxmox VE API client

**What does this page answer?** Why does `pve.py` use `proxmoxer` instead
of a hand-rolled ticket/CSRF client? What does each of its methods
actually call? This page describes `proxmox_storage_drs/pve.py`.

## Why `proxmoxer`

`pve.py` is built on `proxmoxer` rather than a hand-rolled ticket/CSRF
client for its **backend abstraction**. The same `ProxmoxAPI`
attribute-chaining interface (`api.nodes(node).qemu(vmid).config.get()`)
works over plain HTTPS. That is what `build_client()` uses today. The
interface also works over SSH. Over SSH, it shells out to the system's own
`ssh`+`pvesh` (`openssh`). It can also use an in-process client
(`ssh_paramiko`). A deployment that cannot open the API port to the
management host becomes a different keyword argument in `build_client()`.
No other part of the code changes. `PveClient`'s methods do not change.
Their callers do not change either. (`IMPLEMENTATION_PLAN.md` section
3.5 has the full evaluation of the alternatives that led here.)

## `build_client()`: the one place auth is assembled

`config.py`'s `ProxmoxConfig` keeps `verify_ssl` (bool) and `ca_file`
(path-or-`None`) as two separate knobs. An operator thinks about them this
way. `requests` (and so `proxmoxer`'s https backend) wants one value. That
value is a bool or a CA-bundle path, passed as `verify`. `build_client()`
is the one place that reconciles the two. `build_client()` is also the one
place that splits `proxmox.auth.token_id`'s `user@realm!tokenname` format
into `proxmoxer`'s separate `user`/`token_name` keyword arguments. Never
duplicate that parsing anywhere else.

`build_client()` catches every failure `ProxmoxAPI(...)` itself can raise.
Those failures are `proxmoxer.AuthenticationError`, or a
`requests.RequestException` if the host is unreachable. The function
re-raises each one as `PveApiError`. Every caller of `build_client()` and
every `PveClient` method then has exactly one exception type to catch.

## `PveClient`: one method per section 3.5 endpoint

Every method is a single API call. Every method wraps the call through the
private `_call()` helper. `_call()` is the one place `proxmoxer.ResourceException`
(HTTP-level API errors) and `requests.RequestException` (transport failures
the https backend does not wrap itself) both become `PveApiError`. No
method caches anything. The per-run topology cache belongs to `topology.py`
(section 3.5). `topology.py` also holds the bounded thread pool for the
O(VMs) config fetch (`60-topology.md`, REVIEW.md P-02).

`_call()` retries two failure modes, and nothing else.

**1. Expired ticket (REVIEW.md P-01).** `build_client()` wires in a
`reauthenticate` callback. On `proxmoxer.AuthenticationError`, `_call()`
runs one reauthenticate-and-retry cycle. The callback performs a full fresh
login through `_build_api()` again. It never reuses the rejected ticket.
A ticket can expire for reasons unrelated to the call that hits it. A long
`apply --confirm` wait, a suspended process, or a clock jump can each
expire a ticket. `proxmoxer`'s own lazy renewal only checks the age of its
*own* clock. A test double built with a bare `PveClient(fake_api)` (no
`reauthenticate=`) gets no re-login.

**2. Transient failures.** The API (or whatever sits in front of it: a
firewall, a load balancer, a VIP that moves between nodes) did not give a
usable answer. Asking again may work. The line between transient and hard:

| Failure | Class |
|---|---|
| connection refused/reset, timeout, TLS handshake failure, truncated body, a non-JSON body (a firewall's HTML page) | transient |
| HTTP 429 or 5xx (PVE's 595/596 included) | transient |
| login answered with a status other than 401/403 (a failing proxy) | transient |
| login answered 401/403, API answered 401/403 (**not authorized**) | **hard** |
| any other 4xx, a malformed URL/scheme/header | hard |

`proxmoxer` words a failed login as `... code: <HTTP status>`. That
message is the only place the status survives. `_auth_failure_is_transient()`
parses it. A login failure with no status in the message stays hard.

`_call()` repeats only `idempotent` calls. `move_disk` passes
`idempotent=False`. A dropped POST is ambiguous. A blind repeat could start
a second move. The retry logic has two regimes. Inside `outage_tolerance()`
it runs the long 5 s→60 s loop below. Outside it (every read), it runs a
short retry of 1 s, 2 s and 4 s. Each wait is scaled by a random factor in
[0.5, 1.5]. This keeps the `read_workers` threads from retrying in
lockstep. The three waits add up to 7 s before the random
factor, and to between 3.5 s and 10.5 s with it. That is enough for a TLS reset or a VIP
failover. It is short enough not to hide a real outage. Before every retry
after a *transport* failure (not after a 5xx the API answered),
`_refresh_session()` rebuilds the session via `reauthenticate`. This is
best effort. It drops a poisoned pooled connection. It re-resolves DNS and
the VIP. The tool keeps no list of fallback hosts, by design. Failover
belongs to whatever serves `proxmox.host`.

`build_client()` also applies `proxmox.ticket_refresh_seconds` to the
constructed session. This is best-effort. `proxmoxer` 2.x has no
constructor argument for a password/ticket auth's refresh interval.
`ProxmoxHTTPAuth` hard-codes the interval as a `renew_age = 3600` class
attribute. It checks the age lazily, on whichever request runs after the
interval elapses. `_apply_ticket_refresh_seconds()` therefore reaches into
`api._backend.auth`. These are undocumented `proxmoxer` internals, not its
public interface. The function overrides that instance's `renew_age` after
login. The override is deliberately narrow. It only ever *tightens*
proxmoxer's own schedule. It never replaces its refresh logic. If a future
`proxmoxer` version reshapes this, or the backend is not `https`, or the
auth is API-token (API-token has no ticket at all), the `getattr`/`hasattr`
guards make the function a silent no-op. The P-01 reauthenticate-and-retry
above still catches the case this cannot reach.

**`storage_definitions()` deliberately uses `GET /storage` (the list form),
never the singular `GET /storage/{id}`, even though some callers need only
one storage's config.** The check ran empirically against a real PVE 9.2.11
cluster during development. An
API token granted only `Datastore.Audit` can list every storage's full
config via `GET /storage`. The list includes `saferemove`/`saferemove_throughput`.
The identical data via `GET /storage/{id}` for the same storage returns
`403 Forbidden (Datastore.Allocate)`. The single-item route apparently
backs an edit-UI flow. That flow gates on the ability to change the config,
not merely read it. The list form returns the same per-storage object for
every storage in one call. There is no reason to call the singular form.
Using it would force a Storage DRS token to hold more privilege than the
tool needs. `IMPLEMENTATION_PLAN.md` section 3.5
was corrected to match, once this was found. See that section's note.

**`storage_content()` returned an empty list, not an error, on every
storage, node and content-type filter tried. It kept returning that empty
list until the token also held `Datastore.Allocate` on that storage.** This
was a *silent* false negative, and that is what makes it worth calling
out. `Datastore.Audit` alone gives a clean `200` with `{"data": []}`. That
answer looks exactly like "this storage legitimately has no tracked
content." In fact, the caller cannot see the content. The result is
recorded, not guessed: see `IMPLEMENTATION_PLAN.md` section 3.5's note. It
records the exact before/after on the same live cluster: 0 entries with
Audit only, 37 and 1 entries respectively for two real storages once
`Datastore.Allocate` was added. **The practical consequence: `pve.py`'s
own "keep the token to Audit-only" goal for `storage_definitions()` does
not extend to `storage_content()`.** A Storage DRS token needs
`Datastore.Allocate` (bundled with `Datastore.Audit` in one role) on every
storage it manages. Without it, `topology.py` computes `Uˢᵉˣᵗ` (section
5.1.1) as if every storage were empty of untracked volumes. No error tells
the operator. `docs/manual/00-installation.md` states the exact minimum ACL
grant an operator needs. Do not economize on privilege here. The preference
for a lighter grant did not match reality.

This work surfaced two more facts about Proxmox's ACL model. Both now
appear in the manual's token-setup instructions. **An API token's effective
permission is the *intersection* of its owning user's permissions and
whatever is granted to the token itself**, when privilege separation is on
(the default). Granting a role to only one of the two has no effect. Both
need the role. The confirmed grant was made explicitly at each
`/storage/{id}`, not only at the parent `/storage` path. The manual
instructs that placement. It does not rely on propagation, which was not
cleanly isolated as working or not.

**`node_names()` uses `GET /nodes`, not the `node` fields already visible on
`vm_resources()`/`storage_resources()`.** Section 3.4's PromQL node-scoping
filter (`metrics.build_node_selector()`) is built from this list. The
filter needs *every* cluster node. It does not need only the nodes that
currently host a VM or a shared storage. An idle node would be missing from
both `vm_resources()` and `storage_resources()`. Dropping a real node out
of the filter is the quiet under-count that section 3.4 exists to avoid. A
VM that migrated onto the missing node partway through the window would
show less history than it has. `node_names()` runs once per command
invocation (`cli._resolve_node_selector_for_run()`), not per group.

This module used to have a `cluster_name()` method (`GET /cluster/status`,
`Sys.Audit` at `/`). It backed a middle scoping tier in
`metrics.resolve_node_selector()`. That tier matched a `cluster`-naming
label against this cluster's own name. The method and the tier were removed
together, on operator correction. The premise that this project's
deployments carry such a label "as standard practice" was wrong. The extra
`Sys.Audit`-gated API call had no value. See
`docs/internals/30-metrics.md`'s node-scoping section.

**`vm_config()` returns a key's *pending* value, not the one in effect, once one exists.
The check ran against a real cluster** (`config/drs.yaml`'s dev cluster, VM 102).
Every call `vm_config()` makes sends no `current` parameter. With no `current`
parameter, `GET .../qemu/{vmid}/config` merges in the queued change for a key.
It does not show what PVE is running right now. Only `GET .../qemu/{vmid}/pending`
(`vm_pending()`, section 3.8) exposes both. Each entry's `value` is the real,
in-effect one. A `pending`/`delete` field appears only on a key with something
queued. `topology.py`'s `pending_disk_reasons()` turns this into the section
5.3 (C2) pin (`60-topology.md`'s "The pending-change pin"). `pve.py` itself
does nothing with the distinction beyond exposing both calls.

## `move_disk()`: the one and only bytes/s -> KiB/s conversion

Section 9.2 is explicit: `bwlimit`'s bytes/s-to-KiB/s conversion happens
"at the call site and nowhere else." `PveClient.move_disk()` is that call
site. Every caller in this codebase passes `bwlimit_bytes_per_sec` in the
same unit `migration.bwlimit_bytes_per_sec` already uses. The division by
1024 happens exactly once, inside this method. The method rounds the
result, because the API wants an integer. `format` defaults to `None`. The
method forwards `format` only when a caller explicitly passes one.
`move_disk` without `format=` preserves the source format. That is what
section 3.5 requires by default.
