"""``/api/opencode`` Starlette sub-app: OpenCode instance lifecycle.

This sub-app dispatches to either the in-memory mock adapter or the real
HTTP adapter (selected via ``LOUKE_OPENCODE_BACKEND`` or an injected
adapter). Every response carries ``adapter_kind`` (``mock`` | ``real``)
so the frontend can warn when the real adapter is not wired.

Endpoints:
    GET    /instances                        - list instances.
    POST   /instances                        - create an instance.
    DELETE /instances?id=X                   - stop an instance.
    GET    /instances/{id}/messages?after=X  - list messages.
    POST   /instances/{id}/messages           - send a message.
    POST   /instances/{id}/abort             - cancel current generation (AC-04).
    POST   /instances/{id}/recover           - classify instance reachability (AC-05).
    GET    /status                           - return adapter status.

Error envelope (shared across v0.12 sub-apps)::

    HTTPException(status_code=4xx/5xx,
                   detail={"error_code": "...", "message": "..."})

For ``adapter_kind == "real"`` a failing upstream is surfaced as a real
HTTP error (503/502/504/500) and never silently faked as a 200 echo.
"""

from __future__ import annotations

import os
import json
import time
from pathlib import Path
from typing import Any, Optional

import httpx
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.responses import StreamingResponse
from starlette.routing import Route
from starlette.concurrency import iterate_in_threadpool

from louke.opencode import dispatch
from louke.opencode.adapter import Instance
from louke.opencode.persistence import (
    ManagedInstanceState,
    OpenCodeInstanceStore,
)

from ._common import (
    NOT_FOUND,
    VALIDATION_ERROR,
    error_detail,
    install_error_handlers,
    json_body,
    require_str,
)

#: Attribute on ``app.state`` holding the cached adapter (per-app singleton).
_ADAPTER_ATTR: str = "v12_opencode_adapter"
#: Attribute on ``app.state`` holding the workspace root Path.
_WORKSPACE_ATTR: str = "v12_opencode_workspace"
#: Attribute on ``app.state`` holding the OpenCodeInstanceStore (real mode only).
_STORE_ATTR: str = "v12_opencode_store"

#: Error codes for the real-mode failure envelope (B5).
OPENCODE_UNAVAILABLE: str = "OPENCODE_UNAVAILABLE"
OPENCODE_UPSTREAM_ERROR: str = "OPENCODE_UPSTREAM_ERROR"
OPENCODE_TIMEOUT: str = "OPENCODE_TIMEOUT"
OPENCODE_INTERNAL: str = "OPENCODE_INTERNAL"


def create_app(
    adapter: Any = None,
    workspace_root: Optional[Path] = None,
) -> Starlette:
    """Return a self-contained Starlette sub-app for ``/api/opencode``.

    Args:
        adapter: Injectable adapter (for tests). When ``None``, the adapter
            is lazily resolved on the first request via
            :func:`dispatch.get_default_adapter`, honoring the
            ``LOUKE_OPENCODE_BACKEND`` env var.
        workspace_root: Workspace root used for instance persistence in
            real mode. When ``None``, lazily resolved from the
            ``project.toml`` parent or ``cwd``.

    Returns:
        A Starlette application whose routes are relative to ``/api/opencode``.
    """
    app = Starlette(routes=_routes())
    install_error_handlers(app)
    app.state.v12_opencode_adapter = adapter
    app.state.v12_opencode_workspace = workspace_root
    app.state.v12_opencode_store = None
    return app


def _routes() -> list[Route]:
    """Return the routes for the opencode sub-app."""
    return [
        Route("/instances", endpoint=list_instances),
        Route("/instances", endpoint=create_instance, methods=["POST"]),
        Route("/instances", endpoint=stop_instance, methods=["DELETE"]),
        Route(
            "/instances/{instance_id}/messages",
            endpoint=list_messages,
        ),
        Route(
            "/instances/{instance_id}/messages",
            endpoint=send_message,
            methods=["POST"],
        ),
        Route(
            "/instances/{instance_id}/events",
            endpoint=stream_instance_events,
        ),
        Route(
            "/instances/{instance_id}/abort",
            endpoint=abort_instance,
            methods=["POST"],
        ),
        Route(
            "/instances/{instance_id}/recover",
            endpoint=recover_instance,
            methods=["POST"],
        ),
        Route("/status", endpoint=get_status),
    ]


# ---------------------------------------------------------------------------
# Adapter / store resolution
# ---------------------------------------------------------------------------


def _kind_of(adapter: Any) -> str:
    """Return the adapter kind label (``real`` | ``mock``).

    Detection is based on the presence of ``_base_url``, which only the
    :class:`RealOpenCodeAdapter` carries. Any other adapter (including the
    in-memory mock) is reported as ``mock``.

    Args:
        adapter: The cached adapter (or None).

    Returns:
        ``"real"`` when the adapter exposes ``_base_url``, else ``"mock"``.
    """
    if adapter is not None and hasattr(adapter, "_base_url"):
        return "real"
    return "mock"


def _cached_kind(request: Request) -> str:
    """Return the kind of the app's cached adapter (``mock`` if unresolved).

    Used by exception handlers to decide whether a generic ``Exception``
    came from the real-adapter path (and should be mapped to a 5xx) or from
    the mock path (where it should re-raise).

    Args:
        request: The incoming Starlette request.

    Returns:
        ``"real"`` or ``"mock"``.
    """
    return _kind_of(getattr(request.app.state, _ADAPTER_ATTR, None))


def _resolve_adapter_or_cached(request: Request) -> Any:
    """Return the adapter already cached on the app state.

    Counterpart to :func:`_adapter_call`: after a successful call the
    adapter has been resolved and cached, so this just reads it back. It
    never triggers a fresh resolution (and therefore cannot raise).

    Args:
        request: The incoming Starlette request.

    Returns:
        The cached adapter (or None when nothing has been cached yet).
    """
    return getattr(request.app.state, _ADAPTER_ATTR, None)


def _resolve_adapter(request: Request) -> Any:
    """Return the per-app adapter, resolving it lazily on first use.

    When the app was built with ``adapter=None`` (the production path), the
    adapter is resolved via :func:`dispatch.get_default_adapter`, which
    honors ``LOUKE_OPENCODE_BACKEND``. Resolution failures (e.g. ``real``
    requested without a base URL) raise ValueError; callers must surface
    these as 503 rather than silently falling back to the mock.

    Args:
        request: The incoming Starlette request.

    Returns:
        The cached or newly-resolved adapter.

    Raises:
        ValueError: When ``real`` is requested but no base URL is set.
    """
    app = request.app
    adapter = getattr(app.state, _ADAPTER_ATTR, None)
    if adapter is not None:
        return adapter
    workspace = _resolve_workspace(app)
    adapter = dispatch.get_default_adapter(workspace_root=workspace)
    setattr(app.state, _ADAPTER_ATTR, adapter)
    return adapter


def _resolve_workspace(app: Starlette) -> Optional[Path]:
    """Return the cached workspace root, or lazily resolve one.

    Resolution order:
        1. The ``workspace_root`` passed to :func:`create_app` (may be None).
        2. The parent of ``.louke/project/project.toml`` (when present).
        3. The current working directory.

    Args:
        app: The Starlette sub-app.

    Returns:
        The resolved workspace root Path, or None when unset and the
        project.toml lookup is skipped (used only as a hint for the
        real adapter's persisted-base-url fallback).
    """
    cached = getattr(app.state, _WORKSPACE_ATTR, None)
    if cached is not None:
        return cached
    candidate = Path.cwd() / ".louke" / "project" / "project.toml"
    if candidate.is_file():
        resolved = candidate.parent.parent.parent
    else:
        resolved = Path.cwd()
    setattr(app.state, _WORKSPACE_ATTR, resolved)
    return resolved


def _store_for(request: Request) -> Optional[OpenCodeInstanceStore]:
    """Return the per-app ``OpenCodeInstanceStore`` (real mode only).

    The store is created lazily under the cached workspace root. Returns
    ``None`` when no workspace root is available or when the adapter is a
    mock (mock mode never persists).

    Args:
        request: The incoming Starlette request.

    Returns:
        The cached or newly-created store, or ``None`` in mock mode.
    """
    app = request.app
    store = getattr(app.state, _STORE_ATTR, None)
    if store is not None:
        return store
    workspace = _resolve_workspace(app)
    if workspace is None:
        return None
    store = OpenCodeInstanceStore(workspace)
    setattr(app.state, _STORE_ATTR, store)
    return store


def _envelope(adapter: Any, extra: dict[str, Any]) -> dict[str, Any]:
    """Return ``extra`` with the ``adapter_kind`` label prepended."""
    return {"adapter_kind": _kind_of(adapter), **extra}


# ---------------------------------------------------------------------------
# Real-mode error mapping
# ---------------------------------------------------------------------------


def _real_error_response(exc: Exception) -> JSONResponse:
    """Map a real-adapter exception to a structured 5xx response.

    Mapping:
        * ``httpx.TimeoutException``            -> 504 OPENCODE_TIMEOUT
        * ``httpx.HTTPStatusError``            -> 502 OPENCODE_UPSTREAM_ERROR
        * Any other exception in the real path -> 500 OPENCODE_INTERNAL

    Args:
        exc: The exception raised by the real adapter.

    Returns:
        A ``JSONResponse`` with ``adapter_kind: "real"`` and the mapped
        error code/message.
    """
    if isinstance(exc, httpx.TimeoutException):
        return _real_error(504, OPENCODE_TIMEOUT, f"opencode timeout: {exc}")
    if isinstance(exc, httpx.HTTPStatusError):
        return _real_error(
            502, OPENCODE_UPSTREAM_ERROR, f"opencode upstream error: {exc}"
        )
    return _real_error(500, OPENCODE_INTERNAL, f"opencode internal error: {exc}")


def _real_error(status: int, code: str, message: str) -> JSONResponse:
    """Return a structured 5xx JSONResponse tagged ``adapter_kind: real``."""
    return JSONResponse(
        {
            "adapter_kind": "real",
            "error_code": code,
            "message": message,
            "ready": False,
        },
        status_code=status,
    )


def _real_unavailable(message: str) -> JSONResponse:
    """Return the 503 OPENCODE_UNAVAILABLE response (no base URL / dispatch failure)."""
    return _real_error(503, OPENCODE_UNAVAILABLE, message)


def _resolve_or_error(request: Request) -> tuple[Any, Optional[JSONResponse]]:
    """Resolve the cached adapter or return a real-mode error response.

    Centralizes the ``ValueError -> 503`` and ``Exception -> 5xx`` mapping
    that every handler needs, so the handler bodies can focus on the
    adapter call itself rather than repeating the same try/except shell.

    Args:
        request: The incoming Starlette request.

    Returns:
        A tuple ``(adapter, None)`` on success, or ``(None, response)``
        when resolution failed and a structured 5xx response should be
        returned to the client.
    """
    try:
        return _resolve_adapter(request), None
    except ValueError as exc:
        return None, _real_unavailable(str(exc))
    except Exception as exc:
        if _cached_kind(request) == "real":
            return None, _real_error_response(exc)
        raise


def _adapter_call(
    request: Request, fn: str, *args: Any, **kwargs: Any
) -> tuple[Any, Optional[JSONResponse]]:
    """Invoke an adapter method with the shared real-mode error mapping.

    Args:
        request: The incoming Starlette request.
        fn: The adapter method name to call.
        *args: Positional args forwarded to the method.
        **kwargs: Keyword args forwarded to the method.

    Returns:
        A tuple ``(result, None)`` on success, where ``result`` is the
        adapter method's return value; or ``(None, response)`` when the
        call failed and a structured 5xx response should be returned.

    Raises:
        Exception: Any non-ValueError exception raised in mock mode
            (real mode converts them to a 5xx response instead).
    """
    adapter, err = _resolve_or_error(request)
    if err is not None:
        return None, err
    try:
        return getattr(adapter, fn)(*args, **kwargs), None
    except ValueError as exc:
        return None, _real_unavailable(str(exc))
    except Exception as exc:
        if _cached_kind(request) == "real":
            return None, _real_error_response(exc)
        raise


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


async def list_instances(request: Request) -> JSONResponse:
    """AC-FR1401-01: list all OpenCode instances.

    Returns:
        ``200`` with ``{"adapter_kind": ..., "items": [...]}``.

    Raises:
        HTTPException: ``503`` (real, no base URL) or ``502/504/500`` on
            upstream failure.
    """
    result, err = _adapter_call(request, "list")
    if err is not None:
        return err
    adapter = _resolve_adapter_or_cached(request)
    return JSONResponse(_envelope(adapter, {"items": [i.to_dict() for i in result]}))


async def create_instance(request: Request) -> JSONResponse:
    """AC-FR1401-01/05: create a new OpenCode instance.

    In real mode the new instance is persisted to
    :class:`OpenCodeInstanceStore` so it survives a Louke restart.

    Returns:
        ``201`` with ``{"adapter_kind": ..., "instance": {...}}``.
    """
    instance, err = _adapter_call(request, "create", correlation_id="web")
    if err is not None:
        return err
    adapter = _resolve_adapter_or_cached(request)
    if _kind_of(adapter) == "real":
        _persist_instance(request, adapter, instance)
    return JSONResponse(
        _envelope(adapter, {"instance": instance.to_dict()}),
        status_code=201,
    )


def _persist_instance(request: Request, adapter: Any, instance: Instance) -> None:
    """Persist a newly created instance's state (real mode only).

    Args:
        request: The incoming request (for store resolution).
        adapter: The real adapter (its ``_base_url`` is persisted).
        instance: The newly created instance.
    """
    store = _store_for(request)
    if store is None:
        return
    base_url = getattr(adapter, "_base_url", None)
    state = ManagedInstanceState(
        instance_id=instance.id,
        workspace_path=str(_resolve_workspace(request.app) or Path.cwd()),
        pid=os.getpid(),
        base_url=base_url,
        last_seen=time.time(),
        status="running",
    )
    store.save(state)


async def stop_instance(request: Request) -> JSONResponse:
    """AC-FR1401-01/04: stop an OpenCode instance by id.

    Query params:
        id: The instance id to stop.

    Returns:
        ``200`` with ``{"adapter_kind": ..., "instance": {...}}``.
    """
    instance_id = request.query_params.get("id")
    if not instance_id:
        raise HTTPException(
            status_code=400,
            detail=error_detail(VALIDATION_ERROR, "query param 'id' is required"),
        )
    instance, err = _adapter_call(request, "stop", instance_id)
    if err is not None:
        return err
    adapter = _resolve_adapter_or_cached(request)
    if _kind_of(adapter) == "real":
        _mark_stopped(request, instance_id)
    return JSONResponse(_envelope(adapter, {"instance": instance.to_dict()}))


def _mark_stopped(request: Request, instance_id: str) -> None:
    """Mark a persisted instance as ``stopped`` (real mode only)."""
    store = _store_for(request)
    if store is None:
        return
    states = store.load_all()
    for state in states:
        if state.instance_id == instance_id:
            state.status = "stopped"
            state.last_seen = time.time()
            store.save(state)
            break


async def list_messages(request: Request) -> JSONResponse:
    """AC-FR1401-01: list messages for an instance.

    Path params:
        instance_id: The instance to list messages for.

    Query params:
        after: Optional message id cursor.

    Returns:
        ``200`` with ``{"adapter_kind": ..., "items": [...]}``.
    """
    instance_id = request.path_params["instance_id"]
    after = request.query_params.get("after")
    try:
        messages, err = _adapter_call(
            request, "list_messages", instance_id, after_message_id=after
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=error_detail(NOT_FOUND, f"instance {instance_id!r} not found"),
        )
    if err is not None:
        return err
    adapter = _resolve_adapter_or_cached(request)
    return JSONResponse(_envelope(adapter, {"items": [m.to_dict() for m in messages]}))


async def send_message(request: Request) -> JSONResponse:
    """AC-FR1401-01: send a message to an instance.

    Path params:
        instance_id: The instance to send the message to.

    Body:
        ``{"content": str}``.

    Returns:
        ``200`` with ``{"adapter_kind": ..., "message": {...}, "accepted": bool}``
        where ``accepted`` means "204 prompt received, async reply pending".
    """
    instance_id = request.path_params["instance_id"]
    payload = await json_body(request)
    content = require_str(payload, "content")
    try:
        result, err = _adapter_call(
            request, "send_message", instance_id, content, correlation_id="web"
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
    if err is not None:
        return err
    user_msg, accepted = result
    adapter = _resolve_adapter_or_cached(request)
    return JSONResponse(
        _envelope(adapter, {"message": user_msg.to_dict(), "accepted": accepted})
    )


async def stream_instance_events(request: Request) -> StreamingResponse | JSONResponse:
    """Bridge the adapter's normalized events as an SSE response."""
    adapter, err = _resolve_or_error(request)
    if err is not None:
        return err
    stream = getattr(adapter, "stream_events", None)
    if stream is None:
        return _real_error(
            503, "OPENCODE_STREAM_UNAVAILABLE", "adapter has no event stream"
        )
    instance_id = request.path_params["instance_id"]
    last_event_id = request.headers.get("last-event-id")

    async def events():
        async for event in iterate_in_threadpool(stream(instance_id, last_event_id)):
            payload = event.to_dict()
            event_name = {
                "delta": "chat.message.delta",
                "completed": "chat.message.completed",
                "error": "chat.message.error",
            }[event.type]
            yield (
                f"id: {event.event_id}\n"
                f"event: {event_name}\n"
                f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            ).encode("utf-8")

    return StreamingResponse(events(), media_type="text/event-stream")


async def abort_instance(request: Request) -> JSONResponse:
    """AC-FR1401-04: cancel the current generation for an instance.

    Calls ``adapter.cancel(id)`` when available; falls back to
    ``adapter.stop(id)`` otherwise. Returns 202 (the cancellation is
    asynchronous from the assistant's perspective).

    Path params:
        instance_id: The instance to abort the current generation on.
    """
    instance_id = request.path_params["instance_id"]
    adapter, err = _resolve_or_error(request)
    if err is not None:
        return err
    try:
        if hasattr(adapter, "cancel"):
            adapter.cancel(instance_id, correlation_id="web")
        else:
            _result, call_err = _adapter_call(request, "stop", instance_id)
            if call_err is not None:
                return call_err
    except Exception as exc:
        if _cached_kind(request) == "real":
            return _real_error_response(exc)
        raise
    return JSONResponse(_envelope(adapter, {"aborted": instance_id}), status_code=202)


async def recover_instance(request: Request) -> JSONResponse:
    """AC-FR1401-05: classify an instance's reachability.

    Path params:
        instance_id: The instance to classify.

    Returns:
        ``200`` with ``{"adapter_kind": ..., "status": "running|lost|needs_attention"}``.

    Classification:
        * ``running``         - adapter lists the id.
        * ``lost``            - persisted pid is dead (authoritative).
        * ``needs_attention`` - adapter reachable but id missing, pid alive.
    """
    instance_id = request.path_params["instance_id"]
    live_list, err = _adapter_call(request, "list")
    if err is not None:
        return err
    adapter = _resolve_adapter_or_cached(request)
    live_ids = {i.id for i in live_list}
    status = _classify_recovery(instance_id, live_ids, request)
    return JSONResponse(_envelope(adapter, {"status": status}))


def _classify_recovery(
    instance_id: str,
    live_ids: set[str],
    request: Request,
) -> str:
    """Classify an instance as ``running`` | ``lost`` | ``needs_attention``.

    The pid check is authoritative: a dead pid yields ``lost`` even if the
    adapter were to claim the instance is present.

    Args:
        instance_id: The instance to classify.
        live_ids: Ids reported by the adapter.
        request: The incoming request (for store resolution).

    Returns:
        One of ``running``, ``lost``, ``needs_attention``.
    """
    if instance_id in live_ids:
        return "running"
    store = _store_for(request)
    if store is None:
        return "needs_attention"
    states = store.load_all()
    state = next((s for s in states if s.instance_id == instance_id), None)
    if state is None:
        return "needs_attention"
    if state.pid is not None and not _pid_alive(state.pid):
        return "lost"
    return "needs_attention"


def _pid_alive(pid: int) -> bool:
    """Return True if ``pid`` is a live process.

    Args:
        pid: The pid to probe.

    Returns:
        True if the process exists.
    """
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


async def get_status(request: Request) -> JSONResponse:
    """Return the adapter status.

    Returns:
        ``200`` with ``{"adapter_kind": ..., "ready": bool, "message": str,
        "base_url": str|None, "recovered_states": int}``.

    For ``real`` mode: if the adapter cannot be resolved (no base URL),
    returns ``503`` with ``adapter_kind: "real"`` and ``ready: false``.
    """
    adapter, err = _resolve_or_error(request)
    if err is not None:
        return err
    if _kind_of(adapter) == "real":
        return _real_status(adapter, request)
    return JSONResponse(
        _envelope(
            adapter,
            {
                "ready": True,
                "message": "real adapter pending",
                "base_url": None,
                "recovered_states": 0,
            },
        )
    )


def _real_status(adapter: Any, request: Request) -> JSONResponse:
    """Build the real-mode status response.

    Performs a best-effort health probe (``GET /global/health``) and counts
    persisted states. On probe failure the response is still 200 but with
    ``ready: false`` and the error message.
    """
    base_url = getattr(adapter, "_base_url", None)
    recovered = _count_recovered_states(request)
    try:
        healthy = _probe_health(adapter)
    except Exception as exc:
        return JSONResponse(
            _envelope(
                adapter,
                {
                    "ready": False,
                    "message": f"health probe failed: {exc}",
                    "base_url": base_url,
                    "recovered_states": recovered,
                },
            )
        )
    return JSONResponse(
        _envelope(
            adapter,
            {
                "ready": bool(healthy),
                "message": "ok" if healthy else "unhealthy",
                "base_url": base_url,
                "recovered_states": recovered,
            },
        )
    )


def _probe_health(adapter: Any) -> bool:
    """Probe the real adapter's health (``GET /global/health``).

    Args:
        adapter: A real adapter exposing ``probe_version``.

    Returns:
        True when the server reports ``healthy: true``.

    Raises:
        Exception: On transport or non-2xx failure.
    """
    if not hasattr(adapter, "probe_version"):
        return True
    data = adapter.probe_version()
    return bool(data.get("healthy", True))


def _count_recovered_states(request: Request) -> int:
    """Return the number of persisted instance states (0 in mock mode)."""
    store = _store_for(request)
    if store is None:
        return 0
    return len(store.load_all())
