"""AC-FR1512-01@v0.13.1: workbench chrome and runtime identity contract."""

from __future__ import annotations

from html.parser import HTMLParser

from starlette.testclient import TestClient

from louke.web.app import create_app


class _ButtonParser(HTMLParser):
    """Collect toolbar buttons and stable workbench markers from HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.buttons: list[dict[str, str]] = []
        self.markers: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        testid = attributes.get("data-testid", "")
        if testid in {"workbench-toolbar", "workbench-sidebar", "workbench-main"}:
            self.markers.add(testid)
        if tag == "button" and testid.startswith("toolbar-"):
            self.buttons.append(attributes)


def _workbench_html() -> str:
    response = TestClient(create_app()).get("/workbench")
    assert response.status_code == 200
    return response.text


def test_toolbar_item_order() -> None:
    """AC-FR1302-01, AC-FR1302-02: toolbar buttons use the contract order."""
    parser = _ButtonParser()
    parser.feed(_workbench_html())
    assert [button["aria-label"] for button in parser.buttons] == [
        "Chat",
        "Dev Docs",
        "End User Docs",
        "Wiki",
        "Runs",
        "Accounts",
        "Settings",
    ]


def test_toolbar_tooltip() -> None:
    """AC-FR1301-02: every toolbar button exposes its readable title."""
    parser = _ButtonParser()
    parser.feed(_workbench_html())
    assert [button["title"] for button in parser.buttons] == [
        "Chat",
        "Dev Docs",
        "End User Docs",
        "Wiki",
        "Runs",
        "Accounts",
        "Settings",
    ]


def test_tab_can_coexist() -> None:
    """AC-FR1301-03/05: client contract preserves existing tabs on activation."""
    html = _workbench_html()
    assert 'data-tab-key="dev-docs"' in html
    assert 'data-tab-key="runs"' in html
    assert "openTab(activity)" in html
    assert "activity==='gears'" in html
    assert "tabs.has(tabKey)" in html


def test_sidebar_switches_with_toolbar() -> None:
    """AC-FR1301-03: toolbar activation changes the sidebar kind and tree."""
    html = _workbench_html()
    assert 'data-sidebar-kind="chat"' in html
    assert 'data-sidebar-kind="wiki"' in html
    assert 'data-sidebar-kind="dev-docs"' in html
    assert "renderSidebar(activity)" in html


def test_data_testid_present() -> None:
    """AC-FR1301-01: all three workbench landmarks have stable test IDs."""
    parser = _ButtonParser()
    parser.feed(_workbench_html())
    assert parser.markers == {
        "workbench-toolbar",
        "workbench-sidebar",
        "workbench-main",
    }


def test_settings_shows_current_runtime_identity(monkeypatch) -> None:
    """AC-FR1512-01@v0.13.1: Settings exposes the active version and mode."""
    monkeypatch.setenv("LOUKE_RUNTIME_MODE", "global")
    html = _workbench_html()
    assert 'data-testid="settings-runtime-identity"' in html
    assert "(global)" in html
    assert 'data-testid="settings-project-root"' in html
    assert 'data-testid="settings-local-runtime"' in html


def test_settings_runtime_read_model_is_public(monkeypatch) -> None:
    """AC-FR1512-01@v0.13.1: the runtime read model is JSON and uncached."""
    monkeypatch.setenv("LOUKE_RUNTIME_MODE", "global")
    response = TestClient(create_app()).get("/api/ui/settings/runtime")

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "global"
    assert payload["display"].endswith(" (global)")
