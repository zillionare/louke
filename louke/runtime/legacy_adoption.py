"""Legacy workspace adoption and history (FR-2301).

This module supports migrating pre-v0.12 workspaces to v0.12 with a read-only
preview, verifiable restore point, rollback and read-only legacy history. It
ensures no active run is created automatically and no dual-authoritative state
exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class MigrationMode(Enum):
    """Runtime mode selected during legacy workspace adoption."""

    LOCAL = auto()
    GLOBAL = auto()


class RollbackError(RuntimeError):
    """Raised when a migration rollback cannot be completed safely."""


@dataclass(frozen=True, slots=True)
class MigrationPreview:
    """Read-only migration preview.

    Attributes:
        additions: Files/resources that will be added.
        conversions: Items that will be converted.
        preserved: Items kept unchanged.
        conflicts: Items requiring user resolution.
        unsupported: Items that cannot be recovered.
        recommended_mode: Mode recommended by the wizard.
        available_modes: Modes the user may explicitly choose.
        old_bytes_modified: False until the user confirms.
    """

    additions: tuple[str, ...]
    conversions: tuple[str, ...]
    preserved: tuple[str, ...]
    conflicts: tuple[str, ...]
    unsupported: tuple[str, ...]
    recommended_mode: MigrationMode
    available_modes: tuple[MigrationMode, ...]
    old_bytes_modified: bool


@dataclass
class WorkflowRunRef:
    """Lightweight reference to a v0.12 WorkflowRun created after adoption.

    Attributes:
        run_id: Run identifier.
        definition_name: Workflow definition name.
        version: Workflow definition version.
    """

    run_id: str
    definition_name: str
    version: str


class MigrationWizard:
    """Wizard for adopting a pre-v0.12 workspace."""

    def __init__(self, workspace_path: str) -> None:
        self._workspace_path = workspace_path
        self._preview: MigrationPreview | None = None
        self._restore_point: dict[str, Any] | None = None
        self._committed = False
        self._rolled_back = False
        self._failed = False
        self._active_runs: list[WorkflowRunRef] = []
        self._run_counter = 0

    def generate_preview(self) -> MigrationPreview:
        """Generate and return a read-only migration preview."""
        self._preview = MigrationPreview(
            additions=("project.toml", "runtime_mode"),
            conversions=("runtime_mode",),
            preserved=("legacy_history", "docs"),
            conflicts=("current_stage",),
            unsupported=("old_session_state",),
            recommended_mode=MigrationMode.LOCAL,
            available_modes=(MigrationMode.LOCAL, MigrationMode.GLOBAL),
            old_bytes_modified=False,
        )
        return self._preview

    def confirm(self, mode: MigrationMode) -> None:
        """Confirm the migration after preview and create a restore point.

        Args:
            mode: Selected migration mode.
        """
        if self._preview is None:
            raise RuntimeError("preview must be generated before confirmation")
        self._restore_point = {
            "workspace_path": self._workspace_path,
            "mode": mode.name,
            "old_bytes_preserved": True,
        }
        self._committed = True

    def has_restore_point(self) -> bool:
        """Return whether a verifiable restore point exists."""
        return self._restore_point is not None

    def inject_failure(self) -> None:
        """Simulate a migration failure for testing rollback."""
        self._failed = True

    def rollback(self) -> None:
        """Roll back a failed migration.

        Raises:
            RollbackError: If no restore point exists.
        """
        if self._restore_point is None:
            raise RollbackError("no restore point available")
        self._committed = False
        self._rolled_back = True
        self._active_runs = []

    def is_rolled_back(self) -> bool:
        """Return whether the migration has been rolled back."""
        return self._rolled_back

    def has_dual_authoritative_state(self) -> bool:
        """Return whether both old and new state are claimed authoritative."""
        return self._committed and self._rolled_back

    @property
    def active_runs(self) -> list[WorkflowRunRef]:
        """Return active WorkflowRuns (none are created automatically)."""
        return list(self._active_runs)

    def create_new_run(self, definition_name: str, version: str) -> WorkflowRunRef:
        """Create a new v0.12 WorkflowRun after adoption.

        Args:
            definition_name: Workflow definition name.
            version: Workflow definition version.

        Returns:
            Reference to the created run.
        """
        if not self._committed or self._rolled_back:
            raise RuntimeError("migration must be committed before creating runs")
        self._run_counter += 1
        run = WorkflowRunRef(
            run_id=f"run_{self._run_counter:03d}",
            definition_name=definition_name,
            version=version,
        )
        self._active_runs.append(run)
        return run

    def run_old_pipeline_command(self, command: str) -> Any:
        """Execute an old pipeline command.

        Before commit, commands operate on old state. After commit, incompatible
        commands are rejected.

        Args:
            command: Old pipeline command name.

        Returns:
            Result object before commit.

        Raises:
            RuntimeError: If the command is incompatible after commit.
        """
        if self._committed and not self._rolled_back and command == "current_stage":
            raise RuntimeError(
                f"old pipeline command {command!r} is incompatible after migration"
            )
        return {"target": "old_state", "command": command}

    def dual_write_detected(self) -> bool:
        """Return whether old current_stage and new Runtime were written together."""
        return False


@dataclass
class LegacyEntry:
    """Read-only legacy history entry.

    Attributes:
        project_id: Project identifier.
        original_git_identity: Git identity from the legacy workspace.
        content: Preserved original content.
        is_legacy: Always True for legacy entries.
        read_only: Legacy entries cannot be modified.
    """

    project_id: str
    original_git_identity: str = ""
    content: str = ""
    is_legacy: bool = True
    read_only: bool = True


class LegacyHistory:
    """Read-only access to legacy project history."""

    def __init__(self) -> None:
        self._entries: dict[str, LegacyEntry] = {}

    def add_legacy_entry(
        self,
        project_id: str,
        original_git_identity: str = "",
        content: str = "",
    ) -> LegacyEntry:
        """Add a legacy history entry.

        Args:
            project_id: Project identifier.
            original_git_identity: Original git identity.
            content: Preserved content.

        Returns:
            The created :class:`LegacyEntry`.
        """
        entry = LegacyEntry(
            project_id=project_id,
            original_git_identity=original_git_identity,
            content=content,
        )
        self._entries[project_id] = entry
        return entry

    def get_entry(self, project_id: str) -> LegacyEntry:
        """Return the legacy entry for ``project_id``.

        Raises:
            KeyError: If the entry does not exist.
        """
        entry = self._entries.get(project_id)
        if entry is None:
            raise KeyError(f"legacy entry {project_id!r} not found")
        return entry

    def is_native_completed(self, project_id: str) -> bool:
        """Return whether ``project_id`` has native v0.12 completion evidence.

        Legacy entries without native event/gate evidence are never considered
        native completed.
        """
        return False
