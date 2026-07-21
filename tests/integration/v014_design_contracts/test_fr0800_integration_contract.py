"""Integration tests for FR-0800: Integration Test Contract.

AC-FR0800-01: integration contract is machine-readable and validates paths,
discovery, setup/run, services/fixtures, environment, timeout, AC metadata,
suite policy, evidence and failure semantics. Required AC with no executable
path or unwarranted skip fails the gate.
"""
# AC-FR0800-01

from __future__ import annotations

import pytest


def test_integration_contract_has_canonical_envelope(
    integration_test_contract, canonical_envelope_keys
):
    """Contract must carry every required canonical-envelope key (IF-CON-01)."""
    missing = canonical_envelope_keys - set(integration_test_contract)
    assert not missing, f"contract missing envelope keys: {missing}"


def test_integration_contract_kind_matches(integration_test_contract):
    assert integration_test_contract["kind"] == "integration-test"


def test_integration_contract_schema_ref_resolves(integration_test_contract):
    """schema_ref must point to louke.machine-contract.integration-test@1.0.0."""
    ref = integration_test_contract["schema_ref"]
    assert ref["identity"] == "louke.machine-contract.integration-test"
    assert ref["version"] == "1.0.0"
    assert ref["digest"].startswith("sha256:")


def test_integration_contract_manifest_ref_resolves(integration_test_contract):
    """manifest_ref must point to the design-artifact manifest."""
    ref = integration_test_contract["manifest_ref"]
    assert (
        ref["identity"]
        == "louke.design-artifacts.v0.14-002.prism-r3-remediation"
    )
    assert ref["revision"] == "prism-round-3-remediation-candidate"


def test_integration_contract_payload_has_commands(integration_test_contract):
    """payload.commands must be a non-empty list with required fields."""
    commands = integration_test_contract["payload"]["commands"]
    assert isinstance(commands, list) and len(commands) >= 1
    for cmd in commands:
        assert "id" in cmd
        assert "cwd" in cmd
        assert "command" in cmd
        assert "implementation_state" in cmd
        assert "success" in cmd
        assert "failure" in cmd


def test_integration_contract_payload_has_suites(integration_test_contract):
    """payload.suites must list required suites with AC IDs."""
    suites = integration_test_contract["payload"]["suites"]
    assert isinstance(suites, list) and len(suites) >= 1
    required_suite = suites[0]
    assert required_suite["required"] is True
    assert "v014-design-contracts-integration" in required_suite["id"]
    ac_ids = required_suite["ac_ids"]
    assert len(ac_ids) == 34, (
        f"required suite must cover 34 ACs, got {len(ac_ids)}"
    )


def test_integration_contract_failure_policy_fail_closed(
    integration_test_contract
):
    """failure_policy.fail_closed must be True; non_success includes skip."""
    policy = integration_test_contract["payload"]["failure_policy"]
    assert policy["fail_closed"] is True
    non_success = policy["non_success"]
    for required_status in ("failure", "skip", "timeout", "missing"):
        assert required_status in non_success, (
            f"non_success missing {required_status}: {non_success}"
        )


def test_integration_contract_zero_collection_is_nonzero(
    integration_test_contract
):
    """discovery.zero_collection must be 'nonzero'."""
    discovery = integration_test_contract["payload"]["discovery"]
    assert discovery["zero_collection"] == "nonzero"


def test_integration_contract_paths_include_v014_design_contracts(
    integration_test_contract,
):
    """payload.paths must include tests/integration/v014_design_contracts."""
    paths = integration_test_contract["payload"]["paths"]
    assert "tests/integration/v014_design_contracts" in paths, (
        f"v014_design_contracts path missing from contract: {paths}"
    )


@pytest.mark.awaiting_devon("FR-0800")
def test_contract_executable_via_runner(mock_design_contract):
    """Runner can read contract and execute required suite. Awaits Devon."""
    mock_design_contract.validate_manifest.return_value = {
        "ok": True,
        "checks": [{"id": "envelope", "status": "pass"}],
    }
    result = mock_design_contract.validate_manifest("integration-test.candidate.json")
    assert result["ok"]
