"""AC-FR2400-01: Human-optional review & direct diff.

FR-2400 requires the M-DESIGN document surface to allow Human to view,
comment, or directly edit authorised artifacts, but Human may be absent.
Runtime must supply the diff since the last baseline plus inline discussions
to Archer, deduplicating repeats; Archer accepts reasonable edits, raises
inline discussions for technical problems, and Human authorship does not
auto-approve or constitute a new technical gate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from louke.v014.fr2400_human_review import (
    DirectDiff,
    HumanReviewError,
    InlineDiscussion,
    ReviewBundle,
    aggregate_human_review_input,
    build_inline_discussion,
    is_human_absent,
    verify_direct_diff_in_scope,
    verify_human_absent_does_not_block_baseline,
)

_SPEC_ID = "v0.14-002-workflow-reflow-design"
_SPEC_ROOT = (
    Path(__file__).resolve().parents[3] / ".louke" / "project" / "specs" / _SPEC_ID
)


def _design_doc_paths() -> list[str]:
    return [
        f".louke/project/specs/{_SPEC_ID}/test-plan.md",
        f".louke/project/specs/{_SPEC_ID}/architecture.md",
        f".louke/project/specs/{_SPEC_ID}/interfaces.md",
    ]


def _make_direct_diff(
    path: str = f".louke/project/specs/{_SPEC_ID}/architecture.md",
    actor_id: str = "human:alice",
) -> DirectDiff:
    return DirectDiff(
        path=path,
        actor_id=actor_id,
        base_digest="sha256:" + "a" * 64,
        current_digest="sha256:" + "b" * 64,
        inline_discussions=(),
    )


def test_is_human_absent_returns_true_for_no_diffs() -> None:
    """AC-FR2400-01: no diffs and no comments => Human absent."""
    assert is_human_absent(diffs=(), comments=()) is True


def test_is_human_absent_returns_false_when_diff_present() -> None:
    """AC-FR2400-01: a direct diff => Human present."""
    diff = _make_direct_diff()
    assert is_human_absent(diffs=(diff,), comments=()) is False


def test_human_absent_does_not_block_baseline() -> None:
    """AC-FR2400-01: Human absence does not block baseline."""
    verify_human_absent_does_not_block_baseline(diffs=(), comments=())  # no raise


def test_direct_diff_in_scope_is_accepted() -> None:
    """AC-FR2400-01: a direct diff on an authorised path is accepted."""
    diff = _make_direct_diff()
    verify_direct_diff_in_scope(diff, allowed_paths=_design_doc_paths())  # no raise


def test_direct_diff_out_of_scope_is_rejected() -> None:
    """AC-FR2400-01: a direct diff outside the authorised paths is rejected."""
    diff = _make_direct_diff(path="louke/v014/fr2400_human_review.py")
    with pytest.raises(HumanReviewError) as exc:
        verify_direct_diff_in_scope(diff, allowed_paths=_design_doc_paths())
    assert exc.value.code == "HUMAN_DIFF_OUT_OF_SCOPE"


def test_direct_diff_without_actor_rejected() -> None:
    """AC-FR2400-01: a direct diff without actor identity is rejected."""
    diff = _make_direct_diff(actor_id="")
    with pytest.raises(HumanReviewError) as exc:
        verify_direct_diff_in_scope(diff, allowed_paths=_design_doc_paths())
    assert exc.value.code == "HUMAN_DIFF_UNATTRIBUTED"


def test_build_inline_discussion_anchors_to_source_text() -> None:
    """AC-FR2400-01: a technical-problem direct edit creates an anchored discussion."""
    discussion = build_inline_discussion(
        anchor_path=f".louke/project/specs/{_SPEC_ID}/architecture.md",
        anchor_text="Section 3 dependency flow",
        message="This dependency direction conflicts with FR-0300",
        raised_by="archer:att-1",
    )
    assert isinstance(discussion, InlineDiscussion)
    assert discussion.anchor_path
    assert discussion.anchor_text
    assert discussion.message
    assert discussion.raised_by


def test_aggregate_human_review_input_deduplicates_repeated_discussions() -> None:
    """AC-FR2400-01: repeated discussions from the previous round are deduplicated."""
    diff = _make_direct_diff()
    prior_discussion = InlineDiscussion(
        anchor_path=diff.path,
        anchor_text="old text",
        message="previously raised issue",
        raised_by="archer:att-0",
    )
    new_discussion = InlineDiscussion(
        anchor_path=diff.path,
        anchor_text="old text",
        message="previously raised issue",
        raised_by="archer:att-1",
    )
    bundle = aggregate_human_review_input(
        diffs=(diff,),
        comments=(),
        prior_discussions=(prior_discussion,),
        new_discussions=(new_discussion,),
    )
    assert isinstance(bundle, ReviewBundle)
    # The new discussion duplicates the prior one and should be deduplicated
    assert len(bundle.deduplicated_discussions) <= 1


def test_aggregate_human_review_input_includes_diffs_and_comments() -> None:
    """AC-FR2400-01: the review input includes diffs and comments."""
    diff = _make_direct_diff()
    bundle = aggregate_human_review_input(
        diffs=(diff,),
        comments=("LGTM",),
        prior_discussions=(),
        new_discussions=(),
    )
    assert bundle.diffs == (diff,)
    assert bundle.comments == ("LGTM",)


def test_human_authorship_does_not_auto_approve() -> None:
    """AC-FR2400-01: Human authorship of a direct diff does not auto-approve."""
    diff = _make_direct_diff(actor_id="human:ceo")
    bundle = aggregate_human_review_input(
        diffs=(diff,),
        comments=(),
        prior_discussions=(),
        new_discussions=(),
    )
    assert bundle.auto_approved is False


def test_review_bundle_is_immutable() -> None:
    """AC-FR2400-01: the review bundle is an immutable value object."""
    bundle = aggregate_human_review_input(
        diffs=(),
        comments=(),
        prior_discussions=(),
        new_discussions=(),
    )
    with pytest.raises(Exception):
        bundle.diffs = (_make_direct_diff(),)  # type: ignore[misc]


def test_no_new_discussion_for_unproblematic_edit() -> None:
    """AC-FR2400-01: Archer may not create a discussion for an unproblematic edit."""
    diff = _make_direct_diff()
    bundle = aggregate_human_review_input(
        diffs=(diff,),
        comments=(),
        prior_discussions=(),
        new_discussions=(),  # no new discussion needed
    )
    assert bundle.deduplicated_discussions == ()
