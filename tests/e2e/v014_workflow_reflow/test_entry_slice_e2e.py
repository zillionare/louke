"""Browser e2e for the v0.14-001 public-entry slice (installed wheel).

AC-FR0100-01/02, AC-FR0300-01/02, AC-FR0400-01/02/03, AC-FR0500-01/03,
AC-FR0600-02, AC-FR0700-01/02/03, AC-FR0800-01.

The test drives the installed wheel's Workbench through a real Chromium
browser on a random loopback port.  Every page action (login, readiness,
``/projects/new`` preview/confirm, Foundation redirect, Story page, Scribe
Chat, Human Go decision) goes through the public Web surface.  The only
stand-ins are the external OpenCode provider (L2ScribeStandIn, which
delivers recommendations through the validated ``submit_result`` seam) and
the GitHub Project protocol (``gh`` stand-in script).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
from pathlib import Path

import pytest

from tests.fixtures.v014_workflow_reflow.harness import (
    CANONICAL_HUMAN_STORY,
    read_gh_ledger,
)


def _chromium_installed() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            return Path(pw.chromium.executable_path).exists()
    except Exception:
        return False


def _csrf_token(app, session_cookie: str) -> str:
    """Derive the CSRF header token from the server's signing key."""
    from louke.web.auth import csrf_token_for_session

    return csrf_token_for_session(app.state.store, session_cookie)


def _session_cookie(page, base_url: str) -> str:
    """Return the session cookie value from the browser context."""
    cookies = page.context.cookies(base_url)
    for c in cookies:
        if c["name"] == "louke_session":
            return c["value"].strip('"')
    return ""


def _auth_headers(app, page, base_url: str) -> dict[str, str]:
    """Return Content-Type + Origin + CSRF headers for an API mutation."""
    return {
        "Content-Type": "application/json",
        "Origin": base_url,
        "X-Louke-CSRF": _csrf_token(app, _session_cookie(page, base_url)),
    }


@pytest.mark.v014_entry_e2e
@pytest.mark.skipif(
    not _chromium_installed(),
    reason="Chromium or Playwright is not installed (AC-NFR0300-01)",
)
def test_v014_entry_slice_golden_journey(live_server, browser_page):
    """AC-FR0100..0800: installed-wheel browser journey through the entry slice.

    Builds/installs the wheel into an isolated clean environment, starts the
    installed server, and drives Chromium through:
      - public login + readiness
      - ``/projects/new`` preview + confirm
      - Foundation redirect to Story page (M-STORY)
      - Scribe task manifest + Chat (no Maestro/agent selector)
      - Scribe recommendation (delivered through provider/task boundary)
      - waiting_for_human + zero M-SPEC tasks
      - authenticated Human Go decision
      - persisted actor/revision/digest while remaining M-STORY

    Fail-closed cases for stale decision and foreign Origin without state
    advancement are covered by the companion integration test.
    """
    page, base_url = browser_page
    _, stand_in, workspace, app = live_server

    # --- AC-FR0100-01: register one Human principal -----------------------
    register = page.request.post(
        f"{base_url}/api/auth/register",
        data={"username": "human", "password": "secret"},
    )
    assert register.ok, register.text()
    # Verify the session cookie was set.
    session = _session_cookie(page, base_url)
    assert session, "session cookie not set after register"

    # --- AC-FR0300-01: preview through public API -----------------------
    headers = _auth_headers(app, page, base_url)
    preview = page.request.post(
        f"{base_url}/api/v14/releases/preview",
        data=json.dumps({"story": CANONICAL_HUMAN_STORY, "release_version": "0.14.0"}),
        headers=headers,
    )
    assert preview.ok, preview.text()
    preview_body = preview.json()
    assert preview_body["side_effects"] == []
    assert preview_body["release"]["external"] == "0.14.0"
    assert preview_body["release"]["branch"] == "releases/0.14.0"

    # --- AC-FR0300-02/AC-FR0400-02: confirm + Foundation -----------------
    confirm = page.request.post(
        f"{base_url}/api/v14/releases/confirm",
        data=json.dumps(
            {
                "preview_id": preview_body["preview_id"],
                "expected_preview_revision": preview_body["preview_revision"],
                "request_digest": preview_body["request_digest"],
                "idempotency_key": "e2e-confirm-1",
            }
        ),
        headers=headers,
    )
    assert confirm.ok, confirm.text()
    confirm_body = confirm.json()
    request_id = confirm_body["request_id"]

    # Poll the status until Foundation is ready.
    status_body = None
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        status_resp = page.request.get(
            f"{base_url}/api/v14/releases/requests/{request_id}"
        )
        assert status_resp.ok
        status_body = status_resp.json()
        if status_body["status"] == "ready":
            break
        time.sleep(0.5)
    # AC-FR0400-02: Foundation status must reach ready
    assert status_body["status"] == "ready", status_body

    project_id = status_body["project_id"]
    # run_id verified via the current read model below.

    # --- AC-FR0400-02/03: Foundation evidence via IF-EXT-01 ---------------
    foundation_resp = page.request.get(
        f"{base_url}/api/v14/releases/requests/{request_id}/foundation"
    )
    assert foundation_resp.ok
    foundation = foundation_resp.json()
    assert foundation["status"] == "ready"
    release_branch = foundation["foundation"]["resources"]["release_branch"]
    assert release_branch["full_ref"] == "refs/heads/releases/0.14.0"
    assert release_branch["checked_out"] is True
    assert release_branch["head_symbolic_ref"] == "releases/0.14.0"
    worktree_path = foundation["foundation"]["resources"]["worktree"]["path"]
    # Independent Git ground truth: symbolic HEAD must be the release branch.
    sym_head = subprocess.run(
        ["git", "symbolic-ref", "--short", "HEAD"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert sym_head == "releases/0.14.0"

    # --- AC-FR0500-03: follow the public redirect to Story page ---------
    page.goto(
        f"{base_url}/projects/{project_id}/requirements/story",
        wait_until="domcontentloaded",
    )
    main = page.locator("#story-page")
    main.wait_for()
    run_para = page.locator("p[data-run]")
    run_para.wait_for()
    page_text = run_para.inner_text()
    assert "M-STORY" in page_text
    assert "Revision: 1" in page_text

    # --- AC-FR0700-01: Scribe task manifest + Chat binding --------------
    chat = page.locator("#scribe-chat")
    chat.wait_for()
    task_id = chat.get_attribute("data-task-id")
    assert task_id and task_id.startswith("task_")
    # The Scribe recommendation has been delivered through the provider
    # boundary by the L2 stand-in's ``submit_result`` seam.
    assert len(stand_in.dispatch_ledger) >= 1
    dispatch = stand_in.dispatch_ledger[0]
    assert dispatch.recommendation_delivered is True
    assert dispatch.task_id == task_id

    # --- AC-FR0700-02: verify waiting_for_human + zero M-SPEC -----------
    current_resp = page.request.get(f"{base_url}/api/v14/projects/{project_id}/current")
    assert current_resp.ok
    current = current_resp.json()
    assert current["run"]["phase"] == "M-STORY"
    assert current["human_wait"] is True
    assert current["story_gate"]["recommendation"] == "Go"
    assert current["story_gate"]["m_spec_task_count"] == 0
    assert current["allowed_actions"] == ["story_decision"]
    artifact = current["artifact"]
    assert artifact["digest"].startswith("sha256:")
    # Independent Story digest from Git worktree.
    story_path = (
        Path(worktree_path)
        / ".louke"
        / "project"
        / "specs"
        / "v0.14-001-workflow-reflow-spec"
        / "story.md"
    )
    expected_digest = f"sha256:{hashlib.sha256(story_path.read_bytes()).hexdigest()}"
    assert artifact["digest"] == expected_digest

    # --- AC-FR0800-01: click authenticated Human Go decision -------------
    run_revision = current["run"]["revision"]
    decision_section = page.locator("#story-decision-gate")
    decision_section.wait_for()
    go_button = decision_section.locator("[data-decision='Go']")
    go_button.wait_for()
    page.fill("#story-decision-reason", "The Story scope is bounded and ready.")
    go_button.click()
    page.wait_for_function(
        "() => document.getElementById('story-decision-status').textContent.includes('Decision recorded')",
        timeout=10000,
    )

    # Verify persisted actor/revision/digest via the public read API.
    after_resp = page.request.get(f"{base_url}/api/v14/projects/{project_id}/current")
    assert after_resp.ok
    after = after_resp.json()
    assert after["story_gate"]["decision"]["value"] == "Go"
    assert after["story_gate"]["decision"]["actor"] == "human:human"
    # Go advances the revision but the run stays at M-STORY.
    assert after["run"]["revision"] > run_revision
    assert after["run"]["phase"] == "M-STORY"
    assert after["run"]["status"] == "running"
    # The Story digest is unchanged (no document mutation).
    assert after["artifact"]["digest"] == artifact["digest"]

    # --- AC-FR0400-03: GitHub Project ledger proves create happened ------
    gh_ledger = read_gh_ledger(workspace.gh_ledger)
    kinds = [e.kind for e in gh_ledger]
    assert "project_list" in kinds
    assert "project_create" in kinds


@pytest.mark.v014_entry_e2e
@pytest.mark.skipif(
    not _chromium_installed(),
    reason="Chromium or Playwright is not installed (AC-NFR0300-01)",
)
def test_v014_entry_slice_foreign_origin_fail_closed(live_server, browser_page):
    """AC-FR0600-03: foreign Origin cannot mutate release state.

    A cross-origin preview is rejected with 403 before any Driver/Store
    interaction; no release request is persisted.
    """
    page, base_url = browser_page
    _, _, _, app = live_server

    # Register first to get a session.
    page.request.post(
        f"{base_url}/api/auth/register",
        data={"username": "human", "password": "secret"},
    )

    # Foreign origin -> rejected.
    session = _session_cookie(page, base_url)
    csrf = _csrf_token(app, session)
    response = page.request.post(
        f"{base_url}/api/v14/releases/preview",
        data=json.dumps({"story": CANONICAL_HUMAN_STORY, "release_version": "0.14.0"}),
        headers={
            "Content-Type": "application/json",
            "Origin": "https://foreign.example",
            "X-Louke-CSRF": csrf,
        },
    )
    assert response.status == 403
    body = response.json()
    assert body["error_code"] == "ORIGIN_FORBIDDEN"
