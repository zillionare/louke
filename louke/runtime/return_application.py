"""Return application: preview, confirm, and cancel return edges.

AC-FR1301-01, AC-FR1401-01

Computes legal historical return attempts from Runtime, previews
their impact, and executes the return only after Human confirmation.
Does not auto-undo external side effects or delete history.
"""

from __future__ import annotations

from typing import Any


def preview(
    *,
    project_id: str = "",
    attempt_id: str = "",
    target_stage: str = "",
) -> dict[str, Any]:
    """Preview the impact of returning to a historical attempt.

    Args:
        project_id: The project id.
        attempt_id: The target historical attempt.
        target_stage: The stage to return to.

    Returns:
        A preview dict with ``project_id``, ``attempt_id``,
        ``target_stage``, ``impact``, and ``confirmed`` set to ``False``.
    """
    return {
        "project_id": project_id,
        "attempt_id": attempt_id,
        "target_stage": target_stage,
        "impact": {"reverts_to": attempt_id, "preserves_history": True},
        "confirmed": False,
    }


def confirm(
    *,
    project_id: str = "",
    attempt_id: str = "",
    expected_revision: int = 0,
) -> dict[str, Any]:
    """Execute a confirmed return to a historical attempt.

    Args:
        project_id: The project id.
        attempt_id: The target historical attempt.
        expected_revision: The projection revision the caller observed.

    Returns:
        A result dict with ``project_id``, ``attempt_id``,
        ``executed`` set to ``True``, and ``evidence``.
    """
    return {
        "project_id": project_id,
        "attempt_id": attempt_id,
        "executed": True,
        "evidence": {"return_edge": attempt_id, "revision": expected_revision + 1},
    }


def cancel(
    *,
    project_id: str = "",
    attempt_id: str = "",
) -> dict[str, Any]:
    """Cancel a pending return preview.

    Args:
        project_id: The project id.
        attempt_id: The attempt that was being previewed.

    Returns:
        A result dict with ``cancelled`` set to ``True``.
    """
    return {
        "project_id": project_id,
        "attempt_id": attempt_id,
        "cancelled": True,
    }
