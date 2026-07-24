"""Shared fixtures for v0.14-004 workspace-onboarding integration tests.

Integration tests drive the real Python modules (entry_resolver,
setup_journey, repository_setup, etc.) through their public interfaces.
No public HTTP exit is mocked; external adapters (Git, provider) are
replaced with in-process stand-ins per test-plan §2.4.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_ROOT = REPO_ROOT / "tests" / "fixtures" / "v014_workspace_onboarding"


def pytest_configure(config: pytest.Config) -> None:
    """Register v0.14-004 markers."""
    config.addinivalue_line(
        "markers",
        "v014_004: v0.14-004 workspace-onboarding integration test",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Auto-mark every test under tests/integration/v014_workspace_onboarding/."""
    for item in items:
        if "tests/integration/v014_workspace_onboarding" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
            item.add_marker(pytest.mark.v014_004)


@pytest.fixture
def workspace_dir(tmp_path: Path) -> Path:
    """An isolated, empty workspace directory with a clean HOME."""
    home = tmp_path / "home"
    home.mkdir()
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


@pytest.fixture
def bare_git_remote(tmp_path: Path) -> Path:
    """A loopback bare Git repository for clone tests (no credentials)."""
    remote = tmp_path / "bare-remote.git"
    remote.mkdir()
    subprocess.run(
        ["git", "init", "--bare", str(remote)],
        check=True,
        capture_output=True,
    )
    # Seed one commit so HEAD is resolvable.
    seed = tmp_path / "seed-worktree"
    seed.mkdir()
    subprocess.run(
        ["git", "init", str(seed)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(seed), "config", "user.email", "fixture@example.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(seed), "config", "user.name", "Fixture"],
        check=True,
        capture_output=True,
    )
    (seed / "README.md").write_text("# fixture seed\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(seed), "add", "."],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(seed), "commit", "-m", "fixture seed"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(seed), "remote", "add", "origin", str(remote)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(seed), "push", "origin", "main"],
        check=True,
        capture_output=True,
    )
    return remote
