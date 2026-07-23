"""Unit contracts for Ready/Empty Start Story preview."""

from louke.web.story_preview import build_story_preview


def test_story_preview_contains_story_and_release_identity_without_side_effects() -> (
    None
):
    """AC-FR0901-01: preview exposes all identity fields and creates nothing."""
    preview = build_story_preview(
        workspace_id="workspace-1",
        story_input="Improve onboarding",
        version="0.14.0",
        branch="story/improve-onboarding",
    )

    assert preview.workspace_id == "workspace-1"
    assert preview.story_input == "Improve onboarding"
    assert preview.release_version == "0.14.0"
    assert preview.branch == "story/improve-onboarding"
    assert preview.release_resource_creation_count == 0
