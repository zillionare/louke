"""FR-0601: local story backlog e2e (create / list / delete with workflow start)."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from louke.backlog_api import app


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """Workspace with empty .louke/project dir for backlog persistence."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".louke" / "project").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def client(workspace):
    return TestClient(app)


def test_create_backlog_entry_persists_e2e(client, workspace):
    """AC-FR0601-01: POST /api/backlog persists entry, GET returns it."""
    r = client.post("/api/backlog", json={"story": "test story alpha"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["story"] == "test story alpha"
    assert "id" in body
    entries = client.get("/api/backlog").json()["entries"]
    assert any(e["id"] == body["id"] for e in entries)


def test_delete_backlog_with_selection_removes_only_selected_e2e(client, workspace):
    """AC-FR0601-02: DELETE with action=start_development removes only the selected entry; others remain."""
    a = client.post("/api/backlog", json={"story": "A"}).json()["id"]
    b = client.post("/api/backlog", json={"story": "B"}).json()["id"]
    c = client.post("/api/backlog", json={"story": "C"}).json()["id"]
    r = client.request(
        "DELETE", "/api/backlog", json={"id": b, "action": "start_development"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["workflow_started"] is True
    ids = [e["id"] for e in client.get("/api/backlog").json()["entries"]]
    assert a in ids and c in ids and b not in ids


def test_delete_without_selection_returns_400_e2e(client, workspace):
    """AC-FR0601-03: DELETE without selection returns 400 SELECTION_REQUIRED; entry remains (no workflow started)."""
    a = client.post("/api/backlog", json={"story": "stay"}).json()["id"]
    r = client.request("DELETE", "/api/backlog", json={"id": a})
    assert r.status_code == 400, r.text
    assert r.json()["error_code"] == "SELECTION_REQUIRED"
    ids = [e["id"] for e in client.get("/api/backlog").json()["entries"]]
    assert a in ids
