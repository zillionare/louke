from __future__ import annotations

import json
from pathlib import Path

from starlette.testclient import TestClient

from louke.serve import _resolve_project_root
from louke.web.auth import SESSION_COOKIE
from louke.web.app import create_app


def build_project(tmp_path: Path) -> Path:
    root = tmp_path
    (root / ".louke" / "project" / "specs" / "demo").mkdir(parents=True)
    (root / ".louke" / "wiki" / "pages").mkdir(parents=True)
    (root / ".louke" / "wiki" / "pages" / "guides").mkdir(parents=True)
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
    (root / ".louke" / "wiki" / "pages" / "guides" / "getting-started.md").write_text(
        "# Getting Started\n\n- nested page\n",
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


def authenticate(client: TestClient, username: str = "Aaron", password: str = "secret") -> None:
    response = client.post("/api/auth/register", json={"username": username, "password": password})
    assert response.status_code == 200


def test_health_and_home_page(tmp_path: Path) -> None:
    root = build_project(tmp_path)
    client = TestClient(create_app(root))
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "spec_id": "demo"}
    login = client.get("/login")
    assert login.status_code == 200
    assert "Min Square_97" in login.text
    assert "/assets/min-square_97-snk-X32c8tE-unsplash.jpg" in login.text
    assert "Beyond Vibes, Into Craft (Louke)" in login.text
    # No Accept-Language header -> fall back to English
    assert "Sign In" in login.text
    assert "登录" not in login.text
    asset = client.get("/assets/min-square_97-snk-X32c8tE-unsplash.jpg")
    assert asset.status_code == 200
    guest = client.get("/", follow_redirects=False)
    assert guest.status_code == 303
    assert guest.headers["location"].startswith("/login")
    authenticate(client)
    home = client.get("/")
    assert home.status_code == 200
    # No header -> English fallback
    assert "Model Bindings" in home.text
    assert "Design Docs" in home.text
    assert "wiki" in home.text
    assert "Aaron" in home.text

    home_en = client.get("/", headers={"accept-language": "en-US,en;q=0.9"})
    assert home_en.status_code == 200
    assert "Model Bindings" in home_en.text
    assert "Design Docs" in home_en.text
    assert "Log Out" in home_en.text

    login_en = TestClient(create_app(root)).get("/login", headers={"accept-language": "en-US,en;q=0.9"})
    assert login_en.status_code == 200
    assert "Sign In" in login_en.text
    assert "Register &amp; Sign In" in login_en.text

    # Explicit Chinese
    home_zh = client.get("/", headers={"accept-language": "zh-CN,zh;q=0.9"})
    assert home_zh.status_code == 200
    assert "模型绑定" in home_zh.text
    assert "设计文档" in home_zh.text
    assert "退出" in home_zh.text

    login_zh = TestClient(create_app(root)).get("/login", headers={"accept-language": "zh-CN,zh;q=0.9"})
    assert login_zh.status_code == 200
    assert "登录" in login_zh.text
    assert "注册并登录" in login_zh.text

    # Unsupported language (French) -> fall back to English
    home_fr = client.get("/", headers={"accept-language": "fr-FR,fr;q=0.9"})
    assert home_fr.status_code == 200
    assert "Model Bindings" in home_fr.text
    assert "模型绑定" not in home_fr.text


def test_register_login_logout_flow(tmp_path: Path) -> None:
    root = build_project(tmp_path)
    client = TestClient(create_app(root))

    register = client.post("/api/auth/register", json={"username": "Aaron", "password": "secret"})
    assert register.status_code == 200
    assert register.json()["username"] == "Aaron"
    assert SESSION_COOKIE in register.cookies

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 200

    denied = client.get("/api/bindings")
    assert denied.status_code == 401

    login = client.post("/api/auth/login", json={"username": "Aaron", "password": "secret"})
    assert login.status_code == 200
    assert login.json()["username"] == "Aaron"

    models = client.get("/api/bindings")
    assert models.status_code == 200


def test_doc_roundtrip_and_conflict(tmp_path: Path) -> None:
    root = build_project(tmp_path)
    client = TestClient(create_app(root))
    authenticate(client)

    response = client.get("/api/docs/demo/spec")
    assert response.status_code == 200
    payload = response.json()
    assert "<table>" in payload["rendered_html"]
    assert payload["cards"][0]["id"] == "FR-0100"

    saved = client.put(
        "/api/docs/demo/spec",
        json={
            "body_md": payload["body_md"] + "\nNew line.\n",
            "version_token": payload["version_token"],
        },
    )
    assert saved.status_code == 200
    assert saved.json()["last_modified_by"] == "Aaron"
    assert "New line." in (root / ".louke" / "project" / "specs" / "demo" / "spec.md").read_text(encoding="utf-8")

    stale = client.put(
        "/api/docs/demo/spec",
        json={
            "body_md": "stale write\n",
            "version_token": payload["version_token"],
        },
    )
    assert stale.status_code == 409


def test_wiki_roundtrip(tmp_path: Path) -> None:
    root = build_project(tmp_path)
    client = TestClient(create_app(root))
    authenticate(client)

    response = client.get("/api/wiki/overview", headers={"Accept": "application/json"})
    assert response.status_code == 200
    payload = response.json()
    assert "<ul>" in payload["rendered_html"]

    saved = client.put(
        "/api/wiki/overview",
        json={
            "body_md": payload["body_md"] + "\n## Extra\n\nText\n",
            "version_token": payload["version_token"],
        },
    )
    assert saved.status_code == 200
    assert saved.json()["last_modified_by"] == "Aaron"

    nested = client.get("/api/wiki/guides/getting-started", headers={"Accept": "application/json"})
    assert nested.status_code == 200
    assert nested.json()["page"] == "guides/getting-started"

    page = client.get("/wiki/guides/getting-started")
    assert page.status_code == 200
    assert "guides" in page.text
    assert "getting-started" in page.text


def test_bindings_get_and_put(tmp_path: Path) -> None:
    root = build_project(tmp_path)
    client = TestClient(create_app(root))
    authenticate(client)

    response = client.get("/api/bindings")
    assert response.status_code == 200
    payload = response.json()
    assert payload["resolved"]["roles"]["A"]["abstract"] == "minimax-m3"
    assert "Sage" in payload["resolved"]["agents"]

    saved = client.put(
        "/api/bindings",
        json={
            "version_token": payload["version_token"],
            "aliases": payload["aliases"],
            "assignments": {
                "roles": {"A": "minimax-m3", "B": "deepseek-v4-flash"},
                "agents": {"Sage": "glm-5.2"},
            },
        },
    )
    assert saved.status_code == 200
    data = json.loads((root / ".louke" / "models.json").read_text(encoding="utf-8"))
    assert data["assignments"]["roles"]["B"] == "deepseek-v4-flash"
    assert data["assignments"]["agents"]["Sage"] == "glm-5.2"


def test_discussion_mutation_writes_markdown(tmp_path: Path) -> None:
    root = build_project(tmp_path)
    client = TestClient(create_app(root))
    authenticate(client)

    doc = client.get("/api/docs/demo/spec").json()
    created = client.post(
        "/api/discussions/mutate",
        json={
            "target_kind": "doc",
            "target_path": doc["path"],
            "version_token": doc["version_token"],
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
    client.post("/api/auth/logout")
    register_bob = client.post("/api/auth/register", json={"username": "Bob", "password": "hunter2"})
    assert register_bob.status_code == 200
    replied = client.post(
        "/api/discussions/mutate",
        json={
            "target_kind": "doc",
            "target_path": created_payload["path"],
            "version_token": created_payload["version_token"],
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


def test_resolve_project_root_searches_upward(tmp_path: Path, monkeypatch) -> None:
    root = build_project(tmp_path)
    nested = root / "sub" / "dir"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    assert _resolve_project_root("") == root.resolve()
