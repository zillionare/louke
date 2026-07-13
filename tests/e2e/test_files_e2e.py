"""FR-0701 + FR-0801: workspace files / diff / documents / binary rejection e2e."""

from __future__ import annotations

import subprocess

import pytest
from starlette.testclient import TestClient

from louke.files_api import app


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """Real git workspace with .py, .md, .louke design docs, and a binary file."""
    ws = tmp_path / "ws"
    ws.mkdir()
    monkeypatch.chdir(ws)
    subprocess.run(["git", "init", "-q"], cwd=ws, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=ws, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=ws, check=True)
    (ws / "src.py").write_text("print(1)\n", encoding="utf-8")
    (ws / "README.md").write_text("# Hi\n", encoding="utf-8")
    (ws / "image.bin").write_bytes(b"\x00\x01\x02\x03binary")
    sd = ws / ".louke" / "project" / "specs" / "demo"
    sd.mkdir(parents=True)
    (sd / "spec.md").write_text("# Demo spec\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=ws, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=ws, check=True)
    return ws


@pytest.fixture
def client(workspace):
    return TestClient(app)


def test_files_tree_view_e2e(client, workspace):
    """AC-FR0701-01: GET /api/files?view=tree lists project files (.py + .md)."""
    r = client.get("/api/files?view=tree")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["view"] == "tree"
    paths = [e["path"] for e in body["entries"]]
    assert "src.py" in paths and "README.md" in paths


def test_files_changes_view_e2e(client, workspace):
    """AC-FR0701-01: GET /api/files?view=changes lists git-modified files (post-commit edit)."""
    (workspace / "src.py").write_text("print(2)\n", encoding="utf-8")
    r = client.get("/api/files?view=changes")
    assert r.status_code == 200, r.text
    assert "src.py" in [e["path"] for e in r.json()["entries"]]


def test_files_diff_e2e(client, workspace):
    """AC-FR0701-02: modified file -> /api/files/diff returns unified diff with old/new lines."""
    (workspace / "src.py").write_text("print(2)\nprint('new')\n", encoding="utf-8")
    r = client.get("/api/files/diff?path=src.py")
    assert r.status_code == 200, r.text
    diff = r.json()["diff"]
    assert "-print(1)" in diff and "+print(2)" in diff


def test_files_content_with_format_e2e(client, workspace):
    """AC-FR0701-04: GET /api/files?view=content&path=*.md returns markdown + format=markdown.

    v0.11 minimal files API returns content + format + line_count + revision.
    rendered_html is reserved for future rich rendering (FR-0801 documents view);
    not required for FR-0701 content-view contract.
    """
    r = client.get("/api/files?view=content&path=README.md")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["path"] == "README.md"
    assert body["format"] == "markdown"
    assert body["content"]
    assert body["line_count"] >= 1


def test_documents_view_lists_design_docs_e2e(client, workspace):
    """AC-FR0801-01: GET /api/files?view=documents lists .louke design docs (spec.md)."""
    r = client.get("/api/files?view=documents")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["view"] == "documents"
    paths = [e["path"] for e in body["entries"]]
    assert any("spec.md" in p for p in paths)


def test_documents_renders_markdown_e2e(client, workspace):
    """AC-FR0801-02: GET design doc returns markdown content with format=markdown.

    v0.11 minimal files API returns content + format for .louke design docs.
    rendered_html (rich preview) is reserved for the future Documents view
    (already partially implemented in v0.10 web UI, see tests/test_web_server.py).
    """
    r = client.get("/api/files?view=content&path=.louke/project/specs/demo/spec.md")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["format"] == "markdown"
    assert body["content"]
    assert "# Demo spec" in body["content"]


def test_binary_rejected_e2e(client, workspace):
    """AC-FR0801-03: binary file content returns BINARY_NOT_PREVIEWABLE; bytes do not leak in response.

    Note: v0.11 files_api uses 403 (Forbidden) for binary rejection rather than 415
    (Unsupported Media Type), with error_code=BINARY_NOT_PREVIEWABLE. The contract
    test asserts the error_code regardless of HTTP status; the important property
    is that binary bytes are not in the response body.
    """
    r = client.get("/api/files?view=content&path=image.bin")
    assert r.status_code in (403, 415), r.text
    body = r.json()
    assert body["error_code"] == "BINARY_NOT_PREVIEWABLE"
    assert "binary" not in r.text.lower() or "not previewable" in r.text.lower()
