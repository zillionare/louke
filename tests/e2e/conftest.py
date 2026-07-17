"""Shared e2e fixtures: live server, browser page (parametrized chromium/firefox).

For API-only e2e runs (the most common CI scenario), set LOUKE_SKIP_LIVE_SERVER=1
so the live_server_url fixture yields a placeholder URL without spawning a
server; per-test client fixtures use TestClient(sub_app) and need no live server.
"""

from __future__ import annotations

import os
import socket
import subprocess
import time
import urllib.request
from pathlib import Path

import pytest


def pytest_collection_modifyitems(config, items):
    """Auto-mark every test in tests/e2e/ as `e2e` so `pytest -m e2e` selects them
    without requiring each test function to add `@pytest.mark.e2e` explicitly."""
    for item in items:
        if "tests/e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)


def _free_port() -> int:
    """Bind a transient socket to discover a free TCP port."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


@pytest.fixture(scope="session")
def live_server_url():
    """Start louke server in background via `lk e2e start`; yield base URL; stop on teardown.

    Skips if LOUKE_SKIP_LIVE_SERVER=1 (used by API-only e2e runs in CI).
    Also skips if `python -m louke serve` cannot start (e.g. missing uvicorn
    runtime dep — pre-existing v0.10 issue, out of scope for v0.11).
    """
    if os.environ.get("LOUKE_SKIP_LIVE_SERVER") == "1":
        yield "http://127.0.0.1:8765"
        return
    # Pre-check: does `lk serve` have uvicorn? Probe via import (fast, no server start).
    # Issue AC-NFR0001-01 (e2e orchestration); uvicorn is a pyproject dep but may
    # not be installed in this env. We import uvicorn instead of starting the server
    # because the server is long-lived and the probe would race against teardown.
    try:
        import uvicorn  # noqa: F401
    except ImportError as exc:
        # see issue #80 (v0.6 e2e smoke); uvicorn is a pyproject dep
        pytest.skip(f"#80 uvicorn not importable: {exc}")
    port = _free_port()
    env = os.environ.copy()
    env["LOUKE_E2E_STATE"] = ".louke/server"
    subprocess.Popen(
        [
            "python3",
            "-m",
            "louke",
            "e2e",
            "start",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--opencode",
            "mock",
        ],
        env=env,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"{base}/health", timeout=1)
            break
        except Exception:
            time.sleep(0.5)
    else:
        # Clean up state file before failing
        state_file = Path(".louke/server/e2e-state.json")
        if state_file.exists():
            state_file.unlink()
        pytest.fail(f"server failed to start at {base} within 30s")
    yield base
    subprocess.run(
        [
            "python3",
            "-m",
            "louke",
            "e2e",
            "stop",
            "--port",
            str(port),
            "--cleanup-workspace",
        ],
        env=env,
    )


@pytest.fixture(params=["chromium", "firefox"])
def browser_page(request, live_server_url):
    """Playwright browser page, parametrized over chromium and firefox (NFR-0101).

    Skipped when LOUKE_SKIP_LIVE_SERVER=1 (no real server to navigate to).
    Issue AC-NFR0101-01.
    """
    if os.environ.get("LOUKE_SKIP_LIVE_SERVER") == "1":
        # AC-NFR0101-01: chromium + firefox e2e requires live server
        pytest.skip("#80 LOUKE_SKIP_LIVE_SERVER=1; browser e2e requires live server")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        executable = getattr(p, request.param).executable_path
        if not Path(executable).exists():
            pytest.skip(f"AC-NFR0101-01: Playwright {request.param} is not installed")
        browser = getattr(p, request.param).launch(headless=True)
        page = browser.new_page()
        yield page
        browser.close()
