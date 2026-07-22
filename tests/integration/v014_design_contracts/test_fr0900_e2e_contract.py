"""Integration tests for FR-0900: E2E Test Contract (integration layer).

AC-FR0900-01: e2e contract is machine-readable and validates public entry/
journey, paths, runner, environment service lifecycle, isolation, timeout,
artifact, trace and recovery fields. Mapping e2e allocation to tests that
only call internal modules, or missing required journey's run outlet,
fails Prism/program gate.

Note: FR-0900 also has an E2E component (tests/e2e/v014_design_contracts/
test_fr0900_e2e_contract_e2e.py).
"""
# AC-FR0900-01

from __future__ import annotations


def test_e2e_contract_has_canonical_envelope(
    e2e_test_contract, canonical_envelope_keys
):
    """e2e contract must carry every required canonical-envelope key."""
    missing = canonical_envelope_keys - set(e2e_test_contract)
    assert not missing, f"e2e contract missing envelope keys: {missing}"


def test_e2e_contract_kind_matches(e2e_test_contract):
    assert e2e_test_contract["kind"] == "e2e-test"


def test_e2e_contract_schema_ref_resolves(e2e_test_contract):
    """schema_ref must point to louke.machine-contract.e2e-test@1.0.0."""
    ref = e2e_test_contract["schema_ref"]
    assert ref["identity"] == "louke.machine-contract.e2e-test"
    assert ref["version"] == "1.0.0"


def test_e2e_contract_payload_has_commands(e2e_test_contract):
    """payload.commands must list the public e2e entry."""
    commands = e2e_test_contract["payload"]["commands"]
    assert len(commands) >= 1
    cmd = commands[0]
    assert cmd["id"] == "e2e-public"
    assert "tests/e2e/run-project-venv" in cmd["command"]


def test_e2e_contract_payload_has_suites(e2e_test_contract):
    """payload.suites must list required e2e suite with 9 AC IDs."""
    suites = e2e_test_contract["payload"]["suites"]
    assert len(suites) >= 1
    required = suites[0]
    assert required["required"] is True
    assert "v014-design-contracts-e2e" in required["id"]
    assert len(required["ac_ids"]) == 9


def test_e2e_contract_payload_has_journeys(e2e_test_contract):
    """payload.journeys must define public journeys."""
    journeys = e2e_test_contract["payload"]["journeys"]
    assert len(journeys) >= 2
    journey_ids = {j["id"] for j in journeys}
    assert "design-author-review-continue" in journey_ids
    assert "candidate-bootstrap-restart" in journey_ids


def test_e2e_contract_payload_has_public_surfaces(e2e_test_contract):
    """payload.public_surfaces must list Workbench API endpoints."""
    surfaces = e2e_test_contract["payload"]["public_surfaces"]
    assert len(surfaces) >= 1
    assert any("Workbench" in s for s in surfaces)


def test_e2e_contract_failure_policy_fail_closed(e2e_test_contract):
    """failure_policy.fail_closed must be True."""
    policy = e2e_test_contract["payload"]["failure_policy"]
    assert policy["fail_closed"] is True
    assert policy["current_state"] == "candidate-not-installed"


def test_e2e_contract_isolation_rules(e2e_test_contract):
    """payload.isolation must declare port/browser/pointer isolation."""
    iso = e2e_test_contract["payload"]["isolation"]
    assert "ports" in iso
    assert "browser_context" in iso
    assert "active_pointer" in iso
    assert iso["parallel_shared_state"] is False


def test_e2e_contract_paths_include_v014_design_contracts(e2e_test_contract):
    """payload.paths must include tests/e2e/v014_design_contracts."""
    paths = e2e_test_contract["payload"]["paths"]
    assert "tests/e2e/v014_design_contracts" in paths


def test_e2e_contract_services_include_workbench(e2e_test_contract):
    """payload.services must include the Workbench service."""
    services = e2e_test_contract["payload"]["services"]
    assert len(services) >= 1
    assert services[0]["id"] == "workbench"
    assert "lk web" in services[0]["start"]
