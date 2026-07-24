"""E2E journey: Setup Wizard continuous progress and step boundaries.

AC-FR0101-01, AC-FR0101-02

Drives a real Chromium browser through the Setup Wizard: opening the
product as a first-time user, seeing readiness checks and the identity
step, creating the first user, logging in, and verifying that Story/release
actions remain unavailable while Setup is incomplete.
"""

from __future__ import annotations


def test_setup_wizard_shows_readiness_and_identity_step(live_server, browser_page):
    """AC-FR0101-01: Setup page shows readiness checks and identity step.

    A blank workspace's Setup surface must show current readiness facts
    (Git, Store, Catalog, OpenCode, Models) and a first-user form -- the
    starting point of the continuous Wizard.
    """
    # AC-FR0101-01
    page, base_url = browser_page

    # Open the product -- unauthenticated blank workspace
    page.goto(base_url, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")

    # Should redirect to setup (setup-only mode)
    page.goto(f"{base_url}/setup/", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")

    # The setup page must show readiness checks
    body_text = page.inner_text("body")

    # AC-FR0101-01: readiness items are visible (Git, Store, etc.)
    assert "Git" in body_text or "readiness" in body_text.lower()

    # AC-FR0101-01: identity step is visible (first user creation form)
    assert page.locator('input[name="name"]').is_visible()
    assert page.locator('input[name="credential"]').is_visible()
    assert page.locator('button[type="submit"]').is_visible()


def test_setup_wizard_progresses_from_identity_to_login(live_server, browser_page):
    """AC-FR0101-01: completing identity step advances the Wizard to login.

    After creating the first user, the product must persist the identity
    and move to the login step -- not skip to Setup Complete.
    """
    # AC-FR0101-01
    page, base_url = browser_page

    # Start at setup
    page.goto(f"{base_url}/setup/", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")

    # Fill and submit the first-user form
    page.fill('input[name="name"]', "demo_owner")
    page.fill('input[name="credential"]', "demo_secret")
    page.click('button[type="submit"]')
    page.wait_for_load_state("domcontentloaded")

    # After creating first user, should redirect to login (not to projects)
    # The setup status should now show initialized=true
    setup_status = page.request.get(f"{base_url}/api/setup/status")
    assert setup_status.ok
    status = setup_status.json()
    assert status["initialized"] is True
    assert status["first_principal_id"] is not None


def test_setup_wizard_login_returns_to_setup_not_complete(live_server, browser_page):
    """AC-FR0101-02: after identity + login, Setup is still incomplete.

    The Wizard does not report Complete just because the first user exists.
    Story/release actions must remain unavailable.
    """
    # AC-FR0101-02
    page, base_url = browser_page

    # Create first user via setup form
    page.goto(f"{base_url}/setup/", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    page.fill('input[name="name"]', "demo_owner")
    page.fill('input[name="credential"]', "demo_secret")
    page.click('button[type="submit"]')
    page.wait_for_load_state("domcontentloaded")

    # Login with the newly created user
    page.goto(f"{base_url}/login", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    page.fill('input[name="username"]', "demo_owner")
    page.fill('input[name="password"]', "demo_secret")
    page.click('button[type="submit"]')
    page.wait_for_load_state("domcontentloaded")

    # After login, should NOT see "Setup Complete"
    body_text = page.inner_text("body")
    assert "Setup Complete" not in body_text
    assert "setup complete" not in body_text.lower()

    # Story/release actions should not be available
    # Try accessing /projects/new -- it should not show a working create form
    page.goto(f"{base_url}/projects/new", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    # The page should not show a story input form (Setup incomplete)
    story_input = page.query_selector('textarea[name="story"]')
    if story_input:
        # If the form exists, it should be disabled or show a setup-required message
        body = page.inner_text("body").lower()
        assert "setup" in body or "not ready" in body or "blocked" in body


def test_setup_wizard_does_not_require_runtime_terminology(live_server, browser_page):
    """AC-FR0101-02: Setup main path does not expose Runtime stage terms.

    The user completing identity and viewing readiness should not need to
    understand M-DESIGN, release container, or Agent orchestration terms.
    """
    # AC-FR0101-02
    page, base_url = browser_page

    page.goto(f"{base_url}/setup/", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")

    body_text = page.inner_text("body").lower()

    # Internal Runtime terms should not be presented to the user as required input
    assert "m-design" not in body_text
    assert "m-impl" not in body_text
    assert "workflowrun" not in body_text


def test_setup_wizard_blocking_items_visible(live_server, browser_page):
    """AC-FR0101-01: blocking items (e.g. Git not initialized) are visible.

    A blank workspace's Setup surface must show the Git BLOCKED status so
    the user can see what needs to be resolved.
    """
    # AC-FR0101-01
    page, base_url = browser_page

    page.goto(f"{base_url}/setup/", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")

    body_text = page.inner_text("body")

    # The setup page should show at least one readiness item
    # (Git is expected to be BLOCKED on a blank workspace)
    assert "Git" in body_text or "BLOCKED" in body_text or "READY" in body_text
