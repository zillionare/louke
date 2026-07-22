"""Unit contracts for the v0.14 public release request boundary."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from louke.v014.fr0300_release_request import (
    BacklogStore,
    PreviewError,
    ReleaseRequestIdentity,
    confirm_release_request,
    preview_release_request,
)


def _identity(
    story: str = "Ship the reflow", version: str = "v0.14.0"
) -> ReleaseRequestIdentity:
    return ReleaseRequestIdentity(
        workspace_id="workspace-1", story=story, release_version=version
    )


def test_request_identity_rejects_empty_workspace_id() -> None:
    """AC-NFR0100-01: opaque workspace identities are non-empty."""
    with pytest.raises(ValueError, match="workspace_id"):
        ReleaseRequestIdentity(
            workspace_id="", story="story", release_version="v0.14.0"
        )


def test_preview_is_side_effect_free_and_contains_request_identity() -> None:
    """AC-FR0300-01: preview validates input without provisioning resources."""
    preview = preview_release_request(
        workspace_id="workspace-1",
        story="Ship the reflow",
        release_version="v0.14.0",
        active_main_release_present=False,
    )

    assert preview.story == "Ship the reflow"
    assert preview.request_digest.startswith("sha256:")
    assert preview.side_effects == ()


@pytest.mark.parametrize(
    ("story", "release_version", "field"),
    [
        ("", "v0.14.0", "story"),
        ("story", "", "release_version"),
        ("story", "v0.14", "release_version"),
    ],
)
def test_preview_rejects_invalid_release_input(
    story: str, release_version: str, field: str
) -> None:
    """AC-FR0300-01: invalid preview input reports the failing field."""
    with pytest.raises(PreviewError) as error:
        preview_release_request(
            workspace_id="workspace-1",
            story=story,
            release_version=release_version,
            active_main_release_present=False,
        )

    assert error.value.field == field


def test_preview_marks_active_release_without_writing_backlog() -> None:
    """AC-FR0300-01: active-release information remains preview-only."""
    preview = preview_release_request(
        workspace_id="workspace-1",
        story="Ship the reflow",
        release_version="v0.14.0",
        active_main_release_present=True,
    )

    assert preview.blocked_reason
    assert preview.side_effects == ()


def test_duplicate_active_release_confirms_share_one_backlog_entry() -> None:
    """AC-FR0300-02: repeated confirmation creates one canonical backlog entry."""
    store = BacklogStore.in_memory()
    identity = _identity()

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(
            executor.map(
                lambda _: confirm_release_request(
                    identity=identity,
                    active_main_release_present=True,
                    store=store,
                ),
                range(8),
            )
        )

    assert len({result.entry_id for result in results}) == 1
    assert len(store.list_entries(workspace_id="workspace-1")) == 1


def test_confirm_without_active_release_has_no_backlog_side_effect() -> None:
    """AC-FR0300-02: an unblocked request proceeds without backlog mutation."""
    store = BacklogStore.in_memory()

    result = confirm_release_request(
        identity=_identity(),
        active_main_release_present=False,
        store=store,
    )

    assert result.routed_to == "preflight"
    assert result.entry_id is None
    assert store.list_entries(workspace_id="workspace-1") == ()
