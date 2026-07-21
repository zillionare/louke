"""AC-FR1100-01: Final task review & completion gate.

Runtime validates the final formal commit range's scope, dependencies,
secret, generated files, AC trace, anti-pattern, external diff and
current ``B/R/G/(Refactor)`` lineage.  Prism independently reviews the
complete code, test truthfulness, design/CI consistency and
maintainability.  Corrections that change Red tests must return to a new
Red lineage.  A task only completes when both program gates and the
current Prism PASS; Agent self-report, commits or pushes do not
constitute a gate.
"""

from __future__ import annotations


from louke.v014.fr1100_final_review_gate import (
    FinalGateReport,
    FinalLineage,
    PrismFinalVerdict,
    TaskCompletionGate,
    evaluate_final_gate,
)

_B = "b" * 40
_R = "r" * 40
_G = "g" * 40
_F = "f" * 40


def _lineage(*, refactor_oid: str | None = None) -> FinalLineage:
    return FinalLineage(
        baseline_oid=_B,
        red_oid=_R,
        green_oid=_G,
        refactor_oid=refactor_oid,
    )


def _checks(
    *,
    scope_ok: bool = True,
    secret_ok: bool = True,
    ac_trace_ok: bool = True,
    generated_ok: bool = True,
    external_diff_ok: bool = True,
    anti_pattern_ok: bool = True,
    dependency_ok: bool = True,
) -> dict[str, bool]:
    return {
        "scope": scope_ok,
        "secret": secret_ok,
        "ac_trace": ac_trace_ok,
        "generated_files": generated_ok,
        "external_diff": external_diff_ok,
        "anti_pattern": anti_pattern_ok,
        "dependency": dependency_ok,
    }


def _prism(verdict: str = "PASS") -> PrismFinalVerdict:
    return PrismFinalVerdict(
        review_id="rev-final-1",
        subject_oid=_F if _F else _G,
        verdict=verdict,
        status="current",
    )


def test_evaluate_final_gate_passes_with_all_program_pass() -> None:
    """AC-FR1100-01: program gate passes when all checks pass."""
    report = evaluate_final_gate(_lineage(refactor_oid=_F), _checks())
    assert isinstance(report, FinalGateReport)
    assert report.status == "pass"
    assert len(report.failed) == 0


def test_evaluate_final_gate_fails_for_scope_violation() -> None:
    """AC-FR1100-01: scope violation fails the final gate."""
    report = evaluate_final_gate(_lineage(), _checks(scope_ok=False))
    assert report.status == "fail"
    assert "scope" in report.failed


def test_evaluate_final_gate_fails_for_secret() -> None:
    """AC-FR1100-01: secret in final range fails the gate."""
    report = evaluate_final_gate(_lineage(), _checks(secret_ok=False))
    assert report.status == "fail"
    assert "secret" in report.failed


def test_evaluate_final_gate_fails_for_ac_trace_gap() -> None:
    """AC-FR1100-01: missing AC trace fails the gate."""
    report = evaluate_final_gate(_lineage(), _checks(ac_trace_ok=False))
    assert report.status == "fail"
    assert "ac_trace" in report.failed


def test_evaluate_final_gate_fails_for_external_diff() -> None:
    """AC-FR1100-01: unattributed external diff fails the gate."""
    report = evaluate_final_gate(_lineage(), _checks(external_diff_ok=False))
    assert report.status == "fail"
    assert "external_diff" in report.failed


def test_evaluate_final_gate_fails_for_anti_pattern() -> None:
    """AC-FR1100-01: anti-pattern in tests fails the gate."""
    report = evaluate_final_gate(_lineage(), _checks(anti_pattern_ok=False))
    assert report.status == "fail"
    assert "anti_pattern" in report.failed


def test_completion_gate_requires_program_and_prism_pass() -> None:
    """AC-FR1100-01: task completion requires program gate + current Prism PASS."""
    gate = TaskCompletionGate()
    gate.attach_prism_review(_lineage(refactor_oid=_F), _prism("PASS"))
    assert gate.can_complete(_lineage(refactor_oid=_F), _checks()) is True


def test_completion_gate_fails_when_prism_revise() -> None:
    """AC-FR1100-01: REVISE blocks completion and produces a correction."""
    gate = TaskCompletionGate()
    gate.attach_prism_review(_lineage(refactor_oid=_F), _prism("REVISE"))
    assert gate.can_complete(_lineage(refactor_oid=_F), _checks()) is False


def test_completion_gate_fails_when_program_gate_fails() -> None:
    """AC-FR1100-01: program gate failure blocks completion."""
    gate = TaskCompletionGate()
    gate.attach_prism_review(_lineage(refactor_oid=_F), _prism("PASS"))
    assert (
        gate.can_complete(_lineage(refactor_oid=_F), _checks(scope_ok=False)) is False
    )


def test_completion_gate_fails_when_prism_missing() -> None:
    """AC-FR1100-01: missing Prism verdict blocks completion."""
    gate = TaskCompletionGate()
    assert gate.can_complete(_lineage(refactor_oid=_F), _checks()) is False


def test_red_test_change_must_return_to_new_red_lineage() -> None:
    """AC-FR1100-01: changing Red tests requires a new Red lineage; old review stale."""
    gate = TaskCompletionGate()
    gate.attach_prism_review(_lineage(refactor_oid=_F), _prism("PASS"))
    # If Red tests change, the old review becomes stale.
    new_lineage = FinalLineage(
        baseline_oid=_B,
        red_oid="new-r" + "0" * 38,  # different R
        green_oid=_G,
        refactor_oid=_F,
    )
    assert gate.can_complete(new_lineage, _checks()) is False


def test_agent_self_report_does_not_constitute_gate() -> None:
    """AC-FR1100-01: Agent self-report or commit does not complete the task."""
    gate = TaskCompletionGate()
    # No Prism review attached; agent's own "pass" claim cannot complete.
    assert gate.can_complete(_lineage(refactor_oid=_F), _checks()) is False
