"""Unit contracts for canonical Workflow Status projection."""

from louke.web.workflow_status import Phase, WorkflowStatus, project_status


def test_status_projection_preserves_runtime_identity_and_omits_percentages() -> None:
    """AC-FR1001-01: dashboard projects one Runtime-owned object chain."""
    status = project_status(
        WorkflowStatus(
            workspace_id="workspace-1",
            project_id="project-1",
            story_id="story-1",
            run_id="run-1",
            phases=(Phase("M-STORY", "completed"), Phase("M-DESIGN", "current")),
            current_phase="M-DESIGN",
            canonical_state="waiting_human",
            responsible_party="Archer",
            required_action="Review design",
        )
    )

    assert status["context"]["run_id"] == "run-1"
    assert status["current_phase"] == "M-DESIGN"
    assert status["required_action"] == "Review design"
    assert "percent" not in status
    assert "percentage" not in status


def test_attention_status_exposes_one_required_action() -> None:
    """AC-FR1101-02: attention explains ownership and recovery action."""
    status = project_status(
        WorkflowStatus(
            workspace_id="w",
            project_id="p",
            story_id=None,
            run_id=None,
            phases=(Phase("M-STORY", "attention"),),
            current_phase="M-STORY",
            canonical_state="blocked",
            responsible_party="Human",
            required_action="Resolve repository conflict",
        )
    )

    assert status["responsible_party"] == "Human"
    assert status["required_action"] == "Resolve repository conflict"
