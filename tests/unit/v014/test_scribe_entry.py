"""Unit contracts for persistent M-STORY Scribe task and Chat dispatch."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from louke.opencode.adapter import Instance, Message
from louke.runtime.catalog import DefinitionRegistry, Edge, Step, WorkflowDefinition
from louke.runtime.store import WorkflowRunStore
from louke.v014.fr0500_story_init import (
    StoryInitResult,
    StoryNavigation,
    StoryRevisionEvidence,
)
from louke.v014.scribe_entry import ScribeEntryService, ScribeTaskError
from louke.v014.story_entry import StoryArtifactStore


def _store(db_path: str | None = None) -> WorkflowRunStore:
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


def _artifact(store: WorkflowRunStore, run_id: str):
    result = StoryInitResult(
        story_md_bytes=b"# Story\n\n> Ship the reflow\n",
        evidence=StoryRevisionEvidence(
            input_digest="sha256:input",
            file_digest="sha256:story",
            actor="human:alice",
            run_id=run_id,
            commit_sha="sha-story",
        ),
        navigation=StoryNavigation(
            run_id=run_id,
            spec_id="spec-1",
            phase="M-STORY",
            document="story",
            revision_digest="sha256:story",
            commit_sha="sha-story",
        ),
    )
    return StoryArtifactStore(store).save(run_id, "spec-1", result, "story-init-1")


def _story_run(store: WorkflowRunStore):
    """Create the fixture run and move it to the persisted M-STORY position."""
    run = store.create_run(store._catalog.get("new_feature", "0.14.0"))
    return store.update_run(run.with_step("M-STORY", "waiting_for_human"), 0)


@dataclass
class FakeOpenCode:
    fail_create: bool = False
    fail_send: bool = False
    create_calls: int = 0
    send_calls: int = 0
    messages: list[Message] = field(default_factory=list)

    def create(self, *, correlation_id: str) -> Instance:
        self.create_calls += 1
        if self.fail_create:
            raise RuntimeError("OpenCode unavailable")
        return Instance(id="session-1", status="running")

    def send_message(
        self, instance_id: str, content: str, *, correlation_id: str
    ) -> tuple[Message, bool]:
        self.send_calls += 1
        if self.fail_send:
            raise RuntimeError("OpenCode prompt failed")
        message = Message(
            id=f"provider-{self.send_calls}",
            instance_id=instance_id,
            role="user",
            kind="message",
            content=content,
        )
        self.messages.append(message)
        return message, True

    def list_messages(self, instance_id: str, *, after_message_id: str | None):
        return list(self.messages)


def test_ensure_task_persists_manifest_and_dispatches_real_scribe_session() -> None:
    """FR-0700: M-STORY creates one manifest-bound Scribe session."""
    store = _store()
    run = _story_run(store)
    artifact = _artifact(store, run.run_id)
    adapter = FakeOpenCode()

    task = ScribeEntryService(store, adapter).ensure_task(
        run_id=run.run_id,
        artifact=artifact,
        human_request="Ship the reflow",
        foundation_manifest_identity="foundation:one",
        workspace="/workspace",
    )

    assert task["phase"] == "M-STORY"
    assert task["role"] == "Scribe"
    assert task["write_scope"] == ["story.md"]
    assert task["status"] == "running"
    assert task["connection"] == "connected"
    assert task["session_id"] == "session-1"
    assert task["manifest"]["run_id"] == run.run_id
    assert task["manifest"]["artifact"]["digest"] == artifact.digest
    assert adapter.create_calls == 1
    assert adapter.send_calls == 1


def test_unavailable_opencode_is_blocked_and_does_not_fake_a_session() -> None:
    """FR-0700: transport failure is visible and retryable, never PASS."""
    store = _store()
    run = _story_run(store)
    artifact = _artifact(store, run.run_id)

    task = ScribeEntryService(store, FakeOpenCode(fail_create=True)).ensure_task(
        run_id=run.run_id,
        artifact=artifact,
        human_request="Ship the reflow",
        foundation_manifest_identity="foundation:one",
        workspace="/workspace",
    )

    assert task["status"] == "blocked"
    assert task["connection"] == "blocked"
    assert task["session_id"] is None
    assert task["allowed_actions"] == ["retry", "reconcile"]


def test_human_reply_is_persisted_once_and_replayed_idempotently() -> None:
    """IF-API-08: persisted message identity prevents duplicate dispatch."""
    store = _store()
    run = _story_run(store)
    artifact = _artifact(store, run.run_id)
    adapter = FakeOpenCode()
    service = ScribeEntryService(store, adapter)
    task = service.ensure_task(
        run_id=run.run_id,
        artifact=artifact,
        human_request="Ship the reflow",
        foundation_manifest_identity="foundation:one",
        workspace="/workspace",
    )

    first = service.reply(
        run_id=run.run_id,
        task_id=task["task_id"],
        client_message_id="client-1",
        correlation_id="corr-1",
        body="Please interview me first.",
        expected_attempt_id=task["active_attempt"]["attempt_id"],
        expected_artifact_revision=artifact.revision,
    )
    replay = service.reply(
        run_id=run.run_id,
        task_id=task["task_id"],
        client_message_id="client-1",
        correlation_id="corr-1",
        body="Please interview me first.",
        expected_attempt_id=task["active_attempt"]["attempt_id"],
        expected_artifact_revision=artifact.revision,
    )

    assert first["status"] == "dispatched"
    assert replay == first
    assert adapter.send_calls == 2


def test_reply_rejects_wrong_task_attempt_or_stale_artifact() -> None:
    """IF-API-08: cross-task, wrong-attempt and stale Story replies fail closed."""
    store = _store()
    run = _story_run(store)
    artifact = _artifact(store, run.run_id)
    service = ScribeEntryService(store, FakeOpenCode())
    task = service.ensure_task(
        run_id=run.run_id,
        artifact=artifact,
        human_request="Ship the reflow",
        foundation_manifest_identity="foundation:one",
        workspace="/workspace",
    )

    with pytest.raises(ScribeTaskError, match="TASK_ATTEMPT_CONFLICT"):
        service.reply(
            run_id=run.run_id,
            task_id=task["task_id"],
            client_message_id="client-2",
            correlation_id="corr-2",
            body="reply",
            expected_attempt_id="wrong-attempt",
            expected_artifact_revision=artifact.revision,
        )
    with pytest.raises(ScribeTaskError, match="DOCUMENT_WRITE_CONFLICT"):
        service.reply(
            run_id=run.run_id,
            task_id=task["task_id"],
            client_message_id="client-3",
            correlation_id="corr-3",
            body="reply",
            expected_attempt_id=task["active_attempt"]["attempt_id"],
            expected_artifact_revision=artifact.revision + 1,
        )
