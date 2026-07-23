"""Unit contracts for first-user persistence and safe login continuation."""

from __future__ import annotations

from louke.web.auth import authenticate_user, register_user
from louke.web.store import ProjectStore


def test_first_user_is_persisted_once_and_can_authenticate_after_reopen(
    tmp_path,
) -> None:
    """AC-FR0201-01: one owner survives a store reopen and can log in."""
    project = tmp_path / ".louke" / "project"
    project.mkdir(parents=True)
    (project / "project.toml").write_text("[project]\nrepo = 'example/repo'\n")
    credential = "credential-canary"

    owner = register_user(ProjectStore(tmp_path), "owner", credential)
    authenticated = authenticate_user(ProjectStore(tmp_path), "owner", credential)

    assert owner.username == authenticated.username == "owner"
    assert credential not in ProjectStore(tmp_path).users_path.read_text()
