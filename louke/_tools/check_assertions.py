#!/usr/bin/env python3
"""Assertion hygiene scanner for specforge projects."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

TEST_EXTS = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".sh", ".bats", ".java", ".kt", ".rb"}
RE_AC_REF = re.compile(r"\bAC-(?:FR|NFR)\d{4}-\d{2}\b", re.I)
RE_ISSUE_OR_URL = re.compile(r"(https?://|#[0-9]+|issue\s*[:#]\s*[0-9]+)", re.I)

PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("FAKE-001", re.compile(r"\bassert\s+(True\b|1\b(?!\s*[+\-*/]))"), "assert True/1 has no value"),
    ("FAKE-002", re.compile(r"\bassert\s+.+\s+is\s+not\s+None\b"), "weak non-null assertion without AC"),
    ("FAKE-003", re.compile(r"except\b[^:\n]*:\s*(?:#.*)?$\n\s*pass\b", re.M), "try/except/pass swallows exceptions"),
    ("FAKE-004", re.compile(r"except\s+Exception\b[^:\n]*:\s*(?:#.*)?$\n\s*pass\b", re.M), "except Exception/pass swallows exceptions"),
    ("FAKE-005", re.compile(r"pytest\.skip\("), "pytest.skip without issue/AC/URL"),
    ("FAKE-006", re.compile(r"pytest\.mark\.(skip|xfail)|@pytest\.mark\.(skip|xfail)"), "skip/xfail without issue/AC/URL"),
    ("FAKE-008", re.compile(r"\b(TODO|NotImplemented)\b"), "unfinished test marker without issue/URL"),
]


def iter_test_files(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        if p.is_file() and p.suffix in TEST_EXTS:
            out.append(p)
        elif p.is_dir():
            for child in p.rglob("*"):
                if child.is_file() and child.suffix in TEST_EXTS and ".git" not in child.parts:
                    out.append(child)
    return sorted(out)


def has_context_exception(text: str, start: int, end: int, require_ac: bool = False) -> bool:
    context = text[max(0, start - 160) : min(len(text), end + 160)]
    if require_ac:
        return bool(RE_AC_REF.search(context))
    return bool(RE_AC_REF.search(context) or RE_ISSUE_OR_URL.search(context))


def scan_file(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    violations: list[dict[str, Any]] = []
    for code, pattern, msg in PATTERNS:
        for m in pattern.finditer(text):
            if code == "FAKE-002" and has_context_exception(text, m.start(), m.end(), require_ac=True):
                continue
            if code in {"FAKE-005", "FAKE-006", "FAKE-008"} and has_context_exception(text, m.start(), m.end()):
                continue
            line = text.count("\n", 0, m.start()) + 1
            violations.append({"code": code, "file": str(path), "line": line, "message": msg})
    if re.search(r"def\s+test_\w+\([^)]*\):\s*(?:#.*)?\n\s*(pass|return\b)", text):
        m = re.search(r"def\s+test_\w+", text)
        line = text.count("\n", 0, m.start()) + 1 if m else 1
        violations.append({"code": "FAKE-007", "file": str(path), "line": line, "message": "empty test body"})
    return violations


def load_baseline(path: Path | None) -> set[str]:
    if not path or not path.exists():
        return set()
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")}


def violation_key(v: dict[str, Any]) -> str:
    return f"{v['code']} {v['file']}:{v['line']}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tests", nargs="+", required=True)
    ap.add_argument("--legacy-baseline")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    baseline = load_baseline(Path(args.legacy_baseline) if args.legacy_baseline else None)
    violations: list[dict[str, Any]] = []
    baseline_hits: list[dict[str, Any]] = []
    for path in iter_test_files([Path(x) for x in args.tests]):
        for v in scan_file(path):
            if violation_key(v) in baseline:
                baseline_hits.append(v)
            else:
                violations.append(v)
    report = {"ok": not violations, "violations": violations, "baseline": baseline_hits}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for v in violations:
            print(f"[{v['code']}] {v['file']}:{v['line']} {v['message']}")
        for v in baseline_hits:
            print(f"[baseline {v['code']}] {v['file']}:{v['line']} {v['message']}")
        print("[pass]" if not violations else "[fail]")
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
