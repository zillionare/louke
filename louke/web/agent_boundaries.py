"""Specialist Agent eligibility and historical-session boundaries."""

from __future__ import annotations


_SPECIALIST_AGENTS = frozenset({"Scribe", "Sage", "Archer", "Devon"})


def can_create_agent(agent: str) -> bool:
    """Return whether Runtime may create a new specialist Agent session."""
    return agent in _SPECIALIST_AGENTS


def session_kind(agent: str, *, historical: bool) -> tuple[str, bool]:
    """Return public session kind and read-only status."""
    if agent == "Maestro" or historical:
        return "historical_maestro", True
    return "specialist_agent", not can_create_agent(agent)
