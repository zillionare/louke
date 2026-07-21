"""FR-1200: Story 的独立 Sage Review 与多轮返工.

Implements the deterministic contract slice of FR-1200:

* :func:`start_first_story_review_round` opens the first review round bound
  to the handoff commit ``C`` and digest ``D``. The Sage session id is
  required to differ from the Scribe session id; both Human and Sage
  verdicts must bind to ``D`` to count (AC-FR1200-01).

* :func:`build_sage_review_input` produces the Sage input for the case where
  Human submits a modification first (``D2``). The input is bound to ``D2``
  and includes the Human diff; the Human revision commit and Sage's comment
  commit are independent (AC-FR1200-02).

* :func:`start_rework_round` starts a new round bound to the Scribe's
  response revision ``D3``. Verdicts on older digests are stale
  (AC-FR1200-03).

* :func:`advance_to_m_spec_if_both_pass` decides whether the run may advance
  to M-SPEC. Both Human and Sage must PASS the current round's digest; any
  other combination is blocked (AC-FR1200-03). A stale-digest verdict
  raises :class:`MSpecAdvanceBlocked` with code ``WORKFLOW_STATE_CONFLICT``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


M_STORY_ADVANCE_REQUIRED = "M_STORY_ADVANCE_REQUIRED"


class ReviewerRole(str, Enum):
    """Role of a reviewer.

    Members:
        HUMAN: The authenticated Human principal.
        SAGE: The independent Sage reviewer Agent.
    """

    HUMAN = "human"
    SAGE = "sage"


@dataclass(frozen=True)
class ReviewVerdict:
    """A review verdict bound to a digest.

    Attributes:
        reviewer_role: :class:`ReviewerRole` that produced the verdict.
        verdict: ``PASS`` or ``REJECT``.
        digest: ``sha256:<hex>`` digest of the artifact the verdict is bound
            to.
        commit_sha: Commit SHA the verdict is bound to.
        session_id: OpenCode session id when the reviewer is an Agent;
            ``None`` for Human.
    """

    reviewer_role: ReviewerRole
    verdict: str
    digest: str
    commit_sha: str
    session_id: Optional[str]


@dataclass(frozen=True)
class ReviewRound:
    """A Story review round.

    Attributes:
        round_number: 1 for the first round, incremented on each rework.
        story_commit_sha: Commit SHA of the Story revision under review.
        story_digest: ``sha256:<hex>`` digest of the Story revision under
            review.
        scribe_session_id: Scribe OpenCode session id (continues across
            rounds).
        sage_session_id: Sage reviewer OpenCode session id; must differ from
            ``scribe_session_id``.
        human_verdict: Recorded Human verdict, or ``None`` until submitted.
        sage_verdict: Recorded Sage verdict, or ``None`` until submitted.
    """

    round_number: int
    story_commit_sha: str
    story_digest: str
    scribe_session_id: str
    sage_session_id: str
    human_verdict: Optional[ReviewVerdict] = None
    sage_verdict: Optional[ReviewVerdict] = None


def start_first_story_review_round(
    *,
    story_commit_sha: str,
    story_digest: str,
    scribe_session_id: str,
    sage_session_id: str,
) -> ReviewRound:
    """Open the first Story review round.

    Args:
        story_commit_sha: Handoff commit SHA.
        story_digest: Handoff digest.
        scribe_session_id: Scribe OpenCode session id.
        sage_session_id: Sage reviewer OpenCode session id; must differ from
            ``scribe_session_id``.

    Returns:
        A :class:`ReviewRound` with ``round_number == 1`` and no verdicts.

    Raises:
        ValueError: If ``sage_session_id == scribe_session_id`` (AC-FR1200-01
            requires independent sessions).
    """
    if sage_session_id == scribe_session_id:
        raise ValueError(
            "Sage reviewer session must differ from Scribe author session "
            "(AC-FR1200-01)"
        )
    return ReviewRound(
        round_number=1,
        story_commit_sha=story_commit_sha,
        story_digest=story_digest,
        scribe_session_id=scribe_session_id,
        sage_session_id=sage_session_id,
    )


def start_rework_round(
    *,
    previous_round: ReviewRound,
    new_story_commit_sha: str,
    new_story_digest: str,
) -> ReviewRound:
    """Open a rework round bound to the Scribe's response revision ``D3``.

    Args:
        previous_round: The previous :class:`ReviewRound`.
        new_story_commit_sha: Commit SHA of the new Story revision (``D3``).
        new_story_digest: ``sha256:<hex>`` digest of the new Story revision.

    Returns:
        A new :class:`ReviewRound` with ``round_number == previous_round.round_number + 1``,
        the same Scribe/Sage session ids (sessions continue) and no verdicts.
        Verdicts from ``previous_round`` are not carried over; they are
        considered stale (AC-FR1200-03).
    """
    return ReviewRound(
        round_number=previous_round.round_number + 1,
        story_commit_sha=new_story_commit_sha,
        story_digest=new_story_digest,
        scribe_session_id=previous_round.scribe_session_id,
        sage_session_id=previous_round.sage_session_id,
    )


def verdict_is_stale(verdict: ReviewVerdict, round_: ReviewRound) -> bool:
    """Return ``True`` when ``verdict`` is bound to a digest other than the
    current round's digest.

    Args:
        verdict: The verdict to check.
        round_: The current :class:`ReviewRound`.

    Returns:
        ``True`` when ``verdict.digest != round_.story_digest``; ``False``
        otherwise.
    """
    return verdict.digest != round_.story_digest


@dataclass(frozen=True)
class SageReviewInput:
    """Sage reviewer input for a round where Human modified first.

    Attributes:
        bound_digest: ``sha256:<hex>`` digest of the Human-modified Story
            revision (``D2``).
        human_diff: Diff bytes between the previous Story revision and the
            Human-modified revision.
        human_commit_sha: Commit SHA of the Human-modified Story revision.
        sage_session_id: Sage reviewer OpenCode session id.
    """

    bound_digest: str
    human_diff: bytes
    human_commit_sha: str
    sage_session_id: str


def build_sage_review_input(
    *,
    round_: ReviewRound,
    human_commit_sha: str,
    human_digest: str,
    human_diff: bytes,
) -> SageReviewInput:
    """Build the Sage reviewer input when Human modifies first.

    Args:
        round_: The current :class:`ReviewRound`.
        human_commit_sha: Commit SHA of the Human-modified Story revision
            (``D2``).
        human_digest: ``sha256:<hex>`` digest of the Human-modified Story
            revision.
        human_diff: Diff bytes between the previous Story revision and the
            Human-modified revision.

    Returns:
        A :class:`SageReviewInput` bound to ``human_digest`` and including
        the Human diff. The Human revision commit and Sage's eventual
        comment commit are independent (AC-FR1200-02).
    """
    return SageReviewInput(
        bound_digest=human_digest,
        human_diff=human_diff,
        human_commit_sha=human_commit_sha,
        sage_session_id=round_.sage_session_id,
    )


@dataclass(frozen=True)
class StoryRoundAdvanceDecision:
    """Decision returned by :func:`advance_to_m_spec_if_both_pass`.

    Attributes:
        can_advance: ``True`` when both Human and Sage PASS the current
            round's digest; ``False`` otherwise.
        target_phase: ``M-SPEC`` when ``can_advance``; ``M-STORY`` otherwise.
        reason: ``M_STORY_ADVANCE_REQUIRED`` when ``not can_advance``; empty
            otherwise.
    """

    can_advance: bool
    target_phase: str
    reason: str = ""


class MSpecAdvanceBlocked(Exception):
    """Raised when a verdict with a stale digest is submitted for advancement.

    Attributes:
        code: Always ``WORKFLOW_STATE_CONFLICT``.
    """

    def __init__(self, *, message: str) -> None:
        super().__init__(f"WORKFLOW_STATE_CONFLICT: {message}")
        self.code = "WORKFLOW_STATE_CONFLICT"


def advance_to_m_spec_if_both_pass(
    round_: ReviewRound,
    human_verdict: ReviewVerdict,
    sage_verdict: ReviewVerdict,
) -> StoryRoundAdvanceDecision:
    """Decide whether the run may advance to M-SPEC.

    Args:
        round_: The current :class:`ReviewRound`.
        human_verdict: The recorded Human verdict.
        sage_verdict: The recorded Sage verdict.

    Returns:
        A :class:`StoryRoundAdvanceDecision`. ``can_advance is True`` only
        when both verdicts are ``PASS`` AND both verdicts' digests equal
        ``round_.story_digest``.

    Raises:
        MSpecAdvanceBlocked: When either verdict's digest does not match
            ``round_.story_digest``. Code is ``WORKFLOW_STATE_CONFLICT``;
            the run cannot advance via stale-digest verdicts
            (AC-FR1200-01, AC-FR1200-03).
    """
    if verdict_is_stale(human_verdict, round_) or verdict_is_stale(
        sage_verdict, round_
    ):
        raise MSpecAdvanceBlocked(
            message=(
                "cannot advance to M-SPEC: a verdict is bound to a stale "
                f"digest (round digest={round_.story_digest}, "
                f"human verdict digest={human_verdict.digest}, "
                f"sage verdict digest={sage_verdict.digest})"
            )
        )
    if human_verdict.verdict == "PASS" and sage_verdict.verdict == "PASS":
        return StoryRoundAdvanceDecision(
            can_advance=True,
            target_phase="M-SPEC",
            reason="",
        )
    return StoryRoundAdvanceDecision(
        can_advance=False,
        target_phase="M-STORY",
        reason=M_STORY_ADVANCE_REQUIRED,
    )
