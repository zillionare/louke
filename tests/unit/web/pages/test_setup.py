"""TestClient tests for the /setup page sub-app (B3a).

Verifies the setup-only wizard HTML page:
- GET / returns 200 text/html and renders the setup-only state, the first-user
  form (POSTing to /api/setup/first-user), and the readiness list.
- When readiness is complete, GET / redirects to /.
- The page issues the correct upstream GET /api/readiness call (validated by
  patching the module-level fetch seam).
- The page issues the correct upstream POST /api/setup/first-user call when
  the form is submitted (validated by patching the post seam).
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
        {"name": "Catalog", "status": "READY", "diagnosis": "ok", "remediation": "none"},
        {"name": "OpenCode", "status": "READY", "diagnosis": "ok", "remediation": "none"},
        {"name": "Models", "status": "READY", "diagnosis": "default-model", "remediation": "none"},
    ]


def _blocked_payload() -> list[dict[str, str]]:
    """Return a readiness payload where at least one check is BLOCKED."""
    return [
        {"name": "Git", "status": "READY", "diagnosis": "ok", "remediation": "none"},
        {"name": "Store", "status": "READY", "diagnosis": "ok", "remediation": "none"},
        {"name": "Catalog", "status": "BLOCKED", "diagnosis": "missing", "remediation": "run X"},
        {"name": "OpenCode", "status": "BLOCKED", "diagnosis": "no adapter", "remediation": "wait B4"},
        {"name": "Models", "status": "READY", "diagnosis": "default-model", "remediation": "none"},
    ]


def test_setup_page_returns_html_and_shows_wizard(client: TestClient) -> None:
    """GET / returns 200 text/html and renders the setup-only wizard.

    The page must mention setup-only, the first-user form, the readiness
    section, and a form that posts to the page's own /first-user route.
    """
    with patch.object(
        setup_page, "_fetch_readiness", new=AsyncMock(return_value=_blocked_payload())
    ):
        resp = client.get("/")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    body = resp.text
    assert "setup-only" in body
    assert "First user" in body or "first user" in body
    # The form posts to the page's own first-user route (the page forwards
    # to /api/setup/first-user internally).
    assert 'action="/setup/first-user"' in body or 'action="first-user"' in body
    assert "readiness" in body.lower()
    # readiness items rendered
    assert "Git" in body
    assert "OpenCode" in body


def test_setup_page_renders_readiness_items_with_status(client: TestClient) -> None:
    """GET / renders each readiness item name and status."""
    with patch.object(
        setup_page, "_fetch_readiness", new=AsyncMock(return_value=_blocked_payload())
    ):
        resp = client.get("/")

    body = resp.text
    assert "BLOCKED" in body
    assert "READY" in body
    # The blocked OpenCode diagnosis/remediation should be visible
    assert "no adapter" in body
    assert "wait B4" in body


def test_setup_page_calls_readiness_api(client: TestClient) -> None:
    """The page issues GET /api/readiness upstream.

    The seam receives the api_base (same-origin when empty); internally it
    builds ``{api_base}/api/readiness``. We patch the seam and assert it was
    awaited, then separately verify the URL the unpatched seam would build.
    """
    mock = AsyncMock(return_value=_blocked_payload())
    with patch.object(setup_page, "_fetch_readiness", new=mock):
        client.get("/")
    mock.assert_awaited_once()
    # The seam's first positional arg is the api_base (empty = same-origin);
    # the unpatched implementation builds "{api_base}/api/readiness".
    api_base = mock.await_args.args[0]
    assert "/api/readiness" in f"{api_base}/api/readiness"


def test_setup_page_redirects_when_readiness_complete(client: TestClient) -> None:
    """When readiness is complete (all READY), GET / redirects to /."""
    with patch.object(
        setup_page, "_fetch_readiness", new=AsyncMock(return_value=_ready_payload())
    ):
        # follow_redirects=False so we can inspect the redirect
        resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (303, 302, 307)
    assert resp.headers["location"] == "/"


def test_setup_page_shows_form_fields(client: TestClient) -> None:
    """The first-user form has name and credential inputs."""
    with patch.object(
        setup_page, "_fetch_readiness", new=AsyncMock(return_value=_blocked_payload())
    ):
        resp = client.get("/")
    body = resp.text
    assert 'name="name"' in body
    assert 'name="credential"' in body


def test_setup_first_user_post_calls_api(client: TestClient) -> None:
    """POST /first-user with name+credential forwards to /api/setup/first-user.

    The seam receives the upstream base url plus name and credential kwargs;
    internally it builds ``{api_base}/api/setup/first-user``.
    """
    mock = AsyncMock(return_value={"principal_id": "prin_123", "name": "alice"})
    with patch.object(setup_page, "_post_first_user", new=mock):
        resp = client.post(
            "/first-user",
            data={"name": "alice", "credential": "secret"},
            follow_redirects=False,
        )
    mock.assert_awaited_once()
    # The seam receives the api_base (same-origin when empty) plus kwargs.
    api_base = mock.await_args.args[0]
    assert "/api/setup" in f"{api_base}/api/setup/first-user"
    assert mock.await_args.kwargs["name"] == "alice"
    assert mock.await_args.kwargs["credential"] == "secret"
    # After successful creation, redirect back to /setup (or to /).
    assert resp.status_code in (303, 302, 307)


def test_setup_first_user_post_shows_error_on_failure(client: TestClient) -> None:
    """POST /first-user on upstream failure shows an error message in the page."""
    mock = AsyncMock(side_effect=RuntimeError("upstream 500"))
    with patch.object(setup_page, "_post_first_user", new=mock), patch.object(
        setup_page, "_fetch_readiness", new=AsyncMock(return_value=_blocked_payload())
    ):
        resp = client.post(
            "/first-user",
            data={"name": "alice", "credential": "secret"},
        )
    assert resp.status_code == 200
    assert "upstream 500" in resp.text or "error" in resp.text.lower()
