"""FR-0700: Scribe 调查、分流建议与 Human 裁决.

AC references:
- AC-FR0700-01: M-STORY starts and the Story revision is R; Runtime
  dispatches a Scribe investigation. The Scribe task manifest must contain
  run/step/attempt, spec id, R and its digest, Story template path and
  version/digest, the human's original request, Foundation manifest identity
  and (in non-first rounds) the digests of previous feedback.
- AC-FR0700-02: Scribe returns a Go/Park/No-Go suggestion with reasoning;
  until Human decides the run stays ``waiting_human`` and the current step
  remains M-STORY; no M-SPEC task is dispatched.
- AC-FR0700-03: a Human decision on a stale revision, by an Agent identity
  or with a value outside {Go, Park, No-Go} is rejected and the decision
  record remains empty. A valid Human decision on R records actor, R, value
  and time.
"""

from __future__ import annotations

import pytest

from louke.runtime.scribe_dispatch import (
    FOUNDATION_MANIFEST_REQUIRED,
    DecisionRejected,
    ScribeSuggestion,
    ScribeTaskManifest,
    StoryDecisionValue,
    dispatch_scribe_investigation,
    record_story_decision,
)


def _manifest(round_number: int = 1) -> ScribeTaskManifest:
    return ScribeTaskManifest(
        run_id="run_1",
        phase="M-STORY",
        attempt_id="att_1",
        spec_id="v0.14-001-workflow-reflow-spec",
        story_revision=3,
        story_digest="sha256:" + "a" * 64,
        story_template_path="templates/story.md",
        story_template_digest="sha256:" + "t" * 64,
        human_request="让用户在 Web 工作台完成 release 需求定义。",
        foundation_manifest_identity="fop_" + "f" * 21,
        round_number=round_number,
        previous_feedback_digests=() if round_number == 1 else ("sha256:" + "f" * 64,),
    )


# AC-FR0700-01 ---------------------------------------------------------------
def test_scribe_task_manifest_contains_all_required_fields() -> None:
    """AC-FR0700-01: the Scribe task manifest exposes run/step/attempt/spec
    id/Story revision and digest/Story template path and digest/human
    request/foundation identity."""
    manifest = _manifest()
    assert manifest.run_id == "run_1"
    assert manifest.phase == "M-STORY"
    assert manifest.attempt_id == "att_1"
    assert manifest.spec_id == "v0.14-001-workflow-reflow-spec"
    assert manifest.story_revision == 3
    assert manifest.story_digest == "sha256:" + "a" * 64
    assert manifest.story_template_path == "templates/story.md"
    assert manifest.story_template_digest == "sha256:" + "t" * 64
    assert manifest.human_request
    assert manifest.foundation_manifest_identity.startswith("fop_")


def test_scribe_task_manifest_write_scope_is_only_story_md() -> None:
    """AC-FR0700-01: the task write scope only contains the current
    ``story.md``; M-SPEC and acceptance are out of scope."""
    manifest = dispatch_scribe_investigation(
        run_id="run_1",
        story_revision=3,
        story_digest="sha256:" + "a" * 64,
        story_template_path="templates/story.md",
        story_template_digest="sha256:" + "t" * 64,
        human_request="Some story.",
        foundation_manifest_identity="fop_" + "f" * 21,
        spec_id="v0.14-001-workflow-reflow-spec",
        round_number=1,
        previous_feedback_digests=(),
    )
    assert manifest.write_scope == ("story.md",)
    # AC-FR0700-01: previous_feedback_digests only included in non-first rounds.
    assert manifest.previous_feedback_digests == ()


def test_scribe_task_manifest_includes_previous_feedback_in_non_first_rounds() -> None:
    """AC-FR0700-01: in round > 1, the manifest includes the digests of
    previous feedback."""
    manifest = dispatch_scribe_investigation(
        run_id="run_1",
        story_revision=5,
        story_digest="sha256:" + "b" * 64,
        story_template_path="templates/story.md",
        story_template_digest="sha256:" + "t" * 64,
        human_request="Some story.",
        foundation_manifest_identity="fop_" + "f" * 21,
        spec_id="v0.14-001-workflow-reflow-spec",
        round_number=2,
        previous_feedback_digests=("sha256:" + "f" * 64,),
    )
    assert manifest.round_number == 2
    assert manifest.previous_feedback_digests == ("sha256:" + "f" * 64,)


def test_scribe_dispatch_rejects_missing_foundation_manifest_identity() -> None:
    """AC-FR0700-01: a missing foundation manifest identity is rejected before
    dispatch; no task is created."""
    with pytest.raises(ValueError) as exc_info:
        dispatch_scribe_investigation(
            run_id="run_1",
            story_revision=3,
            story_digest="sha256:" + "a" * 64,
            story_template_path="templates/story.md",
            story_template_digest="sha256:" + "t" * 64,
            human_request="Some story.",
            foundation_manifest_identity="",
            spec_id="v0.14-001-workflow-reflow-spec",
            round_number=1,
            previous_feedback_digests=(),
        )
    assert FOUNDATION_MANIFEST_REQUIRED in str(exc_info.value)


# AC-FR0700-02 ---------------------------------------------------------------
def test_scribe_suggestion_keeps_run_waiting_for_human_in_m_story() -> None:
    """AC-FR0700-02: when Scribe returns a Go/Park/No-Go suggestion, the
    run stays ``waiting_human`` and the current step remains M-STORY; no
    M-SPEC task is dispatched."""
    suggestion = ScribeSuggestion(
        suggestion="Go",
        reasoning="The story is technically feasible and aligned with backlog.",
    )
    state = suggestion.apply_to_run_state()
    assert state.status == "waiting_human"
    assert state.current_step == "M-STORY"
    assert state.m_spec_task_count == 0


# AC-FR0700-03 ---------------------------------------------------------------
def test_story_decision_rejects_stale_revision() -> None:
    """AC-FR0700-03: a Human decision on a stale revision is rejected; the
    decision record remains empty."""
    with pytest.raises(DecisionRejected) as exc_info:
        record_story_decision(
            story_revision=3,
            expected_revision=2,  # stale
            value=StoryDecisionValue.GO,
            actor="human:alice",
            actor_kind="human",
        )
    assert exc_info.value.code == "WORKFLOW_STATE_CONFLICT"
    assert exc_info.value.recorded is None


def test_story_decision_rejects_agent_actor() -> None:
    """AC-FR0700-03: an Agent-transport caller cannot submit a story
    decision; the decision record remains empty."""
    with pytest.raises(DecisionRejected) as exc_info:
        record_story_decision(
            story_revision=3,
            expected_revision=3,
            value=StoryDecisionValue.GO,
            actor="agent:scribe",
            actor_kind="agent",
        )
    assert exc_info.value.code == "HUMAN_AUTHORITY_REQUIRED"
    assert exc_info.value.recorded is None


def test_story_decision_rejects_value_outside_legal_set() -> None:
    """AC-FR0700-03: a value outside {Go, Park, No-Go} is rejected."""
    with pytest.raises(DecisionRejected) as exc_info:
        record_story_decision(
            story_revision=3,
            expected_revision=3,
            value="Maybe",  # type: ignore[arg-type]
            actor="human:alice",
            actor_kind="human",
        )
    assert exc_info.value.code == "VALIDATION_FAILED"
    assert exc_info.value.recorded is None


def test_valid_human_decision_records_actor_revision_value_time() -> None:
    """AC-FR0700-03: a valid Human decision on R records actor, R, value and
    time."""
    record = record_story_decision(
        story_revision=3,
        expected_revision=3,
        value=StoryDecisionValue.PARK,
        actor="human:alice",
        actor_kind="human",
    )
    assert record.actor == "human:alice"
    assert record.story_revision == 3
    assert record.value == StoryDecisionValue.PARK
    assert record.decided_at  # non-empty stable timestamp
