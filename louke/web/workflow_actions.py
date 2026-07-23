"""Revision and permission checks for owning-surface workflow actions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Action:
    """Opaque Runtime action presented by an owning surface."""

    action_id: str
    revision: str
    label: str
    kind: str


def validate_action(action: Action, *, revision: str, allowed_ids: set[str]) -> bool:
    """Validate an action against the current Runtime projection.

    Raises:
        ValueError: If the projection revision is stale or the action is not
            currently authorized by Runtime.
    """
    if action.revision != revision:
        raise ValueError("stale workflow action revision")
    if action.action_id not in allowed_ids:
        raise ValueError("workflow action is not allowed")
    return True
