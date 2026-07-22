"""Public adapter protocol + dataclasses for OpenCode instances and messages."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import List, Literal, Optional, Protocol


InstanceStatus = Literal["starting", "running", "stopping", "stopped", "error"]
MessageRole = Literal["user", "assistant", "system"]
MessageKind = Literal["message", "command", "status", "error"]
StreamEventType = Literal["delta", "completed", "error"]
SessionReconcileStatus = Literal["running", "completed", "not_found", "ambiguous"]


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def _iso(t: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


@dataclass
class Instance:
    id: str
    status: InstanceStatus = "starting"
    created_at: float = field(default_factory=lambda: time.time())
    error: Optional[str] = None

    def to_dict(self):
        d = {"id": self.id, "status": self.status, "created_at": _iso(self.created_at)}
        if self.error:
            d["error"] = self.error
        return d


@dataclass
class Message:
    id: str
    instance_id: str
    role: MessageRole
    kind: MessageKind
    content: str
    created_at: float = field(default_factory=lambda: time.time())

    def to_dict(self):
        return {
            "id": self.id,
            "instance_id": self.instance_id,
            "role": self.role,
            "kind": self.kind,
            "content": self.content,
            "created_at": _iso(self.created_at),
        }


@dataclass
class StreamEvent:
    """Normalized assistant-stream event exposed by the OpenCode adapter."""

    event_id: str
    type: StreamEventType
    message_id: str
    delta: Optional[str] = None
    content: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "event_id": self.event_id,
            "type": self.type,
            "message_id": self.message_id,
        }
        if self.delta is not None:
            result["delta"] = self.delta
        if self.content is not None:
            result["content"] = self.content
        if self.error is not None:
            result["error"] = self.error
        return result


@dataclass
class ProviderResult:
    """One normalized, non-secret result emitted by an OpenCode session."""

    result_id: str
    payload: Optional[dict[str, object]] = None


@dataclass
class SessionReconcile:
    """Outcome of querying an existing OpenCode session and turn."""

    status: SessionReconcileStatus
    results: List[ProviderResult] = field(default_factory=list)
    error: Optional[str] = None


class OpenCodeAdapter(Protocol):
    def create(self, *, correlation_id: str) -> Instance: ...
    def list(self) -> List[Instance]: ...
    def stop(self, instance_id: str) -> Instance: ...
    def send_message(
        self, instance_id: str, content: str, *, correlation_id: str
    ) -> tuple[Message, bool]: ...
    def list_messages(
        self, instance_id: str, *, after_message_id: Optional[str]
    ) -> List[Message]: ...

    def stream_events(
        self, instance_id: str, last_event_id: Optional[str] = None
    ) -> object: ...

    def reconcile_session(
        self, instance_id: str, *, after_result_id: Optional[str] = None
    ) -> SessionReconcile:
        """Query the existing session without dispatching another turn."""
