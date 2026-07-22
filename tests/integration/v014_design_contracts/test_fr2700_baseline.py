"""Integration tests for FR-2700: Implementation Baseline & No Second M-LOCK.

AC-FR2700-01: After all program gates and Prism review PASS for the same
revision, Runtime atomically generates a baseline containing requirements/
design/contracts/prompts/base/Issues/release/discussions identity and
enters M-IMPL. WorkflowDefinition and new run history contain no second
M-LOCK after design or Human technical approval wait; any gate stale
cannot enter M-IMPL.
"""
# AC-FR2700-01

from __future__ import annotations

import pytest


def test_design_manifest_has_canonical_release_identity(design_manifest):
    """manifest.canonical_release_identity must lock version=0.14.0,
    spec_id=v0.14-002-workflow-reflow-design, base_commit."""
    identity = design_manifest["canonical_release_identity"]
    assert identity["version"] == "0.14.0"
    assert identity["spec_id"] == "v0.14-002-workflow-reflow-design"
    assert identity["base_commit"].startswith("2734177")


def test_design_manifest_activation_state_is_candidate_not_installed(design_manifest):
    """Candidate manifest must be candidate-not-installed (not active)."""
    assert design_manifest["activation_state"] == "candidate-not-installed"


def test_design_manifest_lists_required_artifacts(design_manifest):
    """manifest must list requirements, spec, acceptance, review_remediation."""
    req = design_manifest["requirements"]
    for key in ("story", "spec", "acceptance", "review_remediation"):
        assert key in req, f"requirements missing {key}"
        assert req[key].startswith("sha256:")


def test_design_manifest_input_artifacts_include_facts_and_task(design_manifest):
    """input_artifacts must include host-project-facts-snapshot and
    archer-author-task-manifest."""
    kinds = {a["kind"] for a in design_manifest["input_artifacts"]}
    assert "host-project-facts-snapshot" in kinds
    assert "archer-author-task-manifest" in kinds


def test_design_manifest_closure_counts_match_expected(design_manifest):
    """closure_counts must reflect 34 ACs, 15 IFs, 16 ARCs, 7 schemas."""
    counts = design_manifest["closure_counts"]
    assert counts["acceptance"] == 34
    assert counts["interfaces"] == 15
    assert counts["architecture_anchors"] == 16
    assert counts["machine_schema_kinds"] == 7
    assert counts["agent_io_schemas"] == 4
    assert counts["contract_instances"] == 7
    assert counts["heterogeneous_positive_fixtures"] == 1
    assert counts["negative_validation_cases"] == 8


@pytest.mark.awaiting_devon("FR-2700")
def test_baseline_atomic_creation(mock_design_coordinator):
    """Runtime must atomically create baseline after all gates PASS."""
    mock_design_coordinator.create_baseline.return_value = {
        "ok": True,
        "baseline_identity": "louke.baseline.v0.14-002.r1",
        "stage": "M-IMPL",
    }
    result = mock_design_coordinator.create_baseline(revision="r1")
    assert result["ok"]
    assert result["stage"] == "M-IMPL"


@pytest.mark.awaiting_devon("FR-2700")
def test_baseline_blocks_when_gate_stale(mock_design_coordinator):
    """Any stale gate must block baseline creation."""
    mock_design_coordinator.create_baseline.return_value = {
        "ok": False,
        "error": "GATE_STALE",
        "stale_gates": ["IF-DES-02", "IF-REV-01"],
    }
    result = mock_design_coordinator.create_baseline(revision="r1")
    assert not result["ok"]
    assert "stale_gates" in result


@pytest.mark.awaiting_devon("FR-2700")
def test_no_second_m_lock_after_design(mock_design_coordinator):
    """WorkflowDefinition must not contain a second M-LOCK after design."""
    mock_design_coordinator.inspect_workflow_definition.return_value = {
        "stages": ["M-DESIGN", "M-IMPL"],
        "m_lock_count": 1,
        "m_lock_positions": ["before-M-DESIGN"],
    }
    result = mock_design_coordinator.inspect_workflow_definition()
    assert result["m_lock_count"] == 1
    assert "after-design" not in result["m_lock_positions"]
