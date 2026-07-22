"""Unit contracts for session-bound v0.14 mutation protection."""

from pathlib import Path


from louke.web.auth import (
    csrf_token_for_session,
    issue_session_cookie,
    verify_csrf_token,
)
from louke.web.store import ProjectStore


def _store(tmp_path: Path) -> ProjectStore:
    """Create the smallest project store fixture required by session signing."""
    project_dir = tmp_path / ".louke" / "project"
    project_dir.mkdir(parents=True)
    (project_dir / "project.toml").write_text(
        "[project]\nrepo = 'example/repo'\n", encoding="utf-8"
    )
    return ProjectStore(tmp_path)


def test_csrf_token_is_bound_to_the_authenticated_session(tmp_path: Path) -> None:
    """AC-FR0600-03: CSRF tokens are valid only for their original session."""
    store = _store(tmp_path)
    session = issue_session_cookie(store, "human")
    token = csrf_token_for_session(store, session)

    assert verify_csrf_token(store, session, token)
    assert not verify_csrf_token(store, session + "x", token)
    assert not verify_csrf_token(store, session, token + "x")


def test_csrf_token_requires_non_empty_values(tmp_path: Path) -> None:
    """AC-FR0600-03: missing session or token fails closed."""
    store = _store(tmp_path)

    assert not verify_csrf_token(store, "", "")
    assert not verify_csrf_token(store, "session", "")
