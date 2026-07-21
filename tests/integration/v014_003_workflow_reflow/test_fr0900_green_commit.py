"""Integration tests for FR-0900: Formal Green commit & lineage.

AC-FR0900-01: After Green checks PASS, the release branch's new commit
``G`` has parent=``B`` and a tree containing the approved tests + minimal
implementation; trailers/evidence reference task and ``R``. ``G`` runs
the ordinary pre-commit; blanket ``--no-verify`` is forbidden. Hook
re-writes must be re-validated. Runtime proves ``B->R`` test-only and
``R->G`` default implementation-only, and ``R`` is NOT a parent of
``G`` (sibling lineage).

Interfaces covered (per interfaces.md):
- IF-RGR-01 (Primary ARC-05)
- IF-PC-01 (pre-commit gate, ARC-02)
"""
# AC-FR0900-01

from __future__ import annotations

import pytest

from louke.v014.fr0900_green_commit import (
    ERROR_CODES,
    GreenCommitError,
    GreenCommitRecord,
    GreenLineage,
    LineageCheck,
    LineageReport,
    commit_green,
    verify_lineage,
)


def _valid_diffs() -> dict:
    """Diff classification dicts for B->R (test-only) and R->G (impl-only)."""
    return {
        "b_r_diff": {"test_only": True, "implementation_only": False},
        "r_g_diff": {"test_only": False, "implementation_only": True},
    }


# ---------------------------------------------------------------------------
# verify_lineage
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_verify_lineage_passes_on_test_only_br_impl_only_rg_sibling():
    """AC-FR0900-01: B->R test-only, R->G impl-only, R not parent of G -> pass."""
    lineage = GreenLineage(
        baseline_oid="b" * 40,
        red_oid="r" * 40,
        green_oid="g" * 40,
        b_r_diff=LineageCheck(test_only=True, implementation_only=False),
        r_g_diff=LineageCheck(test_only=False, implementation_only=True),
        r_is_g_parent=False,
    )
    report = verify_lineage(lineage)
    assert isinstance(report, LineageReport)
    assert report.status == "pass"


@pytest.mark.real_module
def test_verify_lineage_fails_when_r_is_g_parent():
    """AC-FR0900-01: R as parent of G -> RGR_LINEAGE_INVALID (must be siblings)."""
    lineage = GreenLineage(
        baseline_oid="b" * 40,
        red_oid="r" * 40,
        green_oid="g" * 40,
        b_r_diff=LineageCheck(test_only=True, implementation_only=False),
        r_g_diff=LineageCheck(test_only=False, implementation_only=True),
        r_is_g_parent=True,
    )
    report = verify_lineage(lineage)
    assert report.status == "fail"
    assert "RGR_LINEAGE_INVALID" in report.reason


@pytest.mark.real_module
def test_verify_lineage_fails_when_br_not_test_only():
    """AC-FR0900-01: B->R diff must be test-only."""
    lineage = GreenLineage(
        baseline_oid="b" * 40,
        red_oid="r" * 40,
        green_oid="g" * 40,
        b_r_diff=LineageCheck(test_only=False, implementation_only=True),
        r_g_diff=LineageCheck(test_only=False, implementation_only=True),
    )
    report = verify_lineage(lineage)
    assert report.status == "fail"
    assert "B->R" in report.reason or "test-only" in report.reason


@pytest.mark.real_module
def test_verify_lineage_fails_when_rg_is_test_only():
    """AC-FR0900-01: R->G diff must be implementation-only by default."""
    lineage = GreenLineage(
        baseline_oid="b" * 40,
        red_oid="r" * 40,
        green_oid="g" * 40,
        b_r_diff=LineageCheck(test_only=True, implementation_only=False),
        r_g_diff=LineageCheck(test_only=True, implementation_only=False),
    )
    report = verify_lineage(lineage)
    assert report.status == "fail"
    assert "R->G" in report.reason or "implementation-only" in report.reason


# ---------------------------------------------------------------------------
# commit_green
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_commit_green_creates_formal_commit_with_parent_b():
    """AC-FR0900-01: G.parent = B; release branch advances to G."""
    record = commit_green(
        run_id="run-001",
        task_id="T-001",
        attempt_no=1,
        baseline_oid="b" * 40,
        red_oid="r" * 40,
        green_oid="g" * 40,
        precommit_passed=True,
        used_no_verify=False,
        hook_rewrote_files=False,
        **_valid_diffs(),
    )
    assert isinstance(record, GreenCommitRecord)
    assert record.parent == "b" * 40  # G.parent = B
    assert record.branch_oid == "g" * 40  # release branch -> G
    # Trailers reference task_id and red_oid.
    assert record.trailer_refs["task_id"] == "T-001"
    assert record.trailer_refs["red_oid"] == "r" * 40
    # commit_id is stable identity.
    assert record.commit_id.startswith("green:")


@pytest.mark.real_module
def test_commit_green_rejects_no_verify():
    """AC-FR0900-01: blanket --no-verify -> RGR_PRECOMMIT_FAILED."""
    with pytest.raises(GreenCommitError) as exc:
        commit_green(
            run_id="run-001",
            task_id="T-001",
            attempt_no=1,
            baseline_oid="b" * 40,
            red_oid="r" * 40,
            green_oid="g" * 40,
            precommit_passed=True,
            used_no_verify=True,
            hook_rewrote_files=False,
            **_valid_diffs(),
        )
    assert exc.value.code == "RGR_PRECOMMIT_FAILED"


@pytest.mark.real_module
def test_commit_green_rejects_precommit_failure():
    """AC-FR0900-01: pre-commit did not pass -> RGR_PRECOMMIT_FAILED."""
    with pytest.raises(GreenCommitError) as exc:
        commit_green(
            run_id="run-001",
            task_id="T-001",
            attempt_no=1,
            baseline_oid="b" * 40,
            red_oid="r" * 40,
            green_oid="g" * 40,
            precommit_passed=False,
            used_no_verify=False,
            hook_rewrote_files=False,
            **_valid_diffs(),
        )
    assert exc.value.code == "RGR_PRECOMMIT_FAILED"


@pytest.mark.real_module
def test_commit_green_rejects_hook_rewrite_without_revalidation():
    """AC-FR0900-01: hook rewrote files but not re-validated -> RGR_PRECOMMIT_FAILED."""
    with pytest.raises(GreenCommitError) as exc:
        commit_green(
            run_id="run-001",
            task_id="T-001",
            attempt_no=1,
            baseline_oid="b" * 40,
            red_oid="r" * 40,
            green_oid="g" * 40,
            precommit_passed=True,
            used_no_verify=False,
            hook_rewrote_files=True,
            revalidated_after_rewrite=False,
            **_valid_diffs(),
        )
    assert exc.value.code == "RGR_PRECOMMIT_FAILED"


@pytest.mark.real_module
def test_commit_green_accepts_hook_rewrite_with_revalidation():
    """AC-FR0900-01: hook rewrote files + re-validated -> OK."""
    record = commit_green(
        run_id="run-001",
        task_id="T-001",
        attempt_no=1,
        baseline_oid="b" * 40,
        red_oid="r" * 40,
        green_oid="g" * 40,
        precommit_passed=True,
        used_no_verify=False,
        hook_rewrote_files=True,
        revalidated_after_rewrite=True,
        **_valid_diffs(),
    )
    assert record.hook_rewrote_files is True
    assert record.parent == "b" * 40


@pytest.mark.real_module
def test_commit_green_rejects_invalid_lineage():
    """AC-FR0900-01: invalid lineage (R is parent of G) -> RGR_LINEAGE_INVALID."""
    bad_kwargs = _valid_diffs()
    bad_kwargs["b_r_diff"] = {"test_only": False, "implementation_only": True}
    with pytest.raises(GreenCommitError) as exc:
        commit_green(
            run_id="run-001",
            task_id="T-001",
            attempt_no=1,
            baseline_oid="b" * 40,
            red_oid="r" * 40,
            green_oid="g" * 40,
            precommit_passed=True,
            used_no_verify=False,
            hook_rewrote_files=False,
            **bad_kwargs,
        )
    assert exc.value.code == "RGR_LINEAGE_INVALID"


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-FR0900-01: ERROR_CODES includes all codes from interfaces.md §4."""
    expected = {"RGR_PRECOMMIT_FAILED", "RGR_LINEAGE_INVALID", "RGR_BRANCH_CONFLICT"}
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
