"""Deterministic, non-secret dependency readiness projections."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DependencyCheck:
    """One dependency result from the current recheck attempt."""

    dependency_id: str
    required: bool
    state: str
    message: str


def recheck_dependencies(
    checks: tuple[DependencyCheck, ...],
) -> tuple[DependencyCheck, ...]:
    """Normalize a dependency probe result without carrying stale success.

    Args:
        checks: Current independently obtained dependency facts.

    Returns:
        Stable sorted checks. Unknown states become non-ready errors.
    """
    normalized = tuple(
        DependencyCheck(
            check.dependency_id,
            check.required,
            check.state if check.state in {"ready", "missing", "error"} else "error",
            check.message,
        )
        for check in checks
    )
    return tuple(sorted(normalized, key=lambda check: check.dependency_id))


def dependencies_ready(checks: tuple[DependencyCheck, ...]) -> bool:
    """Return whether every required current check is explicitly ready."""
    return bool(checks) and all(
        not check.required or check.state == "ready" for check in checks
    )
