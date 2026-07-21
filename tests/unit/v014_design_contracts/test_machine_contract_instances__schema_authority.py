"""AC-FR1900-01: IF-CON-01 machine contract instance envelope + provenance.

The registry is the sole schema authority: the seven candidate machine-contract
instances validate against the packaged active schemas (never a self-embedded or
substitute schema), each referencing the active schema digest, and their
external-manifest bytes digest plus facts/task provenance resolve.  The eight
design-authored negative mutations must all be rejected at the declared
schema/provenance boundary.  Read-only over design artifacts.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from louke._tools import contract_registry as reg
from louke._tools import machine_contract as mc

_SPEC_ROOT = (
    Path(__file__).resolve().parents[3]
    / ".louke"
    / "project"
    / "specs"
    / "v0.14-002-workflow-reflow-design"
)
_DA = _SPEC_ROOT / "design-artifacts"
_REQUIRED_KINDS = (
    "integration-test",
    "e2e-test",
    "pre-commit",
    "github-actions-ci",
    "release-version",
    "build-artifact",
    "publish-recovery",
)


def _instance(kind: str) -> dict[str, Any]:
    return json.loads((_DA / "contracts" / f"{kind}.candidate.json").read_bytes())


def _negative_cases() -> list[dict[str, Any]]:
    fixtures = json.loads(
        (_DA / "validation" / "negative-schema-fixtures.candidate.json").read_bytes()
    )
    return fixtures["cases"]


def _apply_mutation(doc: Any, operation: str, pointer: str, value: Any = None) -> None:
    parts = [p for p in pointer.split("/") if p != ""]
    target = doc
    for part in parts[:-1]:
        target = target[int(part)] if isinstance(target, list) else target[part]
    last = parts[-1]
    if isinstance(target, list):
        idx = int(last)
        if operation == "remove":
            target.pop(idx)
        else:
            target[idx] = value
    else:
        if operation == "remove":
            del target[last]
        else:
            target[last] = value


# --- schema authority (FR-1900) ---------------------------------------------


def test_all_machine_instances_validate_against_active_schema() -> None:
    """AC-FR1900-01: every candidate instance validates against its active schema."""
    view = {s["identity"]: s for s in reg.discover().schemas}
    for kind in _REQUIRED_KINDS:
        identity = f"louke.machine-contract.{kind}"
        packaged = view[identity]["digest"]
        instance = _instance(kind)
        assert instance["schema_ref"]["digest"] == packaged  # references active schema
        ref = reg.SchemaRef(identity, "1.0.0", packaged)
        result = reg.validate(ref, json.dumps(instance).encode("utf-8"))
        assert result.valid is True, (kind, result.errors)


def test_instance_cannot_self_substitute_schema() -> None:
    """AC-FR1900-01: editing instance content never overrides schema authority."""
    instance = _instance("integration-test")
    instance["embedded_schema"] = {"type": "object"}  # a self-declared schema
    identity = "louke.machine-contract.integration-test"
    packaged = next(s for s in reg.discover().schemas if s["identity"] == identity)[
        "digest"
    ]
    ref = reg.SchemaRef(identity, "1.0.0", packaged)
    result = reg.validate(ref, json.dumps(instance).encode("utf-8"))
    # The active schema forbids unknown top-level fields; the embedded schema is ignored.
    assert result.valid is False
    assert any(err["keyword"] == "additionalProperties" for err in result.errors)


# --- IF-CON-01 provenance + external-manifest digest resolution --------------


def test_resolve_contract_returns_external_manifest_digest() -> None:
    """AC-FR1900-01: full instance bytes digest resolves from the unique manifest entry."""
    manifest = mc.load_manifest(_SPEC_ROOT)
    for kind in _REQUIRED_KINDS:
        resolved = mc.resolve_contract(_instance(kind), manifest, spec_root=_SPEC_ROOT)
        assert resolved.contract_path.endswith(f"contracts/{kind}.candidate.json")
        assert resolved.contract_digest.startswith("sha256:")


def test_verify_provenance_passes_for_authored_instances() -> None:
    """AC-FR1900-01: facts/task digests resolve to the declared kind/path/bytes."""
    manifest = mc.load_manifest(_SPEC_ROOT)
    for kind in _REQUIRED_KINDS:
        mc.verify_provenance(
            _instance(kind), manifest, spec_root=_SPEC_ROOT
        )  # no raise


def test_verify_provenance_rejects_kind_swap() -> None:
    """AC-FR1900-01: swapping facts/task artifact kinds fails provenance closed."""
    manifest = mc.load_manifest(_SPEC_ROOT)
    instance = _instance("integration-test")
    instance["scope"]["project_facts_artifact"]["kind"] = "archer-author-task-manifest"
    instance["generated_by"]["task_manifest_artifact"]["kind"] = (
        "host-project-facts-snapshot"
    )
    with pytest.raises(mc.ContractError) as excinfo:
        mc.verify_provenance(instance, manifest, spec_root=_SPEC_ROOT)
    assert excinfo.value.code == "CONTRACT_PROVENANCE_MISMATCH"


# --- design-authored negative fixtures (all eight must fail) -----------------


@pytest.mark.parametrize("case", _negative_cases(), ids=lambda c: c["id"])
def test_negative_fixture_is_rejected_with_expected_keyword(
    case: dict[str, Any],
) -> None:
    """AC-FR1900-01: each authored mutation is rejected at the schema boundary."""
    target = json.loads(
        (_DA / Path(case["target_path"]).relative_to("design-artifacts")).read_bytes()
    )
    mutated = copy.deepcopy(target)
    for mutation in case["mutations"]:
        _apply_mutation(
            mutated, mutation["operation"], mutation["pointer"], mutation.get("value")
        )
    identity = case["schema_identity"]
    packaged = next(s for s in reg.discover().schemas if s["identity"] == identity)[
        "digest"
    ]
    ref = reg.SchemaRef(identity, "1.0.0", packaged)
    result = reg.validate(ref, json.dumps(mutated).encode("utf-8"))
    assert result.valid is False
    expected = case["required_failure"]["keyword"]
    assert any(err["keyword"] == expected for err in result.errors), (
        case["id"],
        result.errors,
    )


def test_negative_positive_controls_validate() -> None:
    """AC-FR1900-01: the unmutated fixture targets are the positive control."""
    seen: set[str] = set()
    for case in _negative_cases():
        rel = Path(case["target_path"]).relative_to("design-artifacts")
        if str(rel) in seen:
            continue
        seen.add(str(rel))
        target = json.loads((_DA / rel).read_bytes())
        identity = case["schema_identity"]
        packaged = next(s for s in reg.discover().schemas if s["identity"] == identity)[
            "digest"
        ]
        ref = reg.SchemaRef(identity, "1.0.0", packaged)
        result = reg.validate(ref, json.dumps(target).encode("utf-8"))
        assert result.valid is True, (str(rel), result.errors)
