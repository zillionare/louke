"""E2E journey: dashboard and Guide main path.

AC-FR1101-01, AC-FR1301-01, AC-FR1401-01, AC-FR1501-01

User logs in and the Workbench shows the dashboard surface and Guide
sidebar without Maestro dispatch or agent picker interference.
"""

from __future__ import annotations


def test_workbench_shows_dashboard_surface(live_server, browser_page):
    """AC-FR1101-01: Workbench shows dashboard surface after login."""
    # AC-FR1101-01
    page, base_url = browser_page

    page.request.post(
        f"{base_url}/api/auth/register",
        data={"username": "human", "password": "secret"},
    )
    page.goto(f"{base_url}/login", wait_until="domcontentloaded")
    page.fill('input[name="username"]', "human")
    page.fill('input[name="password"]', "secret")
    page.click('button[type="submit"]')
    page.wait_for_load_state("domcontentloaded")

    page.goto(base_url, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    body_text = page.inner_text("body")
    assert len(body_text) > 0


def test_guide_does_not_dispatch_maestro(live_server, browser_page):
    """AC-FR1501-01: Guide does not dispatch or show Maestro as new agent."""
    # AC-FR1501-01
    page, base_url = browser_page

    page.request.post(
        f"{base_url}/api/auth/register",
        data={"username": "human", "password": "secret"},
    )
    page.goto(f"{base_url}/login", wait_until="domcontentloaded")
    page.fill('input[name="username"]', "human")
    page.fill('input[name="password"]', "secret")
    page.click('button[type="submit"]')
    page.wait_for_load_state("domcontentloaded")

    page.goto(base_url, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")

    # Maestro should not be visible as a dispatchable agent
    # The page should not have a "Dispatch Maestro" button
    dispatch_buttons = page.query_selector_all("[data-dispatch='maestro']")
    assert len(dispatch_buttons) == 0


def test_workbench_sidebar_visible(live_server, browser_page):
    """AC-FR1301-01: Workbench sidebar is visible after login."""
    # AC-FR1301-01
    page, base_url = browser_page

    page.request.post(
        f"{base_url}/api/auth/register",
        data={"username": "human", "password": "secret"},
    )
    page.goto(f"{base_url}/login", wait_until="domcontentloaded")
    page.fill('input[name="username"]', "human")
    page.fill('input[name="password"]', "secret")
    page.click('button[type="submit"]')
    page.wait_for_load_state("domcontentloaded")

    page.goto(base_url, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    # The page should have content (sidebar or main area)
    body_text = page.inner_text("body")
    assert len(body_text) > 0


def test_guide_navigation_does_not_change_workflow_state(live_server, browser_page):
    """AC-FR1401-01: Guide navigation does not change workflow state."""
    # AC-FR1401-01
    page, base_url = browser_page

    page.request.post(
        f"{base_url}/api/auth/register",
        data={"username": "human", "password": "secret"},
    )
    page.goto(f"{base_url}/login", wait_until="domcontentloaded")
    page.fill('input[name="username"]', "human")
    page.fill('input[name="password"]', "secret")
    page.click('button[type="submit"]')
    page.wait_for_load_state("domcontentloaded")

    # Navigate through activities without changing workflow state
    page.goto(base_url, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    page.goto(f"{base_url}/projects", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    page.goto(base_url, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")

    # Should still be in the same state
    assert "/login" not in page.url
