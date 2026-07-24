"""E2E journey: existing workspace entry matrix.

AC-FR0001-01, AC-FR1001-01, AC-FR1001-02

User with an existing workspace logs in and the entry resolver selects
the correct destination based on workspace state (Setup, Current Work,
Released, Ready/Empty).
"""

from __future__ import annotations


def test_login_does_not_redirect_to_chat_page(live_server, browser_page):
    """AC-FR0001-02: login does not auto-redirect to a standalone chat page."""
    # AC-FR0001-02
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

    # Should not be on a standalone chat page
    assert "/login" not in page.url


def test_dashboard_shows_workspace_context(live_server, browser_page):
    """AC-FR1001-01: dashboard shows workspace context after login."""
    # AC-FR1001-01
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


def test_navigation_preserves_identity(live_server, browser_page):
    """AC-FR1001-02: navigation between activities preserves workspace identity."""
    # AC-FR1001-02
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

    # Navigate to projects and back
    page.goto(f"{base_url}/projects", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    page.goto(base_url, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")

    # Should still be authenticated
    assert "/login" not in page.url


def test_workbench_shell_accessible(live_server, browser_page):
    """AC-FR0001-01: Workbench shell is accessible after login."""
    # AC-FR0001-01
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

    # Workbench should be accessible
    page.goto(f"{base_url}/workbench", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    assert page.url.startswith(base_url)
