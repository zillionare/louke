"""Git pre-commit quality gates backed by Keeper's scanners."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .check_acs import parse_acceptance, scan_refs
from .check_assertions import scan_file

PREFIXES = (
    "feat: green",
    "fix: green",
    "refactor:",
    "fix:",
    "docs:",
    "chore:",
    "e2e:",
)
TEST_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".sh", ".bats"}


def validate_subject(subject: str) -> list[str]:
    """Return quality-gate findings for a commit subject."""
    if any(subject.startswith(prefix) for prefix in PREFIXES):
        return []
    return [f"commit subject has no allowed prefix: {subject}"]


def should_scan_ac_trace(subject: str) -> bool:
    """Return whether the subject requires AC trace validation."""
    return not subject.startswith("fix:")


def staged_test_files(filenames: list[str] | None = None) -> list[Path]:
    """Return staged test files, or pre-commit's supplied file list."""
    if filenames:
        candidates = [Path(name) for name in filenames]
    else:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            check=False,
            capture_output=True,
            text=True,
        )
        candidates = [Path(line) for line in result.stdout.splitlines()]
    return [
        path
        for path in candidates
        if path.suffix in TEST_SUFFIXES
        and path.is_file()
        and "tests" in path.parts
        and "fixtures" not in path.parts
    ]


def run_quality_checks(subject: str, files: list[Path]) -> list[str]:
    """Run anti-pattern and, unless fixing, AC checks on staged tests."""
    findings: list[str] = []
    for path in files:
        findings.extend(_format_scan_finding(path, item) for item in scan_file(path))
    if not should_scan_ac_trace(subject):
        return findings
    if not files:
        return findings
    acceptance_path = Path(".louke/project/specs") / _spec_id() / "acceptance.md"
    if not acceptance_path.exists():
        return findings + [f"acceptance.md not found: {acceptance_path}"]
    known = set(parse_acceptance(acceptance_path))
    result = scan_refs(
        files,
        current_version=f"v{_project_version()}",
        known_acs=known,
        first_lines_only=True,
    )
    for item in result["refs"]:
        if item["status"] in {"wrong-version", "malformed"}:
            findings.append(
                f"{item['status']}: {item['raw']} ({item['file']}:{item['line']})"
            )
        elif item["status"] == "current" and item["ac"] in result["unknown"]:
            findings.append(f"unknown AC: {item['ac']}")
    if not result["refs"]:
        findings.append("AC trace missing from staged test code")
    return findings


def _format_scan_finding(path: Path, item: dict[str, object]) -> str:
    """Format one Keeper anti-pattern finding for hook output."""
    return f"{item['code']} {path}:{item['line']}"


def _project_version() -> str:
    return _project_value("version") or "0.13.1"


def _spec_id() -> str:
    return _project_value("spec_id")


def _project_value(key: str) -> str:
    try:
        import tomllib

        data = tomllib.loads(
            Path(".louke/project/project.toml").read_text(encoding="utf-8")
        )
    except (OSError, tomllib.TOMLDecodeError):
        return ""
    return str(data.get("project", {}).get(key, ""))


def main(argv: list[str] | None = None) -> int:
    """Run the hook selected by pre-commit and return a process status."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--hook", choices=("pre-commit", "commit-msg"), required=True)
    parser.add_argument("filenames", nargs="*")
    args = parser.parse_args(argv)
    subject = ""
    if args.hook == "commit-msg":
        if not args.filenames:
            return 2
        subject = Path(args.filenames[0]).read_text(encoding="utf-8").splitlines()[0]
        findings = validate_subject(subject)
        findings.extend(run_quality_checks(subject, staged_test_files()))
    else:
        findings = run_quality_checks("", staged_test_files(args.filenames))
    for finding in findings:
        print(f"[REJECT] {finding}", file=sys.stderr)
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
