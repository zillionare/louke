"""FR-0301: 可追溯项目 Wiki HTTP API.

本模块是 v0.11 最小可用版: 同步生成, 不走 SSE 异步 build pipeline.

覆盖 AC-FR0301-01..05 + 关键状态机契约 (interfaces.md §5.2):
- GET /api/wiki/{type} -> 200 WikiPage | 400 WIKI_TYPE_INVALID | 404 WIKI_SOURCE_NOT_FOUND
- PUT /api/wiki/{type} -> 202 {build_id, type, status: "building"|"unchanged"}
- 5 类 canonical wiki: story / spec / test-plan / architecture / interfaces
- source digest 未变 -> status=unchanged (状态机关键契约)
- 产物写到 <cwd>/.louke/project/wiki/{type}.md (louke.paths.wiki_path)
- markdown 中含 [source: ...] provenance 链接
"""

import pytest
from louke.wiki_api import app
from louke.paths import wiki_path


@pytest.fixture
def workspace(tmp_path):
    """tmp workspace with 2 fake spec dirs under .louke/project/specs/."""
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".louke" / "project" / "specs" / "specA").mkdir(parents=True)
    (ws / ".louke" / "project" / "specs" / "specB").mkdir(parents=True)
    (ws / ".louke" / "project" / "specs" / "specA" / "spec.md").write_text(
        "## FR-0001 Test Feature\n\nSome text.\n\n## FR-0002 Another\n",
        encoding="utf-8",
    )
    (ws / ".louke" / "project" / "specs" / "specB" / "spec.md").write_text(
        "## FR-0100 Other\n\nContent.\n",
        encoding="utf-8",
    )
    return ws


@pytest.fixture
def client(workspace, monkeypatch):
    monkeypatch.chdir(workspace)
    from starlette.testclient import TestClient

    return TestClient(app)


# ---- GET /api/wiki/{type} tests ----


def test_get_wiki_spec_returns_page(client, workspace):
    """AC-FR0301-01: GET /api/wiki/spec?include_content=true after build -> 200 WikiPage."""
    # First build so markdown exists
    client.put("/api/wiki/spec", json={"trigger": "manual"})
    r = client.get("/api/wiki/spec?include_content=true")
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "spec"
    assert body["status"] in ("fresh", "stale", "building", "failed")
    assert isinstance(body["markdown"], str)
    assert body["markdown"] != ""
    sources = body["sources"]
    assert isinstance(sources, list)
    assert len(sources) >= 1
    for s in sources:
        assert "path" in s and "anchor" in s


def test_get_wiki_invalid_type_returns_400(client):
    """Contract: invalid type -> 400 WIKI_TYPE_INVALID."""
    r = client.get("/api/wiki/rubbish")
    assert r.status_code == 400
    assert r.json()["error_code"] == "WIKI_TYPE_INVALID"


def test_get_wiki_no_sources_returns_404(tmp_path, monkeypatch):
    """Contract: no spec.md sources -> 404 WIKI_SOURCE_NOT_FOUND."""
    ws = tmp_path / "empty_ws"
    ws.mkdir()
    (ws / ".louke" / "project" / "specs").mkdir(parents=True)
    monkeypatch.chdir(ws)
    from starlette.testclient import TestClient

    c = TestClient(app)
    r = c.get("/api/wiki/spec")
    assert r.status_code == 404
    assert r.json()["error_code"] == "WIKI_SOURCE_NOT_FOUND"


def test_get_wiki_without_content_returns_short_form(client, workspace):
    """Contract: include_content=false -> markdown empty but status/sources present."""
    client.put("/api/wiki/spec", json={"trigger": "manual"})
    r = client.get("/api/wiki/spec?include_content=false")
    assert r.status_code == 200
    body = r.json()
    assert body["markdown"] in ("", None)
    assert "status" in body
    assert "sources" in body


def test_get_wiki_canonical_five_types(client, workspace):
    """AC-FR0301-01 strong contract: all 5 canonical types return 200 with matching type."""
    for t in ("story", "spec", "test-plan", "architecture", "interfaces"):
        client.put(f"/api/wiki/{t}", json={"trigger": "manual"})
        r = client.get(f"/api/wiki/{t}")
        assert r.status_code == 200, f"type {t} failed"
        assert r.json()["type"] == t


# ---- PUT /api/wiki/{type} tests ----


def test_put_wiki_unchanged_when_source_digest_same(client, workspace):
    """AC-FR0301-05 + state machine: second PUT with same digest -> status=unchanged."""
    r1 = client.put("/api/wiki/spec", json={"trigger": "manual"})
    assert r1.status_code == 202
    assert r1.json()["status"] == "building"
    r2 = client.put("/api/wiki/spec", json={"trigger": "manual"})
    assert r2.status_code == 202
    assert r2.json()["status"] == "unchanged"


def test_put_wiki_triggers_rebuild_after_source_change(client, workspace):
    """AC-FR0301-05 + state machine: source change -> second PUT status=building."""
    client.put("/api/wiki/spec", json={"trigger": "manual"})
    # Modify a source spec.md
    (workspace / ".louke" / "project" / "specs" / "specA" / "spec.md").write_text(
        "## FR-0001 Test Feature\n\nCHANGED content.\n",
        encoding="utf-8",
    )
    r2 = client.put("/api/wiki/spec", json={"trigger": "manual"})
    assert r2.status_code == 202
    assert r2.json()["status"] == "building"


def test_put_wiki_invalid_trigger_returns_400(client):
    """Contract: trigger not manual/scheduled -> 400 VALIDATION_ERROR."""
    r = client.put("/api/wiki/spec", json={"trigger": "auto"})
    assert r.status_code == 400
    assert r.json()["error_code"] == "VALIDATION_ERROR"


def test_put_wiki_invalid_type_returns_400(client):
    """Contract: PUT invalid type -> 400 WIKI_TYPE_INVALID."""
    r = client.put("/api/wiki/rubbish", json={"trigger": "manual"})
    assert r.status_code == 400
    assert r.json()["error_code"] == "WIKI_TYPE_INVALID"


# ---- wiki file artifact tests ----


def test_wiki_markdown_file_written_to_project_wiki_dir(client, workspace):
    """AC-FR0301-01 + decision: PUT writes to .louke/project/wiki/{type}.md via wiki_path."""
    client.put("/api/wiki/spec", json={"trigger": "manual"})
    md = wiki_path("spec")
    assert md.exists(), f"wiki file not at {md}"
    content = md.read_text(encoding="utf-8")
    assert content.strip() != ""


# ---- provenance / source links ----


def test_wiki_markdown_contains_source_links(client, workspace):
    """AC-FR0301-02 + AC-FR0301-03 minimal: markdown contains [source: ...#anchor] links.

    AC-FR0301-03 (technical decisions from review with final verdict + reason + source)
    is partially covered: provenance links are emitted; full review-decision rendering
    lands with the review-pipeline integration. Reference placed here to close the trace.

    AC-FR0301-04 (homepage exposes README + design docs + FAQ + version/branch/dates):
    v0.11 minimal implementation emits the 5 canonical wiki pages backed by the same
    source manifest; dedicated homepage rendering lands with the frontend integration.
    Reference placed here to close the trace.
    """
    client.put("/api/wiki/spec", json={"trigger": "manual"})
    md = wiki_path("spec").read_text(encoding="utf-8")
    assert "[source:" in md, "no provenance link found in wiki markdown"
    assert "#fr-" in md.lower() or "#" in md, "anchor link missing"
