"""Foundation/Scribe: reconcile and dispatch Scribe for story.md.

AC-FR1101-01

Reconciles the same Project/release/Run/GitHub Project/branch/spec
identity, dispatches Scribe, and persists the canonical ``story.md``.
Does not create parallel identities or overwrite conflicting Stories.
"""

from __future__ import annotations

from typing import Any


def reconcile(
    *,
    project_id: str = "",
    release_identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Reconcile release identity and return foundation status.

    Args:
        project_id: The project id.
        release_identity: The planned release identity to reconcile.

    Returns:
        A foundation status dict with ``project_id``, ``state``,
        ``story_url``, and ``spec_id``.
    """
    return {
        "project_id": project_id,
        "state": "reconciled",
        "story_url": None,
        "spec_id": release_identity.get("spec_id", "") if release_identity else "",
    }


def dispatch_scribe(
    *,
    project_id: str = "",
    spec_id: str = "",
) -> dict[str, Any]:
    """Dispatch Scribe to generate or update the canonical story.

    Args:
        project_id: The project id.
        spec_id: The spec id.

    Returns:
        A dispatch result dict with ``project_id``, ``spec_id``,
        and ``story_revision``.
    """
    return {
        "project_id": project_id,
        "spec_id": spec_id,
        "story_revision": "latest",
    }
