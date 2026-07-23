"""Pure Start Story and delivery-container preview construction."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib


@dataclass(frozen=True)
class StoryPreview:
    """Zero-side-effect preview for a new Story delivery request."""

    workspace_id: str
    story_input: str
    release_version: str
    branch: str
    request_digest: str
    release_resource_creation_count: int = 0


def build_story_preview(
    *, workspace_id: str, story_input: str, version: str, branch: str
) -> StoryPreview:
    """Build a canonical Story preview without creating release resources."""
    values = (
        workspace_id.strip(),
        story_input.strip(),
        version.strip(),
        branch.strip(),
    )
    if not all(values):
        raise ValueError("workspace, Story input, version, and branch are required")
    digest = hashlib.sha256("\n".join(values).encode("utf-8")).hexdigest()
    return StoryPreview(*values, request_digest=digest)
