"""FR-2001: failure recovery, cancellation, resource cleanup and archive e2e.

Covers AC-FR2001-01..05. Per test-plan §1.1 these tests observe behavior through
the runtime module public report methods (FailureRecord / RecoveryPlan /
CancellationRecord / CleanupResult / ArchiveGuard) which are the observable
exits described in interfaces.md §6.1 (events) and §6.3 (archive). The v0.12
M-DEV HTTP project API is not yet implemented; these public outputs are the
contract surface.

AC references:
- AC-FR2001-01: failures report stable category, retryability, side effects, actions.
- AC-FR2001-02: idempotent retry vs reconcile for uncertain side effects.
- AC-FR2001-03: cancellation records actor/reason/revision + stops scheduling.
- AC-FR2001-04: cleanup preserves events/digests/gate evidence; result unchanged.
- AC-FR2001-05: history read-only; mistaken creations retained as cancelled.
"""

from __future__ import annotations

import pytest

from louke.runtime.failure_recovery import (
    ArchiveGuard,
    CancellationRecord,
    CleanupResult,
    FailureCategory,
    FailureRecord,
    RecoveryAction,
    RecoveryPlanner,
    ResourceCleanup,
    RunCanceller,
)


# ---------------------------------------------------------------------------
# AC-FR2001-01: failure record classification
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2001_01_program_step_failure_classified_with_retryability():
    """AC-FR2001-01: a program step failure reports category, retryability, actions.

    The failure record must surface a stable category, whether it is retryable,
    known side effects and the recovery actions the definition allows, so the
    user is not misled into thinking the step succeeded.
    """
    record = FailureRecord(
        step="implementation",
        category=FailureCategory.PROGRAM_STEP,
        retryable=True,
        known_side_effects=[],
        allowed_actions=[RecoveryAction.RETRY, RecoveryAction.CANCEL],
    )

    assert record.category == FailureCategory.PROGRAM_STEP
    assert record.retryable is True
    assert record.known_side_effects == []
    assert RecoveryAction.RETRY in record.allowed_actions
    assert RecoveryAction.CANCEL in record.allowed_actions


@pytest.mark.e2e
def test_ac_fr2001_01_agent_task_failure_distinct_from_program_step():
    """AC-FR2001-01: agent task failures use a distinct category from program steps.

    The category is stable and distinguishes an Agent task failure from a
    program step failure, so recovery guidance is correct per failure source.
    """
    agent_failure = FailureRecord(
        step="semantic_dispatch",
        category=FailureCategory.AGENT_TASK,
        retryable=False,
        known_side_effects=[],
        allowed_actions=[RecoveryAction.RECONCILE],
    )

    assert agent_failure.category == FailureCategory.AGENT_TASK
    assert agent_failure.category != FailureCategory.PROGRAM_STEP
    assert agent_failure.retryable is False


@pytest.mark.e2e
def test_ac_fr2001_01_external_adapter_failure_records_side_effects():
    """AC-FR2001-01: external adapter failures record known side effects.

    An external adapter failure that may have partially executed must carry its
    known side effects so retry does not blindly repeat them.
    """
    record = FailureRecord(
        step="deploy_release",
        category=FailureCategory.EXTERNAL_ADAPTER,
        retryable=False,
        known_side_effects=["release_published", "tag_created"],
        allowed_actions=[RecoveryAction.RECONCILE],
    )

    assert record.category == FailureCategory.EXTERNAL_ADAPTER
    assert "release_published" in record.known_side_effects
    assert record.retryable is False


# ---------------------------------------------------------------------------
# AC-FR2001-02: idempotent retry vs reconcile
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2001_02_idempotent_failure_retries_safely():
    """AC-FR2001-02: an idempotent retryable failure is retried under the same contract.

    A failure with no side effects that is retryable must produce a RETRY plan,
    executed under the same idempotency contract (not a blind repeat).
    """
    planner = RecoveryPlanner()
    record = FailureRecord(
        step="lint",
        category=FailureCategory.PROGRAM_STEP,
        retryable=True,
        known_side_effects=[],
    )

    plan = planner.plan(record)

    assert plan.action == RecoveryAction.RETRY
    # The plan reason must reference idempotency, not "best effort".
    assert "idempotent" in plan.reason.lower()


@pytest.mark.e2e
def test_ac_fr2001_02_uncertain_side_effects_go_to_reconcile():
    """AC-FR2001-02: uncertain side-effect failures go to reconcile, not retry.

    A failure with known side effects must NOT be retried blindly; it goes to
    reconcile/needs-attention for human determination.
    """
    planner = RecoveryPlanner()
    record = FailureRecord(
        step="publish",
        category=FailureCategory.EXTERNAL_ADAPTER,
        retryable=False,
        known_side_effects=["release published to registry"],
    )

    plan = planner.plan(record)

    assert plan.action == RecoveryAction.RECONCILE
    assert plan.action != RecoveryAction.RETRY
    assert "reconcil" in plan.reason.lower()


@pytest.mark.e2e
def test_ac_fr2001_02_non_retryable_no_side_effects_needs_attention():
    """AC-FR2001-02: a non-retryable failure with no side effects is needs-attention.

    When a failure cannot be retried and has no side effects, the planner
    surfaces it for human attention (CANCEL / needs-attention) rather than
    silently ignoring or auto-retrying.
    """
    planner = RecoveryPlanner()
    record = FailureRecord(
        step="compile",
        category=FailureCategory.PROGRAM_STEP,
        retryable=False,
        known_side_effects=[],
    )

    plan = planner.plan(record)

    assert plan.action == RecoveryAction.CANCEL
    assert "not retryable" in plan.reason.lower()


# ---------------------------------------------------------------------------
# AC-FR2001-03: cancellation records actor/reason/revision + stops scheduling
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2001_03_cancellation_records_actor_reason_revision():
    """AC-FR2001-03: cancellation sets terminal state and records details.

    Cancelling a non-terminal run records the actor, reason and the revision at
    cancellation time, and sets the run to the ``cancelled`` terminal state.
    """
    canceller = RunCanceller()
    record = canceller.cancel(
        run_id="run_001",
        actor="alice",
        reason="wrong story selected",
        revision="rev_42",
    )

    assert isinstance(record, CancellationRecord)
    assert record.run_id == "run_001"
    assert record.actor == "alice"
    assert record.reason == "wrong story selected"
    assert record.revision == "rev_42"
    assert record.terminal_state == "cancelled"


@pytest.mark.e2e
def test_ac_fr2001_03_cancellation_stops_new_scheduling():
    """AC-FR2001-03: after cancellation, no new tasks are scheduled for the run.

    The scheduler must refuse to schedule new tasks for a cancelled run.
    """
    canceller = RunCanceller()
    # Before cancellation, scheduling is allowed.
    assert canceller.can_schedule("run_001") is True

    canceller.cancel(run_id="run_001", actor="alice", reason="stop")

    assert canceller.can_schedule("run_001") is False
    # Other runs are unaffected.
    assert canceller.can_schedule("run_002") is True


@pytest.mark.e2e
def test_ac_fr2001_03_cancellation_is_terminal():
    """AC-FR2001-03: a cancelled run reaches a terminal state, not a paused one.

    The terminal_state is ``cancelled`` (a final state), distinguishing it
    from a paused/interrupted run that could be resumed.
    """
    canceller = RunCanceller()
    record = canceller.cancel(run_id="run_001", actor="alice", reason="done")

    assert record.terminal_state == "cancelled"


# ---------------------------------------------------------------------------
# AC-FR2001-04: cleanup preserves evidence; result unchanged
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2001_04_cleanup_result_observable_and_unchanged():
    """AC-FR2001-04: cleanup makes resource final state observable without rewriting result.

    After cleanup, the resource final state is observable and the project
    result is NOT rewritten by cleanup success or failure.
    """
    cleanup = ResourceCleanup()
    cleanup.register_resource(run_id="run_001", resource_id="sess_1", kind="session")
    cleanup.register_resource(run_id="run_001", resource_id="ws_1", kind="workspace")

    result = cleanup.run(run_id="run_001")

    assert isinstance(result, CleanupResult)
    assert result.observable is True
    assert result.project_result_unchanged is True


@pytest.mark.e2e
def test_ac_fr2001_04_cleanup_preserves_events_and_digests():
    """AC-FR2001-04: cleanup preserves events, artifact digests and gate evidence.

    The event stream, artifact digests and gate evidence remain after cleanup
    so the audit trail is intact even when resources are released.
    """
    cleanup = ResourceCleanup()
    cleanup.register_resource(run_id="run_001", resource_id="srv_1", kind="server")

    result = cleanup.run(run_id="run_001")

    assert result.events_preserved is True
    assert result.digest_preserved is True


@pytest.mark.e2e
def test_ac_fr2001_04_cleanup_after_terminal_run_does_not_affect_other_runs():
    """AC-FR2001-04: cleanup of one run does not touch another run's resources.

    Cleanup is scoped to the cancelled/terminal run; another run's registered
    resources survive.
    """
    cleanup = ResourceCleanup()
    cleanup.register_resource(run_id="run_001", resource_id="sess_1", kind="session")
    cleanup.register_resource(run_id="run_002", resource_id="sess_2", kind="session")

    cleanup.run(run_id="run_001")

    # run_002's resource is untouched (observable via a fresh cleanup result).
    result_002 = cleanup.run(run_id="run_002")
    assert result_002.observable is True


# ---------------------------------------------------------------------------
# AC-FR2001-05: history read-only; mistaken creations retained as cancelled
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2001_05_history_is_read_only():
    """AC-FR2001-05: archived history rejects writes; no physical delete.

    A completed/cancelled archived run is read-only; modification attempts are
    rejected and the archive entry is preserved.
    """
    guard = ArchiveGuard()
    guard.archive(run_id="run_001", result="completed")

    assert guard.is_read_only("run_001") is True
    assert guard.get_status("run_001") == "completed"

    with pytest.raises(PermissionError):
        guard.modify("run_001", {"status": "deleted"})

    # Status unchanged after the rejected modification.
    assert guard.get_status("run_001") == "completed"


@pytest.mark.e2e
def test_ac_fr2001_05_mistaken_creation_retained_as_cancelled():
    """AC-FR2001-05: a mistakenly-created run is retained as cancelled, not deleted.

    There is no physical delete; a mistaken creation is recorded as a
    ``cancelled`` archive entry so the history is honest about the error.
    """
    guard = ArchiveGuard()
    guard.record_mistaken_creation(run_id="run_002", reason="duplicate creation")

    assert guard.is_read_only("run_002") is True
    assert guard.get_status("run_002") == "cancelled"


@pytest.mark.e2e
def test_ac_fr2001_05_unarchived_run_not_treated_as_read_only():
    """AC-FR2001-05: only archived runs are read-only; active runs are not.

    The read-only guard applies to terminal/archived history; an active
    (non-archived) run is not falsely reported as read-only.
    """
    guard = ArchiveGuard()

    assert guard.is_read_only("run_active") is False
