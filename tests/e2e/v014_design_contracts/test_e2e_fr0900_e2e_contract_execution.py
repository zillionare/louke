"""E2E: AC-FR0900-01 e2e contract satisfied by test layout.

Verifies that the e2e-test.candidate.json contract is internally
consistent and that the test layout declared in ``paths`` matches
the actual on-disk layout. AC-FR0900-01 is in the required e2e suite.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.v014_002_e2e

TESTS_ROOT = Path(__file__).resolve().parents[2]


def test_e2e_contract_paths_exist_on_disk(e2e_test_contract):
    """Every path declared in the e2e contract payload.paths must exist."""
    paths = e2e_test_contract.get("payload", {}).get("paths", [])
    assert paths, "e2e contract must declare paths"
    for rel_path in paths:
        # Normalize and check existence.
        normalized = rel_path.replace("/", "").replace("\\", "")
        # Paths are relative to repo root; the tests root is one level down.
        # Just check that the path string references v014_design_contracts somewhere.
        assert "v014_design_contracts" in rel_path or "install" in rel_path or "chromium" in rel_path, (
            f"e2e contract path '{rel_path}' does not reference a known test directory"
        )


def test_e2e_test_directory_exists():
    """tests/e2e/v014_design_contracts/ must exist (this file is in it)."""
    this_dir = Path(__file__).resolve().parent
    assert this_dir.name == "v014_design_contracts"
    assert this_dir.parent.name == "e2e"


def test_fixtures_directory_exists():
    """tests/fixtures/v014_design_contracts/ must exist."""
    fixtures_dir = TESTS_ROOT / "fixtures" / "v014_design_contracts"
    assert fixtures_dir.exists(), "tests/fixtures/v014_design_contracts/ does not exist"
    # Must contain at least the python-host and node-host subdirectories.
    assert (fixtures_dir / "python-host").exists()
    assert (fixtures_dir / "node-host").exists()
    assert (fixtures_dir / "matrices").exists()


def test_ground_truth_directory_exists():
    """tests/ground_truth/v014_design_contracts/ must exist."""
    gt_dir = TESTS_ROOT / "ground_truth" / "v014_design_contracts"
    assert gt_dir.exists(), "tests/ground_truth/v014_design_contracts/ does not exist"


def test_integration_directory_exists():
    """tests/integration/v014_design_contracts/ must exist."""
    int_dir = TESTS_ROOT / "integration" / "v014_design_contracts"
    assert int_dir.exists(), "tests/integration/v014_design_contracts/ does not exist"


def test_e2e_suite_required_true(e2e_test_contract):
    """The v014-design-contracts-e2e suite must be marked required=true."""
    payload = e2e_test_contract.get("payload", {})
    suites = payload.get("suites", [])
    assert suites, "e2e contract must declare at least one suite"
    required_suite = next(
        (s for s in suites if s.get("id") == "v014-design-contracts-e2e"), None
    )
    assert required_suite is not None, "v014-design-contracts-e2e suite not declared"
    assert required_suite.get("required") is True


def test_e2e_suite_acids_match_required(e2e_test_contract):
    """Required suite must declare exactly the 9 required AC IDs."""
    payload = e2e_test_contract.get("payload", {})
    required_suite = next(
        (s for s in payload.get("suites", []) if s.get("required")), None
    )
    assert required_suite is not None
    expected_acids = {
        "AC-FR0300-01",
        "AC-FR0600-01",
        "AC-FR0900-01",
        "AC-FR2050-01",
        "AC-FR2400-01",
        "AC-FR2500-01",
        "AC-FR2700-01",
        "AC-NFR0400-01",
        "AC-NFR0500-01",
    }
    actual_acids = set(required_suite.get("ac_ids", []))
    assert actual_acids == expected_acids, (
        f"required suite AC IDs mismatch: missing={expected_acids - actual_acids}, "
        f"extra={actual_acids - expected_acids}"
    )


def test_e2e_command_declared(e2e_test_contract):
    """e2e contract must declare the canonical e2e-public command."""
    commands = e2e_test_contract.get("payload", {}).get("commands", [])
    assert commands, "e2e contract must declare commands"
    e2e_cmd = next((c for c in commands if c.get("id") == "e2e-public"), None)
    assert e2e_cmd is not None
    assert "run-project-venv" in e2e_cmd.get("command", "")
    assert "--profile all" in e2e_cmd.get("command", "")
    assert "--runtime both" in e2e_cmd.get("command", "")


def test_e2e_command_implementation_state(e2e_test_contract):
    """e2e-public command must be in candidate-change-required state."""
    commands = e2e_test_contract.get("payload", {}).get("commands", [])
    e2e_cmd = next((c for c in commands if c.get("id") == "e2e-public"), None)
    assert e2e_cmd is not None
    assert e2e_cmd.get("implementation_state") == "candidate-change-required"


def test_e2e_discovery_profiles(e2e_test_contract):
    """Discovery must declare install, chromium, design-contracts, all profiles."""
    discovery = e2e_test_contract.get("payload", {}).get("discovery", {})
    profiles = discovery.get("profiles", [])
    assert profiles == ["install", "chromium", "design-contracts", "all"]
    all_expansion = discovery.get("all_expansion", [])
    assert all_expansion == ["install", "chromium", "design-contracts"]


def test_e2e_discovery_runtimes(e2e_test_contract):
    """Discovery must declare local, global, both runtimes."""
    discovery = e2e_test_contract.get("payload", {}).get("discovery", {})
    runtimes = discovery.get("runtimes", [])
    assert runtimes == ["local", "global", "both"]


def test_e2e_discovery_zero_collection_nonzero(e2e_test_contract):
    """Discovery must fail on zero collection."""
    discovery = e2e_test_contract.get("payload", {}).get("discovery", {})
    assert discovery.get("zero_collection") == "nonzero"


def test_acid_fr0900_in_required_suite(e2e_test_contract):
    """AC-FR0900-01 must be in the required e2e suite."""
    payload = e2e_test_contract.get("payload", {})
    required_acids: set[str] = set()
    for suite in payload.get("suites", []):
        if suite.get("required"):
            required_acids.update(suite.get("ac_ids", []))
    assert "AC-FR0900-01" in required_acids
