# Packaging, dependencies and CI

[`../AGENTS.md`](../AGENTS.md) section 9 is the normative short version. This file is the how and
the why.

The target is Proxmox VE 9.x, which is Debian **trixie**. Every decision here follows from that.

## Choosing a dependency

```sh
rmadison -s trixie python3-<name>      # authoritative; the local apt cache is not
```

The local machine is usually running something newer than trixie, so `apt-cache policy` answers a
question nobody asked. `rmadison` queries the archive.

What we depend on today, all confirmed present in trixie:

| Python | Debian | Why |
|---|---|---|
| `requests` | `python3-requests` | Prometheus HTTP, and the transport `proxmoxer`'s https backend uses |
| `proxmoxer` | `python3-proxmoxer` | PVE API client (`pve.py`) — chosen over a hand-rolled ticket/CSRF client specifically for its backend abstraction: the same calls work over https today and over ssh (`openssh`/`ssh_paramiko`) later, with no change to `pve.py` |
| `ruamel.yaml` | `python3-ruamel.yaml` | Config, round-trips comments |
| `jsonschema` | `python3-jsonschema` | Config validation |
| `pulp` | `python3-pulp` + `coinor-cbc` (`Depends`) | The default and only MILP path; the heuristic is the fallback when it's genuinely unavailable |
| `statsmodels` | `python3-statsmodels` | Holt-Winters, optional |

(`ortools` once had a row here — a pip-only CP-SAT bonus backend. It and its
backend were removed, REVIEW.md AL-02: not in Debian, not vendorable, and
never installed by hand on PVE hosts, so `solver.backend: auto` resolved to
CBC on every deployment and the second model builder existed only for a
backend production could never run. With it went the one documented
exception to §9.3's "apt, never pip" rule in GitHub Actions.)

If you must add something Debian does not have and it *is* pure Python and small: vendor it under
`src/proxmox_storage_drs/_vendor/`, record the upstream name, version, URL and licence both in
`debian/copyright` and in a comment at the top of the vendored module, and never modify it in place
— carry a patch next to it instead, so the next update is a re-copy rather than an archaeology
project.

## The package

Source format is `3.0 (native)`: upstream and packaging are the same tree, and there is no separate
upstream tarball to track. `debian/gbp.conf` points at `main` for the same reason.

| File | Keep it current when |
|---|---|
| `debian/control` | Any dependency changes — build or runtime, Python or tool |
| `debian/rules` | A build step is added (a document to generate, a file to install) |
| `debian/pve-storage-drs.docs` | A document is added that a user should have on disk |
| `debian/pve-storage-drs.manpages` | A manpage is added |
| `debian/pve-storage-drs.examples` | An example configuration is added |
| `debian/tests/` | A new failure mode is worth catching on the installed package |
| `debian/changelog` | Every release; `gbp dch` generates it, and its version must match `pyproject.toml` |

**A version bump ships with its changelog entry and a git tag, always together** — AGENTS.md §9.2
has the three-part rule and [`git-workflow.md`](git-workflow.md#releases) the `git tag` mechanics.
In practice, this repo's changelog entries so far are hand-authored (one detailed bullet per
REVIEW.md finding or user-visible change), richer than plain `gbp dch` output — keep doing that;
`gbp dch` is a floor, not what an entry should look like when there is real prose to write.

### What the build does and does not rebuild

It **builds the manpage** from `man/pve-storage-drs.1.md`, because that is generated from source and nobody
should be reading a committed roff file.

It **does not rebuild the PDFs** — the plan, `docs/internals.pdf` and `docs/pve-storage-drs-manual.pdf`.
All three are committed, reproducible artefacts whose freshness `make check` and CI already
enforce, and re-running LuaLaTeX in the chroot three times would pull the better part of TeX Live in
to produce byte-identical files. Instead `debian/rules` verifies each one:

```make
sha256sum --check docs/IMPLEMENTATION_PLAN.pdf.sha256
sha256sum --check docs/internals.pdf.sha256
sha256sum --check docs/pve-storage-drs-manual.pdf.sha256
```

written out rather than calling `make docs-check`, because that target degrades to a warning when
the document toolchain is absent — which it is, in the chroot. A check that can silently not run is
not a check. The GitHub Actions `docs` job does the full rebuild in trixie, so the
document pipeline is still exercised on the target distribution — but it does not compare the
result byte-for-byte with the committed PDFs. `make docs` is reproducible for a *fixed* toolchain,
and trixie's pandoc is a different one; what the job proves is that the documents build there at
all, which is a real statement given that the build fails on a missing glyph or an overfull box.

### The autopkgtest is the only real dependency test

The build chroot has the Build-Depends installed. It therefore *cannot* tell you that
`python3-requests` is missing from `Depends`, or that a module imports an optional
dependency at module level. `debian/tests` installs the package on a system with only its `Depends` and:

- runs `pve-storage-drs --version` and `pve-storage-drs --help` — the entry point resolves and the CLI starts;
- imports every module in the package (`debian/tests/import-all`) — every module is importable with
  the hard dependencies alone, which is what keeps the optional ones optional.

When you add a module that uses an optional dependency, this test is what tells you that you put
the import in the wrong place.

**`coinor-cbc` and `python3-pulp` are `Depends`, not `Recommends`.** CBC-through-`pulp` is the
default, always-present MILP path on a Debian install — the tool should not need a separate step
to get a real solver. This means the autopkgtest can no longer prove the heuristic runs with *no*
solver installed at all: `Depends: @` now includes both, so `debian/tests` verifies the tool's
real, default path (and still catches a missing `Depends` or a module that imports an optional
dependency — `statsmodels` — at the top level), not a heuristic-only configuration. That
narrower guarantee — does the code genuinely still work with no MILP library importable — is the
unit test suite's job now (`test_heuristic.py`, and `test_optimize.py`'s mocked
"backend unavailable" branches), not the packaging level's, since a normal Debian install cannot be
configured without a solver any more. `coinor-cbc` and `python3-pulp` are also `Build-Depends`
under `<!nocheck>` and in the GitHub Actions install list, so `dh_auto_test` and CI exercise the
MILP path too — build-time and install-time now agree, rather than deliberately covering opposite
configurations.

## Two identities, and which goes where

`debian/changelog` is signed with the **packaging** identity, `Bernd Zeimetz <bzed@debian.org>` —
the Debian developer address, which is what belongs on Debian packaging work. Everything else in
the tree — the SPDX headers, `debian/copyright`'s `Upstream-Contact`, `pyproject.toml`'s authors,
the manpage's `AUTHOR` — carries the **upstream** identity, `Bernd Zeimetz <bernd@bzed.de>`. The
two addresses are the same person wearing different hats; neither is a typo for the other, and a
tidy-up that unified them would be wrong in one direction or the other.

## CI

**GitHub Actions**, in `debian:trixie` containers:

- `tests.yml` — the toolchain comes from apt, not pip. `make SYSTEM_TOOLS=1 …` runs the ordinary
  targets against the system tools; `./run-with-system-python.sh` does the same for running the
  CLI itself (no venv, straight out of the checkout) rather than a make target. Coverage goes to
  Codecov with `codecov/codecov-action`, test results with `codecov/test-results-action`; both need
  `CODECOV_TOKEN` in the repository secrets.
- `tests.yml`'s `docs` job builds every document against **trixie's pandoc**, which is older than
  the one you are probably developing against. That job is the reason `make pdf` uses
  `--highlight-style` rather than the newer `--syntax-highlighting`: the option that works on both.
- `debian-package.yml` — `mk-build-deps` from `debian/control`, `dpkg-buildpackage`, lintian, then
  purge the build dependencies, install the `.deb` and run the autopkgtests against it.

**GitLab CI**, `debian/.gitlab-ci.yml`, Debian's Salsa pipeline: sbuild in an unshare chroot, then
lintian, piuparts, reprotest and autopkgtest. Set the project's CI configuration path to
`debian/.gitlab-ci.yml`.

The Salsa build runs **without network**, which in sbuild's unshare mode is simply the default
(`--no-enable-network`). That is the point: it proves the package builds from trixie alone. If a
build genuinely needs to fetch something, vendor it first; `SALSA_CI_SBUILD_ARGS: '--enable-network'`
is the documented fallback and is a deliberate, reviewable edit.

