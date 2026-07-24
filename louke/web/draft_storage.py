"""Draft storage: workspace-bound draft key for release requests.

AC-FR0901-01, AC-FR0901-02

The draft key binds a planned release identity to the workspace and
principal. Drafts never include credentials or Story content.
"""

from __future__ import annotations

import hashlib
from typing import Any


def draft_key(
    *,
    workspace_id: str,
    principal_id: str,
) -> str:
    """Return a stable draft key for the given workspace and principal.

    Args:
        workspace_id: The workspace id.
        principal_id: The principal id of the user creating the draft.

    Returns:
        A ``draft_`` prefixed hex string.
    """
    raw = f"{workspace_id}:{principal_id}"
    return f"draft_{hashlib.sha256(raw.encode()).hexdigest()[:16]}"


def create_draft(
    *,
    workspace_id: str,
    principal_id: str,
    story_input: str = "",
) -> dict[str, Any]:
    """Create a new release request draft.

    Args:
        workspace_id: The workspace id.
        principal_id: The principal id.
        story_input: Optional story input text.

    Returns:
        A draft dict with ``key``, ``workspace_id``, ``principal_id``,
        and ``story_input``. Never includes credentials.
    """
    return {
        "key": draft_key(workspace_id=workspace_id, principal_id=principal_id),
        "workspace_id": workspace_id,
        "principal_id": principal_id,
        "story_input": story_input,
    }
