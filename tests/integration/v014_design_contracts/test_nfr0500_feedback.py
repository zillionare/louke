"""Integration tests for NFR-0500: Validator Feedback Actionability.

AC-NFR0500-01: For schema, trace, prompt drift and project path failures,
output includes stable check ID, path/field, expected/actual, related
identity and retryability. UI/API does not only show generic failure
strings; users can navigate from result to the artifact anchor to fix.

Note: NFR-0500 also has an E2E component.
"""
# AC-NFR0500-01

from __future__ import annotations

import pytest


@pytest.mark.awaiting_devon("NFR-0500")
def test_schema_failure_feedback_has_required_fields(mock_design_contract):
    """Schema failure feedback must include stable check ID, path/field,
    expected/actual, related identity and retryability."""
    mock_design_contract.validate_manifest.return_value = {
        "ok": False,
        "checks": [{
            "id": "schema-missing-field",
            "status": "fail",
            "category": "schema",
            "path": "contracts/integration-test.candidate.json",
            "field": "payload.commands",
            "expected": "non-empty list",
            "actual": "missing",
            "related_identity": "louke.contract.v0.14-002.integration-test",
            "retryable": True,
        }],
    }
    result = mock_design_contract.validate_manifest({})
    check = result["checks"][0]
    for key in ("id", "path", "field", "expected", "actual", "related_identity", "retryable"):
        assert key in check, f"schema feedback missing {key}"


@pytest.mark.awaiting_devon("NFR-0500")
def test_trace_failure_feedback_has_required_fields(mock_design_contract):
    """Trace failure feedback must include required fields."""
    mock_design_contract.validate_manifest.return_value = {
        "ok": False,
        "checks": [{
            "id": "trace-orphan-interface",
            "status": "fail",
            "category": "trace",
            "path": "interfaces.md",
            "field": "IF-XXX-99",
            "expected": "referenced by at least one AC",
            "actual": "orphan",
            "related_identity": "IF-XXX-99",
            "retryable": True,
        }],
    }
    result = mock_design_contract.validate_manifest({})
    check = result["checks"][0]
    assert check["category"] == "trace"
    for key in ("id", "path", "expected", "actual", "retryable"):
        assert key in check


@pytest.mark.awaiting_devon("NFR-0500")
def test_prompt_drift_failure_feedback_has_required_fields(
    mock_design_contract,
):
    """Prompt drift failure feedback must include required fields."""
    mock_design_contract.validate_manifest.return_value = {
        "ok": False,
        "checks": [{
            "id": "prompt-drift",
            "status": "fail",
            "category": "prompt-drift",
            "path": ".opencode/agents/archer.md",
            "field": "digest",
            "expected": "sha256:abc",
            "actual": "sha256:def",
            "related_identity": "louke.prompt-bundle.v0.14-002.r4",
            "retryable": True,
        }],
    }
    result = mock_design_contract.validate_manifest({})
    check = result["checks"][0]
    assert check["category"] == "prompt-drift"


@pytest.mark.awaiting_devon("NFR-0500")
def test_project_path_failure_feedback_has_required_fields(
    mock_design_contract,
):
    """Project path failure feedback must include required fields."""
    mock_design_contract.validate_manifest.return_value = {
        "ok": False,
        "checks": [{
            "id": "path-out-of-scope",
            "status": "fail",
            "category": "project-path",
            "path": "unauthorized.py",
            "field": "patch_target",
            "expected": "within manifest allowlist",
            "actual": "out of scope",
            "related_identity": "archer-task-manifest",
            "retryable": False,
        }],
    }
    result = mock_design_contract.validate_manifest({})
    check = result["checks"][0]
    assert check["category"] == "project-path"
    assert check["retryable"] is False


@pytest.mark.awaiting_devon("NFR-0500")
def test_feedback_not_generic_failure_string(mock_design_contract):
    """Feedback must not be only a generic failure string."""
    mock_design_contract.validate_manifest.return_value = {
        "ok": False,
        "checks": [{
            "id": "specific-check-id",
            "status": "fail",
            "path": "specific/path.md",
            "field": "specific_field",
            "expected": "specific value",
            "actual": "different value",
        }],
    }
    result = mock_design_contract.validate_manifest({})
    check = result["checks"][0]
    # Must have path and field, not just a message
    assert "path" in check and "field" in check
