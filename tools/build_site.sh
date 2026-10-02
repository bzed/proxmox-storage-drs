#!/bin/sh
# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Assemble the MkDocs source tree for the GitHub Pages site and build it.
#
# The site renders the repository's documentation -- IMPLEMENTATION_PLAN.md,
# docs/manual/, docs/internals/ -- from the same Markdown the PDF pipeline
# reads, so the two can never disagree. MkDocs insists on a single docs_dir,
# so this script copies the sources into a throwaway tree (docs/.site,
# gitignored) with the two trees as siblings, which is what the cross-links
# between them already assume: docs/internals/*.md links to
# ../manual/<page>.md, and within a tree the links are bare filenames.
#
# Nothing site-related is committed except this pipeline itself (AGENTS.md
# section 8): the site is built in CI (.github/workflows/docs-pages.yml) and
# deployed to GitHub Pages. mkdocs.yml sets strict: true, so a page missing
# from the nav or a broken link fails the build -- the site's equivalent of
# make docs-check.
#
# Requires mkdocs-material; pip install --requirement docs/site/requirements.txt
set -eu

site_src=docs/.site
site_out=docs/.site-html

if ! command -v mkdocs >/dev/null; then
	echo "mkdocs is not installed (pip install --requirement docs/site/requirements.txt)"
	exit 1
fi

rm -rf "$site_src" "$site_out"
mkdir -p "$site_src"

cp docs/site/index.md "$site_src/index.md"
cp docs/site/extra.css "$site_src/extra.css"
cp docs/logo.svg "$site_src/logo.svg"
cp IMPLEMENTATION_PLAN.md "$site_src/IMPLEMENTATION_PLAN.md"
cp -r docs/manual "$site_src/manual"
cp -r docs/internals "$site_src/internals"

# The two links in the documentation that point outside the rendered trees,
# into the repository -- GitHub renders those paths, the site cannot. Point
# them at the blob on main instead. The list is exhaustive because strict
# mode fails the build on any *other* such link: one of these seds not
# matching anymore (the source link was edited away) also leaves a broken
# link for strict mode to catch, so this cannot silently rot.
sed -i 's#](\.\./\.\./src/#](https://github.com/bzed/proxmox-storage-drs/blob/main/src/#g' \
	"$site_src/internals/97-collect-and-replay.md"
sed -i 's#](config/#](https://github.com/bzed/proxmox-storage-drs/blob/main/config/#g' \
	"$site_src/IMPLEMENTATION_PLAN.md"

mkdocs build
pages=$(find "$site_out" -name '*.html' | wc -l)
echo "site: $site_out ($pages pages)"
