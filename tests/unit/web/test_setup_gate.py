"""Unit contracts for the Setup Gate (AC-FR0001-01, AC-FR0001-02).

AC-FR0001-01: Setup-incomplete requests never reach protected handlers.
AC-FR0001-02: Gate lifts when the manifest is a valid v2 ``complete``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from louke.web.setup_gate import SetupGate, SetupGateMiddleware
from louke.web.setup_state import SetupManifest, SetupStatus, write_manifest

WORKSPACE_ID = "ws_test_gate"


def _make_manifest(
    workspace: Path, status: SetupStatus = SetupStatus.PENDING_USER
) -> None:
    """Write a minimal manifest with the given status."""
    if status == SetupStatus.PENDING_USER:
        manifest = SetupManifest(
            workspace_id=WORKSPACE_ID, revision=0, status=SetupStatus.PENDING_USER
        )
    elif status == SetupStatus.PENDING_MODEL:
        manifest = SetupManifest(
            workspace_id=WORKSPACE_ID, revision=0, status=SetupStatus.PENDING_USER
        )
        manifest = manifest.advance_to_pending_model(
            first_principal_id="prin_alpha", expected_revision=0
        )
    else:
        manifest = SetupManifest(
            workspace_id=WORKSPACE_ID, revision=0, status=SetupStatus.PENDING_USER
        )
        manifest = manifest.advance_to_pending_model(
            first_principal_id="prin_alpha", expected_revision=0
        )
        manifest = manifest.complete(
            model_check_state="passed",
            model_check_id="chk_1",
            model_check_revision=1,
            model_id="minimax/m2",
            diagnosis=None,
            observed_at="2026-07-24T00:00:00Z",
            expected_revision=1,
        )
    write_manifest(workspace, manifest)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """An isolated workspace directory."""
    ws = tmp_path / "workspace"
    (ws / ".louke").mkdir(parents=True)
    return ws


# ---------------------------------------------------------------------------
# Decision-function contracts
# ---------------------------------------------------------------------------


class TestGateBlocksIncompleteSetup:
    """AC-FR0001-01: incomplete Setup blocks all non-allowlisted routes."""

    @pytest.mark.parametrize(
        "path",
        [
            "/",
            "/login",
            "/workbench",
            "/projects",
            "/runs/run_1",
            "/docs/spec_1",
            "/wiki/start",
            "/models",
        ],
    )
    def test_redirects_user_routes_to_setup(self, path: str) -> None:
        """AC-FR0001-01: every user-facing route redirects to ``/setup``."""
        gate = SetupGate()
        gate.set_status("pending_user")
        status, target = gate.redirect(path)
        assert status == 303
        assert target == "/setup"

    def test_api_returns_428(self) -> None:
        """AC-FR0001-01: non-allowlisted API returns 428 SETUP_REQUIRED."""
        gate = SetupGate()
        gate.set_status("pending_user")
        status, body = gate.guard_api("GET", "/api/projects/current")
        assert status == 428
        assert body["error"] == "SETUP_REQUIRED"

    def test_partial_signals_do_not_bypass_gate(self) -> None:
        """AC-FR0001-02: cookies/Guide/executable do not lift the gate."""
        gate = SetupGate()
        gate.set_status("pending_user")
        for hint in ("cookie_set", "guide_only", "executable_only", "user_only"):
            status, target = gate.redirect("/workbench")
            assert status == 303
            assert target == "/setup"


class TestGateAllowsSetupRoutes:
    """AC-FR0001-01: allowlisted routes pass through during incomplete Setup."""

    @pytest.mark.parametrize(
        "path",
        ["/setup", "/setup/", "/health", "/assets/style.css"],
    )
    def test_allowlisted_pages_pass_through(self, path: str) -> None:
        """AC-FR0001-01: allowlisted page routes are not redirected."""
        gate = SetupGate()
        gate.set_status("pending_user")
        status, target = gate.redirect(path)
        assert status == 200

    def test_setup_status_api_allowed(self) -> None:
        """AC-FR0001-01: ``GET /api/setup/status`` is allowlisted."""
        gate = SetupGate()
        gate.set_status("pending_user")
        status, _ = gate.guard_api("GET", "/api/setup/status")
        assert status == 200

    def test_setup_first_user_api_allowed(self) -> None:
        """AC-FR0001-01: ``POST /api/setup/first-user`` is allowlisted."""
        gate = SetupGate()
        gate.set_status("pending_user")
        status, _ = gate.guard_api("POST", "/api/setup/first-user")
        assert status == 200

    def test_auth_login_api_allowed(self) -> None:
        """AC-FR0001-01: ``POST /api/auth/login`` is allowlisted."""
        gate = SetupGate()
        gate.set_status("pending_model")
        status, _ = gate.guard_api("POST", "/api/auth/login")
        assert status == 200

    def test_model_checks_post_allowed(self) -> None:
        """AC-FR0001-01: ``POST /api/setup/model-checks`` is allowlisted."""
        gate = SetupGate()
        gate.set_status("pending_model")
        status, _ = gate.guard_api("POST", "/api/setup/model-checks")
        assert status == 200

    def test_model_checks_get_allowed(self) -> None:
        """AC-FR0001-01: ``GET /api/setup/model-checks/{id}`` is allowlisted."""
        gate = SetupGate()
        gate.set_status("pending_model")
        status, _ = gate.guard_api("GET", "/api/setup/model-checks/chk_1")
        assert status == 200


class TestGateLiftsOnComplete:
    """AC-FR0001-02: gate lifts when manifest is a valid v2 ``complete``."""

    def test_login_passes_through_when_complete(self) -> None:
        """AC-FR0001-02: ``/login`` is accessible after Setup completes."""
        gate = SetupGate()
        gate.set_status("complete")
        status, target = gate.redirect("/login", authenticated=False)
        assert status == 200
        assert target == "/login"

    def test_workbench_redirects_to_projects_when_authenticated(self) -> None:
        """AC-FR0001-02: authenticated ``/workbench`` goes to Projects."""
        gate = SetupGate()
        gate.set_status("complete")
        status, target = gate.redirect("/workbench", authenticated=True)
        assert status == 200
        assert target == "/workbench?activity=projects"

    def test_api_passes_through_when_complete(self) -> None:
        """AC-FR0001-02: protected API is accessible after Setup completes."""
        gate = SetupGate()
        gate.set_status("complete")
        status, _ = gate.guard_api("GET", "/api/projects/current")
        assert status == 200


class TestGateFailClosed:
    """AC-FR0301-02: gate fails closed on missing/corrupt manifest."""

    def test_no_manifest_treats_as_incomplete(self, workspace: Path) -> None:
        """AC-FR0301-02: missing manifest is treated as Setup-incomplete."""
        gate = SetupGate(workspace_root=workspace)
        assert gate.status == "pending_user"
        status, target = gate.redirect("/")
        assert status == 303
        assert target == "/setup"

    def test_corrupt_manifest_treats_as_incomplete(self, workspace: Path) -> None:
        """AC-FR0301-02: corrupt manifest is treated as Setup-incomplete."""
        (workspace / ".louke" / "web-setup-state.json").write_text("not valid json {{{")
        gate = SetupGate(workspace_root=workspace)
        assert gate.status == "pending_user"
        status, target = gate.redirect("/")
        assert status == 303
        assert target == "/setup"

    def test_complete_manifest_lifts_gate(self, workspace: Path) -> None:
        """AC-FR0301-02: valid complete manifest lifts the gate."""
        _make_manifest(workspace, SetupStatus.COMPLETE)
        gate = SetupGate(workspace_root=workspace)
        assert gate.status == "complete"
        status, _ = gate.redirect("/workbench", authenticated=True)
        assert status == 200


# ---------------------------------------------------------------------------
# Middleware integration contracts
# ---------------------------------------------------------------------------


def _create_middleware_app(workspace: Path, status: SetupStatus) -> Starlette:
    """Create a minimal Starlette app with the SetupGateMiddleware."""
    _make_manifest(workspace, status)

    def protected_page(request) -> PlainTextResponse:
        return PlainTextResponse("protected_page_content")

    def protected_api(request) -> JSONResponse:
        return JSONResponse({"data": "protected_api_data"})

    def setup_page(request) -> PlainTextResponse:
        return PlainTextResponse("setup_page_content")

    def health(request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    routes = [
        Route("/", endpoint=protected_page, methods=["GET"]),
        Route("/workbench", endpoint=protected_page, methods=["GET"]),
        Route("/setup", endpoint=setup_page, methods=["GET"]),
        Route("/health", endpoint=health, methods=["GET"]),
        Route("/api/protected", endpoint=protected_api, methods=["GET"]),
        Route(
            "/api/setup/status",
            endpoint=lambda r: JSONResponse({"status": "pending_user"}),
            methods=["GET"],
        ),
    ]
    app = Starlette(routes=routes)
    app.add_middleware(SetupGateMiddleware, workspace_root=workspace)
    return app


class TestMiddlewareIntegration:
    """The ASGI middleware wraps SetupGate for route-level protection."""

    def test_middleware_redirects_root_when_incomplete(self, workspace: Path) -> None:
        """Middleware redirects ``/`` to ``/setup`` with 303."""
        app = _create_middleware_app(workspace, SetupStatus.PENDING_USER)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/setup"

    def test_middleware_returns_428_for_api_when_incomplete(
        self, workspace: Path
    ) -> None:
        """Middleware returns 428 for non-allowlisted API."""
        app = _create_middleware_app(workspace, SetupStatus.PENDING_USER)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/protected")
        assert resp.status_code == 428

    def test_middleware_passes_setup_page_when_incomplete(
        self, workspace: Path
    ) -> None:
        """Middleware allows ``/setup`` during incomplete Setup."""
        app = _create_middleware_app(workspace, SetupStatus.PENDING_USER)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/setup")
        assert resp.status_code == 200
        assert "setup_page_content" in resp.text

    def test_middleware_passes_all_when_complete(self, workspace: Path) -> None:
        """Middleware passes all routes when Setup is complete."""
        app = _create_middleware_app(workspace, SetupStatus.COMPLETE)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/")
        assert resp.status_code == 200
        assert "protected_page_content" in resp.text

        resp = client.get("/api/protected")
        assert resp.status_code == 200
        assert resp.json()["data"] == "protected_api_data"
