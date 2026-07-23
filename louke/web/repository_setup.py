"""Pure repository selection and side-effect-free Setup preview rules."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


class RepositoryValidationError(ValueError):
    """Raised when a repository selection cannot be safely previewed."""


@dataclass(frozen=True)
class RepositorySelection:
    """Human repository choice for the current Setup revision."""

    mode: str
    remote_url: str | None


@dataclass(frozen=True)
class RepositoryPreview:
    """Read-only description of the repository operation to be confirmed."""

    mode: str
    display_remote: str | None
    summary: tuple[str, ...]
    workspace_config_modification_count: int = 0
    repository_resource_creation_count: int = 0


def build_repository_preview(
    selection: RepositorySelection, *, workspace: Path
) -> RepositoryPreview:
    """Build a repository preview without modifying the workspace.

    Args:
        selection: ``init`` or ``clone`` choice and optional remote.
        workspace: Target workspace path used only to describe its state.

    Returns:
        A side-effect-free :class:`RepositoryPreview`.

    Raises:
        RepositoryValidationError: If the mode, URL, or workspace is invalid.
    """
    if selection.mode not in {"init", "clone"}:
        raise RepositoryValidationError("repository mode must be init or clone")
    if not workspace.is_dir():
        raise RepositoryValidationError("workspace directory does not exist")
    display_remote = None
    if selection.mode == "clone":
        display_remote = _validate_remote(selection.remote_url)
    summary = ("initialize .git and preserve existing workspace files",)
    if selection.mode == "clone":
        summary = ("clone into same-filesystem staging", "bind remote after readback")
    return RepositoryPreview(
        mode=selection.mode,
        display_remote=display_remote,
        summary=summary,
    )


def _validate_remote(remote_url: str | None) -> str:
    """Validate and return a credential-free display form of a Git remote."""
    value = str(remote_url or "").strip()
    if not value or any(ord(char) < 32 for char in value):
        raise RepositoryValidationError(
            "clone remote is required and must be printable"
        )
    if value.startswith("/") or value.startswith("file:"):
        raise RepositoryValidationError("local clone paths are not allowed")
    parsed = urlsplit(value)
    if parsed.scheme in {"http", "https", "ssh"}:
        if parsed.username or parsed.password or not parsed.netloc:
            raise RepositoryValidationError(
                "remote credentials and malformed hosts are not allowed"
            )
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if ":" in value and "/" in value.split(":", 1)[1]:
        host, path = value.split(":", 1)
        if host and path and not any(char.isspace() for char in value):
            return f"ssh://{host}/{path.lstrip('/')}"
    raise RepositoryValidationError(
        "remote must use https, ssh, or SCP-like Git syntax"
    )
