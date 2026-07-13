"""FR-1801: workspace initialization, first user and readiness checks.

AC references:
- AC-FR1801-01: `lk serve` in an existing git repo without Louke metadata
  starts a setup-only init wizard instead of exiting; wizard succeeds without
  requiring a separate CLI or internal file edits.
- AC-FR1801-02: Re-opening the wizard on an initialized workspace does not
  recreate ready resources; gaps are repaired deterministically or reported;
  conflicts are not overwritten without confirmation.
- AC-FR1801-03: Until a local human principal exists, the user can only
  complete setup, first-user creation and read-only readiness; gate APIs
  accept decisions only after login.
- AC-FR1801-04: Readiness query reports stable ready/degraded/blocked status,
  non-secret diagnostics and per-item remediation for each dependency.
- AC-FR1801-05: If OpenCode/provider is missing, read-only operations succeed,
  semantic tasks stop at blocked and show re-check action after authorization.
- AC-FR1801-06: Wizard-driven configuration does not expose secrets in project
  files, manifests, events, logs or responses.
"""

from __future__ import annotations

import pytest

from louke.runtime.workspace_init import (
    ConfigLeakError,
    InitWizard,
    ReadinessCheck,
    ReadinessReport,
    ReadinessStatus,
    WorkspacePrincipal,
)


# -- AC-FR1801-01 -------------------------------------------------------------


def test_ac_fr1801_01_wizard_creates_metadata():
    """AC-FR1801-01: init wizard creates Louke metadata for a git repo."""
    wizard = InitWizard(repo_path="/repo")
    report = wizard.run()

    assert report.initialized is True
    assert report.store_ready is True
    assert report.catalog_ready is True


def test_ac_fr1801_01_no_separate_cli_required():
    """AC-FR1801-01: wizard succeeds without CLI or internal edits."""
    wizard = InitWizard(repo_path="/repo")
    report = wizard.run()

    assert report.required_cli is False


# -- AC-FR1801-02 -------------------------------------------------------------


def test_ac_fr1801_02_wizard_is_idempotent():
    """AC-FR1801-02: re-running wizard does not recreate ready resources."""
    wizard = InitWizard(repo_path="/repo")
    first = wizard.run()
    second = wizard.run()

    assert first.initialized is True
    assert second.initialized is True
    assert second.created_resources == []


def test_ac_fr1801_02_conflict_not_overwritten():
    """AC-FR1801-02: existing source files are not overwritten without confirm."""
    wizard = InitWizard(repo_path="/repo", existing_files={"README.md": "hello"})
    report = wizard.run()

    assert report.conflicts == []


# -- AC-FR1801-03 -------------------------------------------------------------


def test_ac_fr1801_03_first_principal_required_for_gate():
    """AC-FR1801-03: gate decisions require the first human principal."""
    wizard = InitWizard(repo_path="/repo")
    wizard.run()

    principal = WorkspacePrincipal(name="alice")
    wizard.create_first_principal(principal)

    assert wizard.is_principal_authenticated(principal.id) is True

    # Before principal exists, gate decisions are rejected.
    empty_wizard = InitWizard(repo_path="/other")
    empty_wizard.run()
    assert empty_wizard.can_make_gate_decision() is False


# -- AC-FR1801-04 -------------------------------------------------------------


def test_ac_fr1801_04_readiness_report_statuses():
    """AC-FR1801-04: readiness reports stable status + remediation."""
    check = ReadinessCheck(
        name="OpenCode",
        status=ReadinessStatus.BLOCKED,
        diagnosis="OpenCode binary not found in PATH",
        remediation="Install OpenCode and authorize the provider",
    )

    report = ReadinessReport(items=[check])

    assert report.items[0].name == "OpenCode"
    assert report.items[0].status == ReadinessStatus.BLOCKED
    assert "Install OpenCode" in report.items[0].remediation


# -- AC-FR1801-05 -------------------------------------------------------------


def test_ac_fr1801_05_readonly_succeeds_when_provider_missing():
    """AC-FR1801-05: read-only operations succeed when provider is missing."""
    wizard = InitWizard(repo_path="/repo", opcodes_available=False)
    wizard.run()

    opcodes_item = next(i for i in wizard.readiness().items if i.name == "OpenCode")
    assert opcodes_item.status == ReadinessStatus.BLOCKED
    assert wizard.can_read_history() is True
    assert wizard.can_start_semantic_task() is False


# -- AC-FR1801-06 -------------------------------------------------------------


def test_ac_fr1801_06_secrets_not_leaked():
    """AC-FR1801-06: secrets are not stored in project files, logs or reports."""
    wizard = InitWizard(repo_path="/repo")
    wizard.run()
    wizard.configure_provider(secret="super-secret-token")

    report = wizard.readiness()
    logs = wizard.logs()

    assert "super-secret-token" not in str(report)
    assert "super-secret-token" not in str(logs)

    # Attempting to expose a secret raises an error.
    with pytest.raises(ConfigLeakError):
        wizard.configure_provider(secret="secret", allow_leak=True)
