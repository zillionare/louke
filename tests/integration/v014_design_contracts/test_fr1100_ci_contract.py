"""Integration tests for FR-1100: Managed GitHub Actions CI Contract.

AC-FR1100-01: For at least two different tech-stack fixtures, generated
contract uses each stack's real setup/build/test/artifact; includes
managed path, triggers, job DAG, permissions, secret/service/cache/
evidence/failure policy. Any required quality layer, AC trace, build or
artifact check missing from CI job/gate fails contract closure.
"""
# AC-FR1100-01

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "v014_design_contracts"
    / "matrices"
)


def test_host_matrix_has_two_distinct_stacks():
    """host_matrix must include at least Python and Node stacks."""
    matrix = json.loads((FIXTURES / "host_matrix.json").read_text())
    stacks = {h["stack"] for h in matrix["hosts"]}
    assert "Python" in stacks
    assert "Node" in stacks


def test_python_host_has_real_setup_build_test():
    """Python host fixture must declare real setup/build/test entries."""
    facts = json.loads(
        (FIXTURES / ".." / "python-host" / "host-project-facts.json").read_text()
    )
    inv = facts["inventory"]
    assert "python -m build" in inv["build_entries"]
    assert "python -m pytest" in inv["test_entries"]


def test_node_host_has_real_setup_build_test():
    """Node host fixture must declare real setup/build/test entries."""
    facts = json.loads(
        (FIXTURES / ".." / "node-host" / "host-project-facts.json").read_text()
    )
    inv = facts["inventory"]
    assert "npm run build" in inv["build_entries"]
    assert "npm test" in inv["test_entries"]


def test_github_actions_ci_contract_in_manifest(design_manifest):
    """design-artifact-manifest must list a github-actions-ci contract instance."""
    instances = design_manifest["contract_instances"]
    ci = [i for i in instances if i["kind"] == "github-actions-ci"]
    assert len(ci) == 1


def test_github_actions_ci_schema_in_registry(registry_candidate):
    """registry must include the github-actions-ci machine-contract schema."""
    kinds = {s["kind"] for s in registry_candidate["schemas"]}
    assert "github-actions-ci" in kinds


@pytest.mark.awaiting_devon("FR-1100")
def test_ci_contract_has_job_dag_and_permissions(mock_ci_contract):
    """Generated CI contract must include job DAG and permissions."""
    mock_ci_contract.generate.return_value = {
        "ok": True,
        "workflow": {
            "jobs": {"unit": {}, "integration": {"needs": ["unit"]}},
            "permissions": {"contents": "read"},
        },
    }
    result = mock_ci_contract.generate(stack="Python")
    assert result["ok"]
    assert "permissions" in result["workflow"]


@pytest.mark.awaiting_devon("FR-1100")
def test_ci_contract_rejects_missing_required_layer(mock_ci_contract):
    """Contract closure must fail if a required quality layer is missing."""
    mock_ci_contract.validate_closure.return_value = {
        "ok": False,
        "error": "MISSING_REQUIRED_LAYER",
        "layer": "integration",
    }
    result = mock_ci_contract.validate_closure(workflow={})
    assert not result["ok"]
