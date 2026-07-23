"""Unit contracts for independent Setup dependency checks."""

from louke.web.dependency_checks import (
    DependencyCheck,
    dependencies_ready,
    recheck_dependencies,
)


def test_required_dependency_failure_blocks_review_without_hiding_ready_items() -> None:
    """AC-FR0501-01: each result remains visible and required errors block."""
    checks = recheck_dependencies(
        (
            DependencyCheck("louke_store", True, "ready", "store readable"),
            DependencyCheck("opencode", True, "error", "OpenCode timed out"),
            DependencyCheck("catalog", False, "ready", "catalog readable"),
        )
    )

    by_id = {check.dependency_id: check for check in checks}
    assert by_id["louke_store"].state == "ready"
    assert by_id["opencode"].message == "OpenCode timed out"
    assert not dependencies_ready(checks)


def test_uncertain_result_is_not_ready() -> None:
    """AC-FR0501-02: unavailable facts cannot be represented as READY."""
    checks = recheck_dependencies(
        (DependencyCheck("model", True, "unknown", "model probe uncertain"),)
    )

    assert checks[0].state == "error"
    assert not dependencies_ready(checks)
