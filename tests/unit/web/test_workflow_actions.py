"""Unit contracts for Runtime-authorized action validation."""

from __future__ import annotations

import pytest

from louke.web.workflow_actions import Action, validate_action


def test_action_requires_current_revision_and_runtime_allowed_id() -> None:
    """AC-FR1101-02: stale or unknown actions cannot dispatch."""
    action = Action("recheck", "status_2", "Recheck", "navigate")

    assert validate_action(action, revision="status_2", allowed_ids={"recheck"})
    with pytest.raises(ValueError, match="stale"):
        validate_action(action, revision="status_1", allowed_ids={"recheck"})
    with pytest.raises(ValueError, match="not allowed"):
        validate_action(action, revision="status_2", allowed_ids=set())
