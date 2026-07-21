"""AC-NFR0400-01: recoverability & audit.

NFR-0400 requires Runtime to recover M-DESIGN current state from persisted
revision/manifest/diff/review/program evidence/operation design after a
restart, never re-dispatch completed attempts, and fail closed on missing or
digest-inconsistent persistence while preserving historical revisions.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from louke._tools.audit_recovery import (
    AuditExport,
    AuditRecoveryError,
    PersistentRevision,
    PersistentStore,
    RecoveryReport,
    export_audit,
    recover_current_revision,
    verify_no_duplicate_dispatch,
    verify_persistence_integrity,
)

_SPEC_ROOT = (
    Path(__file__).resolve().parents[3]
    / ".louke"
    / "project"
    / "specs"
    / "v0.14-002-workflow-reflow-design"
)


def _make_revision(
    *,
    revision_id: str = "design-revision:abc",
    attempt_id: str = "att-1",
    digests_consistent: bool = True,
    completed_dispatches: tuple[str, ...] = ("att-1",),
) -> PersistentRevision:
    return PersistentRevision(
        revision_id=revision_id,
        attempt_id=attempt_id,
        run_id="run-1",
        base_commit="a" * 40,
        requirements_digests={
            "story": "sha256:" + "a" * 64,
            "spec": "sha256:" + "b" * 64,
            "acceptance": "sha256:" + "c" * 64,
        },
        project_facts_digest="sha256:" + "d" * 64,
        task_manifest_digest="sha256:" + "e" * 64,
        program_evidence_digests=(
            "sha256:" + "1" * 64,
            "sha256:" + "2" * 64,
        ),
        prism_verdict_digest="sha256:" + "3" * 64,
        baseline_digest="sha256:" + "4" * 64,
        digests_consistent=digests_consistent,
        completed_dispatches=completed_dispatches,
        history=(
            PersistentRevision(
                revision_id="design-revision:parent",
                attempt_id="att-0",
                run_id="run-1",
                base_commit="a" * 40,
                requirements_digests={
                    "story": "sha256:" + "a" * 64,
                    "spec": "sha256:" + "b" * 64,
                    "acceptance": "sha256:" + "c" * 64,
                },
                project_facts_digest="sha256:" + "d" * 64,
                task_manifest_digest="sha256:" + "old" * 21 + "=",
                program_evidence_digests=(),
                prism_verdict_digest="",
                baseline_digest="",
                digests_consistent=True,
                completed_dispatches=(),
                history=(),
            ),
        ),
    )


def test_recover_current_revision_returns_same_state() -> None:
    """AC-NFR0400-01: a restart recovers the same current revision and pending work."""
    revision = _make_revision()
    store = PersistentStore(current=revision, pending_work=("prism review",))
    report = recover_current_revision(store)
    assert isinstance(report, RecoveryReport)
    assert report.current_revision.revision_id == "design-revision:abc"
    assert report.current_revision.attempt_id == "att-1"
    assert report.pending_work == ("prism review",)


def test_recover_does_not_duplicate_completed_dispatches() -> None:
    """AC-NFR0400-01: a restart does not re-dispatch completed attempts."""
    revision = _make_revision(completed_dispatches=("att-1", "att-2"))
    store = PersistentStore(current=revision, pending_work=())
    report = recover_current_revision(store)
    assert report.completed_dispatches == ("att-1", "att-2")
    assert report.pending_dispatches == ()


def test_verify_no_duplicate_dispatch_detects_re_dispatch() -> None:
    """AC-NFR0400-01: re-dispatching a completed attempt is rejected."""
    revision = _make_revision(completed_dispatches=("att-1",))
    with pytest.raises(AuditRecoveryError) as exc:
        verify_no_duplicate_dispatch(revision, attempted_dispatches=("att-1", "att-2"))
    assert exc.value.code == "RECOVERY_DUPLICATE_DISPATCH"


def test_verify_persistence_integrity_fails_closed_on_digest_inconsistency() -> None:
    """AC-NFR0400-01: a digest mismatch fails closed."""
    revision = _make_revision(digests_consistent=False)
    with pytest.raises(AuditRecoveryError) as exc:
        verify_persistence_integrity(revision)
    assert exc.value.code == "RECOVERY_DIGEST_INCONSISTENT"


def test_verify_persistence_integrity_passes_for_consistent() -> None:
    """AC-NFR0400-01: a digest-consistent revision passes integrity check."""
    revision = _make_revision(digests_consistent=True)
    verify_persistence_integrity(revision)  # does not raise


def test_recovery_preserves_history() -> None:
    """AC-NFR0400-01: recovery preserves historical revisions."""
    revision = _make_revision()
    store = PersistentStore(current=revision, pending_work=())
    report = recover_current_revision(store)
    assert report.history
    assert report.history[0].revision_id == "design-revision:parent"


def test_export_audit_returns_typed_audit_export() -> None:
    """AC-NFR0400-01: audit export returns a typed audit export record."""
    revision = _make_revision()
    store = PersistentStore(current=revision, pending_work=("prism review",))
    audit = export_audit(store)
    assert isinstance(audit, AuditExport)
    assert audit.current_revision.revision_id == revision.revision_id
    assert audit.history
    assert "prism review" in audit.pending_work


def test_export_audit_redacts_secrets() -> None:
    """AC-NFR0400-01: audit export does not echo secrets."""
    revision = _make_revision()
    store = PersistentStore(current=revision, pending_work=())
    audit = export_audit(store)
    payload = audit.to_dict()
    text = str(payload)
    # No secret-looking tokens should appear in the audit export
    for marker in ("AKIA", "BEGIN PRIVATE KEY", "password=", "token="):
        assert marker not in text


def test_recovery_fails_closed_when_store_empty() -> None:
    """AC-NFR0400-01: an empty store fails closed rather than fabricating state."""
    empty_store = PersistentStore(current=None, pending_work=())
    with pytest.raises(AuditRecoveryError) as exc:
        recover_current_revision(empty_store)
    assert exc.value.code == "RECOVERY_NO_CURRENT_REVISION"


def test_recovery_report_is_immutable() -> None:
    """AC-NFR0400-01: the recovery report is an immutable value object."""
    revision = _make_revision()
    store = PersistentStore(current=revision, pending_work=())
    report = recover_current_revision(store)
    with pytest.raises(Exception):
        report.pending_work = ("tampered",)  # type: ignore[misc]
