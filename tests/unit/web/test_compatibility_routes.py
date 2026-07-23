"""Unit contracts for canonical compatibility route resolution."""

from __future__ import annotations

import pytest

from louke.web.compatibility_routes import canonical_route


def test_legacy_setup_route_maps_to_canonical_surface() -> None:
    """AC-NFR0401-01: legacy entry points resolve to one canonical route."""
    assert canonical_route("/workbench") == "/"
    assert canonical_route("/setup") == "/setup"
    assert canonical_route("/api/v14/releases/preview") == "/api/releases/preview"


def test_external_next_target_is_rejected() -> None:
    """AC-NFR0401-02: compatibility redirects cannot become open redirects."""
    with pytest.raises(ValueError, match="same-origin"):
        canonical_route("/setup", next_url="https://evil.example")
