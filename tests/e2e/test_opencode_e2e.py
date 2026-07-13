"""FR-0001: OpenCode HTTP API e2e (instance creation + message isolation + stop)."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from louke.opencode_api import app


@pytest.fixture
def client():
    """TestClient for the opencode_api sub-app. Each test gets a fresh in-memory adapter."""
    return TestClient(app)


def test_create_instance_e2e(client):
    """AC-FR0001-01: POST /api/opencode/instances returns 201 with unique id and starting|running status."""
    r = client.post("/api/opencode/instances", json={})
    assert r.status_code == 201, r.text
    body = r.json()
    assert "id" in body
    assert body["status"] in ("starting", "running")


def test_two_instances_message_isolation_e2e(client):
    """AC-FR0001-02/03: 2 instances; message sent to one must not appear in the other."""
    a = client.post("/api/opencode/instances", json={}).json()["id"]
    b = client.post("/api/opencode/instances", json={}).json()["id"]
    r = client.post(f"/api/opencode/instances/{a}/messages", json={"content": "hi A"})
    assert r.status_code == 202, r.text
    msgs_a = client.get(f"/api/opencode/instances/{a}/messages").json()["messages"]
    msgs_b = client.get(f"/api/opencode/instances/{b}/messages").json()["messages"]
    assert any("hi A" in m["content"] for m in msgs_a)
    assert not any("hi A" in m["content"] for m in msgs_b)


def test_models_agent_command_passthrough_e2e(client):
    """AC-FR0001-03: '/' commands like /models and /agent are passed through to OpenCode."""
    iid = client.post("/api/opencode/instances", json={}).json()["id"]
    r = client.post(
        f"/api/opencode/instances/{iid}/messages", json={"content": "/models"}
    )
    assert r.status_code == 202, r.text


def test_stop_instance_blocks_subsequent_send_e2e(client):
    """AC-FR0001-04: stopped instance blocks subsequent send (409 INSTANCE_NOT_RUNNING)."""
    iid = client.post("/api/opencode/instances", json={}).json()["id"]
    r = client.delete(f"/api/opencode/instances?id={iid}")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "stopped"
    r2 = client.post(f"/api/opencode/instances/{iid}/messages", json={"content": "x"})
    assert r2.status_code == 409, r2.text
    assert r2.json()["error_code"] == "INSTANCE_NOT_RUNNING"
