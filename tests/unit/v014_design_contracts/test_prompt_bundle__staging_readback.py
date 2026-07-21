"""AC-FR1700/1800/2000/2050/2100-01: IF-PRM-01 prompt bundle staging readback.

The prompt bundle program verifies the closed source set is exactly
``louke/agents/Archer.md`` + ``louke/agents/Prism.md``, recomputes the
canonical ``bundle_digest`` deterministically, and reads back the candidate
staging render as ``candidate_staging_in_sync|missing|drifted|stale`` against
the recorded source, transformer and staging digests — without ever touching
``.opencode/agents``.  Unlisted prompts fail closed with ``PROMPT_SCOPE_DENIED``.
"""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from louke._tools import prompt_bundle as pb

_ROOT = Path(__file__).resolve().parents[3]
_SPEC_ROOT = _ROOT / ".louke" / "project" / "specs" / "v0.14-002-workflow-reflow-design"


def _manifest() -> dict[str, Any]:
    return json.loads(
        (
            _SPEC_ROOT / "design-artifacts" / "prompts" / "prompt-bundle.candidate.json"
        ).read_bytes()
    )


def _repo_copy(tmp_path: Path) -> Path:
    """Materialise a repo root carrying the two prompts and the transformer."""
    root = tmp_path / "repo"
    (root / "louke" / "agents").mkdir(parents=True)
    for rel in ("louke/agents/Archer.md", "louke/agents/Prism.md", "louke/board.py"):
        shutil.copy2(_ROOT / rel, root / rel)
    return root


def test_closed_source_set_is_exactly_two_prompts() -> None:
    """AC-FR1700-01: the closed source set is exactly Archer.md + Prism.md."""
    manifest = _manifest()
    pb.verify_closed_set(manifest)  # does not raise
    assert manifest["closed_source_set"] == list(pb.CLOSED_SOURCE_SET)


def test_scope_denied_on_unlisted_prompt() -> None:
    """AC-FR2100-01: smuggling an unlisted prompt fails closed."""
    manifest = _manifest()
    manifest["closed_source_set"] = [*pb.CLOSED_SOURCE_SET, "louke/agents/Devon.md"]
    with pytest.raises(pb.PromptBundleError) as exc:
        pb.verify_closed_set(manifest)
    assert exc.value.code == "PROMPT_SCOPE_DENIED"


def test_bundle_digest_recomputes_to_recorded() -> None:
    """AC-FR2000-01/AC-NFR0100-01: the canonical bundle digest recomputes exactly."""
    manifest = _manifest()
    assert pb.compute_bundle_digest(manifest) == manifest["bundle_digest"]
    assert pb.compute_bundle_digest(manifest) == pb.compute_bundle_digest(manifest)


def test_manifest_carries_required_bundle_identity_fields() -> None:
    """AC-FR1800-01: every required bundle/source identity field is present."""
    manifest = _manifest()
    assert manifest["schema_version"] and manifest["bundle_version"]
    assert manifest["transformer"]["version"]
    for source in manifest["sources"]:
        for field in (
            "path",
            "digest",
            "role",
            "frontmatter",
            "permissions",
            "model_abstraction",
            "protocol_refs",
            "skill_refs",
            "input_schema_ref",
            "output_schema_ref",
        ):
            assert source[field]


def test_activation_state_is_candidate_not_deployed() -> None:
    """AC-FR2050-01: the candidate cannot self-activate; state is not-deployed."""
    manifest = _manifest()
    assert manifest["activation_state"] == "candidate-not-deployed"
    assert manifest["activation_prerequisites"]


def test_staging_readback_in_sync_matches_recorded(tmp_path: Path) -> None:
    """AC-FR2000-01: readback of the pinned tree is candidate_staging_in_sync."""
    result = pb.staging_readback(_manifest(), spec_root=_SPEC_ROOT, repo_root=_ROOT)
    assert result["status"] == "candidate_staging_in_sync"
    recorded = json.loads(
        (
            _SPEC_ROOT
            / "design-artifacts"
            / "prompts"
            / "deployment-readback.candidate.json"
        ).read_bytes()
    )
    assert result["transformer_actual"] == recorded["transformer_expected"]
    assert [r["role"] for r in result["records"]] == [
        r["role"] for r in recorded["records"]
    ]
    for got, exp in zip(result["records"], recorded["records"], strict=True):
        assert got["source_actual"] == exp["source_actual"]
        assert got["render_actual"] == exp["render_actual"]


def test_staging_readback_missing_when_source_absent(tmp_path: Path) -> None:
    """AC-FR2000-01: an absent source copy reads back missing."""
    result = pb.staging_readback(_manifest(), spec_root=_SPEC_ROOT, repo_root=tmp_path)
    assert result["status"] == "missing"


def test_staging_readback_drifted_on_source_edit(tmp_path: Path) -> None:
    """AC-FR2000-01: a hand-edited prompt source is detected as drift."""
    repo = _repo_copy(tmp_path)
    archer = repo / "louke" / "agents" / "Archer.md"
    archer.write_text(archer.read_text() + "\n<!-- human edit -->\n", encoding="utf-8")
    result = pb.staging_readback(_manifest(), spec_root=_SPEC_ROOT, repo_root=repo)
    assert result["status"] == "drifted"


def test_staging_readback_stale_on_transformer_change(tmp_path: Path) -> None:
    """AC-FR2000-01: a changed transformer (board.py) makes the bundle stale."""
    repo = _repo_copy(tmp_path)
    board = repo / "louke" / "board.py"
    board.write_text(board.read_text() + "\n# transformer change\n", encoding="utf-8")
    result = pb.staging_readback(_manifest(), spec_root=_SPEC_ROOT, repo_root=repo)
    assert result["status"] == "stale"


def test_bundle_digest_drift_raises(tmp_path: Path) -> None:
    """AC-FR2000-01: a tampered recorded bundle digest fails closed."""
    manifest = copy.deepcopy(_manifest())
    manifest["bundle_digest"] = "sha256:" + "0" * 64
    with pytest.raises(pb.PromptBundleError) as exc:
        pb.verify_bundle_digest(manifest)
    assert exc.value.code == "PROMPT_DRIFT"
