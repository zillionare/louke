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
    assert "Beyond Vibes, Into Craft" in login.text
    assert "超越氛围编程" in login.text
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


def test_scan_discussion_blocks_detects_resolved_markers() -> None:
    """Verify the discussion scanner finds both open and resolved discussion lines.

    The JS filter/next-discussion buttons in the Vditor editor use the same
    matching rules as scan_discussion_blocks(). This test exercises the
    Python side so the logic is locked down: any regression here also breaks
    the browser filter.
    """
    from louke.web.render import scan_discussion_blocks

    sample = (
        "# v0.10 demo\n"
        "\n"
        "### FR-0100 Demo\n"
        "\n"
        "> [T-001] > **[Aaron]** First open comment\n"
        "> [T-001] >> **[Bob]** reply\n"
        "> [T-001] > status: open\n"
        "\n"
        "### FR-0200 Resolved demo\n"
        "\n"
        "> [T-002] > **[resolved] Aaron:** test\n"
        "> [T-002] > ✓ resolved\n"
        "> [T-002] > **[已决定] Lex:** done\n"
    )
    blocks = scan_discussion_blocks(sample)

    discussion_lines = [b for b in blocks if b["line"] > 0]
    assert len(discussion_lines) == 6, f"expected 6 discussion lines, got {len(discussion_lines)}: {blocks}"

    resolved = [b for b in blocks if b["resolved"]]
    open_blocks = [b for b in blocks if not b["resolved"]]

    # Lines containing resolved markers
    assert any("resolved] Aaron" in r["text"] for r in resolved)
    assert any("✓ resolved" in r["text"] for r in resolved)
    assert any("已决定" in r["text"] for r in resolved)

    # Open discussion lines
    assert any("First open comment" in o["text"] for o in open_blocks)
    assert any("reply" in o["text"] for o in open_blocks)
    assert any("status: open" in o["text"] for o in open_blocks)


def test_doc_page_renders_brand_and_spec_selector(tmp_path: Path) -> None:
    """Verify the sidebar shows Lòukè brand and a spec selector with all specs."""
    root = build_project(tmp_path)
    spec_dir = root / ".louke" / "project" / "specs" / "demo"
    second = root / ".louke" / "project" / "specs" / "v0.10-001-vditor-redesign"
    second.mkdir(parents=True)
    (second / "spec.md").write_text("# v0.10\n", encoding="utf-8")
    (second / "acceptance.md").write_text("## v0.10\n", encoding="utf-8")

    client = TestClient(create_app(root))
    register = client.post("/api/auth/register", json={"username": "Aaron", "password": "secret"})
    assert register.status_code == 200

    doc = client.get("/docs/demo/spec")
    assert doc.status_code == 200
    body = doc.text
    # Brand should show Lòukè, not 'louke / web'
    assert "Lòukè" in body
    assert "louke / web" not in body
    # Spec selector should list both specs
    assert "v0.10-001-vditor-redesign" in body
    assert "demo" in body
    # Configured spec (demo) takes precedence over auto-select
    assert 'value="demo" selected' in body
    # And the v0.10 spec is present in the dropdown (even if not selected)
    assert '<option value="v0.10-001-vditor-redesign"' in body
    # Last Saved prefix on the time display
    assert "Last Saved:" in body
    # Save time placeholder
    assert "Last Saved: --:--:--" in body


def test_resolve_spec_id_picks_highest_version(tmp_path: Path) -> None:
    """resolve_spec_id() falls back to the highest-version spec when project.toml
    points to a missing directory, and respects the configured spec if present."""
    root = build_project(tmp_path)
    (root / ".louke" / "project" / "specs" / "v0.10-001-vditor-redesign").mkdir(parents=True)
    (root / ".louke" / "project" / "specs" / "v0.8-001-web-server").mkdir(parents=True)

    from louke.web.store import ProjectStore
    store = ProjectStore(root)

    # Configured spec ("demo") exists -> return it
    assert store.resolve_spec_id() == "demo"

    # Remove configured spec; should auto-pick the highest version
    import shutil
    shutil.rmtree(root / ".louke" / "project" / "specs" / "demo")
    assert store.resolve_spec_id() == "v0.10-001-vditor-redesign"


def test_doc_page_collapses_and_filters_discussions(tmp_path: Path) -> None:
    """Verify the collapse and filter CSS classes and the next-discussion
    handler are wired into the doc editor page."""
    root = build_project(tmp_path)
    spec_md = root / ".louke" / "project" / "specs" / "demo" / "spec.md"
    spec_md.write_text(
        "# Demo\n\n"
        "### FR-0100\n\n"
        "> [T-001] > **[Aaron]** open comment\n"
        "> [T-001] > **[resolved] Aaron:** resolved comment\n",
        encoding="utf-8",
    )
    client = TestClient(create_app(root))
    client.post("/api/auth/register", json={"username": "Aaron", "password": "secret"})

    doc = client.get("/docs/demo/spec")
    assert doc.status_code == 200
    body = doc.text
    # Filter/collapse CSS rules: hide [data-resolved] and [data-discussion]
    assert "[data-resolved=\"1\"]" in body
    assert "[data-discussion=\"1\"]" in body
    # nextDiscussion handler present
    assert "nextDiscussion" in body
    assert "isResolvedText" in body
    assert "isDiscussionText" in body
    # The spec.md content is loaded into Vditor via JS; we verify the API
    # serves the discussion lines instead of the rendered HTML.
    api = client.get("/api/docs/demo/spec")
    assert api.status_code == 200
    data = api.json()
    assert "open comment" in data["body_md"]
    assert "resolved comment" in data["body_md"]


def test_sidebar_collapse_releases_space(tmp_path: Path) -> None:
    """Verify the sidebar collapse CSS actually releases the 280px column.

    Regression: the sidebar div had min-width: auto (the CSS grid default),
    so even with grid-template-columns: 0 the sidebar kept its content
    width and the right pane got no extra room.
    """
    root = build_project(tmp_path)
    client = TestClient(create_app(root))
    client.post("/api/auth/register", json={"username": "Aaron", "password": "secret"})

    doc = client.get("/docs/demo/spec")
    assert doc.status_code == 200
    body = doc.text
    # Collapsed state collapses the grid track to 0
    assert "grid-template-columns: 0" in body
    # The sidebar div must allow itself to shrink to that 0px track
    # (min-width: 0 on the grid item is the key fix; without it, the
    # grid item's content min-width keeps it at 280px+ even when the
    # track is 0).
    assert "min-width: 0" in body
    # When collapsed, the sidebar div is explicitly sized to 0 so it
    # cannot leak into the right pane.
    assert "width: 0" in body


def test_pane_layout_allows_flex_shrink(tmp_path: Path) -> None:
    """Verify the pane layout CSS allows flex shrinking so adding panes
    doesn't squash existing ones to "one character per line".

    Regression: previously min-width:520px + flex:1 1 0 caused content
    to wrap at every character when panes couldn't all fit at 520px.
    """
    root = build_project(tmp_path)
    client = TestClient(create_app(root))
    client.post("/api/auth/register", json={"username": "Aaron", "password": "secret"})

    doc = client.get("/docs/demo/spec")
    assert doc.status_code == 200
    body = doc.text
    # The pane rule must allow flex-shrink (no fixed min-width that
    # forces per-character wrapping when N panes overflow the container).
    assert "flex: 1 1 0;" in body
    assert "min-width: 0;" in body
    # The container must allow horizontal overflow rather than crushing
    # pane content into single-character columns.
    assert "overflow-x: auto;" in body
    # The single-pane case keeps a comfortable reading width
    # (~720px) centered in the workspace.
    assert "pane:only-child" in body
    assert "max-width: 720px" in body
    # Doc pages have IDs on workspace / workspace-inner so JS can
    # toggle the pane-host class dynamically (NOT applied by default
    # — only when 2+ panes are open, or a single pane cannot reach
    # the 50 Chinese-char reading-width threshold).
    assert 'id="workspace"' in body
    assert 'id="workspace-inner"' in body
    # The pane-host CSS rule must exist (reclaims padding + max-width)
    # but is NOT applied unconditionally to doc pages.
    assert ".pane-host" in body
    assert "max-width: none" in body
    # Split icon is now an SVG background image on the .icon-split CSS class.
    assert "icon-split" in body
    assert "data:image/svg+xml" in body
    # The default <main> markup should NOT have pane-host baked in.
    assert 'class="workspace pane-host"' not in body
