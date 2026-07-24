"""TestClient tests for the /api/readiness sub-app (FR-1801).

AC references covered:
- AC-FR1801-04: readiness returns stable ready/degraded/blocked status for
  each workspace dependency with non-secret diagnosis and remediation.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from louke.web.api import readiness
from louke.web.api.readiness import create_app


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """Return a TestClient backed by a fresh in-memory readiness sub-app."""
    (tmp_path / ".louke" / "store").mkdir(parents=True)
    project = tmp_path / ".louke" / "project"
    project.mkdir()
    (project / "project.toml").write_text("[project]\n", encoding="utf-8")
    return TestClient(create_app(tmp_path))


def test_readiness_returns_items(client: TestClient) -> None:
    """AC-FR1801-04: readiness returns a non-empty list of checks."""
    resp = client.get("/")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 4
    names = {item["name"] for item in items}
    assert "Git" in names
    assert "Store" in names
    assert "Catalog" in names


def test_readiness_opencode_is_blocked_when_binary_is_missing(
    client: TestClient,
) -> None:
    """OpenCode is blocked only when the serving process cannot execute it."""
    with patch.object(readiness.shutil, "which", return_value=None):
        resp = client.get("/")
    assert resp.status_code == 200
    items = resp.json()["items"]
    opencode = next(item for item in items if item["name"] == "OpenCode")
    assert opencode["status"] == "BLOCKED"
    assert opencode["diagnosis"]
    assert opencode["remediation"]


def test_readiness_models_reflects_provider_and_catalog(client: TestClient) -> None:
    """Models are ready only after OpenCode reports credentials and models."""

    def run(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        if args[-2:] == ["auth", "list"]:
            return subprocess.CompletedProcess(args, 0, "2 credentials\n", "")
        if args[-1] == "models":
            return subprocess.CompletedProcess(args, 0, "provider/model\n", "")
        return subprocess.CompletedProcess(args, 0, "", "")

    with (
        patch.object(readiness.shutil, "which", return_value="/usr/bin/opencode"),
        patch.object(readiness, "_run_command", side_effect=run),
    ):
        resp = client.get("/")
    assert resp.status_code == 200
    items = resp.json()["items"]
    models = next(item for item in items if item["name"] == "Models")
    assert models["status"] == "READY"
    assert "2 provider configuration" in models["diagnosis"]


def test_configured_provider_count_includes_environment_providers() -> None:
    """Environment provider credentials count without exposing their values."""
    assert (
        readiness._configured_provider_count("0 credentials\n1 environment variable\n")
        == 1
    )


def test_readiness_each_item_has_stable_fields(client: TestClient) -> None:
    """AC-FR1801-04: each readiness item has name/status/diagnosis/remediation."""
    resp = client.get("/")
    assert resp.status_code == 200
    items = resp.json()["items"]
    for item in items:
        assert "name" in item
        assert item["status"] in ("READY", "DEGRADED", "BLOCKED")
        assert isinstance(item["diagnosis"], str)
        assert isinstance(item["remediation"], str)


def test_readiness_namespace_capability_is_blocked_when_gh_missing(
    client: TestClient,
) -> None:
    """AC-FR0501-01: namespace_capability is blocked when gh CLI is not installed."""
    with patch.object(readiness.shutil, "which", return_value=None):
        resp = client.get("/")
    assert resp.status_code == 200
    items = resp.json()["items"]
    ns = next(item for item in items if item["name"] == "namespace_capability")
    assert ns["status"] == "BLOCKED"
    assert "gh" in ns["diagnosis"].lower() or "github" in ns["diagnosis"].lower()
    remediation_lower = ns["remediation"].lower()
    # Remediation must be platform-agnostic: no brew/apt/choco/scoop hints
    assert "brew" not in remediation_lower
    assert "apt-get" not in remediation_lower
    assert "choco" not in remediation_lower
    # Must point to the cross-platform GitHub quickstart
    assert "docs.github.com" in ns["remediation"]
    assert "github-cli" in ns["remediation"]
    # Must still tell the user what to do
    assert "install" in remediation_lower
    assert "auth" in remediation_lower


def test_readiness_namespace_capability_is_blocked_when_gh_not_authenticated(
    client: TestClient,
) -> None:
    """AC-FR0501-01: gh installed but not authenticated is a blocker."""

    def run(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        if args[-1] == "--version":
            return subprocess.CompletedProcess(args, 0, "gh version 2.0.0\n", "")
        if args[-2:] == ["auth", "status"]:
            return subprocess.CompletedProcess(args, 1, "", "not logged in")
        return subprocess.CompletedProcess(args, 0, "", "")

    with (
        patch.object(readiness.shutil, "which", return_value="/usr/bin/gh"),
        patch.object(readiness, "_run_command", side_effect=run),
    ):
        resp = client.get("/")
    assert resp.status_code == 200
    items = resp.json()["items"]
    ns = next(item for item in items if item["name"] == "namespace_capability")
    assert ns["status"] == "BLOCKED"
    assert "auth" in ns["diagnosis"].lower()
    # Cross-platform link must be present
    assert "docs.github.com" in ns["remediation"]


def test_readiness_namespace_capability_not_executable_has_link(
    client: TestClient,
) -> None:
    """Gh installed but fails to execute must still link to install docs."""

    def run(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        if args[-1] == "--version":
            return subprocess.CompletedProcess(args, 1, "", "permission denied")
        return subprocess.CompletedProcess(args, 0, "", "")

    with (
        patch.object(readiness.shutil, "which", return_value="/usr/bin/gh"),
        patch.object(readiness, "_run_command", side_effect=run),
    ):
        resp = client.get("/")
    assert resp.status_code == 200
    items = resp.json()["items"]
    ns = next(item for item in items if item["name"] == "namespace_capability")
    assert ns["status"] == "BLOCKED"
    # Cross-platform link must be present even for failure remediation
    assert "docs.github.com" in ns["remediation"]


def test_readiness_namespace_capability_not_authenticated_has_link(
    client: TestClient,
) -> None:
    """Not-authenticated remediation must include the cross-platform link."""

    def run(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        if args[-1] == "--version":
            return subprocess.CompletedProcess(args, 0, "gh version 2.0.0\n", "")
        if args[-2:] == ["auth", "status"]:
            return subprocess.CompletedProcess(args, 1, "", "not logged in")
        return subprocess.CompletedProcess(args, 0, "", "")

    with (
        patch.object(readiness.shutil, "which", return_value="/usr/bin/gh"),
        patch.object(readiness, "_run_command", side_effect=run),
    ):
        resp = client.get("/")
    assert resp.status_code == 200
    items = resp.json()["items"]
    ns = next(item for item in items if item["name"] == "namespace_capability")
    assert ns["status"] == "BLOCKED"
    assert "docs.github.com" in ns["remediation"]


def test_readiness_namespace_capability_remediation_uses_official_docs_url() -> None:
    """The cross-platform install link must point at the official GitHub docs.

    Tools and the Workbench render ``remediation`` directly to the user.
    We must never invite users to a non-official source.
    """
    from louke.web.api.readiness import _namespace_capability_check

    # gh missing
    r1 = _namespace_capability_check(None)
    assert (
        "https://docs.github.com/en/github-cli/github-cli/quickstart" in r1.remediation
    )

    # gh present but bad version
    r2 = _namespace_capability_check("/usr/bin/gh")
    assert (
        "https://docs.github.com/en/github-cli/github-cli/quickstart" in r2.remediation
    )


def test_readiness_namespace_capability_ready_when_gh_authenticated(
    client: TestClient,
) -> None:
    """AC-FR0501-01: gh installed and authenticated is ready."""

    def run(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        if args[-1] == "--version":
            return subprocess.CompletedProcess(args, 0, "gh version 2.0.0\n", "")
        if args[-2:] == ["auth", "status"]:
            return subprocess.CompletedProcess(args, 0, "logged in", "")
        return subprocess.CompletedProcess(args, 0, "", "")

    with (
        patch.object(readiness.shutil, "which", return_value="/usr/bin/gh"),
        patch.object(readiness, "_run_command", side_effect=run),
    ):
        resp = client.get("/")
    assert resp.status_code == 200
    items = resp.json()["items"]
    ns = next(item for item in items if item["name"] == "namespace_capability")
    assert ns["status"] == "READY"
