# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# `make check` is what you run before every commit and what CI runs.
# See AGENTS.md section 2.

VENV    := .venv
PY      := $(VENV)/bin/python
PIP     := $(VENV)/bin/pip
BLACK   := $(VENV)/bin/black
ISORT   := $(VENV)/bin/isort
FLAKE8  := $(VENV)/bin/flake8
MYPY    := $(VENV)/bin/mypy
PYTEST  := $(VENV)/bin/pytest

# `src` does not exist yet at the design stage; wildcard keeps the targets usable
# until it does, and picks it up automatically once it is created.
SOURCES := $(wildcard src) tests tools

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
	@echo "pdf-check  assert the committed PDF matches IMPLEMENTATION_PLAN.md"
	@echo "check      fmt-check + lint + typecheck + test + fixtures + pdf-check"

$(VENV)/bin/activate:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev,solver,forecast]" || $(PIP) install black flake8 flake8-bugbear isort mypy pytest pytest-cov pytest-xdist PyYAML

venv: $(VENV)/bin/activate

install: venv
	$(PIP) install -e ".[dev]"

fmt: venv
	$(ISORT) $(SOURCES)
	$(BLACK) $(SOURCES)

fmt-check: venv
	$(ISORT) --check-only --diff $(SOURCES)
	$(BLACK) --check --diff $(SOURCES)

lint: venv
	$(FLAKE8) $(SOURCES)

typecheck: venv
	$(MYPY) $(SOURCES)

# There are no tests yet: the repository is still at the design stage and
# IMPLEMENTATION_PLAN.md is the deliverable. Skip pytest until the first test
# file exists, so `make check` stays usable; from the first test onwards the
# 85 % floor in pyproject.toml applies with no escape hatch.
test: venv
	@if [ -z "$$(find tests -name 'test_*.py' -print -quit 2>/dev/null)" ]; then \
		echo "NOTE: no test_*.py under tests/ yet (design stage); skipping pytest"; \
	else $(PYTEST); fi

cov: venv
	$(PYTEST) --cov-report=html
	@echo "open htmlcov/index.html"

fixtures:
	python3 tests/fixtures/generate_expected.py --check

check: fmt-check lint typecheck test fixtures pdf-check
	@echo "check: OK"

clean:
	rm -rf .pytest_cache .mypy_cache htmlcov .coverage coverage.xml $(BUILDDIR)
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

# ---------------------------------------------------------------- paper ----
# The PDF rendering of the plan.  It is a build product, but it is committed:
# it is a deliverable people read outside a git checkout, and a stale PDF is
# worse than none.  `make pdf-check` is part of `make check`, so a plan edit
# that is not accompanied by a rebuilt PDF fails before it can be committed.
# The stamp records the SHA-256 of the Markdown the PDF was built from, which
# survives clones and checkouts, unlike mtimes.

PLAN       := IMPLEMENTATION_PLAN.md
PAPER      := docs/IMPLEMENTATION_PLAN.pdf
PAPER_SRC  := docs/paper
PAPER_DEPS := $(PAPER_SRC)/header.tex $(PAPER_SRC)/filters.lua $(PAPER_SRC)/metadata.yaml
STAMP      := docs/IMPLEMENTATION_PLAN.pdf.sha256
BUILDDIR   := docs/.build

.PHONY: pdf pdf-check

pdf: $(PAPER)

$(PAPER): $(PLAN) $(PAPER_DEPS)
	@command -v pandoc  >/dev/null || { echo "pandoc is not installed"; exit 1; }
	@command -v lualatex >/dev/null || { echo "lualatex is not installed (texlive-luatex)"; exit 1; }
	@mkdir -p $(BUILDDIR) $(dir $(PAPER))
	@hash=$$(sha256sum $(PLAN) | cut -d' ' -f1); \
	 if git diff --quiet HEAD -- $(PLAN) 2>/dev/null; then \
	   date=$$(git log -1 --format=%cs -- $(PLAN)); \
	   epoch=$$(git log -1 --format=%ct -- $(PLAN)); \
	 fi; \
	 [ -n "$$date" ] || date=$$(date -u +%F); \
	 [ -n "$$epoch" ] || epoch=$$(date +%s); \
	 printf '\\def\\drssourcehash{%s}\n' "$$hash" > $(BUILDDIR)/revision.tex; \
	 pandoc $(PLAN) \
	   --from=markdown \
	   --metadata-file=$(PAPER_SRC)/metadata.yaml \
	   --lua-filter=$(PAPER_SRC)/filters.lua \
	   --include-in-header=$(PAPER_SRC)/header.tex \
	   --include-in-header=$(BUILDDIR)/revision.tex \
	   --toc --toc-depth=4 \
	   --syntax-highlighting=tango \
	   -M date="$$date" \
	   --standalone -o $(BUILDDIR)/plan.tex; \
	 cd $(BUILDDIR) && SOURCE_DATE_EPOCH=$$epoch FORCE_SOURCE_DATE=1 \
	   latexmk -lualatex -interaction=nonstopmode -halt-on-error plan.tex >latexmk.log 2>&1 \
	   || { echo "lualatex failed; see $(BUILDDIR)/plan.log"; \
	        grep -m5 -A3 '^!' plan.log; exit 1; }
	@python3 tools/check_paper_log.py $(BUILDDIR)/plan.log
	@cp $(BUILDDIR)/plan.pdf $(PAPER)
	@sha256sum $(PLAN) > $(STAMP)
	@echo "pdf: $(PAPER) ($$(pdfinfo $(PAPER) 2>/dev/null | awk '/^Pages/{print $$2}') pages)"

# Fails when the committed PDF was built from a different plan than the one in
# the tree.  Skipped, loudly, where the document toolchain is not installed.
pdf-check:
	@if [ ! -f $(PAPER) ] || [ ! -f $(STAMP) ]; then \
		echo "pdf-check: $(PAPER) or its stamp is missing; run 'make pdf'"; exit 1; \
	fi
	@if ! sha256sum --check --status $(STAMP); then \
		if command -v pandoc >/dev/null && command -v lualatex >/dev/null; then \
			echo "pdf-check: $(PLAN) changed since $(PAPER) was built; run 'make pdf'"; \
			exit 1; \
		else \
			echo "NOTE: $(PAPER) is stale but pandoc/lualatex are not installed;"; \
			echo "      install them and run 'make pdf' before committing the plan."; \
		fi; \
	fi
