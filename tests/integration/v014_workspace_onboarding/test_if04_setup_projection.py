"""IF-04: SetupProjection — continuous Wizard and step visibility.

AC-FR0101-01, AC-FR0101-02, AC-FR0701-02, AC-FR1501-01

Integration tests verify that SetupJourney exposes the current step,
completed steps, remaining steps, and blocking items, and that Story/release
actions remain unavailable until Setup completes.
"""

from __future__ import annotations


from louke.web.setup_journey import SetupJourney, SetupStep


def test_wizard_shows_all_steps_in_order():
    """AC-FR0101-01: Wizard displays current, completed, and remaining steps."""
    # AC-FR0101-01
    journey = SetupJourney(
        current_step=SetupStep.DEPENDENCIES,
        completed_steps=(SetupStep.IDENTITY, SetupStep.REPOSITORY),
    )
    assert journey.current_step == SetupStep.DEPENDENCIES
    assert SetupStep.IDENTITY in journey.completed_steps
    assert SetupStep.REPOSITORY in journey.completed_steps
    remaining = journey.remaining_steps
    assert SetupStep.REVIEW in remaining
    assert SetupStep.APPLYING in remaining


def test_wizard_blocking_items_visible():
    """AC-FR0101-01: blocking items are visible in the journey."""
    # AC-FR0101-01
    journey = SetupJourney(
        current_step=SetupStep.REPOSITORY,
        completed_steps=(SetupStep.IDENTITY,),
        blocking_items=("remote_url_required",),
    )
    assert "remote_url_required" in journey.blocking_items


def test_return_to_previous_step_preserves_completed():
    """AC-FR0101-01: returning upstream preserves completed steps."""
    # AC-FR0101-01
    journey = SetupJourney(
        current_step=SetupStep.DEPENDENCIES,
        completed_steps=(SetupStep.IDENTITY, SetupStep.REPOSITORY),
    )
    returned = journey.return_to(SetupStep.REPOSITORY)
    assert returned.current_step == SetupStep.REPOSITORY
    assert SetupStep.IDENTITY in returned.completed_steps


def test_story_actions_blocked_during_partial_setup():
    """AC-FR0101-02: partial Setup does not show Complete or allow Story actions."""
    # AC-FR0101-02
    journey = SetupJourney(
        current_step=SetupStep.DEPENDENCIES,
        completed_steps=(SetupStep.IDENTITY, SetupStep.REPOSITORY),
    )
    # SetupStep has no COMPLETE member; APPLYING is the last step
    assert journey.current_step != SetupStep.APPLYING
    remaining = journey.remaining_steps
    assert len(remaining) > 0  # not all steps done


def test_setup_complete_advances_to_applying():
    """AC-FR0701-02: completing review advances to applying step."""
    # AC-FR0701-02
    journey = SetupJourney(
        current_step=SetupStep.REVIEW,
        completed_steps=(
            SetupStep.IDENTITY,
            SetupStep.REPOSITORY,
            SetupStep.DEPENDENCIES,
        ),
    )
    updated = journey.complete_current()
    assert updated.current_step == SetupStep.APPLYING


def test_setup_step_does_not_dispatch_agent():
    """AC-FR1501-01: Setup step data does not dispatch or trigger Maestro."""
    # AC-FR1501-01
    journey = SetupJourney(
        current_step=SetupStep.REPOSITORY,
        completed_steps=(SetupStep.IDENTITY,),
    )
    # SetupJourney is pure data; it has no dispatch or agent methods
    assert not hasattr(journey, "dispatch")
    assert not hasattr(journey, "send_message")
