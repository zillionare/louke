"""AC coverage for the Batch B workbench panels."""

from __future__ import annotations

from starlette.testclient import TestClient

from louke.web.app import create_app


def _html() -> str:
    return TestClient(create_app()).get("/workbench").text


def test_settings_menu_3_disabled_items() -> None:
    """AC-FR1303-01/02/03/04: settings exposes clickable v0.15 placeholders."""
    html = _html()
    for name in ("version", "server", "model"):
        assert f'data-testid="settings-menu-{name}"' in html
        assert 'aria-disabled="true"' in html
    assert 'data-testid="settings-detail"' in html
    assert "待 v0.15" in html


def test_accounts_logout() -> None:
    """AC-FR1304-01/02/03: accounts posts logout and returns to the home route."""
    html = _html()
    assert 'data-testid="accounts-menu"' in html
    assert 'data-testid="accounts-logout"' in html
    assert "/api/security/logout" in html
    assert "location.href='/'" in html


def test_devdocs_sidebar_tree() -> None:
    """AC-FR1308-01/02/03/04: Dev Docs renders a collapsible spec tree."""
    html = _html()
    assert 'data-testid="devdocs-tree"' in html
    assert "localStorage" in html
    assert "louke.dev-docs.tree." in html
    assert 'data-testid="devdocs-file-' in html


def test_wiki_navigation_and_read_only_render() -> None:
    """AC-FR1311-01/02/03/04: Wiki navigation renders read-only pages."""
    html = _html()
    assert 'data-testid="wiki-tree"' in html
    assert 'data-testid="wiki-page-README"' in html
    assert "design docs" in html
    assert "Save" not in html


def test_wiki_notfound_fallback() -> None:
    """AC-FR1312-01/02/03/04: unknown Wiki pages degrade without a 5xx."""
    html = _html()
    assert 'data-testid="wiki-unknown-page"' in html
    assert "未知页面" in html
    assert 'data-unknown="true"' in html
