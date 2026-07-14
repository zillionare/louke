"""``/api/setup`` Starlette sub-app: first-user setup endpoints.

Exposes the v0.12 runtime :class:`~louke.runtime.workspace_init.InitWizard`
first-principal flow and :class:`~louke.runtime.security.CredentialStore` as a
JSON HTTP API. The sub-app owns a per-app ``InitWizard`` and
``CredentialStore``.

Endpoints:
    GET  /status       - return initialized flag and first principal id.
    POST /first-user   - create the first local human principal.

Error envelope (shared across v0.12 sub-apps)::

    HTTPException(status_code=4xx/5xx,
                   detail={"error_code": "...", "message": "..."})
"""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from louke.runtime.security import CredentialStore
from louke.runtime.workspace_init import InitWizard, WorkspacePrincipal

from ._common import install_error_handlers, json_body, require_str

#: Attribute on ``app.state`` holding the lazily-created ``InitWizard``.
_WIZARD_ATTR: str = "init_wizard"

#: Attribute on ``app.state`` holding the lazily-created ``CredentialStore``.
_CRED_STORE_ATTR: str = "credential_store"

#: Attribute on ``app.state`` holding the first principal id (if any).
_FIRST_PRINCIPAL_ATTR: str = "first_principal_id"


def create_app() -> Starlette:
    """Return a self-contained Starlette sub-app for ``/api/setup``.

    Returns:
        A Starlette application whose routes are relative to ``/api/setup``.
    """
    app = Starlette(routes=_routes())
    install_error_handlers(app)
    return app


def _routes() -> list[Route]:
    """Return the routes for the setup sub-app."""
    return [
        Route("/status", endpoint=get_status),
        Route("/first-user", endpoint=create_first_user, methods=["POST"]),
    ]


def _wizard(request: Request) -> InitWizard:
    """Return the per-app ``InitWizard``, creating it lazily on first use."""
    app = request.app
    wizard = getattr(app.state, _WIZARD_ATTR, None)
    if wizard is None:
        wizard = InitWizard(repo_path=".", opcodes_available=False)
        setattr(app.state, _WIZARD_ATTR, wizard)
    return wizard


def _credential_store(request: Request) -> CredentialStore:
    """Return the per-app ``CredentialStore``, creating it lazily on first use."""
    app = request.app
    store = getattr(app.state, _CRED_STORE_ATTR, None)
    if store is None:
        store = CredentialStore()
        setattr(app.state, _CRED_STORE_ATTR, store)
    return store


async def get_status(request: Request) -> JSONResponse:
    """AC-FR1801-03: return the workspace setup status.

    Returns:
        ``200`` with ``{"initialized": bool, "first_principal_id": str | None}``.
    """
    wizard = _wizard(request)
    # InitWizard has no public accessor for the principal id; track it in
    # app state so we avoid reaching into private attributes.
    principal_id = getattr(request.app.state, _FIRST_PRINCIPAL_ATTR, None)
    return JSONResponse(
        {
            "initialized": wizard.can_make_gate_decision(),
            "first_principal_id": principal_id,
        }
    )


async def create_first_user(request: Request) -> JSONResponse:
    """AC-FR1801-03: create the first local human principal.

    Body:
        ``{"name": str, "credential": str}``.

    Returns:
        ``201`` with ``{"principal_id": str, "name": str}``.
    """
    payload = await json_body(request)
    name = require_str(payload, "name")
    credential = require_str(payload, "credential")
    principal = WorkspacePrincipal(name=name)
    _wizard(request).create_first_principal(principal)
    _credential_store(request).set_principal_credential(principal.id, credential)
    setattr(request.app.state, _FIRST_PRINCIPAL_ATTR, principal.id)
    return JSONResponse(
        {"principal_id": principal.id, "name": principal.name},
        status_code=201,
    )
