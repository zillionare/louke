"""AC-NFR0600-01: State & evidence migration compatibility.

Old Maestro/Agent-driven runs, old stage identities, historical evidence
without RGR refs, and old prompt/schema bundles must be displayable
read-only or migrated via explicit migration.  New runs only write
canonical Runtime-owned stages + evidence; no dual-write state authority.
Migration is idempotent: retry does not produce dual current state, dual
commit authority, or repeated external operations.
"""

from __future__ import annotations


from louke.v014.nfr0600_migration_compat import (
    LegacyRun,
    MigrationDecision,
    MigrationStore,
    migrate_legacy_run,
)

_LEGACY_RUN_ID = "legacy-run-1"
_SOURCE_REVISION = "legacy-schema-v0.13"
_TARGET_SCHEMA = "canonical-runtime-v0.14"


def _legacy(
    *,
    has_red_ref: bool = True,
    has_program_pass: bool = False,
    has_publish_fact: bool = False,
) -> LegacyRun:
    return LegacyRun(
        run_id=_LEGACY_RUN_ID,
        source_revision=_SOURCE_REVISION,
        stage_ids=("M-DESIGN", "M-IMPL", "M-VERIFY"),
        evidence_refs=("ev-legacy-1",),
        prompt_schema_refs=("prompt-v0.13",),
        operation_refs=("op-legacy-1",) if has_publish_fact else (),
        has_private_red_ref=has_red_ref,
        has_program_pass=has_program_pass,
        has_publish_fact=has_publish_fact,
    )


def test_migrate_legacy_run_returns_migrated_when_source_verifiable() -> None:
    """AC-NFR0600-01: verifiable legacy run with unchanged source revision migrates."""
    store = MigrationStore()
    decision = migrate_legacy_run(
        store=store,
        legacy=_legacy(),
        target_schema=_TARGET_SCHEMA,
        expected_source_revision=_SOURCE_REVISION,
    )
    assert isinstance(decision, MigrationDecision)
    assert decision.mode == "migrated"
    assert decision.target_run_id.startswith("canonical-run")


def test_migrate_legacy_run_read_only_when_source_revision_changed() -> None:
    """AC-NFR0600-01: source revision conflict -> read-only."""
    store = MigrationStore()
    decision = migrate_legacy_run(
        store=store,
        legacy=_legacy(),
        target_schema=_TARGET_SCHEMA,
        expected_source_revision="other-revision",
    )
    assert decision.mode == "read_only"


def test_migrate_legacy_run_records_lineage_unavailable_when_no_red_ref() -> None:
    """AC-NFR0600-01: missing private Red ref -> lineage_unavailable diagnostic."""
    store = MigrationStore()
    decision = migrate_legacy_run(
        store=store,
        legacy=_legacy(has_red_ref=False),
        target_schema=_TARGET_SCHEMA,
        expected_source_revision=_SOURCE_REVISION,
    )
    assert "lineage_unavailable" in decision.diagnostics


def test_migrate_legacy_run_records_legacy_unverified_when_no_program_pass() -> None:
    """AC-NFR0600-01: legacy PASS without program evidence -> legacy_unverified."""
    store = MigrationStore()
    decision = migrate_legacy_run(
        store=store,
        legacy=_legacy(has_program_pass=False),
        target_schema=_TARGET_SCHEMA,
        expected_source_revision=_SOURCE_REVISION,
    )
    assert "legacy_unverified" in decision.diagnostics


def test_migrate_legacy_run_needs_attention_for_publish_fact_without_identity() -> None:
    """AC-NFR0600-01: legacy publish fact with insufficient identity -> needs_attention."""
    store = MigrationStore()
    decision = migrate_legacy_run(
        store=store,
        legacy=_legacy(has_publish_fact=True),
        target_schema=_TARGET_SCHEMA,
        expected_source_revision=_SOURCE_REVISION,
    )
    # If publish fact has insufficient provider identity, migration enters needs_attention.
    assert "publish_needs_attention" in decision.diagnostics


def test_migration_idempotent_retry_returns_same_result() -> None:
    """AC-NFR0600-01: repeating the same migration returns the same mapping."""
    store = MigrationStore()
    legacy = _legacy()
    d1 = migrate_legacy_run(
        store=store,
        legacy=legacy,
        target_schema=_TARGET_SCHEMA,
        expected_source_revision=_SOURCE_REVISION,
    )
    d2 = migrate_legacy_run(
        store=store,
        legacy=legacy,
        target_schema=_TARGET_SCHEMA,
        expected_source_revision=_SOURCE_REVISION,
    )
    assert d1.target_run_id == d2.target_run_id
    assert d1.mode == d2.mode


def test_migration_rejects_dual_state_authority() -> None:
    """AC-NFR0600-01: migration must NOT produce dual current state authority."""
    store = MigrationStore()
    legacy = _legacy()
    d1 = migrate_legacy_run(
        store=store,
        legacy=legacy,
        target_schema=_TARGET_SCHEMA,
        expected_source_revision=_SOURCE_REVISION,
    )
    # A second migration attempt for the same source returns the same target
    # (no second canonical run created).
    d2 = migrate_legacy_run(
        store=store,
        legacy=legacy,
        target_schema=_TARGET_SCHEMA,
        expected_source_revision=_SOURCE_REVISION,
    )
    assert d1.target_run_id == d2.target_run_id


def test_migration_rejects_target_schema_downgrade() -> None:
    """AC-NFR0600-01: older target schema than source -> read-only rejection."""
    store = MigrationStore()
    decision = migrate_legacy_run(
        store=store,
        legacy=_legacy(),
        target_schema="canonical-runtime-v0.13",  # older than source
        expected_source_revision=_SOURCE_REVISION,
    )
    assert decision.mode == "read_only"


def test_migration_rejects_unknown_legacy_stage() -> None:
    """AC-NFR0600-01: unknown legacy stage id is recorded as diagnostic, not silently dropped."""
    store = MigrationStore()
    legacy = _legacy()
    legacy = LegacyRun(
        run_id=legacy.run_id,
        source_revision=legacy.source_revision,
        stage_ids=("M-DESIGN", "M-UNKNOWN-STAGE"),
        evidence_refs=legacy.evidence_refs,
        prompt_schema_refs=legacy.prompt_schema_refs,
        operation_refs=legacy.operation_refs,
        has_private_red_ref=legacy.has_private_red_ref,
        has_program_pass=legacy.has_program_pass,
        has_publish_fact=legacy.has_publish_fact,
    )
    decision = migrate_legacy_run(
        store=store,
        legacy=legacy,
        target_schema=_TARGET_SCHEMA,
        expected_source_revision=_SOURCE_REVISION,
    )
    assert "unknown_stage:M-UNKNOWN-STAGE" in decision.diagnostics
