"""``/api/projects`` Starlette sub-app: project lifecycle HTTP endpoints.

Exposes the v0.12 runtime :class:`~louke.runtime.projects.ProjectStore` as a
JSON HTTP API. The sub-app is self-contained: it owns an in-memory
``WorkflowRunStore`` (via :func:`build_run_store`) and a
``ProjectStore`` built on top of it.

Endpoints:
    GET    /active              - list active (non-terminal) projects.
    GET    /history             - list terminal/archived projects.
    GET    /backlog             - list backlog entries (blocked creations).
    GET    /catalog             - list selectable workflow definitions.
    POST   /preview             - preview a project without creating it.
    POST   /confirm             - confirm a preview and create the project.
    POST   /create              - create a project directly.
    GET    /{project_id}        - get a project's detail.
    POST   /{project_id}/archive - archive a project.

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
from louke.runtime.projects import (
    ProjectConflictError,
    ProjectNotFoundError,
    ProjectStore,
)

from ._common import (
    CONFLICT,
    NOT_FOUND,
    VALIDATION_ERROR,
    actor,
    error_detail,
    install_error_handlers,
    principal_id,
)
from ._runtime_store import get_or_create_store


def create_app() -> Starlette:
    """Return a self-contained Starlette sub-app for ``/api/projects``.

    The sub-app owns an in-memory ``WorkflowRunStore`` (lazily created on the
    first request via :func:`get_or_create_store`) and a ``ProjectStore``
    built on top of it.

    Returns:
        A Starlette application whose routes are relative to ``/api/projects``.
    """
    app = Starlette(routes=_routes())
    install_error_handlers(app)
    app.add_exception_handler(ProjectConflictError, _conflict_handler)
    app.add_exception_handler(DefinitionNotFoundError, _definition_not_found_handler)
    app.add_exception_handler(KeyError, _key_error_handler)
    app.add_exception_handler(ValueError, _value_error_handler)
    return app


def _conflict_handler(_: Request, exc: Exception) -> JSONResponse:
    """Map :class:`ProjectConflictError` to a 409 CONFLICT JSON response."""
    return JSONResponse(error_detail(CONFLICT, str(exc)), status_code=409)


def _definition_not_found_handler(_: Request, exc: Exception) -> JSONResponse:
    """Map :class:`DefinitionNotFoundError` to a 404 NOT_FOUND JSON response."""
    return JSONResponse(error_detail(NOT_FOUND, str(exc)), status_code=404)


def _key_error_handler(_: Request, exc: KeyError) -> JSONResponse:
    """Map :class:`KeyError` (unknown workflow id / preview id) to 404."""
    return JSONResponse(error_detail(NOT_FOUND, str(exc)), status_code=404)


def _value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    """Map :class:`ValueError` (invalid input) to a 400 VALIDATION_ERROR."""
    return JSONResponse(error_detail(VALIDATION_ERROR, str(exc)), status_code=400)


def _routes() -> list[Route]:
    """Return the routes for the projects sub-app."""
    return [
        Route("/active", endpoint=list_active),
        Route("/history", endpoint=list_history),
        Route("/backlog", endpoint=list_backlog),
        Route("/catalog", endpoint=list_catalog),
        Route("/preview", endpoint=preview_project, methods=["POST"]),
        Route("/confirm", endpoint=confirm_project, methods=["POST"]),
        Route("/create", endpoint=create_project, methods=["POST"]),
        Route("/{project_id}", endpoint=get_project),
        Route("/{project_id}/archive", endpoint=archive_project, methods=["POST"]),
    ]


def _project_store(request: Request) -> ProjectStore:
    """Return the per-app ``ProjectStore``, creating it lazily on first use."""
    app = request.app
    project_store = getattr(app.state, "project_store", None)
    if project_store is None:
        project_store = ProjectStore(run_store=get_or_create_store(app))
        app.state.project_store = project_store
    return project_store


async def list_active(request: Request) -> JSONResponse:
    """AC-FR1001-01: list non-terminal, non-archived projects.

    Returns:
        ``{"items": [ProjectSummary, ...]}``.
    """
    items = [asdict(s) for s in _project_store(request).list_active()]
    return JSONResponse({"items": items})


async def list_history(request: Request) -> JSONResponse:
    """AC-FR1001-01: list terminal/archived projects.

    Returns:
        ``{"items": [ProjectSummary, ...]}``.
    """
    items = [asdict(s) for s in _project_store(request).list_history()]
    return JSONResponse({"items": items})


async def list_backlog(request: Request) -> JSONResponse:
    """AC-FR1001-01: list backlog entries (stories blocked at creation).

    Returns:
        ``{"items": [BacklogEntry, ...]}``.
    """
    items = [asdict(b) for b in _project_store(request).list_backlog()]
    return JSONResponse({"items": items})


async def list_catalog(request: Request) -> JSONResponse:
    """AC-FR1101-01: list selectable workflow definitions for project creation.

    Returns:
        ``{"items": [CatalogEntry, ...]}`` with ``new_feature`` and
        ``bug_fix`` (``spec_change`` is excluded from the first catalog).
    """
    items = [asdict(c) for c in _project_store(request).list_workflow_catalog()]
    return JSONResponse({"items": items})


async def preview_project(request: Request) -> JSONResponse:
    """AC-FR1101-01..03: validate inputs and return a preview without creating.

    Body:
        ``{"story": str, "release_version": "vX.Y.Z", "definition_id": str,
           "definition_version": str,
           "source_contract": dict | None}``.

    Returns:
        ``200`` with the ``ProjectPreview`` (no ``project_id`` yet).
    """
    payload = await _json_body(request)
    story = _require_str(payload, "story")
    release_version = _require_str(payload, "release_version")
    definition_id = _require_str(payload, "definition_id")
    definition_version = _require_str(payload, "definition_version")
    source_contract = payload.get("source_contract")
    _ = actor(principal_id(request))
    preview = _project_store(request).preview_project(
        story=story,
        release_version=release_version,
        definition_id=definition_id,
        definition_version=definition_version,
        source_contract=source_contract,
    )
    return JSONResponse(asdict(preview))


async def confirm_project(request: Request) -> JSONResponse:
    """AC-FR1101-02: confirm a preview and create the project.

    Body:
        ``{"preview_id": str}``.

    Returns:
        ``201`` with the created :class:`Project`.
    """
    payload = await _json_body(request)
    preview_id = _require_str(payload, "preview_id")
    project = _project_store(request).confirm_project(preview_id)
    return JSONResponse(asdict(project), status_code=201)


async def create_project(request: Request) -> JSONResponse:
    """AC-FR1101-03: create a project and its first workflow run directly.

    Body:
        ``{"story": str, "release_version": "vX.Y.Z", "definition_id": str,
           "definition_version": str,
           "source_contract": dict | None}``.

    Returns:
        ``201`` with the created :class:`Project`.
    """
    payload = await _json_body(request)
    story = _require_str(payload, "story")
    release_version = _require_str(payload, "release_version")
    definition_id = _require_str(payload, "definition_id")
    definition_version = _require_str(payload, "definition_version")
    source_contract = payload.get("source_contract")
    _ = actor(principal_id(request))
    project = _project_store(request).create_project(
        story=story,
        release_version=release_version,
        definition_id=definition_id,
        definition_version=definition_version,
        source_contract=source_contract,
    )
    return JSONResponse(asdict(project), status_code=201)


async def get_project(request: Request) -> JSONResponse:
    """AC-FR1001-03: get a single project's detail by id.

    Path params:
        project_id: The opaque project identifier.

    Returns:
        ``200`` with the :class:`Project`.
    """
    project_id = request.path_params["project_id"]
    try:
        project = _project_store(request).get_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=error_detail(NOT_FOUND, str(exc)),
        ) from exc
    return JSONResponse(asdict(project))


async def archive_project(request: Request) -> JSONResponse:
    """AC-FR1001-02: archive a project, moving it from active to history.

    Path params:
        project_id: The opaque project identifier.

    Returns:
        ``200`` with the archived :class:`Project``.
    """
    project_id = request.path_params["project_id"]
    try:
        archived = _project_store(request).archive_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=error_detail(NOT_FOUND, str(exc)),
        ) from exc
    return JSONResponse(asdict(archived))


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
