"""IF-13: Accessibility and responsive interaction.

AC-NFR0301-01, AC-NFR0301-02

Integration tests verify that layout constraints enforce main content
reachability, Guide restore visibility, and that collapsed Guide does not
block navigation.
"""

from __future__ import annotations

from louke.web.layout_constraints import layout_for_viewport


def test_supported_viewport_keeps_main_content_reachable():
    """AC-NFR0301-01: 1024x768 @ 100% keeps main content reachable."""
    # AC-NFR0301-01
    layout = layout_for_viewport(
        width=1024, height=768, zoom=1.0, guide_collapsed=False
    )
    assert layout.main_content_reachable is True
    assert layout.guide_restore_reachable is True


def test_200_percent_zoom_can_collapse_guide():
    """AC-NFR0301-01: 1280x720 @ 200% allows Guide collapse for main content."""
    # AC-NFR0301-01
    layout = layout_for_viewport(width=1280, height=720, zoom=2.0, guide_collapsed=True)
    assert layout.main_content_reachable is True


def test_200_percent_zoom_without_collapse_degrades():
    """AC-NFR0301-01: 1280x720 @ 200% without collapse may degrade."""
    # AC-NFR0301-01
    layout = layout_for_viewport(
        width=1280, height=720, zoom=2.0, guide_collapsed=False
    )
    # The layout should either degrade or still be reachable
    assert layout.degraded is True or layout.main_content_reachable is True


def test_collapsed_guide_keeps_restore_reachable():
    """AC-NFR0301-01: collapsed Guide keeps restore control reachable."""
    # AC-NFR0301-01
    layout = layout_for_viewport(width=1024, height=768, zoom=1.0, guide_collapsed=True)
    assert layout.guide_restore_reachable is True


def test_layout_does_not_depend_on_animation():
    """AC-NFR0301-02: layout result is a static data class, not animation-dependent."""
    # AC-NFR0301-02
    l1 = layout_for_viewport(width=1024, height=768, zoom=1.0, guide_collapsed=False)
    l2 = layout_for_viewport(width=1024, height=768, zoom=1.0, guide_collapsed=False)
    assert l1 == l2  # deterministic, no animation state
