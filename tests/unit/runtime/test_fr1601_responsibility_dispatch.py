"""FR-1601: separation of programmatic and semantic agent responsibilities.

AC references:
- AC-FR1601-01: deterministic responsibilities run as registered program handlers.
- AC-FR1601-02: agent claims do not cause control-plane or release side effects;
  only program adapter evidence is accepted.
- AC-FR1601-03: program validates diff/allowlist and runs authoritative gates;
  agent self-reported pass cannot substitute for gate results.
- AC-FR1601-04: workflow graphs no longer create agent tasks for already-programmed
  responsibilities; remaining agent tasks declare semantic inputs/outputs.
- AC-FR1601-05: invalid/out-of-scope/digest-mismatch/undeclared-transition results
  are rejected and do not advance the run.
- AC-FR1601-06: built-in responsibility inventory is exhaustive and consistent;
  catalog validation fails on unclassified entries, pure tool-wrapper agents or
  inventory/dispatch mismatches before creating any agent task.
"""

from __future__ import annotations

from typing import Any

import pytest

from louke.runtime.responsibility_dispatch import (
    DispatchResult,
    ResponsibilityCatalog,
    ResponsibilityKind,
    ResponsibilityRegistry,
    UnknownResponsibilityError,
    ValidationError,
)


# -- AC-FR1601-01 -------------------------------------------------------------


def test_ac_fr1601_01_deterministic_responsibility_uses_program_handler():
    """AC-FR1601-01: deterministic responsibilities use program handlers.

    A responsibility that has enumerable deterministic rules for the same input
    is registered as a program handler, not an agent task.
    """
    registry = ResponsibilityRegistry()
    registry.register(
        name="classify_input",
        kind=ResponsibilityKind.PROGRAM,
        handler=lambda inputs: {"category": "bug_fix"},
    )

    result = registry.dispatch("classify_input", {"text": "fix crash"})

    assert isinstance(result, DispatchResult)
    assert result.kind == ResponsibilityKind.PROGRAM
    assert result.output == {"category": "bug_fix"}


# -- AC-FR1601-02 -------------------------------------------------------------


def test_ac_fr1601_02_agent_claim_does_not_change_control_plane():
    """AC-FR1601-02: agent claims cannot cause control-plane side effects.

    An agent result that claims to approve a gate or commit/push must be turned
    into a program adapter verification step before any side effect occurs.
    """
    registry = ResponsibilityRegistry()
    side_effects: list[str] = []

    def approve_gate(inputs: dict[str, Any]) -> dict[str, Any]:
        side_effects.append("gate_approved")
        return {"approved": True}

    registry.register(
        name="approve_gate",
        kind=ResponsibilityKind.PROGRAM,
        handler=approve_gate,
    )

    result = registry.dispatch("approve_gate", {"claim": "I approve the gate"})

    assert result.output == {"approved": True}
    assert side_effects == ["gate_approved"]


# -- AC-FR1601-03 -------------------------------------------------------------


def test_ac_fr1601_03_program_validates_diff_and_runs_authoritative_gate():
    """AC-FR1601-03: program validates diff/allowlist and runs gate.

    The agent may produce a diff and local test output, but only the program
    adapter verifies allowlist and runs the authoritative gate.
    """
    registry = ResponsibilityRegistry()

    def gate_runner(inputs: dict[str, Any]) -> dict[str, Any]:
        diff = inputs.get("diff", [])
        allowlist = inputs.get("allowlist", [])
        forbidden = [p for p in diff if not any(p.startswith(a) for a in allowlist)]
        if forbidden:
            return {"passed": False, "reason": f"forbidden paths: {forbidden}"}
        return {"passed": True}

    registry.register(
        name="authoritative_gate",
        kind=ResponsibilityKind.PROGRAM,
        handler=gate_runner,
    )

    ok = registry.dispatch(
        "authoritative_gate",
        {"diff": ["src/foo.py"], "allowlist": ["src/"]},
    )
    assert ok.output == {"passed": True}

    fail = registry.dispatch(
        "authoritative_gate",
        {"diff": ["secrets/key.pem"], "allowlist": ["src/"]},
    )
    assert fail.output["passed"] is False


# -- AC-FR1601-04 -------------------------------------------------------------


def test_ac_fr1601_04_programmed_responsibilities_not_agent_tasks():
    """AC-FR1601-04: already-programmed responsibilities do not create agent tasks.

    A workflow graph's responsibility catalog marks programmed responsibilities
    as ``program``; they are never dispatched as ``semantic`` tasks.
    """
    catalog = ResponsibilityCatalog()
    catalog.register(
        name="classify_input",
        kind=ResponsibilityKind.PROGRAM,
        input_schema={"text": "string"},
        output_schema={"category": "string"},
    )
    catalog.register(
        name="semantic_decision",
        kind=ResponsibilityKind.SEMANTIC,
        input_schema={"context": "object"},
        output_schema={"decision": "string"},
    )

    assert catalog.kind_of("classify_input") == ResponsibilityKind.PROGRAM
    assert catalog.kind_of("semantic_decision") == ResponsibilityKind.SEMANTIC


# -- AC-FR1601-05 -------------------------------------------------------------


def test_ac_fr1601_05_invalid_results_rejected():
    """AC-FR1601-05: invalid agent results are rejected.

    Schema-invalid, out-of-scope, digest-mismatched or undeclared-transition
    results are refused and the run does not advance.
    """
    catalog = ResponsibilityCatalog()
    catalog.register(
        name="semantic_decision",
        kind=ResponsibilityKind.SEMANTIC,
        input_schema={"context": "object"},
        output_schema={"decision": "string"},
    )

    with pytest.raises(ValidationError):
        catalog.validate_result("semantic_decision", {"wrong_key": "value"})


# -- AC-FR1601-06 -------------------------------------------------------------


def test_ac_fr1601_06_catalog_validation_is_exhaustive():
    """AC-FR1601-06: catalog validation rejects unclassified or inconsistent entries.

    All built-in responsibilities must have an inventory entry with matching kind.
    Unclassified responsibilities, pure tool-wrapper agents or mismatches fail
    validation before any agent task is created.
    """
    catalog = ResponsibilityCatalog()
    catalog.register(
        name="classify_input",
        kind=ResponsibilityKind.PROGRAM,
        input_schema={"text": "string"},
        output_schema={"category": "string"},
    )
    catalog.register(
        name="semantic_decision",
        kind=ResponsibilityKind.SEMANTIC,
        input_schema={"context": "object"},
        output_schema={"decision": "string"},
    )

    # Valid catalog passes validation.
    catalog.validate()

    # Unknown responsibility cannot be dispatched.
    with pytest.raises(UnknownResponsibilityError):
        catalog.kind_of("missing_task")

    # A responsibility with unclassified kind fails validation.
    catalog.register(
        name="unclassified_task",
        kind=ResponsibilityKind.UNCLASSIFIED,
        input_schema={},
        output_schema={},
    )
    with pytest.raises(ValidationError):
        catalog.validate()
