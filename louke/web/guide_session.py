"""Guide session: context-bound chat with Runtime status and advice.

AC-FR0501-01, AC-FR0501-02, AC-FR0501-03

The Guide session is bound to a Projects context (empty or project).
It records Runtime status messages first, then appends de-duplicated
Guide advice. Guide messages never carry Runtime action tokens.
"""

from __future__ import annotations

from typing import Any

AUTHORITY_RUNTIME = "runtime"
AUTHORITY_GUIDE = "guide"
AUTHORITY_HUMAN = "human"

KIND_RUNTIME_STATUS = "runtime_status"
KIND_GUIDE_ADVICE = "guide_advice"
KIND_GUIDE_ERROR = "guide_error"
KIND_USER = "user"
KIND_GUIDE_REPLY = "guide_reply"


def create_session(
    *,
    workspace_id: str = "",
    project_id: str | None = None,
    kind: str = "empty",
) -> dict[str, Any]:
    """Create a new Guide session bound to a context.

    Args:
        workspace_id: The workspace id.
        project_id: Optional project id for project-bound sessions.
        kind: ``empty`` or ``project``.

    Returns:
        A session dict with ``session_id``, ``context``, ``messages``,
        ``composer_enabled``, and ``owning_links``.
    """
    suffix = project_id if project_id else kind
    return {
        "session_id": f"guide_{workspace_id}_{suffix}",
        "context": {
            "workspace_id": workspace_id,
            "project_id": project_id,
            "runtime_revision": None,
            "kind": kind,
        },
        "messages": [],
        "composer_enabled": True,
        "owning_links": [],
    }
