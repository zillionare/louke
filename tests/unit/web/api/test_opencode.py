"""TestClient tests for the /api/opencode sub-app (FR-1401, mock-labeled).

AC references covered:
- AC-FR1401-01: instances can be listed and created (mock adapter).

Every response MUST include ``adapter_kind: "mock"`` so the frontend can show
a "this is a mock, real adapter coming in B4" warning.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from louke.web.api.opencode import create_app


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient backed by a fresh in-memory opencode sub-app."""
    return TestClient(create_app())


def test_status_returns_mock_adapter_kind(client: TestClient) -> None:
    """The status endpoint reports the adapter kind as mock."""
    resp = client.get("/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["adapter_kind"] == "mock"
    assert body["ready"] is True
    assert "pending" in body["message"].lower()


def test_list_instances_empty(client: TestClient) -> None:
    """AC-FR1401-01: instances can be listed (empty by default)."""
    resp = client.get("/instances")
    assert resp.status_code == 200
    body = resp.json()
    assert body["adapter_kind"] == "mock"
    assert body["items"] == []


def test_create_instance(client: TestClient) -> None:
    """AC-FR1401-01: an instance can be created."""
    resp = client.post("/instances")
    assert resp.status_code == 201
    body = resp.json()
    assert body["adapter_kind"] == "mock"
    assert body["instance"]["id"]
    assert body["instance"]["status"] == "running"


def test_send_and_list_messages(client: TestClient) -> None:
    """AC-FR1401-01: messages can be sent and listed."""
    # Create an instance first.
    resp = client.post("/instances")
    instance_id = resp.json()["instance"]["id"]

    # Send a message; the adapter echoes it back internally.
    resp = client.post(
        f"/instances/{instance_id}/messages",
        json={"content": "hello"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["adapter_kind"] == "mock"
    assert body["message"]["role"] == "user"
    assert body["message"]["content"] == "hello"

    # List messages: the echo reply should be the second message.
    resp = client.get(f"/instances/{instance_id}/messages")
    assert resp.status_code == 200
    body = resp.json()
    assert body["adapter_kind"] == "mock"
    assert len(body["items"]) == 2
    assert body["items"][0]["role"] == "user"
    assert body["items"][0]["content"] == "hello"
    assert body["items"][1]["role"] == "assistant"
    assert body["items"][1]["content"] == "echo: hello"


def test_stop_instance(client: TestClient) -> None:
    """AC-FR1401-01: an instance can be stopped."""
    resp = client.post("/instances")
    instance_id = resp.json()["instance"]["id"]

    resp = client.delete("/instances", params={"id": instance_id})
    assert resp.status_code == 200
    body = resp.json()
    assert body["adapter_kind"] == "mock"
    assert body["instance"]["status"] == "stopped"
