"""TestClient tests for the /api/opencode sub-app (FR-1401, mock + real).

AC references covered:
- AC-FR1401-01: instances can be listed and created (mock adapter).
- AC-FR1401-04: abort (cancel current generation) and recover routes.
- AC-FR1401-05: recovery classification (running | lost | needs_attention).

Every response MUST include ``adapter_kind`` so the frontend can show a
"this is a mock, real adapter coming in B4" warning. For ``real`` mode the
sub-app surfaces real upstream errors (503/502/504/500) rather than
silently echoing like the mock.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import pytest
from starlette.testclient import TestClient

from louke.opencode import dispatch
from louke.opencode.adapter import Instance, Message
from louke.opencode.persistence import (
    ManagedInstanceState,
    OpenCodeInstanceStore,
)
from louke.web.api.opencode import create_app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Return a TestClient backed by a fresh in-memory opencode sub-app."""
    monkeypatch.chdir(tmp_path)
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


# ---------------------------------------------------------------------------
# B5: real adapter wiring tests
# ---------------------------------------------------------------------------


class _FakeRealAdapter:
    """A fake adapter that LOOKS like a RealOpenCodeAdapter.

    It carries ``_base_url`` (the marker the sub-app uses to detect
    ``adapter_kind == "real"``) but performs no real I/O. Tests inject it
    via ``create_app(adapter=...)`` to exercise the real-mode code paths
    without starting an HTTP server.
    """

    def __init__(self, base_url: str = "http://test") -> None:
        self._base_url = base_url
        self._instances: dict[str, Instance] = {}
        self._messages: dict[str, list[Message]] = {}
        self.cancel_calls: list[str] = []
        self.list_calls = 0

    def create(self, *, correlation_id: str) -> Instance:
        inst = Instance(id=f"sess-{len(self._instances) + 1}", status="running")
        self._instances[inst.id] = inst
        self._messages.setdefault(inst.id, [])
        return inst

    def list(self) -> List[Instance]:
        self.list_calls += 1
        return list(self._instances.values())

    def stop(self, instance_id: str) -> Instance:
        inst = self._instances.pop(instance_id, None)
        if inst is None:
            return Instance(id=instance_id, status="stopped")
        inst.status = "stopped"
        return inst

    def send_message(
        self, instance_id: str, content: str, *, correlation_id: str
    ) -> tuple[Message, bool]:
        msg = Message(
            id=f"msg-{len(self._messages.get(instance_id, [])) + 1}",
            instance_id=instance_id,
            role="user",
            kind="message",
            content=content,
        )
        self._messages.setdefault(instance_id, []).append(msg)
        return msg, True

    def list_messages(
        self, instance_id: str, *, after_message_id: Optional[str]
    ) -> List[Message]:
        return list(self._messages.get(instance_id, []))

    def cancel(self, instance_id: str, *, correlation_id: str) -> None:
        self.cancel_calls.append(instance_id)


def test_opencode_real_kind_requires_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """When real mode is requested but no base URL is set, /status is 503.

    The sub-app must NOT silently fall back to the mock adapter. The error
    envelope must carry ``adapter_kind: "real"`` and a clear message so the
    operator knows to set ``LOUKE_OPENCODE_BASE_URL``.
    """
    monkeypatch.setenv("LOUKE_OPENCODE_BACKEND", "real")
    monkeypatch.delenv("LOUKE_OPENCODE_BASE_URL", raising=False)

    client = TestClient(create_app(workspace_root=Path("/tmp/nonexistent-louke-b5")))
    resp = client.get("/status")
    assert resp.status_code == 503
    body = resp.json()
    assert body["adapter_kind"] == "real"
    assert body["ready"] is False
    assert "error_code" in body
    assert body["error_code"] == "OPENCODE_UNAVAILABLE"
    assert body["message"]


def test_opencode_real_status_includes_adapter_kind_real() -> None:
    """GET /status reports ``adapter_kind: "real"`` when a real adapter is cached.

    The kind is derived from the cached adapter's type (presence of
    ``_base_url``), not from an env var, so the frontend can trust the label.
    """
    fake = _FakeRealAdapter(base_url="http://test")
    client = TestClient(create_app(adapter=fake))
    resp = client.get("/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["adapter_kind"] == "real"
    assert body["ready"] is True
    assert body["base_url"] == "http://test"


def test_opencode_real_create_persists_instance(tmp_path: Path) -> None:
    """AC-FR1401-01/05: POST /instances in real mode persists ManagedInstanceState.

    Only ``adapter_kind == "real"`` persists; mock mode never writes to the
    store. The persisted row must carry ``status="running"`` and the
    server-assigned instance id.
    """
    fake = _FakeRealAdapter(base_url="http://test")
    client = TestClient(create_app(adapter=fake, workspace_root=tmp_path))

    resp = client.post("/instances")
    assert resp.status_code == 201
    body = resp.json()
    assert body["adapter_kind"] == "real"
    instance_id = body["instance"]["id"]

    store = OpenCodeInstanceStore(tmp_path)
    states = store.load_all()
    assert any(s.instance_id == instance_id for s in states)
    persisted = next(s for s in states if s.instance_id == instance_id)
    assert persisted.status == "running"
    assert persisted.base_url == "http://test"


def test_opencode_recover_route_returns_running() -> None:
    """AC-FR1401-04/05: POST /recover returns ``running`` when the adapter still lists the id."""
    fake = _FakeRealAdapter()
    inst = fake.create(correlation_id="t")
    client = TestClient(create_app(adapter=fake))
    resp = client.post(f"/instances/{inst.id}/recover")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "running"


def test_opencode_recover_route_returns_lost(tmp_path: Path) -> None:
    """AC-FR1401-05: POST /recover returns ``lost`` when the persisted pid is dead.

    A dead pid is authoritative: even if the adapter were reachable, the
    server we started is gone, so the instance is ``lost`` (not
    ``needs_attention``).
    """
    fake = _FakeRealAdapter()
    # Persist a state with a pid that is guaranteed dead (PID 2^31-1).
    store = OpenCodeInstanceStore(tmp_path)
    dead_pid = 2_147_483_647
    store.save(
        ManagedInstanceState(
            instance_id="ghost-session",
            workspace_path=str(tmp_path),
            pid=dead_pid,
            base_url="http://test",
            last_seen=0.0,
            status="running",
        )
    )
    client = TestClient(create_app(adapter=fake, workspace_root=tmp_path))
    resp = client.post("/instances/ghost-session/recover")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "lost"


def test_opencode_real_abort_returns_202() -> None:
    """AC-FR1401-04: POST /abort cancels the current generation and returns 202."""
    fake = _FakeRealAdapter()
    inst = fake.create(correlation_id="t")
    client = TestClient(create_app(adapter=fake))
    resp = client.post(f"/instances/{inst.id}/abort")
    assert resp.status_code == 202
    assert inst.id in fake.cancel_calls


def test_opencode_real_kinds_path_to_dispatch_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``create_app(adapter=None)`` resolves via ``dispatch.get_default_adapter``.

    This guards the wiring: the sub-app must call dispatch (not import the
    in-memory adapter directly) so ``LOUKE_OPENCODE_BACKEND=real`` is honored.
    """
    fake = _FakeRealAdapter()
    calls: list = []

    def _spy(*args, **kwargs):
        calls.append((args, kwargs))
        return fake

    monkeypatch.setattr(dispatch, "get_default_adapter", _spy)
    # Force the "real" path so dispatch is the authority.
    monkeypatch.setenv("LOUKE_OPENCODE_BACKEND", "real")
    monkeypatch.setenv("LOUKE_OPENCODE_BASE_URL", "http://test")

    client = TestClient(create_app())
    resp = client.get("/status")
    assert resp.status_code == 200
    assert resp.json()["adapter_kind"] == "real"
    assert len(calls) == 1
