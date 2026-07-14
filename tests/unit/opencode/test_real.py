"""Unit tests for RealOpenCodeAdapter (FR-1401, B4 / B19).

These tests exercise the HTTP adapter against a mocked httpx.Client so they
do NOT require a running opencode serve. The L3 real smoke (B7 / B19)
covers the end-to-end path against a live server.

Discovered OpenCode HTTP API (v1.17.15, base URL http://127.0.0.1:{port}):
  POST   /api/session               -> {id, slug, ...}                create
  GET    /api/session                -> {data:[{id,...}], cursor}     list
  DELETE /api/session/{id}           -> true                          stop/end
  POST   /api/session/{id}/prompt   -> {data:{id,...}}              send
  POST   /api/session/{id}/abort    -> true                          cancel
  GET    /api/session/{id}/message   -> {data:[{id,type,content,...}], cursor}
  GET    /global/health              -> {healthy, version}           probe

B19 (issue #167) corrected the endpoints (``/api`` prefix, ``/prompt`` not
``/prompt_async``) and the response shapes (``{data: [...]}`` envelope,
message ``type`` + ``content[].text`` instead of ``info.role`` / ``parts``).
"""

from __future__ import annotations

import json
import os
import time
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
    """AC-FR1401-01: create() POSTs to /api/session and returns an Instance."""
    transport = _FakeTransport()
    transport.set("POST", "/api/session", status=200, json_body={
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
    assert any(r.url.path == "/api/session" for r in posts)


def test_create_sends_directory_and_model_body():
    """AC-FR1401-01: create() body has directory + model{providerID,id}."""
    transport = _FakeTransport()
    transport.set("POST", "/api/session", status=200, json_body={
        "id": "ses_x", "time": {"created": 1},
    })
    adapter = _make_adapter(transport)

    adapter.create(correlation_id="cid-1", model="opencode/big-pickle")

    post = next(r for r in transport.requests if r.method == "POST")
    body = json.loads(post.content.decode())
    assert body["directory"] == "/tmp"
    assert body["model"] == {"providerID": "opencode", "id": "big-pickle"}


def test_create_uses_opencode_model_env_when_no_arg(monkeypatch):
    """AC-FR1401-01: create() falls back to OPENCODE_MODEL env var."""
    monkeypatch.setenv("OPENCODE_MODEL", "anthropic/claude-3")
    transport = _FakeTransport()
    transport.set("POST", "/api/session", status=200, json_body={"id": "ses_x"})
    adapter = _make_adapter(transport)

    adapter.create(correlation_id="cid-1")

    post = next(r for r in transport.requests if r.method == "POST")
    body = json.loads(post.content.decode())
    assert body["model"] == {"providerID": "anthropic", "id": "claude-3"}


def test_create_defaults_to_free_model_when_no_model_or_env(monkeypatch):
    """AC-FR1401-01: create() defaults to opencode/big-pickle (free) model."""
    monkeypatch.delenv("OPENCODE_MODEL", raising=False)
    transport = _FakeTransport()
    transport.set("POST", "/api/session", status=200, json_body={"id": "ses_x"})
    adapter = _make_adapter(transport)

    adapter.create(correlation_id="cid-1")

    post = next(r for r in transport.requests if r.method == "POST")
    body = json.loads(post.content.decode())
    assert body["model"] == {"providerID": "opencode", "id": "big-pickle"}


def test_create_sends_correlation_id_header():
    """AC-FR1401-01: create() forwards correlation_id for tracing."""
    transport = _FakeTransport()
    transport.set("POST", "/api/session", status=200, json_body={"id": "ses_x"})
    adapter = _make_adapter(transport)

    adapter.create(correlation_id="trace-99")

    post = next(r for r in transport.requests if r.method == "POST")
    assert post.headers.get("x-correlation-id") == "trace-99"


def test_create_propagates_http_error_not_masked():
    """AC-FR1401-01: A 5xx from the server must surface as RuntimeError."""
    transport = _FakeTransport()
    transport.set("POST", "/api/session", status=500,
                  json_body={"error": "boom"})
    adapter = _make_adapter(transport)

    with pytest.raises(RuntimeError) as exc:
        adapter.create(correlation_id="cid")
    assert "500" in str(exc.value) or "boom" in str(exc.value).lower()


# -- list() ------------------------------------------------------------------


def test_list_issues_get_and_returns_instances():
    """AC-FR1401-01: list() GETs /api/session and parses the {data:[...]} envelope."""
    transport = _FakeTransport()
    transport.set("GET", "/api/session", status=200, json_body={
        "data": [
            {"id": "ses_a", "time": {"created": 1, "updated": 1}},
            {"id": "ses_b", "time": {"created": 2, "updated": 2}},
        ],
        "cursor": {"previous": None, "next": None},
    })
    adapter = _make_adapter(transport)

    instances = adapter.list()

    assert [i.id for i in instances] == ["ses_a", "ses_b"]
    gets = [r for r in transport.requests if r.method == "GET"]
    assert any(r.url.path == "/api/session" for r in gets)


# -- stop() ------------------------------------------------------------------


def test_stop_issues_delete_and_returns_stopped_instance():
    """AC-FR1401-01: stop() DELETEs /api/session/{id} and returns stopped."""
    transport = _FakeTransport()
    transport.set("DELETE", "/api/session/", status=200, json_body=True)
    adapter = _make_adapter(transport)

    inst = adapter.stop("ses_abc123")

    assert inst.id == "ses_abc123"
    assert inst.status == "stopped"
    deletes = [r for r in transport.requests if r.method == "DELETE"]
    assert len(deletes) == 1
    assert deletes[0].url.path == "/api/session/ses_abc123"


def test_stop_propagates_404():
    """AC-FR1401-01: stop() on a missing session surfaces the error."""
    transport = _FakeTransport()
    transport.set("DELETE", "/api/session/", status=404,
                  json_body={"error": "not found"})
    adapter = _make_adapter(transport)

    with pytest.raises(RuntimeError):
        adapter.stop("ses_missing")


# -- send_message() ----------------------------------------------------------


def test_send_message_issues_post_and_returns_message_and_true():
    """AC-FR1401-01: send_message() POSTs /api/session/{id}/prompt with {prompt:{text}}."""
    transport = _FakeTransport()
    transport.set("POST", "/prompt", status=200, json_body={
        "data": {"id": "msg_xyz", "type": "user"},
    })
    adapter = _make_adapter(transport)

    msg, accepted = adapter.send_message("ses_abc", "hello",
                                         correlation_id="cid-7")

    assert accepted is True
    assert msg.instance_id == "ses_abc"
    assert msg.role == "user"
    assert msg.kind == "message"
    assert msg.content == "hello"
    assert msg.id == "msg_xyz"
    posts = [r for r in transport.requests if r.method == "POST"
             and "/prompt" in r.url.path]
    assert len(posts) == 1
    body = json.loads(posts[0].content.decode())
    assert body == {"prompt": {"text": "hello"}}


def test_send_message_correlation_id_header():
    """AC-FR1401-01: send_message forwards correlation_id."""
    transport = _FakeTransport()
    transport.set("POST", "/prompt", status=200, json_body={"data": {"id": "m1"}})
    adapter = _make_adapter(transport)

    adapter.send_message("ses_abc", "hi", correlation_id="cid-7")

    post = next(r for r in transport.requests if r.method == "POST"
                and "/prompt" in r.url.path)
    assert post.headers.get("x-correlation-id") == "cid-7"


def test_send_message_propagates_4xx():
    """AC-FR1401-01: A 400 from /prompt must raise, not echo a fake reply."""
    transport = _FakeTransport()
    transport.set("POST", "/prompt", status=400,
                  json_body={"error": "bad prompt"})
    adapter = _make_adapter(transport)

    with pytest.raises(RuntimeError) as exc:
        adapter.send_message("ses_abc", "x", correlation_id="cid")
    assert "400" in str(exc.value) or "bad prompt" in str(exc.value).lower()


# -- list_messages() ---------------------------------------------------------


def test_list_messages_issues_get_and_returns_messages():
    """AC-FR1401-01: list_messages() GETs /api/session/{id}/message and parses {data:[...]}."""
    transport = _FakeTransport()
    transport.set("GET", "/message", status=200, json_body={
        "data": [
            {
                "id": "msg_1",
                "type": "user",
                "content": [{"type": "text", "id": "t0", "text": "hello"}],
                "time": {"created": 1784027703954},
            },
            {
                "id": "msg_2",
                "type": "assistant",
                "content": [{"type": "text", "id": "t1", "text": "hi there"}],
                "time": {"created": 1784027703960},
            },
        ],
        "cursor": {"previous": None, "next": None},
    })
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


def test_list_messages_concatenates_multiple_text_parts():
    """AC-FR1401-01: multiple text parts in content[] are concatenated."""
    transport = _FakeTransport()
    transport.set("GET", "/message", status=200, json_body={
        "data": [
            {
                "id": "msg_1",
                "type": "assistant",
                "content": [
                    {"type": "text", "text": "part-a "},
                    {"type": "tool_use", "name": "x"},
                    {"type": "text", "text": "part-b"},
                ],
            },
        ],
    })
    adapter = _make_adapter(transport)

    msgs = adapter.list_messages("ses_abc", after_message_id=None)

    assert len(msgs) == 1
    assert msgs[0].content == "part-a part-b"


def test_list_messages_after_filter_excludes_earlier():
    """AC-FR1401-01: after_message_id returns only messages after the cursor."""
    transport = _FakeTransport()
    transport.set("GET", "/message", status=200, json_body={
        "data": [
            {"id": "msg_1", "type": "user", "content": [{"type": "text", "text": "a"}]},
            {"id": "msg_2", "type": "assistant", "content": [{"type": "text", "text": "b"}]},
            {"id": "msg_3", "type": "assistant", "content": [{"type": "text", "text": "c"}]},
        ],
    })
    adapter = _make_adapter(transport)

    msgs = adapter.list_messages("ses_abc", after_message_id="msg_1")

    assert [m.id for m in msgs] == ["msg_2", "msg_3"]


def test_list_messages_propagates_5xx():
    """AC-FR1401-01: A 500 on messages must raise, not silently return []."""
    transport = _FakeTransport()
    transport.set("GET", "/message", status=500, json_body={"error": "db"})
    adapter = _make_adapter(transport)

    with pytest.raises(RuntimeError):
        adapter.list_messages("ses_abc", after_message_id=None)


# -- cancel() / abort --------------------------------------------------------


def test_cancel_issues_post_to_abort_endpoint():
    """AC-FR1401-01: cancel() POSTs /api/session/{id}/abort."""
    transport = _FakeTransport()
    transport.set("POST", "/abort", status=200, json_body=True)
    adapter = _make_adapter(transport)

    adapter.cancel("ses_abc", correlation_id="cid-1")

    aborts = [r for r in transport.requests if r.method == "POST"
              and "/abort" in r.url.path]
    assert len(aborts) == 1
    assert aborts[0].headers.get("x-correlation-id") == "cid-1"


def test_cancel_propagates_error():
    """AC-FR1401-01: A failed abort (non-404) must raise."""
    transport = _FakeTransport()
    transport.set("POST", "/abort", status=500, json_body={"error": "no"})
    adapter = _make_adapter(transport)

    with pytest.raises(RuntimeError):
        adapter.cancel("ses_abc", correlation_id="cid")


def test_cancel_falls_back_to_stop_on_404():
    """AC-FR1401-01: cancel() falls back to DELETE when abort returns 404."""
    transport = _FakeTransport()
    transport.set("POST", "/abort", status=404, json_body={"error": "no route"})
    transport.set("DELETE", "/api/session/", status=200, json_body=True)
    adapter = _make_adapter(transport)

    # Must NOT raise: 404 on abort triggers fallback to stop().
    adapter.cancel("ses_abc", correlation_id="cid")

    deletes = [r for r in transport.requests if r.method == "DELETE"]
    assert len(deletes) == 1
    assert deletes[0].url.path == "/api/session/ses_abc"


# -- version probe -----------------------------------------------------------


def test_version_probe_returns_health_payload():
    """AC-FR1401-02: probe_version() GETs /global/health."""
    transport = _FakeTransport()
    transport.set("GET", "/global/health", status=200,
                  json_body={"healthy": True, "version": "1.17.15"})
    adapter = _make_adapter(transport)

    info = adapter.probe_version()

    assert info["healthy"] is True
    assert info["version"] == "1.17.15"


# -- Live integration smoke (default-skipped) -------------------------------
# AC-FR1401-01 / AC-FR1401-02 (B19): honest live checks against a real
# `opencode serve`. To enable:
#   1. opencode serve --port 41234   (with a free model like big-pickle)
#   2. OPENCODE_INTEGRATION=1 OPENCODE_LIVE_BASE_URL=http://127.0.0.1:41234 \
#      pytest -m real_opencode tests/unit/opencode/test_real.py -v


@pytest.mark.real_opencode
@pytest.mark.skipif(
    not (
        os.environ.get("OPENCODE_INTEGRATION") == "1"
        and os.environ.get("OPENCODE_LIVE_BASE_URL")
    ),
    reason=(
        "Set OPENCODE_INTEGRATION=1 + OPENCODE_LIVE_BASE_URL to run live test"
    ),
)
def test_real_opencode_live_create_send_list_delete_with_free_model():
    """AC-FR1401-01: live opencode serve with opencode/big-pickle (free) responds.

    Skips by default. To enable:
      1. opencode serve --port 41234 (with default config exposing big-pickle)
      2. OPENCODE_INTEGRATION=1 OPENCODE_LIVE_BASE_URL=http://127.0.0.1:41234 \
         pytest -m real_opencode
    """
    import uuid

    base_url = os.environ["OPENCODE_LIVE_BASE_URL"]
    adapter = RealOpenCodeAdapter(base_url=base_url, timeout=30.0)
    marker = f"SMOKE_{uuid.uuid4().hex[:8]}"

    # create
    inst = adapter.create(correlation_id="l3-smoke")
    assert inst.id

    try:
        # send prompt
        msg, accepted = adapter.send_message(
            inst.id, f"please repeat: {marker}", correlation_id="l3-smoke"
        )
        assert accepted

        # poll for assistant reply
        deadline = time.time() + 60.0
        reply_found = False
        while time.time() < deadline:
            messages = adapter.list_messages(inst.id, after_message_id=None)
            for m in messages:
                if m.role == "assistant" and marker in m.content:
                    reply_found = True
                    break
            if reply_found:
                break
            time.sleep(2.0)
        assert reply_found, f"no assistant reply containing {marker!r}"
    finally:
        adapter.stop(inst.id)


@pytest.mark.real_opencode
@pytest.mark.skipif(
    not (
        os.environ.get("OPENCODE_INTEGRATION") == "1"
        and os.environ.get("OPENCODE_LIVE_BASE_URL")
    ),
    reason=(
        "Set OPENCODE_INTEGRATION=1 + OPENCODE_LIVE_BASE_URL to run live test"
    ),
)
def test_real_opencode_live_status_probe():
    """AC-FR1401-02: GET /global/health on live opencode returns healthy:true."""
    import httpx

    base_url = os.environ["OPENCODE_LIVE_BASE_URL"]
    r = httpx.get(f"{base_url}/global/health", timeout=5.0)
    assert r.status_code == 200
    body = r.json()
    assert body["healthy"] is True
