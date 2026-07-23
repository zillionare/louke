"""FR-0300: Web Release 请求与单活跃主 Release.

AC references:
- AC-FR0300-01: preview request with empty/invalid story or release_version
  produces field-level errors and must not create or modify any release-level
  resource (Project, WorkflowRun, release GitHub Project, release branch, Spec
  directory) or Backlog entry.
- AC-FR0300-02: when the workspace already has an active main release,
  repeated or concurrent confirm requests for the same new release produce
  exactly one canonical Backlog entry keyed by request identity/digest, and
  no second Project/WorkflowRun/branch/Spec directory.
- AC-FR0300-03: after `lk serve` restart, the blocked Backlog entry still
  shows the original story, version, reason, created time and source identity
  (byte-equal identity).
"""

from __future__ import annotations

import threading

import pytest

from louke.runtime.release_request import (
    BacklogEntry,
    BacklogStore,
    PreviewError,
    ReleasePreview,
    ReleaseRequestIdentity,
    confirm_release_request,
    preview_release_request,
)


def _identity(
    workspace_id: str = "ws_1",
    story: str = "Add offline cache for project list",
    release_version: str = "0.14.0",
) -> ReleaseRequestIdentity:
    return ReleaseRequestIdentity(
        workspace_id=workspace_id,
        story=story,
        release_version=release_version,
    )


# AC-FR0300-01 ---------------------------------------------------------------
@pytest.mark.parametrize(
    "story, release_version, expected_field, expected_code",
    [
        ("", "0.14.0", "story", "VALIDATION_FAILED"),
        ("   \t  ", "0.14.0", "story", "VALIDATION_FAILED"),
        ("Add offline cache", "", "release_version", "RELEASE_VERSION_INVALID"),
        (
            "Add offline cache",
            "../escape",
            "release_version",
            "RELEASE_VERSION_INVALID",
        ),
    ],
)
def test_preview_rejects_empty_or_invalid_inputs_without_side_effects(
    story: str, release_version: str, expected_field: str, expected_code: str
) -> None:
    """AC-FR0300-01: empty/invalid story or version raises PreviewError."""
    with pytest.raises(PreviewError) as exc_info:
        preview_release_request(
            workspace_id="ws_1",
            story=story,
            release_version=release_version,
            active_main_release_present=False,
        )
    assert exc_info.value.field == expected_field
    assert exc_info.value.code == expected_code


def test_preview_preserves_host_legal_prerelease_and_build_metadata() -> None:
    """AC-FR0300-01: IF-WEB-03 versions are not narrowed to PEP 440."""
    preview = preview_release_request(
        workspace_id="ws_1",
        story="Ship the reflow",
        release_version="v2026-preview+linux",
        active_main_release_present=False,
    )

    assert preview.release_version == "v2026-preview+linux"


def test_preview_with_no_active_main_release_has_zero_side_effects() -> None:
    """AC-FR0300-01: a valid preview never produces release-level resources."""
    preview = preview_release_request(
        workspace_id="ws_1",
        story="Add offline cache for project list",
        release_version="0.14.0",
        active_main_release_present=False,
    )
    assert isinstance(preview, ReleasePreview)
    assert preview.side_effects == ()
    assert preview.request_digest.startswith("sha256:")
    # Preview identity is deterministic and does not leak secrets.
    assert preview.workspace_id == "ws_1"


def test_preview_with_active_main_release_blocked_but_no_resources() -> None:
    """AC-FR0300-01 + AC-FR0300-02: a blocked preview still produces no
    release-level side effects; the blocking reason is observable on the
    preview before any confirm happens."""
    preview = preview_release_request(
        workspace_id="ws_1",
        story="Add offline cache",
        release_version="0.14.0",
        active_main_release_present=True,
    )
    assert preview.side_effects == ()
    assert preview.blocked_reason is not None
    assert "active" in preview.blocked_reason.lower()


# AC-FR0300-02 ---------------------------------------------------------------
def test_confirm_when_active_main_release_present_creates_single_backlog_entry() -> (
    None
):
    """AC-FR0300-02: a single Backlog entry is created and no release-level
    resources are produced."""
    store = BacklogStore.in_memory()
    identity = _identity()
    result = confirm_release_request(
        identity=identity,
        active_main_release_present=True,
        store=store,
    )
    assert result.routed_to == "backlog"
    assert result.created_resources == ()
    entries = store.list_entries(workspace_id="ws_1")
    assert len(entries) == 1
    entry = entries[0]
    assert entry.story == identity.story
    assert entry.release_version == identity.release_version
    assert entry.reason  # non-empty
    assert entry.source_identity.workspace_id == "ws_1"


def test_confirm_idempotent_under_repeated_requests_for_same_identity() -> None:
    """AC-FR0300-02: repeated confirm with the same request identity returns
    the same backlog entry_id and does not create a second entry."""
    store = BacklogStore.in_memory()
    identity = _identity()
    first = confirm_release_request(
        identity=identity,
        active_main_release_present=True,
        store=store,
    )
    second = confirm_release_request(
        identity=identity,
        active_main_release_present=True,
        store=store,
    )
    assert first.entry_id == second.entry_id
    assert len(store.list_entries(workspace_id="ws_1")) == 1


def test_confirm_concurrent_requests_for_same_identity_produce_one_entry() -> None:
    """AC-FR0300-02: concurrent confirms with the same request identity
    produce exactly one Backlog entry; the loser gets an already-completed
    conflict result pointing at the same entry_id."""
    store = BacklogStore.in_memory()
    identity = _identity()
    barrier = threading.Barrier(2)
    results: list[object] = []
    errors: list[BaseException] = []

    def _confirm() -> None:
        try:
            barrier.wait(timeout=2.0)
            results.append(
                confirm_release_request(
                    identity=identity,
                    active_main_release_present=True,
                    store=store,
                )
            )
        except BaseException as exc:  # pragma: no cover - failure path
            errors.append(exc)

    threads = [threading.Thread(target=_confirm) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    assert not errors, f"threads raised: {errors!r}"
    assert len(results) == 2
    entry_ids = {getattr(r, "entry_id") for r in results}  # type: ignore[attr-defined]
    assert entry_ids == {first_result.entry_id for first_result in [results[0]]}  # type: ignore[list-item]
    assert len(store.list_entries(workspace_id="ws_1")) == 1


def test_confirm_when_no_active_main_release_routes_to_preflight() -> None:
    """AC-FR0300-02: when there is no active main release, confirm proceeds
    to preflight rather than Backlog; no Backlog entry is created."""
    store = BacklogStore.in_memory()
    identity = _identity()
    result = confirm_release_request(
        identity=identity,
        active_main_release_present=False,
        store=store,
    )
    assert result.routed_to == "preflight"
    assert result.entry_id is None
    assert store.list_entries(workspace_id="ws_1") == ()


# AC-FR0300-03 ---------------------------------------------------------------
def test_backlog_entry_persists_identical_bytes_across_restart(tmp_path) -> None:
    """AC-FR0300-03: after restart (re-opening the store from disk), the
    Backlog entry shows byte-equal story, version, reason, created time and
    source identity."""
    db_path = tmp_path / "backlog.json"
    store = BacklogStore.at_path(db_path)
    identity = _identity()
    result = confirm_release_request(
        identity=identity,
        active_main_release_present=True,
        store=store,
    )
    # AC-FR0300-03: stable entry_id derived from workspace + request_digest.
    assert result.entry_id.startswith("bl_")
    assert len(result.entry_id) == len("bl_") + 24

    # Simulate restart by reopening the store from the same path.
    restarted = BacklogStore.at_path(db_path)
    entries = restarted.list_entries(workspace_id="ws_1")
    assert len(entries) == 1
    entry: BacklogEntry = entries[0]
    assert entry.entry_id == result.entry_id
    assert entry.story == identity.story
    assert entry.release_version == identity.release_version
    assert entry.reason  # non-empty
    assert entry.created_at  # non-empty stable timestamp
    assert entry.source_identity == identity


def test_request_digest_is_stable_and_changes_on_any_identity_field() -> None:
    """AC-FR0300-02 + AC-FR0300-03: the request digest is deterministic over
    (workspace_id, story, release_version) and changes when any field changes."""
    base = _identity()
    same_again = _identity()
    assert base.request_digest == same_again.request_digest
    different_story = ReleaseRequestIdentity(
        workspace_id="ws_1",
        story="Different story text",
        release_version="0.14.0",
    )
    different_workspace = ReleaseRequestIdentity(
        workspace_id="ws_2",
        story="Add offline cache for project list",
        release_version="0.14.0",
    )
    different_version = ReleaseRequestIdentity(
        workspace_id="ws_1",
        story="Add offline cache for project list",
        release_version="0.15.0",
    )
    assert different_story.request_digest != base.request_digest
    assert different_workspace.request_digest != base.request_digest
    assert different_version.request_digest != base.request_digest
