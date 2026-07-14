"""Unit tests for opencode adapter dispatch + server process (FR-1401, B4).

Dispatch routes between the in-memory mock (for tests) and the real HTTP
adapter (for production). The kind is selected by explicit argument or the
``LOUKE_OPENCODE_BACKEND`` env var (default ``mock``).

Server-process tests use a fake script that prints a URL line, so they do
NOT shell out to a real opencode binary.
"""

from __future__ import annotations

import stat
import sys
from pathlib import Path

import pytest

from louke.opencode.dispatch import get_default_adapter
from louke.opencode.in_memory import InMemoryOpenCodeAdapter, get_default_adapter as _get_mock
from louke.opencode.real import RealOpenCodeAdapter


# -- kind="mock" -------------------------------------------------------------


def test_dispatch_mock_returns_in_memory_singleton():
    """kind='mock' returns the shared InMemoryOpenCodeAdapter singleton."""
    adapter = get_default_adapter(kind="mock")

    assert isinstance(adapter, InMemoryOpenCodeAdapter)
    assert adapter is _get_mock()


def test_dispatch_mock_is_singleton_across_calls():
    """Repeated mock dispatch returns the same object."""
    a = get_default_adapter(kind="mock")
    b = get_default_adapter(kind="mock")
    assert a is b


# -- kind="real" -------------------------------------------------------------


def test_dispatch_real_returns_real_adapter(tmp_path: Path, monkeypatch):
    """kind='real' returns a RealOpenCodeAdapter bound to a base_url."""
    monkeypatch.setenv("LOUKE_OPENCODE_BASE_URL", "http://127.0.0.1:41999")
    adapter = get_default_adapter(kind="real", workspace_root=tmp_path)

    assert isinstance(adapter, RealOpenCodeAdapter)
    assert adapter.base_url == "http://127.0.0.1:41999"


def test_dispatch_real_without_workspace_uses_env_base_url(monkeypatch):
    """kind='real' without workspace_root reads LOUKE_OPENCODE_BASE_URL."""
    monkeypatch.setenv("LOUKE_OPENCODE_BASE_URL", "http://127.0.0.1:42000")
    adapter = get_default_adapter(kind="real")

    assert isinstance(adapter, RealOpenCodeAdapter)
    assert adapter.base_url == "http://127.0.0.1:42000"


def test_dispatch_real_without_base_url_raises(monkeypatch, tmp_path: Path):
    """kind='real' with no env base_url and no workspace -> ValueError."""
    monkeypatch.delenv("LOUKE_OPENCODE_BASE_URL", raising=False)
    with pytest.raises(ValueError):
        get_default_adapter(kind="real", workspace_root=tmp_path)


# -- kind=None -> env var ----------------------------------------------------


def test_dispatch_none_reads_env_default_mock(monkeypatch):
    """kind=None falls back to LOUKE_OPENCODE_BACKEND (default mock)."""
    monkeypatch.delenv("LOUKE_OPENCODE_BACKEND", raising=False)
    adapter = get_default_adapter()

    assert isinstance(adapter, InMemoryOpenCodeAdapter)


def test_dispatch_none_reads_env_real(monkeypatch, tmp_path: Path):
    """kind=None with LOUKE_OPENCODE_BACKEND=real returns RealOpenCodeAdapter."""
    monkeypatch.setenv("LOUKE_OPENCODE_BACKEND", "real")
    monkeypatch.setenv("LOUKE_OPENCODE_BASE_URL", "http://127.0.0.1:42001")
    adapter = get_default_adapter(workspace_root=tmp_path)

    assert isinstance(adapter, RealOpenCodeAdapter)


def test_dispatch_none_env_is_case_insensitive(monkeypatch):
    """LOUKE_OPENCODE_BACKEND=REAL (uppercase) is treated as 'real'."""
    monkeypatch.setenv("LOUKE_OPENCODE_BACKEND", "REAL")
    monkeypatch.setenv("LOUKE_OPENCODE_BASE_URL", "http://127.0.0.1:42002")
    adapter = get_default_adapter()

    assert isinstance(adapter, RealOpenCodeAdapter)


# -- invalid kind ------------------------------------------------------------


def test_dispatch_invalid_kind_raises():
    """An unknown kind raises ValueError (never silently falls back)."""
    with pytest.raises(ValueError) as exc:
        get_default_adapter(kind="bogus")
    assert "bogus" in str(exc.value).lower()


# -- OpenCodeServerProcess ---------------------------------------------------


def _make_fake_bin(tmp_path: Path, lines: list[str]) -> Path:
    """Write a fake executable that prints the given lines to stdout."""
    script = tmp_path / "fake_opencode"
    body = "\n".join([
        "#!" + sys.executable,
        "import sys, time",
        *[f"print({line!r}); sys.stdout.flush()" for line in lines],
        "time.sleep(3)",
    ])
    script.write_text(body, encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def test_process_start_parses_url_from_stdout(tmp_path: Path):
    """start() reads stdout until a 'http://127.0.0.1:NNNN' line appears."""
    from louke.opencode.process import OpenCodeServerProcess
    fake = _make_fake_bin(tmp_path, [
        "Warning: unsecured",
        "opencode server listening on http://127.0.0.1:41999",
    ])
    proc = OpenCodeServerProcess(opencode_bin=str(fake), startup_timeout=5.0)

    url = proc.start()
    try:
        assert url == "http://127.0.0.1:41999"
        assert proc.base_url == "http://127.0.0.1:41999"
        assert proc.pid is not None
    finally:
        proc.stop()


def test_process_start_accepts_localhost_url(tmp_path: Path):
    """start() accepts 'localhost' in addition to '127.0.0.1'."""
    from louke.opencode.process import OpenCodeServerProcess
    fake = _make_fake_bin(tmp_path, ["listening on http://localhost:42001"])
    proc = OpenCodeServerProcess(opencode_bin=str(fake), startup_timeout=5.0)

    url = proc.start()
    try:
        assert url == "http://localhost:42001"
    finally:
        proc.stop()


def test_process_start_raises_when_url_never_logged(tmp_path: Path):
    """start() raises RuntimeError when the deadline elapses with no URL."""
    from louke.opencode.process import OpenCodeServerProcess
    fake = _make_fake_bin(tmp_path, ["just some unrelated log line"])
    proc = OpenCodeServerProcess(opencode_bin=str(fake), startup_timeout=0.3)

    with pytest.raises(RuntimeError) as exc:
        proc.start()
    msg = str(exc.value)
    # Either "did not log a URL" (deadline) or "exited before logging URL"
    # (pipe closed); both are honest failures, never a fake URL.
    assert "URL" in msg
    assert "http://127.0.0.1" not in msg or "did not log" in msg
    # Ensure the orphaned subprocess is reaped.
    proc.stop()


def test_process_start_raises_when_binary_missing(tmp_path: Path):
    """A missing binary raises RuntimeError (not FileNotFoundError)."""
    from louke.opencode.process import OpenCodeServerProcess
    proc = OpenCodeServerProcess(opencode_bin="/nonexistent/opencode-xyz")

    with pytest.raises(RuntimeError) as exc:
        proc.start()
    assert "not found" in str(exc.value).lower()


def test_process_start_returns_same_url_on_repeat_start(tmp_path: Path):
    """Calling start() twice returns the existing base_url (no second spawn)."""
    from louke.opencode.process import OpenCodeServerProcess
    fake = _make_fake_bin(tmp_path, ["listening on http://127.0.0.1:42100"])
    proc = OpenCodeServerProcess(opencode_bin=str(fake), startup_timeout=5.0)

    first = proc.start()
    first_pid = proc.pid
    second = proc.start()
    try:
        assert first == second
        assert proc.pid == first_pid
    finally:
        proc.stop()


def test_process_stop_clears_state(tmp_path: Path):
    """stop() clears pid and base_url."""
    from louke.opencode.process import OpenCodeServerProcess
    fake = _make_fake_bin(tmp_path, ["listening on http://127.0.0.1:42101"])
    proc = OpenCodeServerProcess(opencode_bin=str(fake), startup_timeout=5.0)
    proc.start()
    assert proc.pid is not None

    proc.stop()

    assert proc.pid is None
    assert proc.base_url is None


def test_process_stop_when_not_started_is_noop():
    """stop() on an unstarted process is safe."""
    from louke.opencode.process import OpenCodeServerProcess
    proc = OpenCodeServerProcess()
    proc.stop()  # must not raise


# -- FallbackOpenCodeServerProcess ------------------------------------------


def test_fallback_process_exposes_base_url():
    """FallbackOpenCodeServerProcess exposes a pre-known base_url."""
    from louke.opencode.process import FallbackOpenCodeServerProcess
    proc = FallbackOpenCodeServerProcess("http://127.0.0.1:42200", pid=42)

    assert proc.start() == "http://127.0.0.1:42200"
    assert proc.base_url == "http://127.0.0.1:42200"
    assert proc.pid == 42

    proc.stop()
    assert proc.base_url is None
