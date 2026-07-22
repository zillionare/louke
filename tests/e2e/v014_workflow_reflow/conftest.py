"""Shared pytest configuration for v0.14-001 entry-slice e2e tests.

These tests run against the installed wheel (not editable source) with a
real browser.  The Starlette app is built from the installed package and
served on a random loopback port via uvicorn.  An L2 OpenCode stand-in and
``gh`` stand-in replace the external provider boundaries; everything else
(Runtime, SQLite, Git, Driver authority) is real.
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tests.fixtures.v014_workflow_reflow.harness import (  # noqa: E402
    L2ScribeStandIn,
    build_isolated_workspace,
)


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "v014_entry_e2e: v0.14-001 public-entry-slice browser e2e test",
    )


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "tests/e2e/v014_workflow_reflow" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.chromium_e2e)
            item.add_marker(pytest.mark.v014_entry_e2e)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _chromium_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            return Path(pw.chromium.executable_path).exists()
    except Exception:
        return False


@pytest.fixture(scope="session")
def installed_wheel_python():
    """Return the product venv Python from the run-project-venv harness.

    Skips when the test is not running through the installed-wheel runner.
    """
    product_python = os.environ.get("LOUKE_E2E_SERVER_PYTHON", "")
    if not product_python:
        # AC-NFR0300-01: installed-wheel e2e requires the project-venv runner
        pytest.skip(
            "v0.14 e2e must run through the installed-wheel runner "
            "(tests/e2e/run-project-venv e2e); LOUKE_E2E_SERVER_PYTHON is unset"
        )
    return product_python


@pytest.fixture
def workspace(tmp_path):
    """Build an isolated workspace with bare Git remote and stand-in gh."""
    ws = build_isolated_workspace(tmp_path)
    orig_path = os.environ.get("PATH", "")
    gh_dir = str(ws.gh_bin.parent)
    os.environ["PATH"] = os.pathsep.join([gh_dir, orig_path] if orig_path else [gh_dir])
    os.environ["LOUKE_GH_LEDGER_PATH"] = str(ws.gh_ledger)
    os.environ["LOUKE_GH_OWNER"] = "zillionare"
    yield ws
    os.environ["PATH"] = orig_path
    os.environ.pop("LOUKE_GH_LEDGER_PATH", None)
    os.environ.pop("LOUKE_GH_OWNER", None)
    ws.cleanup()
    import shutil

    if ws.bare_remote.exists():
        shutil.rmtree(ws.bare_remote, ignore_errors=True)


@pytest.fixture
def live_server(workspace):
    """Start the installed-wheel Starlette app on a random loopback port.

    The app is built from the *installed* louke package (verified by the
    run-project-venv harness) with the L2 OpenCode stand-in injected into the
    Scribe service.  This is the provider/task boundary: the stand-in adapter
    delivers Scribe recommendations through ``submit_result``, the validated
    task-result seam, while the browser drives every public page action.

    Yields ``(base_url, stand_in, workspace)``.
    """
    try:
        import uvicorn
    except ImportError as exc:
        pytest.skip(f"uvicorn not available: {exc} (AC-FR0100-01)")

    from louke.web.app import create_app
    from louke.v014.scribe_entry import ScribeEntryService
    from louke.v014.foundation_adapter import ShellFoundationAdapter
    from louke.v014.release_entry import ReleaseEntryService
    from louke.v014.story_entry import StoryEntryService

    stand_in = L2ScribeStandIn()
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    app = create_app(
        workspace.root,
        mode="development_bootstrap",
        allowed_origin=base_url,
    )
    run_store = app.state.v12_run_store
    scribe = ScribeEntryService(run_store, stand_in, workspace_root=workspace.root)
    stand_in._scribe = scribe
    app.state.v14_scribe_entry = scribe
    foundation = ShellFoundationAdapter(
        workspace.root, spec_id="v0.14-001-workflow-reflow-spec"
    )
    story_entry = StoryEntryService(run_store, foundation, scribe_entry=scribe)
    release_entry = ReleaseEntryService(
        run_store,
        foundation,
        workspace_id="louke-0.14.0",
        story_entry=story_entry,
    )
    app.state.v14_release_entry = release_entry
    app.state.v14_story_entry = story_entry

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            with urlopen(f"{base_url}/health", timeout=1) as resp:
                if resp.status == 200:
                    break
        except (URLError, OSError):
            time.sleep(0.2)
    else:
        server.should_exit = True
        pytest.fail(f"server did not become healthy at {base_url}")

    yield base_url, stand_in, workspace, app

    server.should_exit = True
    thread.join(timeout=10)


@pytest.fixture
def browser_page(live_server):
    """Return a Playwright Chromium page bound to the live server."""
    if not _chromium_available():
        pytest.skip(
            "Chromium or Playwright is not installed; "
            "run: python -m playwright install chromium (AC-NFR0300-01)"
        )
    from playwright.sync_api import sync_playwright

    base_url = live_server[0]
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(15000)
        yield page, base_url
        browser.close()
