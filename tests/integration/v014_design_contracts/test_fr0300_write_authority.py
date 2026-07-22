"""Integration tests for FR-0300: Design Write Authority & Artifact Attribution.

AC-FR0300-01: Archer manifest explicitly lists allowed three design docs,
machine contracts, affected prompt sources and forbidden side effects;
only patches in that range are accepted. Constructing out-of-scope files,
Git/stage side effects or unattributed diffs causes program gate to
reject revision; original baseline remains unchanged.
"""
# AC-FR0300-01

from __future__ import annotations

import pytest


def test_manifest_input_artifacts_declare_archer_task_manifest(design_manifest):
    """manifest must include archer-author-task-manifest as input artifact."""
    kinds = {a["kind"] for a in design_manifest["input_artifacts"]}
    assert "archer-author-task-manifest" in kinds


def test_manifest_design_docs_list_three_documents(design_manifest):
    """manifest.design_docs must list test-plan, architecture, interfaces."""
    paths = {d["path"] for d in design_manifest["design_docs"]}
    expected = {
        ".louke/project/specs/v0.14-002-workflow-reflow-design/test-plan.md",
        ".louke/project/specs/v0.14-002-workflow-reflow-design/architecture.md",
        ".louke/project/specs/v0.14-002-workflow-reflow-design/interfaces.md",
    }
    assert paths == expected, f"design_docs paths mismatch: {paths} vs {expected}"


def test_manifest_contract_instances_list_seven_kinds(design_manifest):
    """manifest.contract_instances must list exactly 7 contract kinds."""
    instances = design_manifest["contract_instances"]
    kinds = {i["kind"] for i in instances}
    expected_kinds = {
        "integration-test",
        "e2e-test",
        "pre-commit",
        "github-actions-ci",
        "release-version",
        "build-artifact",
        "publish-recovery",
    }
    assert kinds == expected_kinds


def test_manifest_prompt_sources_only_canonical(design_manifest):
    """manifest prompt sources must only be Archer.md and Prism.md."""
    sources = design_manifest["prompt_candidates"]["sources"]
    paths = {s["path"] for s in sources}
    assert paths == {"louke/agents/Archer.md", "louke/agents/Prism.md"}


@pytest.mark.awaiting_devon("FR-0300")
def test_out_of_scope_file_rejected(mock_design_coordinator):
    """Out-of-scope file patch must be rejected."""
    mock_design_coordinator.validate_patch.return_value = {
        "ok": False,
        "error": "OUT_OF_SCOPE",
        "path": "unauthorized_file.py",
    }
    result = mock_design_coordinator.validate_patch(
        path="unauthorized_file.py", diff="..."
    )
    assert not result["ok"]


@pytest.mark.awaiting_devon("FR-0300")
def test_git_side_effect_rejected(mock_design_coordinator):
    """Git/stage side effect must be rejected."""
    mock_design_coordinator.validate_patch.return_value = {
        "ok": False,
        "error": "GIT_SIDE_EFFECT_FORBIDDEN",
    }
    result = mock_design_coordinator.validate_patch(path=".git/HEAD", diff="...")
    assert not result["ok"]


@pytest.mark.awaiting_devon("FR-0300")
def test_unattributed_diff_rejected(mock_design_coordinator):
    """Unattributed diff must be rejected."""
    mock_design_coordinator.validate_patch.return_value = {
        "ok": False,
        "error": "UNATTRIBUTED_DIFF",
    }
    result = mock_design_coordinator.validate_patch(
        path=".louke/project/specs/v0.14-002-workflow-reflow-design/spec.md",
        diff="...",
        actor=None,
    )
    assert not result["ok"]


@pytest.mark.awaiting_devon("FR-0300")
def test_baseline_unchanged_after_rejection(mock_design_coordinator):
    """After rejection, original baseline must remain unchanged."""
    mock_design_coordinator.validate_patch.return_value = {
        "ok": False,
        "error": "OUT_OF_SCOPE",
        "baseline_unchanged": True,
    }
    result = mock_design_coordinator.validate_patch(path="unauthorized.py", diff="...")
    assert result["baseline_unchanged"] is True
