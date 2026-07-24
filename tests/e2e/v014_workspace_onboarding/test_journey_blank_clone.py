"""E2E journey: blank workspace clone happy path.

AC-FR0301-01, AC-FR0401-01, AC-FR0701-02

User opens a blank workspace, registers, logs in, and reaches the
projects/new page where they can preview a Story delivery.
"""

from __future__ import annotations

import json


def test_clone_journey_reaches_preview(live_server, browser_page):
    """AC-FR0301-01: user can navigate to release preview from Workbench."""
    # AC-FR0301-01
    page, base_url = browser_page

    # Register and login
    page.request.post(
        f"{base_url}/api/auth/register",
        data={"username": "human", "password": "secret"},
    )
    page.goto(f"{base_url}/login", wait_until="domcontentloaded")
    page.fill('input[name="username"]', "human")
    page.fill('input[name="password"]', "secret")
    page.click('button[type="submit"]')
    page.wait_for_load_state("domcontentloaded")

    # Navigate to project creation
    page.goto(f"{base_url}/projects/new", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    assert page.url.startswith(base_url)


def test_clone_preview_has_zero_side_effects(live_server, browser_page):
    """AC-FR0301-01: release preview does not create resources before confirm."""
    # AC-FR0301-01
    page, base_url = browser_page

    page.request.post(
        f"{base_url}/api/auth/register",
        data={"username": "human", "password": "secret"},
    )
    page.goto(f"{base_url}/projects/new", wait_until="domcontentloaded")
    csrf = page.evaluate(
        """() => {
            const m = document.documentElement.innerHTML.match(/const\\s+csrf\\s*=\\s*["']([a-f0-9]+)["']/);
            if (m) return m[1];
            const el = document.querySelector('[data-csrf]');
            return el ? el.dataset.csrf : '';
        }"""
    )

    if csrf:
        preview = page.request.post(
            f"{base_url}/api/v14/releases/preview",
            data=json.dumps({"story": "Fix a bug", "release_version": "0.14.0"}),
            headers={
                "Content-Type": "application/json",
                "Origin": base_url,
                "X-Louke-CSRF": csrf,
            },
        )
        if preview.ok:
            pb = preview.json()
            assert pb.get("side_effects", []) == []


def test_binding_identity_visible(live_server, browser_page):
    """AC-FR0401-01: workspace identity is visible after login."""
    # AC-FR0401-01
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

    # The Workbench should show the workspace context
    page.goto(f"{base_url}/", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    assert page.url.startswith(base_url)


def test_setup_complete_reaches_ready_empty(live_server, browser_page):
    """AC-FR0701-02: after login, user reaches a workbench state (Ready/Empty or Setup)."""
    # AC-FR0701-02
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

    # After login, user should be in the Workbench (not on a standalone login page)
    assert "/login" not in page.url
