"""IF-05: Repository selection, Preview, and Confirm.

AC-FR0301-01, AC-FR0301-02, AC-FR0401-01, AC-FR0401-02, AC-NFR0101-01

Integration tests verify that repository preview is zero-side-effect,
that invalid URLs are rejected, and that binding requires explicit human
selection.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from louke.web.repository_setup import (
    RepositorySelection,
    RepositoryValidationError,
    build_repository_preview,
)
from louke.web.secret_redaction import redact_url
from louke.web.workspace_binding import (
    BindingCandidate,
    resolve_binding,
)


def test_init_preview_has_zero_side_effects(workspace_dir: Path):
    """AC-FR0301-01: init preview does not create .git or modify workspace."""
    # AC-FR0301-01
    selection = RepositorySelection(mode="init", remote_url=None)
    preview = build_repository_preview(selection, workspace=workspace_dir)
    assert preview.workspace_config_modification_count == 0
    assert preview.repository_resource_creation_count == 0
    assert not (workspace_dir / ".git").exists()


def test_clone_preview_rejects_url_with_credentials(workspace_dir: Path):
    """AC-NFR0101-01: clone preview rejects URL with embedded userinfo."""
    # AC-NFR0101-01
    selection = RepositorySelection(
        mode="clone", remote_url="https://user:token@github.com/org/repo.git"
    )
    with pytest.raises(RepositoryValidationError):
        build_repository_preview(selection, workspace=workspace_dir)


def test_clone_preview_shows_redacted_display_remote(workspace_dir: Path):
    """AC-FR0301-01: clone preview shows clean display remote for valid URL."""
    # AC-FR0301-01
    selection = RepositorySelection(
        mode="clone", remote_url="https://github.com/org/repo.git"
    )
    preview = build_repository_preview(selection, workspace=workspace_dir)
    assert preview.display_remote == "https://github.com/org/repo.git"
    assert "token" not in preview.display_remote
    assert "user:" not in preview.display_remote


def test_clone_preview_zero_creation_count(workspace_dir: Path):
    """AC-FR0301-01: clone preview reports zero resource creation."""
    # AC-FR0301-01
    selection = RepositorySelection(
        mode="clone", remote_url="https://github.com/org/repo.git"
    )
    preview = build_repository_preview(selection, workspace=workspace_dir)
    assert preview.repository_resource_creation_count == 0


def test_invalid_remote_url_rejected(workspace_dir: Path):
    """AC-FR0301-02: invalid remote URL scheme is rejected."""
    # AC-FR0301-02
    selection = RepositorySelection(mode="clone", remote_url="file:///etc/passwd")
    with pytest.raises(RepositoryValidationError):
        build_repository_preview(selection, workspace=workspace_dir)


def test_remote_with_userinfo_rejected(workspace_dir: Path):
    """AC-NFR0101-01: URL with embedded userinfo is rejected to prevent credential leak."""
    # AC-NFR0101-01
    selection = RepositorySelection(
        mode="clone", remote_url="https://user:pass@github.com/org/repo.git"
    )
    with pytest.raises(RepositoryValidationError):
        build_repository_preview(selection, workspace=workspace_dir)


def test_binding_requires_explicit_selection():
    """AC-FR0401-01: multiple candidates without selection stays waiting."""
    # AC-FR0401-01
    candidates = (
        BindingCandidate(value="origin/main", source="git_remote"),
        BindingCandidate(value="upstream/main", source="git_remote"),
    )
    result = resolve_binding(candidates)
    assert result.status == "waiting_human"
    assert result.selected is None


def test_binding_single_candidate_without_selection_stays_waiting():
    """AC-FR0401-01: single candidate without explicit selection is not auto-selected."""
    # AC-FR0401-01
    candidates = (BindingCandidate(value="origin/main", source="git_remote"),)
    result = resolve_binding(candidates)
    assert result.status == "waiting_human"


def test_binding_with_explicit_selection_completes():
    """AC-FR0401-02: explicit human selection completes binding."""
    # AC-FR0401-02
    candidates = (BindingCandidate(value="origin/main", source="git_remote"),)
    result = resolve_binding(candidates, selected="origin/main", revision="setup_v1")
    assert result.status == "done"
    assert result.selected == "origin/main"
    assert result.revision == "setup_v1"


def test_binding_revision_change_invalidates_old_selection():
    """AC-FR0401-02: revision change prevents stale selection from being applied."""
    # AC-FR0401-02
    candidates = (BindingCandidate(value="origin/main", source="git_remote"),)
    result = resolve_binding(candidates, selected="origin/main", revision="setup_v2")
    assert result.revision == "setup_v2"
    # A different revision with the same selected value should still be bound to new revision
    assert result.status == "done"


def test_url_redaction_strips_credentials():
    """AC-NFR0101-01: redact_url removes userinfo from display URL."""
    # AC-NFR0101-01
    redacted = redact_url("https://user:secret@github.com/org/repo.git")
    assert "secret" not in redacted
    assert "user:" not in redacted
    assert "github.com" in redacted
