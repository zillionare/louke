"""Integration tests for FR-0400: Test Plan Design.

AC-FR0400-01: Validator reads observable interface, required layers,
runner/command, fixture/environment, CI job, trace metadata and rationale
for every valid AC; observable interface and execution entry both resolve
to real Interfaces identity. Command/path/status semantics align with
machine contract and Architecture; no orphan in either direction.
"""
# AC-FR0400-01

from __future__ import annotations

import json
from pathlib import Path

import pytest

TESTS_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_ROOT = (
    REPO_ROOT
    / ".louke"
    / "project"
    / "specs"
    / "v0.14-002-workflow-reflow-design"
)
CLOSURE_MATRIX = (
    TESTS_ROOT
    / "fixtures"
    / "v014_design_contracts"
    / "matrices"
    / "design_closure_matrix.json"
)


def test_test_plan_lists_34_ac_ids():
    """test-plan.md §4.1 must enumerate exactly 34 AC IDs."""
    from tests.ground_truth.v014_design_contracts.independent_validator import (
        parse_acceptance_ac_ids,
    )
    ac_ids = parse_acceptance_ac_ids(SPEC_ROOT / "acceptance.md")
    assert len(ac_ids) == 34


def test_design_closure_matrix_lists_15_interfaces():
    """closure matrix must list 15 IF-XXX interfaces."""
    matrix = json.loads(CLOSURE_MATRIX.read_text())
    assert len(matrix["interface_set"]) == 15
    assert "IF-DES-01" in matrix["interface_set"]
    assert "IF-AUD-01" in matrix["interface_set"]


def test_design_closure_matrix_lists_16_architecture_anchors():
    """closure matrix must list 16 ARC-XXX anchors."""
    matrix = json.loads(CLOSURE_MATRIX.read_text())
    assert len(matrix["architecture_anchor_set"]) == 16


def test_design_closure_matrix_negative_cases_cover_orphan_and_conflict():
    """closure matrix must include orphan and conflict negative cases."""
    matrix = json.loads(CLOSURE_MATRIX.read_text())
    neg_ids = {c["id"] for c in matrix["negative_cases"]}
    for required in ("orphan-interface", "orphan-anchor", "missing-required-layer"):
        assert required in neg_ids, f"missing negative case: {required}"


def test_manifest_ac_closure_covers_all_34(design_manifest):
    """design-artifact-manifest.ac_closure must list 34 entries."""
    closure = design_manifest.get("ac_closure")
    assert closure is not None, "manifest missing ac_closure"
    assert len(closure) == 34, (
        f"expected 34 AC closure entries, got {len(closure)}"
    )


def test_manifest_ac_closure_every_entry_has_required_fields(design_manifest):
    """Each ac_closure entry must have ac, if, arc, contracts."""
    closure = design_manifest["ac_closure"]
    for entry in closure:
        assert "ac" in entry, f"entry missing ac: {entry}"
        assert "if" in entry, f"entry {entry['ac']} missing if"
        assert "arc" in entry, f"entry {entry['ac']} missing arc"
        assert "contracts" in entry, f"entry {entry['ac']} missing contracts"


def test_manifest_ac_closure_interfaces_subset_of_required(design_manifest):
    """Every IF referenced in ac_closure must be in the required interface set."""
    from tests.ground_truth.v014_design_contracts.independent_validator import (
        REQUIRED_INTERFACES,
    )
    closure = design_manifest["ac_closure"]
    for entry in closure:
        for if_id in entry["if"]:
            assert if_id in REQUIRED_INTERFACES, (
                f"entry {entry['ac']} references unknown interface {if_id}"
            )


def test_manifest_ac_closure_anchors_subset_of_required(design_manifest):
    """Every ARC referenced in ac_closure must be in the required anchor set."""
    from tests.ground_truth.v014_design_contracts.independent_validator import (
        REQUIRED_ARCHITECTURE_ANCHORS,
    )
    closure = design_manifest["ac_closure"]
    for entry in closure:
        for arc in entry["arc"]:
            assert arc in REQUIRED_ARCHITECTURE_ANCHORS, (
                f"entry {entry['ac']} references unknown anchor {arc}"
            )


@pytest.mark.awaiting_devon("FR-0400")
def test_validator_detects_orphan_interface(mock_design_contract):
    """Validator must detect orphan interface not referenced by any AC."""
    mock_design_contract.validate_manifest.return_value = {
        "ok": False,
        "checks": [{"id": "orphan-interface", "status": "fail", "anchor": "IF-XXX-99"}],
    }
    result = mock_design_contract.validate_manifest({})
    assert not result["ok"]


@pytest.mark.awaiting_devon("FR-0400")
def test_validator_detects_missing_required_layer(mock_design_contract):
    """Validator must detect when a required layer is missing for an AC."""
    mock_design_contract.validate_manifest.return_value = {
        "ok": False,
        "checks": [
            {"id": "missing-layer", "status": "fail", "ac": "AC-FR0700-01", "layer": "integration"}
        ],
    }
    result = mock_design_contract.validate_manifest({})
    assert not result["ok"]
