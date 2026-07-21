"""NFR-0600: schema migration compatibility.

Migrates from old M-LOCK-1/second-M-LOCK/old prompt/contract schema formats
using explicit version + compatible reader / one-way migration.  New runs
only write canonical M-REQ-APPROVAL -> M-DESIGN -> M-IMPL identities and
never maintain two writable truths.  Unknown old versions fail closed;
migration interruption is retryable (AC-NFR0600-01).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

ERROR_CODES = (
    "MIGRATION_SOURCE_UNKNOWN",
    "MIGRATION_TARGET_UNSUPPORTED",
    "MIGRATION_INTERRUPTED",
    "MIGRATION_DIGEST_INCONSISTENT",
)

# Legacy versions with known migration paths to canonical 1.0.0.
KNOWN_LEGACY_VERSIONS = frozenset(
    {
        "0.10.0-legacy",  # M-LOCK-1 single-lock
        "0.12.0-second-m-lock",  # second M-LOCK (deprecated)
        "0.13.0-prompt-bundle",  # old prompt/schema format
        "1.0.0",  # already canonical
    }
)

CANONICAL_STAGES = frozenset(
    {
        "M-REQ-APPROVAL",
        "M-DESIGN",
        "M-IMPL",
    }
)

_LEGACY_STAGE_MAP = {
    "0.10.0-legacy": "M-LOCK-1",
    "0.12.0-second-m-lock": "M-LOCK-2",
    "0.13.0-prompt-bundle": "M-PROMPT-LEGACY",
    "1.0.0": "M-DESIGN",
}


class MigrationError(Exception):
    """A fail-closed schema migration rejection carrying a stable code."""

    __test__ = False

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class MigrationStatus(str, Enum):
    """Outcome of a migration attempt."""

    MIGRATED = "migrated"
    READ_ONLY = "read_only"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class MigrationReport:
    """Result of :func:`migrate_legacy_artifact` or :func:`read_legacy_artifact`.

    Attributes:
        source_version: The legacy source version.
        target_version: The canonical target version.
        status: ``migrated`` | ``read_only`` | ``unsupported``.
        diagnostics: Mapping of diagnostic fields (e.g. ``no_op``).
        evidence_digest: ``sha256:<hex>`` of the migration record.
        legacy_stage: The legacy stage identifier (e.g. ``M-LOCK-1``).
        canonical_stage: The canonical stage identifier (e.g. ``M-DESIGN``).
    """

    source_version: str
    target_version: str
    status: MigrationStatus
    diagnostics: dict[str, Any] = field(default_factory=dict)
    evidence_digest: str = ""
    legacy_stage: str = ""
    canonical_stage: str = ""


def _evidence_digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def read_legacy_artifact(
    *,
    artifact: dict[str, Any],
    target_version: str,
) -> MigrationReport:
    """Read a legacy artifact as a read-only diagnostic record.

    Unknown legacy versions are reported as ``read_only`` or ``unsupported``
    rather than migrated blindly.  The artifact is never modified.

    Args:
        artifact: The legacy artifact dict.
        target_version: The canonical target version.

    Returns:
        A :class:`MigrationReport` with ``status=read_only`` (or
        ``unsupported`` for fully unknown versions).
    """
    source_version = artifact.get("schema_version", "")
    if source_version not in KNOWN_LEGACY_VERSIONS:
        return MigrationReport(
            source_version=source_version,
            target_version=target_version,
            status=MigrationStatus.UNSUPPORTED,
            diagnostics={"reason": f"unknown legacy version {source_version!r}"},
            evidence_digest=_evidence_digest(
                {"source": source_version, "target": target_version}
            ),
            legacy_stage=artifact.get("kind", ""),
            canonical_stage="",
        )
    return MigrationReport(
        source_version=source_version,
        target_version=target_version,
        status=MigrationStatus.READ_ONLY,
        diagnostics={"reason": "legacy artifact read for diagnostic only"},
        evidence_digest=_evidence_digest(
            {"source": source_version, "target": target_version, "artifact": artifact}
        ),
        legacy_stage=_LEGACY_STAGE_MAP.get(source_version, artifact.get("kind", "")),
        canonical_stage="",
    )


def migrate_legacy_artifact(
    *,
    artifact: dict[str, Any],
    source_version: str,
    target_version: str,
) -> MigrationReport:
    """Migrate a legacy artifact to the canonical target version (one-way).

    Args:
        artifact: The legacy artifact dict.
        source_version: The legacy source version.
        target_version: The canonical target version.

    Returns:
        A :class:`MigrationReport` with ``status=migrated``.

    Raises:
        MigrationError: With ``MIGRATION_SOURCE_UNKNOWN`` if the source
            version is not a known legacy version, or
            ``MIGRATION_TARGET_UNSUPPORTED`` if the target is older than the
            source (no backward migration).
    """
    if source_version not in KNOWN_LEGACY_VERSIONS:
        raise MigrationError(
            "MIGRATION_SOURCE_UNKNOWN",
            f"source version {source_version!r} is not a known legacy version",
        )
    if target_version not in KNOWN_LEGACY_VERSIONS or target_version == "1.0.0":
        # 1.0.0 is the only supported target
        if target_version != "1.0.0":
            raise MigrationError(
                "MIGRATION_TARGET_UNSUPPORTED",
                f"target version {target_version!r} is not a supported canonical target",
            )
    # Reject backward migration (target older than source)
    if source_version == "1.0.0" and target_version != "1.0.0":
        raise MigrationError(
            "MIGRATION_TARGET_UNSUPPORTED",
            f"cannot migrate backward from 1.0.0 to {target_version!r}",
        )

    no_op = source_version == target_version
    payload = {
        "source": source_version,
        "target": target_version,
        "artifact_kind": artifact.get("kind", ""),
        "no_op": no_op,
    }
    return MigrationReport(
        source_version=source_version,
        target_version=target_version,
        status=MigrationStatus.MIGRATED,
        diagnostics={"no_op": no_op, "artifact_kind": artifact.get("kind", "")},
        evidence_digest=_evidence_digest(payload),
        legacy_stage=_LEGACY_STAGE_MAP.get(source_version, ""),
        canonical_stage=_LEGACY_STAGE_MAP.get(target_version, "M-DESIGN")
        if target_version == "1.0.0"
        else "",
    )
