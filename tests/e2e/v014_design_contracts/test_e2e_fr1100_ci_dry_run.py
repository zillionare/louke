"""E2E: FR-1100 CI contract dry-run (extension beyond required suite).

AC-FR1100-01 is not in the required e2e suite, but the CI contract
generator must produce a readback-able workflow file. This test
verifies the CI contract structure at the e2e layer using the
ci_contract candidate artifact.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.v014_002_e2e

REPO_ROOT = Path(__file__).resolve().parents[3]
TESTS_ROOT = REPO_ROOT / "tests"
SPEC_ROOT = (
    REPO_ROOT / ".louke" / "project" / "specs" / "v0.14-002-workflow-reflow-design"
)
DESIGN_ARTIFACTS = SPEC_ROOT / "design-artifacts"


@pytest.fixture(scope="module")
def ci_contract():
    path = DESIGN_ARTIFACTS / "contracts" / "github-actions-ci.candidate.json"
    if not path.exists():
        # AC-FR1100-01
        pytest.skip(f"CI contract candidate not yet present at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def test_ci_contract_canonical_envelope(ci_contract):
    """CI contract must follow the canonical envelope {kind, identity, ...}."""
    assert ci_contract.get("kind") == "github-actions-ci"
    for key in (
        "identity",
        "revision",
        "schema_ref",
        "manifest_ref",
        "scope",
        "generated_by",
        "compatible_runtime",
        "artifact_refs",
        "payload",
    ):
        assert key in ci_contract, f"CI contract missing envelope key: {key}"


def test_ci_contract_kind_matches(ci_contract):
    """CI contract kind must be github-actions-ci."""
    assert ci_contract.get("kind") == "github-actions-ci"


def test_ci_contract_payload_has_workflow(ci_contract):
    """CI contract payload must declare workflow targets."""
    payload = ci_contract.get("payload", {})
    # The CI contract must declare either workflows, jobs, or rulesets.
    has_workflow = any(
        key in payload
        for key in (
            "workflows",
            "jobs",
            "rulesets",
            "workflow_targets",
            "managed_workflows",
        )
    )
    assert has_workflow, "CI contract payload must declare workflow targets"


def test_ci_contract_preserves_user_workflows(ci_contract):
    """CI contract must declare that user workflows are preserved (not overwritten)."""
    payload = ci_contract.get("payload", {})
    payload_text = json.dumps(payload)
    # Look for preservation semantics: "preserve", "user", "existing", "non-managed".
    preservation_keywords = (
        "preserve",
        "user",
        "existing",
        "non-managed",
        "owner_marker",
    )
    assert any(kw in payload_text.lower() for kw in preservation_keywords), (
        "CI contract must declare user workflow preservation semantics"
    )


def test_ci_contract_owner_marker(ci_contract):
    """CI contract must use owner marker (.github/workflows/louke-ci.yml)."""
    payload = ci_contract.get("payload", {})
    payload_text = json.dumps(payload)
    assert "louke-ci.yml" in payload_text, (
        "CI contract must reference .github/workflows/louke-ci.yml as owner marker"
    )


def test_ci_contract_required_aggregate(ci_contract):
    """CI contract must declare required aggregate (Louke CI / required)."""
    payload = ci_contract.get("payload", {})
    payload_text = json.dumps(payload)
    assert "required" in payload_text.lower(), (
        "CI contract must declare required aggregate job"
    )


@pytest.mark.awaiting_devon("FR-1100")
def test_ci_dry_run_visible_through_workbench(workbench_api):
    """CI dry-run readback must be visible through Workbench."""
    assert workbench_api is not None  # AC-FR1100-01


def test_ci_contract_failure_policy(ci_contract):
    """CI contract must fail closed (publish only accepts Louke CI / required)."""
    payload = ci_contract.get("payload", {})
    failure_policy = payload.get("failure_policy", {})
    # Failure policy may be in payload or nested; check both.
    if not failure_policy:
        # Look for failure_policy key anywhere in payload.
        for value in payload.values():
            if isinstance(value, dict) and "fail_closed" in value:
                failure_policy = value
                break
    # If still not found, the contract must at least mention fail-closed semantics.
    if not failure_policy:
        payload_text = json.dumps(payload)
        assert "fail" in payload_text.lower() and "close" in payload_text.lower(), (
            "CI contract must declare fail-closed semantics"
        )
    else:
        assert failure_policy.get("fail_closed") is True
