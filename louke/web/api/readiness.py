"""``/api/readiness`` Starlette sub-app: workspace readiness endpoint.

Exposes the v0.12 runtime :class:`~louke.runtime.workspace_init.InitWizard`
readiness report as a JSON HTTP API. The sub-app constructs a fresh
``InitWizard`` per request (it is cheap and stateless for readiness checks).

Endpoints:
    GET  /   - return the current readiness report.

Error envelope (shared across v0.12 sub-apps)::

    HTTPException(status_code=4xx/5xx,
                   detail={"error_code": "...", "message": "..."})
"""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from louke.runtime.workspace_init import (
    InitWizard,
    ReadinessCheck,
    ReadinessReport,
    ReadinessStatus,
)

from ._common import install_error_handlers

#: Placeholder model id reported in the Models readiness check (B1 placeholder).
_DEFAULT_MODEL: str = "default-model"


def create_app() -> Starlette:
    """Return a self-contained Starlette sub-app for ``/api/readiness``.

    Returns:
        A Starlette application whose routes are relative to ``/api/readiness``.
    """
    app = Starlette(routes=_routes())
    install_error_handlers(app)
    return app


def _routes() -> list[Route]:
    """Return the routes for the readiness sub-app."""
    return [Route("/", endpoint=get_readiness)]


def _build_report() -> ReadinessReport:
    """Return the current workspace readiness report.

    Delegates to :class:`InitWizard` for Git/Store/Catalog/OpenCode, then
    appends a Models check that is always READY with a fixed
    ``default-model`` placeholder (real model negotiation is deferred).
    OpenCode is forced to BLOCKED because the real adapter arrives in B4.
    """
    wizard = InitWizard(repo_path=".", opcodes_available=False)
    base = wizard.readiness()
    models_check = ReadinessCheck(
        name="Models",
        status=ReadinessStatus.READY,
        diagnosis=f"default model: {_DEFAULT_MODEL}",
        remediation="none",
    )
    return ReadinessReport(items=base.items + (models_check,))


async def get_readiness(request: Request) -> JSONResponse:
    """AC-FR1801-04: return the current workspace readiness report.

    Returns:
        ``200`` with ``{"items": [ReadinessCheck, ...]}``.
    """
    report = _build_report()
    return JSONResponse({"items": [_check_to_dict(c) for c in report.items]})


def _check_to_dict(check: ReadinessCheck) -> dict[str, str]:
    """Return a JSON-serialisable dict for a ``ReadinessCheck``.

    The ``status`` enum is rendered as its name (``READY``/``DEGRADED``/``BLOCKED``)
    so the HTTP response is plain JSON.
    """
    return {
        "name": check.name,
        "status": check.status.name,
        "diagnosis": check.diagnosis,
        "remediation": check.remediation,
    }
