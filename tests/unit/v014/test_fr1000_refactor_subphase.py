"""AC-FR1000-01: Refactor subphase.

After ``G``, Runtime allows Devon to make behaviour-preserving structural
improvements under test protection, re-running all Green checks.  When
there are changes, an independent Refactor commit ``F`` (parent=G) is
created through ordinary pre-commit; when there are no changes, a
no-change evidence bound to ``G`` is recorded.  Changes to public
interface, data semantics, test layering or architecture are identified
as upstream gaps and may NOT be completed as Refactor.
"""

from __future__ import annotations


import pytest

from louke.runtime.refactor_subphase import (
    NoChangeEvidence,
    RefactorError,
    RefactorPatch,
    RefactorRecord,
    build_no_change_evidence,
    commit_refactor,
)

_B = "b" * 40
_G = "g" * 40
_F = "f" * 40


def _patch(
    *,
    diff_paths: tuple[str, ...] = ("louke/v014/x.py",),
    public_interface_changed: bool = False,
    data_semantics_changed: bool = False,
    test_layering_changed: bool = False,
    architecture_changed: bool = False,
    has_changes: bool = True,
) -> RefactorPatch:
    return RefactorPatch(
        diff_paths=diff_paths,
        public_interface_changed=public_interface_changed,
        data_semantics_changed=data_semantics_changed,
        test_layering_changed=test_layering_changed,
        architecture_changed=architecture_changed,
        has_changes=has_changes,
    )


def test_commit_refactor_creates_independent_commit_with_parent_g() -> None:
    """AC-FR1000-01: a Refactor commit F has parent=G and runs ordinary pre-commit."""
    record = commit_refactor(
        run_id="run-1",
        task_id="t-001",
        attempt_no=1,
        green_oid=_G,
        refactor_oid=_F,
        patch=_patch(),
        precommit_passed=True,
        green_checks_passed=True,
    )
    assert isinstance(record, RefactorRecord)
    assert record.parent == _G
    assert record.branch_oid == _F
    assert record.precommit_passed is True


def test_commit_refactor_rejects_public_interface_change() -> None:
    """AC-FR1000-01: public interface change must return upstream, not Refactor."""
    with pytest.raises(RefactorError) as exc:
        commit_refactor(
            run_id="run-1",
            task_id="t-001",
            attempt_no=1,
            green_oid=_G,
            refactor_oid=_F,
            patch=_patch(public_interface_changed=True),
            precommit_passed=True,
            green_checks_passed=True,
        )
    assert exc.value.code == "RGR_REFACTOR_CONTRACT_CHANGED"


def test_commit_refactor_rejects_data_semantics_change() -> None:
    """AC-FR1000-01: data semantics change must return upstream."""
    with pytest.raises(RefactorError) as exc:
        commit_refactor(
            run_id="run-1",
            task_id="t-001",
            attempt_no=1,
            green_oid=_G,
            refactor_oid=_F,
            patch=_patch(data_semantics_changed=True),
            precommit_passed=True,
            green_checks_passed=True,
        )
    assert exc.value.code == "RGR_REFACTOR_CONTRACT_CHANGED"


def test_commit_refactor_rejects_test_layering_change() -> None:
    """AC-FR1000-01: test layering change must return upstream."""
    with pytest.raises(RefactorError) as exc:
        commit_refactor(
            run_id="run-1",
            task_id="t-001",
            attempt_no=1,
            green_oid=_G,
            refactor_oid=_F,
            patch=_patch(test_layering_changed=True),
            precommit_passed=True,
            green_checks_passed=True,
        )
    assert exc.value.code == "RGR_REFACTOR_CONTRACT_CHANGED"


def test_commit_refactor_rejects_architecture_change() -> None:
    """AC-FR1000-01: architecture change must return upstream."""
    with pytest.raises(RefactorError) as exc:
        commit_refactor(
            run_id="run-1",
            task_id="t-001",
            attempt_no=1,
            green_oid=_G,
            refactor_oid=_F,
            patch=_patch(architecture_changed=True),
            precommit_passed=True,
            green_checks_passed=True,
        )
    assert exc.value.code == "RGR_REFACTOR_CONTRACT_CHANGED"


def test_commit_refactor_requires_green_checks_pass() -> None:
    """AC-FR1000-01: Refactor must re-run all Green checks; failure blocks F."""
    with pytest.raises(RefactorError) as exc:
        commit_refactor(
            run_id="run-1",
            task_id="t-001",
            attempt_no=1,
            green_oid=_G,
            refactor_oid=_F,
            patch=_patch(),
            precommit_passed=True,
            green_checks_passed=False,
        )
    assert exc.value.code == "RGR_FINAL_GATE_FAILED"


def test_commit_refactor_rejects_precommit_failure() -> None:
    """AC-FR1000-01: pre-commit failure blocks F."""
    with pytest.raises(RefactorError) as exc:
        commit_refactor(
            run_id="run-1",
            task_id="t-001",
            attempt_no=1,
            green_oid=_G,
            refactor_oid=_F,
            patch=_patch(),
            precommit_passed=False,
            green_checks_passed=True,
        )
    assert exc.value.code == "RGR_PRECOMMIT_FAILED"


def test_no_change_evidence_bound_to_g() -> None:
    """AC-FR1000-01: a no-change Refactor produces evidence bound to G."""
    evidence = build_no_change_evidence(
        run_id="run-1",
        task_id="t-001",
        attempt_no=1,
        green_oid=_G,
        green_checks_passed=True,
    )
    assert isinstance(evidence, NoChangeEvidence)
    assert evidence.green_oid == _G
    assert evidence.status == "no-change"


def test_no_change_evidence_requires_green_checks() -> None:
    """AC-FR1000-01: no-change evidence still requires re-running Green checks."""
    with pytest.raises(RefactorError) as exc:
        build_no_change_evidence(
            run_id="run-1",
            task_id="t-001",
            attempt_no=1,
            green_oid=_G,
            green_checks_passed=False,
        )
    assert exc.value.code == "RGR_FINAL_GATE_FAILED"


def test_refactor_with_no_changes_yields_no_change_evidence() -> None:
    """AC-FR1000-01: when patch has no changes, a no-change evidence is recorded."""
    evidence = build_no_change_evidence(
        run_id="run-1",
        task_id="t-001",
        attempt_no=1,
        green_oid=_G,
        green_checks_passed=True,
    )
    assert evidence.status == "no-change"
    assert evidence.green_oid == _G
