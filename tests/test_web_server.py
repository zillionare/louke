from __future__ import annotations

import json
from pathlib import Path

from starlette.testclient import TestClient

from louke.web.app import create_app


def build_project(tmp_path: Path) -> Path:
    root = tmp_path
    (root / ".louke" / "project" / "specs" / "demo").mkdir(parents=True)
    (root / ".louke" / "wiki" / "pages").mkdir(parents=True)
    (root / ".louke" / "project" / "project.toml").write_text(
        """
[project]
version = "0.8"
repo = "github.com/example/louke"
project = "louke-v0.8"
project_id = "https://example.com/project/8"
spec_id = "demo"
release_branch = "releases/v0.8"

[meta]
created = "2026-07-08"
tag = "v0.7.3"
current_stage = "M-ARCH"
security_audit = "disabled"
smoke_test_issue = "#80"
smoke_test_pr = "#81"
dod = "done"
pre_commit = "installed"
test_framework = "pytest"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (root / ".louke" / "project" / "specs" / "demo" / "spec.md").write_text(
        """
# Demo Spec

## 3. 功能需求

### FR-0100 Demo requirement

| Valid | Testable | Decided |
| ----- | -------- | ------- |
| ✅     | ✅        | ✅       |

支持代码块、表格和列表。

```python
print("hello")
```
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (root / ".louke" / "project" / "specs" / "demo" / "acceptance.md").write_text(
        "## FR-0100 Demo requirement\n\n### AC-1\n- Works.\n",
        encoding="utf-8",
    )
    (root / ".louke" / "project" / "specs" / "demo" / "test-plan.md").write_text(
        "## Plan\n\n- test\n",
        encoding="utf-8",
    )
    (root / ".louke" / "wiki" / "pages" / "overview.md").write_text(
        "# Overview\n\n- first item\n- second item\n",
        encoding="utf-8",
    )
    (root / ".louke" / "models.json").write_text(
        json.dumps(
            {
                "$schema": "louke://models-config",
                "version": 1,
                "aliases": {"minimax-m3": "ark/minimax-m3"},
                "assignments": {"roles": {"A": "minimax-m3"}, "agents": {}},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return root


def test_health_and_home_page(tmp_path: Path) -> None:
    root = build_project(tmp_path)
    client = TestClient(create_app(root))
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "spec_id": "demo"}
    home = client.get("/")
    assert home.status_code == 200
    assert "模型绑定" in home.text
    assert "设计文档" in home.text


def test_doc_roundtrip_and_conflict(tmp_path: Path) -> None:
    root = build_project(tmp_path)
    client = TestClient(create_app(root))

    response = client.get("/api/docs/demo/spec")
    assert response.status_code == 200
    payload = response.json()
    assert "<table>" in payload["rendered_html"]
    assert payload["cards"][0]["id"] == "FR-0100"

    saved = client.put(
        "/api/docs/demo/spec",
        headers={"X-Louke-Actor": "Aaron"},
        json={
            "body_md": payload["body_md"] + "\nNew line.\n",
            "version_token": payload["version_token"],
            "actor_name": "Aaron",
        },
    )
    assert saved.status_code == 200
    assert saved.json()["last_modified_by"] == "Aaron"
    assert "New line." in (root / ".louke" / "project" / "specs" / "demo" / "spec.md").read_text(encoding="utf-8")

    stale = client.put(
        "/api/docs/demo/spec",
        headers={"X-Louke-Actor": "Bob"},
        json={
            "body_md": "stale write\n",
            "version_token": payload["version_token"],
            "actor_name": "Bob",
        },
    )
    assert stale.status_code == 409


def test_wiki_roundtrip(tmp_path: Path) -> None:
    root = build_project(tmp_path)
    client = TestClient(create_app(root))

    response = client.get("/api/wiki/overview", headers={"Accept": "application/json"})
    assert response.status_code == 200
    payload = response.json()
    assert "<ul>" in payload["rendered_html"]

    saved = client.put(
        "/api/wiki/overview",
        headers={"X-Louke-Actor": "Aaron"},
        json={
            "body_md": payload["body_md"] + "\n## Extra\n\nText\n",
            "version_token": payload["version_token"],
            "actor_name": "Aaron",
        },
    )
    assert saved.status_code == 200
    assert saved.json()["last_modified_by"] == "Aaron"


def test_bindings_get_and_put(tmp_path: Path) -> None:
    root = build_project(tmp_path)
    client = TestClient(create_app(root))

    response = client.get("/api/bindings")
    assert response.status_code == 200
    payload = response.json()
    assert payload["resolved"]["roles"]["A"]["abstract"] == "minimax-m3"
    assert "Sage" in payload["resolved"]["agents"]

    saved = client.put(
        "/api/bindings",
        headers={"X-Louke-Actor": "Aaron"},
        json={
            "version_token": payload["version_token"],
            "aliases": payload["aliases"],
            "assignments": {
                "roles": {"A": "minimax-m3", "B": "deepseek-v4-flash"},
                "agents": {"Sage": "glm-5.2"},
            },
            "actor_name": "Aaron",
        },
    )
    assert saved.status_code == 200
    data = json.loads((root / ".louke" / "models.json").read_text(encoding="utf-8"))
    assert data["assignments"]["roles"]["B"] == "deepseek-v4-flash"
    assert data["assignments"]["agents"]["Sage"] == "glm-5.2"


def test_discussion_mutation_writes_markdown(tmp_path: Path) -> None:
    root = build_project(tmp_path)
    client = TestClient(create_app(root))

    doc = client.get("/api/docs/demo/spec").json()
    created = client.post(
        "/api/discussions/mutate",
        headers={"X-Louke-Actor": "Aaron"},
        json={
            "target_kind": "doc",
            "target_path": doc["path"],
            "version_token": doc["version_token"],
            "actor_name": "Aaron",
            "action": "start",
            "anchor": {"anchor_line": 8},
            "payload": {"body": "需要补充降级策略"},
        },
    )
    assert created.status_code == 200
    created_payload = created.json()
    assert created_payload["discussion_threads"]
    content = (root / ".louke" / "project" / "specs" / "demo" / "spec.md").read_text(encoding="utf-8")
    assert "> **Aaron**: 需要补充降级策略" in content

    thread = created_payload["discussion_threads"][0]
    replied = client.post(
        "/api/discussions/mutate",
        headers={"X-Louke-Actor": "Bob"},
        json={
            "target_kind": "doc",
            "target_path": created_payload["path"],
            "version_token": created_payload["version_token"],
            "actor_name": "Bob",
            "action": "reply",
            "anchor": {"anchor_line": thread["anchor_line"]},
            "payload": {
                "thread_id": thread["thread_id"],
                "body": "已收到",
                "anchor_line": thread["anchor_line"],
                "anchor_text": thread["anchor_text"],
                "root_line": thread["root_line"],
                "root_text": thread["root_text"],
            },
        },
    )
    assert replied.status_code == 200
    content = (root / ".louke" / "project" / "specs" / "demo" / "spec.md").read_text(encoding="utf-8")
    assert ">> **Bob**: 已收到" in content
