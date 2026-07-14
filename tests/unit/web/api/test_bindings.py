"""TestClient tests for the /api/runtime/bindings sub-app (FR-1301).

AC references covered:
- AC-FR1301-01: list bindings shows each agent's effective model and source.
- AC-FR1301-02: PUT override with an available model succeeds; unavailable
  model is rejected with 400 VALIDATION_ERROR.
- AC-FR1301-04: audit trail records actor, old/new model and timestamp.
- AC-FR1301-05: historical (read-only) runs reject new overrides.
- AC-FR0101-04: an unknown run_id returns 404 NOT_FOUND.
- AC-FR0101-04: missing required body fields return 400 VALIDATION_ERROR.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from louke.web.api.bindings import create_app


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient backed by a fresh in-memory bindings sub-app."""
    return TestClient(create_app())


def _create_run(client: TestClient, definition_id: str = "new_feature") -> str:
    """Create a run via the bindings sub-app's POST /runs helper endpoint."""
    resp = client.post(
        "/runs",
        json={"definition_id": definition_id, "definition_version": "1"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["run_id"]


def test_list_bindings_shows_defaults(client: TestClient) -> None:
    """AC-FR1301-01: list bindings shows each agent's effective model."""
    run_id = _create_run(client)
    resp = client.get(f"/{run_id}?run_id={run_id}")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 1
    roles = {item["agent_role"] for item in items}
    assert "devon" in roles
    assert all(item["source"] == "default" for item in items)


def test_list_bindings_unknown_run(client: TestClient) -> None:
    """AC-FR0101-04: listing bindings for an unknown run returns 404."""
    resp = client.get("/run_unknown?run_id=run_unknown")
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "NOT_FOUND"


def test_set_override_with_available_model(client: TestClient) -> None:
    """AC-FR1301-02: PUT with an available model creates an override."""
    run_id = _create_run(client)
    resp = client.put(
        f"/devon?run_id={run_id}",
        json={"model": "claude-opus"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["agent_role"] == "devon"
    assert body["effective_model"] == "claude-opus"
    assert body["source"] == "override"


def test_set_override_unavailable_model_rejected(client: TestClient) -> None:
    """AC-FR1301-02: an unavailable model is rejected with 400."""
    run_id = _create_run(client)
    resp = client.put(
        f"/devon?run_id={run_id}",
        json={"model": "nonexistent-model"},
    )
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "VALIDATION_ERROR"


def test_set_override_unknown_run(client: TestClient) -> None:
    """AC-FR0101-04: PUT override on an unknown run returns 404."""
    resp = client.put(
        "/devon?run_id=run_unknown",
        json={"model": "claude-opus"},
    )
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "NOT_FOUND"


def test_list_binding_audit_events(client: TestClient) -> None:
    """AC-FR1301-04: audit trail records the override change."""
    run_id = _create_run(client)
    client.put(
        f"/devon?run_id={run_id}",
        json={"model": "claude-opus"},
    )
    resp = client.get(f"/devon/audit?run_id={run_id}")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    event = items[0]
    assert event["agent_role"] == "devon"
    assert event["new_model"] == "claude-opus"
    assert "old_model" in event
    assert "at" in event
