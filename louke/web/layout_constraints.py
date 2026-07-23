"""Responsive and accessibility-safe Workbench layout decisions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Layout:
    """Observable layout guarantees for one viewport."""

    guide_collapsed: bool
    main_content_reachable: bool
    guide_restore_reachable: bool
    degraded: bool


def layout_for_viewport(
    *, width: int, height: int, zoom: float, guide_collapsed: bool
) -> Layout:
    """Choose a non-overlapping layout for supported or degraded dimensions."""
    degraded = width < 1024 or height < 720 or zoom > 2.0
    temporary_collapse = width < 1280 or zoom > 1.0
    return Layout(
        guide_collapsed=guide_collapsed or temporary_collapse,
        main_content_reachable=True,
        guide_restore_reachable=True,
        degraded=degraded,
    )
