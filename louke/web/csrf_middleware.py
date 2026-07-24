"""CSRF middleware: session-bound anti-forgery tokens for Setup.

AC-NFR0101-01

Tokens are bound to the current pre-auth/authenticated session and
manifest revision. They are never persisted, never logged, and never
survive cross-session use.
"""

from __future__ import annotations

import hashlib
import secrets


def issue_for_session(*, session_id: str, revision: int = 0) -> str:
    """Issue a CSRF token bound to the given session and revision.

    Args:
        session_id: The current session identifier.
        revision: The current manifest revision.

    Returns:
        A hex token string. The token is ephemeral and must not be
        persisted or logged.
    """
    raw = f"{session_id}:{revision}:{secrets.token_hex(16)}"
    return hashlib.sha256(raw.encode()).hexdigest()


def verify_token(*, token: str, session_id: str, revision: int = 0) -> bool:
    """Verify a CSRF token against the given session and revision.

    This is a placeholder that always returns ``False`` because tokens
    are non-deterministic. Real verification requires storing the
    issued token in the session (in-memory only).

    Args:
        token: The token to verify.
        session_id: The current session identifier.
        revision: The current manifest revision.

    Returns:
        ``True`` if the token matches the session-bound token.
    """
    return False
