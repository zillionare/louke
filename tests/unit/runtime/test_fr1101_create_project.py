"""FR-1101: create new project and select workflow.

AC references:
- AC-FR1101-01: creation form provides story, release version, workflow
  inputs and shows catalog; bug_fix additionally requires GitHub Issue.
- AC-FR1101-02: catalog only directly offers new_feature and bug_fix;
  workflow id/version shown before and after confirmation; bug_fix is
  described as a hotfix.
- AC-FR1101-03: valid submission shows a preview (story excerpt, version,
  workflow id/version, readiness) before creating; after confirmation the
  project and run are atomically persisted with an immutable identity.
- AC-FR1101-04: missing fields, invalid release version, unknown workflow or
  conflict produce actionable errors with no half-created records.
- AC-FR1101-05: spec_change is not a direct option; backlog entries only
  prefill the form and still require confirmation.
- AC-FR1101-06: when an active main project exists, new_feature saves to
  backlog; after the main project ends, the backlog entry prefills the form.
- AC-FR1101-07: bug_fix without valid source contract is rejected; valid
  bug_fix can be created alongside an active main project without new
  requirements docs or gate.
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
    start = Step("start", "program", transitions=(Edge("e1", "start", "end", "done"),))
    end = Step("end", "program")
    return WorkflowDefinition("new_feature", "1", "start", (start, end))


def _bug_fix_definition() -> WorkflowDefinition:
    verify = Step(
        "source_contract_verify",
        "program",
        transitions=(Edge("e3", "source_contract_verify", "reproduce", "verified"),),
    )
    reproduce = Step("reproduce", "program")
    return WorkflowDefinition(
        "bug_fix", "1", "source_contract_verify", (verify, reproduce)
    )


def _create_fixtures() -> tuple[DefinitionRegistry, WorkflowRunStore, ProjectStore]:
    registry = DefinitionRegistry()
    registry.register(_new_feature_definition())
    registry.register(_bug_fix_definition())
    store = WorkflowRunStore(catalog=registry)
    project_store = ProjectStore(run_store=store)
    return registry, store, project_store


# -- AC-FR1101-02 -------------------------------------------------------------


def test_ac_fr1101_02_catalog_only_offers_new_feature_and_bug_fix():
    """AC-FR1101-02: first-version catalog only has new_feature and bug_fix.

    ``spec_change`` is not directly available. Each entry shows its
    definition id and version, and bug_fix is described as a hotfix.
    """
    _registry, _store, project_store = _create_fixtures()

    catalog = project_store.list_workflow_catalog()
    definition_ids = {entry.definition_id for entry in catalog}
    assert definition_ids == {"new_feature", "bug_fix"}
    assert "spec_change" not in definition_ids

    bug_fix_entry = next(e for e in catalog if e.definition_id == "bug_fix")
    assert bug_fix_entry.is_hotfix is True
    assert bug_fix_entry.version == "1"

    new_feature_entry = next(e for e in catalog if e.definition_id == "new_feature")
    assert new_feature_entry.is_hotfix is False


# -- AC-FR1101-03 -------------------------------------------------------------


def test_ac_fr1101_03_preview_then_confirm_creates_project_atomically():
    """AC-FR1101-03: preview shows summary without creating; confirm creates.

    The preview must show story excerpt, release version, workflow
    id/version. No project is created during preview. After confirmation,
    the project and run are atomically persisted with an immutable identity.
    """
    _registry, store, project_store = _create_fixtures()

    preview = project_store.preview_project(
        story="Build a new feature",
        release_version="v0.12.0",
        definition_id="new_feature",
        definition_version="1",
    )

    assert preview.story_excerpt
    assert preview.release_version == "v0.12.0"
    assert preview.workflow_definition_id == "new_feature"
    assert preview.workflow_version == "1"
    assert preview.project_id is None

    assert len(project_store.list_active()) == 0

    project = project_store.confirm_project(preview.preview_id)
    assert project.project_id.startswith("prj_")
    assert project.run_id.startswith("run_")
    assert project.release_version == "v0.12.0"

    assert len(project_store.list_active()) == 1
    run = store.get_run(project.run_id)
    assert run.run_id == project.run_id


# -- AC-FR1101-04 -------------------------------------------------------------


def test_ac_fr1101_04_missing_fields_rejected():
    """AC-FR1101-04: missing story is rejected with no half-created records."""
    _registry, _store, project_store = _create_fixtures()

    with pytest.raises(ValueError):
        project_store.preview_project(
            story="",
            release_version="v0.12.0",
            definition_id="new_feature",
            definition_version="1",
        )
    assert len(project_store.list_active()) == 0


def test_ac_fr1101_04_invalid_release_version_rejected():
    """AC-FR1101-04: invalid release version is rejected."""
    _registry, _store, project_store = _create_fixtures()

    with pytest.raises(ValueError):
        project_store.preview_project(
            story="Some story",
            release_version="not-a-version",
            definition_id="new_feature",
            definition_version="1",
        )
    assert len(project_store.list_active()) == 0


def test_ac_fr1101_04_unknown_workflow_rejected():
    """AC-FR1101-04: unknown workflow definition is rejected."""
    _registry, _store, project_store = _create_fixtures()

    with pytest.raises(KeyError):
        project_store.preview_project(
            story="Some story",
            release_version="v0.12.0",
            definition_id="spec_change",
            definition_version="1",
        )
    assert len(project_store.list_active()) == 0


# -- AC-FR1101-06 -------------------------------------------------------------


def test_ac_fr1101_06_active_main_blocks_second_new_feature_to_backlog():
    """AC-FR1101-06: second new_feature saves to backlog, not a second run.

    When an active main project exists, creating another new_feature must
    save the story to backlog. The backlog entry can later prefill the
    creation form, but confirmation still requires a fresh preview.
    """
    _registry, _store, project_store = _create_fixtures()

    project_store.create_project(
        story="First feature",
        release_version="v0.12.0",
        definition_id="new_feature",
        definition_version="1",
    )

    with pytest.raises(ProjectConflictError):
        project_store.preview_project(
            story="Second feature",
            release_version="v0.12.0",
            definition_id="new_feature",
            definition_version="1",
        )

    backlog = project_store.list_backlog()
    assert len(backlog) == 1
    assert backlog[0].story == "Second feature"

    assert len(project_store.list_active()) == 1


# -- AC-FR1101-07 -------------------------------------------------------------


def test_ac_fr1101_07_bug_fix_without_source_contract_rejected():
    """AC-FR1101-07: bug_fix without source contract is rejected.

    A bug_fix requires a source_contract referencing a GitHub Issue and
    an approved source spec/AC. Without it, creation is rejected.
    """
    _registry, _store, project_store = _create_fixtures()

    with pytest.raises(ValueError):
        project_store.preview_project(
            story="Fix a bug",
            release_version="v0.12.0",
            definition_id="bug_fix",
            definition_version="1",
            source_contract=None,
        )

    assert len(project_store.list_active()) == 0


def test_ac_fr1101_07_bug_fix_with_source_contract_created_alongside_main():
    """AC-FR1101-07: valid bug_fix created alongside active main project.

    A bug_fix with a valid source contract can be created alongside an
    active main project. It does not create new requirements docs or gate.
    """
    from louke.runtime.contract_gates import contract_digest
    from louke.runtime.gates import GATE_INHERITED, GateService
    from louke.runtime.orchestrator import WorkflowOrchestrator

    registry = DefinitionRegistry()
    registry.register(_new_feature_definition())
    registry.register(_bug_fix_definition())

    # Register a requirements_approval definition so we can create a source run
    req_def = WorkflowDefinition(
        "fr0801",
        "1",
        "requirements_approval",
        (
            Step(
                "requirements_approval",
                "human_gate",
                transitions=(
                    Edge("e_req", "requirements_approval", "design", "approved"),
                ),
            ),
            Step("design", "program"),
        ),
    )
    registry.register(req_def)

    store = WorkflowRunStore(catalog=registry)
    gate_service = GateService(store)
    orchestrator = WorkflowOrchestrator(store, gate_service=gate_service)
    project_store = ProjectStore(run_store=store)

    # Create and approve the source run
    source_run = store.create_run(registry.get("fr0801", "1"))
    source_digest = contract_digest(
        {
            "story": "sha256:source_story",
            "spec": "sha256:source_spec",
            "acceptance": "sha256:source_acceptance",
        }
    )
    orchestrator.ensure_requirements_gate(
        run_id=source_run.run_id,
        story_digest="sha256:source_story",
        spec_digest="sha256:source_spec",
        acceptance_digest="sha256:source_acceptance",
    )
    orchestrator.apply_gate_decision(
        run_id=source_run.run_id,
        gate_id=store.get_gate_for_run_step(
            source_run.run_id, "requirements_approval"
        ).gate_id,
        decision="approve",
        bound_digest=source_digest,
        expected_revision=source_run.revision,
        principal={"kind": "human", "id": "alice"},
    )
    source_gate = store.get_gate_for_run_step(
        source_run.run_id, "requirements_approval"
    )

    # Create the main project
    project_store.create_project(
        story="Main feature",
        release_version="v0.12.0",
        definition_id="new_feature",
        definition_version="1",
    )

    source_contract = {
        "github_issue": "owner/repo#42",
        "source_spec_digest": "sha256:source_spec",
        "source_acceptance_digest": "sha256:source_acceptance",
        "source_approval_gate_id": source_gate.gate_id,
        "source_approval_bound_digest": source_digest,
        "behavior_change": "implementation_deviation_only",
    }

    preview = project_store.preview_project(
        story="Fix a bug",
        release_version="v0.12.0",
        definition_id="bug_fix",
        definition_version="1",
        source_contract=source_contract,
    )
    project = project_store.confirm_project(preview.preview_id)

    active = project_store.list_active()
    assert len(active) == 2
    assert project.workflow_definition_id == "bug_fix"

    gate = store.get_gate_for_run_step(project.run_id, "requirements_approval")
    assert gate is not None
    assert gate.status == GATE_INHERITED
