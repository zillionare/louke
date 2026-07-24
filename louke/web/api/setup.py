"""``/api/setup`` Starlette sub-app: first-user setup endpoints.

Exposes the first-principal flow as a JSON HTTP API. The first user is written
to the workspace user store so setup state survives a server restart. The
Setup Wizard state is also persisted here so the user-visible step
indicator (current step, completed steps, blocking items) survives reloads.

Endpoints:
    GET  /status       - return initialized flag and first principal id.
    POST /first-user   - create the first local human principal.
    GET  /state        - return the persisted Setup Wizard state.
    POST /state        - overwrite the persisted Setup Wizard state.

Error envelope (shared across v0.12 sub-apps)::

    HTTPException(status_code=4xx/5xx,
                   detail={"error_code": "...", "message": "..."})
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

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
        Route("/state", endpoint=get_state, methods=["GET"]),
        Route("/state", endpoint=post_state, methods=["POST"]),
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


_ALLOWED_STEPS: frozenset[str] = frozenset(
    {
        "identity",
        "repository",
        "dependencies",
        "review",
        "applying",
        "complete",
    }
)


def _validate_state(payload: Any) -> dict[str, Any]:
    """Coerce and validate the wizard-state payload."""
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="state must be an object")
    current_step = payload.get("current_step") or "identity"
    if current_step not in _ALLOWED_STEPS:
        raise HTTPException(
            status_code=400, detail=f"invalid current_step: {current_step}"
        )
    completed_raw = payload.get("completed_steps") or []
    if not isinstance(completed_raw, list):
        raise HTTPException(status_code=400, detail="completed_steps must be a list")
    completed = [c for c in completed_raw if c in _ALLOWED_STEPS]
    blocking_raw = payload.get("blocking_items") or []
    if not isinstance(blocking_raw, list):
        raise HTTPException(status_code=400, detail="blocking_items must be a list")
    blocking = [str(b) for b in blocking_raw]
    selections_raw = payload.get("selections") or {}
    if not isinstance(selections_raw, dict):
        raise HTTPException(status_code=400, detail="selections must be an object")
    selections = {str(k): str(v) for k, v in selections_raw.items()}
    return {
        "current_step": current_step,
        "completed_steps": completed,
        "blocking_items": blocking,
        "selections": selections,
    }


async def get_state(request: Request) -> JSONResponse:
    """GET /api/setup/state: return the persisted Setup Wizard state.

    Returns:
        ``200`` with the persisted state dict, or an empty default if no
        state has been recorded yet.
    """
    state = _store(request).read_setup_state() or {}
    return JSONResponse(_validate_state(state))


async def post_state(request: Request) -> JSONResponse:
    """POST /api/setup/state: overwrite the persisted Setup Wizard state.

    Body: ``{"current_step": str, "completed_steps": list, ...}``.

    Returns:
        ``200`` with the normalized state.
    """
    payload = await json_body(request)
    normalized = _validate_state(payload)
    _store(request).write_setup_state(normalized)
    return JSONResponse(normalized)
