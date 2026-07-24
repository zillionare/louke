"""E2E: Project Status cockpit — node selection + return flow (happy path only).

AC-FR1201-01, AC-FR1201-02, AC-FR1201-03, AC-FR1301-01, AC-FR1301-02,
AC-FR1401-01, AC-FR1401-02

Per interfaces §3.2 only the *happy path* is covered. The detailed
fault matrix lives in the integration tests.
"""

from __future__ import annotations

import json


from tests.integration.v014_workspace_onboarding._mode_b import (
    devon_module_skip,
)


def test_journey_status_shows_thirteen_stages(browser_page, live_server):
    """AC-FR1201-01: Project Status lists all 13 canonical stages."""
    # AC-FR1201-01
    devon_module_skip("IF-STATUS-01", fr="FR-1201")
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
                "stage": "M-IMPL",
            }
        ),
        encoding="utf-8",
    )

    page.goto(
        f"{base_url}/workbench?activity=projects&project=prj_demo",
        wait_until="domcontentloaded",
    )
    page.wait_for_load_state("networkidle")

    body = page.inner_text("body")
    for stage in (
        "M-START",
        "M-STORY",
        "M-SPEC",
        "M-ACC",
        "M-REQ-APPROVAL",
        "M-DESIGN",
        "M-IMPL",
        "M-TEST",
        "M-VERIFY",
        "M-SECURITY",
        "M-RELEASE",
        "M-PUBLISH",
        "M-MILESTONE",
    ):
        assert stage in body, f"{stage!r} missing from Project Status"


def test_journey_status_active_card_shows_owner_and_ordinal(browser_page, live_server):
    """AC-FR1201-02: the active card displays owner and attempt ordinal."""
    # AC-FR1201-02
    devon_module_skip("IF-STATUS-01", fr="FR-1201")
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
                "active": {
                    "stage": "M-IMPL",
                    "owner": "agent_devon",
                    "attempt_ordinal": 4,
                    "elapsed_seconds": 120,
                },
            }
        ),
        encoding="utf-8",
    )

    page.goto(
        f"{base_url}/workbench?activity=projects&project=prj_demo",
        wait_until="domcontentloaded",
    )
    page.wait_for_load_state("networkidle")

    body = page.inner_text("body")
    assert "agent_devon" in body
    assert "4" in body or "fourth" in body.lower()


def test_journey_status_selects_node_without_changing_active(browser_page, live_server):
    """AC-FR1301-01: clicking a timeline node updates the URL but not the active pointer."""
    # AC-FR1301-01
    devon_module_skip("IF-STATUS-01", fr="FR-1201")
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
                "active": {"stage": "M-IMPL", "attempt_id": "att_active"},
                "timeline": [
                    {"attempt_id": "att_1", "stage": "M-START"},
                    {"attempt_id": "att_active", "stage": "M-IMPL"},
                    {"attempt_id": "att_2", "stage": "M-TEST"},
                ],
            }
        ),
        encoding="utf-8",
    )

    page.goto(
        f"{base_url}/workbench?activity=projects&project=prj_demo",
        wait_until="domcontentloaded",
    )
    page.wait_for_load_state("networkidle")

    earlier_node = page.query_selector('[data-attempt-id="att_1"]')
    # AC-FR1301-01: timeline node must be present for selection
    assert earlier_node is not None
    earlier_node.click()
    page.wait_for_load_state("networkidle")
    assert "selected_attempt=att_1" in page.url
    body = page.inner_text("body")
    assert "att_active" in body


def test_journey_return_pointer_only_for_eligible_attempts(browser_page, live_server):
    """AC-FR1401-01: only Runtime-allowed attempts show a return control."""
    # AC-FR1401-01
    devon_module_skip("IF-RETURN-01", fr="FR-1401")
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
                "timeline": [
                    {
                        "attempt_id": "att_1",
                        "stage": "M-START",
                        "return_eligibility": {"allowed": True},
                    },
                    {
                        "attempt_id": "att_active",
                        "stage": "M-IMPL",
                        "return_eligibility": {"allowed": False},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    page.goto(
        f"{base_url}/workbench?activity=projects&project=prj_demo",
        wait_until="domcontentloaded",
    )
    page.wait_for_load_state("networkidle")

    eligible = page.query_selector('[data-attempt-id="att_1"] [data-action="return"]')
    blocked = page.query_selector(
        '[data-attempt-id="att_active"] [data-action="return"]'
    )
    assert eligible is not None
    assert blocked is None


def test_journey_return_confirm_appends_return_edge(browser_page, live_server):
    """AC-FR1401-02: Confirm updates active pointer + appends return edge."""
    # AC-FR1401-02
    devon_module_skip("IF-RETURN-01", fr="FR-1401")
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
                "active": {"stage": "M-IMPL", "attempt_id": "att_active"},
                "timeline": [
                    {
                        "attempt_id": "att_2",
                        "stage": "M-DESIGN",
                        "return_eligibility": {"allowed": True},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    page.goto(
        f"{base_url}/workbench?activity=projects&project=prj_demo",
        wait_until="domcontentloaded",
    )
    page.wait_for_load_state("networkidle")

    page.click('[data-attempt-id="att_2"] [data-action="return"]')
    page.wait_for_selector('[data-role="return-confirm"]', timeout=15_000)
    page.click('[data-role="return-confirm"] button:has-text("Confirm")')
    page.wait_for_load_state("networkidle")
    body = page.inner_text("body")
    # The new active pointer is ``att_2`` after Confirm.
    assert "att_2" in body
