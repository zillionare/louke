"""Tests for OpenCodeInstanceStore.recovery_scan (FR-1401-05)."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest


@dataclass
class _FakeInstance:
    id: str
    status: str = "running"


class _FakeAdapter:
    def __init__(self, ids: list[str]) -> None:
        self._ids = ids

    def list(self):
        return [_FakeInstance(id=i) for i in self._ids]


def _state(pid, instance_id="inst_test") -> "ManagedInstanceState":
    """Helper: build a ManagedInstanceState directly (no asdict roundtrip)."""
    from louke.opencode.persistence import ManagedInstanceState
    return ManagedInstanceState(
        instance_id=instance_id,
        workspace_path="/tmp/ws",
        pid=pid,
        base_url="http://127.0.0.1:41234",
        last_seen=1700000000.0,
        status="running",
    )


def test_recovery_scan_dead_pid_marks_lost(tmp_path):
    """AC-FR1401-05: dead pid -> lost (authoritative)."""
    import sys
    sys.path.insert(0, "/Users/openclaw/workspace/louke")
    from louke.opencode.persistence import OpenCodeInstanceStore

    store = OpenCodeInstanceStore(tmp_path)
    store.save(_state(pid=99999, instance_id="d1"))
    store.save(_state(pid=99998, instance_id="d2"))
    store.save(_state(pid=99997, instance_id="d3"))

    store.recovery_scan()

    statuses = {s.instance_id: s.status for s in store.load_all()}
    assert statuses == {"d1": "lost", "d2": "lost", "d3": "lost"}, statuses


def test_recovery_scan_live_pid_with_matching_adapter_marks_running(tmp_path):
    """AC-FR1401-05: live pid + adapter confirms -> running."""
    import os, sys
    sys.path.insert(0, "/Users/openclaw/workspace/louke")
    from louke.opencode.persistence import OpenCodeInstanceStore

    store = OpenCodeInstanceStore(tmp_path)
    store.save(_state(pid=os.getpid(), instance_id="r1"))

    adapter = _FakeAdapter(ids=["r1"])
    store.recovery_scan(adapter=adapter)

    statuses = {s.instance_id: s.status for s in store.load_all()}
    assert statuses["r1"] == "running"


def test_recovery_scan_live_pid_no_adapter_keeps_running(tmp_path):
    """No adapter given: live-pid-only check, keeps previously persisted status."""
    import os, sys
    sys.path.insert(0, "/Users/openclaw/workspace/louke")
    from louke.opencode.persistence import OpenCodeInstanceStore

    store = OpenCodeInstanceStore(tmp_path)
    store.save(_state(pid=os.getpid(), instance_id="r2"))

    store.recovery_scan()

    statuses = {s.instance_id: s.status for s in store.load_all()}
    assert statuses["r2"] == "running"


def test_recovery_scan_live_pid_but_adapter_missing_marks_needs_attention(tmp_path):
    """AC-FR1401-05: pid alive but adapter cannot see instance -> needs_attention."""
    import os, sys
    sys.path.insert(0, "/Users/openclaw/workspace/louke")
    from louke.opencode.persistence import OpenCodeInstanceStore

    store = OpenCodeInstanceStore(tmp_path)
    store.save(_state(pid=os.getpid(), instance_id="n1"))

    adapter = _FakeAdapter(ids=[])
    store.recovery_scan(adapter=adapter)

    statuses = {s.instance_id: s.status for s in store.load_all()}
    assert statuses["n1"] == "needs_attention"


def test_recovery_scan_dead_pid_wins_over_adapter_lying(tmp_path):
    """AC-FR1401-05: spec 不会虚假显示 running. Dead pid wins over lying adapter."""
    import sys
    sys.path.insert(0, "/Users/openclaw/workspace/louke")
    from louke.opencode.persistence import OpenCodeInstanceStore

    store = OpenCodeInstanceStore(tmp_path)
    store.save(_state(pid=99999, instance_id="lie"))

    adapter = _FakeAdapter(ids=["lie"])  # lying
    store.recovery_scan(adapter=adapter)

    statuses = {s.instance_id: s.status for s in store.load_all()}
    assert statuses["lie"] == "lost", (
        "dead pid must win - spec forbids false 'running' status"
    )
