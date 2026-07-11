"""FR-0501: FR/NFR Markdown task state toggle + persistence."""
import pytest
from pathlib import Path
from louke.tasks_api import app


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    spec_dir = ws / ".louke" / "project" / "specs" / "test"
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec.md").write_text(
        "# Test\n\n"
        "| Valid | Testable | Decided |\n"
        "|---|---|---|\n"
        "| ✅ | ⚠️ | ⚠️ |\n\n"
        "- [x] Valid\n"
        "- [ ] Testable\n"
        "- [ ] Decided\n"
    )
    return ws, spec_dir


@pytest.fixture
def client(workspace, monkeypatch):
    ws, _ = workspace
    monkeypatch.chdir(ws)
    from starlette.testclient import TestClient
    return TestClient(app)


def test_get_initial_state(client, workspace):
    ws, spec_dir = workspace
    spec_path = str(spec_dir.relative_to(ws) / "spec.md")
    r = client.get(f"/api/tasks/FR-0001?document_path={spec_path}")
    assert r.status_code == 200
    body = r.json()
    assert body["fr_id"] == "FR-0001"
    assert body["tasks"]["Valid"] is True
    assert body["tasks"]["Testable"] is False
    assert body["tasks"]["Decided"] is False
    assert "revision" in body


def test_toggle_valid_to_unchecked_persists(client, workspace):
    ws, spec_dir = workspace
    spec_path = str(spec_dir.relative_to(ws) / "spec.md")
    # Get initial revision
    r0 = client.get(f"/api/tasks/FR-0001?document_path={spec_path}")
    rev0 = r0.json()["revision"]
    # Toggle Valid off
    r1 = client.patch(
        f"/api/tasks/FR-0001",
        json={"document_path": spec_path, "task": "Valid", "checked": False, "revision": rev0},
    )
    assert r1.status_code == 200
    body = r1.json()
    assert body["tasks"]["Valid"] is False
    # Persisted on disk
    content = (spec_dir / "spec.md").read_text(encoding="utf-8")
    assert "- [ ] Valid" in content
    assert "- [x] Valid" not in content


def test_toggle_testable_to_checked_persists(client, workspace):
    ws, spec_dir = workspace
    spec_path = str(spec_dir.relative_to(ws) / "spec.md")
    r0 = client.get(f"/api/tasks/FR-0001?document_path={spec_path}")
    rev0 = r0.json()["revision"]
    r1 = client.patch(
        f"/api/tasks/FR-0001",
        json={"document_path": spec_path, "task": "Testable", "checked": True, "revision": rev0},
    )
    assert r1.status_code == 200
    assert r1.json()["tasks"]["Testable"] is True
    content = (spec_dir / "spec.md").read_text(encoding="utf-8")
    assert "- [x] Testable" in content


def test_revision_conflict_returns_409(client, workspace):
    ws, spec_dir = workspace
    spec_path = str(spec_dir.relative_to(ws) / "spec.md")
    r1 = client.patch(
        f"/api/tasks/FR-0001",
        json={"document_path": spec_path, "task": "Valid", "checked": False, "revision": "stale-rev"},
    )
    assert r1.status_code == 409


def test_path_outside_workspace_rejected(client):
    r = client.patch(
        f"/api/tasks/FR-0001",
        json={"document_path": "../../../etc/passwd", "task": "Valid", "checked": False, "revision": "x"},
    )
    # NFR-0201 拒绝
    assert r.status_code == 403


def test_non_design_doc_write_rejected(client, workspace):
    """src.py 不在可写 allowlist(只有 story.md/spec.md/acceptance.md),应被拒。"""
    ws, _ = workspace
    (ws / "src.py").write_text("print(1)")
    r = client.patch(
        f"/api/tasks/FR-0001",
        json={"document_path": "src.py", "task": "Valid", "checked": False, "revision": "x"},
    )
    assert r.status_code == 403
