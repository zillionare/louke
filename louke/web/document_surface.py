"""Document surface: read-only story artifact access.

AC-FR1401-01

Opens the latest ``story.md`` bound to a Project/spec/revision,
preserving a return link to Project Status.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def story_artifact(
    *,
    workspace_root: str | Path,
    spec_id: str,
    revision: str | None = None,
) -> dict[str, Any] | None:
    """Return the latest story artifact for the given spec.

    Args:
        workspace_root: Workspace root containing ``.louke/``.
        spec_id: The spec id.
        revision: Optional specific revision; latest if omitted.

    Returns:
        A dict with ``spec_id``, ``revision``, ``content``, and
        ``return_url``. ``None`` if no story exists.
    """
    story_path = (
        Path(workspace_root) / ".louke" / "project" / "specs" / spec_id / "story.md"
    )
    if not story_path.exists():
        return None
    return {
        "spec_id": spec_id,
        "revision": revision or "latest",
        "content": story_path.read_text(encoding="utf-8"),
        "return_url": "/workbench?activity=projects",
    }
