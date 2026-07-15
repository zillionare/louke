"""FR-1701: fixed workflow, dynamic branch and multi-workflow selection.

AC references:
- AC-FR1701-01: workflow definition nodes/edges/gates/decisions/versions are
  enumerable; agents cannot add nodes or edges at runtime.
- AC-FR1701-02: run binds to the user-selected definition/version; program
  classification only when user did not select and definition allows it.
- AC-FR1701-03: when semantic decision is needed, Maestro receives bounded
  context plus candidate set and returns schema-valid candidate, reason and
  confidence.
- AC-FR1701-04: Maestro suggestions outside candidates, direct side-effect
  commands, or low-confidence human-confirmation suggestions are rejected or
  routed to declared human clarification gate; state is not changed by the
  suggestion.
- AC-FR1701-05: new_feature, valid hotfix and active-main-project requirements
  bind to full-requirement workflow, quick_rgr|design_required hotfix graph, or
  backlog; agent suggestions cannot cross definitions, bypass source-contract
  validation, or create a second main run.
"""

from __future__ import annotations

import pytest

from louke.runtime.workflow_definitions import (
    Classification,
    IllegalSuggestionError,
    WorkflowDefinition,
    WorkflowRegistry,
    WorkflowRunBinding,
)


# -- AC-FR1701-01 -------------------------------------------------------------


def test_ac_fr1701_01_definition_enumerable_and_immutable():
    """AC-FR1701-01: definition structure is enumerable and immutable."""
    definition = WorkflowDefinition(
        name="new_feature",
        version="1.0",
        nodes={"requirements", "design", "implementation", "review", "done"},
        edges={
            ("requirements", "design"),
            ("design", "implementation"),
            ("implementation", "review"),
            ("review", "done"),
        },
        gates={"m_lock"},
        decisions={"design_required"},
    )

    assert definition.nodes == {
        "requirements",
        "design",
        "implementation",
        "review",
        "done",
    }
    assert ("design", "implementation") in definition.edges
    assert "m_lock" in definition.gates
    assert "design_required" in definition.decisions
    assert definition.version == "1.0"


def test_ac_fr1701_01_definition_cannot_be_mutated_by_agent():
    """AC-FR1701-01: agents cannot add nodes or edges at runtime."""
    registry = WorkflowRegistry()
    registry.register(
        WorkflowDefinition(
            name="new_feature",
            version="1.0",
            nodes={"start", "end"},
            edges={("start", "end")},
        )
    )

    with pytest.raises(RuntimeError):
        registry.register(
            WorkflowDefinition(
                name="new_feature",
                version="1.0",
                nodes={"start", "middle", "end"},
                edges={("start", "middle"), ("middle", "end")},
            )
        )


# -- AC-FR1701-02 -------------------------------------------------------------


def test_ac_fr1701_02_run_binds_user_selected_definition():
    """AC-FR1701-02: run binds to the definition selected by the user."""
    registry = WorkflowRegistry()
    registry.register(
        WorkflowDefinition(
            name="new_feature",
            version="1.0",
            nodes={"start", "end"},
            edges={("start", "end")},
        )
    )

    binding = WorkflowRunBinding.start(
        run_id="run_001",
        definition_name="new_feature",
        version="1.0",
        registry=registry,
    )

    assert binding.definition.name == "new_feature"
    assert binding.definition.version == "1.0"
    assert binding.selected_by_user is True


def test_ac_fr1701_02_program_classification_only_when_allowed():
    """AC-FR1701-02: classification happens only when user did not select."""
    registry = WorkflowRegistry()
    registry.register(
        WorkflowDefinition(
            name="auto_classify",
            version="1.0",
            nodes={"start", "end"},
            edges={("start", "end")},
            allow_auto_select=True,
        )
    )

    binding = WorkflowRunBinding.start(
        run_id="run_002",
        registry=registry,
        classification=Classification(
            kind="auto_classify", reason="input is a bug report"
        ),
    )

    assert binding.definition.name == "auto_classify"
    assert binding.selected_by_user is False
    assert binding.classification.kind == "auto_classify"


# -- AC-FR1701-03 -------------------------------------------------------------


def test_ac_fr1701_03_maestro_receives_bounded_context():
    """AC-FR1701-03: Maestro receives bounded context + candidates and returns
    schema-valid candidate, reason and confidence."""
    registry = WorkflowRegistry()
    registry.register(
        WorkflowDefinition(
            name="new_feature",
            version="1.0",
            nodes={"requirements", "design", "implementation"},
            edges={("requirements", "design"), ("design", "implementation")},
            decisions={"design_required"},
        )
    )

    binding = WorkflowRunBinding.start(
        run_id="run_003",
        definition_name="new_feature",
        version="1.0",
        registry=registry,
    )

    suggestion = binding.request_semantic_decision(
        decision="design_required",
        context={"requirement_text": "add user login"},
        candidates=["design_required", "skip_design"],
    )

    assert suggestion.candidate in ["design_required", "skip_design"]
    assert "reason" in suggestion.metadata
    assert "confidence" in suggestion.metadata


# -- AC-FR1701-04 -------------------------------------------------------------


def test_ac_fr1701_04_out_of_scope_suggestion_rejected():
    """AC-FR1701-04: suggestions outside candidates are rejected."""
    registry = WorkflowRegistry()
    registry.register(
        WorkflowDefinition(
            name="new_feature",
            version="1.0",
            nodes={"start", "end"},
            edges={("start", "end")},
            decisions={"approve"},
        )
    )

    binding = WorkflowRunBinding.start(
        run_id="run_004",
        definition_name="new_feature",
        version="1.0",
        registry=registry,
    )

    with pytest.raises(IllegalSuggestionError):
        binding.request_semantic_decision(
            decision="approve",
            context={},
            candidates=["yes", "no"],
            suggestion="maybe",
        )


def test_ac_fr1701_04_low_confidence_routes_to_clarification():
    """AC-FR1701-04: low-confidence suggestions route to human gate."""
    registry = WorkflowRegistry()
    registry.register(
        WorkflowDefinition(
            name="new_feature",
            version="1.0",
            nodes={"start", "clarify", "end"},
            edges={("start", "clarify"), ("clarify", "end")},
            decisions={"route"},
        )
    )

    binding = WorkflowRunBinding.start(
        run_id="run_005",
        definition_name="new_feature",
        version="1.0",
        registry=registry,
    )

    result = binding.request_semantic_decision(
        decision="route",
        context={},
        candidates=["a", "b"],
        suggestion="a",
        confidence=0.3,
        min_confidence=0.7,
    )

    assert result.candidate == "a"
    assert result.requires_human_clarification is True


# -- AC-FR1701-05 -------------------------------------------------------------


def test_ac_fr1701_05_classification_binds_correct_workflow():
    """AC-FR1701-05: classifications bind to the correct workflow graph."""
    registry = WorkflowRegistry()
    registry.register(
        WorkflowDefinition(
            name="new_feature",
            version="1.0",
            nodes={"requirements", "done"},
            edges={("requirements", "done")},
            allow_auto_select=True,
        )
    )
    registry.register(
        WorkflowDefinition(
            name="hotfix",
            version="1.0",
            nodes={"quick_rgr", "design_required"},
            edges={("quick_rgr", "design_required")},
            allow_auto_select=True,
        )
    )

    feature = WorkflowRunBinding.start(
        run_id="run_006",
        registry=registry,
        classification=Classification(kind="new_feature"),
    )
    hotfix = WorkflowRunBinding.start(
        run_id="run_007",
        registry=registry,
        classification=Classification(kind="hotfix"),
    )

    assert feature.definition.name == "new_feature"
    assert hotfix.definition.name == "hotfix"


def test_ac_fr1701_05_no_second_main_run():
    """AC-FR1701-05: cannot create a second main run for the same project."""
    registry = WorkflowRegistry()
    registry.register(
        WorkflowDefinition(
            name="new_feature",
            version="1.0",
            nodes={"start", "end"},
            edges={("start", "end")},
            is_main_workflow=True,
            allow_auto_select=True,
        )
    )

    active: set[str] = set()
    binding_a = WorkflowRunBinding.start(
        run_id="run_008",
        registry=registry,
        classification=Classification(kind="new_feature"),
        active_main_runs=active,
    )
    active.add(binding_a.run_id)

    with pytest.raises(RuntimeError):
        WorkflowRunBinding.start(
            run_id="run_009",
            registry=registry,
            classification=Classification(kind="new_feature"),
            active_main_runs=active,
        )
