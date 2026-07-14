"""``/api/gates`` Starlette sub-app: human gate HTTP endpoints.

Exposes the v0.12 runtime :class:`~louke.runtime.gates.GateService` as a JSON
HTTP API. The sub-app is self-contained: it owns an in-memory
``WorkflowRunStore`` (via :func:`get_or_create_store`) and a
``GateService`` built on top of it.

Endpoints:
    GET  /runs/{run_id}/gates        - list gates for a run.
    GET  /{gate_id}                   - get a gate's detail.
    POST /{gate_id}/decisions         - submit a gate decision (approve/reject).

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

from louke.runtime.gates import (
    DuplicateDecisionError,
    GateError,
    GateNotFoundError,
    GateService,
    Gate,
)
from louke.runtime.store import RunNotFoundError, WorkflowRunStore
from louke.runtime.gates import UnauthenticatedPrincipalError, StaleGateError

from ._common import (
    FORBIDDEN,
    NOT_FOUND,
    STALE,
    VALIDATION_ERROR,
    error_detail,
    install_error_handlers,
    json_body,
    require_str,
)
from ._runtime_store import get_or_create_store


def create_app(run_store: WorkflowRunStore | None = None) -> Starlette:
    """Return a self-contained Starlette sub-app for ``/api/gates``.

    Args:
        run_store: Optional injected ``WorkflowRunStore``. When ``None``, a
            fresh in-memory store with the v0.12 catalog is created lazily on
            the first request.

    Returns:
        A Starlette application whose routes are relative to ``/api/gates``.
    """
    app = Starlette(routes=_routes())
    install_error_handlers(app)
    app.add_exception_handler(GateNotFoundError, _gate_not_found_handler)
    app.add_exception_handler(RunNotFoundError, _run_not_found_handler)
    app.add_exception_handler(UnauthenticatedPrincipalError, _unauthenticated_handler)
    app.add_exception_handler(StaleGateError, _stale_gate_handler)
    app.add_exception_handler(DuplicateDecisionError, _duplicate_decision_handler)
    app.add_exception_handler(GateError, _gate_error_handler)
    if run_store is not None:
        app.state.v12_run_store = run_store
    return app


def _routes() -> list[Route]:
    """Return the routes for the gates sub-app."""
    return [
        Route("/runs/{run_id}/gates", endpoint=list_gates_for_run),
        Route("/{gate_id}", endpoint=get_gate),
        Route("/{gate_id}/decisions", endpoint=submit_decision, methods=["POST"]),
    ]


def _store(request: Request) -> WorkflowRunStore:
    """Return the per-app ``WorkflowRunStore``, creating it lazily on first use."""
    return get_or_create_store(request.app)


def _gate_service(request: Request) -> GateService:
    """Return the per-app ``GateService``, creating it lazily on first use."""
    app = request.app
    service = getattr(app.state, "gate_service", None)
    if service is None:
        service = GateService(_store(request))
        app.state.gate_service = service
    return service


async def list_gates_for_run(request: Request) -> JSONResponse:
    """AC-FR0501-01: list gates for a run.

    Path params:
        run_id: The opaque run identifier.

    Returns:
        ``200`` with ``{"items": [Gate, ...]}``.
    """
    run_id = request.path_params["run_id"]
    store = _store(request)
    # Validate run exists so a missing run returns 404 rather than an empty list.
    store.get_run(run_id)
    gates: list[Gate] = []
    # The store has no public list-gates-for-run method; query the gates table.
    rows = store._conn.execute(
        "SELECT * FROM gates WHERE run_id = ? ORDER BY created_at", (run_id,)
    ).fetchall()
    from louke.runtime.store import _row_to_gate

    gates = [_row_to_gate(row) for row in rows]
    return JSONResponse({"items": [asdict(g) for g in gates]})


async def get_gate(request: Request) -> JSONResponse:
    """AC-FR0501-03: get a single gate's detail by id.

    Path params:
        gate_id: The opaque gate identifier.

    Returns:
        ``200`` with the :class:`Gate`.
    """
    gate_id = request.path_params["gate_id"]
    gate = _store(request).get_gate(gate_id)
    return JSONResponse(asdict(gate))


async def submit_decision(request: Request) -> JSONResponse:
    """AC-FR0501-02: submit a gate decision (approve or reject).

    Path params:
        gate_id: The opaque gate identifier.

    Body:
        ``{"run_id": str, "decision": "approve"|"reject", "bound_digest": str,
           "expected_revision": int, "principal": {"kind": "human", "id": str},
           "reason": str | None}``.

    Returns:
        ``200`` with the updated :class:`Gate`.
    """
    gate_id = request.path_params["gate_id"]
    payload = await json_body(request)
    run_id = require_str(payload, "run_id")
    decision = require_str(payload, "decision")
    bound_digest = require_str(payload, "bound_digest")
    expected_revision = payload.get("expected_revision")
    if not isinstance(expected_revision, int) or isinstance(expected_revision, bool):
        raise HTTPException(
            status_code=400,
            detail=error_detail(VALIDATION_ERROR, "field 'expected_revision' must be an integer"),
        )
    principal = payload.get("principal")
    if not isinstance(principal, dict):
        raise HTTPException(
            status_code=400,
            detail=error_detail(VALIDATION_ERROR, "field 'principal' is required"),
        )
    reason = payload.get("reason")
    gate = _gate_service(request).submit_decision(
        run_id=run_id,
        gate_id=gate_id,
        decision=decision,
        bound_digest=bound_digest,
        expected_revision=expected_revision,
        principal=principal,
        reason=reason,
    )
    return JSONResponse(asdict(gate))


def _gate_not_found_handler(_: Request, exc: Exception) -> JSONResponse:
    """Map :class:`GateNotFoundError` to a 404 NOT_FOUND JSON response."""
    return JSONResponse(error_detail(NOT_FOUND, str(exc)), status_code=404)


def _run_not_found_handler(_: Request, exc: Exception) -> JSONResponse:
    """Map :class:`RunNotFoundError` to a 404 NOT_FOUND JSON response."""
    return JSONResponse(error_detail(NOT_FOUND, str(exc)), status_code=404)


def _unauthenticated_handler(_: Request, exc: Exception) -> JSONResponse:
    """Map :class:`UnauthenticatedPrincipalError` to 403 FORBIDDEN."""
    return JSONResponse(error_detail(FORBIDDEN, str(exc)), status_code=403)


def _stale_gate_handler(_: Request, exc: Exception) -> JSONResponse:
    """Map :class:`StaleGateError` to a 409 STALE JSON response."""
    return JSONResponse(error_detail(STALE, str(exc)), status_code=409)


def _duplicate_decision_handler(_: Request, exc: Exception) -> JSONResponse:
    """Map :class:`DuplicateDecisionError` to a 409 CONFLICT JSON response."""
    from ._common import CONFLICT

    return JSONResponse(error_detail(CONFLICT, str(exc)), status_code=409)


def _gate_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Map :class:`GateError` to a 400 VALIDATION_ERROR JSON response."""
    return JSONResponse(error_detail(VALIDATION_ERROR, str(exc)), status_code=400)
