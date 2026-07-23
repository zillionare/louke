"""InMemoryOpenCodeAdapter - for unit/integration tests (no real OpenCode)."""

from __future__ import annotations

import threading
from typing import List, Optional

from .adapter import Instance, Message, SessionReconcile, StreamEvent, new_id


class InMemoryOpenCodeAdapter:
    def __init__(self):
        self._lock = threading.RLock()
        self._instances: dict[str, Instance] = {}
        self._messages: dict[str, list[Message]] = {}

    def create(self, *, correlation_id: str, agent: Optional[str] = None) -> Instance:
        del agent
        with self._lock:
            inst = Instance(id=new_id(), status="running")
            self._instances[inst.id] = inst
            self._messages.setdefault(inst.id, [])
            return inst

    def list(self) -> List[Instance]:
        with self._lock:
            return list(self._instances.values())

    def stop(self, instance_id: str) -> Instance:
        with self._lock:
            inst = self._instances.get(instance_id)
            if inst is None:
                return Instance(id=instance_id, status="stopped")
            inst.status = "stopped"
            return inst

    def send_message(
        self, instance_id: str, content: str, *, correlation_id: str
    ) -> tuple[Message, bool]:
        with self._lock:
            inst = self._instances.get(instance_id)
            if inst is None:
                raise KeyError(instance_id)
            if inst.status != "running":
                raise RuntimeError(
                    f"instance {instance_id} not running (status={inst.status})"
                )
            user_msg = Message(
                id=new_id(),
                instance_id=inst.id,
                role="user",
                kind="message",
                content=content,
            )
            self._messages[inst.id].append(user_msg)
            echo = Message(
                id=new_id(),
                instance_id=inst.id,
                role="assistant",
                kind="message",
                content=f"echo: {content}",
            )
            self._messages[inst.id].append(echo)
            return user_msg, True

    def list_messages(
        self, instance_id: str, *, after_message_id: Optional[str]
    ) -> List[Message]:
        with self._lock:
            msgs = list(self._messages.get(instance_id, []))
        if not after_message_id:
            return msgs
        for i, m in enumerate(msgs):
            if m.id == after_message_id:
                return msgs[i + 1 :]
        return msgs

    def stream_events(self, instance_id: str, last_event_id: Optional[str] = None):
        """Emit a deterministic stand-in stream for the public SSE contract."""
        messages = self.list_messages(instance_id, after_message_id=None)
        assistant = next((m for m in reversed(messages) if m.role == "assistant"), None)
        if assistant is None:
            return
        if last_event_id:
            # The in-memory stream is intentionally short-lived; a caller that
            # reconnects receives the final completion as a safe resync.
            yield StreamEvent(
                event_id=new_id(),
                type="completed",
                message_id=assistant.id,
                content=assistant.content,
            )
            return
        yield StreamEvent(
            event_id=new_id(),
            type="delta",
            message_id=assistant.id,
            delta=assistant.content,
        )
        yield StreamEvent(
            event_id=new_id(),
            type="completed",
            message_id=assistant.id,
            content=assistant.content,
        )

    def reconcile_session(
        self, instance_id: str, *, after_result_id: str | None = None
    ) -> SessionReconcile:
        """Report that an in-memory session has no controlled result yet."""
        with self._lock:
            instance = self._instances.get(instance_id)
        if instance is None:
            return SessionReconcile(status="not_found")
        if instance.status != "running":
            return SessionReconcile(status="ambiguous", error="session is not running")
        return SessionReconcile(status="running")


_singleton: Optional[InMemoryOpenCodeAdapter] = None


def get_default_adapter() -> InMemoryOpenCodeAdapter:
    global _singleton
    if _singleton is None:
        _singleton = InMemoryOpenCodeAdapter()
    return _singleton
