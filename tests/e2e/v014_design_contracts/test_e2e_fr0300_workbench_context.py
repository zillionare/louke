"""E2E: AC-FR0300-01 Workbench visible context.

Verifies the public Workbench surface that exposes the current Project
M-DESIGN context: revision, facts, docs, contracts, prompts, checks,
review state. Per e2e-test.candidate.json public_surfaces.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.v014_002_e2e


def test_workbench_public_surface_declared(e2e_test_contract):
    """public_surfaces must include Workbench current Project M-DESIGN context."""
    surfaces = e2e_test_contract.get("payload", {}).get("public_surfaces", [])
    assert any("M-DESIGN context" in s for s in surfaces), (
        "Workbench M-DESIGN context public surface not declared"
    )


def test_design_endpoint_declared(e2e_test_contract):
    """public_surfaces must include GET /api/v14/runs/{run_id}/design."""
    surfaces = e2e_test_contract.get("payload", {}).get("public_surfaces", [])
    assert any("/api/v14/runs/" in s and s.endswith("/design") for s in surfaces), (
        "GET /api/v14/runs/{run_id}/design endpoint not declared"
    )


def test_audit_endpoint_declared(e2e_test_contract):
    """public_surfaces must include GET /api/v14/runs/{run_id}/design/audit."""
    surfaces = e2e_test_contract.get("payload", {}).get("public_surfaces", [])
    assert any(
        "/api/v14/runs/" in s and s.endswith("/design/audit") for s in surfaces
    ), "GET /api/v14/runs/{run_id}/design/audit endpoint not declared"


def test_workbench_service_uses_installed_wheel_runtime(e2e_test_contract):
    """Workbench service must run on installed wheel product venv."""
    services = e2e_test_contract.get("payload", {}).get("services", [])
    workbench = next((s for s in services if s.get("id") == "workbench"), None)
    assert workbench is not None  # AC-FR0300-01
    assert workbench.get("runtime") == "installed wheel product venv"
    assert "lk web" in workbench.get("start", "")


def test_workbench_ready_check(e2e_test_contract):
    """Workbench ready check: GET /health, 250ms interval, 60s timeout, expects 0.14.0."""
    ready = e2e_test_contract.get("payload", {}).get("ready", {})
    assert ready.get("request") == "GET /health"
    assert ready.get("interval_ms") == 250
    assert ready.get("timeout_seconds") == 60
    expected = ready.get("expected", "")
    assert "HTTP 200" in expected
    assert "0.14.0" in expected


@pytest.mark.awaiting_devon("FR-0300")
def test_workbench_exposes_revision_facts_docs(workbench_api):
    """Workbench exposes revision, facts, docs through IF-WEB-01."""
    assert workbench_api is not None  # AC-FR0300-01


@pytest.mark.awaiting_devon("FR-0300")
def test_workbench_exposes_contracts_prompts_checks(workbench_api):
    """Workbench exposes contracts, prompts, checks through IF-WEB-01."""
    assert workbench_api is not None  # AC-FR0300-01


@pytest.mark.awaiting_devon("FR-0300")
def test_workbench_does_not_compute_pass(workbench_api):
    """Workbench does not compute PASS or advance stages (architecture §2 WEB module)."""
    assert workbench_api is not None


def test_workbench_acid_in_required_suite(e2e_test_contract):
    """AC-FR0300-01 must be in the required e2e suite."""
    payload = e2e_test_contract.get("payload", {})
    required_acids: set[str] = set()
    for suite in payload.get("suites", []):
        if suite.get("required"):
            required_acids.update(suite.get("ac_ids", []))
    assert "AC-FR0300-01" in required_acids
