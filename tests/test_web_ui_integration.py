"""v0.11-002 Batch 1: mount 6 sub-apps into louke/web/app.py + JS client skeleton.

Covers AC-FR0202-01 (six sub-apps reachable via main app) and the JS client
public surface (interfaces.md §7.1). All assertions go through the real
`create_app()` assembly + Starlette TestClient over HTTP, never inspecting
internal route tables (test-plan §4 integration rules).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from louke.web.app import create_app


def _build_project(tmp_path: Path) -> Path:
    """Create a minimal v0.10 project layout under tmp_path for create_app().

    Mirrors tests/test_web_server.py::build_project but kept local to avoid
    cross-test coupling; only the fields create_app() needs to boot are set.
    """
    root = tmp_path
    (root / ".louke" / "project" / "specs" / "demo").mkdir(parents=True)
    (root / ".louke" / "wiki" / "pages").mkdir(parents=True)
    (root / ".louke" / "project" / "project.toml").write_text(
        "[project]\n"
        "version = \"0.11\"\n"
        "repo = \"github.com/zillionare/louke\"\n"
        "project = \"louke-v0.11\"\n"
        'project_id = "https://example.com/p/8"\n'
        "spec_id = \"demo\"\n"
        "release_branch = \"releases/v0.10\"\n"
        "\n[meta]\n"
        "created = \"2026-07-12\"\n"
        "tag = \"v0.11.0\"\n"
        "current_stage = \"M-DEV\"\n"
        "security_audit = \"disabled\"\n"
        "smoke_test_issue = \"#80\"\n"
        "smoke_test_pr = \"#81\"\n"
        'dod = "done"\n'
        "pre_commit = \"installed\"\n"
        "test_framework = \"pytest\"\n",
        encoding="utf-8",
    )
    (root / ".louke" / "project" / "specs" / "demo" / "spec.md").write_text(
        "# Demo\n\n## FR-0100 Demo\n\n| Valid | Testable | Decided |\n"
        "| ----- | -------- | ------- |\n| ✅ | ✅ | ✅ |\n",
        encoding="utf-8",
    )
    (root / ".louke" / "project" / "specs" / "demo" / "acceptance.md").write_text(
        "## FR-0100 Demo\n\n### AC-1\n- works.\n", encoding="utf-8"
    )
    (root / ".louke" / "wiki" / "pages" / "overview.md").write_text(
        "# Overview\n", encoding="utf-8"
    )
    (root / "models.json").write_text(
        '{"$schema":"louke://models-config","version":1,'
        '"aliases":{},"assignments":{"roles":{},"agents":{}}}',
        encoding="utf-8",
    )
    return root


@pytest.fixture
def web_client(tmp_path, monkeypatch):
    """create_app() TestClient with cwd set to the temp project root.

    The six sub-apps resolve their workspace via Path.cwd() (locked v0.11-001
    behaviour), so we chdir into the temp project so file-backed endpoints
    (backlog persistence, wiki sources) operate inside the isolated workspace
    and never touch the real repo.
    """
    root = _build_project(tmp_path)
    monkeypatch.chdir(root)
    client = TestClient(create_app(root))
    client.post("/api/auth/register", json={"username": "Aaron", "password": "secret"})
    return client


# AC-FR0202-01
def test_create_app_mounts_six_subapps(web_client):
    """AC-FR0202-01: the six locked sub-apps are reachable through the same
    main app URL space, not shadowed by page routes / 404.

    One representative endpoint per sub-app is exercised over real HTTP via
    the main create_app() assembly. Status codes reflect the locked v0.11-001
    contracts (201 create / 200 GET / 400 validation / 404 source-missing for
    wiki without specs); the assertion is "handled by the sub-app, not the
    page wildcard", verified by response body shape.
    """
    client = web_client

    # opencode: POST /api/opencode/instances -> 201 Instance
    r = client.post("/api/opencode/instances", json={})
    assert r.status_code == 201, r.text
    assert "id" in r.json() and "status" in r.json()

    # intent: POST /api/intent/route with empty input -> 400 VALIDATION_ERROR
    r = client.post("/api/intent/route", json={"input": ""})
    assert r.status_code == 400
    assert r.json()["error_code"] == "VALIDATION_ERROR"

    # wiki: GET /api/wiki/spec -> 200 (canonical type, sub-app handles it).
    # Build first so the artifact exists; spec.md fixture present in project.
    put = client.put("/api/wiki/spec", json={"trigger": "manual"})
    assert put.status_code == 202
    r = client.get("/api/wiki/spec")
    assert r.status_code == 200, r.text
    assert r.json()["type"] == "spec"

    # backlog: GET /api/backlog -> 200 {entries: [...]}
    r = client.get("/api/backlog")
    assert r.status_code == 200
    assert "entries" in r.json()

    # files: GET /api/files?view=tree -> 200 {view: tree, entries: [...]}
    r = client.get("/api/files?view=tree")
    assert r.status_code == 200
    assert r.json()["view"] == "tree"

    # tasks: GET /api/tasks/FR-0100?document_path=... -> 400 VALIDATION_ERROR
    # when document_path missing (proves the sub-app, not a page, handled it).
    r = client.get("/api/tasks/FR-0100")
    assert r.status_code == 400
    assert r.json()["error_code"] == "VALIDATION_ERROR"


# AC-FR0202-01 (client surface) + interfaces §7.1
def test_louke_client_global_exists():
    """AC-FR0202-01 + interfaces.md §7.1: /assets/client.js defines
    window.LoukeClient with the six namespace submodules and the locked
    method names.

    Parses the static JS source (no browser) for the public surface; the
    runtime fetch behaviour is covered by UI e2e in later batches.
    """
    client_js = Path("louke/web/assets/client.js")
    assert client_js.exists(), "client.js must live at louke/web/assets/client.js"
    src = client_js.read_text(encoding="utf-8")

    # window.LoukeClient assignment
    assert re.search(r"global\.LoukeClient\s*=\s*LoukeClient", src), (
        "client.js must assign window.LoukeClient (interfaces §7.1)"
    )

    # six namespaces
    for ns in ("opencode", "intent", "wiki", "backlog", "files", "tasks"):
        assert re.search(rf"\b{ns}\s*:\s*\{{", src), (
            f"client.js must expose LoukeClient.{ns} namespace"
        )

    # representative method names from interfaces §7.1 table
    expected_methods = {
        "opencode": ("create", "list"),
        "intent": ("route",),
        "wiki": ("get", "build"),
        "backlog": ("list", "create", "start"),
        "files": ("list", "content", "diff", "save"),
        "tasks": ("get", "toggle"),
    }
    for ns, methods in expected_methods.items():
        for m in methods:
            # accept `m: function (`, `m: async function (`, `m: async (`, `m: (`
            assert re.search(
                rf"\b{m}\s*:\s*(async\s+)?(function\s*)?\(", src
            ), f"client.js {ns}.{m} missing (interfaces §7.1)"


# AC-FR0202-01 (static asset served)
def test_louke_client_static_served(web_client):
    """AC-FR0202-01: /assets/client.js is served by the main app at 200 with
    the correct content-type, so page <script src> tags can load it."""
    r = web_client.get("/assets/client.js")
    assert r.status_code == 200
    assert "javascript" in r.headers.get("content-type", "").lower()
    assert "LoukeClient" in r.text


# AC-FR0202-01 (no route regression)
def test_routes_do_not_clash_with_mounts(web_client):
    """AC-FR0202-01: mounting the six sub-apps does not shadow the existing
    v0.10 page routes. /, /login, /health, /models, /wiki and the v0.10 wiki
    page wildcard API all keep their original behaviour."""
    client = web_client

    # /health -> 200 ready schema (not swallowed by a mount)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    # / -> 200 home page (authed)
    r = client.get("/")
    assert r.status_code == 200
    assert "louke Web Workbench" in r.text

    # /models -> 200
    r = client.get("/models")
    assert r.status_code == 200

    # /wiki -> 200 (v0.10 wiki index page, not the sub-app)
    r = client.get("/wiki")
    assert r.status_code == 200

    # v0.10 wiki page wildcard API: /api/wiki/overview -> 200 page payload,
    # NOT the sub-app's WIKI_TYPE_INVALID 400 (architecture §3.1 precedence).
    r = client.get("/api/wiki/overview", headers={"Accept": "application/json"})
    assert r.status_code == 200, r.text
    assert r.json()["page"] == "overview"

    # /login reachable (logout first to avoid the authed redirect)
    client.post("/api/auth/logout")
    r = client.get("/login")
    assert r.status_code == 200
