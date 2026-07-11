"""Public adapter protocol + dataclasses for OpenCode instances and messages."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Literal, Optional, Protocol


InstanceStatus = Literal["starting", "running", "stopping", "stopped", "error"]
MessageRole = Literal["user", "assistant", "system"]
MessageKind = Literal["message", "command", "status", "error"]


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
            "id": self.id, "instance_id": self.instance_id,
            "role": self.role, "kind": self.kind, "content": self.content,
            "created_at": _iso(self.created_at),
        }


class OpenCodeAdapter(Protocol):
    def create(self, *, correlation_id: str) -> Instance: ...
    def list(self) -> list[Instance]: ...
    def stop(self, instance_id: str) -> Instance: ...
    def send_message(self, instance_id: str, content: str, *, correlation_id: str) -> tuple[Message, bool]: ...
    def list_messages(self, instance_id: str, *, after_message_id: Optional[str]) -> list[Message]: ...
