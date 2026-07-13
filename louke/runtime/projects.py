"""Project lifecycle, backlog and project view composition (FR-1001).

This module manages the project entity that wraps a workflow run. A project
represents one development workflow in the current workspace. Non-terminal,
non-archived projects appear in the active list; terminal or archived projects
appear in the history list. At most one active non-hotfix (main) project may
exist at a time; a ``bug_fix`` project is the only parallel exception. When a
second main project is blocked, the story is saved to backlog for later use.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from louke.runtime.store import WorkflowRunStore


#: Workflow definition ids that represent hotfix workflows, which are the only
#: parallel exception to the single-active-main-project rule.
HOTFIX_DEFINITION_IDS: frozenset[str] = frozenset({"bug_fix"})

#: Terminal project statuses that move a project from the active list to history.
TERMINAL_STATUSES: frozenset[str] = frozenset(
    {"completed", "cancelled", "failed", "archived"}
)

#: Non-terminal statuses that keep a project in the active list.
ACTIVE_STATUS: str = "active"


class ProjectConflictError(Exception):
    """Raised when a second active main project would be created.

    The workspace allows at most one active non-hotfix project. When a
    creation request would violate this rule, the error is raised and the
    story is saved to backlog instead.
    """


class ProjectAlreadyExistsError(Exception):
    """Raised when a project with the same identity already exists."""


class ProjectNotFoundError(KeyError):
    """Raised when a requested project id does not exist."""


@dataclass(frozen=True, slots=True)
class Project:
    """An immutable project record wrapping a workflow run.

    Attributes:
        project_id: Opaque stable identifier for the project.
        run_id: The workflow run id this project wraps.
        name: Human-readable display title derived from the story.
        story_excerpt: Truncated story text for list display.
        release_version: The release version the project targets.
        workflow_definition_id: The workflow definition id (e.g. ``new_feature``).
        workflow_version: The immutable workflow definition version.
        status: Project lifecycle status (``active`` or a terminal status).
        created_at: ISO 8601 UTC timestamp of project creation.
        archived_at: ISO 8601 UTC timestamp of archival, when applicable.
    """

    project_id: str
    run_id: str
    name: str
    story_excerpt: str
    release_version: str
    workflow_definition_id: str
    workflow_version: str
    status: str = ACTIVE_STATUS
    created_at: str = ""
    archived_at: str | None = None


@dataclass(frozen=True, slots=True)
class ProjectSummary:
    """A list-item summary derived from a :class:`Project` and its run.

    Attributes:
        project_id: Opaque project identifier.
        name: Display name for the list item.
        story_excerpt: Truncated story text.
        release_version: Release version string.
        workflow_definition_id: Workflow type identifier.
        workflow_version: Workflow definition version.
        run_id: The wrapped workflow run id.
        run_status: Current run status, or ``None`` if the run is not loaded.
        current_step: Current run step, or ``None``.
        updated_at: Last update timestamp.
        archived_at: Archival timestamp, or ``None`` for active projects.
    """

    project_id: str
    name: str
    story_excerpt: str
    release_version: str
    workflow_definition_id: str
    workflow_version: str
    run_id: str
    run_status: str | None
    current_step: str | None
    updated_at: str
    archived_at: str | None


@dataclass(frozen=True, slots=True)
class BacklogEntry:
    """A story saved to backlog when project creation was blocked.

    Attributes:
        entry_id: Opaque stable identifier for the backlog entry.
        story: The story text the user tried to create a project with.
        release_version: The release version specified at creation time.
        workflow_definition_id: The workflow type the user selected.
        workflow_version: The workflow definition version.
        created_at: ISO 8601 UTC timestamp of the backlog entry.
    """

    entry_id: str
    story: str
    release_version: str
    workflow_definition_id: str
    workflow_version: str
    created_at: str


class ProjectTerminalStatus:
    """Stable terminal status constants for projects."""

    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
    ARCHIVED = "archived"


def _derive_name(story: str) -> str:
    """Return a display title derived from ``story``.

    The title is the first line of the story, truncated to 80 characters.
    """
    first_line = story.strip().split("\n", 1)[0].strip()
    if len(first_line) > 80:
        return first_line[:77] + "..."
    return first_line or "Untitled project"


def _excerpt(story: str, max_len: int = 120) -> str:
    """Return a truncated excerpt of ``story`` for list display."""
    stripped = story.strip().replace("\n", " ")
    if len(stripped) > max_len:
        return stripped[: max_len - 3] + "..."
    return stripped


class ProjectStore:
    """In-memory project collection with active/history partitioning.

    The store wraps a :class:`WorkflowRunStore` to create workflow runs when
    projects are created. It enforces the single-active-main-project rule
    and routes blocked stories to backlog.

    Args:
        run_store: The workflow run store used to create runs for projects.
    """

    def __init__(self, run_store: "WorkflowRunStore") -> None:
        self._run_store = run_store
        self._projects: dict[str, Project] = {}
        self._backlog: list[BacklogEntry] = []

    def create_project(
        self,
        story: str,
        release_version: str,
        definition_id: str,
        definition_version: str,
    ) -> Project:
        """Create a new project and its first workflow run.

        Args:
            story: The story text describing the project goal.
            release_version: The release version the project targets.
            definition_id: The workflow definition id (e.g. ``new_feature``).
            definition_version: The workflow definition version.

        Returns:
            The newly created :class:`Project`.

        Raises:
            ProjectConflictError: If an active non-hotfix project already
                exists and the new project is also non-hotfix. The story is
                saved to backlog before the error is raised.
        """
        if (
            self._has_active_main_project()
            and definition_id not in HOTFIX_DEFINITION_IDS
        ):
            entry = BacklogEntry(
                entry_id=f"bl_{uuid.uuid4().hex[:12]}",
                story=story,
                release_version=release_version,
                workflow_definition_id=definition_id,
                workflow_version=definition_version,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            self._backlog.append(entry)
            raise ProjectConflictError(
                "an active non-hotfix project already exists; story saved to backlog"
            )

        from louke.runtime.catalog import DefinitionNotFoundError
        from louke.runtime.store import DefinitionRegistry

        catalog: DefinitionRegistry | None = self._run_store._catalog
        if catalog is None:
            raise RuntimeError("run store has no catalog to resolve definitions")
        try:
            definition = catalog.get(definition_id, definition_version)
        except DefinitionNotFoundError:
            raise

        run = self._run_store.create_run(definition)
        now = datetime.now(timezone.utc).isoformat()
        project = Project(
            project_id=f"prj_{uuid.uuid4().hex[:12]}",
            run_id=run.run_id,
            name=_derive_name(story),
            story_excerpt=_excerpt(story),
            release_version=release_version,
            workflow_definition_id=definition_id,
            workflow_version=definition_version,
            status=ACTIVE_STATUS,
            created_at=now,
            archived_at=None,
        )
        self._projects[project.project_id] = project
        return project

    def archive_project(self, project_id: str) -> Project:
        """Mark ``project_id`` as archived and move it to history.

        Args:
            project_id: The project to archive.

        Returns:
            The archived project record.

        Raises:
            ProjectNotFoundError: If the project does not exist.
        """
        existing = self._projects.get(project_id)
        if existing is None:
            raise ProjectNotFoundError(f"project {project_id!r} not found")
        now = datetime.now(timezone.utc).isoformat()
        archived = Project(
            project_id=existing.project_id,
            run_id=existing.run_id,
            name=existing.name,
            story_excerpt=existing.story_excerpt,
            release_version=existing.release_version,
            workflow_definition_id=existing.workflow_definition_id,
            workflow_version=existing.workflow_version,
            status=ProjectTerminalStatus.ARCHIVED,
            created_at=existing.created_at,
            archived_at=now,
        )
        self._projects[project_id] = archived
        return archived

    def get_project(self, project_id: str) -> Project:
        """Return the project record for ``project_id``.

        Args:
            project_id: The opaque project identifier.

        Returns:
            The matching :class:`Project`.

        Raises:
            ProjectNotFoundError: If no project with the given id exists.
        """
        project = self._projects.get(project_id)
        if project is None:
            raise ProjectNotFoundError(f"project {project_id!r} not found")
        return project

    def list_active(self) -> tuple[ProjectSummary, ...]:
        """Return summaries of non-terminal, non-archived projects.

        Returns:
            A tuple of :class:`ProjectSummary` for active projects.
        """
        return tuple(
            self._to_summary(project)
            for project in self._projects.values()
            if project.status not in TERMINAL_STATUSES
        )

    def list_history(self) -> tuple[ProjectSummary, ...]:
        """Return summaries of terminal or archived projects.

        Returns:
            A tuple of :class:`ProjectSummary` for history projects.
        """
        return tuple(
            self._to_summary(project)
            for project in self._projects.values()
            if project.status in TERMINAL_STATUSES
        )

    def list_backlog(self) -> tuple[BacklogEntry, ...]:
        """Return all backlog entries.

        Returns:
            A tuple of :class:`BacklogEntry`.
        """
        return tuple(self._backlog)

    def _has_active_main_project(self) -> bool:
        """Return True if there is an active non-hotfix project."""
        return any(
            project.status not in TERMINAL_STATUSES
            and project.workflow_definition_id not in HOTFIX_DEFINITION_IDS
            for project in self._projects.values()
        )

    def _to_summary(self, project: Project) -> ProjectSummary:
        """Build a :class:`ProjectSummary` from a project, reading run status."""
        run_status: str | None = None
        current_step: str | None = None
        updated_at = project.created_at
        try:
            run = self._run_store.get_run(project.run_id)
            run_status = run.status
            current_step = run.current_step
            updated_at = run.updated_at
        except Exception:
            pass
        return ProjectSummary(
            project_id=project.project_id,
            name=project.name,
            story_excerpt=project.story_excerpt,
            release_version=project.release_version,
            workflow_definition_id=project.workflow_definition_id,
            workflow_version=project.workflow_version,
            run_id=project.run_id,
            run_status=run_status,
            current_step=current_step,
            updated_at=updated_at,
            archived_at=project.archived_at,
        )
