#!/bin/sh
# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Runs pve-storage-drs straight out of this checkout, against the system
# python3 and its Debian-packaged modules -- no .venv involved at all.
# This is exactly the toolchain `make SYSTEM_TOOLS=1 <target>` and CI's own
# "test" job use (python3-requests, python3-proxmoxer, python3-ruamel.yaml,
# python3-jsonschema, python3-pulp + coinor-cbc); see AGENTS.md and
# .agents/packaging.md. `ortools`/CP-SAT has no Debian package
# (docs/internals/91-optimize.md) and is not installed here, so
# `solver.backend: auto` falls back to CBC -- the same solver a real
# Debian install of the package gets, and reproducing that here is the
# point, not a limitation of this script.
#
# Usage: ./run-with-system-python.sh [pve-storage-drs args...]
#   ./run-with-system-python.sh -c config/drs.yaml plan
#   ./run-with-system-python.sh -c config/drs.yaml --mode confirm apply

set -e

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

exec env PYTHONPATH="${script_dir}/src${PYTHONPATH:+:${PYTHONPATH}}" \
    python3 -m proxmox_storage_drs.cli "$@"
