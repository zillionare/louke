"""Dispatch between mock and real OpenCode adapters (FR-1401, B4).

The kind is selected by explicit argument or the ``LOUKE_OPENCODE_BACKEND``
env var (values: ``mock``, ``real``; default ``mock``). For ``real``, the
base URL is read from ``LOUKE_OPENCODE_BASE_URL`` or discovered by starting a
managed subprocess.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from .adapter import OpenCodeAdapter
from .in_memory import get_default_adapter as _get_mock
from .real import RealOpenCodeAdapter


_MOCK = "mock"
_REAL = "real"


def get_default_adapter(
    kind: Optional[str] = None,
    *,
    workspace_root: Optional[Path] = None,
) -> OpenCodeAdapter:
    """Return the adapter for the given kind (``mock`` | ``real`` | env).

    Args:
        kind: Adapter kind. When None, reads ``LOUKE_OPENCODE_BACKEND``
            (default ``mock``).
        workspace_root: When given and kind is ``real`` without an explicit
            base URL, a managed subprocess is started under this workspace
            and its base URL is used. When None and kind is ``real``, the
            base URL must come from ``LOUKE_OPENCODE_BASE_URL``.

    Returns:
        An adapter implementing :class:`OpenCodeAdapter`.

    Raises:
        ValueError: When the kind is unknown, or when ``real`` is requested
            but no base URL can be determined (neither env nor workspace).
    """
    resolved = (kind or os.environ.get("LOUKE_OPENCODE_BACKEND", _MOCK)).lower()
    if resolved == _MOCK:
        return _get_mock()
    if resolved == _REAL:
        return _build_real_adapter(workspace_root)
    raise ValueError(f"unknown opencode backend: {resolved!r}")


def _build_real_adapter(workspace_root: Optional[Path]) -> RealOpenCodeAdapter:
    """Build a RealOpenCodeAdapter from env or persisted state.

    Resolution order:

    1. ``LOUKE_OPENCODE_BASE_URL`` env var (explicit, highest priority).
    2. The most recent persisted instance base_url under
       ``<workspace_root>/.louke/opencode/instances.json`` (re-attach).
    3. Otherwise raise ValueError.

    Auto-starting a managed subprocess is intentionally NOT done here:
    starting a server is a heavy side effect and belongs to an explicit
    lifecycle call, not to adapter dispatch.

    Args:
        workspace_root: Optional workspace for re-attaching to a previously
            started managed process.

    Returns:
        A configured :class:`RealOpenCodeAdapter`.

    Raises:
        ValueError: When no base URL can be determined.
    """
    base_url = os.environ.get("LOUKE_OPENCODE_BASE_URL")
    if base_url:
        return RealOpenCodeAdapter(base_url)
    if workspace_root is not None:
        base_url = _load_persisted_base_url(workspace_root)
        if base_url:
            return RealOpenCodeAdapter(base_url)
    raise ValueError(
        "LOUKE_OPENCODE_BASE_URL is not set and no managed opencode instance "
        "was found under <workspace>/.louke/opencode; set LOUKE_OPENCODE_BASE_URL "
        "or start a managed server first"
    )


def _load_persisted_base_url(workspace_root: Path) -> Optional[str]:
    """Return the base_url of the most recent live persisted instance.

    Args:
        workspace_root: The workspace root.

    Returns:
        The base_url, or None when there is no persisted instance.
    """
    # Local import to avoid a hard dependency cycle at module load.
    from .persistence import OpenCodeInstanceStore
    store = OpenCodeInstanceStore(workspace_root)
    states = store.load_all()
    if not states:
        return None
    newest = max(states, key=lambda s: s.last_seen)
    return newest.base_url
