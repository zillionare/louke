"""Unit contracts for explicit workspace/repository binding."""

from __future__ import annotations

from louke.web.workspace_binding import BindingCandidate, resolve_binding


def test_binding_requires_human_when_candidates_are_ambiguous() -> None:
    """AC-FR0401-01: multiple candidates never become an implicit binding."""
    result = resolve_binding(
        (
            BindingCandidate("org/a", "provider_list"),
            BindingCandidate("org/b", "provider_list"),
        )
    )

    assert result.status == "waiting_human"
    assert result.selected is None
    assert result.provenance == ("provider_list", "provider_list")


def test_binding_selection_is_tied_to_revision() -> None:
    """AC-FR0401-02: a selected candidate records the Setup revision."""
    result = resolve_binding(
        (BindingCandidate("org/a", "git_remote"),),
        selected="org/a",
        revision="setup_7",
    )

    assert result.status == "done"
    assert result.selected == "org/a"
    assert result.revision == "setup_7"
