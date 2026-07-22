"""Live HTTP contracts for v0.14 same-origin mutation enforcement."""

from pathlib import Path
from types import SimpleNamespace

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


def test_story_page_renders_task_bound_chat_over_live_http(tmp_path: Path) -> None:
    """AC-FR0700-01: Story page exposes persisted Scribe facts and Chat controls."""
    client = _client(tmp_path)
    app = client.app
    app.state.v14_release_entry.current_project = lambda project_id: {
        "project_id": project_id,
        "run_id": "run-1",
    }
    app.state.v12_run_store.get_run = lambda run_id: SimpleNamespace(
        run_id=run_id, current_step="M-STORY", revision=2, status="waiting_human"
    )
    app.state.v14_story_entry.artifact = lambda run_id: SimpleNamespace(
        run_id=run_id,
        body_md="# Story\n\nShip the reflow",
        revision=1,
    )
    app.state.v14_scribe_entry.task_for_run = lambda run_id: {"task_id": "task-1"}

    response = client.get("/projects/project-1/requirements/story")

    assert response.status_code == 200
    assert "id='scribe-chat'" in response.text
    assert "Scribe Chat" in response.text
    assert "/messages" in response.text
    assert "Role:" in response.text
    assert "Attempt:" in response.text
    assert "Session:" in response.text
    assert "Connection:" in response.text
    assert "scribe-retry" in response.text
    assert "scribe-reconcile" in response.text
    assert "crypto.randomUUID" in response.text
    assert "Maestro" not in response.text
    assert "<aside" not in response.text


def test_project_path_cannot_borrow_another_project_or_wrong_run(
    tmp_path: Path,
) -> None:
    """AC-FR0600-01: project current lookup requires exact project/run binding."""
    client = _client(tmp_path)
    service = client.app.state.v14_release_entry
    preview = service.preview("Ship the reflow", "v0.14.0")
    service._requests.update(
        preview["request_id"], project_id="project-a", run_id="run-a"
    )

    cross_project = client.get("/api/v14/projects/project-b/current")
    wrong_run = client.get("/api/v14/projects/project-a/current")

    assert cross_project.status_code == 404
    assert wrong_run.status_code == 404


def test_logout_deletes_strict_session_cookie(tmp_path: Path) -> None:
    """AC-NFR0100-01: logout deletion preserves the Strict cookie contract."""
    client = _client(tmp_path)

    response = client.post("/api/auth/logout")

    cookies = response.headers.get_list("set-cookie")
    assert len(cookies) == 1
    assert cookies[0].startswith("louke_session=")
    assert "Max-Age=0" in cookies[0]
    assert "SameSite=strict" in cookies[0]
