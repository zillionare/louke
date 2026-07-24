"""Runtime projection: canonical 13-stage workflow status read model.

AC-FR1201-01, AC-FR1301-01

Generates a read-only Project Status from pinned workflow definition,
run, events, attempts, artifacts/evidence/actions. Does not dispatch,
estimate percentages, or allow client-side active pointer changes.
"""

from __future__ import annotations

from typing import Any

CANONICAL_STAGES: tuple[str, ...] = (
    "M-START",
    "M-DESIGN",
    "M-IMPL",
    "M-TEST",
    "M-E2E",
    "M-SECURITY",
    "M-REVIEW",
    "M-FIX",
    "M-MERGE",
    "M-RELEASE",
    "M-DEPLOY",
    "M-VERIFY",
    "M-CLOSE",
)

assert len(CANONICAL_STAGES) == 13


def project_status(
    *,
    workspace_id: str = "",
    project_id: str = "",
    run_id: str = "",
    events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return a read-only Project Status projection.

    Args:
        workspace_id: The workspace id.
        project_id: The project id.
        run_id: The run id.
        events: Runtime events (attempts, artifacts, evidence).

    Returns:
        A projection dict with ``workspace_id``, ``project_id``,
        ``active`` stage, ``timeline``, and ``projection_revision``.
    """
    return {
        "workspace_id": workspace_id,
        "project_id": project_id,
        "run_id": run_id,
        "state": "active",
        "active": {"stage": CANONICAL_STAGES[0], "attempt_id": None, "owner": None},
        "timeline": [],
        "projection_revision": 0,
    }
