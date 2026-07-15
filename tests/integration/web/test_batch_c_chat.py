"""AC coverage for the Batch C Chat workbench contract."""

from __future__ import annotations

from starlette.testclient import TestClient

from louke.web.app import create_app


def _html() -> str:
    return TestClient(create_app()).get("/workbench").text


def test_chat_agent_list_default_maestro() -> None:
    """AC-FR1305-01/02/03: Chat exposes 13 ordered, selectable agents."""
    html = _html()
    assert html.count("data-chat-agent=") == 13
    assert html.index('data-testid="chat-agent-maestro"') < html.index(
        'data-testid="chat-agent-archer"'
    )
    assert 'data-testid="chat-agent-maestro"' in html
    assert 'aria-selected="true"' in html


def test_chat_transcript_renders_input() -> None:
    """AC-FR1306-01/03: Chat renders an empty transcript and plain input."""
    html = _html()
    assert 'data-testid="chat-transcript"' in html
    assert 'data-testid="chat-transcript-maestro"' in html
    assert 'data-testid="chat-input"' in html
    assert 'data-testid="chat-submit"' in html
    assert 'placeholder="Type a message to Maestro..."' in html


def test_chat_submit_clears_input() -> None:
    """AC-FR1306-03: submit clears the input immediately."""
    html = _html()
    assert "input.value=''" in html or "input.value = ''" in html
    assert "submit" in html


def test_chat_agent_switch_isolates_transcript() -> None:
    """AC-FR1307-01/02: each agent owns a separate transcript element."""
    html = _html()
    assert 'data-testid="chat-transcript-maestro"' in html
    assert 'data-testid="chat-transcript-devon"' in html
    assert "transcripts[agent]" in html
    assert "activeAgent" in html


def test_chat_unknown_agent_falls_back_to_maestro() -> None:
    """AC-FR1307-04: unknown agent selection falls back with a visible toast."""
    html = _html()
    assert "未知 Agent:" in html
    assert "Maestro" in html
    assert "chat-agent-maestro" in html
