"""Authenticated v0.14 release preview, confirm, status and recheck APIs."""

from __future__ import annotations

from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse

from louke.web.auth import CSRF_COOKIE, SESSION_COOKIE, current_user, verify_csrf_token
from louke.v014.release_entry import (
    ReleaseEntryService,
    ReleaseRequestConflictError,
    StalePreviewError,
)


async def preview_release(request: Request) -> JSONResponse:
    """POST `/api/v14/releases/preview` for an authenticated Human."""
    user_or_response = _require_human(request, csrf_required=True)
    if isinstance(user_or_response, JSONResponse):
        return user_or_response
    payload = await request.json()
    story = _required_string(payload, "story")
    release_version = _required_string(payload, "release_version")
    try:
        preview = _service(request).preview(story, release_version)
    except ValueError as exc:
        return JSONResponse(_error("VALIDATION_ERROR", str(exc)), status_code=400)
    return JSONResponse(preview)


async def confirm_release(request: Request) -> JSONResponse:
    """POST `/api/v14/releases/confirm` with stale and idempotency guards."""
    user_or_response = _require_human(request, csrf_required=True)
    if isinstance(user_or_response, JSONResponse):
        return user_or_response
    payload = await request.json()
    try:
        result = _service(request).confirm(
            _required_string(payload, "preview_id"),
            expected_preview_revision=_required_int(
                payload, "expected_preview_revision"
            ),
            request_digest=_required_string(payload, "request_digest"),
            idempotency_key=_required_string(payload, "idempotency_key"),
            actor=user_or_response.username,
        )
    except StalePreviewError as exc:
        return JSONResponse(_error("STALE_PREVIEW", str(exc)), status_code=409)
    except ReleaseRequestConflictError as exc:
        return JSONResponse(_error("REQUEST_CONFLICT", str(exc)), status_code=409)
    except (KeyError, ValueError) as exc:
        return JSONResponse(_error("VALIDATION_ERROR", str(exc)), status_code=400)
    return JSONResponse(
        {
            "request_id": result["request_id"],
            "status": result["status"],
            "continue_url": result["continue_url"],
        },
        status_code=202,
    )


async def release_status(request: Request) -> JSONResponse:
    """GET `/api/v14/releases/requests/{request_id}` status read model."""
    user_or_response = _require_human(request, csrf_required=False)
    if isinstance(user_or_response, JSONResponse):
        return user_or_response
    try:
        return JSONResponse(_service(request).status(request.path_params["request_id"]))
    except KeyError as exc:
        return JSONResponse(_error("NOT_FOUND", str(exc)), status_code=404)


async def foundation_status(request: Request) -> JSONResponse:
    """GET `/api/v14/releases/requests/{request_id}/foundation` evidence."""
    user_or_response = _require_human(request, csrf_required=False)
    if isinstance(user_or_response, JSONResponse):
        return user_or_response
    try:
        result = _service(request).status(request.path_params["request_id"])
    except KeyError as exc:
        return JSONResponse(_error("NOT_FOUND", str(exc)), status_code=404)
    return JSONResponse(
        {
            "request_id": result["request_id"],
            "status": result["status"],
            "main_check": result["main_check"],
            "foundation": result["foundation"],
        }
    )


async def recheck_release(request: Request) -> JSONResponse:
    """POST `/api/v14/releases/requests/{request_id}/recheck` recovery action."""
    user_or_response = _require_human(request, csrf_required=True)
    if isinstance(user_or_response, JSONResponse):
        return user_or_response
    try:
        result = _service(request).recheck(
            request.path_params["request_id"], actor=user_or_response.username
        )
    except KeyError as exc:
        return JSONResponse(_error("NOT_FOUND", str(exc)), status_code=404)
    return JSONResponse(result, status_code=202)


def _service(request: Request) -> ReleaseEntryService:
    """Return the Runtime-owned release entry service from app state."""
    return request.app.state.v14_release_entry


def _require_human(request: Request, *, csrf_required: bool):
    """Require a valid Human session and, for writes, its bound CSRF token."""
    store = request.app.state.store
    session = request.cookies.get(SESSION_COOKIE)
    user = current_user(store, session)
    if user is None:
        return JSONResponse(_error("AUTH_REQUIRED", "login required"), status_code=401)
    if csrf_required and not verify_csrf_token(
        store,
        session,
        request.headers.get("x-louke-csrf") or request.cookies.get(CSRF_COOKIE),
    ):
        return JSONResponse(
            _error("CSRF_INVALID", "valid session-bound CSRF token required"),
            status_code=403,
        )
    return user


def _required_string(payload: dict[str, Any], field: str) -> str:
    """Return a non-empty string field from a JSON object."""
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is required")
    return value.strip()


def _required_int(payload: dict[str, Any], field: str) -> int:
    """Return an integer field without accepting booleans."""
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    return value


def _error(code: str, message: str) -> dict[str, Any]:
    """Return the common API error envelope."""
    return {"error_code": code, "message": message}
