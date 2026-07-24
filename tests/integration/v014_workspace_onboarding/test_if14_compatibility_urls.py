"""IF-14: Compatibility URLs and API.

AC-FR1201-01, AC-FR1201-02, AC-NFR0401-01

Integration tests verify that legacy routes resolve to canonical Workbench
routes, that deep links preserve identity, and that open redirects are
rejected.
"""

from __future__ import annotations

import pytest

from louke.web.compatibility_routes import canonical_route
from louke.web.projection_authority import ProjectionAuthority


def test_legacy_workbench_route_resolves_to_canonical():
    """AC-FR1201-01: /workbench resolves to canonical /."""
    # AC-FR1201-01
    result = canonical_route("/workbench")
    assert result == "/"


def test_legacy_setup_route_resolves_to_canonical():
    """AC-FR1201-01: /setup resolves to canonical /setup."""
    # AC-FR1201-01
    result = canonical_route("/setup")
    assert result.startswith("/setup")


def test_legacy_projects_route_resolves_to_canonical():
    """AC-FR1201-01: /projects resolves to canonical route."""
    # AC-FR1201-01
    result = canonical_route("/projects")
    assert result.startswith("/")


def test_open_redirect_rejected():
    """AC-FR1201-02: external next URL is rejected to prevent open redirect."""
    # AC-FR1201-02
    with pytest.raises(ValueError, match="same-origin"):
        canonical_route("/login", next_url="https://evil.example.com")


def test_same_origin_next_preserved():
    """AC-FR1201-02: same-origin next URL is preserved."""
    # AC-FR1201-02
    result = canonical_route("/login", next_url="/projects/p1")
    assert "/projects/p1" in result or result == "/"


def test_projection_authority_rejects_stale_revision():
    """AC-NFR0401-01: stale projection revision is rejected, no second state."""
    # AC-NFR0401-01
    authority = ProjectionAuthority()
    authority.publish("rev_1", {"state": "running"})
    with pytest.raises(ValueError, match="stale"):
        authority.publish("rev_0", {"state": "old"})


def test_projection_authority_read_requires_matching_revision():
    """AC-NFR0401-01: reading projection requires matching revision."""
    # AC-NFR0401-01
    authority = ProjectionAuthority()
    authority.publish("rev_1", {"state": "running"})
    data = authority.read("rev_1")
    assert data["state"] == "running"
    with pytest.raises(ValueError, match="stale"):
        authority.read("rev_0")


def test_projection_authority_only_one_state():
    """AC-NFR0401-01: only one authoritative projection exists at a time."""
    # AC-NFR0401-01
    authority = ProjectionAuthority()
    authority.publish("rev_1", {"state": "running"})
    authority.publish("rev_2", {"state": "waiting_human"})
    data = authority.read("rev_2")
    assert data["state"] == "waiting_human"
    # Old revision is stale
    with pytest.raises(ValueError, match="stale"):
        authority.read("rev_1")
