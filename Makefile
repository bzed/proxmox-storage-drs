# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# `make check` is what you run before every commit and what CI runs.
# See AGENTS.md section 2.

# SYSTEM_TOOLS=1 runs everything with the tools already on PATH instead of a
# virtualenv. That is how CI and the Debian build run: the point of this
# project's dependency policy is that Debian's packaged modules are enough, and
# a `pip install` in CI would hide the day the policy stopped being true.
ifeq ($(SYSTEM_TOOLS),1)
VENV    :=
VENVDEP :=
PY      := python3
PIP     := :
BLACK   := black
ISORT   := isort
FLAKE8  := flake8
MYPY    := mypy
PYTEST  := python3 -m pytest
else
VENV    := .venv
VENVDEP := venv
PY      := $(VENV)/bin/python
PIP     := $(VENV)/bin/pip
BLACK   := $(VENV)/bin/black
ISORT   := $(VENV)/bin/isort
FLAKE8  := $(VENV)/bin/flake8
MYPY    := $(VENV)/bin/mypy
PYTEST  := $(VENV)/bin/pytest
endif

SOURCES := src tests tools

.PHONY: help venv install fmt fmt-check lint typecheck test cov fixtures check clean

help:
	@echo "venv       create $(VENV) and install dev dependencies"
	@echo "install    editable install of the package into $(VENV)"
	@echo "fmt        isort + black (rewrites files)"
	@echo "fmt-check  isort + black in --check mode"
	@echo "lint       flake8"
	@echo "typecheck  mypy"
	@echo "test       pytest with coverage, fails below 85%"
	@echo "cov        pytest with an HTML coverage report in htmlcov/"
	@echo "fixtures   assert tests/fixtures/*.expected.json are current"
	@echo "pdf        render IMPLEMENTATION_PLAN.md to docs/IMPLEMENTATION_PLAN.pdf"
	@echo "internals  render docs/internals/*.md to docs/internals.pdf"
	@echo "manual     render docs/manual/*.md to docs/pve-storage-drs-manual.pdf"
	@echo "man        render man/pve-storage-drs.1.md to man/pve-storage-drs.1"
	@echo "docs       pdf + internals + manual + man"
	@echo "docs-check assert every generated document matches its Markdown"
	@echo "deb        build the Debian package with dpkg-buildpackage"
	@echo "check      fmt-check + lint + typecheck + test + fixtures + pdf-check"

$(VENV)/bin/activate:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev,solver,forecast]" || $(PIP) install black flake8 flake8-bugbear isort mypy pytest pytest-cov pytest-xdist PyYAML

venv: $(VENV)/bin/activate

install: $(VENVDEP)
	$(PIP) install -e ".[dev]"

fmt: $(VENVDEP)
	$(ISORT) $(SOURCES)
	$(BLACK) $(SOURCES)

fmt-check: $(VENVDEP)
	$(ISORT) --check-only --diff $(SOURCES)
	$(BLACK) --check --diff $(SOURCES)

lint: $(VENVDEP)
	$(FLAKE8) $(SOURCES)

typecheck: $(VENVDEP)
	$(MYPY) $(SOURCES)

test: $(VENVDEP)
	$(PYTEST)

cov: $(VENVDEP)
	$(PYTEST) --cov-report=html
	@echo "open htmlcov/index.html"

fixtures:
	python3 tests/fixtures/generate_expected.py --check

check: fmt-check lint typecheck test fixtures docs-check
	@echo "check: OK"

clean:
	rm -rf .pytest_cache .mypy_cache htmlcov .coverage coverage.xml $(BUILDDIR)
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

# ---------------------------------------------------------------- paper ----
# The PDF rendering of the plan, the internals and the operator manual. Each
# is a build product but is committed: all three are deliverables people read
# outside a git checkout, and a stale PDF is worse than none. `make docs-check`
# is part of `make check`, so a source edit not accompanied by a rebuild fails
# before it can be committed. tools/build_paper.sh is the single
# implementation of the pandoc+LuaLaTeX pipeline (AGENTS.md section 5); this
# file only declares, per document, its sources, title and subtitle. Each
# stamp is a `sha256sum` manifest of its sources, which survives clones and
# checkouts unlike mtimes, and works identically for one file (the plan) or
# many (internals, manual).

PLAN          := IMPLEMENTATION_PLAN.md
PAPER         := docs/IMPLEMENTATION_PLAN.pdf
INTERNALS_SRC := $(sort $(wildcard docs/internals/*.md))
INTERNALS_PDF := docs/internals.pdf
MANUAL_SRC    := $(sort $(wildcard docs/manual/*.md))
MANUAL_PDF    := docs/pve-storage-drs-manual.pdf

PAPER_SRC  := docs/paper
PAPER_DEPS := $(PAPER_SRC)/header.tex $(PAPER_SRC)/filters.lua $(PAPER_SRC)/metadata.yaml \
              Makefile tools/check_paper_log.py tools/build_paper.sh
BUILDDIR   := docs/.build

.PHONY: pdf pdf-check internals internals-check manual manual-check man man-check docs docs-check deb

empty :=
comma := ,

# $(call PAPER_DOC,<make-target-stem>,<output.pdf>,<sources>,<title>,<subtitle>)
# defines <stem>, <stem>-check and the .pdf rule itself. A comma in <subtitle>
# must be written as $(comma) since `call` splits its own arguments on commas.
define PAPER_DOC
$(2): $(3) $(PAPER_DEPS)
	tools/build_paper.sh $(2) $(2).sha256 $(BUILDDIR) $(1) "$(4)" "$(5)" $(3)

.PHONY: $(1) $(1)-check
$(1): $(2)

$(1)-check:
	@if [ ! -f $(2) ] || [ ! -f $(2).sha256 ]; then \
		echo "$(1)-check: $(2) or its stamp is missing; run 'make $(1)'"; exit 1; \
	fi
	@if ! sha256sum --check --status $(2).sha256; then \
		if command -v pandoc >/dev/null && command -v lualatex >/dev/null; then \
			echo "$(1)-check: source changed since $(2) was built; run 'make $(1)'"; \
			exit 1; \
		else \
			echo "NOTE: $(2) is stale but pandoc/lualatex are not installed;"; \
			echo "      install them and run 'make $(1)' before committing."; \
		fi; \
	fi
endef

$(eval $(call PAPER_DOC,pdf,$(PAPER),$(PLAN),$(strip Proxmox Storage DRS),$(strip \
  Balancing disk I/O across shared storages on Proxmox VE 9.2)))
$(eval $(call PAPER_DOC,internals,$(INTERNALS_PDF),$(INTERNALS_SRC),$(strip \
  Proxmox Storage DRS -- Internals),$(strip \
  How the tool works$(comma) for whoever changes it)))
$(eval $(call PAPER_DOC,manual,$(MANUAL_PDF),$(MANUAL_SRC),$(strip \
  Proxmox Storage DRS -- Operator Manual),$(strip \
  Installing$(comma) configuring and running it safely)))

MANPAGE  := man/pve-storage-drs.1
MAN_SRC  := man/pve-storage-drs.1.md
VERSION  := $(shell sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml | head -1)

docs: pdf internals manual man
docs-check: pdf-check internals-check manual-check man-check

# Unlike the PDF the manpage is not committed: nobody reads roff outside a
# checkout, and debian/rules builds it during the package build.
man: $(MANPAGE)

$(MANPAGE): $(MAN_SRC) pyproject.toml
	@command -v pandoc >/dev/null || { echo "pandoc is not installed"; exit 1; }
	@date=$$(git log -1 --format=%cs -- $(MAN_SRC) 2>/dev/null); \
	 [ -n "$$date" ] || date=$$(date -u +%F); \
	 sed -e 's/@VERSION@/$(VERSION)/' -e "s/@DATE@/$$date/" $(MAN_SRC) \
	   | pandoc --standalone --from=markdown --to=man --output=$(MANPAGE)
	@echo "man: $(MANPAGE) (version $(VERSION))"

man-check:
	@if command -v pandoc >/dev/null; then \
		$(MAKE) --no-print-directory $(MANPAGE) >/dev/null; \
		grep -q '^\.TH ' $(MANPAGE) \
		  || { echo "man-check: $(MANPAGE) has no .TH header"; exit 1; }; \
		if grep -q '@VERSION@\|@DATE@' $(MANPAGE); then \
			echo "man-check: a placeholder survived into $(MANPAGE)"; exit 1; \
		fi; \
		if command -v groff >/dev/null; then \
			groff -man -Tutf8 -ww -z $(MANPAGE) || exit 1; \
		fi; \
	else \
		echo "NOTE: pandoc is not installed; not checking $(MANPAGE)"; \
	fi

# Builds in place, not in a chroot: a quick local check, not what CI does.
deb:
	dpkg-buildpackage -us -uc -b
