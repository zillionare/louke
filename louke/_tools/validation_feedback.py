"""NFR-0500: validation feedback operability.

Program validation failures return a stable check ID, artifact path/field,
expected vs actual, related FR/AC/contract/prompt identity and retryability
- never a generic 'invalid design' string.  The UI/API must let users
navigate from the result to the failing artifact anchor (AC-NFR0500-01).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ERROR_CODES = (
    "FEEDBACK_NOT_ACTIONABLE",
    "FEEDBACK_MISSING_CHECK_ID",
    "FEEDBACK_MISSING_ARTIFACT_PATH",
    "FEEDBACK_MISSING_EXPECTED_ACTUAL",
)

_GENERIC_MESSAGES = (
    "invalid design",
    "design invalid",
    "validation failed",
    "schema invalid",
)


class FeedbackError(Exception):
    """A fail-closed validation feedback rejection carrying a stable code."""

    __test__ = False

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ValidationFeedback:
    """A validation feedback record (AC-NFR0500-01).

    Attributes:
        check_id: Stable check identifier (e.g. ``DESIGN.TRACE.CLOSURE``).
        artifact_path: Path to the failing artifact.
        field: Field or JSON pointer within the artifact.
        expected: The expected value.
        actual: The actual value (redacted for secrets).
        fr_ids: Tuple of related FR ids.
        ac_ids: Tuple of related AC ids.
        contract_refs: Tuple of related contract kinds.
        prompt_identity: Optional prompt bundle identity.
        retryable: ``True`` if the failure can be retried after fixing.
        remediation: Human-readable remediation guidance.
    """

    check_id: str
    artifact_path: str
    field: str
    expected: Any
    actual: Any
    fr_ids: tuple[str, ...]
    ac_ids: tuple[str, ...]
    contract_refs: tuple[str, ...]
    prompt_identity: str | None
    retryable: bool
    remediation: str


def build_feedback(
    *,
    check_id: str,
    artifact_path: str,
    field: str,
    expected: Any,
    actual: Any,
    fr_ids: tuple[str, ...],
    ac_ids: tuple[str, ...],
    contract_refs: tuple[str, ...],
    prompt_identity: str | None,
    retryable: bool,
    remediation: str,
) -> ValidationFeedback:
    """Build a :class:`ValidationFeedback` record."""
    return ValidationFeedback(
        check_id=check_id,
        artifact_path=artifact_path,
        field=field,
        expected=expected,
        actual=actual,
        fr_ids=fr_ids,
        ac_ids=ac_ids,
        contract_refs=contract_refs,
        prompt_identity=prompt_identity,
        retryable=retryable,
        remediation=remediation,
    )


def verify_actionable_feedback(feedback: ValidationFeedback) -> None:
    """Verify a feedback record is actionable (AC-NFR0500-01).

    Args:
        feedback: The feedback record to verify.

    Raises:
        FeedbackError: With a stable code if the feedback is not actionable.
    """
    if not feedback.check_id:
        raise FeedbackError(
            "FEEDBACK_MISSING_CHECK_ID",
            "feedback record has no stable check_id",
        )
    if not feedback.artifact_path:
        raise FeedbackError(
            "FEEDBACK_MISSING_ARTIFACT_PATH",
            f"feedback {feedback.check_id} has no artifact_path",
        )
    if feedback.expected is None and feedback.actual is None:
        raise FeedbackError(
            "FEEDBACK_MISSING_EXPECTED_ACTUAL",
            f"feedback {feedback.check_id} has neither expected nor actual",
        )
    remediation_lower = (feedback.remediation or "").lower()
    for generic in _GENERIC_MESSAGES:
        if remediation_lower == generic:
            raise FeedbackError(
                "FEEDBACK_NOT_ACTIONABLE",
                f"feedback {feedback.check_id} has generic remediation {generic!r}",
            )


def feedback_to_dict(feedback: ValidationFeedback) -> dict[str, Any]:
    """Serialise feedback to a dict for UI/API display."""
    return {
        "check_id": feedback.check_id,
        "artifact_path": feedback.artifact_path,
        "field": feedback.field,
        "expected": feedback.expected,
        "actual": feedback.actual,
        "fr_ids": list(feedback.fr_ids),
        "ac_ids": list(feedback.ac_ids),
        "contract_refs": list(feedback.contract_refs),
        "prompt_identity": feedback.prompt_identity,
        "retryable": feedback.retryable,
        "remediation": feedback.remediation,
    }
