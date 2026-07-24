"""First-user creation and login recovery for Setup.

AC-FR0201-01, AC-FR0201-02

Provides the unique first-user command that creates the initial
human principal and advances the Setup manifest from
``pending_user`` to ``pending_model``. Login recovery allows an
existing first user to re-authenticate and continue Setup.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from louke.web.setup_state import (
    SetupStateError,
    SetupStatus,
    read_manifest,
    write_manifest,
)

STATUS_PENDING_USER = SetupStatus.PENDING_USER.value
STATUS_PENDING_MODEL = SetupStatus.PENDING_MODEL.value
STATUS_COMPLETE = SetupStatus.COMPLETE.value


def principal_id_for(name: str) -> str:
    """Return a stable local principal id derived from the username.

    Args:
        name: The username.

    Returns:
        A ``prin_`` prefixed hex string.
    """
    return f"prin_{hashlib.sha256(name.encode()).hexdigest()[:12]}"


def create_first_user(
    workspace_root: Path,
    *,
    workspace_id: str,
    name: str,
    credential: str,
    expected_revision: int,
    store: Any | None = None,
) -> dict[str, Any]:
    """Create the unique first user and advance Setup to ``pending_model``.

    Args:
        workspace_root: Workspace root containing ``.louke/``.
        workspace_id: Expected workspace id for manifest validation.
        name: The first user's display name.
        credential: The first user's credential (stored via scrypt).
        expected_revision: The manifest revision the caller observed.
        store: Optional ProjectStore for writing the user credential.
            If omitted, no credential is persisted.

    Returns:
        A dict with ``principal_id``, ``name``, ``setup_revision``,
        ``status``, and ``continue_url``.

    Raises:
        SetupStateMismatch: If ``expected_revision`` is stale.
        SetupStateError: If a first user already exists with a
            different identity.
    """
    manifest = read_manifest(workspace_root, workspace_id=workspace_id)
    if manifest.first_principal_id is not None:
        existing_id = principal_id_for(name)
        if manifest.first_principal_id == existing_id:
            return {
                "principal_id": manifest.first_principal_id,
                "name": name,
                "setup_revision": manifest.revision,
                "status": manifest.status.value,
                "continue_url": "/setup",
            }
        raise SetupStateError(
            f"first user already exists as {manifest.first_principal_id!r}"
        )
    principal_id = principal_id_for(name)
    if store is not None:
        store.add_user(name, credential)
    updated = manifest.advance_to_pending_model(
        first_principal_id=principal_id,
        expected_revision=expected_revision,
    )
    write_manifest(workspace_root, updated)
    return {
        "principal_id": principal_id,
        "name": name,
        "setup_revision": updated.revision,
        "status": updated.status.value,
        "continue_url": "/setup",
    }


def login_recovery(
    workspace_root: Path,
    *,
    workspace_id: str,
    name: str,
    credential: str,
    store: Any | None = None,
) -> dict[str, Any]:
    """Allow an existing first user to log in and continue Setup.

    Args:
        workspace_root: Workspace root containing ``.louke/``.
        workspace_id: Expected workspace id.
        name: The user's display name.
        credential: The user's credential.
        store: Optional ProjectStore for credential verification.

    Returns:
        A dict with ``principal_id``, ``setup_revision``, ``status``,
        and ``continue_url``.

    Raises:
        SetupStateError: If no first user exists or the manifest is
            already complete.
    """
    manifest = read_manifest(workspace_root, workspace_id=workspace_id)
    if manifest.first_principal_id is None:
        raise SetupStateError("no first user exists; use create_first_user")
    if manifest.status == SetupStatus.COMPLETE:
        raise SetupStateError("Setup is already complete")
    if store is not None:
        store.authenticate_user(name, credential)
    return {
        "principal_id": manifest.first_principal_id,
        "setup_revision": manifest.revision,
        "status": manifest.status.value,
        "continue_url": "/setup",
    }
