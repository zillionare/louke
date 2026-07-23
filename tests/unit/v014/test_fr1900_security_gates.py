"""AC-FR1900-01: Security program gates & Judge review.

Runtime first executes the policy-declared secret scan, dependency/SCA,
SAST and project security checks on the current candidate, then provides
Judge with candidate diff/full code, Architecture/Interfaces, dependencies,
trust boundaries, historical findings and program results.  Judge only
returns semantic findings/verdict with location, severity, impact and
required fix; Judge does NOT modify code, execute program gates, write
state or advance the workflow.  Missing required program result, stale
Judge input, or Judge attempting to write state blocks M-SECURITY PASS.
"""

from __future__ import annotations


import pytest

from louke.runtime.security_gates import (
    JudgeVerdict,
    ProgramScanResult,
    SecurityGateError,
    SecurityGateReport,
    evaluate_security_gate,
)

_CAND = "cand:abc"


def _scans(
    *,
    all_pass: bool = True,
    missing: tuple[str, ...] = (),
    failing: tuple[str, ...] = (),
) -> list[ProgramScanResult]:
    required = ("secret-scan", "dependency-sca", "sast", "project-checks")
    out: list[ProgramScanResult] = []
    for scanner in required:
        if scanner in missing:
            continue  # missing
        status = "fail" if scanner in failing else ("pass" if all_pass else "fail")
        out.append(
            ProgramScanResult(
                scanner_id=scanner,
                status=status,
                evidence_id=f"ev-{scanner}",
                tool_digest="sha256:" + scanner[:6].ljust(6, "0") * 10,
            )
        )
    return out


def _judge(
    verdict: str = "PASS",
    wrote_state: bool = False,
    executed_program: bool = False,
    ran_command: bool = False,
) -> JudgeVerdict:
    return JudgeVerdict(
        review_id="rev-judge-1",
        candidate_id=_CAND,
        verdict=verdict,
        findings=(),
        wrote_state=wrote_state,
        executed_program=executed_program,
        ran_command=ran_command,
    )


def test_security_gate_passes_with_all_scans_and_judge_pass() -> None:
    """AC-FR1900-01: all required scans PASS + Judge PASS -> M-SECURITY PASS."""
    report = evaluate_security_gate(_CAND, _scans(), _judge("PASS"))
    assert isinstance(report, SecurityGateReport)
    assert report.status == "pass"


def test_security_gate_fails_when_required_scanner_missing() -> None:
    """AC-FR1900-01: missing required scanner blocks Judge dispatch."""
    with pytest.raises(SecurityGateError) as exc:
        evaluate_security_gate(_CAND, _scans(missing=("sast",)), _judge("PASS"))
    assert exc.value.code == "SEC_SCANNER_REQUIRED_MISSING"


def test_security_gate_fails_when_scan_failed() -> None:
    """AC-FR1900-01: a failed required scan blocks PASS."""
    report = evaluate_security_gate(
        _CAND, _scans(failing=("secret-scan",)), _judge("PASS")
    )
    assert report.status == "fail"


def test_security_gate_rejects_judge_attempting_to_write_state() -> None:
    """AC-FR1900-01: Judge writing state/code/gate is rejected."""
    with pytest.raises(SecurityGateError) as exc:
        evaluate_security_gate(_CAND, _scans(), _judge("PASS", wrote_state=True))
    assert exc.value.code == "SEC_JUDGE_CAPABILITY_VIOLATION"


def test_security_gate_rejects_judge_executing_program() -> None:
    """AC-FR1900-01: Judge executing program gates is rejected."""
    with pytest.raises(SecurityGateError) as exc:
        evaluate_security_gate(_CAND, _scans(), _judge("PASS", executed_program=True))
    assert exc.value.code == "SEC_JUDGE_CAPABILITY_VIOLATION"


def test_security_gate_rejects_judge_running_command() -> None:
    """AC-FR1900-01: Judge running commands is rejected."""
    with pytest.raises(SecurityGateError) as exc:
        evaluate_security_gate(_CAND, _scans(), _judge("PASS", ran_command=True))
    assert exc.value.code == "SEC_JUDGE_CAPABILITY_VIOLATION"


def test_security_gate_fails_when_judge_verdict_revise() -> None:
    """AC-FR1900-01: Judge REVISE blocks M-SECURITY PASS."""
    report = evaluate_security_gate(_CAND, _scans(), _judge("REVISE"))
    assert report.status == "fail"


def test_security_gate_fails_when_secret_detected() -> None:
    """AC-FR1900-01: secret detection is a non-waivable failure."""
    report = evaluate_security_gate(
        _CAND, _scans(failing=("secret-scan",)), _judge("PASS")
    )
    assert report.status == "fail"
    assert "SEC_SECRET_DETECTED" in report.reasons
