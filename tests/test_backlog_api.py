"""FR-0601: local story backlog (persisted to .louke/project/backlog.json)."""

import json
import pytest
from louke.backlog_api import app


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".louke" / "project").mkdir(parents=True)
    return ws


@pytest.fixture
def client(workspace, monkeypatch):
    monkeypatch.chdir(workspace)
    from starlette.testclient import TestClient

    return TestClient(app)


def test_list_empty(client):
    r = client.get("/api/backlog")
    assert r.status_code == 200
    body = r.json()
    assert body["entries"] == []


def test_create_entry_returns_201(client, workspace):
    """AC-FR0601-01: 有效 story 条目提交 -> 持久化并出现在本地列表中."""
    r = client.post("/api/backlog", json={"story": "as user, I want X"})
    assert r.status_code == 201
    body = r.json()
    assert "id" in body
    assert body["story"] == "as user, I want X"
    assert body["status"] == "pending"
    # Persisted to .louke/project/backlog.json
    p = workspace / ".louke" / "project" / "backlog.json"
    assert p.exists()
    data = json.loads(p.read_text(encoding="utf-8"))
    assert any(e["story"] == "as user, I want X" for e in data["entries"])


def test_create_rejects_empty_story(client):
    r = client.post("/api/backlog", json={"story": ""})
    assert r.status_code == 400


def test_list_after_create(client):
    client.post("/api/backlog", json={"story": "story-1"})
    client.post("/api/backlog", json={"story": "story-2"})
    r = client.get("/api/backlog")
    body = r.json()
    assert len(body["entries"]) == 2
    stories = [e["story"] for e in body["entries"]]
    assert "story-1" in stories and "story-2" in stories


def test_delete_with_start_development_removes_entry(client, workspace):
    """AC-FR0601-02: 选中条目点击进入开发 -> 仅选中项传给 Louke 新 story 开发流程."""
    r1 = client.post("/api/backlog", json={"story": "to-start"})
    entry_id = r1.json()["id"]
    r2 = client.request(
        "DELETE",
        "/api/backlog",
        json={"id": entry_id, "action": "start_development"},
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["id"] == entry_id
    assert body["status"] == "removed"
    assert body["workflow_started"] is True
    # Entry no longer in list
    r3 = client.get("/api/backlog")
    ids = [e["id"] for e in r3.json()["entries"]]
    assert entry_id not in ids


def test_delete_without_selection_returns_400(client, workspace):
    """AC-FR0601-03: 未选中条目点击进入开发 -> 不启动新 story 流程并提示需先选择."""
    r1 = client.post("/api/backlog", json={"story": "to-keep"})
    entry_id = r1.json()["id"]
    # Missing "action" key
    r2 = client.request("DELETE", "/api/backlog", json={"id": entry_id})
    assert r2.status_code == 400
    # Entry still in list
    r3 = client.get("/api/backlog")
    ids = [e["id"] for e in r3.json()["entries"]]
    assert entry_id in ids
