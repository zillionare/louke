"""Structured, user-actionable failure diagnostics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Diagnostic:
    """Failure context required by the NFR-0501 user contract."""

    failed_object: str
    known_fact: str
    impact: str
    responsible_party: str
    recovery_location: str


def validate_diagnostic(diagnostic: Diagnostic) -> bool:
    """Return true only when all user recovery fields are actionable."""
    fields = (
        diagnostic.failed_object,
        diagnostic.known_fact,
        diagnostic.impact,
        diagnostic.responsible_party,
        diagnostic.recovery_location,
    )
    if not all(field.strip() for field in fields):
        raise ValueError("diagnostic lacks actionable context")
    if diagnostic.known_fact.lower() in {"failed", "error", "retry"}:
        raise ValueError(
            "diagnostic must include known facts, not generic failure text"
        )
    return True
