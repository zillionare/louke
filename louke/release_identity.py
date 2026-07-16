"""Pure release tag and artifact version identity verification."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReleaseIdentityResult:
    """Result returned by :func:`verify_release_identity`."""

    passed: bool
    normalized_tag: str | None
    artifact_version: str | None
    diagnostic: str


def verify_release_identity(
    tag: str | None, artifact_version: str | None
) -> ReleaseIdentityResult:
    """Compare a release tag with an already-extracted artifact version.

    Args:
        tag: Git tag text, optionally with one leading ``v``.
        artifact_version: Version extracted by the host project's adapter.

    Returns:
        A side-effect-free result containing normalized values and a diagnostic.

    Raises:
        No exceptions are raised for invalid input; invalid identity is a failed
        result so callers can report it through their own release interface.
    """
    normalized = tag[1:] if tag and tag.startswith("v") else tag
    if not normalized:
        return _failure(normalized, artifact_version, "missing tag")
    if not artifact_version:
        return _failure(normalized, artifact_version, "missing artifact version")
    if "-dirty" in normalized or "+local" in normalized:
        return _failure(
            normalized, artifact_version, f"invalid dirty/local tag: {normalized}"
        )
    if normalized != artifact_version:
        return _failure(
            normalized,
            artifact_version,
            f"version mismatch: tag {normalized} != artifact {artifact_version}",
        )
    return ReleaseIdentityResult(
        True,
        normalized,
        artifact_version,
        f"release identity matches: {normalized}",
    )


def _failure(
    normalized_tag: str | None,
    artifact_version: str | None,
    diagnostic: str,
) -> ReleaseIdentityResult:
    """Build the consistent failed-result shape used by validation branches."""
    return ReleaseIdentityResult(False, normalized_tag, artifact_version, diagnostic)
