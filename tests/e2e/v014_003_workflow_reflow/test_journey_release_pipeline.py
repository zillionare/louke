"""E2E journey: release pipeline (candidate -> CI -> Prism -> Human ->
publish -> milestone).

Covers AC IDs:
- AC-FR1400-01 (Release candidate freeze)
- AC-FR1500-01 (Local quality chain)
- AC-FR1600-01 (Artifact version verification)
- AC-FR1700-01 (GitHub candidate CI)
- AC-FR1800-01 (Candidate overall Prism review)
- AC-FR2100-01 (M-RELEASE preview & Human gate)
- AC-FR2200-01 (M-PUBLISH operation ledger)
- AC-FR2300-01 (Post-publish verification)
- AC-FR2400-01 (M-MILESTONE trace/archive/cleanup)

NORMAL PATH: candidate freeze -> local+CI PASS -> Prism PASS -> Human
Release -> publish confirmed -> post-publish verified -> milestone
complete.
"""
# AC-FR1400-01, AC-FR1700-01, AC-FR2100-01, AC-FR2400-01

from __future__ import annotations

import pytest

pytestmark = pytest.mark.v014_003_e2e


def test_release_pipeline_normal_path():
    """J-TEST-VERIFY -> J-PUBLISH-CLOSE: candidate -> release -> milestone."""
    from louke.runtime.release_candidate import (
        CandidateStore,
        DependencyManifest,
        freeze_candidate,
    )
    from louke.runtime.local_quality_chain import (
        QualityChainGate,
        QualityGateResult,
    )
    from louke.runtime.artifact_version import ArtifactEvidence, ArtifactVerifier
    from louke.runtime.github_ci import (
        GitHubCIGate,
        JobResult,
        SuiteCoverage,
    )
    from louke.runtime.candidate_prism_review import (
        CandidatePrismVerdict,
        CandidateReviewStore,
        attach_candidate_review,
        can_enter_m_security,
    )
    from louke.runtime.m_release_preview import (
        build_preview,
        submit_human_decision,
        HumanDecision,
    )
    from louke.runtime.publish_ledger import OperationLedger, OperationStatus
    from louke.runtime.post_publish_recovery import (
        OutletVerification,
        PublishFact,
        verify_post_publish,
    )
    from louke.runtime.m_milestone import (
        ArchiveManifest,
        ArchiveStore,
        CleanupDecision,
        MilestoneState,
        close_milestone,
    )

    # 1. Candidate freeze
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
        run_id="e2e-run-002",
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

    # 2. Local quality chain: all gates PASS
    quality_gate = QualityChainGate()
    gates = [
        QualityGateResult(name=n, status="pass")
        for n in (
            "format",
            "lint",
            "static",
            "type",
            "precommit-drift",
            "precommit-all-files",
            "rgr-lineage",
            "history-unit",
            "integration",
            "e2e",
            "regression",
            "ac-trace",
            "skip-policy",
            "anti-pattern",
            "docs",
            "migration",
            "compat",
            "build",
        )
    ]
    quality_report = quality_gate.evaluate(cand.candidate_id, gates)
    assert quality_report.status == "pass"

    # 3. Artifact version: wheel + sdist match canonical version
    verifier = ArtifactVerifier(canonical_version="0.14.0")
    artifacts = [
        ArtifactEvidence(
            artifact_id=f"art-{kind}",
            kind=kind,
            path=f"dist/louke-0.14.0-{kind}",
            digest=f"sha256:{kind}",
            size=1024,
            stage="installed_runtime_verified",
            extracted_version="0.14.0",
            install_environment="clean-venv",
            runtime_version="0.14.0",
        )
        for kind in ("wheel", "sdist")
    ]
    art_report = verifier.verify(cand.candidate_id, artifacts)
    assert art_report.status == "pass"

    # 4. GitHub CI: all required jobs success + suite coverage complete
    required_jobs = (
        "quality",
        "workflow-contract",
        "ac-trace",
        "build-artifacts",
        "artifact-verify",
        "unit",
        "integration",
        "e2e-standin",
        "ci-e2e",
        "security",
    )
    ci_gate = GitHubCIGate(
        required_jobs=required_jobs,
        required_suites=("tests/unit", "tests/integration", "tests/e2e"),
    )
    ci_report = ci_gate.evaluate(
        candidate_oid="g" * 40,
        commit_oid="g" * 40,
        jobs=[JobResult(name=n, status="success") for n in required_jobs],
        coverage=SuiteCoverage(
            required_suites=("tests/unit", "tests/integration", "tests/e2e"),
            executed_suites=("tests/unit", "tests/integration", "tests/e2e"),
            illegal_skips=(),
            complete=True,
        ),
        required_check_status="success",
    )
    assert ci_report.status == "pass"

    # 5. Candidate Prism review: PASS -> can enter M-SECURITY
    review_store = CandidateReviewStore()
    attach_candidate_review(
        review_store,
        CandidatePrismVerdict(
            review_id="rev-cand-001",
            candidate_id=cand.candidate_id,
            evidence_snapshot_digest="sha256:snapshot",
            verdict="PASS",
        ),
    )
    assert (
        can_enter_m_security(
            review_store,
            cand.candidate_id,
            local_passed=True,
            ci_passed=True,
        )
        is True
    )

    # 6. Human Release -> publishing + authorization
    preview = build_preview(
        candidate_id=cand.candidate_id,
        canonical_version="0.14.0",
        main_target="main",
        tag="v0.14.0",
        all_gates_pass=True,
        workspace_dirty=False,
        release_blocked=False,
        allowed_return_targets=("M-DESIGN",),
        workflow_revision=1,
    )
    decision = submit_human_decision(
        preview,
        HumanDecision(action="Release"),
    )
    assert decision.new_state == "publishing"
    assert decision.authorization_id

    # 7. Publish ledger: tag operation confirmed
    ledger = OperationLedger()
    op = ledger.plan_operation(
        release_identity="0.14.0",
        kind="tag",
        target="v0.14.0",
        payload_digest="sha256:tag-payload",
    )
    ledger.query(
        op.operation_id,
        query_digest="sha256:q",
        cardinality=1,
        existing_digest="sha256:tag-payload",
    )
    assert ledger.get(op.operation_id).status == OperationStatus.CONFIRMED

    # 8. Post-publish verification: all facts + outlets match
    facts = [
        PublishFact(name=n, target_oid="g" * 40, actual_oid="g" * 40)
        for n in ("main", "tag", "release", "artifacts")
    ]
    outlets = [
        OutletVerification(
            name=n,
            outlet=cmd,
            value="0.14.0",
            passed=True,
        )
        for n, cmd in (
            ("install", "pip install louke==0.14.0"),
            ("runtime", "lk --version"),
            ("smoke", "lk health"),
        )
    ]
    pp_report = verify_post_publish("g" * 40, facts, outlets)
    assert pp_report.status == "pass"
    assert pp_report.new_state == "completed"

    # 9. Milestone complete -> next release enabled
    archive_store = ArchiveStore()
    archive_manifest = ArchiveManifest(
        archive_id="archive:1",
        run_id="e2e-run-002",
        candidate_id=cand.candidate_id,
        trace_root="trace:root",
        evidence_ids=("ev-1",),
        red_refs=(("refs/louke/rgr/e2e-run-002/T-001/att-1/red", "r" * 40),),
    )
    cleanup = (
        CleanupDecision(
            refname="refs/louke/rgr/e2e-run-002/T-001/att-1/red",
            expected_oid="r" * 40,
            actual_oid="r" * 40,
            status="success",
        ),
    )
    state = close_milestone(
        store=archive_store,
        run_id="e2e-run-002",
        candidate_id=cand.candidate_id,
        publish_facts_verified=True,
        trace_closed=True,
        archive_manifest=archive_manifest,
        cleanup_results=cleanup,
    )
    assert state == MilestoneState.COMPLETE
    assert archive_store.next_release_eligible() is True
