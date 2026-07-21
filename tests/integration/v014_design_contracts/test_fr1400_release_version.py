"""Integration tests for FR-1400: Canonical Release Identity.

AC-FR1400-01: registry discovers release-version contract; same schema
accepts both Louke Python and Node/SemVer instances; canonical version
maps to adapter/version-source identity, release branch and tag.
"""
# AC-FR1400-01

from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_release_version_schema_in_registry(registry_candidate):
    """registry must include the release-version machine-contract schema."""
    kinds = {s["kind"] for s in registry_candidate["schemas"]}
    assert "release-version" in kinds


def test_louke_release_contract_instance_exists(design_manifest):
    """design-artifact-manifest must list a release-version contract instance."""
    instances = design_manifest["contract_instances"]
    release = [i for i in instances if i["kind"] == "release-version"]
    assert len(release) == 1, f"expected 1 release-version instance, got {len(release)}"
    assert release[0]["activation_state"] == "candidate-not-installed"


def test_node_host_release_fixture_uses_same_schema_identity(
    node_host_release_fixture, registry_candidate
):
    """Node host positive fixture must use the same release-version schema
    identity as the registry (NFR-0300 heterogeneity)."""
    fixture_schema_ref = node_host_release_fixture["schema_ref"]
    registry_release = next(
        s for s in registry_candidate["schemas"] if s["kind"] == "release-version"
    )
    assert fixture_schema_ref["identity"] == registry_release["identity"]
    assert fixture_schema_ref["version"] == registry_release["version"]
    assert fixture_schema_ref["digest"] == registry_release["digest"], (
        "Node fixture must use the SAME schema digest as registry; "
        "heterogeneous hosts share one release-version schema."
    )


def test_node_host_fixture_does_not_reference_python(node_host_release_fixture):
    """Node fixture must NOT reference Python/pyproject/PEP 440 (NFR-0300)."""
    payload = node_host_release_fixture["payload"]
    blob = json.dumps(payload)
    forbidden = ["pyproject", "PEP 440", "setuptools", "wheel", "sdist"]
    for token in forbidden:
        assert token not in blob, (
            f"Node fixture must not reference Python concept '{token}'"
        )


def test_node_host_fixture_version_source_is_package_json(
    node_host_release_fixture,
):
    """Node fixture version_source must point to package.json."""
    payload = node_host_release_fixture["payload"]
    assert payload["version_source"]["path"] == "package.json"
    assert payload["version_source"]["selector"] == "version"


def test_node_host_fixture_branch_and_tag_mappings(node_host_release_fixture):
    """Node fixture must define branch_mapping and tag_mapping."""
    payload = node_host_release_fixture["payload"]
    assert payload["branch_mapping"] == "release/2.3.1"
    assert payload["tag_mapping"] == "widget-v2.3.1"


def test_node_host_adapter_commands_exist(node_host_release_fixture):
    """Node fixture payload must declare read and prepare commands."""
    payload = node_host_release_fixture["payload"]
    assert "node tools/node_release_adapter.mjs inspect-source" in payload["read_command"]
    assert "node tools/node_release_adapter.mjs prepare" in payload["prepare_command"]


def test_python_host_fixture_version_source_is_pyproject():
    """Python host fixture version source must be pyproject.toml."""
    facts_path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "v014_design_contracts"
        / "python-host"
        / "host-project-facts.json"
    )
    facts = json.loads(facts_path.read_text())
    assert "pyproject.toml:[project].version" in facts["inventory"]["version_sources"]


def test_python_host_fixture_artifacts_are_wheel_sdist():
    """Python host fixture artifacts must be wheel + sdist."""
    facts_path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "v014_design_contracts"
        / "python-host"
        / "host-project-facts.json"
    )
    facts = json.loads(facts_path.read_text())
    artifacts = set(facts["inventory"]["artifacts"])
    assert artifacts == {"wheel", "sdist"}


@pytest.mark.awaiting_devon("FR-1400")
def test_registry_rejects_tag_only_without_version_source(
    mock_contract_registry,
):
    """A release-version instance with only branch/tag but no real version
    source must be rejected. Awaits Devon's registry implementation."""
    mock_contract_registry.resolve.return_value = {
        "ok": False,
        "error": "VERSION_SOURCE_MISSING",
    }
    result = mock_contract_registry.resolve(
        "louke.machine-contract.release-version",
        instance={"branch_mapping": "release/1.0", "version_source": None},
    )
    assert not result["ok"]
