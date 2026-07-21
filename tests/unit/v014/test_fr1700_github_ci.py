"""AC-FR1700-01: GitHub candidate CI & required rule.

Runtime pushes the precise candidate, triggers the managed
``.github/workflows/louke-ci.yml``, and via GitHub API links repository,
workflow revision, commit, run attempt, jobs and artifacts.  The managed
workflow must execute all host historical unit suites and all currently
contracted required integration/e2e against the same candidate.  Only
when execution evidence covers these required suites AND the candidate's
``Louke CI / required`` all required jobs succeed may Runtime PASS.
Any required suite missing/excluded/illegally skipped, job failure/cancel/
timeout/missing/unknown or aggregated-check green-from-other-SHA blocks
PASS.  Runtime idempotently reconciles its own ruleset/branch protection
and readback, preserving user rules; permission/network/partial/
capability issues enter ``needs_attention``.
"""

from __future__ import annotations


from louke.v014.fr1700_github_ci import (
    GitHubCIGate,
    JobResult,
    RulesReconcileResult,
    SuiteCoverage,
)

_CAND_OID = "c" * 40
_OTHER_OID = "x" * 40
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
_REQUIRED_SUITES = ("unit-history", "integration-required", "e2e-required")


def _jobs(
    *, all_success: bool = True, failing: tuple[str, ...] = ()
) -> list[JobResult]:
    return [
        JobResult(
            name=n,
            status="success"
            if all_success and n not in failing
            else ("failure" if n in failing else "success"),
        )
        for n in _REQUIRED_JOBS
    ]


def _coverage(
    *,
    complete: bool = True,
    missing: tuple[str, ...] = (),
    illegal_skips: tuple[str, ...] = (),
) -> SuiteCoverage:
    return SuiteCoverage(
        required_suites=_REQUIRED_SUITES,
        executed_suites=tuple(s for s in _REQUIRED_SUITES if s not in missing),
        illegal_skips=illegal_skips,
        complete=complete,
    )


def test_ci_gate_passes_when_all_required_jobs_success_and_coverage_complete() -> None:
    """AC-FR1700-01: all required jobs success + complete suite coverage -> PASS."""
    gate = GitHubCIGate(required_jobs=_REQUIRED_JOBS, required_suites=_REQUIRED_SUITES)
    report = gate.evaluate(
        candidate_oid=_CAND_OID,
        commit_oid=_CAND_OID,
        jobs=_jobs(),
        coverage=_coverage(),
        required_check_status="success",
    )
    assert report.status == "pass"


def test_ci_gate_fails_when_required_job_missing() -> None:
    """AC-FR1700-01: missing required job fails the gate."""
    gate = GitHubCIGate(required_jobs=_REQUIRED_JOBS, required_suites=_REQUIRED_SUITES)
    jobs = [j for j in _jobs() if j.name != "unit"]
    report = gate.evaluate(
        candidate_oid=_CAND_OID,
        commit_oid=_CAND_OID,
        jobs=jobs,
        coverage=_coverage(),
        required_check_status="success",
    )
    assert report.status == "fail"
    assert "CI_REQUIRED_JOB_MISSING" in report.reasons


def test_ci_gate_fails_when_required_job_failed() -> None:
    """AC-FR1700-01: a failed required job fails the gate even if check is green."""
    gate = GitHubCIGate(required_jobs=_REQUIRED_JOBS, required_suites=_REQUIRED_SUITES)
    report = gate.evaluate(
        candidate_oid=_CAND_OID,
        commit_oid=_CAND_OID,
        jobs=_jobs(failing=("unit",)),
        coverage=_coverage(),
        required_check_status="success",  # check is green but job failed
    )
    assert report.status == "fail"
    assert "CI_REQUIRED_JOB_NOT_SUCCESS" in report.reasons


def test_ci_gate_fails_when_required_suite_excluded() -> None:
    """AC-FR1700-01: missing required suite coverage fails the gate."""
    gate = GitHubCIGate(required_jobs=_REQUIRED_JOBS, required_suites=_REQUIRED_SUITES)
    report = gate.evaluate(
        candidate_oid=_CAND_OID,
        commit_oid=_CAND_OID,
        jobs=_jobs(),
        coverage=_coverage(missing=("unit-history",)),
        required_check_status="success",
    )
    assert report.status == "fail"
    assert "CI_SUITE_COVERAGE_INCOMPLETE" in report.reasons


def test_ci_gate_fails_when_illegal_skip() -> None:
    """AC-FR1700-01: illegal skip of a required suite fails the gate."""
    gate = GitHubCIGate(required_jobs=_REQUIRED_JOBS, required_suites=_REQUIRED_SUITES)
    report = gate.evaluate(
        candidate_oid=_CAND_OID,
        commit_oid=_CAND_OID,
        jobs=_jobs(),
        coverage=_coverage(illegal_skips=("unit-history",)),
        required_check_status="success",
    )
    assert report.status == "fail"
    assert "CI_REQUIRED_SUITE_SKIPPED" in report.reasons


def test_ci_gate_fails_when_commit_mismatches_candidate() -> None:
    """AC-FR1700-01: green check from another SHA does not PASS the candidate."""
    gate = GitHubCIGate(required_jobs=_REQUIRED_JOBS, required_suites=_REQUIRED_SUITES)
    report = gate.evaluate(
        candidate_oid=_CAND_OID,
        commit_oid=_OTHER_OID,  # different SHA
        jobs=_jobs(),
        coverage=_coverage(),
        required_check_status="success",
    )
    assert report.status == "fail"
    assert "CI_COMMIT_MISMATCH" in report.reasons


def test_ci_gate_fails_when_required_check_unknown() -> None:
    """AC-FR1700-01: unknown/missing aggregated check fails the gate."""
    gate = GitHubCIGate(required_jobs=_REQUIRED_JOBS, required_suites=_REQUIRED_SUITES)
    report = gate.evaluate(
        candidate_oid=_CAND_OID,
        commit_oid=_CAND_OID,
        jobs=_jobs(),
        coverage=_coverage(),
        required_check_status="unknown",
    )
    assert report.status == "fail"
    assert "CI_API_UNKNOWN" in report.reasons


def test_rules_reconcile_preserves_user_rules() -> None:
    """AC-FR1700-01: Runtime reconcile preserves user rules; only updates owner-marked fields."""
    gate = GitHubCIGate(required_jobs=_REQUIRED_JOBS, required_suites=_REQUIRED_SUITES)
    result = gate.reconcile_rules(
        before={
            "user-rule-1": {"enforce": "true"},
            "louke-required": {"enforce": "false"},
        },
        desired={"louke-required": {"enforce": "true"}},
        actual={
            "user-rule-1": {"enforce": "true"},
            "louke-required": {"enforce": "true"},
        },
    )
    assert isinstance(result, RulesReconcileResult)
    assert result.status == "in_sync"
    assert result.user_rules_preserved is True


def test_rules_reconcile_needs_attention_on_partial() -> None:
    """AC-FR1700-01: partial rules reconcile enters needs_attention."""
    gate = GitHubCIGate(required_jobs=_REQUIRED_JOBS, required_suites=_REQUIRED_SUITES)
    result = gate.reconcile_rules(
        before={"user-rule-1": {"enforce": "true"}},
        desired={"louke-required": {"enforce": "true"}},
        actual={"louke-required": {"enforce": "false"}},  # missing user rule
    )
    assert result.status == "needs_attention"
