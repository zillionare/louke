"""FR-2400: Human-optional review & direct diff.

The M-DESIGN document surface allows Human to view, comment, or directly
edit authorised artifacts, but Human may be absent.  Runtime supplies the
direct diff since the last baseline plus inline discussions to Archer,
deduplicating repeats; Archer accepts reasonable edits, raises inline
discussions for technical problems, and Human authorship does not
auto-approve or constitute a new technical gate (AC-FR2400-01).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

ERROR_CODES = (
    "HUMAN_DIFF_OUT_OF_SCOPE",
    "HUMAN_DIFF_UNATTRIBUTED",
    "HUMAN_AUTO_APPROVE_FORBIDDEN",
)


class HumanReviewError(Exception):
    """A fail-closed Human-review rejection carrying a stable code."""

    __test__ = False

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class DirectDiff:
    """A direct diff attributed to a Human actor (AC-FR2400-01).

    Attributes:
        path: Edited path relative to the workspace root.
        actor_id: Identity of the editing actor (e.g. ``human:alice``).
        base_digest: ``sha256:<hex>`` of the file bytes before the edit.
        current_digest: ``sha256:<hex>`` of the file bytes after the edit.
        inline_discussions: Discussions anchored to this diff.
    """

    path: str
    actor_id: str
    base_digest: str
    current_digest: str
    inline_discussions: tuple["InlineDiscussion", ...] = ()


@dataclass(frozen=True)
class InlineDiscussion:
    """An inline discussion anchored to a source-text location.

    Attributes:
        anchor_path: Path of the anchored artifact.
        anchor_text: Source-text anchor (e.g. a section heading or quoted line).
        message: The discussion message.
        raised_by: Identity of the raising actor.
    """

    anchor_path: str
    anchor_text: str
    message: str
    raised_by: str


@dataclass(frozen=True)
class ReviewBundle:
    """The aggregated Human review input for the next Archer round.

    Attributes:
        diffs: Direct diffs since the last baseline.
        comments: Free-text Human comments.
        prior_discussions: Discussions raised in the previous round.
        deduplicated_discussions: New discussions after deduplication against
            prior ones.  Archer does not re-raise the same issue.
        auto_approved: Always ``False`` - Human authorship does not auto-approve.
    """

    diffs: tuple[DirectDiff, ...] = ()
    comments: tuple[str, ...] = ()
    prior_discussions: tuple[InlineDiscussion, ...] = ()
    deduplicated_discussions: tuple[InlineDiscussion, ...] = ()
    auto_approved: bool = False


def is_human_absent(
    *,
    diffs: Iterable[DirectDiff],
    comments: Iterable[str],
) -> bool:
    """Return ``True`` if Human is absent (no diffs and no comments)."""
    return not tuple(diffs) and not tuple(comments)


def verify_human_absent_does_not_block_baseline(
    *,
    diffs: Iterable[DirectDiff],
    comments: Iterable[str],
) -> None:
    """Verify Human absence does not block the baseline (AC-FR2400-01).

    Human absence is allowed; the baseline proceeds via Archer + program
    gates + Prism review.
    """
    # No check needed; absence is a valid state.
    return


def verify_direct_diff_in_scope(
    diff: DirectDiff,
    *,
    allowed_paths: list[str],
) -> None:
    """Verify a direct diff falls within the authorised write set.

    Args:
        diff: The direct diff to verify.
        allowed_paths: List of paths Human is authorised to edit.

    Raises:
        HumanReviewError: With ``HUMAN_DIFF_OUT_OF_SCOPE`` if the path is
            outside the authorised set, or ``HUMAN_DIFF_UNATTRIBUTED`` if the
            actor identity is empty.
    """
    if not diff.actor_id:
        raise HumanReviewError(
            "HUMAN_DIFF_UNATTRIBUTED",
            f"direct diff at {diff.path} has no actor_id",
        )
    if diff.path not in allowed_paths:
        raise HumanReviewError(
            "HUMAN_DIFF_OUT_OF_SCOPE",
            f"direct diff path {diff.path} is outside the authorised set",
        )


def build_inline_discussion(
    *,
    anchor_path: str,
    anchor_text: str,
    message: str,
    raised_by: str,
) -> InlineDiscussion:
    """Build an inline discussion anchored to a source-text location."""
    if not anchor_path or not anchor_text or not message or not raised_by:
        raise HumanReviewError(
            "HUMAN_DIFF_UNATTRIBUTED",
            "inline discussion requires anchor_path/text/message/raised_by",
        )
    return InlineDiscussion(
        anchor_path=anchor_path,
        anchor_text=anchor_text,
        message=message,
        raised_by=raised_by,
    )


def _discussion_key(d: InlineDiscussion) -> tuple[str, str, str]:
    """Return a deduplication key for an inline discussion."""
    return (d.anchor_path, d.anchor_text, d.message.lower())


def aggregate_human_review_input(
    *,
    diffs: Iterable[DirectDiff],
    comments: Iterable[str],
    prior_discussions: Iterable[InlineDiscussion],
    new_discussions: Iterable[InlineDiscussion],
) -> ReviewBundle:
    """Aggregate Human review input for the next Archer round.

    Deduplicates new discussions against prior ones - Archer does not re-raise
    the same issue.  Human authorship of a direct diff does not auto-approve.

    Args:
        diffs: Direct diffs since the last baseline.
        comments: Free-text Human comments.
        prior_discussions: Discussions raised in the previous round.
        new_discussions: New discussions raised in this round.

    Returns:
        A :class:`ReviewBundle` with deduplicated discussions.
    """
    prior_keys = {_discussion_key(d) for d in prior_discussions}
    deduplicated: list[InlineDiscussion] = []
    for d in new_discussions:
        key = _discussion_key(d)
        if key in prior_keys:
            continue
        prior_keys.add(key)
        deduplicated.append(d)
    return ReviewBundle(
        diffs=tuple(diffs),
        comments=tuple(comments),
        prior_discussions=tuple(prior_discussions),
        deduplicated_discussions=tuple(deduplicated),
        auto_approved=False,
    )
