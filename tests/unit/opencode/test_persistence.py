"""Unit tests for OpenCodeInstanceStore (FR-1401 AC-05, B4).

Recovery scan must re-associate live resources and mark lost ones as
``lost`` or ``needs_attention``; never falsely ``running``.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from louke.opencode.adapter import Instance
from louke.opencode.persistence import (
    ManagedInstanceState,
    OpenCodeInstanceStore,
)


# -- save / load roundtrip ----------------------------------------------------


def test_save_then_load_all_roundtrips(tmp_path: Path):
    """save() persists state; load_all() returns the same values."""
    store = OpenCodeInstanceStore(tmp_path)
    state = ManagedInstanceState(
        instance_id="ses_abc",
        workspace_path=str(tmp_path),
        pid=12345,
        base_url="http://127.0.0.1:41234",
        last_seen=time.time(),
        status="running",
    )

    store.save(state)

    loaded = store.load_all()
    assert len(loaded) == 1
    assert loaded[0].instance_id == "ses_abc"
    assert loaded[0].pid == 12345
    assert loaded[0].base_url == "http://127.0.0.1:41234"
    assert loaded[0].status == "running"


def test_save_overwrites_existing_instance(tmp_path: Path):
    """Saving the same instance_id updates instead of duplicating."""
    store = OpenCodeInstanceStore(tmp_path)
    state = ManagedInstanceState(
        instance_id="ses_x", workspace_path=str(tmp_path), pid=1,
        base_url="http://x", last_seen=time.time(), status="running",
    )
    store.save(state)
    updated = ManagedInstanceState(
        instance_id="ses_x", workspace_path=str(tmp_path), pid=1,
        base_url="http://x", last_seen=time.time(), status="stopped",
    )
    store.save(updated)

    loaded = store.load_all()
    assert len(loaded) == 1
    assert loaded[0].status == "stopped"


def test_load_all_returns_empty_when_no_file(tmp_path: Path):
    """No persisted file -> empty list, not an error."""
    store = OpenCodeInstanceStore(tmp_path)
    assert store.load_all() == []


def test_save_creates_louke_opencode_directory(tmp_path: Path):
    """save() creates .louke/opencode/ if it does not exist."""
    store = OpenCodeInstanceStore(tmp_path)
    state = ManagedInstanceState(
        instance_id="ses_y", workspace_path=str(tmp_path), pid=2,
        base_url="http://y", last_seen=time.time(), status="running",
    )
    store.save(state)
    assert (tmp_path / ".louke" / "opencode" / "instances.json").is_file()


# -- mark_lost ---------------------------------------------------------------


def test_mark_lost_updates_status(tmp_path: Path):
    """mark_lost flips a running instance to lost."""
    store = OpenCodeInstanceStore(tmp_path)
    state = ManagedInstanceState(
        instance_id="ses_z", workspace_path=str(tmp_path), pid=3,
        base_url="http://z", last_seen=time.time(), status="running",
    )
    store.save(state)

    store.mark_lost("ses_z")

    loaded = store.load_all()
    assert loaded[0].status == "lost"


def test_mark_lost_unknown_instance_is_noop(tmp_path: Path):
    """Marking an unknown id does not raise and does not create a row."""
    store = OpenCodeInstanceStore(tmp_path)
    store.mark_lost("does-not-exist")
    assert store.load_all() == []


# -- recovery_scan -----------------------------------------------------------


def test_recovery_scan_all_dead_pids_marked_lost(tmp_path: Path):
    """When every persisted pid is dead, recovery_scan marks all as lost."""
    store = OpenCodeInstanceStore(tmp_path)
    for i in range(3):
        store.save(ManagedInstanceState(
            instance_id=f"ses_dead_{i}", workspace_path=str(tmp_path),
            pid=999_000 + i,  # almost certainly dead
            base_url="http://127.0.0.1:1", last_seen=time.time(),
            status="running",
        ))

    results = store.recovery_scan(adapter=None)

    assert len(results) == 3
    assert all(r.status == "lost" for r in results)
    # And the persisted state is updated.
    reloaded = store.load_all()
    assert all(r.status == "lost" for r in reloaded)


def test_recovery_scan_live_pid_unreachable_adapter_marks_needs_attention(
    tmp_path: Path,
):
    """A live pid whose adapter cannot list it -> needs_attention."""
    store = OpenCodeInstanceStore(tmp_path)
    # Use our own pid (always alive).
    store.save(ManagedInstanceState(
        instance_id="ses_live", workspace_path=str(tmp_path),
        pid=os.getpid(),
        base_url="http://127.0.0.1:1", last_seen=time.time(),
        status="running",
    ))

    class _UnreachableAdapter:
        def list(self):
            raise RuntimeError("connection refused")

    results = store.recovery_scan(adapter=_UnreachableAdapter())

    assert len(results) == 1
    assert results[0].status == "needs_attention"


def test_recovery_scan_live_pid_listed_by_adapter_marks_running(tmp_path: Path):
    """A live pid whose instance is still listed by the adapter -> running."""
    store = OpenCodeInstanceStore(tmp_path)
    store.save(ManagedInstanceState(
        instance_id="ses_live", workspace_path=str(tmp_path),
        pid=os.getpid(),
        base_url="http://127.0.0.1:1", last_seen=time.time(),
        status="running",
    ))

    class _HealthyAdapter:
        def list(self):
            return [Instance(id="ses_live", status="running")]

    results = store.recovery_scan(adapter=_HealthyAdapter())

    assert len(results) == 1
    assert results[0].status == "running"


def test_recovery_scan_live_pid_missing_from_adapter_marks_needs_attention(
    tmp_path: Path,
):
    """A live pid whose instance is no longer listed -> needs_attention."""
    store = OpenCodeInstanceStore(tmp_path)
    store.save(ManagedInstanceState(
        instance_id="ses_gone", workspace_path=str(tmp_path),
        pid=os.getpid(),
        base_url="http://127.0.0.1:1", last_seen=time.time(),
        status="running",
    ))

    class _EmptyAdapter:
        def list(self):
            return []

    results = store.recovery_scan(adapter=_EmptyAdapter())

    assert len(results) == 1
    assert results[0].status == "needs_attention"


def test_recovery_scan_never_reports_running_for_dead_pid(tmp_path: Path):
    """AC-FR1401-05: a dead pid must never be reported as running."""
    store = OpenCodeInstanceStore(tmp_path)
    store.save(ManagedInstanceState(
        instance_id="ses_dead", workspace_path=str(tmp_path),
        pid=999_999,  # dead
        base_url="http://127.0.0.1:1", last_seen=time.time(),
        status="running",  # persisted as running before crash
    ))

    class _LyingAdapter:
        def list(self):
            # Adapter claims it's there, but the pid is dead -> must NOT win.
            return [Instance(id="ses_dead", status="running")]

    results = store.recovery_scan(adapter=_LyingAdapter())

    assert results[0].status == "lost"


def test_recovery_scan_updates_last_seen(tmp_path: Path):
    """recovery_scan bumps last_seen on every persisted instance."""
    store = OpenCodeInstanceStore(tmp_path)
    old_seen = time.time() - 3600
    store.save(ManagedInstanceState(
        instance_id="ses_old", workspace_path=str(tmp_path),
        pid=999_999, base_url="http://x", last_seen=old_seen,
        status="running",
    ))

    results = store.recovery_scan(adapter=None)

    assert results[0].last_seen > old_seen
