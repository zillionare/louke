"""Canonical, read-only resolution of the authenticated Workbench entry.

AC-FR0001-01, AC-FR0401-01

The v0.14-004 resolver removes the ``released`` landing point. After
Setup completes, the user lands on Projects (active or empty). The
old ``setup_step`` parameter is gone; Setup incompleteness redirects
to ``/setup`` unconditionally.
"""

from __future__ import annotations

from dataclasses import dataclass


class EntryResolutionError(ValueError):
    """Raised when persisted entry facts cannot identify a safe destination."""


@dataclass(frozen=True)
class EntryFacts:
    """Facts needed to select one authenticated Workbench destination.

    Args:
        setup_complete: Whether the persisted Setup manifest is ``complete``.
        active_project_url: Canonical deep link for the active Project
            Status, or ``None`` when there is no active Project.
    """

    setup_complete: bool
    active_project_url: str | None = None


@dataclass(frozen=True)
class EntryResolution:
    """The canonical authenticated Workbench destination.

    Args:
        destination: One of ``setup``, ``active_project``, or ``projects``.
        url: Same-origin URL for the destination.
        reason: Stable reason code explaining the selection.
    """

    destination: str
    url: str
    reason: str


def resolve_entry(facts: EntryFacts) -> EntryResolution:
    """Select the only safe authenticated Workbench destination.

    Args:
        facts: Current persisted Setup and Project facts.

    Returns:
        An :class:`EntryResolution` ordered as Setup, active Project,
        then Projects (empty).

    Raises:
        EntryResolutionError: If incomplete Setup lacks a valid manifest.

    This function is read-only and does not mutate Setup, Runtime, or
    browser state.
    """
    if not facts.setup_complete:
        return EntryResolution(
            destination="setup",
            url="/setup",
            reason="setup_incomplete",
        )
    if facts.active_project_url:
        return EntryResolution(
            destination="active_project",
            url=facts.active_project_url,
            reason="active_project",
        )
    return EntryResolution(
        destination="projects",
        url="/workbench?activity=projects",
        reason="no_active_project",
    )
