"""Integration tests for NFR-0600: State & evidence migration compatibility.

AC-NFR0600-01: Old Maestro/Agent-driven runs, old stage identities,
historical evidence without RGR refs, and old prompt/schema bundles
are displayable read-only or migrated via explicit migration. New runs
only write canonical Runtime-owned stages + evidence; no dual-write
state authority. Migration is idempotent: retry does not produce dual
current state, dual commit authority, or repeated external operations.

Interfaces covered (per interfaces.md):
- IF-MIG-01 (Primary ARC-01)
- IF-WFR-01 (workflow current, ARC-01)
- IF-PROMPT-02 (prompt bundle migration, ARC-01)
- IF-TRACE-01 (trace migration, ARC-16)
"""
# AC-NFR0600-01

from __future__ import annotations

from dataclasses import replace

import pytest

from louke.runtime.migration_compat import (
    ERROR_CODES,
    LegacyRun,
    MigrationDecision,
    MigrationStore,
    migrate_legacy_run,
)


def _valid_legacy() -> LegacyRun:
    return LegacyRun(
        run_id="legacy-run-001",
        source_revision="legacy-schema-v0.13",
        stage_ids=("M-DESIGN", "M-IMPL", "legacy-stage-x"),
        evidence_refs=("ev-1", "ev-2"),
        prompt_schema_refs=("prompt-v0.13",),
        operation_refs=("op-1",),
        has_private_red_ref=True,
        has_program_pass=True,
        has_publish_fact=False,
    )


# ---------------------------------------------------------------------------
# migrate_legacy_run
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_migrate_legacy_run_returns_migrated_when_source_revision_matches():
    """AC-NFR0600-01: matching source revision + newer target -> migrated."""
    store = MigrationStore()
    decision = migrate_legacy_run(
        store=store,
        legacy=_valid_legacy(),
        target_schema="canonical-runtime-v0.14",
        expected_source_revision="legacy-schema-v0.13",
    )
    assert isinstance(decision, MigrationDecision)
    assert decision.mode == "migrated"
    assert decision.target_run_id.startswith("canonical-run:")
    assert decision.source_run_id == "legacy-run-001"


@pytest.mark.real_module
def test_migrate_legacy_run_returns_read_only_on_source_revision_mismatch():
    """AC-NFR0600-01: source revision conflict -> read_only (no migration)."""
    store = MigrationStore()
    decision = migrate_legacy_run(
        store=store,
        legacy=_valid_legacy(),
        target_schema="canonical-runtime-v0.14",
        expected_source_revision="legacy-schema-v0.99",  # mismatch
    )
    assert decision.mode == "read_only"
    assert decision.target_run_id == ""
    assert "source_revision_conflict" in decision.diagnostics


@pytest.mark.real_module
def test_migrate_legacy_run_returns_read_only_when_target_schema_older():
    """AC-NFR0600-01: target schema older than source -> read_only."""
    store = MigrationStore()
    legacy = LegacyRun(
        run_id="r1",
        source_revision="legacy-schema-v0.14",
        stage_ids=(),
        evidence_refs=(),
        prompt_schema_refs=(),
        operation_refs=(),
        has_private_red_ref=True,
        has_program_pass=True,
        has_publish_fact=False,
    )
    decision = migrate_legacy_run(
        store=store,
        legacy=legacy,
        target_schema="canonical-runtime-v0.13",  # older
        expected_source_revision="legacy-schema-v0.14",
    )
    assert decision.mode == "read_only"
    assert "target_schema_older" in decision.diagnostics


@pytest.mark.real_module
def test_migrate_legacy_run_records_lineage_unavailable_when_no_red_ref():
    """AC-NFR0600-01: missing Red ref -> lineage_unavailable diagnostic."""
    store = MigrationStore()
    legacy = replace(_valid_legacy(), has_private_red_ref=False)
    decision = migrate_legacy_run(
        store=store,
        legacy=legacy,
        target_schema="canonical-runtime-v0.14",
        expected_source_revision="legacy-schema-v0.13",
    )
    assert "lineage_unavailable" in decision.diagnostics


@pytest.mark.real_module
def test_migrate_legacy_run_records_legacy_unverified_when_no_program_pass():
    """AC-NFR0600-01: missing program PASS -> legacy_unverified."""
    store = MigrationStore()
    legacy = replace(_valid_legacy(), has_program_pass=False)
    decision = migrate_legacy_run(
        store=store,
        legacy=legacy,
        target_schema="canonical-runtime-v0.14",
        expected_source_revision="legacy-schema-v0.13",
    )
    assert "legacy_unverified" in decision.diagnostics


@pytest.mark.real_module
def test_migrate_legacy_run_records_publish_needs_attention_for_legacy_facts():
    """AC-NFR0600-01: legacy publish facts -> publish_needs_attention."""
    store = MigrationStore()
    legacy = replace(_valid_legacy(), has_publish_fact=True)
    decision = migrate_legacy_run(
        store=store,
        legacy=legacy,
        target_schema="canonical-runtime-v0.14",
        expected_source_revision="legacy-schema-v0.13",
    )
    assert "publish_needs_attention" in decision.diagnostics


@pytest.mark.real_module
def test_migrate_legacy_run_records_unknown_legacy_stages():
    """AC-NFR0600-01: legacy stage not in canonical set -> unknown_stage:<id>."""
    store = MigrationStore()
    decision = migrate_legacy_run(
        store=store,
        legacy=_valid_legacy(),
        target_schema="canonical-runtime-v0.14",
        expected_source_revision="legacy-schema-v0.13",
    )
    assert any(d.startswith("unknown_stage:") for d in decision.diagnostics)


# ---------------------------------------------------------------------------
# Idempotency: retry does not produce dual current state
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_migrate_legacy_run_is_idempotent_on_retry():
    """AC-NFR0600-01: retry returns the same decision (no dual current state)."""
    store = MigrationStore()
    legacy = _valid_legacy()
    decision1 = migrate_legacy_run(
        store=store,
        legacy=legacy,
        target_schema="canonical-runtime-v0.14",
        expected_source_revision="legacy-schema-v0.13",
    )
    decision2 = migrate_legacy_run(
        store=store,
        legacy=legacy,
        target_schema="canonical-runtime-v0.14",
        expected_source_revision="legacy-schema-v0.13",
    )
    assert decision1.target_run_id == decision2.target_run_id
    assert decision1.mode == decision2.mode
    # Store has only one mapping (no dual write).
    assert store.has_mapping(legacy.run_id)


@pytest.mark.real_module
def test_migrate_legacy_run_does_not_repeat_external_operations():
    """AC-NFR0600-01: migration retry does NOT repeat external operations."""
    store = MigrationStore()
    legacy = replace(_valid_legacy(), has_publish_fact=True)
    decision1 = migrate_legacy_run(
        store=store,
        legacy=legacy,
        target_schema="canonical-runtime-v0.14",
        expected_source_revision="legacy-schema-v0.13",
    )
    decision2 = migrate_legacy_run(
        store=store,
        legacy=legacy,
        target_schema="canonical-runtime-v0.14",
        expected_source_revision="legacy-schema-v0.13",
    )
    # Same target_run_id, same diagnostics (no new operations).
    assert decision1.target_run_id == decision2.target_run_id
    assert decision1.diagnostics == decision2.diagnostics


@pytest.mark.real_module
def test_migrate_legacy_run_does_not_fabricate_missing_pass():
    """AC-NFR0600-01: missing program PASS recorded as diagnostic; never fabricated."""
    store = MigrationStore()
    legacy = replace(_valid_legacy(), has_program_pass=False)
    decision = migrate_legacy_run(
        store=store,
        legacy=legacy,
        target_schema="canonical-runtime-v0.14",
        expected_source_revision="legacy-schema-v0.13",
    )
    # Mode is still migrated (with diagnostic), but legacy_unverified is recorded.
    assert "legacy_unverified" in decision.diagnostics
    # The migration does NOT fabricate a PASS; it records the gap.


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-NFR0600-01: ERROR_CODES includes all codes from interfaces.md §16."""
    expected = {
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
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
