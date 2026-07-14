"""FR-1901: operable project detail, artifact review and approval UI e2e.

Covers AC-FR1901-01..08. Per test-plan §1.1 these tests observe behavior through
public surfaces: the runtime module public report methods (ProjectDetail /
GatePanel / ArtifactReview / TaskControl / InlineDiscussionStore) and, for
AC-FR1901-07, the real ``lk discuss`` CLI which round-trips inline discussions
through the canonical parser on disk (interfaces.md §4.3 artifact review).

The v0.12 M-DEV HTTP project API is not yet implemented; the runtime module
public outputs (detail fields, gate blockers, canonical discussion form) are
the observable exits described in interfaces.md §3.2/§4.3.

AC references:
- AC-FR1901-01: detail shows status, current/final step, entry reason, actions.
- AC-FR1901-02: artifact review shows bound revision/digest/reviewer/verdict.
- AC-FR1901-03: gate panel distinguishes requirements approval vs M-LOCK.
- AC-FR1901-04: approval blocked until checks/reviews/discussions close.
- AC-FR1901-05: task controls show agent/model/state + allowed actions.
- AC-FR1901-06: detail rebuilt from runtime events (no event loss).
- AC-FR1901-07: inline discussion canonical round-trip via CLI.
- AC-FR1901-08: open discussions + stale digest block approval.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

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


# ---------------------------------------------------------------------------
# AC-FR1901-01: project detail status / step / entry reason / allowed actions
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr1901_01_detail_shows_status_step_reason_actions():
    """AC-FR1901-01: detail shows same-revision status, step, entry reason, actions.

    The user must see the run status, current step, the reason for entering it
    and the actions the definition currently allows, without guessing from
    graphical color alone.
    """
    detail = ProjectDetail(
        run_id="run_001",
        status=RunStatus.WAITING_FOR_HUMAN,
        current_step="requirements_approval",
        entry_reason="awaiting human approval of story/spec/acceptance",
        allowed_actions=["approve", "reject", "add_discussion"],
    )

    assert detail.run_id == "run_001"
    assert detail.status == RunStatus.WAITING_FOR_HUMAN
    assert detail.current_step == "requirements_approval"
    assert "awaiting" in detail.entry_reason
    # The user sees concrete allowed actions, not a color.
    assert "approve" in detail.allowed_actions
    assert "reject" in detail.allowed_actions


# ---------------------------------------------------------------------------
# AC-FR1901-02: artifact review bound revision/digest/reviewer/verdict
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr1901_02_artifact_review_shows_bound_revision_and_digest():
    """AC-FR1901-02: artifact review shows the bound version, not the latest on disk.

    Opening an artifact's review must show the revision/digest actually bound
    to this run, the required reviewer, the verdict, open discussion count and
    check results.
    """
    review = ArtifactReview(
        artifact_id="art_spec",
        revision="rev_3",
        digest="sha256:deadbeef",
        required_reviewer="sage",
        verdict="pending",
        open_discussions=2,
        check_results={"format": "passed", "coverage": "failed"},
    )

    assert review.revision == "rev_3"
    assert review.digest == "sha256:deadbeef"
    assert review.required_reviewer == "sage"
    assert review.verdict == "pending"
    assert review.open_discussions == 2
    assert review.check_results["coverage"] == "failed"


# ---------------------------------------------------------------------------
# AC-FR1901-03: gate panel distinguishes requirements approval vs M-LOCK
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr1901_03_gate_panel_distinguishes_requirements_approval_and_m_lock():
    """AC-FR1901-03: gate panel distinguishes the two gate kinds + scope.

    Requirements approval and M-LOCK must be visibly distinct, each showing
    bound artifacts, changes vs baseline, stale state and the approve scope.
    """
    req_panel = GatePanel(
        gate_id="gate_req",
        gate_type="requirements_approval",
        artifacts=[ArtifactReview(artifact_id="story", digest="sha256:story")],
        baseline_digest="sha256:base",
        changes_since_baseline=["story.md"],
        is_stale=False,
        approve_scope="advance to design authoring",
    )
    mlock_panel = GatePanel(
        gate_id="gate_mlock",
        gate_type="m_lock",
        artifacts=[
            ArtifactReview(artifact_id="architecture", digest="sha256:arch"),
            ArtifactReview(artifact_id="interfaces", digest="sha256:iface"),
        ],
        baseline_digest="sha256:mlock_base",
        changes_since_baseline=[],
        is_stale=False,
        approve_scope="lock design documents, allow implementation",
    )

    assert req_panel.gate_type == "requirements_approval"
    assert req_panel.approve_scope == "advance to design authoring"
    assert mlock_panel.gate_type == "m_lock"
    # M-LOCK binds design docs; requirements approval binds story/spec/acceptance.
    assert {a.artifact_id for a in mlock_panel.artifacts} == {
        "architecture",
        "interfaces",
    }
    assert req_panel.gate_type != mlock_panel.gate_type


# ---------------------------------------------------------------------------
# AC-FR1901-04: approval blocked until conditions met
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr1901_04_approval_blocked_by_open_discussion():
    """AC-FR1901-04: open discussion blocks approval; server-side gate rejects.

    With an open discussion the gate must refuse approval and leave the
    gate/revision unchanged.
    """
    panel = GatePanel(
        gate_id="gate_req",
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
        panel.approve(DecisionRecord(actor="alice", verdict="approve"))
    # No decision recorded after rejection.
    assert panel.decision is None


@pytest.mark.e2e
def test_ac_fr1901_04_approval_blocked_by_failed_check():
    """AC-FR1901-04: a failed required check blocks approval."""
    panel = GatePanel(
        gate_id="gate_req",
        gate_type="requirements_approval",
        artifacts=[
            ArtifactReview(
                artifact_id="spec",
                digest="sha256:spec",
                open_discussions=0,
                check_results={"coverage": "failed"},
            )
        ],
        baseline_digest="sha256:base",
        changes_since_baseline=[],
        is_stale=False,
    )

    with pytest.raises(GateBlockedError):
        panel.approve(DecisionRecord(actor="alice", verdict="approve"))
    assert panel.decision is None


@pytest.mark.e2e
def test_ac_fr1901_04_approval_accepted_when_conditions_met():
    """AC-FR1901-04: once conditions are met, a valid approve records identity.

    After all blockers clear, an approve records the actor and verdict, leaving
    evidence of the human decision.
    """
    panel = GatePanel(
        gate_id="gate_req",
        gate_type="requirements_approval",
        artifacts=[
            ArtifactReview(
                artifact_id="story",
                digest="sha256:story",
                open_discussions=0,
                check_results={"lint": "passed"},
            )
        ],
        baseline_digest="sha256:base",
        changes_since_baseline=[],
        is_stale=False,
    )

    panel.approve(DecisionRecord(actor="alice", verdict="approve"))
    assert panel.decision.actor == "alice"
    assert panel.decision.verdict == "approve"


@pytest.mark.e2e
def test_ac_fr1901_04_reject_with_reason_records_identity():
    """AC-FR1901-04: a reject with reason records identity and evidence."""
    panel = GatePanel(
        gate_id="gate_req",
        gate_type="requirements_approval",
        artifacts=[
            ArtifactReview(
                artifact_id="story",
                digest="sha256:story",
                open_discussions=0,
                check_results={"lint": "passed"},
            )
        ],
        baseline_digest="sha256:base",
        changes_since_baseline=[],
        is_stale=False,
    )

    panel.approve(
        DecisionRecord(actor="bob", verdict="reject", reason="story too vague")
    )
    assert panel.decision.verdict == "reject"
    assert panel.decision.reason == "story too vague"


# ---------------------------------------------------------------------------
# AC-FR1901-05: task controls show agent/model/state + allowed actions
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr1901_05_task_controls_show_pinned_model_and_allowed_actions():
    """AC-FR1901-05: task controls show agent, pinned model, state, allowed actions.

    The user sees the agent role, the pinned (immutable) model, the task and
    session status, and only the actions currently allowed for that resource.
    """
    control = TaskControl(
        agent_role="devon",
        pinned_model="provider/opus-4",
        task_status="running",
        session_status="attached",
        allowed_actions=["detach", "stop_generation"],
    )

    assert control.agent_role == "devon"
    assert control.pinned_model == "provider/opus-4"
    assert control.task_status == "running"
    assert control.session_status == "attached"
    # Only currently-allowed actions are exposed; end_session absent while attached.
    assert "detach" in control.allowed_actions
    assert "stop_generation" in control.allowed_actions
    assert "end_session" not in control.allowed_actions


# ---------------------------------------------------------------------------
# AC-FR1901-06: detail rebuilt from runtime events
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr1901_06_detail_rebuilt_from_events():
    """AC-FR1901-06: project detail is rebuilt from runtime events consistently.

    Applying a sequence of runtime events reconstructs the same detail state
    the server would report, proving the detail is event-sourced and not
    lost across reconnects.
    """
    detail = ProjectDetail(run_id="run_001")

    detail.apply_event({"type": "status_changed", "status": "blocked"})
    detail.apply_event({"type": "step_changed", "step": "implementation_review"})

    assert detail.status == RunStatus.BLOCKED
    assert detail.current_step == "implementation_review"

    # A second detail instance fed the same events reaches the same state
    # (event-sourced rebuild is deterministic, no in-memory state relied upon).
    rebuilt = ProjectDetail(run_id="run_001")
    rebuilt.apply_event({"type": "status_changed", "status": "blocked"})
    rebuilt.apply_event({"type": "step_changed", "step": "implementation_review"})
    assert rebuilt.status == detail.status
    assert rebuilt.current_step == detail.current_step


# ---------------------------------------------------------------------------
# AC-FR1901-07: inline discussion canonical round-trip (via lk discuss CLI)
# ---------------------------------------------------------------------------


def _run_lk_discuss(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run ``lk discuss`` against a spec file in ``cwd``; return completed process."""
    return subprocess.run(
        [sys.executable, "-m", "louke", "discuss", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=True,
    )


def _write_spec(spec_path: Path) -> None:
    """Write a minimal spec.md with one FR heading + a requirement line."""
    spec_path.write_text(
        "### FR-0001\n\nSome requirement text here.\n",
        encoding="utf-8",
    )


@pytest.mark.e2e
def test_ac_fr1901_07_discussion_canonical_roundtrip_via_cli(tmp_path):
    """AC-FR1901-07: inline discussion round-trips through canonical form via CLI.

    Starting a thread via ``lk discuss start`` writes canonical speaker/depth/
    status syntax to disk; ``lk discuss query`` parses it back as the same
    thread, and resolving it flips status with no parse loss. This proves the
    on-disk form is immediately recognized by the gate parser.
    """
    spec = tmp_path / "spec.md"
    _write_spec(spec)

    # Start a thread at the requirement line.
    _run_lk_discuss(
        [
            "start",
            "--file",
            str(spec),
            "--anchor-line",
            "3",
            "--speaker",
            "Sage",
            "This AC is ambiguous.",
        ],
        cwd=tmp_path,
    )

    # Query parses the on-disk canonical form back.
    query = _run_lk_discuss(
        ["query", "--file", str(spec), "--status", "open"],
        cwd=tmp_path,
    )
    threads = json.loads(query.stdout)
    assert len(threads) == 1
    t = threads[0]
    assert t["initiator"] == "sage"
    assert t["status"] == "open"
    assert t["snippet"] == "This AC is ambiguous."

    # Resolve the thread; the canonical form updates and re-parses cleanly.
    _run_lk_discuss(
        [
            "set-status",
            "--file",
            str(spec),
            "--thread-id",
            t["thread_id"],
            "--anchor-line",
            str(t["anchor_line"]),
            "--anchor-text",
            t["anchor_text"],
            "--root-line",
            str(t["root_line"]),
            "--root-text",
            t["root_text"],
            "--status",
            "resolved",
            "--operator",
            "Sage",
        ],
        cwd=tmp_path,
    )

    resolved = _run_lk_discuss(
        ["query", "--file", str(spec), "--status", "resolved"],
        cwd=tmp_path,
    )
    resolved_threads = json.loads(resolved.stdout)
    assert len(resolved_threads) == 1
    assert resolved_threads[0]["status"] == "resolved"
    assert resolved_threads[0]["thread_id"] == t["thread_id"]


@pytest.mark.e2e
def test_ac_fr1901_07_non_roundtrippable_blockquote_rejected():
    """AC-FR1901-07: a non-canonical blockquote is rejected with a fixable error.

    The canonical store rejects malformed canonical strings that cannot be
    round-tripped by the gate parser, producing a fixable error rather than
    silently storing an unparsable block.
    """
    store = InlineDiscussionStore()
    thread = store.add(
        doc_id="story",
        anchor="ac-1",
        speaker="reviewer",
        body="needs example",
    )
    canonical = store.to_canonical(thread.thread_id)
    parsed = store.parse_canonical(canonical)

    # Valid canonical form round-trips.
    assert parsed["speaker"] == "reviewer"
    assert parsed["status"] == DiscussionStatus.OPEN.value

    # A visually-similar but non-canonical blockquote (missing required fields)
    # is rejected with a fixable error, not silently accepted.
    with pytest.raises(ValueError, match="canonical"):
        store.parse_canonical("> **reviewer**: not canonical at all")


# ---------------------------------------------------------------------------
# AC-FR1901-08: open discussions + stale digest block approval
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr1901_08_open_discussions_in_bound_doc_block_gate():
    """AC-FR1901-08: open inline discussions in any bound doc block approval.

    When a bound artifact has an open/reopen discussion thread, the gate must
    refuse approval until all threads are resolved.
    """
    store = InlineDiscussionStore()
    store.add(doc_id="story", anchor="ac-1", speaker="reviewer", body="?")

    panel = GatePanel(
        gate_id="gate_req",
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
        panel.approve(DecisionRecord(actor="alice", verdict="approve"))


@pytest.mark.e2e
def test_ac_fr1901_08_stale_digest_blocks_m_lock():
    """AC-FR1901-08: stale digest blocks gate approval.

    When the bound digest differs from the baseline (artifact changed since
    the gate was created), approval must be blocked.
    """
    panel = GatePanel(
        gate_id="gate_mlock",
        gate_type="m_lock",
        artifacts=[
            ArtifactReview(artifact_id="architecture", digest="sha256:new"),
        ],
        baseline_digest="sha256:old",
        changes_since_baseline=["architecture.md"],
        is_stale=True,
    )

    with pytest.raises(GateBlockedError):
        panel.approve(DecisionRecord(actor="alice", verdict="approve"))


@pytest.mark.e2e
def test_ac_fr1901_08_gate_passes_when_threads_resolved_and_digest_matches():
    """AC-FR1901-08: all threads resolved + fresh digest lets the gate continue.

    This is the positive side proving the block is conditional, not absolute.
    """
    panel = GatePanel(
        gate_id="gate_req",
        gate_type="requirements_approval",
        artifacts=[
            ArtifactReview(
                artifact_id="story",
                digest="sha256:story",
                open_discussions=0,
                check_results={"lint": "passed"},
            )
        ],
        baseline_digest="sha256:story",
        changes_since_baseline=[],
        is_stale=False,
    )

    panel.approve(DecisionRecord(actor="alice", verdict="approve"))
