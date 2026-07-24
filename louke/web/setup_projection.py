"""Setup projection: read-only view of the Setup manifest for UI/API.

AC-FR0101-01, AC-FR0301-01, AC-FR0301-02

Provides a stable read model that the Setup page, API, and gate
consume. The projection is derived from the persisted v2 manifest
and never mutates it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from louke.web.setup_state import MANIFEST_VERSION, SetupStatus, try_read_manifest

STATUS_PENDING_USER = SetupStatus.PENDING_USER.value
STATUS_PENDING_MODEL = SetupStatus.PENDING_MODEL.value
STATUS_COMPLETE = SetupStatus.COMPLETE.value
SCHEMA_VERSION = MANIFEST_VERSION


def read(
    workspace_root: str | Path,
    *,
    workspace_id: str = "",
    revision: int | None = None,
) -> dict[str, Any]:
    """Return the Setup projection for the given workspace.

    Args:
        workspace_root: Workspace root containing ``.louke/``.
        workspace_id: Expected workspace id (for validation).
        revision: If given, only return if the manifest revision matches.

    Returns:
        A dict with ``workspace_id``, ``revision``, ``status``,
        ``first_user``, ``model_check``, ``available_actions``,
        and ``continue_url``. Returns a default ``pending_user``
        projection when the manifest is missing.
    """
    manifest = try_read_manifest(Path(workspace_root))
    if manifest is None:
        return {
            "workspace_id": workspace_id,
            "revision": 0,
            "status": STATUS_PENDING_USER,
            "first_user": None,
            "model_check": None,
            "available_actions": ["create_first_user"],
            "continue_url": "/setup",
        }
    if revision is not None and manifest.revision != revision:
        return {
            "workspace_id": manifest.workspace_id,
            "revision": manifest.revision,
            "status": manifest.status.value,
            "first_user": None,
            "model_check": None,
            "available_actions": [],
            "continue_url": "/setup",
        }
    actions = _available_actions(manifest.status)
    continue_url = _continue_url(manifest.status)
    first_user = None
    if manifest.first_principal_id:
        first_user = {"principal_id": manifest.first_principal_id}
    return {
        "workspace_id": manifest.workspace_id,
        "revision": manifest.revision,
        "status": manifest.status.value,
        "first_user": first_user,
        "model_check": manifest.model_check.to_dict() if manifest.model_check else None,
        "available_actions": actions,
        "continue_url": continue_url,
    }


def _available_actions(status: SetupStatus) -> list[str]:
    """Return the list of available actions for the given status."""
    if status == SetupStatus.PENDING_USER:
        return ["create_first_user"]
    if status == SetupStatus.PENDING_MODEL:
        return ["start_model_check", "retry_model_check", "login"]
    return []


def _continue_url(status: SetupStatus) -> str:
    """Return the canonical continue URL for the given status."""
    if status == SetupStatus.COMPLETE:
        return "/workbench?activity=projects"
    return "/setup"
