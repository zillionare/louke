"""``/api/runtime/bindings`` Starlette sub-app: agent-model binding endpoints.

Exposes the v0.12 runtime :class:`~louke.runtime.agent_bindings.BindingStore`
as a JSON HTTP API. The sub-app reuses the shared in-memory
``WorkflowRunStore`` (via :func:`get_or_create_store`) to validate run
existence, and owns a per-app ``BindingStore`` built with the v0.12 default
models and available model set.

Endpoints:
    GET  /runs                          - create a run (helper for tests).
    GET  /{agent}?run_id=X              - list bindings for a run.
    PUT  /{agent}?run_id=X              - set a run-scoped model override.
    GET  /{agent}/audit?run_id=X        - list the binding audit trail.

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

from louke.runtime.agent_bindings import (
    BindingModelUnavailableError,
    BindingNotFoundError,
    BindingRevisionConflictError,
    BindingStore,
)
from louke.runtime.catalog import DefinitionNotFoundError
from louke.runtime.store import RunNotFoundError, WorkflowRunStore

from ._common import (
    NOT_FOUND,
    STALE,
    VALIDATION_ERROR,
    actor,
    error_detail,
    install_error_handlers,
    json_body,
    principal_id,
    require_str,
)
from ._runtime_store import AVAILABLE_MODELS, DEFAULT_MODELS, get_definition, get_or_create_store


def create_app() -> Starlette:
    """Return a self-contained Starlette sub-app for ``/api/runtime/bindings``.

    Returns:
        A Starlette application whose routes are relative to
        ``/api/runtime/bindings``.
    """
    app = Starlette(routes=_routes())
    install_error_handlers(app)
    app.add_exception_handler(DefinitionNotFoundError, _definition_not_found_handler)
    app.add_exception_handler(RunNotFoundError, _run_not_found_handler)
    app.add_exception_handler(BindingModelUnavailableError, _binding_model_unavailable_handler)
    app.add_exception_handler(BindingRevisionConflictError, _revision_conflict_handler)
    app.add_exception_handler(BindingNotFoundError, _binding_not_found_handler)
    return app


def _routes() -> list[Route]:
    """Return the routes for the bindings sub-app."""
    return [
        Route("/runs", endpoint=create_run, methods=["POST"]),
        Route("/{agent}", endpoint=list_bindings, methods=["GET"]),
        Route("/{agent}", endpoint=set_override, methods=["PUT"]),
        Route("/{agent}/audit", endpoint=list_audit),
    ]


def _store(request: Request) -> WorkflowRunStore:
    """Return the per-app ``WorkflowRunStore``, creating it lazily on first use."""
    return get_or_create_store(request.app)


def _binding_store(request: Request) -> BindingStore:
    """Return the per-app ``BindingStore``, creating it lazily on first use."""
    app = request.app
    binding_store = getattr(app.state, "binding_store", None)
    if binding_store is None:
        binding_store = BindingStore(
            default_models=DEFAULT_MODELS,
            available_models=AVAILABLE_MODELS,
        )
        app.state.binding_store = binding_store
    return binding_store


def _require_run_id(request: Request) -> str:
    """Return the ``run_id`` query param, raising VALIDATION_ERROR if missing."""
    run_id = request.query_params.get("run_id")
    if not run_id:
        raise HTTPException(
            status_code=400,
            detail=error_detail(VALIDATION_ERROR, "query param 'run_id' is required"),
        )
    return run_id


def _validate_run(request: Request, run_id: str) -> None:
    """Validate that ``run_id`` exists in the store, raising NOT_FOUND if not."""
    _store(request).get_run(run_id)


async def create_run(request: Request) -> JSONResponse:
    """Create a new workflow run so bindings have a run to attach to.

    Body:
        ``{"definition_id": str, "definition_version": str}``.

    Returns:
        ``201`` with the created :class:`WorkflowRun`.
    """
    payload = await json_body(request)
    definition_id = require_str(payload, "definition_id")
    definition_version = require_str(payload, "definition_version")
    store = _store(request)
    definition = get_definition(store, definition_id, definition_version)
    _ = actor(principal_id(request))
    run = store.create_run(definition)
    return JSONResponse(asdict(run), status_code=201)


async def list_bindings(request: Request) -> JSONResponse:
    """AC-FR1301-01: list all agent bindings for a run.

    Query params:
        run_id: The run to list bindings for.

    Returns:
        ``200`` with ``{"items": [AgentBindingSummary, ...]}``.
    """
    _ = request.path_params["agent"]
    run_id = _require_run_id(request)
    _validate_run(request, run_id)
    summaries = _binding_store(request).list_bindings(run_id)
    return JSONResponse({"items": [asdict(s) for s in summaries]})


async def set_override(request: Request) -> JSONResponse:
    """AC-FR1301-02: set a run-scoped model override for an agent.

    Path params:
        agent: The agent role to override.

    Query params:
        run_id: The run to set the override on.

    Body:
        ``{"model": str}``.

    Returns:
        ``200`` with the updated :class:`AgentBindingSummary`.
    """
    agent = request.path_params["agent"]
    run_id = _require_run_id(request)
    _validate_run(request, run_id)
    payload = await json_body(request)
    model = require_str(payload, "model")
    summary = _binding_store(request).set_override(
        run_id=run_id,
        agent_role=agent,
        model=model,
        actor=actor(principal_id(request)),
        # B1 simplification: always operate against the initial binding revision
        # (1). Optimistic-concurrency CAS on subsequent updates is deferred.
        expected_binding_revision=1,
    )
    return JSONResponse(asdict(summary))


async def list_audit(request: Request) -> JSONResponse:
    """AC-FR1301-04: list the binding audit trail for an agent on a run.

    Path params:
        agent: The agent role (informational; events are scoped to the run).

    Query params:
        run_id: The run to list audit events for.

    Returns:
        ``200`` with ``{"items": [BindingEvent, ...]}``.
    """
    _ = request.path_params["agent"]
    run_id = _require_run_id(request)
    _validate_run(request, run_id)
    events = _binding_store(request).list_binding_events(run_id)
    return JSONResponse({"items": [asdict(e) for e in events]})


def _definition_not_found_handler(_: Request, exc: Exception) -> JSONResponse:
    """Map :class:`DefinitionNotFoundError` to a 404 NOT_FOUND JSON response."""
    return JSONResponse(error_detail(NOT_FOUND, str(exc)), status_code=404)


def _run_not_found_handler(_: Request, exc: Exception) -> JSONResponse:
    """Map :class:`RunNotFoundError` to a 404 NOT_FOUND JSON response."""
    return JSONResponse(error_detail(NOT_FOUND, str(exc)), status_code=404)


def _binding_model_unavailable_handler(_: Request, exc: Exception) -> JSONResponse:
    """Map :class:`BindingModelUnavailableError` to a 400 VALIDATION_ERROR."""
    return JSONResponse(error_detail(VALIDATION_ERROR, str(exc)), status_code=400)


def _revision_conflict_handler(_: Request, exc: Exception) -> JSONResponse:
    """Map :class:`BindingRevisionConflictError` to a 409 STALE JSON response."""
    return JSONResponse(error_detail(STALE, str(exc)), status_code=409)


def _binding_not_found_handler(_: Request, exc: Exception) -> JSONResponse:
    """Map :class:`BindingNotFoundError` to a 404 NOT_FOUND JSON response."""
    return JSONResponse(error_detail(NOT_FOUND, str(exc)), status_code=404)
