"""Integration tests for FR-1700: GitHub candidate CI & required rule.

AC-FR1700-01: The precise candidate's GitHub run/job/evidence can prove
that the managed ``.github/workflows/louke-ci.yml`` actually executes
the host's full historical unit suites and all currently contracted
required integration/e2e suites. Only after all execution evidence
covers those required suites AND that commit's ``Louke CI / required``
required jobs succeed may Runtime PASS. Missing/excluded/illegal-skip
of any required suite, or job failure/cancel/timeout/missing/unknown,
prevents the aggregated check from PASSing; same-name green checks
from other SHAs are rejected. Runtime idempotently reconciles its own
ruleset/branch protection and reads back, preserving user rules;
permission/network/partial/capability issues enter needs_attention.

Interfaces covered (per interfaces.md):
- IF-CI-02 (Primary ARC-11)
- IF-CI-01 (inherited, ARC-11)
- IF-TEST-02 (suite inventory, ARC-08)
"""
# AC-FR1700-01

from __future__ import annotations

import pytest

from louke.runtime.github_ci import (
    ERROR_CODES,
    CIReport,
    GitHubCIGate,
    JobResult,
    RulesReconcileResult,
    SuiteCoverage,
)


_REQUIRED_JOBS = (
    "quality",
    "workflow-contract",
    "ac-trace",
    "build-artifacts",
    "artifact-verify",
    "unit",
    "integration",
    "e2e-standin",
    "ci-e2e",
    "security",
)
_REQUIRED_SUITES = (
    "tests/unit",
    "tests/integration/v014_003_workflow_reflow",
    "tests/e2e/v014_003_workflow_reflow",
)


def _gate() -> GitHubCIGate:
    return GitHubCIGate(
        required_jobs=_REQUIRED_JOBS,
        required_suites=_REQUIRED_SUITES,
    )


def _all_success_jobs() -> list[JobResult]:
    return [JobResult(name=n, status="success") for n in _REQUIRED_JOBS]


def _full_coverage() -> SuiteCoverage:
    return SuiteCoverage(
        required_suites=_REQUIRED_SUITES,
        executed_suites=_REQUIRED_SUITES,
        illegal_skips=(),
        complete=True,
    )


# ---------------------------------------------------------------------------
# evaluate
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_evaluate_passes_when_all_required_jobs_success_and_coverage_complete():
    """AC-FR1700-01: all required jobs success + coverage complete -> pass."""
    gate = _gate()
    report = gate.evaluate(
        candidate_oid="c" * 40,
        commit_oid="c" * 40,
        jobs=_all_success_jobs(),
        coverage=_full_coverage(),
        required_check_status="success",
    )
    assert isinstance(report, CIReport)
    assert report.status == "pass"
    assert report.reasons == ()


@pytest.mark.real_module
def test_evaluate_fails_when_commit_mismatches_candidate():
    """AC-FR1700-01: green check from other SHA -> CI_COMMIT_MISMATCH."""
    report = _gate().evaluate(
        candidate_oid="c" * 40,
        commit_oid="x" * 40,  # different
        jobs=_all_success_jobs(),
        coverage=_full_coverage(),
        required_check_status="success",
    )
    assert report.status == "fail"
    assert "CI_COMMIT_MISMATCH" in report.reasons


@pytest.mark.real_module
def test_evaluate_fails_when_required_job_missing():
    """AC-FR1700-01: missing required job -> CI_REQUIRED_JOB_MISSING."""
    jobs = [j for j in _all_success_jobs() if j.name != "security"]
    report = _gate().evaluate(
        candidate_oid="c" * 40,
        commit_oid="c" * 40,
        jobs=jobs,
        coverage=_full_coverage(),
        required_check_status="success",
    )
    assert report.status == "fail"
    assert "CI_REQUIRED_JOB_MISSING" in report.reasons


@pytest.mark.real_module
def test_evaluate_fails_when_required_job_not_success():
    """AC-FR1700-01: job failure/cancel/timeout/skip/unknown -> not PASS."""
    for bad_status in (
        "failure",
        "cancelled",
        "timed_out",
        "skipped",
        "neutral",
        "unknown",
    ):
        jobs = _all_success_jobs()
        jobs = [
            JobResult(name=j.name, status=bad_status) if j.name == "unit" else j
            for j in jobs
        ]
        report = _gate().evaluate(
            candidate_oid="c" * 40,
            commit_oid="c" * 40,
            jobs=jobs,
            coverage=_full_coverage(),
            required_check_status="success",
        )
        assert report.status == "fail", f"status {bad_status} should fail"
        assert "CI_REQUIRED_JOB_NOT_SUCCESS" in report.reasons


@pytest.mark.real_module
def test_evaluate_fails_when_required_suite_illegally_skipped():
    """AC-FR1700-01: illegal skip of required suite -> fail."""
    coverage = SuiteCoverage(
        required_suites=_REQUIRED_SUITES,
        executed_suites=_REQUIRED_SUITES[:2],  # missing one
        illegal_skips=(_REQUIRED_SUITES[2],),
        complete=False,
    )
    report = _gate().evaluate(
        candidate_oid="c" * 40,
        commit_oid="c" * 40,
        jobs=_all_success_jobs(),
        coverage=coverage,
        required_check_status="success",
    )
    assert report.status == "fail"
    assert "CI_REQUIRED_SUITE_SKIPPED" in report.reasons


@pytest.mark.real_module
def test_evaluate_fails_when_suite_coverage_incomplete():
    """AC-FR1700-01: required suite missing execution -> CI_SUITE_COVERAGE_INCOMPLETE."""
    coverage = SuiteCoverage(
        required_suites=_REQUIRED_SUITES,
        executed_suites=_REQUIRED_SUITES[:1],
        illegal_skips=(),
        complete=False,
    )
    report = _gate().evaluate(
        candidate_oid="c" * 40,
        commit_oid="c" * 40,
        jobs=_all_success_jobs(),
        coverage=coverage,
        required_check_status="success",
    )
    assert report.status == "fail"
    assert "CI_SUITE_COVERAGE_INCOMPLETE" in report.reasons


@pytest.mark.real_module
def test_evaluate_fails_when_aggregated_check_not_success():
    """AC-FR1700-01: aggregated Louke CI / required must be success;
    unknown -> needs_attention."""
    report = _gate().evaluate(
        candidate_oid="c" * 40,
        commit_oid="c" * 40,
        jobs=_all_success_jobs(),
        coverage=_full_coverage(),
        required_check_status="unknown",
    )
    assert report.status == "fail"
    assert "CI_API_UNKNOWN" in report.reasons

    report2 = _gate().evaluate(
        candidate_oid="c" * 40,
        commit_oid="c" * 40,
        jobs=_all_success_jobs(),
        coverage=_full_coverage(),
        required_check_status="failure",
    )
    assert report2.status == "fail"
    assert "CI_REQUIRED_CHECK_AMBIGUOUS" in report2.reasons


# ---------------------------------------------------------------------------
# reconcile_rules
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_reconcile_rules_in_sync_when_user_rules_preserved():
    """AC-FR1700-01: user rules preserved + Runtime rules match -> in_sync."""
    gate = _gate()
    runtime_rule = {"required_check": {"strict": True}}
    user_rule = {"user-branch-protection": {"enforce_admins": False}}
    before = {**runtime_rule, **user_rule}
    desired = runtime_rule
    actual = {**runtime_rule, **user_rule}  # both preserved
    result = gate.reconcile_rules(before=before, desired=desired, actual=actual)
    assert isinstance(result, RulesReconcileResult)
    assert result.status == "in_sync"
    assert result.user_rules_preserved is True


@pytest.mark.real_module
def test_reconcile_rules_needs_attention_when_user_rule_lost():
    """AC-FR1700-01: user rule missing in actual -> needs_attention."""
    gate = _gate()
    runtime_rule = {"required_check": {"strict": True}}
    user_rule = {"user-branch-protection": {"enforce_admins": False}}
    before = {**runtime_rule, **user_rule}
    desired = runtime_rule
    actual = dict(runtime_rule)  # user rule missing
    result = gate.reconcile_rules(before=before, desired=desired, actual=actual)
    assert result.status == "needs_attention"
    assert result.user_rules_preserved is False
    assert "user-branch-protection" in result.missing_user_rules


@pytest.mark.real_module
def test_reconcile_rules_needs_attention_when_runtime_rule_drifts():
    """AC-FR1700-01: Runtime-owned rule drift -> needs_attention."""
    gate = _gate()
    runtime_rule = {"required_check": {"strict": True}}
    before = dict(runtime_rule)
    desired = runtime_rule
    actual = {"required_check": {"strict": False}}  # drifted
    result = gate.reconcile_rules(before=before, desired=desired, actual=actual)
    assert result.status == "needs_attention"


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-FR1700-01: ERROR_CODES includes all codes from interfaces.md §9."""
    expected = {
        "CI_CONTRACT_NOT_CURRENT",
        "CI_PUSH_CONFLICT",
        "CI_WORKFLOW_MISMATCH",
        "CI_RUN_NOT_FOUND",
        "CI_RUN_AMBIGUOUS",
        "CI_COMMIT_MISMATCH",
        "CI_REQUIRED_JOB_MISSING",
        "CI_REQUIRED_JOB_NOT_SUCCESS",
        "CI_SUITE_COVERAGE_INCOMPLETE",
        "CI_REQUIRED_CHECK_AMBIGUOUS",
        "CI_RULE_CAPABILITY_MISSING",
        "CI_RULE_READBACK_MISMATCH",
        "CI_API_UNKNOWN",
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
