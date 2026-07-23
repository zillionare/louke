"""FR-3000: Keeper retirement & Maestro demotion.

The canonical WorkflowDefinition/ResponsibilityCatalog must NOT contain
Keeper semantic dispatch; Keeper's format/RGR/AC-trace/anti-pattern/
regression capabilities must migrate to Runtime-registered program checks.
A retained Keeper CLI is only a compatibility entrypoint to the same
handler; it must NOT write a second state authority.  Maestro prompt/tools
must NOT have spawn-of-specialist-Agent/advance/regress/waive/commit/
release/archive/branch-management capabilities; its advisory must NOT
directly change persisted workflow state (AC-FR3000-01).
"""

from __future__ import annotations

from dataclasses import dataclass

ERROR_CODES = (
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
)

_REQUIRED_RUNTIME_PROGRAM_CHECKS: frozenset[str] = frozenset(
    {
        "format",
        "rgr",
        "ac-trace",
        "anti-pattern",
        "regression",
    }
)


class KeeperMaestroError(Exception):
    """A fail-closed retirement/demotion rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class RuntimeResponsibilityCatalog:
    """The canonical Runtime responsibility catalog (AC-FR3000-01).

    Attributes:
        semantic_dispatch_roles: Tuple of roles with semantic dispatch
            (must NOT include ``keeper``).
        keeper_dispatch: ``True`` if Keeper is still a dispatched role (forbidden).
        keeper_cli_compat: ``True`` if a compat CLI entrypoint is retained.
        keeper_cli_writes_state: ``True`` if the compat CLI writes a second
            state authority (forbidden).
        runtime_program_checks: Tuple of program checks Keeper previously
            owned (must include format/RGR/AC-trace/anti-pattern/regression).
    """

    semantic_dispatch_roles: tuple[str, ...]
    keeper_dispatch: bool
    keeper_cli_compat: bool
    keeper_cli_writes_state: bool
    runtime_program_checks: tuple[str, ...]


def validate_keeper_retirement(catalog: RuntimeResponsibilityCatalog) -> None:
    """Validate that Keeper has been retired (AC-FR3000-01).

    Args:
        catalog: :class:`RuntimeResponsibilityCatalog` to validate.

    Raises:
        KeeperMaestroError: With ``KEEPER_DISPATCH_FORBIDDEN`` if Keeper is
            still a dispatched role; ``KEEPER_DUAL_STATE_FORBIDDEN`` if the
            compat CLI writes a second state authority;
            ``KEEPER_CAPABILITIES_NOT_MIGRATED`` if the required program
            checks have not been migrated to Runtime.
    """
    if catalog.keeper_dispatch:
        raise KeeperMaestroError(
            "KEEPER_DISPATCH_FORBIDDEN",
            "canonical catalog still contains Keeper semantic dispatch",
        )
    if catalog.keeper_cli_writes_state:
        raise KeeperMaestroError(
            "KEEPER_DUAL_STATE_FORBIDDEN",
            "compat Keeper CLI writes a second state authority",
        )
    missing = _REQUIRED_RUNTIME_PROGRAM_CHECKS - set(catalog.runtime_program_checks)
    if missing:
        raise KeeperMaestroError(
            "KEEPER_CAPABILITIES_NOT_MIGRATED",
            f"Keeper capabilities not migrated to Runtime: {sorted(missing)}",
        )


@dataclass(frozen=True)
class WorkflowDefinition:
    """The canonical WorkflowDefinition with Maestro capabilities (AC-FR3000-01).

    All Maestro capabilities listed must be ``False`` for compliance.
    """

    maestro_can_spawn_specialist_agent: bool
    maestro_can_advance: bool
    maestro_can_regress: bool
    maestro_can_waive: bool
    maestro_can_commit: bool
    maestro_can_release: bool
    maestro_can_archive: bool
    maestro_can_manage_branch: bool
    maestro_advisory_changes_state: bool


def validate_maestro_demotion(definition: WorkflowDefinition) -> None:
    """Validate that Maestro has been demoted (AC-FR3000-01).

    Args:
        definition: :class:`WorkflowDefinition` to validate.

    Raises:
        KeeperMaestroError: With a stable code from :data:`ERROR_CODES` for
            any forbidden Maestro capability.
    """
    if definition.maestro_can_spawn_specialist_agent:
        raise KeeperMaestroError(
            "MAESTRO_SPAWN_FORBIDDEN",
            "Maestro must not spawn specialist Agents",
        )
    if definition.maestro_can_advance:
        raise KeeperMaestroError(
            "MAESTRO_ADVANCE_FORBIDDEN",
            "Maestro must not advance workflow state",
        )
    if definition.maestro_can_regress:
        raise KeeperMaestroError(
            "MAESTRO_REGRESS_FORBIDDEN",
            "Maestro must not regress workflow state",
        )
    if definition.maestro_can_waive:
        raise KeeperMaestroError(
            "MAESTRO_WAIVE_FORBIDDEN",
            "Maestro must not waive gates",
        )
    if definition.maestro_can_commit:
        raise KeeperMaestroError(
            "MAESTRO_COMMIT_FORBIDDEN",
            "Maestro must not commit",
        )
    if definition.maestro_can_release:
        raise KeeperMaestroError(
            "MAESTRO_RELEASE_FORBIDDEN",
            "Maestro must not release",
        )
    if definition.maestro_can_archive:
        raise KeeperMaestroError(
            "MAESTRO_ARCHIVE_FORBIDDEN",
            "Maestro must not archive",
        )
    if definition.maestro_can_manage_branch:
        raise KeeperMaestroError(
            "MAESTRO_BRANCH_FORBIDDEN",
            "Maestro must not manage branches",
        )
    if definition.maestro_advisory_changes_state:
        raise KeeperMaestroError(
            "MAESTRO_ADVISORY_STATE_FORBIDDEN",
            "Maestro advisory must not directly change persisted workflow state",
        )
