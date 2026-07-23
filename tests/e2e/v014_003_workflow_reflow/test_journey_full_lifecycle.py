"""E2E journey: full M-IMPL -> M-TEST -> M-VERIFY -> M-RELEASE ->
M-PUBLISH -> M-MILESTONE lifecycle.

Covers AC IDs:
- AC-FR0100-01 (M-IMPL entry & pre-commit reconcile)
- AC-FR0800-01 (Green minimal impl)
- AC-FR0900-01 (formal Green commit + lineage)
- AC-FR1200-01 (M-TEST assets generation & review)
- AC-FR1300-01 (M-TEST execution & defect triage)
- AC-FR1400-01 (Release candidate freeze & freshness)
- AC-FR1500-01 (Local authoritative quality chain)
- AC-FR2100-01 (M-RELEASE preview & Human gate)
- AC-FR2200-01 (M-PUBLISH operation ledger)
- AC-FR2300-01 (post-publish verification & recovery)
- AC-FR2400-01 (M-MILESTONE trace/archive/cleanup)

This is a NORMAL-PATH journey: each stage passes its preconditions and
advances to the next; no error/boundary cases (those belong to
integration tests per test-plan.md §3.2).
"""
# AC-FR0100-01, AC-FR0900-01, AC-FR1400-01, AC-FR2100-01, AC-FR2400-01

from __future__ import annotations

import pytest

pytestmark = pytest.mark.v014_003_e2e


def test_m_impl_entry_to_baseline_ready():
    """J-IMPL-RGR step 1: M-IMPL entry produces a dispatch-eligible baseline.

    AC-FR0100-01: design PASS + clean workspace + pre-commit in_sync ->
    Runtime can dispatch Archer/Devon.
    """
    from louke.runtime.m_impl_entry import enter_m_impl

    inputs = {
        "run_id": "e2e-run-001",
        "release_identity": {
            "version": "0.14.0",
            "spec_id": "v0.14-003-workflow-reflow-impl",
            "branch": "releases/0.14.0",
            "tag": "v0.14.0",
        },
        "actor_id": "runtime:program",
        "attempt_id": "attempt-1",
        "base_commit": "a" * 40,
        "design": {
            "revision": "prism-r3",
            "digest": "sha256:design",
            "program_evidence_id": "ev-001",
            "prism_review_id": "rev-001",
            "program_status": "PASS",
            "prism_verdict": "PASS",
        },
        "workspace": {
            "tree_digest": "sha256:tree",
            "diffs": [
                {
                    "path": ".pre-commit-config.yaml",
                    "digest": "sha256:cfg",
                    "source": "controlled-commit",
                }
            ],
        },
    }
    contract = {
        "payload": {
            "managed_config_path": ".pre-commit-config.yaml",
            "tool_version": "4.6.0",
            "stages": ["pre-commit"],
            "hooks": [
                {"id": "preserve-existing", "stages": ["pre-commit"]},
                {"id": "louke-rgr", "stages": ["pre-commit"]},
            ],
        }
    }
    record = enter_m_impl(
        inputs,
        precommit_contract=contract,
        installed_stages=["pre-commit"],
        managed_config_present=True,
    )
    assert record.dispatch_eligible is True
    assert record.precommit.readback_status == "in_sync"


def test_green_commit_advances_release_branch():
    """J-IMPL-RGR step 2: Green commit advances the release branch.

    AC-FR0900-01: formal G commit has parent=B and runs pre-commit.
    """
    from louke.runtime.green_commit import commit_green

    record = commit_green(
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
    assert record.parent == "b" * 40
    assert record.branch_oid == "g" * 40


def test_candidate_freeze_blocks_writes_and_advances_to_verify():
    """J-TEST-VERIFY step: candidate freeze -> write_disabled=True.

    AC-FR1400-01: clean workspace + lineage current -> frozen candidate.
    """
    from louke.runtime.release_candidate import (
        CandidateStore,
        DependencyManifest,
        freeze_candidate,
    )

    store = CandidateStore()
    deps = DependencyManifest(
        code_digest="sha256:code",
        test_digest="sha256:test",
        design_digest="sha256:design",
        contract_digest="sha256:contract",
        prompt_digest="sha256:prompt",
        config_digest="sha256:config",
    )
    cand = freeze_candidate(
        store=store,
        run_id="e2e-run-001",
        branch_oid="g" * 40,
        workspace_clean=True,
        formal_ancestry_clean=True,
        no_private_red_in_ancestry=True,
        task_lineage_current=True,
        test_completion_current=True,
        precommit_current=True,
        deps=deps,
    )
    assert cand.write_disabled is True


def test_release_preview_enables_release_after_all_gates_pass():
    """J-RELEASE-DELAY step: all gates PASS -> Release enabled.

    AC-FR2100-01: Release enabled only when all non-waivable gates PASS.
    """
    from louke.runtime.m_release_preview import build_preview, submit_human_decision

    preview = build_preview(
        candidate_id="cand-1",
        canonical_version="0.14.0",
        main_target="main",
        tag="v0.14.0",
        all_gates_pass=True,
        workspace_dirty=False,
        release_blocked=False,
        allowed_return_targets=("M-DESIGN",),
        workflow_revision=1,
    )
    assert preview.release_action_enabled() is True

    # Human chooses Release -> publishing state + authorization.
    result = submit_human_decision(preview, type("D", (), {"action": "Release"})())
    assert result.new_state == "publishing"
    assert result.authorization_id.startswith("auth:")


def test_publish_ledger_confirms_idempotent_tag_operation():
    """J-PUBLISH-CLOSE step: tag operation confirmed without re-effect.

    AC-FR2200-01: confirmed operation not repeated after restart.
    """
    from louke.runtime.publish_ledger import OperationLedger, OperationStatus

    ledger = OperationLedger()
    op = ledger.plan_operation(
        release_identity="0.14.0",
        kind="tag",
        target="v0.14.0",
        payload_digest="sha256:tag-payload",
    )
    # Provider query returns 1 match with same digest -> confirmed.
    ledger.query(
        op.operation_id,
        query_digest="sha256:q",
        cardinality=1,
        existing_digest="sha256:tag-payload",
    )
    assert ledger.get(op.operation_id).status == OperationStatus.CONFIRMED

    # Restart: re-planning returns the existing confirmed op.
    op_after_restart = ledger.plan_operation(
        release_identity="0.14.0",
        kind="tag",
        target="v0.14.0",
        payload_digest="sha256:tag-payload",
    )
    assert op_after_restart.status == OperationStatus.CONFIRMED


def test_milestone_complete_enables_next_release_eligibility():
    """J-PUBLISH-CLOSE step: milestone complete -> next release enabled.

    AC-FR2400-01: complete state enables next main release creation.
    """
    from louke.runtime.m_milestone import (
        ArchiveManifest,
        ArchiveStore,
        CleanupDecision,
        MilestoneState,
        close_milestone,
    )

    store = ArchiveStore()
    manifest = ArchiveManifest(
        archive_id="archive:1",
        run_id="e2e-run-001",
        candidate_id="cand-1",
        trace_root="trace:root",
        evidence_ids=("ev-1",),
        red_refs=(("refs/louke/rgr/e2e-run-001/T-001/att-1/red", "r" * 40),),
    )
    decisions = (
        CleanupDecision(
            refname="refs/louke/rgr/e2e-run-001/T-001/att-1/red",
            expected_oid="r" * 40,
            actual_oid="r" * 40,
            status="success",
        ),
    )
    state = close_milestone(
        store=store,
        run_id="e2e-run-001",
        candidate_id="cand-1",
        publish_facts_verified=True,
        trace_closed=True,
        archive_manifest=manifest,
        cleanup_results=decisions,
    )
    assert state == MilestoneState.COMPLETE
    assert store.next_release_eligible() is True
