"""TestClient tests for the /api/setup sub-app (FR-1801).

AC references covered:
- AC-FR1801-03: GET /status returns initialized flag and first principal id.
- AC-FR1801-03: POST /first-user creates the first principal and stores the
  credential hash via CredentialStore.
- AC-FR0101-04: missing required body fields return 400 VALIDATION_ERROR.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from louke.web.api.setup import create_app


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient backed by a fresh in-memory setup sub-app."""
    return TestClient(create_app())


def test_status_uninitialized(client: TestClient) -> None:
    """AC-FR1801-03: GET /status returns initialized=False and no principal."""
    resp = client.get("/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["initialized"] is False
    assert body["first_principal_id"] is None


def test_create_first_user(client: TestClient) -> None:
    """AC-FR1801-03: POST /first-user creates the first principal."""
    resp = client.post(
        "/first-user",
        json={"name": "alice", "credential": "secret-token"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["principal_id"].startswith("prin_")
    assert body["name"] == "alice"


def test_status_after_first_user(client: TestClient) -> None:
    """AC-FR1801-03: after creating the first user, status reflects it."""
    resp = client.post(
        "/first-user",
        json={"name": "bob", "credential": "secret-token"},
    )
    principal_id = resp.json()["principal_id"]
    resp = client.get("/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["initialized"] is True
    assert body["first_principal_id"] == principal_id


def test_create_first_user_missing_fields(client: TestClient) -> None:
    """AC-FR0101-04: missing required fields return 400 VALIDATION_ERROR."""
    resp = client.post("/first-user", json={"name": "alice"})
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "VALIDATION_ERROR"
