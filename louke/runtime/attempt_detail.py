"""Attempt detail: read-only view of a workflow attempt.

AC-FR1301-01

Provides stage progress, responsible party, evidence, and legal
actions for a specific attempt within a project timeline.
"""

from __future__ import annotations

from typing import Any


def attempt_detail(
    *,
    project_id: str = "",
    attempt_id: str = "",
    stage: str = "",
    owner: str | None = None,
    elapsed_seconds: int = 0,
    evidence: list[dict[str, Any]] | None = None,
    actions: list[str] | None = None,
) -> dict[str, Any]:
    """Return the detail projection for a single attempt.

    Args:
        project_id: The project id.
        attempt_id: The attempt id.
        stage: The canonical stage name.
        owner: The agent or human responsible for this attempt.
        elapsed_seconds: Wall-clock seconds since attempt start.
        evidence: List of evidence artifacts.
        actions: List of legal action names.

    Returns:
        A dict with ``project_id``, ``attempt_id``, ``stage``,
        ``owner``, ``elapsed_seconds``, ``evidence``, and ``actions``.
    """
    return {
        "project_id": project_id,
        "attempt_id": attempt_id,
        "stage": stage,
        "owner": owner,
        "elapsed_seconds": elapsed_seconds,
        "evidence": evidence or [],
        "actions": actions or [],
    }
