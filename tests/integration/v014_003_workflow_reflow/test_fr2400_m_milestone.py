"""Integration tests for FR-2400: M-MILESTONE trace, archive & resource
cleanup.

AC-FR2400-01: History records let every effective requirement be
bidirectionally traced through AC, plan, Issue/task, R/review, formal
commits, tests/CI, artifact/security/release; Project/WorkflowRun/
Issues state matches real publish facts. Without archived Red evidence,
refs are preserved; after archive success only manifest-listed refs are
deleted. Archive/cleanup failures keep ``closing`` idempotent retry,
no re-publish. After publish facts verified and all required archives
closed, Project/WorkflowRun shows ``complete`` and the next main
release creation is enabled, while the just-completed project remains
read-only from history; in ``closing`` or ``needs_attention`` the
next-release entry remains disabled.

Interfaces covered (per interfaces.md):
- IF-TRACE-01 (Primary ARC-16)
- IF-RGR-01 (Red ref cleanup, ARC-05)
- IF-WFR-01 (workflow state, ARC-01)
"""
# AC-FR2400-01

from __future__ import annotations

import pytest

from louke.v014.fr2400_m_milestone import (
    ERROR_CODES,
    ArchiveManifest,
    ArchiveStore,
    CleanupDecision,
    MilestoneState,
    close_milestone,
    plan_cleanup,
)


def _valid_manifest() -> ArchiveManifest:
    return ArchiveManifest(
        archive_id="archive:1",
        run_id="run-001",
        candidate_id="cand-1",
        trace_root="trace:root",
        evidence_ids=("ev-1", "ev-2"),
        red_refs=(
            ("refs/louke/rgr/run-001/T-001/att-1/red", "r" * 40),
            ("refs/louke/rgr/run-001/T-002/att-1/red", "r2" + "r" * 38),
        ),
    )


# ---------------------------------------------------------------------------
# plan_cleanup
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_plan_cleanup_success_when_ref_matches_expected_oid():
    """AC-FR2400-01: actual OID == expected -> success (will be deleted)."""
    manifest = _valid_manifest()
    existing = {
        "refs/louke/rgr/run-001/T-001/att-1/red": "r" * 40,
        "refs/louke/rgr/run-001/T-002/att-1/red": "r2" + "r" * 38,
    }
    decisions = plan_cleanup(manifest, existing_refs=existing)
    assert all(d.status == "success" for d in decisions)
    assert len(decisions) == 2


@pytest.mark.real_module
def test_plan_cleanup_idempotent_when_ref_already_absent():
    """AC-FR2400-01: ref already deleted -> idempotent-success."""
    manifest = _valid_manifest()
    decisions = plan_cleanup(manifest, existing_refs={})
    assert all(d.status == "idempotent-success" for d in decisions)
    assert all(d.actual_oid == "" for d in decisions)


@pytest.mark.real_module
def test_plan_cleanup_conflict_when_actual_oid_differs():
    """AC-FR2400-01: actual OID != expected -> conflict; ref NOT deleted."""
    manifest = _valid_manifest()
    existing = {
        "refs/louke/rgr/run-001/T-001/att-1/red": "x" * 40,  # different
    }
    decisions = plan_cleanup(manifest, existing_refs=existing)
    assert decisions[0].status == "conflict"
    assert decisions[1].status == "idempotent-success"


@pytest.mark.real_module
def test_plan_cleanup_only_deletes_manifest_listed_refs():
    """AC-FR2400-01: foreign/unlisted refs must be preserved (not deleted)."""
    manifest = _valid_manifest()
    existing = {
        "refs/louke/rgr/run-001/T-001/att-1/red": "r" * 40,
        "refs/louke/rgr/foreign/foreign/red": "f" * 40,  # foreign
    }
    decisions = plan_cleanup(manifest, existing_refs=existing)
    # Only manifest-listed refs are in the decision list.
    listed_refnames = {d.refname for d in decisions}
    assert "refs/louke/rgr/foreign/foreign/red" not in listed_refnames


# ---------------------------------------------------------------------------
# close_milestone
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_close_milestone_complete_when_all_preconditions_met():
    """AC-FR2400-01: publish verified + trace closed + no conflicts -> complete."""
    store = ArchiveStore()
    decisions = (
        CleanupDecision(
            refname="refs/louke/rgr/run-001/T-001/att-1/red",
            expected_oid="r" * 40,
            actual_oid="r" * 40,
            status="success",
        ),
    )
    state = close_milestone(
        store=store,
        run_id="run-001",
        candidate_id="cand-1",
        publish_facts_verified=True,
        trace_closed=True,
        archive_manifest=_valid_manifest(),
        cleanup_results=decisions,
    )
    assert state == MilestoneState.COMPLETE
    assert store.next_release_eligible() is True


@pytest.mark.real_module
def test_close_milestone_closing_when_publish_not_verified():
    """AC-FR2400-01: publish facts not verified -> closing (idempotent retry)."""
    store = ArchiveStore()
    decisions = (
        CleanupDecision(
            refname="refs/louke/rgr/run-001/T-001/att-1/red",
            expected_oid="r" * 40,
            actual_oid="r" * 40,
            status="success",
        ),
    )
    state = close_milestone(
        store=store,
        run_id="run-001",
        candidate_id="cand-1",
        publish_facts_verified=False,
        trace_closed=True,
        archive_manifest=_valid_manifest(),
        cleanup_results=decisions,
    )
    assert state == MilestoneState.CLOSING
    assert store.next_release_eligible() is False


@pytest.mark.real_module
def test_close_milestone_closing_when_trace_not_closed():
    """AC-FR2400-01: trace not closed -> closing."""
    store = ArchiveStore()
    decisions = (
        CleanupDecision(
            refname="refs/louke/rgr/run-001/T-001/att-1/red",
            expected_oid="r" * 40,
            actual_oid="r" * 40,
            status="success",
        ),
    )
    state = close_milestone(
        store=store,
        run_id="run-001",
        candidate_id="cand-1",
        publish_facts_verified=True,
        trace_closed=False,
        archive_manifest=_valid_manifest(),
        cleanup_results=decisions,
    )
    assert state == MilestoneState.CLOSING


@pytest.mark.real_module
def test_close_milestone_needs_attention_on_cleanup_conflict():
    """AC-FR2400-01: cleanup conflict -> needs_attention; no re-publish."""
    store = ArchiveStore()
    decisions = (
        CleanupDecision(
            refname="refs/louke/rgr/run-001/T-001/att-1/red",
            expected_oid="r" * 40,
            actual_oid="x" * 40,
            status="conflict",
        ),
    )
    state = close_milestone(
        store=store,
        run_id="run-001",
        candidate_id="cand-1",
        publish_facts_verified=True,
        trace_closed=True,
        archive_manifest=_valid_manifest(),
        cleanup_results=decisions,
    )
    assert state == MilestoneState.NEEDS_ATTENTION
    assert store.next_release_eligible() is False


@pytest.mark.real_module
def test_next_release_eligibility_disabled_in_closing_or_needs_attention():
    """AC-FR2400-01: closing/needs_attention -> next release entry disabled."""
    store = ArchiveStore()
    assert store.next_release_eligible() is False  # initial: closing
    store.set_state(MilestoneState.NEEDS_ATTENTION)
    assert store.next_release_eligible() is False
    store.set_state(MilestoneState.COMPLETE)
    assert store.next_release_eligible() is True


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-FR2400-01: ERROR_CODES includes all codes from interfaces.md §14."""
    expected = {
        "TRACE_EDGE_INVALID",
        "TRACE_FORWARD_MISSING",
        "TRACE_REVERSE_ORPHAN",
        "TRACE_AMBIGUOUS",
        "ARCHIVE_PUBLISH_UNCONFIRMED",
        "ARCHIVE_MEMBER_MISSING",
        "ARCHIVE_DIGEST_MISMATCH",
        "ARCHIVE_READBACK_FAILED",
        "CLEANUP_REF_CONFLICT",
        "CLEANUP_FOREIGN_REF",
        "CLEANUP_INCOMPLETE",
        "HISTORY_PROJECTION_FAILED",
        "NEXT_RELEASE_NOT_ELIGIBLE",
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
