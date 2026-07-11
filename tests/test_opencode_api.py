"""FR-0001: OpenCode instance + message HTTP API."""
import pytest
from louke.opencode_api import app


@pytest.fixture
def client():
    from starlette.testclient import TestClient
    return TestClient(app)


def test_create_instance_returns_201_with_id(client):
    """AC-FR0001-01 + AC-FR0001-03: 创建实例返回 201, 可选择, id 唯一; 后续 models/agent 命令依赖该实例."""
    r = client.post("/api/opencode/instances", json={})
    assert r.status_code == 201
    body = r.json()
    assert "id" in body
    assert body["status"] in ("starting", "running")


def test_list_instances_returns_at_least_created(client):
    client.post("/api/opencode/instances", json={})
    r = client.get("/api/opencode/instances")
    assert r.status_code == 200
    body = r.json()
    assert "instances" in body
    assert len(body["instances"]) >= 1
    for inst in body["instances"]:
        assert "id" in inst and "status" in inst


def test_delete_instance_is_idempotent(client):
    """AC-FR0001-04: 停止实例 -> 显示非运行, 后续发送不被当作成功执行."""
    r1 = client.post("/api/opencode/instances", json={})
    inst_id = r1.json()["id"]
    r2 = client.delete(f"/api/opencode/instances?id={inst_id}")
    assert r2.status_code == 200
    r3 = client.delete(f"/api/opencode/instances?id={inst_id}")
    assert r3.status_code == 200
    assert r3.json()["status"] == "stopped"


def test_send_message_to_running_instance_returns_202(client):
    r1 = client.post("/api/opencode/instances", json={})
    inst_id = r1.json()["id"]
    r2 = client.post(f"/api/opencode/instances/{inst_id}/messages", json={"content": "hello"})
    assert r2.status_code == 202
    body = r2.json()
    assert body["accepted"] is True
    assert body["message"]["role"] == "user"
    assert body["message"]["content"] == "hello"


def test_send_message_to_unknown_instance_returns_404(client):
    r = client.post("/api/opencode/instances/no-such/messages", json={"content": "x"})
    assert r.status_code == 404


def test_message_isolation_between_instances(client):
    r1 = client.post("/api/opencode/instances", json={})
    r2 = client.post("/api/opencode/instances", json={})
    id_a, id_b = r1.json()["id"], r2.json()["id"]
    client.post(f"/api/opencode/instances/{id_a}/messages", json={"content": "msg-to-a"})
    client.post(f"/api/opencode/instances/{id_b}/messages", json={"content": "msg-to-b"})

    msgs_a = client.get(f"/api/opencode/instances/{id_a}/messages").json()["messages"]
    msgs_b = client.get(f"/api/opencode/instances/{id_b}/messages").json()["messages"]

    a_contents = [m["content"] for m in msgs_a if m["role"] == "user"]
    b_contents = [m["content"] for m in msgs_b if m["role"] == "user"]

    assert "msg-to-a" in a_contents
    assert "msg-to-b" not in a_contents
    assert "msg-to-b" in b_contents
    assert "msg-to-a" not in b_contents
