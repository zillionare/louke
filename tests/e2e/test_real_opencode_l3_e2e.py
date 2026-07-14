"""L3 real-OpenCode smoke (test-plan §5.3, AC-FR1401-01, AC-NFR0301-04).

This is the HONEST L3 smoke. Run only when:

    LOUKE_OPENCODE_BASE_URL=http://127.0.0.1:<port> \\
    LOUKE_OPENCODE_BACKEND=real \\
    LOUKE_RUN_REAL_OPENCODE=1 \\
    pytest -m real_opencode tests/e2e/test_real_opencode_l3_e2e.py -v

The test creates a real OpenCode instance via louke.opencode.real.RealOpenCodeAdapter,
sends a message through it, waits for the async reply, and verifies the response
was received via list_messages. NO MOCK / NO ECHO. Failure is reported as-is.

If `opencode serve` is not reachable, the test is skipped (NOT passed).
"""

from __future__ import annotations

import os
import sys
import time
import uuid

import httpx
import pytest


pytestmark = pytest.mark.real_opencode


def _opencode_available() -> bool:
    """True if a real OpenCode server is reachable at LOUKE_OPENCODE_BASE_URL."""
    if os.environ.get("LOUKE_RUN_REAL_OPENCODE") != "1":
        return False
    base = os.environ.get("LOUKE_OPENCODE_BASE_URL", "").rstrip("/")
    if not base:
        return False
    try:
        r = httpx.get(f"{base}/global/health", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


@pytest.mark.skipif(
    not _opencode_available(),
    reason="L3 smoke requires LOUKE_RUN_REAL_OPENCODE=1 + reachable LOUKE_OPENCODE_BASE_URL",
)
def test_real_opencode_create_attach_send_detach_end_l3_smoke() -> None:
    """AC-FR1401-01 / test-plan §5.3 / AC-NFR0301-04: minimal real-OpenCode lifecycle.

    1. Create a session via POST /session on the real OpenCode server.
    2. Send a uniquely-marked message via POST /session/{id}/prompt_async.
    3. Poll GET /session/{id}/message until our marker appears (real reply).
    4. DELETE the session.

    Honest failure reporting: if any step fails, the test fails with the actual
    HTTP response (status, body excerpt). No retries that hide failures.
    """
    sys.path.insert(0, "/Users/openclaw/workspace/louke")
    from louke.opencode.real import RealOpenCodeAdapter
    from louke.opencode.adapter import Instance, Message

    base_url = os.environ["LOUKE_OPENCODE_BASE_URL"].rstrip("/")
    adapter = RealOpenCodeAdapter(base_url=base_url, timeout=10.0)

    # 1. create
    instance = adapter.create(correlation_id=f"l3-smoke-{uuid.uuid4().hex[:6]}")
    assert isinstance(instance, Instance)
    assert instance.status in ("starting", "running"), (
        f"create returned unexpected status: {instance.status!r}"
    )

    try:
        # 2. send message (async)
        marker = f"l3-smoke-marker-{uuid.uuid4().hex[:8]}"
        msg, accepted = adapter.send_message(
            instance.id, f"echo {marker}", correlation_id="l3-smoke",
        )
        assert isinstance(msg, Message)
        assert accepted is True, (
            "send_message did not return accepted=True; real OpenCode prompt_async "
            "should return 204 (accepted)"
        )

        # 3. poll for the reply (real OpenCode serves replies asynchronously)
        deadline = time.time() + 15.0
        reply = None
        messages: list[Message] = []
        while time.time() < deadline:
            messages = adapter.list_messages(instance.id, after_message_id=None)
            for m in messages:
                if m.role == "assistant" and marker in m.content:
                    reply = m
                    break
            if reply is not None:
                break
            time.sleep(0.5)

        assert reply is not None, (
            f"real OpenCode did not echo marker {marker!r} within 15s. "
            f"last messages: {[m.content for m in messages]}"
        )

    finally:
        # 4. always tear down (even on assertion failure)
        try:
            adapter.stop(instance.id)
        except Exception:
            pass
