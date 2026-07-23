"""AC-FR0400-01: Task manifest, single writer & external modifications.

Each task attempt must have a manifest binding baseline commit, Issue/FR/AC,
design refs, phase, write/forbidden scopes, test commands, Human/external
diff, prompt/schema identity and output contract.  An ordinary feature
holds at most one active write lease at a time; Agent out-of-scope
modifications are rejected.  Human/external modifications are preserved and
handed to the current specialist Agent: acceptable -> controlled commit,
technical issue -> discussion, source-unknown or baseline-changing ->
stop and reconcile/return upstream.
"""

from __future__ import annotations

from typing import Any

import pytest

from louke.runtime.task_manifest import (
    ExternalDiff,
    TaskLease,
    TaskLeaseError,
    TaskManifest,
    TaskManifestError,
    build_manifest,
    classify_external_diff,
    decide_lease,
)

_BASELINE_OID = "b" * 40


def _manifest_kwargs(*, attempt_no: int = 1, **overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "run_id": "run-1",
        "task_id": "t-001",
        "attempt_no": attempt_no,
        "graph_revision": "graph-rev:abc",
        "baseline_commit": _BASELINE_OID,
        "issue_id": 284,
        "fr_ids": ("FR-0100",),
        "nfr_ids": (),
        "ac_ids": ("AC-FR0100-01",),
        "design_refs": ("design-rev:abc",),
        "phase": "red",
        "write_scopes": ("louke/v014/fr0100_m_impl_entry.py",),
        "forbidden_scopes": ("louke/_tools/",),
        "test_commands": {"unit": ".venv/bin/python3 -m pytest -q"},
        "prompt_bundle": "bundle:abc",
        "schema_refs": ("schema:rgr",),
        "output_contract": "rgr-output:v1",
        "deadline": "2026-07-22T00:00:00Z",
        "retry_policy": {"max_attempts": 3},
    }
    base.update(overrides)
    return base


def test_build_manifest_returns_immutable_record() -> None:
    """AC-FR0400-01: manifest carries baseline/issue/FR/AC/scopes/commands/etc."""
    manifest = build_manifest(**_manifest_kwargs())
    assert isinstance(manifest, TaskManifest)
    assert manifest.baseline_commit == _BASELINE_OID
    assert manifest.issue_id == 284
    assert manifest.fr_ids == ("FR-0100",)
    assert manifest.ac_ids == ("AC-FR0100-01",)
    assert manifest.phase == "red"
    assert manifest.write_scopes == ("louke/v014/fr0100_m_impl_entry.py",)
    assert manifest.test_commands["unit"].endswith("pytest -q")
    assert manifest.prompt_bundle == "bundle:abc"
    assert manifest.schema_refs == ("schema:rgr",)
    assert manifest.output_contract == "rgr-output:v1"
    with pytest.raises(Exception):
        manifest.phase = "green"  # type: ignore[misc]


def test_build_manifest_rejects_missing_required_field() -> None:
    """AC-FR0400-01: missing required field blocks manifest creation."""
    kwargs = _manifest_kwargs()
    del kwargs["baseline_commit"]
    with pytest.raises(TaskManifestError) as exc:
        build_manifest(**kwargs)
    assert exc.value.code == "TASK_MANIFEST_INCOMPLETE"


def test_decide_lease_grants_single_writer_for_feature() -> None:
    """AC-FR0400-01: an ordinary feature task grants at most one active lease."""
    manifest = build_manifest(**_manifest_kwargs())
    decision = decide_lease(manifest, existing_active_lease=None, actor="devon:1")
    assert decision.granted is True
    assert isinstance(decision.lease, TaskLease)
    assert decision.lease.holder_role == "devon"


def test_decide_lease_rejects_second_concurrent_lease() -> None:
    """AC-FR0400-01: a second concurrent lease for the same task is rejected."""
    manifest = build_manifest(**_manifest_kwargs())
    first = decide_lease(manifest, existing_active_lease=None, actor="devon:1")
    second = decide_lease(manifest, existing_active_lease=first.lease, actor="devon:2")
    assert second.granted is False
    assert second.reason_code == "TASK_LEASE_HELD"
    assert second.lease is None


def test_decide_lease_rejects_agent_out_of_scope_modification() -> None:
    """AC-FR0400-01: Agent edits outside write_scopes are rejected."""
    manifest = build_manifest(**_manifest_kwargs())
    with pytest.raises(TaskLeaseError) as exc:
        decide_lease(
            manifest,
            existing_active_lease=None,
            actor="devon:1",
            requested_write_paths=("louke/_tools/secret.py",),
        )
    assert exc.value.code == "TASK_SCOPE_DENIED"


def test_classify_external_diff_accepts_attributed_human() -> None:
    """AC-FR0400-01: attributed Human diff -> controlled commit."""
    diff = ExternalDiff(
        paths=("louke/v014/fr0100_m_impl_entry.py",),
        source="human",
        baseline_changed=False,
        digest="sha256:" + "h" * 64,
    )
    classification = classify_external_diff(diff)
    assert classification.disposition == "accept"
    assert classification.route == "controlled-commit"


def test_classify_external_diff_routes_technical_issue_to_discussion() -> None:
    """AC-FR0400-01: technical issue -> discussion."""
    diff = ExternalDiff(
        paths=("louke/v014/fr0100_m_impl_entry.py",),
        source="external-attributed",
        baseline_changed=False,
        digest="sha256:" + "e" * 64,
        technical_concern="scope-conflict",
    )
    classification = classify_external_diff(diff)
    assert classification.disposition == "discuss"
    assert classification.route == "discussion"


def test_classify_external_diff_stops_when_source_unknown() -> None:
    """AC-FR0400-01: source-unknown external diff stops the task."""
    diff = ExternalDiff(
        paths=("louke/v014/fr0100_m_impl_entry.py",),
        source="unknown",
        baseline_changed=False,
        digest="sha256:" + "u" * 64,
    )
    classification = classify_external_diff(diff)
    assert classification.disposition == "stop"
    assert classification.route == "reconcile"


def test_classify_external_diff_stops_when_baseline_changed() -> None:
    """AC-FR0400-01: baseline-changing external diff stops without overwriting."""
    diff = ExternalDiff(
        paths=("louke/v014/fr0100_m_impl_entry.py",),
        source="external-attributed",
        baseline_changed=True,
        digest="sha256:" + "b" * 64,
    )
    classification = classify_external_diff(diff)
    assert classification.disposition == "stop"
    assert classification.route == "return-upstream"


def test_manifest_attempt_no_increments_on_correction() -> None:
    """AC-FR0400-01: a new attempt_no is allocated when manifest content changes."""
    m1 = build_manifest(**_manifest_kwargs(attempt_no=1))
    m2 = build_manifest(**_manifest_kwargs(attempt_no=2, phase="green"))
    assert m1.attempt_no != m2.attempt_no
    assert m2.phase == "green"
