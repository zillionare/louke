"""AC-FR1600-01: Version, build, artifact & public version verification.

For every declared artifact, evidence must show version source prepared,
artifact built, digest/version extracted+matched, applicable installed/
runtime version matched, all bound to candidate/canonical identity.
Injected artifact missing, unextractable, version mismatch or stale public
outlet must FAIL the candidate gate; branch/tag/source declarations may
NOT substitute for artifact/install verification.
"""

from __future__ import annotations


import pytest

from louke.v014.fr1600_artifact_version import (
    ArtifactEvidence,
    ArtifactVerificationError,
    ArtifactVerifier,
    Stage,
)

_CAND = "cand:abc"
_VERSION = "0.14.0"


def _evidence(
    *,
    artifact_id: str = "wheel:abc",
    kind: str = "wheel",
    path: str = "dist/louke-0.14.0-py3-none-any.whl",
    stage: Stage = "installed_runtime_verified",
    extracted_version: str = _VERSION,
    runtime_version: str = _VERSION,
    digest: str = "sha256:" + "a" * 64,
    install_environment: str = "venv:py-3.12",
) -> ArtifactEvidence:
    return ArtifactEvidence(
        artifact_id=artifact_id,
        kind=kind,
        path=path,
        digest=digest,
        size=1024,
        stage=stage,
        extracted_version=extracted_version,
        install_environment=install_environment,
        runtime_version=runtime_version,
    )


def test_verifier_passes_when_all_artifacts_verified() -> None:
    """AC-FR1600-01: all four stages current PASS with version match."""
    v = ArtifactVerifier(canonical_version=_VERSION)
    wheel = _evidence(artifact_id="wheel:abc")
    sdist = _evidence(
        artifact_id="sdist:abc",
        kind="sdist",
        path="dist/louke-0.14.0.tar.gz",
    )
    report = v.verify(_CAND, artifacts=[wheel, sdist])
    assert report.status == "pass"
    assert len(report.failed) == 0


def test_verifier_fails_when_artifact_missing() -> None:
    """AC-FR1600-01: missing required artifact fails the gate."""
    v = ArtifactVerifier(canonical_version=_VERSION)
    with pytest.raises(ArtifactVerificationError) as exc:
        v.verify(_CAND, artifacts=[_evidence(artifact_id="wheel:abc")])  # sdist missing
    assert exc.value.code == "BLD_ARTIFACT_MISSING"


def test_verifier_fails_when_extra_artifact() -> None:
    """AC-FR1600-01: undeclared extra artifact fails the gate."""
    v = ArtifactVerifier(canonical_version=_VERSION)
    extra = _evidence(artifact_id="extra:abc", kind="binary", path="dist/extra.bin")
    with pytest.raises(ArtifactVerificationError) as exc:
        v.verify(
            _CAND,
            artifacts=[
                _evidence(artifact_id="wheel:abc"),
                _evidence(
                    artifact_id="sdist:abc",
                    kind="sdist",
                    path="dist/louke-0.14.0.tar.gz",
                ),
                extra,
            ],
        )
    assert exc.value.code == "BLD_ARTIFACT_EXTRA"


def test_verifier_fails_when_version_unextractable() -> None:
    """AC-FR1600-01: version cannot be extracted -> FAIL."""
    v = ArtifactVerifier(canonical_version=_VERSION)
    bad = _evidence(extracted_version="")
    with pytest.raises(ArtifactVerificationError) as exc:
        v.verify(
            _CAND,
            artifacts=[
                bad,
                _evidence(
                    artifact_id="sdist:abc",
                    kind="sdist",
                    path="dist/louke-0.14.0.tar.gz",
                ),
            ],
        )
    assert exc.value.code == "BLD_VERSION_UNEXTRACTABLE"


def test_verifier_fails_when_extracted_version_mismatches_canonical() -> None:
    """AC-FR1600-01: extracted version != canonical identity -> FAIL."""
    v = ArtifactVerifier(canonical_version=_VERSION)
    bad = _evidence(extracted_version="0.13.0")
    with pytest.raises(ArtifactVerificationError) as exc:
        v.verify(
            _CAND,
            artifacts=[
                bad,
                _evidence(
                    artifact_id="sdist:abc",
                    kind="sdist",
                    path="dist/louke-0.14.0.tar.gz",
                ),
            ],
        )
    assert exc.value.code == "BLD_VERSION_MISMATCH"


def test_verifier_fails_when_runtime_version_mismatches() -> None:
    """AC-FR1600-01: installed/runtime version mismatch -> FAIL."""
    v = ArtifactVerifier(canonical_version=_VERSION)
    bad = _evidence(runtime_version="0.13.0")
    with pytest.raises(ArtifactVerificationError) as exc:
        v.verify(
            _CAND,
            artifacts=[
                bad,
                _evidence(
                    artifact_id="sdist:abc",
                    kind="sdist",
                    path="dist/louke-0.14.0.tar.gz",
                ),
            ],
        )
    assert exc.value.code == "BLD_OUTLET_MISMATCH"


def test_verifier_fails_when_stage_not_final() -> None:
    """AC-FR1600-01: every artifact must reach installed_runtime_verified stage."""
    v = ArtifactVerifier(canonical_version=_VERSION)
    bad = _evidence(stage="built")
    with pytest.raises(ArtifactVerificationError) as exc:
        v.verify(
            _CAND,
            artifacts=[
                bad,
                _evidence(
                    artifact_id="sdist:abc",
                    kind="sdist",
                    path="dist/louke-0.14.0.tar.gz",
                ),
            ],
        )
    assert exc.value.code == "BLD_ARTIFACT_CORRUPT"


def test_verifier_rejects_branch_tag_as_substitute() -> None:
    """AC-FR1600-01: branch/tag/source declarations cannot substitute for artifact/install."""
    v = ArtifactVerifier(canonical_version=_VERSION)
    # Provide only source prepared stage with no built artifact.
    src_only = _evidence(stage="source_prepared")
    with pytest.raises(ArtifactVerificationError) as exc:
        v.verify(
            _CAND,
            artifacts=[
                src_only,
                _evidence(
                    artifact_id="sdist:abc",
                    kind="sdist",
                    path="dist/louke-0.14.0.tar.gz",
                    stage="source_prepared",
                ),
            ],
        )
    assert exc.value.code == "BLD_ARTIFACT_CORRUPT"
