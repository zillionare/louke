"""FR-1901: operable project detail, artifact review and approval UI.

AC references:
- AC-FR1901-01: project detail shows run status, current/final step, entry
  reason and allowed actions.
- AC-FR1901-02: artifacts/evidence show bound revision, digest, required
  reviewer, verdict, open discussions and check results.
- AC-FR1901-03: gate panel distinguishes requirements approval vs M-LOCK,
  shows bound artifacts/digest, changes vs baseline, stale status and
  approve/reject scope.
- AC-FR1901-04: approval is blocked until required checks/reviews/discussions
  close; valid approve/reject records identity and evidence.
- AC-FR1901-05: task controls display agent, pinned model, task/session state
  and only currently allowed actions.
- AC-FR1901-06: project list/detail rebuild from runtime events; no events
  lost across browser reconnects.
- AC-FR1901-07: inline discussions are persisted in canonical form and
  parsed by the gate parser.
- AC-FR1901-08: open inline discussions in bound docs block gate approval;
  gate continues only when all threads resolved and digests match.
"""

from __future__ import annotations

import pytest

from louke.runtime.project_detail import (
    ArtifactReview,
    DecisionRecord,
    DiscussionStatus,
    GateBlockedError,
    GatePanel,
    InlineDiscussionStore,
    ProjectDetail,
    RunStatus,
    TaskControl,
)


# -- AC-FR1901-01 -------------------------------------------------------------


def test_ac_fr1901_01_project_detail_shows_status_and_actions():
    """AC-FR1901-01: detail shows status, current step and allowed actions."""
    detail = ProjectDetail(
        run_id="run_001",
        status=RunStatus.WAITING_FOR_HUMAN,
        current_step="requirements_approval",
        entry_reason="awaiting human approval",
        allowed_actions=["approve", "reject", "add_discussion"],
    )

    assert detail.run_id == "run_001"
    assert detail.status == RunStatus.WAITING_FOR_HUMAN
    assert detail.current_step == "requirements_approval"
    assert "approve" in detail.allowed_actions


# -- AC-FR1901-02 -------------------------------------------------------------


def test_ac_fr1901_02_artifact_review_shows_bound_revision():
    """AC-FR1901-02: artifact review shows bound revision/digest/reviewer."""
    review = ArtifactReview(
        artifact_id="art_001",
        revision="v1.2",
        digest="sha256:abc",
        required_reviewer="human_lead",
        verdict="pending",
        open_discussions=1,
        check_results={"lint": "passed"},
    )

    assert review.revision == "v1.2"
    assert review.digest == "sha256:abc"
    assert review.open_discussions == 1


# -- AC-FR1901-03 -------------------------------------------------------------


def test_ac_fr1901_03_gate_panel_distinguishes_gate_types():
    """AC-FR1901-03: gate panel distinguishes requirements approval and M-LOCK."""
    panel = GatePanel(
        gate_id="gate_001",
        gate_type="requirements_approval",
        artifacts=[ArtifactReview(artifact_id="story", digest="sha256:story")],
        baseline_digest="sha256:baseline",
        changes_since_baseline=["story.md"],
        is_stale=False,
        approve_scope="advance to design",
    )

    assert panel.gate_type == "requirements_approval"
    assert panel.approve_scope == "advance to design"

    mlock = GatePanel(
        gate_id="gate_002",
        gate_type="m_lock",
        artifacts=[ArtifactReview(artifact_id="architecture", digest="sha256:arch")],
        baseline_digest="sha256:base",
        changes_since_baseline=["architecture.md"],
        is_stale=True,
        approve_scope="lock design documents",
    )

    assert mlock.gate_type == "m_lock"
    assert mlock.is_stale is True


# -- AC-FR1901-04 -------------------------------------------------------------


def test_ac_fr1901_04_approval_blocked_until_conditions_met():
    """AC-FR1901-04: approval blocked until checks/reviews/discussions close."""
    panel = GatePanel(
        gate_id="gate_001",
        gate_type="requirements_approval",
        artifacts=[
            ArtifactReview(
                artifact_id="story",
                digest="sha256:story",
                open_discussions=1,
                check_results={"lint": "passed"},
            )
        ],
        baseline_digest="sha256:base",
        changes_since_baseline=[],
        is_stale=False,
    )

    with pytest.raises(GateBlockedError):
        panel.approve(decision=DecisionRecord(actor="alice", verdict="approve"))

    resolved_artifact = ArtifactReview(
        artifact_id="story",
        digest="sha256:story",
        open_discussions=0,
        check_results={"lint": "passed"},
    )
    panel_clean = GatePanel(
        gate_id="gate_001",
        gate_type="requirements_approval",
        artifacts=[resolved_artifact],
        baseline_digest="sha256:base",
        changes_since_baseline=[],
        is_stale=False,
    )
    panel_clean.approve(decision=DecisionRecord(actor="alice", verdict="approve"))
    assert panel_clean.decision.verdict == "approve"


# -- AC-FR1901-05 -------------------------------------------------------------


def test_ac_fr1901_05_task_controls_show_allowed_actions():
    """AC-FR1901-05: task controls show agent/model/state and allowed actions."""
    control = TaskControl(
        agent_role="devon",
        pinned_model="gpt-4",
        task_status="running",
        session_status="attached",
        allowed_actions=["detach", "stop_generation"],
    )

    assert control.agent_role == "devon"
    assert control.pinned_model == "gpt-4"
    assert control.allowed_actions == ["detach", "stop_generation"]


# -- AC-FR1901-06 -------------------------------------------------------------


def test_ac_fr1901_06_project_detail_rebuilt_from_events():
    """AC-FR1901-06: detail state is rebuilt from runtime events."""
    detail = ProjectDetail(run_id="run_001")
    detail.apply_event({"type": "status_changed", "status": "blocked"})
    detail.apply_event({"type": "step_changed", "step": "review"})

    assert detail.status == RunStatus.BLOCKED
    assert detail.current_step == "review"


# -- AC-FR1901-07 -------------------------------------------------------------


def test_ac_fr1901_07_inline_discussion_canonical_roundtrip():
    """AC-FR1901-07: inline discussions round-trip in canonical form."""
    store = InlineDiscussionStore()
    thread = store.add(
        doc_id="story",
        anchor="ac-1",
        speaker="reviewer",
        body="This AC is ambiguous.",
    )

    assert thread.speaker == "reviewer"
    assert thread.depth == 1
    assert thread.status == DiscussionStatus.OPEN

    canonical = store.to_canonical(thread.thread_id)
    parsed = store.parse_canonical(canonical)
    assert parsed["speaker"] == "reviewer"
    assert parsed["status"] == "open"


# -- AC-FR1901-08 -------------------------------------------------------------


def test_ac_fr1901_08_open_discussions_block_gate():
    """AC-FR1901-08: open inline discussions in bound docs block approval."""
    store = InlineDiscussionStore()
    store.add(doc_id="story", anchor="ac-1", speaker="reviewer", body="?")

    panel = GatePanel(
        gate_id="gate_001",
        gate_type="requirements_approval",
        artifacts=[
            ArtifactReview(
                artifact_id="story",
                digest="sha256:story",
                open_discussions=1,
            )
        ],
        baseline_digest="sha256:base",
        changes_since_baseline=[],
        is_stale=False,
    )

    with pytest.raises(GateBlockedError):
        panel.approve(decision=DecisionRecord(actor="alice", verdict="approve"))


def test_ac_fr1901_08_stale_digest_blocks_gate():
    """AC-FR1901-08: stale digest blocks gate approval."""
    panel = GatePanel(
        gate_id="gate_001",
        gate_type="m_lock",
        artifacts=[
            ArtifactReview(
                artifact_id="architecture",
                digest="sha256:new",
            )
        ],
        baseline_digest="sha256:old",
        changes_since_baseline=["architecture.md"],
        is_stale=True,
    )

    with pytest.raises(GateBlockedError):
        panel.approve(decision=DecisionRecord(actor="alice", verdict="approve"))
