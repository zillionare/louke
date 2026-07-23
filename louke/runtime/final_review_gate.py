"""FR-1100: Final task review & completion gate.

Runtime validates the final formal commit range's scope, dependencies,
secret, generated files, AC trace, anti-pattern, external diff and
current ``B/R/G/(Refactor)`` lineage.  Prism independently reviews the
complete code, test truthfulness, design/CI consistency and
maintainability.  Corrections that change Red tests must return to a new
Red lineage.  A task only completes when both program gates and the
current Prism PASS; Agent self-report, commits or pushes do not
constitute a gate (AC-FR1100-01).
"""

from __future__ import annotations

from dataclasses import dataclass

ERROR_CODES = (
    "RGR_FINAL_GATE_FAILED",
    "RGR_LINEAGE_INVALID",
    "RGR_RED_REVIEW_NOT_CURRENT",
)


class FinalGateError(Exception):
    """A fail-closed final gate rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class FinalLineage:
    """The final ``B/R/G/(F)`` lineage evidence (AC-FR1100-01).

    Attributes:
        baseline_oid: ``B`` commit OID.
        red_oid: ``R`` commit OID (private).
        green_oid: ``G`` commit OID.
        refactor_oid: Optional ``F`` commit OID.
    """

    baseline_oid: str
    red_oid: str
    green_oid: str
    refactor_oid: str | None = None


@dataclass(frozen=True)
class FinalGateReport:
    """Result of :func:`evaluate_final_gate`.

    Attributes:
        status: ``pass`` or ``fail``.
        failed: Tuple of check names that failed.
    """

    status: str
    failed: tuple[str, ...] = ()


def evaluate_final_gate(
    lineage: FinalLineage, checks: dict[str, bool]
) -> FinalGateReport:
    """Evaluate the final program gate (AC-FR1100-01).

    Args:
        lineage: :class:`FinalLineage` for the task.
        checks: Mapping of check name -> passed for scope/secret/ac_trace/
            generated_files/external_diff/anti_pattern/dependency.

    Returns:
        A :class:`FinalGateReport` with ``status=pass`` only when every
        required check passed.
    """
    required = (
        "scope",
        "secret",
        "ac_trace",
        "generated_files",
        "external_diff",
        "anti_pattern",
        "dependency",
    )
    failed = tuple(name for name in required if not checks.get(name, False))
    return FinalGateReport(status="fail" if failed else "pass", failed=failed)


@dataclass(frozen=True)
class PrismFinalVerdict:
    """A Prism final review verdict (AC-FR1100-01).

    Attributes:
        review_id: Stable review identity.
        subject_oid: The commit OID the review is bound to (``G`` or ``F``).
        verdict: ``PASS|REVISE``.
        status: ``current`` (default) or ``stale`` once lineage changes.
    """

    review_id: str
    subject_oid: str
    verdict: str
    status: str = "current"


class TaskCompletionGate:
    """Program gate + Prism review store for final task completion (AC-FR1100-01)."""

    def __init__(self) -> None:
        self._reviews: dict[str, PrismFinalVerdict] = {}
        # Map subject_oid -> lineage signature (B/R/G/F tuple) to detect R drift.
        self._lineage_signature: dict[str, tuple[str, ...]] = {}

    def attach_prism_review(
        self, lineage: FinalLineage, verdict: PrismFinalVerdict
    ) -> None:
        """Attach a Prism final verdict bound to ``lineage``."""
        subject = lineage.refactor_oid or lineage.green_oid
        signature = (
            lineage.baseline_oid,
            lineage.red_oid,
            lineage.green_oid,
            lineage.refactor_oid or "",
        )
        # Mark prior current verdicts as stale.
        for oid, existing in list(self._reviews.items()):
            if oid != subject and existing.status == "current":
                self._reviews[oid] = PrismFinalVerdict(
                    review_id=existing.review_id,
                    subject_oid=existing.subject_oid,
                    verdict=existing.verdict,
                    status="stale",
                )
        self._reviews[subject] = verdict
        self._lineage_signature[subject] = signature

    def can_complete(self, lineage: FinalLineage, checks: dict[str, bool]) -> bool:
        """Return ``True`` only when program gate AND current Prism PASS."""
        report = evaluate_final_gate(lineage, checks)
        if report.status != "pass":
            return False
        subject = lineage.refactor_oid or lineage.green_oid
        verdict = self._reviews.get(subject)
        if verdict is None or verdict.status != "current" or verdict.verdict != "PASS":
            return False
        # Red lineage must match the review's bound lineage signature.
        # If R drifted, the prior PASS is stale.
        expected_signature = (
            lineage.baseline_oid,
            lineage.red_oid,
            lineage.green_oid,
            lineage.refactor_oid or "",
        )
        if self._lineage_signature.get(subject) != expected_signature:
            return False
        # No other review may be current.
        for oid, existing in self._reviews.items():
            if existing.status == "current" and oid != subject:
                return False
        return True
