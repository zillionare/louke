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
from typing import Any

import httpx
import pytest


pytestmark = pytest.mark.real_opencode


def _best_effort(step: str, fn: Any, *args: Any, **kwargs: Any) -> None:
    """Run a best-effort teardown step, logging failures to stderr.

    Teardown must continue past errors so a failure in one step does not mask
    the assertion that triggered the finally block. FAKE-003: errors are
    surfaced on stderr (not swallowed with ``pass``) so silent failures stay
    observable.

    Args:
        step: Label identifying the teardown step (e.g. ``"cancel"``).
        fn: Callable to invoke; receives ``*args`` / ``**kwargs``.
        *args: Positional arguments forwarded to ``fn``.
        **kwargs: Keyword arguments forwarded to ``fn``.
    """
    try:
        fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 - best-effort teardown
        print(f"  teardown warn ({step}): {exc}", file=sys.stderr)


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
    reason=(
        "#170: L3 smoke requires LOUKE_RUN_REAL_OPENCODE=1 + reachable "
        "LOUKE_OPENCODE_BASE_URL (AC-FR1401-01)"
    ),
)
def test_real_opencode_fr_1401_01_create_attach_send_detach_end_l3_smoke() -> None:
    """AC-FR1401-01 / test-plan §5.3 / AC-NFR0301-04: minimal real-OpenCode lifecycle.

    Tracked in issue #170 (https://github.com/zillionare/louke/issues/170).

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

    # `sent` tracks whether prompt_async was accepted, so the finally block
    # can cancel an in-flight turn before deleting the session. Defined on
    # every path (including the one where send_message raises) so teardown
    # ordering is deterministic.
    sent = False
    try:
        # 2. send message (async)
        marker = f"l3-smoke-marker-{uuid.uuid4().hex[:8]}"
        msg, accepted = adapter.send_message(
            instance.id, f"echo {marker}", correlation_id="l3-smoke",
        )
        sent = accepted
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

        # FAKE-002: value-based check tied to AC-FR1401-01 (real reply must
        # carry our marker), not just a non-null object reference.
        assert reply is not None and marker in reply.content, (
            f"real OpenCode did not echo marker {marker!r} within 15s. "
            f"last messages: {[m.content for m in messages]}"
        )

    finally:
        # 4. deterministic teardown: cancel any in-flight turn first, then
        #    delete the session. Each step is best-effort so a failure in one
        #    does not mask the assertion that triggered the finally.
        if sent:
            _best_effort(
                "cancel",
                adapter.cancel,
                instance.id,
                correlation_id="l3-smoke-teardown",
            )
        _best_effort("stop", adapter.stop, instance.id)
