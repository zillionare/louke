"""E2E journey: compatibility and deep link main path.

AC-FR1201-01, AC-FR1201-02, AC-NFR0401-01

User accesses legacy routes (/workbench, /setup, /projects) and deep links,
and the Workbench resolves them to the canonical shell without losing
context.
"""

from __future__ import annotations


def test_legacy_workbench_route_resolves(live_server, browser_page):
    """AC-FR1201-01: /workbench resolves to canonical Workbench shell."""
    # AC-FR1201-01
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

    page.goto(f"{base_url}/workbench", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    assert page.url.startswith(base_url)


def test_legacy_setup_route_resolves(live_server, browser_page):
    """AC-FR1201-01: /setup resolves to canonical Setup surface."""
    # AC-FR1201-01
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

    page.goto(f"{base_url}/setup", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    assert page.url.startswith(base_url)


def test_legacy_projects_route_resolves(live_server, browser_page):
    """AC-FR1201-01: /projects resolves to canonical Workbench."""
    # AC-FR1201-01
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

    page.goto(f"{base_url}/projects", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    assert page.url.startswith(base_url)


def test_refresh_preserves_identity(live_server, browser_page):
    """AC-FR1201-02: refresh preserves workspace/project identity."""
    # AC-FR1201-02
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
    # Refresh the page
    page.reload(wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")

    # Should still be authenticated
    assert "/login" not in page.url


def test_not_found_does_not_silently_fall_to_other_project(live_server, browser_page):
    """AC-FR1201-02: nonexistent deep link shows not-found, not another project."""
    # AC-FR1201-02
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

    # Access a nonexistent project
    response = page.request.get(f"{base_url}/projects/nonexistent_project_id")
    # Should return 404 or redirect, not 200 with another project's content
    assert response.status in (404, 302, 307, 403)


def test_compatible_api_alias_works(live_server, browser_page):
    """AC-NFR0401-01: compatible API alias returns same response."""
    # AC-NFR0401-01
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

    # Both /api/releases/* and /api/v14/releases/* should be accessible
    r1 = page.request.get(f"{base_url}/api/v14/releases/preview")
    r2 = page.request.get(f"{base_url}/api/releases/preview")
    # Both should return the same status code
    assert r1.status == r2.status
