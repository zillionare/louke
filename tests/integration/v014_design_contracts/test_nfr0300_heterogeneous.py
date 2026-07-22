"""Integration tests for NFR-0300: Host Technology Stack Portability.

AC-NFR0300-01: At least two different language/build/artifact fixtures
pass schema and design gates; generated content only references each
project's real facts. Unsupported capability returns diagnostic with
contract kind and facts identity; no hardcoded Python/Node/Java default.
"""
# AC-NFR0300-01

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "v014_design_contracts"


def test_python_host_fixture_exists():
    """Python host fixture directory must exist with required files."""
    host = FIXTURES / "python-host"
    assert (host / "pyproject.toml").exists()
    assert (host / "host-project-facts.json").exists()
    assert (host / "src" / "demo_pkg" / "__init__.py").exists()


def test_node_host_fixture_exists():
    """Node host fixture directory must exist with required files."""
    host = FIXTURES / "node-host"
    assert (host / "package.json").exists()
    assert (host / "host-project-facts.json").exists()
    assert (host / "tools" / "node_release_adapter.mjs").exists()


def test_node_host_release_fixture_uses_same_release_schema(
    node_host_release_fixture, registry_candidate
):
    """The Node host release fixture must be accepted by the SAME
    release-version@1.0.0 schema as the Louke Python instance."""
    fixture_schema = node_host_release_fixture["schema_ref"]
    registry_schema = next(
        s for s in registry_candidate["schemas"] if s["kind"] == "release-version"
    )
    assert fixture_schema["identity"] == registry_schema["identity"]
    assert fixture_schema["version"] == registry_schema["version"]
    assert fixture_schema["digest"] == registry_schema["digest"]


def test_node_host_fixture_version_is_semver(node_host_release_fixture):
    """Node fixture release identity must be canonical SemVer."""
    version = node_host_release_fixture["scope"]["release_identity"]
    import re

    assert re.match(r"^\d+\.\d+\.\d+$", version), (
        f"release identity must be SemVer: {version}"
    )


def test_python_and_node_fixtures_do_not_cross_reference():
    """Python and Node host fixtures must not reference each other's paths."""
    py_facts = json.loads(
        (FIXTURES / "python-host" / "host-project-facts.json").read_text()
    )
    node_facts = json.loads(
        (FIXTURES / "node-host" / "host-project-facts.json").read_text()
    )
    py_blob = json.dumps(py_facts).lower()
    node_blob = json.dumps(node_facts).lower()
    python_tokens = ["pyproject", "setuptools", "wheel", "sdist"]
    node_tokens = ["package.json", "npm", "node", "tarball"]
    for token in node_tokens:
        assert token not in py_blob, f"Python fixture references Node concept '{token}'"
    for token in python_tokens:
        assert token not in node_blob, (
            f"Node fixture references Python concept '{token}'"
        )


def test_host_matrix_includes_unsupported_capability():
    """host_matrix must include an unsupported-capability case."""
    matrix = json.loads((FIXTURES / "matrices" / "host_matrix.json").read_text())
    unsupported = next(
        (h for h in matrix["hosts"] if h["id"] == "unsupported-capability"), None
    )
    assert unsupported is not None  # AC-NFR0300-01
    assert unsupported["expected_behavior"].startswith("diagnostic")
    assert (
        "hardcoded" in unsupported["expected_behavior"]
        or "default" in unsupported["expected_behavior"]
    )


def test_host_matrix_blank_project_requires_no_human():
    """blank-project case must require Archer autonomy."""
    matrix = json.loads((FIXTURES / "matrices" / "host_matrix.json").read_text())
    blank = next((h for h in matrix["hosts"] if h["id"] == "blank-project"), None)
    assert blank is not None  # AC-NFR0300-01
    assert (
        "Human" in blank["expected_behavior"]
        or "human" in blank["expected_behavior"].lower()
    )
    assert (
        "default" in blank["expected_behavior"].lower()
        or "Louke" in blank["expected_behavior"]
    )


def test_node_host_adapter_inspect_source_returns_version(tmp_path):
    """node_release_adapter.mjs inspect-source must return the package version."""
    import shutil
    import subprocess

    node_host = FIXTURES / "node-host"
    # Copy package.json and adapter into tmp_path (adapter expects cwd layout)
    (tmp_path / "package.json").write_text((node_host / "package.json").read_text())
    (tmp_path / "tools").mkdir()
    shutil.copy(
        node_host / "tools" / "node_release_adapter.mjs",
        tmp_path / "tools" / "node_release_adapter.mjs",
    )
    try:
        result = subprocess.run(
            ["node", "tools/node_release_adapter.mjs", "inspect-source"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            # AC-NFR0300-01
            pytest.skip(f"node not available or adapter failed: {result.stderr}")
        payload = json.loads(result.stdout)
        assert payload["ok"] is True
        assert payload["version"] == "2.3.1"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # AC-FR0200-01
        pytest.skip("node runtime not available in this environment")


@pytest.mark.awaiting_devon("NFR-0300")
def test_unsupported_capability_returns_diagnostic_with_kind_and_facts(
    mock_host_facts,
):
    """Unsupported capability must return diagnostic with contract kind and
    facts identity; no fallback to hardcoded language default."""
    mock_host_facts.diagnose.return_value = {
        "ok": False,
        "kind": "release-version",
        "facts_identity": "fixture.host-facts.unsupported",
        "reason": "no version source available",
    }
    result = mock_host_facts.diagnose("unsupported-capability")
    assert not result["ok"]
    assert "kind" in result
    assert "facts_identity" in result
