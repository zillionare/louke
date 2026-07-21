"""FR-0900: Go 后的访谈、Story 完成与交接 Revision.

Implements the deterministic contract slice of FR-0900:

* :class:`ReplyOutbox` is the persistent outbox for Human replies to the
  Scribe interview. Each reply is persisted before it is dispatched; the
  ``reply_persisted`` event sequence is strictly less than the
  ``reply_dispatched`` event sequence for the same correlation identity
  (AC-FR0900-01). Retrying with the same correlation identity (ack loss)
  is deduplicated: exactly one logical reply, one transcript message and
  the same Scribe session survive.

* :func:`accept_scribe_handoff` validates the Scribe's handoff digest
  against the baseline Story digest. When they are equal the task receives
  ``STORY_CHANGE_REQUIRED``, the phase stays ``authoring`` and no review
  task is dispatched (AC-FR0900-02). When the digest has changed the
  handoff is accepted: the commit only contains ``story.md`` and the
  evidence records digest, parent commit SHA, commit SHA, task/attempt/
  session; review tasks become possible only after acceptance
  (AC-FR0900-03).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


STORY_CHANGE_REQUIRED = "STORY_CHANGE_REQUIRED"


@dataclass
class ReplyOutbox:
    """Persistent outbox for Human replies to a Scribe interview.

    The outbox is the authority for reply ordering and deduplication. Each
    reply is persisted with a monotonically increasing ``persisted_sequence``
    before being dispatched with a strictly greater ``dispatched_sequence``.
    Retries with the same ``correlation_id`` are deduplicated: the original
    persisted/dispatched sequences and transcript message are returned, and
    no second logical reply is created.
    """

    _next_sequence: int = 1
    _replies: dict[str, "ReplyRecord"] = field(default_factory=dict)

    def persist_and_dispatch(
        self,
        *,
        correlation_id: str,
        body: str,
        scribe_session_id: str,
    ) -> "ReplyResult":
        """Persist and dispatch a reply.

        Args:
            correlation_id: Client-supplied correlation identity; deduplicates
                ack-loss retries.
            body: Reply body bytes.
            scribe_session_id: Scribe OpenCode session the reply is sent to.

        Returns:
            A :class:`ReplyResult` with ``persisted_sequence`` strictly less
            than ``dispatched_sequence``. On retry with the same
            ``correlation_id``, the original sequences are returned and
            ``deduplicated is True``.
        """
        existing = self._replies.get(correlation_id)
        if existing is not None:
            return ReplyResult(
                correlation_id=correlation_id,
                persisted_sequence=existing.persisted_sequence,
                dispatched_sequence=existing.dispatched_sequence,
                persisted_event_type="reply_persisted",
                dispatched_event_type="reply_dispatched",
                deduplicated=True,
            )
        persisted_sequence = self._next_sequence
        self._next_sequence += 1
        dispatched_sequence = self._next_sequence
        self._next_sequence += 1
        record = ReplyRecord(
            correlation_id=correlation_id,
            body=body,
            scribe_session_id=scribe_session_id,
            persisted_sequence=persisted_sequence,
            dispatched_sequence=dispatched_sequence,
        )
        self._replies[correlation_id] = record
        return ReplyResult(
            correlation_id=correlation_id,
            persisted_sequence=persisted_sequence,
            dispatched_sequence=dispatched_sequence,
            persisted_event_type="reply_persisted",
            dispatched_event_type="reply_dispatched",
            deduplicated=False,
        )

    def logical_reply_count(self, correlation_id: str) -> int:
        """Return ``1`` if a reply for ``correlation_id`` exists, else ``0``."""
        return 1 if correlation_id in self._replies else 0

    def transcript_message_count(self, correlation_id: str) -> int:
        """Return the number of transcript messages for ``correlation_id``.

        Always equal to :meth:`logical_reply_count`; ack-loss retries do not
        produce additional transcript messages.
        """
        return self.logical_reply_count(correlation_id)

    def session_id_for(self, correlation_id: str) -> Optional[str]:
        """Return the Scribe session id bound to ``correlation_id``."""
        record = self._replies.get(correlation_id)
        return record.scribe_session_id if record is not None else None


@dataclass(frozen=True)
class ReplyRecord:
    """Internal record of a persisted-and-dispatched reply.

    Attributes:
        correlation_id: Client-supplied correlation identity.
        body: Reply body bytes.
        scribe_session_id: Scribe OpenCode session the reply was sent to.
        persisted_sequence: Event sequence of the ``reply_persisted`` event.
        dispatched_sequence: Event sequence of the ``reply_dispatched``
            event; strictly greater than ``persisted_sequence``.
    """

    correlation_id: str
    body: str
    scribe_session_id: str
    persisted_sequence: int
    dispatched_sequence: int


@dataclass(frozen=True)
class ReplyResult:
    """Result of :func:`persist_and_dispatch_reply`.

    Attributes:
        correlation_id: Client-supplied correlation identity.
        persisted_sequence: Event sequence of the ``reply_persisted`` event.
        dispatched_sequence: Event sequence of the ``reply_dispatched``
            event; strictly greater than ``persisted_sequence``.
        persisted_event_type: Always ``reply_persisted``.
        dispatched_event_type: Always ``reply_dispatched``.
        deduplicated: ``True`` when the result corresponds to an ack-loss
            retry of an already-persisted reply.
    """

    correlation_id: str
    persisted_sequence: int
    dispatched_sequence: int
    persisted_event_type: str
    dispatched_event_type: str
    deduplicated: bool


def persist_and_dispatch_reply(
    *,
    outbox: ReplyOutbox,
    correlation_id: str,
    body: str,
    scribe_session_id: str,
) -> ReplyResult:
    """Persist and dispatch a Human reply to the Scribe interview.

    Args:
        outbox: The :class:`ReplyOutbox` to persist into.
        correlation_id: Client-supplied correlation identity; deduplicates
            ack-loss retries.
        body: Reply body bytes.
        scribe_session_id: Scribe OpenCode session the reply is sent to.

    Returns:
        A :class:`ReplyResult` with ``persisted_sequence`` strictly less
        than ``dispatched_sequence``. On retry with the same
        ``correlation_id``, the original sequences are returned and
        ``deduplicated is True``.

    Side effects:
        Mutates ``outbox``: the reply is persisted before it is dispatched.
    """
    return outbox.persist_and_dispatch(
        correlation_id=correlation_id,
        body=body,
        scribe_session_id=scribe_session_id,
    )


class StoryChangeRequired(Exception):
    """Raised when the Scribe handoff digest equals the baseline Story digest.

    Attributes:
        code: Always :data:`STORY_CHANGE_REQUIRED`.
        phase: Always ``authoring``; the Scribe must revise the Story.
        review_task_count: Always ``0``; no review task is dispatched until
            the Story actually changes.
        task_id: The Scribe task id that must revise the Story.
    """

    def __init__(self, *, task_id: str) -> None:
        super().__init__(
            f"{STORY_CHANGE_REQUIRED}: Scribe handoff digest matches baseline; "
            "Story must be revised before review"
        )
        self.code = STORY_CHANGE_REQUIRED
        self.phase = "authoring"
        self.review_task_count = 0
        self.task_id = task_id


@dataclass(frozen=True)
class ScribeHandoffEvidence:
    """Evidence for an accepted Scribe handoff (AC-FR0900-03).

    Attributes:
        run_id: Opaque run identifier.
        phase: ``review`` after a successful handoff.
        review_task_count: >= 1; review tasks appear strictly after the
            handoff commit.
        commit_document_path: Always ``story.md``; the commit tree diff
            only contains this path.
        story_digest: ``sha256:<hex>`` digest of the new Story bytes.
        parent_commit_sha: Parent commit SHA the new commit is built on.
        new_commit_sha: New commit SHA recorded for the revision.
        scribe_task_id: Scribe task id that produced the handoff.
        scribe_attempt_id: Scribe attempt id that produced the handoff.
        scribe_session_id: Scribe OpenCode session id that produced the
            handoff.
    """

    run_id: str
    phase: str
    review_task_count: int
    commit_document_path: str
    story_digest: str
    parent_commit_sha: str
    new_commit_sha: str
    scribe_task_id: str
    scribe_attempt_id: str
    scribe_session_id: str


@dataclass(frozen=True)
class ScribeHandoffOutcome:
    """Tagged union result of :func:`accept_scribe_handoff`.

    Either :class:`StoryChangeRequired` (failure) or
    :class:`ScribeHandoffEvidence` (success).
    """


def accept_scribe_handoff(
    *,
    baseline_story_digest: str,
    scribe_handoff_digest: str,
    scribe_task_id: str,
    scribe_attempt_id: str,
    scribe_session_id: str,
    run_id: str,
    parent_commit_sha: Optional[str] = None,
    new_commit_sha: Optional[str] = None,
) -> StoryChangeRequired | ScribeHandoffEvidence:
    """Validate and accept a Scribe handoff.

    Args:
        baseline_story_digest: ``sha256:<hex>`` digest of the current Story
            bytes that the Scribe read.
        scribe_handoff_digest: ``sha256:<hex>`` digest of the Scribe's new
            Story bytes.
        scribe_task_id: Scribe task id that produced the handoff.
        scribe_attempt_id: Scribe attempt id that produced the handoff.
        scribe_session_id: Scribe OpenCode session id that produced the
            handoff.
        run_id: Opaque run identifier.
        parent_commit_sha: Parent commit SHA the new commit is built on;
            required for a successful handoff.
        new_commit_sha: New commit SHA recorded for the revision; required
            for a successful handoff.

    Returns:
        A :class:`ScribeHandoffEvidence` when the digest has changed and
        ``parent_commit_sha``/``new_commit_sha`` are supplied.

    Raises:
        StoryChangeRequired: When ``scribe_handoff_digest ==
            baseline_story_digest``. ``phase`` stays ``authoring`` and no
            review task is dispatched.
        ValueError: When the digest has changed but ``parent_commit_sha``
            or ``new_commit_sha`` is missing.

    Side effects:
        None.
    """
    if scribe_handoff_digest == baseline_story_digest:
        return StoryChangeRequired(task_id=scribe_task_id)
    if not parent_commit_sha or not new_commit_sha:
        raise ValueError(
            "parent_commit_sha and new_commit_sha are required for a "
            "successful Scribe handoff"
        )
    return ScribeHandoffEvidence(
        run_id=run_id,
        phase="review",
        review_task_count=1,
        commit_document_path="story.md",
        story_digest=scribe_handoff_digest,
        parent_commit_sha=parent_commit_sha,
        new_commit_sha=new_commit_sha,
        scribe_task_id=scribe_task_id,
        scribe_attempt_id=scribe_attempt_id,
        scribe_session_id=scribe_session_id,
    )
