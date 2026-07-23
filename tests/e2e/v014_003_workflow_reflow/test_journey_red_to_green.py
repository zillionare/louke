"""E2E journey: Red -> Green -> Refactor -> final review cycle.

Covers AC IDs:
- AC-FR0500-01 (Red program gate)
- AC-FR0600-01 (private Red git checkpoint)
- AC-FR0700-01 (Red independent review & correction)
- AC-FR0800-01 (Green minimal impl & Red test protection)
- AC-FR0900-01 (formal Green commit & lineage)
- AC-FR1000-01 (Refactor subphase)
- AC-FR1100-01 (final task review & completion gate)

NORMAL PATH: Red PASS -> Prism PASS -> Green PASS -> Refactor (or
no-change) -> final review PASS -> task complete.
"""
# AC-FR0500-01, AC-FR0800-01, AC-FR0900-01, AC-FR1000-01, AC-FR1100-01

from __future__ import annotations

import pytest

pytestmark = pytest.mark.v014_003_e2e


def test_red_to_green_to_refactor_normal_path():
    """J-IMPL-RGR: Red PASS -> Prism PASS -> Green PASS -> Refactor commit.

    Normal path through the RGR cycle.
    """
    from louke.runtime.red_program_gate import (
        FailureFingerprint,
        RedPatch,
        evaluate_red_gate,
    )
    from louke.runtime.red_git_checkpoint import (
        PrivateRefStore,
        create_red_checkpoint,
    )
    from louke.runtime.red_review import (
        PrismRedVerdict,
        RedReviewStore,
        attach_red_review,
        can_start_green,
    )
    from louke.runtime.green_minimal import (
        GreenCheck,
        GreenPatch,
        build_green_attempt,
        evaluate_green_checks,
    )
    from louke.runtime.green_commit import commit_green
    from louke.runtime.refactor_subphase import (
        RefactorPatch,
        commit_refactor,
    )

    # Red gate: valid assertion failure -> PASS
    red_patch = RedPatch(
        diff_paths=("tests/unit/test_fr0100.py",),
        product_code_changed=False,
        test_weakened=False,
        ac_refs=("AC-FR0100-01",),
        has_anti_pattern=False,
        syntax_valid=True,
        secret_detected=False,
        static_check_passed=True,
        format_passed=True,
    )
    red_failure = FailureFingerprint(
        category="assertion",
        command="pytest -q tests/unit/test_fr0100.py",
        ac_refs=("AC-FR0100-01",),
        assertion_identity="tests/unit/test_fr0100.py::test_x",
        output_digest="sha256:output",
    )
    red_result = evaluate_red_gate(
        patch=red_patch,
        failure=red_failure,
        command="pytest -q tests/unit/test_fr0100.py",
    )
    assert red_result.status == "pass"

    # Red checkpoint: private ref created
    store = PrivateRefStore()
    checkpoint = create_red_checkpoint(
        store=store,
        run_id="e2e-run-001",
        task_id="T-001",
        attempt_no=1,
        baseline_oid="b" * 40,
        red_oid="r" * 40,
        test_command="pytest -q tests/unit/test_fr0100.py",
        failure_fingerprint="assertion:AC-FR0100-01",
        output_digest="sha256:output",
        creator="runtime:program",
    )
    assert checkpoint.parent == "b" * 40
    assert store.branch_oid == "b" * 40  # release branch unchanged

    # Prism Red review: PASS
    review_store = RedReviewStore()
    attach_red_review(
        review_store,
        PrismRedVerdict(
            review_id="rev-red-001",
            baseline_oid="b" * 40,
            red_oid="r" * 40,
            evidence_digest="sha256:ev",
            verdict="PASS",
        ),
    )
    assert (
        can_start_green(
            review_store,
            red_oid="r" * 40,
            program_passed=True,
        )
        is True
    )

    # Green: minimal implementation, R tests preserved
    green_patch = GreenPatch(
        diff_paths=("louke/v014/fr0100.py",),
        test_deleted=False,
        test_weakened=False,
        implementation_added=True,
        design_contract_change=False,
    )
    green_attempt = build_green_attempt(
        run_id="e2e-run-001",
        task_id="T-001",
        attempt_no=1,
        baseline_oid="b" * 40,
        reviewed_red_oid="r" * 40,
        patch=green_patch,
    )
    # AC-FR0800-01: Green attempt restores R tree; branch unchanged.
    assert green_attempt.workspace_tree_oid == "r" * 40
    assert green_attempt.branch_oid == "b" * 40
    checks = [
        GreenCheck(name=n, passed=True)
        for n in ("target", "history-unit", "static", "contract", "lint", "format")
    ]
    green_report = evaluate_green_checks(checks)
    assert green_report.status == "pass"

    # Formal Green commit: G.parent=B, branch advances to G
    green_record = commit_green(
        run_id="e2e-run-001",
        task_id="T-001",
        attempt_no=1,
        baseline_oid="b" * 40,
        red_oid="r" * 40,
        green_oid="g" * 40,
        precommit_passed=True,
        used_no_verify=False,
        hook_rewrote_files=False,
        b_r_diff={"test_only": True, "implementation_only": False},
        r_g_diff={"test_only": False, "implementation_only": True},
    )
    assert green_record.parent == "b" * 40
    assert green_record.branch_oid == "g" * 40

    # Refactor: structural improvement, behavior preserved
    refactor_patch = RefactorPatch(
        diff_paths=("louke/v014/fr0100.py",),
        public_interface_changed=False,
        data_semantics_changed=False,
        test_layering_changed=False,
        architecture_changed=False,
        has_changes=True,
    )
    refactor_record = commit_refactor(
        run_id="e2e-run-001",
        task_id="T-001",
        attempt_no=1,
        green_oid="g" * 40,
        refactor_oid="f" * 40,
        patch=refactor_patch,
        precommit_passed=True,
        green_checks_passed=True,
    )
    assert refactor_record.parent == "g" * 40
    assert refactor_record.branch_oid == "f" * 40


def test_final_review_pass_completes_task():
    """J-IMPL-RGR final step: final review PASS -> task complete.

    AC-FR1100-01: program gate + Prism PASS -> task completion.
    """
    from louke.runtime.final_review_gate import (
        FinalLineage,
        PrismFinalVerdict,
        TaskCompletionGate,
    )

    gate = TaskCompletionGate()
    lineage = FinalLineage(
        baseline_oid="b" * 40,
        red_oid="r" * 40,
        green_oid="g" * 40,
        refactor_oid="f" * 40,
    )
    verdict = PrismFinalVerdict(
        review_id="rev-final-001",
        subject_oid="f" * 40,
        verdict="PASS",
    )
    gate.attach_prism_review(lineage, verdict)
    checks = {
        "scope": True,
        "secret": True,
        "ac_trace": True,
        "generated_files": True,
        "external_diff": True,
        "anti_pattern": True,
        "dependency": True,
    }
    assert gate.can_complete(lineage, checks) is True
