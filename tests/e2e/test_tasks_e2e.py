"""FR-0501: FR/NFR task toggle e2e (3 independent checkboxes + roundtrip + non-pollution)."""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from louke.tasks_api import app


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """Workspace with a spec.md containing 3 task checkboxes (Valid/Testable/Decided)."""
    monkeypatch.chdir(tmp_path)
    sd = tmp_path / ".louke" / "project" / "specs" / "demo"
    sd.mkdir(parents=True)
    (sd / "spec.md").write_text(
        "## FR-0001\n\n- [ ] Valid\n- [ ] Testable\n- [ ] Decided\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def client(workspace):
    return TestClient(app)


def test_three_independent_task_checkboxes_e2e(client, workspace):
    """AC-FR0501-01: PATCH /api/tasks/{fr_id} toggles Valid/Testable/Decided independently in the file."""
    spec_rel = ".louke/project/specs/demo/spec.md"
    r = client.patch("/api/tasks/FR-0001", json={
        "document_path": spec_rel, "task": "Valid", "checked": True,
    })
    assert r.status_code == 200, r.text
    text = (workspace / spec_rel).read_text()
    assert "- [x] Valid" in text
    assert "- [ ] Testable" in text
    assert "- [ ] Decided" in text


def test_task_save_roundtrip_e2e(client, workspace):
    """AC-FR0501-02: PATCH then GET shows correct - [x] / - [ ] state across all 3 tasks."""
    spec_rel = ".louke/project/specs/demo/spec.md"
    client.patch("/api/tasks/FR-0001", json={
        "document_path": spec_rel, "task": "Testable", "checked": True,
    })
    tasks = client.get(f"/api/tasks/FR-0001?document_path={spec_rel}").json()["tasks"]
    assert tasks["Testable"] is True
    assert tasks["Valid"] is False
    assert tasks["Decided"] is False


def test_single_task_change_does_not_pollute_others_e2e(client, workspace):
    """AC-FR0501-03: changing 1 task does not affect other tasks' state in the same file."""
    spec_rel = ".louke/project/specs/demo/spec.md"
    client.patch("/api/tasks/FR-0001", json={
        "document_path": spec_rel, "task": "Decided", "checked": True,
    })
    text = (workspace / spec_rel).read_text()
    assert "- [x] Decided" in text
    assert "- [ ] Valid" in text
    assert "- [ ] Testable" in text