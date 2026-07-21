"""Integration tests for FR-1000: Refactor subphase.

AC-FR1000-01: Structural improvements produce an independent Refactor
commit ``F`` (parent=G) and re-run all Green checks/pre-commit; no
changes produce a no-change evidence bound to ``G``. Changes to public
interface/data semantics/test layering/architecture are identified as
upstream gaps and may NOT be completed as Refactor.

Interfaces covered (per interfaces.md):
- IF-RGR-01 (Primary ARC-05)
- IF-REV-02 (Prism review, ARC-07)
"""
# AC-FR1000-01

from __future__ import annotations

import pytest

from louke.v014.fr1000_refactor_subphase import (
    ERROR_CODES,
    NoChangeEvidence,
    RefactorError,
    RefactorPatch,
    RefactorRecord,
    build_no_change_evidence,
    commit_refactor,
)


def _valid_patch() -> RefactorPatch:
    return RefactorPatch(
        diff_paths=("louke/v014/fr0100_m_impl_entry.py",),
        public_interface_changed=False,
        data_semantics_changed=False,
        test_layering_changed=False,
        architecture_changed=False,
        has_changes=True,
    )


# ---------------------------------------------------------------------------
# commit_refactor
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_commit_refactor_creates_commit_with_parent_g():
    """AC-FR1000-01: F.parent = G; release branch advances to F."""
    record = commit_refactor(
        run_id="run-001",
        task_id="T-001",
        attempt_no=1,
        green_oid="g" * 40,
        refactor_oid="f" * 40,
        patch=_valid_patch(),
        precommit_passed=True,
        green_checks_passed=True,
    )
    assert isinstance(record, RefactorRecord)
    assert record.parent == "g" * 40  # F.parent = G
    assert record.branch_oid == "f" * 40  # release branch -> F
    assert record.commit_id.startswith("refactor:")


@pytest.mark.real_module
def test_commit_refactor_rejects_public_interface_change():
    """AC-FR1000-01: public interface change -> RGR_REFACTOR_CONTRACT_CHANGED."""
    p = RefactorPatch(
        diff_paths=_valid_patch().diff_paths,
        public_interface_changed=True,
        data_semantics_changed=False,
        test_layering_changed=False,
        architecture_changed=False,
        has_changes=True,
    )
    with pytest.raises(RefactorError) as exc:
        commit_refactor(
            run_id="run-001",
            task_id="T-001",
            attempt_no=1,
            green_oid="g" * 40,
            refactor_oid="f" * 40,
            patch=p,
            precommit_passed=True,
            green_checks_passed=True,
        )
    assert exc.value.code == "RGR_REFACTOR_CONTRACT_CHANGED"


@pytest.mark.real_module
def test_commit_refactor_rejects_data_semantics_change():
    """AC-FR1000-01: data semantics change -> RGR_REFACTOR_CONTRACT_CHANGED."""
    p = RefactorPatch(
        diff_paths=_valid_patch().diff_paths,
        public_interface_changed=False,
        data_semantics_changed=True,
        test_layering_changed=False,
        architecture_changed=False,
        has_changes=True,
    )
    with pytest.raises(RefactorError) as exc:
        commit_refactor(
            run_id="run-001",
            task_id="T-001",
            attempt_no=1,
            green_oid="g" * 40,
            refactor_oid="f" * 40,
            patch=p,
            precommit_passed=True,
            green_checks_passed=True,
        )
    assert exc.value.code == "RGR_REFACTOR_CONTRACT_CHANGED"


@pytest.mark.real_module
def test_commit_refactor_rejects_test_layering_change():
    """AC-FR1000-01: test layering change -> RGR_REFACTOR_CONTRACT_CHANGED."""
    p = RefactorPatch(
        diff_paths=_valid_patch().diff_paths,
        public_interface_changed=False,
        data_semantics_changed=False,
        test_layering_changed=True,
        architecture_changed=False,
        has_changes=True,
    )
    with pytest.raises(RefactorError) as exc:
        commit_refactor(
            run_id="run-001",
            task_id="T-001",
            attempt_no=1,
            green_oid="g" * 40,
            refactor_oid="f" * 40,
            patch=p,
            precommit_passed=True,
            green_checks_passed=True,
        )
    assert exc.value.code == "RGR_REFACTOR_CONTRACT_CHANGED"


@pytest.mark.real_module
def test_commit_refactor_rejects_architecture_change():
    """AC-FR1000-01: architecture change -> RGR_REFACTOR_CONTRACT_CHANGED."""
    p = RefactorPatch(
        diff_paths=_valid_patch().diff_paths,
        public_interface_changed=False,
        data_semantics_changed=False,
        test_layering_changed=False,
        architecture_changed=True,
        has_changes=True,
    )
    with pytest.raises(RefactorError) as exc:
        commit_refactor(
            run_id="run-001",
            task_id="T-001",
            attempt_no=1,
            green_oid="g" * 40,
            refactor_oid="f" * 40,
            patch=p,
            precommit_passed=True,
            green_checks_passed=True,
        )
    assert exc.value.code == "RGR_REFACTOR_CONTRACT_CHANGED"


@pytest.mark.real_module
def test_commit_refactor_rejects_green_checks_not_passed():
    """AC-FR1000-01: Green checks not re-run/passed -> RGR_FINAL_GATE_FAILED."""
    with pytest.raises(RefactorError) as exc:
        commit_refactor(
            run_id="run-001",
            task_id="T-001",
            attempt_no=1,
            green_oid="g" * 40,
            refactor_oid="f" * 40,
            patch=_valid_patch(),
            precommit_passed=True,
            green_checks_passed=False,
        )
    assert exc.value.code == "RGR_FINAL_GATE_FAILED"


@pytest.mark.real_module
def test_commit_refactor_rejects_precommit_failure():
    """AC-FR1000-01: pre-commit failed -> RGR_PRECOMMIT_FAILED."""
    with pytest.raises(RefactorError) as exc:
        commit_refactor(
            run_id="run-001",
            task_id="T-001",
            attempt_no=1,
            green_oid="g" * 40,
            refactor_oid="f" * 40,
            patch=_valid_patch(),
            precommit_passed=False,
            green_checks_passed=True,
        )
    assert exc.value.code == "RGR_PRECOMMIT_FAILED"


# ---------------------------------------------------------------------------
# build_no_change_evidence
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_no_change_evidence_bound_to_g_when_no_changes():
    """AC-FR1000-01: no structural changes -> NoChangeEvidence bound to G."""
    ev = build_no_change_evidence(
        run_id="run-001",
        task_id="T-001",
        attempt_no=1,
        green_oid="g" * 40,
        green_checks_passed=True,
    )
    assert isinstance(ev, NoChangeEvidence)
    assert ev.status == "no-change"
    assert ev.green_oid == "g" * 40
    assert ev.evidence_id.startswith("refactor-nochange:")


@pytest.mark.real_module
def test_no_change_evidence_requires_green_checks_passed():
    """AC-FR1000-01: no-change still requires re-running Green checks."""
    with pytest.raises(RefactorError) as exc:
        build_no_change_evidence(
            run_id="run-001",
            task_id="T-001",
            attempt_no=1,
            green_oid="g" * 40,
            green_checks_passed=False,
        )
    assert exc.value.code == "RGR_FINAL_GATE_FAILED"


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-FR1000-01: ERROR_CODES includes all codes from interfaces.md §4."""
    expected = {
        "RGR_REFACTOR_CONTRACT_CHANGED",
        "RGR_PRECOMMIT_FAILED",
        "RGR_FINAL_GATE_FAILED",
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
