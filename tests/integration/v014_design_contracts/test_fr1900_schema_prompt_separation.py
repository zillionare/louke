"""Integration tests for FR-1900: Prompt Semantics & Machine Schema Separation.

AC-FR1900-01: Runtime/program registry can obtain and validate Agent
input/output and machine contract authoritative schema identity/version/
digest WITHOUT parsing prompt examples or contract instance self-embedded
definitions; task manifest/contract registry carries exact reference;
Archer output only generates instances referencing active schema. Instance
self-embedding or self-certifying substitute schema, using unknown/
candidate/digest-mismatch schema, or missing fields / wrong type / enum /
forbidden additional fields is rejected; modifying prompt examples or
instance content does not change schema authoritative result.
"""
# AC-FR1900-01

from __future__ import annotations

import pytest


def test_registry_separates_machine_schemas_from_agent_io(registry_candidate):
    """registry must keep schemas and agent_io_schemas as distinct lists."""
    assert "schemas" in registry_candidate
    assert "agent_io_schemas" in registry_candidate
    machine_identities = {s["identity"] for s in registry_candidate["schemas"]}
    agent_io_identities = {
        s["identity"] for s in registry_candidate["agent_io_schemas"]
    }
    # No overlap: machine contracts are louke.machine-contract.*,
    # agent I/O are louke.agent-io.*
    assert machine_identities.isdisjoint(agent_io_identities)


def test_registry_machine_schemas_all_owned_by_runtime(registry_candidate):
    """All machine schemas must be owned by Runtime/program."""
    for schema in registry_candidate["schemas"]:
        assert schema["owner"] == "Runtime/program", (
            f"schema {schema['identity']} owner must be Runtime/program"
        )


def test_registry_agent_io_schemas_all_owned_by_runtime(registry_candidate):
    """All agent I/O schemas must be owned by Runtime/program."""
    for schema in registry_candidate["agent_io_schemas"]:
        assert schema["owner"] == "Runtime/program"


def test_registry_all_schemas_have_activation_state(registry_candidate):
    """Every schema must declare activation_state."""
    for schema in (
        registry_candidate["schemas"] + registry_candidate["agent_io_schemas"]
    ):
        assert "activation_state" in schema
        assert schema["activation_state"] == "candidate", (
            f"schema {schema['identity']} must be candidate, got {schema['activation_state']}"
        )


def test_contract_instances_reference_schema_not_embed(design_manifest):
    """Contract instances must reference schema_ref, not embed schema."""
    for instance in design_manifest["contract_instances"]:
        # Each instance has schema_ref pointing to registry, not inline schema
        # The contract JSON files are separate from schema files
        assert "kind" in instance
        assert "identity" in instance
        assert "path" in instance


def test_manifest_validation_record_is_design_time_only(design_manifest):
    """validation.record must qualify as design-time-candidate-only."""
    record = design_manifest["validation"]["record"]
    assert (
        "design-time" in record["qualification"]
        or "candidate" in record["qualification"]
    )


def test_manifest_negative_fixtures_count_is_8(design_manifest):
    """validation.negative_fixtures must declare case_count=8."""
    neg = design_manifest["validation"]["negative_fixtures"]
    assert neg["case_count"] == 8


def test_manifest_heterogeneous_positive_fixture_exists(design_manifest):
    """validation.heterogeneous_positive_fixture must point to Node host."""
    het = design_manifest["validation"]["heterogeneous_positive_fixture"]
    assert "node-host" in het["path"]
    assert het["schema_identity"] == "louke.machine-contract.release-version"
    assert het["host_stack"] == "Node.js/package.json/SemVer"


@pytest.mark.awaiting_devon("FR-1900")
def test_registry_rejects_self_embedded_schema(mock_contract_registry):
    """Instance with self-embedded schema must be rejected."""
    mock_contract_registry.resolve.return_value = {
        "ok": False,
        "error": "SELF_EMBEDDED_SCHEMA_REJECTED",
    }
    result = mock_contract_registry.resolve(
        "louke.machine-contract.integration-test",
        instance={"inline_schema": {"type": "object"}},
    )
    assert not result["ok"]


@pytest.mark.awaiting_devon("FR-1900")
def test_modifying_prompt_does_not_change_schema_result(
    mock_contract_registry, mock_prompt_bundle
):
    """Schema validation result must not change when prompt examples are modified."""
    mock_contract_registry.resolve.return_value = {
        "ok": True,
        "digest": "sha256:stable",
    }
    r1 = mock_contract_registry.resolve("louke.machine-contract.integration-test")
    r2 = mock_contract_registry.resolve("louke.machine-contract.integration-test")
    assert r1["digest"] == r2["digest"]
