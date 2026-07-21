"""FR-1600: Version, build, artifact & public version verification.

For every declared artifact, evidence must show version source prepared,
artifact built, digest/version extracted+matched, applicable installed/
runtime version matched, all bound to candidate/canonical identity.
Injected artifact missing, unextractable, version mismatch or stale public
outlet must FAIL the candidate gate; branch/tag/source declarations may
NOT substitute for artifact/install verification (AC-FR1600-01).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ERROR_CODES = (
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
)

Stage = Literal[
    "source_prepared",
    "built",
    "artifact_version_verified",
    "installed_runtime_verified",
]

_FINAL_STAGE: Stage = "installed_runtime_verified"

_REQUIRED_KINDS: tuple[str, ...] = ("wheel", "sdist")


class ArtifactVerificationError(Exception):
    """A fail-closed artifact verification rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ArtifactEvidence:
    """Evidence for one artifact (AC-FR1600-01).

    Attributes:
        artifact_id: Stable artifact identity.
        kind: ``wheel|sdist`` (or other host-project kind).
        path: Artifact path.
        digest: ``sha256:<hex>`` of the artifact bytes.
        size: Artifact size in bytes.
        stage: Current verification stage.
        extracted_version: Version extracted from artifact metadata.
        install_environment: Install environment identity.
        runtime_version: Version read back from runtime outlet.
    """

    artifact_id: str
    kind: str
    path: str
    digest: str
    size: int
    stage: Stage
    extracted_version: str
    install_environment: str
    runtime_version: str


@dataclass(frozen=True)
class VerificationReport:
    """Result of :meth:`ArtifactVerifier.verify` (AC-FR1600-01).

    Attributes:
        candidate_id: Bound candidate id.
        status: ``pass`` or ``fail``.
        failed: Tuple of failed artifact ids.
    """

    candidate_id: str
    status: str
    failed: tuple[str, ...] = ()


class ArtifactVerifier:
    """Verifies every declared artifact reaches the final stage (AC-FR1600-01)."""

    def __init__(self, *, canonical_version: str) -> None:
        self._canonical_version = canonical_version

    def verify(
        self,
        candidate_id: str,
        artifacts: list[ArtifactEvidence],
    ) -> VerificationReport:
        """Verify all required artifacts reach the final stage and match versions.

        Args:
            candidate_id: Bound candidate id.
            artifacts: List of :class:`ArtifactEvidence` for each artifact.

        Returns:
            A :class:`VerificationReport` with ``status=pass`` only when every
            required artifact reaches ``installed_runtime_verified`` and its
            extracted/runtime versions match the canonical version.

        Raises:
            ArtifactVerificationError: With a stable code from :data:`ERROR_CODES`
                for any missing/extra/corrupt artifact, unextractable version,
                version mismatch or runtime outlet mismatch.
        """
        # Check required kinds are present.
        kinds_present = {a.kind for a in artifacts}
        for required_kind in _REQUIRED_KINDS:
            if required_kind not in kinds_present:
                raise ArtifactVerificationError(
                    "BLD_ARTIFACT_MISSING",
                    f"required artifact kind {required_kind!r} is missing",
                )
        # Check for extras (only required kinds are allowed for Louke dogfood).
        extras = kinds_present - set(_REQUIRED_KINDS)
        if extras:
            raise ArtifactVerificationError(
                "BLD_ARTIFACT_EXTRA",
                f"undeclared artifact kinds present: {sorted(extras)}",
            )
        for artifact in artifacts:
            if artifact.stage != _FINAL_STAGE:
                raise ArtifactVerificationError(
                    "BLD_ARTIFACT_CORRUPT",
                    f"artifact {artifact.artifact_id!r} did not reach {_FINAL_STAGE}",
                )
            if not artifact.extracted_version:
                raise ArtifactVerificationError(
                    "BLD_VERSION_UNEXTRACTABLE",
                    f"artifact {artifact.artifact_id!r} has no extracted version",
                )
            if artifact.extracted_version != self._canonical_version:
                raise ArtifactVerificationError(
                    "BLD_VERSION_MISMATCH",
                    f"artifact {artifact.artifact_id!r} extracted version "
                    f"{artifact.extracted_version!r} != canonical {self._canonical_version!r}",
                )
            if artifact.runtime_version != self._canonical_version:
                raise ArtifactVerificationError(
                    "BLD_OUTLET_MISMATCH",
                    f"artifact {artifact.artifact_id!r} runtime version "
                    f"{artifact.runtime_version!r} != canonical {self._canonical_version!r}",
                )
        return VerificationReport(
            candidate_id=candidate_id,
            status="pass",
        )
