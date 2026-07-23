"""Canonical Runtime workflow status projection for Workbench surfaces."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Phase:
    """One phase and its canonical display state."""

    phase_id: str
    state: str


@dataclass(frozen=True)
class WorkflowStatus:
    """Runtime-owned status facts consumed by dashboard and Guide."""

    workspace_id: str
    project_id: str
    story_id: str | None
    run_id: str | None
    phases: tuple[Phase, ...]
    current_phase: str | None
    canonical_state: str
    responsible_party: str | None
    required_action: str | None


def project_status(status: WorkflowStatus) -> dict[str, object]:
    """Serialize status facts without deriving client-side progress metrics."""
    return {
        "context": {
            "workspace_id": status.workspace_id,
            "project_id": status.project_id,
            "story_id": status.story_id,
            "run_id": status.run_id,
        },
        "phases": [
            {"id": phase.phase_id, "state": phase.state} for phase in status.phases
        ],
        "current_phase": status.current_phase,
        "canonical_state": status.canonical_state,
        "responsible_party": status.responsible_party,
        "required_action": status.required_action,
    }
