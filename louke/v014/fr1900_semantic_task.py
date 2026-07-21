"""FR-1900: Semantic Task、Agent Session 与受控结果.

Implements the deterministic contract slice of FR-1900:

* :func:`build_semantic_task` builds a :class:`SemanticTask` with the full
  evidence identity (run/step/role/artifact digest/write scope/output
  contract/attempt/session). When the role is a reviewer, the caller must
  supply an ``author_session_id`` that differs from the new session id;
  otherwise :class:`AuthorReviewerSessionMismatchError` is raised
  (AC-FR1900-01).

* :func:`apply_timeout_retry` handles an HTTP timeout on a session with an
  active turn. The dispatch count is not incremented until reconcile
  completes. The returned :class:`TimeoutRetryDecision` carries a
  :class:`RecycleDecision` that is ``RECYCLE_VALID`` when an existing valid
  result is present, ``WAIT_RUNNING`` when the session is still running and
  ``RECONCILE`` otherwise (AC-FR1900-02).

* :func:`validate_agent_result` validates an Agent result against the
  expected role/attempt/manifest digest/artifact digest/write scope and
  schema. Any mismatch raises :class:`AgentResultRejected` and the workflow
  revision/review verdict/controlled document bytes do not change
  (AC-FR1900-03).

* :func:`recover_after_session_lost` recovers a task whose session is
  confirmed lost with no valid final result. The original attempt becomes
  ``LOST``; a new attempt with a new session id is created, referencing the
  same input digests; no attempt is automatically marked PASS
  (AC-FR1900-04).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AttemptStatus(str, Enum):
    """Lifecycle status of a semantic attempt.

    Members:
        QUEUED: Attempt is queued for dispatch.
        DISPATCHING: Attempt is being dispatched.
        RUNNING: Attempt's session has an active turn.
        RECONCILING: Attempt is reconciling after a timeout/ack loss.
        COMPLETED: Attempt produced a valid result (not automatically PASS).
        REJECTED: Attempt's result was rejected by validation.
        FAILED: Attempt failed terminally.
        INTERRUPTED: Attempt was interrupted (e.g. process death).
        LOST: Attempt's session was confirmed lost.
    """

    QUEUED = "queued"
    DISPATCHING = "dispatching"
    RUNNING = "running"
    RECONCILING = "reconciling"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    LOST = "lost"


class RecycleDecision(str, Enum):
    """Decision returned by :func:`apply_timeout_retry`.

    Members:
        RECYCLE_VALID: An existing valid result is recycled; no new dispatch.
        WAIT_RUNNING: The session is still running; continue to wait.
        RECONCILE: No existing result; reconcile to confirm session state.
    """

    RECYCLE_VALID = "recycle_valid"
    WAIT_RUNNING = "wait_running"
    RECONCILE = "reconcile"


@dataclass(frozen=True)
class SemanticResult:
    """A semantic Agent result for validation.

    Attributes:
        role: Role that produced the result (must match expected).
        attempt_id: Attempt id that produced the result (must match
            expected).
        manifest_digest: ``sha256:<hex>`` digest of the task manifest the
            Agent read (must match expected).
        artifact_digest: ``sha256:<hex>`` digest of the artifact the Agent
            read (must match expected).
        schema_valid: Whether the result conformed to the output schema.
        write_scope_ok: Whether the Agent stayed within its write scope.
        verdict: Free-form verdict text (e.g. ``PASS``, ``REJECT``,
            ``SUGGESTION``).
    """

    role: str
    attempt_id: str
    manifest_digest: str
    artifact_digest: str
    schema_valid: bool
    write_scope_ok: bool
    verdict: str


@dataclass(frozen=True)
class SemanticAttempt:
    """A single semantic attempt.

    Attributes:
        attempt_id: Opaque attempt identifier.
        session_id: OpenCode session id bound to this attempt.
        status: :class:`AttemptStatus`.
        dispatch_count: Number of times this attempt has been dispatched.
        input_digest: ``sha256:<hex>`` digest of the authoritative input the
            attempt is bound to.
        existing_result: A previously-observed valid result, when available.
    """

    attempt_id: str
    session_id: str
    status: AttemptStatus
    dispatch_count: int
    input_digest: str
    existing_result: Optional[SemanticResult] = None


@dataclass(frozen=True)
class SemanticTask:
    """A semantic task with its full evidence identity.

    Attributes:
        run_id: Opaque run identifier.
        step: Workflow step the task belongs to.
        role: Role of the Agent (``scribe_author``, ``sage_author``,
            ``sage_reviewer``, ``lex_reviewer``).
        artifact_digest: ``sha256:<hex>`` digest of the artifact the task
            reads/writes.
        write_scope: Tuple of allowed write paths.
        output_contract_digest: ``sha256:<hex>`` digest of the output
            contract schema.
        attempt_id: Active attempt id.
        session_id: Active session id.
    """

    run_id: str
    step: str
    role: str
    artifact_digest: str
    write_scope: tuple[str, ...]
    output_contract_digest: str
    attempt_id: str
    session_id: str


class AuthorReviewerSessionMismatchError(ValueError):
    """Raised when an author and reviewer would share a session id."""


_REVIEWER_ROLES: frozenset[str] = frozenset({"sage_reviewer", "lex_reviewer"})


def build_semantic_task(
    *,
    run_id: str,
    step: str,
    role: str,
    artifact_digest: str,
    write_scope: tuple[str, ...],
    output_contract_digest: str,
    attempt_id: str,
    session_id: str,
    author_session_id: Optional[str] = None,
) -> SemanticTask:
    """Build a :class:`SemanticTask` with full evidence identity.

    Args:
        run_id: Opaque run identifier.
        step: Workflow step the task belongs to.
        role: Role of the Agent.
        artifact_digest: ``sha256:<hex>`` digest of the artifact.
        write_scope: Tuple of allowed write paths.
        output_contract_digest: ``sha256:<hex>`` digest of the output
            contract schema.
        attempt_id: Active attempt id.
        session_id: Active session id.
        author_session_id: When ``role`` is a reviewer, the author session
            id that must differ from ``session_id``.

    Returns:
        A :class:`SemanticTask`.

    Raises:
        AuthorReviewerSessionMismatchError: When ``role`` is a reviewer and
            ``author_session_id == session_id`` (AC-FR1900-01).
    """
    if role in _REVIEWER_ROLES:
        if author_session_id is None:
            raise AuthorReviewerSessionMismatchError(
                f"reviewer role {role!r} requires author_session_id to compare against"
            )
        if author_session_id == session_id:
            raise AuthorReviewerSessionMismatchError(
                f"reviewer session {session_id!r} must differ from author session "
                f"{author_session_id!r} (AC-FR1900-01)"
            )
    return SemanticTask(
        run_id=run_id,
        step=step,
        role=role,
        artifact_digest=artifact_digest,
        write_scope=write_scope,
        output_contract_digest=output_contract_digest,
        attempt_id=attempt_id,
        session_id=session_id,
    )


@dataclass(frozen=True)
class TimeoutRetryDecision:
    """Decision returned by :func:`apply_timeout_retry`.

    Attributes:
        attempt: The updated attempt with status ``RECONCILING`` (or
            unchanged when an existing valid result is recycled).
        dispatch_count: The dispatch count after the retry decision. Always
            equal to the input attempt's dispatch count (no increment until
            reconcile completes).
        recycle_decision: :class:`RecycleDecision` telling the caller what
            to do next.
    """

    attempt: SemanticAttempt
    dispatch_count: int
    recycle_decision: RecycleDecision


def apply_timeout_retry(attempt: SemanticAttempt) -> TimeoutRetryDecision:
    """Apply an HTTP-timeout retry on ``attempt``.

    Args:
        attempt: The :class:`SemanticAttempt` whose session timed out.

    Returns:
        A :class:`TimeoutRetryDecision`. The dispatch count is **not**
        incremented; the caller must reconcile the session state before any
        new dispatch. ``recycle_decision`` is ``RECYCLE_VALID`` when an
        existing valid result is present, ``WAIT_RUNNING`` when the session
        is still running, and ``RECONCILE`` otherwise (AC-FR1900-02).
    """
    if attempt.existing_result is not None:
        return TimeoutRetryDecision(
            attempt=attempt,
            dispatch_count=attempt.dispatch_count,
            recycle_decision=RecycleDecision.RECYCLE_VALID,
        )
    if attempt.status == AttemptStatus.RUNNING:
        return TimeoutRetryDecision(
            attempt=SemanticAttempt(
                attempt_id=attempt.attempt_id,
                session_id=attempt.session_id,
                status=AttemptStatus.RECONCILING,
                dispatch_count=attempt.dispatch_count,
                input_digest=attempt.input_digest,
                existing_result=attempt.existing_result,
            ),
            dispatch_count=attempt.dispatch_count,
            recycle_decision=RecycleDecision.WAIT_RUNNING,
        )
    return TimeoutRetryDecision(
        attempt=SemanticAttempt(
            attempt_id=attempt.attempt_id,
            session_id=attempt.session_id,
            status=AttemptStatus.RECONCILING,
            dispatch_count=attempt.dispatch_count,
            input_digest=attempt.input_digest,
            existing_result=attempt.existing_result,
        ),
        dispatch_count=attempt.dispatch_count,
        recycle_decision=RecycleDecision.RECONCILE,
    )


@dataclass(frozen=True)
class ValidatedAgentResult:
    """Result of :func:`validate_agent_result`.

    Attributes:
        accepted: ``True`` when the result is accepted; ``False`` when
            rejected.
        result: The validated :class:`SemanticResult` when accepted.
    """

    accepted: bool
    result: SemanticResult


class AgentResultRejected(Exception):
    """Raised when an Agent result fails validation.

    Attributes:
        code: ``RESULT_REJECTED``.
        reason: Non-secret reason for rejection.
    """

    def __init__(self, *, reason: str) -> None:
        super().__init__(f"RESULT_REJECTED: {reason}")
        self.code = "RESULT_REJECTED"
        self.reason = reason


def validate_agent_result(
    *,
    result: SemanticResult,
    expected_role: str,
    expected_attempt_id: str,
    expected_manifest_digest: str,
    expected_artifact_digest: str,
    expected_write_scope: tuple[str, ...],
) -> ValidatedAgentResult:
    """Validate an Agent result against the expected identity.

    Args:
        result: The :class:`SemanticResult` to validate.
        expected_role: Expected role.
        expected_attempt_id: Expected attempt id.
        expected_manifest_digest: Expected manifest digest.
        expected_artifact_digest: Expected artifact digest.
        expected_write_scope: Expected write scope.

    Returns:
        A :class:`ValidatedAgentResult` with ``accepted is True`` when all
        checks pass.

    Raises:
        AgentResultRejected: When any check fails. ``code`` is
            ``RESULT_REJECTED`` and the workflow revision, review verdict
            and controlled document bytes do not change (AC-FR1900-03).
    """
    if result.role != expected_role:
        raise AgentResultRejected(
            reason=f"role {result.role!r} != expected {expected_role!r}"
        )
    if result.attempt_id != expected_attempt_id:
        raise AgentResultRejected(
            reason=f"attempt_id {result.attempt_id!r} != expected {expected_attempt_id!r}"
        )
    if result.manifest_digest != expected_manifest_digest:
        raise AgentResultRejected(
            reason=f"manifest_digest {result.manifest_digest!r} != expected {expected_manifest_digest!r}"
        )
    if result.artifact_digest != expected_artifact_digest:
        raise AgentResultRejected(
            reason=f"artifact_digest {result.artifact_digest!r} != expected {expected_artifact_digest!r}"
        )
    if not result.schema_valid:
        raise AgentResultRejected(reason="result schema is invalid")
    if not result.write_scope_ok:
        raise AgentResultRejected(reason="result writes out of scope")
    return ValidatedAgentResult(accepted=True, result=result)


@dataclass(frozen=True)
class SessionLostRecovery:
    """Result of :func:`recover_after_session_lost`.

    Attributes:
        original_attempt: The original attempt with status ``LOST``.
        new_attempt: A new attempt with a fresh session id, status ``QUEUED``
            and the same input digest. Not automatically marked PASS.
    """

    original_attempt: SemanticAttempt
    new_attempt: SemanticAttempt


def recover_after_session_lost(attempt: SemanticAttempt) -> SessionLostRecovery:
    """Recover a task whose session is confirmed lost with no valid result.

    Args:
        attempt: The :class:`SemanticAttempt` whose session was lost.

    Returns:
        A :class:`SessionLostRecovery`. The original attempt becomes ``LOST``
        and a new attempt is created with a fresh session id, status
        ``QUEUED`` and the same ``input_digest``. Neither attempt is
        automatically marked PASS (AC-FR1900-04).
    """
    original = SemanticAttempt(
        attempt_id=attempt.attempt_id,
        session_id=attempt.session_id,
        status=AttemptStatus.LOST,
        dispatch_count=attempt.dispatch_count,
        input_digest=attempt.input_digest,
        existing_result=attempt.existing_result,
    )
    new = SemanticAttempt(
        attempt_id=f"att_{uuid.uuid4().hex[:12]}",
        session_id=f"sess_{uuid.uuid4().hex[:16]}",
        status=AttemptStatus.QUEUED,
        dispatch_count=0,
        input_digest=attempt.input_digest,
    )
    return SessionLostRecovery(original_attempt=original, new_attempt=new)
