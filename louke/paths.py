"""Canonical .louke directory layout (FR-0401).

All paths are computed off `canonical_root()` which resolves to `<cwd>/.louke/`.
The four subtrees (`server/`, `reviews/`, `raw/{date}/`, `project/wiki/`) are
non-overlapping by construction.
"""

from __future__ import annotations

from datetime import date as _date, datetime, timezone
from pathlib import Path
from typing import Optional


WIKI_TYPES: frozenset[str] = frozenset(
    {"story", "spec", "test-plan", "architecture", "interfaces"}
)


def canonical_root() -> Path:
    """Return `<cwd>/.louke/` (not necessarily existing on disk)."""
    return Path.cwd() / ".louke"


def server_dir() -> Path:
    return canonical_root() / "server"


def review_dir() -> Path:
    return canonical_root() / "reviews"


def session_dir(date: Optional[_date] = None) -> Path:
    """Return `<cwd>/.louke/raw/{yy-mm-dd}/`. date=None -> today (UTC)."""
    if date is None:
        date = datetime.now(timezone.utc).date()
    return canonical_root() / "raw" / date.strftime("%Y-%m-%d")


def wiki_path(wiki_type: str) -> Path:
    """Return `<cwd>/.louke/project/wiki/{type}.md`. Type must be in WIKI_TYPES."""
    if wiki_type not in WIKI_TYPES:
        raise ValueError(
            f"wiki_type must be one of {sorted(WIKI_TYPES)}, got {wiki_type!r}"
        )
    return canonical_root() / "project" / "wiki" / f"{wiki_type}.md"
