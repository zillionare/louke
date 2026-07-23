"""Unit contracts for specialist Agent and retired Maestro boundaries."""

from louke.web.agent_boundaries import can_create_agent, session_kind


def test_guide_and_maestro_cannot_be_created_as_specialist_agents() -> None:
    """AC-FR1501-01: Guide/Maestro never become dispatch authorities."""
    assert can_create_agent("Scribe")
    assert can_create_agent("Devon")
    assert not can_create_agent("Guide")
    assert not can_create_agent("Maestro")


def test_historical_maestro_is_read_only() -> None:
    """AC-FR1501-02: historical Maestro sessions are explicit read-only history."""
    assert session_kind("Maestro", historical=True) == ("historical_maestro", True)
    assert session_kind("Archer", historical=False) == ("specialist_agent", False)
