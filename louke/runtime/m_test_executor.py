"""FR-1300: M-TEST execution & defect triage.

After Prism approves the test contract, Runtime independently executes
integration/e2e and records runner, environment/fixture, commit, command,
result and covered AC.  Test/fixture errors return to Shield;
implementation defects keep tests and return to Devon; design gaps
return to M-DESIGN; requirements/Acceptance gaps return via Human to
M-SPEC/M-ACC; semantic ambiguity may be diagnosed by Prism, never punted
to Human for technical attribution.  After fixes, affected layers are
re-run and re-reviewed; success creates a controlled test commit
(AC-FR1300-01).
"""

from __future__ import annotations

from dataclasses import dataclass

ERROR_CODES = (
    "TEST_RUNNER_FAILED",
    "TEST_DEFECT_ROUTE_INVALID",
    "TEST_SUITE_REQUIRED_MISSING",
    "TEST_COMMIT_CONFLICT",
)

_VALID_DEFECT_CATEGORIES = (
    "test_or_fixture",
    "implementation",
    "design",
    "requirement",
)

_DEFECT_ROUTES: dict[str, tuple[str, bool]] = {
    "test_or_fixture": ("Shield", False),
    "implementation": ("Devon", False),
    "design": ("M-DESIGN", False),
    "requirement": ("M-SPEC/M-ACC", True),
}


class MTestExecutionError(Exception):
    """A fail-closed M-TEST execution rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class SuiteResult:
    """Result of executing one required test suite (AC-FR1300-01).

    Attributes:
        suite_id: Stable suite identity.
        layer: ``integration|e2e|regression``.
        passed: ``True`` if the suite passed.
        runner: Runner identity (e.g. ``project-venv``).
        environment: Environment identity (e.g. ``py-3.12``).
        fixture: Fixture identity.
        commit_oid: Commit OID the suite ran against.
        command: Exact command that was run.
        result_digest: ``sha256:<hex>`` of the result bytes.
        ac_ids: Tuple of AC anchors the suite covers.
        defect_category: Optional defect category if the suite failed.
    """

    suite_id: str
    layer: str
    passed: bool
    runner: str
    environment: str
    fixture: str
    commit_oid: str
    command: str
    result_digest: str
    ac_ids: tuple[str, ...]
    defect_category: str | None = None


@dataclass(frozen=True)
class DefectRoute:
    """A defect triage route (AC-FR1300-01).

    Attributes:
        target: ``Shield|Devon|M-DESIGN|M-SPEC/M-ACC``.
        requires_human: ``True`` only for requirement gaps.
        preserve_tests: ``True`` for implementation defects (tests preserved).
    """

    target: str
    requires_human: bool
    preserve_tests: bool = False


@dataclass(frozen=True)
class ControlledTestCommit:
    """A controlled test commit after all required suites pass (AC-FR1300-01).

    Attributes:
        commit_id: Stable commit identity.
        branch_oid: Branch OID the commit was created on.
        suite_ids: Tuple of suite ids included in the commit.
    """

    commit_id: str
    branch_oid: str
    suite_ids: tuple[str, ...]


class MTestExecutor:
    """Records suite results and routes defects (AC-FR1300-01)."""

    def __init__(self) -> None:
        self._results: dict[str, SuiteResult] = {}

    def execute(self, result: SuiteResult) -> SuiteResult:
        """Record the execution result of a suite."""
        self._results[result.suite_id] = result
        return result

    def route_defect(self, result: SuiteResult) -> DefectRoute:
        """Route a failed suite's defect to its owner (AC-FR1300-01).

        Args:
            result: The failed :class:`SuiteResult`.

        Returns:
            A :class:`DefectRoute` with the target owner.

        Raises:
            MTestExecutionError: With ``TEST_DEFECT_ROUTE_INVALID`` if the
                defect category is unknown or the suite passed (no defect).
        """
        if result.passed:
            raise MTestExecutionError(
                "TEST_DEFECT_ROUTE_INVALID",
                f"suite {result.suite_id} passed; no defect to route",
            )
        category = result.defect_category
        if category not in _VALID_DEFECT_CATEGORIES:
            raise MTestExecutionError(
                "TEST_DEFECT_ROUTE_INVALID",
                f"unknown defect category {category!r}; must be one of {_VALID_DEFECT_CATEGORIES}",
            )
        target, requires_human = _DEFECT_ROUTES[category]
        return DefectRoute(
            target=target,
            requires_human=requires_human,
            preserve_tests=(category == "implementation"),
        )

    def create_controlled_test_commit(
        self, *, branch_oid: str, required_suite_ids: tuple[str, ...]
    ) -> ControlledTestCommit:
        """Create a controlled test commit after all required suites pass.

        Args:
            branch_oid: Branch OID the commit is created on.
            required_suite_ids: Tuple of required suite ids.

        Returns:
            A :class:`ControlledTestCommit` with the suite ids.

        Raises:
            MTestExecutionError: With ``TEST_SUITE_REQUIRED_MISSING`` if any
                required suite was not executed; ``TEST_RUNNER_FAILED`` if any
                required suite failed.
        """
        for sid in required_suite_ids:
            if sid not in self._results:
                raise MTestExecutionError(
                    "TEST_SUITE_REQUIRED_MISSING",
                    f"required suite {sid!r} was not executed",
                )
            if not self._results[sid].passed:
                raise MTestExecutionError(
                    "TEST_RUNNER_FAILED",
                    f"required suite {sid!r} did not pass",
                )
        return ControlledTestCommit(
            commit_id=f"test-commit:{branch_oid[:8]}",
            branch_oid=branch_oid,
            suite_ids=tuple(required_suite_ids),
        )
