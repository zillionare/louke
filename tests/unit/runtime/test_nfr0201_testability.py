"""NFR-0201: testability and honest stand-ins.

AC references:
- AC-NFR0201-01: the unit test suite runs offline without importing or
  initializing any external SDK (GitHub, OpenCode, model providers).
- AC-NFR0201-02: when a capability only has a stand-in adapter, querying the
  product capability or test report labels it as ``stand-in``, not real.
- AC-NFR0201-03: each implementation slice's core modules achieve statement
  coverage >= 0.95 when driven by the test suite.
"""

from __future__ import annotations

import ast
import pathlib
import subprocess
import sys

import pytest

from louke.runtime.catalog import DefinitionRegistry, Edge, Step, WorkflowDefinition
from louke.runtime.e2e_journey import E2EAdapterSet, GoldenJourney
from louke.runtime.foundation import (
    FoundationError,
    FoundationGap,
    foundation_ensure_handler,
)
from louke.runtime.program_steps import StepContext
from louke.runtime.recovery import recover_run
from louke.runtime.store import WorkflowRunStore


# -- AC-NFR0201-01 ------------------------------------------------------------


# Modules that constitute external SDKs and must never be imported by the
# offline unit test suite. Imports of these would make the suite depend on
# network credentials or real services.
_FORBIDDEN_SDK_MODULES: frozenset[str] = frozenset(
    {
        "openai",
        "anthropic",
        "github",
        "requests",
        "aiohttp",
        "grpc",
        "google.cloud",
        "boto3",
    }
)

# ``httpx`` is allowed as a dependency of the Starlette web layer, but the
# runtime unit tests must not import the live OpenCode client. We allow
# ``louke.*`` and stdlib/pytest imports implicitly.


def _imported_module_names(tree: ast.AST) -> set[str]:
    """Return the set of top-level module names imported by ``tree``."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_ac_nfr0201_01_unit_tests_import_no_external_sdk():
    """AC-NFR0201-01: unit test files do not import any external SDK module."""
    violations: list[str] = []
    for path in pathlib.Path("tests/unit").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported = _imported_module_names(tree)
        leaked = imported & _FORBIDDEN_SDK_MODULES
        if leaked:
            violations.append(f"{path}: imports {sorted(leaked)}")
    assert violations == [], "external SDK imports found: " + "; ".join(violations)


def test_ac_nfr0201_01_unit_suite_runs_offline():
    """AC-NFR0201-01: ``pytest tests/unit`` succeeds without network access.

    The subprocess deselects the two recursion-causing tests in this file
    (this one and the coverage test) so it does not re-enter them.
    """
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit",
            "-q",
            "--no-header",
            "--deselect=tests/unit/runtime/test_nfr0201_testability.py::test_ac_nfr0201_01_unit_suite_runs_offline",
            "--deselect=tests/unit/runtime/test_nfr0201_testability.py::test_ac_nfr0201_03_runtime_statement_coverage_at_least_95",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"unit suite failed (rc={result.returncode}):\n{result.stdout}\n{result.stderr}"
    )


# -- AC-NFR0201-02 ------------------------------------------------------------


def test_ac_nfr0201_02_stand_in_adapter_labeled():
    """AC-NFR0201-02: a stand-in OpenCode adapter is labeled ``stand-in``.

    Constructing a journey with ``opencode_real=False`` must report the
    adapter label as ``stand-in``, never ``real``.
    """
    adapters = E2EAdapterSet(opencode_real=False)
    journey = GoldenJourney(adapters=adapters)
    result = journey.run_new_feature()

    assert result.adapter_labels["opencode"] == "stand-in"


def test_ac_nfr0201_02_real_adapter_labeled_real():
    """AC-NFR0201-02: a real OpenCode adapter is labeled ``real``.

    The labeling is symmetric: when the adapter is real, the report must
    say so, so consumers can distinguish honest stand-ins from real
    integrations.
    """
    adapters = E2EAdapterSet(opencode_real=True)
    journey = GoldenJourney(adapters=adapters)
    result = journey.run_new_feature()

    assert result.adapter_labels["opencode"] == "real"


# -- AC-NFR0201-03 ------------------------------------------------------------


def test_ac_nfr0201_03_runtime_statement_coverage_at_least_95():
    """AC-NFR0201-03: ``louke/runtime/`` statement coverage >= 0.95.

    Runs ``coverage run -m pytest`` as a subprocess over the unit suite, then
    parses the JSON report to compute the statement coverage ratio for the
    runtime package. This avoids re-entrant pytest invocation.

    The subprocess excludes this test file to avoid infinite recursion.
    """
    pytest.importorskip("coverage")
    import json
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        cov_file = pathlib.Path(tmpdir) / ".coverage"
        json_file = pathlib.Path(tmpdir) / "cov.json"
        env = {**os.environ, "COVERAGE_FILE": str(cov_file)}

        run_result = subprocess.run(
            [
                sys.executable,
                "-m",
                "coverage",
                "run",
                "--source=louke.runtime",
                "-m",
                "pytest",
                "tests/unit",
                "-q",
                "--no-header",
                "--deselect=tests/unit/runtime/test_nfr0201_testability.py::test_ac_nfr0201_01_unit_suite_runs_offline",
                "--deselect=tests/unit/runtime/test_nfr0201_testability.py::test_ac_nfr0201_03_runtime_statement_coverage_at_least_95",
            ],
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        assert run_result.returncode == 0, (
            f"unit suite failed under coverage:\n{run_result.stdout}\n{run_result.stderr}"
        )

        json_result = subprocess.run(
            [
                sys.executable,
                "-m",
                "coverage",
                "json",
                "-o",
                str(json_file),
            ],
            capture_output=True,
            text=True,
            env=env,
        )
        assert json_result.returncode == 0, json_result.stderr

        data = json.loads(json_file.read_text(encoding="utf-8"))
        totals = data["totals"]

    ratio = totals["percent_covered"] / 100.0
    total_statements = totals["covered_lines"] + totals["missing_lines"]
    assert ratio >= 0.95, (
        f"runtime statement coverage {ratio:.4f} < 0.95 "
        f"({totals['missing_lines']} of {total_statements} statements missing)"
    )


# -- Coverage completion tests --------------------------------------------------
# These tests exercise edge-case branches in foundation.py and recovery.py
# that the FR-0401/FR-0201 tests do not reach, so the runtime package
# achieves the >= 0.95 statement coverage required by AC-NFR0201-03.


class _GapListAdapter:
    """Foundation adapter that returns a fixed gap list and records creates."""

    def __init__(self, gaps: list[FoundationGap]) -> None:
        self._gaps = list(gaps)
        self.create_calls: list[FoundationGap] = []

    def check(self, workspace: str) -> list[FoundationGap]:
        return list(self._gaps)

    def create(self, workspace: str, gap: FoundationGap) -> None:
        self.create_calls.append(gap)
        self._gaps = [g for g in self._gaps if g.key != gap.key]


def _ctx() -> StepContext:
    """Return a minimal StepContext for foundation handler tests."""
    return StepContext(
        run_id="run",
        step_id="foundation.ensure",
        attempt_id="att_1",
        workspace="ws",
        idempotency_key="att_1",
    )


def test_coverage_repair_leaves_unresolved_gap_fails():
    """Cover foundation.py: repair that does not resolve all gaps returns failed."""
    gap = FoundationGap(key="workspace/config", auto_repairable=True)
    adapter = _GapListAdapter([gap])
    # Simulate a repair that re-adds the gap on the next check.
    original_check = adapter.check

    def stubborn_check(workspace: str) -> list[FoundationGap]:
        adapter._gaps = [gap]
        return original_check(workspace)

    adapter.check = stubborn_check  # type: ignore[method-assign]

    handler = foundation_ensure_handler(adapter)
    result = handler(_ctx())

    assert result.result == "failed"


def test_coverage_safe_check_generic_exception_returns_failed():
    """Cover foundation.py: a generic exception in check returns failed."""
    adapter = _GapListAdapter([])

    def raise_generic(workspace: str) -> list[FoundationGap]:
        raise RuntimeError("unexpected")

    adapter.check = raise_generic  # type: ignore[method-assign]

    handler = foundation_ensure_handler(adapter)
    result = handler(_ctx())

    assert result.result == "failed"
    assert "unexpected" in str(result.output.get("error", ""))


def test_coverage_repair_create_foundation_error_wraps_message():
    """Cover foundation.py: FoundationError during create wraps the key."""
    gap = FoundationGap(key="workspace/config", auto_repairable=True)

    class CreateFailAdapter(_GapListAdapter):
        def create(self, workspace: str, gap: FoundationGap) -> None:
            raise FoundationError("disk full", retryable=False)

    adapter = CreateFailAdapter([gap])
    handler = foundation_ensure_handler(adapter)

    with pytest.raises(FoundationError, match="failed to create workspace/config"):
        handler(_ctx())


def test_coverage_repair_create_generic_error_wraps_message():
    """Cover foundation.py: generic exception during create becomes FoundationError."""
    gap = FoundationGap(key="workspace/config", auto_repairable=True)

    class CreateGenericFailAdapter(_GapListAdapter):
        def create(self, workspace: str, gap: FoundationGap) -> None:
            raise OSError("permission denied")

    adapter = CreateGenericFailAdapter([gap])
    handler = foundation_ensure_handler(adapter)

    with pytest.raises(FoundationError, match="permission denied"):
        handler(_ctx())


def test_coverage_repair_duplicate_key_skipped():
    """Cover foundation.py: duplicate keys in auto_gaps are skipped via seen set."""
    gap = FoundationGap(key="workspace/config", auto_repairable=True)
    adapter = _GapListAdapter([gap, gap])
    handler = foundation_ensure_handler(adapter)

    result = handler(_ctx())

    assert result.result == "repaired"
    assert len(adapter.create_calls) == 1


def test_coverage_recheck_after_repair_returns_handler_result():
    """Cover foundation.py: recheck after repair returning a HandlerResult."""
    gap = FoundationGap(key="workspace/config", auto_repairable=True)
    call_count = 0

    class RecheckFailAdapter(_GapListAdapter):
        def check(self, workspace: str) -> list[FoundationGap]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [gap]
            raise FoundationError("recheck failed", retryable=True)

    adapter = RecheckFailAdapter([gap])
    handler = foundation_ensure_handler(adapter)

    result = handler(_ctx())

    assert result.result == "retryable"


def test_coverage_recovery_idempotent_when_already_needs_attention():
    """Cover recovery.py: recovering a run already in needs_attention is a no-op."""
    definition = WorkflowDefinition(
        definition_id="nfr0201_recover",
        version="1",
        start_step="start",
        steps=(
            Step(
                step_id="start",
                kind="program",
                transitions=(Edge("e1", "start", "end", "done"),),
            ),
            Step(step_id="end", kind="program"),
        ),
    )
    registry = DefinitionRegistry()
    registry.register(definition)
    store = WorkflowRunStore(catalog=registry)
    run = store.create_run(definition)

    store.record_step_attempt(
        run_id=run.run_id,
        step_id=run.current_step,
        idempotency_key="att_1",
        status="uncertain",
    )
    first_recovery = recover_run(store, run.run_id)
    assert first_recovery.status == "needs_attention"

    second_recovery = recover_run(store, run.run_id)
    assert second_recovery.revision == first_recovery.revision
    assert second_recovery.status == "needs_attention"
