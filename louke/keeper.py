"""Deprecated compatibility CLI for Runtime-owned quality programs."""

import sys
from pathlib import Path

from ._common import git
from .runtime.quality import (
    resolve_scan_targets as _runtime_resolve_scan_targets,
    run_quality_gate,
    run_regression_gate,
)


def resolve_scan_targets(
    commit_range: str,
    tests_roots: list[str],
    cwd: Path = None,
    full_scan: bool = False,
) -> list[str]:
    """Compatibility wrapper for the Runtime scan-target resolver.

    Args:
        commit_range: Git revision range under review.
        tests_roots: Relative test roots.
        cwd: Workspace root.
        full_scan: Whether to scan all roots.

    Returns:
        Runtime-resolved changed paths.
    """
    return _runtime_resolve_scan_targets(
        commit_range,
        tests_roots,
        Path.cwd() if cwd is None else cwd,
        full_scan,
        git_runner=git,
    )


def register(subparsers):
    parser = subparsers.add_parser(
        "keeper", help="deprecated compatibility adapter for Runtime gates"
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    p = sub.add_parser(
        "gate",
        help="per-commit gate (format + R-G-R order + AC trace + anti-pattern scan)",
    )
    p.add_argument(
        "--commit-range", default="HEAD~1..HEAD", help="commit range to check"
    )
    p.add_argument("--tests", action="store_true", help="deprecated (v0.7-001)")
    p.add_argument("--lint", action="store_true", help="deprecated (v0.7-001)")
    p.add_argument("--typecheck", action="store_true", help="deprecated (v0.7-001)")
    p.add_argument(
        "--stage",
        default="M-DEV",
        choices=["M-DEV", "M-E2E"],
        help="retained compatibility option; Runtime does not write stage artifacts",
    )
    p.add_argument(
        "--spec-id",
        default="",
        help="spec-id for AC trace validation (falls back to project.toml)",
    )
    p.add_argument(
        "--tests-root",
        action="append",
        default=[],
        help="repeatable host-project test root used by AC trace and anti-pattern scans",
    )
    p.add_argument(
        "--skip-ac-trace", action="store_true", help="skip AC trace validation"
    )
    p.add_argument(
        "--skip-anti-pattern", action="store_true", help="skip anti-pattern scan"
    )
    p.add_argument(
        "--full-scan",
        action="store_true",
        help="manually scan complete test roots instead of changed files",
    )

    p = sub.add_parser(
        "regression", help="regression check (per-bug-fix, compare before/after fix)"
    )
    p.add_argument("--baseline", default="main", help="baseline (before fix)")
    p.add_argument("--current", default="HEAD", help="current (after fix)")
    p.add_argument(
        "--tests",
        action="store_true",
        help="run tests for actual comparison (default: diff range only)",
    )


def run(args):
    handlers = {
        "gate": cmd_gate,
        "regression": cmd_regression,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def cmd_gate(args):
    """per-commit gate check: commit format + R-G-R order + AC trace + anti-pattern scan."""
    if args.tests:
        print(
            "error: --tests deprecated (v0.7-001); lint/test/typecheck no longer scheduled by keeper gate",
            file=sys.stderr,
        )
        return 1
    if args.lint:
        print(
            "error: --lint deprecated (v0.7-001); lint/test/typecheck no longer scheduled by keeper gate",
            file=sys.stderr,
        )
        return 1
    if args.typecheck:
        print(
            "error: --typecheck deprecated (v0.7-001); lint/test/typecheck no longer scheduled by keeper gate",
            file=sys.stderr,
        )
        return 1

    result = run_quality_gate(
        commit_range=args.commit_range,
        tests_roots=args.tests_root,
        cwd=Path.cwd(),
        spec_id=args.spec_id,
        skip_ac_trace=args.skip_ac_trace,
        skip_anti_pattern=args.skip_anti_pattern,
        full_scan=args.full_scan,
    )
    print("=== Deprecated compatibility adapter ===")
    print("Runtime quality program owns this gate; no stage result was written.")
    status = result.status if hasattr(result, "status") else result["status"]
    findings = result.findings if hasattr(result, "findings") else result["findings"]
    print(f"Status: {status}")
    for finding in findings:
        print(f"[{finding.get('severity', '?')}] {finding.get('description', '')}")
    if not args.skip_ac_trace:
        trace_failed = any(
            "AC trace" in str(item.get("description", "")) for item in findings
        )
        print(f"--- AC Trace: {'FAIL' if trace_failed else 'PASS'} ---")
    if not args.skip_anti_pattern:
        anti_failed = any(
            "anti-pattern" in str(item.get("description", "")) for item in findings
        )
        print(f"--- Anti-Pattern: {'FAIL' if anti_failed else 'PASS'} ---")
    return 0 if status == "pass" else 1


def cmd_regression(args):
    """Regression check: compare baseline vs current test results."""
    cwd = Path.cwd()
    print("=== Deprecated compatibility adapter ===")
    print(f"Baseline: {args.baseline}")
    print(f"Current: {args.current}")
    print()

    result = run_regression_gate(
        baseline=args.baseline,
        current=args.current,
        cwd=cwd,
    )
    print(f"Runtime regression status: {result.status}")
    for finding in result.findings:
        print(f"[{finding.get('severity', '?')}] {finding.get('description', '')}")
    return 0 if result.status == "pass" else 1
