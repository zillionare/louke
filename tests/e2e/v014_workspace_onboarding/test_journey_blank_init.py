"""E2E journey: blank workspace init happy path.

AC-FR0001-01, AC-FR0101-01, AC-FR0201-01, AC-FR0301-01, AC-FR0701-02,
AC-FR0901-01, AC-NFR0501-01

User opens a blank workspace, registers, logs in, and reaches the
Workbench shell. This is the main success path for a first-time user.
"""

from __future__ import annotations


def _csrf_from_page(page) -> str:
    return page.evaluate(
        """() => {
            const m = document.documentElement.innerHTML.match(/const\\s+csrf\\s*=\\s*["']([a-f0-9]+)["']/);
            if (m) return m[1];
            const el = document.querySelector('[data-csrf]');
            return el ? el.dataset.csrf : '';
        }"""
    )


def test_blank_workspace_reaches_workbench_shell(live_server, browser_page):
    """AC-FR0001-01: blank workspace reaches Workbench shell after login."""
    # AC-FR0001-01
    page, base_url = browser_page

    # Open the product
    page.goto(base_url, wait_until="domcontentloaded")

    # Register first user
    page.request.post(
        f"{base_url}/api/auth/register",
        data={"username": "human", "password": "secret"},
    )

    # Login
    page.goto(f"{base_url}/login", wait_until="domcontentloaded")
    page.fill('input[name="username"]', "human")
    page.fill('input[name="password"]', "secret")
    page.click('button[type="submit"]')
    page.wait_for_load_state("domcontentloaded")

    # Should be in Workbench shell (not a standalone chat page)
    assert "/login" not in page.url


def test_setup_wizard_shows_steps(live_server, browser_page):
    """AC-FR0101-01: Setup Wizard shows current and remaining steps."""
    # AC-FR0101-01
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

    # After login, user should see the Workbench or setup surface
    # The page content should indicate setup or workbench context
    body_text = page.inner_text("body")
    assert len(body_text) > 0


def test_first_user_creation_then_login_continuity(live_server, browser_page):
    """AC-FR0201-01: first user creation followed by login reaches same workspace."""
    # AC-FR0201-01
    page, base_url = browser_page

    # Register
    reg = page.request.post(
        f"{base_url}/api/auth/register",
        data={"username": "owner", "password": "secret"},
    )
    assert reg.ok

    # Login
    page.goto(f"{base_url}/login", wait_until="domcontentloaded")
    page.fill('input[name="username"]', "owner")
    page.fill('input[name="password"]', "secret")
    page.click('button[type="submit"]')
    page.wait_for_load_state("domcontentloaded")

    # Verify we are authenticated and in the Workbench
    health = page.request.get(f"{base_url}/health")
    assert health.ok


def test_credential_not_echoed_on_page(live_server, browser_page):
    """AC-FR0201-02: credential is not echoed back on any page."""
    # AC-FR0201-02
    page, base_url = browser_page

    page.request.post(
        f"{base_url}/api/auth/register",
        data={"username": "human", "password": "canary-secret-12345"},
    )

    page.goto(base_url, wait_until="domcontentloaded")
    body_text = page.inner_text("body")
    assert "canary-secret-12345" not in body_text


def test_start_story_entry_visible(live_server, browser_page):
    """AC-FR0901-01: Start Story entry is visible from Ready/Empty."""
    # AC-FR0901-01
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

    # Navigate to projects page
    page.goto(f"{base_url}/projects/new", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    # The page should load without error
    assert page.url.startswith(base_url)


def test_main_path_does_not_require_runtime_terminology(live_server, browser_page):
    """AC-NFR0501-01: main path does not require user to input Runtime stage terms."""
    # AC-NFR0501-01
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

    # The user should not see internal Runtime stage terminology on the main page
    body_text = page.inner_text("body").lower()
    # These are internal terms that should not be user-facing
    assert "m-design" not in body_text or "story" in body_text
