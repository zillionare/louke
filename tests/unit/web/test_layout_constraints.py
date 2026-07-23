"""Unit contracts for accessible Guide layout constraints."""

from louke.web.layout_constraints import layout_for_viewport


def test_supported_zoom_keeps_main_content_and_guide_reachable() -> None:
    """AC-NFR0301-01: high zoom temporarily collapses Guide safely."""
    layout = layout_for_viewport(
        width=1280, height=720, zoom=2.0, guide_collapsed=False
    )

    assert layout.guide_collapsed
    assert layout.main_content_reachable
    assert layout.guide_restore_reachable


def test_unsupported_small_viewport_is_explicitly_degraded() -> None:
    """AC-NFR0301-02: unsupported dimensions do not claim full layout support."""
    layout = layout_for_viewport(width=800, height=600, zoom=1.0, guide_collapsed=False)

    assert layout.degraded
    assert layout.main_content_reachable
