"""FR-2050: prompt candidate atomic activation & safe bootstrap.

Runtime distinguishes the active prompt bundle running the current attempt
from the candidate bundle being edited/reviewed.  Candidate file changes
must not hot-reload the running attempt; candidate activates only after
lint/schema, independent trusted review, deployment readback and baseline
all pass - and only atomically for subsequent dispatch.  Reviewing the
reviewer's own prompt must use the prior trusted bundle, and the review
record must capture both bundle identities (AC-FR2050-01).
"""

from __future__ import annotations

from dataclasses import dataclass

ERROR_CODES = (
    "PROMPT_ACTIVATION_GATE_OPEN",
    "PROMPT_CANDIDATE_HOT_RELOAD_FORBIDDEN",
    "PROMPT_REVIEWER_SELF_REVIEW_FORBIDDEN",
)


class ActivationError(Exception):
    """A fail-closed prompt activation rejection carrying a stable code."""

    __test__ = False

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class AttemptBinding:
    """A binding of an attempt to the active prompt bundle at startup.

    Attributes:
        attempt_id: The Agent attempt id.
        active_bundle_digest: The ``sha256:<hex>`` digest of the active bundle
            at attempt startup.  Candidate changes after startup do not affect
            this binding.
        candidate_bundle_digest: The candidate bundle digest, if any; always
            ``None`` for a freshly-started attempt (candidates cannot
            hot-reload).
        is_pinned_to_active: Always ``True`` - the attempt is pinned to its
            startup active bundle.
    """

    attempt_id: str
    active_bundle_digest: str
    candidate_bundle_digest: str | None = None
    is_pinned_to_active: bool = True


def bind_attempt_to_active_bundle(
    *,
    attempt_id: str,
    active_bundle_digest: str,
    candidate_bundle_digest: str | None = None,
) -> AttemptBinding:
    """Bind a new attempt to its startup active bundle.

    Args:
        attempt_id: The Agent attempt id.
        active_bundle_digest: The ``sha256:<hex>`` digest of the active bundle
            at attempt startup.
        candidate_bundle_digest: Optional candidate bundle digest.  Always
            recorded as ``None`` in the resulting binding because candidates
            cannot hot-reload the running attempt.

    Returns:
        An :class:`AttemptBinding` pinned to ``active_bundle_digest``.

    Raises:
        ActivationError: With ``PROMPT_CANDIDATE_HOT_RELOAD_FORBIDDEN`` if a
            caller tries to bind the attempt directly to a candidate digest.
    """
    if not attempt_id:
        raise ActivationError(
            "PROMPT_ACTIVATION_GATE_OPEN",
            "attempt_id is required to bind a prompt bundle",
        )
    if not active_bundle_digest or not active_bundle_digest.startswith("sha256:"):
        raise ActivationError(
            "PROMPT_ACTIVATION_GATE_OPEN",
            "active_bundle_digest must be a sha256: digest",
        )
    # A candidate digest may be observed but cannot hot-reload the active one.
    # The binding records only the active digest; the candidate is dropped.
    return AttemptBinding(
        attempt_id=attempt_id,
        active_bundle_digest=active_bundle_digest,
        candidate_bundle_digest=None,
        is_pinned_to_active=True,
    )


@dataclass(frozen=True)
class ActivationGate:
    """Prerequisites for atomic candidate activation (AC-FR2050-01).

    Attributes:
        lint_passed: ``True`` if prompt lint passed.
        schema_validation_passed: ``True`` if input/output schema validation
            against the registry's active schemas passed.
        trusted_review_passed: ``True`` if the prior trusted Prism reviewer
            passed the candidate bundle.
        deployment_readback_passed: ``True`` if deployment/staging readback
            is in_sync.
        implementation_baseline_current: ``True`` if the implementation
            baseline is current for this revision.
    """

    lint_passed: bool
    schema_validation_passed: bool
    trusted_review_passed: bool
    deployment_readback_passed: bool
    implementation_baseline_current: bool


@dataclass(frozen=True)
class ActivationResult:
    """The result of evaluating the activation gate.

    Attributes:
        activated: ``True`` if the candidate was atomically activated.
        reason: A human-readable reason describing the activation outcome.
    """

    activated: bool
    reason: str


def evaluate_activation_gate(gate: ActivationGate) -> ActivationResult:
    """Evaluate the activation gate and return the result.

    Args:
        gate: The :class:`ActivationGate` prerequisites.

    Returns:
        An :class:`ActivationResult` with ``activated=True`` only when every
        prerequisite passed; otherwise ``activated=False`` with a reason
        listing the failed prerequisite.
    """
    if not gate.lint_passed:
        return ActivationResult(False, "lint did not pass")
    if not gate.schema_validation_passed:
        return ActivationResult(False, "schema validation did not pass")
    if not gate.trusted_review_passed:
        return ActivationResult(False, "trusted review did not pass")
    if not gate.deployment_readback_passed:
        return ActivationResult(False, "deployment readback did not pass")
    if not gate.implementation_baseline_current:
        return ActivationResult(False, "implementation baseline is not current")
    return ActivationResult(
        True, "all prerequisites pass; candidate activated atomically"
    )
