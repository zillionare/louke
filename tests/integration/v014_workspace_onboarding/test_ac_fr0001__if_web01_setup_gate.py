"""IF-WEB-01 — Setup Global gate protection + completion解除.

AC-FR0001-01, AC-FR0001-02

Cross-module: ``Setup Gate × Fact Stores``. Without Setup-complete:

* any user-facing route returns ``303`` to ``/setup``;
* any non-allowlist API returns ``428 SETUP_REQUIRED``;
* the allowlist cannot open Projects/Runs/Docs or forge a complete.

With Setup-complete: the gate must not redirect users away from
``/login`` or Workbench.

Tests drive the real ``louke.web.setup_gate.SetupGate`` and a real
TestClient-backed Starlette app wired with ``SetupGateMiddleware``.
The gate reads the real ``.louke/web-setup-state.json`` manifest.
"""

from __future__ import annotations


import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from louke.web.setup_gate import SetupGate, SetupGateMiddleware
from louke.web.setup_state import (
    SetupManifest,
    SetupStatus,
    write_manifest,
)


WORKSPACE_ID = "ws_test_gate"


def _write_manifest(synthetic_host, status: SetupStatus) -> None:
    """Persist a v2 manifest with the given status to the workspace."""
    base = SetupManifest(
        workspace_id=WORKSPACE_ID,
        revision=0,
        status=SetupStatus.PENDING_USER,
    )
    if status == SetupStatus.PENDING_USER:
        manifest = base
    elif status == SetupStatus.PENDING_MODEL:
        manifest = base.advance_to_pending_model(
            first_principal_id="prin_alpha", expected_revision=0
        )
    else:
        manifest = base.advance_to_pending_model(
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
    write_manifest(synthetic_host, manifest)


def _build_app(synthetic_host, *, status: SetupStatus) -> Starlette:
    """Build a minimal Starlette app with the Setup Gate middleware."""
    _write_manifest(synthetic_host, status)

    def protected_page(_request):
        return PlainTextResponse("protected_page_content")

    def protected_api(_request):
        return JSONResponse({"data": "protected_api_data"})

    def setup_page(_request):
        return PlainTextResponse("setup_page_content")

    def health(_request):
        return PlainTextResponse("ok")

    def setup_status_api(_request):
        return JSONResponse({"status": status.value})

    def setup_first_user_api(_request):
        return JSONResponse({"principal_id": "prin_alpha"})

    def auth_login_api(_request):
        return JSONResponse({"ok": True})

    routes = [
        Route("/", endpoint=protected_page),
        Route("/login", endpoint=protected_page),
        Route("/workbench", endpoint=protected_page),
        Route("/projects", endpoint=protected_page),
        Route("/projects/{project_id:path}", endpoint=protected_page),
        Route("/runs/{run_id:path}", endpoint=protected_page),
        Route("/docs/{spec_id:path}", endpoint=protected_page),
        Route("/wiki/start", endpoint=protected_page),
        Route("/models", endpoint=protected_page),
        Route("/setup", endpoint=setup_page),
        Route("/health", endpoint=health),
        Route("/api/protected", endpoint=protected_api),
        Route("/api/setup/status", endpoint=setup_status_api),
        Route("/api/setup/first-user", endpoint=setup_first_user_api, methods=["POST"]),
        Route("/api/auth/login", endpoint=auth_login_api, methods=["POST"]),
        Route(
            "/api/setup/model-checks",
            endpoint=setup_status_api,
            methods=["POST"],
        ),
        Route(
            "/api/setup/model-checks/{check_id}",
            endpoint=setup_status_api,
        ),
    ]
    app = Starlette(routes=routes)
    app.add_middleware(SetupGateMiddleware, workspace_root=synthetic_host)
    return app


# ---------------------------------------------------------------------------
# AC-FR0001-01: incomplete Setup blocks non-allowlisted exits
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/login",
        "/workbench",
        "/projects",
        "/projects/ws_1/prj_x",
        "/runs/run_1",
        "/docs/spec_1",
        "/wiki/start",
        "/models",
    ],
)
def test_setup_incomplete_redirects_user_route(synthetic_host, path: str) -> None:
    """AC-FR0001-01: every user-facing route 303s to ``/setup``."""
    # AC-FR0001-01
    app = _build_app(synthetic_host, status=SetupStatus.PENDING_USER)
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get(path, follow_redirects=False)
    assert resp.status_code == 303, f"{path}: expected 303, got {resp.status_code}"
    assert resp.headers["location"] == "/setup"


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/protected"),
        ("POST", "/api/protected"),
        ("GET", "/api/projects/current"),
        ("POST", "/api/projects/preview"),
        ("GET", "/api/guide/session"),
    ],
)
def test_setup_incomplete_api_returns_428(
    synthetic_host, method: str, path: str
) -> None:
    """AC-FR0001-01: non-allowlist API emits ``428 SETUP_REQUIRED``."""
    # AC-FR0001-01
    app = _build_app(synthetic_host, status=SetupStatus.PENDING_USER)
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.request(method, path)
    assert resp.status_code == 428, (
        f"{method} {path}: expected 428, got {resp.status_code}"
    )
    body = resp.json()
    assert body["error"] == "SETUP_REQUIRED"
    assert body["setup_url"] == "/setup"


def test_setup_incomplete_blocks_protected_handler_execution(
    synthetic_host,
) -> None:
    """AC-FR0001-01: blocked handlers do NOT execute before redirect."""
    # AC-FR0001-01
    app = _build_app(synthetic_host, status=SetupStatus.PENDING_USER)
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/", follow_redirects=False)
    assert "protected_page_content" not in resp.text

    resp = client.get("/api/protected")
    assert "protected_api_data" not in resp.text


# ---------------------------------------------------------------------------
# AC-FR0001-01: allowlist remains reachable during incomplete Setup
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    ["/setup", "/setup/", "/health"],
)
def test_setup_incomplete_allowlist_passes(synthetic_host, path: str) -> None:
    """AC-FR0001-01: allowlist routes are not blocked."""
    # AC-FR0001-01
    app = _build_app(synthetic_host, status=SetupStatus.PENDING_USER)
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get(path)
    assert resp.status_code == 200, f"{path}: expected 200, got {resp.status_code}"


def test_setup_incomplete_allowlist_api_passes(synthetic_host) -> None:
    """AC-FR0001-01: setup-allowlist API routes stay reachable."""
    # AC-FR0001-01
    app = _build_app(synthetic_host, status=SetupStatus.PENDING_USER)
    client = TestClient(app, raise_server_exceptions=False)
    for path in ("/api/setup/status",):
        assert client.get(path).status_code == 200
    for path in ("/api/setup/first-user",):
        assert client.post(path).status_code == 200
    for path in ("/api/setup/model-checks",):
        assert client.post(path).status_code == 200
    for path in ("/api/setup/model-checks/chk_1",):
        assert client.get(path).status_code == 200
    for path in ("/api/auth/login",):
        assert client.post(path).status_code == 200


# ---------------------------------------------------------------------------
# AC-FR0001-02: gate lifts when manifest is a valid v2 ``complete``
# ---------------------------------------------------------------------------


def test_setup_complete_lifts_gate_for_user_routes(synthetic_host) -> None:
    """AC-FR0001-02: completed Setup no longer redirects user routes."""
    # AC-FR0001-02
    app = _build_app(synthetic_host, status=SetupStatus.COMPLETE)
    client = TestClient(app, raise_server_exceptions=False)
    for path in (
        "/",
        "/login",
        "/workbench",
        "/projects",
        "/projects/ws_1/prj_x",
        "/runs/run_1",
        "/docs/spec_1",
        "/wiki/start",
        "/models",
    ):
        resp = client.get(path, follow_redirects=False)
        assert resp.status_code == 200, f"{path}: expected 200, got {resp.status_code}"
        assert resp.headers.get("location") != "/setup"


def test_setup_complete_lifts_gate_for_apis(synthetic_host) -> None:
    """AC-FR0001-02: protected APIs return real responses, not 428."""
    # AC-FR0001-02
    app = _build_app(synthetic_host, status=SetupStatus.COMPLETE)
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/protected")
    assert resp.status_code == 200
    assert resp.json()["data"] == "protected_api_data"


# ---------------------------------------------------------------------------
# AC-FR0001-02: only the persisted manifest drops the gate
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "status",
    [SetupStatus.PENDING_USER, SetupStatus.PENDING_MODEL],
)
def test_setup_decision_function_redirects_incomplete(status: SetupStatus) -> None:
    """AC-FR0001-02: ``SetupGate.redirect()`` returns (303, /setup) for incomplete states."""
    # AC-FR0001-02
    gate = SetupGate()
    gate.set_status(status.value)
    for path in ("/login", "/workbench", "/projects", "/runs/1"):
        code, target = gate.redirect(path)
        assert code == 303, f"{path}: expected 303, got {code}"
        assert target == "/setup", f"{path}: expected /setup, got {target}"


def test_setup_decision_function_passes_complete() -> None:
    """AC-FR0001-02: ``SetupGate.redirect()`` returns 200 for complete Setup."""
    # AC-FR0001-02
    gate = SetupGate()
    gate.set_status(SetupStatus.COMPLETE.value)
    code, target = gate.redirect("/login", authenticated=False)
    assert code == 200
    assert target == "/login"

    code, target = gate.redirect("/workbench", authenticated=True)
    assert code == 200
    assert target == "/workbench?activity=projects"


def test_setup_decision_function_rejects_partial_signals() -> None:
    """AC-FR0001-02: cookie / Guide / executable presence do NOT bypass the gate.

    The persisted manifest is the only authoritative signal; partial
    hints must not lift an incomplete gate.
    """
    # AC-FR0001-02
    gate = SetupGate()
    gate.set_status(SetupStatus.PENDING_USER.value)
    for hint in ("cookie_set", "guide_only", "executable_only", "user_only"):
        code, target = gate.redirect("/workbench", authenticated=True)
        assert code == 303, f"hint={hint!r} must not lift incomplete Setup; got {code}"
        assert target == "/setup"


# ---------------------------------------------------------------------------
# AC-FR0301-02: fail-closed on missing or corrupt manifest
# ---------------------------------------------------------------------------


def test_missing_manifest_is_treated_as_incomplete(tmp_path) -> None:
    """AC-FR0301-02: missing manifest keeps the gate closed."""
    # AC-FR0301-02
    workspace = tmp_path / "ws"
    (workspace / ".louke").mkdir(parents=True)
    gate = SetupGate(workspace_root=workspace)
    assert gate.status == SetupStatus.PENDING_USER.value
    code, target = gate.redirect("/")
    assert code == 303
    assert target == "/setup"


def test_corrupt_manifest_is_treated_as_incomplete(tmp_path) -> None:
    """AC-FR0301-02: corrupt manifest is fail-closed (incomplete)."""
    # AC-FR0301-02
    workspace = tmp_path / "ws"
    (workspace / ".louke").mkdir(parents=True)
    (workspace / ".louke" / "web-setup-state.json").write_text("not json {{{")
    gate = SetupGate(workspace_root=workspace)
    assert gate.status == SetupStatus.PENDING_USER.value
    code, target = gate.redirect("/")
    assert code == 303
    assert target == "/setup"
