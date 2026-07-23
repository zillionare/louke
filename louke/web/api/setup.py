"""``/api/setup`` Starlette sub-app: first-user setup endpoints.

Exposes the first-principal flow as a JSON HTTP API. The first user is written
to the workspace user store so setup state survives a server restart.

Endpoints:
    GET  /status       - return initialized flag and first principal id.
    POST /first-user   - create the first local human principal.

Error envelope (shared across v0.12 sub-apps)::

    HTTPException(status_code=4xx/5xx,
                   detail={"error_code": "...", "message": "..."})
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from louke.web.store import ProjectStore, ValidationError

from ._common import install_error_handlers, json_body, require_str


def create_app(workspace_root: str | Path | None = None) -> Starlette:
    """Return a self-contained Starlette sub-app for ``/api/setup``.

    Returns:
        A Starlette application whose routes are relative to ``/api/setup``.
    """
    app = Starlette(routes=_routes())
    app.state.workspace_root = Path(workspace_root or ".").resolve()
    install_error_handlers(app)
    return app


def _routes() -> list[Route]:
    """Return the routes for the setup sub-app."""
    return [
        Route("/status", endpoint=get_status),
        Route("/first-user", endpoint=create_first_user, methods=["POST"]),
    ]


def _store(request: Request) -> ProjectStore:
    """Return the workspace store shared with serve and web authentication."""
    return ProjectStore(request.app.state.workspace_root)


def _principal_id(name: str) -> str:
    """Return a stable local principal id derived from the username."""
    return f"prin_{hashlib.sha256(name.encode()).hexdigest()[:12]}"


async def get_status(request: Request) -> JSONResponse:
    """AC-FR1801-03: return the workspace setup status.

    Returns:
        ``200`` with ``{"initialized": bool, "first_principal_id": str | None}``.
    """
    users = _store(request).list_users()
    first_user = users[0] if users else None
    return JSONResponse(
        {
            "initialized": first_user is not None,
            "first_principal_id": _principal_id(first_user["username"])
            if first_user
            else None,
        }
    )


async def create_first_user(request: Request) -> JSONResponse:
    """AC-FR1801-03: create the first local human principal.

    Body:
        ``{"name": str, "credential": str}``.

    Returns:
        ``201`` with ``{"principal_id": str, "name": str}``.
    """
    payload = await json_body(request)
    name = require_str(payload, "name")
    credential = require_str(payload, "credential")
    store = _store(request)
    if store.list_users():
        raise HTTPException(status_code=409, detail="first user already exists")
    try:
        store.create_user(name, credential)
    except ValidationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return JSONResponse(
        {"principal_id": _principal_id(name), "name": name},
        status_code=201,
    )
