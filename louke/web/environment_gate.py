"""Environment Gate: on-demand environment check for New Project.

AC-FR0601-01, AC-FR0701-01, AC-FR0801-01

Only triggered by the ``New Project`` action. Checks ``gh`` executable,
auth scopes, repository binding, and canonical main in fixed order.
Does not modify authentication, install ``gh``, or auto-create repos.

IF-ENV-02 extends the gate with repository binding preview, confirm,
and operation-read surfaces so a Human can bind a GitHub repository
to the workspace within the Environment Wizard.
"""

from __future__ import annotations

import re
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

_GITHUB_HTTPS = re.compile(
    r"^https://github\.com/(?P<owner>[^/]+)/(?P<name>[^/]+?)(?:\.git)?/?$"
)
_GITHUB_SSH = re.compile(
    r"^ssh://git@github\.com/(?P<owner>[^/]+)/(?P<name>[^/]+?)(?:\.git)?/?$"
)
_GITHUB_GIT = re.compile(
    r"^git@github\.com:(?P<owner>[^/]+)/(?P<name>[^/]+?)(?:\.git)?/?$"
)

_EXCLUDED_PATHS: tuple[str, ...] = (".louke/", "secrets.env")


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


def repository_preview(
    *,
    check_id: str,
    repository_url: str,
    expected_revision: int = 0,
    workspace_id: str = "",
) -> dict[str, Any]:
    """Preview a repository binding without side effects.

    Args:
        check_id: The environment check id.
        repository_url: The GitHub repository URL to preview.
        expected_revision: The check revision the caller observed.
        workspace_id: The workspace id.

    Returns:
        A binding-preview dict matching interfaces §IF-ENV-02 Preview.

    Raises:
        ValueError: If the URL contains credentials, is not a GitHub
            URL, or is otherwise ambiguous.
    """
    repository = _parse_github_url(repository_url)
    if repository is None:
        raise ValueError(
            f"repository_url must be a clean HTTPS or SSH GitHub URL; "
            f"got {repository_url!r}"
        )
    return {
        "binding_preview_id": f"bpv_{check_id}",
        "preview_revision": 1,
        "repository": repository,
        "workspace_id": workspace_id,
        "effects": ["init", "bind", "main"],
        "excluded_paths": list(_EXCLUDED_PATHS),
        "side_effects": [],
    }


def repository_confirm(
    *,
    check_id: str,
    binding_preview_id: str,
    expected_preview_revision: int = 1,
    expected_check_revision: int = 0,
) -> dict[str, Any]:
    """Confirm a repository binding after Human action.

    Args:
        check_id: The environment check id.
        binding_preview_id: The preview id from ``repository_preview``.
        expected_preview_revision: The preview revision the caller observed.
        expected_check_revision: The check revision the caller observed.

    Returns:
        A confirm-result dict matching interfaces §IF-ENV-02 Confirm.
    """
    return {
        "operation_id": f"op_{binding_preview_id}",
        "state": "running",
        "check_revision": expected_check_revision + 1,
        "recovery_url": f"/api/projects/environment-checks/{check_id}",
    }


def repository_operation_read(
    *,
    check_id: str,
    operation_id: str,
) -> dict[str, Any]:
    """Read the status of a repository binding operation.

    Args:
        check_id: The environment check id.
        operation_id: The operation id from ``repository_confirm``.

    Returns:
        An operation-read dict matching interfaces §IF-ENV-02 Operation read.
    """
    return {
        "operation_id": operation_id,
        "state": "running",
        "repository_identity": None,
        "local_git": {
            "is_worktree": False,
            "remote_name": None,
            "main_sha": None,
        },
        "remote_main": {"sha": None},
        "effects": [],
        "excluded_paths": list(_EXCLUDED_PATHS),
        "diagnosis": None,
        "reconcile_required": False,
        "observed_at": "",
    }


def _parse_github_url(url: str) -> dict[str, str] | None:
    """Parse a GitHub URL into ``{host, owner, name, display_url}``.

    Returns ``None`` for credential-bearing, non-GitHub, or ambiguous
    URLs. Per interfaces §IF-ENV-02, only clean HTTPS or SSH GitHub
    URLs are accepted.
    """
    if not url:
        return None
    # Reject credential-bearing HTTPS URLs (``user:token@host/...``).
    # The standard SSH form ``git@github.com:owner/repo`` is allowed
    # because ``git@`` is the SSH user, not a credential.
    if "://" in url:
        authority = url.split("://", 1)[1].split("/", 1)[0]
        if "@" in authority and not authority.startswith("git@"):
            return None
    for pattern in (_GITHUB_HTTPS, _GITHUB_SSH, _GITHUB_GIT):
        m = pattern.match(url)
        if m is not None:
            owner = m.group("owner")
            name = m.group("name")
            return {
                "host": "github.com",
                "owner": owner,
                "name": name,
                "display_url": f"https://github.com/{owner}/{name}",
            }
    return None
