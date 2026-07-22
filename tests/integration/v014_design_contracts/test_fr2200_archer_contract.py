"""Integration tests for FR-2200: Archer Normative Semantic Contract.

AC-FR2200-01: Archer prompt lint/behavior fixture confirms output
responsibilities include three design docs, machine contracts, direct diff
and gap advisory; new projects get autonomous technical choices. Prompt
contains no instructions to actively question Human technical scheme,
install, commit/push, dispatch, write review/gate or advance stage.
"""
# AC-FR2200-01

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
ARCHER_MD = REPO_ROOT / "louke" / "agents" / "Archer.md"


def test_archer_md_exists():
    """Archer.md canonical prompt must exist."""
    assert ARCHER_MD.exists()


def test_archer_md_has_frontmatter():
    """Archer.md must have YAML frontmatter."""
    text = ARCHER_MD.read_text(encoding="utf-8")
    assert text.startswith("---"), "Archer.md must start with frontmatter"
    # Find closing ---
    end = text.find("\n---", 4)
    assert end > 0, "Archer.md frontmatter must close with ---"


def test_manifest_lists_archer_as_canonical_source(design_manifest):
    """manifest must list louke/agents/Archer.md as canonical source."""
    sources = design_manifest["prompt_candidates"]["sources"]
    archer = next(s for s in sources if "Archer" in s["path"])
    assert archer["path"] == "louke/agents/Archer.md"
    assert archer["digest"].startswith("sha256:")


def test_archer_md_does_not_question_human_technical_scheme():
    """Archer prompt must not instruct to actively question Human technical scheme."""
    text = ARCHER_MD.read_text(encoding="utf-8").lower()
    # Negative patterns that should NOT appear as instructions
    forbidden_patterns = [
        "ask human which technology",
        "question human about technology choice",
        "prompt human to select",
    ]
    for pattern in forbidden_patterns:
        assert pattern not in text, f"Archer must not instruct: '{pattern}'"


def test_archer_md_does_not_commit_or_push():
    """Archer prompt must not instruct to commit or push."""
    text = ARCHER_MD.read_text(encoding="utf-8").lower()
    # Look for instruction-style commit/push
    forbidden = [
        "you must commit",
        "commit and push",
        "git push",
        "you should commit",
    ]
    for pattern in forbidden:
        assert pattern not in text, f"Archer must not instruct: '{pattern}'"


def test_archer_md_does_not_dispatch():
    """Archer prompt must not instruct to dispatch other agents."""
    text = ARCHER_MD.read_text(encoding="utf-8").lower()
    forbidden = [
        "dispatch prism",
        "dispatch devon",
        "call sage",
        "invoke scribe",
    ]
    for pattern in forbidden:
        assert pattern not in text


def test_archer_md_does_not_write_review():
    """Archer prompt must not instruct to write review artifacts."""
    text = ARCHER_MD.read_text(encoding="utf-8").lower()
    forbidden = [
        "write review",
        "create review artifact",
        "approve your own",
    ]
    for pattern in forbidden:
        assert pattern not in text


def test_archer_md_does_not_advance_stage():
    """Archer prompt must not instruct to advance workflow stage."""
    text = ARCHER_MD.read_text(encoding="utf-8").lower()
    forbidden = [
        "advance to m-impl",
        "transition to next stage",
        "enter m-lock",
        "proceed to m-implement",
    ]
    for pattern in forbidden:
        assert pattern not in text


@pytest.mark.awaiting_devon("FR-2200")
def test_archer_lint_confirms_three_design_docs_responsibility(mock_prompt_bundle):
    """Archer lint must confirm responsibility for three design docs."""
    mock_prompt_bundle.lint.return_value = {
        "ok": True,
        "responsibilities": [
            "three-design-docs",
            "machine-contracts",
            "direct-diff",
            "gap-advisory",
        ],
    }
    result = mock_prompt_bundle.lint(role="Archer")
    assert "three-design-docs" in result["responsibilities"]
    assert "machine-contracts" in result["responsibilities"]
