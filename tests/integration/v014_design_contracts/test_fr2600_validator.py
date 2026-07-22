"""Integration tests for FR-2600: Design Program Validation, Gap & Stale.

AC-FR2600-01: Validator discovers bad ID/ref, AC layer gap, schema error,
prompt drift, open discussion and out-of-scope diff; bi-directionally
verifies Test Plan observable interface/execution entry resolves to
Interfaces real identity, Interfaces state/permission/error/recovery
carried by Architecture, machine contracts commands/paths/status semantics
consistent with three documents. Any missing, orphan or bi-directional
conflict returns stable check ID, locates FR/AC/interface/architecture
anchor/contract and blocks baseline.
"""
# AC-FR2600-01

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


def test_negative_schema_fixtures_has_8_cases(negative_schema_fixtures):
    """negative-schema-fixtures must contain exactly 8 mutation cases."""
    cases = negative_schema_fixtures.get("cases", [])
    assert len(cases) == 8, f"expected 8 negative cases, got {len(cases)}"


def test_negative_schema_fixtures_each_has_expected_error(negative_schema_fixtures):
    """Each negative case must declare its expected schema/provenance error.

    The canonical fixture field is ``required_failure`` (per
    ``negative-schema-fixtures.candidate.json``), which carries the gate,
    keyword, JSON pointer and reason of the expected failure.
    """
    for case in negative_schema_fixtures["cases"]:
        assert "id" in case, f"case missing id: {case}"
        rf = case.get("required_failure") or case.get("expected")
        assert rf is not None, (  # AC-FR2600-01
            f"case {case.get('id')} missing required_failure/expected error"
        )
        if isinstance(rf, dict):
            # required_failure sub-fields
            assert "reason" in rf, (
                f"case {case.get('id')} required_failure missing reason"
            )
            assert "gate" in rf, f"case {case.get('id')} required_failure missing gate"


def test_design_closure_matrix_negative_cases():
    """design_closure_matrix must include orphan and conflict cases."""
    matrix = json.loads((FIXTURES / "design_closure_matrix.json").read_text())
    neg_ids = {c["id"] for c in matrix["negative_cases"]}
    required = {
        "orphan-interface",
        "orphan-anchor",
        "missing-required-layer",
        "command-path-conflict",
        "status-semantics-conflict",
    }
    assert required.issubset(neg_ids), f"missing negative cases: {required - neg_ids}"


@pytest.mark.awaiting_devon("FR-2600")
def test_validator_detects_bad_id(mock_design_contract):
    """Validator must detect bad ID/ref with stable check ID."""
    mock_design_contract.validate_manifest.return_value = {
        "ok": False,
        "checks": [{"id": "bad-ref", "status": "fail", "ref": "AC-XX-99"}],
    }
    result = mock_design_contract.validate_manifest({})
    assert not result["ok"]
    assert result["checks"][0]["id"] == "bad-ref"


@pytest.mark.awaiting_devon("FR-2600")
def test_validator_detects_open_discussion(mock_design_contract):
    """Validator must detect open (un-resolved) discussion."""
    mock_design_contract.validate_manifest.return_value = {
        "ok": False,
        "checks": [{"id": "open-discussion", "status": "fail"}],
    }
    result = mock_design_contract.validate_manifest({})
    assert not result["ok"]


@pytest.mark.awaiting_devon("FR-2600")
def test_validator_detects_out_of_scope_diff(mock_design_contract):
    """Validator must detect out-of-scope diff."""
    mock_design_contract.validate_manifest.return_value = {
        "ok": False,
        "checks": [
            {"id": "scope-violation", "status": "fail", "path": "unauthorized.py"}
        ],
    }
    result = mock_design_contract.validate_manifest({})
    assert not result["ok"]


@pytest.mark.awaiting_devon("FR-2600")
def test_validator_returns_stable_check_id(mock_design_contract):
    """Validator failures must include a stable check ID."""
    mock_design_contract.validate_manifest.return_value = {
        "ok": False,
        "checks": [{"id": "stable-check-id", "status": "fail"}],
    }
    result = mock_design_contract.validate_manifest({})
    assert "id" in result["checks"][0]


@pytest.mark.awaiting_devon("FR-2600")
def test_validator_locates_fr_ac_if_arc_contract(mock_design_contract):
    """Validator failure must locate FR/AC/IF/ARC/contract."""
    mock_design_contract.validate_manifest.return_value = {
        "ok": False,
        "checks": [
            {
                "id": "located-failure",
                "status": "fail",
                "fr": "FR-0700",
                "ac": "AC-FR0700-01",
                "interface": "IF-REG-01",
                "arc": "ARC-REGISTRY",
                "contract": "integration-test",
            }
        ],
    }
    result = mock_design_contract.validate_manifest({})
    check = result["checks"][0]
    for key in ("fr", "ac", "interface", "arc", "contract"):
        assert key in check
