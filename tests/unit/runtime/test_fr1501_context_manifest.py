"""FR-1501: per-step customizable and traceable agent context.

AC references:
- AC-FR1501-01: a context manifest contains run/step/attempt, agent,
  base commit/worktree, input artifacts/digests, allowed tools, allowed
  write scopes, output schema and forbidden side effects.
- AC-FR1501-02: contexts for different runs/steps are independent and do
  not inherit Maestro's implicit workflow state.
- AC-FR1501-03: Devon's manifest lists assigned issues, acceptance criteria,
  design docs, scope, authoritative tests and completion outputs.
- AC-FR1501-04: manifest and agent results are persisted and can be read
  after session loss or restart.
- AC-FR1501-05: a result whose manifest/base commit/contract digest does
  not match the current task is rejected for state transition.
"""

from __future__ import annotations

import pytest

from louke.runtime.context_manifest import (
    ContextManifestBuilder,
    ManifestDigestMismatchError,
    ManifestResultValidator,
)
from louke.runtime.store import WorkflowRunStore


# -- Fixtures -----------------------------------------------------------------

def _create_manifest_builder() -> tuple[WorkflowRunStore, ContextManifestBuilder]:
    """Create a run store and manifest builder."""
    store = WorkflowRunStore()
    builder = ContextManifestBuilder(store=store)
    return store, builder


# -- AC-FR1501-01 -------------------------------------------------------------


def test_ac_fr1501_01_manifest_contains_required_fields():
    """AC-FR1501-01: context manifest contains all required fields.

    The manifest must include run/step/attempt, agent, base commit/worktree,
    input artifact refs/digests, allowed tools, allowed write scopes,
    output schema and forbidden side effects.
    """
    _store, builder = _create_manifest_builder()

    manifest = builder.build(
        run_id="run_001",
        step_id="implementation",
        attempt_id="att_001",
        agent_role="devon",
        base_commit="sha256:base",
        workspace="/workspace",
        artifact_refs=[{"id": "art_1", "digest": "sha256:abc", "access": "read"}],
        allowed_tools=["git.read", "edit"],
        write_scopes=["src/"],
        output_schema="semantic-result/v1",
        forbidden_side_effects=["commit", "push"],
    )

    assert manifest.run_id == "run_001"
    assert manifest.step_id == "implementation"
    assert manifest.attempt_id == "att_001"
    assert manifest.agent_role == "devon"
    assert manifest.base_commit == "sha256:base"
    assert manifest.workspace == "/workspace"
    assert manifest.artifact_refs == (
        {"id": "art_1", "digest": "sha256:abc", "access": "read"},
    )
    assert manifest.allowed_tools == ("git.read", "edit")
    assert manifest.write_scopes == ("src/",)
    assert manifest.output_schema == "semantic-result/v1"
    assert manifest.forbidden_side_effects == ("commit", "push")


# -- AC-FR1501-02 -------------------------------------------------------------


def test_ac_fr1501_02_manifests_for_different_runs_are_independent():
    """AC-FR1501-02: manifests for different runs/steps are independent.

    Each manifest contains only its own task data; they do not share
    Maestro-level implicit state.
    """
    _store, builder = _create_manifest_builder()

    manifest_a = builder.build(
        run_id="run_001",
        step_id="step_a",
        attempt_id="att_a",
        agent_role="devon",
        base_commit="sha256:base_a",
        workspace="/workspace_a",
    )
    manifest_b = builder.build(
        run_id="run_002",
        step_id="step_b",
        attempt_id="att_b",
        agent_role="devon",
        base_commit="sha256:base_b",
        workspace="/workspace_b",
    )

    assert manifest_a.run_id != manifest_b.run_id
    assert manifest_a.step_id != manifest_b.step_id
    assert manifest_a.base_commit != manifest_b.base_commit
    assert manifest_a.workspace != manifest_b.workspace


# -- AC-FR1501-03 -------------------------------------------------------------


def test_ac_fr1501_03_devon_manifest_lists_assigned_issues():
    """AC-FR1501-03: Devon manifest lists issues, ACs, docs, scope, tests.

    When Devon is assigned a batch of GitHub issues, the manifest records
    the issues, acceptance criteria, related design docs, modification
    scope, authoritative tests and completion output. Unlisted issues do
    not enter the task scope.
    """
    _store, builder = _create_manifest_builder()

    manifest = builder.build(
        run_id="run_001",
        step_id="implementation",
        attempt_id="att_001",
        agent_role="devon",
        base_commit="sha256:base",
        workspace="/workspace",
        assignments={
            "fr": ["FR-2201"],
            "ac": ["AC-FR2201-01"],
            "issues": ["#123"],
        },
        design_doc_refs=[
            {"id": "architecture", "digest": "sha256:arch_v1"},
            {"id": "interfaces", "digest": "sha256:ifc_v1"},
        ],
        modification_scope="src/louke/runtime/",
        authoritative_tests=["tests/unit/runtime/test_context_manifest.py"],
        completion_outputs=["code changes", "tests passing"],
    )

    assert manifest.assignments["issues"] == ("#123",)
    assert manifest.assignments["ac"] == ("AC-FR2201-01",)
    assert len(manifest.design_doc_refs) == 2
    assert manifest.modification_scope == "src/louke/runtime/"
    assert manifest.authoritative_tests == (
        "tests/unit/runtime/test_context_manifest.py",
    )
    assert manifest.completion_outputs == ("code changes", "tests passing")


# -- AC-FR1501-04 -------------------------------------------------------------


def test_ac_fr1501_04_manifest_and_results_persisted():
    """AC-FR1501-04: manifest and agent results are persisted.

    After creating a manifest and recording an agent result, both can be
    retrieved later (e.g. after session loss or restart).
    """
    store, builder = _create_manifest_builder()

    manifest = builder.build(
        run_id="run_001",
        step_id="implementation",
        attempt_id="att_001",
        agent_role="devon",
        base_commit="sha256:base",
        workspace="/workspace",
    )

    builder.record_agent_result(
        run_id="run_001",
        attempt_id="att_001",
        manifest_digest=manifest.digest(),
        result={"files_changed": ["src/foo.py"]},
    )

    retrieved_manifest = builder.get_manifest(run_id="run_001", attempt_id="att_001")
    assert retrieved_manifest.run_id == "run_001"
    assert retrieved_manifest.digest() == manifest.digest()

    result = builder.get_agent_result(run_id="run_001", attempt_id="att_001")
    assert result["files_changed"] == ["src/foo.py"]


# -- AC-FR1501-05 -------------------------------------------------------------


def test_ac_fr1501_05_mismatched_digest_rejected():
    """AC-FR1501-05: mismatched manifest/base commit/contract digest rejected.

    If an agent result references a manifest digest or base commit that
    does not match the current task, the result is rejected for state
    transition.
    """
    _store, builder = _create_manifest_builder()

    manifest = builder.build(
        run_id="run_001",
        step_id="implementation",
        attempt_id="att_001",
        agent_role="devon",
        base_commit="sha256:base",
        workspace="/workspace",
    )

    validator = ManifestResultValidator(
        expected_manifest_digest=manifest.digest(),
        expected_base_commit="sha256:base",
        expected_contract_digest="sha256:contract",
    )

    # Valid result passes
    validator.validate(
        manifest_digest=manifest.digest(),
        base_commit="sha256:base",
        contract_digest="sha256:contract",
    )

    # Mismatched manifest digest fails
    with pytest.raises(ManifestDigestMismatchError):
        validator.validate(
            manifest_digest="sha256:wrong",
            base_commit="sha256:base",
            contract_digest="sha256:contract",
        )

    # Mismatched base commit fails
    with pytest.raises(ManifestDigestMismatchError):
        validator.validate(
            manifest_digest=manifest.digest(),
            base_commit="sha256:other",
            contract_digest="sha256:contract",
        )
