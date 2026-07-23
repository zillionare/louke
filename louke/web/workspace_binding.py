"""Explicit workspace/repository identity binding and provenance rules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BindingCandidate:
    """A non-secret identity candidate and the fact that produced it."""

    value: str
    source: str


@dataclass(frozen=True)
class BindingResult:
    """Binding decision tied to one Setup revision."""

    status: str
    selected: str | None
    provenance: tuple[str, ...]
    revision: str | None


def resolve_binding(
    candidates: tuple[BindingCandidate, ...],
    *,
    selected: str | None = None,
    revision: str | None = None,
) -> BindingResult:
    """Resolve a binding only when a Human selection is unambiguous.

    Args:
        candidates: Values discovered from independent workspace/provider facts.
        selected: Human-selected value for the current revision.
        revision: Opaque Setup revision carrying the selection.

    Returns:
        ``waiting_human`` for zero/multiple candidates or invalid selection;
        ``done`` with source provenance for one exact selected candidate.
    """
    sources = tuple(candidate.source for candidate in candidates)
    if selected is None or revision is None:
        return BindingResult("waiting_human", None, sources, None)
    matches = [candidate for candidate in candidates if candidate.value == selected]
    if len(matches) != 1:
        return BindingResult("waiting_human", None, sources, None)
    return BindingResult("done", selected, (matches[0].source,), revision)
