"""Browser e2e for the v0.14-001 public-entry slice (installed wheel).

AC-FR0100-01/02, AC-FR0300-01/02, AC-FR0400-01/02/03, AC-FR0500-01/03,
AC-FR0600-02, AC-FR0700-01/02.

The test drives the installed ``lk serve`` through a real Chromium browser
on a random loopback port.  Every page action (login, readiness,
``/projects/new`` preview/confirm, Foundation redirect, Story page, Scribe
Chat) goes through the public Web surface.  The OpenCode stand-in is a
subprocess HTTP server communicating over the declared public protocol
boundary; the ``gh`` stand-in handles GitHub Project operations.
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
    SCRIBE_RESULT_UPSTREAM_BLOCKER,
    read_gh_ledger,
)


def _chromium_installed() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            return Path(pw.chromium.executable_path).exists()
    except Exception:
        return False


def _session_cookie(page, base_url: str) -> str:
    cookies = page.context.cookies(base_url)
    for c in cookies:
        if c["name"] == "louke_session":
            return c["value"].strip('"')
    return ""


def _csrf_from_page(page) -> str:
    """Read the CSRF token from the /projects/new page's JS variable."""
    return page.evaluate(
        """() => {
            // The release page embeds CSRF in: const csrf = "...";
            const m = document.documentElement.innerHTML.match(/const\\s+csrf\\s*=\\s*["']([a-f0-9]+)["']/);
            if (m) return m[1];
            const el = document.querySelector('[data-csrf]');
            return el ? el.dataset.csrf : '';
        }"""
    )


@pytest.mark.v014_entry_e2e
@pytest.mark.skipif(
    not _chromium_installed(),
    reason="Chromium or Playwright is not installed (AC-NFR0300-01)",
)
def test_v014_entry_slice_golden_journey(live_server, browser_page):
    """AC-FR0100..0700: installed-wheel browser journey through the entry slice.

    Drives Chromium through: login -> preview/confirm -> Foundation redirect
    -> Story page -> Scribe Chat binding.  The Scribe recommendation cannot
    be delivered through the public protocol (upstream blocker documented
    in SCRIBE_RESULT_UPSTREAM_BLOCKER).
    """
    page, base_url = browser_page
    _, workspace, opencode = live_server

    # --- AC-FR0100-01: register one Human principal -----------------------
    reg = page.request.post(
        f"{base_url}/api/auth/register",
        data={"username": "human", "password": "secret"},
    )
    assert reg.ok, reg.text()
    session = _session_cookie(page, base_url)
    assert session, "session cookie not set after register"

    # --- AC-FR0300-01: preview through public API -----------------------
    # Navigate to /projects/new to get a page with CSRF token.
    page.goto(f"{base_url}/projects/new", wait_until="domcontentloaded")
    csrf = _csrf_from_page(page)
    if not csrf:
        # The workbench page may have it.
        page.goto(f"{base_url}/", wait_until="domcontentloaded")
        csrf = _csrf_from_page(page)
    assert csrf, "CSRF token not found on any public page"

    preview = page.request.post(
        f"{base_url}/api/v14/releases/preview",
        data=json.dumps({"story": CANONICAL_HUMAN_STORY, "release_version": "0.14.0"}),
        headers={
            "Content-Type": "application/json",
            "Origin": base_url,
            "X-Louke-CSRF": csrf,
        },
    )
    assert preview.ok, preview.text()
    preview_body = preview.json()
    assert preview_body["side_effects"] == []
    assert preview_body["release"]["external"] == "0.14.0"

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
        headers={
            "Content-Type": "application/json",
            "Origin": base_url,
            "X-Louke-CSRF": csrf,
        },
    )
    assert confirm.ok, confirm.text()
    request_id = confirm.json()["request_id"]

    # Poll status until ready.
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
    assert status_body and status_body["status"] == "ready", status_body

    project_id = status_body["project_id"]

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
    # Independent Git ground truth.
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

    # The OpenCode stand-in recorded the dispatch through the public HTTP
    # protocol boundary.
    ledger = opencode.read_ledger()
    kinds = [e.get("kind") for e in ledger]
    assert "session_create" in kinds
    assert "send_message" in kinds

    # --- AC-FR0700-02: Scribe recommendation upstream blocker -----------
    current_resp = page.request.get(f"{base_url}/api/v14/projects/{project_id}/current")
    assert current_resp.ok
    current = current_resp.json()
    assert current["run"]["phase"] == "M-STORY"
    gate = current["story_gate"]
    # The recommendation is None because submit_result has no public path.
    assert gate["recommendation"] is None, (
        "unexpected recommendation without public ingestion path: "
        + SCRIBE_RESULT_UPSTREAM_BLOCKER
    )
    assert gate["m_spec_task_count"] == 0
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

    # --- AC-FR0400-03: GitHub Project ledger proves create happened ------
    gh_ledger = read_gh_ledger(workspace.gh_ledger)
    gh_kinds = [e.kind for e in gh_ledger]
    assert "project_list" in gh_kinds
    assert "project_create" in gh_kinds


@pytest.mark.v014_entry_e2e
@pytest.mark.skipif(
    not _chromium_installed(),
    reason="Chromium or Playwright is not installed (AC-NFR0300-01)",
)
def test_v014_entry_slice_foreign_origin_fail_closed(live_server, browser_page):
    """AC-FR0600-03: foreign Origin cannot mutate release state."""
    page, base_url = browser_page

    page.request.post(
        f"{base_url}/api/auth/register",
        data={"username": "human", "password": "secret"},
    )
    page.goto(f"{base_url}/projects/new", wait_until="domcontentloaded")
    csrf = _csrf_from_page(page)
    assert csrf

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
    assert response.json()["error_code"] == "ORIGIN_FORBIDDEN"
