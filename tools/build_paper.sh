#!/bin/sh
# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Shared pandoc + LuaLaTeX pipeline for every PDF this project ships
# (IMPLEMENTATION_PLAN.pdf, internals.pdf, pve-storage-drs-manual.pdf). One
# implementation (AGENTS.md section 5) so the three documents cannot drift in
# how they are built; see .agents/paper.md and .agents/documentation.md for
# the mechanism and the traps (Unicode fallback, the log checker,
# reproducible builds).
#
# Usage:
#   build_paper.sh <output.pdf> <stamp> <builddir> <tex-basename> \
#                  <title> <subtitle> <source.md>...
#
# The stamp is a `sha256sum` manifest of every source file given (one line
# each), so `sha256sum --check <stamp>` -- what pdf-check/docs-check run --
# verifies all of them at once, in the same format for one file or many.
set -eu

output_pdf=$1; shift
stamp=$1; shift
builddir=$1; shift
texbase=$1; shift
title=$1; shift
subtitle=$1; shift
# Remaining arguments: the source Markdown files, in build order.
sources="$*"

if ! command -v pandoc >/dev/null; then echo "pandoc is not installed"; exit 1; fi
if ! command -v lualatex >/dev/null; then echo "lualatex is not installed (texlive-luatex)"; exit 1; fi

paper_src=docs/paper
mkdir -p "$builddir" "$(dirname "$output_pdf")"

hash=$(cat $sources | sha256sum | cut -d' ' -f1)
if git diff --quiet HEAD -- $sources 2>/dev/null; then
	date=$(git log -1 --format=%cs -- $sources)
	epoch=$(git log -1 --format=%ct -- $sources)
fi
[ -n "${date:-}" ] || date=$(date -u +%F)
[ -n "${epoch:-}" ] || epoch=$(date +%s)

# A single source is named exactly; several (internals/manual, each a
# directory of numbered files) are described by their shared directory, since
# spelling out every filename would overflow the title page.
set -- $sources
if [ "$#" -eq 1 ]; then
	source_desc=$1
else
	source_desc="$(dirname "$1")/*.md"
fi

{
	printf '\\def\\drssourcehash{%s}\n' "$hash"
	printf '\\def\\drssourcename{%s}\n' "$(echo "$source_desc" | sed 's/_/\\_/g')"
	printf '\\def\\drsverifycmd{sha256sum --check %s}\n' "$(echo "$stamp" | sed 's/_/\\_/g')"
} >"$builddir/$texbase-revision.tex"

pandoc $sources \
	--from=markdown \
	--metadata-file="$paper_src/metadata.yaml" \
	-M title="$title" \
	-M subtitle="$subtitle" \
	--lua-filter="$paper_src/filters.lua" \
	--include-in-header="$paper_src/header.tex" \
	--include-in-header="$builddir/$texbase-revision.tex" \
	--toc --toc-depth=4 \
	--highlight-style=tango \
	-M date="$date" \
	--standalone -o "$builddir/$texbase.tex"

(
	cd "$builddir"
	SOURCE_DATE_EPOCH=$epoch FORCE_SOURCE_DATE=1 \
		latexmk -lualatex -interaction=nonstopmode -halt-on-error "$texbase.tex" \
		>"$texbase-latexmk.log" 2>&1
) || {
	echo "lualatex failed; see $builddir/$texbase.log"
	grep -m5 -A3 '^!' "$builddir/$texbase.log" || true
	exit 1
}

python3 tools/check_paper_log.py "$builddir/$texbase.log"
cp "$builddir/$texbase.pdf" "$output_pdf"
sha256sum $sources >"$stamp"
pages=$(pdfinfo "$output_pdf" 2>/dev/null | awk '/^Pages/{print $2}')
echo "pdf: $output_pdf ($pages pages)"
