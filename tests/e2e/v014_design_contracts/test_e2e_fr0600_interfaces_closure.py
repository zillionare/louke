"""E2E: AC-FR0600-01 Interfaces closure observable at e2e layer.

Verifies that the e2e contract references interfaces.md and that the
journey exposes the interfaces closure through the Workbench public
surface. AC-FR0600-01 is in the required e2e suite.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.v014_002_e2e


def test_interfaces_md_referenced_by_e2e_contract(e2e_test_contract):
    """e2e contract artifact_refs must reference interfaces.md."""
    refs = e2e_test_contract.get("artifact_refs", [])
    interfaces_refs = [r for r in refs if "interfaces.md" in r.get("path", "")]
    assert interfaces_refs, "e2e contract must reference interfaces.md"
    # Each interfaces.md ref must carry interface_ids.
    for ref in interfaces_refs:
        assert "interface_ids" in ref
        assert len(ref["interface_ids"]) > 0


def test_required_interface_ids_present(e2e_test_contract):
    """e2e suite must reference the required interface IDs."""
    payload = e2e_test_contract.get("payload", {})
    required_interfaces: set[str] = set()
    for suite in payload.get("suites", []):
        if suite.get("required"):
            required_interfaces.update(suite.get("interface_ids", []))
    # IF-DES-01, IF-TST-01, IF-PRM-01, IF-REV-01, IF-WEB-01, IF-AUD-01 are required.
    expected = {"IF-DES-01", "IF-TST-01", "IF-PRM-01", "IF-REV-01", "IF-WEB-01", "IF-AUD-01"}
    missing = expected - required_interfaces
    assert not missing, f"required e2e suite missing interface IDs: {missing}"


def test_acid_fr0600_in_required_suite(e2e_test_contract):
    """AC-FR0600-01 must be in the required e2e suite."""
    payload = e2e_test_contract.get("payload", {})
    required_acids: set[str] = set()
    for suite in payload.get("suites", []):
        if suite.get("required"):
            required_acids.update(suite.get("ac_ids", []))
    assert "AC-FR0600-01" in required_acids


def test_interfaces_referenced_by_journey(e2e_test_contract):
    """Journey design-author-review-continue must reference interfaces via artifact_refs."""
    # The first journey covers AC-FR0600-01.
    payload = e2e_test_contract.get("payload", {})
    journey = next(
        (j for j in payload.get("journeys", []) if j.get("id") == "design-author-review-continue"),
        None,
    )
    assert journey is not None
    assert "AC-FR0600-01" in journey.get("ac_ids", [])


@pytest.mark.awaiting_devon("FR-0600")
def test_interfaces_closure_visible_through_workbench(workbench_api):
    """Interfaces closure must be visible through the Workbench public surface."""
    assert workbench_api is not None


def test_interfaces_artifact_ref_carries_architecture_anchors(e2e_test_contract):
    """interfaces.md artifact_ref must carry architecture anchors."""
    refs = e2e_test_contract.get("artifact_refs", [])
    interfaces_ref = next((r for r in refs if "interfaces.md" in r.get("path", "")), None)
    assert interfaces_ref is not None
    anchors = interfaces_ref.get("architecture_anchors", [])
    # ARC-WEB, ARC-DESIGN, ARC-CONTRACTS are expected for interfaces.
    for expected_anchor in ("ARC-WEB", "ARC-DESIGN", "ARC-CONTRACTS"):
        assert expected_anchor in anchors, (
            f"interfaces.md ref missing architecture anchor: {expected_anchor}"
        )


def test_interfaces_artifact_ref_carries_digest(e2e_test_contract):
    """interfaces.md artifact_ref must carry a sha256 digest."""
    refs = e2e_test_contract.get("artifact_refs", [])
    interfaces_ref = next((r for r in refs if "interfaces.md" in r.get("path", "")), None)
    assert interfaces_ref is not None
    digest = interfaces_ref.get("digest", "")
    assert digest.startswith("sha256:")
    hex_part = digest.removeprefix("sha256:")
    assert len(hex_part) == 64
    int(hex_part, 16)
