"""FR-0701: workspace file tree + diff."""
import pytest
from pathlib import Path
from louke.files_api import app


@pytest.fixture
def workspace(tmp_path):
    """Create a workspace with some files and a single .louke design doc dir."""
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "src.py").write_text("print(1)\n")
    (ws / "README.md").write_text("# Hi\n")
    louke_dir = ws / ".louke" / "project" / "specs" / "test"
    louke_dir.mkdir(parents=True)
    (louke_dir / "story.md").write_text("story text\n")
    return ws


@pytest.fixture
def client(workspace, monkeypatch):
    """Test client with CWD pointing at the workspace so paths resolve correctly."""
    monkeypatch.chdir(workspace)
    from starlette.testclient import TestClient
    return TestClient(app)


def test_list_tree_returns_files_and_dirs(client):
    r = client.get("/api/files?view=tree")
    assert r.status_code == 200
    body = r.json()
    assert body["view"] == "tree"
    names = [e["path"] for e in body["entries"]]
    assert "src.py" in names
    assert "README.md" in names


def test_list_changes_returns_git_status(client, workspace):
    """If git is initialized and a file is modified, view=changes should surface it."""
    import subprocess
    subprocess.run(["git", "-C", str(workspace), "init", "-q"], check=False, capture_output=True)
    subprocess.run(["git", "-C", str(workspace), "config", "user.email", "t@t"], check=False)
    subprocess.run(["git", "-C", str(workspace), "config", "user.name", "t"], check=False)
    subprocess.run(["git", "-C", str(workspace), "add", "."], check=False, capture_output=True)
    subprocess.run(["git", "-C", str(workspace), "commit", "-m", "init", "-q"],
                   check=False, capture_output=True)
    (workspace / "src.py").write_text("print(2)\n")
    r = client.get("/api/files?view=changes")
    assert r.status_code == 200
    body = r.json()
    assert body["view"] == "changes"
    # 至少 1 个 changed entry
    assert any(e["changed"] for e in body["entries"])


def test_read_content_returns_text(client, workspace):
    r = client.get("/api/files?view=content&path=src.py")
    assert r.status_code == 200
    body = r.json()
    assert body["format"] in ("text", "markdown")
    assert "print(1)" in body["content"]
    assert "revision" in body


def test_path_outside_workspace_rejected(client, workspace):
    r = client.get("/api/files?view=content&path=../../../etc/passwd")
    # NFR-0201 应拒绝(403)
    assert r.status_code == 403


def test_diff_returns_unified_diff(client, workspace):
    """修改文件后,/api/files/diff 返回 unified diff。"""
    import subprocess
    subprocess.run(["git", "-C", str(workspace), "init", "-q"], check=False, capture_output=True)
    subprocess.run(["git", "-C", str(workspace), "config", "user.email", "t@t"], check=False)
    subprocess.run(["git", "-C", str(workspace), "config", "user.name", "t"], check=False)
    subprocess.run(["git", "-C", str(workspace), "add", "."], check=False, capture_output=True)
    subprocess.run(["git", "-C", str(workspace), "commit", "-m", "init", "-q"],
                   check=False, capture_output=True)
    (workspace / "src.py").write_text("print(99)\n")
    r = client.get("/api/files/diff?path=src.py")
    assert r.status_code == 200
    body = r.json()
    assert body["path"] == "src.py"
    assert "diff" in body
    assert "-print(1)" in body["diff"] or "-print(2)" in body["diff"] or "print(1)" in body["diff"]


def test_diff_path_outside_workspace_rejected(client, workspace):
    r = client.get("/api/files/diff?path=../../etc/passwd")
    assert r.status_code == 403
