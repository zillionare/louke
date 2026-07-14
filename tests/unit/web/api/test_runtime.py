"""TestClient tests for the /api/runtime sub-app (FR-0001, FR-0101, FR-0201, FR-0601, FR-2001).

AC references covered:
- AC-FR0001-01: a workflow run can be created via POST /runs.
- AC-FR0101-01: runtime is the sole writer of run state.
- AC-FR0201-01: persisted run can be retrieved via GET /runs/{id}.
- AC-FR0601-01: events for a run can be listed via GET /runs/{id}/events.
- AC-FR2001-01: a needs_attention run can be recovered via POST /runs/{id}/recover.
- AC-FR0101-02: applying a command advances the run (apply_command).
- AC-FR0101-03: a stale expected_revision returns 409 STALE.
- AC-FR0101-04: an unknown run id returns 404 NOT_FOUND.
- AC-FR0101-05: missing required body fields return 400 VALIDATION_ERROR.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from louke.web.api.runtime import create_app


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient backed by a fresh in-memory runtime sub-app."""
    return TestClient(create_app())


def _create_run(client: TestClient, definition_id: str = "new_feature") -> dict:
    """Helper: create a run and return the response body."""
    resp = client.post(
        "/runs",
        json={
            "definition_id": definition_id,
            "definition_version": "1",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_run_happy_path(client: TestClient) -> None:
    """AC-FR0001-01: a workflow run can be created via POST /runs."""
    body = _create_run(client)
    assert body["run_id"].startswith("run_")
    assert body["definition_id"] == "new_feature"
    assert body["definition_version"] == "1"
    assert body["revision"] == 0
    assert body["status"] == "in_progress"
    assert body["current_step"] == "start"


def test_create_run_validation_error_missing_definition_id(client: TestClient) -> None:
    """AC-FR0101-05: missing definition_id returns 400 VALIDATION_ERROR."""
    resp = client.post("/runs", json={"definition_version": "1"})
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "VALIDATION_ERROR"


def test_create_run_unknown_definition(client: TestClient) -> None:
    """AC-FR0101-04: an unknown workflow definition returns 404 NOT_FOUND."""
    resp = client.post(
        "/runs",
        json={"definition_id": "does_not_exist", "definition_version": "1"},
    )
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "NOT_FOUND"


def test_get_run_detail(client: TestClient) -> None:
    """AC-FR0201-01: a persisted run can be retrieved via GET /runs/{id}."""
    created = _create_run(client)
    resp = client.get(f"/runs/{created['run_id']}")
    assert resp.status_code == 200
    assert resp.json()["run_id"] == created["run_id"]


def test_get_run_not_found(client: TestClient) -> None:
    """AC-FR0101-04: GET on an unknown run returns 404 NOT_FOUND."""
    resp = client.get("/runs/run_unknown")
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "NOT_FOUND"


def test_list_run_events(client: TestClient) -> None:
    """AC-FR0601-01: events for a run can be listed via GET /runs/{id}/events."""
    created = _create_run(client)
    resp = client.get(f"/runs/{created['run_id']}/events")
    assert resp.status_code == 200
    events = resp.json()["items"]
    assert len(events) >= 1
    assert events[0]["type"] == "run.created"


def test_list_run_events_unknown_run(client: TestClient) -> None:
    """AC-FR0601-01: listing events for an unknown run returns 404 NOT_FOUND."""
    resp = client.get("/runs/run_unknown/events")
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "NOT_FOUND"


def test_apply_command_advances_run(client: TestClient) -> None:
    """AC-FR0101-02: applying a command with a valid result advances the run."""
    created = _create_run(client)
    run_id = created["run_id"]
    expected_revision = created["revision"]

    resp = client.post(
        f"/runs/{run_id}/commands",
        json={
            "expected_revision": expected_revision,
            "result": "done",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["run"]["run_id"] == run_id
    assert body["run"]["current_step"] == "requirements_approval"
    assert body["run"]["revision"] == 1
    assert body["event"]["type"] == "step.transition"


def test_apply_command_stale_revision(client: TestClient) -> None:
    """AC-FR0101-03: a stale expected_revision returns 409 STALE."""
    created = _create_run(client)
    run_id = created["run_id"]
    # Advance once
    client.post(
        f"/runs/{run_id}/commands",
        json={"expected_revision": 0, "result": "done"},
    )
    # Now try with the stale revision 0
    resp = client.post(
        f"/runs/{run_id}/commands",
        json={"expected_revision": 0, "result": "done"},
    )
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "STALE"


def test_apply_command_unknown_run(client: TestClient) -> None:
    """AC-FR0101-04: applying a command to an unknown run returns 404 NOT_FOUND."""
    resp = client.post(
        "/runs/run_unknown/commands",
        json={"expected_revision": 0, "result": "done"},
    )
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "NOT_FOUND"


def test_apply_command_validation_error_missing_result(client: TestClient) -> None:
    """AC-FR0101-05: applying a command without a result returns 400."""
    created = _create_run(client)
    resp = client.post(
        f"/runs/{created['run_id']}/commands",
        json={"expected_revision": 0},
    )
    # The runtime raises IllegalTransitionError ("no step result provided")
    # which maps to 400 VALIDATION_ERROR.
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "VALIDATION_ERROR"


def test_recover_run_no_op_when_no_uncertain_attempts(client: TestClient) -> None:
    """AC-FR2001-01: recover returns the unchanged run when no uncertain attempts."""
    created = _create_run(client)
    resp = client.post(f"/runs/{created['run_id']}/recover")
    assert resp.status_code == 200
    assert resp.json()["run_id"] == created["run_id"]
    assert resp.json()["status"] == "in_progress"


def test_recover_run_unknown(client: TestClient) -> None:
    """AC-FR2001-01: recovering an unknown run returns 404 NOT_FOUND."""
    resp = client.post("/runs/run_unknown/recover")
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "NOT_FOUND"


def test_list_runs(client: TestClient) -> None:
    """AC-FR0201-01: GET /runs lists all persisted runs."""
    _create_run(client)
    _create_run(client, definition_id="bug_fix")
    resp = client.get("/runs")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2
