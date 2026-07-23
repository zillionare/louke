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
