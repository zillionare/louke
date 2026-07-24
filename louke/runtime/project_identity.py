"""Project identity: canonical object chain for project/release/run.

AC-FR1001-01, AC-FR1101-01, AC-FR1501-01

The canonical chain is:
``project_id -> planned_release_identity -> github_project_node_id
-> request_id -> run_id -> spec_id -> latest_story_revision``

This chain is persisted by release request/Foundation evidence. Every
Project-related API/page exposes the same identity; new writes produce
exactly one writable binding; unsafe mappings surface as
``migration_required`` and are read-only.
"""

from __future__ import annotations

from typing import Any

from louke.runtime.release_request import _canonical_release_version


def build_identity(
    *,
    workspace_id: str = "",
    project_id: str = "",
    request_id: str = "",
    release_version: str = "",
    github_project_node_id: str | None = None,
    github_project_url: str | None = None,
    run_id: str = "",
    spec_id: str = "",
    story_path: str | None = None,
    story_revision: str | None = None,
    story_digest: str | None = None,
    activity_state: str = "active",
    identity_revision: int = 0,
) -> dict[str, Any]:
    """Build a canonical project identity chain.

    Args:
        workspace_id: The workspace id.
        project_id: The project id.
        request_id: Release request id.
        release_version: The planned release version (canonicalised to
            a 3-segment PEP440 form before being stored under
            ``planned_release.canonical``).
        github_project_node_id: GitHub project node id, or ``None``.
        github_project_url: GitHub project URL, or ``None``.
        run_id: Workflow run id.
        spec_id: Spec id.
        story_path: Path to the canonical ``story.md``, or ``None``.
        story_revision: Story revision, or ``None``.
        story_digest: Story content digest, or ``None``.
        activity_state: ``active``, ``historical``, or
            ``migration_required``.
        identity_revision: Monotonic identity revision.

    Returns:
        A dict matching the locked ``ProjectIdentity`` schema from
        interfaces §IF-IDENTITY-01, with nested ``planned_release``,
        ``github_project`` and ``story`` objects.
    """
    canonical = _canonical_release_version(release_version) or release_version
    planned_release = {
        "canonical": canonical,
        "tag": f"v{canonical}" if canonical else "",
        "branch": f"releases/{canonical}" if canonical else "",
    }
    github_project: dict[str, Any] | None = None
    if github_project_node_id is not None or github_project_url is not None:
        github_project = {
            "node_id": github_project_node_id,
            "url": github_project_url,
        }
    story: dict[str, Any] | None = None
    if story_path is not None or story_revision is not None or story_digest is not None:
        story = {
            "path": story_path,
            "revision": story_revision,
            "digest": story_digest,
        }
    return {
        "workspace_id": workspace_id,
        "project_id": project_id,
        "request_id": request_id,
        "planned_release": planned_release,
        "github_project": github_project,
        "run_id": run_id,
        "spec_id": spec_id,
        "story": story,
        "activity_state": activity_state,
        "identity_revision": identity_revision,
    }
