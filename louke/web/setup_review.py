"""Revision-bound Setup review and confirmation decisions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Preview:
    """Complete Setup preview shown before Human confirmation."""

    revision: str
    digest: str
    operations: tuple[str, ...]
    workspace_identity: str


@dataclass(frozen=True)
class Confirmation:
    """Accepted confirmation result with explicit release isolation."""

    confirmed: bool
    revision: str
    release_resource_creation_count: int = 0


def confirm_preview(
    preview: Preview, *, expected_revision: str, digest: str
) -> Confirmation:
    """Confirm the exact current preview without creating release resources.

    Args:
        preview: Server-held preview to confirm.
        expected_revision: Revision supplied by the authenticated Human.
        digest: Preview digest supplied by the Human surface.

    Returns:
        A confirmation with zero release-level side effects.

    Raises:
        ValueError: If revision or digest is stale.
    """
    if expected_revision != preview.revision or digest != preview.digest:
        raise ValueError("stale setup preview")
    return Confirmation(confirmed=True, revision=preview.revision)
