"""FR-2001: failure recovery, cancellation, resource cleanup and archive.

AC references:
- AC-FR2001-01: failures report stable category, retryability, known side
  effects and allowed recovery actions.
- AC-FR2001-02: idempotent failures are retried safely; uncertain side-effect
  failures go to reconcile/needs-attention instead of blindly repeating.
- AC-FR2001-03: cancellation stops new scheduling, stops/retains tasks per
  policy, sets project to cancelled terminal state and records actor/reason/revision.
- AC-FR2001-04: cleanup of managed sessions/workspaces/servers after terminal
  state is observable; cleanup failures do not rewrite project result; events,
  digests and gate evidence remain.
- AC-FR2001-05: history is read-only; ordinary delete/modify requests are
  rejected; mistaken creations are kept as cancelled records.
"""

from __future__ import annotations

import pytest

from louke.runtime.failure_recovery import (
    ArchiveGuard,
    CancellationRecord,
    FailureCategory,
    FailureRecord,
    RecoveryAction,
    RecoveryPlanner,
    ResourceCleanup,
    RunCanceller,
)


# -- AC-FR2001-01 -------------------------------------------------------------


def test_ac_fr2001_01_failure_record_classifies_error():
    """AC-FR2001-01: failure record contains category, retryability, actions."""
    record = FailureRecord(
        step="implementation",
        category=FailureCategory.PROGRAM_STEP,
        retryable=True,
        known_side_effects=[],
        allowed_actions=[RecoveryAction.RETRY],
    )

    assert record.category == FailureCategory.PROGRAM_STEP
    assert record.retryable is True
    assert RecoveryAction.RETRY in record.allowed_actions


# -- AC-FR2001-02 -------------------------------------------------------------


def test_ac_fr2001_02_idempotent_failure_can_retry():
    """AC-FR2001-02: idempotent failures are retried."""
    planner = RecoveryPlanner()
    record = FailureRecord(
        step="lint",
        category=FailureCategory.PROGRAM_STEP,
        retryable=True,
        known_side_effects=[],
    )
    plan = planner.plan(record)

    assert plan.action == RecoveryAction.RETRY


def test_ac_fr2001_02_uncertain_side_effect_goes_to_reconcile():
    """AC-FR2001-02: uncertain side-effect failures go to reconcile."""
    planner = RecoveryPlanner()
    record = FailureRecord(
        step="deploy",
        category=FailureCategory.EXTERNAL_ADAPTER,
        retryable=False,
        known_side_effects=["published release"],
    )
    plan = planner.plan(record)

    assert plan.action == RecoveryAction.RECONCILE


# -- AC-FR2001-03 -------------------------------------------------------------


def test_ac_fr2001_03_cancellation_records_actor_and_reason():
    """AC-FR2001-03: cancellation sets terminal cancelled state and records details."""
    canceller = RunCanceller()
    record = canceller.cancel(
        run_id="run_001",
        actor="alice",
        reason="user requested",
        revision="rev_123",
    )

    assert isinstance(record, CancellationRecord)
    assert record.run_id == "run_001"
    assert record.actor == "alice"
    assert record.reason == "user requested"
    assert record.revision == "rev_123"
    assert record.terminal_state == "cancelled"


def test_ac_fr2001_03_cancellation_stops_new_scheduling():
    """AC-FR2001-03: after cancellation, no new tasks are scheduled."""
    canceller = RunCanceller()
    canceller.cancel(run_id="run_001", actor="alice", reason="stop")

    assert canceller.can_schedule("run_001") is False


# -- AC-FR2001-04 -------------------------------------------------------------


def test_ac_fr2001_04_cleanup_does_not_rewrite_result():
    """AC-FR2001-04: cleanup failures leave project result unchanged."""
    cleanup = ResourceCleanup()
    cleanup.register_resource(run_id="run_001", resource_id="sess_1", kind="session")

    result = cleanup.run(run_id="run_001")

    assert result.observable is True
    assert result.project_result_unchanged is True


def test_ac_fr2001_04_cleanup_preserves_evidence():
    """AC-FR2001-04: cleanup preserves events, digests and gate evidence."""
    cleanup = ResourceCleanup()
    cleanup.register_resource(run_id="run_001", resource_id="ws_1", kind="workspace")

    result = cleanup.run(run_id="run_001")

    assert result.events_preserved is True
    assert result.digest_preserved is True


# -- AC-FR2001-05 -------------------------------------------------------------


def test_ac_fr2001_05_history_is_read_only():
    """AC-FR2001-05: archived history rejects writes."""
    guard = ArchiveGuard()
    guard.archive(run_id="run_001", result="completed")

    assert guard.is_read_only("run_001") is True
    with pytest.raises(PermissionError):
        guard.modify("run_001", {"status": "deleted"})


def test_ac_fr2001_05_mistaken_creation_kept_as_cancelled():
    """AC-FR2001-05: mistaken creation is retained as cancelled record."""
    guard = ArchiveGuard()
    guard.record_mistaken_creation(run_id="run_002", reason="duplicate")

    assert guard.get_status("run_002") == "cancelled"
