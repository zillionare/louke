"""FR-0600: Runtime 权威工作流与 Web 当前状态.

AC references:
- AC-FR0600-01: a request (Web, Agent message, document text) that attempts a
  direct phase transition not allowed by the workflow definition returns
  ``WORKFLOW_STATE_CONFLICT`` and leaves the current step, current revision,
  artifact bytes, gate count and Issue count unchanged.
- AC-FR0600-02: refreshing or restarting the Project page returns the same
  step, status, artifact revision, writer, review round, task/session,
  verdict and last error as the persisted read model.
- AC-FR0600-03: a save/review/transition request that carries a stale
  revision or requests an action not in the current phase's allowed list is
  rejected; the run, artifact and external resources do not change, and the
  response exposes the current revision/phase and a continue URL.
"""

from __future__ import annotations

import pytest

from louke.v014.fr0600_workflow_authority import (
    ActionForbidden,
    Phase,
    PhaseAction,
    WorkflowAuthority,
    WorkflowStateConflict,
    build_read_model,
)


def _authority() -> WorkflowAuthority:
    return WorkflowAuthority()


# AC-FR0600-01 ---------------------------------------------------------------
def test_phase_machine_rejects_disallowed_direct_transitions() -> None:
    """AC-FR0600-01: an attempt to jump from M-SPEC to M-LOCK-1 directly is
    rejected with WORKFLOW_STATE_CONFLICT; phase and revision are unchanged."""
    auth = _authority()
    state = auth.begin(run_id="run_1", phase=Phase.M_SPEC, revision=3)
    with pytest.raises(WorkflowStateConflict) as exc_info:
        auth.transition(
            state=state,
            target=Phase.M_LOCK_1,
            expected_revision=3,
            actor_kind="agent",
        )
    assert exc_info.value.code == "WORKFLOW_STATE_CONFLICT"
    assert exc_info.value.current_phase == Phase.M_SPEC
    assert exc_info.value.current_revision == 3
    # Phase and revision unchanged.
    assert state.phase == Phase.M_SPEC
    assert state.revision == 3


def test_phase_machine_rejects_payload_actor_overriding_human_authority() -> None:
    """AC-FR0600-01 + IF-COMMON-01: payload-supplied actor/role has no
    authority; an Agent-transport request to transition phases is rejected."""
    auth = _authority()
    state = auth.begin(run_id="run_1", phase=Phase.M_STORY, revision=1)
    with pytest.raises(ActionForbidden) as exc_info:
        auth.transition(
            state=state,
            target=Phase.M_SPEC,
            expected_revision=1,
            actor_kind="agent",
        )
    assert exc_info.value.code == "HUMAN_AUTHORITY_REQUIRED"
    assert state.phase == Phase.M_STORY
    assert state.revision == 1


def test_legal_transition_advances_phase_and_revision() -> None:
    """AC-FR0600-01: a legal transition (M_STORY -> M_SPEC) by an authenticated
    Human principal advances phase and increments revision."""
    auth = _authority()
    state = auth.begin(run_id="run_1", phase=Phase.M_STORY, revision=2)
    new_state = auth.transition(
        state=state,
        target=Phase.M_SPEC,
        expected_revision=2,
        actor_kind="human",
    )
    assert new_state.phase == Phase.M_SPEC
    assert new_state.revision == 3


# AC-FR0600-02 ---------------------------------------------------------------
def test_read_model_is_deterministic_for_same_persisted_state() -> None:
    """AC-FR0600-02: building the read model twice from the same persisted
    state returns byte-equal field values for step/status/artifact revision/
    writer/round/task/session/verdict/last error."""
    state = _authority().begin(
        run_id="run_1",
        phase=Phase.M_SPEC,
        revision=4,
        artifact_revision=2,
        writer="scribe:task_1",
        review_round=1,
        task_id="task_xyz",
        attempt_id="att_1",
        session_id="sess_1",
        last_error="model timeout",
    )
    first = build_read_model(state, allowed_actions=(PhaseAction.HUMAN_REVIEW,))
    second = build_read_model(state, allowed_actions=(PhaseAction.HUMAN_REVIEW,))
    assert first == second
    assert first.phase == Phase.M_SPEC
    assert first.revision == 4
    assert first.artifact_revision == 2
    assert first.writer == "scribe:task_1"
    assert first.review_round == 1
    assert first.task_id == "task_xyz"
    assert first.attempt_id == "att_1"
    assert first.session_id == "sess_1"
    assert first.last_error == "model timeout"
    assert first.allowed_actions == (PhaseAction.HUMAN_REVIEW,)


# AC-FR0600-03 ---------------------------------------------------------------
def test_stale_revision_save_is_rejected_with_current_state_exposed() -> None:
    """AC-FR0600-03: a save with a stale expected_revision is rejected with
    WORKFLOW_STATE_CONFLICT; the response exposes the current revision, phase
    and a continue URL the Human can follow without invoking CLI commands."""
    auth = _authority()
    state = auth.begin(run_id="run_1", phase=Phase.M_STORY, revision=5)
    with pytest.raises(WorkflowStateConflict) as exc_info:
        auth.assert_revision_current(state, expected_revision=3)
    assert exc_info.value.code == "WORKFLOW_STATE_CONFLICT"
    assert exc_info.value.current_revision == 5
    assert exc_info.value.current_phase == Phase.M_STORY
    assert exc_info.value.continue_url.endswith("/projects/run_1/current")


def test_action_not_in_allowed_list_is_rejected() -> None:
    """AC-FR0600-03: a phase action that is not in the server-computed
    allowed list is rejected; the run, artifact and external resources do not
    change."""
    auth = _authority()
    state = auth.begin(
        run_id="run_1",
        phase=Phase.M_SPEC,
        revision=1,
        allowed_actions=(PhaseAction.HUMAN_REVIEW, PhaseAction.AGENT_REPLY),
    )
    with pytest.raises(ActionForbidden) as exc_info:
        auth.assert_action_allowed(state, PhaseAction.APPROVE_M_LOCK_1)
    assert exc_info.value.code == "WORKFLOW_STATE_CONFLICT"
    # State is unchanged.
    assert state.phase == Phase.M_SPEC
    assert state.revision == 1
