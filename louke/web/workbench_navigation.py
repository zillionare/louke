"""Stable same-origin Workbench context URL construction."""

from __future__ import annotations

from urllib.parse import quote


def build_context_url(
    project_id: str, *, story_id: str | None = None, run_id: str | None = None
) -> str:
    """Build an encoded Project/Story/Run deep link.

    Raises:
        ValueError: If the required project identity is empty.
    """
    project = str(project_id).strip()
    if not project:
        raise ValueError("project identity is required")
    url = f"/projects/{quote(project, safe='')}"
    if story_id is not None:
        url += f"/stories/{quote(_required(story_id, 'story'), safe='')}"
    if run_id is not None:
        url += f"/runs/{quote(_required(run_id, 'run'), safe='')}"
    return url


def _required(value: str, label: str) -> str:
    """Normalize one optional-but-present URL identity."""
    clean = str(value).strip()
    if not clean:
        raise ValueError(f"{label} identity is required")
    return clean
