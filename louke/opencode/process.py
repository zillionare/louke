"""Lifecycle management for a child ``opencode serve`` subprocess (FR-1401, B4).

Louke owns the server process so it can re-attach after restart and report
its pid/base_url to the persistence layer. The process is a singleton per
workspace: starting twice returns the existing base_url.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path
from typing import Optional


_DEFAULT_BIN = "opencode"
_DEFAULT_HOST = "127.0.0.1"
_PORT_ZERO_LOG_TIMEOUT = 10.0
_URL_RE = re.compile(r"https?://(127\.0\.0\.1|localhost):(\d+)")


class OpenCodeServerProcess:
    """Manage a child ``opencode serve`` subprocess (singleton per workspace).

    Owns the :class:`subprocess.Popen`; records pid + base_url so louke can
    re-attach after restart and report them to the persistence layer.

    Args:
        host: Bind address passed to ``--hostname``. Defaults to loopback.
        port: Port passed to ``--port``. ``0`` lets OpenCode pick a free
            port and log it to stdout (recommended).
        opencode_bin: Path to or name of the opencode executable.
        cwd: Working directory for the subprocess. Defaults to cwd.
        env: Extra environment variables for the subprocess.
        startup_timeout: Seconds to wait for the server to log its URL.

    Attributes:
        base_url: The base URL once started, or None.
        pid: The subprocess pid once started, or None.
    """

    def __init__(
        self,
        host: str = _DEFAULT_HOST,
        port: int = 0,
        *,
        opencode_bin: str = _DEFAULT_BIN,
        cwd: Optional[Path] = None,
        env: Optional[dict[str, str]] = None,
        startup_timeout: float = _PORT_ZERO_LOG_TIMEOUT,
    ) -> None:
        self._host = host
        self._port = port
        self._bin = opencode_bin
        self._cwd = str(cwd) if cwd else None
        self._env = env
        self._startup_timeout = startup_timeout
        self._proc: Optional[subprocess.Popen] = None
        self._base_url: Optional[str] = None
        self._pid: Optional[int] = None

    @property
    def base_url(self) -> Optional[str]:
        return self._base_url

    @property
    def pid(self) -> Optional[int]:
        return self._pid

    def start(self) -> str:
        """Start the subprocess; return base_url when ready.

        Constructs the opencode argv, launches it with stdout/stderr captured
        to a pipe, and reads lines until one matches the URL regex or the
        startup deadline expires.

        Returns:
            The base URL the server is listening on.

        Raises:
            RuntimeError: If the subprocess exits before logging a URL, or
                the startup deadline elapses without a URL.
        """
        if self._proc is not None and self._base_url is not None:
            return self._base_url
        argv = self._build_argv()
        try:
            proc = subprocess.Popen(
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=self._cwd,
                env=self._build_env(),
                text=True,
                bufsize=1,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"opencode binary not found: {self._bin!r}"
            ) from exc
        self._proc = proc
        self._pid = proc.pid
        self._base_url = self._await_url(proc)
        return self._base_url

    def stop(self) -> None:
        """Terminate the subprocess.

        Sends SIGTERM and waits up to 5s; escalates to SIGKILL if needed.
        Safe to call when not started (no-op).
        """
        proc = self._proc
        if proc is None:
            return
        proc.terminate()
        try:
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5.0)
        finally:
            self._proc = None
            self._base_url = None
            self._pid = None

    def _build_argv(self) -> list[str]:
        """Build the opencode serve command line."""
        return [
            self._bin, "serve",
            "--hostname", self._host,
            "--port", str(self._port),
        ]

    def _build_env(self) -> Optional[dict[str, str]]:
        """Merge the extra env into a copy of os.environ."""
        if self._env is None:
            return None
        merged = dict(os.environ)
        merged.update(self._env)
        return merged

    def _await_url(self, proc: subprocess.Popen) -> str:
        """Read stdout lines until a base URL appears or the deadline passes.

        Args:
            proc: The running subprocess.

        Returns:
            The discovered base URL.

        Raises:
            RuntimeError: If the process exits or the deadline elapses
                without a URL. Includes the last lines of output for
                diagnosis.
        """
        deadline = time.time() + self._startup_timeout
        last_lines: list[str] = []
        assert proc.stdout is not None
        while time.time() < deadline:
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    raise RuntimeError(
                        f"opencode serve exited (code={proc.returncode}) "
                        f"before logging URL; output: {''.join(last_lines[-5:])}"
                    )
                continue
            last_lines.append(line)
            match = _URL_RE.search(line)
            if match:
                host, port = match.group(1), match.group(2)
                return f"http://{host}:{port}"
        raise RuntimeError(
            f"opencode serve did not log a URL within {self._startup_timeout}s; "
            f"output: {''.join(last_lines[-5:])}"
        )


class FallbackOpenCodeServerProcess:
    """A no-op process wrapper for environments without a real opencode binary.

    Used by tests/CI where the real opencode cannot run: it accepts a
    pre-known base_url and exposes the same ``base_url`` / ``pid``
    interface, but ``start`` is a no-op and ``stop`` does nothing.

    Args:
        base_url: The pre-known base URL.
        pid: Optional pre-known pid (for the persistence layer).
    """

    def __init__(self, base_url: str, *, pid: Optional[int] = None) -> None:
        self._base_url = base_url
        self._pid = pid

    @property
    def base_url(self) -> Optional[str]:
        return self._base_url

    @property
    def pid(self) -> Optional[int]:
        return self._pid

    def start(self) -> str:
        return self._base_url

    def stop(self) -> None:
        self._base_url = None
        self._pid = None
