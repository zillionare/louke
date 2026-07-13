"""Loopback identity and secret security controls (NFR-0401).

This module provides runtime security primitives: loopback binding, encrypted
credential storage, secret redaction across artifacts/logs/errors, and
idempotent request validation with replay detection.
"""

from __future__ import annotations

import hmac
import json
import secrets
from typing import Any


class ReplayDetectedError(ValueError):
    """Raised when a request nonce has already been used."""


class LoopbackGuard:
    """Enforce loopback-only Web server binding."""

    def default_host(self) -> str:
        """Return the default loopback host."""
        return "127.0.0.1"

    def assert_loopback(self, host: str) -> None:
        """Raise if ``host`` is not a loopback address.

        Args:
            host: Client/server host address.

        Raises:
            PermissionError: If ``host`` is not loopback.
        """
        if host not in {"127.0.0.1", "::1", "localhost"}:
            raise PermissionError(
                f"non-loopback host {host!r} is not supported in this release; "
                "bind to 127.0.0.1 or configure external transport protection"
            )


class CredentialStore:
    """Store principal credentials without persisting plaintext."""

    def __init__(self) -> None:
        self._secret = secrets.token_hex(32)
        self._credentials: dict[str, str] = {}
        self._valid_sessions: set[str] = set()

    def _hash(self, credential: str) -> str:
        """Return an HMAC digest of ``credential`` using the store secret."""
        return hmac.new(
            self._secret.encode(), credential.encode(), "sha256"
        ).hexdigest()

    def set_principal_credential(self, principal_id: str, credential: str) -> None:
        """Store a credential for ``principal_id``.

        The credential is hashed with an HMAC so the plaintext is not retained.
        """
        self._credentials[principal_id] = self._hash(credential)
        self._valid_sessions.add(principal_id)

    def verify(self, principal_id: str, credential: str) -> bool:
        """Return True if ``credential`` matches the stored hash."""
        stored = self._credentials.get(principal_id)
        if stored is None:
            return False
        return hmac.compare_digest(stored, self._hash(credential))

    def invalidate_session(self, principal_id: str) -> None:
        """Invalidate the session for ``principal_id``."""
        self._valid_sessions.discard(principal_id)

    def can_approve(self, principal_id: str) -> bool:
        """Return whether ``principal_id`` may approve a gate."""
        return principal_id in self._valid_sessions

    def dump(self) -> str:
        """Return a string representation of stored credentials for auditing.

        Plaintext credentials are never included.
        """
        return json.dumps(
            {pid: "***" for pid in self._credentials},
            sort_keys=True,
        )


class SecretRedactor:
    """Redact registered secrets from arbitrary payloads."""

    def __init__(self) -> None:
        self._secrets: set[str] = set()

    def register_secret(self, secret: str) -> None:
        """Register a secret string to be redacted."""
        self._secrets.add(secret)

    def redact(self, payload: Any) -> Any:
        """Return a copy of ``payload`` with all registered secrets replaced."""
        if isinstance(payload, dict):
            return {key: self.redact(value) for key, value in payload.items()}
        if isinstance(payload, list):
            return [self.redact(item) for item in payload]
        if isinstance(payload, str):
            result = payload
            for secret in self._secrets:
                result = result.replace(secret, "***")
            return result
        return payload


class RequestValidator:
    """Validate control-plane requests and detect replays.

    Args:
        expected_principal: Principal that may issue the request.
        expected_run: Run the request targets.
        expected_revision: Revision the request is bound to.
    """

    def __init__(
        self,
        expected_principal: str,
        expected_run: str,
        expected_revision: str,
    ) -> None:
        self._expected_principal = expected_principal
        self._expected_run = expected_run
        self._expected_revision = expected_revision
        self._seen_nonces: set[str] = set()
        self.execution_count = 0

    def validate(
        self,
        principal: str,
        run: str,
        revision: str,
        nonce: str | None = None,
    ) -> None:
        """Validate a control-plane request.

        Args:
            principal: Requesting principal.
            run: Target run id.
            revision: Target revision.
            nonce: Unique request nonce (required for execution).

        Raises:
            PermissionError: If principal/run/revision does not match.
            ReplayDetectedError: If the nonce was already used.
        """
        if principal != self._expected_principal:
            raise PermissionError(
                f"principal mismatch: expected {self._expected_principal!r}, got {principal!r}"
            )
        if run != self._expected_run:
            raise PermissionError(
                f"run mismatch: expected {self._expected_run!r}, got {run!r}"
            )
        if revision != self._expected_revision:
            raise PermissionError(
                f"revision mismatch: expected {self._expected_revision!r}, got {revision!r}"
            )
        if nonce is None:
            return
        if nonce in self._seen_nonces:
            raise ReplayDetectedError(f"request nonce {nonce!r} already used")
        self._seen_nonces.add(nonce)
        self.execution_count += 1
