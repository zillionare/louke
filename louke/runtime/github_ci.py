"""FR-1700: GitHub candidate CI & required rule.

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
capability issues enter ``needs_attention`` (AC-FR1700-01).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ERROR_CODES = (
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
)

_NON_SUCCESS = {
    "failure",
    "cancelled",
    "timed_out",
    "skipped",
    "neutral",
    "action_required",
    "missing",
    "unknown",
}


class GitHubCIError(Exception):
    """A fail-closed GitHub CI rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class JobResult:
    """A single GitHub Actions job result (AC-FR1700-01).

    Attributes:
        name: Job name (must match a required job).
        status: ``success|failure|cancelled|timed_out|skipped|neutral|action_required|missing|unknown``.
    """

    name: str
    status: str


@dataclass(frozen=True)
class SuiteCoverage:
    """Coverage evidence for required suites (AC-FR1700-01).

    Attributes:
        required_suites: Tuple of required suite ids.
        executed_suites: Tuple of suite ids actually executed.
        illegal_skips: Tuple of suite ids that were skipped without policy.
        complete: ``True`` if all required suites were executed.
    """

    required_suites: tuple[str, ...]
    executed_suites: tuple[str, ...]
    illegal_skips: tuple[str, ...]
    complete: bool


@dataclass(frozen=True)
class CIReport:
    """Result of :meth:`GitHubCIGate.evaluate` (AC-FR1700-01).

    Attributes:
        candidate_oid: Bound candidate OID.
        status: ``pass`` or ``fail``.
        reasons: Tuple of stable reason codes.
    """

    candidate_oid: str
    status: str
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class RulesReconcileResult:
    """Result of :meth:`GitHubCIGate.reconcile_rules` (AC-FR1700-01).

    Attributes:
        status: ``in_sync|needs_attention``.
        user_rules_preserved: ``True`` if all user rules were preserved.
        missing_user_rules: Tuple of user rule ids missing from actual.
    """

    status: str
    user_rules_preserved: bool
    missing_user_rules: tuple[str, ...] = ()


class GitHubCIGate:
    """Aggregated GitHub CI gate + rules reconcile (AC-FR1700-01)."""

    def __init__(
        self, *, required_jobs: tuple[str, ...], required_suites: tuple[str, ...]
    ) -> None:
        self._required_jobs = required_jobs
        self._required_suites = required_suites

    def evaluate(
        self,
        *,
        candidate_oid: str,
        commit_oid: str,
        jobs: list[JobResult],
        coverage: SuiteCoverage,
        required_check_status: str,
    ) -> CIReport:
        """Evaluate the GitHub CI gate for a candidate.

        Args:
            candidate_oid: Expected candidate OID.
            commit_oid: Actual commit OID the run is bound to.
            jobs: List of :class:`JobResult` from the GitHub run.
            coverage: :class:`SuiteCoverage` evidence.
            required_check_status: Aggregated ``Louke CI / required`` status.

        Returns:
            A :class:`CIReport` with ``status=pass`` only when every required
            job is ``success``, every required suite is executed without
            illegal skip, commit OID matches candidate OID and aggregated
            check status is ``success``.
        """
        reasons: list[str] = []
        if commit_oid != candidate_oid:
            reasons.append("CI_COMMIT_MISMATCH")
        if required_check_status != "success":
            reasons.append(
                "CI_API_UNKNOWN"
                if required_check_status == "unknown"
                else "CI_REQUIRED_CHECK_AMBIGUOUS"
            )
        job_by_name = {j.name: j for j in jobs}
        for required in self._required_jobs:
            job = job_by_name.get(required)
            if job is None:
                reasons.append("CI_REQUIRED_JOB_MISSING")
            elif job.status != "success":
                reasons.append("CI_REQUIRED_JOB_NOT_SUCCESS")
        if coverage.illegal_skips:
            reasons.append("CI_REQUIRED_SUITE_SKIPPED")
        if not coverage.complete or set(coverage.executed_suites) != set(
            self._required_suites
        ):
            reasons.append("CI_SUITE_COVERAGE_INCOMPLETE")
        return CIReport(
            candidate_oid=candidate_oid,
            status="pass" if not reasons else "fail",
            reasons=tuple(reasons),
        )

    def reconcile_rules(
        self,
        *,
        before: dict[str, dict[str, Any]],
        desired: dict[str, dict[str, Any]],
        actual: dict[str, dict[str, Any]],
    ) -> RulesReconcileResult:
        """Reconcile Runtime-owned rules preserving user rules (AC-FR1700-01).

        Args:
            before: Existing rules before reconcile (Runtime-owned + user).
            desired: Runtime-owned rules to enforce.
            actual: Actual rules after the reconcile attempt.

        Returns:
            A :class:`RulesReconcileResult` with ``status=in_sync`` only when
            every Runtime-owned desired rule is present and matches in
            ``actual``, AND every user rule from ``before`` is preserved in
            ``actual``.
        """
        runtime_keys = set(desired.keys())
        user_keys = set(before.keys()) - runtime_keys
        missing_user = tuple(sorted(k for k in user_keys if k not in actual))
        # Runtime-owned rules must match desired.
        runtime_match = all(actual.get(k) == desired[k] for k in runtime_keys)
        if missing_user or not runtime_match:
            return RulesReconcileResult(
                status="needs_attention",
                user_rules_preserved=not missing_user,
                missing_user_rules=missing_user,
            )
        return RulesReconcileResult(
            status="in_sync",
            user_rules_preserved=True,
        )
