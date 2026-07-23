"""FR-2100: 全流程中断恢复与外部副作用 Reconcile.

AC references:
- AC-FR2100-01: when a run is at any review round with write lease, tasks
  and Human wait, killing the Louke process and restarting from the same
  workspace recovers the same step/revision/round/artifact digest/lease
  state/task/session/gate/last error; completed-step dispatch counts do not
  increase.
- AC-FR2100-02: when an external operation's result is unknown at
  interruption, the recovery scan does not show PASS and does not advance;
  query confirms completion -> record the same resource ID; query confirms
  not happened -> retry with the same idempotency identity; cannot determine
  -> ``needs_attention`` with operation/target/known effects.
- AC-FR2100-03: when the browser or OpenCode disconnects but Runtime still
  runs, reopening Project and Chat recovers the current document revision
  and task/session identity from the persistent outlet; no duplicate task or
  external resource is created due to the client disconnect.
"""

from __future__ import annotations


from louke.runtime.process_recovery import (
    BrowserDisconnectRecovery,
    ExternalOperationOutcome,
    RunRecoverySnapshot,
    recover_browser_disconnect,
    recover_external_operation,
    recover_run_after_process_restart,
)


# AC-FR2100-01 ---------------------------------------------------------------
def test_process_restart_recovers_same_run_state_without_incrementing_dispatch() -> (
    None
):
    """AC-FR2100-01: a process restart recovers the same step/revision/round/
    artifact digest/lease/task/session/gate/last error; completed-step
    dispatch counts do not increase."""
    snapshot = RunRecoverySnapshot(
        step="M-SPEC",
        revision=4,
        review_round=2,
        artifact_digest="sha256:" + "a" * 64,
        lease_holder="human:alice",
        task_id="task_1",
        attempt_id="att_1",
        session_id="sess_1",
        gate_status="pending",
        last_error="model timeout",
        completed_step_dispatch_count=3,
    )
    recovered = recover_run_after_process_restart(snapshot)
    assert recovered.step == "M-SPEC"
    assert recovered.revision == 4
    assert recovered.review_round == 2
    assert recovered.artifact_digest == "sha256:" + "a" * 64
    assert recovered.lease_holder == "human:alice"
    assert recovered.task_id == "task_1"
    assert recovered.attempt_id == "att_1"
    assert recovered.session_id == "sess_1"
    assert recovered.gate_status == "pending"
    assert recovered.last_error == "model timeout"
    # AC-FR2100-01: completed-step dispatch counts do not increase.
    assert recovered.completed_step_dispatch_count == 3


# AC-FR2100-02 ---------------------------------------------------------------
def test_external_operation_reconcile_unknown_does_not_pass_or_advance() -> None:
    """AC-FR2100-02: when the external operation result is unknown, the run
    does not show PASS and does not advance."""
    decision = recover_external_operation(
        query_outcome=ExternalOperationOutcome.UNKNOWN,
        operation_id="op_1",
        idempotency_identity="idem_1",
        target="release_project:P_1",
        known_effects=(),
    )
    assert decision.run_status == "needs_attention"
    assert decision.advanced is False
    assert decision.recorded_pass is False
    assert decision.operation_id == "op_1"
    assert decision.target == "release_project:P_1"


def test_external_operation_reconcile_confirmed_completed_records_same_resource_id() -> (
    None
):
    """AC-FR2100-02: when query confirms completion, the same resource ID is
    recorded."""
    decision = recover_external_operation(
        query_outcome=ExternalOperationOutcome.CONFIRMED_COMPLETED,
        operation_id="op_1",
        idempotency_identity="idem_1",
        target="release_project:P_1",
        known_effects=(),
        observed_resource_id="P_node_1",
    )
    assert decision.run_status == "ok"
    assert decision.advanced is True
    assert decision.recorded_resource_id == "P_node_1"
    # AC-FR2100-02: no retry, no second resource creation.
    assert decision.retry is False


def test_external_operation_reconcile_confirmed_not_happened_retries_with_same_idempotency() -> (
    None
):
    """AC-FR2100-02: when query confirms not happened, the same idempotency
    identity is used to retry."""
    decision = recover_external_operation(
        query_outcome=ExternalOperationOutcome.CONFIRMED_NOT_HAPPENED,
        operation_id="op_1",
        idempotency_identity="idem_1",
        target="release_project:P_1",
        known_effects=(),
    )
    assert decision.run_status == "ok"
    assert decision.retry is True
    assert decision.idempotency_identity == "idem_1"
    # AC-FR2100-02: not advanced yet; the retry will determine the outcome.
    assert decision.advanced is False
    assert decision.recorded_pass is False


def test_external_operation_reconcile_unknown_lists_operation_target_known_effects() -> (
    None
):
    """AC-FR2100-02: an unknown outcome lists operation/target/known effects
    so the page can surface them."""
    decision = recover_external_operation(
        query_outcome=ExternalOperationOutcome.UNKNOWN,
        operation_id="op_42",
        idempotency_identity="idem_42",
        target="release_branch:refs/heads/releases/0.14.0",
        known_effects=("local_project:created", "workflow_run:created"),
    )
    assert decision.run_status == "needs_attention"
    assert decision.operation_id == "op_42"
    assert decision.target == "release_branch:refs/heads/releases/0.14.0"
    assert "local_project:created" in decision.known_effects
    assert "workflow_run:created" in decision.known_effects


# AC-FR2100-03 ---------------------------------------------------------------
def test_browser_disconnect_recovery_preserves_revision_and_task_session() -> None:
    """AC-FR2100-03: when the browser disconnects but Runtime still runs,
    reopening Project and Chat recovers the current document revision and
    task/session identity; no duplicate task or external resource is
    created."""
    recovery = recover_browser_disconnect(
        document_revision=5,
        document_digest="sha256:" + "d" * 64,
        task_id="task_1",
        attempt_id="att_1",
        session_id="sess_1",
    )
    assert isinstance(recovery, BrowserDisconnectRecovery)
    assert recovery.recovered_document_revision == 5
    assert recovery.recovered_document_digest == "sha256:" + "d" * 64
    assert recovery.recovered_task_id == "task_1"
    assert recovery.recovered_attempt_id == "att_1"
    assert recovery.recovered_session_id == "sess_1"
    # AC-FR2100-03: no duplicate task or external resource.
    assert recovery.duplicate_task_created is False
    assert recovery.duplicate_external_resource_created is False
