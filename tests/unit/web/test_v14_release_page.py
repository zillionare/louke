"""Unit contracts for the form-first v0.14 release page."""

from louke.web.pages.v14_release import _render_page


def test_release_page_uses_public_release_api_and_recheck_surface() -> None:
    """AC-FR0300-01: `/projects/new` exposes only the v0.14 public journey."""
    html = _render_page("csrf-token")

    assert "/api/v14/releases/preview" in html
    assert "/api/v14/releases/confirm" in html
    assert "/api/v14/releases/requests/" in html
    assert "Recheck Foundation" in html
    assert "workflow" not in html.lower()
