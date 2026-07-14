"""``/api/opencode`` Starlette sub-app: OpenCode instance lifecycle (mock).

.. note::

    This sub-app is an **honest placeholder**. The only adapter today is
    :class:`~louke.opencode.in_memory.InMemoryOpenCodeAdapter`, which echoes
    messages rather than calling a real OpenCode binary. Every response
    includes ``adapter_kind: "mock"`` so the frontend can render a warning
    that the real adapter arrives in B4 (AC-FR1401-01).

Endpoints:
    GET    /instances                   - list instances.
    POST   /instances                   - create an instance.
    DELETE /instances?id=X              - stop an instance.
    GET    /instances/{id}/messages     - list messages.
    POST   /instances/{id}/messages     - send a message (echo).
    GET    /status                      - return adapter status.

Error envelope (shared across v0.12 sub-apps)::

    HTTPException(status_code=4xx/5xx,
                   detail={"error_code": "...", "message": "..."})
"""

from __future__ import annotations

from typing import Any

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from louke.opencode.in_memory import InMemoryOpenCodeAdapter

from ._common import NOT_FOUND, VALIDATION_ERROR, error_detail, install_error_handlers, json_body, require_str

#: Adapter kind label included in every response so the frontend can warn.
_ADAPTER_KIND: str = "mock"


def create_app() -> Starlette:
    """Return a self-contained Starlette sub-app for ``/api/opencode``.

    Returns:
        A Starlette application whose routes are relative to ``/api/opencode``.
    """
    app = Starlette(routes=_routes())
    install_error_handlers(app)
    return app


def _routes() -> list[Route]:
    """Return the routes for the opencode sub-app."""
    return [
        Route("/instances", endpoint=list_instances),
        Route("/instances", endpoint=create_instance, methods=["POST"]),
        Route("/instances", endpoint=stop_instance, methods=["DELETE"]),
        Route("/instances/{instance_id}/messages", endpoint=list_messages),
        Route("/instances/{instance_id}/messages", endpoint=send_message, methods=["POST"]),
        Route("/status", endpoint=get_status),
    ]


def _adapter(request: Request) -> InMemoryOpenCodeAdapter:
    """Return the per-app ``InMemoryOpenCodeAdapter``, created lazily on first use."""
    app = request.app
    adapter = getattr(app.state, "opencode_adapter", None)
    if adapter is None:
        adapter = InMemoryOpenCodeAdapter()
        app.state.opencode_adapter = adapter
    return adapter


def _mock_envelope(extra: dict[str, Any]) -> dict[str, Any]:
    """Return ``extra`` with the ``adapter_kind: "mock"`` label prepended."""
    return {"adapter_kind": _ADAPTER_KIND, **extra}


async def list_instances(request: Request) -> JSONResponse:
    """AC-FR1401-01: list all OpenCode instances (mock).

    Returns:
        ``200`` with ``{"adapter_kind": "mock", "items": [...]}``.
    """
    instances = _adapter(request).list()
    return JSONResponse(_mock_envelope({"items": [i.to_dict() for i in instances]}))


async def create_instance(request: Request) -> JSONResponse:
    """AC-FR1401-01: create a new OpenCode instance (mock).

    Returns:
        ``201`` with ``{"adapter_kind": "mock", "instance": {...}}``.
    """
    instance = _adapter(request).create(correlation_id="mock")
    return JSONResponse(_mock_envelope({"instance": instance.to_dict()}), status_code=201)


async def stop_instance(request: Request) -> JSONResponse:
    """AC-FR1401-01: stop an OpenCode instance by id (mock).

    Query params:
        id: The instance id to stop.

    Returns:
        ``200`` with ``{"adapter_kind": "mock", "instance": {...}}``.
    """
    instance_id = request.query_params.get("id")
    if not instance_id:
        raise HTTPException(
            status_code=400,
            detail=error_detail(VALIDATION_ERROR, "query param 'id' is required"),
        )
    instance = _adapter(request).stop(instance_id)
    return JSONResponse(_mock_envelope({"instance": instance.to_dict()}))


async def list_messages(request: Request) -> JSONResponse:
    """AC-FR1401-01: list messages for an instance (mock).

    Path params:
        instance_id: The instance to list messages for.

    Returns:
        ``200`` with ``{"adapter_kind": "mock", "items": [...]}``.
    """
    instance_id = request.path_params["instance_id"]
    try:
        messages = _adapter(request).list_messages(instance_id, after_message_id=None)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=error_detail(NOT_FOUND, f"instance {instance_id!r} not found"),
        )
    return JSONResponse(_mock_envelope({"items": [m.to_dict() for m in messages]}))


async def send_message(request: Request) -> JSONResponse:
    """AC-FR1401-01: send a message to an instance and get an echo reply (mock).

    Path params:
        instance_id: The instance to send the message to.

    Body:
        ``{"content": str}``.

    Returns:
        ``200`` with ``{"adapter_kind": "mock", "reply": {...}}``.
    """
    instance_id = request.path_params["instance_id"]
    payload = await json_body(request)
    content = require_str(payload, "content")
    try:
        user_msg, _ok = _adapter(request).send_message(
            instance_id, content, correlation_id="mock"
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=error_detail(NOT_FOUND, f"instance {instance_id!r} not found"),
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=400,
            detail=error_detail(VALIDATION_ERROR, str(exc)),
        )
    return JSONResponse(_mock_envelope({"message": user_msg.to_dict()}))


async def get_status(request: Request) -> JSONResponse:
    """Return the adapter status (always mock, ready, with a pending message).

    Returns:
        ``200`` with ``{"adapter_kind": "mock", "ready": true,
        "message": "real adapter pending"}``.
    """
    _ = request
    return JSONResponse(
        _mock_envelope({"ready": True, "message": "real adapter pending"})
    )
