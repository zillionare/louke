"""Canonical, read-only resolution of the authenticated Workbench entry."""

from __future__ import annotations

from dataclasses import dataclass


class EntryResolutionError(ValueError):
    """Raised when persisted entry facts cannot identify a safe destination."""


@dataclass(frozen=True)
class EntryFacts:
    """Facts needed to select one authenticated Workbench destination.

    Args:
        setup_complete: Whether the persisted Setup Manifest is valid and complete.
        setup_step: Current recoverable Setup step when Setup is incomplete.
        active_work_url: Canonical deep link for current Runtime work, if any.
        released_url: Canonical deep link for the most recent released work, if any.
    """

    setup_complete: bool
    setup_step: str | None = None
    active_work_url: str | None = None
    released_url: str | None = None


@dataclass(frozen=True)
class EntryResolution:
    """The canonical authenticated Workbench destination.

    Args:
        destination: One of ``setup``, ``current_work``, ``released``, or
            ``ready_empty``.
        url: Same-origin URL for the destination.
        reason: Stable reason code explaining the selection.
    """

    destination: str
    url: str
    reason: str


def resolve_entry(facts: EntryFacts) -> EntryResolution:
    """Select the only safe authenticated Workbench destination.

    Args:
        facts: Current persisted Setup and Runtime facts.

    Returns:
        An :class:`EntryResolution` ordered as Setup, active work, released
        history, then Ready/Empty.

    Raises:
        EntryResolutionError: If incomplete Setup lacks a recoverable step.

    This function is read-only and does not mutate Setup, Runtime, or browser
    state.
    """
    if not facts.setup_complete:
        if not facts.setup_step:
            raise EntryResolutionError("incomplete setup has no recoverable setup step")
        return EntryResolution(
            destination="setup",
            url=f"/setup?step={facts.setup_step}",
            reason="setup_incomplete",
        )
    if facts.active_work_url:
        return EntryResolution(
            destination="current_work",
            url=facts.active_work_url,
            reason="active_work",
        )
    if facts.released_url:
        return EntryResolution(
            destination="released",
            url=facts.released_url,
            reason="latest_released",
        )
    return EntryResolution(
        destination="ready_empty",
        url="/projects",
        reason="no_current_work",
    )
