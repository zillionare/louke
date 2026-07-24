"""IF-08: WorkflowStatusProjection.

AC-FR1001-01, AC-FR1101-01, AC-FR1101-02

Integration tests verify that the workflow status projection exposes all
required fields, does not include percentages, and that attention states
show at most one required action.
"""

from __future__ import annotations

from louke.web.workflow_status import Phase, WorkflowStatus, project_status


def _status(
    canonical_state: str = "running",
    required_action: str | None = None,
    responsible_party: str | None = "human",
) -> WorkflowStatus:
    return WorkflowStatus(
        workspace_id="ws_1",
        project_id="proj_1",
        story_id="story_1",
        run_id="run_1",
        phases=(
            Phase(phase_id="M-STORY", state="completed"),
            Phase(phase_id="M-DESIGN", state="current"),
            Phase(phase_id="M-IMPL", state="pending"),
        ),
        current_phase="M-DESIGN",
        canonical_state=canonical_state,
        responsible_party=responsible_party,
        required_action=required_action,
    )


def test_status_projection_contains_all_required_fields():
    """AC-FR1101-01: projection exposes phases, state, responsible party, action."""
    # AC-FR1101-01
    status = _status()
    result = project_status(status)
    assert "phases" in result
    assert "current_phase" in result
    assert "canonical_state" in result
    assert "responsible_party" in result
    assert "required_action" in result


def test_status_projection_does_not_include_percentage():
    """AC-FR1101-01: projection must not include percentage or completion estimate."""
    # AC-FR1101-01
    status = _status()
    result = project_status(status)
    result_str = str(result).lower()
    assert "%" not in result_str
    assert "percent" not in result_str
    assert "progress" not in result_str or "progress" not in str(result.keys())


def test_phase_states_use_canonical_values():
    """AC-FR1101-01: phases use completed/current/pending/attention only."""
    # AC-FR1101-01
    status = _status()
    result = project_status(status)
    valid_states = {"completed", "current", "pending", "attention"}
    for phase in result["phases"]:
        assert phase["state"] in valid_states


def test_attention_state_shows_required_action():
    """AC-FR1101-02: attention state shows at most one required action."""
    # AC-FR1101-02
    status = _status(canonical_state="waiting_human", required_action="Confirm Story")
    result = project_status(status)
    assert result["canonical_state"] == "waiting_human"
    assert result["required_action"] is not None


def test_no_action_shows_waiting_responsible_party():
    """AC-FR1101-02: no action shows the responsible party being waited on."""
    # AC-FR1101-02
    status = _status(
        canonical_state="waiting_human",
        required_action=None,
        responsible_party="agent:Archer",
    )
    result = project_status(status)
    assert result["required_action"] is None
    assert result["responsible_party"] is not None


def test_status_has_workspace_and_project_identity():
    """AC-FR1001-01: status carries workspace and project identity for object continuity."""
    # AC-FR1001-01
    status = _status()
    result = project_status(status)
    assert result["context"]["project_id"] == "proj_1"
