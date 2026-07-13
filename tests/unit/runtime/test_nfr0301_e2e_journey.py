"""NFR-0301: product-level first-use to history archive E2E.

AC references:
- AC-NFR0301-01: golden journey from clean git fixture through init wizard,
  first user, readiness, new_feature, two approvals, agent/program steps,
  service restart, completion and history view passes without pre-writing
  runtime state or calling internal Python objects directly.
- AC-NFR0301-02: E2E suite covers new_feature dual-gate path and bug_fix
  quick/design-required paths with correct graph, gates, evidence and final
  history state.
- AC-NFR0301-03: missing model/provider, stale approval, agent/adapter failure
  and user cancellation fixtures produce blocked/reapproval/recovery/cleanup.
- AC-NFR0301-04: CI stand-ins and real OpenCode smoke are labeled;
  smoke proves create/attach/task/detach/exit.
- AC-NFR0301-05: concurrent workspaces with different local/global runtimes
  keep identity isolated in UI, processes, manifests, events and history.
- AC-NFR0301-06: active main new_feature + parallel hotfix + new requirement
  flow keeps backlog, no second main run, no cross-run contamination.
"""

from __future__ import annotations

from louke.runtime.e2e_journey import (
    E2EAdapterSet,
    GoldenJourney,
    JourneyResult,
)


# -- AC-NFR0301-01 ------------------------------------------------------------


def test_ac_nfr0301_01_golden_journey_reaches_history():
    """AC-NFR0301-01: golden journey completes and archives to history."""
    adapters = E2EAdapterSet()
    journey = GoldenJourney(adapters=adapters)
    result = journey.run_new_feature()

    assert isinstance(result, JourneyResult)
    assert result.completed is True
    assert result.archived is True
    assert result.history_viewable is True
    assert result.internal_python_objects_called is False


# -- AC-NFR0301-02 ------------------------------------------------------------


def test_ac_nfr0301_02_new_feature_dual_gate_path():
    """AC-NFR0301-02: new_feature has dual gate path and trace evidence."""
    adapters = E2EAdapterSet()
    journey = GoldenJourney(adapters=adapters)
    result = journey.run_new_feature()

    assert "requirements_approval" in result.gates_approved
    assert "m_lock" in result.gates_approved
    assert result.trace_complete is True


def test_ac_nfr0301_02_bug_fix_paths():
    """AC-NFR0301-02: bug_fix has quick_rgr and design_required paths."""
    adapters = E2EAdapterSet()
    journey = GoldenJourney(adapters=adapters)

    quick = journey.run_bug_fix(impact="quick")
    assert quick.completed is True
    assert quick.path_taken == "quick_rgr"

    design = journey.run_bug_fix(impact="design_required")
    assert design.completed is True
    assert design.path_taken == "design_required"


# -- AC-NFR0301-03 ------------------------------------------------------------


def test_ac_nfr0301_03_missing_model_blocks_with_action():
    """AC-NFR0301-03: missing model/provider blocks with re-check action."""
    adapters = E2EAdapterSet(model_available=False)
    journey = GoldenJourney(adapters=adapters)
    result = journey.run_new_feature()

    assert result.completed is False
    assert result.blocked_reason == "model/provider unavailable"
    assert "reinstall and re-detect" in result.recommended_action


def test_ac_nfr0301_03_user_cancel_reaches_terminal_state():
    """AC-NFR0301-03: user cancellation results in cleanup and audit."""
    adapters = E2EAdapterSet()
    journey = GoldenJourney(adapters=adapters)
    result = journey.run_new_feature(cancel_after="requirements_approval")

    assert result.cancelled is True
    assert result.cleanup_run is True
    assert result.audit_record is not None


# -- AC-NFR0301-04 ------------------------------------------------------------


def test_ac_nfr0301_04_stand_in_labeled():
    """AC-NFR0301-04: stand-in adapters are labeled in the report."""
    adapters = E2EAdapterSet(opencode_real=False)
    journey = GoldenJourney(adapters=adapters)
    result = journey.run_new_feature()

    assert result.adapter_labels == {"opencode": "stand-in"}


# -- AC-NFR0301-05 ------------------------------------------------------------


def test_ac_nfr0301_05_concurrent_workspaces_isolated():
    """AC-NFR0301-05: concurrent workspaces keep runtime identity isolated."""
    adapters_a = E2EAdapterSet(runtime_version="0.12.1")
    adapters_b = E2EAdapterSet(runtime_version="0.12.2")
    adapters_c = E2EAdapterSet(mode="global", runtime_version="0.12.0")

    journey_a = GoldenJourney(adapters=adapters_a)
    journey_b = GoldenJourney(adapters=adapters_b)
    journey_c = GoldenJourney(adapters=adapters_c)

    result_a = journey_a.run_new_feature()
    result_b = journey_b.run_new_feature()
    result_c = journey_c.run_new_feature()

    assert result_a.runtime_identity["version"] == "0.12.1"
    assert result_b.runtime_identity["version"] == "0.12.2"
    assert result_c.runtime_identity["mode"] == "global"
    assert result_a.runtime_identity["executable"] != result_b.runtime_identity["executable"]


# -- AC-NFR0301-06 ------------------------------------------------------------


def test_ac_nfr0301_06_main_plus_hotfix_no_second_main_run():
    """AC-NFR0301-06: new requirement goes to backlog while main + hotfix run."""
    adapters = E2EAdapterSet()
    journey = GoldenJourney(adapters=adapters)

    main = journey.start_new_feature()
    hotfix = journey.start_hotfix(linked_issue="#200", spec_status="approved")
    backlog = journey.submit_new_requirement("FR-9999")

    assert main.status == "running"
    assert hotfix.status == "running"
    assert backlog.status == "backlog"
    assert journey.active_main_run_count() == 1
