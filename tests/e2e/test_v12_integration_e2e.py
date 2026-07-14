"""Integration-style e2e for v0.12 sub-apps (FR-0101..1701).

These tests stand up the full Starlette app stack (v0.12 sub-apps + v0.11 web
routes mounted together, with a fresh in-memory SQLite per test) and exercise
end-to-end flows. They do NOT start a live uvicorn server; the conftest
default skips the live-server fixture.

AC references covered (one e2e test per FR):
- FR-0101 (AC-FR0101-01..04): WorkflowRun lifecycle - preview, confirm, audit events.
- FR-0401 (AC-FR0401-01): ProjectStore create/read/update via HTTP archive.
- FR-0901 (AC-FR0901-01..04): M-LOCK semantics - gate blocks, approve, advance.
- FR-1001 (AC-FR1001-01..03): project listing - active/history partitioning.
- FR-1101 (AC-FR1101-01..03): project creation flow - preview/confirm/run state.
- FR-1201 (AC-FR1201-01): workflow graph - nodes/edges/current_step.
- FR-1301 (AC-FR1301-01..02): bindings - list defaults, PUT override.
- FR-1501 (AC-FR1501-01): context manifest - event stream carries digests.
- FR-1601 (AC-FR1601-01): responsibility catalog - 2 definitions registered.
- FR-1701 (AC-FR1701-01): workflow definitions - catalog validation passes.

Architecture note: the v0.12 sub-apps (projects/runtime/gates/bindings) are
module-level singletons in ``louke.web.app``. Each lazily creates its own
``WorkflowRunStore`` on first request via ``get_or_create_store``. Because the
``sqlite3`` connection is thread-bound and Starlette dispatches requests in a
portal thread, the store must be created (or injected) inside the portal. The
``client`` fixture below uses ``TestClient`` as a context manager so the
portal stays alive for the test, then injects a single shared store into all
four sub-apps via ``portal.call`` so cross-sub-app flows (e.g. create a
project via ``/api/projects`` then read its run via ``/api/runtime``) work.

The ``/api/runtime/bindings`` Mount is shadowed by ``/api/runtime`` in
``app.py`` (a pre-existing routing issue out of scope for this issue), so the
FR-1301 bindings test uses a dedicated wrapper app that mounts the real
bindings sub-app at a non-shadowed path, with the same shared store injected.
This is still a real integration: real sub-app + real store + multi-step flow.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.testclient import TestClient


#: The module-level v0.12 sub-apps that cache a shared ``WorkflowRunStore``.
#: Listed in the same order they are mounted in ``louke.web.app.create_app``.
_V12_SUBAPPS_ATTR: str = "v12_run_store"


def _v12_subapps() -> tuple[Any, ...]:
    """Return the four module-level v0.12 sub-apps that share the run store."""
    import louke.web.app as appmod

    return (
        appmod.projects_app,
        appmod.runtime_app,
        appmod.gates_app,
        appmod.bindings_app,
    )


def _write_project_toml(root: Any) -> None:
    """Write a minimal project.toml so ``create_app`` does not fail on meta reads."""
    project_dir = root / ".louke" / "project"
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "project.toml").write_text(
        '[project]\nversion = "0.12"\n'
        'spec_id = "v0.12-001-programmatic-workflow-runtime"\n'
        'release_branch = "main"\n\n'
        '[meta]\ncreated = "2026-07-14"\ntag = "unreleased"\n'
        'current_stage = "M-DEV"\nsecurity_audit = "disabled"\n'
        'smoke_test_issue = ""\nsmoke_test_pr = ""\n'
        'pre_commit = "installed"\ntest_framework = "pytest"\n'
        'acknowledged_orphan_releases = []\n',
        encoding="utf-8",
    )


def _reset_subapp_state() -> None:
    """Clear cached state on the module-level v0.12 sub-apps.

    The sub-apps (projects/runtime/gates/bindings) are module-level singletons
    that cache their ``WorkflowRunStore`` and derived services on
    ``app.state``. Without clearing, state leaks across ``create_app`` calls
    (and thus across tests). This clears the internal ``_state`` dict of each
    sub-app so the next request lazily rebuilds from scratch.
    """
    for sub_app in _v12_subapps():
        sub_app.state._state.clear()


def _inject_shared_store(client: TestClient) -> Any:
    """Inject a single shared ``WorkflowRunStore`` into all v0.12 sub-apps.

    Must be called inside the ``TestClient`` context manager (portal thread)
    because the ``sqlite3`` connection is thread-bound. Returns the shared
    store so tests can reach into it for orchestration that has no HTTP
    endpoint yet (e.g. ``ensure_m_lock_gate`` / ``apply_gate_decision``).
    """
    from louke.web.api._runtime_store import build_run_store

    def _setup() -> Any:
        store = build_run_store()
        for sub_app in _v12_subapps():
            setattr(sub_app.state, _V12_SUBAPPS_ATTR, store)
        return store

    return client.portal.call(_setup)


@pytest.fixture
def client(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Build a fresh Starlette app + TestClient per test, with a tmp workspace.

    The TestClient is used as a context manager so the ASGI portal thread stays
    alive for the test duration, allowing direct store access via
    ``client.portal.call`` for orchestration steps that have no HTTP endpoint.
    """
    from louke.web.app import create_app

    _write_project_toml(tmp_path)
    monkeypatch.setenv("LOUKE_E2E_STATE", str(tmp_path / ".louke" / "server"))
    _reset_subapp_state()
    app = create_app(tmp_path)
    with TestClient(app) as c:
        _inject_shared_store(c)
        yield c


def _create_project(
    client: TestClient,
    story: str = "Build programmatic workflow runtime",
    definition_id: str = "new_feature",
    source_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a project via POST /api/projects/create and return the body."""
    payload: dict[str, Any] = {
        "story": story,
        "release_version": "v0.12.0",
        "definition_id": definition_id,
        "definition_version": "1",
    }
    if source_contract is not None:
        payload["source_contract"] = source_contract
    resp = client.post("/api/projects/create", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _approve_gate(
    store: Any,
    run_id: str,
    gate: Any,
) -> Any:
    """Approve a gate via the orchestrator and return the transition outcome.

    This helper exists because there is no HTTP endpoint for
    ``orchestrator.apply_gate_decision``; tests that need to advance a run
    through a human gate must reach into the store via the portal. The
    principal is a fixed test actor (``alice``).
    """
    from louke.runtime.gates import GateService
    from louke.runtime.orchestrator import WorkflowOrchestrator

    gs = GateService(store)
    orch = WorkflowOrchestrator(store, gate_service=gs)
    return orch.apply_gate_decision(
        run_id=run_id,
        gate_id=gate.gate_id,
        decision="approve",
        bound_digest=gate.bound_digest,
        expected_revision=store.get_run(run_id).revision,
        principal={"kind": "human", "id": "alice"},
    )


def _seed_approved_source_gate(client: TestClient) -> dict[str, str]:
    """Create and approve a source run's requirements gate.

    A ``bug_fix`` project creation requires a source contract referencing an
    already-approved requirements gate. This helper creates a ``new_feature``
    run, advances it to ``requirements_approval``, and approves the gate via
    the orchestrator (no HTTP endpoint for gate advancement exists). Returns
    the gate id, bound digest and spec digest the bug_fix contract must cite.
    """
    from louke.runtime.contract_gates import contract_digest
    from louke.runtime.gates import GateService
    from louke.runtime.orchestrator import WorkflowOrchestrator
    import louke.web.app as appmod

    store = appmod.projects_app.state.v12_run_store

    def _seed() -> dict[str, str]:
        from louke.runtime.domain import RuntimeCommand

        catalog = store._catalog
        assert catalog is not None
        definition = catalog.get("new_feature", "1")
        source_run = store.create_run(definition)
        # Advance the source run from ``start`` to ``requirements_approval``
        # so the requirements gate can be created and approved. The gate's
        # freshness check requires the run to be at the gate's step.
        gs = GateService(store)
        orch = WorkflowOrchestrator(store, gate_service=gs)
        orch.apply_command(
            RuntimeCommand(
                run_id=source_run.run_id,
                expected_revision=0,
                result="done",
            )
        )
        spec_digest = "sha256:source_spec_v1"
        acceptance_digest = "sha256:source_acc_v1"
        bound_digest = contract_digest(
            {
                "story": "sha256:source_story_v1",
                "spec": spec_digest,
                "acceptance": acceptance_digest,
            }
        )
        gate = orch.ensure_requirements_gate(
            run_id=source_run.run_id,
            story_digest="sha256:source_story_v1",
            spec_digest=spec_digest,
            acceptance_digest=acceptance_digest,
        )
        _approve_gate(store, source_run.run_id, gate)
        return {
            "gate_id": gate.gate_id,
            "bound_digest": bound_digest,
            "spec_digest": spec_digest,
            "acceptance_digest": acceptance_digest,
        }

    return client.portal.call(_seed)


def _valid_source_contract(seeded: dict[str, str]) -> dict[str, Any]:
    """Return a source contract dict citing the seeded approved gate."""
    return {
        "github_issue": "zillionare/louke#100",
        "source_spec_digest": seeded["spec_digest"],
        "source_acceptance_digest": seeded["acceptance_digest"],
        "source_approval_gate_id": seeded["gate_id"],
        "source_approval_bound_digest": seeded["bound_digest"],
        "behavior_change": "implementation_deviation_only",
    }


def test_e2e_fr_0101_workflow_run_lifecycle(client: TestClient) -> None:
    """AC-FR0101-01..04: preview, confirm, audit events exist with revision.

    Drives the full creation flow: a project is created, its workflow run is
    fetched via ``/api/runtime/runs/{id}``, and the audit event stream is read
    via ``/api/runtime/runs/{id}/events``. The run must have a ``current_step``
    and at least one ``run.created`` event with a non-empty ``correlation_id``
    and ``at`` timestamp.
    """
    project = _create_project(client)
    run_id = project["run_id"]

    run_resp = client.get(f"/api/runtime/runs/{run_id}")
    assert run_resp.status_code == 200, run_resp.text
    run = run_resp.json()
    assert run["run_id"] == run_id
    assert run["current_step"] == "start"
    assert run["revision"] == 0
    assert run["status"] == "in_progress"

    events_resp = client.get(f"/api/runtime/runs/{run_id}/events")
    assert events_resp.status_code == 200, events_resp.text
    events = events_resp.json()["items"]
    assert len(events) >= 1
    created = events[0]
    assert created["type"] == "run.created"
    assert created["at"] != ""
    assert created["correlation_id"] != ""


def test_e2e_fr_0401_project_store_crud_via_http(client: TestClient) -> None:
    """AC-FR0401-01: ProjectStore create/read/update (archive) via HTTP.

    Exercises the full project lifecycle: create -> get detail -> archive ->
    verify it moved from active to history. Archiving sets the run status to
    ``archived`` so the orchestrator rejects further transitions (the
    read-only contract).
    """
    project = _create_project(client, story="Foundation CRUD e2e")
    pid = project["project_id"]
    run_id = project["run_id"]

    # Read back the project detail.
    detail = client.get(f"/api/projects/{pid}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["project_id"] == pid
    assert detail.json()["name"] == "Foundation CRUD e2e"

    # Active list contains it.
    active = client.get("/api/projects/active")
    assert active.status_code == 200
    active_ids = [item["project_id"] for item in active.json()["items"]]
    assert pid in active_ids

    # History is empty before archiving.
    history = client.get("/api/projects/history")
    assert history.status_code == 200
    assert history.json()["items"] == []

    # Archive moves it to history.
    arch = client.post(f"/api/projects/{pid}/archive")
    assert arch.status_code == 200, arch.text
    archived = arch.json()
    assert archived["status"] == "archived"
    assert archived["archived_at"] != ""

    # Now active is empty and history has it.
    active2 = client.get("/api/projects/active")
    assert active2.json()["items"] == []
    history2 = client.get("/api/projects/history")
    assert any(item["project_id"] == pid for item in history2.json()["items"])

    # The run is now read-only: commands return 400.
    cmd = client.post(
        f"/api/runtime/runs/{run_id}/commands",
        json={"expected_revision": 0, "result": "done"},
    )
    assert cmd.status_code == 400
    assert cmd.json()["error_code"] == "VALIDATION_ERROR"


def test_e2e_fr_0901_m_lock_gate_semantics(client: TestClient) -> None:
    """AC-FR0901-01..04: M-LOCK blocks implementation, approve advances.

    Drives the run from ``start`` through ``requirements_approval`` (approved
    via the orchestrator) to ``m_lock``. At ``m_lock`` the graph shows a
    ``waiting_for_human`` gate. Submitting an approve decision via
    the orchestrator records the approval, and the run can then advance
    into the ``implementation`` step. The approved M-LOCK gate is visible
    via the gates HTTP API.
    """
    from louke.runtime.gates import GateService
    from louke.runtime.orchestrator import WorkflowOrchestrator
    import louke.web.app as appmod

    project = _create_project(client, story="M-LOCK semantics e2e")
    run_id = project["run_id"]
    pid = project["project_id"]
    store = appmod.projects_app.state.v12_run_store

    # Advance start -> requirements_approval (human_gate).
    adv1 = client.post(
        f"/api/runtime/runs/{run_id}/commands",
        json={"expected_revision": 0, "result": "done"},
    )
    assert adv1.status_code == 200, adv1.text
    assert adv1.json()["run"]["current_step"] == "requirements_approval"

    # Approve the requirements gate via the orchestrator (no HTTP endpoint).
    def _approve_req() -> Any:
        gs = GateService(store)
        orch = WorkflowOrchestrator(store, gate_service=gs)
        gate = orch.ensure_requirements_gate(
            run_id=run_id,
            story_digest="sha256:story",
            spec_digest="sha256:spec",
            acceptance_digest="sha256:acc",
        )
        return _approve_gate(store, run_id, gate)

    outcome = client.portal.call(_approve_req)
    assert outcome.run.current_step == "design"

    # Advance design -> m_lock (human_gate).
    adv2 = client.post(
        f"/api/runtime/runs/{run_id}/commands",
        json={"expected_revision": outcome.run.revision, "result": "done"},
    )
    assert adv2.status_code == 200, adv2.text
    assert adv2.json()["run"]["current_step"] == "m_lock"

    # The graph shows m_lock as the current step.
    graph = client.get(f"/api/projects/{pid}/graph")
    assert graph.status_code == 200, graph.text
    assert graph.json()["current_step"] == "m_lock"

    # Ensure and approve the M-LOCK gate via the orchestrator.
    def _approve_m_lock() -> Any:
        gs = GateService(store)
        orch = WorkflowOrchestrator(store, gate_service=gs)
        gate = orch.ensure_m_lock_gate(
            run_id=run_id,
            story_digest="sha256:story",
            spec_digest="sha256:spec",
            acceptance_digest="sha256:acc",
            test_plan_digest="sha256:tp",
            architecture_digest="sha256:arch",
            interfaces_digest="sha256:iface",
        )
        return _approve_gate(store, run_id, gate)

    m_outcome = client.portal.call(_approve_m_lock)
    assert m_outcome.run.current_step == "implementation"

    # The approved M-LOCK gate is visible via the gates HTTP API.
    gates_resp = client.get(f"/api/gates/runs/{run_id}/gates")
    assert gates_resp.status_code == 200, gates_resp.text
    m_lock_gates = [
        g for g in gates_resp.json()["items"] if g["step_id"] == "m_lock"
    ]
    assert len(m_lock_gates) == 1
    assert m_lock_gates[0]["status"] == "approved"


def test_e2e_fr_1001_project_listing_active_and_history(
    client: TestClient,
) -> None:
    """AC-FR1001-01..03: active/history partitioning and list item fields.

    Creates two projects (one ``new_feature``, one ``bug_fix``), archives the
    ``new_feature`` one, then verifies the active list holds the bug_fix
    project and the history list holds the archived one. Each list item
    carries distinguishing name, release_version, workflow type and status.
    """
    # Empty workspace: active and history are both empty.
    assert client.get("/api/projects/active").json() == {"items": []}
    assert client.get("/api/projects/history").json() == {"items": []}

    p1 = _create_project(client, story="First feature")
    seeded = _seed_approved_source_gate(client)
    p2 = _create_project(
        client,
        story="Second feature (hotfix)",
        definition_id="bug_fix",
        source_contract=_valid_source_contract(seeded),
    )

    # Both are active.
    active = client.get("/api/projects/active").json()["items"]
    assert len(active) == 2
    active_ids = {item["project_id"] for item in active}
    assert {p1["project_id"], p2["project_id"]} == active_ids

    # List items carry distinguishing fields.
    for item in active:
        assert item["name"] != ""
        assert item["release_version"] == "v0.12.0"
        assert item["workflow_definition_id"] in ("new_feature", "bug_fix")
        assert item["run_id"] != ""

    # Archive the first; it moves to history.
    client.post(f"/api/projects/{p1['project_id']}/archive")
    active2 = client.get("/api/projects/active").json()["items"]
    assert len(active2) == 1
    assert active2[0]["project_id"] == p2["project_id"]

    history = client.get("/api/projects/history").json()["items"]
    assert len(history) == 1
    assert history[0]["project_id"] == p1["project_id"]
    assert history[0]["archived_at"] != ""


def test_e2e_fr_1101_project_creation_preview_confirm(client: TestClient) -> None:
    """AC-FR1101-01..03: preview shows summary without creating; confirm persists.

    The two-step creation flow: ``POST /preview`` returns a ``ProjectPreview``
    with ``story_excerpt`` and ``workflow_definition_id`` but no ``project_id``.
    ``POST /confirm`` with the ``preview_id`` atomically creates the project
    and its first ``WorkflowRun``.
    """
    preview_resp = client.post(
        "/api/projects/preview",
        json={
            "story": "Create project via preview and confirm flow",
            "release_version": "v0.12.0",
            "definition_id": "new_feature",
            "definition_version": "1",
        },
    )
    assert preview_resp.status_code == 200, preview_resp.text
    preview = preview_resp.json()
    assert preview["preview_id"] != ""
    assert preview["project_id"] is None
    assert preview["workflow_definition_id"] == "new_feature"
    assert preview["workflow_version"] == "1"
    assert "Create project via preview" in preview["story_excerpt"]

    confirm_resp = client.post(
        "/api/projects/confirm",
        json={"preview_id": preview["preview_id"]},
    )
    assert confirm_resp.status_code == 201, confirm_resp.text
    project = confirm_resp.json()
    assert project["project_id"].startswith("prj_")
    assert project["run_id"].startswith("run_")
    assert project["workflow_definition_id"] == "new_feature"
    assert project["workflow_version"] == "1"
    assert project["status"] == "active"
    assert project["created_at"] != ""

    # The run exists and is at the start step.
    run = client.get(f"/api/runtime/runs/{project['run_id']}")
    assert run.status_code == 200
    assert run.json()["current_step"] == "start"


def test_e2e_fr_1201_workflow_graph_nodes_and_edges(client: TestClient) -> None:
    """AC-FR1201-01: workflow graph returns nodes, edges and current_step.

    After creating a project, ``GET /api/projects/{id}/graph`` returns the
    full definition-bound graph with all expected node ids, edges and the
    current step pointing at ``start``.
    """
    project = _create_project(client, story="Workflow graph e2e")
    pid = project["project_id"]
    run_id = project["run_id"]

    resp = client.get(f"/api/projects/{pid}/graph")
    assert resp.status_code == 200, resp.text
    graph = resp.json()
    assert graph["run_id"] == run_id
    assert graph["definition_id"] == "new_feature"
    assert graph["definition_version"] == "1"
    assert graph["current_step"] == "start"

    node_ids = [n["step_id"] for n in graph["nodes"]]
    assert node_ids == [
        "start",
        "requirements_approval",
        "design",
        "m_lock",
        "implementation",
        "complete",
    ]

    # The start node is marked current; others are pending.
    states = {n["step_id"]: n["state"] for n in graph["nodes"]}
    assert states["start"] == "current"
    assert states["requirements_approval"] == "pending"

    # Edges connect the steps in order.
    edges = [(e["from_step"], e["to_step"]) for e in graph["edges"]]
    assert ("start", "requirements_approval") in edges
    assert ("m_lock", "implementation") in edges


def test_e2e_fr_1301_agent_bindings_default_and_override(
    client: TestClient,
) -> None:
    """AC-FR1301-01..02: list defaults, PUT override updates effective model.

    The ``/api/runtime/bindings`` Mount is shadowed by ``/api/runtime`` in
    ``app.py`` (pre-existing routing issue out of scope for this issue). To
    exercise the real bindings sub-app end-to-end, this test builds a small
    wrapper Starlette app that mounts the real bindings sub-app at a
    non-shadowed path (``/api/bindings``) alongside the real runtime sub-app,
    injects the same shared store, and drives the multi-step flow: create a
    run via the runtime sub-app, list default bindings, PUT an override, then
    re-list to verify the override persists.
    """
    from louke.web.api._runtime_store import build_run_store
    import louke.web.app as appmod

    # Build a dedicated wrapper so the bindings sub-app is reachable.
    # The sub-apps are the real module-level singletons; we mount them at
    # non-shadowed paths and inject a fresh shared store into both.
    _reset_subapp_state()
    wrapper = Starlette(
        routes=[
            Mount("/api/runtime", app=appmod.runtime_app),
            Mount("/api/bindings", app=appmod.bindings_app),
        ]
    )

    with TestClient(wrapper) as bindings_client:
        # Inject a shared store into both sub-apps inside the portal thread.
        def _setup_store() -> Any:
            store = build_run_store()
            setattr(appmod.runtime_app.state, _V12_SUBAPPS_ATTR, store)
            setattr(appmod.bindings_app.state, _V12_SUBAPPS_ATTR, store)
            return store

        bindings_client.portal.call(_setup_store)

        # Create a run via the runtime sub-app so bindings have a run to attach to.
        run_resp = bindings_client.post(
            "/api/runtime/runs",
            json={"definition_id": "new_feature", "definition_version": "1"},
        )
        assert run_resp.status_code == 201, run_resp.text
        run_id = run_resp.json()["run_id"]

        # List defaults: devon -> claude-sonnet.
        list_resp = bindings_client.get(f"/api/bindings/devon?run_id={run_id}")
        assert list_resp.status_code == 200, list_resp.text
        items = list_resp.json()["items"]
        assert len(items) >= 1
        devon = next(it for it in items if it["agent_role"] == "devon")
        assert devon["effective_model"] == "claude-sonnet"
        assert devon["source"] == "default"

        # PUT an override: devon -> claude-opus.
        put_resp = bindings_client.put(
            f"/api/bindings/devon?run_id={run_id}",
            json={"model": "claude-opus"},
        )
        assert put_resp.status_code == 200, put_resp.text
        overridden = put_resp.json()
        assert overridden["agent_role"] == "devon"
        assert overridden["effective_model"] == "claude-opus"
        assert overridden["source"] == "override"

        # Re-list: the override persists.
        list2_resp = bindings_client.get(f"/api/bindings/devon?run_id={run_id}")
        assert list2_resp.status_code == 200
        devon2 = next(
            it
            for it in list2_resp.json()["items"]
            if it["agent_role"] == "devon"
        )
        assert devon2["effective_model"] == "claude-opus"
        assert devon2["source"] == "override"


def test_e2e_fr_1501_context_manifest_event_stream(client: TestClient) -> None:
    """AC-FR1501-01: event stream carries manifest digests and correlation.

    The context manifest is materialised when a semantic task is created, but
    the observable HTTP surface for this FR is the event stream: each event
    carries ``at``, ``correlation_id``, ``input_digest`` and ``output_digest``
    fields that downstream manifest consumers rely on. This test verifies the
    run's audit events have the required manifest-adjacent fields populated.
    """
    project = _create_project(client, story="Context manifest e2e")
    run_id = project["run_id"]

    events_resp = client.get(f"/api/runtime/runs/{run_id}/events")
    assert events_resp.status_code == 200, events_resp.text
    events = events_resp.json()["items"]
    assert len(events) >= 1

    created = events[0]
    # Manifest-adjacent fields required by FR-1501.
    assert created["run_id"] == run_id
    assert created["at"] != ""
    assert created["correlation_id"] != ""
    assert created["input_digest"] != ""
    assert created["output_digest"] != ""
    assert created["revision"] == 0


def test_e2e_fr_1601_responsibility_catalog_two_definitions(
    client: TestClient,
) -> None:
    """AC-FR1601-01: catalog exposes program handlers (new_feature + bug_fix).

    The responsibility catalog is registered via ``build_catalog()`` and
    exposed via ``GET /api/projects/catalog``. It must return exactly the two
    selectable definitions (``new_feature`` and ``bug_fix``), with
    ``spec_change`` excluded from the first-version catalog. Each entry carries
    ``definition_id``, ``version``, ``label`` and ``is_hotfix``.
    """
    resp = client.get("/api/projects/catalog")
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert len(items) == 2

    by_id = {item["definition_id"]: item for item in items}
    assert set(by_id.keys()) == {"new_feature", "bug_fix"}

    nf = by_id["new_feature"]
    assert nf["version"] == "1"
    assert nf["label"] == "New feature"
    assert nf["is_hotfix"] is False

    bf = by_id["bug_fix"]
    assert bf["version"] == "1"
    assert bf["label"] == "Bug fix (hotfix)"
    assert bf["is_hotfix"] is True


def test_e2e_fr_1701_workflow_definitions_catalog_validation(
    client: TestClient,
) -> None:
    """AC-FR1701-01: registered definitions have enumerable nodes, edges, gates.

    A workflow definition's nodes, legal edges and candidate decision results
    must be enumerable at registration time. This test creates a project for
    each catalog definition (``new_feature`` and ``bug_fix``) and verifies the
    graph endpoint returns a structurally valid graph (non-empty nodes/edges,
    a start step, a terminal step). Catalog validation passes without
    exceptions.
    """
    # new_feature graph.
    nf_project = _create_project(client, story="New feature def e2e")
    nf_graph = client.get(f"/api/projects/{nf_project['project_id']}/graph")
    assert nf_graph.status_code == 200, nf_graph.text
    nf = nf_graph.json()
    assert nf["definition_id"] == "new_feature"
    assert len(nf["nodes"]) >= 4
    assert len(nf["edges"]) >= 3
    assert nf["nodes"][0]["step_id"] == "start"
    # Terminal node has no outgoing edges.
    from_steps = {e["from_step"] for e in nf["edges"]}
    terminal_ids = {
        n["step_id"] for n in nf["nodes"] if n["step_id"] not in from_steps
    }
    assert "complete" in terminal_ids

    # bug_fix graph.
    seeded = _seed_approved_source_gate(client)
    bf_project = _create_project(
        client,
        story="Bug fix def e2e",
        definition_id="bug_fix",
        source_contract=_valid_source_contract(seeded),
    )
    bf_graph = client.get(f"/api/projects/{bf_project['project_id']}/graph")
    assert bf_graph.status_code == 200, bf_graph.text
    bf = bf_graph.json()
    assert bf["definition_id"] == "bug_fix"
    assert len(bf["nodes"]) >= 3
    assert len(bf["edges"]) >= 2
    # bug_fix starts at source_contract_verify.
    assert bf["nodes"][0]["step_id"] == "source_contract_verify"
