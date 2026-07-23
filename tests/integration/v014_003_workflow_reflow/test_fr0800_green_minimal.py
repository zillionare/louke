"""Integration tests for FR-0800: Green minimal implementation & Red test
protection.

AC-FR0800-01: Green workspace is restored from the approved ``R`` tree;
Devon may only add the minimal code to pass Red within the authorised
implementation scope. Runtime's target tests, all historical unit tests
and applicable static/contract checks must all PASS. Deleting/weakening/
rewriting ``R`` tests, skipping historical failures, or violating design
contracts blocks Green; legitimate test corrections must return to a
new Red review.

Interfaces covered (per interfaces.md):
- IF-RGR-01 (Primary ARC-05)
- IF-QUAL-01 (quality chain, ARC-10)
"""
# AC-FR0800-01

from __future__ import annotations

import pytest

from louke.runtime.green_minimal import (
    ERROR_CODES,
    GreenAttempt,
    GreenCheck,
    GreenChecksError,
    GreenChecksReport,
    GreenPatch,
    build_green_attempt,
    evaluate_green_checks,
)


def _valid_patch() -> GreenPatch:
    return GreenPatch(
        diff_paths=("louke/v014/fr0100_m_impl_entry.py",),
        test_deleted=False,
        test_weakened=False,
        implementation_added=True,
        design_contract_change=False,
    )


# ---------------------------------------------------------------------------
# build_green_attempt
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_build_green_attempt_restores_reviewed_r_tree():
    """AC-FR0800-01: workspace_tree_oid=R; branch_oid=B (unchanged)."""
    attempt = build_green_attempt(
        run_id="run-001",
        task_id="T-001",
        attempt_no=1,
        baseline_oid="b" * 40,
        reviewed_red_oid="r" * 40,
        patch=_valid_patch(),
    )
    assert isinstance(attempt, GreenAttempt)
    assert attempt.workspace_tree_oid == "r" * 40  # restored from R
    assert attempt.branch_oid == "b" * 40  # release branch unchanged
    assert attempt.reviewed_red_oid == "r" * 40


@pytest.mark.real_module
def test_build_green_attempt_rejects_test_deletion():
    """AC-FR0800-01: deleting R tests -> RGR_TEST_MUTATED."""
    p = GreenPatch(
        diff_paths=_valid_patch().diff_paths,
        test_deleted=True,
        test_weakened=False,
        implementation_added=True,
        design_contract_change=False,
    )
    with pytest.raises(GreenChecksError) as exc:
        build_green_attempt(
            run_id="run-001",
            task_id="T-001",
            attempt_no=1,
            baseline_oid="b" * 40,
            reviewed_red_oid="r" * 40,
            patch=p,
        )
    assert exc.value.code == "RGR_TEST_MUTATED"


@pytest.mark.real_module
def test_build_green_attempt_rejects_test_weakening():
    """AC-FR0800-01: weakening R tests -> RGR_TEST_MUTATED."""
    p = GreenPatch(
        diff_paths=_valid_patch().diff_paths,
        test_deleted=False,
        test_weakened=True,
        implementation_added=True,
        design_contract_change=False,
    )
    with pytest.raises(GreenChecksError) as exc:
        build_green_attempt(
            run_id="run-001",
            task_id="T-001",
            attempt_no=1,
            baseline_oid="b" * 40,
            reviewed_red_oid="r" * 40,
            patch=p,
        )
    assert exc.value.code == "RGR_TEST_MUTATED"


@pytest.mark.real_module
def test_build_green_attempt_rejects_design_contract_change():
    """AC-FR0800-01: design/contract change -> RGR_REFACTOR_CONTRACT_CHANGED
    (must return upstream, not Green)."""
    p = GreenPatch(
        diff_paths=_valid_patch().diff_paths,
        test_deleted=False,
        test_weakened=False,
        implementation_added=True,
        design_contract_change=True,
    )
    with pytest.raises(GreenChecksError) as exc:
        build_green_attempt(
            run_id="run-001",
            task_id="T-001",
            attempt_no=1,
            baseline_oid="b" * 40,
            reviewed_red_oid="r" * 40,
            patch=p,
        )
    assert exc.value.code == "RGR_REFACTOR_CONTRACT_CHANGED"


@pytest.mark.real_module
def test_build_green_attempt_rejects_no_implementation_added():
    """AC-FR0800-01: no implementation code -> RGR_GREEN_SCOPE_DENIED."""
    p = GreenPatch(
        diff_paths=_valid_patch().diff_paths,
        test_deleted=False,
        test_weakened=False,
        implementation_added=False,
        design_contract_change=False,
    )
    with pytest.raises(GreenChecksError) as exc:
        build_green_attempt(
            run_id="run-001",
            task_id="T-001",
            attempt_no=1,
            baseline_oid="b" * 40,
            reviewed_red_oid="r" * 40,
            patch=p,
        )
    assert exc.value.code == "RGR_GREEN_SCOPE_DENIED"


# ---------------------------------------------------------------------------
# evaluate_green_checks
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_evaluate_green_checks_passes_when_all_required_pass():
    """AC-FR0800-01: target + history unit + static + contract + lint + format
    all PASS -> status=pass."""
    checks = [
        GreenCheck("target", True),
        GreenCheck("history-unit", True),
        GreenCheck("static", True),
        GreenCheck("contract", True),
        GreenCheck("lint", True),
        GreenCheck("format", True),
    ]
    report = evaluate_green_checks(checks)
    assert isinstance(report, GreenChecksReport)
    assert report.status == "pass"
    assert report.failed_checks == ()


@pytest.mark.real_module
def test_evaluate_green_checks_fails_when_history_unit_fails():
    """AC-FR0800-01: historical unit failure cannot be skipped (must PASS)."""
    checks = [
        GreenCheck("target", True),
        GreenCheck("history-unit", False, "skip not allowed"),
        GreenCheck("static", True),
        GreenCheck("contract", True),
        GreenCheck("lint", True),
        GreenCheck("format", True),
    ]
    report = evaluate_green_checks(checks)
    assert report.status == "fail"
    assert len(report.failed_checks) == 1
    assert report.failed_checks[0].name == "history-unit"


@pytest.mark.real_module
def test_evaluate_green_checks_fails_when_any_check_fails():
    """AC-FR0800-01: any check failure -> status=fail with all failed checks."""
    checks = [
        GreenCheck("target", True),
        GreenCheck("history-unit", True),
        GreenCheck("static", False, "type error"),
        GreenCheck("contract", False, "scope breach"),
        GreenCheck("lint", True),
        GreenCheck("format", True),
    ]
    report = evaluate_green_checks(checks)
    assert report.status == "fail"
    failed_names = {c.name for c in report.failed_checks}
    assert failed_names == {"static", "contract"}


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-FR0800-01: ERROR_CODES includes all codes from interfaces.md §4."""
    expected = {
        "RGR_TEST_MUTATED",
        "RGR_GREEN_SCOPE_DENIED",
        "RGR_HISTORY_TEST_FAILED",
        "RGR_REFACTOR_CONTRACT_CHANGED",
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
