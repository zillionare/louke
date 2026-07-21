"""FR-2100: 全流程中断恢复与外部副作用 Reconcile.

Implements the deterministic contract slice of FR-2100:

* :func:`recover_run_after_process_restart` recovers the run state from a
  persisted snapshot after a Louke process restart. The recovered state
  has the same step/revision/round/artifact digest/lease holder/task/
  attempt/session/gate status/last error as the snapshot, and completed-step
  dispatch counts do not increase (AC-FR2100-01).

* :func:`recover_external_operation` reconciles an external operation whose
  result was unknown at interruption. ``CONFIRMED_COMPLETED`` records the
  same resource id and advances; ``CONFIRMED_NOT_HAPPENED`` retries with the
  same idempotency identity (not advanced, not PASS); ``UNKNOWN`` enters
  ``needs_attention`` with the operation/target/known effects listed and
  never records PASS or advances (AC-FR2100-02).

* :func:`recover_browser_disconnect` recovers the current document revision
  and task/session identity from the persistent outlet after a browser/
  OpenCode disconnect while Runtime still runs. No duplicate task or
  external resource is created due to the client disconnect
  (AC-FR2100-03).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ExternalOperationOutcome(str, Enum):
    """Outcome of an external operation reconcile query.

    Members:
        CONFIRMED_COMPLETED: Query confirms the operation completed; the
            resource id is recorded.
        CONFIRMED_NOT_HAPPENED: Query confirms the operation did not happen;
            retry with the same idempotency identity.
        UNKNOWN: Query cannot determine the outcome; enter needs_attention.
    """

    CONFIRMED_COMPLETED = "confirmed_completed"
    CONFIRMED_NOT_HAPPENED = "confirmed_not_happened"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class RunRecoverySnapshot:
    """Persisted snapshot of a run's recoverable state.

    Attributes:
        step: Current workflow step.
        revision: Current run revision.
        review_round: Current review round number.
        artifact_digest: ``sha256:<hex>`` digest of the current artifact.
        lease_holder: Current write-lease holder identity.
        task_id: Active Agent task id.
        attempt_id: Active Agent attempt id.
        session_id: Active Agent session id.
        gate_status: Current gate status.
        last_error: Non-secret last error message.
        completed_step_dispatch_count: Number of dispatches already
            completed; not incremented by recovery.
    """

    step: str
    revision: int
    review_round: int
    artifact_digest: str
    lease_holder: Optional[str]
    task_id: Optional[str]
    attempt_id: Optional[str]
    session_id: Optional[str]
    gate_status: str
    last_error: Optional[str]
    completed_step_dispatch_count: int


@dataclass(frozen=True)
class RunRecoveryResult:
    """Recovered run state after a process restart.

    Attributes mirror :class:`RunRecoverySnapshot`.
    """

    step: str
    revision: int
    review_round: int
    artifact_digest: str
    lease_holder: Optional[str]
    task_id: Optional[str]
    attempt_id: Optional[str]
    session_id: Optional[str]
    gate_status: str
    last_error: Optional[str]
    completed_step_dispatch_count: int


def recover_run_after_process_restart(
    snapshot: RunRecoverySnapshot,
) -> RunRecoveryResult:
    """Recover the run state from ``snapshot`` after a process restart.

    Args:
        snapshot: The persisted :class:`RunRecoverySnapshot`.

    Returns:
        A :class:`RunRecoveryResult` with the same field values as
        ``snapshot``. The ``completed_step_dispatch_count`` is preserved
        (not incremented) because completed steps are not re-dispatched
        (AC-FR2100-01).
    """
    return RunRecoveryResult(
        step=snapshot.step,
        revision=snapshot.revision,
        review_round=snapshot.review_round,
        artifact_digest=snapshot.artifact_digest,
        lease_holder=snapshot.lease_holder,
        task_id=snapshot.task_id,
        attempt_id=snapshot.attempt_id,
        session_id=snapshot.session_id,
        gate_status=snapshot.gate_status,
        last_error=snapshot.last_error,
        completed_step_dispatch_count=snapshot.completed_step_dispatch_count,
    )


@dataclass(frozen=True)
class ExternalOperationReconcileDecision:
    """Decision returned by :func:`recover_external_operation`.

    Attributes:
        operation_id: The operation id being reconciled.
        target: The operation's target (e.g. ``release_project:P_1``).
        known_effects: Tuple of known effects so the page can surface them.
        run_status: ``ok`` when the operation is confirmed or retried;
            ``needs_attention`` when unknown.
        advanced: ``True`` only when the operation is confirmed completed.
        recorded_pass: Always ``False``; reconciliation never auto-passes.
        retry: ``True`` when the operation should be retried with the same
            idempotency identity.
        idempotency_identity: The idempotency identity to use for retry.
        recorded_resource_id: The resource id recorded when
            ``CONFIRMED_COMPLETED``; ``None`` otherwise.
    """

    operation_id: str
    target: str
    known_effects: tuple[str, ...]
    run_status: str
    advanced: bool
    recorded_pass: bool
    retry: bool
    idempotency_identity: str
    recorded_resource_id: Optional[str] = None


def recover_external_operation(
    *,
    query_outcome: ExternalOperationOutcome,
    operation_id: str,
    idempotency_identity: str,
    target: str,
    known_effects: tuple[str, ...] = (),
    observed_resource_id: Optional[str] = None,
) -> ExternalOperationReconcileDecision:
    """Reconcile an external operation whose result was unknown at
    interruption.

    Args:
        query_outcome: The :class:`ExternalOperationOutcome} returned by the
            adapter query.
        operation_id: The operation id being reconciled.
        idempotency_identity: Stable idempotency identity for retry.
        target: The operation's target.
        known_effects: Tuple of known effects to surface on
            ``needs_attention``.
        observed_resource_id: Resource id observed by the query when
            ``CONFIRMED_COMPLETED``.

    Returns:
        An :class:`ExternalOperationReconcileDecision}.

        - ``CONFIRMED_COMPLETED``: ``run_status == 'ok'``,
          ``advanced is True``, ``recorded_resource_id == observed_resource_id``,
          ``retry is False``.
        - ``CONFIRMED_NOT_HAPPENED``: ``run_status == 'ok'``,
          ``advanced is False``, ``retry is True``,
          ``idempotency_identity`` preserved.
        - ``UNKNOWN``: ``run_status == 'needs_attention'``,
          ``advanced is False``, ``recorded_pass is False``,
          ``retry is False``, ``known_effects`` listed.

        ``recorded_pass`` is always ``False``; reconciliation never
        auto-passes (AC-FR2100-02).
    """
    if query_outcome == ExternalOperationOutcome.CONFIRMED_COMPLETED:
        return ExternalOperationReconcileDecision(
            operation_id=operation_id,
            target=target,
            known_effects=known_effects,
            run_status="ok",
            advanced=True,
            recorded_pass=False,
            retry=False,
            idempotency_identity=idempotency_identity,
            recorded_resource_id=observed_resource_id,
        )
    if query_outcome == ExternalOperationOutcome.CONFIRMED_NOT_HAPPENED:
        return ExternalOperationReconcileDecision(
            operation_id=operation_id,
            target=target,
            known_effects=known_effects,
            run_status="ok",
            advanced=False,
            recorded_pass=False,
            retry=True,
            idempotency_identity=idempotency_identity,
        )
    return ExternalOperationReconcileDecision(
        operation_id=operation_id,
        target=target,
        known_effects=known_effects,
        run_status="needs_attention",
        advanced=False,
        recorded_pass=False,
        retry=False,
        idempotency_identity=idempotency_identity,
    )


@dataclass(frozen=True)
class BrowserDisconnectRecovery:
    """Recovery result after a browser/OpenCode disconnect (AC-FR2100-03).

    Attributes:
        recovered_document_revision: The document revision recovered from
            the persistent outlet.
        recovered_document_digest: ``sha256:<hex>`` digest recovered from
            the persistent outlet.
        recovered_task_id: Active task id recovered from the persistent
            outlet.
        recovered_attempt_id: Active attempt id recovered from the
            persistent outlet.
        recovered_session_id: Active session id recovered from the
            persistent outlet.
        duplicate_task_created: Always ``False``; no duplicate task is
            created due to the client disconnect.
        duplicate_external_resource_created: Always ``False``; no duplicate
            external resource is created.
    """

    recovered_document_revision: int
    recovered_document_digest: str
    recovered_task_id: str
    recovered_attempt_id: str
    recovered_session_id: str
    duplicate_task_created: bool = False
    duplicate_external_resource_created: bool = False


def recover_browser_disconnect(
    *,
    document_revision: int,
    document_digest: str,
    task_id: str,
    attempt_id: str,
    session_id: str,
) -> BrowserDisconnectRecovery:
    """Recover the document revision and task/session identity after a
    browser/OpenCode disconnect.

    Args:
        document_revision: Persisted current document revision.
        document_digest: Persisted current document digest.
        task_id: Persisted active task id.
        attempt_id: Persisted active attempt id.
        session_id: Persisted active session id.

    Returns:
        A :class:`BrowserDisconnectRecovery} with the persisted revision/
        digest/task/attempt/session recovered. No duplicate task or
        external resource is created due to the client disconnect
        (AC-FR2100-03).
    """
    return BrowserDisconnectRecovery(
        recovered_document_revision=document_revision,
        recovered_document_digest=document_digest,
        recovered_task_id=task_id,
        recovered_attempt_id=attempt_id,
        recovered_session_id=session_id,
        duplicate_task_created=False,
        duplicate_external_resource_created=False,
    )
