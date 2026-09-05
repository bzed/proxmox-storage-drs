# How a YAML file becomes a validated `Config`

**What does this page answer?** What exactly happens between
`pve-storage-drs -c foo.yaml plan` and a type-checked `Config` object, and
where does each of the section 11.1 validation rules actually live?
Describes `proxmox_storage_drs/config.py` and `config_schema.json`.

## Resolution order

`resolve_config_path()` implements `IMPLEMENTATION_PLAN.md` section 11's
three-source order: `--config` (`cli_path`), then `$PVE_STORAGE_DRS_CONFIG`,
then `config.DEFAULT_CONFIG_PATH` (`/etc/pve/drs.yaml`). It also returns
`was_explicit`, which `load_config()` uses to decide the error message on a
read failure: an explicitly named path that cannot be read is always fatal
with no fallback, per section 11, but the *message* additionally points at
`config/drs.example.yaml` only when the failing path was the unnamed
default — there is nothing useful to suggest when the operator named the
path themselves.

## The two-stage validation

1. **`_validate_schema()`** loads `config_schema.json` via
   `importlib.resources` (it ships as package data — see
   `pyproject.toml`'s `[tool.setuptools.package-data]`) and runs it through
   `jsonschema`. Every object in the schema sets `additionalProperties:
   false`: a typo'd key is caught here as a validation error, not silently
   ignored, which is what keeps section 15.1's knob-to-formula table
   trustworthy (a key with no formula would otherwise go unnoticed).
2. **`_build_config()`** walks the now-schema-valid raw `dict` into the
   frozen dataclasses defined earlier in the module, applying every default
   inline via `.get(key, default)`. These defaults are also what
   `config/drs.example.yaml` documents and what the manual's
   [`../manual/10-configuration.md`](../manual/10-configuration.md)
   describes — there is deliberately no second copy of a default anywhere
   else in the codebase.
3. **`_validate_semantics()`** runs the section 11.1 rules jsonschema cannot
   express — cross-field comparisons, or rules needing a value derived from
   two independently-optional settings. Each rule is a small `_check_*`
   function appending to a shared `errors`/`warnings` list (kept separate
   functions rather than one large one, partly for flake8's `max-complexity`
   and partly because each is independently testable). `errors` become one
   `ConfigError` naming every problem found, not just the first; `warnings`
   are returned to the caller (`ResolvedConfig.warnings`) for `cli.py` to log
   — section 11.1's `saturation_load` check is the one warning-only rule
   today.

Every duration or size field is parsed **once**, at this point, via
`units.parse_duration_seconds`/`parse_size_bytes`, and stored on the
dataclass already in its canonical unit (seconds, bytes) — nothing
downstream re-parses a string.

## Secrets from the environment

`_build_config()` fills `proxmox.auth.password`/`token_secret` from
`PVE_PASSWORD`/`PVE_TOKEN_SECRET` **only when the file's own value is
`null`** — a secret actually written in the file is used as-is, never
silently overridden by an environment variable a deploy script forgot to
unset. This one-directional fallback is what section 11's "keep secrets out
of `/etc/pve`" guidance is for: the file can omit the field entirely and rely
on the environment, or set it explicitly and take responsibility for the
file's own permissions.

## What is deliberately *not* checked here

Two section 11.1 rules need live cluster data this module does not have and
are therefore **not** part of `config.py`:

- storage ids actually existing in the cluster;
- `execution.source_release.timeout` / `gates.cooldown_per_storage` against
  a storage's real `saferemove_throughput`.

Both belong to `pve.py`/`topology.py` (not yet written) and
`pve-storage-drs verify-storages`, once they exist — see
[`../manual/30-safety-and-status.md`](../manual/30-safety-and-status.md) for
current status.

## `ResolvedConfig`: what the caller actually gets

`load_config()` returns a `ResolvedConfig`, not a bare `Config`: the
resolved `path` and the file's `sha256` travel with it, because
`IMPLEMENTATION_PLAN.md` section 11 requires every run to log both — a
plan must always be traceable to the exact file that produced it, even
though the file is never re-read after startup.
