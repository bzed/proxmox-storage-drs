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
| `pulp` | `python3-pulp` + `coinor-cbc` | The MILP path that Debian can actually install |
| `statsmodels` | `python3-statsmodels` | Holt-Winters, optional |
| `ortools` | — | **Not in Debian.** CP-SAT is a pip-only bonus |

`ortools` is the interesting case and the reason rule 3 exists. It is a large C++ extension, so
vendoring it is not on the table, and Debian does not carry it. Rather than let that dictate the
architecture, the design already required a solver-independent path: CBC through PuLP, and below
that a dependency-free heuristic. On a Debian install, **CBC is the solver**, and §5.5 of the plan
should be read that way.

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
`python3-requests` is missing from `Depends`, or that `optimize.py` imports `ortools` at module
level. `debian/tests` installs the package on a system with only its `Depends` and:

- runs `pve-storage-drs --version` and `pve-storage-drs --help` — the entry point resolves and the CLI starts;
- imports every module in the package (`debian/tests/import-all`) — every module is importable with
  the hard dependencies alone, which is what keeps the optional ones optional.

When you add a module that uses an optional dependency, this test is what tells you that you put
the import in the wrong place.

**The autopkgtest deliberately runs without `python3-pulp`.** `Depends: @` installs the package's
`Depends` and not its `Recommends`, which is exactly the configuration the test exists to
exercise: the tool must plan with the heuristic alone. The *build-time* suite is the opposite —
`coinor-cbc` and `python3-pulp` are `Build-Depends` under `<!nocheck>` and are in the GitHub
Actions install list, so `dh_auto_test` and CI do exercise the MILP path, which is the primary
solver on a Debian install. Keep both halves: a solver test that quietly `importorskip`s in every
pipeline would leave the packaged solver path untested, and an autopkgtest that had pulp available
would stop proving the tool runs without it.

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
  targets against the system tools. Coverage goes to Codecov with `codecov/codecov-action`, test
  results with `codecov/test-results-action`; both need `CODECOV_TOKEN` in the repository secrets.
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

