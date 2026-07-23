"""FR-1900: Security program gates & Judge review.

Runtime first executes the policy-declared secret scan, dependency/SCA,
SAST and project security checks on the current candidate, then provides
Judge with candidate diff/full code, Architecture/Interfaces, dependencies,
trust boundaries, historical findings and program results.  Judge only
returns semantic findings/verdict with location, severity, impact and
required fix; Judge does NOT modify code, execute program gates, write
state or advance the workflow.  Missing required program result, stale
Judge input, or Judge attempting to write state blocks M-SECURITY PASS
(AC-FR1900-01).
"""

from __future__ import annotations

from dataclasses import dataclass

ERROR_CODES = (
    "SEC_POLICY_NOT_CURRENT",
    "SEC_SCANNER_REQUIRED_MISSING",
    "SEC_SCAN_FAILED",
    "SEC_SCAN_UNKNOWN",
    "SEC_SECRET_DETECTED",
    "SEC_JUDGE_INPUT_INCOMPLETE",
    "SEC_JUDGE_SCHEMA_INVALID",
    "SEC_JUDGE_STALE",
    "SEC_JUDGE_CAPABILITY_VIOLATION",
    "SEC_FINDING_ROUTE_INVALID",
    "SEC_WAIVER_FORBIDDEN",
    "SEC_WAIVER_INVALID",
    "SEC_SKIP_FORBIDDEN",
    "SEC_SKIP_INVALID",
)

_REQUIRED_SCANNERS: tuple[str, ...] = (
    "secret-scan",
    "dependency-sca",
    "sast",
    "project-checks",
)


class SecurityGateError(Exception):
    """A fail-closed security gate rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ProgramScanResult:
    """Result of one required security scanner (AC-FR1900-01).

    Attributes:
        scanner_id: Stable scanner id (``secret-scan|dependency-sca|sast|project-checks``).
        status: ``pass|fail|unknown``.
        evidence_id: Bound evidence id.
        tool_digest: ``sha256:<hex>`` of the scanner tool bytes.
    """

    scanner_id: str
    status: str
    evidence_id: str
    tool_digest: str


@dataclass(frozen=True)
class JudgeFinding:
    """A single Judge finding (AC-FR1900-01).

    Attributes:
        finding_id: Stable finding id.
        location: File path + line/anchor.
        severity: ``critical|high|medium|low``.
        impact: Free-text impact description.
        required_fix: Free-text required fix.
        route: ``implementation|security_test|design|requirement``.
    """

    finding_id: str
    location: str
    severity: str
    impact: str
    required_fix: str
    route: str


@dataclass(frozen=True)
class JudgeVerdict:
    """A Judge verdict (AC-FR1900-01).

    Attributes:
        review_id: Stable review id.
        candidate_id: Bound candidate id.
        verdict: ``PASS|REVISE``.
        findings: Tuple of :class:`JudgeFinding`.
        wrote_state: ``True`` if Judge attempted to write state (forbidden).
        executed_program: ``True`` if Judge attempted to execute a program gate (forbidden).
        ran_command: ``True`` if Judge attempted to run a command (forbidden).
    """

    review_id: str
    candidate_id: str
    verdict: str
    findings: tuple[JudgeFinding, ...] = ()
    wrote_state: bool = False
    executed_program: bool = False
    ran_command: bool = False


@dataclass(frozen=True)
class SecurityGateReport:
    """Result of :func:`evaluate_security_gate` (AC-FR1900-01).

    Attributes:
        candidate_id: Bound candidate id.
        status: ``pass`` or ``fail``.
        reasons: Tuple of stable reason codes.
    """

    candidate_id: str
    status: str
    reasons: tuple[str, ...] = ()


def _check_scans(scans: list[ProgramScanResult]) -> tuple[list[str], list[str]]:
    """Return (missing, failed) scanner ids from the scan set."""
    present = {s.scanner_id: s for s in scans}
    missing = [s for s in _REQUIRED_SCANNERS if s not in present]
    failed = [s.scanner_id for s in scans if s.status != "pass"]
    return missing, failed


def evaluate_security_gate(
    candidate_id: str,
    scans: list[ProgramScanResult],
    judge: JudgeVerdict,
) -> SecurityGateReport:
    """Evaluate the security program gate + Judge review (AC-FR1900-01).

    Args:
        candidate_id: Bound candidate id.
        scans: List of :class:`ProgramScanResult` for each required scanner.
        judge: :class:`JudgeVerdict` from the Judge review.

    Returns:
        A :class:`SecurityGateReport` with ``status=pass`` only when every
        required scanner passed and Judge verdict is ``PASS``.

    Raises:
        SecurityGateError: With ``SEC_SCANNER_REQUIRED_MISSING`` if a required
            scanner is missing; ``SEC_JUDGE_CAPABILITY_VIOLATION`` if Judge
            attempted to write state, execute a program or run a command.
    """
    missing, failed = _check_scans(scans)
    if missing:
        raise SecurityGateError(
            "SEC_SCANNER_REQUIRED_MISSING",
            f"missing required scanners: {missing}",
        )
    if judge.wrote_state or judge.executed_program or judge.ran_command:
        raise SecurityGateError(
            "SEC_JUDGE_CAPABILITY_VIOLATION",
            "Judge attempted to write state, execute a program gate or run a command",
        )
    reasons: list[str] = []
    for scanner_id in failed:
        if scanner_id == "secret-scan":
            reasons.append("SEC_SECRET_DETECTED")
        else:
            reasons.append("SEC_SCAN_FAILED")
    if judge.verdict != "PASS":
        reasons.append("SEC_JUDGE_SCHEMA_INVALID")
    return SecurityGateReport(
        candidate_id=candidate_id,
        status="pass" if not reasons else "fail",
        reasons=tuple(reasons),
    )
