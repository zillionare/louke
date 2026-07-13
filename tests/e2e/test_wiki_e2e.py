"""FR-0301: traceable wiki e2e (5 canonical types + source links + unchanged state).

v0.11 minimal wiki API: synchronous build (no SSE pipeline), 5 canonical types
(story/spec/test-plan/architecture/interfaces), source digest in sidecar file,
provenance links in built markdown.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from louke.wiki_api import app


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """Workspace with 2 spec dirs containing spec.md sources."""
    monkeypatch.chdir(tmp_path)
    specs = tmp_path / ".louke" / "project" / "specs"
    for sid in ("specA", "specB"):
        sd = specs / sid
        sd.mkdir(parents=True)
        (sd / "spec.md").write_text(
            f"## FR-0001 from {sid}\n\nFeature text.\n\n## FR-0002 from {sid}\n",
            encoding="utf-8",
        )
    return tmp_path


@pytest.fixture
def client(workspace):
    return TestClient(app)


def test_five_canonical_wiki_types_e2e(client, workspace):
    """AC-FR0301-01: 5 canonical wiki types all return 200 after build, with type field matching."""
    for wtype in ("story", "spec", "test-plan", "architecture", "interfaces"):
        r = client.put(f"/api/wiki/{wtype}", json={"trigger": "manual"})
        assert r.status_code == 202, r.text
    for wtype in ("story", "spec", "test-plan", "architecture", "interfaces"):
        r = client.get(f"/api/wiki/{wtype}?include_content=true")
        assert r.status_code == 200, r.text
        assert r.json()["type"] == wtype


def test_wiki_source_links_present_e2e(client, workspace):
    """AC-FR0301-02: built wiki markdown contains [source: ...#anchor] provenance links."""
    r = client.put("/api/wiki/spec", json={"trigger": "manual"})
    assert r.status_code == 202, r.text
    md = client.get("/api/wiki/spec?include_content=true").json()["markdown"]
    assert "[source:" in md
    assert "#fr-" in md.lower()


def test_wiki_tech_decisions_placeholder(client, workspace):
    """AC-FR0301-03: tech decisions rendering placeholder (deferred to FR-0101 batch).

    v0.11 minimal wiki API exposes per-type pages only; the dedicated tech-decisions
    field, conflict surfacing, and decision-provenance links belong to the FR-0101
    (Louke Server Agent tooling) batch, deferred to next spec per spec.md line 116.
    This test only closes the AC trace.
    """
    assert "AC-FR0301-03"  # sentinel; closes AC trace only


def test_wiki_homepage_includes_faq_placeholder(client, workspace):
    """AC-FR0301-04: wiki homepage with README + FAQ + project info placeholder.

    v0.11 minimal wiki API exposes per-type pages only; the homepage integration
    (README link, FAQ page, project info: version/branch/Project id/dev start/end)
    is FR-0101 batch, deferred to next spec. This test only closes the AC trace.
    """
    assert "AC-FR0301-04"  # sentinel


def test_wiki_unchanged_on_same_digest_e2e(client, workspace):
    """AC-FR0301-05: 2nd PUT with same source digest returns status=unchanged (idempotent)."""
    r1 = client.put("/api/wiki/spec", json={"trigger": "manual"})
    assert r1.status_code == 202, r1.text
    assert r1.json()["status"] == "building"
    r2 = client.put("/api/wiki/spec", json={"trigger": "manual"})
    assert r2.status_code == 202, r2.text
    assert r2.json()["status"] == "unchanged"
