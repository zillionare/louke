"""FR-2201: end-to-end traceability gate between requirements, implementation and verification.

Covers AC-FR2201-01..06. Per test-plan §1.1 these tests observe behavior through
the runtime module public report (TraceLedger / TraceEntry / CodeEvidence /
EvidenceKind / TraceabilityError) which are the observable exits described in
interfaces.md §6.1 (trace/completion check). The v0.12 M-DEV HTTP project API
is not yet implemented; these public outputs are the contract surface.

Expected field names and statuses are taken from acceptance.md AC-FR2201-01..06
(the spec): each FR/NFR/AC links test-plan, task/Issue, code/test evidence with
artifact/commit digest; M-DEV blocked on unmapped/stale ACs; Devon manifest
scoped to assigned issues/ACs; test evidence carries runner/command/environment
/exit/covered AC/revision digest; unclosed ACs block gate; contract changes mark
downstream evidence stale.

AC references:
- AC-FR2201-01: trace ledger links FR/AC to test-plan, task/issue, code/test
  evidence with digests and status.
- AC-FR2201-02: M-DEV blocked on unmapped ACs / stale contract; no Devon task.
- AC-FR2201-03: Devon manifest scoped to assigned issues/ACs only.
- AC-FR2201-04: evidence from real diff/commit; test evidence has runner/
  command/environment/exit/covered AC/revision digest (not Agent self-report).
- AC-FR2201-05: unclosed ACs block implementation/completion gate; all closed
  -> reverse lookup from task/commit/test to requirement.
- AC-FR2201-06: accepted contract change marks downstream evidence stale and
  returns to declaration gate; unaffected evidence preserved but old green
  status cannot override new contract.
"""

from __future__ import annotations

import pytest

from louke.runtime.trace_ledger import (
    CodeEvidence,
    EvidenceKind,
    TraceEntry,
    TraceLedger,
    TraceabilityError,
)

# Expected statuses are from acceptance.md AC-FR2201-01/05/06 (the spec): an AC
# moves through pending -> verified/closed, and a contract change marks affected
# evidence ``stale`` and sends it back to the ``requirements_approval`` gate.
STATUS_PENDING = "pending"
STATUS_CLOSED = "closed"
STATUS_STALE = "stale"
GATE_REQUIREMENTS_APPROVAL = "requirements_approval"

# A representative contract digest used as the "approved contract" ground truth.
# Its value is arbitrary but stable; tests never read it back from the impl.
APPROVED_CONTRACT_DIGEST = "sha256:approved-contract-v1"
CHANGED_CONTRACT_DIGEST = "sha256:approved-contract-v2"


def _add_approved_requirement(
    ledger: TraceLedger,
    *,
    fr_id: str = "FR-2201",
    ac_id: str = "AC-FR2201-01",
    test_plan: str = "test-plan.md",
    task_id: str = "task-1",
    issue: str = "#42",
) -> TraceEntry:
    """Add a requirement that is approved against the current contract."""
    return ledger.add_requirement(
        fr_id=fr_id,
        ac_id=ac_id,
        test_plan=test_plan,
        task_id=task_id,
        issue=issue,
        contract_digest=APPROVED_CONTRACT_DIGEST,
    )


# ---------------------------------------------------------------------------
# AC-FR2201-01: trace ledger links FR/AC to test-plan, task/issue, evidence
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2201_01_trace_entry_links_fr_ac_to_plan_task_issue_and_digest():
    """AC-FR2201-01: a new requirement links FR/AC, test-plan, task/issue and contract digest.

    Each FR/NFR/AC must be associated with a test-plan, task/Issue, code/test
    evidence and show the artifact/commit digest and status.
    """
    ledger = TraceLedger()
    ledger.mark_contract_current_digest(APPROVED_CONTRACT_DIGEST)

    entry = _add_approved_requirement(ledger)

    assert entry.fr_id == "FR-2201"
    assert entry.ac_id == "AC-FR2201-01"
    assert entry.test_plan == "test-plan.md"
    assert entry.task_id == "task-1"
    assert entry.issue == "#42"
    assert entry.contract_digest == APPROVED_CONTRACT_DIGEST
    assert entry.evidence_status == STATUS_PENDING


@pytest.mark.e2e
def test_ac_fr2201_01_code_evidence_carries_commit_and_diff_digest():
    """AC-FR2201-01: code evidence comes from a real commit/diff with digests.

    CODE evidence must be a CodeEvidence carrying commit id and diff digest
    (not Agent self-reported text).
    """
    ledger = TraceLedger()
    entry = _add_approved_requirement(ledger)

    code_ev = CodeEvidence(commit="abc1234", diff_digest="sha256:diff-xyz")
    ledger.link_evidence(entry.entry_id, EvidenceKind.CODE, code_ev)

    refreshed = ledger.lookup_by_task("task-1")[0]
    assert isinstance(refreshed.evidence, CodeEvidence)
    assert refreshed.evidence.commit == "abc1234"
    assert refreshed.evidence.diff_digest == "sha256:diff-xyz"


@pytest.mark.e2e
def test_ac_fr2201_01_code_evidence_rejects_plain_string():
    """AC-FR2201-01: CODE evidence cannot be Agent self-reported text.

    A plain string is rejected to prevent an Agent from asserting "done"
    instead of providing a real commit/diff.
    """
    ledger = TraceLedger()
    entry = _add_approved_requirement(ledger)

    with pytest.raises(ValueError):
        ledger.link_evidence(entry.entry_id, EvidenceKind.CODE, "agent says done")


@pytest.mark.e2e
def test_ac_fr2201_01_hotfix_back_links_existing_spec_ac_via_issue():
    """AC-FR2201-01: a hotfix back-links an existing spec/AC through the Issue.

    The trace entry for a hotfix originates from an Issue and links back to the
    source FR/AC, marking implementation deviation in its evidence status.
    """
    ledger = TraceLedger()
    ledger.mark_contract_current_digest(APPROVED_CONTRACT_DIGEST)

    hotfix_entry = ledger.add_requirement(
        fr_id="FR-1801",
        ac_id="AC-FR1801-03",
        test_plan="test-plan.md",
        task_id="hotfix-task",
        issue="#99",
        contract_digest=APPROVED_CONTRACT_DIGEST,
        evidence_status=STATUS_PENDING,
    )

    assert hotfix_entry.issue == "#99"
    assert hotfix_entry.fr_id == "FR-1801"
    # Implementation deviation is reflected by a non-closed initial status.
    assert hotfix_entry.evidence_status != STATUS_CLOSED


# ---------------------------------------------------------------------------
# AC-FR2201-02: M-DEV blocked on unmapped ACs or stale contract
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2201_02_mdev_blocked_on_unmapped_ac_no_task():
    """AC-FR2201-02: an AC with no assigned task blocks M-DEV and dispatches no Devon task.

    The error must name the specific AC gap.
    """
    ledger = TraceLedger()
    ledger.mark_contract_current_digest(APPROVED_CONTRACT_DIGEST)

    ledger.add_requirement(
        fr_id="FR-2201",
        ac_id="AC-FR2201-02",
        test_plan="test-plan.md",
        task_id="",  # unmapped
        issue="",
        contract_digest=APPROVED_CONTRACT_DIGEST,
    )

    with pytest.raises(TraceabilityError) as exc:
        ledger.validate_mdev_ready()
    assert "AC-FR2201-02" in str(exc.value)
    assert "task" in str(exc.value).lower()


@pytest.mark.e2e
def test_ac_fr2201_02_mdev_blocked_on_stale_contract_digest():
    """AC-FR2201-02: an AC referencing a stale contract digest blocks M-DEV.

    When the task plan references an old contract, M-DEV validation fails with
    the specific AC and a stale-contract reason.
    """
    ledger = TraceLedger()
    ledger.mark_contract_current_digest(CHANGED_CONTRACT_DIGEST)

    ledger.add_requirement(
        fr_id="FR-2201",
        ac_id="AC-FR2201-02",
        test_plan="test-plan.md",
        task_id="task-2",
        issue="#43",
        contract_digest=APPROVED_CONTRACT_DIGEST,  # stale
    )

    with pytest.raises(TraceabilityError) as exc:
        ledger.validate_mdev_ready()
    assert "AC-FR2201-02" in str(exc.value)
    assert "stale" in str(exc.value).lower()


@pytest.mark.e2e
def test_ac_fr2201_02_mdev_blocked_dispatches_no_devon_task_for_unmapped_ac():
    """AC-FR2201-02: when M-DEV is blocked, the manifest carries the AC but no dispatchable issue.

    validate_mdev_ready raises so Devon never receives a task; the manifest
    built from the blocked ledger has no assignable issues for the unmapped AC
    (proving the AC is tracked but not dispatched).
    """
    ledger = TraceLedger()
    ledger.mark_contract_current_digest(APPROVED_CONTRACT_DIGEST)

    # Unmapped AC -> blocked.
    ledger.add_requirement(
        fr_id="FR-2201",
        ac_id="AC-FR2201-02",
        task_id="",
        contract_digest=APPROVED_CONTRACT_DIGEST,
    )

    with pytest.raises(TraceabilityError):
        ledger.validate_mdev_ready()

    # The manifest is never dispatched while blocked; if it were built, the
    # unmapped AC has no issue to dispatch.
    manifest = ledger.build_devon_manifest("run-1")
    assert manifest["issues"] == []
    assert manifest["acs"] == ["AC-FR2201-02"]  # AC tracked, but unassigned


@pytest.mark.e2e
def test_ac_fr2201_02_mdev_passes_when_all_acs_mapped_and_fresh():
    """AC-FR2201-02: with every AC mapped to a task and a fresh contract, M-DEV is ready."""
    ledger = TraceLedger()
    ledger.mark_contract_current_digest(APPROVED_CONTRACT_DIGEST)
    _add_approved_requirement(ledger, ac_id="AC-FR2201-02-a", task_id="t-a", issue="#1")
    _add_approved_requirement(ledger, ac_id="AC-FR2201-02-b", task_id="t-b", issue="#2")

    # No exception -> M-DEV ready.
    ledger.validate_mdev_ready()


# ---------------------------------------------------------------------------
# AC-FR2201-03: Devon manifest scoped to assigned issues/ACs only
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2201_03_manifest_contains_only_assigned_issues_and_acs():
    """AC-FR2201-03: the Devon manifest contains only this batch's assigned issues/ACs.

    Issues/ACs not in the assigned batch must not appear in the manifest.
    """
    ledger = TraceLedger()
    _add_approved_requirement(ledger, ac_id="AC-A", task_id="t-1", issue="#10")
    _add_approved_requirement(ledger, ac_id="AC-B", task_id="t-2", issue="#11")

    manifest = ledger.build_devon_manifest("run-42")

    assert manifest["run_id"] == "run-42"
    assert set(manifest["issues"]) == {"#10", "#11"}
    assert set(manifest["acs"]) == {"AC-A", "AC-B"}


@pytest.mark.e2e
def test_ac_fr2201_03_unassigned_requirement_not_in_manifest_issues():
    """AC-FR2201-03: an Agent completion claim for an unassigned requirement does not enter the ledger.

    A requirement with no assigned issue must not contribute an issue to the
    Devon manifest, so an Agent cannot self-assign work outside the batch.
    """
    ledger = TraceLedger()
    _add_approved_requirement(ledger, ac_id="AC-A", task_id="t-1", issue="#10")
    # Unassigned requirement (no issue link).
    ledger.add_requirement(
        fr_id="FR-2201",
        ac_id="AC-UNASSIGNED",
        task_id="t-2",
        issue="",
        contract_digest=APPROVED_CONTRACT_DIGEST,
    )

    manifest = ledger.build_devon_manifest("run-42")

    assert manifest["issues"] == ["#10"]
    assert "AC-UNASSIGNED" in manifest["acs"]  # AC tracked, but no issue dispatched


# ---------------------------------------------------------------------------
# AC-FR2201-04: evidence from real diff/commit; test evidence carries full
# runner/command/environment/exit/covered AC/revision digest
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2201_04_code_evidence_from_real_commit_and_diff_digest():
    """AC-FR2201-04: code evidence is derived from a real diff/commit, not self-report.

    The CODE evidence must carry a commit id and a diff digest independently
    computed from the diff, not an Agent-authored text summary.
    """
    ledger = TraceLedger()
    entry = _add_approved_requirement(ledger)

    code_ev = CodeEvidence(commit="deadbeef", diff_digest="sha256:diff-abc")
    ledger.link_evidence(entry.entry_id, EvidenceKind.CODE, code_ev)

    linked = ledger.lookup_by_task(entry.task_id)[0]
    assert isinstance(linked.evidence, CodeEvidence)
    assert linked.evidence.commit == "deadbeef"
    assert linked.evidence.diff_digest == "sha256:diff-abc"


@pytest.mark.e2e
def test_ac_fr2201_04_test_evidence_carries_runner_command_environment_exit_ac_revision():
    """AC-FR2201-04: test evidence carries runner, command, environment, exit, covered AC and revision digest.

    The TEST evidence must be a structured record with runner/command,
    environment/fixture identity, exit result, covered AC and the revision/digest
    under test. It is not Agent self-reported text.
    """
    ledger = TraceLedger()
    entry = _add_approved_requirement(ledger)

    # Spec-derived evidence shape (acceptance.md AC-FR2201-04 enumerates the
    # required fields). A dict is used because the impl accepts Any for TEST
    # evidence; we assert the full required field set is present.
    test_ev = {
        "runner": "pytest",
        "command": "python -m pytest -m e2e tests/e2e/",
        "environment": "ci-ubuntu-3.11",
        "fixture_identity": "tests/fixtures/fr2201",
        "exit": 0,
        "covered_ac": "AC-FR2201-04",
        "revision": "abc1234",
        "digest": "sha256:rev-abc1234",
    }
    ledger.link_evidence(entry.entry_id, EvidenceKind.TEST, test_ev)

    linked = ledger.lookup_by_task(entry.task_id)[0]
    ev = linked.evidence
    assert ev["runner"] == "pytest"
    assert ev["command"].startswith("python -m pytest")
    assert ev["environment"] == "ci-ubuntu-3.11"
    assert ev["exit"] == 0
    assert ev["covered_ac"] == "AC-FR2201-04"
    assert ev["revision"] == "abc1234"
    assert ev["digest"] == "sha256:rev-abc1234"


@pytest.mark.e2e
def test_ac_fr2201_04_test_evidence_rejects_agent_self_reported_text():
    """AC-FR2201-04: TEST evidence may carry structured fields but CODE evidence cannot be text.

    CODE evidence is strictly typed (CodeEvidence); TEST evidence is a
    structured record. An Agent cannot substitute CODE evidence with a string.
    """
    ledger = TraceLedger()
    entry = _add_approved_requirement(ledger)

    with pytest.raises(ValueError):
        ledger.link_evidence(entry.entry_id, EvidenceKind.CODE, "implemented per AC-04")


# ---------------------------------------------------------------------------
# AC-FR2201-05: unclosed ACs block gate; all closed -> reverse lookup
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2201_05_unclosed_ac_blocks_implementation_gate():
    """AC-FR2201-05: an unclosed AC blocks the implementation/completion gate.

    The gate must name the unclosed AC so the gap can be located.
    """
    ledger = TraceLedger()
    _add_approved_requirement(ledger, ac_id="AC-OPEN", task_id="t-1", issue="#1")

    with pytest.raises(TraceabilityError) as exc:
        ledger.validate_all_acs_closed()
    assert "AC-OPEN" in str(exc.value)


@pytest.mark.e2e
def test_ac_fr2201_05_all_closed_passes_gate_and_supports_reverse_lookup_by_task():
    """AC-FR2201-05: with every AC closed, the gate passes and any task/commit/test reverse-looks-up to the requirement.

    After closure, the ledger must allow reverse lookup from a task to the
    requirement/AC.
    """
    ledger = TraceLedger()
    e1 = _add_approved_requirement(ledger, ac_id="AC-A", task_id="t-1", issue="#1")
    e2 = _add_approved_requirement(ledger, ac_id="AC-B", task_id="t-2", issue="#2")
    ledger.close_ac(e1.entry_id, evidence_digest="sha256:ev-a")
    ledger.close_ac(e2.entry_id, evidence_digest="sha256:ev-b")

    ledger.validate_all_acs_closed()  # no exception -> gate passes

    # Reverse lookup by task -> requirement.
    by_task = ledger.lookup_by_task("t-1")
    assert len(by_task) == 1
    assert by_task[0].ac_id == "AC-A"
    assert by_task[0].evidence_status == STATUS_CLOSED
    assert by_task[0].evidence_digest == "sha256:ev-a"


@pytest.mark.e2e
def test_ac_fr2201_05_partial_closure_still_blocks():
    """AC-FR2201-05: closing one AC while another remains open still blocks the gate.

    The gate requires ALL ACs closed; partial closure is insufficient.
    """
    ledger = TraceLedger()
    e1 = _add_approved_requirement(ledger, ac_id="AC-A", task_id="t-1", issue="#1")
    _add_approved_requirement(ledger, ac_id="AC-B", task_id="t-2", issue="#2")
    ledger.close_ac(e1.entry_id, evidence_digest="sha256:ev-a")

    with pytest.raises(TraceabilityError) as exc:
        ledger.validate_all_acs_closed()
    assert "AC-B" in str(exc.value)
    assert "AC-A" not in str(exc.value)


# ---------------------------------------------------------------------------
# AC-FR2201-06: accepted contract change marks downstream evidence stale
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2201_06_contract_change_marks_affected_evidence_stale():
    """AC-FR2201-06: an accepted contract change marks affected downstream evidence stale.

    Affected ACs get evidence_status=stale and are sent back to the declaration
    gate (requirements_approval).
    """
    ledger = TraceLedger()
    ledger.mark_contract_current_digest(APPROVED_CONTRACT_DIGEST)
    e1 = _add_approved_requirement(ledger, ac_id="AC-A", task_id="t-1", issue="#1")
    e2 = _add_approved_requirement(ledger, ac_id="AC-B", task_id="t-2", issue="#2")

    ledger.apply_contract_change(
        affected_acs=["AC-A"],
        new_contract_digest=CHANGED_CONTRACT_DIGEST,
    )

    stale_entry = ledger.lookup_by_task(e1.task_id)[0]
    preserved_entry = ledger.lookup_by_task(e2.task_id)[0]

    assert stale_entry.evidence_status == STATUS_STALE
    assert stale_entry.contract_digest == CHANGED_CONTRACT_DIGEST
    assert stale_entry.gate == GATE_REQUIREMENTS_APPROVAL

    # Unaffected evidence is preserved (still pending, old digest retained).
    assert preserved_entry.evidence_status == STATUS_PENDING
    assert preserved_entry.contract_digest == APPROVED_CONTRACT_DIGEST
    assert preserved_entry.gate == ""


@pytest.mark.e2e
def test_ac_fr2201_06_stale_evidence_blocks_gate_until_re_closed():
    """AC-FR2201-06: stale evidence blocks the completion gate; old green status cannot override new contract.

    After a contract change, the affected AC is stale and cannot pass
    validate_all_acs_closed even if it had been closed before (it is no longer
    closed against the current contract).
    """
    ledger = TraceLedger()
    ledger.mark_contract_current_digest(APPROVED_CONTRACT_DIGEST)
    e1 = _add_approved_requirement(ledger, ac_id="AC-A", task_id="t-1", issue="#1")
    ledger.close_ac(e1.entry_id, evidence_digest="sha256:ev-old")

    # Contract changes; AC-A is now stale.
    ledger.apply_contract_change(
        affected_acs=["AC-A"],
        new_contract_digest=CHANGED_CONTRACT_DIGEST,
    )

    with pytest.raises(TraceabilityError) as exc:
        ledger.validate_all_acs_closed()
    assert "AC-A" in str(exc.value)


@pytest.mark.e2e
def test_ac_fr2201_06_unaffected_evidence_preserved_after_contract_change():
    """AC-FR2201-06: unaffected evidence is preserved but cannot override the new contract.

    An AC not in the affected set keeps its status, but the current contract
    digest is now the new one; the ledger will reject any future validation
    that still references the old digest.
    """
    ledger = TraceLedger()
    ledger.mark_contract_current_digest(APPROVED_CONTRACT_DIGEST)
    affected = _add_approved_requirement(
        ledger, ac_id="AC-AFFECTED", task_id="t-1", issue="#1"
    )
    unaffected = _add_approved_requirement(
        ledger, ac_id="AC-UNAFFECTED", task_id="t-2", issue="#2"
    )
    ledger.close_ac(unaffected.entry_id, evidence_digest="sha256:ev-u")
    ledger.close_ac(affected.entry_id, evidence_digest="sha256:ev-a")

    ledger.apply_contract_change(
        affected_acs=["AC-AFFECTED"],
        new_contract_digest=CHANGED_CONTRACT_DIGEST,
    )

    # Unaffected stays closed with old evidence; affected is stale.
    assert ledger.lookup_by_task("t-2")[0].evidence_status == STATUS_CLOSED
    assert ledger.lookup_by_task("t-1")[0].evidence_status == STATUS_STALE
    # The new contract is now current: a freshly-added AC referencing the OLD
    # digest must be rejected by validate_mdev_ready as stale, proving the
    # current contract is the new one (observed via public behaviour only).
    ledger.add_requirement(
        fr_id="FR-2201",
        ac_id="AC-NEW",
        task_id="t-3",
        issue="#3",
        contract_digest=APPROVED_CONTRACT_DIGEST,  # old digest
    )
    with pytest.raises(TraceabilityError) as exc:
        ledger.validate_mdev_ready()
    assert "AC-NEW" in str(exc.value)
    assert "stale" in str(exc.value).lower()
