"""Context-bound Guide message history and last-seen announcements."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GuideMessage:
    """One Guide message with explicit current-context status."""

    workspace_id: str
    status_revision: str
    content: str
    historical: bool


class GuideMessageLedger:
    """Small deterministic ledger for de-duplicated Guide announcements."""

    def __init__(self) -> None:
        self._seen: set[tuple[str, str]] = set()
        self._messages: list[GuideMessage] = []

    def should_announce(self, workspace_id: str, status_revision: str) -> bool:
        """Return whether this workspace/status pair needs a first announcement."""
        return (workspace_id, status_revision) not in self._seen

    def mark_seen(self, workspace_id: str, status_revision: str) -> None:
        """Persist that one canonical status revision was announced."""
        self._seen.add((workspace_id, status_revision))

    def append(
        self, workspace_id: str, status_revision: str, content: str
    ) -> GuideMessage:
        """Append a message and return its current-context projection."""
        message = GuideMessage(workspace_id, status_revision, content, historical=False)
        self._messages.append(message)
        return message

    def messages(self, workspace_id: str) -> tuple[GuideMessage, ...]:
        """Return all messages, marking other workspaces historical."""
        return tuple(
            GuideMessage(
                item.workspace_id,
                item.status_revision,
                item.content,
                item.workspace_id != workspace_id,
            )
            for item in self._messages
        )
