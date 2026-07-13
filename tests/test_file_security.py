import pytest
from pathlib import Path

from louke.security import WorkspaceSecurity, SecurityError


def test_path_outside_workspace_rejected(tmp_path):
    """AC-NFR0201-01: 指向工作区外目标的读取/diff/保存请求 -> 拒绝, 目标内容未被读取/修改."""
    ws = tmp_path / "ws"
    ws.mkdir()
    sec = WorkspaceSecurity(ws)
    with pytest.raises(SecurityError) as exc:
        sec.read(Path("/etc/passwd"))
    assert exc.value.code == "PATH_OUTSIDE_WORKSPACE"


def test_symlink_inside_workspace_rejected(tmp_path):
    """AC-NFR0201-01: symlink 越界 (指向工作区内但逃逸) 同样拒绝读取."""
    ws = tmp_path / "ws"
    ws.mkdir()
    target = ws / "real.md"
    target.write_text("hello")
    link = ws / "link.md"
    link.symlink_to(target)
    sec = WorkspaceSecurity(ws)
    with pytest.raises(SecurityError) as exc:
        sec.read(link)
    assert exc.value.code == "PATH_OUTSIDE_WORKSPACE"


def test_write_to_readonly_file_rejected(tmp_path):
    """AC-NFR0201-02: 对源代码或未列入可编辑清单的文件发起写请求 -> 拒绝, 字节不变."""
    ws = tmp_path / "ws"
    ws.mkdir()
    src = ws / "src.py"
    src.write_text("print(1)")
    sec = WorkspaceSecurity(ws)
    with pytest.raises(SecurityError) as exc:
        sec.write(src, "evil", revision=None)
    assert exc.value.code == "FILE_READ_ONLY"


def test_writable_allowlist_only_three_design_docs(tmp_path):
    """AC-NFR0201-02: 可编辑清单仅 story/spec/acceptance; 其他设计文档 (test-plan.md) 写入被拒."""
    ws = tmp_path / "ws"
    ws.mkdir()
    sec = WorkspaceSecurity(ws)
    louke_dir = ws / ".louke" / "project" / "specs" / "test-spec"
    louke_dir.mkdir(parents=True)
    for allowed in ("story.md", "spec.md", "acceptance.md"):
        p = louke_dir / allowed
        p.write_text("x")
        rev = sec.write(p, "new content", revision=None)
        assert rev
    other = louke_dir / "test-plan.md"
    other.write_text("x")
    with pytest.raises(SecurityError) as exc:
        sec.write(other, "evil", revision=None)
    assert exc.value.code == "FILE_READ_ONLY"


def test_revision_conflict(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    louke_dir = ws / ".louke" / "project" / "specs" / "test-spec"
    louke_dir.mkdir(parents=True)
    p = louke_dir / "spec.md"
    p.write_text("v1")
    sec = WorkspaceSecurity(ws)
    rev1 = sec.read(p).revision
    p.write_text("v2")
    rev2 = sec.read(p).revision
    assert rev2 != rev1
    with pytest.raises(SecurityError) as exc:
        sec.write(p, "v3", revision=rev1)
    assert exc.value.code == "REVISION_CONFLICT"
