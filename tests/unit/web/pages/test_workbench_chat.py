"""Unit contract tests for the Workbench Chat client behavior."""

from __future__ import annotations

from starlette.testclient import TestClient

from louke.web.app import create_app


def test_chat_delta_registers_message_id_before_transcript_refresh() -> None:
    """An SSE-rendered assistant id must be known to refresh deduplication."""
    response = TestClient(create_app()).get("/workbench")

    assert response.status_code == 200
    html = response.text
    add_start = html.index("function addChatMessage")
    start = html.index("function appendChatDelta")
    end = html.index("function connectChatStream", start)
    add_message = html[add_start:start]
    append_delta = html[start:end]

    assert "renderedMessages[agent].has(id)" in add_message
    assert "renderedMessages[agent].add(id)" in add_message
    assert "renderedMessages[agent]??=new Set()" in append_delta
    assert "renderedMessages[agent].add(event.message_id)" in append_delta
    assert append_delta.index("item.textContent") < append_delta.index(
        "renderedMessages[agent].add"
    )


def test_chat_uses_normalized_agent_ids_and_inflight_submit_guard() -> None:
    """Chat setup targets the selected Agent and admits one in-flight submit."""
    response = TestClient(create_app()).get("/workbench")

    assert response.status_code == 200
    html = response.text
    assert 'data-chat-agent="devon"' in html
    assert 'data-testid="chat-transcript-devon"' in html
    session_start = html.index("async function chatSession")
    session_end = html.index("async function refreshChat", session_start)
    chat_session = html[session_start:session_end]
    assert "body:JSON.stringify({agent})" in chat_session
    send_start = html.index("async function sendChat")
    send_end = html.index('document.querySelector(\'[data-testid="chat-form"]')
    send_chat = html[send_start:send_end]
    assert "chatSubmissions[agent]" in send_chat
