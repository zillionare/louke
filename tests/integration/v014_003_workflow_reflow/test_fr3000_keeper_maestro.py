"""Integration tests for FR-3000: Keeper retirement & Maestro demotion.

AC-FR3000-01: The canonical WorkflowDefinition/ResponsibilityCatalog
must NOT contain Keeper semantic dispatch; Keeper's format/RGR/AC-trace/
anti-pattern/regression capabilities must migrate to Runtime-registered
program checks. A retained Keeper CLI is only a compat entrypoint to
the same handler; it must NOT write a second state authority. Maestro
prompt/tools must NOT have spawn/advance/regress/waive/commit/release/
archive/branch-management capabilities; its advisory must NOT directly
change persisted workflow state.

Interfaces covered (per interfaces.md):
- IF-PROMPT-02 (Primary ARC-01)
- IF-WFR-01 (workflow state, ARC-01)
- IF-QUAL-01 (quality checks, ARC-10)
"""
# AC-FR3000-01

from __future__ import annotations

import pytest

from louke.v014.fr3000_keeper_maestro import (
    ERROR_CODES,
    KeeperMaestroError,
    RuntimeResponsibilityCatalog,
    WorkflowDefinition,
    validate_keeper_retirement,
    validate_maestro_demotion,
)


def _valid_catalog() -> RuntimeResponsibilityCatalog:
    return RuntimeResponsibilityCatalog(
        semantic_dispatch_roles=("archer", "devon", "shield", "prism", "judge"),
        keeper_dispatch=False,
        keeper_cli_compat=True,  # compat CLI allowed
        keeper_cli_writes_state=False,  # but cannot write state
        runtime_program_checks=(
            "format",
            "rgr",
            "ac-trace",
            "anti-pattern",
            "regression",
        ),
    )


def _valid_definition() -> WorkflowDefinition:
    return WorkflowDefinition(
        maestro_can_spawn_specialist_agent=False,
        maestro_can_advance=False,
        maestro_can_regress=False,
        maestro_can_waive=False,
        maestro_can_commit=False,
        maestro_can_release=False,
        maestro_can_archive=False,
        maestro_can_manage_branch=False,
        maestro_advisory_changes_state=False,
    )


# ---------------------------------------------------------------------------
# validate_keeper_retirement
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_validate_keeper_retirement_passes_when_no_dispatch_no_dual_state():
    """AC-FR3000-01: Keeper retired + capabilities migrated -> OK."""
    validate_keeper_retirement(_valid_catalog())  # no raise


@pytest.mark.real_module
def test_validate_keeper_retirement_rejects_keeper_dispatch():
    """AC-FR3000-01: Keeper still in semantic_dispatch_roles -> KEEPER_DISPATCH_FORBIDDEN."""
    bad = RuntimeResponsibilityCatalog(
        semantic_dispatch_roles=("archer", "keeper"),  # keeper still there
        keeper_dispatch=True,
        keeper_cli_compat=True,
        keeper_cli_writes_state=False,
        runtime_program_checks=_valid_catalog().runtime_program_checks,
    )
    with pytest.raises(KeeperMaestroError) as exc:
        validate_keeper_retirement(bad)
    assert exc.value.code == "KEEPER_DISPATCH_FORBIDDEN"


@pytest.mark.real_module
def test_validate_keeper_retirement_rejects_dual_state_authority():
    """AC-FR3000-01: compat Keeper CLI writes second state -> KEEPER_DUAL_STATE_FORBIDDEN."""
    bad = RuntimeResponsibilityCatalog(
        semantic_dispatch_roles=("archer",),
        keeper_dispatch=False,
        keeper_cli_compat=True,
        keeper_cli_writes_state=True,  # writing second state
        runtime_program_checks=_valid_catalog().runtime_program_checks,
    )
    with pytest.raises(KeeperMaestroError) as exc:
        validate_keeper_retirement(bad)
    assert exc.value.code == "KEEPER_DUAL_STATE_FORBIDDEN"


@pytest.mark.real_module
def test_validate_keeper_retirement_rejects_unmigrated_capabilities():
    """AC-FR3000-01: missing program checks -> KEEPER_CAPABILITIES_NOT_MIGRATED."""
    bad = RuntimeResponsibilityCatalog(
        semantic_dispatch_roles=("archer",),
        keeper_dispatch=False,
        keeper_cli_compat=True,
        keeper_cli_writes_state=False,
        runtime_program_checks=(
            "format",
            "rgr",
        ),  # missing ac-trace, anti-pattern, regression
    )
    with pytest.raises(KeeperMaestroError) as exc:
        validate_keeper_retirement(bad)
    assert exc.value.code == "KEEPER_CAPABILITIES_NOT_MIGRATED"


@pytest.mark.real_module
def test_keeper_cli_compat_allowed_without_state_writes():
    """AC-FR3000-01: retained Keeper CLI is OK if it's only a compat entrypoint."""
    catalog = RuntimeResponsibilityCatalog(
        semantic_dispatch_roles=("archer",),
        keeper_dispatch=False,
        keeper_cli_compat=True,  # OK
        keeper_cli_writes_state=False,
        runtime_program_checks=_valid_catalog().runtime_program_checks,
    )
    validate_keeper_retirement(catalog)  # no raise


# ---------------------------------------------------------------------------
# validate_maestro_demotion
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_validate_maestro_demotion_passes_when_all_capabilities_false():
    """AC-FR3000-01: all Maestro capabilities False -> OK."""
    validate_maestro_demotion(_valid_definition())  # no raise


@pytest.mark.real_module
def test_validate_maestro_demotion_rejects_spawn_capability():
    """AC-FR3000-01: Maestro cannot spawn specialist Agents."""
    bad = WorkflowDefinition(
        maestro_can_spawn_specialist_agent=True,
        maestro_can_advance=False,
        maestro_can_regress=False,
        maestro_can_waive=False,
        maestro_can_commit=False,
        maestro_can_release=False,
        maestro_can_archive=False,
        maestro_can_manage_branch=False,
        maestro_advisory_changes_state=False,
    )
    with pytest.raises(KeeperMaestroError) as exc:
        validate_maestro_demotion(bad)
    assert exc.value.code == "MAESTRO_SPAWN_FORBIDDEN"


@pytest.mark.real_module
def test_validate_maestro_demotion_rejects_advance_capability():
    """AC-FR3000-01: Maestro cannot advance workflow state."""
    bad = WorkflowDefinition(
        maestro_can_spawn_specialist_agent=False,
        maestro_can_advance=True,  # forbidden
        maestro_can_regress=False,
        maestro_can_waive=False,
        maestro_can_commit=False,
        maestro_can_release=False,
        maestro_can_archive=False,
        maestro_can_manage_branch=False,
        maestro_advisory_changes_state=False,
    )
    with pytest.raises(KeeperMaestroError) as exc:
        validate_maestro_demotion(bad)
    assert exc.value.code == "MAESTRO_ADVANCE_FORBIDDEN"


@pytest.mark.real_module
def test_validate_maestro_demotion_rejects_regress_capability():
    """AC-FR3000-01: Maestro cannot regress workflow state."""
    bad = WorkflowDefinition(
        maestro_can_spawn_specialist_agent=False,
        maestro_can_advance=False,
        maestro_can_regress=True,  # forbidden
        maestro_can_waive=False,
        maestro_can_commit=False,
        maestro_can_release=False,
        maestro_can_archive=False,
        maestro_can_manage_branch=False,
        maestro_advisory_changes_state=False,
    )
    with pytest.raises(KeeperMaestroError) as exc:
        validate_maestro_demotion(bad)
    assert exc.value.code == "MAESTRO_REGRESS_FORBIDDEN"


@pytest.mark.real_module
def test_validate_maestro_demotion_rejects_waive_capability():
    """AC-FR3000-01: Maestro cannot waive gates."""
    bad = WorkflowDefinition(
        maestro_can_spawn_specialist_agent=False,
        maestro_can_advance=False,
        maestro_can_regress=False,
        maestro_can_waive=True,  # forbidden
        maestro_can_commit=False,
        maestro_can_release=False,
        maestro_can_archive=False,
        maestro_can_manage_branch=False,
        maestro_advisory_changes_state=False,
    )
    with pytest.raises(KeeperMaestroError) as exc:
        validate_maestro_demotion(bad)
    assert exc.value.code == "MAESTRO_WAIVE_FORBIDDEN"


@pytest.mark.real_module
def test_validate_maestro_demotion_rejects_commit_capability():
    """AC-FR3000-01: Maestro cannot commit."""
    bad = WorkflowDefinition(
        maestro_can_spawn_specialist_agent=False,
        maestro_can_advance=False,
        maestro_can_regress=False,
        maestro_can_waive=False,
        maestro_can_commit=True,  # forbidden
        maestro_can_release=False,
        maestro_can_archive=False,
        maestro_can_manage_branch=False,
        maestro_advisory_changes_state=False,
    )
    with pytest.raises(KeeperMaestroError) as exc:
        validate_maestro_demotion(bad)
    assert exc.value.code == "MAESTRO_COMMIT_FORBIDDEN"


@pytest.mark.real_module
def test_validate_maestro_demotion_rejects_release_capability():
    """AC-FR3000-01: Maestro cannot release."""
    bad = WorkflowDefinition(
        maestro_can_spawn_specialist_agent=False,
        maestro_can_advance=False,
        maestro_can_regress=False,
        maestro_can_waive=False,
        maestro_can_commit=False,
        maestro_can_release=True,  # forbidden
        maestro_can_archive=False,
        maestro_can_manage_branch=False,
        maestro_advisory_changes_state=False,
    )
    with pytest.raises(KeeperMaestroError) as exc:
        validate_maestro_demotion(bad)
    assert exc.value.code == "MAESTRO_RELEASE_FORBIDDEN"


@pytest.mark.real_module
def test_validate_maestro_demotion_rejects_archive_capability():
    """AC-FR3000-01: Maestro cannot archive."""
    bad = WorkflowDefinition(
        maestro_can_spawn_specialist_agent=False,
        maestro_can_advance=False,
        maestro_can_regress=False,
        maestro_can_waive=False,
        maestro_can_commit=False,
        maestro_can_release=False,
        maestro_can_archive=True,  # forbidden
        maestro_can_manage_branch=False,
        maestro_advisory_changes_state=False,
    )
    with pytest.raises(KeeperMaestroError) as exc:
        validate_maestro_demotion(bad)
    assert exc.value.code == "MAESTRO_ARCHIVE_FORBIDDEN"


@pytest.mark.real_module
def test_validate_maestro_demotion_rejects_branch_management():
    """AC-FR3000-01: Maestro cannot manage branches."""
    bad = WorkflowDefinition(
        maestro_can_spawn_specialist_agent=False,
        maestro_can_advance=False,
        maestro_can_regress=False,
        maestro_can_waive=False,
        maestro_can_commit=False,
        maestro_can_release=False,
        maestro_can_archive=False,
        maestro_can_manage_branch=True,  # forbidden
        maestro_advisory_changes_state=False,
    )
    with pytest.raises(KeeperMaestroError) as exc:
        validate_maestro_demotion(bad)
    assert exc.value.code == "MAESTRO_BRANCH_FORBIDDEN"


@pytest.mark.real_module
def test_validate_maestro_demotion_rejects_advisory_state_change():
    """AC-FR3000-01: Maestro advisory cannot directly change persisted state."""
    bad = WorkflowDefinition(
        maestro_can_spawn_specialist_agent=False,
        maestro_can_advance=False,
        maestro_can_regress=False,
        maestro_can_waive=False,
        maestro_can_commit=False,
        maestro_can_release=False,
        maestro_can_archive=False,
        maestro_can_manage_branch=False,
        maestro_advisory_changes_state=True,  # forbidden
    )
    with pytest.raises(KeeperMaestroError) as exc:
        validate_maestro_demotion(bad)
    assert exc.value.code == "MAESTRO_ADVISORY_STATE_FORBIDDEN"


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-FR3000-01: ERROR_CODES includes all codes from interfaces.md §15."""
    expected = {
        "KEEPER_DISPATCH_FORBIDDEN",
        "KEEPER_DUAL_STATE_FORBIDDEN",
        "KEEPER_CAPABILITIES_NOT_MIGRATED",
        "MAESTRO_SPAWN_FORBIDDEN",
        "MAESTRO_ADVANCE_FORBIDDEN",
        "MAESTRO_REGRESS_FORBIDDEN",
        "MAESTRO_WAIVE_FORBIDDEN",
        "MAESTRO_COMMIT_FORBIDDEN",
        "MAESTRO_RELEASE_FORBIDDEN",
        "MAESTRO_ARCHIVE_FORBIDDEN",
        "MAESTRO_BRANCH_FORBIDDEN",
        "MAESTRO_ADVISORY_STATE_FORBIDDEN",
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
