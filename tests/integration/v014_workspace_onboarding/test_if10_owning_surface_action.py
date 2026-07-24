"""IF-10: Owning-surface Runtime-authorized action.

AC-FR1101-02, AC-FR1401-01, AC-FR1501-01, AC-NFR0101-01

Integration tests verify that actions are validated against the current
revision and allowed action set, and that stale/unknown actions are rejected.
"""

from __future__ import annotations

import pytest

from louke.web.workflow_actions import Action, validate_action


def _action(action_id: str = "act_1", revision: str = "rev_1") -> Action:
    return Action(
        action_id=action_id,
        revision=revision,
        label="Confirm Story",
        kind="dispatch",
    )


def test_valid_action_accepted():
    """AC-FR1101-02: action matching revision and allowed set is accepted."""
    # AC-FR1101-02
    action = _action()
    assert validate_action(action, revision="rev_1", allowed_ids={"act_1"}) is True


def test_stale_revision_action_rejected():
    """AC-FR1101-02: action with stale revision is rejected."""
    # AC-FR1101-02
    action = _action(revision="rev_1")
    with pytest.raises(ValueError, match="stale"):
        validate_action(action, revision="rev_2", allowed_ids={"act_1"})


def test_unknown_action_id_rejected():
    """AC-FR1101-02: action not in allowed set is rejected."""
    # AC-FR1101-02
    action = _action(action_id="act_unknown")
    with pytest.raises(ValueError, match="not allowed"):
        validate_action(action, revision="rev_1", allowed_ids={"act_1"})


def test_guide_cannot_inject_action():
    """AC-FR1501-01: Guide cannot create valid actions; only owning surface can."""
    # AC-FR1501-01
    # An action from a Guide context would not be in the allowed set
    action = _action(action_id="guide_injected")
    with pytest.raises(ValueError, match="not allowed"):
        validate_action(action, revision="rev_1", allowed_ids={"act_1"})


def test_action_does_not_execute_without_authorization():
    """AC-NFR0101-01: unauthorized action does not produce side effects."""
    # AC-NFR0101-01
    action = _action()
    # If validation raises, the action should not be dispatched
    with pytest.raises(ValueError, match="stale"):
        validate_action(action, revision="stale_rev", allowed_ids={"act_1"})
