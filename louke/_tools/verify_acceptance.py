#!/usr/bin/env python3
"""
verify_acceptance.py — validate whether the acceptance.md produced by Sage is compliant

This is the input validation tool for Lex stage one. Lex runs this before reading spec.md
to confirm that Sage's work (especially the acceptance split) is well-formed, before doing semantic review.

Design goals:
- Zero LLM tokens: pure structural checks
- Zero extra dependencies: Python stdlib only
- Offline-testable: supports --offline + fixture files, bats can feed samples directly

Checks (L1-L5):
  L1 File exists:        .louke/project/specs/{id}/acceptance.md exists
  L2 FR/NFR section exists:   every FR/NFR in spec.md has a matching ## section in acceptance.md
  L3 AC numbering sequential:     within each FR/NFR section, ### AC-N starts at 1 and increments by 1
  L4 AC content non-empty:     each ### AC-N has at least 1 bullet, with concrete assertable content
  L5 Reverse coverage:        every ## FR/NFR section in acceptance.md corresponds to an FR/NFR in spec.md
                      (prevents "ghost FRs" in acceptance that do not exist in spec)

Usage:
  python louke/_tools/verify_acceptance.py --spec v0.1-001-louke
  python louke/_tools/verify_acceptance.py --offline \\
      --spec-file .louke/project/specs/v0.1-001-louke/spec.md \\
      --acceptance-file .louke/project/specs/v0.1-001-louke/acceptance.md
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------- Regex definitions ----------

# FR/NFR sections in spec.md: ### FR-010 {title} or ### NFR-020 {title}
# (FR uses a level-3 heading; level 2 is reserved for semantic groupings like "Functional / Non-functional requirements")
RE_FR_SECTION = re.compile(r"^###\s+(FR|NFR)-(\d{4})\b", re.MULTILINE)

# FR/NFR sections in acceptance.md: ## FR-010 {title}
# (acceptance.md has no semantic grouping, so FR is directly level 2)
RE_ACC_FR_SECTION = re.compile(r"^##\s+(FR|NFR)-(\d{4})\b", re.MULTILINE)

# AC sections in acceptance.md: ### AC-1 or ### AC-2
RE_AC_SECTION = re.compile(r"^###\s+AC-(\d+)\s*$", re.MULTILINE)

# Bullet: optional leading whitespace + (- or *) + at least one whitespace + capture the non-empty content
RE_BULLET = re.compile(r"^[\s]*[-*]\s+(.+)$")

# Placeholders that must not be used as AC content (should be replaced with real conditions)
# Note: {repo}, {version}, {id}, {date}, {browser} etc. single-brace tokens are valid command template references,
# not placeholders. Only {{...}} (Jinja style) is treated as an unreplaced placeholder.
PLACEHOLDER_PATTERNS = [
    re.compile(r"\{\{.*?\}\}"),  # {{ variable }} — Jinja-style unreplaced placeholder
]

# ---------- Data classes ----------


@dataclass
class AccResult:
    code: str  # L1/L2/...
    name: str
    passed: bool
    message: str = ""
    failures: list[str] = field(default_factory=list)


@dataclass
class SpecFRSpec:
    fr_id: str  # FR-010
    nfr: bool  # True if NFR
    number: int  # 10
    title: str = ""


# ---------- Utility functions ----------


def _project_info_value(label: str) -> str:
    """Read a nested-key string value from project.toml (after fix-002)."""
    path = Path(".louke/project/project.toml")
    if not path.exists():
        return ""
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            return ""
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        return ""
    snake = label.lower().replace(" ", "_").replace("-", "_")
    for section in ("project", "meta"):
        if snake in data.get(section, {}):
            return str(data[section][snake])
    if snake in data:
        return str(data[snake])
    return ""


def gh_api_read(path: str, repo: str = "", branch: str = "") -> str:
    """Read a file via gh api. Returns None on failure (FR-0540 release branch + repo path fix)."""
    repo = repo or _project_info_value("Repo").replace("github.com/", "")
    pi_branch = _project_info_value("Release Branch")
    if not branch:
        branch = pi_branch or "main"
        if not pi_branch:
            print(
                "warn: project.toml missing Release Branch; fallback to main",
                file=sys.stderr,
            )
    endpoint = (
        f"repos/{repo}/contents/{path}?ref={branch}"
        if repo
        else f"contents/{path}?ref={branch}"
    )
    try:
        out = subprocess.check_output(
            ["gh", "api", endpoint],
            stderr=subprocess.STDOUT,
        )
        import base64
        import json

        data = json.loads(out)
        return base64.b64decode(data["content"]).decode("utf-8")
    except Exception as e:  # noqa: BLE001
        print(f"warn: gh api failed for {path}: {e}", file=sys.stderr)
        return None


def fetch_spec_text(spec_id: str, repo: str = "", branch: str = "") -> str | None:
    """Read .louke/project/specs/{spec_id}/spec.md"""
    return gh_api_read(
        f".louke/project/specs/{spec_id}/spec.md", repo=repo, branch=branch
    )


def fetch_acceptance_text(spec_id: str, repo: str = "", branch: str = "") -> str | None:
    """Read .louke/project/specs/{spec_id}/acceptance.md"""
    return gh_api_read(
        f".louke/project/specs/{spec_id}/acceptance.md", repo=repo, branch=branch
    )


def parse_fr_sections(text: str) -> list[SpecFRSpec]:
    """Extract all FR/NFR sections from spec.md text."""
    result = []
    for m in RE_FR_SECTION.finditer(text):
        is_nfr = m.group(1) == "NFR"
        result.append(
            SpecFRSpec(
                fr_id=f"{m.group(1)}-{m.group(2)}",
                nfr=is_nfr,
                number=int(m.group(2)),
            )
        )
    return result


def parse_acc_sections(text: str) -> dict[str, list[int]]:
    """Extract all FR/NFR sections + their AC-N lists from acceptance.md text.

    Returns: { "FR-010": [1, 2, 3], "NFR-020": [1], ... }
    """
    sections: dict[str, list[int]] = {}
    current_fr: str | None = None
    current_acs: list[int] = []

    for line in text.splitlines():
        # Match ## FR-XXX or ## NFR-XXX section header
        m = RE_ACC_FR_SECTION.match(line)
        if m:
            # Entering a new section: commit the previous one
            if current_fr is not None:
                sections[current_fr] = current_acs
            current_fr = f"{m.group(1)}-{m.group(2)}"
            current_acs = []
            continue

        # Match ### AC-N
        am = RE_AC_SECTION.match(line)
        if am and current_fr is not None:
            current_acs.append(int(am.group(1)))

    # Final commit
    if current_fr is not None:
        sections[current_fr] = current_acs

    return sections


def extract_ac_body(text: str, fr_id: str, ac_num: int) -> list[str]:
    """Extract the bullet list after the ### AC-N header under ## FR-XXX in acceptance.md.

    Returns: a list of bullet text (with the leading - removed).
    """
    lines = text.splitlines()
    in_section = False
    in_target_ac = False
    bullets: list[str] = []

    for line in lines:
        # Enter the target FR/NFR section
        m = RE_ACC_FR_SECTION.match(line)
        if m and f"{m.group(1)}-{m.group(2)}" == fr_id:
            in_section = True
            continue
        if m and in_section:
            # Entering the next section, end
            break

        if not in_section:
            continue

        # Check whether we entered the target AC section
        am = RE_AC_SECTION.match(line)
        if am:
            if int(am.group(1)) == ac_num:
                in_target_ac = True
                continue
            else:
                in_target_ac = False
                continue

        if in_target_ac:
            m = RE_BULLET.match(line)
            if m:
                bullets.append(m.group(1).strip())

    return bullets


# ---------- L1-L5 validation ----------


def check_L1_exists(acceptance_text: str | None) -> AccResult:
    r = AccResult(code="L1", name="File exists", passed=False)
    if acceptance_text is None:
        r.message = "acceptance.md missing"
        r.failures.append("acceptance.md not found")
        return r
    if acceptance_text.strip() == "":
        r.message = "acceptance.md is empty"
        r.failures.append("acceptance.md content is empty")
        return r
    r.passed = True
    r.message = f"acceptance.md read ({len(acceptance_text)} chars)"
    return r


def check_L2_fr_sections(
    spec_frs: list[SpecFRSpec], acc_sections: dict[str, list[int]]
) -> AccResult:
    """Every FR/NFR in spec.md has a same-named section in acceptance.md."""
    r = AccResult(code="L2", name="FR/NFR section exists", passed=False)
    spec_ids = {f.fr_id for f in spec_frs}
    acc_ids = set(acc_sections.keys())
    missing = spec_ids - acc_ids
    if missing:
        r.failures.append(
            f"acceptance.md is missing {len(missing)} FR/NFR sections: {sorted(missing)}"
        )
        return r
    r.passed = True
    r.message = f"all {len(spec_ids)} FR/NFR in spec.md have same-named sections in acceptance.md"
    return r


def check_L3_ac_sequential(acc_sections: dict[str, list[int]]) -> AccResult:
    """Within each FR/NFR section, AC-N starts at 1 and increments by 1."""
    r = AccResult(code="L3", name="AC numbering sequential", passed=False)
    bad: list[str] = []
    for fr_id, acs in acc_sections.items():
        if not acs:
            bad.append(f"{fr_id}: no AC at all")
            continue
        expected = list(range(1, len(acs) + 1))
        if acs != expected:
            bad.append(f"{fr_id}: AC numbers {acs} (expected {expected})")
    if bad:
        r.failures.append("AC numbering not sequential: " + "; ".join(bad))
        return r
    r.passed = True
    r.message = f"AC numbering for all {len(acc_sections)} FR/NFR sections starts at 1 and is sequential"
    return r


def check_L4_ac_content(
    acceptance_text: str, acc_sections: dict[str, list[int]]
) -> AccResult:
    """Each AC has at least 1 bullet, and the content is not a placeholder."""
    r = AccResult(code="L4", name="AC content non-empty", passed=False)
    bad: list[str] = []
    for fr_id, acs in acc_sections.items():
        for ac_num in acs:
            bullets = extract_ac_body(acceptance_text, fr_id, ac_num)
            if not bullets:
                bad.append(f"{fr_id} / AC-{ac_num}: missing bullet content")
                continue
            # Check whether all bullets are placeholders
            for b in bullets:
                if any(p.search(b) for p in PLACEHOLDER_PATTERNS):
                    bad.append(
                        f"{fr_id} / AC-{ac_num}: bullet '{b[:40]}...' is a placeholder, should be replaced with real conditions"
                    )
                    break
    if bad:
        r.failures.append("AC content invalid: " + "; ".join(bad))
        return r
    r.passed = True
    total_ac = sum(len(acs) for acs in acc_sections.values())
    r.message = f"all {total_ac} ACs have bullet content, no placeholder residue"
    return r


def check_L5_reverse_cover(
    spec_frs: list[SpecFRSpec], acc_sections: dict[str, list[int]]
) -> AccResult:
    """Every ## FR/NFR section in acceptance.md corresponds to an FR/NFR in spec.md (prevents ghost FRs)."""
    r = AccResult(code="L5", name="Reverse coverage", passed=False)
    spec_ids = {f.fr_id for f in spec_frs}
    acc_ids = set(acc_sections.keys())
    ghost = acc_ids - spec_ids
    if ghost:
        r.failures.append(
            f"acceptance.md references FR/NFR not present in spec.md: {sorted(ghost)}"
        )
        return r
    r.passed = True
    r.message = f"all {len(acc_ids)} FR/NFR in acceptance.md exist in spec.md"
    return r


# ---------- Main flow ----------


def run_checks(
    spec_text: str,
    acceptance_text: str | None,
) -> list[AccResult]:
    spec_frs = parse_fr_sections(spec_text)
    norm_acc = acceptance_text or ""
    acc_sections = parse_acc_sections(norm_acc)

    return [
        check_L1_exists(acceptance_text),
        check_L2_fr_sections(spec_frs, acc_sections),
        check_L3_ac_sequential(acc_sections),
        check_L4_ac_content(norm_acc, acc_sections),
        check_L5_reverse_cover(spec_frs, acc_sections),
    ]


def report(results: list[AccResult]) -> int:
    failed = [r for r in results if not r.passed]
    passed = [r for r in results if r.passed]

    for r in results:
        status = "[PASS]" if r.passed else "[REJECT]"
        print(f"{r.code} {status} {r.name}: {r.message}")
        for f in r.failures:
            print(f"   - {f}")

    print()
    if failed:
        print(f"[REJECT] {len(failed)} checks failed, {len(passed)} checks passed")
        print("Sage must fix acceptance.md before asking Lex to re-review")
        return 1
    print(f"[PASS] all {len(passed)} checks passed")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="validate whether acceptance.md is compliant (Lex stage one)"
    )
    p.add_argument("--spec", required=True, help="spec-id, e.g. v0.1-001-louke")
    p.add_argument(
        "--repo",
        default="",
        help="owner/repo, e.g. my-org/my-project (the project running louke, not the louke framework itself)",
    )
    p.add_argument(
        "--branch",
        default="",
        help="branch where the spec lives; defaults to project-info Release Branch",
    )
    p.add_argument(
        "--offline",
        action="store_true",
        help="offline mode: use --spec-file/--acceptance-file directly",
    )
    p.add_argument("--spec-file", help="offline mode: path to spec.md")
    p.add_argument("--acceptance-file", help="offline mode: path to acceptance.md")
    args = p.parse_args()

    if args.offline:
        if not args.spec_file:
            print("--offline requires --spec-file", file=sys.stderr)
            return 1
        spec_path = Path(args.spec_file)
        if not spec_path.exists():
            print(f"not found: {spec_path}", file=sys.stderr)
            return 1
        spec_text = spec_path.read_text(encoding="utf-8")
        # A missing acceptance file is not a hard error: let the L1 check report uniformly
        if args.acceptance_file:
            acc_path = Path(args.acceptance_file)
            acceptance_text = (
                acc_path.read_text(encoding="utf-8") if acc_path.exists() else None
            )
        else:
            acceptance_text = None
    else:
        if not args.spec:
            print("non-offline mode requires --spec SPEC_ID", file=sys.stderr)
            return 1
        spec_text = fetch_spec_text(args.spec, repo=args.repo, branch=args.branch)
        acceptance_text = fetch_acceptance_text(
            args.spec, repo=args.repo, branch=args.branch
        )
        if spec_text is None:
            branch = args.branch or _project_info_value("Release Branch") or "main"
            print(
                f"unable to read .louke/project/specs/{args.spec}/spec.md on branch {branch}",
                file=sys.stderr,
            )
            return 1
        if acceptance_text is None:
            # Do not error out, fall through to L1 check
            pass

    results = run_checks(spec_text or "", acceptance_text)
    return report(results)


if __name__ == "__main__":
    sys.exit(main())
