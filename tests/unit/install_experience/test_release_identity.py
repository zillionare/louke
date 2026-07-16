"""Unit tests for the host-independent release identity contract."""

from louke.release_identity import verify_release_identity


def test_ac_fr1510_01_matching_tag_and_artifact_pass() -> None:
    """AC-FR1510-01: a matching tag and artifact version passes."""
    result = verify_release_identity("v0.13.1", "0.13.1")

    assert result.passed is True
    assert result.normalized_tag == "0.13.1"
    assert result.artifact_version == "0.13.1"
    assert result.diagnostic


def test_ac_fr1510_01_mismatch_reports_both_versions() -> None:
    """AC-FR1510-01: a mismatch fails with both versions in its diagnostic."""
    result = verify_release_identity("v0.13.1", "0.13.0")

    assert result.passed is False
    assert "0.13.1" in result.diagnostic
    assert "0.13.0" in result.diagnostic


def test_ac_fr1510_02_removes_only_one_leading_v() -> None:
    """AC-FR1510-02: only one leading ``v`` is normalized away."""
    result = verify_release_identity("vv1.2.3", "v1.2.3")

    assert result.passed is True
    assert result.normalized_tag == "v1.2.3"


def test_ac_nfr1504_02_dirty_tag_fails_with_diagnostic() -> None:
    """AC-NFR1504-02: dirty tags fail and explain the invalid input."""
    result = verify_release_identity("v0.13.1-dirty", "0.13.1")

    assert result.passed is False
    assert result.diagnostic
    assert "dirty" in result.diagnostic


def test_ac_nfr1504_02_missing_inputs_fail_with_diagnostic() -> None:
    """AC-NFR1504-02: missing tag or version fails without side effects."""
    for tag, version in ((None, "0.13.1"), ("v0.13.1", None)):
        result = verify_release_identity(tag, version)

        assert result.passed is False
        assert result.diagnostic
