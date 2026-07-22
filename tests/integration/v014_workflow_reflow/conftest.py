"""Shared pytest configuration for v0.14-001 entry-slice integration tests.

Builds an isolated Louke-like workspace with a bare Git remote, stand-in
``gh`` and stand-in OpenCode adapter, then wires the Starlette app so that
every cross-module interface (IF-CLI-01, IF-WEB-01/03/04/05, IF-API-03/04/08,
IF-EXT-01) is exercised through real HTTP against real SQLite/Git.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Ensure the repo root is importable so the fixtures package resolves.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from starlette.testclient import TestClient  # noqa: E402

from louke.web.app import create_app  # noqa: E402
from louke.v014.scribe_entry import ScribeEntryService  # noqa: E402

from tests.fixtures.v014_workflow_reflow.harness import (  # noqa: E402
    L2ScribeStandIn,
    build_isolated_workspace,
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


@pytest.fixture
def workspace(tmp_path):
    """Build an isolated Louke workspace with bare Git remote and stand-in gh."""
    ws = build_isolated_workspace(tmp_path)
    # Put the stand-in gh first on PATH for the Foundation adapter subprocess.
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
    # Best-effort cleanup of release branches pushed to the bare remote.
    import shutil

    if ws.bare_remote.exists():
        shutil.rmtree(ws.bare_remote, ignore_errors=True)


@pytest.fixture
def stand_in():
    """Return a fresh L2 OpenCode stand-in (not yet bound to a service)."""
    return L2ScribeStandIn()


@pytest.fixture
def app(workspace, stand_in):
    """Build the Starlette app with the L2 stand-in OpenCode adapter bound."""
    allowed_origin = "http://127.0.0.1:9999"
    application = create_app(
        workspace.root,
        mode="development_bootstrap",
        allowed_origin=allowed_origin,
    )
    # Replace the Scribe service with one whose adapter is the L2 stand-in.
    # The stand-in replaces only the external OpenCode boundary (test-plan §6.2);
    # the Runtime store, Driver authority, SQLite transactions and Git
    # allowlist commit remain real.
    run_store = application.state.v12_run_store
    scribe = ScribeEntryService(run_store, stand_in, workspace_root=workspace.root)
    stand_in._scribe = scribe
    application.state.v14_scribe_entry = scribe
    # Re-bind the release entry service so its story_entry uses the new scribe.
    from louke.v014.foundation_adapter import ShellFoundationAdapter
    from louke.v014.release_entry import ReleaseEntryService
    from louke.v014.story_entry import StoryEntryService

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
    application.state.v14_release_entry = release_entry
    application.state.v14_story_entry = story_entry
    return application


@pytest.fixture
def client(app):
    """Return an authenticated TestClient bound to the stand-in app."""
    from tests.fixtures.v014_workflow_reflow.harness import register_and_login

    test_client = TestClient(app)
    register_and_login(test_client)
    return test_client
