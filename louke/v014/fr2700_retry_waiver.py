"""FR-2700: Retry, waiver & cancel.

Runtime may only retry operations declared idempotent/reconcile-safe by
the WorkflowDefinition; each attempt is independent and does NOT rewrite
old facts.  Red ref same-attempt retry requires compare-and-set yielding
the same commit; otherwise a new attempt is allocated.  Waiver applies
only to current policy non-critical checks and must bind actor/reason/
scope/candidate/expiry; requirement approval, release approval, trace/
freshness, required CI, artifact version, critical security and publish
identity are NOT waivable.  Human may cancel unpublished runs; runs with
published facts may only enter recovery/close (AC-FR2700-01).
"""

from __future__ import annotations

from dataclasses import dataclass

ERROR_CODES = (
    "RETRY_NOT_IDEMPOTENT",
    "RETRY_MAX_ATTEMPTS_EXCEEDED",
    "WAIVER_FORBIDDEN",
    "WAIVER_INVALID",
    "CANCEL_FORBIDDEN_AFTER_EFFECT",
    "CANCEL_FORBIDDEN_AGENT",
)

_NON_WAIVABLE_GATES: frozenset[str] = frozenset(
    {
        "required-ci",
        "release-approval",
        "trace-freshness",
        "artifact-version",
        "critical-security",
        "publish-identity",
        "requirement-approval",
    }
)

_NON_WAIVABLE_SEVERITIES: frozenset[str] = frozenset({"critical", "high"})


class RetryWaiverError(Exception):
    """A fail-closed retry/waiver/cancel rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class RetryDecision:
    """A retry decision (AC-FR2700-01).

    Attributes:
        allowed: ``True`` if retry is allowed.
        new_attempt_no: New attempt number allocated for the retry.
    """

    allowed: bool
    new_attempt_no: int


def evaluate_retry(
    *,
    operation_kind: str,
    idempotent_safe: bool,
    prior_attempts: int,
    max_attempts: int,
) -> RetryDecision:
    """Evaluate whether an operation may be retried (AC-FR2700-01).

    Args:
        operation_kind: Stable operation kind.
        idempotent_safe: ``True`` if WorkflowDefinition declares the operation
            idempotent/reconcile-safe.
        prior_attempts: Number of prior attempts.
        max_attempts: Maximum attempts allowed by policy.

    Returns:
        A :class:`RetryDecision` with ``allowed=True`` and the new attempt no.

    Raises:
        RetryWaiverError: With ``RETRY_NOT_IDEMPOTENT`` if not idempotent;
            ``RETRY_MAX_ATTEMPTS_EXCEEDED`` if ``prior_attempts >= max_attempts``.
    """
    if not idempotent_safe:
        raise RetryWaiverError(
            "RETRY_NOT_IDEMPOTENT",
            f"operation {operation_kind!r} is not declared idempotent/reconcile-safe",
        )
    if prior_attempts >= max_attempts:
        raise RetryWaiverError(
            "RETRY_MAX_ATTEMPTS_EXCEEDED",
            f"prior attempts {prior_attempts} >= max {max_attempts}",
        )
    return RetryDecision(allowed=True, new_attempt_no=prior_attempts + 1)


@dataclass(frozen=True)
class WaiverDecision:
    """A waiver request (AC-FR2700-01).

    Attributes:
        actor: Actor identity.
        reason: Free-text waiver reason.
        scope: Scope of the waiver.
        issue_id: Issue id backing the waiver.
        expires_at: Expiry of the waiver.
        policy_digest: ``sha256:<hex>`` of the policy bytes.
    """

    actor: str
    reason: str
    scope: str
    issue_id: int
    expires_at: str
    policy_digest: str


@dataclass(frozen=True)
class WaiverEvaluation:
    """Result of :func:`evaluate_waiver` (AC-FR2700-01).

    Attributes:
        allowed: ``True`` if waiver is allowed.
        reason_code: Stable reason code explaining a denial.
    """

    allowed: bool
    reason_code: str = ""


def evaluate_waiver(
    *,
    gate_name: str,
    severity: str,
    waiver: WaiverDecision | None = None,
) -> WaiverEvaluation:
    """Evaluate whether a gate may be waived (AC-FR2700-01).

    Args:
        gate_name: Stable gate name.
        severity: ``critical|high|medium|low``.
        waiver: Optional :class:`WaiverDecision` with policy-bound metadata.

    Returns:
        A :class:`WaiverEvaluation` with ``allowed=True`` only when the gate
        is not in :data:`_NON_WAIVABLE_GATES`, severity is not in
        :data:`_NON_WAIVABLE_SEVERITIES`, and waiver metadata is fully populated.

    Raises:
        RetryWaiverError: With ``WAIVER_FORBIDDEN`` if the gate or severity is
            non-waivable.
    """
    if gate_name in _NON_WAIVABLE_GATES:
        raise RetryWaiverError(
            "WAIVER_FORBIDDEN",
            f"gate {gate_name!r} is in the non-waivable list",
        )
    if severity in _NON_WAIVABLE_SEVERITIES:
        raise RetryWaiverError(
            "WAIVER_FORBIDDEN",
            f"severity {severity!r} is non-waivable",
        )
    if waiver is None or not (
        waiver.actor
        and waiver.reason
        and waiver.scope
        and waiver.issue_id
        and waiver.expires_at
        and waiver.policy_digest
    ):
        return WaiverEvaluation(allowed=False, reason_code="WAIVER_INVALID")
    return WaiverEvaluation(allowed=True)


@dataclass(frozen=True)
class CancelDecision:
    """A cancel decision (AC-FR2700-01).

    Attributes:
        allowed: ``True`` if cancel is allowed.
        new_state: ``cancelled`` for an allowed cancel.
    """

    allowed: bool
    new_state: str = ""


def evaluate_cancel(
    *,
    has_published_facts: bool,
    actor_role: str,
) -> CancelDecision:
    """Evaluate whether a run may be cancelled (AC-FR2700-01).

    Args:
        has_published_facts: ``True`` if the run has any published facts.
        actor_role: ``human|devon|shield|...``.

    Returns:
        A :class:`CancelDecision` with ``allowed=True`` and ``new_state=cancelled``
        only for Human-initiated cancel of an unpublished run.

    Raises:
        RetryWaiverError: With ``CANCEL_FORBIDDEN_AFTER_EFFECT`` if published
            facts exist; ``CANCEL_FORBIDDEN_AGENT`` if actor is not Human.
    """
    if actor_role != "human":
        raise RetryWaiverError(
            "CANCEL_FORBIDDEN_AGENT",
            f"actor role {actor_role!r} cannot cancel; only Human may",
        )
    if has_published_facts:
        raise RetryWaiverError(
            "CANCEL_FORBIDDEN_AFTER_EFFECT",
            "run has published facts; only recovery/close allowed",
        )
    return CancelDecision(allowed=True, new_state="cancelled")
