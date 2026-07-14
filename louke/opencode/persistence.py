"""Persistence of managed OpenCode instance states (FR-1401 AC-05, B4).

After a Louke restart, the recovery scan must re-associate resources that are
still reachable and mark the rest as ``lost`` or ``needs_attention``. A dead
pid must never be reported as ``running`` even if a (lying) adapter claims the
instance is still there.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

from .adapter import OpenCodeAdapter


_STATUS_RUNNING = "running"
_STATUS_LOST = "lost"
_STATUS_NEEDS_ATTENTION = "needs_attention"


@dataclass
class ManagedInstanceState:
    """Persisted snapshot of a managed OpenCode instance.

    Attributes:
        instance_id: The OpenCode session id.
        workspace_path: Absolute path of the workspace owning this instance.
        pid: OS pid of the ``opencode serve`` subprocess, or None when the
            server was started externally and its pid is unknown.
        base_url: Base URL of the opencode server (e.g. http://127.0.0.1:41234).
        last_seen: Epoch seconds of the last successful contact.
        status: One of ``running``, ``lost``, ``needs_attention``, ``stopped``.
    """

    instance_id: str
    workspace_path: str
    pid: Optional[int]
    base_url: Optional[str]
    last_seen: float
    status: str


class OpenCodeInstanceStore:
    """JSON-file persistence of managed OpenCode instance states.

    The file lives at ``<workspace>/.louke/opencode/instances.json`` and is a
    single small dict keyed by instance_id. Concurrency is best-effort: the
    store writes atomically (tmp + rename) but does not lock; it is intended
    for single-process louke servers.

    Args:
        workspace_root: The workspace root path. The store is created under
            ``<workspace_root>/.louke/opencode/``.
    """

    def __init__(self, workspace_root: Path) -> None:
        self._dir = workspace_root / ".louke" / "opencode"
        self._path = self._dir / "instances.json"

    def save(self, state: ManagedInstanceState) -> None:
        """Persist or update a single instance state.

        Overwrites any existing row with the same ``instance_id``.

        Args:
            state: The state to persist.
        """
        data = self._load_raw()
        data[state.instance_id] = asdict(state)
        self._write_raw(data)

    def load_all(self) -> List[ManagedInstanceState]:
        """Load all persisted instance states.

        Returns:
            A list of :class:`ManagedInstanceState`. Empty when no file
            exists or the file is empty.
        """
        data = self._load_raw()
        return [ManagedInstanceState(**row) for row in data.values()]

    def mark_lost(self, instance_id: str) -> None:
        """Mark an instance as lost.

        No-op when the instance is not persisted (does not create a row).

        Args:
            instance_id: The instance to mark.
        """
        data = self._load_raw()
        row = data.get(instance_id)
        if row is None:
            return
        row["status"] = _STATUS_LOST
        self._write_raw(data)

    def recovery_scan(
        self, adapter: Optional[OpenCodeAdapter] = None
    ) -> List[ManagedInstanceState]:
        """Re-associate live resources; mark dead ones.

        For each persisted state:

        * If the pid is dead (``os.kill(pid, 0)`` raises): mark ``lost``.
          The pid check is authoritative: even if the adapter reports the
          instance, a dead pid means the server we started is gone.
        * If the pid is alive and an adapter is given: ask the adapter to
          ``list()``. If the instance is present, mark ``running``; otherwise
          mark ``needs_attention``. If ``list()`` raises, mark
          ``needs_attention``.
        * If the pid is alive but no adapter is given: leave the status
          unchanged (assume still running).

        ``last_seen`` is bumped to ``now`` for every row touched.

        Args:
            adapter: Optional adapter used to confirm reachability of live
                instances. When None, live instances keep their persisted
                status.

        Returns:
            The updated list of states (also persisted).
        """
        data = self._load_raw()
        now = time.time()
        live_ids = self._live_instance_ids(adapter) if adapter else None
        updated: List[ManagedInstanceState] = []
        for row in data.values():
            row["last_seen"] = now
            row["status"] = _recovery_status(row, adapter, live_ids)
            updated.append(ManagedInstanceState(**row))
        self._write_raw(data)
        return updated

    def _load_raw(self) -> dict:
        """Load the raw dict from disk, or return {} when missing/corrupt."""
        if not self._path.is_file():
            return {}
        try:
            with self._path.open("r", encoding="utf-8") as fh:
                content = fh.read()
        except OSError:
            return {}
        if not content.strip():
            return {}
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return {}
        if not isinstance(data, dict):
            return {}
        return data

    def _write_raw(self, data: dict) -> None:
        """Atomically write the dict to disk (tmp + rename)."""
        self._dir.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
        os.replace(tmp, self._path)

    @staticmethod
    def _live_instance_ids(adapter: OpenCodeAdapter) -> set[str]:
        """Return the set of instance ids the adapter currently reports.

        Returns an empty set when the adapter raises.
        """
        try:
            return {inst.id for inst in adapter.list()}
        except Exception:
            return set()


def _recovery_status(
    row: dict,
    adapter: Optional[OpenCodeAdapter],
    live_ids: Optional[set[str]],
) -> str:
    """Decide the recovery status for a single persisted row.

    The pid check is authoritative: a dead pid always wins over a (possibly
    lying) adapter and yields ``lost``. A live pid with an adapter is
    confirmed via the adapter's reported ids. A live pid without an adapter
    keeps its previously persisted status.

    Args:
        row: The persisted dict row.
        adapter: The adapter passed to recovery_scan, or None.
        live_ids: Ids reported by the adapter (already fetched), or None
            when no adapter was given.

    Returns:
        One of ``running``, ``lost``, ``needs_attention``, or the row's
        existing status.
    """
    if not _pid_alive(row.get("pid")):
        return _STATUS_LOST
    if adapter is None:
        return row.get("status", _STATUS_RUNNING)
    if row["instance_id"] in (live_ids or set()):
        return _STATUS_RUNNING
    return _STATUS_NEEDS_ATTENTION


def _pid_alive(pid: Optional[int]) -> bool:
    """Return True if ``pid`` is a live process.

    Args:
        pid: The pid to probe, or None.

    Returns:
        True if the process exists. ``None`` is treated as "unknown pid"
        (server started externally) and returns True so the adapter is the
        authority; ``recovery_scan`` will then downgrade to
        ``needs_attention`` if the adapter cannot list it.
    """
    if pid is None:
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we cannot signal it; treat as alive.
        return True
    except OSError:
        return False
    return True
