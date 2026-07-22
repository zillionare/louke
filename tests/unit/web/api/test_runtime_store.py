"""Unit contracts for the shared Runtime store app-state seam."""

from __future__ import annotations

from types import SimpleNamespace

from louke.web.api._runtime_store import get_or_create_store


def test_legacy_injected_store_is_promoted_to_canonical_identity() -> None:
    """Legacy test and host injection remains usable after the canonical rename."""
    legacy_store = object()
    app = SimpleNamespace(state=SimpleNamespace(v12_run_store=legacy_store))

    assert get_or_create_store(app) is legacy_store
    assert app.state.runtime_run_store is legacy_store


def test_canonical_store_wins_and_repairs_legacy_alias() -> None:
    """The canonical identity is authoritative when both aliases are present."""
    canonical_store = object()
    legacy_store = object()
    app = SimpleNamespace(
        state=SimpleNamespace(
            runtime_run_store=canonical_store,
            v12_run_store=legacy_store,
        )
    )

    assert get_or_create_store(app) is canonical_store
    assert app.state.v12_run_store is canonical_store
