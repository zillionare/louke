"""Unit tests for RealOpenCodeAdapter (FR-1401, B4).

These tests exercise the HTTP adapter against a mocked httpx.Client so they
do NOT require a running opencode serve. The L3 real smoke (B7) covers the
end-to-end path.

Discovered OpenCode HTTP API (v1.17.15, base URL http://127.0.0.1:{port}):
  POST   /session                         -> {id, slug, ...}            create
  GET    /session                          -> [{id, ...}]               list
  GET    /session/{id}                     -> {id, ...} | 404           get
  DELETE /session/{id}                     -> true                      stop/end
  POST   /session/{id}/prompt_async        -> 204 (async)              send
  POST   /session/{id}/abort               -> true                      cancel
  GET    /session/{id}/message?limit=N     -> [{info, parts}]           messages
  GET    /global/health                    -> {healthy, version}        probe
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from louke.opencode.real import RealOpenCodeAdapter


# -- Fakes --------------------------------------------------------------------


class _FakeTransport:
    """Records requests and returns canned httpx.Response objects."""

    def __init__(self, routes: dict[tuple[str, str], dict[str, Any]] | None = None):
        self._routes = routes or {}
        self.requests: list[httpx.Request] = []

    def set(self, method: str, path_substr: str, *, status: int, json_body: Any = None,
            text: str | None = None) -> None:
        self._routes[(method.upper(), path_substr)] = {
            "status": status, "json": json_body, "text": text,
        }

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        for (method, path_substr), resp in self._routes.items():
            if request.method.upper() != method:
                continue
            if path_substr in request.url.path or path_substr in str(request.url):
                status = resp["status"]
                if resp["json"] is not None:
                    return httpx.Response(status, json=resp["json"],
                                          request=request)
                return httpx.Response(status, text=resp["text"] or "",
                                       request=request)
        return httpx.Response(404, json={"error": "no route"},
                              request=request)


def _make_adapter(transport: _FakeTransport) -> RealOpenCodeAdapter:
    client = httpx.Client(transport=httpx.MockTransport(transport))
    return RealOpenCodeAdapter("http://127.0.0.1:41234", client=client, timeout=2.0)


# -- create() ----------------------------------------------------------------


def test_create_issues_post_and_returns_instance():
    """create() POSTs to /session and returns an Instance with the server id."""
    transport = _FakeTransport()
    transport.set("POST", "/session", status=200, json_body={
        "id": "ses_abc123",
        "slug": "calm-garden",
        "title": "New session",
        "version": "1.17.15",
        "time": {"created": 1784027703954, "updated": 1784027703954},
    })
    adapter = _make_adapter(transport)

    inst = adapter.create(correlation_id="cid-1")

    assert inst.id == "ses_abc123"
    assert inst.status == "running"
    # Confirm the POST actually happened with the right method + path.
    posts = [r for r in transport.requests if r.method == "POST"]
    assert any(r.url.path == "/session" for r in posts)


def test_create_sends_correlation_id_header():
    """create() forwards correlation_id so the server can trace the request."""
    transport = _FakeTransport()
    transport.set("POST", "/session", status=200, json_body={"id": "ses_x"})
    adapter = _make_adapter(transport)

    adapter.create(correlation_id="trace-99")

    post = next(r for r in transport.requests if r.method == "POST")
    assert post.headers.get("x-correlation-id") == "trace-99"


def test_create_propagates_http_error_not_masked():
    """A 5xx from the server must surface as RuntimeError, not silently echo."""
    transport = _FakeTransport()
    transport.set("POST", "/session", status=500,
                  json_body={"error": "boom"})
    adapter = _make_adapter(transport)

    with pytest.raises(RuntimeError) as exc:
        adapter.create(correlation_id="cid")
    assert "500" in str(exc.value) or "boom" in str(exc.value).lower()


# -- list() ------------------------------------------------------------------


def test_list_issues_get_and_returns_instances():
    """list() GETs /session and returns Instance objects."""
    transport = _FakeTransport()
    transport.set("GET", "/session", status=200, json_body=[
        {"id": "ses_a", "time": {"created": 1, "updated": 1}},
        {"id": "ses_b", "time": {"created": 2, "updated": 2}},
    ])
    adapter = _make_adapter(transport)

    instances = adapter.list()

    assert [i.id for i in instances] == ["ses_a", "ses_b"]
    gets = [r for r in transport.requests if r.method == "GET"]
    assert any(r.url.path == "/session" for r in gets)


# -- stop() ------------------------------------------------------------------


def test_stop_issues_delete_and_returns_stopped_instance():
    """stop() DELETEs /session/{id} and returns a stopped Instance."""
    transport = _FakeTransport()
    transport.set("DELETE", "/session/", status=200, json_body=True)
    adapter = _make_adapter(transport)

    inst = adapter.stop("ses_abc123")

    assert inst.id == "ses_abc123"
    assert inst.status == "stopped"
    deletes = [r for r in transport.requests if r.method == "DELETE"]
    assert len(deletes) == 1
    assert deletes[0].url.path == "/session/ses_abc123"


def test_stop_propagates_404():
    """stop() on a missing session surfaces the error, not a silent stopped."""
    transport = _FakeTransport()
    transport.set("DELETE", "/session/", status=404, json_body={"error": "not found"})
    adapter = _make_adapter(transport)

    with pytest.raises(RuntimeError):
        adapter.stop("ses_missing")


# -- send_message() ----------------------------------------------------------


def test_send_message_issues_post_and_returns_message_and_true():
    """send_message() POSTs /session/{id}/prompt_async and returns (Message, True)."""
    transport = _FakeTransport()
    transport.set("POST", "/prompt_async", status=204)
    adapter = _make_adapter(transport)

    msg, accepted = adapter.send_message("ses_abc", "hello", correlation_id="cid-7")

    assert accepted is True
    assert msg.instance_id == "ses_abc"
    assert msg.role == "user"
    assert msg.kind == "message"
    assert msg.content == "hello"
    posts = [r for r in transport.requests if r.method == "POST"
             and "/prompt_async" in r.url.path]
    assert len(posts) == 1
    body = json.loads(posts[0].content.decode())
    assert body["parts"][0]["text"] == "hello"


def test_send_message_correlation_id_header():
    """send_message forwards correlation_id."""
    transport = _FakeTransport()
    transport.set("POST", "/prompt_async", status=204)
    adapter = _make_adapter(transport)

    adapter.send_message("ses_abc", "hi", correlation_id="cid-7")

    post = next(r for r in transport.requests if r.method == "POST"
                and "/prompt_async" in r.url.path)
    assert post.headers.get("x-correlation-id") == "cid-7"


def test_send_message_propagates_4xx():
    """A 400 from prompt_async must raise RuntimeError, not echo a fake reply."""
    transport = _FakeTransport()
    transport.set("POST", "/prompt_async", status=400,
                  json_body={"error": "bad parts"})
    adapter = _make_adapter(transport)

    with pytest.raises(RuntimeError) as exc:
        adapter.send_message("ses_abc", "x", correlation_id="cid")
    assert "400" in str(exc.value) or "bad parts" in str(exc.value).lower()


# -- list_messages() ---------------------------------------------------------


def test_list_messages_issues_get_and_returns_messages():
    """list_messages() GETs /session/{id}/message and parses info+parts."""
    transport = _FakeTransport()
    transport.set("GET", "/message", status=200, json_body=[
        {
            "info": {
                "id": "msg_1",
                "sessionID": "ses_abc",
                "role": "user",
                "time": {"created": 1784027703954},
            },
            "parts": [{"type": "text", "text": "hello"}],
        },
        {
            "info": {
                "id": "msg_2",
                "sessionID": "ses_abc",
                "role": "assistant",
                "time": {"created": 1784027703960},
            },
            "parts": [{"type": "text", "text": "hi there"}],
        },
    ])
    adapter = _make_adapter(transport)

    msgs = adapter.list_messages("ses_abc", after_message_id=None)

    assert len(msgs) == 2
    assert msgs[0].id == "msg_1"
    assert msgs[0].role == "user"
    assert msgs[0].content == "hello"
    assert msgs[1].id == "msg_2"
    assert msgs[1].role == "assistant"
    assert msgs[1].content == "hi there"
    gets = [r for r in transport.requests if r.method == "GET"
            and "/message" in r.url.path]
    assert len(gets) == 1


def test_list_messages_after_filter_excludes_earlier():
    """after_message_id returns only messages strictly after the cursor."""
    transport = _FakeTransport()
    transport.set("GET", "/message", status=200, json_body=[
        {"info": {"id": "msg_1", "role": "user"}, "parts": [{"text": "a"}]},
        {"info": {"id": "msg_2", "role": "assistant"}, "parts": [{"text": "b"}]},
        {"info": {"id": "msg_3", "role": "assistant"}, "parts": [{"text": "c"}]},
    ])
    adapter = _make_adapter(transport)

    msgs = adapter.list_messages("ses_abc", after_message_id="msg_1")

    assert [m.id for m in msgs] == ["msg_2", "msg_3"]


def test_list_messages_propagates_5xx():
    """A 500 on messages must raise, not silently return []."""
    transport = _FakeTransport()
    transport.set("GET", "/message", status=500, json_body={"error": "db"})
    adapter = _make_adapter(transport)

    with pytest.raises(RuntimeError):
        adapter.list_messages("ses_abc", after_message_id=None)


# -- cancel() / abort --------------------------------------------------------


def test_cancel_issues_post_to_abort_endpoint():
    """cancel() POSTs /session/{id}/abort to stop the current generation."""
    transport = _FakeTransport()
    transport.set("POST", "/abort", status=200, json_body=True)
    adapter = _make_adapter(transport)

    adapter.cancel("ses_abc", correlation_id="cid-1")

    aborts = [r for r in transport.requests if r.method == "POST"
              and "/abort" in r.url.path]
    assert len(aborts) == 1
    assert aborts[0].headers.get("x-correlation-id") == "cid-1"


def test_cancel_propagates_error():
    """A failed abort must raise, not silently report success."""
    transport = _FakeTransport()
    transport.set("POST", "/abort", status=500, json_body={"error": "no"})
    adapter = _make_adapter(transport)

    with pytest.raises(RuntimeError):
        adapter.cancel("ses_abc", correlation_id="cid")


# -- version probe -----------------------------------------------------------


def test_version_probe_returns_health_payload():
    """probe_version() GETs /global/health and returns the version string."""
    transport = _FakeTransport()
    transport.set("GET", "/global/health", status=200,
                  json_body={"healthy": True, "version": "1.17.15"})
    adapter = _make_adapter(transport)

    info = adapter.probe_version()

    assert info["healthy"] is True
    assert info["version"] == "1.17.15"
