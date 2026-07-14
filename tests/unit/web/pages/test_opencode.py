"""TestClient tests for the /opencode page sub-app (B6).

Verifies the opencode HTML page sub-app:
- GET / lists instances with an adapter_kind banner (mock yellow vs real green).
- GET /{instance_id} renders the chat view: messages + send form + Stop button.
- POST /new creates an instance and redirects to its chat view.
- Upstream errors are rendered on the page (status 200), never 500.

The page talks to the upstream ``/api/opencode/*`` sub-app via module-level
seams (``_fetch_*`` / ``_post_*``) so tests can patch them without a live
server, mirroring the ``/projects`` and ``/gates`` page test patterns.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from starlette.testclient import TestClient

from louke.web.pages import opencode as opencode_page


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient backed by a fresh opencode page sub-app.

    The app is created with ``api_base="http://testserver"`` so the seam's
    first positional arg is deterministic.
    """
    return TestClient(opencode_page.create_app(api_base="http://testserver"))


# -- fixtures: upstream payloads ---------------------------------------------


def _status_mock() -> dict[str, object]:
    """Return a status payload with adapter_kind=mock."""
    return {"adapter_kind": "mock"}


def _status_real() -> dict[str, object]:
    """Return a status payload with adapter_kind=real."""
    return {"adapter_kind": "real"}


def _instances_payload() -> dict[str, object]:
    """Return a two-item instances list payload."""
    return {
        "items": [
            {
                "id": "inst_aaa",
                "status": "running",
                "created_at": "2026-07-14T00:00:00Z",
            },
            {
                "id": "inst_bbb",
                "status": "stopped",
                "created_at": "2026-07-14T00:01:00Z",
            },
        ]
    }


def _messages_payload() -> dict[str, object]:
    """Return a three-item messages list payload."""
    return {
        "items": [
            {
                "role": "user",
                "kind": "text",
                "content": "Hello",
                "created_at": "2026-07-14T00:00:00Z",
            },
            {
                "role": "assistant",
                "kind": "text",
                "content": "Hi there",
                "created_at": "2026-07-14T00:00:01Z",
            },
            {
                "role": "user",
                "kind": "text",
                "content": "How are you?",
                "created_at": "2026-07-14T00:00:02Z",
            },
        ]
    }


# -- GET / (index) -----------------------------------------------------------


def test_opencode_index_lists_instances_with_mock_banner(client: TestClient) -> None:
    """GET / lists instances and shows the yellow mock-backend banner."""
    with patch.object(
        opencode_page, "_fetch_status", new=AsyncMock(return_value=_status_mock())
    ), patch.object(
        opencode_page, "_fetch_instances", new=AsyncMock(return_value=_instances_payload())
    ):
        resp = client.get("/")

    assert resp.status_code == 200
    body = resp.text
    # Both instance cards appear.
    assert "inst_aaa" in body
    assert "inst_bbb" in body
    # The mock-backend warning banner element is shown (not just the CSS rule).
    assert '<div class="banner-mock">' in body
    assert "Mock backend:" in body
    assert "messages echo" in body


def test_opencode_index_lists_instances_with_real_backend_no_banner(
    client: TestClient,
) -> None:
    """GET / with adapter_kind=real shows the real banner, NOT the mock banner."""
    with patch.object(
        opencode_page, "_fetch_status", new=AsyncMock(return_value=_status_real())
    ), patch.object(
        opencode_page, "_fetch_instances", new=AsyncMock(return_value=_instances_payload())
    ):
        resp = client.get("/")

    assert resp.status_code == 200
    body = resp.text
    # The mock warning banner element is NOT shown (CSS rule is always present,
    # so we check the element + user-visible text instead of the class name).
    assert '<div class="banner-mock">' not in body
    assert "Mock backend:" not in body
    assert "messages echo" not in body
    # The real backend banner IS shown.
    assert '<div class="banner-real">' in body
    assert "Real backend:" in body


def test_opencode_index_handles_empty(client: TestClient) -> None:
    """GET / with no instances renders the empty-state message."""
    with patch.object(
        opencode_page, "_fetch_status", new=AsyncMock(return_value=_status_mock())
    ), patch.object(
        opencode_page, "_fetch_instances", new=AsyncMock(return_value={"items": []})
    ):
        resp = client.get("/")

    assert resp.status_code == 200
    assert "No instances" in resp.text


# -- GET /{instance_id} (chat) -----------------------------------------------


def test_opencode_chat_shows_messages_and_form(client: TestClient) -> None:
    """GET /{instance_id} renders messages, send form, and Stop button."""
    with patch.object(
        opencode_page, "_fetch_messages", new=AsyncMock(return_value=_messages_payload())
    ):
        resp = client.get("/inst_aaa")

    assert resp.status_code == 200
    body = resp.text
    # All three messages are rendered.
    assert "Hello" in body
    assert "Hi there" in body
    assert "How are you?" in body
    # The send-message form posts to the upstream messages API.
    assert 'action="/api/opencode/instances/inst_aaa/messages"' in body
    # The Stop button is present.
    assert "Stop" in body


def test_opencode_chat_stop_button_calls_abort(client: TestClient) -> None:
    """GET /{instance_id} renders the Stop button form posting to the abort endpoint.

    The page has no ``/{instance_id}/stop`` route; the Stop button form posts
    directly to the upstream ``/api/opencode/instances/{id}/abort`` API.
    """
    with patch.object(
        opencode_page, "_fetch_messages", new=AsyncMock(return_value=_messages_payload())
    ):
        resp = client.get("/inst_aaa")

    assert resp.status_code == 200
    body = resp.text
    # The Stop button form posts to the upstream abort API.
    assert 'action="/api/opencode/instances/inst_aaa/abort"' in body
    assert "Stop" in body


def test_opencode_chat_handles_upstream_error_gracefully(client: TestClient) -> None:
    """GET /{instance_id} when the messages fetch fails shows an error, status 200."""
    with patch.object(
        opencode_page,
        "_fetch_messages",
        new=AsyncMock(side_effect=RuntimeError("upstream 500")),
    ):
        resp = client.get("/inst_aaa")

    assert resp.status_code == 200
    assert "upstream 500" in resp.text


# -- POST /new ---------------------------------------------------------------


def test_opencode_new_creates_and_redirects(client: TestClient) -> None:
    """POST /new creates an instance and redirects to its chat view."""
    create_mock = AsyncMock(return_value={"instance": {"id": "inst_new"}})
    with patch.object(opencode_page, "_post_create_instance", new=create_mock):
        resp = client.post("/new", follow_redirects=False)

    create_mock.assert_awaited_once()
    assert resp.status_code in (303, 302, 307)
    assert "/opencode/inst_new" in resp.headers["location"]
