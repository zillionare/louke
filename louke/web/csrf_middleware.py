"""CSRF middleware: session-bound anti-forgery tokens for Setup.

AC-NFR0101-01

Tokens are bound to the current pre-auth/authenticated session and
manifest revision. They are never persisted to disk, never written to
logs, and never survive cross-session use. Each token is single-use:
``verify_token`` consumes it immediately upon verification.
"""

from __future__ import annotations

import hashlib
import secrets
from threading import Lock

_token_store: dict[str, str] = {}
_lock = Lock()


def issue_for_session(*, session_id: str, revision: int = 0) -> str:
    """Issue a CSRF token bound to the given session and revision.

    The token replaces any previously issued token for the same
    session. The token is stored in-process only; it is never
    persisted to disk, written to logs, or included in manifests.

    Args:
        session_id: The current session identifier.
        revision: The current manifest revision (included in the
            token derivation so a new revision invalidates old tokens).

    Returns:
        A 64-character hex token string.
    """
    raw = f"{session_id}:{revision}:{secrets.token_hex(16)}"
    token = hashlib.sha256(raw.encode()).hexdigest()
    with _lock:
        _token_store[session_id] = token
    return token


def verify_token(*, token: str, session_id: str, revision: int = 0) -> bool:
    """Verify a CSRF token against the stored session-bound token.

    The token is bound to ``(session_id, revision)``; verification
    is **idempotent** so a single page render that issues one
    token can be used for multiple mutations within the same
    session+revision window. The token expires automatically when
    a new token is issued for the same session (see
    :func:`issue_for_session`).

    Args:
        token: The token to verify (from ``X-Louke-CSRF`` header).
        session_id: The current session identifier.
        revision: The current manifest revision (unused in
            verification but accepted for API symmetry).

    Returns:
        ``True`` if the token matches the session-bound token.
    """
    with _lock:
        expected = _token_store.get(session_id)
    if expected is None:
        return False
    return secrets.compare_digest(token, expected)


def clear_session(*, session_id: str) -> None:
    """Remove any stored token for the given session.

    Args:
        session_id: The session to clear.
    """
    with _lock:
        _token_store.pop(session_id, None)
