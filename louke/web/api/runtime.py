"""``/api/runtime`` Starlette sub-app: workflow run HTTP endpoints.

Exposes the v0.12 runtime :class:`~louke.runtime.orchestrator.WorkflowOrchestrator`
and :class:`~louke.runtime.store.WorkflowRunStore` as a JSON HTTP API. The
sub-app is self-contained: it owns an in-memory ``WorkflowRunStore`` (via
:func:`get_or_create_store`) and a ``WorkflowOrchestrator`` built on top of it.

Endpoints:
    GET    /runs                       - list all persisted runs.
    POST   /runs                       - create a new workflow run.
    GET    /runs/{run_id}              - get a run's detail.
    GET    /runs/{run_id}/events       - list events for a run.
    POST   /runs/{run_id}/commands     - apply a runtime command to advance the run.
    POST   /runs/{run_id}/recover      - recover a run from needs_attention.

Error envelope (shared across v0.12 sub-apps)::

    HTTPException(status_code=4xx/5xx,
                   detail={"error_code": "...", "message": "..."})
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from louke.runtime.catalog import DefinitionNotFoundError
from louke.runtime.domain import (
    IllegalTransitionError,
    RevisionConflictError,
    RuntimeCommand,
    RuntimeStateError,
    UndeclaredResultError,
)
from louke.runtime.orchestrator import WorkflowOrchestrator
from louke.runtime.recovery import recover_run
from louke.runtime.store import RunNotFoundError, WorkflowRun, WorkflowRunStore

from ._common import (
    INTERNAL,
    NOT_FOUND,
    STALE,
    VALIDATION_ERROR,
    actor,
    error_detail,
    install_error_handlers,
    principal_id,
)
from ._runtime_store import get_definition, get_or_create_store


def create_app() -> Starlette:
    """Return a self-contained Starlette sub-app for ``/api/runtime``.

    The sub-app owns an in-memory ``WorkflowRunStore`` (lazily created on the
    first request via :func:`get_or_create_store`) and a
    ``WorkflowOrchestrator`` built on top of it.

    Returns:
        A Starlette application whose routes are relative to ``/api/runtime``.
    """
    app = Starlette(routes=_routes())
    install_error_handlers(app)
    app.add_exception_handler(DefinitionNotFoundError, _definition_not_found_handler)
    app.add_exception_handler(RunNotFoundError, _run_not_found_handler)
    app.add_exception_handler(RevisionConflictError, _revision_conflict_handler)
    app.add_exception_handler(IllegalTransitionError, _illegal_transition_handler)
    app.add_exception_handler(UndeclaredResultError, _undeclared_result_handler)
    app.add_exception_handler(RuntimeStateError, _runtime_state_handler)
    return app


def _routes() -> list[Route]:
    """Return the routes for the runtime sub-app."""
    return [
        Route("/runs", endpoint=list_runs),
        Route("/runs", endpoint=create_run, methods=["POST"]),
        Route("/runs/{run_id}", endpoint=get_run),
        Route("/runs/{run_id}/events", endpoint=list_events),
        Route("/runs/{run_id}/commands", endpoint=apply_command, methods=["POST"]),
        Route("/runs/{run_id}/recover", endpoint=recover_run_endpoint, methods=["POST"]),
    ]


def _store(request: Request) -> WorkflowRunStore:
    """Return the per-app ``WorkflowRunStore``, creating it lazily on first use."""
    return get_or_create_store(request.app)


def _orchestrator(request: Request) -> WorkflowOrchestrator:
    """Return the per-app ``WorkflowOrchestrator``, creating it lazily on first use."""
    app = request.app
    orchestrator = getattr(app.state, "orchestrator", None)
    if orchestrator is None:
        orchestrator = WorkflowOrchestrator(_store(request))
        app.state.orchestrator = orchestrator
    return orchestrator


def _run_to_dict(run: WorkflowRun) -> dict[str, Any]:
    """Return a JSON-serialisable dict for a ``WorkflowRun``."""
    return asdict(run)


def _event_to_dict(event: Any) -> dict[str, Any]:
    """Return a JSON-serialisable dict for a ``WorkflowEvent``."""
    return asdict(event)


async def list_runs(request: Request) -> JSONResponse:
    """AC-FR0201-01: list all persisted workflow runs.

    Returns:
        ``{"items": [WorkflowRun, ...]}`` ordered by ``updated_at`` desc.
    """
    runs = [_run_to_dict(r) for r in _store(request).list_runs()]
    return JSONResponse({"items": runs})


async def create_run(request: Request) -> JSONResponse:
    """AC-FR0001-01: create a new workflow run bound to a catalog definition.

    Body:
        ``{"definition_id": str, "definition_version": str}``.

    Returns:
        ``201`` with the created :class:`WorkflowRun`.
    """
    payload = await _json_body(request)
    definition_id = _require_str(payload, "definition_id")
    definition_version = _require_str(payload, "definition_version")
    store = _store(request)
    definition = get_definition(store, definition_id, definition_version)
    _ = actor(principal_id(request))
    run = store.create_run(definition)
    return JSONResponse(_run_to_dict(run), status_code=201)


async def get_run(request: Request) -> JSONResponse:
    """AC-FR0201-01: get a single run's detail by id.

    Path params:
        run_id: The opaque run identifier.

    Returns:
        ``200`` with the :class:`WorkflowRun`.
    """
    run_id = request.path_params["run_id"]
    run = _store(request).get_run(run_id)
    return JSONResponse(_run_to_dict(run))


async def list_events(request: Request) -> JSONResponse:
    """AC-FR0601-01: list events for a run in ascending sequence order.

    Path params:
        run_id: The opaque run identifier.

    Returns:
        ``200`` with ``{"items": [WorkflowEvent, ...]}``.
    """
    run_id = request.path_params["run_id"]
    # Validate run exists first so a missing run returns 404 rather than an
    # empty event list.
    _store(request).get_run(run_id)
    events = [_event_to_dict(e) for e in _store(request).get_events(run_id)]
    return JSONResponse({"items": events})


async def apply_command(request: Request) -> JSONResponse:
    """AC-FR0101-02: apply a runtime command to advance a run.

    Path params:
        run_id: The opaque run identifier.

    Body:
        ``{"expected_revision": int, "result": str | None,
           "requested_next_step": str | None,
           "idempotency_key": str | None}``.

    Returns:
        ``200`` with ``{"run": WorkflowRun, "event": WorkflowEvent}``.
    """
    run_id = request.path_params["run_id"]
    payload = await _json_body(request)
    expected_revision = _require_int(payload, "expected_revision")
    result = payload.get("result")
    requested_next_step = payload.get("requested_next_step")
    idempotency_key = payload.get("idempotency_key")
    principal = principal_id(request)
    command = RuntimeCommand(
        run_id=run_id,
        expected_revision=expected_revision,
        result=result,
        requested_next_step=requested_next_step,
        idempotency_key=idempotency_key,
    )
    outcome = _orchestrator(request).apply_command(command, actor=actor(principal))
    return JSONResponse(
        {
            "run": _run_to_dict(outcome.run),
            "event": _event_to_dict(outcome.event),
        }
    )


async def recover_run_endpoint(request: Request) -> JSONResponse:
    """AC-FR2001-01: recover a run from needs_attention after an uncertain interruption.

    Path params:
        run_id: The opaque run identifier.

    Returns:
        ``200`` with the recovered :class:`WorkflowRun`. If the run has no
        uncertain step attempts, it is returned unchanged.
    """
    run_id = request.path_params["run_id"]
    run = recover_run(_store(request), run_id)
    return JSONResponse(_run_to_dict(run))


def _definition_not_found_handler(_: Request, exc: Exception) -> JSONResponse:
    """Map :class:`DefinitionNotFoundError` to a 404 NOT_FOUND JSON response."""
    return JSONResponse(error_detail(NOT_FOUND, str(exc)), status_code=404)


def _run_not_found_handler(_: Request, exc: Exception) -> JSONResponse:
    """Map :class:`RunNotFoundError` to a 404 NOT_FOUND JSON response."""
    return JSONResponse(error_detail(NOT_FOUND, str(exc)), status_code=404)


def _revision_conflict_handler(_: Request, exc: Exception) -> JSONResponse:
    """Map :class:`RevisionConflictError` to a 409 STALE JSON response."""
    return JSONResponse(error_detail(STALE, str(exc)), status_code=409)


def _illegal_transition_handler(_: Request, exc: Exception) -> JSONResponse:
    """Map :class:`IllegalTransitionError` to a 400 VALIDATION_ERROR JSON response."""
    return JSONResponse(error_detail(VALIDATION_ERROR, str(exc)), status_code=400)


def _undeclared_result_handler(_: Request, exc: Exception) -> JSONResponse:
    """Map :class:`UndeclaredResultError` to a 400 VALIDATION_ERROR JSON response."""
    return JSONResponse(error_detail(VALIDATION_ERROR, str(exc)), status_code=400)


def _runtime_state_handler(_: Request, exc: Exception) -> JSONResponse:
    """Map :class:`RuntimeStateError` to a 500 INTERNAL JSON response."""
    return JSONResponse(error_detail(INTERNAL, str(exc)), status_code=500)


async def _json_body(request: Request) -> dict[str, Any]:
    """Return the parsed JSON body, raising VALIDATION_ERROR on malformed JSON."""
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=error_detail(VALIDATION_ERROR, "request body must be valid JSON"),
        ) from exc
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400,
            detail=error_detail(VALIDATION_ERROR, "request body must be a JSON object"),
        )
    return payload


def _require_str(payload: dict[str, Any], field: str) -> str:
    """Return ``payload[field]`` as a non-empty string, else VALIDATION_ERROR."""
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise HTTPException(
            status_code=400,
            detail=error_detail(VALIDATION_ERROR, f"field {field!r} is required"),
        )
    return value


def _require_int(payload: dict[str, Any], field: str) -> int:
    """Return ``payload[field]`` as an int, else VALIDATION_ERROR."""
    value = payload.get(field)
    if not isinstance(value, int) or isinstance(value, bool):
        raise HTTPException(
            status_code=400,
            detail=error_detail(VALIDATION_ERROR, f"field {field!r} must be an integer"),
        )
    return value
