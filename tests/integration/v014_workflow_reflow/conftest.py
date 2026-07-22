"""Shared pytest configuration for v0.14-001 entry-slice integration tests.

Starts the installed ``lk serve`` as a subprocess against an isolated
workspace with a bare Git remote, stand-in ``gh`` and stand-in OpenCode
HTTP server.  No internal Python calls, direct SQLite writes, or service
construction are used; all progression goes through public HTTP endpoints.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys

import pytest

from tests.fixtures.v014_workflow_reflow.harness import (
    build_isolated_workspace,
    server_command,
    start_opencode_standin,
    wait_for_health,
)


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "v014_entry: v0.14-001 public-entry-slice integration test",
    )


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "tests/integration/v014_workflow_reflow" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
            item.add_marker(pytest.mark.v014_entry)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture
def live_server(tmp_path):
    """Start ``lk serve`` and the OpenCode stand-in as subprocesses.

    Yields ``(base_url, workspace, opencode_stand_in)``.  The server runs
    from the current Python interpreter (the project venv for the
    ``integration`` runner, or ``LOUKE_E2E_SERVER_PYTHON`` when set).
    """
    workspace = build_isolated_workspace(tmp_path)

    # Start the OpenCode HTTP stand-in subprocess.
    opencode = start_opencode_standin(tmp_path)

    orig_path = os.environ.get("PATH", "")
    gh_dir = str(workspace.gh_bin.parent)
    os.environ["PATH"] = os.pathsep.join([gh_dir, orig_path] if orig_path else [gh_dir])
    os.environ["LOUKE_GH_LEDGER_PATH"] = str(workspace.gh_ledger)
    os.environ["LOUKE_GH_OWNER"] = "zillionare"
    os.environ["LOUKE_OPENCODE_BASE_URL"] = opencode.base_url
    os.environ["LOUKE_OPENCODE_BACKEND"] = "real"
    os.environ["LOUKE_OPENCODE_USE_SERVER_DEFAULT"] = "1"
    # Ensure the lk serve subprocess does not route localhost through a proxy.
    os.environ["NO_PROXY"] = "127.0.0.1,localhost"
    os.environ["no_proxy"] = "127.0.0.1,localhost"

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    python = os.environ.get("LOUKE_E2E_SERVER_PYTHON", sys.executable)
    cmd = server_command(python, str(workspace.root), port=port)
    server_proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=os.environ.copy(),
    )

    try:
        wait_for_health(base_url, timeout=30)
        yield base_url, workspace, opencode
    finally:
        if server_proc.poll() is None:
            server_proc.terminate()
            try:
                server_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server_proc.kill()
                server_proc.wait(timeout=5)
        opencode.stop()
        os.environ["PATH"] = orig_path
        os.environ.pop("LOUKE_GH_LEDGER_PATH", None)
        os.environ.pop("LOUKE_GH_OWNER", None)
        os.environ.pop("LOUKE_OPENCODE_BASE_URL", None)
        os.environ.pop("LOUKE_OPENCODE_BACKEND", None)
        os.environ.pop("LOUKE_OPENCODE_USE_SERVER_DEFAULT", None)
        workspace.cleanup()
        import shutil

        if workspace.bare_remote.exists():
            shutil.rmtree(workspace.bare_remote, ignore_errors=True)
