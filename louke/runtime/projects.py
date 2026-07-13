"""Project lifecycle, backlog and project view composition (FR-1001).

This module manages the project entity that wraps a workflow run. A project
represents one development workflow in the current workspace. Non-terminal,
non-archived projects appear in the active list; terminal or archived projects
appear in the history list. At most one active non-hotfix (main) project may
exist at a time; a ``bug_fix`` project is the only parallel exception. When a
second main project is blocked, the story is saved to backlog for later use.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from louke.runtime.contract_gates import (
    BugFixInheritanceVerifier,
    HotfixInheritanceError,
    InheritedApproval,
    SourceContract,
)

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


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    """A selectable workflow definition in the project creation catalog.

    Attributes:
        definition_id: The workflow definition id (e.g. ``new_feature``).
        version: The immutable definition version.
        label: Human-readable label for the workflow.
        is_hotfix: ``True`` for bug_fix workflows (published product hotfix).
    """

    definition_id: str
    version: str
    label: str
    is_hotfix: bool


@dataclass(frozen=True, slots=True)
class ProjectPreview:
    """A non-persisted preview of a project before confirmation.

    Attributes:
        preview_id: Opaque stable identifier for the preview, used by
            :meth:`ProjectStore.confirm_project` to create the project.
        story_excerpt: Truncated story text for display.
        release_version: The release version the project targets.
        workflow_definition_id: The workflow definition id.
        workflow_version: The workflow definition version.
        project_id: Always ``None`` until the preview is confirmed.
        source_contract: The source contract for bug_fix previews, if any.
    """

    preview_id: str
    story_excerpt: str
    release_version: str
    workflow_definition_id: str
    workflow_version: str
    project_id: str | None = None
    source_contract: dict[str, Any] | None = None


#: The set of workflow definition ids directly offered in the first-version
#: catalog. ``spec_change`` is intentionally excluded.
_CATALOG_DEFINITION_IDS: tuple[str, ...] = ("new_feature", "bug_fix")

_CATALOG_LABELS: dict[str, str] = {
    "new_feature": "New feature",
    "bug_fix": "Bug fix (hotfix)",
}

#: Regex for validating release version strings like ``v0.12.0``.
_RELEASE_VERSION_RE = re.compile(r"^v\d+\.\d+\.\d+$")


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
        self._previews: dict[str, ProjectPreview] = {}

    def list_workflow_catalog(self) -> tuple[CatalogEntry, ...]:
        """Return the selectable workflow definitions for project creation.

        Only ``new_feature`` and ``bug_fix`` are directly offered.
        ``spec_change`` is excluded from the first-version catalog.

        Returns:
            A tuple of :class:`CatalogEntry`.
        """
        return tuple(
            CatalogEntry(
                definition_id=def_id,
                version="1",
                label=_CATALOG_LABELS.get(def_id, def_id),
                is_hotfix=def_id in HOTFIX_DEFINITION_IDS,
            )
            for def_id in _CATALOG_DEFINITION_IDS
        )

    def preview_project(
        self,
        story: str,
        release_version: str,
        definition_id: str,
        definition_version: str,
        source_contract: dict[str, Any] | None = None,
    ) -> ProjectPreview:
        """Validate inputs and return a preview without creating a project.

        Args:
            story: The story text describing the project goal.
            release_version: The release version (must match ``vX.Y.Z``).
            definition_id: The workflow definition id.
            definition_version: The workflow definition version.
            source_contract: Required for bug_fix; must reference a GitHub
                Issue and an approved source spec/AC.

        Returns:
            A :class:`ProjectPreview` that can be confirmed via
            :meth:`confirm_project`.

        Raises:
            ValueError: If story is empty, release version is invalid, or
                bug_fix is missing a valid source contract.
            KeyError: If the workflow definition is not in the catalog.
            ProjectConflictError: If a second active main project would be
                created; the story is saved to backlog.
        """
        if not story.strip():
            raise ValueError("story is required")

        if not _RELEASE_VERSION_RE.match(release_version):
            raise ValueError(
                f"invalid release version {release_version!r}; expected format vX.Y.Z"
            )

        if definition_id not in _CATALOG_DEFINITION_IDS:
            raise KeyError(f"workflow {definition_id!r} is not in the catalog")

        if definition_id == "bug_fix" and source_contract is None:
            raise ValueError("bug_fix requires a source_contract")

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

        preview = ProjectPreview(
            preview_id=f"prev_{uuid.uuid4().hex[:12]}",
            story_excerpt=_excerpt(story),
            release_version=release_version,
            workflow_definition_id=definition_id,
            workflow_version=definition_version,
            project_id=None,
            source_contract=source_contract,
        )
        self._previews[preview.preview_id] = preview
        return preview

    def confirm_project(self, preview_id: str) -> Project:
        """Create the project from a previously returned preview.

        Args:
            preview_id: The preview id returned by :meth:`preview_project`.

        Returns:
            The newly created :class:`Project`.

        Raises:
            KeyError: If the preview id does not exist.
        """
        preview = self._previews.get(preview_id)
        if preview is None:
            raise KeyError(f"preview {preview_id!r} not found")

        project = self.create_project(
            story=preview.story_excerpt,
            release_version=preview.release_version,
            definition_id=preview.workflow_definition_id,
            definition_version=preview.workflow_version,
            source_contract=preview.source_contract,
        )
        del self._previews[preview_id]
        return project

    def create_project(
        self,
        story: str,
        release_version: str,
        definition_id: str,
        definition_version: str,
        source_contract: dict[str, Any] | None = None,
    ) -> Project:
        """Create a new project and its first workflow run.

        Args:
            story: The story text describing the project goal.
            release_version: The release version the project targets.
            definition_id: The workflow definition id (e.g. ``new_feature``).
            definition_version: The workflow definition version.
            source_contract: Required for bug_fix; must reference a GitHub
                Issue and an approved source spec/AC.

        Returns:
            The newly created :class:`Project`.

        Raises:
            ProjectConflictError: If an active non-hotfix project already
                exists and the new project is also non-hotfix. The story is
                saved to backlog before the error is raised.
            ValueError: If bug_fix is missing a valid source contract.
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

        if definition_id == "bug_fix" and source_contract is not None:
            self._apply_bug_fix_inheritance(run.run_id, source_contract)

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

    def _apply_bug_fix_inheritance(
        self, run_id: str, source_contract: dict[str, Any]
    ) -> None:
        """Verify source contract and record inherited requirements approval.

        Args:
            run_id: The bug_fix run inheriting the approval.
            source_contract: The source contract dict referencing a GitHub
                Issue and an approved source spec/AC.

        Raises:
            ValueError: If the source contract is invalid or the referenced
                source approval is not actually approved.
        """
        try:
            contract = SourceContract(
                github_issue=source_contract["github_issue"],
                source_spec_digest=source_contract["source_spec_digest"],
                source_acceptance_digest=source_contract["source_acceptance_digest"],
                source_approval_gate_id=source_contract["source_approval_gate_id"],
                source_approval_bound_digest=source_contract[
                    "source_approval_bound_digest"
                ],
                behavior_change=source_contract["behavior_change"],
            )
        except KeyError as exc:
            raise ValueError(f"source_contract missing field: {exc}") from exc

        verifier = BugFixInheritanceVerifier(self._run_store)
        try:
            inherited = verifier.verify(run_id, contract)
        except HotfixInheritanceError as exc:
            raise ValueError(str(exc)) from exc

        _record_inherited_gate(
            self._run_store,
            run_id=run_id,
            inherited=inherited,
        )

    def archive_project(self, project_id: str) -> Project:
        """Mark ``project_id`` as archived and move it to history.

        The run's status is also set to ``archived`` so the orchestrator
        rejects any further transitions on it.

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
        run = self._run_store.get_run(existing.run_id)
        self._run_store.update_run(
            run.with_status(ProjectTerminalStatus.ARCHIVED),
            run.revision,
        )
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


def _record_inherited_gate(
    run_store: "WorkflowRunStore",
    run_id: str,
    inherited: InheritedApproval,
) -> None:
    """Persist an inherited requirements gate for a bug_fix run.

    Args:
        run_store: The workflow run store.
        run_id: The bug_fix run inheriting the approval.
        inherited: The inherited approval record.
    """
    from louke.runtime.contract_gates import _make_inherited_gate

    run = run_store.get_run(run_id)
    now = datetime.now(timezone.utc).isoformat()
    gate = _make_inherited_gate(
        run_id=run_id,
        step_id="requirements_approval",
        bound_digest=inherited.bound_digest,
        expected_revision=run.revision,
        created_at=now,
        decided_at=inherited.inherited_at,
    )
    run_store.create_gate(gate)
