"""TestClient tests for the /api/readiness sub-app (FR-1801).

AC references covered:
- AC-FR1801-04: readiness returns stable ready/degraded/blocked status for
  each workspace dependency with non-secret diagnosis and remediation.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from louke.web.api.readiness import create_app


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient backed by a fresh in-memory readiness sub-app."""
    return TestClient(create_app())


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


def test_readiness_opencode_is_blocked(client: TestClient) -> None:
    """AC-FR1801-04: OpenCode is marked BLOCKED (real adapter pending in B4)."""
    resp = client.get("/")
    assert resp.status_code == 200
    items = resp.json()["items"]
    opencode = next(item for item in items if item["name"] == "OpenCode")
    assert opencode["status"] == "BLOCKED"
    assert opencode["diagnosis"]
    assert opencode["remediation"]


def test_readiness_models_is_ready(client: TestClient) -> None:
    """AC-FR1801-04: models report READY with a default-model placeholder."""
    resp = client.get("/")
    assert resp.status_code == 200
    items = resp.json()["items"]
    models = next(item for item in items if item["name"] == "Models")
    assert models["status"] == "READY"
    assert "default-model" in models["diagnosis"]


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
