"""Environment Gate: on-demand environment check for New Project.

AC-FR0601-01, AC-FR0701-01, AC-FR0801-01

Only triggered by the ``New Project`` action. Checks ``gh`` executable,
auth scopes, repository binding, and canonical main in fixed order.
Does not modify authentication, install ``gh``, or auto-create repos.
"""

from __future__ import annotations

from typing import Any

REQUIRED_SCOPES: tuple[str, ...] = ("gist", "project", "repo", "workflow")

STEP_GH_EXECUTABLE = "gh_executable"
STEP_GH_AUTH_SCOPES = "gh_auth_scopes"
STEP_REPOSITORY_BINDING = "repository_binding"
STEP_CANONICAL_MAIN = "canonical_main"

CANONICAL_STEPS: tuple[str, ...] = (
    STEP_GH_EXECUTABLE,
    STEP_GH_AUTH_SCOPES,
    STEP_REPOSITORY_BINDING,
    STEP_CANONICAL_MAIN,
)


def start_check(
    *,
    workspace_id: str = "",
    expected_revision: int = 0,
) -> dict[str, Any]:
    """Start a new environment check.

    Args:
        workspace_id: The workspace id.
        expected_revision: The project context revision.

    Returns:
        An ``EnvironmentCheck`` dict with state ``running``.
    """
    return {
        "check_id": f"envchk_{workspace_id}",
        "revision": 1,
        "state": "running",
        "current_step": STEP_GH_EXECUTABLE,
        "steps": [
            {
                "id": step,
                "state": "pending",
                "observed": None,
                "missing": [],
                "diagnosis": None,
                "actions": [],
            }
            for step in CANONICAL_STEPS
        ],
        "observed_at": "",
        "fresh_until": "",
        "fingerprint": "",
        "story_input_enabled": False,
        "preview_enabled": False,
        "create_enabled": False,
        "guide_session_id": None,
    }
