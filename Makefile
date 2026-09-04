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
SOURCES := $(wildcard src) tests

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
	@echo "check      fmt-check + lint + typecheck + test + fixtures  <- run before committing"

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
	python3 tests/fixtures/generate_fc_tier1.py --check

check: fmt-check lint typecheck test fixtures
	@echo "check: OK"

clean:
	rm -rf .pytest_cache .mypy_cache htmlcov .coverage coverage.xml
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
