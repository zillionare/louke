#!/usr/bin/env python3
"""
git_diff_quote_resolver.py — NFR-006 implementation

When user pushes changes to spec.md, this tool:
1. Parses `git diff` output for spec.md
2. For each line in the diff that's part of a user edit
3. Finds [open] quotes within ±10 lines
4. Outputs a recommendation for which [open] quotes to mark ✓ resolved

This is the mechanical rule from NFR-006. It's a recommendation engine,
not a mutator — Sage should still review the recommendations before
actually changing the spec.md status markers.

Usage:
    python3 tools/git_diff_quote_resolver.py <spec-path>
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

WINDOW_LINES = 10


def get_diff_line_numbers(spec_path: Path, base_ref: str) -> list[int]:
    try:
        out = subprocess.run(
            ["git", "diff", base_ref, "--", str(spec_path)],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"git diff failed: {e.stderr}", file=sys.stderr)
        return []

    diff_output = out.stdout
    touched_lines: list[int] = []

    # Hunk header: @@ -old_start,old_count +new_start,new_count @@
    hunk_re = re.compile(r"^@@\s+-\d+(?:,\d+)?\s+\+(\d+)(?:,(\d+))?\s+@@")
    current_new_line = 0

    for line in diff_output.splitlines():
        m = hunk_re.match(line)
        if m:
            current_new_line = int(m.group(1))
            continue
        if line.startswith("+") and not line.startswith("+++"):
            touched_lines.append(current_new_line)
            current_new_line += 1
        elif line.startswith("-") and not line.startswith("---"):
            pass
        elif line.startswith(" "):
            current_new_line += 1

    return sorted(set(touched_lines))


def find_open_quotes_near(
    open_lines: list[int],
    touched: list[int],
    window: int = WINDOW_LINES,
) -> list[int]:
    result = set()
    for t in touched:
        for o in open_lines:
            if abs(o - t) <= window:
                result.add(o)
    return sorted(result)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("spec_path", type=Path, help="path to spec.md (post-edit)")
    parser.add_argument(
        "--base-ref",
        default="origin/spec/004-quote-dialogue",
        help="git ref to diff against (default: origin/spec/004-quote-dialogue)",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=WINDOW_LINES,
        help="±N lines window for auto-resolve",
    )
    args = parser.parse_args()

    touched = get_diff_line_numbers(args.spec_path, args.base_ref)
    if not touched:
        print("no changes detected in spec.md vs base ref", file=sys.stderr)
        return 0

    sys.path.insert(0, str(Path(__file__).parent))
    try:
        from quote_parser import parse_spec
    except ImportError:
        print("quote_parser.py not found in tools/", file=sys.stderr)
        return 1
    result = parse_spec(args.spec_path)
    open_lines = [q.line_number for q in result.open_quotes]

    to_resolve = find_open_quotes_near(open_lines, touched, args.window)

    print(f"spec: {args.spec_path}")
    print(f"base ref: {args.base_ref}")
    print(f"touched lines: {touched}")
    print(f"open quotes in spec: {len(open_lines)}")
    print(f"recommended resolve (within ±{args.window} lines): {len(to_resolve)}")
    if to_resolve:
        print("\nRecommendation: mark these [open] quotes as ✓ resolved:")
        for line_no in to_resolve:
            quote = next(q for q in result.open_quotes if q.line_number == line_no)
            body_preview = quote.body[:60]
            print(f"  L{line_no} d{quote.depth} {quote.speaker}: {body_preview}...")

    return 0


if __name__ == "__main__":
    sys.exit(main())