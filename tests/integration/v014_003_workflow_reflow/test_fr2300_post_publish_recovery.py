"""Integration tests for FR-2300: Post-publish verification & recovery.

AC-FR2300-01: Publish success requires main/tag/release/artifacts to
point to the approved candidate AND real install/deploy/run version +
basic smoke all verified. On failure, Runtime executes the current
rollback/forward-fix contract's automatic safe steps; credential/
external-ownership/irreversible-conflict issues request Human
authorization; technical fixes still return to the specialist Agent.
All facts must be verified before leaving publishing/needs_attention;
completed is forbidden before verification.

Interfaces covered (per interfaces.md):
- IF-PUB-02 (Primary ARC-15)
- IF-BLD-02 (artifact outlets, ARC-12)
- IF-WFR-01 (workflow state, ARC-01)
"""
# AC-FR2300-01

from __future__ import annotations

import pytest

from louke.v014.fr2300_post_publish_recovery import (
    ERROR_CODES,
    OutletVerification,
    PostPublishReport,
    PublishFact,
    RecoveryDecision,
    verify_post_publish,
)


def _matching_facts() -> list[PublishFact]:
    return [
        PublishFact(name="main", target_oid="c" * 40, actual_oid="c" * 40),
        PublishFact(name="tag", target_oid="c" * 40, actual_oid="c" * 40),
        PublishFact(name="release", target_oid="c" * 40, actual_oid="c" * 40),
        PublishFact(name="artifacts", target_oid="c" * 40, actual_oid="c" * 40),
    ]


def _passing_outlets() -> list[OutletVerification]:
    return [
        OutletVerification(
            name="install",
            outlet="pip install louke==0.14.0",
            value="0.14.0",
            passed=True,
        ),
        OutletVerification(
            name="runtime",
            outlet="lk --version",
            value="0.14.0",
            passed=True,
        ),
        OutletVerification(
            name="smoke",
            outlet="lk health",
            value="ok",
            passed=True,
        ),
    ]


# ---------------------------------------------------------------------------
# verify_post_publish
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_verify_post_publish_passes_when_all_facts_and_outlets_match():
    """AC-FR2300-01: main/tag/release/artifacts + install/runtime/smoke verified
    -> completed."""
    report = verify_post_publish(
        "c" * 40,
        _matching_facts(),
        _passing_outlets(),
    )
    assert isinstance(report, PostPublishReport)
    assert report.status == "pass"
    assert report.new_state == "completed"
    assert report.recovery is None


@pytest.mark.real_module
def test_verify_post_publish_fails_when_main_oid_mismatches():
    """AC-FR2300-01: main not pointing to candidate -> fail + needs_attention."""
    facts = _matching_facts()
    facts[0] = PublishFact(
        name="main",
        target_oid="c" * 40,
        actual_oid="x" * 40,  # different
    )
    report = verify_post_publish("c" * 40, facts, _passing_outlets())
    assert report.status == "fail"
    assert report.new_state == "needs_attention"
    assert report.recovery is not None


@pytest.mark.real_module
def test_verify_post_publish_fails_when_tag_oid_mismatches():
    """AC-FR2300-01: tag not pointing to candidate -> fail."""
    facts = _matching_facts()
    facts[1] = PublishFact(
        name="tag",
        target_oid="c" * 40,
        actual_oid="x" * 40,
    )
    report = verify_post_publish("c" * 40, facts, _passing_outlets())
    assert report.status == "fail"


@pytest.mark.real_module
def test_verify_post_publish_fails_when_install_outlet_fails():
    """AC-FR2300-01: install outlet returned wrong version -> fail."""
    outlets = _passing_outlets()
    outlets[0] = OutletVerification(
        name="install",
        outlet="pip install louke==0.14.0",
        value="0.13.0",
        passed=False,  # wrong version
    )
    report = verify_post_publish("c" * 40, _matching_facts(), outlets)
    assert report.status == "fail"
    assert report.new_state == "needs_attention"


@pytest.mark.real_module
def test_verify_post_publish_recovery_technical_routes_to_devon():
    """AC-FR2300-01: technical failure -> forward-fix to Devon (not Human)."""
    facts = _matching_facts()
    facts[0] = PublishFact(
        name="main",
        target_oid="c" * 40,
        actual_oid="x" * 40,
    )
    report = verify_post_publish(
        "c" * 40,
        facts,
        _passing_outlets(),
        issue_kind="technical",
    )
    assert report.recovery.kind == "forward-fix"
    assert report.recovery.target == "Devon"


@pytest.mark.real_module
def test_verify_post_publish_recovery_credential_conflict_requires_human():
    """AC-FR2300-01: credential conflict -> Human authorization required."""
    facts = _matching_facts()
    facts[0] = PublishFact(
        name="main",
        target_oid="c" * 40,
        actual_oid="x" * 40,
    )
    report = verify_post_publish(
        "c" * 40,
        facts,
        _passing_outlets(),
        issue_kind="credential-conflict",
    )
    assert isinstance(report.recovery, RecoveryDecision)
    assert report.recovery.kind == "human-authorization"


@pytest.mark.real_module
def test_verify_post_publish_recovery_irreversible_conflict_requires_human():
    """AC-FR2300-01: irreversible conflict -> Human authorization required."""
    facts = _matching_facts()
    facts[0] = PublishFact(
        name="main",
        target_oid="c" * 40,
        actual_oid="x" * 40,
    )
    report = verify_post_publish(
        "c" * 40,
        facts,
        _passing_outlets(),
        issue_kind="irreversible-conflict",
    )
    assert report.recovery.kind == "human-authorization"


@pytest.mark.real_module
def test_verify_post_publish_does_not_complete_before_verification():
    """AC-FR2300-01: completed forbidden until all facts verified."""
    facts = _matching_facts()
    facts[0] = PublishFact(
        name="main",
        target_oid="c" * 40,
        actual_oid="x" * 40,
    )
    report = verify_post_publish("c" * 40, facts, _passing_outlets())
    # new_state must NOT be completed.
    assert report.new_state != "completed"


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-FR2300-01: ERROR_CODES includes all codes from interfaces.md §13."""
    expected = {
        "PUB_PRECONDITION_FAILED",
        "PUB_PROVIDER_AMBIGUOUS",
        "PUB_RESOURCE_IDENTITY_MISMATCH",
        "PUB_IMMUTABLE_CONFLICT",
        "PUB_CREDENTIAL_UNAVAILABLE",
        "PUB_RECONCILE_REQUIRED",
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
