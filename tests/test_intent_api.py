"""FR-0201: 用户指令意图分类与路由契约测试.

本模块是纯规则/关键词分类, 不用 LLM, 不真触发 Backlog/Maestro。
所有 `executed` 必须为 False, `execution_id` 必须为 None (本期契约)。
"""

import pytest
from starlette.testclient import TestClient

from louke.intent_api import app


@pytest.fixture
def client():
    return TestClient(app)


def test_route_story_intent_requires_choice(client):
    """AC-FR0201-01: story 输入必须返回 choose_story_destination 且需用户选择。"""
    r = client.post("/api/intent/route", json={"input": "新做一个用户登录页"})
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "story"
    assert body["proposed_action"] == "choose_story_destination"
    assert body["requires_confirmation"] is True
    assert body["executed"] is False
    assert body["execution_id"] is None
    q = body.get("clarification_question") or ""
    assert "立即" in q or "开发" in q
    assert "backlog" in q.lower() or "存" in q


def test_route_story_with_start_development_selection_clarifies(client):
    """AC-FR0201-01 续: selection=start_development 后 proposed_action 变为 start_development, 但仍不执行。"""
    r = client.post(
        "/api/intent/route",
        json={
            "input": "开发一个 dashboard",
            "selection": "start_development",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "story"
    assert body["proposed_action"] == "start_development"
    assert body["executed"] is False
    assert body["execution_id"] is None


def test_route_spec_change_intent(client):
    """AC-FR0201-02: spec change 输入返回 spec_change 动作。"""
    r = client.post("/api/intent/route", json={"input": "把 AC-FR0201-01 改一下"})
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "spec_change"
    assert body["proposed_action"] == "spec_change"
    assert body["requires_confirmation"] is True
    assert body["executed"] is False


def test_route_bug_fix_intent(client):
    """AC-FR0201-03: bug fix 输入返回 fix 动作。"""
    r = client.post("/api/intent/route", json={"input": "登录页报错了, fix this"})
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "bug_fix"
    assert body["proposed_action"] == "fix"
    assert body["requires_confirmation"] is True
    assert body["executed"] is False


def test_route_unknown_input_returns_clarify(client):
    """AC-FR0201-04: 未识别输入返回 unknown + clarify, 且不执行。"""
    r = client.post("/api/intent/route", json={"input": "asdfqwer"})
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "unknown"
    assert body["proposed_action"] == "clarify"
    assert body["requires_confirmation"] is True
    assert body["executed"] is False
    assert body["execution_id"] is None
    q = body.get("clarification_question") or ""
    assert "新功能" in q or "story" in q.lower()


def test_route_with_confirmation_unknown_keeps_clarify(client):
    """AC-FR0201-04 续: 即使 confirmation=true, unknown 也不执行。"""
    r = client.post(
        "/api/intent/route",
        json={
            "input": "今天天气真好",
            "confirmation": True,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "unknown"
    assert body["proposed_action"] == "clarify"
    assert body["executed"] is False
    assert body["execution_id"] is None


def test_route_low_confidence_story_with_high_signal_returns_story(client):
    """补充: 高信号 story 词 (实现 XXX) 应当 confidence >= 0.7。"""
    r = client.post(
        "/api/intent/route", json={"input": "实现一个用户登录的 OAuth 集成"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "story"
    assert body["confidence"] >= 0.7


def test_route_validation_error_missing_input(client):
    """POST body 缺 input 字段返回 400 VALIDATION_ERROR。"""
    r = client.post("/api/intent/route", json={})
    assert r.status_code == 400
    body = r.json()
    assert body["error_code"] == "VALIDATION_ERROR"
