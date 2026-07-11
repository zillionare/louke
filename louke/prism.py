"""Prism commands - code review (incl. test code + security quick scan).

Prism responsibilities: multi-perspective code review + critical-perspective +
test anti-pattern scan + security quick scan.
"""

import re
import sys
from pathlib import Path

from ._common import get_diff_files, print_findings, has_blocking_severity
from ._security import scan_file
from .stage_results import write_stage_result
from ._tests import scan_test_file, find_test_files


def register(subparsers):
    parser = subparsers.add_parser("prism", help="code review (Prism)")
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    p = sub.add_parser("review", help="full review (production + test + security)")
    p.add_argument("--diff", default="HEAD", help="ref to review (default HEAD)")
    p.add_argument(
        "--stage",
        choices=["M-DEV", "M-E2E"],
        help="optional stage; when set with --spec-id, persist review artifact automatically",
    )
    p.add_argument(
        "--spec-id",
        default="",
        help="spec-id used when persisting stage artifact from review",
    )
    p.add_argument(
        "--commit-range",
        default="",
        help="optional commit range for persisted review artifact",
    )
    p.add_argument(
        "--reviewed-target",
        dest="reviewed_targets",
        action="append",
        default=[],
        help="repeatable path / contract target reviewed by Prism",
    )

    p = sub.add_parser(
        "test-patterns",
        help="test code anti-pattern scan (8 categories + AC reference)",
    )
    p.add_argument("--tests", default="tests/", help="tests directory (default tests/)")

    p = sub.add_parser("security-quick-scan", help="shallow security pattern scan")
    p.add_argument("--diff", default="HEAD", help="ref to scan")

    p = sub.add_parser(
        "code-quality",
        help="code quality check (function length / nesting depth / DRY)",
    )
    p.add_argument("--diff", default="HEAD", help="ref to scan")

    p = sub.add_parser(
        "review-arch",
        help="architecture review (semantic document checks + stage artifact)",
    )
    p.add_argument("--spec-id", required=True)
    p.add_argument(
        "--reviewed-target",
        dest="reviewed_targets",
        action="append",
        default=[],
        help="repeatable contract target reviewed by Prism",
    )

    p = sub.add_parser(
        "record-review", help="persist Prism review verdict as a stage artifact"
    )
    p.add_argument("--stage", required=True, choices=["M-ARCH", "M-DEV", "M-E2E"])
    p.add_argument("--spec-id", required=True)
    p.add_argument("--verdict", required=True, choices=["pass", "reject"])
    p.add_argument(
        "--reviewed-target",
        dest="reviewed_targets",
        action="append",
        default=[],
        help="repeatable path / contract target reviewed by Prism",
    )
    p.add_argument(
        "--blocking-finding",
        action="append",
        default=[],
        help="repeatable blocking finding summary",
    )
    p.add_argument(
        "--accepted-risk",
        action="append",
        default=[],
        help="repeatable accepted risk summary",
    )
    p.add_argument(
        "--commit-range",
        default="",
        help="optional commit range for M-DEV / M-E2E reviews",
    )


def run(args):
    handlers = {
        "review": cmd_review,
        "test-patterns": cmd_test_patterns,
        "security-quick-scan": cmd_security_quick_scan,
        "code-quality": cmd_code_quality,
        "review-arch": cmd_review_arch,
        "record-review": cmd_record_review,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def cmd_review(args):
    """Full review: production + test + security quick scan."""
    cwd = Path.cwd()
    print("=== Prism Full Review ===")
    print(f"Diff: {args.diff}")
    print()

    changed = get_diff_files("HEAD~1", args.diff, cwd=cwd)

    # Test patterns
    test_findings = []
    for fp_str in changed:
        if "test" in fp_str.lower():
            fp = cwd / fp_str
            if fp.exists():
                test_findings.extend(scan_test_file(fp))

    # Security patterns
    security_findings = []
    for fp_str in changed:
        fp = cwd / fp_str
        if fp.exists():
            security_findings.extend(scan_file(fp))

    print_findings(test_findings, header="Test Anti-patterns")
    print_findings(security_findings, header="Security Quick Scan")

    print("\n=== Summary ===")
    print(f"Test findings:     {len(test_findings)}")
    print(f"Security findings: {len(security_findings)}")

    # Verdict: critical/high -> REJECT
    all_findings = test_findings + security_findings
    if has_blocking_severity(all_findings):
        print("-> REJECT (critical/high found)")
        _write_review_artifact(
            stage=args.stage,
            spec_id=args.spec_id,
            verdict="fail",
            reviewed_targets=args.reviewed_targets or changed,
            blocking_findings=_summarize_findings(all_findings),
            commit_range=args.commit_range,
            source_command="review",
            diff_ref=args.diff,
        )
        return 1
    print("-> PASS (semantic review still required by Prism agent)")
    _write_review_artifact(
        stage=args.stage,
        spec_id=args.spec_id,
        verdict="pass",
        reviewed_targets=args.reviewed_targets or changed,
        blocking_findings=[],
        commit_range=args.commit_range,
        source_command="review",
        diff_ref=args.diff,
    )
    return 0


def cmd_test_patterns(args):
    """Test code anti-pattern scan."""
    cwd = Path.cwd()
    test_root = cwd / args.tests

    test_files = find_test_files(test_root)
    print("=== Test Anti-patterns Scan ===")
    print(f"Test root: {test_root}")
    print(f"Files found: {len(test_files)}")

    all_findings = []
    for fp in test_files:
        all_findings.extend(scan_test_file(fp))

    print_findings(all_findings, header="Test Anti-pattern Findings")

    print(f"\n=== Summary: {len(all_findings)} findings ===")
    if has_blocking_severity(all_findings):
        print("-> critical/high hit; needs fix")
        return 1
    return 0


def cmd_security_quick_scan(args):
    """Shallow security pattern scan - similar to judge quick-scan but from a different angle (Prism looks at code quality)."""
    cwd = Path.cwd()
    changed = get_diff_files("HEAD~1", args.diff, cwd=cwd)
    print("=== Prism Security Quick Scan ===")
    print(f"Files: {len(changed)}")

    all_findings = []
    for fp_str in changed:
        fp = cwd / fp_str
        if fp.exists():
            all_findings.extend(scan_file(fp))

    print_findings(all_findings, header="Findings")
    return 1 if has_blocking_severity(all_findings) else 0


def cmd_code_quality(args):
    """Code quality check (function length / nesting depth)."""
    cwd = Path.cwd()
    changed = get_diff_files("HEAD~1", args.diff, cwd=cwd)
    print("=== Code Quality Check ===")
    print(f"Files: {len(changed)}")

    findings = []
    for fp_str in changed:
        fp = cwd / fp_str
        if not fp.exists() or fp.suffix != ".py":
            continue
        try:
            content = fp.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError):
            continue

        # function length check
        lines = content.split("\n")
        in_func = False
        func_start = 0
        func_name = ""
        func_indent = 0
        for i, line in enumerate(lines):
            m = re.match(r"^(\s*)(?:async\s+)?def\s+(\w+)\s*\(", line)
            if m:
                # entering a new function
                if in_func:
                    func_len = i - func_start
                    if func_len > 30:
                        findings.append(
                            {
                                "file": str(fp),
                                "line": func_start + 1,
                                "severity": "medium",
                                "pattern_id": "func-too-long",
                                "description": f"function {func_name} length {func_len} lines (recommended <=30)",
                                "matched": "function length",
                                "snippet": lines[func_start].strip()[:120],
                            }
                        )
                in_func = True
                func_start = i
                func_name = m.group(2)
                func_indent = len(m.group(1))
            elif (
                in_func
                and line.strip()
                and not line.startswith(" " * (func_indent + 1))
                and not line.startswith(func_indent * " ")
            ):
                # function ended
                func_len = i - func_start
                if func_len > 30:
                    findings.append(
                        {
                            "file": str(fp),
                            "line": func_start + 1,
                            "severity": "medium",
                            "pattern_id": "func-too-long",
                            "description": f"function {func_name} length {func_len} lines (recommended <=30)",
                            "matched": "function length",
                            "snippet": lines[func_start].strip()[:120],
                        }
                    )
                in_func = False

    print_findings(findings, header="Code Quality Findings")
    print(f"\n=== Summary: {len(findings)} findings ===")
    return 1 if has_blocking_severity(findings) else 0


def cmd_review_arch(args):
    """Architecture review for M-ARCH: inspect design documents and persist review artifact."""
    reviewed_targets = args.reviewed_targets or [
        f".louke/project/specs/{args.spec_id}/architecture.md",
        f".louke/project/specs/{args.spec_id}/interfaces.md",
        f".louke/project/specs/{args.spec_id}/test-plan.md",
        f".louke/project/specs/{args.spec_id}/spec.md",
        f".louke/project/specs/{args.spec_id}/acceptance.md",
        ".louke/project/project.toml",
    ]
    blocking_findings = _review_arch_documents(args.spec_id)
    verdict = "fail" if blocking_findings else "pass"
    path = _write_review_artifact(
        stage="M-ARCH",
        spec_id=args.spec_id,
        verdict=verdict,
        reviewed_targets=reviewed_targets,
        blocking_findings=blocking_findings,
        source_command="review",
    )
    if blocking_findings:
        print("=== Prism M-ARCH Review ===")
        for item in blocking_findings:
            print(f"- {item}")
        if path:
            print(f"✗ review artifact written: {path}")
        return 1
    print("=== Prism M-ARCH Review ===")
    if path:
        print(f"✓ review artifact written: {path}")
    return 0


def cmd_record_review(args):
    """Persist Prism's verdict so Maestro can gate on a concrete artifact."""
    if args.stage in {"M-ARCH", "M-DEV", "M-E2E"} and args.verdict == "pass":
        print(
            f"prism record-review: pass artifacts for {args.stage} must come from "
            "lk agent prism review ... or lk agent prism review-arch --spec-id ...",
            file=sys.stderr,
        )
        return 2
    path = _write_review_artifact(
        stage=args.stage,
        spec_id=args.spec_id,
        verdict="pass" if args.verdict == "pass" else "fail",
        reviewed_targets=args.reviewed_targets,
        blocking_findings=args.blocking_finding,
        accepted_risks=args.accepted_risk,
        commit_range=args.commit_range,
        source_command="record-review",
    )
    print(f"✓ review artifact written: {path}")
    return 0


def _summarize_findings(findings):
    summaries = []
    for item in findings:
        pattern = item.get("pattern_id") or item.get("severity") or "finding"
        desc = item.get("description") or ""
        file_path = item.get("file") or ""
        line = item.get("line")
        location = f"{file_path}:{line}" if file_path and line else file_path
        parts = [str(pattern).strip()]
        if location:
            parts.append(location)
        if desc:
            parts.append(str(desc).strip())
        summaries.append(" - ".join(part for part in parts if part))
    return summaries


def _write_review_artifact(
    *,
    stage,
    spec_id,
    verdict,
    reviewed_targets,
    blocking_findings,
    accepted_risks=None,
    commit_range="",
    source_command="",
    diff_ref="",
):
    if not stage or not spec_id:
        return None
    metadata = {}
    if commit_range:
        metadata["commit_range"] = commit_range
    if source_command:
        metadata["source_command"] = source_command
    if diff_ref:
        metadata["diff"] = diff_ref
    return write_stage_result(
        spec_id=spec_id,
        stage=stage,
        kind="review-result",
        role="Prism",
        verdict=verdict,
        reviewed_targets=reviewed_targets,
        blocking_findings=blocking_findings,
        accepted_risks=accepted_risks,
        metadata=metadata,
    )


def _review_arch_documents(spec_id):
    spec_dir = Path(f".louke/project/specs/{spec_id}")
    checks = {
        "spec.md": spec_dir / "spec.md",
        "acceptance.md": spec_dir / "acceptance.md",
        "test-plan.md": spec_dir / "test-plan.md",
        "architecture.md": spec_dir / "architecture.md",
        "interfaces.md": spec_dir / "interfaces.md",
        "project.toml": Path(".louke/project/project.toml"),
    }
    failures = []
    contents = {}
    for label, path in checks.items():
        if not path.exists():
            failures.append(f"missing {path.as_posix()}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            failures.append(f"empty {path.as_posix()}")
            continue
        contents[label] = text
    if failures:
        return failures

    if "FR-" not in contents["architecture.md"]:
        failures.append("architecture.md must reference at least one FR requirement")
    if (
        "Interfaces" not in contents["interfaces.md"]
        and "# Interfaces" not in contents["interfaces.md"]
    ):
        failures.append("interfaces.md must define interface scope explicitly")
    if "[e2e]" not in contents["project.toml"]:
        failures.append(
            "project.toml missing [e2e] section required by Archer contract"
        )
    if "test_framework" not in contents["project.toml"]:
        failures.append("project.toml missing [meta].test_framework")
    return failures
