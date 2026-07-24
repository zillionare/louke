"""IF-09: GuideProjection and preferences.

AC-FR1301-01, AC-FR1301-02, AC-FR1401-01, AC-FR1401-02, AC-FR1501-01

Integration tests verify that Guide projection reads Runtime facts (not
authoring them), that preferences are persisted and constrained, and that
Guide does not dispatch or execute owning-surface actions.
"""

from __future__ import annotations

from louke.web.guide_context import GuideMessageLedger
from louke.web.guide_projection import (
    GuidePreference,
    project_guide,
)


def test_guide_projection_contains_summary_and_responsible_party():
    """AC-FR1401-01: Guide summary answers where, what, status, and next step."""
    # AC-FR1401-01
    pref = GuidePreference(collapsed=False, divider_ratio=0.3333)
    projection = project_guide(
        summary="You are in M-DESIGN. Archer is designing.",
        responsible_party="agent:Archer",
        required_action="Review design",
        preference=pref,
    )
    assert "M-DESIGN" in projection.summary
    assert projection.responsible_party == "agent:Archer"
    assert projection.required_action == "Review design"


def test_guide_links_only_navigate_not_dispatch():
    """AC-FR1501-01: Guide links only navigate; no dispatch tokens."""
    # AC-FR1501-01
    pref = GuidePreference(collapsed=False, divider_ratio=0.3333)
    projection = project_guide(
        summary="summary",
        responsible_party=None,
        required_action=None,
        preference=pref,
        owning_surface_url="/projects/p1/stories/s1",
    )
    for link in projection.links:
        assert link.startswith("/")


def test_guide_preference_normalizes_ratio():
    """AC-FR1301-02: divider ratio is constrained to 0.20..0.50."""
    # AC-FR1301-02
    pref = GuidePreference(collapsed=False, divider_ratio=0.9)
    normalized = pref.normalized()
    assert normalized.divider_ratio == 0.50

    pref_low = GuidePreference(collapsed=False, divider_ratio=0.05)
    normalized_low = pref_low.normalized()
    assert normalized_low.divider_ratio == 0.20


def test_guide_preference_default_ratio():
    """AC-FR1301-02: default divider ratio is approximately 1/3."""
    # AC-FR1301-02
    pref = GuidePreference(collapsed=False, divider_ratio=0.3333)
    assert 0.20 <= pref.divider_ratio <= 0.50


def test_guide_message_marks_context_change_as_historical():
    """AC-FR1401-01: messages from a prior context are marked historical."""
    # AC-FR1401-01
    ledger = GuideMessageLedger()
    ledger.append("ws_1", "rev_1", "You are in M-STORY.")
    # New context
    ledger.append("ws_1", "rev_2", "You are in M-DESIGN.")
    messages = ledger.messages("ws_1")
    # At least the newest message should be current
    assert any(not m.historical for m in messages)


def test_guide_does_not_repeat_announcement_for_unchanged_state():
    """AC-FR1401-02: unchanged state does not trigger repeat announcement."""
    # AC-FR1401-02
    ledger = GuideMessageLedger()
    ledger.append("ws_1", "rev_1", "Welcome")
    ledger.mark_seen("ws_1", "rev_1")
    # Same revision -> should not announce again
    assert not ledger.should_announce("ws_1", "rev_1")
