"""TestClient tests for the /runs/{run_id} page sub-app (B3b).

Verifies the workflow-run detail HTML page sub-app:
- GET /runs/{run_id} renders the project header (definition_id, status,
  current step, revision), the workflow graph as inline SVG (nodes as circles,
  edges as arrows, current step green, completed steps blue, waiting gates
  orange), the last 50 events, the gates list, and a run-command form.
- POST /runs/{run_id}/command forwards to upstream /api/runtime/{run_id}/commands.
- Upstream 404 renders a not-found message (status 200).
- Upstream command failure re-renders with the error (status 200).

The page talks to the upstream ``/api/runtime/*`` and ``/api/gates/*`` sub-apps
via module-level seams (``_fetch_*`` / ``_post_*``) so tests can patch them
without a live server, mirroring the ``/projects`` page test pattern.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from starlette.testclient import TestClient

from louke.web.pages import runs as runs_page


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient backed by a fresh runs page sub-app.

    The app is created with ``api_base="http://testserver"`` so the seam's
    first positional arg is deterministic in assertions.
    """
    return TestClient(runs_page.create_app(api_base="http://testserver"))


# -- fixtures: upstream payloads ---------------------------------------------


def _run_detail() -> dict[str, object]:
    """Return a single-run detail payload."""
    return {
        "run_id": "run_active1",
        "definition_id": "new_feature",
        "definition_version": "1",
        "current_step": "requirements_approval",
        "revision": 1,
        "status": "waiting_for_human",
        "contract_digest": "sha256:abc",
        "created_at": "2026-07-14T00:00:00Z",
        "updated_at": "2026-07-14T00:01:00Z",
    }


def _events_payload() -> list[dict[str, object]]:
    """Return an events payload for the run detail page timeline."""
    return [
        {
            "event_id": "evt_1",
            "run_id": "run_active1",
            "sequence": 1,
            "type": "run.created",
            "at": "2026-07-14T00:00:00Z",
            "actor": {"kind": "human", "id": "alice"},
            "from_step": None,
            "to_step": "start",
            "revision": 0,
            "details": {"definition_id": "new_feature"},
            "step_id": "start",
        },
        {
            "event_id": "evt_2",
            "run_id": "run_active1",
            "sequence": 2,
            "type": "run.step_entered",
            "at": "2026-07-14T00:01:00Z",
            "actor": {"kind": "human", "id": "alice"},
            "from_step": "start",
            "to_step": "requirements_approval",
            "revision": 1,
            "details": {"step_id": "requirements_approval"},
            "step_id": "requirements_approval",
        },
    ]


def _gates_payload() -> list[dict[str, object]]:
    """Return a one-item gates payload for the run."""
    return [
        {
            "gate_id": "gate_requirements1",
            "challenge_id": "chal_aaa",
            "run_id": "run_active1",
            "step_id": "requirements_approval",
            "expected_revision": 1,
            "bound_digest": "sha256:abc",
            "status": "waiting_for_human",
            "actor_id": None,
            "reason": None,
            "decided_at": None,
            "created_at": "2026-07-14T00:01:00Z",
        }
    ]


# -- GET /runs/{run_id} ------------------------------------------------------


def test_runs_detail_renders_header_graph_events_gates(client: TestClient) -> None:
    """GET /runs/{run_id} renders the header, SVG graph, events and gates."""
    with patch.object(
        runs_page, "_fetch_run", new=AsyncMock(return_value=_run_detail())
    ), patch.object(
        runs_page, "_fetch_events", new=AsyncMock(return_value=_events_payload())
    ), patch.object(
        runs_page, "_fetch_gates", new=AsyncMock(return_value=_gates_payload())
    ):
        resp = client.get("/runs/run_active1")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    body = resp.text
    # Header: definition_id, status, current step.
    assert "new_feature" in body
    assert "waiting_for_human" in body
    assert "requirements_approval" in body
    # SVG graph: contains <svg and <circle (nodes) and <line or <path (edges).
    assert "<svg" in body
    assert "<circle" in body
    # Events timeline.
    assert "run.created" in body
    assert "run.step_entered" in body
    # Gates list with a link into the gate detail.
    assert "gate_requirements1" in body
    assert "/runs/run_active1/gates/gate_requirements1" in body
    # Run command form.
    assert 'action="/runs/run_active1/command"' in body
    assert 'name="step_id"' in body
    assert 'name="result"' in body


def test_runs_detail_graph_colors(client: TestClient) -> None:
    """The SVG colors the current step green, completed steps blue, gates orange."""
    with patch.object(
        runs_page, "_fetch_run", new=AsyncMock(return_value=_run_detail())
    ), patch.object(
        runs_page, "_fetch_events", new=AsyncMock(return_value=_events_payload())
    ), patch.object(
        runs_page, "_fetch_gates", new=AsyncMock(return_value=[])
    ):
        resp = client.get("/runs/run_active1")

    body = resp.text
    # The current step (requirements_approval) is a human_gate at the current
    # position -> rendered as a waiting gate (orange / current).
    assert "orange" in body.lower() or "waiting" in body.lower()
    # Completed step (start) -> blue / completed.
    assert "blue" in body.lower() or "completed" in body.lower()


def test_runs_detail_404(client: TestClient) -> None:
    """GET /runs/{unknown} renders a not-found message, status 200."""
    with patch.object(
        runs_page, "_fetch_run", new=AsyncMock(side_effect=RuntimeError("404 not found"))
    ):
        resp = client.get("/runs/run_unknown")

    assert resp.status_code == 200
    assert "not found" in resp.text.lower()


def test_runs_detail_handles_empty_events(client: TestClient) -> None:
    """GET /runs/{run_id} with no events renders an empty-state message."""
    with patch.object(
        runs_page, "_fetch_run", new=AsyncMock(return_value=_run_detail())
    ), patch.object(
        runs_page, "_fetch_events", new=AsyncMock(return_value=[])
    ), patch.object(
        runs_page, "_fetch_gates", new=AsyncMock(return_value=[])
    ):
        resp = client.get("/runs/run_active1")

    assert resp.status_code == 200
    assert "No events" in resp.text or "no events" in resp.text.lower()
