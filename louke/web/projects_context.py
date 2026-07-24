"""Projects context: read model for the Workbench Projects activity.

AC-FR0401-01

Resolves to exactly one of three states: ``empty``, ``active``, or
``conflict``. The resolution is based on persisted Release/Project/Run
bindings, never on list order, recent access, or Guide suggestions.
"""

from __future__ import annotations

from typing import Any

STATE_EMPTY = "empty"
STATE_ACTIVE = "active"
STATE_CONFLICT = "conflict"


def resolve(
    *,
    workspace_id: str = "",
    bindings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Resolve the current Projects context.

    Args:
        workspace_id: The workspace id.
        bindings: Persisted project bindings (from Fact Stores).

    Returns:
        A dict with ``workspace_id``, ``state``, ``project``, ``conflicts``,
        ``primary_action``, and ``guide_session_id``.
    """
    if not bindings:
        return {
            "workspace_id": workspace_id,
            "state": STATE_EMPTY,
            "project": None,
            "conflicts": [],
            "primary_action": {
                "kind": "new_project",
                "href": "/workbench?activity=projects&action=new_project",
                "enabled": True,
                "reason": "no_active_project",
            },
            "guide_session_id": None,
        }
    if len(bindings) == 1:
        return {
            "workspace_id": workspace_id,
            "state": STATE_ACTIVE,
            "project": bindings[0],
            "conflicts": [],
            "primary_action": None,
            "guide_session_id": None,
        }
    return {
        "workspace_id": workspace_id,
        "state": STATE_CONFLICT,
        "project": None,
        "conflicts": bindings,
        "primary_action": {
            "kind": "new_project",
            "href": "",
            "enabled": False,
            "reason": "conflict_requires_resolution",
        },
        "guide_session_id": None,
    }
