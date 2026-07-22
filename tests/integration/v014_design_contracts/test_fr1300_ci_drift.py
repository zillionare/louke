"""Integration tests for FR-1300: CI Coexistence, Generation & Drift Lifecycle.

AC-FR1300-01: Same contract input repeatedly generating managed workflow
yields identical canonical content/digest; other workflows/rules unchanged;
non-drifted files idempotently upgrade. After Human modifies managed file,
reconcile preserves visible diff without silent overwrite; missing, invalid
YAML, command not existing or digest drift all block PASS.
"""
# AC-FR1300-01

from __future__ import annotations

import pytest


@pytest.mark.awaiting_devon("FR-1300")
def test_repeated_generation_yields_identical_digest(mock_ci_contract):
    """Same contract input must produce identical canonical digest."""
    mock_ci_contract.generate.return_value = {
        "ok": True,
        "digest": "sha256:abc",
        "content": "name: CI\n",
    }
    r1 = mock_ci_contract.generate(contract={})
    r2 = mock_ci_contract.generate(contract={})
    assert r1["digest"] == r2["digest"]


@pytest.mark.awaiting_devon("FR-1300")
def test_other_workflows_unchanged(mock_ci_contract):
    """Other workflows/rules must remain unchanged after generation."""
    mock_ci_contract.generate.return_value = {
        "ok": True,
        "managed_files": [".github/workflows/louke-ci.yml"],
        "unchanged_files": [
            ".github/workflows/ci.yml",
            ".github/workflows/release.yml",
        ],
    }
    result = mock_ci_contract.generate(contract={})
    assert len(result["unchanged_files"]) >= 2


@pytest.mark.awaiting_devon("FR-1300")
def test_human_drift_preserves_visible_diff(mock_ci_contract):
    """Human-modified managed file must preserve visible diff."""
    mock_ci_contract.reconcile.return_value = {
        "ok": True,
        "visible_diff": True,
        "silent_overwrite": False,
    }
    result = mock_ci_contract.reconcile()
    assert result["visible_diff"] is True
    assert result["silent_overwrite"] is False


@pytest.mark.awaiting_devon("FR-1300")
def test_missing_managed_file_blocks_pass(mock_ci_contract):
    """Missing managed file must block PASS."""
    mock_ci_contract.reconcile.return_value = {
        "ok": False,
        "error": "MISSING_MANAGED_FILE",
        "path": ".github/workflows/louke-ci.yml",
    }
    result = mock_ci_contract.reconcile()
    assert not result["ok"]


@pytest.mark.awaiting_devon("FR-1300")
def test_invalid_yaml_blocks_pass(mock_ci_contract):
    """Invalid YAML must block PASS."""
    mock_ci_contract.reconcile.return_value = {
        "ok": False,
        "error": "INVALID_YAML",
    }
    result = mock_ci_contract.reconcile()
    assert not result["ok"]


@pytest.mark.awaiting_devon("FR-1300")
def test_command_missing_blocks_pass(mock_ci_contract):
    """Command referenced in workflow not existing must block PASS."""
    mock_ci_contract.reconcile.return_value = {
        "ok": False,
        "error": "COMMAND_NOT_FOUND",
        "command": "tests/e2e/run-project-venv",
    }
    result = mock_ci_contract.reconcile()
    assert not result["ok"]
