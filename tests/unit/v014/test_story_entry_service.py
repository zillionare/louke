"""Unit contracts for the Runtime-owned initial Story entry."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from louke.runtime.catalog import DefinitionRegistry, Edge, Step, WorkflowDefinition
from louke.runtime.store import WorkflowRunStore
from louke.runtime.story_init import (
    StoryInitConflict,
    StoryInitResult,
    StoryNavigation,
    StoryRevisionEvidence,
)
from louke.runtime.story_entry import StoryEntryService


def _run_store(db_path: str | None = None) -> WorkflowRunStore:
    catalog = DefinitionRegistry()
    catalog.register(
        WorkflowDefinition(
            definition_id="new_feature",
            version="0.14.0",
            start_step="M-START",
            steps=(
                Step(
                    step_id="M-START",
                    kind="program",
                    handler="v014.m_start",
                    transitions=(Edge("start-story", "M-START", "M-STORY", "done"),),
                ),
                Step(step_id="M-STORY", kind="program", handler="v014.m_story"),
            ),
        )
    )
    return WorkflowRunStore(db_path=db_path, catalog=catalog)


def _result(run_id: str, story: str) -> StoryInitResult:
    body = f"# Story\n\n> {story}\n"
    return StoryInitResult(
        story_md_bytes=body.encode(),
        evidence=StoryRevisionEvidence(
            input_digest="sha256:input",
            file_digest="sha256:file",
            actor="human:alice",
            run_id=run_id,
            commit_sha="sha-story",
        ),
        navigation=StoryNavigation(
            run_id=run_id,
            spec_id="spec-1",
            phase="M-STORY",
            document="story",
            revision_digest="sha256:file",
            commit_sha="sha-story",
        ),
    )


@dataclass
class FakeStoryWriter:
    calls: int = 0
    conflict: StoryInitConflict | None = None

    def write_story(
        self,
        *,
        workspace: str,
        spec_id: str,
        human_story: str,
        actor: str,
        run_id: str,
    ) -> StoryInitResult:
        self.calls += 1
        if self.conflict is not None:
            raise self.conflict
        return _result(run_id, human_story)


@dataclass
class FakeScribeEntry:
    calls: list[dict[str, object]]

    def ensure_task(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(kwargs)
        return {"task_id": "task-1", "state": "blocked"}


def test_story_entry_persists_artifact_and_advances_runtime_to_m_story() -> None:
    """Initial Story creation commits one Runtime transition and one artifact."""
    store = _run_store()
    writer = FakeStoryWriter()
    run = store.create_run(store._catalog.get("new_feature", "0.14.0"))

    outcome = StoryEntryService(store, writer).initialize(
        run_id=run.run_id,
        workspace="/workspace",
        spec_id="spec-1",
        human_story="Ship the reflow",
        actor="human:alice",
        idempotency_key="story-init-1",
    )

    assert outcome.run.current_step == "M-STORY"
    assert outcome.artifact.revision == 1
    assert outcome.artifact.commit_sha == "sha-story"
    assert store.get_run(run.run_id).current_step == "M-STORY"
    assert writer.calls == 1


def test_story_entry_replay_reuses_revision_after_service_restart(tmp_path) -> None:
    """The same initialization key reuses the persisted attempt and artifact."""
    db_path = str(tmp_path / "runtime.sqlite3")
    first_store = _run_store(db_path)
    run = first_store.create_run(first_store._catalog.get("new_feature", "0.14.0"))
    first_writer = FakeStoryWriter()
    first = StoryEntryService(first_store, first_writer).initialize(
        run_id=run.run_id,
        workspace="/workspace",
        spec_id="spec-1",
        human_story="Ship the reflow",
        actor="human:alice",
        idempotency_key="story-init-1",
    )
    first_store.close()

    second_store = _run_store(db_path)
    second_writer = FakeStoryWriter()
    second = StoryEntryService(second_store, second_writer).initialize(
        run_id=run.run_id,
        workspace="/workspace",
        spec_id="spec-1",
        human_story="Ship the reflow",
        actor="human:alice",
        idempotency_key="story-init-1",
    )

    assert second == first
    assert second_writer.calls == 0


def test_story_entry_ensures_scribe_task_after_story_is_persisted() -> None:
    """Story persistence binds the first Scribe task to its artifact identity."""
    store = _run_store()
    writer = FakeStoryWriter()
    scribe = FakeScribeEntry(calls=[])
    run = store.create_run(store._catalog.get("new_feature", "0.14.0"))

    outcome = StoryEntryService(store, writer, scribe_entry=scribe).initialize(
        run_id=run.run_id,
        workspace="/workspace",
        spec_id="spec-1",
        human_story="Ship the reflow",
        actor="human:alice",
        idempotency_key="story-init-1",
        foundation_manifest_identity="foundation:abc",
    )

    assert outcome.task == {"task_id": "task-1", "state": "blocked"}
    assert scribe.calls == [
        {
            "run_id": run.run_id,
            "artifact": outcome.artifact,
            "human_request": "Ship the reflow",
            "foundation_manifest_identity": "foundation:abc",
            "workspace": "/workspace",
        }
    ]


def test_story_entry_conflict_keeps_runtime_at_m_start() -> None:
    """A Story byte conflict is surfaced without advancing or persisting a revision."""
    store = _run_store()
    conflict = StoryInitConflict(
        existing_bytes=b"human edit",
        expected_file_digest="sha256:expected",
    )
    writer = FakeStoryWriter(conflict=conflict)
    run = store.create_run(store._catalog.get("new_feature", "0.14.0"))

    with pytest.raises(StoryInitConflict):
        StoryEntryService(store, writer).initialize(
            run_id=run.run_id,
            workspace="/workspace",
            spec_id="spec-1",
            human_story="Ship the reflow",
            actor="human:alice",
            idempotency_key="story-init-1",
        )

    assert store.get_run(run.run_id).current_step == "M-START"
    assert StoryEntryService(store, writer).artifact(run.run_id) is None
