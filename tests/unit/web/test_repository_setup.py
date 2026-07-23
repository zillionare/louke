"""Unit contracts for safe repository selection and preview."""

from __future__ import annotations

import pytest

from louke.web.repository_setup import (
    RepositorySelection,
    RepositoryValidationError,
    build_repository_preview,
)


def test_init_preview_is_side_effect_free_and_describes_impact(tmp_path) -> None:
    """AC-FR0301-01: init selection only creates a preview."""
    preview = build_repository_preview(
        RepositorySelection(mode="init", remote_url=None),
        workspace=tmp_path,
    )

    assert preview.mode == "init"
    assert preview.workspace_config_modification_count == 0
    assert preview.repository_resource_creation_count == 0
    assert any(".git" in item for item in preview.summary)
    assert not (tmp_path / ".git").exists()


@pytest.mark.parametrize(
    "remote", ["file:///tmp/repo", "/tmp/repo", "https://user:pass@example/repo"]
)
def test_clone_preview_rejects_unsafe_remote(remote: str, tmp_path) -> None:
    """AC-FR0301-02: local paths and URL credentials fail closed."""
    with pytest.raises(RepositoryValidationError):
        build_repository_preview(
            RepositorySelection(mode="clone", remote_url=remote),
            workspace=tmp_path,
        )
