"""FR-0201: user instruction intent routing e2e (story/spec_change/bug_fix/unknown)."""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from louke.intent_api import app


@pytest.fixture
def client():
    """TestClient for the intent_api sub-app (pure-rule classifier)."""
    return TestClient(app)


def test_story_intent_shows_choice_e2e(client):
    """AC-FR0201-01: story input returns choose_story_destination + requires_confirmation; never executed."""
    r = client.post("/api/intent/route", json={"input": "新做一个用户管理模块"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["intent"] == "story"
    assert body["proposed_action"] == "choose_story_destination"
    assert body["requires_confirmation"] is True
    assert body["executed"] is False


def test_spec_change_action_e2e(client):
    """AC-FR0201-02: spec change input selects spec_change action (not new dev, not fix)."""
    r = client.post("/api/intent/route", json={"input": "把 spec 改一下"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["intent"] == "spec_change"
    assert body["proposed_action"] == "spec_change"


def test_bug_fix_action_e2e(client):
    """AC-FR0201-03: bug fix input selects fix action (not new dev, not spec change)."""
    r = client.post("/api/intent/route", json={"input": "fix the login bug"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["intent"] == "bug_fix"
    assert body["proposed_action"] == "fix"


def test_unknown_input_clarifies_no_side_effect_e2e(client):
    """AC-FR0201-04: unknown input returns clarify and never executes; clarification question is non-empty."""
    r = client.post("/api/intent/route", json={"input": "asdfqwer 今天天气真好"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["intent"] == "unknown"
    assert body["proposed_action"] == "clarify"
    assert body["executed"] is False
    assert body["clarification_question"]
    # Even with explicit confirmation, unknown intent must not execute
    r2 = client.post("/api/intent/route",
                     json={"input": "asdfqwer", "confirmation": True})
    assert r2.json()["executed"] is False
    assert r2.json()["proposed_action"] == "clarify"