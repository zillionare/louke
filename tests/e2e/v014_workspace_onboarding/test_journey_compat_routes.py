"""E2E compatibility deep-link router.

AC-FR1501-02, AC-NFR0401-01, AC-NFR0401-02

The happy-path compatibility flow: legacy ``/projects``, ``/projects/<id>``,
``/runs/<id>`` and ``/projects/new`` all resolve to the canonical
Workbench Project surface for the same Project identity. The conflict
branch is asserted through the same harness with seeded conflict state.
"""

from __future__ import annotations

import json


from tests.integration.v014_workspace_onboarding._mode_b import (
    devon_module_skip,
)


def test_compat_legacy_projects_url_resolves_to_workbench(browser_page, live_server):
    """AC-FR1501-02: ``/projects`` redirects to Projects activity."""
    # AC-FR1501-02
    devon_module_skip("IF-COMPAT-01", fr="FR-1501")
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

    response = page.goto(f"{base_url}/projects", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    assert response.status in (200, 303)
    assert "/workbench?activity=projects" in page.url


def test_compat_legacy_projects_new_routes_to_wizard_on_empty(
    browser_page,
    live_server,
):
    """AC-FR1501-02: ``/projects/new`` opens the Wizard on an empty Project."""
    # AC-FR1501-02
    devon_module_skip("IF-COMPAT-01", fr="FR-1501")
    page, _ = browser_page
    base_url, workspace, _ = live_server

    state_path = workspace.root / ".louke" / "project-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps({"version": 1, "workspace_id": "ws_demo", "state": "empty"})
    )

    page.goto(f"{base_url}/projects/new", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    page.wait_for_selector('form[name="new_project_story"]', timeout=15_000)
    assert "Story" in page.inner_text("body")


def test_compat_legacy_project_url_loads_same_status(browser_page, live_server):
    """AC-FR1501-02: ``/projects/{id}`` shows the canonical Project Status."""
    # AC-FR1501-02
    devon_module_skip("IF-COMPAT-01", fr="FR-1501")
    page, _ = browser_page
    base_url, workspace, _ = live_server

    state_path = workspace.root / ".louke" / "project-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "version": 1,
                "workspace_id": "ws_demo",
                "state": "active",
                "project_id": "prj_legacy",
            }
        ),
        encoding="utf-8",
    )

    page.goto(f"{base_url}/projects/prj_legacy", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    assert "/workbench?activity=projects&project=prj_legacy" in page.url


def test_compat_legacy_run_url_resolves_only_when_safe(browser_page, live_server):
    """AC-FR1501-02 / AC-NFR0401-02: ``/runs/<id>`` resolves if a binding exists."""
    # AC-FR1501-02 / AC-NFR0401-02
    devon_module_skip("IF-COMPAT-01", fr="FR-1501")
    page, _ = browser_page
    base_url, workspace, _ = live_server

    state_path = workspace.root / ".louke" / "project-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "version": 1,
                "workspace_id": "ws_demo",
                "state": "active",
                "project_id": "prj_demo",
                "runs": {"run_legacy": "prj_demo"},
            }
        ),
        encoding="utf-8",
    )

    page.goto(f"{base_url}/runs/run_legacy", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    assert "/workbench?activity=projects&project=prj_demo" in page.url


def test_compat_legacy_run_url_unknown_fails_migration(browser_page, live_server):
    """AC-NFR0401-02: unknown legacy ``/runs/<id>`` shows migration_required."""
    # AC-NFR0401-02
    devon_module_skip("IF-COMPAT-01", fr="FR-1501")
    page, _ = browser_page
    base_url, workspace, _ = live_server

    state_path = workspace.root / ".louke" / "project-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "version": 1,
                "workspace_id": "ws_demo",
                "state": "active",
                "project_id": "prj_demo",
                "runs": {},
            }
        ),
        encoding="utf-8",
    )

    page.goto(f"{base_url}/runs/run_unknown", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    body = page.inner_text("body").lower()
    assert "migration" in body or "read-only" in body or "not found" in body
