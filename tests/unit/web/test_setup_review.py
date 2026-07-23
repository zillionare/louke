"""Unit contracts for Setup review and revision-bound confirmation."""

from __future__ import annotations

import pytest

from louke.web.setup_review import Preview, confirm_preview


def test_review_preview_has_no_release_side_effects() -> None:
    """AC-FR0601-01: review explicitly states workspace-only impact."""
    preview = Preview(
        revision="setup_1",
        digest="digest_1",
        operations=("repository_init",),
        workspace_identity="workspace_1",
    )

    result = confirm_preview(preview, expected_revision="setup_1", digest="digest_1")

    assert result.confirmed
    assert result.release_resource_creation_count == 0


def test_stale_review_confirmation_is_rejected() -> None:
    """AC-FR0601-02: stale preview cannot execute an old choice."""
    preview = Preview("setup_2", "digest_2", ("repository_init",), "workspace_1")

    with pytest.raises(ValueError, match="stale"):
        confirm_preview(preview, expected_revision="setup_1", digest="digest_2")
