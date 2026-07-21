"""IF-REL-01 release-version adapter contract verification (FR-1400).

The release-version machine contract maps the Human canonical version to a
release branch, tag and host project version source.  This module verifies
the contract's canonical->branch/tag mapping, prefix normalization, version
source resolution, adapter identity, and failure policy (fail-closed with
explicit reasons).  It does not execute the adapter - that lives in
``tools/louke_python_release_adapter.py`` per AC-FR1400-01.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ERROR_CODES = (
    "RELEASE_VERSION_INVALID",
    "RELEASE_VERSION_MISMATCH",
    "RELEASE_VERSION_SOURCE_MISSING",
    "RELEASE_VERSION_ADAPTER_UNKNOWN",
)


class ReleaseVersionError(Exception):
    """A fail-closed release-version contract rejection carrying a stable code."""

    __test__ = False

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def load_contract(contract_path: Path) -> dict[str, Any]:
    """Load a release-version contract instance from ``contract_path``."""
    return json.loads(Path(contract_path).read_bytes())


def _is_pep440(version: str) -> bool:
    """Return ``True`` if ``version`` is a (loose) PEP 440 version string."""
    if not version:
        return False
    # Loose PEP 440 check: starts with digits and has no spaces.
    if any(c.isspace() for c in version):
        return False
    if not version[0].isdigit():
        return False
    return True


def normalise_external_version(external_version: str) -> str:
    """Strip the leading ``v`` prefix and verify PEP 440 form.

    Args:
        external_version: The Human-provided external version (e.g. ``v0.14.0``).

    Returns:
        The canonical version (e.g. ``0.14.0``).

    Raises:
        ReleaseVersionError: With ``RELEASE_VERSION_INVALID`` if the version
            is not a valid PEP 440 string after prefix stripping.
    """
    if not external_version:
        raise ReleaseVersionError(
            "RELEASE_VERSION_INVALID",
            "external version is empty",
        )
    canonical = (
        external_version[1:] if external_version.startswith("v") else external_version
    )
    if not _is_pep440(canonical):
        raise ReleaseVersionError(
            "RELEASE_VERSION_INVALID",
            f"version {external_version!r} is not PEP 440",
        )
    return canonical


def canonical_to_branch(canonical_version: str) -> str:
    """Return the release branch name for ``canonical_version`` (e.g. ``0.14.0`` -> ``releases/0.14.0``)."""
    return f"releases/{canonical_version}"


def canonical_to_tag(canonical_version: str) -> str:
    """Return the release tag name for ``canonical_version`` (e.g. ``0.14.0`` -> ``v0.14.0``)."""
    return f"v{canonical_version}"


def resolve_version_source(contract: dict[str, Any]) -> dict[str, str]:
    """Return the declared version source path and selector."""
    payload = contract.get("payload", {})
    source = payload.get("version_source", {})
    if not source.get("path") or not source.get("selector"):
        raise ReleaseVersionError(
            "RELEASE_VERSION_SOURCE_MISSING",
            "contract does not declare version_source.path/selector",
        )
    return {"path": source["path"], "selector": source["selector"]}


def verify_canonical_mapping(
    contract: dict[str, Any],
    *,
    canonical_version: str,
    branch: str,
    tag: str,
) -> None:
    """Verify that the canonical->branch/tag mapping is consistent.

    Args:
        contract: The release-version contract instance.
        canonical_version: The canonical version (e.g. ``0.14.0``).
        branch: The release branch name.
        tag: The release tag name.

    Raises:
        ReleaseVersionError: With ``RELEASE_VERSION_INVALID`` if the canonical
            version is empty, ``RELEASE_VERSION_MISMATCH`` if branch or tag
            do not match the canonical version.
    """
    if not canonical_version:
        raise ReleaseVersionError(
            "RELEASE_VERSION_INVALID",
            "canonical_version is empty; tag/branch alone cannot prove version source",
        )
    expected_branch = canonical_to_branch(canonical_version)
    expected_tag = canonical_to_tag(canonical_version)
    if branch != expected_branch:
        raise ReleaseVersionError(
            "RELEASE_VERSION_MISMATCH",
            f"branch {branch!r} != expected {expected_branch!r}",
        )
    if tag != expected_tag:
        raise ReleaseVersionError(
            "RELEASE_VERSION_MISMATCH",
            f"tag {tag!r} != expected {expected_tag!r}",
        )


def verify_adapter_identity(contract: dict[str, Any], *, expected_adapter: str) -> None:
    """Verify the contract declares the expected adapter path."""
    payload = contract.get("payload", {})
    if payload.get("adapter") != expected_adapter:
        raise ReleaseVersionError(
            "RELEASE_VERSION_ADAPTER_UNKNOWN",
            f"adapter {payload.get('adapter')!r} != expected {expected_adapter!r}",
        )
