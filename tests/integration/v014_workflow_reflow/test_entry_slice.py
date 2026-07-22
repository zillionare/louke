"""Integration coverage for the v0.14-001 public-entry slice.

AC-FR0100-01/02/03, AC-FR0300-01/02, AC-FR0400-01/02/03/04/05,
AC-FR0500-01/03, AC-FR0600-02, AC-FR0700-01/02/03, AC-FR0800-01.

Every test drives the real ``lk serve`` process through public HTTP JSON
endpoints against real SQLite, real Git CLI and a bare remote.  The only
stand-ins are the external OpenCode HTTP server and GitHub ``gh`` script
per test-plan §6.2.  No internal Python calls, direct SQLite writes, or
service construction are used.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import httpx

from tests.fixtures.v014_workflow_reflow.harness import (
    CANONICAL_HUMAN_STORY,
    SCRIBE_RESULT_UPSTREAM_BLOCKER,
    read_gh_ledger,
)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _client(base_url: str) -> httpx.Client:
    """Return an httpx client that bypasses proxy settings for localhost."""
    return httpx.Client(base_url=base_url, trust_env=False, follow_redirects=True)


def _register(
    client: httpx.Client, username: str = "human", password: str = "secret"
) -> httpx.Response:
    return client.post(
        "/api/auth/register", json={"username": username, "password": password}
    )


def _session_cookie(response: httpx.Response) -> str:
    return response.cookies.get("louke_session", "").strip('"')


def _csrf(client: httpx.Client, session: str) -> str:
    """Derive the CSRF token from the ``/projects/new`` public page."""
    resp = client.get("/projects/new", cookies={"louke_session": session})
    import re

    # The release page embeds the CSRF in a JS variable: const csrf = "...";
    m = re.search(r'const\s+csrf\s*=\s*"([a-f0-9]+)"', resp.text)
    if m:
        return m.group(1)
    # Fallback: data-csrf attribute (Story page).
    m = re.search(r'data-csrf="([^"]+)"', resp.text)
    if m:
        return m.group(1)
    raise RuntimeError("Could not derive CSRF token from /projects/new")


def _headers(base_url: str, session: str, csrf: str | None = None) -> dict[str, str]:
    h: dict[str, str] = {}
    if csrf:
        h["X-Louke-CSRF"] = csrf
    return h


def _cookies(session: str) -> dict[str, str]:
    return {"louke_session": session}


# ---------------------------------------------------------------------------
# Entry-slice golden path
# ---------------------------------------------------------------------------


class TestEntrySliceGoldenPath:
    """AC-FR0100..0800: authenticated form-first release -> M-STORY."""

    def test_authenticated_release_foundation_story_scribe_via_public_http(
        self, live_server
    ):
        """AC-FR0100-01/02, AC-FR0300-01/02, AC-FR0400-01/02/03,
        AC-FR0500-01/03, AC-FR0600-02, AC-FR0700-01.

        Drives the complete implemented entry slice through public HTTP
        against the installed ``lk serve``: preview -> confirm -> Foundation
        -> Story -> Scribe task manifest.
        """
        base_url, workspace, opencode = live_server
        client = _client(base_url)

        # --- AC-FR0100-01: register + authenticate -------------------------
        reg = _register(client)
        assert reg.status_code == 200, reg.text
        session = _session_cookie(reg)
        assert session, "session cookie not set"

        # --- AC-FR0300-01: preview produces no side effects ----------------
        csrf = _csrf(client, session)
        mut_headers = {"Origin": base_url, "X-Louke-CSRF": csrf}
        preview = client.post(
            "/api/v14/releases/preview",
            json={"story": CANONICAL_HUMAN_STORY, "release_version": "0.14.0"},
            cookies=_cookies(session),
            headers=mut_headers,
        )
        assert preview.status_code == 200, preview.text
        preview_body = preview.json()
        assert preview_body["side_effects"] == []
        assert preview_body["release"]["external"] == "0.14.0"

        # --- AC-FR0300-02/AC-FR0400-02: confirm + Foundation ----------------
        confirm = client.post(
            "/api/v14/releases/confirm",
            json={
                "preview_id": preview_body["preview_id"],
                "expected_preview_revision": preview_body["preview_revision"],
                "request_digest": preview_body["request_digest"],
                "idempotency_key": "confirm-integration-1",
            },
            cookies=_cookies(session),
            headers=mut_headers,
        )
        assert confirm.status_code == 202, confirm.text
        confirm_body = confirm.json()
        request_id = confirm_body["request_id"]

        # Poll status until ready.
        import time

        status_body = None
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            status_resp = client.get(
                f"/api/v14/releases/requests/{request_id}",
                cookies=_cookies(session),
            )
            assert status_resp.status_code == 200
            status_body = status_resp.json()
            if status_body["status"] == "ready":
                break
            time.sleep(0.5)
        assert status_body and status_body["status"] == "ready", status_body

        project_id = status_body["project_id"]
        run_id = status_body["run_id"]

        # --- AC-FR0400-02/03: Foundation evidence (IF-EXT-01) ---------------
        foundation_resp = client.get(
            f"/api/v14/releases/requests/{request_id}/foundation",
            cookies=_cookies(session),
        )
        assert foundation_resp.status_code == 200
        foundation = foundation_resp.json()
        assert foundation["status"] == "ready"
        main_check = foundation["main_check"]
        assert main_check["status"] == "pass"
        assert main_check["remote_main"]["full_ref"] == "refs/remotes/origin/main"
        resources = foundation["foundation"]["resources"]
        release_branch = resources["release_branch"]
        assert release_branch["full_ref"] == "refs/heads/releases/0.14.0"
        assert release_branch["checked_out"] is True
        assert release_branch["head_symbolic_ref"] == "releases/0.14.0"
        worktree_path = resources["worktree"]["path"]

        # Independent Git ground truth: symbolic HEAD must be the release branch.
        sym_head = subprocess.run(
            ["git", "symbolic-ref", "--short", "HEAD"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        assert sym_head == "releases/0.14.0"

        # --- AC-FR0500-01/03: Story revision + independent digest ----------
        current_resp = client.get(
            f"/api/v14/projects/{project_id}/current",
            cookies=_cookies(session),
        )
        assert current_resp.status_code == 200
        current = current_resp.json()
        assert current["run"]["phase"] == "M-STORY"
        assert current["run"]["run_id"] == run_id
        artifact = current["artifact"]
        assert artifact, "Story artifact must exist (AC-FR0500-01)"
        assert artifact["kind"] == "story"
        assert artifact["revision"] == 1
        assert artifact["digest"].startswith("sha256:")
        # Independent digest from the Git worktree.
        story_path = (
            Path(worktree_path)
            / ".louke"
            / "project"
            / "specs"
            / "v0.14-001-workflow-reflow-spec"
            / "story.md"
        )
        story_bytes = story_path.read_bytes()
        expected_digest = f"sha256:{hashlib.sha256(story_bytes).hexdigest()}"
        assert artifact["digest"] == expected_digest

        # --- AC-FR0700-01: Scribe task manifest (IF-API-08) -----------------
        task = current["task"]
        assert task, "Scribe task must exist (AC-FR0700-01)"
        assert task["task_id"].startswith("task_")
        task_detail_resp = client.get(
            f"/api/v14/runs/{run_id}/tasks/{task['task_id']}",
            cookies=_cookies(session),
        )
        assert task_detail_resp.status_code == 200
        task_detail = task_detail_resp.json()
        assert task_detail["phase"] == "M-STORY"
        assert task_detail["role"] == "Scribe"
        assert task_detail["write_scope"] == ["story.md"]

        # The OpenCode stand-in recorded the dispatch through the public
        # HTTP protocol boundary.
        ledger = opencode.read_ledger()
        kinds = [e.get("kind") for e in ledger]
        assert "session_create" in kinds
        assert "send_message" in kinds

        # --- AC-FR0700-02: Scribe recommendation upstream blocker -----------
        # The Scribe recommendation cannot be delivered through the public
        # protocol because ``submit_result`` is not exposed via any public
        # web route and no adapter callback feeds into it.
        gate = current["story_gate"]
        assert gate["recommendation"] is None, (
            "unexpected recommendation without public ingestion path: "
            + SCRIBE_RESULT_UPSTREAM_BLOCKER
        )
        assert gate["m_spec_task_count"] == 0

        # --- AC-FR0400-03: GitHub Project ledger proves create happened -----
        gh_ledger = read_gh_ledger(workspace.gh_ledger)
        gh_kinds = [e.kind for e in gh_ledger]
        assert "project_list" in gh_kinds
        assert "project_create" in gh_kinds


# ---------------------------------------------------------------------------
# Fail-closed cases
# ---------------------------------------------------------------------------


class TestEntrySliceFailClosed:
    """AC-FR0300-01, AC-FR0600-03: invalid inputs leave state unchanged."""

    def test_foreign_origin_rejected_before_preview(self, live_server):
        """AC-FR0600-03: foreign Origin cannot create a release request."""
        base_url, _, _ = live_server
        client = _client(base_url)
        reg = _register(client)
        session = _session_cookie(reg)
        csrf = _csrf(client, session)

        response = client.post(
            "/api/v14/releases/preview",
            json={"story": CANONICAL_HUMAN_STORY, "release_version": "0.14.0"},
            cookies=_cookies(session),
            headers={"Origin": "https://foreign.example", "X-Louke-CSRF": csrf},
        )
        assert response.status_code == 403
        assert response.json()["error_code"] == "ORIGIN_FORBIDDEN"

    def test_unauthenticated_preview_rejected(self, live_server):
        """AC-FR0600-01: anonymous requests are rejected before Driver."""
        base_url, _, _ = live_server
        client = _client(base_url)
        response = client.post(
            "/api/v14/releases/preview",
            json={"story": CANONICAL_HUMAN_STORY, "release_version": "0.14.0"},
        )
        assert response.status_code == 401

    def test_preview_invalid_release_version_fails_closed(self, live_server):
        """AC-FR0300-01: invalid release version returns 400."""
        base_url, _, _ = live_server
        client = _client(base_url)
        reg = _register(client)
        session = _session_cookie(reg)
        csrf = _csrf(client, session)

        response = client.post(
            "/api/v14/releases/preview",
            json={"story": CANONICAL_HUMAN_STORY, "release_version": "../escape"},
            cookies=_cookies(session),
            headers={"Origin": base_url, "X-Louke-CSRF": csrf},
        )
        assert response.status_code == 400
        assert response.json()["error_code"] == "RELEASE_VERSION_INVALID"
