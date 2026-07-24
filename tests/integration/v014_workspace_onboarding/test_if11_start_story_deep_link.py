"""IF-11: Start Story and release/story deep links.

AC-FR0901-01, AC-FR0901-02, AC-FR1001-02

Integration tests verify that Story Preview is zero-side-effect and that
deep links preserve project/story/run identity.
"""

from __future__ import annotations

from louke.web.story_preview import build_story_preview
from louke.web.workbench_navigation import build_context_url


def test_story_preview_has_zero_release_creation():
    """AC-FR0901-01: Story Preview does not create release resources."""
    # AC-FR0901-01
    preview = build_story_preview(
        workspace_id="ws_1",
        story_input="Fix login bug",
        version="0.14.0",
        branch="releases/0.14.0",
    )
    assert preview.release_resource_creation_count == 0


def test_story_preview_contains_workspace_and_story_input():
    """AC-FR0901-01: Preview shows workspace identity and original story input."""
    # AC-FR0901-01
    preview = build_story_preview(
        workspace_id="ws_1",
        story_input="Fix login bug",
        version="0.14.0",
        branch="releases/0.14.0",
    )
    assert preview.workspace_id == "ws_1"
    assert preview.story_input == "Fix login bug"


def test_story_preview_has_request_digest():
    """AC-FR0901-01: Preview includes a request digest for idempotency."""
    # AC-FR0901-01
    preview = build_story_preview(
        workspace_id="ws_1",
        story_input="Fix login bug",
        version="0.14.0",
        branch="releases/0.14.0",
    )
    assert len(preview.request_digest) > 0


def test_story_preview_digest_is_deterministic():
    """AC-FR0901-01: same inputs produce same digest (deterministic)."""
    # AC-FR0901-01
    p1 = build_story_preview(
        workspace_id="ws_1",
        story_input="Fix login bug",
        version="0.14.0",
        branch="releases/0.14.0",
    )
    p2 = build_story_preview(
        workspace_id="ws_1",
        story_input="Fix login bug",
        version="0.14.0",
        branch="releases/0.14.0",
    )
    assert p1.request_digest == p2.request_digest


def test_deep_link_preserves_project_and_story_identity():
    """AC-FR1001-02: deep link preserves project and story identity."""
    # AC-FR1001-02
    url = build_context_url("proj_1", story_id="story_1")
    assert "proj_1" in url
    assert "story_1" in url


def test_deep_link_preserves_run_identity():
    """AC-FR1001-02: deep link preserves run identity."""
    # AC-FR1001-02
    url = build_context_url("proj_1", run_id="run_1")
    assert "run_1" in url
