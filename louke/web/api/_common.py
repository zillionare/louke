"""Shared helpers for the v0.12 runtime HTTP sub-apps (package-private).

Each sub-app is self-contained: it brings its own in-memory
``WorkflowRunStore`` (with a registered v0.12 catalog) via a per-app
singleton accessor, and shares the error envelope and principal
extraction helpers defined here.

Error envelope contract (stable across all v0.12 sub-apps)::

    HTTPException(status_code=..., detail={"error_code": "...", "message": "..."})

The installed :func:`http_exception_handler` renders that envelope as a
``JSONResponse`` because Starlette's built-in handler renders ``detail`` as a
plain text body, which would lose the structured error_code/message shape.
"""

from __future__ import annotations

from typing import Any

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

#: Error code returned when request body or query params are invalid.
VALIDATION_ERROR: str = "VALIDATION_ERROR"
#: Error code returned when a referenced resource does not exist.
NOT_FOUND: str = "NOT_FOUND"
#: Error code returned when a state transition is not allowed.
CONFLICT: str = "CONFLICT"
#: Error code returned when an optimistic-concurrency revision mismatch occurs.
STALE: str = "STALE"
#: Error code returned when the principal is not allowed to perform the action.
FORBIDDEN: str = "FORBIDDEN"
#: Error code returned for otherwise unclassified internal failures.
INTERNAL: str = "INTERNAL"

#: Default header name carrying the requesting principal id (no auth in B1).
PRINCIPAL_HEADER: str = "x-louke-principal"

#: Default anonymous principal when the header is absent.
ANONYMOUS_PRINCIPAL: str = "anonymous"


def principal_id(request: Request) -> str:
    """Return the requesting principal id from the request header.

    Args:
        request: The incoming Starlette request.

    Returns:
        The principal id from the ``x-louke-principal`` header, or
        ``"anonymous"`` when the header is absent.
    """
    return request.headers.get(PRINCIPAL_HEADER) or ANONYMOUS_PRINCIPAL


def actor(principal: str) -> dict[str, str]:
    """Build a redacted actor dict for a runtime call.

    Args:
        principal: The requesting principal id.

    Returns:
        A ``{"kind": "human", "id": principal}`` dict suitable for the
        orchestrator / gate service actor parameter.
    """
    return {"kind": "human", "id": principal}


def error_detail(error_code: str, message: str) -> dict[str, Any]:
    """Return the stable v0.12 error envelope detail dict.

    Args:
        error_code: One of the ``VALIDATION_ERROR`` / ``NOT_FOUND`` / ... constants.
        message: Human-readable error message.

    Returns:
        A dict suitable as the ``detail`` of a Starlette ``HTTPException``.
    """
    return {"error_code": error_code, "message": message}


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Render an :class:`HTTPException` with a dict ``detail`` as JSON.

    Starlette's built-in handler renders ``detail`` as a plain-text body, which
    loses the structured ``{"error_code": ..., "message": ...}`` shape. This
    handler restores that shape and falls back to a plain ``{"error_code":
    "INTERNAL", "message": str(detail)}`` envelope when ``detail`` is not a
    dict (e.g. raised by Starlette's own routing layer for 404s).

    Args:
        request: The request that raised the exception (unused).
        exc: The raised HTTPException.

    Returns:
        A ``JSONResponse`` with the structured error envelope and the same
        status code as ``exc``.
    """
    detail = exc.detail
    if isinstance(detail, dict) and "error_code" in detail:
        payload = detail
    elif isinstance(detail, str):
        code = _status_to_default_code(exc.status_code)
        payload = error_detail(code, detail)
    else:
        payload = error_detail(INTERNAL, str(detail))
    return JSONResponse(payload, status_code=exc.status_code, headers=exc.headers)


def install_error_handlers(app: Starlette) -> None:
    """Register the v0.12 JSON error handler on ``app``.

    Args:
        app: The Starlette sub-app to install the handler on.
    """
    app.add_exception_handler(HTTPException, http_exception_handler)


def _status_to_default_code(status_code: int) -> str:
    """Return the default error_code for a bare ``HTTPException`` status code."""
    if status_code == 404:
        return NOT_FOUND
    if status_code == 403:
        return FORBIDDEN
    if status_code == 409:
        return CONFLICT
    if status_code >= 500:
        return INTERNAL
    return VALIDATION_ERROR

