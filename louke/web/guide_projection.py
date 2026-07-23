"""Deterministic Guide projection and user-owned layout preferences."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GuidePreference:
    """Persistable Guide layout controls."""

    collapsed: bool
    divider_ratio: float

    def normalized(self) -> "GuidePreference":
        """Return preference constrained to the supported layout range."""
        return GuidePreference(self.collapsed, min(0.50, max(0.20, self.divider_ratio)))


@dataclass(frozen=True)
class GuideProjection:
    """Non-authoritative explanation and navigation projection."""

    summary: str
    responsible_party: str | None
    required_action: str | None
    preference: GuidePreference
    links: tuple[str, ...]


def project_guide(
    *,
    summary: str,
    responsible_party: str | None,
    required_action: str | None,
    preference: GuidePreference,
    owning_surface_url: str | None = None,
) -> GuideProjection:
    """Build Guide text and owning-surface navigation without dispatch data."""
    links = (owning_surface_url,) if owning_surface_url else ()
    return GuideProjection(
        summary=summary,
        responsible_party=responsible_party,
        required_action=required_action,
        preference=preference.normalized(),
        links=links,
    )
