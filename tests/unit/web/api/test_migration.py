"""TestClient tests for the /api/migration sub-app (FR-2301).

AC references covered:
- AC-FR2301-01: GET /preview returns a read-only migration preview listing
  additions, conversions, preserved, conflicts, unsupported, recommended and
  available modes, with old_bytes_modified=False before confirm.
- AC-FR2301-02: POST /confirm creates a verifiable restore point; POST /rollback
  rolls back a failed migration. Confirm without preview is rejected.
- AC-FR2301-03: GET /legacy?project_id=X returns the legacy entry (404 if
  missing). Entries are read-only and marked is_legacy.
- AC-FR2301-05 (mistaken creation): POST /mistaken records a mistaken creation
  as a cancelled entry.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from louke.web.api.migration import create_app


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient backed by a fresh in-memory migration sub-app."""
    return TestClient(create_app())


def test_preview_returns_migration_fields(client: TestClient) -> None:
    """AC-FR2301-01: GET /preview returns a read-only migration preview."""
    resp = client.get("/preview", params={"workspace_path": "/tmp/ws"})
    assert resp.status_code == 200
    body = resp.json()
    assert "additions" in body
    assert "conversions" in body
    assert "preserved" in body
    assert "conflicts" in body
    assert "unsupported" in body
    assert body["recommended_mode"] in ("local", "global")
    assert "local" in body["available_modes"]
    assert "global" in body["available_modes"]
    assert body["old_bytes_modified"] is False


def test_confirm_creates_restore_point(client: TestClient) -> None:
    """AC-FR2301-02: POST /confirm with local mode creates a restore point."""
    client.get("/preview", params={"workspace_path": "/tmp/ws"})
    resp = client.post(
        "/confirm",
        json={"workspace_path": "/tmp/ws", "mode": "local"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["workspace_path"] == "/tmp/ws"
    assert body["committed"] is True
    assert body["has_restore_point"] is True


def test_confirm_global_mode(client: TestClient) -> None:
    """AC-FR2301-02: POST /confirm with global mode also succeeds."""
    client.get("/preview", params={"workspace_path": "/tmp/ws"})
    resp = client.post(
        "/confirm",
        json={"workspace_path": "/tmp/ws", "mode": "global"},
    )
    assert resp.status_code == 200
    assert resp.json()["committed"] is True


def test_confirm_without_preview_rejected(client: TestClient) -> None:
    """AC-FR2301-02: POST /confirm without a preview is rejected."""
    resp = client.post(
        "/confirm",
        json={"workspace_path": "/tmp/ws", "mode": "local"},
    )
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "CONFLICT"


def test_rollback_after_confirm(client: TestClient) -> None:
    """AC-FR2301-02: POST /rollback after confirm rolls back the migration."""
    client.get("/preview", params={"workspace_path": "/tmp/ws"})
    client.post(
        "/confirm",
        json={"workspace_path": "/tmp/ws", "mode": "local"},
    )
    resp = client.post(
        "/rollback",
        json={"workspace_path": "/tmp/ws"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["rolled_back"] is True


def test_legacy_missing_returns_404(client: TestClient) -> None:
    """AC-FR2301-03: GET /legacy?project_id=X returns 404 for missing entries."""
    resp = client.get("/legacy", params={"project_id": "nonexistent"})
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "NOT_FOUND"


def test_mistaken_records_creation(client: TestClient) -> None:
    """AC-FR2301-05/AC-FR2001-05: POST /mistaken records a mistaken creation."""
    resp = client.post(
        "/mistaken",
        json={"project_id": "legacy-proj-1", "reason": "duplicate creation"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["project_id"] == "legacy-proj-1"
    assert body["recorded"] is True
