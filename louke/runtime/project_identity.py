"""Project identity: canonical object chain for project/release/run.

AC-FR1001-01, AC-FR1101-01

The canonical chain is:
``project_id -> planned_release_identity -> github_project_node_id
-> request_id -> run_id -> spec_id -> latest_story_revision``

This chain is persisted by release request/Foundation evidence.
"""

from __future__ import annotations

from typing import Any


def build_identity(
    *,
    project_id: str = "",
    release_identity: str = "",
    github_project_node_id: str | None = None,
    request_id: str = "",
    run_id: str = "",
    spec_id: str = "",
    story_revision: str = "",
) -> dict[str, Any]:
    """Build a canonical project identity chain.

    Args:
        project_id: The project id.
        release_identity: The planned release identity.
        github_project_node_id: GitHub project node id.
        request_id: Release request id.
        run_id: Workflow run id.
        spec_id: Spec id.
        story_revision: Latest story revision.

    Returns:
        A dict representing the full canonical identity chain.
    """
    return {
        "project_id": project_id,
        "release_identity": release_identity,
        "github_project_node_id": github_project_node_id,
        "request_id": request_id,
        "run_id": run_id,
        "spec_id": spec_id,
        "latest_story_revision": story_revision,
    }
