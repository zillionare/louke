"""Runtime-owned deterministic quality program checks."""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from louke._common import _read_project_info_field, git, normalize_repo_relative_roots


@dataclass(frozen=True)
class QualityProgramResult:
    """Structured result of a Runtime quality gate.

    Attributes:
        status: ``pass`` or ``fail``.
        findings: Structured blocking and non-blocking findings.
    """

    status: str
    findings: tuple[dict[str, object], ...]


def run_quality_gate(
    *,
    commit_range: str,
    tests_roots: list[str] | None = None,
    cwd: Path | None = None,
    spec_id: str = "",
    skip_ac_trace: bool = False,
    skip_anti_pattern: bool = False,
    full_scan: bool = False,
) -> QualityProgramResult:
    """Run Runtime-owned format, RGR, trace and anti-pattern checks.

    Args:
        commit_range: Git revision range under review.
        tests_roots: Relative test roots scanned for evidence.
        cwd: Workspace root; defaults to the current directory.
        spec_id: Optional Spec identity for AC trace.
        skip_ac_trace: Whether to omit AC trace validation.
        skip_anti_pattern: Whether to omit anti-pattern validation.
        full_scan: Scan all roots instead of changed files.

    Returns:
        A :class:`QualityProgramResult`; no stage or workflow state is written.
    """
    root = Path.cwd() if cwd is None else Path(cwd)
    roots = normalize_repo_relative_roots(tests_roots or [], default=["tests/"])
    targets = _resolve_scan_targets(commit_range, roots, root, full_scan)
    findings = _commit_findings(commit_range, root)
    findings.extend(_rgr_findings(commit_range, root))
    if not skip_ac_trace:
        findings.extend(_trace_findings(spec_id, targets, roots, root))
    if not skip_anti_pattern:
        findings.extend(_anti_pattern_findings(targets, root))
    status = "fail" if any(_is_blocking(item) for item in findings) else "pass"
    return QualityProgramResult(status=status, findings=tuple(findings))


def run_regression_gate(
    *, baseline: str, current: str, cwd: Path | None = None
) -> QualityProgramResult:
    """Run the Runtime regression gate without creating a legacy stage result.

    Args:
        baseline: Revision before the fix.
        current: Revision containing the fix.
        cwd: Workspace root; defaults to the current directory.

    Returns:
        A :class:`QualityProgramResult` with regression findings.
    """
    root = Path.cwd() if cwd is None else Path(cwd)
    rc, output, _ = git("diff", "--name-only", baseline, current, cwd=root)
    if rc != 0:
        return QualityProgramResult(
            status="fail",
            findings=({"severity": "critical", "description": "git diff failed"},),
        )
    changed = [item for item in output.splitlines() if item]
    code_changes = [item for item in changed if "test" not in item.lower()]
    findings: list[dict[str, object]] = []
    if len(code_changes) > 5:
        findings.append(
            {
                "severity": "medium",
                "description": f"bug fix changed {len(code_changes)} code files",
            }
        )
    dependency_files = {
        "package.json",
        "requirements.txt",
        "pyproject.toml",
        "Cargo.toml",
        "go.mod",
    }
    for path in changed:
        if Path(path).name in dependency_files:
            findings.append(
                {
                    "severity": "high",
                    "description": f"dependency file changed: {path}",
                }
            )
    status = "fail" if any(_is_blocking(item) for item in findings) else "pass"
    return QualityProgramResult(status=status, findings=tuple(findings))


_ISSUE_RE = re.compile(r"#(\d+)")


def _resolve_scan_targets(
    commit_range: str, roots: list[str], cwd: Path, full_scan: bool
) -> list[str]:
    if full_scan:
        return roots
    rc, output, _ = git("diff", "--name-only", commit_range, "--", *roots, cwd=cwd)
    if rc != 0:
        return roots
    return [line for line in output.splitlines() if line] or roots


def _commit_findings(commit_range: str, cwd: Path) -> list[dict[str, object]]:
    rc, output, _ = git("log", "--format=%H %s", commit_range, cwd=cwd)
    if rc != 0:
        return [{"severity": "critical", "description": f"git log failed: {output}"}]
    prefixes = (
        "feat: green",
        "fix: green",
        "refactor:",
        "fix:",
        "docs:",
        "chore:",
        "e2e:",
    )
    findings = []
    for line in output.splitlines():
        parts = line.split(" ", 1)
        if len(parts) == 2 and not parts[1].startswith(prefixes):
            findings.append(
                {
                    "severity": "medium",
                    "commit": parts[0][:8],
                    "subject": parts[1],
                    "description": "commit message format is non-standard",
                }
            )
    return findings


def _rgr_findings(commit_range: str, cwd: Path) -> list[dict[str, object]]:
    rc, output, _ = git("log", "--reverse", "--format=%s", commit_range, cwd=cwd)
    if rc != 0:
        return [{"severity": "critical", "description": f"git log failed: {output}"}]
    grouped: dict[str, list[str]] = {}
    for subject in output.splitlines():
        phase = _phase(subject)
        if phase is not None:
            issue = _ISSUE_RE.search(subject)
            grouped.setdefault(issue.group(1) if issue else subject, []).append(phase)
    findings = []
    for phases in grouped.values():
        if "refactor" in phases and any(
            phase == "green" for phase in phases[phases.index("refactor") + 1 :]
        ):
            findings.append(
                {
                    "severity": "high",
                    "description": "refactor before green within one issue",
                }
            )
    return findings


def _trace_findings(
    spec_id: str, targets: list[str], roots: list[str], cwd: Path
) -> list[dict[str, object]]:
    resolved_spec = spec_id.strip() or _read_project_info_field("Spec ID").strip()
    if not resolved_spec:
        return [{"severity": "high", "description": "AC trace requires spec-id"}]
    if not targets:
        return []
    command = [
        sys.executable,
        "-m",
        "louke.__main__",
        "agent",
        "archer",
        "ci-scan",
        "--spec",
        resolved_spec,
        "--tests",
        *targets,
        "--diff-only",
    ]
    if subprocess.run(command, cwd=cwd).returncode == 0:
        return []
    return [{"severity": "high", "description": f"AC trace failed for {roots}"}]


def _anti_pattern_findings(targets: list[str], cwd: Path) -> list[dict[str, object]]:
    if not targets:
        return []
    command = [
        sys.executable,
        "-m",
        "louke._tools.check_assertions",
        "--tests",
        *targets,
        "--exclude",
        "tests/fixtures",
    ]
    baseline = cwd / ".louke" / "project" / "baselines" / "keeper-anti-pattern.txt"
    if baseline.exists():
        command.extend(["--legacy-baseline", str(baseline)])
    if subprocess.run(command, cwd=cwd).returncode == 0:
        return []
    return [{"severity": "high", "description": "anti-pattern scan failed"}]


def _phase(subject: str) -> str | None:
    if subject.startswith(("feat: green", "fix: green")):
        return "green"
    if subject.startswith("refactor:"):
        return "refactor"
    return None


def _is_blocking(finding: dict[str, object]) -> bool:
    return finding.get("severity") in {"critical", "high"}
