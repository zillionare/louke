"""NFR-0101: browser compatibility e2e (chromium + firefox for web UI critical paths).

The browser_page fixture (see tests/e2e/conftest.py) is parametrized over
chromium + firefox; pytest-playwright also auto-injects a `browser_name` fixture.
We use the fixture's parametrization to avoid duplicate-parametrize errors.
"""
from __future__ import annotations

import pytest


def test_home_page_loads(browser_page, live_server_url, browser_name):
    """AC-NFR0101-01: home page loads in chromium and firefox (status 200, non-empty title)."""
    r = browser_page.goto(live_server_url + "/")
    assert r.ok or r.status == 200
    assert browser_page.title() != ""


def test_wiki_page_loads(browser_page, live_server_url, browser_name):
    """AC-NFR0101-01: wiki index page loads in chromium and firefox (status 200)."""
    r = browser_page.goto(live_server_url + "/wiki")
    assert r.ok or r.status == 200


def test_login_page_loads(browser_page, live_server_url, browser_name):
    """AC-NFR0101-01: login page loads in chromium and firefox (status 200)."""
    r = browser_page.goto(live_server_url + "/login")
    assert r.ok or r.status == 200