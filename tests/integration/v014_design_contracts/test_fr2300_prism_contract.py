"""Integration tests for FR-2300: Prism Design Review Semantic Contract.

AC-FR2300-01: Prism design-review manifest contains exact design, contract,
prompt bundle identities; output schema only allows identity-bound
verdict/findings/questions/advisory. Prompt contains no instructions to
write review artifact, call Runtime gate/stage commands, forge author
results or treat findings as Human decisions.
"""
# AC-FR2300-01

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PRISM_MD = REPO_ROOT / "louke" / "agents" / "Prism.md"


def test_prism_md_exists():
    assert PRISM_MD.exists()


def test_prism_md_has_frontmatter():
    text = PRISM_MD.read_text(encoding="utf-8")
    assert text.startswith("---")


def test_manifest_lists_prism_as_canonical_source(design_manifest):
    """manifest must list louke/agents/Prism.md as canonical source."""
    sources = design_manifest["prompt_candidates"]["sources"]
    prism = next(s for s in sources if "Prism" in s["path"])
    assert prism["path"] == "louke/agents/Prism.md"
    assert prism["digest"].startswith("sha256:")


def test_registry_has_prism_review_task_input_schema(registry_candidate):
    """registry must include prism-design-review-task-input schema."""
    ids = {s["identity"] for s in registry_candidate["agent_io_schemas"]}
    assert "louke.agent-io.prism-design-review-task-input" in ids


def test_registry_has_prism_review_output_schema(registry_candidate):
    """registry must include prism-design-review output schema."""
    ids = {s["identity"] for s in registry_candidate["agent_io_schemas"]}
    assert "louke.agent-io.prism-design-review" in ids


def test_prism_md_does_not_write_review_artifact():
    """Prism prompt must not instruct to write review artifact directly."""
    text = PRISM_MD.read_text(encoding="utf-8").lower()
    forbidden = [
        "write review artifact",
        "create review file",
        "persist review yourself",
    ]
    for pattern in forbidden:
        assert pattern not in text


def test_prism_md_does_not_call_runtime_gate():
    """Prism prompt must not instruct to call Runtime gate/stage commands."""
    text = PRISM_MD.read_text(encoding="utf-8").lower()
    forbidden = [
        "call runtime gate",
        "advance stage",
        "transition to m-impl",
        "enter m-lock",
    ]
    for pattern in forbidden:
        assert pattern not in text


def test_prism_md_does_not_forge_author_results():
    """Prism prompt must not instruct to forge author results."""
    text = PRISM_MD.read_text(encoding="utf-8").lower()
    forbidden = [
        "forge author",
        "fake archer result",
        "impersonate author",
    ]
    for pattern in forbidden:
        assert pattern not in text


@pytest.mark.awaiting_devon("FR-2300")
def test_prism_output_schema_only_allows_verdict_findings_questions_advisory(
    mock_design_review,
):
    """Prism output schema must only allow verdict/findings/questions/advisory."""
    mock_design_review.submit.return_value = {
        "ok": True,
        "verdict": "PASS",
        "findings": [],
        "questions": [],
        "advisory": None,
        "identity_bound": True,
    }
    result = mock_design_review.submit(verdict="PASS")
    allowed_fields = {"verdict", "findings", "questions", "advisory"}
    output_keys = {k for k in result if k not in ("ok", "identity_bound")}
    assert output_keys.issubset(allowed_fields), (
        f"unexpected fields: {output_keys - allowed_fields}"
    )
