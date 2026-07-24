"""TestClient tests for the /api/setup sub-app (v0.14-004).

AC references covered:
- AC-FR0301-01: GET /status returns the v2 manifest projection.
- AC-FR0201-01: POST /first-user creates the first principal and
  advances the v2 manifest from pending_user to pending_model.
- AC-FR0101-04: missing required body fields return 400 VALIDATION_ERROR.
- AC-NFR0101-01: CSRF token is required for the first-user POST.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from louke.web.api.setup import create_app


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """Return a TestClient backed by a fresh persisted setup sub-app."""
    project = tmp_path / ".louke" / "project"
    project.mkdir(parents=True)
    (project / "project.toml").write_text("[project]\n", encoding="utf-8")
    return TestClient(create_app(tmp_path))


def _csrf_token(client: TestClient) -> str:
    """Fetch a fresh CSRF token from the v2 status endpoint."""
    resp = client.get("/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "csrf_token" in body
    return body["csrf_token"]


def test_status_returns_v2_manifest_shape(client: TestClient) -> None:
    """AC-FR0301-01: GET /status returns the v2 manifest projection."""
    resp = client.get("/status")
    assert resp.status_code == 200
    body = resp.json()
    # v2 shape per interfaces §IF-SETUP-01.
    assert body["status"] == "pending_user"
    assert body["first_user"] is None
    assert body["model_check"] is None
    assert body["revision"] == 0
    assert "create_first_user" in body["available_actions"]
    assert body["continue_url"] == "/setup"
    assert len(body["csrf_token"]) == 64


def test_status_advances_after_first_user(client: TestClient) -> None:
    """AC-FR0301-01: status reflects the v2 manifest advance after first-user."""
    token = _csrf_token(client)
    resp = client.post(
        "/first-user",
        json={"name": "alice", "credential": "secret-token", "expected_revision": 0},
        headers={"X-Louke-CSRF": token},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["principal_id"].startswith("prin_")
    assert body["status"] == "pending_model"
    assert body["setup_revision"] == 1
    # Manifest is persisted.
    status = client.get("/status").json()
    assert status["status"] == "pending_model"
    assert status["first_user"]["principal_id"].startswith("prin_")


def test_first_user_without_csrf_is_rejected(client: TestClient) -> None:
    """AC-NFR0101-01: a POST without CSRF token returns 403."""
    resp = client.post(
        "/first-user",
        json={"name": "alice", "credential": "secret-token"},
    )
    assert resp.status_code == 403


def test_first_user_with_invalid_csrf_is_rejected(client: TestClient) -> None:
    """AC-NFR0101-01: a POST with wrong CSRF token returns 403."""
    resp = client.post(
        "/first-user",
        json={"name": "alice", "credential": "secret-token"},
        headers={"X-Louke-CSRF": "deadbeef" * 8},
    )
    assert resp.status_code == 403


def test_first_user_persists_to_workspace(client: TestClient, tmp_path: Path) -> None:
    """The first user is present after a fresh setup sub-app is created."""
    token = _csrf_token(client)
    client.post(
        "/first-user",
        json={"name": "alice", "credential": "secret-token"},
        headers={"X-Louke-CSRF": token},
    )
    # Restart the sub-app against the same workspace.
    restarted = TestClient(create_app(tmp_path))
    status = restarted.get("/status").json()
    assert status["status"] == "pending_model"
    assert status["first_user"]["principal_id"].startswith("prin_")


def test_create_first_user_missing_fields(client: TestClient) -> None:
    """AC-FR0101-04: missing required fields return 400 VALIDATION_ERROR."""
    token = _csrf_token(client)
    resp = client.post(
        "/first-user",
        json={"name": "alice"},
        headers={"X-Louke-CSRF": token},
    )
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "VALIDATION_ERROR"


def test_csrf_token_rotation_on_re_issue(client: TestClient) -> None:
    """AC-NFR0101-01: re-issuing a CSRF token invalidates the old one."""
    # First issuance: get a token and use it successfully.
    token1 = _csrf_token(client)
    resp = client.post(
        "/first-user",
        json={"name": "alice", "credential": "secret-token"},
        headers={"X-Louke-CSRF": token1},
    )
    assert resp.status_code == 201
    # A fresh token issuance rotates the old one out.
    token2_resp = client.get("/status")
    assert token2_resp.status_code == 200
    token2 = token2_resp.json()["csrf_token"]
    assert token1 != token2, "issue_for_session must rotate the stored token"
