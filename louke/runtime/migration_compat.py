"""NFR-0600: State & evidence migration compatibility.

Old Maestro/Agent-driven runs, old stage identities, historical evidence
without RGR refs, and old prompt/schema bundles must be displayable
read-only or migrated via explicit migration.  New runs only write
canonical Runtime-owned stages + evidence; no dual-write state authority.
Migration is idempotent: retry does not produce dual current state, dual
commit authority, or repeated external operations (AC-NFR0600-01).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

ERROR_CODES = (
    "MIG_SOURCE_NOT_FOUND",
    "MIG_SOURCE_REVISION_CONFLICT",
    "MIG_SOURCE_DIGEST_MISMATCH",
    "MIG_SCHEMA_UNSUPPORTED",
    "MIG_TARGET_OLDER",
    "MIG_IDENTITY_AMBIGUOUS",
    "MIG_INTEGRITY_FAILED",
    "MIG_CURRENT_AUTHORITY_CONFLICT",
    "MIG_OPERATION_IDENTITY_MISSING",
    "MIG_DUAL_WRITE_DETECTED",
    "MIG_INTERRUPTED",
)


class MigrationError(Exception):
    """A fail-closed migration rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class LegacyRun:
    """A legacy run to be migrated or displayed read-only (AC-NFR0600-01).

    Attributes:
        run_id: Legacy run id.
        source_revision: Legacy schema/source revision.
        stage_ids: Tuple of legacy stage ids.
        evidence_refs: Tuple of legacy evidence ids.
        prompt_schema_refs: Tuple of legacy prompt/schema refs.
        operation_refs: Tuple of legacy publish operation refs.
        has_private_red_ref: ``True`` if a private Red ref is present.
        has_program_pass: ``True`` if a legacy program PASS exists.
        has_publish_fact: ``True`` if a publish fact exists.
    """

    run_id: str
    source_revision: str
    stage_ids: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    prompt_schema_refs: tuple[str, ...]
    operation_refs: tuple[str, ...]
    has_private_red_ref: bool
    has_program_pass: bool
    has_publish_fact: bool


_CANONICAL_STAGES: frozenset[str] = frozenset(
    {
        "M-DESIGN",
        "M-IMPL",
        "M-TEST",
        "M-VERIFY",
        "M-SECURITY",
        "M-RELEASE",
        "M-PUBLISH",
        "M-MILESTONE",
    }
)


@dataclass(frozen=True)
class MigrationDecision:
    """Result of :func:`migrate_legacy_run` (AC-NFR0600-01).

    Attributes:
        mode: ``migrated|read_only``.
        target_run_id: Canonical target run id (or empty for read_only).
        source_run_id: Legacy source run id.
        diagnostics: Tuple of diagnostic codes (e.g. ``lineage_unavailable``,
            ``legacy_unverified``, ``publish_needs_attention``,
            ``unknown_stage:<id>``).
    """

    mode: str
    target_run_id: str
    source_run_id: str
    diagnostics: tuple[str, ...] = ()


class MigrationStore:
    """In-memory migration mapping store (AC-NFR0600-01)."""

    def __init__(self) -> None:
        self._mappings: dict[str, MigrationDecision] = {}

    def has_mapping(self, source_run_id: str) -> bool:
        return source_run_id in self._mappings

    def get_mapping(self, source_run_id: str) -> MigrationDecision | None:
        return self._mappings.get(source_run_id)

    def record_mapping(self, decision: MigrationDecision) -> None:
        self._mappings[decision.source_run_id] = decision


def _target_schema_is_newer(target: str, source: str) -> bool:
    """Return ``True`` if ``target`` schema is newer than ``source``."""

    # Simple lexical comparison on the trailing version.
    def extract(s: str) -> tuple[int, int]:
        # Format: "canonical-runtime-v0.14" or "legacy-schema-v0.13"
        parts = s.rsplit("v", 1)
        if len(parts) != 2:
            return (0, 0)
        try:
            major, minor = parts[1].split(".")
            return (int(major), int(minor))
        except (ValueError, AttributeError):
            return (0, 0)

    return extract(target) > extract(source)


def migrate_legacy_run(
    *,
    store: MigrationStore,
    legacy: LegacyRun,
    target_schema: str,
    expected_source_revision: str,
) -> MigrationDecision:
    """Migrate a legacy run to the canonical Runtime schema (AC-NFR0600-01).

    Args:
        store: :class:`MigrationStore` for idempotency tracking.
        legacy: :class:`LegacyRun` to migrate.
        target_schema: Target canonical schema id.
        expected_source_revision: Expected source revision; mismatch -> read_only.

    Returns:
        A :class:`MigrationDecision`:
        - ``migrated`` with a target_run_id if source revision matches AND
          target schema is newer.
        - ``read_only`` otherwise.
        Diagnostics record missing program PASS, missing Red ref, publish
        facts with insufficient identity, and unknown legacy stages.
    """
    # Idempotency: if already migrated, return the same decision.
    existing = store.get_mapping(legacy.run_id)
    if existing is not None:
        return existing

    diagnostics: list[str] = []
    if legacy.source_revision != expected_source_revision:
        decision = MigrationDecision(
            mode="read_only",
            target_run_id="",
            source_run_id=legacy.run_id,
            diagnostics=("source_revision_conflict",),
        )
        store.record_mapping(decision)
        return decision
    if not _target_schema_is_newer(target_schema, legacy.source_revision):
        decision = MigrationDecision(
            mode="read_only",
            target_run_id="",
            source_run_id=legacy.run_id,
            diagnostics=("target_schema_older",),
        )
        store.record_mapping(decision)
        return decision
    if not legacy.has_private_red_ref:
        diagnostics.append("lineage_unavailable")
    if not legacy.has_program_pass:
        diagnostics.append("legacy_unverified")
    if legacy.has_publish_fact:
        # Legacy publish facts typically lack sufficient provider identity
        # for safe resume; record diagnostic and avoid re-creating operations.
        diagnostics.append("publish_needs_attention")
    for stage in legacy.stage_ids:
        if stage not in _CANONICAL_STAGES:
            diagnostics.append(f"unknown_stage:{stage}")
    target_run_id = (
        "canonical-run:" + hashlib.sha256(legacy.run_id.encode()).hexdigest()[:12]
    )
    decision = MigrationDecision(
        mode="migrated",
        target_run_id=target_run_id,
        source_run_id=legacy.run_id,
        diagnostics=tuple(diagnostics),
    )
    store.record_mapping(decision)
    return decision
