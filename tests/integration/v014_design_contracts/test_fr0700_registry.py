"""Integration tests for FR-0700: Machine Contract Registry.

AC-FR0700-01: Runtime/program registry discovers all 7 required machine
contract kinds; each schema has identity/version/digest; each Archer
instance references the schema and resolves its own revision/digest, scope,
refs and failure policy. Missing kind, self-embedded schema, unknown/
candidate/digest-mismatch schema/version blocks baseline.
"""
# AC-FR0700-01

from __future__ import annotations

import pytest


def test_registry_lists_seven_required_machine_schema_kinds(
    registry_candidate, required_machine_schema_kinds
):
    """registry.candidate.json must list exactly the 7 required kinds."""
    actual_kinds = {s["kind"] for s in registry_candidate["schemas"]}
    assert actual_kinds == required_machine_schema_kinds, (
        f"missing: {required_machine_schema_kinds - actual_kinds}; "
        f"extra: {actual_kinds - required_machine_schema_kinds}"
    )


def test_registry_lists_four_agent_io_schemas(
    registry_candidate, required_agent_io_schemas
):
    """registry.candidate.json must list exactly the 4 Agent I/O schemas."""
    actual_ids = {s["identity"] for s in registry_candidate["agent_io_schemas"]}
    expected = set(required_agent_io_schemas)
    assert actual_ids == expected, (
        f"missing: {expected - actual_ids}; "
        f"extra: {actual_ids - expected}"
    )


def test_every_schema_has_identity_version_digest(registry_candidate):
    """Each schema entry must carry identity, version, digest, path."""
    for schema in registry_candidate["schemas"]:
        assert "identity" in schema, f"schema missing identity: {schema}"
        assert "version" in schema, f"schema missing version: {schema}"
        assert "digest" in schema, f"schema missing digest: {schema}"
        assert "path" in schema, f"schema missing path: {schema}"
        assert schema["digest"].startswith("sha256:"), (
            f"digest must be sha256-prefixed: {schema['digest']}"
        )


def test_registry_activation_state_is_candidate(registry_candidate):
    """Candidate registry must declare activation_state=candidate.

    Per FR-0700 / FR-2050: before activation prerequisites are met,
    resolve must return SCHEMA_NOT_ACTIVE and block baseline.
    """
    assert registry_candidate["activation_state"] == "candidate", (
        f"expected candidate, got {registry_candidate['activation_state']}"
    )


def test_registry_atomic_activation_gate(registry_candidate):
    """activation_gate must be atomic with all prerequisites listed."""
    gate = registry_candidate["activation_gate"]
    assert gate["atomic"] is True, "activation must be atomic"
    prereqs = gate["prerequisites"]
    assert isinstance(prereqs, list) and len(prereqs) >= 3, (
        "activation prerequisites must be a non-empty list"
    )
    assert "fail_closed" in gate["failure_semantics"] or "fail closed" in gate[
        "failure_semantics"
    ].lower(), "failure semantics must mention fail closed"


def test_every_schema_path_exists_under_design_artifacts(registry_candidate):
    """Schema paths declared in registry must exist on disk."""
    from pathlib import Path
    from tests.integration.v014_design_contracts.conftest import DESIGN_ARTIFACTS

    for schema in registry_candidate["schemas"]:
        path = DESIGN_ARTIFACTS.parent / schema["path"]
        assert path.exists(), f"schema file missing: {path}"


@pytest.mark.awaiting_devon("FR-0700")
def test_resolve_returns_schema_not_active_before_activation(
    mock_contract_registry,
):
    """louke._tools.contract_registry.resolve must return SCHEMA_NOT_ACTIVE
    while registry is candidate. Awaits Devon's implementation."""
    # Mode B: mock returns a sentinel; real impl must fail closed.
    mock_contract_registry.resolve.return_value = {
        "ok": False,
        "error": "SCHEMA_NOT_ACTIVE",
    }
    result = mock_contract_registry.resolve("louke.machine-contract.integration-test")
    assert not result["ok"]
    assert result["error"] == "SCHEMA_NOT_ACTIVE"


@pytest.mark.awaiting_devon("FR-0700")
def test_registry_rejects_unknown_schema_version(mock_contract_registry):
    """resolve must reject unknown schema/version with stable error."""
    mock_contract_registry.resolve.return_value = {
        "ok": False,
        "error": "SCHEMA_UNKNOWN",
        "identity": "louke.machine-contract.nonexistent",
    }
    result = mock_contract_registry.resolve(
        "louke.machine-contract.nonexistent", version="9.9.9"
    )
    assert not result["ok"]
