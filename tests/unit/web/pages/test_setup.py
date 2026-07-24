"""TestClient tests for the /setup page sub-app (FR-0101 Setup Wizard).

The Wizard has step-by-step routes:
  GET  /setup/                        -> redirects to current step page
  GET  /setup/identity/               -> identity step (first-user form)
  POST /setup/identity/complete        -> advance to repository
  GET  /setup/repository/             -> repository step
  POST /setup/repository/complete     -> record init/clone and advance
  GET  /setup/dependencies/           -> readiness report
  POST /setup/dependencies/complete   -> advance to review
  GET  /setup/review/                 -> review summary
  POST /setup/review/complete         -> advance to applying
  GET  /setup/applying/               -> apply step (stub)
  GET  /setup/complete/               -> completion page
  POST /setup/first-user              -> legacy first-user submission
  POST /setup/return/<step>           -> rewind to prior step
  POST /setup/reset                   -> clear wizard state
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from starlette.testclient import TestClient

from louke.web.pages import setup as setup_page


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient backed by a fresh setup page sub-app."""
    return TestClient(setup_page.create_app())


def _ready_payload() -> list[dict[str, str]]:
    """Return a readiness payload where every check is READY."""
    return [
        {"name": "Git", "status": "READY", "diagnosis": "ok", "remediation": "none"},
        {"name": "Store", "status": "READY", "diagnosis": "ok", "remediation": "none"},
        {
            "name": "Catalog",
            "status": "READY",
            "diagnosis": "ok",
            "remediation": "none",
        },
        {
            "name": "OpenCode",
            "status": "READY",
            "diagnosis": "ok",
            "remediation": "none",
        },
        {
            "name": "Models",
            "status": "READY",
            "diagnosis": "default-model",
            "remediation": "none",
        },
    ]


def _blocked_payload() -> list[dict[str, str]]:
    """Return a readiness payload where at least one check is BLOCKED."""
    return [
        {"name": "Git", "status": "READY", "diagnosis": "ok", "remediation": "none"},
        {"name": "Store", "status": "READY", "diagnosis": "ok", "remediation": "none"},
        {
            "name": "Catalog",
            "status": "BLOCKED",
            "diagnosis": "missing",
            "remediation": "run X",
        },
        {
            "name": "OpenCode",
            "status": "BLOCKED",
            "diagnosis": "no adapter",
            "remediation": "wait B4",
        },
        {
            "name": "Models",
            "status": "READY",
            "diagnosis": "default-model",
            "remediation": "none",
        },
    ]


# -- Root redirect ----------------------------------------------------------


def test_root_redirects_to_identity_when_no_first_user(client: TestClient) -> None:
    """GET /setup/ with no first user renders the identity form."""
    with patch.object(
        setup_page,
        "_fetch_setup_status",
        new=AsyncMock(return_value={"initialized": False, "first_principal_id": None}),
    ):
        resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 200
    assert "First user" in resp.text
    assert 'name="name"' in resp.text
    assert 'name="credential"' in resp.text


def test_root_redirects_to_current_step_when_initialized(client: TestClient) -> None:
    """GET /setup/ with first user present redirects to the current step."""
    with (
        patch.object(
            setup_page,
            "_fetch_setup_status",
            new=AsyncMock(
                return_value={
                    "initialized": True,
                    "first_principal_id": "prin_abc",
                }
            ),
        ),
        patch.object(setup_page, "_read_persisted_state", return_value={}),
    ):
        resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (303, 302, 307)
    assert resp.headers["location"].endswith("/setup/identity/")


# -- Identity step ----------------------------------------------------------


def test_identity_step_renders_first_user_form(client: TestClient) -> None:
    """GET /setup/identity/ shows the first-user form when not initialized."""
    with patch.object(
        setup_page,
        "_fetch_setup_status",
        new=AsyncMock(return_value={"initialized": False, "first_principal_id": None}),
    ):
        resp = client.get("/identity/", follow_redirects=False)
    assert resp.status_code == 200
    assert "First user" in resp.text
    assert 'name="name"' in resp.text
    assert 'name="credential"' in resp.text


def test_identity_step_shows_completion_when_initialized(client: TestClient) -> None:
    """GET /setup/identity/ with first user shows the identity-done panel."""
    with (
        patch.object(
            setup_page,
            "_fetch_setup_status",
            new=AsyncMock(
                return_value={
                    "initialized": True,
                    "first_principal_id": "prin_abc",
                }
            ),
        ),
        patch.object(setup_page, "_read_persisted_state", return_value={}),
    ):
        resp = client.get("/identity/", follow_redirects=False)
    assert resp.status_code == 200
    assert "Identity established" in resp.text or "first principal" in resp.text.lower()


# -- Repository step --------------------------------------------------------


def test_repository_step_renders_init_clone_form(client: TestClient) -> None:
    """GET /setup/repository/ renders the init/clone choice form."""
    with patch.object(setup_page, "_read_persisted_state", return_value={}):
        resp = client.get("/repository/")
    assert resp.status_code == 200
    body = resp.text
    assert 'name="mode"' in body
    assert 'value="init"' in body
    assert 'value="clone"' in body
    assert 'name="remote_url"' in body


def test_repository_complete_advances_to_dependencies(client: TestClient) -> None:
    """POST /setup/repository/complete with mode=init advances the wizard."""
    with (
        patch.object(
            setup_page,
            "_read_persisted_state",
            return_value={
                "current_step": "repository",
                "completed_steps": ["identity"],
                "blocking_items": [],
                "selections": {},
            },
        ),
        patch.object(setup_page, "_persist_state", return_value=True),
    ):
        resp = client.post(
            "/repository/complete",
            data={"mode": "init", "remote_url": ""},
            follow_redirects=False,
        )
    assert resp.status_code in (303, 302, 307)
    assert resp.headers["location"].endswith("/setup/dependencies/")


def test_repository_complete_rejects_clone_without_url(client: TestClient) -> None:
    """POST /setup/repository/complete with clone but no URL returns 400."""
    with patch.object(
        setup_page,
        "_read_persisted_state",
        return_value={
            "current_step": "repository",
            "completed_steps": ["identity"],
            "blocking_items": [],
            "selections": {},
        },
    ):
        resp = client.post(
            "/repository/complete",
            data={"mode": "clone", "remote_url": ""},
        )
    assert resp.status_code == 400


def test_repository_complete_rejects_invalid_mode(client: TestClient) -> None:
    """POST /setup/repository/complete with bogus mode returns 400."""
    with patch.object(
        setup_page,
        "_read_persisted_state",
        return_value={
            "current_step": "repository",
            "completed_steps": ["identity"],
            "blocking_items": [],
            "selections": {},
        },
    ):
        resp = client.post(
            "/repository/complete",
            data={"mode": "bogus", "remote_url": ""},
        )
    assert resp.status_code == 400


# -- Dependencies step ------------------------------------------------------


def test_dependencies_step_renders_readiness(client: TestClient) -> None:
    """GET /setup/dependencies/ shows the readiness report."""
    with (
        patch.object(
            setup_page,
            "_read_persisted_state",
            return_value={
                "current_step": "dependencies",
                "completed_steps": ["identity", "repository"],
                "blocking_items": [],
                "selections": {"repository:mode": "init"},
            },
        ),
        patch.object(
            setup_page,
            "_fetch_readiness",
            new=AsyncMock(return_value=_blocked_payload()),
        ),
    ):
        resp = client.get("/dependencies/", follow_redirects=False)
    assert resp.status_code == 200
    body = resp.text
    assert "BLOCKED" in body
    assert "OpenCode" in body


def test_dependencies_complete_advances_to_review(client: TestClient) -> None:
    """POST /setup/dependencies/complete advances to review."""
    with patch.object(
        setup_page,
        "_read_persisted_state",
        return_value={
            "current_step": "dependencies",
            "completed_steps": ["identity", "repository"],
            "blocking_items": [],
            "selections": {},
        },
    ):
        resp = client.post("/dependencies/complete", follow_redirects=False)
    assert resp.status_code in (303, 302, 307)
    assert resp.headers["location"].endswith("/setup/review/")


# -- Review step ------------------------------------------------------------


def test_review_step_shows_provenance(client: TestClient) -> None:
    """GET /setup/review/ shows the apply summary with provenance labels."""
    with patch.object(
        setup_page,
        "_read_persisted_state",
        return_value={
            "current_step": "review",
            "completed_steps": ["identity", "repository", "dependencies"],
            "blocking_items": [],
            "selections": {"repository:mode": "init"},
        },
    ):
        resp = client.get("/review/")
    assert resp.status_code == 200
    body = resp.text
    assert "Review" in body
    assert "provenance" in body.lower()
    assert "Confirm" in body


def test_review_complete_advances_to_applying(client: TestClient) -> None:
    """POST /setup/review/complete advances to applying."""
    with patch.object(
        setup_page,
        "_read_persisted_state",
        return_value={
            "current_step": "review",
            "completed_steps": ["identity", "repository", "dependencies"],
            "blocking_items": [],
            "selections": {},
        },
    ):
        resp = client.post("/review/complete", follow_redirects=False)
    assert resp.status_code in (303, 302, 307)
    assert resp.headers["location"].endswith("/setup/applying/")


# -- Applying step ----------------------------------------------------------


def test_applying_step_renders_apply_body(client: TestClient) -> None:
    """GET /setup/applying/ shows the apply body."""
    with patch.object(setup_page, "_read_persisted_state", return_value={}):
        resp = client.get("/applying/")
    assert resp.status_code == 200
    body = resp.text
    assert "Apply" in body


# -- Complete step ----------------------------------------------------------


def test_complete_step_renders_confirmation(client: TestClient) -> None:
    """GET /setup/complete/ shows the setup-complete confirmation."""
    with patch.object(setup_page, "_read_persisted_state", return_value={}):
        resp = client.get("/complete/")
    assert resp.status_code == 200
    body = resp.text
    assert "Setup Complete" in body
    assert "Start Story" in body


# -- First-user submission (legacy entry) ----------------------------------


def test_first_user_post_calls_api_and_advances(client: TestClient) -> None:
    """POST /setup/first-user forwards to upstream and redirects to repository."""
    mock = AsyncMock(return_value={"principal_id": "prin_123", "name": "alice"})
    with (
        patch.object(setup_page, "_post_first_user", new=mock),
        patch.object(setup_page, "_persist_state", return_value=True),
    ):
        resp = client.post(
            "/first-user",
            data={"name": "alice", "credential": "secret"},
            follow_redirects=False,
        )
    mock.assert_awaited_once()
    assert resp.status_code in (303, 302, 307)
    assert resp.headers["location"].endswith("/setup/repository/")


def test_first_user_post_shows_error_on_failure(client: TestClient) -> None:
    """POST /setup/first-user on upstream failure returns 400 with error message."""
    mock = AsyncMock(side_effect=RuntimeError("upstream 500"))
    with patch.object(setup_page, "_post_first_user", new=mock):
        resp = client.post(
            "/first-user",
            data={"name": "alice", "credential": "secret"},
        )
    assert resp.status_code == 400
    assert "upstream 500" in resp.text or "error" in resp.text.lower()


# -- Stepper & blocking items -----------------------------------------------


def test_stepper_shows_current_and_remaining_steps(client: TestClient) -> None:
    """The wizard stepper shows the current step, completed steps, and remaining steps."""
    with patch.object(setup_page, "_read_persisted_state", return_value={}):
        resp = client.get("/repository/")
    body = resp.text
    # The stepper is rendered as an ordered list
    assert "stepper" in body
    # The current step class is present
    assert "current" in body
    # Remaining steps are listed
    assert "Dependencies" in body or "dependencies" in body
    # Completed steps are also indicated
    assert "Identity" in body or "identity" in body


def test_blocking_items_visible_at_top(client: TestClient) -> None:
    """Blocking items (e.g. Git BLOCKED) are visible prominently at the top."""
    with (
        patch.object(setup_page, "_read_persisted_state", return_value={}),
        patch.object(
            setup_page,
            "_fetch_readiness",
            new=AsyncMock(return_value=_blocked_payload()),
        ),
    ):
        resp = client.get("/dependencies/", follow_redirects=False)
    body = resp.text
    assert "Blocking" in body or "blocking" in body


# -- Return / reset ---------------------------------------------------------


def test_return_endpoint_rewinds_journey(client: TestClient) -> None:
    """POST /setup/return/<step> re-anchors the journey to that step."""
    with (
        patch.object(setup_page, "_read_persisted_state", return_value={}),
        patch.object(setup_page, "_persist_state", return_value=True) as persist,
    ):
        resp = client.post("/return/repository", follow_redirects=False)
    assert resp.status_code in (303, 302, 307)
    assert resp.headers["location"].endswith("/setup/repository/")
    persist.assert_called_once()


def test_reset_endpoint_clears_state(client: TestClient) -> None:
    """POST /setup/reset clears the wizard state and returns to identity."""
    with (
        patch.object(setup_page, "_read_persisted_state", return_value={}),
        patch.object(setup_page, "_persist_state", return_value=True) as persist,
    ):
        resp = client.post("/reset", follow_redirects=False)
    assert resp.status_code in (303, 302, 307)
    assert resp.headers["location"].endswith("/setup/identity/")
    persist.assert_called_once()


# -- Wizard reuses the readiness seam --------------------------------------


def test_dependencies_step_calls_readiness_seam(client: TestClient) -> None:
    """The dependencies step awaits the readiness seam with the api_base."""
    mock = AsyncMock(return_value=_ready_payload())
    with (
        patch.object(setup_page, "_read_persisted_state", return_value={}),
        patch.object(setup_page, "_fetch_readiness", new=mock),
    ):
        client.get("/dependencies/")
    mock.assert_awaited_once()
    api_base = mock.await_args.args[0]
    assert api_base == "http://testserver"
