"""FR-1100: Human Review 的编辑、Discussion 与明确结论.

Implements the deterministic contract slice of FR-1100:

* :func:`create_discussion_thread`/:func:`resolve_discussion_thread`/
  :func:`reopen_discussion_thread` produce :class:`DiscussionThread`
  records with a stable ``thread_id`` and status
  ``OPEN``/``RESOLVED``/``REOPEN``. The records follow the canonical
  blockquote contract so ``lk discuss query`` can identify them
  (AC-FR1100-01).

* :func:`compute_human_review_verdict` is the only authority for a Human
  review verdict. The verdict is PASS only when all of the following hold:

    - ``signal == 'no_comment'``
    - ``edited is False`` (no document bytes changed in this round)
    - ``open_threads == 0`` (no OPEN or REOPEN discussions)
    - ``dirty is False`` (no unsaved browser edits)

  Any other combination raises :class:`HumanReviewRejected` with a stable
  code:

    - ``HUMAN_REVIEW_EDITED`` when ``edited is True`` and signal is
      ``no_comment`` (AC-FR1100-02).
    - ``HUMAN_REVIEW_DIRTY`` when ``dirty is True``.
    - ``HUMAN_REVIEW_OPEN_THREADS`` when ``open_threads > 0``.
    - ``HUMAN_REVIEW_COMMENT`` when ``signal == 'comment'``.
    - ``VALIDATION_FAILED`` for unknown signals.

  The PASS verdict is bound to the current artifact revision and digest
  (AC-FR1100-03).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum


HUMAN_REVIEW_EDITED = "HUMAN_REVIEW_EDITED"
HUMAN_REVIEW_DIRTY = "HUMAN_REVIEW_DIRTY"
HUMAN_REVIEW_OPEN_THREADS = "HUMAN_REVIEW_OPEN_THREADS"
HUMAN_REVIEW_COMMENT = "HUMAN_REVIEW_COMMENT"


class DiscussionThreadStatus(str, Enum):
    """Status of an inline-discussion thread.

    Members:
        OPEN: Thread is open and awaiting response.
        RESOLVED: Human or Agent has marked the thread resolved.
        REOPEN: A previously resolved thread has been reopened.
    """

    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    REOPEN = "REOPEN"


@dataclass(frozen=True)
class DiscussionThread:
    """An inline-discussion thread bound to an artifact revision.

    Attributes:
        thread_id: Stable opaque identifier; queryable by ``lk discuss query``.
        artifact_revision: Artifact revision the thread is anchored to.
        anchor: Anchor within the document (e.g. ``story.md#L42``).
        initiator: Non-secret identity of the thread creator.
        last_speaker: Non-secret identity of the last replier; ``None`` until
            a reply is recorded.
        body: The thread body text.
        status: :class:`DiscussionThreadStatus`.
    """

    thread_id: str
    artifact_revision: int
    anchor: str
    initiator: str
    last_speaker: str | None
    body: str
    status: DiscussionThreadStatus


def create_discussion_thread(
    *,
    artifact_revision: int,
    anchor: str,
    initiator: str,
    body: str,
) -> DiscussionThread:
    """Create a new OPEN discussion thread bound to ``artifact_revision``.

    Args:
        artifact_revision: Artifact revision the thread is anchored to.
        anchor: Anchor within the document.
        initiator: Non-secret identity of the thread creator.
        body: The thread body text.

    Returns:
        A :class:`DiscussionThread` with status ``OPEN`` and a fresh
        ``thread_id``.

    Side effects:
        None.
    """
    if not body.strip():
        raise ValueError("discussion thread body must be non-empty")
    return DiscussionThread(
        thread_id=f"thread_{uuid.uuid4().hex[:16]}",
        artifact_revision=artifact_revision,
        anchor=anchor,
        initiator=initiator,
        last_speaker=initiator,
        body=body,
        status=DiscussionThreadStatus.OPEN,
    )


def resolve_discussion_thread(
    thread: DiscussionThread,
    *,
    last_speaker: str,
) -> DiscussionThread:
    """Mark ``thread`` as RESOLVED.

    Args:
        thread: The thread to resolve.
        last_speaker: Non-secret identity of the resolver.

    Returns:
        A new :class:`DiscussionThread` with status ``RESOLVED``.

    Raises:
        ValueError: If ``thread`` is already RESOLVED.
    """
    if thread.status == DiscussionThreadStatus.RESOLVED:
        raise ValueError(f"thread {thread.thread_id!r} is already RESOLVED")
    from dataclasses import replace

    return replace(
        thread,
        status=DiscussionThreadStatus.RESOLVED,
        last_speaker=last_speaker,
    )


def reopen_discussion_thread(
    thread: DiscussionThread,
    *,
    last_speaker: str,
) -> DiscussionThread:
    """Reopen a previously RESOLVED ``thread``.

    Args:
        thread: The thread to reopen.
        last_speaker: Non-secret identity of the reopener.

    Returns:
        A new :class:`DiscussionThread` with status ``REOPEN``.

    Raises:
        ValueError: If ``thread`` is not RESOLVED.
    """
    if thread.status != DiscussionThreadStatus.RESOLVED:
        raise ValueError(
            f"thread {thread.thread_id!r} cannot be reopened from status {thread.status.value}"
        )
    from dataclasses import replace

    return replace(
        thread,
        status=DiscussionThreadStatus.REOPEN,
        last_speaker=last_speaker,
    )


class HumanReviewVerdict(str, Enum):
    """Human review verdict.

    Members:
        PASS: Clean ``no_comment`` on the current revision with no edits, no
            dirty state and no open/reopen threads.
        NOT_PASS: Any other combination. (Verdicts that fail in
            :func:`compute_human_review_verdict` raise
            :class:`HumanReviewRejected` instead of returning NOT_PASS, but
            the value is exposed for comparison.)
    """

    PASS = "PASS"
    NOT_PASS = "NOT_PASS"


@dataclass(frozen=True)
class HumanReviewInput:
    """Inputs to :func:`compute_human_review_verdict`.

    Attributes:
        signal: ``comment`` or ``no_comment``.
        edited: ``True`` when at least one byte of the document was changed
            in this round.
        open_threads: Number of OPEN or REOPEN discussion threads on the
            current revision.
        dirty: ``True`` when the browser has unsaved edits.
        artifact_revision: Current artifact revision.
        artifact_digest: ``sha256:<hex>`` digest of the current artifact bytes.
    """

    signal: str
    edited: bool
    open_threads: int
    dirty: bool
    artifact_revision: int
    artifact_digest: str


@dataclass(frozen=True)
class HumanReviewVerdictRecord:
    """A recorded Human review verdict.

    Attributes:
        verdict: :class:`HumanReviewVerdict`.
        artifact_revision: The artifact revision the verdict is bound to.
        artifact_digest: The ``sha256:<hex>`` digest the verdict is bound to.
    """

    verdict: HumanReviewVerdict
    artifact_revision: int
    artifact_digest: str


class HumanReviewRejected(Exception):
    """Raised when a Human review verdict cannot be PASS.

    Attributes:
        code: One of :data:`HUMAN_REVIEW_EDITED`,
            :data:`HUMAN_REVIEW_DIRTY`, :data:`HUMAN_REVIEW_OPEN_THREADS`,
            :data:`HUMAN_REVIEW_COMMENT` or ``VALIDATION_FAILED``.
        verdict: Always :data:`HumanReviewVerdict.NOT_PASS`.
    """

    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.verdict = HumanReviewVerdict.NOT_PASS


_LEGAL_SIGNALS: frozenset[str] = frozenset({"comment", "no_comment"})


def compute_human_review_verdict(
    inp: HumanReviewInput,
) -> HumanReviewVerdictRecord:
    """Compute the Human review verdict for ``inp``.

    Args:
        inp: The :class:`HumanReviewInput` for the round.

    Returns:
        A :class:`HumanReviewVerdictRecord` with verdict ``PASS`` only when
        ``signal == 'no_comment'`` AND ``not edited`` AND
        ``open_threads == 0`` AND ``not dirty``. The PASS is bound to the
        current artifact revision/digest.

    Raises:
        HumanReviewRejected: For any non-PASS combination. ``code`` is
            ``VALIDATION_FAILED`` for unknown signals; otherwise it
            identifies the first blocking condition in the order: edited,
            dirty, open_threads, comment.

    Side effects:
        None.
    """
    if inp.signal not in _LEGAL_SIGNALS:
        raise HumanReviewRejected(
            code="VALIDATION_FAILED",
            message=(
                f"signal must be one of {sorted(_LEGAL_SIGNALS)}; got {inp.signal!r}"
            ),
        )
    if inp.signal == "no_comment":
        if inp.edited:
            raise HumanReviewRejected(
                code=HUMAN_REVIEW_EDITED,
                message=(
                    "no_comment is not allowed after Human edited at least "
                    "one byte in this round; submit comment instead"
                ),
            )
        if inp.dirty:
            raise HumanReviewRejected(
                code=HUMAN_REVIEW_DIRTY,
                message=(
                    "no_comment is not allowed while the browser has unsaved "
                    "edits; save or discard first"
                ),
            )
        if inp.open_threads > 0:
            raise HumanReviewRejected(
                code=HUMAN_REVIEW_OPEN_THREADS,
                message=(
                    f"no_comment is not allowed with {inp.open_threads} "
                    "open/reopen thread(s); resolve or comment first"
                ),
            )
        return HumanReviewVerdictRecord(
            verdict=HumanReviewVerdict.PASS,
            artifact_revision=inp.artifact_revision,
            artifact_digest=inp.artifact_digest,
        )
    # signal == 'comment'
    raise HumanReviewRejected(
        code=HUMAN_REVIEW_COMMENT,
        message=(
            "comment signal does not produce a PASS; the author must respond "
            "and produce a new revision"
        ),
    )
