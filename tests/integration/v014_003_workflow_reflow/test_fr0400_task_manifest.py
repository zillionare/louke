"""Integration tests for FR-0400: Task manifest, single writer & external
modifications.

AC-FR0400-01: A task manifest can be read with
baseline/Issue/FR/AC/design/phase/scopes/commands/external-diff/prompt/
schema/output identities, and the same ordinary feature grants at most
one active write lease. Agent out-of-scope modifications are rejected.
Human legitimate modifications can be incorporated as controlled
commits; technical issues raise discussion; source-unknown or
baseline-changing modifications stop the task without overwriting.

Interfaces covered (per interfaces.md):
- IF-TASK-01 (Primary ARC-03, ARC-04, manifest+lease authority)
- IF-WFR-01 (workflow current context, ARC-01)
"""
# AC-FR0400-01

from __future__ import annotations

import pytest

from louke.runtime.task_manifest import (
    ERROR_CODES,
    DiffClassification,
    ExternalDiff,
    LeaseDecision,
    TaskLease,
    TaskLeaseError,
    TaskManifest,
    TaskManifestError,
    build_manifest,
    classify_external_diff,
    decide_lease,
)


def _valid_manifest_kwargs() -> dict:
    return {
        "run_id": "run-001",
        "task_id": "T-001",
        "attempt_no": 1,
        "graph_revision": "rev-1",
        "baseline_commit": "a" * 40,
        "issue_id": 284,
        "fr_ids": ["FR-0100"],
        "nfr_ids": [],
        "ac_ids": ["AC-FR0100-01"],
        "design_refs": ["design:rev-1"],
        "phase": "red",
        "write_scopes": ["louke/v014/fr0100_"],
        "forbidden_scopes": ["tests/"],
        "test_commands": {"unit": "pytest -q"},
        "prompt_bundle": "sha256:bundle",
        "schema_refs": ["schema:rgr"],
        "output_contract": "IF-RGR-01",
        "deadline": "2026-12-31T23:59:59Z",
        "retry_policy": {"max_attempts": 3},
    }


# ---------------------------------------------------------------------------
# build_manifest
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_build_manifest_returns_immutable_with_required_fields():
    """AC-FR0400-01: valid manifest has all required identity fields bound."""
    m = build_manifest(**_valid_manifest_kwargs())
    assert isinstance(m, TaskManifest)
    for f in (
        "run_id",
        "task_id",
        "attempt_no",
        "graph_revision",
        "baseline_commit",
        "issue_id",
        "fr_ids",
        "design_refs",
        "phase",
        "write_scopes",
        "forbidden_scopes",
        "test_commands",
        "prompt_bundle",
        "schema_refs",
        "output_contract",
        "deadline",
        "retry_policy",
    ):
        assert getattr(m, f) is not None, f"manifest missing {f}"


@pytest.mark.real_module
def test_build_manifest_rejects_missing_required_field():
    """AC-FR0400-01: missing required field -> TASK_MANIFEST_INCOMPLETE."""
    kwargs = _valid_manifest_kwargs()
    del kwargs["baseline_commit"]
    with pytest.raises(TaskManifestError) as exc:
        build_manifest(**kwargs)
    assert exc.value.code == "TASK_MANIFEST_INCOMPLETE"


@pytest.mark.real_module
def test_build_manifest_rejects_invalid_phase():
    """AC-FR0400-01: phase must be red|green|refactor|final."""
    kwargs = _valid_manifest_kwargs()
    kwargs["phase"] = "purple"
    with pytest.raises(TaskManifestError) as exc:
        build_manifest(**kwargs)
    assert exc.value.code == "TASK_MANIFEST_INCOMPLETE"


# ---------------------------------------------------------------------------
# decide_lease
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_decide_lease_grants_when_no_existing_lease():
    """AC-FR0400-01: no existing lease -> grant new lease."""
    m = build_manifest(**_valid_manifest_kwargs())
    decision = decide_lease(m, existing_active_lease=None, actor="devon:1")
    assert isinstance(decision, LeaseDecision)
    assert decision.granted is True
    assert isinstance(decision.lease, TaskLease)
    assert decision.lease.holder_role == "devon"
    assert decision.lease.task_id == "T-001"


@pytest.mark.real_module
def test_decide_lease_denies_when_active_lease_exists():
    """AC-FR0400-01: ordinary feature has at most one active write lease."""
    m = build_manifest(**_valid_manifest_kwargs())
    existing = TaskLease(
        lease_id="lease:abc",
        task_id="T-001",
        attempt_no=1,
        holder_role="devon",
        holder_session="devon:1",
        status="active",
    )
    decision = decide_lease(m, existing_active_lease=existing, actor="devon:2")
    assert decision.granted is False
    assert decision.lease is None
    assert decision.reason_code == "TASK_LEASE_HELD"


@pytest.mark.real_module
def test_decide_lease_grants_after_existing_lease_released():
    """AC-FR0400-01: released lease does not block new grant."""
    m = build_manifest(**_valid_manifest_kwargs())
    existing = TaskLease(
        lease_id="lease:abc",
        task_id="T-001",
        attempt_no=1,
        holder_role="devon",
        holder_session="devon:1",
        status="released",
    )
    decision = decide_lease(m, existing_active_lease=existing, actor="devon:2")
    assert decision.granted is True


@pytest.mark.real_module
def test_decide_lease_rejects_out_of_scope_write_paths():
    """AC-FR0400-01: agent out-of-scope modification -> TASK_SCOPE_DENIED."""
    m = build_manifest(**_valid_manifest_kwargs())
    with pytest.raises(TaskLeaseError) as exc:
        decide_lease(
            m,
            existing_active_lease=None,
            actor="devon:1",
            requested_write_paths=("tests/integration/forbidden.py",),
        )
    assert exc.value.code == "TASK_SCOPE_DENIED"


@pytest.mark.real_module
def test_decide_lease_rejects_forbidden_scope_write_paths():
    """AC-FR0400-01: forbidden scope path -> TASK_SCOPE_DENIED."""
    m = build_manifest(**_valid_manifest_kwargs())
    # forbidden_scopes is ["tests/"], so writing under tests/ must reject
    # even if also in write_scopes (it isn't here, but the test verifies
    # forbidden always wins).
    with pytest.raises(TaskLeaseError) as exc:
        decide_lease(
            m,
            existing_active_lease=None,
            actor="devon:1",
            requested_write_paths=("tests/foo.py",),
        )
    assert exc.value.code == "TASK_SCOPE_DENIED"


@pytest.mark.real_module
def test_decide_lease_accepts_in_scope_write_paths():
    """AC-FR0400-01: paths inside write_scopes -> grant lease.

    ``_path_in_scopes`` uses prefix match, so ``louke/v014/fr0100_``
    matches any path starting with that prefix.
    """
    m = build_manifest(**_valid_manifest_kwargs())
    decision = decide_lease(
        m,
        existing_active_lease=None,
        actor="devon:1",
        requested_write_paths=("louke/v014/fr0100_m_impl_entry.py",),
    )
    assert decision.granted is True


# ---------------------------------------------------------------------------
# classify_external_diff
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_classify_external_diff_human_accepts_as_controlled_commit():
    """AC-FR0400-01: Human diff without concerns -> controlled-commit."""
    diff = ExternalDiff(
        paths=("docs/notes.md",),
        source="human",
        baseline_changed=False,
        digest="sha256:diff",
    )
    classification = classify_external_diff(diff)
    assert isinstance(classification, DiffClassification)
    assert classification.disposition == "accept"
    assert classification.route == "controlled-commit"


@pytest.mark.real_module
def test_classify_external_diff_technical_concern_routes_to_discussion():
    """AC-FR0400-01: technical concern -> discussion (not Human judgment)."""
    diff = ExternalDiff(
        paths=("louke/v014/x.py",),
        source="human",
        baseline_changed=False,
        digest="sha256:diff",
        technical_concern="scope-conflict",
    )
    classification = classify_external_diff(diff)
    assert classification.disposition == "discuss"
    assert classification.route == "discussion"


@pytest.mark.real_module
def test_classify_external_diff_unknown_source_stops_and_reconciles():
    """AC-FR0400-01: unknown source -> stop + reconcile; never overwrite."""
    diff = ExternalDiff(
        paths=("x.py",),
        source="unknown",
        baseline_changed=False,
        digest="sha256:diff",
    )
    classification = classify_external_diff(diff)
    assert classification.disposition == "stop"
    assert classification.route == "reconcile"


@pytest.mark.real_module
def test_classify_external_diff_baseline_change_stops_and_returns_upstream():
    """AC-FR0400-01: baseline-changing diff -> stop + return upstream."""
    diff = ExternalDiff(
        paths=("x.py",),
        source="human",
        baseline_changed=True,
        digest="sha256:diff",
    )
    classification = classify_external_diff(diff)
    assert classification.disposition == "stop"
    assert classification.route == "return-upstream"


@pytest.mark.real_module
def test_classify_external_diff_rejects_unrecognized_source():
    """AC-FR0400-01: source not in {human, external-attributed, unknown} ->
    TASK_EXTERNAL_DIFF_UNKNOWN."""
    diff = ExternalDiff(
        paths=("x.py",),
        source="rogue-tool",
        baseline_changed=False,
        digest="sha256:diff",
    )
    with pytest.raises(TaskManifestError) as exc:
        classify_external_diff(diff)
    assert exc.value.code == "TASK_EXTERNAL_DIFF_UNKNOWN"


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-FR0400-01: ERROR_CODES includes all codes from interfaces.md §3."""
    expected = {
        "TASK_MANIFEST_INCOMPLETE",
        "TASK_SCOPE_DENIED",
        "TASK_LEASE_HELD",
        "TASK_LEASE_LOST",
        "TASK_BASELINE_STALE",
        "TASK_EXTERNAL_DIFF_UNKNOWN",
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
