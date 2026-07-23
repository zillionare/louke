"""Compatibility route normalization without duplicate product state."""

from __future__ import annotations

from urllib.parse import urlsplit


_ALIASES = {
    "/workbench": "/",
    "/setup": "/setup",
    "/api/v14/releases/preview": "/api/releases/preview",
    "/api/v14/releases/confirm": "/api/releases/confirm",
}


def canonical_route(path: str, *, next_url: str | None = None) -> str:
    """Map a supported legacy path to its canonical same-origin path."""
    target = _ALIASES.get(path, path)
    if next_url is not None:
        parsed = urlsplit(next_url)
        if parsed.scheme or parsed.netloc or not next_url.startswith("/"):
            raise ValueError("next URL must be same-origin")
        target = f"{target}?next={next_url}"
    return target
