"""``/api/v12/discussions`` Starlette sub-app: inline discussion HTTP endpoints.

Exposes the v0.12 runtime
:class:`~louke.runtime.project_detail.InlineDiscussionStore` as a JSON HTTP API.

Endpoints:
    POST /              - add a new inline discussion thread.
    GET  /{thread_id}   - return the canonical serialized form of a thread.
    POST /parse          - parse a canonical discussion form.

Canonical form:
    Threads are persisted in a canonical ``speaker/depth/status`` form that the
    gate parser can round-trip. Non-round-trippable input is rejected with a
    400 and a human-readable reason.

Error envelope (shared across v0.12 sub-apps)::

    HTTPException(status_code=4xx/5xx,
                   detail={"error_code": "...", "message": "..."})
"""

from __future__ import annotations

from dataclasses import asdict

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from louke.runtime.project_detail import (
    DiscussionStatus,
    DiscussionThread,
    InlineDiscussionStore,
)

from ._common import (
    NOT_FOUND,
    VALIDATION_ERROR,
    error_detail,
    install_error_handlers,
    json_body,
    require_str,
)

#: Attribute on ``app.state`` holding the lazily-created ``InlineDiscussionStore``.
_STORE_ATTR: str = "discussion_store"

#: Map of status string -> ``DiscussionStatus`` enum accepted by the API.
_STATUS_MAP: dict[str, DiscussionStatus] = {
    "open": DiscussionStatus.OPEN,
    "resolved": DiscussionStatus.RESOLVED,
    "reopened": DiscussionStatus.REOPENED,
}


def create_app() -> Starlette:
    """Return a self-contained Starlette sub-app for ``/api/v12/discussions``.

    Returns:
        A Starlette application whose routes are relative to
        ``/api/v12/discussions``.
    """
    app = Starlette(routes=_routes())
    install_error_handlers(app)
    app.add_exception_handler(KeyError, _key_error_handler)
    app.add_exception_handler(ValueError, _value_error_handler)
    return app


def _routes() -> list[Route]:
    """Return the routes for the discussions sub-app."""
    return [
        Route("/", endpoint=add_thread, methods=["POST"]),
        Route("/{thread_id}", endpoint=get_canonical),
        Route("/parse", endpoint=parse_canonical, methods=["POST"]),
    ]


def _store(request: Request) -> InlineDiscussionStore:
    """Return the per-app ``InlineDiscussionStore``, creating it lazily on first use."""
    app = request.app
    store = getattr(app.state, _STORE_ATTR, None)
    if store is None:
        store = InlineDiscussionStore()
        setattr(app.state, _STORE_ATTR, store)
    return store


def _thread_to_dict(thread: DiscussionThread) -> dict[str, object]:
    """Return a JSON-serialisable dict for a ``DiscussionThread``.

    The ``status`` enum is rendered as its lowercase value so the HTTP
    response is plain JSON.
    """
    data = asdict(thread)
    data["status"] = thread.status.value
    return data


async def add_thread(request: Request) -> JSONResponse:
    """AC-FR1901-07: add a new inline discussion thread.

    Body:
        ``{"doc_id": str, "anchor": str, "speaker": str, "body": str}``.

    Returns:
        ``201`` with ``{"thread_id": str, ...thread fields}``.

    Raises:
        HTTPException: ``400 VALIDATION_ERROR`` if required fields are missing.
    """
    payload = await json_body(request)
    doc_id = require_str(payload, "doc_id")
    anchor = require_str(payload, "anchor")
    speaker = require_str(payload, "speaker")
    body = require_str(payload, "body")
    status_str = str(payload.get("status") or "open").lower()
    status = _STATUS_MAP.get(status_str)
    if status is None:
        raise HTTPException(
            status_code=400,
            detail=error_detail(
                VALIDATION_ERROR,
                f"status {status_str!r} must be open/resolved/reopened",
            ),
        )
    thread = _store(request).add(
        doc_id=doc_id,
        anchor=anchor,
        speaker=speaker,
        body=body,
        status=status,
    )
    return JSONResponse(_thread_to_dict(thread), status_code=201)


async def get_canonical(request: Request) -> JSONResponse:
    """AC-FR1901-07: return the canonical serialized form of a thread.

    Path params:
        thread_id: The opaque thread identifier.

    Returns:
        ``200`` with ``{"thread_id": str, "canonical": str}`` where
        ``canonical`` is the canonical ``speaker/depth/status`` JSON string
        that the gate parser can round-trip.

    Raises:
        HTTPException: ``404 NOT_FOUND`` if the thread does not exist.
    """
    thread_id = request.path_params["thread_id"]
    store = _store(request)
    try:
        canonical = store.to_canonical(thread_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=error_detail(NOT_FOUND, f"thread {thread_id!r} not found"),
        ) from None
    return JSONResponse({"thread_id": thread_id, "canonical": canonical})


async def parse_canonical(request: Request) -> JSONResponse:
    """AC-FR1901-07: parse a canonical discussion form.

    Body:
        ``{"canonical": str}``.

    Returns:
        ``200`` with ``{"parsed": dict}`` containing the parsed thread fields.

    Raises:
        HTTPException: ``400 VALIDATION_ERROR`` if the canonical form is
            invalid (non-JSON or missing required speaker/depth/status fields).
    """
    payload = await json_body(request)
    canonical = require_str(payload, "canonical")
    store = _store(request)
    try:
        parsed = store.parse_canonical(canonical)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                **error_detail(VALIDATION_ERROR, str(exc)),
                "reason": str(exc),
            },
        ) from exc
    return JSONResponse({"parsed": parsed})


def _key_error_handler(_: Request, exc: KeyError) -> JSONResponse:
    """Map :class:`KeyError` (unknown thread) to 404 NOT_FOUND."""
    return JSONResponse(error_detail(NOT_FOUND, str(exc)), status_code=404)


def _value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    """Map :class:`ValueError` (invalid canonical form) to 400 VALIDATION_ERROR."""
    return JSONResponse(error_detail(VALIDATION_ERROR, str(exc)), status_code=400)
