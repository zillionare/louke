"""Unit contracts for Guide preference and deterministic projection."""

from louke.web.guide_projection import GuidePreference, project_guide


def test_guide_preference_clamps_divider_and_preserves_canonical_action() -> None:
    """AC-FR1301-02: layout preference cannot alter Runtime action facts."""
    guide = project_guide(
        summary="You are reviewing the current Story.",
        responsible_party="Human",
        required_action="Review design",
        preference=GuidePreference(collapsed=False, divider_ratio=0.9),
    )

    assert guide.preference.divider_ratio == 0.50
    assert guide.required_action == "Review design"
    assert guide.links == ()


def test_guide_projection_can_navigate_but_has_no_dispatch_token() -> None:
    """AC-FR1401-01: Guide explains and links to owning surface only."""
    guide = project_guide(
        summary="Open the design review surface.",
        responsible_party="Archer",
        required_action="Review design",
        preference=GuidePreference(False, 0.3333),
        owning_surface_url="/projects/p1/stories/s1",
    )

    assert guide.links == ("/projects/p1/stories/s1",)
    assert not hasattr(guide, "dispatch_token")
