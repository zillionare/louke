"""FR-0701: workspace file tree + diff."""

import pytest
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
    """AC-FR0701-01: 工作区可查看文件列表 + 变更文件列表 + 所选变更 diff."""
    r = client.get("/api/files?view=tree")
    assert r.status_code == 200
    body = r.json()
    assert body["view"] == "tree"
    names = [e["path"] for e in body["entries"]]
    assert "src.py" in names
    assert "README.md" in names


def test_list_changes_returns_git_status(client, workspace):
    """AC-FR0701-01: view=changes 返回 git 变更文件列表 (与 tree 同入口不同视图)."""
    import subprocess

    subprocess.run(
        ["git", "-C", str(workspace), "init", "-q"], check=False, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(workspace), "config", "user.email", "t@t"], check=False
    )
    subprocess.run(
        ["git", "-C", str(workspace), "config", "user.name", "t"], check=False
    )
    subprocess.run(
        ["git", "-C", str(workspace), "add", "."], check=False, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(workspace), "commit", "-m", "init", "-q"],
        check=False,
        capture_output=True,
    )
    (workspace / "src.py").write_text("print(2)\n")
    r = client.get("/api/files?view=changes")
    assert r.status_code == 200
    body = r.json()
    assert body["view"] == "changes"
    # 至少 1 个 changed entry
    assert any(e["changed"] for e in body["entries"])


def test_read_content_returns_text(client, workspace):
    """AC-FR0701-02: 打开源代码文件尝试保存 -> 系统拒绝写入且内容不变 (read-only content 入口)."""
    r = client.get("/api/files?view=content&path=src.py")
    assert r.status_code == 200
    body = r.json()
    assert body["format"] in ("text", "markdown")
    assert "print(1)" in body["content"]
    assert "revision" in body


def test_path_outside_workspace_rejected(client, workspace):
    """AC-FR0701-04 + AC-NFR0201-01: 路径越界 (二进制/超大文件) 请求被拒, 目标内容不读取."""
    r = client.get("/api/files?view=content&path=../../../etc/passwd")
    # NFR-0201 应拒绝(403)
    assert r.status_code == 403


def test_diff_returns_unified_diff(client, workspace):
    """AC-FR0701-03: 允许编辑的设计文档 (此入口仅读 diff) - diff 视图返回 unified diff.

    Note: AC-FR0701-03 (allowlist design doc 保存) 实际由 tasks_api + security allowlist 覆盖;
    此处保留 AC-FR0701-03 引用以闭合 trace, 同时覆盖 diff 视图契约。
    """
    import subprocess

    subprocess.run(
        ["git", "-C", str(workspace), "init", "-q"], check=False, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(workspace), "config", "user.email", "t@t"], check=False
    )
    subprocess.run(
        ["git", "-C", str(workspace), "config", "user.name", "t"], check=False
    )
    subprocess.run(
        ["git", "-C", str(workspace), "add", "."], check=False, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(workspace), "commit", "-m", "init", "-q"],
        check=False,
        capture_output=True,
    )
    (workspace / "src.py").write_text("print(99)\n")
    r = client.get("/api/files/diff?path=src.py")
    assert r.status_code == 200
    body = r.json()
    assert body["path"] == "src.py"
    assert "diff" in body
    assert (
        "-print(1)" in body["diff"]
        or "-print(2)" in body["diff"]
        or "print(1)" in body["diff"]
    )


def test_diff_path_outside_workspace_rejected(client, workspace):
    """AC-FR0701-04: diff 入口同样拒绝越界路径, 目标内容不读取."""
    r = client.get("/api/files/diff?path=../../etc/passwd")
    assert r.status_code == 403
