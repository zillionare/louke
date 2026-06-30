#!/usr/bin/env python3
"""AC traceability scanner for specforge projects."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

RE_AC_ANCHOR = re.compile(r'<a\s+id="ac-((?:fr|nfr)-\d{4})"></a>', re.I)
RE_FR_HEADING = re.compile(r"^##\s+((?:FR|NFR)-\d{4})\b", re.I)
RE_AC_HEADING = re.compile(r"^###\s+AC-(\d+)\b", re.I)
RE_AC_COLON = re.compile(r"^AC-(\d+)\s*:", re.I)
RE_AC_REF = re.compile(r"\bAC-((?:FR|NFR)\d{4})-(\d{2})\b", re.I)
TEST_EXTS = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".sh", ".bats", ".java", ".kt", ".rb", ".php", ".c", ".cc", ".cpp", ".h", ".hpp"}


def canonical(fr: str, ac_no: str | int) -> str:
    fr_norm = fr.upper().replace("-", "")
    return f"AC-{fr_norm}-{int(ac_no):02d}"


def parse_acceptance(path: Path) -> dict[str, dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    current_fr: str | None = None
    acs: dict[str, dict[str, Any]] = {}
    pending_anchor: str | None = None
    for idx, line in enumerate(text.splitlines(), start=1):
        m_anchor = RE_AC_ANCHOR.search(line)
        if m_anchor:
            pending_anchor = m_anchor.group(1).upper()
            continue
        m_fr = RE_FR_HEADING.match(line)
        if m_fr:
            current_fr = m_fr.group(1).upper()
            if pending_anchor and pending_anchor != current_fr.lower().upper():
                pass
            continue
        if current_fr:
            m_ac = RE_AC_HEADING.match(line) or RE_AC_COLON.match(line)
            if m_ac:
                ac_id = canonical(current_fr, m_ac.group(1))
                acs[ac_id] = {"fr": current_fr, "line": idx, "source": str(path)}
    return acs


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


def parse_refs(files: list[Path]) -> dict[str, list[dict[str, Any]]]:
    refs: dict[str, list[dict[str, Any]]] = {}
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for idx, line in enumerate(text.splitlines(), start=1):
            for m in RE_AC_REF.finditer(line):
                ac_id = f"AC-{m.group(1).upper()}-{m.group(2)}"
                refs.setdefault(ac_id, []).append({"file": str(path), "line": idx})
    return refs


def load_baseline(path: Path | None) -> set[str]:
    if not path or not path.exists():
        return set()
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--acceptance", required=True)
    ap.add_argument("--tests", nargs="+", required=True)
    ap.add_argument("--legacy-baseline")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    acceptance = Path(args.acceptance)
    if not acceptance.exists():
        print(f"acceptance not found: {acceptance}", file=sys.stderr)
        return 2
    test_paths = [Path(x) for x in args.tests]
    acs = parse_acceptance(acceptance)
    refs = parse_refs(iter_test_files(test_paths))
    baseline = load_baseline(Path(args.legacy_baseline) if args.legacy_baseline else None)

    missing = sorted([ac for ac in acs if ac not in refs and ac not in baseline])
    baseline_missing = sorted([ac for ac in acs if ac not in refs and ac in baseline])
    unknown = sorted([ac for ac in refs if ac not in acs])
    ok = not missing and not unknown
    report = {
        "ok": ok,
        "acceptance": str(acceptance),
        "total_ac": len(acs),
        "referenced_ac": len([ac for ac in acs if ac in refs]),
        "missing": missing,
        "baseline_missing": baseline_missing,
        "unknown": unknown,
        "refs": refs,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"AC traceability: {report['referenced_ac']}/{report['total_ac']} referenced")
        for ac in missing:
            print(f"[missing] {ac}")
        for ac in baseline_missing:
            print(f"[baseline] {ac}")
        for ac in unknown:
            print(f"[unknown] {ac}")
        print("[pass]" if ok else "[fail]")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
