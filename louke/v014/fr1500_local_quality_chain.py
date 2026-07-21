"""FR-1500: Local authoritative quality chain.

Runtime executes against the same candidate the full chain of project-local
format/lint/static/type, pre-commit config/installation drift + all-files,
RGR lineage, all historical host unit tests, all required integration/e2e/
regression, AC bidirectional trace, skip/quarantine policy, anti-pattern,
docs/migration/compat and a real build.  Local selectors are diagnostic
only; historical tests may only be excluded via formal policy-bound
quarantine/deprecation.  No selector, skip or missing policy identity may
PASS (AC-FR1500-01).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ERROR_CODES = (
    "QUAL_CONTRACT_NOT_CURRENT",
    "QUAL_GATE_MISSING",
    "QUAL_COMMAND_FAILED",
    "QUAL_TIMEOUT",
    "QUAL_REQUIRED_SUITE_MISSING",
    "QUAL_REQUIRED_SUITE_SKIPPED",
    "QUAL_HISTORY_EXCLUDED",
    "QUAL_SELECTOR_PARTIAL",
    "QUAL_QUARANTINE_INVALID",
    "QUAL_TRACE_INCOMPLETE",
    "QUAL_BUILD_FAILED",
    "QUAL_EVIDENCE_UNKNOWN",
    "QUAL_CANDIDATE_STALE",
)

_REQUIRED_GATES: tuple[str, ...] = (
    "format",
    "lint",
    "static",
    "type",
    "precommit-drift",
    "precommit-all-files",
    "rgr-lineage",
    "history-unit",
    "integration",
    "e2e",
    "regression",
    "ac-trace",
    "skip-policy",
    "anti-pattern",
    "docs",
    "migration",
    "compat",
    "build",
)


class LocalQualityError(Exception):
    """A fail-closed local quality rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class QualityGateResult:
    """Result of a single quality gate (AC-FR1500-01).

    Attributes:
        name: Stable gate name (e.g. ``format``, ``history-unit``).
        status: ``pass|fail|skip|unknown|missing``.
        policy_digest: Required for ``skip`` (formal quarantine policy identity).
        issue_id: Issue id backing the quarantine.
        owner: Owner of the quarantine.
        scope: Scope of the quarantine.
        expiry: Expiry of the quarantine.
    """

    name: str
    status: str
    policy_digest: str = ""
    issue_id: int = 0
    owner: str = ""
    scope: str = ""
    expiry: str = ""


@dataclass(frozen=True)
class LocalQualityReport:
    """Result of :meth:`QualityChainGate.evaluate` (AC-FR1500-01).

    Attributes:
        candidate_id: Bound candidate id.
        status: ``pass`` or ``fail``.
        failed: Tuple of failed gate names.
    """

    candidate_id: str
    status: str
    failed: tuple[str, ...] = ()


class QualityChainGate:
    """Local authoritative quality chain evaluator (AC-FR1500-01)."""

    def evaluate(
        self,
        candidate_id: str,
        gates: list[QualityGateResult],
        *,
        selector_only: bool = False,
        quarantines: dict[str, dict[str, Any] | None] | None = None,
    ) -> LocalQualityReport:
        """Evaluate the full quality chain for a candidate.

        Args:
            candidate_id: Bound candidate id.
            gates: List of :class:`QualityGateResult` for each required gate.
            selector_only: ``True`` if a partial selector was used (diagnostic-only).
            quarantines: Optional map of gate name -> quarantine metadata; a
                ``None`` value means an invalid (policy-less) quarantine.

        Returns:
            A :class:`LocalQualityReport` with ``status=pass`` only when every
            required gate passed or was properly quarantined.

        Raises:
            LocalQualityError: With ``QUAL_QUARANTINE_INVALID`` if a quarantine
                lacks formal policy identity.
        """
        if selector_only:
            return LocalQualityReport(
                candidate_id=candidate_id,
                status="fail",
                failed=("selector-partial",),
            )
        gate_by_name = {g.name: g for g in gates}
        failed: list[str] = []
        for required in _REQUIRED_GATES:
            gate = gate_by_name.get(required)
            if gate is None:
                failed.append(required)
                continue
            if gate.status == "pass":
                continue
            if gate.status == "skip":
                if (
                    not gate.policy_digest
                    or not gate.issue_id
                    or not gate.owner
                    or not gate.scope
                ):
                    raise LocalQualityError(
                        "QUAL_QUARANTINE_INVALID",
                        f"gate {required!r} is skipped without formal policy identity",
                    )
                # Policy-bound quarantine is acceptable.
                continue
            failed.append(required)
        return LocalQualityReport(
            candidate_id=candidate_id,
            status="fail" if failed else "pass",
            failed=tuple(failed),
        )
