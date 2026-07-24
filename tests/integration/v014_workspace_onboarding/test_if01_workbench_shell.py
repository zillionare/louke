"""IF-01: Workbench shell and stable navigation.

AC-FR0001-01, AC-FR1201-01, AC-FR1301-01

Integration tests verify that the Workbench shell URL builder and entry
resolver cooperate to produce stable, same-origin navigation URLs that
preserve workspace/project/story/run identity across activities.
"""

from __future__ import annotations

from louke.web.entry_resolver import EntryFacts, resolve_entry
from louke.web.workbench_navigation import build_context_url


def test_entry_resolver_returns_setup_when_incomplete():
    """AC-FR0001-01: blank workspace with incomplete Setup resolves to Setup."""
    # AC-FR0001-01
    facts = EntryFacts(setup_complete=False, setup_step="repository")
    result = resolve_entry(facts)
    assert result.destination == "setup"
    assert result.url.startswith("/setup")
    assert result.reason == "setup_incomplete"


def test_entry_resolver_returns_current_work_when_active():
    """AC-FR0001-01: active work takes priority over released history."""
    # AC-FR0001-01
    facts = EntryFacts(
        setup_complete=True,
        active_work_url="/projects/proj_1/stories/story_1",
        released_url="/projects/proj_1/runs/run_1",
    )
    result = resolve_entry(facts)
    assert result.destination == "current_work"
    assert result.url == "/projects/proj_1/stories/story_1"
    assert result.reason == "active_work"


def test_entry_resolver_returns_released_when_no_active_work():
    """AC-FR0001-01: no active work but released item resolves to Released."""
    # AC-FR0001-01
    facts = EntryFacts(
        setup_complete=True,
        active_work_url=None,
        released_url="/projects/proj_1/runs/run_1",
    )
    result = resolve_entry(facts)
    assert result.destination == "released"
    assert result.url == "/projects/proj_1/runs/run_1"
    assert result.reason == "latest_released"


def test_entry_resolver_returns_ready_empty_when_nothing_pending():
    """AC-FR0001-01: Setup complete with no work resolves to Ready/Empty."""
    # AC-FR0001-01
    facts = EntryFacts(setup_complete=True)
    result = resolve_entry(facts)
    assert result.destination == "ready_empty"
    assert result.reason == "no_current_work"


def test_active_work_takes_priority_over_released():
    """AC-FR0001-01: new active work supersedes released history as main view."""
    # AC-FR0001-01
    facts = EntryFacts(
        setup_complete=True,
        active_work_url="/projects/proj_2/stories/story_2",
        released_url="/projects/proj_1/runs/run_1",
    )
    result = resolve_entry(facts)
    assert result.destination == "current_work"
    assert "proj_2" in result.url


def test_navigation_url_preserves_project_identity():
    """AC-FR1201-01: build_context_url preserves project_id across activities."""
    # AC-FR1201-01
    url = build_context_url("proj_1")
    assert url == "/projects/proj_1"


def test_navigation_url_preserves_story_and_run_identity():
    """AC-FR1201-01: build_context_url preserves story_id and run_id deep links."""
    # AC-FR1201-01
    url = build_context_url("proj_1", story_id="story_1", run_id="run_1")
    assert "proj_1" in url
    assert "story_1" in url
    assert "run_1" in url


def test_navigation_url_encodes_identifiers():
    """AC-FR1201-01: identifiers with special characters are URL-encoded."""
    # AC-FR1201-01
    url = build_context_url("proj with space")
    assert " " not in url
