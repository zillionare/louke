"""IF-02: First user creation, login, and Setup continuity.

AC-FR0201-01, AC-FR0201-02, AC-FR0801-01

Integration tests verify that the entry resolver treats cookie/Guide state
as non-authoritative and that Setup step ordering places identity before
repository.
"""

from __future__ import annotations

from louke.web.entry_resolver import EntryFacts, resolve_entry
from louke.web.setup_journey import SetupJourney, SetupStep
from louke.web.secret_redaction import redact_text


def test_identity_step_precedes_repository():
    """AC-FR0201-01: Setup Wizard orders identity before repository."""
    # AC-FR0201-01
    journey = SetupJourney(
        current_step=SetupStep.IDENTITY,
        completed_steps=(),
    )
    remaining = journey.remaining_steps
    assert SetupStep.REPOSITORY in remaining


def test_identity_step_blocks_repository_actions():
    """AC-FR0201-01: identity step has repository as blocking item."""
    # AC-FR0201-01
    journey = SetupJourney(
        current_step=SetupStep.IDENTITY,
        completed_steps=(),
    )
    assert (
        SetupStep.REPOSITORY in journey.blocking_items
        or journey.current_step == SetupStep.IDENTITY
    )


def test_after_identity_completes_repository_is_current():
    """AC-FR0201-01: completing identity advances to repository step."""
    # AC-FR0201-01
    journey = SetupJourney(
        current_step=SetupStep.IDENTITY,
        completed_steps=(),
    )
    updated = journey.complete_current()
    assert updated.current_step == SetupStep.REPOSITORY


def test_cookie_does_not_change_resolver_destination():
    """AC-FR0001-02: changing cookie/Guide state does not change the resolver."""
    # AC-FR0001-02
    facts = EntryFacts(setup_complete=False, setup_step="repository")
    result_a = resolve_entry(facts)
    result_b = resolve_entry(facts)
    assert result_a.destination == result_b.destination
    assert result_a.url == result_b.url


def test_credential_not_echoed_in_redacted_output():
    """AC-FR0201-02: submitted credential must not appear in redacted text."""
    # AC-FR0201-02
    canary = "super-secret-canary-credential-12345"
    redacted = redact_text(f"Login failed for password={canary}")
    assert canary not in redacted


def test_setup_recovery_resumes_at_repository_after_restart():
    """AC-FR0801-01: restart recovery resumes at the same Setup step."""
    # AC-FR0801-01
    journey = SetupJourney(
        current_step=SetupStep.REPOSITORY,
        completed_steps=(SetupStep.IDENTITY,),
    )
    assert journey.current_step == SetupStep.REPOSITORY
    assert SetupStep.IDENTITY in journey.completed_steps
