"""AC-FR3000-01: Keeper retirement & Maestro demotion.

The canonical WorkflowDefinition/ResponsibilityCatalog must NOT contain
Keeper semantic dispatch; Keeper's format/RGR/AC-trace/anti-pattern/
regression capabilities must migrate to Runtime-registered program checks.
A retained Keeper CLI is only a compatibility entrypoint to the same
handler; it must NOT write a second state authority.  Maestro prompt/tools
must NOT have spawn-of-specialist-Agent/advance/regress/waive/commit/
release/archive/branch-management capabilities; its advisory must NOT
directly change persisted workflow state.
"""

from __future__ import annotations


import pytest

from louke.runtime.keeper_maestro import (
    KeeperMaestroError,
    RuntimeResponsibilityCatalog,
    WorkflowDefinition,
    validate_keeper_retirement,
    validate_maestro_demotion,
)


def _catalog(
    *,
    has_keeper_dispatch: bool = False,
    keeper_cli_compat: bool = True,
    dual_state_authority: bool = False,
) -> RuntimeResponsibilityCatalog:
    return RuntimeResponsibilityCatalog(
        semantic_dispatch_roles=(
            "archer",
            "devon",
            "shield",
            "prism",
            "judge",
            "librarian",
            "maestro",
        ),
        keeper_dispatch=has_keeper_dispatch,
        keeper_cli_compat=keeper_cli_compat,
        keeper_cli_writes_state=dual_state_authority,
        runtime_program_checks=(
            "format",
            "rgr",
            "ac-trace",
            "anti-pattern",
            "regression",
        ),
    )


def _maestro(
    *,
    can_spawn: bool = False,
    can_advance: bool = False,
    can_regress: bool = False,
    can_waive: bool = False,
    can_commit: bool = False,
    can_release: bool = False,
    can_archive: bool = False,
    can_manage_branch: bool = False,
    advisory_changes_state: bool = False,
) -> WorkflowDefinition:
    return WorkflowDefinition(
        maestro_can_spawn_specialist_agent=can_spawn,
        maestro_can_advance=can_advance,
        maestro_can_regress=can_regress,
        maestro_can_waive=can_waive,
        maestro_can_commit=can_commit,
        maestro_can_release=can_release,
        maestro_can_archive=can_archive,
        maestro_can_manage_branch=can_manage_branch,
        maestro_advisory_changes_state=advisory_changes_state,
    )


def test_keeper_retirement_passes_when_no_dispatch_and_runtime_has_program_checks() -> (
    None
):
    """AC-FR3000-01: catalog without Keeper dispatch + migrated program checks PASS."""
    catalog = _catalog()
    validate_keeper_retirement(catalog)  # does not raise


def test_keeper_retirement_rejects_keeper_dispatch() -> None:
    """AC-FR3000-01: canonical catalog must not have Keeper semantic dispatch."""
    with pytest.raises(KeeperMaestroError) as exc:
        validate_keeper_retirement(_catalog(has_keeper_dispatch=True))
    assert exc.value.code == "KEEPER_DISPATCH_FORBIDDEN"


def test_keeper_retirement_rejects_dual_state_authority() -> None:
    """AC-FR3000-01: compat Keeper CLI must not write second state authority."""
    with pytest.raises(KeeperMaestroError) as exc:
        validate_keeper_retirement(_catalog(dual_state_authority=True))
    assert exc.value.code == "KEEPER_DUAL_STATE_FORBIDDEN"


def test_keeper_retirement_rejects_missing_runtime_program_checks() -> None:
    """AC-FR3000-01: Keeper capabilities must migrate to Runtime program checks."""
    catalog = _catalog()
    catalog_no_checks = RuntimeResponsibilityCatalog(
        semantic_dispatch_roles=catalog.semantic_dispatch_roles,
        keeper_dispatch=False,
        keeper_cli_compat=True,
        keeper_cli_writes_state=False,
        runtime_program_checks=(),  # missing
    )
    with pytest.raises(KeeperMaestroError) as exc:
        validate_keeper_retirement(catalog_no_checks)
    assert exc.value.code == "KEEPER_CAPABILITIES_NOT_MIGRATED"


def test_maestro_demotion_passes_when_no_forbidden_capabilities() -> None:
    """AC-FR3000-01: Maestro without spawn/advance/regress/waive/commit/release/archive."""
    validate_maestro_demotion(_maestro())  # does not raise


def test_maestro_demotion_rejects_spawn_specialist_agent() -> None:
    """AC-FR3000-01: Maestro must not spawn specialist Agents."""
    with pytest.raises(KeeperMaestroError) as exc:
        validate_maestro_demotion(_maestro(can_spawn=True))
    assert exc.value.code == "MAESTRO_SPAWN_FORBIDDEN"


def test_maestro_demotion_rejects_advance() -> None:
    """AC-FR3000-01: Maestro must not advance workflow state."""
    with pytest.raises(KeeperMaestroError) as exc:
        validate_maestro_demotion(_maestro(can_advance=True))
    assert exc.value.code == "MAESTRO_ADVANCE_FORBIDDEN"


def test_maestro_demotion_rejects_waive() -> None:
    """AC-FR3000-01: Maestro must not waive gates."""
    with pytest.raises(KeeperMaestroError) as exc:
        validate_maestro_demotion(_maestro(can_waive=True))
    assert exc.value.code == "MAESTRO_WAIVE_FORBIDDEN"


def test_maestro_demotion_rejects_commit_release_archive() -> None:
    """AC-FR3000-01: Maestro must not commit/release/archive."""
    for capability, code in [
        ("can_commit", "MAESTRO_COMMIT_FORBIDDEN"),
        ("can_release", "MAESTRO_RELEASE_FORBIDDEN"),
        ("can_archive", "MAESTRO_ARCHIVE_FORBIDDEN"),
    ]:
        with pytest.raises(KeeperMaestroError) as exc:
            validate_maestro_demotion(_maestro(**{capability: True}))
        assert exc.value.code == code


def test_maestro_demotion_rejects_branch_management() -> None:
    """AC-FR3000-01: Maestro must not manage branches."""
    with pytest.raises(KeeperMaestroError) as exc:
        validate_maestro_demotion(_maestro(can_manage_branch=True))
    assert exc.value.code == "MAESTRO_BRANCH_FORBIDDEN"


def test_maestro_demotion_rejects_advisory_changing_state() -> None:
    """AC-FR3000-01: Maestro advisory must not directly change persisted state."""
    with pytest.raises(KeeperMaestroError) as exc:
        validate_maestro_demotion(_maestro(advisory_changes_state=True))
    assert exc.value.code == "MAESTRO_ADVISORY_STATE_FORBIDDEN"
