# How a YAML file becomes a validated `Config`

**What does this page answer?** What happens between
`pve-storage-drs -c foo.yaml plan` and a type-checked `Config` object? Where
does each section 11.1 validation rule live? This page describes
`proxmox_storage_drs/config.py` and `config_schema.json`.

## Resolution order

`resolve_config_path()` implements the three-source order from
`IMPLEMENTATION_PLAN.md` section 11: `--config` (`cli_path`), then
`$PVE_STORAGE_DRS_CONFIG`, then `config.DEFAULT_CONFIG_PATH`
(`/etc/pve/drs.yaml`). The function also returns `was_explicit`.
`load_config()` uses that flag to pick the error message on a read failure.
A named path that cannot be read is always fatal, with no fallback
(section 11). The message points at `config/drs.example.yaml` only when the
failing path was the unnamed default. When the operator named the path,
there is nothing useful to suggest.

## The two-stage validation

1. **`_validate_schema()`** loads `config_schema.json` via
   `importlib.resources`. The file ships as package data -- see
   `pyproject.toml`'s `[tool.setuptools.package-data]`. The function then
   runs the schema through `jsonschema`. Every object in the schema sets
   `additionalProperties: false`. A mistyped key becomes a validation error
   here, not a silent ignore. That keeps section 15.1's knob-to-formula
   table trustworthy. A key with no formula would go unnoticed otherwise.
2. **`_build_config()`** walks the now-schema-valid raw `dict` into the
   frozen dataclasses defined earlier in the module. It applies every
   default inline via `.get(key, default)`. These defaults are also what
   `config/drs.example.yaml` documents and what the manual's
   [`../manual/10-configuration.md`](../manual/10-configuration.md)
   describes. There is deliberately no second copy of a default anywhere
   else in the codebase.
3. **`_validate_semantics()`** runs the section 11.1 rules that
   `jsonschema` cannot express: cross-field comparisons, and rules that need
   a value derived from two independently-optional settings. Each rule is a
   small `_check_*` function. Each function appends to a shared
   `errors`/`warnings` list. The rules stay in separate functions rather
   than one large one, for two reasons: flake8's `max-complexity` limit, and
   the fact that each function is independently testable. `errors` become
   one `ConfigError` that names every problem found, not just the first.
   The function returns the `warnings` to the caller
   (`ResolvedConfig.warnings`) so `cli.py` can log them. The
   payback-horizon and objective-weight advisories are warning-only.

The code parses every duration or size field **once**, at this point, via
`units.parse_duration_seconds`/`parse_size_bytes`. It stores the value on
the dataclass in its canonical unit (seconds, bytes). Nothing downstream
re-parses a string.

## Secrets from the environment

`_build_config()` fills `proxmox.auth.password`/`token_secret` from
`PVE_PASSWORD`/`PVE_TOKEN_SECRET` **only when the file's own value is
`null`**. A secret written in the file is used as-is. No environment
variable can silently override it, not even one a deploy script forgot to
unset. This one-directional fallback serves section 11's "keep secrets out
of `/etc/pve`" guidance. The file can omit the field and rely on the
environment. Or it can set the field and take responsibility for the
file's own permissions.

## What is deliberately *not* checked here

Two section 11.1 rules need live cluster data this module does not have and
are therefore **not** part of `config.py`:

- storage ids actually existing in the cluster;
- `execution.source_release.timeout` / `gates.cooldown_per_storage` against
  a storage's real `saferemove_throughput`.

Both belong to `pve.py`/`topology.py` (which do the live cluster fetch) and
`pve-storage-drs verify-storages` — see
[`../manual/30-safety-and-status.md`](../manual/30-safety-and-status.md) for
current status.

## `ResolvedConfig`: what the caller actually gets

`load_config()` returns a `ResolvedConfig`, not a bare `Config`: the
resolved `path` and the file's `sha256` travel with it, because
`IMPLEMENTATION_PLAN.md` section 11 requires every run to log both — a
plan must always be traceable to the exact file that produced it, even
though the file is never re-read after startup.
