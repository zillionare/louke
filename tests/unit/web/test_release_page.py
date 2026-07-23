"""Unit contracts for the version-agnostic public release page."""

from louke.web.pages.release import _render_page


def test_release_page_is_version_agnostic_and_uses_project_release_context() -> None:
    """The page must not identify itself with a Louke product version."""
    html = _render_page("csrf-token", "v0.37.0")

    assert "<title>New release</title>" in html
    assert 'value="v0.37.0"' in html
    assert "v14_release" not in html
    assert "v0.14.0" not in html


def test_release_page_uses_stable_release_api_and_recheck_surface() -> None:
    """The generic page exposes preview, confirmation, and recovery actions."""
    html = _render_page("csrf-token", "v0.37.0")

    assert "/api/releases/preview" in html
    assert "/api/releases/confirm" in html
    assert "/api/releases/requests/" in html
    assert "/api/v14/releases" not in html
    assert "Recheck Foundation" in html
    assert "setTimeout" in html
    assert 'body.status === "ready"' in html
    assert "function createIdempotencyKey" in html
    assert "typeof window.crypto.randomUUID" in html
    assert "idempotency_key: createIdempotencyKey()" in html
    assert "workflow" not in html.lower()
