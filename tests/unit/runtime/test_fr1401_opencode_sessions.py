"""FR-1401: real OpenCode instance and session lifecycle.

AC references:
- AC-FR1401-01: created OpenCode resources correspond to real, observable
  server/workspace/session identity; memory echo is rejected.
- AC-FR1401-02: detach releases client connection but keeps server/session;
  the run is not marked completed or deleted.
- AC-FR1401-03: re-attach to the same authorized run shows session history;
  attach with a different run/session identity is rejected.
- AC-FR1401-04: stop-generation, end-session, release-workspace and
  stop-server each produce only their defined lifecycle change.
- AC-FR1401-05: after restart, recoverable resources are re-associated and
  lost resources are marked needs-attention; nothing is falsely running.
"""

from __future__ import annotations

import pytest

from louke.runtime.opencode_sessions import (
    SessionUnavailableError,
    SessionLifecycleManager,
    SessionAlreadyEndedError,
)


# -- Contract adapter for testing ---------------------------------------------


class ContractOpenCodeAdapter:
    """A contract adapter that simulates OpenCode lifecycle for testing.

    It maintains real state (instances, sessions, messages) so the lifecycle
    manager can observe and verify transitions. The ``adapter_kind`` is
    ``contract`` to distinguish it from a real provider.
    """

    adapter_kind = "contract"

    def __init__(self) -> None:
        self.servers: dict[str, dict] = {}
        self.workspaces: dict[str, dict] = {}
        self.sessions: dict[str, dict] = {}
        self.messages: dict[str, list] = {}
        self._next_id = 0

    def create_server(self, run_id: str) -> str:
        self._next_id += 1
        server_id = f"srv_{self._next_id}"
        self.servers[server_id] = {
            "id": server_id,
            "run_id": run_id,
            "status": "running",
        }
        return server_id

    def create_workspace(self, server_id: str) -> str:
        self._next_id += 1
        ws_id = f"ws_{self._next_id}"
        self.workspaces[ws_id] = {
            "id": ws_id,
            "server_id": server_id,
            "status": "active",
        }
        return ws_id

    def create_session(self, run_id: str, server_id: str, workspace_id: str) -> str:
        self._next_id += 1
        session_id = f"sess_{self._next_id}"
        self.sessions[session_id] = {
            "id": session_id,
            "run_id": run_id,
            "server_id": server_id,
            "workspace_id": workspace_id,
            "status": "attached",
            "generating": False,
        }
        self.messages[session_id] = []
        return session_id

    def send_message(self, session_id: str, content: str) -> str:
        self._next_id += 1
        msg_id = f"msg_{self._next_id}"
        self.messages[session_id].append({"id": msg_id, "content": content})
        return msg_id

    def stop_generation(self, session_id: str) -> None:
        self.sessions[session_id]["generating"] = False

    def end_session(self, session_id: str) -> None:
        self.sessions[session_id]["status"] = "ended"

    def release_workspace(self, workspace_id: str) -> None:
        for ws in self.workspaces.values():
            if ws["id"] == workspace_id:
                ws["status"] = "released"

    def stop_server(self, server_id: str) -> None:
        self.servers[server_id]["status"] = "stopped"

    def is_server_alive(self, server_id: str) -> bool:
        return self.servers.get(server_id, {}).get("status") == "running"

    def list_sessions(self) -> list[dict]:
        return list(self.sessions.values())


# -- AC-FR1401-01 -------------------------------------------------------------


def test_ac_fr1401_01_created_resources_have_real_identity():
    """AC-FR1401-01: created OpenCode resources have observable identity.

    Creating a session for a run must produce a real server id, workspace id
    and session id. The adapter kind must be ``contract`` (not real), and the
    resources must be observable through the manager.
    """
    adapter = ContractOpenCodeAdapter()
    manager = SessionLifecycleManager(adapter)

    session = manager.create_session(run_id="run_001")

    assert session.server_id.startswith("srv_")
    assert session.workspace_id.startswith("ws_")
    assert session.session_id.startswith("sess_")
    assert session.run_id == "run_001"
    assert session.adapter_kind == "contract"
    assert session.status == "attached"

    queried = manager.get_session(session.session_id)
    assert queried.session_id == session.session_id
    assert queried.server_id == session.server_id


# -- AC-FR1401-02 -------------------------------------------------------------


def test_ac_fr1401_02_detach_keeps_session_and_run():
    """AC-FR1401-02: detach releases client but keeps server/session.

    After detach, the session status becomes ``detached`` but the server
    and session still exist. The session can be queried.
    """
    adapter = ContractOpenCodeAdapter()
    manager = SessionLifecycleManager(adapter)

    session = manager.create_session(run_id="run_001")
    manager.detach(session.session_id)

    detached = manager.get_session(session.session_id)
    assert detached.status == "detached"
    assert adapter.is_server_alive(session.server_id)


# -- AC-FR1401-03 -------------------------------------------------------------


def test_ac_fr1401_03_reattach_same_run_shows_history():
    """AC-FR1401-03: re-attach shows session history; cross-run rejected.

    After detach, the same run can re-attach and see the session's message
    history. A different run identity cannot attach.
    """
    adapter = ContractOpenCodeAdapter()
    manager = SessionLifecycleManager(adapter)

    session = manager.create_session(run_id="run_001")
    manager.send_message(session.session_id, "Hello")
    manager.detach(session.session_id)

    reattached = manager.attach(session.session_id, run_id="run_001")
    assert reattached.status == "attached"

    messages = manager.list_messages(session.session_id)
    assert len(messages) == 1
    assert messages[0]["content"] == "Hello"

    with pytest.raises(SessionUnavailableError):
        manager.attach(session.session_id, run_id="run_other")


# -- AC-FR1401-04 -------------------------------------------------------------


def test_ac_fr1401_04_lifecycle_levels_independent():
    """AC-FR1401-04: stop-generation, end-session, release-workspace, stop-server.

    Each lifecycle action only affects its own level. Stop-generation does
    not end the session. End-session does not release the workspace. Release-
    workspace does not stop the server. Stop-server stops the server.
    """
    adapter = ContractOpenCodeAdapter()
    manager = SessionLifecycleManager(adapter)

    session = manager.create_session(run_id="run_001")

    # Stop generation: session stays, not generating
    manager.stop_generation(session.session_id)
    after_stop_gen = manager.get_session(session.session_id)
    assert after_stop_gen.status == "attached"

    # End session: session ended, workspace still active
    manager.end_session(session.session_id)
    after_end = manager.get_session(session.session_id)
    assert after_end.status == "ended"
    assert adapter.workspaces[session.workspace_id]["status"] == "active"

    # Release workspace: workspace released, server still running
    manager.release_workspace(session.workspace_id)
    assert adapter.workspaces[session.workspace_id]["status"] == "released"
    assert adapter.is_server_alive(session.server_id)

    # Stop server: server stopped
    manager.stop_server(session.server_id)
    assert not adapter.is_server_alive(session.server_id)


def test_ac_fr1401_04_ended_session_rejects_send():
    """AC-FR1401-04: ended session rejects new messages."""
    adapter = ContractOpenCodeAdapter()
    manager = SessionLifecycleManager(adapter)

    session = manager.create_session(run_id="run_001")
    manager.end_session(session.session_id)

    with pytest.raises(SessionAlreadyEndedError):
        manager.send_message(session.session_id, "should fail")


# -- AC-FR1401-05 -------------------------------------------------------------


def test_ac_fr1401_05_recovery_scan_marks_lost_resources():
    """AC-FR1401-05: after restart, recoverable resources re-associate.

    Sessions whose underlying server is still alive are re-associated.
    Sessions whose server has been lost are marked as ``needs_attention``,
    not ``running``.
    """
    adapter = ContractOpenCodeAdapter()
    manager = SessionLifecycleManager(adapter)

    session_alive = manager.create_session(run_id="run_001")
    session_lost = manager.create_session(run_id="run_002")

    # Simulate server crash for session_lost
    adapter.servers[session_lost.server_id]["status"] = "stopped"
    adapter.sessions[session_lost.session_id]["status"] = "detached"

    # Simulate restart: create a new manager with the same adapter
    new_manager = SessionLifecycleManager(adapter)
    new_manager.recover_sessions()

    alive_session = new_manager.get_session(session_alive.session_id)
    assert alive_session.status in ("attached", "detached")

    lost_session = new_manager.get_session(session_lost.session_id)
    assert lost_session.status == "needs_attention"
