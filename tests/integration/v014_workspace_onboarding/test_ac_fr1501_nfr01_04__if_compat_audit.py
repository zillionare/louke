"""IF-COMPAT-01 / IF-AUDIT-01 — Compatibility router + structured audit evidence.

AC-FR1501-01, AC-FR1501-02, AC-NFR0101-01, AC-NFR0101-02, AC-NFR0401-01, AC-NFR0401-02

Cross-module:
* Compatibility Router (Compatibility Router × Setup Gate × Project
  Context × Workbench Presentation × Document Surface × Runtime
  Projection).
* Audit evidence (Setup Application × Environment Gate × Release
  Entry × Foundation/Scribe × Return Application × Fact Stores).

Tests drive the real ``louke.web.compatibility_router`` and the real
``louke.runtime.audit_observability`` modules.
"""

from __future__ import annotations

import inspect

import pytest

from louke.runtime.audit_observability import (
    AuditEvent,
    AuditStore,
    EvidenceStatus,
    record_event,
)
from louke.web.compatibility_router import (
    ENTRY_CANONICAL_PROJECTS,
    resolve,
)


# ---------------------------------------------------------------------------
# IF-COMPAT-01: compatibility router resolves legacy deep links
# ---------------------------------------------------------------------------


def test_compat_router_canonical_projects_constant() -> None:
    """AC-FR1501-01: ``ENTRY_CANONICAL_PROJECTS`` is the locked canonical URL."""
    # AC-FR1501-01
    assert ENTRY_CANONICAL_PROJECTS == "/workbench?activity=projects"


@pytest.mark.parametrize(
    "path",
    [
        "/projects",
        "/projects/prj_x",
        "/projects/ws_1/prj_x/gates",
        "/runs/run_1",
        "/runs/legacy_unknown",
        "/projects/ws_1/requirements/story",
    ],
)
def test_compat_router_resolves_legacy_routes(path: str) -> None:
    """AC-FR1501-02: legacy deep links resolve to the canonical Projects activity."""
    # AC-FR1501-02
    assert resolve(path) == ENTRY_CANONICAL_PROJECTS


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/login",
        "/unknown",
        "/foo/bar/baz",
    ],
)
def test_compat_router_returns_none_for_non_legacy(path: str) -> None:
    """AC-FR1501-02: non-legacy paths return ``None`` (no mapping)."""
    # AC-FR1501-02
    assert resolve(path) is None


def test_compat_router_does_not_create_second_writable_project() -> None:
    """AC-FR1501-01: every legacy path lands on the same read-only canonical URL."""
    # AC-FR1501-01
    targets = {
        resolve(p)
        for p in ("/projects", "/projects/prj_a", "/projects/prj_b", "/runs/run_1")
    }
    # Only one canonical target — never a second writable surface.
    assert targets == {ENTRY_CANONICAL_PROJECTS}


# ---------------------------------------------------------------------------
# IF-AUDIT-01: structured operation/audit evidence
# ---------------------------------------------------------------------------


@pytest.fixture
def audit_store() -> AuditStore:
    """A real AuditStore backed by an in-memory connection."""
    return AuditStore()


def test_audit_event_carries_locked_fields(audit_store) -> None:
    """AC-NFR0101-01: ``record_event`` writes every contract field."""
    # AC-NFR0101-01
    event = record_event(
        audit_store,
        run_id="run_1",
        kind="environment_check_started",
        actor="prin_alpha",
        attempt_no=1,
        input_identities=("ws_1",),
        output_identity="chk_1",
        state=EvidenceStatus.UNKNOWN.value,
    )
    assert isinstance(event, AuditEvent)
    assert event.run_id == "run_1"
    assert event.kind == "environment_check_started"
    assert event.actor == "prin_alpha"
    assert event.attempt_no == 1
    assert event.output_identity == "chk_1"
    assert event.state == EvidenceStatus.UNKNOWN
    assert event.event_id
    assert event.observed_at


def test_audit_event_state_uses_evidence_status_enum() -> None:
    """AC-NFR0101-01: ``EvidenceStatus`` exposes a closed status set."""
    # AC-NFR0101-01
    values = {status.value for status in EvidenceStatus}
    # The set must include both a passing and a non-passing status
    # so the runtime can keep an honest ``uncertain``-class state
    # until readback confirms.
    assert "PASS" in values
    assert "FAIL" in values
    assert len(values) >= 3


def test_audit_persists_event_to_store(audit_store) -> None:
    """AC-NFR0101-01: events survive a round-trip through the store."""
    # AC-NFR0101-01
    event = record_event(
        audit_store,
        run_id="run_1",
        kind="opencode_probe_finished",
        actor="prin_alpha",
        attempt_no=2,
        input_identities=("minimax/m2",),
        output_identity="chk_2",
        state=EvidenceStatus.PASS.value,
    )
    # ``AuditStore.query`` is the documented read surface; using it
    # keeps the round-trip independent of any private repr.
    rows = audit_store.query(run_id="run_1")
    assert any(row.event_id == event.event_id for row in rows)


def test_audit_event_does_not_accept_secret_kwarg(audit_store) -> None:
    """AC-NFR0101-01: ``record_event`` accepts no ``credential``/``token`` field.

    The contract forbids runtime evidence from carrying secret
    fields; the public signature is the surface that enforces this.
    """
    # AC-NFR0101-01
    sig = inspect.signature(record_event)
    forbidden = {
        "credential",
        "password",
        "session_secret",
        "csrf_token",
        "token",
        "userinfo",
        "authorization",
    }
    leaked = forbidden & set(sig.parameters)
    assert not leaked, f"record_event signature leaks secret fields: {leaked!r}"


# ---------------------------------------------------------------------------
# Activation: real artifact surface
# ---------------------------------------------------------------------------


def test_real_compatibility_router_surface() -> None:
    """AC-FR1501-01: real artifact exposes the canonical entry."""
    # AC-FR1501-01
    import louke.web.compatibility_router as mod

    assert mod.ENTRY_CANONICAL_PROJECTS == "/workbench?activity=projects"
    assert callable(mod.resolve)


def test_real_audit_observability_surface() -> None:
    """AC-NFR0101-01: real artifact exposes the audit contract."""
    # AC-NFR0101-01
    import louke.runtime.audit_observability as mod

    # Either ``emit`` (v0.14-004 canonical) or ``record_event``
    # (legacy v0.13.x) is acceptable. Both surface ``AuditEvent``.
    surface = "emit" if hasattr(mod, "emit") else "record_event"
    assert callable(getattr(mod, surface, None))
    # AC-NFR0101-01: real artifact exposes the AuditEvent evidence envelope
    assert mod.AuditEvent is not None
    # AC-NFR0101-01: real artifact exposes the closed EvidenceStatus enum
    assert mod.EvidenceStatus is not None
