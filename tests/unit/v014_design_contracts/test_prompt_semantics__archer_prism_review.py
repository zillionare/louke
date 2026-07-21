"""AC-FR2200/2300/2400/2500-01: Archer/Prism prompt semantic + review contracts.

These are contract-as-artifact assertions over the candidate prompt bundle and
the reviewer binding: the Archer/Prism roles carry the exact permission-forbidden
sets and bound output schema identities, the reviewer executes independently of
the reviewed candidate (self-review prohibited), and every reviewed input is a
declared freshness trigger.  No new runtime is introduced; the design artifacts
are the authoritative source of the semantic contract.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[3]
_PROMPTS = (
    _ROOT
    / ".louke"
    / "project"
    / "specs"
    / "v0.14-002-workflow-reflow-design"
    / "design-artifacts"
    / "prompts"
)


def _bundle() -> dict[str, Any]:
    return json.loads((_PROMPTS / "prompt-bundle.candidate.json").read_bytes())


def _reviewer_binding() -> dict[str, Any]:
    return json.loads((_PROMPTS / "reviewer-binding.candidate.json").read_bytes())


def _source(role: str) -> dict[str, Any]:
    return next(s for s in _bundle()["sources"] if s["role"] == role)


# --- FR-2200 Archer normative semantic contract --------------------------------


def test_archer_forbidden_actions_cover_all_out_of_scope_verbs() -> None:
    """AC-FR2200-01: Archer cannot commit/push/dispatch/review/activate/progress."""
    forbidden = set(_source("archer")["permissions"]["forbidden"])
    assert {
        "commit",
        "push",
        "dispatch",
        "review persistence",
        "activation",
        "stage progression",
    } <= forbidden


def test_archer_output_binds_the_active_design_result_schema() -> None:
    """AC-FR2200-01: Archer output is the bound archer-design-result schema."""
    out = _source("archer")["output_schema_ref"]
    assert out["identity"] == "louke.agent-io.archer-design-result"
    assert _source("archer")["input_schema_ref"]["identity"] == (
        "louke.agent-io.archer-design-task-input"
    )
    assert (
        _source("archer")["permissions"]["write"]
        == "only current task-manifest allowlist"
    )


# --- FR-2300 Prism design-review semantic contract -----------------------------


def test_prism_forbidden_actions_cover_all_out_of_scope_verbs() -> None:
    """AC-FR2300-01: Prism cannot write review artifacts, gate, activate or progress."""
    prism = _source("prism")
    forbidden = set(prism["permissions"]["forbidden"])
    assert {
        "review artifact write",
        "commit",
        "push",
        "Runtime gate command",
        "activation",
        "stage progression",
    } <= forbidden
    assert prism["permissions"]["write"] == "none"


def test_prism_output_binds_the_design_review_schema() -> None:
    """AC-FR2300-01: Prism verdict/findings bind to the design-review schema identity."""
    prism = _source("prism")
    assert (
        prism["output_schema_ref"]["identity"] == "louke.agent-io.prism-design-review"
    )
    assert prism["input_schema_ref"]["identity"] == (
        "louke.agent-io.prism-design-review-task-input"
    )


# --- FR-2400 Human-optional review + direct diff -------------------------------


def test_review_path_does_not_require_human_author() -> None:
    """AC-FR2400-01: baseline path is Archer + gates + Prism; self-review prohibited."""
    binding = _reviewer_binding()
    assert binding["self_review_prohibited"] is True
    # Both author and reviewer roles exist in the closed bundle.
    roles = {s["role"] for s in _bundle()["sources"]}
    assert roles == {"archer", "prism"}


# --- FR-2500 Independent review loop + freshness -------------------------------


def test_reviewer_execution_is_independent_of_reviewed_candidate() -> None:
    """AC-FR2500-01: reviewer execution bundle differs from the reviewed candidate."""
    binding = _reviewer_binding()
    exec_digest = binding["reviewer_execution_bundle"]["deployment_digest"]
    reviewed_bundle = binding["reviewed_candidate_bundle"]["digest"]
    reviewed_render = binding["reviewed_candidate_bundle"][
        "candidate_prism_render_digest"
    ]
    assert exec_digest != reviewed_bundle
    assert exec_digest != reviewed_render
    assert binding["reviewer_execution_bundle"]["state"] == "trusted-active-existing"
    assert binding["reviewed_candidate_bundle"]["state"] == "candidate-not-deployed"


def test_any_reviewed_input_change_is_a_freshness_trigger() -> None:
    """AC-FR2500-01: every reviewed input change makes the verdict stale."""
    stale_if = _reviewer_binding()["stale_if"]
    joined = " ".join(stale_if).lower()
    assert "reviewer active digest" in joined
    assert "candidate bundle digest" in joined
    assert "base commit" in joined
    assert "discussion" in joined


def test_candidate_cannot_self_certify_or_activate() -> None:
    """AC-FR2500-01/AC-FR2050-01: candidate output cannot establish trust itself."""
    binding = _reviewer_binding()
    semantics = binding["failure_semantics"].lower()
    assert "cannot establish trust" in semantics or "activate itself" in semantics
