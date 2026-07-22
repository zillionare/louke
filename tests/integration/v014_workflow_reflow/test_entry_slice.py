"""Integration coverage for the v0.14-001 public-entry slice.

AC-FR0100-01/02/03, AC-FR0300-01/02, AC-FR0400-01/02/03/04/05,
AC-FR0500-01/03, AC-FR0600-02, AC-FR0700-01/02/03, AC-FR0800-01.

Every test drives the real Starlette app through public HTTP JSON endpoints
(IF-API-03/04/08, IF-EXT-01) against real SQLite, real Git CLI and a bare
remote.  The only stand-ins are the external OpenCode provider (L2ScribeStandIn)
and GitHub Project protocol (``gh`` script) per test-plan §6.2.

No test imports a private orchestrator/adapter, writes SQLite directly, or
pre-creates Runtime state.  All state is established through the public
preview/confirm/Foundation/Story/Scribe/task/action endpoints.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


from tests.fixtures.v014_workflow_reflow.harness import (
    CANONICAL_HUMAN_STORY,
    auth_headers,
    csrf_token,
    read_gh_ledger,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _preview(client, story: str = CANONICAL_HUMAN_STORY):
    """Create a release preview through the authenticated public HTTP surface."""
    response = client.post(
        "/api/v14/releases/preview",
        headers=auth_headers(client),
        json={"story": story, "release_version": "0.14.0"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _confirm(client, preview: dict):
    """Confirm the preview and return the release request read model."""
    response = client.post(
        "/api/v14/releases/confirm",
        headers=auth_headers(client),
        json={
            "preview_id": preview["preview_id"],
            "expected_preview_revision": preview["preview_revision"],
            "request_digest": preview["request_digest"],
            "idempotency_key": "confirm-integration-1",
        },
    )
    assert response.status_code == 202, response.text
    return response.json()


def _status(client, request_id: str):
    """Read the public release status read model."""
    response = client.get(f"/api/v14/releases/requests/{request_id}")
    assert response.status_code == 200, response.text
    return response.json()


def _foundation(client, request_id: str):
    """Read the public Foundation evidence (IF-EXT-01)."""
    response = client.get(f"/api/v14/releases/requests/{request_id}/foundation")
    assert response.status_code == 200, response.text
    return response.json()


def _current(client, project_id: str):
    """Read the public project current read model (IF-API-04)."""
    response = client.get(f"/api/v14/projects/{project_id}/current")
    assert response.status_code == 200, response.text
    return response.json()


def _task(client, run_id: str, task_id: str):
    """Read the public Scribe task read model (IF-API-08)."""
    response = client.get(f"/api/v14/runs/{run_id}/tasks/{task_id}")
    assert response.status_code == 200, response.text
    return response.json()


def _story_gate(client, run_id: str):
    """Read the story gate from the project current model."""
    current = _current(client, _project_id_for_run(client, run_id))
    return current["story_gate"]


def _project_id_for_run(client, run_id: str) -> str:
    binding = client.app.state.v14_release_entry.project_for_run(run_id)
    assert binding, f"no project binding for run {run_id}"
    return binding["project_id"]


def _git_symbolic_head(workspace, worktree_path: str) -> str:
    """Return the symbolic HEAD of the controlled worktree."""
    result = subprocess.run(
        ["git", "symbolic-ref", "--short", "HEAD"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _git_head_sha(workspace, worktree_path: str) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Entry-slice golden path
# ---------------------------------------------------------------------------


class TestEntrySliceGoldenPath:
    """AC-FR0100..0800: authenticated form-first release -> M-STORY Human gate."""

    def test_authenticated_release_foundation_story_scribe_gate_go(
        self, client, workspace, stand_in
    ):
        """AC-FR0100-01/02, AC-FR0300-01/02, AC-FR0400-01/02/03, AC-FR0500-01/03,
        AC-FR0600-02, AC-FR0700-01/02, AC-FR0800-01.

        Drives the complete implemented entry slice through public HTTP:
        preview -> confirm -> Foundation -> Story -> Scribe task -> Go gate.
        """
        # --- AC-FR0300-01: preview produces no side effects ----------------
        preview = _preview(client)
        assert preview["side_effects"] == []
        assert preview["release"]["external"] == "0.14.0"
        assert preview["release"]["branch"] == "releases/0.14.0"
        assert preview["workspace_id"] == "louke-0.14.0"

        # --- AC-FR0300-02/AC-FR0400-02: confirm + Foundation ----------------
        confirm = _confirm(client, preview)
        assert confirm["status"] in ("foundation", "ready")
        request_id = confirm["request_id"]
        status = _status(client, request_id)
        assert status["status"] == "ready"
        assert status["project_id"], "project_id must be assigned by Foundation"
        assert status["run_id"], "run_id must be assigned by Foundation"
        continue_url = status["continue_url"]
        assert continue_url == f"/projects/{status['project_id']}/requirements/story"

        # --- AC-FR0400-02/03: Foundation evidence (IF-EXT-01) ---------------
        foundation = _foundation(client, request_id)
        assert foundation["status"] == "ready"
        main_check = foundation["main_check"]
        assert main_check["status"] == "pass"
        assert main_check["remote_main"]["full_ref"] == "refs/remotes/origin/main"
        assert main_check["previous_branch"]["relation"] == "merged"
        foundation_resources = foundation["foundation"]["resources"]
        release_branch = foundation_resources["release_branch"]
        assert release_branch["full_ref"] == "refs/heads/releases/0.14.0"
        assert release_branch["checked_out"] is True
        assert release_branch["head_symbolic_ref"] == "releases/0.14.0"
        worktree_path = foundation_resources["worktree"]["path"]
        # Independent Git ground truth: symbolic HEAD and SHA.
        assert _git_symbolic_head(workspace, worktree_path) == "releases/0.14.0"
        head_sha = _git_head_sha(workspace, worktree_path)
        assert release_branch["head_sha"] == head_sha
        assert foundation_resources["spec_directory"]["path"].endswith(SPEC_ID_REF)

        # --- AC-FR0500-01/03: Story revision + navigation -------------------
        project_id = status["project_id"]
        run_id = status["run_id"]
        current = _current(client, project_id)
        assert current["run"]["phase"] == "M-STORY"
        assert current["run"]["run_id"] == run_id
        artifact = current["artifact"]
        assert artifact, "Story artifact must exist after Foundation (AC-FR0500-01)"
        assert artifact["kind"] == "story"
        assert artifact["revision"] == 1
        assert artifact["digest"].startswith("sha256:")
        assert artifact["locked"] is True
        # Independent digest: hash the Story body from the Git worktree.
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
        assert task is not None
        assert task["task_id"].startswith("task_")
        assert task["status"] in ("running", "pending", "blocked")
        task_detail = _task(client, run_id, task["task_id"])
        assert task_detail["phase"] == "M-STORY"
        assert task_detail["role"] == "Scribe"
        assert task_detail["artifact"]["kind"] == "story"
        assert task_detail["write_scope"] == ["story.md"]
        assert task_detail["session_id"], (
            "Scribe session must be established (AC-FR0700-01)"
        )
        # The stand-in delivered a Go recommendation through submit_result.
        assert len(stand_in.dispatch_ledger) >= 1
        dispatch = stand_in.dispatch_ledger[0]
        assert dispatch.recommendation_delivered is True
        assert dispatch.task_id == task["task_id"]

        # --- AC-FR0700-02: waiting_for_human, zero M-SPEC tasks ------------
        gate = current["story_gate"]
        assert gate["recommendation"] == "Go"
        assert gate["human_wait"] is True
        assert gate["pending_action"] == "story_decision"
        assert gate["m_spec_task_count"] == 0

        # --- AC-FR0600-02: read model stability on re-read -----------------
        current_again = _current(client, project_id)
        assert current_again["run"]["revision"] == current["run"]["revision"]
        assert current_again["run"]["phase"] == "M-STORY"
        assert current_again["artifact"]["digest"] == artifact["digest"]

        # --- AC-FR0800-01: authenticated Human Go decision ------------------
        run_revision = current["run"]["revision"]
        artifact_revision = artifact["revision"]
        decision_response = client.post(
            f"/api/v14/runs/{run_id}/actions",
            headers=auth_headers(client),
            json={
                "action": "story_decision",
                "expected_run_revision": run_revision,
                "expected_artifact_revision": artifact_revision,
                "idempotency_key": "human-go-1",
                "payload": {
                    "candidate": "Go",
                    "reason": "The Story scope is bounded and ready.",
                    "project_id": project_id,
                },
            },
        )
        assert decision_response.status_code == 200, decision_response.text
        decision = decision_response.json()
        assert decision["value"] == "Go"
        assert decision["actor"] == "human:human"
        assert decision["backlog_entry_count"] == 0
        assert decision["run"]["phase"] == "M-STORY"
        # Go advances only the revision; the run stays at M-STORY.
        assert decision["run"]["revision"] > run_revision
        assert decision["run"]["status"] == "running"

        # --- AC-FR0700-03: idempotent replay returns same decision ----------
        replay = client.post(
            f"/api/v14/runs/{run_id}/actions",
            headers=auth_headers(client),
            json={
                "action": "story_decision",
                "expected_run_revision": run_revision,
                "expected_artifact_revision": artifact_revision,
                "idempotency_key": "human-go-1",
                "payload": {
                    "candidate": "Go",
                    "reason": "The Story scope is bounded and ready.",
                    "project_id": project_id,
                },
            },
        )
        assert replay.status_code == 200
        assert replay.json()["value"] == "Go"
        assert replay.json()["run"]["revision"] == decision["run"]["revision"]

        # --- AC-FR0400-03: GitHub Project ledger proves create happened -----
        gh_ledger = read_gh_ledger(workspace.gh_ledger)
        kinds = [e.kind for e in gh_ledger]
        assert "project_list" in kinds
        assert "project_create" in kinds


SPEC_ID_REF = "v0.14-001-workflow-reflow-spec"


# ---------------------------------------------------------------------------
# Fail-closed cases
# ---------------------------------------------------------------------------


class TestEntrySliceFailClosed:
    """AC-FR0300-01, AC-FR0600-03, AC-FR0700-03: invalid inputs leave state unchanged."""

    def test_foreign_origin_rejected_before_preview(self, client):
        """AC-FR0600-03: foreign Origin cannot create a release request."""
        response = client.post(
            "/api/v14/releases/preview",
            headers={
                "Origin": "https://foreign.example",
                "X-Louke-CSRF": csrf_token(client),
            },
            json={"story": "Ship the reflow", "release_version": "0.14.0"},
        )
        assert response.status_code == 403
        assert response.json()["error_code"] == "ORIGIN_FORBIDDEN"

    def test_stale_decision_revision_rejected_without_advancement(
        self, client, stand_in
    ):
        """AC-FR0700-03: stale run revision is rejected; state unchanged."""
        preview = _preview(client)
        confirm = _confirm(client, preview)
        status = _status(client, confirm["request_id"])
        run_id = status["run_id"]
        project_id = status["project_id"]
        current = _current(client, project_id)
        run_revision = current["run"]["revision"]
        artifact = current["artifact"]

        # Use an intentionally stale revision.
        stale = client.post(
            f"/api/v14/runs/{run_id}/actions",
            headers=auth_headers(client),
            json={
                "action": "story_decision",
                "expected_run_revision": run_revision + 999,
                "expected_artifact_revision": artifact["revision"],
                "idempotency_key": "stale-1",
                "payload": {
                    "candidate": "Go",
                    "reason": "stale attempt",
                    "project_id": project_id,
                },
            },
        )
        assert stale.status_code == 409
        assert stale.json()["error_code"] == "WORKFLOW_STATE_CONFLICT"
        # State unchanged.
        after = _current(client, project_id)
        assert after["run"]["revision"] == run_revision
        assert after["story_gate"]["decision"] is None

    def test_invalid_candidate_rejected_without_advancement(self, client, stand_in):
        """AC-FR0700-03: candidate outside {Go,Park,No-Go} is rejected."""
        preview = _preview(client)
        confirm = _confirm(client, preview)
        status = _status(client, confirm["request_id"])
        run_id = status["run_id"]
        project_id = status["project_id"]
        current = _current(client, project_id)
        run_revision = current["run"]["revision"]
        artifact = current["artifact"]

        invalid = client.post(
            f"/api/v14/runs/{run_id}/actions",
            headers=auth_headers(client),
            json={
                "action": "story_decision",
                "expected_run_revision": run_revision,
                "expected_artifact_revision": artifact["revision"],
                "idempotency_key": "invalid-cand-1",
                "payload": {
                    "candidate": "Maybe",
                    "reason": "invalid",
                    "project_id": project_id,
                },
            },
        )
        assert invalid.status_code == 400
        assert invalid.json()["error_code"] == "VALIDATION_FAILED"
        after = _current(client, project_id)
        assert after["story_gate"]["decision"] is None

    def test_unauthenticated_preview_rejected(self, app):
        """AC-FR0600-01: anonymous requests are rejected before Driver."""
        # Use a bare client with no session cookie.
        from starlette.testclient import TestClient

        bare_client = TestClient(app)
        response = bare_client.post(
            "/api/v14/releases/preview",
            json={"story": CANONICAL_HUMAN_STORY, "release_version": "0.14.0"},
        )
        assert response.status_code == 401

    def test_park_decision_creates_backlog_and_stays_terminal(self, client, stand_in):
        """AC-FR0800-01: Park persists one Backlog identity and terminal state."""
        preview = _preview(client)
        confirm = _confirm(client, preview)
        status = _status(client, confirm["request_id"])
        run_id = status["run_id"]
        project_id = status["project_id"]
        current = _current(client, project_id)
        run_revision = current["run"]["revision"]
        artifact = current["artifact"]

        park = client.post(
            f"/api/v14/runs/{run_id}/actions",
            headers=auth_headers(client),
            json={
                "action": "story_decision",
                "expected_run_revision": run_revision,
                "expected_artifact_revision": artifact["revision"],
                "idempotency_key": "human-park-1",
                "payload": {
                    "candidate": "Park",
                    "reason": "Deprioritised for this cycle.",
                    "project_id": project_id,
                },
            },
        )
        assert park.status_code == 200, park.text
        decision = park.json()
        assert decision["value"] == "Park"
        assert decision["backlog_entry_count"] == 1
        assert decision["run"]["status"] == "parked"

    def test_preview_invalid_release_version_fails_closed(self, client):
        """AC-FR0300-01: invalid release version returns 400 without persistence."""
        response = client.post(
            "/api/v14/releases/preview",
            headers=auth_headers(client),
            json={"story": "Ship the reflow", "release_version": "../escape"},
        )
        assert response.status_code == 400
        assert response.json()["error_code"] == "RELEASE_VERSION_INVALID"
