"""NFR-0101: browser compatibility e2e (chromium + firefox for web UI critical paths)."""
from __future__ import annotations

import pytest


@pytest.mark.parametrize("browser_name", ["chromium", "firefox"])
def test_home_page_loads(browser_page, live_server_url, browser_name):
    """AC-NFR0101-01: home page loads in chromium and firefox (status 200, non-empty title)."""
    r = browser_page.goto(live_server_url + "/")
    assert r is not None
    assert r.ok or r.status == 200
    assert browser_page.title() != ""


@pytest.mark.parametrize("browser_name", ["chromium", "firefox"])
def test_wiki_page_loads(browser_page, live_server_url, browser_name):
    """AC-NFR0101-01: wiki index page loads in chromium and firefox (status 200)."""
    r = browser_page.goto(live_server_url + "/wiki")
    assert r is not None
    assert r.ok or r.status == 200


@pytest.mark.parametrize("browser_name", ["chromium", "firefox"])
def test_login_page_loads(browser_page, live_server_url, browser_name):
    """AC-NFR0101-01: login page loads in chromium and firefox (status 200)."""
    r = browser_page.goto(live_server_url + "/login")
    assert r is not None
    assert r.ok or r.status == 200