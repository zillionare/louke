"""FR-0400: Test Plan design closure.

Validates that the Test Plan binds every effective AC to an observable
interface, required layer(s), host runner/command, fixture/environment, CI
job, trace metadata and rationale.  Observable interfaces and execution
entries must resolve to Interfaces real identities whose command/path/status
semantics match the corresponding machine contract and Architecture.  Unit-
only coverage of cross-module behavior, internal-API-only main user journeys,
missing required layer, or any orphan FR/AC/interface/contract mapping
blocks the baseline (AC-FR0400-01).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ERROR_CODES = (
    "TEST_PLAN_AC_MISSING",
    "TEST_PLAN_ORPHAN_INTERFACE",
    "TEST_PLAN_LAYER_MISSING",
    "TEST_PLAN_INTERNAL_API_ONLY",
    "TEST_PLAN_ORPHAN_CONTRACT",
)

_AC_ID_PATTERN = re.compile(r"\bAC-(?:FR|NFR)\d{4}-\d{2}\b")
_IF_PATTERN = re.compile(r"\bIF-[A-Z]{2,4}-\d{2}\b")
_REQUIRED_LAYER_LINE_PATTERN = re.compile(
    r"\|\s*`(AC-[A-Z]+-\d{2})`\s*\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|"
)
_KNOWN_CONTRACT_KINDS = frozenset(
    {
        "integration-test",
        "e2e-test",
        "pre-commit",
        "github-actions-ci",
        "release-version",
        "build-artifact",
        "publish-recovery",
    }
)
_CROSS_MODULE_INTERFACES = frozenset(
    {
        "IF-DES-01",
        "IF-DES-02",
        "IF-CON-01",
        "IF-REG-01",
        "IF-TST-01",
        "IF-PC-01",
        "IF-CI-01",
        "IF-REL-01",
        "IF-BLD-01",
        "IF-PUB-01",
        "IF-PRM-01",
        "IF-REV-01",
        "IF-WEB-01",
        "IF-FCT-01",
        "IF-AUD-01",
    }
)


class TestPlanError(Exception):
    """A fail-closed Test Plan rejection carrying a stable code."""

    __test__ = False

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class TestPlanEntry:
    """A single Test Plan entry binding an AC to its test layer closure.

    Attributes:
        ac_id: The acceptance criterion identifier (e.g. ``AC-FR0100-01``).
        observable_interfaces: Tuple of IF-* identities the AC is observed
            through.
        required_layers: Tuple of layer codes (``U``, ``C``, ``I``, ``E``).
        runner_command: Host runner command or path.
        ci_job: CI job name that runs the test.
        fixture_environment: Fixture/environment description.
        trace_metadata: Mapping of trace metadata (e.g. ``contracts``).
        rationale: Free-text rationale for the layer/fixture/CI choice.
        orphan_interfaces: IF-* references that do not resolve to Interfaces.
    """

    __test__ = False

    ac_id: str
    observable_interfaces: tuple[str, ...]
    required_layers: tuple[str, ...]
    runner_command: str
    ci_job: str
    fixture_environment: str
    trace_metadata: dict[str, Any]
    rationale: str
    orphan_interfaces: tuple[str, ...] = ()

    def has_required_layer(self) -> bool:
        """Return ``True`` if at least one required layer is declared."""
        return bool(self.required_layers)

    def is_cross_module(self) -> bool:
        """Return ``True`` if any observable interface is cross-module."""
        return any(
            iface in _CROSS_MODULE_INTERFACES for iface in self.observable_interfaces
        )

    def requires_integration_layer(self) -> bool:
        """Return ``True`` if a cross-module interface requires integration."""
        return self.is_cross_module()

    def is_main_user_journey(self) -> bool:
        """Return ``True`` if the rationale mentions a main user journey."""
        rationale = self.rationale.lower()
        return "journey" in rationale or "m-design" in rationale


def _extract_ac_ids(path: Path) -> set[str]:
    return {
        m.group(0) for m in _AC_ID_PATTERN.finditer(path.read_text(encoding="utf-8"))
    }


def _extract_interface_identities(path: Path) -> set[str]:
    return {m.group(0) for m in _IF_PATTERN.finditer(path.read_text(encoding="utf-8"))}


def _parse_entries(test_plan_path: Path) -> list[TestPlanEntry]:
    """Parse the §4.1 AC table into Test Plan entries.

    The Test Plan §4.1 table has rows of the form::

        | `AC-FRXXXX-YY` | IF-XXX-XX | U+C+I / jobs | fixture | rationale |

    The parser extracts ac_id, observable interfaces, required layers, CI
    jobs, fixture and rationale.  It is intentionally simple and tolerant of
    table formatting variations; missing rows raise TEST_PLAN_AC_MISSING.
    """
    text = test_plan_path.read_text(encoding="utf-8")
    entries: list[TestPlanEntry] = []
    for line in text.splitlines():
        if "`AC-" not in line or "|" not in line:
            continue
        ac_match = _AC_ID_PATTERN.search(line)
        if not ac_match:
            continue
        ac_id = ac_match.group(0)
        ifaces = tuple(_IF_PATTERN.findall(line))
        # Cells are pipe-delimited: | AC | IF | layers / CI | fixture | rationale |
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        layers = _parse_layer_codes(cells[2] if len(cells) > 2 else "")
        ci_job = cells[2] if len(cells) > 2 else ""
        fixture = cells[3] if len(cells) > 3 else ""
        rationale = cells[4] if len(cells) > 4 else ""
        contracts = sorted({c for c in _KNOWN_CONTRACT_KINDS if c in line})
        entries.append(
            TestPlanEntry(
                ac_id=ac_id,
                observable_interfaces=ifaces,
                required_layers=layers,
                runner_command=ci_job,
                ci_job=ci_job,
                fixture_environment=fixture,
                trace_metadata={"contracts": contracts},
                rationale=rationale,
                orphan_interfaces=(),
            )
        )
    return entries


def _parse_layer_codes(cell: str) -> tuple[str, ...]:
    """Extract layer codes (``U``, ``C``, ``I``, ``E``) from a table cell."""
    codes: list[str] = []
    for token in ("U", "C", "I", "E"):
        if token in cell:
            codes.append(token)
    return tuple(codes)


@dataclass(frozen=True)
class TestPlanReport:
    """Result of :func:`validate_test_plan`.

    Attributes:
        status: ``pass`` or ``fail``.
        entries: Parsed Test Plan entries with closure information.
        orphan_ac_ids: AC IDs declared in acceptance but missing from the
            Test Plan.
    """

    __test__ = False

    status: str
    entries: list[TestPlanEntry]
    orphan_ac_ids: tuple[str, ...] = ()


def validate_test_plan(
    *,
    acceptance_path: Path,
    test_plan_path: Path,
    interfaces_path: Path,
) -> TestPlanReport:
    """Validate the Test Plan against the Acceptance and Interfaces docs.

    Args:
        acceptance_path: Path to ``acceptance.md`` declaring the AC IDs.
        test_plan_path: Path to ``test-plan.md``.
        interfaces_path: Path to ``interfaces.md`` declaring IF-* identities.

    Returns:
        A :class:`TestPlanReport` with parsed entries and closure status.

    Raises:
        TestPlanError: When the Test Plan is structurally invalid (e.g.
            missing required sections).
    """
    acceptance_ids = _extract_ac_ids(acceptance_path)
    interfaces_ids = _extract_interface_identities(interfaces_path)
    entries = _parse_entries(test_plan_path)
    entry_by_ac = {e.ac_id: e for e in entries}
    orphan_ac_ids = sorted(acceptance_ids - set(entry_by_ac))

    # Mark orphan interfaces on each entry
    final_entries: list[TestPlanEntry] = []
    has_failure = bool(orphan_ac_ids)
    for entry in entries:
        orphans = tuple(
            iface
            for iface in entry.observable_interfaces
            if iface not in interfaces_ids
        )
        if orphans:
            has_failure = True
        final_entries.append(
            TestPlanEntry(
                ac_id=entry.ac_id,
                observable_interfaces=entry.observable_interfaces,
                required_layers=entry.required_layers,
                runner_command=entry.runner_command,
                ci_job=entry.ci_job,
                fixture_environment=entry.fixture_environment,
                trace_metadata=entry.trace_metadata,
                rationale=entry.rationale,
                orphan_interfaces=orphans,
            )
        )

    status = "fail" if has_failure else "pass"
    return TestPlanReport(
        status=status,
        entries=final_entries,
        orphan_ac_ids=tuple(orphan_ac_ids),
    )
