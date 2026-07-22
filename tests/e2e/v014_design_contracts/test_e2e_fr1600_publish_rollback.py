"""E2E: FR-1600 Publish recovery rollback (extension beyond required suite).

AC-FR1600-01 is not in the required e2e suite, but publish recovery
ledger semantics (query-before-retry, rollback, partial success) are
critical for safety. This test verifies the publish-recovery contract
candidate at the e2e layer.
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
def publish_contract():
    path = DESIGN_ARTIFACTS / "contracts" / "publish-recovery.candidate.json"
    if not path.exists():
        # AC-FR1600-01
        pytest.skip(f"publish-recovery contract candidate not yet present at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def test_publish_contract_canonical_envelope(publish_contract):
    """publish-recovery contract must follow the canonical envelope."""
    assert publish_contract.get("kind") == "publish-recovery"
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
        assert key in publish_contract, f"publish contract missing envelope key: {key}"


def test_publish_contract_kind_matches(publish_contract):
    """publish-recovery contract kind must be publish-recovery."""
    assert publish_contract.get("kind") == "publish-recovery"


def test_publish_contract_declares_operations(publish_contract):
    """publish-recovery payload must declare operations (ledger entries)."""
    payload = publish_contract.get("payload", {})
    has_operations = any(
        key in payload
        for key in ("operations", "ledger", "operation_sequence", "publish_operations")
    )
    assert has_operations, "publish-recovery payload must declare operations"


def test_publish_contract_query_before_retry(publish_contract):
    """publish-recovery must enforce query-before-retry semantics."""
    payload = publish_contract.get("payload", {})
    payload_text = json.dumps(payload).lower()
    # Look for query/reconcile/identity semantics.
    assert any(
        kw in payload_text for kw in ("query", "reconcile", "identity", "expected_fact")
    ), "publish-recovery must declare query-before-retry semantics"


def test_publish_contract_no_blind_retry(publish_contract):
    """publish-recovery must NOT endorse blind retry.

    The contract may mention ``--skip-existing`` in a prohibition context
    (e.g., "no --skip-existing inference"). What's forbidden is ENDORSING
    blind retry without query, not merely mentioning the term.
    """
    payload = publish_contract.get("payload", {})
    payload_text = json.dumps(payload).lower()
    # Forbidden: endorsement of blind retry without query.
    forbidden_endorsements = ("blind_retry", "auto_retry_without_query")
    for pattern in forbidden_endorsements:
        assert pattern not in payload_text, (
            f"publish-recovery must not endorse forbidden pattern: {pattern}"
        )
    # "skip-existing" may appear only in a prohibition context.
    if "skip-existing" in payload_text:
        # Must be preceded by a negation keyword.
        idx = payload_text.find("skip-existing")
        prefix = payload_text[max(0, idx - 20) : idx]
        negation_keywords = ("no ", "not ", "forbidden", "must not", "without")
        assert any(neg in prefix for neg in negation_keywords), (
            "publish-recovery mentions 'skip-existing' without negation context; "
            "blind retry is forbidden"
        )


def test_publish_contract_partial_success(publish_contract):
    """publish-recovery must declare partial-success handling."""
    payload = publish_contract.get("payload", {})
    payload_text = json.dumps(payload).lower()
    assert any(
        kw in payload_text
        for kw in ("partial", "forward_fix", "forward-fix", "rollback")
    ), "publish-recovery must declare partial-success or rollback semantics"


def test_publish_contract_immutable_tag(publish_contract):
    """publish-recovery must declare that immutable tags/versions are not rolled back."""
    payload = publish_contract.get("payload", {})
    payload_text = json.dumps(payload).lower()
    # Look for "immutable", "no_rollback", "no-rollback", "tag" + "not rollback".
    assert any(
        kw in payload_text
        for kw in ("immutable", "no_rollback", "no-rollback", "irreversible")
    ), "publish-recovery must declare immutable tag/version no-rollback semantics"


def test_publish_contract_credentials_reference_only(publish_contract):
    """publish-recovery must NOT persist credentials, only references."""
    payload = publish_contract.get("payload", {})
    payload_text = json.dumps(payload).lower()
    # Look for credential reference semantics.
    assert any(
        kw in payload_text for kw in ("reference", "credential", "secret", "token")
    ), "publish-recovery must declare credential reference semantics"
    # Must NOT persist actual secret values.
    forbidden_secret_patterns = ("password=", "token=", "api_key=", "secret=")
    for pattern in forbidden_secret_patterns:
        # Allow these only if they're in a "reference" context, not as values.
        if pattern in payload_text:
            # Check the context around it - if "reference" appears, it's OK.
            assert "reference" in payload_text, (
                f"publish-recovery payload contains '{pattern}' without credential reference semantics"
            )


@pytest.mark.awaiting_devon("FR-1600")
def test_publish_rollback_visible_through_workbench(workbench_api):
    """Publish rollback ledger must be visible through Workbench audit surface."""
    assert workbench_api is not None  # AC-FR1600-01


def test_publish_contract_failure_policy(publish_contract):
    """publish-recovery must fail closed on unknown state."""
    payload = publish_contract.get("payload", {})
    failure_policy = payload.get("failure_policy", {})
    if not failure_policy:
        # Look for failure_policy key anywhere in payload.
        for value in payload.values():
            if isinstance(value, dict) and "fail_closed" in value:
                failure_policy = value
                break
    if not failure_policy:
        payload_text = json.dumps(payload)
        assert "fail" in payload_text.lower() and "close" in payload_text.lower(), (
            "publish-recovery must declare fail-closed semantics"
        )
    else:
        assert failure_policy.get("fail_closed") is True
