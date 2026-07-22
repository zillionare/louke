"""FR-1001: Projects navigation and history.

AC references:
- AC-FR1001-01: Projects menu exposes current list, history list and
  create-new-project entry.
- AC-FR1001-02: non-terminal, non-archived projects appear only in the
  current list; terminal/archived projects appear only in the history list.
- AC-FR1001-03: each list item shows distinguishing name, release version,
  workflow type and status, and can be opened for detail.
- AC-FR1001-04: an active non-hotfix Project blocks creation of a second
  main Project; the new story is saved to backlog and the existing run is
  unchanged.
- AC-FR1001-05: a valid hotfix Project can exist alongside an active main
  Project; the two runs do not cross-write identity, state or events.
"""

from __future__ import annotations

import pytest

from louke.runtime.catalog import DefinitionRegistry, Edge, Step, WorkflowDefinition
from louke.runtime.projects import (
    ProjectConflictError,
    ProjectStore,
)
from louke.runtime.store import WorkflowRunStore


# -- Definition helpers -------------------------------------------------------


def _new_feature_definition() -> WorkflowDefinition:
    """Return a minimal new_feature definition."""
    start = Step(
        step_id="start",
        kind="program",
        transitions=(Edge("e1", "start", "requirements_approval", "done"),),
        implemented=True,
    )
    req = Step(
        step_id="requirements_approval",
        kind="human_gate",
        transitions=(Edge("e2", "requirements_approval", "design", "approved"),),
        implemented=True,
    )
    design = Step(step_id="design", kind="program", implemented=True)
    return WorkflowDefinition(
        definition_id="new_feature",
        version="1",
        start_step="start",
        steps=(start, req, design),
    )


def _bug_fix_definition() -> WorkflowDefinition:
    """Return a minimal bug_fix definition."""
    verify = Step(
        step_id="source_contract_verify",
        kind="program",
        transitions=(Edge("e3", "source_contract_verify", "reproduce", "verified"),),
        implemented=True,
    )
    reproduce = Step(step_id="reproduce", kind="program", implemented=True)
    return WorkflowDefinition(
        definition_id="bug_fix",
        version="1",
        start_step="source_contract_verify",
        steps=(verify, reproduce),
    )


def _create_registry_and_store() -> tuple[DefinitionRegistry, WorkflowRunStore]:
    """Register definitions and return a registry + run store."""
    registry = DefinitionRegistry()
    registry.register(_new_feature_definition())
    registry.register(_bug_fix_definition())
    store = WorkflowRunStore(catalog=registry)
    return registry, store


# -- AC-FR1001-01 -------------------------------------------------------------


def test_ac_fr1001_01_projects_menu_exposes_current_history_create():
    """AC-FR1001-01: project store exposes current, history and create entry.

    The ``ProjectStore`` must partition projects into active (current) and
    terminal (history) collections, and provide a method to create new
    projects. This mirrors the sidebar menu contract.
    """
    registry, run_store = _create_registry_and_store()
    project_store = ProjectStore(run_store=run_store)

    # Initially both lists are empty but accessible
    assert project_store.list_active() == ()
    assert project_store.list_history() == ()

    # Create a new project
    project = project_store.create_project(
        story="Build programmatic workflow runtime",
        release_version="v0.12.0",
        definition_id="new_feature",
        definition_version="1",
    )
    assert project.project_id.startswith("prj_")
    assert project.name == "Build programmatic workflow runtime"
    assert project.release_version == "v0.12.0"
    assert project.workflow_definition_id == "new_feature"
    assert project.workflow_version == "1"

    active = project_store.list_active()
    assert len(active) == 1
    assert active[0].project_id == project.project_id


# -- AC-FR1001-02 -------------------------------------------------------------


def test_ac_fr1001_02_terminal_projects_only_in_history():
    """AC-FR1001-02: terminal/archived projects appear only in history.

    A project whose status is terminal (cancelled, completed, or
    archived) must appear in the history list, not in the active list.
    A non-terminal project must appear only in the active list.
    """
    registry, run_store = _create_registry_and_store()
    project_store = ProjectStore(run_store=run_store)

    active_project = project_store.create_project(
        story="Active project",
        release_version="v0.12.0",
        definition_id="new_feature",
        definition_version="1",
    )
    completed_project = project_store.create_project(
        story="Completed project",
        release_version="v0.11.0",
        definition_id="bug_fix",
        definition_version="1",
    )
    project_store.archive_project(completed_project.project_id)

    active = project_store.list_active()
    history = project_store.list_history()

    active_ids = {p.project_id for p in active}
    history_ids = {p.project_id for p in history}

    assert active_project.project_id in active_ids
    assert active_project.project_id not in history_ids
    assert completed_project.project_id in history_ids
    assert completed_project.project_id not in active_ids


# -- AC-FR1001-03 -------------------------------------------------------------


def test_ac_fr1001_03_list_items_show_distinguishing_fields():
    """AC-FR1001-03: each list item shows name, version, workflow type, status.

    ``ProjectSummary`` must carry enough fields to distinguish two projects
    by name, release version, workflow type and run status.
    """
    registry, run_store = _create_registry_and_store()
    project_store = ProjectStore(run_store=run_store)

    project_a = project_store.create_project(
        story="Feature A",
        release_version="v0.12.0",
        definition_id="new_feature",
        definition_version="1",
    )
    project_b = project_store.create_project(
        story="Feature B",
        release_version="v0.13.0",
        definition_id="bug_fix",
        definition_version="1",
    )

    summaries = project_store.list_active()
    assert len(summaries) == 2

    summary_a = next(s for s in summaries if s.project_id == project_a.project_id)
    summary_b = next(s for s in summaries if s.project_id == project_b.project_id)

    assert summary_a.name != summary_b.name
    assert summary_a.release_version != summary_b.release_version
    assert summary_a.workflow_definition_id != summary_b.workflow_definition_id
    assert summary_a.run_status == "in_progress"
    assert summary_b.run_status == "in_progress"

    detail = project_store.get_project(project_a.project_id)
    assert detail.project_id == project_a.project_id


# -- AC-FR1001-04 -------------------------------------------------------------


def test_ac_fr1001_04_second_main_project_blocked_and_backlog_saved():
    """AC-FR1001-04: a second active main project is blocked; story saved to backlog.

    When an active non-hotfix Project already exists, creating another
    ``new_feature`` must raise ``ProjectConflictError``. The story must be
    saved to backlog so the user can retrieve it after the main project
    ends.
    """
    registry, run_store = _create_registry_and_store()
    project_store = ProjectStore(run_store=run_store)

    project_store.create_project(
        story="First feature",
        release_version="v0.12.0",
        definition_id="new_feature",
        definition_version="1",
    )

    with pytest.raises(ProjectConflictError):
        project_store.create_project(
            story="Second feature",
            release_version="v0.12.0",
            definition_id="new_feature",
            definition_version="1",
        )

    backlog = project_store.list_backlog()
    assert len(backlog) == 1
    assert backlog[0].story == "Second feature"

    active = project_store.list_active()
    assert len(active) == 1


# -- AC-FR1001-05 -------------------------------------------------------------


def test_ac_fr1001_05_hotfix_parallel_to_main_project():
    """AC-FR1001-05: a valid hotfix can coexist with an active main project.

    A ``bug_fix`` project is the only parallel exception. It must be
    allowed alongside an active ``new_feature`` project. The two projects'
    runs must not cross-write: each has its own run_id, workflow state and
    events.
    """
    registry, run_store = _create_registry_and_store()
    project_store = ProjectStore(run_store=run_store)

    main = project_store.create_project(
        story="Main feature",
        release_version="v0.12.0",
        definition_id="new_feature",
        definition_version="1",
    )

    hotfix = project_store.create_project(
        story="Fix login bug",
        release_version="v0.12.0",
        definition_id="bug_fix",
        definition_version="1",
    )

    assert hotfix.project_id != main.project_id
    assert hotfix.run_id != main.run_id

    active = project_store.list_active()
    assert len(active) == 2

    active_ids = {p.project_id for p in active}
    assert main.project_id in active_ids
    assert hotfix.project_id in active_ids

    # Events must not cross-write
    main_events = run_store.get_events(main.run_id)
    hotfix_events = run_store.get_events(hotfix.run_id)
    main_run_ids = {e.run_id for e in main_events}
    hotfix_run_ids = {e.run_id for e in hotfix_events}
    assert main_run_ids == {main.run_id}
    assert hotfix_run_ids == {hotfix.run_id}
