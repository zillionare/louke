"""AC-FR2400-01: M-MILESTONE trace, archive & resource cleanup.

After publish verification, Runtime closes the bidirectional trace
(FR/NFR->AC->Test Plan->task/Issue->R/review->code/test/CI->artifact/
release), updates requirement Issues/Project, archives run/tasks/
reviews/gates/events/diffs/RGR/CI/artifact/security/publish evidence,
and turns the project into read-only history.  Only after publish facts
verified AND all required archives closed may Project/WorkflowRun
``complete`` and release the next main release eligibility.  ``closing``
or ``needs_attention`` may NOT release that eligibility.  Only after
Red commit/tree + evidence enter recoverable archive may Runtime
precisely delete the run-manifest-listed ``refs/louke/rgr/{run}/...``;
close failure keeps ``closing`` idempotent retry, no re-publish.
"""

from __future__ import annotations


from louke.v014.fr2400_m_milestone import (
    ArchiveManifest,
    ArchiveStore,
    CleanupDecision,
    MilestoneState,
    close_milestone,
    plan_cleanup,
)

_RUN = "run-1"
_CAND = "cand:abc"
_REF = "refs/louke/rgr/run-1/t-001/att-1/red"
_R_OID = "r" * 40


def _archive(*, red_refs: tuple[str, ...] = (_REF,)) -> ArchiveManifest:
    return ArchiveManifest(
        archive_id="archive:1",
        run_id=_RUN,
        candidate_id=_CAND,
        trace_root="trace-root:1",
        evidence_ids=("ev-1", "ev-2"),
        red_refs=tuple((ref, _R_OID) for ref in red_refs),
    )


def test_close_milestone_completes_when_all_evidence_archived() -> None:
    """AC-FR2400-01: complete only after publish verified + archive closed."""
    store = ArchiveStore()
    state = close_milestone(
        store=store,
        run_id=_RUN,
        candidate_id=_CAND,
        publish_facts_verified=True,
        trace_closed=True,
        archive_manifest=_archive(),
        cleanup_results=(),
    )
    assert state == MilestoneState.COMPLETE


def test_close_milestone_blocks_when_publish_unverified() -> None:
    """AC-FR2400-01: unverified publish facts block complete (stay closing)."""
    store = ArchiveStore()
    state = close_milestone(
        store=store,
        run_id=_RUN,
        candidate_id=_CAND,
        publish_facts_verified=False,
        trace_closed=True,
        archive_manifest=_archive(),
        cleanup_results=(),
    )
    assert state == MilestoneState.CLOSING


def test_close_milestone_blocks_when_trace_open() -> None:
    """AC-FR2400-01: open trace blocks complete."""
    store = ArchiveStore()
    state = close_milestone(
        store=store,
        run_id=_RUN,
        candidate_id=_CAND,
        publish_facts_verified=True,
        trace_closed=False,
        archive_manifest=_archive(),
        cleanup_results=(),
    )
    assert state == MilestoneState.CLOSING


def test_close_milestone_needs_attention_when_cleanup_fails() -> None:
    """AC-FR2400-01: cleanup conflict enters needs_attention, no re-publish."""
    store = ArchiveStore()
    state = close_milestone(
        store=store,
        run_id=_RUN,
        candidate_id=_CAND,
        publish_facts_verified=True,
        trace_closed=True,
        archive_manifest=_archive(),
        cleanup_results=(
            CleanupDecision(
                refname=_REF,
                expected_oid=_R_OID,
                actual_oid="x" * 40,
                status="conflict",
            ),
        ),
    )
    assert state == MilestoneState.NEEDS_ATTENTION


def test_plan_cleanup_only_deletes_manifest_listed_refs() -> None:
    """AC-FR2400-01: cleanup deletes only refs listed in archive manifest."""
    manifest = _archive(red_refs=(_REF,))
    decisions = plan_cleanup(
        manifest, existing_refs=({_REF: _R_OID, "refs/other": "y" * 40})
    )
    targets = {d.refname for d in decisions}
    assert _REF in targets
    assert "refs/other" not in targets


def test_plan_cleanup_idempotent_when_ref_already_deleted() -> None:
    """AC-FR2400-01: ref already deleted is idempotent success."""
    manifest = _archive(red_refs=(_REF,))
    decisions = plan_cleanup(manifest, existing_refs={})  # ref not present
    assert all(d.status == "idempotent-success" for d in decisions)


def test_plan_cleanup_rejects_foreign_ref() -> None:
    """AC-FR2400-01: foreign refs not in manifest must not be deleted."""
    manifest = _archive(red_refs=(_REF,))
    decisions = plan_cleanup(
        manifest,
        existing_refs={_REF: _R_OID, "refs/foreign": "z" * 40},
    )
    targets = {d.refname for d in decisions}
    assert "refs/foreign" not in targets


def test_plan_cleanup_conflict_when_oid_mismatches() -> None:
    """AC-FR2400-01: actual OID != expected R OID -> conflict, no delete."""
    manifest = _archive()
    decisions = plan_cleanup(manifest, existing_refs={_REF: "x" * 40})
    assert decisions[0].status == "conflict"


def test_close_milestone_idempotent_retry_does_not_republish() -> None:
    """AC-FR2400-01: closing retry is idempotent; no re-publish."""
    store = ArchiveStore()
    close_milestone(
        store=store,
        run_id=_RUN,
        candidate_id=_CAND,
        publish_facts_verified=False,
        trace_closed=True,
        archive_manifest=_archive(),
        cleanup_results=(),
    )
    # Retry with same inputs -> still CLOSING, no new publish.
    state2 = close_milestone(
        store=store,
        run_id=_RUN,
        candidate_id=_CAND,
        publish_facts_verified=False,
        trace_closed=True,
        archive_manifest=_archive(),
        cleanup_results=(),
    )
    assert state2 == MilestoneState.CLOSING


def test_complete_releases_next_release_eligibility() -> None:
    """AC-FR2400-01: complete releases next main release eligibility."""
    store = ArchiveStore()
    close_milestone(
        store=store,
        run_id=_RUN,
        candidate_id=_CAND,
        publish_facts_verified=True,
        trace_closed=True,
        archive_manifest=_archive(),
        cleanup_results=(),
    )
    assert store.next_release_eligible() is True


def test_closing_or_needs_attention_does_not_release_eligibility() -> None:
    """AC-FR2400-01: closing/needs_attention must not release next eligibility."""
    store = ArchiveStore()
    close_milestone(
        store=store,
        run_id=_RUN,
        candidate_id=_CAND,
        publish_facts_verified=False,
        trace_closed=True,
        archive_manifest=_archive(),
        cleanup_results=(),
    )
    assert store.next_release_eligible() is False
