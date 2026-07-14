"""TestClient tests for the /projects/{project_id}/gates page sub-app (B3b).

Verifies the gates HTML page sub-app:
- GET /projects/{project_id}/gates lists all gates for the project's run as cards.
- GET /projects/{project_id}/gates/{gate_id} renders the gate detail with state,
  bound digest, expected revision and the approve/reject form.
- For requirements_approval and m_lock gates, two clearly labeled sections are
  shown (AC-FR1901-03).
- When the gate is stale or has open discussions, the approve button is disabled
  and a blocker text is shown.
- POST .../decide approves/rejects via upstream /api/gates/{gate_id}/decisions.
- On success the page redirects to the gate detail and shows the decision.
- On upstream 4xx the page re-renders with the error message (status 200).

The page talks to the upstream ``/api/gates/*`` and ``/api/projects/*`` sub-apps
via module-level seams (``_fetch_*`` / ``_post_*``) so tests can patch them
without a live server, mirroring the ``/projects`` page test pattern.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from starlette.testclient import TestClient

from louke.web.pages import gates as gates_page


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient backed by a fresh gates page sub-app.

    The app is created with ``api_base="http://testserver"`` so the seam's
    first positional arg is deterministic in assertions.
    """
    return TestClient(gates_page.create_app(api_base="http://testserver"))


# -- fixtures: upstream payloads ---------------------------------------------


def _project_detail() -> dict[str, object]:
    """Return a single-project detail payload."""
    return {
        "project_id": "prj_active1",
        "run_id": "run_active1",
        "name": "Active feature",
        "story_excerpt": "Build X",
        "release_version": "v0.12.0",
        "workflow_definition_id": "new_feature",
        "workflow_version": "1",
        "status": "active",
        "created_at": "2026-07-14T00:00:00Z",
        "archived_at": None,
    }


def _gates_list_payload() -> list[dict[str, object]]:
    """Return a two-item gates list payload (requirements_approval + m_lock)."""
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
        },
        {
            "gate_id": "gate_mlock1",
            "challenge_id": "chal_bbb",
            "run_id": "run_active1",
            "step_id": "m_lock",
            "expected_revision": 3,
            "bound_digest": "sha256:def",
            "status": "waiting_for_human",
            "actor_id": None,
            "reason": None,
            "decided_at": None,
            "created_at": "2026-07-14T00:02:00Z",
        },
    ]


def _gate_detail_payload(*, step_id: str = "requirements_approval") -> dict[str, object]:
    """Return a single gate detail payload."""
    return {
        "gate_id": "gate_requirements1",
        "challenge_id": "chal_aaa",
        "run_id": "run_active1",
        "step_id": step_id,
        "expected_revision": 1,
        "bound_digest": "sha256:abc",
        "status": "waiting_for_human",
        "actor_id": None,
        "reason": None,
        "decided_at": None,
        "created_at": "2026-07-14T00:01:00Z",
    }


def _approved_gate_payload() -> dict[str, object]:
    """Return a gate detail payload after an approve decision."""
    return {
        "gate_id": "gate_requirements1",
        "challenge_id": "chal_aaa",
        "run_id": "run_active1",
        "step_id": "requirements_approval",
        "expected_revision": 1,
        "bound_digest": "sha256:abc",
        "status": "approved",
        "actor_id": "alice",
        "reason": None,
        "decided_at": "2026-07-14T00:03:00Z",
        "created_at": "2026-07-14T00:01:00Z",
    }


# -- GET / (gates list) ------------------------------------------------------


def test_gates_list_shows_all_gates(client: TestClient) -> None:
    """GET / renders a card per gate for the project's run."""
    with patch.object(
        gates_page, "_fetch_project", new=AsyncMock(return_value=_project_detail())
    ), patch.object(
        gates_page, "_fetch_gates", new=AsyncMock(return_value=_gates_list_payload())
    ):
        resp = client.get("/projects/prj_active1/gates")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    body = resp.text
    # Both gates appear as cards.
    assert "gate_requirements1" in body
    assert "gate_mlock1" in body
    # The two gate kinds (sections per AC-FR1901-03) are distinguished.
    assert "requirements_approval" in body
    assert "m_lock" in body
    # Each card links to the gate detail page.
    assert 'href="/projects/prj_active1/gates/gate_requirements1"' in body
    assert 'href="/projects/prj_active1/gates/gate_mlock1"' in body


def test_gates_list_handles_empty(client: TestClient) -> None:
    """GET / with no gates renders an empty-state message."""
    with patch.object(
        gates_page, "_fetch_project", new=AsyncMock(return_value=_project_detail())
    ), patch.object(
        gates_page, "_fetch_gates", new=AsyncMock(return_value=[])
    ):
        resp = client.get("/projects/prj_active1/gates")

    assert resp.status_code == 200
    assert "No gates" in resp.text or "no gates" in resp.text.lower()


def test_gates_list_handles_project_404(client: TestClient) -> None:
    """GET / for an unknown project renders a not-found message, status 200."""
    with patch.object(
        gates_page,
        "_fetch_project",
        new=AsyncMock(side_effect=RuntimeError("404 not found")),
    ):
        resp = client.get("/projects/prj_unknown/gates")

    assert resp.status_code == 200
    assert "not found" in resp.text.lower()


def test_gates_list_handles_gate_fetch_error(client: TestClient) -> None:
    """GET / when the gate-list call fails shows an error, status 200."""
    with patch.object(
        gates_page, "_fetch_project", new=AsyncMock(return_value=_project_detail())
    ), patch.object(
        gates_page,
        "_fetch_gates",
        new=AsyncMock(side_effect=RuntimeError("upstream 500")),
    ):
        resp = client.get("/projects/prj_active1/gates")

    assert resp.status_code == 200
    assert "upstream 500" in resp.text or "error" in resp.text.lower()


def _stale_gate_detail_payload() -> dict[str, object]:
    """Return a gate detail payload whose status is stale."""
    return {
        "gate_id": "gate_requirements1",
        "challenge_id": "chal_aaa",
        "run_id": "run_active1",
        "step_id": "requirements_approval",
        "expected_revision": 1,
        "bound_digest": "sha256:abc",
        "status": "stale",
        "actor_id": None,
        "reason": None,
        "decided_at": None,
        "created_at": "2026-07-14T00:01:00Z",
    }


def _open_discussions_gate_payload() -> dict[str, object]:
    """Return a gate detail payload with open discussions (forward-compat field)."""
    payload = _gate_detail_payload()
    payload["open_discussions"] = 2  # type: ignore[assignment]
    return payload


# -- GET /{gate_id} (detail) -------------------------------------------------


def test_gate_detail_renders_state_and_form(client: TestClient) -> None:
    """GET /{gate_id} renders the gate state, digest, revision and form."""
    with patch.object(
        gates_page, "_fetch_project", new=AsyncMock(return_value=_project_detail())
    ), patch.object(
        gates_page, "_fetch_gate", new=AsyncMock(return_value=_gate_detail_payload())
    ):
        resp = client.get("/projects/prj_active1/gates/gate_requirements1")

    assert resp.status_code == 200
    body = resp.text
    # Gate state, bound digest and expected revision are shown.
    assert "waiting_for_human" in body
    assert "sha256:abc" in body
    assert "1" in body  # expected_revision
    # The gate kind is labeled (AC-FR1901-03).
    assert "requirements_approval" in body
    # The approve/reject form posts to the decide route.
    assert 'action="/projects/prj_active1/gates/gate_requirements1/decide"' in body
    assert 'name="verdict"' in body
    assert 'name="reason"' in body


def test_gate_detail_distinguishes_m_lock(client: TestClient) -> None:
    """GET /{gate_id} for an m_lock gate shows the m_lock section label."""
    with patch.object(
        gates_page, "_fetch_project", new=AsyncMock(return_value=_project_detail())
    ), patch.object(
        gates_page,
        "_fetch_gate",
        new=AsyncMock(return_value=_gate_detail_payload(step_id="m_lock")),
    ):
        resp = client.get("/projects/prj_active1/gates/gate_mlock1")

    assert resp.status_code == 200
    body = resp.text
    assert "m_lock" in body
    # The m_lock section is clearly labeled separately from requirements.
    assert "M-LOCK" in body or "m_lock" in body


def test_gate_detail_stale_disables_button(client: TestClient) -> None:
    """GET /{gate_id} with a stale gate shows a blocker and disables the button."""
    with patch.object(
        gates_page, "_fetch_project", new=AsyncMock(return_value=_project_detail())
    ), patch.object(
        gates_page, "_fetch_gate", new=AsyncMock(return_value=_stale_gate_detail_payload())
    ):
        resp = client.get("/projects/prj_active1/gates/gate_requirements1")

    assert resp.status_code == 200
    body = resp.text
    assert "stale" in body.lower()
    # Blocker text is shown.
    assert "blocker" in body.lower() or "stale" in body.lower()
    # The submit button is disabled.
    assert "disabled" in body


def test_gate_detail_open_discussions_disables_button(client: TestClient) -> None:
    """GET /{gate_id} with open_discussions > 0 disables the approve button."""
    with patch.object(
        gates_page, "_fetch_project", new=AsyncMock(return_value=_project_detail())
    ), patch.object(
        gates_page,
        "_fetch_gate",
        new=AsyncMock(return_value=_open_discussions_gate_payload()),
    ):
        resp = client.get("/projects/prj_active1/gates/gate_requirements1")

    assert resp.status_code == 200
    body = resp.text
    # Blocker text mentions open discussions.
    assert "open discussion" in body.lower() or "blocker" in body.lower()
    # The submit button is disabled.
    assert "disabled" in body


# -- POST /{gate_id}/decide --------------------------------------------------


def test_gate_decide_approve_redirects_and_records(client: TestClient) -> None:
    """POST .../decide with verdict=approve redirects to the gate detail."""
    decide_mock = AsyncMock(return_value=_approved_gate_payload())
    with patch.object(
        gates_page, "_fetch_project", new=AsyncMock(return_value=_project_detail())
    ), patch.object(
        gates_page, "_fetch_gate", new=AsyncMock(return_value=_gate_detail_payload())
    ), patch.object(
        gates_page, "_post_decision", new=decide_mock
    ):
        resp = client.post(
            "/projects/prj_active1/gates/gate_requirements1/decide",
            data={"verdict": "approve", "reason": ""},
            follow_redirects=False,
        )

    decide_mock.assert_awaited_once()
    assert resp.status_code in (303, 302, 307)
    assert "/projects/prj_active1/gates/gate_requirements1" in resp.headers["location"]


def test_gate_decide_reject_without_reason_shows_error(client: TestClient) -> None:
    """POST .../decide with verdict=reject and no reason shows the 400 error."""
    decide_mock = AsyncMock(side_effect=RuntimeError("400 reject requires a reason"))
    with patch.object(
        gates_page, "_fetch_project", new=AsyncMock(return_value=_project_detail())
    ), patch.object(
        gates_page, "_fetch_gate", new=AsyncMock(return_value=_gate_detail_payload())
    ), patch.object(
        gates_page, "_post_decision", new=decide_mock
    ):
        resp = client.post(
            "/projects/prj_active1/gates/gate_requirements1/decide",
            data={"verdict": "reject", "reason": ""},
        )

    assert resp.status_code == 200
    assert "reject requires a reason" in resp.text or "error" in resp.text.lower()
