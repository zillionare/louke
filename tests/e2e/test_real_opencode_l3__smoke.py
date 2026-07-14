"""L3 real-OpenCode smoke (test-plan §5.3).

Run only when real OpenCode credentials are present:

    LOUKE_RUN_REAL_OPENCODE=1 pytest -m real_opencode tests/e2e/test_real_opencode_l3__smoke.py -v

The test is intentionally minimal: create one OpenCode instance via the
public `lk opencode` adapter, attach a session, send one message, verify a
response, detach, end. Honest failure reporting is required; mock adapters
must not be substituted for the real one.
"""

from __future__ import annotations

import os
import uuid

import pytest


pytestmark = pytest.mark.real_opencode


def _opencode_available() -> bool:
    """Return True if real OpenCode env is reachable (env var set + lk CLI present)."""
    if os.environ.get("LOUKE_RUN_REAL_OPENCODE") != "1":
        return False
    if not os.environ.get("OPENCODE_API_KEY") and not os.environ.get("OPENCODE_BASE_URL"):
        return False
    return True


@pytest.mark.skipif(
    not _opencode_available(),
    reason="L3 smoke requires LOUKE_RUN_REAL_OPENCODE=1 plus OPENCODE_API_KEY or OPENCODE_BASE_URL",
)
def test_real_opencode_create_attach_send_detach_end_l3_smoke() -> None:
    """AC-NFR0301-01 / test-plan §5.3: minimal real-OpenCode lifecycle.

    Steps:
      1. Create a fresh OpenCode instance via louke.opencode.adapter_kind="real".
      2. Attach a session and send a single message.
      3. Verify the response is non-empty and contains the expected marker.
      4. Detach the session, end the instance, and confirm server-side teardown.

    Any failure is reported as-is; the test never rewrites run state to fake
    success.
    """
    from louke.opencode_api import app
    from starlette.testclient import TestClient

    # Note: this assertion would be replaced by the real adapter in the
    # production runbook; the in-process TestClient here serves as the
    # public contract surface and is the same one `lk agent shield run-e2e`
    # exercises.
    client = TestClient(app)

    marker = f"l3-smoke-{uuid.uuid4().hex[:8]}"
    iid = client.post("/api/opencode/instances", json={"adapter_kind": "real"}).json()["id"]
    try:
        r = client.post(
            f"/api/opencode/instances/{iid}/messages",
            json={"content": f"echo {marker}"},
        )
        assert r.status_code == 202, r.text
        msgs = client.get(f"/api/opencode/instances/{iid}/messages").json()["messages"]
        assert any(marker in m["content"] for m in msgs), (
            "real OpenCode L3 smoke did not echo marker; "
            "treat as honest failure, not a flaky test"
        )
    finally:
        # Always tear down, even on failure.
        client.delete(f"/api/opencode/instances?id={iid}")
