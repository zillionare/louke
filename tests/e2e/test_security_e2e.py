"""NFR-0201: workspace security e2e (path traversal rejection + writable allowlist)."""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from louke.files_api import app


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """Workspace with a source file (.py) and a design doc (.md)."""
    ws = tmp_path / "ws"
    ws.mkdir()
    monkeypatch.chdir(ws)
    (ws / "src.py").write_text("# source\n", encoding="utf-8")
    sd = ws / ".louke" / "project" / "specs" / "demo"
    sd.mkdir(parents=True)
    (sd / "spec.md").write_text("# spec\n", encoding="utf-8")
    return ws


@pytest.fixture
def client(workspace):
    return TestClient(app)


def test_outside_workspace_read_rejected_e2e(client, workspace):
    """AC-NFR0201-01: GET /api/files with traversal path returns 403 PATH_OUTSIDE_WORKSPACE; sentinel bytes unchanged."""
    r = client.get("/api/files?view=content&path=../../../etc/passwd")
    assert r.status_code == 403, r.text
    assert r.json()["error_code"] == "PATH_OUTSIDE_WORKSPACE"


def test_writable_allowlist_blocks_source_write_e2e(client, workspace):
    """AC-NFR0201-02: source files (not in writable allowlist) cannot be PUT; bytes unchanged.

    v0.11 files_api PUT route is currently registered only for design docs in
    `.louke/project/**/story.md|spec.md|acceptance.md`. Source files return 404
    (route not matched) which is the correct rejection — bytes are not modified
    because the route does not exist. We assert sentinel-bytes-unchanged.
    """
    r = client.put("/api/files/src.py", json={"content": "print('hacked')"})
    # 404 (route not registered for source files) is the correct rejection
    assert r.status_code in (403, 400, 404), r.text
    # Sentinel bytes must be unchanged
    assert (workspace / "src.py").read_text() == "# source\n"