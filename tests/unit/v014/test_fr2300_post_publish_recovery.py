"""AC-FR2300-01: Post-publish verification & recovery.

Runtime must confirm main/tag/release/artifacts point to the approved
candidate, and execute version + basic smoke from real install/deploy/
run outlets.  On failure, Runtime executes the current rollback/forward-
fix contract's automatic safe steps; credential/external-ownership/
irreversible-conflict issues request Human authorization; technical
fixes still return to the specialist Agent.  All facts must be verified
before the state leaves ``publishing``/``needs_attention``; ``completed``
is forbidden before verification.
"""

from __future__ import annotations


from louke.v014.fr2300_post_publish_recovery import (
    OutletVerification,
    PostPublishReport,
    PublishFact,
    verify_post_publish,
)

_CAND = "c" * 40


def _facts(
    *,
    main_ok: bool = True,
    tag_ok: bool = True,
    release_ok: bool = True,
    artifacts_ok: bool = True,
) -> list[PublishFact]:
    return [
        PublishFact(
            name="main", target_oid=_CAND, actual_oid=_CAND if main_ok else "x" * 40
        ),
        PublishFact(
            name="tag", target_oid=_CAND, actual_oid=_CAND if tag_ok else "x" * 40
        ),
        PublishFact(
            name="release",
            target_oid=_CAND,
            actual_oid=_CAND if release_ok else "x" * 40,
        ),
        PublishFact(
            name="artifacts",
            target_oid=_CAND,
            actual_oid=_CAND if artifacts_ok else "x" * 40,
        ),
    ]


def _outlets(
    *, install_ok: bool = True, runtime_ok: bool = True, smoke_ok: bool = True
) -> list[OutletVerification]:
    return [
        OutletVerification(
            name="install",
            outlet="pip install louke==0.14.0",
            value="0.14.0",
            passed=install_ok,
        ),
        OutletVerification(
            name="runtime", outlet="lk --version", value="0.14.0", passed=runtime_ok
        ),
        OutletVerification(
            name="smoke", outlet="lk --help", value="ok", passed=smoke_ok
        ),
    ]


def test_verify_post_publish_passes_when_all_facts_and_outlets_match() -> None:
    """AC-FR2300-01: main/tag/release/artifacts match + install/runtime/smoke PASS."""
    report = verify_post_publish(_CAND, _facts(), _outlets())
    assert isinstance(report, PostPublishReport)
    assert report.status == "pass"
    assert report.recovery is None


def test_verify_post_publish_fails_when_main_mismatches() -> None:
    """AC-FR2300-01: main pointer mismatch blocks PASS."""
    report = verify_post_publish(_CAND, _facts(main_ok=False), _outlets())
    assert report.status == "fail"
    assert report.recovery is not None  # AC-FR2300-01
    assert report.recovery.kind in ("rollback", "forward-fix", "human-authorization")


def test_verify_post_publish_fails_when_tag_mismatches() -> None:
    """AC-FR2300-01: tag pointer mismatch blocks PASS."""
    report = verify_post_publish(_CAND, _facts(tag_ok=False), _outlets())
    assert report.status == "fail"


def test_verify_post_publish_fails_when_release_mismatches() -> None:
    """AC-FR2300-01: GitHub Release target mismatch blocks PASS."""
    report = verify_post_publish(_CAND, _facts(release_ok=False), _outlets())
    assert report.status == "fail"


def test_verify_post_publish_fails_when_artifacts_mismatch() -> None:
    """AC-FR2300-01: artifact target mismatch blocks PASS."""
    report = verify_post_publish(_CAND, _facts(artifacts_ok=False), _outlets())
    assert report.status == "fail"


def test_verify_post_publish_fails_when_install_outlet_fails() -> None:
    """AC-FR2300-01: install outlet failure blocks PASS."""
    report = verify_post_publish(_CAND, _facts(), _outlets(install_ok=False))
    assert report.status == "fail"


def test_verify_post_publish_fails_when_smoke_fails() -> None:
    """AC-FR2300-01: smoke failure blocks PASS."""
    report = verify_post_publish(_CAND, _facts(), _outlets(smoke_ok=False))
    assert report.status == "fail"


def test_recovery_routes_credential_issue_to_human() -> None:
    """AC-FR2300-01: credential/external-ownership issues request Human authorization."""
    report = verify_post_publish(
        _CAND,
        _facts(main_ok=False),
        _outlets(),
        issue_kind="credential-conflict",
    )
    assert report.recovery.kind == "human-authorization"


def test_recovery_routes_technical_fix_to_specialist_agent() -> None:
    """AC-FR2300-01: technical fixes return to specialist Agent, not Human."""
    report = verify_post_publish(
        _CAND,
        _facts(main_ok=False),
        _outlets(),
        issue_kind="technical",
    )
    assert report.recovery.kind == "forward-fix"
    assert report.recovery.target.startswith(("Devon", "Shield", "M-DESIGN"))


def test_state_stays_publishing_until_verified() -> None:
    """AC-FR2300-01: state stays publishing/needs_attention until all facts verified."""
    report = verify_post_publish(_CAND, _facts(main_ok=False), _outlets())
    assert report.new_state == "needs_attention"


def test_state_completed_only_after_full_pass() -> None:
    """AC-FR2300-01: completed only after all facts + outlets PASS."""
    report = verify_post_publish(_CAND, _facts(), _outlets())
    assert report.new_state == "completed"
