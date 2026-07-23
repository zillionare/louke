"""Integration tests for FR-1900: Security program gates & Judge review.

AC-FR1900-01: Runtime executes the policy-declared secret scan,
dependency/SCA, SAST and project security checks on the candidate
before providing Judge with the full security context. Judge returns
schema-valid findings/verdict with location, severity, impact and
required fix; Judge does NOT modify code, execute program gates, write
state or advance the workflow. Missing required program result, stale
Judge input, or Judge attempting to write state blocks M-SECURITY PASS.

Interfaces covered (per interfaces.md):
- IF-SEC-01 (Primary ARC-13)
- IF-CAND-01 (candidate context, ARC-09)
- IF-PROMPT-02 (Judge capability, ARC-01)
"""
# AC-FR1900-01

from __future__ import annotations

import pytest

from louke.runtime.security_gates import (
    ERROR_CODES,
    JudgeFinding,
    JudgeVerdict,
    ProgramScanResult,
    SecurityGateError,
    SecurityGateReport,
    evaluate_security_gate,
)


def _all_pass_scans() -> list[ProgramScanResult]:
    return [
        ProgramScanResult(
            scanner_id=s,
            status="pass",
            evidence_id=f"ev-{s}",
            tool_digest=f"sha256:{s}",
        )
        for s in ("secret-scan", "dependency-sca", "sast", "project-checks")
    ]


def _valid_judge(verdict: str = "PASS") -> JudgeVerdict:
    return JudgeVerdict(
        review_id="rev-judge-001",
        candidate_id="cand-1",
        verdict=verdict,
        findings=(),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_security_gate_passes_when_all_scans_pass_and_judge_pass():
    """AC-FR1900-01: 4 required scanners pass + Judge PASS -> pass."""
    report = evaluate_security_gate(
        "cand-1",
        _all_pass_scans(),
        _valid_judge("PASS"),
    )
    assert isinstance(report, SecurityGateReport)
    assert report.status == "pass"
    assert report.reasons == ()


@pytest.mark.real_module
def test_security_gate_rejects_missing_scanner():
    """AC-FR1900-01: missing required scanner -> SEC_SCANNER_REQUIRED_MISSING."""
    scans = _all_pass_scans()[:3]  # missing project-checks
    with pytest.raises(SecurityGateError) as exc:
        evaluate_security_gate("cand-1", scans, _valid_judge("PASS"))
    assert exc.value.code == "SEC_SCANNER_REQUIRED_MISSING"


@pytest.mark.real_module
def test_security_gate_fails_when_secret_scan_detects_secret():
    """AC-FR1900-01: secret-scan failure -> SEC_SECRET_DETECTED."""
    scans = _all_pass_scans()
    scans[0] = ProgramScanResult(
        scanner_id="secret-scan",
        status="fail",
        evidence_id="ev-secret",
        tool_digest="sha256:secret-scan",
    )
    report = evaluate_security_gate("cand-1", scans, _valid_judge("PASS"))
    assert report.status == "fail"
    assert "SEC_SECRET_DETECTED" in report.reasons


@pytest.mark.real_module
def test_security_gate_fails_when_sast_fails():
    """AC-FR1900-01: SAST failure -> SEC_SCAN_FAILED."""
    scans = _all_pass_scans()
    scans[2] = ProgramScanResult(
        scanner_id="sast",
        status="fail",
        evidence_id="ev-sast",
        tool_digest="sha256:sast",
    )
    report = evaluate_security_gate("cand-1", scans, _valid_judge("PASS"))
    assert report.status == "fail"
    assert "SEC_SCAN_FAILED" in report.reasons


@pytest.mark.real_module
def test_security_gate_fails_when_judge_revise():
    """AC-FR1900-01: Judge REVISE -> fail (cannot PASS M-SECURITY)."""
    report = evaluate_security_gate(
        "cand-1",
        _all_pass_scans(),
        _valid_judge("REVISE"),
    )
    assert report.status == "fail"


@pytest.mark.real_module
def test_security_gate_rejects_judge_writing_state():
    """AC-FR1900-01: Judge cannot write state -> SEC_JUDGE_CAPABILITY_VIOLATION."""
    judge = JudgeVerdict(
        review_id="rev-x",
        candidate_id="cand-1",
        verdict="PASS",
        wrote_state=True,  # forbidden!
    )
    with pytest.raises(SecurityGateError) as exc:
        evaluate_security_gate("cand-1", _all_pass_scans(), judge)
    assert exc.value.code == "SEC_JUDGE_CAPABILITY_VIOLATION"


@pytest.mark.real_module
def test_security_gate_rejects_judge_executing_program():
    """AC-FR1900-01: Judge cannot execute program gate -> SEC_JUDGE_CAPABILITY_VIOLATION."""
    judge = JudgeVerdict(
        review_id="rev-x",
        candidate_id="cand-1",
        verdict="PASS",
        executed_program=True,  # forbidden!
    )
    with pytest.raises(SecurityGateError) as exc:
        evaluate_security_gate("cand-1", _all_pass_scans(), judge)
    assert exc.value.code == "SEC_JUDGE_CAPABILITY_VIOLATION"


@pytest.mark.real_module
def test_security_gate_rejects_judge_running_command():
    """AC-FR1900-01: Judge cannot run commands -> SEC_JUDGE_CAPABILITY_VIOLATION."""
    judge = JudgeVerdict(
        review_id="rev-x",
        candidate_id="cand-1",
        verdict="PASS",
        ran_command=True,  # forbidden!
    )
    with pytest.raises(SecurityGateError) as exc:
        evaluate_security_gate("cand-1", _all_pass_scans(), judge)
    assert exc.value.code == "SEC_JUDGE_CAPABILITY_VIOLATION"


@pytest.mark.real_module
def test_judge_findings_carry_required_fields():
    """AC-FR1900-01: findings have location, severity, impact, required_fix, route."""
    finding = JudgeFinding(
        finding_id="F-001",
        location="louke/v014/x.py:42",
        severity="high",
        impact="credential leak risk",
        required_fix="remove hardcoded token",
        route="implementation",
    )
    assert finding.location
    assert finding.severity in ("critical", "high", "medium", "low")
    assert finding.required_fix
    assert finding.route in ("implementation", "security_test", "design", "requirement")


@pytest.mark.real_module
def test_required_scanners_set_includes_all_four_categories():
    """AC-FR1900-01: required scanners = secret-scan + dependency-sca + sast + project-checks."""
    from louke.runtime.security_gates import _REQUIRED_SCANNERS

    expected = {"secret-scan", "dependency-sca", "sast", "project-checks"}
    actual = set(_REQUIRED_SCANNERS)
    assert actual == expected


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-FR1900-01: ERROR_CODES includes all codes from interfaces.md §11."""
    expected = {
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
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
