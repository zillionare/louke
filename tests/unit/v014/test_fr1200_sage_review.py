"""FR-1200: Story 的独立 Sage Review 与多轮返工.

AC references:
- AC-FR1200-01: the first Story review round binds both Human and Sage
  reviews to the same handoff commit ``C`` and digest ``D``; the Sage
  session id is different from the Scribe session id; verdicts on any older
  digest are not counted as PASS.
- AC-FR1200-02: when Human submits a modification first (producing ``D2``),
  Sage's input includes the Human diff and is bound to ``D2``; the Human
  revision and Sage's comment correspond to two independent commits.
- AC-FR1200-03: when Human or Sage does not PASS, the original Scribe
  session produces a response revision ``D3``; ``D``/``D2`` verdicts are
  marked stale; the new round only reviews ``D3``; both Human and Sage
  PASS on ``D3`` advances the current step to M-SPEC.
"""

from __future__ import annotations

import pytest

from louke.v014.fr1200_sage_review import (
    M_STORY_ADVANCE_REQUIRED,
    MSpecAdvanceBlocked,
    ReviewVerdict,
    ReviewerRole,
    advance_to_m_spec_if_both_pass,
    build_sage_review_input,
    start_first_story_review_round,
    start_rework_round,
    verdict_is_stale,
)


def _commit(digest_char: str = "a") -> tuple[str, str]:
    return (f"c_{digest_char}" * 20, f"sha256:{digest_char * 64}")


# AC-FR1200-01 ---------------------------------------------------------------
def test_first_round_binds_human_and_sage_to_same_commit_and_digest() -> None:
    """AC-FR1200-01: both Human and Sage reviews bind to the handoff commit C
    and digest D; Sage session id != Scribe session id."""
    commit_sha, digest = _commit("a")
    round_ = start_first_story_review_round(
        story_commit_sha=commit_sha,
        story_digest=digest,
        scribe_session_id="sess_scribe",
        sage_session_id="sess_sage",
    )
    assert round_.round_number == 1
    assert round_.story_commit_sha == commit_sha
    assert round_.story_digest == digest
    assert round_.human_verdict is None
    assert round_.sage_verdict is None
    assert round_.scribe_session_id == "sess_scribe"
    assert round_.sage_session_id == "sess_sage"
    assert round_.sage_session_id != round_.scribe_session_id


def test_old_digest_verdict_does_not_count_as_pass() -> None:
    """AC-FR1200-01: a verdict bound to an older digest is stale and does not
    combine with a current verdict to advance to M-SPEC."""
    commit_sha, digest = _commit("a")
    round_ = start_first_story_review_round(
        story_commit_sha=commit_sha,
        story_digest=digest,
        scribe_session_id="sess_scribe",
        sage_session_id="sess_sage",
    )
    old_human_verdict = ReviewVerdict(
        reviewer_role=ReviewerRole.HUMAN,
        verdict="PASS",
        digest="sha256:" + "z" * 64,  # old digest
        commit_sha="old_commit",
        session_id=None,
    )
    assert verdict_is_stale(old_human_verdict, round_) is True


# AC-FR1200-02 ---------------------------------------------------------------
def test_sage_review_input_includes_human_diff_and_binds_to_d2() -> None:
    """AC-FR1200-02: when Human submits a modification first, Sage's input is
    bound to D2 and includes the Human diff; the Human revision and Sage's
    comment correspond to two independent commits."""
    commit_d1, digest_d1 = _commit("a")
    round_ = start_first_story_review_round(
        story_commit_sha=commit_d1,
        story_digest=digest_d1,
        scribe_session_id="sess_scribe",
        sage_session_id="sess_sage",
    )
    commit_d2, digest_d2 = _commit("b")
    human_diff = b"--- story.md\n+++ story.md\n@@ -1 +1 @@\n-old\n+new\n"
    sage_input = build_sage_review_input(
        round_=round_,
        human_commit_sha=commit_d2,
        human_digest=digest_d2,
        human_diff=human_diff,
    )
    assert sage_input.bound_digest == digest_d2
    assert sage_input.human_diff == human_diff
    assert sage_input.human_commit_sha == commit_d2
    # Sage input is bound to D2 (not D1).
    assert sage_input.bound_digest != digest_d1


def test_human_revision_and_sage_comment_are_independent_commits() -> None:
    """AC-FR1200-02: Human revision (D2) and Sage's comment revision are
    independent commits."""
    commit_d1, digest_d1 = _commit("a")
    round_ = start_first_story_review_round(
        story_commit_sha=commit_d1,
        story_digest=digest_d1,
        scribe_session_id="sess_scribe",
        sage_session_id="sess_sage",
    )
    commit_d2, digest_d2 = _commit("b")
    sage_input = build_sage_review_input(
        round_=round_,
        human_commit_sha=commit_d2,
        human_digest=digest_d2,
        human_diff=b"diff",
    )
    sage_commit_sha = "sage_comment_commit"
    sage_verdict = ReviewVerdict(
        reviewer_role=ReviewerRole.SAGE,
        verdict="REJECT",
        digest=sage_input.bound_digest,
        commit_sha=sage_commit_sha,
        session_id="sess_sage",
    )
    # Human revision commit != Sage comment commit.
    assert sage_verdict.commit_sha != commit_d2


# AC-FR1200-03 ---------------------------------------------------------------
def test_rework_round_marks_old_verdicts_stale_and_only_reviews_d3() -> None:
    """AC-FR1200-03: when Human or Sage does not PASS, the original Scribe
    session produces D3; D/D2 verdicts are stale; the new round only
    reviews D3."""
    commit_d1, digest_d1 = _commit("a")
    round_ = start_first_story_review_round(
        story_commit_sha=commit_d1,
        story_digest=digest_d1,
        scribe_session_id="sess_scribe",
        sage_session_id="sess_sage",
    )
    commit_d3, digest_d3 = _commit("c")
    round_3 = start_rework_round(
        previous_round=round_,
        new_story_commit_sha=commit_d3,
        new_story_digest=digest_d3,
    )
    assert round_3.round_number == 2
    assert round_3.story_commit_sha == commit_d3
    assert round_3.story_digest == digest_d3
    # Old verdicts (if any) on D1 are stale.
    old_human_verdict_d1 = ReviewVerdict(
        reviewer_role=ReviewerRole.HUMAN,
        verdict="PASS",
        digest=digest_d1,
        commit_sha=commit_d1,
        session_id=None,
    )
    assert verdict_is_stale(old_human_verdict_d1, round_3) is True


def test_advance_to_m_spec_requires_both_pass_on_current_digest() -> None:
    """AC-FR1200-03: both Human and Sage must PASS the current digest to
    advance to M-SPEC; any other combination is blocked."""
    commit_d3, digest_d3 = _commit("c")
    round_3 = start_first_story_review_round(
        story_commit_sha=commit_d3,
        story_digest=digest_d3,
        scribe_session_id="sess_scribe",
        sage_session_id="sess_sage",
    )
    human_pass = ReviewVerdict(
        reviewer_role=ReviewerRole.HUMAN,
        verdict="PASS",
        digest=digest_d3,
        commit_sha=commit_d3,
        session_id=None,
    )
    sage_pass = ReviewVerdict(
        reviewer_role=ReviewerRole.SAGE,
        verdict="PASS",
        digest=digest_d3,
        commit_sha="sage_commit",
        session_id="sess_sage",
    )
    decision = advance_to_m_spec_if_both_pass(round_3, human_pass, sage_pass)
    assert decision.can_advance is True
    assert decision.target_phase == "M-SPEC"

    sage_reject = ReviewVerdict(
        reviewer_role=ReviewerRole.SAGE,
        verdict="REJECT",
        digest=digest_d3,
        commit_sha="sage_commit",
        session_id="sess_sage",
    )
    blocked = advance_to_m_spec_if_both_pass(round_3, human_pass, sage_reject)
    assert blocked.can_advance is False
    assert blocked.reason == M_STORY_ADVANCE_REQUIRED


def test_advance_blocked_when_digests_do_not_match() -> None:
    """AC-FR1200-01 + AC-FR1200-03: a verdict whose digest does not match
    the current round's digest cannot advance to M-SPEC."""
    commit_d3, digest_d3 = _commit("c")
    round_3 = start_first_story_review_round(
        story_commit_sha=commit_d3,
        story_digest=digest_d3,
        scribe_session_id="sess_scribe",
        sage_session_id="sess_sage",
    )
    human_pass_stale = ReviewVerdict(
        reviewer_role=ReviewerRole.HUMAN,
        verdict="PASS",
        digest="sha256:" + "z" * 64,  # stale digest
        commit_sha="old_commit",
        session_id=None,
    )
    sage_pass = ReviewVerdict(
        reviewer_role=ReviewerRole.SAGE,
        verdict="PASS",
        digest=digest_d3,
        commit_sha="sage_commit",
        session_id="sess_sage",
    )
    with pytest.raises(MSpecAdvanceBlocked) as exc_info:
        advance_to_m_spec_if_both_pass(round_3, human_pass_stale, sage_pass)
    assert exc_info.value.code == "WORKFLOW_STATE_CONFLICT"
