"""Unit contracts for Workbench entry resolution (AC-FR0001-01, AC-FR0401-01).

AC-FR0001-01, AC-FR0001-02, AC-FR0401-01

The v0.14-004 entry resolver removes the ``released`` landing point.
After Setup completes, the user lands on Projects (active or empty).
"""

from __future__ import annotations


from louke.web.entry_resolver import EntryFacts, resolve_entry


def test_resolver_prioritizes_setup_before_anything() -> None:
    """AC-FR0001-01: incomplete Setup is the first destination."""
    resolution = resolve_entry(
        EntryFacts(
            setup_complete=False,
            active_project_url="/workbench?activity=projects&project=prj_1",
        )
    )
    assert resolution.destination == "setup"
    assert resolution.url == "/setup"
    assert resolution.reason == "setup_incomplete"


def test_resolver_returns_active_project_when_setup_complete() -> None:
    """AC-FR0401-01: setup-complete with active project -> Project Status."""
    resolution = resolve_entry(
        EntryFacts(
            setup_complete=True,
            active_project_url="/workbench?activity=projects&project=prj_1",
        )
    )
    assert resolution.destination == "active_project"
    assert resolution.url == "/workbench?activity=projects&project=prj_1"
    assert resolution.reason == "active_project"


def test_resolver_returns_projects_empty_when_no_active_work() -> None:
    """AC-FR0401-01: setup-complete with no active project -> Projects empty."""
    resolution = resolve_entry(EntryFacts(setup_complete=True, active_project_url=None))
    assert resolution.destination == "projects"
    assert resolution.url == "/workbench?activity=projects"
    assert resolution.reason == "no_active_project"


def test_resolver_never_returns_released() -> None:
    """AC-FR0401-01: the ``released`` destination is retired."""
    resolution = resolve_entry(EntryFacts(setup_complete=True))
    assert resolution.destination != "released"


def test_incomplete_setup_always_redirects_to_setup() -> None:
    """AC-FR0001-02: incomplete Setup always redirects to ``/setup``."""
    resolution = resolve_entry(EntryFacts(setup_complete=False))
    assert resolution.destination == "setup"
    assert resolution.url == "/setup"
