"""AC-FR0800-01: Green minimal implementation & Red test protection.

Entering Green, Runtime restores the precise reviewed ``R`` tree; the
release branch remains ``B``.  Devon may only add the minimal code that
makes the Red tests pass, following current design/CI contracts.  The
``R`` tests must not be deleted, weakened or rewritten; corrections must
return to Red.  Runtime independently runs target tests, all historical
host unit tests, applicable lint/format/type/static and task contract
checks; historical failures may not be skipped.
"""

from __future__ import annotations


import pytest

from louke.runtime.green_minimal import (
    GreenAttempt,
    GreenCheck,
    GreenChecksError,
    GreenPatch,
    build_green_attempt,
    evaluate_green_checks,
)

_B = "b" * 40
_R = "r" * 40


def _patch(
    *,
    diff_paths: tuple[str, ...] = ("louke/v014/x.py",),
    test_deleted: bool = False,
    test_weakened: bool = False,
    implementation_added: bool = True,
    design_contract_change: bool = False,
) -> GreenPatch:
    return GreenPatch(
        diff_paths=diff_paths,
        test_deleted=test_deleted,
        test_weakened=test_weakened,
        implementation_added=implementation_added,
        design_contract_change=design_contract_change,
    )


def _checks(
    *,
    target_pass: bool = True,
    history_pass: bool = True,
    static_pass: bool = True,
    contract_pass: bool = True,
    lint_pass: bool = True,
    format_pass: bool = True,
) -> list[GreenCheck]:
    return [
        GreenCheck(name="target", passed=target_pass),
        GreenCheck(name="history-unit", passed=history_pass),
        GreenCheck(name="static", passed=static_pass),
        GreenCheck(name="contract", passed=contract_pass),
        GreenCheck(name="lint", passed=lint_pass),
        GreenCheck(name="format", passed=format_pass),
    ]


def test_build_green_attempt_restores_reviewed_r_tree() -> None:
    """AC-FR0800-01: Green workspace restores the reviewed R tree; branch stays B."""
    attempt = build_green_attempt(
        run_id="run-1",
        task_id="t-001",
        attempt_no=1,
        baseline_oid=_B,
        reviewed_red_oid=_R,
        patch=_patch(),
    )
    assert isinstance(attempt, GreenAttempt)
    assert attempt.workspace_tree_oid == _R
    assert attempt.branch_oid == _B  # release branch unchanged


def test_build_green_attempt_rejects_test_deletion() -> None:
    """AC-FR0800-01: deleting R tests blocks Green."""
    with pytest.raises(GreenChecksError) as exc:
        build_green_attempt(
            run_id="run-1",
            task_id="t-001",
            attempt_no=1,
            baseline_oid=_B,
            reviewed_red_oid=_R,
            patch=_patch(test_deleted=True),
        )
    assert exc.value.code == "RGR_TEST_MUTATED"


def test_build_green_attempt_rejects_test_weakening() -> None:
    """AC-FR0800-01: weakening R tests blocks Green."""
    with pytest.raises(GreenChecksError) as exc:
        build_green_attempt(
            run_id="run-1",
            task_id="t-001",
            attempt_no=1,
            baseline_oid=_B,
            reviewed_red_oid=_R,
            patch=_patch(test_weakened=True),
        )
    assert exc.value.code == "RGR_TEST_MUTATED"


def test_build_green_attempt_rejects_design_contract_change() -> None:
    """AC-FR0800-01: changing design/contract during Green requires return upstream."""
    with pytest.raises(GreenChecksError) as exc:
        build_green_attempt(
            run_id="run-1",
            task_id="t-001",
            attempt_no=1,
            baseline_oid=_B,
            reviewed_red_oid=_R,
            patch=_patch(design_contract_change=True),
        )
    assert exc.value.code == "RGR_REFACTOR_CONTRACT_CHANGED"


def test_evaluate_green_checks_passes_when_all_required_pass() -> None:
    """AC-FR0800-01: target + all history unit + static + contract all PASS."""
    report = evaluate_green_checks(_checks())
    assert report.status == "pass"
    assert len(report.failed_checks) == 0


def test_evaluate_green_checks_fails_when_history_unit_fails() -> None:
    """AC-FR0800-01: historical unit failures may not be skipped."""
    report = evaluate_green_checks(_checks(history_pass=False))
    assert report.status == "fail"
    assert any(c.name == "history-unit" for c in report.failed_checks)


def test_evaluate_green_checks_fails_when_target_fails() -> None:
    """AC-FR0800-01: target test failure blocks Green."""
    report = evaluate_green_checks(_checks(target_pass=False))
    assert report.status == "fail"
    assert any(c.name == "target" for c in report.failed_checks)


def test_evaluate_green_checks_fails_when_contract_fails() -> None:
    """AC-FR0800-01: contract check failure blocks Green."""
    report = evaluate_green_checks(_checks(contract_pass=False))
    assert report.status == "fail"
    assert any(c.name == "contract" for c in report.failed_checks)


def test_green_attempt_requires_implementation_added() -> None:
    """AC-FR0800-01: Green must add minimal implementation to pass Red tests."""
    with pytest.raises(GreenChecksError) as exc:
        build_green_attempt(
            run_id="run-1",
            task_id="t-001",
            attempt_no=1,
            baseline_oid=_B,
            reviewed_red_oid=_R,
            patch=_patch(implementation_added=False),
        )
    assert exc.value.code == "RGR_GREEN_SCOPE_DENIED"
