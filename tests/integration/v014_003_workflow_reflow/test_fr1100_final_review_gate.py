"""Integration tests for FR-1100: Final task review & completion gate.

AC-FR1100-01: Prism's final review binds the complete formal commit
range, ``B/R/G/(Refactor)`` lineage and current checks; the program
gate verifies scope, secret, trace, generated files and unattributed
diff. Missing valid Red/review/pre-commit, Red test changes, or only
Agent self-reported PASS / Agent-created commits prevent task
completion and the requirement Issue is not marked release-complete.

Interfaces covered (per interfaces.md):
- IF-RGR-01 (Primary ARC-05)
- IF-REV-02 (Prism final review, ARC-07)
- IF-TRACE-01 (trace edges, ARC-16)
"""
# AC-FR1100-01

from __future__ import annotations

import pytest

from louke.v014.fr1100_final_review_gate import (
    ERROR_CODES,
    FinalGateReport,
    FinalLineage,
    PrismFinalVerdict,
    TaskCompletionGate,
    evaluate_final_gate,
)


def _valid_lineage() -> FinalLineage:
    return FinalLineage(
        baseline_oid="b" * 40,
        red_oid="r" * 40,
        green_oid="g" * 40,
        refactor_oid=None,
    )


def _valid_checks() -> dict:
    return {
        "scope": True,
        "secret": True,
        "ac_trace": True,
        "generated_files": True,
        "external_diff": True,
        "anti_pattern": True,
        "dependency": True,
    }


def _valid_verdict(subject_oid: str = "g" * 40) -> PrismFinalVerdict:
    return PrismFinalVerdict(
        review_id="rev-final-001",
        subject_oid=subject_oid,
        verdict="PASS",
    )


# ---------------------------------------------------------------------------
# evaluate_final_gate
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_evaluate_final_gate_passes_when_all_required_checks_pass():
    """AC-FR1100-01: all required checks pass -> status=pass."""
    report = evaluate_final_gate(_valid_lineage(), _valid_checks())
    assert isinstance(report, FinalGateReport)
    assert report.status == "pass"
    assert report.failed == ()


@pytest.mark.real_module
def test_evaluate_final_gate_fails_when_scope_check_fails():
    """AC-FR1100-01: scope breach -> fail."""
    checks = _valid_checks()
    checks["scope"] = False
    report = evaluate_final_gate(_valid_lineage(), checks)
    assert report.status == "fail"
    assert "scope" in report.failed


@pytest.mark.real_module
def test_evaluate_final_gate_fails_when_secret_check_fails():
    """AC-FR1100-01: secret detected in range -> fail."""
    checks = _valid_checks()
    checks["secret"] = False
    report = evaluate_final_gate(_valid_lineage(), checks)
    assert report.status == "fail"
    assert "secret" in report.failed


@pytest.mark.real_module
def test_evaluate_final_gate_fails_when_ac_trace_missing():
    """AC-FR1100-01: missing AC trace -> fail."""
    checks = _valid_checks()
    checks["ac_trace"] = False
    report = evaluate_final_gate(_valid_lineage(), checks)
    assert report.status == "fail"
    assert "ac_trace" in report.failed


@pytest.mark.real_module
def test_evaluate_final_gate_fails_when_generated_files_unexpected():
    """AC-FR1100-01: unexpected generated files -> fail."""
    checks = _valid_checks()
    checks["generated_files"] = False
    report = evaluate_final_gate(_valid_lineage(), checks)
    assert report.status == "fail"
    assert "generated_files" in report.failed


@pytest.mark.real_module
def test_evaluate_final_gate_fails_when_external_diff_unattributed():
    """AC-FR1100-01: unattributed external diff -> fail."""
    checks = _valid_checks()
    checks["external_diff"] = False
    report = evaluate_final_gate(_valid_lineage(), checks)
    assert report.status == "fail"
    assert "external_diff" in report.failed


@pytest.mark.real_module
def test_evaluate_final_gate_fails_when_anti_pattern_detected():
    """AC-FR1100-01: anti-pattern in tests/code -> fail."""
    checks = _valid_checks()
    checks["anti_pattern"] = False
    report = evaluate_final_gate(_valid_lineage(), checks)
    assert report.status == "fail"
    assert "anti_pattern" in report.failed


@pytest.mark.real_module
def test_evaluate_final_gate_fails_when_dependency_violated():
    """AC-FR1100-01: dependency violation -> fail."""
    checks = _valid_checks()
    checks["dependency"] = False
    report = evaluate_final_gate(_valid_lineage(), checks)
    assert report.status == "fail"
    assert "dependency" in report.failed


# ---------------------------------------------------------------------------
# TaskCompletionGate
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_can_complete_true_when_program_and_prism_pass_current():
    """AC-FR1100-01: program PASS + Prism PASS current -> can complete."""
    gate = TaskCompletionGate()
    gate.attach_prism_review(_valid_lineage(), _valid_verdict())
    assert gate.can_complete(_valid_lineage(), _valid_checks()) is True


@pytest.mark.real_module
def test_can_complete_false_when_program_fails():
    """AC-FR1100-01: Agent self-report / commit doesn't count; gate must PASS."""
    gate = TaskCompletionGate()
    gate.attach_prism_review(_valid_lineage(), _valid_verdict())
    checks = _valid_checks()
    checks["scope"] = False
    assert gate.can_complete(_valid_lineage(), checks) is False


@pytest.mark.real_module
def test_can_complete_false_when_no_prism_review():
    """AC-FR1100-01: no Prism review -> cannot complete."""
    gate = TaskCompletionGate()
    assert gate.can_complete(_valid_lineage(), _valid_checks()) is False


@pytest.mark.real_module
def test_can_complete_false_when_prism_revise():
    """AC-FR1100-01: REVISE verdict -> cannot complete."""
    gate = TaskCompletionGate()
    verdict = PrismFinalVerdict(
        review_id="rev-1",
        subject_oid="g" * 40,
        verdict="REVISE",
    )
    gate.attach_prism_review(_valid_lineage(), verdict)
    assert gate.can_complete(_valid_lineage(), _valid_checks()) is False


@pytest.mark.real_module
def test_can_complete_false_when_lineage_drifts_from_review():
    """AC-FR1100-01: Red lineage change -> prior PASS stale; cannot complete."""
    gate = TaskCompletionGate()
    gate.attach_prism_review(_valid_lineage(), _valid_verdict())
    # Drift: new R OID.
    drifted = FinalLineage(
        baseline_oid="b" * 40,
        red_oid="r2" + "r" * 38,
        green_oid="g" * 40,
    )
    assert gate.can_complete(drifted, _valid_checks()) is False


@pytest.mark.real_module
def test_can_complete_with_refactor_oid_as_subject():
    """AC-FR1100-01: when F exists, review subject is F (not G)."""
    lineage_f = FinalLineage(
        baseline_oid="b" * 40,
        red_oid="r" * 40,
        green_oid="g" * 40,
        refactor_oid="f" * 40,
    )
    gate = TaskCompletionGate()
    verdict = PrismFinalVerdict(
        review_id="rev-1",
        subject_oid="f" * 40,
        verdict="PASS",
    )
    gate.attach_prism_review(lineage_f, verdict)
    assert gate.can_complete(lineage_f, _valid_checks()) is True


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-FR1100-01: ERROR_CODES includes all codes from interfaces.md §4."""
    expected = {
        "RGR_FINAL_GATE_FAILED",
        "RGR_LINEAGE_INVALID",
        "RGR_RED_REVIEW_NOT_CURRENT",
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
