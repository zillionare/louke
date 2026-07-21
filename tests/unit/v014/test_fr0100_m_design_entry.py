"""AC-FR0100-01: M-DESIGN entry & revision identity.

Runtime may only enter M-DESIGN when the approved requirements digests, base
commit and host-project facts snapshot are all current; entry must persist a
record that binds run/release/revision/attempt/actor and every input identity.
Any missing, stale or conflicting input blocks Archer dispatch with a stable
fail-closed reason.  No Git/GitHub/stage side effects are emitted.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from louke.v014.fr0100_m_design_entry import (
    DesignEntryError,
    DesignRevisionRecord,
    enter_m_design,
)

_ROOT = Path(__file__).resolve().parents[3]
_SPEC_ROOT = _ROOT / ".louke" / "project" / "specs" / "v0.14-002-workflow-reflow-design"
_MANIFEST = _SPEC_ROOT / "design-artifacts" / "design-artifact-manifest.candidate.json"


def _approved_inputs() -> dict[str, Any]:
    return {
        "run_id": "run-v0.14.002-r1",
        "release_identity": {
            "version": "0.14.0",
            "spec_id": "v0.14-002-workflow-reflow-design",
            "branch": "releases/0.14.0",
            "tag": "v0.14.0",
        },
        "actor_id": "human:alice",
        "attempt_id": "att-prism-r3-remediation",
        "requirements": {
            "story": "sha256:06d5573efbf59dd18b480d6539ad16df237fd4460f9f95d1589110cbfeec1993",
            "spec": "sha256:315c8d20254fceb63971b029d69c81889972eedb581621981a012f17edc8867f",
            "acceptance": "sha256:39b09cbf36cc0f4f0dcc8f0e8a79949049a2b6baddcecbcf2183ad407e493559",
        },
        "base_commit": "2734177ef5398e4c10a1f68039ec469ccc21f2b8",
        "project_facts_digest": "sha256:4b1a523c1cf946b480162e5321d3c92aeebdea75f57d5768948aee6f76672130",
        "task_manifest_digest": "sha256:0a9d58474340e9520af49d2bea462c41533c1fabc81afbcf4f5f292caecefbfc",
    }


def test_enter_m_design_persists_full_identity_record() -> None:
    """AC-FR0100-01: current inputs yield a record binding every identity."""
    record = enter_m_design(_approved_inputs(), spec_root=_SPEC_ROOT)
    assert isinstance(record, DesignRevisionRecord)
    assert record.run_id == "run-v0.14.002-r1"
    assert record.release_identity["version"] == "0.14.0"
    assert record.attempt_id == "att-prism-r3-remediation"
    assert record.actor_id == "human:alice"
    assert record.base_commit == "2734177ef5398e4c10a1f68039ec469ccc21f2b8"
    assert record.requirements["acceptance"].startswith("sha256:")
    assert record.project_facts_digest.startswith("sha256:")
    assert record.task_manifest_digest.startswith("sha256:")
    assert record.design_revision_id  # Runtime establishes a unique revision id
    assert record.block_reason is None


def test_enter_m_design_blocks_when_requirements_digest_missing() -> None:
    """AC-FR0100-01: missing approval digest blocks Archer dispatch."""
    inputs = _approved_inputs()
    del inputs["requirements"]["acceptance"]
    with pytest.raises(DesignEntryError) as exc:
        enter_m_design(inputs, spec_root=_SPEC_ROOT)
    assert exc.value.code == "DESIGN_INPUT_MISSING"
    assert "acceptance" in exc.value.message


def test_enter_m_design_blocks_when_base_commit_conflicts() -> None:
    """AC-FR0100-01: base commit mismatch with project facts is a conflict."""
    inputs = _approved_inputs()
    inputs["base_commit"] = "deadbeef" * 5
    with pytest.raises(DesignEntryError) as exc:
        enter_m_design(inputs, spec_root=_SPEC_ROOT)
    assert exc.value.code == "BASE_COMMIT_CONFLICT"


def test_enter_m_design_blocks_when_facts_stale() -> None:
    """AC-FR0100-01: stale project-facts digest blocks dispatch."""
    inputs = _approved_inputs()
    inputs["project_facts_digest"] = "sha256:" + "0" * 64
    with pytest.raises(DesignEntryError) as exc:
        enter_m_design(inputs, spec_root=_SPEC_ROOT)
    assert exc.value.code == "DESIGN_INPUT_STALE"


def test_enter_m_design_blocks_when_attempt_already_dispatched() -> None:
    """AC-FR0100-01: a duplicate attempt id is rejected, no second dispatch."""
    inputs = _approved_inputs()
    first = enter_m_design(inputs, spec_root=_SPEC_ROOT)
    with pytest.raises(DesignEntryError) as exc:
        enter_m_design(inputs, spec_root=_SPEC_ROOT, prior_attempts=[first])
    assert exc.value.code == "DESIGN_INPUT_STALE"
    assert "attempt" in exc.value.message.lower()


def test_record_is_immutable_and_reidentifies_inputs() -> None:
    """AC-FR0100-01: the persisted record is immutable and reidentifies inputs."""
    record = enter_m_design(_approved_inputs(), spec_root=_SPEC_ROOT)
    with pytest.raises(Exception):
        record.run_id = "tampered"  # type: ignore[misc]
    again = enter_m_design(_approved_inputs(), spec_root=_SPEC_ROOT)
    assert again.design_revision_id == record.design_revision_id


def test_record_carries_no_stage_side_effects() -> None:
    """AC-FR0100-01: entry does not emit Git/GitHub/stage side effects."""
    record = enter_m_design(_approved_inputs(), spec_root=_SPEC_ROOT)
    assert record.side_effects_emitted == ()


def test_enter_m_design_uses_canonical_artifact_inputs() -> None:
    """AC-FR0100-01: Runtime binds the actual candidate manifest/facts identity."""
    manifest = json.loads(_MANIFEST.read_bytes())
    inputs = _approved_inputs()
    record = enter_m_design(inputs, spec_root=_SPEC_ROOT)
    facts_artifact = next(
        a
        for a in manifest["input_artifacts"]
        if a["kind"] == "host-project-facts-snapshot"
    )
    task_artifact = next(
        a
        for a in manifest["input_artifacts"]
        if a["kind"] == "archer-author-task-manifest"
    )
    assert record.project_facts_digest == facts_artifact["digest"]
    assert record.task_manifest_digest == task_artifact["digest"]
