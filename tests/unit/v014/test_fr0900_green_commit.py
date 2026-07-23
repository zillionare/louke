"""AC-FR0900-01: Formal Green commit & lineage.

After Green checks pass, Runtime creates formal commit ``G`` on the
release branch with ``parent=B`` and tree containing the reviewed tests
+ minimal implementation.  Trailers/evidence associate task and ``R``.
``G`` runs the ordinary pre-commit; ``--no-verify`` is forbidden.  If
hooks rewrite files, Runtime re-validates scope/lineage/checks.  Runtime
proves ``B->R`` test-only, ``R->G`` default implementation-only; ``R``
is NOT a parent of ``G``.
"""

from __future__ import annotations

from typing import Any

import pytest

from louke.runtime.green_commit import (
    GreenCommitError,
    GreenCommitRecord,
    GreenLineage,
    LineageCheck,
    commit_green,
    verify_lineage,
)

_B = "b" * 40
_R = "r" * 40
_G = "g" * 40


def _kwargs(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "run_id": "run-1",
        "task_id": "t-001",
        "attempt_no": 1,
        "baseline_oid": _B,
        "red_oid": _R,
        "green_oid": _G,
        "precommit_passed": True,
        "used_no_verify": False,
        "hook_rewrote_files": False,
        "b_r_diff": {"test_only": True, "implementation_only": False},
        "r_g_diff": {"test_only": False, "implementation_only": True},
    }
    base.update(overrides)
    return base


def test_commit_green_creates_formal_commit_with_parent_b() -> None:
    """AC-FR0900-01: G is a formal commit on release branch with parent=B."""
    record = commit_green(**_kwargs())
    assert isinstance(record, GreenCommitRecord)
    assert record.parent == _B
    assert record.green_oid == _G
    assert record.branch_oid == _G  # release branch tip advances to G
    assert record.precommit_passed is True
    # Trailers/evidence associate task and R.
    assert record.trailer_refs["task_id"] == "t-001"
    assert record.trailer_refs["red_oid"] == _R


def test_commit_green_rejects_no_verify() -> None:
    """AC-FR0900-01: --no-verify is forbidden; pre-commit must run."""
    with pytest.raises(GreenCommitError) as exc:
        commit_green(**_kwargs(used_no_verify=True))
    assert exc.value.code == "RGR_PRECOMMIT_FAILED"


def test_commit_green_rejects_precommit_failure() -> None:
    """AC-FR0900-01: pre-commit failure blocks G."""
    with pytest.raises(GreenCommitError) as exc:
        commit_green(**_kwargs(precommit_passed=False))
    assert exc.value.code == "RGR_PRECOMMIT_FAILED"


def test_commit_green_rejects_hook_rewrite_unverified() -> None:
    """AC-FR0900-01: hook rewriting files requires re-validation."""
    with pytest.raises(GreenCommitError) as exc:
        commit_green(
            **_kwargs(hook_rewrote_files=True, revalidated_after_rewrite=False)
        )
    assert exc.value.code == "RGR_PRECOMMIT_FAILED"


def test_commit_green_accepts_hook_rewrite_after_revalidation() -> None:
    """AC-FR0900-01: hook rewrite accepted after scope/lineage/checks re-validation."""
    record = commit_green(
        **_kwargs(hook_rewrote_files=True, revalidated_after_rewrite=True)
    )
    assert record.green_oid == _G


def test_verify_lineage_proves_b_to_r_test_only() -> None:
    """AC-FR0900-01: lineage proves B->R test-only."""
    lineage = GreenLineage(
        baseline_oid=_B,
        red_oid=_R,
        green_oid=_G,
        b_r_diff=LineageCheck(test_only=True, implementation_only=False),
        r_g_diff=LineageCheck(test_only=False, implementation_only=True),
    )
    assert verify_lineage(lineage).status == "pass"


def test_verify_lineage_rejects_r_in_g_ancestry() -> None:
    """AC-FR0900-01: R must NOT be a parent of G."""
    lineage = GreenLineage(
        baseline_oid=_B,
        red_oid=_R,
        green_oid=_G,
        b_r_diff=LineageCheck(test_only=True, implementation_only=False),
        r_g_diff=LineageCheck(test_only=False, implementation_only=True),
        r_is_g_parent=True,
    )
    report = verify_lineage(lineage)
    assert report.status == "fail"
    assert "RGR_LINEAGE_INVALID" in report.reason


def test_verify_lineage_rejects_b_r_not_test_only() -> None:
    """AC-FR0900-01: B->R must be test-only."""
    lineage = GreenLineage(
        baseline_oid=_B,
        red_oid=_R,
        green_oid=_G,
        b_r_diff=LineageCheck(test_only=False, implementation_only=False),
        r_g_diff=LineageCheck(test_only=False, implementation_only=True),
    )
    report = verify_lineage(lineage)
    assert report.status == "fail"


def test_verify_lineage_rejects_r_g_with_test_changes() -> None:
    """AC-FR0900-01: R->G must not contain test changes (default impl-only)."""
    lineage = GreenLineage(
        baseline_oid=_B,
        red_oid=_R,
        green_oid=_G,
        b_r_diff=LineageCheck(test_only=True, implementation_only=False),
        r_g_diff=LineageCheck(test_only=True, implementation_only=True),
    )
    report = verify_lineage(lineage)
    assert report.status == "fail"


def test_commit_green_idempotent_for_same_inputs() -> None:
    """AC-FR0900-01: same inputs produce same commit identity."""
    a = commit_green(**_kwargs())
    b = commit_green(**_kwargs())
    assert a.commit_id == b.commit_id
