"""FR-1900: Semantic Task、Agent Session 与受控结果.

AC references:
- AC-FR1900-01: every Scribe/Sage/Lex task evidence contains run/step/role/
  artifact digest/write scope/output contract/attempt/session; author and
  independent reviewer session IDs are different.
- AC-FR1900-02: when a session has an active turn and HTTP times out, a
  retry request does not increment the dispatch count until session
  status/result reconcile completes; an existing valid result is recycled,
  a still-running session continues to be awaited.
- AC-FR1900-03: an Agent result with the wrong role/attempt/manifest/
  artifact digest/schema or out-of-scope write is rejected; the workflow
  revision, review verdict and controlled document bytes do not change.
- AC-FR1900-04: when the original session is confirmed lost with no valid
  final result, Runtime recovers the task: the original attempt becomes
  ``lost`` or ``interrupted``; a new attempt with a new session id is
  created, referencing the same authoritative input digests; no attempt is
  automatically marked PASS.
"""

from __future__ import annotations

import pytest

from louke.v014.fr1900_semantic_task import (
    AgentResultRejected,
    AttemptStatus,
    AuthorReviewerSessionMismatchError,
    RecycleDecision,
    SemanticTask,
    SemanticAttempt,
    SemanticResult,
    apply_timeout_retry,
    build_semantic_task,
    recover_after_session_lost,
    validate_agent_result,
)


# AC-FR1900-01 ---------------------------------------------------------------
def test_semantic_task_evidence_contains_all_required_fields() -> None:
    """AC-FR1900-01: every SemanticTask carries run/step/role/artifact
    digest/write scope/output contract/attempt/session."""
    task = build_semantic_task(
        run_id="run_1",
        step="M-STORY",
        role="scribe_author",
        artifact_digest="sha256:" + "a" * 64,
        write_scope=("story.md",),
        output_contract_digest="sha256:" + "c" * 64,
        attempt_id="att_1",
        session_id="sess_scribe",
    )
    assert isinstance(task, SemanticTask)
    assert task.run_id == "run_1"
    assert task.step == "M-STORY"
    assert task.role == "scribe_author"
    assert task.artifact_digest == "sha256:" + "a" * 64
    assert task.write_scope == ("story.md",)
    assert task.output_contract_digest == "sha256:" + "c" * 64
    assert task.attempt_id == "att_1"
    assert task.session_id == "sess_scribe"


def test_author_and_reviewer_sessions_must_differ() -> None:
    """AC-FR1900-01: author and independent reviewer session IDs must
    differ."""
    with pytest.raises(AuthorReviewerSessionMismatchError):
        build_semantic_task(
            run_id="run_1",
            step="M-STORY",
            role="sage_reviewer",
            artifact_digest="sha256:" + "a" * 64,
            write_scope=("story.md",),
            output_contract_digest="sha256:" + "c" * 64,
            attempt_id="att_2",
            session_id="sess_scribe",  # same as author
            author_session_id="sess_scribe",
        )


# AC-FR1900-02 ---------------------------------------------------------------
def test_timeout_retry_does_not_increment_dispatch_until_reconciled() -> None:
    """AC-FR1900-02: when a session has an active turn and HTTP times out, a
    retry request does not increment the dispatch count until reconcile
    completes."""
    attempt = SemanticAttempt(
        attempt_id="att_1",
        session_id="sess_1",
        status=AttemptStatus.RUNNING,
        dispatch_count=1,
        input_digest="sha256:" + "i" * 64,
    )
    result = apply_timeout_retry(attempt)
    assert result.dispatch_count == 1  # unchanged
    assert result.attempt.status == AttemptStatus.RECONCILING


def test_timeout_recycles_existing_valid_result() -> None:
    """AC-FR1900-02: an existing valid result is recycled after timeout."""
    attempt = SemanticAttempt(
        attempt_id="att_1",
        session_id="sess_1",
        status=AttemptStatus.RUNNING,
        dispatch_count=1,
        input_digest="sha256:" + "i" * 64,
        existing_result=SemanticResult(
            role="scribe_author",
            attempt_id="att_1",
            manifest_digest="sha256:" + "m" * 64,
            artifact_digest="sha256:" + "a" * 64,
            schema_valid=True,
            write_scope_ok=True,
            verdict="SUGGESTION",
        ),
    )
    decision = apply_timeout_retry(attempt)
    assert decision.recycle_decision == RecycleDecision.RECYCLE_VALID


def test_timeout_running_continues_waiting() -> None:
    """AC-FR1900-02: a still-running session continues to be awaited."""
    attempt = SemanticAttempt(
        attempt_id="att_1",
        session_id="sess_1",
        status=AttemptStatus.RUNNING,
        dispatch_count=1,
        input_digest="sha256:" + "i" * 64,
    )
    decision = apply_timeout_retry(attempt)
    assert decision.recycle_decision == RecycleDecision.WAIT_RUNNING


# AC-FR1900-03 ---------------------------------------------------------------
@pytest.mark.parametrize(
    "wrong_field, value",
    [
        ("role", "wrong_role"),
        ("attempt_id", "att_other"),
        ("manifest_digest", "sha256:" + "x" * 64),
        ("artifact_digest", "sha256:" + "y" * 64),
        ("schema_valid", False),
        ("write_scope_ok", False),
    ],
)
def test_invalid_agent_result_is_rejected(wrong_field: str, value: object) -> None:
    """AC-FR1900-03: an Agent result with wrong role/attempt/manifest/
    artifact digest/schema or out-of-scope write is rejected."""
    base = dict(
        role="scribe_author",
        attempt_id="att_1",
        manifest_digest="sha256:" + "m" * 64,
        artifact_digest="sha256:" + "a" * 64,
        schema_valid=True,
        write_scope_ok=True,
        verdict="SUGGESTION",
    )
    base[wrong_field] = value
    result = SemanticResult(**base)  # type: ignore[arg-type]
    with pytest.raises(AgentResultRejected):
        validate_agent_result(
            result=result,
            expected_role="scribe_author",
            expected_attempt_id="att_1",
            expected_manifest_digest="sha256:" + "m" * 64,
            expected_artifact_digest="sha256:" + "a" * 64,
            expected_write_scope=("story.md",),
        )


def test_valid_agent_result_passes_validation() -> None:
    """AC-FR1900-03: a valid Agent result passes validation."""
    result = SemanticResult(
        role="scribe_author",
        attempt_id="att_1",
        manifest_digest="sha256:" + "m" * 64,
        artifact_digest="sha256:" + "a" * 64,
        schema_valid=True,
        write_scope_ok=True,
        verdict="SUGGESTION",
    )
    validated = validate_agent_result(
        result=result,
        expected_role="scribe_author",
        expected_attempt_id="att_1",
        expected_manifest_digest="sha256:" + "m" * 64,
        expected_artifact_digest="sha256:" + "a" * 64,
        expected_write_scope=("story.md",),
    )
    assert validated.accepted is True


# AC-FR1900-04 ---------------------------------------------------------------
def test_recover_after_session_lost_creates_new_attempt_without_auto_pass() -> None:
    """AC-FR1900-04: when the original session is confirmed lost with no
    valid final result, the original attempt becomes ``lost``; a new attempt
    with a new session id is created, referencing the same input digests;
    no attempt is automatically marked PASS."""
    attempt = SemanticAttempt(
        attempt_id="att_1",
        session_id="sess_1",
        status=AttemptStatus.RUNNING,
        dispatch_count=1,
        input_digest="sha256:" + "i" * 64,
    )
    recovery = recover_after_session_lost(attempt)
    assert recovery.original_attempt.status == AttemptStatus.LOST
    assert recovery.new_attempt.session_id != attempt.session_id
    assert recovery.new_attempt.attempt_id != attempt.attempt_id
    assert recovery.new_attempt.input_digest == attempt.input_digest
    assert recovery.new_attempt.status == AttemptStatus.QUEUED
    # No attempt is automatically marked PASS.
    assert recovery.original_attempt.status != AttemptStatus.COMPLETED
    assert recovery.new_attempt.status != AttemptStatus.COMPLETED
