"""``/api/migration`` Starlette sub-app: legacy workspace adoption HTTP endpoints.

Exposes the v0.12 runtime :class:`~louke.runtime.legacy_adoption.MigrationWizard`
and legacy history as a JSON HTTP API. The sub-app owns an in-memory
``MigrationWizard`` per workspace path (created lazily on first use).

Endpoints:
    GET  /preview    - generate a read-only migration preview.
    POST /confirm    - confirm a migration after preview.
    POST /rollback   - roll back a confirmed migration.
    GET  /legacy     - fetch a read-only legacy history entry.
    POST /mistaken   - record a mistaken creation as cancelled.

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

from louke.runtime.legacy_adoption import (
    MigrationMode,
    MigrationPreview,
    MigrationWizard,
    RollbackError,
)
from louke.runtime.failure_recovery import ArchiveGuard

from ._common import (
    CONFLICT,
    NOT_FOUND,
    VALIDATION_ERROR,
    error_detail,
    install_error_handlers,
    json_body,
    require_str,
)

#: Attribute on ``app.state`` holding lazily-created wizards keyed by path.
_WIZARDS_ATTR: str = "migration_wizards"

#: Attribute on ``app.state`` holding the lazily-created ``ArchiveGuard``.
_ARCHIVE_GUARD_ATTR: str = "archive_guard"


def create_app() -> Starlette:
    """Return a self-contained Starlette sub-app for ``/api/migration``.

    Returns:
        A Starlette application whose routes are relative to ``/api/migration``.
    """
    app = Starlette(routes=_routes())
    install_error_handlers(app)
    app.add_exception_handler(RollbackError, _rollback_error_handler)
    app.add_exception_handler(KeyError, _key_error_handler)
    return app


def _routes() -> list[Route]:
    """Return the routes for the migration sub-app."""
    return [
        Route("/preview", endpoint=preview),
        Route("/confirm", endpoint=confirm, methods=["POST"]),
        Route("/rollback", endpoint=rollback, methods=["POST"]),
        Route("/legacy", endpoint=get_legacy),
        Route("/mistaken", endpoint=record_mistaken, methods=["POST"]),
    ]


def _wizards(request: Request) -> dict[str, MigrationWizard]:
    """Return the per-app wizard registry, creating it lazily on first use."""
    app = request.app
    wizards: dict[str, MigrationWizard] | None = getattr(
        app.state, _WIZARDS_ATTR, None
    )
    if wizards is None:
        wizards = {}
        setattr(app.state, _WIZARDS_ATTR, wizards)
    return wizards


def _wizard(request: Request, workspace_path: str) -> MigrationWizard:
    """Return the ``MigrationWizard`` for ``workspace_path``, creating it lazily.

    A single wizard is cached per workspace path so preview/confirm/rollback
    operate on the same in-memory state across requests.
    """
    wizards = _wizards(request)
    wizard = wizards.get(workspace_path)
    if wizard is None:
        wizard = MigrationWizard(workspace_path)
        wizards[workspace_path] = wizard
    return wizard


def _archive_guard(request: Request) -> ArchiveGuard:
    """Return the per-app ``ArchiveGuard``, creating it lazily on first use."""
    app = request.app
    guard = getattr(app.state, _ARCHIVE_GUARD_ATTR, None)
    if guard is None:
        guard = ArchiveGuard()
        setattr(app.state, _ARCHIVE_GUARD_ATTR, guard)
    return guard


def _preview_to_dict(preview: MigrationPreview) -> dict[str, Any]:
    """Return a JSON-serialisable dict for a ``MigrationPreview``.

    The ``MigrationMode`` enums are rendered as their lowercase names so the
    HTTP response is plain JSON without enum serialization.
    """
    data = asdict(preview)
    data["recommended_mode"] = preview.recommended_mode.name.lower()
    data["available_modes"] = tuple(m.name.lower() for m in preview.available_modes)
    return data


async def preview(request: Request) -> JSONResponse:
    """AC-FR2301-01: generate and return a read-only migration preview.

    Query params:
        workspace_path: The workspace root to preview.

    Returns:
        ``200`` with the :class:`MigrationPreview` fields. The preview lists
        additions, conversions, preserved, conflicts, unsupported, recommended
        and available modes, with ``old_bytes_modified=False`` before confirm.
    """
    workspace_path = request.query_params.get("workspace_path") or ""
    if not workspace_path.strip():
        raise HTTPException(
            status_code=400,
            detail=error_detail(
                VALIDATION_ERROR, "query param 'workspace_path' is required"
            ),
        )
    wizard = _wizard(request, workspace_path)
    return JSONResponse(_preview_to_dict(wizard.generate_preview()))


async def confirm(request: Request) -> JSONResponse:
    """AC-FR2301-02: confirm a migration after preview.

    Body:
        ``{"workspace_path": str, "mode": "local"|"global"}``.

    Returns:
        ``200`` with ``{"workspace_path": str, "committed": bool,
        "has_restore_point": bool}``.

    Raises:
        HTTPException: ``409 CONFLICT`` if no preview was generated first.
        HTTPException: ``400 VALIDATION_ERROR`` if the mode is invalid.
    """
    payload = await json_body(request)
    workspace_path = require_str(payload, "workspace_path")
    mode_str = require_str(payload, "mode")
    try:
        mode = MigrationMode[mode_str.upper()]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=error_detail(
                VALIDATION_ERROR, f"mode {mode_str!r} must be 'local' or 'global'"
            ),
        ) from None
    wizard = _wizard(request, workspace_path)
    try:
        wizard.confirm(mode)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=409,
            detail=error_detail(CONFLICT, str(exc)),
        ) from exc
    return JSONResponse(
        {
            "workspace_path": workspace_path,
            "committed": True,
            "has_restore_point": wizard.has_restore_point(),
        }
    )


async def rollback(request: Request) -> JSONResponse:
    """AC-FR2301-02: roll back a confirmed migration.

    Body:
        ``{"workspace_path": str}``.

    Returns:
        ``200`` with ``{"workspace_path": str, "rolled_back": bool}``.

    Raises:
        HTTPException: ``409 CONFLICT`` if no restore point exists.
    """
    payload = await json_body(request)
    workspace_path = require_str(payload, "workspace_path")
    wizard = _wizard(request, workspace_path)
    try:
        wizard.rollback()
    except RollbackError as exc:
        raise HTTPException(
            status_code=409,
            detail=error_detail(CONFLICT, str(exc)),
        ) from exc
    return JSONResponse(
        {"workspace_path": workspace_path, "rolled_back": wizard.is_rolled_back()}
    )


async def get_legacy(request: Request) -> JSONResponse:
    """AC-FR2301-03: fetch a read-only legacy history entry.

    Query params:
        project_id: The legacy project identifier.

    Returns:
        ``200`` with the :class:`LegacyEntry` fields. Entries are read-only
        and marked ``is_legacy=True``.

    Raises:
        HTTPException: ``404 NOT_FOUND`` if no entry exists for ``project_id``.
    """
    project_id = request.query_params.get("project_id") or ""
    if not project_id.strip():
        raise HTTPException(
            status_code=400,
            detail=error_detail(
                VALIDATION_ERROR, "query param 'project_id' is required"
            ),
        )
    guard = _archive_guard(request)
    try:
        status = guard.get_status(project_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=error_detail(
                NOT_FOUND, f"legacy entry {project_id!r} not found"
            ),
        ) from None
    return JSONResponse(
        {
            "project_id": project_id,
            "status": status,
            "is_legacy": True,
            "read_only": True,
        }
    )


async def record_mistaken(request: Request) -> JSONResponse:
    """AC-FR2301-05/AC-FR2001-05: record a mistaken creation as cancelled.

    Body:
        ``{"project_id": str, "reason": str}``.

    Returns:
        ``201`` with ``{"project_id": str, "recorded": bool, "status": "cancelled"}``.

    Mistaken creations are retained as cancelled records rather than being
    physically deleted, so the history remains honest about the error.
    """
    payload = await json_body(request)
    project_id = require_str(payload, "project_id")
    reason = payload.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise HTTPException(
            status_code=400,
            detail=error_detail(VALIDATION_ERROR, "field 'reason' is required"),
        )
    guard = _archive_guard(request)
    guard.record_mistaken_creation(run_id=project_id, reason=reason)
    return JSONResponse(
        {"project_id": project_id, "recorded": True, "status": "cancelled"},
        status_code=201,
    )


def _rollback_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Map :class:`RollbackError` to a 409 CONFLICT JSON response."""
    return JSONResponse(error_detail(CONFLICT, str(exc)), status_code=409)


def _key_error_handler(_: Request, exc: KeyError) -> JSONResponse:
    """Map :class:`KeyError` (missing legacy entry) to 404 NOT_FOUND."""
    return JSONResponse(error_detail(NOT_FOUND, str(exc)), status_code=404)
