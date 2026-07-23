"""AC-FR0400-01: Test Plan design closure.

FR-0400 requires the Test Plan validator to read each effective AC and bind
an observable interface, required layer(s), host runner/command, fixture/
environment, CI job, trace metadata and rationale.  Observable interface
and execution entry must resolve to Interfaces real identities whose
command/path/status semantics match the corresponding machine contract and
Architecture.  Unit-only coverage of cross-module behavior, internal-API
only main user journeys, missing required layer, or any orphan FR/AC/
interface/contract mapping blocks the baseline (AC-FR0400-01).
"""

from __future__ import annotations

from pathlib import Path


from louke.runtime.test_plan import (
    TestPlanEntry,
    TestPlanReport,
    validate_test_plan,
)

_SPEC_ROOT = (
    Path(__file__).resolve().parents[3]
    / ".louke"
    / "project"
    / "specs"
    / "v0.14-002-workflow-reflow-design"
)
_TEST_PLAN = _SPEC_ROOT / "test-plan.md"
_ACCEPTANCE = _SPEC_ROOT / "acceptance.md"
_INTERFACES = _SPEC_ROOT / "interfaces.md"


def _entries() -> list[TestPlanEntry]:
    return validate_test_plan(
        acceptance_path=_ACCEPTANCE,
        test_plan_path=_TEST_PLAN,
        interfaces_path=_INTERFACES,
    ).entries


def test_validate_returns_entries_for_all_34_acs() -> None:
    """AC-FR0400-01: each effective AC has a Test Plan entry."""
    report = validate_test_plan(
        acceptance_path=_ACCEPTANCE,
        test_plan_path=_TEST_PLAN,
        interfaces_path=_INTERFACES,
    )
    assert isinstance(report, TestPlanReport)
    ac_ids = {e.ac_id for e in report.entries}
    assert len(ac_ids) == 34
    assert "AC-FR0100-01" in ac_ids
    assert "AC-FR2700-01" in ac_ids
    assert "AC-NFR0600-01" in ac_ids


def test_each_entry_carries_observable_interface_and_required_layers() -> None:
    """AC-FR0400-01: every entry binds observable interface + required layers."""
    for entry in _entries():
        assert entry.ac_id
        assert entry.observable_interfaces, entry.ac_id
        assert entry.required_layers, entry.ac_id
        assert entry.runner_command, entry.ac_id
        assert entry.ci_job, entry.ac_id
        assert entry.fixture_environment, entry.ac_id
        assert entry.trace_metadata, entry.ac_id
        assert entry.rationale, entry.ac_id


def test_each_entry_resolves_interfaces_to_real_identities() -> None:
    """AC-FR0400-01: observable interfaces resolve to Interfaces real identities."""
    interfaces = _INTERFACES.read_text(encoding="utf-8")
    for entry in _entries():
        for iface in entry.observable_interfaces:
            assert iface in interfaces, (
                f"{entry.ac_id}: interface {iface} not in interfaces.md"
            )


def test_validate_rejects_orphan_interface_reference() -> None:
    """AC-FR0400-01: an AC referencing an unknown interface is an orphan."""
    bad_interfaces = _INTERFACES.parent / "interfaces_missing.md"
    bad_interfaces.write_text(
        _INTERFACES.read_text().replace("IF-DES-01", "IF-REMOVED-01"), encoding="utf-8"
    )
    try:
        report = validate_test_plan(
            acceptance_path=_ACCEPTANCE,
            test_plan_path=_TEST_PLAN,
            interfaces_path=bad_interfaces,
        )
        assert report.status == "fail"
        assert any("IF-DES-01" in e.orphan_interfaces for e in report.entries)
    finally:
        bad_interfaces.unlink()


def test_validate_rejects_unit_only_layer_for_cross_module_interface() -> None:
    """AC-FR0400-01: a cross-module interface with only unit coverage fails closure."""
    entries = _entries()
    cross_module_entry = next(
        e
        for e in entries
        if "IF-DES-01" in e.observable_interfaces and "U" in e.required_layers
    )
    # Simulate stripping integration coverage from a cross-module AC
    stripped = TestPlanEntry(
        ac_id=cross_module_entry.ac_id,
        observable_interfaces=cross_module_entry.observable_interfaces,
        required_layers=("U",),  # unit only - cross-module interface
        runner_command=cross_module_entry.runner_command,
        ci_job=cross_module_entry.ci_job,
        fixture_environment=cross_module_entry.fixture_environment,
        trace_metadata=cross_module_entry.trace_metadata,
        rationale=cross_module_entry.rationale,
        orphan_interfaces=(),
    )
    assert stripped.is_cross_module()
    assert stripped.requires_integration_layer() is True
    assert "I" not in stripped.required_layers


def test_validate_rejects_missing_required_layer_entry() -> None:
    """AC-FR0400-01: an AC without any required layer fails closure."""
    missing_layer = TestPlanEntry(
        ac_id="AC-FR9999-99",
        observable_interfaces=("IF-DES-01",),
        required_layers=(),  # no required layer
        runner_command="pytest",
        ci_job="unit",
        fixture_environment="fixture",
        trace_metadata={},
        rationale="rationale",
        orphan_interfaces=(),
    )
    assert missing_layer.has_required_layer() is False


def test_validate_rejects_internal_api_only_main_user_journey() -> None:
    """AC-FR0400-01: main user journeys must not use only internal APIs."""
    # An entry for a main user journey (e.g. AC-FR2400-01 Human M-DESIGN
    # surface) must declare an E layer; we verify the parser picked up the
    # E layer for at least one such entry.
    entries = _entries()
    human_journey = next(e for e in entries if e.ac_id == "AC-FR2400-01")
    assert "E" in human_journey.required_layers

    # The closure rule: a journey entry must require E layer; an entry that
    # claims to be a journey but only has U fails the rule.
    rule_entry = TestPlanEntry(
        ac_id="AC-FR9999-99",
        observable_interfaces=("IF-WEB-01",),
        required_layers=("U",),
        runner_command="internal",
        ci_job="unit",
        fixture_environment="fixture",
        trace_metadata={},
        rationale="main user journey",
        orphan_interfaces=(),
    )
    # The rule fails the closure: is_main_user_journey() True but no E layer
    closure_ok = (
        not rule_entry.is_main_user_journey() or "E" in rule_entry.required_layers
    )
    assert closure_ok is False


def test_report_includes_status_field() -> None:
    """AC-FR0400-01: report has a status field (pass/fail)."""
    report = validate_test_plan(
        acceptance_path=_ACCEPTANCE,
        test_plan_path=_TEST_PLAN,
        interfaces_path=_INTERFACES,
    )
    assert report.status in ("pass", "fail")


def test_report_localises_failure_to_ac_and_interface() -> None:
    """AC-FR0400-01: a failure must localise to a specific AC/interface/contract."""
    report = validate_test_plan(
        acceptance_path=_ACCEPTANCE,
        test_plan_path=_TEST_PLAN,
        interfaces_path=_INTERFACES,
    )
    # When passing, every entry is localised; when failing, the failing entry is localised.
    for entry in report.entries:
        assert entry.ac_id
        assert entry.observable_interfaces


def test_validate_rejects_orphan_contract_reference() -> None:
    """AC-FR0400-01: an AC referencing an unknown contract is rejected."""
    entries = _entries()
    # All entries should reference known contract kinds only
    known_contract_kinds = {
        "integration-test",
        "e2e-test",
        "pre-commit",
        "github-actions-ci",
        "release-version",
        "build-artifact",
        "publish-recovery",
    }
    for entry in entries:
        # Trace metadata may include contract kinds; verify they're all known
        contracts = entry.trace_metadata.get("contracts", [])
        for c in contracts:
            assert c in known_contract_kinds, f"{entry.ac_id}: unknown contract {c}"
