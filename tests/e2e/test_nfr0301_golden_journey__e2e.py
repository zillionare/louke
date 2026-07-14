"""NFR-0301: first-use to history-archive product-level E2E journey.

Covers AC-NFR0301-01..06. Per test-plan §1.1 (black-box declaration) and §6.9
(non-functional specialty) these tests observe the golden journey through its
public ``JourneyResult`` and ``GoldenJourney`` surface and the controllable
``E2EAdapterSet``. The result exposes observable exits described in
interfaces.md §6.3 (archive/history), §4 (gate/graph), §5 (events) and
§2.2 (runtime identity). The v0.12 M-DEV HTTP project API is not yet
implemented; these public outputs are the contract surface, mirroring the
established pattern in ``test_fr2301_legacy_adoption__e2e.py``.

Expected path, gate sequence, trace/archive state and adapter labels come
from acceptance.md AC-NFR0301-01..06 (the spec), not from implementation
output. The journey must not call internal Python objects or pre-write runtime
state; it must drive init -> first user -> readiness -> new_feature -> two
approvals -> agent/program steps -> service restart -> completion -> history.

AC references:
- AC-NFR0301-01: golden journey from a clean git fixture through init -> first
  user -> readiness -> new_feature -> two approvals -> agent/program steps ->
  service restart -> completion -> history, without pre-written runtime state
  or internal Python objects.
- AC-NFR0301-02: new_feature dual-gate path + bug_fix quick_rgr and
  design_required paths; each observes correct graph, gates, trace and history.
- AC-NFR0301-03: missing model/provider, stale approval, agent failure and
  cancellation fixtures each present blocked/reapproval/recovery/cleanup
  results without false success or lost audit.
- AC-NFR0301-04: CI stand-in adapters are explicitly labeled; contract vs real
  adapter kinds are distinguishable in evidence.
- AC-NFR0301-05: concurrent workspaces with different local/global runtimes
  keep identity isolated; no cross-workspace package/definition/prompt/state
  pollution.
- AC-NFR0301-06: active main + parallel hotfix + new requirement; new
  requirement enters backlog, second main project rejected, hotfix and main
  can complete in parallel without cross-write.
"""

from __future__ import annotations

import pytest

from louke.runtime.e2e_journey import (
    E2EAdapterSet,
    GoldenJourney,
)

# Fixed runtime versions and paths - driven by the test fixtures, not derived
# from implementation output.
WS_A_VERSION = "0.12.1"
WS_B_VERSION = "0.12.2"


# ---------------------------------------------------------------------------
# AC-NFR0301-01: golden journey from clean git fixture
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_nfr0301_01_golden_journey_completes_without_internal_objects():
    """AC-NFR0301-01: the golden journey completes without pre-written state or internal objects.

    Starting from a clean adapter set, ``run_new_feature`` must drive init ->
    first user -> readiness -> new_feature -> two approvals -> agent/program
    steps -> service restart -> completion -> history, reporting completed,
    archived and history_viewable; ``internal_python_objects_called`` must be
    False.
    """
    adapters = E2EAdapterSet(model_available=True, opencode_real=True)
    journey = GoldenJourney(adapters)

    result = journey.run_new_feature()

    assert result.completed is True
    assert result.archived is True
    assert result.history_viewable is True
    # The contract: the journey must not bypass the runtime by calling internal
    # Python objects directly.
    assert result.internal_python_objects_called is False
    assert result.status == "completed"


@pytest.mark.e2e
def test_ac_nfr0301_01_golden_journey_requires_two_approvals():
    """AC-NFR0301-01: the golden journey records exactly two gate approvals.

    A new_feature run must pass requirements approval and M-LOCK - the two
    non-skippable human gates - before reaching completion. The gates list
    must contain both, in order.
    """
    adapters = E2EAdapterSet()
    journey = GoldenJourney(adapters)

    result = journey.run_new_feature()

    assert result.gates_approved == ["requirements_approval", "m_lock"]
    assert result.trace_complete is True


@pytest.mark.e2e
def test_ac_nfr0301_01_golden_journey_records_runtime_identity():
    """AC-NFR0301-01: the completed journey records the resolved runtime identity.

    The journey result must surface the runtime identity (version, mode,
    executable) so the audit trail links completion to a precise runtime.
    """
    adapters = E2EAdapterSet(runtime_version=WS_A_VERSION, mode="local")
    journey = GoldenJourney(adapters)

    result = journey.run_new_feature()

    identity = result.runtime_identity
    assert identity["version"] == WS_A_VERSION
    assert identity["mode"] == "local"
    assert "executable" in identity
    assert WS_A_VERSION in identity["executable"]


# ---------------------------------------------------------------------------
# AC-NFR0301-02: new_feature dual-gate + bug_fix quick_rgr + design_required
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_nfr0301_02_new_feature_dual_gate_path():
    """AC-NFR0301-02: new_feature follows the dual-gate (requirements + M-LOCK) path.

    The new_feature definition requires both gates; the path must produce
    trace evidence and a completed/archived history terminal state.
    """
    adapters = E2EAdapterSet()
    journey = GoldenJourney(adapters)

    result = journey.run_new_feature()

    assert "requirements_approval" in result.gates_approved
    assert "m_lock" in result.gates_approved
    assert result.trace_complete is True
    assert result.completed is True
    assert result.archived is True


@pytest.mark.e2e
def test_ac_nfr0301_02_bug_fix_quick_rgr_path():
    """AC-NFR0301-02: bug_fix quick path records the quick_rgr trace path.

    A linked-Issue quick R-G-R hotfix must validate the issue source contract,
    pass M-LOCK, complete trace evidence and archive with history terminal.
    """
    adapters = E2EAdapterSet()
    journey = GoldenJourney(adapters)

    result = journey.run_bug_fix(impact="quick")

    assert result.path_taken == "quick_rgr"
    assert "issue_source_contract_validation" in result.gates_approved
    assert "m_lock" in result.gates_approved
    assert result.trace_complete is True
    assert result.completed is True
    assert result.archived is True
    assert result.history_viewable is True


@pytest.mark.e2e
def test_ac_nfr0301_02_bug_fix_design_required_path():
    """AC-NFR0301-02: bug_fix design-required path adds design reviews before M-LOCK.

    The design-required hotfix path must include test plan review and
    architecture review gates in addition to the source-contract validation
    and M-LOCK, producing complete trace and history terminal state.
    """
    adapters = E2EAdapterSet()
    journey = GoldenJourney(adapters)

    result = journey.run_bug_fix(impact="design_required")

    assert result.path_taken == "design_required"
    assert "issue_source_contract_validation" in result.gates_approved
    assert "test_plan_review" in result.gates_approved
    assert "architecture_review" in result.gates_approved
    assert "m_lock" in result.gates_approved
    assert result.trace_complete is True
    assert result.completed is True
    assert result.archived is True


# ---------------------------------------------------------------------------
# AC-NFR0301-03: missing model / stale approval / agent failure / cancellation
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_nfr0301_03_missing_model_blocks_journey_with_repair_action():
    """AC-NFR0301-03: a missing model/provider blocks the journey with a recommended action.

    When the model/provider is unavailable, the journey must not reach
    completion; it must present a blocked reason and a repair action without
    false success.
    """
    adapters = E2EAdapterSet(model_available=False)
    journey = GoldenJourney(adapters)

    result = journey.run_new_feature()

    assert result.completed is False
    assert result.archived is False
    assert result.status != "completed"
    assert result.blocked_reason != ""
    assert "model" in result.blocked_reason.lower() or "provider" in result.blocked_reason.lower()
    assert result.recommended_action != ""


@pytest.mark.e2e
def test_ac_nfr0301_03_cancellation_records_audit_and_cleanup():
    """AC-NFR0301-03: cancelling after requirements approval records audit and cleanup.

    When the user cancels after the first gate, the journey must record a
    cancellation audit entry, run cleanup and not lose the audit record.
    """
    adapters = E2EAdapterSet()
    journey = GoldenJourney(adapters)

    result = journey.run_new_feature(cancel_after="requirements_approval")

    assert result.cancelled is True
    assert result.cleanup_run is True
    assert result.audit_record["actor"] == "user"
    assert "reason" in result.audit_record
    assert result.status == "cancelled"
    # Cancelled journey must not be reported as completed.
    assert result.completed is False


# ---------------------------------------------------------------------------
# AC-NFR0301-04: CI stand-in adapters explicitly labeled
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_nfr0301_04_contract_stand_in_adapter_labeled():
    """AC-NFR0301-04: a contract stand-in adapter is labeled as stand-in in evidence.

    When running the suite in a CI environment with contract-compatible
    stand-ins, the adapter kind must be explicitly labeled; stand-in must
    not be reported as a real integration.
    """
    adapters = E2EAdapterSet(opencode_real=False)
    journey = GoldenJourney(adapters)

    result = journey.run_new_feature()

    assert result.adapter_labels["opencode"] == "stand-in"
    assert result.adapter_labels["opencode"] != "real"


@pytest.mark.e2e
def test_ac_nfr0301_04_real_adapter_labeled():
    """AC-NFR0301-04: a real OpenCode adapter is labeled as real in evidence.

    When a real adapter is used (release smoke), the label must reflect real,
    distinguishable from the stand-in.
    """
    adapters = E2EAdapterSet(opencode_real=True)
    journey = GoldenJourney(adapters)

    result = journey.run_new_feature()

    assert result.adapter_labels["opencode"] == "real"


# ---------------------------------------------------------------------------
# AC-NFR0301-05: concurrent workspaces keep identity isolated
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_nfr0301_05_concurrent_workspaces_keep_identity_isolated():
    """AC-NFR0301-05: two workspaces with different local runtimes keep identity isolated.

    Two clean workspace fixtures pinning different local Louke runtimes must
    each complete their golden journey with their own runtime identity; the
    user-visible result, manifest and event evidence must show each
    workspace's correct runtime version, with no cross-workspace pollution.
    """
    adapters_a = E2EAdapterSet(runtime_version=WS_A_VERSION, mode="local")
    adapters_b = E2EAdapterSet(runtime_version=WS_B_VERSION, mode="local")
    journey_a = GoldenJourney(adapters_a)
    journey_b = GoldenJourney(adapters_b)

    result_a = journey_a.run_new_feature()
    result_b = journey_b.run_new_feature()

    assert result_a.runtime_identity["version"] == WS_A_VERSION
    assert result_b.runtime_identity["version"] == WS_B_VERSION
    assert result_a.runtime_identity["version"] != result_b.runtime_identity["version"]
    assert result_a.runtime_identity["executable"] != result_b.runtime_identity["executable"]
    # Both must complete independently.
    assert result_a.completed is True
    assert result_b.completed is True


@pytest.mark.e2e
def test_ac_nfr0301_05_local_and_global_mode_workspaces_isolated():
    """AC-NFR0301-05: a local-mode and a global-mode workspace keep identity isolated.

    A workspace fixture choosing local mode and another choosing global mode
    must each surface their own mode in the journey result; the global
    workspace must not pollute the local one's identity.
    """
    adapters_local = E2EAdapterSet(runtime_version=WS_A_VERSION, mode="local")
    adapters_global = E2EAdapterSet(runtime_version="0.12.3", mode="global")
    journey_local = GoldenJourney(adapters_local)
    journey_global = GoldenJourney(adapters_global)

    result_local = journey_local.run_new_feature()
    result_global = journey_global.run_new_feature()

    assert result_local.runtime_identity["mode"] == "local"
    assert result_global.runtime_identity["mode"] == "global"
    assert result_local.runtime_identity["version"] == WS_A_VERSION
    assert result_global.runtime_identity["version"] == "0.12.3"


# ---------------------------------------------------------------------------
# AC-NFR0301-06: active main + parallel hotfix + new requirement (backlog)
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_nfr0301_06_new_requirement_enters_backlog_during_active_main():
    """AC-NFR0301-06: a new requirement submitted during an active main run goes to backlog.

    Only one main project may be active at a time; a new requirement submitted
    while a main run is active must enter the backlog rather than start a
    second main run.
    """
    adapters = E2EAdapterSet()
    journey = GoldenJourney(adapters)

    main_result = journey.start_new_feature()
    assert main_result.status == "running"

    backlog_result = journey.submit_new_requirement("FR-9999")

    assert backlog_result.status == "backlog"
    # The active main run count must remain 1 - no second main project.
    assert journey.active_main_run_count() == 1


@pytest.mark.e2e
def test_ac_nfr0301_06_parallel_hotfix_can_run_alongside_main():
    """AC-NFR0301-06: a source-contract-validated hotfix runs in parallel with the main.

    A hotfix with an approved linked issue and source contract may start
    alongside an active main project; both must be able to complete without
    cross-write or identity pollution.
    """
    adapters = E2EAdapterSet()
    journey = GoldenJourney(adapters)

    main_result = journey.start_new_feature()
    assert main_result.status == "running"

    hotfix_result = journey.start_hotfix(
        linked_issue="issue-42",
        spec_status="approved",
    )
    assert hotfix_result.status == "running"
    # Main run count remains 1 - hotfix does not count as a second main.
    assert journey.active_main_run_count() == 1


@pytest.mark.e2e
def test_ac_nfr0301_06_hotfix_without_source_contract_blocked():
    """AC-NFR0301-06: a hotfix without an approved source contract is blocked.

    A hotfix missing the linked issue or the approved spec status must be
    blocked rather than starting; this prevents an unvalidated parallel run.
    """
    adapters = E2EAdapterSet()
    journey = GoldenJourney(adapters)

    # Missing linked issue.
    blocked_no_issue = journey.start_hotfix(linked_issue="", spec_status="approved")
    assert blocked_no_issue.status == "blocked"

    # Spec not approved.
    blocked_no_spec = journey.start_hotfix(
        linked_issue="issue-43",
        spec_status="draft",
    )
    assert blocked_no_spec.status == "blocked"
