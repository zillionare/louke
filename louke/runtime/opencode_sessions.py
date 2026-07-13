"""OpenCode session lifecycle management (FR-1401).

This module manages the lifecycle of OpenCode server, workspace and session
resources. It supports create, detach, attach, send-message, stop-generation,
end-session, release-workspace and stop-server operations, and distinguishes
between real and contract adapters. After a restart, a recovery scan
re-associates live resources and marks lost ones as ``needs_attention``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol


class SessionNotFoundError(KeyError):
    """Raised when a requested session does not exist."""


class SessionUnavailableError(Exception):
    """Raised when an attach or send is attempted on an unavailable session."""


class SessionAlreadyEndedError(Exception):
    """Raised when an operation is attempted on an ended session."""


class CrossRunAttachError(SessionUnavailableError):
    """Raised when a different run identity tries to attach to a session."""


class OpenCodeLifecycleAdapter(Protocol):
    """Boundary for OpenCode server/workspace/session operations."""

    adapter_kind: str

    def create_server(self, run_id: str) -> str: ...
    def create_workspace(self, server_id: str) -> str: ...
    def create_session(self, run_id: str, server_id: str, workspace_id: str) -> str: ...
    def send_message(self, session_id: str, content: str) -> str: ...
    def stop_generation(self, session_id: str) -> None: ...
    def end_session(self, session_id: str) -> None: ...
    def release_workspace(self, workspace_id: str) -> None: ...
    def stop_server(self, server_id: str) -> None: ...
    def is_server_alive(self, server_id: str) -> bool: ...
    def list_sessions(self) -> list[dict[str, Any]]: ...


@dataclass(frozen=True, slots=True)
class ManagedSession:
    """A session managed by the lifecycle manager.

    Attributes:
        session_id: Opaque session identifier.
        run_id: The run the session belongs to.
        server_id: The server backing this session.
        workspace_id: The workspace backing this session.
        status: Session status (attached, detached, ended, needs_attention).
        adapter_kind: ``contract`` or ``real``.
        created_at: ISO 8601 UTC timestamp.
    """

    session_id: str
    run_id: str
    server_id: str
    workspace_id: str
    status: str
    adapter_kind: str
    created_at: str


class SessionLifecycleManager:
    """Manage OpenCode session lifecycle with detach/attach and recovery.

    Args:
        adapter: The OpenCode lifecycle adapter (contract or real).
    """

    def __init__(self, adapter: OpenCodeLifecycleAdapter) -> None:
        self._adapter = adapter
        self._sessions: dict[str, ManagedSession] = {}
        self._messages: dict[str, list[dict[str, Any]]] = {}

    def create_session(self, run_id: str) -> ManagedSession:
        """Create a new managed session for ``run_id``.

        Args:
            run_id: The run to create the session for.

        Returns:
            The created :class:`ManagedSession`.
        """
        server_id = self._adapter.create_server(run_id)
        workspace_id = self._adapter.create_workspace(server_id)
        session_id = self._adapter.create_session(run_id, server_id, workspace_id)
        session = ManagedSession(
            session_id=session_id,
            run_id=run_id,
            server_id=server_id,
            workspace_id=workspace_id,
            status="attached",
            adapter_kind=self._adapter.adapter_kind,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._sessions[session_id] = session
        self._messages[session_id] = []
        return session

    def get_session(self, session_id: str) -> ManagedSession:
        """Return the managed session for ``session_id``.

        Args:
            session_id: The session identifier.

        Returns:
            The :class:`ManagedSession`.

        Raises:
            SessionNotFoundError: If the session does not exist.
        """
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError(f"session {session_id!r} not found")
        return session

    def detach(self, session_id: str) -> ManagedSession:
        """Detach from ``session_id``, releasing the client connection.

        The server and session continue to exist.

        Args:
            session_id: The session to detach.

        Returns:
            The updated session with status ``detached``.
        """
        session = self.get_session(session_id)
        updated = _with_status(session, "detached")
        self._sessions[session_id] = updated
        return updated

    def attach(self, session_id: str, run_id: str) -> ManagedSession:
        """Re-attach to ``session_id`` from the same authorized ``run_id``.

        Args:
            session_id: The session to attach.
            run_id: The run identity requesting the attach.

        Returns:
            The updated session with status ``attached``.

        Raises:
            CrossRunAttachError: If ``run_id`` does not match the session's run.
            SessionUnavailableError: If the session has ended or its server is gone.
        """
        session = self.get_session(session_id)
        if session.run_id != run_id:
            raise CrossRunAttachError(
                f"session {session_id!r} belongs to run {session.run_id!r}, "
                f"not {run_id!r}"
            )
        if session.status == "ended":
            raise SessionUnavailableError(
                f"session {session_id!r} has ended and cannot be re-attached"
            )
        if not self._adapter.is_server_alive(session.server_id):
            raise SessionUnavailableError(f"session {session_id!r} server is not alive")
        updated = _with_status(session, "attached")
        self._sessions[session_id] = updated
        return updated

    def send_message(self, session_id: str, content: str) -> str:
        """Send a message to ``session_id``.

        Args:
            session_id: The session to send to.
            content: The message content.

        Returns:
            The message id.

        Raises:
            SessionAlreadyEndedError: If the session has ended.
        """
        session = self.get_session(session_id)
        if session.status == "ended":
            raise SessionAlreadyEndedError(
                f"session {session_id!r} has ended; cannot send messages"
            )
        msg_id = self._adapter.send_message(session_id, content)
        self._messages.setdefault(session_id, []).append(
            {"id": msg_id, "content": content}
        )
        return msg_id

    def list_messages(self, session_id: str) -> tuple[dict[str, Any], ...]:
        """Return all messages for ``session_id``.

        Args:
            session_id: The session to list messages for.

        Returns:
            A tuple of message dicts.
        """
        return tuple(self._messages.get(session_id, ()))

    def stop_generation(self, session_id: str) -> None:
        """Stop the current generation for ``session_id``.

        Args:
            session_id: The session to stop generation on.
        """
        self.get_session(session_id)
        self._adapter.stop_generation(session_id)

    def end_session(self, session_id: str) -> ManagedSession:
        """End ``session_id`` permanently.

        Args:
            session_id: The session to end.

        Returns:
            The updated session with status ``ended``.
        """
        self.get_session(session_id)
        self._adapter.end_session(session_id)
        updated = _with_status(self._sessions[session_id], "ended")
        self._sessions[session_id] = updated
        return updated

    def release_workspace(self, workspace_id: str) -> None:
        """Release the workspace ``workspace_id``.

        Args:
            workspace_id: The workspace to release.
        """
        self._adapter.release_workspace(workspace_id)

    def stop_server(self, server_id: str) -> None:
        """Stop the server ``server_id``.

        Args:
            server_id: The server to stop.
        """
        self._adapter.stop_server(server_id)

    def recover_sessions(self) -> None:
        """Scan all sessions reported by the adapter after a restart.

        Sessions discovered from the adapter are imported into the manager.
        Sessions whose server is still alive are re-associated with their
        last known status. Sessions whose server has been lost are marked
        ``needs_attention``. Ended sessions are preserved as-is.
        """
        for raw in self._adapter.list_sessions():
            session_id = raw["id"]
            run_id = raw["run_id"]
            server_id = raw["server_id"]
            workspace_id = raw["workspace_id"]
            old_status = raw.get("status", "detached")

            if old_status == "ended":
                status = "ended"
            elif not self._adapter.is_server_alive(server_id):
                status = "needs_attention"
            else:
                status = old_status

            session = ManagedSession(
                session_id=session_id,
                run_id=run_id,
                server_id=server_id,
                workspace_id=workspace_id,
                status=status,
                adapter_kind=self._adapter.adapter_kind,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            self._sessions[session_id] = session
            self._messages.setdefault(session_id, [])


def _with_status(session: ManagedSession, status: str) -> ManagedSession:
    """Return a new session with the given status."""
    return ManagedSession(
        session_id=session.session_id,
        run_id=session.run_id,
        server_id=session.server_id,
        workspace_id=session.workspace_id,
        status=status,
        adapter_kind=session.adapter_kind,
        created_at=session.created_at,
    )
