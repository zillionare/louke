"""TestClient tests for the /api/gates sub-app (FR-0501, FR-0801, FR-0901).

AC references covered:
- AC-FR0501-01: gates for a run can be listed via GET /runs/{run_id}/gates.
- AC-FR0501-02: a gate decision (approve/reject) can be submitted via POST /{gate_id}/decisions.
- AC-FR0501-03: a gate's detail can be retrieved via GET /{gate_id}.
- AC-FR0501-04: submitting a decision for an unknown gate returns 404 NOT_FOUND.
- AC-FR0501-05: an unauthenticated principal (no header) returns 403 FORBIDDEN.
- AC-FR0801-01: a reject decision requires a reason or returns 400 VALIDATION_ERROR.
- AC-FR0901-01: a stale revision returns 409 STALE.
"""

from __future__ import annotations

import uuid
from typing import NamedTuple

import pytest
from starlette.testclient import TestClient

from louke.runtime.gates import Gate, GATE_WAITING
from louke.runtime.store import WorkflowRunStore
from louke.web.api.gates import create_app


class _Ctx(NamedTuple):
    """Bundle of test context returned by the ``client_env`` fixture."""

    client: TestClient
    store: WorkflowRunStore


def _make_gate(
    store: WorkflowRunStore,
    run_id: str,
    step_id: str = "requirements_approval",
) -> Gate:
    """Create a gate directly in ``store`` with a unique id.

    A unique ``gate_id`` is generated per call so multiple gates against the
    same store never collide on the ``gates.gate_id`` UNIQUE constraint.

    This helper MUST be called from the same thread that owns the store's
    sqlite connection (i.e. inside the TestClient portal).
    """
    gate = Gate(
        gate_id=f"gate_{uuid.uuid4().hex[:8]}",
        challenge_id=f"chal_{uuid.uuid4().hex[:8]}",
        run_id=run_id,
        step_id=step_id,
        expected_revision=0,
        bound_digest="sha256:abc",
        status=GATE_WAITING,
        created_at="2026-07-14T00:00:00Z",
    )
    store.create_gate(gate)
    return gate


def _make_run(store: WorkflowRunStore) -> str:
    """Create a real run so the store has a run_id to reference.

    Must be called from the store's owning thread (the TestClient portal).
    """
    run = store.create_run(store._catalog.get("new_feature", "1"))
    return run.run_id


@pytest.fixture
def client_env() -> _Ctx:
    """Return a started TestClient and the lazily-created store.

    The store is created *inside* the TestClient portal thread (via a first
    HTTP request that triggers ``get_or_create_store``) so subsequent direct
    store access from the portal thread is safe. The TestClient is used as a
    context manager so the portal stays alive for the lifetime of the test.
    """
    app = create_app()
    with TestClient(app) as client:
        # Trigger lazy store creation in the portal thread.
        client.get("/runs/run_warmup/gates")
        store = app.state.v12_run_store
        yield _Ctx(client=client, store=store)


def test_list_gates_for_run(client_env: _Ctx) -> None:
    """AC-FR0501-01: gates for a run can be listed via GET /runs/{run_id}/gates."""
    ctx = client_env

    def setup() -> str:
        run_id = _make_run(ctx.store)
        _make_gate(ctx.store, run_id=run_id, step_id="requirements_approval")
        _make_gate(ctx.store, run_id=run_id, step_id="m_lock")
        return run_id

    run_id = ctx.client.portal.call(setup)
    resp = ctx.client.get(f"/runs/{run_id}/gates")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 2
    assert all(item["run_id"] == run_id for item in items)


def test_list_gates_unknown_run(client_env: _Ctx) -> None:
    """AC-FR0501-04: listing gates for an unknown run returns 404 NOT_FOUND."""
    resp = client_env.client.get("/runs/run_unknown/gates")
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "NOT_FOUND"


def test_get_gate_detail(client_env: _Ctx) -> None:
    """AC-FR0501-03: a gate's detail can be retrieved via GET /{gate_id}."""
    ctx = client_env

    def make_gate() -> Gate:
        run_id = _make_run(ctx.store)
        return _make_gate(ctx.store, run_id=run_id)

    gate = ctx.client.portal.call(make_gate)
    resp = ctx.client.get(f"/{gate.gate_id}")
    assert resp.status_code == 200
    assert resp.json()["gate_id"] == gate.gate_id


def test_get_gate_not_found(client_env: _Ctx) -> None:
    """AC-FR0501-04: GET on an unknown gate returns 404 NOT_FOUND."""
    resp = client_env.client.get("/gate_unknown")
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "NOT_FOUND"


def test_submit_approve_decision(client_env: _Ctx) -> None:
    """AC-FR0501-02: an approve decision can be submitted via POST /{gate_id}/decisions."""
    ctx = client_env

    def setup() -> tuple[str, Gate]:
        from louke.runtime.domain import RuntimeCommand
        from louke.runtime.orchestrator import WorkflowOrchestrator

        run_id = _make_run(ctx.store)
        gate = _make_gate(ctx.store, run_id=run_id, step_id="requirements_approval")
        orch = WorkflowOrchestrator(ctx.store)
        orch.apply_command(
            RuntimeCommand(run_id=run_id, expected_revision=0, result="done")
        )
        return run_id, gate

    run_id, gate = ctx.client.portal.call(setup)
    resp = ctx.client.post(
        f"/{gate.gate_id}/decisions",
        json={
            "run_id": run_id,
            "decision": "approve",
            "bound_digest": gate.bound_digest,
            "expected_revision": 1,
            "principal": {"kind": "human", "id": "alice"},
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


def test_submit_decision_unknown_gate(client_env: _Ctx) -> None:
    """AC-FR0501-04: submitting a decision for an unknown gate returns 404."""
    ctx = client_env

    def make_run() -> str:
        return _make_run(ctx.store)

    run_id = ctx.client.portal.call(make_run)
    resp = ctx.client.post(
        "/gate_unknown/decisions",
        json={
            "run_id": run_id,
            "decision": "approve",
            "bound_digest": "sha256:abc",
            "expected_revision": 0,
            "principal": {"kind": "human", "id": "alice"},
        },
    )
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "NOT_FOUND"


def test_submit_decision_unauthenticated_principal(client_env: _Ctx) -> None:
    """AC-FR0501-05: a missing/unauthenticated principal returns 403 FORBIDDEN."""
    ctx = client_env

    def setup() -> tuple[str, Gate]:
        run_id = _make_run(ctx.store)
        gate = _make_gate(ctx.store, run_id=run_id)
        return run_id, gate

    run_id, gate = ctx.client.portal.call(setup)
    resp = ctx.client.post(
        f"/{gate.gate_id}/decisions",
        json={
            "run_id": run_id,
            "decision": "approve",
            "bound_digest": gate.bound_digest,
            "expected_revision": 0,
            "principal": {"kind": "machine", "id": "bot"},
        },
    )
    assert resp.status_code == 403
    assert resp.json()["error_code"] == "FORBIDDEN"


def test_submit_reject_requires_reason(client_env: _Ctx) -> None:
    """AC-FR0801-01: a reject decision requires a reason or returns 400."""
    ctx = client_env

    def setup() -> tuple[str, Gate]:
        from louke.runtime.domain import RuntimeCommand
        from louke.runtime.orchestrator import WorkflowOrchestrator

        run_id = _make_run(ctx.store)
        gate = _make_gate(ctx.store, run_id=run_id, step_id="requirements_approval")
        orch = WorkflowOrchestrator(ctx.store)
        orch.apply_command(
            RuntimeCommand(run_id=run_id, expected_revision=0, result="done")
        )
        return run_id, gate

    run_id, gate = ctx.client.portal.call(setup)
    resp = ctx.client.post(
        f"/{gate.gate_id}/decisions",
        json={
            "run_id": run_id,
            "decision": "reject",
            "bound_digest": gate.bound_digest,
            "expected_revision": 1,
            "principal": {"kind": "human", "id": "alice"},
            "reason": "",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "VALIDATION_ERROR"


def test_submit_decision_stale_revision(client_env: _Ctx) -> None:
    """AC-FR0901-01: a stale expected_revision returns 409 STALE."""
    ctx = client_env

    def setup() -> tuple[str, Gate]:
        run_id = _make_run(ctx.store)
        gate = _make_gate(ctx.store, run_id=run_id)
        return run_id, gate

    run_id, gate = ctx.client.portal.call(setup)
    resp = ctx.client.post(
        f"/{gate.gate_id}/decisions",
        json={
            "run_id": run_id,
            "decision": "approve",
            "bound_digest": gate.bound_digest,
            "expected_revision": 99,
            "principal": {"kind": "human", "id": "alice"},
        },
    )
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "STALE"
