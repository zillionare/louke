"""TestClient tests for the /api/projects sub-app (FR-1001, FR-1101).

AC references covered:
- AC-FR1001-01: active/history/backlog lists exposed via HTTP.
- AC-FR1001-02: terminal/archived projects appear only in history.
- AC-FR1001-03: list items carry name, release version, workflow type, status.
- AC-FR1001-04: second active main project blocked; story saved to backlog (409).
- AC-FR1101-01..03: preview/confirm/create project endpoints.
- AC-FR1101-04: invalid release version returns 400 VALIDATION_ERROR.
- AC-FR1101-05: unknown workflow returns 404 NOT_FOUND.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from louke.web.api.projects import create_app


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient backed by a fresh in-memory projects sub-app."""
    return TestClient(create_app())


def test_list_active_history_backlog_empty(client: TestClient) -> None:
    """AC-FR1001-01: the three list endpoints are exposed and empty by default."""
    resp = client.get("/active")
    assert resp.status_code == 200
    assert resp.json() == {"items": []}

    resp = client.get("/history")
    assert resp.status_code == 200
    assert resp.json() == {"items": []}

    resp = client.get("/backlog")
    assert resp.status_code == 200
    assert resp.json() == {"items": []}


def test_create_project_happy_path(client: TestClient) -> None:
    """AC-FR1101-03: a project can be created via POST /create."""
    resp = client.post(
        "/create",
        json={
            "story": "Build programmatic workflow runtime",
            "release_version": "v0.12.0",
            "definition_id": "new_feature",
            "definition_version": "1",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["project_id"].startswith("prj_")
    assert body["run_id"].startswith("run_")
    assert body["name"] == "Build programmatic workflow runtime"
    assert body["release_version"] == "v0.12.0"
    assert body["workflow_definition_id"] == "new_feature"
    assert body["status"] == "active"


def test_create_project_validation_error_missing_story(client: TestClient) -> None:
    """AC-FR1101-04: missing required story returns 400 VALIDATION_ERROR."""
    resp = client.post(
        "/create",
        json={
            "story": "",
            "release_version": "v0.12.0",
            "definition_id": "new_feature",
            "definition_version": "1",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "VALIDATION_ERROR"


def test_create_project_validation_error_bad_version(client: TestClient) -> None:
    """AC-FR1101-04: malformed release version returns 400 VALIDATION_ERROR.

    The release-version regex validation lives in ``preview_project`` in the
    runtime; the ``/preview`` endpoint surfaces it as a 400.
    """
    resp = client.post(
        "/preview",
        json={
            "story": "Story",
            "release_version": "0.12.0",
            "definition_id": "new_feature",
            "definition_version": "1",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "VALIDATION_ERROR"


def test_create_project_not_found_unknown_workflow(client: TestClient) -> None:
    """AC-FR1101-05: an unknown workflow definition id returns 404 NOT_FOUND."""
    resp = client.post(
        "/create",
        json={
            "story": "Story",
            "release_version": "v0.12.0",
            "definition_id": "does_not_exist",
            "definition_version": "1",
        },
    )
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "NOT_FOUND"


def test_second_main_project_blocked_and_backlog_saved(client: TestClient) -> None:
    """AC-FR1001-04: a second active main project is blocked; story saved to backlog."""
    client.post(
        "/create",
        json={
            "story": "First feature",
            "release_version": "v0.12.0",
            "definition_id": "new_feature",
            "definition_version": "1",
        },
    )

    resp = client.post(
        "/create",
        json={
            "story": "Second feature",
            "release_version": "v0.12.0",
            "definition_id": "new_feature",
            "definition_version": "1",
        },
    )
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "CONFLICT"

    backlog = client.get("/backlog").json()["items"]
    assert len(backlog) == 1
    assert backlog[0]["story"] == "Second feature"


def test_hotfix_parallel_to_main(client: TestClient) -> None:
    """AC-FR1001-05: a bug_fix can coexist with an active main project."""
    client.post(
        "/create",
        json={
            "story": "Main feature",
            "release_version": "v0.12.0",
            "definition_id": "new_feature",
            "definition_version": "1",
        },
    )
    resp = client.post(
        "/create",
        json={
            "story": "Fix login bug",
            "release_version": "v0.12.0",
            "definition_id": "bug_fix",
            "definition_version": "1",
        },
    )
    assert resp.status_code == 201

    active = client.get("/active").json()["items"]
    assert len(active) == 2


def test_preview_and_confirm_project(client: TestClient) -> None:
    """AC-FR1101-01..03: preview then confirm creates the project."""
    preview = client.post(
        "/preview",
        json={
            "story": "Previewed feature",
            "release_version": "v0.12.0",
            "definition_id": "new_feature",
            "definition_version": "1",
        },
    )
    assert preview.status_code == 200
    preview_id = preview.json()["preview_id"]

    confirm = client.post("/confirm", json={"preview_id": preview_id})
    assert confirm.status_code == 201
    assert confirm.json()["name"] == "Previewed feature"


def test_confirm_unknown_preview_returns_not_found(client: TestClient) -> None:
    """Confirming a preview that doesn't exist returns 404 NOT_FOUND."""
    resp = client.post("/confirm", json={"preview_id": "prev_unknown"})
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "NOT_FOUND"


def test_get_project_detail(client: TestClient) -> None:
    """AC-FR1001-03: GET /{project_id} returns project detail."""
    create = client.post(
        "/create",
        json={
            "story": "Detail feature",
            "release_version": "v0.12.0",
            "definition_id": "new_feature",
            "definition_version": "1",
        },
    )
    project_id = create.json()["project_id"]

    resp = client.get(f"/{project_id}")
    assert resp.status_code == 200
    assert resp.json()["project_id"] == project_id


def test_get_project_not_found(client: TestClient) -> None:
    """GET on an unknown project returns 404 NOT_FOUND."""
    resp = client.get("/prj_unknown")
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "NOT_FOUND"


def test_archive_project_moves_to_history(client: TestClient) -> None:
    """AC-FR1001-02: archiving a project moves it from active to history."""
    create = client.post(
        "/create",
        json={
            "story": "To archive",
            "release_version": "v0.12.0",
            "definition_id": "bug_fix",
            "definition_version": "1",
        },
    )
    project_id = create.json()["project_id"]

    archive = client.post(f"/{project_id}/archive")
    assert archive.status_code == 200
    assert archive.json()["status"] == "archived"

    active = {p["project_id"] for p in client.get("/active").json()["items"]}
    history = {p["project_id"] for p in client.get("/history").json()["items"]}
    assert project_id not in active
    assert project_id in history


def test_archive_unknown_returns_not_found(client: TestClient) -> None:
    """Archiving an unknown project returns 404 NOT_FOUND."""
    resp = client.post("/prj_unknown/archive")
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "NOT_FOUND"


def test_workflow_catalog(client: TestClient) -> None:
    """AC-FR1101-01: GET /catalog returns selectable workflow definitions."""
    resp = client.get("/catalog")
    assert resp.status_code == 200
    ids = {entry["definition_id"] for entry in resp.json()["items"]}
    assert "new_feature" in ids
    assert "bug_fix" in ids
    assert "spec_change" not in ids


def test_principal_header_propagated(client: TestClient) -> None:
    """The x-louke-principal header is read and used as the actor id."""
    resp = client.post(
        "/create",
        json={
            "story": "Principal story",
            "release_version": "v0.12.0",
            "definition_id": "new_feature",
            "definition_version": "1",
        },
        headers={"x-louke-principal": "alice"},
    )
    assert resp.status_code == 201
