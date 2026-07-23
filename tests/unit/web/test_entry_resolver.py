"""Unit contracts for Workbench entry resolution (AC-FR0001-01)."""

from __future__ import annotations

import pytest

from louke.web.entry_resolver import EntryFacts, EntryResolutionError, resolve_entry


def test_resolver_prioritizes_setup_before_active_or_released_work() -> None:
    """AC-FR0001-01: incomplete Setup is the first authenticated destination."""
    resolution = resolve_entry(
        EntryFacts(
            setup_complete=False,
            setup_step="repository",
            active_work_url="/projects/project-1/runs/run-1",
            released_url="/projects/project-1/stories/story-1",
        )
    )

    assert resolution.destination == "setup"
    assert resolution.url == "/setup?step=repository"
    assert resolution.reason == "setup_incomplete"


@pytest.mark.parametrize(
    ("facts", "destination", "url", "reason"),
    [
        (
            EntryFacts(
                setup_complete=True,
                active_work_url="/projects/project-1/runs/run-1",
                released_url="/projects/project-1/stories/story-1",
            ),
            "current_work",
            "/projects/project-1/runs/run-1",
            "active_work",
        ),
        (
            EntryFacts(
                setup_complete=True,
                released_url="/projects/project-1/stories/story-1",
            ),
            "released",
            "/projects/project-1/stories/story-1",
            "latest_released",
        ),
        (
            EntryFacts(setup_complete=True),
            "ready_empty",
            "/projects",
            "no_current_work",
        ),
    ],
)
def test_resolver_uses_canonical_authenticated_priority(
    facts: EntryFacts, destination: str, url: str, reason: str
) -> None:
    """AC-FR0001-01: active work wins over released history, then Ready/Empty."""
    resolution = resolve_entry(facts)

    assert (resolution.destination, resolution.url, resolution.reason) == (
        destination,
        url,
        reason,
    )


def test_resolver_fails_closed_when_incomplete_setup_has_no_step() -> None:
    """AC-FR0001-02: contradictory persisted facts do not select a destination."""
    with pytest.raises(EntryResolutionError, match="setup step"):
        resolve_entry(EntryFacts(setup_complete=False))
