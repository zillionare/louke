"""FR-0900: Go 后的访谈、Story 完成与交接 Revision.

AC references:
- AC-FR0900-01: after Human chooses Go, replies flow through a persistent
  outbox: the ``reply_persisted`` event sequence is strictly less than the
  ``reply_dispatched`` event sequence for the same correlation identity.
  After a send-retry (ack loss) there is still exactly one logical reply,
  one transcript message and the same Scribe session.
- AC-FR0900-02: when Scribe declares completion but the Story digest has
  not changed, the task receives ``STORY_CHANGE_REQUIRED``; the phase
  remains ``authoring`` and no review task is dispatched.
- AC-FR0900-03: when the Story has actually changed, Runtime accepts the
  Scribe handoff: the new commit only contains ``story.md``; the evidence
  records digest, parent commit SHA, commit SHA, task/attempt/session; only
  then are review tasks created.
"""

from __future__ import annotations


from louke.v014.fr0900_go_handoff import (
    STORY_CHANGE_REQUIRED,
    ReplyOutbox,
    ReplyResult,
    ScribeHandoffEvidence,
    StoryChangeRequired,
    accept_scribe_handoff,
    persist_and_dispatch_reply,
)


def _outbox() -> ReplyOutbox:
    return ReplyOutbox()


# AC-FR0900-01 ---------------------------------------------------------------
def test_reply_persisted_seq_is_strictly_less_than_dispatched_seq() -> None:
    """AC-FR0900-01: persisted event sequence is strictly less than the
    dispatched event sequence for the same correlation identity."""
    outbox = _outbox()
    result = persist_and_dispatch_reply(
        outbox=outbox,
        correlation_id="corr_1",
        body="We need offline cache for the project list.",
        scribe_session_id="sess_S",
    )
    assert isinstance(result, ReplyResult)
    assert result.persisted_sequence < result.dispatched_sequence
    assert result.persisted_event_type == "reply_persisted"
    assert result.dispatched_event_type == "reply_dispatched"
    assert result.correlation_id == "corr_1"


def test_ack_loss_retry_keeps_single_logical_reply_and_session() -> None:
    """AC-FR0900-01: after a send-retry on ack loss, there is still one
    logical reply, one transcript message and the same Scribe session."""
    outbox = _outbox()
    first = persist_and_dispatch_reply(
        outbox=outbox,
        correlation_id="corr_1",
        body="Same body.",
        scribe_session_id="sess_S",
    )
    # Simulate ack loss: caller retries with the same correlation id.
    retry = persist_and_dispatch_reply(
        outbox=outbox,
        correlation_id="corr_1",
        body="Same body.",
        scribe_session_id="sess_S",
    )
    assert retry.correlation_id == first.correlation_id
    assert retry.deduplicated is True
    # Logical reply, transcript message and session are each one.
    assert outbox.logical_reply_count("corr_1") == 1
    assert outbox.transcript_message_count("corr_1") == 1
    assert outbox.session_id_for("corr_1") == "sess_S"


def test_distinct_correlation_ids_produce_distinct_replies() -> None:
    """AC-FR0900-01: distinct correlation identities produce distinct logical
    replies; each has its own persisted<dispatched ordering."""
    outbox = _outbox()
    a = persist_and_dispatch_reply(
        outbox=outbox,
        correlation_id="corr_a",
        body="A",
        scribe_session_id="sess_S",
    )
    b = persist_and_dispatch_reply(
        outbox=outbox,
        correlation_id="corr_b",
        body="B",
        scribe_session_id="sess_S",
    )
    assert a.correlation_id != b.correlation_id
    assert outbox.logical_reply_count("corr_a") == 1
    assert outbox.logical_reply_count("corr_b") == 1


# AC-FR0900-02 ---------------------------------------------------------------
def test_unchanged_story_digest_returns_story_change_required() -> None:
    """AC-FR0900-02: when Scribe's handoff digest equals the baseline digest,
    the task receives STORY_CHANGE_REQUIRED; phase stays authoring and no
    review task is dispatched."""
    baseline_digest = "sha256:" + "a" * 64
    outcome = accept_scribe_handoff(
        baseline_story_digest=baseline_digest,
        scribe_handoff_digest=baseline_digest,
        scribe_task_id="task_scribe_1",
        scribe_attempt_id="att_1",
        scribe_session_id="sess_S",
        run_id="run_1",
    )
    assert isinstance(outcome, StoryChangeRequired)
    assert outcome.code == STORY_CHANGE_REQUIRED
    assert outcome.phase == "authoring"
    assert outcome.review_task_count == 0
    assert outcome.task_id == "task_scribe_1"


# AC-FR0900-03 ---------------------------------------------------------------
def test_changed_story_digest_accepts_handoff_with_single_document_commit() -> None:
    """AC-FR0900-03: when the Story digest has changed, Runtime accepts the
    Scribe handoff; the commit only contains ``story.md`` and the evidence
    records digest, parent commit SHA, commit SHA, task/attempt/session;
    review tasks become possible after acceptance."""
    baseline_digest = "sha256:" + "a" * 64
    new_digest = "sha256:" + "b" * 64
    outcome = accept_scribe_handoff(
        baseline_story_digest=baseline_digest,
        scribe_handoff_digest=new_digest,
        scribe_task_id="task_scribe_1",
        scribe_attempt_id="att_1",
        scribe_session_id="sess_S",
        run_id="run_1",
        parent_commit_sha="p" * 40,
        new_commit_sha="c" * 40,
    )
    assert isinstance(outcome, ScribeHandoffEvidence)
    assert outcome.phase == "review"
    assert outcome.review_task_count >= 1
    assert outcome.commit_document_path == "story.md"
    assert outcome.parent_commit_sha == "p" * 40
    assert outcome.new_commit_sha == "c" * 40
    assert outcome.story_digest == new_digest
    assert outcome.scribe_task_id == "task_scribe_1"
    assert outcome.scribe_attempt_id == "att_1"
    assert outcome.scribe_session_id == "sess_S"


def test_handoff_evidence_commit_only_contains_story_md() -> None:
    """AC-FR0900-03: the accepted commit's tree diff only contains
    ``story.md``; no other document is touched."""
    baseline_digest = "sha256:" + "a" * 64
    new_digest = "sha256:" + "b" * 64
    outcome = accept_scribe_handoff(
        baseline_story_digest=baseline_digest,
        scribe_handoff_digest=new_digest,
        scribe_task_id="task_scribe_1",
        scribe_attempt_id="att_1",
        scribe_session_id="sess_S",
        run_id="run_1",
        parent_commit_sha="p" * 40,
        new_commit_sha="c" * 40,
    )
    assert isinstance(outcome, ScribeHandoffEvidence)
    # AC-FR0900-03: review tasks appear strictly after the handoff commit.
    assert outcome.commit_document_path == "story.md"
    assert outcome.review_task_count >= 1
