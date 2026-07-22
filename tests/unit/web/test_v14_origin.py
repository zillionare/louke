"""Live HTTP contracts for v0.14 same-origin mutation enforcement."""

from pathlib import Path

from starlette.testclient import TestClient

from louke.web.auth import csrf_token_for_session
from louke.web.app import create_app

from tests.test_web_server import build_project


def _client(tmp_path: Path) -> TestClient:
    """Build an authenticated live HTTP client with a configured origin."""
    client = TestClient(
        create_app(build_project(tmp_path), allowed_origin="https://louke.example")
    )
    assert (
        client.post(
            "/api/auth/register", json={"username": "human", "password": "secret"}
        ).status_code
        == 200
    )
    return client


def _csrf(client: TestClient) -> str:
    """Return the header token derived from the HttpOnly session cookie."""
    session = client.cookies.get("louke_session")
    return csrf_token_for_session(client.app.state.store, session)


def test_cross_origin_release_mutation_is_rejected_before_preview(
    tmp_path: Path,
) -> None:
    """AC-FR0600-03: foreign Origin cannot create or mutate a release request."""
    client = _client(tmp_path)

    response = client.post(
        "/api/v14/releases/preview",
        headers={"Origin": "https://foreign.example", "X-Louke-CSRF": _csrf(client)},
        json={"story": "Ship the reflow", "release_version": "0.14.0"},
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == "ORIGIN_FORBIDDEN"


def test_cross_origin_scribe_mutation_is_rejected_before_task_access(
    tmp_path: Path,
) -> None:
    """AC-FR0600-03: foreign Origin cannot reply to a Scribe task."""
    client = _client(tmp_path)

    response = client.post(
        "/api/v14/runs/run-1/tasks/task-1/messages",
        headers={"Origin": "https://foreign.example", "X-Louke-CSRF": _csrf(client)},
        json={
            "client_message_id": "message-1",
            "correlation_id": "correlation-1",
            "body": "Continue",
            "expected_attempt_id": "attempt-1",
            "expected_artifact_revision": 1,
        },
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == "ORIGIN_FORBIDDEN"
