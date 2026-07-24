"""IF-03: EntryProjection resolver priority.

AC-FR0001-01, AC-FR0001-02, AC-FR0901-01

Integration tests verify the priority ordering: Setup > current work >
released > ready/empty, and that GET entry has no side effects.
"""

from __future__ import annotations


from louke.web.entry_resolver import EntryFacts, resolve_entry


def test_setup_incomplete_highest_priority():
    """AC-FR0001-01: Setup incomplete overrides active work and released."""
    # AC-FR0001-01
    facts = EntryFacts(
        setup_complete=False,
        setup_step="repository",
        active_work_url="/projects/p1/stories/s1",
        released_url="/projects/p1/runs/r1",
    )
    result = resolve_entry(facts)
    assert result.destination == "setup"


def test_active_work_over_released():
    """AC-FR0001-01: active work takes priority over released history."""
    # AC-FR0001-01
    facts = EntryFacts(
        setup_complete=True,
        active_work_url="/projects/p2/stories/s2",
        released_url="/projects/p1/runs/r1",
    )
    result = resolve_entry(facts)
    assert result.destination == "current_work"


def test_released_when_no_active_work():
    """AC-FR0001-01: released item is shown when no active work exists."""
    # AC-FR0001-01
    facts = EntryFacts(
        setup_complete=True,
        released_url="/projects/p1/runs/r1",
    )
    result = resolve_entry(facts)
    assert result.destination == "released"


def test_ready_empty_when_setup_complete_and_no_work():
    """AC-FR0001-01: ready/empty when Setup complete and nothing pending."""
    # AC-FR0001-01
    facts = EntryFacts(setup_complete=True)
    result = resolve_entry(facts)
    assert result.destination == "ready_empty"


def test_resolver_is_pure_no_side_effects():
    """AC-FR0001-02: calling resolve_entry repeatedly produces identical results."""
    # AC-FR0001-02
    facts = EntryFacts(setup_complete=True, active_work_url="/projects/p1/stories/s1")
    r1 = resolve_entry(facts)
    r2 = resolve_entry(facts)
    r3 = resolve_entry(facts)
    assert r1 == r2 == r3


def test_resolver_url_is_same_origin():
    """AC-FR0901-01: entry URL is same-origin (starts with /)."""
    # AC-FR0901-01
    facts = EntryFacts(setup_complete=True)
    result = resolve_entry(facts)
    assert result.url.startswith("/")
    assert "://" not in result.url
