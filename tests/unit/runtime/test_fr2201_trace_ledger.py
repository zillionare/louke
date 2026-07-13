"""FR-2201: end-to-end traceability gate for requirements, implementation and verification.

AC references:
- AC-FR2201-01: trace ledger links FR/NFR/AC to test-plan, task/issue,
  code/test evidence with artifact/commit digest and status.
- AC-FR2201-02: entering M-DEV fails if task plan has unmapped ACs, missing
  verification, duplicate/conflicting assignments or stale contract references.
- AC-FR2201-03: Devon task manifest contains only explicitly assigned issues/ACs.
- AC-FR2201-04: accepted evidence comes from real diff/commit and authoritative
  test runs, not agent self-reports.
- AC-FR2201-05: incomplete/unverified/failed/stale ACs block implementation gate
  or completion; all closed enables bidirectional trace lookup.
- AC-FR2201-06: accepted changes to approved requirements/design mark downstream
  evidence stale and return to declared gate.
"""

from __future__ import annotations

import pytest

from louke.runtime.trace_ledger import (
    CodeEvidence,
    EvidenceKind,
    TraceLedger,
    TraceabilityError,
)


# -- AC-FR2201-01 -------------------------------------------------------------


def test_ac_fr2201_01_ledger_links_requirements_to_evidence():
    """AC-FR2201-01: ledger links FR/AC to tasks, evidence and digests."""
    ledger = TraceLedger()
    entry = ledger.add_requirement(
        fr_id="FR-2201",
        ac_id="AC-FR2201-01",
        test_plan="tests/unit/runtime/test_trace_ledger.py",
    )
    ledger.link_task(entry.entry_id, task_id="task_001", issue="#132")
    ledger.link_evidence(
        entry.entry_id,
        kind=EvidenceKind.CODE,
        evidence=CodeEvidence(
            commit="abc123",
            diff_digest="sha256:diff",
        ),
    )

    assert entry.fr_id == "FR-2201"
    assert entry.ac_id == "AC-FR2201-01"
    assert entry.task_id == "task_001"
    assert entry.evidence.commit == "abc123"


# -- AC-FR2201-02 -------------------------------------------------------------


def test_ac_fr2201_02_mdev_blocked_on_unmapped_ac():
    """AC-FR2201-02: M-DEV entry blocked when AC is unmapped or stale."""
    ledger = TraceLedger()
    ledger.add_requirement(fr_id="FR-2201", ac_id="AC-FR2201-02")

    with pytest.raises(TraceabilityError):
        ledger.validate_mdev_ready()


def test_ac_fr2201_02_mdev_blocked_on_stale_contract():
    """AC-FR2201-02: M-DEV entry blocked when contract reference is stale."""
    ledger = TraceLedger()
    ledger.add_requirement(
        fr_id="FR-2201",
        ac_id="AC-FR2201-02",
        task_id="task_001",
        contract_digest="sha256:old",
    )
    ledger.mark_contract_current_digest("sha256:new")

    with pytest.raises(TraceabilityError):
        ledger.validate_mdev_ready()


# -- AC-FR2201-03 -------------------------------------------------------------


def test_ac_fr2201_03_manifest_contains_only_assigned_issues():
    """AC-FR2201-03: Devon manifest only includes assigned issues/ACs."""
    ledger = TraceLedger()
    ledger.add_requirement(fr_id="FR-2201", ac_id="AC-FR2201-03", issue="#132")

    manifest = ledger.build_devon_manifest(run_id="run_001")

    assert manifest["issues"] == ["#132"]
    assert manifest["acs"] == ["AC-FR2201-03"]
    assert "unassigned" not in manifest["acs"]


# -- AC-FR2201-04 -------------------------------------------------------------


def test_ac_fr2201_04_evidence_from_real_commit_and_tests():
    """AC-FR2201-04: accepted evidence includes real commit, runner and result."""
    ledger = TraceLedger()
    entry = ledger.add_requirement(fr_id="FR-2201", ac_id="AC-FR2201-04")
    ledger.link_evidence(
        entry.entry_id,
        kind=EvidenceKind.TEST,
        evidence={
            "runner": "pytest",
            "command": "pytest tests/unit",
            "environment": "py3.11",
            "exit_result": "passed",
            "covered_ac": "AC-FR2201-04",
            "revision_digest": "sha256:rev",
        },
    )

    assert entry.evidence["runner"] == "pytest"
    assert entry.evidence["exit_result"] == "passed"
    assert entry.evidence["revision_digest"] == "sha256:rev"


# -- AC-FR2201-05 -------------------------------------------------------------


def test_ac_fr2201_05_unclosed_ac_blocks_gate():
    """AC-FR2201-05: unclosed AC blocks implementation gate or completion."""
    ledger = TraceLedger()
    ledger.add_requirement(fr_id="FR-2201", ac_id="AC-FR2201-05")

    with pytest.raises(TraceabilityError):
        ledger.validate_all_acs_closed()


def test_ac_fr2201_05_all_closed_enables_lookup():
    """AC-FR2201-05: all ACs closed enables bidirectional trace lookup."""
    ledger = TraceLedger()
    entry = ledger.add_requirement(
        fr_id="FR-2201",
        ac_id="AC-FR2201-05",
        task_id="task_001",
    )
    ledger.close_ac(entry.entry_id, evidence_digest="sha256:ev")

    ledger.validate_all_acs_closed()
    assert ledger.lookup_by_task("task_001") == [entry]


# -- AC-FR2201-06 -------------------------------------------------------------


def test_ac_fr2201_06_change_marks_downstream_stale():
    """AC-FR2201-06: approved change marks downstream evidence stale."""
    ledger = TraceLedger()
    entry = ledger.add_requirement(
        fr_id="FR-2201",
        ac_id="AC-FR2201-06",
        task_id="task_001",
        evidence_status="verified",
    )

    ledger.apply_contract_change(
        affected_acs=["AC-FR2201-06"],
        new_contract_digest="sha256:changed",
    )

    assert entry.evidence_status == "stale"
    assert entry.gate == "requirements_approval"
