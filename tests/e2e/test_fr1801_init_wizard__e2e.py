"""FR-1801: workspace init wizard, first user and readiness e2e.

Covers AC-FR1801-01..06. Per test-plan §1.1 (black-box declaration) these tests
observe the init wizard through its public report/readiness/log surface and the
documented setup-only behavior, not internal Runtime objects. The wizard is an
in-memory class with no dedicated HTTP API yet (v0.12 M-DEV not started); its
public ``InitReport`` / ``ReadinessReport`` / sanitized ``logs()`` outputs are
the observable exits described in interfaces.md §2.3 (setup/readiness).

AC references:
- AC-FR1801-01: setup-only wizard bootstraps metadata without a separate CLI.
- AC-FR1801-02: re-running wizard is idempotent; conflicts not overwritten.
- AC-FR1801-03: gate decisions require an authenticated first principal.
- AC-FR1801-04: readiness reports stable ready/degraded/blocked + remediation.
- AC-FR1801-05: missing provider keeps read-only ops working, tasks blocked.
- AC-FR1801-06: secrets never appear in project files, logs or responses.
"""

from __future__ import annotations

import pytest

from louke.runtime.workspace_init import (
    ConfigLeakError,
    InitWizard,
    ReadinessStatus,
    WorkspacePrincipal,
)

# A high-entropy-looking token used to verify secret redaction (AC-FR1801-06).
# Value is fixed by the test, not derived from implementation output.
_PROVIDER_SECRET = "sk-proj-1234567890abcdefABCDEF"


@pytest.mark.e2e
def test_ac_fr1801_01_setup_only_wizard_no_separate_cli(tmp_path):
    """AC-FR1801-01: wizard bootstraps metadata; store/catalog ready; no CLI required.

    Given a git repo without Louke metadata, the setup-only wizard creates the
    runtime store + catalog entries and reports ``required_cli=False`` so the
    user does not need a second initialization CLI or internal file edits.
    """
    wizard = InitWizard(repo_path=str(tmp_path))
    report = wizard.run()

    assert report.initialized is True
    assert report.store_ready is True
    assert report.catalog_ready is True
    # The contract: no separate init CLI is required after the wizard.
    assert report.required_cli is False
    # Default resources are documented in the module contract (.louke metadata).
    assert ".louke/project/project.toml" in report.created_resources
    assert ".louke/store" in report.created_resources


@pytest.mark.e2e
def test_ac_fr1801_02_idempotent_rerun_no_duplicate_resources(tmp_path):
    """AC-FR1801-02: re-running the wizard does not recreate ready resources.

    Idempotency means the second run observes already-initialized state and
    creates no new resources, with no conflicts reported for ready resources.
    """
    wizard = InitWizard(repo_path=str(tmp_path))
    first = wizard.run()
    second = wizard.run()

    assert first.initialized is True
    assert second.initialized is True
    # Idempotency contract: second run creates nothing new.
    assert second.created_resources == []
    assert second.conflicts == []


@pytest.mark.e2e
def test_ac_fr1801_02_conflicting_source_file_not_overwritten(tmp_path):
    """AC-FR1801-02: existing source files are not overwritten without confirm.

    When an existing file conflicts with a resource the wizard would create,
    the wizard reports the conflict rather than overwriting the source.
    """
    wizard = InitWizard(
        repo_path=str(tmp_path),
        existing_files={".louke/project/project.toml"},
    )
    report = wizard.run()

    assert ".louke/project/project.toml" in report.conflicts
    assert ".louke/project/project.toml" not in report.created_resources
    # The store can still be created (the conflict is isolated to that file).
    assert ".louke/store" in report.created_resources


@pytest.mark.e2e
def test_ac_fr1801_03_gate_decision_requires_first_principal(tmp_path):
    """AC-FR1801-03: gate decisions accepted only after first principal login.

    Until a local human principal is registered, the wizard rejects gate
    decisions; after ``create_first_principal`` the principal is authenticated
    and gate decisions become acceptable.
    """
    wizard = InitWizard(repo_path=str(tmp_path))
    wizard.run()

    # Before first principal: no gate decisions.
    assert wizard.can_make_gate_decision() is False

    principal = WorkspacePrincipal(name="alice")
    wizard.create_first_principal(principal)

    assert wizard.is_principal_authenticated(principal.id) is True
    assert wizard.can_make_gate_decision() is True


@pytest.mark.e2e
def test_ac_fr1801_04_readiness_reports_stable_status_and_remediation(tmp_path):
    """AC-FR1801-04: readiness reports ready/blocked status + non-secret diagnosis + remediation.

    Each dependency item reports a stable status, a non-secret diagnosis and a
    remediation action that is meaningful for that item (not a generic hint).
    """
    wizard = InitWizard(repo_path=str(tmp_path), opcodes_available=False)
    wizard.run()

    report = wizard.readiness()
    by_name = {item.name: item for item in report.items}

    # Contract: at least Git, Store, Catalog, OpenCode are covered.
    assert {"Git", "Store", "Catalog", "OpenCode"}.issubset(by_name.keys())

    opcodes = by_name["OpenCode"]
    assert opcodes.status == ReadinessStatus.BLOCKED
    # Diagnosis must be non-secret and mention OpenCode specifically.
    assert "OpenCode" in opcodes.diagnosis
    # Remediation must point to install/authorize, not a no-op.
    assert opcodes.remediation != "none"
    assert "Install" in opcodes.remediation

    git = by_name["Git"]
    assert git.status == ReadinessStatus.READY
    assert git.remediation == "none"


@pytest.mark.e2e
def test_ac_fr1801_05_missing_provider_blocks_semantic_task_not_readonly(tmp_path):
    """AC-FR1801-05: missing provider keeps read-only ops working; tasks blocked.

    When OpenCode/provider is missing, history/docs/readiness remain readable
    but starting a semantic task is blocked and reports a re-check action.
    """
    wizard = InitWizard(repo_path=str(tmp_path), opcodes_available=False)
    wizard.run()

    # Read-only operations succeed.
    assert wizard.can_read_history() is True
    # Semantic tasks are blocked (no fake session created).
    assert wizard.can_start_semantic_task() is False

    opcodes = next(i for i in wizard.readiness().items if i.name == "OpenCode")
    assert opcodes.status == ReadinessStatus.BLOCKED
    # The remediation is the "re-check after authorization" action.
    assert "authorize" in opcodes.remediation.lower()


@pytest.mark.e2e
def test_ac_fr1801_05_provider_available_enables_semantic_task(tmp_path):
    """AC-FR1801-05 (positive side): provider present lets semantic tasks start.

    The blocked state from the missing-provider case must flip to ready when
    OpenCode is available, proving the block is not a static false-negative.
    """
    wizard = InitWizard(repo_path=str(tmp_path), opcodes_available=True)
    wizard.run()

    assert wizard.can_read_history() is True
    assert wizard.can_start_semantic_task() is True
    opcodes = next(i for i in wizard.readiness().items if i.name == "OpenCode")
    assert opcodes.status == ReadinessStatus.READY


@pytest.mark.e2e
def test_ac_fr1801_06_secret_not_leaked_in_logs_or_report(tmp_path):
    """AC-FR1801-06: provider secret never appears in project files, logs or readiness.

    After configuring a provider secret, the sanitized wizard logs and the
    readiness report must not contain the raw secret.
    """
    wizard = InitWizard(repo_path=str(tmp_path))
    wizard.run()
    wizard.configure_provider(secret=_PROVIDER_SECRET)

    logs = wizard.logs()
    report = wizard.readiness()

    assert _PROVIDER_SECRET not in "\n".join(logs)
    assert _PROVIDER_SECRET not in str(report)
    # Logs confirm configuration happened, but redacted.
    assert any("provider" in line.lower() for line in logs)


@pytest.mark.e2e
def test_ac_fr1801_06_leaking_secret_is_rejected(tmp_path):
    """AC-FR1801-06: attempting to store a secret in project files is rejected.

    The wizard must refuse to persist a secret into project files; this is the
    fail-closed side of the no-leak contract.
    """
    wizard = InitWizard(repo_path=str(tmp_path))
    wizard.run()

    with pytest.raises(ConfigLeakError):
        wizard.configure_provider(secret="any", allow_leak=True)
