"""Browser-local New Project draft storage.

AC-FR0901-01, AC-FR0901-02

The draft key follows the contract shape
``louke.new-project.v1:<workspace_id>:<principal_id>`` so browser
storage scoping is enforceable per-browser / per-principal. The
payload is limited to the allowed fields and MUST NOT carry
credential / token / repository URL / preview id / project identity.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

_DRAFT_PREFIX = "louke.new-project.v1"


def draft_key(
    *,
    workspace_id: str,
    principal_id: str,
) -> str:
    """Return the browser-storage key for the given workspace and principal.

    Args:
        workspace_id: The workspace id.
        principal_id: The principal id of the user creating the draft.

    Returns:
        ``louke.new-project.v1:<workspace_id>:<principal_id>``.
    """
    return f"{_DRAFT_PREFIX}:{workspace_id}:{principal_id}"


def create_draft(
    *,
    workspace_id: str,
    principal_id: str,
    story: str = "",
    release_version: str = "",
    resume_step: str = "input",
) -> dict[str, Any]:
    """Create a new release request draft payload.

    Args:
        workspace_id: The workspace id.
        principal_id: The principal id.
        story: Story input text.
        release_version: Release version string.
        resume_step: ``input`` or ``preview``.

    Returns:
        A draft dict with ``version``, ``story``, ``release_version``,
        ``resume_step``, and ``saved_at``. Never includes credentials,
        tokens, repository URLs, preview ids, or project identity.
    """
    if resume_step not in ("input", "preview"):
        resume_step = "input"
    return {
        "version": 1,
        "story": story,
        "release_version": release_version,
        "resume_step": resume_step,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
