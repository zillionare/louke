"""``/api/security`` Starlette sub-app: loopback and secret security HTTP endpoints.

Exposes the v0.12 runtime :class:`~louke.runtime.security.LoopbackGuard`,
:class:`~louke.runtime.security.CredentialStore` and
:class:`~louke.runtime.security.SecretRedactor` as a JSON HTTP API.

Endpoints:
    GET  /loopback                             - check if a host is loopback.
    POST /credentials                           - store a principal credential.
    GET  /credentials/{principal_id}/verify     - verify a credential.
    POST /redact                                - redact secrets from a payload.

Security contract:
    The plaintext credential is NEVER echoed in any response body. The
    ``CredentialStore`` hashes credentials with an HMAC so the plaintext is not
    retained, and responses only return boolean/status flags.

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

from louke.runtime.security import (
    CredentialStore,
    LoopbackGuard,
    SecretRedactor,
)

from ._common import (
    VALIDATION_ERROR,
    error_detail,
    install_error_handlers,
    json_body,
    require_str,
)

#: Attribute on ``app.state`` holding the lazily-created ``CredentialStore``.
_CRED_STORE_ATTR: str = "credential_store"

#: Attribute on ``app.state`` holding the lazily-created ``SecretRedactor``.
_REDACTOR_ATTR: str = "secret_redactor"


def create_app() -> Starlette:
    """Return a self-contained Starlette sub-app for ``/api/security``.

    Returns:
        A Starlette application whose routes are relative to ``/api/security``.
    """
    app = Starlette(routes=_routes())
    install_error_handlers(app)
    return app


def _routes() -> list[Route]:
    """Return the routes for the security sub-app."""
    return [
        Route("/loopback", endpoint=check_loopback),
        Route("/credentials", endpoint=set_credential, methods=["POST"]),
        Route(
            "/credentials/{principal_id}/verify",
            endpoint=verify_credential,
        ),
        Route("/redact", endpoint=redact_payload, methods=["POST"]),
    ]


def _credential_store(request: Request) -> CredentialStore:
    """Return the per-app ``CredentialStore``, creating it lazily on first use."""
    app = request.app
    store = getattr(app.state, _CRED_STORE_ATTR, None)
    if store is None:
        store = CredentialStore()
        setattr(app.state, _CRED_STORE_ATTR, store)
    return store


def _redactor(request: Request) -> SecretRedactor:
    """Return the per-app ``SecretRedactor``, creating it lazily on first use."""
    app = request.app
    redactor = getattr(app.state, _REDACTOR_ATTR, None)
    if redactor is None:
        redactor = SecretRedactor()
        setattr(app.state, _REDACTOR_ATTR, redactor)
    return redactor


async def check_loopback(request: Request) -> JSONResponse:
    """AC-NFR0401-01: check if a host is a loopback address.

    Query params:
        host: The host address to check.

    Returns:
        ``200`` with ``{"allowed": bool, "host": str}``. When the host is not
        loopback, ``allowed`` is ``False`` (the endpoint catches the
        ``PermissionError`` raised by the guard and reports it as not allowed
        rather than crashing).
    """
    host = request.query_params.get("host") or ""
    if not host.strip():
        raise HTTPException(
            status_code=400,
            detail=error_detail(VALIDATION_ERROR, "query param 'host' is required"),
        )
    guard = LoopbackGuard()
    try:
        guard.assert_loopback(host)
        allowed = True
    except PermissionError:
        allowed = False
    return JSONResponse({"allowed": allowed, "host": host})


async def set_credential(request: Request) -> JSONResponse:
    """AC-NFR0401-02: store a credential for a principal.

    Body:
        ``{"principal_id": str, "credential": str}``.

    Returns:
        ``201`` with ``{"principal_id": str, "credential_set": true}``.

    Security:
        The credential is hashed with an HMAC before storage; the plaintext
        is NEVER retained and NEVER echoed in the response body.
    """
    payload = await json_body(request)
    principal_id = require_str(payload, "principal_id")
    credential = require_str(payload, "credential")
    _credential_store(request).set_principal_credential(principal_id, credential)
    return JSONResponse(
        {"principal_id": principal_id, "credential_set": True},
        status_code=201,
    )


async def verify_credential(request: Request) -> JSONResponse:
    """AC-NFR0401-03: verify a credential against the stored hash.

    Path params:
        principal_id: The principal whose credential is being verified.

    Query params:
        credential: The plaintext credential to verify.

    Returns:
        ``200`` with ``{"valid": bool}``.

    Security:
        The stored credential plaintext is NEVER echoed in the response body.
        Only the boolean ``valid`` flag is returned.
    """
    principal_id = request.path_params["principal_id"]
    credential = request.query_params.get("credential") or ""
    if not credential.strip():
        raise HTTPException(
            status_code=400,
            detail=error_detail(
                VALIDATION_ERROR, "query param 'credential' is required"
            ),
        )
    valid = _credential_store(request).verify(principal_id, credential)
    return JSONResponse({"valid": valid})


async def redact_payload(request: Request) -> JSONResponse:
    """AC-NFR0401-03: redact registered secrets from an arbitrary payload.

    Body:
        ``{"payload": Any, "secrets": [str, ...]}``.

    Returns:
        ``200`` with ``{"payload": <redacted copy>}``. Each registered secret
        is replaced with ``"***"`` in all string values (including nested
        dicts and lists).
    """
    payload = await json_body(request)
    target = payload.get("payload")
    secrets = payload.get("secrets")
    if not isinstance(secrets, list):
        raise HTTPException(
            status_code=400,
            detail=error_detail(VALIDATION_ERROR, "field 'secrets' must be a list"),
        )
    redactor = _redactor(request)
    for secret in secrets:
        if not isinstance(secret, str):
            raise HTTPException(
                status_code=400,
                detail=error_detail(
                    VALIDATION_ERROR, "each secret must be a string"
                ),
            )
        redactor.register_secret(secret)
    redacted: Any = redactor.redact(target)
    return JSONResponse({"payload": redacted})
