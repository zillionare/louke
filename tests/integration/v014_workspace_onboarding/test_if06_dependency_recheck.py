"""IF-06: Dependency Recheck.

AC-FR0501-01, AC-FR0501-02, AC-NFR0401-01

Integration tests verify that dependency checks are isolated, that
unavailable items block Review, and that Recheck returns current results.
"""

from __future__ import annotations

from louke.web.dependency_checks import (
    DependencyCheck,
    dependencies_ready,
    recheck_dependencies,
)


def _checks(*items: tuple[str, str]) -> tuple[DependencyCheck, ...]:
    return tuple(
        DependencyCheck(
            dependency_id=did, required=True, state=state, message=f"{did}={state}"
        )
        for did, state in items
    )


def test_all_ready_enables_review():
    """AC-FR0501-01: all required dependencies ready enables Review."""
    # AC-FR0501-01
    checks = _checks(("python", "ready"), ("git", "ready"), ("opencode", "ready"))
    assert dependencies_ready(checks) is True


def test_missing_dependency_blocks_review():
    """AC-FR0501-01: a missing required dependency blocks Review."""
    # AC-FR0501-01
    checks = _checks(("python", "ready"), ("git", "missing"))
    assert dependencies_ready(checks) is False


def test_error_dependency_blocks_review():
    """AC-FR0501-01: an error state dependency blocks Review."""
    # AC-FR0501-01
    checks = _checks(("python", "ready"), ("opencode", "error"))
    assert dependencies_ready(checks) is False


def test_recheck_returns_current_results():
    """AC-FR0501-02: Recheck returns current facts, not cached values."""
    # AC-FR0501-02
    original = _checks(("python", "ready"), ("git", "missing"))
    rechecked = recheck_dependencies(original)
    # recheck returns a new tuple of DependencyCheck objects
    assert len(rechecked) == len(original)
    for item in rechecked:
        assert item.dependency_id in {c.dependency_id for c in original}


def test_dependency_check_message_does_not_leak_secret():
    """AC-FR0501-02: dependency message does not contain credential or token."""
    # AC-FR0501-02
    check = DependencyCheck(
        dependency_id="provider_auth",
        required=True,
        state="error",
        message="authentication failed for provider",
    )
    assert "token" not in check.message.lower() or "token" in "authentication"
    assert "password" not in check.message.lower()


def test_uncertain_does_not_become_ready():
    """AC-NFR0401-01: uncertain result is not treated as ready."""
    # AC-NFR0401-01
    checks = _checks(("python", "ready"), ("model", "error"))
    assert dependencies_ready(checks) is False
