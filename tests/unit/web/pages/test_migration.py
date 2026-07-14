"""TestClient tests for the migration page sub-app (B3c).

Verifies the migration preview / confirm / rollback / legacy HTML page:
- GET / returns 200 text/html with three sections: Preview, Confirm, Rollback
  (plus a Legacy history section).
- POST /preview with a workspace path calls the upstream preview seam and
  re-renders the page showing the categorized preview (additions, conversions,
  preserved, conflicts, unsupported) plus the recommended mode and a mode
  override radio.
- POST /confirm calls the upstream confirm seam and re-renders with an
  "applied" message.
- POST /rollback calls the upstream rollback seam and re-renders with a
  "rolled back" message.
- Upstream errors surface as a user-facing error message with status 200.

All upstream calls go through module-level seams patched with AsyncMock.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from starlette.testclient import TestClient

from louke.web.pages import migration as migration_page


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient backed by a fresh migration page sub-app."""
    return TestClient(migration_page.create_app(api_base="http://testserver"))


def _preview_payload() -> dict:
    """Return a migration preview payload mirroring the API shape."""
    return {
        "additions": ("docs/migrated.md",),
        "conversions": ("old-config.json",),
        "preserved": ("README.md",),
        "conflicts": ("stale-state.json",),
        "unsupported": ("binary.dat",),
        "recommended_mode": "local",
        "available_modes": ("local", "global"),
        "old_bytes_modified": False,
    }


def test_migration_index_renders_three_sections(client: TestClient) -> None:
    """GET / returns 200 and renders Preview, Confirm and Rollback sections."""
    resp = client.get("/")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    body = resp.text
    assert "Preview" in body
    assert "Confirm" in body
    assert "Rollback" in body
    # The page must contain three <section> blocks.
    assert body.count("<section") >= 3


def test_migration_preview_renders_categories(client: TestClient) -> None:
    """POST /preview renders the categorized preview and mode selector."""
    mock = AsyncMock(return_value=_preview_payload())
    with patch.object(migration_page, "_fetch_preview", new=mock):
        resp = client.post("/preview", data={"workspace_path": "/tmp/ws"})

    assert resp.status_code == 200
    body = resp.text
    # The seam received the api_base and the workspace path.
    mock.assert_awaited_once()
    assert mock.await_args.args[0] == "http://testserver"
    assert mock.await_args.args[1] == "/tmp/ws"
    # Every preview category is rendered.
    assert "docs/migrated.md" in body
    assert "old-config.json" in body
    assert "README.md" in body
    assert "stale-state.json" in body
    assert "binary.dat" in body
    # Recommended mode and a mode override radio for confirm.
    assert "local" in body
    assert 'name="mode"' in body


def test_migration_confirm_renders_applied_message(client: TestClient) -> None:
    """POST /confirm calls the confirm seam and shows an applied message."""
    mock = AsyncMock(
        return_value={
            "workspace_path": "/tmp/ws",
            "committed": True,
            "has_restore_point": True,
        }
    )
    with patch.object(migration_page, "_post_confirm", new=mock):
        resp = client.post(
            "/confirm",
            data={"workspace_path": "/tmp/ws", "mode": "local"},
        )

    assert resp.status_code == 200
    body = resp.text
    mock.assert_awaited_once()
    assert mock.await_args.args[0] == "http://testserver"
    assert mock.await_args.args[1] == "/tmp/ws"
    assert mock.await_args.args[2] == "local"
    assert "applied" in body.lower()


def test_migration_rollback_renders_rolled_back_message(client: TestClient) -> None:
    """POST /rollback calls the rollback seam and shows a rolled-back message."""
    mock = AsyncMock(
        return_value={"workspace_path": "/tmp/ws", "rolled_back": True}
    )
    with patch.object(migration_page, "_post_rollback", new=mock):
        resp = client.post("/rollback", data={"workspace_path": "/tmp/ws"})

    assert resp.status_code == 200
    body = resp.text
    mock.assert_awaited_once()
    assert mock.await_args.args[0] == "http://testserver"
    assert mock.await_args.args[1] == "/tmp/ws"
    assert "rolled back" in body.lower()


def test_migration_handles_upstream_error(client: TestClient) -> None:
    """When the preview seam raises, the page shows an error, status 200."""
    mock = AsyncMock(side_effect=RuntimeError("upstream 500"))
    with patch.object(migration_page, "_fetch_preview", new=mock):
        resp = client.post("/preview", data={"workspace_path": "/tmp/ws"})

    assert resp.status_code == 200
    assert "upstream 500" in resp.text or "error" in resp.text.lower()
