"""Shared v0.12 workflow catalog and per-app run-store singletons.

Each v0.12 HTTP sub-app is self-contained and operates against an in-memory
``WorkflowRunStore`` (``db_path=None``) by default, with a registered catalog
containing minimal ``new_feature`` and ``bug_fix`` definitions.

The store is created lazily on the first request rather than at app-build
time, because Starlette's ASGI server (and the test ``TestClient``) dispatches
requests in a portal thread distinct from the thread that built the app. The
underlying ``sqlite3`` connection in :class:`WorkflowRunStore` is bound to the
thread that created it, so the store must be created inside the request
lifecycle. :func:`get_or_create_store` is the single accessor every sub-app
handler uses to obtain the per-app singleton store.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from louke.runtime.catalog import DefinitionRegistry, Edge, Step, WorkflowDefinition
from louke.runtime.store import WorkflowRunStore

if TYPE_CHECKING:
    from starlette.applications import Starlette

#: Attribute on ``app.state`` holding the lazily-created ``WorkflowRunStore``.
_STORE_ATTR: str = "v12_run_store"

#: Default models offered to the v0.12 binding sub-app (FR-1301 placeholder).
DEFAULT_MODELS: dict[str, str] = {
    "devon": "claude-sonnet",
    "maestro": "claude-opus",
    "sage": "claude-haiku",
}

#: Models that may be selected as overrides.
AVAILABLE_MODELS: frozenset[str] = frozenset(
    {"claude-sonnet", "claude-opus", "claude-haiku", "gpt-4o"}
)


def _new_feature_definition() -> WorkflowDefinition:
    """Return the minimal ``new_feature`` workflow definition.

    The graph is: ``start`` (program) -> ``requirements_approval`` (human_gate)
    -> ``design`` (program) -> ``m_lock`` (human_gate) -> ``implementation``
    (semantic_task) -> ``complete`` (program, terminal).
    """
    start = Step(
        step_id="start",
        kind="program",
        transitions=(Edge("e1", "start", "requirements_approval", "done"),),
    )
    req = Step(
        step_id="requirements_approval",
        kind="human_gate",
        transitions=(Edge("e2", "requirements_approval", "design", "approved"),),
    )
    design = Step(
        step_id="design",
        kind="program",
        transitions=(Edge("e3", "design", "m_lock", "done"),),
    )
    m_lock = Step(
        step_id="m_lock",
        kind="human_gate",
        transitions=(Edge("e4", "m_lock", "implementation", "approved"),),
    )
    implementation = Step(
        step_id="implementation",
        kind="semantic_task",
        capability="code_generation",
        transitions=(Edge("e5", "implementation", "complete", "done"),),
    )
    complete = Step(step_id="complete", kind="program")
    return WorkflowDefinition(
        definition_id="new_feature",
        version="1",
        start_step="start",
        steps=(start, req, design, m_lock, implementation, complete),
    )


def _bug_fix_definition() -> WorkflowDefinition:
    """Return the minimal ``bug_fix`` workflow definition.

    The graph is: ``source_contract_verify`` (program) -> ``reproduce``
    (program) -> ``fix`` (semantic_task) -> ``complete`` (program, terminal).
    """
    verify = Step(
        step_id="source_contract_verify",
        kind="program",
        transitions=(Edge("e3", "source_contract_verify", "reproduce", "verified"),),
    )
    reproduce = Step(
        step_id="reproduce",
        kind="program",
        transitions=(Edge("e6", "reproduce", "fix", "done"),),
    )
    fix = Step(
        step_id="fix",
        kind="semantic_task",
        capability="code_generation",
        transitions=(Edge("e7", "fix", "complete", "done"),),
    )
    complete = Step(step_id="complete", kind="program")
    return WorkflowDefinition(
        definition_id="bug_fix",
        version="1",
        start_step="source_contract_verify",
        steps=(verify, reproduce, fix, complete),
    )


def build_catalog() -> DefinitionRegistry:
    """Return a ``DefinitionRegistry`` populated with v0.12 definitions."""
    registry = DefinitionRegistry()
    registry.register(_new_feature_definition())
    registry.register(_bug_fix_definition())
    return registry


def build_run_store() -> WorkflowRunStore:
    """Return an in-memory ``WorkflowRunStore`` with the v0.12 catalog bound.

    The store uses ``db_path=None`` so each call returns an isolated, in-memory
    SQLite database. Callers that need the store to persist across requests
    should use :func:`get_or_create_store` instead.
    """
    return WorkflowRunStore(catalog=build_catalog())


def get_or_create_store(app: "Starlette") -> WorkflowRunStore:
    """Return the per-app singleton ``WorkflowRunStore``, creating it lazily.

    The store is created on first call (inside the request thread) and cached
    on ``app.state.v12_run_store`` so subsequent requests reuse it. This is
    required because the ``sqlite3`` connection is thread-bound and Starlette
    dispatches requests in a portal thread distinct from the app-build thread.

    Args:
        app: The Starlette sub-app whose ``state`` caches the store.

    Returns:
        The cached or newly-created ``WorkflowRunStore``.
    """
    store = getattr(app.state, _STORE_ATTR, None)
    if store is None:
        store = build_run_store()
        setattr(app.state, _STORE_ATTR, store)
    return store
