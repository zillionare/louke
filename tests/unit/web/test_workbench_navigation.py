"""Unit contracts for stable Workbench deep links."""

from __future__ import annotations

from louke.web.workbench_navigation import build_context_url


def test_context_url_preserves_encoded_identity() -> None:
    """AC-FR1201-01: project/story/run links share one stable URL scheme."""
    assert build_context_url("project/1", story_id="story 1", run_id="run/1") == (
        "/projects/project%2F1/stories/story%201/runs/run%2F1"
    )


def test_context_url_rejects_empty_project_identity() -> None:
    """AC-FR1201-02: missing identity cannot silently select another project."""
    try:
        build_context_url("")
    except ValueError as exc:
        assert "project" in str(exc)
    else:
        raise AssertionError("empty project identity must fail")
