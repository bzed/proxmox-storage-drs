#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Bernd Zeimetz <bernd@bzed.de>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fail the paper build on LaTeX problems that silently damage the PDF.

`lualatex` exits 0 for two classes of defect that matter here:

* **Missing characters.** The plan is full of mathematical and box-drawing
  Unicode.  A codepoint no font in the fallback chain covers is dropped
  silently, so a formula loses a symbol and nobody notices.
* **Overfull boxes.** Wide code blocks and tables run into the margin or off
  the page edge instead of wrapping.

Both are warnings in the log.  This script turns them into a non-zero exit so
that ``make pdf`` refuses to install a damaged PDF.

Usage: ``check_paper_log.py <plan.log> [--max-overfull PT]``
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List

# Boxes narrower than this are invisible in practice: TeX reports a hair of
# overhang for many perfectly acceptable lines.
DEFAULT_MAX_OVERFULL_PT = 2.0

MISSING_CHAR_RE = re.compile(r"^Missing character: There is no (.*?) \(U\+([0-9A-Fa-f]+)\)")
OVERFULL_RE = re.compile(r"^Overfull \\[hv]box \(([0-9.]+)pt too (?:wide|high)\)(.*)$")
UNDEFINED_REF_RE = re.compile(r"^LaTeX Warning: (Reference|Citation) `([^']*)' on page")


def _logical_lines(text: str) -> List[str]:
    """Undo the log's hard wrap at 79 columns.

    TeX breaks log lines mid-message, which splits the warnings this script
    looks for.  Joining a line with its successor when the successor is not
    the start of a new message is good enough for the patterns above.
    """
    joined: List[str] = []
    for line in text.splitlines():
        if joined and len(joined[-1]) >= 79:
            joined[-1] += line
        else:
            joined.append(line)
    return joined


def check(log_path: Path, max_overfull_pt: float) -> int:
    text = log_path.read_text(encoding="utf-8", errors="replace")
    lines = _logical_lines(text)

    missing: List[str] = []
    overfull: List[str] = []
    undefined: List[str] = []

    for line in lines:
        match = MISSING_CHAR_RE.match(line)
        if match:
            missing.append(f"U+{match.group(2).upper()} in {match.group(1)}")
            continue
        match = OVERFULL_RE.match(line)
        if match and float(match.group(1)) > max_overfull_pt:
            overfull.append(f"{float(match.group(1)):.1f}pt{match.group(2)}")
            continue
        match = UNDEFINED_REF_RE.match(line)
        if match:
            undefined.append(f"{match.group(1).lower()} {match.group(2)}")

    problems = 0
    for label, found in (
        ("missing characters (no font in the fallback chain covers them)", missing),
        (f"overfull boxes wider than {max_overfull_pt:g}pt", overfull),
        ("undefined references", undefined),
    ):
        if not found:
            continue
        problems += len(found)
        print(f"{log_path}: {len(found)} {label}:", file=sys.stderr)
        for item in sorted(set(found))[:20]:
            print(f"  {item}", file=sys.stderr)
        if len(set(found)) > 20:
            print(f"  ... and {len(set(found)) - 20} more", file=sys.stderr)

    if problems:
        print(
            "paper build rejected; fix the source or docs/paper/header.tex",
            file=sys.stderr,
        )
        return 1
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="the lualatex .log file")
    parser.add_argument(
        "--max-overfull",
        type=float,
        default=DEFAULT_MAX_OVERFULL_PT,
        metavar="PT",
        help=f"tolerated overhang in points (default {DEFAULT_MAX_OVERFULL_PT:g})",
    )
    args = parser.parse_args(argv)
    if not args.log.is_file():
        print(f"{args.log}: no such file", file=sys.stderr)
        return 2
    return check(args.log, args.max_overfull)


if __name__ == "__main__":
    raise SystemExit(main())
