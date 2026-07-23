"""Redaction helpers for Setup responses, diagnostics, and evidence."""

from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit


_ASSIGNMENT = re.compile(r"(?i)(password|token|secret|credential)(\s*[=:]\s*)[^\s,;]+")


def redact_text(value: str) -> str:
    """Remove common secret assignments and URL userinfo from text."""
    redacted = _ASSIGNMENT.sub(r"\1\2[REDACTED]", value)
    return re.sub(r"https?://[^/\s]+@", "https://[REDACTED]@", redacted)


def redact_url(value: str) -> str:
    """Return a URL with userinfo removed while preserving endpoint identity."""
    parsed = urlsplit(value)
    if not parsed.scheme or not parsed.netloc:
        return value
    host = parsed.hostname or ""
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme, host, parsed.path, parsed.query, ""))
