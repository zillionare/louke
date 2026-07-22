"""Shared pytest configuration for v0.14-002 design-contracts E2E tests.

These tests run against a built wheel + live Workbench (``lk web``) per
test-plan.md §2.3. In Mode B (mock-first), we use the same mock
infrastructure as integration tests plus an API-level stand-in for the
Workbench HTTP surface.

When Devon ships the real Workbench and runner discovery, these tests
should be re-run against the live server (set ``LOUKE_SKIP_LIVE_SERVER=0``
and ensure ``uvicorn`` is installed).
"""

from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
TESTS_ROOT = REPO_ROOT / "tests"
SPEC_ROOT = (
    REPO_ROOT / ".louke" / "project" / "specs" / "v0.14-002-workflow-reflow-design"
)
DESIGN_ARTIFACTS = SPEC_ROOT / "design-artifacts"

# Same module list as integration conftest (kept in sync).
MOCK_MODULES: dict[str, dict[str, str]] = {
    "louke._tools.design_contract": {"if": "IF-DES-02", "fr": "FR-0400"},
    "louke._tools.contract_registry": {"if": "IF-REG-01", "fr": "FR-0700"},
    "louke._tools.ci_contract": {"if": "IF-CI-01", "fr": "FR-1100"},
    "louke._tools.precommit_contract": {"if": "IF-PC-01", "fr": "FR-1000"},
    "louke._tools.release_version": {"if": "IF-REL-01", "fr": "FR-1400"},
    "louke._tools.build_artifact": {"if": "IF-BLD-01", "fr": "FR-1500"},
    "louke._tools.publish_recovery": {"if": "IF-PUB-01", "fr": "FR-1600"},
    "louke._tools.prompt_bundle": {"if": "IF-PRM-01", "fr": "FR-1700"},
    "louke._tools.design_review": {"if": "IF-REV-01", "fr": "FR-2500"},
    "louke._tools.host_facts": {"if": "IF-FCT-01", "fr": "FR-0200"},
    "louke._tools.workbench": {"if": "IF-WEB-01", "fr": "FR-0300"},
    "louke._tools.audit_export": {"if": "IF-AUD-01", "fr": "NFR-0400"},
    "louke._tools.design_coordinator": {"if": "IF-DES-01", "fr": "FR-0100"},
}


def _import_or_mock(module_path: str) -> tuple[Any, bool]:
    try:
        return importlib.import_module(module_path), False
    except ImportError:
        return MagicMock(name=module_path), True


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Required fixture missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "v014_002_e2e: v0.14-002 design-contracts end-to-end test",
    )
    config.addinivalue_line(
        "markers",
        "awaiting_devon(fr): test exercises an interface whose real "
        "implementation is pending; expected to xfail until Devon ships "
        "the corresponding louke._tools.* module",
    )


def pytest_collection_modifyitems(config, items):
    """Auto-mark every test under tests/e2e/v014_design_contracts/."""
    for item in items:
        if "tests/e2e/v014_design_contracts" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.v014_002_e2e)


@pytest.fixture(scope="session")
def mock_louke_tools_e2e() -> dict[str, Any]:
    cache: dict[str, Any] = {}
    for path in MOCK_MODULES:
        module, _ = _import_or_mock(path)
        cache[path] = module
    return cache


@pytest.fixture
def workbench_api(mock_louke_tools_e2e, monkeypatch):
    """Stand-in for the M-DESIGN Workbench HTTP API (IF-WEB-01).

    Mode B: returns mock responses derived from candidate artifacts.
    When Devon ships the real ``lk web`` server, set
    ``LOUKE_V014_002_LIVE_SERVER=1`` to run against the live server.
    When the real ``louke._tools.workbench`` module exists (Devon's
    implementation), this fixture auto-skips to force the test author
    to write a real e2e test against the actual server.
    """
    if os.environ.get("LOUKE_V014_002_LIVE_SERVER") == "1":
        # Live server mode: real integration test against ``lk web``.
        # TODO: when Devon ships ``lk web``, implement live HTTP client here. (#250)
        # AC-FR0300-01
        pytest.skip(
            "Live server mode not yet configured for v014_002 e2e; "
            "implement HTTP client when Devon ships lk web"
        )
    workbench = mock_louke_tools_e2e["louke._tools.workbench"]
    if not isinstance(workbench, MagicMock):
        # AC-FR0300-01
        pytest.skip(
            "louke._tools.workbench is now implemented by Devon; "
            "replace this mock test with a real e2e test against lk web"
        )
    monkeypatch.setitem(sys.modules, "louke._tools.workbench", workbench)
    return workbench


@pytest.fixture(scope="session")
def design_manifest():
    return _load_json(DESIGN_ARTIFACTS / "design-artifact-manifest.candidate.json")


@pytest.fixture(scope="session")
def integration_test_contract():
    return _load_json(
        DESIGN_ARTIFACTS / "contracts" / "integration-test.candidate.json"
    )


@pytest.fixture(scope="session")
def e2e_test_contract():
    return _load_json(DESIGN_ARTIFACTS / "contracts" / "e2e-test.candidate.json")


@pytest.fixture(scope="session")
def host_facts_snapshot():
    return _load_json(DESIGN_ARTIFACTS / "inputs" / "host-project-facts.snapshot.json")
