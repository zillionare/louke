#!/usr/bin/env python3
"""AC traceability scanner for specforge projects."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# FR/AC schema: 4-digit IDs per louke/schema.py (FR_DIGITS=4)
# Note: each _tools/*.py has slightly different capture-group needs (some capture
# FR|NFR prefix, some don't), so we keep the \d{4} literal here rather than
# f-string from schema.FR_DIGITS — the literal is self-documenting and grep-friendly.
RE_AC_ANCHOR = re.compile(r'<a\s+id="ac-((?:fr|nfr)-\d{4})"></a>', re.I)
RE_FR_HEADING = re.compile(r"^##\s+((?:FR|NFR)-\d{4})\b", re.I)
RE_AC_HEADING = re.compile(r"^###\s+AC-(\d+)\b", re.I)
RE_AC_COLON = re.compile(r"^AC-(\d+)\s*:", re.I)
RE_AC_REF = re.compile(r"\bAC-((?:FR|NFR)\d{4})-(\d{2})(?:@([A-Za-z0-9._-]+))?", re.I)
RE_AC_CANDIDATE = re.compile(r"\bAC-(?:FR|NFR)[A-Za-z0-9_.@-]+", re.I)
RE_VERSION = re.compile(r"v\d+\.\d+\.\d+$", re.I)
TEST_EXTS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".go",
    ".rs",
    ".sh",
    ".bats",
    ".java",
    ".kt",
    ".rb",
    ".php",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".hpp",
}


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


def iter_test_files(paths: list[Path], exclude: list[Path] | None = None) -> list[Path]:
    exclude_resolved = [e.resolve() for e in (exclude or [])]
    out: list[Path] = []
    for p in paths:
        if p.is_file() and p.suffix in TEST_EXTS:
            if not any(
                p.resolve() == e or e in p.resolve().parents for e in exclude_resolved
            ):
                out.append(p)
        elif p.is_dir():
            for child in p.rglob("*"):
                if (
                    child.is_file()
                    and child.suffix in TEST_EXTS
                    and ".git" not in child.parts
                    and not any(
                        child.resolve() == e or e in child.resolve().parents
                        for e in exclude_resolved
                    )
                ):
                    out.append(child)
    return sorted(out)


def scan_refs(
    files: list[Path],
    current_version: str = "v0.13.1",
    known_acs: set[str] | None = None,
) -> dict[str, Any]:
    """Scan test files and classify AC references by version status.

    The returned ``current`` list contains only references explicitly pinned to
    ``current_version``. Legacy references remain visible as ``legacy`` and are
    deliberately not promoted to current-version coverage.
    """
    version = (
        current_version if current_version.startswith("v") else f"v{current_version}"
    )
    refs: list[dict[str, Any]] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            matches = list(RE_AC_REF.finditer(line))
            consumed: set[int] = set()
            for match in matches:
                consumed.add(match.start())
                ac_id = f"AC-{match.group(1).upper()}-{match.group(2)}"
                suffix = match.group(3)
                if suffix is None:
                    status = "legacy"
                elif not RE_VERSION.fullmatch(suffix):
                    status = "malformed"
                else:
                    status = "current" if suffix == version else "wrong-version"
                refs.append(
                    {
                        "ac": ac_id,
                        "raw": match.group(0),
                        "status": status,
                        "file": str(path),
                        "line": line_no,
                    }
                )
            for candidate in RE_AC_CANDIDATE.finditer(line):
                if any(
                    abs(candidate.start() - start) < len(candidate.group(0))
                    for start in consumed
                ):
                    continue
                refs.append(
                    {
                        "ac": candidate.group(0),
                        "raw": candidate.group(0),
                        "status": "malformed",
                        "file": str(path),
                        "line": line_no,
                    }
                )

    current = sorted({r["ac"] for r in refs if r["status"] == "current"})
    legacy = sorted({r["ac"] for r in refs if r["status"] == "legacy"})
    wrong_version = sorted({r["ac"] for r in refs if r["status"] == "wrong-version"})
    malformed = sorted({r["raw"] for r in refs if r["status"] == "malformed"})
    unknown = sorted(
        {
            r["ac"]
            for r in refs
            if r["status"] == "current"
            and known_acs is not None
            and r["ac"] not in known_acs
        }
    )
    return {
        "refs": refs,
        "current": current,
        "legacy": legacy,
        "wrong_version": wrong_version,
        "malformed": malformed,
        "unknown": unknown,
        "ok": not wrong_version and not malformed and not unknown,
    }


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
                refs.setdefault(ac_id, []).append(
                    {"file": str(path), "line": idx, "raw": m.group(0)}
                )
    return refs


def load_baseline(path: Path | None) -> set[str]:
    if not path or not path.exists():
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--acceptance", required=True)
    ap.add_argument("--tests", nargs="+", required=True)
    ap.add_argument(
        "--exclude", nargs="*", default=[], help="paths to exclude from scan"
    )
    ap.add_argument("--legacy-baseline")
    ap.add_argument("--version", default="v0.13.1")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    acceptance = Path(args.acceptance)
    if not acceptance.exists():
        print(f"acceptance not found: {acceptance}", file=sys.stderr)
        return 2
    test_paths = [Path(x) for x in args.tests]
    exclude_paths = [Path(x) for x in args.exclude]
    acs = parse_acceptance(acceptance)
    files = iter_test_files(test_paths, exclude=exclude_paths)
    refs = parse_refs(files)
    versioned = scan_refs(files, current_version=args.version, known_acs=set(acs))
    baseline = load_baseline(
        Path(args.legacy_baseline) if args.legacy_baseline else None
    )

    missing = sorted([ac for ac in acs if ac not in refs and ac not in baseline])
    baseline_missing = sorted([ac for ac in acs if ac not in refs and ac in baseline])
    unknown = sorted(set(versioned["unknown"]) | {ac for ac in refs if ac not in acs})
    ok = (
        not missing
        and not unknown
        and not versioned["wrong_version"]
        and not versioned["malformed"]
    )
    report = {
        "ok": ok,
        "acceptance": str(acceptance),
        "total_ac": len(acs),
        "referenced_ac": len([ac for ac in acs if ac in refs]),
        "missing": missing,
        "baseline_missing": baseline_missing,
        "unknown": unknown,
        "legacy": versioned["legacy"],
        "wrong_version": versioned["wrong_version"],
        "malformed": versioned["malformed"],
        "refs": refs,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(
            f"AC traceability: {report['referenced_ac']}/{report['total_ac']} referenced"
        )
        for ac in missing:
            print(f"[missing] {ac}")
        for ac in baseline_missing:
            print(f"[baseline] {ac}")
        for ac in unknown:
            print(f"[unknown] {ac}")
        for ac in versioned["legacy"]:
            print(f"[legacy] {ac} (not current-version coverage)")
        for ac in versioned["wrong_version"]:
            print(f"[wrong-version] {ac}")
        for ac in versioned["malformed"]:
            print(f"[malformed] {ac}")
        print("[pass]" if ok else "[fail]")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
