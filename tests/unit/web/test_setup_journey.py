"""Unit contracts for the continuous Setup journey (AC-FR0101-01)."""

from __future__ import annotations

from louke.web.setup_journey import SetupJourney, SetupStep


def test_setup_journey_keeps_verified_unaffected_steps_when_returning() -> None:
    """AC-FR0101-01: returning only invalidates downstream dependent results."""
    journey = SetupJourney.new()

    journey = journey.complete_current()
    journey = journey.complete_current()
    returned = journey.return_to(SetupStep.REPOSITORY)

    assert returned.current_step is SetupStep.REPOSITORY
    assert returned.completed_steps == (SetupStep.IDENTITY,)
    assert returned.remaining_steps == (
        SetupStep.REPOSITORY,
        SetupStep.DEPENDENCIES,
        SetupStep.REVIEW,
        SetupStep.APPLYING,
    )


def test_setup_journey_reports_current_completed_remaining_and_blockers() -> None:
    """AC-FR0101-01: one projection exposes progress and blocking state."""
    journey = SetupJourney.new().block("Repository remote is unreachable")

    assert journey.current_step is SetupStep.IDENTITY
    assert journey.completed_steps == ()
    assert journey.remaining_steps[0] is SetupStep.IDENTITY
    assert journey.blocking_items == ("Repository remote is unreachable",)
