"""FR-0801: Markdown document discovery + rendering."""
import pytest
from pathlib import Path
from louke.files_api import app  # reuse the same ASGI app


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    # Louke design Markdown under .louke/project/
    louke_dir = ws / ".louke" / "project" / "specs" / "test"
    louke_dir.mkdir(parents=True)
    (louke_dir / "story.md").write_text("# Test story\nbody\n")
    (louke_dir / "spec.md").write_text("# Test spec\nbody\n")
    (louke_dir / "acceptance.md").write_text("# Test acceptance\nbody\n")
    (louke_dir / "test-plan.md").write_text("# Test test-plan\nbody\n")
    # root README
    (ws / "README.md").write_text("# Project\n")
    # docs/**/*.md (recursive)
    docs = ws / "docs" / "guide" / "advanced"
    docs.mkdir(parents=True)
    (docs / "design.md").write_text("# Design\nbody\n")
    (docs / "other.txt").write_text("not markdown\n")
    # binary file
    (ws / "image.bin").write_bytes(b"\x00\x01\x02\x03")
    # Range of design doc types per spec
    (louke_dir / "architecture.md").write_text("# Arch\nbody\n")
    (louke_dir / "interfaces.md").write_text("# IFs\nbody\n")
    return ws


@pytest.fixture
def client(workspace, monkeypatch):
    monkeypatch.chdir(workspace)
    from starlette.testclient import TestClient
    return TestClient(app)


def test_documents_view_lists_design_docs(client):
    """AC-FR0801-01: .louke/project/** 设计 Markdown + README + docs/**/*.md 在文档导航可发现."""
    r = client.get("/api/files?view=documents")
    assert r.status_code == 200
    body = r.json()
    assert body["view"] == "documents"
    paths = [e["path"] for e in body["entries"]]
    assert any("story.md" in p for p in paths)
    assert any("spec.md" in p for p in paths)
    assert any("acceptance.md" in p for p in paths)
    assert any("architecture.md" in p for p in paths)
    assert any("interfaces.md" in p for p in paths)
    assert any("README.md" in p for p in paths)
    assert any("design.md" in p for p in paths)


def test_documents_view_excludes_non_markdown(client):
    """AC-FR0801-01: 范围外文件 (非 .md) 不在文档导航入口渲染."""
    r = client.get("/api/files?view=documents")
    paths = [e["path"] for e in r.json()["entries"]]
    assert not any("other.txt" in p for p in paths)


def test_documents_view_excludes_binary(client):
    """AC-FR0801-03: 二进制文件不经文档展示入口渲染."""
    r = client.get("/api/files?view=documents")
    paths = [e["path"] for e in r.json()["entries"]]
    assert not any("image.bin" in p for p in paths)


def test_documents_view_excludes_test_plan_md(client):
    """AC-FR0801-01: test-plan.md 不在承诺的可发现范围内 (只有 story/spec/acceptance/architecture/interfaces)."""
    r = client.get("/api/files?view=documents")
    paths = [e["path"] for e in r.json()["entries"]]
    assert not any("test-plan.md" in p for p in paths)


def test_render_design_doc_returns_html(client):
    """AC-FR0801-02: 选择范围内 Markdown 文件 -> 内容来自所选文件并按 Markdown 展示."""
    r = client.get("/api/files?view=content&path=.louke/project/specs/test/story.md")
    assert r.status_code == 200
    body = r.json()
    assert "content" in body
    assert body["format"] == "markdown"
    # rendered_html 由 Python-Markdown 渲染(可在视图层加;本 issue 暂用 raw content)


def test_render_binary_rejected(client):
    """AC-FR0801-03: 二进制文件 / 超过 500 行 Markdown 仅在用户批准后渲染正文 (此处二进制直接拒)."""
    r = client.get("/api/files?view=content&path=image.bin")
    assert r.status_code in (403, 415)
