"""FR-1100: Human Review 的编辑、Discussion 与明确结论.

AC references:
- AC-FR1100-01: Human opens the review page for the current revision and
  either edits the document directly or creates/replies to an inline
  discussion. The page marks the round as ``edited`` or shows a thread that
  ``lk discuss query`` can identify, and displays the current revision and
  open/reopen thread count.
- AC-FR1100-02: once Human has edited at least one byte in the round, the
  ``no comment`` button is disabled; a direct client submit of
  ``no comment`` is rejected with ``HUMAN_REVIEW_EDITED`` and the Human
  verdict is not PASS.
- AC-FR1100-03: ``comment``, an open/reopen thread or unsaved edits never
  produce a PASS. Only a clean current-revision ``no comment`` with zero
  open/reopen threads records a digest-bound Human PASS.
"""

from __future__ import annotations

import pytest

from louke.v014.fr1100_human_review import (
    DiscussionThread,
    DiscussionThreadStatus,
    HUMAN_REVIEW_EDITED,
    HumanReviewInput,
    HumanReviewRejected,
    HumanReviewVerdict,
    compute_human_review_verdict,
    create_discussion_thread,
    reopen_discussion_thread,
    resolve_discussion_thread,
)


def _input(
    *,
    signal: str = "no_comment",
    edited: bool = False,
    open_threads: int = 0,
    dirty: bool = False,
) -> HumanReviewInput:
    return HumanReviewInput(
        signal=signal,
        edited=edited,
        open_threads=open_threads,
        dirty=dirty,
        artifact_revision=3,
        artifact_digest="sha256:" + "a" * 64,
    )


# AC-FR1100-01 ---------------------------------------------------------------
def test_create_discussion_thread_produces_lk_discuss_queryable_identity() -> None:
    """AC-FR1100-01: a created thread has a stable ``thread_id`` and the
    status OPEN; the canonical blockquote contract is preserved so
    ``lk discuss query`` can identify it."""
    thread = create_discussion_thread(
        artifact_revision=3,
        anchor="story.md#L42",
        initiator="human:alice",
        body="This section needs more detail on offline behaviour.",
    )
    assert isinstance(thread, DiscussionThread)
    assert thread.status == DiscussionThreadStatus.OPEN
    assert thread.thread_id  # non-empty stable id
    assert thread.initiator == "human:alice"
    assert thread.anchor == "story.md#L42"
    assert thread.artifact_revision == 3
    assert "needs more detail" in thread.body


def test_resolve_and_reopen_thread_transitions_are_queryable() -> None:
    """AC-FR1100-01: a thread moves OPEN -> RESOLVED -> REOPEN; each
    transition is recorded so ``lk discuss query`` sees the current status."""
    thread = create_discussion_thread(
        artifact_revision=3,
        anchor="story.md#L42",
        initiator="human:alice",
        body="Question.",
    )
    resolved = resolve_discussion_thread(thread, last_speaker="agent:sage")
    assert resolved.status == DiscussionThreadStatus.RESOLVED
    reopened = reopen_discussion_thread(resolved, last_speaker="human:alice")
    assert reopened.status == DiscussionThreadStatus.REOPEN


# AC-FR1100-02 ---------------------------------------------------------------
def test_no_comment_after_one_byte_edit_is_rejected_with_human_review_edited() -> None:
    """AC-FR1100-02: a ``no_comment`` signal on a round where Human edited at
    least one byte is rejected; the page must keep ``no comment`` disabled
    and the Human verdict is not PASS."""
    with pytest.raises(HumanReviewRejected) as exc_info:
        compute_human_review_verdict(
            _input(signal="no_comment", edited=True),
        )
    assert exc_info.value.code == HUMAN_REVIEW_EDITED
    assert exc_info.value.verdict != HumanReviewVerdict.PASS


def test_no_comment_with_open_thread_is_not_pass() -> None:
    """AC-FR1100-03: a ``no_comment`` with an open/reopen thread is not PASS."""
    with pytest.raises(HumanReviewRejected):
        compute_human_review_verdict(
            _input(signal="no_comment", open_threads=1),
        )


def test_comment_signal_is_not_pass_even_without_edits_or_threads() -> None:
    """AC-FR1100-03: a ``comment`` signal never produces PASS even on a clean
    current revision with no open threads."""
    with pytest.raises(HumanReviewRejected):
        compute_human_review_verdict(
            _input(signal="comment", edited=False, open_threads=0, dirty=False),
        )


def test_dirty_unsaved_edits_block_pass() -> None:
    """AC-FR1100-03: unsaved edits (dirty) block PASS even with ``no_comment``
    and no open threads."""
    with pytest.raises(HumanReviewRejected):
        compute_human_review_verdict(
            _input(signal="no_comment", edited=False, open_threads=0, dirty=True),
        )


# AC-FR1100-03 ---------------------------------------------------------------
def test_clean_no_comment_records_digest_bound_human_pass() -> None:
    """AC-FR1100-03: a clean current-revision ``no_comment`` with zero
    open/reopen threads and no dirty edits records a digest-bound Human
    PASS."""
    verdict = compute_human_review_verdict(
        _input(signal="no_comment", edited=False, open_threads=0, dirty=False),
    )
    assert verdict.verdict == HumanReviewVerdict.PASS
    # The PASS is bound to the current artifact revision/digest.
    assert verdict.artifact_revision == 3
    assert verdict.artifact_digest == "sha256:" + "a" * 64


def test_invalid_signal_is_rejected() -> None:
    """AC-FR1100-03: an unknown signal value is rejected."""
    with pytest.raises(HumanReviewRejected) as exc_info:
        compute_human_review_verdict(
            _input(signal="maybe"),  # type: ignore[arg-type]
        )
    assert exc_info.value.code == "VALIDATION_FAILED"
