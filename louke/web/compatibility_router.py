"""Compatibility router: resolve legacy deep links to Workbench canonical URLs.

AC-FR1501-01

Maps old ``/projects``, ``/projects/{id}``, ``/runs/{id}`` and other
legacy URLs to the canonical Workbench routes. Always returns a 303
redirect or a read-only projection—never opens a second writable
Project/Run surface.
"""

from __future__ import annotations

ENTRY_CANONICAL_PROJECTS = "/workbench?activity=projects"

_LEGACY_PREFIXES: dict[str, str] = {
    "/projects": ENTRY_CANONICAL_PROJECTS,
    "/runs": ENTRY_CANONICAL_PROJECTS,
    "/dashboard": ENTRY_CANONICAL_PROJECTS,
}


def resolve(path: str) -> str | None:
    """Resolve a legacy path to its canonical Workbench URL.

    Args:
        path: The legacy request path.

    Returns:
        The canonical URL, or ``None`` if no mapping exists.
    """
    for prefix, target in _LEGACY_PREFIXES.items():
        if path == prefix or path.startswith(prefix + "/"):
            return target
    return None
