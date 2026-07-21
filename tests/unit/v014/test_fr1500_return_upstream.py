"""FR-1500: Human 主导的合法返回上游.

AC references:
- AC-FR1500-01: from M-SPEC the only legal return target is M-STORY; from
  M-ACC the legal targets are M-SPEC and M-STORY. Submitting any other
  target is rejected with ``UPSTREAM_RETURN_TARGET_INVALID`` and the
  revision/phase do not change.
- AC-FR1500-02: when Human confirms a legal target T, Runtime preserves the
  historical artifact/review ledger, marks T and its downstream verdicts/
  format results/approval evidence as ``stale``/``superseded``, sets the
  current step to T and does not delete Git history.
- AC-FR1500-03: an Agent suggestion to return upstream only produces a
  Human wait; the run's step and revision do not change until Human
  confirms.
"""

from __future__ import annotations

import pytest

from louke.v014.fr1500_return_upstream import (
    UPSTREAM_RETURN_TARGET_INVALID,
    AgentReturnSuggestion,
    ReturnUpstreamDecision,
    ReturnUpstreamForbidden,
    apply_return_upstream,
    legal_return_targets,
    record_agent_return_suggestion,
)


# AC-FR1500-01 ---------------------------------------------------------------
def test_legal_return_targets_from_m_spec() -> None:
    """AC-FR1500-01: from M-SPEC the only legal return target is M-STORY."""
    targets = legal_return_targets("M-SPEC")
    assert targets == ("M-STORY",)


def test_legal_return_targets_from_m_acc() -> None:
    """AC-FR1500-01: from M-ACC the legal return targets are M-SPEC and
    M-STORY."""
    targets = legal_return_targets("M-ACC")
    assert targets == ("M-SPEC", "M-STORY")


def test_legal_return_targets_from_m_story_or_m_lock_1_is_empty() -> None:
    """AC-FR1500-01: M-STORY and M-LOCK-1 do not expose return targets."""
    assert legal_return_targets("M-STORY") == ()
    assert legal_return_targets("M-LOCK-1") == ()


def test_return_to_illegal_target_is_rejected() -> None:
    """AC-FR1500-01: submitting an illegal target is rejected with
    UPSTREAM_RETURN_TARGET_INVALID; the revision/phase do not change."""
    with pytest.raises(ReturnUpstreamForbidden) as exc_info:
        apply_return_upstream(
            current_phase="M-SPEC",
            target="M-ACC",  # not a legal return target from M-SPEC
            expected_revision=3,
            actor_kind="human",
        )
    assert exc_info.value.code == UPSTREAM_RETURN_TARGET_INVALID
    assert exc_info.value.current_phase == "M-SPEC"
    assert exc_info.value.current_revision == 3
    assert exc_info.value.legal_targets == ("M-STORY",)


def test_return_by_agent_actor_is_rejected() -> None:
    """AC-FR1500-01 + IF-COMMON-01: an Agent-transport caller cannot return
    upstream; only an authenticated Human principal may."""
    with pytest.raises(ReturnUpstreamForbidden) as exc_info:
        apply_return_upstream(
            current_phase="M-ACC",
            target="M-STORY",
            expected_revision=5,
            actor_kind="agent",
        )
    assert exc_info.value.code == "HUMAN_AUTHORITY_REQUIRED"


# AC-FR1500-02 ---------------------------------------------------------------
def test_apply_return_upstream_marks_downstream_verdicts_stale_and_keeps_git() -> None:
    """AC-FR1500-02: applying a legal return preserves the ledger, marks
    downstream verdicts/format/approval as stale/superseded, sets the
    current step to the target and does not delete Git history."""
    decision = apply_return_upstream(
        current_phase="M-SPEC",
        target="M-STORY",
        expected_revision=3,
        actor_kind="human",
    )
    assert isinstance(decision, ReturnUpstreamDecision)
    assert decision.new_phase == "M-STORY"
    assert decision.new_revision == 4
    assert decision.git_history_deleted is False
    assert "spec_verdict" in decision.stale_evidence
    assert "spec_format" in decision.stale_evidence
    assert "acceptance_verdict" in decision.stale_evidence
    assert "m_lock_1_approval" in decision.stale_evidence


def test_apply_return_from_m_acc_to_m_story_marks_all_downstream() -> None:
    """AC-FR1500-02: returning from M-ACC to M-STORY marks Spec and
    Acceptance verdicts/format/approval as stale."""
    decision = apply_return_upstream(
        current_phase="M-ACC",
        target="M-STORY",
        expected_revision=7,
        actor_kind="human",
    )
    assert decision.new_phase == "M-STORY"
    assert "spec_verdict" in decision.stale_evidence
    assert "acceptance_verdict" in decision.stale_evidence


# AC-FR1500-03 ---------------------------------------------------------------
def test_agent_return_suggestion_does_not_move_step_or_revision() -> None:
    """AC-FR1500-03: an Agent suggestion to return upstream only produces a
    Human wait; the run's step and revision do not change until Human
    confirms."""
    suggestion = record_agent_return_suggestion(
        current_phase="M-SPEC",
        suggested_target="M-STORY",
        reasoning="The Story is missing a user scenario.",
        agent_identity="agent:lex",
    )
    assert isinstance(suggestion, AgentReturnSuggestion)
    assert suggestion.run_status == "waiting_human"
    assert suggestion.current_phase == "M-SPEC"
    assert suggestion.current_revision is None  # unchanged
    assert suggestion.suggested_target == "M-STORY"
    assert suggestion.requires_human_confirmation is True
