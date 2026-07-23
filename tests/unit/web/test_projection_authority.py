"""Unit contracts for one canonical projection revision."""

from __future__ import annotations

import pytest

from louke.web.projection_authority import ProjectionAuthority


def test_newer_runtime_projection_replaces_cached_surface_facts() -> None:
    """AC-NFR0201-01: clients cannot restore an older canonical revision."""
    authority = ProjectionAuthority()
    authority.publish("status-2", {"state": "current"})

    assert authority.read("status-2")["state"] == "current"
    with pytest.raises(ValueError, match="stale"):
        authority.publish("status-1", {"state": "ready"})
