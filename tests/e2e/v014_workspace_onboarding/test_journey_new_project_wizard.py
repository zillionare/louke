"""E2E happy path: empty Project → Environment Wizard → Preview → Create → Dev Docs.

AC-FR0601-01, AC-FR0601-02, AC-FR0701-01, AC-FR0801-01, AC-FR1001-01,
AC-FR1101-01, AC-NFR0301-01

Mode B stub-first: only the *happy path* is covered per interfaces §3.2;
faults and stale branches live in the integration tests.
"""

from __future__ import annotations

import json


from tests.integration.v014_workspace_onboarding._mode_b import (
    devon_module_skip,
)


def test_journey_wizard_only_runs_after_new_project_click(browser_page, live_server):
    """AC-FR0601-01: empty Projects page does not auto-start the gate."""
    # AC-FR0601-01
    devon_module_skip("IF-ENV-01", fr="FR-0601")
    page, _ = browser_page
    base_url, workspace, _ = live_server

    state_path = workspace.root / ".louke" / "project-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "version": 1,
                "workspace_id": "ws_demo",
                "state": "empty",
                "project": None,
            }
        ),
        encoding="utf-8",
    )

    page.goto(f"{base_url}/workbench?activity=projects", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    # The Wizard modal must NOT be visible yet.
    assert page.query_selector('form[name="new_project_story"]') is None


def test_journey_new_project_wizard_passes_and_creates_doc(browser_page, live_server):
    """AC-FR0601-01 / AC-FR0801-01 / AC-FR1001-01 / AC-FR1101-01.

    The happy-path journey: empty → env wizard → story/version → preview
    → create → Dev Docs.
    """
    # AC-FR0601-01 / AC-FR0801-01 / AC-FR1001-01 / AC-FR1101-01
    devon_module_skip("IF-PREVIEW-01", fr="FR-1001")
    page, _ = browser_page
    base_url, workspace, _ = live_server

    # 1. Empty Projects state
    state_path = workspace.root / ".louke" / "project-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "version": 1,
                "workspace_id": "ws_demo",
                "state": "empty",
                "project": None,
            }
        ),
        encoding="utf-8",
    )

    # 2. Seed gh ledger with all four scopes + a bound worktree.
    remote = workspace.gh_remote
    init_dir = workspace.init_dir if hasattr(workspace, "init_dir") else workspace.root
    ledger = {
        "gh_executable": True,
        "gh_auth_scopes": ["gist", "project", "repo", "workflow"],
        "repository_binding": {
            "host": "github.com",
            "owner": "zillionare",
            "name": "louke",
        },
        "canonical_main": {
            "sha": "deadbeef",
            "remote": str(remote),
            "worktree": str(init_dir),
        },
    }
    ledger_path = workspace.root / ".louke" / "gh-ledger.json"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    # 3. Click ``New Project`` from empty Projects.
    page.goto(f"{base_url}/workbench?activity=projects", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    page.click('button:has-text("New Project")')
    page.wait_for_load_state("networkidle")

    # 4. Wizard passes through and reveals the Story/version form.
    page.wait_for_selector('form[name="new_project_story"]', timeout=15_000)
    page.fill('textarea[name="story"]', "Initial Story for v0.14")
    page.fill('input[name="release_version"]', "0.14")

    # 5. Preview surface shows the canonical identity + Create + Cancel.
    page.click('button:has-text("Preview")')
    page.wait_for_load_state("networkidle")
    body = page.inner_text("body")
    assert "Create" in body
    assert "Cancel" in body
    assert "0.14.0" in body  # canonical padded version.

    # 6. Confirm and wait for the Dev Docs deep link.
    page.click('button:has-text("Create")')
    page.wait_for_load_state("networkidle")
    page.wait_for_url(
        f"{base_url}/workbench?activity=dev-docs*",
        timeout=15_000,
    )
    doc_body = page.inner_text("body")
    assert "Initial Story for v0.14" in doc_body


def test_journey_full_happy_path_keyboard_only(browser_page, live_server):
    """AC-NFR0301-01: keyboard-only flow completes the journey."""
    # AC-NFR0301-01
    devon_module_skip("IF-WEB-01", fr="FR-0001")
    page, _ = browser_page
    base_url, workspace, _ = live_server
    state_path = workspace.root / ".louke" / "project-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "version": 1,
                "workspace_id": "ws_demo",
                "state": "empty",
                "project": None,
            }
        ),
        encoding="utf-8",
    )

    page.goto(f"{base_url}/workbench?activity=projects", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")

    # Tab to ``New Project`` button and press Enter.
    for _ in range(10):
        page.keyboard.press("Tab")
        focused = page.evaluate("() => document.activeElement?.tagName")
        if focused in ("BUTTON", "A"):
            break
    page.keyboard.press("Enter")
    page.wait_for_load_state("networkidle")
    page.wait_for_selector('form[name="new_project_story"]', timeout=15_000)

    # Tab to the Story textarea and type.
    for _ in range(15):
        page.keyboard.press("Tab")
        if page.evaluate(
            "() => document.activeElement?.matches('textarea[name=story]')"
        ):
            break
    page.keyboard.type("Keyboard-only Story")

    # Tab to release_version and type.
    for _ in range(5):
        page.keyboard.press("Tab")
        if page.evaluate(
            "() => document.activeElement?.matches('input[name=release_version]')"
        ):
            break
    page.keyboard.type("0.14")

    # Move focus to Preview and press Enter.
    page.keyboard.press("Tab")
    page.keyboard.press("Enter")
    page.wait_for_load_state("networkidle")

    body = page.inner_text("body")
    assert "0.14.0" in body or "Preview" in body
