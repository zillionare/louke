"""Integration tests for FR-1600: Version, build, artifact & public version
verification.

AC-FR1600-01: For every declared artifact, evidence shows version source
prepared, artifact built, digest/version extracted+matched, applicable
installed/runtime version matched, all bound to candidate/canonical
identity. Injected artifact missing, unextractable, version mismatch or
stale public outlet must FAIL; branch/tag/source declarations may NOT
substitute for artifact/install verification.

Interfaces covered (per interfaces.md):
- IF-BLD-02 (Primary ARC-12)
- IF-REL-01 (inherited, ARC-12)
- IF-BLD-01 (inherited, ARC-12)
"""
# AC-FR1600-01

from __future__ import annotations

import pytest

from louke.v014.fr1600_artifact_version import (
    ERROR_CODES,
    ArtifactEvidence,
    ArtifactVerificationError,
    ArtifactVerifier,
    VerificationReport,
)


def _valid_artifact(kind: str = "wheel") -> ArtifactEvidence:
    return ArtifactEvidence(
        artifact_id=f"art-{kind}",
        kind=kind,
        path=f"dist/louke-0.14.0.{'whl' if kind == 'wheel' else 'tar.gz'}",
        digest=f"sha256:{kind}-digest",
        size=1024,
        stage="installed_runtime_verified",
        extracted_version="0.14.0",
        install_environment="clean-venv",
        runtime_version="0.14.0",
    )


def _valid_artifacts() -> list[ArtifactEvidence]:
    return [_valid_artifact("wheel"), _valid_artifact("sdist")]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_verify_passes_when_wheel_and_sdist_match_canonical_version():
    """AC-FR1600-01: wheel+sdist both reach installed_runtime_verified + match."""
    verifier = ArtifactVerifier(canonical_version="0.14.0")
    report = verifier.verify("cand-1", _valid_artifacts())
    assert isinstance(report, VerificationReport)
    assert report.status == "pass"
    assert report.candidate_id == "cand-1"


@pytest.mark.real_module
def test_verify_rejects_missing_wheel():
    """AC-FR1600-01: missing wheel -> BLD_ARTIFACT_MISSING."""
    verifier = ArtifactVerifier(canonical_version="0.14.0")
    with pytest.raises(ArtifactVerificationError) as exc:
        verifier.verify("cand-1", [_valid_artifact("sdist")])
    assert exc.value.code == "BLD_ARTIFACT_MISSING"


@pytest.mark.real_module
def test_verify_rejects_missing_sdist():
    """AC-FR1600-01: missing sdist -> BLD_ARTIFACT_MISSING."""
    verifier = ArtifactVerifier(canonical_version="0.14.0")
    with pytest.raises(ArtifactVerificationError) as exc:
        verifier.verify("cand-1", [_valid_artifact("wheel")])
    assert exc.value.code == "BLD_ARTIFACT_MISSING"


@pytest.mark.real_module
def test_verify_rejects_extra_artifact_kind():
    """AC-FR1600-01: undeclared artifact kind -> BLD_ARTIFACT_EXTRA."""
    verifier = ArtifactVerifier(canonical_version="0.14.0")
    artifacts = _valid_artifacts() + [
        ArtifactEvidence(
            artifact_id="art-deb",
            kind="debian-package",  # undeclared
            path="dist/louke.deb",
            digest="sha256:deb",
            size=2048,
            stage="installed_runtime_verified",
            extracted_version="0.14.0",
            install_environment="clean-venv",
            runtime_version="0.14.0",
        )
    ]
    with pytest.raises(ArtifactVerificationError) as exc:
        verifier.verify("cand-1", artifacts)
    assert exc.value.code == "BLD_ARTIFACT_EXTRA"


@pytest.mark.real_module
def test_verify_rejects_artifact_not_at_final_stage():
    """AC-FR1600-01: artifact not at installed_runtime_verified -> BLD_ARTIFACT_CORRUPT."""
    verifier = ArtifactVerifier(canonical_version="0.14.0")
    artifacts = _valid_artifacts()
    artifacts[0] = ArtifactEvidence(
        artifact_id=artifacts[0].artifact_id,
        kind=artifacts[0].kind,
        path=artifacts[0].path,
        digest=artifacts[0].digest,
        size=artifacts[0].size,
        stage="built",  # not yet verified
        extracted_version="0.14.0",
        install_environment="clean-venv",
        runtime_version="0.14.0",
    )
    with pytest.raises(ArtifactVerificationError) as exc:
        verifier.verify("cand-1", artifacts)
    assert exc.value.code == "BLD_ARTIFACT_CORRUPT"


@pytest.mark.real_module
def test_verify_rejects_unextractable_version():
    """AC-FR1600-01: empty extracted_version -> BLD_VERSION_UNEXTRACTABLE."""
    verifier = ArtifactVerifier(canonical_version="0.14.0")
    artifacts = _valid_artifacts()
    artifacts[0] = ArtifactEvidence(
        artifact_id=artifacts[0].artifact_id,
        kind=artifacts[0].kind,
        path=artifacts[0].path,
        digest=artifacts[0].digest,
        size=artifacts[0].size,
        stage="installed_runtime_verified",
        extracted_version="",  # cannot extract
        install_environment="clean-venv",
        runtime_version="0.14.0",
    )
    with pytest.raises(ArtifactVerificationError) as exc:
        verifier.verify("cand-1", artifacts)
    assert exc.value.code == "BLD_VERSION_UNEXTRACTABLE"


@pytest.mark.real_module
def test_verify_rejects_artifact_version_mismatch():
    """AC-FR1600-01: extracted version != canonical -> BLD_VERSION_MISMATCH;
    branch/tag/source declarations cannot substitute."""
    verifier = ArtifactVerifier(canonical_version="0.14.0")
    artifacts = _valid_artifacts()
    artifacts[0] = ArtifactEvidence(
        artifact_id=artifacts[0].artifact_id,
        kind=artifacts[0].kind,
        path=artifacts[0].path,
        digest=artifacts[0].digest,
        size=artifacts[0].size,
        stage="installed_runtime_verified",
        extracted_version="0.13.0",  # wrong version
        install_environment="clean-venv",
        runtime_version="0.14.0",
    )
    with pytest.raises(ArtifactVerificationError) as exc:
        verifier.verify("cand-1", artifacts)
    assert exc.value.code == "BLD_VERSION_MISMATCH"


@pytest.mark.real_module
def test_verify_rejects_runtime_outlet_mismatch():
    """AC-FR1600-01: installed/runtime version != canonical -> BLD_OUTLET_MISMATCH."""
    verifier = ArtifactVerifier(canonical_version="0.14.0")
    artifacts = _valid_artifacts()
    artifacts[0] = ArtifactEvidence(
        artifact_id=artifacts[0].artifact_id,
        kind=artifacts[0].kind,
        path=artifacts[0].path,
        digest=artifacts[0].digest,
        size=artifacts[0].size,
        stage="installed_runtime_verified",
        extracted_version="0.14.0",
        install_environment="clean-venv",
        runtime_version="0.13.0",  # stale outlet
    )
    with pytest.raises(ArtifactVerificationError) as exc:
        verifier.verify("cand-1", artifacts)
    assert exc.value.code == "BLD_OUTLET_MISMATCH"


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-FR1600-01: ERROR_CODES includes all codes from interfaces.md §10."""
    expected = {
        "BLD_RELEASE_IDENTITY_INVALID",
        "BLD_CONTRACT_NOT_CURRENT",
        "BLD_ADAPTER_FAILED",
        "BLD_SOURCE_MISSING",
        "BLD_SOURCE_VERSION_MISMATCH",
        "BLD_COMMAND_FAILED",
        "BLD_ARTIFACT_MISSING",
        "BLD_ARTIFACT_EXTRA",
        "BLD_ARTIFACT_CORRUPT",
        "BLD_VERSION_UNEXTRACTABLE",
        "BLD_VERSION_MISMATCH",
        "BLD_PAYLOAD_MISSING",
        "BLD_INSTALL_FAILED",
        "BLD_OUTLET_MISMATCH",
        "BLD_RESULT_UNKNOWN",
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
