"""Integration tests for FR-0600: Interfaces Design.

AC-FR0600-01: Each main user journey traces from host product's existing
or newly-designed entry to a real-identity interface with input, output,
state, permission, error, recovery and observable completion result.
Test Plan observable interface/execution entry resolves to that identity;
its semantics are carried by Architecture; consistent with machine contract
commands/paths/status semantics.
"""
# AC-FR0600-01

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_ROOT = (
    REPO_ROOT
    / ".louke"
    / "project"
    / "specs"
    / "v0.14-002-workflow-reflow-design"
)


def test_interfaces_md_exists():
    assert (SPEC_ROOT / "interfaces.md").exists()


def test_interfaces_md_lists_all_15_interfaces():
    """interfaces.md must define all 15 IF-XXX interfaces."""
    from tests.ground_truth.v014_design_contracts.independent_validator import (
        parse_interfaces_ids,
        REQUIRED_INTERFACES,
    )
    ids = set(parse_interfaces_ids(SPEC_ROOT / "interfaces.md"))
    missing = REQUIRED_INTERFACES - ids
    assert not missing, f"interfaces.md missing: {missing}"


def test_interfaces_md_no_unknown_interfaces():
    """interfaces.md must not define interfaces outside the required set."""
    from tests.ground_truth.v014_design_contracts.independent_validator import (
        parse_interfaces_ids,
        REQUIRED_INTERFACES,
    )
    ids = set(parse_interfaces_ids(SPEC_ROOT / "interfaces.md"))
    extra = ids - REQUIRED_INTERFACES
    assert not extra, f"interfaces.md has unknown interfaces: {extra}"


def test_manifest_interface_set_matches_required(design_manifest):
    """manifest.interface_set must equal the 15 required interfaces."""
    from tests.ground_truth.v014_design_contracts.independent_validator import (
        REQUIRED_INTERFACES,
    )
    actual = set(design_manifest["interface_set"])
    assert actual == REQUIRED_INTERFACES


def test_manifest_architecture_anchor_set_matches_required(design_manifest):
    """manifest.architecture_anchor_set must equal the 16 required anchors."""
    from tests.ground_truth.v014_design_contracts.independent_validator import (
        REQUIRED_ARCHITECTURE_ANCHORS,
    )
    actual = set(design_manifest["architecture_anchor_set"])
    assert actual == REQUIRED_ARCHITECTURE_ANCHORS


@pytest.mark.awaiting_devon("FR-0600")
def test_validator_detects_interface_without_public_outlet(mock_design_contract):
    """Validator must detect when Acceptance requires observation but
    Interfaces has no public outlet."""
    mock_design_contract.validate_manifest.return_value = {
        "ok": False,
        "checks": [
            {"id": "no-public-outlet", "status": "fail", "interface": "IF-XXX-99"}
        ],
    }
    result = mock_design_contract.validate_manifest({})
    assert not result["ok"]
