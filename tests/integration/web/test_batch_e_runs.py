"""Black-box contract checks for the Batch E Runs presentation."""

from __future__ import annotations

import json
from pathlib import Path

from starlette.testclient import TestClient

from louke.web.app import create_app


FIXTURE = Path(__file__).parents[2] / "fixtures" / "runs" / "project_active.json"


def _client(tmp_path: Path) -> TestClient:
    project = tmp_path / ".louke" / "project"
    project.mkdir(parents=True)
    (project / "project.toml").write_text(
        "[project]\nspec_id='fixture'\n", encoding="utf-8"
    )
    (project / "runs.json").write_text(
        FIXTURE.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return TestClient(create_app(tmp_path))


def test_runs_sidebar_lists_projects(tmp_path: Path) -> None:
    """AC-FR1313-01: Runs lists current and historical fixture projects."""
    response = _client(tmp_path).get("/workbench")
    assert response.status_code == 200
    assert 'data-testid="runs-sidebar"' in response.text
    assert 'data-testid="runs-project-project-active"' in response.text
    assert 'data-testid="runs-project-project-history"' in response.text


def test_runs_workflow_graph_renders(tmp_path: Path) -> None:
    """AC-FR1313-02/04, AC-FR1314-01/02/03: graph nodes expose badges."""
    client = _client(tmp_path)
    graph = client.get("/api/ui/runs/run-active/graph")
    assert graph.status_code == 200
    payload = graph.json()
    assert [node["stage_id"] for node in payload["nodes"]] == [
        "author",
        "review",
        "gate",
    ]
    html = client.get("/workbench").text
    assert 'data-testid="runs-graph"' in html
    assert 'data-testid="runs-node-author"' in html
    assert 'data-testid="badge-done"' in html


def test_stage_node_click_opens_artifact_detail(tmp_path: Path) -> None:
    """AC-FR1315-01/02/03: artifact detail is read-only and has four fields."""
    client = _client(tmp_path)
    artifact = client.get("/api/ui/runs/run-active/stages/review/artifact")
    assert artifact.status_code == 200
    body = artifact.json()
    assert body["digest"] == "abc123"
    assert body["verdict"] == "PASS"
    assert body["required_reviewer"] == "Prism"
    assert body["review_conclusion"] == "Looks good"
    assert "Save" not in client.get("/workbench").text


def test_stage_unknown_kind_fallback(tmp_path: Path) -> None:
    """AC-FR1316-01/03/04: unknown result values are explicit fallbacks."""
    client = _client(tmp_path)
    runs = json.loads((tmp_path / ".louke" / "project" / "runs.json").read_text())
    runs["graphs"]["run-active"]["nodes"].append(
        {
            "stage_id": "future_stage",
            "label": "future_stage",
            "state": "future_status",
            "result": json.loads(
                (
                    Path(__file__).parents[2]
                    / "fixtures"
                    / "runs"
                    / "stage_result_unknown_kind.json"
                ).read_text()
            ),
        }
    )
    (tmp_path / ".louke" / "project" / "runs.json").write_text(json.dumps(runs))
    payload = client.get("/api/ui/runs/run-active/graph").json()
    unknown = payload["nodes"][-1]
    assert unknown["unknown"] is True
    assert unknown["badges"][0]["display_label"]
    assert any(badge["value"] == "unknown_thing_xyz" for badge in unknown["badges"])
    assert any(badge["unknown"] for badge in unknown["badges"])


def test_badge_mapping_correct() -> None:
    """AC-FR1314-02/03: stage-result values map to approved labels."""
    from louke.web.runs.badges import badges_for_result

    assert (
        badges_for_result({"kind": "review", "verdict": "PASS"})[0]["display_label"]
        == "approved"
    )
    assert (
        badges_for_result({"kind": "gate", "verdict": "fail"})[0]["display_label"]
        == "blocked"
    )
    assert (
        badges_for_result({"kind": "author", "outcome": "running"})[0]["display_label"]
        == "running"
    )
